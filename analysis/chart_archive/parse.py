"""Flatten every downloaded capture into one long table of chart rows.

Output: data/chart-archive/parsed/chart_rows.parquet (plus a CSV sample) with
one row per (capture, rank). Sources disagree on what they rank -- shows,
episodes, publishers -- so `unit` says which, and `rank_depth` (added later)
says how far down each capture goes.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from html import unescape
from urllib.parse import unquote, urlsplit

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2] / "data" / "chart-archive"
RAW = ROOT / "raw"
OUT = ROOT / "parsed"

APPLE_GENRES = {
    "26": "All Podcasts", "1301": "Arts", "1302": "Personal Journals",
    "1303": "Comedy", "1304": "Education", "1305": "Kids & Family",
    "1309": "TV & Film", "1310": "Music", "1314": "Religion & Spirituality",
    "1318": "Technology", "1321": "Business", "1323": "Games & Hobbies",
    "1324": "Society & Culture", "1325": "Government & Organizations",
    "1482": "Arts (legacy)", "1483": "Fiction", "1487": "History",
    "1488": "True Crime", "1489": "News", "1493": "Sports (legacy)",
    "1502": "Leisure", "1511": "Government", "1512": "Health & Fitness",
    "1533": "Science", "1545": "Sports",
}


def ts_to_iso(ts: str) -> str:
    return datetime.strptime(ts, "%Y%m%d%H%M%S").replace(
        tzinfo=timezone.utc).isoformat()


def _apple_id(url: str | None) -> str | None:
    m = re.search(r"/id(\d+)", url or "")
    return m.group(1) if m else None


def read(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes())


def unslug(dirname: str) -> str:
    """Recover the normalized URL path/query from a raw/ directory name."""
    return dirname.rsplit("-", 1)[0]


# --------------------------------------------------------------------------
# Spotify chart API (JSON)

def parse_spotify_api(path: Path, slug: str) -> list[dict]:
    try:
        data = json.loads(read(path))
    except (json.JSONDecodeError, OSError, EOFError):
        return []
    if not isinstance(data, list) or not data:
        return []
    # slug: api_charts_<chart>[_limit=N][_region=xx]
    body = slug[len("api_charts_"):] if slug.startswith("api_charts_") else slug
    chart = body.split("_")[0].strip("_") or "top"
    region = "us"
    m = re.search(r"region=([a-z]{2})", slug)
    if m:
        region = m.group(1)
    rows = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        if "episodeUri" in item or "episodeName" in item:
            unit, uri = "episode", item.get("episodeUri")
            name = item.get("episodeName")
            publisher = item.get("showName")
        else:
            unit, uri = "show", item.get("showUri")
            name = item.get("showName")
            publisher = item.get("showPublisher")
        rows.append({
            "source": "spotify_api", "platform": "spotify", "unit": unit,
            "chart": chart, "region": region, "genre": chart,
            "rank": i, "name": name, "publisher": publisher,
            "entity_id": uri, "entity_url": None,
        })
    return rows


# --------------------------------------------------------------------------
# Chartable (server-rendered HTML tables)

CHARTABLE_REGION = {
    "united-states-of-america": "us", "great-britain": "gb", "australia": "au",
    "canada": "ca", "germany": "de", "global": "global",
}


def chartable_slug(raw: str) -> tuple[str, int]:
    """(chart slug, page number) from a raw/ directory name.

    Directory names keep the whole URL path, e.g.
    charts_itunes_us-all-podcasts-podcasts_page=2 -> ("us-all-podcasts-podcasts", 2)
    """
    m = re.search(r"_page=(\d+)$", raw)
    page = int(m.group(1)) if m else 1
    body = raw[:m.start()] if m else raw
    body = re.sub(r"^charts_(itunes|spotify|chartable)_?", "", body)
    return body, page


def chartable_facets(slug: str, source: str) -> tuple[str | None, str | None]:
    """(region, genre) from a Chartable chart slug.

    itunes:  us-all-podcasts-podcasts, us-health-fitness-podcasts[-<uuid>]
    spotify: united-states-of-america-top-podcasts, ...-news-politics
    reach:   podcast-us-all-podcasts-reach, podcasts-global-health-fitness-trending
    """
    body = re.sub(r"-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                  "", slug)
    if source == "chartable_itunes":
        m = re.match(r"([a-z]{2})-(.+?)-(podcasts|episodes)$", body)
        return (m.group(1), m.group(2)) if m else (None, body)
    if source == "chartable_spotify":
        for name, code in CHARTABLE_REGION.items():
            if body.startswith(name + "-"):
                return code, body[len(name) + 1:]
        return None, body
    body = re.sub(r"^podcasts?-", "", body)
    m = re.match(r"(.+?)-(reach|trending)$", body)
    body = m.group(1) if m else body
    for name, code in CHARTABLE_REGION.items():
        if body.startswith(name + "-"):
            return code, body[len(name) + 1:]
    m = re.match(r"([a-z]{2})-(.+)$", body)
    return (m.group(1), m.group(2)) if m else (None, body)


def _chartable_grid_rows(soup: BeautifulSoup) -> list[tuple[int, str | None, str | None, str | None]]:
    """Chartable's pre-2020 layout: a stack of div.mb4 blocks, not a table."""
    out = []
    for block in soup.find_all("div", class_="mb4"):
        links = block.find_all("a", href=re.compile(r"/podcasts/"))
        if not links:
            continue
        rank = None
        header = block.find("div", class_="header-font")
        if header is not None:
            m = re.match(r"\s*(\d+)\.", header.get_text(" ", strip=True))
            if m:
                rank = int(m.group(1))
        title = show_slug = show_name = None
        episode = next((a for a in links if "/episodes/" in a["href"]), None)
        # the artwork link points at the same slug but has no text, so prefer
        # a candidate that actually carries the show name
        candidates = [a for a in links if re.search(r"/podcasts/[^/]+$", a["href"])]
        show_link = next((a for a in candidates if a.get_text(strip=True)),
                         candidates[0] if candidates else None)
        if show_link is not None:
            show_slug = show_link["href"].rstrip("/").rsplit("/", 1)[-1]
            show_name = show_link.get_text(strip=True) or None
        if episode is not None:
            title = episode.get_text(strip=True)
        else:
            text = show_name or ""
            m = re.match(r"\s*(\d+)\.\s*(.+)", text)
            if m:
                rank = rank or int(m.group(1))
                title = m.group(2)
                show_name = None
            else:
                title = text or None
        if rank is None:
            continue
        out.append((rank, title, show_name, show_slug))
    return out


def parse_chartable(path: Path, raw_slug: str, source: str) -> list[dict]:
    soup = BeautifulSoup(read(path), "html.parser")
    slug, page = chartable_slug(raw_slug)
    region, genre = chartable_facets(slug, source)
    platform = {"chartable_itunes": "apple", "chartable_spotify": "spotify"}.get(
        source, "chartable")
    unit = "episode" if slug.endswith("-episodes") else "podcast"
    base = {"source": source, "platform": platform, "unit": unit,
            "chart": slug, "page": page, "region": region, "genre": genre}
    rows = []
    for tr in soup.find_all("tr"):
        rank_div = tr.find("div", class_="header-font")
        if rank_div is None:
            continue
        text = rank_div.get_text(strip=True)
        if not text.isdigit():
            continue
        show = tr.find("a", href=re.compile(r"/podcasts/"))
        title_div = tr.find("div", class_="title")
        title = (title_div.get_text(strip=True) if title_div
                 else (show.get_text(strip=True) if show else None))
        pub_el = tr.find(class_="silver")
        move_el = tr.select_one("div.tc.mt1 span")
        rows.append({**base, "rank": int(text), "name": title or None,
                     "publisher": pub_el.get_text(strip=True) if pub_el else None,
                     "rank_move": move_el.get_text(strip=True) if move_el else None,
                     "entity_id": (show["href"].rstrip("/").rsplit("/", 1)[-1]
                                   if show else None),
                     "entity_url": show["href"] if show else None})
    if rows:
        return rows
    for rank, title, show_name, show_slug in _chartable_grid_rows(soup):
        rows.append({**base, "rank": rank, "name": title, "publisher": show_name,
                     "rank_move": None, "entity_id": show_slug,
                     "entity_url": (f"https://chartable.com/podcasts/{show_slug}"
                                    if show_slug else None)})
    return rows


# --------------------------------------------------------------------------
# Apple podcasts.apple.com/us/charts (JSON embedded in the HTML)

def _salvage_shelves(tail: str) -> list[tuple[str, list[dict]]]:
    """Pull complete item objects out of a JSON blob that was cut off mid-document.

    Common Crawl stops fetching at 1 MB and Wayback occasionally truncates too,
    which leaves the `serialized-server-data` script unterminated. The shelves we
    care about sit early in the document, so a brace-counting walk recovers them
    in full even though `json.loads` on the whole blob would fail.
    """
    out: list[tuple[str, list[dict]]] = []
    for m in re.finditer(r'"title"\s*:\s*"((?:Top|Trending) [^"]{0,60})"', tail):
        j = tail.find('"items":[', m.end())
        if j < 0:
            continue
        k = j + len('"items":[')
        depth, start, items = 0, None, []
        while k < len(tail):
            c = tail[k]
            if c == '"':
                k += 1
                while k < len(tail) and tail[k] != '"':
                    k += 2 if tail[k] == "\\" else 1
            elif c == "{":
                if depth == 0:
                    start = k
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        items.append(json.loads(tail[start:k + 1]))
                    except json.JSONDecodeError:
                        pass
            elif c == "]" and depth == 0:
                break
            k += 1
        if items:
            out.append((m.group(1), items))
    return out


def _apple_rows(shelves, genre_id: str) -> list[dict]:
    rows = []
    for title, items in shelves:
        unit = "episode" if "Episode" in title else (
            "channel" if "Channel" in title else "podcast")
        # From 2025 the shelf itself names the genre ("Top Shows: Comedy"), and
        # the 2026 landing page carries every genre in one document, so the
        # shelf beats the URL as the genre label.
        kind, _, shelf_genre = title.partition(": ")
        genre = shelf_genre.strip() or APPLE_GENRES.get(genre_id, genre_id)
        for i, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            subs = item.get("subtitles") or []
            rows.append({
                "source": "apple_charts_page", "platform": "apple",
                "unit": unit, "chart": kind.strip(),
                "region": "us", "genre": genre,
                "rank": i, "name": item.get("title"),
                "publisher": (item.get("showTitle") if unit == "episode"
                              else (subs[0] if subs else None)),
                "entity_id": item.get("adamId") or item.get("id"),
                "entity_url": (item.get("clickAction") or {}).get("pageUrl"),
            })
    return rows


def parse_apple_page(path: Path, slug: str) -> list[dict]:
    html = read(path).decode("utf-8", "replace")
    genre_id = "26"
    g = re.search(r"genre=(\d+)", slug)
    if g:
        genre_id = g.group(1)
    open_at = html.find('id="serialized-server-data"')
    if open_at < 0:
        return []
    body_at = html.find(">", open_at) + 1
    close_at = html.find("</script>", body_at)
    if close_at > 0:
        try:
            blob = json.loads(html[body_at:close_at])
        except json.JSONDecodeError:
            blob = None
        if blob is not None:
            # Apple rewrapped the payload in 2025: what used to be a bare list
            # of pages is now {"data": [...pages...], "userTokenHash": ...}.
            if isinstance(blob, dict):
                inner = blob.get("data")
                pages = inner if isinstance(inner, list) else [blob]
            else:
                pages = blob
            shelves = []
            for page in pages:
                if not isinstance(page, dict):
                    continue
                data = page.get("data")
                for shelf in (data.get("shelves") if isinstance(data, dict) else None) or []:
                    if isinstance(shelf, dict) and isinstance(shelf.get("items"), list):
                        shelves.append((shelf.get("title") or "?", shelf["items"]))
            rows = _apple_rows(shelves, genre_id)
            if rows:
                return rows
    return _apple_rows(_salvage_shelves(html[body_at:]), genre_id)


# --------------------------------------------------------------------------
# Podbay (podbay.fm mirrored the US Apple chart from 2012 to 2019)

PODBAY_ROW = re.compile(
    r'href="/show/(\d+)".{0,1500}?badge[^>]*>(\d+)</span>\s*<h4>(.*?)</h4>\s*<h6>(.*?)</h6>',
    re.S)


def parse_podbay(path: Path, slug: str) -> list[dict]:
    html = read(path).decode("utf-8", "replace")
    genre = re.sub(r"^browse_?", "", slug).strip("_/") or "top"
    genre = re.sub(r"_podbay\.fm$", "", genre)
    if genre in ("top", "all", ""):
        genre = "all-podcasts"
    rows = []
    for adam_id, rank, name, publisher in PODBAY_ROW.findall(html):
        rows.append({
            "source": "podbay", "platform": "apple", "unit": "podcast",
            "chart": genre, "region": "us", "genre": genre,
            "rank": int(rank),
            "name": unescape(re.sub(r"<[^>]+>", "", name)).strip() or None,
            "publisher": unescape(re.sub(r"<[^>]+>", "", publisher)).strip() or None,
            "entity_id": adam_id,
            "entity_url": f"https://podcasts.apple.com/us/podcast/id{adam_id}",
        })
    # a capture can repeat a show (sidebar duplicates); rank is the key
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: r["rank"]):
        if r["rank"] in seen:
            continue
        seen.add(r["rank"])
        out.append(r)
    return out


# --------------------------------------------------------------------------
# Legacy iTunes toppodcasts RSS + Apple Marketing Tools RSS (XML/JSON)

def parse_itunes_rss(path: Path, slug: str) -> list[dict]:
    body = read(path)
    text = body.decode("utf-8", "replace")
    genre_id = "26"
    g = re.search(r"genre=(\d+)", slug)
    if g:
        genre_id = g.group(1)
    rows = []
    if text.lstrip().startswith("{"):
        try:
            feed = json.loads(text).get("feed", {})
        except json.JSONDecodeError:
            return []
        for i, e in enumerate(feed.get("entry", []) or [], start=1):
            rows.append({
                "name": (e.get("im:name") or {}).get("label"),
                "publisher": (e.get("im:artist") or {}).get("label"),
                "entity_id": (((e.get("id") or {}).get("attributes") or {}).get("im:id")
                              or _apple_id((e.get("id") or {}).get("label"))),
                "entity_url": (e.get("id") or {}).get("label"),
                "rank": i,
            })
    else:
        soup = BeautifulSoup(text, "xml")
        for i, entry in enumerate(soup.find_all("entry"), start=1):
            name = entry.find("im:name")
            artist = entry.find("im:artist")
            eid = entry.find("id")
            rows.append({
                "name": name.get_text(strip=True) if name else None,
                "publisher": artist.get_text(strip=True) if artist else None,
                "entity_id": _apple_id(eid.get_text(strip=True) if eid else None),
                "entity_url": eid.get_text(strip=True) if eid else None,
                "rank": i,
            })
        if not rows:  # marketing-tools feeds are plain RSS <item>s
            for i, item in enumerate(soup.find_all("item"), start=1):
                title = item.find("title")
                rows.append({
                    "name": title.get_text(strip=True) if title else None,
                    "publisher": None, "entity_id": None,
                    "entity_url": (item.find("link").get_text(strip=True)
                                   if item.find("link") else None),
                    "rank": i,
                })
    unit = "episode" if "podcast-episodes" in slug else "podcast"
    for r in rows:
        r.update({"source": "itunes_rss", "platform": "apple", "unit": unit,
                  "chart": slug, "region": "us",
                  "genre": APPLE_GENRES.get(genre_id, genre_id)})
    return rows


PARSERS = {
    "spotify_api": lambda p, s: parse_spotify_api(p, s),
    "chartable_itunes_us": lambda p, s: parse_chartable(p, s, "chartable_itunes"),
    "chartable_spotify": lambda p, s: parse_chartable(p, s, "chartable_spotify"),
    "chartable_reach": lambda p, s: parse_chartable(p, s, "chartable_reach"),
    "apple_charts_page": lambda p, s: parse_apple_page(p, s),
    "itunes_rss": lambda p, s: parse_itunes_rss(p, s),
    "itunes_rss_ax": lambda p, s: parse_itunes_rss(p, s),
    "podbay": lambda p, s: parse_podbay(p, s),
    "marketingtools": lambda p, s: parse_itunes_rss(p, s),
    "applemarketingtools": lambda p, s: parse_itunes_rss(p, s),
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    args = [a for a in sys.argv[1:]]
    use_cc = "--cc" in args
    args = [a for a in args if not a.startswith("--")]
    only = args[0] if args else None
    raw_dir = (ROOT / "raw_cc") if use_cc else RAW
    archive = "commoncrawl" if use_cc else "wayback"
    records: list[dict] = []
    failures: list[dict] = []
    for target_dir in sorted(raw_dir.iterdir()):
        if not target_dir.is_dir():
            continue
        target = target_dir.name
        if only and target != only:
            continue
        parser = PARSERS.get(target)
        if parser is None:
            print(f"skip {target}: no parser", flush=True)
            continue
        files = sorted(target_dir.glob("*/*.gz"))
        print(f"{target}: {len(files)} captures", flush=True)
        for n, path in enumerate(files, start=1):
            slug = unslug(path.parent.name)
            ts = path.name.split(".")[0]
            try:
                rows = parser(path, slug)
            except Exception as exc:  # a single bad capture must not stop the run
                failures.append({"path": str(path), "error": repr(exc)})
                continue
            if not rows:
                failures.append({"path": str(path), "error": "no rows"})
                continue
            iso = ts_to_iso(ts)
            for r in rows:
                r["captured_at"] = iso
                r["capture_ts"] = ts
                r["slug"] = slug
                r["path"] = str(path.relative_to(ROOT))
                r["archive"] = archive
            records.extend(rows)
            if n % 500 == 0:
                print(f"  {n}/{len(files)} ({len(records)} rows)", flush=True)

    df = pd.DataFrame.from_records(records)
    print(f"{len(df)} rows from {df['path'].nunique() if len(df) else 0} captures")
    suffix = ("_cc" if use_cc else "") + (f"_{only}" if only else "")
    df.to_parquet(OUT / f"chart_rows{suffix}.parquet", index=False)
    pd.DataFrame(failures).to_csv(OUT / f"parse_failures{suffix}.csv", index=False)
    print(f"{len(failures)} captures produced no rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
