"""Where a study's episode windows are not reached by what we have.

A window is a gap when no episode of the member falls in it, or when it opens
before the earliest episode we know for that podcast (the live feed no longer
reaches back that far, so the window is probably incomplete even if a stray
episode landed in it). These are what `discover-archived` goes looking for in
archived copies of the feed.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass
class PodcastGaps:
    podcast_id: int
    title: str
    entity: str
    earliest_known: str | None                 # earliest published_date we hold, any source
    windows: list[tuple[str, str, str]] = field(default_factory=list)   # (label, start, end)
    empty: set[str] = field(default_factory=set)   # labels with no episode at all; the rest are partial

    @property
    def span(self) -> tuple[str, str]:
        return min(w[1] for w in self.windows), max(w[2] for w in self.windows)


def study_gaps(conn: sqlite3.Connection, study: str) -> list[PodcastGaps]:
    """Gap windows per resolved member of ``study``, oldest podcast-gap first."""
    rows = conn.execute("""
        WITH counts AS (
            SELECT entity, window_label, COUNT(*) AS n
            FROM study_episodes WHERE study = ? GROUP BY entity, window_label
        ),
        earliest AS (
            SELECT podcast_id, MIN(published_date) AS first_pub
            FROM episodes WHERE published_date >= '1995' GROUP BY podcast_id
        )
        SELECT m.podcast_id, p.title, m.entity, w.label, w.start_date, w.end_date,
               COALESCE(c.n, 0) AS n, ea.first_pub
        FROM study_windows w
        JOIN study_members m ON m.study = w.study AND m.entity = w.entity
        JOIN podcasts p ON p.id = m.podcast_id
        LEFT JOIN counts c ON c.entity = w.entity AND c.window_label = w.label
        LEFT JOIN earliest ea ON ea.podcast_id = m.podcast_id
        WHERE w.study = ? AND m.podcast_id IS NOT NULL
        ORDER BY m.podcast_id, w.start_date
    """, (study, study)).fetchall()
    by_podcast: dict[int, PodcastGaps] = {}
    for r in rows:
        first = r["first_pub"]
        if r["n"] > 0 and first is not None and first[:10] <= r["start_date"]:
            continue
        gaps = by_podcast.setdefault(r["podcast_id"], PodcastGaps(
            r["podcast_id"], r["title"], r["entity"], first))
        gaps.windows.append((r["label"], r["start_date"], r["end_date"]))
        if r["n"] == 0:
            gaps.empty.add(r["label"])
    return sorted(by_podcast.values(), key=lambda g: g.span[0])
