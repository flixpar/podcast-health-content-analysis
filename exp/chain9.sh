#!/bin/bash
# Qwen3.8 follow-up: medium effort quality, low effort throughput.
cd /scratch/fparker9/podcasts/pha-v8-exp
while ! grep -q CHAIN8_DONE exp/logs/chain8.log 2>/dev/null; do sleep 10; done
TAG=q3 EXTRA="--enable-mamba-shared-prefix-checkpoint --api-server-count 4" exp/serve-qwen38.sh
exp/wait-server.sh exp/logs/qwen38-server-q3.log || { echo CHAIN9_DONE; exit 1; }
.venv/bin/python exp/xlabel.py --bench v3 --name v8q-medium --model qwen38 --strata health_dense mixed null ad_read discourse --concurrency 160 --effort medium > exp/logs/v8q-medium.log 2>&1
BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark score --alias exp/alias-v8-to-v7.json benchmark/v3/runs/v8q-medium > /dev/null 2>&1
MODEL_NAME=qwen38 exp/tprun.sh qwen38-low 20 --effort low
echo CHAIN9_DONE
