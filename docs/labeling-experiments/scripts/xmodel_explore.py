import pickle, sys, json
from collections import Counter, defaultdict
d = pickle.load(open(sys.argv[1], "rb"))
items = d["items"]; gold = d["gold"]
G = ("detection:topic", "detection:frame", "detection:evidence", "claim", "product")
CREDIT = ("required", "acceptable")
# 1. attempts validation
print("== attempts")
for name, r in d["runs"].items():
    kinds = Counter(); rep = Counter(); drop = Counter(); out_tok = []; reason = []
    for a in r["attempts"]:
        kinds["ok" if a.get("ok") else "rej:" + str(a.get("error_kind") or a.get("kind") or a.get("error", "")[:40])] += 1
        v = a.get("validation") or {}
        rep.update(v.get("repaired") or {}); drop.update(v.get("dropped") or {})
        u = a.get("usage") or {}
        ot = u.get("output_tokens") or u.get("completion_tokens")
        if ot: out_tok.append(ot)
    out_tok.sort()
    print(name, dict(kinds), "repaired", dict(rep), "dropped", dict(drop), "out_tok median", out_tok[len(out_tok)//2] if out_tok else None, "max", out_tok[-1] if out_tok else None)
    print("  attempt keys", sorted(set(k for a in r["attempts"] for k in a)))
# 2. error classes (all70, summed over repeats /2)
print("\n== error classes (mean per repeat)")
for name, r in d["runs"].items():
    c = Counter()
    for rep in r["reps"]:
        for iid, x in rep.items():
            for e in x["row"]["errors"]:
                c[f"{e['type']}:{e['group'].split(':')[-1]}:{e['class']}"] += 0.5
    print(name, {k: v for k, v in sorted(c.items())})
# 3. per-item frame/evidence counts vs gold required
print("\n== per-item axis counts: items with required>0 where model predicts 0 (sum over repeats), and pred/gold ratio")
for g in ("detection:frame", "detection:evidence", "detection:topic", "claim"):
    print(" group", g)
    goldn = {iid: sum(1 for a in gold[iid] if a["group"] == g and a["tier"] in CREDIT) for iid in items}
    has = [iid for iid in items if goldn[iid] > 0]
    print("   items with credit gold:", len(has), "; gold atoms", sum(goldn.values()))
    for name, r in d["runs"].items():
        zero = 0; tot = 0; wins = 0
        for rep in r["reps"]:
            for iid in has:
                x = rep[iid]
                if not x["labeled"]: continue
                tot += 1
                n = sum(1 for p in x["preds"] if p["group"] == g)
                if n == 0: zero += 1
        nullpred = sum(1 for rep in r["reps"] for iid in items if goldn[iid] == 0 and rep[iid]["labeled"] and any(p["group"] == g for p in rep[iid]["preds"]))
        print(f"   {name:24s} zero-pred on gold items {zero}/{tot} ; windows w/o gold but with pred {nullpred}/{2*(len(items)-len(has))}")
