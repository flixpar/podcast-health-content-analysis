"""What the System One method costs on real corpus windows, not benchmark ones.

The benchmark's strata are far denser in health content than the corpus, so
tokens per benchmark window over-state what a corpus pass costs. This labels a
run of consecutive windows from a production run's windows file (whole
episodes, so the real mix of empty and health windows) under a policy and the
production taxonomy, through the same validator, and reports tokens and
seconds per window.

    .venv/bin/python -m analysis.benchmark.clef_corpus_cost \
        /scratch/fparker9/podcasts/podcast-misinfo/outputs/fullrun \
        --endpoint http://127.0.0.1:8302/v1 --model clef \
        --policy benchmark/policies/clef-efficient.toml --windows 300
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean
from typing import Sequence

from analysis import topic_labeling as tl
from analysis import typesafe_labeling as typesafe
from analysis.benchmark.clef_screen import ask as http_ask
from analysis.benchmark.clef_screen import corpus_windows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("corpus", type=Path, help="Production label directory (labels.sqlite, windows.jsonl.zst, taxonomy.json)")
    parser.add_argument("--endpoint", nargs="+", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--windows", type=int, default=300)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    taxonomy = tl.load_taxonomy(args.corpus / "taxonomy.json")
    axes = {label["label_id"]: label["axis"] for label in taxonomy["labels"]}
    overrides = tomllib.loads(args.policy.read_text()) if args.policy else {}
    policy = typesafe.Policy.from_mapping(overrides)
    entries = list(corpus_windows(args.corpus, args.windows))

    def one(index_entry):
        index, entry = index_entry
        endpoint = args.endpoint[index % len(args.endpoint)]
        started = time.monotonic()
        raw, judgments = typesafe.label_window(
            entry["window"], taxonomy, policy, lambda state, questions: http_ask(endpoint, args.model, state, questions)
        )
        result = tl.validate_response(raw, entry["window"], axes)
        return {
            "window_id": entry["window"]["window_id"],
            "seconds": time.monotonic() - started,
            "tokens": judgments["usage"]["input_tokens"],
            "requests": judgments["usage"]["requests"],
            "by_stage": judgments["usage"]["input_tokens_by_stage"],
            "atoms": sum(len(result[key]) for key in ("detections", "verification_candidates", "product_mentions")),
            "reference_positive": entry["reference"]["positive"],
        }

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        rows = list(pool.map(one, enumerate(entries)))
    wall = time.monotonic() - started
    stopped = [row for row in rows if set(row["by_stage"]) <= {"gate"}]
    print(f"{len(rows)} windows in {wall:.0f}s ({len(rows) / wall * 3600:,.0f} windows/h over {len(args.endpoint)} endpoint(s))")
    print(f"tokens per window {mean(row['tokens'] for row in rows):,.0f}; "
          f"{len(stopped) / len(rows):.1%} stopped at the gate; "
          f"tokens per window that went on {mean(row['tokens'] for row in rows if row not in stopped) if len(stopped) < len(rows) else 0:,.0f}")
    print(f"windows with any output {sum(row['atoms'] > 0 for row in rows) / len(rows):.1%} "
          f"(the DeepSeek run: {sum(row['reference_positive'] for row in rows) / len(rows):.1%})")
    if args.out:
        args.out.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
