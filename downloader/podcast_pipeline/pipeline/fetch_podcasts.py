"""Stage 1: fetch a podcast chart and record each podcast.

Runs are additive. The collection is built from several charts fetched on
different days, so a podcast already in the database is updated in place (it
keeps its id and therefore its episodes) and its membership in this chart is
recorded in ``podcast_charts``.
"""

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
    logger.info(f"Fetching top {limit} podcasts via {config.fetcher.type} "
                f"(chart {source.chart_name})")
    records = source.top_podcasts(limit)

    stats = {"chart": source.chart_name, "fetched": len(records),
             "new": 0, "updated": 0, "without_rss": 0}
    for rank, record in enumerate(records, start=1):
        existed = conn.execute("SELECT 1 FROM podcasts WHERE podchaser_id = ? OR apple_podcasts_id = ?",
                               (record.source_id, record.apple_podcasts_id)).fetchone()
        podcast_id = db.upsert_podcast(conn, record)
        db.record_chart_entry(conn, podcast_id, source.chart_name, rank)
        stats["updated" if existed else "new"] += 1
        if not record.rss_url:
            stats["without_rss"] += 1
            logger.warning(f"No RSS URL for {record.title!r}; it cannot be discovered")
    conn.commit()
    logger.info(f"Podcast fetch complete: {stats}")
    return stats
