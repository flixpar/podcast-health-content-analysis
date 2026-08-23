"""Plain data records passed between modules.

Nothing here touches the network, the database, or the filesystem; these are
the shapes the pipeline stages agree on.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class PodcastRecord:
    """A podcast as returned by a chart source (Apple or Podchaser)."""

    source_id: str              # "apple_<id>" or the Podchaser id; unique per podcast
    title: str
    description: str | None = None
    publisher: str | None = None
    rss_url: str | None = None
    apple_podcasts_id: str | None = None
    spotify_id: str | None = None
    categories: list[str] = field(default_factory=list)
    latest_episode_date: str | None = None
    extra: dict = field(default_factory=dict)   # anything else worth keeping, stored as JSON

    def to_json_dict(self) -> dict:
        return asdict(self)


@dataclass
class FeedEpisode:
    """One episode as parsed from a podcast RSS feed."""

    guid: str
    title: str
    audio_url: str
    description: str = ""
    audio_length: int = 0
    audio_type: str | None = None
    published_date: str | None = None     # ISO 8601
    duration_seconds: int | None = None
    season: str | None = None
    episode_number: str | None = None
    episode_type: str = "full"
    explicit: bool = False
    transcript_url: str | None = None
    transcript_type: str | None = None
    transcript_language: str | None = None
    chapters_url: str | None = None

    @property
    def has_transcript(self) -> bool:
        return bool(self.transcript_url)

    def to_json_dict(self) -> dict:
        return asdict(self)


@dataclass
class Segment:
    """A span of transcript text. Timestamps are seconds, or None when the
    source (an untimed publisher transcript) does not provide them."""

    text: str
    start: float | None = None
    end: float | None = None

    def to_json_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "text": self.text}
