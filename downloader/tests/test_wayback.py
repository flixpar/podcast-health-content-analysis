"""Wayback Machine recovery: the CDX client, capture selection, discover-archived,
and the download fallback. No network: sessions and the client are fakes."""

import json
import socket
import threading
import time
from email.utils import format_datetime
from datetime import datetime, timezone
from unittest.mock import Mock

import numpy as np
import pytest
import requests

from podcast_pipeline import db
from podcast_pipeline.archive import wayback
from podcast_pipeline.archive.wayback import (Capture, CdxError, Snapshot, WaybackClient, parse_cdx,
                                              url_identity)
from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.audio.download import (AudioDownloader, DownloadError, is_dead_link,
                                             unwrap_tracking_url)
from podcast_pipeline.audio.naming import episode_stem, podcast_dir
from podcast_pipeline.config import CompressionConfig, WaybackConfig
from podcast_pipeline.models import FeedEpisode, PodcastRecord
from podcast_pipeline.pipeline import discover_archived, download
from podcast_pipeline.pipeline.discover_archived import WindowTarget, next_capture

HEADER = ["timestamp", "original", "statuscode", "mimetype", "length", "digest"]


def cap(ts: str, original="http://old.host/feed", digest=None) -> Capture:
    ts = ts.ljust(14, "0")
    return Capture(ts, original, "200", "application/rss+xml", 1000, digest or f"D{ts}")


# --- CDX parsing and the client ------------------------------------------------------

def test_parse_cdx_reads_records_and_rejects_ambiguous_bodies():
    body = json.dumps([HEADER, ["20150402120000", "http://old.host/feed", "200", "text/xml", "1234", "ABC"],
                       ["20140101000000", "https://old.host/feed", "200", "text/xml", "-", "DEF"]])
    captures = parse_cdx(body)
    assert [c.timestamp for c in captures] == ["20150402120000", "20140101000000"]
    assert captures[0].day == "2015-04-02" and captures[0].length == 1234 and captures[1].length is None
    assert captures[1].original == "https://old.host/feed"
    assert parse_cdx("[]") == []                      # a real "never archived"
    assert parse_cdx("") is None                      # a dropped request looks like this
    assert parse_cdx("  \n") is None
    assert parse_cdx("<html>busy</html>") is None
    assert parse_cdx(json.dumps([["timestamp", "original"], ["20150402120000", "x"]])) is None
    assert parse_cdx(json.dumps([HEADER, ["2015", "x", "200", "t", "1", "d"]])) is None


def cdx_response(text: str, status=200):
    response = Mock()
    response.status_code = status
    response.text = text
    response.content = text.encode()
    return response


def make_client(tmp_path, cdx_session, sleeps=None, **cfg):
    config = WaybackConfig(cdx_delay_seconds=cfg.pop("delay", 0.0), cdx_backoff_seconds=1.0, **cfg)
    return WaybackClient(config, tmp_path / "wayback", session=Mock(), cdx_session=cdx_session,
                         sleep=(sleeps.append if sleeps is not None else time.sleep))


def test_empty_cdx_body_is_retried_not_trusted_and_only_valid_listings_are_cached(tmp_path):
    good = json.dumps([HEADER, ["20150402120000", "http://old.host/feed", "200", "text/xml", "10", "A"]])
    session = Mock()
    session.get.side_effect = [cdx_response(""), cdx_response("", status=503), cdx_response(good)]
    sleeps = []
    client = make_client(tmp_path, session, sleeps)
    captures = client.list_captures("http://old.host/feed")
    assert [c.timestamp for c in captures] == ["20150402120000"]
    assert session.get.call_count == 3
    assert 1.0 in sleeps and 2.0 in sleeps            # backoff doubles
    params = session.get.call_args.kwargs["params"]
    assert params["filter"] == "statuscode:200" and params["url"] == "http://old.host/feed"

    # Cached: no second request.
    assert client.list_captures("http://old.host/feed") == captures
    assert session.get.call_count == 3


def test_cdx_that_never_answers_raises_and_caches_nothing(tmp_path):
    session = Mock()
    session.get.return_value = cdx_response("")
    client = make_client(tmp_path, session, [], cdx_attempts=3)
    with pytest.raises(CdxError, match="3 attempts.*empty"):
        client.list_captures("http://old.host/feed")
    assert session.get.call_count == 3
    assert not (tmp_path / "wayback" / "cdx").exists() or not any((tmp_path / "wayback" / "cdx").iterdir())


def test_cdx_requests_are_sequential_and_paced_across_threads(tmp_path):
    lock = threading.Lock()
    state = {"active": 0, "max_active": 0, "starts": [], "ends": []}

    def get(url, params, timeout):
        with lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
            state["starts"].append(time.monotonic())
        time.sleep(0.01)
        with lock:
            state["active"] -= 1
            state["ends"].append(time.monotonic())
        return cdx_response("[]")

    session = Mock()
    session.get.side_effect = get
    client = make_client(tmp_path, session, delay=0.05)
    threads = [threading.Thread(target=client.list_captures, args=(f"http://host{i}/feed",)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert state["max_active"] == 1
    starts, ends = sorted(state["starts"]), sorted(state["ends"])
    assert all(start - end >= 0.045 for end, start in zip(ends, starts[1:]))
    assert client.cdx_requests == 6


def test_snapshot_fetch_uses_the_capture_url_as_captured_and_caches(tmp_path):
    import gzip
    response = Mock(status_code=200, content=gzip.compress(b"<rss/>"),
                    url="https://web.archive.org/web/20150402120000id_/http://old.host/feed?a=1")
    session = Mock()
    session.get.return_value = response
    client = WaybackClient(WaybackConfig(), tmp_path / "wb", session=session, cdx_session=Mock())
    capture = cap("20150402120000", original="http://old.host/feed?a=1")
    snapshot = client.fetch_snapshot(capture)
    assert session.get.call_args.args[0] == "https://web.archive.org/web/20150402120000id_/http://old.host/feed?a=1"
    assert snapshot.body == b"<rss/>" and snapshot.served_timestamp == "20150402120000"
    assert client.fetch_snapshot(capture).body == b"<rss/>"
    assert session.get.call_count == 1

    session.get.return_value = Mock(status_code=404, content=b"", url="x")
    with pytest.raises(wayback.SnapshotError, match="404"):
        client.fetch_snapshot(cap("20160101"))


# --- capture selection -----------------------------------------------------------------

def test_first_pick_is_the_earliest_capture_at_or_after_the_window_end():
    captures = [cap("20150215"), cap("20150320"), cap("20150405"), cap("20150601")]
    target = WindowTarget("2015-03", "2015-03-01", "2015-04-01")
    assert next_capture(target, captures, set(), set()).timestamp.startswith("20150405")


def test_short_feed_walks_back_into_the_window_then_stops():
    captures = [cap("20150215"), cap("20150310"), cap("20150320"), cap("20150405"), cap("20150601")]
    target = WindowTarget("2015-03", "2015-03-01", "2015-04-01")
    tried = set()
    first = next_capture(target, captures, tried, set())
    tried.add((first.timestamp, first.original))
    target.apply(first, "2015-03-25", picked_here=True)       # feed reaches back to the 25th
    second = next_capture(target, captures, tried, set())
    assert second.timestamp.startswith("20150320")             # earliest at/after the 25th? none before 0405 -> inside
    tried.add((second.timestamp, second.original))
    target.apply(second, "2015-03-12", picked_here=True)
    third = next_capture(target, captures, tried, set())
    assert third.timestamp.startswith("20150310")
    target.apply(third, "2015-02-20", picked_here=True)
    assert target.covered
    assert next_capture(target, captures, tried | {(third.timestamp, third.original)}, set()) is None


def test_selection_skips_later_captures_and_identical_bodies():
    # Later than a capture already used: lists newer items, can never help.
    captures = [cap("20150405"), cap("20150410", digest="SAME"), cap("20150420")]
    target = WindowTarget("2015-03", "2015-03-01", "2015-04-01")
    target.apply(captures[0], "2015-03-15", picked_here=True)
    tried = {(captures[0].timestamp, captures[0].original)}
    assert next_capture(target, captures, tried, set()) is None
    # A byte-identical body to one already fetched is skipped.
    fresh = WindowTarget("2015-03", "2015-03-01", "2015-04-01")
    assert next_capture(fresh, captures[1:], set(), {"SAME"}).timestamp.startswith("20150420")


# --- discover-archived end to end ---------------------------------------------------------

def rss(*items: tuple[str, str]) -> bytes:
    entries = "".join(
        f"<item><guid>{guid}</guid><title>{guid}</title>"
        f"<pubDate>{format_datetime(datetime.fromisoformat(day).replace(hour=12, tzinfo=timezone.utc))}</pubDate>"
        f"<enclosure url='https://cdn.old/{guid}.mp3' type='audio/mpeg' length='1'/></item>"
        for guid, day in items)
    return f"<?xml version='1.0'?><rss version='2.0'><channel><title>t</title>{entries}</channel></rss>".encode()


class FakeClient:
    def __init__(self, listings, bodies, on_list=None):
        self.listings, self.bodies, self.on_list = listings, bodies, on_list
        self.listed, self.fetched = [], []
        self.cdx_requests = 0

    def list_captures(self, url, refresh=False):
        self.listed.append((url, refresh))
        self.cdx_requests += 1
        if self.on_list:
            self.on_list(url)
        listing = self.listings[url]
        if isinstance(listing, Exception):
            raise listing
        return listing

    def fetch_snapshot(self, capture):
        self.fetched.append(capture.timestamp[:8])
        body = self.bodies[capture.timestamp[:8]]
        if isinstance(body, Exception):
            raise body
        return Snapshot(capture, capture.replay_url("https://web.archive.org/web"), body)


def add_study(conn, members: list[tuple[int, list[tuple[str, str, str]]]], name="s"):
    conn.execute("INSERT INTO studies (name, definition, definition_hash, refreshed_at) "
                 "VALUES (?, '{}', 'h', CURRENT_TIMESTAMP)", (name,))
    for podcast_id, windows in members:
        entity = f"podcast:{podcast_id}"
        conn.execute("INSERT INTO study_members (study, entity, podcast_id, name, scope) "
                     "VALUES (?, ?, ?, 'n', 'windows')", (name, entity, podcast_id))
        for label, start, end in windows:
            conn.execute("INSERT INTO study_windows (study, entity, label, start_date, end_date) "
                         "VALUES (?, ?, ?, ?, ?)", (name, entity, label, start, end))
    conn.commit()


def add_podcast(conn, n: int, rss_url: str, old_urls=()) -> int:
    pid = db.upsert_podcast(conn, PodcastRecord(f"apple_{n}", f"Show {n}", rss_url=rss_url,
                                                apple_podcasts_id=str(n)))
    for url in old_urls:
        db.record_feed_url(conn, pid, url, "manual")
    conn.commit()
    return pid


MARCH_APRIL = [("2015-03", "2015-03-01", "2015-04-01"), ("2015-04", "2015-04-01", "2015-05-01")]
OLD = "http://old.host/feed"
NEW = "https://new.host/feed"


@pytest.fixture
def archive(config, conn, monkeypatch):
    """A show that moved hosts: the old feed URL is archived through 2015, the new one never."""
    pid = add_podcast(conn, 1, NEW, old_urls=[OLD])
    other = add_podcast(conn, 2, "https://other/feed")
    db.insert_episode(conn, other, FeedEpisode("foreign-guid", "Elsewhere", "https://x/f.mp3"))
    db.insert_episode(conn, pid, FeedEpisode("ep-0424", "Live", "https://x/live.mp3",
                                             published_date="2015-04-24T12:00:00"))
    conn.commit()
    add_study(conn, [(pid, MARCH_APRIL)])
    listings = {OLD: [cap("20150101", OLD), cap("20150315", OLD), cap("20150402", OLD), cap("20150503", OLD)],
                NEW: []}
    bodies = {
        "20150101": rss(("ep-1201", "2014-12-01")),
        "20150315": rss(("ep-0313", "2015-03-13"), ("ep-0306", "2015-03-06"), ("ep-0227", "2015-02-27")),
        "20150402": rss(("ep-0401", "2015-04-01"), ("ep-0327", "2015-03-27"), ("ep-0320", "2015-03-20"),
                        ("foreign-guid", "2015-03-21")),
        "20150503": rss(("ep-0501", "2015-05-01"), ("ep-0424", "2015-04-24"), ("ep-0410", "2015-04-10")),
    }
    fake = FakeClient(listings, bodies)
    monkeypatch.setattr(discover_archived, "WaybackClient", lambda cfg, cache_dir: fake)
    return config, conn, pid, fake


def test_discover_archived_recovers_windows_with_provenance(archive):
    config, conn, pid, fake = archive
    result = discover_archived.run(config, conn, "s")

    # March: 0402 reaches back to 03-20, then 0315 (inside) to 02-27. April: 0503 reaches 04-10.
    assert sorted(fake.fetched) == ["20150315", "20150402", "20150503"]
    assert result["podcasts_probed"] == 1 and result["probes"] == {"ok": 1, "no_captures": 1, "error": 0}
    assert result["episodes_foreign_guid"] == 1
    assert result["episodes_new"] == 8                  # every parsed item, in a window or not
    assert result["episodes_found"] == 9                # + ep-0424, which we already held
    assert result["gap_windows_targeted"] == 2
    assert result["gap_windows_with_episodes_before"] == 1
    assert result["gap_windows_with_episodes_after"] == 2

    owner = dict(conn.execute("SELECT episode_guid, podcast_id FROM episodes").fetchall())
    assert owner["foreign-guid"] != pid and owner["ep-0227"] == pid and owner["ep-0501"] == pid
    refs = conn.execute("""
        SELECT es.ref FROM episode_sources es JOIN episodes e ON e.id = es.episode_id
        WHERE e.episode_guid = 'ep-0424' AND es.source = 'wayback_feed'
    """).fetchall()
    assert [r[0] for r in refs] == ["https://web.archive.org/web/20150503000000id_/http://old.host/feed"]
    assert conn.execute("""
        SELECT COUNT(*) FROM episode_sources es JOIN episodes e ON e.id = es.episode_id
        WHERE e.episode_guid = 'foreign-guid' AND es.source = 'wayback_feed'
    """).fetchone()[0] == 0

    probes = {r["url"]: r for r in conn.execute("SELECT * FROM wayback_probes")}
    assert probes[OLD]["status"] == "ok" and probes[OLD]["captures_listed"] == 4
    assert probes[OLD]["captures_fetched"] == 3 and probes[OLD]["episodes_new"] == 8
    assert json.loads(probes[OLD]["windows_targeted"]) == [["2015-03-01", "2015-04-01"],
                                                           ["2015-04-01", "2015-05-01"]]
    assert json.loads(probes[OLD]["detail"])["windows_unreached"] == ["2015-04"]
    assert probes[NEW]["status"] == "no_captures"


def test_probed_urls_are_skipped_unless_retry_and_errors_are_reprobed(archive):
    config, conn, pid, fake = archive
    fake.listings[NEW] = CdxError("CDX listing failed after 5 attempts: empty body")
    first = discover_archived.run(config, conn, "s")
    assert first["probes"] == {"ok": 1, "no_captures": 0, "error": 1}

    # Re-run: the ok URL covers the same windows and is skipped; the error one is retried.
    fake.listed.clear()
    fake.listings[NEW] = []
    second = discover_archived.run(config, conn, "s")
    assert fake.listed == [(NEW, False)] and second["probes"]["no_captures"] == 1

    # Now everything is probed: nothing to do.
    fake.listed.clear()
    third = discover_archived.run(config, conn, "s")
    assert fake.listed == [] and third["podcasts_already_probed"] == 1 and third["podcasts_probed"] == 0

    # --retry probes again, bypassing the CDX cache.
    fourth = discover_archived.run(config, conn, "s", retry=True)
    assert sorted(fake.listed) == sorted([(NEW, True), (OLD, True)]) and fourth["podcasts_probed"] == 1
    assert conn.execute("SELECT COUNT(*) FROM episodes WHERE podcast_id = ?", (pid,)).fetchone()[0] == 9


def test_another_feed_url_can_reach_back_where_the_old_one_could_not(archive):
    """A later capture of the *same* feed never reaches further back, but the
    show's new host may serve a much longer feed."""
    config, conn, pid, fake = archive
    fake.listings[NEW] = [cap("20200101", NEW)]
    fake.bodies["20200101"] = rss(("ep-0405", "2015-04-05"), ("ep-0402", "2015-04-02"), ("ep-0301", "2015-03-01"))
    result = discover_archived.run(config, conn, "s")
    assert "20200101" in fake.fetched
    detail = json.loads(conn.execute("SELECT detail FROM wayback_probes WHERE url = ?", (OLD,)).fetchone()[0])
    assert detail["windows_unreached"] == []
    assert result["probes"]["ok"] == 2


def test_url_identity_matches_cdx_canonicalization():
    assert url_identity("http://feeds.feedburner.com:80/themoth") == url_identity("https://feeds.feedburner.com/themoth")
    assert url_identity("https://www.x.com/feed?a=1") == "x.com/feed?a=1"
    assert url_identity("http://x.com:8080/feed") == "x.com:8080/feed"


def test_capture_cap_limits_fetches_per_podcast(archive):
    config, conn, pid, fake = archive
    config.wayback.max_captures_per_podcast = 1
    discover_archived.run(config, conn, "s")
    assert fake.fetched == ["20150402"]                  # the oldest window's first pick


def test_failed_snapshot_fetches_try_another_capture(archive):
    config, conn, pid, fake = archive
    fake.bodies["20150402"] = wayback.SnapshotError("HTTP 503")
    fake.listings[OLD].append(cap("20150404", OLD))
    fake.bodies["20150404"] = rss(("ep-0320", "2015-03-20"))
    discover_archived.run(config, conn, "s")
    assert "20150404" in fake.fetched
    detail = json.loads(conn.execute("SELECT detail FROM wayback_probes WHERE url = ?", (OLD,)).fetchone()[0])
    assert detail["capture_failures"][0]["timestamp"].startswith("20150402")

    # Not every chosen capture could be fetched, so the search is not complete:
    # the probe is an error and the next run tries again (and now succeeds).
    status = lambda: conn.execute("SELECT status FROM wayback_probes WHERE url = ?", (OLD,)).fetchone()[0]
    assert status() == "error"
    fake.listed.clear()
    fake.bodies["20150402"] = rss(("ep-0320", "2015-03-20"))
    discover_archived.run(config, conn, "s")
    assert (OLD, False) in fake.listed and status() == "ok"


def test_a_capture_that_is_not_a_feed_does_not_force_a_reprobe(archive):
    config, conn, pid, fake = archive
    fake.bodies["20150402"] = b"<html><body>Feed moved</body></html>"
    discover_archived.run(config, conn, "s")
    assert conn.execute("SELECT status FROM wayback_probes WHERE url = ?", (OLD,)).fetchone()[0] == "ok"


def three_podcasts(config, conn, monkeypatch, listing, on_list=None):
    members = []
    listings = {}
    for n in (1, 2, 3):
        url = f"https://host{n}/feed"
        members.append((add_podcast(conn, n, url), [(f"201{n}-01", f"201{n}-01-01", f"201{n}-02-01")]))
        listings[url] = listing
    add_study(conn, members)
    fake = FakeClient(listings, {}, on_list=on_list)
    monkeypatch.setattr(discover_archived, "WaybackClient", lambda cfg, cache_dir: fake)
    return fake


def test_budget_stops_starting_new_podcasts(config, conn, monkeypatch):
    clock = {"now": 0.0}
    monkeypatch.setattr(discover_archived, "monotonic", lambda: clock["now"])
    fake = three_podcasts(config, conn, monkeypatch, [],
                          on_list=lambda url: clock.__setitem__("now", clock["now"] + 90))
    result = discover_archived.run(config, conn, "s", budget_minutes=2)
    assert [u for u, _ in fake.listed] == ["https://host1/feed", "https://host2/feed"]
    assert result["stopped"] == "budget" and result["podcasts_probed"] == 2
    assert result["podcasts_not_reached"] == 1 and result["minutes_used"] == 3.0


def test_limit_counts_probed_podcasts(config, conn, monkeypatch):
    fake = three_podcasts(config, conn, monkeypatch, [])
    result = discover_archived.run(config, conn, "s", limit=1)
    assert len(fake.listed) == 1 and result["stopped"] == "limit" and result["podcasts_not_reached"] == 2


def test_consecutive_cdx_failures_stop_the_run(config, conn, monkeypatch):
    config.wayback.cdx_failure_limit = 2
    fake = three_podcasts(config, conn, monkeypatch, CdxError("failed after 5 attempts: empty body"))
    with pytest.raises(discover_archived.CdxUnavailableError, match="2 podcasts in a row"):
        discover_archived.run(config, conn, "s")
    assert len(fake.listed) == 2
    statuses = [r[0] for r in conn.execute("SELECT status FROM wayback_probes")]
    assert statuses == ["error", "error"]            # recorded and committed before stopping


# --- download fallback ---------------------------------------------------------------------

AUDIO = b"ID3" + b"\0" * (MIN_AUDIO_BYTES + 1000)


@pytest.fixture(autouse=True)
def decoded_seconds(monkeypatch):
    """What decoding a fallback file yields; the fake bodies are not real audio."""
    seconds = {"value": 3600}
    monkeypatch.setattr("podcast_pipeline.audio.download.decode_pcm",
                        lambda path, sample_rate: np.zeros(int(seconds["value"] * sample_rate), np.float32))
    return seconds


def http_response(url: str, body: bytes = b"", status=200, content_type="audio/mpeg"):
    response = Mock()
    response.url = url
    response.status_code = status
    response.headers = {"content-length": str(len(body)), "content-type": content_type}
    if status >= 400:
        response.raise_for_status = Mock(side_effect=requests.HTTPError(f"{status} Client Error", response=response))
    else:
        response.raise_for_status = Mock()
    response.iter_content = lambda chunk_size: (body[i:i + chunk_size] for i in range(0, len(body), chunk_size))
    return response


class FakeHttp:
    """Answers by URL prefix; records every URL requested."""

    def __init__(self, routes):
        self.routes, self.requested = routes, []

    def get(self, url, **kwargs):
        self.requested.append(url)
        for prefix, answer in self.routes.items():
            if url.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return answer(url)
        raise AssertionError(f"unexpected request {url}")


ARCHIVED = "https://web.archive.org/web/20150402093000id_/https://dead.host/ep.mp3"


def fallback_downloader(tmp_path, routes, enabled=True):
    session = FakeHttp(routes)
    dl = AudioDownloader(tmp_path, CompressionConfig(enabled=False), min_free_gb=0, session=session,
                         wayback_replay_url="https://web.archive.org/web" if enabled else None)
    return dl, session


def test_dead_enclosure_falls_back_to_wayback(tmp_path):
    dl, session = fallback_downloader(tmp_path, {
        "https://dead.host/": lambda url: http_response(url, status=404),
        "https://web.archive.org/web/20150401id_/": lambda url: http_response(ARCHIVED, AUDIO),
    })
    stale = podcast_dir(tmp_path, "Show") / f"{episode_stem('Ep 1', 'g')}.mp3.part"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"old bytes from the dead host")
    result = dl.download_episode("https://dead.host/ep.mp3", "Show", "Ep 1", "g",
                                 published_date="2015-04-01T12:00:00")
    assert session.requested == ["https://dead.host/ep.mp3",
                                 "https://web.archive.org/web/20150401id_/https://dead.host/ep.mp3"]
    assert (result.fallback_source, result.fallback_url) == ("wayback_audio", ARCHIVED)
    assert result.path.read_bytes() == AUDIO
    assert result.path == stale.with_suffix("")      # named exactly like a normal download
    assert not stale.exists() and not list(tmp_path.rglob("*.part"))


def test_fallback_failure_mentions_every_attempt(tmp_path):
    dl, _ = fallback_downloader(tmp_path, {
        "https://dead.host/": requests.ConnectionError("Failed to resolve 'dead.host'"),
        "https://web.archive.org/": lambda url: http_response(url, b"<html>" + b"x" * MIN_AUDIO_BYTES,
                                                              content_type="text/html"),
    })
    # A bare ConnectionError carries no DNS cause, so it is not a dead link: no fallback.
    with pytest.raises(DownloadError) as excinfo:
        dl.download_episode("https://dead.host/ep.mp3", "Show", "Ep 1", "g")
    assert "wayback" not in str(excinfo.value)

    dl, _ = fallback_downloader(tmp_path, {
        "https://dead.host/": lambda url: http_response(url, status=410),
        "https://web.archive.org/": lambda url: http_response(url, b"<html>" + b"x" * MIN_AUDIO_BYTES,
                                                              content_type="text/html"),
    })
    with pytest.raises(DownloadError) as excinfo:
        dl.download_episode("https://dead.host/ep.mp3", "Show", "Ep 1", "g", published_date=None)
    message = str(excinfo.value)
    assert "original https://dead.host/ep.mp3: request failed: 410" in message
    assert "wayback https://web.archive.org/web/2id_/https://dead.host/ep.mp3: not audio" in message
    assert not list(tmp_path.rglob("*.part")) and not list(tmp_path.rglob("*.mp3"))


def chained(outer: Exception, cause: Exception) -> Exception:
    try:
        try:
            raise cause
        except type(cause) as inner:
            raise outer from inner
    except type(outer) as e:
        return e


def test_dead_link_classification():
    assert is_dead_link(chained(requests.ConnectionError("Failed to resolve"),
                                socket.gaierror(-2, "Name or service not known")))
    assert is_dead_link(chained(requests.ConnectionError("Failed to connect"),
                                ConnectionRefusedError(111, "Connection refused")))
    assert not is_dead_link(requests.ConnectionError("reset by peer"))
    assert not is_dead_link(requests.ConnectTimeout("slow"))
    for status, dead in [(404, True), (410, True), (403, True), (451, True), (500, False), (429, False)]:
        response = Mock(status_code=status)
        assert is_dead_link(requests.HTTPError(str(status), response=response)) is dead


def test_fallback_off_or_transient_failure_does_not_touch_wayback(tmp_path):
    dl, session = fallback_downloader(tmp_path, {
        "https://dead.host/": lambda url: http_response(url, status=404)}, enabled=False)
    with pytest.raises(DownloadError, match="404"):
        dl.download_episode("https://dead.host/ep.mp3", "Show", "Ep 1", "g")
    assert session.requested == ["https://dead.host/ep.mp3"]

    dl, session = fallback_downloader(tmp_path, {
        "https://slow.host/": requests.ReadTimeout("read timed out")})
    with pytest.raises(DownloadError, match="timed out"):
        dl.download_episode("https://slow.host/ep.mp3", "Show", "Ep 1", "g")
    assert session.requested == ["https://slow.host/ep.mp3"]


def test_download_stage_records_fallback_provenance(config, conn, monkeypatch):
    pid = add_podcast(conn, 1, "https://feed")
    db.insert_episode(conn, pid, FeedEpisode("g1", "Ep 1", "https://dead.host/ep.mp3",
                                             published_date="2015-04-01T12:00:00"))
    db.insert_episode(conn, pid, FeedEpisode("g2", "Ep 2", "https://live.host/ep.mp3"))
    conn.commit()
    config.audio_compression.enabled = False
    config.download.min_free_gb = 0
    session = FakeHttp({
        "https://dead.host/": lambda url: http_response(url, status=404),
        "https://live.host/": lambda url: http_response(url, AUDIO),
        "https://web.archive.org/web/20150401id_/": lambda url: http_response(ARCHIVED, AUDIO),
    })
    monkeypatch.setattr("podcast_pipeline.audio.download.make_session", lambda **kw: session)

    result = download.run(config, conn, workers=1, wayback_fallback=True)
    assert result["downloaded"] == 2 and result["wayback_audio"] == 1 and result["failed"] == 0
    rows = conn.execute("""
        SELECT e.episode_guid, es.ref FROM episode_sources es JOIN episodes e ON e.id = es.episode_id
        WHERE es.source = 'wayback_audio'
    """).fetchall()
    assert [tuple(r) for r in rows] == [("g1", ARCHIVED)]
    assert conn.execute("SELECT status FROM episodes WHERE episode_guid = 'g1'").fetchone()[0] == "downloaded"


# --- tracking-prefix unwrapping ------------------------------------------------------------

@pytest.mark.parametrize("wrapped, inner", [
    ("https://dts.podtrac.com/redirect.mp3/traffic.libsyn.com/show/ep.mp3",
     "https://traffic.libsyn.com/show/ep.mp3"),
    # Nested: podtrac around chartable around libsyn; the query rides along.
    ("https://dts.podtrac.com/redirect.mp3/chtbl.com/track/AB12C/traffic.libsyn.com/secure/show/ep.mp3?dest-id=9",
     "https://traffic.libsyn.com/secure/show/ep.mp3?dest-id=9"),
    ("http://www.podtrac.com/pts/redirect.mp3/https://chrt.fm/track/9G7/pdst.fm/e/media.example.org/a/ep.mp3",
     "https://media.example.org/a/ep.mp3"),
    ("https://play.podtrac.com/npr-510289/edge1.pod.npr.org/anon.npr-podcasts/podcast/ep.mp3",
     "https://edge1.pod.npr.org/anon.npr-podcasts/podcast/ep.mp3"),
    ("https://mgln.ai/e/58/arttrk.com/p/ABCD/pfx.vpixl.com/xyz/cdn.host.fm/ep.m4a",
     "https://cdn.host.fm/ep.m4a"),
    ("https://pdst.fm/e/tracking.swap.fm/track/v9Uiw3bGr54f6BVZKSyc/pscrb.fm/rss/p/serve.castfire.com/"
     "audio/8208784/8208784_2026-04-13-035324.192.mp3?rssID=6066",
     "https://serve.castfire.com/audio/8208784/8208784_2026-04-13-035324.192.mp3?rssID=6066"),
])
def test_unwrap_tracking_url_peels_known_prefixes(wrapped, inner):
    assert unwrap_tracking_url(wrapped) == inner


@pytest.mark.parametrize("url", [
    "https://traffic.megaphone.fm/ABC123.mp3",                       # a host, not a wrapper
    "http://feedproxy.google.com/~r/themothpodcast/~5/Sj7qSMnl96U/ep.mp3",   # target not in the URL
    "https://unknown-tracker.example/track/X/traffic.libsyn.com/ep.mp3",
    "https://dts.podtrac.com/redirect.mp3/",                          # nothing inside
    "https://chtbl.com/track/ABC",                                    # no wrapped URL
])
def test_unwrap_tracking_url_leaves_everything_else_alone(url):
    assert unwrap_tracking_url(url) == url


WRAPPED = "https://dts.podtrac.com/redirect.mp3/dead-cdn.host/ep.mp3"
INNER = "https://dead-cdn.host/ep.mp3"


def test_fallback_tries_the_unwrapped_url_live_first(tmp_path):
    dl, session = fallback_downloader(tmp_path, {
        "https://dts.podtrac.com/": lambda url: http_response(url, status=404),
        INNER: lambda url: http_response(url, AUDIO),
    })
    result = dl.download_episode(WRAPPED, "Show", "Ep 1", "g", published_date="2015-04-01T12:00:00")
    assert session.requested == [WRAPPED, INNER]
    assert (result.fallback_source, result.fallback_url) == ("unwrapped_audio", INNER)


def test_fallback_order_ends_with_the_wayback_copy_of_the_unwrapped_url(tmp_path):
    archived_inner = "https://web.archive.org/web/20150401id_/" + INNER
    dl, session = fallback_downloader(tmp_path, {
        "https://dts.podtrac.com/": lambda url: http_response(url, status=404),
        INNER: requests.ConnectionError("reset"),
        "https://web.archive.org/web/20150401id_/https://dts": lambda url: http_response(url, status=404),
        archived_inner: lambda url: http_response(url, AUDIO),
    })
    result = dl.download_episode(WRAPPED, "Show", "Ep 1", "g", published_date="2015-04-01T12:00:00")
    assert session.requested == [WRAPPED, INNER, "https://web.archive.org/web/20150401id_/" + WRAPPED,
                                 archived_inner]
    assert (result.fallback_source, result.fallback_url) == ("wayback_audio", archived_inner)

    dl, _ = fallback_downloader(tmp_path, {
        "https://dts.podtrac.com/": lambda url: http_response(url, status=404),
        INNER: requests.ConnectionError("reset"),
        "https://web.archive.org/": lambda url: http_response(url, status=404),
    })
    with pytest.raises(DownloadError) as excinfo:
        dl.download_episode(WRAPPED, "Show", "Ep 2", "g2", published_date="2015-04-01")
    message = str(excinfo.value)
    for attempt in (f"original {WRAPPED}", f"unwrapped {INNER}", "wayback https://web.archive.org/web/",
                    f"wayback unwrapped {archived_inner}"):
        assert attempt in message


def test_one_wayback_feed_row_per_episode_and_feed(archive):
    config, conn, pid, fake = archive
    # ep-0320 is listed by two captures of the same feed.
    fake.bodies["20150315"] = rss(("ep-0320", "2015-03-20"), ("ep-0313", "2015-03-13"), ("ep-0227", "2015-02-27"))

    def refs(guid):
        return [r[0] for r in conn.execute("""
            SELECT es.ref FROM episode_sources es JOIN episodes e ON e.id = es.episode_id
            WHERE e.episode_guid = ? AND es.source = 'wayback_feed'""", (guid,))]

    discover_archived.run(config, conn, "s")
    assert refs("ep-0320") == ["https://web.archive.org/web/20150315000000id_/http://old.host/feed"]
    # A later run (here: --retry) adds nothing for a feed the episode already has a row for.
    total = conn.execute("SELECT COUNT(*) FROM episode_sources WHERE source = 'wayback_feed'").fetchone()[0]
    discover_archived.run(config, conn, "s", retry=True)
    assert conn.execute("SELECT COUNT(*) FROM episode_sources WHERE source = 'wayback_feed'").fetchone()[0] == total
    detail = json.loads(conn.execute("SELECT detail FROM wayback_probes WHERE url = ?", (OLD,)).fetchone()[0])
    assert len(detail["captures_used"]) == 3


def test_truncated_fallback_audio_is_rejected_and_the_next_source_tried(tmp_path, monkeypatch):
    archived_inner = "https://web.archive.org/web/20150401id_/" + INNER
    durations = [1000, 3500]            # the first Wayback copy is truncated, the second is whole
    monkeypatch.setattr("podcast_pipeline.audio.download.decode_pcm",
                        lambda path, sample_rate: np.zeros(durations.pop(0) * sample_rate, np.float32))
    dl, session = fallback_downloader(tmp_path, {
        "https://dts.podtrac.com/": lambda url: http_response(url, status=404),
        INNER: lambda url: http_response(url, status=404),
        "https://web.archive.org/": lambda url: http_response(url, AUDIO),
    })
    result = dl.download_episode(WRAPPED, "Show", "Ep 1", "g", published_date="2015-04-01",
                                 declared_duration=3600)
    assert (result.fallback_source, result.fallback_url) == ("wayback_audio", archived_inner)

    durations[:] = [1000, 1000]
    with pytest.raises(DownloadError, match="truncated: decodes to 1000s of 3600s declared"):
        dl.download_episode(WRAPPED, "Show", "Ep 2", "g2", published_date="2015-04-01",
                            declared_duration=3600)
    assert not list(tmp_path.rglob("ep-2*"))
    # Without a declared duration, any file that decodes is accepted.
    durations[:] = [1000]
    assert dl.download_episode(WRAPPED, "Show", "Ep 3", "g3").fallback_source == "wayback_audio"


def test_dead_link_check_tolerates_string_reasons():
    # An SSL hostname mismatch: the chain holds an exception whose ``reason``
    # is a str. Not a dead link -- and it must not crash the classifier.
    class Mismatch(Exception):
        reason = "hostname 'podcast.thisamericanlife.org' doesn't match"
    error = requests.ConnectionError(Mismatch("cert"))
    assert not is_dead_link(error)


@pytest.mark.parametrize("wrapped, inner", [
    ("https://claritaspod.com/measure/dts.podtrac.com/redirect.mp3/mgln.ai/e/1124/prfx.byspotify.com/e/"
     "arttrk.com/p/MRWRK/pscrb.fm/rss/p/traffic.libsyn.com/secure/show/371.mp3",
     "https://traffic.libsyn.com/secure/show/371.mp3"),
    ("https://arttrk.com/p/ABMA5/clrtpod.com/m/pscrb.fm/rss/p/prfx.byspotify.com/e/dts.podtrac.com/"
     "redirect.mp3/audioboom.com/posts/8565991.mp3?modified=1&source=rss",
     "https://audioboom.com/posts/8565991.mp3?modified=1&source=rss"),
    ("https://dts.podtrac.com/redirect.mp3/pdrl.fm/c52dde/tracking.swap.fm/track/sblTq/mgln.ai/e/48/"
     "dovetail.prxu.org/59/x/1307_A.mp3", "https://dovetail.prxu.org/59/x/1307_A.mp3"),
    ("https://dts.podtrac.com/redirect.mp3/media.blubrry.com/reveal/tracking.swap.fm/track/sbl/"
     "dovetail.prxu.org/149/y/1123_Reveal.mp3", "https://dovetail.prxu.org/149/y/1123_Reveal.mp3"),
    ("https://chrt.fm/track/53A61E/pdst.fm/e/dts.podtrac.com/pts/redirect.mp3/waaa.wnyc.org/e/128/default.mp3?aid=rss",
     "https://waaa.wnyc.org/e/128/default.mp3?aid=rss"),
    ("https://p.podderapp.com/1226842767/pscrb.fm/rss/p/prefix.up.audio/s/stitcher.simplecastaudio.com/e/default.mp3",
     "https://stitcher.simplecastaudio.com/e/default.mp3"),
    ("https://pdst.fm/e/pscrb.fm/rss/p/s.gum.fm/s-5fe37a10f0786e0025359373/traffic.megaphone.fm/LEW1.mp3?updated=1",
     "https://traffic.megaphone.fm/LEW1.mp3?updated=1"),
    ("https://www.claritaspod.com/measure/op3.dev/e/rss.art19.com/episodes/abc.mp3?rss_browser=x",
     "https://rss.art19.com/episodes/abc.mp3?rss_browser=x"),
    ("https://op3.dev/e,pg=f00/https://cdn.example.org/ep.mp3", "https://cdn.example.org/ep.mp3"),
    ("https://pdcn.co/e/afp-973833-injected.calisto.simplecastaudio.com/x/default.mp3?aid=rss",
     "https://afp-973833-injected.calisto.simplecastaudio.com/x/default.mp3?aid=rss"),
    ("https://verifi.podscribe.com/rss/p/traffic.libsyn.com/secure/jbpod/01.mp3?dest-id=1",
     "https://traffic.libsyn.com/secure/jbpod/01.mp3?dest-id=1"),
])
def test_unwrap_handles_prefixes_found_in_the_study(wrapped, inner):
    assert unwrap_tracking_url(wrapped) == inner
