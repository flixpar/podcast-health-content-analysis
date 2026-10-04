#!/bin/bash
# Score runs against a silver benchmark without touching their gold score.json:
#   exp/silver_score.sh exp/silver-v7 benchmark/v2/runs/v7-low-b24k ...
silver=$1; shift
cd "$(dirname "$0")/.."
for run in "$@"; do
  out=exp/silver-scores/$(basename $silver)/$(basename $run)
  rm -rf $out; mkdir -p $out
  cp $run/run_manifest.json $out/; for r in $run/repeat_*; do mkdir -p $out/$(basename $r); cp $r/labels.sqlite $out/$(basename $r)/; [ -f $r/attempts.jsonl ] && cp $r/attempts.jsonl $out/$(basename $r)/; done
  BENCHMARK_DIR=$silver .venv/bin/python -m analysis.benchmark score $out ${ALIAS:+--alias $ALIAS} > /dev/null || echo "failed $run"
done
