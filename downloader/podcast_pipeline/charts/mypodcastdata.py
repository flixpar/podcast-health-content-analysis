"""``import-mypodcastdata``: backfill Apple charts from My Podcast Data.

My Podcast Data (mypodcastdata.com) is an independent site that records
Apple's charts daily: the top 100 of every Apple genre, from 2024-09-01, with
Apple podcast ids. The website sits behind a Cloudflare challenge; its JSON API
does not::

    https://api.mypodcastdata.com/api/applerankers/shows
        ?country=us&category=<Apple genre id>&datestring=DD/MM/YYYY

It fills the gap between Chartable's shutdown (2024-12) and our live capture
(2026-10), where the archive holds only Apple's 24-deep page. Checked on
2026-10-09: a chart dated D is Apple's chart at about 00:00-02:00 UTC on D. It
matches the legacy iTunes RSS 100/100 rank for rank, and Apple's page top 24
exactly on 86% of days we captured that page before 03:00 UTC. Later captures
differ by ordinary intraday movement.

Each (genre, day) becomes one ``origin = 'mirror_api'`` snapshot from source
``mypodcastdata``, with ``captured_on`` the chart's date and ``captured_at``
NULL (MPD does not say when it fetched). Raw responses are kept under
``config.chart_capture_dir/mypodcastdata/<genre id>/<YYYY-MM-DD>.json`` and
never refetched, so a re-run only asks for days it does not have. Days the API
answers with no rows (gaps in MPD's record, or a day it has not published yet)
are not saved and get no snapshot. A chart identical to the previous day's is
a stale copy: it is imported with ``trusted = 0``.

The import is idempotent: each run replaces this source's snapshots for the
days it covers. It does not add podcasts to the catalog. A day whose request
fails (network error, or a response that is not a chart) is recorded and
skipped; the rest are still imported, and the command raises at the end.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from podcast_pipeline.charts import keys
from podcast_pipeline.charts.capture import ChartCaptureError, ChartSourceError, Entry, complete_to
from podcast_pipeline.config import Config
from podcast_pipeline.http import make_session

logger = logging.getLogger(__name__)

SOURCE = "mypodcastdata"
ORIGIN = "mirror_api"
API_URL = "https://api.mypodcastdata.com/api/applerankers/shows"
FIRST_DAY = date(2024, 9, 1)          # earliest date the API returns

# Apple genre id -> chart genre slug, matching apple_charts_page's chart ids.
GENRES = {"26": "all", "1512": "health-fitness"}

STALE_NOTE = "identical to the previous day's chart: stale copy"


def chart_for(country: str, genre_id: str) -> str:
    if genre_id not in GENRES:
        raise ValueError(f"unknown genre id {genre_id!r}; known: {sorted(GENRES)}")
    return keys.chart_id("apple", country.lower(), "podcast", GENRES[genre_id])


def raw_path(config: Config, genre_id: str, day: date) -> Path:
    return config.chart_capture_dir / SOURCE / genre_id / f"{day.isoformat()}.json"


def fetch_day(session: requests.Session, country: str, genre_id: str, day: date) -> bytes:
    response = session.get(API_URL, timeout=30, params={
        "country": country, "category": genre_id, "datestring": day.strftime("%d/%m/%Y")})
    response.raise_for_status()
    return response.content


def parse(body: bytes) -> list[Entry]:
    try:
        rows = json.loads(body)
    except ValueError as e:
        raise ChartSourceError(f"not JSON: {e}") from e
    if not isinstance(rows, list):
        raise ChartSourceError(f"expected a list of chart rows, got {type(rows).__name__}")
    entries = []
    for r in rows:
        try:
            rank, apple_id = int(r["rank"]), str(r["key"])
        except (KeyError, TypeError, ValueError) as e:
            raise ChartSourceError(f"bad chart row {str(r)[:200]}") from e
        if not apple_id.isdigit():
            raise ChartSourceError(f"rank {rank}: Apple id {apple_id!r} is not numeric")
        slug = r.get("slug")
        entries.append(Entry(rank, r.get("name"), r.get("artist"), apple_id=apple_id,
                             source_entity_id=slug,
                             entity_url=f"https://www.mypodcastdata.com/podcast/show/{slug}"
                             if slug else None))
    return entries


def fetch_missing(config: Config, session: requests.Session, country: str, genre_id: str,
                  start: date, end: date) -> dict:
    """Save the raw response for every day in [start, end] not already on disk."""
    fetched, empty, failed = 0, [], {}
    day = start
    while day <= end:
        path = raw_path(config, genre_id, day)
        if not path.exists():
            try:
                body = fetch_day(session, country, genre_id, day)
                rows = parse(body)
            except (requests.RequestException, ChartSourceError) as e:
                logger.warning(f"{SOURCE} {genre_id} {day}: {e}")
                failed[day.isoformat()] = str(e)
            else:
                if rows:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(body)
                    fetched += 1
                else:
                    empty.append(day.isoformat())
            time.sleep(config.charts.mypodcastdata_delay_seconds)
        day += timedelta(days=1)
    return {"fetched": fetched, "empty": empty, "failed": failed}


def import_days(config: Config, conn: sqlite3.Connection, country: str, genre_id: str,
                start: date, end: date) -> dict:
    """Replace this source's snapshots of the chart for [start, end] from the raw files."""
    chart = chart_for(country, genre_id)
    days = []
    day = start
    while day <= end:
        path = raw_path(config, genre_id, day)
        if path.exists():
            days.append((day, path, parse(path.read_bytes())))
        day += timedelta(days=1)

    with conn:
        old = conn.execute("""
            SELECT id FROM chart_snapshots
            WHERE source = ? AND chart = ? AND captured_on BETWEEN ? AND ?
        """, (SOURCE, chart, start.isoformat(), end.isoformat())).fetchall()
        conn.executemany("DELETE FROM chart_entries WHERE snapshot_id = ?", old)
        conn.executemany("DELETE FROM chart_snapshots WHERE id = ?", old)
        stale, previous = [], _previous_chart(config, genre_id, start)
        for day, path, entries in days:
            ranking = [(e.rank, e.apple_id) for e in entries]
            note = STALE_NOTE if ranking == previous else None
            if note:
                stale.append(day.isoformat())
            previous = ranking
            ranks = [e.rank for e in entries]
            cur = conn.execute("""
                INSERT INTO chart_snapshots (source, chart, captured_on, captured_at, origin,
                                             depth, n_entries, complete_to, trusted, raw_path, note)
                VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
            """, (SOURCE, chart, day.isoformat(), ORIGIN, max(ranks), len(entries),
                  complete_to(ranks), 0 if note else 1,
                  str(path.relative_to(config.data_path)), note))
            conn.executemany("""
                INSERT INTO chart_entries (snapshot_id, rank, name, publisher, title_key,
                                           apple_id, source_entity_id, entity_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [(cur.lastrowid, e.rank, e.name, e.publisher, keys.title_key(e.name),
                   e.apple_id, e.source_entity_id, e.entity_url) for e in entries])
    covered = {d for d, _, _ in days}
    missing = [(start + timedelta(n)).isoformat() for n in range((end - start).days + 1)
               if start + timedelta(n) not in covered]
    short = [d.isoformat() for d, _, e in days if complete_to([x.rank for x in e]) < 100]
    return {"chart": chart, "replaced": len(old), "snapshots": len(days),
            "entries": sum(len(e) for _, _, e in days), "stale": stale,
            "missing_days": missing, "incomplete_days": short}


def _previous_chart(config: Config, genre_id: str, day: date) -> list | None:
    path = raw_path(config, genre_id, day - timedelta(days=1))
    if not path.exists():
        return None
    return [(e.rank, e.apple_id) for e in parse(path.read_bytes())]


def run(config: Config, conn: sqlite3.Connection, genres: list[str] | None = None,
        start: date | None = None, end: date | None = None, fetch: bool = True,
        country: str = "us") -> dict:
    genres = genres or config.charts.mypodcastdata_genres
    start = max(start or FIRST_DAY, FIRST_DAY)
    end = end or date.today()
    if end < start:
        raise ValueError(f"end {end} is before start {start}")
    for genre_id in genres:
        chart_for(country, genre_id)          # reject unknown genres before any fetching
    session = make_session() if fetch else None
    result = {}
    for genre_id in genres:
        fetched = (fetch_missing(config, session, country, genre_id, start, end) if fetch
                   else {"fetched": 0, "empty": [], "failed": {}})
        imported = import_days(config, conn, country, genre_id, start, end)
        logger.info(f"{imported['chart']}: {imported['snapshots']} days imported "
                    f"({fetched['fetched']} fetched), {len(imported['missing_days'])} missing")
        result[genre_id] = {**fetched, **imported}
    failed = {g: r["failed"] for g, r in result.items() if r["failed"]}
    if failed:
        raise ChartCaptureError(f"{SOURCE}: requests failed for {sum(map(len, failed.values()))} "
                                f"day(s); the rest were imported: {json.dumps(failed, indent=2)}")
    return result
