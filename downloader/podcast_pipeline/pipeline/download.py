"""Stage 3: download audio for every episode that needs it.

Works straight off ``episodes.status``, so an interrupted run resumes where
it stopped. Episodes whose feed advertises a transcript are skipped; their
text comes from ``fetch-rss-transcripts`` instead.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from podcast_pipeline import db
from podcast_pipeline.audio.disk import DiskSpaceError
from podcast_pipeline.audio.download import AudioDownloader, DownloadError, DownloadResult
from podcast_pipeline.config import Config

logger = logging.getLogger(__name__)


def pending_episodes(conn: sqlite3.Connection, retry_errors: bool, limit: int | None) -> list[sqlite3.Row]:
    statuses = [db.EpisodeStatus.PENDING] + ([db.EpisodeStatus.ERROR] if retry_errors else [])
    # An error row with audio on disk failed at transcription, not download.
    return conn.execute(f"""
        SELECT e.id, e.episode_guid, e.title, e.audio_url, p.title AS podcast_title
        FROM episodes e JOIN podcasts p ON p.id = e.podcast_id
        WHERE e.status IN ({",".join("?" * len(statuses))})
          AND e.audio_file_path IS NULL
          AND e.has_rss_transcript = 0
          AND e.audio_url IS NOT NULL AND e.audio_url != ''
        ORDER BY e.id
        {"LIMIT ?" if limit else ""}
    """, statuses + ([limit] if limit else [])).fetchall()


def run(config: Config, conn: sqlite3.Connection, limit: int | None = None,
        retry_errors: bool = True, workers: int | None = None) -> dict:
    episodes = pending_episodes(conn, retry_errors, limit)
    workers = workers or config.download.max_workers
    logger.info(f"Downloading {len(episodes)} episodes with {workers} workers")
    stats = {"total": len(episodes), "downloaded": 0, "reused": 0, "failed": 0, "not_attempted": 0}
    if not episodes:
        return stats

    downloader = AudioDownloader(
        config.audio_dir, config.audio_compression,
        timeout=config.download.timeout_seconds,
        min_free_gb=config.download.min_free_gb, pool_size=workers,
    )
    stop = threading.Event()

    def fetch(row: sqlite3.Row) -> DownloadResult | None:
        if stop.is_set():
            return None
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
                db.record_download(conn, row["id"], result.path, result.original_size_mb,
                                   result.compressed_size_mb, result.is_compressed)
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
