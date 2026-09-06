#!/usr/bin/env python3
"""Build a slice of the windows the pilot could only call other_health_topic.

The seven topics added to the taxonomy were chosen from the pilot's visible
gaps, so the test of whether they earn their place is not a random slice --
where they are correctly never used -- but the windows that actually fell
through. If the added labels are right, these windows get a specific topic;
if they are decoration, they stay other_health_topic.
"""

from __future__ import annotations

import collections, hashlib, io, json, random, sqlite3, sys
from pathlib import Path

import zstandard as zstd

FULLRUN = Path("outputs/fullrun")
OUT = Path(sys.argv[1])
TAXONOMY = Path(sys.argv[2])
N = int(sys.argv[3]) if len(sys.argv) > 3 else 120
SEED = 20260906


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(FULLRUN / "labels.sqlite")
    hits: dict[str, dict] = {}
    for wid, eid, rj in db.execute(
        "SELECT window_id, episode_id, result_json FROM window_labels"
    ):
        r = json.loads(rj)
        n = sum(
            1 for d in (r.get("detections") or [])
            if "topic:other_health_topic" in d["label_ids"]
        )
        if n:
            hits[wid] = {"episode_id": eid, "result": r, "n_other": n}
    print(f"pilot windows using other_health_topic: {len(hits)}")

    rng = random.Random(SEED)
    chosen = sorted(hits)
    rng.shuffle(chosen)
    chosen = set(chosen[:N])

    kept = []
    with open(FULLRUN / "windows.jsonl.zst", "rb") as fh:
        stream = io.TextIOWrapper(zstd.ZstdDecompressor().stream_reader(fh), encoding="utf-8")
        for line in stream:
            obj = json.loads(line)
            if obj["window_id"] in chosen:
                kept.append(obj)
                if len(kept) == len(chosen):
                    break
    print(f"recovered {len(kept)} window payloads")

    windows_path = OUT / "windows.jsonl.zst"
    with open(windows_path, "wb") as fh, zstd.ZstdCompressor(level=10).stream_writer(fh) as w:
        for obj in kept:
            w.write((json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))

    tax = json.loads(TAXONOMY.read_text())
    src = json.loads((FULLRUN / "prepare_manifest.json").read_text())
    (OUT / "prepare_manifest.json").write_text(json.dumps({
        **src,
        "windows": len(kept),
        "episodes_prepared": len({o["episode_id"] for o in kept}),
        "windows_path": str(windows_path.resolve()),
        "windows_sha256": hashlib.sha256(windows_path.read_bytes()).hexdigest(),
        "taxonomy_path": str(TAXONOMY.resolve()),
        "taxonomy_sha256": tax["taxonomy_sha256"],
        "eval_slice": True, "eval_seed": SEED,
    }, indent=2))
    (OUT / "reference.json").write_text(json.dumps({
        w: {"stratum": "other_health", "episode_id": hits[w]["episode_id"],
            "result": hits[w]["result"]}
        for w in chosen
    }, indent=2))
    n_other = sum(hits[w]["n_other"] for w in chosen)
    print(f"reference other_health_topic detections in slice: {n_other}")


if __name__ == "__main__":
    main()
