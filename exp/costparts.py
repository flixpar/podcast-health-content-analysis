"""Where the output tokens go: split each window's completion into reasoning
and answer tokens, the answer by section and field, and attribute reasoning
tokens to label groups by non-negative least squares on per-window counts.

    python exp/costparts.py --bench v3 exp/corpus/v8-glm exp/corpus/v8-high
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import nnls
from tokenizers import Tokenizer

TOK = Tokenizer.from_file(str(next(Path("/tmp/huggingface2/hub/models--canada-quant--GLM-5.3-Flash-W4A16-MTP/snapshots").glob("*/tokenizer.json"))))


def ntok(text: str) -> int:
    return len(TOK.encode(text).ids)


def load(run: Path):
    con = sqlite3.connect(run / "repeat_0" / "labels.sqlite")
    results = {w: json.loads(r) for w, r in con.execute("select window_id, result_json from window_labels")}
    usage = {}
    for line in open(run / "repeat_0" / "attempts.jsonl"):
        r = json.loads(line)
        if r.get("ok") and r.get("usage"):
            usage[r["window_id"]] = r["usage"]
    return results, usage


def group_of(label: str, tax: dict) -> str:
    meta = tax.get(label)
    if not meta:
        return label.split(":")[0] + ":?"
    if meta["axis"] == "topic":
        return "topic/" + meta["domain"]
    if meta["axis"] == "narrative":
        return "narr/" + meta.get("family", "?")
    return meta["axis"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="v3")
    ap.add_argument("runs", nargs="+")
    args = ap.parse_args()
    tax = {l["label_id"]: l for l in json.load(open(f"benchmark/{args.bench}/taxonomy.json"))["labels"]}
    for run in map(Path, args.runs):
        results, usage = load(run)
        ids = [w for w in results if w in usage]
        print(f"\n## {run}  windows={len(ids)}")
        comp = np.array([usage[w]["completion_tokens"] for w in ids], float)
        reas = np.array([(usage[w].get("completion_tokens_details") or {}).get("reasoning_tokens") or 0 for w in ids], float)
        ans = comp - reas
        print(f"completion mean {comp.mean():.0f} (median {np.median(comp):.0f}); reasoning {reas.mean():.0f} ({reas.sum()/comp.sum():.0%}); answer {ans.mean():.0f}")
        empty = np.array([not (results[w]["detections"] or results[w]["verification_candidates"] or results[w]["product_mentions"]) for w in ids])
        print(f"empty windows {empty.mean():.0%}: share of all completion tokens {comp[empty].sum()/comp.sum():.0%}, mean {comp[empty].mean():.0f}; non-empty mean {comp[~empty].mean():.0f}")
        # answer tokens by section and field
        sec = Counter()
        field = Counter()
        for w in ids:
            r = results[w]
            for d in r["detections"]:
                ax = d.get("axis") or (tax.get(d["label_ids"][0], {}).get("axis") if d["label_ids"] else "?")
                sec["det/" + str(ax)] += ntok(json.dumps(d, ensure_ascii=False))
                for f in ("summary", "evidence_quote"):
                    field["det." + f] += ntok(d.get(f, ""))
            for c in r["verification_candidates"]:
                sec["claims"] += ntok(json.dumps(c, ensure_ascii=False))
                for f in ("claim_text", "evidence_quote", "rationale"):
                    field["claim." + f] += ntok(c.get(f, ""))
            for p in r["product_mentions"]:
                sec["products"] += ntok(json.dumps(p, ensure_ascii=False))
                field["product.evidence_quote"] += ntok(p.get("evidence_quote", ""))
        tot = ans.sum()
        print("answer tokens by section (share of answer tokens; per window):")
        for k, v in sec.most_common():
            print(f"  {k:24s} {v/tot:6.1%}  {v/len(ids):7.0f}")
        print("free-text fields:")
        for k, v in field.most_common():
            print(f"  {k:24s} {v/tot:6.1%}  {v/len(ids):7.0f}")
        # attribution of reasoning tokens by label group (NNLS on counts)
        groups = Counter()
        rows = []
        for w in ids:
            r = results[w]
            c = Counter()
            for d in r["detections"]:
                for l in d["label_ids"]:
                    c[group_of(l, tax)] += 1
            c["claims"] += len(r["verification_candidates"])
            c["products"] += len(r["product_mentions"])
            rows.append(c)
            groups.update(k for k in c)
        cols = [g for g, n in groups.items() if n >= 8]
        X = np.array([[1.0] + [row.get(g, 0) for g in cols] for row in rows])
        for name, y in (("reasoning", reas), ("completion", comp)):
            coef, _ = nnls(X, y)
            share = {g: coef[i + 1] * X[:, i + 1].sum() / y.sum() for i, g in enumerate(cols)}
            print(f"NNLS {name}: intercept {coef[0]:.0f}/window ({coef[0]*len(ids)/y.sum():.0%} of total)")
            for g in sorted(share, key=share.get, reverse=True)[:18]:
                i = cols.index(g)
                print(f"  {g:40s} +{coef[i+1]:6.0f}/item  windows={groups[g]:4d}  share={share[g]:.1%}")


if __name__ == "__main__":
    main()
