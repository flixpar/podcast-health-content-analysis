"""Stage 2: read every podcast's feed and record its episodes.

Only metadata is written here; audio is fetched by the ``download`` stage.
Paged feeds are read across their pages (``rss.read_feed``): some hosts list
only the newest N items per document and link to older ones.
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
from podcast_pipeline.rss import FeedError, read_feed
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

    cfg = config.discovery
    workers = cfg.max_parallel_feeds
    session = make_session(pool_size=workers)
    stats = {"scope": scope, "podcasts": len(podcasts), "feed_errors": 0, "episodes_seen": 0,
             "episodes_new": 0, "with_rss_transcript": 0, "paged_feeds": 0, "extra_pages": 0,
             "feeds_paged_partially": 0}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(read_feed, row["rss_url"], session, cfg.feed_timeout_seconds, cfg.max_feed_pages,
                        cfg.feed_page_size, cfg.feed_page_delay_seconds): row
            for row in podcasts
        }
        for future in as_completed(futures):
            podcast = futures[future]
            try:
                read = future.result()
            except FeedError as e:
                logger.error(f"Feed failed for {podcast['title']!r}: {e}")
                db.set_podcast_status(conn, podcast["id"], db.PodcastStatus.ERROR)
                db.record_feed_read(conn, podcast["id"], podcast["rss_url"], f"error: {e}")
                conn.commit()
                stats["feed_errors"] += 1
                continue

            # Retention is measured on the whole (merged) feed, before the cap trims it.
            # A walk cut short keeps its pages; the status says what is missing.
            feed = read.episodes
            status = f"ok, partial: {read.error}" if read.partial else "ok"
            db.record_feed_read(conn, podcast["id"], podcast["rss_url"], status, feed)
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
            stats["paged_feeds"] += read.pages > 1
            stats["extra_pages"] += read.pages - 1
            stats["feeds_paged_partially"] += read.partial
            pages = f" from {read.pages} pages ({read.stopped})" if read.pages > 1 or read.partial else ""
            logger.info(f"{podcast['title']!r}: {len(episodes)} episodes{pages}, {new} new")

    logger.info(f"Discovery complete: {stats}")
    return stats
