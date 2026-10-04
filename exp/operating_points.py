"""For each screen: the smallest corpus pass rate that keeps a target share of the
reference labeler's substantive topic detections and claims, and what else it keeps."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from screens import read_scores, run_atoms, retention, CLASSES

ref = run_atoms(Path("exp/corpus/v8-high"))
ids = [w for w in Path("exp/corpus/sample2000.ids").read_text().split() if w in ref]
targets = [0.95, 0.98, 0.99]
key = lambda a: CLASSES["topic (substantive)"](a) or a["kind"] == "claim"  # noqa: E731
print(f"{len(ids)} corpus windows; reference = DeepSeek-high v8\n")
print("| screen | target | threshold | pass rate | substantive topic | claim | passing topic | ad topic | product | all atoms |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for name in sys.argv[1:]:
    scores = read_scores(name)
    values = sorted({scores.get(w, 0.0) for w in ids}, reverse=True)
    for t in targets:
        best = None
        for v in values:  # descending: first threshold reaching the target has the lowest pass rate
            r = retention(scores, ref, v, ids)
            kept = (r["topic (substantive)"][0] * r["topic (substantive)"][1] + r["claim"][0] * r["claim"][1]) / (r["topic (substantive)"][1] + r["claim"][1])
            if kept >= t:
                best = (v, r)
                break
        if best is None:
            continue
        v, r = best
        f = lambda c: f"{r[c][0]:.3f}"  # noqa: E731
        print(f"| {name} | {t} | {v:.3g} | {r['pass_rate']:.3f} | {f('topic (substantive)')} | {f('claim')} | {f('topic (passing)')} | {f('topic (ad)')} | {f('product')} | {f('all atoms')} |")
