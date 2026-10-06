"""``link-entity``: record a human identity decision for a chart entity.

Automatic resolution (``resolve``) matches chart entities to catalog podcasts
by Apple id and title search. It gets some wrong: a generic title ("Betrayal",
"Serial Killers") lands on an unrelated show, or a show Apple no longer lists
is matched to nothing. A manual decision corrects that. It is written to
``entity_links`` with ``method = 'manual'`` and wins over every automatic rule
(``db.podcast_for_entity``); ``resolve`` treats it as final.

Exactly one target:

* ``podcast_id`` -- a podcast already in the catalog;
* ``apple_id`` -- looked up on iTunes; the podcast is created only if the
  catalog lacks it;
* ``feed_url`` -- the podcast that reads (or once read) that feed; else, for
  'apple:<id>', the catalog podcast holding that Apple id if it has no feed
  (Apple lists the show without one); else a new podcast keyed
  ``feed_<sha1(url)[:12]>`` with the given title and publisher;
* ``unresolvable`` -- no source for the show could be found (``podcast_id``
  NULL).

An existing podcast row is never rewritten; the only change allowed is
filling an empty ``rss_url`` with a feed no other podcast reads. The link's
detail keeps the note, the decision time and the link it replaced.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone

from podcast_pipeline import db
from podcast_pipeline.config import Config
from podcast_pipeline.http import make_session
from podcast_pipeline.models import PodcastRecord
from podcast_pipeline.sources.apple import _to_record, lookup_many

logger = logging.getLogger(__name__)

METHOD = "manual"
ENTITY_KINDS = ("apple", "title")


def feed_source_id(url: str) -> str:
    """The source id of a podcast known only by its feed URL."""
    return f"feed_{hashlib.sha1(url.encode()).hexdigest()[:12]}"


def _previous(conn: sqlite3.Connection, entity: str) -> dict | None:
    row = conn.execute("SELECT podcast_id, method, detail, resolved_at FROM entity_links WHERE entity = ?",
                       (entity,)).fetchone()
    if row is None:
        return None
    return {"podcast_id": row["podcast_id"], "method": row["method"],
            "resolved_at": row["resolved_at"], "detail": json.loads(row["detail"] or "null")}


def _podcast_row(conn: sqlite3.Connection, podcast_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT id, title, publisher, rss_url, apple_podcasts_id FROM podcasts WHERE id = ?",
                        (podcast_id,)).fetchone()


def _by_apple(conn: sqlite3.Connection, apple_id: str) -> int | None:
    row = conn.execute("SELECT id FROM podcasts WHERE podchaser_id = ? OR apple_podcasts_id = ? "
                       "ORDER BY id LIMIT 1", (f"apple_{apple_id}", apple_id)).fetchone()
    return row["id"] if row else None


def _by_feed(conn: sqlite3.Connection, url: str) -> tuple[int | None, str | None]:
    """The podcast reading ``url`` now, else one that read it before."""
    row = conn.execute("SELECT id FROM podcasts WHERE rss_url = ? ORDER BY id LIMIT 1", (url,)).fetchone()
    if row:
        return row["id"], "rss_url"
    row = conn.execute("SELECT podcast_id FROM podcast_feeds WHERE url = ? ORDER BY podcast_id LIMIT 1",
                       (url,)).fetchone()
    if row:
        return row["podcast_id"], "podcast_feeds"
    return None, None


def _fill_empty_feed(conn: sqlite3.Connection, podcast_id: int, url: str | None) -> bool:
    """Record ``url`` for the podcast; make it ``rss_url`` only if that is empty
    and no other podcast reads it. Returns whether ``rss_url`` was filled."""
    if not url:
        return False
    db.record_feed_url(conn, podcast_id, url, METHOD)
    holder = conn.execute("SELECT id FROM podcasts WHERE rss_url = ? AND id != ? LIMIT 1",
                          (url, podcast_id)).fetchone()
    if holder is not None:
        return False
    cur = conn.execute("UPDATE podcasts SET rss_url = ? WHERE id = ? AND (rss_url IS NULL OR rss_url = '')",
                       (url, podcast_id))
    return cur.rowcount > 0


def _target_apple(config: Config, conn: sqlite3.Connection, entity: str, apple_id: str,
                  detail: dict) -> tuple[int, bool]:
    if not apple_id.isdigit():
        raise ValueError(f"--apple-id must be numeric, got {apple_id!r}")
    listing = lookup_many(make_session(), [apple_id], batch_size=config.resolve.lookup_batch_size,
                          delay=config.resolve.lookup_delay_seconds).get(apple_id)
    feed = (listing or {}).get("feedUrl")
    detail["itunes_lookup"] = ({"listed": True, "title": listing.get("collectionName"),
                                "publisher": listing.get("artistName"), "feed": feed}
                               if listing else {"listed": False})
    podcast_id = _by_apple(conn, apple_id)
    if podcast_id is None and feed:
        podcast_id, how = _by_feed(conn, feed)
        if podcast_id is not None:
            detail["existing_podcast_by_feed"] = {"podcast_id": podcast_id, "via": how}
    created = False
    if podcast_id is None:
        if listing is None:
            raise ValueError(f"Apple does not list podcast {apple_id} and the catalog does not hold it; "
                             f"link it with --feed-url instead")
        podcast_id = db.upsert_podcast(conn, _to_record(
            {"id": apple_id, "name": listing.get("collectionName"),
             "artistName": listing.get("artistName")}, listing))
        created = True
        if feed:
            db.record_feed_url(conn, podcast_id, feed, METHOD)
    elif feed:
        detail["rss_url_filled"] = _fill_empty_feed(conn, podcast_id, feed)
    db.record_podcast_source(conn, podcast_id, db.SourceKind.MANUAL, entity,
                             {"apple_id": apple_id, "note": detail["note"]})
    return podcast_id, created


def _own_feedless_podcast(conn: sqlite3.Connection, entity: str) -> int | None:
    """For 'apple:<id>', the catalog podcast carrying that Apple id, if it has no feed."""
    kind, _, value = entity.partition(":")
    if kind != "apple":
        return None
    podcast_id = _by_apple(conn, value)
    row = _podcast_row(conn, podcast_id) if podcast_id is not None else None
    return podcast_id if row is not None and not row["rss_url"] else None


def _target_feed(conn: sqlite3.Connection, entity: str, url: str, title: str | None,
                 publisher: str | None, detail: dict) -> tuple[int, bool]:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"--feed-url must be an http(s) URL, got {url!r}")
    podcast_id, how = _by_feed(conn, url)
    own = _own_feedless_podcast(conn, entity)
    created = False
    if podcast_id is not None:
        detail["existing_podcast_by_feed"] = {"podcast_id": podcast_id, "via": how}
        detail["rss_url_filled"] = _fill_empty_feed(conn, podcast_id, url)
    elif own is not None:
        # The entity's own Apple id is in the catalog without a feed: give it this one.
        podcast_id = own
        detail["feedless_podcast_for_apple_id"] = own
        detail["rss_url_filled"] = _fill_empty_feed(conn, podcast_id, url)
    else:
        if not title:
            raise ValueError("--title is required when --feed-url creates a new podcast")
        podcast_id = db.upsert_podcast(conn, PodcastRecord(
            source_id=feed_source_id(url), title=title, publisher=publisher, rss_url=url,
            extra={"source": METHOD, "entity": entity}))
        db.record_feed_url(conn, podcast_id, url, METHOD)
        created = True
    db.record_podcast_source(conn, podcast_id, db.SourceKind.MANUAL, entity,
                             {"feed_url": url, "note": detail["note"]})
    return podcast_id, created


def run(config: Config, conn: sqlite3.Connection, entity: str, podcast_id: int | None = None,
        apple_id: str | None = None, feed_url: str | None = None, unresolvable: bool = False,
        note: str = "", title: str | None = None, publisher: str | None = None) -> dict:
    kind, _, value = entity.partition(":")
    if kind not in ENTITY_KINDS or not value:
        raise ValueError(f"Entity must be 'apple:<id>' or 'title:<key>', got {entity!r}")
    targets = [podcast_id is not None, apple_id is not None, feed_url is not None, bool(unresolvable)]
    if sum(targets) != 1:
        raise ValueError("Give exactly one of podcast_id, apple_id, feed_url, unresolvable")
    if not (note or "").strip():
        raise ValueError("A manual link needs a note with its evidence")
    if (title or publisher) and feed_url is None:
        raise ValueError("--title/--publisher only apply to --feed-url")

    previous = _previous(conn, entity)
    detail = {"note": note.strip(), "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "previous": previous}
    created = False
    if podcast_id is not None:
        if _podcast_row(conn, podcast_id) is None:
            raise ValueError(f"No podcast {podcast_id} in the catalog")
        detail["target"] = {"podcast_id": podcast_id}
        db.record_podcast_source(conn, podcast_id, db.SourceKind.MANUAL, entity, {"note": detail["note"]})
    elif apple_id is not None:
        detail["target"] = {"apple_id": apple_id}
        podcast_id, created = _target_apple(config, conn, entity, apple_id, detail)
    elif feed_url is not None:
        detail["target"] = {"feed_url": feed_url, "title": title, "publisher": publisher}
        podcast_id, created = _target_feed(conn, entity, feed_url, title, publisher, detail)
    else:
        detail["target"] = {"unresolvable": True}

    db.link_entity(conn, entity, podcast_id, METHOD, detail)
    members = conn.execute("UPDATE study_members SET podcast_id = ? WHERE entity = ?",
                           (podcast_id, entity)).rowcount
    conn.commit()

    row = _podcast_row(conn, podcast_id) if podcast_id is not None else None
    logger.info(f"{entity} -> {podcast_id} (manual{', created' if created else ''}); "
                f"was {previous['podcast_id'] if previous else None}")
    return {
        "entity": entity,
        "podcast_id": podcast_id,
        "created": created,
        "podcast": dict(row) if row else None,
        "previous": ({"podcast_id": previous["podcast_id"], "method": previous["method"]}
                     if previous else None),
        "study_members_updated": members,
        "detail": {k: v for k, v in detail.items() if k != "previous"},
        "next": "run `study refresh` for the studies that contain this entity, then `discover`",
    }
