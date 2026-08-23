"""Stage 1: fetch the podcast chart and record each podcast."""

from __future__ import annotations

import logging
import sqlite3

from podcast_pipeline import db
from podcast_pipeline.config import Config
from podcast_pipeline.http import make_session
from podcast_pipeline.sources import make_source

logger = logging.getLogger(__name__)


def run(config: Config, conn: sqlite3.Connection, limit: int | None = None) -> dict:
    limit = limit or config.fetcher.default_limit
    source = make_source(config, make_session())
    logger.info(f"Fetching top {limit} podcasts via {config.fetcher.type}")
    records = source.top_podcasts(limit)

    stats = {"fetched": len(records), "new": 0, "updated": 0, "without_rss": 0}
    for record in records:
        existed = conn.execute("SELECT 1 FROM podcasts WHERE podchaser_id = ? OR apple_podcasts_id = ?",
                               (record.source_id, record.apple_podcasts_id)).fetchone()
        db.upsert_podcast(conn, record)
        stats["updated" if existed else "new"] += 1
        if not record.rss_url:
            stats["without_rss"] += 1
            logger.warning(f"No RSS URL for {record.title!r}; it cannot be discovered")
    conn.commit()
    logger.info(f"Podcast fetch complete: {stats}")
    return stats
