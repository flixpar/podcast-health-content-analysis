"""``import-chart-archive``: load the reconstructed chart archive into the DB.

Input is the output of ``analysis/chart_archive/parse.py``:
``<archive_dir>/parsed/chart_rows.parquet`` (Wayback) and
``chart_rows_cc.parquet`` (Common Crawl), one row per (capture, rank).

Each (source, chart id, UTC capture date) becomes one ``chart_snapshots`` row:
Chartable paginates and some charts were captured several times a day, so
captures from the same day are merged, and where two captures give the same
rank the earliest capture's row is kept.

The import is idempotent and all-or-nothing: one transaction deletes every
non-live snapshot (and its entries) and inserts the archive again. Live
captures (``origin = 'live'``) are never touched; an archive snapshot that
would collide with a live one for the same source/chart/day is skipped.
Snapshot ids are therefore not stable across re-imports.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections import Counter
from pathlib import Path

from podcast_pipeline.charts import keys
from podcast_pipeline.config import Config

logger = logging.getLogger(__name__)

FLAGSHIP = "apple:us:podcast:all"

# Chartable captures of the flagship that disagree with Apple's own chart on
# the day (analysis/chart_archive/population.py DISTRUSTED): its last days
# before shutdown, and one stale October page.
DISTRUSTED = {
    ("chartable_itunes", FLAGSHIP, "2024-10-07"):
        "stale page: disagrees with Apple's own chart that day (population.py DISTRUSTED)",
    **{("chartable_itunes", FLAGSHIP, d):
       "Chartable's last days before shutdown: disagrees with Apple's own chart "
       "(population.py DISTRUSTED)"
       for d in ("2024-12-06", "2024-12-07", "2024-12-08", "2024-12-09")},
}

# population.trusted_days(): the 100-deep mirrors must have >=95 of ranks
# 1-100 (analyze.py's full_top100); Apple's page is 24 deep by design.
FULL_TOP100_MIN = 95
DEEP_CUT, SHALLOW_CUT = 50, 24
FLAGSHIP_SERIES = {"podbay": DEEP_CUT, "chartable_itunes": DEEP_CUT,
                   "apple_charts_page": SHALLOW_CUT}
# What the research reported (data/chart-archive/parsed/population/summary.json).
RESEARCH_TRUSTED_DAYS = {"total": 941, "podbay": 361, "chartable_itunes": 121,
                         "apple_charts_page": 459}

ORIGINS = {"wayback": "wayback", "commoncrawl": "common_crawl"}
APPLE_ID_SOURCES = {"podbay", "apple_charts_page", "itunes_rss"}

COLUMNS = ["source", "platform", "unit", "chart", "region", "genre", "rank", "name",
           "publisher", "entity_id", "entity_url", "captured_at", "path", "archive"]


def load_rows(archive_dir: Path):
    """Both parsed parquet files, in file order (the order breaks exact ties)."""
    import pandas as pd

    parsed = archive_dir / "parsed"
    main = parsed / "chart_rows.parquet"
    if not main.exists():
        raise FileNotFoundError(f"{main} not found; run analysis/chart_archive/parse.py "
                                f"or pass --archive-dir")
    files = [main]
    cc = parsed / "chart_rows_cc.parquet"
    if cc.exists():
        files.append(cc)
    else:
        logger.warning(f"{cc} not found; importing Wayback captures only")
    frames = [pd.read_parquet(f, columns=COLUMNS) for f in files]
    df = pd.concat(frames, ignore_index=True)
    logger.info(f"Read {len(df):,} rows from {', '.join(f.name for f in files)}")
    return df


def map_charts(df):
    """Attach ``snap_source`` / ``chart_id``; returns (mapped rows, skipped counts)."""
    import pandas as pd

    facets = ["source", "unit", "chart", "region", "genre"]
    combos = df[facets].fillna("").drop_duplicates()
    out, skipped = [], Counter()
    for source, unit, chart, region, genre in combos.itertuples(index=False, name=None):
        try:
            snap_source, cid = keys.archive_chart(source, unit, chart, region or None, genre)
            reason = None
        except keys.Unmapped as e:
            snap_source, cid, reason = None, None, f"{source}: {e}"
        out.append((source, unit, chart, region, genre, snap_source, cid, reason))
    table = pd.DataFrame(out, columns=facets + ["snap_source", "chart_id", "reason"])
    df = df.assign(**{f: df[f].fillna("") for f in facets}).merge(
        table, on=facets, how="left", sort=False, validate="many_to_one")
    if df["snap_source"].isna().sum() != df["reason"].notna().sum():
        raise AssertionError("chart mapping lost rows: a facet failed to join")
    bad = df["chart_id"].isna()
    for reason, n in df.loc[bad, "reason"].value_counts().items():
        skipped[reason] += int(n)
    return df.loc[~bad].drop(columns=["reason"]), skipped


def build(df):
    """(snapshots frame, entries frame) from mapped rows."""
    import pandas as pd

    df = df.copy()
    df["captured_on"] = df["captured_at"].str[:10]
    if not df["captured_at"].str.endswith("+00:00").all():
        # parse.py writes UTC; anything else would put captures on the wrong day
        stamps = pd.to_datetime(df["captured_at"], utc=True, format="ISO8601")
        df["captured_on"] = stamps.dt.strftime("%Y-%m-%d")
        df["captured_at"] = stamps.dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    df["order"] = range(len(df))
    key = ["snap_source", "chart_id", "captured_on"]
    df = df.sort_values(key + ["captured_at", "path", "order"], kind="stable")
    # one row per rank per day: the earliest capture wins
    df = df.drop_duplicates(key + ["rank"], keep="first")

    first = df.drop_duplicates(key, keep="first").set_index(key)
    by_rank = df.sort_values(key + ["rank"], kind="stable")
    position = by_rank.groupby(key, sort=False).cumcount() + 1
    complete = (by_rank["rank"] == position).groupby([by_rank[k] for k in key]).sum()
    g = df.groupby(key)
    snaps = pd.DataFrame({
        "captured_at": g["captured_at"].min(),
        "depth": g["rank"].max(),
        "n_entries": g["rank"].size(),
        "complete_to": complete,
        "origin": first["archive"].map(ORIGINS),
        "raw_path": first["path"],
    }).reset_index()
    if snaps["origin"].isna().any():
        raise ValueError(f"unknown archive values: {set(first['archive']) - set(ORIGINS)}")
    return snaps, df


def run(config: Config, conn: sqlite3.Connection, archive_dir: Path | None = None) -> dict:
    t0 = time.monotonic()
    archive_dir = Path(archive_dir) if archive_dir else config.chart_archive_path
    raw = load_rows(archive_dir)
    mapped, skipped = map_charts(raw)
    snaps, entries = build(mapped)

    live = {tuple(r) for r in conn.execute(
        "SELECT source, chart, captured_on FROM chart_snapshots WHERE origin = 'live'")}
    if live:
        clash = snaps.apply(lambda r: (r["snap_source"], r["chart_id"], r["captured_on"]) in live,
                            axis=1)
        if clash.any():
            skipped["live capture exists for that source/chart/day"] += int(
                snaps.loc[clash, "n_entries"].sum())
            snaps = snaps.loc[~clash]
    logger.info(f"{len(snaps):,} snapshots, {int(snaps['n_entries'].sum()):,} entries to insert")

    with conn:
        removed = _delete_archive(conn)
        snapshot_ids = _insert_snapshots(conn, snaps)
        n_entries = _insert_entries(conn, entries, snapshot_ids)
    elapsed = time.monotonic() - t0
    logger.info(f"Imported {len(snapshot_ids):,} snapshots / {n_entries:,} entries "
                f"in {elapsed:.0f}s")

    verification = verify_flagship(conn)
    if not verification["matches_research"]:
        logger.warning(f"Flagship trusted days differ from the research: {verification}")
    return {
        "archive_dir": str(archive_dir),
        "rows_read": int(len(raw)),
        "rows_skipped": int(sum(skipped.values())),
        "skipped": dict(skipped.most_common()),
        "rows_merged_away": int(len(mapped) - len(entries)),
        "replaced": removed,
        "snapshots": len(snapshot_ids),
        "entries": n_entries,
        "by_source": _by_source(snaps),
        "top_charts": _top_charts(snaps),
        "flagship_verification": verification,
        "elapsed_seconds": round(elapsed, 1),
    }


def _delete_archive(conn: sqlite3.Connection) -> dict:
    n_entries = conn.execute("""
        DELETE FROM chart_entries WHERE snapshot_id IN
            (SELECT id FROM chart_snapshots WHERE origin != 'live')
    """).rowcount
    n_snaps = conn.execute("DELETE FROM chart_snapshots WHERE origin != 'live'").rowcount
    return {"snapshots": n_snaps, "entries": n_entries}


def _insert_snapshots(conn: sqlite3.Connection, snaps) -> dict:
    """Insert with explicit ids (past both AUTOINCREMENT's high-water mark and
    any live row), so entries can be written without reading ids back."""
    seq = conn.execute("SELECT seq FROM sqlite_sequence WHERE name = 'chart_snapshots'").fetchone()
    top = conn.execute("SELECT MAX(id) FROM chart_snapshots").fetchone()[0]
    next_id = max(seq[0] if seq else 0, top or 0) + 1
    ids, rows = {}, []
    for r in snaps.itertuples(index=False):
        key = (r.snap_source, r.chart_id, r.captured_on)
        note = DISTRUSTED.get(key)
        ids[key] = next_id
        rows.append((next_id, r.snap_source, r.chart_id, r.captured_on, r.captured_at,
                     r.origin, int(r.depth), int(r.n_entries), int(r.complete_to),
                     0 if note else 1, r.raw_path, note))
        next_id += 1
    conn.executemany("""
        INSERT INTO chart_snapshots (id, source, chart, captured_on, captured_at, origin,
                                     depth, n_entries, complete_to, trusted, raw_path, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    # population.py lists 2024-12-07 and 2024-12-09 defensively; the archive
    # holds no flagship capture on either day.
    missing = set(DISTRUSTED) - set(ids)
    if missing:
        logger.info(f"Distrusted days with no snapshot: {sorted(k[2] for k in missing)}")
    return ids


def _insert_entries(conn: sqlite3.Connection, df, snapshot_ids: dict) -> int:
    import pandas as pd

    sid = pd.Series([snapshot_ids.get(k) for k in
                     zip(df["snap_source"], df["chart_id"], df["captured_on"])],
                    index=df.index, dtype="object")
    df = df.assign(snapshot_id=sid).loc[sid.notna()]    # rows of skipped (live-clash) snapshots
    entity = df["entity_id"].astype("string")
    is_apple = (df["source"].isin(APPLE_ID_SOURCES) & df["unit"].eq("podcast")
                & entity.str.fullmatch(r"[0-9]+").fillna(False).astype(bool))
    apple_id = entity.where(is_apple)
    other = entity.where(~is_apple)
    spotify = df["platform"].eq("spotify") & other.str.startswith("spotify:").fillna(False)
    other = other.where(~spotify, other.str.rsplit(":", n=1).str[-1])
    frame = pd.DataFrame({
        "snapshot_id": df["snapshot_id"].astype(int),
        "rank": df["rank"].astype(int),
        "name": df["name"],
        "publisher": df["publisher"],
        "title_key": df["name"].map(keys.title_key),
        "apple_id": apple_id,
        "source_entity_id": other,
        "entity_url": df["entity_url"],
    }).astype(object)
    frame = frame.where(frame.notna(), None)
    rows = list(frame.itertuples(index=False, name=None))
    conn.executemany("""
        INSERT INTO chart_entries (snapshot_id, rank, name, publisher, title_key, apple_id,
                                   source_entity_id, entity_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    return len(rows)


def _by_source(snaps) -> dict:
    g = snaps.groupby("snap_source").agg(snapshots=("n_entries", "size"),
                                         entries=("n_entries", "sum"),
                                         charts=("chart_id", "nunique"))
    return {s: {k: int(v) for k, v in row.items()} for s, row in g.iterrows()}


def _top_charts(snaps, n: int = 15) -> list[dict]:
    g = (snaps.groupby(["snap_source", "chart_id"])
         .agg(snapshots=("n_entries", "size"), entries=("n_entries", "sum"),
              first=("captured_on", "min"), last=("captured_on", "max"))
         .sort_values("entries", ascending=False).head(n).reset_index())
    return [{"source": r.snap_source, "chart": r.chart_id, "snapshots": int(r.snapshots),
             "entries": int(r.entries), "first": r.first, "last": r.last}
            for r in g.itertuples(index=False)]


# --- verification against the archive research --------------------------------

def trusted_flagship_days(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """``[(captured_on, source)]``: the usable days of ``apple:us:podcast:all``,
    by the rules of ``population.trusted_days()``.

    Podbay and Chartable must be complete to 100 (>=95 of ranks 1-100 present);
    Apple's page must reach rank 24; distrusted snapshots are excluded. A day
    covered by several series is counted once, deepest series first.
    """
    rows = conn.execute(f"""
        SELECT s.captured_on, s.source, s.depth,
               (SELECT COUNT(*) FROM chart_entries e
                 WHERE e.snapshot_id = s.id AND e.rank <= 100) AS top100
        FROM chart_snapshots s
        WHERE s.chart = ? AND s.trusted = 1
          AND s.source IN ({",".join("?" * len(FLAGSHIP_SERIES))})
    """, (FLAGSHIP, *FLAGSHIP_SERIES)).fetchall()
    best: dict[str, tuple[int, str]] = {}
    order = list(FLAGSHIP_SERIES)
    for day, source, depth, top100 in rows:
        cut = FLAGSHIP_SERIES[source]
        usable = top100 >= FULL_TOP100_MIN if cut == DEEP_CUT else depth >= SHALLOW_CUT
        if not usable:
            continue
        rank = (-cut, order.index(source))
        if day not in best or rank < best[day][0]:
            best[day] = (rank, source)
    return sorted((day, source) for day, (_, source) in best.items())


def verify_flagship(conn: sqlite3.Connection) -> dict:
    days = trusted_flagship_days(conn)
    counts = Counter(source for _, source in days)
    got = {"total": len(days), **{s: counts.get(s, 0) for s in FLAGSHIP_SERIES}}
    return {"trusted_days": got, "research": RESEARCH_TRUSTED_DAYS,
            "matches_research": got == RESEARCH_TRUSTED_DAYS}
