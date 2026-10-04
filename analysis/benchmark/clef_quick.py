"""Score a System One run's stored judgments under a policy, per split; no requests.

The quick read used while comparing Clef policies (docs/clef-labeling.md): the
same compose-and-score path as ``typesafe_tune``, but for any split, any subset
of repeats, and a policy given as JSON overrides.

    .venv/bin/python -m analysis.benchmark.clef_quick benchmark/runs/flash-v1 \
        --policy '{"claim_threshold": 0.8}' --split dev test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from analysis import typesafe_labeling as typesafe
from analysis.benchmark import GOLD_PATH, ITEMS_PATH, TAXONOMY_PATH
from analysis.benchmark import items as items_mod
from analysis.benchmark import references as refs_mod
from analysis.benchmark.report import HEADLINE_ROWS
from analysis.benchmark.taxonomy import load_benchmark_taxonomy
from analysis.benchmark.typesafe_tune import load_judgments, score_policy

# The scorecard's headline strata; rare-label windows are scored separately.
HEADLINE = ("health_dense", "mixed", "null", "ad_read", "discourse")


def summarize(run_dir: Path, policy: typesafe.Policy, splits: Sequence[str], repeats: Sequence[int] | None) -> dict:
    """The scorecard's headline rows per split, for ``policy`` over the stored judgments."""
    taxonomy = load_benchmark_taxonomy(TAXONOMY_PATH)
    gold = refs_mod.load_gold(GOLD_PATH)
    judgments = load_judgments(run_dir)
    if repeats is not None:
        judgments = [judgments[index] for index in repeats]
    out = {}
    for split in splits:
        items = [
            item for item in items_mod.load_items(ITEMS_PATH)
            if item["split"] == split and item["stratum"] in HEADLINE
        ]
        groups = score_policy(judgments, items, gold, taxonomy, policy)["groups"]
        out[split] = {label: groups[group].get(field) for label, group, field in HEADLINE_ROWS}
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--policy", default="{}", help="Policy overrides as JSON, or @file.json")
    parser.add_argument("--split", nargs="+", default=["dev", "test"])
    parser.add_argument("--repeats", nargs="+", type=int)
    args = parser.parse_args(argv)
    text = Path(args.policy[1:]).read_text() if args.policy.startswith("@") else args.policy
    policy = typesafe.Policy.from_mapping(json.loads(text))
    result = summarize(args.run_dir, policy, args.split, args.repeats)
    print(f"| metric | {' | '.join(args.split)} |")
    print(f"| --- | {' | '.join('---' for _ in args.split)} |")
    for label, _, _ in HEADLINE_ROWS:
        cells = [result[split][label] for split in args.split]
        print(f"| {label} | " + " | ".join("-" if v is None else f"{v:.3f}" for v in cells) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
