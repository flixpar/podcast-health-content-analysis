import json

from podcast_pipeline import db
from podcast_pipeline.models import FeedEpisode, PodcastRecord
from podcast_pipeline.studies import quality
from podcast_pipeline.studies.quality import exclusion_reason, rerun_flags


def ep(title, duration=1800, episode_type="full"):
    return {"title": title, "duration_seconds": duration, "episode_type": episode_type}


def test_trailers_promos_and_short_items_are_excluded():
    assert exclusion_reason(ep("Season 2 is coming", episode_type="trailer", duration=120), "Show") == "trailer"
    assert exclusion_reason(ep("Introducing: Harsh Reality", 271), "Suspect") == "promo: introducing"
    assert exclusion_reason(ep("What to Listen to Next: Operator", 355), "Over My Dead Body") \
        == "promo: what to listen to next"
    assert exclusion_reason(ep("Introducing Uncover: The Village", 2428), "Dr. Death") == "promo: introducing"
    assert exclusion_reason(ep("Announcing a live show!", 45), "Show") == "short: 45 s"


def test_bonus_self_introductions_and_unknown_durations_are_kept():
    assert exclusion_reason(ep("Listener mail", 1200, "bonus"), "Show") is None
    assert exclusion_reason(ep("Introducing Dear Alana,", 125), "Dear Alana,") is None
    assert exclusion_reason(ep("Episode 4", None), "Show") is None
    assert exclusion_reason(ep("Episode 4", 0), "Show") is None
    assert exclusion_reason(ep("Episode 4", quality.MIN_EPISODE_SECONDS), "Show") is None


def test_episode_type_is_read_from_metadata_json():
    row = {"title": "Coming soon", "duration_seconds": 120,
           "metadata": json.dumps({"episode_type": "trailer"})}
    assert exclusion_reason(row, "Show") == "trailer"
    assert exclusion_reason({**row, "metadata": None}, "Show") is None


def podcast(conn, n):
    return db.upsert_podcast(conn, PodcastRecord(source_id=f"apple_{n}", title=f"Show {n}",
                                                 apple_podcasts_id=str(n), rss_url=f"https://f.example/{n}"))


def episode(conn, podcast_id, guid, day, title, duration, in_scope=True):
    db.insert_episode(conn, podcast_id, FeedEpisode(guid=guid, title=title, audio_url=f"https://a/{guid}",
                                                    published_date=f"{day}T10:00:00",
                                                    duration_seconds=duration))
    eid = conn.execute("SELECT id FROM episodes WHERE episode_guid = ?", (guid,)).fetchone()[0]
    if in_scope:
        conn.execute("INSERT INTO study_episodes (study, episode_id, entity, window_label, priority, "
                     "added_revision) VALUES ('s', ?, ?, ?, 0, 1)", (eid, f"podcast:{podcast_id}", day[:7]))
    return eid


def test_reruns_are_flagged_and_originals_are_not(conn):
    p = podcast(conn, 1)
    orig = episode(conn, p, "o", "2017-02-01", "How Empathy Works", 3164)
    marked = episode(conn, p, "m", "2021-10-02", "Selects: How Empathy Works", 3141)
    yearly_old = episode(conn, p, "y1", "2021-01-30", "Day 30: Nile Turned to Blood", 1197, in_scope=False)
    yearly = episode(conn, p, "y2", "2023-01-30", "Day 30: Nile Turned to Blood (2023)", 1197)
    guid = episode(conn, p, "7173 at https://www.thisamericanlife.org#rerun-2016-10-10",
                   "2016-10-10", "#598: My Undesirable Talent", 3500)
    conn.commit()
    flags = rerun_flags(conn, "s")
    assert orig not in flags
    assert flags[marked].startswith("same_title_copy:") and "rerun marker" in flags[marked]
    assert flags[yearly].startswith(f"rerun_of_earlier: {yearly_old}")
    assert flags[guid] == "guid_rerun: rerun-2016-10-10"


def test_recurring_titles_with_new_content_are_not_reruns(conn):
    p = podcast(conn, 1)
    episode(conn, p, "a", "2016-05-04", "#793 - Whitney Cummings", 9000)
    later = episode(conn, p, "b", "2018-01-23", "#1067 - Whitney Cummings", 9030)
    m1 = episode(conn, p, "c", "2017-03-20", "MFM Minisode 22", 1435)
    m2 = episode(conn, p, "d", "2021-04-05", "MFM Minisode 221", 1449)
    mail1 = episode(conn, p, "e", "2023-07-16", "Mailbag Sunday", 755)
    mail2 = episode(conn, p, "f", "2023-08-27", "Mailbag Sunday", 750)
    conn.commit()
    flags = rerun_flags(conn, "s")
    assert not {later, m1, m2, mail1, mail2} & set(flags)


def test_old_episode_numbers_are_reruns(conn):
    p = podcast(conn, 13)
    for n in range(600, 640):
        episode(conn, p, f"n{n}", f"2017-{1 + (n - 600) // 4:02d}-{1 + (n % 4) * 7:02d}",
                f"{n}: Story {n}", 3600 + n, in_scope=False)
    rerun = episode(conn, p, "r", "2018-02-18", "542: Wait, Do You Have The Map?", 3400)
    new = episode(conn, p, "new", "2018-02-25", "640: A New One", 3700)
    conn.commit()
    flags = rerun_flags(conn, "s")
    assert flags[rerun] == "old_number: 542 after the feed reached 639"
    assert new not in flags


def test_a_series_reposted_by_another_feed_flags_only_the_later_copy(conn):
    series, host = podcast(conn, 1), podcast(conn, 2)
    original = episode(conn, series, "s1", "2023-03-14", "1 - Michelle's Last Day", 1775)
    repost = episode(conn, host, "h1", "2026-02-16", "The Girl in the Blue Mustang - Ep. 1: Michelle's Last Day", 1775)
    unrelated = episode(conn, host, "h2", "2026-02-23", "Michelle's Last Dance", 1776)
    conn.commit()
    flags = rerun_flags(conn, "s")
    assert flags[repost] == f"repost_of_other_podcast: {original} in podcast {series} (2023-03-14)"
    assert original not in flags and unrelated not in flags


def test_old_number_rule_ignores_years_and_hyphenated_words():
    from podcast_pipeline.studies.quality import LEADING_NUMBER
    assert LEADING_NUMBER.match("542: Act One").group(1) == "542"
    assert LEADING_NUMBER.match("2020: The Year in Review") is None
    assert LEADING_NUMBER.match("80-Year-Old Man Loses War") is None


def test_long_feed_tagged_trailers_are_episodes():
    from podcast_pipeline.studies.quality import exclusion_reason
    interview = {"title": "E138 Interview with Shahn Ellis", "duration_seconds": 4075,
                 "episode_type": "trailer"}
    teaser = {"title": "Season 2 is coming", "duration_seconds": 95, "episode_type": "trailer"}
    assert exclusion_reason(interview, "15 Minutes to Freedom") is None
    assert exclusion_reason(teaser, "Some Show") == "trailer"
