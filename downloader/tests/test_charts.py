"""Chart history: chart ids, the archive import, and the daily live capture.

The archive is a tiny synthetic parquet in parse.py's column layout; the
network is a fake session injected at ``capture.make_session``.
"""

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from podcast_pipeline import db
from podcast_pipeline.charts import archive_import, capture, keys

POPULATION = Path(__file__).resolve().parents[2] / "analysis" / "chart_archive" / "population.py"


# --- chart ids -------------------------------------------------------------------

@pytest.mark.parametrize("source, unit, chart, region, genre, expected", [
    # the flagship, from every source that carries it
    ("podbay", "podcast", "all-podcasts", "us", "all-podcasts", ("podbay", "apple:us:podcast:all")),
    ("chartable_itunes", "podcast", "us-all-podcasts-podcasts", "us", "all-podcasts",
     ("chartable_itunes", "apple:us:podcast:all")),
    ("apple_charts_page", "podcast", "Top Shows", "us", "All Podcasts",
     ("apple_charts_page", "apple:us:podcast:all")),
    ("itunes_rss", "podcast", "us_rss_toppodcasts_limit=300_xml", "us", "All Podcasts",
     ("itunes_rss", "apple:us:podcast:all")),
    # other Apple-page shelves are other charts
    ("apple_charts_page", "episode", "Top Episodes", "us", "All Podcasts",
     ("apple_charts_page", "apple:us:episode:all")),
    ("apple_charts_page", "episode", "Trending Episodes", "us", "True Crime",
     ("apple_charts_page", "apple:us:trending_episode:true-crime")),
    ("apple_charts_page", "podcast", "Top Subscriber Shows", "us", "All Podcasts",
     ("apple_charts_page", "apple:us:subscriber_podcast:all")),
    ("apple_charts_page", "channel", "Top Subscriber Channels", "us", "All Podcasts",
     ("apple_charts_page", "apple:us:channel:all")),
    ("apple_charts_page", "podcast", "Top Shows", "us", "Health & Fitness",
     ("apple_charts_page", "apple:us:podcast:health-fitness")),
    # genres are slugs; podbay's "-and-" spelling folds to the same slug
    ("podbay", "podcast", "news-and-politics", "us", "news-and-politics",
     ("podbay", "apple:us:podcast:news-politics")),
    ("podbay", "podcast", "comedy_itunes", "us", "comedy_itunes",
     ("podbay_itunes", "apple:us:podcast:comedy")),
    # Chartable: episodes mislabelled 'podcast' by parse.py, uuid twins, bestsellers
    ("chartable_itunes", "podcast", "us-history-podcasts-d6c80344-54b8-46a0-b652-00831b7a06be",
     "us", "history", ("chartable_itunes", "apple:us:podcast:history-d6c80344")),
    ("chartable_itunes", "podcast", "us-tech-news-episodes-6f99d1cb-af1a-477c-ad94-81b5a94410d3",
     "us", "tech-news", ("chartable_itunes", "apple:us:episode:tech-news-6f99d1cb")),
    ("chartable_itunes", "podcast", "us-politics-all-time-bestsellers", "", "x",
     ("chartable_itunes", "apple:us:bestseller_podcast:politics")),
    # Chartable reach is Chartable's own chart, not Apple's
    ("chartable_reach", "podcast", "podcast-us-all-podcasts-reach", "us", "all-podcasts",
     ("chartable_reach", "chartable:us:podcast:all")),
    ("chartable_reach", "podcast", "podcasts-usa-all-podcasts-trending", "", "x",
     ("chartable_reach", "chartable:us:trending_podcast:all")),
    ("chartable_reach", "podcast", "", "", "", ("chartable_reach", "chartable:default:podcast:all")),
    # Spotify shows are podcasts
    ("spotify_api", "show", "top", "us", "top", ("spotify_api", "spotify:us:podcast:all")),
    ("spotify_api", "show", "top-podcasts", "us", "top-podcasts",
     ("spotify_api", "spotify:us:podcast:all")),
    ("spotify_api", "episode", "top-episodes", "gb", "top-episodes",
     ("spotify_api", "spotify:gb:episode:all")),
    ("spotify_api", "show", "trending", "us", "trending",
     ("spotify_api", "spotify:us:trending_podcast:all")),
    ("chartable_spotify", "podcast", "united-states-of-america-top-podcasts", "us", "top-podcasts",
     ("chartable_spotify", "spotify:us:podcast:all")),
    ("chartable_spotify", "podcast", "hungaria-top-podcasts", "", "x",
     ("chartable_spotify", "spotify:hu:podcast:all")),
    # itunes_rss variants must not collide with the main chart
    ("itunes_rss", "podcast", "us_rss_toppodcasts_limit=10_explicit=true_xml", "us", "All Podcasts",
     ("itunes_rss", "apple:us:explicit_podcast:all")),
    ("itunes_rss", "podcast", "WebObjects_MZStoreServices.woa_ws_RSS_toppodcasts_sf=143442_limit=300_genre=1310_xml",
     "us", "Music", ("itunes_rss", "apple:fr:podcast:music")),
    ("itunes_rss", "podcast", "us_rss_toppodcasts_limit=300_genre=1311_xml", "us", "1311",
     ("itunes_rss", "apple:us:podcast:news-politics")),
    ("itunes_rss", "podcast", "us_rss_toppodcasts_limit_5Cx3d100_genre_5Cx3d1315_explicit_5Cx3dtrue_xml",
     "us", "All Podcasts", ("itunes_rss", "apple:us:explicit_podcast:science-medicine")),
    ("itunes_rss", "episode", "api_v2_us_podcasts_top_10_podcast-episodes.rss", "us", "All Podcasts",
     ("itunes_rss", "apple:us:episode:all")),
])
def test_archive_chart_ids(source, unit, chart, region, genre, expected):
    assert keys.archive_chart(source, unit, chart, region or None, genre) == expected


@pytest.mark.parametrize("source, chart, genre", [
    ("podbay", "SOCIALMEDIA", "SOCIALMEDIA"),       # URL artifact serving the overall chart
    ("itunes_rss", "WebObjects_MZStoreServices.woa_ws_RSS_toppodcasts_sf=_limit=5_explicit=true_xml",
     "All Podcasts"),
    ("apple_charts_page", "Top Something New", "All Podcasts"),
])
def test_unmappable_charts_are_refused(source, chart, genre):
    with pytest.raises(keys.Unmapped):
        keys.archive_chart(source, "podcast", chart, "us", genre)


def test_live_chart_ids():
    assert keys.live_chart("apple_marketing_tools", "us") == "apple:us:podcast:all"
    assert keys.live_chart("spotify_api", "us") == "spotify:us:podcast:all"


@pytest.mark.parametrize("name", ["The Joe Rogan Experience", "WNYC's Radiolab", "Ológica: 99%",
                                  "!!!", "", None, "Crime Junkie "])
def test_title_key_matches_population(name):
    if not POPULATION.exists():
        pytest.skip("analysis/chart_archive not present")
    spec = importlib.util.spec_from_file_location("population", POPULATION)
    population = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(population)
    assert keys.title_key(name) == population.key(name)


# --- archive import ----------------------------------------------------------------

def row(source, chart, genre, rank, captured_at, *, unit="podcast", platform="apple",
        region="us", name=None, entity_id=None, path=None, archive="wayback"):
    return {"source": source, "platform": platform, "unit": unit, "chart": chart,
            "region": region, "genre": genre, "rank": rank,
            "name": name or f"Show {rank}", "publisher": "Pub", "entity_id": entity_id,
            "entity_url": None, "captured_at": captured_at,
            "capture_ts": captured_at[:19].replace("-", "").replace(":", "").replace("T", ""),
            "slug": chart, "path": path or f"raw/{source}/{captured_at}.html.gz",
            "archive": archive, "page": None, "rank_move": None}


def podbay_day(date, ranks, hour="10", archive="wayback"):
    at = f"{date}T{hour}:00:00+00:00"
    return [row("podbay", "all-podcasts", "all-podcasts", r, at, entity_id=str(1000 + r),
                path=f"raw/podbay/browse/{date}{hour}.html.gz", archive=archive) for r in ranks]


def write_archive(tmp_path, rows, cc_rows=()):
    parsed = tmp_path / "archive" / "parsed"
    parsed.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(parsed / "chart_rows.parquet", index=False)
    if cc_rows:
        pd.DataFrame(list(cc_rows)).to_parquet(parsed / "chart_rows_cc.parquet", index=False)
    return tmp_path / "archive"


def snapshot(conn, source, chart, day):
    return conn.execute("SELECT * FROM chart_snapshots WHERE source = ? AND chart = ? "
                        "AND captured_on = ?", (source, chart, day)).fetchone()


def entries(conn, snapshot_id):
    return {r["rank"]: dict(r) for r in conn.execute(
        "SELECT * FROM chart_entries WHERE snapshot_id = ? ORDER BY rank", (snapshot_id,))}


def test_same_day_captures_merge_and_earliest_rank_wins(tmp_path, config, conn):
    day = "2016-05-01"
    early = [row("chartable_itunes", "us-all-podcasts-podcasts", "all-podcasts", r,
                 f"{day}T08:00:00+00:00", entity_id=f"slug-{r}", name=f"Early {r}",
                 path="raw/chartable/p1-early.html.gz") for r in (1, 2, 3)]
    late = [row("chartable_itunes", "us-all-podcasts-podcasts", "all-podcasts", r,
                f"{day}T20:00:00+00:00", entity_id=f"slug-{r}", name=f"Late {r}",
                path="raw/chartable/p2-late.html.gz") for r in (2, 3, 4, 6)]
    # the late page is listed first in the file: order in the file must not matter
    archive = write_archive(tmp_path, late + early)
    summary = archive_import.run(config, conn, archive_dir=archive)

    snap = snapshot(conn, "chartable_itunes", "apple:us:podcast:all", day)
    assert snap["captured_at"] == f"{day}T08:00:00+00:00"
    assert snap["raw_path"] == "raw/chartable/p1-early.html.gz"
    assert (snap["depth"], snap["n_entries"], snap["complete_to"]) == (6, 5, 4)
    assert snap["origin"] == "wayback" and snap["trusted"] == 1
    got = entries(conn, snap["id"])
    assert [got[r]["name"] for r in (1, 2, 3, 4, 6)] == ["Early 1", "Early 2", "Early 3",
                                                         "Late 4", "Late 6"]
    assert got[2]["apple_id"] is None and got[2]["source_entity_id"] == "slug-2"   # Chartable slug
    assert got[2]["title_key"] == "early2"
    assert summary["entries"] == 5 and summary["rows_merged_away"] == 2


def test_origin_ids_and_skips(tmp_path, config, conn):
    rows = (podbay_day("2015-01-01", [1, 2])
            + [row("apple_charts_page", "Top Episodes", "All Podcasts", 1, "2025-01-01T00:00:00+00:00",
                   unit="episode", entity_id="1000665759196"),
               row("spotify_api", "top", "top", 1, "2024-01-01T00:00:00+00:00", unit="show",
                   platform="spotify", entity_id="spotify:show:AAA"),
               row("podbay", "SOCIALMEDIA", "SOCIALMEDIA", 1, "2016-07-10T00:00:00+00:00",
                   entity_id="5")])
    cc = podbay_day("2015-01-02", [1], archive="commoncrawl")
    summary = archive_import.run(config, conn, archive_dir=write_archive(tmp_path, rows, cc))

    pb = snapshot(conn, "podbay", "apple:us:podcast:all", "2015-01-01")
    assert entries(conn, pb["id"])[1]["apple_id"] == "1001"
    assert snapshot(conn, "podbay", "apple:us:podcast:all", "2015-01-02")["origin"] == "common_crawl"
    ep = snapshot(conn, "apple_charts_page", "apple:us:episode:all", "2025-01-01")
    assert entries(conn, ep["id"])[1]["apple_id"] is None          # an episode id, not a show
    assert entries(conn, ep["id"])[1]["source_entity_id"] == "1000665759196"
    sp = snapshot(conn, "spotify_api", "spotify:us:podcast:all", "2024-01-01")
    assert entries(conn, sp["id"])[1]["source_entity_id"] == "AAA"
    assert summary["rows_skipped"] == 1
    [(reason, n)] = summary["skipped"].items()
    assert "non-genre URL" in reason and n == 1


def test_distrusted_chartable_days(tmp_path, config, conn):
    rows = [row("chartable_itunes", "us-all-podcasts-podcasts", "all-podcasts", r,
                f"{day}T12:00:00+00:00", entity_id=f"s{r}")
            for day in ("2024-12-05", "2024-12-06") for r in (1, 2)]
    rows += [row("chartable_itunes", "us-politics-podcasts", "politics", 1,
                 "2024-12-06T12:00:00+00:00", entity_id="s1")]
    archive_import.run(config, conn, archive_dir=write_archive(tmp_path, rows))
    bad = snapshot(conn, "chartable_itunes", "apple:us:podcast:all", "2024-12-06")
    assert bad["trusted"] == 0 and "DISTRUSTED" in bad["note"]
    assert snapshot(conn, "chartable_itunes", "apple:us:podcast:all", "2024-12-05")["trusted"] == 1
    assert snapshot(conn, "chartable_itunes", "apple:us:podcast:politics", "2024-12-06")["trusted"] == 1


def test_reimport_is_idempotent_and_leaves_live_rows(tmp_path, config, conn):
    live_at = datetime(2015, 1, 2, 12, tzinfo=timezone.utc)
    capture.write_snapshot(conn, "apple_marketing_tools", "apple:us:podcast:all", live_at,
                           [capture.Entry(1, "Live Show", "Pub", apple_id="42")], "raw.json")
    # an archive snapshot that collides with a live one is skipped, not merged
    capture.write_snapshot(conn, "spotify_api", "spotify:us:podcast:all", live_at,
                           [capture.Entry(1, "Live Spotify", "Pub", source_entity_id="LIVE")],
                           "raw2.json")
    conn.commit()
    rows = podbay_day("2015-01-01", range(1, 4)) + [
        row("spotify_api", "top", "top", 1, "2015-01-02T08:00:00+00:00", unit="show",
            platform="spotify", entity_id="spotify:show:OLD")]
    archive = write_archive(tmp_path, rows)

    first = archive_import.run(config, conn, archive_dir=archive)
    second = archive_import.run(config, conn, archive_dir=archive)
    assert first["snapshots"] == second["snapshots"] == 1
    assert second["replaced"] == {"snapshots": 1, "entries": 3}
    assert "live capture exists" in next(iter(second["skipped"]))
    counts = conn.execute("SELECT origin, COUNT(*) FROM chart_snapshots GROUP BY origin").fetchall()
    assert dict(map(tuple, counts)) == {"live": 2, "wayback": 1}
    assert conn.execute("SELECT COUNT(*) FROM chart_entries").fetchone()[0] == 3 + 2
    live = snapshot(conn, "spotify_api", "spotify:us:podcast:all", "2015-01-02")
    assert live["origin"] == "live" and entries(conn, live["id"])[1]["source_entity_id"] == "LIVE"


def test_trusted_flagship_days_rules(tmp_path, config, conn):
    page = lambda day, depth: [row("apple_charts_page", "Top Shows", "All Podcasts", r,  # noqa: E731
                                   f"{day}T00:00:00+00:00", entity_id=str(r))
                               for r in range(1, depth + 1)]
    rows = (podbay_day("2016-01-01", range(1, 96))       # 95 of 100: usable
            + podbay_day("2016-01-02", range(1, 95))     # 94: not
            + page("2016-01-01", 24)                     # same day as podbay: podbay wins
            + page("2016-01-03", 24) + page("2016-01-04", 23))
    archive_import.run(config, conn, archive_dir=write_archive(tmp_path, rows))
    assert archive_import.trusted_flagship_days(conn) == [
        ("2016-01-01", "podbay"), ("2016-01-03", "apple_charts_page")]


# --- live capture --------------------------------------------------------------------

APPLE_FEED = {"feed": {"title": "Top Shows", "results": [
    {"id": "1200361736", "name": "The Daily", "artistName": "The New York Times",
     "url": "https://podcasts.apple.com/us/podcast/the-daily/id1200361736",
     "genres": [{"genreId": "1489", "name": "News"}]},
    {"id": "360084272", "name": "The Joe Rogan Experience", "artistName": "Joe Rogan",
     "url": "https://podcasts.apple.com/us/podcast/id360084272", "genres": []},
    {"id": "999", "name": "Gone From Lookup", "artistName": "Nobody", "url": None, "genres": []},
]}}
SPOTIFY_CHART = [
    {"showUri": "spotify:show:ROGAN", "showName": "The Joe Rogan Experience",
     "showPublisher": "Joe Rogan"},
    {"showUri": "spotify:show:EXCL", "showName": "A Spotify Exclusive", "showPublisher": "Spotify"},
]


class FakeResponse:
    def __init__(self, payload, status=200):
        self.content = json.dumps(payload).encode()
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise capture.requests.HTTPError(f"{self.status_code}")


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        for fragment, response in self.routes.items():
            if fragment in url:
                if isinstance(response, Exception):
                    raise response
                return response
        raise AssertionError(f"unexpected URL {url}")


@pytest.fixture
def fake_net(monkeypatch):
    def install(apple=APPLE_FEED, spotify=SPOTIFY_CHART, lookup=None):
        session = FakeSession({"marketingtools": apple if isinstance(apple, Exception)
                               else FakeResponse(apple),
                               "byspotify": spotify if isinstance(spotify, Exception)
                               else FakeResponse(spotify)})
        monkeypatch.setattr(capture, "make_session", lambda: session)
        asked = []

        def fake_lookup(sess, ids, batch_size, delay):
            asked.append(list(ids))
            return {i: d for i, d in (lookup or {}).items() if i in ids}
        monkeypatch.setattr(capture.apple, "lookup_many", fake_lookup)
        return session, asked
    return install


def at(hour, minute=0):
    return lambda: datetime(2026, 10, 2, hour, minute, 5, tzinfo=timezone.utc)


def test_capture_writes_raw_files_and_replaces_same_day(config, conn, fake_net, monkeypatch):
    session, _ = fake_net()
    monkeypatch.setattr(capture, "_now", at(9))
    first = capture.run(config, conn, catalog=False)
    assert first["failed"] == {}
    assert session.calls[1][1] == {"region": "us"}
    raw = config.chart_capture_dir / "apple_marketing_tools" / "2026-10-02T090005Z.json"
    assert json.loads(raw.read_bytes()) == APPLE_FEED
    assert (config.chart_capture_dir / "spotify_api" / "2026-10-02T090005Z.json").exists()

    monkeypatch.setattr(capture, "_now", at(15))
    second = capture.run(config, conn, catalog=False)
    assert second["captured"]["spotify_api"]["replaced"] is True
    snaps = conn.execute("SELECT * FROM chart_snapshots ORDER BY source").fetchall()
    assert [(s["source"], s["chart"], s["origin"], s["captured_at"]) for s in snaps] == [
        ("apple_marketing_tools", "apple:us:podcast:all", "live", "2026-10-02T15:00:05+00:00"),
        ("spotify_api", "spotify:us:podcast:all", "live", "2026-10-02T15:00:05+00:00")]
    assert (snaps[0]["depth"], snaps[0]["n_entries"], snaps[0]["complete_to"]) == (3, 3, 3)
    assert snaps[0]["raw_path"] == "charts/raw/apple_marketing_tools/2026-10-02T150005Z.json"
    apple_rows = entries(conn, snaps[0]["id"])
    assert apple_rows[1]["apple_id"] == "1200361736" and apple_rows[1]["title_key"] == "thedaily"
    assert entries(conn, snaps[1]["id"])[2]["source_entity_id"] == "EXCL"
    assert conn.execute("SELECT COUNT(*) FROM chart_entries").fetchone()[0] == 5
    # both responses of the day are kept
    assert len(list((config.chart_capture_dir / "apple_marketing_tools").iterdir())) == 2
    assert conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0] == 0     # catalog=False


def test_capture_catalog_adds_apple_and_links_spotify(config, conn, fake_net, monkeypatch):
    from podcast_pipeline.models import PodcastRecord
    existing = db.upsert_podcast(conn, PodcastRecord(
        source_id="apple_360084272", title="The Joe Rogan Experience",
        apple_podcasts_id="360084272", spotify_id="ROGAN", rss_url="https://feeds/rogan"))
    conn.commit()
    lookup = {"1200361736": {"collectionId": 1200361736, "collectionName": "The Daily",
                             "artistName": "The New York Times",
                             "feedUrl": "https://feeds/daily", "genres": ["News"]}}
    _, asked = fake_net(lookup=lookup)
    monkeypatch.setattr(capture, "_now", at(9))
    summary = capture.run(config, conn)

    assert asked == [["1200361736", "999"]]          # only ids the catalog lacks
    assert summary["captured"]["apple_marketing_tools"]["catalog"] == {
        "seen": 3, "added": 2, "already_known": 1, "added_without_feed": 1}
    assert summary["captured"]["spotify_api"]["catalog"] == {
        "seen": 2, "linked": 1, "not_in_catalog": 1}
    daily = conn.execute("SELECT * FROM podcasts WHERE apple_podcasts_id = '1200361736'").fetchone()
    assert daily["rss_url"] == "https://feeds/daily" and daily["podchaser_id"] == "apple_1200361736"
    gone = conn.execute("SELECT * FROM podcasts WHERE apple_podcasts_id = '999'").fetchone()
    assert gone["title"] == "Gone From Lookup" and gone["rss_url"] is None
    feeds = conn.execute("SELECT podcast_id, url, source FROM podcast_feeds "
                         "WHERE source = 'itunes_lookup'").fetchall()
    assert [tuple(f) for f in feeds] == [(daily["id"], "https://feeds/daily", "itunes_lookup")]
    sources = conn.execute("SELECT podcast_id, ref, detail FROM podcast_sources "
                           "WHERE source = 'chart_capture' ORDER BY podcast_id, ref").fetchall()
    assert [(s["podcast_id"], s["ref"]) for s in sources] == sorted([
        (existing, "apple:us:podcast:all"), (existing, "spotify:us:podcast:all"),
        (daily["id"], "apple:us:podcast:all"), (gone["id"], "apple:us:podcast:all")])
    assert json.loads(sources[0]["detail"])["captured_on"] == "2026-10-02"
    # Spotify-only shows are not added to the catalog
    assert conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0] == 3


def test_failing_source_is_recorded_others_still_captured(config, conn, fake_net, monkeypatch):
    fake_net(spotify=capture.requests.ConnectionError("down"))
    monkeypatch.setattr(capture, "_now", at(9))
    with pytest.raises(capture.ChartCaptureError, match="spotify_api"):
        capture.run(config, conn, catalog=False)
    rows = conn.execute("SELECT source FROM chart_snapshots").fetchall()
    assert [r["source"] for r in rows] == ["apple_marketing_tools"]


def test_unexpected_payload_is_a_source_failure(config, conn, fake_net, monkeypatch):
    fake_net(spotify={"error": "maintenance"})
    monkeypatch.setattr(capture, "_now", at(9))
    with pytest.raises(capture.ChartCaptureError, match="ChartSourceError"):
        capture.run(config, conn, catalog=False)
    # the odd response is still kept, and Apple's chart was recorded
    assert (config.chart_capture_dir / "spotify_api" / "2026-10-02T090005Z.json").exists()
    assert conn.execute("SELECT COUNT(*) FROM chart_snapshots").fetchone()[0] == 1


def test_disk_error_writing_raw_file_propagates(config, conn, fake_net, monkeypatch):
    session, _ = fake_net()
    monkeypatch.setattr(capture, "_now", at(9))

    def full_disk(*args):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(capture, "save_raw", full_disk)
    with pytest.raises(OSError, match="No space left"):
        capture.run(config, conn, catalog=False)
    assert len(session.calls) == 1        # stopped at once, Spotify never asked
    assert conn.execute("SELECT COUNT(*) FROM chart_snapshots").fetchone()[0] == 0


def test_unknown_source_is_rejected(config, conn):
    with pytest.raises(ValueError, match="unknown chart source"):
        capture.run(config, conn, sources=["podbay"])
