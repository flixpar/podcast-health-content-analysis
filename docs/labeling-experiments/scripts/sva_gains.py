"""Upper-bound what-ifs on the dev corpus items, dev-high-chat-lenient repeats 0 and 1."""

from __future__ import annotations

import copy
from collections import Counter, defaultdict

from sva_common import CORPUS, gold, items, pool_items, pred_atoms, run, index, DEV_RUN
from analysis.benchmark import scoring
from analysis.benchmark.matching import assign, overlaps, overlap_coefficient, near_miss_class

DEV = pool_items("dev", CORPUS)
reps = run(DEV_RUN)["repeats"]


def f1(tp, fp, fn):
    return 2 * tp / (2 * tp + fp + fn)


tot = defaultdict(Counter)
for rep in reps:
    for iid in DEV:
        item = items()[iid]
        res = rep.get(item["window_id"])
        if res is None:
            continue
        golds = gold()[iid]
        scorable = [g for g in golds if g.tier != "rejected"]
        row = scoring.score_item(item, res, golds)
        for grp in ("detection:topic", "detection:frame", "detection:evidence", "claim", "product"):
            for f in ("tp", "fp", "fn"):
                tot[grp][f] += row["counts"][grp][f]
        preds = pred_atoms(res, iid)
        matched = assign(preds, scorable)
        mp = {i for i, _, _ in matched}
        mg = {j for _, j, _ in matched}
        for i, p in enumerate(preds):
            if i not in mp and p.kind == "detection":
                cls = near_miss_class(p, scorable)
                tot[f"detection:{p.axis}"]["fp_" + cls] += 1
        for j, g in enumerate(scorable):
            if g.tier != "required" or j in mg or g.kind != "detection":
                continue
            near = [p for p in preds if p.kind == "detection" and overlaps((p.start, p.end), g.envelope)]
            if any(p.axis == g.axis and p.label == g.label for p in near):
                tot[f"detection:{g.axis}"]["fn_span_only"] += 1
                continue
            strong = [p for p in near if p.axis == g.axis and overlap_coefficient((p.start, p.end), g.tight) >= 0.5]
            cogold = {h.label for h in scorable if h.kind == "detection" and h.axis == g.axis and h.label != g.label
                      and h.tier in ("required", "acceptable") and overlap_coefficient(h.tight, g.tight) >= 0.5}
            if any(p.label in cogold for p in strong):
                key = "fn_colabel_" + ("strong" if len(g.annotators) >= 3 else "weak")
                tot[f"detection:{g.axis}"][key] += 1
        # product-type oracle: DS product types replaced by the plurality of the overlapping gold product
        res2 = copy.deepcopy(res)
        idx = index(iid)
        gprod = [g for g in scorable if g.kind == "product"]
        for pm in res2.get("product_mentions", []):
            s, e = idx.span(pm["start_unit_id"], pm["end_unit_id"])
            best = max((g for g in gprod if overlaps((s, e), g.envelope)), key=lambda g: overlap_coefficient((s, e), g.tight), default=None)
            if best is not None and best.plurality("product_type"):
                pm["product_type"] = best.plurality("product_type")
        row2 = scoring.score_item(item, res2, golds)
        for f in ("tp", "fp", "fn"):
            tot["product_oracle_type"][f] += row2["counts"]["product"][f]

print("| group | F1 now | + span-only pairs resolved | + co-labels (3-4 annotators) | + all co-labels |")
for grp in ("detection:topic", "detection:frame", "detection:evidence"):
    c = tot[grp]
    base = f1(c["tp"], c["fp"], c["fn"])
    so = min(c["fn_span_only"], c["fp_span_only"])
    span = f1(c["tp"] + c["fn_span_only"], c["fp"] - c["fp_span_only"], c["fn"] - c["fn_span_only"])
    strong = f1(c["tp"] + c["fn_colabel_strong"], c["fp"], c["fn"] - c["fn_colabel_strong"])
    allc = f1(c["tp"] + c["fn_colabel_strong"] + c["fn_colabel_weak"], c["fp"], c["fn"] - c["fn_colabel_strong"] - c["fn_colabel_weak"])
    print(f"| {grp} | {base:.3f} | {span:.3f} | {strong:.3f} | {allc:.3f} |", dict(c))
c = tot["product"]; o = tot["product_oracle_type"]
print("product F1 now", round(f1(c["tp"], c["fp"], c["fn"]), 3), "with gold product_type", round(f1(o["tp"], o["fp"], o["fn"]), 3), dict(c), dict(o))
c = tot["claim"]
print("claim F1 now", round(f1(c["tp"], c["fp"], c["fn"]), 3), dict(c))
