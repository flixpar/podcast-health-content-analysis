"""Fetch the transcripts publishers already attach to their feeds.

Pure HTTP, no GPU, and publisher transcripts usually carry speaker labels
that ASR does not. Run this before ``download``: an episode with a publisher
transcript never needs its audio fetched.
"""

from __future__ import annotations

import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import requests

from podcast_pipeline import db
from podcast_pipeline.config import Config
from podcast_pipeline.http import make_session
from podcast_pipeline.models import Segment
from podcast_pipeline.transcripts.parsers import parse_transcript
from podcast_pipeline.transcripts.store import TranscriptStore, has_speaker_labels

logger = logging.getLogger(__name__)


class RssTranscriptError(RuntimeError):
    """Carries the outcome category ('http_error', 'unparseable', 'too_short')."""

    def __init__(self, category: str, detail: str):
        super().__init__(f"{category}: {detail}")
        self.category = category


@dataclass
class FetchedTranscript:
    segments: list[Segment]
    source_format: str


def fetch_one(session: requests.Session, url: str, timeout: int, min_words: int) -> FetchedTranscript:
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RssTranscriptError("http_error", str(e)) from e

    segments, source_format = parse_transcript(response.text, response.headers.get("content-type", ""))
    if not segments:
        raise RssTranscriptError("unparseable", f"{source_format} ({len(response.text)} bytes)")
    words = sum(len(s.text.split()) for s in segments)
    if words < min_words:
        raise RssTranscriptError("too_short", f"{words} words")
    return FetchedTranscript(segments, source_format)


def run(config: Config, conn: sqlite3.Connection, limit: int | None = None,
        workers: int = 8, timeout: int = 60, min_words: int = 100) -> dict:
    rows = conn.execute(f"""
        SELECT id, transcript_url, title
        FROM episodes
        WHERE has_rss_transcript = 1
          AND transcript_url IS NOT NULL AND transcript_url != ''
          AND (transcript_file_path IS NULL OR transcript_file_path = '')
        ORDER BY id
        {"LIMIT ?" if limit else ""}
    """, (limit,) if limit else ()).fetchall()
    logger.info(f"Fetching {len(rows)} publisher transcripts with {workers} workers")
    stats = {"total": len(rows), "saved": 0}
    if not rows:
        return stats

    store = TranscriptStore(config.transcript_dir, config.storage.transcript_compression_level)
    session = make_session(pool_size=workers)
    failures: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_one, session, row["transcript_url"], timeout, min_words): row
                   for row in rows}
        for i, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            try:
                fetched = future.result()
            except RssTranscriptError as e:
                stats[e.category] = stats.get(e.category, 0) + 1
                failures.append(f"episode {row['id']}: {e}")
                continue

            saved = store.save(row["id"], fetched.segments, {
                "source": "rss", "source_format": fetched.source_format,
                "source_url": row["transcript_url"], "episode_title": row["title"],
            })
            db.record_transcript(conn, row["id"], saved.path, saved.word_count,
                                 saved.duration_seconds, saved.has_timestamps,
                                 has_speaker_labels(fetched.segments),
                                 {"source": "rss", "source_format": fetched.source_format})
            conn.commit()
            stats["saved"] += 1
            if i % 100 == 0:
                logger.info(f"  {i}/{len(rows)} -- {stats}")

    logger.info(f"RSS transcript fetch complete: {stats}")
    for line in failures[:10]:
        logger.info(f"  {line}")
    return stats
