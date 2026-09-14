"""Regime classification per label from sva_labels.json (written by sva_tables.py)."""
import json
from collections import defaultdict
rows = json.load(open("sva_labels.json"))
def regime(r):
    A, C, S = r["cross"], r["vs_ann"], r["self"]
    if A is None or C is None or S is None or r["req"] < 5:
        return None
    gap = A - C
    if A < 0.55:
        return "R1 ambiguous spec (cross-family F1 < 0.55)"
    if gap <= 0.05:
        return "R2 clear, DS at annotator level"
    if S >= 0.65:
        return "R3 clear, DS below and self-consistent (systematic)"
    return "R4 clear, DS below and unstable (noise)"
vol = defaultdict(int); labs = defaultdict(list)
for r in rows:
    g = regime(r)
    if g is None:
        continue
    vol[g] += r["req"]; labs[g].append((r["req"], r["label"].replace("topic:", "t:").replace("cross_cutting:", "x:"), r["cross"], r["self"], r["vs_ann"]))
tot = sum(vol.values())
for g in sorted(vol):
    print(f"{g}: labels {len(labs[g])}, required {vol[g]} ({vol[g]/tot:.0%})")
    print("   ", "; ".join(f"{l} ({n}, A={a:.2f} S={s:.2f} C={c:.2f})" for n, l, a, s, c in sorted(labs[g], reverse=True)))
# same but by group, detections only
bygrp = defaultdict(lambda: defaultdict(int))
for r in rows:
    g = regime(r)
    if g: bygrp[r["group"]][g[:2]] += r["req"]
print({k: dict(v) for k, v in bygrp.items()})
