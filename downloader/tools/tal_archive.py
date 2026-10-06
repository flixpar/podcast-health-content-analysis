#!/usr/bin/env python3
"""This American Life: episodes for a study's TAL windows, as JSONL for ``import-episodes``.

TAL's live feed lists only ~15 items, and its 2016-2019 enclosures
(``podcast.thisamericanlife.org``, feedburner redirects) are dead: the host
answers with a certificate for another name. Two sources together fill the
study's windows:

1. **What went out, and when** -- Wayback copies of the podcast feed. Until
   2018 the feed was ``feed.thisamericanlife.org/talpodcast`` (feedburner,
   4 items); from 2018 ``www.thisamericanlife.org/podcast/rss.xml`` (4, later
   10 items). TAL republishes old episodes as new podcast items (reruns), so a
   feed item's ``pubDate`` is the date that episode went out *as a podcast
   episode*, which is what the study's windows count. The item's guid is kept,
   so items already in the catalog match by guid.
   Captures are taken one per 7-day bucket from each window's start to 35
   days past its end; every window's coverage (the union of each capture's
   [oldest item, capture day]) is reported, so a gap the archive cannot fill
   is visible rather than silent.
2. **Audio that still plays** -- the item's own enclosure if a 64 KB range
   GET returns audio (the 2020+ Simplecast URLs mostly do), else the episode's
   page on thisamericanlife.org, whose player data names an MP3 under
   ``/sites/default/files/audio/<n>/``. The page also gives the original
   (radio) air date and the canonical title, both kept as evidence. A page is
   rejected if its episode number differs from the feed item's.

The site is fetched with its robots.txt crawl delay (10 s) and every page is
cached under ``--cache``, so a re-run costs nothing. Reads the database
read-only; writes only the JSONL, the page cache and the shared Wayback cache.

Usage (from downloader/):
    ../.venv/bin/python tools/tal_archive.py --out /path/tal.jsonl --cache /path/tal-cache
    $P import-episodes /path/tal.jsonl --source publisher_site --podcast-id 13 --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import re
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from podcast_pipeline.archive.wayback import Capture, SnapshotError, WaybackClient  # noqa: E402
from podcast_pipeline.audio.download import looks_like_audio  # noqa: E402
from podcast_pipeline.config import Config  # noqa: E402
from podcast_pipeline.http import make_session  # noqa: E402
from podcast_pipeline.pipeline.import_episodes import title_key  # noqa: E402
from podcast_pipeline.rss import FeedError, parse_feed  # noqa: E402

logger = logging.getLogger("tal_archive")

SITE = "https://www.thisamericanlife.org"
FEED_URLS = ("feed.thisamericanlife.org/talpodcast",
             "https://www.thisamericanlife.org/podcast/rss.xml")
USER_AGENT = "podcast-misinfo-research/1.0 (academic study of podcast content; flixpar@gmail.com)"
SITE_DELAY_SECONDS = 10.0       # robots.txt: Crawl-delay: 10
AUDIO_DELAY_SECONDS = 1.0
WAYBACK_DELAY_SECONDS = 1.0
CAPTURE_BUCKET_DAYS = 7
CAPTURE_TAIL_DAYS = 35
SAME_AIRING_SECONDS = 36 * 3600
RANGE_BYTES = 65536

NUMBER = re.compile(r"^\s*#?(\d+)\s*:\s*(.*)$")


def episode_number(title: str) -> int | None:
    m = NUMBER.match(title)
    return int(m.group(1)) if m else None


# --- inputs ----------------------------------------------------------------------

def study_windows(db_path: Path, study: str, podcast_id: int) -> list[tuple[str, str, str]]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute("""
            SELECT w.label, w.start_date, w.end_date
            FROM study_windows w JOIN study_members m ON m.study = w.study AND m.entity = w.entity
            WHERE w.study = ? AND m.podcast_id = ? ORDER BY w.start_date
        """, (study, podcast_id)).fetchall()
    finally:
        conn.close()


def catalog_episodes(db_path: Path, podcast_id: int) -> list[dict]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("""
            SELECT id, episode_guid, title, published_date, audio_url, status, audio_file_path,
                   transcript_file_path
            FROM episodes WHERE podcast_id = ?
        """, (podcast_id,))]
    finally:
        conn.close()


# --- Wayback feed captures -------------------------------------------------------

def pick_captures(captures: list[Capture], windows) -> list[Capture]:
    """One capture per 7-day bucket from each window's start to 35 days past its end."""
    picked: dict[tuple[str, int], Capture] = {}
    for _label, start, end in windows:
        lo = date.fromisoformat(start)
        hi = date.fromisoformat(end) + timedelta(days=CAPTURE_TAIL_DAYS)
        for c in captures:
            day = date.fromisoformat(c.day)
            if lo <= day < hi:
                key = (c.original.split("://")[-1].split("/")[0], (day - date(2000, 1, 1)).days
                       // CAPTURE_BUCKET_DAYS)
                if key not in picked or c.timestamp < picked[key].timestamp:
                    picked[key] = c
    return sorted(picked.values(), key=lambda c: c.timestamp)


def feed_items(client: WaybackClient, captures: list[Capture]) -> tuple[dict, list, list]:
    """Items by (guid, day) (from the earliest capture listing each), coverage spans, failures."""
    items: dict[str, dict] = {}
    spans: list[tuple[str, str]] = []
    failures: list[str] = []
    seen_digests: set[str] = set()
    for i, cap in enumerate(captures):
        if cap.digest in seen_digests:
            continue
        seen_digests.add(cap.digest)
        if not client._snapshot_cache_path(cap).exists():
            time.sleep(WAYBACK_DELAY_SECONDS)
        try:
            snap = client.fetch_snapshot(cap)
            episodes = parse_feed(snap.body, source=snap.served_url)
        except (SnapshotError, FeedError) as e:
            failures.append(str(e))
            continue
        links = {e.get("id") or e.get("guid"): e.get("link")
                 for e in feedparser.parse(snap.body).entries}
        dated = [e for e in episodes if e.published_date]
        if not dated:
            failures.append(f"{snap.served_url}: no dated items")
            continue
        spans.append((min(e.published_date[:10] for e in dated), cap.day))
        for e in dated:
            if e.published_date[:10] > cap.day:
                failures.append(f"{snap.served_url}: item {e.guid} dated after its capture")
                continue
            # Keyed by guid and day: from ~2019 a rerun reuses its first airing's guid.
            # In Nov 2016 the guids switched from http:// to https://.
            key = (e.guid.replace("http://", "https://", 1), e.published_date[:10])
            if key not in items:
                items[key] = {"episode": e, "link": links.get(e.guid), "capture": snap.served_url}
        if (i + 1) % 25 == 0:
            logger.info(f"captures: {i + 1}/{len(captures)}, {len(items)} items")
    return items, spans, failures


def uncovered(start: str, end: str, spans: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Parts of [start, end) no capture's [oldest item, capture day] reaches."""
    gaps, cursor = [], start
    for lo, hi in sorted(spans):
        if hi < cursor:
            continue
        if lo > cursor:
            gaps.append((cursor, min(lo, end)))
        cursor = max(cursor, (date.fromisoformat(hi) + timedelta(days=1)).isoformat())
        if cursor >= end:
            break
    if cursor < end:
        gaps.append((cursor, end))
    return [g for g in gaps if g[0] < g[1]]


# --- network checks ----------------------------------------------------------------

class Fetcher:
    def __init__(self, cache: Path, site_delay: float):
        self.session = make_session(pool_size=1)
        self.session.headers["User-Agent"] = USER_AGENT
        # A dead enclosure fails the same way every time; one attempt is enough.
        self.probe_session = make_session(pool_size=1, retries=0)
        self.probe_session.headers["User-Agent"] = USER_AGENT
        self.cache = cache
        self.site_delay = site_delay
        self.last: dict[str, float] = {}
        self.probes: dict[str, dict] = {}
        probe_cache = cache / "probes.json"
        if probe_cache.exists():
            self.probes = json.loads(probe_cache.read_text())

    def _pace(self, url: str, delay: float) -> None:
        host = urlparse(url).netloc
        wait = self.last.get(host, 0) + delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last[host] = time.monotonic()

    def probe_audio(self, url: str) -> dict:
        """First 64 KB of ``url``: whether it is audio, and where it ended up."""
        if url in self.probes:
            return self.probes[url]
        self._pace(url, AUDIO_DELAY_SECONDS)
        try:
            r = self.probe_session.get(url, headers={"Range": f"bytes=0-{RANGE_BYTES - 1}"},
                                 timeout=60, stream=True)
            head = r.raw.read(RANGE_BYTES, decode_content=True)
            r.close()
            total = (r.headers.get("Content-Range") or "").rpartition("/")[2]
            result = {"ok": r.status_code in (200, 206)
                      and looks_like_audio(head, r.headers.get("Content-Type", "")),
                      "status": r.status_code, "final_url": r.url,
                      "content_type": r.headers.get("Content-Type"),
                      "total_bytes": int(total) if total.isdigit() else None}
        except Exception as e:  # noqa: BLE001 -- a probe failure is a dead URL, recorded
            result = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
        self.probes[url] = result
        (self.cache / "probes.json").write_text(json.dumps(self.probes, indent=0))
        return result

    def page(self, url: str) -> str | None:
        path = self.cache / "pages" / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".html")
        if path.exists():
            text = path.read_text()
            return text or None
        self._pace(url, self.site_delay)
        r = self.session.get(url, timeout=60)
        path.parent.mkdir(parents=True, exist_ok=True)
        if r.status_code == 404:
            path.write_text("")
            return None
        r.raise_for_status()
        path.write_text(r.text)
        return r.text


def page_urls(link: str | None, number: int) -> list[str]:
    """Candidate pages for the episode on the site, from the feed item's link.

    The site has since dropped non-ASCII characters from slugs
    (``didn%E2%80%99t`` -> ``didnt``) and split some episodes into parts
    (``.../the-problem-we-all-live-with-part-one``).
    """
    if not link:
        return []
    slug = urlparse(link).path.rstrip("/").rsplit("/", 1)[-1]
    if not slug or slug.isdigit():
        return []
    ascii_slug = re.sub(r"%[0-9A-Fa-f]{2}", "", slug)
    slugs = dict.fromkeys([slug, ascii_slug, f"{ascii_slug}-part-one"])
    return [f"{SITE}/{number}/{s}" for s in slugs]


def parse_page(text: str) -> dict:
    """Episode number, title, original air date and audio URL from an episode page."""
    out: dict = {}
    m = re.search(r'<script id="playlist-data" type="application/json">(.*?)</script>', text, re.S)
    if m:
        data = json.loads(m.group(1))
        out["audio"] = data.get("audio")
        out["number"] = int(data["episode"]) if str(data.get("episode", "")).isdigit() else None
        out["title"] = html.unescape(data.get("title") or "").strip()
        out["site_guid"] = data.get("guid")
    m = re.search(r'field-name-field-radio-air-date.*?<span\s+class="date-display-single">([^<]+)</span>',
                  text, re.S)
    if m:
        out["original_air_date"] = datetime.strptime(m.group(1).strip(), "%B %d, %Y").date().isoformat()
    m = re.search(r'<link rel="canonical" href="([^"]+)"', text)
    if m:
        out["canonical"] = m.group(1)
    return out


# --- assembly ------------------------------------------------------------------------

def build(args) -> dict:
    config = Config.load(args.config) if args.config else Config.load()
    db_path = config.db_path
    windows = study_windows(db_path, args.study, args.podcast_id)
    if not windows:
        raise SystemExit(f"no windows for podcast {args.podcast_id} in {args.study}")
    if args.windows:
        wanted = set(args.windows.split(","))
        windows = [w for w in windows if w[0] in wanted]
    logger.info(f"{len(windows)} windows")

    client = WaybackClient(config.wayback, config.wayback_cache_dir)
    captures = [c for url in FEED_URLS for c in client.list_captures(url)]
    picked = pick_captures(captures, windows)
    logger.info(f"{len(captures)} captures listed, {len(picked)} picked")
    items, spans, failures = feed_items(client, picked)

    in_window = {}
    last_day: dict[str, str] = {}
    for (guid, day), item in sorted(items.items(), key=lambda kv: kv[0][1]):
        if guid in last_day and (date.fromisoformat(day)
                                 - date.fromisoformat(last_day[guid])).days <= 7:
            continue    # the same item, its pubDate retouched between captures
        last_day[guid] = day
        label = next((lab for lab, s, e in windows if s <= day < e), None)
        if label:
            in_window[(guid, day)] = {**item, "window": label}
    # The same item can sit in both feeds under one guid; distinct guids for one
    # (day, title) would be a re-issue, which import-episodes dedupes anyway.

    existing = catalog_episodes(db_path, args.podcast_id)
    by_guid = {e["episode_guid"]: e for e in existing}
    by_key = {(e["published_date"][:10], title_key(e["title"])): e
              for e in existing if e["published_date"]}

    fetcher = Fetcher(Path(args.cache), args.site_delay)
    rows, reruns, skipped = [], [], []
    emitted: dict[str, str] = {}    # guid -> published_date of the row that took it
    airings: dict[str, list[datetime]] = {}     # title key -> airings known or emitted
    for e in existing:
        if e["published_date"]:
            airings.setdefault(title_key(e["title"]), []).append(
                datetime.fromisoformat(e["published_date"]))
    for (guid, _day), item in sorted(in_window.items(),
                                     key=lambda kv: kv[1]["episode"].published_date):
        ep = item["episode"]
        title = re.sub(r"\s+", " ", ep.title).strip()
        number = episode_number(title)
        match = by_guid.get(guid) or by_key.get((ep.published_date[:10], title_key(title)))
        aired = datetime.fromisoformat(ep.published_date)
        if match is None and any(abs((aired - t).total_seconds()) <= SAME_AIRING_SECONDS
                                 for t in airings.get(title_key(title), [])):
            # During the 2018 feed move one airing was listed in both feeds,
            # under different guids and an hour apart (across UTC midnight).
            skipped.append({"guid": guid, "title": title, "window": item["window"],
                            "reason": "same airing as another feed's item within 36 h"})
            continue
        airings.setdefault(title_key(title), []).append(aired)
        rerun_of = None
        if match and abs((date.fromisoformat(match["published_date"][:10])
                          - date.fromisoformat(ep.published_date[:10])).days) > 7:
            # TAL reuses a feed guid when it republishes an episode, so the
            # catalog may already hold this guid under another airing's date
            # (earlier or later). This airing becomes its own episode with a
            # derived guid, written to the separate reruns file.
            rerun_of, match = match, None
        elif match is None and guid in emitted:
            # An earlier airing in this file already holds this guid.
            rerun_of = {"id": None, "published_date": emitted[guid]}
        if match and (match["audio_file_path"] or match["transcript_file_path"]):
            continue    # already has audio or text: nothing to do
        evidence = {"feed_capture": item["capture"], "feed_guid": guid,
                    "podcast_published_date": ep.published_date, "episode_number": number,
                    "date_rule": "pubDate of the item in an archived copy of the TAL podcast feed",
                    "window": item["window"]}

        enclosure = fetcher.probe_audio(ep.audio_url)
        audio_url, audio_from = None, None
        if enclosure["ok"]:
            audio_url, audio_from = ep.audio_url, "feed_enclosure"
        page = None
        if number is not None:
            url, text = None, None
            for url in page_urls(item["link"], number):
                text = fetcher.page(url)
                if text:
                    break
            page = parse_page(text) if text else None
            if page is not None:
                if page.get("number") != number:
                    skipped.append({"guid": guid, "title": title,
                                    "reason": f"page {url} is episode {page.get('number')}"})
                    continue
                evidence.update({"page_url": page.get("canonical") or url,
                                 "site_title": page.get("title"),
                                 "original_air_date": page.get("original_air_date"),
                                 "site_guid": page.get("site_guid")})
                if page.get("original_air_date"):
                    evidence["rerun"] = page["original_air_date"] < (
                        date.fromisoformat(ep.published_date[:10]) - timedelta(days=21)).isoformat()
                if audio_url is None and page.get("audio"):
                    site = fetcher.probe_audio(page["audio"])
                    if site["ok"]:
                        audio_url, audio_from = page["audio"], "publisher_site_audio"
                        evidence["site_audio_bytes"] = site.get("total_bytes")
        if audio_url is None:
            skipped.append({"guid": guid, "title": title, "window": item["window"],
                            "reason": "no working audio (enclosure dead, no site audio)"
                                      if number is not None else
                                      "no episode number in the title, enclosure dead",
                            "enclosure": enclosure, "page_found": page is not None})
            continue
        evidence["audio_from"] = audio_from
        if audio_from != "feed_enclosure":
            evidence["feed_enclosure"] = ep.audio_url
            evidence["feed_enclosure_probe"] = enclosure
        row = {"title": title, "published_date": ep.published_date, "audio_url": audio_url,
               "guid": guid, "description": ep.description, "evidence": evidence}
        if ep.duration_seconds:
            row["duration_seconds"] = ep.duration_seconds
        if match and match["audio_url"] != audio_url:
            row["replaces_episode_id"] = match["id"]
        if rerun_of is not None:
            row["guid"] = f"{guid}#rerun-{ep.published_date[:10]}"
            evidence.update({"rerun_of_episode_id": rerun_of["id"],
                             "rerun_of_published_date": rerun_of["published_date"],
                             "guid_note": "the feed reused this guid for another airing of the same episode"})
            reruns.append(row)
        else:
            rows.append(row)
            emitted[guid] = ep.published_date

    out = Path(args.out)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    out.with_suffix(".reruns.jsonl").write_text("".join(json.dumps(r) + "\n" for r in reruns))
    coverage = {label: uncovered(s, e, spans) for label, s, e in windows}
    by_window: dict[str, int] = {}
    for item in in_window.values():
        by_window[item["window"]] = by_window.get(item["window"], 0) + 1
    report = {
        "windows": len(windows), "captures_picked": len(picked), "feed_items": len(items),
        "items_in_windows": len(in_window), "rows": len(rows),
        "reruns_with_reused_guid": len(reruns), "skipped": skipped,
        "capture_failures": failures,
        "items_per_window": {lab: by_window.get(lab, 0) for lab, _s, _e in windows},
        "uncovered": {k: v for k, v in coverage.items() if v},
    }
    Path(args.out).with_suffix(".report.json").write_text(json.dumps(report, indent=1))
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--study", default="apple-top24-monthly")
    p.add_argument("--podcast-id", type=int, default=13)
    p.add_argument("--windows", help="comma-separated window labels (default: all of the podcast's)")
    p.add_argument("--out", required=True, help="JSONL for import-episodes")
    p.add_argument("--cache", required=True, help="directory for site pages and audio probes")
    p.add_argument("--site-delay", type=float, default=SITE_DELAY_SECONDS)
    p.add_argument("--config", type=Path)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Path(args.cache).mkdir(parents=True, exist_ok=True)
    report = build(args)
    summary = {k: v for k, v in report.items() if k not in ("skipped", "capture_failures")}
    summary["skipped"] = len(report["skipped"])
    summary["capture_failures"] = len(report["capture_failures"])
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
