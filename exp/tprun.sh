#!/bin/bash
# Fixed-horizon throughput run: keep CONC requests in flight from a 4,000-window
# random corpus pool for MIN minutes, then stop. Extra args go to xlabel.py/toollabel.py.
# Usage: exp/tprun.sh <name> <minutes> [args...]   (TOOL=1 uses toollabel.py)
set -u
cd /scratch/fparker9/podcasts/pha-v8-exp
NAME=$1; MIN=$2; shift 2
W=../podcast-health-content-analysis-01/benchmark/runs/prod-sample-1000/run/windows.jsonl.zst
SCRIPT=exp/xlabel.py; [ "${TOOL:-0}" = 1 ] && SCRIPT=exp/toollabel.py
timeout --signal=KILL $((MIN*60)) .venv/bin/python $SCRIPT --bench ${BENCH:-v3} --name tp-$NAME --windows $W --ids-file exp/corpus/tp4000.ids --out-dir exp/tp/$NAME --model ${MODEL_NAME:-glm53-w4} --concurrency ${CONC:-512} --metrics-log exp/tp/$NAME.metrics.jsonl "$@" > exp/logs/tp-$NAME.log 2>&1
echo TPRUN_DONE $NAME
