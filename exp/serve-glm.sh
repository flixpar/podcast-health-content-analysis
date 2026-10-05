#!/bin/bash
# Start GLM-5.3-Flash-W4A16-MTP on port 8222 in tmux session "glm" (window "server"),
# killing any running vLLM first. Config by env:
#   TAG       log name suffix (exp/logs/glm-server-$TAG.log)
#   SPEC      speculative config JSON, or "none" (default MTP 2)
#   SEQS      --max-num-seqs (default 256)
#   GMU       --gpu-memory-utilization (default 0.92)
#   MAXLEN    --max-model-len (default 196608)
#   MODEL     HF repo (default canada-quant/GLM-5.3-Flash-W4A16-MTP)
#   EXTRA     extra serve flags
set -u
TAG=${TAG:-default}
SPEC=${SPEC:-'{"method":"mtp","num_speculative_tokens":2}'}
SEQS=${SEQS:-256}; GMU=${GMU:-0.92}; MAXLEN=${MAXLEN:-196608}
MODEL=${MODEL:-canada-quant/GLM-5.3-Flash-W4A16-MTP}
EXTRA=${EXTRA:-}
cd /scratch/fparker9/podcasts/pha-v8-exp
pkill -f 'vllm serve' ; pkill -f 'VLLM::' ; sleep 5
while nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1>2000{f=1} END{exit !f}'; do sleep 3; done
SPECFLAG=""; [ "$SPEC" != none ] && SPECFLAG="--speculative-config '$SPEC'"
LOG=exp/logs/glm-server-$TAG.log
CMD="export CUDA_HOME=/scratch/fparker9/cuda129-rpm/usr/local/cuda-12.9 PATH=/scratch/fparker9/cuda129-rpm/usr/local/cuda-12.9/bin:\$PATH LD_LIBRARY_PATH=/scratch/fparker9/cuda-compat-12-9/usr/local/cuda-12.9/compat:/scratch/fparker9/cuda129-rpm/usr/local/cuda-12.9/targets/x86_64-linux/lib:\$LD_LIBRARY_PATH HF_HOME=/tmp/huggingface2 VLLM_CACHE_ROOT=/tmp/vllm_cache VLLM_ENGINE_READY_TIMEOUT_S=2400 VLLM_CHAT_TEMPLATE_RENDER_TIMEOUT=600; /scratch/fparker9/vllm-nightly-venv/bin/vllm serve $MODEL --served-model-name glm53-w4 --tensor-parallel-size 4 --enable-expert-parallel --max-model-len $MAXLEN --max-num-seqs $SEQS --gpu-memory-utilization $GMU $SPECFLAG --reasoning-parser glm45 --tool-call-parser glm47 --enable-auto-tool-choice --trust-remote-code --attention-backend FLASH_ATTN_MLA_SPARSE --language-model-only --enable-prompt-tokens-details --host 0.0.0.0 --port 8222 $EXTRA"
echo "$CMD" > $LOG
tmux kill-window -t glm:server 2>/dev/null
tmux has-session -t glm 2>/dev/null || tmux new-session -d -s glm -n keep "sleep 1000000"
tmux new-window -t glm -n server "cd $PWD; $CMD 2>&1 | tee -a $LOG; echo SERVER_EXITED >> $LOG; sleep 1000000"
echo started $TAG
