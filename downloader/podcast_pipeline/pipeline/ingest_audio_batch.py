"""Prepare and verify a transferred audio batch on a transcription server."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from podcast_pipeline.batches import (BatchFormatError, atomic_write,
                                      checksum_from_sidecar, load_audio_manifest,
                                      load_audio_manifest_bytes,
                                      read_root_manifest_from_tar,
                                      stage_verified_archive,
                                      validate_audio_batch_directory)


class AudioBatchIngestError(RuntimeError):
    pass


def run(archive_path: Path, workspace_dir: Path, checksum_path: Path | None = None,
        skip_archive_checksum: bool = False) -> dict:
    archive_path = Path(archive_path).expanduser()
    workspace_dir = Path(workspace_dir).expanduser()
    if not archive_path.is_file():
        raise AudioBatchIngestError(f"Audio batch archive not found: {archive_path}")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    root_name, manifest_payload = read_root_manifest_from_tar(archive_path)
    preview_manifest = load_audio_manifest_bytes(manifest_payload)
    if root_name != preview_manifest.batch_id:
        raise BatchFormatError(
            f"Tar root {root_name!r} does not match batch_id {preview_manifest.batch_id!r}"
        )
    existing_dir = workspace_dir / preview_manifest.batch_id
    if existing_dir.exists():
        existing_manifest = validate_audio_batch_directory(existing_dir)
        if existing_manifest.sha256 != preview_manifest.sha256:
            raise AudioBatchIngestError(
                f"Existing batch directory has a different manifest: {existing_dir}"
            )
        receipt_path = existing_dir / "ingest_receipt.json"
        if not receipt_path.exists():
            raise AudioBatchIngestError(
                f"Existing batch has no ingest receipt and cannot be trusted as prepared: {existing_dir}"
            )
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("audio_manifest_sha256") != existing_manifest.sha256:
            raise AudioBatchIngestError(
                "Existing batch receipt does not match its audio manifest"
            )
        expected_archive_sha = checksum_from_sidecar(
            archive_path, checksum_path, skip_archive_checksum,
        )
        if (expected_archive_sha is not None
                and receipt.get("archive_sha256") != expected_archive_sha):
            raise AudioBatchIngestError(
                "Existing batch receipt does not match the transferred archive checksum"
            )
        return {
            "batch_id": existing_manifest.batch_id,
            "batch_dir": str(existing_dir),
            "episodes": len(existing_manifest.episodes),
            "audio_bytes": sum(item.size_bytes for item in existing_manifest.episodes.values()),
            "archive_sha256": receipt.get("archive_sha256"),
            "audio_manifest_sha256": existing_manifest.sha256,
            "already_prepared": True,
        }
    free = shutil.disk_usage(workspace_dir).free
    if free < archive_path.stat().st_size:
        raise AudioBatchIngestError(
            f"Not enough free space in {workspace_dir}: need at least "
            f"{archive_path.stat().st_size:,} bytes, have {free:,}"
        )

    staged = stage_verified_archive(
        archive_path, workspace_dir,
        allowed_exact={"manifest.jsonl", "README.txt"}, allowed_prefix="audio/",
        checksum_path=checksum_path, skip_archive_checksum=skip_archive_checksum,
    )
    try:
        manifest_member = staged.members.get("manifest.jsonl")
        if manifest_member is None:
            raise BatchFormatError("Audio batch has no manifest.jsonl")
        manifest = load_audio_manifest(staged.stage_dir / "manifest.jsonl")
        if staged.root_name != manifest.batch_id:
            raise BatchFormatError(
                f"Tar root {staged.root_name!r} does not match batch_id {manifest.batch_id!r}"
            )
        expected_paths = {episode.archive_path for episode in manifest.episodes.values()}
        actual_paths = {path for path in staged.members if path.startswith("audio/")}
        if actual_paths != expected_paths:
            missing = sorted(expected_paths - actual_paths)[:10]
            extra = sorted(actual_paths - expected_paths)[:10]
            raise BatchFormatError(f"Audio members do not match manifest; missing={missing}, extra={extra}")
        for episode in manifest.episodes.values():
            member = staged.members[episode.archive_path]
            if member.size_bytes != episode.size_bytes or member.sha256 != episode.sha256:
                raise BatchFormatError(
                    f"Audio integrity mismatch for episode {episode.episode_id}: "
                    f"{episode.archive_path}"
                )

        final_dir = workspace_dir / manifest.batch_id
        if final_dir.exists():
            raise AudioBatchIngestError(
                f"Destination batch already exists: {final_dir}. Remove the transferred tar if "
                "this batch has already been prepared."
            )
        receipt = {
            "record_type": "audio_batch_ingest_receipt",
            "schema_version": 1,
            "batch_id": manifest.batch_id,
            "ingested_at": datetime.now(UTC).isoformat(),
            "source_archive": archive_path.name,
            "archive_sha256": staged.archive_sha256,
            "audio_manifest_sha256": manifest.sha256,
            "episode_count": len(manifest.episodes),
            "audio_bytes": sum(item.size_bytes for item in manifest.episodes.values()),
        }
        atomic_write(staged.stage_dir / "ingest_receipt.json",
                     (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
        (staged.stage_dir / "transcripts").mkdir()
        staged.stage_dir.replace(final_dir)
        return {
            "batch_id": manifest.batch_id,
            "batch_dir": str(final_dir),
            "episodes": len(manifest.episodes),
            "audio_bytes": sum(item.size_bytes for item in manifest.episodes.values()),
            "archive_sha256": staged.archive_sha256,
            "audio_manifest_sha256": manifest.sha256,
            "already_prepared": False,
        }
    except BaseException:
        shutil.rmtree(staged.stage_dir, ignore_errors=True)
        raise
