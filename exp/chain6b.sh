#!/bin/bash
# Resume the tool group (+ high repeat, no-narrative rerun) on a priority-scheduled GLM server.
cd /scratch/fparker9/podcasts/pha-v8-exp
TAG=Q3 SPEC=none SEQS=80 EXTRA="--enable-mamba-shared-prefix-checkpoint --api-server-count 4 --async-scheduling --trust-request-chat-template --scheduling-policy priority" exp/serve-glm.sh
exp/wait-server.sh exp/logs/glm-server-Q3.log || exit 1
.venv/bin/python exp/xlabel.py --bench v3 --name v8g-nonarr2 --model glm53-w4 --strata health_dense mixed null ad_read discourse --concurrency 160 --drop narrative > exp/logs/v8g-nonarr2.log 2>&1 &
exp/phase6.sh tools
wait
for r in benchmark/v3/runs/v8g-*; do
  [ -f $r/score.json ] || BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark score --alias exp/alias-v8-to-v7.json $r > /dev/null 2>&1 || echo "score failed $r"
done
echo "GROUP tools scored"
echo CHAIN6_DONE
