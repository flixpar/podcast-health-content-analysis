"""Regression checks for archive identity, retry, and recovery decisions."""
import gzip
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from analysis.chart_archive import cdx_index, parse, population, recoverability as rec, within_month


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
                               "new": {"era_version": rec.WAYBACK_ERA_VERSION,
                                       "window": ["2019-01-01", "2019-12-31"]}})
    monkeypatch.setattr(rec, "build_rows", lambda: [
        {"sid": sid, "needs_fallback": True, "first_seen": "2019-01-01",
         "last_seen": "2019-12-31",
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
    wb = {"era_version": version, "window": ["2019-01-01", "2019-12-31"],
          "era_enclosures_ok": 1, "era_enclosures_tried": 1,
          "first_capture": "20190101000000", "last_capture": "20191231000000"}
    monkeypatch.setattr(rec, "load_cache", lambda name: {"123": wb} if name == "wayback" else {})
    row = rec.build_rows()[0]
    assert row["verdict"] == expected
    assert row["wb_probed"] == (version == rec.WAYBACK_ERA_VERSION)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("archive regression tests must run offline")
    monkeypatch.setattr(requests.Session, "request", fail)


def test_lookup_failure_retries_and_successful_missing_result_is_cached(monkeypatch, tmp_path):
    monkeypatch.setattr(rec, "CACHE", tmp_path)
    monkeypatch.setattr(rec, "population", lambda: pd.DataFrame([
        dict(apple_id="123", sid="123", name="Show", publisher="Publisher")]))
    lookup = Mock(return_value=None)
    monkeypatch.setattr(rec, "_itunes", lookup)
    first = rec.phase_lookup()
    assert first["123"]["error"]
    assert first["s:123"]["error"]
    assert lookup.call_count == 2
    lookup.return_value = {"results": []}
    second = rec.phase_lookup()
    assert second["123"]["source"] == "lookup_missing"
    assert second["s:123"]["source"] == "search_missing"
    assert lookup.call_count == 4
    rec.phase_lookup()
    assert lookup.call_count == 4


def test_legacy_lookup_misses_retry_without_refetching_good_records(monkeypatch, tmp_path):
    monkeypatch.setattr(rec, "CACHE", tmp_path)
    rec.save_cache("lookup", {"123": {"source": "lookup_missing"},
                             "s:123": {"source": "search_missing"},
                             "456": {"source": "lookup", "feed_url": "https://good"}})
    monkeypatch.setattr(rec, "population", lambda: pd.DataFrame([
        dict(apple_id=aid, sid=aid, name="Show", publisher="Publisher")
        for aid in ("123", "456")]))
    lookup = Mock(return_value={"results": []})
    monkeypatch.setattr(rec, "_itunes", lookup)
    result = rec.phase_lookup()
    assert lookup.call_count == 2
    assert result["456"]["feed_url"] == "https://good"
    rec.phase_lookup()
    assert lookup.call_count == 2


CDX_ROW = "20190101000000 https://example.com/chart com,example)/chart text/html 200 DIGEST 123\n"


@pytest.mark.parametrize("bad", ["<html>503 Service Unavailable</html>", "", "bad row",
                                  CDX_ROW + "truncated\n"])
def test_cdx_rejects_bad_responses_before_accepting_valid_data(monkeypatch, bad):
    run = Mock(side_effect=[SimpleNamespace(returncode=0, stdout=bad),
                            SimpleNamespace(returncode=0, stdout=CDX_ROW)])
    monkeypatch.setattr(cdx_index.subprocess, "run", run)
    monkeypatch.setattr(cdx_index.time, "sleep", lambda _: None)
    assert cdx_index.cdx("example.com") == CDX_ROW
    assert run.call_count == 2
    assert "-fsSL" in run.call_args.args[0]


def test_cdx_replaces_invalid_cache_and_keeps_failure_retryable(monkeypatch, tmp_path):
    monkeypatch.setattr(cdx_index, "INDEX_DIR", tmp_path)
    monkeypatch.setattr(cdx_index, "TARGETS", {"chart": "example.com"})
    monkeypatch.setattr(cdx_index.time, "sleep", lambda _: None)
    path = tmp_path / "chart.cdx"
    path.write_text("<html>503</html>")
    fetch = Mock(return_value=None)
    monkeypatch.setattr(cdx_index, "cdx", fetch)
    assert cdx_index.main() == 1
    fetch.return_value = CDX_ROW
    assert cdx_index.main() == 0
    assert path.read_text() == CDX_ROW
    assert cdx_index.main() == 0
    assert fetch.call_count == 2


@pytest.mark.parametrize("body, expected", [
    ("<html>503</html>", None), ("", None),
    ('[["timestamp", "original"]]', []),
    ('[["timestamp", "original"], ["20190101000000", "https://feed"]]',
     [["20190101000000", "https://feed"]]),
])
def test_feed_cdx_distinguishes_failed_requests_from_empty_results(monkeypatch, body, expected):
    monkeypatch.setattr(rec.subprocess, "run", Mock(
        return_value=SimpleNamespace(returncode=0, stdout=body)))
    monkeypatch.setattr(rec.time, "sleep", lambda _: None)
    assert rec.cdx("https://feed", attempts=1) == expected


def test_failed_wayback_request_is_incomplete_and_changed_window_requires_retry(monkeypatch):
    monkeypatch.setattr(rec, "cdx", lambda _: None)
    monkeypatch.setattr(rec.time, "sleep", lambda _: None)
    row = dict(feed_url="https://feed", first_seen="2019-01-01", last_seen="2019-12-31")
    failed = rec.wayback_record(row)
    assert failed["error"]
    assert not rec.current_wayback(failed, row)
    successful = dict(failed, error=None)
    assert rec.current_wayback(successful, row)
    assert not rec.current_wayback(successful, dict(row, last_seen="2020-12-31"))


def test_sparse_turnover_main_writes_readable_empty_outputs(monkeypatch, tmp_path):
    # Enough usable days to reach the analysis, but no pair in a supported gap bin.
    rows = [dict(source="podbay", region="us", chart="all-podcasts", unit="podcast",
                 genre="all-podcasts", rank=rank, entity_id=str(rank), captured_at=date)
            for date in ("2010-01-01", "2011-01-01", "2012-01-01")
            for rank in range(1, 101)]
    (tmp_path / "chart_rows.parquet").touch()
    monkeypatch.setattr(within_month, "PARSED", tmp_path)
    monkeypatch.setattr(within_month, "SUMMARY", tmp_path / "summary")
    monkeypatch.setattr(pd, "read_parquet", lambda _: pd.DataFrame(rows))
    assert within_month.main() == 0
    assert pd.read_csv(tmp_path / "summary/within_month_turnover.csv").empty
    assert pd.read_csv(tmp_path / "summary/within_month_coverage.csv").empty


def test_offline_chart_to_population_to_recovery_report(monkeypatch, tmp_path):
    # Real parser inputs: Apple show ID plus Chartable's numeric title/slug.
    apple = tmp_path / "apple.json.gz"
    apple.write_bytes(gzip.compress(json.dumps({"feed": {"entry": [{
        "im:name": {"label": "1619"}, "im:artist": {"label": "Publisher"},
        "id": {"attributes": {"im:id": "1476928106"}},
    }]}}).encode()))
    chartable = tmp_path / "chartable.html.gz"
    chartable.write_bytes(gzip.compress(b'<table><tr><div class="header-font">1</div>'
        b'<a href="/podcasts/1619">1619</a><div class="silver">Publisher</div></tr></table>'))
    evidence = pd.DataFrame(parse.parse_itunes_rss(apple, "toppodcasts")
                            + parse.parse_chartable(chartable, "us-all-podcasts-podcasts",
                                                    "chartable_itunes"))
    evidence["key"] = evidence["name"].map(population.key)
    obs = pd.concat([evidence.iloc[[1]].assign(date=date, cut=50)
                     for date in ("2019-01-01", "2019-04-01", "2019-07-01")])
    resolved = population.resolve_entities(evidence, obs)
    scored = population.score(resolved, population.midpoint_weights(
        pd.Series(["2019-01-01", "2019-04-01", "2019-07-01"])))
    assert scored.entity.unique().tolist() == ["1476928106"]
    assert scored.w.sum() == 181
    show = dict(entity="1476928106", key="1619", name="1619", publisher="Publisher",
                titles=1, apple_id="1476928106", sid="1476928106", n_obs=3,
                est_days=181, deep_obs=3, shallow_obs=0, best_rank=1,
                first_seen="2019-01-01", last_seen="2019-07-01",
                first_year=2019, last_year=2019)
    monkeypatch.setattr(rec, "population", lambda: pd.DataFrame([show]))
    monkeypatch.setattr(rec, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(rec, "feed_urls", lambda: {show["sid"]: "https://feed"})
    body = b"""<rss version="2.0"><channel><title>1619</title>
        <item><title>First</title><guid>first</guid><pubDate>Tue, 01 Jan 2019 00:00:00 GMT</pubDate>
        <enclosure url="https://audio/first" type="audio/mpeg" length="10000"/></item>
        <item><title>Last</title><guid>last</guid><pubDate>Mon, 01 Jul 2019 00:00:00 GMT</pubDate>
        <enclosure url="https://audio/last" type="audio/mpeg" length="10000"/></item>
        </channel></rss>"""
    response = Mock(status_code=200, url="https://feed")
    response.iter_content.return_value = [body]
    monkeypatch.setattr(rec, "session", lambda: SimpleNamespace(get=lambda *a, **k: response))
    rec.save_cache("feeds", {show["sid"]: rec.fetch_feed_record("https://feed")})
    rec.save_cache("audio", {show["sid"]: [dict(status=206, bytes=65536, content_type="audio/mpeg")]})
    rows = rec.build_rows()
    assert rows[0]["verdict"] == "fully_recoverable"
    df = pd.DataFrame(rows).assign(era="2018-2021")
    monkeypatch.setattr(rec, "POP", tmp_path)
    (tmp_path / "summary.json").write_text(json.dumps({"rule": {
        "min_est_days": 180, "min_obs": 3, "deep_cut": 50, "shallow_cut": 24}}))
    report = rec.render_md(df, pd.DataFrame())
    assert "≥180 exposure-weighted days" in report
    assert "| fully_recoverable | 1 | 100% |" in report
    assert "feed-fetch records for 1 of 1 shows" in report
    assert "All five phases ran" not in report
    assert "three hours" not in report
    assert "Ben Shapiro" not in report


def test_wayback_reuses_discovery_but_reprobes_legacy_enclosures(monkeypatch):
    cdx = Mock(side_effect=AssertionError("known captures need no new CDX query"))
    monkeypatch.setattr(rec, "cdx", cdx)
    monkeypatch.setattr(rec, "_wayback_body", lambda _: b"feed")
    monkeypatch.setattr(rec, "parse_feed", lambda *a, **k: [
        SimpleNamespace(published_date="2010-01-01", audio_url="https://unrelated")])
    probe = Mock(side_effect=AssertionError("out-of-window audio must not be probed"))
    monkeypatch.setattr(rec, "probe_audio", probe)
    old = dict(n_captures=5, first_capture="20190101000000", last_capture="20191231000000",
               snapshot_ts="20191231000000", urls_tried=["https://feed"], era_enclosures_ok=3)
    row = dict(feed_url="https://feed", first_seen="2019-01-01", last_seen="2019-12-31")
    result = rec.wayback_record(row, previous=old)
    assert result["capture_source"] == "cached"
    assert result["spans_window"]
    assert result["era_enclosures_ok"] == 0
    assert rec.current_wayback(result, row)
