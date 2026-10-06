"""The collection as it stood when studies were introduced (2026-10-02).

Every podcast recorded from the four live charts fetched since 2025-10-13 --
Apple US overall top 100 (the original 2025-10-13 fetch and its refresh),
Apple US Health & Fitness top 50, Spotify US top 100 -- and every episode
their feeds list (the newest ``discovery.max_episodes_per_podcast``). This is
what the existing transcripts, the lexical scan and the labeling pilots were
run on.

Membership is frozen at podcasts first recorded before ``ADDED_BEFORE``: a
later ``fetch-podcasts`` that reuses one of these chart names adds new shows
to the catalog, not to this study. Episodes are not frozen, because the study
is also the ongoing live panel; ``discover`` keeps adding its new episodes.
"""

from __future__ import annotations

import sqlite3

from podcast_pipeline.studies.base import Member, Study

CHARTS = ("apple_us_top_20251013", "apple_us_top", "apple_us_genre_1512", "spotify_us_top")
ADDED_BEFORE = "2026-10-03"


class Corpus2025(Study):
    name = "corpus-2025"
    description = ("The 2025-26 live-chart collection: Apple US top 100, Apple US Health & "
                   "Fitness top 50 and Spotify US top 100 (fetched from 2025-10-13), all episodes.")
    version = 1

    def params(self) -> dict:
        return {"charts": list(CHARTS), "added_before": ADDED_BEFORE}

    def select(self, conn: sqlite3.Connection) -> list[Member]:
        rows = conn.execute(f"""
            SELECT p.id, p.title, GROUP_CONCAT(c.chart || ':' || COALESCE(c.rank, ''), ' ') AS charts
            FROM podcast_charts c JOIN podcasts p ON p.id = c.podcast_id
            WHERE c.chart IN ({",".join("?" * len(CHARTS))})
              AND c.first_seen_at < ?
            GROUP BY p.id ORDER BY p.id
        """, (*CHARTS, ADDED_BEFORE)).fetchall()
        return [Member(f"podcast:{r['id']}", r["title"], None, {"charts": r["charts"].split(" ")})
                for r in rows]
