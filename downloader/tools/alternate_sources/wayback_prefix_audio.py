"""Archived audio for failed downloads, found by Wayback *prefix* searches.

``download --wayback-fallback`` asks Wayback for exactly the enclosure URL
(and the URL inside its tracking prefixes), query string and all. Two things
defeat that and this tool works around both:

* the audio was captured under a variant URL -- another query string
  (``?rss_browser=...``, ``&from=PodcastAddict``), no query, http vs https --
  so the CDX listing is searched with ``matchType=prefix`` on host + path;
* the capture is a redirect whose archived chain loops or runs past requests'
  30-hop limit (Art19's ``/episodes/`` -> ``/external/episodes/`` -> CDN), so
  hops are followed by hand.

For each failed episode (``status='error'``, no audio) in a study, every
capture found is resolved, nearest the publication date first, until one
yields audio whose estimated length fits the declared duration. Found audio is
written as ``import-episodes`` rows that repair the episode in place
(``replaces_episode_id``); every attempt is logged to a second file.

    ../.venv/bin/python tools/alternate_sources/wayback_prefix_audio.py \\
        apple-top24-monthly OUT_DIR [--exclude-podcast 13] [--episode ID ...]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from podcast_pipeline.audio.download import unwrap_tracking_url  # noqa: E402
from podcast_pipeline.config import Config  # noqa: E402
from tools.alternate_sources.common import (  # noqa: E402
    Fetcher, cdx_prefix, duration_matches, open_db, read_jsonl, strip_query, wayback_resolve,
    write_jsonl,
)

MAX_CAPTURES_TRIED = 3
SOURCE = "wayback_prefix"
DEFINITIVE = ("found", "not archived", "no capture yields audio", "audio of the wrong length")


def _transient(log: dict) -> bool:
    """Whether an attempt failed for reasons that say nothing about the archive."""
    return any("request failed" in (t.get("problem") or "") for t in log["tried"]) \
        or any(str(v).startswith("error") for v in log["prefixes"].values())


def failed_episodes(conn, study: str, exclude: set[int], only: set[int] | None) -> list[dict]:
    rows = conn.execute("""
        SELECT e.id, e.podcast_id, p.title AS podcast, e.title, e.published_date,
               e.duration_seconds, e.episode_guid, e.audio_url
        FROM study_episodes se JOIN episodes e ON e.id = se.episode_id
        JOIN podcasts p ON p.id = e.podcast_id
        WHERE se.study = ? AND e.status = 'error'
          AND (e.audio_file_path IS NULL OR e.audio_file_path = '')
        ORDER BY p.title, e.published_date
    """, (study,)).fetchall()
    return [dict(r) for r in rows
            if r["podcast_id"] not in exclude and (only is None or r["id"] in only)]


def prefixes(audio_url: str) -> list[str]:
    """Host+path prefixes to search: the enclosure as given, and inside its trackers."""
    out = []
    for url in (unwrap_tracking_url(audio_url), audio_url):
        p = strip_query(url)
        if p and p not in out:
            out.append(p)
    return out


def _distance(timestamp: str, published: str | None) -> float:
    if not published:
        return 0.0
    try:
        t = datetime.strptime(timestamp[:8], "%Y%m%d")
        p = datetime.fromisoformat(published[:10])
    except ValueError:
        return 0.0
    return abs((t - p).days)


def rank_captures(captures: list[dict], published: str | None) -> list[dict]:
    """Direct audio captures first, then redirects; nearest the publication date first.

    One capture per distinct (original URL, digest) is enough: equal digests are
    byte-identical.
    """
    usable = [c for c in captures if c["statuscode"] in ("200", "206", "301", "302", "303", "307")]
    seen, unique = set(), []
    for c in sorted(usable, key=lambda c: (c["statuscode"] not in ("200", "206"),
                                           _distance(c["timestamp"], published))):
        key = (c["original"], c["digest"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def media_key(audio_url: str) -> str | None:
    """The enclosure's file name without extension (a BBC vpid, an Art19 episode
    uuid), when it is distinctive enough to find the file under other URLs."""
    name = strip_query(unwrap_tracking_url(audio_url)).rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return name if len(name) >= 8 and not name.lower().startswith(("audio", "default", "media")) else None


def read_capture_dump(path: Path) -> dict[str, list[dict]]:
    """A CDX dump (``timestamp original statuscode`` per line, e.g. from a broad
    prefix query over a whole id range), indexed by ``media_key``."""
    out: dict[str, list[dict]] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        key = media_key(parts[1])
        if key:
            out.setdefault(key, []).append({"timestamp": parts[0], "original": parts[1],
                                            "statuscode": parts[2], "digest": f"{parts[0]}{parts[1]}"})
    return out


def search(fetcher: Fetcher, cdx_url: str, replay: str, ep: dict,
           dump: dict[str, list[dict]] | None = None, query_cdx: bool = True) -> tuple[dict | None, dict]:
    """(import row or None, attempt log) for one failed episode."""
    log = {"episode_id": ep["id"], "podcast": ep["podcast"], "title": ep["title"],
           "published_date": ep["published_date"], "declared_duration": ep["duration_seconds"],
           "prefixes": {}, "tried": [], "result": "not archived"}
    captures = []
    if dump is not None:
        found = dump.get(media_key(ep["audio_url"]) or "", [])
        log["prefixes"]["capture dump"] = len(found)
        captures += found
    for prefix in prefixes(ep["audio_url"]) if query_cdx else []:
        try:
            found = cdx_prefix(fetcher, cdx_url, prefix)
        except RuntimeError as e:
            log["prefixes"][prefix] = f"error: {e}"
            log["result"] = "cdx error"
            continue
        log["prefixes"][prefix] = len(found)
        captures += found
    ranked = rank_captures(captures, ep["published_date"])
    if ranked and log["result"] == "not archived":
        log["result"] = "no capture yields audio"
    for c in ranked[:MAX_CAPTURES_TRIED]:
        probe, hops, problem = wayback_resolve(fetcher, replay, c["timestamp"], c["original"])
        attempt = {"capture": f"{c['timestamp']} {c['original']}", "status": c["statuscode"],
                   "hops": len(hops)}
        log["tried"].append(attempt)
        if probe is None:
            attempt["problem"] = problem
            continue
        attempt["probe"] = probe.to_dict()
        if not probe.is_audio:
            attempt["problem"] = probe.error
            continue
        fits = duration_matches(probe, ep["duration_seconds"])
        if fits is False:
            attempt["problem"] = (f"length {probe.duration['seconds']}s does not fit declared "
                                  f"{ep['duration_seconds']}s")
            log["result"] = "audio of the wrong length"
            continue
        log["result"] = "found"
        row = {
            "podcast_id": ep["podcast_id"], "replaces_episode_id": ep["id"],
            "guid": ep["episode_guid"], "title": ep["title"],
            "published_date": ep["published_date"], "audio_url": probe.url,
            "evidence": {
                "route": "wayback prefix search on the enclosure's host+path",
                "previous_audio_url": ep["audio_url"],
                "capture": {"timestamp": c["timestamp"], "original": c["original"],
                            "statuscode": c["statuscode"], "redirect_hops": len(hops)},
                "probe": {"total_size": probe.total_size, "content_type": probe.content_type,
                          "estimated_seconds": (probe.duration or {}).get("seconds"),
                          "estimate_method": (probe.duration or {}).get("method"),
                          "declared_seconds": ep["duration_seconds"],
                          "duration_fits": fits, "id3_title": probe.id3_title},
            },
        }
        if ep["duration_seconds"]:
            row["duration_seconds"] = ep["duration_seconds"]
        return row, log
    return None, log


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("study")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--exclude-podcast", type=int, action="append", default=[])
    ap.add_argument("--episode", type=int, action="append")
    ap.add_argument("--podcast", type=int, action="append", help="only these podcasts")
    ap.add_argument("--captures", type=Path, help="a CDX dump to match episodes against by media key")
    ap.add_argument("--no-cdx", action="store_true", help="use only --captures, no per-episode queries")
    args = ap.parse_args()

    config = Config.load()
    conn = open_db()
    episodes = failed_episodes(conn, args.study, set(args.exclude_podcast),
                               set(args.episode) if args.episode else None)
    conn.close()
    if args.podcast:
        episodes = [ep for ep in episodes if ep["podcast_id"] in args.podcast]
    dump = read_capture_dump(args.captures) if args.captures else None
    fetcher = Fetcher()
    rows, logs = [], []
    # Resume: keep definitive outcomes from an earlier run into the same directory;
    # redo the rest (a refused connection or a CDX error is not an answer).
    attempts_path = args.out_dir / f"{SOURCE}.attempts.jsonl"
    if attempts_path.exists():
        found = {r["replaces_episode_id"]: r for r in read_jsonl(args.out_dir / f"{SOURCE}.jsonl")}
        for log in read_jsonl(attempts_path):
            if log["result"] in DEFINITIVE and not _transient(log):
                logs.append(log)
                if log["episode_id"] in found:
                    rows.append(found[log["episode_id"]])
        done = {log["episode_id"] for log in logs}
        episodes = [ep for ep in episodes if ep["id"] not in done]
        print(f"resuming: {len(done)} episodes already settled", flush=True)
    for n, ep in enumerate(episodes, 1):
        row, log = search(fetcher, config.wayback.cdx_url, config.wayback.replay_url, ep,
                          dump, query_cdx=not args.no_cdx)
        logs.append(log)
        if row:
            rows.append(row)
        print(f"[{n}/{len(episodes)}] {ep['podcast']} | {ep['title'][:50]}: {log['result']}",
              flush=True)
        # Flush as we go, so an interrupted run keeps what it found.
        write_jsonl(args.out_dir / f"{SOURCE}.jsonl", rows)
        write_jsonl(args.out_dir / f"{SOURCE}.attempts.jsonl", logs)
    print(f"{len(rows)} of {len(episodes)} failed episodes have archived audio")


if __name__ == "__main__":
    main()
