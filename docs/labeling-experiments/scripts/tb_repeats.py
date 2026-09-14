"""All unbudgeted vs 16k repeats on the 70 shared items: is the dev 16k frame loss a noisy repeat?"""
import sys, itertools, random; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
import statistics as st
its = sorted(D["runs"][("s70-high-chat-lenient",0)])
CH = [("dev-high-chat-lenient",0),("dev-high-chat-lenient",1),("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)]
BU = [("dev-high-budget16k-lenient",0),("s70-high-budget16k-lenient",0),("s70-high-budget16k-lenient",1)]
for k in CH+BU:
    rows=[D["runs"][k][i] for i in its]
    cap = sum(r["usage"]["reasoning"]>=16000 for r in rows)
    print(k, "frame tp", pool(rows,"detection:frame")["tp"], "claim tp", pool(rows,"claim")["tp"], "windows >=16k reasoning", cap, "median reasoning", st.median(r["usage"]["reasoning"] for r in rows))
for g in ("detection:frame","claim","detection:evidence"):
    def pdiff(a,b): return sum(abs(D["runs"][a][i]["counts"][g]["tp"]-D["runs"][b][i]["counts"][g]["tp"]) for i in its)
    def sdiff(a,b): return sum(D["runs"][b][i]["counts"][g]["tp"]-D["runs"][a][i]["counts"][g]["tp"] for i in its)
    cc=[(pdiff(a,b),sdiff(a,b)) for a,b in itertools.combinations(CH,2)]
    bb=[(pdiff(a,b),sdiff(a,b)) for a,b in itertools.combinations(BU,2)]
    cb=[(pdiff(a,b),sdiff(a,b)) for a in CH for b in BU]
    print(g, "sum|tp diff| chat-chat", cc, "\n   16k-16k", bb, "\n   chat->16k", cb)
# pooled F1 over all repeats (item-repeat rows) and bootstrap over items of mean-over-repeats difference
rng = random.Random(1)
for g, m in (("detection:frame","f1"),("detection:frame","rec"),("claim","rec"),("detection:evidence","f1")):
    def stat(keys, s): return pool([D["runs"][k][i] for k in keys for i in s], g)[m]
    point = stat(BU, its) - stat(CH, its)
    point2 = stat(BU[1:], its) - stat(CH, its)
    bs=[]; bs2=[]
    for _ in range(2000):
        s=[rng.choice(its) for _ in its]
        bs.append(stat(BU,s)-stat(CH,s)); bs2.append(stat(BU[1:],s)-stat(CH,s))
    bs.sort(); bs2.sort()
    print(f"{g} {m}: all 3 16k vs 4 chat {point:+.3f} [{bs[50]:+.3f},{bs[1949]:+.3f}] | excluding dev-16k r0 {point2:+.3f} [{bs2[50]:+.3f},{bs2[1949]:+.3f}]")
