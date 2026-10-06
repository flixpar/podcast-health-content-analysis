"""Where a study's episode windows are not reached by what we have, and why.

A window is a *gap* when no episode of the member falls in it, or when it
opens before the earliest episode we know for that podcast. Not every gap is
missing data: a finished limited series keeps charting on back-catalog
listening, and a chart-identity error can put a show in months before it
existed. Each gap window gets a ``gap_class`` from the evidence we hold:

``not_publishing``
    A *listing* covers the whole window and none of its items fall inside. A
    listing is one read of a feed -- the live read recorded in
    ``podcast_feeds``, or a Wayback capture recorded in ``wayback_probes`` --
    and a feed lists its items contiguously, so it covers every day from its
    oldest item to the moment it was read.
``before_launch``
    The window ends before the show's earliest known episode (any source:
    live feed, Wayback, imported), and that episode looks like the first: it
    is marked as a trailer, an introduction or episode 1, or the live feed is
    complete (it lists every episode we hold back to that one, has at least
    ``MIN_COMPLETE_ITEMS`` items, and shows no sign of truncation). A show
    charting before it existed is a chart-identity or archive error -- or a
    feed that was reset and relaunched (The Ramsey Show's starts in 2022 with
    "Introducing The Ramsey Show"). These are for review, not archive search.
``missing``
    Episodes existed and we lack them. Either the window precedes the
    earliest known episode and the feed demonstrably drops items: that
    episode is numbered past 1 (tag or title), the live feed no longer lists
    older episodes we hold, a listing lists fewer items than we hold in its
    span, its length is a page size, its oldest few items are isolated, or
    its read stopped before the last page. Or the window lies between
    episodes we hold, no listing covers it, and the show published within
    ``ACTIVE_NEIGHBOUR_DAYS`` on both sides or its feed drops items.
``unknown``
    Not enough evidence either way.

A partial window holding the show's launch (the earliest episode is inside it
and marked as a start) is not a gap at all: nothing preceded it.

``discover-archived`` targets ``missing`` and ``unknown`` windows
(``TARGET_CLASSES``): ``PodcastGaps.windows`` holds only those.
"""

from __future__ import annotations

import json
import re
import sqlite3
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import date, timedelta

GAP_CLASSES = ("missing", "unknown", "not_publishing", "before_launch")
#: What archive searches should look for: data that existed, or might have.
TARGET_CLASSES = ("missing", "unknown")

#: Publication dates before this are feed junk (epoch defaults), not history.
EARLIEST_PLAUSIBLE_DATE = "1995"

#: Feed lengths that are a host's page size or cap rather than a catalogue.
#: The count we record excludes items without audio, so it can fall just under.
PAGE_SIZES = frozenset({50, 100, 150, 200, 250, 300, 500, 1000})
PAGE_SIZE_SLACK = 0.02

#: A live feed with fewer items than this proves nothing about completeness.
MIN_COMPLETE_ITEMS = 5
#: A feed whose 5th-oldest item is over a year after its oldest has isolated
#: old items (The Daily's truncated feed keeps one 2021 and one 2022 episode).
ISOLATED_RANK = 4
ISOLATED_DAYS = 365
#: A listing holding fewer items than we hold episodes in its date span (by
#: more than this share, plus two) skips items and covers nothing.
LISTING_SLACK = 0.1

#: Episodes this close to the earliest one count as "the first episodes" when
#: looking for a launch marker (a trailer and episode 1 often share a week).
LAUNCH_SPAN_DAYS = 14

#: An uncovered window between episodes we hold is ``missing`` when the show
#: published within this many days on both sides of it; further apart, the
#: show may have been on hiatus and the window is ``unknown``.
ACTIVE_NEIGHBOUR_DAYS = 92

_NUMBER_TITLE = re.compile(r"\b(?:episode|ep|no)\.?\s*#?\s*(\d{1,4})\b|(?:^|\s)#(\d{1,4})\b", re.IGNORECASE)
_SEASON_TITLE = re.compile(r"\b(?:season\s*|s)(\d{1,2})\s*[:,]?\s*(?:e|ep\b|episode\b)", re.IGNORECASE)
_LAUNCH_TITLE = re.compile(
    r"\b(trailer|teaser|introducing|coming soon|sneak (peek|preview)|welcome to|pilot)\b"
    r"|\b(episode|ep\.?|chapter)\s*#?0*[01]\b|^\s*#?0*1\s*[:.)\-|]|\bs0*1\s*:?\s*e0*1\b",
    re.IGNORECASE)


@dataclass
class GapWindow:
    label: str
    start: str
    end: str
    empty: bool                # no study episode at all; otherwise partial
    gap_class: str
    reason: str


@dataclass
class PodcastGaps:
    podcast_id: int
    title: str
    entity: str
    earliest_known: str | None                 # earliest published_date we hold, any source
    windows: list[tuple[str, str, str]] = field(default_factory=list)   # targets: (label, start, end)
    empty: set[str] = field(default_factory=set)   # target labels with no episode at all
    classified: list[GapWindow] = field(default_factory=list)          # every gap window
    launch_windows: list[str] = field(default_factory=list)  # partial windows holding the launch

    @property
    def span(self) -> tuple[str, str]:
        return min(w[1] for w in self.windows), max(w[2] for w in self.windows)


@dataclass
class Evidence:
    """What we know about one podcast's publishing history."""

    dates: list[str]                          # plausible publication days we hold, sorted
    listings: list[tuple[str, str]]           # (oldest item day, read day), merged
    first: str | None                         # earliest known day, any source
    launch: str | None                        # why ``first`` is the show's first episode
    truncated: str | None                     # why the feed drops old episodes
    skipping: str | None = None               # a listing that omits episodes we hold


def study_gaps(conn: sqlite3.Connection, study: str,
               classes: tuple[str, ...] = TARGET_CLASSES) -> list[PodcastGaps]:
    """Gap windows per resolved member of ``study``, oldest podcast-gap first.

    Only podcasts with a gap window in ``classes`` are returned, and
    ``windows``/``empty`` list only those windows; ``classified`` always holds
    every gap window with its class.
    """
    gaps = [g for g in classify_study(conn, study, classes) if g.windows]
    return sorted(gaps, key=lambda g: g.span[0])


def classify_study(conn: sqlite3.Connection, study: str,
                   classes: tuple[str, ...] = TARGET_CLASSES) -> list[PodcastGaps]:
    """Every resolved member podcast with a gap or launch window, by podcast id."""
    rows = conn.execute("""
        WITH counts AS (
            SELECT entity, window_label, COUNT(*) AS n
            FROM study_episodes WHERE study = ? GROUP BY entity, window_label
        )
        SELECT m.podcast_id, p.title, m.entity, w.label, w.start_date, w.end_date,
               COALESCE(c.n, 0) AS n
        FROM study_windows w
        JOIN study_members m ON m.study = w.study AND m.entity = w.entity
        JOIN podcasts p ON p.id = m.podcast_id
        LEFT JOIN counts c ON c.entity = w.entity AND c.window_label = w.label
        WHERE w.study = ? AND m.podcast_id IS NOT NULL
        ORDER BY m.podcast_id, w.start_date
    """, (study, study)).fetchall()
    by_podcast: dict[int, PodcastGaps] = {}
    evidence: dict[int, Evidence] = {}
    # Keyed by podcast: a study rewrites a manually linked 'title:K' member into
    # the 'apple:'/'podcast:' entity of the podcast it resolves to.
    manual = {r[0] for r in conn.execute(
        "SELECT podcast_id FROM entity_links WHERE method = 'manual' AND podcast_id IS NOT NULL")}
    for r in rows:
        pid = r["podcast_id"]
        if pid not in evidence:
            evidence[pid] = podcast_evidence(conn, pid)
        ev = evidence[pid]
        gaps = by_podcast.setdefault(pid, PodcastGaps(pid, r["title"], r["entity"], ev.first))
        verdict = classify(ev, r["start_date"], r["end_date"], r["n"])
        if verdict is None:
            continue
        gap_class, reason = verdict
        if gap_class == "before_launch" and pid in manual:
            # A hand-made identity link usually means the show was renamed or
            # re-hosted, so the matched feed's "first episode" is that feed's,
            # not the show's: its older episodes may exist under an older URL.
            gap_class, reason = "unknown", f"{reason}; but the identity is a manual link, so the " \
                                           f"feed may postdate the show"
        if gap_class == "launch":
            gaps.launch_windows.append(r["label"])
            continue
        gaps.classified.append(GapWindow(r["label"], r["start_date"], r["end_date"], r["n"] == 0,
                                         gap_class, reason))
        if gap_class in classes:
            gaps.windows.append((r["label"], r["start_date"], r["end_date"]))
            if r["n"] == 0:
                gaps.empty.add(r["label"])
    return [g for g in by_podcast.values() if g.classified or g.launch_windows]


def classify(ev: Evidence, start: str, end: str, n: int) -> tuple[str, str] | None:
    """The gap class of window ``[start, end)`` holding ``n`` study episodes.

    None when the window is not a gap; ``("launch", ...)`` for a partial
    window that holds the show's launch.
    """
    if n > 0 and ev.first is not None and ev.first <= start:
        return None
    if ev.first is None:
        return "unknown", "no dated episode from any source"
    if covered(ev.listings, start, end):
        if n > 0:
            return None
        oldest, read = next((o, r) for o, r in ev.listings if o <= start and end <= _next_day(r))
        return "not_publishing", f"a listing spans {oldest}..{read} and has nothing in the window"
    if ev.first >= end or n > 0:
        # Before the earliest episode we know, or the window that holds it.
        # Evidence that the feed has lost its older items outranks a launch
        # marker: a renamed show's "Introducing ..." trailer looks like a
        # launch but is not one (The Ramsey Show, 2022).
        if ev.truncated or ev.skipping:
            return "missing", f"window precedes the earliest known episode ({ev.first}): " \
                              f"{ev.truncated or ev.skipping}"
        if ev.launch:
            if n > 0:
                return "launch", ev.launch
            return "before_launch", f"window ends before the first episode ({ev.first}): {ev.launch}"
        return "unknown", f"window precedes the earliest known episode ({ev.first}); no evidence " \
                          f"whether it was the first"
    # After the earliest episode, empty, and no listing covers it.
    before = max((d for d in ev.dates if d < start), default=None)
    after = min((d for d in ev.dates if d >= end), default=None)
    if before and after:
        if _days(before, start) <= ACTIVE_NEIGHBOUR_DAYS and _days(end, after) <= ACTIVE_NEIGHBOUR_DAYS:
            return "missing", f"episodes on {before} and {after} around it, and no listing covers it"
        if ev.truncated:
            return "missing", (f"between episodes on {before} and {after}, no listing covers it, "
                               f"and the show's feed drops episodes: {ev.truncated}")
    return "unknown", f"no listing covers it; nearest episodes {before} and {after}"


def covered(listings: list[tuple[str, str]], start: str, end: str) -> bool:
    """Whether one merged listing spans all of ``[start, end)``."""
    return any(oldest <= start and end <= _next_day(read) for oldest, read in listings)


def podcast_evidence(conn: sqlite3.Connection, podcast_id: int) -> Evidence:
    episodes = conn.execute("""
        SELECT substr(published_date, 1, 10) AS day, title, metadata FROM episodes
        WHERE podcast_id = ? AND published_date >= ? ORDER BY published_date
    """, (podcast_id, EARLIEST_PLAUSIBLE_DATE)).fetchall()
    dates = [e["day"] for e in episodes]
    # Publication days, not episodes: a copy re-issued under a new GUID and a
    # new title must not make a listing look like it skips items.
    days = sorted(set(dates))

    listings = _listings(conn, podcast_id)
    spans, skipping = [], []
    for kind, oldest, read, count in listings:
        held = bisect_right(days, read) - bisect_left(days, oldest)
        if count is not None and held > count * (1 + LISTING_SLACK) + 2:
            # It lists fewer items than we hold in its span, so it is not contiguous:
            # a truncated feed that keeps (or re-surfaces) a few old episodes.
            skipping.append(f"a {kind} read on {read} lists {count} items, but we hold episodes "
                            f"on {held} days from {oldest} on, so it skips some")
        else:
            spans.append((oldest, read))
    live = [(oldest, count) for kind, oldest, _read, count in listings if kind == "live feed"]
    partial = [oldest for kind, oldest, _read, _count in listings if kind == "partial live feed"]
    capped = [oldest for kind, oldest, _read, _count in listings if kind == "capped live feed"]

    first = min(dates[:1] + [o for _k, o, _r, _c in listings], default=None)
    launch = truncated = None
    if first is not None:
        horizon = (date.fromisoformat(first) + timedelta(days=LAUNCH_SPAN_DAYS)).isoformat()
        earliest = [e for e in episodes if e["day"] <= horizon]
        launch = _launch_marker(earliest)
        truncated = _truncation(earliest, dates, live, first)
        if truncated is None and partial and min(partial) <= first:
            truncated = "the feed's read stopped before its last page"
        if truncated is None and capped and min(capped) <= first:
            truncated = "the feed lists older items than discovery kept (discovery.max_episodes_per_podcast)"
        if launch is None and truncated is None and not skipping:
            launch = _complete_feed(live, first)
    return Evidence(dates, merge(spans), first, launch, truncated, skipping[0] if skipping else None)


def _listings(conn: sqlite3.Connection, podcast_id: int) -> list[tuple[str, str, str, int | None]]:
    """(kind, oldest item day, read day, item count) for every read of a feed we know of."""
    out = []
    for f in conn.execute("""
        SELECT url, item_count, oldest_item, last_read_at, last_status FROM podcast_feeds
        WHERE podcast_id = ? AND last_status LIKE 'ok%' AND last_read_at IS NOT NULL
    """, (podcast_id,)):
        oldest = f["oldest_item"] if (f["oldest_item"] or "") >= EARLIEST_PLAUSIBLE_DATE else None
        if oldest is None:
            # Undated or junk-dated items: the earliest plausible item this feed gave us.
            oldest = conn.execute("""
                SELECT MIN(e.published_date) FROM episodes e JOIN episode_sources es ON es.episode_id = e.id
                WHERE e.podcast_id = ? AND es.source = 'feed' AND es.ref = ? AND e.published_date >= ?
            """, (podcast_id, f["url"], EARLIEST_PLAUSIBLE_DATE)).fetchone()[0]
        held_count, held_oldest = conn.execute("""
            SELECT COUNT(*), MIN(e.published_date) FROM episodes e
            JOIN episode_sources es ON es.episode_id = e.id
            WHERE e.podcast_id = ? AND es.source = 'feed' AND es.ref = ? AND e.published_date >= ?
        """, (podcast_id, f["url"], EARLIEST_PLAUSIBLE_DATE)).fetchone()
        if oldest and f["item_count"] and 0 < held_count < f["item_count"]:
            # discover keeps only the newest max_episodes_per_podcast items of a
            # feed, so the span we actually hold starts later than the feed's
            # oldest item; months between were listed but not kept, and are
            # missing, not "not publishing".
            oldest, capped = held_oldest, True
        else:
            capped = False
        if oldest:
            # A read cut short ("ok, partial: ...") is still contiguous, but not the whole feed.
            kind = "live feed" if f["last_status"] == "ok" else "partial live feed"
            if capped:
                kind = "capped live feed"
            out.append((kind, oldest[:10], f["last_read_at"][:10], f["item_count"]))
    for p in conn.execute("SELECT detail FROM wayback_probes WHERE podcast_id = ? AND detail IS NOT NULL",
                          (podcast_id,)):
        for c in json.loads(p["detail"]).get("captures_used", []):
            if c.get("oldest"):
                ts = c["timestamp"]
                out.append(("Wayback capture", c["oldest"], f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", c.get("episodes")))
    return out


def merge(spans: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Union of listing spans; spans that touch (a day apart) join."""
    merged: list[list[str]] = []
    for oldest, read in sorted(spans):
        if merged and oldest <= _next_day(merged[-1][1]):
            merged[-1][1] = max(merged[-1][1], read)
        else:
            merged.append([oldest, read])
    return [(o, r) for o, r in merged]


def _launch_marker(earliest) -> str | None:
    for e in earliest:
        meta = json.loads(e["metadata"] or "{}")
        if (meta.get("episode_type") or "").lower() == "trailer":
            return f"{e['day']} {e['title']!r} is a trailer"
        number, season = _numbering(e)
        if number in (0, 1) and season in (None, 0, 1):
            return f"{e['day']} {e['title']!r} is episode {number}"
        if _LAUNCH_TITLE.search(e["title"] or ""):
            return f"{e['day']} {e['title']!r} reads as a launch"
    return None


def _truncation(earliest, dates: list[str], live: list[tuple[str, int | None]], first: str) -> str | None:
    numbers = [_numbering(e) for e in earliest]
    numbered = [n for n, _s in numbers if n is not None]
    seasons = [s for _n, s in numbers if s is not None]
    if numbered and min(numbered) > 1:
        return f"its earliest episodes are numbered from {min(numbered)} ({earliest[0]['title']!r})"
    if seasons and min(seasons) > 1:
        return f"its earliest episodes are season {min(seasons)} ({earliest[0]['title']!r})"
    for oldest, count in live:
        size = _page_size(count)
        if size and oldest <= first:
            return f"the feed listing it holds {count} items, a page size ({size})"
    if live and dates and all(oldest > dates[0] for oldest, _c in live):
        dropped = sum(d < min(o for o, _c in live) for d in dates)
        return f"the live feed no longer lists {dropped} older episodes we hold, so it rolls"
    if len(dates) >= MIN_COMPLETE_ITEMS and _days(dates[0], dates[ISOLATED_RANK]) > ISOLATED_DAYS:
        return (f"its oldest items are isolated ({dates[ISOLATED_RANK]} is only the "
                f"{ISOLATED_RANK + 1}th), as when a truncated feed re-surfaces a few old episodes")
    return None


def _complete_feed(live: list[tuple[str, int | None]], first: str) -> str | None:
    for oldest, count in live:
        if oldest <= first and (count or 0) >= MIN_COMPLETE_ITEMS:
            return f"the live feed still lists every episode we hold ({count} items, back to {oldest})"
    return None


def _numbering(episode) -> tuple[int | None, int | None]:
    """(episode number, season) from the feed's tags, else from the title."""
    meta = json.loads(episode["metadata"] or "{}")
    number, season = _int(meta.get("episode_number")), _int(meta.get("season"))
    if number is None:
        m = _NUMBER_TITLE.search(episode["title"] or "")
        number = int(m.group(1) or m.group(2)) if m else None
    if season is None:
        m = _SEASON_TITLE.search(episode["title"] or "")
        season = int(m.group(1)) if m else None
    return number, season


def _page_size(count: int | None) -> int | None:
    """The page size ``count`` sits at or just under (items without audio are not counted)."""
    for size in sorted(PAGE_SIZES):
        if count is not None and size * (1 - PAGE_SIZE_SLACK) <= count <= size:
            return size
    return None


def _int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _next_day(day: str) -> str:
    return (date.fromisoformat(day[:10]) + timedelta(days=1)).isoformat()


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b[:10]) - date.fromisoformat(a[:10])).days
