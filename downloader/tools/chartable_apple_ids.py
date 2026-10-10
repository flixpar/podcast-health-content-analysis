#!/usr/bin/env python3
"""Apple id and feed of each Chartable show on the overall chart, from archived Chartable pages.

Chartable's chart rows (``chartable_itunes``) carry a title and a slug but no
Apple id. Its show page, ``chartable.com/podcasts/<slug>``, links the Apple
listing ("Listen on Apple Podcasts", ``.../id<N>``) and the feed ("RSS
feed"). For every slug that ranked <= ``--max-rank`` on a trusted overall-chart
snapshot, this fetches the Wayback capture nearest the slug's first chart month
(then its last month, then 2023), and writes one JSON line per slug:

    {"slug", "name", "title_key", "first", "last", "ts", "apple_ids", "feeds", "page_title"}

Load the result with ``import-chart-ids OUT.jsonl``. Read-only on the DB;
resumable (slugs already in OUT are skipped); pages are cached under
``--cache``. One request at a time, paced: Wayback refuses connections from a
host that sends too many, so a refused connection pauses the run for 10 minutes.
First run 2026-10-10 (``data/studies/apple-top100-monthly/review/r3/chartable-slugs.jsonl``).

    ../.venv/bin/python tools/chartable_apple_ids.py OUT.jsonl [--cache DIR] [--max-rank 100]
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from podcast_pipeline.config import DEFAULT_CONFIG_PATH, Config  # noqa: E402

APPLE = re.compile(r'href="https?://(?:podcasts|itunes)\.apple\.com/[^"]*?/id(\d+)[^"]*"[^>]*>\s*'
                   r'Listen on Apple Podcasts')
FEED = re.compile(r'href="([^"]+)"[^>]*>\s*RSS feed\s*<')
TITLE = re.compile(r"<title>\s*(.*?)\s*(?:Podcast)?\s*-\s*Listen, Reviews, Charts", re.S)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-podcast-chart-study"}
PACE_SECONDS, REFUSED_PAUSE_SECONDS = 1.0, 600


def fetch(cache: Path, ts: str, url: str) -> tuple[str | None, str | None]:
    """(body of the capture nearest ``ts``, None) or (None, error)."""
    wb = f"https://web.archive.org/web/{ts}id_/{url}"
    path = cache / hashlib.sha1(wb.encode()).hexdigest()
    if path.exists():
        return path.read_bytes().decode("utf-8", "replace"), None
    err = None
    for attempt in range(5):
        time.sleep(PACE_SECONDS)
        try:
            r = requests.get(wb, headers=UA, timeout=90)
        except requests.RequestException as e:
            err = str(e)[:200]
            time.sleep(REFUSED_PAUSE_SECONDS if "refused" in err.lower() else 10 * (attempt + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            err = f"HTTP {r.status_code}"
            time.sleep(20 * (attempt + 1))
            continue
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}"
        path.write_bytes(r.content)
        return r.content.decode("utf-8", "replace"), None
    return None, err


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", type=Path)
    ap.add_argument("--cache", type=Path, help="page cache (default: <wayback cache>/chartable-pages)")
    ap.add_argument("--max-rank", type=int, default=100)
    args = ap.parse_args()
    config = Config.load(DEFAULT_CONFIG_PATH)
    cache = args.cache or Path(config.wayback_cache_dir) / "chartable-pages"
    cache.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{config.db_path}?mode=ro", uri=True)
    slugs = conn.execute("""
        SELECT e.source_entity_id, MIN(s.captured_on), MAX(s.captured_on), MIN(e.name), MIN(e.title_key)
        FROM chart_entries e JOIN chart_snapshots s ON s.id = e.snapshot_id
        WHERE s.source = 'chartable_itunes' AND s.chart = 'apple:us:podcast:all' AND s.trusted = 1
          AND e.rank <= ? AND e.source_entity_id IS NOT NULL
        GROUP BY 1 ORDER BY MIN(e.rank)
    """, (args.max_rank,)).fetchall()
    done = {json.loads(line)["slug"] for line in args.out.open()} if args.out.exists() else set()
    todo = [s for s in slugs if s[0] not in done]
    print(f"{len(todo)} of {len(slugs)} slugs to fetch", flush=True)
    with args.out.open("a") as out:
        for i, (slug, first, last, name, key) in enumerate(todo):
            url = f"https://chartable.com/podcasts/{slug}"
            row = {"slug": slug, "name": name, "title_key": key, "first": first, "last": last}
            for ts in (first.replace("-", "")[:6], last.replace("-", "")[:6], "2023"):
                body, err = fetch(cache, ts, url)
                if body is None:
                    row.setdefault("errors", []).append(f"{ts}: {err}")
                    continue
                title = TITLE.search(body)
                row.update(ts=ts, apple_ids=sorted(set(APPLE.findall(body))),
                           feeds=sorted({html.unescape(f) for f in FEED.findall(body)}),
                           page_title=html.unescape(title.group(1)) if title else None)
                if row["apple_ids"] or row["feeds"]:
                    break
            out.write(json.dumps(row) + "\n")
            out.flush()
            if i % 50 == 0:
                print(i, flush=True)


if __name__ == "__main__":
    main()
