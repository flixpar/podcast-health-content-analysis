"""Tune the TypeSafe method's composition thresholds on a benchmark run, offline.

A ``--api typesafe`` run keeps every probability it was given in
``typesafe_judgments.jsonl``, and ``typesafe_labeling.compose_result`` turns
those into a window result under any policy without a request. So the
thresholds that decide spans are swept here against the benchmark's own scorer,
for free, instead of by re-labeling:

    BENCHMARK_DIR=benchmark .venv/bin/python -m analysis.benchmark.typesafe_tune local/benchmark/runs/ts-v1

Only the dev split is read. Only composition keys can be swept: the ones that
decide which questions are asked (passage sizes, the fan-out and gate
thresholds) need a new run, and a product span the sweep creates has no name
judgments, so product spans are left alone and only ``product_name_threshold``
moves. Each axis is swept on its own, which is exact: a detection's axis never
changes another axis's score, and claims are scored on spans and quotes.

The shipped defaults in ``typesafe_labeling.Policy`` came from this sweep over
an earlier dev run. Re-run on ``local/benchmark/runs/ts-v1`` it picks the same values
except ``product_name_threshold`` (0.5 over the shipped 0.7, F1 0.587 against
0.575, inside the noise); that run then scored them on the test split
(docs/typesafe-labeling.md).
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from analysis import topic_labeling as tl
from analysis import typesafe_labeling as typesafe
from analysis.benchmark import GOLD_PATH, ITEMS_PATH, TAXONOMY_PATH
from analysis.benchmark import items as items_mod
from analysis.benchmark import references as refs_mod
from analysis.benchmark import scoring
from analysis.benchmark.taxonomy import label_axes, load_benchmark_taxonomy

# Rare-label windows are in: they are where most labels have any gold at all.
STRATA = ("health_dense", "mixed", "null", "ad_read", "discourse", "rare_label")
DETECTION_GRID: dict[str, list[Any]] = {
    "window_threshold": [0.3, 0.5, 0.7, 0.85],
    "seed_threshold": [0.5, 0.6, 0.7, 0.8, 0.9],
    "extend_threshold": [0.2, 0.3, 0.5],
    "bridge_units": [0, 1],
}
GRIDS: dict[str, dict[str, list[Any]]] = {
    "detection:topic": DETECTION_GRID,
    "detection:frame": DETECTION_GRID,
    "detection:evidence": DETECTION_GRID,
    "claim": {"claim_threshold": [0.4, 0.5, 0.6, 0.7, 0.8], "max_claim_units": [1, 2, 3]},
    "product": {"product_name_threshold": [0.3, 0.5, 0.7, 0.8, 0.9]},
}


def load_judgments(run_dir: Path) -> list[dict[str, dict[str, Any]]]:
    """Per repeat, the last judgments recorded for each window."""
    repeats = []
    for path in sorted(Path(run_dir).glob(f"repeat_*/{tl.TYPESAFE_JUDGMENTS}")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        repeats.append({row["window_id"]: row for row in rows})
    if not repeats:
        raise tl.TopicLabelingError(f"{run_dir} has no {tl.TYPESAFE_JUDGMENTS}; is it a --api typesafe run?")
    return repeats


def score_policy(
    repeats: Sequence[dict[str, dict[str, Any]]],
    items: Sequence[dict[str, Any]],
    gold: dict[str, list[Any]],
    taxonomy: dict[str, Any],
    policy: typesafe.Policy,
) -> dict[str, Any]:
    """Pooled benchmark metrics for ``policy`` over every repeat's judgments."""
    axes = label_axes(taxonomy)
    rows = []
    for judgments in repeats:
        for item in items:
            stored = judgments.get(item["window_id"])
            if stored is None or item["item_id"] not in gold:
                continue
            raw = typesafe.compose_result(item, taxonomy, stored, policy)
            result = tl.validate_window_result(raw, item, axes)
            rows.append(scoring.score_item(item, result, gold[item["item_id"]]))
    return scoring.summarize(rows)


def sweep(
    repeats: Sequence[dict[str, dict[str, Any]]],
    items: Sequence[dict[str, Any]],
    gold: dict[str, list[Any]],
    taxonomy: dict[str, Any],
    group: str,
    base: dict[str, Any],
) -> list[tuple[float, dict[str, Any], dict[str, Any]]]:
    """(strict F1, overrides, group metrics) for every grid point, best first."""
    grid = GRIDS[group]
    axis = group.split(":")[-1]
    defaults = typesafe.Policy()
    results = []
    for combo in itertools.product(*grid.values()):
        overrides = dict(base)
        for key, value in zip(grid, combo):
            default = getattr(defaults, key)
            # Per-axis keys move for this group's axis only.
            overrides[key] = {**default, **base.get(key, {}), axis: value} if isinstance(default, dict) else value
        summary = score_policy(repeats, items, gold, taxonomy, typesafe.Policy.from_mapping(overrides))
        metrics = summary["groups"][group]
        results.append((metrics["f1_strict"] or 0.0, overrides, metrics))
    return sorted(results, key=lambda row: -row[0])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--top", type=int, default=3, help="Grid points to print per group")
    parser.add_argument("--out", type=Path, help="Write the best overrides here as JSON")
    args = parser.parse_args(argv)

    taxonomy = load_benchmark_taxonomy(TAXONOMY_PATH)
    tl.require_label_taxonomy("typesafe", taxonomy)
    gold = refs_mod.load_gold(GOLD_PATH)
    items = [
        item for item in items_mod.load_items(ITEMS_PATH)
        if item["split"] == "dev" and item["stratum"] in STRATA
    ]
    repeats = load_judgments(args.run_dir)
    best: dict[str, Any] = {}
    for group, grid in GRIDS.items():
        ranked = sweep(repeats, items, gold, taxonomy, group, best)
        for f1, overrides, metrics in ranked[: args.top]:
            shown = {key: overrides[key][group.split(":")[-1]] if isinstance(overrides[key], dict) else overrides[key] for key in grid}
            print(
                f"{group:20s} F1 {f1:.3f}  P {metrics['precision'] or 0:.3f}  R {metrics['recall_strict'] or 0:.3f}  "
                f"yield {metrics['yield_ratio'] or 0:.2f}  IoU {metrics['mean_span_iou'] or 0:.2f}  {shown}"
            )
        best = ranked[0][1]
    print(json.dumps(best, indent=2, sort_keys=True))
    if args.out:
        tl.write_json(args.out, best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
