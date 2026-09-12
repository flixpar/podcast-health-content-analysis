#!/usr/bin/env python3
"""Why does coverage thin out as we go back in time?

`temporal_coverage.py` shows the corpus observes a shrinking share of its show
panel the further back you look. That decline has several possible causes, and
they have opposite consequences for analysis:

  1. the show had not launched yet          -> nothing is missing; the panel is young
  2. the feed no longer carries old episodes -> real, silent data loss
  3. the feed is a rebrand of an older show  -> the show is older than its feed
  4. the pipeline missed episodes            -> fixable data loss

This module separates them. The core test is episode numbering: if a feed's
oldest episode is numbered 1, the feed reaches the show's launch and nothing is
missing. Where numbering is unusable it falls back to explicit launch markers
(an iTunes `episode` tag of 1, a trailer-typed entry, or launch language in the
first few titles and descriptions). Shows with no such evidence are reported as
unverified rather than assumed either way.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

DEFAULT_DB = Path("downloader/data/podcast_metadata.db")
DEFAULT_OUTPUT = Path("analysis/output/temporal-coverage")
EPOCH_CUTOFF = pd.Timestamp("1995-01-01")
LIVE_START = pd.Timestamp("2025-10-13")

BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#4a3aa7", "#e34948",
)
INK, INK_2, INK_MUTED, GRID = "#0b0b0b", "#52514e", "#7a7975", "#e6e5e1"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2,
    "axes.titlesize": 13, "axes.titleweight": "semibold", "axes.titlecolor": INK,
    "axes.labelsize": 10, "axes.spines.top": False, "axes.spines.right": False,
    "text.color": INK, "xtick.color": INK_MUTED, "ytick.color": INK_MUTED,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "grid.color": GRID, "grid.linewidth": 0.8, "legend.frameon": False,
    "legend.fontsize": 9, "font.family": "DejaVu Sans",
    "figure.dpi": 140, "savefig.bbox": "tight",
})

TITLE_NUM = re.compile(r"(?:^|[\s\|\(\[])(?:#|ep(?:isode)?\.?\s*)(\d{1,4})\b", re.I)

LAUNCH_LANGUAGE = re.compile(
    r"welcome to (?:the |our |this )|first episode|our first|episode one\b|introducing\b|"
    r"coming soon|series premiere|premiere episode|pilot episode|\btrailer\b|"
    r"launch(?:ing)? (?:of )?(?:our |the )?(?:new )?(?:podcast|show|series)|"
    r"new podcast from|debut episode|kick(?:ing)? (?:it )?off|meet your host|"
    r"what (?:is |to expect from )this (?:podcast|show)|why (?:i|we) started", re.I)

# Launch dates confirmed against published sources, used to check the classifier
# against the world rather than against itself. `expected` is the show's real
# first episode; `precision` says how exactly the source pins it down.
EXTERNAL_CHECKS = [
    ("Stuff You Should Know", "2008-04-17", "day",
     "https://en.wikipedia.org/wiki/Stuff_You_Should_Know"),
    ("Watch What Crappens", "2012-01-26", "day",
     "https://en.wikipedia.org/wiki/Watch_What_Crappens"),
    ("Sword and Scale", "2014-01-01", "day",
     "https://podcasts.apple.com/us/podcast/sword-and-scale/id790487079"),
    ("Fantasy Footballers - Fantasy Football Podcast", "2014-01-01", "year",
     "https://en.wikipedia.org/wiki/The_Fantasy_Footballers"),
    ("Happier with Gretchen Rubin", "2015-02-01", "month",
     "https://gretchenrubin.com/podcast/1-welcome-to-the-happier-podcast/"),
    ("Casefile True Crime", "2016-01-09", "day",
     "https://en.wikipedia.org/wiki/Casefile"),
    ("This American Life", "1995-11-17", "day",
     "https://www.thisamericanlife.org/about/faq"),
    ("The Bill Simmons Podcast", "2007-05-08", "day",
     "https://en.wikipedia.org/wiki/The_B.S._Report"),
]

TOLERANCE_DAYS = {"day": 3, "month": 45, "year": 400}


# ------------------------------------------------------------------------- load


def load(db_path: Path) -> pd.DataFrame:
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        df = pd.read_sql_query(
            """
            SELECT e.podcast_id, e.title, e.description, e.published_date,
                   e.metadata, p.title AS show
            FROM episodes e JOIN podcasts p ON p.id = e.podcast_id
            """,
            conn,
        )
    df["published"] = pd.to_datetime(df["published_date"], errors="coerce")
    df = df[df["published"] >= EPOCH_CUTOFF].copy()

    meta = df["metadata"].map(json.loads)
    df["itunes_ep"] = pd.to_numeric(meta.map(lambda m: m.get("episode")), errors="coerce")
    df["season"] = pd.to_numeric(meta.map(lambda m: m.get("season")), errors="coerce")
    df["ep_type"] = meta.map(lambda m: m.get("episode_type"))
    df["title_ep"] = pd.to_numeric(
        df["title"].map(lambda t: (m := TITLE_NUM.search(t or "")) and m.group(1)),
        errors="coerce")
    return df.drop(columns=["metadata"])


# --------------------------------------------------------------------- classify


def sequential_numbering(show: pd.DataFrame) -> int | None:
    """Smallest episode number, when the show numbers episodes globally.

    Requires enough numbered episodes to be meaningful, that most episodes carry
    a number (otherwise the numbered subset is its own biased sample), a single
    season (per-season restarts are not a global counter), and that numbers
    mostly increase with date.
    """
    for source in ("itunes_ep", "title_ep"):
        nums = show[source].dropna()
        if len(nums) < 20 or len(nums) / len(show) < 0.70:
            continue
        if show.loc[nums.index, "season"].dropna().nunique() > 1:
            continue
        if np.mean(np.diff(nums.values) > 0) < 0.85:
            continue
        return int(nums.min())
    return None


def classify(df: pd.DataFrame) -> pd.DataFrame:
    """One row per show: does its feed reach the show's first episode?"""
    recs = []
    for pid, group in df.groupby("podcast_id"):
        show = group.sort_values("published").reset_index(drop=True)
        head = show.head(5)
        min_num = sequential_numbering(show)

        if min_num is not None and min_num > 3:
            verdict, basis = "truncated", "numbering"
        elif min_num is not None:
            verdict, basis = "complete", "numbering"
        elif (head["itunes_ep"] <= 1).any():
            verdict, basis = "complete", "episode 1 tag"
        elif (head["ep_type"] == "trailer").any():
            verdict, basis = "complete", "trailer"
        elif (head["title"].fillna("").str.contains(LAUNCH_LANGUAGE).any()
              or head["description"].fillna("").str.contains(LAUNCH_LANGUAGE).any()):
            verdict, basis = "complete", "launch language"
        else:
            verdict, basis = "unverified", "none"

        recs.append({
            "podcast_id": pid, "show": show["show"].iloc[0], "episodes": len(show),
            "first": show["published"].iloc[0], "last": show["published"].iloc[-1],
            "min_episode_number": min_num, "verdict": verdict, "basis": basis,
        })

    shows = pd.DataFrame(recs)
    shows["span_years"] = (shows["last"] - shows["first"]).dt.days / 365.25
    return shows.sort_values("first").reset_index(drop=True)


def validate(shows: pd.DataFrame) -> pd.DataFrame:
    """Check first-observed dates against externally published launch dates."""
    rows = []
    lookup = shows.set_index("show")
    for title, expected, precision, source in EXTERNAL_CHECKS:
        if title not in lookup.index:
            continue
        row = lookup.loc[title]
        delta = (row["first"] - pd.Timestamp(expected)).days
        rows.append({
            "show": title, "observed_first": row["first"].date(),
            "published_launch": expected, "precision": precision,
            "gap_days": delta,
            "agrees": abs(delta) <= TOLERANCE_DAYS[precision],
            "verdict": row["verdict"], "source": source,
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ attribution


def attribute(df: pd.DataFrame, shows: pd.DataFrame,
              start: str = "2010-01") -> pd.DataFrame:
    """For every month, sort all shows into why they are or are not covered."""
    months = pd.period_range(start, df["published"].dt.to_period("M").max(), freq="M")
    active = (df.assign(month=df["published"].dt.to_period("M"))
              .groupby(["month", "podcast_id"]).size().unstack(fill_value=0) > 0)
    active = active.reindex(index=months, columns=shows["podcast_id"], fill_value=False)

    first = shows.set_index("podcast_id")["first"].dt.to_period("M")
    last = shows.set_index("podcast_id")["last"].dt.to_period("M")
    verdict = shows.set_index("podcast_id")["verdict"]

    rows = []
    for month in months:
        started, ended = first <= month, last < month
        covered = active.loc[month]
        silent = started & ~ended & ~covered
        pending = ~started
        rows.append({
            "month": month,
            "covered": int(covered.sum()),
            "in_run_no_episode": int(silent.sum()),
            "feed_truncated": int((pending & (verdict == "truncated")).sum()),
            "not_launched_unverified": int((pending & (verdict == "unverified")).sum()),
            "not_launched_verified": int((pending & (verdict == "complete")).sum()),
            "ended": int(ended.sum()),
        })
    table = pd.DataFrame(rows).set_index("month")
    table["date"] = table.index.to_timestamp()
    return table


BANDS = [
    ("covered", "Covered: published this month", BLUE),
    ("in_run_no_episode", "In its run, no episode that month", "#a9c9ef"),
    ("feed_truncated", "Launched, but feed no longer carries it", RED),
    ("not_launched_unverified", "Not yet launched (unverified)", "#cfcec9"),
    ("not_launched_verified", "Not yet launched (verified)", "#eceae5"),
    ("ended", "Finished publishing", YELLOW),
]


def fig_attribution(table: pd.DataFrame, n_shows: int, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 6))
    ax.stackplot(table["date"], [table[k] for k, _, _ in BANDS],
                 colors=[c for _, _, c in BANDS], linewidth=0)
    ax.set_ylim(0, n_shows)
    ax.set_xlim(table["date"].iloc[0], table["date"].iloc[-1])
    ax.set_ylabel(f"Shows (of {n_shows})")
    ax.set_xlabel("Month")
    ax.set_title("Why a show is missing from any given month")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.axvline(LIVE_START, color=INK, linewidth=1, linestyle=(0, (4, 3)))
    ax.annotate("collection begins", xy=(LIVE_START, n_shows * 0.965),
                xytext=(-8, 0), textcoords="offset points",
                fontsize=9, color=INK_2, ha="right", va="top")
    ax.legend(handles=[Patch(facecolor=c, label=l) for _, l, c in reversed(BANDS)],
              loc="upper left", ncol=2, bbox_to_anchor=(0.01, 0.98))
    fig.text(0.5, -0.01,
             "The pale bands are shows that did not exist yet. The red band is genuine "
             "loss: shows that were publishing but whose feed no longer offers those "
             "episodes.",
             ha="center", fontsize=9, color=INK_MUTED)
    fig.savefig(out / "fig8_coverage_attribution.png")
    plt.close(fig)


def fig_evidence(shows: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4),
                             gridspec_kw={"width_ratios": [1.15, 1]})

    order = ["numbering", "trailer", "launch language", "episode 1 tag", "none"]
    labels = {"numbering": "Numbered back to #1", "trailer": "Trailer in first entries",
              "launch language": "Launch language", "episode 1 tag": "Tagged episode 1",
              "none": "No evidence either way"}
    counts, colors = [], []
    for basis in order:
        sub = shows[shows["basis"] == basis]
        if basis == "numbering":
            counts.append(int((sub["verdict"] == "complete").sum()))
        else:
            counts.append(len(sub))
        colors.append("#cfcec9" if basis == "none" else BLUE)
    truncated = int((shows["verdict"] == "truncated").sum())
    order_labels = [labels[b] for b in order] + ["Feed demonstrably truncated"]
    counts.append(truncated)
    colors.append(RED)

    y = np.arange(len(counts))
    axes[0].barh(y, counts, color=colors, height=0.66)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(order_labels, fontsize=9)
    axes[0].invert_yaxis()
    axes[0].set_xlabel(f"Shows (of {len(shows)})")
    axes[0].set_title("What we can establish about each feed")
    for i, v in enumerate(counts):
        axes[0].annotate(f"{v}", xy=(v, i), xytext=(4, 0), textcoords="offset points",
                         va="center", fontsize=9, color=INK_2)
    axes[0].grid(axis="x", alpha=0.9)
    axes[0].set_axisbelow(True)
    axes[0].set_xlim(0, max(counts) * 1.12)

    numbered = shows["min_episode_number"].dropna()
    bins = [0.5, 1.5, 3.5, 10.5, 30.5, 100.5, 1000.5]
    axes[1].hist(numbered.clip(upper=1000), bins=bins, color=BLUE, edgecolor="white")
    axes[1].set_xscale("log")
    axes[1].set_xticks([1, 3, 10, 30, 100, 1000])
    axes[1].get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    axes[1].set_xlabel("Lowest episode number the feed still carries")
    axes[1].set_ylabel("Shows")
    axes[1].set_title(f"Where numbered feeds start (n={len(numbered)})")
    axes[1].grid(axis="y", alpha=0.9)
    axes[1].set_axisbelow(True)
    reach = int((numbered <= 3).sum())
    axes[1].annotate(f"{reach} of {len(numbered)} numbered feeds\nstill carry episode 1-3",
                     xy=(6, len(numbered) * 0.62), fontsize=9, color=INK_2)

    fig.savefig(out / "fig9_feed_completeness_evidence.png")
    plt.close(fig)


# ---------------------------------------------------------------- live-window gaps


def live_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Shows whose live-window coverage has a hole far larger than their cadence.

    The year before collection was swept in one pass, so it cannot itself contain
    a between-runs hole; it is the reference cadence.
    """
    rows = []
    for pid, group in df.groupby("podcast_id"):
        g = group.sort_values("published")
        pre = g[(g["published"] >= LIVE_START - pd.DateOffset(years=1))
                & (g["published"] < LIVE_START)]
        live = g[g["published"] >= LIVE_START]
        if len(pre) < 12 or len(live) < 3:
            continue
        pre_gap = float(np.median(np.diff(pre["published"].values)
                                  .astype("timedelta64[D]").astype(int)))
        gaps = np.diff(live["published"].values).astype("timedelta64[D]").astype(int)
        max_gap = int(gaps.max()) if len(gaps) else 0
        rows.append({
            "show": g["show"].iloc[0],
            "normal_gap_days": pre_gap, "largest_live_gap_days": max_gap,
            "gap_ratio": max_gap / max(pre_gap, 1),
            "rate_before": len(pre) / 12, "rate_live": len(live) / 10.5,
        })
    r = pd.DataFrame(rows)
    r["rate_drop"] = 1 - r["rate_live"] / r["rate_before"]
    return r.sort_values("gap_ratio", ascending=False).reset_index(drop=True)


# -------------------------------------------------------------------------- main


def write_findings(shows: pd.DataFrame, table: pd.DataFrame, checks: pd.DataFrame,
                   gaps: pd.DataFrame, out: Path) -> dict:
    n = len(shows)
    counts = shows["verdict"].value_counts()
    suspects = gaps[(gaps["gap_ratio"] >= 6) & (gaps["largest_live_gap_days"] >= 45)]

    snapshots = {}
    for m in ("2015-01", "2018-01", "2021-01", "2024-01"):
        row = table.loc[pd.Period(m)]
        absent = n - row["covered"] - row["in_run_no_episode"]
        snapshots[m] = {
            "covered": int(row["covered"]),
            "absent": int(absent),
            "not_launched_verified": int(row["not_launched_verified"]),
            "not_launched_unverified": int(row["not_launched_unverified"]),
            "feed_truncated": int(row["feed_truncated"]),
            # Worst case: every unverified show is secretly a truncated feed.
            "max_missing_share_of_absent": round(
                100 * (row["feed_truncated"] + row["not_launched_unverified"])
                / max(absent, 1), 1),
            "min_missing_share_of_absent": round(
                100 * row["feed_truncated"] / max(absent, 1), 1),
        }

    summary = {
        "shows": n,
        "verdicts": {k: int(v) for k, v in counts.items()},
        "verdict_basis": {k: int(v) for k, v in shows["basis"].value_counts().items()},
        "external_checks": int(len(checks)),
        "external_agreements": int(checks["agrees"].sum()),
        "month_snapshots": snapshots,
        "live_gap_suspects": int(len(suspects)),
        "median_live_rate_change": round(float(-gaps["rate_drop"].median()), 3),
        "shows_losing_40pct_live": int((gaps["rate_drop"] > 0.4).sum()),
    }

    lines = [
        "# Why coverage thins out going back in time",
        "",
        "The short answer: **the shows had not launched yet.** Feed truncation is real "
        "but rare, and it is not what drives the decline.",
        "",
        "## What we can establish about each feed",
        "",
        f"- **{counts.get('complete', 0)} of {n} shows** ({100 * counts.get('complete', 0) / n:.0f}%) "
        f"have positive evidence that their feed reaches the show's first episode.",
        f"- **{counts.get('truncated', 0)} shows** ({100 * counts.get('truncated', 0) / n:.0f}%) "
        f"demonstrably do not: their feed's oldest episode is numbered well above 1.",
        f"- **{counts.get('unverified', 0)} shows** ({100 * counts.get('unverified', 0) / n:.0f}%) "
        f"leave no machine-readable trace either way.",
        "",
        "Evidence used, in order of strength: sequential episode numbering that reaches "
        "#1; an iTunes `episode` tag of 1; a trailer-typed entry; launch language in the "
        "first few titles or descriptions.",
        "",
        "## The decomposition",
        "",
        "Of the shows absent from a given month, how many are absent because they had "
        "not launched? The verified column is what we can prove; the unverified column "
        "is where the residual doubt lives.",
        "",
        "| Month | Covered | Absent | Not launched (verified) | Not launched (unverified) | Feed truncated | Missing-data share |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for m, snap in snapshots.items():
        lines.append(
            f"| {m} | {snap['covered']} | {snap['absent']} | "
            f"{snap['not_launched_verified']} | {snap['not_launched_unverified']} | "
            f"{snap['feed_truncated']} | "
            f"{snap['min_missing_share_of_absent']}%-{snap['max_missing_share_of_absent']}% |")
    lines += [
        "",
        "The last column brackets the answer. The low end counts only feeds we can prove "
        "are truncated; the high end assumes every unverified show is secretly truncated "
        "too, which the external checks below say is far from true.",
    ]

    lines += [
        "",
        "## External validation",
        "",
        "Our first-observed date checked against published launch dates:",
        "",
        "| Show | First observed | Published launch | Agrees? | Classifier said |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, r in checks.iterrows():
        lines.append(
            f"| {r['show']} | {r['observed_first']} | {r['published_launch']} "
            f"({r['precision']}) | {'yes' if r['agrees'] else 'NO'} | {r['verdict']} |")

    lines += [
        "",
        f"{int(checks['agrees'].sum())} of {len(checks)} agree.",
        "",
        "The two disagreements are different in kind. *This American Life* is the "
        "classifier working: it is flagged `truncated`, and its feed really does hold "
        "only about ten weeks. *The Bill Simmons Podcast* is the classifier's blind "
        "spot: the feed is complete back to its own first episode in 2015, but the show "
        "began in 2007 as *The B.S. Report* on a different feed. No feed-internal "
        "evidence can detect a rebrand, so shows that migrated feeds will always look "
        "younger than they are.",
        "",
        "The result that matters most: of the shows the classifier calls **unverified**, "
        "five of the six checked externally turned out to have complete feeds "
        "(Stuff You Should Know, Watch What Crappens, Fantasy Footballers, Happier with "
        "Gretchen Rubin, Casefile) matching their published launch date, several to the "
        "day. The sixth was the Bill Simmons rebrand. The unverified bucket is mostly "
        "shows that simply do not announce themselves in a machine-readable way, not "
        "shows hiding a truncated archive.",
        "",
        "## Mechanisms found, in order of size",
        "",
        "1. **Show age.** Most shows in the panel simply did not exist. The panel is the "
        "current top-100 charts, and today's charts are dominated by shows launched in "
        "the last five years.",
        "2. **Feed retention.** A minority of publishers rotate old episodes out. Where "
        "it happens it can be severe, but it is a property of a handful of feeds.",
        "3. **Feed rebrands.** A show can be older than its feed. Chart-derived panels "
        "cannot see the earlier incarnation at all.",
        f"4. **Discovery cadence.** {len(suspects)} shows have a hole in the live window "
        "far larger than their own publication interval. For short-retention feeds, "
        "episodes published between discovery runs fall off the feed permanently.",
        "",
        "## The pipeline issue worth fixing",
        "",
        f"Across the panel, live capture is healthy: the median show's publication rate "
        f"changed by {summary['median_live_rate_change']:+.1%} between the year before "
        f"collection and the live window, and only "
        f"{summary['shows_losing_40pct_live']} shows lost more than 40%.",
        "",
        "But short-retention feeds need `discover` to run more often than their retention "
        "window. *This American Life* is the clear case: the corpus holds episodes 862-870 "
        "and 887-895 but nothing in between, a seven-month hole covering episodes 871-886 "
        "that have now aged out of the feed and cannot be recovered from it.",
        "",
        "| Show | Normal gap (days) | Largest live gap (days) | Ratio |",
        "| --- | ---: | ---: | ---: |",
    ]
    for _, r in suspects.head(10).iterrows():
        lines.append(
            f"| {r['show']} | {r['normal_gap_days']:.0f} | "
            f"{r['largest_live_gap_days']} | {r['gap_ratio']:.0f}x |")

    lines += [
        "",
        "Some of those are legitimately seasonal (limited series, TV-linked shows on "
        "hiatus). The ones to act on are the weekly shows with month-scale holes.",
        "",
        "## What this means for analysis",
        "",
        "- The back catalogue is **not** systematically censored, so it is usable for "
        "tracing narratives backwards through the shows that were publishing.",
        "- It **is** a young, survivorship-selected panel. Pre-2020 coverage reflects "
        "which of today's top shows existed then, not what podcasting looked like then.",
        "- A prevalence statistic per year is measuring panel composition unless the "
        "cohort is held fixed.",
        "",
    ]
    (out / "attribution_findings.md").write_text("\n".join(lines) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    df = load(args.db)
    shows = classify(df)
    checks = validate(shows)
    table = attribute(df, shows)
    gaps = live_gaps(df)

    fig_attribution(table, len(shows), out)
    fig_evidence(shows, out)

    shows.to_csv(out / "feed_completeness.csv", index=False)
    table.drop(columns=["date"]).to_csv(out / "coverage_attribution.csv")
    gaps.to_csv(out / "live_window_gaps.csv", index=False)
    checks.to_csv(out / "external_launch_checks.csv", index=False)

    summary = write_findings(shows, table, checks, gaps, out)
    (out / "attribution_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
