#!/usr/bin/env python3
"""Project a run's token cost onto the whole corpus, reweighted by stratum.

The eval slice is a third zero-yield by construction; the corpus is about
seventy percent. Output tokens track how much there is to annotate, so a slice
average overstates the corpus by two to three times. This weights each
stratum's measured cost by that stratum's real share of the pilot.
"""

from __future__ import annotations

import collections, json, sqlite3, sys
from pathlib import Path

FULLRUN = Path("outputs/fullrun")
CORPUS_WINDOWS = 327_929


def pilot_strata() -> dict[str, float]:
    """Share of pilot windows in each stratum, by the slice's own definitions."""
    db = sqlite3.connect(FULLRUN / "labels.sqlite")
    ep_sub: collections.Counter[int] = collections.Counter()
    per: dict[str, dict] = {}
    for wid, eid, rj in db.execute(
        "SELECT window_id, episode_id, result_json FROM window_labels"
    ):
        r = json.loads(rj)
        dets = r.get("detections") or []
        sub = sum(1 for d in dets if d["relevance"] == "substantive")
        ad = sum(1 for d in dets if d["relevance"] == "advertisement")
        ep_sub[eid] += sub
        per[wid] = {"episode_id": eid, "sub": sub, "ad": ad,
                    "det": len(dets), "claims": len(r.get("verification_candidates") or [])}
    ranked = [e for e, _ in ep_sub.most_common()]
    dense_eps = set(ranked[: max(1, len(ranked) // 10)])
    counts: collections.Counter[str] = collections.Counter()
    for wid, s in per.items():
        if s["episode_id"] in dense_eps and s["sub"] > 0:
            counts["health_dense"] += 1
        elif s["ad"] > 0:
            counts["ad_heavy"] += 1
        elif s["det"] == 0 and s["claims"] == 0:
            counts["zero_yield"] += 1
        else:
            counts["other"] += 1
    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}, counts, total


def main() -> None:
    run_dir = Path(sys.argv[1])
    reference = json.loads(Path(sys.argv[2]).read_text())
    shares, counts, total = pilot_strata()

    db = sqlite3.connect(run_dir / "labels.sqlite")
    size: collections.Counter[str] = collections.Counter()
    usage: dict[str, dict] = {}
    windows: list[tuple[str, str]] = []
    for wid, rid, uj in db.execute(
        "SELECT window_id, response_id, usage_json FROM window_labels"
    ):
        if not rid:
            continue
        size[rid] += 1
        if uj and rid not in usage:
            usage[rid] = json.loads(uj)
        windows.append((wid, rid))

    # A request's tokens are shared by every window in it, so split evenly --
    # mixed-stratum batches otherwise charge one stratum for another's work.
    out_by: collections.Counter[str] = collections.Counter()
    n_by: collections.Counter[str] = collections.Counter()
    for wid, rid in windows:
        st = reference.get(wid, {}).get("stratum", "other")
        u = usage.get(rid) or {}
        out_by[st] += u.get("output_tokens", 0) / size[rid]
        n_by[st] += 1

    print(f"pilot stratum shares (of {total:,} labeled windows):")
    for k in sorted(shares):
        print(f"   {k:14s} {counts[k]:6,d}  {shares[k]:6.1%}")

    print(f"\n{run_dir.name} measured output tokens/window by stratum:")
    per_stratum = {}
    for k in sorted(n_by):
        if n_by[k]:
            per_stratum[k] = out_by[k] / n_by[k]
            print(f"   {k:14s} {n_by[k]:4d} windows  {per_stratum[k]:8,.0f} tok/window")

    # `other` is unmeasured by the slice; it sits between ad_heavy and
    # health_dense in yield, so charge it the ad_heavy rate as the conservative
    # nearer neighbour and say so rather than silently dropping it.
    fallback = per_stratum.get("ad_heavy", 0)
    weighted = sum(shares[k] * per_stratum.get(k, fallback) for k in shares)
    slice_avg = sum(out_by.values()) / max(sum(n_by.values()), 1)
    print(f"\nslice average          {slice_avg:8,.0f} tok/window")
    print(f"corpus-weighted        {weighted:8,.0f} tok/window"
          f"   ({weighted/max(slice_avg,1):.2f}x the slice average)")
    print(f"corpus output tokens   {weighted * CORPUS_WINDOWS/1e9:8.2f}B"
          f"   over {CORPUS_WINDOWS:,} windows")


if __name__ == "__main__":
    main()
