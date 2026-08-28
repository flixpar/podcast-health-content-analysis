import sys
import types

import numpy as np
import pytest

from podcast_pipeline.asr.vad import (
    SileroVoiceActivityDetector,
    SpeechDetection,
    speech_chunk_spans,
    vad_metadata,
)
from podcast_pipeline.config import TranscriptionConfig


def test_speech_regions_are_chunked_without_transcribing_silence():
    assert speech_chunk_spans(
        ((10.0, 25.0), (40.0, 44.0)), chunk_seconds=10, overlap_seconds=2,
    ) == [(10.0, 20.0), (18.0, 25.0), (40.0, 44.0)]


def test_silero_detector_preserves_absolute_sample_timestamps(monkeypatch):
    captured = {}

    def get_speech_timestamps(audio, model, **kwargs):
        captured.update(kwargs)
        assert isinstance(audio, np.ndarray)
        assert model == "model"
        return [{"start": 8_000, "end": 24_000}]

    fake = types.ModuleType("silero_vad")
    fake.load_silero_vad = lambda: "model"
    fake.get_speech_timestamps = get_speech_timestamps
    monkeypatch.setitem(sys.modules, "silero_vad", fake)
    config = TranscriptionConfig(
        vad_enabled=True,
        vad_threshold=0.6,
        vad_min_speech_duration_ms=400,
        vad_min_silence_duration_ms=200,
        vad_speech_pad_ms=50,
    )

    detection = SileroVoiceActivityDetector(config).detect(np.zeros(32_000, dtype=np.float32))

    assert detection == SpeechDetection(((0.5, 1.5),))
    assert detection.seconds == 1.0
    assert captured == {
        "sampling_rate": 16_000,
        "threshold": 0.6,
        "min_speech_duration_ms": 400,
        "min_silence_duration_ms": 200,
        "speech_pad_ms": 50,
    }


def test_invalid_vad_configuration_fails_before_loading_model():
    with pytest.raises(ValueError, match="vad_threshold"):
        SileroVoiceActivityDetector(TranscriptionConfig(vad_enabled=True, vad_threshold=1.0))
    with pytest.raises(ValueError, match="vad_speech_pad_ms"):
        SileroVoiceActivityDetector(TranscriptionConfig(vad_enabled=True, vad_speech_pad_ms=-1))


def test_vad_metadata_records_detection_provenance():
    config = TranscriptionConfig(vad_enabled=True)
    result = types.SimpleNamespace(
        detected_speech_seconds=12.3456,
        detected_speech_spans=((1.0, 4.0), (10.0, 19.3456)),
    )

    assert vad_metadata(config, result) == {
        "vad_enabled": True,
        "vad_model": "silero-vad",
        "vad_threshold": 0.5,
        "vad_min_speech_duration_ms": 250,
        "vad_min_silence_duration_ms": 2000,
        "vad_speech_pad_ms": 30,
        "detected_speech_seconds": 12.346,
        "detected_speech_spans": 2,
    }
    assert vad_metadata(TranscriptionConfig(), object()) == {"vad_enabled": False}
