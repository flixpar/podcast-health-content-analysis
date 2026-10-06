"""Canonical parsed inputs and coherent daily chart snapshots."""

from pathlib import Path

import pandas as pd

CANONICAL_FILES = ("chart_rows.parquet", "chart_rows_cc.parquet")
PAGE_TOLERANCE = pd.Timedelta(hours=1)


def load_canonical(directory: Path) -> pd.DataFrame:
    """Targeted parse shards are diagnostics, not additional observations."""
    paths = [directory / name for name in CANONICAL_FILES
             if (directory / name).exists()]
    return pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)


def select_daily(df: pd.DataFrame, keys: list[str] | None = None) -> pd.DataFrame:
    """Prefer deepest then earliest capture, aligning Chartable pages within 1h.

    Pages must come from the same archive and UTC day. Each page contributes
    at most one capture; overlapping ranks keep the lower-numbered page's row.
    A page-2-only capture remains partial and cannot complete another day's
    chart. Selection precedes any population depth cut.
    """
    if df.empty:
        return df.copy()
    work = df.reset_index(drop=True).copy()
    work["captured_at"] = pd.to_datetime(work["captured_at"], utc=True)
    work["_day"] = work["captured_at"].dt.date
    work["_archive"] = work.get("archive", pd.Series("wayback", index=work.index)).fillna("wayback")
    work["_page"] = work.get("page", pd.Series(1, index=work.index)).fillna(1).astype(int)
    if keys is None:
        keys = [c for c in ("source", "region", "chart", "genre", "unit") if c in work]
    selected = []
    for _, day in work.groupby(keys + ["_day"], dropna=False, sort=False):
        captures = (day.groupby(["_archive", "path", "_page"], dropna=False)
                    .agg(at=("captured_at", "min"))
                    .reset_index().sort_values(["at", "_archive", "path"]))
        anchors = captures[captures._page == captures._page.min()]
        best, best_score = None, None
        for anchor in anchors.to_dict("records"):
            paths = [anchor["path"]]
            if str(day["source"].iloc[0]).startswith("chartable"):
                nearby = captures[(captures._archive == anchor["_archive"])
                                  & (captures._page != anchor["_page"])].copy()
                nearby["gap"] = (nearby["at"] - anchor["at"]).abs()
                nearby = nearby[nearby.gap <= PAGE_TOLERANCE]
                nearby = nearby.sort_values(["gap", "at", "path"]).drop_duplicates("_page")
                paths.extend(nearby["path"].tolist())
            candidate = day[(day._archive == anchor["_archive"]) & day.path.isin(paths)]
            candidate = candidate.sort_values(["_page", "rank"]).drop_duplicates("rank")
            ranks = candidate["rank"]
            # Top-100 completeness outranks extra lower-page rows. Stable
            # iteration breaks ties toward the earliest capture and path.
            quality = (int(ranks.between(1, 100).sum()), len(candidate))
            if best_score is None or quality > best_score:
                best, best_score = candidate, quality
        selected.append(best)
    return (pd.concat(selected).drop(columns=["_day", "_archive", "_page"])
            .reset_index(drop=True))
