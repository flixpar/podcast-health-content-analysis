"""Where a study stands in every stage, and what to run next.

Read-only, so it is safe while ``download`` is running.
"""

from __future__ import annotations

import json
import shutil
import sqlite3

from podcast_pipeline.config import Config
from podcast_pipeline.studies.gaps import study_gaps
from podcast_pipeline.studies.scope import require_refreshed

# Episode state, from the shared catalog's point of view. The order is the
# order of precedence: an episode with a transcript is done however it got it.
EPISODE_STATE_SQL = """
    CASE
        WHEN t.episode_id IS NOT NULL AND json_extract(t.metadata, '$.source') = 'rss' THEN 'transcribed_rss'
        WHEN t.episode_id IS NOT NULL THEN 'transcribed_asr'
        WHEN e.has_rss_transcript = 1 THEN 'awaiting_rss_transcript'
        WHEN e.audio_file_path IS NOT NULL AND e.audio_file_path != '' AND e.status = 'error' THEN 'asr_failed'
        WHEN e.audio_file_path IS NOT NULL AND e.audio_file_path != '' THEN 'awaiting_asr'
        WHEN e.audio_url IS NULL OR e.audio_url = '' THEN 'no_audio_url'
        WHEN e.status = 'error' THEN 'download_failed'
        ELSE 'awaiting_download'
    END
"""


def status(config: Config, conn: sqlite3.Connection, name: str, by: str = "year") -> dict:
    require_refreshed(conn, name)
    study = conn.execute("SELECT * FROM studies WHERE name = ?", (name,)).fetchone()
    out: dict = {
        "study": name,
        "description": study["description"],
        "revision": study["revision"],
        "refreshed_at": study["refreshed_at"],
        "definition_hash": study["definition_hash"],
        "last_refresh": json.loads(study["summary"] or "{}"),
    }

    m = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(sm.podcast_id IS NOT NULL) AS resolved,
               SUM(p.rss_url IS NOT NULL AND p.rss_url != '') AS with_feed,
               SUM(sm.podcast_id IS NOT NULL AND (p.rss_url IS NULL OR p.rss_url = '')) AS without_feed,
               SUM(p.status = 'discovered') AS feed_read,
               SUM(p.status = 'error') AS feed_error,
               SUM(p.rss_url IS NOT NULL AND p.rss_url != '' AND p.status = 'pending') AS feed_never_read
        FROM study_members sm LEFT JOIN podcasts p ON p.id = sm.podcast_id
        WHERE sm.study = ?
    """, (name,)).fetchone()
    out["members"] = {k: m[k] or 0 for k in m.keys()}
    out["members"]["unresolved"] = out["members"]["total"] - out["members"]["resolved"]
    out["members"]["resolution_failed"] = conn.execute("""
        SELECT COUNT(*) FROM study_members sm JOIN entity_links l ON l.entity = sm.entity
        WHERE sm.study = ? AND sm.podcast_id IS NULL AND l.podcast_id IS NULL
    """, (name,)).fetchone()[0]

    states = conn.execute(f"""
        SELECT {EPISODE_STATE_SQL} AS state, COUNT(*) AS n,
               COALESCE(SUM(e.duration_seconds), 0) / 3600.0 AS hours
        FROM study_episodes se JOIN episodes e ON e.id = se.episode_id
        LEFT JOIN transcripts t ON t.episode_id = e.id
        WHERE se.study = ? GROUP BY state
    """, (name,)).fetchall()
    out["episodes"] = {"total": sum(r["n"] for r in states), **{r["state"]: r["n"] for r in states}}
    out["hours"] = {r["state"]: round(r["hours"], 1) for r in states}
    done = out["episodes"].get("transcribed_rss", 0) + out["episodes"].get("transcribed_asr", 0)
    out["episodes"]["transcribed_share"] = round(done / out["episodes"]["total"], 3) if out["episodes"]["total"] else None

    out["provenance"] = {r["source"]: r["n"] for r in conn.execute("""
        SELECT es.source, COUNT(DISTINCT es.episode_id) AS n
        FROM study_episodes se JOIN episode_sources es ON es.episode_id = se.episode_id
        WHERE se.study = ? GROUP BY es.source
    """, (name,))}
    out["shared"] = {r["study"]: r["n"] for r in conn.execute("""
        SELECT o.study, COUNT(*) AS n FROM study_episodes se
        JOIN study_episodes o ON o.episode_id = se.episode_id AND o.study != se.study
        WHERE se.study = ? GROUP BY o.study
    """, (name,))}

    out["storage"] = _storage(config, conn, out["hours"].get("awaiting_download", 0.0),
                              out["episodes"].get("awaiting_download", 0))

    windowed = conn.execute("SELECT COUNT(*) FROM study_windows WHERE study = ?", (name,)).fetchone()[0]
    if windowed:
        out["windows"] = _window_coverage(conn, name)
        gaps = study_gaps(conn, name)
        out["windows"]["gap_windows"] = sum(len(g.windows) for g in gaps)
        out["windows"]["gap_windows_empty"] = sum(len(g.empty) for g in gaps)
        out["windows"]["podcasts_with_gaps"] = len(gaps)
    out["wayback_probes"] = {r["status"]: r["n"] for r in conn.execute("""
        SELECT w.status, COUNT(*) AS n FROM wayback_probes w
        WHERE w.podcast_id IN (SELECT podcast_id FROM study_members WHERE study = ?)
        GROUP BY w.status
    """, (name,))}

    out[f"by_{by}"] = _breakdown(conn, name, by)
    out["next_steps"] = _next_steps(name, out)
    return out


def _storage(config: Config, conn, pending_hours: float, pending_episodes: int) -> dict:
    """Projected audio volume for what is still to download.

    The rate is measured on this archive's own downloads (24 kbps Opus plus
    files kept as-is), not assumed. Episodes without a declared duration are
    costed at the mean declared duration.
    """
    rate = conn.execute("""
        SELECT SUM(compressed_file_size_mb) / (SUM(duration_seconds) / 3600.0)
        FROM episodes
        WHERE compressed_file_size_mb > 0 AND duration_seconds > 0
    """).fetchone()[0] or 11.0
    usage = shutil.disk_usage(config.audio_dir if config.audio_dir.exists() else config.data_path)
    return {
        "mb_per_hour_measured": round(rate, 2),
        "pending_download_gb_estimate": round(pending_hours * rate / 1024, 1),
        "pending_download_episodes": pending_episodes,
        "free_gb": round(usage.free / 1024 ** 3, 1),
        "download_stops_below_gb": config.download.min_free_gb,
        "usable_gb": round(usage.free / 1024 ** 3 - config.download.min_free_gb, 1),
    }


def _window_coverage(conn, name: str) -> dict:
    r = conn.execute(f"""
        WITH per_window AS (
            SELECT w.entity, w.label,
                   json_extract(w.attrs, '$.snapshots_in_month') AS snaps,
                   COUNT(se.episode_id) AS n,
                   SUM(t.episode_id IS NOT NULL) AS transcribed
            FROM study_windows w
            LEFT JOIN study_episodes se
                   ON se.study = w.study AND se.entity = w.entity AND se.window_label = w.label
            LEFT JOIN transcripts t ON t.episode_id = se.episode_id
            WHERE w.study = ?
            GROUP BY w.entity, w.label
        )
        SELECT COUNT(*) AS total,
               SUM(n > 0) AS with_episodes,
               SUM(transcribed > 0) AS with_transcript,
               SUM(snaps = 0) AS imputed_from_neighbouring_snapshots
        FROM per_window
    """, (name,)).fetchone()
    return {k: r[k] or 0 for k in r.keys()}


def _breakdown(conn, name: str, by: str) -> list[dict]:
    if by == "member":
        group, label = "sm.entity", "sm.name"
    elif by == "window":
        group, label = "COALESCE(se.window_label, 'all')", "COALESCE(se.window_label, 'all')"
    else:
        group = label = "COALESCE(substr(se.window_label, 1, 4), substr(e.published_date, 1, 4))"
    rows = conn.execute(f"""
        SELECT {group} AS key, MIN({label}) AS label, COUNT(*) AS episodes,
               SUM(t.episode_id IS NOT NULL) AS transcribed,
               SUM(t.episode_id IS NULL AND e.audio_file_path IS NOT NULL AND e.audio_file_path != '') AS awaiting_asr,
               SUM(t.episode_id IS NULL AND (e.audio_file_path IS NULL OR e.audio_file_path = '')
                   AND e.has_rss_transcript = 0) AS needs_audio
        FROM study_episodes se JOIN episodes e ON e.id = se.episode_id
        JOIN study_members sm ON sm.study = se.study AND sm.entity = se.entity
        LEFT JOIN transcripts t ON t.episode_id = e.id
        WHERE se.study = ? GROUP BY key ORDER BY key
    """, (name,)).fetchall()
    result = [dict(r) for r in rows]
    if by == "year" and conn.execute("SELECT 1 FROM study_windows WHERE study = ? LIMIT 1", (name,)).fetchone():
        windows = {r["y"]: (r["n"], r["filled"]) for r in conn.execute("""
            SELECT substr(w.label, 1, 4) AS y, COUNT(*) AS n,
                   SUM(EXISTS (SELECT 1 FROM study_episodes se WHERE se.study = w.study
                               AND se.entity = w.entity AND se.window_label = w.label)) AS filled
            FROM study_windows w WHERE w.study = ? GROUP BY y
        """, (name,))}
        for r in result:
            n, filled = windows.get(r["key"], (0, 0))
            r["windows"], r["windows_with_episodes"] = n, filled
    return result


def _next_steps(name: str, s: dict) -> list[str]:
    steps = []
    members, episodes = s["members"], s["episodes"]
    unattempted = members["unresolved"] - members["resolution_failed"]
    if unattempted or members["without_feed"]:
        steps.append(f"resolve --study {name}   # {unattempted} members not yet resolved to a podcast, "
                     f"{members['without_feed']} resolved without a feed URL; then `study refresh {name}`")
    if members["feed_never_read"]:
        steps.append(f"discover --study {name}   # {members['feed_never_read']} resolved podcasts "
                     f"never had their feed read; then `study refresh {name}`")
    if s.get("windows", {}).get("gap_windows"):
        w = s["windows"]
        steps.append(f"discover-archived --study {name}   # {w['gap_windows']} windows across "
                     f"{w['podcasts_with_gaps']} podcasts that live feeds do not fully reach "
                     f"({w['gap_windows_empty']} empty); then `study refresh {name}`")
    if episodes.get("awaiting_rss_transcript"):
        steps.append(f"fetch-rss-transcripts --study {name}   # {episodes['awaiting_rss_transcript']} "
                     f"publisher transcripts to fetch")
    if episodes.get("awaiting_download"):
        st = s["storage"]
        note = "" if st["pending_download_gb_estimate"] < st["usable_gb"] else \
            f"; WARNING: ~{st['pending_download_gb_estimate']} GB needed, {st['usable_gb']} GB usable"
        steps.append(f"download --study {name}   # {episodes['awaiting_download']} episodes, "
                     f"~{st['pending_download_gb_estimate']} GB{note}")
    if episodes.get("download_failed"):
        steps.append(f"download --study {name} --wayback-fallback   # retry "
                     f"{episodes['download_failed']} failed downloads via archived audio")
    if episodes.get("awaiting_asr"):
        steps.append(f"export-audio-batch <dir> --study {name}  (or transcribe --study {name})   # "
                     f"{episodes['awaiting_asr']} episodes have audio but no transcript")
    return steps
