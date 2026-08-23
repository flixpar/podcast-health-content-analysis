"""Free-space guard for the audio volume."""

from __future__ import annotations

import shutil
from pathlib import Path


class DiskSpaceError(RuntimeError):
    """Free space on the audio volume fell below the configured floor.

    This is fatal on purpose. A previous run filled the disk and then wrote
    thousands of zero-byte files while every write failed; halting loudly is
    far cheaper to recover from. Never catch this and continue.
    """


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024 ** 3)


def ensure_free_space(path: Path, min_free_gb: float) -> None:
    free = free_gb(path)
    if free < min_free_gb:
        raise DiskSpaceError(f"Only {free:.1f}GB free on {path} (floor is {min_free_gb}GB). "
                             f"Stopping before the disk fills.")
