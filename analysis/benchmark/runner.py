"""Label the benchmark items with a candidate configuration.

A benchmark run is configured exactly like a production run: the same TOML
tables, the same flags, the same ``ResponsesClient``, ``ModelSettings``,
``LabelStore`` and usage limiter. What it adds is an attempts log (every
request, accepted or rejected, with its rejection kind, usage and latency),
repeats, a prompt override, and a manifest that records what was scored on.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, Callable, Sequence

from analysis import topic_labeling as tl
from analysis.usage_limits import Usage
from analysis.benchmark import BENCHMARK_VERSION, REPO_ROOT, RUNS_DIR
from analysis.benchmark.items import items_hash, window_payload
from analysis.benchmark.taxonomy import label_axes

RUN_FIELDS = ("name", "repeats", "split", "rubric_file", "alias", "limit", "items_file", "notes")


def validator_sha256() -> str:
    """Identity of the validator the pipeline currently ships, for the manifest."""
    source = "".join(
        inspect.getsource(function)
        for function in (
            tl.parse_json_output,
            tl.validate_response,
            tl.validate_response_lenient,
            tl.validate_window_result,
            tl._lenient_window_result,
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def label_args(argv: Sequence[str], config: Path | None) -> argparse.Namespace:
    """Parse pipeline ``label`` flags, with the TOML config expanded first.

    Same mechanism as the pipeline: config values become flags in front of the
    typed ones, so a typed flag wins and argparse validates the file.
    """
    tokens = ["label", *(["--config", str(config)] if config is not None else []), *argv]
    parser = tl.build_parser()
    args = parser.parse_args(tl.expand_config_args(tokens))
    return tl.resolve_output_paths(args)


def build_instructions(taxonomy: dict[str, Any], rubric_file: Path | None) -> tuple[str, str, str]:
    """(instructions, prompt_version, rubric_sha256) for the run."""
    if rubric_file is None:
        instructions = tl.taxonomy_instructions(taxonomy)
        version = tl.PROMPT_VERSION
        rubric = tl.SYSTEM_RUBRIC
    else:
        rubric = Path(rubric_file).read_text(encoding="utf-8")
        compact = [
            {
                "label_id": label["label_id"],
                "axis": label["axis"],
                "name": label["name"],
                "definition": label["definition"],
                "examples": label["concepts"],
            }
            for label in taxonomy["labels"]
        ]
        instructions = (
            rubric
            + "\n# Codebook\n\nEach label carries its axis, the definition that governs "
            "it, and example terms. The definition decides; the examples are only "
            "illustrations and matching one is neither necessary nor sufficient.\n\n"
            + tl.canonical_json(compact)
        )
        version = f"file:{Path(rubric_file).name}"
    return instructions, version, tl.sha256_bytes(rubric.encode("utf-8"))


class AttemptLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.counts: Counter[str] = Counter()
        # What lenient validation repaired and dropped across accepted attempts.
        self.repaired: Counter[str] = Counter()
        self.dropped: Counter[str] = Counter()

    def __call__(self, record: dict[str, Any]) -> None:
        record = {**record, "logged_at": tl.utc_now()}
        with self.lock:
            self.counts["attempts"] += 1
            self.counts["accepted" if record["ok"] else f"rejected:{record.get('kind')}"] += 1
            changes = record.get("validation") or {}
            self.repaired.update(changes.get("repaired") or {})
            self.dropped.update(changes.get("dropped") or {})
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")


# Manifest keys that describe a run without changing what it labels. Everything
# else in the manifest is a fingerprint input; two runs with the same
# fingerprint are interchangeable, and a label store refuses a different one.
# A run from before one-window requests carries a batch_size input, so its
# recomputed fingerprint still matches the one it was stored under.
MANIFEST_ONLY_KEYS = frozenset({
    "run_fingerprint", "items_hash", "benchmark_version", "name", "notes", "created_at",
    "validator_sha256", "git_commit", "endpoints", "provider", "experiment", "usage_limits",
    "config", "rubric_file", "no_auth", "items", "repeats", "concurrency", "repeat_summaries",
    "stopped_by_usage_limit", "finished_at", "completed_at", "repeat", "validation_changes",
})


def fingerprint_from_manifest(manifest: dict[str, Any]) -> str:
    inputs = {key: value for key, value in manifest.items() if key not in MANIFEST_ONLY_KEYS}
    return tl.sha256_bytes(tl.canonical_json(inputs).encode("utf-8"))


def run_benchmark(
    items: Sequence[dict[str, Any]],
    taxonomy: dict[str, Any],
    args: argparse.Namespace,
    name: str,
    repeats: int = 2,
    rubric_file: Path | None = None,
    runs_dir: Path = RUNS_DIR,
    notes: str | None = None,
    log: Any = None,
) -> dict[str, Any]:
    """Label every item ``repeats`` times; writes benchmark/runs/<name>/."""
    if args.concurrency < 1 or args.attempts < 1:
        raise tl.TopicLabelingError("concurrency and attempts must both be positive")
    run_dir = Path(runs_dir) / name
    run_dir.mkdir(parents=True, exist_ok=True)
    api_key = tl.resolve_api_key(args)
    api_bases = args.api_base or [tl.DEFAULT_API_BASE]
    limiter = tl.build_limiter(args)
    client = tl.ResponsesClient(
        api_bases, api_key, args.timeout, args.attempts, limiter=limiter, provider=args.provider, api=args.api
    )
    served = client.served_models()
    model = args.model or client.discover_model()
    settings = tl.ModelSettings.from_args(args)
    instructions, prompt_version, rubric_sha = build_instructions(taxonomy, rubric_file)
    windows = [window_payload(item) for item in items]
    fingerprint_inputs = {
        "schema_version": tl.SCHEMA_VERSION,
        "prompt_version": prompt_version,
        "rubric_sha256": rubric_sha,
        "taxonomy_sha256": taxonomy["taxonomy_sha256"],
        "model": model,
        "api": args.api,
        "validation": args.validation,
        **settings.fingerprint(),
    }
    manifest: dict[str, Any] = {
        **fingerprint_inputs,
        "run_fingerprint": fingerprint_from_manifest(fingerprint_inputs),
        # Recorded, not fingerprinted: the item set may grow between passes,
        # and a run is resumed over the new items rather than started over.
        "items_hash": items_hash(items),
        "benchmark_version": BENCHMARK_VERSION,
        "name": name,
        "notes": notes,
        "created_at": tl.utc_now(),
        "validator_sha256": validator_sha256(),
        "git_commit": git_commit(),
        "endpoints": served,
        "provider": args.provider,
        "experiment": args.experiment,
        "usage_limits": str(args.usage_limits) if args.usage_limits else None,
        "config": str(args.config) if getattr(args, "config", None) and Path(args.config).exists() else None,
        "rubric_file": str(rubric_file) if rubric_file else None,
        "no_auth": args.api_key_env is None,
        "items": len(items),
        "repeats": repeats,
        "concurrency": args.concurrency,
    }
    tl.write_json(run_dir / "run_manifest.json", manifest)
    repeat_summaries = []
    budget_stop = None
    try:
        for repeat in range(repeats):
            repeat_dir = run_dir / f"repeat_{repeat}"
            repeat_dir.mkdir(exist_ok=True)
            attempts = AttemptLog(repeat_dir / "attempts.jsonl")
            store = tl.LabelStore(repeat_dir / "labels.sqlite", {**manifest, "repeat": repeat})
            started = time.monotonic()
            try:
                summary = _label_repeat(windows, taxonomy, client, model, settings, instructions, args, store, attempts, log)
            finally:
                store.close()
            summary.update(
                {
                    "repeat": repeat,
                    "wall_seconds": round(time.monotonic() - started, 1),
                    "attempts": dict(attempts.counts),
                    "validation_changes": {
                        "repaired": dict(sorted(attempts.repaired.items())),
                        "dropped": dict(sorted(attempts.dropped.items())),
                    },
                }
            )
            tl.write_json(repeat_dir / "repeat_manifest.json", summary)
            repeat_summaries.append(summary)
            if summary.get("stopped_by_usage_limit"):
                budget_stop = summary["stopped_by_usage_limit"]
                break
    finally:
        limiter.close()
    repaired: Counter[str] = Counter()
    dropped: Counter[str] = Counter()
    for summary in repeat_summaries:
        repaired.update(summary["validation_changes"]["repaired"])
        dropped.update(summary["validation_changes"]["dropped"])
    manifest.update(
        {
            "completed_at": tl.utc_now(),
            "repeat_summaries": repeat_summaries,
            # Summed over the repeats' accepted responses in this invocation;
            # always empty under strict validation.
            "validation_changes": {
                "repaired": dict(sorted(repaired.items())),
                "dropped": dict(sorted(dropped.items())),
            },
            "stopped_by_usage_limit": budget_stop,
        }
    )
    tl.write_json(run_dir / "run_manifest.json", manifest)
    return manifest


def _label_repeat(
    windows: Sequence[dict[str, Any]],
    taxonomy: dict[str, Any],
    client: tl.ResponsesClient,
    model: str,
    settings: tl.ModelSettings,
    instructions: str,
    args: argparse.Namespace,
    store: tl.LabelStore,
    attempts: AttemptLog,
    log: Any,
) -> dict[str, Any]:
    done = store.done_ids()
    pending = [window for window in windows if window["window_id"] not in done]

    def classify(window: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        return client.classify(
            window, taxonomy, model, settings, instructions=instructions, on_attempt=attempts, validation=args.validation
        )

    budget_stop: tl.BudgetExceeded | None = None
    iterator = iter(pending)
    futures: dict[Future[Any], dict[str, Any]] = {}
    completed = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        while len(futures) < args.concurrency * 2:
            try:
                window = next(iterator)
            except StopIteration:
                break
            futures[executor.submit(classify, window)] = window
        while futures:
            finished, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in finished:
                window = futures.pop(future)
                try:
                    result, meta = future.result()
                    store.record_success(window, result, meta)
                except tl.BudgetExceeded as exc:
                    budget_stop = budget_stop or exc
                    store.record_failure(window, exc)
                except Exception as exc:
                    store.record_failure(window, exc)
                completed += 1
                if budget_stop is None:
                    try:
                        window = next(iterator)
                    except StopIteration:
                        pass
                    else:
                        futures[executor.submit(classify, window)] = window
                if log and completed % 10 == 0:
                    complete, failed = store.counts()
                    print(f"requests={completed} windows={complete} unresolved={failed}", file=log)
    exported, sha = store.export_jsonl(store.path.parent / "window_labels.jsonl.zst")
    complete, failed = store.counts()
    return {
        "windows_labeled": complete,
        "unresolved_windows": failed,
        "unresolved_windows_by_kind": store.failure_kinds(),
        "exported": exported,
        "window_labels_sha256": sha,
        "stopped_by_usage_limit": str(budget_stop) if budget_stop else None,
    }


# --------------------------------------------------------------------------
# Reading a run back
# --------------------------------------------------------------------------


def load_run(run_dir: Path) -> dict[str, Any]:
    """Manifest, per-repeat results keyed by window_id, and attempts."""
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    repeats: list[dict[str, dict[str, Any]]] = []
    attempts: list[dict[str, Any]] = []
    for repeat_dir in sorted(run_dir.glob("repeat_*")):
        db = repeat_dir / "labels.sqlite"
        results: dict[str, dict[str, Any]] = {}
        if db.exists():
            import sqlite3

            connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                for window_id, result_json in connection.execute(
                    "SELECT window_id, result_json FROM window_labels"
                ):
                    results[window_id] = json.loads(result_json)
            finally:
                connection.close()
        repeats.append(results)
        log = repeat_dir / "attempts.jsonl"
        if log.exists():
            for line in log.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    record["repeat"] = repeat_dir.name
                    attempts.append(record)
    return {"manifest": manifest, "repeats": repeats, "attempts": attempts, "run_dir": str(run_dir)}


def usage_summary(attempts: Sequence[dict[str, Any]], prices: dict[str, float] | None) -> dict[str, Any]:
    """Tokens, validity and cost from the attempts log (one row per request)."""
    totals: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    repaired: Counter[str] = Counter()
    dropped: Counter[str] = Counter()
    seconds = 0.0
    windows_accepted = 0
    for record in attempts:
        totals["requests"] += 1
        seconds += float(record.get("seconds") or 0)
        usage = record.get("usage") or {}
        parsed = Usage.parse(usage)
        if parsed is not None:
            totals["input_tokens"] += int(parsed.input_tokens)
            # DeepSeek's Chat Completions dialect reports cache hits beside the
            # prompt count rather than inside a details object.
            cached = parsed.cached_input_tokens or float(usage.get("prompt_cache_hit_tokens") or 0)
            totals["cached_input_tokens"] += int(cached)
            totals["output_tokens"] += int(parsed.output_tokens)
        if record.get("ok"):
            totals["accepted"] += 1
            # One window per request; a log from a batched run lists them.
            windows_accepted += len(record["windows"]) if "windows" in record else 1
            # Lenient validation's repairs and drops ride on accepted attempts.
            changes = record.get("validation") or {}
            repaired.update(changes.get("repaired") or {})
            dropped.update(changes.get("dropped") or {})
        else:
            totals["rejected"] += 1
            kinds[str(record.get("kind"))] += 1
    first_attempts = [r for r in attempts if r.get("attempt") == 0]
    summary: dict[str, Any] = {
        **dict(totals),
        "windows_accepted": windows_accepted,
        "rejected_by_kind": dict(kinds),
        "annotations_repaired": dict(sorted(repaired.items())),
        "annotations_dropped": dict(sorted(dropped.items())),
        "first_attempt_validity": round(
            sum(1 for r in first_attempts if r.get("ok")) / len(first_attempts), 4
        ) if first_attempts else None,
        "requests_per_accepted_window": round(totals["requests"] / windows_accepted, 3) if windows_accepted else None,
        "output_tokens_per_accepted_window": round(totals["output_tokens"] / windows_accepted) if windows_accepted else None,
        "mean_seconds_per_request": round(seconds / totals["requests"], 1) if totals["requests"] else None,
    }
    if prices:
        uncached = totals["input_tokens"] - totals["cached_input_tokens"]
        cost = (
            uncached / 1e6 * float(prices.get("input_per_mtok", 0))
            + totals["cached_input_tokens"] / 1e6 * float(prices.get("cached_input_per_mtok", prices.get("input_per_mtok", 0)))
            + totals["output_tokens"] / 1e6 * float(prices.get("output_per_mtok", 0))
        )
        summary["cost_usd"] = round(cost, 4)
        summary["cost_per_accepted_window"] = round(cost / windows_accepted, 5) if windows_accepted else None
    return summary


def model_prices(usage_limits_path: Path | None, provider: str | None, model: str | None) -> dict[str, float] | None:
    if not usage_limits_path or not provider or not model or not Path(usage_limits_path).exists():
        return None
    import tomllib

    with open(usage_limits_path, "rb") as handle:
        config = tomllib.load(handle)
    entry = config.get("model", {}).get(provider, {}).get(model)
    if not entry:
        return None
    return {k: v for k, v in entry.items() if k.endswith("_per_mtok")}
