import os, pickle, sys
from collections import Counter, defaultdict
PKL = os.environ.get("TB_PKL") or "benchmark/runs/analysis/tb.pkl"
D = pickle.load(open(PKL, "rb"))
GROUPS = ("detection:topic", "detection:frame", "detection:evidence", "claim", "product")
def pool(rows, group):
    tp = sum(r["counts"][group]["tp"] for r in rows); fp = sum(r["counts"][group]["fp"] for r in rows); fn = sum(r["counts"][group]["fn"] for r in rows)
    req = sum(r["counts"][group]["required"] for r in rows)
    f1 = 2*tp/(2*tp+fp+fn) if tp+fp+fn else float("nan")
    rec = tp/(tp+fn) if tp+fn else float("nan")
    return dict(tp=tp, fp=fp, fn=fn, pred=sum(r["counts"][group]["pred"] for r in rows), f1=f1, rec=rec, prec=tp/(tp+fp) if tp+fp else float("nan"))
def run(name, k): return D["runs"][(name, k)]
