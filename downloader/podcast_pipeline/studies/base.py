"""What a study is: a named, versioned rule that selects podcasts (and,
optionally, publication-date windows of their episodes) from the catalog.

A study only *selects*. Audio, transcripts and every other per-episode
artifact belong to the catalog and are shared, so two studies that contain the
same episode never download or transcribe it twice.

Writing a new study
-------------------
Subclass ``Study`` in a module under ``podcast_pipeline/studies/``, set
``name``, ``description`` and ``version``, implement ``select``, and add the
class to ``REGISTRY`` in ``studies/__init__.py``. ``select`` returns
``Member``s keyed by entity:

* ``podcast:<id>`` -- a podcast already in the catalog;
* ``apple:<id>``   -- an Apple podcast id (resolved by ``resolve --study``);
* ``title:<key>``  -- a chart title with no id, normalized like
  ``charts.keys.title_key`` (resolved by a paced iTunes title search).

A member with ``windows=None`` contributes every episode; otherwise only
episodes published inside one of its windows. Bump ``version`` whenever the
selection logic changes, so the stored definition hash records it.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True)
class Window:
    """Episodes published in [start, end), dates as ISO 'YYYY-MM-DD' (UTC)."""

    label: str
    start: str
    end: str
    attrs: dict = field(default_factory=dict, compare=False, hash=False)


@dataclass
class Member:
    entity: str
    name: str | None = None
    windows: list[Window] | None = None   # None: every episode of the podcast
    attrs: dict = field(default_factory=dict)

    @property
    def scope(self) -> str:
        return "all" if self.windows is None else "windows"


class Study:
    name: ClassVar[str]
    description: ClassVar[str]
    version: ClassVar[int] = 1

    #: At most this many episodes per window. Picks are spread evenly across
    #: the window and prefer episodes that already have a transcript, so a cap
    #: reuses finished work before asking for new downloads.
    max_per_window: ClassVar[int | None] = None
    #: Drop episodes that repeat another's (podcast, published_date, title)
    #: under a different GUID: publishers re-issue items, and each copy would
    #: otherwise be downloaded and counted separately.
    dedupe: ClassVar[bool] = True

    def select(self, conn: sqlite3.Connection) -> list[Member]:
        raise NotImplementedError

    def params(self) -> dict:
        """Parameters that shape the selection; part of the definition hash."""
        return {}

    def definition(self) -> dict:
        return {
            "module": type(self).__module__,
            "class": type(self).__name__,
            "version": self.version,
            "max_per_window": self.max_per_window,
            "dedupe": self.dedupe,
            "params": self.params(),
        }

    def definition_hash(self) -> str:
        blob = json.dumps(self.definition(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]
