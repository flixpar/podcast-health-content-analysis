#!/bin/bash
# Start DeepSeek-V4-Flash (analysis/serving/serve-deepseek-v4.sh) in tmux glm:dserver, killing any vLLM.
# Env: TAG, SEQS (512), EXTRA (extra serve flags, e.g. a speculative config).
set -u
TAG=${TAG:-ds}; SEQS=${SEQS:-512}; EXTRA=${EXTRA:-}
cd /scratch/fparker9/podcasts/pha-v8-exp
pkill -f 'vllm serve' ; pkill -f 'VLLM::' ; sleep 5
while nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1>2000{f=1} END{exit !f}'; do sleep 3; done
LOG=exp/logs/ds-server-$TAG.log
CMD="MAX_NUM_SEQS=$SEQS MAX_MODEL_LEN=196608 analysis/serving/serve-deepseek-v4.sh --enable-prompt-tokens-details $EXTRA"
echo "$CMD" > $LOG
for w in server qserver dserver; do tmux kill-window -t glm:$w 2>/dev/null; done
tmux new-window -t glm -n dserver "cd $PWD; $CMD 2>&1 | tee -a $LOG; echo SERVER_EXITED >> $LOG; sleep 1000000"
echo started $TAG
