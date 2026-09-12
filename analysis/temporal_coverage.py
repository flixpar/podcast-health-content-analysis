#!/usr/bin/env python3
"""Temporal coverage analysis of the collected podcast episode corpus.

Reads the pipeline's SQLite metadata read-only and characterises *when* the
corpus covers, not what it says: the publication-date distribution, how far each
show's back catalogue reaches, how complete the show panel is in any given
month, and whether transcript availability is biased across time.

Outputs figures, a monthly table, a machine-readable summary, and a findings
memo under `analysis/output/temporal-coverage/`.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

DEFAULT_DB = Path("downloader/data/podcast_metadata.db")
DEFAULT_OUTPUT = Path("analysis/output/temporal-coverage")

# Episodes dated before this are feed artefacts (missing/zero pubDate), not real
# publications, and are excluded from every time series.
EPOCH_CUTOFF = pd.Timestamp("1995-01-01")

# Reference categorical palette (light mode), assigned in fixed slot order.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#4a3aa7", "#e34948",
)
INK, INK_2, INK_MUTED, GRID = "#0b0b0b", "#52514e", "#7a7975", "#e6e5e1"
SEQ_BLUE = LinearSegmentedColormap.from_list(
    "seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#0d366b"]
)

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlesize": 13,
    "axes.titleweight": "semibold",
    "axes.titlecolor": INK,
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "text.color": INK,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "font.family": "DejaVu Sans",
    "figure.dpi": 140,
    "savefig.bbox": "tight",
})


# --------------------------------------------------------------------------- load


def load(db_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (episodes, podcasts) frames from a read-only connection."""
    uri = f"file:{db_path}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        episodes = pd.read_sql_query(
            """
            SELECT e.id, e.podcast_id, e.published_date, e.duration_seconds,
                   e.status, e.has_rss_transcript, e.title, p.title AS podcast_title
            FROM episodes e
            JOIN podcasts p ON p.id = e.podcast_id
            """,
            conn,
        )
        podcasts = pd.read_sql_query(
            """
            SELECT p.id, p.title, p.categories,
                   GROUP_CONCAT(c.chart) AS charts
            FROM podcasts p
            LEFT JOIN podcast_charts c ON c.podcast_id = p.id
            GROUP BY p.id
            """,
            conn,
        )

    episodes["published"] = pd.to_datetime(episodes["published_date"], errors="coerce")
    episodes["month"] = episodes["published"].dt.to_period("M")
    episodes["hours"] = episodes["duration_seconds"] / 3600.0
    episodes["transcribed"] = episodes["status"] == "transcribed"
    return episodes, podcasts


# ----------------------------------------------------------------------- aggregate


def monthly_table(valid: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar month, reindexed over the full span (gaps included)."""
    grouped = valid.groupby("month")
    table = pd.DataFrame({
        "episodes": grouped.size(),
        "podcasts": grouped["podcast_id"].nunique(),
        "transcribed": grouped["transcribed"].sum(),
        "rss_transcripts": grouped["has_rss_transcript"].sum(),
        "hours": grouped["hours"].sum(),
        "median_minutes": grouped["duration_seconds"].median() / 60.0,
    })
    full = pd.period_range(table.index.min(), table.index.max(), freq="M")
    table = table.reindex(full)
    counts = ["episodes", "podcasts", "transcribed", "rss_transcripts", "hours"]
    table[counts] = table[counts].fillna(0)
    table.index.name = "month"
    table["transcribed_pct"] = 100 * table["transcribed"] / table["episodes"].replace(0, np.nan)
    table["date"] = table.index.to_timestamp()
    return table


def per_podcast(valid: pd.DataFrame) -> pd.DataFrame:
    """First/last episode, count and density for each show."""
    grouped = valid.groupby(["podcast_id", "podcast_title"])
    spans = grouped["published"].agg(["min", "max", "size"]).reset_index()
    spans.columns = ["podcast_id", "title", "first", "last", "episodes"]
    spans["span_days"] = (spans["last"] - spans["first"]).dt.days
    spans["span_years"] = spans["span_days"] / 365.25
    spans["eps_per_month"] = spans["episodes"] / (spans["span_days"] / 30.44).clip(lower=1)
    spans["hours"] = grouped["hours"].sum().values
    spans["transcribed"] = grouped["transcribed"].sum().values
    return spans.sort_values("first").reset_index(drop=True)


# -------------------------------------------------------------------------- figures


def _month_axis(ax: plt.Axes, years: int = 2) -> None:
    ax.xaxis.set_major_locator(mdates.YearLocator(years))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", alpha=0.9)
    ax.set_axisbelow(True)


def fig_volume(table: pd.DataFrame, live_start: pd.Timestamp, out: Path) -> None:
    """Monthly episode volume, and the episode length behind the audio-hour total."""
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    for ax, col, color, label in (
        (axes[0], "episodes", BLUE, "Episodes published"),
        (axes[1], "median_minutes", ORANGE, "Median episode length\n(minutes)"),
    ):
        ax.fill_between(table["date"], table[col], color=color, alpha=0.16, linewidth=0)
        ax.plot(table["date"], table[col], color=color, linewidth=2)
        ax.set_ylabel(label)
        ax.axvline(live_start, color=INK_MUTED, linewidth=1, linestyle=(0, (4, 3)))
        _month_axis(ax)
    axes[1].set_ylim(bottom=0)

    axes[0].annotate(
        "collection begins\n2025-10-13",
        xy=(live_start, table["episodes"].max() * 0.94),
        xytext=(-96, 0), textcoords="offset points",
        fontsize=9, color=INK_2, ha="left", va="top",
    )
    axes[0].set_title("Corpus volume by month of publication")
    axes[1].set_xlabel("Month published")
    fig.text(
        0.5, -0.01,
        "Everything left of the dashed line is back catalogue harvested from RSS at collection time; "
        "everything right of it was captured live.",
        ha="center", fontsize=9, color=INK_MUTED,
    )
    fig.savefig(out / "fig1_volume_by_month.png")
    plt.close(fig)


def fig_panel(table: pd.DataFrame, n_shows: int, live_start: pd.Timestamp, out: Path) -> None:
    """How much of the show panel is actually observed in each month."""
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    pct = 100 * table["podcasts"] / n_shows
    axes[0].fill_between(table["date"], pct, color=AQUA, alpha=0.16, linewidth=0)
    axes[0].plot(table["date"], pct, color=AQUA, linewidth=2)
    axes[0].axhline(90, color=INK_MUTED, linewidth=1, linestyle=(0, (4, 3)))
    axes[0].annotate("90% of shows", xy=(table["date"].iloc[3], 82), fontsize=9, color=INK_2)
    axes[0].set_ylabel(f"Shows with ≥1 episode\n(% of {n_shows})")
    axes[0].set_ylim(0, 105)
    axes[0].set_title("Panel completeness: share of shows observed in each month")

    median_eps = (table["episodes"] / table["podcasts"].replace(0, np.nan))
    axes[1].plot(table["date"], median_eps, color=VIOLET, linewidth=2)
    axes[1].set_ylabel("Mean episodes per\nobserved show")
    axes[1].set_xlabel("Month published")

    for ax in axes:
        ax.axvline(live_start, color=INK_MUTED, linewidth=1, linestyle=(0, (4, 3)))
        _month_axis(ax)

    fig.savefig(out / "fig2_panel_completeness.png")
    plt.close(fig)


def fig_backcatalog(spans: pd.DataFrame, table: pd.DataFrame, out: Path) -> None:
    """How deep each show's archive reaches, and where the corpus mass sits."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))

    years = np.sort(spans["span_years"].values)
    survival = 100 * (1 - np.arange(len(years)) / len(years))
    axes[0].step(years, survival, where="post", color=BLUE, linewidth=2)
    axes[0].fill_between(years, survival, step="post", color=BLUE, alpha=0.14, linewidth=0)
    for mark in (1, 3, 5, 10):
        share = 100 * (spans["span_years"] >= mark).mean()
        axes[0].plot([mark], [share], marker="o", markersize=7, color=BLUE,
                     markeredgecolor="white", markeredgewidth=1.5, zorder=3)
        axes[0].annotate(f"{share:.0f}% reach\n≥{mark}y", xy=(mark, share),
                         xytext=(6, 6), textcoords="offset points",
                         fontsize=8.5, color=INK_2)
    axes[0].set_xlabel("Archive depth (years between first and last episode)")
    axes[0].set_ylabel("Share of shows (%)")
    axes[0].set_title("Back-catalogue depth per show")
    axes[0].grid(axis="y", alpha=0.9)
    axes[0].set_axisbelow(True)

    cum = 100 * table["episodes"].cumsum() / table["episodes"].sum()
    axes[1].plot(table["date"], cum, color=ORANGE, linewidth=2)
    axes[1].fill_between(table["date"], cum, color=ORANGE, alpha=0.14, linewidth=0)
    for q in (25, 50, 75):
        hit = table["date"][cum >= q].iloc[0]
        axes[1].plot([hit], [q], marker="o", markersize=7, color=ORANGE,
                     markeredgecolor="white", markeredgewidth=1.5, zorder=3)
        axes[1].annotate(f"{q}% by {hit:%b %Y}", xy=(hit, q), xytext=(-4, 10),
                         textcoords="offset points", fontsize=8.5, color=INK_2, ha="right")
    axes[1].set_xlabel("Month published")
    axes[1].set_ylabel("Cumulative share of episodes (%)")
    axes[1].set_title("Where the corpus mass sits in time")
    _month_axis(axes[1], years=4)

    fig.savefig(out / "fig3_backcatalog_depth.png")
    plt.close(fig)


def fig_spans(spans: pd.DataFrame, out: Path) -> None:
    """One bar per show, first to last episode, shaded by publication density."""
    ordered = spans.sort_values("first").reset_index(drop=True)
    height = max(6.0, 0.052 * len(ordered) + 2.0)
    fig, ax = plt.subplots(figsize=(11, height))

    density = ordered["eps_per_month"].clip(upper=20)
    norm = plt.Normalize(0, 20)
    for i, row in ordered.iterrows():
        ax.barh(i, row["last"] - row["first"], left=row["first"], height=0.72,
                color=SEQ_BLUE(norm(min(row["eps_per_month"], 20))), linewidth=0)

    ax.set_ylim(-1, len(ordered))
    ax.invert_yaxis()
    ax.set_yticks([])
    ax.set_ylabel(f"{len(ordered)} shows, ordered by first episode")
    ax.set_xlabel("Episode publication window")
    ax.set_title("Per-show coverage spans")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="x", alpha=0.9)
    ax.set_axisbelow(True)

    cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=SEQ_BLUE), ax=ax,
                        fraction=0.025, pad=0.02)
    cbar.set_label("Episodes per month (capped at 20)", color=INK_2, fontsize=9)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(labelsize=8, color=INK_MUTED, labelcolor=INK_MUTED)

    # Label every 20th show. Consecutive rows are ~3pt apart, so labelling
    # neighbours would overprint; a fixed stride keeps the ordering legible.
    # Labels sit in the empty margin to the left of each bar, except for the
    # earliest shows, which start too close to the axis for that to fit.
    label_box = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.2)
    for i in range(0, len(ordered), 20):
        row = ordered.iloc[i]
        left = row["first"] > pd.Timestamp("2013-01-01")
        ax.annotate(f"{row['title'][:40]}  ({row['first']:%Y})",
                    xy=(row["first"], i), xytext=(-5 if left else 5, 0),
                    textcoords="offset points", fontsize=7.5, color=INK_2,
                    va="center", ha="right" if left else "left", bbox=label_box)

    fig.savefig(out / "fig4_coverage_spans.png")
    plt.close(fig)


def fig_transcripts(table: pd.DataFrame, live_start: pd.Timestamp, out: Path) -> None:
    """Transcript availability over time: counts and share."""
    recent = table[table["date"] >= "2018-01-01"]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    untranscribed = recent["episodes"] - recent["transcribed"]
    axes[0].stackplot(
        recent["date"],
        [recent["transcribed"], untranscribed],
        colors=[BLUE, "#d8d7d2"], linewidth=0,
    )
    axes[0].set_ylabel("Episodes per month")
    axes[0].set_title("Transcript availability by month of publication")
    axes[0].legend(
        handles=[Patch(facecolor=BLUE, label="Transcribed"),
                 Patch(facecolor="#d8d7d2", label="Audio only")],
        loc="upper left", ncol=2,
    )

    axes[1].plot(recent["date"], recent["transcribed_pct"], color=BLUE, linewidth=2)
    overall = 100 * table["transcribed"].sum() / table["episodes"].sum()
    axes[1].axhline(overall, color=ORANGE, linewidth=1.5, linestyle=(0, (4, 3)))
    axes[1].annotate(f"corpus mean {overall:.0f}%", xy=(recent["date"].iloc[2], overall + 1.5),
                     fontsize=9, color=ORANGE)
    axes[1].set_ylabel("Transcribed (%)")
    axes[1].set_xlabel("Month published")
    axes[1].set_ylim(0, 100)

    for ax in axes:
        ax.axvline(live_start, color=INK_MUTED, linewidth=1, linestyle=(0, (4, 3)))
        ax.xaxis.set_major_locator(mdates.YearLocator(1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.grid(axis="y", alpha=0.9)
        ax.set_axisbelow(True)

    fig.savefig(out / "fig5_transcript_coverage.png")
    plt.close(fig)


def fig_cadence(valid: pd.DataFrame, live_start: pd.Timestamp, out: Path) -> None:
    """Weekly publication volume in the live window, plus the weekday/hour rhythm.

    Publication timestamps come from feedparser's `published_parsed`, which is
    normalised to UTC, so the hour panel is UTC and not the publisher's clock.
    """
    live = valid[valid["published"] >= live_start]
    weekly = live.set_index("published").resample("W")["id"].size()
    weekly = weekly.iloc[1:-1]  # drop partial first/last weeks

    fig = plt.figure(figsize=(12, 4.6))
    grid = fig.add_gridspec(1, 3, width_ratios=[2, 1, 1], wspace=0.32)

    ax0 = fig.add_subplot(grid[0, 0])
    ax0.plot(weekly.index, weekly.values, color=BLUE, linewidth=1.8)
    ax0.axhline(weekly.mean(), color=ORANGE, linewidth=1.5, linestyle=(0, (4, 3)))
    ax0.annotate(f"mean {weekly.mean():.0f}/week", xy=(weekly.index[2], weekly.mean() + 12),
                 fontsize=9, color=ORANGE)
    ax0.set_ylabel("Episodes per week")
    ax0.set_title("Weekly publication volume, live window")
    ax0.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax0.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax0.tick_params(axis="x", rotation=0)
    ax0.grid(axis="y", alpha=0.9)
    ax0.set_axisbelow(True)

    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    by_day = live["published"].dt.dayofweek.value_counts().reindex(range(7), fill_value=0)
    ax1 = fig.add_subplot(grid[0, 1])
    ax1.bar(names, by_day.values, color=AQUA, width=0.7)
    ax1.set_title("By weekday")
    ax1.set_ylabel("Episodes")
    ax1.tick_params(axis="x", rotation=45)
    ax1.grid(axis="y", alpha=0.9)
    ax1.set_axisbelow(True)

    by_hour = live["published"].dt.hour.value_counts().reindex(range(24), fill_value=0)
    ax2 = fig.add_subplot(grid[0, 2])
    ax2.bar(by_hour.index, by_hour.values, color=VIOLET, width=0.8)
    ax2.set_title("By hour (UTC)")
    ax2.set_ylabel("Episodes")
    ax2.set_xlabel("Hour of day")
    ax2.set_xticks([0, 6, 12, 18, 23])
    ax2.grid(axis="y", alpha=0.9)
    ax2.set_axisbelow(True)

    fig.savefig(out / "fig6_cadence.png")
    plt.close(fig)


def fig_heatmap(valid: pd.DataFrame, spans: pd.DataFrame, live_start: pd.Timestamp,
                out: Path) -> None:
    """Per-show monthly output in the live window, each row scaled to its own peak.

    Absolute counts span two orders of magnitude across shows, so a shared scale
    would render every row but the busiest as one flat colour. Row-relative
    shading answers the coverage question instead: a pale cell is a month in
    which that show produced far less than it normally does.
    """
    live = valid[valid["published"] >= live_start].copy()
    top_ids = spans.nlargest(35, "episodes")["podcast_id"]
    live = live[live["podcast_id"].isin(top_ids)]

    pivot = live.pivot_table(index="podcast_title", columns="month",
                             values="id", aggfunc="size", fill_value=0)
    totals = pivot.sum(axis=1).sort_values(ascending=False)
    pivot = pivot.loc[totals.index]
    relative = pivot.div(pivot.max(axis=1), axis=0)

    fig, ax = plt.subplots(figsize=(11, 0.30 * len(pivot) + 2.8))
    mesh = ax.pcolormesh(np.arange(pivot.shape[1] + 1), np.arange(pivot.shape[0] + 1),
                         relative.values, cmap=SEQ_BLUE, vmin=0, vmax=1,
                         edgecolors="white", linewidth=1.2)

    ax.set_yticks(np.arange(pivot.shape[0]) + 0.5)
    ax.set_yticklabels([f"{t[:40]}  ({totals[t]:,})" for t in pivot.index], fontsize=8)
    ax.set_xticks(np.arange(pivot.shape[1]) + 0.5)
    ax.set_xticklabels([str(m) for m in pivot.columns], fontsize=8, rotation=90)
    ax.invert_yaxis()
    ax.set_title("Month-to-month output of the 35 largest shows, relative to each show's peak")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    cbar = fig.colorbar(mesh, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label("Share of that show's busiest month", color=INK_2, fontsize=9)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(labelsize=8, color=INK_MUTED, labelcolor=INK_MUTED)
    # The trailing month is truncated at the snapshot date, so its paler column
    # is an artefact of when collection stopped, not a real drop in output.
    fig.text(0.5, -0.005,
             f"Row labels carry each show's episode total for the window. "
             f"{pivot.columns[-1]} is partial (through {valid['published'].max():%b %d}).",
             ha="center", fontsize=9, color=INK_MUTED)

    fig.savefig(out / "fig7_show_month_heatmap.png")
    plt.close(fig)


# -------------------------------------------------------------------------- summary


def build_summary(episodes: pd.DataFrame, valid: pd.DataFrame, table: pd.DataFrame,
                  spans: pd.DataFrame, live_start: pd.Timestamp) -> dict:
    live = table[table["date"] >= live_start]
    last12 = valid[valid["published"] >= valid["published"].max() - pd.DateOffset(months=12)]
    cum = table["episodes"].cumsum() / table["episodes"].sum()

    stamp_groups = valid.groupby(["podcast_id", "published_date"])["title"]
    sizes, distinct = stamp_groups.size(), stamp_groups.nunique()
    collided = sizes > 1
    dupe_rows = int(sizes[collided & (distinct == 1)].sum())
    batch_rows = int(sizes[collided & (distinct > 1)].sum())
    empty_months = int((table["episodes"] == 0).sum())

    return {
        "episodes_total": int(len(episodes)),
        "episodes_dated": int(len(valid)),
        "episodes_undated": int(len(episodes) - len(valid)),
        "shows_total": int(episodes["podcast_id"].nunique()),
        "audio_hours": round(float(valid["hours"].sum()), 1),
        "first_episode": str(valid["published"].min().date()),
        "last_episode": str(valid["published"].max().date()),
        "months_spanned": int(len(table)),
        "months_with_zero_episodes": empty_months,
        "collection_start": str(live_start.date()),
        "live_window_months": int(len(live)),
        "live_episodes": int(live["episodes"].sum()),
        "live_episodes_per_month_mean": round(float(live["episodes"].mean()), 1),
        "live_episodes_per_month_cv": round(
            float(live["episodes"].std() / live["episodes"].mean()), 3),
        "live_shows_per_month_mean": round(float(live["podcasts"].mean()), 1),
        "share_last_12_months_pct": round(100 * len(last12) / len(valid), 1),
        "median_month": str(table.index[(cum >= 0.5).argmax()]),
        "quartile_months": {
            str(q): str(table.index[(cum >= q / 100).argmax()]) for q in (25, 50, 75)
        },
        "archive_depth_years": {
            "median": round(float(spans["span_years"].median()), 2),
            "p25": round(float(spans["span_years"].quantile(0.25)), 2),
            "p75": round(float(spans["span_years"].quantile(0.75)), 2),
            "max": round(float(spans["span_years"].max()), 2),
        },
        "shows_reaching_back": {
            f"{y}y": int((spans["span_years"] >= y).sum()) for y in (1, 3, 5, 10)
        },
        "shows_active_in_final_month": int(
            (spans["last"] >= valid["published"].max() - pd.DateOffset(months=1)).sum()),
        "shows_stale_over_6_months": int(
            (spans["last"] < valid["published"].max() - pd.DateOffset(months=6)).sum()),
        "transcribed_total": int(valid["transcribed"].sum()),
        "transcribed_pct": round(100 * float(valid["transcribed"].mean()), 1),
        "transcribed_pct_by_year": {
            str(y): round(float(g["transcribed"].mean() * 100), 1)
            for y, g in valid.groupby(valid["published"].dt.year) if y >= 2015
        },
        "rss_transcripts": int(valid["has_rss_transcript"].sum()),
        "duplicate_title_rows": dupe_rows,
        "same_timestamp_distinct_title_rows": batch_rows,
        "shows_joining_after_2026_06": int((spans["first"] > pd.Timestamp("2026-06-01")).sum()),
    }


def write_findings(summary: dict, spans: pd.DataFrame, out: Path) -> None:
    depth = summary["archive_depth_years"]
    reach = summary["shows_reaching_back"]
    lines = [
        "# Temporal coverage of the podcast corpus",
        "",
        f"Generated from `downloader/data/podcast_metadata.db`. "
        f"{summary['episodes_total']:,} episodes across {summary['shows_total']} shows, "
        f"{summary['audio_hours']:,.0f} hours of audio.",
        "",
        "## Corpus window",
        "",
        f"- Publication dates run {summary['first_episode']} to {summary['last_episode']} "
        f"({summary['months_spanned']} months, {summary['months_with_zero_episodes']} of them empty).",
        f"- Collection began {summary['collection_start']}; everything earlier is back "
        f"catalogue pulled from RSS at that moment.",
        f"- The corpus is heavily recency-weighted: 25% of episodes were published after "
        f"{summary['quartile_months']['25']}, half after {summary['quartile_months']['50']}, "
        f"75% after {summary['quartile_months']['75']}. "
        f"{summary['share_last_12_months_pct']}% fall in the last 12 months alone.",
        "",
        "## Live collection is stable",
        "",
        f"- {summary['live_window_months']} months of live capture, "
        f"{summary['live_episodes']:,} episodes, mean "
        f"{summary['live_episodes_per_month_mean']:,.0f} per month "
        f"(coefficient of variation {summary['live_episodes_per_month_cv']}).",
        f"- Mean {summary['live_shows_per_month_mean']:.0f} distinct shows publish per month.",
        f"- {summary['shows_active_in_final_month']} shows are still current; "
        f"{summary['shows_stale_over_6_months']} have gone quiet for 6+ months.",
        "",
        "## Back catalogue is uneven",
        "",
        f"- Median archive depth {depth['median']:.1f} years "
        f"(IQR {depth['p25']:.1f}-{depth['p75']:.1f}, max {depth['max']:.1f}).",
        f"- Shows reaching back at least 1/3/5/10 years: "
        f"{reach['1y']}/{reach['3y']}/{reach['5y']}/{reach['10y']} of {summary['shows_total']}.",
        "- Depth is mostly a matter of show age, not feed retention: see "
        "`attribution_findings.md`, which finds that 97-98% of the shows absent from any "
        "past month had not launched yet, and only ~3% of shows have a demonstrably "
        "truncated feed. The back catalogue is a young panel, not a censored one.",
        "",
        "## Transcripts are not temporally biased",
        "",
        f"- {summary['transcribed_total']:,} of {summary['episodes_dated']:,} dated episodes "
        f"are transcribed ({summary['transcribed_pct']}%); "
        f"{summary['rss_transcripts']:,} came from publisher feeds.",
        "- Per-year transcribed share: "
        + ", ".join(f"{y} {v}%" for y, v in summary["transcribed_pct_by_year"].items()) + ".",
        "- The share is flat across eras, so time-sliced analyses are not confounded by "
        "differential transcription — except in the newest month, which is still in flight.",
        "",
        "## Data-quality notes",
        "",
        f"- {summary['episodes_undated']} episodes carry an epoch (1970) publication date "
        f"and are excluded from every series above.",
        f"- {summary['duplicate_title_rows']:,} rows share a show, timestamp *and* title: "
        f"genuine duplicate feed entries that got distinct GUIDs. Deduplicate before "
        f"counting episodes per period.",
        f"- A further {summary['same_timestamp_distinct_title_rows']:,} rows share a show "
        f"and timestamp but differ in title; those are ordinary batch drops, not duplicates.",
        f"- The panel is not fixed: {summary['shows_joining_after_2026_06']} shows first "
        f"appear after 2026-06-01 as they entered the charts, which is part of why weekly "
        f"volume steps up in July 2026. Trends in raw episode counts partly track panel "
        f"growth rather than publishing behaviour.",
        "",
        "## Deepest archives",
        "",
        "| Show | First | Last | Episodes | Years |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for _, r in spans.nlargest(8, "span_years").iterrows():
        lines.append(
            f"| {r['title']} | {r['first']:%Y-%m-%d} | {r['last']:%Y-%m-%d} | "
            f"{r['episodes']:,} | {r['span_years']:.1f} |"
        )
    (out / "findings.md").write_text("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    episodes, podcasts = load(args.db)
    valid = episodes[episodes["published"] >= EPOCH_CUTOFF].copy()
    table = monthly_table(valid)
    spans = per_podcast(valid)
    live_start = pd.Timestamp("2025-10-13")

    fig_volume(table, live_start, out)
    fig_panel(table, spans.shape[0], live_start, out)
    fig_backcatalog(spans, table, out)
    fig_spans(spans, out)
    fig_transcripts(table, live_start, out)
    fig_cadence(valid, live_start, out)
    fig_heatmap(valid, spans, live_start, out)

    summary = build_summary(episodes, valid, table, spans, live_start)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    table.drop(columns=["date"]).to_csv(out / "monthly_coverage.csv")
    spans.to_csv(out / "podcast_spans.csv", index=False)
    write_findings(summary, spans, out)

    # Compact series for downstream rendering (the HTML memo reads this).
    series = {
        "months": [str(m) for m in table.index],
        "episodes": table["episodes"].astype(int).tolist(),
        "podcasts": table["podcasts"].astype(int).tolist(),
        "transcribed": table["transcribed"].astype(int).tolist(),
        "hours": table["hours"].round(1).tolist(),
        "summary": summary,
    }
    (out / "series.json").write_text(json.dumps(series) + "\n")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
