"""Package completed remote transcripts for a verified return transfer."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import tarfile
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from tqdm import tqdm

from podcast_pipeline.batches import (TRANSCRIPT_BATCH_SCHEMA_VERSION,
                                      AudioEpisode, HashingReader, HashingWriter,
                                      add_bytes, atomic_write, tar_info,
                                      validate_audio_batch_directory)
from podcast_pipeline.pipeline.transcribe_audio_batch import validate_batch_transcript
from podcast_pipeline.transcripts.store import TranscriptStore


class TranscriptBatchExportError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptCandidate:
    episode: AudioEpisode
    path: Path
    size_bytes: int
    mtime_ns: int
    word_count: int
    duration_seconds: float | None
    has_timestamps: bool
    model: str
    sha256: str | None = None


def _manifest_bytes(header: dict, candidates: list[TranscriptCandidate]) -> bytes:
    records = [header]
    for candidate in candidates:
        if candidate.sha256 is None:
            raise TranscriptBatchExportError(
                f"Transcript for episode {candidate.episode.episode_id} was not hashed"
            )
        records.append({
            "record_type": "transcript",
            "episode_id": candidate.episode.episode_id,
            "source_audio_sha256": candidate.episode.sha256,
            "archive_path": f"transcripts/episode_{candidate.episode.episode_id}.jsonl.zst",
            "size_bytes": candidate.size_bytes,
            "sha256": candidate.sha256,
            "word_count": candidate.word_count,
            "duration_seconds": candidate.duration_seconds,
            "has_timestamps": candidate.has_timestamps,
            "model": candidate.model,
        })
    return b"".join(
        (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        for record in records
    )


def _readme_bytes(transcript_batch_id: str, source_batch_id: str) -> bytes:
    return f"""Podcast transcript return batch: {transcript_batch_id}
Source audio batch: {source_batch_id}

Transfer this .tar together with its .tar.sha256 sidecar to the source machine.
From the downloader directory, import it with:

    python -m podcast_pipeline import-transcript-batch {transcript_batch_id}.tar

manifest.jsonl binds every transcript to its episode ID, source audio checksum,
source audio manifest, ASR model, byte size, and SHA-256.
""".encode("utf-8")


def _candidates(batch_dir: Path, manifest) -> tuple[list[TranscriptCandidate], list[int]]:
    store = TranscriptStore(batch_dir / "transcripts")
    complete: list[TranscriptCandidate] = []
    missing: list[int] = []
    for episode in manifest.episodes.values():
        path = store.path_for(episode.episode_id)
        if not path.exists():
            missing.append(episode.episode_id)
            continue
        transcript = validate_batch_transcript(path, episode, manifest.batch_id, store)
        ends = [segment.end for segment in transcript.segments if segment.end is not None]
        stat = path.stat()
        complete.append(TranscriptCandidate(
            episode=episode,
            path=path,
            size_bytes=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            word_count=len(transcript.text.split()),
            duration_seconds=max(ends) if ends else None,
            has_timestamps=any(segment.start is not None for segment in transcript.segments),
            model=transcript.metadata["model"],
        ))
    return complete, missing


def _create_archive(partial_path: Path, transcript_batch_id: str, source_manifest,
                    candidates: list[TranscriptCandidate], missing_ids: list[int],
                    created_at: datetime) -> tuple[list[TranscriptCandidate], bytes, str]:
    completed: list[TranscriptCandidate] = []
    try:
        with partial_path.open("xb") as raw:
            writer = HashingWriter(raw)
            with tarfile.open(fileobj=writer, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                root = f"{transcript_batch_id}/"
                with tqdm(total=sum(item.size_bytes for item in candidates),
                          desc="Exporting transcripts", unit="B", unit_scale=True) as progress:
                    for candidate in candidates:
                        before = candidate.path.stat()
                        if (before.st_size != candidate.size_bytes
                                or before.st_mtime_ns != candidate.mtime_ns):
                            raise TranscriptBatchExportError(
                                f"Transcript changed after selection: {candidate.path}"
                            )
                        with candidate.path.open("rb") as source:
                            opened = os.fstat(source.fileno())
                            reader = HashingReader(source)
                            archive_path = (
                                f"transcripts/episode_{candidate.episode.episode_id}.jsonl.zst"
                            )
                            tar.addfile(
                                tar_info(root + archive_path, candidate.size_bytes,
                                         int(opened.st_mtime)), reader,
                            )
                            after = os.fstat(source.fileno())
                        if (after.st_size != opened.st_size
                                or after.st_mtime_ns != opened.st_mtime_ns
                                or after.st_ino != opened.st_ino
                                or after.st_dev != opened.st_dev):
                            raise TranscriptBatchExportError(
                                f"Transcript changed while archiving: {candidate.path}"
                            )
                        completed.append(replace(candidate, sha256=reader.hasher.hexdigest()))
                        progress.update(candidate.size_bytes)

                header = {
                    "record_type": "transcript_batch",
                    "schema_version": TRANSCRIPT_BATCH_SCHEMA_VERSION,
                    "transcript_batch_id": transcript_batch_id,
                    "source_audio_batch_id": source_manifest.batch_id,
                    "source_audio_manifest_sha256": source_manifest.sha256,
                    "created_at": created_at.isoformat(),
                    "source_episode_count": len(source_manifest.episodes),
                    "transcript_count": len(completed),
                    "missing_episode_count": len(missing_ids),
                    "missing_episode_ids": missing_ids,
                    "complete": not missing_ids,
                }
                manifest_bytes = _manifest_bytes(header, completed)
                timestamp = int(created_at.timestamp())
                add_bytes(tar, root + "manifest.jsonl", manifest_bytes, timestamp)
                add_bytes(tar, root + "README.txt",
                          _readme_bytes(transcript_batch_id, source_manifest.batch_id), timestamp)
            raw.flush()
            os.fsync(raw.fileno())
            archive_sha256 = writer.hasher.hexdigest()
    except BaseException:
        partial_path.unlink(missing_ok=True)
        raise
    return completed, manifest_bytes, archive_sha256


def run(batch_dir: Path, output_dir: Path, allow_partial: bool = False,
        dry_run: bool = False) -> dict:
    batch_dir = Path(batch_dir).expanduser()
    output_dir = Path(output_dir).expanduser()
    source_manifest = validate_audio_batch_directory(batch_dir)
    candidates, missing_ids = _candidates(batch_dir, source_manifest)
    summary = {
        "source_audio_batch_id": source_manifest.batch_id,
        "source_episodes": len(source_manifest.episodes),
        "transcripts": len(candidates),
        "missing": len(missing_ids),
        "complete": not missing_ids,
    }
    if dry_run:
        return {"dry_run": True, **summary, "would_write_to": str(output_dir)}
    if missing_ids and not allow_partial:
        raise TranscriptBatchExportError(
            f"Batch is not complete: {len(missing_ids)} of {len(source_manifest.episodes)} episodes "
            "have no transcript. Finish/retry transcription or explicitly use --allow-partial."
        )
    if not candidates:
        raise TranscriptBatchExportError("No completed transcripts are available to export")

    output_dir.mkdir(parents=True, exist_ok=True)
    estimated_bytes = sum(item.size_bytes + 2048 for item in candidates) + 1024 * 1024
    if shutil.disk_usage(output_dir).free < estimated_bytes:
        raise TranscriptBatchExportError(
            f"Not enough free space in {output_dir}: need approximately {estimated_bytes:,} bytes"
        )
    lock_path = batch_dir / "export-transcripts.lock"
    with lock_path.open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise TranscriptBatchExportError(
                f"Another transcript export is using {batch_dir}"
            ) from exc
        created_at = datetime.now(UTC)
        transcript_batch_id = (
            f"transcript-batch-{source_manifest.batch_id.removeprefix('audio-batch-')}-"
            f"{created_at:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
        )
        final_path = output_dir / f"{transcript_batch_id}.tar"
        partial_path = output_dir / f".{transcript_batch_id}.tar.partial"
        sidecar_path = output_dir / f"{transcript_batch_id}.tar.sha256"
        completed, manifest_bytes, archive_sha256 = _create_archive(
            partial_path, transcript_batch_id, source_manifest, candidates,
            missing_ids, created_at,
        )
        partial_path.replace(final_path)
        atomic_write(sidecar_path,
                     f"{archive_sha256}  {final_path.name}\n".encode("ascii"))
    return {
        "dry_run": False,
        **summary,
        "transcript_batch_id": transcript_batch_id,
        "archive": str(final_path),
        "archive_bytes": final_path.stat().st_size,
        "archive_sha256": archive_sha256,
        "checksum": str(sidecar_path),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
