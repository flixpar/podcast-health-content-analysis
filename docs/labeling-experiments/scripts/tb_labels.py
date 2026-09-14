"""Per-label recall and loss classification: chat vs budget."""
import sys; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
from analysis.benchmark.matching import Atom, GoldAtom
from analysis.benchmark.scoring import _miss_class, group_of

def gold_atoms(item_id):
    return [GoldAtom(**{k: (tuple(v) if k in ("tight","envelope") else v) for k, v in g.items()}) for g in D["gold"][item_id]]
def pred_atoms(row):
    return [Atom(kind=p["kind"], start=p["start"], end=p["end"], axis=p["axis"], label=p["label"], attributes=p["attributes"]) for p in row["preds"]]

def label_table(pairs, group_prefix):
    # pairs: list of run keys; returns per-label found counts over required gold
    req = Counter(); found = defaultdict(Counter); predn = defaultdict(Counter)
    for key in pairs:
        rows = D["runs"][key]
        for iid, row in rows.items():
            for p in row["preds"]:
                if p["kind"] == "detection" and p["axis"] == group_prefix: predn[key][p["label"]] += 1
    items = set.intersection(*[set(D["runs"][k]) for k in pairs])
    for iid in items:
        for g in D["gold"][iid]:
            if g["kind"] == "detection" and g["axis"] == group_prefix and g["tier"] == "required":
                req[g["label"]] += 1
                for key in pairs:
                    if g["gold_id"] in D["runs"][key][iid]["matched_gold"]: found[key][g["label"]] += 1
    return req, found, predn

mode = sys.argv[1]
if mode == "labels":
    A = [("dev-high-chat-lenient",0),("dev-high-chat-lenient",1),("dev-high-budget16k-lenient",0)]
    for axis in ("frame","evidence"):
        req, found, predn = label_table(A, axis)
        print(f"## {axis}: label | required | found chat r0 | chat r1 | b16 r0 | pred chat r0 | chat r1 | b16")
        for lab in sorted(set(req)|set(predn[A[0]]), key=lambda l: -req[l]):
            print(lab, req[lab], *[found[k][lab] for k in A], *[predn[k][lab] for k in A])
    S = [("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)] + [(f"s70-high-budget{b}k-lenient",r) for b in (16,12,8,4) for r in (0,1)]
    for axis in ("frame","evidence"):
        req, found, predn = label_table(S, axis)
        print(f"## s70 {axis}: label | req | found: chat r0 r1 | 16k r0 r1 | 12k | 8k | 4k")
        for lab in sorted(req, key=lambda l: -req[l]):
            print(lab, req[lab], *[found[k][lab] for k in S])
if mode == "claimtypes":
    # required claim gold by plurality claim_type, found per run
    for A in ([("dev-high-chat-lenient",0),("dev-high-chat-lenient",1),("dev-high-budget16k-lenient",0)],
              [("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)] + [(f"s70-high-budget{b}k-lenient",r) for b in (16,12,8,4) for r in (0,1)]):
        items = set.intersection(*[set(D["runs"][k]) for k in A])
        req = Counter(); found = defaultdict(Counter)
        for iid in items:
            for g in D["gold"][iid]:
                if g["kind"] == "claim" and g["tier"] == "required":
                    v = g["votes"].get("claim_type", {}); ct = max(sorted(v), key=lambda x: v[x]) if v else None
                    rel = g["votes"].get("relevance", {}); rl = max(sorted(rel), key=lambda x: rel[x]) if rel else None
                    dr = g["votes"].get("discourse_role", {}); d = max(sorted(dr), key=lambda x: dr[x]) if dr else None
                    for keyname in (f"type:{ct}", f"rel:{rl}", f"role:{d}"):
                        req[keyname] += 1
                        for k in A:
                            if g["gold_id"] in D["runs"][k][iid]["matched_gold"]: found[k][keyname] += 1
        print("## claims", [f"{k[0][-20:]}:{k[1]}" for k in A])
        for kn in sorted(req):
            print(kn, req[kn], *[found[k][kn] for k in A])
        # predicted claim_type distribution
        for k in A:
            c = Counter(p["attributes"].get("claim_type") for r in D["runs"][k].values() for p in r["preds"] if p["kind"]=="claim")
            print("pred types", k, dict(c.most_common()))
if mode == "missclass":
    # gold (required) matched by chat but not by budget: what did budget output there?
    def classify(base, cand):
        out = defaultdict(Counter); exs = defaultdict(list)
        for iid in set(D["runs"][base]) & set(D["runs"][cand]):
            golds = gold_atoms(iid); preds = pred_atoms(D["runs"][cand][iid])
            mb = set(D["runs"][base][iid]["matched_gold"]); mc = set(D["runs"][cand][iid]["matched_gold"])
            for g in golds:
                if g.tier != "required": continue
                grp = group_of(g)
                if g.gold_id in mb and g.gold_id not in mc:
                    out[grp]["lost:" + _miss_class(g, preds)] += 1
                elif g.gold_id in mc and g.gold_id not in mb:
                    out[grp]["gained"] += 1
                elif g.gold_id in mc: out[grp]["both"] += 1
                else: out[grp]["neither"] += 1
        return out
    pairs = [(("dev-high-chat-lenient",0),("dev-high-budget16k-lenient",0)), (("dev-high-chat-lenient",0),("dev-high-chat-lenient",1)),(("dev-high-chat-lenient",1),("dev-high-budget16k-lenient",0))]
    for b in (16,12,8,4):
        for r in (0,1): pairs.append((("s70-high-chat-lenient",r),(f"s70-high-budget{b}k-lenient",r)))
    pairs.append((("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)))
    for base, cand in pairs:
        out = classify(base, cand)
        print("##", base, "->", cand)
        for grp in GROUPS:
            print("  ", grp, dict(sorted(out[grp].items())))
