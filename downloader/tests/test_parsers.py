import json

from podcast_pipeline.transcripts.parsers import parse_transcript

SRT = """1
00:00:01,000 --> 00:00:03,500
Hello <i>there</i>.

2
00:00:03,500 --> 00:00:05,000
Second cue
continues here.
"""

VTT = """WEBVTT

00:00:01.000 --> 00:00:03.500 position:50%
Hello there.
"""


def test_srt():
    segments, fmt = parse_transcript(SRT, "application/srt")
    assert fmt == "srt/vtt"
    assert [(s.text, s.start, s.end) for s in segments] == [
        ("Hello there.", 1.0, 3.5), ("Second cue continues here.", 3.5, 5.0)]


def test_vtt_ignores_cue_settings():
    segments, fmt = parse_transcript(VTT, "text/vtt")
    assert fmt == "srt/vtt" and segments[0].text == "Hello there."


def test_podcast20_json():
    body = json.dumps({"segments": [{"startTime": 0, "endTime": 2.5, "body": "Hi"},
                                    {"startTime": 2.5, "endTime": 4, "body": ""}]})
    segments, fmt = parse_transcript(body, "application/json")
    assert fmt == "json" and len(segments) == 1 and segments[0].end == 2.5


def test_plain_timestamped_text():
    body = "00:00:00\nFirst bit\n00:00:10\nSecond bit\nmore\n00:00:20\nLast"
    segments, fmt = parse_transcript(body, "text/plain")
    assert fmt == "timestamped-text"
    assert [(s.text, s.start, s.end) for s in segments] == [
        ("First bit", 0, 10), ("Second bit more", 10, 20), ("Last", 20, None)]


def test_html_requires_substance():
    short = "<html><body><nav>menu</nav><p>Just a player page</p></body></html>"
    assert parse_transcript(short, "text/html") == ([], "html")
    long = "<html><body><p>" + "word " * 300 + "</p><script>x()</script></body></html>"
    segments, fmt = parse_transcript(long, "text/html")
    assert fmt == "html" and "x()" not in segments[0].text and len(segments[0].text.split()) == 300


def test_plain_text_and_empty():
    segments, fmt = parse_transcript("  some   untimed\ntext ", "text/plain")
    assert fmt == "plain-text" and segments[0].text == "some untimed text" and segments[0].start is None
    assert parse_transcript("   ", "") == ([], "empty")
