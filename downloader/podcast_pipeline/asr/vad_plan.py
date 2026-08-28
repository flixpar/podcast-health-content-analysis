"""Validated precomputed VAD plans for remote audio batches."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from podcast_pipeline.asr.vad import SpeechDetection

VAD_PLAN_SCHEMA_VERSION = 1
_EPISODE_STEM = re.compile(r"episode_(\d+)")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class VADPlanError(ValueError):
    """A precomputed VAD plan is malformed or does not match its audio."""


@dataclass(frozen=True)
class VADPlanEpisode:
    episode_id: int
    archive_path: str
    source_audio_sha256: str
    duration_seconds: float
    speech_spans: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class PrecomputedVADPlan:
    path: Path
    sha256: str
    batch_id: str
    source_audio_manifest_sha256: str
    model: str
    batch_size: int
    min_duration_on: float
    min_duration_off: float
    episodes: dict[int, VADPlanEpisode]

    @classmethod
    def load(cls, path: str | Path) -> "PrecomputedVADPlan":
        path = Path(path).expanduser()
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise VADPlanError(f"Cannot read VAD plan {path}: {exc}") from exc
        records = []
        for line_number, line in enumerate(payload.splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise VADPlanError(
                    f"Invalid JSON in VAD plan {path} line {line_number}: {exc}"
                ) from exc
            if not isinstance(record, dict):
                raise VADPlanError(f"VAD plan {path} line {line_number} is not an object")
            records.append(record)
        if not records:
            raise VADPlanError(f"VAD plan {path} is empty")

        header = records[0]
        if header.get("record_type") != "vad_plan":
            raise VADPlanError("VAD plan must start with a vad_plan record")
        if header.get("schema_version") != VAD_PLAN_SCHEMA_VERSION:
            raise VADPlanError(
                f"Unsupported VAD plan schema: {header.get('schema_version')!r}"
            )
        batch_id = _string(header.get("batch_id"), "batch_id")
        manifest_sha256 = _digest(
            header.get("source_audio_manifest_sha256"),
            "source_audio_manifest_sha256",
        )
        model = _string(header.get("model"), "model")
        batch_size = _positive_int(header.get("batch_size"), "batch_size")
        min_duration_on = _nonnegative_float(
            header.get("min_duration_on"), "min_duration_on"
        )
        min_duration_off = _nonnegative_float(
            header.get("min_duration_off"), "min_duration_off"
        )

        episodes: dict[int, VADPlanEpisode] = {}
        for record in records[1:]:
            if record.get("record_type") != "episode":
                raise VADPlanError("VAD plan contains a non-episode detail record")
            episode_id = _positive_int(record.get("episode_id"), "episode_id")
            if episode_id in episodes:
                raise VADPlanError(f"Duplicate episode_id in VAD plan: {episode_id}")
            archive_path = _archive_path(record.get("archive_path"), episode_id)
            source_sha256 = _digest(
                record.get("source_audio_sha256"),
                f"episode {episode_id} source_audio_sha256",
            )
            duration = _positive_float(
                record.get("duration_seconds"), f"episode {episode_id} duration_seconds"
            )
            spans = _spans(record.get("speech_spans"), episode_id, duration)
            reported_speech = _nonnegative_float(
                record.get("speech_seconds"), f"episode {episode_id} speech_seconds"
            )
            actual_speech = sum(end - start for start, end in spans)
            if abs(reported_speech - actual_speech) > 0.01:
                raise VADPlanError(
                    f"Episode {episode_id} speech_seconds does not match its spans"
                )
            episodes[episode_id] = VADPlanEpisode(
                episode_id, archive_path, source_sha256, duration, spans,
            )
        if header.get("episode_count") != len(episodes):
            raise VADPlanError("VAD plan episode_count does not match its records")
        return cls(
            path=path,
            sha256=hashlib.sha256(payload).hexdigest(),
            batch_id=batch_id,
            source_audio_manifest_sha256=manifest_sha256,
            model=model,
            batch_size=batch_size,
            min_duration_on=min_duration_on,
            min_duration_off=min_duration_off,
            episodes=episodes,
        )

    def detect(self, audio_path: Path, duration_seconds: float) -> SpeechDetection:
        match = _EPISODE_STEM.fullmatch(audio_path.stem)
        if match is None:
            raise VADPlanError(
                f"Cannot identify episode id from planned audio name: {audio_path.name}"
            )
        episode_id = int(match.group(1))
        try:
            episode = self.episodes[episode_id]
        except KeyError as exc:
            raise VADPlanError(f"VAD plan has no episode {episode_id}") from exc
        if PurePosixPath(episode.archive_path).name != audio_path.name:
            raise VADPlanError(
                f"VAD plan path mismatch for episode {episode_id}: "
                f"{episode.archive_path!r} != {audio_path.name!r}"
            )
        if abs(episode.duration_seconds - duration_seconds) > 0.5:
            raise VADPlanError(
                f"VAD plan duration mismatch for episode {episode_id}: "
                f"{episode.duration_seconds:.3f}s != {duration_seconds:.3f}s"
            )
        return SpeechDetection(episode.speech_spans)

    def validate_batch(self, manifest, episode_ids: set[int]) -> None:
        if self.batch_id != manifest.batch_id:
            raise VADPlanError(
                f"VAD plan batch {self.batch_id!r} does not match {manifest.batch_id!r}"
            )
        if self.source_audio_manifest_sha256 != manifest.sha256:
            raise VADPlanError("VAD plan belongs to a different audio manifest")
        missing = episode_ids - self.episodes.keys()
        if missing:
            preview = ", ".join(map(str, sorted(missing)[:10]))
            raise VADPlanError(f"VAD plan is missing queued episodes: {preview}")
        for episode_id in episode_ids:
            planned = self.episodes[episode_id]
            source = manifest.episodes[episode_id]
            if planned.archive_path != source.archive_path:
                raise VADPlanError(f"VAD plan archive path mismatch for episode {episode_id}")
            if planned.source_audio_sha256 != source.sha256:
                raise VADPlanError(f"VAD plan audio SHA-256 mismatch for episode {episode_id}")

    def transcript_metadata(self) -> dict:
        return {
            "vad_backend": "precomputed",
            "vad_model": self.model,
            "vad_plan_sha256": self.sha256,
            "vad_batch_size": self.batch_size,
            "vad_min_duration_on_seconds": self.min_duration_on,
            "vad_min_duration_off_seconds": self.min_duration_off,
        }


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VADPlanError(f"VAD plan {label} must be a non-empty string")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise VADPlanError(f"VAD plan {label} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise VADPlanError(f"VAD plan {label} must be a positive integer")
    return value


def _positive_float(value: object, label: str) -> float:
    number = _number(value, label)
    if number <= 0:
        raise VADPlanError(f"VAD plan {label} must be positive")
    return number


def _nonnegative_float(value: object, label: str) -> float:
    number = _number(value, label)
    if number < 0:
        raise VADPlanError(f"VAD plan {label} cannot be negative")
    return number


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VADPlanError(f"VAD plan {label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise VADPlanError(f"VAD plan {label} must be finite")
    return number


def _archive_path(value: object, episode_id: int) -> str:
    if not isinstance(value, str):
        raise VADPlanError(f"Episode {episode_id} archive_path must be a string")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or len(path.parts) != 2
        or path.parts[0] != "audio"
        or ".." in path.parts
        or "." in path.parts
    ):
        raise VADPlanError(f"Unsafe VAD plan archive_path for episode {episode_id}")
    return value


def _spans(value: object, episode_id: int, duration: float) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, list):
        raise VADPlanError(f"Episode {episode_id} speech_spans must be a list")
    spans = []
    previous_end = 0.0
    for index, item in enumerate(value):
        if not isinstance(item, list) or len(item) != 2:
            raise VADPlanError(f"Episode {episode_id} span {index} must be [start, end]")
        start = _nonnegative_float(item[0], f"episode {episode_id} span {index} start")
        end = _positive_float(item[1], f"episode {episode_id} span {index} end")
        if start >= end or start < previous_end or end > duration + 0.01:
            raise VADPlanError(f"Episode {episode_id} has invalid speech span {index}")
        spans.append((start, min(end, duration)))
        previous_end = end
    return tuple(spans)
