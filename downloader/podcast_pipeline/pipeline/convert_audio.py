"""Re-encode the existing MP3 archive to Opus/OGG.

Each file is converted, verified against the source duration, recorded in
the database, and only then is the source deleted -- in that order, so an
interruption can never leave a deleted original with no record of its
replacement.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from podcast_pipeline import db
from podcast_pipeline.audio.disk import DiskSpaceError, ensure_free_space
from podcast_pipeline.audio.ffmpeg import EncodeError, check_conversion, encode_opus
from podcast_pipeline.config import Config

logger = logging.getLogger(__name__)

# Tighter than the download floor: a conversion frees space once it finishes.
MIN_FREE_GB = 20.0


@dataclass
class Candidate:
    episode_id: int
    source: Path
    size_mb: float

    @property
    def target(self) -> Path:
        return self.source.with_suffix(".ogg")


@dataclass
class Conversion:
    candidate: Candidate
    compressed_mb: float
    reused: bool   # a complete .ogg from an earlier interrupted run was already there


def candidates(conn: sqlite3.Connection, min_size_mb: float, reconcile_only: bool) -> list[Candidate]:
    rows = conn.execute("""
        SELECT id, audio_file_path FROM episodes
        WHERE audio_file_path IS NOT NULL AND is_compressed = 0 AND status != 'error'
    """).fetchall()
    found = []
    for row in rows:
        source = Path(row["audio_file_path"])
        if not source.exists():
            logger.warning(f"Episode {row['id']}: file missing on disk: {source}")
            continue
        size_mb = source.stat().st_size / 1024 ** 2
        candidate = Candidate(row["id"], source, size_mb)
        if reconcile_only:
            if not candidate.target.exists():
                continue
        elif size_mb < min_size_mb:
            continue
        found.append(candidate)
    return found


def convert(candidate: Candidate, bitrate: str) -> Conversion:
    """Produce a verified .ogg for ``candidate``, reusing one if it is already complete."""
    target = candidate.target
    if target.exists():
        reason = check_conversion(candidate.source, target)
        if reason is None:
            return Conversion(candidate, target.stat().st_size / 1024 ** 2, reused=True)
        logger.warning(f"Discarding bad earlier conversion {target.name}: {reason}")
        target.unlink()

    ensure_free_space(target.parent, MIN_FREE_GB)
    encode_opus(candidate.source, target, bitrate=bitrate)
    return Conversion(candidate, target.stat().st_size / 1024 ** 2, reused=False)


def run(config: Config, conn: sqlite3.Connection, threshold_mb: float | None = None,
        reconcile_only: bool = False, workers: int = 4, limit: int | None = None,
        dry_run: bool = False, keep_original: bool | None = None) -> dict:
    compression = config.audio_compression
    threshold_mb = compression.size_threshold_mb if threshold_mb is None else threshold_mb
    keep_original = compression.keep_original if keep_original is None else keep_original

    todo = candidates(conn, threshold_mb, reconcile_only)
    if limit:
        todo = todo[:limit]
    total_mb = sum(c.size_mb for c in todo)
    logger.info(f"{len(todo)} files to convert ({total_mb / 1024:.1f} GB)"
                + (" [reconcile only]" if reconcile_only else ""))
    stats = {"total": len(todo), "converted": 0, "reused": 0, "failed": 0, "not_attempted": 0,
             "original_mb": 0.0, "compressed_mb": 0.0}
    if dry_run or not todo:
        for c in todo[:20]:
            logger.info(f"  would convert {c.source} ({c.size_mb:.1f} MB)")
        return stats

    stop = threading.Event()

    def job(candidate: Candidate) -> Conversion | None:
        if stop.is_set():
            return None
        if reconcile_only and not candidate.target.exists():
            return None
        return convert(candidate, compression.bitrate)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(job, c): c for c in todo}
        try:
            for future in tqdm(as_completed(futures), total=len(futures), desc="Converting", unit="file"):
                candidate = futures[future]
                try:
                    conversion = future.result()
                except EncodeError as e:
                    logger.error(f"Episode {candidate.episode_id}: {e}")
                    stats["failed"] += 1
                    continue
                except DiskSpaceError as e:
                    logger.error(f"Halting: {e}")
                    stop.set()
                    stats["not_attempted"] += 1
                    continue
                if conversion is None:
                    stats["not_attempted"] += 1
                    continue

                # Commit before unlinking: see module docstring.
                db.record_conversion(conn, candidate.episode_id, candidate.target,
                                     candidate.size_mb, conversion.compressed_mb)
                conn.commit()
                if not keep_original:
                    candidate.source.unlink(missing_ok=True)
                stats["reused" if conversion.reused else "converted"] += 1
                stats["original_mb"] += candidate.size_mb
                stats["compressed_mb"] += conversion.compressed_mb
        except BaseException:
            stop.set()
            pool.shutdown(wait=True, cancel_futures=True)
            raise

    if stop.is_set():
        logger.error("Stopped early on low disk space -- free space and re-run; "
                     "finished conversions are recorded and will not be redone")
    saved_gb = (stats["original_mb"] - stats["compressed_mb"]) / 1024
    logger.info(f"Conversion complete: {stats} (saved {saved_gb:.2f} GB)")
    return stats
