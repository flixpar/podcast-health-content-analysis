"""Chart sources: parsing each chart's payload and resolving it to a feed.

The fixtures are trimmed copies of real responses; the network is replaced by
a fake session at the ``requests.Session`` boundary.
"""

import json

import pytest
import requests

from podcast_pipeline.config import Config, SpotifyConfig
from podcast_pipeline.sources import make_source
from podcast_pipeline.sources.apple import AppleChartsSource
from podcast_pipeline.sources.spotify import SpotifyChartsSource, SpotifyResolveError

#: No pacing between searches; the real delay is there to dodge throttling.
FAST = SpotifyConfig(search_delay_seconds=0, search_attempts=3)

GENRE_FEED = {"feed": {"entry": [
    {"im:name": {"label": "Huberman Lab"},
     "im:artist": {"label": "Scicomm Media"},
     "im:image": [{"label": "https://img/100.jpg"}, {"label": "https://img/170.jpg"}],
     "category": {"attributes": {"im:id": "1512", "term": "Health & Fitness"}},
     "id": {"label": "https://podcasts.apple.com/us/podcast/id1545953110",
            "attributes": {"im:id": "1545953110"}}},
    {"im:name": {"label": "Get Sleepy"},
     "im:artist": {"label": "Slumber Studios"},
     "im:image": [{"label": "https://img/a.jpg"}],
     "category": {"attributes": {"im:id": "1512", "term": "Health & Fitness"}},
     "id": {"label": "https://podcasts.apple.com/us/podcast/id1487513861",
            "attributes": {"im:id": "1487513861"}}},
]}}

LOOKUPS = {
    "1545953110": {"collectionId": 1545953110, "collectionName": "Huberman Lab",
                   "artistName": "Scicomm Media", "feedUrl": "https://feeds/huberman",
                   "genres": ["Health & Fitness", "Science"], "description": "Neuroscience."},
    "1487513861": {"collectionId": 1487513861, "collectionName": "Get Sleepy: stories for sleep",
                   "artistName": "Slumber Studios", "feedUrl": "https://feeds/getsleepy",
                   "genres": ["Health & Fitness"], "description": "Sleep stories."},
}

SPOTIFY_CHART = [
    {"showUri": "spotify:show:AAA", "showName": "Huberman Lab",
     "showPublisher": "Scicomm Media", "showDescription": "Neuroscience.",
     "showImageUrl": "https://i.scdn.co/a"},
    {"showUri": "spotify:show:BBB", "showName": "Spotify Exclusive Show",
     "showPublisher": "Spotify", "showDescription": "Nowhere else.",
     "showImageUrl": "https://i.scdn.co/b"},
]


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.headers = {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class FakeSession:
    """Routes by URL substring; records every URL requested."""

    def __init__(self, routes):
        self.routes = routes
        self.urls = []

    def get(self, url, params=None, **kwargs):
        self.urls.append((url, params or {}))
        for fragment, payload in self.routes.items():
            if fragment in url:
                return FakeResponse(payload(url, params or {}) if callable(payload) else payload)
        raise AssertionError(f"unexpected request to {url}")


def _lookup_route(url, params):
    apple_id = url.split("id=")[1].split("&")[0]
    return {"results": [LOOKUPS[apple_id]]}


# --- Apple -------------------------------------------------------------------

def test_genre_chart_is_parsed_and_enriched():
    session = FakeSession({"rss/toppodcasts": GENRE_FEED, "lookup": _lookup_route})
    source = AppleChartsSource(session, genre="1512", lookup_delay=0)

    records = source.top_podcasts(50)

    assert source.chart_name == "apple_us_genre_1512"
    assert [r.title for r in records] == ["Huberman Lab", "Get Sleepy: stories for sleep"]
    assert [r.rss_url for r in records] == ["https://feeds/huberman", "https://feeds/getsleepy"]
    assert records[0].apple_podcasts_id == "1545953110"
    assert records[0].source_id == "apple_1545953110"
    assert "Science" in records[0].categories
    assert "genre=1512" in session.urls[0][0] and "limit=50" in session.urls[0][0]


def test_genre_chart_limit_is_capped_at_the_feeds_maximum():
    session = FakeSession({"rss/toppodcasts": GENRE_FEED, "lookup": _lookup_route})
    AppleChartsSource(session, genre="1512", lookup_delay=0).top_podcasts(500)
    assert "limit=200" in session.urls[0][0]


def test_overall_chart_still_uses_the_marketing_tools_feed():
    charts = {"feed": {"results": [{"id": "1545953110", "name": "Huberman Lab",
                                    "artistName": "Scicomm Media", "genres": []}]}}
    session = FakeSession({"marketingtools": charts, "lookup": _lookup_route})
    source = AppleChartsSource(session, lookup_delay=0)

    records = source.top_podcasts(100)

    assert source.chart_name == "apple_us_top"
    assert records[0].rss_url == "https://feeds/huberman"


def test_lookup_failure_still_yields_a_record_without_a_feed():
    session = FakeSession({"rss/toppodcasts": GENRE_FEED, "lookup": {"results": []}})
    records = AppleChartsSource(session, genre="1512", lookup_delay=0).top_podcasts(50)
    assert records[0].title == "Huberman Lab"      # from the chart entry
    assert records[0].rss_url is None


# --- Spotify -----------------------------------------------------------------

def _spotify_session(search_results):
    return FakeSession({
        "podcastcharts.byspotify.com": SPOTIFY_CHART,
        "itunes.apple.com/search": lambda url, params: {"results": search_results(params["term"])},
    })


def test_spotify_show_is_matched_to_its_apple_feed():
    session = _spotify_session(lambda term: [LOOKUPS["1545953110"]] if "Huberman" in term else [])
    source = SpotifyChartsSource(session, FAST, lookup_delay=0)

    records = source.top_podcasts(100)

    assert source.chart_name == "spotify_us_top"
    matched = records[0]
    # Identified by its Apple id so a show on both charts updates one row.
    assert matched.source_id == "apple_1545953110"
    assert matched.rss_url == "https://feeds/huberman"
    assert matched.spotify_id == "AAA"


def test_spotify_exclusive_is_recorded_without_a_feed():
    session = _spotify_session(lambda term: [LOOKUPS["1545953110"]] if "Huberman" in term else [])
    records = SpotifyChartsSource(session, FAST, lookup_delay=0).top_podcasts(100)

    unmatched = records[1]
    assert unmatched.source_id == "spotify_BBB"
    assert unmatched.spotify_id == "BBB"
    assert unmatched.rss_url is None
    assert unmatched.extra["rss_lookup"] == "unmatched"


def test_spotify_rejects_a_search_hit_with_a_different_title():
    """iTunes search is fuzzy; a near-miss must not silently attach the wrong feed."""
    other = dict(LOOKUPS["1487513861"], collectionName="Huberman Lab Essentials")
    session = _spotify_session(lambda term: [other])
    records = SpotifyChartsSource(session, FAST, lookup_delay=0).top_podcasts(100)
    assert records[0].rss_url is None


def test_spotify_title_match_ignores_punctuation_and_accents():
    journal = {"collectionId": 7, "collectionName": "The Journal.", "artistName": "WSJ",
               "feedUrl": "https://feeds/journal", "genres": ["News"], "description": ""}
    chart = [{"showUri": "spotify:show:CCC", "showName": "The Journal",
              "showPublisher": "The Wall Street Journal"}]
    session = FakeSession({"podcastcharts.byspotify.com": chart,
                           "itunes.apple.com/search": {"results": [journal]}})
    records = SpotifyChartsSource(session, FAST, lookup_delay=0).top_podcasts(100)
    assert records[0].rss_url == "https://feeds/journal"


def test_spotify_prefers_the_candidate_whose_publisher_matches():
    same_name = [
        {"collectionId": 1, "collectionName": "The Daily", "artistName": "Someone Else",
         "feedUrl": "https://feeds/impostor", "genres": [], "description": ""},
        {"collectionId": 2, "collectionName": "The Daily", "artistName": "The New York Times",
         "feedUrl": "https://feeds/nyt", "genres": [], "description": ""},
    ]
    chart = [{"showUri": "spotify:show:DDD", "showName": "The Daily",
              "showPublisher": "The New York Times"}]
    session = FakeSession({"podcastcharts.byspotify.com": chart,
                           "itunes.apple.com/search": {"results": same_name}})
    records = SpotifyChartsSource(session, FAST, lookup_delay=0).top_podcasts(100)
    assert records[0].rss_url == "https://feeds/nyt"


# --- factory -----------------------------------------------------------------

def test_make_source_honours_type_and_genre():
    config = Config.from_dict({"fetcher": {"type": "apple", "genre": "1512", "country": "gb"}})
    source = make_source(config, session=None)
    assert isinstance(source, AppleChartsSource)
    assert source.chart_name == "apple_gb_genre_1512"

    config = Config.from_dict({"fetcher": {"type": "spotify"}})
    assert isinstance(make_source(config, session=None), SpotifyChartsSource)

    with pytest.raises(ValueError, match="Unknown fetcher.type"):
        make_source(Config.from_dict({"fetcher": {"type": "nope"}}), session=None)


def test_a_throttled_search_aborts_instead_of_recording_shows_as_feedless():
    """403 means "ask again later", not "this show has no feed". Recording it
    as the latter once marked 41 charting shows, The Ezra Klein Show among
    them, as having no RSS feed."""
    class Throttling(FakeSession):
        def get(self, url, params=None, **kwargs):
            self.urls.append((url, params or {}))
            if "search" in url:
                return FakeResponse({}, status=403)
            return FakeResponse(SPOTIFY_CHART)

    session = Throttling({})
    with pytest.raises(SpotifyResolveError, match="iTunes search unavailable"):
        SpotifyChartsSource(session, FAST, lookup_delay=0).top_podcasts(100)
    assert sum(1 for url, _ in session.urls if "search" in url) == FAST.search_attempts


def test_a_search_that_recovers_after_a_throttle_is_retried():
    calls = {"n": 0}

    class Flaky(FakeSession):
        def get(self, url, params=None, **kwargs):
            self.urls.append((url, params or {}))
            if "search" not in url:
                return FakeResponse(SPOTIFY_CHART[:1])
            calls["n"] += 1
            if calls["n"] == 1:
                return FakeResponse({}, status=429)
            return FakeResponse({"results": [LOOKUPS["1545953110"]]})

    records = SpotifyChartsSource(Flaky({}), FAST, lookup_delay=0).top_podcasts(100)
    assert records[0].rss_url == "https://feeds/huberman"
