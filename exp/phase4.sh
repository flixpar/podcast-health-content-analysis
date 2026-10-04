#!/bin/bash
# Phase 4: Qwen3.5-397B-A17B (GPTQ-Int4, TP4) as an alternative full labeler,
# after the Clef phase. One repeat on v7 and on v8, thinking with a 24k budget.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
log() { echo "[$(date +%T)] $*"; }
until grep -q "phase 3 done" exp/logs/phase3.log 2>/dev/null; do sleep 60; done
[ -f exp/HOLD_PHASE4 ] && { log "held"; while [ -f exp/HOLD_PHASE4 ]; do sleep 60; done; }
tmux kill-session -t clef 2>/dev/null; sleep 20; pkill -f clef_server; sleep 10
export VLLM_CACHE_ROOT=/tmp/vllm_cache HF_HOME=/tmp/huggingface2 VLLM_ENGINE_READY_TIMEOUT_S=1800 VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm
tmux new-session -d -s qwen -n server "cd $PWD; source /etc/profile.d/lmod.sh 2>/dev/null; ml restore gpu >/dev/null 2>&1; /scratch/fparker9/vllm-29-venv/bin/vllm serve Qwen/Qwen3.5-397B-A17B-GPTQ-Int4 --tensor-parallel-size 4 --enable-expert-parallel --gpu-memory-utilization 0.93 --max-model-len 196608 --max-num-seqs 256 --enable-prefix-caching --trust-remote-code --api-server-count 4 --async-scheduling --host 0.0.0.0 --port 8222 --language-model-only --reasoning-parser-plugin analysis/serving/fast_reasoning_end_plugin.py --reasoning-parser qwen3_fast --tool-call-parser qwen3_xml --enable-auto-tool-choice 2>&1 | tee exp/logs/qwen-server.log; sleep 100000"
until curl -s --noproxy '*' http://127.0.0.1:8222/v1/models | grep -q Qwen; do sleep 15; grep -q -E 'Traceback|Error' exp/logs/qwen-server.log && grep -q 'EngineCore failed\|RuntimeError' exp/logs/qwen-server.log && { log "server failed"; exit 1; }; done
log "qwen up"
for v in 7 8; do
  bd=benchmark/v$((v-5))
  tmux new-window -t qwen -n q$v "cd $PWD; BENCHMARK_DIR=$bd $PY -m analysis.benchmark run --name v$v-qwen397-b24k --pipeline-config benchmark/pipeline-local.toml --repeats 1 --split all -- --model Qwen/Qwen3.5-397B-A17B-GPTQ-Int4 2>&1 | tee exp/logs/v$v-qwen397.log"
done
log "qwen runs queued"
