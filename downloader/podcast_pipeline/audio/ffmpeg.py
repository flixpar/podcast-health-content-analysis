"""Everything that shells out to ffmpeg/ffprobe lives here."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import numpy as np

from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.audio.disk import DiskSpaceError

logger = logging.getLogger(__name__)

# A re-encode must retain at least this fraction of the source duration
# before the source may be deleted.
DURATION_TOLERANCE = 0.98


class EncodeError(RuntimeError):
    """ffmpeg failed, or produced a file that does not hold the whole episode."""


def probe_duration(path: Path) -> float | None:
    """Decoded duration in seconds, or None if ffprobe cannot read the file."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, errors="replace", timeout=120,
    )
    if out.returncode != 0:
        return None
    value = out.stdout.strip()
    try:
        return float(value)
    except ValueError:
        return None


def probe_stream_types(path: Path) -> tuple[str, ...] | None:
    """Return container stream types in index order, or None on probe failure."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, errors="replace", timeout=120,
    )
    if out.returncode != 0:
        return None
    return tuple(line.strip() for line in out.stdout.splitlines() if line.strip())


def check_conversion(source: Path, encoded: Path) -> str | None:
    """Return None if ``encoded`` is a complete re-encode of ``source``, else the reason.

    An interrupted run once converted files while their source was still
    downloading, leaving .ogg files holding 2% of the episode. Nothing may
    delete a source on the strength of an encode that has not been decoded and
    compared against it.
    """
    if not encoded.exists():
        return "output file not created"
    if encoded.stat().st_size < MIN_AUDIO_BYTES:
        return f"output implausibly small ({encoded.stat().st_size} bytes)"
    stream_types = probe_stream_types(encoded)
    if stream_types is None:
        return "output stream layout is not readable"
    if stream_types != ("audio",):
        layout = ", ".join(stream_types) if stream_types else "no streams"
        return f"output must contain exactly one audio stream (found: {layout})"
    encoded_duration = probe_duration(encoded)
    if encoded_duration is None:
        return "output is not decodable"
    source_duration = probe_duration(source)
    if source_duration and encoded_duration < source_duration * DURATION_TOLERANCE:
        return f"output is short: {encoded_duration:.0f}s vs source {source_duration:.0f}s"
    return None


def encode_opus(source: Path, target: Path, bitrate: str = "24k", timeout: int = 600) -> None:
    """Re-encode ``source`` to mono Opus in an OGG container at ``target``.

    Raises EncodeError (with the target removed) unless the result verifiably
    holds the whole source, and DiskSpaceError if the volume filled mid-encode.
    """
    cmd = ["ffmpeg", "-v", "error", "-i", str(source),
           "-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "-1",
           "-c:a", "libopus", "-b:a", bitrate, "-vbr", "on", "-ac", "1",
           "-y", str(target)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        target.unlink(missing_ok=True)
        raise EncodeError(f"ffmpeg timed out after {timeout}s on {source}")

    if proc.returncode != 0:
        # ffmpeg creates the output before encoding anything, so a failed run
        # leaves an empty file that later passes would mistake for a success.
        target.unlink(missing_ok=True)
        if "No space left on device" in proc.stderr:
            raise DiskSpaceError(f"Disk full while re-encoding {source}")
        raise EncodeError(f"ffmpeg failed ({proc.returncode}): {proc.stderr.strip()[-500:]}")

    reason = check_conversion(source, target)
    if reason:
        target.unlink(missing_ok=True)
        raise EncodeError(f"{reason} ({target.name})")


def decode_pcm(path: Path, sample_rate: int = 16000, timeout: int = 1800) -> np.ndarray:
    """Decode a whole file to mono float32 samples at ``sample_rate``.

    Decoding from sample zero (never seeking) is what makes slices of two
    encodings of the same audio comparable: ffmpeg's seek is frame-approximate
    on MP3 and sample-accurate on Opus.
    """
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-f", "f32le", "-ar", str(sample_rate), "-ac", "1", "-"],
        capture_output=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise EncodeError(f"ffmpeg failed to decode {path}: {proc.stderr.decode(errors='replace')[-300:]}")
    return np.frombuffer(proc.stdout, dtype=np.float32)
