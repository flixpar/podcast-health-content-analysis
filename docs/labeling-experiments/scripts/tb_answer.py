"""Answer-length collapse and reasoning leakage after a forced stop."""
import sys, re, json; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
import statistics as st
LEAK = re.compile(r"\b(let's|let me|actually need|wait,|hmm|we need to|i need to|okay so|fix later|double-check)\b", re.I)
def ans(k, i): u = D["runs"][k][i]["usage"]; return u["completion"] - u["reasoning"]
for k in D["runs"]:
    rows = D["runs"][k]
    capped = [i for i in rows if rows[i]["usage"]["reasoning"] >= (int(re.search(r"budget(\d+)k", k[0]).group(1))*1000 if "budget" in k[0] else 10**9)]
    small = [i for i in rows if ans(k, i) < 400 and len(rows[i]["preds"]) <= 2]
    nonnull_small = [i for i in small if D["items"][i]["stratum"] != "null" and sum(1 for g in D["gold"][i] if g["tier"]=="required") >= 5]
    leaks = []
    for i, r in rows.items():
        res = r["result"]
        for coll in ("detections", "verification_candidates", "product_mentions"):
            for a in res.get(coll, []):
                for f in ("summary", "claim_text", "rationale"):
                    if a.get(f) and LEAK.search(a[f]): leaks.append((i, f, a[f][:140]))
    print(k, "capped", len(capped), "| near-empty answers on windows with >=5 required gold:", [(i, ans(k,i), len(rows[i]["preds"])) for i in nonnull_small], "| leaked-reasoning fields", len(leaks), "in windows", len(set(l[0] for l in leaks)))
    for l in leaks[:4]: print("     ", l)
