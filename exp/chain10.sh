#!/bin/bash
# bf16 KDA recurrent state and higher GPU memory utilization (GLM-5.3-Flash, G1-style serving).
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
# 1. bf16 state, cap 128: quality x2, complete run
if boot S1-bf16-128 MAX_NUM_SEQS=128 $SERVE --mamba-ssm-cache-dtype bfloat16; then
  .venv/bin/python exp/xlabel.py --bench v3 --name v8gb-high-r1 --model glm53-w4 $H --concurrency 160 > exp/logs/v8gb-high-r1.log 2>&1 &
  .venv/bin/python exp/xlabel.py --bench v3 --name v8gb-high-r2 --model glm53-w4 $H --concurrency 160 > exp/logs/v8gb-high-r2.log 2>&1 &
  wait
  for r in v8gb-high-r1 v8gb-high-r2; do BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark score --alias exp/alias-v8-to-v7.json benchmark/v3/runs/$r > /dev/null 2>&1; done
  echo QUALITY_DONE
  CONC=384 exp/fullrun.sh glm-bf16-128
fi
# 2. bf16 state, higher caps
for n in 192 256; do
  boot S2-bf16-$n MAX_NUM_SEQS=$n $SERVE --mamba-ssm-cache-dtype bfloat16 && CONC=$((n*3)) exp/fullrun.sh glm-bf16-$n
done
# 3. fp32 state, higher GPU memory utilization
if boot S3-gmu95 MAX_NUM_SEQS=160 GPU_MEMORY_UTILIZATION=0.95 $SERVE; then
  CONC=480 exp/fullrun.sh glm-gmu95-160
else
  echo "gmu 0.95 failed; trying 0.94"
  boot S3-gmu94 MAX_NUM_SEQS=160 GPU_MEMORY_UTILIZATION=0.94 $SERVE && CONC=480 exp/fullrun.sh glm-gmu94-160
fi
echo CHAIN10_DONE
