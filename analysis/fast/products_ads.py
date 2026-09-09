"""Product mentions and sponsor reads: chart-ready tables (analysis/output/fast-analysis/products_ads.json)."""
import json, os, re, sqlite3, string, sys
import numpy as np
import pandas as pd

ROOT = "/home/felix/projects/podcast-misinfo"
DB = f"{ROOT}/downloader/data/podcast_metadata.db"
SCAN = os.environ.get("SCAN_OUT", "/mnt/data2/podcast-data/fast-analysis/scan")
OUT = f"{ROOT}/analysis/output/fast-analysis"
LEX = json.load(open(os.environ.get("SCAN_LEX", f"{ROOT}/analysis/fast/lexicon.json")))
LIVE_START = "2025-10-13"
WIN = 4

PRODUCTS = LEX["products"]
HEALTH_PRODUCTS = {k for k, v in PRODUCTS.items() if v.get("health_related")}
CTRL_PRODUCTS = {k for k, v in PRODUCTS.items() if not v.get("health_related")}

# ---------- load ----------
prof = json.load(open(f"{OUT}/corpus_profile.json"))
shows = pd.DataFrame(prof["per_show"]).set_index("podcast_id")
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ep = pd.read_sql("select id episode_id, podcast_id, substr(published_date,1,10) pub from episodes", conn)
conn.close()
ep["pub"] = pd.to_datetime(ep.pub, errors="coerce")
ep.loc[ep.pub < "1995-01-01", "pub"] = pd.NaT
ep["month"] = ep.pub.dt.to_period("M").astype(str)
ep["live"] = ep.pub >= LIVE_START
ep = ep.join(shows[["title", "genre_group", "on_health_chart"]].rename(columns={"title": "show"}), on="podcast_id")

epi = pd.read_parquet(f"{SCAN}/episodes.parquet").set_index("episode_id")
epi = epi.join(ep.set_index("episode_id"))
epi = epi[epi.n_sent > 0]
epi["genre_group"] = epi.genre_group.fillna("unknown")
epi["on_health_chart"] = epi.on_health_chart.fillna(False).astype(bool)

sents = pd.read_parquet(f"{SCAN}/sentences.parquet")
sents = sents[sents.episode_id.isin(epi.index)].reset_index(drop=True)
print(f"loaded {len(epi)} episodes, {len(sents)} hit sentences", file=sys.stderr)

lab = sents.labels
sents["is_comm"] = lab.str.contains("commercial:commercial", regex=False)
sents["is_health"] = lab.str.contains(r"topics:(?!other_health_topic)", regex=True)
sents["is_evidence"] = lab.str.contains("evidence:", regex=False)
sents["is_strength"] = lab.str.contains("evidence:evidence_strength_claim", regex=False)
sents["is_study"] = lab.str.contains("evidence:scientific_study_citation", regex=False)
sents["is_absolute"] = lab.str.contains("certainty:absolute", regex=False)
sents["has_product"] = lab.str.contains("products:", regex=False)

MULT = np.int64(epi.n_sent.max() + 10)
sents["key"] = sents.episode_id.to_numpy(np.int64) * MULT + sents.sent_idx.to_numpy(np.int64)

meta = epi[["podcast_id", "show", "genre_group", "on_health_chart", "month", "live", "n_sent"]]
sents = sents.join(meta, on="episode_id")


def pct(a, b):
    return round(100.0 * a / b, 3) if b else None


def per_k(a, b):
    return round(1000.0 * a / b, 3) if b else None


R = {"meta": {"live_start": LIVE_START, "window": WIN, "n_episodes": int(len(epi)),
              "n_sentences": int(epi.n_sent.sum()), "n_hit_sentences": int(len(sents)),
              "n_health_products": len(HEALTH_PRODUCTS), "n_control_products": len(CTRL_PRODUCTS)}}

# ================= 1. sponsor-read footprint =================
comm = sents[sents.is_comm]
ep_comm = comm.groupby("episode_id").size()
epi["comm_sents"] = ep_comm.reindex(epi.index).fillna(0).astype(int)
epi["has_comm"] = epi.comm_sents > 0

R["footprint"] = {
    "episodes_with_commercial_marker": int(epi.has_comm.sum()),
    "share_episodes_with_commercial_marker_pct": pct(epi.has_comm.sum(), len(epi)),
    "commercial_sentences": int(epi.comm_sents.sum()),
    "commercial_per_1000_sentences_overall": per_k(epi.comm_sents.sum(), epi.n_sent.sum()),
}

g = epi.groupby("genre_group").agg(episodes=("n_sent", "size"), sentences=("n_sent", "sum"),
                                   comm=("comm_sents", "sum"), eps_with=("has_comm", "sum"))
g["per_1000"] = 1000.0 * g.comm / g.sentences
g["share_episodes_pct"] = 100.0 * g.eps_with / g.episodes
R["footprint"]["by_genre"] = [
    {"genre_group": i, "episodes": int(r.episodes), "sentences": int(r.sentences),
     "commercial_sentences": int(r.comm), "commercial_per_1000": round(r.per_1000, 3),
     "share_episodes_with_ad_pct": round(r.share_episodes_pct, 2)}
    for i, r in g.sort_values("per_1000", ascending=False).iterrows()]

g2 = epi.groupby(["show", "genre_group", "on_health_chart"]).agg(
    episodes=("n_sent", "size"), sentences=("n_sent", "sum"), comm=("comm_sents", "sum"),
    eps_with=("has_comm", "sum"))
g2 = g2[g2.episodes >= 10].reset_index()
g2["per_1000"] = 1000.0 * g2.comm / g2.sentences
g2["share_episodes_pct"] = 100.0 * g2.eps_with / g2.episodes
R["footprint"]["top_shows"] = [
    {"show": r.show, "genre_group": r.genre_group, "on_health_chart": bool(r.on_health_chart),
     "episodes": int(r.episodes), "commercial_sentences": int(r.comm),
     "commercial_per_1000": round(r.per_1000, 3), "share_episodes_with_ad_pct": round(r.share_episodes_pct, 2)}
    for r in g2.sort_values("per_1000", ascending=False).head(25).itertuples()]

live = epi[epi.live.fillna(False)]
m = live.groupby("month").agg(episodes=("n_sent", "size"), sentences=("n_sent", "sum"), comm=("comm_sents", "sum"))
m = m[m.episodes >= 20]
R["footprint"]["monthly_live"] = [
    {"month": i, "episodes": int(r.episodes), "sentences": int(r.sentences),
     "commercial_sentences": int(r.comm), "commercial_per_1000": round(1000.0 * r.comm / r.sentences, 3)}
    for i, r in m.iterrows()]

# ================= 2. where ads sit =================
comm = comm.copy()
comm["decile"] = np.minimum(9, (comm.sent_idx / comm.n_sent * 10).astype(int))
sents["decile"] = np.minimum(9, (sents.sent_idx / sents.n_sent * 10).astype(int))
overall = comm.decile.value_counts().reindex(range(10), fill_value=0)
by_chart = comm.groupby("on_health_chart").decile.value_counts().unstack(fill_value=0).reindex(columns=range(10), fill_value=0)
R["ad_position"] = {
    "overall": [{"decile": int(d), "commercial_sentences": int(overall[d]),
                 "share_pct": pct(overall[d], overall.sum())} for d in range(10)],
    "health_chart_shows": [{"decile": int(d), "commercial_sentences": int(by_chart.loc[True, d]),
                            "share_pct": pct(by_chart.loc[True, d], by_chart.loc[True].sum())} for d in range(10)],
    "other_shows": [{"decile": int(d), "commercial_sentences": int(by_chart.loc[False, d]),
                     "share_pct": pct(by_chart.loc[False, d], by_chart.loc[False].sum())} for d in range(10)],
}

# ================= product long table =================
prod = sents.loc[sents.has_product, ["episode_id", "sent_idx", "key", "labels", "text", "podcast_id", "show",
                                     "genre_group", "on_health_chart", "is_comm", "is_health", "is_evidence",
                                     "is_absolute"]].copy()
prod["product"] = prod.labels.str.findall(r"products:([a-z0-9_]+)")
prod = prod.explode("product")
prod["health_related"] = prod["product"].isin(HEALTH_PRODUCTS)

# ================= 3. products =================
hp = prod[prod.health_related]
psum = hp.groupby("product").agg(sentences=("key", "size"), episodes=("episode_id", "nunique"),
                                 shows=("show", "nunique"))
psum["ad_cooccur_sentences"] = hp.groupby("product").is_comm.sum()
top_show = hp.groupby(["product", "show"]).episode_id.nunique().rename("eps")
top_show_share = top_show / top_show.groupby("product").sum()
psum["top_show_share_pct"] = (top_show_share.groupby("product").max() * 100).round(2)
psum["type"] = [PRODUCTS[p]["type"] for p in psum.index]
psum = psum.sort_values("episodes", ascending=False)
R["health_products"] = [
    {"product": i, "type": r.type, "sentences": int(r.sentences), "episodes": int(r.episodes),
     "shows": int(r.shows), "sentences_with_commercial_marker": int(r.ad_cooccur_sentences),
     "share_sentences_with_commercial_marker_pct": pct(r.ad_cooccur_sentences, r.sentences),
     "top_show_episode_share_pct": float(r.top_show_share_pct)}
    for i, r in psum.iterrows()]

# product x genre matrix (episodes)
mat = hp.groupby(["product", "genre_group"]).episode_id.nunique().unstack(fill_value=0)
top20 = psum.head(20).index
R["product_genre_matrix"] = {"genres": list(mat.columns),
                             "rows": [{"product": p, "episodes": [int(x) for x in mat.loc[p]]} for p in top20 if p in mat.index]}

# concentration: HHI over shows, min 20 episodes
conc = []
for p, grp in top_show.groupby(level=0):
    tot = grp.sum()
    if psum.loc[p, "episodes"] < 20:
        continue
    sh = (grp / tot).sort_values(ascending=False)
    conc.append({"product": p, "episodes": int(psum.loc[p, "episodes"]), "shows": int(len(sh)),
                 "top_show": sh.index[0][1], "top_show_share_pct": round(100 * sh.iloc[0], 2),
                 "top3_share_pct": round(100 * sh.head(3).sum(), 2), "hhi": round(float((sh ** 2).sum()), 4)})
conc.sort(key=lambda d: -d["hhi"])
R["health_product_concentration"] = conc[:25]

R["health_product_top_shows"] = []
for p in psum.head(15).index:
    sh = top_show.loc[p].sort_values(ascending=False)
    R["health_product_top_shows"].append({
        "product": p, "episodes": int(psum.loc[p, "episodes"]), "shows": int(psum.loc[p, "shows"]),
        "top3": [{"show": s, "episodes": int(n), "share_pct": round(100.0 * n / sh.sum(), 2)} for s, n in sh.head(3).items()]})

# distinct health products per episode, by genre
dpe = hp.groupby("episode_id")["product"].nunique()
epi["n_health_products"] = dpe.reindex(epi.index).fillna(0)
gd = epi.groupby("genre_group").agg(episodes=("n_health_products", "size"),
                                    mean_products=("n_health_products", "mean"),
                                    eps_with=("n_health_products", lambda s: (s > 0).sum()))
R["health_products_per_episode"] = [
    {"genre_group": i, "episodes": int(r.episodes), "mean_distinct_health_products": round(r.mean_products, 3),
     "share_episodes_naming_one_pct": pct(r.eps_with, r.episodes)}
    for i, r in gd.sort_values("mean_products", ascending=False).iterrows()]

# ================= 4. ad windows =================
def expand(keys, w=WIN):
    off = np.arange(-w, w + 1, dtype=np.int64)
    return np.unique((keys[:, None] + off[None, :]).ravel())

seed = sents.loc[sents.is_comm, "key"].to_numpy(np.int64)
win1 = expand(seed)
prod_keys = prod.key.to_numpy(np.int64)
secondary = np.intersect1d(prod_keys, win1)          # product mentions co-occurring with an ad marker
adwin = expand(np.union1d(seed, secondary))
sents["in_adwin"] = np.isin(sents.key.to_numpy(np.int64), adwin)
prod["in_adwin"] = np.isin(prod_keys, adwin)

hs = sents[sents.is_health]
R["ad_windows"] = {
    "anchor_sentences": int(len(np.union1d(seed, secondary))),
    "commercial_anchors": int(len(seed)),
    "product_anchors_added": int(len(secondary)),
    "matched_sentences_in_ad_windows": int(sents.in_adwin.sum()),
    "share_matched_sentences_in_ad_windows_pct": pct(sents.in_adwin.sum(), len(sents)),
    "health_topic_sentences": int(len(hs)),
    "health_topic_sentences_in_ad_windows": int(hs.in_adwin.sum()),
    "share_health_topic_sentences_in_ad_windows_pct": pct(hs.in_adwin.sum(), len(hs)),
    "evidence_sentences_in_ad_windows": int(sents[sents.is_evidence].in_adwin.sum()),
    "share_evidence_sentences_in_ad_windows_pct": pct(sents[sents.is_evidence].in_adwin.sum(), int(sents.is_evidence.sum())),
    "strength_claim_sentences_in_ad_windows": int(sents[sents.is_strength].in_adwin.sum()),
    "share_strength_claim_in_ad_windows_pct": pct(sents[sents.is_strength].in_adwin.sum(), int(sents.is_strength.sum())),
    "study_citation_sentences_in_ad_windows": int(sents[sents.is_study].in_adwin.sum()),
    "share_study_citation_in_ad_windows_pct": pct(sents[sents.is_study].in_adwin.sum(), int(sents.is_study.sum())),
    "absolute_certainty_sentences_in_ad_windows": int(sents[sents.is_absolute].in_adwin.sum()),
    "share_absolute_certainty_in_ad_windows_pct": pct(sents[sents.is_absolute].in_adwin.sum(), int(sents.is_absolute.sum())),
}

gh = hs.groupby("genre_group").in_adwin.agg(["size", "sum"])
R["ad_windows"]["health_in_adwin_by_genre"] = [
    {"genre_group": i, "health_topic_sentences": int(r["size"]), "in_ad_windows": int(r["sum"]),
     "share_pct": pct(r["sum"], r["size"])} for i, r in gh.sort_values("size", ascending=False).iterrows()]
ghc = hs.groupby("on_health_chart").in_adwin.agg(["size", "sum"])
R["ad_windows"]["health_in_adwin_by_chart"] = [
    {"on_health_chart": bool(i), "health_topic_sentences": int(r["size"]), "in_ad_windows": int(r["sum"]),
     "share_pct": pct(r["sum"], r["size"])} for i, r in ghc.iterrows()]

# most ad-borne topics
tl = sents.loc[sents.is_health, ["key", "labels", "in_adwin"]].copy()
tl["topic"] = tl.labels.str.findall(r"topics:([a-z0-9_]+)")
tl = tl.explode("topic")
tl = tl[tl.topic != "other_health_topic"]
tt = tl.groupby("topic").in_adwin.agg(["size", "sum"])
tt = tt[tt["size"] >= 200]
tt["share"] = 100.0 * tt["sum"] / tt["size"]
R["ad_borne_topics"] = [
    {"topic": i, "sentences": int(r["size"]), "in_ad_windows": int(r["sum"]), "share_pct": round(r.share, 2)}
    for i, r in tt.sort_values("share", ascending=False).iterrows()]

# ================= product neighbourhoods (Q4 rates + Q6 control) =================
neigh_rows = []
key_arr = sents.key.to_numpy(np.int64)
order = np.argsort(key_arr)
key_sorted = key_arr[order]
flags = {c: sents[c].to_numpy()[order] for c in ("is_health", "is_evidence", "is_strength", "is_study", "is_absolute", "in_adwin")}

for p, grp in prod.groupby("product"):
    nb = expand(grp.key.to_numpy(np.int64))
    pos = np.clip(np.searchsorted(key_sorted, nb), 0, len(key_sorted) - 1)
    idx = pos[key_sorted[pos] == nb]
    n = len(idx)
    if n < 100:
        continue
    row = {"product": p, "health_related": p in HEALTH_PRODUCTS, "type": PRODUCTS[p]["type"],
           "mentions": int(len(grp)), "episodes": int(grp.episode_id.nunique()), "shows": int(grp.show.nunique()),
           "neighbourhood_sentences": int(n)}
    for c, name in [("is_health", "health_topic"), ("is_evidence", "evidence"), ("is_strength", "strength_claim"),
                    ("is_study", "study_citation"), ("is_absolute", "absolute_certainty"), ("in_adwin", "in_ad_window")]:
        row[f"{name}_pct"] = pct(flags[c][idx].sum(), n)
    neigh_rows.append(row)
neigh = pd.DataFrame(neigh_rows)
R["product_neighbourhoods"] = neigh.sort_values("neighbourhood_sentences", ascending=False).to_dict("records")
R["product_evidence_leaders"] = neigh[neigh.health_related].sort_values("evidence_pct", ascending=False).head(20).to_dict("records")
R["product_absolute_leaders"] = neigh[neigh.health_related].sort_values("absolute_certainty_pct", ascending=False).head(20).to_dict("records")

ctrl = neigh[~neigh.health_related]
hlt = neigh[neigh.health_related]


def agg(df):
    tot = df.neighbourhood_sentences.sum()
    out = {"products": int(len(df)), "neighbourhood_sentences": int(tot)}
    for name in ("health_topic", "evidence", "strength_claim", "study_citation", "absolute_certainty"):
        w = (df[f"{name}_pct"] / 100 * df.neighbourhood_sentences).sum()
        out[f"{name}_pct"] = round(100.0 * w / tot, 3) if tot else None
    return out


def adwin_w(df):
    t = df.neighbourhood_sentences.sum()
    return round(float((df.in_ad_window_pct / 100 * df.neighbourhood_sentences).sum() / t * 100), 2) if t else None


R["summary"] = {
    "health_products_observed": int(hp["product"].nunique()),
    "episodes_naming_a_health_product": int((epi.n_health_products > 0).sum()),
    "share_episodes_naming_a_health_product_pct": pct((epi.n_health_products > 0).sum(), len(epi)),
    "mean_distinct_health_products_per_episode": round(float(epi.n_health_products.mean()), 3),
    "health_product_mention_sentences": int(len(hp)),
    "control_product_mention_sentences": int((~prod.health_related).sum()),
    "weighted_in_ad_window_pct_health": adwin_w(hlt),
    "weighted_in_ad_window_pct_control": adwin_w(ctrl),
}

R["control_baseline"] = {"health_products": agg(hlt), "control_products": agg(ctrl),
                         "control_detail": ctrl.sort_values("neighbourhood_sentences", ascending=False).to_dict("records")}

# ================= examples =================
cand = sents[sents.in_adwin & sents.is_health & (sents.is_evidence | sents.is_absolute)].copy()
cand = cand[cand.text.str.len().between(60, 240)]
# attach nearest product
pmap = {}
for p, grp in prod[prod.health_related].groupby("product"):
    for k in expand(grp.key.to_numpy(np.int64)):
        pmap.setdefault(int(k), p)
cand["product"] = cand.key.map(pmap)
cand = cand[cand["product"].notna()]
cand = cand.sort_values(["product", "key"])
examples, seen_p, seen_s = [], set(), set()
for p, grp in cand.groupby("product"):
    grp = grp.iloc[[len(grp) // 2]]  # median row per product, avoids extreme picks
    r = grp.iloc[0]
    examples.append({"product": p, "show": r.show, "genre_group": r.genre_group,
                     "text": r.text, "labels": r.labels, "n_candidates_for_product": int(len(cand[cand["product"] == p]))})
examples.sort(key=lambda d: -d["n_candidates_for_product"])
picked, shows_used = [], set()
for e in examples:
    if e["show"] in shows_used and len(picked) < 12:
        continue
    picked.append(e); shows_used.add(e["show"])
    if len(picked) == 12:
        break
for e in examples:
    if len(picked) == 12:
        break
    if e not in picked:
        picked.append(e)
R["ad_health_claim_examples"] = picked[:12]

# ================= 5. repetition =================
punct = str.maketrans("", "", string.punctuation)


def norm(s):
    return re.sub(r"\s+", " ", s.lower().translate(punct)).strip()


rep = []
for p in psum.head(10).index:
    d = prod[prod["product"] == p]
    per_show_eps = d.groupby("show").episode_id.nunique()
    n = d.text.map(norm)
    vc = n.value_counts()
    dupes = n.map(vc)
    top = vc.head(3)
    rep.append({"product": p, "sentences": int(len(d)), "episodes": int(d.episode_id.nunique()),
                "shows": int(len(per_show_eps)), "median_episodes_per_show": float(per_show_eps.median()),
                "max_episodes_in_one_show": int(per_show_eps.max()),
                "duplicate_sentence_share_pct": pct((dupes > 1).sum(), len(d)),
                "distinct_sentence_share_pct": pct(vc.size, len(d)),
                "top_repeated": [{"text": t[:200], "count": int(c)} for t, c in top.items()]})
R["repetition"] = rep


def default(o):
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, np.floating): return float(o)
    if isinstance(o, (np.bool_, bool)): return bool(o)
    raise TypeError(type(o))


json.dump(R, open(f"{OUT}/products_ads.json", "w"), indent=1, default=default)
print("wrote", f"{OUT}/products_ads.json", file=sys.stderr)
