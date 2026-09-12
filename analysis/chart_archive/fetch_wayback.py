"""Download every Wayback capture listed in index/*.cdx.

Captures are fetched with the `id_` modifier so we get the original bytes
rather than Wayback's rewritten HTML, then stored gzipped under
raw/<target>/<url-slug>/<timestamp>.<ext>.gz. Reruns skip files already on
disk, so the job is resumable after a throttle-induced stall.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

ROOT = Path(__file__).resolve().parents[2] / "data" / "chart-archive"
INDEX_DIR = ROOT / "index"
RAW_DIR = ROOT / "raw"
MANIFEST_DIR = ROOT / "manifest"

WORKERS = 10
UA = "podcast-misinfo-research/1.0 (academic chart-history collection)"

# Query params worth keeping per target; everything else (affiliate ids,
# utm_*, Outlook safelink junk) is dropped before de-duplication.
KEEP_PARAMS = {
    "apple_charts_page": {"genre", "l"},
    "chartable_itunes_us": {"page"},
    "chartable_reach": {"page"},
    "chartable_spotify": {"page"},
    "spotify_api": {"region", "limit"},
    "itunes_rss": set(),
    "itunes_rss_ax": set(),
    "podbay": set(),
    "marketingtools": set(),
    "applemarketingtools": set(),
}

EXT_BY_MIME = {
    "application/json": "json",
    "text/json": "json",
    "text/html": "html",
    "application/xml": "xml",
    "text/xml": "xml",
    "application/rss+xml": "xml",
}

_print_lock = threading.Lock()
_throttle = threading.Semaphore(WORKERS)


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def normalize(target: str, url: str) -> str | None:
    """Canonical form of a capture URL, or None if it is a variant to skip."""
    parts = urlsplit(url)
    keep = KEEP_PARAMS.get(target, set())
    params = [(k, v) for k, v in parse_qsl(parts.query) if k in keep]
    if target == "apple_charts_page":
        lang = dict(params).get("l")
        if lang and not lang.startswith("en"):
            return None  # translated duplicate of the same chart
        params = [(k, v) for k, v in params if k != "l"]
    params.sort()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", parts.netloc, path, urlencode(params), ""))


def slug(url: str) -> str:
    parts = urlsplit(url)
    raw = (parts.path + ("?" + parts.query if parts.query else "")).strip("/")
    raw = raw or "root"
    clean = re.sub(r"[^A-Za-z0-9._=-]+", "_", raw).strip("_")[:100]
    return f"{clean}-{hashlib.sha1(url.encode()).hexdigest()[:8]}"


def load_rows() -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple] = set()
    for path in sorted(INDEX_DIR.glob("*.cdx")):
        target = path.stem
        for line in path.read_text().splitlines():
            fields = line.split()
            if len(fields) != 7:
                continue
            ts, original, _urlkey, mime, status, digest, length = fields
            norm = normalize(target, original)
            if norm is None:
                continue
            # One fetch per (url, content) pair: repeated identical captures of
            # the same chart add nothing, but the same digest under a different
            # URL (a genre chart mirroring the overall one) is worth keeping.
            key = (target, norm, digest)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "target": target,
                    "timestamp": ts,
                    "original": original,
                    "url": norm,
                    "mime": mime,
                    "status": status,
                    "digest": digest,
                    "length": int(length) if length.isdigit() else None,
                }
            )
    return rows


def dest_for(row: dict) -> Path:
    ext = EXT_BY_MIME.get(row["mime"], "bin")
    if row["target"] in {"spotify_api", "marketingtools", "applemarketingtools"}:
        ext = "json" if "json" in row["url"] or ext == "json" else ext
    return RAW_DIR / row["target"] / slug(row["url"]) / f"{row['timestamp']}.{ext}.gz"


def fetch(row: dict, session: requests.Session) -> dict:
    dest = dest_for(row)
    row["path"] = str(dest.relative_to(ROOT))
    if dest.exists() and dest.stat().st_size > 0:
        row["result"] = "cached"
        return row
    # Ask for the exact captured URL, tracking params and all: requesting the
    # normalized form makes Wayback redirect to the *nearest* capture of that
    # URL, which silently files a snapshot under the wrong date.
    wb = f"https://web.archive.org/web/{row['timestamp']}id_/{row['original']}"
    delay = 8.0
    for attempt in range(1, 7):
        try:
            with _throttle:
                resp = session.get(wb, timeout=120)
            if resp.status_code == 200 and resp.content:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(gzip.compress(resp.content))
                row["result"] = "ok"
                row["bytes"] = len(resp.content)
                served = re.search(r"/web/(\d{14})", resp.url)
                row["served_ts"] = served.group(1) if served else None
                return row
            if resp.status_code in (403, 404, 451):
                row["result"] = f"http_{resp.status_code}"
                return row
            reason = f"http_{resp.status_code}"
            if resp.status_code == 429:
                time.sleep(30)  # a global rate limit, not a per-URL problem
        except requests.RequestException as exc:
            reason = type(exc).__name__
        time.sleep(delay + random.uniform(0, 3))
        delay = min(delay * 1.7, 90)
    row["result"] = f"failed:{reason}"
    return row


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    rows = [r for r in load_rows() if only is None or r["target"] == only]
    log(f"{len(rows)} captures to fetch")
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    out = MANIFEST_DIR / ("wayback.jsonl" if only is None else f"wayback_{only}.jsonl")
    done = 0
    session = requests.Session()
    session.headers["User-Agent"] = UA
    with out.open("w") as fh, ThreadPoolExecutor(WORKERS) as pool:
        for row in pool.map(lambda r: fetch(r, session), rows):
            fh.write(json.dumps(row) + "\n")
            done += 1
            if done % 100 == 0:
                log(f"  {done}/{len(rows)}")
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
