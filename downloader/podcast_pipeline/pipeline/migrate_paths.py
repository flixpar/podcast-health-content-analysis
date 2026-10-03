"""Rewrite absolute audio/transcript paths as paths relative to the data directory.

The database once stored absolute paths, and moving the repository broke all of
them at once (``/home/felix/projects/podcast-misinfo/downloader/data/...``). The
rule is now ``paths.to_stored`` / ``paths.resolve``; this command converts the
rows written before it.

For every absolute value in ``episodes.audio_file_path``,
``episodes.transcript_file_path`` and ``transcripts.file_path``:

* a known prefix is stripped: the current data directory (or its real path, or
  its path through another checkout/worktree), or anything up to
  ``/downloader/data/``;
* the result must name an existing file under the data directory, or the row
  is left untouched and reported;
* an audio row naming an ``.mp3`` that is gone is pointed at its same-stem
  ``.ogg`` only if that file is what ``convert-audio`` would have written:
  Opus, plausibly complete, and with a duration consistent with the recorded
  MP3 size. The row's compression columns are updated as ``record_conversion``
  would have, so ``convert-audio`` never picks it up again;
* every changed value is first copied to ``path_migration_backup``.

Work happens in batches, one commit each, so the write lock is never held for
long, and an update only applies if the value is still the one that was read.
Re-running is a no-op for everything already migrated.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from podcast_pipeline import paths
from podcast_pipeline.audio import MIN_AUDIO_BYTES
from podcast_pipeline.audio.ffmpeg import probe_audio_codec, probe_duration
from podcast_pipeline.config import Config

logger = logging.getLogger(__name__)

#: (table, column) pairs that hold file paths.
COLUMNS = (("episodes", "audio_file_path"),
           ("episodes", "transcript_file_path"),
           ("transcripts", "file_path"))

#: Every checkout of the repository kept its data under ``downloader/data``.
LEGACY_DATA_MARKER = "/downloader/data/"

BATCH_ROWS = 5000
EXAMPLES = 20

#: Implied MP3 bitrate (recorded MP3 size over the .ogg's duration) a genuine
#: conversion falls inside. A wrong file gives an implausible rate.
MP3_KBPS_RANGE = (24.0, 330.0)

BACKUP_SCHEMA = """
CREATE TABLE IF NOT EXISTS path_migration_backup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    row_id INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_path_migration_backup_row
    ON path_migration_backup(table_name, row_id);
"""


@dataclass
class Change:
    row_id: int
    old: str
    new: str
    #: extra columns of the same row to set (mp3 -> ogg rows only)
    extra: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)


@dataclass
class ColumnReport:
    absolute_before: int = 0
    relative_before: int = 0
    migrated: int = 0
    mp3_to_ogg: int = 0
    missing: int = 0
    unmapped: int = 0
    conflicts: int = 0
    by_prefix: Counter = field(default_factory=Counter)
    examples: dict = field(default_factory=lambda: {"missing": [], "unmapped": [], "mp3_to_ogg": [],
                                                    "conflicts": []})

    def example(self, kind: str, item: dict) -> None:
        if len(self.examples[kind]) < EXAMPLES:
            self.examples[kind].append(item)

    def to_dict(self) -> dict:
        return {"absolute_before": self.absolute_before, "relative_before": self.relative_before,
                "migrated": self.migrated, "mp3_to_ogg": self.mp3_to_ogg,
                "missing": self.missing, "unmapped": self.unmapped, "conflicts": self.conflicts,
                "by_prefix": dict(self.by_prefix.most_common()),
                "examples": {k: v for k, v in self.examples.items() if v}}


def relative_form(config: Config, value: str) -> str | None:
    """``value`` relative to the data directory, or None if no known prefix fits."""
    try:
        relative = paths.to_stored(config, value)
    except paths.StoredPathError:
        _, marker, relative = value.partition(LEGACY_DATA_MARKER)
        if not marker:
            return None
    parts = PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or ".." in parts:
        return None
    return relative


def _prefix(value: str, relative: str | None) -> str:
    return value[:len(value) - len(relative)] if relative and value.endswith(relative) else "(unmapped)"


def converted_sibling(config: Config, relative: str, original_mb: float | None) -> tuple[str | None, dict]:
    """The ``.ogg`` that ``convert-audio`` made from the missing ``relative`` MP3, if
    the file on disk is plausibly that conversion. Returns (relative .ogg, evidence)."""
    source = PurePosixPath(relative)
    if source.suffix.lower() != ".mp3":
        return None, {}
    candidate = str(source.with_suffix(".ogg"))
    path = config.data_path / candidate
    if not path.is_file():
        return None, {"reason": "no .ogg sibling"}
    size = path.stat().st_size
    evidence = {"ogg": candidate, "ogg_bytes": size}
    if size < MIN_AUDIO_BYTES:
        return None, {**evidence, "reason": "ogg too small"}
    codec = probe_audio_codec(path)
    duration = probe_duration(path)
    evidence.update(codec=codec, ogg_seconds=round(duration, 1) if duration else duration)
    if codec != "opus" or not duration:
        return None, {**evidence, "reason": "not an Opus file convert-audio would have written"}
    if original_mb:
        kbps = original_mb * 1024 ** 2 * 8 / duration / 1000
        evidence["implied_mp3_kbps"] = round(kbps, 1)
        if not MP3_KBPS_RANGE[0] <= kbps <= MP3_KBPS_RANGE[1]:
            return None, {**evidence, "reason": "duration inconsistent with the recorded MP3 size"}
    return candidate, evidence


def _plan(config: Config, table: str, column: str, rows: list[sqlite3.Row],
          report: ColumnReport) -> list[Change]:
    changes = []
    for row in rows:
        value = row["value"]
        relative = relative_form(config, value)
        report.by_prefix[_prefix(value, relative)] += 1
        if relative is None:
            report.unmapped += 1
            report.example("unmapped", {"row_id": row["row_id"], "value": value})
            continue
        if (config.data_path / relative).is_file():
            changes.append(Change(row["row_id"], value, relative))
            continue
        if column == "audio_file_path":
            ogg, evidence = converted_sibling(config, relative, row["original_file_size_mb"])
            if ogg is not None:
                compressed_mb = evidence["ogg_bytes"] / 1024 ** 2
                original_mb = row["original_file_size_mb"] or compressed_mb
                changes.append(Change(row["row_id"], value, ogg, evidence=evidence, extra={
                    "is_compressed": 1, "compressed_file_size_mb": compressed_mb,
                    "compression_ratio": original_mb / compressed_mb,
                }))
                continue
        else:
            evidence = {}
        report.missing += 1
        report.example("missing", {"row_id": row["row_id"], "value": value,
                                   "looked_for": relative, **evidence})
    return changes


def _apply(conn: sqlite3.Connection, table: str, column: str, changes: list[Change],
           report: ColumnReport) -> None:
    for change in changes:
        cur = conn.execute(f"UPDATE {table} SET {column} = ? WHERE rowid = ? AND {column} = ?",
                           (change.new, change.row_id, change.old))
        if cur.rowcount != 1:
            report.conflicts += 1
            report.example("conflicts", {"row_id": change.row_id, "value": change.old})
            continue
        backups = [(column, change.old, change.new)]
        if change.extra:
            names = list(change.extra)
            current = conn.execute(f"SELECT {', '.join(names)} FROM {table} WHERE rowid = ?",
                                   (change.row_id,)).fetchone()
            conn.execute(f"UPDATE {table} SET {', '.join(f'{n} = ?' for n in names)} WHERE rowid = ?",
                         [change.extra[n] for n in names] + [change.row_id])
            backups += [(n, current[n], change.extra[n]) for n in names]
        conn.executemany("""
            INSERT INTO path_migration_backup (table_name, row_id, column_name, old_value, new_value)
            VALUES (?, ?, ?, ?, ?)
        """, [(table, change.row_id, name, old, new) for name, old, new in backups])
        _count(change, report)


def _count(change: Change, report: ColumnReport) -> None:
    report.migrated += 1
    if change.extra:
        report.mp3_to_ogg += 1
        report.example("mp3_to_ogg", {"row_id": change.row_id, "old": change.old,
                                      "new": change.new, **change.evidence})


def _counts(conn: sqlite3.Connection, table: str, column: str) -> tuple[int, int]:
    row = conn.execute(f"""
        SELECT SUM({column} LIKE '/%'), SUM({column} NOT LIKE '/%')
        FROM {table} WHERE {column} IS NOT NULL AND {column} != ''
    """).fetchone()
    return row[0] or 0, row[1] or 0


def migrate_column(config: Config, conn: sqlite3.Connection, table: str, column: str,
                   dry_run: bool) -> ColumnReport:
    report = ColumnReport()
    report.absolute_before, report.relative_before = _counts(conn, table, column)
    extra = ", original_file_size_mb" if column == "audio_file_path" else ""
    last = 0
    while True:
        rows = conn.execute(f"""
            SELECT rowid AS row_id, {column} AS value{extra} FROM {table}
            WHERE rowid > ? AND {column} LIKE '/%' ORDER BY rowid LIMIT ?
        """, (last, BATCH_ROWS)).fetchall()
        if not rows:
            break
        last = rows[-1]["row_id"]
        changes = _plan(config, table, column, rows, report)
        if dry_run:
            for change in changes:
                _count(change, report)
            continue
        _apply(conn, table, column, changes, report)
        conn.commit()
        logger.info(f"{table}.{column}: through rowid {last}, {report.migrated} migrated")
    return report


def run(config: Config, conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    if not dry_run:
        conn.executescript(BACKUP_SCHEMA)
        conn.commit()
    result: dict = {"dry_run": dry_run, "data_path": str(config.data_path)}
    for table, column in COLUMNS:
        report = migrate_column(config, conn, table, column, dry_run)
        summary = report.to_dict()
        if not dry_run:
            summary["absolute_after"], summary["relative_after"] = _counts(conn, table, column)
        result[f"{table}.{column}"] = summary
        logger.info(f"{table}.{column}: " + ", ".join(
            f"{k}={v}" for k, v in summary.items() if isinstance(v, int)))
    return result
