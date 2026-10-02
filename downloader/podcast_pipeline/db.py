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


class SourceKind:
    """Values of ``podcast_sources.source``."""
    CHART_FETCH = "chart_fetch"        # fetch-podcasts: the podcast was on a live chart (ref: chart name)
    CHART_CAPTURE = "chart_capture"    # capture-charts: seen on a daily live capture (ref: chart id)
    CHART_ARCHIVE = "chart_archive"    # resolved from the reconstructed chart archive (ref: entity)
    STUDY = "study"                    # added because a study selected it (ref: study name)
    MANUAL = "manual"


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

-- ---------------------------------------------------------------------------
-- Provenance. The catalog (podcasts, episodes, audio, transcripts) is shared by
-- every study; these tables record how each item got into it.
-- ---------------------------------------------------------------------------

-- How a podcast entered (or was re-confirmed in) the catalog. A podcast can
-- have many: it charted live, it was found in the chart archive, a study
-- resolved it by title search.
CREATE TABLE IF NOT EXISTS podcast_sources (
    podcast_id INTEGER NOT NULL,
    source TEXT NOT NULL,                -- see SourceKind
    ref TEXT NOT NULL DEFAULT '',        -- chart id, study name, search term, ...
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- NULL on backfilled rows: not known
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detail TEXT,                         -- JSON evidence
    PRIMARY KEY (podcast_id, source, ref),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);

-- Every feed URL known for a podcast. ``podcasts.rss_url`` stays the current
-- one; older URLs (a publisher migration, an archived iTunes lookup) are kept
-- here because archived copies of the *old* URL are often what reaches back
-- into a show's early years. The item counts are what the last read saw, so a
-- rolling feed (oldest item moving forward between reads) is visible.
CREATE TABLE IF NOT EXISTS podcast_feeds (
    podcast_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    source TEXT NOT NULL,                -- 'itunes_lookup' | 'archived_lookup' | 'recoverability' | 'manual' | 'backfill'
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_read_at TIMESTAMP,
    last_status TEXT,                    -- 'ok' or the error
    item_count INTEGER,
    oldest_item TEXT,
    newest_item TEXT,
    PRIMARY KEY (podcast_id, url),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);

-- How an episode is known. 'feed' = the live feed (ref: its URL);
-- 'wayback_feed' = an archived copy of a feed (ref: the capture URL);
-- 'wayback_audio' = the audio itself came from the Wayback Machine because
-- the enclosure URL no longer serves it (ref: the archived audio URL).
CREATE TABLE IF NOT EXISTS episode_sources (
    episode_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    ref TEXT NOT NULL DEFAULT '',
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- NULL on backfilled rows
    PRIMARY KEY (episode_id, source, ref),
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

-- Identity decisions an id does not carry: which catalog podcast a chart
-- entity ('title:<key>' with no Apple id, or an Apple id the lookup API no
-- longer knows) refers to. podcast_id NULL records a failed attempt, so it is
-- not retried blindly; ``detail`` keeps the evidence either way.
CREATE TABLE IF NOT EXISTS entity_links (
    entity TEXT PRIMARY KEY,             -- 'apple:<id>' | 'title:<key>'
    podcast_id INTEGER,
    method TEXT NOT NULL,                -- 'itunes_lookup' | 'itunes_search' | 'recoverability' | 'manual'
    detail TEXT,
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);

-- One row per (podcast, feed URL) archive search by `discover-archived`, so a
-- re-run resumes instead of re-querying, and status can say what was tried.
CREATE TABLE IF NOT EXISTS wayback_probes (
    podcast_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    probed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,                -- 'ok' | 'no_captures' | 'error'
    captures_listed INTEGER,
    captures_fetched INTEGER,
    episodes_found INTEGER,
    episodes_new INTEGER,
    windows_targeted TEXT,               -- JSON list of [start, end) the probe aimed at
    detail TEXT,                         -- JSON
    PRIMARY KEY (podcast_id, url),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);

-- ---------------------------------------------------------------------------
-- Chart history: the reconstructed 2012-2026 archive and live daily captures,
-- in one shape. A snapshot is one chart, from one source, on one day.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chart_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,                -- publisher or mirror: 'podbay', 'chartable_itunes',
                                         -- 'apple_charts_page', 'apple_marketing_tools', 'spotify_api', ...
    chart TEXT NOT NULL,                 -- '<platform>:<region>:<unit>:<genre>', e.g. 'apple:us:podcast:all'
    captured_on TEXT NOT NULL,           -- UTC date of capture; the chart's date to within a day
    captured_at TEXT,                    -- earliest capture time that day (ISO)
    origin TEXT NOT NULL,                -- 'wayback' | 'common_crawl' | 'live'
    depth INTEGER NOT NULL,              -- highest rank present
    n_entries INTEGER NOT NULL,
    complete_to INTEGER NOT NULL,        -- largest N with every rank 1..N present
    trusted BOOLEAN NOT NULL DEFAULT 1,  -- 0: complete but known wrong (see note)
    raw_path TEXT,
    note TEXT,
    UNIQUE (source, chart, captured_on)
);

CREATE TABLE IF NOT EXISTS chart_entries (
    snapshot_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    name TEXT,
    publisher TEXT,
    title_key TEXT,                      -- lowercase name with everything but [a-z0-9] removed
    apple_id TEXT,                       -- only when the source itself carries a genuine Apple podcast id
    source_entity_id TEXT,               -- the source's own id (Chartable slug, Spotify show id, ...)
    entity_url TEXT,
    PRIMARY KEY (snapshot_id, rank),
    FOREIGN KEY (snapshot_id) REFERENCES chart_snapshots(id)
);

-- ---------------------------------------------------------------------------
-- Studies. A study is a named selection over the shared catalog, defined in
-- code (podcast_pipeline/studies/) and materialized here by `study refresh`.
-- Work stages run per study but write per episode, so nothing is done twice.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS studies (
    name TEXT PRIMARY KEY,
    description TEXT,
    definition TEXT NOT NULL,            -- JSON: module, version, params
    definition_hash TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0, -- bumped whenever membership changes
    refreshed_at TIMESTAMP,
    summary TEXT                         -- JSON from the last refresh
);

CREATE TABLE IF NOT EXISTS study_revisions (
    study TEXT NOT NULL,
    revision INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    definition_hash TEXT NOT NULL,
    summary TEXT,                        -- JSON: members, episodes, added, removed
    PRIMARY KEY (study, revision)
);

-- One row per selected entity. podcast_id is NULL until the entity has been
-- resolved to a catalog podcast (`resolve --study`).
CREATE TABLE IF NOT EXISTS study_members (
    study TEXT NOT NULL,
    entity TEXT NOT NULL,                -- 'podcast:<id>' | 'apple:<id>' | 'title:<key>'
    podcast_id INTEGER,
    name TEXT,
    scope TEXT NOT NULL,                 -- 'all' (every episode) | 'windows' (see study_windows)
    attrs TEXT,                          -- JSON: why the entity is in
    PRIMARY KEY (study, entity)
);

-- Publication-date windows whose episodes a member contributes.
CREATE TABLE IF NOT EXISTS study_windows (
    study TEXT NOT NULL,
    entity TEXT NOT NULL,
    label TEXT NOT NULL,                 -- e.g. '2017-03'
    start_date TEXT NOT NULL,            -- inclusive ISO date
    end_date TEXT NOT NULL,              -- exclusive ISO date
    attrs TEXT,
    PRIMARY KEY (study, entity, label)
);

CREATE TABLE IF NOT EXISTS study_episodes (
    study TEXT NOT NULL,
    episode_id INTEGER NOT NULL,
    entity TEXT NOT NULL,
    window_label TEXT,                   -- NULL when the member's scope is 'all'
    priority INTEGER NOT NULL,           -- work order; round-robin across windows
    added_revision INTEGER NOT NULL,
    PRIMARY KEY (study, episode_id)
);

CREATE INDEX IF NOT EXISTS idx_podcasts_status ON podcasts(status);
CREATE INDEX IF NOT EXISTS idx_podcasts_apple ON podcasts(apple_podcasts_id);
CREATE INDEX IF NOT EXISTS idx_episode_sources_source ON episode_sources(source);
CREATE INDEX IF NOT EXISTS idx_chart_snapshots_chart ON chart_snapshots(chart, captured_on);
CREATE INDEX IF NOT EXISTS idx_chart_entries_apple ON chart_entries(apple_id);
CREATE INDEX IF NOT EXISTS idx_chart_entries_key ON chart_entries(title_key);
CREATE INDEX IF NOT EXISTS idx_study_members_podcast ON study_members(podcast_id);
CREATE INDEX IF NOT EXISTS idx_study_episodes_episode ON study_episodes(episode_id);
CREATE INDEX IF NOT EXISTS idx_study_episodes_order ON study_episodes(study, priority, episode_id);
CREATE INDEX IF NOT EXISTS idx_podcast_charts_chart ON podcast_charts(chart);
CREATE INDEX IF NOT EXISTS idx_episodes_status ON episodes(status);
CREATE INDEX IF NOT EXISTS idx_episodes_podcast ON episodes(podcast_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_episode ON transcripts(episode_id);
"""


#: How long a contended write waits before giving up. Long enough that a
#: multi-day ``download`` survives another command's write burst.
BUSY_TIMEOUT_SECONDS = 300.0


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database, creating the schema if needed.

    WAL lets readers proceed alongside a writer (a second command, or the
    monitoring queries in ``stats``), and the busy timeout makes a contended
    write wait instead of failing.

    The timeout is generous because ``download`` runs for days: a 60 s wait was
    not enough to outlast a concurrent ``discover`` + ``fetch-rss-transcripts``
    pass, and the download died with "database is locked" after an hour of work.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=BUSY_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(f"PRAGMA busy_timeout={int(BUSY_TIMEOUT_SECONDS * 1000)}")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


#: ``PRAGMA user_version`` once provenance has been backfilled for rows that
#: predate the provenance tables.
SCHEMA_VERSION = 1


def _migrate(conn: sqlite3.Connection) -> None:
    """One-time, additive backfill. Nothing existing is modified or deleted.

    Rows written before provenance existed get it from what the database
    already knows: podcasts from ``podcast_charts``, feeds from
    ``podcasts.rss_url``, episodes from their podcast's feed. ``first_seen_at``
    is left NULL on backfilled episode rows because it was never recorded.
    """
    if conn.execute("PRAGMA user_version").fetchone()[0] >= SCHEMA_VERSION:
        return
    with conn:
        conn.execute("""
            INSERT OR IGNORE INTO podcast_sources (podcast_id, source, ref, first_seen_at, last_seen_at)
            SELECT podcast_id, ?, chart, first_seen_at, last_seen_at FROM podcast_charts
        """, (SourceKind.CHART_FETCH,))
        conn.execute("""
            INSERT OR IGNORE INTO podcast_feeds
                (podcast_id, url, source, first_seen_at, last_read_at, last_status,
                 item_count, oldest_item, newest_item)
            SELECT p.id, p.rss_url, 'backfill', p.fetched_at, p.processed_at,
                   CASE p.status WHEN 'discovered' THEN 'ok' ELSE p.status END,
                   NULL, NULL, NULL
            FROM podcasts p WHERE p.rss_url IS NOT NULL AND p.rss_url != ''
        """)
        conn.execute("""
            INSERT OR IGNORE INTO episode_sources (episode_id, source, ref, first_seen_at)
            SELECT e.id, 'feed', COALESCE(p.rss_url, ''), NULL
            FROM episodes e JOIN podcasts p ON p.id = e.podcast_id
        """)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


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


def record_podcast_source(conn: sqlite3.Connection, podcast_id: int, source: str,
                          ref: str = "", detail: dict | None = None) -> None:
    """Note how ``podcast_id`` came into the catalog; repeats refresh ``last_seen_at``."""
    conn.execute("""
        INSERT INTO podcast_sources (podcast_id, source, ref, detail) VALUES (?, ?, ?, ?)
        ON CONFLICT (podcast_id, source, ref) DO UPDATE
        SET last_seen_at = CURRENT_TIMESTAMP, detail = COALESCE(excluded.detail, detail)
    """, (podcast_id, source, ref, json.dumps(detail) if detail is not None else None))


def record_feed_url(conn: sqlite3.Connection, podcast_id: int, url: str, source: str) -> None:
    """Remember a feed URL for a podcast without changing its current ``rss_url``."""
    conn.execute("INSERT OR IGNORE INTO podcast_feeds (podcast_id, url, source) VALUES (?, ?, ?)",
                 (podcast_id, url, source))


def record_feed_read(conn: sqlite3.Connection, podcast_id: int, url: str, status: str,
                     episodes: list[FeedEpisode] | None = None) -> None:
    """What the latest read of a feed saw: its size and the dates it spans."""
    dates = sorted(e.published_date for e in episodes or [] if e.published_date)
    conn.execute("INSERT OR IGNORE INTO podcast_feeds (podcast_id, url, source) VALUES (?, ?, 'itunes_lookup')",
                 (podcast_id, url))
    conn.execute("""
        UPDATE podcast_feeds
        SET last_read_at = CURRENT_TIMESTAMP, last_status = ?,
            item_count = COALESCE(?, item_count),
            oldest_item = COALESCE(?, oldest_item), newest_item = COALESCE(?, newest_item)
        WHERE podcast_id = ? AND url = ?
    """, (status[:500], len(episodes) if episodes is not None else None,
          dates[0] if dates else None, dates[-1] if dates else None, podcast_id, url))


def link_entity(conn: sqlite3.Connection, entity: str, podcast_id: int | None, method: str,
                detail: dict | None = None) -> None:
    """Record which podcast a chart entity is (or that a resolution attempt failed)."""
    conn.execute("""
        INSERT INTO entity_links (entity, podcast_id, method, detail) VALUES (?, ?, ?, ?)
        ON CONFLICT (entity) DO UPDATE SET podcast_id = excluded.podcast_id,
            method = excluded.method, detail = excluded.detail, resolved_at = CURRENT_TIMESTAMP
    """, (entity, podcast_id, method, json.dumps(detail) if detail is not None else None))


def podcast_for_entity(conn: sqlite3.Connection, entity: str) -> int | None:
    """The catalog podcast an entity refers to, or None if it is not resolved.

    'podcast:<id>' is the id itself; 'apple:<id>' matches the podcast's Apple
    id; anything else (or an Apple id the catalog lacks) goes through
    ``entity_links``.
    """
    kind, _, value = entity.partition(":")
    if kind == "podcast":
        return int(value)
    if kind == "apple":
        row = conn.execute("SELECT id FROM podcasts WHERE apple_podcasts_id = ? ORDER BY id LIMIT 1",
                           (value,)).fetchone()
        if row:
            return row["id"]
    row = conn.execute("SELECT podcast_id FROM entity_links WHERE entity = ?", (entity,)).fetchone()
    return row["podcast_id"] if row else None


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


def record_episode_source(conn: sqlite3.Connection, podcast_id: int, guid: str,
                          source: str, ref: str = "") -> None:
    """Note where an episode (identified by its podcast and GUID) was seen."""
    conn.execute("""
        INSERT OR IGNORE INTO episode_sources (episode_id, source, ref)
        SELECT id, ?, ? FROM episodes WHERE episode_guid = ? AND podcast_id = ?
    """, (source, ref, guid, podcast_id))


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
