"""Top podcasts from Apple's public charts feed, enriched via the iTunes lookup API.

No authentication needed. The charts endpoint only exposes the top 100, and
the RSS URL for each podcast comes from a second request to the lookup API.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

from podcast_pipeline.models import PodcastRecord

logger = logging.getLogger(__name__)

CHARTS_URL = "https://rss.marketingtools.apple.com/api/v2/{country}/podcasts/top/100/podcasts.json"
LOOKUP_URL = "https://itunes.apple.com/lookup?id={apple_id}&entity=podcast"
CHART_LIMIT = 100

# Apple genre ids that count as health-related: Health & Fitness, Alternative
# Health, Medicine, Mental Health, Science, Self-Improvement, Personal
# Journals, How To, Health, Fitness.
HEALTH_GENRES = {"1512", "1513", "1517", "1520", "1533",
                 "1307", "1471", "1469", "1468", "1461"}
HEALTH_KEYWORDS = (
    "health", "fitness", "wellness", "medical", "medicine", "nutrition", "diet",
    "workout", "mental health", "therapy", "psychology", "mindfulness", "meditation",
    "yoga", "doctor", "healthcare", "healing", "supplement", "sleep", "anxiety",
    "depression", "stress", "immune", "longevity",
)


class AppleChartsSource:
    def __init__(self, session: requests.Session, filter_health_only: bool = False,
                 country: str = "us", lookup_delay: float = 0.1):
        self.session = session
        self.filter_health_only = filter_health_only
        self.country = country
        self.lookup_delay = lookup_delay

    def top_podcasts(self, limit: int) -> list[PodcastRecord]:
        if limit > CHART_LIMIT:
            logger.warning(f"Apple charts expose at most {CHART_LIMIT} podcasts; --limit {limit} capped")
        url = CHARTS_URL.format(country=self.country)
        logger.info(f"Fetching Apple top podcasts from {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        results = response.json()["feed"]["results"]

        records = []
        for entry in results:
            if self.filter_health_only and not _is_health_related(entry):
                continue
            details = self.lookup(entry["id"])
            time.sleep(self.lookup_delay)   # be polite to the lookup API
            records.append(_to_record(entry, details))
            logger.info(f"  {len(records):3d}. {records[-1].title}")
            if len(records) >= limit:
                break
        logger.info(f"Fetched {len(records)} podcasts from Apple charts")
        return records

    def lookup(self, apple_id: str, attempts: int = 3) -> dict | None:
        """iTunes lookup record for a podcast (carries feedUrl), or None if unavailable."""
        url = LOOKUP_URL.format(apple_id=apple_id)
        for attempt in range(attempts):
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 429:
                    wait = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited by iTunes lookup; waiting {wait}s")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                results = response.json().get("results") or []
                if not results:
                    logger.warning(f"No iTunes lookup data for podcast {apple_id}")
                    return None
                return results[0]
            except requests.RequestException as e:
                logger.warning(f"iTunes lookup for {apple_id} failed (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)
        logger.error(f"Giving up on iTunes lookup for {apple_id}")
        return None


def _is_health_related(entry: dict) -> bool:
    if any(str(g.get("genreId", "")) in HEALTH_GENRES for g in entry.get("genres", [])):
        return True
    text = f"{entry.get('name', '')} {entry.get('artistName', '')}".lower()
    return any(keyword in text for keyword in HEALTH_KEYWORDS)


def _to_record(entry: dict, details: dict | None) -> PodcastRecord:
    details = details or {}
    latest = None
    if details.get("releaseDate"):
        try:
            latest = datetime.fromisoformat(details["releaseDate"].replace("Z", "+00:00")).isoformat()
        except ValueError:
            pass
    categories = details.get("genres") or [g.get("name", "") for g in entry.get("genres", [])]
    return PodcastRecord(
        source_id=f"apple_{entry['id']}",
        title=details.get("collectionName") or entry.get("name"),
        description=details.get("description") or f"Popular podcast by {entry.get('artistName', 'Unknown')}",
        publisher=details.get("artistName") or entry.get("artistName"),
        rss_url=details.get("feedUrl"),
        apple_podcasts_id=str(entry["id"]),
        categories=[c for c in categories if c],
        latest_episode_date=latest,
        extra={
            "web_url": details.get("collectionViewUrl") or entry.get("url"),
            "artwork_url": details.get("artworkUrl600") or entry.get("artworkUrl100"),
            "explicit": (details.get("contentAdvisoryRating") or entry.get("contentAdvisoryRating"))
                        in ("Explicit", "Explict"),   # Apple's charts feed misspells it
            "source": "apple_rss_itunes" if details else "apple_rss",
        },
    )
