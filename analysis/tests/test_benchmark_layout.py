"""A fresh checkout generates benchmark artifacts away from tracked specs."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from analysis import topic_labeling as tl
from analysis.benchmark.taxonomy import load_benchmark_taxonomy


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("spec,version", [("benchmark", "v1"), ("benchmark/v2", "v2"), ("benchmark/v3", "v3")])
def test_benchmark_cli_generates_local_taxonomy_and_preserves_roster(tmp_path, spec, version):
    env = {**os.environ, "BENCHMARK_DIR": spec}
    env.pop("BENCHMARK_OUTPUT_DIR", None)
    env.pop("BENCHMARK_TASKS_DIR", None)
    probe = """
import json
from analysis import benchmark as b
from analysis.benchmark.tasks import tasks_root
print(json.dumps({'config': str(b.CONFIG_PATH), 'data': str(b.DATA_DIR), 'version': b.BENCHMARK_VERSION, 'tasks': str(tasks_root())}))
"""
    result = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    paths = json.loads(result.stdout)
    assert paths == {"config": str(ROOT / spec / "config.toml"),
                     "data": str(ROOT / "local" / spec), "version": version,
                     "tasks": str(ROOT / "local" / "benchmark-tasks")}
    output = tmp_path / f"{version} output"
    env["BENCHMARK_OUTPUT_DIR"] = str(output)
    subprocess.run([sys.executable, "-m", "analysis.benchmark", "taxonomy"],
                   cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    taxonomy = load_benchmark_taxonomy(output / "taxonomy.json")
    assert taxonomy["benchmark_version"] == version
    assert set(taxonomy["label_aliases"]) == ({"v5-84"} if version == "v1" else {"parent", "domain"})
    roster = ROOT / spec / "annotators.json"
    before = roster.read_bytes()
    registration = """
from analysis.benchmark.references import register_annotator
register_annotator({'annotator_id': 'new-test', 'model': 'offline', 'method': 'test'})
"""
    subprocess.run([sys.executable, "-c", registration], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    registered = json.loads((output / "annotators.json").read_text())
    assert set(registered) == set(json.loads(before)) | {"new-test"}
    assert roster.read_bytes() == before
    # Generated validator instructions preserve the specification and output
    # override, including paths containing spaces. Execute them offline.
    tasks = tmp_path / "task bundles"
    env["BENCHMARK_TASKS_DIR"] = str(tasks)
    item = {"item_id": "offline", "window_id": "offline_window", "stratum": "health_dense",
            "source": "synthetic", "units": [{"unit_id": "u000001", "text": "Vaccines cause autism."}]}
    tl.write_jsonl_atomic(output / "items.jsonl", [item])
    subprocess.run([sys.executable, "-m", "analysis.benchmark", "reference", "tasks",
                    "--annotator", "offline", "--run-id", "test"],
                   cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    bundle = tasks / "reference" / "offline-test" / "bundle_001"
    command = next(line.strip() for line in (bundle / "INSTRUCTIONS.md").read_text().splitlines()
                   if "-m analysis.benchmark" in line)
    (bundle / "windows").mkdir()
    result = {"window_id": item["window_id"], "verification_candidates": [], "product_mentions": [],
              "detections": [{"start_unit_id": "u000001", "end_unit_id": "u000001",
                              "label_ids": ["topic:sleep" if version == "v1" else "narrative:vaccines_cause_autism"],
                              "relevance": "substantive", "discourse_role": "asserted_or_endorsed",
                              "confidence": 0.9, "summary": "Offline validation fixture.",
                              "evidence_quote": "Vaccines cause autism"}]}
    tl.write_json(bundle / "windows" / "offline_window.json", result)
    subprocess.run(command, shell=True, cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    assembled = json.loads((bundle / "results.json").read_text())
    assert assembled[0]["detections"][0]["label_ids"] == result["detections"][0]["label_ids"]


def test_missing_benchmark_taxonomy_explains_generation(tmp_path):
    with pytest.raises(tl.TopicLabelingError, match="python -m analysis.benchmark taxonomy"):
        load_benchmark_taxonomy(tmp_path / "taxonomy.json")


def test_shipped_pipeline_config_selects_v8_and_flat_source_remains_available(monkeypatch):
    monkeypatch.chdir(ROOT)
    parser = tl.build_parser()
    current = parser.parse_args(tl.expand_config_args(["prepare"]))
    assert current.topics == Path("taxonomy/health-v8.md")
    legacy = parser.parse_args(tl.expand_config_args(["prepare", "--topics", str(tl.DEFAULT_TOPICS)]))
    assert legacy.topics == Path("docs/original/topics.md")
    assert tl.compile_taxonomy(legacy.topics)["schema_version"] == tl.SCHEMA_VERSION
