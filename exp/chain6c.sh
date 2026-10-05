#!/bin/bash
# Tool group with fixed item normalization (+ no-narrative rerun) on the running Q3 server.
cd /scratch/fparker9/podcasts/pha-v8-exp
curl -sf --noproxy '*' http://127.0.0.1:8222/v1/models > /dev/null || exit 1
.venv/bin/python exp/xlabel.py --bench v3 --name v8g-nonarr2 --model glm53-w4 --strata health_dense mixed null ad_read discourse --concurrency 160 --drop narrative > exp/logs/v8g-nonarr2.log 2>&1 &
exp/phase6.sh tools
wait
for r in benchmark/v3/runs/v8g-*; do
  [ -f $r/score.json ] || BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark score --alias exp/alias-v8-to-v7.json $r > /dev/null 2>&1 || echo "score failed $r"
done
echo "GROUP tools scored"
echo CHAIN6_DONE
