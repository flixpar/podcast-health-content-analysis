"""Export completed, transcript-free audio as a transferable tar batch.

The download stage writes ``.part`` files and only records the final path after
an atomic rename. Selecting database rows whose audio download is complete
therefore gives this stage a safe snapshot while downloads continue.

Completed manifests live outside the archives and form an append-only export
ledger. They deliberately do not use SQLite: creating a batch can take hours,
and the downloader must remain the database's only writer during that time.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import shutil
import sqlite3
import tarfile
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from tqdm import tqdm

from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.batches import (AUDIO_BATCH_SCHEMA_VERSION, HashingReader,
                                      HashingWriter, add_bytes, atomic_write,
                                      tar_info)
from podcast_pipeline.config import PROJECT_ROOT, Config

logger = logging.getLogger(__name__)

BYTES_PER_GB = 1_000_000_000


class BatchExportError(RuntimeError):
    """A batch cannot be created without risking an incomplete result."""


@dataclass(frozen=True)
class Candidate:
    episode_id: int
    podcast_id: int
    podcast_title: str
    episode_title: str
    episode_guid: str | None
    published_date: str | None
    duration_seconds: int | None
    episode_status: str
    source_path: Path
    source_relative_path: str | None
    archive_path: str
    size_bytes: int
    mtime_ns: int
    sha256: str | None = None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _source_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _already_exported_episode_ids(manifest_dir: Path) -> set[int]:
    exported: set[int] = set()
    if not manifest_dir.exists():
        return exported
    for path in sorted(manifest_dir.glob("*.jsonl")):
        line_number = 0
        try:
            with path.open(encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    record = json.loads(line)
                    if record.get("record_type") == "episode":
                        exported.add(int(record["episode_id"]))
        except (OSError, ValueError, KeyError) as exc:
            raise BatchExportError(
                f"Cannot read completed batch manifest {path} at line {line_number}: {exc}"
            ) from exc
    return exported


def eligible_candidates(config: Config, conn: sqlite3.Connection,
                        exported_ids: set[int]) -> tuple[list[Candidate], dict[str, int]]:
    """Return usable snapshot candidates and counts for rows rejected on disk."""
    rows = conn.execute("""
        SELECT e.id, e.podcast_id, p.title AS podcast_title, e.title AS episode_title,
               e.episode_guid, e.published_date, e.duration_seconds, e.status,
               e.audio_file_path
        FROM episodes e
        JOIN podcasts p ON p.id = e.podcast_id
        WHERE e.status IN ('downloaded', 'error')
          AND e.audio_file_path IS NOT NULL AND e.audio_file_path != ''
          AND (e.transcript_file_path IS NULL OR e.transcript_file_path = '')
          AND NOT EXISTS (SELECT 1 FROM transcripts t WHERE t.episode_id = e.id)
        ORDER BY e.id
    """).fetchall()

    rejected = {"already_exported": 0, "missing": 0, "not_regular": 0, "too_small": 0}
    candidates: list[Candidate] = []
    for row in rows:
        episode_id = int(row["id"])
        if episode_id in exported_ids:
            rejected["already_exported"] += 1
            continue
        source = _source_path(row["audio_file_path"])
        try:
            stat = source.stat()
        except FileNotFoundError:
            rejected["missing"] += 1
            continue
        if not source.is_file():
            rejected["not_regular"] += 1
            continue
        if stat.st_size < MIN_AUDIO_BYTES:
            rejected["too_small"] += 1
            continue
        try:
            relative = source.relative_to(config.audio_dir).as_posix()
        except ValueError:
            relative = None
        suffix = source.suffix.lower() or ".audio"
        candidates.append(Candidate(
            episode_id=episode_id,
            podcast_id=int(row["podcast_id"]),
            podcast_title=row["podcast_title"],
            episode_title=row["episode_title"],
            episode_guid=row["episode_guid"],
            published_date=row["published_date"],
            duration_seconds=row["duration_seconds"],
            episode_status=row["status"],
            source_path=source,
            source_relative_path=relative,
            archive_path=f"audio/episode_{episode_id}{suffix}",
            size_bytes=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
        ))
    return candidates, rejected


def select_batch(candidates: list[Candidate], target_bytes: int) -> list[Candidate]:
    """Greedily fill up to the target, continuing past files that do not fit."""
    selected: list[Candidate] = []
    used = 0
    for candidate in candidates:
        if candidate.size_bytes <= target_bytes - used:
            selected.append(candidate)
            used += candidate.size_bytes
    return selected


def _episode_record(candidate: Candidate) -> dict:
    if candidate.sha256 is None:
        raise BatchExportError(f"Episode {candidate.episode_id} was not hashed")
    return {
        "record_type": "episode",
        "episode_id": candidate.episode_id,
        "podcast_id": candidate.podcast_id,
        "podcast_title": candidate.podcast_title,
        "episode_title": candidate.episode_title,
        "episode_guid": candidate.episode_guid,
        "published_date": candidate.published_date,
        "duration_seconds": candidate.duration_seconds,
        "episode_status_at_export": candidate.episode_status,
        "archive_path": candidate.archive_path,
        "source_relative_path": candidate.source_relative_path,
        "size_bytes": candidate.size_bytes,
        "sha256": candidate.sha256,
    }


def _manifest_bytes(batch_record: dict, candidates: list[Candidate]) -> bytes:
    records = [batch_record, *(_episode_record(candidate) for candidate in candidates)]
    return b"".join(
        (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        for record in records
    )


def _readme_bytes(batch_id: str) -> bytes:
    return f"""Podcast transcription audio batch: {batch_id}

Contents
--------
- audio/episode_<database-id>.<ext>: completed podcast audio.
- manifest.jsonl: one batch record followed by one episode record per audio file.
  Each episode record contains its database episode ID, metadata, byte size, and SHA-256.

The outer .sha256 sidecar verifies the tar after transfer:
    sha256sum -c {batch_id}.tar.sha256

Extract without special software:
    tar -xf {batch_id}.tar

The manifest is the transcription job list and the episode_id is the stable key
to use when returning transcripts to the source pipeline.
""".encode("utf-8")


def _create_archive(partial_path: Path, batch_id: str, created_at: datetime,
                    target_bytes: int, selected: list[Candidate]) -> tuple[list[Candidate], bytes, str]:
    """Stream a tar while hashing both every source member and the whole tar."""
    completed: list[Candidate] = []
    try:
        with partial_path.open("xb") as raw:
            writer = HashingWriter(raw)
            # Streaming tar mode never seeks, so writer.hasher is the exact
            # checksum of the final archive without a second 250 GB read.
            with tarfile.open(fileobj=writer, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                root = f"{batch_id}/"
                with tqdm(total=sum(item.size_bytes for item in selected), desc="Exporting batch",
                          unit="B", unit_scale=True, unit_divisor=1000) as progress:
                    for candidate in selected:
                        before = candidate.source_path.stat()
                        if (before.st_size != candidate.size_bytes
                                or before.st_mtime_ns != candidate.mtime_ns):
                            raise BatchExportError(
                                f"Source changed after selection: {candidate.source_path}"
                            )
                        with candidate.source_path.open("rb") as source:
                            opened = os.fstat(source.fileno())
                            if opened.st_size != candidate.size_bytes:
                                raise BatchExportError(
                                    f"Source changed while opening: {candidate.source_path}"
                                )
                            reader = HashingReader(source)
                            tar.addfile(
                                tar_info(root + candidate.archive_path,
                                         candidate.size_bytes, int(opened.st_mtime)),
                                reader,
                            )
                            after = os.fstat(source.fileno())
                        if (after.st_size != opened.st_size
                                or after.st_mtime_ns != opened.st_mtime_ns
                                or after.st_ino != opened.st_ino
                                or after.st_dev != opened.st_dev):
                            raise BatchExportError(
                                f"Source changed while archiving: {candidate.source_path}"
                            )
                        completed.append(replace(candidate, sha256=reader.hasher.hexdigest()))
                        progress.update(candidate.size_bytes)

                batch_record = {
                    "record_type": "batch",
                    "schema_version": AUDIO_BATCH_SCHEMA_VERSION,
                    "batch_id": batch_id,
                    "created_at": created_at.isoformat(),
                    "target_audio_bytes": target_bytes,
                    "audio_bytes": sum(item.size_bytes for item in completed),
                    "episode_count": len(completed),
                    "selection_order": "episode_id_ascending_greedy",
                }
                manifest = _manifest_bytes(batch_record, completed)
                add_bytes(tar, root + "manifest.jsonl", manifest, int(created_at.timestamp()))
                add_bytes(tar, root + "README.txt", _readme_bytes(batch_id),
                          int(created_at.timestamp()))
            raw.flush()
            os.fsync(raw.fileno())
            archive_sha256 = writer.hasher.hexdigest()
    except BaseException:
        partial_path.unlink(missing_ok=True)
        raise
    return completed, manifest, archive_sha256


def _estimated_tar_bytes(selected: list[Candidate]) -> int:
    # 512-byte header + payload rounded to 512 for each audio member, generous
    # manifest/README allowance, and the tar end blocks/record padding.
    audio = sum(512 + ((item.size_bytes + 511) // 512) * 512 for item in selected)
    return audio + max(64 * 1024, len(selected) * 1024)


def _ensure_destination_space(config: Config, output_dir: Path, required_bytes: int) -> None:
    free = shutil.disk_usage(output_dir).free
    reserve = 0
    try:
        if os.stat(output_dir).st_dev == os.stat(config.audio_dir).st_dev:
            reserve = int(config.download.min_free_gb * 1024 ** 3)
    except FileNotFoundError:
        pass
    if free < required_bytes + reserve:
        raise BatchExportError(
            f"Not enough free space in {output_dir}: need {required_bytes + reserve:,} bytes "
            f"({required_bytes:,} for the tar and {reserve:,} reserved), have {free:,}"
        )


def run(config: Config, conn: sqlite3.Connection, output_dir: Path,
        target_gb: float | None = None, include_exported: bool = False,
        dry_run: bool = False) -> dict:
    target_gb = config.batch_export.target_size_gb if target_gb is None else target_gb
    if target_gb <= 0:
        raise BatchExportError("target_gb must be greater than zero")
    target_bytes = int(target_gb * BYTES_PER_GB)
    manifest_dir = config.batch_export_dir / "manifests"
    lock_path = config.batch_export_dir / "export.lock"

    def select() -> tuple[list[Candidate], dict[str, int], int]:
        exported_ids = set() if include_exported else _already_exported_episode_ids(manifest_dir)
        candidates, rejected = eligible_candidates(config, conn, exported_ids)
        return select_batch(candidates, target_bytes), rejected, len(candidates)

    if dry_run:
        selected, rejected, eligible = select()
        return {
            "dry_run": True,
            "target_gb": target_gb,
            "target_audio_bytes": target_bytes,
            "eligible": eligible,
            "selected": len(selected),
            "selected_audio_bytes": sum(item.size_bytes for item in selected),
            "not_selected_for_size": eligible - len(selected),
            "rejected": rejected,
            "would_write_to": str(output_dir),
        }

    config.batch_export_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BatchExportError("Another audio batch export is already running") from exc

        # Select only after taking the lock so two exporters cannot reserve the
        # same completed-manifest snapshot.
        selected, rejected, eligible = select()
        if not selected:
            return {
                "dry_run": False,
                "target_gb": target_gb,
                "eligible": eligible,
                "selected": 0,
                "selected_audio_bytes": 0,
                "not_selected_for_size": eligible,
                "rejected": rejected,
                "archive": None,
            }

        _ensure_destination_space(config, output_dir, _estimated_tar_bytes(selected))
        created_at = _utc_now()
        batch_id = f"audio-batch-{created_at:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
        final_path = output_dir / f"{batch_id}.tar"
        partial_path = output_dir / f".{batch_id}.tar.partial"
        sidecar_path = output_dir / f"{batch_id}.tar.sha256"
        registry_path = manifest_dir / f"{batch_id}.jsonl"

        logger.info("Exporting %d episodes (%.3f GB) to %s", len(selected),
                    sum(item.size_bytes for item in selected) / BYTES_PER_GB, final_path)
        completed, manifest, archive_sha256 = _create_archive(
            partial_path, batch_id, created_at, target_bytes, selected,
        )
        partial_path.replace(final_path)
        atomic_write(sidecar_path,
                     f"{archive_sha256}  {final_path.name}\n".encode("ascii"))
        # This final atomic write is the commit point. Only completed registry
        # manifests exclude episodes from future batches.
        atomic_write(registry_path, manifest)

        result = {
            "dry_run": False,
            "batch_id": batch_id,
            "target_gb": target_gb,
            "eligible": eligible,
            "selected": len(completed),
            "selected_audio_bytes": sum(item.size_bytes for item in completed),
            "not_selected_for_size": eligible - len(completed),
            "archive_bytes": final_path.stat().st_size,
            "archive_sha256": archive_sha256,
            "archive": str(final_path),
            "checksum": str(sidecar_path),
            "registry_manifest": str(registry_path),
            "rejected": rejected,
        }
        logger.info("Audio batch complete: %s", result)
        return result
