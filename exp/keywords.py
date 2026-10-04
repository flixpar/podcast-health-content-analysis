"""Keyword methods for the v7/v8 labels: lexicons, a keyword labeler, a keyword screen.

Lexicon file: {"source": ..., "labels": {label_id: {"terms": [phrase, ...], "regex": [pattern, ...]}}}.
Terms are literal phrases matched case-insensitively on word boundaries;
regexes are Python patterns (case-insensitive) for co-occurrence cues.

    python exp/keywords.py concepts --bench v3 --out exp/lexicon-concepts-v8.json
    python exp/keywords.py llm --bench v3 --out exp/lexicon-llm-v8.json
    python exp/keywords.py label --bench v2 --lexicon exp/lexicon-llm-v7.json --name kw-llm-v7
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from analysis import topic_labeling as tl  # noqa: E402
from analysis.benchmark.lexicon import trie_regex  # noqa: E402

SPEAKER = re.compile(r"^\s*(?:Speaker\s*\d+|[A-Z][A-Za-z .'-]{1,40})\s*:\s+")


def normalize(text: str) -> str:
    text = SPEAKER.sub("", text)
    return re.sub(r"[^\w\s']+", " ", text.lower()).replace("'", "")


class Lexicon:
    """Compiled per-label matcher; ``match(text)`` yields (label_id, matched term)."""

    def __init__(self, labels: dict[str, dict[str, list[str]]]) -> None:
        self.labels = labels
        by_term: dict[str, set[str]] = defaultdict(set)
        self.regex: list[tuple[re.Pattern[str], str]] = []
        for label, body in labels.items():
            for term in body.get("terms", []):
                key = " ".join(normalize(term).split())
                if len(key) >= 3:
                    by_term[key].add(label)
            for pattern in body.get("regex", []):
                try:
                    self.regex.append((re.compile(pattern, re.I), label))
                except re.error:
                    pass
        self.term_labels = {k: sorted(v) for k, v in by_term.items()}
        terms = sorted(self.term_labels, key=len, reverse=True)
        self.literal = re.compile(r"\b(" + trie_regex(terms) + r")\b") if terms else None

    @classmethod
    def load(cls, path: Path) -> "Lexicon":
        return cls(json.loads(Path(path).read_text())["labels"])

    def match(self, text: str) -> list[tuple[str, str]]:
        hits: list[tuple[str, str]] = []
        norm = " ".join(normalize(text).split())
        if self.literal is not None:
            for m in self.literal.finditer(norm):
                term = m.group(1).strip()
                for label in self.term_labels.get(term, ()):
                    hits.append((label, term))
        for pattern, label in self.regex:
            m = pattern.search(norm)
            if m:
                hits.append((label, m.group(0)[:60]))
        return hits


# --------------------------------------------------------------------------
# Lexicon builders
# --------------------------------------------------------------------------


def taxonomy_of(bench: str) -> dict[str, Any]:
    return json.loads((REPO / f"benchmark/{bench}/taxonomy.json").read_text())


def build_concepts(taxonomy: dict[str, Any]) -> dict[str, Any]:
    """Terms straight from the taxonomy: each label's concepts list (examples)."""
    labels = {}
    for label in taxonomy["labels"]:
        terms = [c for c in label.get("concepts", []) if 3 <= len(c) <= 60]
        labels[label["label_id"]] = {"terms": terms, "regex": []}
    return {"source": "taxonomy concepts", "labels": labels}


LLM_INSTRUCTIONS = """You write keyword lexicons for finding health content in podcast transcripts.

The transcripts are automatic speech recognition output: lowercase-insensitive, punctuation unreliable, numbers often spelled out ("covid nineteen", "five g"), brand and drug names often misspelled the way they sound ("ozempic", "oh zempic", "wegovy", "we go vee").

For each label below, write keyword cues that an automatic matcher can use to find stretches of talk that probably carry that label:
- "terms": 8 to 40 literal phrases (matched case-insensitively on word boundaries, punctuation stripped). Prefer specific words and multi-word phrases a speaker would actually say: names of conditions, drugs, supplements, procedures, products, agencies, people, coined slogans, plus common ASR spellings. Include singular/plural and common inflections as separate terms when they differ.
- "regex": 0 to 6 Python regexes (case-insensitive, run on the lowercased transcript with punctuation removed) for cues that need two ideas together, e.g. "vaccin\\w*.{0,60}autis\\w*". Use these mostly for narratives, frames and evidence signals, which are propositions or rhetoric rather than nouns. Keep gaps at most 80 characters.
- Avoid terms that are common outside health talk (e.g. "shot", "pressure", "doctor" alone, "energy", "drug" alone) unless combined with context in a regex. Precision matters: the cue should usually indicate this label.
- Do not use a term for a label whose definition says that kind of mention belongs elsewhere.

Return JSON: an object with one key per label id, each {"terms": [...], "regex": [...]}."""


def label_groups(taxonomy: dict[str, Any]) -> list[list[dict[str, Any]]]:
    labels = taxonomy["labels"]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for label in labels:
        if label["axis"] == "topic":
            key = label.get("parent") or label["label_id"]
        elif label["axis"] == "narrative":
            key = "narrative:" + str(label.get("family") or label.get("domain") or "all")
        else:
            key = label["axis"]
        groups[key].append(label)
    out = []
    for group in groups.values():
        for i in range(0, len(group), 20):  # keep requests small
            out.append(group[i : i + 20])
    return out


def build_llm(taxonomy: dict[str, Any], concurrency: int = 32, effort: str = "high", budget: int = 8000) -> dict[str, Any]:
    from xlabel import API, MODEL, post  # same server

    def ask(group: list[dict[str, Any]]) -> dict[str, Any]:
        described = [
            {k: label.get(k) for k in ("label_id", "name", "definition", "concepts") if label.get(k)}
            for label in group
        ]
        schema = {
            "type": "object",
            "properties": {
                label["label_id"]: {
                    "type": "object",
                    "properties": {
                        "terms": {"type": "array", "items": {"type": "string"}},
                        "regex": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["terms", "regex"],
                    "additionalProperties": False,
                }
                for label in group
            },
            "required": [label["label_id"] for label in group],
            "additionalProperties": False,
        }
        settings = tl.ModelSettings(max_output_tokens=40000, reasoning_effort=effort, temperature=1.0, top_p=0.95, thinking_token_budget=budget)
        payload = {"model": MODEL, **tl.API_FLAVORS["chat_completions"].payload(
            LLM_INSTRUCTIONS, "Labels:\n" + json.dumps(described, ensure_ascii=False, indent=1), "keyword_lexicon", schema, settings)}
        for _ in range(3):
            try:
                response = post(payload, 3600)
                tl.raise_for_chat_status(response)
                return tl.parse_json_output(tl.extract_chat_output_text(response))
            except Exception as error:  # noqa: BLE001
                print("retry", group[0]["label_id"], error, file=sys.stderr)
        return {}

    labels: dict[str, Any] = {}
    with ThreadPoolExecutor(concurrency) as pool:
        for result in pool.map(ask, label_groups(taxonomy)):
            labels.update(result)
    return {"source": "DeepSeek-V4-Flash authored, high effort", "labels": labels}


# --------------------------------------------------------------------------
# Keyword labeler
# --------------------------------------------------------------------------


def label_window(window: dict[str, Any], lexicon: Lexicon, axes: dict[str, str], gap: int = 2) -> dict[str, Any]:
    """Detections from keyword hits: one per label per run of nearby hit units."""
    units = window["units"]
    hits: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for position, unit in enumerate(units):
        for label, term in lexicon.match(unit["text"]):
            if label in axes:
                hits[label].append((position, term))
    detections = []
    for label, rows in hits.items():
        rows.sort()
        spans: list[list[tuple[int, str]]] = []
        for row in rows:
            if spans and row[0] - spans[-1][-1][0] <= gap:
                spans[-1].append(row)
            else:
                spans.append([row])
        for span in spans:
            start, end = span[0][0], span[-1][0]
            # A verbatim quote: the first matched unit's own text.
            quote = units[start]["text"][:300]
            count = len(span)
            detections.append({
                "start_unit_id": units[start]["unit_id"],
                "end_unit_id": units[end]["unit_id"],
                "label_ids": [label],
                "axis": axes[label],
                "relevance": "substantive" if count >= 2 else "passing",
                "discourse_role": "asserted_or_endorsed",
                "confidence": round(min(0.95, 0.4 + 0.15 * count), 3),
                "summary": "keyword: " + ", ".join(sorted({t for _, t in span}))[:200],
                "evidence_quote": quote,
            })
    return {"window_id": window["window_id"], "detections": detections, "verification_candidates": [], "product_mentions": []}


def write_run(run_dir: Path, manifest: dict[str, Any], repeats: Iterable[dict[str, dict[str, Any]]]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    for n, results in enumerate(repeats):
        repeat_dir = run_dir / f"repeat_{n}"
        repeat_dir.mkdir(exist_ok=True)
        db = repeat_dir / "labels.sqlite"
        if db.exists():
            db.unlink()
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE window_labels (window_id TEXT PRIMARY KEY, result_json TEXT NOT NULL)")
        con.executemany("INSERT INTO window_labels VALUES (?, ?)", [(k, json.dumps(v)) for k, v in results.items()])
        con.commit()
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("concepts")
    c.add_argument("--bench", default="v3")
    c.add_argument("--out", required=True)
    l = sub.add_parser("llm")
    l.add_argument("--bench", default="v3")
    l.add_argument("--out", required=True)
    l.add_argument("--effort", default="high")
    k = sub.add_parser("label")
    k.add_argument("--bench", default="v2")
    k.add_argument("--lexicon", required=True)
    k.add_argument("--name", required=True)
    k.add_argument("--axes", nargs="*", help="only these axes")
    k.add_argument("--min-hits", type=int, default=1, help="drop spans with fewer hits")
    args = parser.parse_args()

    if args.cmd == "concepts":
        Path(args.out).write_text(json.dumps(build_concepts(taxonomy_of(args.bench)), indent=1))
    elif args.cmd == "llm":
        sys.path.insert(0, str(REPO / "exp"))
        lex = build_llm(taxonomy_of(args.bench), effort=args.effort)
        Path(args.out).write_text(json.dumps(lex, indent=1, ensure_ascii=False))
        print(len(lex["labels"]), "labels")
    else:
        taxonomy = taxonomy_of(args.bench)
        axes = {x["label_id"]: x["axis"] for x in taxonomy["labels"]}
        if args.axes:
            axes = {k: v for k, v in axes.items() if v in args.axes}
        lexicon = Lexicon.load(Path(args.lexicon))
        items = [json.loads(line) for line in open(REPO / f"benchmark/{args.bench}/items.jsonl")]
        results = {}
        for item in items:
            result = label_window(item, lexicon, axes)
            if args.min_hits > 1:
                result["detections"] = [d for d in result["detections"] if d["confidence"] >= 0.4 + 0.15 * args.min_hits - 1e-9]
            results[item["window_id"]] = result
        write_run(REPO / f"benchmark/{args.bench}/runs/{args.name}",
                  {"name": args.name, "model": "keywords", "provider": None, "lexicon": args.lexicon, "min_hits": args.min_hits}, [results])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
