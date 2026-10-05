"""Per-item concentration of the frame/claim loss, noise floor, stratum, and thinking-token correlation."""
import sys, random; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
import statistics as st
C0, C1, B = ("dev-high-chat-lenient",0), ("dev-high-chat-lenient",1), ("dev-high-budget16k-lenient",0)
items = sorted(set(D["runs"][C0]) & set(D["runs"][C1]) & set(D["runs"][B]))
def f1(rows, g):
    return pool(rows, g)["f1"]
# stratum table
print("## stratum frame F1 / claim recall: C0 C1 B | n items | frame required")
for s in sorted(set(D["items"][i]["stratum"] for i in items)):
    its = [i for i in items if D["items"][i]["stratum"] == s]
    req = sum(D["runs"][C0][i]["counts"]["detection:frame"]["required"] for i in its)
    print(s, len(its), req, *[f"{f1([D['runs'][k][i] for i in its],'detection:frame'):.3f}" for k in (C0,C1,B)], "|", *[f"{pool([D['runs'][k][i] for i in its],'claim')['rec']:.3f}" for k in (C0,C1,B)])
# per-item tp delta
for g in ("detection:frame", "claim", "detection:evidence"):
    d_b = {i: D["runs"][B][i]["counts"][g]["tp"] - D["runs"][C0][i]["counts"][g]["tp"] for i in items}
    d_n = {i: D["runs"][C1][i]["counts"][g]["tp"] - D["runs"][C0][i]["counts"][g]["tp"] for i in items}
    d_b1 = {i: D["runs"][B][i]["counts"][g]["tp"] - D["runs"][C1][i]["counts"][g]["tp"] for i in items}
    for nm, d in (("B-C0", d_b), ("C1-C0", d_n), ("B-C1", d_b1)):
        vals = list(d.values())
        neg = sorted(vals)[:10]
        print(f"## {g} {nm}: sum {sum(vals)} items down {sum(v<0 for v in vals)} up {sum(v>0 for v in vals)} same {sum(v==0 for v in vals)}; sum abs {sum(map(abs,vals))}; top-10 losses {neg} = {sum(neg)}; sd {st.pstdev(vals):.2f}")
    top = sorted(items, key=lambda i: d_b[i])[:12]
    print("  worst items B-C0:", [(i, D['items'][i]['stratum'], d_b[i], d_n[i]) for i in top])
    # leave-top-k-out frame F1 delta
    for k in (0, 3, 5, 10):
        keep = [i for i in items if i not in set(sorted(items, key=lambda i: d_b[i])[:k])]
        print(f"  drop worst {k}: F1 C0 {f1([D['runs'][C0][i] for i in keep], g):.3f} C1 {f1([D['runs'][C1][i] for i in keep], g):.3f} B {f1([D['runs'][B][i] for i in keep], g):.3f}")
# bootstrap: B-C0 vs C1-C0 in frame F1
rng = random.Random(0)
for g in ("detection:frame", "claim"):
    stat = (lambda rows: pool(rows, g)["f1"]) if g != "claim" else (lambda rows: pool(rows, g)["rec"])
    bs = {"B-C0": [], "C1-C0": [], "B-meanC": []}
    for _ in range(2000):
        s = [rng.choice(items) for _ in items]
        c0 = stat([D["runs"][C0][i] for i in s]); c1 = stat([D["runs"][C1][i] for i in s]); b = stat([D["runs"][B][i] for i in s])
        bs["B-C0"].append(b - c0); bs["C1-C0"].append(c1 - c0); bs["B-meanC"].append(b - (c0 + c1) / 2)
    for k, v in bs.items():
        v.sort(); print(g, k, f"mean {st.mean(v):.3f} CI [{v[50]:.3f}, {v[1949]:.3f}] P(<0) {sum(x<0 for x in v)/len(v):.3f}")
