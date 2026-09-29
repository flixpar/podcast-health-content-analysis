"""Summarise what the downloaded chart archive actually contains.

Writes a set of CSV tables under data/chart-archive/parsed/summary/ plus a
findings.json with the numbers quoted in the write-up.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2] / "data" / "chart-archive"
PARSED = ROOT / "parsed"
SUMMARY = PARSED / "summary"
DB = Path(__file__).resolve().parents[2] / "downloader" / "data" / "podcast_metadata.db"


def load() -> pd.DataFrame:
    frames = [pd.read_parquet(p) for p in sorted(PARSED.glob("chart_rows*.parquet"))]
    df = pd.concat(frames, ignore_index=True)
    df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
    df["date"] = df["captured_at"].dt.date
    df["month"] = df["captured_at"].dt.to_period("M").astype(str)
    if "archive" not in df:
        df["archive"] = "wayback"
    df["archive"] = df["archive"].fillna("wayback")
    return df


def normkey(name: str | None) -> str | None:
    """Match shows across sources by title: the sources share no id space."""
    if not isinstance(name, str):
        return None
    key = re.sub(r"[^a-z0-9]+", "", name.lower())
    return key or None


def agreement(fl: pd.DataFrame, a: str, b: str, depth: int,
              tolerance_days: int = 1) -> dict:
    """Do two series rank the same shows on (nearly) the same day?"""
    def table(series: str) -> dict:
        sub = fl[(fl.series == series) & (fl["rank"] <= depth)].copy()
        sub["key"] = sub["name"].map(normkey)
        sub = sub.dropna(subset=["key"])
        out = {}
        for date, g in sub.groupby("date"):
            # one capture per day: merging two captures of the same chart
            # inflates the set and depresses Jaccard for no good reason
            best = max(g.groupby("path"), key=lambda kv: len(kv[1]))[1]
            best = best.sort_values("rank").drop_duplicates("key")
            if len(best) >= min(depth, 10):
                out[date] = dict(zip(best["key"], best["rank"]))
        return out

    ta, tb = table(a), table(b)
    pairs = []
    for date, ranks_a in ta.items():
        best = None
        for offset in range(0, tolerance_days + 1):
            for signed in ({offset, -offset} if offset else {0}):
                cand = date + timedelta(days=signed)
                if cand in tb:
                    best = cand
                    break
            if best:
                break
        if best is None:
            continue
        ranks_b = tb[best]
        shared = set(ranks_a) & set(ranks_b)
        union = set(ranks_a) | set(ranks_b)
        row = {"date_a": str(date), "date_b": str(best),
               "n_a": len(ranks_a), "n_b": len(ranks_b),
               "shared": len(shared),
               "jaccard": len(shared) / len(union) if union else None,
               "overlap_pct": 100 * len(shared) / min(len(ranks_a), len(ranks_b))
               if ranks_a and ranks_b else None}
        if len(shared) >= 5:
            xs = [ranks_a[k] for k in shared]
            ys = [ranks_b[k] for k in shared]
            row["spearman"] = float(pd.Series(xs).corr(pd.Series(ys), method="spearman"))
        pairs.append(row)
    if not pairs:
        return {"pair": f"{a} vs {b}", "depth": depth, "matched_days": 0}
    d = pd.DataFrame(pairs)
    return {
        "pair": f"{a} vs {b}", "depth": depth, "matched_days": int(len(d)),
        "median_overlap_pct": round(float(d["overlap_pct"].median()), 1),
        "median_jaccard": round(float(d["jaccard"].median()), 3),
        "median_spearman": (round(float(d["spearman"].median()), 3)
                            if "spearman" in d else None),
        "detail": d.to_dict("records"),
    }


def flagship(df: pd.DataFrame) -> pd.DataFrame:
    """The 'overall US top shows' chart from each source, one row per rank."""
    masks = {
        "apple/itunes_rss": (df.source == "itunes_rss") & (df.genre == "All Podcasts")
        & (df.unit == "podcast"),
        "apple/charts_page": (df.source == "apple_charts_page")
        & (df.genre == "All Podcasts") & (df.chart == "Top Shows"),
        "apple/chartable": (df.source == "chartable_itunes") & (df.region == "us")
        & (df.genre == "all-podcasts") & (df.unit == "podcast"),
        "apple/podbay": (df.source == "podbay") & (df.genre == "all-podcasts"),
        # Spotify renamed the same chart from `top` to `top-podcasts` in 2025
        "spotify/api": (df.source == "spotify_api") & (df.region == "us")
        & df.chart.isin(["top", "top-podcasts"]) & (df.unit == "show"),
        "spotify/chartable": (df.source == "chartable_spotify") & (df.region == "us")
        & (df.genre == "top-podcasts"),
        "reach/chartable": (df.source == "chartable_reach") & (df.region == "us")
        & (df.genre == "all-podcasts"),
    }
    out = []
    for name, mask in masks.items():
        sub = df[mask].copy()
        sub["series"] = name
        out.append(sub)
    return pd.concat(out, ignore_index=True) if out else df.head(0)


def main() -> int:
    SUMMARY.mkdir(parents=True, exist_ok=True)
    df = load()
    findings: dict = {}

    findings["total_rows"] = int(len(df))
    findings["total_captures"] = int(df["path"].nunique())
    findings["date_range"] = [str(df["date"].min()), str(df["date"].max())]

    by_source = df.groupby(["archive", "source"]).agg(
        rows=("rank", "size"),
        captures=("path", "nunique"),
        charts=("chart", "nunique"),
        first=("date", "min"),
        last=("date", "max"),
        max_rank=("rank", "max"),
        shows=("entity_id", "nunique"),
    ).reset_index()
    by_source.to_csv(SUMMARY / "by_source.csv", index=False)
    findings["by_source"] = by_source.to_dict("records")

    fl = flagship(df)
    fl.to_parquet(PARSED / "flagship_us_overall.parquet", index=False)

    # snapshot = one capture of one chart; depth = deepest rank in it
    snaps = fl.groupby(["series", "path", "date", "month"]).agg(
        depth=("rank", "max"), rows=("rank", "size")).reset_index()
    # Chartable paginates, so merge pages captured on the same day. `top100`
    # counts distinct ranks 1-100 actually present: a day where only ?page=2
    # was captured has depth 200 and no top-100 rows at all.
    top100 = (fl[fl["rank"] <= 100].groupby(["series", "date"])["rank"]
              .nunique().rename("top100").reset_index())
    daily = snaps.groupby(["series", "date", "month"]).agg(
        depth=("depth", "max"), pages=("path", "size")).reset_index()
    daily = daily.merge(top100, on=["series", "date"], how="left")
    daily["top100"] = daily["top100"].fillna(0).astype(int)
    daily["full_top100"] = daily["top100"] >= 95
    daily.to_csv(SUMMARY / "flagship_daily_snapshots.csv", index=False)

    cadence = daily.groupby(["series", "month"]).agg(
        days=("date", "nunique"), depth=("depth", "max"),
        full_top100_days=("full_top100", "sum")).reset_index()
    cadence.to_csv(SUMMARY / "flagship_cadence_by_month.csv", index=False)

    cov = daily.groupby("series").agg(
        days=("date", "nunique"), first=("date", "min"), last=("date", "max"),
        median_depth=("depth", "median"), max_depth=("depth", "max"),
        full_top100_days=("full_top100", "sum")).reset_index()
    cov["months_covered"] = daily.groupby("series")["month"].nunique().values
    cov["span_months"] = [
        (pd.Period(str(r.last)[:7]) - pd.Period(str(r.first)[:7])).n + 1
        for r in cov.itertuples()]
    cov["month_fill_pct"] = (100 * cov["months_covered"] / cov["span_months"]).round(1)
    cov.to_csv(SUMMARY / "flagship_coverage.csv", index=False)
    findings["flagship_coverage"] = cov.to_dict("records")

    # longest gap between consecutive snapshot days, per series
    gaps = []
    for series, g in daily.groupby("series"):
        d = pd.to_datetime(sorted(g["date"].unique()))
        if len(d) < 2:
            continue
        delta = d.to_series().diff().dt.days.dropna()
        gaps.append({"series": series, "median_gap_days": float(delta.median()),
                     "p90_gap_days": float(delta.quantile(0.9)),
                     "max_gap_days": int(delta.max())})
    pd.DataFrame(gaps).to_csv(SUMMARY / "flagship_gaps.csv", index=False)
    findings["flagship_gaps"] = gaps

    # genre coverage (Apple genres and Spotify categories)
    genre = df[df.unit.isin(["podcast", "show"])].groupby(
        ["source", "genre"]).agg(days=("date", "nunique"), rows=("rank", "size"),
                                 max_rank=("rank", "max")).reset_index()
    genre.sort_values("days", ascending=False).to_csv(
        SUMMARY / "genre_coverage.csv", index=False)

    # how big is the universe of shows that ever charted?
    apple = df[(df.platform == "apple") & (df.unit == "podcast")
               & df.entity_id.notna()]
    findings["apple_distinct_entities"] = int(apple["entity_id"].nunique())
    numeric = apple[apple.entity_id.str.fullmatch(r"\d+", na=False)]
    findings["apple_distinct_ids"] = int(numeric["entity_id"].nunique())
    spot = df[(df.platform == "spotify") & (df.unit == "show")]
    findings["spotify_distinct_uris"] = int(spot["entity_id"].nunique())

    # overlap with the podcasts already in the corpus
    if DB.exists():
        with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as conn:
            have = pd.read_sql_query(
                "SELECT apple_podcasts_id, title FROM podcasts", conn)
        have_ids = set(have["apple_podcasts_id"].dropna().astype(str)) | {
            i.replace("apple_", "") for i in have["apple_podcasts_id"].dropna().astype(str)}
        chart_ids = set(numeric["entity_id"].unique())
        findings["corpus_apple_ids"] = len(
            {i for i in have_ids if i.isdigit()})
        findings["corpus_in_archive"] = len(
            {i for i in have_ids if i.isdigit()} & chart_ids)
        findings["archive_not_in_corpus"] = len(
            chart_ids - {i for i in have_ids if i.isdigit()})

    # top-100 churn: how many distinct shows occupy the Apple top N over time
    ch = fl[(fl.series == "apple/chartable") & (fl["rank"] <= 100)]
    if len(ch):
        per_year = ch.groupby(ch["captured_at"].dt.year)["entity_id"].nunique()
        findings["chartable_top100_distinct_shows_per_year"] = {
            str(k): int(v) for k, v in per_year.items()}
        findings["chartable_top100_distinct_shows_total"] = int(
            ch["entity_id"].nunique())

    # ---- genre charts, for the health/news focus of the study --------------
    shows = df[df.unit.isin(["podcast", "show"])]
    gseries = {
        "apple/chartable": (shows.source == "chartable_itunes") & (shows.region == "us"),
        "apple/charts_page": (shows.source == "apple_charts_page")
        & (shows.chart == "Top Shows"),
        "apple/podbay": shows.source == "podbay",
        "spotify/api": (shows.source == "spotify_api") & (shows.region == "us"),
        "spotify/chartable": (shows.source == "chartable_spotify") & (shows.region == "us"),
    }
    grows = []
    for name, mask in gseries.items():
        sub = shows[mask]
        g = sub.groupby("genre").agg(
            days=("date", "nunique"), months=("month", "nunique"),
            first=("date", "min"), last=("date", "max"),
            depth=("rank", "median"), shows=("entity_id", "nunique")).reset_index()
        g.insert(0, "series", name)
        grows.append(g)
    genre_series = pd.concat(grows, ignore_index=True)
    genre_series.to_csv(SUMMARY / "genre_series_coverage.csv", index=False)
    focus = genre_series[genre_series.genre.astype(str).str.contains(
        "health|news|politic|science|society", case=False, na=False)]
    findings["focus_genres"] = focus.sort_values(
        ["series", "days"], ascending=[True, False]).to_dict("records")

    # ---- cross-source agreement -------------------------------------------
    comparisons = [
        ("apple/chartable", "apple/charts_page", 24),
        ("apple/chartable", "apple/itunes_rss", 100),
        ("apple/podbay", "apple/itunes_rss", 100),
        ("apple/podbay", "apple/chartable", 100),
        ("spotify/api", "spotify/chartable", 50),
        ("apple/chartable", "spotify/api", 50),
    ]
    agree = [agreement(fl, a, b, d) for a, b, d in comparisons]
    pd.DataFrame([{k: v for k, v in a.items() if k != "detail"}
                  for a in agree]).to_csv(SUMMARY / "agreement.csv", index=False)
    for a in agree:
        if a.get("detail"):
            pd.DataFrame(a["detail"]).to_csv(
                SUMMARY / f"agreement_{a['pair'].replace('/', '_').replace(' ', '')}.csv",
                index=False)
    findings["agreement"] = [{k: v for k, v in a.items() if k != "detail"}
                             for a in agree]

    # Is the region-less Spotify `top` chart the US one? Compare same-day pairs.
    sp = df[(df.source == "spotify_api") & (df.chart.isin(["top", "top-podcasts"]))
            & (df.unit == "show")].copy()
    sp["has_region"] = sp["slug"].str.contains("region=")
    same = []
    for date, g in sp.groupby("date"):
        with_r = g[g.has_region & (g.region == "us")].sort_values("rank")
        without = g[~g.has_region].sort_values("rank")
        if len(with_r) >= 20 and len(without) >= 20:
            a = set(with_r.head(50)["entity_id"])
            b = set(without.head(50)["entity_id"])
            same.append(len(a & b) / max(len(a | b), 1))
    findings["spotify_bare_top_matches_us"] = {
        "days_compared": len(same),
        "median_jaccard": round(float(pd.Series(same).median()), 3) if same else None,
    }

    (SUMMARY / "findings.json").write_text(json.dumps(findings, indent=2, default=str))
    print(json.dumps({k: v for k, v in findings.items()
                      if not isinstance(v, (list, dict))}, indent=2))
    print(cov.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
