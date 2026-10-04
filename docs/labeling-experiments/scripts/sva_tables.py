"""Tables for part 1 from sva_decompose.json."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

from sva_common import OUT

R = json.loads((OUT / "sva_decompose.json").read_text())


def f1(c):
    if not c:
        return None
    d = 2 * c.get("tp", 0) + c.get("fp", 0) + c.get("fn", 0)
    return 2 * c.get("tp", 0) / d if d else None


def fmt(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


def group_label(lab):
    if lab in ("claim", "product"):
        return lab
    return None


tax = json.loads((OUT.parent.parent / "taxonomy.json").read_text())
AXIS = {l["label_id"]: l["axis"] for l in tax["labels"]}


def axis_of(lab):
    return AXIS.get(lab, lab)


def merge(d, keys):
    c = Counter()
    for k in keys:
        c.update(d.get(k, {}))
    return c


groups = ["topic", "frame", "evidence", "claim", "product"]
labels_by_group = defaultdict(list)
all_labels = set(R["gold_volume"]) | set(R["ds_self"]) | set(R["ann_pairs"]["cross"])
for lab in all_labels:
    labels_by_group[axis_of(lab)].append(lab)

# per-atom systematic / stochastic miss
atom_rows = R["atom_p"]


def miss_split(rows):
    sys_ = sto = 0.0
    for r in rows:
        n, k = r["n"], r["k"]
        p = k / n
        stoch = k * (n - k) / (n * (n - 1)) if n > 1 else 0
        sto += stoch
        sys_ += (1 - p) - stoch
    return sys_ / len(rows) if rows else None, sto / len(rows) if rows else None


print("## T1 axis summary")
print("| group | required | ann O-O | ann S-S | ann cross | DS self | DS vs ann | DS gold P | DS gold R | DS gold F1 | miss systematic | miss stochastic |")
for g in groups:
    labs = labels_by_group[g]
    oo = f1(merge(R["ann_pairs"]["same_O"], labs))
    ss = f1(merge(R["ann_pairs"]["same_S"], labs))
    cr = f1(merge(R["ann_pairs"]["cross"], labs))
    se = f1(merge(R["ds_self"], labs))
    va = f1(merge(R["ds_vs_ann"], labs))
    dg = merge(R["ds_gold"], labs)
    if g in ("claim", "product"):
        P = dg["tp"] / (dg["tp"] + dg["fp"]); Rr = dg["tp"] / dg["required"] if dg["required"] else 0
    else:
        P = dg["tp"] / (dg["tp"] + dg["fp"]); Rr = dg["found"] / dg["required"]
    F = 2 * P * Rr / (P + Rr)
    req = sum(R["gold_volume"].get(l, {}).get("required", 0) for l in labs)
    rows = [r for r in atom_rows if axis_of(r["label"]) == g]
    sy, st = miss_split(rows)
    print(f"| {g} | {req} | {fmt(oo)} | {fmt(ss)} | {fmt(cr)} | {fmt(se)} | {fmt(va)} | {fmt(P)} | {fmt(Rr)} | {fmt(F)} | {fmt(sy)} | {fmt(st)} |")

print("\n## T1b support pattern of required gold and DS match rate by pattern")
pat_order = ["4of4", "3of4", "OO", "SS", "OS"]
print("| group | " + " | ".join(f"{p} n (DS match)" for p in pat_order) + " |")
for g in groups:
    cells = []
    for p in pat_order:
        rows = [r for r in atom_rows if axis_of(r["label"]) == g and r["pattern"] == p]
        if rows:
            m = sum(r["k"] / r["n"] for r in rows) / len(rows)
            cells.append(f"{len(rows)} ({m:.2f})")
        else:
            cells.append("-")
    print(f"| {g} | " + " | ".join(cells) + " |")

print("\n## T2 miss classes (share of required gold x samples)")
for g, c in R["miss_classes"].items():
    tot = sum(c.values())
    print(g, {k: round(v / tot, 3) for k, v in sorted(c.items(), key=lambda kv: -kv[1])})
print("\nby pattern (detections pooled / claim):")
agg = defaultdict(Counter)
for key, c in R["miss_by_pattern"].items():
    grp, pat = key.split("|")
    kind = "claim" if grp == "claim" else ("product" if grp == "product" else "detection")
    agg[(kind, pat)].update(c)
for (kind, pat), c in sorted(agg.items()):
    tot = sum(c.values())
    print(kind, pat, round(tot), {k: round(v / tot, 2) for k, v in sorted(c.items(), key=lambda kv: -kv[1])})

# per label table
print("\n## T3 per label")
rows_out = []
for g in groups:
    for lab in labels_by_group[g]:
        vol = R["gold_volume"].get(lab, {})
        req = vol.get("required", 0)
        cr = f1(R["ann_pairs"]["cross"].get(lab))
        oo = f1(R["ann_pairs"]["same_O"].get(lab))
        ss = f1(R["ann_pairs"]["same_S"].get(lab))
        se = f1(R["ds_self"].get(lab))
        va = f1(R["ds_vs_ann"].get(lab))
        dg = R["ds_gold"].get(lab, {})
        if g in ("claim", "product"):
            rec = dg.get("tp", 0) / dg["required"] if dg.get("required") else None
        else:
            rec = dg.get("found", 0) / dg["required"] if dg.get("required") else None
        prec = dg.get("tp", 0) / (dg.get("tp", 0) + dg.get("fp", 0)) if dg.get("tp", 0) + dg.get("fp", 0) else None
        rows = [r for r in atom_rows if r["label"] == lab]
        sy, st = miss_split(rows)
        fam_share = (vol.get("OO", 0)) / req if req else None
        ann_tot = sum(R["ann_pairs"]["cross"].get(lab, {}).values())
        rows_out.append(dict(group=g, label=lab, req=req, p44=vol.get("4of4", 0), oo_only=vol.get("OO", 0),
                             cross=cr, oo=oo, ss=ss, self=se, vs_ann=va, rec=rec, prec=prec, sys=sy, sto=st,
                             ann_tot=ann_tot))
(OUT / "sva_labels.json").write_text(json.dumps(rows_out, indent=1))
rows_out.sort(key=lambda r: -r["req"])
print("| label | req | 4/4 | OO-only | ann cross | ann OO | ann SS | DS self | DS vs ann | DS R | DS P | miss sys | miss sto |")
for r in rows_out:
    if r["req"] < 8 and len(sys.argv) < 2:
        continue
    print(f"| {r['label'].replace('topic:','t:').replace('cross_cutting:','x:')} | {r['req']} | {r['p44']} | {r['oo_only']} | {fmt(r['cross'])} | {fmt(r['oo'])} | {fmt(r['ss'])} | {fmt(r['self'])} | {fmt(r['vs_ann'])} | {fmt(r['rec'])} | {fmt(r['prec'])} | {fmt(r['sys'])} | {fmt(r['sto'])} |")

print("\n## T4 attributes: pairwise exact agreement on matched atoms")
print("| attribute | ann O-O | ann S-S | ann cross | DS self | DS vs ann | DS vs plurality (all) | DS vs unanimous gold | n unanimous | DS vs split gold (share) |")
vd = R["vote_detail"]
for attr in sorted(R["ann_attr"]["cross"]):
    def ag(d):
        c = d.get(attr)
        return c["agree"] / c["n"] if c and c["n"] else None
    rows = [v for v in vd if v["attr"] == attr]
    tot_w = sum(v["w"] for v in rows)
    plur = sum(v["w"] * (v["pred"] == v["plurality"]) for v in rows) / tot_w if tot_w else None
    un = [v for v in rows if v["unanimous"] and v["voters"] >= 3]
    unw = sum(v["w"] for v in un)
    una = sum(v["w"] * (v["pred"] == v["plurality"]) for v in un) / unw if unw else None
    sp = [v for v in rows if not v["unanimous"]]
    spw = sum(v["w"] for v in sp)
    spa = sum(v["w"] * v["share"] for v in sp) / spw if spw else None
    print(f"| {attr} | {fmt(ag(R['ann_attr']['same_O']))} | {fmt(ag(R['ann_attr']['same_S']))} | {fmt(ag(R['ann_attr']['cross']))} | {fmt(ag(R['ds_self_attr']))} | {fmt(ag(R['ds_vs_ann_attr']))} | {fmt(plur)} | {fmt(una)} | {round(unw)} | {fmt(spa)} |")

print("\n## T5 confusion on unanimous (>=3 voters) gold: gold -> DS (sample-weighted)")
for attr in ("claim:claim_type", "claim:expressed_certainty", "claim:discourse_role", "product:product_type", "detection:discourse_role", "detection:relevance", "product:mention_role", "claim:relevance"):
    rows = [v for v in vd if v["attr"] == attr and v["unanimous"] and v["voters"] >= 3 and v["pred"] != v["plurality"]]
    c = Counter()
    for v in rows:
        c[f"{v['plurality']}->{v['pred']}"] += v["w"]
    print(attr, [(k, round(n, 1)) for k, n in c.most_common(8)])
    totals = Counter()
    for v in vd:
        if v["attr"] == attr and v["unanimous"] and v["voters"] >= 3:
            totals[v["plurality"]] += v["w"]
    print("   gold totals", {k: round(n) for k, n in totals.most_common()})
