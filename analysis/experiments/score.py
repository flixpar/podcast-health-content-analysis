#!/usr/bin/env python3
"""Score one labeling variant against the pilot reference labels.

The reference is the existing `high`-effort output, which is a comparison
point rather than ground truth: a variant that finds something the reference
missed scores as a disagreement, not an error. Both directions are reported so
the two cases stay distinguishable.
"""

from __future__ import annotations

import collections
import json
import sqlite3
import sys
from pathlib import Path


def spans(result: dict, key: str = "detections") -> list[dict]:
    return result.get(key) or []


def unit_no(unit_id: str) -> int:
    digits = "".join(ch for ch in unit_id if ch.isdigit())
    return int(digits) if digits else -1


def overlaps(a: dict, b: dict) -> bool:
    a0, a1 = unit_no(a["start_unit_id"]), unit_no(a["end_unit_id"])
    b0, b1 = unit_no(b["start_unit_id"]), unit_no(b["end_unit_id"])
    return not (a1 < b0 or a0 > b1)


def ad_units(result: dict) -> set[int]:
    covered: set[int] = set()
    for d in spans(result):
        if d.get("relevance") == "advertisement":
            covered.update(range(unit_no(d["start_unit_id"]), unit_no(d["end_unit_id"]) + 1))
    return covered


def match_rate(ref: list[dict], var: list[dict]) -> tuple[int, int]:
    """How many reference detections a variant detection covers."""
    hit = 0
    for r in ref:
        rl = set(r["label_ids"])
        if any(rl & set(v["label_ids"]) and overlaps(r, v) for v in var):
            hit += 1
    return hit, len(ref)


def main() -> None:
    run_dir = Path(sys.argv[1])
    ref_path = Path(sys.argv[2])
    label = sys.argv[3] if len(sys.argv) > 3 else run_dir.name

    reference = json.loads(ref_path.read_text())
    db = sqlite3.connect(run_dir / "labels.sqlite")
    got = {
        wid: json.loads(rj)
        for wid, rj in db.execute("SELECT window_id, result_json FROM window_labels")
    }

    # Token + request accounting: usage is per request, shared by every window
    # in the batch, so dedupe by response_id before summing.
    seen: dict[str, dict] = {}
    batch_of: collections.Counter[str] = collections.Counter()
    for rid, uj in db.execute("SELECT response_id, usage_json FROM window_labels"):
        if rid:
            batch_of[rid] += 1
            if rid not in seen and uj:
                seen[rid] = json.loads(uj)
    out_tokens = sum(u.get("output_tokens", 0) for u in seen.values())
    in_tokens = sum(u.get("input_tokens", 0) for u in seen.values())

    failures = db.execute("SELECT kind, COUNT(*) FROM failures GROUP BY 1").fetchall()

    per_stratum: dict[str, dict] = collections.defaultdict(
        lambda: {
            "windows": 0,
            "labeled": 0,
            "ref_sub": 0,
            "hit_sub": 0,
            "var_sub": 0,
            "hit_back": 0,
            "ref_claims": 0,
            "var_claims": 0,
            "ad_i": 0,
            "ad_u": 0,
        }
    )

    for wid, meta in reference.items():
        st = per_stratum[meta["stratum"]]
        st["windows"] += 1
        ref = meta["result"]
        var = got.get(wid)
        ref_sub = [d for d in spans(ref) if d["relevance"] == "substantive"]
        st["ref_sub"] += len(ref_sub)
        st["ref_claims"] += len(spans(ref, "verification_candidates"))
        if var is None:
            continue
        st["labeled"] += 1
        var_sub = [d for d in spans(var) if d["relevance"] == "substantive"]
        st["var_sub"] += len(var_sub)
        st["var_claims"] += len(spans(var, "verification_candidates"))
        hit, _ = match_rate(ref_sub, var_sub)
        st["hit_sub"] += hit
        back, _ = match_rate(var_sub, ref_sub)
        st["hit_back"] += back
        ra, va = ad_units(ref), ad_units(var)
        st["ad_i"] += len(ra & va)
        st["ad_u"] += len(ra | va)

    total = collections.Counter()
    for st in per_stratum.values():
        for k, v in st.items():
            total[k] += v

    def pct(a: int, b: int) -> float:
        return round(100.0 * a / b, 1) if b else 0.0

    report = {
        "variant": label,
        "windows_in_slice": len(reference),
        "windows_labeled": len(got),
        "unresolved": {k: v for k, v in failures},
        "requests": len(seen),
        "batch_sizes": dict(collections.Counter(batch_of.values())),
        "output_tokens_total": out_tokens,
        "input_tokens_total": in_tokens,
        "output_tokens_per_window": round(out_tokens / max(len(got), 1)),
        "input_tokens_per_window": round(in_tokens / max(len(got), 1)),
        "substantive_recall_vs_reference_pct": pct(total["hit_sub"], total["ref_sub"]),
        "reference_recall_vs_variant_pct": pct(total["hit_back"], total["var_sub"]),
        "substantive_detections": {
            "reference": total["ref_sub"],
            "variant": total["var_sub"],
        },
        "claims": {"reference": total["ref_claims"], "variant": total["var_claims"]},
        "ad_unit_jaccard_pct": pct(total["ad_i"], total["ad_u"]),
        "per_stratum": {
            name: {
                "labeled": f"{st['labeled']}/{st['windows']}",
                "sub_recall_pct": pct(st["hit_sub"], st["ref_sub"]),
                "sub_det": f"{st['var_sub']} vs {st['ref_sub']} ref",
                "claims": f"{st['var_claims']} vs {st['ref_claims']} ref",
                "ad_jaccard_pct": pct(st["ad_i"], st["ad_u"]),
            }
            for name, st in sorted(per_stratum.items())
        },
    }
    manifest = run_dir / "label_manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
        report["isolation"] = {
            "batches_isolated": m.get("batches_isolated_this_invocation"),
            "windows_isolated": m.get("windows_isolated_this_invocation"),
            "recovered": m.get("windows_recovered_by_isolation"),
            "by_kind": m.get("batches_isolated_by_kind"),
        }
    timing = run_dir / "timing.json"
    if timing.exists():
        report["timing"] = json.loads(timing.read_text())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
