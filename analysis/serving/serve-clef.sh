#!/usr/bin/env bash
# Serve a Clef model on one GPU behind a local /v1/systemone endpoint.
#
#   analysis/serving/serve-clef.sh clef-flash 0 8301
#   analysis/serving/serve-clef.sh clef 1 8302 [extra clef_server flags]
#
# Weights come from the Hugging Face cache (download once with
# `hf download Cloudflare/clef-flash`). Kernel autotuning results are cached on
# disk, so only the first start on a machine pays the full warm-up.
set -euo pipefail
model=${1:?model: clef or clef-flash}
gpu=${2:?gpu index}
port=${3:?port}
shift 3
cd "$(dirname "$0")/../.."
export CUDA_VISIBLE_DEVICES=$gpu
export HF_HUB_OFFLINE=${HF_HUB_OFFLINE:-1}
export TRITON_CACHE_AUTOTUNING=1
exec .venv/bin/python -m analysis.serving.clef_server --model "$model" --port "$port" "$@"
