"""Enumerate Common Crawl captures of the chart sources, crawl by crawl.

The CC index is per-crawl, so this walks every published crawl (~127 of them)
for each URL pattern. Results are cached per (crawl, pattern) so the job can be
re-run after a stall without repeating work.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[2] / "data" / "chart-archive"
CC_DIR = ROOT / "cc_index"

PATTERNS = {
    "apple_charts_page": "podcasts.apple.com/us/charts*",
    "chartable_itunes_us": "chartable.com/charts/itunes/us-*",
    "chartable_reach": "chartable.com/charts/chartable/*",
    "itunes_rss": "itunes.apple.com/us/rss/toppodcasts*",
    "spotify_api": "podcastcharts.byspotify.com/api/charts/*",
    "applemarketingtools": "rss.applemarketingtools.com/api/v2/us/podcasts/*",
    "marketingtools": "rss.marketingtools.apple.com/api/v2/us/podcasts/*",
}

UA = "podcast-misinfo-research/1.0 (academic chart-history collection)"


def get(session: requests.Session, url: str, attempts: int = 5) -> str | None:
    delay = 5.0
    for _ in range(attempts):
        try:
            resp = session.get(url, timeout=180)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                return ""  # crawl has no captures for this pattern
        except requests.RequestException:
            pass
        time.sleep(delay)
        delay = min(delay * 1.8, 60)
    return None


def main() -> int:
    CC_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA
    cache = CC_DIR / "collinfo.json"
    if not cache.exists():
        body = get(session, "https://index.commoncrawl.org/collinfo.json", attempts=8)
        if not body:
            print("could not fetch the crawl list", flush=True)
            return 1
        cache.write_text(body)
    crawls = [c["id"] for c in json.loads(cache.read_text())]
    print(f"{len(crawls)} crawls x {len(PATTERNS)} patterns", flush=True)

    for name, pattern in PATTERNS.items():
        out_dir = CC_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)
        total = 0
        for crawl in crawls:
            out = out_dir / f"{crawl}.jsonl"
            if out.exists():
                total += sum(1 for _ in out.open())
                continue
            url = (f"https://index.commoncrawl.org/{crawl}-index"
                   f"?url={quote(pattern, safe='')}&output=json")
            body = get(session, url)
            if body is None:
                print(f"  {name} {crawl}: gave up", flush=True)
                continue
            lines = [ln for ln in body.splitlines()
                     if ln.startswith("{") and '"message"' not in ln[:40]]
            out.write_text("\n".join(lines) + ("\n" if lines else ""))
            total += len(lines)
            if lines:
                print(f"  {name} {crawl}: {len(lines)}", flush=True)
            time.sleep(1.0)
        print(f"{name}: {total} captures across all crawls", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
