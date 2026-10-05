#!/bin/bash
# Local GLM-5.3-Flash (W4A16 + MTP head) server for topic labeling (4x H100, port 8222).
#
#   analysis/serving/serve-glm53.sh [extra vllm flags]
#
# Tuned for the v8 labeling workload: an ~87k-token codebook shared by every
# request, one ~1.5k-token window each, outputs of ~2k tokens on average and up
# to ~30k. See docs/glm53-serving.md for the measurements behind each default.
#
#   MAX_NUM_SEQS   concurrent sequences (128). The one tuning knob: keep it
#                  below the point where the KV pool fills (watch
#                  vllm:kv_cache_usage_perc stay under ~0.8). A full pool evicts
#                  the shared-prefix checkpoint, requests stop sharing the
#                  codebook and the server collapses into preemption.
#   SPEC           speculative decoding config JSON, or "none" (default). MTP
#                  speeds up each sequence but its extra linear-attention state
#                  costs a third of the KV pool; capped servers do better
#                  without it.
#   MAX_MODEL_LEN  context (196608): the v8 prompt plus a 40k output budget.
#   GPU_MEMORY_UTILIZATION (0.92)
#
# This model needs a vLLM nightly from 2026-09-08 or later (VLLM below). On a
# node whose driver is older than the wheel's CUDA (gpu313: driver 570, cu129
# wheel) set CUDA_COMPAT to NVIDIA's cuda-compat libcuda directory and
# CUDA_HOME to a CUDA >= 12.9 toolkit for DeepGEMM/FlashInfer JIT; the defaults
# below are the user-space copies on gpu313 and are skipped when absent.
set -eo pipefail
export VLLM_CACHE_ROOT=/tmp/vllm_cache HF_HOME=/tmp/huggingface2
export VLLM_ENGINE_READY_TIMEOUT_S=2400
# Rendering the 350k-character prompt for hundreds of queued requests can take
# longer than vLLM's 30 s default, which then answers 500.
export VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT=600
set -u
VLLM="${VLLM:-/scratch/fparker9/vllm-nightly-venv/bin/vllm}"
CUDA_COMPAT="${CUDA_COMPAT:-/scratch/fparker9/cuda-compat-12-9/usr/local/cuda-12.9/compat}"
CUDA_TOOLKIT="${CUDA_HOME:-/scratch/fparker9/cuda129-rpm/usr/local/cuda-12.9}"
if [ -d "$CUDA_COMPAT" ]; then
    export LD_LIBRARY_PATH="$CUDA_COMPAT:${LD_LIBRARY_PATH:-}"
fi
if [ -d "$CUDA_TOOLKIT" ]; then
    export CUDA_HOME="$CUDA_TOOLKIT" PATH="$CUDA_TOOLKIT/bin:$PATH"
    export LD_LIBRARY_PATH="$CUDA_TOOLKIT/targets/x86_64-linux/lib:$LD_LIBRARY_PATH"
fi

SPEC="${SPEC:-none}"
SPEC_FLAGS=()
if [ "$SPEC" != none ]; then
    SPEC_FLAGS=(--speculative-config "$SPEC")
fi

exec "$VLLM" serve canada-quant/GLM-5.3-Flash-W4A16-MTP \
    --served-model-name glm53-w4 \
    --trust-remote-code \
    --language-model-only \
    --tensor-parallel-size 4 --enable-expert-parallel \
    --attention-backend FLASH_ATTN_MLA_SPARSE \
    --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.92}" \
    --max-model-len "${MAX_MODEL_LEN:-196608}" \
    --max-num-seqs "${MAX_NUM_SEQS:-128}" \
    --enable-prefix-caching \
    --enable-mamba-shared-prefix-checkpoint \
    --reasoning-parser glm45 \
    --api-server-count "${API_SERVER_COUNT:-4}" \
    --async-scheduling \
    --enable-prompt-tokens-details \
    "${SPEC_FLAGS[@]}" \
    --host 0.0.0.0 --port "${PORT:-8222}" \
    "$@"
