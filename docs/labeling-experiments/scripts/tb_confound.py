"""Thinking need vs gold density; capped vs finished budget windows."""
import sys; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
import statistics as st, scipy.stats as ss
C = [("dev-high-chat-lenient",0),("dev-high-chat-lenient",1)]; B = ("dev-high-budget16k-lenient",0)
items = sorted(set(D["runs"][B]))
G3 = ("detection:frame","detection:evidence","claim")
need = {i: st.mean(D["runs"][k][i]["usage"]["reasoning"] for k in C) for i in items}
req = {i: sum(D["runs"][C[0]][i]["counts"][g]["required"] for g in G3) for i in items}
def delta(i, gs=G3): return sum(D["runs"][B][i]["counts"][g]["tp"] - st.mean(D["runs"][k][i]["counts"][g]["tp"] for k in C) for g in gs)
COLL = {"c176979w0018", "c184181w0018"}
# partial spearman via rank residuals
import numpy as np
def partial(x, y, z):
    rx, ry, rz = ss.rankdata(x), ss.rankdata(y), ss.rankdata(z)
    ex = rx - np.polyval(np.polyfit(rz, rx, 1), rz); ey = ry - np.polyval(np.polyfit(rz, ry, 1), rz)
    return ss.pearsonr(ex, ey)
for gs, nm in ((G3, "frame+evid+claim"), (("detection:frame",), "frame"), (("claim",), "claim")):
    x = [need[i] for i in items]; y = [delta(i, gs) for i in items]; z = [req[i] for i in items]
    print(nm, "rho(need,delta)", round(ss.spearmanr(x,y)[0],3), "rho(req,delta)", round(ss.spearmanr(z,y)[0],3), "partial rho(need,delta | req)", [round(v,3) for v in partial(x,y,z)])
# within required-gold quartile
qs = np.quantile([req[i] for i in items], [0.25,0.5,0.75])
print("quartile cutpoints", qs)
for lo, hi in ((-1,qs[0]),(qs[0],qs[1]),(qs[1],qs[2]),(qs[2],1e9)):
    its = [i for i in items if lo < req[i] <= hi]
    hiN = [i for i in its if need[i] > 24000]; loN = [i for i in its if need[i] <= 24000]
    f = lambda s: (len(s), round(sum(delta(i) for i in s),1), round(sum(req[i] for i in s)))
    print(f"req in ({lo:.0f},{hi:.0f}]: need<=24k n/tpdelta/req {f(loN)} | need>24k {f(hiN)}")
# capped vs finished
cap = [i for i in items if D["runs"][B][i]["usage"]["reasoning"] >= 16000]; fin = [i for i in items if i not in cap]
for nm, s in (("capped", cap), ("finished", fin)):
    out = []
    for g in ("detection:frame","detection:evidence","claim","detection:topic"):
        rc = st.mean(pool([D["runs"][k][i] for i in s], g)["rec"] for k in C); rb = pool([D["runs"][B][i] for i in s], g)["rec"]
        tpd = sum(D["runs"][B][i]["counts"][g]["tp"] for i in s) - st.mean(sum(D["runs"][k][i]["counts"][g]["tp"] for i in s) for k in C)
        out.append(f"{g.split(':')[-1]} R {rc:.2f}->{rb:.2f} tp {tpd:+.1f}")
    print(nm, len(s), "median need", st.median(need[i] for i in s), " | ".join(out))
# >32k bin without collapsed windows
s = [i for i in items if need[i] >= 32000 and i not in COLL]
for g in ("detection:frame","claim","detection:evidence"):
    print(">32k w/o collapse", len(s), g, round(st.mean(pool([D["runs"][k][i] for i in s], g)["rec"] for k in C),3), "->", round(pool([D["runs"][B][i] for i in s], g)["rec"],3))
# overall deltas without collapsed windows
s = [i for i in items if i not in COLL]
for g in ("detection:frame","claim","detection:evidence"):
    print("all w/o collapse", g, "F1", [round(pool([D["runs"][k][i] for i in s], g)["f1"],3) for k in C+[B]], "R", [round(pool([D["runs"][k][i] for i in s], g)["rec"],3) for k in C+[B]])
