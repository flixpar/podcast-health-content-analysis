#!/usr/bin/env python3
"""Find advertisement spans by cross-episode repetition, with no model call.

Sponsor reads are the one thing in a podcast corpus that repeats verbatim
across unrelated episodes: the same Gatorade copy ran in 94 of the pilot's 447
episodes. Hosts do not repeat themselves that way. So a unit whose exact
wording appears in several different episodes is almost always ad copy, and
runs of such units are ad breaks.

Scored against the model's own `relevance: advertisement` spans -- which are a
comparison, not truth: this finds ads in windows the model labeled nothing in,
and those show up here as false positives.
"""

from __future__ import annotations

import collections
import io
import json
import re
import sqlite3
import sys
from pathlib import Path

import zstandard as zstd

FULLRUN = Path("outputs/fullrun")
MIN_WORDS = 6          # below this, ordinary conversation repeats too
MIN_EPISODES = 3       # distinct episodes a wording must appear in
BRIDGE = 2             # flagged units this far apart join one span


def norm(text: str) -> str:
    t = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", t).strip()


def unit_no(uid: str) -> int:
    d = "".join(c for c in uid if c.isdigit())
    return int(d) if d else -1


def main() -> None:
    min_eps = int(sys.argv[1]) if len(sys.argv) > 1 else MIN_EPISODES
    db = sqlite3.connect(FULLRUN / "labels.sqlite")
    labeled = {
        wid: json.loads(rj)
        for wid, rj in db.execute("SELECT window_id, result_json FROM window_labels")
    }

    # Pass 1: how many distinct episodes carry each exact wording.
    episodes_for: dict[str, set[int]] = collections.defaultdict(set)
    windows: list[dict] = []
    with open(FULLRUN / "windows.jsonl.zst", "rb") as fh:
        stream = io.TextIOWrapper(zstd.ZstdDecompressor().stream_reader(fh), encoding="utf-8")
        for line in stream:
            obj = json.loads(line)
            if obj["window_id"] not in labeled:
                continue
            windows.append(obj)
            for u in obj["units"]:
                n = norm(u["text"])
                if len(n.split()) >= MIN_WORDS:
                    episodes_for[n].add(obj["episode_id"])
            if len(windows) == len(labeled):
                break

    repeated = {t for t, eps in episodes_for.items() if len(eps) >= min_eps}
    print(f"windows: {len(windows)}   distinct wordings >= {MIN_WORDS} words: {len(episodes_for):,}")
    print(f"wordings repeated across >= {min_eps} episodes: {len(repeated):,}")

    # Pass 2: flag units, join runs into spans, compare to the model's ad spans.
    tp = fp = fn = 0
    pred_units_total = 0
    ref_units_total = 0
    found_windows = 0
    novel: list[tuple[str, str]] = []
    for obj in windows:
        units = obj["units"]
        flags = [
            i for i, u in enumerate(units)
            if len(norm(u["text"]).split()) >= MIN_WORDS and norm(u["text"]) in repeated
        ]
        pred: set[int] = set()
        if flags:
            start = prev = flags[0]
            for i in flags[1:]:
                if i - prev <= BRIDGE + 1:
                    prev = i
                    continue
                pred.update(range(start, prev + 1))
                start = prev = i
            pred.update(range(start, prev + 1))

        idx = {u["unit_id"]: i for i, u in enumerate(units)}
        ref: set[int] = set()
        for d in labeled[obj["window_id"]].get("detections") or []:
            if d["relevance"] == "advertisement":
                a, b = idx.get(d["start_unit_id"]), idx.get(d["end_unit_id"])
                if a is not None and b is not None:
                    ref.update(range(a, b + 1))
        tp += len(pred & ref)
        fp += len(pred - ref)
        fn += len(ref - pred)
        pred_units_total += len(pred)
        ref_units_total += len(ref)
        if pred and not ref:
            found_windows += 1
            if len(novel) < 6:
                novel.append(
                    (obj["window_id"], " ".join(units[i]["text"] for i in sorted(pred))[:150])
                )

    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    print(f"\nunit-level vs the model's advertisement spans")
    print(f"  predicted ad units: {pred_units_total:,}   model ad units: {ref_units_total:,}")
    print(f"  precision {prec:.1%}   recall {rec:.1%}   F1 {2*prec*rec/max(prec+rec,1e-9):.1%}")
    print(f"  windows where this finds ad copy the model marked none: {found_windows}")
    for wid, text in novel:
        print(f"    {wid}: {text}")


if __name__ == "__main__":
    main()
