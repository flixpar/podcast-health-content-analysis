"""Steady-state throughput probe for the local vLLM server.

Holds `--concurrency` labeling-shaped requests open for `--seconds`, then reads
the server's own counters over the measured interval (after `--warmup`), so
the number is aggregate decode tokens/s under that load, independent of how
long individual responses are.

  .venv/bin/python analysis/serving/loadtest.py --concurrency 64 --seconds 240 --effort high
"""
from __future__ import annotations

import argparse, json, os, random, re, sys, threading, time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from analysis import topic_labeling as tl  # noqa: E402
from analysis.benchmark import ITEMS_PATH, TAXONOMY_PATH  # noqa: E402
from analysis.benchmark.items import load_items, window_payload  # noqa: E402
from analysis.benchmark.taxonomy import load_benchmark_taxonomy  # noqa: E402

BASE = "http://127.0.0.1:8222"  # --base overrides


def metrics() -> dict[str, float]:
    response = requests.get(f"{BASE}/metrics", timeout=30)
    response.raise_for_status()
    text = response.text
    out: dict[str, float] = {}
    for key in ("generation_tokens_total", "prompt_tokens_total", "num_requests_running",
                "num_requests_waiting", "kv_cache_usage_perc", "num_preemptions_total",
                "iteration_tokens_total_count", "iteration_tokens_total_sum"):
        # Counters/counts sum over engines; cache utilization tracks the fullest
        # engine so data parallelism cannot turn a fraction into a value > 1.
        values = re.findall(rf"^vllm:{key}(?:\{{[^}}]*\}})? ([0-9.e+]+)$", text, re.M)
        if values:
            numbers = [float(value) for value in values]
            out[key] = max(numbers) if key == "kv_cache_usage_perc" else sum(numbers)
    return out


def main() -> None:
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--seconds", type=int, default=240)
    ap.add_argument("--warmup", type=int, default=60)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--max-tokens", type=int, default=40000)
    ap.add_argument("--thinking-token-budget", type=int)
    ap.add_argument("--api", choices=["chat", "responses"], default="chat")
    ap.add_argument("--no-schema", action="store_true")
    ap.add_argument("--label", default="")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--items", type=Path, default=ITEMS_PATH)
    ap.add_argument("--taxonomy", type=Path, default=TAXONOMY_PATH)
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "local/serving/loadtest.jsonl")
    args = ap.parse_args()
    if args.concurrency < 1 or args.seconds < 1 or args.warmup < 0 or args.max_tokens < 1:
        ap.error("concurrency, seconds and max-tokens must be positive; warmup must be non-negative")
    if args.thinking_token_budget is not None and (
        args.api != "chat" or args.thinking_token_budget < 1
    ):
        ap.error("thinking-token-budget requires --api chat and a positive token count")
    BASE = args.base.rstrip("/")

    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    items = load_items(args.items)
    windows = [window_payload(i) for i in items]
    if not windows:
        ap.error("items file contains no windows")
    instructions = tl.taxonomy_instructions(taxonomy)
    schema = tl.response_schema(taxonomy)
    settings = tl.ModelSettings(
        max_output_tokens=args.max_tokens, reasoning_effort=args.effort,
        thinking_token_budget=args.thinking_token_budget,
    )
    flavor = tl.ChatCompletionsFlavor() if args.api == "chat" else tl.ResponsesFlavor()
    response = requests.get(f"{BASE}/v1/models", timeout=30)
    response.raise_for_status()
    model = response.json()["data"][0]["id"]

    deadline = time.monotonic() + args.warmup + args.seconds
    done = {"requests": 0, "errors": 0}
    lock = threading.Lock()

    def worker(seed: int) -> None:
        rng = random.Random(seed)
        with requests.Session() as client:
            while time.monotonic() < deadline:
                window = rng.choice(windows)
                payload = {"model": model, **flavor.payload(instructions, tl.window_input(window), "podcast_topic_clips", schema, settings)}
                if args.no_schema:
                    payload.pop("response_format", None)
                    payload.pop("text", None)
                try:
                    r = client.post(f"{BASE}/v1{flavor.path}", json=payload)
                    ok = r.status_code == 200
                except Exception:
                    ok = False
                with lock:
                    done["requests" if ok else "errors"] += 1

    threads = [threading.Thread(target=worker, args=(s,), daemon=True) for s in range(args.concurrency)]
    for t in threads:
        t.start()
    time.sleep(args.warmup)
    m0, t0 = metrics(), time.monotonic()
    samples = []
    while time.monotonic() < deadline:
        time.sleep(min(15, max(0, deadline - time.monotonic())))
        samples.append(metrics())
    m1, t1 = metrics(), time.monotonic()
    dt = t1 - t0
    steps = m1["iteration_tokens_total_count"] - m0["iteration_tokens_total_count"]
    result = {
        "label": args.label, "model": model, "concurrency": args.concurrency, "effort": args.effort, "api": args.api,
        "schema": not args.no_schema, "max_tokens": args.max_tokens, "seconds": round(dt),
        "thinking_token_budget": args.thinking_token_budget,
        "gen_tok_s": round((m1["generation_tokens_total"] - m0["generation_tokens_total"]) / dt),
        "prompt_tok_s": round((m1["prompt_tokens_total"] - m0["prompt_tokens_total"]) / dt),
        "steps_s": round(steps / dt, 1),
        "tokens_per_step": round((m1["iteration_tokens_total_sum"] - m0["iteration_tokens_total_sum"]) / max(steps, 1), 1),
        "running_mean": round(sum(s["num_requests_running"] for s in samples) / max(len(samples), 1), 1),
        "waiting_mean": round(sum(s["num_requests_waiting"] for s in samples) / max(len(samples), 1), 1),
        "kv_max": round(max(s["kv_cache_usage_perc"] for s in samples), 3) if samples else None,
        "preemptions": m1["num_preemptions_total"] - m0["num_preemptions_total"],
        "completed": done["requests"], "errors": done["errors"],
    }
    print(json.dumps(result), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(result) + "\n")
    os._exit(0)  # drop in-flight connections so the server aborts them


if __name__ == "__main__":
    main()
