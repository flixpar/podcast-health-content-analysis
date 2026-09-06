#!/usr/bin/env python3
"""Compare two labeling runs to each other, per stratum.

Scoring every variant against the pilot reference conflates two changes: the
reference was produced by a different prompt and a different validator, so a
variant that differs from it may be differing about effort or about the
prompt. Two runs of the same code differ only in the thing that was varied,
which is the only comparison that answers "what does effort buy".

Direction matters and both are reported. `a_covered_by_b` is how much of A's
output B also found; if B is a clean subset of A, B's own coverage by A is
near total and it is simply sparser. If neither direction is high, the two
disagree rather than one being a reduction of the other.
"""

from __future__ import annotations

import collections
import json
import sqlite3
import sys
from pathlib import Path


def unit_no(unit_id: str) -> int:
    digits = "".join(ch for ch in unit_id if ch.isdigit())
    return int(digits) if digits else -1


def spans(result: dict, key: str = "detections") -> list[dict]:
    return result.get(key) or []


def overlaps(a: dict, b: dict) -> bool:
    a0, a1 = unit_no(a["start_unit_id"]), unit_no(a["end_unit_id"])
    b0, b1 = unit_no(b["start_unit_id"]), unit_no(b["end_unit_id"])
    return not (a1 < b0 or a0 > b1)


def covered(src: list[dict], dst: list[dict]) -> int:
    return sum(
        1 for s in src
        if any(set(s["label_ids"]) & set(d["label_ids"]) and overlaps(s, d) for d in dst)
    )


def ad_units(result: dict) -> set[int]:
    out: set[int] = set()
    for d in spans(result):
        if d.get("relevance") == "advertisement":
            out.update(range(unit_no(d["start_unit_id"]), unit_no(d["end_unit_id"]) + 1))
    return out


def load(run_dir: Path) -> dict[str, dict]:
    db = sqlite3.connect(run_dir / "labels.sqlite")
    return {
        wid: json.loads(rj)
        for wid, rj in db.execute("SELECT window_id, result_json FROM window_labels")
    }


def relevance_report(runs: dict[str, dict[str, dict]]) -> dict:
    """Does the model set `relevance` on claims, and does it agree with spans?

    The field exists so verification can be pointed at editorial content alone.
    That only works if the value is right, so it is checked against the thing
    it should agree with: the relevance of the detection span the claim sits
    inside. A claim in an ad span that calls itself substantive is the failure
    mode that would put sponsor copy back into the verification queue.
    """
    out: dict[str, dict] = {}
    for name, got in runs.items():
        tally: collections.Counter[str] = collections.Counter()
        for result in got.values():
            ads = ad_units(result)
            for claim in spans(result, "verification_candidates"):
                rel = claim.get("relevance")
                if rel is None:
                    tally["missing_field"] += 1
                    continue
                tally[f"claim_{rel}"] += 1
                lo, hi = unit_no(claim["start_unit_id"]), unit_no(claim["end_unit_id"])
                in_ad = bool(set(range(lo, hi + 1)) & ads)
                if in_ad and rel == "advertisement":
                    tally["agree_ad"] += 1
                elif in_ad:
                    tally["in_ad_span_but_not_marked"] += 1
                elif rel == "advertisement":
                    tally["marked_ad_outside_ad_span"] += 1
                else:
                    tally["agree_editorial"] += 1
        total = sum(v for k, v in tally.items() if k.startswith("claim_")) + tally["missing_field"]
        agreed = tally["agree_ad"] + tally["agree_editorial"]
        out[name] = {
            "claims": total,
            "by_relevance": {
                k.removeprefix("claim_"): v for k, v in sorted(tally.items())
                if k.startswith("claim_")
            },
            "missing_field": tally["missing_field"],
            "pct_advertisement": round(100.0 * tally["claim_advertisement"] / max(total, 1), 1),
            "agreement_with_span_relevance_pct": round(100.0 * agreed / max(total, 1), 1),
            "in_ad_span_but_not_marked": tally["in_ad_span_but_not_marked"],
            "marked_ad_outside_ad_span": tally["marked_ad_outside_ad_span"],
        }
    return out


def main() -> None:
    a_dir, b_dir = Path(sys.argv[1]), Path(sys.argv[2])
    strata = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else {}
    a, b = load(a_dir), load(b_dir)
    shared = sorted(set(a) & set(b))

    def pct(x: int, y: int) -> float:
        return round(100.0 * x / y, 1) if y else 0.0

    per: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for wid in shared:
        st = per[strata.get(wid, {}).get("stratum", "all")]
        asub = [d for d in spans(a[wid]) if d["relevance"] == "substantive"]
        bsub = [d for d in spans(b[wid]) if d["relevance"] == "substantive"]
        st["windows"] += 1
        st["a_sub"] += len(asub)
        st["b_sub"] += len(bsub)
        st["a_in_b"] += covered(asub, bsub)
        st["b_in_a"] += covered(bsub, asub)
        st["a_claims"] += len(spans(a[wid], "verification_candidates"))
        st["b_claims"] += len(spans(b[wid], "verification_candidates"))
        aa, ba = ad_units(a[wid]), ad_units(b[wid])
        st["ad_i"] += len(aa & ba)
        st["ad_u"] += len(aa | ba)

    tot = collections.Counter()
    for st in per.values():
        tot.update(st)

    print(json.dumps({
        "a": a_dir.name, "b": b_dir.name,
        "windows_compared": len(shared),
        "only_in_a": len(set(a) - set(b)), "only_in_b": len(set(b) - set(a)),
        "substantive_detections": {"a": tot["a_sub"], "b": tot["b_sub"]},
        "a_covered_by_b_pct": pct(tot["a_in_b"], tot["a_sub"]),
        "b_covered_by_a_pct": pct(tot["b_in_a"], tot["b_sub"]),
        "claims": {"a": tot["a_claims"], "b": tot["b_claims"]},
        "ad_unit_jaccard_pct": pct(tot["ad_i"], tot["ad_u"]),
        "per_stratum": {
            name: {
                "windows": st["windows"],
                "sub_det": f"a={st['a_sub']} b={st['b_sub']}",
                "a_covered_by_b_pct": pct(st["a_in_b"], st["a_sub"]),
                "b_covered_by_a_pct": pct(st["b_in_a"], st["b_sub"]),
                "claims": f"a={st['a_claims']} b={st['b_claims']}",
                "ad_jaccard_pct": pct(st["ad_i"], st["ad_u"]),
            }
            for name, st in sorted(per.items())
        },
        "claim_relevance": relevance_report({a_dir.name: a, b_dir.name: b}),
    }, indent=2))


if __name__ == "__main__":
    main()
