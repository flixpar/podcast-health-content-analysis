#!/bin/bash
# DeepSeek phase 2: after the v7/v8 high-effort benchmark runs, restart the
# server at 512 sequences and queue the corpus references and the variants.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
W=../podcast-health-content-analysis-01/benchmark/runs/prod-sample-1000/run/windows.jsonl.zst
IDS=exp/corpus/sample4000.ids
log() { echo "[$(date +%T)] $*"; }
until curl -s --noproxy "*" http://127.0.0.1:8222/v1/models | grep -q DeepSeek; do sleep 10; done; log "server up at 512"
run() { local name=$1; shift; tmux new-window -t vllm -n "$name" "cd $PWD; $* 2>&1 | tee exp/logs/$name.log"; }

# 3. corpus references (v8 is the screen reference; v7 for v7-vs-v8 yields)
run corpus-v8 $PY exp/xlabel.py --bench v3 --name corpus-v8-high --windows $W --ids-file $IDS --out-dir exp/corpus/v8-high --concurrency 192
run corpus-v7 $PY exp/xlabel.py --bench v2 --name corpus-v7-high --windows $W --ids-file $IDS --out-dir exp/corpus/v7-high --concurrency 128
# 4. cheap DeepSeek modes on the benchmark, production path
run v7-none "BENCHMARK_DIR=benchmark/v2 $PY -m analysis.benchmark run --name v7-none --pipeline-config benchmark/pipeline-local.toml --repeats 2 --split all -- --reasoning-effort none --max-output-tokens 30000"
run v8-none "BENCHMARK_DIR=benchmark/v3 $PY -m analysis.benchmark run --name v8-none --pipeline-config benchmark/pipeline-local.toml --repeats 2 --split all -- --reasoning-effort none --max-output-tokens 30000"
run v7-low "BENCHMARK_DIR=benchmark/v2 $PY -m analysis.benchmark run --name v7-low-b24k --pipeline-config benchmark/pipeline-local.toml --repeats 1 --split all -- --reasoning-effort low"
run v7-nobudget "BENCHMARK_DIR=benchmark/v2 $PY -m analysis.benchmark run --name v7-high-nobudget --pipeline-config benchmark/pipeline-local-nobudget.toml --repeats 1 --split all"
# 5. DeepSeek no-thinking screen over the benchmark and the whole corpus sample
run ds-screen $PY exp/xlabel.py --bench v3 --name ds-screen --mode screen --effort none --budget 0 --max-tokens 400 --windows $W --out-dir exp/corpus/ds-screen --concurrency 128
run ds-screen-bench $PY exp/xlabel.py --bench v3 --name ds-screen-bench --mode screen --effort none --budget 0 --max-tokens 400 --out-dir exp/corpus/ds-screen-bench --concurrency 64
# 6. second-pass refinement of the v7 high run (repeat 0 as the first pass)
run v7-refine $PY exp/xlabel.py --bench v2 --name v7-refine --mode refine --base-run benchmark/v2/runs/v7-high-b24k --concurrency 128
log "queued"
