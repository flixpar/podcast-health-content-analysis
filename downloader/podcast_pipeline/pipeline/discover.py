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
from podcast_pipeline.studies.scope import podcast_filter

logger = logging.getLogger(__name__)


def run(config: Config, conn: sqlite3.Connection, max_episodes: int | None = None,
        study: str | None = None, all_podcasts: bool = False) -> dict:
    """Read feeds for one study's podcasts, every study's (the default), or,
    with ``all_podcasts``, every podcast in the catalog.

    The catalog can hold far more podcasts than any study needs (every show
    that ever charted), so reading all of them is opt-in.
    """
    max_episodes = max_episodes or config.discovery.max_episodes_per_podcast
    clause, params = ("", []) if all_podcasts else podcast_filter(conn, study, "id")
    podcasts = conn.execute(
        f"SELECT id, title, rss_url FROM podcasts WHERE rss_url IS NOT NULL AND rss_url != '' {clause}",
        params,
    ).fetchall()
    scope = "all podcasts" if all_podcasts else (f"study {study}" if study else "every study")
    logger.info(f"Discovering episodes for {len(podcasts)} podcasts ({scope}; "
                f"newest {max_episodes} per feed)")

    workers = config.discovery.max_parallel_feeds
    session = make_session(pool_size=workers)
    stats = {"scope": scope, "podcasts": len(podcasts), "feed_errors": 0, "episodes_seen": 0,
             "episodes_new": 0, "with_rss_transcript": 0}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_feed, row["rss_url"], session, config.discovery.feed_timeout_seconds): row
            for row in podcasts
        }
        for future in as_completed(futures):
            podcast = futures[future]
            try:
                feed = future.result()
            except FeedError as e:
                logger.error(f"Feed failed for {podcast['title']!r}: {e}")
                db.set_podcast_status(conn, podcast["id"], db.PodcastStatus.ERROR)
                db.record_feed_read(conn, podcast["id"], podcast["rss_url"], f"error: {e}")
                conn.commit()
                stats["feed_errors"] += 1
                continue

            # Retention is measured on the whole feed, before the cap trims it.
            db.record_feed_read(conn, podcast["id"], podcast["rss_url"], "ok", feed)
            episodes = feed[:max_episodes]
            new = 0
            for ep in episodes:
                new += db.insert_episode(conn, podcast["id"], ep)
                db.record_episode_source(conn, podcast["id"], ep.guid, "feed", podcast["rss_url"])
            db.set_podcast_status(conn, podcast["id"], db.PodcastStatus.DISCOVERED)
            conn.commit()   # one transaction per feed: atomic and already parsed

            stats["episodes_seen"] += len(episodes)
            stats["episodes_new"] += new
            stats["with_rss_transcript"] += sum(ep.has_transcript for ep in episodes)
            logger.info(f"{podcast['title']!r}: {len(episodes)} episodes, {new} new")

    logger.info(f"Discovery complete: {stats}")
    return stats
