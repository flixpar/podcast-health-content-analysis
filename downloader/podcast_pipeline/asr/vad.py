"""Silero voice activity detection while preserving episode timestamps."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from podcast_pipeline.asr import SAMPLE_RATE
from podcast_pipeline.asr.chunking import chunk_spans
from podcast_pipeline.config import TranscriptionConfig


@dataclass(frozen=True)
class SpeechDetection:
    spans: tuple[tuple[float, float], ...]

    @property
    def seconds(self) -> float:
        return sum(end - start for start, end in self.spans)


class SileroVoiceActivityDetector:
    """A stateful Silero model intended for one transcription worker.

    Audio decoding remains in this project so VAD and ASR see the same mono
    16 kHz samples. The small TorchScript model stays on CPU and leaves GPU
    memory to ASR.
    """

    def __init__(self, config: TranscriptionConfig):
        _validate_config(config)
        from silero_vad import get_speech_timestamps, load_silero_vad

        self.config = config
        self._get_speech_timestamps = get_speech_timestamps
        self.model = load_silero_vad()

    def detect(self, audio: np.ndarray) -> SpeechDetection:
        timestamps = self._get_speech_timestamps(
            audio,
            self.model,
            sampling_rate=SAMPLE_RATE,
            threshold=self.config.vad_threshold,
            min_speech_duration_ms=self.config.vad_min_speech_duration_ms,
            min_silence_duration_ms=self.config.vad_min_silence_duration_ms,
            speech_pad_ms=self.config.vad_speech_pad_ms,
        )
        spans = tuple(
            (item["start"] / SAMPLE_RATE, item["end"] / SAMPLE_RATE)
            for item in timestamps
        )
        return SpeechDetection(spans)


def speech_chunk_spans(
    speech_spans: tuple[tuple[float, float], ...],
    chunk_seconds: float,
    overlap_seconds: float,
) -> list[tuple[float, float]]:
    """Chunk each detected speech region without filling intervening silence."""
    spans: list[tuple[float, float]] = []
    for speech_start, speech_end in speech_spans:
        duration = speech_end - speech_start
        spans.extend(
            (speech_start + start, speech_start + end)
            for start, end in chunk_spans(duration, chunk_seconds, overlap_seconds)
        )
    return spans


def vad_metadata(config: TranscriptionConfig, result) -> dict:
    """Transcript provenance shared by local and batch transcription."""
    metadata = {"vad_enabled": config.vad_enabled}
    if not config.vad_enabled:
        return metadata
    provenance = getattr(result, "vad_provenance", None)
    if provenance:
        metadata.update(provenance)
    else:
        metadata.update({
            "vad_backend": "inline",
            "vad_model": "silero-vad",
            "vad_threshold": config.vad_threshold,
            "vad_min_speech_duration_ms": config.vad_min_speech_duration_ms,
            "vad_min_silence_duration_ms": config.vad_min_silence_duration_ms,
            "vad_speech_pad_ms": config.vad_speech_pad_ms,
        })
    metadata.update({
        "detected_speech_seconds": round(result.detected_speech_seconds, 3),
        "detected_speech_spans": len(result.detected_speech_spans),
    })
    return metadata


def _validate_config(config: TranscriptionConfig) -> None:
    if not 0 < config.vad_threshold < 1:
        raise ValueError("transcription.vad_threshold must be between 0 and 1")
    for name in (
        "vad_min_speech_duration_ms",
        "vad_min_silence_duration_ms",
        "vad_speech_pad_ms",
    ):
        if getattr(config, name) < 0:
            raise ValueError(f"transcription.{name} cannot be negative")
