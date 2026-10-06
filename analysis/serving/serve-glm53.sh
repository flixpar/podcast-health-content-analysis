#!/bin/bash
# Local GLM-5.3-Flash (W4A16 + MTP head) server for topic labeling (4x H100, port 8222).
#
#   analysis/serving/serve-glm53.sh [extra vllm flags]
#
# Tuned for the v8 labeling workload: an ~87k-token codebook shared by every
# request, one ~1.5k-token window each, outputs of ~2k tokens on average and up
# to ~30k. See docs/glm53-serving.md for the measurements behind each default.
#
#   MAX_NUM_SEQS   concurrent sequences (160; 224 with KDA_STATE_DTYPE=bfloat16).
#                  The one tuning knob: keep it below the point where the KV
#                  pool fills (watch vllm:kv_cache_usage_perc stay under ~0.8).
#                  A full pool evicts the shared-prefix checkpoint, requests
#                  stop sharing the codebook and the server collapses into
#                  preemption.
#   KDA_STATE_DTYPE  float32 (default) or bfloat16 for the linear-attention
#                  recurrent state. bfloat16 halves the per-request state, so
#                  more requests fit (+23% windows/h with the 224 cap, no
#                  measured quality change), but vLLM ignores the setting for
#                  this model unless patches/vllm-glm5next-kda-state-dtype.patch
#                  is applied to the vLLM install; the script checks.
#   SPEC           speculative decoding config JSON, or "none" (default). MTP
#                  speeds up each sequence but its extra linear-attention state
#                  costs a third of the KV pool; capped servers do better
#                  without it.
#   MAX_MODEL_LEN  context (196608): the v8 prompt plus a 40k output budget.
#   GPU_MEMORY_UTILIZATION (0.95; boots on 80 GB H100s and adds ~8% to the KV pool)
#
# Use a compatible vLLM installation on PATH, or set VLLM to its executable.
# If your driver/toolkit needs CUDA compatibility libraries, explicitly set
# CUDA_COMPAT and CUDA_HOME to the matching installed directories.
set -eo pipefail
export VLLM_CACHE_ROOT="${VLLM_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/vllm}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export VLLM_ENGINE_READY_TIMEOUT_S="${VLLM_ENGINE_READY_TIMEOUT_S:-2400}"
# Rendering the 350k-character prompt for hundreds of queued requests can take
# longer than vLLM's 30 s default, which then answers 500.
export VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT="${VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT:-600}"
# One CPU thread per worker: an inherited OMP_NUM_THREADS=16 makes
# every GPU worker spin ~3 cores in torch CPU ops for nothing, which throttles
# the server when it shares or is pinned to a few cores.
export OMP_NUM_THREADS="${VLLM_OMP_NUM_THREADS:-1}"
set -u
VLLM="${VLLM:-vllm}"
CUDA_TOOLKIT="${CUDA_HOME:-}"
if [ -n "${CUDA_COMPAT:-}" ] && [ -d "$CUDA_COMPAT" ]; then
    export LD_LIBRARY_PATH="$CUDA_COMPAT${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
if [ -d "$CUDA_TOOLKIT" ]; then
    export CUDA_HOME="$CUDA_TOOLKIT" PATH="$CUDA_TOOLKIT/bin:$PATH"
    export LD_LIBRARY_PATH="$CUDA_TOOLKIT/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

KDA_STATE_DTYPE="${KDA_STATE_DTYPE:-float32}"
DEFAULT_SEQS=160
if [ "$KDA_STATE_DTYPE" = bfloat16 ]; then
    VLLM_EXECUTABLE="$(command -v "$VLLM")"
    VLLM_PYTHON="${VLLM_PYTHON:-$(dirname "$VLLM_EXECUTABLE")/python}"
    GLM_KDA="$("$VLLM_PYTHON" -c 'import os, vllm; print(os.path.join(os.path.dirname(vllm.__file__), "models/glm5next/common/kda.py"))')"
    if ! grep -q "mamba_ssm_cache_dtype" "$GLM_KDA"; then
        SITE="$(dirname "$(dirname "$(dirname "$(dirname "$(dirname "$GLM_KDA")")")")")"
        echo "KDA_STATE_DTYPE=bfloat16 needs the vLLM patch; without it vLLM keeps the state" >&2
        echo "in float32 and the higher cap overfills the KV pool. Apply it with:" >&2
        echo "  patch -d $SITE -p1 < $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/patches/vllm-glm5next-kda-state-dtype.patch" >&2
        exit 2
    fi
    DEFAULT_SEQS=224
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
    --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.95}" \
    --max-model-len "${MAX_MODEL_LEN:-196608}" \
    --max-num-seqs "${MAX_NUM_SEQS:-$DEFAULT_SEQS}" \
    --mamba-ssm-cache-dtype "$KDA_STATE_DTYPE" \
    --enable-prefix-caching \
    --enable-mamba-shared-prefix-checkpoint \
    --reasoning-parser glm45 \
    --api-server-count "${API_SERVER_COUNT:-4}" \
    --async-scheduling \
    --enable-prompt-tokens-details \
    "${SPEC_FLAGS[@]}" \
    --host 0.0.0.0 --port "${PORT:-8222}" \
    "$@"
