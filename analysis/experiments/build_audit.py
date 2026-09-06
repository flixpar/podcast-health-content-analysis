#!/usr/bin/env python3
"""Assemble a blinded audit set from where two runs disagree.

The throughput sweep can only say that `high` finds more than `medium`; it
cannot say whether the extra detections are recall or noise, because its only
yardstick is another model run. That question needs a reader.

Three arms, shuffled together and stripped of their provenance so the reader
cannot infer the answer from the source:
  high_only   -- found by eff-high, matched by neither the reference nor medium
  shared      -- found by eff-high AND the reference (a positive control: if the
                 audit does not rate these highly, the audit is miscalibrated
                 and the high_only rate cannot be read)
  medium_only -- found by medium, missed by high (the reverse direction)
"""

from __future__ import annotations

import io, json, random, sqlite3, sys
from pathlib import Path

import zstandard as zstd

S = Path(sys.argv[1])
SEED = 20260906
PER_ARM = 30


def load(run):
    db = sqlite3.connect(S / "runs" / run / "labels.sqlite")
    return {w: json.loads(r) for w, r in db.execute(
        "SELECT window_id, result_json FROM window_labels")}


def unit_no(uid): 
    d = "".join(c for c in uid if c.isdigit())
    return int(d) if d else -1


def sub(res):
    return [d for d in (res.get("detections") or []) if d["relevance"] == "substantive"]


def matches(a, b):
    """Same label and overlapping span -- the scorer's own matching rule."""
    a0, a1 = unit_no(a["start_unit_id"]), unit_no(a["end_unit_id"])
    b0, b1 = unit_no(b["start_unit_id"]), unit_no(b["end_unit_id"])
    return bool(set(a["label_ids"]) & set(b["label_ids"])) and not (a1 < b0 or a0 > b1)


def main():
    high, med = load("eff-high"), load("eff-medium")
    ref = {k: v["result"] for k, v in
           json.loads((S / "eval120" / "reference.json").read_text()).items()}
    taxonomy = {l["label_id"]: l["name"] for l in
                json.loads((S / "eval" / "taxonomy.json").read_text())["labels"]}

    windows = {}
    with open(S / "eval120" / "windows.jsonl.zst", "rb") as fh:
        st = io.TextIOWrapper(zstd.ZstdDecompressor().stream_reader(fh), encoding="utf-8")
        for line in st:
            o = json.loads(line)
            windows[o["window_id"]] = o

    arms = {"high_only": [], "shared": [], "medium_only": []}
    for wid in windows:
        h, m, r = sub(high.get(wid, {})), sub(med.get(wid, {})), sub(ref.get(wid, {}))
        for d in h:
            if any(matches(d, x) for x in r):
                arms["shared"].append((wid, d))
            elif not any(matches(d, x) for x in m):
                arms["high_only"].append((wid, d))
        for d in m:
            if not any(matches(d, x) for x in h):
                arms["medium_only"].append((wid, d))

    print({k: len(v) for k, v in arms.items()}, file=sys.stderr)

    rng = random.Random(SEED)
    items = []
    for arm, pool in arms.items():
        rng.shuffle(pool)
        for wid, d in pool[:PER_ARM]:
            units = windows[wid]["units"]
            idx = {u["unit_id"]: i for i, u in enumerate(units)}
            a, b = idx.get(d["start_unit_id"]), idx.get(d["end_unit_id"])
            if a is None or b is None:
                continue
            items.append({
                "arm": arm,
                "window_id": wid,
                "span_text": " ".join(u["text"] for u in units[a:b + 1]),
                "full_window": " ".join(u["text"] for u in units),
                "labels": [taxonomy.get(l, l) for l in d["label_ids"]],
                "label_ids": d["label_ids"],
                "relevance": d["relevance"],
                "discourse_role": d.get("discourse_role"),
                "summary": d.get("summary"),
                "evidence_quote": d.get("evidence_quote"),
                "confidence": d.get("confidence"),
            })
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["item_id"] = f"D{i:03d}"
    (S / "audit_items.json").write_text(json.dumps(items, indent=2))
    print(f"wrote {len(items)} items")


if __name__ == "__main__":
    main()
