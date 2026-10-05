"""Throughput breakdown for benchmark runs: tokens spent, wasted, per accepted window."""
import json, sys, collections, statistics
from pathlib import Path

for run in sys.argv[1:]:
    rows = []
    pattern = sys.argv[0] and __import__("os").environ.get("REPEAT_GLOB", "repeat_*")
    for f in sorted(Path(run).glob(f"{pattern}/attempts.jsonl")):
        rows += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    transport = sum(1 for r in rows if r.get("kind") == "transport")
    rows = [r for r in rows if r.get("kind") != "transport"]
    if not rows:
        print(run, "no attempts"); continue
    out = lambda r: (r.get("usage") or {}).get("output_tokens") or (r.get("usage") or {}).get("completion_tokens") or 0
    reas = lambda r: ((r.get("usage") or {}).get("output_tokens_details") or (r.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0
    tot = sum(map(out, rows)); wasted = sum(out(r) for r in rows if not r["ok"])
    nwin = lambda r: len(r["windows"]) if "windows" in r else 1
    acc = sum(nwin(r) for r in rows if r["ok"])
    kinds = collections.Counter(r.get("kind") for r in rows if not r["ok"])
    ok_out = [out(r) / nwin(r) for r in rows if r["ok"]]
    ok_reas = [reas(r) / max(1, out(r)) for r in rows if r["ok"]]
    first = [r for r in rows if r.get("attempt") == 0]
    secs = [r["seconds"] for r in rows if r.get("seconds")]
    print(f"== {Path(run).name}: requests={len(rows)} accepted_windows={acc} "
          f"first_ok={sum(r['ok'] for r in first)}/{len(first)} transport_dropped={transport}")
    print(f"   out_tokens total={tot} per_acc_window={tot/max(acc,1):.0f} wasted_frac={wasted/max(tot,1):.2f} "
          f"ok_out_per_window(median)={statistics.median(ok_out) if ok_out else 0:.0f} reasoning_share={statistics.mean(ok_reas) if ok_reas else 0:.2f}")
    print(f"   sec/request median={statistics.median(secs):.0f} total_request_sec={sum(secs):.0f}  rejects={dict(kinds)}")
