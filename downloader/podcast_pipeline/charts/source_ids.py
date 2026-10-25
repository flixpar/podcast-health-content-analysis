"""``import-chart-ids``: Apple ids for chart rows that carry only a source's own id.

Chartable's copies of the Apple chart (``chartable_itunes``, 2018-11 to
2024-12) name each show by title and Chartable slug, with no Apple id. A study
then has to guess the id from the title: the id the same title carried
nearest in time elsewhere on the chart (``studies.apple_chart_monthly``). The
guess fails when two shows share a title (two "Betrayal"s, 2022 and 2024),
or when a title never appears with an id.

Chartable's own show page (``chartable.com/podcasts/<slug>``) links the
show's Apple listing ("Listen on Apple Podcasts", ``.../id<N>``) and its feed.
Archived copies of those pages are read by ``tools/chartable_apple_ids.py``,
which writes one JSON line per slug:

    {"slug": "bag-man", "apple_ids": ["1438463967"],
     "feeds": ["https://podcastfeeds.nbcnews.com/y8D0o0f3"],
     "ts": "201811", "page_title": "Bag Man", ...}

This command loads such a file into ``chart_source_ids``. A slug whose page
named exactly one Apple id is imported. A page with none (removed listing,
unarchived page) or several is skipped and counted. The import replaces the
source's rows, in one transaction.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def run(conn: sqlite3.Connection, path: Path, source: str) -> dict:
    rows, skipped = [], {"no_apple_id": 0, "several_apple_ids": 0}
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            ids = r.get("apple_ids") or []
            if len(ids) != 1:
                skipped["no_apple_id" if not ids else "several_apple_ids"] += 1
                continue
            feeds = r.get("feeds") or []
            evidence = {k: r.get(k) for k in ("page_url", "ts", "capture", "page_title", "name")
                        if r.get(k)}
            rows.append((source, r["slug"], ids[0], feeds[0] if len(feeds) == 1 else None,
                         json.dumps(evidence)))
    if len({(s, slug) for s, slug, *_ in rows}) != len(rows):
        raise ValueError(f"{path}: a slug appears more than once")
    with conn:
        replaced = conn.execute("DELETE FROM chart_source_ids WHERE source = ?", (source,)).rowcount
        conn.executemany("""
            INSERT INTO chart_source_ids (source, source_entity_id, apple_id, feed_url, evidence)
            VALUES (?, ?, ?, ?, ?)
        """, rows)
    result = {"source": source, "imported": len(rows), "replaced": replaced, "skipped": skipped}
    logger.info(f"import-chart-ids: {result}")
    return result
