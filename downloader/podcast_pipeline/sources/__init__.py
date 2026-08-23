"""Where the list of podcasts comes from: Apple's charts or Podchaser."""

from __future__ import annotations

from typing import Protocol

import requests

from podcast_pipeline.config import Config
from podcast_pipeline.models import PodcastRecord


class PodcastSource(Protocol):
    def top_podcasts(self, limit: int) -> list[PodcastRecord]: ...


def make_source(config: Config, session: requests.Session) -> PodcastSource:
    kind = config.fetcher.type.lower()
    if kind == "apple":
        from podcast_pipeline.sources.apple import AppleChartsSource
        return AppleChartsSource(session, filter_health_only=config.fetcher.filter_health_only)
    if kind == "podchaser":
        from podcast_pipeline.sources.podchaser import PodchaserSource
        return PodchaserSource(session, config.podchaser,
                               filter_health_only=config.fetcher.filter_health_only)
    raise ValueError(f"Unknown fetcher.type {config.fetcher.type!r}; expected 'apple' or 'podchaser'")
