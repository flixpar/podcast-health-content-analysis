"""Download one episode's audio, resuming partial files, optionally re-encoding."""

from __future__ import annotations

import errno
import logging
from dataclasses import dataclass
from pathlib import Path

import requests

from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.audio.disk import DiskSpaceError, ensure_free_space
from podcast_pipeline.audio.ffmpeg import EncodeError, encode_opus
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


class DownloadError(RuntimeError):
    """The episode could not be fetched. Message is suitable for the DB."""


@dataclass
class DownloadResult:
    path: Path
    original_size_mb: float
    compressed_size_mb: float
    is_compressed: bool
    reused: bool = False   # an existing file was found; nothing was fetched


class AudioDownloader:
    def __init__(self, audio_dir: Path, compression: CompressionConfig,
                 timeout: int = 600, min_free_gb: float = 100.0, pool_size: int = 8,
                 session: requests.Session | None = None):
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.compression = compression
        self.timeout = timeout
        self.min_free_gb = min_free_gb
        self.session = session or make_session(pool_size=pool_size)

    def download_episode(self, audio_url: str, podcast_title: str, episode_title: str,
                         guid: str | None) -> DownloadResult:
        """Fetch an episode, or return the file already on disk for it.

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
        self._fetch(audio_url, mp3_path)
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
                return DownloadResult(ogg_path, original_mb, compressed_mb, is_compressed=True)

        return DownloadResult(mp3_path, original_mb, original_mb, is_compressed=False)

    def _fetch(self, url: str, final_path: Path, chunk_size: int = 64 * 1024) -> None:
        """Stream ``url`` to ``final_path`` via a sidecar .part file, resuming if one exists."""
        partial_path = final_path.with_suffix(final_path.suffix + PARTIAL_SUFFIX)
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
            raise DownloadError(f"request failed: {e}") from e
        except OSError as e:
            if e.errno == errno.ENOSPC:
                raise DiskSpaceError(f"Disk full while writing {final_path}") from e
            raise

        size = partial_path.stat().st_size
        if size < MIN_AUDIO_BYTES:
            partial_path.unlink()
            raise DownloadError(f"implausibly small response: {size} bytes")
        if total_size and size < total_size * COMPLETE_FRACTION:
            # Leave the partial file for the next attempt to resume.
            raise DownloadError(f"incomplete: {size}/{total_size} bytes")

        partial_path.replace(final_path)
