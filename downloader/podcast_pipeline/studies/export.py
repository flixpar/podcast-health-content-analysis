"""Write a study's episode manifest, pinned to its current revision.

Analyses should read the manifest rather than re-query the live tables, so a
result can always be traced to the exact membership it was computed on.

The database stores file paths relative to the data directory; the manifest's
``transcript_path``/``audio_path`` are those resolved to absolute real paths
(through the ``data`` symlink), so a reader can open them directly.
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from pathlib import Path

from podcast_pipeline import paths
from podcast_pipeline.config import Config
from podcast_pipeline.studies.quality import rerun_flags
from podcast_pipeline.studies.scope import require_refreshed
from podcast_pipeline.studies.status import EPISODE_STATE_SQL

COLUMNS = ["study", "revision", "episode_id", "episode_guid", "podcast_id", "podcast_title",
           "entity", "window_label", "published_date", "episode_title", "duration_seconds",
           "state", "transcript_source", "transcript_path", "audio_path", "added_revision",
           "window_provisional", "rerun"]


def export(config: Config, conn: sqlite3.Connection, name: str, output: Path | None = None,
           link_transcripts: Path | None = None) -> dict:
    require_refreshed(conn, name)
    study = conn.execute("SELECT * FROM studies WHERE name = ?", (name,)).fetchone()
    revision = study["revision"]
    output = output or config.study_export_dir / name / f"rev{revision}" / "episodes.csv"
    output.parent.mkdir(parents=True, exist_ok=True)

    rows = conn.execute(f"""
        SELECT se.study, ? AS revision, e.id AS episode_id, e.episode_guid, e.podcast_id,
               p.title AS podcast_title, se.entity, se.window_label, e.published_date,
               e.title AS episode_title, e.duration_seconds, {EPISODE_STATE_SQL} AS state,
               json_extract(t.metadata, '$.source') AS transcript_source,
               t.file_path AS transcript_path, e.audio_file_path AS audio_path, se.added_revision,
               COALESCE(json_extract(w.attrs, '$.provisional'), 0) AS window_provisional
        FROM study_episodes se JOIN episodes e ON e.id = se.episode_id
        JOIN podcasts p ON p.id = e.podcast_id
        LEFT JOIN transcripts t ON t.episode_id = e.id
        LEFT JOIN study_windows w
               ON w.study = se.study AND w.entity = se.entity AND w.label = se.window_label
        WHERE se.study = ? ORDER BY e.podcast_id, e.published_date
    """, (revision, name)).fetchall()
    # Reruns stay in scope (they did air that month) but are marked, with the
    # evidence, so an analysis can choose "what aired" or "new content".
    reruns = rerun_flags(conn, name)
    rows = [{**_with_real_paths(config, r), "rerun": reruns.get(r["episode_id"], "")} for r in rows]
    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows([[r[c] for c in COLUMNS] for r in rows])

    members = conn.execute("""
        SELECT entity, podcast_id, name, scope, attrs FROM study_members WHERE study = ? ORDER BY entity
    """, (name,)).fetchall()
    windows = conn.execute("""
        SELECT entity, label, start_date, end_date, attrs FROM study_windows WHERE study = ?
        ORDER BY entity, label
    """, (name,)).fetchall()
    (output.parent / "study.json").write_text(json.dumps({
        "name": name, "revision": revision, "description": study["description"],
        "definition": json.loads(study["definition"]), "definition_hash": study["definition_hash"],
        "refreshed_at": study["refreshed_at"], "summary": json.loads(study["summary"] or "{}"),
        "members": [{**dict(m), "attrs": json.loads(m["attrs"] or "{}")} for m in members],
        "windows": [{**dict(w), "attrs": json.loads(w["attrs"] or "{}")} for w in windows],
    }, indent=1))

    result = {"study": name, "revision": revision, "manifest": str(output),
              "episodes": len(rows), "with_transcript": sum(1 for r in rows if r["transcript_path"]),
              "reruns_flagged": sum(1 for r in rows if r["rerun"]),
              "in_provisional_windows": sum(1 for r in rows if r["window_provisional"])}
    if link_transcripts:
        result["linked"] = _link(rows, link_transcripts)
        result["linked_dir"] = str(link_transcripts)
    return result


def _with_real_paths(config: Config, row: sqlite3.Row) -> dict:
    out = dict(row)
    for column in ("transcript_path", "audio_path"):
        path = paths.resolve(config, row[column])
        out[column] = str(path.resolve()) if path is not None else None
    return out


def _link(rows, directory: Path) -> int:
    """Symlink each transcript under its own file name (``episode_<id>.jsonl.zst``),
    the layout ``analysis/topic_labeling.py --transcripts`` reads. Links that
    are no longer in the study are removed; nothing else is touched."""
    directory.mkdir(parents=True, exist_ok=True)
    wanted = {}
    for r in rows:
        if r["transcript_path"]:
            source = Path(r["transcript_path"])   # already absolute and real
            wanted[source.name] = source
    for existing in directory.iterdir():
        if existing.is_symlink() and existing.name not in wanted:
            existing.unlink()
    for file_name, source in wanted.items():
        link = directory / file_name
        if link.is_symlink() and os.readlink(link) == str(source):
            continue
        if link.exists() or link.is_symlink():
            if not link.is_symlink():
                raise FileExistsError(f"{link} exists and is not a symlink; refusing to replace it")
            link.unlink()
        link.symlink_to(source)
    return len(wanted)
