"""For frames found by the unbudgeted run(s) but lost by the budget run: miss class per gold label, substitutions."""
import sys; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
from analysis.benchmark.matching import Atom, GoldAtom, overlaps
from analysis.benchmark.scoring import _miss_class
def go(C, Bs, label):
    cls = defaultdict(Counter); subs = Counter(); n = 0
    for Bk in Bs:
        for i in set(D["runs"][Bk]) & set.intersection(*[set(D["runs"][k]) for k in C]):
            preds = [Atom(kind=p["kind"], start=p["start"], end=p["end"], axis=p["axis"], label=p["label"]) for p in D["runs"][Bk][i]["preds"]]
            for g in D["gold"][i]:
                if g["kind"] != "detection" or g["axis"] != "frame" or g["tier"] != "required": continue
                if not any(g["gold_id"] in D["runs"][k][i]["matched_gold"] for k in C) or g["gold_id"] in D["runs"][Bk][i]["matched_gold"]: continue
                ga = GoldAtom(**{k: (tuple(v) if k in ("tight","envelope") else v) for k, v in g.items()})
                c = _miss_class(ga, preds); n += 1
                cls[g["label"].split(":")[-1]][c] += 1
                if c == "same_axis_wrong_label":
                    for p in preds:
                        if p.kind == "detection" and p.axis == "frame" and overlaps((p.start, p.end), ga.envelope):
                            subs[(g["label"].split(":")[-1], p.label.split(":")[-1])] += 1
    print(f"## {label}: {n} lost frame gold")
    for lab, c in sorted(cls.items(), key=lambda kv: -sum(kv[1].values()))[:10]: print("  ", lab, dict(c))
    print("   substitutions:", subs.most_common(10))
go([("dev-high-chat-lenient",0)], [("dev-high-budget16k-lenient",0)], "dev chat r0 -> 16k")
go([("dev-high-chat-lenient",0)], [("dev-high-chat-lenient",1)], "dev chat r0 -> chat r1 (noise)")
go([("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)], [("s70-high-budget8k-lenient",0),("s70-high-budget8k-lenient",1)], "s70 either chat -> 8k (both repeats pooled)")
