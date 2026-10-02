"""resolve --study: chart entities to catalog podcasts.

The network is replaced at its two boundaries: ``lookup_many`` (batched iTunes
lookup) and the HTTP session the paced search uses. The recoverability CSV is
a small file in tmp_path.
"""

import json

import pytest
import requests

from podcast_pipeline import db
from podcast_pipeline.catalog import itunes_search, resolve
from podcast_pipeline.catalog.itunes_search import ITunesSearchUnavailable, best_match, publisher_matches

STUDY = "chart_test"

CSV_HEADER = "entity,key,name,publisher,apple_id,feed_source,feed_url,final_url,http_status,feed_error,verdict\n"


def itunes(collection_id, name, publisher, feed="auto"):
    return {"collectionId": collection_id, "collectionName": name, "artistName": publisher,
            "feedUrl": f"https://feeds/{collection_id}" if feed == "auto" else feed,
            "genres": ["News"], "kind": "podcast"}


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


class FakeSearch:
    """Answers iTunes searches from ``{term: [results]}``; records each term."""

    def __init__(self, results=None, status=200):
        self.results = results or {}
        self.status = status
        self.terms = []

    def get(self, url, params=None, **kwargs):
        assert "itunes.apple.com/search" in url, url
        self.terms.append(params["term"])
        if self.status != 200:
            return FakeResponse({}, status=self.status)
        return FakeResponse({"results": self.results.get(params["term"], [])})


@pytest.fixture
def env(config, conn, tmp_path, monkeypatch):
    """Wires fakes into resolve and returns a handle to configure them."""
    config.spotify.search_delay_seconds = 0
    config.spotify.search_attempts = 2

    class Env:
        lookups: dict = {}
        lookup_calls: list = []
        search = FakeSearch()
        csv_path = tmp_path / "recoverability.csv"

        def run(self, **kwargs):
            return resolve.run(config, conn, STUDY, **kwargs)

    e = Env()
    e.lookups, e.lookup_calls = {}, []
    e.csv_path.write_text(CSV_HEADER)

    def fake_lookup_many(session, ids, batch_size, delay):
        e.lookup_calls.append(list(ids))
        return {i: e.lookups[i] for i in ids if i in e.lookups}

    monkeypatch.setattr(resolve, "lookup_many", fake_lookup_many)
    monkeypatch.setattr(resolve, "make_session", lambda: e.search)
    monkeypatch.setattr(resolve, "recoverability_path", lambda config: e.csv_path)
    monkeypatch.setattr(itunes_search.time, "sleep", lambda s: None)
    conn.execute("INSERT INTO studies (name, definition, definition_hash, refreshed_at) "
                 "VALUES (?, '{}', 'x', CURRENT_TIMESTAMP)", (STUDY,))
    conn.commit()
    return e


def add_member(conn, entity, name=None, publisher=None, podcast_id=None, study=STUDY):
    attrs = json.dumps({"publisher": publisher} if publisher else {})
    conn.execute("INSERT INTO study_members (study, entity, podcast_id, name, scope, attrs) "
                 "VALUES (?, ?, ?, ?, 'all', ?)", (study, entity, podcast_id, name, attrs))
    conn.commit()


def member_podcast(conn, entity):
    row = conn.execute("SELECT m.podcast_id, p.rss_url, p.apple_podcasts_id, p.title FROM study_members m "
                       "LEFT JOIN podcasts p ON p.id = m.podcast_id WHERE m.entity = ?",
                       (entity,)).fetchone()
    return dict(row)


def link(conn, entity):
    row = conn.execute("SELECT * FROM entity_links WHERE entity = ?", (entity,)).fetchone()
    return None if row is None else {**dict(row), "detail": json.loads(row["detail"])}


# --- apple ---------------------------------------------------------------------

def test_listed_apple_id_is_upserted_with_its_feed(env, conn):
    add_member(conn, "apple:1200361736", "The Daily", "The New York Times")
    env.lookups["1200361736"] = itunes(1200361736, "The Daily", "The New York Times")

    summary = env.run()

    got = member_podcast(conn, "apple:1200361736")
    assert got["rss_url"] == "https://feeds/1200361736"
    assert got["apple_podcasts_id"] == "1200361736"
    assert summary["outcomes"] == {"resolved": 1}
    assert summary["methods"] == {"itunes_lookup": 1}
    assert env.search.terms == []
    source = conn.execute("SELECT * FROM podcast_sources WHERE podcast_id = ?", (got["podcast_id"],)).fetchone()
    assert (source["source"], source["ref"]) == (db.SourceKind.CHART_ARCHIVE, "apple:1200361736")
    assert json.loads(source["detail"])["study"] == STUDY
    assert conn.execute("SELECT source FROM podcast_feeds WHERE podcast_id = ?",
                        (got["podcast_id"],)).fetchone()[0] == "itunes_lookup"
    assert link(conn, "apple:1200361736") is None      # the Apple id is the identity


def test_unlisted_apple_id_falls_back_to_a_title_search(env, conn):
    add_member(conn, "apple:111", "Old Show", "Old Network")
    env.search.results["Old Show"] = [itunes(999, "Old Show", "Old Network")]

    summary = env.run()

    got = member_podcast(conn, "apple:111")
    assert got["apple_podcasts_id"] == "999" and got["rss_url"] == "https://feeds/999"
    entry = link(conn, "apple:111")
    assert entry["method"] == "itunes_search" and entry["podcast_id"] == got["podcast_id"]
    assert entry["detail"]["match"]["candidate_id"] == "999"
    assert entry["detail"]["match"]["publisher_match"] is True
    assert entry["detail"]["steps"][0] == {"step": "itunes_lookup", "apple_id": "111",
                                           "listed": False, "feed": None}
    assert summary["methods"] == {"itunes_search_exact": 1}


def test_unlisted_apple_id_falls_back_to_the_recoverability_feed(env, conn):
    add_member(conn, "apple:222", "Gone Show", "Gone Inc")
    env.csv_path.write_text(CSV_HEADER + "222,goneshow,Gone Show,Gone Inc,222,lookup,"
                            "https://old/feed.xml,https://new/feed.xml,200,,archive_only\n")

    summary = env.run()

    got = member_podcast(conn, "apple:222")
    assert got["apple_podcasts_id"] == "222" and got["rss_url"] == "https://old/feed.xml"
    assert conn.execute("SELECT podchaser_id FROM podcasts WHERE id = ?",
                        (got["podcast_id"],)).fetchone()[0] == "apple_222"
    feeds = conn.execute("SELECT url, source FROM podcast_feeds WHERE podcast_id = ? ORDER BY url",
                         (got["podcast_id"],)).fetchall()
    assert [tuple(f) for f in feeds] == [("https://new/feed.xml", "recoverability"),
                                         ("https://old/feed.xml", "recoverability")]
    entry = link(conn, "apple:222")
    assert entry["method"] == "recoverability"
    assert entry["detail"]["recoverability"]["feed_source"] == "lookup"
    assert entry["detail"]["searched"] is True        # the search ran first and found nothing
    assert summary["methods"] == {"recoverability": 1}


def test_recoverability_reuses_a_podcast_that_already_has_the_feed(env, conn):
    existing = db.upsert_podcast(conn, db.PodcastRecord(source_id="spotify_X", title="Gone Show",
                                                        rss_url="https://old/feed.xml"))
    add_member(conn, "apple:222", "Gone Show")
    env.csv_path.write_text(CSV_HEADER + "222,goneshow,Gone Show,Gone Inc,222,lookup,"
                            "https://old/feed.xml,,200,,archive_only\n")
    env.run(search=False)
    assert member_podcast(conn, "apple:222")["podcast_id"] == existing


def test_unresolvable_apple_id_is_recorded_as_a_failure(env, conn):
    add_member(conn, "apple:333", "Nothing Show")
    summary = env.run()
    assert member_podcast(conn, "apple:333")["podcast_id"] is None
    entry = link(conn, "apple:333")
    assert entry["podcast_id"] is None and entry["method"] == "itunes_search"
    assert summary["outcomes"] == {"failed": 1}
    assert summary["unresolved"] == [{"entity": "apple:333", "name": "Nothing Show"}]


# --- title ---------------------------------------------------------------------

def test_title_exact_match_prefers_the_publisher_then_relevance(env, conn):
    add_member(conn, "title:thedaily", "The Daily", "The New York Times")
    env.search.results["The Daily"] = [itunes(1, "The Daily", "Someone Else"),
                                       itunes(2, "The Daily", "The New York Times"),
                                       itunes(3, "The Daily", "The New York Times")]
    env.run()
    assert member_podcast(conn, "title:thedaily")["apple_podcasts_id"] == "2"
    entry = link(conn, "title:thedaily")
    assert entry["method"] == "itunes_search"
    assert entry["detail"]["match"]["tier"] == "exact"


def test_title_exact_match_without_publisher_agreement_is_accepted_but_flagged(env, conn):
    add_member(conn, "title:betrayal", "Betrayal", "iHeartPodcasts")
    env.search.results["Betrayal"] = [itunes(5, "Betrayal", "A Stranger")]
    summary = env.run()
    assert member_podcast(conn, "title:betrayal")["apple_podcasts_id"] == "5"
    assert summary["title_only_matches"][0]["candidate_publisher"] == "A Stranger"


def test_title_fuzzy_match_needs_the_publisher(env, conn):
    add_member(conn, "title:wecandohardthingswithglennondoyle",
               "We Can Do Hard Things with Glennon Doyle", "Glennon Doyle & Cadence13")
    add_member(conn, "title:aboveandbeyond", "Above & Beyond", None)
    env.search.results["We Can Do Hard Things with Glennon Doyle"] = [
        itunes(10, "We Can Do Hard Things", "Glennon Doyle & Audacy")]
    env.search.results["Above & Beyond"] = [itunes(11, "Above & Beyond: Group Therapy", "aboveandbeyond.nu")]

    summary = env.run()

    assert member_podcast(conn, "title:wecandohardthingswithglennondoyle")["apple_podcasts_id"] == "10"
    match = link(conn, "title:wecandohardthingswithglennondoyle")["detail"]["match"]
    assert (match["tier"], match["rule"], match["publisher_match"]) == \
        ("fuzzy", "candidate_title_is_chart_head", True)
    # No publisher known: the subtitle match is not enough.
    assert member_podcast(conn, "title:aboveandbeyond")["podcast_id"] is None
    assert link(conn, "title:aboveandbeyond")["podcast_id"] is None
    assert summary["methods"] == {"itunes_search_fuzzy": 1}


def test_title_fuzzy_match_with_a_different_publisher_is_rejected(env, conn):
    add_member(conn, "title:aboveandbeyond", "Above & Beyond", "Somebody Else")
    env.search.results["Above & Beyond"] = [itunes(11, "Above & Beyond: Group Therapy", "aboveandbeyond.nu")]
    env.run()
    assert member_podcast(conn, "title:aboveandbeyond")["podcast_id"] is None


def test_title_falls_back_to_recoverability_by_key(env, conn):
    add_member(conn, "title:murdaughmurderspodcast", "Murdaugh Murders Podcast", "Mandy Matney")
    env.csv_path.write_text(CSV_HEADER + "title:murdaughmurderspodcast,murdaughmurderspodcast,"
                            "Murdaugh Murders Podcast,Mandy Matney,,search:title,"
                            "https://feeds.megaphone.fm/BER,,200,,recent_only\n")
    env.run(search=False)
    got = member_podcast(conn, "title:murdaughmurderspodcast")
    assert got["rss_url"] == "https://feeds.megaphone.fm/BER"
    assert link(conn, "title:murdaughmurderspodcast")["method"] == "recoverability"


def test_matching_rules():
    assert publisher_matches("NBC News", "NBC News Studios")
    assert publisher_matches("Wondery | Campside", "Wondery")
    assert publisher_matches("The New York Times", "New York Times")
    assert not publisher_matches("iHeartRadio", "iHeartPodcasts")
    # Two different subtitles on one head are not the same show.
    results = [itunes(1, "Crime: Part Two", "Pub")]
    assert best_match(results, "Crime: Part One", ["Pub"]) is None
    assert best_match([itunes(1, "Daily", "Pub")], "The Daily Podcast", ["Pub"]).rule == "stripped"


# --- run behaviour -----------------------------------------------------------------

def test_a_throttle_stops_the_run_and_records_nothing_as_missing(env, conn):
    add_member(conn, "title:first", "First", "P")
    add_member(conn, "title:second", "Second", "P")
    env.search.status = 403
    with pytest.raises(ITunesSearchUnavailable, match="iTunes search unavailable"):
        env.run()
    assert conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0] == 0
    assert env.search.terms == ["First", "First"]       # search_attempts = 2


def test_entities_resolved_before_a_throttle_stay_committed(env, conn):
    add_member(conn, "title:first", "First", "P")
    add_member(conn, "title:second", "Second", "P")
    env.search.results["First"] = [itunes(1, "First", "P")]
    original = env.search.get

    def throttle_second(url, params=None, **kwargs):
        if params["term"] == "Second":
            return FakeResponse({}, status=403)
        return original(url, params, **kwargs)

    env.search.get = throttle_second
    with pytest.raises(ITunesSearchUnavailable):
        env.run()
    conn.rollback()
    assert link(conn, "title:first")["podcast_id"] is not None


def test_recent_failures_wait_for_the_retry_window(env, conn):
    add_member(conn, "title:nothing", "Nothing", "P")
    env.run()
    assert env.search.terms == ["Nothing"]

    summary = env.run()
    assert env.search.terms == ["Nothing"]               # not searched again
    assert summary["skipped_recent_failure"] == 1 and summary["attempted"] == 0

    env.run(retry_failed=True)
    assert env.search.terms == ["Nothing", "Nothing"]

    conn.execute("UPDATE entity_links SET resolved_at = datetime('now', '-8 days')")
    conn.commit()
    env.run()
    assert env.search.terms == ["Nothing"] * 3


def test_a_failure_without_search_is_retried_when_search_is_on(env, conn):
    add_member(conn, "title:later", "Later", "P")
    env.run(search=False)
    assert link(conn, "title:later")["podcast_id"] is None
    env.search.results["Later"] = [itunes(7, "Later", "P")]
    env.run()
    assert member_podcast(conn, "title:later")["apple_podcasts_id"] == "7"


def test_relinking_picks_up_known_mappings_and_reports_merges(env, conn):
    pid = db.upsert_podcast(conn, db.PodcastRecord(source_id="apple_42", title="Known",
                                                   apple_podcasts_id="42", rss_url="https://feeds/42"))
    db.link_entity(conn, "title:knownshow", pid, "manual")
    conn.commit()
    add_member(conn, "apple:42", "Known")
    add_member(conn, "title:knownshow", "Known Show")
    add_member(conn, f"podcast:{pid}", "Known", podcast_id=pid)

    summary = env.run()

    assert {member_podcast(conn, e)["podcast_id"]
            for e in ("apple:42", "title:knownshow", f"podcast:{pid}")} == {pid}
    assert summary["already_known"] == 2 and summary["attempted"] == 0
    assert summary["merged"] == [{"podcast_id": pid,
                                  "entities": ["apple:42", "title:knownshow", f"podcast:{pid}"]}]
    assert env.lookup_calls == [] and env.search.terms == []


def test_relinking_includes_entities_resolved_by_another_study(env, conn):
    conn.execute("INSERT INTO studies (name, definition, definition_hash) VALUES ('other', '{}', 'y')")
    add_member(conn, "title:shared", "Shared", "P", study="other")
    add_member(conn, "title:shared", "Shared", "P")
    env.search.results["Shared"] = [itunes(8, "Shared", "P")]
    resolve.run(env_config(conn), conn, "other")
    # Members of this study were never touched by the other run.
    assert conn.execute("SELECT podcast_id FROM study_members WHERE study = ? AND entity = 'title:shared'",
                        (STUDY,)).fetchone()[0] is None
    summary = env.run()
    assert member_podcast(conn, "title:shared")["apple_podcasts_id"] == "8"
    assert summary["already_known"] == 1 and env.search.terms == ["Shared"]


def env_config(conn):
    from podcast_pipeline.config import Config
    config = Config()
    config.spotify.search_delay_seconds = 0
    return config


def test_feedless_podcast_member_gets_a_feed_from_a_fresh_lookup(env, conn):
    pid = db.upsert_podcast(conn, db.PodcastRecord(source_id="apple_50", title="Feedless",
                                                   apple_podcasts_id="50", spotify_id="SP"))
    conn.commit()
    add_member(conn, f"podcast:{pid}", "Feedless")
    env.lookups["50"] = itunes(50, "Feedless", "P")
    summary = env.run()
    row = conn.execute("SELECT rss_url, spotify_id FROM podcasts WHERE id = ?", (pid,)).fetchone()
    assert tuple(row) == ("https://feeds/50", "SP")
    assert summary["with_feed"] == 1


def test_limit_counts_attempted_entities(env, conn):
    for i in range(3):
        add_member(conn, f"title:show{i}", f"Show {i}", "P")
    summary = env.run(limit=2)
    assert summary["attempted"] == 2 and env.search.terms == ["Show 0", "Show 1"]


def test_rerun_is_idempotent(env, conn):
    add_member(conn, "apple:1200361736", "The Daily", "The New York Times")
    add_member(conn, "title:oldshow", "Old Show", "Old Network")
    add_member(conn, "apple:222", "Gone Show")
    env.lookups["1200361736"] = itunes(1200361736, "The Daily", "The New York Times")
    env.search.results["Old Show"] = [itunes(999, "Old Show", "Old Network")]
    env.csv_path.write_text(CSV_HEADER + "222,goneshow,Gone Show,Gone Inc,222,lookup,"
                            "https://old/feed.xml,,200,,archive_only\n")
    first = env.run()
    snapshot = lambda: [tuple(r) for r in conn.execute(
        "SELECT entity, podcast_id FROM study_members ORDER BY entity")]
    before = (snapshot(), conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0])
    terms = list(env.search.terms)

    second = env.run()

    assert (snapshot(), conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0]) == before
    assert env.search.terms == terms and second["attempted"] == 0
    assert first["with_feed"] == second["with_feed"] == 3
    assert second["unresolved_count"] == 0 and second["merged"] == []


def test_unknown_study_is_an_error(env, conn):
    with pytest.raises(ValueError, match="Unknown study"):
        resolve.run(env_config(conn), conn, "nope")
