"""How file paths are stored in the database.

Audio and transcript paths are stored *relative to the data directory*
(``audio/the-daily/episode.ogg``, ``transcripts/episode_12.jsonl.zst``), so the
database survives the repository moving, a worktree being removed, or the data
volume being mounted elsewhere. Every writer stores ``to_stored(...)`` and every
reader opens ``resolve(...)``; nothing else should join or split these paths.

Code outside the pipeline that reads the database (the analysis scripts) must
also call ``resolve(config, stored)`` so the configured data directory applies.
"""

from __future__ import annotations

from pathlib import Path

from podcast_pipeline.config import Config


class StoredPathError(ValueError):
    """A path to store is not inside the data directory."""


def to_stored(config: Config, path: Path | str) -> str:
    """The form of ``path`` to write to the database: relative to the data dir."""
    path = Path(path)
    if not path.is_absolute():
        return path.as_posix()
    for base in (config.data_path, config.data_path.resolve()):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            pass
    try:
        return path.resolve().relative_to(config.data_path.resolve()).as_posix()
    except ValueError:
        raise StoredPathError(f"{path} is outside the data directory {config.data_path}; "
                              f"refusing to store a path the database could not follow") from None


def resolve(config: Config, stored: str | Path | None) -> Path | None:
    """The file a stored path refers to. Absolute values (rows written before
    paths were relative) are returned unchanged."""
    if stored is None or str(stored) == "":
        return None
    path = Path(stored)
    return path if path.is_absolute() else config.data_path / path
