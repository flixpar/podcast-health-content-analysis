"""SQLite schema and the write operations the pipeline stages share.

Concurrency rule: every connection is used by exactly one thread. The pipeline
commands open one connection on the main thread and do all writes there;
worker threads return results instead of touching the database. Sharing a
connection across threads is what produced the "cannot start a transaction
within a transaction" failures in the 2025-10-14 run.

Helpers here do not commit; callers decide the transaction boundary.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from podcast_pipeline.models import PodcastRecord, FeedEpisode


class PodcastStatus:
    PENDING = "pending"          # never had its feed read
    DISCOVERED = "discovered"    # feed read, episodes recorded
    ERROR = "error"              # feed could not be fetched or parsed


class EpisodeStatus:
    PENDING = "pending"          # known from the feed, no audio yet
    DOWNLOADED = "downloaded"    # audio on disk, awaiting transcription
    TRANSCRIBED = "transcribed"  # transcript file written (ASR or publisher-provided)
    ERROR = "error"              # see error_message; audio_file_path tells which stage failed


SCHEMA = """
CREATE TABLE IF NOT EXISTS podcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    podchaser_id TEXT UNIQUE,            -- source id: "apple_<id>" or the Podchaser id
    title TEXT NOT NULL,
    description TEXT,
    publisher TEXT,
    rss_url TEXT,
    apple_podcasts_id TEXT,
    spotify_id TEXT,
    categories TEXT,                     -- JSON list
    episode_count INTEGER,
    latest_episode_date TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,              -- last time the feed was read
    status TEXT DEFAULT 'pending',
    metadata TEXT                        -- JSON, the full source record
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    podcast_id INTEGER,
    episode_guid TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    audio_url TEXT,
    duration_seconds INTEGER,            -- as declared by the feed
    published_date TEXT,
    transcript_url TEXT,
    has_rss_transcript BOOLEAN DEFAULT 0,
    audio_file_path TEXT,
    transcript_file_path TEXT,
    transcribed_at TIMESTAMP,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    metadata TEXT,                       -- JSON, the full feed entry
    original_file_size_mb REAL,
    compressed_file_size_mb REAL,
    compression_ratio REAL,
    is_compressed BOOLEAN DEFAULT 0,
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER UNIQUE,
    format TEXT,
    compression TEXT DEFAULT 'zstd',
    file_path TEXT,
    word_count INTEGER,
    duration_seconds REAL,
    confidence_score REAL,
    has_timestamps BOOLEAN DEFAULT 1,
    has_speakers BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                       -- JSON: {"source": "rss"|"asr", ...}
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- Which chart each podcast came from. The collection is assembled from
-- several charts (Apple overall, Apple by genre, Spotify) fetched on
-- different days; this table is what lets a later analysis select a subset
-- ("everything that was in the Apple health top 50") without re-fetching.
CREATE TABLE IF NOT EXISTS podcast_charts (
    podcast_id INTEGER NOT NULL,
    chart TEXT NOT NULL,                 -- e.g. "apple_us_top" or "apple_us_genre_1512"
    rank INTEGER,                        -- 1-based position in that chart
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (podcast_id, chart),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);

CREATE INDEX IF NOT EXISTS idx_podcasts_status ON podcasts(status);
CREATE INDEX IF NOT EXISTS idx_podcast_charts_chart ON podcast_charts(chart);
CREATE INDEX IF NOT EXISTS idx_episodes_status ON episodes(status);
CREATE INDEX IF NOT EXISTS idx_episodes_podcast ON episodes(podcast_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_episode ON transcripts(episode_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database, creating the schema if needed.

    WAL lets readers proceed alongside a writer (a second command, or the
    monitoring queries in ``stats``), and the busy timeout makes a contended
    write wait instead of failing.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=60.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.executescript(SCHEMA)
    return conn


# --- podcasts ----------------------------------------------------------------

def upsert_podcast(conn: sqlite3.Connection, podcast: PodcastRecord) -> int:
    """Insert a podcast or refresh its metadata, keeping its id (and therefore
    its episodes). Returns the row id.

    Rows written by earlier versions have a NULL source id, so an existing row
    is also matched on its Apple id; the source id is filled in on update.
    """
    row = conn.execute(
        "SELECT id FROM podcasts WHERE podchaser_id = ? "
        "OR (apple_podcasts_id IS NOT NULL AND apple_podcasts_id = ?)",
        (podcast.source_id, podcast.apple_podcasts_id),
    ).fetchone()
    values = (
        podcast.source_id, podcast.title, podcast.description, podcast.publisher,
        podcast.rss_url, podcast.apple_podcasts_id, podcast.spotify_id,
        json.dumps(podcast.categories), podcast.latest_episode_date,
        json.dumps(podcast.to_json_dict()),
    )
    if row is None:
        cur = conn.execute("""
            INSERT INTO podcasts (podchaser_id, title, description, publisher, rss_url,
                                  apple_podcasts_id, spotify_id, categories,
                                  latest_episode_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, values)
        return cur.lastrowid
    conn.execute("""
        UPDATE podcasts
        SET podchaser_id = ?, title = ?, description = ?, publisher = ?, rss_url = ?,
            apple_podcasts_id = ?, spotify_id = ?, categories = ?,
            latest_episode_date = ?, metadata = ?, fetched_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, values + (row["id"],))
    return row["id"]


def record_chart_entry(conn: sqlite3.Connection, podcast_id: int, chart: str, rank: int) -> None:
    """Note that ``podcast_id`` appeared at ``rank`` in ``chart``.

    ``first_seen_at`` is kept from the earliest run so the history of a
    re-fetched chart is not lost; the rank is refreshed to the latest.
    """
    conn.execute("""
        INSERT INTO podcast_charts (podcast_id, chart, rank) VALUES (?, ?, ?)
        ON CONFLICT (podcast_id, chart) DO UPDATE
        SET rank = excluded.rank, last_seen_at = CURRENT_TIMESTAMP
    """, (podcast_id, chart, rank))


def set_podcast_status(conn: sqlite3.Connection, podcast_id: int, status: str) -> None:
    conn.execute("UPDATE podcasts SET status = ?, processed_at = CURRENT_TIMESTAMP WHERE id = ?",
                 (status, podcast_id))


# --- episodes ----------------------------------------------------------------

def insert_episode(conn: sqlite3.Connection, podcast_id: int, episode: FeedEpisode) -> bool:
    """Record a feed episode. Returns True if it was new (GUIDs are unique)."""
    cur = conn.execute("""
        INSERT OR IGNORE INTO episodes
            (podcast_id, episode_guid, title, description, audio_url, duration_seconds,
             published_date, transcript_url, has_rss_transcript, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        podcast_id, episode.guid, episode.title, episode.description, episode.audio_url,
        episode.duration_seconds, episode.published_date, episode.transcript_url,
        episode.has_transcript, json.dumps(episode.to_json_dict()),
    ))
    return cur.rowcount == 1


def record_download(conn: sqlite3.Connection, episode_id: int, path: Path,
                    original_size_mb: float, compressed_size_mb: float,
                    is_compressed: bool) -> None:
    ratio = original_size_mb / compressed_size_mb if compressed_size_mb > 0 else 1.0
    conn.execute("""
        UPDATE episodes
        SET audio_file_path = ?, status = ?, error_message = NULL,
            original_file_size_mb = ?, compressed_file_size_mb = ?,
            compression_ratio = ?, is_compressed = ?
        WHERE id = ?
    """, (str(path), EpisodeStatus.DOWNLOADED, original_size_mb, compressed_size_mb,
          ratio, is_compressed, episode_id))


def record_conversion(conn: sqlite3.Connection, episode_id: int, path: Path,
                      original_size_mb: float, compressed_size_mb: float) -> None:
    """Point an episode at its re-encoded file. Status is untouched."""
    ratio = original_size_mb / compressed_size_mb if compressed_size_mb > 0 else 1.0
    conn.execute("""
        UPDATE episodes
        SET audio_file_path = ?, original_file_size_mb = ?, compressed_file_size_mb = ?,
            compression_ratio = ?, is_compressed = 1
        WHERE id = ?
    """, (str(path), original_size_mb, compressed_size_mb, ratio, episode_id))


def mark_episode_error(conn: sqlite3.Connection, episode_id: int, message: str) -> None:
    conn.execute("UPDATE episodes SET status = ?, error_message = ? WHERE id = ?",
                 (EpisodeStatus.ERROR, message[:1000], episode_id))


def reset_episode_for_download(conn: sqlite3.Connection, episode_id: int) -> bool:
    """Clear an episode's audio so the download stage fetches it again.

    Never touches an episode that already has a transcript: text from the
    publisher's feed makes its audio unnecessary. Returns True if reset.
    """
    cur = conn.execute("""
        UPDATE episodes
        SET status = ?, audio_file_path = NULL, error_message = NULL,
            original_file_size_mb = NULL, compressed_file_size_mb = NULL,
            compression_ratio = NULL, is_compressed = 0
        WHERE id = ?
          AND status != ?
          AND (transcript_file_path IS NULL OR transcript_file_path = '')
    """, (EpisodeStatus.PENDING, episode_id, EpisodeStatus.TRANSCRIBED))
    return cur.rowcount == 1


# --- transcripts -------------------------------------------------------------

def record_transcript(conn: sqlite3.Connection, episode_id: int, file_path: Path,
                      word_count: int, duration_seconds: float | None,
                      has_timestamps: bool, has_speakers: bool, metadata: dict) -> None:
    """Register a transcript file and mark the episode transcribed.

    ``metadata`` must carry ``source`` ("asr" or "rss") so the two provenances
    stay distinguishable downstream.
    """
    if "source" not in metadata:
        raise ValueError("transcript metadata must include 'source'")
    conn.execute("""
        INSERT INTO transcripts
            (episode_id, format, compression, file_path, word_count, duration_seconds,
             has_timestamps, has_speakers, metadata)
        VALUES (?, 'jsonl', 'zstd', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(episode_id) DO UPDATE SET
            file_path = excluded.file_path, word_count = excluded.word_count,
            duration_seconds = excluded.duration_seconds,
            has_timestamps = excluded.has_timestamps, has_speakers = excluded.has_speakers,
            metadata = excluded.metadata, created_at = CURRENT_TIMESTAMP
    """, (episode_id, str(file_path), word_count, duration_seconds,
          int(has_timestamps), int(has_speakers), json.dumps(metadata)))
    conn.execute("""
        UPDATE episodes
        SET transcript_file_path = ?, transcribed_at = CURRENT_TIMESTAMP,
            status = ?, error_message = NULL
        WHERE id = ?
    """, (str(file_path), EpisodeStatus.TRANSCRIBED, episode_id))


def delete_transcript(conn: sqlite3.Connection, episode_id: int) -> None:
    """Forget an episode's transcript so it can be transcribed again."""
    conn.execute("DELETE FROM transcripts WHERE episode_id = ?", (episode_id,))
    conn.execute("""
        UPDATE episodes
        SET status = ?, transcript_file_path = NULL, transcribed_at = NULL, error_message = NULL
        WHERE id = ?
    """, (EpisodeStatus.DOWNLOADED, episode_id))
