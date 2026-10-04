"""Attribute agreement, span IoU/length and position of lost gold within the window."""
import sys; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
from analysis.benchmark.matching import iou
import statistics as st
def plural(g, a):
    v = g["votes"].get(a) or {}
    return max(sorted(v), key=lambda x: v[x]) if v else None
KEYS = [("dev-high-chat-lenient",0),("dev-high-chat-lenient",1),("dev-high-budget16k-lenient",0)] + [("s70-high-chat-lenient",r) for r in (0,1)] + [(f"s70-high-budget{b}k-lenient",r) for b in (16,12,8,4) for r in (0,1)]
print("key | group | matched n | discourse_role exact | relevance exact | claim_type exact | certainty exact | mean IoU | mean pred span len | preds/window | frames on claims")
for key in KEYS:
    rows = D["runs"][key]
    for grp in ("detection:frame", "detection:evidence", "detection:topic", "claim"):
        n = dr = rel = ct = cert = 0; ious = []; lens = []
        for iid, row in rows.items():
            gmap = {g["gold_id"]: g for g in D["gold"][iid]}
            for p in row["preds"]:
                pg = f"detection:{p['axis']}" if p["kind"] == "detection" else p["kind"]
                if pg != grp: continue
                lens.append(p["end"] - p["start"] + 1)
                if not p["gold_id"]: continue
                g = gmap[p["gold_id"]]
                if g["tier"] not in ("required", "acceptable"): continue
                n += 1
                dr += p["attributes"].get("discourse_role") == plural(g, "discourse_role")
                rel += p["attributes"].get("relevance") == plural(g, "relevance")
                if grp == "claim":
                    ct += p["attributes"].get("claim_type") == plural(g, "claim_type")
                    cert += p["attributes"].get("expressed_certainty") == plural(g, "expressed_certainty")
                else:
                    ious.append(iou((p["start"], p["end"]), tuple(g["tight"])))
        nw = len(rows)
        print(key[0][:26], key[1], grp.split(":")[-1], n, f"{dr/n:.3f}", f"{rel/n:.3f}", f"{ct/n:.3f}" if grp=="claim" else "", f"{cert/n:.3f}" if grp=="claim" else "", f"{st.mean(ious):.3f}" if ious else "", f"{st.mean(lens):.2f}", f"{len(lens)/nw:.2f}")
    # frame ids attached to claims
    fc = sum(len(p["labels"].get("frame", [])) for r in rows.values() for p in r["preds"] if p["kind"] == "claim")
    nc = sum(1 for r in rows.values() for p in r["preds"] if p["kind"] == "claim")
    print("   claim frame_ids per claim", f"{fc/nc:.3f}", "evidence ids per claim", f"{sum(len(p['labels'].get('evidence', [])) for r in rows.values() for p in r['preds'] if p['kind']=='claim')/nc:.3f}")
