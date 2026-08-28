from pathlib import Path

from podcast_pipeline.cli import build_parser


def test_transcription_vad_cli_override():
    parser = build_parser()

    assert parser.parse_args(["transcribe"]).vad is None
    assert parser.parse_args(["transcribe", "--vad"]).vad is True
    assert parser.parse_args(["transcribe", "--no-vad"]).vad is False
    assert parser.parse_args(["transcribe-audio-batch", "/tmp/batch", "--vad"]).vad is True


def test_audio_batch_precomputed_vad_plan_is_available():
    parser = build_parser()
    args = parser.parse_args([
        "transcribe-audio-batch", "/tmp/batch", "--vad-plan", "/tmp/plan.jsonl",
    ])

    assert args.vad_plan == Path("/tmp/plan.jsonl")
