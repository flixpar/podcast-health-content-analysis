#!/bin/bash
# Phase 5: GLM-5.3-Flash (W4A16 + MTP) on the vLLM nightly venv, after the Qwen runs.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
log() { echo "[$(date +%T)] $*"; }
: # qwen already done
: #
until grep -q DONE /tmp/claude-40481/venv-nightly.log 2>/dev/null; do sleep 30; done
log "qwen done, venv ready"
: #
serve() {
  tmux new-session -d -s glm -n server "cd $PWD; export CUDA_HOME=/scratch/fparker9/cuda129-rpm/usr/local/cuda-12.9 PATH=/scratch/fparker9/cuda129-rpm/usr/local/cuda-12.9/bin:\$PATH LD_LIBRARY_PATH=/scratch/fparker9/cuda-compat-12-9/usr/local/cuda-12.9/compat:/scratch/fparker9/cuda129-rpm/usr/local/cuda-12.9/targets/x86_64-linux/lib:\$LD_LIBRARY_PATH HF_HOME=/tmp/huggingface2 VLLM_CACHE_ROOT=/tmp/vllm_cache VLLM_ENGINE_READY_TIMEOUT_S=2400; /scratch/fparker9/vllm-nightly-venv/bin/vllm serve canada-quant/GLM-5.3-Flash-W4A16-MTP --served-model-name glm53-w4 --tensor-parallel-size 4 --enable-expert-parallel --max-model-len 196608 --max-num-seqs 256 --gpu-memory-utilization 0.92 $1 --speculative-config '{\"method\":\"mtp\",\"num_speculative_tokens\":2}' --reasoning-parser glm45 --tool-call-parser glm47 --enable-auto-tool-choice --trust-remote-code --attention-backend FLASH_ATTN_MLA_SPARSE --language-model-only --host 0.0.0.0 --port 8222 2>&1 | tee -a exp/logs/glm-server.log; echo SERVER_EXITED >> exp/logs/glm-server.log; sleep 100000"
}
wait_up() {
  until curl -s --noproxy '*' http://127.0.0.1:8222/v1/models | grep -q glm53; do
    grep -q SERVER_EXITED exp/logs/glm-server.log && return 1; sleep 15; done
}
serve --enable-prefix-caching
if ! wait_up; then
  log "prefix caching failed to boot; retrying without"
  tmux kill-session -t glm; sleep 20; : > exp/logs/glm-server.log
  serve --no-enable-prefix-caching
  wait_up || { log "server failed"; exit 1; }
fi
log "glm up"
for v in 7 8; do
  bd=benchmark/v$((v-5))
  tmux new-window -t glm -n g$v "cd $PWD; BENCHMARK_DIR=$bd $PY -m analysis.benchmark run --name v$v-glm53-b24k --pipeline-config benchmark/pipeline-local.toml --repeats 1 --split all -- --model glm53-w4 2>&1 | tee exp/logs/v$v-glm53.log"
done
log "glm runs queued"
