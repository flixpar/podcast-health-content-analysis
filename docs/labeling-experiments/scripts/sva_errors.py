"""Part 2: stratified sample of DeepSeek errors (dev-high-chat-lenient repeat_0) with dossiers."""

from __future__ import annotations

import json
import random
from collections import defaultdict

from sva_common import CORPUS, OUT, gold, items, pool_items, pred_atoms, ref_atoms, run, index, taxonomy, group_of, DEV_RUN
from analysis.benchmark import scoring
from analysis.benchmark.matching import assign, overlaps, overlap_coefficient, near_miss_class

QUOTAS = {  # (group, type) -> n
    ("detection:topic", "miss"): 8, ("detection:topic", "false_positive"): 6,
    ("detection:frame", "miss"): 6, ("detection:frame", "false_positive"): 4,
    ("detection:evidence", "miss"): 6, ("detection:evidence", "false_positive"): 4,
    ("claim", "miss"): 10, ("claim", "false_positive"): 6,
    ("product", "miss"): 6, ("product", "false_positive"): 4,
}
DEFS = {l["label_id"]: l for l in taxonomy()["labels"]}
atom_p = {(r["item_id"], r["gold_id"]): (r["k"], r["n"], r["pattern"]) for r in json.loads((OUT / "sva_decompose.json").read_text())["atom_p"]}
fp_rows = json.loads((OUT / "sva_fp_rows.json").read_text())

rep0 = run(DEV_RUN)["repeats"][0]
DEVI = pool_items("dev", CORPUS)
candidates = defaultdict(list)
for iid in DEVI:
    item = items()[iid]
    res = rep0.get(item["window_id"])
    if res is None:
        continue
    golds = gold()[iid]
    scorable = [g for g in golds if g.tier != "rejected"]
    preds = pred_atoms(res, iid)
    matched = assign(preds, scorable)
    mp = {i for i, _, _ in matched}
    mg = {j for _, j, _ in matched}
    for j, g in enumerate(scorable):
        if g.tier == "required" and j not in mg:
            candidates[(group_of(g), "miss")].append((iid, "miss", j))
    for i, p in enumerate(preds):
        if i not in mp:
            candidates[(group_of(p), "false_positive")].append((iid, "fp", i))

rng = random.Random(20260913)
chosen = []
for key, n in QUOTAS.items():
    pool = candidates[key]
    # at most 2 per item to spread across windows
    rng.shuffle(pool)
    per_item = defaultdict(int)
    picked = []
    for c in pool:
        if per_item[c[0]] >= 2:
            continue
        per_item[c[0]] += 1
        picked.append(c)
        if len(picked) == n:
            break
    chosen += [(key, c) for c in picked]
    print(key, "pool", len(pool), "picked", len(picked))


def span_text(iid, s, e, ctx=1, max_words=140):
    idx = index(iid)
    lo, hi = max(0, s - ctx), min(len(idx.units) - 1, e + ctx)
    parts = []
    for k in range(lo, hi + 1):
        mark = "" if s <= k <= e else "(ctx) "
        parts.append(f"[{k}] {mark}{idx.units[k]['text']}")
    words = " ".join(parts).split()
    if len(words) > max_words:
        words = words[:100] + ["....."] + words[-40:]
    return " ".join(words)


def short(label):
    return (label or "").replace("topic:", "t:").replace("cross_cutting:", "x:")


out = []
used_labels = set()
for n, (key, (iid, kind, k)) in enumerate(chosen, 1):
    item = items()[iid]
    res = rep0[item["window_id"]]
    golds = gold()[iid]
    scorable = [g for g in golds if g.tier != "rejected"]
    preds = pred_atoms(res, iid)
    refs = ref_atoms(iid)
    lines = [f"### E{n:02d} {key[0]} {key[1]} | {iid} ({item['stratum']}, {item.get('podcast_title','')[:40]})"]
    if kind == "miss":
        g = scorable[k]
        kk, nn, pat = atom_p.get((iid, g.gold_id), (None, None, None))
        used_labels.add(g.label)
        lines.append(f"GOLD {short(g.label) or g.kind} span {g.tight} env {g.envelope} annotators {g.annotators} ({pat}) DS matched in {kk}/{nn} samples votes {g.votes}")
        for q in (g.claim_texts or [])[:2]:
            lines.append(f"  claim_text: {q}")
        for q in (g.product_names or [])[:2]:
            lines.append(f"  product: {q}")
        for q in list(dict.fromkeys(g.quotes))[:2]:
            lines.append(f"  quote: \"{q}\"")
        others = [a for a in refs if a not in g.annotators]
        for a in others:
            near = [x for x in refs[a] if x.kind == g.kind and overlaps((x.start, x.end), g.envelope) and (g.kind != "detection" or x.axis == g.axis)]
            lines.append(f"  non-supporting {a} on span: " + (", ".join(f"{short(x.label) or x.kind}{(x.start, x.end)}" + (f" '{x.claim_text[:60]}'" if x.claim_text else "") for x in near[:5]) or "nothing"))
        near = [p for p in preds if p.kind == g.kind and overlaps((p.start, p.end), g.envelope)]
        if g.kind == "detection":
            near = [p for p in preds if p.kind == "detection" and overlaps((p.start, p.end), g.envelope)]
        lines.append("  DS on span: " + ("; ".join(f"{short(p.label) or p.kind}{(p.start, p.end)} q='{p.quote[:80]}'" + (f" ct='{p.claim_text[:90]}'" if p.claim_text else "") for p in near[:6]) or "nothing"))
        for p in near:
            if p.label:
                used_labels.add(p.label)
        lines.append("  TEXT: " + span_text(iid, g.tight[0], g.tight[1]))
    else:
        p = preds[k]
        cls = near_miss_class(p, scorable)
        from sva_decompose_helpers import other_samples
        others_atoms = other_samples(iid)
        from analysis.benchmark.references import _single_gold
        rec_hits = sum(1 for oa in others_atoms if assign(oa, [_single_gold(p, 0)]))
        used_labels.add(p.label)
        lines.append(f"PRED {short(p.label) or p.kind} span {(p.start, p.end)} class {cls} attrs {p.attributes}")
        if p.claim_text:
            lines.append(f"  claim_text: {p.claim_text}")
        if p.product_name:
            lines.append(f"  product: {p.product_name}")
        lines.append(f"  quote: \"{p.quote}\"")
        res_obj = res
        lines.append(f"  same atom in {rec_hits}/{len(others_atoms)} other DS samples")
        gnear = [g for g in golds if g.kind == p.kind and overlaps((p.start, p.end), g.envelope) and (p.kind != "detection" or g.axis == p.axis)]
        lines.append("  gold on span: " + ("; ".join(f"{short(g.label) or g.kind}{g.tight}/{g.envelope} {g.tier} {len(g.annotators)}ann" + (f" '{g.claim_texts[0][:70]}'" if g.claim_texts else "") + (f" '{g.product_names}'" if g.product_names else "") for g in gnear[:6]) or "nothing"))
        for g in gnear:
            if g.label:
                used_labels.add(g.label)
        lines.append("  TEXT: " + span_text(iid, p.start, p.end))
    out.append("\n".join(lines))

glossary = [f"- {short(l)}: {DEFS[l]['definition']}" for l in sorted(x for x in used_labels if x in DEFS)]
(OUT / "sva_error_dossiers.txt").write_text("\n\n".join(out) + "\n\n## Glossary\n" + "\n".join(glossary))
print(len(out), "dossiers")
