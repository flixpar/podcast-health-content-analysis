import json
import types
from pathlib import Path

import pytest

from podcast_pipeline.asr.qwen_vllm import QwenVLLMTranscriber
from podcast_pipeline.asr.vad import vad_metadata
from podcast_pipeline.asr.vad_plan import PrecomputedVADPlan, VADPlanError
from podcast_pipeline.config import TranscriptionConfig


def _write_plan(path: Path, **episode_overrides) -> Path:
    episode = {
        "record_type": "episode",
        "episode_id": 42,
        "archive_path": "audio/episode_42.ogg",
        "source_audio_sha256": "b" * 64,
        "duration_seconds": 30.0,
        "speech_seconds": 12.0,
        "speech_spans": [[2.0, 10.0], [20.0, 24.0]],
    }
    episode.update(episode_overrides)
    records = [{
        "record_type": "vad_plan",
        "schema_version": 1,
        "batch_id": "audio-batch-test",
        "source_audio_manifest_sha256": "a" * 64,
        "model": "pyannote/segmentation-3.0",
        "batch_size": 512,
        "min_duration_on": 0.25,
        "min_duration_off": 10.0,
        "episode_count": 1,
    }, episode]
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    return path


def test_precomputed_plan_validates_batch_and_detects_episode(tmp_path):
    path = _write_plan(tmp_path / "plan.jsonl")
    plan = PrecomputedVADPlan.load(path)
    manifest = types.SimpleNamespace(
        batch_id="audio-batch-test",
        sha256="a" * 64,
        episodes={42: types.SimpleNamespace(
            archive_path="audio/episode_42.ogg", sha256="b" * 64,
        )},
    )

    plan.validate_batch(manifest, {42})
    detection = plan.detect(Path("/tmp/episode_42.ogg"), 30.0)

    assert detection.spans == ((2.0, 10.0), (20.0, 24.0))
    assert plan.transcript_metadata()["vad_plan_sha256"] == plan.sha256


def test_precomputed_plan_rejects_overlapping_spans(tmp_path):
    path = _write_plan(
        tmp_path / "plan.jsonl",
        speech_seconds=13.0,
        speech_spans=[[2.0, 10.0], [9.0, 14.0]],
    )

    with pytest.raises(VADPlanError, match="invalid speech span"):
        PrecomputedVADPlan.load(path)


def test_qwen_uses_precomputed_plan_without_decoding(tmp_path, monkeypatch):
    plan_path = _write_plan(tmp_path / "plan.jsonl")
    audio_path = tmp_path / "episode_42.ogg"
    audio_path.write_bytes(b"audio")
    monkeypatch.setattr("podcast_pipeline.asr.qwen_vllm.probe_duration", lambda path: 30.0)
    monkeypatch.setattr("podcast_pipeline.asr.qwen_vllm.probe_stream_types", lambda path: ("audio",))
    monkeypatch.setattr(
        "podcast_pipeline.asr.qwen_vllm.decode_pcm",
        lambda *args: pytest.fail("precomputed plans must not decode full audio"),
    )
    config = TranscriptionConfig(
        backend="qwen_vllm",
        vad_enabled=True,
        vad_plan_path=str(plan_path),
        chunk_duration_seconds=6,
        overlap_seconds=1,
    )

    plan = QwenVLLMTranscriber(config).plan_file(audio_path)

    assert plan.detected_speech_spans == ((2.0, 10.0), (20.0, 24.0))
    assert plan.spans == [(2.0, 8.0), (7.0, 10.0), (20.0, 24.0)]
    assert plan.vad_provenance["vad_model"] == "pyannote/segmentation-3.0"


def test_precomputed_metadata_is_recorded(tmp_path):
    plan = PrecomputedVADPlan.load(_write_plan(tmp_path / "plan.jsonl"))
    result = types.SimpleNamespace(
        detected_speech_seconds=12.0,
        detected_speech_spans=((2.0, 10.0), (20.0, 24.0)),
        vad_provenance=plan.transcript_metadata(),
    )

    metadata = vad_metadata(
        TranscriptionConfig(vad_enabled=True, vad_plan_path=str(plan.path)), result,
    )

    assert metadata["vad_backend"] == "precomputed"
    assert metadata["vad_model"] == "pyannote/segmentation-3.0"
    assert metadata["vad_plan_sha256"] == plan.sha256
    assert metadata["detected_speech_spans"] == 2
