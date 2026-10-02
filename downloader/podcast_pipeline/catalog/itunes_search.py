"""The paced iTunes search API, and the rules for accepting one of its results.

Two callers need a podcast found by title: the Spotify chart (which carries no
RSS URLs) and ``resolve`` (chart-archive titles with no Apple id, and Apple ids
the lookup API no longer knows).

The search API throttles hard: it answers 403 after roughly 20 requests in a
minute and stays that way for many minutes. A throttled search is *not* a show
without a feed, and recording it as one quietly poisons the collection -- the
first Spotify run marked 41 shows as feedless, among them The Ezra Klein Show.
So searches are paced, and a throttle that outlasts the retries raises
instead of returning an empty result.

Matching (``best_match``) works on titles folded by ``normalise``:

* ``exact``: the folded titles are equal. Among several, a publisher match
  wins, then iTunes' own relevance order.
* ``fuzzy``: equal after a conservative trim -- a leading "the", a trailing
  "podcast" / "the podcast", or a subtitle after ":", " - ", " | " or " with "
  -- where at least one side is used whole, so two different subtitles on the
  same head never match. A fuzzy match is only accepted when the publisher
  matches as well.

When the publisher is known, a fuzzy match whose publisher agrees is preferred
to an exact title whose publisher does not: a generic title ("Betrayal",
"Suspect") is shared by many unrelated shows.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://itunes.apple.com/search"
THROTTLE_STATUSES = (403, 429)

#: Where a title's subtitle starts. " with " covers "Show with Host Name".
SUBTITLE_SEPARATORS = re.compile(r"\s*:\s*|\s+[-–—|]\s+|\s+with\s+", re.IGNORECASE)
#: A trimmed title shorter than this (folded) is too generic to match on.
MIN_FUZZY_LENGTH = 4
#: Words that say nothing about who publishes a show.
PUBLISHER_STOPWORDS = {"the", "and", "a", "of", "inc", "llc", "ltd"}


class ITunesSearchUnavailable(RuntimeError):
    """The iTunes search API stayed unavailable across every retry.

    Fatal on purpose: no title can be resolved, and continuing would record
    every remaining one as having no match.
    """


class ITunesSearch:
    """Paced podcast searches with throttle handling.

    ``error`` is the exception class raised when the API stays unavailable, so
    a caller can keep its own (``SpotifyResolveError``).
    """

    def __init__(self, session: requests.Session, delay_seconds: float, attempts: int,
                 limit: int = 10, country: str = "us",
                 error: type[ITunesSearchUnavailable] = ITunesSearchUnavailable,
                 advice: str = "retry later or raise search_delay_seconds"):
        self.session = session
        self.delay_seconds = delay_seconds
        self.attempts = attempts
        self.limit = limit
        self.country = country
        self.error = error
        self.advice = advice
        self.requests = 0
        self._last_search_at = 0.0

    def search(self, term: str) -> list[dict]:
        """iTunes podcast records for ``term``, in iTunes' relevance order.

        An empty list means the API answered and found nothing; a throttle or
        outage that outlasts ``attempts`` raises ``self.error``.
        """
        params = {"term": term, "entity": "podcast", "country": self.country,
                  "limit": self.limit}
        for attempt in range(self.attempts):
            self._pace()
            self.requests += 1
            try:
                response = self.session.get(SEARCH_URL, params=params, timeout=20)
            except requests.RequestException as e:
                logger.warning(f"iTunes search for {term!r} failed (attempt {attempt + 1}): {e}")
                time.sleep(self.delay_seconds * 2 ** attempt)
                continue
            if response.status_code in THROTTLE_STATUSES:
                wait = float(response.headers.get("Retry-After",
                                                  self.delay_seconds * 5 * 2 ** attempt))
                logger.warning(f"iTunes search throttled ({response.status_code}); "
                               f"waiting {wait:.0f}s before retrying {term!r}")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json().get("results") or []
        raise self.error(
            f"iTunes search unavailable after {self.attempts} attempts (last term {term!r}). "
            f"A throttled search is not a podcast without a match, so the run is stopping "
            f"instead of recording the rest as unmatched; {self.advice}.")

    def _pace(self) -> None:
        """Keep at least ``delay_seconds`` between searches."""
        elapsed = time.monotonic() - self._last_search_at
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self._last_search_at = time.monotonic()


# --- matching ----------------------------------------------------------------

def normalise(text: str | None) -> str:
    """Fold a title to a form that survives punctuation and accent drift
    between catalogues (``The Journal.`` vs ``The Journal``)."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _words(text: str | None) -> list[str]:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", text.lower().replace("'", "").replace("’", ""))


def core_title(text: str | None) -> str:
    """The folded title without a leading "the" or a trailing "(the) podcast"."""
    words = _words(text)
    if words[:1] == ["the"] and len(words) > 1:
        words = words[1:]
    if words[-2:] == ["the", "podcast"] and len(words) > 2:
        words = words[:-2]
    elif words[-1:] == ["podcast"] and len(words) > 1:
        words = words[:-1]
    return "".join(words)


def title_head(text: str | None) -> str | None:
    """The title before its subtitle, or None if it has none."""
    head = SUBTITLE_SEPARATORS.split(text or "", maxsplit=1)[0]
    return head if head.strip() and head.strip() != (text or "").strip() else None


def fuzzy_rule(chart_title: str, candidate_title: str) -> str | None:
    """How two titles match in the second tier, or None if they do not.

    One side is always taken whole, so "Crime: Part One" and "Crime: Part Two"
    (same head, different subtitles) do not match.
    """
    chart_core, cand_core = core_title(chart_title), core_title(candidate_title)
    if min(len(chart_core), len(cand_core)) < MIN_FUZZY_LENGTH:
        return None
    if chart_core == cand_core:
        return "stripped"
    cand_head = title_head(candidate_title)
    if cand_head and core_title(cand_head) == chart_core:
        return "chart_title_is_candidate_head"
    chart_head = title_head(chart_title)
    if chart_head and core_title(chart_head) == cand_core:
        return "candidate_title_is_chart_head"
    return None


def publisher_matches(wanted: str | None, candidate: str | None) -> bool:
    """Whether two publisher strings plausibly name the same publisher.

    Equal when folded; or the words of one are a subset of the other's
    ("NBC News" / "NBC News Studios", "Wondery" / "Wondery | Campside"); or
    they share a whole credited party ("Glennon Doyle & Cadence13" /
    "Glennon Doyle & Audacy").
    """
    if not normalise(wanted) or not normalise(candidate):
        return False
    if normalise(wanted) == normalise(candidate):
        return True
    a = set(_words(wanted)) - PUBLISHER_STOPWORDS
    b = set(_words(candidate)) - PUBLISHER_STOPWORDS
    if a and b and (a <= b or b <= a):
        return True
    split = re.compile(r"\s*(?:&|\+|,|;|/|\||\band\b)\s*", re.IGNORECASE)
    parts_a = {normalise(p) for p in split.split(wanted)} - {""}
    parts_b = {normalise(p) for p in split.split(candidate)} - {""}
    return any(len(p) >= MIN_FUZZY_LENGTH for p in parts_a & parts_b)


@dataclass
class Match:
    record: dict              # the iTunes search result
    tier: str                 # 'exact' | 'fuzzy'
    rule: str                 # 'title' or one of fuzzy_rule's values
    publisher_match: bool | None   # None: no publisher was known to compare
    position: int             # 0-based relevance position in the results

    def evidence(self) -> dict:
        r = self.record
        return {"tier": self.tier, "rule": self.rule, "publisher_match": self.publisher_match,
                "position": self.position, "candidate_id": str(r.get("collectionId")),
                "candidate_title": r.get("collectionName"),
                "candidate_publisher": r.get("artistName"),
                "candidate_feed": r.get("feedUrl")}


def best_match(results: list[dict], title: str, publishers: list[str] | None = None,
               fuzzy: bool = True) -> Match | None:
    """The accepted candidate for ``title`` among search ``results``, or None.

    Preference: exact title + publisher, fuzzy title + publisher, exact title
    alone; each tier in relevance order. Fuzzy needs a known publisher.
    """
    publishers = [p for p in publishers or [] if normalise(p)]
    wanted = normalise(title)
    exact_pub, fuzzy_pub, exact_any = [], [], []
    for position, record in enumerate(results):
        name = record.get("collectionName") or ""
        pub = (any(publisher_matches(p, record.get("artistName")) for p in publishers)
               if publishers else None)
        if wanted and normalise(name) == wanted:
            match = Match(record, "exact", "title", pub, position)
            (exact_pub if pub else exact_any).append(match)
        elif fuzzy and pub:
            rule = fuzzy_rule(title, name)
            if rule:
                fuzzy_pub.append(Match(record, "fuzzy", rule, True, position))
    for tier in (exact_pub, fuzzy_pub, exact_any):
        if tier:
            return tier[0]
    return None
