"""Benchmark for the podcast health-content labeler.

The benchmark is a fixed set of transcript windows (``benchmark/items.jsonl``)
with reference labels from several annotators (``benchmark/references/``),
aggregated into a soft gold (``benchmark/gold.jsonl``) that records where the
annotators agree and disagree. ``run`` labels the items with a candidate
configuration, ``score`` measures it against the gold and against the
annotators' own agreement, and ``compare`` puts two runs side by side with
bootstrap intervals. See ``docs/benchmark.md``.

Everything an agent produces (references, synthetic items, screening,
adjudication) passes through ``tasks.py`` bundles and is validated on ingest;
nothing enters the benchmark unvalidated.
"""

from __future__ import annotations

from pathlib import Path

BENCHMARK_VERSION = "v1"
# Repository root, resolved from this file so the CLI works from anywhere.
REPO_ROOT = Path(__file__).resolve().parents[2]
# Tracked benchmark data. Not under ``analysis/`` because the root .gitignore
# ignores every path named ``data`` and ``output``.
DATA_DIR = REPO_ROOT / "benchmark"
CONFIG_PATH = DATA_DIR / "config.toml"
ITEMS_PATH = DATA_DIR / "items.jsonl"
GOLD_PATH = DATA_DIR / "gold.jsonl"
TAXONOMY_PATH = DATA_DIR / "taxonomy.json"
ANNOTATORS_PATH = DATA_DIR / "annotators.json"
ADJUDICATION_PATH = DATA_DIR / "adjudication.jsonl"
AGREEMENT_PATH = DATA_DIR / "agreement.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"
REFERENCES_DIR = DATA_DIR / "references"
RUNS_DIR = DATA_DIR / "runs"
POOL_DIR = DATA_DIR / "pool"
CODEBOOK_PATH = Path(__file__).resolve().parent / "codebook.md"
