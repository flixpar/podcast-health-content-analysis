"""Enumerate Wayback captures for every podcast-chart source we might use.

One CDX request per target, run strictly sequentially with backoff: the CDX
endpoint drops parallel requests on the floor (an empty body, not an error),
which silently looks like "this URL was never archived".
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2] / "data" / "chart-archive"
INDEX_DIR = ROOT / "index"

# name -> URL prefix (all requests keep only HTTP 200 captures)
TARGETS = {
    "spotify_api": "podcastcharts.byspotify.com/api/charts/",
    "chartable_itunes_us": "chartable.com/charts/itunes/us-",
    "chartable_spotify": "chartable.com/charts/spotify",
    "chartable_reach": "chartable.com/charts/chartable/",
    "apple_charts_page": "podcasts.apple.com/us/charts",
    "itunes_rss": "itunes.apple.com/us/rss/toppodcasts",
    "itunes_rss_ax": "ax.itunes.apple.com/WebObjects/MZStoreServices.woa/ws/RSS/toppodcasts",
    "podbay": "podbay.fm/browse",
    "marketingtools": "rss.marketingtools.apple.com/api/v2/us/podcasts",
    "applemarketingtools": "rss.applemarketingtools.com/api/v2/us/podcasts",
}

FIELDS = "timestamp,original,urlkey,mimetype,statuscode,digest,length"


def valid_index(body: str) -> bool:
    """Reject error pages and truncated/malformed CDX responses, including caches."""
    lines = [line.split() for line in body.splitlines() if line.strip()]
    if not lines:
        return False
    return all(len(fields) == 7 and len(fields[0]) == 14 and fields[0].isdigit()
               and urlsplit(fields[1]).scheme in {"http", "https"}
               and fields[4] == "200" and (fields[6].isdigit() or fields[6] == "-")
               for fields in lines)


def cdx(prefix: str, attempts: int = 6) -> str | None:
    url = (
        "https://web.archive.org/cdx/search/cdx"
        f"?url={prefix}&matchType=prefix&fl={FIELDS}"
        "&filter=statuscode:200&collapse=digest&limit=400000"
    )
    delay = 10
    for attempt in range(1, attempts + 1):
        proc = subprocess.run(
            ["curl", "-fsSL", "--max-time", "300", url],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and valid_index(proc.stdout):
            return proc.stdout
        print(f"  retry {attempt} (rc={proc.returncode}, {len(proc.stdout)} bytes)", flush=True)
        time.sleep(delay)
        delay = min(delay * 2, 120)
    return None


def main() -> int:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}
    failed = []
    for name, prefix in TARGETS.items():
        out = INDEX_DIR / f"{name}.cdx"
        cached = out.read_text() if out.exists() else ""
        if valid_index(cached):
            summary[name] = sum(bool(line.strip()) for line in cached.splitlines())
            print(f"{name}: cached ({summary[name]} rows)", flush=True)
            continue
        print(f"{name}: querying {prefix} ...", flush=True)
        body = cdx(prefix)
        if body is None:
            failed.append(name)
            summary[name] = None
            print(f"{name}: fetch failed; rerun to retry", flush=True)
            continue
        tmp = out.with_suffix(".cdx.tmp")
        tmp.write_text(body)
        tmp.replace(out)
        rows = len([ln for ln in body.splitlines() if ln.strip()])
        summary[name] = rows
        print(f"{name}: {rows} captures", flush=True)
        time.sleep(5)
    (INDEX_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
