"""Small statistics used by the benchmark: bootstrap, kappa, alpha, AUROC."""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any, Callable, Sequence


def paired_bootstrap(
    per_item_a: Sequence[dict[str, float]],
    per_item_b: Sequence[dict[str, float]],
    statistic: Callable[[Sequence[dict[str, float]]], float],
    iterations: int = 2000,
    seed: int = 0,
) -> dict[str, float]:
    """Bootstrap the difference statistic(B) - statistic(A) over paired items.

    Items are resampled with replacement together, so the interval reflects
    item-to-item variation in the *difference*, not in each run separately.
    """
    if len(per_item_a) != len(per_item_b):
        raise ValueError("paired bootstrap needs the same items in both runs")
    n = len(per_item_a)
    if n == 0:
        return {"delta": 0.0, "low": 0.0, "high": 0.0, "n": 0}
    point = statistic(per_item_b) - statistic(per_item_a)
    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(iterations):
        picks = [rng.randrange(n) for _ in range(n)]
        sample_a = [per_item_a[i] for i in picks]
        sample_b = [per_item_b[i] for i in picks]
        deltas.append(statistic(sample_b) - statistic(sample_a))
    deltas.sort()
    low = deltas[int(0.025 * iterations)]
    high = deltas[min(iterations - 1, int(0.975 * iterations))]
    share_positive = sum(1 for d in deltas if d > 0) / iterations
    return {"delta": point, "low": low, "high": high, "n": n, "share_positive": share_positive}


def pooled_f1(rows: Sequence[dict[str, float]], prefix: str = "") -> float:
    tp = sum(r.get(prefix + "tp", 0) for r in rows)
    fp = sum(r.get(prefix + "fp", 0) for r in rows)
    fn = sum(r.get(prefix + "fn", 0) for r in rows)
    return f1(tp, fp, fn)


def f1(tp: float, fp: float, fn: float) -> float:
    denominator = 2 * tp + fp + fn
    return 2 * tp / denominator if denominator else 0.0


def precision(tp: float, fp: float) -> float:
    return tp / (tp + fp) if tp + fp else 0.0


def recall(tp: float, fn: float) -> float:
    return tp / (tp + fn) if tp + fn else 0.0


def weighted_kappa(pairs: Sequence[tuple[int, int]], levels: int) -> float | None:
    """Linear-weighted Cohen's kappa on ordinal codes 0..levels-1."""
    if len(pairs) < 2:
        return None
    n = len(pairs)
    observed = [[0.0] * levels for _ in range(levels)]
    for a, b in pairs:
        observed[a][b] += 1
    row = [sum(observed[i][j] for j in range(levels)) for i in range(levels)]
    col = [sum(observed[i][j] for i in range(levels)) for j in range(levels)]
    num = 0.0
    den = 0.0
    for i in range(levels):
        for j in range(levels):
            weight = abs(i - j) / (levels - 1)
            num += weight * observed[i][j]
            den += weight * row[i] * col[j] / n
    if den == 0:
        return None
    return 1 - num / den


def krippendorff_alpha(
    units: Sequence[Sequence[Any]], metric: str = "nominal", levels: Sequence[Any] | None = None
) -> float | None:
    """Krippendorff's alpha over units, each a list of coder values (>= 2)."""
    usable = [list(values) for values in units if len(values) >= 2]
    if not usable:
        return None
    if metric == "ordinal":
        order = {value: index for index, value in enumerate(levels or [])}

        def delta(a: Any, b: Any) -> float:
            return float((order[a] - order[b]) ** 2)

    else:

        def delta(a: Any, b: Any) -> float:
            return 0.0 if a == b else 1.0

    total = Counter()
    for values in usable:
        total.update(values)
    n = sum(total.values())
    observed = 0.0
    for values in usable:
        m = len(values)
        for i in range(m):
            for j in range(m):
                if i != j:
                    observed += delta(values[i], values[j]) / (m - 1)
    observed /= n
    expected = 0.0
    keys = list(total)
    for a in keys:
        for b in keys:
            if a != b:
                expected += total[a] * total[b] * delta(a, b)
    expected /= n * (n - 1)
    if expected == 0:
        return None
    return 1 - observed / expected


def auroc(scores: Sequence[float], labels: Sequence[bool]) -> float | None:
    """Area under the ROC curve by rank statistic; None without both classes."""
    positives = [s for s, l in zip(scores, labels) if l]
    negatives = [s for s, l in zip(scores, labels) if not l]
    if not positives or not negatives:
        return None
    wins = 0.0
    for p in positives:
        for q in negatives:
            wins += 1.0 if p > q else 0.5 if p == q else 0.0
    return wins / (len(positives) * len(negatives))


def mean(values: Sequence[float]) -> float | None:
    values = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return sum(values) / len(values) if values else None
