"""Read-only audit of a study's in-scope episodes: duplicates, dates, content type, windows.

Writes, into OUT_DIR:

* ``flagged_episodes.csv``: one row per (episode, issue) with the evidence;
* ``windows.csv``: every window with its evidence and what fills it;
* ``summary.json``: counts per issue.

Issues
------
``dup_title_same_window`` / ``dup_title_other_window``
    Two in-scope episodes of one podcast whose titles agree after stripping
    rerun markers ("Rebroadcast", "Encore", "Best of", "(Replay)", ...),
    episode numbers and punctuation ("Part N" is kept), *and* the later one
    carries a rerun marker or the same duration (within 1% or 5 s). The
    *later* copy is flagged.
``rerun_of_earlier``
    Same podcast, an episode published more than a week earlier (in scope or
    not) with the same duration (within 1% or 5 s, > 10 min) and one title
    (>= 12 normalized characters) containing the other: a re-post such as
    "SYSK Selects: ..." or a yearly re-release. Identical normalized titles
    (recurring guests, "Mailbag Sunday") also need the duration within 2 s or
    a rerun marker on the later one, and the titles' numbers (years aside)
    must agree ("MFM Minisode 221" is not "MFM Minisode 22").
``rerun_old_number``
    The title leads with an episode number more than ``OLD_NUMBER_GAP`` below
    the highest number the feed had reached by that date: a re-post of an
    old episode (This American Life's weekly reruns), when no copy of the
    original is in the catalog to match against.
``dup_other_podcast``
    The same normalized title within one day and with the same duration in
    scope under a second podcast: one show held as two catalog podcasts.
``repost_of_other_podcast`` / ``reposted_elsewhere``
    The same recording (duration within 1 s, > 10 min, titles nearly equal or
    one containing the other; see ``same_recording``) is also an episode of another catalog podcast: a
    series re-posted into a host feed (Dateline re-running a limited series, a
    network show swapping episodes). Its date is the re-post's, not the
    content's, and if both podcasts are in scope it is counted twice.
``feed_drop``
    "Introducing ...", "Presenting ...", "Feed drop", "What to listen to
    next ..." where the rest of the title is not the show's own name:
    another show's trailer or episode carried in this feed.
``wayback_dup_of_feed``
    A ``wayback_feed``-only episode within one day of a live-feed episode of
    the same podcast with a similar title (>= 0.85, numbers kept) and the same
    duration (within 2%; >= 0.95 title similarity when either is unknown):
    one recording, two GUIDs.
``bulk_day``
    Published on a day when the podcast has more than ``BULK_DAY`` episodes
    (a feed re-published in bulk carries the re-publication date, not the
    content's).
``future_date``
    Published after today.
``trailer`` / ``bonus`` / ``short_lt180``
    ``episode_type`` from the feed, or a declared duration under 3 minutes.
``zero_or_missing_duration``
    Declared duration missing or 0 (often wayback items).

Nothing is written to the database.

    ../.venv/bin/python tools/audit/study_episodes.py apple-top24-monthly OUT_DIR
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from podcast_pipeline.studies.quality import (  # noqa: E402  (shared rules)
    FEED_DROP, LEADING_NUMBER, RERUN_MARKER, norm_title, title_numbers)

DB = Path(__file__).resolve().parents[2] / "data" / "podcast_metadata.db"
BULK_DAY = 20
REPOST_MIN_SECONDS = 600
OLD_NUMBER_GAP = 15
SHORT_SECONDS = 180
TODAY = date.today().isoformat()
RERUN = RERUN_MARKER
numbers = title_numbers


def is_copy(a: dict, b: dict) -> str | None:
    """Why ``b`` (the later of two same-title episodes) is a copy of ``a``, or None.

    A shared normalized title alone is not enough: a show with recurring guests
    ("#793 - Whitney Cummings", "#1067 - Whitney Cummings") reuses titles for
    new recordings. A copy also carries a rerun marker or the same duration.
    """
    if RERUN.search(b["title"] or "") and not RERUN.search(a["title"] or ""):
        return "rerun marker"
    if numbers(a["title"]) != numbers(b["title"]):
        return None
    da, db_ = a["duration_seconds"] or 0, b["duration_seconds"] or 0
    if da and db_ and abs(da - db_) <= max(5, 0.01 * max(da, db_)):
        return f"same duration ({db_} vs {da} s)"
    return None


def same_recording(e: dict, r: dict) -> bool:
    """Is catalog episode ``r`` (duration within 1 s of ``e``) the same recording as ``e``?

    Nearly equal titles, or one containing the other: a long contained title
    is enough; a short one ("Homecoming", "Family Tree") also needs an exact
    duration or dates within a week, because short generic titles recur.
    """
    a, b = e["norm"], r["norm"]
    if len(a) < 8 or len(b) < 8:
        return False
    if abs(len(a) - len(b)) <= 0.1 * max(len(a), len(b)) and SequenceMatcher(None, a, b).ratio() >= 0.9:
        return True
    if not (a in b or b in a):
        return False
    if min(len(a), len(b)) >= 12:
        return True
    days = abs((date.fromisoformat((e["published_date"] or "1900-01-01")[:10])
                - date.fromisoformat((r["published_date"] or "1900-01-01")[:10])).days)
    return e["duration_seconds"] == r["duration_seconds"] or days <= 7


def sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def main(study: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    eps = [dict(r) for r in conn.execute("""
        SELECT e.id, e.podcast_id, s.entity, s.window_label, e.title, e.published_date,
               e.duration_seconds, e.status, e.audio_file_path IS NOT NULL AS has_audio,
               json_extract(e.metadata, '$.episode_type') AS episode_type,
               (SELECT group_concat(x.source) FROM episode_sources x WHERE x.episode_id = e.id) AS sources
        FROM study_episodes s JOIN episodes e ON e.id = s.episode_id
        WHERE s.study = ?
    """, (study,))]
    in_scope = {e["id"] for e in eps}
    flags: list[dict] = []

    def flag(e: dict, issue: str, detail: str = "", other: int | None = None) -> None:
        flags.append({"episode_id": e["id"], "podcast_id": e["podcast_id"], "entity": e["entity"],
                      "window_label": e["window_label"], "published_date": (e["published_date"] or "")[:10],
                      "title": e["title"], "duration_seconds": e["duration_seconds"], "status": e["status"],
                      "sources": e["sources"], "issue": issue, "other_episode_id": other, "detail": detail})

    # -- 2. duplicates within scope
    by_podcast: dict[int, list[dict]] = defaultdict(list)
    for e in eps:
        e["norm"] = norm_title(e["title"])
        by_podcast[e["podcast_id"]].append(e)
    for podcast_eps in by_podcast.values():
        podcast_eps.sort(key=lambda e: (e["published_date"] or "", e["id"]))
        first_by_norm: dict[str, dict] = {}
        for e in podcast_eps:
            o = first_by_norm.get(e["norm"]) if len(e["norm"]) >= 6 else None
            why = is_copy(o, e) if o else None
            if why:
                same = o["window_label"] == e["window_label"]
                flag(e, "dup_title_same_window" if same else "dup_title_other_window",
                     f"{why}; copy of {o['id']} ({(o['published_date'] or '')[:10]}: {o['title']})", o["id"])
            else:
                first_by_norm.setdefault(e["norm"], e)

    # -- 2a'. the same episode in scope under two podcasts (one show, two catalog rows)
    by_key: dict[str, list[dict]] = defaultdict(list)
    for e in eps:
        if len(e["norm"]) >= 10 and e["published_date"]:
            by_key[e["norm"]].append(e)
    for group in by_key.values():
        if len({e["podcast_id"] for e in group}) < 2:
            continue
        group.sort(key=lambda e: (e["published_date"], e["id"]))
        for i, e in enumerate(group):
            for o in group[:i]:
                if o["podcast_id"] == e["podcast_id"]:
                    continue
                days = abs((date.fromisoformat(e["published_date"][:10])
                            - date.fromisoformat(o["published_date"][:10])).days)
                da, db_ = o["duration_seconds"] or 0, e["duration_seconds"] or 0
                if days <= 1 and (not da or not db_ or abs(da - db_) <= max(5, 0.02 * max(da, db_))):
                    flag(e, "dup_other_podcast",
                         f"podcast {o['podcast_id']} ({o['entity']}) has {o['id']} "
                         f"({o['published_date'][:10]}, {da} s): {o['title']}", o["id"])
                    break

    # -- 2a+. reruns of an older episode of the same podcast (in scope or not)
    for pid, podcast_eps in by_podcast.items():
        older = [{**dict(r), "norm": norm_title(r["title"])} for r in conn.execute(
            "SELECT id, title, published_date, duration_seconds FROM episodes "
            "WHERE podcast_id = ? AND published_date IS NOT NULL", (pid,))]
        by_d: dict[int, list[dict]] = defaultdict(list)
        for r in older:
            if r["duration_seconds"]:
                by_d[r["duration_seconds"]].append(r)
        flagged_here = {f["episode_id"] for f in flags if f["issue"].startswith("dup_title")}
        for e in podcast_eps:
            d = e["duration_seconds"] or 0
            if d <= REPOST_MIN_SECONDS or e["id"] in flagged_here or not e["published_date"]:
                continue
            cutoff = (date.fromisoformat(e["published_date"][:10]) - timedelta(days=7)).isoformat()
            tol = max(5, int(0.01 * d))
            hit = next((r for dd in range(-tol, tol + 1) for r in by_d.get(d + dd, [])
                        if r["id"] != e["id"] and r["published_date"][:10] < cutoff
                        and min(len(r["norm"]), len(e["norm"])) >= 12
                        and (r["norm"] in e["norm"] or e["norm"] in r["norm"])
                        and numbers(r["title"]) == numbers(e["title"])
                        and (r["norm"] != e["norm"] or abs(r["duration_seconds"] - d) <= 2
                             or (RERUN.search(e["title"] or "") and not RERUN.search(r["title"] or "")))),
                       None)
            if hit:
                flag(e, "rerun_of_earlier",
                     f"same title and duration as {hit['id']} ({hit['published_date'][:10]}, "
                     f"{hit['duration_seconds']} s, in_scope={hit['id'] in in_scope}): {hit['title']}", hit["id"])

    # -- 2a++. old episode numbers re-posted ("542: ..." in a 2018 This American Life feed)
    for pid, podcast_eps in by_podcast.items():
        running, high = 0, {}
        for d, t in conn.execute("SELECT substr(published_date, 1, 10), title FROM episodes "
                                 "WHERE podcast_id = ? AND published_date IS NOT NULL "
                                 "ORDER BY published_date", (pid,)):
            m = LEADING_NUMBER.match(t or "")
            if m:
                running = max(running, int(m.group(1)))
            high[d] = running
        already = {f["episode_id"] for f in flags}
        for e in podcast_eps:
            m = LEADING_NUMBER.match(e["title"] or "")
            top = high.get((e["published_date"] or "")[:10], 0)
            if m and e["id"] not in already and top >= 50 and int(m.group(1)) < top - OLD_NUMBER_GAP:
                flag(e, "rerun_old_number", f"episode number {m.group(1)} while the feed had reached {top}")

    # -- 2a''. episodes another catalog podcast also carries (feed swaps, re-posted series)
    by_dur: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for r in conn.execute("""
        SELECT id, podcast_id, title, published_date, duration_seconds FROM episodes
        WHERE duration_seconds > ?
    """, (REPOST_MIN_SECONDS,)):
        by_dur[r["duration_seconds"]].append({**dict(r), "norm": norm_title(r["title"])})
    for e in eps:
        d = e["duration_seconds"] or 0
        if d <= REPOST_MIN_SECONDS or len(e["norm"]) < 6:
            continue
        for dd in (-1, 0, 1):
            hit = next((r for r in by_dur.get(d + dd, []) if r["podcast_id"] != e["podcast_id"]
                        and same_recording(e, r)), None)
            if hit:
                earlier = (hit["published_date"] or "") < (e["published_date"] or "")
                flag(e, "repost_of_other_podcast" if earlier else "reposted_elsewhere",
                     f"{'earlier' if earlier else 'later'} copy in podcast {hit['podcast_id']}: {hit['id']} "
                     f"({(hit['published_date'] or '')[:10]}, {hit['duration_seconds']} s): {hit['title']}",
                     hit["id"])
                break

    # -- 2a'''. another show's episode or trailer dropped into this feed
    titles = {r["id"]: r["title"] for r in conn.execute(
        f"SELECT id, title FROM podcasts WHERE id IN ({','.join(map(str, by_podcast))})")}
    for e in eps:
        m = FEED_DROP.search(e["title"] or "")
        if not m:
            continue
        own = norm_title(titles[e["podcast_id"]])
        rest = norm_title(e["title"][m.end():])
        if own and rest and (own[:12] in rest or rest[:12] in own):
            continue   # the show introducing itself
        flag(e, "feed_drop", f"'{m.group(0).strip()}' in a feed of '{titles[e['podcast_id']]}'"
                             f" ({e['episode_type']}, {e['duration_seconds']} s)")

    # -- 2b. wayback copies of live-feed episodes (whole podcast, either side in scope)
    podcasts = sorted(by_podcast)
    for pid in podcasts:
        rows = [dict(r) for r in conn.execute("""
            SELECT e.id, e.podcast_id, e.title, e.published_date, e.duration_seconds, e.status,
                   (SELECT group_concat(x.source) FROM episode_sources x WHERE x.episode_id = e.id) AS sources
            FROM episodes e WHERE e.podcast_id = ? AND e.published_date IS NOT NULL
        """, (pid,))]
        wb = [r for r in rows if r["sources"] == "wayback_feed"]
        if not wb:
            continue
        live_by_day: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            if r["sources"] != "wayback_feed":
                live_by_day[r["published_date"][:10]].append(r)
        for w in wb:
            if w["id"] not in in_scope:
                continue
            d0 = date.fromisoformat(w["published_date"][:10])
            wn = re.sub(r"[^a-z0-9]+", "", (w["title"] or "").lower())
            best = None
            for dd in (-1, 0, 1):
                for r in live_by_day.get((d0 + timedelta(days=dd)).isoformat(), []):
                    s = sim(wn, re.sub(r"[^a-z0-9]+", "", (r["title"] or "").lower()))
                    da, db_ = w["duration_seconds"] or 0, r["duration_seconds"] or 0
                    same_len = abs(da - db_) <= max(5, 0.02 * max(da, db_)) if da and db_ else s >= 0.95
                    if s >= 0.85 and same_len and (best is None or s > best[0]):
                        best = (s, r)
            if best:
                r = best[1]
                ep = next(e for e in by_podcast[pid] if e["id"] == w["id"])
                flag(ep, "wayback_dup_of_feed",
                     f"live {r['id']} ({r['published_date'][:10]}, {r['status']}, in_scope={r['id'] in in_scope}): "
                     f"{r['title']} [sim {best[0]:.2f}, dur {w['duration_seconds']} vs {r['duration_seconds']}]",
                     r["id"])

    # -- 3. dates
    bulk: dict[tuple[int, str], int] = {}
    for r in conn.execute(f"""
        SELECT podcast_id, substr(published_date, 1, 10) AS day, COUNT(*) AS n FROM episodes
        WHERE podcast_id IN ({",".join(map(str, podcasts))}) AND published_date IS NOT NULL
        GROUP BY 1, 2 HAVING n > ?
    """, (BULK_DAY,)):
        bulk[(r["podcast_id"], r["day"])] = r["n"]
    for e in eps:
        day = (e["published_date"] or "")[:10]
        if (e["podcast_id"], day) in bulk:
            flag(e, "bulk_day", f"{bulk[(e['podcast_id'], day)]} episodes of this podcast dated {day}")
        if day > TODAY:
            flag(e, "future_date", day)

    # -- 5. content type
    for e in eps:
        if e["episode_type"] in ("trailer", "bonus"):
            flag(e, e["episode_type"])
        if e["duration_seconds"] is not None and 0 < e["duration_seconds"] < SHORT_SECONDS:
            flag(e, "short_lt180", f"{e['duration_seconds']} s")
        if not e["duration_seconds"]:
            flag(e, "zero_or_missing_duration")

    # -- 6. windows
    by_ep_issue: dict[int, set[str]] = defaultdict(set)
    for f in flags:
        by_ep_issue[f["episode_id"]].add(f["issue"])
    win_eps: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in eps:
        win_eps[(e["entity"], e["window_label"])].append(e)
    members = {r["entity"]: r for r in conn.execute(
        "SELECT entity, name, podcast_id FROM study_members WHERE study = ?", (study,))}
    windows = []
    drop = {"dup_title_same_window", "dup_title_other_window", "dup_other_podcast",
            "repost_of_other_podcast", "feed_drop", "rerun_of_earlier", "rerun_old_number",
            "wayback_dup_of_feed", "bulk_day", "future_date", "trailer", "short_lt180"}
    for w in conn.execute("SELECT * FROM study_windows WHERE study = ? ORDER BY label, entity", (study,)):
        a = json.loads(w["attrs"] or "{}")
        we = win_eps.get((w["entity"], w["label"]), [])
        clean = [e for e in we if not (by_ep_issue[e["id"]] & drop)]
        bulk_only = bool(we) and all("bulk_day" in by_ep_issue[e["id"]] for e in we)
        trailer_only = bool(we) and all(by_ep_issue[e["id"]] & {"trailer", "short_lt180"} for e in we)
        windows.append({"entity": w["entity"], "name": members[w["entity"]]["name"],
                        "podcast_id": members[w["entity"]]["podcast_id"], "label": w["label"],
                        "monthly_rank": a.get("monthly_rank"), "points": a.get("points"),
                        "mean_points": a.get("mean_points"), "best_rank": a.get("best_rank"),
                        "snapshots_in_month": a.get("snapshots_in_month"),
                        "in_month_coverage": a.get("in_month_coverage"),
                        "sources": ",".join(a.get("sources", [])), "episodes": len(we),
                        "episodes_clean": len(clean), "bulk_only": bulk_only, "trailer_only": trailer_only})
    with open(out / "windows.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(windows[0]))
        wr.writeheader()
        wr.writerows(windows)
    with open(out / "flagged_episodes.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(flags[0]))
        wr.writeheader()
        wr.writerows(sorted(flags, key=lambda r: (r["issue"], r["podcast_id"], r["published_date"])))
    issue_counts = Counter(f["issue"] for f in flags)
    hours = defaultdict(float)
    for f in flags:
        hours[f["issue"]] += (f["duration_seconds"] or 0) / 3600
    summary = {
        "episodes": len(eps), "flag_rows": len(flags), "flagged_episodes": len({f["episode_id"] for f in flags}),
        "issues": {k: {"episodes": v, "hours": round(hours[k], 1)} for k, v in issue_counts.most_common()},
        "windows": len(windows),
        "windows_with_episodes": sum(1 for w in windows if w["episodes"]),
        "windows_bulk_only": sum(1 for w in windows if w["bulk_only"]),
        "windows_trailer_only": sum(1 for w in windows if w["trailer_only"]),
        "windows_nonempty_but_no_clean": sum(1 for w in windows if w["episodes"] and not w["episodes_clean"]),
        "windows_imputed": sum(1 for w in windows if w["snapshots_in_month"] == 0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
