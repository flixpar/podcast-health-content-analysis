#!/usr/bin/env python3
"""Evaluate a keyword pre-filter against the pilot's own labels.

The question is only ever recall: a screen that drops a window means the
expensive pass never sees it, so a miss is unrecoverable. Terms come from the
taxonomy's own `concepts` and label names -- deriving them from this slice's
labels would fit the genre pocket the slice happens to be.
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
STOP = {
    "health", "other", "content", "claims", "general", "the", "and", "for",
    "uncategorised health content", "name the subject in the summary",
}


def build_terms(taxonomy: dict) -> tuple[set[str], set[str]]:
    """Split taxonomy vocabulary into whole-word terms and phrase terms."""
    words: set[str] = set()
    phrases: set[str] = set()
    for label in taxonomy["labels"]:
        raw = list(label.get("concepts") or []) + re.split(
            r"[/&,]", label.get("name", "")
        )
        for item in raw:
            term = item.strip().strip("“”\"'").lower()
            term = re.sub(r"[^a-z0-9\s\-']", " ", term)
            term = re.sub(r"\s+", " ", term).strip()
            if not term or term in STOP or len(term) < 4:
                continue
            (phrases if " " in term else words).add(term)
    return words, phrases


def main() -> None:
    taxonomy = json.loads((FULLRUN / "taxonomy.json").read_text())
    words, phrases = build_terms(taxonomy)
    extra = Path(sys.argv[1]).read_text().split() if len(sys.argv) > 1 else []
    words.update(w.lower() for w in extra if w)
    print(f"screen vocabulary: {len(words)} words + {len(phrases)} phrases")

    word_re = re.compile(r"\b(" + "|".join(sorted(map(re.escape, words), key=len, reverse=True)) + r")\b")
    phrase_re = re.compile("|".join(sorted(map(re.escape, phrases), key=len, reverse=True)))

    db = sqlite3.connect(FULLRUN / "labels.sqlite")
    truth: dict[str, dict] = {}
    for wid, rj in db.execute("SELECT window_id, result_json FROM window_labels"):
        r = json.loads(rj)
        dets = r.get("detections") or []
        truth[wid] = {
            "sub": sum(1 for d in dets if d["relevance"] == "substantive"),
            "any": len(dets),
            "claims": len(r.get("verification_candidates") or []),
            "ad": sum(1 for d in dets if d["relevance"] == "advertisement"),
        }

    stats = collections.Counter()
    missed_examples: list[tuple[str, int, int]] = []
    with open(FULLRUN / "windows.jsonl.zst", "rb") as fh:
        stream = io.TextIOWrapper(
            zstd.ZstdDecompressor().stream_reader(fh), encoding="utf-8"
        )
        for line in stream:
            obj = json.loads(line)
            wid = obj["window_id"]
            t = truth.get(wid)
            if t is None:
                continue
            text = " ".join(u["text"] for u in obj["units"]).lower()
            hit = bool(word_re.search(text)) or bool(phrase_re.search(text))
            stats["scanned"] += 1
            stats["kept" if hit else "dropped"] += 1
            for name, positive in (
                ("substantive", t["sub"] > 0),
                ("claim", t["claims"] > 0),
                ("any_detection", t["any"] > 0),
                ("payload", t["sub"] > 0 or t["claims"] > 0),
            ):
                if positive:
                    stats[f"pos_{name}"] += 1
                    if hit:
                        stats[f"recalled_{name}"] += 1
                    elif name == "payload" and len(missed_examples) < 8:
                        missed_examples.append((wid, t["sub"], t["claims"]))
            if stats["scanned"] == len(truth):
                break

    print(f"\nwindows scanned: {stats['scanned']}")
    kept = stats["kept"]
    print(f"kept by screen:  {kept} ({kept/stats['scanned']:.1%})")
    print(f"dropped:         {stats['dropped']} ({stats['dropped']/stats['scanned']:.1%})")
    print("\nrecall of positives (what the screen would NOT have thrown away):")
    for name in ("substantive", "claim", "payload", "any_detection"):
        pos = stats[f"pos_{name}"]
        rec = stats[f"recalled_{name}"]
        print(f"  {name:15s} {rec}/{pos} = {rec/max(pos,1):.2%}")
    print("\nmissed payload windows (window_id, substantive, claims):")
    for m in missed_examples:
        print("   ", m)


if __name__ == "__main__":
    main()
