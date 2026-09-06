#!/usr/bin/env python3
"""Build a fixed, stratified evaluation slice from the fullrun pilot.

The pilot slice is ~70% zero-yield, so a random draw measures almost nothing.
Three strata of 100 windows each: health-dense (from top-decile substantive
episodes), ad-heavy, and zero-yield. The existing `high` labels for those
windows are saved as a reference -- not gold, but the thing every variant is
compared against.
"""

from __future__ import annotations

import collections
import hashlib
import io
import json
import random
import sqlite3
import sys
from pathlib import Path

import zstandard as zstd

FULLRUN = Path("outputs/fullrun")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "eval")
PER_STRATUM = 100
SEED = 20260906


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(FULLRUN / "labels.sqlite")

    rows = db.execute(
        "SELECT window_id, episode_id, result_json FROM window_labels"
    ).fetchall()

    # Episode-level substantive counts, to find the health-dense decile.
    ep_sub: collections.Counter[int] = collections.Counter()
    per_window: dict[str, dict] = {}
    for wid, eid, rj in rows:
        r = json.loads(rj)
        sub = sum(
            1 for d in r.get("detections") or [] if d["relevance"] == "substantive"
        )
        ad = sum(
            1 for d in r.get("detections") or [] if d["relevance"] == "advertisement"
        )
        ep_sub[eid] += sub
        per_window[wid] = {
            "episode_id": eid,
            "sub": sub,
            "ad": ad,
            "claims": len(r.get("verification_candidates") or []),
            "det": len(r.get("detections") or []),
            "result": r,
        }

    ranked = [e for e, _ in ep_sub.most_common()]
    dense_eps = set(ranked[: max(1, len(ranked) // 10)])

    dense = [w for w, s in per_window.items() if s["episode_id"] in dense_eps and s["sub"] > 0]
    ad_heavy = [w for w, s in per_window.items() if s["ad"] > 0]
    zero = [w for w, s in per_window.items() if s["det"] == 0 and s["claims"] == 0]

    rng = random.Random(SEED)
    # Disjoint strata, in priority order, so a window is only counted once.
    chosen: dict[str, str] = {}

    def take(pool: list[str], name: str) -> None:
        avail = sorted(w for w in pool if w not in chosen)
        rng.shuffle(avail)
        for w in avail[:PER_STRATUM]:
            chosen[w] = name

    take(dense, "health_dense")
    take(ad_heavy, "ad_heavy")
    take(zero, "zero_yield")

    print(f"strata: {dict(collections.Counter(chosen.values()))}")
    print(f"pool sizes: dense={len(dense)} ad={len(ad_heavy)} zero={len(zero)}")

    # Pull the window payloads out of the corpus file, preserving corpus order.
    kept: list[dict] = []
    with open(FULLRUN / "windows.jsonl.zst", "rb") as fh:
        stream = io.TextIOWrapper(
            zstd.ZstdDecompressor().stream_reader(fh), encoding="utf-8"
        )
        for line in stream:
            obj = json.loads(line)
            if obj["window_id"] in chosen:
                kept.append(obj)
                if len(kept) == len(chosen):
                    break
    print(f"recovered {len(kept)} window payloads")

    windows_path = OUT / "windows.jsonl.zst"
    cctx = zstd.ZstdCompressor(level=10)
    with open(windows_path, "wb") as fh, cctx.stream_writer(fh) as writer:
        for obj in kept:
            writer.write(
                (json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n").encode(
                    "utf-8"
                )
            )

    digest = hashlib.sha256(windows_path.read_bytes()).hexdigest()
    src_manifest = json.loads((FULLRUN / "prepare_manifest.json").read_text())
    manifest = {
        **src_manifest,
        "windows": len(kept),
        "episodes_prepared": len({o["episode_id"] for o in kept}),
        "windows_path": str(windows_path.resolve()),
        "windows_sha256": digest,
        "eval_slice": True,
        "eval_seed": SEED,
    }
    (OUT / "prepare_manifest.json").write_text(json.dumps(manifest, indent=2))

    reference = {
        w: {
            "stratum": chosen[w],
            "episode_id": per_window[w]["episode_id"],
            "result": per_window[w]["result"],
        }
        for w in chosen
    }
    (OUT / "reference.json").write_text(json.dumps(reference, indent=2))

    words = sum(o["word_count"] for o in kept)
    print(f"wrote {windows_path} ({windows_path.stat().st_size/1e6:.1f} MB), {words:,} words")
    print(f"sha256 {digest[:16]}...")


if __name__ == "__main__":
    main()
