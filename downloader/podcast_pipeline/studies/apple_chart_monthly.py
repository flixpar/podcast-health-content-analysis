"""Apple US overall chart, top N per calendar month, from January 2016.

The shared method behind the ``apple-top*-monthly`` studies. For every
calendar month since 2016-01, the N podcasts that held the top of Apple's US
overall chart that month; a study collects each show's episodes published in
the months it was in that list. A study fixes N (``depth``) and which chart
copies it reads (``sources``, best first); see ``apple_top24_monthly.py`` and
the classes at the end of this module.

Why this construction
---------------------
* **One depth throughout.** A study scores every month at the same depth so
  that 2016 and 2026 stay comparable. Apple's own page is 24 deep, so the
  deeper studies cannot use it: from 2024-09 they rely on My Podcast Data,
  and from 2024-08 to its start only Chartable's sparse copies reach them.
* **Exactly N per month, ranked by time-weighted points.** The archive's
  snapshot density varies from one snapshot a month (2019-2023, Chartable)
  to daily (2025-26). Taking every show seen in the top N would give ~N
  shows in a sparse month and about twice that in a dense one: a sampling
  artefact, not a popularity difference. Instead each snapshot stands for the
  calendar time closer to it than to its neighbours (the midpoint partition
  the population analysis validated), that time is clipped to each month,
  and a show earns ``days x (N + 1 - rank)`` for every snapshot in which it
  ranks <= N. The month's list is the N highest scorers (ties: best rank).
  Every month then contributes the same N slots, weighted by how high and how
  long a show charted.
* **Months without a snapshot are filled from their neighbours** (and marked
  ``provisional`` when those neighbours come from different sources). Such
  windows carry ``snapshots_in_month = 0`` and ``in_month_coverage = 0`` so an
  analysis can drop or down-weight them.
* **One chart, several copies.** Apple's chart page, the Marketing Tools feed
  (live capture), My Podcast Data (daily from 2024-09), Podbay (to 2019-08)
  and Chartable (2018-11 to 2024-12) carry the same chart; where two cover a
  day the source listed first wins. A snapshot is usable only if every rank
  1..N is present. The legacy iTunes RSS feed is excluded: the archive
  analysis found it disagrees with Podbay (median Jaccard 0.03 at depth 100),
  i.e. it is a different list. Chartable dates known to be wrong are already
  marked ``trusted = 0`` at import and are skipped.
* **Identity before scoring.** An entry's Apple id is used where its source
  carries one; otherwise its normalized title is mapped to the Apple id the
  same title carries elsewhere in the chart record, and then through
  ``entity_links`` (titles resolved by ``resolve``). Points are pooled per
  entity, so a show that changed title stays one show.

Months are included up to the last month the snapshot timeline fully covers,
so a study grows by itself as ``capture-charts`` adds days; refresh it.
"""

from __future__ import annotations

import bisect
import logging
import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import ClassVar

from podcast_pipeline.studies.base import Member, Study, Window

logger = logging.getLogger(__name__)

CHART = "apple:us:podcast:all"
START_MONTH = "2016-01"

MARKETING_TOOLS, APPLE_PAGE, MPD = "apple_marketing_tools", "apple_charts_page", "mypodcastdata"
PODBAY, CHARTABLE = "podbay", "chartable_itunes"


class AppleChartMonthly(Study):
    """Top ``depth`` of the Apple US overall chart per month; subclasses set
    ``name``, ``description``, ``version``, ``depth`` and ``sources``."""

    depth: ClassVar[int]
    sources: ClassVar[tuple[str, ...]]
    exclude_trailers = True

    def params(self) -> dict:
        return {"chart": CHART, "sources": list(self.sources), "depth": self.depth,
                "start_month": START_MONTH}

    def select(self, conn: sqlite3.Connection) -> list[Member]:
        days = snapshot_days(conn, self.sources, self.depth)
        if not days:
            raise ValueError(f"No usable {CHART} snapshots at depth {self.depth}; "
                             f"run import-chart-archive first")
        resolve = entity_resolver(conn)
        observations = _observations(conn, days, resolve, self.depth)
        months = monthly_lists(days, observations, self.depth)
        return _members(months, observations)


def snapshot_days(conn: sqlite3.Connection, sources: tuple[str, ...],
                  depth: int) -> list[tuple[str, int, str]]:
    """(date, snapshot id, source): one usable snapshot per day, best source first."""
    rows = conn.execute(f"""
        SELECT captured_on, id, source FROM chart_snapshots
        WHERE chart = ? AND trusted = 1 AND complete_to >= ?
          AND source IN ({",".join("?" * len(sources))})
    """, (CHART, depth, *sources)).fetchall()
    best: dict[str, tuple[str, int, str]] = {}
    for r in rows:
        current = best.get(r["captured_on"])
        if current is None or sources.index(r["source"]) < sources.index(current[2]):
            best[r["captured_on"]] = (r["captured_on"], r["id"], r["source"])
    return sorted(best.values())


def entity_resolver(conn: sqlite3.Connection):
    """(apple_id, title_key, day) -> entity string, following the rules above.

    A bare title takes the Apple id the same title carried on this chart
    *nearest in time*: some titles changed hands (The Ezra Klein Show moved
    from Vox to the New York Times under a new id), so the most common id
    overall can belong to the wrong era. Titles never seen with an id on this
    chart fall back to the most common id anywhere in the chart record.
    """
    on_chart: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for r in conn.execute("""
        SELECT DISTINCT e.title_key, s.captured_on, e.apple_id
        FROM chart_entries e JOIN chart_snapshots s ON s.id = e.snapshot_id
        WHERE s.chart = ? AND e.apple_id IS NOT NULL AND e.title_key IS NOT NULL
        ORDER BY e.title_key, s.captured_on, e.apple_id
    """, (CHART,)):
        on_chart[r["title_key"]].append((r["captured_on"], r["apple_id"]))
    key_counts: dict[str, Counter] = defaultdict(Counter)
    for r in conn.execute("""
        SELECT title_key, apple_id, COUNT(*) AS n FROM chart_entries
        WHERE apple_id IS NOT NULL AND title_key IS NOT NULL GROUP BY title_key, apple_id
    """):
        key_counts[r["title_key"]][r["apple_id"]] += r["n"]
    # most common id for the title; ties go to the smaller id, deterministically
    key_to_id = {k: min(c.items(), key=lambda kv: (-kv[1], kv[0]))[0] for k, c in key_counts.items()}
    links = {r["entity"]: (r["podcast_id"], r["apple_podcasts_id"]) for r in conn.execute("""
        SELECT l.entity, l.podcast_id, p.apple_podcasts_id
        FROM entity_links l JOIN podcasts p ON p.id = l.podcast_id
        WHERE l.entity LIKE 'title:%'
    """)}

    def nearest(seen: list[tuple[str, str]], day: str) -> str:
        i = bisect.bisect_left(seen, (day, ""))
        candidates = seen[max(0, i - 1):i + 1]
        gap = lambda c: abs((date.fromisoformat(c[0]) - date.fromisoformat(day)).days)
        return min(candidates, key=lambda c: (gap(c), c[0]))[1]

    def resolve(apple_id: str | None, title_key: str | None, day: str) -> str | None:
        if apple_id:
            return f"apple:{apple_id}"
        if not title_key:
            return None
        if title_key in on_chart:
            return f"apple:{nearest(on_chart[title_key], day)}"
        if title_key in key_to_id:
            return f"apple:{key_to_id[title_key]}"
        linked = links.get(f"title:{title_key}")
        if linked:
            podcast_id, linked_apple = linked
            return f"apple:{linked_apple}" if linked_apple else f"podcast:{podcast_id}"
        return f"title:{title_key}"

    return resolve


def _observations(conn, days, resolve, depth: int) -> dict[str, dict[str, dict]]:
    """{date: {entity: {rank, name, publisher}}}, best rank if an entity repeats."""
    by_snapshot = {snap: day for day, snap, _ in days}
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    unidentifiable = []
    ids = list(by_snapshot)
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        for r in conn.execute(f"""
            SELECT snapshot_id, rank, name, publisher, title_key, apple_id FROM chart_entries
            WHERE snapshot_id IN ({",".join("?" * len(chunk))}) AND rank <= ?
        """, (*chunk, depth)):
            day = by_snapshot[r["snapshot_id"]]
            entity = resolve(r["apple_id"], r["title_key"], day)
            if entity is None:
                unidentifiable.append((day, r["rank"], r["name"]))
                continue
            seen = out[day].get(entity)
            if seen is None or r["rank"] < seen["rank"]:
                out[day][entity] = {"rank": r["rank"], "name": r["name"], "publisher": r["publisher"]}
    if unidentifiable:
        # No id and a title with no [a-z0-9] at all: nothing to key it on.
        logger.warning(f"{len(unidentifiable)} top-{depth} entries have neither an Apple id nor a "
                       f"usable title and are left out: {unidentifiable[:10]}")
    return out


def _cells(dates: list[date]) -> list[tuple[float, float]]:
    """[lo, hi) per snapshot, in hours from midnight of the first snapshot day:
    the time closer to it than to either neighbour.

    A capture's time of day is not used (it is not the chart's publication
    time either), so each snapshot sits at midday of its date; the first and
    last snapshots extend half a day outward, covering their own day.
    """
    t = [(d - dates[0]).days * 24.0 + 12.0 for d in dates]
    mids = [(a + b) / 2 for a, b in zip(t, t[1:])]
    return list(zip([t[0] - 12.0] + mids, mids + [t[-1] + 12.0]))


def monthly_lists(days, observations, depth: int) -> dict[str, list[dict]]:
    """{'YYYY-MM': ranked top-``depth`` list} with per-entry scoring evidence."""
    dates = [date.fromisoformat(d) for d, _, _ in days]
    sources = {d: s for d, _, s in days}
    origin = dates[0]
    cells = _cells(dates)
    timeline_end = cells[-1][1]

    months = []
    m = date.fromisoformat(START_MONTH + "-01")
    while True:
        nxt = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
        if (nxt - origin).days * 24 > timeline_end:
            break
        months.append((m, nxt))
        m = nxt

    lists = {}
    for m_start, m_end in months:
        a, b = (m_start - origin).days * 24, (m_end - origin).days * 24
        points: dict[str, float] = defaultdict(float)
        best: dict[str, int] = {}
        snaps_in_month = 0
        in_month_hours = 0.0
        contributing = set()
        for (lo, hi), d in zip(cells, dates):
            overlap = min(hi, b) - max(lo, a)
            if overlap <= 0:
                continue
            key = d.isoformat()
            contributing.add(sources[key])
            if m_start <= d < m_end:
                snaps_in_month += 1
                in_month_hours += overlap
            for entity, obs in observations.get(key, {}).items():
                points[entity] += overlap / 24 * (depth + 1 - obs["rank"])
                best[entity] = min(best.get(entity, depth + 1), obs["rank"])
        ranked = sorted(points, key=lambda e: (-points[e], best[e], e))[:depth]
        days_in_month = (m_end - m_start).days
        lists[m_start.strftime("%Y-%m")] = [{
            "entity": e,
            "monthly_rank": i + 1,
            "points": round(points[e], 2),
            "mean_points": round(points[e] / days_in_month, 3),
            "best_rank": best[e],
            "snapshots_in_month": snaps_in_month,
            "in_month_coverage": round(in_month_hours / (b - a), 3),
            "sources": sorted(contributing),
            # No snapshot inside the month, and the snapshots either side come
            # from different sources: the list rests on an untested assumption
            # that the two sources are the same chart (2026-09: Apple's page on
            # Aug 31, the Marketing Tools feed from Oct 2).
            "provisional": snaps_in_month == 0 and len(contributing) > 1,
            "start": m_start.isoformat(), "end": m_end.isoformat(),
        } for i, e in enumerate(ranked)]
    return lists


def _members(months: dict[str, list[dict]], observations) -> list[Member]:
    names: dict[str, Counter] = defaultdict(Counter)
    publishers: dict[str, Counter] = defaultdict(Counter)
    for day in observations.values():
        for entity, obs in day.items():
            if obs["name"]:
                names[entity][obs["name"]] += 1
            if obs["publisher"]:
                publishers[entity][obs["publisher"]] += 1

    windows: dict[str, list[Window]] = defaultdict(list)
    for label, ranked in months.items():
        for entry in ranked:
            attrs = {k: v for k, v in entry.items() if k not in ("entity", "start", "end")}
            windows[entry["entity"]].append(Window(label, entry["start"], entry["end"], attrs))

    members = []
    for entity, ws in sorted(windows.items()):
        publisher = publishers[entity].most_common(1)[0][0] if publishers[entity] else None
        members.append(Member(
            entity=entity,
            name=names[entity].most_common(1)[0][0] if names[entity] else entity,
            windows=ws,
            attrs={
                "publisher": publisher,
                "titles": [n for n, _ in names[entity].most_common(5)],
                "months": len(ws),
                "first_month": ws[0].label,
                "last_month": ws[-1].label,
                "best_monthly_rank": min(w.attrs["monthly_rank"] for w in ws),
            },
        ))
    return members


class AppleTop24MonthlyMPD(AppleChartMonthly):
    """``apple-top24-monthly`` with My Podcast Data filling days from 2024-09."""
    name = "apple-top24-monthly-mpd"
    description = ("Apple US overall chart, top 24 per calendar month since 2016-01 "
                   "(time-weighted points), with My Podcast Data from 2024-09; each show's "
                   "episodes from its charting months.")
    version = 1
    depth = 24
    sources = (MARKETING_TOOLS, APPLE_PAGE, MPD, PODBAY, CHARTABLE)


class AppleTop50Monthly(AppleChartMonthly):
    name = "apple-top50-monthly"
    description = ("Apple US overall chart, top 50 per calendar month since 2016-01 "
                   "(time-weighted points); each show's episodes from its charting months.")
    version = 1
    depth = 50
    sources = (MARKETING_TOOLS, MPD, PODBAY, CHARTABLE)     # Apple's page is 24 deep


class AppleTop100Monthly(AppleChartMonthly):
    name = "apple-top100-monthly"
    description = ("Apple US overall chart, top 100 per calendar month since 2016-01 "
                   "(time-weighted points); each show's episodes from its charting months.")
    version = 1
    depth = 100
    sources = (MARKETING_TOOLS, MPD, PODBAY, CHARTABLE)
