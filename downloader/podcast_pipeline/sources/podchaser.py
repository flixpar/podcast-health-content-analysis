"""Top podcasts from the Podchaser GraphQL API (requires API credentials)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

import requests

from podcast_pipeline.config import PodchaserConfig
from podcast_pipeline.models import PodcastRecord

logger = logging.getLogger(__name__)

PODCAST_FIELDS = """
    id title description webUrl rssUrl applePodcastsId spotifyId latestEpisodeDate
    categories { title }
"""

CHARTS_QUERY = f"""
    query Charts($limit: Int!, $country: String!, $category: String!,
                 $platform: ChartPlatform!, $day: Date!) {{
        charts(platform: $platform, country: $country, category: $category,
               day: $day, first: $limit) {{
            data {{ podcast {{ {PODCAST_FIELDS} }} position }}
            paginatorInfo {{ hasMorePages currentPage }}
        }}
    }}
"""

SEARCH_HEALTH_QUERY = f"""
    query SearchHealthPodcasts($limit: Int!, $cursor: String) {{
        podcasts(searchTerm: "health",
                 filters: {{ categories: ["Health & Fitness", "Medicine", "Mental Health", "Nutrition"] }},
                 sort: {{ sortBy: FOLLOWER_COUNT, direction: DESCENDING }},
                 first: $limit, cursor: $cursor) {{
            data {{ {PODCAST_FIELDS} }}
            cursorInfo {{ total nextCursor }}
        }}
    }}
"""

SEARCH_ALL_QUERY = f"""
    query SearchAllPodcasts($limit: Int!, $cursor: String) {{
        podcasts(sort: {{ sortBy: FOLLOWER_COUNT, direction: DESCENDING }},
                 first: $limit, cursor: $cursor) {{
            data {{ {PODCAST_FIELDS} }}
            cursorInfo {{ total nextCursor }}
        }}
    }}
"""

AUTH_MUTATION = """
    mutation Auth($id: String!, $secret: String!) {
        requestAccessToken(input: {grant_type: CLIENT_CREDENTIALS, client_id: $id, client_secret: $secret}) {
            access_token expires_in
        }
    }
"""


class PodchaserError(RuntimeError):
    pass


class PodchaserSource:
    def __init__(self, session: requests.Session, config: PodchaserConfig,
                 filter_health_only: bool = False, country: str = "US"):
        if not (config.client_id and config.client_secret):
            raise PodchaserError("Podchaser credentials missing: set podchaser.client_id/client_secret "
                                 "in config.json or PODCHASER_CLIENT_ID/PODCHASER_CLIENT_SECRET")
        self.session = session
        self.config = config
        self.filter_health_only = filter_health_only
        self.country = country
        self.access_token: str | None = None
        self.token_expires_at = datetime.min

    @property
    def chart_name(self) -> str:
        """Identifier recorded in ``podcast_charts.chart``."""
        return f"podchaser_{self.country.lower()}_top"

    # --- auth / transport ---------------------------------------------------

    def _authenticate(self) -> None:
        logger.info("Authenticating with Podchaser")
        data = self._post(AUTH_MUTATION, {"id": self.config.client_id,
                                          "secret": self.config.client_secret}, auth=False)
        token = data["requestAccessToken"]
        self.access_token = token["access_token"]
        # Renew an hour early rather than racing the expiry.
        self.token_expires_at = datetime.now() + timedelta(seconds=token.get("expires_in", 31536000) - 3600)

    def _post(self, query: str, variables: dict, auth: bool = True) -> dict:
        if auth and (not self.access_token or datetime.now() >= self.token_expires_at):
            self._authenticate()
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = f"Bearer {self.access_token}"
        response = self.session.post(self.config.api_url, json={"query": query, "variables": variables},
                                     headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise PodchaserError(f"GraphQL errors: {payload['errors']}")
        return payload["data"]

    # --- podcasts -----------------------------------------------------------

    def top_podcasts(self, limit: int) -> list[PodcastRecord]:
        records: list[PodcastRecord] = []
        seen: set[str] = set()

        def add(raw: dict) -> None:
            record = _to_record(raw)
            if record.source_id not in seen:
                seen.add(record.source_id)
                records.append(record)

        # Charts first; they are the better signal when available.
        try:
            data = self._post(CHARTS_QUERY, {
                "limit": min(limit, 20), "country": self.country,
                "category": "Health & Fitness" if self.filter_health_only else "All",
                "platform": "APPLE_PODCASTS",
                "day": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            })
            for item in (data.get("charts") or {}).get("data", []):
                add(item["podcast"])
        except (PodchaserError, requests.RequestException, KeyError) as e:
            logger.warning(f"Podchaser charts query failed ({e}); falling back to search")

        # Search by follower count for the rest.
        query = SEARCH_HEALTH_QUERY if self.filter_health_only else SEARCH_ALL_QUERY
        cursor = None
        while len(records) < limit:
            variables = {"limit": min(limit - len(records), 50)}
            if cursor:
                variables["cursor"] = cursor
            page = self._post(query, variables).get("podcasts") or {}
            for raw in page.get("data", []):
                add(raw)
            cursor = (page.get("cursorInfo") or {}).get("nextCursor")
            if not cursor or not page.get("data"):
                break
            time.sleep(0.5)

        logger.info(f"Fetched {len(records)} podcasts from Podchaser")
        return records[:limit]


def _to_record(raw: dict) -> PodcastRecord:
    return PodcastRecord(
        source_id=str(raw["id"]),
        title=raw.get("title") or "",
        description=raw.get("description"),
        rss_url=raw.get("rssUrl"),
        apple_podcasts_id=_str_or_none(raw.get("applePodcastsId")),
        spotify_id=_str_or_none(raw.get("spotifyId")),
        categories=[c.get("title") for c in raw.get("categories") or [] if c.get("title")],
        latest_episode_date=raw.get("latestEpisodeDate"),
        extra={"web_url": raw.get("webUrl"), "source": "podchaser"},
    )


def _str_or_none(value) -> str | None:
    return None if value in (None, "") else str(value)
