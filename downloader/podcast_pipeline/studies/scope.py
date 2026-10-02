"""SQL fragments that restrict a work stage to one study.

Stages keep writing per episode, exactly as before; a study only narrows which
rows a run picks up. Work done for one study is therefore already done for
every other study that contains the same episode.
"""

from __future__ import annotations

import sqlite3


class StudyError(ValueError):
    """The named study does not exist or has not been materialized."""


def require_refreshed(conn: sqlite3.Connection, study: str) -> None:
    row = conn.execute("SELECT refreshed_at FROM studies WHERE name = ?", (study,)).fetchone()
    if row is None:
        known = [r[0] for r in conn.execute("SELECT name FROM studies ORDER BY name")]
        raise StudyError(f"Study {study!r} has never been refreshed (materialized studies: {known}). "
                         f"Run `study refresh {study}` first.")


def episode_filter(conn: sqlite3.Connection, study: str | None,
                   column: str = "e.id") -> tuple[str, list]:
    """``AND <column> IN (study's episodes)``, or nothing when ``study`` is None."""
    if not study:
        return "", []
    require_refreshed(conn, study)
    return f"AND {column} IN (SELECT episode_id FROM study_episodes WHERE study = ?)", [study]


def podcast_filter(conn: sqlite3.Connection, study: str | None,
                   column: str = "p.id") -> tuple[str, list]:
    """``AND <column> IN (study's resolved podcasts)``.

    With no study, the podcasts of *every* study: the catalog may hold far
    more podcasts than anyone has asked to collect.
    """
    if study:
        require_refreshed(conn, study)
        return (f"AND {column} IN (SELECT podcast_id FROM study_members "
                f"WHERE study = ? AND podcast_id IS NOT NULL)", [study])
    return (f"AND {column} IN (SELECT podcast_id FROM study_members "
            f"WHERE podcast_id IS NOT NULL)", [])
