"""List robust losses: required gold found by every unbudgeted repeat and missed by the budget run(s)."""
import sys, json; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
import statistics as st
mode = sys.argv[1]
if mode == "dev":
    C = [("dev-high-chat-lenient",0),("dev-high-chat-lenient",1)]; B = [("dev-high-budget16k-lenient",0)]
else:
    C = [("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)]; B = [(f"s70-high-budget{mode}k-lenient",r) for r in (0,1)]
kinds = sys.argv[2].split(",")
items = sorted(set.intersection(*[set(D["runs"][k]) for k in C + B]))
per_item = defaultdict(list)
for i in items:
    for g in D["gold"][i]:
        gg = g["axis"] if g["kind"] == "detection" else g["kind"]
        if gg not in kinds or g["tier"] != "required": continue
        if all(g["gold_id"] in D["runs"][k][i]["matched_gold"] for k in C) and not any(g["gold_id"] in D["runs"][k][i]["matched_gold"] for k in B):
            per_item[i].append(g)
for i, gs in sorted(per_item.items(), key=lambda kv: -len(kv[1])):
    need = st.mean(D["runs"][k][i]["usage"]["reasoning"] for k in C)
    print(f"{i} {D['items'][i]['stratum']} units={len(D['items'][i]['units'])} words={D['items'][i]['word_count']} need={need:.0f} budget_rt={[D['runs'][k][i]['usage']['reasoning'] for k in B]} lost={len(gs)} "
          f"counts C frame/claim tp {[ (D['runs'][k][i]['counts']['detection:frame']['tp'], D['runs'][k][i]['counts']['claim']['tp']) for k in C]} B {[ (D['runs'][k][i]['counts']['detection:frame']['tp'], D['runs'][k][i]['counts']['claim']['tp']) for k in B]}")
    for g in gs:
        print("   ", g["label"] or "claim", g["tight"], (g["claim_texts"] or g["quotes"] or [""])[0][:110])
