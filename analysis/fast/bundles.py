"""Episode-level co-occurrence (PMI) of topics and narratives, and verbatim-duplicate rates."""
import json, re, sys
import numpy as np, pandas as pd, pyarrow.parquet as pq
SCAN="/mnt/data2/podcast-data/fast-analysis/scan"; OUT="/home/felix/projects/podcast-misinfo/analysis/output/fast-analysis"
c = pq.read_table(f"{SCAN}/counts.parquet").to_pandas()
c = c[c.section.isin(["topics","narratives"])]
ep_lab = c.groupby(["episode_id","section","label"]).n_sent.sum().reset_index()
N = ep_lab.episode_id.nunique(); N_all = 132411
def pmi_table(section, min_eps=300, top=30, thresh=1):
    d = ep_lab[(ep_lab.section==section) & (ep_lab.n_sent>=thresh)]
    if section=="topics": d = d[d.label!="other_health_topic"]
    piv = pd.crosstab(d.episode_id, d.label).astype(bool)
    keep = piv.sum().sort_values(ascending=False); keep = keep[keep>=min_eps].index[:top]
    piv = piv[keep]
    co = piv.T.astype(int) @ piv.astype(int)
    p = piv.sum()/N_all
    pmi = pd.DataFrame(np.log2((co.values/N_all) / np.outer(p.values,p.values)), index=keep, columns=keep)
    for k in keep: pmi.loc[k,k] = np.nan
    # lift table for the strongest pairs
    pairs=[]
    for i,a in enumerate(keep):
        for b in keep[i+1:]:
            pairs.append((a,b,int(co.loc[a,b]),round(float(pmi.loc[a,b]),2)))
    pairs = sorted(pairs, key=lambda x:-x[3])
    return {"labels":list(keep), "episodes":[int(piv[k].sum()) for k in keep], "pmi":pmi.round(2).fillna(0).values.tolist(), "top_pairs":pairs[:25], "bottom_pairs":pairs[-15:]}
R = {"topics": pmi_table("topics", min_eps=2000, top=30, thresh=2), "narratives": pmi_table("narratives", min_eps=60, top=30, thresh=1)}
# narrative diversity per show
s = pq.read_table(f"{SCAN}/sentences.parquet", columns=["episode_id","labels","text"]).to_pandas()
ns = s[s.labels.str.contains("narratives:")].copy()
ns["norm"] = ns.text.str.lower().str.replace(r"[^a-z0-9 ]","",regex=True).str.replace(r"\s+"," ",regex=True).str.strip()
ns["narrs"] = ns.labels.str.findall(r"narratives:([a-z0-9_]+)")
nx = ns.explode("narrs")
dup = nx.groupby("narrs").agg(sentences=("norm","size"), distinct=("norm","nunique"))
dup["dup_share_pct"] = (100*(1-dup.distinct/dup.sentences)).round(1)
top_rep = nx.groupby(["narrs","norm"]).size().reset_index(name="n").sort_values("n",ascending=False)
dup["top_repeat"] = top_rep.groupby("narrs").first().reindex(dup.index)["norm"].str.slice(0,120)
dup["top_repeat_n"] = top_rep.groupby("narrs").first().reindex(dup.index)["n"]
R["narrative_dedup"] = dup.sort_values("sentences",ascending=False).reset_index().to_dict("records")
# overall: share of narrative sentences that are exact repeats
R["narrative_dedup_overall"] = {"sentences":int(len(ns)), "distinct":int(ns.norm.nunique()), "dup_share_pct": round(100*(1-ns.norm.nunique()/len(ns)),1)}
prof = json.load(open(f"{OUT}/corpus_profile.json")); shows = {p["podcast_id"]:p for p in prof["per_show"]}
import sqlite3; conn = sqlite3.connect("file:/home/felix/projects/podcast-misinfo/downloader/data/podcast_metadata.db?mode=ro", uri=True)
ep = pd.read_sql("select id episode_id, podcast_id from episodes", conn).set_index("episode_id")
nx = nx.join(ep, on="episode_id"); nx["show"] = nx.podcast_id.map(lambda p: shows.get(p,{}).get("title"))
div = nx.groupby("show").agg(narratives=("narrs","nunique"), sentences=("narrs","size"), episodes=("episode_id","nunique")).sort_values("narratives",ascending=False)
R["narrative_diversity"] = div.head(25).reset_index().to_dict("records")
json.dump(R, open(f"{OUT}/bundles.json","w"), default=lambda o: int(o) if isinstance(o,(np.integer,)) else float(o))
print("topics top pairs"); [print(p) for p in R["topics"]["top_pairs"][:15]]
print("narr top pairs"); [print(p) for p in R["narratives"]["top_pairs"][:20]]
print(R["narrative_dedup_overall"]); print(dup.sort_values("dup_share_pct",ascending=False).head(12)[["sentences","dup_share_pct","top_repeat_n","top_repeat"]].to_string())
print(div.head(12).to_string())
