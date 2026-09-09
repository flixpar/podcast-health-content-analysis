"""Build the study population from the archived Apple US overall chart.

Two things this has to get right, both learned the hard way:

* **Identity before counting.** 76 shows charted under more than one title, so
  titles are mapped to an Apple `adamId` first and the id is the entity. Days
  are pooled across a show's titles *before* any threshold is applied.
* **Exposure before tenure.** The archive's sampling rate varies sevenfold
  (one snapshot every 4 days in 2016, every 61 days in 2012), so counting
  snapshots measures tenure x sampling rate, not tenure. Each snapshot instead
  carries a weight equal to the calendar time closer to it than to any
  neighbouring snapshot, and a show's exposure-weighted sum estimates the days
  it actually spent in the chart.

The chart is mixed-depth by necessity: the Podbay and Chartable mirrors publish
100 places, Apple's own page only 24, so from 2024-08 a show must reach the top
24 to be seen at all. `deep_obs` / `shallow_obs` record which era each show's
evidence comes from, and a uniform top-24 variant is written alongside as a
sensitivity check.
"""

from __future__ import annotations

import glob
import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2] / "data" / "chart-archive"
PARSED = ROOT / "parsed"
OUT = PARSED / "population"
DB = Path(__file__).resolve().parents[2] / "downloader" / "data" / "podcast_metadata.db"

DEEP_CUT = 50     # what we use where the mirrors publish 100 places
SHALLOW_CUT = 24  # what Apple's own page publishes, 2024-08 onward
MIN_DAYS = 90     # estimated days in the chart
MIN_OBS = 3       # guard against one sparse snapshot carrying a 77-day weight

# Chartable captures that disagree with Apple's own chart on the day (see the
# agreement table): its last days before shutdown, and one stale October page.
DISTRUSTED = {("apple/chartable", d) for d in
              ("2024-10-07", "2024-12-06", "2024-12-07", "2024-12-08", "2024-12-09")}

SERIES = {                       # flagship series -> (parsed source, depth cut)
    "apple/podbay": ("podbay", DEEP_CUT),
    "apple/chartable": ("chartable_itunes", DEEP_CUT),
    "apple/charts_page": ("apple_charts_page", SHALLOW_CUT),
}


def key(name) -> str | None:
    if not isinstance(name, str):
        return None
    k = re.sub(r"[^a-z0-9]+", "", name.lower())
    return k or None


def load_rows() -> pd.DataFrame:
    df = pd.concat([pd.read_parquet(p) for p in sorted(PARSED.glob("chart_rows*.parquet"))],
                   ignore_index=True)
    df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
    df["date"] = df["captured_at"].dt.date.astype(str)
    df["key"] = df["name"].map(key)
    return df


def trusted_days() -> pd.DataFrame:
    """One row per usable snapshot day: which series it came from, how deep."""
    daily = pd.read_csv(PARSED / "summary" / "flagship_daily_snapshots.csv")
    daily["date"] = daily["date"].astype(str)
    keep = []
    for series, (_source, cut) in SERIES.items():
        sub = daily[daily.series == series]
        # the 100-deep mirrors have to be complete; Apple's page is 24 by design
        sub = sub[sub.full_top100] if cut == DEEP_CUT else sub[sub.depth >= cut]
        sub = sub[~sub.apply(lambda r: (r["series"], r["date"]) in DISTRUSTED, axis=1)]
        keep.append(sub.assign(cut=cut)[["date", "series", "cut"]])
    days = pd.concat(keep, ignore_index=True)
    # a day covered by two series is counted once, at the greater depth
    days = days.sort_values("cut", ascending=False).drop_duplicates("date")
    return days.sort_values("date").reset_index(drop=True)


def midpoint_weights(dates: pd.Series) -> pd.Series:
    """Calendar days each snapshot stands for: half the gap on either side."""
    d = pd.to_datetime(dates)
    mid = d.iloc[:-1].values + (d.iloc[1:].values - d.iloc[:-1].values) / 2
    edges = [d.iloc[0]] + list(pd.to_datetime(mid)) + [d.iloc[-1]]
    # keep fractional days: truncating each of ~940 segments to whole days
    # loses ~3% of the total exposure
    return pd.Series([(edges[i + 1] - edges[i]).total_seconds() / 86400
                      for i in range(len(d))], index=dates.values, dtype=float)


def chart_observations(df: pd.DataFrame, days: pd.DataFrame,
                       uniform_cut: int | None = None) -> pd.DataFrame:
    """One row per (show, snapshot day) inside the depth cut for that day."""
    src_of = {s: v[0] for s, v in SERIES.items()}
    frames = []
    for series, group in days.groupby("series"):
        source = src_of[series]
        cut = uniform_cut or int(group["cut"].iloc[0])
        sub = df[(df.source == source) & df.date.isin(set(group["date"]))
                 & df.key.notna() & (df["rank"] <= cut)]
        if source == "apple_charts_page":
            sub = sub[(sub.chart == "Top Shows") & (sub.genre == "All Podcasts")]
        else:
            sub = sub[(sub.genre == "all-podcasts") & (sub.unit == "podcast")]
        frames.append(sub.assign(series=series, cut=cut))
    return pd.concat(frames, ignore_index=True)


def resolve_entities(df: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
    ided = df[df.entity_id.astype(str).str.fullmatch(r"\d+", na=False) & df.key.notna()]
    key_to_id = ided.groupby("key")["entity_id"].agg(lambda s: s.value_counts().idxmax())
    obs = obs.copy()
    obs["entity"] = obs["key"].map(key_to_id).fillna("title:" + obs["key"])
    return obs


def score(obs: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    per_day = (obs.groupby(["entity", "date"])
               .agg(rank=("rank", "min"), name=("name", "first"),
                    publisher=("publisher", "first"), key=("key", "first"),
                    cut=("cut", "first"))
               .reset_index())
    per_day["w"] = per_day["date"].map(weights)
    return per_day


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_rows()
    days = trusted_days()
    weights = midpoint_weights(days["date"])

    obs = resolve_entities(df, chart_observations(df, days))
    per_day = score(obs, weights)

    agg = per_day.groupby("entity").agg(
        name=("name", lambda s: s.value_counts().idxmax()),
        titles=("name", lambda s: len(set(s))),
        key=("key", "first"),
        publisher=("publisher", lambda s: s.dropna().value_counts().idxmax()
                   if s.notna().any() else None),
        n_obs=("date", "nunique"),
        est_days=("w", "sum"),
        best_rank=("rank", "min"),
        median_rank=("rank", "median"),
        first_seen=("date", "min"),
        last_seen=("date", "max"),
    ).reset_index()
    depth_obs = (per_day.assign(deep=per_day["cut"] == DEEP_CUT)
                 .groupby("entity")["deep"].agg(deep_obs="sum", all_obs="size"))
    agg = agg.merge(depth_obs, left_on="entity", right_index=True)
    agg["shallow_obs"] = agg["all_obs"] - agg["deep_obs"]
    agg = agg.drop(columns=["all_obs"])
    agg["est_days"] = agg["est_days"].round(1)

    # threshold curve over the estimator, at each depth policy
    curve = []
    for label, uni in (("mixed", None), ("top24_uniform", SHALLOW_CUT),
                       ("top10_uniform", 10)):
        o = resolve_entities(df, chart_observations(df, days, uniform_cut=uni))
        pd_ = score(o, weights)
        g = pd_.groupby("entity").agg(est=("w", "sum"), n=("date", "nunique"))
        for t in (30, 45, 60, 90, 120, 180, 365):
            sel = g[(g.est >= t) & (g.n >= MIN_OBS)]
            curve.append({"policy": label, "min_est_days": t, "shows": int(len(sel))})
        if uni == SHALLOW_CUT:
            g.to_csv(OUT / "scores_top24_uniform.csv")
    pd.DataFrame(curve).to_csv(OUT / "threshold_curve.csv", index=False)

    pop = agg[(agg.est_days >= MIN_DAYS) & (agg.n_obs >= MIN_OBS)].copy()
    pop["apple_id"] = pop["entity"].where(~pop["entity"].astype(str).str.startswith("title:"))
    pop["span_days"] = (pd.to_datetime(pop["last_seen"]) -
                        pd.to_datetime(pop["first_seen"])).dt.days
    yrs = per_day.assign(year=pd.to_datetime(per_day["date"]).dt.year)
    span = yrs.groupby("entity")["year"].agg(["min", "max"])
    pop = pop.merge(span, left_on="entity", right_index=True).rename(
        columns={"min": "first_year", "max": "last_year"})

    genre_rows = df[(df.source == "podbay") & (df.genre != "all-podcasts")
                    & df.key.notna() & (df["rank"] <= 50)]
    top_genre = (genre_rows.groupby(["key", "genre"]).size().reset_index(name="n")
                 .sort_values("n", ascending=False).drop_duplicates("key")
                 .set_index("key")["genre"])
    pop["podbay_genre"] = pop["key"].map(top_genre)
    pop = pop.sort_values("est_days", ascending=False)
    pop.to_csv(OUT / "population.csv", index=False)
    agg.sort_values("est_days", ascending=False).to_csv(OUT / "all_scores.csv", index=False)

    corpus_ids = set()
    if DB.exists():
        with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as conn:
            have = pd.read_sql_query("SELECT apple_podcasts_id FROM podcasts", conn)
        corpus_ids = {str(i) for i in have["apple_podcasts_id"].dropna() if str(i).isdigit()}

    summary = {
        "snapshot_days": int(len(days)),
        "days_by_series": days.series.value_counts().to_dict(),
        "window": [days["date"].min(), days["date"].max()],
        "weight_total_days": float(weights.sum()),
        "calendar_span_days": int((pd.to_datetime(days["date"].max()) -
                                   pd.to_datetime(days["date"].min())).days),
        "rule": {"deep_cut": DEEP_CUT, "shallow_cut": SHALLOW_CUT,
                 "min_est_days": MIN_DAYS, "min_obs": MIN_OBS},
        "population": int(len(pop)),
        "with_apple_id": int(pop["apple_id"].notna().sum()),
        "renamed_while_charting": int((pop["titles"] > 1).sum()),
        "shallow_era_only": int((pop["deep_obs"] == 0).sum()),
        "deep_era_only": int((pop["shallow_obs"] == 0).sum()),
        "in_corpus_by_id": int(len(set(pop["apple_id"].dropna()) & corpus_ids)),
        "median_est_days": float(pop["est_days"].median()),
        "median_obs": float(pop["n_obs"].median()),
        "distinct_publishers": int(pop["publisher"].nunique()),
        "still_charting_2025_2026": int((pop["last_year"] >= 2025).sum()),
        "last_charted_before_2018": int((pop["last_year"] < 2018).sum()),
        "first_year_distribution": {str(k): int(v) for k, v in
                                    pop.first_year.value_counts().sort_index().items()},
        "last_year_distribution": {str(k): int(v) for k, v in
                                   pop.last_year.value_counts().sort_index().items()},
        "genre_mix": {k: int(v) for k, v in pop.podbay_genre.value_counts().head(10).items()},
        "top_publishers": {k: int(v) for k, v in pop.publisher.value_counts().head(8).items()},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(pd.DataFrame(curve).pivot(index="min_est_days", columns="policy",
                                    values="shows").to_string())
    print()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
