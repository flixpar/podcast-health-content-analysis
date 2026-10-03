"""Read-only audit: does each study member's catalog podcast look like the show that charted?

For every resolved member of a study, compares the chart's names and publisher
(``study_members.attrs``) with the catalog podcast's title and publisher, notes
how the identity was decided (direct Apple id, iTunes lookup, iTunes search,
title link), and checks whether the podcast's earliest known episode predates
the member's first charting month. Writes one CSV row per member with a
``flags`` column; nothing is written to the database.

    ../.venv/bin/python tools/audit/study_identity.py apple-top24-monthly OUT.csv
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from difflib import SequenceMatcher
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "podcast_metadata.db"
STOP = {"the", "a", "an", "podcast", "show", "with", "and", "of", "inc", "llc", "media",
        "network", "studios", "productions", "podcasts", "radio", "news"}


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def tokens(s: str | None) -> set[str]:
    return {t for t in norm(s).split() if t not in STOP}


def similarity(a: str | None, b: str | None) -> float:
    """Max of character ratio and token containment, in [0, 1]."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    ratio = SequenceMatcher(None, na.replace(" ", ""), nb.replace(" ", "")).ratio()
    ta, tb = tokens(a), tokens(b)
    contain = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0
    return max(ratio, contain)


def main(study: str, out: str) -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    links = {r["entity"]: r for r in conn.execute("SELECT * FROM entity_links")}
    title_links_by_podcast: dict[int, list[sqlite3.Row]] = {}
    for r in links.values():
        if r["entity"].startswith("title:") and r["podcast_id"] is not None:
            title_links_by_podcast.setdefault(r["podcast_id"], []).append(r)
    rows = []
    for m in conn.execute("""
        SELECT m.entity, m.name, m.attrs, m.podcast_id, p.title AS p_title, p.publisher AS p_pub,
               p.apple_podcasts_id AS p_apple, p.rss_url
        FROM study_members m JOIN podcasts p ON p.id = m.podcast_id
        WHERE m.study = ?
    """, (study,)):
        attrs = json.loads(m["attrs"] or "{}")
        chart_titles = [m["name"], *attrs.get("titles", [])]
        title_sim = max(similarity(t, m["p_title"]) for t in chart_titles if t)
        pub_sim = similarity(attrs.get("publisher"), m["p_pub"]) if attrs.get("publisher") else None
        link = links.get(m["entity"])
        method = link["method"] if link else ("title_link" if m["podcast_id"] in title_links_by_podcast
                                              else "catalog_apple_id")
        first = conn.execute("""
            SELECT MIN(published_date) AS first, MAX(published_date) AS last, COUNT(*) AS n,
                   SUM(EXISTS(SELECT 1 FROM episode_sources s WHERE s.episode_id = e.id
                              AND s.source = 'wayback_feed')) AS n_wb
            FROM episodes e WHERE podcast_id = ? AND published_date >= '1990'
        """, (m["podcast_id"],)).fetchone()
        scope = conn.execute("""
            SELECT COUNT(*) AS n, MIN(e.published_date) AS first_in_scope
            FROM study_episodes s JOIN episodes e ON e.id = s.episode_id
            WHERE s.study = ? AND s.entity = ?
        """, (study, m["entity"])).fetchone()
        windows = conn.execute("SELECT COUNT(*) FROM study_windows WHERE study = ? AND entity = ?",
                               (study, m["entity"])).fetchone()[0]
        flags = []
        if title_sim < 0.6:
            flags.append("title_mismatch")
        if pub_sim is not None and pub_sim < 0.34:
            flags.append("publisher_mismatch")
        if method in ("itunes_search", "title_link"):
            flags.append(f"resolved_by_{method}")
        if link is not None and m["entity"].startswith("apple:") \
                and m["entity"][6:] != (m["p_apple"] or ""):
            flags.append("apple_id_differs")
        first_month = attrs.get("first_month")
        if first["first"] and first_month and first["first"][:7] > first_month:
            flags.append("first_episode_after_first_chart_month")
        if first["n"] == 0:
            flags.append("no_episodes")
        rows.append({
            "entity": m["entity"], "podcast_id": m["podcast_id"], "method": method,
            "chart_name": m["name"], "chart_titles": " | ".join(attrs.get("titles", [])),
            "chart_publisher": attrs.get("publisher"), "podcast_title": m["p_title"],
            "podcast_publisher": m["p_pub"], "podcast_apple_id": m["p_apple"],
            "title_sim": round(title_sim, 2), "pub_sim": None if pub_sim is None else round(pub_sim, 2),
            "first_chart_month": first_month, "last_chart_month": attrs.get("last_month"),
            "months": attrs.get("months"), "windows": windows,
            "catalog_first_episode": (first["first"] or "")[:10],
            "catalog_last_episode": (first["last"] or "")[:10], "catalog_episodes": first["n"],
            "catalog_wayback_episodes": first["n_wb"] or 0, "in_scope_episodes": scope["n"],
            "flags": ";".join(flags),
        })
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({"members": len(rows),
                      "flagged": sum(1 for r in rows if r["flags"]), "out": out}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
