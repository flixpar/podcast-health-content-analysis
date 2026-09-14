"""Are lost gold atoms in later parts of the window?"""
import sys; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
import statistics as st
def rt(key, i): return D["runs"][key][i]["usage"]["reasoning"]
def pos_table(base_keys, cand_keys, label, only=None):
    items = sorted(set.intersection(*[set(D["runs"][k]) for k in base_keys + cand_keys]))
    if only: items = [i for i in items if only(i)]
    print(f"## {label} ({len(items)} windows): required gold, share found by thirds of the window (base mean -> cand mean)")
    for grp in ("detection:frame", "detection:evidence", "claim", "detection:topic"):
        cells = []
        for third in range(3):
            n = 0; fb = 0.0; fc = 0.0
            for i in items:
                nu = len(D["items"][i]["units"])
                for g in D["gold"][i]:
                    gg = f"detection:{g['axis']}" if g["kind"] == "detection" else g["kind"]
                    if gg != grp or g["tier"] != "required": continue
                    mid = (g["tight"][0] + g["tight"][1]) / 2
                    if min(2, int(3 * mid / nu)) != third: continue
                    n += 1
                    fb += st.mean(g["gold_id"] in D["runs"][k][i]["matched_gold"] for k in base_keys)
                    fc += st.mean(g["gold_id"] in D["runs"][k][i]["matched_gold"] for k in cand_keys)
            cells.append(f"T{third+1} n{n} {fb/n:.2f}->{fc/n:.2f}" if n else f"T{third+1} n0")
        print("  ", grp.split(":")[-1], " | ".join(cells))
C = [("dev-high-chat-lenient",0),("dev-high-chat-lenient",1)]; B = [("dev-high-budget16k-lenient",0)]
pos_table(C, B, "dev 16k all")
pos_table(C, B, "dev 16k, unbudgeted needed >24k", only=lambda i: st.mean(rt(k,i) for k in C) > 24000)
pos_table([C[0]], [C[1]], "dev noise chat r0 -> r1")
S = [("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)]
for b in (16, 8, 4):
    pos_table(S, [(f"s70-high-budget{b}k-lenient",r) for r in (0,1)], f"s70 {b}k")
# predicted atom positions: share of frame/claim predictions in the last third, windows needing >24k
for keys, nm in ((C,"dev chat"),(B,"dev 16k"),(S,"s70 chat"),([("s70-high-budget8k-lenient",r) for r in (0,1)],"s70 8k"),([("s70-high-budget4k-lenient",r) for r in (0,1)],"s70 4k")):
    its = [i for i in D["runs"][keys[0]] if st.mean(rt(k,i) for k in (C if nm.startswith("dev") else S)) > 24000]
    for kind in ("frame","claim"):
        ps=[]
        for k in keys:
            for i in its:
                nu=len(D["items"][i]["units"])
                for p in D["runs"][k][i]["preds"]:
                    if (p["kind"]=="claim" and kind=="claim") or (p["kind"]=="detection" and p["axis"]==kind):
                        ps.append((p["start"]+p["end"])/2/nu)
        print(nm, kind, "n/window", round(len(ps)/len(keys)/len(its),2), "share in last third", round(sum(x>=2/3 for x in ps)/len(ps),3), "mean rel pos", round(st.mean(ps),3))
