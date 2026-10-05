#!/bin/bash
# Complete run over 1,500 random corpus windows (production-style estimate incl. the tail).
# Usage: exp/fullrun.sh <name> [args...]   (MODEL_NAME, CONC, TOOL as in tprun.sh)
cd /scratch/fparker9/podcasts/pha-v8-exp
NAME=$1; shift
W=../podcast-health-content-analysis-01/benchmark/runs/prod-sample-1000/run/windows.jsonl.zst
SCRIPT=exp/xlabel.py; [ "${TOOL:-0}" = 1 ] && SCRIPT=exp/toollabel.py
.venv/bin/python $SCRIPT --bench ${BENCH:-v3} --name full-$NAME --windows $W --ids-file exp/corpus/tp1500.ids --out-dir exp/full/$NAME --model ${MODEL_NAME:-glm53-w4} --concurrency ${CONC:-512} --metrics-log exp/full/$NAME.metrics.jsonl "$@" > exp/logs/full-$NAME.log 2>&1
echo FULLRUN_DONE $NAME
