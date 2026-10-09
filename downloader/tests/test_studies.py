import json
from collections import Counter

import pytest

from podcast_pipeline import db
from podcast_pipeline.models import FeedEpisode, PodcastRecord
from podcast_pipeline.pipeline import discover, download
from podcast_pipeline.rss import FeedRead
from podcast_pipeline.studies import apple_chart_monthly as monthly
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
                     (f"audio/show/{guid}.ogg", eid))
    if transcript:
        db.record_transcript(conn, eid, f"transcripts/episode_{eid}.jsonl.zst", 10, 60.0, True, False,
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


@pytest.mark.parametrize("change", ["add_member", "remove_member", "name", "member_attrs",
                                   "scope", "window_dates", "window_attrs", "add_window",
                                   "remove_window", "resolve"])
def test_member_or_empty_window_changes_bump_revision(conn, config, change):
    member = Member("title:show", "Show", [Window("2020-01", "2020-01-01", "2020-02-01")],
                    {"publisher": "Publisher"})
    study = FixedStudy([member])
    assert refresh(conn, study)["revision"] == 1
    first = export(config, conn, study.name)
    first_metadata = (config.study_export_dir / study.name / "rev1" / "study.json").read_bytes()
    if change == "add_member":
        study._members.append(Member("title:other", "Other"))
    elif change == "remove_member":
        study._members.clear()
    elif change == "name":
        member.name = "New name"
    elif change == "member_attrs":
        member.attrs["publisher"] = "New publisher"
    elif change == "scope":
        member.windows = None
    elif change == "window_dates":
        member.windows = [Window("2020-01", "2020-01-02", "2020-02-01")]
    elif change == "window_attrs":
        member.windows = [Window("2020-01", "2020-01-01", "2020-02-01", {"provisional": True})]
    elif change == "add_window":
        member.windows.append(Window("2020-02", "2020-02-01", "2020-03-01"))
    elif change == "remove_window":
        member.windows.clear()
    elif change == "resolve":
        db.link_entity(conn, member.entity, add_podcast(conn, 7), "manual")
        conn.commit()
    summary = refresh(conn, study)
    assert summary["revision"] == 2 and summary["episodes"] == 0
    assert summary["episodes_added"] == summary["episodes_removed"] == 0
    second = export(config, conn, study.name)
    assert first["manifest"] != second["manifest"]
    assert (config.study_export_dir / study.name / "rev1" / "study.json").read_bytes() == first_metadata
    assert refresh(conn, study)["revision"] == 2
    assert conn.execute("SELECT COUNT(*) FROM study_revisions").fetchone()[0] == 2


def test_member_order_and_json_key_order_do_not_bump_revision(conn):
    study = FixedStudy([Member("title:a", attrs={"x": 1, "y": 2}), Member("title:b")])
    assert refresh(conn, study)["revision"] == 1
    study._members.reverse()
    study._members[1].attrs = {"y": 2, "x": 1}
    assert refresh(conn, study)["revision"] == 1


@pytest.mark.parametrize("duration", [None, 0, -1])
def test_storage_estimates_unknown_durations_without_double_counting(conn, config, duration):
    p = add_podcast(conn, 1)
    measured = add_episode(conn, p, "measured", "2020-01-01T00:00:00", audio=True)
    known = add_episode(conn, p, "known", "2020-01-02T00:00:00")
    unknown = add_episode(conn, p, "unknown", "2020-01-03T00:00:00")
    conn.execute("UPDATE episodes SET duration_seconds = 3600, compressed_file_size_mb = 1024 WHERE id = ?", (measured,))
    conn.execute("UPDATE episodes SET duration_seconds = 7200 WHERE id = ?", (known,))
    conn.execute("UPDATE episodes SET duration_seconds = ? WHERE id = ?", (duration, unknown))
    conn.commit()
    refresh(conn, FixedStudy([Member(f"podcast:{p}")]))
    s = status(config, conn, "fixed")
    assert s["storage"]["pending_download_episodes"] == 2
    # Two known pending hours plus one unknown at the catalog mean (1.5 hours).
    assert s["storage"]["pending_download_gb_estimate"] == 3.5
    assert s["hours"]["awaiting_download"] == 2.0


def test_storage_uses_configured_fallback_and_warns_when_all_durations_unknown(conn, config, monkeypatch):
    import shutil
    import importlib
    status_module = importlib.import_module("podcast_pipeline.studies.status")
    monkeypatch.setattr(status_module.shutil, "disk_usage", lambda path:
                        shutil._ntuple_diskusage(1024 ** 4, 0, 101 * 1024 ** 3))
    config.storage.estimated_episode_duration_seconds = 7200
    p = add_podcast(conn, 1)
    for n in range(100):
        add_episode(conn, p, str(n), "2020-01-01T00:00:00")
    conn.commit()
    refresh(conn, FixedStudy([Member(f"podcast:{p}")]))
    s = status(config, conn, "fixed")
    assert s["storage"]["pending_download_gb_estimate"] == 2.1
    assert s["storage"]["pending_download_episodes"] == 100
    assert any("WARNING" in step for step in s["next_steps"])


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
    monkeypatch.setattr(discover, "read_feed", lambda url, *a: read.append(url) or FeedRead([
        FeedEpisode(guid=f"{url}#1", title="t", audio_url="https://a/1.mp3",
                    published_date="2026-01-01T00:00:00")], 1, "complete"))
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

    transcript = config.transcript_dir / f"episode_{done}.jsonl.zst"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_bytes(b"x")
    links = tmp_path / "links"
    result = export(config, conn, "fixed", output=tmp_path / "m" / "episodes.csv", link_transcripts=links)
    assert result["episodes"] == 2 and result["linked"] == 1
    assert (links / transcript.name).resolve() == transcript.resolve()
    meta = json.loads((tmp_path / "m" / "study.json").read_text())
    assert meta["revision"] == 1 and len(meta["windows"]) == 2


# --- the monthly top-24 study ------------------------------------------------

def add_snapshot(conn, source, day, entries, chart=monthly.CHART, trusted=1):
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
    monkeypatch.setattr(monthly, "START_MONTH", "2017-01")
    # January: one snapshot early in the month with list A.
    # February: list B on the 1st, then list C on 26 later days. C held the
    # month; a union of snapshots would also admit B.
    add_snapshot(conn, "podbay", "2017-01-03", chart("A"))
    add_snapshot(conn, "podbay", "2017-02-01", chart("B"))
    for d in range(3, 29):
        add_snapshot(conn, "podbay", f"2017-02-{d:02d}", chart("C"))
    add_snapshot(conn, "podbay", "2017-04-02", chart("C"))   # March has no snapshot
    days = monthly.snapshot_days(conn, top24.AppleTop24Monthly.sources, 24)
    obs = monthly._observations(conn, days, monthly.entity_resolver(conn), 24)
    lists = monthly.monthly_lists(days, obs, 24)
    assert list(lists) == ["2017-01", "2017-02", "2017-03"]   # April not fully covered
    assert all(len(v) == 24 for v in lists.values())
    # B ranked for ~1.5 days, C for the other ~26.5: a union would hold 48
    # shows; the weighted list keeps C, except where B's very top outscores C's
    # bottom (B's #1 for 1.5 days = 36 points > C's #24 for 26.5 days).
    feb = {e["entity"] for e in lists["2017-02"]}
    assert sum(e.startswith("apple:C") for e in feb) == 23 and "apple:B0" in feb
    assert lists["2017-03"][0]["snapshots_in_month"] == 0
    assert lists["2017-02"][0]["monthly_rank"] == 1 and lists["2017-02"][0]["entity"] == "apple:C0"


def test_top24_sources_identity_and_trust(conn, monkeypatch):
    monkeypatch.setattr(monthly, "START_MONTH", "2020-01")
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
    days = dict((d, s) for d, _, s in monthly.snapshot_days(conn, top24.AppleTop24Monthly.sources, 24))
    assert days["2020-02-15"] == "apple_charts_page"


def test_mypodcastdata_source_order_per_study(conn):
    add_snapshot(conn, "apple_charts_page", "2024-10-01", chart("APPLE"))
    add_snapshot(conn, "mypodcastdata", "2024-10-01", chart("MPD", 100))
    add_snapshot(conn, "mypodcastdata", "2024-10-02", chart("MPD", 100))
    add_snapshot(conn, "chartable_itunes", "2024-10-02", chart("CH", 100, ids=False))
    add_snapshot(conn, "mypodcastdata", "2024-10-03", chart("MPD", 100), trusted=0)
    add_snapshot(conn, "mypodcastdata", "2024-10-04", chart("MPD", 60))

    def days(study):
        return {d: s for d, _, s in monthly.snapshot_days(conn, study.sources, study.depth)}
    # the original study never reads My Podcast Data
    assert days(top24.AppleTop24Monthly) == {"2024-10-01": "apple_charts_page",
                                             "2024-10-02": "chartable_itunes"}
    # it ranks below Apple's page and above Chartable
    assert days(monthly.AppleTop24MonthlyMPD) == {
        "2024-10-01": "apple_charts_page", "2024-10-02": "mypodcastdata",
        "2024-10-04": "mypodcastdata"}
    # deep studies skip Apple's 24-deep page and any snapshot short of their depth
    assert days(monthly.AppleTop50Monthly) == {
        "2024-10-01": "mypodcastdata", "2024-10-02": "mypodcastdata", "2024-10-04": "mypodcastdata"}
    assert days(monthly.AppleTop100Monthly) == {
        "2024-10-01": "mypodcastdata", "2024-10-02": "mypodcastdata"}


def test_deep_month_lists_hold_exactly_depth_shows(conn, monkeypatch):
    monkeypatch.setattr(monthly, "START_MONTH", "2017-01")
    add_snapshot(conn, "podbay", "2017-01-05", chart("A", 100))
    add_snapshot(conn, "podbay", "2017-01-20", chart("B", 100))
    add_snapshot(conn, "podbay", "2017-02-10", chart("A", 100))
    add_snapshot(conn, "podbay", "2017-02-25", chart("A", 100))
    add_snapshot(conn, "podbay", "2017-03-01", chart("A", 100))   # so February is fully covered
    for study, depth in ((monthly.AppleTop50Monthly, 50), (monthly.AppleTop100Monthly, 100)):
        members = study().select(conn)
        per_month = Counter(w.label for m in members for w in m.windows)
        assert per_month == {"2017-01": depth, "2017-02": depth}
        # B held most of January (Jan 13 on), A all of February
        firsts = {w.label: m.entity for m in members for w in m.windows
                  if w.attrs["monthly_rank"] == 1}
        assert firsts == {"2017-01": "apple:B0", "2017-02": "apple:A0"}


def test_original_study_definition_is_unchanged():
    # the definition hash stored in production for apple-top24-monthly v3
    assert top24.AppleTop24Monthly().definition_hash() == "5b5aa881fb998cb6"


def test_top24_uses_entity_links_for_titles(conn, monkeypatch):
    monkeypatch.setattr(monthly, "START_MONTH", "2020-01")
    p = add_podcast(conn, 1, apple_id="555")
    db.link_entity(conn, "title:noidshow", p, "itunes_search")
    add_snapshot(conn, "chartable_itunes", "2020-01-10", [("No Id Show", None)] + chart("Q", 23, ids=False))
    add_snapshot(conn, "chartable_itunes", "2020-02-10", [("No Id Show", None)] + chart("Q", 23, ids=False))
    entities = {m.entity for m in top24.AppleTop24Monthly().select(conn)}
    assert "apple:555" in entities and "title:noidshow" not in entities


def test_top24_cells_centre_on_midday():
    from datetime import date
    days = [date(2017, 1, 31), date(2017, 2, 1), date(2017, 2, 2)]
    cells = monthly._cells(days)
    # the snapshot of Feb 1 covers exactly Feb 1 (hours 24..48 from Jan 31 00:00)
    assert cells[1] == (24.0, 48.0)
    assert cells[0] == (0.0, 24.0) and cells[2] == (48.0, 72.0)


def test_top24_bare_titles_take_the_id_nearest_in_time(conn, monkeypatch):
    monkeypatch.setattr(monthly, "START_MONTH", "2018-01")
    add_snapshot(conn, "podbay", "2017-01-10", [("Same Name", "OLD")] + chart("A", 23))
    add_snapshot(conn, "apple_charts_page", "2024-09-10", [("Same Name", "NEW")] + chart("A", 23))
    resolve = monthly.entity_resolver(conn)
    assert resolve(None, "samename", "2018-06-01") == "apple:OLD"
    assert resolve(None, "samename", "2024-01-01") == "apple:NEW"


def test_reassignment_bumps_revision(conn):
    p = add_podcast(conn, 1)
    add_episode(conn, p, "e", "2019-01-05T00:00:00")
    conn.commit()
    refresh(conn, FixedStudy([Member("apple:1", None, [Window("a", "2019-01-01", "2019-02-01")])]))
    summary = refresh(conn, FixedStudy([Member("apple:1", None, [Window("b", "2019-01-01", "2019-02-01")])]))
    assert summary["revision"] == 2 and summary["episodes_reassigned"] == 1


def test_default_scope_requires_a_study(conn):
    with pytest.raises(StudyError):
        download.pending_episodes(conn, True, None, all_episodes=False)


def test_dedupe_ignores_time_and_punctuation_drift(conn):
    p = add_podcast(conn, 1)
    add_episode(conn, p, "a", "2020-01-01T05:00:00", title="Ep. 12: The Thing")
    add_episode(conn, p, "b", "2020-01-01T09:30:00", title="Ep 12 - The Thing")
    conn.commit()
    assert refresh(conn, FixedStudy([Member(f"podcast:{p}")]))["excluded"]["duplicate"] == 1


# --- gap classes ------------------------------------------------------------------

def month(label):
    y, m = map(int, label.split("-"))
    end = f"{y + (m == 12)}-{m % 12 + 1:02d}-01"
    return Window(label, f"{label}-01", end)


def weekly(conn, podcast_id, prefix, first, last, **kw):
    """One episode a week from ``first`` to ``last`` (ISO days)."""
    from datetime import date, timedelta
    day, n = date.fromisoformat(first), 0
    while day <= date.fromisoformat(last):
        n += 1
        db.insert_episode(conn, podcast_id, FeedEpisode(
            f"{prefix}-{n}", kw.get("title", "{prefix} {n}").format(prefix=prefix, n=n),
            f"https://a/{prefix}{n}.mp3", published_date=f"{day}T00:00:00"))
        day += timedelta(days=7)


def live_read(conn, podcast_id, oldest, read_on, items, status="ok"):
    url = conn.execute("SELECT rss_url FROM podcasts WHERE id = ?", (podcast_id,)).fetchone()[0]
    db.record_feed_read(conn, podcast_id, url, status)
    conn.execute("UPDATE podcast_feeds SET oldest_item = ?, last_read_at = ?, item_count = ? "
                 "WHERE podcast_id = ? AND url = ?", (oldest, read_on, items, podcast_id, url))


def classes_of(conn, study="fixed"):
    from podcast_pipeline.studies.gaps import GAP_CLASSES
    return {(g.podcast_id, w.label): w.gap_class
            for g in study_gaps(conn, study, classes=GAP_CLASSES) for w in g.classified}


def test_a_finished_series_is_not_publishing_and_not_an_archive_target(conn, config):
    """S-Town: seven episodes in March 2017, then years of back-catalog charting."""
    p = add_podcast(conn, 1)
    db.insert_episode(conn, p, FeedEpisode("t", "Introducing S-Town", "https://a/t.mp3",
                                           published_date="2017-03-05T00:00:00", episode_type="trailer"))
    for n in range(1, 8):
        add_episode(conn, p, f"s{n}", "2017-03-28T00:00:00", title=f"Chapter {n}")
    live_read(conn, p, "2017-03-05T00:00:00", "2026-10-02 12:00:00", 8)
    conn.commit()
    refresh(conn, FixedStudy([Member("apple:1", "S-Town", [month("2017-02"), month("2017-03"),
                                                           month("2017-05"), month("2018-01")])]))
    assert classes_of(conn) == {(p, "2017-02"): "before_launch",      # charted before it existed
                                (p, "2017-05"): "not_publishing",
                                (p, "2018-01"): "not_publishing"}
    assert study_gaps(conn, "fixed") == []                 # nothing for discover-archived
    s = status(config, conn, "fixed")
    w = s["windows"]
    assert w["gap_classes"] == {"missing": 0, "unknown": 0, "not_publishing": 2, "before_launch": 1}
    assert w["launch_windows"] == 1 and w["archive_targets"] == 0
    assert not any(step.startswith("discover-archived") for step in s["next_steps"])
    assert any("precede their show's first episode" in step for step in s["next_steps"])

    by_window = {r["label"]: r for r in status(config, conn, "fixed", by="window")["by_window"]}
    assert by_window["2017-05"]["gap_classes"]["not_publishing"] == 1 and by_window["2017-05"]["episodes"] == 0
    assert by_window["2017-03"]["episodes"] == 8
    by_member = status(config, conn, "fixed", by="member")["by_member"]
    assert by_member[0]["gap_classes"] == {"not_publishing": ["2017-05", "2018-01"], "before_launch": ["2017-02"]}


def test_a_rolling_feed_leaves_missing_windows_for_the_archive(conn):
    """A weekly show whose live feed keeps only recent items: Wayback gave us
    2016, the feed reaches back to 2020, and 2018 is in neither."""
    p = add_podcast(conn, 1)
    weekly(conn, p, "old", "2016-01-04", "2016-12-26", title="Ep. {n}0")   # numbered from 10
    weekly(conn, p, "new", "2020-01-06", "2026-09-28")
    live_read(conn, p, "2020-01-06T00:00:00", "2026-10-02 12:00:00", 300)
    conn.execute("INSERT INTO wayback_probes (podcast_id, url, status, detail) VALUES (?, 'u', 'ok', ?)",
                 (p, json.dumps({"captures_used": [{"timestamp": "20170101000000", "episodes": 52,
                                                    "oldest": "2016-01-04"}]})))
    conn.commit()
    windows = [month("2015-11"), month("2016-06"), month("2018-03"), month("2023-05")]
    refresh(conn, FixedStudy([Member("apple:1", "Show 1", windows)]))
    classes = classes_of(conn)
    assert classes == {(p, "2015-11"): "missing", (p, "2018-03"): "missing"}
    [gaps] = study_gaps(conn, "fixed")
    assert [w[0] for w in gaps.windows] == ["2015-11", "2018-03"] and gaps.empty == {"2015-11", "2018-03"}
    reasons = {w.label: w.reason for w in gaps.classified}
    assert "numbered from 10" in reasons["2015-11"] and "no listing covers it" in reasons["2018-03"]


def test_a_feed_that_skips_items_covers_nothing(conn):
    """The Daily's public feed lists 63 items: the last few weeks plus a few
    re-surfaced old episodes. Its date span is not coverage."""
    p = add_podcast(conn, 1)
    weekly(conn, p, "o", "2021-10-04", "2021-11-08")       # held from earlier reads
    weekly(conn, p, "w", "2024-01-01", "2026-09-28")
    live_read(conn, p, "2021-10-04T00:00:00", "2026-10-02 12:00:00", 20)
    conn.commit()
    refresh(conn, FixedStudy([Member("apple:1", "Show 1", [month("2019-05"), month("2023-03")])]))
    [gaps] = study_gaps(conn, "fixed")
    reasons = {w.label: (w.gap_class, w.reason) for w in gaps.classified}
    assert reasons["2019-05"][0] == "missing" and "skips some" in reasons["2019-05"][1]
    assert reasons["2023-03"][0] == "unknown"           # a year-long hole, and no rolling evidence


def test_without_evidence_a_gap_is_unknown(conn):
    p = add_podcast(conn, 1)
    add_episode(conn, p, "a", "2020-06-10T00:00:00", title="On the economy")
    add_episode(conn, p, "b", "2020-06-17T00:00:00", title="On the weather")
    p2 = add_podcast(conn, 2)                                # resolved, but no episodes at all
    conn.commit()
    refresh(conn, FixedStudy([Member("apple:1", "Show 1", [month("2020-04"), month("2020-06")]),
                              Member("apple:2", "Show 2", [month("2020-04")])]))
    assert classes_of(conn) == {(p, "2020-04"): "unknown", (p, "2020-06"): "unknown",
                                (p2, "2020-04"): "unknown"}


def test_manual_identity_links_are_never_before_launch(conn):
    p = add_podcast(conn, 1)
    add_episode(conn, p, "late", "2021-06-01T00:00:00")
    db.link_entity(conn, "title:renamed", p, "manual", {"note": "renamed show"})
    conn.commit()
    w = [Window("2019-03", "2019-03-01", "2019-04-01")]
    refresh(conn, FixedStudy([Member("title:renamed", "Renamed", w)]))
    [g] = study_gaps(conn, "fixed")
    assert [c.gap_class for c in g.classified] == ["unknown"]


def test_dedupe_across_utc_midnight_needs_matching_duration(conn):
    p = add_podcast(conn, 1)
    for guid, when in (("a", "2018-01-07T23:30:00"), ("b", "2018-01-08T00:30:00")):
        add_episode(conn, p, guid, when, title="550: Three Miles")
    conn.execute("UPDATE episodes SET duration_seconds = 3600")
    # a daily show reusing one title: adjacent days, different lengths
    for guid, when, secs in (("c", "2018-02-01T06:00:00", 1500), ("d", "2018-02-02T06:00:00", 2400)):
        add_episode(conn, p, guid, when, title="Morning Briefing")
        conn.execute("UPDATE episodes SET duration_seconds = ? WHERE episode_guid = ?", (secs, guid))
    conn.commit()
    summary = refresh(conn, FixedStudy([Member(f"podcast:{p}")]))
    assert summary["excluded"]["duplicate"] == 1 and summary["episodes"] == 3


class NoTrailers(FixedStudy):
    exclude_trailers = True


def test_trailers_promos_and_clips_are_excluded_when_asked(conn):
    p = add_podcast(conn, 1)
    keep = add_episode(conn, p, "real", "2020-01-02T00:00:00", title="Episode 1: The Start")
    add_episode(conn, p, "promo", "2020-01-03T00:00:00", title="Introducing: Some Other Show")
    clip = add_episode(conn, p, "clip", "2020-01-04T00:00:00", title="A quick note")
    conn.execute("UPDATE episodes SET duration_seconds = 40 WHERE id = ?", (clip,))
    conn.execute("UPDATE episodes SET duration_seconds = 3000 WHERE id != ?", (clip,))
    conn.commit()
    summary = refresh(conn, NoTrailers([Member(f"podcast:{p}")]))
    assert list(episodes_of(conn, "fixed")) == [keep]
    assert summary["excluded"]["trailer_or_promo"] == 2


def test_feed_items_beyond_the_discovery_cap_are_missing_not_quiet(conn):
    p = add_podcast(conn, 1)
    url = "https://feeds.example/1"
    for d in ("2025-03-01", "2025-04-01"):
        add_episode(conn, p, d, f"{d}T00:00:00")
        db.record_episode_source(conn, p, d, "feed", url)
    # the feed listed 12,000 items back to 2022, but discover kept only the newest
    conn.execute("""INSERT OR REPLACE INTO podcast_feeds (podcast_id, url, source, last_read_at, last_status,
                    item_count, oldest_item, newest_item)
                    VALUES (?, ?, 'itunes_lookup', '2026-10-03', 'ok', 12000, '2022-12-01T00:00:00',
                            '2025-04-01T00:00:00')""", (p, url))
    conn.commit()
    refresh(conn, FixedStudy([Member(f"podcast:{p}", None, [Window("2023-01", "2023-01-01", "2023-02-01")])]))
    from podcast_pipeline.studies.gaps import classify_study
    [g] = classify_study(conn, "fixed", ("missing", "unknown"))
    assert [c.gap_class for c in g.classified] == ["missing"]


def test_dedupe_never_chains_consecutive_daily_episodes(conn):
    p = add_podcast(conn, 1)
    for i, (when, secs) in enumerate((("2020-03-01T23:00:00", 3093), ("2020-03-02T23:00:00", 2969),
                                      ("2020-03-03T23:00:00", 3085))):
        add_episode(conn, p, f"d{i}", when, title="The Best of Stugotz")
        conn.execute("UPDATE episodes SET duration_seconds = ? WHERE episode_guid = ?", (secs, f"d{i}"))
    conn.commit()
    assert refresh(conn, FixedStudy([Member(f"podcast:{p}")]))["episodes"] == 3
