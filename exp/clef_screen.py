"""Clef / Clef-flash window screens as exp/scores files.

Asks the clef branch's gate questions (the TypeSafe method's health gate and the
"broad" health gate from analysis/benchmark/clef_screen.py) over each window's
transcript and writes one score file per gate: exp/scores/<prefix>-<gate>.jsonl.

    python exp/clef_screen.py --prefix clef-flash --api http://127.0.0.1:8301/v1 http://127.0.0.1:8303/v1 \
        --windows <corpus windows.jsonl.zst> --ids-file exp/corpus/sample4000.ids
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from analysis import topic_labeling as tl  # noqa: E402
from analysis import typesafe_labeling as ts  # noqa: E402
from analysis.benchmark.clef_screen import HEALTH_BROAD, ask  # noqa: E402

QUESTIONS = {"broad": HEALTH_BROAD, **ts.GATE_QUESTIONS}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--api", nargs="+", required=True)
    parser.add_argument("--model", default="clef-flash")
    parser.add_argument("--windows")
    parser.add_argument("--ids-file")
    parser.add_argument("--concurrency", type=int, default=32)
    args = parser.parse_args()
    windows = [json.loads(line) for line in open(REPO / "benchmark/v2/items.jsonl")]
    if args.windows:
        corpus = list(tl.iter_jsonl(Path(args.windows)))
        if args.ids_file:
            wanted = set(Path(args.ids_file).read_text().split())
            corpus = [w for w in corpus if w["window_id"] in wanted]
        windows += corpus
    apis = itertools.cycle(args.api)
    out = REPO / "exp/scores"
    out.mkdir(exist_ok=True)
    files = {g: open(out / f"{args.prefix}-{g}.jsonl", "w") for g in QUESTIONS}
    started = time.monotonic()

    def one(window):
        state = {"transcript": " ".join(u["text"] for u in window["units"])}
        questions = {f"gate|{g}": q for g, q in QUESTIONS.items()}
        for attempt in range(4):
            try:
                answers = ask(next(apis), args.model, state, questions)["answers"]
                return window["window_id"], {g: ts._noul(answers[f"gate|{g}"]) for g in QUESTIONS}
            except Exception as error:  # noqa: BLE001
                if attempt == 3:
                    print("failed", window["window_id"], error, file=sys.stderr)
                    return window["window_id"], None
                time.sleep(3)

    with ThreadPoolExecutor(args.concurrency) as pool:
        futures = [pool.submit(one, w) for w in windows]
        for n, f in enumerate(as_completed(futures), 1):
            window_id, scores = f.result()
            if scores:
                for g, s in scores.items():
                    files[g].write(json.dumps({"window_id": window_id, "score": s}) + "\n")
            if n % 500 == 0 or n == len(futures):
                print(f"{n}/{len(futures)} {time.monotonic() - started:.0f}s", flush=True)
    for f in files.values():
        f.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
