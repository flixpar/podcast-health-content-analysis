"""Paired comparison of two runs over the same items."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from analysis.benchmark import stats
from analysis.benchmark.runner import load_run
from analysis.benchmark.scoring import score_item

METRICS = [
    ("topic F1 (strict)", "detection:topic", "f1"),
    ("topic recall (required)", "detection:topic", "recall"),
    ("topic precision", "detection:topic", "precision"),
    ("frame F1 (strict)", "detection:frame", "f1"),
    ("evidence F1 (strict)", "detection:evidence", "f1"),
    ("claim recall (required)", "claim", "recall"),
    ("claim precision", "claim", "precision"),
    ("product F1 (strict)", "product", "f1"),
]


def _flat(row: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for group, counts in row["counts"].items():
        for key in ("tp", "fp", "fn"):
            out[f"{group}:{key}"] = float(counts.get(key, 0))
    return out


def _statistic(group: str, kind: str):
    def compute(rows: Sequence[dict[str, float]]) -> float:
        tp = sum(r.get(f"{group}:tp", 0) for r in rows)
        fp = sum(r.get(f"{group}:fp", 0) for r in rows)
        fn = sum(r.get(f"{group}:fn", 0) for r in rows)
        if kind == "f1":
            return stats.f1(tp, fp, fn)
        if kind == "recall":
            return stats.recall(tp, fn)
        return stats.precision(tp, fp)

    return compute


def compare_runs(run_a: Path, run_b: Path, items, gold, aliases, iterations: int = 2000) -> dict[str, Any]:
    a = load_run(run_a)
    b = load_run(run_b)
    by_window = {item["window_id"]: item for item in items if item["item_id"] in gold and item.get("source") != "contrast"}
    pairs_a: list[dict[str, float]] = []
    pairs_b: list[dict[str, float]] = []
    shared_items: set[str] = set()
    moved: list[dict[str, Any]] = []
    per_stratum: dict[str, dict[str, list[dict[str, float]]]] = defaultdict(lambda: {"a": [], "b": []})
    # Pair repeat r of A with repeat r of B; extra repeats on one side are dropped.
    for repeat_a, repeat_b in zip(a["repeats"], b["repeats"]):
        for window_id, item in by_window.items():
            if window_id not in repeat_a or window_id not in repeat_b:
                continue
            shared_items.add(item["item_id"])
            row_a = score_item(item, repeat_a[window_id], gold[item["item_id"]], aliases)
            row_b = score_item(item, repeat_b[window_id], gold[item["item_id"]], aliases)
            fa, fb = _flat(row_a), _flat(row_b)
            pairs_a.append(fa)
            pairs_b.append(fb)
            per_stratum[item["stratum"]]["a"].append(fa)
            per_stratum[item["stratum"]]["b"].append(fb)
            if item.get("split") == "dev":
                delta = abs(fa.get("detection:topic:tp", 0) - fb.get("detection:topic:tp", 0)) + abs(fa.get("detection:topic:fp", 0) - fb.get("detection:topic:fp", 0)) + abs(fa.get("detection:topic:fn", 0) - fb.get("detection:topic:fn", 0))
                moved.append({"item_id": item["item_id"], "stratum": item["stratum"], "delta": delta, "a_tp": fa.get("detection:topic:tp", 0), "b_tp": fb.get("detection:topic:tp", 0), "a_fp": fa.get("detection:topic:fp", 0), "b_fp": fb.get("detection:topic:fp", 0), "a_fn": fa.get("detection:topic:fn", 0), "b_fn": fb.get("detection:topic:fn", 0)})
    metrics = []
    for index, (label, group, kind) in enumerate(METRICS):
        statistic = _statistic(group, kind)
        boot = stats.paired_bootstrap(pairs_a, pairs_b, statistic, iterations, seed=index)
        metrics.append({"metric": label, "a": round(statistic(pairs_a), 4), "b": round(statistic(pairs_b), 4), **{k: round(v, 4) if isinstance(v, float) else v for k, v in boot.items()}})
    by_stratum = {}
    for stratum, sides in sorted(per_stratum.items()):
        by_stratum[stratum] = {
            "topic_a": round(_statistic("detection:topic", "f1")(sides["a"]), 4),
            "topic_b": round(_statistic("detection:topic", "f1")(sides["b"]), 4),
            "claim_a": round(_statistic("claim", "recall")(sides["a"]), 4),
            "claim_b": round(_statistic("claim", "recall")(sides["b"]), 4),
        }
    moved.sort(key=lambda r: -r["delta"])
    return {
        "a": a["manifest"].get("name"),
        "b": b["manifest"].get("name"),
        "items": len(shared_items),
        "rows": len(pairs_a),
        "metrics": metrics,
        "by_stratum": by_stratum,
        "moved_items": [m for m in moved if m["delta"] > 0][:30],
    }
