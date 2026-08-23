"""Stage 2: read every podcast's feed and record its episodes.

Only metadata is written here; audio is fetched by the ``download`` stage.
Feed parsing takes minutes while downloading takes days, so keeping them
apart means the whole backlog is visible immediately and downloading can be
resumed freely.
"""

from __future__ import annotations

import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

from podcast_pipeline import db
from podcast_pipeline.config import Config
from podcast_pipeline.http import make_session
from podcast_pipeline.rss import FeedError, fetch_feed

logger = logging.getLogger(__name__)


def run(config: Config, conn: sqlite3.Connection, max_episodes: int | None = None) -> dict:
    max_episodes = max_episodes or config.discovery.max_episodes_per_podcast
    podcasts = conn.execute(
        "SELECT id, title, rss_url FROM podcasts WHERE rss_url IS NOT NULL AND rss_url != ''"
    ).fetchall()
    logger.info(f"Discovering episodes for {len(podcasts)} podcasts "
                f"(newest {max_episodes} per feed)")

    workers = config.discovery.max_parallel_feeds
    session = make_session(pool_size=workers)
    stats = {"podcasts": len(podcasts), "feed_errors": 0, "episodes_seen": 0,
             "episodes_new": 0, "with_rss_transcript": 0}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_feed, row["rss_url"], session, config.discovery.feed_timeout_seconds): row
            for row in podcasts
        }
        for future in as_completed(futures):
            podcast = futures[future]
            try:
                episodes = future.result()[:max_episodes]
            except FeedError as e:
                logger.error(f"Feed failed for {podcast['title']!r}: {e}")
                db.set_podcast_status(conn, podcast["id"], db.PodcastStatus.ERROR)
                conn.commit()
                stats["feed_errors"] += 1
                continue

            new = sum(db.insert_episode(conn, podcast["id"], ep) for ep in episodes)
            db.set_podcast_status(conn, podcast["id"], db.PodcastStatus.DISCOVERED)
            conn.commit()   # one transaction per feed: atomic and already parsed

            stats["episodes_seen"] += len(episodes)
            stats["episodes_new"] += new
            stats["with_rss_transcript"] += sum(ep.has_transcript for ep in episodes)
            logger.info(f"{podcast['title']!r}: {len(episodes)} episodes, {new} new")

    logger.info(f"Discovery complete: {stats}")
    return stats
