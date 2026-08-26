import json

import pytest

from podcast_pipeline.pipeline.transcribe_audio_batch import (
    AudioBatchTranscriptionError, _load_failures,
)


def _record(episode_id: int) -> bytes:
    return json.dumps({"episode_id": episode_id}, separators=(",", ":")).encode()


def test_load_failures_discards_only_a_malformed_unterminated_tail(tmp_path):
    path = tmp_path / "transcription_failures.jsonl"
    valid = _record(11) + b"\n"
    path.write_bytes(valid + b'{"episode_id":12,"error":"interrup')

    assert _load_failures(path) == {11}
    assert path.read_bytes() == valid


def test_load_failures_normalizes_a_valid_unterminated_tail(tmp_path):
    path = tmp_path / "transcription_failures.jsonl"
    record = _record(11)
    path.write_bytes(record)

    assert _load_failures(path) == {11}
    assert path.read_bytes() == record + b"\n"


@pytest.mark.parametrize("payload", [
    b'{"episode_id":11\n' + _record(12) + b"\n",
    _record(11) + b"\n" + b'{"episode_id":12\n',
])
def test_load_failures_rejects_malformed_terminated_records(tmp_path, payload):
    path = tmp_path / "transcription_failures.jsonl"
    path.write_bytes(payload)

    with pytest.raises(AudioBatchTranscriptionError, match="Invalid failure log"):
        _load_failures(path)
    assert path.read_bytes() == payload
