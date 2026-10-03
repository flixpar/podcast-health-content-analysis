"""Paths stored relative to the data directory, and the migration of absolute ones."""

import pytest

from podcast_pipeline import db, paths
from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.config import Config
from podcast_pipeline.models import FeedEpisode, PodcastRecord
from podcast_pipeline.pipeline import audit, convert_audio, migrate_paths, transcribe

AUDIO = b"\0" * (MIN_AUDIO_BYTES + 1)
OLD = "/home/felix/projects/podcast-misinfo/downloader/data/"


@pytest.fixture
def linked(tmp_path):
    """A data directory that is a symlink, as ``downloader/data`` is."""
    real = tmp_path / "volume" / "podcasts-2025-10-13"
    real.mkdir(parents=True)
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "data").symlink_to(real)
    config = Config(data_dir=str(tmp_path / "repo" / "data"))
    conn = db.connect(config.db_path)
    yield config, conn, real
    conn.close()


def _file(config, relative, data=AUDIO):
    path = config.data_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _episode(conn, guid, audio=None, transcript=None, original_mb=None, duration=None):
    pid = db.upsert_podcast(conn, PodcastRecord("apple_1", "Show", apple_podcasts_id="1"))
    db.insert_episode(conn, pid, FeedEpisode(guid, f"Ep {guid}", f"https://x/{guid}.mp3",
                                             duration_seconds=duration))
    eid = conn.execute("SELECT id FROM episodes WHERE episode_guid = ?", (guid,)).fetchone()[0]
    conn.execute("""UPDATE episodes SET audio_file_path = ?, transcript_file_path = ?,
                    status = 'downloaded', original_file_size_mb = ?, compressed_file_size_mb = ?,
                    is_compressed = 0 WHERE id = ?""",
                 (audio, transcript, original_mb, original_mb, eid))
    if transcript:
        conn.execute("INSERT INTO transcripts (episode_id, file_path) VALUES (?, ?)", (eid, transcript))
    conn.commit()
    return eid


# --- the storage contract ------------------------------------------------------

def test_to_stored_and_resolve_round_trip(linked):
    config, _, real = linked
    file = config.audio_dir / "show" / "ep.ogg"
    assert paths.to_stored(config, file) == "audio/show/ep.ogg"
    assert paths.to_stored(config, real / "audio" / "show" / "ep.ogg") == "audio/show/ep.ogg"
    assert paths.resolve(config, "audio/show/ep.ogg") == file
    assert paths.resolve(config, "/legacy/abs.ogg").as_posix() == "/legacy/abs.ogg"
    assert paths.resolve(config, None) is None and paths.resolve(config, "") is None
    with pytest.raises(paths.StoredPathError):
        paths.to_stored(config, "/elsewhere/ep.ogg")


# --- the migration --------------------------------------------------------------

@pytest.fixture
def legacy(linked, monkeypatch):
    """Rows as the database held them: absolute paths under several prefixes."""
    config, conn, real = linked
    monkeypatch.setattr(migrate_paths, "probe_audio_codec", lambda path: "opus")
    monkeypatch.setattr(migrate_paths, "probe_duration", lambda path: 3600.0)
    _file(config, "audio/show/old.ogg")
    _file(config, "audio/show/worktree.ogg")
    _file(config, "audio/show/real.ogg")
    _file(config, "audio/show/converted.ogg")
    _file(config, "audio/show/vorbis.ogg")
    _file(config, "transcripts/episode_1.jsonl.zst", b"t")
    ids = {
        "old": _episode(conn, "old", OLD + "audio/show/old.ogg",
                        OLD + "transcripts/episode_1.jsonl.zst"),
        "worktree": _episode(conn, "worktree", str(config.data_path / "audio/show/worktree.ogg")),
        "real": _episode(conn, "real", str(real / "audio/show/real.ogg")),
        "relative": _episode(conn, "relative", "audio/show/real.ogg"),
        # 54.97 MB of 128 kbps MP3 is one hour, the .ogg's duration
        "converted": _episode(conn, "converted", OLD + "audio/show/converted.mp3", original_mb=54.97),
        "implausible": _episode(conn, "implausible", OLD + "audio/show/vorbis.mp3", original_mb=900.0),
        "missing": _episode(conn, "missing", OLD + "audio/show/gone.ogg"),
        "unmapped": _episode(conn, "unmapped", "/somewhere/else/x.ogg"),
    }
    return config, conn, ids


def _audio(conn, eid):
    return conn.execute("SELECT audio_file_path FROM episodes WHERE id = ?", (eid,)).fetchone()[0]


def test_dry_run_reports_and_writes_nothing(legacy):
    config, conn, ids = legacy
    before = [tuple(r) for r in conn.execute("SELECT * FROM episodes ORDER BY id")]
    result = migrate_paths.run(config, conn, dry_run=True)
    audio = result["episodes.audio_file_path"]
    assert (audio["absolute_before"], audio["relative_before"]) == (7, 1)
    assert audio["migrated"] == 4 and audio["mp3_to_ogg"] == 1
    assert audio["missing"] == 2 and audio["unmapped"] == 1
    assert [tuple(r) for r in conn.execute("SELECT * FROM episodes ORDER BY id")] == before
    assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'path_migration_backup'").fetchone()


def test_migration_rewrites_verified_paths_and_backs_them_up(legacy):
    config, conn, ids = legacy
    result = migrate_paths.run(config, conn)

    assert _audio(conn, ids["old"]) == "audio/show/old.ogg"
    assert _audio(conn, ids["worktree"]) == "audio/show/worktree.ogg"
    assert _audio(conn, ids["real"]) == "audio/show/real.ogg"
    assert _audio(conn, ids["relative"]) == "audio/show/real.ogg"
    # untouched: no file, an .ogg that is not the conversion, an unknown prefix
    assert _audio(conn, ids["missing"]) == OLD + "audio/show/gone.ogg"
    assert _audio(conn, ids["implausible"]) == OLD + "audio/show/vorbis.mp3"
    assert _audio(conn, ids["unmapped"]) == "/somewhere/else/x.ogg"

    # the MP3 was converted: point at the .ogg and record the conversion
    row = conn.execute("SELECT audio_file_path, is_compressed, compressed_file_size_mb "
                       "FROM episodes WHERE id = ?", (ids["converted"],)).fetchone()
    assert row[0] == "audio/show/converted.ogg" and row[1] == 1
    assert row[2] == pytest.approx(len(AUDIO) / 1024 ** 2)

    stored = conn.execute("SELECT e.transcript_file_path, t.file_path FROM episodes e "
                          "JOIN transcripts t ON t.episode_id = e.id").fetchone()
    assert tuple(stored) == ("transcripts/episode_1.jsonl.zst",) * 2

    backup = {(r["table_name"], r["row_id"], r["column_name"]): (r["old_value"], r["new_value"])
              for r in conn.execute("SELECT * FROM path_migration_backup")}
    assert backup[("episodes", ids["old"], "audio_file_path")] == (
        OLD + "audio/show/old.ogg", "audio/show/old.ogg")
    assert backup[("episodes", ids["converted"], "is_compressed")] == ("0", "1")   # TEXT column
    assert ("episodes", ids["relative"], "audio_file_path") not in backup
    assert len(backup) == 4 + 3 + 1 + 1   # audio + mp3 extras + both transcript columns

    audio = result["episodes.audio_file_path"]
    assert audio["migrated"] == 4 and audio["absolute_after"] == 3 and audio["relative_after"] == 5
    assert {e["row_id"] for e in audio["examples"]["missing"]} == {ids["missing"], ids["implausible"]}
    assert audio["examples"]["unmapped"][0]["value"] == "/somewhere/else/x.ogg"
    assert result["transcripts.file_path"]["absolute_after"] == 0

    # Idempotent: nothing left to do, nothing new backed up.
    again = migrate_paths.run(config, conn)
    assert again["episodes.audio_file_path"]["migrated"] == 0
    assert again["transcripts.file_path"]["absolute_before"] == 0
    assert conn.execute("SELECT COUNT(*) FROM path_migration_backup").fetchone()[0] == len(backup)


def test_migration_batches_and_skips_a_row_changed_underneath(legacy, monkeypatch):
    config, conn, ids = legacy
    monkeypatch.setattr(migrate_paths, "BATCH_ROWS", 2)
    real_plan = migrate_paths._plan

    def plan_then_concurrent_write(config, table, column, rows, report, taken=frozenset()):
        changes = real_plan(config, table, column, rows, report, taken)
        if column == "audio_file_path" and any(r["row_id"] == ids["old"] for r in rows):
            conn.execute("UPDATE episodes SET audio_file_path = 'audio/show/other.ogg' WHERE id = ?",
                         (ids["old"],))
        return changes

    monkeypatch.setattr(migrate_paths, "_plan", plan_then_concurrent_write)
    result = migrate_paths.run(config, conn)
    assert _audio(conn, ids["old"]) == "audio/show/other.ogg"
    assert result["episodes.audio_file_path"]["conflicts"] == 1
    assert result["episodes.audio_file_path"]["migrated"] == 3
    assert _audio(conn, ids["converted"]) == "audio/show/converted.ogg"


# --- readers take both forms ------------------------------------------------------

def test_readers_resolve_relative_and_absolute_values(linked):
    config, conn, real = linked
    relative = _file(config, "audio/show/rel.mp3")
    absolute = _file(config, "audio/show/abs.mp3")
    rel_id = _episode(conn, "rel", "audio/show/rel.mp3")
    abs_id = _episode(conn, "abs", str(absolute))

    jobs = {j.episode_id: j.audio_path for j in transcribe.episodes_to_transcribe(config, conn, False, None)}
    assert jobs == {rel_id: relative, abs_id: absolute}

    findings = audit.audit(config, conn, skip_probe=True)
    assert not findings["missing"] and not findings["orphan"] and not findings["shared_path"]

    todo = {c.episode_id: c.source for c in convert_audio.candidates(config, conn, 0, False)}
    assert todo == {rel_id: relative, abs_id: absolute}


def test_convert_audio_never_treats_an_ogg_as_its_own_source(linked):
    config, conn, _ = linked
    _file(config, "audio/show/x.ogg")
    _episode(conn, "x", "audio/show/x.ogg")   # is_compressed = 0, but already Opus
    assert convert_audio.candidates(config, conn, 0, False) == []


def test_a_sibling_another_episode_owns_is_not_taken(legacy):
    config, conn, ids = legacy
    # a rerun whose legacy name collides with the first airing's converted file
    owner = _episode(conn, "owner", OLD + "audio/show/shared.ogg")
    _file(config, "audio/show/shared.ogg")
    rerun = _episode(conn, "rerun", OLD + "audio/show/shared.mp3", original_mb=54.97)
    migrate_paths.run(config, conn)
    assert _audio(conn, owner) == "audio/show/shared.ogg"
    assert _audio(conn, rerun) == OLD + "audio/show/shared.mp3"   # left for a re-download
