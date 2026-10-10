"""``import-archived-pages``: Apple chart days from archived chart-tracker pages.

Two sites published Apple's US overall chart on public pages that the Wayback
Machine captured, outside the canonical chart archive
(``analysis/chart_archive``). They were found on 2026-10-10 while looking for
top-100 days in 2019-2024, which the archive covers only thinly.

* ``podcharts`` -- podcharts.co, a daily tracker later bought by Podchaser.
  ``/charts/us/<YYYY-MM-DD>[/allcategories]`` lists the day's top 200 with
  Apple ids. Logged-out visitors could see only the last week, so captures of
  older dates are a login page and are rejected. The chart date comes from the
  URL and must agree with the page's day picker. Spot checks against other
  sources:

  | Day | Compared with | Result |
  |---|---|---|
  | 2024-09-19 | My Podcast Data | 100/100, rank for rank |
  | 2020-11, 2021-10, 2022-08 | Chartable | 92-95/100 |

* ``podcast_insights`` -- podcastinsights.com/top-us-podcasts/ embeds Apple's
  top-100 feed under an "Updated <RFC 2822 time>" stamp (from 2021-10). The
  stamp is when the feed was read, and it gives the chart date and time. The
  page was cached for days, so several captures can share one stamp. Pages
  without a stamp are rejected, because their age is unknown. Spot checks:

  | Day | Compared with | Result |
  |---|---|---|
  | 2024-09-01 | My Podcast Data | 100/100, rank for rank |
  | 2022-03-03 | Chartable | 100/100, rank for rank |

Each chart day becomes one snapshot with ``origin = 'wayback'``. Its
``raw_path`` is the cached capture under ``config.wayback_cache_dir``. The
import replaces this source's snapshots, and ``import-chart-archive`` leaves
them alone (``archive_import.STANDALONE_SOURCES``). A capture that cannot be
fetched is recorded and skipped; the command raises at the end if any failed.
"""

from __future__ import annotations

import html
import json
import logging
import re
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from podcast_pipeline.archive.wayback import SnapshotError, WaybackClient, _cache_key
from podcast_pipeline.charts import keys
from podcast_pipeline.charts.capture import ChartCaptureError, ChartSourceError, Entry, complete_to
from podcast_pipeline.config import Config

logger = logging.getLogger(__name__)

ORIGIN = "wayback"
CHART = keys.chart_id("apple", "us", "podcast", "all")
PODCHARTS, PODCAST_INSIGHTS = "podcharts", "podcast_insights"
SOURCES = (PODCHARTS, PODCAST_INSIGHTS)

PODCHARTS_PREFIX = "podcharts.co/charts/us/"
PODCHARTS_URL = re.compile(r"^https?://(?:www\.)?podcharts\.co(?::\d+)?/charts/us/(\d{4}-\d{2}-\d{2})(?:/allcategories)?/?$")
PODCAST_INSIGHTS_URL = "https://www.podcastinsights.com/top-us-podcasts/"
MIN_CAPTURE_BYTES = 3000      # compressed: podcharts' login page is ~4 KB raw, a chart page 100+ KB
MIN_RANKS = 100


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_podcharts(body: bytes, day: str) -> list[Entry]:
    """The overall US chart on a podcharts.co day page; raises ChartSourceError otherwise."""
    page = body.decode("utf-8", "replace")
    if "To access charts older than a week" in page:
        raise ChartSourceError("login page (charts older than a week)")
    if not re.search(r'<option value="us"\s+selected', page):
        raise ChartSourceError("country selector is not US")
    if not re.search(r'<option value="allcategories"\s+selected', page):
        raise ChartSourceError("genre selector is not All Categories")
    picker = re.search(r'<div class="day-picker">\s*<a[^>]*href="/charts/us/(\d{4}-\d{2}-\d{2})', page)
    if not picker:
        raise ChartSourceError("no day picker")
    shown = date.fromisoformat(picker.group(1)) + timedelta(days=1)
    if shown.isoformat() != day:
        raise ChartSourceError(f"page shows {shown}, URL says {day}")
    entries = []
    for block in page.split('<div class="podcast-position">')[1:]:
        rank = re.match(r"\s*(\d+)\s*</div>", block)
        name = re.search(r'<div class="podcast-name" id(?:="(\d*)")?>(.*?)</div>', block, re.S)
        author = re.search(r'<div class="author-name">(.*?)</div>', block, re.S)
        if not (rank and name):
            raise ChartSourceError(f"unparseable row: {block[:200]!r}")
        apple_id = name.group(1) or None           # a few rows carry an empty id
        entries.append(Entry(int(rank.group(1)), _text(name.group(2)) or None,
                             _text(author.group(1)) if author else None, apple_id=apple_id,
                             source_entity_id=apple_id,
                             entity_url=f"https://podcharts.co/graphs/{apple_id}/us/allcategories"
                             if apple_id else None))
    return entries


def parse_podcast_insights(body: bytes) -> tuple[datetime, list[Entry]]:
    """(chart time, entries) from a stamped Podcast Insights page; raises ChartSourceError otherwise."""
    page = body.decode("utf-8", "replace")
    stamp = re.search(r"Updated ([A-Z][a-z]{2}, \d+ [A-Z][a-z]{2} \d{4} [\d:]+ [+-]\d{4})", page)
    if not stamp:
        raise ChartSourceError("no 'Updated' stamp: the chart's date is unknown")
    when = parsedate_to_datetime(stamp.group(1)).astimezone(timezone.utc)
    listing = page[stamp.end():]
    end = listing.find("</ol>")
    if end < 0:
        raise ChartSourceError("no chart list after the stamp")
    entries = []
    for rank, item in enumerate(listing[:end].split("<li")[1:], start=1):
        apple = re.search(r"(?:itunes|podcasts)\.apple\.com/[^\"']*?id(\d+)", item)
        name = re.search(r"Podcast Name:\s*<strong>(.*?)</strong>", item, re.S)
        artist = re.search(r"Network/Artist:\s*(.*?)</p>", item, re.S)
        if not apple:
            raise ChartSourceError(f"rank {rank}: no Apple id")
        entries.append(Entry(rank, _text(name.group(1)) if name else None,
                             _text(artist.group(1)) if artist else None, apple_id=apple.group(1),
                             source_entity_id=apple.group(1), entity_url=None))
    if len({e.apple_id for e in entries}) != len(entries):
        raise ChartSourceError("repeated Apple ids")
    return when, entries


def _usable(entries: list[Entry]) -> bool:
    return complete_to([e.rank for e in entries]) >= MIN_RANKS


def collect(client: WaybackClient, source: str) -> tuple[dict, dict, dict]:
    """({day: (capture, time or None, entries)}, rejected, unfetched) for one source.

    ``rejected`` and ``unfetched`` map a capture to why it was not used. A
    podcharts day's captures are tried oldest first and the first usable one is
    kept; a Podcast Insights stamp keeps its first usable capture.
    """
    days: dict[str, tuple] = {}
    problems: dict[str, str] = {}
    unfetched: dict[str, str] = {}
    if source == PODCHARTS:
        by_day = defaultdict(list)
        for c in client.list_captures(PODCHARTS_PREFIX, prefix=True):
            m = PODCHARTS_URL.match(c.original)
            if m and (c.length is None or c.length >= MIN_CAPTURE_BYTES):
                by_day[m.group(1)].append(c)
        for day, captures in sorted(by_day.items()):
            for c in sorted(captures, key=lambda c: c.timestamp):
                if c.timestamp[:8] < day.replace("-", ""):
                    continue                      # captured before the chart existed: not this day
                try:
                    entries = parse_podcharts(client.fetch_snapshot(c).body, day)
                except SnapshotError as e:
                    unfetched[f"{c.timestamp} {c.original}"] = str(e)
                    continue
                except ChartSourceError as e:
                    problems[f"{c.timestamp} {c.original}"] = str(e)
                    continue
                if _usable(entries):
                    days[day] = (c, None, entries)
                    break
                problems[f"{c.timestamp} {c.original}"] = f"complete to {complete_to([e.rank for e in entries])}"
    elif source == PODCAST_INSIGHTS:
        for c in client.list_captures(PODCAST_INSIGHTS_URL):
            try:
                when, entries = parse_podcast_insights(client.fetch_snapshot(c).body)
            except SnapshotError as e:
                unfetched[f"{c.timestamp} {c.original}"] = str(e)
                continue
            except ChartSourceError as e:
                problems[f"{c.timestamp} {c.original}"] = str(e)
                continue
            day = when.date().isoformat()
            if day not in days and _usable(entries):
                days[day] = (c, when, entries)
    else:
        raise ValueError(f"unknown source {source!r}; known: {SOURCES}")
    return days, problems, unfetched


def import_source(config: Config, conn: sqlite3.Connection, client: WaybackClient, source: str,
                  days: dict) -> dict:
    """Replace ``source``'s snapshots with ``days``."""
    with conn:
        old = conn.execute("SELECT id FROM chart_snapshots WHERE source = ? AND chart = ?",
                           (source, CHART)).fetchall()
        conn.executemany("DELETE FROM chart_entries WHERE snapshot_id = ?", old)
        conn.executemany("DELETE FROM chart_snapshots WHERE id = ?", old)
        for day, (capture, when, entries) in sorted(days.items()):
            ranks = [e.rank for e in entries]
            cache = client.cache_dir / "snapshots" / f"{capture.timestamp}_{_cache_key(capture.original)}.zst"
            cur = conn.execute("""
                INSERT INTO chart_snapshots (source, chart, captured_on, captured_at, origin,
                                             depth, n_entries, complete_to, trusted, raw_path, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (source, CHART, day, when.strftime("%Y-%m-%dT%H:%M:%SZ") if when else None, ORIGIN,
                  max(ranks), len(entries), complete_to(ranks),
                  str(cache.relative_to(config.data_path)),
                  f"wayback {capture.timestamp} {capture.original}"))
            conn.executemany("""
                INSERT INTO chart_entries (snapshot_id, rank, name, publisher, title_key,
                                           apple_id, source_entity_id, entity_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [(cur.lastrowid, e.rank, e.name, e.publisher, keys.title_key(e.name),
                   e.apple_id, e.source_entity_id, e.entity_url) for e in entries])
    return {"replaced": len(old), "snapshots": len(days), "days_by_month": _per_month(days)}


def _per_month(days: dict) -> dict:
    months: dict[str, int] = defaultdict(int)
    for day in days:
        months[day[:7]] += 1
    return dict(sorted(months.items()))


def run(config: Config, conn: sqlite3.Connection, sources: list[str] | None = None) -> dict:
    sources = sources or list(SOURCES)
    for source in sources:
        if source not in SOURCES:
            raise ValueError(f"unknown source {source!r}; known: {SOURCES}")
    client = WaybackClient(config.wayback, config.wayback_cache_dir)
    result, failed = {}, {}
    for source in sources:
        days, rejected, unfetched = collect(client, source)
        imported = import_source(config, conn, client, source, days)
        logger.info(f"{source}: {imported['snapshots']} chart days imported; {len(rejected)} captures "
                    f"rejected, {len(unfetched)} could not be fetched")
        result[source] = {**imported, "rejected": len(rejected), "rejected_reasons": _reasons(rejected),
                          "unfetched": len(unfetched)}
        if unfetched:
            failed[source] = unfetched
    if failed:
        raise ChartCaptureError(f"archived pages: some captures could not be fetched; re-run to retry "
                                f"(fetched pages are cached): {json.dumps(failed, indent=2)[:4000]}")
    return result


def _reasons(problems: dict) -> dict:
    reasons: dict[str, int] = defaultdict(int)
    for problem in problems.values():
        reasons[re.sub(r"\d{4}-\d{2}-\d{2}|\d+", "N", problem)[:80]] += 1
    return dict(sorted(reasons.items(), key=lambda kv: -kv[1]))
