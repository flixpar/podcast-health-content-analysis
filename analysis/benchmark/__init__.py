"""Benchmark for the podcast health-content labeler.

The benchmark is a fixed set of transcript windows (``local/benchmark/items.jsonl``)
with reference labels from several annotators (``local/benchmark/references/``),
aggregated into a soft gold (``local/benchmark/gold.jsonl``) that records where the
annotators agree and disagree. ``run`` labels the items with a candidate
configuration, ``score`` measures it against the gold and against the
annotators' own agreement, and ``compare`` puts two runs side by side with
bootstrap intervals. See ``docs/benchmark.md``.

Everything an agent produces (references, synthetic items, screening,
adjudication) passes through ``tasks.py`` bundles and is validated on ingest;
nothing enters the benchmark unvalidated.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

# Repository root, resolved from this file so the CLI works from anywhere.
REPO_ROOT = Path(__file__).resolve().parents[2]
# Select tracked benchmark specifications with BENCHMARK_DIR. Their config
# names a separate, ignored artifact directory; external configs without
# data_dir retain the original behavior of storing artifacts beside the config.
DATA_DIR_ENV = "BENCHMARK_DIR"
OUTPUT_DIR_ENV = "BENCHMARK_OUTPUT_DIR"
_selected = Path(os.environ.get(DATA_DIR_ENV) or "benchmark")
SPEC_DIR = _selected if _selected.is_absolute() else REPO_ROOT / _selected
CONFIG_PATH = SPEC_DIR / "config.toml"


def _config_value(section: str, key: str) -> str | None:
    try:
        with CONFIG_PATH.open("rb") as handle:
            return tomllib.load(handle).get(section, {}).get(key)
    except FileNotFoundError:
        return None


# The version and the codebook are properties of the benchmark directory, so
# a v2 task bundle can never be written with v1's codebook or stamped v1.
BENCHMARK_VERSION = _config_value("benchmark", "version") or "v1"
_output = os.environ.get(OUTPUT_DIR_ENV) or _config_value("benchmark", "data_dir")
_data = Path(_output) if _output else SPEC_DIR
DATA_DIR = _data if _data.is_absolute() else REPO_ROOT / _data
ITEMS_PATH = DATA_DIR / "items.jsonl"
GOLD_PATH = DATA_DIR / "gold.jsonl"
TAXONOMY_PATH = DATA_DIR / "taxonomy.json"
ANNOTATORS_PATH = DATA_DIR / "annotators.json"
ANNOTATOR_SPECS_PATH = SPEC_DIR / "annotators.json"
ADJUDICATION_PATH = DATA_DIR / "adjudication.jsonl"
AGREEMENT_PATH = DATA_DIR / "agreement.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"
REFERENCES_DIR = DATA_DIR / "references"
RUNS_DIR = DATA_DIR / "runs"
POOL_DIR = DATA_DIR / "pool"
_codebook = _config_value("paths", "codebook")
CODEBOOK_PATH = REPO_ROOT / _codebook if _codebook else Path(__file__).resolve().parent / "codebook.md"
