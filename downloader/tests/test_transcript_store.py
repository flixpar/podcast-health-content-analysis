import pytest

from podcast_pipeline.models import Segment
from podcast_pipeline.transcripts.store import TranscriptStore, has_speaker_labels


def test_save_and_load_roundtrip(tmp_path):
    store = TranscriptStore(tmp_path)
    segments = [Segment("Hello there.", 0.0, 1.5), Segment("General Kenobi.", 1.5, 3.25)]
    saved = store.save(7, segments, {"source": "asr", "model": "m"})

    assert saved.path == tmp_path / "episode_7.jsonl.zst"
    assert saved.word_count == 4
    assert saved.duration_seconds == 3.25
    assert saved.has_timestamps

    loaded = store.load(saved.path)
    assert loaded.episode_id == 7
    assert loaded.text == "Hello there. General Kenobi."
    assert loaded.metadata["source"] == "asr" and loaded.metadata["model"] == "m"
    assert [(s.text, s.start, s.end) for s in loaded.segments] == [
        ("Hello there.", 0.0, 1.5), ("General Kenobi.", 1.5, 3.25)]


def test_untimed_transcript(tmp_path):
    saved = TranscriptStore(tmp_path).save(1, [Segment("just words")], {"source": "rss"})
    assert saved.duration_seconds is None and not saved.has_timestamps


def test_source_is_required(tmp_path):
    with pytest.raises(ValueError, match="source"):
        TranscriptStore(tmp_path).save(1, [Segment("x")], {})


def test_has_speaker_labels():
    labelled = [Segment(f"Alice: line {i}") if i % 2 else Segment(f"Bob: line {i}") for i in range(10)]
    assert has_speaker_labels(labelled)
    assert not has_speaker_labels([Segment("no labels here at all") for _ in range(10)])
    assert not has_speaker_labels([Segment("Alice: one")])
