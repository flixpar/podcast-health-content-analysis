"""discover-archived: recover episodes that have fallen off a study's live feeds.

A live feed lists only its newest N items, so a show's early years are often
missing from what `discover` recorded. The Wayback Machine kept copies of many
feeds as they looked years ago. For each study member with gap windows (see
``studies/gaps.py``), oldest gaps first:

1. List the captures of every feed URL we know for the podcast
   (``podcasts.rss_url`` and ``podcast_feeds``; old hosts are the valuable
   ones). CDX is queried strictly one request at a time, paced, with retries.
2. Pick captures that reach into the gap windows (``next_capture``), fetch them
   a few at a time, and parse them as feeds. Repeat until the windows are
   covered, the archive has nothing more to offer, or the per-podcast cap.
3. Record every parsed episode (catalog metadata, whether or not it falls in
   a window) with a ``wayback_feed`` provenance row, and a ``wayback_probes``
   row per (podcast, URL) so a re-run resumes. One commit per podcast.

Archived enclosure URLs are often dead; ``download --wayback-fallback`` then
tries Wayback's copy of the audio.

Run ``study refresh`` afterwards to add the recovered episodes to the study.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from podcast_pipeline import db
from podcast_pipeline.archive.wayback import (Capture, CdxError, SnapshotError, WaybackClient,
                                              archived_original, url_identity)
from podcast_pipeline.config import Config
from podcast_pipeline.models import FeedEpisode
from podcast_pipeline.rss import FeedError, parse_feed
from podcast_pipeline.studies.gaps import PodcastGaps, study_gaps
from podcast_pipeline.studies.scope import require_refreshed

logger = logging.getLogger(__name__)

#: Publication dates before this are feed junk (epoch defaults), not history.
EARLIEST_PLAUSIBLE_DATE = "1995"

#: The budget clock; tests replace it.
monotonic = time.monotonic


class CdxUnavailableError(RuntimeError):
    """CDX failed for several podcasts in a row; the service is down, not the feeds."""


# --- capture selection ---------------------------------------------------------

@dataclass(eq=False)
class WindowTarget:
    """How far back a gap window has been reached.

    Everything published in ``[frontier, end)`` is covered by fetched captures
    (as far as the archive allows); the window is done when ``frontier`` has
    reached ``start``. ``before`` maps each feed (by ``url_identity``) to its
    earliest successfully fetched capture that counted for this window: a later
    capture *of the same feed* lists the same or newer items, so it can never
    reach further back. Another feed URL (the show's new host) still might.
    """

    label: str
    start: str          # inclusive ISO date
    end: str            # exclusive ISO date
    frontier: str = ""
    before: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.frontier = self.frontier or self.end

    @property
    def covered(self) -> bool:
        return self.frontier <= self.start

    def apply(self, capture: Capture, oldest: str, picked_here: bool) -> None:
        """Account for a fetched capture whose oldest dated item is ``oldest``.

        A capture taken at or after the frontier lists every item from
        ``oldest`` up to its own date, contiguously, so it pushes the frontier
        back. One taken below the frontier (only ever picked as a last resort)
        leaves the span between it and the frontier unrecoverable; it counts
        only for the window that picked it.
        """
        if picked_here or capture.day >= self.frontier:
            self.frontier = min(self.frontier, oldest)
            feed = url_identity(capture.original)
            self.before[feed] = min(self.before.get(feed, capture.timestamp), capture.timestamp)

    def may_reach_back(self, capture: Capture) -> bool:
        bound = self.before.get(url_identity(capture.original))
        return bound is None or capture.timestamp < bound


def capture_key(capture: Capture) -> tuple[str, str]:
    return capture.timestamp, capture.original


def next_capture(target: WindowTarget, captures: list[Capture], tried: set[tuple[str, str]],
                 fetched_digests: set[str]) -> Capture | None:
    """The next capture to fetch for ``target``, or None when nothing can help.

    A feed capture lists the newest N items as of the capture time, so the
    capture that reaches furthest back into a window is the *earliest one at or
    after the window's end*. That is the first pick. If its oldest item still
    falls inside the window (a short feed), the frontier moves back to that item
    and the rule repeats: the earliest capture at or after the new frontier,
    skipping captures of the same feed taken after one already used -- so
    usually a capture *inside* the window, or one of another feed URL. When no
    capture remains at or after the frontier, the latest one inside the window
    still beats nothing.

    ``captures`` is sorted oldest first. Captures already tried, and captures
    byte-identical (same digest) to one already fetched, are skipped.
    """
    if target.covered:
        return None
    usable = [c for c in captures
              if capture_key(c) not in tried and c.digest not in fetched_digests]
    for c in usable:
        if c.day >= target.frontier and target.may_reach_back(c):
            return c
    inside = [c for c in usable if target.start <= c.day < target.frontier]
    return inside[-1] if inside else None


# --- one podcast -----------------------------------------------------------------

@dataclass
class Fetched:
    """A worker's result for one capture."""

    capture: Capture
    feed_url: str                      # the candidate URL whose listing held it
    snapshot_url: str | None = None    # what Wayback actually served
    episodes: list[FeedEpisode] = field(default_factory=list)
    error: str | None = None

    @property
    def oldest(self) -> str | None:
        dates = [e.published_date[:10] for e in self.episodes
                 if e.published_date and e.published_date >= EARLIEST_PLAUSIBLE_DATE]
        return min(dates) if dates else None


@dataclass
class UrlProbe:
    url: str
    captures: list[Capture] = field(default_factory=list)
    cdx_error: str | None = None
    fetched: list[Fetched] = field(default_factory=list)


def fetch_capture(client: WaybackClient, capture: Capture, feed_url: str) -> Fetched:
    """Worker: fetch and parse one capture. Per-capture failures are returned, not raised."""
    try:
        snapshot = client.fetch_snapshot(capture)
        episodes = parse_feed(snapshot.body, source=snapshot.served_url)
    except (SnapshotError, FeedError) as e:
        return Fetched(capture, feed_url, error=str(e)[:500])
    return Fetched(capture, feed_url, snapshot.served_url, episodes)


def probe_podcast(client: WaybackClient, pool: ThreadPoolExecutor, gaps: PodcastGaps,
                  urls: list[str], max_captures: int, refresh: bool) -> tuple[list[UrlProbe], list[WindowTarget]]:
    """List, choose and fetch captures for one podcast. No database access."""
    probes = [UrlProbe(url) for url in urls]
    for probe in probes:
        try:
            probe.captures = client.list_captures(probe.url, refresh=refresh)
        except CdxError as e:
            probe.cdx_error = str(e)
            logger.warning(f"{gaps.title}: {e}")

    # One pool of captures across all URLs; a feed that moved hosts is archived
    # under both, each covering its own era.
    owner: dict[tuple[str, str], UrlProbe] = {}
    for probe in probes:
        for c in probe.captures:
            owner.setdefault(capture_key(c), probe)
    captures = sorted((c for p in probes for c in p.captures if owner[capture_key(c)] is p),
                      key=lambda c: c.timestamp)

    targets = [WindowTarget(label, start, end) for label, start, end in sorted(gaps.windows, key=lambda w: w[1])]
    tried: set[tuple[str, str]] = set()
    fetched_digests: set[str] = set()
    while len(tried) < max_captures:
        picks: dict[tuple[str, str], tuple[Capture, list[WindowTarget]]] = {}
        for target in targets:
            c = next_capture(target, captures, tried, fetched_digests)
            if c is None:
                continue
            if capture_key(c) not in picks and len(tried) + len(picks) >= max_captures:
                break
            picks.setdefault(capture_key(c), (c, []))[1].append(target)
        if not picks:
            break
        jobs = list(picks.values())
        results = list(pool.map(lambda job: fetch_capture(client, job[0], owner[capture_key(job[0])].url),
                                jobs))
        for (capture, pickers), result in zip(jobs, results):
            tried.add(capture_key(capture))
            owner[capture_key(capture)].fetched.append(result)
            if result.error is None:
                fetched_digests.add(capture.digest)
            oldest = result.oldest
            if oldest is None:
                continue          # failed, or no dated items: the next round tries another capture
            for target in targets:
                if not target.covered:
                    target.apply(capture, oldest, picked_here=any(t is target for t in pickers))
    return probes, targets


# --- database (main thread) ---------------------------------------------------------

def candidate_urls(conn: sqlite3.Connection, podcast_id: int) -> list[str]:
    """Every feed URL known for the podcast, current first, one per CDX identity.

    CDX canonicalizes URLs (scheme and a leading ``www.`` are ignored), so
    variants differing only in those would return the same listing twice.
    """
    rows = conn.execute("""
        SELECT rss_url AS url, 0 AS ord, '' AS seen FROM podcasts WHERE id = ?
        UNION ALL
        SELECT url, 1, COALESCE(first_seen_at, '') FROM podcast_feeds WHERE podcast_id = ?
        ORDER BY ord, seen, url
    """, (podcast_id, podcast_id)).fetchall()
    urls, identities = [], set()
    for row in rows:
        url = (row["url"] or "").strip()
        if not url:
            continue
        identity = url_identity(url)
        if identity not in identities:
            identities.add(identity)
            urls.append(url)
    return urls


def previous_windows(conn: sqlite3.Connection, podcast_id: int, url: str) -> set[tuple[str, str]] | None:
    """Windows an earlier ok/no_captures probe of this URL already targeted; None to probe."""
    row = conn.execute("SELECT status, windows_targeted FROM wayback_probes WHERE podcast_id = ? AND url = ?",
                       (podcast_id, url)).fetchone()
    if row is None or row["status"] not in ("ok", "no_captures"):
        return None
    return {tuple(w) for w in json.loads(row["windows_targeted"] or "[]")}


def record_episodes(conn: sqlite3.Connection, podcast_id: int, fetched: Fetched,
                    seen: set[str], new: set[str], foreign: set[str]) -> None:
    """Insert one capture's episodes under ``podcast_id`` with provenance.

    Called for one feed URL's captures in time order, with ``seen`` holding the
    GUIDs its earlier captures listed. Provenance is one ``wayback_feed`` row per
    (episode, feed): the earliest capture that listed it, unless an earlier run
    already recorded one for this feed.

    GUIDs are unique across the whole catalog: a GUID already held by another
    podcast is left alone and counted in ``foreign``.
    """
    feed = url_identity(fetched.capture.original)
    for episode in fetched.episodes:
        if episode.guid in seen:
            continue
        row = conn.execute("SELECT podcast_id FROM episodes WHERE episode_guid = ?",
                           (episode.guid,)).fetchone()
        if row is not None and row["podcast_id"] != podcast_id:
            foreign.add(episode.guid)
            continue
        seen.add(episode.guid)
        if row is None and db.insert_episode(conn, podcast_id, episode):
            new.add(episode.guid)
        elif has_wayback_feed_source(conn, podcast_id, episode.guid, feed):
            continue
        db.record_episode_source(conn, podcast_id, episode.guid, "wayback_feed", fetched.snapshot_url)


def has_wayback_feed_source(conn: sqlite3.Connection, podcast_id: int, guid: str, feed: str) -> bool:
    """Whether the episode already has a ``wayback_feed`` row from a capture of ``feed``."""
    refs = conn.execute("""
        SELECT es.ref FROM episode_sources es JOIN episodes e ON e.id = es.episode_id
        WHERE e.episode_guid = ? AND e.podcast_id = ? AND es.source = 'wayback_feed'
    """, (guid, podcast_id)).fetchall()
    return any(url_identity(original) == feed
               for original in (archived_original(r["ref"]) for r in refs) if original)


def write_probe(conn: sqlite3.Connection, podcast_id: int, url: str, status: str,
                captures_listed: int, captures_fetched: int, episodes_found: int, episodes_new: int,
                windows: list[tuple[str, str]], detail: dict) -> None:
    conn.execute("""
        INSERT INTO wayback_probes (podcast_id, url, probed_at, status, captures_listed,
                                    captures_fetched, episodes_found, episodes_new,
                                    windows_targeted, detail)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (podcast_id, url) DO UPDATE SET
            probed_at = CURRENT_TIMESTAMP, status = excluded.status,
            captures_listed = excluded.captures_listed, captures_fetched = excluded.captures_fetched,
            episodes_found = excluded.episodes_found, episodes_new = excluded.episodes_new,
            windows_targeted = excluded.windows_targeted, detail = excluded.detail
    """, (podcast_id, url, status, captures_listed, captures_fetched, episodes_found, episodes_new,
          json.dumps(sorted([list(w) for w in windows])), json.dumps(detail)))


def windows_with_episodes(conn: sqlite3.Connection, podcast_id: int,
                          windows: list[tuple[str, str, str]]) -> int:
    return sum(
        conn.execute("SELECT EXISTS (SELECT 1 FROM episodes WHERE podcast_id = ? "
                     "AND published_date >= ? AND published_date < ?)",
                     (podcast_id, start, end)).fetchone()[0]
        for _label, start, end in windows)


def save_podcast(conn: sqlite3.Connection, gaps: PodcastGaps, probes: list[UrlProbe],
                 targets: list[WindowTarget], previous: dict[str, set], stats: dict) -> None:
    """Write one podcast's episodes and probe rows, then commit."""
    windows = [(start, end) for _label, start, end in gaps.windows]
    unreached = [t.label for t in targets if not t.covered]
    foreign: set[str] = set()
    for probe in probes:
        seen: set[str] = set()
        new: set[str] = set()
        ok = [f for f in probe.fetched if f.error is None]
        for fetched in sorted(ok, key=lambda f: f.capture.timestamp):
            record_episodes(conn, gaps.podcast_id, fetched, seen, new, foreign)
        failures = [f for f in probe.fetched if f.error is not None]
        if probe.cdx_error:
            status = "error"
        elif not probe.captures:
            status = "no_captures"
        elif probe.fetched and not ok:
            status = "error"          # every fetch failed: try again next run
        else:
            status = "ok"
        targeted = windows if status == "error" else sorted(set(windows) | previous.get(probe.url, set()))
        detail = {
            "cdx_error": probe.cdx_error,
            "captures_used": [{"timestamp": f.capture.timestamp, "served": f.snapshot_url,
                               "episodes": len(f.episodes), "oldest": f.oldest} for f in ok],
            "capture_failures": [{"timestamp": f.capture.timestamp, "error": f.error} for f in failures],
            "windows_unreached": unreached,
        }
        write_probe(conn, gaps.podcast_id, probe.url, status, len(probe.captures), len(ok),
                    len(seen), len(new), targeted, detail)
        stats["probes"][status] += 1
        stats["captures_listed"] += len(probe.captures)
        stats["captures_fetched"] += len(ok)
        stats["capture_failures"] += len(failures)
        stats["episodes_found"] += len(seen)
        stats["episodes_new"] += len(new)
    stats["episodes_foreign_guid"] += len(foreign)
    conn.commit()


# --- the stage ------------------------------------------------------------------

def run(config: Config, conn: sqlite3.Connection, study: str, budget_minutes: float | None = None,
        limit: int | None = None, retry: bool = False) -> dict:
    require_refreshed(conn, study)
    cfg = config.wayback
    budget_minutes = cfg.budget_minutes if budget_minutes is None else budget_minutes
    started = monotonic()
    all_gaps = study_gaps(conn, study)
    logger.info(f"discover-archived {study}: {len(all_gaps)} podcasts with gap windows, "
                f"budget {budget_minutes:g} min")

    stats = {
        "study": study, "podcasts_with_gaps": len(all_gaps), "podcasts_probed": 0,
        "podcasts_already_probed": 0, "podcasts_without_feed_urls": 0, "podcasts_not_reached": 0,
        "stopped": None, "probes": {"ok": 0, "no_captures": 0, "error": 0},
        "captures_listed": 0, "captures_fetched": 0, "capture_failures": 0,
        "episodes_found": 0, "episodes_new": 0, "episodes_foreign_guid": 0,
        "gap_windows_targeted": 0, "gap_windows_with_episodes_before": 0,
        "gap_windows_with_episodes_after": 0,
    }
    client = WaybackClient(cfg, config.wayback_cache_dir)
    probed: list[PodcastGaps] = []
    cdx_down_streak = 0
    with ThreadPoolExecutor(max_workers=max(cfg.fetch_workers, 1)) as pool:
        for i, gaps in enumerate(all_gaps):
            if limit is not None and stats["podcasts_probed"] >= limit:
                stats["stopped"] = "limit"
            elif monotonic() - started >= budget_minutes * 60:
                stats["stopped"] = "budget"
            if stats["stopped"]:
                stats["podcasts_not_reached"] = len(all_gaps) - i
                break

            urls = candidate_urls(conn, gaps.podcast_id)
            if not urls:
                stats["podcasts_without_feed_urls"] += 1
                continue
            windows = {(start, end) for _label, start, end in gaps.windows}
            previous = {url: previous_windows(conn, gaps.podcast_id, url) for url in urls}
            todo = [url for url in urls
                    if retry or previous[url] is None or not windows <= previous[url]]
            if not todo:
                stats["podcasts_already_probed"] += 1
                continue

            logger.info(f"[{i + 1}/{len(all_gaps)}] {gaps.title}: {len(gaps.windows)} gap windows "
                        f"({gaps.span[0]}..{gaps.span[1]}), {len(todo)} feed URLs")
            before = windows_with_episodes(conn, gaps.podcast_id, gaps.windows)
            probes, targets = probe_podcast(client, pool, gaps, todo,
                                            cfg.max_captures_per_podcast, refresh=retry)
            save_podcast(conn, gaps, probes, targets,
                         {u: w for u, w in previous.items() if w is not None}, stats)
            stats["podcasts_probed"] += 1
            stats["gap_windows_targeted"] += len(gaps.windows)
            stats["gap_windows_with_episodes_before"] += before
            probed.append(gaps)

            if all(p.cdx_error for p in probes):
                cdx_down_streak += 1
                if cdx_down_streak >= cfg.cdx_failure_limit:
                    raise CdxUnavailableError(
                        f"CDX failed for {cdx_down_streak} podcasts in a row (last: {probes[-1].cdx_error}). "
                        f"The Wayback CDX service looks down; their probes are recorded as 'error' "
                        f"and will be retried. Re-run later.")
            else:
                cdx_down_streak = 0

    # The gap check again, against the episodes table: study_episodes only
    # picks up the recovered episodes at the next `study refresh`.
    stats["gap_windows_with_episodes_after"] = sum(
        windows_with_episodes(conn, g.podcast_id, g.windows) for g in probed)
    stats["cdx_requests"] = client.cdx_requests
    stats["budget_minutes"] = budget_minutes
    stats["minutes_used"] = round((monotonic() - started) / 60, 2)
    logger.info(f"discover-archived complete: {stats}")
    return stats
