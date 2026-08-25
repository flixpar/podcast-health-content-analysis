"""End-to-end tests of each stage against a temporary data directory, with the
network and GPU replaced by fakes at the module boundary."""

import sys
import types
from pathlib import Path

import pytest

from podcast_pipeline import db
from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.audio.download import DownloadError, DownloadResult
from podcast_pipeline.audio.ffmpeg import EncodeError
from podcast_pipeline.models import FeedEpisode, PodcastRecord, Segment
from podcast_pipeline.pipeline import (audit, convert_audio, discover, download,
                                       fetch_podcasts, reset_transcripts, rss_transcripts,
                                       stats, transcribe)
from podcast_pipeline.pipeline.rss_transcripts import FetchedTranscript, RssTranscriptError
from podcast_pipeline.rss import FeedError
from podcast_pipeline.transcripts.store import TranscriptStore

REAL_AUDIO = b"\0" * (MIN_AUDIO_BYTES + 1)


class FakeSource:
    chart_name = "fake_chart"

    def __init__(self, records):
        self.records = records

    def top_podcasts(self, limit):
        return self.records[:limit]


@pytest.fixture
def seeded(config, conn, monkeypatch):
    """Two podcasts with episodes discovered: one normal, one with a publisher transcript."""
    records = [PodcastRecord("apple_1", "Show One", rss_url="https://x/one", apple_podcasts_id="1"),
               PodcastRecord("apple_2", "Show Two", rss_url="https://x/two", apple_podcasts_id="2"),
               PodcastRecord("apple_3", "No Feed", apple_podcasts_id="3")]
    monkeypatch.setattr(fetch_podcasts, "make_source", lambda cfg, session: FakeSource(records))
    fetch_podcasts.run(config, conn)

    feeds = {
        "https://x/one": [FeedEpisode("g1", "Ep One", "https://x/1.mp3", duration_seconds=600),
                          FeedEpisode("g2", "Ep Two", "https://x/2.mp3")],
        "https://x/two": [FeedEpisode("g3", "Has Transcript", "https://x/3.mp3",
                                      transcript_url="https://x/3.srt")],
    }
    monkeypatch.setattr(discover, "fetch_feed", lambda url, session, timeout: feeds[url])
    discover.run(config, conn)
    return config, conn


def test_fetch_and_discover(seeded):
    config, conn = seeded
    assert conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 3
    statuses = dict(conn.execute("SELECT title, status FROM podcasts").fetchall())
    assert statuses == {"Show One": "discovered", "Show Two": "discovered", "No Feed": "pending"}
    assert conn.execute("SELECT has_rss_transcript FROM episodes WHERE episode_guid='g3'").fetchone()[0] == 1


def test_fetch_records_chart_membership(seeded):
    _, conn = seeded
    rows = conn.execute("""
        SELECT p.title, c.chart, c.rank FROM podcast_charts c
        JOIN podcasts p ON p.id = c.podcast_id ORDER BY c.rank
    """).fetchall()
    assert [tuple(r) for r in rows] == [("Show One", "fake_chart", 1),
                                        ("Show Two", "fake_chart", 2),
                                        ("No Feed", "fake_chart", 3)]


def test_refetching_a_chart_updates_rank_without_duplicating(seeded, config, monkeypatch):
    """A chart re-fetched later must not add a second podcast row: the whole
    collection is assembled by repeated additive fetches."""
    _, conn = seeded
    reordered = [PodcastRecord("apple_2", "Show Two", rss_url="https://x/two", apple_podcasts_id="2"),
                 PodcastRecord("apple_1", "Show One", rss_url="https://x/one", apple_podcasts_id="1")]
    monkeypatch.setattr(fetch_podcasts, "make_source", lambda cfg, session: FakeSource(reordered))
    result = fetch_podcasts.run(config, conn)

    assert result["new"] == 0 and result["updated"] == 2
    assert conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0] == 3
    ranks = dict(conn.execute("""
        SELECT p.title, c.rank FROM podcast_charts c JOIN podcasts p ON p.id = c.podcast_id
    """).fetchall())
    assert ranks == {"Show Two": 1, "Show One": 2, "No Feed": 3}


def test_discover_is_idempotent_and_marks_feed_errors(seeded, monkeypatch):
    config, conn = seeded

    def flaky(url, session, timeout):
        if url == "https://x/one":
            raise FeedError("404")
        return [FeedEpisode("g3", "Has Transcript", "https://x/3.mp3"), FeedEpisode("g4", "New", "https://x/4.mp3")]

    monkeypatch.setattr(discover, "fetch_feed", flaky)
    result = discover.run(config, conn)
    assert result["feed_errors"] == 1 and result["episodes_new"] == 1
    assert conn.execute("SELECT status FROM podcasts WHERE title='Show One'").fetchone()[0] == "error"
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 4


def test_download_records_results_and_errors(seeded, monkeypatch):
    config, conn = seeded
    outcomes = {"https://x/1.mp3": DownloadResult(Path("/audio/1.ogg"), 100.0, 20.0, True),
                "https://x/2.mp3": DownloadError("HTTP 404")}

    class FakeDownloader:
        def __init__(self, *a, **kw):
            pass

        def download_episode(self, url, podcast_title, episode_title, guid):
            outcome = outcomes[url]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(download, "AudioDownloader", FakeDownloader)
    result = download.run(config, conn, workers=2)
    assert result == {"total": 2, "downloaded": 1, "reused": 0, "failed": 1, "not_attempted": 0}

    rows = {r["episode_guid"]: r for r in conn.execute("SELECT * FROM episodes")}
    assert rows["g1"]["status"] == "downloaded" and rows["g1"]["audio_file_path"] == "/audio/1.ogg"
    assert rows["g2"]["status"] == "error" and rows["g2"]["error_message"] == "HTTP 404"
    assert rows["g3"]["status"] == "pending"   # publisher transcript: never downloaded

    # A second pass retries the failure only.
    outcomes["https://x/2.mp3"] = DownloadResult(Path("/audio/2.mp3"), 10.0, 10.0, False)
    assert download.run(config, conn)["downloaded"] == 1
    assert download.run(config, conn)["total"] == 0


def test_rss_transcripts(seeded, monkeypatch):
    config, conn = seeded
    segments = [Segment("Alice: hello " * 20, 0, 5), Segment("Bob: hi " * 20, 5, 9.5)]
    monkeypatch.setattr(rss_transcripts, "fetch_one",
                        lambda session, url, timeout, min_words: FetchedTranscript(segments, "srt/vtt"))
    result = rss_transcripts.run(config, conn)
    assert result["saved"] == 1

    row = conn.execute("SELECT e.status, t.has_speakers, t.duration_seconds, t.metadata "
                       "FROM episodes e JOIN transcripts t ON t.episode_id = e.id").fetchone()
    assert row[0] == "transcribed" and row[1] == 1 and row[2] == 9.5 and '"source": "rss"' in row[3]
    assert TranscriptStore(config.transcript_dir).load(Path(conn.execute(
        "SELECT transcript_file_path FROM episodes WHERE status='transcribed'").fetchone()[0])).segments[1].text.startswith("Bob")

    monkeypatch.setattr(rss_transcripts, "fetch_one",
                        lambda *a: (_ for _ in ()).throw(RssTranscriptError("too_short", "3 words")))
    assert rss_transcripts.run(config, conn)["total"] == 0   # already done


def test_transcribe_with_fake_model(seeded, monkeypatch):
    config, conn = seeded
    audio = config.audio_dir / "show-one" / "ep-one.mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(REAL_AUDIO)
    ids = {r[0]: r[1] for r in conn.execute("SELECT episode_guid, id FROM episodes")}
    db.record_download(conn, ids["g1"], audio, 1.0, 1.0, False)
    db.record_download(conn, ids["g2"], Path("/missing.mp3"), 1.0, 1.0, False)
    conn.commit()

    class FakeResult:
        segments = [Segment("Hello world.", 0.0, 1.0), Segment("Bye.", 1.0, 2.0)]
        duration_seconds = 2.0
        chunk_count = 1
        transcription_seconds = 0.1
        rtf = 0.05

    class FakeTranscriber:
        def __init__(self, cfg, gpu_id):
            self.gpu_id = gpu_id

        def transcribe_file(self, path):
            assert path == audio
            return FakeResult()

    fake_module = types.ModuleType("podcast_pipeline.asr.parakeet")
    fake_module.ParakeetTranscriber = FakeTranscriber
    fake_module.TranscriptionError = RuntimeError
    monkeypatch.setitem(sys.modules, "podcast_pipeline.asr.parakeet", fake_module)
    config.transcription.gpu_ids = [0, 1]

    result = transcribe.run(config, conn)
    assert result == {"total": 2, "transcribed": 1, "failed": 0, "missing_audio": 1}
    row = conn.execute("SELECT status, transcript_file_path FROM episodes WHERE id = ?", (ids["g1"],)).fetchone()
    assert row[0] == "transcribed"
    loaded = TranscriptStore(config.transcript_dir).load(Path(row[1]))
    assert loaded.text == "Hello world. Bye." and loaded.metadata["source"] == "asr"
    assert conn.execute("SELECT status FROM episodes WHERE id = ?", (ids["g2"],)).fetchone()[0] == "error"

    # reset-transcripts puts it back for another pass; RSS transcripts are untouched.
    assert reset_transcripts.run(config, conn, everything=True)["reset"] == 1
    assert not Path(row[1]).exists()
    assert conn.execute("SELECT status FROM episodes WHERE id = ?", (ids["g1"],)).fetchone()[0] == "downloaded"


def test_convert_audio_commits_before_deleting(seeded, monkeypatch):
    config, conn = seeded
    big = config.audio_dir / "show-one" / "ep-one.mp3"
    big.parent.mkdir(parents=True)
    big.write_bytes(REAL_AUDIO)
    ids = {r[0]: r[1] for r in conn.execute("SELECT episode_guid, id FROM episodes")}
    db.record_download(conn, ids["g1"], big, 5.0, 5.0, False)
    conn.commit()

    def fake_encode(source, target, bitrate):
        target.write_bytes(b"o" * 2000)

    monkeypatch.setattr(convert_audio, "encode_opus", fake_encode)
    monkeypatch.setattr(convert_audio, "ensure_free_space", lambda path, floor: None)

    assert convert_audio.run(config, conn, threshold_mb=0, dry_run=True)["total"] == 1
    assert big.exists()

    result = convert_audio.run(config, conn, threshold_mb=0)
    assert result["converted"] == 1 and result["failed"] == 0
    assert not big.exists() and big.with_suffix(".ogg").exists()
    row = conn.execute("SELECT audio_file_path, is_compressed FROM episodes WHERE id = ?", (ids["g1"],)).fetchone()
    assert row[0] == str(big.with_suffix(".ogg")) and row[1] == 1
    assert convert_audio.run(config, conn, threshold_mb=0)["total"] == 0

    # An encode failure leaves the source alone.
    db.record_conversion(conn, ids["g1"], big, 5.0, 5.0)
    conn.execute("UPDATE episodes SET is_compressed = 0 WHERE id = ?", (ids["g1"],))
    conn.commit()
    big.write_bytes(REAL_AUDIO)
    big.with_suffix(".ogg").unlink()
    monkeypatch.setattr(convert_audio, "encode_opus", lambda *a, **k: (_ for _ in ()).throw(EncodeError("bad")))
    assert convert_audio.run(config, conn, threshold_mb=0)["failed"] == 1
    assert big.exists()


def test_audit_and_fix(seeded, monkeypatch):
    config, conn = seeded
    present = config.audio_dir / "show-one" / "present.mp3"
    present.parent.mkdir(parents=True)
    present.write_bytes(REAL_AUDIO)
    (config.audio_dir / "show-one" / "orphan.mp3").write_bytes(REAL_AUDIO)
    ids = {r[0]: r[1] for r in conn.execute("SELECT episode_guid, id FROM episodes")}
    db.record_download(conn, ids["g1"], present, 1.0, 1.0, False)
    db.record_download(conn, ids["g2"], Path("/gone.mp3"), 1.0, 1.0, False)
    conn.commit()

    result = audit.run(config, conn, skip_probe=True, report=config.data_path / "report.json")
    assert result["missing"] == 1 and result["orphan"] == 1 and result["shared_path"] == 0
    assert (config.data_path / "report.json").exists()

    result = audit.run(config, conn, fix=True, skip_probe=True)
    assert result["reset"] == 1
    assert tuple(conn.execute("SELECT status, audio_file_path FROM episodes WHERE id = ?",
                              (ids["g2"],)).fetchone()) == ("pending", None)


def test_stats(seeded):
    config, conn = seeded
    result = stats.run(config, conn)
    assert result["episodes"] == {"pending": 3}
    assert result["episodes_with_rss_transcript"] == 1
    assert result["transcripts"]["total"] == 0


def test_download_charts_filter_restricts_to_that_chart(seeded, monkeypatch):
    """The queue takes days, so a chart is prioritised by downloading it first."""
    config, conn = seeded
    one = conn.execute("SELECT id FROM podcasts WHERE title='Show One'").fetchone()["id"]
    conn.execute("INSERT INTO podcast_charts (podcast_id, chart, rank) VALUES (?, 'health', 1)", (one,))
    conn.commit()

    all_pending = download.pending_episodes(conn, retry_errors=True, limit=None)
    health_only = download.pending_episodes(conn, retry_errors=True, limit=None, charts=["health"])

    assert {r["title"] for r in all_pending} == {"Ep One", "Ep Two"}
    assert {r["title"] for r in health_only} == {"Ep One", "Ep Two"}

    two = conn.execute("SELECT id FROM podcasts WHERE title='Show Two'").fetchone()["id"]
    conn.execute("UPDATE episodes SET has_rss_transcript = 0 WHERE podcast_id = ?", (two,))
    conn.commit()
    assert len(download.pending_episodes(conn, retry_errors=True, limit=None)) == 3
    assert len(download.pending_episodes(conn, retry_errors=True, limit=None, charts=["health"])) == 2
    assert download.pending_episodes(conn, retry_errors=True, limit=None, charts=["absent"]) == []
