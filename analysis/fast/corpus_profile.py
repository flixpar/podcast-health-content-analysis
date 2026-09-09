"""Fast structural profile of the podcast transcript corpus.

Reads only downloader/data/podcast_metadata.db (read-only) and writes
compact, chart-ready tables to analysis/output/fast-analysis/corpus_profile.json.
No transcript files are opened.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "downloader" / "data" / "podcast_metadata.db"
OUT_DIR = ROOT / "analysis" / "output" / "fast-analysis"
OUT_JSON = OUT_DIR / "corpus_profile.json"

LIVE_START = "2025-10-13"
LIVE_END = "2026-08-28"
HEALTH_CHART = "apple_us_genre_1512"

# Hand-tuned Apple-category -> coarse genre group. Applied in this order:
# the first category on a show that matches a rule wins.
GENRE_RULES: list[tuple[str, list[str]]] = [
    ("news_politics", ["Daily News", "News Commentary", "Politics", "Government", "News", "Business News", "Tech News"]),
    ("true_crime", ["True Crime"]),
    ("health_wellness", ["Alternative Health", "Mental Health", "Nutrition", "Fitness", "Medicine", "Sexuality", "Health & Fitness"]),
    ("business_selfhelp", ["Entrepreneurship", "Investing", "Management", "Marketing", "Careers", "Self-Improvement", "Business", "How To"]),
    ("religion", ["Christianity", "Spirituality", "Religion & Spirituality", "Philosophy"]),
    ("comedy", ["Stand-Up", "Improv", "Comedy Interviews", "Comedy"]),
    ("sports", ["Football", "Fantasy Sports", "Sports"]),
    ("education_science", ["Natural Sciences", "Life Sciences", "Social Sciences", "Science", "History", "Courses", "Education"]),
    ("entertainment", ["TV & Film", "Film History", "Music Interviews", "Music", "Performing Arts", "Books", "Fiction", "Drama", "Fantasy", "Science Fiction", "Arts", "Leisure", "Hobbies", "Wilderness", "Technology"]),
    ("society_culture", ["Relationships", "Personal Journals", "Documentary", "Society & Culture"]),
]
GENRE_ORDER = [g for g, _ in GENRE_RULES] + ["other"]


def genre_of(cats: list[str]) -> str:
    for group, keys in GENRE_RULES:
        if any(k in cats for k in keys):
            return group
    return "other"


def jparse(s, default):
    if not s:
        return default
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return default


def r(x, n=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return None
    return round(float(x), n)


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    pod = pd.read_sql("SELECT id, title, publisher, categories, episode_count FROM podcasts", con)
    ep = pd.read_sql(
        "SELECT id, podcast_id, title, duration_seconds, published_date, status, has_rss_transcript FROM episodes",
        con,
    )
    tr = pd.read_sql(
        "SELECT episode_id, word_count, duration_seconds, has_speakers, has_timestamps, metadata FROM transcripts",
        con,
    )
    ch = pd.read_sql("SELECT podcast_id, chart, rank FROM podcast_charts", con)
    con.close()

    pod["cats"] = pod["categories"].map(lambda s: jparse(s, []))
    pod["primary_category"] = pod["cats"].map(
        lambda L: next((c for c in L if c != "Podcasts"), "Unknown")
    )
    pod["genre_group"] = pod["cats"].map(genre_of)

    meta = tr["metadata"].map(lambda s: jparse(s, {}))
    tr["source"] = meta.map(lambda d: d.get("source"))
    tr["model"] = meta.map(lambda d: d.get("model"))
    tr["source_format"] = meta.map(lambda d: d.get("source_format"))
    tr = tr.drop(columns=["metadata"])

    ep["published_date"] = pd.to_datetime(ep["published_date"], errors="coerce", utc=True).dt.tz_localize(None)
    return pod, ep, tr, ch


def main() -> None:
    pod, ep, tr, ch = load()

    # transcript-level frame joined to episode + podcast
    t = tr.merge(
        ep[["id", "podcast_id", "title", "duration_seconds", "published_date", "has_rss_transcript"]].rename(
            columns={"id": "episode_id", "duration_seconds": "ep_duration_s", "title": "ep_title"}
        ),
        on="episode_id",
        how="left",
    )
    # prefer transcript duration, fall back to episode duration
    t["dur_s"] = t["duration_seconds"].where(t["duration_seconds"].notna() & (t["duration_seconds"] > 0), t["ep_duration_s"])
    t["minutes"] = t["dur_s"] / 60.0
    t["wpm"] = np.where(t["minutes"] > 0, t["word_count"] / t["minutes"], np.nan)
    t = t.merge(
        pod[["id", "title", "publisher", "primary_category", "genre_group"]].rename(
            columns={"id": "podcast_id", "title": "show_title"}
        ),
        on="podcast_id",
        how="left",
    )

    live_start, live_end = pd.Timestamp(LIVE_START), pd.Timestamp(LIVE_END)
    live_weeks = (live_end - live_start).days / 7.0
    t["in_live"] = t["published_date"].between(live_start, live_end)

    out: dict = {
        "meta": {
            "database": str(DB),
            "live_window": [LIVE_START, LIVE_END],
            "generated_from": "analysis/fast/corpus_profile.py",
            "note": "transcript-level metrics; transcript files were not opened",
        }
    }

    # ---------- 1. headline ----------
    words = t["word_count"].fillna(0)
    by_source = t.groupby("source", dropna=False)["word_count"].agg(["count", "sum"])
    total_words = float(words.sum())
    out["headline"] = {
        "n_podcasts_total": int(len(pod)),
        "n_podcasts_with_transcript": int(t["podcast_id"].nunique()),
        "n_episodes_in_db": int(len(ep)),
        "n_transcripts": int(len(t)),
        "episodes_without_transcript": int(len(ep) - len(t)),
        "total_words": int(total_words),
        "total_transcript_hours": r(t["dur_s"].sum() / 3600.0, 1),
        "mean_words_per_transcript": r(words.mean(), 1),
        "median_words_per_transcript": r(words.median(), 1),
        "median_minutes_per_transcript": r(t["minutes"].median(), 1),
        "median_words_per_minute": r(t["wpm"].median(), 1),
        "by_source": [
            {
                "source": (s if isinstance(s, str) else "unknown"),
                "n_transcripts": int(by_source.loc[s, "count"]),
                "share_transcripts_pct": r(100 * by_source.loc[s, "count"] / len(t)),
                "words": int(by_source.loc[s, "sum"]),
                "share_words_pct": r(100 * by_source.loc[s, "sum"] / total_words),
            }
            for s in by_source.index
        ],
        "asr_models": [
            {"model": k if isinstance(k, str) else "unknown", "n_transcripts": int(v)}
            for k, v in t.loc[t["source"] == "asr", "model"].fillna("unknown").value_counts().items()
        ],
        "rss_source_formats": [
            {"source_format": k, "n_transcripts": int(v)}
            for k, v in t.loc[t["source"] == "rss", "source_format"].fillna("unknown").value_counts().items()
        ],
        "speaker_labels": {
            "n_with_speakers": int(t["has_speakers"].fillna(0).astype(bool).sum()),
            "pct_with_speakers": r(100 * t["has_speakers"].fillna(0).astype(bool).mean()),
            "n_with_timestamps": int(t["has_timestamps"].fillna(0).astype(bool).sum()),
            "pct_with_timestamps": r(100 * t["has_timestamps"].fillna(0).astype(bool).mean()),
            "speakers_by_source": [
                {"source": s, "pct_with_speakers": r(100 * g["has_speakers"].fillna(0).astype(bool).mean())}
                for s, g in t.groupby("source", dropna=False)
                if isinstance(s, str)
            ],
        },
        "date_range": {
            "first_published": str(t["published_date"].min().date()),
            "last_published": str(t["published_date"].max().date()),
            "n_undated": int(t["published_date"].isna().sum()),
        },
        "live_window": {
            "n_transcripts": int(t["in_live"].sum()),
            "share_of_transcripts_pct": r(100 * t["in_live"].mean()),
            "words": int(t.loc[t["in_live"], "word_count"].sum()),
            "share_of_words_pct": r(100 * t.loc[t["in_live"], "word_count"].sum() / total_words),
            "hours": r(t.loc[t["in_live"], "dur_s"].sum() / 3600.0, 1),
            "n_shows_active": int(t.loc[t["in_live"], "podcast_id"].nunique()),
            "weeks": r(live_weeks, 1),
        },
    }

    # ---------- 2. per-show table ----------
    charts_by_pod: dict[int, dict[str, int]] = {}
    for row in ch.itertuples():
        d = charts_by_pod.setdefault(row.podcast_id, {})
        if row.chart not in d or row.rank < d[row.chart]:
            d[row.chart] = int(row.rank)

    ep_counts = ep.groupby("podcast_id").size()
    shows = []
    for pid, g in t.groupby("podcast_id"):
        prow = pod.loc[pod["id"] == pid].iloc[0]
        cm = charts_by_pod.get(pid, {})
        glive = g[g["in_live"]]
        shows.append(
            {
                "podcast_id": int(pid),
                "title": prow["title"],
                "publisher": prow["publisher"],
                "primary_category": prow["primary_category"],
                "categories": [c for c in prow["cats"] if c != "Podcasts"],
                "genre_group": prow["genre_group"],
                "on_health_chart": HEALTH_CHART in cm,
                "charts": sorted(cm),
                "best_rank_by_chart": {k: cm[k] for k in sorted(cm)},
                "n_charts": len(cm),
                "n_episodes_in_db": int(ep_counts.get(pid, 0)),
                "n_transcripts": int(len(g)),
                "total_words": int(g["word_count"].sum()),
                "total_hours": r(g["dur_s"].sum() / 3600.0, 1),
                "median_episode_minutes": r(g["minutes"].median(), 1),
                "first_published": str(g["published_date"].min().date()) if g["published_date"].notna().any() else None,
                "last_published": str(g["published_date"].max().date()) if g["published_date"].notna().any() else None,
                "live_episodes": int(len(glive)),
                "live_episodes_per_week": r(len(glive) / live_weeks, 2),
                "live_words": int(glive["word_count"].sum()),
                "share_rss_transcripts": r((g["source"] == "rss").mean(), 3),
                "median_words_per_minute": r(g["wpm"].median(), 1),
            }
        )
    shows.sort(key=lambda d: -d["total_words"])
    out["per_show"] = shows

    # ---------- 3. genre groups ----------
    gt = t.copy()
    grp = gt.groupby("genre_group")
    genre_rows = []
    for gname in GENRE_ORDER:
        if gname not in grp.groups:
            continue
        g = grp.get_group(gname)
        n_shows = g["podcast_id"].nunique()
        health = {s["podcast_id"] for s in shows if s["on_health_chart"]}
        genre_rows.append(
            {
                "genre_group": gname,
                "n_shows": int(n_shows),
                "n_transcripts": int(len(g)),
                "words": int(g["word_count"].sum()),
                "share_words_pct": r(100 * g["word_count"].sum() / total_words),
                "hours": r(g["dur_s"].sum() / 3600.0, 1),
                "median_episode_minutes": r(g["minutes"].median(), 1),
                "live_episodes": int(g["in_live"].sum()),
                "live_episodes_per_week": r(g["in_live"].sum() / live_weeks, 1),
                "n_shows_on_health_chart": int(len(set(g["podcast_id"].unique()) & health)),
            }
        )
    genre_rows.sort(key=lambda d: -d["words"])
    out["genre_groups"] = {
        "mapping": {g: keys for g, keys in GENRE_RULES},
        "mapping_note": "first matching rule in listed order wins; shows matching none are 'other'",
        "rows": genre_rows,
    }

    health_ids = {s["podcast_id"] for s in shows if s["on_health_chart"]}
    ht = t[t["podcast_id"].isin(health_ids)]
    out["health_chart"] = {
        "n_shows": int(len(health_ids)),
        "n_shows_with_transcripts": int(ht["podcast_id"].nunique()),
        "n_transcripts": int(len(ht)),
        "words": int(ht["word_count"].sum()),
        "share_words_pct": r(100 * ht["word_count"].sum() / total_words),
        "hours": r(ht["dur_s"].sum() / 3600.0, 1),
        "median_episode_minutes": r(ht["minutes"].median(), 1),
        "genre_mix": [
            {"genre_group": k, "n_shows": int(v)}
            for k, v in pod.loc[pod["id"].isin(health_ids), "genre_group"].value_counts().items()
        ],
    }

    # ---------- 4. distributions ----------
    dur_bins = [0, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 10**9]
    dur_labels = ["0-5", "5-10", "10-15", "15-20", "20-30", "30-45", "45-60", "60-90", "90-120", "120-180", "180-240", "240+"]
    dcut = pd.cut(t["minutes"], bins=dur_bins, labels=dur_labels, right=False)
    w_bins = [0, 200, 500, 1000, 2000, 4000, 6000, 8000, 10000, 15000, 20000, 30000, 10**9]
    w_labels = ["0-200", "200-500", "500-1k", "1k-2k", "2k-4k", "4k-6k", "6k-8k", "8k-10k", "10k-15k", "15k-20k", "20k-30k", "30k+"]
    wcut = pd.cut(t["word_count"], bins=w_bins, labels=w_labels, right=False)

    live = t[t["in_live"]].copy()
    live["month"] = live["published_date"].dt.to_period("M").astype(str)
    months = sorted(live["month"].unique())
    by_month_genre = live.pivot_table(index="month", columns="genre_group", values="episode_id", aggfunc="count").fillna(0)

    t_year = t.dropna(subset=["published_date"]).copy()
    t_year["year"] = t_year["published_date"].dt.year

    out["distributions"] = {
        "episode_duration_minutes": [
            {"bin_minutes": lab, "n_transcripts": int(v), "pct": r(100 * v / len(t))}
            for lab, v in dcut.value_counts().reindex(dur_labels).fillna(0).items()
        ],
        "duration_percentiles_minutes": {
            f"p{p}": r(np.nanpercentile(t["minutes"].dropna(), p), 1) for p in (5, 25, 50, 75, 90, 95, 99)
        },
        "words_per_episode": [
            {"bin_words": lab, "n_transcripts": int(v), "pct": r(100 * v / len(t))}
            for lab, v in wcut.value_counts().reindex(w_labels).fillna(0).items()
        ],
        "words_percentiles": {
            f"p{p}": int(np.nanpercentile(t["word_count"].dropna(), p)) for p in (5, 25, 50, 75, 90, 95, 99)
        },
        "live_episodes_per_month": [
            {
                "month": m,
                "n_episodes": int((live["month"] == m).sum()),
                "words": int(live.loc[live["month"] == m, "word_count"].sum()),
                "by_genre": {c: int(by_month_genre.loc[m, c]) for c in by_month_genre.columns if by_month_genre.loc[m, c] > 0},
            }
            for m in months
        ],
        "transcripts_by_year": [
            {
                "year": int(y),
                "n_transcripts": int(len(g)),
                "words": int(g["word_count"].sum()),
                "hours": r(g["dur_s"].sum() / 3600.0, 1),
                "pct_rss": r(100 * (g["source"] == "rss").mean()),
            }
            for y, g in t_year.groupby("year")
        ],
    }

    # ---------- 5. concentration ----------
    sw = np.array([s["total_words"] for s in shows], dtype=float)
    cum = np.cumsum(sw) / sw.sum()
    lorenz = []
    for k in (1, 5, 10, 20, 50, 100, len(shows)):
        if k <= len(shows):
            lorenz.append(
                {
                    "n_shows": int(k),
                    "share_of_shows_pct": r(100 * k / len(shows)),
                    "cum_share_of_words_pct": r(100 * cum[k - 1]),
                }
            )
    # Gini over shows
    srt = np.sort(sw)
    n = len(srt)
    gini = (2 * np.sum((np.arange(1, n + 1)) * srt) / (n * srt.sum())) - (n + 1) / n
    out["concentration"] = {
        "n_shows": int(len(shows)),
        "lorenz_points": lorenz,
        "top10_share_of_words_pct": r(100 * cum[9]) if len(shows) >= 10 else None,
        "top10_shows": [{"title": s["title"], "total_words": s["total_words"]} for s in shows[:10]],
        "gini_words_across_shows": r(gini, 3),
        "shows_to_reach_50pct_words": int(np.searchsorted(cum, 0.5) + 1),
        "shows_to_reach_80pct_words": int(np.searchsorted(cum, 0.8) + 1),
    }

    # ---------- 6. chart overlap ----------
    chart_names = sorted(ch["chart"].unique())
    memb = {c: set(ch.loc[ch["chart"] == c, "podcast_id"]) for c in chart_names}
    n_by_count = pd.Series({p: len(v) for p, v in charts_by_pod.items()}).value_counts().sort_index()
    out["chart_overlap"] = {
        "chart_sizes": [{"chart": c, "n_shows": len(memb[c])} for c in chart_names],
        "shows_on_n_charts": [{"n_charts": int(k), "n_shows": int(v)} for k, v in n_by_count.items()],
        "shows_on_multiple_charts": int(sum(v for k, v in n_by_count.items() if k >= 2)),
        "shows_on_no_chart": int(len(pod) - len(charts_by_pod)),
        "crosstab": [
            {"chart_a": a, "chart_b": b, "n_shared": len(memb[a] & memb[b])}
            for a in chart_names
            for b in chart_names
        ],
        "apple_top_churn_2025_vs_now": {
            "in_both": len(memb.get("apple_us_top", set()) & memb.get("apple_us_top_20251013", set())),
            "only_20251013": len(memb.get("apple_us_top_20251013", set()) - memb.get("apple_us_top", set())),
            "only_current": len(memb.get("apple_us_top", set()) - memb.get("apple_us_top_20251013", set())),
        },
    }

    # ---------- 7. data quality ----------
    dup = ep.dropna(subset=["title"]).groupby(["podcast_id", "title"]).size()
    dup_extra = int((dup - 1).clip(lower=0).sum())
    dup_shows = int(dup[dup > 1].reset_index()["podcast_id"].nunique())
    wpm = t["wpm"]
    low = t[(wpm < 60) & wpm.notna()]
    high = t[(wpm > 250) & wpm.notna()]
    ep1970 = ep[ep["published_date"].notna() & (ep["published_date"].dt.year <= 1971)]
    out["quality_flags"] = {
        "transcripts_word_count_lt_200": int((t["word_count"] < 200).sum()),
        "transcripts_word_count_lt_50": int((t["word_count"] < 50).sum()),
        "transcripts_word_count_zero_or_null": int((t["word_count"].fillna(0) == 0).sum()),
        "transcripts_missing_duration": int((t["dur_s"].isna() | (t["dur_s"] <= 0)).sum()),
        "episodes_missing_duration": int((ep["duration_seconds"].isna() | (ep["duration_seconds"] <= 0)).sum()),
        "wpm_below_60": int(len(low)),
        "wpm_above_250": int(len(high)),
        "wpm_outlier_pct": r(100 * (len(low) + len(high)) / len(t)),
        "wpm_outliers_by_source": [
            {
                "source": s,
                "n_low": int(((g["wpm"] < 60) & g["wpm"].notna()).sum()),
                "n_high": int(((g["wpm"] > 250) & g["wpm"].notna()).sum()),
                "n": int(len(g)),
            }
            for s, g in t.groupby("source", dropna=False)
            if isinstance(s, str)
        ],
        "top_shows_by_wpm_outliers": [
            {"title": k, "n_outliers": int(v)}
            for k, v in pd.concat([low, high])["show_title"].value_counts().head(10).items()
        ],
        "duplicate_title_extra_rows": dup_extra,
        "shows_with_duplicate_titles": dup_shows,
        "episodes_dated_1970": int(len(ep1970)),
        "episodes_undated": int(ep["published_date"].isna().sum()),
        "rss_transcript_formats": [
            {"source_format": k, "n": int(v)}
            for k, v in t.loc[t["source"] == "rss", "source_format"].fillna("unknown").value_counts().items()
        ],
        "episodes_by_status": [
            {"status": k, "n": int(v)} for k, v in ep["status"].value_counts().items()
        ],
        "podcasts_with_zero_transcripts": int(len(pod) - t["podcast_id"].nunique()),
        "has_rss_transcript_flag_vs_rss_source": {
            "episodes_flagged_has_rss_transcript": int(ep["has_rss_transcript"].fillna(0).astype(bool).sum()),
            "transcripts_with_source_rss": int((t["source"] == "rss").sum()),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT_JSON} ({OUT_JSON.stat().st_size/1e6:.2f} MB)")
    print(json.dumps(out["headline"], indent=1)[:2000])
    print(json.dumps(out["concentration"], indent=1)[:1500])
    print(json.dumps(out["genre_groups"]["rows"], indent=1))
    print(json.dumps(out["quality_flags"], indent=1)[:2500])
    print(json.dumps(out["chart_overlap"], indent=1)[:1500])
    print(json.dumps(out["health_chart"], indent=1))
    print(json.dumps(out["distributions"]["duration_percentiles_minutes"], indent=1))
    print(json.dumps(out["distributions"]["words_percentiles"], indent=1))
    print(json.dumps(out["distributions"]["transcripts_by_year"][-8:], indent=1))
    print(json.dumps([{k: v for k, v in m.items() if k != 'by_genre'} for m in out["distributions"]["live_episodes_per_month"]], indent=1))
    print(json.dumps(shows[:15], indent=1))


if __name__ == "__main__":
    main()
