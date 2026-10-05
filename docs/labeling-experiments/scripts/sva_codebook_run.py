"""Read-only check of s70-high-codebook-lenient (rubric = annotators' codebook) against the SYSTEM_RUBRIC runs.

Only repeats with a repeat_manifest.json are used.
"""

from __future__ import annotations

import json
import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from sva_common import B, HEADLINE, CORPUS, gold, items
from analysis.benchmark import scoring

wid2iid = {it["window_id"]: iid for iid, it in items().items()}


def load(name):
    out = []
    for rep in sorted((B / "runs" / name).glob("repeat_*")):
        if not (rep / "repeat_manifest.json").exists():
            continue
        con = sqlite3.connect(f"file:{rep / 'labels.sqlite'}?mode=ro", uri=True)
        res, use = {}, {}
        for wid, rj, uj in con.execute("select window_id, result_json, usage_json from window_labels"):
            res[wid] = json.loads(rj)
            u = json.loads(uj) if uj else {}
            d = u.get("output_tokens_details") or u.get("completion_tokens_details") or {}
            use[wid] = d.get("reasoning_tokens")
        out.append((rep.name, res, use))
    return out


RUNS = {"codebook": ["s70-high-codebook-lenient"], "rubric (chat)": ["s70-high-chat-lenient"],
        "rubric (all 3 s70 runs)": ["s70-high-lenient", "s70-high-chat-lenient", "s70-high-budget24k-lenient"]}
cb = load("s70-high-codebook-lenient")
ids = sorted(wid2iid[w] for w in cb[0][1] if wid2iid.get(w) in gold())


def per_item_rows(samples, strata):
    rows = defaultdict(list)
    for _, res, use in samples:
        for iid in ids:
            it = items()[iid]
            if it["stratum"] not in strata or it["window_id"] not in res:
                continue
            r = scoring.score_item(it, res[it["window_id"]], gold()[iid])
            r["reasoning"] = use.get(it["window_id"])
            rows[iid].append(r)
    return rows


def metrics(rows):
    c = defaultdict(Counter)
    attr = defaultdict(lambda: [0.0, 0.0])
    reasoning = []
    for iid, rs in rows.items():
        w = 1 / len(rs)
        for r in rs:
            for g, cnt in r["counts"].items():
                for f in ("tp", "fp", "fn", "pred", "gold"):
                    c[g][f] += cnt.get(f, 0) * w
            for p in r["attribute_pairs"]:
                k = f"{p['kind']}:{p['attribute']}"
                attr[k][0] += w * p["exact"]
                attr[k][1] += w
            if r["reasoning"]:
                reasoning.append(r["reasoning"])
    out = {}
    for g in ("detection:topic", "detection:frame", "detection:evidence", "claim", "product"):
        tp, fp, fn = c[g]["tp"], c[g]["fp"], c[g]["fn"]
        out[g] = dict(P=tp / (tp + fp), R=tp / (tp + fn), F1=2 * tp / (2 * tp + fp + fn), yield_=c[g]["pred"] / c[g]["gold"])
    out["attr"] = {k: (v[0] / v[1], v[1]) for k, v in attr.items()}
    out["reasoning_mean"] = float(np.mean(reasoning)) if reasoning else None
    return out


def boot(rows_a, rows_b, group, stat="F1", n=2000, seed=0):
    common = sorted(set(rows_a) & set(rows_b))
    rng = random.Random(seed)
    def val(rows, pick):
        return metrics({i: rows[i] for i in pick})[group][stat] if group in ("detection:topic", "detection:frame", "detection:evidence", "claim", "product") else None
    point = metrics({i: rows_b[i] for i in common})[group][stat] - metrics({i: rows_a[i] for i in common})[group][stat]
    ds = []
    for _ in range(n // 4):
        pick = [rng.choice(common) for _ in common]
        ds.append(metrics({f"{k}-{j}": rows_b[k] for j, k in enumerate(pick)})[group][stat] - metrics({f"{k}-{j}": rows_a[k] for j, k in enumerate(pick)})[group][stat])
    ds.sort()
    return point, ds[int(0.025 * len(ds))], ds[int(0.975 * len(ds)) - 1]


print("codebook repeats used:", [r[0] for r in cb], "items", len(ids))
for strata_name, strata in (("headline+rare (corpus)", CORPUS),):
    table = {}
    rows_by = {}
    for name, runs in RUNS.items():
        samples = [s for rn in runs for s in load(rn)]
        rows_by[name] = per_item_rows(samples, strata)
        table[name] = metrics(rows_by[name])
    print(f"\n## {strata_name}")
    print("| metric | " + " | ".join(table) + " |")
    for g in ("detection:topic", "detection:frame", "detection:evidence", "claim", "product"):
        for s in ("F1", "P", "R", "yield_"):
            print(f"| {g} {s} | " + " | ".join(f"{table[n][g][s]:.3f}" for n in table) + " |")
    for k in ("claim:claim_type", "product:product_type", "claim:expressed_certainty", "claim:discourse_role", "detection:discourse_role", "detection:relevance", "product:mention_role"):
        print(f"| {k} exact | " + " | ".join(f"{table[n]['attr'].get(k, (float('nan'), 0))[0]:.3f} (n={table[n]['attr'].get(k, (0, 0))[1]:.0f})" for n in table) + " |")
    print("| reasoning tokens mean | " + " | ".join(f"{table[n]['reasoning_mean']:.0f}" for n in table) + " |")
    for g in ("detection:topic", "detection:frame", "detection:evidence", "claim", "product"):
        print("bootstrap codebook - rubric(chat)", g, "F1", [round(x, 3) for x in boot(rows_by["rubric (chat)"], rows_by["codebook"], g)])
    print("bootstrap codebook - rubric(chat) claim R", [round(x, 3) for x in boot(rows_by["rubric (chat)"], rows_by["codebook"], "claim", "R")])
    print("bootstrap codebook - rubric(chat) topic R", [round(x, 3) for x in boot(rows_by["rubric (chat)"], rows_by["codebook"], "detection:topic", "R")])

# claim_type distribution under codebook
dist = Counter()
for _, res, _ in cb:
    for w, r in res.items():
        for c in r.get("verification_candidates", []):
            dist[c["claim_type"]] += 1
tot = sum(dist.values())
print("codebook-run claim_type distribution", {k: round(v / tot, 2) for k, v in dist.most_common()})
pdist = Counter(p["product_type"] for _, res, _ in cb for r in res.values() for p in r.get("product_mentions", []))
tot = sum(pdist.values())
print("codebook-run product_type distribution", {k: round(v / tot, 2) for k, v in pdist.most_common()})
