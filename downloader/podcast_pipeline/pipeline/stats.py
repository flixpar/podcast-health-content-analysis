"""Summary counts for the database and storage."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from podcast_pipeline.config import Config


def run(config: Config, conn: sqlite3.Connection) -> dict:
    stats = {
        "podcasts": _counts_by_status(conn, "podcasts"),
        "episodes": _counts_by_status(conn, "episodes"),
        "episodes_with_rss_transcript": conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE has_rss_transcript = 1").fetchone()[0],
    }
    row = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(word_count), 0), COALESCE(SUM(duration_seconds), 0),
               SUM(json_extract(metadata, '$.source') = 'rss'),
               SUM(json_extract(metadata, '$.source') = 'asr')
        FROM transcripts
    """).fetchone()
    stats["transcripts"] = {
        "total": row[0], "total_words": row[1], "total_hours": round(row[2] / 3600, 1),
        "from_rss": row[3] or 0, "from_asr": row[4] or 0,
    }
    stats["storage"] = {
        "audio_gb": round(_tree_size(config.audio_dir) / 1024 ** 3, 2),
        "transcripts_mb": round(_tree_size(config.transcript_dir) / 1024 ** 2, 2),
    }
    return stats


def _counts_by_status(conn: sqlite3.Connection, table: str) -> dict:
    rows = conn.execute(f"SELECT status, COUNT(*) FROM {table} GROUP BY status").fetchall()
    return {row[0]: row[1] for row in rows}


def _tree_size(root: Path) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            try:
                total += os.stat(os.path.join(dirpath, name)).st_size
            except FileNotFoundError:
                pass   # a download finished/renamed while we walked
    return total
