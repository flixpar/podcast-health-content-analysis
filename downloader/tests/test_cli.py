from podcast_pipeline.cli import build_parser


def test_transcription_vad_cli_override():
    parser = build_parser()

    assert parser.parse_args(["transcribe"]).vad is None
    assert parser.parse_args(["transcribe", "--vad"]).vad is True
    assert parser.parse_args(["transcribe", "--no-vad"]).vad is False
    assert parser.parse_args(["transcribe-audio-batch", "/tmp/batch", "--vad"]).vad is True
