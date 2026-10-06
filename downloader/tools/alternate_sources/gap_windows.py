"""Which empty study windows are probably *missing* episodes, not quiet months.

A show can chart in a month it published nothing (a finished limited series, a
hiatus), so an empty window is not by itself a hole in the data. This tool
labels each empty window of a study with what the catalog says around it:

* ``bracketed`` -- the podcast has episodes shortly before and shortly after
  the window, and published often enough around it that a month with none is
  unlikely (its median gap between episodes is well under the window);
* ``predates_catalog`` -- the window ends before the podcast's earliest known
  episode: the show charted before anything we hold, so its feed has rolled
  the episodes off;
* ``sparse`` -- neither: a quiet stretch (the show was between seasons, or
  publishes rarely). Not worth chasing.

Writes one JSON object per empty window (sorted by podcast), plus a per-podcast
summary to stdout, sorted by the number of probably-missing windows.

    ../.venv/bin/python tools/alternate_sources/gap_windows.py apple-top24-monthly OUT.jsonl
"""

from __future__ import annotations

import argparse
import statistics
import sys
from bisect import bisect_left
from collections import Counter
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from podcast_pipeline.studies.gaps import study_gaps  # noqa: E402
from tools.alternate_sources.common import open_db, write_jsonl  # noqa: E402

# An episode within this many days on each side counts as "shortly".
BRACKET_DAYS = 75
# Around the window, look at this many days of episodes to measure cadence.
CADENCE_SPAN_DAYS = 365
# The median gap must be at most this many days for an empty month to be odd.
MAX_MEDIAN_GAP_DAYS = 10


def _day(s: str) -> date:
    return datetime.fromisoformat(s[:10]).date()


def classify(dates: list[date], start: date, end: date) -> dict:
    """Label one empty window [start, end) from the podcast's sorted episode dates."""
    i = bisect_left(dates, start)
    prev = dates[i - 1] if i > 0 else None
    nxt = dates[i] if i < len(dates) else None    # first on/after start; the window is empty
    around = [d for d in dates if abs((d - start).days) <= CADENCE_SPAN_DAYS]
    gaps = [(b - a).days for a, b in zip(around, around[1:]) if (b - a).days > 0]
    median_gap = statistics.median(gaps) if gaps else None
    info = {"prev_episode": prev.isoformat() if prev else None,
            "next_episode": nxt.isoformat() if nxt else None,
            "median_gap_days": median_gap, "episodes_within_year": len(around)}
    if not dates or end <= dates[0]:
        label = "predates_catalog"
    elif (prev and nxt and (start - prev).days <= BRACKET_DAYS and (nxt - end).days <= BRACKET_DAYS
          and median_gap is not None and median_gap <= MAX_MEDIAN_GAP_DAYS):
        label = "bracketed"
    else:
        label = "sparse"
    return {"label": label, **info}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("study")
    ap.add_argument("out", type=Path)
    args = ap.parse_args()

    conn = open_db()
    out = []
    for g in study_gaps(conn, args.study):
        dates = sorted(_day(r[0]) for r in conn.execute(
            "SELECT published_date FROM episodes WHERE podcast_id = ? AND published_date >= '1995'",
            (g.podcast_id,)))
        feed = conn.execute("""SELECT url, oldest_item, item_count FROM podcast_feeds
                               WHERE podcast_id = ? ORDER BY oldest_item""", (g.podcast_id,)).fetchall()
        rss = conn.execute("SELECT rss_url FROM podcasts WHERE id = ?", (g.podcast_id,)).fetchone()[0]
        for label, start, end in g.windows:
            if label not in g.empty:
                continue
            out.append({"podcast_id": g.podcast_id, "title": g.title, "entity": g.entity,
                        "window": label, "start": start, "end": end, "rss_url": rss,
                        "earliest_known": g.earliest_known,
                        "feeds": [dict(f) for f in feed],
                        **classify(dates, _day(start), _day(end))})
    write_jsonl(args.out, out)
    labels = Counter(w["label"] for w in out)
    print(f"{len(out)} empty windows: {dict(labels)}")
    missing = Counter((w["podcast_id"], w["title"]) for w in out if w["label"] != "sparse")
    for (pid, title), n in missing.most_common(60):
        print(f"{n:3d}  {pid:6d}  {title}")


if __name__ == "__main__":
    main()
