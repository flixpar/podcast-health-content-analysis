import hashlib
import sys
import types
from pathlib import Path

from podcast_pipeline.asr.qwen_vllm import (
    QwenVLLMTranscriber,
    _encode_flac_chunk,
    _span_union_seconds,
    is_implausible_transcript,
    trim_repeated_prefix,
)
from podcast_pipeline.config import TranscriptionConfig
from podcast_pipeline.audio.ffmpeg import probe_stream_types
from podcast_pipeline.models import Segment
from podcast_pipeline.pipeline import ingest_audio_batch, transcribe_audio_batch
from podcast_pipeline.transcripts.store import TranscriptStore

from test_batch_roundtrip import _source_batch


def test_trim_repeated_prefix_removes_chunk_overlap():
    assert trim_repeated_prefix(
        "Alpha beta gamma four five",
        "beta gamma four five six seven.",
    ) == "six seven."


def test_trim_repeated_prefix_preserves_text_without_safe_anchor():
    current = "Entirely different material starts here."
    assert trim_repeated_prefix("The earlier passage ends now.", current) == current


def test_trim_repeated_prefix_ignores_distant_common_phrase():
    filler = " ".join(f"old{i}" for i in range(40))
    lead = " ".join(f"new{i}" for i in range(40))
    current = f"{lead} a common phrase appears only in the middle trailing words"
    previous = f"a common phrase appears only in the middle {filler}"
    assert trim_repeated_prefix(previous, current) == current


def test_trim_repeated_prefix_preserves_new_failure_marker_before_anchor():
    marker = "[UNTRANSCRIBED_AUDIO_535.0-565.0s_ASR_FAILURE]"
    assert trim_repeated_prefix(
        "Earlier words end with this repeated phrase here",
        f"{marker} repeated phrase here and then new speech",
    ) == f"{marker} and then new speech"


def test_trim_repeated_prefix_deduplicates_identical_failure_marker():
    marker = "[UNTRANSCRIBED_AUDIO_535.0-565.0s_ASR_FAILURE]"
    assert trim_repeated_prefix(
        f"Earlier words {marker} repeated phrase here",
        f"{marker} repeated phrase here and then new speech",
    ) == "and then new speech"


def test_qwen_request_sends_completion_ceiling(monkeypatch):
    config = TranscriptionConfig(
        backend="qwen_vllm",
        model_name="Qwen/Qwen3-ASR-1.7B",
        vllm_max_completion_tokens=4096,
    )
    transcriber = QwenVLLMTranscriber(config)
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"text": "A bounded transcript."}

    class Session:
        def post(self, url, **kwargs):
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr(transcriber, "_session", lambda: Session())

    assert transcriber._request(b"audio", "clip") == "A bounded transcript."
    assert captured["data"]["max_completion_tokens"] == "4096"


def test_runaway_transcript_detection():
    assert is_implausible_transcript("oh " * 500, 600)
    assert is_implausible_transcript("word " * 3001, 600)
    assert is_implausible_transcript("the same five word phrase " * 80, 600)
    assert is_implausible_transcript("the same five word phrase " * 6, 120)
    ordinary = " ".join(f"ordinary{index}" for index in range(1600))
    assert not is_implausible_transcript(ordinary, 600)


def test_omitted_span_accounting_deduplicates_overlap():
    assert _span_union_seconds(((535.0, 565.0), (560.0, 580.0))) == 45.0


def test_cover_art_input_is_remuxed_before_chunk_seeking(
    one_frame_cover_art_ogg, tmp_path,
):
    config = TranscriptionConfig(
        backend="qwen_vllm",
        model_name="Qwen/Qwen3-ASR-1.7B",
        chunk_duration_seconds=10,
        overlap_seconds=0,
        vllm_audio_remux_cache_dir=str(tmp_path / "remux-cache"),
    )
    plan = QwenVLLMTranscriber(config).plan_file(one_frame_cover_art_ogg)

    assert plan.path != one_frame_cover_art_ogg
    assert plan.input_preprocessing == "lossless_audio_stream_remux"
    assert not plan.seek_after_input
    assert probe_stream_types(plan.path) == ("audio",)
    chunk_hashes = {
        hashlib.sha256(_encode_flac_chunk(plan.path, start, end).data).hexdigest()
        for start, end in plan.spans
    }
    assert len(chunk_hashes) == len(plan.spans)


def test_cover_art_input_uses_safe_seek_without_remux_cache(one_frame_cover_art_ogg):
    config = TranscriptionConfig(
        backend="qwen_vllm",
        model_name="Qwen/Qwen3-ASR-1.7B",
        chunk_duration_seconds=10,
        overlap_seconds=0,
    )
    plan = QwenVLLMTranscriber(config).plan_file(one_frame_cover_art_ogg)

    assert plan.path == one_frame_cover_art_ogg
    assert plan.seek_after_input
    assert plan.input_preprocessing == "safe_output_seek_for_extra_streams"


def test_audio_batch_uses_concurrent_qwen_vllm_backend(
    config, conn, tmp_path, monkeypatch):
    _, outbound = _source_batch(config, conn, tmp_path, count=3)
    ingested = ingest_audio_batch.run(
        Path(outbound["archive"]), tmp_path / "workspace",
        checksum_path=Path(outbound["checksum"]),
    )
    batch_dir = Path(ingested["batch_dir"])

    class Result:
        segments = [Segment("Qwen words here.", 0.0, 2.5)]
        duration_seconds = 2.5
        chunk_count = 1
        rtf = 0.02
        fallback_retries = 0
        omitted_audio_seconds = 0.0
        omitted_audio_spans = ()
        input_preprocessing = None

    class FakeTranscriber:
        def __init__(self, cfg):
            assert cfg.vllm_request_concurrency == 2

        def plan_file(self, path):
            assert path.is_file()
            return types.SimpleNamespace(spans=[(0.0, 2.5)])

        def transcribe_chunk(self, plan, index):
            assert index == 0
            return types.SimpleNamespace(text="Qwen words here.")

        def assemble(self, plan, chunks):
            assert len(chunks) == 1
            return Result()

    fake_module = types.ModuleType("podcast_pipeline.asr.qwen_vllm")
    fake_module.QwenVLLMTranscriber = FakeTranscriber
    fake_module.TranscriptionError = RuntimeError
    monkeypatch.setitem(sys.modules, "podcast_pipeline.asr.qwen_vllm", fake_module)
    config.transcription.backend = "qwen_vllm"
    config.transcription.model_name = "Qwen/Qwen3-ASR-1.7B"
    config.transcription.vllm_request_concurrency = 2

    result = transcribe_audio_batch.run(config, batch_dir)

    assert result["transcribed"] == 3
    assert result["audio_seconds"] == 7.5
    store = TranscriptStore(batch_dir / "transcripts")
    transcript = store.load(next((batch_dir / "transcripts").iterdir()))
    assert transcript.metadata["backend"] == "qwen_vllm"
