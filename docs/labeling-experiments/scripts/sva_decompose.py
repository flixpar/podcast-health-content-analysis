"""Part 1: decompose disagreement per label / attribute into annotator ambiguity,
DeepSeek self-agreement and DeepSeek-vs-gold.

Pools: every dev corpus item (headline strata + rare_label) that the dev run
labeled; DeepSeek samples per item = dev-high-chat-lenient repeats (2) plus, for
the 70 s70 items, the three s70 runs (2 repeats each) -> up to 8 samples.
Per-item statistics over sample pairs are averaged per item before pooling so
an item with 8 samples does not count 28 times.
"""

from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict

from sva_common import (
    ANNOTATORS, CORPUS, OUT, gold, items, pool_items, pred_atoms, ref_atoms,
    samples_for, group_of, label_key,
)
from analysis.benchmark import scoring
from analysis.benchmark.matching import assign, overlaps, overlap_coefficient
from analysis.benchmark.references import _single_gold, VOTED_ATTRIBUTES

FAMILY = {"opus-r1": "O", "opus-r2": "O", "sonnet-r1": "S", "sonnet-r2": "S"}


def all_samples(item_id):
    return samples_for(item_id, "dev") + (samples_for(item_id, "s70") if item_id in S70 else [])


def pair_stats(a_atoms, b_atoms):
    """B against A: per label tp/fp/fn and attribute agreement on matched pairs."""
    per_label = defaultdict(Counter)
    attrs = defaultdict(Counter)
    a_gold = [_single_gold(atom, i) for i, atom in enumerate(a_atoms)]
    matched = assign(b_atoms, a_gold)
    mb = {i: j for i, j, _ in matched}
    ma = {j for _, j, _ in matched}
    for i, atom in enumerate(b_atoms):
        key = label_key(atom)
        if i in mb:
            per_label[key]["tp"] += 1
            other = a_atoms[mb[i]]
            for attribute in VOTED_ATTRIBUTES[atom.kind]:
                if attribute == "product_name":
                    va, vb = other.product_key, atom.product_key
                else:
                    va, vb = other.attributes.get(attribute), atom.attributes.get(attribute)
                if va is None or vb is None:
                    continue
                k = f"{atom.kind}:{attribute}"
                attrs[k]["n"] += 1
                attrs[k]["agree"] += int(str(va) == str(vb))
        else:
            per_label[key]["fp"] += 1
    for j, atom in enumerate(a_atoms):
        if j not in ma:
            per_label[label_key(atom)]["fn"] += 1
    return per_label, attrs


def add(dst, src, weight=1.0):
    for k, c in src.items():
        for f, v in c.items():
            dst[k][f] += v * weight


def f1(c):
    d = 2 * c["tp"] + c["fp"] + c["fn"]
    return round(2 * c["tp"] / d, 3) if d else None


def support_pattern(g):
    fam = Counter(FAMILY[a] for a in g.annotators)
    n = len(g.annotators)
    if n == 4:
        return "4of4"
    if n == 3:
        return "3of4"
    if n == 2:
        return {("O",): "OO", ("S",): "SS"}.get(tuple(sorted(set(fam))), "OS")
    return "1"


DEV = pool_items("dev", CORPUS)
S70 = set(pool_items("s70", CORPUS))

ann_pairs = {"same_O": defaultdict(Counter), "same_S": defaultdict(Counter), "cross": defaultdict(Counter)}
ann_attr = {"same_O": defaultdict(Counter), "same_S": defaultdict(Counter), "cross": defaultdict(Counter)}
ds_self = defaultdict(Counter)
ds_self_attr = defaultdict(Counter)
ds_vs_ann = defaultdict(Counter)
ds_vs_ann_attr = defaultdict(Counter)
ds_gold = defaultdict(Counter)  # per label: required/found/tp/fp (mean over samples)
gold_volume = defaultdict(Counter)  # per label: required by support pattern
atom_p = []  # per required gold atom: label, group, pattern, p (match rate over samples), n
attr_pairs = []  # score_item attribute pairs with gold vote detail
miss_classes = defaultdict(Counter)  # group -> class (sample-weighted)
miss_by_pattern = defaultdict(Counter)
n_samples = Counter()


def detail_miss(g, preds, scorable, matched_gold_ids):
    """Finer class for a required gold atom a sample did not match."""
    if g.kind != "detection":
        same = [p for p in preds if p.kind == g.kind and overlaps((p.start, p.end), g.envelope)]
        return "different_" + g.kind if same else "nothing_predicted"
    near = [p for p in preds if p.kind == "detection" and overlaps((p.start, p.end), g.envelope)]
    strong = [p for p in near if overlap_coefficient((p.start, p.end), g.tight) >= 0.5]
    same_axis = [p for p in strong if p.axis == g.axis]
    if any(p.label == g.label for p in near if p.axis == g.axis):
        return "span_only"
    if same_axis:
        # does the predicted other label also exist as credit gold on this span?
        cogold = {
            h.label for h in scorable
            if h.kind == "detection" and h.axis == g.axis and h.label != g.label
            and h.tier in ("required", "acceptable") and overlap_coefficient(h.tight, g.tight) >= 0.5
        }
        if any(p.label in cogold for p in same_axis):
            return "colabel_missing"  # DS used a neighbouring gold label, not this one as well
        return "substitution"
    if g.axis != "topic" and any(p.axis not in (g.axis, "topic") for p in strong):
        return "cross_axis"
    return "uncovered"


for iid in DEV:
    item = items()[iid]
    refs = ref_atoms(iid)
    # (a) annotator pairs
    for a, b in itertools.combinations(sorted(refs), 2):
        kind = "same_" + FAMILY[a] if FAMILY[a] == FAMILY[b] else "cross"
        pl, at = pair_stats(refs[a], refs[b])
        w = 1.0 if kind != "cross" else 0.25
        add(ann_pairs[kind], pl, w)
        add(ann_attr[kind], at, w)
    samples = all_samples(iid)
    patoms = [pred_atoms(s, iid) for s in samples]
    n_samples[len(samples)] += 1
    # (b) DS self
    pairs = list(itertools.combinations(range(len(patoms)), 2))
    for i, j in pairs:
        pl, at = pair_stats(patoms[i], patoms[j])
        add(ds_self, pl, 1 / len(pairs))
        add(ds_self_attr, at, 1 / len(pairs))
    # DS vs each annotator (like for like with (a) cross)
    for s in patoms:
        for a in refs:
            pl, at = pair_stats(refs[a], s)
            w = 1 / (len(patoms) * len(refs))
            add(ds_vs_ann, pl, w)
            add(ds_vs_ann_attr, at, w)
    # (c) DS vs gold
    golds = gold()[iid]
    scorable = [g for g in golds if g.tier != "rejected"]
    for g in scorable:
        if g.tier == "required":
            gold_volume[label_key(g)][support_pattern(g)] += 1
            gold_volume[label_key(g)]["required"] += 1
    hits = Counter()
    for s, atoms in zip(samples, patoms):
        row = scoring.score_item(item, s, golds)
        w = 1 / len(samples)
        for lab, c in row["per_label"].items():
            for f in ("tp", "fp", "fn", "found", "required"):
                ds_gold[lab][f] += c.get(f, 0) * w
        for grp in ("claim", "product"):
            c = row["counts"][grp]
            for f in ("tp", "fp", "fn", "required"):
                ds_gold[grp][f] += c.get(f, 0) * w
        matched = assign(atoms, scorable)
        mg = {j for _, j, _ in matched}
        for j, g in enumerate(scorable):
            if g.tier != "required":
                continue
            if j in mg:
                hits[j] += 1
                cls = "matched"
            else:
                cls = detail_miss(g, atoms, scorable, mg)
            miss_classes[group_of(g)][cls] += w
            miss_by_pattern[(group_of(g), support_pattern(g))][cls] += w
        for pair in row["attribute_pairs"]:
            attr_pairs.append({**pair, "item_id": iid})
    for j, g in enumerate(scorable):
        if g.tier == "required":
            atom_p.append({
                "item_id": iid, "gold_id": g.gold_id, "group": group_of(g), "label": label_key(g),
                "pattern": support_pattern(g), "k": hits[j], "n": len(samples),
            })

# unanimity of gold votes for attribute pairs: redo with votes
vote_detail = []
for iid in DEV:
    item = items()[iid]
    golds = gold()[iid]
    scorable = [g for g in golds if g.tier != "rejected"]
    for s in all_samples(iid):
        atoms = pred_atoms(s, iid)
        for i, j, _ in assign(atoms, scorable):
            p, g = atoms[i], scorable[j]
            for attribute in VOTED_ATTRIBUTES[p.kind]:
                if attribute == "product_name":
                    continue
                votes = g.votes.get(attribute) or {}
                total = sum(votes.values())
                val = p.attributes.get(attribute)
                if total < 2 or val is None:
                    continue
                top = max(sorted(votes), key=lambda v: votes[v])
                vote_detail.append({
                    "item_id": iid, "attr": f"{p.kind}:{attribute}", "pred": str(val), "plurality": top,
                    "unanimous": len(votes) == 1, "voters": total, "share": votes.get(str(val), 0) / total,
                    "w": 1 / len(all_samples(iid)), "label": label_key(p),
                })

result = {
    "items": len(DEV), "s70_items": len(S70), "samples_hist": dict(n_samples),
    "ann_pairs": {k: {lab: dict(c) for lab, c in v.items()} for k, v in ann_pairs.items()},
    "ann_attr": {k: {lab: dict(c) for lab, c in v.items()} for k, v in ann_attr.items()},
    "ds_self": {lab: dict(c) for lab, c in ds_self.items()},
    "ds_self_attr": {lab: dict(c) for lab, c in ds_self_attr.items()},
    "ds_vs_ann": {lab: dict(c) for lab, c in ds_vs_ann.items()},
    "ds_vs_ann_attr": {lab: dict(c) for lab, c in ds_vs_ann_attr.items()},
    "ds_gold": {lab: dict(c) for lab, c in ds_gold.items()},
    "gold_volume": {lab: dict(c) for lab, c in gold_volume.items()},
    "miss_classes": {k: dict(v) for k, v in miss_classes.items()},
    "miss_by_pattern": {f"{k[0]}|{k[1]}": dict(v) for k, v in miss_by_pattern.items()},
    "atom_p": atom_p,
    "vote_detail": vote_detail,
}
(OUT / "sva_decompose.json").write_text(json.dumps(result))
print("done", len(DEV), dict(n_samples), len(atom_p), len(vote_detail))
