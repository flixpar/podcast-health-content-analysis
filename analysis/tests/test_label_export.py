"""label_export: a merged run becomes a checksummed, joinable release."""

import argparse
import json
import sqlite3

import pyarrow.parquet as pq
import pytest

from analysis import label_export
from analysis import topic_labeling as labeling
from analysis.tests.test_labeling_robustness import prepare_args, write_transcripts
from analysis.tests.test_topic_labeling import ROOT

TOPIC = "topic:sleep.sleep_duration_quality"


def merged_run(tmp_path, monkeypatch, episode_ids=(3, 5)):
    """prepare -> label (fake model: one sleep detection per window) -> merge."""
    transcripts = tmp_path / "transcripts"
    write_transcripts(transcripts, episode_ids)
    run = tmp_path / "run"
    prepare = labeling.run_prepare(prepare_args(
        tmp_path, transcripts, output_dir=run, topics=ROOT / "taxonomy" / "health-v8.md"
    ))

    def fake_classify(self, window, taxonomy, model, *rest, **kwargs):
        unit = window["units"][0]
        detection = {
            "axis": "topic", "label_ids": [TOPIC], "start_unit_id": unit["unit_id"],
            "end_unit_id": unit["unit_id"], "evidence_quote": unit["text"].split(" discusses")[0],
            "summary": "Sleep is discussed.", "confidence": 0.9, "relevance": "substantive",
            "discourse_role": "asserted_or_endorsed",
        }
        result = {"window_id": window["window_id"], "detections": [detection],
                  "verification_candidates": [], "product_mentions": []}
        return result, {"response_id": "r", "response_model": model,
                        "usage": {"completion_tokens": 10}, "attempts": 1,
                        "validation": {"mode": "lenient", "repaired": {}, "dropped": {}}}

    monkeypatch.setattr(labeling.ResponsesClient, "classify", fake_classify)
    monkeypatch.setattr(
        labeling.ResponsesClient, "served_models", lambda self: {r: "fake" for r in self.roots}
    )
    labeling.run_label(argparse.Namespace(
        output_dir=run, taxonomy=run / "taxonomy.json", windows=run / "windows.jsonl.zst",
        prepare_manifest=run / "prepare_manifest.json", api_base=["http://127.0.0.1:1/v1"],
        api=labeling.DEFAULT_API, model="fake", api_key_env=None, env_file=None, concurrency=1,
        max_output_tokens=100, timeout=10, attempts=1, reasoning_effort="none", temperature=None,
        top_p=None, seed=None, validation="lenient", usage_limits=None, provider=None,
        experiment=None, config=tmp_path / "none.toml",
    ))
    labeling.run_merge(argparse.Namespace(
        output_dir=run, taxonomy=run / "taxonomy.json", windows=run / "windows.jsonl.zst",
        label_manifest=run / "label_manifest.json", allow_incomplete=False,
    ))
    return run, prepare


def catalog(tmp_path):
    """A study of two show-months for one podcast charting under two entities, plus an
    episode without a transcript and a chart entity never matched to a podcast."""
    path = tmp_path / "catalog.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE studies (name TEXT, revision INTEGER, definition_hash TEXT, refreshed_at TEXT,
                              definition TEXT);
        CREATE TABLE study_members (study TEXT, entity TEXT, podcast_id INTEGER, name TEXT,
                                    scope TEXT, attrs TEXT);
        CREATE TABLE study_windows (study TEXT, entity TEXT, label TEXT, start_date TEXT,
                                    end_date TEXT, attrs TEXT);
        CREATE TABLE study_episodes (study TEXT, episode_id INTEGER, entity TEXT, window_label TEXT,
                                     priority INTEGER, added_revision INTEGER);
        CREATE TABLE episodes (id INTEGER, podcast_id INTEGER, title TEXT, description TEXT,
                               published_date TEXT, duration_seconds INTEGER, audio_url TEXT,
                               has_rss_transcript INTEGER, status TEXT);
        CREATE TABLE podcasts (id INTEGER, title TEXT, publisher TEXT, apple_podcasts_id TEXT,
                               spotify_id TEXT, rss_url TEXT, categories TEXT, description TEXT);
        INSERT INTO studies VALUES ('s', 4, 'abc', '2026-10-01', '{"version": 1}');
        INSERT INTO study_members VALUES
          ('s', 'apple:1', 9, 'Show', 'windows', '{"titles": ["Old title"]}'),
          ('s', 'podcast:9', 9, 'Show', 'windows', '{"titles": ["Show"]}'),
          ('s', 'title:lost', NULL, 'Lost show', 'windows', '{}');
        INSERT INTO study_windows VALUES
          ('s', 'apple:1', '2019-07', '2019-07-01', '2019-08-01', '{"monthly_rank": 4}'),
          ('s', 'podcast:9', '2021-04', '2021-04-01', '2021-05-01', '{"monthly_rank": 2}'),
          ('s', 'title:lost', '2021-04', '2021-04-01', '2021-05-01', '{"monthly_rank": 20}');
        INSERT INTO study_episodes VALUES
          ('s', 3, 'apple:1', '2019-07', 0, 1),
          ('s', 5, 'podcast:9', '2021-04', 0, 1),
          ('s', 8, 'podcast:9', '2021-04', 1, 1);
        INSERT INTO episodes VALUES
          (3, 9, 'E3', '', '2019-07-02', 60, 'a', 0, 'transcribed'),
          (5, 9, 'E5', '', '2021-04-02', 60, 'b', 0, 'transcribed'),
          (8, 9, 'E8', '', '2021-04-03', 60, 'c', 0, 'error');
        INSERT INTO podcasts VALUES (9, 'Show', 'Pub', '1', NULL, 'rss', '["Health"]', 'd');
        """
    )
    db.commit()
    db.close()
    return path


def test_a_merged_run_exports_to_a_checksummed_joinable_release(tmp_path, monkeypatch):
    run, prepare = merged_run(tmp_path, monkeypatch)
    out = tmp_path / "release"
    manifest = label_export.export(run, out, catalog(tmp_path), "s")

    for name, entry in manifest["files"].items():
        assert labeling.sha256_file(out / name) == entry["sha256"]
    assert (out / "README.md").read_text().startswith("# release")
    counts = manifest["row_counts"]
    assert counts["windows"] == prepare["windows"] and counts["units"] == prepare["units"]
    assert counts["annotations"] == 2 and counts["window_outputs"] == 2

    annotations = pq.read_table(out / "labels" / "annotations.parquet").to_pylist()
    assert {row["label_id"] for row in annotations} == {TOPIC}
    assert "source_transcript" not in annotations[0] and "labeling_model" not in annotations[0]
    units = {(r["episode_id"], r["unit_id"]): r["text"]
             for r in pq.read_table(out / "transcripts" / "units.parquet").to_pylist()}
    for row in annotations:
        assert row["evidence_quote"] in units[(row["episode_id"], row["start_unit_id"])]

    episodes = {r["episode_id"]: r for r in pq.read_table(out / "metadata" / "episodes.parquet").to_pylist()}
    assert sorted(episodes) == [3, 5, 8]
    assert [episodes[i]["labeled"] for i in (3, 5, 8)] == [True, True, False]
    assert episodes[3]["study_month"] == "2019-07" and episodes[3]["monthly_rank"] == 4

    (podcast,) = pq.read_table(out / "metadata" / "podcasts.parquet").to_pylist()
    assert podcast["study_entities"] == ["apple:1", "podcast:9"]
    assert podcast["months_in_study"] == 2 and podcast["first_month"] == "2019-07"
    assert podcast["chart_titles"] == ["Old title", "Show"] and podcast["best_monthly_rank"] == 2

    coverage = manifest["stats"]["coverage"]
    assert coverage["show_months_without_labeled_episode"] == 1
    assert coverage["chart_entities_without_catalog_podcast"] == ["Lost show"]
    assert manifest["labeling"]["validation_totals"]["windows_with_validation_record"] == 2
    assert manifest["merge"]["schema_version"] == manifest["taxonomy"]["schema_version"]


def test_export_without_a_catalog_keeps_labels_and_transcripts(tmp_path, monkeypatch):
    run, _ = merged_run(tmp_path, monkeypatch)
    manifest = label_export.export(run, tmp_path / "release")
    assert "episodes" not in manifest["row_counts"]
    assert (tmp_path / "release" / "taxonomy" / "labels.csv").exists()


def test_export_refuses_stale_merge_outputs_and_a_used_directory(tmp_path, monkeypatch):
    run, _ = merged_run(tmp_path, monkeypatch)
    used = tmp_path / "used"
    used.mkdir()
    (used / "x").write_text("x")
    with pytest.raises(label_export.ExportError, match="not empty"):
        label_export.export(run, used)
    with (run / "clips.jsonl").open("a") as handle:
        handle.write(json.dumps({"clip_id": "tampered"}) + "\n")
    with pytest.raises(label_export.ExportError, match="rerun merge"):
        label_export.export(run, tmp_path / "release")
