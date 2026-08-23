"""Reconcile the ``episodes`` table against what is actually on disk.

Findings:
  missing      status says downloaded but the file is gone
  empty        file exists but is too small to be an episode
  unreadable   ffprobe cannot decode the file
  truncated    decoded duration far short of the feed-declared duration
               (the signature of a download killed by a full disk)
  shared_path  several episode rows point at one file (title collision under
               the old title-only naming scheme)
  orphan       audio file on disk that no episode row references

With ``fix=True`` the repairable rows are reset to ``pending`` so the download
stage fetches them again.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from podcast_pipeline import db
from podcast_pipeline.audio import AUDIO_EXTENSIONS, MIN_AUDIO_BYTES
from podcast_pipeline.audio.ffmpeg import probe_duration
from podcast_pipeline.config import Config

logger = logging.getLogger(__name__)

TRUNCATION_TOLERANCE = 0.90   # decoded duration must be >= this fraction of the feed's
REPAIRABLE = ("missing", "empty", "unreadable", "truncated")
FINDING_KEYS = REPAIRABLE + ("shared_path", "orphan")


def audit(conn: sqlite3.Connection, audio_dir: Path, newer_than: str | None = None,
          workers: int = 8, skip_probe: bool = False) -> dict[str, list]:
    rows = conn.execute("""
        SELECT id, audio_file_path, duration_seconds FROM episodes
        WHERE audio_file_path IS NOT NULL AND audio_file_path != ''
    """).fetchall()
    logger.info(f"Auditing {len(rows)} episode rows with an audio path")
    cutoff = datetime.strptime(newer_than, "%Y-%m-%d %H:%M").timestamp() if newer_than else None

    findings: dict[str, list] = {key: [] for key in FINDING_KEYS}
    owners: dict[str, list[int]] = defaultdict(list)
    to_probe = []
    for row in rows:
        path = Path(row["audio_file_path"])
        owners[row["audio_file_path"]].append(row["id"])
        if not path.exists():
            findings["missing"].append({"episode_id": row["id"], "path": str(path)})
            continue
        stat = path.stat()
        if stat.st_size < MIN_AUDIO_BYTES:
            findings["empty"].append({"episode_id": row["id"], "path": str(path), "size": stat.st_size})
            continue
        if cutoff is not None and stat.st_mtime < cutoff:
            continue
        if not skip_probe:
            to_probe.append((row["id"], path, row["duration_seconds"]))

    for path, ids in owners.items():
        if len(ids) > 1:
            findings["shared_path"].append({"path": path, "episode_ids": ids})

    if to_probe:
        logger.info(f"Probing {len(to_probe)} files with ffprobe ({workers} workers)")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            durations = list(pool.map(lambda item: probe_duration(item[1]), to_probe))
        for (episode_id, path, declared), actual in zip(to_probe, durations):
            if actual is None:
                findings["unreadable"].append({"episode_id": episode_id, "path": str(path)})
            elif declared and declared > 60 and actual < declared * TRUNCATION_TOLERANCE:
                findings["truncated"].append({
                    "episode_id": episode_id, "path": str(path),
                    "actual_seconds": round(actual, 1), "expected_seconds": declared,
                    "fraction": round(actual / declared, 3),
                })

    known = {Path(row["audio_file_path"]).resolve() for row in rows}
    for file in audio_dir.rglob("*"):
        if file.suffix.lower() not in AUDIO_EXTENSIONS or file.resolve() in known:
            continue
        try:
            size = file.stat().st_size
        except FileNotFoundError:
            continue   # deleted mid-walk by a concurrent convert-audio run
        findings["orphan"].append({"path": str(file), "size_mb": round(size / 1024 ** 2, 1)})
    return findings


def apply_fix(conn: sqlite3.Connection, findings: dict[str, list]) -> int:
    """Re-queue broken rows for download. Returns the number of rows reset."""
    broken = sorted({f["episode_id"] for key in REPAIRABLE for f in findings[key]})
    reset = sum(db.reset_episode_for_download(conn, episode_id) for episode_id in broken)
    logger.info(f"Reset {reset} broken episodes to pending "
                f"({len(broken) - reset} skipped because they already have a transcript)")

    # Several rows pointing at one file means identically titled episodes
    # overwrote each other. The lowest id keeps the file; the others download
    # again under GUID-hashed names and stop colliding.
    collided = sorted({episode_id for f in findings["shared_path"]
                       for episode_id in sorted(f["episode_ids"])[1:]} - set(broken))
    requeued = sum(db.reset_episode_for_download(conn, episode_id) for episode_id in collided)
    logger.info(f"Re-queued {requeued} episodes that shared a file with another episode")
    conn.commit()
    return reset + requeued


def run(config: Config, conn: sqlite3.Connection, fix: bool = False, newer_than: str | None = None,
        workers: int = 8, skip_probe: bool = False, report: Path | None = None) -> dict:
    findings = audit(conn, config.audio_dir, newer_than, workers, skip_probe)
    stats = {key: len(findings[key]) for key in FINDING_KEYS}
    for key in ("truncated", "unreadable"):
        for item in findings[key][:5]:
            logger.info(f"  [{key}] {item}")
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(findings, indent=2))
        logger.info(f"Full report: {report}")
    if fix:
        stats["reset"] = apply_fix(conn, findings)
    elif any(findings[key] for key in REPAIRABLE) or findings["shared_path"]:
        logger.info("Re-run with --fix to reset broken rows to pending")
    return stats
