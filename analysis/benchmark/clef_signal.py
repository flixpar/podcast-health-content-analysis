"""How good is each stage's raw signal, before any threshold?

Thresholds can only trade precision for recall along the curve a model's
probabilities draw; they cannot move the curve. So this reads each stage of a
System One run against the gold directly:

- **screen**: per (window, label), the window probability against whether the
  gold has a required atom of that label in the window (AUROC, and recall of
  gold labels at the fan-out threshold with the labels per window it costs);
- **gate**: the health gate against whether the window has any required atom;
- **localize**: per (window, label) that was localized, unit probabilities
  against the units inside the gold atoms' tight spans (average precision,
  pooled), so it is read only where the label is really present;
- **claim units**: the same for the claim question against required claims.

    .venv/bin/python -m analysis.benchmark.clef_signal benchmark/runs/flash-v1 --split dev
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from analysis.benchmark import GOLD_PATH, ITEMS_PATH
from analysis.benchmark import items as items_mod
from analysis.benchmark import references as refs_mod
from analysis.benchmark.clef_screen import auroc
from analysis.benchmark.taxonomy import label_axes, load_benchmark_taxonomy
from analysis.benchmark.typesafe_tune import load_judgments

STRATA = ("health_dense", "mixed", "null", "ad_read", "discourse", "rare_label")
CREDITED = ("required", "acceptable")


def average_precision(scores: Sequence[float], labels: Sequence[bool]) -> float | None:
    ranked = sorted(zip(scores, labels), key=lambda pair: -pair[0])
    positives = sum(labels)
    if not positives:
        return None
    hits = 0
    total = 0.0
    for rank, (_, label) in enumerate(ranked, start=1):
        if label:
            hits += 1
            total += hits / rank
    return total / positives


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dirs", type=Path, nargs="+")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--fanout", type=float, default=0.3)
    args = parser.parse_args(argv)
    gold = refs_mod.load_gold(GOLD_PATH)
    axes = label_axes(load_benchmark_taxonomy())
    items = {
        item["window_id"]: item for item in items_mod.load_items(ITEMS_PATH)
        if item["split"] == args.split and item["stratum"] in STRATA
    }
    for run_dir in args.run_dirs:
        judgments = load_judgments(run_dir)[args.repeat]
        screen_scores, screen_labels = [], []
        gate_scores, gate_labels = [], []
        loc: dict[str, tuple[list[float], list[bool]]] = defaultdict(lambda: ([], []))
        fanned = gold_labels = gold_kept = 0
        windows = 0
        for window_id, item in items.items():
            stored = judgments.get(window_id)
            if stored is None or item["item_id"] not in gold:
                continue
            windows += 1
            atoms = [atom for atom in gold[item["item_id"]] if atom.tier in CREDITED]
            present: dict[str, list[tuple[int, int]]] = defaultdict(list)
            for atom in atoms:
                if atom.kind == "detection":
                    present[atom.label].append(atom.tight)
                elif atom.kind == "claim":
                    present["claim"].append(atom.tight)
            gate_scores.append(stored["gates"]["health"])
            gate_labels.append(bool(atoms))
            for label_id, p in stored["window"].items():
                screen_scores.append(p)
                screen_labels.append(label_id in present)
                fanned += p >= args.fanout
            gold_labels += sum(1 for label in present if label != "claim")
            gold_kept += sum(
                1 for label in present if label != "claim" and stored["window"].get(label, 0.0) >= args.fanout
            )
            count = len(item["units"])
            sizes = stored.get("passage_units") or {}
            for name, probs in [*stored["labels"].items(), *stored["units"].items()]:
                if name == "product" or name not in present:
                    continue
                key = "claim" if name == "claim" else axes.get(name, "topic")
                size = 1 if name == "claim" else int(sizes.get(key, 1))
                unit_probs = [p for p in probs for _ in range(size)][:count]
                inside = [False] * count
                for start, end in present[name]:
                    for index in range(start, min(end, count - 1) + 1):
                        inside[index] = True
                loc[key][0].extend(unit_probs)
                loc[key][1].extend(inside[: len(unit_probs)])
        print(f"\n== {run_dir.name} ({args.split}, repeat {args.repeat}, {windows} windows)")
        print(f"health gate AUROC (window has any credited atom): {auroc(gate_scores, gate_labels):.3f}")
        print(f"label screen AUROC (per window x label): {auroc(screen_scores, screen_labels):.3f}")
        print(
            f"at fan-out {args.fanout}: {gold_kept}/{gold_labels} gold labels kept "
            f"({gold_kept / max(gold_labels, 1):.1%}), {fanned / max(windows, 1):.1f} labels per window"
        )
        for key, (scores, labels) in sorted(loc.items()):
            ap = average_precision(scores, labels)
            base = sum(labels) / max(len(labels), 1)
            print(f"localize {key:10s} unit AP {ap:.3f} (base rate {base:.3f}, AUROC {auroc(scores, labels):.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
