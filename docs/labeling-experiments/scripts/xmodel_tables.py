import pickle, sys, json
from collections import Counter, defaultdict
from statistics import mean
d = pickle.load(open(sys.argv[1], "rb"))
items = d["items"]; G = ("detection:topic", "detection:frame", "detection:evidence", "claim", "product")
HEAD = {i for i, v in items.items() if v["stratum"] not in ("rare_label", "synthetic", "contrast")}
def f1(tp, fp, fn): return 2*tp/(2*tp+fp+fn) if tp else 0
print("headline items", len(HEAD))
for scope, ids in (("headline", HEAD), ("all70", set(items))):
    print(f"\n== {scope}: per-repeat mean  pred / required / tp / fp / fn / unscored / P / R / F1")
    for name, r in d["runs"].items():
        line = [name]
        for g in G:
            c = Counter()
            for rep in r["reps"]:
                for iid in ids:
                    x = rep[iid]
                    if not x["labeled"]: continue
                    c.update({k: v for k, v in x["row"]["counts"][g].items() if isinstance(v, (int, float))})
            n = len(r["reps"])
            tp, fp, fn = c["tp"], c["fp"], c["fn"]
            P = tp/(tp+fp) if tp+fp else 0; R = tp/(tp+fn) if tp+fn else 0
            line.append(f"{g.split(':')[-1]}: pred {c['pred']/n:.0f} req {c['required']/n:.0f} tp {tp/n:.0f} fp {fp/n:.0f} fn {fn/n:.0f} uns {c['unscored']/n:.0f} P {P:.2f} R {R:.2f} F1 {f1(tp,fp,fn):.2f}")
        print("\n  ".join(line))
    print("labeled windows per repeat:", {n: [sum(1 for iid in ids if rep[iid]['labeled']) for rep in r['reps']] for n, r in d["runs"].items()})
