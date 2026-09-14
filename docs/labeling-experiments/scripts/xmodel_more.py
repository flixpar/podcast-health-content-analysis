import pickle, sys, json
from collections import Counter, defaultdict
from statistics import mean, median
sys.path.insert(0, "/scratch/fparker9/podcasts/podcast-health-content-analysis-01")
from analysis.benchmark import stats
d = pickle.load(open(sys.argv[1], "rb"))
items = d["items"]; gold = d["gold"]; R = d["runs"]
CREDIT = ("required", "acceptable")
print("== shape per labeled window: detections(results), labels/detection, claims, frames on claims, evidence on claims")
for name, r in R.items():
    nd = []; lpd = []; nc = []; cf = 0; ce = 0; ncl = 0; claims_with_frames = 0
    frame_det = 0; ev_det = 0
    for rep in r["reps"]:
        for iid, x in rep.items():
            res = x["result"]
            if res is None: continue
            nd.append(len(res["detections"])); nc.append(len(res["verification_candidates"]))
            lpd += [len(dd["label_ids"]) for dd in res["detections"]]
            for c in res["verification_candidates"]:
                ncl += 1; cf += len(c["frame_ids"]); ce += len(c["evidence_signal_ids"])
                claims_with_frames += bool(c["frame_ids"] or c["evidence_signal_ids"])
            frame_det += sum(1 for dd in res["detections"] if dd["axis"] == "frame")
            ev_det += sum(1 for dd in res["detections"] if dd["axis"] == "evidence")
    n = len(r["reps"])
    print(f"{name:24s} det/win mean {mean(nd):.1f} med {median(nd)} | labels/det {mean(lpd):.2f} | claims/win {mean(nc):.1f} | claims w/ frame|ev ids {claims_with_frames/max(ncl,1):.2f} (frame ids {cf/n:.0f}, ev ids {ce/n:.0f} per rep) | frame dets {frame_det/n:.0f} ev dets {ev_det/n:.0f}")
# gold per window
gd = [sum(1 for a in gold[i] if a['tier'] in CREDIT and a['group'].startswith('detection')) for i in items]
print("gold detection atoms per window mean", mean(gd), "median", median(gd))
# labels per gold detection? gold is per atom.
print("\n== frame/evidence label distribution (pred atoms per rep) vs gold credit atoms")
for axis in ("frame", "evidence"):
    g = Counter(a["label"] for i in items for a in gold[i] if a["group"] == f"detection:{axis}" and a["tier"] in CREDIT)
    table = {name: Counter() for name in R}
    tps = {name: Counter() for name in R}
    for name, r in R.items():
        for rep in r["reps"]:
            for iid, x in rep.items():
                for p in x["preds"]:
                    if p["group"] == f"detection:{axis}":
                        table[name][p["label"]] += 0.5
                        if p["status"] == "tp": tps[name][p["label"]] += 0.5
    labs = sorted(set(g) | set().union(*table.values()), key=lambda l: -g.get(l, 0))
    print(f"{'label':45s} gold " + " ".join(f"{n[:10]:>11s}" for n in R))
    for l in labs:
        print(f"{l.replace('cross_cutting:',''):45s} {g.get(l,0):4d} " + " ".join(f"{table[n][l]:5.1f}/{tps[n][l]:<5.1f}" for n in R))
print("\n== null windows: atoms per window, share with output, and labels emitted")
nulls = [i for i, v in items.items() if v["stratum"] == "null"]
for name, r in R.items():
    at = []; labs = Counter()
    for rep in r["reps"]:
        for iid in nulls:
            x = rep[iid]
            if not x["labeled"]: continue
            at.append(len(x["preds"]))
            for p in x["preds"]: labs[(p["group"], p["label"] or p["product"] or p["claim"][:60], p["status"])] += 1
    print(f"{name:24s} atoms/win {mean(at):.2f} share {sum(1 for a in at if a)/len(at):.2f}", dict(labs.most_common(6)))
print("\n== calibration & attributes")
for name, r in R.items():
    cal = [c for rep in r["reps"] for x in rep.values() for c in x["row"]["calibration"]]
    s = [c[0] for c in cal]; l = [c[1] for c in cal]
    confs = Counter(round(v, 2) for v in s)
    tpc = [a for a, b in cal if b]; fpc = [a for a, b in cal if not b]
    attrs = defaultdict(list)
    for rep in r["reps"]:
        for iid, x in rep.items():
            for p in x["row"]["attribute_pairs"]:
                attrs[f"{p['kind']}:{p['attribute']}"].append(p["exact"])
    print(f"{name:24s} AUROC {stats.auroc(s,l)} TPmean {mean(tpc):.3f} FPmean {mean(fpc):.3f} conf values {dict(confs.most_common(5))}")
    print("    ", {k: f"{mean(v):.2f} (n={len(v)//2})" for k, v in sorted(attrs.items())})
print("\n== discourse role on detections/claims: predicted non-asserted share vs gold plurality non-asserted share (matched)")
for name, r in R.items():
    c = Counter()
    for rep in r["reps"]:
        for iid, x in rep.items():
            for p in x["row"]["attribute_pairs"]:
                if p["attribute"] == "discourse_role":
                    c[(p["kind"], p["plurality"], p["predicted"])] += 0.5
    conf = {k: v for k, v in c.items() if k[1] != k[2]}
    tot_gold_non = sum(v for k, v in c.items() if k[1] != "asserted_or_endorsed")
    hit_non = sum(v for k, v in c.items() if k[1] != "asserted_or_endorsed" and k[1] == k[2])
    pred_non = sum(v for k, v in c.items() if k[2] != "asserted_or_endorsed")
    print(f"{name:24s} gold non-asserted matched {tot_gold_non:.0f}, recovered {hit_non:.0f}, pred non-asserted {pred_non:.0f}; top confusions", sorted(conf.items(), key=lambda kv: -kv[1])[:4])
print("\n== claim types & certainty distribution of predicted claims (per rep)")
for name, r in R.items():
    ct = Counter(); cert = Counter(); ln = []
    for rep in r["reps"]:
        for x in rep.values():
            if not x["result"]: continue
            for c in x["result"]["verification_candidates"]:
                ct[c["claim_type"]] += .5; cert[c["expressed_certainty"]] += .5; ln.append(len(c["claim_text"].split()))
    print(f"{name:24s} words/claim {mean(ln):.1f}", dict(ct.most_common()), dict(cert))
