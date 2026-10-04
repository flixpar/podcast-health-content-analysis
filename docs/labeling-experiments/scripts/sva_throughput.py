"""Part 3: does DeepSeek's thinking length track window ambiguity or content volume?"""

from __future__ import annotations

import itertools
import json
import math
from collections import defaultdict

import numpy as np
from scipy import stats as ss

from sva_common import B, CORPUS, OUT, S70_RUNS, DEV_RUN, gold, items, pool_items, pred_atoms, ref_atoms, run, samples_for
from analysis.benchmark.references import pairwise_f1
from analysis.benchmark import scoring

FAMILY = {"opus-r1": "O", "opus-r2": "O", "sonnet-r1": "S", "sonnet-r2": "S"}


def reasoning_tokens(usage):
    d = usage.get("output_tokens_details") or usage.get("completion_tokens_details") or {}
    return d.get("reasoning_tokens")


def output_tokens(usage):
    return usage.get("output_tokens", usage.get("completion_tokens"))


by_window = defaultdict(list)  # window_id -> list of (run, repeat, reasoning, output)
runs = S70_RUNS + [DEV_RUN]
for name in runs:
    for a in run(name)["attempts"]:
        if not a.get("ok"):
            continue
        r = reasoning_tokens(a["usage"])
        o = output_tokens(a["usage"])
        if r is None:
            continue
        by_window[a["window_id"]].append((name, a["repeat"], r, o))

wid2iid = {it["window_id"]: iid for iid, it in items().items()}


def pooled_f1(pairs):
    tp = sum(p["tp"] for p in pairs); fp = sum(p["fp"] for p in pairs); fn = sum(p["fn"] for p in pairs)
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None


rows = []
for wid, recs in by_window.items():
    iid = wid2iid.get(wid)
    if iid is None or iid not in gold() or items()[iid]["stratum"] not in CORPUS:
        continue
    it = items()[iid]
    g = [x for x in gold()[iid] if x.tier != "rejected"]
    refs = ref_atoms(iid)
    ann_pairs, cross_pairs, oo_pairs = [], [], []
    for a, b in itertools.combinations(sorted(refs), 2):
        c = pairwise_f1(refs[a], refs[b])
        tot = {k: sum(v[k] for v in c.values()) for k in ("tp", "fp", "fn")}
        ann_pairs.append(tot)
        (cross_pairs if FAMILY[a] != FAMILY[b] else oo_pairs if FAMILY[a] == "O" else []).append(tot)
    samples = samples_for(iid, "dev") + samples_for(iid, "s70")
    atoms = [pred_atoms(s, iid) for s in samples]
    self_pairs = []
    for i, j in itertools.combinations(range(len(atoms)), 2):
        c = pairwise_f1(atoms[i], atoms[j])
        self_pairs.append({k: sum(v[k] for v in c.values()) for k in ("tp", "fp", "fn")})
    ann_f1 = pooled_f1(ann_pairs)
    words = sum(len(u["text"].split()) for u in it["units"])
    rows.append({
        "item_id": iid, "stratum": it["stratum"], "n_samples": len(recs),
        "reasoning": float(np.mean([r[2] for r in recs])),
        "reasoning_list": [r[2] for r in recs],
        "answer": float(np.mean([r[3] - r[2] for r in recs])),
        "n_gold": len(g), "n_required": sum(1 for x in g if x.tier == "required"),
        "ann_atoms_mean": float(np.mean([len(v) for v in refs.values()])),
        "ds_atoms": float(np.mean([len(a) for a in atoms])) if atoms else None,
        "singleton_share": (sum(1 for x in g if x.tier != "required") / len(g)) if g else None,
        "ann_disagree": None if ann_f1 is None else 1 - ann_f1,
        "cross_disagree": None if pooled_f1(cross_pairs) is None else 1 - pooled_f1(cross_pairs),
        "oo_disagree": None if pooled_f1(oo_pairs) is None else 1 - pooled_f1(oo_pairs),
        "ds_self_disagree": None if pooled_f1(self_pairs) is None else 1 - pooled_f1(self_pairs),
        "health_units": (it.get("features") or {}).get("health_units"),
        "screen_ambiguity": (it.get("screening") or {}).get("ambiguity"),
        "words": words,
    })

print("windows", len(rows), "with >=2 samples", sum(1 for r in rows if r["n_samples"] >= 2))
R = [r for r in rows if r["n_gold"] > 0]
print("non-empty-gold windows", len(R))


def sp(x, y, data):
    pts = [(d[x], d[y]) for d in data if d[x] is not None and d[y] is not None]
    rho, p = ss.spearmanr([a for a, _ in pts], [b for _, b in pts])
    return round(rho, 2), p, len(pts)


print("\n## Spearman with mean reasoning tokens (windows with any gold)")
for f in ["n_gold", "n_required", "ann_atoms_mean", "ds_atoms", "answer", "words", "health_units", "singleton_share", "ann_disagree", "cross_disagree", "oo_disagree", "ds_self_disagree", "screen_ambiguity"]:
    rho, p, n = sp("reasoning", f, R)
    print(f"  {f:18s} rho={rho:+.2f} p={p:.3g} n={n}")
rho, p, n = sp("reasoning", "n_gold", rows)
print("  (all windows incl. empty gold) n_gold rho", rho, n)

# partial: log reasoning ~ log(1+n_gold) + ambiguity measures
import numpy.linalg as la


def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X)
    beta, *_ = la.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    s2 = resid @ resid / (n - k)
    cov = s2 * la.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))
    return {nm: (round(b, 3), round(b / s, 2)) for nm, b, s in zip(["const"] + names, beta, se)}, round(r2, 3)


D = [r for r in R if r["ann_disagree"] is not None and r["ds_self_disagree"] is not None]
y = np.log([r["reasoning"] for r in D])
vol = np.log1p([r["n_gold"] for r in D])
dsa = np.log1p([r["ds_atoms"] for r in D])
for label, X, names in [
    ("volume only (gold atoms)", [vol], ["log1p_gold"]),
    ("volume + annotator disagreement", [vol, np.array([r["ann_disagree"] for r in D])], ["log1p_gold", "ann_disagree"]),
    ("volume + cross-family disagreement", [vol, np.array([r["cross_disagree"] for r in D])], ["log1p_gold", "cross_disagree"]),
    ("volume + DS self disagreement", [vol, np.array([r["ds_self_disagree"] for r in D])], ["log1p_gold", "ds_self_disagree"]),
    ("DS output atoms + ann disagreement + DS self", [dsa, np.array([r["ann_disagree"] for r in D]), np.array([r["ds_self_disagree"] for r in D])], ["log1p_ds_atoms", "ann_disagree", "ds_self_disagree"]),
    ("gold + words + ann disagreement", [vol, np.array([r["words"] for r in D]) / 100, np.array([r["ann_disagree"] for r in D])], ["log1p_gold", "words_per100", "ann_disagree"]),
]:
    coef, r2 = ols(y, X, names)
    print(f"\nOLS log(reasoning) ~ {label}: R2={r2} coef(t)={coef}")

# partial Spearman: residualise ranks on volume
def partial_spearman(x, y, z, data):
    pts = [(d[x], d[y], d[z]) for d in data if None not in (d[x], d[y], d[z])]
    rx, ry, rz = (ss.rankdata([p[i] for p in pts]) for i in range(3))
    def res(a, b):
        b1 = np.column_stack([np.ones(len(b)), b]); beta, *_ = la.lstsq(b1, a, rcond=None); return a - b1 @ beta
    r, p = ss.pearsonr(res(rx, rz), res(ry, rz))
    return round(r, 2), p, len(pts)

print("\n## partial Spearman with reasoning, controlling gold atom count")
for f in ["ann_disagree", "cross_disagree", "oo_disagree", "singleton_share", "ds_self_disagree", "screen_ambiguity", "words"]:
    print(" ", f, partial_spearman("reasoning", f, "n_gold", R))
print("\n## partial Spearman with reasoning, controlling DS output atoms")
for f in ["ann_disagree", "cross_disagree", "ds_self_disagree", "n_gold"]:
    print(" ", f, partial_spearman("reasoning", f, "ds_atoms", R))

# within-window variability of reasoning length
multi = [r for r in rows if len(r["reasoning_list"]) >= 4]
cv = [np.std(r["reasoning_list"]) / np.mean(r["reasoning_list"]) for r in multi if np.mean(r["reasoning_list"]) > 0]
allv = [np.log(v) for r in multi for v in r["reasoning_list"] if v > 0]
within = np.mean([np.var(np.log([v for v in r["reasoning_list"] if v > 0])) for r in multi])
print(f"\nwithin-window CV (>=4 samples, n={len(multi)}): median {np.median(cv):.2f}; share of log-variance within windows {within / np.var(allv):.2f}")

# by stratum and null
from collections import Counter
print("\nmean reasoning by stratum:", {s: round(np.mean([r["reasoning"] for r in rows if r["stratum"] == s])) for s in sorted({r["stratum"] for r in rows})})
print("empty-gold windows mean reasoning", round(np.mean([r["reasoning"] for r in rows if r["n_gold"] == 0])), "n", sum(1 for r in rows if r["n_gold"] == 0))
print("non-empty mean reasoning", round(np.mean([r["reasoning"] for r in R])), "median", round(np.median([r["reasoning"] for r in R])))
# reasoning per gold atom
print("reasoning tokens per gold atom (median over windows)", round(np.median([r["reasoning"] / r["n_gold"] for r in R])))
print("reasoning tokens per DS output atom (median)", round(np.median([r["reasoning"] / r["ds_atoms"] for r in R if r["ds_atoms"]])))

# ambiguity terciles at fixed volume: split windows by gold volume median, compare reasoning by ann_disagree tercile
med = np.median([r["n_gold"] for r in R])
for half, sel in (("low volume", [r for r in R if r["n_gold"] <= med]), ("high volume", [r for r in R if r["n_gold"] > med])):
    sel = [r for r in sel if r["ann_disagree"] is not None]
    q = np.quantile([r["ann_disagree"] for r in sel], [1 / 3, 2 / 3])
    groups = [[r for r in sel if r["ann_disagree"] <= q[0]], [r for r in sel if q[0] < r["ann_disagree"] <= q[1]], [r for r in sel if r["ann_disagree"] > q[1]]]
    print(half, "reasoning by annotator-disagreement tercile:", [(round(np.mean([r['ann_disagree'] for r in g_]), 2), round(np.median([r['reasoning'] for r in g_])), round(np.mean([r['n_gold'] for r in g_]), 1)) for g_ in groups])

json.dump(rows, open(OUT / "sva_throughput_rows.json", "w"))
