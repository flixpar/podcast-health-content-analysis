"""Score a run's window results against the gold and the annotators.

All metrics are computed per item first (so a paired bootstrap over items is
possible) and then pooled. Tiers decide credit: matching a ``required`` or
``acceptable`` gold atom is a true positive; matching an unadjudicated
``singleton`` is unscored (neither TP nor FP); matching ``rejected`` or
nothing is a false positive.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence

from analysis import topic_labeling as tl
from analysis.benchmark import stats
from analysis.benchmark.matching import (
    iou,
    CERTAINTY_ORDER,
    Atom,
    GoldAtom,
    WindowIndex,
    assign,
    explode,
    near_miss_class,
)
from analysis.benchmark.references import VOTED_ATTRIBUTES, pairwise_f1, _atoms_for

CREDIT_TIERS = ("required", "acceptable")
GROUPS = ("detection:topic", "detection:frame", "detection:evidence", "claim", "product")


def group_of(atom: Atom | GoldAtom) -> str:
    return f"detection:{atom.axis}" if atom.kind == "detection" else atom.kind


def score_item(
    item: dict[str, Any],
    result: dict[str, Any] | None,
    golds: Sequence[GoldAtom],
    aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Everything about one item: counts per group, attribute pairs, errors."""
    index = WindowIndex(item)
    preds = explode(result, index, aliases) if result else []
    scorable = [g for g in golds if g.tier != "rejected"]
    matched = assign(preds, scorable)
    pred_to_gold = {i: (j, s) for i, j, s in matched}
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for group in GROUPS:
        counts[group].update({key: 0 for key in ("tp", "fp", "fn", "unscored", "required", "gold", "pred")})
    per_label: dict[str, Counter[str]] = defaultdict(Counter)
    attribute_pairs: list[dict[str, Any]] = []
    calibration: list[tuple[float, bool]] = []
    errors: list[dict[str, Any]] = []
    matched_gold: set[int] = set()
    for i, pred in enumerate(preds):
        group = group_of(pred)
        if i in pred_to_gold:
            j, score = pred_to_gold[i]
            gold = scorable[j]
            matched_gold.add(j)
            if gold.tier in CREDIT_TIERS:
                counts[group]["tp"] += 1
                counts[group]["soft_tp"] += 1
                if pred.kind == "detection":
                    per_label[pred.label]["tp"] += 1
                calibration.append((pred.confidence, True))
            else:
                counts[group]["unscored"] += 1
                counts[group]["soft_tp"] += 1
            if pred.kind == "detection":
                counts[group]["span_iou_sum"] += iou((pred.start, pred.end), gold.tight)
            for attribute in VOTED_ATTRIBUTES[pred.kind]:
                value = pred.product_name if attribute == "product_name" else pred.attributes.get(attribute)
                if attribute == "product_name":
                    exact = pred.product_key in gold.product_keys
                    share = 1.0 if exact else 0.0
                    plurality = gold.product_names[0] if gold.product_names else None
                else:
                    plurality = gold.plurality(attribute)
                    if value is None or plurality is None:
                        continue
                    exact = str(value) == str(plurality)
                    share = gold.vote_share(attribute, str(value))
                attribute_pairs.append(
                    {
                        "kind": pred.kind,
                        "attribute": attribute,
                        "predicted": value,
                        "plurality": plurality,
                        "exact": exact,
                        "vote_share": share,
                        "tier": gold.tier,
                    }
                )
        else:
            counts[group]["fp"] += 1
            if pred.kind == "detection":
                per_label[pred.label]["fp"] += 1
            calibration.append((pred.confidence, False))
            errors.append(
                {
                    "type": "false_positive",
                    "group": group,
                    "class": near_miss_class(pred, scorable),
                    "label": pred.label,
                    "span": [pred.start, pred.end],
                    "text": pred.claim_text or pred.product_name or pred.quote,
                }
            )
    for j, gold in enumerate(scorable):
        group = group_of(gold)
        counts[group]["gold"] += 1
        if gold.tier == "required":
            counts[group]["required"] += 1
            if gold.kind == "detection":
                per_label[gold.label]["required"] += 1
        counts[group]["soft_gold"] += gold.support
        if j in matched_gold:
            counts[group]["soft_matched"] += gold.support
            if gold.kind == "detection" and gold.tier == "required":
                per_label[gold.label]["found"] += 1
            continue
        if gold.tier == "required":
            counts[group]["fn"] += 1
            if gold.kind == "detection":
                per_label[gold.label]["fn"] += 1
            errors.append(
                {
                    "type": "miss",
                    "group": group,
                    "class": _miss_class(gold, preds),
                    "label": gold.label,
                    "span": list(gold.tight),
                    "text": (gold.claim_texts or gold.product_names or gold.quotes or [""])[0],
                }
            )
    for group in GROUPS:
        counts[group]["pred"] = sum(1 for p in preds if group_of(p) == group)
    return {
        "item_id": item["item_id"],
        "stratum": item.get("stratum"),
        "split": item.get("split"),
        "labeled": result is not None,
        "counts": {group: dict(c) for group, c in counts.items()},
        "per_label": {label: dict(c) for label, c in per_label.items()},
        "attribute_pairs": attribute_pairs,
        "calibration": calibration,
        "errors": errors,
        "pred_atoms": len(preds),
        "gold_atoms": len(scorable),
    }


def _miss_class(gold: GoldAtom, preds: Sequence[Atom]) -> str:
    span = gold.envelope
    same_kind = [p for p in preds if p.kind == gold.kind and not (p.end < span[0] or p.start > span[1])]
    if gold.kind == "detection":
        if any(p.axis == gold.axis and p.label == gold.label for p in same_kind):
            return "span_only"
        if any(p.axis == gold.axis for p in same_kind):
            return "same_axis_wrong_label"
        if same_kind:
            return "cross_axis"
        return "nothing_predicted"
    return "different_" + gold.kind if same_kind else "nothing_predicted"


# --------------------------------------------------------------------------
# Pooling
# --------------------------------------------------------------------------


def _pool(rows: Sequence[dict[str, Any]], group: str) -> dict[str, Any]:
    tp = sum(r["counts"].get(group, {}).get("tp", 0) for r in rows)
    fp = sum(r["counts"].get(group, {}).get("fp", 0) for r in rows)
    fn = sum(r["counts"].get(group, {}).get("fn", 0) for r in rows)
    unscored = sum(r["counts"].get(group, {}).get("unscored", 0) for r in rows)
    required = sum(r["counts"].get(group, {}).get("required", 0) for r in rows)
    gold = sum(r["counts"].get(group, {}).get("gold", 0) for r in rows)
    pred = sum(r["counts"].get(group, {}).get("pred", 0) for r in rows)
    soft_gold = sum(r["counts"].get(group, {}).get("soft_gold", 0.0) for r in rows)
    soft_matched = sum(r["counts"].get(group, {}).get("soft_matched", 0.0) for r in rows)
    iou_sum = sum(r["counts"].get(group, {}).get("span_iou_sum", 0.0) for r in rows)
    return {
        "pred": pred,
        "gold": gold,
        "required": required,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "unscored": unscored,
        "precision": round(stats.precision(tp, fp), 4) if tp + fp else None,
        "recall_strict": round(stats.recall(tp, fn), 4) if tp + fn else None,
        "recall_soft": round(soft_matched / soft_gold, 4) if soft_gold else None,
        "f1_strict": round(stats.f1(tp, fp, fn), 4) if tp + fp + fn else None,
        "f1_soft": round(_soft_f1(tp, fp, soft_matched, soft_gold), 4) if soft_gold else None,
        "yield_ratio": round(pred / gold, 3) if gold else None,
        "mean_span_iou": round(iou_sum / tp, 3) if tp and group.startswith("detection") else None,
    }


def _soft_f1(tp: int, fp: int, soft_matched: float, soft_gold: float) -> float:
    precision = stats.precision(tp, fp)
    recall = soft_matched / soft_gold if soft_gold else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _attribute_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    pairs = [p for r in rows for p in r["attribute_pairs"]]
    out: dict[str, Any] = {}
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        by_key[f"{pair['kind']}:{pair['attribute']}"].append(pair)
    for key, group in sorted(by_key.items()):
        entry: dict[str, Any] = {
            "n": len(group),
            "exact": round(sum(1 for p in group if p["exact"]) / len(group), 4),
            "vote_share": round(sum(p["vote_share"] for p in group) / len(group), 4),
        }
        if key.endswith("expressed_certainty"):
            ordinal = [
                (CERTAINTY_ORDER[str(p["predicted"])], CERTAINTY_ORDER[str(p["plurality"])])
                for p in group
                if str(p["predicted"]) in CERTAINTY_ORDER and str(p["plurality"]) in CERTAINTY_ORDER
            ]
            kappa = stats.weighted_kappa(ordinal, len(CERTAINTY_ORDER))
            entry["weighted_kappa"] = None if kappa is None else round(kappa, 4)
        confusion: Counter[str] = Counter(
            f"{p['plurality']}->{p['predicted']}" for p in group if not p["exact"]
        )
        entry["confusions"] = dict(confusion.most_common(8))
        out[key] = entry
    return out


def _error_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    for row in rows:
        for error in row["errors"]:
            counter[f"{error['type']}:{error['group']}:{error['class']}"] += 1
    return dict(sorted(counter.items()))


def _label_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for label, counts in row["per_label"].items():
            totals[label].update(counts)
    out = {}
    for label, c in sorted(totals.items()):
        out[label] = {
            "required": c["required"],
            "found": c["found"],
            "tp": c["tp"],
            "fp": c["fp"],
            "recall": round(c["found"] / c["required"], 3) if c["required"] else None,
            "precision": round(stats.precision(c["tp"], c["fp"]), 3) if c["tp"] + c["fp"] else None,
        }
    return out


def _null_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    null_rows = [r for r in rows if r["stratum"] == "null" and r["labeled"]]
    if not null_rows:
        return {"windows": 0}
    atoms = [r["pred_atoms"] for r in null_rows]
    return {
        "windows": len(null_rows),
        "atoms_per_window": round(sum(atoms) / len(atoms), 3),
        "share_with_output": round(sum(1 for a in atoms if a > 0) / len(atoms), 3),
    }


def _calibration_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    scores = [s for r in rows for s, _ in r["calibration"]]
    labels = [l for r in rows for _, l in r["calibration"]]
    tp_conf = [s for s, l in zip(scores, labels) if l]
    fp_conf = [s for s, l in zip(scores, labels) if not l]
    area = stats.auroc(scores, labels)
    return {
        "n": len(scores),
        "auroc": None if area is None else round(area, 4),
        "mean_confidence_tp": round(stats.mean(tp_conf), 3) if tp_conf else None,
        "mean_confidence_fp": round(stats.mean(fp_conf), 3) if fp_conf else None,
    }


def summarize(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Pooled metrics for a set of per-item rows."""
    labeled = [r for r in rows if r["labeled"]]
    return {
        "items": len(rows),
        "labeled": len(labeled),
        "groups": {group: _pool(labeled, group) for group in GROUPS},
        "attributes": _attribute_summary(labeled),
        "errors": _error_summary(labeled),
        "null": _null_summary(labeled),
        "calibration": _calibration_summary(labeled),
    }


def breakdown(rows: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key))].append(row)
    return {
        name: {
            "items": len(group_rows),
            "groups": {group: _pool([r for r in group_rows if r["labeled"]], group) for group in GROUPS},
        }
        for name, group_rows in sorted(groups.items())
    }


def score_run(
    items: Sequence[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    gold: dict[str, list[GoldAtom]],
    aliases: dict[str, str] | None = None,
    hide_test: bool = True,
) -> dict[str, Any]:
    """Score one repeat of a run over the items that have gold."""
    rows = []
    for item in items:
        if item["item_id"] not in gold:
            continue
        rows.append(score_item(item, results.get(item["window_id"]), gold[item["item_id"]], aliases))
    headline_rows = [r for r in rows if r["stratum"] not in ("rare_label", "synthetic", "contrast")]
    report = {
        "items_scored": len(rows),
        "headline": summarize(headline_rows),
        "all": summarize(rows),
        "by_split": {
            split: summarize([r for r in headline_rows if r["split"] == split]) for split in ("dev", "test")
        },
        "by_stratum": breakdown(rows, "stratum"),
        "per_label": _label_summary([r for r in rows if r["labeled"]]),
        "per_item": [
            {
                "item_id": r["item_id"],
                "stratum": r["stratum"],
                "split": r["split"],
                "labeled": r["labeled"],
                "counts": r["counts"],
                "errors": r["errors"] if (r["split"] != "test" or not hide_test) else "hidden",
            }
            for r in rows
        ],
    }
    return report


def agreement_with_annotators(
    items: Sequence[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    references: dict[str, dict[str, dict[str, Any]]],
    aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """The candidate as a fourth annotator: pairwise F1 against each reference."""
    totals: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for item in items:
        refs = references.get(item["item_id"])
        result = results.get(item["window_id"])
        if not refs or result is None:
            continue
        index = WindowIndex(item)
        candidate = explode(result, index, aliases)
        for annotator_id, ref in refs.items():
            for group, counts in pairwise_f1(_atoms_for(ref, index), candidate).items():
                for field in ("tp", "fp", "fn"):
                    totals[annotator_id][group][field] += counts[field]
    return {
        annotator_id: {
            group: {**c, "f1": round(stats.f1(c["tp"], c["fp"], c["fn"]), 4)}
            for group, c in sorted(groups.items())
        }
        for annotator_id, groups in sorted(totals.items())
    }


def repeat_agreement(
    items: Sequence[dict[str, Any]],
    repeats: Sequence[dict[str, dict[str, Any]]],
    aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Self-agreement between repeats of the same configuration: the noise floor."""
    if len(repeats) < 2:
        return {}
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    pairs = 0
    for item in items:
        index = WindowIndex(item)
        atoms = [
            explode(r[item["window_id"]], index, aliases) for r in repeats if item["window_id"] in r
        ]
        for i in range(len(atoms)):
            for j in range(i + 1, len(atoms)):
                pairs += 1
                for group, counts in pairwise_f1(atoms[i], atoms[j]).items():
                    for field in ("tp", "fp", "fn"):
                        totals[group][field] += counts[field]
    return {
        "pairs": pairs,
        **{
            group: {**c, "f1": round(stats.f1(c["tp"], c["fp"], c["fn"]), 4)}
            for group, c in sorted(totals.items())
        },
    }
