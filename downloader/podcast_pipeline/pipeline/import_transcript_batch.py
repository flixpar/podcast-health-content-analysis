"""Verify and import remotely generated transcripts into the source dataset."""

from __future__ import annotations

import fcntl
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from podcast_pipeline import db
from podcast_pipeline.batches import (BatchFormatError, atomic_write,
                                      load_audio_manifest,
                                      load_transcript_manifest,
                                      sha256_file, stage_verified_archive)
from podcast_pipeline.config import PROJECT_ROOT, Config
from podcast_pipeline.transcripts.store import TranscriptStore


class TranscriptBatchImportError(RuntimeError):
    pass


def _database_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _episode_rows(conn: sqlite3.Connection, episode_ids: set[int]) -> dict[int, sqlite3.Row]:
    rows: dict[int, sqlite3.Row] = {}
    ids = sorted(episode_ids)
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        placeholders = ",".join("?" for _ in chunk)
        for row in conn.execute(f"""
            SELECT e.id, e.podcast_id, e.episode_guid, e.status, e.transcript_file_path,
                   t.file_path AS registered_transcript_path, t.metadata AS transcript_metadata
            FROM episodes e
            LEFT JOIN transcripts t ON t.episode_id = e.id
            WHERE e.id IN ({placeholders})
        """, chunk):
            rows[int(row["id"])] = row
    return rows


def _validate_transcript_file(path: Path, entry, audio_episode, transcript_manifest,
                              store: TranscriptStore):
    try:
        transcript = store.load(path)
    except Exception as exc:
        raise BatchFormatError(f"Cannot read returned transcript {path}: {exc}") from exc
    metadata = transcript.metadata
    episode_id = entry.episode_id
    if transcript.episode_id != episode_id:
        raise BatchFormatError(
            f"Returned transcript {path} says episode {transcript.episode_id}, expected {episode_id}"
        )
    expected_metadata = {
        "source": "asr",
        "model": entry.model,
        "source_audio_batch_id": transcript_manifest.source_audio_batch_id,
        "source_audio_manifest_sha256": transcript_manifest.source_audio_manifest_sha256,
        "source_audio_sha256": audio_episode.sha256,
    }
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            raise BatchFormatError(
                f"Returned transcript for episode {episode_id} has {key}={metadata.get(key)!r}, "
                f"expected {expected!r}"
            )
    ends = [segment.end for segment in transcript.segments if segment.end is not None]
    duration = max(ends) if ends else None
    has_timestamps = any(segment.start is not None for segment in transcript.segments)
    if len(transcript.text.split()) != entry.word_count:
        raise BatchFormatError(f"Word count mismatch for returned episode {episode_id}")
    if duration != entry.duration_seconds:
        raise BatchFormatError(f"Duration mismatch for returned episode {episode_id}")
    if has_timestamps != entry.has_timestamps:
        raise BatchFormatError(f"Timestamp flag mismatch for returned episode {episode_id}")
    return transcript


def run(config: Config, conn: sqlite3.Connection, archive_path: Path,
        checksum_path: Path | None = None, skip_archive_checksum: bool = False,
        dry_run: bool = False) -> dict:
    archive_path = Path(archive_path).expanduser()
    if not archive_path.is_file():
        raise TranscriptBatchImportError(f"Transcript batch archive not found: {archive_path}")
    imports_dir = config.batch_export_dir / "imports"
    staging_dir = imports_dir / "staging"
    imports_dir.mkdir(parents=True, exist_ok=True)
    lock = (imports_dir / "import.lock").open("a+b")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        lock.close()
        raise TranscriptBatchImportError("Another transcript batch import is running") from exc
    try:
        staged = stage_verified_archive(
            archive_path, staging_dir,
            allowed_exact={"manifest.jsonl", "README.txt"}, allowed_prefix="transcripts/",
            checksum_path=checksum_path, skip_archive_checksum=skip_archive_checksum,
        )
    except BaseException:
        lock.close()
        raise
    try:
        if "manifest.jsonl" not in staged.members:
            raise BatchFormatError("Transcript batch has no manifest.jsonl")
        transcript_manifest = load_transcript_manifest(staged.stage_dir / "manifest.jsonl")
        if staged.root_name != transcript_manifest.transcript_batch_id:
            raise BatchFormatError(
                f"Tar root {staged.root_name!r} does not match transcript_batch_id "
                f"{transcript_manifest.transcript_batch_id!r}"
            )
        expected_paths = {entry.archive_path for entry in transcript_manifest.transcripts.values()}
        actual_paths = {path for path in staged.members if path.startswith("transcripts/")}
        if actual_paths != expected_paths:
            raise BatchFormatError(
                f"Transcript members do not match manifest; "
                f"missing={sorted(expected_paths - actual_paths)[:10]}, "
                f"extra={sorted(actual_paths - expected_paths)[:10]}"
            )
        for entry in transcript_manifest.transcripts.values():
            member = staged.members[entry.archive_path]
            if member.size_bytes != entry.size_bytes or member.sha256 != entry.sha256:
                raise BatchFormatError(
                    f"Returned transcript integrity mismatch for episode {entry.episode_id}"
                )

        audio_manifest_path = (
            config.batch_export_dir / "manifests" /
            f"{transcript_manifest.source_audio_batch_id}.jsonl"
        )
        if not audio_manifest_path.exists():
            raise TranscriptBatchImportError(
                f"Source audio batch receipt is missing: {audio_manifest_path}. "
                "The return archive cannot be tied to this source dataset."
            )
        audio_manifest = load_audio_manifest(audio_manifest_path)
        if audio_manifest.sha256 != transcript_manifest.source_audio_manifest_sha256:
            raise BatchFormatError(
                "Returned transcripts reference a different version of the source audio manifest"
            )
        returned_ids = set(transcript_manifest.transcripts)
        missing_ids = set(transcript_manifest.header["missing_episode_ids"])
        source_ids = set(audio_manifest.episodes)
        if returned_ids | missing_ids != source_ids:
            raise BatchFormatError(
                "Returned transcript/missing episode IDs do not partition the source audio batch"
            )
        rows = _episode_rows(conn, returned_ids)
        if set(rows) != returned_ids:
            raise TranscriptBatchImportError(
                f"Source database is missing episode IDs: {sorted(returned_ids - set(rows))[:20]}"
            )

        staged_store = TranscriptStore(staged.stage_dir / "transcripts")
        validated = {}
        conflicts: list[int] = []
        already_imported: list[int] = []
        for episode_id, entry in transcript_manifest.transcripts.items():
            audio_episode = audio_manifest.episodes[episode_id]
            if entry.source_audio_sha256 != audio_episode.sha256:
                raise BatchFormatError(
                    f"Returned transcript for episode {episode_id} references different audio bytes"
                )
            row = rows[episode_id]
            if (int(row["podcast_id"]) != audio_episode.podcast_id
                    or row["episode_guid"] != audio_episode.episode_guid):
                raise TranscriptBatchImportError(
                    f"Episode identity mismatch in source database for episode {episode_id}"
                )
            path = staged.stage_dir.joinpath(*PurePosixPath(entry.archive_path).parts)
            _validate_transcript_file(
                path, entry, audio_episode, transcript_manifest, staged_store,
            )
            existing_value = row["registered_transcript_path"] or row["transcript_file_path"]
            if existing_value:
                existing = _database_path(existing_value)
                metadata = json.loads(row["transcript_metadata"] or "{}")
                if (existing.is_file() and sha256_file(existing) == entry.sha256
                        and metadata.get("source_audio_batch_id") == audio_manifest.batch_id):
                    already_imported.append(episode_id)
                    continue
                conflicts.append(episode_id)
                continue
            if row["status"] == db.EpisodeStatus.TRANSCRIBED:
                conflicts.append(episode_id)
                continue
            canonical = config.transcript_dir / f"episode_{episode_id}.jsonl.zst"
            if canonical.exists() and sha256_file(canonical) != entry.sha256:
                conflicts.append(episode_id)
                continue
            validated[episode_id] = (entry, path)

        if conflicts:
            raise TranscriptBatchImportError(
                f"Refusing to overwrite {len(conflicts)} existing/different transcripts; "
                f"episode IDs: {conflicts[:20]}"
            )
        summary = {
            "transcript_batch_id": transcript_manifest.transcript_batch_id,
            "source_audio_batch_id": audio_manifest.batch_id,
            "returned": len(returned_ids),
            "new": len(validated),
            "already_imported": len(already_imported),
            "source_batch_complete": bool(transcript_manifest.header.get("complete")),
            "source_batch_missing": int(transcript_manifest.header.get("missing_episode_count", 0)),
            "archive_sha256": staged.archive_sha256,
        }
        if dry_run:
            return {"dry_run": True, **summary}

        destination_store = TranscriptStore(
            config.transcript_dir, config.storage.transcript_compression_level,
        )
        imported = 0
        for episode_id, (entry, incoming_path) in validated.items():
            destination = destination_store.path_for(episode_id)
            atomic_write(destination, incoming_path.read_bytes())
            db.record_transcript(
                conn, episode_id, destination, entry.word_count, entry.duration_seconds,
                has_timestamps=entry.has_timestamps, has_speakers=False,
                metadata={
                    "source": "asr",
                    "model": entry.model,
                    "source_audio_batch_id": audio_manifest.batch_id,
                    "source_audio_manifest_sha256": audio_manifest.sha256,
                    "source_audio_sha256": entry.source_audio_sha256,
                    "transcript_batch_id": transcript_manifest.transcript_batch_id,
                    "remote_transcript_sha256": entry.sha256,
                },
            )
            conn.commit()
            imported += 1

        receipt = {
            "record_type": "transcript_batch_import_receipt",
            "schema_version": 1,
            "imported_at": datetime.now(UTC).isoformat(),
            **summary,
            "imported": imported,
            "transcript_manifest_sha256": transcript_manifest.sha256,
        }
        receipt_path = imports_dir / f"{transcript_manifest.transcript_batch_id}.json"
        atomic_write(receipt_path, (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
        return {"dry_run": False, **summary, "imported": imported,
                "receipt": str(receipt_path)}
    finally:
        shutil.rmtree(staged.stage_dir, ignore_errors=True)
        lock.close()
