"""Top podcasts from Apple's public charts, enriched via the iTunes lookup API.

No authentication needed. Two charts are exposed, because Apple publishes them
at different endpoints:

* the overall chart, from the Apple Marketing Tools feed. It only ever returns
  the top 100 and takes no genre.
* a per-genre chart, from the older iTunes ``toppodcasts`` RSS feed, which is
  the only public endpoint that filters by genre. Its ordering was checked
  against the Health & Fitness chart on podcasts.apple.com and matches
  position for position.

Neither chart carries the RSS URL, so every entry costs a second request to
the lookup API.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

from podcast_pipeline.models import PodcastRecord

logger = logging.getLogger(__name__)

CHARTS_URL = "https://rss.marketingtools.apple.com/api/v2/{country}/podcasts/top/100/podcasts.json"
GENRE_CHARTS_URL = "https://itunes.apple.com/{country}/rss/toppodcasts/limit={limit}/genre={genre}/json"
LOOKUP_URL = "https://itunes.apple.com/lookup?id={apple_id}&entity=podcast"
CHART_LIMIT = 100
GENRE_CHART_LIMIT = 200

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
                 country: str = "us", genre: str | None = None, lookup_delay: float = 0.1):
        self.session = session
        self.filter_health_only = filter_health_only
        self.country = country
        self.genre = genre
        self.lookup_delay = lookup_delay

    @property
    def chart_name(self) -> str:
        """Identifier recorded in ``podcast_charts.chart``."""
        if self.genre:
            return f"apple_{self.country}_genre_{self.genre}"
        return f"apple_{self.country}_top"

    def top_podcasts(self, limit: int) -> list[PodcastRecord]:
        entries = self._genre_entries(limit) if self.genre else self._overall_entries(limit)

        records = []
        for entry in entries:
            if self.filter_health_only and not _is_health_related(entry):
                continue
            details = self.lookup(entry["id"])
            time.sleep(self.lookup_delay)   # be polite to the lookup API
            records.append(_to_record(entry, details))
            logger.info(f"  {len(records):3d}. {records[-1].title}")
            if len(records) >= limit:
                break
        logger.info(f"Fetched {len(records)} podcasts from Apple chart {self.chart_name}")
        return records

    def _overall_entries(self, limit: int) -> list[dict]:
        if limit > CHART_LIMIT:
            logger.warning(f"Apple's overall chart exposes at most {CHART_LIMIT} podcasts; "
                           f"--limit {limit} capped")
        url = CHARTS_URL.format(country=self.country)
        logger.info(f"Fetching Apple top podcasts from {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()["feed"]["results"]

    def _genre_entries(self, limit: int) -> list[dict]:
        """The genre chart, normalised to the shape ``_overall_entries`` returns.

        The feed is asked for more entries than requested only when a health
        filter may drop some; asking beyond ``GENRE_CHART_LIMIT`` returns the
        maximum silently, so the cap is applied here instead.
        """
        wanted = min(limit if not self.filter_health_only else limit * 2, GENRE_CHART_LIMIT)
        url = GENRE_CHARTS_URL.format(country=self.country, limit=wanted, genre=self.genre)
        logger.info(f"Fetching Apple genre {self.genre} chart from {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        feed = response.json()["feed"]
        entries = feed.get("entry") or []
        if isinstance(entries, dict):       # the feed unwraps a single result
            entries = [entries]
        return [_normalise_genre_entry(e) for e in entries]

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


def _normalise_genre_entry(entry: dict) -> dict:
    """One ``toppodcasts`` RSS entry in the shape the Marketing Tools feed uses."""
    def label(node, default=""):
        return (node or {}).get("label", default)

    images = entry.get("im:image") or []
    category = (entry.get("category") or {}).get("attributes") or {}
    return {
        "id": entry["id"]["attributes"]["im:id"],
        "name": label(entry.get("im:name")),
        "artistName": label(entry.get("im:artist")),
        "url": label(entry.get("id")),
        "artworkUrl100": label(images[-1]) if images else None,
        "genres": [{"genreId": category.get("im:id", ""), "name": category.get("term", "")}],
        "contentAdvisoryRating": (entry.get("im:contentType") or {}).get("attributes", {}).get("term"),
    }


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
