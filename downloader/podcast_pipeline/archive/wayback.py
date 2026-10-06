"""The Wayback Machine: CDX capture listings and archived snapshots, cached on disk.

Lessons from ``analysis/chart_archive`` (see its README) that this module encodes:

- The CDX API silently drops *parallel* requests: the dropped one comes back as
  an empty body, which reads exactly like "never archived". Every CDX query in
  the process therefore goes through one lock, is paced
  (``cdx_delay_seconds`` between requests), and an empty or malformed body is
  retried with backoff rather than trusted. A genuine "no captures" is the JSON
  body ``[]``.
- Only validated listings are cached, so a dropped request can never be
  remembered as an empty archive.
- A snapshot is fetched with the ``original`` URL exactly as captured, and with
  the ``id_`` flag so the bytes are the archived response, not the replay page.
  ``id_`` hands back the original bytes, gzip and all, so a gzipped body is
  inflated here.
"""

from __future__ import annotations

import errno
import gzip
import hashlib
import json
import logging
import os
import re
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

import requests
import zstandard

from podcast_pipeline.audio.disk import DiskSpaceError
from podcast_pipeline.config import WaybackConfig
from podcast_pipeline.http import make_session

logger = logging.getLogger(__name__)

CDX_FIELDS = ("timestamp", "original", "statuscode", "mimetype", "length", "digest")

_TIMESTAMP = re.compile(r"\d{14}")
_SERVED_TIMESTAMP = re.compile(r"/web/(\d{14})id_/")


class CdxError(RuntimeError):
    """A CDX listing could not be obtained after every attempt."""


class SnapshotError(RuntimeError):
    """One archived capture could not be fetched. Per-capture, not fatal."""


@dataclass(frozen=True)
class Capture:
    """One CDX record: an archived copy of ``original`` taken at ``timestamp``."""

    timestamp: str          # YYYYMMDDhhmmss, UTC
    original: str           # the URL exactly as it was captured
    statuscode: str
    mimetype: str
    length: int | None      # compressed WARC record size; None when CDX says '-'
    digest: str             # content hash; equal digests are byte-identical bodies

    @property
    def day(self) -> str:
        """Capture date as an ISO date, comparable with ``published_date[:10]``."""
        ts = self.timestamp
        return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"

    def replay_url(self, replay_root: str) -> str:
        return f"{replay_root.rstrip('/')}/{self.timestamp}id_/{self.original}"

    def to_row(self) -> list[str]:
        return [self.timestamp, self.original, self.statuscode, self.mimetype,
                "-" if self.length is None else str(self.length), self.digest]


@dataclass(frozen=True)
class Snapshot:
    capture: Capture
    served_url: str         # where the bytes actually came from (Wayback may redirect)
    body: bytes

    @property
    def served_timestamp(self) -> str | None:
        match = _SERVED_TIMESTAMP.search(self.served_url)
        return match.group(1) if match else None


def parse_cdx(text: str) -> list[Capture] | None:
    """Captures from an ``output=json`` CDX body, or None if the body cannot be trusted.

    ``[]`` is a real answer (nothing archived). An empty body, invalid JSON, an
    unexpected header row, or a malformed record is ambiguous -- the CDX server
    answers a dropped request that way -- and the caller must retry.
    """
    text = text.strip()
    if not text:
        return None
    try:
        rows = json.loads(text)
    except json.JSONDecodeError:
        return None
    if rows == []:
        return []
    if not isinstance(rows, list) or rows[0] != list(CDX_FIELDS):
        return None
    captures = []
    for row in rows[1:]:
        if not (isinstance(row, list) and len(row) == len(CDX_FIELDS)
                and all(isinstance(v, str) for v in row) and _TIMESTAMP.fullmatch(row[0])
                and row[1]):
            return None
        ts, original, status, mimetype, length, digest = row
        captures.append(Capture(ts, original, status, mimetype,
                                int(length) if length.isdigit() else None, digest))
    return captures


def url_identity(url: str) -> str:
    """A URL as CDX matches it: scheme, default port and a leading ``www.`` ignored.

    ``http://feeds.example.com:80/x`` and ``https://www.feeds.example.com/x``
    are one feed to CDX, and one listing answers for both.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").removeprefix("www.")
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    return f"{host}{parts.path or '/'}{'?' + parts.query if parts.query else ''}"


def archived_original(replay_url: str) -> str | None:
    """The original URL inside a ``.../web/<timestamp>[id_]/<original>`` replay URL."""
    match = re.search(r"/web/\d{14}(?:id_)?/(.+)$", replay_url)
    return match.group(1) if match else None


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def _write_atomic(path: Path, data: bytes) -> None:
    """Write via a temp file and rename, so a reader never sees half a cache entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except OSError as e:
        Path(tmp).unlink(missing_ok=True)
        if e.errno == errno.ENOSPC:
            raise DiskSpaceError(f"Disk full while writing {path}") from e
        raise


class WaybackClient:
    """CDX listings and snapshot fetches, both cached under ``cache_dir``.

    ``list_captures`` is safe to call from any thread but never runs two CDX
    requests at once. ``fetch_snapshot`` may run in parallel (a few workers).
    """

    def __init__(self, config: WaybackConfig, cache_dir: Path,
                 session: requests.Session | None = None,
                 cdx_session: requests.Session | None = None,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic):
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.session = session or make_session(pool_size=max(config.fetch_workers, 1))
        # No transport-level retries for CDX: the loop below owns retrying, and
        # it must keep requests strictly one at a time.
        self.cdx_session = cdx_session or make_session(pool_size=1, retries=0)
        self._sleep = sleep
        self._clock = clock
        self._cdx_lock = threading.Lock()
        self._last_cdx: float | None = None
        self.cdx_requests = 0

    # --- CDX -------------------------------------------------------------------

    def _cdx_cache_path(self, url: str) -> Path:
        return self.cache_dir / "cdx" / f"{_cache_key(url)}.json"

    def list_captures(self, url: str, refresh: bool = False) -> list[Capture]:
        """Every day's first successful capture of exactly ``url``, oldest first.

        CDX matches on the canonical form of the URL (scheme and ``www.``
        dropped), so http and https variants come back together; ``original``
        says which was captured. ``collapse=timestamp:8`` keeps one capture per
        day, which bounds a daily-crawled feed to a few thousand rows.

        Raises CdxError when every attempt failed.
        """
        cache_path = self._cdx_cache_path(url)
        if not refresh and cache_path.exists():
            cached = json.loads(cache_path.read_text())
            if cached.get("url") != url:
                raise RuntimeError(f"CDX cache collision: {cache_path} holds {cached.get('url')!r}, not {url!r}")
            return [Capture(r[0], r[1], r[2], r[3], int(r[4]) if r[4].isdigit() else None, r[5])
                    for r in cached["captures"]]

        params = {"url": url, "fl": ",".join(CDX_FIELDS), "filter": "statuscode:200",
                  "collapse": "timestamp:8", "output": "json"}
        problem = "no attempt made"
        with self._cdx_lock:
            for attempt in range(self.config.cdx_attempts):
                if attempt:
                    self._sleep(self.config.cdx_backoff_seconds * 2 ** (attempt - 1))
                self._wait_for_cdx_turn()
                try:
                    response = self.cdx_session.get(self.config.cdx_url, params=params,
                                                    timeout=self.config.timeout_seconds)
                except requests.RequestException as e:
                    problem = f"request failed: {e}"
                else:
                    if response.status_code == 200:
                        captures = parse_cdx(response.text)
                        if captures is not None:
                            captures.sort(key=lambda c: c.timestamp)
                            _write_atomic(cache_path, json.dumps({
                                "url": url, "listed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "captures": [c.to_row() for c in captures],
                            }).encode())
                            return captures
                        problem = f"empty or malformed body ({len(response.content)} bytes)"
                    else:
                        problem = f"HTTP {response.status_code}"
                finally:
                    self.cdx_requests += 1
                    self._last_cdx = self._clock()
                logger.warning(f"CDX attempt {attempt + 1}/{self.config.cdx_attempts} for {url}: {problem}")
        raise CdxError(f"CDX listing for {url} failed after {self.config.cdx_attempts} attempts: {problem}")

    def _wait_for_cdx_turn(self) -> None:
        if self._last_cdx is None:
            return
        remaining = self._last_cdx + self.config.cdx_delay_seconds - self._clock()
        if remaining > 0:
            self._sleep(remaining)

    # --- snapshots ---------------------------------------------------------------

    def _snapshot_cache_path(self, capture: Capture) -> Path:
        return self.cache_dir / "snapshots" / f"{capture.timestamp}_{_cache_key(capture.original)}.zst"

    def fetch_snapshot(self, capture: Capture) -> Snapshot:
        """The archived bytes of ``capture``. Raises SnapshotError on failure.

        The cache entry is the served URL, a newline, then the body,
        zstd-compressed (feeds shrink about tenfold).
        """
        cache_path = self._snapshot_cache_path(capture)
        if cache_path.exists():
            served, _, body = zstandard.decompress(cache_path.read_bytes()).partition(b"\n")
            return Snapshot(capture, served.decode(), body)

        url = capture.replay_url(self.config.replay_url)
        try:
            try:
                response = self.session.get(url, timeout=self.config.timeout_seconds)
            except requests.exceptions.ContentDecodingError:
                # A corrupt Content-Encoding body (seen live on Megaphone); ask for identity.
                response = self.session.get(url, timeout=self.config.timeout_seconds,
                                            headers={"Accept-Encoding": "identity"})
        except requests.RequestException as e:
            raise SnapshotError(f"{url}: request failed: {e}") from e
        if response.status_code != 200:
            raise SnapshotError(f"{url}: HTTP {response.status_code}")
        body = response.content
        if body[:2] == b"\x1f\x8b":
            try:
                body = gzip.decompress(body)
            except (OSError, EOFError) as e:
                raise SnapshotError(f"{url}: archived gzip body does not inflate: {e}") from e
        if not body.strip():
            raise SnapshotError(f"{url}: empty body")
        served = response.url or url
        _write_atomic(cache_path, zstandard.compress(served.encode() + b"\n" + body))
        return Snapshot(capture, served, body)
