"""Download one episode's audio, resuming partial files, optionally re-encoding."""

from __future__ import annotations

import errno
import logging
import re
import socket
from dataclasses import dataclass
from pathlib import Path

import requests
from urllib3.exceptions import NameResolutionError

from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.audio.disk import DiskSpaceError, ensure_free_space
from podcast_pipeline.audio.ffmpeg import EncodeError, decode_pcm, encode_opus
from podcast_pipeline.audio.naming import episode_stem, find_existing_audio, podcast_dir
from podcast_pipeline.config import CompressionConfig
from podcast_pipeline.http import make_session

logger = logging.getLogger(__name__)

# Downloads land here first and are renamed on success, so a partial file can
# never be mistaken for a complete one.
PARTIAL_SUFFIX = ".part"

# A download shorter than this fraction of the declared Content-Length is
# treated as incomplete and left in place for the next attempt to resume.
COMPLETE_FRACTION = 0.95

# Fallback sources (the unwrapped URL, Wayback copies) are fetched fresh into
# their own partial file, never resumed onto bytes from another source.
FALLBACK_PARTIAL_SUFFIX = ".fallback.part"

# Audio from a fallback source must decode to at least this fraction of the
# duration the feed declares. Archived MP3s are often truncated, and a header
# duration says what the file should hold, not what it does.
FALLBACK_MIN_DURATION_FRACTION = 0.9
# Decoding to this sample rate is enough to count seconds, and cheap to hold.
DURATION_PROBE_RATE = 1000

# ``episode_sources.source`` values for audio that did not come from the enclosure URL.
WAYBACK_AUDIO = "wayback_audio"        # the Wayback Machine's copy (ref: the archived URL)
UNWRAPPED_AUDIO = "unwrapped_audio"    # the host URL inside a tracking prefix (ref: that URL)

# Measurement prefixes wrapped around an enclosure: (host, path prefix), and
# everything after the prefix is the next URL in the chain, usually without
# its scheme. Only these are unwrapped; an unknown host is left alone.
# feedproxy.google.com/~r/... is not here: its target is not in the URL.
TRACKING_PREFIXES = [
    (re.compile(host), re.compile(prefix)) for host, prefix in [
        (r"dts\.podtrac\.com", r"/redirect\.[a-z0-9]+/"),
        (r"(www\.)?podtrac\.com", r"/pts/redirect\.[a-z0-9]+/"),
        (r"play\.podtrac\.com", r"/[^/]+/"),
        (r"(www\.)?chtbl\.com", r"/track/[^/]+/"),
        (r"chrt\.fm", r"/track/[^/]+/"),
        (r"pdst\.fm", r"/e/"),
        (r"mgln\.ai", r"/e/[^/]+/"),
        (r"arttrk\.com", r"/p/[^/]+/"),
        (r"pfx\.vpixl\.com", r"/[^/]+/"),
        # Seen nested in the Moth's 2026 feed: pdst.fm -> swap.fm -> podscribe -> castfire.
        (r"tracking\.swap\.fm", r"/track/[^/]+/"),
        (r"pscrb\.fm", r"/rss/p/"),
    ]
]

# Responses that mean the enclosure is gone, not that the request was unlucky.
DEAD_LINK_STATUSES = frozenset({403, 404, 410, 451})

# Content types a real enclosure is served with. Anything else must prove it is
# audio by its first bytes.
AUDIO_CONTENT_TYPES = ("audio/", "video/mp4", "application/ogg", "application/octet-stream",
                       "binary/octet-stream")


class DownloadError(RuntimeError):
    """The episode could not be fetched. Message is suitable for the DB.

    ``dead_link`` is set when the enclosure itself is gone (HTTP 403/404/410/451,
    the host no longer resolves, or it refuses connections) rather than the
    attempt failing for a reason a retry might fix (a timeout, a 5xx).
    """

    def __init__(self, message: str, dead_link: bool = False):
        super().__init__(message)
        self.dead_link = dead_link


@dataclass
class DownloadResult:
    path: Path
    original_size_mb: float
    compressed_size_mb: float
    is_compressed: bool
    reused: bool = False   # an existing file was found; nothing was fetched
    # Set when the enclosure was dead and a fallback served the audio:
    # WAYBACK_AUDIO or UNWRAPPED_AUDIO, and the URL that worked.
    fallback_source: str | None = None
    fallback_url: str | None = None


def unwrap_tracking_url(url: str) -> str:
    """The URL inside any known tracking prefixes, peeled innermost-first.

    ``https://dts.podtrac.com/redirect.mp3/chtbl.com/track/X/traffic.libsyn.com/show/ep.mp3?d=1``
    -> ``https://traffic.libsyn.com/show/ep.mp3?d=1``. A wrapped URL without a
    scheme inherits the outer one; the query string stays with the URL, as the
    redirect chain passes it through. Unknown hosts are returned unchanged, and
    so is a prefix whose remainder does not start with a host name.
    """
    while True:
        match = re.match(r"(https?)://([^/?#]+)(/[^?#]*)?(.*)$", url, re.IGNORECASE)
        if not match:
            return url
        scheme, host, path, rest = match.group(1), match.group(2).lower(), match.group(3) or "", match.group(4)
        for host_re, prefix_re in TRACKING_PREFIXES:
            prefix = prefix_re.match(path) if host_re.fullmatch(host) else None
            if prefix:
                inner = path[prefix.end():] + rest
                if not re.match(r"https?://", inner, re.IGNORECASE):
                    inner = f"{scheme}://{inner}"
                inner_host = re.match(r"https?://([^/?#]*)", inner, re.IGNORECASE).group(1)
                if "." in inner_host and " " not in inner_host:
                    url = inner
                    break
        else:
            return url


def is_dead_link(error: requests.RequestException) -> bool:
    """Whether a failed request says the URL is gone for good."""
    if isinstance(error, requests.HTTPError):
        return error.response is not None and error.response.status_code in DEAD_LINK_STATUSES
    if not isinstance(error, requests.ConnectionError) or isinstance(error, requests.Timeout):
        return False
    # requests wraps urllib3's MaxRetryError, whose ``reason`` is the real cause.
    stack, seen = [error], set()
    while stack:
        exc = stack.pop()
        if exc is None or id(exc) in seen:
            continue
        seen.add(id(exc))
        if isinstance(exc, (NameResolutionError, socket.gaierror, ConnectionRefusedError)):
            return True
        stack += [exc.__cause__, exc.__context__, getattr(exc, "reason", None)]
        stack += [a for a in exc.args if isinstance(a, BaseException)]
    return False


def looks_like_audio(head: bytes, content_type: str) -> bool:
    """Audio by its magic bytes, or by an audio content type on a non-markup body.

    The check exists for archived copies: the Wayback Machine can answer 200
    with an HTML page where the audio should be.
    """
    if (head[:3] == b"ID3" or head[:4] in (b"OggS", b"fLaC", b"RIFF", b"\x1aE\xdf\xa3")
            or head[4:8] == b"ftyp"
            or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)):   # MPEG/ADTS frame sync
        return True
    content_type = content_type.split(";")[0].strip().lower()
    return (any(content_type.startswith(t) for t in AUDIO_CONTENT_TYPES)
            and not head.lstrip()[:1] == b"<")


def wayback_audio_url(replay_root: str, audio_url: str, published_date: str | None) -> str:
    """Wayback's copy of ``audio_url`` nearest the publication date.

    Wayback redirects a timestamp to the nearest capture it holds ("2" means
    "the earliest you have"), or answers 404 if it never captured the URL.
    """
    stamp = (published_date or "")[:10].replace("-", "")
    if not (len(stamp) == 8 and stamp.isdigit()):
        stamp = "2"
    return f"{replay_root.rstrip('/')}/{stamp}id_/{audio_url}"


class AudioDownloader:
    def __init__(self, audio_dir: Path, compression: CompressionConfig,
                 timeout: int = 600, min_free_gb: float = 100.0, pool_size: int = 8,
                 session: requests.Session | None = None,
                 wayback_replay_url: str | None = None):
        """``wayback_replay_url`` (e.g. https://web.archive.org/web) turns on the
        fallback to archived audio for dead enclosures; None leaves it off."""
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.compression = compression
        self.timeout = timeout
        self.min_free_gb = min_free_gb
        self.session = session or make_session(pool_size=pool_size)
        self.wayback_replay_url = wayback_replay_url

    def download_episode(self, audio_url: str, podcast_title: str, episode_title: str,
                         guid: str | None, published_date: str | None = None,
                         declared_duration: int | None = None) -> DownloadResult:
        """Fetch an episode, or return the file already on disk for it.

        With the fallback on, a dead enclosure is retried, stopping at the first
        source that yields real audio: the URL inside its tracking prefixes
        (live), then the Wayback Machine's copy (nearest ``published_date``) of
        the original URL, then of the unwrapped one. A fallback file must look
        like audio and decode in full -- to at least 90% of
        ``declared_duration`` when the feed declares one -- and is then named
        and converted exactly like a normal download;
        ``fallback_source``/``fallback_url`` say where it came from.

        Raises DownloadError on failure and DiskSpaceError when the volume is
        too full to continue.
        """
        existing = find_existing_audio(self.audio_dir, podcast_title, episode_title, guid)
        if existing:
            size_mb = existing.stat().st_size / 1024 ** 2
            return DownloadResult(existing, size_mb, size_mb,
                                  is_compressed=existing.suffix == ".ogg", reused=True)

        ensure_free_space(self.audio_dir, self.min_free_gb)

        directory = podcast_dir(self.audio_dir, podcast_title)
        directory.mkdir(parents=True, exist_ok=True)
        stem = episode_stem(episode_title, guid)
        mp3_path = directory / f"{stem}.mp3"

        logger.info(f"Downloading: {episode_title} ({podcast_title})")
        fallback_source = fallback_url = None
        try:
            self._fetch(audio_url, mp3_path)
        except DownloadError as e:
            if not (self.wayback_replay_url and e.dead_link):
                raise
            fallback_source, fallback_url = self._fetch_fallback(audio_url, published_date, mp3_path, e,
                                                                 declared_duration)
            # A partial left by earlier attempts on the dead original is now moot.
            mp3_path.with_suffix(mp3_path.suffix + PARTIAL_SUFFIX).unlink(missing_ok=True)
        original_mb = mp3_path.stat().st_size / 1024 ** 2

        if self.compression.enabled and original_mb > self.compression.size_threshold_mb:
            ogg_path = directory / f"{stem}.ogg"
            try:
                encode_opus(mp3_path, ogg_path, bitrate=self.compression.bitrate)
            except EncodeError as e:
                # The MP3 is intact; keep it and let `convert-audio` retry later.
                logger.warning(f"Keeping MP3 for {episode_title}: re-encode failed: {e}")
            else:
                compressed_mb = ogg_path.stat().st_size / 1024 ** 2
                if not self.compression.keep_original:
                    mp3_path.unlink()
                logger.info(f"Re-encoded {episode_title}: {original_mb:.1f}MB -> {compressed_mb:.1f}MB")
                return DownloadResult(ogg_path, original_mb, compressed_mb, is_compressed=True,
                                      fallback_source=fallback_source, fallback_url=fallback_url)

        return DownloadResult(mp3_path, original_mb, original_mb, is_compressed=False,
                              fallback_source=fallback_source, fallback_url=fallback_url)

    def _fetch_fallback(self, audio_url: str, published_date: str | None, mp3_path: Path,
                        original_error: DownloadError,
                        declared_duration: int | None = None) -> tuple[str, str]:
        """Try each fallback source in turn; (source, URL that worked) for the first
        real audio, or a DownloadError listing every attempt."""
        inner = unwrap_tracking_url(audio_url)
        attempts = []
        if inner != audio_url:
            attempts.append((UNWRAPPED_AUDIO, "unwrapped", inner))
        attempts.append((WAYBACK_AUDIO, "wayback",
                         wayback_audio_url(self.wayback_replay_url, audio_url, published_date)))
        if inner != audio_url:
            attempts.append((WAYBACK_AUDIO, "wayback unwrapped",
                             wayback_audio_url(self.wayback_replay_url, inner, published_date)))
        failures = [f"original {audio_url}: {original_error}"]
        for source, label, url in attempts:
            logger.info(f"Dead enclosure {audio_url}; trying {label} {url}")
            try:
                served = self._fetch(url, mp3_path, resume=False,
                                     partial_suffix=FALLBACK_PARTIAL_SUFFIX, require_audio=True)
            except DownloadError as e:
                failures.append(f"{label} {url}: {e}")
                continue
            problem = self._truncation(mp3_path, declared_duration)
            if problem:
                mp3_path.unlink()
                failures.append(f"{label} {url}: {problem}")
                continue
            return source, served
        raise DownloadError("; ".join(failures))

    @staticmethod
    def _truncation(path: Path, declared_duration: int | None) -> str | None:
        """Why a fallback file is not the whole episode, or None if it is.

        The length is measured by decoding every sample; a header duration
        lies about truncated MP3s.
        """
        try:
            seconds = len(decode_pcm(path, sample_rate=DURATION_PROBE_RATE)) / DURATION_PROBE_RATE
        except EncodeError as e:
            return f"not decodable: {e}"
        if seconds <= 0:
            return "decodes to no audio"
        if declared_duration and seconds < declared_duration * FALLBACK_MIN_DURATION_FRACTION:
            return f"truncated: decodes to {seconds:.0f}s of {declared_duration}s declared"
        return None

    def _fetch(self, url: str, final_path: Path, chunk_size: int = 64 * 1024, *,
               resume: bool = True, partial_suffix: str = PARTIAL_SUFFIX,
               require_audio: bool = False) -> str:
        """Stream ``url`` to ``final_path`` via a sidecar partial file. Returns the
        URL the bytes finally came from (after redirects).

        With ``resume`` an existing partial is continued; without it the fetch
        starts over and a failed attempt leaves nothing behind.
        ``require_audio`` rejects a body that is not recognisably audio.
        """
        partial_path = final_path.with_suffix(final_path.suffix + partial_suffix)
        if not resume:
            partial_path.unlink(missing_ok=True)
        resume_pos = partial_path.stat().st_size if partial_path.exists() else 0

        try:
            headers = {"Range": f"bytes={resume_pos}-"} if resume_pos else {}
            response = self.session.get(url, headers=headers, stream=True, timeout=self.timeout)

            if resume_pos and response.status_code != 206:
                # 200: server ignored the range. 416: range past the end (the
                # remote file shrank or our partial is already complete).
                # Either way, start over.
                logger.warning(f"Server did not honour resume from byte {resume_pos}; restarting")
                resume_pos = 0
                if response.status_code == 416:
                    response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            if resume_pos and response.status_code == 206:
                content_range = response.headers.get("content-range", "")
                if "/" in content_range:
                    total_size = int(content_range.rsplit("/", 1)[1])

            with open(partial_path, "ab" if resume_pos else "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
        except requests.RequestException as e:
            if not resume:
                partial_path.unlink(missing_ok=True)
            raise DownloadError(f"request failed: {e}", dead_link=is_dead_link(e)) from e
        except OSError as e:
            if e.errno == errno.ENOSPC:
                raise DiskSpaceError(f"Disk full while writing {final_path}") from e
            raise

        size = partial_path.stat().st_size
        if size < MIN_AUDIO_BYTES:
            partial_path.unlink()
            raise DownloadError(f"implausibly small response: {size} bytes")
        if total_size and size < total_size * COMPLETE_FRACTION:
            if not resume:
                partial_path.unlink()
            # Otherwise leave the partial file for the next attempt to resume.
            raise DownloadError(f"incomplete: {size}/{total_size} bytes")
        if require_audio:
            with open(partial_path, "rb") as f:
                head = f.read(16)
            content_type = response.headers.get("content-type", "")
            if not looks_like_audio(head, content_type):
                partial_path.unlink()
                raise DownloadError(f"not audio: content-type {content_type!r}, starts {head[:8]!r}")

        partial_path.replace(final_path)
        return response.url
