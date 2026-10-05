"""Whole-section drops: a run emits (almost) no claims / frames where the other repeats emit many."""
import sys; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
import statistics as st
def n(k, i, what):
    r = D["runs"][k][i]["result"]
    if what == "claim": return len(r["verification_candidates"])
    if what == "product": return len(r["product_mentions"])
    return sum(1 for d in r["detections"] if d["axis"] == what)
def drops(ref_keys, cand, what, lo, hi):
    its = set.intersection(*[set(D["runs"][k]) for k in ref_keys + [cand]])
    return sorted(i for i in its if all(n(k, i, what) >= hi for k in ref_keys) and n(cand, i, what) <= lo)
C = [("dev-high-chat-lenient",0),("dev-high-chat-lenient",1)]; S = [("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)]
tests = [(C, ("dev-high-budget16k-lenient",0)), ([C[0]], C[1]), ([C[1]], C[0])]
tests += [(S, (f"s70-high-budget{b}k-lenient", r)) for b in (16,12,8,4) for r in (0,1)] + [([S[0]], S[1]), ([S[1]], S[0])]
for ref, cand in tests:
    out = []
    for what, lo, hi in (("claim", 2, 6), ("frame", 0, 2), ("evidence", 0, 2), ("topic", 1, 4)):
        d = drops(ref, cand, what, lo, hi)
        lost = {g: sum(st.mean(D["runs"][k][i]["counts"][g]["tp"] for k in ref) - D["runs"][cand][i]["counts"][g]["tp"] for i in d) for g in ("claim","detection:frame","detection:evidence")}
        out.append(f"{what}: {len(d)} windows {d[:6]} tp lost there {({k.split(':')[-1]: round(v,1) for k,v in lost.items()})}")
    print(cand, "vs", [f"{k[0][:3]}{k[1]}" for k in ref]); [print("   ", o) for o in out]
