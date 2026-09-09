"""Turn the scan output into report tables (analysis/output/fast-analysis/report_data.json)."""
import json, os, sqlite3, sys, random
from collections import defaultdict
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = "/home/felix/projects/podcast-misinfo"
DB = f"{ROOT}/downloader/data/podcast_metadata.db"
SCAN = os.environ.get("SCAN_OUT", "/mnt/data2/podcast-data/fast-analysis/scan")
OUT = f"{ROOT}/analysis/output/fast-analysis"
LEX = json.load(open(os.environ.get("SCAN_LEX", f"{ROOT}/analysis/fast/lexicon.json")))
LIVE_START = "2025-10-13"
random.seed(7)

# ---------- load ----------
prof = json.load(open(f"{OUT}/corpus_profile.json"))
shows = pd.DataFrame(prof["per_show"]).set_index("podcast_id")
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ep = pd.read_sql("select e.id episode_id, e.podcast_id, e.title, substr(e.published_date,1,10) pub from episodes e", conn)
ep["pub"] = pd.to_datetime(ep.pub, errors="coerce")
ep.loc[ep.pub < "1995-01-01", "pub"] = pd.NaT
ep["month"] = ep.pub.dt.to_period("M").astype(str)
ep["year"] = ep.pub.dt.year
ep["live"] = ep.pub >= LIVE_START
ep = ep.join(shows[["title", "genre_group", "on_health_chart"]].rename(columns={"title": "show"}), on="podcast_id")

epi = pq.read_table(f"{SCAN}/episodes.parquet").to_pandas().set_index("episode_id")
epi = epi.join(ep.set_index("episode_id"))
epi = epi[epi.n_sent > 0]
for c in ("n_sent", "n_words", "n_seg"):
    epi[c] = epi[c].astype("int64")
counts = pq.read_table(f"{SCAN}/counts.parquet").to_pandas()
sents = pq.read_table(f"{SCAN}/sentences.parquet").to_pandas()
print("loaded", len(epi), len(counts), len(sents), file=sys.stderr)

# label-level (dedupe multiple terms of the same label in one sentence: use sentence table)
lab = sents[["episode_id", "labels"]].copy()
lab["labels"] = lab.labels.str.split("|")
lab = lab.explode("labels")
lab[["section", "label"]] = lab.labels.str.split(":", n=1, expand=True)
lab = lab.drop(columns="labels")
ep_lab = lab.groupby(["episode_id", "section", "label"]).size().rename("n").reset_index()
ep_lab = ep_lab.join(epi[["n_sent", "n_words", "podcast_id", "show", "genre_group", "on_health_chart", "month", "year", "live"]], on="episode_id")

TOPICS = [t for t in LEX["topics"] if t != "other_health_topic"]
is_topic = (lab.section == "topics") & (lab.label != "other_health_topic")
health_sent_ids = lab[is_topic].groupby("episode_id").size()  # not unique sentences yet
# unique health sentences per episode
s_topic = sents[sents.labels.str.contains(r"(?:^|\|)topics:(?!other_health_topic)", regex=True)]
epi["health_sents"] = s_topic.groupby("episode_id").size().reindex(epi.index).fillna(0).astype(int)
epi["health_density"] = epi.health_sents / epi.n_sent
sents["is_health"] = sents.index.isin(s_topic.index)

R = {"meta": {"live_start": LIVE_START, "n_episodes": int(len(epi)), "n_sentences": int(epi.n_sent.sum()),
              "n_words": int(epi.n_words.sum()), "n_hit_sentences": int(len(sents)),
              "n_health_sentences": int(epi.health_sents.sum())}}

def pct(a, b):
    return round(100.0 * a / b, 2) if b else None

# ---------- A. where health talk happens ----------
g = epi.groupby("genre_group").agg(n_ep=("n_sent", "size"), n_sent=("n_sent", "sum"), health=("health_sents", "sum"), words=("n_words", "sum"))
g["share_words_pct"] = (100 * g.words / g.words.sum()).round(1)
g["share_health_pct"] = (100 * g.health / g.health.sum()).round(1)
g["health_per_1k_sent"] = (1000 * g.health / g.n_sent).round(1)
R["health_by_genre"] = g.reset_index().sort_values("share_health_pct", ascending=False).to_dict("records")
hc = epi.groupby("on_health_chart").agg(n_sent=("n_sent", "sum"), health=("health_sents", "sum"), words=("n_words", "sum"))
R["health_by_chart"] = {str(k): {"share_words_pct": pct(v.words, hc.words.sum()), "share_health_pct": pct(v.health, hc.health.sum()),
                                  "health_per_1k_sent": round(1000 * v.health / v.n_sent, 1)} for k, v in hc.iterrows()}
sh = epi.groupby(["podcast_id"]).agg(show=("show", "first"), genre=("genre_group", "first"), on_health_chart=("on_health_chart", "first"),
                                     n_ep=("n_sent", "size"), n_sent=("n_sent", "sum"), health=("health_sents", "sum"),
                                     ep_health_heavy=("health_density", lambda s: int((s > 0.10).sum())))
sh["health_per_1k_sent"] = (1000 * sh.health / sh.n_sent).round(1)
sh["share_health_pct"] = (100 * sh.health / sh.health.sum()).round(2)
sh["pct_ep_health_heavy"] = (100 * sh.ep_health_heavy / sh.n_ep).round(1)
sh = sh.sort_values("health", ascending=False)
sh["cum_share_pct"] = sh.share_health_pct.cumsum().round(1)
R["shows"] = sh.reset_index().to_dict("records")
R["health_concentration"] = {"top10_share_pct": round(float(sh.share_health_pct.head(10).sum()), 1),
                             "top20_share_pct": round(float(sh.share_health_pct.head(20).sum()), 1),
                             "shows_to_50pct": int((sh.cum_share_pct < 50).sum() + 1),
                             "non_health_chart_share_pct": pct(sh[~sh.on_health_chart.astype(bool)].health.sum(), sh.health.sum())}
# episode-level distribution of health density
R["health_density_hist"] = {"bins": [0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.01],
                            "counts": np.histogram(epi.health_density, bins=[0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.01])[0].tolist(),
                            "pct_ep_any_health": pct((epi.health_sents > 0).sum(), len(epi)),
                            "pct_ep_over_5pct": pct((epi.health_density > 0.05).sum(), len(epi)),
                            "pct_ep_over_20pct": pct((epi.health_density > 0.2).sum(), len(epi))}

# ---------- B. topic prevalence ----------
def label_table(section, exclude=()):
    d = ep_lab[(ep_lab.section == section) & (~ep_lab.label.isin(exclude))]
    t = d.groupby("label").agg(sentences=("n", "sum"), episodes=("episode_id", "nunique"), shows=("podcast_id", "nunique"))
    t["pct_episodes"] = (100 * t.episodes / len(epi)).round(1)
    t["per_million_sent"] = (1e6 * t.sentences / epi.n_sent.sum()).round(1)
    # top shows by sentence share
    top = d.groupby(["label", "show"]).n.sum().reset_index().sort_values("n", ascending=False)
    ts = {}
    for r in top.itertuples():
        ts.setdefault(r.label, [])
        if len(ts[r.label]) < 5:
            ts[r.label].append((r.show, int(r.n)))
    t["top_shows"] = pd.Series({k: ts.get(k, []) for k in t.index}, dtype=object) if len(t) else pd.Series(dtype=object)
    lv = d[d.live].groupby("label").n.sum()
    t["live_sentences"] = lv.reindex(t.index).fillna(0).astype(int)
    hc_ = d[d.on_health_chart.astype(bool)].groupby("label").n.sum().reindex(t.index).fillna(0)
    t["pct_from_health_chart"] = (100 * hc_ / t.sentences).round(1)
    pol = d[d.genre_group == "news_politics"].groupby("label").n.sum().reindex(t.index).fillna(0)
    t["pct_from_news_politics"] = (100 * pol / t.sentences).round(1)
    return t.sort_values("sentences", ascending=False)

R["topics"] = label_table("topics", exclude=("other_health_topic",)).reset_index().to_dict("records")
R["frames"] = label_table("frames").reset_index().to_dict("records")
R["evidence"] = label_table("evidence").reset_index().to_dict("records")
R["narratives"] = label_table("narratives").reset_index().to_dict("records")
R["products"] = label_table("products").reset_index().to_dict("records")

# topic x genre heatmap (per 10k sentences)
tg = ep_lab[(ep_lab.section == "topics") & (ep_lab.label != "other_health_topic")].groupby(["label", "genre_group"]).n.sum().unstack(fill_value=0)
gs = epi.groupby("genre_group").n_sent.sum()
R["topic_by_genre"] = {"genres": list(tg.columns), "rows": [{"topic": i, "vals": (1e4 * tg.loc[i] / gs[tg.columns]).round(2).tolist()} for i in tg.index]}

# ---------- C. narratives detail ----------
narr_sents = sents[sents.labels.str.contains("narratives:")].copy()
narr_sents["narrs"] = narr_sents.labels.str.findall(r"narratives:([a-z0-9_]+)")
narr_sents["corrected"] = narr_sents.labels.str.contains("frames:misinformation_correction_debunking")
narr_sents["distrust"] = narr_sents.labels.str.contains("frames:(?:big_pharma|suppressed_science|conspiracy_cover_up|government_institution|conflict_of_interest|anti_mainstream)")
narr_sents["commercial"] = narr_sents.labels.str.contains("frames:commercialization|commercial:")
nx = narr_sents.explode("narrs").join(epi[["show", "genre_group", "month", "year", "live", "on_health_chart"]], on="episode_id")
nd = {}
for k, grp in nx.groupby("narrs"):
    by_show = grp.groupby("show").size().sort_values(ascending=False)
    live = grp[grp.live]
    monthly = live.groupby("month").size()
    ex = grp.sample(min(4, len(grp)), random_state=1)
    nd[k] = {"sentences": int(len(grp)), "episodes": int(grp.episode_id.nunique()), "shows": int(grp.show.nunique()),
             "live_sentences": int(len(live)), "top_shows": [(s, int(n)) for s, n in by_show.head(6).items()],
             "top5_show_share_pct": pct(by_show.head(5).sum(), len(grp)),
             "pct_with_correction_marker": pct(grp.corrected.sum(), len(grp)),
             "pct_with_distrust_frame": pct(grp.distrust.sum(), len(grp)),
             "pct_health_chart_shows": pct(grp.on_health_chart.astype(bool).sum(), len(grp)),
             "genre_mix": grp.groupby("genre_group").size().to_dict(),
             "monthly_live": monthly.to_dict(),
             "yearly": grp.groupby("year").size().to_dict(),
             "examples": [{"show": r.show, "month": r.month, "text": r.text[:300]} for r in ex.itertuples()],
             "description": LEX["narratives"][k].get("description", ""), "note": LEX["narratives"][k].get("note", ""),
             "topic": LEX["narratives"][k].get("topic", "")}
R["narrative_detail"] = nd
# narrative x show matrix for top shows by narrative volume
top_shows_n = nx.groupby("show").size().sort_values(ascending=False).head(30).index
mat = nx[nx.show.isin(top_shows_n)].groupby(["show", "narrs"]).size().unstack(fill_value=0)
show_sent = epi.groupby("show").n_sent.sum()
R["narrative_show_matrix"] = {"shows": list(mat.index), "narratives": list(mat.columns),
                              "counts": mat.values.tolist(),
                              "per_million": (1e6 * mat.div(show_sent[mat.index], axis=0)).round(1).values.tolist()}
# narrative rate per show (all narratives combined) per million sentences, min 200 episodes... use min 50k sentences
ns = nx.groupby("show").size()
rate = (1e6 * ns / show_sent[ns.index]).round(1)
rate = rate[show_sent[ns.index] > 50000].sort_values(ascending=False)
R["narrative_rate_by_show"] = [{"show": s, "per_million_sent": float(v), "n": int(ns[s]), "genre": str(epi[epi.show == s].genre_group.iloc[0])} for s, v in rate.head(40).items()]
R["narrative_rate_by_genre"] = (1e6 * nx.groupby("genre_group").size() / gs).round(1).sort_values(ascending=False).to_dict()

# ---------- D. frames / evidence in health context ----------
hs = sents[sents.is_health].copy()
def frame_share(mask_regex, name):
    m = hs.labels.str.contains(mask_regex)
    by = hs[m].groupby("episode_id").size()
    e = epi[["show", "genre_group", "health_sents", "n_sent"]].copy()
    e[name] = by.reindex(e.index).fillna(0)
    return e
fr = frame_share(r"frames:(?:big_pharma|suppressed_science|conspiracy_cover_up|government_institution|conflict_of_interest|anti_mainstream|medical_freedom|anti_expert)", "distrust")
fr["study"] = frame_share(r"evidence:scientific_study_citation", "x")["x"]
fr["personal"] = frame_share(r"evidence:personal_experience_evidence", "x")["x"]
fr["weak"] = frame_share(r"evidence:weak_evidence_extrapolation", "x")["x"]
fr["strength"] = frame_share(r"evidence:evidence_strength_claim", "x")["x"]
fr["correction"] = frame_share(r"frames:misinformation_correction", "x")["x"]
fr["commercial"] = frame_share(r"commercial:|frames:commercialization", "x")["x"]
fr["absolute"] = frame_share(r"certainty:absolute", "x")["x"]
fr["hedged"] = frame_share(r"certainty:(?:hedged|speculative)", "x")["x"]
agg_cols = ["health_sents", "distrust", "study", "personal", "weak", "strength", "correction", "commercial", "absolute", "hedged"]
def rates(df):
    out = df[agg_cols].sum()
    r = {c: round(1000 * out[c] / out.health_sents, 1) for c in agg_cols[1:]}
    r["health_sents"] = int(out.health_sents)
    return r
R["frames_by_genre"] = {k: rates(v) for k, v in fr.groupby("genre_group")}
fs = fr.groupby("show")
R["frames_by_show"] = {k: rates(v) for k, v in fs if v.health_sents.sum() >= 3000}
R["frames_overall"] = rates(fr)

# ---------- E. commercialization ----------
com = sents[sents.labels.str.contains(r"commercial:|frames:commercialization")]
epi["commercial_sents"] = com.groupby("episode_id").size().reindex(epi.index).fillna(0).astype(int)
R["commercial"] = {"pct_episodes_with_ad_marker": pct((epi.commercial_sents > 0).sum(), len(epi)),
                   "mean_ad_sents_per_episode": round(float(epi.commercial_sents.mean()), 2),
                   "by_genre": epi.groupby("genre_group").apply(lambda d: round(float(d.commercial_sents.sum() / d.n_sent.sum() * 1000), 2)).to_dict()}
# position of commercial sentences within episode (deciles)
com = com.join(epi[["n_sent"]], on="episode_id")
com_pos = (com.sent_idx / com.n_sent.clip(lower=1)).clip(0, 0.999)
R["commercial"]["position_deciles"] = np.histogram(com_pos, bins=np.linspace(0, 1, 11))[0].tolist()
hpos = (hs.join(epi[["n_sent"]], on="episode_id").pipe(lambda d: d.sent_idx / d.n_sent.clip(lower=1))).clip(0, 0.999)
R["commercial"]["health_position_deciles"] = np.histogram(hpos, bins=np.linspace(0, 1, 11))[0].tolist()
# ad-adjacent health talk: health sentence within 3 sentences of a commercial marker
com_idx = set(zip(com.episode_id, com.sent_idx))
def near_ad(row):
    return any((row.episode_id, row.sent_idx + d) in com_idx for d in range(-3, 4))
hs_small = hs[["episode_id", "sent_idx", "labels"]]
near = np.fromiter((near_ad(r) for r in hs_small.itertuples()), dtype=bool, count=len(hs_small))
R["commercial"]["pct_health_sents_ad_adjacent"] = pct(near.sum(), len(hs_small))
# which topics are most ad-adjacent
hs_small = hs_small.assign(near=near)
tt = hs_small.assign(t=hs_small.labels.str.findall(r"topics:([a-z0-9_]+)")).explode("t")
ta = tt.groupby("t").near.agg(["mean", "size"])
R["commercial"]["ad_adjacent_by_topic"] = [{"topic": i, "pct": round(100 * r["mean"], 1), "n": int(r["size"])} for i, r in ta.sort_values("mean", ascending=False).iterrows() if r["size"] > 500]
# products: top by episodes, health-related flag, top shows, genre mix
pr = ep_lab[ep_lab.section == "products"]
prod_rows = []
for k, grp in pr.groupby("label"):
    spec = LEX["products"].get(k, {})
    prod_rows.append({"product": k, "type": spec.get("type"), "health_related": spec.get("health_related"),
                      "sentences": int(grp.n.sum()), "episodes": int(grp.episode_id.nunique()), "shows": int(grp.podcast_id.nunique()),
                      "live_episodes": int(grp[grp.live].episode_id.nunique()),
                      "top_shows": [(s, int(n)) for s, n in grp.groupby("show").episode_id.nunique().sort_values(ascending=False).head(4).items()]})
R["products_detail"] = sorted(prod_rows, key=lambda r: -r["episodes"])
# products co-mentioned with commercial marker in same sentence vs not
ps = sents[sents.labels.str.contains("products:")]
R["commercial"]["pct_product_sents_with_ad_marker"] = pct(ps.labels.str.contains("commercial:|frames:commercialization").sum(), len(ps))

# ---------- F. temporal ----------
live_epi = epi[epi.live]
month_sent = live_epi.groupby("month").n_sent.sum()
def monthly_series(section, labels=None):
    d = ep_lab[(ep_lab.section == section) & ep_lab.live]
    if labels is not None:
        d = d[d.label.isin(labels)]
    m = d.groupby(["label", "month"]).n.sum().unstack(fill_value=0).reindex(columns=month_sent.index, fill_value=0)
    return {"months": list(month_sent.index), "month_sentences": month_sent.tolist(),
            "series": {l: (1e6 * m.loc[l] / month_sent).round(1).tolist() for l in m.index},
            "raw": {l: m.loc[l].astype(int).tolist() for l in m.index}}
R["monthly_topics"] = monthly_series("topics")
mh = live_epi.groupby("month").health_sents.sum()
R["monthly_health"] = {"months": list(month_sent.index), "per_1k": (1000 * mh / month_sent).round(2).tolist(),
                       "by_genre": {g_: (1000 * v.groupby("month").health_sents.sum() / v.groupby("month").n_sent.sum()).round(2).reindex(month_sent.index).fillna(0).tolist() for g_, v in live_epi.groupby("genre_group")}}
R["monthly_narratives"] = monthly_series("narratives")
R["monthly_frames"] = monthly_series("frames")
# weekly series in live window for narratives and select topics
live_epi2 = live_epi.copy()
live_epi2["week"] = live_epi2.pub.dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")
week_sent = live_epi2.groupby("week").n_sent.sum()
wl = ep_lab[ep_lab.live].join(live_epi2[["week"]], on="episode_id")
wk = wl[wl.section == "narratives"].groupby(["label", "week"]).n.sum().unstack(fill_value=0).reindex(columns=week_sent.index, fill_value=0)
R["weekly_narratives"] = {"weeks": list(week_sent.index), "raw": {l: wk.loc[l].astype(int).tolist() for l in wk.index}}
# yearly long-run for select topics, normalized per million sentences (2015+)
ys = epi[epi.year >= 2015].groupby("year").n_sent.sum()
yt = ep_lab[(ep_lab.section == "topics") & (ep_lab.year >= 2015)].groupby(["label", "year"]).n.sum().unstack(fill_value=0).reindex(columns=ys.index, fill_value=0)
R["yearly_topics"] = {"years": [int(y) for y in ys.index], "year_sentences": ys.tolist(), "n_shows": epi[epi.year >= 2015].groupby("year").podcast_id.nunique().tolist(),
                      "series": {l: (1e6 * yt.loc[l] / ys).round(1).tolist() for l in yt.index}}
yn = ep_lab[(ep_lab.section == "narratives") & (ep_lab.year >= 2015)].groupby(["label", "year"]).n.sum().unstack(fill_value=0).reindex(columns=ys.index, fill_value=0)
R["yearly_narratives"] = {"years": [int(y) for y in ys.index], "series": {l: (1e6 * yn.loc[l] / ys).round(1).tolist() for l in yn.index}}
# bursts: monthly z-score in live window for topics and narratives
def bursts(ms, min_raw=30):
    out = []
    for l, vals in ms["series"].items():
        v = np.array(vals, dtype=float)
        raw = np.array(ms["raw"][l])
        if raw.sum() < min_raw or len(v) < 4:
            continue
        med = np.median(v); mad = np.median(np.abs(v - med)) + 1e-9
        z = (v - med) / (1.4826 * mad)
        i = int(np.argmax(z))
        if z[i] > 3 and raw[i] >= 10:
            out.append({"label": l, "month": ms["months"][i], "peak_per_million": float(v[i]), "median_per_million": float(med), "ratio": round(float(v[i] / (med + 1e-9)), 1), "raw": int(raw[i])})
    return sorted(out, key=lambda r: -r["ratio"])
R["bursts"] = {"topics": bursts(R["monthly_topics"]), "narratives": bursts(R["monthly_narratives"]), "frames": bursts(R["monthly_frames"])}

# ---------- G. diffusion: first-mention lead/lag for bursty narratives in live window ----------
diff = {}
for key in ["tylenol_pregnancy_autism", "leucovorin_autism", "hepatitis_b_birth_dose", "maha_report_claims", "vaccines_cause_autism", "fluoride_iq", "seed_oils_toxic", "food_dyes_behavior"]:
    d = nx[nx.narrs == key].join(ep.set_index("episode_id")[["pub"]], on="episode_id")
    d = d[d.pub >= "2025-08-01"]
    if len(d) < 10:
        continue
    first = d.groupby("show").pub.min().sort_values()
    diff[key] = {"first_mentions": [(s, p.strftime("%Y-%m-%d")) for s, p in first.head(12).items()], "n_shows": int(len(first)),
                 "daily": d.groupby(d.pub.dt.strftime("%Y-%m-%d")).size().to_dict()}
R["diffusion"] = diff

# ---------- H. examples for the report ----------
def examples(regex, n=5, min_len=60):
    d = sents[sents.labels.str.contains(regex) & (sents.text.str.len() > min_len)]
    d = d.sample(min(n, len(d)), random_state=3).join(epi[["show", "month"]], on="episode_id")
    return [{"show": r.show, "month": r.month, "text": r.text[:280], "labels": r.labels} for r in d.itertuples()]
R["examples"] = {"distrust_health": examples(r"frames:big_pharma.*topics:|topics:.*frames:big_pharma"),
                 "correction": examples(r"frames:misinformation_correction"), "weak_evidence": examples(r"evidence:weak_evidence"),
                 "ad_health": examples(r"commercial:.*products:|products:.*commercial:")}

# ---------- I. speaker labels (RSS subset) ----------
sp = sents[sents.speaker.notna() & sents.is_health]
R["speakers"] = {"n_health_sents_with_speaker": int(len(sp)), "n_episodes": int(sp.episode_id.nunique())}

def default(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    if isinstance(o, pd.Timestamp): return o.strftime("%Y-%m-%d")
    raise TypeError(type(o))
json.dump(R, open(f"{OUT}/" + os.environ.get("REPORT_NAME", "report_data.json"), "w"), default=default)
print("wrote", os.environ.get("REPORT_NAME", "report_data.json"), file=sys.stderr)
