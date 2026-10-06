"""Recovery diagnostics honor configured archives without touching real data."""

import csv
import json
import sys

import pytest

from tools.alternate_sources import archived_alt_feed
from podcast_pipeline import db
from podcast_pipeline.models import FeedEpisode, PodcastRecord
from podcast_pipeline.studies.base import Member, Study
from podcast_pipeline.studies.materialize import refresh
from tools.audit import decode_sample, study_episodes, study_identity


@pytest.mark.parametrize("absolute", [False, True])
def test_decode_audit_resolves_custom_data_directory(config, monkeypatch, absolute):
    audio = config.audio_dir / "show" / "clip.ogg"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"test fixture")
    probed = []
    monkeypatch.setattr(decode_sample, "probe", lambda path:
                        probed.append(path) or {"has_audio_stream": True, "header_duration": 120})
    monkeypatch.setattr(decode_sample, "decode", lambda path:
                        {"decoded_duration": 120, "decode_error_lines": 0, "returncode": 0})
    row = {"audio_file_path": str(audio) if absolute else "audio/show/clip.ogg",
           "duration_seconds": 120}
    result = decode_sample.check(row, config)
    assert probed == [audio]
    assert result["local_path"] == str(audio)
    assert result["exists"] and result["flags"] == ""


@pytest.mark.parametrize("stored", [None, "", "audio/missing.ogg"])
def test_decode_audit_records_missing_paths(config, stored):
    result = decode_sample.check({"audio_file_path": stored, "duration_seconds": 120}, config)
    assert result["flags"] == "not_audio(missing)"
    assert not result["exists"]


@pytest.mark.parametrize("override", [False, True])
def test_alternate_feed_tool_uses_configured_database_and_cache(conn, config, tmp_path, monkeypatch, override):
    output = tmp_path / "reports"
    cache = tmp_path / "custom-cache" if override else config.wayback_cache_dir / "alternate_feeds"
    argv = ["archived_alt_feed.py", "fixed", str(output), "--feed", "7=https://example.com/feed"]
    if override:
        argv += ["--cache-dir", str(cache)]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(archived_alt_feed.Config, "load", lambda: config)
    monkeypatch.setattr(archived_alt_feed, "CACHE", None)
    opened = []
    monkeypatch.setattr(archived_alt_feed, "open_db", lambda path: opened.append(path) or conn)
    monkeypatch.setattr(archived_alt_feed, "Fetcher", lambda: None)

    def collect(connection, fetcher, settings, study, podcast_id, feed, *args):
        assert connection is conn and settings is config
        assert archived_alt_feed.CACHE == cache
        assert (study, podcast_id, feed) == ("fixed", 7, "https://example.com/feed")
        return [], {"captures": []}

    monkeypatch.setattr(archived_alt_feed, "collect", collect)
    archived_alt_feed.main()
    assert opened == [config.db_path]
    assert (output / "alternate_feed.jsonl").read_text() == ""
    assert (output / "alternate_feed.log.jsonl").exists()


@pytest.mark.parametrize("has_episode", [False, True])
def test_audits_write_header_only_reports_without_flags_or_windows(conn, config, tmp_path, has_episode):
    class Sample(Study):
        name = "sample"
        description = "test"

        def select(self, connection):
            return [Member(f"podcast:{podcast}", "Show")] if has_episode else []

    podcast = db.upsert_podcast(conn, PodcastRecord(source_id="test", title="Show"))
    if has_episode:
        db.insert_episode(conn, podcast, FeedEpisode("guid", "Regular episode", "https://example.com/audio",
                                                   duration_seconds=1200, published_date="2020-01-01"))
    conn.commit()
    refresh(conn, Sample())
    output = tmp_path / "episode-audit"
    study_episodes.main("sample", str(output), config)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["episodes"] == int(has_episode)
    assert summary["flag_rows"] == summary["windows"] == 0
    with (output / "flagged_episodes.csv").open() as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == study_episodes.FLAG_FIELDS
        assert list(reader) == []
    identity = tmp_path / "identity.csv"
    study_identity.main("sample", str(identity), config)
    with identity.open() as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == study_identity.FIELDS
        assert len(list(reader)) == int(has_episode)
