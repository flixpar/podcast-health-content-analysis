"""Materialize a study's definition into ``study_members`` / ``study_windows`` /
``study_episodes``.

Refreshing is cheap (seconds) and safe to repeat. Run it after anything that
changes what the study can see: new chart data, ``resolve`` (members gain a
podcast), ``discover`` / ``discover-archived`` (podcasts gain episodes).

Membership is fully derived, so the member and window tables are rewritten on
every refresh. Episode rows keep the revision that first added them, and the
study's ``revision`` is bumped (with a ``study_revisions`` row) whenever the
selected episode set, an episode's member or window, or the definition changes, so an exported manifest can be
tied to exactly the membership it came from.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from podcast_pipeline import db
from podcast_pipeline.studies.base import Member, Study
from podcast_pipeline.studies.quality import exclusion_reason

logger = logging.getLogger(__name__)

#: Earlier publication dates are parse failures (an unset pubDate becomes the
#: 1970 epoch), not real episodes; a windowed study cannot place them.
MIN_PLAUSIBLE_DATE = "1995"


@dataclass
class Selected:
    episode_id: int
    entity: str
    window_label: str | None
    priority: int


def refresh(conn: sqlite3.Connection, study: Study) -> dict:
    members = study.select(conn)
    _check_members(study, members)
    definition_hash = study.definition_hash()

    resolved = {m.entity: db.podcast_for_entity(conn, m.entity) for m in members}
    selected, excluded = _select_episodes(conn, study, members, resolved)

    row = conn.execute("SELECT revision, definition_hash FROM studies WHERE name = ?",
                       (study.name,)).fetchone()
    old_revision = row["revision"] if row else 0
    previous, placed = {}, {}
    for r in conn.execute("SELECT episode_id, added_revision, entity, window_label "
                          "FROM study_episodes WHERE study = ?", (study.name,)):
        previous[r["episode_id"]] = r["added_revision"]
        placed[r["episode_id"]] = (r["entity"], r["window_label"])
    added = [s for s in selected if s.episode_id not in previous]
    removed = set(previous) - {s.episode_id for s in selected}
    moved = sum(1 for s in selected if s.episode_id in placed
                and placed[s.episode_id] != (s.entity, s.window_label))
    changed = (bool(added or removed or moved) or row is None
               or row["definition_hash"] != definition_hash)
    revision = old_revision + 1 if changed else old_revision

    by_podcast: dict[int, list[str]] = defaultdict(list)
    for entity, pid in resolved.items():
        if pid is not None:
            by_podcast[pid].append(entity)
    merged = {e: ents for ents in by_podcast.values() if len(ents) > 1 for e in ents}

    summary = {
        "revision": revision,
        "definition_hash": definition_hash,
        "members": len(members),
        "members_resolved": sum(pid is not None for pid in resolved.values()),
        "members_merged": len(merged),
        "windows": sum(len(m.windows or []) for m in members),
        "episodes": len(selected),
        "episodes_added": len(added),
        "episodes_removed": len(removed),
        "episodes_reassigned": moved,
        "excluded": excluded,
    }

    with conn:
        conn.execute("DELETE FROM study_members WHERE study = ?", (study.name,))
        conn.execute("DELETE FROM study_windows WHERE study = ?", (study.name,))
        conn.executemany("""
            INSERT INTO study_members (study, entity, podcast_id, name, scope, attrs)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(study.name, m.entity, resolved[m.entity], m.name, m.scope,
               json.dumps({**m.attrs, **({"merged_with": merged[m.entity]} if m.entity in merged else {})}))
              for m in members])
        conn.executemany("""
            INSERT INTO study_windows (study, entity, label, start_date, end_date, attrs)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(study.name, m.entity, w.label, w.start, w.end, json.dumps(w.attrs))
              for m in members for w in m.windows or []])
        conn.execute("DELETE FROM study_episodes WHERE study = ?", (study.name,))
        conn.executemany("""
            INSERT INTO study_episodes (study, episode_id, entity, window_label, priority, added_revision)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(study.name, s.episode_id, s.entity, s.window_label, s.priority,
               previous.get(s.episode_id, revision)) for s in selected])
        conn.execute("""
            INSERT INTO studies (name, description, definition, definition_hash, revision,
                                 refreshed_at, summary)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT (name) DO UPDATE SET
                description = excluded.description, definition = excluded.definition,
                definition_hash = excluded.definition_hash, revision = excluded.revision,
                refreshed_at = excluded.refreshed_at, summary = excluded.summary
        """, (study.name, study.description, json.dumps(study.definition()), definition_hash,
              revision, json.dumps(summary)))
        if changed:
            conn.execute("""
                INSERT INTO study_revisions (study, revision, definition_hash, summary)
                VALUES (?, ?, ?, ?)
            """, (study.name, revision, definition_hash, json.dumps(summary)))
    logger.info(f"Study {study.name}: {summary}")
    return summary


def _check_members(study: Study, members: list[Member]) -> None:
    seen = set()
    for m in members:
        if m.entity in seen:
            raise ValueError(f"study {study.name} selected entity {m.entity!r} twice")
        seen.add(m.entity)
        if m.entity.partition(":")[0] not in ("podcast", "apple", "title"):
            raise ValueError(f"study {study.name}: unknown entity kind {m.entity!r}")
        labels = [w.label for w in m.windows or []]
        if len(labels) != len(set(labels)):
            raise ValueError(f"study {study.name}: {m.entity} has duplicate window labels")
        for w in m.windows or []:
            if not w.start < w.end:
                raise ValueError(f"study {study.name}: empty window {w} for {m.entity}")


def _select_episodes(conn: sqlite3.Connection, study: Study, members: list[Member],
                     resolved: dict[str, int | None]) -> tuple[list[Selected], dict]:
    """The episodes each resolved member contributes, and counts of what was left out.

    Two entities resolving to one podcast (a show that charted under an id
    and, elsewhere, under a bare title) share the podcast's episodes: each
    episode is assigned once, to the first entity whose scope takes it.
    """
    excluded = {"undated": 0, "duplicate": 0, "over_window_cap": 0, "trailer_or_promo": 0}
    per_podcast: dict[int, list[Member]] = defaultdict(list)
    for m in members:
        if resolved[m.entity] is not None:
            per_podcast[resolved[m.entity]].append(m)

    selected: list[Selected] = []
    taken: set[int] = set()
    for podcast_id, podcast_members in per_podcast.items():
        episodes = _podcast_episodes(conn, podcast_id, study.dedupe, excluded)
        if study.exclude_trailers:
            title = conn.execute("SELECT title FROM podcasts WHERE id = ?", (podcast_id,)).fetchone()[0]
            kept = [ep for ep in episodes if exclusion_reason(ep, title) is None]
            excluded["trailer_or_promo"] += len(episodes) - len(kept)
            episodes = kept
        for m in podcast_members:
            if m.windows is None:
                for ep in episodes:
                    if ep["id"] not in taken:
                        taken.add(ep["id"])
                        selected.append(Selected(ep["id"], m.entity, None, 0))
                continue
            dated = [ep for ep in episodes
                     if ep["published_date"] and ep["published_date"] >= MIN_PLAUSIBLE_DATE]
            excluded["undated"] += len(episodes) - len(dated)
            for w in m.windows:
                inside = [ep for ep in dated
                          if w.start <= ep["published_date"][:10] < w.end and ep["id"] not in taken]
                chosen = _cap(inside, study.max_per_window)
                excluded["over_window_cap"] += len(inside) - len(chosen)
                for position, ep in enumerate(sorted(chosen, key=lambda e: e["published_date"])):
                    taken.add(ep["id"])
                    selected.append(Selected(ep["id"], m.entity, w.label, position))
    return selected, excluded


def _podcast_episodes(conn: sqlite3.Connection, podcast_id: int, dedupe: bool,
                      excluded: dict) -> list[sqlite3.Row]:
    rows = conn.execute("""
        SELECT id, published_date, title, duration_seconds,
               json_extract(metadata, '$.episode_type') AS episode_type,
               (transcript_file_path IS NOT NULL AND transcript_file_path != '') AS done,
               (audio_file_path IS NOT NULL AND audio_file_path != '') AS has_audio
        FROM episodes WHERE podcast_id = ?
        ORDER BY id
    """, (podcast_id,)).fetchall()
    if not dedupe:
        return rows
    kept = [r for r in rows if r["published_date"] is None]
    by_title: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        if r["published_date"] is not None:
            # Case, punctuation and spacing are ignored: re-issues retouch titles.
            by_title[re.sub(r"[^a-z0-9]+", "", (r["title"] or "").lower())].append(r)
    for group in by_title.values():
        group.sort(key=lambda r: r["published_date"])
        cluster = [group[0]]
        for r in group[1:]:
            if _same_airing(cluster[-1], r):
                cluster.append(r)
                continue
            kept.append(_best_copy(cluster))
            cluster = [r]
        kept.append(_best_copy(cluster))
    excluded["duplicate"] += len(rows) - len(kept)
    return sorted(kept, key=lambda r: r["id"])


def _same_airing(a: sqlite3.Row, b: sqlite3.Row) -> bool:
    """Same title, and either the same UTC day or adjacent days with matching
    durations. A re-issue under a new GUID keeps its day, except across UTC
    midnight (a feed migration can list one airing at 23:00 and 01:00); a show
    that reuses one title for every daily episode is kept apart by duration."""
    day_a, day_b = date.fromisoformat(a["published_date"][:10]), date.fromisoformat(b["published_date"][:10])
    if day_a == day_b:
        return True
    if (day_b - day_a).days != 1:
        return False
    da, db_ = a["duration_seconds"], b["duration_seconds"]
    return bool(da and db_ and abs(da - db_) <= 0.05 * max(da, db_))


def _best_copy(copies: list[sqlite3.Row]) -> sqlite3.Row:
    """The copy with the most work already done, then the oldest row."""
    return min(copies, key=lambda r: (-r["done"], -r["has_audio"], r["id"]))


def _cap(episodes: list[sqlite3.Row], cap: int | None) -> list[sqlite3.Row]:
    """At most ``cap`` episodes, transcribed ones first, then evenly spaced in time."""
    if cap is None or len(episodes) <= cap:
        return episodes
    done = [e for e in episodes if e["done"]]
    if len(done) >= cap:
        return _spread(done, cap)
    rest = [e for e in episodes if not e["done"]]
    return done + _spread(rest, cap - len(done))


def _spread(episodes: list[sqlite3.Row], n: int) -> list[sqlite3.Row]:
    ordered = sorted(episodes, key=lambda e: e["published_date"])
    if n <= 0:
        return []
    if n >= len(ordered):
        return ordered
    step = len(ordered) / n
    return [ordered[int(i * step + step / 2)] for i in range(n)]
