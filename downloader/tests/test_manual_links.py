"""link-entity: manual identity decisions, and their precedence in podcast_for_entity.

The only network boundary is ``lookup_many`` (iTunes lookup), replaced by a
dict of fake listings.
"""

import json

import pytest

from podcast_pipeline import db
from podcast_pipeline.catalog import manual
from podcast_pipeline.models import PodcastRecord


def itunes(collection_id, name, publisher, feed="auto"):
    return {"collectionId": collection_id, "collectionName": name, "artistName": publisher,
            "feedUrl": f"https://feeds/{collection_id}" if feed == "auto" else feed,
            "genres": ["News"], "kind": "podcast"}


@pytest.fixture
def lookups(monkeypatch):
    """Fake iTunes listings by Apple id; an id not in the dict is not listed."""
    listed: dict[str, dict] = {}
    monkeypatch.setattr(manual, "lookup_many",
                        lambda session, ids, batch_size, delay: {i: listed[i] for i in ids if i in listed})
    monkeypatch.setattr(manual, "make_session", lambda: None)
    return listed


def add_podcast(conn, source_id, title, apple_id=None, rss_url=None, publisher="Pub"):
    pid = db.upsert_podcast(conn, PodcastRecord(source_id=source_id, title=title, publisher=publisher,
                                                rss_url=rss_url, apple_podcasts_id=apple_id))
    conn.commit()
    return pid


def podcast(conn, pid):
    return dict(conn.execute("SELECT * FROM podcasts WHERE id = ?", (pid,)).fetchone())


def link(conn, entity):
    row = conn.execute("SELECT * FROM entity_links WHERE entity = ?", (entity,)).fetchone()
    return None if row is None else {**dict(row), "detail": json.loads(row["detail"])}


def link_entity(config, conn, entity, note="evidence", **target):
    return manual.run(config, conn, entity, note=note, **target)


# --- podcast_for_entity precedence ---------------------------------------------

def test_manual_link_overrides_apple_id_match(config, conn):
    wrong = add_podcast(conn, "apple_111", "Betrayal (unrelated)", apple_id="111")
    right = add_podcast(conn, "apple_222", "Betrayal", apple_id="222")
    assert db.podcast_for_entity(conn, "apple:111") == wrong

    link_entity(config, conn, "apple:111", podcast_id=right)

    assert db.podcast_for_entity(conn, "apple:111") == right


def test_manual_unresolvable_overrides_apple_id_match(config, conn):
    add_podcast(conn, "apple_111", "Wrong show", apple_id="111")
    link_entity(config, conn, "apple:111", unresolvable=True, note="no source found")
    assert db.podcast_for_entity(conn, "apple:111") is None


def test_automatic_links_keep_their_precedence(config, conn):
    by_apple = add_podcast(conn, "apple_111", "Show", apple_id="111")
    other = add_podcast(conn, "apple_333", "Other", apple_id="333")
    db.link_entity(conn, "apple:111", other, "itunes_search", {})
    db.link_entity(conn, "title:show", other, "itunes_search", {})
    db.link_entity(conn, "apple:999", by_apple, "recoverability", {})
    conn.commit()

    assert db.podcast_for_entity(conn, "apple:111") == by_apple       # the Apple id still wins
    assert db.podcast_for_entity(conn, "title:show") == other
    assert db.podcast_for_entity(conn, "apple:999") == by_apple       # an id the catalog lacks
    assert db.podcast_for_entity(conn, "apple:555") is None
    assert db.podcast_for_entity(conn, f"podcast:{other}") == other


def test_manual_link_on_title_overrides_earlier_search_link(config, conn):
    wrong = add_podcast(conn, "apple_111", "Serial Killers (other)", apple_id="111")
    right = add_podcast(conn, "apple_222", "Serial Killers", apple_id="222")
    db.link_entity(conn, "title:serialkillers", wrong, "itunes_search", {"match": {"tier": "exact"}})
    conn.commit()

    out = link_entity(config, conn, "title:serialkillers", podcast_id=right, note="Parcast, 2017")

    assert db.podcast_for_entity(conn, "title:serialkillers") == right
    row = link(conn, "title:serialkillers")
    assert row["method"] == "manual"
    assert row["detail"]["note"] == "Parcast, 2017"
    assert row["detail"]["decided_at"]
    assert row["detail"]["previous"]["podcast_id"] == wrong
    assert row["detail"]["previous"]["method"] == "itunes_search"
    assert row["detail"]["previous"]["detail"] == {"match": {"tier": "exact"}}
    assert out["previous"] == {"podcast_id": wrong, "method": "itunes_search"}


def test_manual_link_updates_study_members(config, conn):
    pid = add_podcast(conn, "apple_222", "Show", apple_id="222")
    conn.execute("INSERT INTO studies (name, definition, definition_hash, refreshed_at) "
                 "VALUES ('s', '{}', 'x', CURRENT_TIMESTAMP)")
    conn.execute("INSERT INTO study_members (study, entity, podcast_id, name, scope, attrs) "
                 "VALUES ('s', 'title:show', NULL, 'Show', 'all', '{}')")
    conn.commit()

    out = link_entity(config, conn, "title:show", podcast_id=pid)

    assert out["study_members_updated"] == 1
    assert conn.execute("SELECT podcast_id FROM study_members WHERE entity = 'title:show'").fetchone()[0] == pid


# --- targets ---------------------------------------------------------------------

def test_podcast_id_target_records_source_and_leaves_podcast_alone(config, conn):
    pid = add_podcast(conn, "apple_222", "Show", apple_id="222", rss_url="https://feed/a")
    before = podcast(conn, pid)

    link_entity(config, conn, "title:show", podcast_id=pid)

    assert podcast(conn, pid) == before
    src = conn.execute("SELECT * FROM podcast_sources WHERE podcast_id = ? AND source = 'manual'",
                       (pid,)).fetchone()
    assert src["ref"] == "title:show"


def test_unknown_podcast_id_fails(config, conn):
    with pytest.raises(ValueError, match="No podcast 42"):
        link_entity(config, conn, "title:show", podcast_id=42)
    assert link(conn, "title:show") is None


def test_apple_id_creates_podcast_when_catalog_lacks_it(config, conn, lookups):
    lookups["555"] = itunes(555, "Real Show", "Real Pub")

    out = link_entity(config, conn, "title:realshow", apple_id="555")

    assert out["created"] is True
    p = podcast(conn, out["podcast_id"])
    assert (p["apple_podcasts_id"], p["title"], p["rss_url"]) == ("555", "Real Show", "https://feeds/555")
    assert conn.execute("SELECT source FROM podcast_feeds WHERE podcast_id = ? AND url = ?",
                        (p["id"], "https://feeds/555")).fetchone()["source"] == "manual"
    assert conn.execute("SELECT 1 FROM podcast_sources WHERE podcast_id = ? AND source = 'manual' "
                        "AND ref = 'title:realshow'", (p["id"],)).fetchone()
    assert link(conn, "title:realshow")["detail"]["itunes_lookup"]["listed"] is True


def test_apple_id_reuses_catalog_podcast_without_rewriting_it(config, conn, lookups):
    pid = add_podcast(conn, "apple_555", "Old Title", apple_id="555", rss_url="https://feed/old",
                      publisher="Old Pub")
    before = podcast(conn, pid)
    lookups["555"] = itunes(555, "New Title", "New Pub", feed="https://feed/new")

    out = link_entity(config, conn, "apple:1", apple_id="555")

    assert out["created"] is False and out["podcast_id"] == pid
    assert podcast(conn, pid) == before
    # the newer feed is remembered, not made current
    assert conn.execute("SELECT 1 FROM podcast_feeds WHERE podcast_id = ? AND url = 'https://feed/new'",
                        (pid,)).fetchone()


def test_apple_id_fills_only_an_empty_rss_url(config, conn, lookups):
    pid = add_podcast(conn, "apple_555", "Show", apple_id="555")
    lookups["555"] = itunes(555, "Show", "Pub")

    link_entity(config, conn, "apple:555", apple_id="555")

    assert podcast(conn, pid)["rss_url"] == "https://feeds/555"


def test_apple_id_whose_feed_another_podcast_reads_links_to_it(config, conn, lookups):
    pid = add_podcast(conn, "title_x", "Show", rss_url="https://feeds/555")
    lookups["555"] = itunes(555, "Show", "Pub")

    out = link_entity(config, conn, "title:show", apple_id="555")

    assert out["podcast_id"] == pid and out["created"] is False
    assert conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0] == 1


def test_unlisted_apple_id_not_in_catalog_fails(config, conn, lookups):
    with pytest.raises(ValueError, match="--feed-url"):
        link_entity(config, conn, "title:show", apple_id="777")
    assert link(conn, "title:show") is None


def test_unlisted_apple_id_in_catalog_links(config, conn, lookups):
    pid = add_podcast(conn, "apple_777", "Gone Show", apple_id="777", rss_url="https://feed/g")
    out = link_entity(config, conn, "title:goneshow", apple_id="777")
    assert out["podcast_id"] == pid
    assert link(conn, "title:goneshow")["detail"]["itunes_lookup"] == {"listed": False}


def test_feed_url_creates_podcast(config, conn):
    url = "https://example.com/feed.xml"
    out = link_entity(config, conn, "apple:1", feed_url=url, title="Lost Show", publisher="Net")

    p = podcast(conn, out["podcast_id"])
    assert out["created"] is True
    assert p["podchaser_id"] == manual.feed_source_id(url)
    assert p["podchaser_id"].startswith("feed_") and len(p["podchaser_id"]) == len("feed_") + 12
    assert (p["title"], p["publisher"], p["rss_url"], p["apple_podcasts_id"]) == ("Lost Show", "Net", url, None)
    assert db.podcast_for_entity(conn, "apple:1") == p["id"]


def test_feed_url_reuses_podcast_with_that_feed(config, conn):
    pid = add_podcast(conn, "apple_9", "Show", apple_id="9", rss_url="https://example.com/feed")
    before = podcast(conn, pid)
    out = link_entity(config, conn, "title:show", feed_url="https://example.com/feed", title="Ignored")
    assert out["podcast_id"] == pid and out["created"] is False
    assert podcast(conn, pid) == before


def test_feed_url_known_from_history_fills_empty_rss_url(config, conn):
    pid = add_podcast(conn, "apple_9", "Show", apple_id="9")
    db.record_feed_url(conn, pid, "https://old/feed", "archived_lookup")
    conn.commit()

    out = link_entity(config, conn, "title:show", feed_url="https://old/feed")

    assert out["podcast_id"] == pid
    assert podcast(conn, pid)["rss_url"] == "https://old/feed"


def test_feed_url_fills_the_feedless_podcast_of_the_entitys_apple_id(config, conn):
    pid = add_podcast(conn, "apple_9", "Homecoming", apple_id="9")
    before = podcast(conn, pid)

    out = link_entity(config, conn, "apple:9", feed_url="https://old/homecoming")

    assert out["podcast_id"] == pid and out["created"] is False
    assert podcast(conn, pid) == {**before, "rss_url": "https://old/homecoming"}
    assert conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0] == 1


def test_feed_url_does_not_touch_a_podcast_with_a_feed(config, conn):
    pid = add_podcast(conn, "apple_9", "Undone (unrelated)", apple_id="9", rss_url="https://other/feed")

    out = link_entity(config, conn, "apple:9", feed_url="https://old/undone", title="Undone")

    assert out["created"] is True and out["podcast_id"] != pid
    assert podcast(conn, pid)["rss_url"] == "https://other/feed"
    assert db.podcast_for_entity(conn, "apple:9") == out["podcast_id"]


def test_feed_url_needs_title_to_create(config, conn):
    with pytest.raises(ValueError, match="--title"):
        link_entity(config, conn, "title:show", feed_url="https://example.com/new")
    assert conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0] == 0


def test_unresolvable_records_null_link_with_note(config, conn):
    db.link_entity(conn, "title:gone", None, "itunes_search", {"searched": True})
    conn.commit()

    out = link_entity(config, conn, "title:gone", unresolvable=True, note="deleted 2018; no Wayback copy")

    row = link(conn, "title:gone")
    assert out["podcast_id"] is None
    assert row["podcast_id"] is None and row["method"] == "manual"
    assert row["detail"]["note"] == "deleted 2018; no Wayback copy"
    assert row["detail"]["previous"]["method"] == "itunes_search"


@pytest.mark.parametrize("entity, target, error", [
    ("podcast:1", {"unresolvable": True}, "Entity must be"),
    ("show", {"unresolvable": True}, "Entity must be"),
    ("title:x", {}, "exactly one"),
    ("title:x", {"unresolvable": True, "podcast_id": 1}, "exactly one"),
    ("title:x", {"unresolvable": True, "title": "T"}, "only apply to --feed-url"),
    ("title:x", {"feed_url": "example.com/feed", "title": "T"}, "http"),
])
def test_bad_arguments_fail(config, conn, entity, target, error):
    with pytest.raises(ValueError, match=error):
        link_entity(config, conn, entity, **target)


def test_note_is_required(config, conn):
    with pytest.raises(ValueError, match="note"):
        link_entity(config, conn, "title:x", unresolvable=True, note="  ")
