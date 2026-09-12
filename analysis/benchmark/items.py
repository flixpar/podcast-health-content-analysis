"""Benchmark items: windows in the pipeline's own shape, plus how they were chosen.

An item is one window exactly as ``run_prepare`` would emit it for that
episode (same units, IDs, timing and metadata), with benchmark fields added:
``item_id``, ``stratum``, ``split``, ``source``, ``tags``, ``provenance``,
``features`` and ``added_in``. ``window_payload`` strips the benchmark fields
back off, so a labeler consumes an item as an ordinary window.

``build_pool`` draws candidate windows per stratum from the corpus using the
lexical scan's per-episode counts to choose episodes and the same lexicon over
each window's units to choose windows. ``select_items`` then fills the quotas
from the pool, preferring windows that screening kept, and assigns the
dev/test split.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sqlite3
import tomllib
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from analysis import topic_labeling as tl
from analysis.benchmark import (
    BENCHMARK_VERSION,
    CONFIG_PATH,
    ITEMS_PATH,
    POOL_DIR,
    REPO_ROOT,
)
from analysis.benchmark.lexicon import HEALTH_SECTIONS, Matcher, repeated_ngram_ratio

# The keys ``run_prepare`` writes for a window (analysis/topic_labeling.py,
# run_prepare). Everything else on an item is benchmark bookkeeping.
WINDOW_KEYS = (
    "schema_version",
    "window_id",
    "episode_id",
    "window_index",
    "podcast_id",
    "podcast_title",
    "episode_title",
    "published_date",
    "duration_seconds",
    "source_transcript",
    "source_transcript_sha256",
    "transcript_source",
    "transcript_model",
    "language",
    "start_seconds",
    "end_seconds",
    "timing_quality",
    "word_count",
    "units",
)
STRATA = (
    "health_dense",
    "mixed",
    "null",
    "ad_read",
    "discourse",
    "rare_label",
    "synthetic",
    "contrast",
)
CORPUS_STRATA = STRATA[:6]
SOURCES = ("corpus", "synthetic", "contrast")
SPLITS = ("dev", "test")


class BenchmarkError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Config and I/O
# --------------------------------------------------------------------------


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with open(path, "rb") as handle:
        return tomllib.load(handle)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_items(path: Path = ITEMS_PATH) -> list[dict[str, Any]]:
    if not Path(path).exists():
        return []
    return list(tl.iter_jsonl(Path(path)))


def write_items(path: Path, items: Iterable[dict[str, Any]]) -> tuple[int, str]:
    """Write items sorted by item_id; returns (count, sha256 of the file)."""
    rows = sorted(items, key=lambda item: item["item_id"])
    ids = [row["item_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise BenchmarkError("duplicate item_id in items")
    window_ids = [row["window_id"] for row in rows]
    if len(window_ids) != len(set(window_ids)):
        raise BenchmarkError("duplicate window_id in items")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return tl.write_jsonl_atomic(Path(path), rows)


def items_hash(items: Sequence[dict[str, Any]]) -> str:
    """Content hash over item ids and unit text, independent of bookkeeping."""
    digest = hashlib.sha256()
    for item in sorted(items, key=lambda row: row["item_id"]):
        digest.update(item["item_id"].encode("utf-8"))
        for unit in item["units"]:
            digest.update(b"\0" + unit["unit_id"].encode("utf-8"))
            digest.update(b"\0" + unit["text"].encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def window_payload(item: dict[str, Any]) -> dict[str, Any]:
    """The window as a labeler sees it: the pipeline's keys, nothing else."""
    return {key: item.get(key) for key in WINDOW_KEYS}


def window_text(window: dict[str, Any]) -> str:
    return " ".join(unit["text"] for unit in window["units"])


# --------------------------------------------------------------------------
# Corpus metadata
# --------------------------------------------------------------------------


def genre_group(categories: Sequence[str], mapping: dict[str, list[str]]) -> str:
    for group, names in mapping.items():
        if any(category in names for category in categories):
            return group
    return "other"


def _sqlite_ro(path: Path) -> sqlite3.Connection:
    """Read-only connection, tolerating the WAL files beside the database."""
    absolute = Path(path).resolve()
    quoted = urllib.parse.quote(str(absolute))
    try:
        connection = sqlite3.connect(f"file:{quoted}?mode=ro", uri=True)
        connection.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchall()
    except sqlite3.OperationalError:
        wal = Path(str(absolute) + "-wal")
        if wal.exists() and wal.stat().st_size:
            raise BenchmarkError(f"{path} has an active WAL and cannot be opened read-only")
        connection = sqlite3.connect(f"file:{quoted}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def read_metadata(db_path: Path, mapping: dict[str, list[str]]) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    """Episode and podcast metadata keyed by id; podcasts carry genre_group."""
    connection = _sqlite_ro(db_path)
    try:
        podcasts: dict[int, dict[str, Any]] = {}
        for row in connection.execute("SELECT id, title, publisher, categories FROM podcasts"):
            try:
                categories = [c for c in json.loads(row["categories"] or "[]") if c != "Podcasts"]
            except json.JSONDecodeError:
                categories = []
            podcasts[int(row["id"])] = {
                "podcast_id": int(row["id"]),
                "podcast_title": row["title"],
                "publisher": row["publisher"],
                "categories": categories,
                "genre_group": genre_group(categories, mapping),
            }
        episodes: dict[int, dict[str, Any]] = {}
        query = """SELECT e.id AS episode_id, e.podcast_id, e.title AS episode_title,
                          e.published_date, e.duration_seconds,
                          t.metadata AS transcript_metadata
                   FROM episodes e LEFT JOIN transcripts t ON t.episode_id = e.id"""
        for row in connection.execute(query):
            meta = {}
            if row["transcript_metadata"]:
                try:
                    meta = json.loads(row["transcript_metadata"])
                except json.JSONDecodeError:
                    meta = {}
            podcast = podcasts.get(int(row["podcast_id"]) if row["podcast_id"] is not None else -1, {})
            episodes[int(row["episode_id"])] = {
                "episode_id": int(row["episode_id"]),
                "podcast_id": row["podcast_id"],
                "podcast_title": podcast.get("podcast_title"),
                "genre_group": podcast.get("genre_group", "other"),
                "episode_title": row["episode_title"],
                "published_date": row["published_date"],
                "duration_seconds": row["duration_seconds"],
                "transcript_source": meta.get("source"),
                "transcript_model": meta.get("model"),
            }
        return episodes, podcasts
    finally:
        connection.close()


# --------------------------------------------------------------------------
# Windows
# --------------------------------------------------------------------------


def transcript_path(transcripts_dir: Path, episode_id: int) -> Path:
    path = Path(transcripts_dir) / f"episode_{episode_id}.jsonl.zst"
    if not path.exists():
        alt = Path(transcripts_dir) / f"episode_{episode_id}.jsonl"
        if alt.exists():
            return alt
    return path


def windows_for_episode(
    path: Path,
    windowing: dict[str, int],
    episode_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Every window of one transcript, byte-for-byte what ``run_prepare`` emits."""
    path = Path(path)
    episode_id = tl.episode_id_from_path(path)
    transcript_meta, units = tl.read_transcript(path, windowing["max_unit_words"])
    if not units:
        return []
    source_sha256 = tl.sha256_file(path)
    meta = episode_meta or {}
    rows: list[dict[str, Any]] = []
    for window_index, window_units in tl.make_windows(
        units, windowing["window_words"], windowing["overlap_words"]
    ):
        rows.append(
            {
                "schema_version": tl.SCHEMA_VERSION,
                "window_id": f"episode_{episode_id}_window_{window_index:04d}",
                "episode_id": episode_id,
                "window_index": window_index,
                "podcast_id": meta.get("podcast_id"),
                "podcast_title": meta.get("podcast_title"),
                "episode_title": meta.get("episode_title")
                or meta.get("title")
                or transcript_meta.get("episode_title"),
                "published_date": meta.get("published_date"),
                "duration_seconds": meta.get("duration_seconds"),
                "source_transcript": str(path),
                "source_transcript_sha256": source_sha256,
                "transcript_source": transcript_meta.get("source"),
                "transcript_model": transcript_meta.get("model"),
                "language": transcript_meta.get("language", "en"),
                "start_seconds": tl._window_time(window_units, "start_seconds"),
                "end_seconds": tl._window_time(window_units, "end_seconds", reverse=True),
                "timing_quality": tl._window_timing_quality(window_units),
                "word_count": sum(len(unit["text"].split()) for unit in window_units),
                "units": window_units,
            }
        )
    return rows


# --------------------------------------------------------------------------
# Pool
# --------------------------------------------------------------------------


def _episode_stats(scan_dir: Path) -> "pandas.DataFrame":
    """Per-episode scan counts: sentences, health/commercial/discourse hits, per-label hits."""
    import pandas as pd
    import pyarrow.parquet as pq

    episodes = pq.read_table(Path(scan_dir) / "episodes.parquet").to_pandas()
    counts = pq.read_table(
        Path(scan_dir) / "counts.parquet", columns=["episode_id", "section", "label", "n_sent"]
    ).to_pandas()
    counts["n_sent"] = counts["n_sent"].astype("int64")
    by_section = (
        counts.groupby(["episode_id", "section"])["n_sent"].sum().unstack(fill_value=0)
    )
    frame = episodes.set_index("episode_id").join(by_section, how="left").fillna(0)
    for section in (*HEALTH_SECTIONS, "commercial", "correction", "distrust"):
        if section not in frame.columns:
            frame[section] = 0
    frame["health_hits"] = sum(frame[section] for section in HEALTH_SECTIONS)
    frame["health_density"] = frame["health_hits"] / frame["n_sent"].clip(lower=1)
    frame["discourse_hits"] = frame["correction"] + frame["distrust"]
    per_label = (
        counts.groupby(["episode_id", "section", "label"])["n_sent"].sum().reset_index()
    )
    per_label["key"] = per_label["section"] + ":" + per_label["label"]
    return frame, per_label


def _sample_with_caps(
    rng: random.Random,
    candidates: Sequence[int],
    episodes: dict[int, dict[str, Any]],
    count: int,
    max_per_show: int,
) -> list[int]:
    pool = sorted(candidates)
    rng.shuffle(pool)
    chosen: list[int] = []
    per_show: Counter[Any] = Counter()
    for episode_id in pool:
        show = episodes.get(episode_id, {}).get("podcast_id")
        if per_show[show] >= max_per_show:
            continue
        per_show[show] += 1
        chosen.append(episode_id)
        if len(chosen) >= count:
            break
    return chosen


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(math.ceil(q * len(ordered))) - 1))
    return ordered[index]


def choose_episodes(
    config: dict[str, Any],
    stats: "pandas.DataFrame",
    per_label: "pandas.DataFrame",
    episodes: dict[int, dict[str, Any]],
    rng: random.Random,
) -> dict[str, list[tuple[int, str | None]]]:
    """Candidate episodes per stratum as (episode_id, rare_label_or_None)."""
    pool_cfg = config["pool"]
    strata_cfg = config["strata"]
    count = int(pool_cfg["episodes_per_stratum"])
    max_per_show = int(pool_cfg["max_episodes_per_show"])
    usable = stats[stats["n_sent"] >= 50]
    genre_of = {eid: meta["genre_group"] for eid, meta in episodes.items()}
    usable = usable.assign(genre=[genre_of.get(int(eid), "other") for eid in usable.index])
    chosen: dict[str, list[tuple[int, str | None]]] = {}

    def in_genres(frame: "pandas.DataFrame", genres: Sequence[str]) -> "pandas.DataFrame":
        return frame[frame["genre"].isin(list(genres))]

    dense_cfg = strata_cfg["health_dense"]
    dense = in_genres(usable, dense_cfg["genres"])
    cutoff = _quantile(list(dense["health_density"]), float(dense_cfg["episode_density_quantile"]))
    dense = dense[dense["health_density"] >= cutoff]
    chosen["health_dense"] = [
        (eid, None) for eid in _sample_with_caps(rng, [int(e) for e in dense.index], episodes, count, max_per_show)
    ]

    mixed_cfg = strata_cfg["mixed"]
    mixed = in_genres(usable, mixed_cfg["genres"])
    mixed = mixed[mixed["health_hits"] >= 3]
    chosen["mixed"] = [
        (eid, None) for eid in _sample_with_caps(rng, [int(e) for e in mixed.index], episodes, count, max_per_show)
    ]

    null_cfg = strata_cfg["null"]
    null = in_genres(usable, null_cfg["genres"])
    cutoff = _quantile(list(null["health_density"]), float(null_cfg["episode_density_quantile_max"]))
    null = null[null["health_density"] <= cutoff]
    chosen["null"] = [
        (eid, None) for eid in _sample_with_caps(rng, [int(e) for e in null.index], episodes, count, max_per_show)
    ]

    ad_cfg = strata_cfg["ad_read"]
    ads = in_genres(usable, ad_cfg["genres"])
    ads = ads[(ads["commercial"] >= 5) & (ads["products"] >= 2)]
    chosen["ad_read"] = [
        (eid, None) for eid in _sample_with_caps(rng, [int(e) for e in ads.index], episodes, count, max_per_show)
    ]

    disc_cfg = strata_cfg["discourse"]
    show_ids = set(int(x) for x in disc_cfg["podcast_ids"])
    disc_show = [int(eid) for eid in usable.index if episodes.get(int(eid), {}).get("podcast_id") in show_ids]
    disc_other = usable[(usable["discourse_hits"] >= 3) & (usable["health_hits"] >= 5)]
    disc_other = [int(eid) for eid in disc_other.index if int(eid) not in set(disc_show)]
    half = count // 2
    chosen["discourse"] = [
        (eid, None) for eid in _sample_with_caps(rng, disc_show, episodes, half, max_per_show)
    ] + [
        (eid, None) for eid in _sample_with_caps(rng, disc_other, episodes, count - half, max_per_show)
    ]

    rare_cfg = strata_cfg["rare_label"]
    keys = (
        [f"topics:{label}" for label in rare_cfg["topics"]]
        + [f"frames:{label}" for label in rare_cfg["frames"]]
        + [f"narratives:{label}" for label in rare_cfg["narratives"]]
    )
    per_key = per_label[per_label["key"].isin(keys)]
    rare: list[tuple[int, str | None]] = []
    seen: set[int] = set()
    for key in keys:
        eids = [int(e) for e in per_key[per_key["key"] == key]["episode_id"] if int(e) in usable.index]
        eids = [e for e in eids if e not in seen]
        for eid in _sample_with_caps(rng, eids, episodes, int(rare_cfg["episodes_per_label"]), max_per_show):
            rare.append((eid, key))
            seen.add(eid)
    chosen["rare_label"] = rare
    return chosen


def _window_qualifies(
    stratum: str,
    features: dict[str, Any],
    neighbours: Sequence[dict[str, Any]],
    cfg: dict[str, Any],
    rare_key: str | None,
) -> bool:
    sections = features["section_units"]
    health = features["health_units"]
    commercial = sections.get("commercial", 0)
    discourse = sections.get("correction", 0) + sections.get("distrust", 0)
    if stratum == "health_dense":
        return health >= int(cfg["min_health_units"])
    if stratum == "mixed":
        return (
            int(cfg["min_health_units"]) <= health <= int(cfg["max_health_units"])
            and commercial <= int(cfg["max_commercial_units"])
        )
    if stratum == "null":
        return health <= int(cfg["max_health_units"]) and all(
            n["health_units"] <= int(cfg["max_neighbour_health_units"]) for n in neighbours
        )
    if stratum == "ad_read":
        return (
            commercial >= int(cfg["min_commercial_units"])
            and features["health_product_units"] >= int(cfg["min_health_product_units"])
        )
    if stratum == "discourse":
        return health >= int(cfg["min_health_units"]) and discourse >= int(cfg["min_discourse_units"])
    if stratum == "rare_label":
        return rare_key is not None and features["label_units"].get(rare_key, 0) > 0
    raise BenchmarkError(f"unknown stratum {stratum}")


def build_pool(
    config: dict[str, Any],
    out_dir: Path = POOL_DIR,
    seed: int | None = None,
    log: Any = None,
) -> dict[str, Any]:
    """Draw candidate windows per stratum; writes pool.jsonl and pool_summary.json."""
    paths = config["paths"]
    windowing = config["windowing"]
    pool_cfg = config["pool"]
    rng = random.Random(int(seed if seed is not None else config["benchmark"]["seed"]))
    episodes, _ = read_metadata(resolve_path(paths["metadata_db"]), config["genre_groups"])
    stats, per_label = _episode_stats(resolve_path(paths["scan_dir"]))
    matcher = Matcher.from_path(resolve_path(paths["lexicon"]))
    transcripts_dir = resolve_path(paths["transcripts"])
    chosen = choose_episodes(config, stats, per_label, episodes, rng)
    quotas = config["quotas"]
    targets = {
        stratum: int(math.ceil(quotas[stratum] * float(pool_cfg["oversample"])))
        for stratum in CORPUS_STRATA
    }
    max_per_episode = int(pool_cfg["max_windows_per_episode"])
    min_words = int(pool_cfg["min_window_words"])
    repeat_threshold = float(config["tags"]["asr_noise_repeat_ratio"])
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"episodes_read": 0, "episodes_missing": 0, "per_stratum": {}}
    used_windows: set[str] = set()
    feature_cache: dict[int, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}

    def windows_and_features(episode_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if episode_id in feature_cache:
            return feature_cache[episode_id]
        path = transcript_path(transcripts_dir, episode_id)
        if not path.exists():
            summary["episodes_missing"] += 1
            feature_cache[episode_id] = ([], [])
            return feature_cache[episode_id]
        windows = windows_for_episode(path, windowing, episodes.get(episode_id))
        features = [matcher.window_features(window["units"]) for window in windows]
        summary["episodes_read"] += 1
        feature_cache[episode_id] = (windows, features)
        return feature_cache[episode_id]

    for stratum in CORPUS_STRATA:
        cfg = config["strata"][stratum]
        taken = 0
        per_label_taken: Counter[str] = Counter()
        candidates = list(chosen[stratum])
        if stratum == "rare_label":
            # Round-robin across labels so the least common ones are not
            # crowded out by whichever label came first in the list.
            by_key: dict[str, list[tuple[int, str | None]]] = defaultdict(list)
            for episode_id, rare_key in candidates:
                by_key[str(rare_key)].append((episode_id, rare_key))
            interleaved: list[tuple[int, str | None]] = []
            while any(by_key.values()):
                for key in list(by_key):
                    if by_key[key]:
                        interleaved.append(by_key[key].pop(0))
            candidates = interleaved
        for episode_id, rare_key in candidates:
            if taken >= targets[stratum]:
                break
            if stratum == "rare_label" and per_label_taken[rare_key] >= int(config["strata"]["rare_label"].get("pool_windows_per_label", 3)):
                continue
            windows, features = windows_and_features(episode_id)
            qualifying: list[int] = []
            for index, (window, feats) in enumerate(zip(windows, features)):
                if window["word_count"] < min_words or window["window_id"] in used_windows:
                    continue
                neighbours = [features[j] for j in (index - 1, index + 1) if 0 <= j < len(features)]
                if _window_qualifies(stratum, feats, neighbours, cfg, rare_key):
                    qualifying.append(index)
            rng.shuffle(qualifying)
            per_episode_limit = 1 if stratum == "rare_label" else max_per_episode
            for index in qualifying[:per_episode_limit]:
                window = windows[index]
                feats = features[index]
                meta = episodes.get(episode_id, {})
                text = window_text(window)
                repeat = repeated_ngram_ratio(text)
                tags = []
                if repeat >= repeat_threshold:
                    tags.append("asr_noise")
                rows.append(
                    {
                        **window,
                        "pool_stratum": stratum,
                        "pool_rare_label": rare_key,
                        "features": {**feats, "repeat_ratio": round(repeat, 4)},
                        "tags": tags,
                        "provenance": {
                            "episode_id": episode_id,
                            "window_index": window["window_index"],
                            "podcast_id": meta.get("podcast_id"),
                            "podcast_title": meta.get("podcast_title"),
                            "genre_group": meta.get("genre_group", "other"),
                            "transcript_source": window.get("transcript_source"),
                            "transcript_model": window.get("transcript_model"),
                            "transcript_sha256": window["source_transcript_sha256"],
                            "windows_in_episode": len(windows),
                        },
                    }
                )
                used_windows.add(window["window_id"])
                taken += 1
                if rare_key:
                    per_label_taken[rare_key] += 1
                if taken >= targets[stratum]:
                    break
        summary["per_stratum"][stratum] = {
            "target": targets[stratum],
            "taken": taken,
            "episodes_offered": len(candidates),
            **({"per_label": dict(per_label_taken)} if stratum == "rare_label" else {}),
        }
        if log:
            print(f"pool {stratum}: {taken}/{targets[stratum]} windows", file=log)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    count, sha = tl.write_jsonl_atomic(out_dir / "pool.jsonl", rows)
    summary.update({"windows": count, "pool_sha256": sha, "seed": rng and int(seed if seed is not None else config["benchmark"]["seed"])})
    tl.write_json(out_dir / "pool_summary.json", summary)
    return summary


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------


def item_id_for(window: dict[str, Any]) -> str:
    return f"c{window['episode_id']}w{window['window_index']:04d}"


def load_screening(path: Path | None) -> dict[str, dict[str, Any]]:
    """Screening verdicts keyed by window_id (see tasks.py ``screen``)."""
    if path is None or not Path(path).exists():
        return {}
    return {row["window_id"]: row for row in tl.iter_jsonl(Path(path))}


def screening_fit(stratum: str, verdict: dict[str, Any]) -> int | None:
    """How well a screened window fits its stratum: 2 good, 1 usable, None skip.

    Unscreened windows (empty verdict) are treated as usable.
    """
    if not verdict:
        return 1
    density = verdict.get("health_density")
    tags = set(verdict.get("tags") or [])
    discourse_tags = {"rebuttal", "quoted_or_reported", "questioned"}
    if stratum == "null":
        if density == "none":
            return 2
        return 1 if density == "sparse" and int(verdict.get("health_units") or 0) == 0 else None
    if stratum == "health_dense":
        return {"dense": 2, "moderate": 1}.get(density)
    if stratum == "mixed":
        return {"sparse": 2, "moderate": 1, "dense": 0}.get(density)
    if stratum == "ad_read":
        if "ad_read" in tags:
            return 2 if "health_product" in tags else 1
        return None
    if stratum == "discourse":
        if density == "none":
            return None
        return 2 if tags & discourse_tags else (1 if "checkable_claims" in tags else 0)
    if stratum == "rare_label":
        if density == "none":
            return None
        return 2 if int(verdict.get("interest") or 0) >= 2 else 1
    return 1


def assign_split(
    items: list[dict[str, Any]], test_fraction: float, seed: int
) -> None:
    """Stratified dev/test split, in place, deterministic for a seed."""
    rng = random.Random(seed)
    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_stratum[item["stratum"]].append(item)
    for stratum, rows in by_stratum.items():
        rows = sorted(rows, key=lambda row: row["item_id"])
        rng.shuffle(rows)
        n_test = int(round(len(rows) * test_fraction))
        for index, row in enumerate(rows):
            row["split"] = "test" if index < n_test else "dev"


def select_items(
    config: dict[str, Any],
    pool_path: Path,
    screening_path: Path | None,
    existing: Sequence[dict[str, Any]] = (),
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Fill the corpus strata quotas from the pool.

    Windows screening marked ``drop`` are skipped; those marked ``keep`` come
    first, then unscreened ones. Existing items are kept (the set only grows)
    and their episodes and shows count against the caps.
    """
    rng = random.Random(int(seed if seed is not None else config["benchmark"]["seed"]))
    quotas = config["quotas"]
    pool_cfg = config["pool"]
    max_per_show = int(pool_cfg["max_items_per_show"])
    max_per_episode = int(pool_cfg["max_windows_per_episode"])
    screening = load_screening(screening_path)
    kept: list[dict[str, Any]] = [dict(item) for item in existing]
    per_show: Counter[Any] = Counter()
    per_episode: Counter[int] = Counter()
    per_stratum: Counter[str] = Counter()
    for item in kept:
        per_show[item["provenance"].get("podcast_id")] += 1
        per_episode[item["episode_id"]] += 1
        per_stratum[item["stratum"]] += 1
    pool = list(tl.iter_jsonl(Path(pool_path)))
    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for window in pool:
        by_stratum[window["pool_stratum"]].append(window)
    existing_ids = {item["item_id"] for item in kept}
    for stratum in CORPUS_STRATA:
        need = int(quotas[stratum]) - per_stratum[stratum]
        if need <= 0:
            continue
        candidates = sorted(by_stratum.get(stratum, []), key=item_id_for)
        rng.shuffle(candidates)

        def priority(window: dict[str, Any]) -> tuple[int, int]:
            verdict = screening.get(window["window_id"], {})
            fit = screening_fit(stratum, verdict)
            return (-(fit if fit is not None else 1), -int(verdict.get("interest", 0) or 0))

        candidates.sort(key=priority)
        rare_taken: Counter[str] = Counter()
        for window in candidates:
            if need <= 0:
                break
            verdict = screening.get(window["window_id"], {})
            if verdict.get("verdict") == "drop" or (verdict and screening_fit(stratum, verdict) is None):
                continue
            item_id = item_id_for(window)
            if item_id in existing_ids:
                continue
            show = window["provenance"].get("podcast_id")
            if per_show[show] >= max_per_show or per_episode[window["episode_id"]] >= max_per_episode:
                continue
            if stratum == "rare_label" and rare_taken[window["pool_rare_label"]] >= int(config["strata"]["rare_label"].get("items_per_label", 2)):
                continue
            tags = sorted(set(window.get("tags", [])) | set(verdict.get("tags", [])))
            item = {
                **window_payload(window),
                "item_id": item_id,
                "stratum": stratum,
                "split": None,
                "source": "corpus",
                "tags": tags,
                "provenance": {**window["provenance"], "rare_label": window.get("pool_rare_label")},
                "features": window.get("features", {}),
                "screening": {k: verdict.get(k) for k in ("interest", "ambiguity", "notes") if k in verdict},
                "added_in": str(config.get("benchmark", {}).get("added_in", BENCHMARK_VERSION)),
            }
            kept.append(item)
            existing_ids.add(item_id)
            per_show[show] += 1
            per_episode[window["episode_id"]] += 1
            per_stratum[stratum] += 1
            if stratum == "rare_label":
                rare_taken[window["pool_rare_label"]] += 1
            need -= 1
    unsplit = [item for item in kept if not item.get("split")]
    if unsplit:
        assign_split(unsplit, float(config["split"]["test_fraction"]), rng.randrange(1 << 30))
    return kept


def composition(items: Sequence[dict[str, Any]]) -> dict[str, Any]:
    strata = Counter(item["stratum"] for item in items)
    splits = Counter((item["stratum"], item["split"]) for item in items)
    sources = Counter(item["provenance"].get("transcript_source") for item in items if item["source"] == "corpus")
    shows = Counter(item["provenance"].get("podcast_title") for item in items if item["source"] == "corpus")
    return {
        "items": len(items),
        "per_stratum": dict(sorted(strata.items())),
        "per_split": {f"{s}/{p}": n for (s, p), n in sorted(splits.items())},
        "transcript_sources": dict(sources),
        "shows": len(shows),
        "max_items_one_show": max(shows.values()) if shows else 0,
        "items_hash": items_hash(items),
    }
