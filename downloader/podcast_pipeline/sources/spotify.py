"""Top podcasts from Spotify's public chart at podcastcharts.byspotify.com.

The chart is what the site's own front end calls: no authentication, no
Spotify API credentials. It returns show names and Spotify URIs but **no RSS
feed**, and the rest of this pipeline can do nothing with a show it cannot
fetch a feed for. So every charting show is looked up by title in the iTunes
search API to recover an Apple id and a feed URL.

A show that cannot be matched is still recorded, with no feed and
``extra["rss_lookup"] == "unmatched"``. Spotify exclusives genuinely have no
public feed, and a silently shorter list would look like a fetch that worked.
Such rows are skipped by ``discover`` because their ``rss_url`` is NULL.

The search API throttles hard: it answers 403 after roughly 20 requests in a
minute and stays that way for many minutes. A throttled search is *not* a show
without a feed, and recording it as one would quietly poison the collection --
the first run of this code marked 41 shows as feedless, among them The Ezra
Klein Show and This American Life. So searches are paced by
``spotify.search_delay_seconds``, and a throttle that outlasts the retries
aborts the run instead of being recorded.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata

import requests

from podcast_pipeline.config import SpotifyConfig
from podcast_pipeline.models import PodcastRecord
from podcast_pipeline.sources.apple import _to_record as _apple_record

logger = logging.getLogger(__name__)

SEARCH_URL = "https://itunes.apple.com/search"
THROTTLE_STATUSES = (403, 429)


class SpotifyResolveError(RuntimeError):
    """The iTunes search API stayed unavailable across every retry.

    Fatal on purpose: it means no show can be resolved, and continuing would
    record a chart's worth of podcasts as having no feed.
    """


class SpotifyChartsSource:
    def __init__(self, session: requests.Session, config: SpotifyConfig,
                 filter_health_only: bool = False, country: str = "us",
                 lookup_delay: float = 0.1):
        self.session = session
        self.config = config
        self.filter_health_only = filter_health_only
        self.country = country
        self.lookup_delay = lookup_delay
        self._last_search_at = 0.0

    @property
    def chart_name(self) -> str:
        return f"spotify_{self.country}_top"

    def top_podcasts(self, limit: int) -> list[PodcastRecord]:
        shows = self._chart(limit)
        records = []
        for show in shows:
            if self.filter_health_only and not _is_health_related(show):
                continue
            records.append(self._resolve(show))
            logger.info(f"  {len(records):3d}. {records[-1].title}"
                        f"{'' if records[-1].rss_url else '  [no feed found]'}")
            if len(records) >= limit:
                break
        matched = sum(1 for r in records if r.rss_url)
        logger.info(f"Fetched {len(records)} podcasts from Spotify chart {self.chart_name}; "
                    f"{matched} resolved to an RSS feed, {len(records) - matched} unmatched")
        return records

    def _chart(self, limit: int) -> list[dict]:
        # The endpoint ignores `limit` beyond its own page size, so the list is
        # trimmed here as well.
        params = {"region": self.country, "limit": str(limit)}
        logger.info(f"Fetching Spotify chart from {self.config.chart_url} ({params})")
        response = self.session.get(self.config.chart_url, params=params,
                                    headers={"Accept": "application/json"}, timeout=30)
        response.raise_for_status()
        return response.json()[:limit]

    def _resolve(self, show: dict) -> PodcastRecord:
        """Find the show's Apple listing so it has a feed the pipeline can read."""
        details = self._search_apple(show["showName"], show.get("showPublisher"))
        spotify_id = show["showUri"].rsplit(":", 1)[-1]

        if details is None:
            logger.warning(f"No Apple listing matched Spotify show {show['showName']!r} "
                           f"by {show.get('showPublisher')!r}; recorded without a feed")
            return PodcastRecord(
                source_id=f"spotify_{spotify_id}",
                title=show["showName"],
                description=show.get("showDescription"),
                publisher=show.get("showPublisher"),
                spotify_id=spotify_id,
                extra={"artwork_url": show.get("showImageUrl"),
                       "source": "spotify_charts", "rss_lookup": "unmatched"},
            )

        # Identify the podcast by its Apple id, exactly as the Apple source
        # does, so a show on both charts updates one row instead of adding a
        # second one under a Spotify source id.
        record = _apple_record({"id": str(details["collectionId"])}, details)
        record.spotify_id = spotify_id
        record.extra["source"] = "spotify_charts_itunes"
        record.extra["rss_lookup"] = "matched"
        record.extra["spotify_name"] = show["showName"]
        return record

    def _search_apple(self, name: str, publisher: str | None) -> dict | None:
        """The best iTunes match for a show title, or None if there is none.

        Raises ``SpotifyResolveError`` if the API could not be asked at all;
        None means it was asked and nothing matched.
        """
        results = self._search(name)
        wanted = _normalise(name)
        exact = [r for r in results if _normalise(r.get("collectionName", "")) == wanted]
        if not exact:
            return None
        if len(exact) > 1 and publisher:
            by_publisher = [r for r in exact
                            if _normalise(r.get("artistName", "")) == _normalise(publisher)]
            if by_publisher:
                exact = by_publisher
        # Ties are broken by the relevance order iTunes already returned.
        return exact[0]

    def _search(self, term: str) -> list[dict]:
        params = {"term": term, "entity": "podcast", "country": self.country,
                  "limit": self.config.match_candidates}
        for attempt in range(self.config.search_attempts):
            self._pace()
            try:
                response = self.session.get(SEARCH_URL, params=params, timeout=20)
            except requests.RequestException as e:
                logger.warning(f"iTunes search for {term!r} failed "
                               f"(attempt {attempt + 1}): {e}")
                time.sleep(self.config.search_delay_seconds * 2 ** attempt)
                continue
            if response.status_code in THROTTLE_STATUSES:
                wait = float(response.headers.get("Retry-After",
                                                  self.config.search_delay_seconds * 5 * 2 ** attempt))
                logger.warning(f"iTunes search throttled ({response.status_code}); "
                               f"waiting {wait:.0f}s before retrying {term!r}")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json().get("results") or []
        raise SpotifyResolveError(
            f"iTunes search unavailable after {self.config.search_attempts} attempts "
            f"(last term {term!r}). Every remaining show would be recorded as having "
            f"no feed, so the run is stopping; retry later or raise "
            f"spotify.search_delay_seconds.")

    def _pace(self) -> None:
        """Keep at least ``search_delay_seconds`` between searches."""
        elapsed = time.monotonic() - self._last_search_at
        if elapsed < self.config.search_delay_seconds:
            time.sleep(self.config.search_delay_seconds - elapsed)
        self._last_search_at = time.monotonic()


def _normalise(text: str) -> str:
    """Fold a show title to a form that survives punctuation and accent drift
    between the two catalogues (``The Journal.`` vs ``The Journal``)."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _is_health_related(show: dict) -> bool:
    from podcast_pipeline.sources.apple import HEALTH_KEYWORDS
    text = f"{show.get('showName', '')} {show.get('showDescription', '')}".lower()
    return any(keyword in text for keyword in HEALTH_KEYWORDS)
