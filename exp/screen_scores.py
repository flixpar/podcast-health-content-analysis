"""Turn an xlabel screen run into an exp/scores file: none=0, passing=1, substantive=2 (+0.5 if an ad).

    python exp/screen_scores.py exp/corpus/ds-screen-bench exp/corpus/ds-screen --name ds-screen
"""
import argparse, json, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from screens import write_scores

LEVEL = {"none": 0.0, "passing": 1.0, "substantive": 2.0}
p = argparse.ArgumentParser(); p.add_argument("runs", nargs="+"); p.add_argument("--name", required=True)
a = p.parse_args()
scores = {}
for run in a.runs:
    con = sqlite3.connect(f"file:{run}/repeat_0/labels.sqlite?mode=ro", uri=True)
    for w, r in con.execute("SELECT window_id, result_json FROM window_labels"):
        s = json.loads(r)["screen"]
        scores[w] = LEVEL.get(s.get("health"), 0.0) + (0.5 if s.get("ad") else 0.0)
write_scores(a.name, scores)
print(a.name, len(scores))
