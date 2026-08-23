"""The transcript file format: zstd-compressed JSONL.

Line 1 is ``{"type": "metadata", ...}``, line 2 is ``{"type": "summary", "text": <full text>, ...}``,
and every following line is a ``{"type": "segment", "index", "start", "end", "text"}``.
Both ASR output and publisher-provided transcripts are written through this
class, so consumers cannot tell them apart except by ``metadata.source``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import zstandard as zstd

from podcast_pipeline.models import Segment

FORMAT_VERSION = "1.0"


@dataclass
class SavedTranscript:
    path: Path
    word_count: int
    duration_seconds: float | None   # end of the last timed segment
    has_timestamps: bool


@dataclass
class Transcript:
    episode_id: int
    text: str
    language: str
    segments: list[Segment]
    metadata: dict


class TranscriptStore:
    def __init__(self, transcript_dir: Path, compression_level: int = 3):
        self.transcript_dir = Path(transcript_dir)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.compression_level = compression_level

    def path_for(self, episode_id: int) -> Path:
        return self.transcript_dir / f"episode_{episode_id}.jsonl.zst"

    def save(self, episode_id: int, segments: list[Segment], metadata: dict,
             language: str = "en") -> SavedTranscript:
        if "source" not in metadata:
            raise ValueError("transcript metadata must include 'source' ('asr' or 'rss')")
        full_text = " ".join(s.text for s in segments).strip()
        lines = [
            {"type": "metadata", "episode_id": episode_id,
             "created_at": datetime.now().isoformat(), "version": FORMAT_VERSION,
             "format": "jsonl_compressed", "compression": "zstd", **metadata},
            {"type": "summary", "text": full_text, "language": language,
             "word_count": len(full_text.split()), "segment_count": len(segments)},
        ]
        for i, segment in enumerate(segments):
            lines.append({"type": "segment", "index": i, **segment.to_json_dict()})

        payload = "\n".join(json.dumps(line, ensure_ascii=False, separators=(",", ":"))
                            for line in lines)
        path = self.path_for(episode_id)
        path.write_bytes(zstd.ZstdCompressor(level=self.compression_level).compress(payload.encode("utf-8")))

        ends = [s.end for s in segments if s.end is not None]
        return SavedTranscript(
            path=path, word_count=len(full_text.split()),
            duration_seconds=max(ends) if ends else None,
            has_timestamps=any(s.start is not None for s in segments),
        )

    def load(self, path: Path) -> Transcript:
        payload = zstd.ZstdDecompressor().decompress(Path(path).read_bytes()).decode("utf-8")
        metadata, summary, segments = {}, {}, []
        for line in payload.split("\n"):
            if not line:
                continue
            record = json.loads(line)
            kind = record.get("type")
            if kind == "metadata":
                metadata = record
            elif kind == "summary":
                summary = record
            elif kind == "segment":
                segments.append(Segment(text=record.get("text", ""),
                                        start=record.get("start"), end=record.get("end")))
        return Transcript(
            episode_id=metadata.get("episode_id"),
            text=summary.get("text") or " ".join(s.text for s in segments),
            language=summary.get("language", "en"),
            segments=segments,
            metadata=metadata,
        )


SPEAKER_LABEL = re.compile(r"^(?:speaker\s*\d+|[A-Z][A-Za-z.'-]{1,30})\s*:", re.IGNORECASE)


def has_speaker_labels(segments: list[Segment]) -> bool:
    """True when segments are prefixed with speaker names, as most publisher transcripts are."""
    sample = segments[:50]
    labelled = sum(1 for s in sample if SPEAKER_LABEL.match(s.text))
    return labelled >= max(2, len(sample) // 4)
