"""Where an episode's audio lives on disk.

Files are ``{audio_dir}/{normalized podcast title}/{normalized episode title}_{md5(guid)[:8]}.{ext}``.
Most of the archive predates the GUID hash and is named by title alone, so
lookups check both schemes (and both formats) before concluding an episode
still needs downloading.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

from podcast_pipeline.audio import AUDIO_EXTENSIONS, MIN_AUDIO_BYTES


def normalize_id(value: str | None, max_length: int = 100) -> str:
    """Lowercase ASCII slug: accents stripped, non-alphanumerics collapsed to '-'."""
    if not value:
        return "unknown"
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if max_length > 0 and len(value) > max_length:
        value = value[:max_length].rstrip("-")
    return value or "unknown"


def episode_stem(episode_title: str, guid: str | None) -> str:
    """Filename stem for new downloads. The GUID hash keeps identically titled
    episodes from overwriting each other."""
    stem = normalize_id(episode_title)
    if guid:
        return f"{stem}_{hashlib.md5(guid.encode()).hexdigest()[:8]}"
    return stem


def podcast_dir(audio_dir: Path, podcast_title: str) -> Path:
    return audio_dir / normalize_id(podcast_title)


def find_existing_audio(audio_dir: Path, podcast_title: str, episode_title: str,
                        guid: str | None) -> Path | None:
    """An already-downloaded, plausibly complete file for this episode, if any."""
    directory = podcast_dir(audio_dir, podcast_title)
    stems = dict.fromkeys([episode_stem(episode_title, guid), normalize_id(episode_title)])
    for stem in stems:
        for ext in AUDIO_EXTENSIONS:
            candidate = directory / f"{stem}{ext}"
            if candidate.exists() and candidate.stat().st_size >= MIN_AUDIO_BYTES:
                return candidate
    return None
