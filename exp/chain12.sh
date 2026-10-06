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
export OMP_NUM_THREADS=1 HF_HUB_OFFLINE=1
E="OMP_NUM_THREADS=1 HF_HUB_OFFLINE=1"
boot P1-bf16-256 $E MAX_NUM_SEQS=256 $SERVE --mamba-ssm-cache-dtype bfloat16 && CONC=768 exp/fullrun.sh pin-bf16-256
if boot P2-gmu95 $E MAX_NUM_SEQS=160 GPU_MEMORY_UTILIZATION=0.95 $SERVE; then
  CONC=480 exp/fullrun.sh pin-gmu95-160
  G=0.95
else
  boot P2-gmu94 $E MAX_NUM_SEQS=160 GPU_MEMORY_UTILIZATION=0.94 $SERVE && CONC=480 exp/fullrun.sh pin-gmu94-160
  G=0.94
fi
boot P3-bf16-gmu-224 $E MAX_NUM_SEQS=224 GPU_MEMORY_UTILIZATION=$G $SERVE --mamba-ssm-cache-dtype bfloat16 && CONC=672 exp/fullrun.sh pin-bf16-gmu-224
echo CHAIN12_DONE
