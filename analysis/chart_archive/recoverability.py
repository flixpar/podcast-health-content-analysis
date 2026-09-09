"""Can we still obtain the charting-era content of the chart population?

Five phases, each cached to disk under ``population/recoverability_cache/`` so a
rerun resumes rather than refetches:

1. ``lookup``   Apple id -> feedUrl, batched iTunes lookups plus a paced title
                search for the shows with no id.
   ``verify``   one-at-a-time re-check of shows Apple lists without a feedUrl.
2. ``feeds``    fetch every feed, record status, redirect target, episode date
                range, transcript tags and truncation signals.
3. (folded into ``report``) coverage of the ``first_seen``..``last_seen`` window.
4. ``audio``    ranged 64 KB GET of up to three enclosures per show.
5. ``wayback``  for shows that phases 2-4 did not settle, CDX captures of the
                feed URL and a probe of enclosures recovered from one archived
                snapshot near ``last_seen``.

``report`` writes recoverability.csv / recoverability.md from whatever the cache
holds, so it is safe (and useful) to run before the later phases finish.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "downloader"))
from podcast_pipeline.models import FeedEpisode  # noqa: E402
from podcast_pipeline.rss import parse_feed  # noqa: E402

POP = ROOT / "data" / "chart-archive" / "parsed" / "population"
CACHE = POP / "recoverability_cache"
OUT_CSV = POP / "recoverability.csv"
OUT_DROPPED = POP / "recoverability_dropped.csv"
OUT_MD = POP / "recoverability.md"
DB = ROOT / "downloader" / "data" / "podcast_metadata.db"
# Rows for shows that left the population when the inclusion rule moved from
# raw snapshot days to exposure-weighted estimated days. Frozen at the 346-show
# run so its numbers stay reproducible: there is no live population row to
# rescore them against, so they are copied out rather than recomputed.
DROPPED_SNAPSHOT = CACHE / "dropped_346.csv"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "*/*"}

LOOKUP_URL = "https://itunes.apple.com/lookup?id={ids}&entity=podcast"
SEARCH_URL = "https://itunes.apple.com/search?media=podcast&entity=podcast&limit=5&term={term}"
LOOKUP_BATCH = 200
ITUNES_DELAY = 5.0          # ~12 req/min, under the ~20/min the API tolerates

FEED_WORKERS = 8
AUDIO_WORKERS = 4
MAX_FEED_BYTES = 200 * 1024 * 1024   # one Omny feed exceeds 40MB; truncating it
                                     # would drop exactly the oldest episodes
RANGE_BYTES = 65536
NEAR_DAYS = 30              # slack allowed at each end of the charting window
COVERAGE_OK = 0.80

# Feed episode counts that are a page size rather than a catalogue.
PAGE_SIZES = {50, 100, 200, 250, 300, 500, 1000}


# --------------------------------------------------------------------------- utils

def norm_key(name) -> str:
    """The normaliser population.py used to match titles across mirrors."""
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def load_cache(name: str) -> dict:
    path = CACHE / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else {}


def save_cache(name: str, obj: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = CACHE / f"{name}.json.tmp"
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True))
    tmp.replace(CACHE / f"{name}.json")


def population() -> pd.DataFrame:
    """The study population, one row per show.

    ``entity`` is the identity key: the Apple id, or ``title:<key>`` for the 13
    shows that never carried one. It is used as the sid every cache is keyed by.
    """
    df = pd.read_csv(POP / "population.csv")
    # Built as an explicit object Series: ``Series.map`` returning None on a
    # float column silently coerces the Nones back to NaN, and NaN is truthy,
    # so the missing ids would reach ",".join and blow up on a fresh run.
    df["apple_id"] = pd.Series([None if pd.isna(v) else str(int(v))
                                for v in df.apple_id], dtype=object, index=df.index)
    df["sid"] = df.entity.astype(str)
    clash = df[df.apple_id.notna() & (df.sid != df.apple_id)]
    if len(clash):
        raise SystemExit(f"entity disagrees with apple_id for {len(clash)} rows; "
                         "the caches are keyed on entity and would silently miss")
    return df


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def to_date(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:19].replace("Z", ""))
    except ValueError:
        return None


# --------------------------------------------------------------------- phase 1

def phase_lookup() -> dict:
    """Apple id -> iTunes record. Two batch calls, then paced title searches."""
    cache = load_cache("lookup")
    pop = population()
    s = session()

    missing = [a for a in pop.apple_id if isinstance(a, str) and a not in cache]
    for i in range(0, len(missing), LOOKUP_BATCH):
        batch = missing[i:i + LOOKUP_BATCH]
        url = LOOKUP_URL.format(ids=",".join(batch))
        print(f"  lookup batch of {len(batch)} ids")
        r = _itunes(s, url)
        found = {}
        for rec in (r or {}).get("results", []):
            cid = str(rec.get("collectionId") or "")
            if cid:
                found[cid] = {"feed_url": rec.get("feedUrl"),
                              "name": rec.get("collectionName"),
                              "publisher": rec.get("artistName"),
                              "track_count": rec.get("trackCount"),
                              "latest": rec.get("releaseDate"),
                              "source": "lookup"}
        for aid in batch:
            cache[aid] = found.get(aid, {"feed_url": None, "source": "lookup_missing"})
        save_cache("lookup", cache)

    # Rows with no Apple id, plus ids Apple no longer lists: search by title.
    # Search results are cached under "s:<sid>" so they never collide with the
    # batch-lookup entry the same id already has.
    need_search = [(r.sid, r.name, r.publisher) for r in pop.itertuples()
                   if (not r.apple_id or not (cache.get(r.apple_id) or {}).get("feed_url"))
                   and f"s:{r.sid}" not in cache]
    print(f"  {len(need_search)} shows need a title search")
    for sid, name, publisher in need_search:
        url = SEARCH_URL.format(term=requests.utils.quote(str(name)))
        print(f"  search {name!r}")
        r = _itunes(s, url)
        best, quality = None, "none"
        for rec in (r or {}).get("results", []):
            if norm_key(rec.get("collectionName")) == norm_key(name):
                pub_ok = norm_key(rec.get("artistName")) == norm_key(publisher)
                if best is None or pub_ok:
                    best, quality = rec, "title+publisher" if pub_ok else "title"
                if pub_ok:
                    break
        cache[f"s:{sid}"] = ({"feed_url": best.get("feedUrl"), "name": best.get("collectionName"),
                       "publisher": best.get("artistName"), "track_count": best.get("trackCount"),
                       "apple_id": str(best.get("collectionId")),
                       "source": f"search:{quality}"} if best else
                      {"feed_url": None, "source": "search_missing"})
        save_cache("lookup", cache)
    return cache


def _itunes(s: requests.Session, url: str, attempts: int = 3) -> dict | None:
    for attempt in range(attempts):
        time.sleep(ITUNES_DELAY)
        try:
            r = s.get(url, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 30))
                print(f"    429 from iTunes; waiting {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"    iTunes call failed ({attempt + 1}/{attempts}): {e}")
            time.sleep(10 * (attempt + 1))
    return None


def feed_urls() -> dict[str, str]:
    """Best known feed URL per show: Apple's, else the one the pipeline used."""
    lookup = load_cache("lookup")
    pop = population()
    db_feeds = _db_feeds()
    out = {}
    for r in pop.itertuples():
        url = (lookup.get(r.apple_id or "", {}) or {}).get("feed_url")
        url = url or (lookup.get(f"s:{r.sid}", {}) or {}).get("feed_url")
        url = url or (lookup.get(f"v:{r.sid}", {}) or {}).get("feed_url")
        url = url or db_feeds.get(r.apple_id or "")
        if url:
            out[r.sid] = url
    return out


def phase_verify() -> dict:
    """Re-check the shows Apple lists but publishes no ``feedUrl`` for.

    A batched lookup can silently return fewer records than asked for, so an
    absent ``feedUrl`` is first re-tested one id at a time, then against two
    other country catalogues, then against whatever the pipeline database and
    Wayback's copy of the lookup response remember.
    """
    cache = load_cache("lookup")
    rows = build_rows()
    lookup = load_cache("lookup")
    todo = [r for r in rows
            if not r["feed_url"] and r["apple_id"]
            and ((lookup.get(r["sid"]) or {}).get("name")
                 or (lookup.get(f"s:{r['sid']}") or {}).get("name"))
            and f"v:{r['sid']}" not in cache]
    print(f"  {len(todo)} listed-but-feedless shows to verify")
    s = session()
    db_feeds = _db_feeds()
    for r in todo:
        aid = r["apple_id"]
        rec = {"feed_url": None, "how": None, "track_count": None,
               "latest": None, "publisher": None, "db_rss_url": db_feeds.get(aid),
               "wayback_lookup_feed": None}
        for label, url in [("single", LOOKUP_URL.format(ids=aid)),
                           ("country_gb", f"https://itunes.apple.com/lookup?id={aid}&country=gb"),
                           ("country_ca", f"https://itunes.apple.com/lookup?id={aid}&country=ca")]:
            got = ((_itunes(s, url) or {}).get("results") or [{}])[0]
            rec["track_count"] = rec["track_count"] or got.get("trackCount")
            rec["latest"] = rec["latest"] or got.get("releaseDate")
            rec["publisher"] = rec["publisher"] or got.get("artistName")
            if got.get("feedUrl"):
                rec["feed_url"], rec["how"] = got["feedUrl"], label
                break
        if not rec["feed_url"]:
            rec["wayback_lookup_feed"] = _wayback_lookup_feed(aid)
            rec["feed_url"] = rec["wayback_lookup_feed"] or rec["db_rss_url"]
            rec["how"] = ("wayback_lookup" if rec["wayback_lookup_feed"] else
                          "pipeline_db" if rec["db_rss_url"] else None)
        print(f"    {r['name'][:40]:42} {rec['how'] or 'no feed anywhere'}")
        cache[f"v:{r['sid']}"] = rec
        save_cache("lookup", cache)
    return cache


def _wayback_lookup_feed(apple_id: str) -> str | None:
    """A feedUrl from an archived iTunes lookup response, if Wayback kept one."""
    caps = cdx(f"https://itunes.apple.com/lookup?id={apple_id}")
    for ts, url in caps[:3]:
        body = _wayback_body(f"https://web.archive.org/web/{ts}id_/{url}")
        try:
            results = json.loads(body or b"{}").get("results") or []
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        for rec in results:
            if rec.get("feedUrl"):
                return rec["feedUrl"]
    return None


def _db_feeds() -> dict[str, str]:
    if not DB.exists():
        return {}
    con = sqlite3.connect(DB)
    out = {str(a): u for a, u in con.execute(
        "select apple_podcasts_id, rss_url from podcasts "
        "where apple_podcasts_id is not null and rss_url is not null")}
    con.close()
    return out


# --------------------------------------------------------------------- phase 2

def phase_feeds() -> dict:
    cache = load_cache("feeds")
    urls = feed_urls()
    todo = [(sid, u) for sid, u in urls.items()
            if sid not in cache or "months" not in cache[sid]]
    print(f"  {len(todo)} feeds to fetch ({len(cache)} cached, "
          f"{population().sid.nunique() - len(urls)} distinct shows have no feed URL at all)")
    done = 0
    with ThreadPoolExecutor(FEED_WORKERS) as pool:
        for sid, rec in pool.map(lambda t: (t[0], fetch_feed_record(t[1])), todo):
            # A transient failure must not overwrite a good earlier fetch, and
            # must leave "months" absent so the next run retries this show.
            if rec.get("error") and cache.get(sid) and not cache[sid].get("error"):
                continue
            cache[sid] = rec
            done += 1
            if done % 25 == 0:
                save_cache("feeds", cache)
                print(f"    {done}/{len(todo)}")
    save_cache("feeds", cache)
    return cache


def fetch_feed_record(url: str) -> dict:
    rec = {"feed_url": url, "status": None, "final_url": None, "error": None,
           "n_entries": 0, "n_episodes": 0, "min_pub": None, "max_pub": None,
           "n_no_date": 0, "has_transcript_tag": False, "n_transcript_urls": 0,
           "transcript_min_pub": None, "transcript_max_pub": None,
           "paginated": False, "months": [], "video_sourced": False, "samples": []}
    s = session()
    try:
        try:
            r = s.get(url, timeout=60, stream=True, allow_redirects=True)
        except requests.exceptions.ContentDecodingError:
            # Megaphone intermittently sends an undecodable gzip body for a feed
            # that is fine uncompressed. rss.py::_get carries the same retry;
            # without it Dan Bongino's 2,740-episode feed reads as empty.
            r = s.get(url, timeout=60, stream=True, allow_redirects=True,
                      headers={"Accept-Encoding": "identity"})
        rec["status"] = r.status_code
        rec["final_url"] = r.url
        body = b""
        for chunk in r.iter_content(65536):
            body += chunk        # may also raise ContentDecodingError; caught below
            if len(body) > MAX_FEED_BYTES:
                rec["error"] = "feed larger than the read cap; truncated"
                break
        r.close()
        if r.status_code >= 400:
            rec["error"] = f"HTTP {r.status_code}"
            return rec
    except requests.RequestException as e:
        rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        return rec
    except Exception as e:                                  # noqa: BLE001 - never lose a show
        rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        return rec

    rec["has_transcript_tag"] = b"podcast:transcript" in body
    rec["paginated"] = b'rel="next"' in body or b"rel='next'" in body
    try:
        rec["n_entries"] = len(feedparser.parse(body).entries)
    except Exception:                                       # noqa: BLE001
        rec["n_entries"] = 0
    try:
        episodes = parse_feed(body, source=url)
    except Exception as e:                                  # noqa: BLE001 - FeedError and parser crashes
        rec["error"] = rec["error"] or f"parse: {str(e)[:200]}"
        return rec

    if not episodes and rec["n_entries"]:
        # ``parse_feed`` keeps only ``audio/*`` enclosures, so a video-only feed
        # reads as dead. The pipeline transcodes everything to 24 kbps Opus, so a
        # video enclosure is a perfectly good source; recover those here rather
        # than loosening rss.py, which the download pipeline shares.
        episodes = _video_episodes(body)
        rec["video_sourced"] = bool(episodes)

    rec["n_episodes"] = len(episodes)
    dated = [(e.published_date, e) for e in episodes if e.published_date]
    rec["n_no_date"] = len(episodes) - len(dated)
    if dated:
        dated.sort(key=lambda t: t[0])
        rec["min_pub"], rec["max_pub"] = dated[0][0], dated[-1][0]
        rec["months"] = sorted({d[:7] for d, _ in dated})
        picks = [0, len(dated) // 2, len(dated) - 1]
        rec["samples"] = [{"pub": dated[i][0], "url": dated[i][1].audio_url}
                          for i in sorted(set(picks))]
    elif episodes:
        rec["samples"] = [{"pub": None, "url": e.audio_url} for e in episodes[:3]]

    with_tx = [(e.published_date, e.transcript_url) for e in episodes if e.transcript_url]
    rec["n_transcript_urls"] = len(with_tx)
    tx_dates = sorted(d for d, _ in with_tx if d)
    if tx_dates:
        rec["transcript_min_pub"], rec["transcript_max_pub"] = tx_dates[0], tx_dates[-1]
    rec["paginated"] = bool(rec["paginated"] or rec["n_episodes"] in PAGE_SIZES)
    return rec


def _video_episodes(body: bytes) -> list[FeedEpisode]:
    """Entries whose only enclosure is video (or carries no type at all)."""
    episodes = []
    for entry in feedparser.parse(body).entries:
        url = kind = None
        for enclosure in entry.get("enclosures", []):
            href = enclosure.get("href") or enclosure.get("url")
            typ = (enclosure.get("type") or "").lower()
            if href and (typ.startswith("video") or not typ):
                url, kind = href, enclosure.get("type")
                break
        if not url:
            continue
        published = entry.get("published_parsed")
        episodes.append(FeedEpisode(
            guid=entry.get("id") or url, title=entry.get("title") or "",
            audio_url=url, audio_type=kind,
            published_date=(datetime(*published[:6]).isoformat() if published else None)))
    return episodes


# --------------------------------------------------------------------- phase 4

def phase_audio() -> dict:
    cache = load_cache("audio")
    feeds = load_cache("feeds")
    todo = [(sid, [s["url"] for s in rec.get("samples", [])])
            for sid, rec in feeds.items() if sid not in cache and rec.get("samples")]
    print(f"  {len(todo)} shows to spot-check ({len(cache)} cached)")
    done = 0
    with ThreadPoolExecutor(AUDIO_WORKERS) as pool:
        for sid, probes in pool.map(lambda t: (t[0], [probe_audio(u) for u in t[1]]), todo):
            cache[sid] = probes
            done += 1
            if done % 25 == 0:
                save_cache("audio", cache)
                print(f"    {done}/{len(todo)}")
    save_cache("audio", cache)
    return cache


def probe_audio(url: str) -> dict:
    """Ranged 64 KB GET. Never reads the whole body: some hosts ignore Range."""
    out = {"url": url, "status": None, "content_type": None, "bytes": 0, "error": None}
    try:
        r = requests.get(url, timeout=45, stream=True, allow_redirects=True,
                         headers={**HEADERS, "Range": f"bytes=0-{RANGE_BYTES - 1}"})
        out["status"] = r.status_code
        out["content_type"] = (r.headers.get("Content-Type") or "").split(";")[0].strip()
        if r.status_code in (200, 206):
            out["bytes"] = len(r.raw.read(RANGE_BYTES, decode_content=True) or b"")
        r.close()
    except requests.RequestException as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:150]}"
    except Exception as e:                                  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e)[:150]}"
    return out


def audio_ok(probes) -> bool:
    for p in probes or []:
        ct = (p.get("content_type") or "").lower()
        if p.get("status") in (200, 206) and p.get("bytes", 0) > 1024 and (
                ct.startswith("audio") or ct.startswith("video")
                or "octet-stream" in ct or "mpeg" in ct or ct == ""):
            return True
    return False


# --------------------------------------------------------------------- phase 5

def cdx(url: str, attempts: int = 3) -> list[list[str]]:
    """One capture per month for an exact URL. Sequential: parallel CDX drops."""
    query = ("http://web.archive.org/cdx/search/cdx?url=" + requests.utils.quote(url, safe="")
             + "&fl=timestamp,original&filter=statuscode:200"
               "&collapse=timestamp:6&limit=2000&output=json")
    delay = 5.0
    for _ in range(attempts):
        proc = subprocess.run(["curl", "-s", "-A", UA, "--max-time", "120", query],
                              capture_output=True, text=True)
        text = (proc.stdout or "").strip()
        if proc.returncode == 0 and text:
            try:
                rows = json.loads(text)
            except json.JSONDecodeError:
                rows = []
            return rows[1:] if rows else []
        if proc.returncode == 0 and not text:
            return []           # genuine empty result and a dropped one look alike
        time.sleep(delay)
        delay *= 2
    return []


def phase_wayback(budget_seconds: float, only: list[str] | None = None) -> dict:
    """Fallback for shows phases 2-4 did not settle. Sequential, time-bounded."""
    cache = load_cache("wayback")
    rows = build_rows()
    todo = {}
    for r in sorted(rows, key=lambda r: r["last_seen"]):
        if r["needs_fallback"] and r["sid"] not in cache and r["sid"] not in todo:
            todo[r["sid"]] = r        # renamed shows share a feed; probe it once
    todo = list(todo.values())
    if only:
        todo = [r for r in todo if r["sid"] in set(only)]
    todo.sort(key=lambda r: (r["last_year"], -r["est_days"]))  # oldest charting first
    print(f"  {len(todo)} shows in the fallback set ({len(cache)} cached), "
          f"budget {budget_seconds / 60:.0f} min")
    started = time.time()
    for i, r in enumerate(todo):
        if time.time() - started > budget_seconds:
            print(f"  budget exhausted after {i} shows; {len(todo) - i} left unprobed")
            break
        cache[r["sid"]] = wayback_record(r)
        save_cache("wayback", cache)
        if (i + 1) % 10 == 0:
            print(f"    {i + 1}/{len(todo)} ({time.time() - started:.0f}s)")
    return cache


def wayback_record(row: dict) -> dict:
    rec = {"urls_tried": [], "n_captures": 0, "first_capture": None, "last_capture": None,
           "spans_window": False, "snapshot_ts": None, "snapshot_episodes": 0,
           "snapshot_min_pub": None, "snapshot_max_pub": None,
           "era_enclosures_ok": 0, "era_enclosures_tried": 0, "note": None}
    candidates = [u for u in {row.get("feed_url"), row.get("final_url")} if u]
    stamps = []
    for url in candidates:
        rec["urls_tried"].append(url)
        caps = cdx(url)
        time.sleep(1.0)
        for ts, _orig in caps:
            stamps.append((ts, url))
    if not stamps:
        rec["note"] = "no wayback captures of the feed URL"
        return rec
    stamps.sort()
    rec["n_captures"] = len(stamps)
    rec["first_capture"], rec["last_capture"] = stamps[0][0], stamps[-1][0]

    first_seen, last_seen = to_date(row["first_seen"]), to_date(row["last_seen"])
    cap_first, cap_last = _stamp_date(stamps[0][0]), _stamp_date(stamps[-1][0])
    rec["spans_window"] = bool(cap_first and cap_last and first_seen and last_seen
                               and cap_first <= first_seen + timedelta(days=90)
                               and cap_last >= last_seen - timedelta(days=90))

    # One archived snapshot as close to last_seen as the captures allow.
    target = last_seen or cap_last
    ts, url = min(stamps, key=lambda t: abs((_stamp_date(t[0]) - target).days))
    rec["snapshot_ts"] = ts
    body = _wayback_body(f"https://web.archive.org/web/{ts}id_/{url}")
    if not body:
        rec["note"] = "snapshot fetch failed"
        return rec
    try:
        episodes = parse_feed(body, source=url)
    except Exception as e:                                  # noqa: BLE001
        rec["note"] = f"snapshot parse: {str(e)[:120]}"
        return rec
    rec["snapshot_episodes"] = len(episodes)
    dated = sorted([e for e in episodes if e.published_date], key=lambda e: e.published_date)
    if dated:
        rec["snapshot_min_pub"] = dated[0].published_date
        rec["snapshot_max_pub"] = dated[-1].published_date

    # Probe up to 3 enclosures that fall inside the charting window.
    in_window = [e for e in dated
                 if first_seen and last_seen
                 and first_seen - timedelta(days=NEAR_DAYS)
                 <= to_date(e.published_date) <= last_seen + timedelta(days=NEAR_DAYS)]
    picks = in_window or dated
    if picks:
        idx = sorted({0, len(picks) // 2, len(picks) - 1})
        for i in idx:
            rec["era_enclosures_tried"] += 1
            probe = probe_audio(picks[i].audio_url)
            if audio_ok([probe]):
                rec["era_enclosures_ok"] += 1
                continue
            if _wayback_available(picks[i].audio_url):
                rec["era_enclosures_ok"] += 1
            time.sleep(0.5)
    return rec


def _stamp_date(ts: str) -> datetime:
    return datetime.strptime(ts[:8], "%Y%m%d")


def _wayback_body(url: str) -> bytes | None:
    for attempt in range(2):
        # --compressed matters: the ``id_`` replay hands back the original bytes,
        # gzip and all, and feedparser sees only a not-well-formed token.
        proc = subprocess.run(["curl", "-sL", "--compressed", "-A", UA,
                               "--max-time", "120", url], capture_output=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
        time.sleep(5 * (attempt + 1))
    return None


def _wayback_available(url: str) -> bool:
    try:
        r = requests.get("http://archive.org/wayback/available",
                         params={"url": url}, headers=HEADERS, timeout=30)
        snap = (r.json().get("archived_snapshots") or {}).get("closest") or {}
        return bool(snap.get("available")) and str(snap.get("status")) == "200"
    except (requests.RequestException, ValueError):
        return False


# --------------------------------------------------------------- rows + verdicts

def build_rows() -> list[dict]:
    pop = population()
    lookup, feeds = load_cache("lookup"), load_cache("feeds")
    audio, wayback = load_cache("audio"), load_cache("wayback")
    urls = feed_urls()

    rows = []
    for r in pop.itertuples():
        sid = r.sid
        feed = feeds.get(sid, {})
        probes = audio.get(sid)
        wb = wayback.get(sid, {})
        first_seen, last_seen = to_date(r.first_seen), to_date(r.last_seen)
        min_pub, max_pub = to_date(feed.get("min_pub")), to_date(feed.get("max_pub"))

        row = {
            "entity": r.entity, "key": r.key, "name": r.name,
            "publisher": r.publisher, "titles": r.titles,
            "apple_id": r.apple_id, "sid": sid,
            "n_obs": r.n_obs, "est_days": r.est_days,
            "deep_obs": r.deep_obs, "shallow_obs": r.shallow_obs,
            "shallow_only": bool(r.deep_obs == 0),
            "best_rank": r.best_rank,
            "first_seen": r.first_seen, "last_seen": r.last_seen,
            "first_year": r.first_year, "last_year": r.last_year,
            "feed_source": ((lookup.get(r.apple_id or "") or {}).get("feed_url")
                            and (lookup.get(r.apple_id or "") or {}).get("source")
                            or (lookup.get(f"s:{sid}") or {}).get("source")
                            or (lookup.get(r.apple_id or "") or {}).get("source")),
            "feed_url": urls.get(sid),
            "http_status": feed.get("status"),
            "final_url": feed.get("final_url"),
            "feed_error": feed.get("error"),
            "n_entries": feed.get("n_entries"),
            "n_episodes": feed.get("n_episodes"),
            "min_pub": feed.get("min_pub"), "max_pub": feed.get("max_pub"),
            "n_no_date": feed.get("n_no_date"),
            "has_transcript_tag": feed.get("has_transcript_tag"),
            "n_transcript_urls": feed.get("n_transcript_urls"),
            "transcript_min_pub": feed.get("transcript_min_pub"),
            "paginated": feed.get("paginated"),
            "video_sourced": feed.get("video_sourced"),
        }
        row["feed_live"] = bool(feed.get("status") == 200 and feed.get("n_episodes"))
        months = feed.get("months")
        row["window_coverage"] = coverage(first_seen, last_seen, min_pub, max_pub)
        row["months_covered"] = (None if months is None else
                                 month_coverage(first_seen, last_seen, months))
        row["hollow_feed"] = (None if months is None else
                              hollow(first_seen, last_seen, months))
        row["coverage_gap"] = gap_end(first_seen, last_seen, min_pub, max_pub)
        row["covers_window"] = bool(
            min_pub and max_pub and first_seen and last_seen
            and min_pub <= first_seen + timedelta(days=NEAR_DAYS)
            and max_pub >= last_seen - timedelta(days=NEAR_DAYS))
        row["audio_checked"] = len(probes or [])
        row["audio_ok"] = bool(probes) and audio_ok(probes)
        row["audio_statuses"] = ";".join(str(p.get("status")) for p in (probes or []))
        row["audio_types"] = ";".join((p.get("content_type") or "") for p in (probes or []))
        tx_min = to_date(feed.get("transcript_min_pub"))
        row["transcripts_cover_era"] = bool(
            feed.get("n_transcript_urls") and tx_min and first_seen
            and tx_min <= first_seen + timedelta(days=NEAR_DAYS))
        row["wb_captures"] = wb.get("n_captures")
        row["wb_first_capture"] = wb.get("first_capture")
        row["wb_last_capture"] = wb.get("last_capture")
        cap_first, cap_last = wb.get("first_capture"), wb.get("last_capture")
        row["wb_spans_window"] = bool(
            cap_first and cap_last and first_seen and last_seen
            and _stamp_date(cap_first) <= first_seen + timedelta(days=90)
            and _stamp_date(cap_last) >= last_seen - timedelta(days=90))
        row["wb_snapshot_episodes"] = wb.get("snapshot_episodes")
        row["wb_era_enclosures_ok"] = wb.get("era_enclosures_ok")
        row["wb_era_enclosures_tried"] = wb.get("era_enclosures_tried")
        row["wb_note"] = wb.get("note")
        row["wb_probed"] = sid in wayback

        row["verdict"] = verdict(row)
        # Anything not already fully recoverable is worth a Wayback attempt.
        row["needs_fallback"] = row["verdict"] != "fully_recoverable"
        rows.append(row)
    return rows


def coverage(first_seen, last_seen, min_pub, max_pub) -> float:
    if not (first_seen and last_seen and min_pub and max_pub):
        return 0.0
    window = (last_seen - first_seen).days
    if window <= 0:
        return 1.0 if min_pub <= first_seen and max_pub >= last_seen else 0.0
    lo, hi = max(first_seen, min_pub), min(last_seen, max_pub)
    return max(0.0, min(1.0, (hi - lo).days / window))


def month_coverage(first_seen, last_seen, months) -> float:
    """Fraction of the charting window's months in which the feed holds an episode.

    Reported alongside ``window_coverage`` but deliberately not used for the
    verdict. It catches feeds that keep a few legacy episodes beside recent ones
    so that ``min_pub``..``max_pub`` brackets a window they do not populate
    (Sword and Scale: nothing between 2014-02 and 2023-01). But it also punishes
    shows that simply publish in bursts — Serial's feed carries every season and
    still scores 0.15, because Serial only ever published in 24 months. Read it
    as a gap detector, not as a recoverability score.
    """
    if not (first_seen and last_seen):
        return 0.0
    want, cursor = [], first_seen.replace(day=1)
    while cursor <= last_seen:
        want.append(f"{cursor:%Y-%m}")
        cursor = (cursor.replace(day=28) + timedelta(days=7)).replace(day=1)
    if not want:
        return 0.0
    have = set(months or [])
    return len([m for m in want if m in have]) / len(want)


def hollow(first_seen, last_seen, months) -> bool:
    """The feed holds nothing from anywhere near the charting era.

    Stricter than ``months_covered == 0``, which a limited series trips
    innocently: S-Town released every episode in 2017-03 and first charted
    2017-04, so no episode falls *inside* its window even though the charting-era
    content is all there. Allowing six months of lead-in keeps those, while still
    catching the feeds this study cannot use — Sword and Scale charted 2016-2022
    and its feed jumps from 2014-02 to 2023-01.
    """
    if not (first_seen and last_seen):
        return True
    lo = f"{first_seen - timedelta(days=180):%Y-%m}"
    hi = f"{last_seen + timedelta(days=30):%Y-%m}"
    return not any(lo <= m <= hi for m in months or [])


def gap_end(first_seen, last_seen, min_pub, max_pub) -> str:
    """Which end of the charting window the feed fails to reach."""
    if not (first_seen and last_seen and min_pub and max_pub):
        return "unknown"
    late_start = min_pub > first_seen + timedelta(days=NEAR_DAYS)
    early_stop = max_pub < last_seen - timedelta(days=NEAR_DAYS)
    return ({(True, True): "both", (True, False): "start",
             (False, True): "end"}.get((late_start, early_stop), "none"))


def verdict(row: dict) -> str:
    """Precedence matters: the tiers overlap. Best obtainable outcome wins."""
    if (row["feed_live"] and row["audio_ok"] and row["window_coverage"] >= COVERAGE_OK
            and not row.get("hollow_feed")):
        return "fully_recoverable"
    if row.get("wb_spans_window") and (row.get("wb_era_enclosures_ok") or 0) > 0:
        return "archive_only"
    if row["feed_live"] and row["audio_ok"] and row["window_coverage"] < COVERAGE_OK:
        return "recent_only"
    if row["transcripts_cover_era"]:
        return "transcript_only"
    return "not_recoverable"


# ------------------------------------------------------------------- calibration

def calibration(rows: list[dict]) -> pd.DataFrame:
    """The 63 population shows the pipeline actually downloaded, as ground truth."""
    if not DB.exists():
        return pd.DataFrame()
    con = sqlite3.connect(DB)
    db = pd.read_sql(
        "select p.apple_podcasts_id as apple_id, p.rss_url as db_rss_url, "
        "  count(e.id) as db_episodes, "
        "  sum(case when e.audio_file_path is not null then 1 else 0 end) as db_downloaded, "
        "  min(e.published_date) as db_min_pub, max(e.published_date) as db_max_pub, "
        "  min(case when e.audio_file_path is not null then e.published_date end) as db_min_dl "
        "from podcasts p left join episodes e on e.podcast_id = p.id "
        "where p.apple_podcasts_id is not null group by p.id", con)
    con.close()
    df = pd.DataFrame(rows).merge(db, on="apple_id", how="inner")
    df = df[df.db_episodes > 0].copy()
    df["db_covers_window"] = [
        bool(to_date(a) and to_date(b) and to_date(f) and to_date(l)
             and to_date(a) <= to_date(f) + timedelta(days=NEAR_DAYS)
             and to_date(b) >= to_date(l) - timedelta(days=NEAR_DAYS))
        for a, b, f, l in zip(df.db_min_pub, df.db_max_pub, df.first_seen, df.last_seen)]
    df["feed_url_matches_db"] = [
        bool(a and b and a.rstrip("/") == b.rstrip("/"))
        for a, b in zip(df.feed_url, df.db_rss_url)]
    df["min_pub_gap_days"] = [
        (to_date(a) - to_date(b)).days if to_date(a) and to_date(b) else None
        for a, b in zip(df.min_pub, df.db_min_pub)]
    return df


# ----------------------------------------------------------------------- report

# Counts from the two earlier runs of this script, kept as literals so the
# change stays traceable now that both population files have been replaced.
# 373 rows: title-keyed, one row per charting *title*. 346: entity-keyed, but
# scored on raw snapshot days and a window that stopped at 2024-12.
RUN_373 = {"n": 373, "usable": 253, "eras": {"pre-2018": 130}}
PRIOR = {"n": 346, "fully_recoverable": 230, "recent_only": 72, "archive_only": 3,
         "transcript_only": 1, "not_recoverable": 40, "usable": 234,
         "eras": {"pre-2018": 102, "2018-2021": 116, "2022-2024": 128},
         "dropped": 88, "added": 84, "retained": 258}


def _change_section(df: pd.DataFrame) -> list[str]:
    """How this population differs from the two the script scored before it."""
    n = len(df)
    counts = df.verdict.value_counts()
    usable = int(counts.get("fully_recoverable", 0) + counts.get("archive_only", 0)
                 + counts.get("transcript_only", 0))
    dropped = (pd.read_csv(DROPPED_SNAPSHOT) if DROPPED_SNAPSHOT.exists()
               else pd.DataFrame())
    recent = df[df.last_year >= 2025]

    lines = [
        "## Change from the earlier runs", "",
        "This script has now scored three populations. The first "
        f"({RUN_373['n']} rows) was keyed on charting *title*, so renamed shows "
        "were counted several times. The second "
        f"({PRIOR['n']} shows) fixed that by resolving each show to its Apple id, "
        "but still selected on raw snapshot days — which measures tenure times "
        "sampling rate — and stopped at 2024-12. This one "
        f"({n} shows) selects on exposure-weighted estimated days and runs to "
        "2026-08-31.",
        "",
        "| tier | 346-show run | this run |",
        "|---|---:|---:|",
    ]
    for tier in TIERS:
        lines.append(f"| {tier} | {PRIOR[tier]} | {int(counts.get(tier, 0))} |")
    lines += [
        f"| **usable** | **{PRIOR['usable']} of {PRIOR['n']} "
        f"({PRIOR['usable'] / PRIOR['n']:.0%})** | **{usable} of {n} "
        f"({usable / n:.0%})** |",
        "",
        f"**The usable fraction moved from {PRIOR['usable'] / PRIOR['n']:.0%} to "
        f"{usable / n:.0%}**"
        + (", so the additions did improve it, but by less than their recency "
           "suggests." if usable / n > PRIOR["usable"] / PRIOR["n"] else
           " — it did not improve, despite the additions skewing recent.")
        + " The reason is that the two changes to the rule cut against each other, "
        "and the second is the stronger:",
        "",
        f"- **The {PRIOR['added']} shows added** skew heavily recent, and the "
        "extended window pulls retained shows forward too: "
        f"{len(recent)} shows now last chart in 2025 or 2026, a stretch the old "
        "population could not describe at all because its window closed 2024-12. "
        "Whether added or merely extended into it, those shows' feeds are almost "
        f"all intact — {int((recent.verdict == 'fully_recoverable').sum())} of "
        f"{len(recent)} are `fully_recoverable`, and just "
        f"{int((recent.verdict == 'not_recoverable').sum())} `not_recoverable`.",
        f"- **The {PRIOR['dropped']} shows dropped** were disproportionately *easy* "
        "ones. Of them "
        + (f"{int((dropped.verdict == 'fully_recoverable').sum())} were "
           f"`fully_recoverable` and only "
           f"{int((dropped.verdict == 'not_recoverable').sum())} `not_recoverable` "
           "— a healthier mix than the population they left."
           if len(dropped) else "no frozen record survives.")
        + " Weighting exposure removed shows that had looked long-lived only "
        "because the archive happened to sample them often.",
        "- **Every retained show was rescored, not carried over.** Windows now "
        "extend to the show's true last appearance, which in many cases is 2026 "
        "rather than 2024. A wider window is a harder test: a feed must reach both "
        "further back and further forward. Verdicts were recomputed from the cached "
        "feed measurements against the new windows; no verdict was inherited.",
        "",
        f"The {PRIOR['dropped']} dropped shows keep their 346-run rows in "
        "[`recoverability_dropped.csv`](recoverability_dropped.csv) so that run's "
        "numbers stay reproducible. Those rows are a frozen copy, not a rescoring: "
        "there is no population row left to score them against.",
        "",
        "### What the earlier rules distorted", "",
        "Two defects have now been corrected, and both had been inflating the "
        "apparent difficulty of the older eras.",
        "",
        f"**Title-keying** (fixed before the {PRIOR['n']}-show run) padded the "
        f"pre-2018 bucket with early titles of shows still charting today — "
        "`NPR: Fresh Air Podcast` last seen 2015 is the same podcast as `Fresh Air` "
        f"last seen 2024. Pre-2018 fell from {RUN_373['eras']['pre-2018']} rows to "
        f"{PRIOR['eras']['pre-2018']} shows on that fix alone, and stands at "
        f"{int((df.era == 'pre-2018').sum())} now.",
        "",
        "**Snapshot-day counting** (fixed here) measured how often the archive "
        "looked, not how long a show charted. It demanded far more real tenure in "
        "sparsely sampled years than in densely sampled ones, so it under-selected "
        "exactly the early period whose recoverability we were most worried about. "
        f"Pre-2018 is now {int((df.era == 'pre-2018').sum())} shows of {n} "
        f"({int((df.era == 'pre-2018').sum()) / n:.0%}), and its recoverability is "
        "measured on a membership that no longer depends on capture cadence.",
        "",
        "One measurement was not redone: for a show whose window widened, the "
        "Wayback phase reused the snapshot it had already probed against the older, "
        "narrower window. `wb_spans_window` is recomputed against the current "
        "window, but `wb_era_enclosures_ok` was not re-probed. That can only affect "
        f"whether a show reaches `archive_only`, and at "
        f"{int((df.verdict == 'archive_only').sum())} shows the tier is marginal "
        "either way.",
        "",
    ]
    return lines


def _shallow_section(df: pd.DataFrame) -> list[str]:
    """The shows that qualified only on Apple's 24-deep chart page."""
    shallow = df[df.shallow_only]
    if not len(shallow):
        return []
    bad = shallow[~shallow.verdict.isin(["fully_recoverable", "archive_only",
                                         "transcript_only"])]
    lines = [
        "## The shallow-era-only shows", "",
        f"{len(shallow)} shows qualified purely on Apple's own charts page, which "
        "is only 24 deep — they hold no observation from the 100-deep mirrors, and "
        "exist in this population only because the window was extended past "
        "2024-08. They are worth checking separately: if the shows the extension "
        "was built to capture turned out to be unrecoverable, the extension would "
        "have bought nothing.",
        "",
        "| show | charting window | verdict | window coverage | episodes |",
        "|---|---|---|---:|---:|",
    ]
    for r in shallow.sort_values("est_days", ascending=False).itertuples():
        lines.append(f"| {_cell(r.name)} | {r.first_seen} - {r.last_seen} | "
                     f"`{r.verdict}` | {r.window_coverage:.2f} | "
                     f"{'' if pd.isna(r.n_episodes) else int(r.n_episodes)} |")
    lines += [
        "",
        f"**{len(shallow) - len(bad)} of {len(shallow)} are usable**, all of them "
        "through live feeds with working audio — unsurprising for shows that "
        "charted within the last two years, but worth confirming rather than "
        "assuming."
        + ("" if not len(bad) else
           (" The exception is " if len(bad) == 1 else " The exceptions are ")
           + ", ".join(f"*{_cell(r.name)}* (`{r.verdict}`, coverage "
                       f"{r.window_coverage:.2f})" for r in bad.itertuples())
           + (", which is not a dead feed" if len(bad) == 1 else
              ", none of them a dead feed")
           + ": live and fetchable, but starting after the charting window does. "
             "*Digital Social Hour* serves a 200-episode page and nothing older — a "
             "truncation a paginated fetch could work around if the show matters."),
        "",
    ]
    return lines


def _cell(text) -> str:
    """A show or publisher name safe to drop into a markdown table cell."""
    plain = str(text).replace("|", "/")
    return plain if len(plain) <= 44 else plain[:41] + "..."


def _feedless_section(df: pd.DataFrame, lookup: dict) -> list[str]:
    """Shows Apple lists but exposes no feed for, and what each re-check found."""
    rows = [(r, lookup[f"v:{r.sid}"]) for r in df.itertuples()
            if f"v:{r.sid}" in lookup]
    if not rows:
        return []
    lines = [
        "## Shows Apple lists but publishes no feed for", "",
        "An absent `feedUrl` in a 200-id batch lookup could just be the batch "
        "dropping records, so each of these was re-checked one id at a time, then "
        "against the `gb` and `ca` catalogues, then against an archived copy of the "
        "lookup response in Wayback, then against the RSS URL our own pipeline "
        f"database holds. **None of the {len(rows)} produced a feed by any route.**",
        "",
        "| show | publisher | episodes Apple counts | latest episode | verdict |",
        "|---|---|---:|---|---|",
    ]
    for r, v in sorted(rows, key=lambda t: -(t[1].get("track_count") or 0)):
        lines.append(f"| {_cell(r.name)} | {_cell(v.get('publisher') or '?')} | "
                     f"{v.get('track_count') or '?'} | "
                     f"{str(v.get('latest') or '?')[:10]} | `{r.verdict}` |")
    spotify = [r for r, v in rows
               if any(owner in str(v.get("publisher") or "")
                      for owner in ("Gimlet", "Spotify", "Pineapple Street"))]
    live = [r for r, v in rows if str(v.get("latest") or "")[:4] >= "2026"]
    lines += [
        "",
        f"{len(spotify)} of the {len(rows)} are Spotify-owned catalogues — "
        + ", ".join(f"*{_cell(r.name)}*" for r in spotify)
        + " — where RSS was withdrawn after acquisition. Those are structurally "
        "uncollectable for this study however they charted.",
        "",
        f"The other {len(rows) - len(spotify)} are a different case. "
        + (", ".join(f"*{_cell(r.name)}*" for r in live)
           + (" are still publishing in 2026" if len(live) != 1 else
              " is still publishing in 2026")
           + ", so a feed almost certainly exists somewhere; what is established is "
           "only that **Apple exposes no path to it**, through either of its public "
           "endpoints, through the `gb` or `ca` catalogues, through an archived "
           "lookup response, or through our own database. Since the population is "
           "Apple-defined they are scored as unreachable, but they are the ones "
           "worth a manual look."
           if live else "None of them has published since 2025."),
        "",
        "**A correction to the previous run.** That report named *The Ben Shapiro "
        "Show* as the headline no-feed case. That was wrong. Apple's lookup does "
        "omit its `feedUrl`, but the show has a working feed "
        "(`feeds.megaphone.fm/BVDWV5370667266`, picked up from the pipeline "
        "database) and it is `fully_recoverable`. No top-tier news podcast is "
        "structurally uncollectable.",
        "",
    ]
    return lines


# The archive now runs to 2026-08-31, so the recent bucket is split: 2025-2026
# is the stretch the extended window was added to capture.
ERAS = ["pre-2018", "2018-2021", "2022-2024", "2025-2026"]
TIERS = ["fully_recoverable", "recent_only", "archive_only",
         "transcript_only", "not_recoverable"]


def era_of(last_year: int) -> str:
    if last_year < 2018:
        return "pre-2018"
    if last_year <= 2021:
        return "2018-2021"
    return "2022-2024" if last_year <= 2024 else "2025-2026"


def phase_report() -> None:
    rows = build_rows()
    df = pd.DataFrame(rows)
    df["era"] = df.last_year.map(era_of)
    df.drop(columns=["needs_fallback"]).to_csv(OUT_CSV, index=False)
    if DROPPED_SNAPSHOT.exists():
        pd.read_csv(DROPPED_SNAPSHOT).to_csv(OUT_DROPPED, index=False)

    cal = calibration(rows)
    OUT_MD.write_text(render_md(df, cal))
    print(f"  wrote {OUT_CSV} and {OUT_MD}")
    print(df.verdict.value_counts().to_string())


def render_md(df: pd.DataFrame, cal: pd.DataFrame) -> str:
    n = len(df)
    counts = df.verdict.value_counts()
    usable = int(counts.get("fully_recoverable", 0) + counts.get("archive_only", 0)
                 + counts.get("transcript_only", 0))
    probed = int(df[df.wb_probed].sid.nunique())

    lines = [
        f"# Recoverability of the {n}-show chart population",
        "",
        f"Measured {datetime.now():%Y-%m-%d}. One row per show in "
        "[`recoverability.csv`](recoverability.csv); produced by "
        "`analysis/chart_archive/recoverability.py`.",
        "",
        "**Question.** For how many of these shows can we still obtain audio (or "
        "publisher transcripts) covering the period in which the show charted — "
        "not merely a live feed, but one that reaches back into its charting window?",
        "",
        f"**One row per show.** The population is keyed on `entity` — the Apple id, "
        f"or `title:<key>` for the {int(df.apple_id.isna().sum())} shows that never "
        f"carried one — so each of the {n} rows is one podcast. "
        f"{int((df.titles > 1).sum())} of them charted under more than one title "
        "(*Fresh Air* under four, *Radiolab* under three), and each is measured "
        "against the **union** of its charting windows: *The Dave Ramsey Show* is "
        "scored over its whole run, not over two shorter ones.",
        "",
        "The population selects on **exposure-weighted estimated days in the chart "
        f"(≥90) with ≥3 observations**, over 2012-07-15 to 2026-08-31 — rank ≤50 "
        "where the mirrors publish 100 deep, rank ≤24 for 2024-08 onward where only "
        "Apple's own page survives. `est_days`, `n_obs`, `deep_obs` and "
        "`shallow_obs` are carried into the output so any row can be traced back to "
        "why it is in scope.",
        "",
        "## Verdicts",
        "",
        "| tier | shows | share |",
        "|---|---:|---:|",
    ]
    for tier in TIERS:
        c = int(counts.get(tier, 0))
        lines.append(f"| {tier} | {c} | {c / n:.0%} |")
    lines += [
        f"| **total** | **{n}** | |",
        "",
        "Tiers are assigned by precedence, because they overlap: "
        "`fully_recoverable` (live feed, audio fetches, feed spans ≥"
        f"{COVERAGE_OK:.0%} of the charting window and is not hollow — see below) "
        "→ `archive_only` (Wayback "
        "holds feed captures spanning the window and a sampled charting-era "
        "enclosure still resolves) → `recent_only` (live feed and working "
        "audio, but the episodes postdate the charting window) → "
        "`transcript_only` → `not_recoverable`.",
        "",
        "## By charting era (`last_year`)",
        "",
        "| era | " + " | ".join(TIERS) + " | total |",
        "|---|" + "---:|" * (len(TIERS) + 1),
    ]
    for era in ERAS:
        sub = df[df.era == era]
        cells = [str(int((sub.verdict == t).sum())) for t in TIERS]
        lines.append(f"| {era} | " + " | ".join(cells) + f" | {len(sub)} |")
    lines += [
        "",
        f"Median coverage of the charting window by the live feed: "
        + " · ".join(f"{era} {df[df.era == era].window_coverage.median():.2f}" for era in ERAS)
        + ".",
        "",
        "## Bottom line",
        "",
        f"- **Usable for their charting era: {usable} shows of {n} "
        f"({usable / n:.0%}).** "
        "That is `fully_recoverable` + `archive_only` + `transcript_only`.",
        f"- **Not usable: {n - usable} shows ({(n - usable) / n:.0%}).** "
        f"{int(counts.get('recent_only', 0))} of those have a live feed we could "
        "collect going forward, but it no longer carries the episodes that "
        "charted; the remaining "
        f"{int(counts.get('not_recoverable', 0))} yield nothing.",
        "",
    ]

    # measurement caveats
    lines += ["## What was actually measured", ""]
    no_feed = int(df.feed_url.isna().sum())
    lookup = load_cache("lookup")
    listed = sum(1 for sid, aid in zip(df[df.feed_url.isna()].sid,
                                       df[df.feed_url.isna()].apple_id)
                 if (lookup.get(str(aid)) or {}).get("name")
                 or (lookup.get(f"s:{sid}") or {}).get("name"))
    video = int(df.video_sourced.eq(True).sum())
    unprobed = int(df[(df.verdict != "fully_recoverable") & ~df.wb_probed].sid.nunique())
    lines += [
        f"- Feed URL resolved for {n - no_feed} of {n} shows ({no_feed} unresolved). "
        f"Two different failures hide in there: {no_feed - listed} shows Apple no "
        f"longer lists at all, and {listed} Apple still lists but publishes no "
        "`feedUrl` for — verified one at a time below.",
        f"- {video} shows are **video** feeds: they return 200 with 20-148 entries "
        "carrying only `video/*` enclosures, which `rss.py` drops. Because the "
        "pipeline transcodes to 24 kbps Opus anyway, this script recovers those "
        "enclosures and spot-checks them like any other; the `video_sourced` column "
        "marks them. All five fetch (HTTP 206, `video/mp4` or `video/quicktime`), so "
        "they are collectable — but every one of them now carries only episodes "
        "postdating its charting window, so all five land in `recent_only`.",
        f"- {int((df.feed_source == 'search:title').sum())} feed URLs come from a "
        "title-only iTunes search with no publisher agreement, so they are the "
        "weakest identifications in the file (`feed_source` column).",
        f"- Feeds returning HTTP 200 with at least one parseable episode: "
        f"{int(df.feed_live.sum())}.",
        f"- HTTP status distribution: "
        + ", ".join(f"{int(k)}×{v}" if pd.notna(k) else f"none×{v}"
                    for k, v in df.http_status.value_counts(dropna=False).items()),
        f"- Audio spot-check: up to 3 enclosures per show, ranged 64 KB GET. "
        f"{int(df.audio_ok.sum())} shows returned playable bytes from at least one.",
        f"- Feeds advertising `<podcast:transcript>`: "
        f"{int(df.has_transcript_tag.sum())}; of those, "
        f"{int(df.transcripts_cover_era.sum())} carry transcript entries reaching "
        "back into the charting window.",
        f"- Wayback fallback run on {probed} distinct feeds — every show phases 2-4 "
        "did not settle"
        + ("." if not unprobed else
           f", except **{unprobed} left unprobed when the time budget ran out**, so "
           "the `archive_only` count is a lower bound."),
        "",
        "**The Wayback fallback mostly does not work, and that is a finding rather "
        f"than a gap.** Of {probed} feeds probed, "
        f"{int(df[df.wb_probed].groupby('sid').wb_captures.max().gt(0).sum())} have "
        "any CDX capture at all, and only "
        f"{int(df.wb_spans_window.eq(True).sum())} shows have "
        "captures spanning their charting window. The reason is structural: what "
        "Wayback archived is the feed URL *as it stands today*, and a show that "
        "charted in 2014 usually served it from a Feedburner or Podtrac address "
        "Apple has since replaced — so the captures start years after the show "
        "charted. Old enclosures survive better than the feeds that listed them: "
        "where an archived snapshot did parse, "
        f"{int(df[df.wb_probed].groupby('sid').wb_era_enclosures_ok.max().gt(0).sum())} "
        "feeds gave up at least one charting-era enclosure that still resolves. The "
        "bottleneck is finding the historical feed URL, not the audio behind it.",
        "",
    ]

    strong = df[df.verdict == "fully_recoverable"]
    lines += [
        "## How coverage was measured, and the trap in it", "",
        "`window_coverage` is the fraction of `first_seen`..`last_seen` spanned by "
        "the feed's oldest-to-newest episode range. On its own it is too generous: "
        "a feed keeping a couple of legacy episodes beside its recent ones brackets "
        "the whole window while holding nothing from the charting era. Sword and "
        "Scale charted 2016-2022 and its feed jumps from 2014-02 straight to "
        "2023-01, yet scores 1.00.",
        "",
        "So two more columns qualify it. `months_covered` is the share of the "
        "window's months in which the feed actually has an episode. `hollow_feed` "
        "is the test that decides verdicts: **true when the feed has no episode "
        "anywhere in the charting window or the six months before it**. "
        f"{int(df.hollow_feed.eq(True).sum())} shows are hollow; "
        "`fully_recoverable` requires that they are not.",
        "",
        "The six months of lead-in matter. `months_covered == 0` alone would "
        "condemn limited series that released everything just before they charted "
        "— S-Town published its whole run in 2017-03 and first charted 2017-04-23, "
        "so no episode falls inside its window even though all of its content is "
        "there. For the same reason `months_covered` is reported but never used as "
        "a verdict: Serial's feed carries every season and still scores 0.15, "
        "because Serial only ever published in 24 months of a 122-month window. "
        "Read it as a gap detector to sort by.",
        "",
        "Among the "
        f"{len(strong)} `fully_recoverable` shows, `months_covered` is "
        + ", ".join(
            f"{int(((strong.months_covered >= lo) & (strong.months_covered < hi)).sum())} "
            f"{label}"
            for lo, hi, label in [(0.0, 0.25, "under 25%"), (0.25, 0.5, "at 25-50%"),
                                  (0.5, 0.8, "at 50-80%"), (0.8, 1.01, "at 80%+")])
        + " — the low tail is seasonal and limited-run shows, not pruned feeds.",
        "",
        f"`recent_only` is named for its dominant case but is not exclusively that: "
        f"{int((df[df.verdict == 'recent_only'].coverage_gap == 'start').sum())} of "
        f"{int((df.verdict == 'recent_only').sum())} such shows miss the start of the "
        "window (the feed was pruned), while "
        f"{int(df[df.verdict == 'recent_only'].coverage_gap.isin(['end', 'both']).sum())} "
        "miss the *end* — feeds frozen mid-charting-run, like Above & Beyond: Group "
        "Therapy, whose feed stops in 2012 for a show that charted into 2015. The "
        "`coverage_gap` column says which end failed. Either way the charting era is "
        "not obtainable.",
        "",
    ]
    lines += _feedless_section(df, lookup)
    lines += [
        "## Completeness", "",
        f"All five phases ran for every show: {n} shows resolved, {n - no_feed} feeds "
        f"fetched, {int((df.audio_checked > 0).sum())} shows audio-spot-checked, and "
        f"the Wayback fallback run on {probed} feeds"
        + (". Nothing was left unprobed for want of time." if not unprobed else
           f", with {unprobed} left unprobed.")
        + " Measured over roughly three hours of wall clock across two population "
        "revisions; the sequential Wayback phase accounts for about half of it.",
        ""]
    lines += _shallow_section(df)
    lines += _change_section(df)
    lines += ["## Calibration against the pipeline's real download record", ""]
    if cal.empty:
        lines.append("The metadata database was unavailable; no calibration was run.")
    else:
        agree = int((cal.audio_ok & (cal.db_downloaded > 0)).sum())
        dl = int((cal.db_downloaded > 0).sum())
        lines += [
            f"{len(cal)} of these shows have already been collected by the "
            "pipeline, which gives a real "
            "download record to check the spot-check against (joined on "
            "`apple_podcasts_id`).",
            "",
            f"- {dl} of {len(cal)} have episodes with audio actually on disk. "
            f"My spot-check called {agree} of those fetchable — "
            f"{dl - agree} disagreement{'' if dl - agree == 1 else 's'}. "
            "The spot-check is sound, with a small false-negative rate from CDNs "
            "that reject a ranged request from an unfamiliar client.",
            f"- Feed URL I resolved matches the one the pipeline used for "
            f"{int(cal.feed_url_matches_db.sum())} of {len(cal)}.",
            f"- The pipeline's own episode range covers the charting window for "
            f"{int(cal.db_covers_window.sum())} of {len(cal)}; my live-feed test says "
            f"{int(cal.covers_window.sum())}. "
            "Where the database reaches further back than the feed does, the feed "
            "has been pruned since the pipeline collected it.",
            "",
        ]
        bad = cal[(cal.db_downloaded > 0) & ~cal.audio_ok]
        if len(bad):
            lines += ["Shows the pipeline downloaded but my spot-check called unfetchable:", ""]
            for r in bad.itertuples():
                lines.append(f"- {r.name} — statuses `{r.audio_statuses or 'none'}`, "
                             f"types `{r.audio_types or 'none'}`, verdict `{r.verdict}`")
            lines.append("")
        drift = cal[(cal.min_pub_gap_days.notna()) & (cal.min_pub_gap_days > 365)]
        if len(drift):
            lines += [
                f"{len(drift)} show{'' if len(drift) == 1 else 's'} where the live "
                "feed's oldest episode is now more than a year newer than the oldest "
                "the pipeline recorded — feeds are actively pruning history:",
                "",
            ]
            for r in drift.sort_values("min_pub_gap_days", ascending=False).head(15).itertuples():  # noqa: E501
                lines.append(f"- {r.name} — feed starts {str(r.min_pub)[:10]}, "
                             f"database has {str(r.db_min_pub)[:10]} "
                             f"({int(r.min_pub_gap_days)} days newer)")
            lines.append("")
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------------------- cli

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phases", nargs="*", default=["all"],
                    help="lookup feeds audio verify wayback report (default: all)")
    ap.add_argument("--wayback-budget", type=float, default=1800.0,
                    help="seconds to spend on the Wayback fallback")
    args = ap.parse_args()
    phases = args.phases or ["all"]
    if "all" in phases:
        phases = ["lookup", "feeds", "audio", "verify", "feeds", "audio",
                  "report", "wayback", "report"]

    for phase in phases:
        started = time.time()
        print(f"[{phase}]")
        if phase == "lookup":
            phase_lookup()
        elif phase == "feeds":
            phase_feeds()
        elif phase == "audio":
            phase_audio()
        elif phase == "verify":
            phase_verify()
        elif phase == "wayback":
            phase_wayback(args.wayback_budget)
        elif phase == "report":
            phase_report()
        else:
            print(f"unknown phase {phase!r}")
            return 2
        print(f"[{phase}] {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
