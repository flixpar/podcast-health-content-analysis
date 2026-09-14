import pickle, sys, json, random
from collections import Counter, defaultdict
S = sys.argv[1]
d = pickle.load(open(S, "rb"))
items = d["items"]; gold = d["gold"]; R = d["runs"]
full = {json.loads(l)["item_id"]: json.loads(l) for l in open("/scratch/fparker9/podcasts/podcast-health-content-analysis-01/benchmark/runs/sample-dev70.jsonl")}
mode = sys.argv[2]
if mode == "fp":  # sample FPs per model, group, class
    name, group, cls = sys.argv[3], sys.argv[4], sys.argv[5]
    n = int(sys.argv[6]) if len(sys.argv) > 6 else 12
    rows = []
    for k, rep in enumerate(R[name]["reps"]):
        for iid, x in rep.items():
            for p in x["preds"]:
                if p["status"] == "fp" and p["group"] == group and (cls == "any" or p["cls"] == cls):
                    rows.append((iid, k, p))
    print(len(rows))
    random.seed(1)
    for iid, k, p in random.sample(rows, min(n, len(rows))):
        print(f"{iid} r{k} {items[iid]['stratum']} {p['label']} {p['span']} conf={p['conf']} {p['attrs']} |Q {p['quote'][:160]!r} |C {p['claim'][:160]!r} |P {p['product']!r}")
elif mode == "item":
    iid = sys.argv[3]; names = sys.argv[4].split(",")
    groups = sys.argv[5].split(",") if len(sys.argv) > 5 else None
    lo, hi = (int(sys.argv[6]), int(sys.argv[7])) if len(sys.argv) > 7 else (0, 10**9)
    it = full[iid]
    for i, u in enumerate(it["units"]):
        if lo <= i <= hi: print(f"[{i}] {u['text']}")
    print("-- gold")
    for g in gold[iid]:
        if groups and g["group"] not in groups: continue
        print(f"  {g['gold_id']} {g['tier']} s={g['support']} {g['group']} {g['label']} {g['tight']} {g['envelope']} | {(g['claim_texts'] or g['product_names'] or g['quotes'] or [''])[0][:140]}")
    for name in names:
        for k, rep in enumerate(R[name]["reps"]):
            print(f"-- {name} r{k}")
            for p in rep[iid]["preds"]:
                if groups and p["group"] not in groups: continue
                print(f"  {p['status']} {p['cls'] or ''} {p['gold_id'] or ''} {p['group']} {p['label']} {p['span']} {p['attrs'].get('discourse_role')} | {(p['claim'] or p['product'] or p['quote'])[:140]}")
