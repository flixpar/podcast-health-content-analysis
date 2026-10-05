"""Throughput summary for runs made by exp/xlabel.py with --metrics-log.

Steady-state rate counts completions between the 10th and 90th percentile
completion times, so the warm-up and the long tail (the last few long windows
running alone) do not count; this approximates a node fed by a continuous
queue, which is what a 100k-episode job is.

    python exp/tpstats.py exp/tp/glm-A-high [more run dirs]
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

WINDOWS_PER_EPISODE = 15.36  # prod-sample-1000: 15,362 windows over 1,000 episodes


def attempts(run: Path) -> list[dict]:
    rows = []
    for path in sorted(run.glob("repeat_*/attempts.jsonl")):
        rows += [json.loads(line) for line in open(path)]
    return rows


def metrics(run: Path) -> list[dict]:
    path = run.with_suffix(".metrics.jsonl") if not (run / "metrics.jsonl").exists() else run / "metrics.jsonl"
    path = Path(str(run) + ".metrics.jsonl") if not path.exists() else path
    return [json.loads(line) for line in open(path)] if path.exists() else []


def summarize(run: Path, window: tuple[float, float] | None = None) -> dict:
    rows = [r for r in attempts(run) if r.get("ok") and r.get("t_end")]
    calls = attempts(run)
    ends = sorted(r["t_end"] for r in rows)
    n = len(ends)
    t0 = min(r["t_start"] for r in calls if "t_start" in r)
    if window:
        lo, hi = t0 + 60 * window[0], min(t0 + 60 * window[1], ends[-1])
        steady = sum(lo <= e <= hi for e in ends) / (hi - lo) * 3600
    else:
        lo, hi = ends[int(0.1 * n)], ends[int(0.9 * n) - 1]
        steady = (int(0.9 * n) - int(0.1 * n)) / (hi - lo) * 3600 if hi > lo else float("nan")
    wall = ends[-1] - t0
    out_tok = [r["usage"]["completion_tokens"] for r in rows if r.get("usage")]
    prompt_tok = [r["usage"]["prompt_tokens"] for r in rows if r.get("usage")]
    res = {
        "run": run.name,
        "ok": n,
        "failed_attempts": sum(1 for r in calls if not r.get("ok")),
        "wall_min": round(wall / 60, 1),
        "win_per_h_wall": round(n / wall * 3600),
        "win_per_h_steady": round(steady),
        "out_tok_mean": round(st.mean(out_tok)) if out_tok else None,
        "out_tok_median": round(st.median(out_tok)) if out_tok else None,
        "out_tok_p95": round(sorted(out_tok)[int(0.95 * len(out_tok))]) if out_tok else None,
        "prompt_tok_mean": round(st.mean(prompt_tok)) if prompt_tok else None,
    }
    ms = [m for m in metrics(run) if lo <= m["t"] <= hi]
    if len(ms) > 2:
        a, b = ms[0], ms[-1]
        dt = b["t"] - a["t"]
        d = lambda k: b.get(k, 0) - a.get(k, 0)  # noqa: E731
        res.update(
            gen_tok_s=round(d("vllm:generation_tokens_total") / dt),
            prefill_tok_s=round((d("vllm:prompt_tokens_total") - d("vllm:prompt_tokens_cached_total")) / dt),
            cached_frac=round(d("vllm:prompt_tokens_cached_total") / max(1, d("vllm:prompt_tokens_total")), 3),
            running_mean=round(st.mean(m["vllm:num_requests_running"] for m in ms), 1),
            kv_mean=round(st.mean(m["vllm:kv_cache_usage_perc"] for m in ms), 3),
            preemptions=int(d("vllm:num_preemptions_total")),
        )
        drafted = d("vllm:spec_decode_num_draft_tokens_total")
        if drafted:
            res["spec_accept"] = round(d("vllm:spec_decode_num_accepted_tokens_total") / drafted, 3)
    res["node_h_per_100k_episodes"] = round(100_000 * WINDOWS_PER_EPISODE / res["win_per_h_steady"]) if res["win_per_h_steady"] else None
    return res


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--window", nargs=2, type=float, help="minutes from start: count completions and tokens in [a, b]")
    ap.add_argument("--ref-tokens", type=float, help="mean output tokens per window of this config on the full set; adds win_per_h_tok = gen_tok_s*3600/ref")
    a = ap.parse_args()
    rows = []
    for p in a.runs:
        r = summarize(Path(p), tuple(a.window) if a.window else None)
        if a.ref_tokens and r.get("gen_tok_s"):
            r["win_per_h_tok"] = round(r["gen_tok_s"] * 3600 / a.ref_tokens)
        rows.append(r)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    print("| " + " | ".join(keys) + " |")
    print("| " + " | ".join("---" for _ in keys) + " |")
    for r in rows:
        print("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")
