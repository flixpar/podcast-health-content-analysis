#!/bin/bash
# Serve an alternative labeling model with vLLM on this node's 4 H100s, port 8222.
#
#   analysis/serving/serve-model.sh qwen3.5-35b-a3b [extra vllm flags]
#
# Models: qwen3.5-35b-a3b, qwen3.8-flash-next, gpt-oss-120b, gemma-4-26b-a4b.
# Common flags follow tmp/vllm-launch-commands.md. PARALLEL=dp runs one replica
# per GPU (data parallel) instead of tensor parallel across all four, for models
# that fit on one card. Parsers built on vLLM's parser engine load the
# *_fast variants from fast_reasoning_end_plugin.py.
set -eo pipefail
export VLLM_CACHE_ROOT=/tmp/vllm_cache HF_HOME=/tmp/huggingface2
export VLLM_ENGINE_READY_TIMEOUT_S=1800 VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm
source /etc/profile.d/lmod.sh 2>/dev/null || true
ml restore gpu >/dev/null 2>&1 || true
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VLLM="${VLLM:-/scratch/fparker9/vllm-29-venv/bin/vllm}"
NAME="${1:?model name}"
shift

PLUGIN=(--reasoning-parser-plugin "$HERE/fast_reasoning_end_plugin.py")
case "$NAME" in
    qwen3.5-35b-a3b)
        MODEL=Qwen/Qwen3.5-35B-A3B-FP8
        FLAGS=("${PLUGIN[@]}" --reasoning-parser qwen3_fast --tool-call-parser qwen3_xml
               --enable-auto-tool-choice --language-model-only)
        ;;
    qwen3.8-flash-next)
        MODEL=Qwen/Qwen3.8-Flash-Next-FP8
        export VLLM_PLE_CPU_OFFLOAD=1
        FLAGS=("${PLUGIN[@]}" --reasoning-parser qwen3_fast --tool-call-parser qwen3_xml
               --enable-auto-tool-choice --no-enable-flashinfer-autotune --moe-backend triton)
        ;;
    gpt-oss-120b)
        MODEL=openai/gpt-oss-120b
        # openai_harmony fetches its vocab at request time and cannot reach the
        # blob store from the compute nodes; point it at a pre-downloaded copy of
        # o200k_base.tiktoken and cl100k_base.tiktoken from
        # https://openaipublic.blob.core.windows.net/encodings/
        export TIKTOKEN_ENCODINGS_BASE="${TIKTOKEN_ENCODINGS_BASE:-/scratch/fparker9/tiktoken_encodings}"
        FLAGS=(--reasoning-parser openai_gptoss --tool-call-parser openai --enable-auto-tool-choice)
        ;;
    gemma-4-26b-a4b)
        MODEL=google/gemma-4-26B-A4B-it
        FLAGS=("${PLUGIN[@]}" --reasoning-parser gemma4_fast --tool-call-parser gemma4
               --enable-auto-tool-choice --language-model-only)
        ;;
    *)
        echo "unknown model $NAME" >&2
        exit 2
        ;;
esac

if [ "${PARALLEL:-tp}" = dp ]; then
    # Independent replicas: expert parallel across DP ranks needs all-to-all
    # kernels and hung at startup on this build.
    PAR=(--data-parallel-size 4 --tensor-parallel-size 1)
else
    PAR=(--tensor-parallel-size 4 --enable-expert-parallel)
fi

exec "$VLLM" serve "$MODEL" \
    "${PAR[@]}" \
    --gpu-memory-utilization 0.93 \
    --max-model-len 96K --max-num-seqs "${MAX_NUM_SEQS:-256}" \
    --enable-prefix-caching --trust-remote-code \
    --api-server-count "${API_SERVER_COUNT:-4}" \
    --async-scheduling \
    --host 0.0.0.0 --port 8222 \
    "${FLAGS[@]}" "$@"
