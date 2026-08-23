from pathlib import Path

from podcast_pipeline import db
from podcast_pipeline.models import FeedEpisode, PodcastRecord


def podcast(**overrides):
    base = dict(source_id="apple_1", title="Show", rss_url="https://x/feed", apple_podcasts_id="1")
    return PodcastRecord(**{**base, **overrides})


def episode(guid="g1", **overrides):
    base = dict(guid=guid, title=f"Ep {guid}", audio_url=f"https://x/{guid}.mp3")
    return FeedEpisode(**{**base, **overrides})


def test_connect_creates_schema(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"podcasts", "episodes", "transcripts"} <= tables


def test_upsert_podcast_keeps_id_and_episodes(conn):
    pid = db.upsert_podcast(conn, podcast())
    db.insert_episode(conn, pid, episode())
    same = db.upsert_podcast(conn, podcast(title="Show (renamed)", rss_url="https://x/new"))
    assert same == pid
    row = conn.execute("SELECT title, rss_url FROM podcasts").fetchone()
    assert (row["title"], row["rss_url"]) == ("Show (renamed)", "https://x/new")
    assert conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0] == 1
    assert conn.execute("SELECT podcast_id FROM episodes").fetchone()[0] == pid


def test_upsert_matches_legacy_rows_with_null_source_id(conn):
    # Rows written by the old pipeline have podchaser_id NULL but an Apple id.
    conn.execute("INSERT INTO podcasts (title, apple_podcasts_id) VALUES ('Old', '1')")
    legacy_id = conn.execute("SELECT id FROM podcasts").fetchone()[0]
    assert db.upsert_podcast(conn, podcast()) == legacy_id
    assert conn.execute("SELECT podchaser_id FROM podcasts").fetchone()[0] == "apple_1"


def test_insert_episode_ignores_duplicate_guid(conn):
    pid = db.upsert_podcast(conn, podcast())
    assert db.insert_episode(conn, pid, episode()) is True
    assert db.insert_episode(conn, pid, episode(title="again")) is False
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1


def test_download_and_transcript_lifecycle(conn, tmp_path):
    pid = db.upsert_podcast(conn, podcast())
    db.insert_episode(conn, pid, episode())
    eid = conn.execute("SELECT id FROM episodes").fetchone()[0]

    db.record_download(conn, eid, Path("/a.ogg"), 100.0, 20.0, True)
    row = conn.execute("SELECT * FROM episodes").fetchone()
    assert row["status"] == "downloaded" and row["compression_ratio"] == 5.0

    db.record_transcript(conn, eid, tmp_path / "t.zst", 10, 12.5, True, False, {"source": "asr"})
    db.record_transcript(conn, eid, tmp_path / "t.zst", 11, 12.5, True, False, {"source": "asr"})
    assert tuple(conn.execute("SELECT COUNT(*), MAX(word_count) FROM transcripts").fetchone()) == (1, 11)
    assert conn.execute("SELECT status FROM episodes").fetchone()[0] == "transcribed"

    # Transcribed episodes are never re-queued for download.
    assert db.reset_episode_for_download(conn, eid) is False

    db.delete_transcript(conn, eid)
    assert tuple(conn.execute("SELECT status, transcript_file_path FROM episodes").fetchone()) == ("downloaded", None)
    assert db.reset_episode_for_download(conn, eid) is True
    row = conn.execute("SELECT status, audio_file_path FROM episodes").fetchone()
    assert (row[0], row[1]) == ("pending", None)
