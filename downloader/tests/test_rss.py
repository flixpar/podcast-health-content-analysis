from unittest.mock import Mock

import pytest
import requests

from podcast_pipeline.rss import FeedError, _duration_seconds, fetch_feed, parse_feed

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
