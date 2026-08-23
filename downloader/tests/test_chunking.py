import pytest

from podcast_pipeline.asr.chunking import (MAX_SEGMENT_WORDS, Word, chunk_spans,
                                           merge_chunk_words, words_to_segments)


def test_chunk_spans():
    assert chunk_spans(100, 300, 30) == [(0.0, 100)]
    assert chunk_spans(600, 300, 30) == [(0.0, 300), (270, 570), (540, 600)]
    spans = chunk_spans(1000, 300, 30)
    assert spans[0][0] == 0 and spans[-1][1] == 1000
    assert all(b[0] == a[1] - 30 for a, b in zip(spans, spans[1:]))
    with pytest.raises(ValueError):
        chunk_spans(100, 30, 30)


def test_merge_resolves_overlap_at_midpoint():
    # Chunk A covers 0-100, chunk B covers 80-180: overlap 80-100, midpoint 90.
    a = [Word("a1", 10, 11), Word("shared-early", 84, 85), Word("shared-late", 95, 96), Word("a-tail", 98, 99)]
    b = [Word("b-head", 81, 82), Word("shared-early", 84, 85), Word("shared-late", 95, 96), Word("b2", 150, 151)]
    merged = merge_chunk_words([(0, 100, a), (80, 180, b)])
    assert [w.text for w in merged] == ["a1", "shared-early", "shared-late", "b2"]


def test_single_chunk_passes_through():
    words = [Word("x", 0, 1), Word("y", 1, 2)]
    assert merge_chunk_words([(0, 10, words)]) == words


def test_words_to_segments_splits_on_sentence_end():
    words = [Word("Hello", 0, 0.5), Word("there.", 0.5, 1), Word("How", 2, 2.5),
             Word("are", 2.5, 3), Word("you?", 3, 3.5), Word("Fine", 4, 4.5)]
    segments = words_to_segments(words)
    assert [(s.text, s.start, s.end) for s in segments] == [
        ("Hello there.", 0, 1), ("How are you?", 2, 3.5), ("Fine", 4, 4.5)]


def test_runaway_sentences_are_split():
    words = [Word("w", i, i + 1) for i in range(MAX_SEGMENT_WORDS * 2 + 5)]
    segments = words_to_segments(words)
    assert [len(s.text.split()) for s in segments] == [MAX_SEGMENT_WORDS, MAX_SEGMENT_WORDS, 5]
