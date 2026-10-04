"""Derived runs, built from existing runs with no requests.

  union    every annotation from any input (repeats of one run, or several runs),
           de-duplicated: detections of one label whose spans overlap merge into
           their union span; claims and products that overlap are kept once
  vote     keep an annotation when at least k inputs have it (same matching)
  gate     a run's results with windows below a screen threshold emptied, to
           measure what a screen in front of the labeler costs end to end

    python exp/combine.py union --out benchmark/v2/runs/v7-union2 benchmark/v2/runs/v7-high-b24k:0 benchmark/v2/runs/v7-high-b24k:1
    python exp/combine.py vote --k 2 --out ... run:0 run:1 run:2
    python exp/combine.py gate --screen kw-lexv2 --threshold 1 --out ... benchmark/v2/runs/v7-high-b24k
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "exp"))
from keywords import write_run  # noqa: E402


def load(spec: str) -> dict[str, dict[str, Any]]:
    path, _, repeat = spec.partition(":")
    db = Path(path) / f"repeat_{repeat or 0}/labels.sqlite"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return {w: json.loads(r) for w, r in con.execute("SELECT window_id, result_json FROM window_labels")}
    finally:
        con.close()


def unit_index(result: dict[str, Any]) -> Any:
    def pos(unit_id: str) -> int:
        return int(unit_id.lstrip("u"))
    return pos


def overlaps(a: dict[str, Any], b: dict[str, Any], pos) -> bool:
    return pos(a["start_unit_id"]) <= pos(b["end_unit_id"]) and pos(b["start_unit_id"]) <= pos(a["end_unit_id"])


def explode_detections(result: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for d in result.get("detections", []):
        for label in d["label_ids"]:
            out.append({**d, "label_ids": [label]})
    return out


def cluster(rows: list[tuple[int, dict[str, Any]]], same, pos) -> list[list[tuple[int, dict[str, Any]]]]:
    """Greedy clusters of (source, row) by `same` and span overlap."""
    clusters: list[list[tuple[int, dict[str, Any]]]] = []
    for source, row in rows:
        for c in clusters:
            if any(same(row, other) and overlaps(row, other, pos) for _, other in c):
                c.append((source, row))
                break
        else:
            clusters.append([(source, row)])
    return clusters


def _words(text: str) -> set[str]:
    return set("".join(ch if ch.isalnum() else " " for ch in text.casefold()).split())


def same_claim(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Overlapping quotes, as the scorer matches claims: half the shorter quote's words shared."""
    wa, wb = _words(a.get("evidence_quote", "")), _words(b.get("evidence_quote", ""))
    return bool(wa and wb) and len(wa & wb) >= 0.5 * min(len(wa), len(wb))


def merge_window(results: list[dict[str, Any] | None], k: int, window_id: str) -> dict[str, Any]:
    present = [r for r in results if r is not None]
    pos = unit_index(present[0]) if present else None
    out: dict[str, Any] = {"window_id": window_id, "detections": [], "verification_candidates": [], "product_mentions": []}
    if not present:
        return out

    def keep(c):
        return len({s for s, _ in c}) >= k

    det = [(s, d) for s, r in enumerate(results) if r for d in explode_detections(r)]
    for c in cluster(det, lambda a, b: a["label_ids"] == b["label_ids"], pos):
        if not keep(c):
            continue
        best = max(c, key=lambda x: x[1].get("confidence", 0))[1]
        if k == 1:
            # Union span: annotators mark the same thing at different extents.
            start = min((x[1] for x in c), key=lambda d: pos(d["start_unit_id"]))["start_unit_id"]
            end = max((x[1] for x in c), key=lambda d: pos(d["end_unit_id"]))["end_unit_id"]
            best = {**best, "start_unit_id": start, "end_unit_id": end}
        out["detections"].append(best)
    claims = [(s, c) for s, r in enumerate(results) if r for c in r.get("verification_candidates", [])]
    for c in cluster(claims, same_claim, pos):
        if keep(c):
            out["verification_candidates"].append(max(c, key=lambda x: x[1].get("confidence", 0))[1])
    prods = [(s, p) for s, r in enumerate(results) if r for p in r.get("product_mentions", [])]
    key = lambda p: "".join(ch for ch in p.get("product_name", "").casefold() if ch.isalnum())  # noqa: E731
    for c in cluster(prods, lambda a, b: key(a) == key(b), pos):
        if keep(c):
            out["product_mentions"].append(max(c, key=lambda x: x[1].get("confidence", 0))[1])
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("union", "vote"):
        p = sub.add_parser(name)
        p.add_argument("inputs", nargs="+", help="run_dir[:repeat]")
        p.add_argument("--out", required=True)
        if name == "vote":
            p.add_argument("--k", type=int, default=2)
    g = sub.add_parser("gate")
    g.add_argument("run")
    g.add_argument("--screen", required=True)
    g.add_argument("--threshold", type=float, required=True)
    g.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.cmd in ("union", "vote"):
        sources = [load(s) for s in args.inputs]
        ids = sorted(set().union(*sources))
        k = 1 if args.cmd == "union" else args.k
        merged = {w: merge_window([s.get(w) for s in sources], k, w) for w in ids}
        write_run(Path(args.out), {"name": Path(args.out).name, "model": "combined", "provider": None, "combine": args.cmd, "k": k, "inputs": args.inputs}, [merged])
        # Cost of a combination is the sum of its inputs' requests.
        with open(Path(args.out) / "repeat_0/attempts.jsonl", "w") as log:
            for spec in args.inputs:
                path, _, repeat = spec.partition(":")
                attempts = Path(path) / f"repeat_{repeat or 0}/attempts.jsonl"
                if attempts.exists():
                    log.write(attempts.read_text())
        return 0

    scores = {}
    for line in open(REPO / f"exp/scores/{args.screen}.jsonl"):
        row = json.loads(line)
        scores[row["window_id"]] = row["score"]
    run = Path(args.run)
    repeats = sorted(run.glob("repeat_*"))
    gated = []
    for repeat in repeats:
        results = load(f"{run}:{repeat.name.split('_')[1]}")
        gated.append({w: (r if scores.get(w, 0.0) >= args.threshold else {"window_id": w, "detections": [], "verification_candidates": [], "product_mentions": []}) for w, r in results.items()})
    manifest = json.loads((run / "run_manifest.json").read_text())
    manifest.update(name=Path(args.out).name, gated_by=args.screen, gate_threshold=args.threshold)
    write_run(Path(args.out), manifest, gated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
