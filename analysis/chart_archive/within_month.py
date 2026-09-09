"""How much does a top chart move between snapshots?

Answers the question a monthly-resolution archive raises: if we only see one
snapshot a month, how much of that month's chart do we miss? Uses the two
dense series (Spotify's API in 2024, Apple's own page in 2025-26) to measure
turnover as a function of the gap between snapshots, then checks the result
against the sparse Chartable series in its few dense months.
"""

from __future__ import annotations

import glob
import itertools
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2] / "data" / "chart-archive"
PARSED = ROOT / "parsed"
SUMMARY = PARSED / "summary"

GAP_BINS = [(1, 1, "1 day"), (2, 3, "2-3 days"), (4, 9, "~1 week"),
            (10, 20, "~2 weeks"), (21, 45, "~1 month"), (46, 100, "2-3 months")]
BANDS = [(1, 10, "top 10"), (11, 50, "11-50"), (51, 100, "51-100")]


def series_frames(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "spotify/api (depth 200)": df[
            (df.source == "spotify_api") & (df.region == "us")
            & df.chart.isin(["top", "top-podcasts"]) & (df.unit == "show")],
        "apple/charts_page (depth 24)": df[
            (df.source == "apple_charts_page") & (df.genre == "All Podcasts")
            & (df.chart == "Top Shows")],
        "apple/chartable (depth 100)": df[
            (df.source == "chartable_itunes") & (df.region == "us")
            & (df.genre == "all-podcasts") & (df.unit == "podcast")],
        "apple/podbay (depth 100)": df[
            (df.source == "podbay") & (df.genre == "all-podcasts")],
    }


def daily_maps(sub: pd.DataFrame, depth: int) -> dict[pd.Timestamp, dict[str, int]]:
    """date -> {entity: rank}, keeping the deepest capture of each day."""
    sub = sub.dropna(subset=["entity_id"])
    out: dict[pd.Timestamp, dict[str, int]] = {}
    for date, g in sub.groupby("date"):
        g = g[g["rank"] <= depth].sort_values("rank").drop_duplicates("entity_id")
        if len(g) >= depth * 0.95:
            out[pd.Timestamp(date)] = dict(zip(g["entity_id"], g["rank"]))
    return out


def gap_label(days: int) -> str | None:
    for lo, hi, label in GAP_BINS:
        if lo <= days <= hi:
            return label
    return None


def turnover(maps: dict, depth: int) -> pd.DataFrame:
    rows = []
    for a, b in itertools.combinations(sorted(maps), 2):
        label = gap_label((b - a).days)
        if label is None:
            continue
        ra, rb = maps[a], maps[b]
        sa, sb = set(ra), set(rb)
        row = {"gap": label, "days": (b - a).days,
               "jaccard": len(sa & sb) / len(sa | sb)}
        shared = sa & sb
        if len(shared) >= 5:
            row["median_move"] = float(
                pd.Series([abs(ra[k] - rb[k]) for k in shared]).median())
        for lo, hi, band in BANDS:
            if lo > depth:
                continue
            band_a = {k for k, v in ra.items() if lo <= v <= min(hi, depth)}
            if not band_a:
                continue
            row[f"retain:{band}"] = len(band_a & sb) / len(band_a)
        rows.append(row)
    return pd.DataFrame(rows)


def month_coverage(maps: dict, depth: int, min_days: int = 4) -> pd.DataFrame:
    rows = []
    by_month: dict[str, list] = {}
    for date, ranks in maps.items():
        by_month.setdefault(f"{date:%Y-%m}", []).append((date, ranks))
    for month, entries in by_month.items():
        if len(entries) < min_days:
            continue
        union: set[str] = set()
        for _d, r in entries:
            union |= set(r)
        rows.append({
            "month": month, "snapshots": len(entries), "union": len(union),
            "median_single_coverage": float(pd.Series(
                [len(r) / len(union) for _d, r in entries]).median()),
            "first_last_jaccard": (
                lambda a, b: len(set(a) & set(b)) / len(set(a) | set(b))
            )(min(entries)[1], max(entries)[1]),
        })
    return pd.DataFrame(rows).sort_values("month")


def main() -> int:
    SUMMARY.mkdir(parents=True, exist_ok=True)
    df = pd.concat([pd.read_parquet(p) for p in sorted(PARSED.glob("chart_rows*.parquet"))],
                   ignore_index=True)
    df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
    df["date"] = df["captured_at"].dt.date

    depths = {"spotify/api (depth 200)": 100,
              "apple/charts_page (depth 24)": 24,
              "apple/chartable (depth 100)": 100,
              "apple/podbay (depth 100)": 100}
    tables, months, findings = [], [], {}
    for name, sub in series_frames(df).items():
        depth = depths[name]
        maps = daily_maps(sub, depth)
        findings[name] = {"usable_days": len(maps)}
        if len(maps) < 3:
            continue
        t = turnover(maps, depth)
        agg = t.groupby("gap").agg(
            pairs=("jaccard", "size"), jaccard=("jaccard", "median"),
            median_move=("median_move", "median"),
            **{f"retain_{b}": (f"retain:{b}", "median")
               for _lo, _hi, b in BANDS if f"retain:{b}" in t}).reset_index()
        agg.insert(0, "series", name)
        agg["gap"] = pd.Categorical(agg["gap"], [g[2] for g in GAP_BINS], ordered=True)
        tables.append(agg.sort_values("gap"))
        m = month_coverage(maps, depth)
        if len(m):
            m.insert(0, "series", name)
            months.append(m)
            findings[name]["dense_months"] = int(len(m))
            findings[name]["median_single_month_coverage"] = round(
                float(m["median_single_coverage"].median()), 3)
            findings[name]["median_month_union"] = float(m["union"].median())

    out = pd.concat(tables, ignore_index=True)
    out.to_csv(SUMMARY / "within_month_turnover.csv", index=False)
    mm = pd.concat(months, ignore_index=True) if months else pd.DataFrame()
    mm.to_csv(SUMMARY / "within_month_coverage.csv", index=False)
    (SUMMARY / "within_month_findings.json").write_text(
        json.dumps(findings, indent=2))

    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))
    print()
    print(mm.round(3).to_string(index=False))
    print()
    print(json.dumps(findings, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
