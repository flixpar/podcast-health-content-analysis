"""Shared contracts and safe I/O for portable audio/transcript batches."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import tarfile
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

AUDIO_BATCH_SCHEMA_VERSION = 1
TRANSCRIPT_BATCH_SCHEMA_VERSION = 1
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class BatchFormatError(RuntimeError):
    """A portable batch or its integrity metadata violates the batch contract."""


@dataclass(frozen=True)
class AudioEpisode:
    episode_id: int
    podcast_id: int
    podcast_title: str
    episode_title: str
    episode_guid: str | None
    published_date: str | None
    duration_seconds: int | None
    archive_path: str
    size_bytes: int
    sha256: str
    record: dict


@dataclass(frozen=True)
class AudioBatchManifest:
    batch_id: str
    episodes: dict[int, AudioEpisode]
    header: dict
    payload: bytes
    sha256: str


@dataclass(frozen=True)
class TranscriptEntry:
    episode_id: int
    archive_path: str
    source_audio_sha256: str
    size_bytes: int
    sha256: str
    word_count: int
    duration_seconds: float | None
    has_timestamps: bool
    model: str
    record: dict


@dataclass(frozen=True)
class TranscriptBatchManifest:
    transcript_batch_id: str
    source_audio_batch_id: str
    source_audio_manifest_sha256: str
    transcripts: dict[int, TranscriptEntry]
    header: dict
    payload: bytes
    sha256: str


@dataclass(frozen=True)
class ExtractedMember:
    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class StagedArchive:
    root_name: str
    stage_dir: Path
    members: dict[str, ExtractedMember]
    archive_sha256: str


class HashingReader:
    def __init__(self, raw):
        self.raw = raw
        self.hasher = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        data = self.raw.read(size)
        self.hasher.update(data)
        return data


class HashingWriter:
    def __init__(self, raw):
        self.raw = raw
        self.hasher = hashlib.sha256()

    def write(self, data: bytes) -> int:
        self.hasher.update(data)
        return self.raw.write(data)


def tar_info(name: str, size: int, mtime: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mtime = mtime
    info.mode = 0o644
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def add_bytes(tar: tarfile.TarFile, name: str, data: bytes, mtime: int) -> None:
    tar.addfile(tar_info(name, len(data), mtime), io.BytesIO(data))


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checksum_from_sidecar(archive_path: Path, checksum_path: Path | None,
                          skip_checksum: bool) -> str | None:
    if skip_checksum:
        return None
    checksum_path = checksum_path or archive_path.with_name(archive_path.name + ".sha256")
    if not checksum_path.exists():
        raise BatchFormatError(
            f"Archive checksum is required but missing: {checksum_path}. "
            "Transfer the .sha256 sidecar or explicitly use --skip-archive-checksum."
        )
    matches = []
    for line in checksum_path.read_text(encoding="ascii").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == archive_path.name:
            matches.append(parts[0].lower())
    if len(matches) != 1 or not SHA256_RE.fullmatch(matches[0]):
        raise BatchFormatError(
            f"Expected exactly one valid SHA-256 entry for {archive_path.name} in {checksum_path}"
        )
    return matches[0]


def _records(payload: bytes, label: str) -> list[dict]:
    records = []
    try:
        text = payload.decode("utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            if line:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise BatchFormatError(f"{label} line {line_number} is not a JSON object")
                records.append(record)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BatchFormatError(f"Invalid {label}: {exc}") from exc
    if not records:
        raise BatchFormatError(f"{label} is empty")
    return records


def _safe_relative(value: object, prefix: str, episode_id: int) -> str:
    if not isinstance(value, str):
        raise BatchFormatError(f"Episode {episode_id} has no string archive_path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise BatchFormatError(f"Unsafe archive_path for episode {episode_id}: {value!r}")
    if not value.startswith(prefix) or len(path.parts) != 2:
        raise BatchFormatError(f"Unexpected archive_path for episode {episode_id}: {value!r}")
    return value


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BatchFormatError(f"{label} must be a positive integer")
    return value


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise BatchFormatError(f"{label} must be a lowercase SHA-256")
    return value


def load_audio_manifest_bytes(payload: bytes) -> AudioBatchManifest:
    records = _records(payload, "audio batch manifest")
    header = records[0]
    if header.get("record_type") != "batch":
        raise BatchFormatError("Audio manifest must start with a batch record")
    if header.get("schema_version") != AUDIO_BATCH_SCHEMA_VERSION:
        raise BatchFormatError(f"Unsupported audio batch schema: {header.get('schema_version')!r}")
    batch_id = header.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id:
        raise BatchFormatError("Audio manifest has no batch_id")

    episodes: dict[int, AudioEpisode] = {}
    paths: set[str] = set()
    for record in records[1:]:
        if record.get("record_type") != "episode":
            raise BatchFormatError("Audio manifest contains a non-episode detail record")
        episode_id = _positive_int(record.get("episode_id"), "episode_id")
        if episode_id in episodes:
            raise BatchFormatError(f"Duplicate episode_id in audio manifest: {episode_id}")
        archive_path = _safe_relative(record.get("archive_path"), "audio/", episode_id)
        if archive_path in paths:
            raise BatchFormatError(f"Duplicate archive_path in audio manifest: {archive_path}")
        paths.add(archive_path)
        size_bytes = _positive_int(record.get("size_bytes"), f"episode {episode_id} size_bytes")
        digest = _sha256(record.get("sha256"), f"episode {episode_id} sha256")
        podcast_id = _positive_int(record.get("podcast_id"), f"episode {episode_id} podcast_id")
        episodes[episode_id] = AudioEpisode(
            episode_id=episode_id,
            podcast_id=podcast_id,
            podcast_title=str(record.get("podcast_title", "")),
            episode_title=str(record.get("episode_title", "")),
            episode_guid=record.get("episode_guid"),
            published_date=record.get("published_date"),
            duration_seconds=record.get("duration_seconds"),
            archive_path=archive_path,
            size_bytes=size_bytes,
            sha256=digest,
            record=record,
        )
    if header.get("episode_count") != len(episodes):
        raise BatchFormatError("Audio manifest episode_count does not match its records")
    if header.get("audio_bytes") != sum(item.size_bytes for item in episodes.values()):
        raise BatchFormatError("Audio manifest audio_bytes does not match its records")
    return AudioBatchManifest(batch_id, episodes, header, payload,
                              hashlib.sha256(payload).hexdigest())


def load_audio_manifest(path: Path) -> AudioBatchManifest:
    return load_audio_manifest_bytes(Path(path).read_bytes())


def validate_audio_batch_directory(batch_dir: Path,
                                   verify_hashes: bool = False) -> AudioBatchManifest:
    batch_dir = Path(batch_dir)
    manifest = load_audio_manifest(batch_dir / "manifest.jsonl")
    if batch_dir.name != manifest.batch_id:
        raise BatchFormatError(
            f"Batch directory name {batch_dir.name!r} does not match {manifest.batch_id!r}"
        )
    for episode in manifest.episodes.values():
        path = batch_dir.joinpath(*PurePosixPath(episode.archive_path).parts)
        try:
            stat = path.stat()
        except FileNotFoundError as exc:
            raise BatchFormatError(f"Audio missing for episode {episode.episode_id}: {path}") from exc
        if not path.is_file() or stat.st_size != episode.size_bytes:
            raise BatchFormatError(
                f"Audio size/type mismatch for episode {episode.episode_id}: {path}"
            )
        if verify_hashes and sha256_file(path) != episode.sha256:
            raise BatchFormatError(f"Audio SHA-256 mismatch for episode {episode.episode_id}: {path}")
    return manifest


def load_transcript_manifest_bytes(payload: bytes) -> TranscriptBatchManifest:
    records = _records(payload, "transcript batch manifest")
    header = records[0]
    if header.get("record_type") != "transcript_batch":
        raise BatchFormatError("Transcript manifest must start with a transcript_batch record")
    if header.get("schema_version") != TRANSCRIPT_BATCH_SCHEMA_VERSION:
        raise BatchFormatError(
            f"Unsupported transcript batch schema: {header.get('schema_version')!r}"
        )
    transcript_batch_id = header.get("transcript_batch_id")
    source_batch_id = header.get("source_audio_batch_id")
    if not isinstance(transcript_batch_id, str) or not transcript_batch_id:
        raise BatchFormatError("Transcript manifest has no transcript_batch_id")
    if not isinstance(source_batch_id, str) or not source_batch_id:
        raise BatchFormatError("Transcript manifest has no source_audio_batch_id")
    source_manifest_sha = _sha256(header.get("source_audio_manifest_sha256"),
                                  "source_audio_manifest_sha256")

    transcripts: dict[int, TranscriptEntry] = {}
    paths: set[str] = set()
    for record in records[1:]:
        if record.get("record_type") != "transcript":
            raise BatchFormatError("Transcript manifest contains a non-transcript detail record")
        episode_id = _positive_int(record.get("episode_id"), "episode_id")
        if episode_id in transcripts:
            raise BatchFormatError(f"Duplicate episode_id in transcript manifest: {episode_id}")
        archive_path = _safe_relative(record.get("archive_path"), "transcripts/", episode_id)
        if archive_path in paths:
            raise BatchFormatError(f"Duplicate archive_path in transcript manifest: {archive_path}")
        paths.add(archive_path)
        model = record.get("model")
        if not isinstance(model, str) or not model:
            raise BatchFormatError(f"Transcript {episode_id} has no model")
        duration = record.get("duration_seconds")
        if duration is not None and not isinstance(duration, (int, float)):
            raise BatchFormatError(f"Transcript {episode_id} has invalid duration_seconds")
        word_count = record.get("word_count")
        if isinstance(word_count, bool) or not isinstance(word_count, int) or word_count < 0:
            raise BatchFormatError(f"Transcript {episode_id} has invalid word_count")
        if not isinstance(record.get("has_timestamps"), bool):
            raise BatchFormatError(f"Transcript {episode_id} has invalid has_timestamps")
        transcripts[episode_id] = TranscriptEntry(
            episode_id=episode_id,
            archive_path=archive_path,
            source_audio_sha256=_sha256(record.get("source_audio_sha256"),
                                        f"transcript {episode_id} source_audio_sha256"),
            size_bytes=_positive_int(record.get("size_bytes"),
                                     f"transcript {episode_id} size_bytes"),
            sha256=_sha256(record.get("sha256"), f"transcript {episode_id} sha256"),
            word_count=word_count,
            duration_seconds=float(duration) if duration is not None else None,
            has_timestamps=bool(record.get("has_timestamps")),
            model=model,
            record=record,
        )
    if header.get("transcript_count") != len(transcripts):
        raise BatchFormatError("Transcript manifest transcript_count does not match its records")
    missing_ids = header.get("missing_episode_ids")
    if (not isinstance(missing_ids, list)
            or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
                   for value in missing_ids)
            or len(set(missing_ids)) != len(missing_ids)):
        raise BatchFormatError("Transcript manifest has invalid missing_episode_ids")
    if set(missing_ids) & set(transcripts):
        raise BatchFormatError("Transcript and missing episode IDs overlap")
    if header.get("missing_episode_count") != len(missing_ids):
        raise BatchFormatError("Transcript manifest missing_episode_count is inconsistent")
    source_count = header.get("source_episode_count")
    if source_count != len(transcripts) + len(missing_ids):
        raise BatchFormatError("Transcript manifest source_episode_count is inconsistent")
    if header.get("complete") is not (not missing_ids):
        raise BatchFormatError("Transcript manifest complete flag is inconsistent")
    return TranscriptBatchManifest(
        transcript_batch_id, source_batch_id, source_manifest_sha, transcripts,
        header, payload, hashlib.sha256(payload).hexdigest(),
    )


def load_transcript_manifest(path: Path) -> TranscriptBatchManifest:
    return load_transcript_manifest_bytes(Path(path).read_bytes())


def _safe_tar_name(name: str) -> tuple[str, str]:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or len(path.parts) < 2:
        raise BatchFormatError(f"Unsafe or unrooted tar member path: {name!r}")
    return path.parts[0], PurePosixPath(*path.parts[1:]).as_posix()


def read_root_manifest_from_tar(archive_path: Path) -> tuple[str, bytes]:
    """Read only tar headers plus the root manifest, without copying payload files."""
    root_name: str | None = None
    manifest_member: tarfile.TarInfo | None = None
    with tarfile.open(archive_path, mode="r:*") as tar:
        for member in tar:
            if not member.isfile():
                raise BatchFormatError(
                    f"Only regular files are permitted in batches: {member.name!r}"
                )
            member_root, relative = _safe_tar_name(member.name)
            if root_name is None:
                root_name = member_root
            elif member_root != root_name:
                raise BatchFormatError("Batch tar contains more than one root directory")
            if relative == "manifest.jsonl":
                if manifest_member is not None:
                    raise BatchFormatError("Batch tar contains multiple root manifests")
                manifest_member = member
        if root_name is None or manifest_member is None:
            raise BatchFormatError("Batch tar has no root manifest.jsonl")
        stream = tar.extractfile(manifest_member)
        if stream is None:
            raise BatchFormatError("Cannot read batch manifest.jsonl")
        return root_name, stream.read()


def stage_verified_archive(archive_path: Path, staging_parent: Path,
                           allowed_exact: set[str], allowed_prefix: str,
                           checksum_path: Path | None = None,
                           skip_archive_checksum: bool = False) -> StagedArchive:
    """Safely extract and hash a tar in one sequential pass into a temporary directory."""
    archive_path = Path(archive_path)
    expected_archive_sha = checksum_from_sidecar(
        archive_path, checksum_path, skip_archive_checksum,
    )
    staging_parent.mkdir(parents=True, exist_ok=True)
    stage_dir = staging_parent / f".batch-ingest-{uuid.uuid4().hex}.partial"
    stage_dir.mkdir()
    root_name: str | None = None
    members: dict[str, ExtractedMember] = {}
    try:
        with archive_path.open("rb") as raw:
            archive_reader = HashingReader(raw)
            with tarfile.open(fileobj=archive_reader, mode="r|*") as tar:
                for member in tar:
                    if not member.isfile():
                        raise BatchFormatError(
                            f"Only regular files are permitted in batches: {member.name!r}"
                        )
                    member_root, relative = _safe_tar_name(member.name)
                    if root_name is None:
                        root_name = member_root
                    elif member_root != root_name:
                        raise BatchFormatError("Batch tar contains more than one root directory")
                    if relative not in allowed_exact and not relative.startswith(allowed_prefix):
                        raise BatchFormatError(f"Unexpected batch member: {member.name!r}")
                    if relative in members:
                        raise BatchFormatError(f"Duplicate batch member: {member.name!r}")
                    source = tar.extractfile(member)
                    if source is None:
                        raise BatchFormatError(f"Cannot read tar member: {member.name!r}")
                    target = stage_dir.joinpath(*PurePosixPath(relative).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256()
                    written = 0
                    with target.open("xb") as output:
                        while True:
                            chunk = source.read(4 * 1024 * 1024)
                            if not chunk:
                                break
                            output.write(chunk)
                            digest.update(chunk)
                            written += len(chunk)
                        output.flush()
                        os.fsync(output.fileno())
                    if written != member.size:
                        raise BatchFormatError(
                            f"Tar member size changed while reading {member.name!r}: "
                            f"expected {member.size}, got {written}"
                        )
                    members[relative] = ExtractedMember(relative, written, digest.hexdigest())
            # A streaming tar reader can stop at the end markers before the
            # record padding. Drain it so this digest covers every archive byte.
            while archive_reader.read(4 * 1024 * 1024):
                pass
            actual_archive_sha = archive_reader.hasher.hexdigest()
        if expected_archive_sha is not None and actual_archive_sha != expected_archive_sha:
            raise BatchFormatError(
                f"Archive SHA-256 mismatch: expected {expected_archive_sha}, got {actual_archive_sha}"
            )
        if root_name is None:
            raise BatchFormatError("Batch tar is empty")
        return StagedArchive(root_name, stage_dir, members, actual_archive_sha)
    except BaseException:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise
