"""Parse the transcript formats publishers attach to their feeds.

Every parser returns timed ``Segment`` lists; ``parse_transcript`` sniffs the
format from the content type and the body itself, since feeds routinely
mislabel what they serve.
"""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from podcast_pipeline.models import Segment

TIMECODE = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[.,](?P<ms>\d{1,3})"
    r"\s*-->\s*"
    r"(?P<h2>\d{1,2}):(?P<m2>\d{2}):(?P<s2>\d{2})[.,](?P<ms2>\d{1,3})"
)

# Omny and similar serve "TextWithTimestamps": bare "HH:MM:SS" lines, then text.
PLAIN_TIMESTAMP = re.compile(r"^\s*(\d{1,2}):(\d{2}):(\d{2})(?:[.,](\d{1,3}))?\s*$")

# An HTML transcript page must carry at least this many words to count as a
# transcript rather than a player page with boilerplate.
MIN_HTML_WORDS = 200


def parse_transcript(body: str, content_type: str = "") -> tuple[list[Segment], str]:
    """Return (segments, detected_format). Empty segments mean nothing usable was found."""
    stripped = body.strip()
    content_type = content_type.lower()
    if not stripped:
        return [], "empty"

    if "json" in content_type or stripped[0] in "[{":
        try:
            segments = parse_json(stripped)
        except (json.JSONDecodeError, TypeError, AttributeError):
            segments = []
        if segments:
            return segments, "json"

    if TIMECODE.search(stripped):
        segments = parse_srt_vtt(stripped)
        if segments:
            return segments, "srt/vtt"

    if any(PLAIN_TIMESTAMP.match(line) for line in stripped.split("\n")[:20]):
        segments = parse_plain_timestamped(stripped)
        if segments:
            return segments, "timestamped-text"

    if "html" in content_type or stripped.lower().startswith(("<!doctype", "<html")):
        text = html_to_text(stripped)
        if len(text.split()) >= MIN_HTML_WORDS:
            return [Segment(text=text)], "html"
        return [], "html"

    # Untimed plain text still carries the words, which is what matters most.
    return [Segment(text=re.sub(r"\s+", " ", stripped))], "plain-text"


def _seconds(h, m, s, ms=None) -> float:
    total = int(h) * 3600 + int(m) * 60 + int(s)
    if ms:
        total += int(str(ms).ljust(3, "0")) / 1000
    return total


def parse_srt_vtt(body: str) -> list[Segment]:
    """SRT or WebVTT cues -> timed segments."""
    segments = []
    for block in re.split(r"\n\s*\n", body.replace("\r\n", "\n")):
        match = TIMECODE.search(block)
        if not match:
            continue
        g = match.groupdict()
        after_timecode = block[match.end():].split("\n")[1:]
        text = " ".join(line.strip() for line in after_timecode
                        if line.strip() and not line.strip().isdigit())
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            segments.append(Segment(text=text,
                                    start=_seconds(g["h"], g["m"], g["s"], g["ms"]),
                                    end=_seconds(g["h2"], g["m2"], g["s2"], g["ms2"])))
    return segments


def parse_plain_timestamped(body: str) -> list[Segment]:
    """Alternating 'HH:MM:SS' / text lines -> segments closed at the next timestamp."""
    segments: list[Segment] = []
    start = None
    buffer: list[str] = []

    def flush():
        if start is not None and buffer:
            segments.append(Segment(text=" ".join(buffer).strip(), start=start))

    for line in body.replace("\r\n", "\n").split("\n"):
        m = PLAIN_TIMESTAMP.match(line)
        if m:
            flush()
            start = _seconds(m.group(1), m.group(2), m.group(3), m.group(4))
            buffer = []
        elif line.strip():
            buffer.append(line.strip())
    flush()

    for current, following in zip(segments, segments[1:]):
        current.end = following.start
    return segments


def parse_json(body: str) -> list[Segment]:
    """Podcast 2.0 JSON transcripts: {"segments": [{"startTime", "endTime", "body"}]}."""
    data = json.loads(body)
    raw = data.get("segments") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        return []
    segments = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = (item.get("body") or item.get("text") or "").strip()
        if text:
            segments.append(Segment(text=text,
                                    start=item.get("startTime", item.get("start")),
                                    end=item.get("endTime", item.get("end"))))
    return segments


def html_to_text(body: str) -> str:
    soup = BeautifulSoup(body, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()
