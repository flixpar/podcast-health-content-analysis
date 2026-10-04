"""Shared loaders for the spec-vs-model analysis (read-only on benchmark data)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path("/scratch/fparker9/podcasts/podcast-health-content-analysis-01")
sys.path.insert(0, str(ROOT))

from analysis.benchmark import references as refs_mod  # noqa: E402
from analysis.benchmark import runner as runner_mod  # noqa: E402
from analysis.benchmark import items as items_mod  # noqa: E402
from analysis.benchmark.matching import WindowIndex, explode  # noqa: E402

B = ROOT / "benchmark"
OUT = B / "runs" / "analysis"
S70_RUNS = ["s70-high-lenient", "s70-high-chat-lenient", "s70-high-budget24k-lenient"]
DEV_RUN = "dev-high-chat-lenient"
ANNOTATORS = ["opus-r1", "opus-r2", "sonnet-r1", "sonnet-r2"]
HEADLINE = ("health_dense", "mixed", "null", "ad_read", "discourse")
CORPUS = HEADLINE + ("rare_label",)


@lru_cache(None)
def items() -> dict[str, dict]:
    return {it["item_id"]: it for it in items_mod.load_items(B / "items.jsonl")}


@lru_cache(None)
def gold() -> dict:
    return refs_mod.load_gold(B / "gold.jsonl")


@lru_cache(None)
def references() -> dict:
    return refs_mod.load_references(B / "references")


@lru_cache(None)
def agreement() -> dict:
    return json.loads((B / "agreement.json").read_text())


@lru_cache(None)
def taxonomy() -> dict:
    return json.loads((B / "taxonomy.json").read_text())


@lru_cache(None)
def index(item_id: str) -> WindowIndex:
    return WindowIndex(items()[item_id])


@lru_cache(None)
def run(name: str) -> dict:
    return runner_mod.load_run(B / "runs" / name)


def samples_for(item_id: str, pool: str) -> list[dict]:
    """Window results for one item: pool 's70' = up to 6 samples, 'dev' = dev run repeats."""
    wid = items()[item_id]["window_id"]
    names = S70_RUNS if pool == "s70" else [DEV_RUN]
    out = []
    for name in names:
        for rep in run(name)["repeats"]:
            if wid in rep:
                out.append(rep[wid])
    return out


def ref_atoms(item_id: str) -> dict[str, list]:
    idx = index(item_id)
    return {a: refs_mod._atoms_for(r, idx) for a, r in references()[item_id].items()}


def pred_atoms(result: dict, item_id: str) -> list:
    return explode(result, index(item_id))


def pool_items(pool: str, strata=CORPUS) -> list[str]:
    names = S70_RUNS if pool == "s70" else [DEV_RUN]
    wids = set()
    for name in names:
        for rep in run(name)["repeats"]:
            wids |= set(rep)
    return sorted(
        iid
        for iid, it in items().items()
        if it["window_id"] in wids and it.get("stratum") in strata and iid in gold()
    )


def group_of(atom) -> str:
    return f"detection:{atom.axis}" if atom.kind == "detection" else atom.kind


def label_key(atom) -> str:
    return atom.label if atom.kind == "detection" else atom.kind
