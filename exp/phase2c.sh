#!/bin/bash
# Third repeats of the v7/v8 high runs (silver references need 2-of-3 consensus).
cd "$(dirname "$0")/.."
until grep -q queued exp/logs/phase2.log 2>/dev/null; do sleep 30; done
PY=.venv/bin/python
for v in 7 8; do
  bd=benchmark/v$((v-5))
  tmux new-window -t vllm -n v$v-hb24-r3 "cd $PWD; BENCHMARK_DIR=$bd $PY -m analysis.benchmark run --name v$v-high-b24k --pipeline-config benchmark/pipeline-local.toml --repeats 3 --split all --notes 'v$v prompt, high, 24k budget' 2>&1 | tee exp/logs/v$v-high-b24k-r3.log"
done
echo "[$(date +%T)] third repeats queued"
