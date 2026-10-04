#!/bin/bash
# Local DeepSeek-V4-Flash-0731 server for topic labeling (4x H100, port 8222).
#
# Same flags as tmp/vllm-launch-commands.md, plus a reasoning-parser plugin that
# fixes an O(tokens) per-step reasoning-end scan in vLLM 0.29's DeepSeek-V4
# adapter (see fast_reasoning_end_plugin.py). Extra flags are passed through.
set -eo pipefail
export VLLM_CACHE_ROOT=/tmp/vllm_cache HF_HOME=/tmp/huggingface2
export VLLM_ENGINE_READY_TIMEOUT_S=1800 VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm
source /etc/profile.d/lmod.sh 2>/dev/null || true
ml restore gpu >/dev/null 2>&1 || true
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VLLM="${VLLM:-/scratch/fparker9/vllm-29-venv/bin/vllm}"
PARSER="${REASONING_PARSER:-deepseek_v4_fast}"

exec "$VLLM" serve deepseek-ai/DeepSeek-V4-Flash-0731 \
    --trust-remote-code \
    --kv-cache-dtype fp8 --block-size 256 \
    --enable-expert-parallel --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.93 \
    --max-model-len 96K --max-num-seqs "${MAX_NUM_SEQS:-256}" \
    --enable-prefix-caching \
    --tokenizer-mode deepseek_v4 \
    --tool-call-parser deepseek_v4 --enable-auto-tool-choice \
    --reasoning-parser-plugin "$HERE/fast_reasoning_end_plugin.py" \
    --reasoning-parser "$PARSER" \
    --reasoning-config "{\"reasoning_parser\":\"$PARSER\",\"reasoning_start_str\":\"\",\"reasoning_end_str\":\"\"}" \
    --api-server-count "${API_SERVER_COUNT:-4}" \
    --async-scheduling \
    --host 0.0.0.0 --port 8222 \
    "$@"
