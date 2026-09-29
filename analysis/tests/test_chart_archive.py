"""Regression checks for archive identity, retry, and recovery decisions."""
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from analysis.chart_archive import population, recoverability as rec, within_month


def test_resolve_entities_uses_only_apple_show_ids_and_preserves_direct_ids():
    rows = [
        ("chartable_itunes", "podcast", "1619", "1619"),
        ("podbay", "podcast", "1476928106", "1619"),
        ("apple_charts_page", "episode", "999", "1619"),
        ("apple_charts_page", "channel", "888", "1619"),
        ("spotify_api", "show", "777", "1619"),
        ("itunes_rss", "podcast", "123", "sharedtitle"),
        ("podbay", "podcast", "456", "sharedtitle"),
        ("chartable_itunes", "podcast", "42", "42"),
        ("chartable_itunes", "podcast", "sharedtitle", "sharedtitle"),
    ]
    obs = pd.DataFrame(rows, columns=["source", "unit", "entity_id", "key"])
    # Misleading slug and non-show evidence vastly outnumber the correct ID.
    evidence = pd.concat([obs, obs.iloc[[0, 2, 3, 4, 5]].loc[lambda d: d.index.repeat(5)]])
    got = population.resolve_entities(evidence, obs)
    assert got.entity.tolist() == [
        "1476928106", "1476928106", "1476928106", "1476928106", "1476928106",
        "123", "456", "title:42", "123",
    ]
    assert "entity" not in obs


@pytest.mark.parametrize("failure", ["timeout", "http", "parse"])
def test_failed_feed_has_no_months(monkeypatch, failure):
    response = Mock(status_code=503 if failure == "http" else 200, url="https://feed")
    response.iter_content.return_value = [b"<rss><channel/></rss>"]
    session = Mock()
    session.get.return_value = response
    if failure == "timeout":
        session.get.side_effect = requests.Timeout("timed out")
    monkeypatch.setattr(rec, "session", lambda: session)
    monkeypatch.setattr(rec, "parse_feed", Mock(side_effect=ValueError("invalid feed")))
    result = rec.fetch_feed_record("https://feed")
    assert result["error"]
    assert "months" not in result


def test_successfully_parsed_empty_feed_is_complete(monkeypatch):
    response = Mock(status_code=200, url="https://feed")
    response.iter_content.return_value = [b"<rss><channel/></rss>"]
    monkeypatch.setattr(rec, "session", lambda: SimpleNamespace(get=lambda *a, **k: response))
    monkeypatch.setattr(rec, "parse_feed", lambda *a, **k: [])
    result = rec.fetch_feed_record("https://feed")
    assert result["error"] is None
    assert result["months"] == []


def test_feed_phase_retries_legacy_errors_but_retains_success(monkeypatch, tmp_path):
    monkeypatch.setattr(rec, "CACHE", tmp_path)
    rec.save_cache("feeds", {
        "failed": {"error": "HTTP 503", "months": []},
        "good": {"error": None, "months": []},
        "legacy": {"error": None, "n_episodes": 10},
    })
    monkeypatch.setattr(rec, "feed_urls", lambda: {sid: sid for sid in ("failed", "good", "legacy")})
    monkeypatch.setattr(rec, "population", lambda: pd.DataFrame({"sid": ["failed", "good", "legacy"]}))
    fetch = Mock(side_effect=lambda url: ({"error": None, "months": ["2019-01"]}
                                         if url == "failed" else {"error": "timeout"}))
    monkeypatch.setattr(rec, "fetch_feed_record", fetch)
    result = rec.phase_feeds()
    assert {call.args[0] for call in fetch.call_args_list} == {"failed", "legacy"}
    assert result["failed"]["months"] == ["2019-01"]
    assert result["good"] == {"error": None, "months": []}
    assert result["legacy"] == {"error": None, "n_episodes": 10}


@pytest.mark.parametrize("date, expected", [("2010-01-01", 0), ("2019-06-01", 1)])
def test_wayback_only_counts_era_episodes(monkeypatch, date, expected):
    monkeypatch.setattr(rec, "cdx", lambda url: [("20190101000000", url), ("20191231000000", url)])
    monkeypatch.setattr(rec.time, "sleep", lambda _: None)
    monkeypatch.setattr(rec, "_wayback_body", lambda _: b"feed")
    monkeypatch.setattr(rec, "parse_feed", lambda *a, **k: [
        SimpleNamespace(published_date=date, audio_url="https://audio")])
    probe = Mock(return_value={"status": 206, "content_type": "audio/mpeg", "bytes": 65536})
    monkeypatch.setattr(rec, "_wayback_available", Mock(return_value=False))
    monkeypatch.setattr(rec, "probe_audio", probe)
    wb = rec.wayback_record({"feed_url": "https://feed", "first_seen": "2019-01-01",
                             "last_seen": "2019-12-31"})
    assert wb["spans_window"]
    assert wb["era_enclosures_ok"] == wb["era_enclosures_tried"] == expected
    assert probe.call_count == expected
    assert rec.verdict({"feed_live": False, "audio_ok": False, "window_coverage": 0,
                        "transcripts_cover_era": False, "wb_spans_window": True,
                        "wb_era_enclosures_ok": wb["era_enclosures_ok"]}) == (
                            "archive_only" if expected else "not_recoverable")


def test_wayback_phase_refreshes_legacy_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(rec, "CACHE", tmp_path)
    rec.save_cache("wayback", {"old": {"era_enclosures_ok": 3},
                               "new": {"era_version": rec.WAYBACK_ERA_VERSION}})
    monkeypatch.setattr(rec, "build_rows", lambda: [
        {"sid": sid, "needs_fallback": True, "last_seen": "2019-12-31",
         "last_year": 2019, "est_days": 100} for sid in ("old", "new")])
    fetch = Mock(return_value={"era_version": rec.WAYBACK_ERA_VERSION, "era_enclosures_ok": 0})
    monkeypatch.setattr(rec, "wayback_record", fetch)
    result = rec.phase_wayback(60)
    assert fetch.call_count == 1
    assert fetch.call_args.args[0]["sid"] == "old"
    assert result["old"]["era_enclosures_ok"] == 0


def test_sparse_month_coverage_has_defined_columns():
    maps = {pd.Timestamp(date): {"show": 1}
            for date in ("2020-01-01", "2020-02-01", "2020-03-01")}
    result = within_month.month_coverage(maps, depth=1)
    assert result.empty
    assert result.columns.tolist() == ["month", "snapshots", "union",
                                       "median_single_coverage", "first_last_jaccard"]
    maps[pd.Timestamp("2020-01-02")] = {"other": 1}
    maps[pd.Timestamp("2020-01-03")] = {"show": 1}
    maps[pd.Timestamp("2020-01-04")] = {"show": 1}
    result = within_month.month_coverage(maps, depth=1)
    assert result.iloc[0]["month"] == "2020-01"
    assert result.iloc[0]["union"] == 2


@pytest.mark.parametrize("version, expected", [(None, "not_recoverable"),
                                              (rec.WAYBACK_ERA_VERSION, "archive_only")])
def test_report_rejects_legacy_enclosure_counts(monkeypatch, version, expected):
    show = dict(entity="123", key="show", name="Show", publisher="Publisher",
                titles=1, apple_id="123", sid="123", n_obs=10, est_days=100,
                deep_obs=10, shallow_obs=0, best_rank=1, first_seen="2019-01-01",
                last_seen="2019-12-31", first_year=2019, last_year=2019)
    monkeypatch.setattr(rec, "population", lambda: pd.DataFrame([show]))
    monkeypatch.setattr(rec, "feed_urls", lambda: {"123": "https://feed"})
    wb = {"era_version": version, "era_enclosures_ok": 1, "era_enclosures_tried": 1,
          "first_capture": "20190101000000", "last_capture": "20191231000000"}
    monkeypatch.setattr(rec, "load_cache", lambda name: {"123": wb} if name == "wayback" else {})
    row = rec.build_rows()[0]
    assert row["verdict"] == expected
    assert row["wb_probed"] == (version == rec.WAYBACK_ERA_VERSION)
