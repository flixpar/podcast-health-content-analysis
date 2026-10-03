import json

import pytest

from podcast_pipeline import db
from podcast_pipeline.models import FeedEpisode, PodcastRecord
from podcast_pipeline.pipeline import import_episodes
from podcast_pipeline.pipeline.import_episodes import ImportFileError, generated_guid


def add_podcast(conn, n: int) -> int:
    return db.upsert_podcast(conn, PodcastRecord(source_id=f"apple_{n}", title=f"Show {n}",
                                                 rss_url=f"https://feeds.example/{n}"))


def add_episode(conn, podcast_id, guid, title, date, url, **state) -> int:
    db.insert_episode(conn, podcast_id, FeedEpisode(guid=guid, title=title, audio_url=url,
                                                    published_date=date))
    episode_id = conn.execute("SELECT id FROM episodes WHERE episode_guid = ?", (guid,)).fetchone()[0]
    if state:
        sets = ", ".join(f"{k} = ?" for k in state)
        conn.execute(f"UPDATE episodes SET {sets} WHERE id = ?", (*state.values(), episode_id))
    return episode_id


def write_jsonl(path, rows) -> object:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def episode(conn, episode_id):
    return conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()


def sources(conn, episode_id):
    return sorted((r["source"], r["ref"]) for r in conn.execute(
        "SELECT source, ref FROM episode_sources WHERE episode_id = ?", (episode_id,)))


@pytest.fixture
def show(conn):
    pid = add_podcast(conn, 1)
    eps = {
        "failed": add_episode(conn, pid, "g-failed", "#600: Failed One", "2018-03-04T23:00:00",
                              "https://dead.host/600.mp3", status="error",
                              error_message="SSL hostname mismatch"),
        "done": add_episode(conn, pid, "g-done", "601: Has Audio", "2018-03-11T23:00:00",
                            "https://dead.host/601.mp3", status="downloaded",
                            audio_file_path="/a/601.ogg"),
        "pending": add_episode(conn, pid, "g-pending", "602: Pending", "2018-03-18T23:00:00",
                               "https://dead.host/602.mp3"),
        "transcribed_error": add_episode(conn, pid, "g-tx", "603: Transcribed", "2018-03-25T23:00:00",
                                         "https://dead.host/603.mp3", status="error",
                                         transcript_file_path="/t/603.jsonl.zst"),
    }
    conn.commit()
    return pid, eps


def test_failed_episode_matched_by_day_and_title_gets_the_new_url(config, conn, tmp_path, show):
    pid, eps = show
    path = write_jsonl(tmp_path / "in.jsonl", [{
        "title": "600: Failed one!", "published_date": "2018-03-04T18:00:00-05:00",
        "audio_url": "https://good.host/600.mp3", "evidence": {"page": "https://site/600"},
    }])
    out = import_episodes.run(config, conn, path, "publisher_site", podcast_id=pid)
    assert (out["inserted"], out["updated"], out["provenance_only"], out["rejected"]) == (0, 1, 0, 0)
    ep = episode(conn, eps["failed"])
    assert ep["audio_url"] == "https://good.host/600.mp3"
    assert ep["status"] == "pending" and ep["error_message"] is None
    assert sources(conn, eps["failed"]) == [("previous_audio_url", "https://dead.host/600.mp3"),
                                            ("publisher_site", "https://good.host/600.mp3")]
    imported = json.loads(ep["metadata"])["imported"]
    assert imported[0]["evidence"] == {"page": "https://site/600"}


def test_episodes_with_work_are_never_modified(config, conn, tmp_path, show):
    pid, eps = show
    path = write_jsonl(tmp_path / "in.jsonl", [
        {"title": "601: Has Audio", "published_date": "2018-03-11", "audio_url": "https://good/601"},
        {"title": "x", "published_date": "2018-01-01", "audio_url": "https://good/603",
         "replaces_episode_id": eps["transcribed_error"]},
    ])
    before = {k: dict(episode(conn, v)) for k, v in eps.items()}
    out = import_episodes.run(config, conn, path, "publisher_site", podcast_id=pid)
    assert (out["updated"], out["provenance_only"]) == (0, 2)
    for key in ("done", "transcribed_error"):
        after = dict(episode(conn, eps[key]))
        assert {k: v for k, v in after.items() if k != "metadata"} == \
               {k: v for k, v in before[key].items() if k != "metadata"}
    assert sources(conn, eps["done"]) == [("publisher_site", "https://good/601")]


def test_pending_is_replaced_only_when_named(config, conn, tmp_path, show):
    pid, eps = show
    by_title = write_jsonl(tmp_path / "a.jsonl", [
        {"title": "602: Pending", "published_date": "2018-03-18", "audio_url": "https://good/602"}])
    out = import_episodes.run(config, conn, by_title, "alt_host", podcast_id=pid)
    assert (out["updated"], out["provenance_only"]) == (0, 1)
    assert episode(conn, eps["pending"])["audio_url"] == "https://dead.host/602.mp3"

    named = write_jsonl(tmp_path / "b.jsonl", [
        {"title": "602: Pending", "published_date": "2018-03-18", "audio_url": "https://good/602",
         "replaces_episode_id": eps["pending"]}])
    out = import_episodes.run(config, conn, named, "alt_host", podcast_id=pid)
    assert out["updated"] == 1
    assert episode(conn, eps["pending"])["audio_url"] == "https://good/602"


def test_unmatched_rows_are_inserted_with_a_stable_guid(config, conn, tmp_path, show):
    pid, _ = show
    row = {"title": "590: New Old One", "published_date": "2016-05-01T00:00:00Z",
           "audio_url": "https://good/590.mp3", "duration_seconds": 3540.4}
    path = write_jsonl(tmp_path / "in.jsonl", [row])
    out = import_episodes.run(config, conn, path, "publisher_site", podcast_id=pid)
    assert out["inserted"] == 1
    guid = generated_guid("publisher_site", pid, "2016-05-01T00:00:00", "590: New Old One")
    ep = conn.execute("SELECT * FROM episodes WHERE episode_guid = ?", (guid,)).fetchone()
    assert ep["published_date"] == "2016-05-01T00:00:00" and ep["duration_seconds"] == 3540
    assert ep["status"] == "pending"
    assert sources(conn, ep["id"]) == [("publisher_site", "https://good/590.mp3")]

    # A re-import finds the same episode by its generated guid.
    out = import_episodes.run(config, conn, path, "publisher_site", podcast_id=pid)
    assert (out["inserted"], out["provenance_only"]) == (0, 1)


def test_rejections_and_dry_run(config, conn, tmp_path, show):
    pid, eps = show
    other = add_podcast(conn, 2)
    foreign = add_episode(conn, other, "g-foreign", "Elsewhere", "2018-01-01T00:00:00", "https://x/1")
    conn.commit()
    good = {"title": "New", "published_date": "2019-01-01", "audio_url": "https://good/new"}
    path = write_jsonl(tmp_path / "in.jsonl", [
        good,
        dict(good),                                                    # duplicate in file
        {"title": "Old", "published_date": "1980-01-01", "audio_url": "https://good/old"},
        {"title": "No URL", "published_date": "2019-01-01"},
        {**good, "title": "Ghost", "podcast_id": 999},
        {**good, "title": "Foreign", "replaces_episode_id": foreign},
        {**good, "title": "Stolen", "guid": "g-foreign"},
        {**good, "title": "Typo", "replace_episode_id": eps["failed"]},
        {"title": "600: Failed One", "published_date": "2018-03-04", "audio_url": "https://good/600"},
    ])
    total_before = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    out = import_episodes.run(config, conn, path, "publisher_site", podcast_id=pid, dry_run=True)
    assert (out["inserted"], out["updated"], out["rejected"]) == (1, 1, 7)
    reasons = [r["reason"] for r in out["rejected_rows"]]
    assert reasons[0] == "same episode as line 1"
    assert any("implausible" in r for r in reasons) and any("missing audio_url" in r for r in reasons)
    assert any("does not exist" in r for r in reasons)
    assert any(f"belongs to podcast {other}" in r for r in reasons)
    assert any("unknown fields" in r for r in reasons)
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == total_before
    assert episode(conn, eps["failed"])["status"] == "error"
    assert conn.execute("SELECT COUNT(*) FROM episode_sources WHERE source = 'publisher_site'"
                        ).fetchone()[0] == 0


def test_a_malformed_file_fails_loudly(config, conn, tmp_path, show):
    pid, _ = show
    path = tmp_path / "bad.jsonl"
    path.write_text('{"title": "ok"}\nnot json\n')
    with pytest.raises(ImportFileError):
        import_episodes.run(config, conn, path, "publisher_site", podcast_id=pid)
    with pytest.raises(ValueError):
        import_episodes.run(config, conn, path, "previous_audio_url", podcast_id=pid)


# --- tools/tal_archive.py (the first producer of import-episodes JSONL) ----------

def _tal():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import tal_archive
    return tal_archive


def test_tal_page_parsing_and_numbers():
    tal = _tal()
    page = ('<div class="field field-name-field-radio-air-date"><div><span  class="date-display-single">'
            'October 7, 2016</span></div></div><link rel="canonical" href="https://site/598/x" />'
            '<script id="playlist-data" type="application/json">{"audio": "https://site/a/598.mp3", '
            '"episode": "598", "title": "598: My Undesirable Talent ", "guid": "37075 at x"}</script>')
    assert tal.parse_page(page) == {
        "audio": "https://site/a/598.mp3", "number": 598, "title": "598: My Undesirable Talent",
        "site_guid": "37075 at x", "original_air_date": "2016-10-07", "canonical": "https://site/598/x"}
    assert tal.episode_number("#581: Anatomy of Doubt") == 581
    assert tal.episode_number("Bonus: Nancy's Deep Cuts") is None
    assert tal.page_urls("http://feed.x/~r/talpodcast/~3/GDa/didn%E2%80%99t-x", 607) == [
        "https://www.thisamericanlife.org/607/didn%E2%80%99t-x",
        "https://www.thisamericanlife.org/607/didnt-x",
        "https://www.thisamericanlife.org/607/didnt-x-part-one"]


def test_tal_coverage_reports_what_no_capture_reaches():
    tal = _tal()
    spans = [("2016-02-08", "2016-03-01"), ("2016-03-07", "2016-03-20")]
    assert tal.uncovered("2016-02-01", "2016-04-01", spans) == [
        ("2016-02-01", "2016-02-08"), ("2016-03-02", "2016-03-07"), ("2016-03-21", "2016-04-01")]
    assert tal.uncovered("2016-03-01", "2016-03-15", [("2016-02-20", "2016-03-30")]) == []


def test_a_local_publisher_date_matches_the_feeds_utc_next_day(config, conn, tmp_path, show):
    pid, eps = show
    # the feed has 2018-03-04T23:00 UTC; the publisher's page says "March 3" (US evening)
    path = write_jsonl(tmp_path / "in.jsonl", [{
        "title": "600: Failed One", "published_date": "2018-03-03",
        "audio_url": "https://good.host/600.mp3",
    }])
    out = import_episodes.run(config, conn, path, "publisher_site", podcast_id=pid)
    assert (out["inserted"], out["updated"]) == (0, 1)
    assert episode(conn, eps["failed"])["audio_url"] == "https://good.host/600.mp3"
