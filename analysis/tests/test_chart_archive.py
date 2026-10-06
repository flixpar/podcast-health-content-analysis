"""Regression checks for archive identity, retry, and recovery decisions."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from analysis.chart_archive import (
    analyze, cc_fetch, cc_index, cdx_index, fetch_wayback, parse, population,
    recoverability as rec, snapshots, within_month,
)


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
    assert "collapse=" not in run.call_args.args[0][-1]


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
                 genre="all-podcasts", rank=rank, entity_id=str(rank), captured_at=date,
                 path=f"raw/{date}")
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


def test_cdx_refreshes_legacy_digest_collapsed_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(cdx_index, "INDEX_DIR", tmp_path)
    monkeypatch.setattr(cdx_index, "TARGETS", {"chart": "example.com"})
    monkeypatch.setattr(cdx_index.time, "sleep", lambda _: None)
    (tmp_path / "chart.cdx").write_text(CDX_ROW)
    repeated = CDX_ROW + CDX_ROW.replace("20190101000000", "20190110000000")
    fetch = Mock(return_value=repeated)
    monkeypatch.setattr(cdx_index, "cdx", fetch)
    assert cdx_index.main() == 0
    assert (tmp_path / "chart.cdx").read_text() == repeated
    assert cdx_index.main() == 0
    fetch.assert_called_once()


def test_downloaders_keep_identical_payloads_at_distinct_dates(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch_wayback, "INDEX_DIR", tmp_path)
    repeated = CDX_ROW.replace("20190101000000", "20190110000000")
    (tmp_path / "podbay.cdx").write_text(CDX_ROW + repeated + repeated)
    assert [r["timestamp"] for r in fetch_wayback.load_rows()] == [
        "20190101000000", "20190110000000"]
    monkeypatch.setattr(cc_fetch, "CC_INDEX", tmp_path / "cc")
    target = tmp_path / "cc/podbay"
    target.mkdir(parents=True)
    captures = [dict(status="200", url="https://example.com/chart", digest="SAME",
                     timestamp=ts, filename="capture.warc.gz", offset="0", length="100")
                for ts in ("20190101000000", "20190110000000", "20190110000000")]
    (target / "crawl.jsonl").write_text("\n".join(map(json.dumps, captures)))
    assert [r["timestamp"] for r in cc_fetch.load_rows()] == [
        "20190101000000", "20190110000000"]
    weights = population.midpoint_weights(pd.Series(["2019-01-01", "2019-01-10", "2019-01-11"]))
    assert weights.iloc[:2].sum() == 9.5  # repeated chart stays through Jan 10


def test_cc_failure_exits_nonzero_and_only_retries_missing_query(monkeypatch, tmp_path):
    monkeypatch.setattr(cc_index, "CC_DIR", tmp_path)
    monkeypatch.setattr(cc_index, "PATTERNS", {"chart": "example.com/*"})
    monkeypatch.setattr(cc_index.time, "sleep", lambda _: None)
    (tmp_path / "collinfo.json").write_text(json.dumps([{"id": "ok"}, {"id": "failed"}]))
    fetch = Mock(side_effect=['{"url": "https://example.com/chart"}', None, ""])
    monkeypatch.setattr(cc_index, "get", fetch)
    assert cc_index.main() == 1
    assert (tmp_path / "chart/ok.jsonl").exists()
    assert not (tmp_path / "chart/failed.jsonl").exists()
    assert cc_index.main() == 0
    assert (tmp_path / "chart/failed.jsonl").read_text() == ""
    assert fetch.call_count == 3
    assert cc_index.main() == 0
    assert fetch.call_count == 3


@pytest.mark.parametrize("target", ["marketingtools", "applemarketingtools"])
@pytest.mark.parametrize("slug, unit", [("api_v2_us_podcasts_top_100_podcasts.json", "podcast"),
                                        ("api_v2_us_podcasts_top_100_podcast-episodes.json", "episode")])
def test_marketing_tools_results_parse_in_order(tmp_path, target, slug, unit):
    path = tmp_path / "feed.json.gz"
    url = "https://podcasts.apple.com/us/podcast/show/id123"
    path.write_bytes(gzip.compress(json.dumps({"feed": {"results": [
        dict(id="123", name="First", artistName="Publisher", url=url),
        dict(id="456", name="Second", artistName="Other", url=url.replace("123", "456")),
    ]}}).encode()))
    rows = parse.PARSERS[target](path, slug)
    assert [(r["entity_id"], r["name"], r["rank"], r["unit"]) for r in rows] == [
        ("123", "First", 1, unit), ("456", "Second", 2, unit)]
    assert rows[0]["publisher"] == "Publisher"
    assert rows[0]["entity_url"] == url


@pytest.mark.parametrize("failed", [dict(error="timeout"), dict(status=503),
                                  dict(status=200, bytes=0),
                                  dict(status=200, bytes=4096, content_type="text/html")])
def test_audio_retries_failed_probes_and_refreshes_changed_samples(monkeypatch, tmp_path, failed):
    monkeypatch.setattr(rec, "CACHE", tmp_path)
    rec.save_cache("feeds", {"123": {"samples": [{"url": "https://audio/old"}]}})
    rec.save_cache("audio", {"123": [dict(failed, url="https://audio/old")]})
    probe = Mock(side_effect=lambda url: dict(url=url, status=206, bytes=4096,
                                            content_type="audio/mpeg"))
    monkeypatch.setattr(rec, "probe_audio", probe)
    assert rec.audio_ok(rec.phase_audio()["123"])
    assert probe.call_count == 1
    rec.phase_audio()
    assert probe.call_count == 1
    rec.save_cache("feeds", {"123": {"samples": [{"url": "https://audio/new"}]}})
    assert rec.phase_audio()["123"][0]["url"] == "https://audio/new"
    assert probe.call_count == 2


def chart_capture(path, timestamp, ranks=range(1, 101), *, source="podbay", page=1,
                  archive="wayback", changed=False):
    return [dict(source=source, platform="apple", region="us", unit="podcast",
                 chart="all-podcasts", genre="all-podcasts", page=page, archive=archive,
                 rank=rank, entity_id="999" if changed and rank == 50 else str(rank),
                 name="Changed" if changed and rank == 50 else f"Show {rank}",
                 key="changed" if changed and rank == 50 else f"show{rank}",
                 publisher="Publisher", captured_at=timestamp,
                 date=timestamp[:10], path=path)
            for rank in ranks]


def test_population_uses_one_capture_before_applying_depth_cut():
    df = pd.DataFrame(chart_capture("early", "2020-01-01T01:00:00Z", range(1, 51))
                      + chart_capture("late", "2020-01-01T02:00:00Z", changed=True))
    days = pd.DataFrame([dict(date="2020-01-01", series="apple/podbay", cut=50)])
    observations = population.chart_observations(df, days)
    assert len(observations) == 50
    assert set(observations.path) == {"late"}
    per_day = population.score(population.resolve_entities(df, observations),
                               pd.Series({"2020-01-01": 10.0}))
    assert "50" not in set(per_day.entity)
    assert "999" in set(per_day.entity)
    assert per_day.w.sum() == 500


def test_daily_ties_choose_earliest_capture_deterministically():
    df = pd.DataFrame(chart_capture("early", "2020-01-01T01:00:00Z")
                      + chart_capture("late", "2020-01-01T02:00:00Z", changed=True))
    assert set(snapshots.select_daily(df.sample(frac=1, random_state=1)).path) == {"early"}


@pytest.mark.parametrize("timestamp, archive, complete", [
    ("2020-01-01T01:05:00Z", "wayback", True),
    ("2020-01-01T13:00:00Z", "wayback", False),
    ("2020-01-01T01:05:00Z", "commoncrawl", False),
    ("2020-01-02T01:05:00Z", "wayback", False),
])
def test_chartable_aligns_pages_by_time_and_archive(timestamp, archive, complete):
    df = pd.DataFrame(chart_capture("page1", "2020-01-01T01:00:00Z", range(1, 51),
                                    source="chartable_itunes")
                      + chart_capture("page2", timestamp, range(51, 101),
                                      source="chartable_itunes", page=2, archive=archive))
    selected = snapshots.select_daily(df)
    first_day = selected[selected.date == "2020-01-01"]
    assert len(first_day) == (100 if complete else 50)
    maps = within_month.daily_maps(df, depth=100)
    assert bool(maps) == complete


def test_chartable_uses_nearest_page_once_and_does_not_combine_partial_page1s():
    df = pd.DataFrame(chart_capture("page1", "2020-01-01T01:00:00Z", range(1, 51),
                                    source="chartable_itunes")
                      + chart_capture("near", "2020-01-01T01:05:00Z", range(51, 101),
                                      source="chartable_itunes", page=2)
                      + chart_capture("far", "2020-01-01T01:15:00Z", range(51, 101),
                                      source="chartable_itunes", page=2, changed=True))
    assert set(snapshots.select_daily(df).path) == {"page1", "near"}
    partial = pd.DataFrame(chart_capture("a", "2020-01-01T01:00:00Z", range(1, 51))
                           + chart_capture("b", "2020-01-01T02:00:00Z", range(51, 101)))
    assert len(snapshots.select_daily(partial)) == 50
    assert not within_month.daily_maps(partial, depth=100)


def test_all_aggregate_consumers_exclude_targeted_shards(monkeypatch, tmp_path):
    main = pd.DataFrame(chart_capture("main", "2020-01-01T01:00:00Z", range(1, 2)))
    cc = pd.DataFrame(chart_capture("cc", "2020-01-02T01:00:00Z", range(1, 2), archive="commoncrawl"))
    main.to_parquet(tmp_path / "chart_rows.parquet")
    cc.to_parquet(tmp_path / "chart_rows_cc.parquet")
    pd.concat([main] * 10).to_parquet(tmp_path / "chart_rows_podbay.parquet")
    pd.concat([cc] * 10).to_parquet(tmp_path / "chart_rows_cc_podbay.parquet")
    monkeypatch.setattr(analyze, "PARSED", tmp_path)
    monkeypatch.setattr(population, "PARSED", tmp_path)
    assert analyze.load().path.tolist() == ["main", "cc"]
    assert population.load_rows().path.tolist() == ["main", "cc"]
    monkeypatch.setattr(within_month, "PARSED", tmp_path)
    monkeypatch.setattr(within_month, "SUMMARY", tmp_path / "summary")
    seen = []
    monkeypatch.setattr(within_month, "series_frames", lambda df: seen.extend(df.path) or {})
    assert within_month.main() == 0
    assert seen == ["main", "cc"]


@pytest.mark.parametrize("source, page, timestamp, expected_top100", [
    ("podbay", 1, "2020-01-01T02:00:00Z", 50),
    ("chartable_itunes", 2, "2020-01-01T01:05:00Z", 100),
    ("chartable_itunes", 2, "2020-01-01T13:00:00Z", 50),
])
def test_summary_and_population_trust_the_same_selected_snapshot(
        monkeypatch, tmp_path, source, page, timestamp, expected_top100):
    rows = chart_capture("first", "2020-01-01T01:00:00Z", range(1, 51), source=source)
    rows += chart_capture("second", timestamp, range(51, 101), source=source, page=page)
    pd.DataFrame(rows).assign(slug="overall").to_parquet(tmp_path / "chart_rows.parquet")
    monkeypatch.setattr(analyze, "PARSED", tmp_path)
    monkeypatch.setattr(analyze, "SUMMARY", tmp_path / "summary")
    monkeypatch.setattr(analyze, "DB", tmp_path / "absent.db")
    monkeypatch.setattr(population, "PARSED", tmp_path)
    assert analyze.main() == 0
    daily = pd.read_csv(tmp_path / "summary/flagship_daily_snapshots.csv")
    assert daily.top100.tolist() == [expected_top100]
    assert daily.full_top100.tolist() == [expected_top100 == 100]
    assert len(population.trusted_days()) == (1 if expected_top100 == 100 else 0)
    assert len(pd.read_parquet(tmp_path / "flagship_us_overall.parquet")) == expected_top100


@pytest.mark.parametrize("success_at, expected_code, attempts", [(1, 0, 1), (3, 0, 3), (25, 1, 24)])
def test_cc_wrapper_reports_retry_exhaustion(monkeypatch, tmp_path, success_at, expected_code, attempts):
    root = Path(__file__).resolve().parents[2]
    runner = tmp_path / "analysis/chart_archive/run_cc_index.sh"
    runner.parent.mkdir(parents=True)
    runner.write_text((root / "analysis/chart_archive/run_cc_index.sh").read_text())
    python = tmp_path / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text('''#!/bin/sh
count=$(cat "$CHECK_COUNTER" 2>/dev/null || echo 0)
count=$((count + 1))
echo "$count" > "$CHECK_COUNTER"
[ "$count" -ge "$SUCCESS_AT" ]
''')
    python.chmod(0o755)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    sleep = fake_bin / "sleep"
    sleep.write_text('#!/bin/sh\necho sleep >> "$CHECK_SLEEPS"\n')
    sleep.chmod(0o755)
    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}",
               CHECK_COUNTER=str(tmp_path / "calls"), CHECK_SLEEPS=str(tmp_path / "sleeps"),
               SUCCESS_AT=str(success_at))
    result = subprocess.run(["bash", str(runner)], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode == expected_code
    assert int((tmp_path / "calls").read_text()) == attempts
    sleeps = (tmp_path / "sleeps").read_text().splitlines() if (tmp_path / "sleeps").exists() else []
    assert len(sleeps) == attempts - 1
    assert ("CC index complete" in result.stdout) == (expected_code == 0)
    if expected_code:
        assert "still incomplete after 24 attempts" in result.stderr


@pytest.mark.parametrize("name", ["analyze", "population", "within_month"])
def test_archive_modules_load_by_file_path_outside_repository(tmp_path, name):
    root = Path(__file__).resolve().parents[2]
    script = root / f"analysis/chart_archive/{name}.py"
    code = '''import importlib.util, sys
spec = importlib.util.spec_from_file_location("file_loaded_archive", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.load_canonical)
assert callable(module.select_daily)
'''
    result = subprocess.run([sys.executable, "-c", code, str(script)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
