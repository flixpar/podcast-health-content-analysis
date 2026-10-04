"""Dump transcript fragment, lost gold atom and each run's overlapping output for chosen windows."""
import sys; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
item, cset, bset, kinds = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
RUNSETS = {"dev": [("dev-high-chat-lenient",0),("dev-high-chat-lenient",1)], "s70": [("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)],
           "b16": [("dev-high-budget16k-lenient",0)], "s16": [("s70-high-budget16k-lenient",r) for r in (0,1)], "s8": [("s70-high-budget8k-lenient",r) for r in (0,1)], "s4": [("s70-high-budget4k-lenient",r) for r in (0,1)]}
C, B = RUNSETS[cset], RUNSETS[bset]
units = D["items"][item]["units"]
print(item, D["items"][item]["stratum"], D["items"][item]["podcast_title"], "|", D["items"][item]["episode_title"][:80], "| units", len(units))
for k in C + B:
    r = D["runs"][k][item]; res = r["result"]
    print(f"  {k}: reasoning {r['usage']['reasoning']} det {len(res['detections'])} frames {sum(d['axis']=='frame' for d in res['detections'])} claims {len(res['verification_candidates'])} counts frame tp {r['counts']['detection:frame']['tp']} claim tp {r['counts']['claim']['tp']}")
for g in D["gold"][item]:
    gk = g["axis"] if g["kind"] == "detection" else g["kind"]
    if gk not in kinds or g["tier"] != "required": continue
    if not (all(g["gold_id"] in D["runs"][k][item]["matched_gold"] for k in C) and not any(g["gold_id"] in D["runs"][k][item]["matched_gold"] for k in B)): continue
    t0, t1 = g["tight"]; e0, e1 = g["envelope"]
    print(f"\n  GOLD {g['gold_id']} {g['label'] or 'claim'} tight {t0}-{t1} env {e0}-{e1} support {g['support']} annot {g['annotators']} votes {g['votes']}")
    print("   claim_texts:", g["claim_texts"][:2]); print("   quotes:", g["quotes"][:2])
    print("   TEXT:", " ".join(f"[{j}] {units[j]['text']}" for j in range(max(0, t0), min(len(units), t1 + 1)))[:700])
    for k in C + B:
        ov = [p for p in D["runs"][k][item]["preds"] if p["kind"] == g["kind"] and not (p["end"] < e0 or p["start"] > e1) and (g["kind"] != "detection" or True)]
        print(f"   -- {k[0][:26]} r{k[1]}:")
        for p in ov:
            if p["kind"] == "detection":
                print(f"      det {p['axis']}:{p['label'].split(':')[-1]} {p['start']}-{p['end']} role={p['attributes'].get('discourse_role')} gold={p['gold_id']} q=\"{p['quote'][:90]}\"")
            else:
                print(f"      claim {p['start']}-{p['end']} type={p['attributes'].get('claim_type')} gold={p['gold_id']} \"{p['claim_text'][:110]}\"")
