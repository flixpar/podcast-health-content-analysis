from unittest.mock import Mock

import pytest
import requests

from podcast_pipeline.rss import FeedError, _duration_seconds, fetch_feed, parse_feed, read_feed

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>Test Podcast</title>
    <item>
      <title>Episode 1</title>
      <description>&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;</description>
      <enclosure url="https://example.com/1.mp3" type="audio/mpeg" length="1000000"/>
      <guid>ep-1</guid>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <itunes:duration>1:30:00</itunes:duration>
      <itunes:explicit>yes</itunes:explicit>
      <podcast:transcript url="https://example.com/1.srt" type="application/srt"/>
    </item>
    <item>
      <title>Video only</title>
      <enclosure url="https://example.com/2.mp4" type="video/mp4" length="5"/>
      <guid>ep-2</guid>
    </item>
    <item>
      <title>Episode 3</title>
      <enclosure url="https://example.com/3.mp3" type="audio/mpeg"/>
      <itunes:duration>1800</itunes:duration>
    </item>
  </channel>
</rss>"""


def test_parse_feed_extracts_episodes():
    episodes = parse_feed(FEED)
    assert [e.title for e in episodes] == ["Episode 1", "Episode 3"]   # video entry skipped

    first = episodes[0]
    assert first.guid == "ep-1"
    assert first.audio_url == "https://example.com/1.mp3"
    assert first.audio_length == 1000000
    assert first.description == "Hello world"
    assert first.published_date == "2024-01-01T00:00:00"
    assert first.duration_seconds == 5400
    assert first.explicit is True
    assert first.transcript_url == "https://example.com/1.srt"
    assert first.has_transcript

    third = episodes[1]
    assert third.guid == "https://example.com/3.mp3"   # falls back to the audio URL
    assert third.duration_seconds == 1800
    assert not third.has_transcript


def test_garbage_is_an_error():
    with pytest.raises(FeedError):
        parse_feed(b"this is not a feed")


@pytest.mark.parametrize("value,expected", [
    ("30:00", 1800), ("1:30:00", 5400), ("45", 45), (1800, 1800), ("", None), ("abc", None),
    ("01:02:03.5", 3723),
])
def test_duration_parsing(value, expected):
    assert _duration_seconds(value) == expected


def test_fetch_feed_wraps_http_failures():
    session = Mock()
    session.get.side_effect = requests.ConnectionError("boom")
    with pytest.raises(FeedError, match="fetch failed"):
        fetch_feed("https://x/feed", session)


def test_fetch_feed_parses_response_body():
    session = Mock()
    session.get.return_value = Mock(content=FEED, raise_for_status=Mock())
    assert len(fetch_feed("https://x/feed", session, timeout=5)) == 2
    session.get.assert_called_once_with("https://x/feed", timeout=5)


def test_fetch_feed_retries_uncompressed_when_gzip_is_corrupt():
    """Megaphone serves some feeds with a gzip body that will not inflate but
    a perfectly good identity body; without the retry the show looks dead."""
    session = Mock()
    good = Mock(content=FEED, raise_for_status=Mock())
    session.get.side_effect = [requests.exceptions.ContentDecodingError("bad gzip"), good]

    assert len(fetch_feed("https://x/feed", session, timeout=5)) == 2

    assert session.get.call_count == 2
    assert session.get.call_args_list[1].kwargs["headers"] == {"Accept-Encoding": "identity"}


def test_fetch_feed_gives_up_if_the_uncompressed_retry_also_fails():
    session = Mock()
    session.get.side_effect = [requests.exceptions.ContentDecodingError("bad gzip"),
                              requests.ConnectionError("boom")]
    with pytest.raises(FeedError, match="fetch failed"):
        fetch_feed("https://x/feed", session)


def test_feedburner_proxy_enclosures_use_the_original_link():
    feed = b"""<rss xmlns:feedburner="http://rssnamespace.org/feedburner/ext/1.0" version="2.0">
    <channel><title>t</title><item><guid>g1</guid><title>e</title>
    <enclosure url="http://feedproxy.google.com/~r/x/~5/abc/ep.mp3" type="audio/mpeg" length="1"/>
    <feedburner:origEnclosureLink>http://www.podtrac.com/pts/redirect.mp3/host.com/ep.mp3</feedburner:origEnclosureLink>
    </item></channel></rss>"""
    [episode] = parse_feed(feed)
    assert episode.audio_url == "http://www.podtrac.com/pts/redirect.mp3/host.com/ep.mp3"


# --- paged feeds -----------------------------------------------------------------

def page(guids, next_href=None, rel="next"):
    """A feed document listing ``guids``, optionally linking to an older page."""
    link = f'<atom:link rel="{rel}" href="{next_href}"/>' if next_href else ""
    items = "".join(f"<item><guid>{g}</guid><title>{g}</title>"
                    f'<enclosure url="https://a/{g}.mp3" type="audio/mpeg"/></item>' for g in guids)
    return (f'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>t</title>'
            f'<atom:link rel="self" href="https://x/feed"/>{link}{items}</channel></rss>').encode()


class Pages:
    """A fake session serving fixed documents by URL; anything else is a 404."""

    def __init__(self, docs):
        self.docs = docs
        self.requested = []

    def get(self, url, timeout=None, headers=None):
        self.requested.append(url)
        if url not in self.docs:
            raise requests.HTTPError(f"404 for {url}")
        return Mock(content=self.docs[url], url=url, raise_for_status=Mock())


def test_unpaged_feed_reads_exactly_as_before():
    session = Pages({"https://x/feed": FEED})
    read = read_feed("https://x/feed", session, max_pages=10)
    assert [e.guid for e in read.episodes] == [e.guid for e in parse_feed(FEED)]
    assert (read.pages, read.stopped, read.partial) == (1, "complete", False)


def test_follows_next_links_and_merges_pages_newest_first():
    session = Pages({
        "https://x/feed": page(["e5", "e4"], "https://x/feed?page=2"),
        "https://x/feed?page=2": page(["e4", "e3", "e2"], "?page=3"),     # overlap; relative link
        "https://x/feed?page=3": page(["e1"]),
    })
    read = read_feed("https://x/feed", session, max_pages=10)
    assert [e.guid for e in read.episodes] == ["e5", "e4", "e3", "e2", "e1"]
    assert (read.pages, read.stopped) == (3, "complete")


def test_prev_archive_links_are_followed():
    session = Pages({"https://x/feed": page(["new"], "https://x/archive/1", rel="prev-archive"),
                     "https://x/archive/1": page(["old"])})
    assert [e.guid for e in read_feed("https://x/feed", session, max_pages=5).episodes] == ["new", "old"]


def test_paging_stops_on_a_loop_and_on_a_page_with_nothing_new():
    loop = Pages({"https://x/feed": page(["a"], "https://x/p2"),
                  "https://x/p2": page(["b"], "https://x/feed")})
    read = read_feed("https://x/feed", loop, max_pages=10)
    assert ([e.guid for e in read.episodes], read.stopped) == (["a", "b"], "loop")

    stale = Pages({"https://x/feed": page(["a"], "https://x/p2"),
                   "https://x/p2": page(["a"], "https://x/p3"),
                   "https://x/p3": page(["z"])})
    read = read_feed("https://x/feed", stale, max_pages=10)
    assert ([e.guid for e in read.episodes], read.stopped) == (["a"], "no_new_items")
    assert "https://x/p3" not in stale.requested


def test_paging_is_bounded_and_a_cut_short_read_says_so():
    docs = {f"https://x/p{i}": page([f"e{i}"], f"https://x/p{i + 1}") for i in range(1, 10)}
    read = read_feed("https://x/p1", Pages(docs), max_pages=3)
    assert [e.guid for e in read.episodes] == ["e1", "e2", "e3"]
    assert read.partial and read.stopped == "max_pages" and "https://x/p4" in read.error


def test_a_failed_later_page_keeps_the_earlier_ones():
    session = Pages({"https://x/feed": page(["a"], "https://x/gone")})
    read = read_feed("https://x/feed", session, max_pages=5)
    assert [e.guid for e in read.episodes] == ["a"]
    assert read.partial and read.stopped == "page_error" and "404" in read.error


def test_a_failed_first_page_is_a_feed_error():
    with pytest.raises(FeedError, match="fetch failed"):
        read_feed("https://x/feed", Pages({}), max_pages=5)
    with pytest.raises(FeedError, match="unparseable"):
        read_feed("https://x/feed", Pages({"https://x/feed": b"not a feed"}), max_pages=5)


def test_megaphone_feeds_are_read_with_limit_and_offset():
    """Megaphone caps a feed at a per-show default (ESPN: 200) unless asked
    for more; it publishes no next link, so full pages are followed by offset."""
    base = "https://feeds.megaphone.fm/ESP123"
    session = Pages({
        f"{base}?limit=2": page(["e5", "e4"]),
        f"{base}?limit=2&offset=2": page(["e3", "e2"]),
        f"{base}?limit=2&offset=4": page(["e1"]),
    })
    read = read_feed(base, session, max_pages=10, page_size=2)
    assert [e.guid for e in read.episodes] == ["e5", "e4", "e3", "e2", "e1"]
    assert (read.pages, read.stopped) == (3, "complete")

    # A proxy in front of Megaphone drops the query, so only Megaphone's own host is paged.
    proxied = Pages({"https://rss.pdrl.fm/abc/feeds.megaphone.fm/ESP123": page(["e5", "e4"])})
    assert read_feed("https://rss.pdrl.fm/abc/feeds.megaphone.fm/ESP123", proxied,
                     max_pages=10, page_size=2).pages == 1
