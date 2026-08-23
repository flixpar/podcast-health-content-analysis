#!/usr/bin/env python3
"""
Fetch transcripts that podcast publishers already provide in their RSS feeds.

Phase 2 deliberately skips downloading audio for episodes whose feed advertises
a transcript, but nothing ever fetched those transcripts -- so those episodes
have neither audio nor text. This closes that gap. It is pure HTTP, needs no
GPU, and yields publisher-quality text for episodes ASR would otherwise have to
process from scratch.

Transcripts are normalized into the same JSONL+zstd layout the ASR pipeline
writes, so downstream consumers cannot tell the two sources apart apart from the
`source` field in the metadata line.

Usage:
    python tools/fetch_rss_transcripts.py --limit 50    # try a batch first
    python tools/fetch_rss_transcripts.py
"""

import argparse
import json
import logging
import re
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests
import zstandard as zstd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "podcast_metadata.db"
TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "transcripts"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_local = threading.local()


def session():
    s = getattr(_local, "session", None)
    if s is None:
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=1,
                      status_forcelist=[429, 500, 502, 503, 504])
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; PodcastTranscriber/1.0)"})
        _local.session = s
    return s


def db():
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), timeout=60.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")
        _local.conn = conn
    return conn


# --- parsers -----------------------------------------------------------------

TIMECODE = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[.,](?P<ms>\d{1,3})"
    r"\s*-->\s*"
    r"(?P<h2>\d{1,2}):(?P<m2>\d{2}):(?P<s2>\d{2})[.,](?P<ms2>\d{1,3})"
)

# Omny and similar serve "TextWithTimestamps": bare "HH:MM:SS" lines then text.
PLAIN_TIMESTAMP = re.compile(r"^\s*(\d{1,2}):(\d{2}):(\d{2})(?:[.,](\d{1,3}))?\s*$")


def _seconds(h, m, s, ms=0):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(str(ms).ljust(3, "0")) / 1000 if ms else \
        int(h) * 3600 + int(m) * 60 + int(s)


def parse_srt_vtt(body):
    """Parse SRT or WebVTT cues into timed segments."""
    segments = []
    blocks = re.split(r"\n\s*\n", body.replace("\r\n", "\n"))
    for block in blocks:
        match = TIMECODE.search(block)
        if not match:
            continue
        g = match.groupdict()
        text_lines = [ln for ln in block.split("\n")[match.string[:match.start()].count("\n") + 1:]
                      if ln.strip() and not ln.strip().isdigit()]
        text = " ".join(ln.strip() for ln in text_lines)
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            segments.append({
                "start": _seconds(g["h"], g["m"], g["s"], g["ms"]),
                "end": _seconds(g["h2"], g["m2"], g["s2"], g["ms2"]),
                "text": text,
            })
    return segments


def parse_plain_timestamped(body):
    """Parse alternating 'HH:MM:SS' / text lines."""
    segments = []
    pending_start = None
    buffer = []
    for line in body.replace("\r\n", "\n").split("\n"):
        m = PLAIN_TIMESTAMP.match(line)
        if m:
            if pending_start is not None and buffer:
                segments.append({"start": pending_start, "end": None,
                                 "text": " ".join(buffer).strip()})
            pending_start = _seconds(m.group(1), m.group(2), m.group(3), m.group(4) or 0)
            buffer = []
        elif line.strip():
            buffer.append(line.strip())
    if pending_start is not None and buffer:
        segments.append({"start": pending_start, "end": None, "text": " ".join(buffer).strip()})

    # Close each segment at the next one's start so downstream timing is usable
    for i in range(len(segments) - 1):
        segments[i]["end"] = segments[i + 1]["start"]
    return segments


def parse_json_transcript(body):
    """Parse the Podcast 2.0 JSON transcript shape."""
    data = json.loads(body)
    raw = data.get("segments") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        return []
    segments = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = (item.get("body") or item.get("text") or "").strip()
        if not text:
            continue
        segments.append({
            "start": item.get("startTime", item.get("start")),
            "end": item.get("endTime", item.get("end")),
            "text": text,
        })
    return segments


SPEAKER_LABEL = re.compile(r"^(?:speaker\s*\d+|[A-Z][A-Za-z.'-]{1,30})\s*:", re.IGNORECASE)


def html_to_text(body):
    """Strip an HTML transcript page down to its readable text."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(body, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def has_speaker_labels(segments):
    """True when segments are prefixed with speaker names, as most publisher transcripts are."""
    labelled = sum(1 for s in segments[:50] if SPEAKER_LABEL.match(s["text"]))
    return labelled >= max(2, min(len(segments), 50) // 4)


def parse_transcript(body, content_type):
    """Turn a fetched transcript into timed segments, whatever format it arrived in."""
    stripped = body.strip()
    if not stripped:
        return [], "empty"

    if "json" in content_type or stripped[0] in "[{":
        try:
            segments = parse_json_transcript(stripped)
            if segments:
                return segments, "json"
        except (json.JSONDecodeError, TypeError):
            pass

    if TIMECODE.search(stripped):
        segments = parse_srt_vtt(stripped)
        if segments:
            return segments, "srt/vtt"

    if PLAIN_TIMESTAMP.search(stripped.split("\n")[0]) or \
            any(PLAIN_TIMESTAMP.match(ln) for ln in stripped.split("\n")[:20]):
        segments = parse_plain_timestamped(stripped)
        if segments:
            return segments, "timestamped-text"

    if "html" in content_type or stripped.lower().lstrip().startswith(("<!doctype", "<html")):
        text = html_to_text(stripped)
        # Some feeds point at a player page rather than a transcript; those
        # yield only boilerplate, so require real substance before accepting.
        if len(text.split()) >= 200:
            return [{"start": None, "end": None, "text": text}], "html"
        return [], "html"

    # Untimed plain text still carries the words, which is what matters most.
    text = re.sub(r"\s+", " ", stripped)
    return [{"start": None, "end": None, "text": text}], "plain-text"


# --- storage -----------------------------------------------------------------

def save_transcript(episode_id, segments, metadata, level=3):
    """Write the JSONL+zstd file the rest of the pipeline expects."""
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TRANSCRIPT_DIR / f"episode_{episode_id}.jsonl.zst"

    full_text = " ".join(s["text"] for s in segments).strip()
    lines = [
        {"type": "metadata", "episode_id": episode_id,
         "created_at": datetime.now().isoformat(), "version": "1.0",
         "format": "jsonl_compressed", "compression": "zstd", **metadata},
        {"type": "summary", "text": full_text, "language": "en",
         "word_count": len(full_text.split()), "segment_count": len(segments)},
    ]
    for i, seg in enumerate(segments):
        lines.append({"type": "segment", "index": i, "start": seg.get("start"),
                      "end": seg.get("end"), "text": seg["text"], "confidence": None})

    payload = "\n".join(json.dumps(l, ensure_ascii=False, separators=(",", ":")) for l in lines)
    file_path.write_bytes(zstd.ZstdCompressor(level=level).compress(payload.encode("utf-8")))
    return str(file_path), len(full_text.split())


def record(episode_id, file_path, word_count, segments, source_format):
    conn = db()
    cur = conn.cursor()
    duration = next((s["end"] for s in reversed(segments) if s.get("end")), None)
    cur.execute("""
        INSERT OR REPLACE INTO transcripts
        (episode_id, format, compression, file_path, word_count, duration_seconds,
         confidence_score, has_timestamps, has_speakers, metadata)
        VALUES (?, 'jsonl', 'zstd', ?, ?, ?, NULL, ?, 0, ?)
    """, (episode_id, file_path, word_count, duration,
          int(any(s.get("start") is not None for s in segments)),
          json.dumps({"source": "rss", "source_format": source_format})))
    cur.execute("UPDATE transcripts SET has_speakers = ? WHERE episode_id = ?",
                (int(has_speaker_labels(segments)), episode_id))
    cur.execute("""
        UPDATE episodes
        SET transcript_file_path = ?, transcribed_at = CURRENT_TIMESTAMP,
            status = 'transcribed', error_message = NULL
        WHERE id = ?
    """, (file_path, episode_id))
    conn.commit()


# --- driver ------------------------------------------------------------------

def fetch_one(row, timeout, min_words):
    episode_id, url, title = row
    try:
        resp = session().get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        return ("http_error", f"{episode_id}: {e}")

    content_type = (resp.headers.get("content-type") or "").lower()
    segments, source_format = parse_transcript(resp.text, content_type)
    if not segments:
        return ("unparseable", f"{episode_id}: {source_format} ({len(resp.text)} bytes)")

    word_count = sum(len(s["text"].split()) for s in segments)
    if word_count < min_words:
        return ("too_short", f"{episode_id}: {word_count} words")

    file_path, words = save_transcript(episode_id, segments,
                                       {"source": "rss", "source_format": source_format,
                                        "source_url": url, "episode_title": title})
    record(episode_id, file_path, words, segments, source_format)
    return ("saved", source_format)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--min-words", type=int, default=100,
                        help="Reject suspiciously short transcripts as failures")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Also retry episodes a previous run could not parse")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, transcript_url, title
        FROM episodes
        WHERE has_rss_transcript = 1
          AND transcript_url IS NOT NULL AND transcript_url != ''
          AND (transcript_file_path IS NULL OR transcript_file_path = '')
        ORDER BY id
        {'LIMIT ?' if args.limit else ''}
    """, (args.limit,) if args.limit else ())
    rows = cur.fetchall()
    conn.close()

    logger.info(f"Fetching {len(rows)} RSS transcripts with {args.workers} workers")
    if not rows:
        return

    counts = {}
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, (outcome, detail) in enumerate(
                pool.map(lambda r: fetch_one(r, args.timeout, args.min_words), rows), 1):
            counts[outcome] = counts.get(outcome, 0) + 1
            if outcome != "saved":
                failures.append(f"{outcome}: {detail}")
            if i % 100 == 0:
                logger.info(f"  {i}/{len(rows)} -- {counts}")

    print("\n" + "=" * 52)
    print("RSS TRANSCRIPT FETCH")
    print("=" * 52)
    for key, value in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {key:16s}: {value}")
    print("=" * 52)
    if failures:
        print("\nFirst failures:")
        for line in failures[:10]:
            print("  " + line)


if __name__ == "__main__":
    main()
