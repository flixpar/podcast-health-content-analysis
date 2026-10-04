"""One table of headline numbers across scored runs.

    python exp/summarize.py benchmark/v2/runs/* [--split headline|dev|test] [--stratum narrative] [--md]

Reads each run's score.json (written by `python -m analysis.benchmark score`).
`headline` is the corpus strata of both splits pooled (160 items on v2).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def pick(score: dict, split: str, stratum: str | None) -> dict:
    mean = score["mean"]
    if stratum:
        return mean["by_stratum"].get(stratum, {})
    return mean["headline"] if split == "headline" else mean["by_split"].get(split, {})


def level_f1(score: dict, level: str, split: str) -> float | None:
    entry = score.get("levels", {}).get(level, {})
    block = entry.get("headline") if split == "headline" else entry.get("by_split", {}).get(split)
    return (block or {}).get("f1_strict")


def row(run_dir: Path, split: str, stratum: str | None) -> dict | None:
    path = run_dir / "score.json"
    if not path.exists():
        return None
    score = json.loads(path.read_text())
    block = pick(score, split, stratum)
    groups = block.get("groups", {})
    g = lambda name, key: (groups.get(name) or {}).get(key)  # noqa: E731
    usage = score.get("usage", {})
    null = (score["mean"]["headline"].get("null") or {}) if not stratum else {}
    return {
        "run": run_dir.name,
        "items": block.get("items"),
        "topic P": g("detection:topic", "precision"),
        "topic R": g("detection:topic", "recall_strict"),
        "topic F1": g("detection:topic", "f1_strict"),
        "parent F1": None if stratum else level_f1(score, "parent", split),
        "domain F1": None if stratum else level_f1(score, "domain", split),
        "narr F1": g("detection:narrative", "f1_strict"),
        "frame F1": g("detection:frame", "f1_strict"),
        "evid F1": g("detection:evidence", "f1_strict"),
        "pop F1": g("detection:population", "f1_strict"),
        "claim P": g("claim", "precision"),
        "claim R": g("claim", "recall_strict"),
        "claim F1": g("claim", "f1_strict"),
        "prod F1": g("product", "f1_strict"),
        "topic yield": g("detection:topic", "yield_ratio"),
        "null atoms/w": null.get("atoms_per_window"),
        "out tok/w": usage.get("output_tokens_per_accepted_window"),
        "1st valid": usage.get("first_attempt_validity"),
        "self-agree topic": ((score.get("repeat_agreement") or {}).get("detection:topic") or {}).get("f1"),
    }


def fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}" if value < 10 else f"{value:,.0f}"
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--split", default="headline", choices=("headline", "dev", "test"))
    parser.add_argument("--stratum")
    parser.add_argument("--cols", nargs="*")
    args = parser.parse_args()
    rows = [r for r in (row(p, args.split, args.stratum) for p in args.runs) if r]
    if not rows:
        return 0
    cols = args.cols or [c for c in rows[0] if any(r[c] is not None for r in rows)]
    if "run" not in cols:
        cols = ["run", *cols]
    print("| " + " | ".join(cols) + " |")
    print("| " + " | ".join("---" for _ in cols) + " |")
    for r in rows:
        print("| " + " | ".join(fmt(r[c]) for c in cols) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
