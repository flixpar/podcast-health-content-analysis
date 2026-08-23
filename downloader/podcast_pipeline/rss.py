"""Podcast RSS feeds -> FeedEpisode records.

Only episode discovery lives here. Publisher-provided transcript files are
parsed in ``podcast_pipeline.transcripts.parsers``.
"""

from __future__ import annotations

import logging
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup

from podcast_pipeline.models import FeedEpisode

logger = logging.getLogger(__name__)


class FeedError(RuntimeError):
    """The feed could not be fetched or yielded no parseable entries."""


def fetch_feed(rss_url: str, session: requests.Session, timeout: int = 60) -> list[FeedEpisode]:
    """Download and parse a feed. Episodes come back newest first, as listed.

    The fetch goes through ``requests`` rather than ``feedparser.parse(url)``
    because feedparser applies no timeout of its own.
    """
    try:
        response = session.get(rss_url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        raise FeedError(f"fetch failed: {e}") from e
    return parse_feed(response.content, source=rss_url)


def parse_feed(content: bytes | str, source: str = "<bytes>") -> list[FeedEpisode]:
    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        raise FeedError(f"unparseable feed {source}: {feed.bozo_exception}")
    if feed.bozo:
        # feedparser is lenient; a feed with entries but an encoding quirk is usable.
        logger.debug(f"Feed {source} parsed with warnings: {feed.bozo_exception}")

    episodes = []
    for entry in feed.entries:
        episode = _parse_entry(entry)
        if episode is not None:
            episodes.append(episode)
    return episodes


def _parse_entry(entry) -> FeedEpisode | None:
    audio_url, audio_length, audio_type = None, 0, None
    for enclosure in entry.get("enclosures", []):
        if "audio" in (enclosure.get("type") or "").lower():
            audio_url = enclosure.get("href") or enclosure.get("url")
            audio_length = _to_int(enclosure.get("length"))
            audio_type = enclosure.get("type")
            break
    if not audio_url:
        return None   # trailers/announcements without audio are not episodes

    transcript = _transcript_info(entry)
    return FeedEpisode(
        guid=entry.get("id") or entry.get("guid") or audio_url,
        title=entry.get("title") or "",
        audio_url=audio_url,
        description=_clean_html(entry.get("description") or ""),
        audio_length=audio_length,
        audio_type=audio_type,
        published_date=_iso_date(entry.get("published_parsed")),
        duration_seconds=_duration_seconds(entry.get("itunes_duration")),
        season=_str_or_none(entry.get("itunes_season")),
        episode_number=_str_or_none(entry.get("itunes_episode")),
        episode_type=entry.get("itunes_episodetype") or "full",
        explicit=_is_explicit(entry.get("itunes_explicit")),
        transcript_url=transcript.get("url"),
        transcript_type=transcript.get("type"),
        transcript_language=transcript.get("language"),
        chapters_url=(entry.get("podcast_chapters") or {}).get("url"),
    )


def _transcript_info(entry) -> dict:
    """Publisher transcript advertised for an entry (Podcast 2.0 or link rel)."""
    candidates = []
    if entry.get("podcast_transcript"):
        candidates.append(entry["podcast_transcript"])
    candidates.extend(entry.get("podcast_transcripts") or [])
    for candidate in candidates:
        if candidate.get("url"):
            return {"url": candidate["url"],
                    "type": candidate.get("type", "text/plain"),
                    "language": candidate.get("language", "en")}

    for link in entry.get("links", []):
        rel = link.get("rel")
        rel = " ".join(rel) if isinstance(rel, list) else (rel or "")
        if "transcript" in rel.lower() and link.get("href"):
            return {"url": link["href"], "type": link.get("type", "text/plain"), "language": "en"}
    return {}


def _duration_seconds(value) -> int | None:
    """iTunes durations come as seconds, MM:SS, or HH:MM:SS."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    try:
        if ":" in text:
            parts = [int(float(p)) for p in text.split(":")]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            return None
        return int(float(text))
    except ValueError:
        return None


def _iso_date(date_tuple) -> str | None:
    if not date_tuple:
        return None
    try:
        return datetime(*date_tuple[:6]).isoformat()
    except (TypeError, ValueError):
        return None


def _clean_html(text: str, max_length: int = 1000) -> str:
    if not text:
        return ""
    plain = " ".join(BeautifulSoup(text, "html.parser").get_text().split())
    return plain[:max_length - 3] + "..." if len(plain) > max_length else plain


def _is_explicit(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"yes", "true", "1", "explicit"}


def _to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _str_or_none(value) -> str | None:
    return None if value in (None, "") else str(value)
