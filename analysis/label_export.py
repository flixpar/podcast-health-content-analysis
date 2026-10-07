"""Package a merged labeling run as a shareable, analysis-ready release.

    .venv/bin/python -m analysis.label_export --run-dir local/topic-labeling-glm53 \\
        --out local/releases/my-release [--metadata-db downloader/data/podcast_metadata.db] \\
        [--study apple-top24-monthly] [--readme my-README.md]

Reads the run directory written by ``topic_labeling.py prepare/label/merge`` and
writes Parquet tables (zstd) for the labels, the transcripts (as the
sentence-like units every label span refers to) and, with a catalog database,
episode and podcast metadata; with ``--study``, also the study's selection
(every study episode, chart evidence per show-month, coverage statistics).
The taxonomy sources, a README (generated unless ``--readme`` is given) and
MANIFEST.json (provenance plus the sha256 of every file) complete it.

Node-local transcript paths and per-row provenance constants are dropped; the
constants are recorded once in the manifest. Label field names are kept as the
pipeline writes them.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from analysis import topic_labeling as labeling

REPO = Path(__file__).resolve().parents[1]
# Identical on every row of a run; recorded once in MANIFEST.json instead.
PROVENANCE_KEYS = {
    "schema_version",
    "labeling_model",
    "labeling_run_fingerprint",
    "taxonomy_sha256",
    "source_transcript",
}
LABEL_TABLES = (
    ("annotations", "label_annotations.jsonl", "label_annotations_sha256"),
    ("clips", "clips.jsonl", "clips_sha256"),
    ("claims", "verification_candidates.jsonl", "verification_candidates_sha256"),
    ("products", "product_mentions.jsonl", "product_mentions_sha256"),
)
# Dicts keyed by label become lists of structs, so every row has the same schema.
VARIABLE_KEY_FIELDS = {
    "claim_certainty_counts": "count",
    "label_annotation_counts": "count",
    "label_max_confidence": "max_confidence",
}


class ExportError(RuntimeError):
    pass


def write_table(rows: list[dict[str, Any]], path: Path, schema: pa.Schema | None = None) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if schema is None:
        # from_pylist takes its columns from the first row; fields that only
        # some rows carry (parent_topic_id exists only on topic annotations)
        # would otherwise vanish when another row comes first.
        keys = list(dict.fromkeys(key for row in rows for key in row))
        rows = [{key: row.get(key) for key in keys} for row in rows]
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path, compression="zstd")
    return table.num_rows


def tidy(row: dict[str, Any]) -> dict[str, Any]:
    row = {key: value for key, value in row.items() if key not in PROVENANCE_KEYS}
    for key, value_name in VARIABLE_KEY_FIELDS.items():
        if isinstance(row.get(key), dict):
            row[key] = [{"label_id": k, value_name: v} for k, v in sorted(row[key].items())]
    return row


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def export_labels(run: Path, out: Path, merge_summary: dict[str, Any], counts: dict, stats: dict) -> None:
    for name, source, digest_key in LABEL_TABLES:
        if labeling.sha256_file(run / source) != merge_summary[digest_key]:
            raise ExportError(f"{source} does not match merge_summary.{digest_key}; rerun merge")
        rows = [tidy(row) for row in labeling.iter_jsonl(run / source)]
        counts[name] = write_table(rows, out / "labels" / f"{name}.parquet")
        if name == "claims":
            ads = sum("advertisement" in (row.get("relevance") or []) for row in rows)
            stats["claims_advertising"] = {"rows": ads, "share": round(ads / max(len(rows), 1), 4)}
        if name == "products":
            ads = sum(row.get("mention_role") == "advertised" for row in rows)
            stats["products_advertised"] = {"rows": ads, "share": round(ads / max(len(rows), 1), 4)}
    summary = [tidy(row) for row in labeling.iter_jsonl(run / "episodes.jsonl")]
    counts["episode_label_summary"] = write_table(summary, out / "labels" / "episode_label_summary.parquet")
    with (run / "review_queue.csv").open("rb") as src, gzip.open(
        out / "labels" / "clips_review.csv.gz", "wb"
    ) as dst:
        shutil.copyfileobj(src, dst)


def export_window_outputs(run: Path, out: Path, counts: dict) -> None:
    store = sqlite3.connect(f"file:{run / 'labels.sqlite'}?mode=ro", uri=True)
    try:
        columns = {row[1] for row in store.execute("PRAGMA table_info(window_labels)")}
        extra = [c for c in ("validation_json", "attempts", "rejected_completion_tokens") if c in columns]
        schema = pa.schema(
            [("window_id", pa.string()), ("episode_id", pa.int64()), ("window_index", pa.int64()),
             ("result_json", pa.string()), ("prompt_tokens", pa.int64()),
             ("cached_prompt_tokens", pa.int64()), ("completion_tokens", pa.int64()),
             ("reasoning_tokens", pa.int64()), ("labeled_at", pa.string()),
             ("validation_json", pa.string()), ("attempts", pa.int64()),
             ("rejected_completion_tokens", pa.int64())]
        )
        select = ", ".join(["window_id", "episode_id", "window_index", "result_json", "usage_json",
                            "labeled_at", *extra])
        writer = pq.ParquetWriter(out / "labels" / "window_outputs.parquet", schema, compression="zstd")
        batch: list[dict[str, Any]] = []
        total = 0
        for row in store.execute(f"SELECT {select} FROM window_labels ORDER BY episode_id, window_index"):
            record = dict(zip(["window_id", "episode_id", "window_index", "result_json", "usage_json",
                               "labeled_at", *extra], row))
            usage = json.loads(record.pop("usage_json") or "null") or {}
            record.update(
                prompt_tokens=usage.get("prompt_tokens"),
                cached_prompt_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            )
            batch.append(record)
            if len(batch) >= 50_000:
                writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                total += len(batch)
                batch = []
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
            total += len(batch)
        writer.close()
    finally:
        store.close()
    counts["window_outputs"] = total


def export_transcripts(
    run: Path, out: Path, prepare_manifest: dict[str, Any], counts: dict, stats: dict
) -> dict[int, dict[str, Any]]:
    """Units (deduplicated across window overlaps) and the window index."""
    unit_schema = pa.schema(
        [("episode_id", pa.int64()), ("unit_index", pa.int64()), ("unit_id", pa.string()),
         ("start_seconds", pa.float64()), ("end_seconds", pa.float64()),
         ("timing_quality", pa.string()), ("source_segment_index", pa.int64()), ("text", pa.string())]
    )
    window_schema = pa.schema(
        [("window_id", pa.string()), ("episode_id", pa.int64()), ("window_index", pa.int64()),
         ("start_unit_id", pa.string()), ("end_unit_id", pa.string()),
         ("start_seconds", pa.float64()), ("end_seconds", pa.float64()),
         ("timing_quality", pa.string()), ("word_count", pa.int64())]
    )
    (out / "transcripts").mkdir(parents=True, exist_ok=True)
    writer = pq.ParquetWriter(out / "transcripts" / "units.parquet", unit_schema, compression="zstd")
    episodes: dict[int, dict[str, Any]] = {}
    window_rows: list[dict[str, Any]] = []
    batch: list[dict[str, Any]] = []
    current: int | None = None
    seen: set[str] = set()
    previous_start: float | None = None
    total_units = regressions = 0
    regression_episodes: set[int] = set()
    for window in labeling.iter_jsonl(run / "windows.jsonl.zst"):
        episode_id = window["episode_id"]
        if episode_id != current:
            if episode_id in episodes:
                raise ExportError(f"episode {episode_id}'s windows are not contiguous")
            current, seen, previous_start = episode_id, set(), None
            episodes[episode_id] = {
                "source_transcript_sha256": window.get("source_transcript_sha256"),
                "transcript_source": window.get("transcript_source"),
                "transcript_model": window.get("transcript_model"),
                "n_windows": 0, "n_units": 0, "n_words": 0, "untimed_units": 0,
            }
        episode = episodes[episode_id]
        episode["n_windows"] += 1
        units = window["units"]
        window_rows.append(
            {"window_id": window["window_id"], "episode_id": episode_id,
             "window_index": window["window_index"], "start_unit_id": units[0]["unit_id"],
             "end_unit_id": units[-1]["unit_id"], "start_seconds": window.get("start_seconds"),
             "end_seconds": window.get("end_seconds"), "timing_quality": window.get("timing_quality"),
             "word_count": window.get("word_count")}
        )
        for unit in units:
            if unit["unit_id"] in seen:
                continue
            seen.add(unit["unit_id"])
            episode["n_units"] += 1
            episode["n_words"] += len(unit["text"].split())
            episode["untimed_units"] += unit.get("timing_quality") == "unavailable"
            start = unit.get("start_seconds")
            if start is not None:
                if previous_start is not None and start < previous_start:
                    regressions += 1
                    regression_episodes.add(episode_id)
                previous_start = start
            batch.append(
                {"episode_id": episode_id, "unit_index": int(unit["unit_id"][1:]),
                 "unit_id": unit["unit_id"], "start_seconds": start,
                 "end_seconds": unit.get("end_seconds"), "timing_quality": unit.get("timing_quality"),
                 "source_segment_index": unit.get("source_segment_index"), "text": unit["text"]}
            )
        if len(batch) >= 500_000:
            writer.write_table(pa.Table.from_pylist(batch, schema=unit_schema))
            total_units += len(batch)
            batch = []
    if batch:
        writer.write_table(pa.Table.from_pylist(batch, schema=unit_schema))
        total_units += len(batch)
    writer.close()
    counts["units"] = total_units
    counts["windows"] = write_table(window_rows, out / "transcripts" / "windows.parquet", window_schema)
    expected = (prepare_manifest.get("units"), prepare_manifest.get("windows"))
    if expected != (None, None) and expected != (counts["units"], counts["windows"]):
        raise ExportError(
            f"{counts['units']} units / {counts['windows']} windows disagree with prepare_manifest "
            f"({expected[0]} / {expected[1]})"
        )
    stats["unit_start_time_regressions"] = {"units": regressions, "episodes": len(regression_episodes)}
    return episodes


def episode_text_fields(info: dict[str, Any] | None) -> dict[str, Any]:
    if info is None:
        return {"labeled": False, "transcript_source": None, "transcript_model": None,
                "source_transcript_sha256": None, "n_windows": None, "n_units": None,
                "n_words": None, "timed_unit_share": None}
    return {"labeled": True, "transcript_source": info["transcript_source"],
            "transcript_model": info["transcript_model"],
            "source_transcript_sha256": info["source_transcript_sha256"],
            "n_windows": info["n_windows"], "n_units": info["n_units"], "n_words": info["n_words"],
            "timed_unit_share": 1 - info["untimed_units"] / info["n_units"] if info["n_units"] else None}


def export_metadata(
    db_path: Path, study: str | None, out: Path, labeled: dict[int, dict[str, Any]],
    counts: dict, stats: dict,
) -> dict[str, Any] | None:
    db = sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        study_info = None
        selection: dict[int, sqlite3.Row] = {}
        windows: dict[tuple[str, str], dict[str, Any]] = {}
        members: dict[str, sqlite3.Row] = {}
        if study:
            row = db.execute("SELECT * FROM studies WHERE name = ?", (study,)).fetchone()
            if row is None:
                raise ExportError(f"study {study!r} is not in {db_path}")
            study_info = {"name": study, "revision": row["revision"],
                          "definition_hash": row["definition_hash"], "refreshed_at": row["refreshed_at"],
                          "definition": json.loads(row["definition"])}
            members = {r["entity"]: r for r in db.execute(
                "SELECT * FROM study_members WHERE study = ?", (study,))}
            for r in db.execute("SELECT * FROM study_windows WHERE study = ?", (study,)):
                attrs = json.loads(r["attrs"] or "{}")
                member = members.get(r["entity"])
                windows[(r["entity"], r["label"])] = {
                    "entity": r["entity"],
                    "podcast_id": int(member["podcast_id"]) if member and member["podcast_id"] is not None else None,
                    "month": r["label"], "start_date": r["start_date"], "end_date": r["end_date"],
                    "monthly_rank": attrs.get("monthly_rank"), "points": attrs.get("points"),
                    "mean_points": attrs.get("mean_points"), "best_rank": attrs.get("best_rank"),
                    "snapshots_in_month": attrs.get("snapshots_in_month"),
                    "in_month_coverage": attrs.get("in_month_coverage"),
                    "provisional": attrs.get("provisional"), "chart_sources": attrs.get("sources")}
            counts["study_windows"] = write_table(list(windows.values()), out / "metadata" / "study_windows.parquet")
            selection = {int(r["episode_id"]): r for r in db.execute(
                "SELECT * FROM study_episodes WHERE study = ?", (study,))}
            unlisted = set(labeled) - set(selection)
            if unlisted:
                raise ExportError(f"{len(unlisted)} labeled episodes are not in study {study!r}")
        episode_ids = sorted(set(labeled) | set(selection))
        episodes = []
        for start in range(0, len(episode_ids), 900):
            chunk = episode_ids[start:start + 900]
            for r in db.execute(
                "SELECT id, podcast_id, title, description, published_date, duration_seconds, audio_url, "
                f"has_rss_transcript, status FROM episodes WHERE id IN ({','.join('?' * len(chunk))})", chunk
            ):
                episode_id = int(r["id"])
                row = {"episode_id": episode_id,
                       "podcast_id": int(r["podcast_id"]) if r["podcast_id"] is not None else None,
                       "title": r["title"], "description": r["description"],
                       "published_date": r["published_date"], "duration_seconds": r["duration_seconds"],
                       "audio_url": r["audio_url"], "has_rss_transcript": bool(r["has_rss_transcript"]),
                       "catalog_status": r["status"]}
                if study:
                    chosen = selection.get(episode_id)
                    window = windows.get((chosen["entity"], chosen["window_label"]), {}) if chosen else {}
                    row.update(study_entity=chosen["entity"] if chosen else None,
                               study_month=chosen["window_label"] if chosen else None,
                               study_priority=chosen["priority"] if chosen else None,
                               monthly_rank=window.get("monthly_rank"),
                               provisional_month=window.get("provisional"))
                row.update(episode_text_fields(labeled.get(episode_id)))
                episodes.append(row)
        if len(episodes) != len(episode_ids):
            raise ExportError(f"{len(episode_ids) - len(episodes)} episodes are missing from {db_path}")
        episodes.sort(key=lambda row: row["episode_id"])
        counts["episodes"] = write_table(episodes, out / "metadata" / "episodes.parquet")

        # A podcast can chart under more than one study entity: aggregate them.
        entities_of: dict[int, list[sqlite3.Row]] = {}
        for member in members.values():
            if member["podcast_id"] is not None:
                entities_of.setdefault(int(member["podcast_id"]), []).append(member)
        podcast_ids = sorted({e["podcast_id"] for e in episodes if e["podcast_id"] is not None} | set(entities_of))
        podcasts = []
        for start in range(0, len(podcast_ids), 900):
            chunk = podcast_ids[start:start + 900]
            for r in db.execute(
                "SELECT id, title, publisher, apple_podcasts_id, spotify_id, rss_url, categories, description "
                f"FROM podcasts WHERE id IN ({','.join('?' * len(chunk))})", chunk
            ):
                podcast_id = int(r["id"])
                row = {"podcast_id": podcast_id, "title": r["title"], "publisher": r["publisher"],
                       "apple_podcasts_id": r["apple_podcasts_id"], "spotify_id": r["spotify_id"],
                       "rss_url": r["rss_url"], "categories": json.loads(r["categories"] or "[]"),
                       "description": r["description"]}
                if study:
                    titles: list[str] = []
                    for member in entities_of.get(podcast_id, []):
                        titles += [t for t in json.loads(member["attrs"] or "{}").get("titles", []) if t not in titles]
                    months = [w for w in windows.values() if w["podcast_id"] == podcast_id]
                    ranks = [w["monthly_rank"] for w in months if w["monthly_rank"] is not None]
                    row.update(study_entities=sorted(m["entity"] for m in entities_of.get(podcast_id, [])),
                               chart_titles=titles, months_in_study=len({w["month"] for w in months}),
                               first_month=min((w["month"] for w in months), default=None),
                               last_month=max((w["month"] for w in months), default=None),
                               best_monthly_rank=min(ranks, default=None))
                podcasts.append(row)
        counts["podcasts"] = write_table(podcasts, out / "metadata" / "podcasts.parquet")

        if study:
            labeled_months = {(e["study_entity"], e["study_month"]) for e in episodes if e["labeled"]}
            selected_months = {(e["study_entity"], e["study_month"]) for e in episodes}
            by_year: dict[str, Counter] = {}
            for key, window in windows.items():
                year = by_year.setdefault(window["month"][:4], Counter())
                year["show_months"] += 1
                year["without_labeled_episode"] += key not in labeled_months
            with_episodes = {e["podcast_id"] for e in episodes}
            with_labels = {e["podcast_id"] for e in episodes if e["labeled"]}
            unmatched = [m for m in members.values() if m["podcast_id"] is None]
            stats["coverage"] = {
                "study_episodes": len(selection),
                "labeled_study_episodes": sum(e["labeled"] for e in episodes),
                "show_months": len(windows),
                "show_months_without_any_study_episode": sum(k not in selected_months for k in windows),
                "show_months_without_labeled_episode": sum(k not in labeled_months for k in windows),
                "show_months_without_labeled_episode_by_year": {y: dict(c) for y, c in sorted(by_year.items())},
                "podcasts_without_study_episodes": sum(p["podcast_id"] not in with_episodes for p in podcasts),
                "podcasts_without_labeled_episodes": sum(p["podcast_id"] not in with_labels for p in podcasts),
                "chart_entities_without_catalog_podcast": sorted(m["name"] for m in unmatched),
            }
        return study_info
    finally:
        db.close()


def export_taxonomy(run: Path, out: Path, taxonomy: dict[str, Any]) -> None:
    directory = out / "taxonomy"
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copy(run / "taxonomy.json", directory / "taxonomy.json")
    rows = [{"label_id": l["label_id"], "axis": l["axis"], "level": l.get("level"), "name": l["name"],
             "parent_topic_id": l.get("parent"), "domain": l.get("domain"),
             "narrative_family": l.get("family"), "narrative_family_name": l.get("family_name"),
             "narrative_home_topic": l.get("home_topic"), "definition": l["definition"],
             "concepts": "; ".join(l.get("concepts") or [])} for l in taxonomy["labels"]]
    with (directory / "labels.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if taxonomy.get("domains"):
        with (directory / "domains.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["domain_id", "name"])
            writer.writeheader()
            writer.writerows(taxonomy["domains"])
    sources = [REPO / taxonomy["source_path"]]
    version = taxonomy.get("taxonomy_version")
    if version:
        sources += [labeling.TAXONOMY_DIR / f"codebook-{version}.md", labeling.PROMPTS_DIR / f"rubric-{version}.md"]
    else:
        sources.append(labeling.CODEBOOK_PATH)
    for source in sources:
        if source.exists():
            shutil.copy(source, directory / source.name)


def generated_readme(manifest: dict[str, Any]) -> str:
    counts, labeling_info = manifest["row_counts"], manifest["labeling"]
    study = manifest.get("study")
    lines = [
        f"# {manifest['release']}",
        "",
        "Machine-generated health-content labels for podcast transcripts"
        + (f" in the `{study['name']}` study (revision {study['revision']})." if study else "."),
        "The labels describe what was said and how it was framed; they do not say whether it is true,",
        "and they have not been human-verified. `MANIFEST.json` records how they were produced.",
        "",
        "## Tables (Parquet)",
        "",
        "| File | Rows | One row per |",
        "|---|---|---|",
    ]
    described = [
        ("labels/annotations.parquet", "annotations", "label annotation (any axis) on a transcript span"),
        ("labels/clips.parquet", "clips", "merged topic clip, with all axes nested"),
        ("labels/claims.parquet", "claims", "atomic checkable claim (unverified)"),
        ("labels/products.parquet", "products", "specific product mention"),
        ("labels/episode_label_summary.parquet", "episode_label_summary", "labeled episode: counts per label"),
        ("labels/window_outputs.parquet", "window_outputs", "window: validated model output and token usage"),
        ("transcripts/units.parquet", "units", "sentence-like transcript unit (the IDs spans use)"),
        ("transcripts/windows.parquet", "windows", "labeling window: unit and time range"),
        ("metadata/episodes.parquet", "episodes", "episode (with `labeled` = has transcript and labels)"),
        ("metadata/podcasts.parquet", "podcasts", "podcast"),
        ("metadata/study_windows.parquet", "study_windows", "study show-month with chart evidence"),
    ]
    for path, key, meaning in described:
        if key in counts:
            lines.append(f"| `{path}` | {counts[key]:,} | {meaning} |")
    lines += [
        "",
        "`labels/clips_review.csv.gz` is a flat CSV of the clips for spreadsheet review, and `taxonomy/`",
        "holds every label's definition (`labels.csv`) and the codebook the model was prompted with.",
        "",
        "## Joining",
        "",
        "- `episode_id` joins to `metadata/episodes.parquet`; `podcast_id` to `metadata/podcasts.parquet`.",
        "- A span is `(episode_id, start_unit_id … end_unit_id)`, inclusive; join `transcripts/units.parquet`",
        "  on `(episode_id, unit_id)` (or `unit_index` between `start_unit_index` and `end_unit_index`).",
        "- `label_id` joins to `taxonomy/labels.csv`; clips list their claims (`verification_candidate_ids` →",
        "  `claims.candidate_id`) and products (`product_mention_ids` → `products.mention_id`).",
        "",
        "## Reading the labels",
        "",
        "- `relevance` is `substantive`, `passing` or `advertisement`; filter to `substantive` for real discussion.",
        "- `discourse_role` separates endorsing, quoting, questioning and rebutting a proposition.",
        "- `confidence` is the model's coding confidence; `expressed_certainty` on claims is the speaker's.",
        "- `possible_misinformation` is true whenever a clip or episode contains at least one extracted",
        "  checkable claim. It is not a finding that anything is false.",
        "- Unit timestamps are interpolated within transcript segments (`timing_quality`); locate text by unit.",
        "",
        "## Provenance",
        "",
        f"- Model `{labeling_info.get('model')}`, reasoning effort `{labeling_info.get('reasoning_effort')}`, "
        f"temperature {labeling_info.get('temperature')}, validation `{labeling_info.get('validation')}`.",
        f"- {labeling_info.get('windows_labeled'):,} windows labeled, "
        f"{labeling_info.get('unresolved_windows')} unresolved; run fingerprint "
        f"`{labeling_info.get('run_fingerprint')}`.",
        f"- Taxonomy {manifest['taxonomy'].get('version') or 'flat'} "
        f"(`{manifest['taxonomy']['taxonomy_sha256'][:12]}…`).",
    ]
    if manifest.get("stats", {}).get("coverage"):
        coverage = manifest["stats"]["coverage"]
        lines += [
            f"- Coverage: {coverage['labeled_study_episodes']:,} of {coverage['study_episodes']:,} study episodes "
            f"labeled; {coverage['show_months_without_labeled_episode']:,} of {coverage['show_months']:,} "
            "show-months have no labeled episode (see `MANIFEST.json` → `stats.coverage`).",
        ]
    return "\n".join(lines) + "\n"


def export(run: Path, out: Path, metadata_db: Path | None = None, study: str | None = None,
           readme: Path | None = None) -> dict[str, Any]:
    if study and not metadata_db:
        raise ExportError("--study needs --metadata-db")
    if out.exists() and any(out.iterdir()):
        raise ExportError(f"{out} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    prepare_manifest = json.loads((run / "prepare_manifest.json").read_text(encoding="utf-8"))
    label_manifest = json.loads((run / "label_manifest.json").read_text(encoding="utf-8"))
    merge_summary = json.loads((run / "merge_summary.json").read_text(encoding="utf-8"))
    taxonomy = json.loads((run / "taxonomy.json").read_text(encoding="utf-8"))
    if not merge_summary.get("complete"):
        raise ExportError("merge_summary.json reports an incomplete merge; finish labeling and rerun merge")
    if merge_summary.get("labeling_run_fingerprint") != label_manifest.get("run_fingerprint"):
        raise ExportError("merge outputs come from a different labeling run; rerun merge")
    counts: dict[str, int] = {}
    stats: dict[str, Any] = {}
    export_labels(run, out, merge_summary, counts, stats)
    export_window_outputs(run, out, counts)
    labeled = export_transcripts(run, out, prepare_manifest, counts, stats)
    study_info = export_metadata(metadata_db, study, out, labeled, counts, stats) if metadata_db else None
    export_taxonomy(run, out, taxonomy)
    keys = ("model", "api", "validation", "prompt_version", "reasoning_effort", "max_output_tokens",
            "temperature", "top_p", "thinking_token_budget", "seed", "run_fingerprint",
            "windows_labeled", "unresolved_windows", "completed_at", "validation_totals")
    manifest: dict[str, Any] = {
        "release": out.name,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "study": study_info,
        "taxonomy": {"version": taxonomy.get("taxonomy_version"), "taxonomy_sha256": taxonomy["taxonomy_sha256"],
                     "source_sha256": taxonomy.get("source_sha256"), "schema_version": taxonomy["schema_version"]},
        "windowing": prepare_manifest.get("windowing"),
        "prepare": {k: prepare_manifest.get(k) for k in ("episode_filter", "order", "episodes_prepared",
                                                         "windows_sha256")},
        "labeling": {k: label_manifest[k] for k in keys if k in label_manifest},
        "merge": {k: merge_summary.get(k) for k in ("schema_version", "episodes", "topic_clips",
                                                     "label_annotations", "verification_candidates",
                                                     "product_mentions", "complete")},
        "code_commit": git_commit(),
        "row_counts": counts,
        "stats": stats,
    }
    if readme is not None:
        shutil.copy(readme, out / "README.md")
    else:
        (out / "README.md").write_text(generated_readme(manifest), encoding="utf-8")
    files = sorted(path for path in out.rglob("*") if path.is_file())
    manifest["files"] = {
        str(path.relative_to(out)): {"bytes": path.stat().st_size, "sha256": labeling.sha256_file(path)}
        for path in files
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", type=Path, required=True, help="merged labeling run directory")
    parser.add_argument("--out", type=Path, required=True, help="new (empty) release directory")
    parser.add_argument("--metadata-db", type=Path, help="catalog database for episode/podcast metadata")
    parser.add_argument("--study", help="study whose selection and chart evidence to include")
    parser.add_argument("--readme", type=Path, help="README to ship instead of the generated one")
    args = parser.parse_args(argv)
    try:
        manifest = export(args.run_dir, args.out, args.metadata_db, args.study, args.readme)
    except (ExportError, labeling.TopicLabelingError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"release": str(args.out), "row_counts": manifest["row_counts"],
                      "stats": manifest["stats"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
