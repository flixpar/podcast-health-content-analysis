"""Podcast RSS feeds -> FeedEpisode records.

Only episode discovery lives here. Publisher-provided transcript files are
parsed in ``podcast_pipeline.transcripts.parsers``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

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
        response = _get(session, rss_url, timeout)
    except requests.RequestException as e:
        raise FeedError(f"fetch failed: {e}") from e
    return parse_feed(response.content, source=rss_url)


#: Links to the next (older) page of a feed: RFC 5005 paged feeds use "next",
#: archived feeds "prev-archive". Audioboom (?page=2), Amperwave (?offset=N)
#: and SoundCloud (?before=ID) all advertise their pages this way.
NEXT_PAGE_RELS = ("next", "prev-archive")

#: Megaphone serves a per-show number of items by default (ESPN shows 200,
#: ABC's 20/20 60) but honours ``limit`` and ``offset`` -- through its own
#: host only; proxies in front of it (rss.pdrl.fm, introcast) drop the query.
MEGAPHONE_HOST = "feeds.megaphone.fm"


@dataclass
class FeedRead:
    """A feed read across its pages: the merged episodes, newest first as listed."""

    episodes: list[FeedEpisode]
    pages: int
    stopped: str             # 'complete' | 'loop' | 'no_new_items' | 'max_pages' | 'page_error'
    error: str | None = None

    @property
    def partial(self) -> bool:
        """Older pages exist that this read did not get."""
        return self.stopped in ("max_pages", "page_error")


def read_feed(rss_url: str, session: requests.Session, timeout: int = 60, max_pages: int = 1,
              page_size: int = 1000, page_delay: float = 0.0) -> FeedRead:
    """Read a feed and, up to ``max_pages`` documents, the older pages it links to.

    A page that adds no GUID not already seen ends the walk, as does a link
    back to a page already read. A failure on the first page raises
    ``FeedError``; a failure on a later one keeps what the earlier pages gave
    and is reported in ``error``. Page one is kept exactly as listed, so an
    unpaged feed reads the same as ``fetch_feed`` (a Megaphone feed is asked
    for ``page_size`` items rather than its default); later pages contribute
    only GUIDs not seen before.
    """
    megaphone = urlsplit(rss_url).netloc.lower() == MEGAPHONE_HOST
    url = _with_query(rss_url, limit=page_size) if megaphone else rss_url
    episodes: list[FeedEpisode] = []
    guids: set[str] = set()
    visited: set[str] = set()
    pages = 0
    while True:
        try:
            try:
                response = _get(session, url, timeout)
            except requests.RequestException as e:
                raise FeedError(f"fetch failed: {e}") from e
            feed, page = _parse(response.content, url)
        except FeedError as e:
            if pages == 0:
                raise
            logger.warning(f"{rss_url}: page {pages + 1} ({url}) failed; keeping {pages} pages: {e}")
            return FeedRead(episodes, pages, "page_error", f"page {pages + 1} failed: {e}"[:400])
        pages += 1
        visited.update((url, response.url))
        new = [ep for ep in page if ep.guid not in guids]
        episodes.extend(page if pages == 1 else new)
        guids.update(ep.guid for ep in page)
        if pages > 1 and not new:
            return FeedRead(episodes, pages, "no_new_items")

        next_url = _next_page(feed, response.url)
        if next_url is None and megaphone and len(feed.entries) >= page_size:
            next_url = _with_query(rss_url, limit=page_size, offset=pages * page_size)
        if next_url is None:
            return FeedRead(episodes, pages, "complete")
        if next_url in visited:
            return FeedRead(episodes, pages, "loop")
        if pages >= max_pages:
            logger.warning(f"{rss_url}: stopped after {pages} pages; {next_url} not read")
            return FeedRead(episodes, pages, "max_pages",
                            f"stopped at max_feed_pages={max_pages}; {next_url} not read")
        url = next_url
        time.sleep(page_delay)


def _next_page(feed, base_url: str) -> str | None:
    for rel in NEXT_PAGE_RELS:
        for link in feed.feed.get("links", []):
            if link.get("rel") == rel and link.get("href"):
                return urljoin(base_url, link["href"])
    return None


def _with_query(url: str, **params) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in params]
    query += [(k, str(v)) for k, v in params.items()]
    return urlunsplit(parts._replace(query=urlencode(query)))


def _get(session: requests.Session, rss_url: str, timeout: int) -> requests.Response:
    """GET a feed, retrying uncompressed if the server's gzip body is corrupt.

    Megaphone serves some feeds (observed on Vox's ``Today, Explained``) with
    ``Content-Encoding: gzip`` and a body that fails to inflate, while the same
    URL returns a perfectly good document when compression is not negotiated.
    Without this retry the show looks like a dead feed and contributes nothing.
    """
    try:
        response = session.get(rss_url, timeout=timeout)
    except requests.exceptions.ContentDecodingError:
        logger.warning(f"{rss_url} sent an undecodable compressed body; retrying uncompressed")
        response = session.get(rss_url, timeout=timeout,
                               headers={"Accept-Encoding": "identity"})
    response.raise_for_status()
    return response


def parse_feed(content: bytes | str, source: str = "<bytes>") -> list[FeedEpisode]:
    return _parse(content, source)[1]


def _parse(content: bytes | str, source: str):
    """The parsed document and its episodes."""
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
    return feed, episodes


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
    # Feedburner feeds point every enclosure at a feedproxy.google.com redirect,
    # which Google retired, so those URLs are dead. The feed also carries the
    # publisher's own URL; archived feeds from before ~2020 are full of these.
    # The GUID fallback keeps using the enclosure as listed, so an item without
    # a <guid> keeps the identity it had before this rewrite existed.
    guid = entry.get("id") or entry.get("guid") or audio_url
    original = entry.get("feedburner_origenclosurelink")
    if original and "feedproxy.google.com" in audio_url:
        audio_url = original

    transcript = _transcript_info(entry)
    return FeedEpisode(
        guid=guid,
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
