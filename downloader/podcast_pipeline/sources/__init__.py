"""Where the list of podcasts comes from: Apple's charts, Spotify's, or Podchaser."""

from __future__ import annotations

from typing import Protocol

import requests

from podcast_pipeline.config import Config
from podcast_pipeline.models import PodcastRecord


class PodcastSource(Protocol):
    #: Identifier for the chart this source reads, recorded in ``podcast_charts``.
    chart_name: str

    def top_podcasts(self, limit: int) -> list[PodcastRecord]: ...


def make_source(config: Config, session: requests.Session) -> PodcastSource:
    kind = config.fetcher.type.lower()
    if kind == "apple":
        from podcast_pipeline.sources.apple import AppleChartsSource
        return AppleChartsSource(session, filter_health_only=config.fetcher.filter_health_only,
                                 country=config.fetcher.country, genre=config.fetcher.genre)
    if kind == "spotify":
        from podcast_pipeline.sources.spotify import SpotifyChartsSource
        return SpotifyChartsSource(session, config.spotify,
                                   filter_health_only=config.fetcher.filter_health_only,
                                   country=config.fetcher.country)
    if kind == "podchaser":
        from podcast_pipeline.sources.podchaser import PodchaserSource
        return PodchaserSource(session, config.podchaser,
                               filter_health_only=config.fetcher.filter_health_only)
    raise ValueError(f"Unknown fetcher.type {config.fetcher.type!r}; "
                     f"expected 'apple', 'spotify', or 'podchaser'")
