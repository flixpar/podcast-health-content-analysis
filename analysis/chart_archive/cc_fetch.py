"""Pull the WARC payload for every Common Crawl capture found by cc_index.py.

Each index row carries the WARC file, byte offset and length, so one ranged
GET per capture is enough; the gzip member is decoded and the WARC/HTTP
headers stripped so the stored bytes match what Wayback gives us.
"""

from __future__ import annotations

import gzip
import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_wayback import KEEP_PARAMS, normalize, slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data" / "chart-archive"
CC_INDEX = ROOT / "cc_index"
RAW_CC = ROOT / "raw_cc"
BASE = "https://data.commoncrawl.org/"
WORKERS = 8
UA = "podcast-misinfo-research/1.0 (academic chart-history collection)"

EXT = {"text/html": "html", "application/json": "json", "text/xml": "xml",
       "application/xml": "xml", "application/rss+xml": "xml"}


def dechunk(body: bytes) -> bytes:
    out, pos = bytearray(), 0
    while pos < len(body):
        nl = body.find(b"\r\n", pos)
        if nl == -1:
            break
        try:
            size = int(body[pos:nl].split(b";")[0], 16)
        except ValueError:
            return bytes(body)
        if size == 0:
            break
        out += body[nl + 2:nl + 2 + size]
        pos = nl + 2 + size + 2
    return bytes(out)


def payload(raw: bytes) -> bytes:
    """Strip the WARC and HTTP headers, undoing chunking/gzip if declared.

    CC stores the response exactly as received, so a chunked body still has its
    hex length lines interleaved and a gzipped one is still compressed.
    """
    body = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    parts = body.split(b"\r\n\r\n", 2)
    if len(parts) < 3:
        parts = body.split(b"\n\n", 2)
        if len(parts) < 3:
            return body
    http_headers, content = parts[1], parts[2]
    lowered = http_headers.lower()
    if b"transfer-encoding: chunked" in lowered:
        content = dechunk(content)
    if b"content-encoding: gzip" in lowered:
        try:
            content = gzip.decompress(content)
        except (OSError, EOFError):
            pass
    return content


def load_rows() -> list[dict]:
    rows, seen = [], set()
    for target_dir in sorted(CC_INDEX.iterdir()):
        if not target_dir.is_dir():
            continue
        target = target_dir.name
        for jf in sorted(target_dir.glob("*.jsonl")):
            for line in jf.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("status") != "200" or "filename" not in rec:
                    continue
                norm = normalize(target, rec["url"])
                if norm is None:
                    continue
                key = (target, norm, rec.get("digest"))
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "target": target, "url": norm, "original": rec["url"],
                    "timestamp": rec["timestamp"], "crawl": jf.stem,
                    "filename": rec["filename"], "offset": int(rec["offset"]),
                    "length": int(rec["length"]),
                    "mime": rec.get("mime-detected") or rec.get("mime") or "",
                })
    return rows


def fetch(row: dict, session: requests.Session) -> dict:
    ext = EXT.get(row["mime"], "html")
    dest = RAW_CC / row["target"] / slug(row["url"]) / f"{row['timestamp']}.{ext}.gz"
    row["path"] = str(dest.relative_to(ROOT))
    if dest.exists() and dest.stat().st_size > 0:
        row["result"] = "cached"
        return row
    end = row["offset"] + row["length"] - 1
    headers = {"Range": f"bytes={row['offset']}-{end}"}
    delay = 5.0
    for _ in range(5):
        try:
            resp = session.get(BASE + row["filename"], headers=headers, timeout=120)
            if resp.status_code in (200, 206) and resp.content:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(gzip.compress(payload(resp.content)))
                row["result"] = "ok"
                return row
            reason = f"http_{resp.status_code}"
        except (requests.RequestException, OSError, EOFError) as exc:
            reason = type(exc).__name__
        time.sleep(delay)
        delay = min(delay * 1.8, 60)
    row["result"] = f"failed:{reason}"
    return row


def main() -> int:
    rows = load_rows()
    print(f"{len(rows)} Common Crawl captures", flush=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA
    out = ROOT / "manifest" / "commoncrawl.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = 0
    with out.open("w") as fh, ThreadPoolExecutor(WORKERS) as pool:
        for row in pool.map(lambda r: fetch(r, session), rows):
            fh.write(json.dumps(row) + "\n")
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(rows)}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
