"""``resolve --study NAME``: turn a study's chart entities into catalog podcasts.

A study member is ``'podcast:<id>'``, ``'apple:<id>'`` or ``'title:<key>'``.
Before its episodes can be found it needs a catalog podcast, ideally one with
a feed. For every member that has no podcast, or whose podcast has no
``rss_url``:

1. A mapping already known (``db.podcast_for_entity``) is used as is.
2. ``apple:<id>`` (and ``podcast:<id>`` rows that carry an Apple id) go
   through one batched iTunes lookup. A listed show is upserted under its
   Apple id. A show Apple no longer lists -- common before 2018 -- falls back
   to a title search and then to the feed the recoverability audit found.
3. ``title:<key>`` is searched by title (``itunes_search.best_match`` holds the
   acceptance rules), then falls back to the recoverability audit.

Every decision an id does not carry is written to ``entity_links`` with its
evidence; a failure is a row with ``podcast_id`` NULL and is not retried for
``resolve.retry_after_days`` (unless ``--retry-failed``, or this run searches
and the failed attempt did not). Each entity is committed as it finishes, and
a search throttle that outlasts its retries stops the run rather than being
recorded as "not found".

Finally every member of the study is re-linked from ``podcast_for_entity``,
which also picks up entities resolved by earlier runs or other studies.
"""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from podcast_pipeline import db
from podcast_pipeline.catalog.itunes_search import ITunesSearch, Match, best_match, normalise, title_head
from podcast_pipeline.config import Config
from podcast_pipeline.http import make_session
from podcast_pipeline.models import PodcastRecord
from podcast_pipeline.sources.apple import _to_record, lookup_many

logger = logging.getLogger(__name__)

#: The 2026 recoverability audit (analysis/chart_archive/recoverability.py),
#: relative to ``Config.chart_archive_path``.
RECOVERABILITY_CSV = Path("parsed/population/recoverability.csv")
#: How many members each list in the summary names.
SUMMARY_LIST_CAP = 50


def recoverability_path(config: Config) -> Path:
    return config.chart_archive_path / RECOVERABILITY_CSV


# --- inputs ------------------------------------------------------------------

@dataclass
class Member:
    entity: str
    name: str | None
    podcast_id: int | None
    publishers: list[str] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return self.entity.partition(":")[0]

    @property
    def value(self) -> str:
        return self.entity.partition(":")[2]


@dataclass
class Recovered:
    """One row of the recoverability audit: a feed URL found for a show."""

    csv_entity: str
    key: str
    apple_id: str | None
    name: str
    publisher: str
    feed_source: str
    feed_url: str
    final_url: str
    http_status: str
    feed_error: str
    verdict: str
    matched_by: str = ""

    def evidence(self) -> dict:
        return {"csv_entity": self.csv_entity, "matched_by": self.matched_by,
                "apple_id": self.apple_id, "name": self.name, "publisher": self.publisher,
                "feed_source": self.feed_source, "feed_url": self.feed_url,
                "final_url": self.final_url or None, "http_status": self.http_status or None,
                "feed_error": self.feed_error or None, "verdict": self.verdict}


class RecoverabilityIndex:
    """recoverability.csv by entity ('apple:<id>' / 'title:<key>') and by title key."""

    def __init__(self, rows: list[Recovered], path: Path | None):
        self.path = path
        self.by_entity = {r.csv_entity: r for r in rows}
        keys = Counter(r.key for r in rows)
        self.by_key = {r.key: r for r in rows if r.key and keys[r.key] == 1}

    @classmethod
    def load(cls, path: Path) -> "RecoverabilityIndex":
        if not path.exists():
            logger.warning(f"No recoverability audit at {path}; that fallback is unavailable this run")
            return cls([], None)
        rows = []
        with path.open(newline="") as f:
            for r in csv.DictReader(f):
                entity = r["entity"].strip()
                apple_id = _apple_id(r.get("apple_id"))
                if not entity.startswith("title:"):
                    apple_id = apple_id or _apple_id(entity)
                    entity = f"apple:{apple_id}"
                rows.append(Recovered(
                    csv_entity=entity, key=r.get("key") or "", apple_id=apple_id,
                    name=r.get("name") or "", publisher=r.get("publisher") or "",
                    feed_source=r.get("feed_source") or "", feed_url=(r.get("feed_url") or "").strip(),
                    final_url=(r.get("final_url") or "").strip(), http_status=r.get("http_status") or "",
                    feed_error=r.get("feed_error") or "", verdict=r.get("verdict") or ""))
        logger.info(f"Loaded {len(rows)} recoverability rows from {path}")
        return cls(rows, path)

    def find(self, member: Member, apple_id: str | None) -> Recovered | None:
        """The audit row for a member: by entity (or Apple id), else by unique title key."""
        candidates = [(f"apple:{apple_id}", "apple_id")] if apple_id else []
        candidates.append((member.entity, "entity"))
        for entity, how in candidates:
            if entity in self.by_entity:
                return _with_match(self.by_entity[entity], how)
        if member.kind == "title" and member.value in self.by_key:
            return _with_match(self.by_key[member.value], "key")
        return None


def _with_match(row: Recovered, how: str) -> Recovered:
    return Recovered(**{**row.__dict__, "matched_by": how})


def _apple_id(value) -> str | None:
    """'1200361736', '1200361736.0' -> '1200361736'; anything else -> None."""
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text if text.isdigit() else None


def _publishers(attrs: str | None) -> list[str]:
    data = json.loads(attrs) if attrs else {}
    found = []
    for key in ("publisher", "publishers"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, list):
            found.extend(v for v in value if isinstance(v, str))
    return [p for p in dict.fromkeys(found) if p.strip()]


# --- catalog writes ------------------------------------------------------------

def _podcast(conn: sqlite3.Connection, podcast_id: int | None) -> sqlite3.Row | None:
    if podcast_id is None:
        return None
    return conn.execute("SELECT id, rss_url, apple_podcasts_id FROM podcasts WHERE id = ?",
                        (podcast_id,)).fetchone()


def _has_feed(conn: sqlite3.Connection, podcast_id: int | None) -> bool:
    row = _podcast(conn, podcast_id)
    return bool(row and row["rss_url"])


def _apple_id_of(conn: sqlite3.Connection, podcast_id: int | None) -> str | None:
    row = _podcast(conn, podcast_id)
    return row["apple_podcasts_id"] if row else None


def _podcast_by_apple(conn: sqlite3.Connection, apple_id: str) -> int | None:
    row = conn.execute("SELECT id FROM podcasts WHERE apple_podcasts_id = ? ORDER BY id LIMIT 1",
                       (apple_id,)).fetchone()
    return row["id"] if row else None


def _podcast_by_feed(conn: sqlite3.Connection, urls: list[str]) -> int | None:
    for url in urls:
        row = conn.execute("""
            SELECT id FROM podcasts WHERE rss_url = ?
            UNION SELECT podcast_id FROM podcast_feeds WHERE url = ?
            ORDER BY 1 LIMIT 1""", (url, url)).fetchone()
        if row:
            return row[0]
    return None


def _upsert_itunes(conn: sqlite3.Connection, details: dict, feed_source: str) -> int:
    """Upsert an iTunes lookup/search record under its Apple id.

    An existing row's feed and Spotify id are kept when the record lacks them:
    an Apple listing without ``feedUrl`` must not erase a feed found earlier.
    """
    entry = {"id": str(details["collectionId"]), "name": details.get("collectionName"),
             "artistName": details.get("artistName")}
    record = _to_record(entry, details)
    row = conn.execute("SELECT rss_url, spotify_id FROM podcasts WHERE podchaser_id = ? "
                       "OR apple_podcasts_id = ? ORDER BY id LIMIT 1",
                       (record.source_id, record.apple_podcasts_id)).fetchone()
    if row:
        record.rss_url = record.rss_url or row["rss_url"]
        record.spotify_id = record.spotify_id or row["spotify_id"]
    podcast_id = db.upsert_podcast(conn, record)
    if details.get("feedUrl"):
        db.record_feed_url(conn, podcast_id, details["feedUrl"], feed_source)
    return podcast_id


def _attach_feed(conn: sqlite3.Connection, podcast_id: int, urls: list[str], source: str) -> None:
    """Remember feed URLs for a podcast; the first becomes ``rss_url`` if it has none."""
    urls = [u for u in dict.fromkeys(urls) if u]
    for url in urls:
        db.record_feed_url(conn, podcast_id, url, source)
    if urls:
        conn.execute("UPDATE podcasts SET rss_url = ? WHERE id = ? AND (rss_url IS NULL OR rss_url = '')",
                     (urls[0], podcast_id))


def _create_from_recoverability(conn: sqlite3.Connection, member: Member, rec: Recovered,
                                apple_id: str | None) -> int:
    record = PodcastRecord(
        source_id=f"apple_{apple_id}" if apple_id else f"title_{member.value}",
        title=rec.name or member.name or member.value,
        publisher=rec.publisher or (member.publishers[0] if member.publishers else None),
        rss_url=rec.feed_url, apple_podcasts_id=apple_id,
        extra={"source": "recoverability", "entity": member.entity,
               "feed_source": rec.feed_source, "verdict": rec.verdict})
    return db.upsert_podcast(conn, record)


# --- one entity ----------------------------------------------------------------

@dataclass
class Outcome:
    status: str                  # 'resolved' | 'resolved_without_feed' | 'failed'
    method: str | None           # how the podcast was found this run; None if it was not
    podcast_id: int | None
    detail: dict


@dataclass
class Context:
    conn: sqlite3.Connection
    study: str
    search: bool
    searcher: ITunesSearch | None
    lookups: dict[str, dict]
    recoverability: RecoverabilityIndex


def _search(ctx: Context, member: Member) -> tuple[Match | None, list[dict]]:
    """Search by the member's name, then by its head if it has a subtitle."""
    terms = [member.name]
    head = title_head(member.name)
    if head and normalise(head) != normalise(member.name):
        terms.append(head)
    steps = []
    for term in terms:
        results = ctx.searcher.search(term)
        match = best_match(results, member.name, member.publishers)
        steps.append({"step": "itunes_search", "term": term, "results": len(results),
                      "top": [{"id": str(r.get("collectionId")), "title": r.get("collectionName"),
                               "publisher": r.get("artistName")} for r in results[:3]],
                      "accepted": match.evidence() if match else None})
        if match:
            return match, steps
    return None, steps


def resolve_member(ctx: Context, member: Member) -> Outcome:
    """Find (or create) the catalog podcast for one member and record why."""
    conn = ctx.conn
    podcast_id = member.podcast_id
    method = None
    match: Match | None = None
    detail: dict = {"study": ctx.study, "name": member.name, "publishers": member.publishers,
                    "searched": False, "steps": []}
    steps = detail["steps"]

    apple_id = member.value if member.kind == "apple" else _apple_id_of(conn, podcast_id)

    # 1. Apple's own listing.
    listed = False
    if apple_id:
        details = ctx.lookups.get(apple_id)
        listed = details is not None
        steps.append({"step": "itunes_lookup", "apple_id": apple_id, "listed": listed,
                      "feed": (details or {}).get("feedUrl")})
        if details:
            podcast_id = _upsert_itunes(conn, details, "itunes_lookup")
            method = "itunes_lookup"

    # 2. A title search, when Apple does not list the show at all. A listed
    # show without a feed is not searched: its own listing is the identity.
    # ``search_covered`` says whether a later run with search on would try
    # anything more (see _recently_failed).
    searchable = (not listed and member.kind in ("apple", "title") and bool(member.name))
    detail["search_covered"] = not searchable or ctx.search
    if not _has_feed(conn, podcast_id) and ctx.search and searchable:
        detail["searched"] = True
        match, search_steps = _search(ctx, member)
        steps.extend(search_steps)
        if match:
            detail["match"] = match.evidence()
            held = _podcast_by_apple(conn, apple_id) if apple_id else None
            if held is not None:
                # The catalog already holds this Apple id (feedless), and
                # podcast_for_entity answers with it; give it the feed.
                podcast_id = held
                _attach_feed(conn, podcast_id, [match.record.get("feedUrl")], "itunes_search")
            else:
                podcast_id = _upsert_itunes(conn, match.record, "itunes_search")
            method = "itunes_search"

    # 3. The recoverability audit's feed URL.
    if not _has_feed(conn, podcast_id):
        rec = ctx.recoverability.find(member, apple_id)
        steps.append({"step": "recoverability", "found": rec is not None,
                      "feed": rec.feed_url if rec else None,
                      "checked": ctx.recoverability.path is not None})
        if rec and rec.feed_url:
            detail["recoverability"] = rec.evidence()
            urls = [rec.feed_url, rec.final_url]
            rec_apple = apple_id or rec.apple_id
            if podcast_id is None and rec_apple:
                podcast_id = db.podcast_for_entity(conn, f"apple:{rec_apple}")
            if podcast_id is None:
                podcast_id = _podcast_by_feed(conn, urls)
                if podcast_id is not None:
                    detail["recoverability"]["existing_podcast_by_feed"] = podcast_id
            if podcast_id is None:
                podcast_id = _create_from_recoverability(conn, member, rec, rec_apple)
            _attach_feed(conn, podcast_id, urls, "recoverability")
            method = "recoverability"

    has_feed = _has_feed(conn, podcast_id)
    status = ("failed" if podcast_id is None else
              "resolved" if has_feed else "resolved_without_feed")
    detail["outcome"] = status

    if method is not None and podcast_id is not None and member.kind != "podcast":
        db.record_podcast_source(conn, podcast_id, db.SourceKind.CHART_ARCHIVE, member.entity,
                                 {"study": ctx.study, "method": method,
                                  **({"match_tier": match.tier} if match and method == "itunes_search" else {})})

    if member.kind != "podcast":
        trivial = method == "itunes_lookup" and has_feed
        known = conn.execute("SELECT method, detail FROM entity_links WHERE entity = ?",
                             (member.entity,)).fetchone()
        if not trivial or known:
            link_method = method or ("itunes_search" if detail["searched"] else
                                     "itunes_lookup" if apple_id else "recoverability")
            if method is None and podcast_id is not None and known:
                # Nothing new was found for an entity already linked (to a
                # feedless podcast): keep the evidence for that link.
                link_method = known["method"]
                detail["previous"] = json.loads(known["detail"] or "null")
            db.link_entity(conn, member.entity, podcast_id, link_method, detail)

    return Outcome(status, method, podcast_id, detail)


# --- the command -----------------------------------------------------------------

def _members(conn: sqlite3.Connection, study: str) -> list[Member]:
    rows = conn.execute("""
        SELECT entity, name, podcast_id, attrs FROM study_members
        WHERE study = ? ORDER BY rowid""", (study,)).fetchall()
    return [Member(r["entity"], r["name"], r["podcast_id"], _publishers(r["attrs"])) for r in rows]


def _recently_failed(conn: sqlite3.Connection, member: Member, search: bool, days: float) -> bool:
    """A recent attempt that found no feed, and covered everything this run would try."""
    row = conn.execute("""
        SELECT detail, julianday('now') - julianday(resolved_at) AS age
        FROM entity_links WHERE entity = ?""", (member.entity,)).fetchone()
    if row is None or row["age"] is None or row["age"] >= days:
        return False
    covered = bool(json.loads(row["detail"] or "{}").get("search_covered"))
    return covered or not search


def _set_member(conn: sqlite3.Connection, study: str, entity: str, podcast_id: int | None) -> None:
    conn.execute("UPDATE study_members SET podcast_id = ? WHERE study = ? AND entity = ?",
                 (podcast_id, study, entity))


def run(config: Config, conn: sqlite3.Connection, study: str, retry_failed: bool = False,
        search: bool = True, limit: int | None = None) -> dict:
    if conn.execute("SELECT 1 FROM studies WHERE name = ?", (study,)).fetchone() is None:
        raise ValueError(f"Unknown study {study!r}; run `study refresh {study}` first")
    members = _members(conn, study)

    # 1. Mappings already known, and what is left to do.
    known, todo = 0, []
    for m in members:
        if m.podcast_id is None:
            m.podcast_id = db.podcast_for_entity(conn, m.entity)
            if m.podcast_id is not None:
                _set_member(conn, study, m.entity, m.podcast_id)
                known += 1
        if not _has_feed(conn, m.podcast_id):
            todo.append(m)
    conn.commit()

    skipped_recent, no_route, attempt = [], [], []
    for m in todo:
        if m.kind not in ("podcast", "apple", "title"):
            raise ValueError(f"Unknown entity kind in study {study!r}: {m.entity!r}")
        if m.kind == "podcast" and not _apple_id_of(conn, m.podcast_id):
            no_route.append(m)      # a catalog podcast with no Apple id: nothing to look up
        elif not retry_failed and _recently_failed(conn, m, search, config.resolve.retry_after_days):
            skipped_recent.append(m)
        else:
            attempt.append(m)
    if limit is not None:
        attempt = attempt[:limit]
    logger.info(f"Study {study}: {len(members)} members, {len(todo)} without a feed; "
                f"attempting {len(attempt)} ({len(skipped_recent)} failed recently, "
                f"{len(no_route)} catalog podcasts with no Apple id)")

    session = make_session()
    apple_ids = []
    for m in attempt:
        if m.kind == "apple":
            apple_ids.append(m.value)
        elif m.kind == "podcast":
            apple_ids.append(_apple_id_of(conn, m.podcast_id))
    lookups = (lookup_many(session, apple_ids, batch_size=config.resolve.lookup_batch_size,
                           delay=config.resolve.lookup_delay_seconds) if apple_ids else {})
    if apple_ids:
        logger.info(f"iTunes lookup: {len(lookups)} of {len(set(apple_ids))} Apple ids still listed")

    searcher = (ITunesSearch(session, delay_seconds=config.spotify.search_delay_seconds,
                             attempts=config.spotify.search_attempts,
                             limit=config.resolve.search_candidates,
                             advice="entities finished so far are committed; re-run `resolve` "
                                    "later or raise spotify.search_delay_seconds")
                if search else None)
    ctx = Context(conn, study, search, searcher, lookups,
                  RecoverabilityIndex.load(recoverability_path(config)))

    outcomes, methods = Counter(), Counter()
    title_only = []
    for i, m in enumerate(attempt, 1):
        outcome = resolve_member(ctx, m)
        conn.commit()
        outcomes[outcome.status] += 1
        if outcome.method:
            match = outcome.detail.get("match") or {}
            label = (f"itunes_search_{match['tier']}" if outcome.method == "itunes_search"
                     else outcome.method)
            methods[label] += 1
            if outcome.method == "itunes_search" and match.get("publisher_match") is False:
                title_only.append({"entity": m.entity, "name": m.name,
                                   "publishers": m.publishers,
                                   "candidate_title": match["candidate_title"],
                                   "candidate_publisher": match["candidate_publisher"]})
        logger.info(f"  {i}/{len(attempt)} {m.entity} ({m.name}): {outcome.status}"
                    f"{' via ' + outcome.method if outcome.method else ''}")

    # 6. Re-link every member, including ones resolved by earlier runs or other studies.
    by_podcast = defaultdict(list)
    for m in members:
        m.podcast_id = db.podcast_for_entity(conn, m.entity)
        _set_member(conn, study, m.entity, m.podcast_id)
        if m.podcast_id is not None:
            by_podcast[m.podcast_id].append(m.entity)
    conn.commit()

    unresolved = [m for m in members if m.podcast_id is None]
    feedless = [m for m in members if m.podcast_id is not None and not _has_feed(conn, m.podcast_id)]
    merged = [{"podcast_id": pid, "entities": entities}
              for pid, entities in sorted(by_podcast.items()) if len(entities) > 1]
    return {
        "study": study,
        "members": len(members),
        "already_known": known,
        "needing_work": len(todo),
        "attempted": len(attempt),
        "skipped_recent_failure": len(skipped_recent),
        "no_route": len(no_route),
        "outcomes": dict(outcomes),
        "methods": dict(methods),
        "searches": searcher.requests if searcher else 0,
        "recoverability_csv": str(ctx.recoverability.path) if ctx.recoverability.path else None,
        "title_only_matches": title_only[:SUMMARY_LIST_CAP],
        "resolved_members": len(members) - len(unresolved),
        "with_feed": len(members) - len(unresolved) - len(feedless),
        "unresolved_count": len(unresolved),
        "unresolved": [{"entity": m.entity, "name": m.name} for m in unresolved[:SUMMARY_LIST_CAP]],
        "without_feed_count": len(feedless),
        "without_feed": [{"entity": m.entity, "name": m.name, "podcast_id": m.podcast_id}
                         for m in feedless[:SUMMARY_LIST_CAP]],
        "merged": merged,
    }
