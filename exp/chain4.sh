#!/bin/bash
# Qwen3.8-Flash-Next-FP8: boot, smoke, v8 headline quality (xhigh, low), throughput.
cd /scratch/fparker9/podcasts/pha-v8-exp
while ! grep -q CHAIN3_DONE exp/logs/chain3.log 2>/dev/null; do sleep 10; done
PY=.venv/bin/python
H="--strata health_dense mixed null ad_read discourse"
TAG=q1 EXTRA="--enable-mamba-shared-prefix-checkpoint --api-server-count 4" exp/serve-qwen38.sh
if ! exp/wait-server.sh exp/logs/qwen38-server-q1.log; then
  echo "qwen: retry without the checkpoint flag"
  TAG=q2 EXTRA="--api-server-count 4" exp/serve-qwen38.sh
  exp/wait-server.sh exp/logs/qwen38-server-q2.log || { echo QWEN_FAILED; echo CHAIN4_DONE; exit 1; }
fi
$PY exp/xlabel.py --bench v3 --name smoke-qwen --out-dir exp/tmp/smoke-qwen --model qwen38 --strata health_dense --limit 3 --effort xhigh > exp/logs/smoke-qwen.log 2>&1
$PY exp/xlabel.py --bench v3 --name v8q-xhigh --model qwen38 $H --concurrency 160 --effort xhigh > exp/logs/v8q-xhigh.log 2>&1 &
$PY exp/xlabel.py --bench v3 --name v8q-low --model qwen38 $H --concurrency 160 --effort low > exp/logs/v8q-low.log 2>&1 &
wait
for r in benchmark/v3/runs/v8q-*; do BENCHMARK_DIR=benchmark/v2 $PY -m analysis.benchmark score --alias exp/alias-v8-to-v7.json $r > /dev/null 2>&1; done
MODEL_NAME=qwen38 exp/tprun.sh qwen38-xhigh 20 --effort xhigh
echo CHAIN4_DONE
