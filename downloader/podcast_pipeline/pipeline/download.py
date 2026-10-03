"""Stage 3: download audio for every episode that needs it.

Works straight off ``episodes.status``, so an interrupted run resumes where
it stopped. Episodes whose feed advertises a transcript are skipped; their
text comes from ``fetch-rss-transcripts`` instead.

With ``--wayback-fallback``, an enclosure that is gone (404, dead host) is
retried from the host URL inside its tracking prefixes and from the Wayback
Machine's copies, recorded as an ``unwrapped_audio`` or ``wayback_audio``
episode source.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from podcast_pipeline import db, paths
from podcast_pipeline.audio.disk import DiskSpaceError
from podcast_pipeline.audio.download import AudioDownloader, DownloadError, DownloadResult
from podcast_pipeline.config import Config
from podcast_pipeline.studies.scope import episode_filter, require_any_study

logger = logging.getLogger(__name__)


def pending_episodes(conn: sqlite3.Connection, retry_errors: bool, limit: int | None,
                     charts: list[str] | None = None,
                     study: str | None = None,
                     all_episodes: bool = True) -> list[sqlite3.Row]:
    """Episodes still needing audio, oldest row first.

    ``charts`` restricts the run to podcasts that appear in those charts (see
    ``podcast_charts``). The whole queue takes days, so downloading one chart
    ahead of the rest is how a subset gets prioritised: run with the filter,
    then run again without it to pick up everything else.

    ``study`` restricts it to that study's episodes, in the study's priority
    order: round-robin across its windows, so an interrupted run (or a full
    disk) leaves coverage spread evenly rather than front-loaded. Without a
    study, ``all_episodes=False`` restricts it to the episodes of *any* study
    (what the CLI does by default: the catalog holds far more episodes than
    anyone has asked to collect).
    """
    statuses = [db.EpisodeStatus.PENDING] + ([db.EpisodeStatus.ERROR] if retry_errors else [])
    params = list(statuses)
    chart_filter = ""
    if charts:
        chart_filter = (f"AND e.podcast_id IN (SELECT podcast_id FROM podcast_charts "
                        f"WHERE chart IN ({','.join('?' * len(charts))}))")
        params += charts
    study_clause, study_params = episode_filter(conn, study)
    if not study and not all_episodes:
        require_any_study(conn)
        study_clause = "AND e.id IN (SELECT episode_id FROM study_episodes)"
    params += study_params
    order = "e.id"
    if study:
        order = ("(SELECT priority FROM study_episodes se WHERE se.study = ? "
                 "AND se.episode_id = e.id), e.id")
        params.append(study)
    if limit:
        params.append(limit)
    # An error row with audio on disk failed at transcription, not download.
    return conn.execute(f"""
        SELECT e.id, e.podcast_id, e.episode_guid, e.title, e.audio_url, e.published_date,
               e.duration_seconds, p.title AS podcast_title
        FROM episodes e JOIN podcasts p ON p.id = e.podcast_id
        WHERE e.status IN ({",".join("?" * len(statuses))})
          AND e.audio_file_path IS NULL
          AND e.has_rss_transcript = 0
          AND e.audio_url IS NOT NULL AND e.audio_url != ''
          {chart_filter}
          {study_clause}
        ORDER BY {order}
        {"LIMIT ?" if limit else ""}
    """, params).fetchall()


def run(config: Config, conn: sqlite3.Connection, limit: int | None = None,
        retry_errors: bool = True, workers: int | None = None,
        charts: list[str] | None = None, study: str | None = None,
        wayback_fallback: bool = False, all_episodes: bool = True) -> dict:
    episodes = pending_episodes(conn, retry_errors, limit, charts, study, all_episodes)
    workers = workers or config.download.max_workers
    logger.info(f"Downloading {len(episodes)} episodes with {workers} workers"
                + (f" (charts: {', '.join(charts)})" if charts else "")
                + (f" (study: {study})" if study else ""))
    stats = {"total": len(episodes), "downloaded": 0, "reused": 0, "failed": 0, "not_attempted": 0}
    if wayback_fallback:
        # Of "downloaded": dead enclosures recovered from the URL inside a
        # tracking prefix, or from the Wayback Machine.
        stats["unwrapped_audio"] = 0
        stats["wayback_audio"] = 0
    if charts:
        stats["charts"] = charts
    if study:
        stats["study"] = study
    if not episodes:
        return stats

    downloader = AudioDownloader(
        config.audio_dir, config.audio_compression,
        timeout=config.download.timeout_seconds,
        min_free_gb=config.download.min_free_gb, pool_size=workers,
        wayback_replay_url=config.wayback.replay_url if wayback_fallback else None,
    )
    stop = threading.Event()

    def fetch(row: sqlite3.Row) -> DownloadResult | None:
        if stop.is_set():
            return None
        if wayback_fallback:
            return downloader.download_episode(row["audio_url"], row["podcast_title"],
                                               row["title"] or "unknown", row["episode_guid"],
                                               published_date=row["published_date"],
                                               declared_duration=row["duration_seconds"])
        return downloader.download_episode(row["audio_url"], row["podcast_title"],
                                           row["title"] or "unknown", row["episode_guid"])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, row): row for row in episodes}
        try:
            for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading", unit="ep"):
                row = futures[future]
                try:
                    result = future.result()
                except DownloadError as e:
                    logger.error(f"Download failed for {row['title']!r}: {e}")
                    db.mark_episode_error(conn, row["id"], str(e))
                    conn.commit()
                    stats["failed"] += 1
                    continue
                except DiskSpaceError as e:
                    # Fatal on purpose; nothing downstream can succeed until space is freed.
                    logger.error(f"Halting: {e}")
                    stop.set()
                    stats["not_attempted"] += 1
                    continue

                if result is None:
                    stats["not_attempted"] += 1
                    continue
                db.record_download(conn, row["id"], paths.to_stored(config, result.path),
                                   result.original_size_mb,
                                   result.compressed_size_mb, result.is_compressed)
                if result.fallback_source:
                    db.record_episode_source(conn, row["podcast_id"], row["episode_guid"],
                                             result.fallback_source, result.fallback_url)
                    stats[result.fallback_source] += 1
                conn.commit()
                stats["reused" if result.reused else "downloaded"] += 1
        except BaseException:
            # A bug or Ctrl-C: stop feeding the pool rather than draining 25k queued jobs.
            stop.set()
            pool.shutdown(wait=True, cancel_futures=True)
            raise

    if stop.is_set():
        logger.error("Stopped early on low disk space -- free space and re-run to resume")
    logger.info(f"Download complete: {stats}")
    return stats
