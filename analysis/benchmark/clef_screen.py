"""Is a System One model a usable screen in front of the generative labeler?

A screen reads each window once and decides whether it goes on to full
labeling. It is only worth having if it is much cheaper than labeling and
almost never drops a window that carries labels, so this measures both, for
several screen designs, against two references:

- ``benchmark``: the benchmark items, positive when the gold holds at least
  one ``required`` atom. Human-consensus truth, but the strata are curated, so
  pass rates here are not corpus pass rates.
- ``corpus``: windows from a production label store (a DeepSeek run over whole
  episodes), positive when that run produced any annotation. Real base rates,
  and the closest thing to "what would the LLM have done with this window",
  which is what a screen in front of it should preserve.

    .venv/bin/python -m analysis.benchmark.clef_screen run --source benchmark \
        --endpoint http://127.0.0.1:8301/v1 --model clef-flash --out benchmark/runs/clef/screen-flash-bench.jsonl
    .venv/bin/python -m analysis.benchmark.clef_screen report benchmark/runs/clef/screen-flash-bench.jsonl

Every probability is stored, so thresholds are chosen afterwards.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sqlite3
import threading
import time
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable

from analysis import typesafe_labeling as typesafe
from analysis.benchmark.items import load_items, window_payload
from analysis.benchmark.taxonomy import load_benchmark_taxonomy

CORPUS_STRATA = ("health_dense", "mixed", "null", "ad_read", "discourse")

# Gate wordings. `health`, `claim` and `product` are the TypeSafe method's own
# screen gates; the others are alternatives worth comparing on a model that was
# not the one they were written for.
HEALTH_PLAIN = {
    "type": "noul",
    "instructions": (
        "Does this podcast transcript excerpt discuss health, medicine, disease, "
        "nutrition, diet, fitness, mental health, the body or wellness, or advertise "
        "a health or wellness product?"
    ),
}
HEALTH_SUBSTANTIVE = {
    "type": "noul",
    "instructions": (
        "Would a researcher studying health information in podcasts want to read "
        "this excerpt? Yes if any stretch discusses a health, medical, nutrition, "
        "fitness, mental-health or wellness subject, gives health advice, makes a "
        "health claim, or promotes a health product; no if health words appear only "
        "in passing or as figures of speech."
    ),
}


# Written after reading what the method's gate rejected on corpus windows that
# the DeepSeek run had labeled: three quarters were passing mentions, and mental
# health (therapy, trauma, "gaslighting") was half of them. The method's gate
# never names mental health and tells the model that incidental mentions do not
# count, which suits a precise gate but not a screen in front of a labeler
# whose codebook records passing mentions.
HEALTH_BROAD = {
    "type": "noul",
    "instructions": (
        "Does any part of `transcript` touch on health in any way: physical or mental "
        "health, illness, medicine, therapy or psychology, sleep, nutrition or diet, "
        "fitness, the body, sex or reproduction, drugs or alcohol, or wellness -- even "
        "briefly or in passing, including in an advertisement?"
    ),
    "criteria": {
        "true": "At least one stretch mentions or discusses a health-related subject, however briefly, including in an ad.",
        "false": "Nothing health-related comes up at all, or health words appear only as idioms (\"that's sick\", \"my brain is fried\").",
    },
}
MENTAL = {
    "type": "noul",
    "instructions": (
        "Does any part of `transcript` mention mental health or psychology: therapy or "
        "counselling, trauma, anxiety, depression, stress, addiction, self-esteem or "
        "insecurity, emotional abuse or manipulation, or a psychological diagnosis?"
    ),
}


def variants() -> dict[str, dict[str, Any]]:
    gates = typesafe.GATE_QUESTIONS
    return {
        "health": {"gate|health": gates["health"]},
        "gates": {f"gate|{name}": question for name, question in gates.items()},
        "plain": {"gate|plain": HEALTH_PLAIN},
        "substantive": {"gate|substantive": HEALTH_SUBSTANTIVE},
        "broad": {"gate|broad": HEALTH_BROAD},
        "broad_mental": {"gate|broad": HEALTH_BROAD, "gate|mental": MENTAL},
        # The method's full screen: every taxonomy label plus the three gates.
        "full": None,
    }


def full_screen(taxonomy: dict[str, Any]) -> dict[str, Any]:
    return {
        **{
            f"label|{label['label_id']}": typesafe.screen_question(label, True)
            for label in taxonomy["labels"]
        },
        **{f"gate|{name}": question for name, question in typesafe.GATE_QUESTIONS.items()},
    }


def ask(endpoint: str, model: str, state: Any, questions: dict[str, Any], timeout: int = 600) -> dict[str, Any]:
    payload = json.dumps({"model": model, "state": state, "questions": questions}).encode("utf-8")
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/systemone", data=payload, headers={"Content-Type": "application/json"}
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


# --------------------------------------------------------------------------
# Windows and their references
# --------------------------------------------------------------------------


def benchmark_windows() -> Iterable[dict[str, Any]]:
    from analysis.benchmark.references import load_gold

    gold = load_gold()
    for item in load_items():
        if item["stratum"] not in CORPUS_STRATA:
            continue
        atoms = [atom for atom in gold.get(item["item_id"], []) if atom.tier in ("required", "acceptable")]
        kinds = Counter(atom.kind if atom.kind != "detection" else f"detection:{atom.axis}" for atom in atoms)
        yield {
            "window": window_payload(item),
            "reference": {
                "positive": bool(atoms),
                "atoms": len(atoms),
                "kinds": dict(kinds),
                "stratum": item["stratum"],
                "split": item["split"],
            },
        }


CACHE_DIR = Path("benchmark/runs/clef")


def corpus_cache(run_dir: Path) -> Path:
    """One cache per label store: finding its windows reads the whole corpus."""
    store = (Path(run_dir) / "labels.sqlite").resolve()
    key = hashlib.sha256(f"{store}:{store.stat().st_mtime_ns}".encode("utf-8")).hexdigest()[:12]
    return CACHE_DIR / f"corpus-windows-{key}.jsonl"


def corpus_windows(run_dir: Path, limit: int | None = None) -> Iterable[dict[str, Any]]:
    """The windows a production run labeled, with what it labeled in each."""
    cache = corpus_cache(run_dir)
    if cache.exists():
        with open(cache, encoding="utf-8") as handle:
            for number, line in enumerate(handle):
                if limit and number >= limit:
                    return
                yield json.loads(line)
        return
    entries = list(_scan_corpus(run_dir))
    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")
    yield from entries[:limit] if limit else entries


def _scan_corpus(run_dir: Path) -> Iterable[dict[str, Any]]:
    import zstandard

    store = sqlite3.connect(f"file:{run_dir / 'labels.sqlite'}?mode=ro", uri=True)
    labeled: dict[str, dict[str, Any]] = {}
    for window_id, result_json in store.execute("SELECT window_id, result_json FROM window_labels"):
        result = json.loads(result_json)
        counts = {
            "detection": len(result.get("detections") or []),
            "claim": len(result.get("verification_candidates") or []),
            "product": len(result.get("product_mentions") or []),
        }
        labeled[window_id] = {
            "positive": any(counts.values()),
            "atoms": sum(counts.values()),
            "kinds": counts,
            "stratum": "corpus",
            "split": "corpus",
        }
    store.close()
    found = 0
    with open(run_dir / "windows.jsonl.zst", "rb") as raw:
        reader = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(raw), encoding="utf-8")
        for line in reader:
            window = json.loads(line)
            reference = labeled.get(window["window_id"])
            if reference is None:
                continue
            yield {"window": {key: window.get(key) for key in ("window_id", "units")}, "reference": reference}
            found += 1
            if found == len(labeled):
                return


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------


def run(args: argparse.Namespace) -> None:
    taxonomy = load_benchmark_taxonomy()
    chosen = {name: question for name, question in variants().items() if name in args.variants}
    if "full" in chosen:
        chosen["full"] = full_screen(taxonomy)
    out = Path(args.out)
    done: set[tuple[str, str]] = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            done.add((row["window_id"], row["variant"]))
    if args.source == "corpus" and not args.corpus:
        raise SystemExit("--source corpus needs --corpus")
    windows = list(benchmark_windows() if args.source == "benchmark" else corpus_windows(Path(args.corpus), args.limit))
    jobs = [
        (entry, name)
        for entry in windows
        for name in chosen
        if (entry["window"]["window_id"], name) not in done
    ]
    print(f"{len(windows)} windows, {len(jobs)} requests to send", flush=True)
    lock = threading.Lock()
    endpoints = args.endpoint
    counter = Counter()
    started = time.monotonic()

    def one(index_job: tuple[int, tuple[dict[str, Any], str]]) -> None:
        index, (entry, name) = index_job
        window = entry["window"]
        state = {"transcript": " ".join(unit["text"] for unit in window["units"])}
        t0 = time.monotonic()
        response = ask(endpoints[index % len(endpoints)], args.model, state, chosen[name])
        row = {
            "window_id": window["window_id"],
            "variant": name,
            "model": response["model"],
            "seconds": round(time.monotonic() - t0, 3),
            "input_tokens": response["usage"]["input_tokens"],
            "answers": {key: answer["noul"] for key, answer in response["answers"].items()},
            "reference": entry["reference"],
        }
        with lock:
            with open(out, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row) + "\n")
            counter[name] += 1
            total = sum(counter.values())
            if total % 200 == 0:
                rate = total / (time.monotonic() - started)
                print(f"{total}/{len(jobs)} requests, {rate:.1f}/s", flush=True)

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(one, enumerate(jobs)))
    elapsed = time.monotonic() - started
    print(f"done: {len(jobs)} requests in {elapsed:.0f}s ({len(jobs) / max(elapsed, 1e-9):.1f}/s)", flush=True)


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


def auroc(scores: list[float], labels: list[bool]) -> float | None:
    positives = [s for s, y in zip(scores, labels) if y]
    negatives = [s for s, y in zip(scores, labels) if not y]
    if not positives or not negatives:
        return None
    wins = 0.0
    for p in positives:
        for n in negatives:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(positives) * len(negatives))


def score_of(row: dict[str, Any], rule: str) -> float:
    answers = row["answers"]
    if rule == "gate":  # the variant's one health question
        return next(value for key, value in answers.items() if key.startswith("gate|") and key != "gate|claim" and key != "gate|product")
    if rule == "max_gates":
        return max(value for key, value in answers.items() if key.startswith("gate|"))
    if rule == "max_labels":
        return max(value for key, value in answers.items() if key.startswith("label|"))
    if rule == "health_and_labels":  # the method's own fan-out rule
        labels = max(value for key, value in answers.items() if key.startswith("label|"))
        return min(answers["gate|health"], labels)
    raise ValueError(rule)


RULES = {
    "health": ["gate"],
    "gates": ["gate", "max_gates"],
    "plain": ["gate"],
    "substantive": ["gate"],
    "broad": ["gate"],
    "broad_mental": ["gate", "max_gates"],
    "full": ["gate", "max_labels", "health_and_labels"],
}
THRESHOLDS = (0.02, 0.05, 0.1, 0.2, 0.3, 0.5)


def report(args: argparse.Namespace) -> None:
    rows = [json.loads(line) for path in args.files for line in Path(path).read_text().splitlines()]
    by_variant: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        source = "corpus" if row["reference"]["split"] == "corpus" else "benchmark"
        by_variant[(source, row["model"], row["variant"])].append(row)
    lines = []
    for (source, model, variant), group in sorted(by_variant.items()):
        labels = [row["reference"]["positive"] for row in group]
        atoms = [row["reference"]["atoms"] for row in group]
        tokens = sum(row["input_tokens"] for row in group) / len(group)
        lines.append(
            f"\n### {source}: {model} / {variant}  (n={len(group)}, positive {sum(labels)}, "
            f"{tokens:,.0f} tokens per window)\n"
        )
        lines.append("| rule | AUROC | threshold | windows passed | positive windows kept | atoms kept | negatives passed |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for rule in RULES[variant]:
            scores = [score_of(row, rule) for row in group]
            area = auroc(scores, labels)
            for threshold in THRESHOLDS:
                passed = [s >= threshold for s in scores]
                kept_pos = sum(p and y for p, y in zip(passed, labels))
                kept_atoms = sum(a for p, a in zip(passed, atoms) if p)
                neg = len(labels) - sum(labels)
                lines.append(
                    f"| {rule} | {area:.3f} | {threshold} | {sum(passed) / len(passed):.1%} | "
                    f"{kept_pos}/{sum(labels)} ({kept_pos / max(sum(labels), 1):.1%}) | "
                    f"{kept_atoms / max(sum(atoms), 1):.1%} | "
                    f"{sum(p and not y for p, y in zip(passed, labels))}/{neg} "
                    f"({sum(p and not y for p, y in zip(passed, labels)) / max(neg, 1):.1%}) |"
                )
    if args.store:
        lines.extend(relevance_table(rows, Path(args.store)))
    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")


def relevance_table(rows: list[dict[str, Any]], store_path: Path) -> list[str]:
    """Corpus atoms kept, split by what the labeler said they were.

    A screen that loses passing mentions is a different thing from one that
    loses substantive discussion or claims, and the totals do not tell them apart.
    """
    store = sqlite3.connect(f"file:{store_path}?mode=ro", uri=True)
    results = {window_id: json.loads(text) for window_id, text in store.execute("SELECT window_id, result_json FROM window_labels")}
    store.close()
    kinds = ("substantive", "advertisement", "passing", "claim", "product")
    lines = []
    by_variant: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["reference"]["split"] == "corpus":
            by_variant[(row["model"], row["variant"])].append(row)
    for (model, variant), group in sorted(by_variant.items()):
        lines.append(f"\n### corpus atoms kept by relevance: {model} / {variant}\n")
        lines.append("| threshold | windows passed | " + " | ".join(kinds) + " |")
        lines.append("| --- | --- | " + " | ".join("---" for _ in kinds) + " |")
        scores = [score_of(row, "gate") for row in group]
        for threshold in THRESHOLDS:
            kept: Counter[str] = Counter()
            total: Counter[str] = Counter()
            for row, score in zip(group, scores):
                result = results[row["window_id"]]
                counts: Counter[str] = Counter(
                    detection.get("relevance") for detection in result.get("detections") or []
                )
                counts["claim"] = len(result.get("verification_candidates") or [])
                counts["product"] = len(result.get("product_mentions") or [])
                for kind in kinds:
                    total[kind] += counts[kind]
                    kept[kind] += counts[kind] if score >= threshold else 0
            passed = sum(score >= threshold for score in scores) / len(scores)
            lines.append(
                f"| {threshold} | {passed:.1%} | "
                + " | ".join(f"{kept[kind] / max(total[kind], 1):.1%}" for kind in kinds)
                + " |"
            )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--source", choices=("benchmark", "corpus"), required=True)
    run_parser.add_argument("--corpus", help="A production label directory (labels.sqlite, windows.jsonl.zst)")
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--endpoint", nargs="+", required=True)
    run_parser.add_argument("--model", required=True)
    run_parser.add_argument("--variants", nargs="+", default=["health", "gates", "plain", "substantive"])
    run_parser.add_argument("--concurrency", type=int, default=32)
    run_parser.add_argument("--out", required=True)
    report_parser = commands.add_parser("report")
    report_parser.add_argument("files", nargs="+")
    report_parser.add_argument("--out")
    report_parser.add_argument("--store", help="The corpus label store, to split atoms kept by relevance")
    args = parser.parse_args()
    (run if args.command == "run" else report)(args)


if __name__ == "__main__":
    main()
