"""Episodes for a study's gap windows from a hosting platform's public catalog API.

A feed can be capped (the newest N items) or trimmed by the publisher, while
the host still lists every published episode through its public API:

* **Simplecast** -- ``api.simplecast.com/podcasts/<id>/episodes`` (no key);
  the podcast id is read from the show's enclosure URLs.
* **Omny Studio** -- ``omny.fm/api/orgs/<org>/programs/<program>/clips``
  (no key; robots.txt allows all); org and program come from the playlist
  feed URL.

Only publicly listed episodes are taken (Simplecast ``status=published``,
``is_hidden`` false; Omny ``Visibility`` ``Public``), through unauthenticated
public URLs. Shows whose back catalog the publisher now sells
(``PAYWALLED_ARCHIVES``) are refused unless ``--allow-paywalled-archive`` is
given -- a decision for the project owner (taken for The Daily and The Run-Up
on 2026-10-03), which is then recorded in each row's evidence.

For each podcast given, the items published inside its gap windows
(``studies/gaps.py``) that the catalog does not already hold (guid, or UTC day
+ normalized title) are probed with a small ranged GET and written as
``import-episodes`` JSONL. Nothing is written to the database.

    ../.venv/bin/python tools/alternate_sources/host_catalog.py apple-top24-monthly OUT_DIR 717 769 ...
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from podcast_pipeline.studies.gaps import study_gaps  # noqa: E402
from tools.alternate_sources.common import (  # noqa: E402
    Fetcher, open_db, range_probe, title_key, write_jsonl,
)

SOURCE = "host_catalog"   # output file stem; import with --source alternate_host
# Simplecast account audio hosts whose shows' archives are subscriber-only now
# (New York Times podcasts since October 2024: only the newest few episodes are
# free; the archive is sold on Apple Podcasts / Spotify).
PAYWALLED_ARCHIVES = {"nyt.simplecastaudio.com": "New York Times podcast archives are subscriber-only "
                                                 "since 2024-10"}
PAGE_SIZE = 100
MAX_PAGES = 60

_SIMPLECAST = re.compile(r"(?:([a-z0-9-]+)\.simplecastaudio\.com|cdn\.simplecast\.com/audio)/"
                         r"([0-9a-f-]{36})/episodes/")
_OMNY = re.compile(r"omnycontent\.com/d/playlist/([0-9a-f-]{36})/([0-9a-f-]{36})/")


def _utc(stamp: str) -> str:
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0).isoformat()


def detect_host(conn, podcast_id: int,
                allow_paywalled: bool = False) -> tuple[str, dict] | tuple[None, str]:
    rss = conn.execute("SELECT rss_url FROM podcasts WHERE id = ?", (podcast_id,)).fetchone()[0] or ""
    m = _OMNY.search(rss)
    if m:
        return "omny", {"org": m.group(1), "program": m.group(2)}
    for (url,) in conn.execute("SELECT audio_url FROM episodes WHERE podcast_id = ? AND audio_url "
                               "LIKE '%simplecast%' ORDER BY published_date DESC LIMIT 20", (podcast_id,)):
        m = _SIMPLECAST.search(url)
        if m:
            host = f"{m.group(1)}.simplecastaudio.com" if m.group(1) else "cdn.simplecast.com"
            if host in PAYWALLED_ARCHIVES and not allow_paywalled:
                return None, f"{host}: {PAYWALLED_ARCHIVES[host]}"
            return "simplecast", {"podcast": m.group(2), "audio_host": host}
    return None, f"no supported host for feed {rss!r}"


def simplecast_episodes(fetcher: Fetcher, podcast: str, **_) -> list[dict]:
    out = []
    url = (f"https://api.simplecast.com/podcasts/{podcast}/episodes?limit={PAGE_SIZE}"
           "&private=false&sort=latest&status=published")
    for _ in range(MAX_PAGES):
        data = fetcher.get_json(url)
        for e in data["collection"]:
            if e.get("is_hidden") or e.get("status") != "published" or not e.get("enclosure_url"):
                continue
            out.append({"guid": e.get("guid") or e["id"], "title": e["title"],
                        "published_date": _utc(e["published_at"]), "audio_url": e["enclosure_url"],
                        "duration_seconds": e.get("duration"), "description": e.get("description") or "",
                        "host_ref": e["href"]})
        nxt = (data.get("pages") or {}).get("next")
        if not nxt:
            return out
        url = nxt["href"]
    raise RuntimeError(f"simplecast {podcast}: more than {MAX_PAGES} pages")


def omny_episodes(fetcher: Fetcher, org: str, program: str) -> list[dict]:
    out = []
    base = f"https://omny.fm/api/orgs/{org}/programs/{program}/clips?pageSize={PAGE_SIZE}"
    url = base
    for _ in range(MAX_PAGES):
        data = fetcher.get_json(url)
        for c in data["Clips"]:
            if c.get("Visibility") != "Public" or not c.get("AudioUrl") or not c.get("PublishedUtc"):
                continue
            out.append({"guid": c["Id"], "title": c["Title"], "published_date": _utc(c["PublishedUtc"]),
                        "audio_url": c["AudioUrl"], "duration_seconds": c.get("DurationSeconds"),
                        "description": c.get("Description") or "",
                        "host_ref": c.get("PublishedUrl") or c["Id"]})
        cursor = data.get("Cursor")
        if not cursor or not data["Clips"]:
            return out
        url = f"{base}&cursor={cursor}"
    raise RuntimeError(f"omny {program}: more than {MAX_PAGES} pages")


BACKENDS = {"simplecast": simplecast_episodes, "omny": omny_episodes}


def collect(conn, fetcher: Fetcher, study: str, podcast_id: int, allow_paywalled: bool = False,
            probe_every: int = 1) -> tuple[list[dict], dict]:
    """Rows for the podcast's gap windows: new episodes, and repairs of matching
    episodes whose download failed (``replaces_episode_id``). Anything else the
    catalog already holds is skipped."""
    log = {"podcast_id": podcast_id}
    gaps = next((g for g in study_gaps(conn, study) if g.podcast_id == podcast_id), None)
    if gaps is None:
        log["problem"] = "no gap windows"
        return [], log
    host, info = detect_host(conn, podcast_id, allow_paywalled)
    if host is None:
        log["problem"] = info
        return [], log
    log.update(host=host, **info)
    paywalled = PAYWALLED_ARCHIVES.get(info.get("audio_host", ""))
    listed = BACKENDS[host](fetcher, **{k: v for k, v in info.items() if k != "audio_host"})
    log["listed"] = len(listed)
    if listed:
        log["listed_span"] = [min(e["published_date"] for e in listed), max(e["published_date"] for e in listed)]
    rows_db = conn.execute("""SELECT id, episode_guid, title, published_date, status, audio_file_path
                              FROM episodes WHERE podcast_id = ?""", (podcast_id,)).fetchall()
    by_guid = {r["episode_guid"]: r for r in rows_db}
    by_key = {((r["published_date"] or "")[:10], title_key(r["title"])): r for r in rows_db}
    rows, windows = [], {}
    for e in sorted(listed, key=lambda e: e["published_date"]):
        window = next((w for w in gaps.windows if w[1] <= e["published_date"][:10] < w[2]), None)
        if window is None:
            continue
        counts = windows.setdefault(window[0], {"listed": 0, "new": 0, "repair": 0})
        counts["listed"] += 1
        known = by_guid.get(e["guid"]) or by_key.get((e["published_date"][:10], title_key(e["title"])))
        stuck = known is not None and known["status"] == "error" and not known["audio_file_path"]
        if known is not None and not stuck:
            continue
        counts["repair" if stuck else "new"] += 1
        evidence = {"route": f"{host} public catalog API (unauthenticated)", "host_ref": e["host_ref"],
                    "window": window[0], "declared_seconds": e["duration_seconds"]}
        if paywalled:
            evidence["paywalled_archive"] = f"{paywalled}; imported by the project owner's decision"
        if (len(rows) % probe_every) == 0:
            probe = range_probe(fetcher, e["audio_url"])
            evidence["probe"] = {"is_audio": probe.is_audio, "status": probe.status,
                                 "total_size": probe.total_size, "error": probe.error,
                                 "estimated_seconds": (probe.duration or {}).get("seconds"),
                                 "declared_seconds": e["duration_seconds"], "id3_title": probe.id3_title}
        row = {"podcast_id": podcast_id, "guid": known["episode_guid"] if stuck else e["guid"],
               "title": e["title"], "published_date": e["published_date"], "audio_url": e["audio_url"],
               "description": re.sub(r"<[^>]+>", " ", e["description"])[:1000], "evidence": evidence}
        if stuck:
            row["replaces_episode_id"] = known["id"]
        if e["duration_seconds"]:
            row["duration_seconds"] = round(e["duration_seconds"])
        rows.append(row)
    log["windows"] = windows
    log["new_episodes"] = sum(1 for r in rows if "replaces_episode_id" not in r)
    log["repairs"] = len(rows) - log["new_episodes"]
    return rows, log


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("study")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("podcast_ids", type=int, nargs="+")
    ap.add_argument("--allow-paywalled-archive", action="store_true",
                    help="import from PAYWALLED_ARCHIVES hosts too (the project owner's decision)")
    ap.add_argument("--probe-every", type=int, default=1, help="range-probe every k-th row (a sample)")
    args = ap.parse_args()

    conn = open_db()
    fetcher = Fetcher()
    rows, logs = [], []
    for pid in args.podcast_ids:
        got, log = collect(conn, fetcher, args.study, pid, args.allow_paywalled_archive, args.probe_every)
        rows += got
        logs.append(log)
        probed = [r["evidence"]["probe"] for r in got if "probe" in r["evidence"]]
        live = sum(p["is_audio"] for p in probed)
        print(f"{pid}: {log.get('problem') or ''}{log.get('listed', '')} listed, "
              f"{log.get('new_episodes', 0)} new + {log.get('repairs', 0)} repairs in gap windows "
              f"({live}/{len(probed)} probed live) {log.get('windows', '')}", flush=True)
        write_jsonl(args.out_dir / f"{SOURCE}.jsonl", rows)
        write_jsonl(args.out_dir / f"{SOURCE}.log.jsonl", logs)


if __name__ == "__main__":
    main()
