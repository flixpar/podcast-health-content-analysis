"""Episode-quality rules for studies: what to leave out, and what re-airs old content.

Two questions, answered separately because a study treats them differently:

* :func:`exclusion_reason` -- is this item an episode at all? Trailers, another
  show's promo dropped into the feed ("Introducing ...", "What to listen to
  next ...") and items under :data:`MIN_EPISODE_SECONDS` are not content a
  study of what shows said should count. Pure; looks at one row.
* :func:`rerun_flags` -- does an in-scope episode re-air earlier content? Reruns
  stay in a study (they are what aired that month) but are flagged so an
  analysis of *new* content can drop them. Read-only over the catalog.

The rules come from the 2026-10-03 audit of ``apple-top24-monthly``
(``data/studies/apple-top24-monthly/gapfill-audit.md``), where each was checked
against the real catalog for false positives: a shared title alone is not a
rerun (recurring guests, "Mailbag Sunday", "MFM Minisode 22" vs "221"), so
every same-content rule also needs a matching duration or an explicit rerun
marker, and the titles' episode numbers must agree.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from difflib import SequenceMatcher
from typing import Mapping

#: Items shorter than this (declared duration) are announcements, not episodes.
MIN_EPISODE_SECONDS = 75
#: Cross-feed and same-feed content matching only considers episodes longer than
#: this: short items (promos, updates) share durations by coincidence.
RERUN_MIN_SECONDS = 600
#: A leading episode number this far below the feed's running maximum is a re-post.
OLD_NUMBER_GAP = 15
#: ... once the feed has numbered at least this many episodes.
OLD_NUMBER_MIN_HIGH = 50
#: Same title, duration within 1% (not exact): a re-air only this many days apart.
SAME_TITLE_MIN_DAYS = 90
#: An older catalog copy must predate the episode by more than this to count as the original.
RERUN_MIN_DAYS = 7

#: Another show's trailer or episode carried in this feed.
FEED_DROP = re.compile(
    r"^\W*(bonus:?\s*|special:?\s*)?(introducing|presenting|feed ?drop|what to listen to next|"
    r"sneak peek|special preview|a preview of|listen now|new show|from our friends)\b\W*", re.I)
#: Words publishers use to mark a re-aired episode.
RERUN_MARKER = re.compile(
    r"\b(re-?broadcast|encore( presentation)?|best of|replay|rerun|re-?run|repeat|re-?release[d]?|"
    r"re-?air(ed)?|classic|from the archives?|vault|throwback|revisited|rewind|fbf|flashback|selects|"
    r"playlist)\b|\(r\)|\[r\]", re.I)
#: Episode numbers, but not "Part N": multi-part stories are distinct episodes.
EPISODE_NUMBER = re.compile(r"\b(ep(isode)?|no)\.?\s*#?\d+\b|^\s*#?\d+\s*[:.\-|]|\|\s*#?\d+\s*$|#\d+|"
                            r"\bs\d+\s*e\d+\b|\bseason \d+,? episode \d+\b", re.I)
LEADING_NUMBER = re.compile(r"^\s*#?(\d{1,4})\s*[:.|\-]")
#: GUID suffix ``tools/tal_archive.py`` gives a This American Life rerun airing.
RERUN_GUID = "#rerun-"


def norm_title(title: str | None) -> str:
    """Lowercase alphanumerics with rerun markers and episode numbers removed."""
    t = RERUN_MARKER.sub(" ", (title or "").lower())
    t = EPISODE_NUMBER.sub(" ", t)
    return re.sub(r"[^a-z0-9]+", "", t)


def title_numbers(title: str | None) -> set[str]:
    """Digit runs in a title, years aside: differing numbers mean different episodes."""
    return {n.lstrip("0") for n in re.findall(r"\d+", title or "") if not re.fullmatch(r"(19|20)\d\d", n)}


def _episode_type(row: Mapping) -> str | None:
    keys = row.keys()
    if "episode_type" in keys:
        return row["episode_type"]
    meta = row["metadata"] if "metadata" in keys else None
    return json.loads(meta).get("episode_type") if meta else None


def exclusion_reason(episode: Mapping, podcast_title: str | None) -> str | None:
    """Why ``episode`` is not an episode a study should count, or None.

    ``episode`` needs ``title``, ``duration_seconds`` and either ``episode_type``
    or the ``metadata`` JSON. Bonus episodes are kept (mostly substantive). A
    promo that is the show introducing itself ("Introducing: Skimm This" in
    Skimm This) is kept; an unknown duration never excludes.
    """
    if _episode_type(episode) == "trailer":
        return "trailer"
    title = episode["title"] or ""
    m = FEED_DROP.search(title)
    if m:
        own, rest = norm_title(podcast_title), norm_title(title[m.end():])
        if not (own and rest and (own[:12] in rest or rest[:12] in own)):
            return f"promo: {re.sub(r'[^a-z ]+', '', m.group(0).lower()).strip()}"
    duration = episode["duration_seconds"]
    if duration is not None and 0 < duration < MIN_EPISODE_SECONDS:
        return f"short: {duration} s"
    return None


def _same_length(a: int | None, b: int | None, rel: float, floor: int) -> bool:
    return bool(a and b and abs(a - b) <= max(floor, rel * max(a, b)))


def _copy_reason(first: dict, later: dict) -> str | None:
    """Why ``later`` (same normalized title as ``first``) re-airs it, or None."""
    if RERUN_MARKER.search(later["title"] or "") and not RERUN_MARKER.search(first["title"] or ""):
        return "rerun marker"
    if title_numbers(first["title"]) != title_numbers(later["title"]):
        return None
    a, b = first["duration_seconds"], later["duration_seconds"]
    apart = (date.fromisoformat(later["published_date"][:10])
             - date.fromisoformat(first["published_date"][:10])).days
    # a recurring segment ("Mailbag Sunday") repeats its title at a similar
    # length every week; a re-air of the same file is exact, or months later
    if _same_length(a, b, 0, 2) or (_same_length(a, b, 0.01, 5) and apart > SAME_TITLE_MIN_DAYS):
        return "same duration"
    return None


def _same_recording(e: dict, r: dict) -> bool:
    """Is ``r`` (another podcast's episode, duration within 1 s) the recording ``e`` is?

    Nearly equal titles, or one containing the other. A short contained title
    ("Family Tree") also needs an exact duration or dates within a week.
    """
    a, b = e["norm"], r["norm"]
    if len(a) < 8 or len(b) < 8:
        return False
    if abs(len(a) - len(b)) <= 0.1 * max(len(a), len(b)) and SequenceMatcher(None, a, b).ratio() >= 0.9:
        return True
    if not (a in b or b in a):
        return False
    if min(len(a), len(b)) >= 12:
        return True
    days = abs((date.fromisoformat(e["published_date"][:10]) - date.fromisoformat(r["published_date"][:10])).days)
    return e["duration_seconds"] == r["duration_seconds"] or days <= RERUN_MIN_DAYS


def rerun_flags(conn: sqlite3.Connection, study: str) -> dict[int, str]:
    """``episode_id -> reason`` for the study's episodes that re-air earlier content.

    Reasons are ``"<kind>: <evidence>"`` with kind one of ``guid_rerun``,
    ``same_title_copy``, ``rerun_of_earlier``, ``old_number`` or
    ``repost_of_other_podcast``; the first rule that matches wins. The earliest
    copy is never flagged. Read-only.
    """
    eps = [dict(r) for r in conn.execute("""
        SELECT e.id, e.podcast_id, e.episode_guid AS guid, e.title, e.published_date, e.duration_seconds
        FROM study_episodes s JOIN episodes e ON e.id = s.episode_id
        WHERE s.study = ? AND e.published_date IS NOT NULL
        ORDER BY e.published_date, e.id
    """, (study,))]
    flags: dict[int, str] = {}
    by_podcast: dict[int, list[dict]] = defaultdict(list)
    for e in eps:
        e["norm"] = norm_title(e["title"])
        by_podcast[e["podcast_id"]].append(e)
        if RERUN_GUID in (e["guid"] or ""):
            flags[e["id"]] = f"guid_rerun: {e['guid'].rsplit('#', 1)[1]}"

    for podcast_id, podcast_eps in by_podcast.items():
        # an earlier in-scope episode with the same title
        first_by_norm: dict[str, dict] = {}
        for e in podcast_eps:
            first = first_by_norm.get(e["norm"]) if len(e["norm"]) >= 6 else None
            why = _copy_reason(first, e) if first else None
            if why:
                flags.setdefault(e["id"], f"same_title_copy: of {first['id']} "
                                           f"({first['published_date'][:10]}), {why}")
            else:
                first_by_norm.setdefault(e["norm"], e)

        # an older catalog episode (in scope or not) with the same content
        catalog = [dict(r) for r in conn.execute(
            "SELECT id, title, published_date, duration_seconds FROM episodes "
            "WHERE podcast_id = ? AND published_date IS NOT NULL ORDER BY published_date", (podcast_id,))]
        by_duration: dict[int, list[dict]] = defaultdict(list)
        for r in catalog:
            if r["duration_seconds"] and r["duration_seconds"] > RERUN_MIN_SECONDS:
                by_duration[r["duration_seconds"]].append(r)
        for e in podcast_eps:
            d = e["duration_seconds"] or 0
            if d <= RERUN_MIN_SECONDS or e["id"] in flags or len(e["norm"]) < 12:
                continue
            cutoff = (date.fromisoformat(e["published_date"][:10]) - timedelta(days=RERUN_MIN_DAYS)).isoformat()
            tol = max(5, int(0.01 * d))
            for r in (r for dd in range(-tol, tol + 1) for r in by_duration.get(d + dd, [])):
                if r["published_date"][:10] >= cutoff:
                    continue
                rn = r.setdefault("norm", norm_title(r["title"]))
                if (len(rn) >= 12 and (rn in e["norm"] or e["norm"] in rn)
                        and title_numbers(r["title"]) == title_numbers(e["title"])
                        and (rn != e["norm"] or abs(r["duration_seconds"] - d) <= 2
                             or (RERUN_MARKER.search(e["title"] or "")
                                 and not RERUN_MARKER.search(r["title"] or "")))):
                    flags[e["id"]] = f"rerun_of_earlier: {r['id']} ({r['published_date'][:10]})"
                    break

        # an old episode number re-posted ("542: ..." in a 2018 This American Life feed)
        running, high = 0, {}
        for r in catalog:
            m = LEADING_NUMBER.match(r["title"] or "")
            if m:
                running = max(running, int(m.group(1)))
            high[r["published_date"][:10]] = running
        for e in podcast_eps:
            m = LEADING_NUMBER.match(e["title"] or "")
            top = high.get(e["published_date"][:10], 0)
            if m and e["id"] not in flags and top >= OLD_NUMBER_MIN_HIGH \
                    and int(m.group(1)) < top - OLD_NUMBER_GAP:
                flags[e["id"]] = f"old_number: {m.group(1)} after the feed reached {top}"

    # the same recording published earlier by another podcast
    wanted = {e["duration_seconds"] + dd for e in eps
              if (e["duration_seconds"] or 0) > RERUN_MIN_SECONDS for dd in (-1, 0, 1)}
    others: dict[int, list[dict]] = defaultdict(list)
    for r in conn.execute("""
        SELECT id, podcast_id, title, published_date, duration_seconds FROM episodes
        WHERE duration_seconds > ? AND published_date IS NOT NULL
    """, (RERUN_MIN_SECONDS,)):
        if r[4] in wanted:
            others[r[4]].append({"id": r[0], "podcast_id": r[1], "title": r[2],
                                 "published_date": r[3], "duration_seconds": r[4]})
    for e in eps:
        d = e["duration_seconds"] or 0
        if d <= RERUN_MIN_SECONDS or e["id"] in flags or len(e["norm"]) < 8:
            continue
        for r in (r for dd in (-1, 0, 1) for r in others.get(d + dd, [])):
            if r["podcast_id"] == e["podcast_id"] or (r["published_date"], r["id"]) >= (e["published_date"], e["id"]):
                continue
            r.setdefault("norm", norm_title(r["title"]))
            if _same_recording(e, r):
                flags[e["id"]] = (f"repost_of_other_podcast: {r['id']} in podcast {r['podcast_id']} "
                                  f"({r['published_date'][:10]})")
                break
    return flags
