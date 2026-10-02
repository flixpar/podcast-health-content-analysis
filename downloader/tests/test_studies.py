import json

import pytest

from podcast_pipeline import db
from podcast_pipeline.models import FeedEpisode, PodcastRecord
from podcast_pipeline.pipeline import discover, download
from podcast_pipeline.studies import apple_top24_monthly as top24
from podcast_pipeline.studies.base import Member, Study, Window
from podcast_pipeline.studies.corpus_2025 import Corpus2025
from podcast_pipeline.studies.export import export
from podcast_pipeline.studies.gaps import study_gaps
from podcast_pipeline.studies.materialize import refresh
from podcast_pipeline.studies.scope import StudyError, episode_filter
from podcast_pipeline.studies.status import status


def add_podcast(conn, n, apple_id=None, rss=True):
    return db.upsert_podcast(conn, PodcastRecord(
        source_id=f"apple_{apple_id or n}", title=f"Show {n}",
        apple_podcasts_id=str(apple_id or n), rss_url=f"https://feeds.example/{n}" if rss else None))


def add_episode(conn, podcast_id, guid, date, title=None, transcript=False, audio=False):
    db.insert_episode(conn, podcast_id, FeedEpisode(
        guid=guid, title=title or guid, audio_url=f"https://a.example/{guid}.mp3",
        published_date=date))
    eid = conn.execute("SELECT id FROM episodes WHERE episode_guid = ?", (guid,)).fetchone()[0]
    if audio or transcript:
        conn.execute("UPDATE episodes SET audio_file_path = ?, status = 'downloaded' WHERE id = ?",
                     (f"/audio/{guid}.ogg", eid))
    if transcript:
        db.record_transcript(conn, eid, f"/t/episode_{eid}.jsonl.zst", 10, 60.0, True, False,
                             {"source": "asr"})
    return eid


class FixedStudy(Study):
    name = "fixed"
    description = "test"
    version = 1

    def __init__(self, members, cap=None):
        self._members = members
        self.max_per_window = cap

    def select(self, conn):
        return self._members


def episodes_of(conn, study):
    return {r["episode_id"]: dict(r) for r in conn.execute(
        "SELECT * FROM study_episodes WHERE study = ?", (study,))}


def test_windows_select_by_date_and_round_robin_priority(conn):
    p = add_podcast(conn, 1)
    a1 = add_episode(conn, p, "a1", "2017-03-02T10:00:00")
    a2 = add_episode(conn, p, "a2", "2017-03-20T10:00:00")
    b1 = add_episode(conn, p, "b1", "2017-05-01T00:00:00")
    add_episode(conn, p, "out", "2017-04-15T00:00:00")
    add_episode(conn, p, "epoch", "1970-01-01T00:30:00")
    conn.commit()
    study = FixedStudy([Member("apple:1", "Show 1", [Window("2017-03", "2017-03-01", "2017-04-01"),
                                                      Window("2017-05", "2017-05-01", "2017-06-01")])])
    summary = refresh(conn, study)
    eps = episodes_of(conn, "fixed")
    assert set(eps) == {a1, a2, b1}
    assert (eps[a1]["priority"], eps[a2]["priority"], eps[b1]["priority"]) == (0, 1, 0)
    assert eps[a1]["window_label"] == "2017-03"
    assert summary["excluded"]["undated"] == 1


def test_duplicates_keep_the_copy_with_work_done(conn):
    p = add_podcast(conn, 1)
    add_episode(conn, p, "first", "2020-01-01T00:00:00", title="Same")
    done = add_episode(conn, p, "second", "2020-01-01T00:00:00", title="Same", transcript=True)
    conn.commit()
    summary = refresh(conn, FixedStudy([Member("podcast:%d" % p)]))
    assert set(episodes_of(conn, "fixed")) == {done}
    assert summary["excluded"]["duplicate"] == 1


def test_window_cap_prefers_transcribed_then_spreads(conn):
    p = add_podcast(conn, 1)
    ids = [add_episode(conn, p, f"e{d}", f"2018-01-{d:02d}T00:00:00", transcript=(d == 30))
           for d in range(1, 31)]
    conn.commit()
    refresh(conn, FixedStudy([Member("apple:1", None, [Window("2018-01", "2018-01-01", "2018-02-01")])],
                             cap=3))
    chosen = set(episodes_of(conn, "fixed"))
    assert len(chosen) == 3 and ids[29] in chosen


def test_revision_only_moves_when_membership_changes(conn):
    p = add_podcast(conn, 1)
    first = add_episode(conn, p, "x", "2020-01-01T00:00:00")
    conn.commit()
    study = FixedStudy([Member(f"podcast:{p}")])
    assert refresh(conn, study)["revision"] == 1
    assert refresh(conn, study)["revision"] == 1
    second = add_episode(conn, p, "y", "2020-02-01T00:00:00")
    conn.commit()
    summary = refresh(conn, study)
    assert summary["revision"] == 2 and summary["episodes_added"] == 1
    eps = episodes_of(conn, "fixed")
    assert eps[first]["added_revision"] == 1 and eps[second]["added_revision"] == 2
    assert conn.execute("SELECT COUNT(*) FROM study_revisions").fetchone()[0] == 2


def test_unresolved_members_are_kept_without_episodes(conn):
    refresh(conn, FixedStudy([Member("title:someshow", "Some Show", [Window("2019-01", "2019-01-01", "2019-02-01")])]))
    row = conn.execute("SELECT podcast_id, scope FROM study_members").fetchone()
    assert row["podcast_id"] is None and row["scope"] == "windows"
    db.link_entity(conn, "title:someshow", add_podcast(conn, 7), "manual")
    add_episode(conn, 1, "z", "2019-01-05T00:00:00")
    conn.commit()
    assert refresh(conn, FixedStudy([Member("title:someshow", "Some Show",
                                            [Window("2019-01", "2019-01-01", "2019-02-01")])]))["episodes"] == 1


def test_two_entities_for_one_podcast_share_its_episodes_once(conn):
    p = add_podcast(conn, 5)
    e = add_episode(conn, p, "e", "2019-01-05T00:00:00")
    db.link_entity(conn, "title:showfive", p, "manual")
    conn.commit()
    w = [Window("2019-01", "2019-01-01", "2019-02-01")]
    summary = refresh(conn, FixedStudy([Member("apple:5", None, w), Member("title:showfive", None, w)]))
    assert summary["members_merged"] == 2 and list(episodes_of(conn, "fixed")) == [e]


def test_stage_filters(conn, config):
    p1, p2 = add_podcast(conn, 1), add_podcast(conn, 2)
    e1 = add_episode(conn, p1, "one", "2020-01-01T00:00:00")
    add_episode(conn, p2, "two", "2020-01-01T00:00:00")
    conn.commit()
    with pytest.raises(StudyError):
        episode_filter(conn, "fixed")
    refresh(conn, FixedStudy([Member(f"podcast:{p1}")]))
    assert [r["id"] for r in download.pending_episodes(conn, True, None, study="fixed")] == [e1]
    assert [r["id"] for r in download.pending_episodes(conn, True, None, all_episodes=False)] == [e1]
    assert len(download.pending_episodes(conn, True, None)) == 2


def test_discover_defaults_to_study_podcasts(conn, config, monkeypatch):
    p1, _ = add_podcast(conn, 1), add_podcast(conn, 2)
    conn.commit()
    refresh(conn, FixedStudy([Member(f"podcast:{p1}")]))
    read = []
    monkeypatch.setattr(discover, "fetch_feed", lambda url, *a: read.append(url) or [
        FeedEpisode(guid=f"{url}#1", title="t", audio_url="https://a/1.mp3",
                    published_date="2026-01-01T00:00:00")])
    discover.run(config, conn)
    assert read == ["https://feeds.example/1"]
    feed = conn.execute("SELECT item_count, oldest_item FROM podcast_feeds WHERE podcast_id = ?",
                        (p1,)).fetchone()
    assert feed["item_count"] == 1 and feed["oldest_item"].startswith("2026")
    assert conn.execute("SELECT source FROM episode_sources").fetchone()[0] == "feed"
    discover.run(config, conn, all_podcasts=True)
    assert len(read) == 3


def test_corpus_study_freezes_podcasts_by_first_seen(conn):
    old, new = add_podcast(conn, 1), add_podcast(conn, 2)
    db.record_chart_entry(conn, old, "apple_us_top", 1)
    db.record_chart_entry(conn, new, "apple_us_top", 2)
    conn.execute("UPDATE podcast_charts SET first_seen_at = '2025-10-13 10:00:00' WHERE podcast_id = ?", (old,))
    conn.execute("UPDATE podcast_charts SET first_seen_at = '2026-11-01 10:00:00' WHERE podcast_id = ?", (new,))
    conn.commit()
    assert [m.entity for m in Corpus2025().select(conn)] == [f"podcast:{old}"]


def test_status_gaps_and_export(conn, config, tmp_path):
    p = add_podcast(conn, 1)
    done = add_episode(conn, p, "done", "2017-03-05T00:00:00", transcript=True)
    add_episode(conn, p, "todo", "2017-03-09T00:00:00")
    conn.commit()
    windows = [Window("2017-03", "2017-03-01", "2017-04-01", {"snapshots_in_month": 2}),
               Window("2017-02", "2017-02-01", "2017-03-01", {"snapshots_in_month": 0})]
    refresh(conn, FixedStudy([Member("apple:1", "Show 1", windows)]))
    gaps = study_gaps(conn, "fixed")
    # February is empty; March is partial: the feed's oldest episode is after it opens
    assert [w[0] for w in gaps[0].windows] == ["2017-02", "2017-03"]
    assert gaps[0].empty == {"2017-02"}
    s = status(config, conn, "fixed")
    assert s["episodes"]["transcribed_asr"] == 1 and s["episodes"]["awaiting_download"] == 1
    assert s["windows"]["total"] == 2 and s["windows"]["with_episodes"] == 1
    assert s["windows"]["imputed_from_neighbouring_snapshots"] == 1
    assert any(step.startswith("discover-archived") for step in s["next_steps"])

    transcript = tmp_path / f"episode_{done}.jsonl.zst"
    transcript.write_bytes(b"x")
    conn.execute("UPDATE transcripts SET file_path = ? WHERE episode_id = ?", (str(transcript), done))
    conn.commit()
    links = tmp_path / "links"
    result = export(config, conn, "fixed", output=tmp_path / "m" / "episodes.csv", link_transcripts=links)
    assert result["episodes"] == 2 and result["linked"] == 1
    assert (links / transcript.name).resolve() == transcript.resolve()
    meta = json.loads((tmp_path / "m" / "study.json").read_text())
    assert meta["revision"] == 1 and len(meta["windows"]) == 2


# --- the monthly top-24 study ------------------------------------------------

def add_snapshot(conn, source, day, entries, chart=top24.CHART, trusted=1):
    cur = conn.execute("""
        INSERT INTO chart_snapshots (source, chart, captured_on, origin, depth, n_entries,
                                     complete_to, trusted)
        VALUES (?, ?, ?, 'wayback', ?, ?, ?, ?)
    """, (source, chart, day, len(entries), len(entries), len(entries), trusted))
    conn.executemany("""
        INSERT INTO chart_entries (snapshot_id, rank, name, title_key, apple_id) VALUES (?, ?, ?, ?, ?)
    """, [(cur.lastrowid, rank, name, name.lower().replace(" ", ""), apple)
          for rank, (name, apple) in enumerate(entries, start=1)])


def chart(prefix, n=24, ids=True):
    return [(f"{prefix} {i}", f"{prefix}{i}" if ids else None) for i in range(n)]


def test_top24_month_lists_weight_by_time_not_snapshot_count(conn, monkeypatch):
    monkeypatch.setattr(top24, "START_MONTH", "2017-01")
    # January: one snapshot early in the month with list A.
    # February: list B on the 1st, then list C on 26 later days. C held the
    # month; a union of snapshots would also admit B.
    add_snapshot(conn, "podbay", "2017-01-03", chart("A"))
    add_snapshot(conn, "podbay", "2017-02-01", chart("B"))
    for d in range(3, 29):
        add_snapshot(conn, "podbay", f"2017-02-{d:02d}", chart("C"))
    add_snapshot(conn, "podbay", "2017-04-02", chart("C"))   # March has no snapshot
    days = top24.snapshot_days(conn)
    obs = top24._observations(conn, days, top24.entity_resolver(conn))
    lists = top24.monthly_lists(days, obs)
    assert list(lists) == ["2017-01", "2017-02", "2017-03"]   # April not fully covered
    assert all(len(v) == 24 for v in lists.values())
    assert {e["entity"] for e in lists["2017-02"]} == {f"apple:C{i}" for i in range(24)}
    assert lists["2017-03"][0]["snapshots_in_month"] == 0
    assert lists["2017-02"][0]["monthly_rank"] == 1 and lists["2017-02"][0]["entity"] == "apple:C0"


def test_top24_sources_identity_and_trust(conn, monkeypatch):
    monkeypatch.setattr(top24, "START_MONTH", "2020-01")
    # a podbay day carries the id for "Renamed Show"; chartable carries only titles
    add_snapshot(conn, "podbay", "2019-12-01", [("Renamed Show", "777")] + chart("P", 23))
    add_snapshot(conn, "chartable_itunes", "2020-01-10",
                 [("Renamed Show", None), ("No Id Show", None)] + chart("Q", 22, ids=False))
    # distrusted and itunes_rss snapshots are ignored even on otherwise empty days
    add_snapshot(conn, "chartable_itunes", "2020-01-20", chart("BAD"), trusted=0)
    add_snapshot(conn, "itunes_rss", "2020-01-25", chart("RSS"))
    add_snapshot(conn, "chartable_itunes", "2020-02-15", chart("Q", ids=False))
    # where two sources cover a day, the first-party page wins
    add_snapshot(conn, "apple_charts_page", "2020-02-15", chart("APPLE"))
    entities = {m.entity for m in top24.AppleTop24Monthly().select(conn)}
    assert "apple:777" in entities and "title:noidshow" in entities
    assert not any("BAD" in e or "RSS" in e for e in entities)
    days = dict((d, s) for d, _, s in top24.snapshot_days(conn))
    assert days["2020-02-15"] == "apple_charts_page"


def test_top24_uses_entity_links_for_titles(conn, monkeypatch):
    monkeypatch.setattr(top24, "START_MONTH", "2020-01")
    p = add_podcast(conn, 1, apple_id="555")
    db.link_entity(conn, "title:noidshow", p, "itunes_search")
    add_snapshot(conn, "chartable_itunes", "2020-01-10", [("No Id Show", None)] + chart("Q", 23, ids=False))
    add_snapshot(conn, "chartable_itunes", "2020-02-10", [("No Id Show", None)] + chart("Q", 23, ids=False))
    entities = {m.entity for m in top24.AppleTop24Monthly().select(conn)}
    assert "apple:555" in entities and "title:noidshow" not in entities
