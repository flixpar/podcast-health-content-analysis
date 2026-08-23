"""Split long audio into overlapping chunks and stitch the transcripts back together.

Pure functions, no torch: this is the part worth unit-testing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from podcast_pipeline.models import Segment

SENTENCE_END = (".", "!", "?", '."', '!"', '?"', ".'", "!'", "?'")

# A sentence this long is almost certainly a run-on the model failed to
# punctuate; split it so segments stay usable for citation.
MAX_SEGMENT_WORDS = 80


@dataclass
class Word:
    text: str
    start: float   # absolute seconds within the episode
    end: float

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2


def chunk_spans(total_seconds: float, chunk_seconds: float,
                overlap_seconds: float) -> list[tuple[float, float]]:
    """Consecutive (start, end) spans covering [0, total), each overlapping the
    previous by ``overlap_seconds``. Short audio yields a single span."""
    if chunk_seconds <= overlap_seconds:
        raise ValueError(f"chunk ({chunk_seconds}s) must be longer than overlap ({overlap_seconds}s)")
    spans = []
    start = 0.0
    while True:
        end = min(start + chunk_seconds, total_seconds)
        spans.append((start, end))
        if end >= total_seconds:
            return spans
        start = end - overlap_seconds


def merge_chunk_words(chunks: list[tuple[float, float, list[Word]]]) -> list[Word]:
    """Combine per-chunk word lists into one, resolving each overlap at its midpoint.

    ``chunks`` is ``[(span_start, span_end, words)]`` in order, with word times
    already absolute. Within an overlap, words left of the midpoint come from
    the earlier chunk and words right of it from the later one, so every word
    is taken from a chunk where it sits well inside the audio the model saw.
    """
    merged: list[Word] = []
    for i, (start, end, words) in enumerate(chunks):
        lower = -math.inf if i == 0 else (chunks[i - 1][1] + start) / 2
        upper = math.inf if i == len(chunks) - 1 else (end + chunks[i + 1][0]) / 2
        merged.extend(w for w in words if lower <= w.midpoint < upper)
    return merged


def words_to_segments(words: list[Word]) -> list[Segment]:
    """Group words into sentence segments with the timestamps of their first and last word."""
    segments: list[Segment] = []
    current: list[Word] = []

    def flush():
        if current:
            segments.append(Segment(text=" ".join(w.text for w in current),
                                    start=current[0].start, end=current[-1].end))
            current.clear()

    for word in words:
        current.append(word)
        if word.text.endswith(SENTENCE_END) or len(current) >= MAX_SEGMENT_WORDS:
            flush()
    flush()
    return segments
