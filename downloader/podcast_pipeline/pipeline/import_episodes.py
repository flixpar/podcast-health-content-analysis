"""import-episodes: add or repair episodes from a source that is not an RSS feed.

Some episodes a study needs are not in any feed we can read: the live feed
rolls them off, no Wayback copy lists them, or the enclosure host is dead.
A publisher's own site (an episode archive page) or an alternate audio host
often still has them. A one-off tool scrapes such a source into JSONL; this
command loads it, with provenance, in one transaction per file.

Input: one JSON object per line.

* required: ``title``, ``published_date`` (ISO 8601; a timezone is converted
  to UTC, a bare date means midnight UTC), ``audio_url``;
* optional: ``podcast_id`` (else ``--podcast-id``), ``guid``,
  ``duration_seconds``, ``description``, ``transcript_url``, ``evidence`` (a
  free-form dict: how the row was established, stored on the episode's
  ``metadata.imported``), ``replaces_episode_id``.

Each row is matched against the podcast's existing episodes: by ``guid`` (the
given one, or the one this command would generate), else by an explicit
``replaces_episode_id``, else by the same UTC day plus normalized title (the
key ``studies/materialize.py`` dedupes on).

* **Matched, and the episode is stuck** -- its download failed without
  leaving audio (``status = 'error'``, no ``audio_file_path``), or it is
  ``pending`` and the row names it with ``replaces_episode_id`` (the caller
  asserts its URL is dead) -- the episode gets the new ``audio_url`` and goes
  back to ``pending`` with the error cleared. ``episode_sources`` records the
  new URL under ``--source`` and the old one under ``previous_audio_url``, so
  nothing is lost.
* **Matched, otherwise** -- an episode with audio or a transcript, or a
  pending one nobody said was dead, is never modified. It gains a provenance
  row only.
* **Unmatched** -- inserted via ``db.insert_episode``, with the given guid or
  ``<source>:<hash of podcast, day and normalized title>``, which is stable
  across re-imports.

Rejected rows (missing fields, a date before 1995, an unknown podcast, a guid
or ``replaces_episode_id`` that belongs to another podcast, a second row for
the same episode) are listed with their reasons; the rest of the file is
still imported. ``--dry-run`` plans the same changes and writes nothing.

Run ``study refresh`` afterwards so studies see the changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from podcast_pipeline import db
from podcast_pipeline.config import Config
from podcast_pipeline.db import EpisodeStatus
from podcast_pipeline.models import FeedEpisode
from podcast_pipeline.pipeline.discover_archived import EARLIEST_PLAUSIBLE_DATE

logger = logging.getLogger(__name__)

#: ``episode_sources.source`` for the URL an episode had before an import replaced it.
PREVIOUS_AUDIO_URL_SOURCE = "previous_audio_url"

REQUIRED_FIELDS = ("title", "published_date", "audio_url")
OPTIONAL_FIELDS = ("podcast_id", "guid", "duration_seconds", "description", "transcript_url",
                   "evidence", "replaces_episode_id")


class ImportFileError(ValueError):
    """The file itself is unusable (not JSONL objects), as opposed to one bad row."""


def title_key(title: str) -> str:
    """Title with case, punctuation and spacing removed (as ``materialize`` dedupes)."""
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def utc_iso(value: str) -> str:
    """An ISO 8601 date or datetime as the catalog stores it: naive UTC, seconds."""
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0).isoformat()


def generated_guid(source: str, podcast_id: int, published_date: str, title: str) -> str:
    digest = hashlib.sha1(f"{podcast_id}|{published_date[:10]}|{title_key(title)}".encode())
    return f"{source}:{digest.hexdigest()[:16]}"


# --- planning (read-only) -----------------------------------------------------

@dataclass
class Row:
    line: int
    podcast_id: int
    guid: str
    title: str
    published_date: str
    audio_url: str
    duration_seconds: int | None
    description: str
    transcript_url: str | None
    evidence: dict
    replaces_episode_id: int | None


@dataclass
class Action:
    kind: str                    # 'insert' | 'update' | 'provenance'
    row: Row
    episode_id: int | None = None
    previous_url: str | None = None
    reason: str = ""             # why a matched episode was or was not updated


@dataclass
class Plan:
    actions: list[Action] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)

    def reject(self, line: int, reason: str, row: dict | None = None) -> None:
        title = (row or {}).get("title")
        self.rejected.append({"line": line, "reason": reason,
                              **({"title": title} if title else {})})


def _validate(line: int, raw: dict, source: str, default_podcast: int | None) -> Row | str:
    unknown = set(raw) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
    if unknown:
        return f"unknown fields: {', '.join(sorted(unknown))}"
    missing = [f for f in REQUIRED_FIELDS if not isinstance(raw.get(f), str) or not raw[f].strip()]
    if missing:
        return f"missing {', '.join(missing)}"
    podcast_id = raw.get("podcast_id", default_podcast)
    if not isinstance(podcast_id, int):
        return "no podcast_id (in the row or --podcast-id)"
    try:
        published = utc_iso(raw["published_date"])
    except ValueError:
        return f"unparseable published_date {raw['published_date']!r}"
    if published < EARLIEST_PLAUSIBLE_DATE:
        return f"implausible published_date {published}"
    audio_url = raw["audio_url"].strip()
    if not audio_url.startswith(("http://", "https://")):
        return f"audio_url is not http(s): {audio_url!r}"
    evidence = raw.get("evidence") or {}
    if not isinstance(evidence, dict):
        return "evidence must be an object"
    replaces = raw.get("replaces_episode_id")
    if replaces is not None and not isinstance(replaces, int):
        return "replaces_episode_id must be an integer"
    duration = raw.get("duration_seconds")
    if duration is not None and not isinstance(duration, (int, float)):
        return "duration_seconds must be a number"
    title = raw["title"].strip()
    return Row(
        line=line, podcast_id=podcast_id,
        guid=(raw.get("guid") or "").strip() or generated_guid(source, podcast_id, published, title),
        title=title, published_date=published, audio_url=audio_url,
        duration_seconds=round(duration) if duration is not None else None,
        description=raw.get("description") or "", transcript_url=raw.get("transcript_url") or None,
        evidence=evidence, replaces_episode_id=replaces,
    )


def read_rows(path: Path) -> list[tuple[int, dict]]:
    rows = []
    for n, text in enumerate(path.read_text().splitlines(), start=1):
        if not text.strip():
            continue
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise ImportFileError(f"{path}:{n}: not JSON ({e})") from e
        if not isinstance(obj, dict):
            raise ImportFileError(f"{path}:{n}: expected a JSON object")
        rows.append((n, obj))
    return rows


def _has_work(ep: sqlite3.Row) -> bool:
    return bool(ep["audio_file_path"] or ep["transcript_file_path"] or ep["has_rss_transcript"]
                or ep["status"] == EpisodeStatus.TRANSCRIBED)


class _Catalog:
    """The episodes of the podcasts a file touches, loaded once per podcast."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.by_podcast: dict[int, dict] = {}

    def podcast_exists(self, podcast_id: int) -> bool:
        return self.conn.execute("SELECT 1 FROM podcasts WHERE id = ?",
                                 (podcast_id,)).fetchone() is not None

    def episodes(self, podcast_id: int) -> dict:
        if podcast_id not in self.by_podcast:
            rows = self.conn.execute("""
                SELECT id, podcast_id, episode_guid, title, published_date, audio_url, status,
                       audio_file_path, transcript_file_path, has_rss_transcript
                FROM episodes WHERE podcast_id = ? ORDER BY id
            """, (podcast_id,)).fetchall()
            by_key: dict[tuple, list] = {}
            for r in rows:
                if r["published_date"]:
                    by_key.setdefault((r["published_date"][:10], title_key(r["title"] or "")),
                                      []).append(r)
            self.by_podcast[podcast_id] = {"by_id": {r["id"]: r for r in rows},
                                           "by_guid": {r["episode_guid"]: r for r in rows},
                                           "by_key": by_key}
        return self.by_podcast[podcast_id]

    def guid_owner(self, guid: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT id, podcast_id FROM episodes WHERE episode_guid = ?",
                                 (guid,)).fetchone()

    def episode(self, episode_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT id, podcast_id FROM episodes WHERE id = ?",
                                 (episode_id,)).fetchone()


def plan(conn: sqlite3.Connection, rows: list[tuple[int, dict]], source: str,
         default_podcast: int | None) -> Plan:
    out = Plan()
    catalog = _Catalog(conn)
    known_podcasts: dict[int, bool] = {}
    claimed: dict[object, int] = {}      # episode id / new guid / new key -> first line

    for line, raw in rows:
        row = _validate(line, raw, source, default_podcast)
        if isinstance(row, str):
            out.reject(line, row, raw)
            continue
        if row.podcast_id not in known_podcasts:
            known_podcasts[row.podcast_id] = catalog.podcast_exists(row.podcast_id)
        if not known_podcasts[row.podcast_id]:
            out.reject(line, f"podcast {row.podcast_id} does not exist", raw)
            continue
        eps = catalog.episodes(row.podcast_id)

        target = eps["by_guid"].get(row.guid)
        if target is None:
            owner = catalog.guid_owner(row.guid)
            if owner is not None:
                out.reject(line, f"guid belongs to episode {owner['id']} of podcast "
                                 f"{owner['podcast_id']}", raw)
                continue
        explicit = False
        if row.replaces_episode_id is not None:
            named = eps["by_id"].get(row.replaces_episode_id)
            if named is None:
                other = catalog.episode(row.replaces_episode_id)
                out.reject(line, f"replaces_episode_id {row.replaces_episode_id} "
                                 + ("does not exist" if other is None
                                    else f"belongs to podcast {other['podcast_id']}"), raw)
                continue
            if target is not None and target["id"] != named["id"]:
                out.reject(line, f"guid matches episode {target['id']} but replaces_episode_id "
                                 f"names {named['id']}", raw)
                continue
            target, explicit = named, True
        if target is None:
            same_day = eps["by_key"].get((row.published_date[:10], title_key(row.title)), [])
            if same_day:
                # Prefer the copy with work done: it needs nothing, so the row is provenance.
                target = max(same_day, key=lambda r: (_has_work(r), -r["id"]))

        claim = target["id"] if target is not None else ("new", row.podcast_id, row.guid)
        key_claim = ("key", row.podcast_id, row.published_date[:10], title_key(row.title))
        first = claimed.get(claim) or (claimed.get(key_claim) if target is None else None)
        if first is not None:
            out.reject(line, f"same episode as line {first}", raw)
            continue
        claimed[claim] = line
        if target is None:
            claimed[key_claim] = line
            out.actions.append(Action("insert", row))
            continue

        stuck_error = target["status"] == EpisodeStatus.ERROR and not target["audio_file_path"]
        stuck_pending = target["status"] == EpisodeStatus.PENDING and explicit
        if _has_work(target):
            action = Action("provenance", row, target["id"], reason="has audio or transcript")
        elif target["audio_url"] == row.audio_url:
            action = Action("provenance", row, target["id"], reason="same audio_url")
        elif stuck_error or stuck_pending:
            action = Action("update", row, target["id"], previous_url=target["audio_url"],
                            reason="download failed" if stuck_error else "named as dead")
        else:
            action = Action("provenance", row, target["id"],
                            reason=f"status {target['status']}; URL not known dead")
        out.actions.append(action)
    return out


# --- applying (writes) ----------------------------------------------------------

def _append_import_record(conn: sqlite3.Connection, episode_id: int, source: str,
                          row: Row, previous_url: str | None) -> None:
    """Keep the row's evidence on the episode (``metadata.imported``, a list)."""
    raw = conn.execute("SELECT metadata FROM episodes WHERE id = ?", (episode_id,)).fetchone()[0]
    metadata = json.loads(raw) if raw else {}
    metadata.setdefault("imported", []).append({
        "source": source, "audio_url": row.audio_url, "previous_audio_url": previous_url,
        "published_date": row.published_date, "title": row.title, "evidence": row.evidence,
        "imported_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    })
    conn.execute("UPDATE episodes SET metadata = ? WHERE id = ?", (json.dumps(metadata), episode_id))


def _add_source(conn: sqlite3.Connection, episode_id: int, source: str, ref: str) -> None:
    conn.execute("INSERT OR IGNORE INTO episode_sources (episode_id, source, ref) VALUES (?, ?, ?)",
                 (episode_id, source, ref))


def apply(conn: sqlite3.Connection, actions: list[Action], source: str) -> None:
    """Write a plan. The caller commits."""
    for a in actions:
        row = a.row
        if a.kind == "insert":
            episode = FeedEpisode(
                guid=row.guid, title=row.title, audio_url=row.audio_url,
                description=row.description, published_date=row.published_date,
                duration_seconds=row.duration_seconds, transcript_url=row.transcript_url)
            if not db.insert_episode(conn, row.podcast_id, episode):
                raise RuntimeError(f"line {row.line}: guid {row.guid} appeared during the import")
            a.episode_id = conn.execute("SELECT id FROM episodes WHERE episode_guid = ?",
                                        (row.guid,)).fetchone()[0]
        elif a.kind == "update":
            cur = conn.execute("""
                UPDATE episodes SET audio_url = ?, status = ?, error_message = NULL
                WHERE id = ? AND status IN (?, ?)
                  AND (audio_file_path IS NULL OR audio_file_path = '')
                  AND (transcript_file_path IS NULL OR transcript_file_path = '')
            """, (row.audio_url, EpisodeStatus.PENDING, a.episode_id,
                  EpisodeStatus.ERROR, EpisodeStatus.PENDING))
            if cur.rowcount != 1:
                raise RuntimeError(f"line {row.line}: episode {a.episode_id} changed during the import")
            _add_source(conn, a.episode_id, PREVIOUS_AUDIO_URL_SOURCE, a.previous_url or "")
        _add_source(conn, a.episode_id, source, row.audio_url)
        _append_import_record(conn, a.episode_id, source, row, a.previous_url)


def run(config: Config, conn: sqlite3.Connection, path: Path, source: str,
        podcast_id: int | None = None, dry_run: bool = False) -> dict:
    if not re.fullmatch(r"[a-z0-9_]+", source):
        raise ValueError(f"--source must be a short snake_case label, got {source!r}")
    if source == PREVIOUS_AUDIO_URL_SOURCE:
        raise ValueError(f"--source {PREVIOUS_AUDIO_URL_SOURCE!r} is reserved")
    rows = read_rows(path)
    result = plan(conn, rows, source, podcast_id)
    if not dry_run:
        try:
            apply(conn, result.actions, source)
        except BaseException:
            conn.rollback()
            raise
        conn.commit()

    count = {k: sum(a.kind == k for a in result.actions) for k in ("insert", "update", "provenance")}
    summary = {
        "path": str(path), "source": source, "dry_run": dry_run, "rows": len(rows),
        "inserted": count["insert"], "updated": count["update"],
        "provenance_only": count["provenance"], "rejected": len(result.rejected),
        "rejected_reasons": _tally(re.sub(r"\d+", "N", r["reason"]) for r in result.rejected),
        "rejected_rows": result.rejected[:50],
        "updated_episodes": [{"line": a.row.line, "episode_id": a.episode_id, "reason": a.reason}
                             for a in result.actions if a.kind == "update"][:200],
        "provenance_only_reasons": _tally(a.reason for a in result.actions if a.kind == "provenance"),
    }
    logger.info(f"import-episodes {path} ({source}{', dry run' if dry_run else ''}): "
                f"{count['insert']} inserted, {count['update']} updated, "
                f"{count['provenance']} provenance only, {len(result.rejected)} rejected")
    return summary


def _tally(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out
