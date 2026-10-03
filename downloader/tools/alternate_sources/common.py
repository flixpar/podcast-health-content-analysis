"""Shared pieces of the alternate-source research tools.

These tools look for audio the pipeline could not fetch (dead enclosures) and
for episodes no feed lists any more (empty study windows), through routes the
pipeline itself does not take: Wayback prefix searches, archive.org items,
hosts' full-catalog APIs. They only read the database; what they find is
written as JSONL in the ``import-episodes`` format, and loading it is a
separate, locked step.

Everything here is network-polite by construction: one ``Fetcher`` paces
requests per host, and only small ranged GETs are made for audio (magic bytes
and the total size, never a full download).
"""

from __future__ import annotations

import json
import re
import sqlite3
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlsplit

import requests

DOWNLOADER = Path(__file__).resolve().parents[2]
DB = DOWNLOADER / "data" / "podcast_metadata.db"
USER_AGENT = "Mozilla/5.0 (compatible; PodcastTranscriber/1.0; research gap-fill)"

# Seconds between two requests to the same host. The Wayback Machine refuses
# connections outright for a while when hit faster (seen on 2026-10-02: the
# download fallback lost ~75 episodes to "Connection refused").
DEFAULT_HOST_DELAY = 1.0
HOST_DELAYS = {"web.archive.org": 6.0, "archive.org": 1.5}
# Waits before retrying a refused connection (a host-level rate limit).
REFUSED_WAITS = (120.0, 300.0, 600.0)
PROBE_BYTES = 65536
MAX_WAYBACK_HOPS = 15

AUDIO_CONTENT_TYPES = ("audio/", "application/octet-stream", "binary/octet-stream", "video/mp4")


def open_db(path: Path = DB) -> sqlite3.Connection:
    """The catalog, read-only."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def title_key(title: str) -> str:
    """Case, punctuation and spacing removed (the key ``import-episodes`` matches on)."""
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


# --- polite HTTP -----------------------------------------------------------------

class Fetcher:
    """A requests session that waits between requests to the same host."""

    def __init__(self, session: requests.Session | None = None,
                 delays: dict[str, float] | None = None, default_delay: float = DEFAULT_HOST_DELAY,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)
        self.session.headers["User-Agent"] = USER_AGENT
        self.delays = {**HOST_DELAYS, **(delays or {})}
        self.default_delay = default_delay
        self._sleep, self._clock = sleep, clock
        self._last: dict[str, float] = {}

    def _wait(self, url: str) -> None:
        host = (urlsplit(url).hostname or "").lower()
        delay = self.delays.get(host, self.default_delay)
        last = self._last.get(host)
        if last is not None:
            remaining = last + delay - self._clock()
            if remaining > 0:
                self._sleep(remaining)
        self._last[host] = self._clock()

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET, paced per host. A refused connection is a host's rate limit
        (the Wayback Machine blocks an address for minutes), so it is waited
        out (``REFUSED_WAITS``) before being raised."""
        kwargs.setdefault("timeout", 60)
        host = (urlsplit(url).hostname or "").lower()
        for wait in (*REFUSED_WAITS, None):
            self._wait(url)
            try:
                return self.session.get(url, **kwargs)
            except requests.ConnectionError as e:
                if wait is None or "Connection refused" not in str(e):
                    raise
                print(f"  {host} refused the connection; waiting {wait:.0f}s", flush=True)
                self._sleep(wait)
            finally:
                self._last[host] = self._clock()
        raise AssertionError("unreachable")

    def get_json(self, url: str, attempts: int = 4, backoff: float = 10.0, **kwargs):
        """JSON from ``url``; retries connection errors and 429/5xx, raises otherwise."""
        problem = ""
        for attempt in range(attempts):
            if attempt:
                self._sleep(backoff * 2 ** (attempt - 1))
            try:
                r = self.get(url, **kwargs)
            except requests.RequestException as e:
                problem = f"request failed: {e}"
                continue
            if r.status_code == 429 or r.status_code >= 500:
                problem = f"HTTP {r.status_code}"
                continue
            r.raise_for_status()
            if not r.content.strip():
                problem = "empty body"
                continue
            return r.json()
        raise RuntimeError(f"{url}: {problem} after {attempts} attempts")


# --- audio probing ----------------------------------------------------------------

def is_audio_head(head: bytes, content_type: str = "") -> bool:
    """Audio by magic bytes (or an audio type on a body that is not markup)."""
    if (head[:3] == b"ID3" or head[:4] in (b"OggS", b"fLaC", b"RIFF", b"\x1aE\xdf\xa3")
            or head[4:8] == b"ftyp"
            or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)):
        return True
    ct = content_type.split(";")[0].strip().lower()
    return ct.startswith("audio/") and head.lstrip()[:1] != b"<"


def id3_text(head: bytes, frame_id: bytes = b"TIT2") -> str | None:
    """A text frame (default: the title) from a leading ID3v2.3/2.4 tag."""
    if head[:3] != b"ID3" or head[3] not in (3, 4):
        return None
    end = min(id3_size(head), len(head))
    i = 10
    while i + 10 <= end:
        fid = head[i:i + 4]
        raw = head[i + 4:i + 8]
        size = (((raw[0] << 21) | (raw[1] << 14) | (raw[2] << 7) | raw[3]) if head[3] == 4
                else struct.unpack(">I", raw)[0])
        if not fid.strip(b"\x00") or size <= 0:
            return None
        if fid == frame_id:
            body = head[i + 10:i + 10 + size]
            if not body:
                return None
            enc, text = body[0], body[1:]
            codec = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}.get(enc, "latin-1")
            return text.decode(codec, errors="replace").strip("\x00").strip()
        i += 10 + size
    return None


_BITRATES = {  # (version_is_mpeg1, layer) -> kbps table indexed by the 4-bit field
    (True, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],
    (False, 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
    (True, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0],
}
_SAMPLE_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def id3_size(head: bytes) -> int:
    """Bytes taken by a leading ID3v2 tag (0 if none)."""
    if head[:3] != b"ID3" or len(head) < 10:
        return 0
    b = head[6:10]
    size = (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]
    footer = 10 if head[5] & 0x10 else 0
    return 10 + size + footer


def mp3_duration(head: bytes, total_size: int | None, audio_start: int | None = None) -> dict | None:
    """Estimated duration of an MP3 from its first bytes and its total size.

    Uses the Xing/Info/VBRI frame count when present (exact for VBR files),
    else the first frame's bitrate (exact for CBR). ``head`` is the start of
    the file, or, when ``audio_start`` is given, the bytes from that offset
    (the end of an ID3 tag too large to fit in the first read). None when the
    first frame is not inside ``head`` or does not parse.
    """
    if audio_start is None:
        start = audio_start = id3_size(head)
    else:
        start = 0
    if start >= len(head):
        return None
    i = start
    # Skip padding between the tag and the first frame.
    while i + 4 <= len(head) and not (head[i] == 0xFF and head[i + 1] & 0xE0 == 0xE0):
        i += 1
        if i - start > 8192:
            return None
    if i + 4 > len(head):
        return None
    h = struct.unpack(">I", head[i:i + 4])[0]
    version_bits = (h >> 19) & 3          # 3 = MPEG1, 2 = MPEG2, 0 = MPEG2.5
    layer_bits = (h >> 17) & 3            # 1 = layer III, 2 = layer II
    bitrate_idx = (h >> 12) & 0xF
    rate_idx = (h >> 10) & 3
    channel_mode = (h >> 6) & 3
    if version_bits == 1 or layer_bits not in (1, 2) or rate_idx == 3:
        return None
    layer = 3 if layer_bits == 1 else 2
    mpeg1 = version_bits == 3
    table = _BITRATES.get((mpeg1, layer)) or _BITRATES[(False, 3)]
    kbps = table[bitrate_idx]
    sample_rate = _SAMPLE_RATES[version_bits][rate_idx]
    samples_per_frame = 1152 if (mpeg1 or layer == 2) else 576
    # Xing/Info sits after the side information; VBRI 32 bytes after the header.
    side = (32 if channel_mode != 3 else 17) if mpeg1 else (17 if channel_mode != 3 else 9)
    for off, tag in ((i + 4 + side, (b"Xing", b"Info")), (i + 36, (b"VBRI",))):
        if head[off:off + 4] in tag:
            if tag[0] == b"VBRI":
                frames = struct.unpack(">I", head[off + 14:off + 18])[0]
            else:
                flags = struct.unpack(">I", head[off + 4:off + 8])[0]
                if not flags & 1:
                    break
                frames = struct.unpack(">I", head[off + 8:off + 12])[0]
            if frames:
                return {"seconds": round(frames * samples_per_frame / sample_rate, 1),
                        "method": "xing", "kbps": kbps, "sample_rate": sample_rate}
    if not kbps or total_size is None:
        return None
    return {"seconds": round((total_size - audio_start) * 8 / (kbps * 1000), 1),
            "method": "cbr", "kbps": kbps, "sample_rate": sample_rate}


@dataclass
class Probe:
    url: str                    # what was asked for
    final_url: str              # where the bytes came from
    status: int | None
    content_type: str
    total_size: int | None
    is_audio: bool
    duration: dict | None
    error: str = ""
    id3_title: str | None = None

    def to_dict(self) -> dict:
        return {"url": self.url, "final_url": self.final_url, "status": self.status,
                "content_type": self.content_type, "total_size": self.total_size,
                "is_audio": self.is_audio, "duration": self.duration, "error": self.error,
                "id3_title": self.id3_title}


def _total_size(r: requests.Response) -> int | None:
    cr = r.headers.get("Content-Range", "")
    m = re.match(r"bytes \d+-\d+/(\d+)", cr)
    if m:
        return int(m.group(1))
    if r.status_code == 200 and r.headers.get("Content-Length", "").isdigit():
        return int(r.headers["Content-Length"])
    return None


def _read_head(r: requests.Response, nbytes: int) -> bytes:
    head = b""
    for chunk in r.iter_content(8192):
        head += chunk
        if len(head) >= nbytes:
            break
    r.close()
    return head[:nbytes]


def _probe_response(fetcher: Fetcher, url: str, r: requests.Response, head: bytes) -> Probe:
    """A Probe from a ranged response whose first bytes are ``head``."""
    ct = r.headers.get("Content-Type", "")
    total = _total_size(r)
    ok = r.status_code in (200, 206) and is_audio_head(head, ct)
    duration = mp3_duration(head, total) if ok else None
    tag = id3_size(head)
    note = ""
    if ok and duration is None and tag + 4 > len(head) and total and tag < total:
        # A large tag (cover art) hides the first frame; read just past it.
        try:
            r2 = fetcher.get(r.url, headers={"Range": f"bytes={tag}-{tag + 4095}"})
        except requests.RequestException as e:
            note = f"frame after the ID3 tag not read: {e}"
        else:
            if r2.status_code == 206:
                duration = mp3_duration(r2.content, total, audio_start=tag)
            else:
                note = f"frame after the ID3 tag not read: HTTP {r2.status_code}"
    error = note if ok else f"HTTP {r.status_code}, {ct or 'no content type'}, not audio"
    return Probe(url, r.url, r.status_code, ct, total, ok, duration, error,
                 id3_text(head) if ok else None)


def range_probe(fetcher: Fetcher, url: str, nbytes: int = PROBE_BYTES) -> Probe:
    """The first ``nbytes`` of ``url`` (following redirects): is it audio, how long."""
    try:
        r = fetcher.get(url, headers={"Range": f"bytes=0-{nbytes - 1}"}, stream=True,
                        allow_redirects=True)
        head = _read_head(r, nbytes)
    except requests.RequestException as e:
        return Probe(url, url, None, "", None, False, None, f"request failed: {e}")
    return _probe_response(fetcher, url, r, head)


def duration_matches(probe: Probe, declared: int | float | None,
                     low: float = 0.9, high: float = 1.35) -> bool | None:
    """Whether a probed file's length is plausible for a declared duration.

    The range is lopsided on purpose: dynamically inserted ads make an archived
    copy longer than the feed's figure far more often than shorter. None when
    either side is unknown.
    """
    if not declared or not probe.duration:
        return None
    ratio = probe.duration["seconds"] / declared
    return low <= ratio <= high


# --- tracking prefixes -----------------------------------------------------------

# Prefixes ``download.unwrap_tracking_url`` does not peel (as of 2026-10-03),
# seen in the enclosures of the apple-top24-monthly study. Research use only;
# reported to the coordinator rather than added to the pipeline.
EXTRA_TRACKING_PREFIXES = [
    (r"(www\.)?claritaspod\.com", r"/measure/"),
    (r"prfx\.byspotify\.com", r"/e/"),
    (r"clrtpod\.com", r"/m/"),
    (r"pdrl\.fm", r"/[0-9a-f]+/"),
    (r"swap\.fm", r"/track/[^/]+/"),
    (r"pdcn\.co", r"/e/"),
    (r"dts\.podtrac\.com", r"/pts/redirect\.mp3/"),
    (r"prefix\.up\.audio", r"/s/"),
    (r"verifi\.podscribe\.com", r"/rss/p/"),
    (r"p\.podderapp\.com", r"/\d+/"),
    (r"s\.gum\.fm", r"/s-[0-9a-f]+/"),
    (r"op3\.dev", r"/e(,[^/]*)?/"),
]


def peel_extra(url: str) -> str:
    """One layer of an ``EXTRA_TRACKING_PREFIXES`` prefix removed, or ``url`` unchanged."""
    m = re.match(r"(https?)://([^/?#]+)(/.*)?$", url, re.IGNORECASE)
    if not m:
        return url
    scheme, host, rest = m.group(1), m.group(2).lower(), m.group(3) or ""
    for host_re, prefix_re in EXTRA_TRACKING_PREFIXES:
        if re.fullmatch(host_re, host):
            pm = re.match(prefix_re, rest)
            if pm:
                inner = rest[pm.end():]
                if not re.match(r"https?://", inner, re.IGNORECASE):
                    inner = f"{scheme}://{inner}"
                inner_host = re.match(r"https?://([^/?#]*)", inner, re.IGNORECASE).group(1)
                if "." in inner_host:
                    return inner
    return url


# Hosts that served a publisher's files under a measurement domain that no
# longer resolves, and the origin that still serves the same path.
ORIGIN_REWRITES = [
    # NPR, 2015-2017: npr.mc.tritondigital.com/<mount>/media/anon.npr-{mp3,podcasts}/...
    # (mounts seen: NPR_<feed id>, WAITWAIT_PODCAST)
    (re.compile(r"https?://npr\.mc\.tritondigital\.com/[A-Z0-9_]+/media/(anon\.npr-(?:mp3|podcasts)/.*)$",
                re.I),
     r"https://edge1.pod.npr.org/\1"),
    # Pardon My Take, 2016: Barstool moved the launch-era files from LaunchPod
    # (noxsolutions, dead) to its own bucket under the same names, where the
    # current feed's 2016 enclosures (pmt46.mp3, ...) also live.
    (re.compile(r"https?://podone\.noxsolutions\.com/launchpod/pardonmytake/mp3/([^/?#]+)", re.I),
     r"https://landmark.barstoolsports.net/pardon-my-take/\1"),
]


def origin_url(url: str) -> str:
    """``url`` with a dead measurement host replaced by the publisher's origin."""
    for pattern, repl in ORIGIN_REWRITES:
        if pattern.match(url):
            return pattern.sub(repl, url)
    return url


def deep_unwrap(url: str) -> str:
    """The pipeline's unwrapping, plus the extra prefixes, until nothing changes."""
    from podcast_pipeline.audio.download import unwrap_tracking_url
    while True:
        inner = peel_extra(unwrap_tracking_url(url))
        if inner == url:
            return url
        url = inner


# --- Wayback ----------------------------------------------------------------------

def strip_query(url: str) -> str:
    """``host/path`` without scheme or query: the form CDX prefix searches take."""
    parts = urlsplit(url)
    return f"{parts.netloc}{parts.path}"


def cdx_prefix(fetcher: Fetcher, cdx_url: str, prefix: str, limit: int = 200) -> list[dict]:
    """Every capture whose URL starts with ``prefix`` (any status).

    CDX answers a dropped (rate-limited) request with an empty body, which must
    not be read as "never archived"; ``get_json`` retries those. A genuine
    "nothing" is ``[]``.
    """
    params = {"url": prefix, "matchType": "prefix", "output": "json", "limit": str(limit),
              "fl": "timestamp,original,statuscode,mimetype,length,digest"}
    data = fetcher.get_json(cdx_url, params=params)
    if not data:
        return []
    fields, *rows = data
    return [dict(zip(fields, r)) for r in rows]


def wayback_resolve(fetcher: Fetcher, replay_root: str, timestamp: str, original: str,
                    max_hops: int = MAX_WAYBACK_HOPS,
                    nbytes: int = PROBE_BYTES) -> tuple[Probe | None, list[str], str]:
    """Follow an archived redirect chain to the archived bytes, and probe them.

    Returns (probe of the final replay URL, hops, problem). Wayback answers a
    capture of a redirect with a 302 into another replay URL; chains through
    tracking hosts can loop between near timestamps (requests gives up after
    30), so hops are followed by hand and a revisited URL ends the chain. Every
    hop asks for a range, so the last one already carries the probe bytes.
    """
    url = f"{replay_root.rstrip('/')}/{timestamp}id_/{original}"
    seen, hops = set(), []
    for _ in range(max_hops):
        if url in seen:
            return None, hops, "redirect loop"
        seen.add(url)
        hops.append(url)
        try:
            r = fetcher.get(url, headers={"Range": f"bytes=0-{nbytes - 1}"},
                            allow_redirects=False, stream=True)
            if r.status_code in (200, 206):
                return _probe_response(fetcher, url, r, _read_head(r, nbytes)), hops, ""
            r.close()
        except requests.RequestException as e:
            return None, hops, f"request failed: {e}"
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("Location", "")
            if not loc:
                return None, hops, "redirect without Location"
            if loc.startswith("/"):
                loc = f"https://web.archive.org{loc}"
            url = loc
            continue
        return None, hops, f"HTTP {r.status_code}"
    return None, hops, "too many hops"
