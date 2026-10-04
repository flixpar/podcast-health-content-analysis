"""Evaluate window screens (filters in front of the labeler).

A screen gives every window a score; windows below a threshold are not sent to
the labeler and get an empty result. What matters is (a) the share of windows
that pass, read on real corpus traffic, and (b) how much of the labeled content
survives, read on the benchmark gold and on a corpus sample a full labeler
annotated.

Scores come from `scores/<screen>.jsonl` files ({"window_id", "score"}), written
by the screen producers (keyword matchers here; DeepSeek, Clef-flash and the
learned screens elsewhere).

    python exp/screens.py keyword --lexicon exp/lexicon-llm-v3.json --name kw-llm --windows <corpus windows> --bench v2
    python exp/screens.py eval --screens kw-llm deepseek-screen clef-flash --reference-run exp/corpus/v8-ref
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "exp"))
from analysis import topic_labeling as tl  # noqa: E402

SCORES = REPO / "exp/scores"
HEALTH_AXES = ("topic", "narrative")


def write_scores(name: str, scores: dict[str, float]) -> None:
    SCORES.mkdir(exist_ok=True)
    with open(SCORES / f"{name}.jsonl", "w") as out:
        for window_id, score in scores.items():
            out.write(json.dumps({"window_id": window_id, "score": score}) + "\n")


def read_scores(name: str) -> dict[str, float]:
    out = {}
    for line in open(SCORES / f"{name}.jsonl"):
        row = json.loads(line)
        out[row["window_id"]] = float(row["score"])
    return out


def bench_windows(bench: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in open(REPO / f"benchmark/{bench}/items.jsonl")]


_LEX: Any = None
_KEEP: set[str] = set()


def _init(lexicon_path: str, keep: set[str]) -> None:
    global _LEX, _KEEP
    from keywords import Lexicon

    _LEX, _KEEP = Lexicon.load(Path(lexicon_path)), keep


def _count(window: dict[str, Any]) -> tuple[str, float]:
    return window["window_id"], float(sum(1 for u in window["units"] if any(lab in _KEEP for lab, _ in _LEX.match(u["text"]))))


def keyword_scores(windows, lexicon_path: str, axes=HEALTH_AXES, bench="v3") -> dict[str, float]:
    """Number of units with a hit on a topic or narrative label."""
    from multiprocessing import Pool

    taxonomy = json.loads((REPO / f"benchmark/{bench}/taxonomy.json").read_text())
    keep = {l["label_id"] for l in taxonomy["labels"] if l["axis"] in axes}
    with Pool(48, initializer=_init, initargs=(lexicon_path, keep)) as pool:
        return dict(pool.imap_unordered(_count, windows, chunksize=8))


def lexv2_scores(windows) -> dict[str, float]:
    """The fast lexical scan's lexicon (benchmark/lexicon-v2.json), health sections."""
    from analysis.benchmark.lexicon import Matcher

    m = Matcher(json.loads((REPO / "benchmark/lexicon-v2.json").read_text()))
    out = {}
    for w in windows:
        n = 0
        for u in w["units"]:
            hits = m.match(u["text"])
            if any(h[0] in ("topics", "narratives", "products") for h in hits):
                n += 1
        out[w["window_id"]] = float(n)
    return out


# --------------------------------------------------------------------------
# What a screen keeps
# --------------------------------------------------------------------------


def gold_atoms(bench: str) -> dict[str, list[dict[str, Any]]]:
    items = {i["item_id"]: i["window_id"] for i in bench_windows(bench)}
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in open(REPO / f"benchmark/{bench}/gold.jsonl"):
        g = json.loads(line)
        if g["tier"] not in ("required", "acceptable"):
            continue
        rel = g.get("votes", {}).get("relevance") or {}
        relevance = max(rel, key=rel.get) if rel else None
        out[items[g["item_id"]]].append({"kind": g["kind"], "axis": g.get("axis"), "relevance": relevance, "label": g.get("label")})
    return out


def run_atoms(run_dir: Path, repeat: int = 0) -> dict[str, list[dict[str, Any]]]:
    db = Path(run_dir) / f"repeat_{repeat}/labels.sqlite"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out: dict[str, list[dict[str, Any]]] = {}
    for window_id, result_json in con.execute("SELECT window_id, result_json FROM window_labels"):
        r = json.loads(result_json)
        atoms = []
        for d in r.get("detections", []):
            for label in d["label_ids"]:
                atoms.append({"kind": "detection", "axis": d.get("axis") or label.split(":")[0], "relevance": d.get("relevance"), "label": label})
        atoms += [{"kind": "claim", "axis": None, "relevance": c.get("relevance"), "label": None} for c in r.get("verification_candidates", [])]
        atoms += [{"kind": "product", "axis": None, "relevance": None, "label": None} for _ in r.get("product_mentions", [])]
        out[window_id] = atoms
    return out


CLASSES = {
    "topic (substantive)": lambda a: a["kind"] == "detection" and a["axis"] == "topic" and a["relevance"] == "substantive",
    "topic (passing)": lambda a: a["kind"] == "detection" and a["axis"] == "topic" and a["relevance"] == "passing",
    "topic (ad)": lambda a: a["kind"] == "detection" and a["axis"] == "topic" and a["relevance"] == "advertisement",
    "narrative": lambda a: a["kind"] == "detection" and a["axis"] == "narrative",
    "frame+evidence": lambda a: a["kind"] == "detection" and a["axis"] in ("frame", "evidence"),
    "claim": lambda a: a["kind"] == "claim",
    "product": lambda a: a["kind"] == "product",
    "all atoms": lambda a: True,
}


def auroc(pos: list[float], neg: list[float]) -> float | None:
    if not pos or not neg:
        return None
    ranked = sorted([(s, 1) for s in pos] + [(s, 0) for s in neg])
    # Average ranks for ties.
    rank_sum, i, n = 0.0, 0, len(ranked)
    while i < n:
        j = i
        while j + 1 < n and ranked[j + 1][0] == ranked[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        rank_sum += avg * sum(1 for k in range(i, j + 1) if ranked[k][1])
        i = j + 1
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def retention(scores: dict[str, float], atoms: dict[str, list[dict[str, Any]]], threshold: float, windows: list[str]) -> dict[str, Any]:
    passed = {w for w in windows if scores.get(w, 0.0) >= threshold}
    out: dict[str, Any] = {"pass_rate": len(passed) / len(windows) if windows else None}
    for name, test in CLASSES.items():
        total = sum(1 for w in windows for a in atoms.get(w, []) if test(a))
        kept = sum(1 for w in passed for a in atoms.get(w, []) if test(a))
        out[name] = (kept / total if total else None, total)
    return out


def describe(name: str, scores: dict[str, float], atoms, windows: list[str], thresholds: list[float]) -> list[str]:
    substantive = lambda w: any(CLASSES["topic (substantive)"](a) or a["kind"] == "claim" for a in atoms.get(w, []))  # noqa: E731
    pos = [scores.get(w, 0.0) for w in windows if substantive(w)]
    neg = [scores.get(w, 0.0) for w in windows if not atoms.get(w)]
    au = auroc(pos, neg)
    lines = [f"### {name}  (AUROC substantive-vs-empty {au:.3f})" if au is not None else f"### {name}"]
    cols = list(CLASSES)
    lines.append("| threshold | pass | " + " | ".join(cols) + " |")
    lines.append("| --- | --- | " + " | ".join("---" for _ in cols) + " |")
    for t in thresholds:
        r = retention(scores, atoms, t, windows)
        cells = [f"{r[c][0]:.3f}" if r[c][0] is not None else "-" for c in cols]
        lines.append(f"| {t:g} | {r['pass_rate']:.3f} | " + " | ".join(cells) + " |")
    totals = retention(scores, atoms, 0, windows)
    lines.append("| (atoms) | | " + " | ".join(str(totals[c][1]) for c in cols) + " |")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keyword")
    k.add_argument("--name", required=True)
    k.add_argument("--lexicon", help="exp/keywords.py lexicon; omit for benchmark/lexicon-v2.json")
    k.add_argument("--bench", default="v3")
    k.add_argument("--windows", help="corpus windows jsonl.zst")
    k.add_argument("--ids-file")
    e = sub.add_parser("eval")
    e.add_argument("--screens", nargs="+", required=True)
    e.add_argument("--bench", default="v2")
    e.add_argument("--strata", nargs="*", default=["health_dense", "mixed", "null", "ad_read", "discourse"])
    e.add_argument("--reference-run", help="corpus labels to measure retention against")
    e.add_argument("--corpus-ids", help="the corpus windows to evaluate (default: every window in the reference run)")
    e.add_argument("--thresholds", nargs="*")
    args = parser.parse_args()

    if args.cmd == "keyword":
        windows = bench_windows("v2")
        if args.windows:
            windows += list(tl.iter_jsonl(Path(args.windows)))
            if args.ids_file:
                wanted = set(Path(args.ids_file).read_text().split()) | {w["window_id"] for w in bench_windows("v2")}
                windows = [w for w in windows if w["window_id"] in wanted]
        scores = lexv2_scores(windows) if not args.lexicon else keyword_scores(windows, args.lexicon, bench=args.bench)
        write_scores(args.name, scores)
        print(args.name, len(scores), "windows")
        return 0

    gold = gold_atoms(args.bench)
    items = [i for i in bench_windows(args.bench) if i["stratum"] in args.strata]
    bench_ids = [i["window_id"] for i in items]
    ref = run_atoms(Path(args.reference_run)) if args.reference_run else None
    corpus_ids = None
    if ref is not None:
        corpus_ids = sorted(ref) if not args.corpus_ids else [w for w in Path(args.corpus_ids).read_text().split() if w in ref]
    for name in args.screens:
        spec = name.split("@", 1)
        scores = read_scores(spec[0])
        if args.thresholds:
            thresholds = [float(x) for x in args.thresholds]
        else:
            values = sorted(set(scores.values()))
            thresholds = values if len(values) <= 12 else sorted({values[int(q * (len(values) - 1))] for q in (0, .1, .2, .3, .4, .5, .6, .7, .8, .9)})
        print(f"\n## {name}")
        print("\nBenchmark gold (" + ", ".join(args.strata) + f"; {len(bench_ids)} windows)\n")
        print("\n".join(describe(name, scores, gold, bench_ids, thresholds)))
        if corpus_ids is not None:
            missing = sum(1 for w in corpus_ids if w not in scores)
            print(f"\nCorpus sample ({len(corpus_ids)} windows labeled by the reference run; {missing} without a score count as 0)\n")
            print("\n".join(describe(name, scores, ref, corpus_ids, thresholds)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
