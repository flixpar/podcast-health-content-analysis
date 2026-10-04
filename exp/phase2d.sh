#!/bin/bash
# Relaunch the paused long-tail clients once the server queue has drained.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
W=../podcast-health-content-analysis-01/benchmark/runs/prod-sample-1000/run/windows.jsonl.zst
waiting() { curl -s --noproxy '*' http://127.0.0.1:8222/metrics | grep -E '^vllm:num_requests_waiting\{' | awk '{print int($2)}'; }
until [ "$(waiting)" -lt 30 ]; do sleep 30; done
run() { local name=$1; shift; tmux new-window -t vllm -n "$name" "cd $PWD; $* 2>&1 | tee -a exp/logs/$name.log"; }
run ds-screen $PY exp/xlabel.py --bench v3 --name ds-screen --mode screen --effort none --budget 0 --max-tokens 400 --windows $W --out-dir exp/corpus/ds-screen --concurrency 256
echo "[$(date +%T)] ds-screen relaunched"
sleep 600
for v in 7 8; do
  bd=benchmark/v$((v-5))
  run v$v-hb24-r3 "BENCHMARK_DIR=$bd $PY -m analysis.benchmark run --name v$v-high-b24k --pipeline-config benchmark/pipeline-local.toml --repeats 3 --split all --notes 'v$v prompt, high, 24k budget'"
done
run v7-hints $PY exp/xlabel.py --bench v2 --name v7-hints-llm --mode hints --lexicon exp/lexicon-llm-v2.json --concurrency 128
run v8-hints $PY exp/xlabel.py --bench v3 --name v8-hints-llm --mode hints --lexicon exp/lexicon-llm-v3.json --concurrency 128
echo "[$(date +%T)] long tail relaunched"
