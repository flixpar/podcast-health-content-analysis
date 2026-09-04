import hashlib
import shutil
import subprocess
import sys
import types
from concurrent.futures import Future
from pathlib import Path

import pytest

from podcast_pipeline.asr.qwen_vllm import (
    QwenVLLMTranscriber,
    _encode_flac_chunk,
    _span_union_seconds,
    is_implausible_transcript,
    trim_repeated_prefix,
)
from podcast_pipeline.asr.vad import SpeechDetection
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
    assert is_implausible_transcript("啊！" * 200, 600)
    assert is_implausible_transcript("敬爱你，" * 200, 600)
    ordinary = " ".join(f"ordinary{index}" for index in range(1600))
    assert not is_implausible_transcript(ordinary, 600)


def test_fallback_stops_at_nominal_30_second_span_with_float_drift(monkeypatch):
    transcriber = QwenVLLMTranscriber(TranscriptionConfig())
    requests = []

    monkeypatch.setattr(
        "podcast_pipeline.asr.qwen_vllm._encode_flac_chunk",
        lambda *args: types.SimpleNamespace(
            data=b"audio", mean_volume_db=-20.0, sample_count=480000,
        ),
    )

    def repeated_output(audio, label, max_tokens):
        requests.append(label)
        return "the same five word phrase " * 30

    monkeypatch.setattr(transcriber, "_request", repeated_output)

    result = transcriber._transcribe_span(
        Path("episode.ogg"), 0.0, 30.000000000000114, "clip"
    )

    assert requests == ["clip"]
    assert result.text == "[UNTRANSCRIBED_AUDIO_0.0-30.0s_ASR_FAILURE]"
    assert result.fallback_retries == 1
    assert result.omitted_audio_spans == ((0.0, 30.000000000000114),)


def test_omitted_span_accounting_deduplicates_overlap():
    assert _span_union_seconds(((535.0, 565.0), (560.0, 580.0))) == 45.0


def test_bounded_futures_never_retains_more_than_limit(monkeypatch):
    pending_sizes = []

    class ImmediateExecutor:
        def submit(self, function, item):
            future = Future()
            future.set_result(function(item))
            return future

    def observe_wait(pending, return_when=None):
        pending_sizes.append(len(pending))
        return {next(iter(pending))}, set()

    monkeypatch.setattr(transcribe_audio_batch, "wait", observe_wait)

    completed = list(transcribe_audio_batch._bounded_futures(
        ImmediateExecutor(), range(20), lambda value: value * 2, max_pending=3,
    ))

    assert [future.result() for future, _ in completed] == [value * 2 for _, value in completed]
    assert len(completed) == 20
    assert max(pending_sizes) == 3


def test_bounded_futures_cancels_abandoned_window(monkeypatch):
    futures = []

    class WindowExecutor:
        def submit(self, function, item):
            future = Future()
            if item == 0:
                future.set_exception(RuntimeError("chunk failed"))
            futures.append(future)
            return future

    def choose_failed_future(pending, return_when=None):
        failed = next((future for future in pending if future.done()), None)
        if failed is not None:
            return {failed}, set(pending) - {failed}
        return set(pending), set()

    monkeypatch.setattr(transcribe_audio_batch, "wait", choose_failed_future)
    completed = transcribe_audio_batch._bounded_futures(
        WindowExecutor(), range(3), lambda value: value, max_pending=3,
    )
    failed, _ = next(completed)

    with pytest.raises(RuntimeError, match="chunk failed"):
        failed.result()
    completed.close()

    assert all(future.cancelled() for future in futures[1:])


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


def test_cover_art_mp3_remuxes_into_a_container_that_holds_mp3(
    cover_art_mp3, tmp_path,
):
    # Ogg cannot carry an MP3 stream, so remuxing one used to fail with
    # "Unsupported codec id in stream 0" and discard the whole episode.
    config = TranscriptionConfig(
        backend="qwen_vllm",
        model_name="Qwen/Qwen3-ASR-1.7B",
        chunk_duration_seconds=10,
        overlap_seconds=0,
        vllm_audio_remux_cache_dir=str(tmp_path / "remux-cache"),
    )
    plan = QwenVLLMTranscriber(config).plan_file(cover_art_mp3)

    assert plan.path != cover_art_mp3
    assert plan.path.suffix == ".mka"
    assert plan.input_preprocessing == "lossless_audio_stream_remux"
    assert not plan.seek_after_input
    assert probe_stream_types(plan.path) == ("audio",)
    chunk_hashes = {
        hashlib.sha256(_encode_flac_chunk(plan.path, start, end).data).hexdigest()
        for start, end in plan.spans
    }
    assert len(chunk_hashes) == len(plan.spans)


def test_ogg_native_input_still_remuxes_to_ogg(one_frame_cover_art_ogg, tmp_path):
    config = TranscriptionConfig(
        backend="qwen_vllm",
        model_name="Qwen/Qwen3-ASR-1.7B",
        chunk_duration_seconds=10,
        overlap_seconds=0,
        vllm_audio_remux_cache_dir=str(tmp_path / "remux-cache"),
    )
    plan = QwenVLLMTranscriber(config).plan_file(one_frame_cover_art_ogg)

    assert plan.path.suffix == ".ogg"


def test_span_past_real_audio_reports_zero_samples(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")
    source = tmp_path / "short.flac"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "anoisesrc=d=5:c=pink:r=16000:s=7",
         "-y", str(source)],
        check=True,
    )

    present = _encode_flac_chunk(source, 0.0, 5.0)
    past_end = _encode_flac_chunk(source, 100.0, 110.0)

    # ffmpeg exits 0 and writes a header-only FLAC whose "unknown" sample count
    # libsndfile reports as 2**63 samples, so the bytes alone look valid.
    assert present.sample_count > 0
    assert past_end.sample_count == 0
    assert past_end.data


def test_span_with_no_audio_is_omitted_without_an_asr_request(monkeypatch):
    transcriber = QwenVLLMTranscriber(TranscriptionConfig())
    monkeypatch.setattr(
        "podcast_pipeline.asr.qwen_vllm._encode_flac_chunk",
        lambda *args: types.SimpleNamespace(
            data=b"flac-header-only", mean_volume_db=None, sample_count=0,
        ),
    )

    def unexpected_request(audio, label, max_tokens):
        raise AssertionError("an empty span must never reach vLLM")

    monkeypatch.setattr(transcriber, "_request", unexpected_request)

    result = transcriber._transcribe_span(Path("episode.mp3"), 2380.0, 2515.5, "clip")

    assert result.text == "[UNTRANSCRIBED_AUDIO_2380.0-2515.5s_NO_AUDIO]"
    assert result.omitted_audio_spans == ((2380.0, 2515.5),)
    assert result.fallback_retries == 0


def test_qwen_vad_only_plans_detected_speech(tmp_path, monkeypatch):
    audio_path = tmp_path / "episode.ogg"
    audio_path.write_bytes(b"audio")
    decoded = object()

    class FakeVad:
        def __init__(self, config):
            assert config.vad_enabled

        def detect(self, audio):
            assert audio is decoded
            return SpeechDetection(((2.0, 10.0), (20.0, 24.0)))

    monkeypatch.setattr("podcast_pipeline.asr.qwen_vllm.SileroVoiceActivityDetector", FakeVad)
    monkeypatch.setattr("podcast_pipeline.asr.qwen_vllm.probe_duration", lambda path: 30.0)
    monkeypatch.setattr("podcast_pipeline.asr.qwen_vllm.probe_stream_types", lambda path: ("audio",))
    monkeypatch.setattr("podcast_pipeline.asr.qwen_vllm.decode_pcm", lambda path, rate: decoded)
    config = TranscriptionConfig(
        backend="qwen_vllm", vad_enabled=True,
        chunk_duration_seconds=6, overlap_seconds=1,
    )

    plan = QwenVLLMTranscriber(config).plan_file(audio_path)

    assert plan.detected_speech_spans == ((2.0, 10.0), (20.0, 24.0))
    assert plan.spans == [(2.0, 8.0), (7.0, 10.0), (20.0, 24.0)]


def test_qwen_vad_can_return_empty_transcript_without_asr_requests():
    plan = types.SimpleNamespace(
        path=Path("silent.ogg"), duration_seconds=60.0, spans=[],
        input_preprocessing=None, detected_speech_spans=(),
    )

    result = QwenVLLMTranscriber(TranscriptionConfig()).assemble(plan, [])

    assert result.segments == []
    assert result.chunk_count == 0
    assert result.detected_speech_seconds == 0


def test_qwen_vad_does_not_deduplicate_across_skipped_silence():
    plan = types.SimpleNamespace(
        path=Path("episode.ogg"), duration_seconds=30.0,
        spans=[(0.0, 5.0), (20.0, 25.0)], input_preprocessing=None,
        detected_speech_spans=((0.0, 5.0), (20.0, 25.0)),
    )
    chunks = [
        types.SimpleNamespace(
            text="The same phrase here", start=0.0, end=5.0,
            transcription_seconds=0.1, fallback_retries=0, omitted_audio_spans=(),
        ),
        types.SimpleNamespace(
            text="The same phrase here", start=20.0, end=25.0,
            transcription_seconds=0.1, fallback_retries=0, omitted_audio_spans=(),
        ),
    ]

    result = QwenVLLMTranscriber(TranscriptionConfig()).assemble(plan, chunks)

    assert result.text == "The same phrase here The same phrase here"


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
