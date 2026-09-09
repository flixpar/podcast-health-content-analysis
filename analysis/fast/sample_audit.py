"""Draw a blinded precision-audit sample of hit sentences per label."""
import os, sys, json
import pandas as pd, pyarrow.parquet as pq
SCAN = os.environ.get("SCAN_OUT", "/mnt/data2/podcast-data/fast-analysis/scan")
OUT = "/home/felix/projects/podcast-misinfo/analysis/output/fast-analysis"
n_per = int(sys.argv[1]) if len(sys.argv) > 1 else 20
s = pq.read_table(f"{SCAN}/sentences.parquet", columns=["episode_id", "labels", "text"]).to_pandas()
s = s[s.text.str.len() > 40]
lab = s.assign(l=s.labels.str.split("|")).explode("l")
rows = []
for l, grp in lab.groupby("l"):
    sec = l.split(":")[0]
    if sec in ("certainty", "commercial"):
        continue
    k = n_per if sec in ("narratives", "frames", "evidence", "distrust", "correction") else max(8, n_per // 2)
    for r in grp.sample(min(k, len(grp)), random_state=11).itertuples():
        rows.append({"label": l, "episode_id": int(r.episode_id), "text": r.text})
df = pd.DataFrame(rows)
df.to_csv(f"{OUT}/audit_sample.csv", index=False)
print(len(df), "rows,", df.label.nunique(), "labels")
