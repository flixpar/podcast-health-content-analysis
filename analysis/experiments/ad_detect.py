#!/usr/bin/env python3
"""Detect ad breaks from cross-episode repetition plus promotional register.

Repetition alone confuses sponsor copy with show boilerplate -- "Someone said
you're the asshole" recurs in as many episodes as a Gatorade read does. The
second signal separates them: ad copy carries promotional register (a price, a
URL, a discount code, "sponsored by", "terms apply") and catchphrases do not.

The model's `advertisement` relevance only ever marks ads it also found health
content in, so a Dell laptop read is a real ad break that the model correctly
left unlabeled. Recall against the model's spans is therefore the meaningful
agreement number; the extra spans are assessed by their own promotional
register rather than counted as errors.
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
MIN_WORDS = 6
BRIDGE = 1

PROMO = re.compile(
    r"\b("
    r"sponsor|sponsored|sponsors|promo|promo code|coupon|discount|offer|offers"
    r"|deal|deals|sale|save \d|\d+% off|percent off|free trial|free shipping"
    r"|terms apply|terms and conditions|restrictions apply|limited time"
    r"|available at|visit |go to |head to |check out |sign up|subscribe"
    r"|dot com|\.com|dot co|slash |use code|code |link in|shop |order now"
    r"|buy |purchase|in stores|at target|at walmart|at safeway|at costco"
    r"|starting at|\$\d|only \$|per month|a month|money back|guarantee"
    r"|brought to you by|this episode is|our partner|ad break|advertisement"
    r")",
    re.I,
)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


def main() -> None:
    min_eps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    promo_seed = "--no-promo" not in sys.argv

    db = sqlite3.connect(FULLRUN / "labels.sqlite")
    labeled = {
        wid: json.loads(rj)
        for wid, rj in db.execute("SELECT window_id, result_json FROM window_labels")
    }

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

    tp = fp = fn = 0
    pred_total = ref_total = 0
    extra_promo = extra_plain = 0
    seeds_kept = 0
    examples: list[str] = []

    for obj in windows:
        units = obj["units"]
        rep = [
            i for i, u in enumerate(units)
            if len(norm(u["text"]).split()) >= MIN_WORDS and norm(u["text"]) in repeated
        ]
        # Group repeated units into runs, then keep only runs whose own text
        # reads as an ad. A catchphrase run has no promotional register.
        runs: list[tuple[int, int]] = []
        if rep:
            s = p = rep[0]
            for i in rep[1:]:
                if i - p <= BRIDGE + 1:
                    p = i
                    continue
                runs.append((s, p))
                s = p = i
            runs.append((s, p))

        pred: set[int] = set()
        for a, b in runs:
            text = " ".join(u["text"] for u in units[a : b + 1])
            if promo_seed and not PROMO.search(text):
                continue
            seeds_kept += 1
            # Grow through neighbouring units that also read promotionally, so a
            # read is captured whole rather than only its repeated sentence.
            lo, hi = a, b
            while lo > 0 and PROMO.search(units[lo - 1]["text"]):
                lo -= 1
            while hi + 1 < len(units) and PROMO.search(units[hi + 1]["text"]):
                hi += 1
            pred.update(range(lo, hi + 1))

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
        pred_total += len(pred)
        ref_total += len(ref)
        for i in pred - ref:
            if PROMO.search(units[i]["text"]):
                extra_promo += 1
            else:
                extra_plain += 1
        if pred - ref and len(examples) < 5:
            examples.append(" ".join(units[i]["text"] for i in sorted(pred - ref))[:140])

    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    mode = "repetition + promo register" if promo_seed else "repetition only"
    print(f"=== {mode}, >= {min_eps} episodes ===")
    print(f"  seeds kept: {seeds_kept}")
    print(f"  predicted ad units {pred_total:,}   model health-ad units {ref_total:,}")
    print(f"  recall of model ad spans: {rec:.1%}   overlap precision: {prec:.1%}")
    extra = extra_promo + extra_plain
    if extra:
        print(f"  units predicted beyond the model's spans: {extra:,}"
              f" -- {extra_promo/extra:.0%} carry promotional register")
    for e in examples:
        print(f"    + {e}")


if __name__ == "__main__":
    main()
