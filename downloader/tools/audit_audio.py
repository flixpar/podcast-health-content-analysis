#!/usr/bin/env python3
"""
Audio/database integrity auditor.

Reconciles the `episodes` table against what is actually on disk and reports:

  missing        - status='downloaded' but the file is gone
  empty          - file exists but is zero/near-zero bytes
  unreadable     - ffprobe cannot decode the file
  truncated      - decoded duration is far short of the RSS-declared duration
                   (the signature of a download killed by a full disk)
  shared_path    - several episode rows point at the same file (title collision)
  orphan         - audio file on disk that no episode row references

With --fix, rows in the missing/empty/unreadable/truncated categories are reset to
status='pending' with their audio_file_path cleared, so Phase 2 re-downloads them.

Usage:
    python tools/audit_audio.py                       # audit everything
    python tools/audit_audio.py --newer-than '2025-10-14 03:00'   # only suspect window
    python tools/audit_audio.py --fix
"""

import argparse
import json
import logging
import sqlite3
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "podcast_metadata.db"
AUDIO_DIR = PROJECT_ROOT / "data" / "audio"

MIN_BYTES = 100 * 1024          # anything smaller than this is not a real episode
TRUNCATION_TOLERANCE = 0.90     # decoded duration must be >= this fraction of RSS duration

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def probe_duration(path):
    """Return decoded duration in seconds, or None if the file cannot be read."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=120,
        )
        if out.returncode != 0:
            return None
        value = out.stdout.strip()
        return float(value) if value and value != "N/A" else None
    except (subprocess.TimeoutExpired, ValueError):
        return None


def audit(conn, newer_than=None, workers=8, skip_probe=False):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, podcast_id, audio_file_path, duration_seconds, status
        FROM episodes
        WHERE audio_file_path IS NOT NULL AND audio_file_path != ''
    """)
    rows = cursor.fetchall()
    logger.info(f"Auditing {len(rows)} episode rows with an audio path")

    cutoff = datetime.strptime(newer_than, "%Y-%m-%d %H:%M").timestamp() if newer_than else None

    findings = defaultdict(list)
    path_owners = defaultdict(list)
    to_probe = []

    for ep_id, podcast_id, path_str, rss_duration, status in rows:
        path = Path(path_str)
        path_owners[path_str].append(ep_id)

        if not path.exists():
            findings["missing"].append({"episode_id": ep_id, "path": path_str})
            continue

        size = path.stat().st_size
        if size < MIN_BYTES:
            findings["empty"].append({"episode_id": ep_id, "path": path_str, "size": size})
            continue

        if cutoff is not None and path.stat().st_mtime < cutoff:
            continue
        if not skip_probe:
            to_probe.append((ep_id, path, rss_duration))

    for path_str, owners in path_owners.items():
        if len(owners) > 1:
            findings["shared_path"].append({"path": path_str, "episode_ids": owners})

    if to_probe:
        logger.info(f"Probing {len(to_probe)} files with ffprobe ({workers} workers)...")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            durations = list(pool.map(lambda t: probe_duration(t[1]), to_probe))

        for (ep_id, path, rss_duration), actual in zip(to_probe, durations):
            if actual is None:
                findings["unreadable"].append({"episode_id": ep_id, "path": str(path)})
            elif rss_duration and rss_duration > 60 and actual < rss_duration * TRUNCATION_TOLERANCE:
                findings["truncated"].append({
                    "episode_id": ep_id, "path": str(path),
                    "actual_seconds": round(actual, 1), "expected_seconds": rss_duration,
                    "fraction": round(actual / rss_duration, 3),
                })

    # Files on disk that no episode row claims
    known = {Path(r[2]).resolve() for r in rows}
    for audio_file in AUDIO_DIR.rglob("*"):
        if audio_file.suffix.lower() in (".mp3", ".ogg", ".m4a", ".wav") and audio_file.is_file():
            if audio_file.resolve() not in known:
                findings["orphan"].append({"path": str(audio_file),
                                           "size_mb": round(audio_file.stat().st_size / 1024**2, 1)})

    return findings


REPAIRABLE = ("missing", "empty", "unreadable", "truncated")

# Never re-queue an episode we already have text for: a transcript fetched from
# the publisher's feed makes its audio unnecessary.
RESET_SQL = """
    UPDATE episodes
    SET status = 'pending', audio_file_path = NULL, error_message = NULL,
        original_file_size_mb = NULL, compressed_file_size_mb = NULL,
        compression_ratio = NULL, is_compressed = 0
    WHERE id = ?
      AND status != 'transcribed'
      AND (transcript_file_path IS NULL OR transcript_file_path = '')
"""


def apply_fix(conn, findings):
    """Reset broken rows to 'pending' so a download pass picks them up again."""
    cursor = conn.cursor()

    ids = sorted({f["episode_id"] for key in REPAIRABLE for f in findings.get(key, [])})
    reset_count = 0
    if ids:
        for episode_id in ids:
            cursor.execute(RESET_SQL, (episode_id,))
            reset_count += cursor.rowcount
        logger.info(f"Reset {reset_count} broken episodes to 'pending' "
                    f"({len(ids) - reset_count} skipped, already transcribed)")

    # Several rows pointing at one file means episodes with identical titles
    # overwrote each other under the old title-only naming scheme. Exactly one
    # row legitimately owns the file; the rest never got their own audio.
    # Keep the lowest id and re-queue the others, which will now download under
    # GUID-hashed filenames and stop colliding.
    collided = []
    for entry in findings.get("shared_path", []):
        collided.extend(sorted(entry["episode_ids"])[1:])
    collided = sorted(set(collided) - set(ids))
    collided_count = 0
    if collided:
        for episode_id in collided:
            cursor.execute(RESET_SQL, (episode_id,))
            collided_count += cursor.rowcount
        logger.info(f"Re-queued {collided_count} episodes that shared a file with another episode")

    conn.commit()
    return reset_count + collided_count


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--newer-than", help="Only probe files modified after 'YYYY-MM-DD HH:MM'")
    parser.add_argument("--skip-probe", action="store_true",
                        help="Skip ffprobe; only check existence and size")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--fix", action="store_true", help="Reset broken rows to 'pending'")
    parser.add_argument("--report", default=str(PROJECT_ROOT / "tools" / "audit_report.json"))
    args = parser.parse_args()

    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    findings = audit(conn, args.newer_than, args.workers, args.skip_probe)

    print("\n" + "=" * 56)
    print("AUDIO INTEGRITY AUDIT")
    print("=" * 56)
    for key in ("missing", "empty", "unreadable", "truncated", "shared_path", "orphan"):
        print(f"  {key:12s}: {len(findings.get(key, [])):6d}")
    print("=" * 56)

    for sample_key in ("truncated", "unreadable"):
        for item in findings.get(sample_key, [])[:5]:
            print(f"  [{sample_key}] {item}")

    Path(args.report).write_text(json.dumps(findings, indent=2))
    print(f"\nFull report: {args.report}")

    if args.fix:
        apply_fix(conn, findings)
    elif any(findings.get(k) for k in REPAIRABLE) or findings.get("shared_path"):
        print("\nRe-run with --fix to reset broken rows to 'pending'.")

    conn.close()


if __name__ == "__main__":
    main()
