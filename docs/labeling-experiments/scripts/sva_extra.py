"""Part 1 extras: labeling density, co-label pairs, false-positive recurrence, value distributions."""

from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict

from sva_common import CORPUS, OUT, gold, items, pool_items, pred_atoms, ref_atoms, samples_for, group_of, label_key
from analysis.benchmark import scoring
from analysis.benchmark.matching import assign, overlaps, overlap_coefficient, near_miss_class
from analysis.benchmark.references import _single_gold

DEV = pool_items("dev", CORPUS)
S70 = set(pool_items("s70", CORPUS))


def all_samples(iid):
    return samples_for(iid, "dev") + (samples_for(iid, "s70") if iid in S70 else [])


# 1. density: atoms per item per group, topic labels per detection, distinct topics per item
dens = defaultdict(Counter)
for iid in DEV:
    for a, atoms in ref_atoms(iid).items():
        for at in atoms:
            dens[a][group_of(at)] += 1
        dens[a]["distinct_topics"] += len({at.label for at in atoms if at.kind == "detection" and at.axis == "topic"})
    ss = all_samples(iid)
    for s in ss:
        atoms = pred_atoms(s, iid)
        for at in atoms:
            dens["deepseek"][group_of(at)] += 1 / len(ss)
        dens["deepseek"]["distinct_topics"] += len({at.label for at in atoms if at.kind == "detection" and at.axis == "topic"}) / len(ss)
print("## density per item (dev corpus items)", len(DEV))
for who, c in dens.items():
    print(who, {k: round(v / len(DEV), 2) for k, v in sorted(c.items())})

# labels per topic detection
from sva_common import references
lpd = defaultdict(list)
for iid in DEV:
    for a, ref in references()[iid].items():
        for d in ref["result"].get("detections", []):
            if d.get("axis") == "topic" or all(l.startswith("topic:") for l in d["label_ids"]):
                lpd[a].append(len(d["label_ids"]))
    for s in all_samples(iid):
        for d in s.get("detections", []):
            if all(l.startswith("topic:") for l in d["label_ids"]):
                lpd["deepseek"].append(len(d["label_ids"]))
print("topic labels per topic detection:", {a: round(sum(v) / len(v), 2) for a, v in lpd.items()})

# 2. colabel_missing / substitution pairs: required gold label missed, DS label on the span
pairs_col = Counter()
pairs_sub = Counter()
missed_by_label_class = defaultdict(Counter)
for iid in DEV:
    golds = gold()[iid]
    scorable = [g for g in golds if g.tier != "rejected"]
    ss = all_samples(iid)
    for s in ss:
        atoms = pred_atoms(s, iid)
        mg = {j for _, j, _ in assign(atoms, scorable)}
        for j, g in enumerate(scorable):
            if g.tier != "required" or j in mg or g.kind != "detection":
                continue
            strong = [p for p in atoms if p.kind == "detection" and p.axis == g.axis and p.label != g.label
                      and overlaps((p.start, p.end), g.envelope) and overlap_coefficient((p.start, p.end), g.tight) >= 0.5]
            if any(p.label == g.label for p in atoms if p.kind == "detection" and overlaps((p.start, p.end), g.envelope)):
                continue
            cogold = {h.label for h in scorable if h.kind == "detection" and h.axis == g.axis and h.label != g.label
                      and h.tier in ("required", "acceptable") and overlap_coefficient(h.tight, g.tight) >= 0.5}
            for p in strong:
                if p.label in cogold:
                    pairs_col[(g.label, p.label)] += 1 / len(ss)
                else:
                    pairs_sub[(g.label, p.label)] += 1 / len(ss)
print("\n## co-label missing: (gold label missed, DS label present that is also gold)")
for (a, b), n in pairs_col.most_common(25):
    print(f"  {a} | {b} | {n:.1f}")
print("\n## substitution: (gold label missed, DS label not in gold there)")
for (a, b), n in pairs_sub.most_common(15):
    print(f"  {a} | {b} | {n:.1f}")

# 3. false positives: recurrence across samples and class
fp_rows = []
for iid in DEV:
    item = items()[iid]
    golds = gold()[iid]
    scorable = [g for g in golds if g.tier != "rejected"]
    rejected = [g for g in golds if g.tier == "rejected"]
    ss = all_samples(iid)
    all_atoms = [pred_atoms(s, iid) for s in ss]
    for si, atoms in enumerate(all_atoms):
        matched = assign(atoms, scorable)
        m = {i for i, _, _ in matched}
        for i, p in enumerate(atoms):
            if i in m:
                continue
            # recurrence: other samples with a matching atom
            me = [_single_gold(p, 0)]
            rec = sum(1 for sj, other in enumerate(all_atoms) if sj != si and assign(other, me))
            rej = bool(assign([p], rejected)) if rejected else False
            fp_rows.append({
                "item_id": iid, "group": group_of(p), "label": label_key(p), "cls": near_miss_class(p, scorable),
                "recur": rec / (len(ss) - 1) if len(ss) > 1 else None, "w": 1 / len(ss), "rejected_match": rej,
            })
print("\n## false positives (sample-weighted per item) by group and class, and recurrence")
agg = defaultdict(Counter)
recw = defaultdict(lambda: [0.0, 0.0])
for r in fp_rows:
    agg[r["group"]][r["cls"]] += r["w"]
    if r["recur"] is not None:
        recw[r["group"]][0] += r["w"] * r["recur"]
        recw[r["group"]][1] += r["w"]
for g, c in agg.items():
    tot = sum(c.values())
    print(g, round(tot, 1), {k: round(v / tot, 2) for k, v in c.most_common()}, "mean recurrence", round(recw[g][0] / recw[g][1], 2))
# recurrence distribution
hi = defaultdict(Counter)
for r in fp_rows:
    if r["recur"] is None:
        continue
    b = "stable(>=0.5)" if r["recur"] >= 0.5 else ("rare(0)" if r["recur"] == 0 else "some")
    hi[r["group"]][b] += r["w"]
print({g: {k: round(v / sum(c.values()), 2) for k, v in c.items()} for g, c in hi.items()})
print("fp matching a rejected singleton:", round(sum(r["w"] for r in fp_rows if r["rejected_match"]), 1), "of", round(sum(r["w"] for r in fp_rows), 1))
fpl = Counter()
for r in fp_rows:
    fpl[r["label"]] += r["w"]
print("top FP labels", [(k, round(v, 1)) for k, v in fpl.most_common(12)])

# 4. value distributions: claim_type and product_type, DS vs annotators
dist = defaultdict(lambda: defaultdict(Counter))
for iid in DEV:
    for a, atoms in ref_atoms(iid).items():
        fam = "opus" if a.startswith("opus") else "sonnet"
        for at in atoms:
            if at.kind == "claim":
                dist["claim_type"][fam][at.attributes.get("claim_type")] += 1
            if at.kind == "product":
                dist["product_type"][fam][at.attributes.get("product_type")] += 1
    ss = all_samples(iid)
    for s in ss:
        for at in pred_atoms(s, iid):
            if at.kind == "claim":
                dist["claim_type"]["deepseek"][at.attributes.get("claim_type")] += 1 / len(ss)
            if at.kind == "product":
                dist["product_type"]["deepseek"][at.attributes.get("product_type")] += 1 / len(ss)
print("\n## value distributions (share)")
for attr, fams in dist.items():
    print(attr)
    for fam, c in fams.items():
        tot = sum(c.values())
        print("  ", fam, {k: round(v / tot, 2) for k, v in c.most_common()})
json.dump(fp_rows, open(OUT / "sva_fp_rows.json", "w"))
