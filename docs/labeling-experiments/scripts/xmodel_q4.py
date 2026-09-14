import pickle, sys, json
from collections import Counter, defaultdict
d = pickle.load(open(sys.argv[1], "rb"))
items = d["items"]; gold = d["gold"]; R = d["runs"]
CREDIT = ("required", "acceptable")
DS = "s70-high-lenient"; ALTS = [n for n in R if n != DS]
def found(name, iid):
    reps = [rep[iid] for rep in R[name]["reps"] if rep[iid]["labeled"]]
    return [{p["gold_id"] for p in x["preds"] if p["status"] == "tp"} for x in reps]
wins = defaultdict(list); shared = []
for iid in items:
    for g in gold[iid]:
        if g["tier"] not in CREDIT: continue
        ds = found(DS, iid)
        ds_any = any(g["gold_id"] in s for s in ds); ds_all = all(g["gold_id"] in s for s in ds)
        alt_status = {}
        for a in ALTS:
            f = found(a, iid)
            alt_status[a] = (sum(g["gold_id"] in s for s in f), len(f))
            if not ds_any and f and all(g["gold_id"] in s for s in f):
                wins[a].append((iid, g))
        if not ds_any and all(v[0] == 0 for v in alt_status.values()):
            shared.append((iid, g))
print("== alt wins (TP in all alt repeats, missed in both DS repeats)")
for a in ALTS:
    c = Counter(g["group"] for _, g in wins[a])
    print(a, len(wins[a]), dict(c))
    for iid, g in wins[a][:8]:
        print("   ", iid, items[iid]["stratum"], g["group"], g["label"], g["tier"], g["tight"], "|", (g["claim_texts"] or g["product_names"] or g["quotes"] or [""])[0][:130])
tot = Counter(g["group"] for iid in items for g in gold[iid] if g["tier"] in CREDIT)
print("\n== shared misses (no model, no repeat finds):", len(shared), dict(Counter(g["group"] for _, g in shared)), "of credit gold", dict(tot))
print("by tier", Counter(g["tier"] for _, g in shared), "by label", Counter(g["label"] for _, g in shared).most_common(15))
print("support", Counter(round(g["support"],2) for _, g in shared))
json.dump([dict(iid=iid, stratum=items[iid]["stratum"], **{k: g[k] for k in ("gold_id","group","label","tier","tight","envelope","support","quotes","claim_texts","product_names","votes")}) for iid, g in shared],
          open(sys.argv[2], "w"), indent=1, default=list)
# systematic FPs shared: pred atoms (label, span) by DS both reps that are FP, and which alt models also have an FP overlapping same label
print("\n== DS false positives also produced (same group+label, overlapping span, FP) by >=4 of 6 alt models")
def fps(name, iid):
    out = []
    for rep in R[name]["reps"]:
        out += [p for p in rep[iid]["preds"] if p["status"] == "fp"]
    return out
cnt = 0
for iid in items:
    dsf = [p for p in fps(DS, iid) if p["group"].startswith("detection")]
    seen = set()
    for p in dsf:
        key = (p["label"], p["span"])
        if key in seen: continue
        seen.add(key)
        n = 0
        for a in ALTS:
            if any(q["label"] == p["label"] and not (q["span"][1] < p["span"][0] or q["span"][0] > p["span"][1]) for q in fps(a, iid)):
                n += 1
        if n >= 3:
            cnt += 1
            print("  ", iid, items[iid]["stratum"], p["label"], p["span"], p["cls"], f"alts={n}", "|", p["quote"][:120])
print("count", cnt)
