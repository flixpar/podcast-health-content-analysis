"""Episodes for a study's gap windows from archived copies of a show's *old* feed URLs.

``discover-archived`` reads Wayback copies of the feed URLs the catalog knows
(``podcasts.rss_url`` and ``podcast_feeds``). Many shows moved host or URL
scheme, and the old URL -- the one that was live when the show charted -- is
in neither place: NPR's ``www.npr.org/rss/podcast.php?id=N`` became
``feeds.npr.org/N/podcast.xml`` in 2020, Art19 shows moved to Simplecast or
Megaphone, ESPN's radio feeds moved to Megaphone. Wayback holds years of the
old URLs.

For each (podcast, old feed URL) given, this lists the URL's captures, walks
backwards through each gap window -- a capture just after the window's end,
then one just after the oldest item that capture reached, and so on -- parses
them with the pipeline's own feed parser, and keeps the items published inside
a gap window that the catalog does not already hold (by guid, or by UTC day +
normalized title). Each kept item's enclosure is probed with a small ranged
GET; the row records whether it is live.

Output is ``import-episodes`` JSONL (one file per run) plus a log of the
captures used. Nothing is written to the database.

    ../.venv/bin/python tools/alternate_sources/archived_alt_feed.py apple-top24-monthly OUT_DIR \\
        --feed 667=https://www.npr.org/rss/podcast.php?id=510289 [--feed ID=URL ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import zstandard

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from podcast_pipeline.config import Config  # noqa: E402
from podcast_pipeline.pipeline.discover_archived import EARLIEST_PLAUSIBLE_DATE  # noqa: E402
from podcast_pipeline.rss import FeedError, parse_feed  # noqa: E402
from podcast_pipeline.studies.gaps import GAP_CLASSES, TARGET_CLASSES, study_gaps  # noqa: E402
from tools.alternate_sources.common import (  # noqa: E402
    Fetcher, deep_unwrap, open_db, origin_url, range_probe, title_key, write_jsonl,
)

SOURCE = "alternate_feed"
CACHE = Config().wayback_cache_dir / "alternate_feeds"
# Fetch at most this many captures per (podcast, URL).
MAX_FETCHES = 80
# A capture taken this long after a window's end still counts as "just after".
MAX_LAG_DAYS = 45


def _day(stamp: str) -> date:
    return datetime.strptime(stamp[:8], "%Y%m%d").date() if stamp[:8].isdigit() and len(stamp) >= 8 \
        else datetime.fromisoformat(stamp[:10]).date()


def _cache_path(kind: str, key: str) -> Path:
    return CACHE / kind / f"{hashlib.sha1(key.encode()).hexdigest()}.zst"


def list_captures(fetcher: Fetcher, cdx_url: str, url: str) -> list[dict]:
    """One successful capture per day of exactly ``url``, oldest first (cached)."""
    path = _cache_path("cdx", url)
    if path.exists():
        return json.loads(zstandard.decompress(path.read_bytes()))
    data = fetcher.get_json(cdx_url, params={
        "url": url, "output": "json", "filter": "statuscode:200", "collapse": "timestamp:8",
        "fl": "timestamp,original,digest"})
    caps = [dict(zip(data[0], r)) for r in data[1:]] if data else []
    # An empty listing is not cached, so "never archived" is always re-asked
    # rather than remembered from one throttled moment.
    if caps:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(zstandard.compress(json.dumps(caps).encode()))
    return caps


def fetch_capture(fetcher: Fetcher, replay: str, cap: dict) -> bytes | None:
    """The archived feed body, or None when Wayback will not serve it."""
    key = f"{cap['timestamp']} {cap['original']}"
    path = _cache_path("snap", key)
    if path.exists():
        return zstandard.decompress(path.read_bytes())
    r = fetcher.get(f"{replay.rstrip('/')}/{cap['timestamp']}id_/{cap['original']}")
    if r.status_code != 200 or not r.content.strip():
        return None
    body = r.content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(zstandard.compress(body))
    return body


def choose_capture(captures: list[dict], point: date, floor: date, used: set[str]) -> dict | None:
    """The capture to read next for items published before ``point``.

    The first unused capture on/after ``point`` (within ``MAX_LAG_DAYS``), else
    the latest unused one strictly between ``floor`` and ``point``.
    """
    after = [c for c in captures if c["timestamp"] not in used
             and point <= _day(c["timestamp"]) <= point + timedelta(days=MAX_LAG_DAYS)]
    if after:
        return after[0]
    inside = [c for c in captures if c["timestamp"] not in used and floor < _day(c["timestamp"]) < point]
    return inside[-1] if inside else None


def walk_window(fetcher, replay, captures, start: date, end: date, used: set[str],
                parsed: dict[str, list], log: list, budget: list[int]) -> None:
    """Read captures backwards through [start, end) until it is covered."""
    point = end
    while point > start and budget[0] > 0:
        cap = choose_capture(captures, point, start, used)
        if cap is None:
            return
        used.add(cap["timestamp"])
        budget[0] -= 1
        body = fetch_capture(fetcher, replay, cap)
        entry = {"capture": cap["timestamp"], "url": cap["original"]}
        log.append(entry)
        if body is None:
            entry["problem"] = "not served"
            continue
        try:
            episodes = parse_feed(body, cap["original"])
        except FeedError as e:
            entry["problem"] = str(e)
            continue
        dated = [e for e in episodes if e.published_date and e.published_date >= EARLIEST_PLAUSIBLE_DATE]
        parsed[cap["timestamp"]] = dated
        entry["items"] = len(dated)
        if not dated:
            continue
        oldest = min(_day(e.published_date) for e in dated)
        entry["oldest"] = oldest.isoformat()
        cap_day = _day(cap["timestamp"])
        new_point = min(oldest, cap_day) if cap_day < point else oldest
        if new_point >= point:
            # The feed reaches no further back than where we are; try an earlier capture.
            new_point = min(point, cap_day) - timedelta(days=1) if cap_day < point else point
            if new_point >= point:
                return
        point = new_point


def existing_keys(conn, podcast_id: int) -> tuple[set[str], set[tuple[str, str]]]:
    rows = conn.execute("SELECT episode_guid, title, published_date FROM episodes WHERE podcast_id = ?",
                        (podcast_id,)).fetchall()
    return ({r["episode_guid"] for r in rows},
            {((r["published_date"] or "")[:10], title_key(r["title"])) for r in rows})


def collect(conn, fetcher, config, study: str, podcast_id: int, feed_url: str,
            probe_limit: int, classes: tuple[str, ...] = TARGET_CLASSES,
            max_fetches: int = MAX_FETCHES) -> tuple[list[dict], dict]:
    gaps = next((g for g in study_gaps(conn, study, classes=classes) if g.podcast_id == podcast_id), None)
    log = {"podcast_id": podcast_id, "feed_url": feed_url, "captures": [], "windows": {}}
    if gaps is None:
        log["problem"] = "no gap windows"
        return [], log
    captures = list_captures(fetcher, config.wayback.cdx_url, feed_url)
    log["captures_listed"] = len(captures)
    if captures:
        log["capture_span"] = [captures[0]["timestamp"], captures[-1]["timestamp"]]
    parsed: dict[str, list] = {}
    used: set[str] = set()
    budget = [max_fetches]
    windows = sorted(gaps.windows, key=lambda w: w[1])
    for label, start, end in windows:
        walk_window(fetcher, config.wayback.replay_url, captures, _day(start), _day(end), used,
                    parsed, log["captures"], budget)

    guids, keys = existing_keys(conn, podcast_id)
    found: dict[str, tuple] = {}
    for stamp in sorted(parsed):
        for e in parsed[stamp]:
            window = next((w for w in windows if w[1] <= e.published_date[:10] < w[2]), None)
            if window is None:
                continue
            log["windows"].setdefault(window[0], {"in_feed": 0, "new": 0})
            log["windows"][window[0]]["in_feed"] += 1
            if e.guid in guids or (e.published_date[:10], title_key(e.title)) in keys:
                continue
            k = e.guid or f"{e.published_date[:10]}|{title_key(e.title)}"
            if k not in found:
                found[k] = (e, stamp, window[0])
                log["windows"][window[0]]["new"] += 1
    # The same episode under two guids (a re-keyed feed) is one episode.
    by_key: dict[tuple, tuple] = {}
    for e, stamp, label in found.values():
        by_key.setdefault((e.published_date[:10], title_key(e.title)), (e, stamp, label))

    rows = []
    for n, (e, stamp, label) in enumerate(sorted(by_key.values(), key=lambda t: t[0].published_date)):
        evidence = {"route": "Wayback copy of an old feed URL the catalog does not list",
                    "gap_classes": list(classes),
                    "feed_url": feed_url, "capture": stamp, "window": label,
                    "enclosure": e.audio_url}
        audio_url = e.audio_url
        if n < probe_limit:
            probe = range_probe(fetcher, e.audio_url)
            if not probe.is_audio:
                inner = deep_unwrap(e.audio_url)
                for alt_url in dict.fromkeys((inner, origin_url(inner))):
                    if alt_url == e.audio_url:
                        continue
                    alt = range_probe(fetcher, alt_url)
                    if alt.is_audio:
                        probe, audio_url = alt, alt_url
                        break
            evidence["probe"] = {"url": probe.url, "is_audio": probe.is_audio, "status": probe.status,
                                 "total_size": probe.total_size, "error": probe.error,
                                 "estimated_seconds": (probe.duration or {}).get("seconds"),
                                 "declared_seconds": e.duration_seconds, "id3_title": probe.id3_title}
        row = {"podcast_id": podcast_id, "guid": e.guid, "title": e.title,
               "published_date": e.published_date, "audio_url": audio_url,
               "description": e.description, "evidence": evidence}
        if e.duration_seconds:
            row["duration_seconds"] = e.duration_seconds
        if e.transcript_url:
            row["transcript_url"] = e.transcript_url
        rows.append(row)
    log["new_episodes"] = len(rows)
    return rows, log


def main() -> None:
    global CACHE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("study")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--feed", action="append", required=True, help="PODCAST_ID=OLD_FEED_URL")
    ap.add_argument("--probe-limit", type=int, default=1000,
                    help="probe at most this many enclosures per feed")
    ap.add_argument("--name", default=SOURCE, help="output file stem")
    ap.add_argument("--cache-dir", type=Path,
                    help="cache directory (default: configured data/wayback/alternate_feeds)")
    ap.add_argument("--max-fetches", type=int, default=MAX_FETCHES,
                    help="captures to read per (podcast, URL); a daily show with a short feed needs several a month")
    ap.add_argument("--all-gap-classes", type=int, action="append", default=[], metavar="PODCAST_ID",
                    help="for this podcast, target every gap window, not only missing/unknown "
                         "(when the classifier is demonstrably wrong; say why in the report)")
    args = ap.parse_args()

    config = Config.load()
    CACHE = args.cache_dir or config.wayback_cache_dir / "alternate_feeds"
    conn = open_db(config.db_path)
    fetcher = Fetcher()
    rows, logs = [], []
    for spec in args.feed:
        pid, _, url = spec.partition("=")
        classes = GAP_CLASSES if int(pid) in args.all_gap_classes else TARGET_CLASSES
        got, log = collect(conn, fetcher, config, args.study, int(pid), url, args.probe_limit, classes,
                           args.max_fetches)
        log["gap_classes"] = list(classes)
        rows += got
        logs.append(log)
        live = sum(1 for r in got if r["evidence"].get("probe", {}).get("is_audio"))
        print(f"{pid} {url}: {log.get('captures_listed', 0)} captures, "
              f"{len(log['captures'])} read, {len(got)} new episodes ({live} live audio)", flush=True)
        write_jsonl(args.out_dir / f"{args.name}.jsonl", rows)
        write_jsonl(args.out_dir / f"{args.name}.log.jsonl", logs)


if __name__ == "__main__":
    main()
