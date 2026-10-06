"""``capture-charts``: record today's live charts. Run daily; a missed day
cannot be recovered (both historical mirrors are dead).

Sources (no authentication):

* ``apple_marketing_tools``: Apple's Marketing Tools feed, the US top 100 with
  Apple ids -> ``apple:<country>:podcast:all``. Cross-validated 100/100 against
  the legacy iTunes RSS and 24/24 against podcasts.apple.com
  (docs/chart-2024-sources.md, the dated source investigation).
* ``spotify_api``: podcastcharts.byspotify.com, the top 200 shows ->
  ``spotify:<country>:podcast:all``. Spotify ids only, no feeds.

Every raw response is kept under ``config.chart_capture_dir/<source>/
<YYYY-MM-DD>THHMMSSZ.json`` (never overwritten), because parsing can be
redone and a missed day cannot. Each source then writes one ``origin = 'live'``
snapshot for the UTC day; capturing again the same day replaces it.

With ``catalog=True``, Apple ids not yet in the catalog are looked up (batched
iTunes lookup) and added, and every podcast seen gets a ``chart_capture``
provenance row. Spotify-only shows are not added: resolving them needs the
throttled iTunes search (see sources/spotify.py); existing podcasts are linked
by ``spotify_id``.

Only per-source problems are recorded and skipped past: a network error
(``requests.RequestException``) or a response that is not the chart we expect
(``ChartSourceError``: bad JSON, unexpected shape, empty chart). The others
still run, and the command raises at the end so a cron job notices. Disk,
database and programming errors propagate at once. Every source is captured
before any catalog work starts, so a catalog failure (e.g. the iTunes lookup
being down) can never cost another source its day.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

from podcast_pipeline import db
from podcast_pipeline.charts import keys
from podcast_pipeline.config import Config
from podcast_pipeline.http import make_session
from podcast_pipeline.sources import apple

logger = logging.getLogger(__name__)


class ChartCaptureError(RuntimeError):
    """At least one live source failed; the others were recorded."""


class ChartSourceError(RuntimeError):
    """A source answered, but not with the chart we expect (shape, JSON, empty)."""


# What counts as "this source is broken today" rather than a bug or a local fault.
SOURCE_FAILURES = (requests.RequestException, ChartSourceError)


@dataclass
class Entry:
    rank: int
    name: str | None
    publisher: str | None
    apple_id: str | None = None
    source_entity_id: str | None = None
    entity_url: str | None = None
    raw: dict = field(default_factory=dict, repr=False)


# --- sources -------------------------------------------------------------------

def fetch_apple_marketing_tools(session: requests.Session, config: Config) -> bytes:
    response = session.get(apple.CHARTS_URL.format(country=config.charts.country), timeout=30)
    response.raise_for_status()
    return response.content


def parse_apple_marketing_tools(body: bytes) -> list[Entry]:
    results = json.loads(body)["feed"]["results"]
    entries = []
    for rank, r in enumerate(results, start=1):
        apple_id = str(r["id"])
        if not apple_id.isdigit():
            raise ChartSourceError(f"rank {rank}: Apple id {apple_id!r} is not numeric")
        entries.append(Entry(rank=rank, name=r.get("name"), publisher=r.get("artistName"),
                             apple_id=apple_id, entity_url=r.get("url"), raw=r))
    return entries


def fetch_spotify_api(session: requests.Session, config: Config) -> bytes:
    response = session.get(config.spotify.chart_url, params={"region": config.charts.country},
                           headers={"Accept": "application/json"}, timeout=30)
    response.raise_for_status()
    return response.content


def parse_spotify_api(body: bytes) -> list[Entry]:
    shows = json.loads(body)
    if not isinstance(shows, list):
        raise ChartSourceError(f"expected a list of shows, got {type(shows).__name__}"
                         f"{' with keys ' + str(sorted(shows)) if isinstance(shows, dict) else ''}")
    entries = []
    for rank, show in enumerate(shows, start=1):
        show_id = keys.bare_spotify_id(show["showUri"])
        entries.append(Entry(rank=rank, name=show.get("showName"),
                             publisher=show.get("showPublisher"), source_entity_id=show_id,
                             entity_url=f"https://open.spotify.com/show/{show_id}", raw=show))
    return entries


SOURCES = {
    "apple_marketing_tools": (fetch_apple_marketing_tools, parse_apple_marketing_tools),
    "spotify_api": (fetch_spotify_api, parse_spotify_api),
}


# --- run -----------------------------------------------------------------------

def run(config: Config, conn: sqlite3.Connection, sources: list[str] | None = None,
        catalog: bool = True) -> dict:
    names = list(sources or config.charts.capture_sources)
    unknown = [n for n in names if n not in SOURCES]
    if unknown:
        raise ValueError(f"unknown chart source(s) {unknown}; known: {sorted(SOURCES)}")
    session = make_session()
    captured: dict[str, dict] = {}
    failed: dict[str, str] = {}
    for name in names:
        try:
            captured[name] = capture_source(config, conn, session, name)
        except SOURCE_FAILURES as e:   # one dead endpoint must not cost the other its day
            conn.rollback()
            logger.exception(f"Capturing {name} failed")
            failed[name] = f"capture: {type(e).__name__}: {e}"
    if catalog:
        for name, snapshot in captured.items():
            try:
                snapshot["catalog"] = update_catalog(config, conn, session, name, snapshot)
                conn.commit()
            except requests.RequestException as e:
                conn.rollback()
                logger.exception(f"Cataloguing {name} failed (the snapshot is kept)")
                failed[name] = f"catalog: {type(e).__name__}: {e}"
    for snap in captured.values():
        snap.pop("_entries", None)
    summary = {"captured": captured, "failed": failed}
    if failed:
        raise ChartCaptureError(f"{len(failed)} of {len(names)} chart source(s) failed: "
                                f"{json.dumps(summary, indent=2)}")
    return summary


def capture_source(config: Config, conn: sqlite3.Connection, session: requests.Session,
                   name: str) -> dict:
    """Fetch, keep the raw body, parse, write the day's snapshot, commit."""
    fetch, parse = SOURCES[name]
    chart = keys.live_chart(name, config.charts.country)
    now = _now()
    body = fetch(session, config)
    raw_path = save_raw(config, name, now, body)
    try:
        entries = parse(body)
    except (ValueError, KeyError, TypeError, AttributeError) as e:   # incl. JSONDecodeError
        raise ChartSourceError(f"{name}: unexpected response ({type(e).__name__}: {e}); "
                               f"raw response kept at {raw_path}") from e
    if not entries:
        raise ChartSourceError(f"{name} returned an empty chart (raw response kept at {raw_path})")
    snapshot = write_snapshot(conn, name, chart, now, entries,
                              str(raw_path.relative_to(config.data_path)))
    conn.commit()
    replaced = " (replaced the day's earlier capture)" if snapshot["replaced"] else ""
    logger.info(f"{name}: {chart} {snapshot['captured_on']} depth {snapshot['depth']}{replaced}")
    return {**snapshot, "_entries": entries}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def save_raw(config: Config, name: str, now: datetime, body: bytes) -> Path:
    path = config.chart_capture_dir / name / f"{now.strftime('%Y-%m-%dT%H%M%SZ')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as f:      # never overwrite a kept response
        f.write(body)
    return path


def complete_to(ranks: list[int]) -> int:
    """Largest N with every rank 1..N present."""
    present, n = set(ranks), 0
    while n + 1 in present:
        n += 1
    return n


def write_snapshot(conn: sqlite3.Connection, source: str, chart: str, now: datetime,
                   entries: list[Entry], raw_path: str) -> dict:
    """Replace today's live snapshot of ``chart`` from ``source``. Does not commit."""
    captured_on = now.strftime("%Y-%m-%d")
    old = conn.execute("""
        SELECT id FROM chart_snapshots
        WHERE source = ? AND chart = ? AND captured_on = ? AND origin = 'live'
    """, (source, chart, captured_on)).fetchone()
    if old is not None:
        conn.execute("DELETE FROM chart_entries WHERE snapshot_id = ?", (old[0],))
        conn.execute("DELETE FROM chart_snapshots WHERE id = ?", (old[0],))
    ranks = [e.rank for e in entries]
    snapshot = {"chart": chart, "captured_on": captured_on,
                "captured_at": now.isoformat(timespec="seconds"), "depth": max(ranks),
                "n_entries": len(entries), "complete_to": complete_to(ranks),
                "raw_path": raw_path, "replaced": old is not None}
    cur = conn.execute("""
        INSERT INTO chart_snapshots (source, chart, captured_on, captured_at, origin, depth,
                                     n_entries, complete_to, trusted, raw_path)
        VALUES (?, ?, ?, ?, 'live', ?, ?, ?, 1, ?)
    """, (source, chart, captured_on, snapshot["captured_at"], snapshot["depth"],
          snapshot["n_entries"], snapshot["complete_to"], raw_path))
    conn.executemany("""
        INSERT INTO chart_entries (snapshot_id, rank, name, publisher, title_key, apple_id,
                                   source_entity_id, entity_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [(cur.lastrowid, e.rank, e.name, e.publisher, keys.title_key(e.name), e.apple_id,
           e.source_entity_id, e.entity_url) for e in entries])
    return snapshot


# --- catalog -------------------------------------------------------------------

def update_catalog(config: Config, conn: sqlite3.Connection, session: requests.Session,
                   name: str, snapshot: dict) -> dict:
    entries: list[Entry] = snapshot["_entries"]
    chart, day = snapshot["chart"], snapshot["captured_on"]
    if name == "apple_marketing_tools":
        return _catalog_apple(config, conn, session, chart, day, entries)
    if name == "spotify_api":
        return _catalog_spotify(conn, chart, day, entries)
    raise ValueError(f"no catalog rule for {name}")


def _catalog_apple(config: Config, conn: sqlite3.Connection, session: requests.Session,
                   chart: str, day: str, entries: list[Entry]) -> dict:
    manual_unresolved = {r[0] for r in conn.execute(
        "SELECT entity FROM entity_links WHERE method = 'manual' AND podcast_id IS NULL")}
    blocked = {e.apple_id for e in entries if f"apple:{e.apple_id}" in manual_unresolved}
    known = {e.apple_id: pid for e in entries
             if (pid := db.podcast_for_entity(conn, f"apple:{e.apple_id}")) is not None}
    new = [e for e in entries if e.apple_id not in known and e.apple_id not in blocked]
    details = (apple.lookup_many(session, [e.apple_id for e in new],
                                 batch_size=config.resolve.lookup_batch_size,
                                 delay=config.resolve.lookup_delay_seconds) if new else {})
    no_lookup = []
    added = 0
    for e in new:
        record = apple._to_record(e.raw, details.get(e.apple_id))
        holder = conn.execute("""
            SELECT id FROM podcasts WHERE rss_url = ?
            UNION SELECT podcast_id FROM podcast_feeds WHERE url = ?
            ORDER BY 1 LIMIT 1
        """, (record.rss_url, record.rss_url)).fetchone() if record.rss_url else None
        if holder is not None:
            podcast_id = holder[0]
            db.link_entity(conn, f"apple:{e.apple_id}", podcast_id, "itunes_lookup",
                           {"existing_podcast_by_feed": podcast_id, "feed": record.rss_url,
                            "chart": chart, "captured_on": day})
        else:
            podcast_id = db.upsert_podcast(conn, record)
            added += 1
        if record.rss_url:
            db.record_feed_url(conn, podcast_id, record.rss_url, "itunes_lookup")
        else:
            no_lookup.append(e.apple_id)
        known[e.apple_id] = podcast_id
    if no_lookup:
        logger.warning(f"{len(no_lookup)} charting Apple ids have no feed in the iTunes lookup "
                       f"(added from the chart alone): {no_lookup}")
    for e in entries:
        if e.apple_id in blocked:
            continue  # Manual "unresolvable" decisions are final, as in resolve.
        db.record_podcast_source(conn, known[e.apple_id], db.SourceKind.CHART_CAPTURE, chart,
                                 {"rank": e.rank, "captured_on": day})
    return {"seen": len(entries), "added": added, "already_known": len(entries) - added - len(blocked),
            "skipped_manual": len(blocked),
            "added_without_feed": len(no_lookup)}


def _catalog_spotify(conn: sqlite3.Connection, chart: str, day: str,
                     entries: list[Entry]) -> dict:
    linked = 0
    for e in entries:
        row = conn.execute("SELECT id FROM podcasts WHERE spotify_id = ? ORDER BY id LIMIT 1",
                           (e.source_entity_id,)).fetchone()
        if row is None:
            continue
        db.record_podcast_source(conn, row[0], db.SourceKind.CHART_CAPTURE, chart,
                                 {"rank": e.rank, "captured_on": day})
        linked += 1
    return {"seen": len(entries), "linked": linked, "not_in_catalog": len(entries) - linked}
