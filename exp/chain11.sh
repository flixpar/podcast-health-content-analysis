#!/bin/bash
# Throughput of bf16 KDA state and higher GPU memory utilization, CPU-pinned (session), OMP_NUM_THREADS=1.
cd /scratch/fparker9/podcasts/pha-v8-exp
SERVE=/scratch/fparker9/podcasts/pha-glm53/analysis/serving/serve-glm53.sh
H="--strata health_dense mixed null ad_read discourse"
boot() {  # tag, env assignments..., -- extra flags
  local tag=$1; shift
  tmux kill-window -t glm:g53 2>/dev/null
  while nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1>2000{f=1} END{exit !f}'; do sleep 3; done
  local LOG=exp/logs/glm-server-$tag.log
  echo "$*" > $LOG
  tmux new-window -t glm -n g53 "cd /scratch/fparker9/podcasts/pha-glm53; env $* 2>&1 | tee -a /scratch/fparker9/podcasts/pha-v8-exp/$LOG; echo SERVER_EXITED >> /scratch/fparker9/podcasts/pha-v8-exp/$LOG; sleep 1000000"
  echo "booting $tag"
  exp/wait-server.sh $LOG || return 1
  grep -h "GPU KV cache size\|attention block size\|Padding mamba" $LOG | head -2 | sed 's/.*INFO/INFO/'
}
export OMP_NUM_THREADS=1
# 0. fp32 baseline under the same CPU pinning
boot P0-fp32-128 OMP_NUM_THREADS=1 MAX_NUM_SEQS=128 $SERVE && CONC=384 exp/fullrun.sh pin-fp32-128
# 1. bf16 state
for n in 128 192 256; do
  boot P1-bf16-$n OMP_NUM_THREADS=1 MAX_NUM_SEQS=$n $SERVE --mamba-ssm-cache-dtype bfloat16 && CONC=$((n*3)) exp/fullrun.sh pin-bf16-$n
done
# 2. fp32 state, higher GPU memory utilization
if boot P2-gmu95 OMP_NUM_THREADS=1 MAX_NUM_SEQS=160 GPU_MEMORY_UTILIZATION=0.95 $SERVE; then
  CONC=480 exp/fullrun.sh pin-gmu95-160
else
  boot P2-gmu94 OMP_NUM_THREADS=1 MAX_NUM_SEQS=160 GPU_MEMORY_UTILIZATION=0.94 $SERVE && CONC=480 exp/fullrun.sh pin-gmu94-160
fi
echo CHAIN11_DONE
