#!/bin/bash
# Build a "silver" benchmark: the benchmark's items scored against gold made from
# DeepSeek-high repeats (2-of-3 consensus, no adjudication).
#   exp/make_silver.sh v2 exp/silver-v7 benchmark/v2/runs/v7-high-b24k
set -eu
src=benchmark/$1; out=$2; run=$3
cd "$(dirname "$0")/.."
rm -rf $out; mkdir -p $out
cp $src/config.toml $src/items.jsonl $src/taxonomy.json $out/
# The codebook path in config.toml is repo-relative, so it still resolves.
echo '{}' > $out/annotators.json
for r in 0 1 2; do
  BENCHMARK_DIR=$out .venv/bin/python -m analysis.benchmark reference add-run $run --annotator ds-r$r --repeat $r
done
BENCHMARK_DIR=$out .venv/bin/python -m analysis.benchmark aggregate | tail -3
