#!/bin/bash
# Clef phase: after every DeepSeek job is done, swap the node to four Clef
# servers (two Clef-flash, two Clef) and run the screens and hierarchical labelers.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
W=../podcast-health-content-analysis-01/benchmark/runs/prod-sample-1000/run/windows.jsonl.zst
IDS=exp/corpus/sample4000.ids
log() { echo "[$(date +%T)] $*"; }

while [ "$(tmux list-windows -t vllm -F '#W' 2>/dev/null | grep -vc '^server$')" != "0" ]; do sleep 60; done
log "DeepSeek jobs done"
[ -f exp/HOLD_PHASE3 ] && { log "held"; while [ -f exp/HOLD_PHASE3 ]; do sleep 60; done; }
tmux kill-session -t vllm; sleep 30
pkill -f 'vllm serve'; sleep 10

export HF_HOME=/tmp/huggingface2
tmux new-session -d -s clef -n flash0 "cd $PWD; HF_HOME=$HF_HOME bash analysis/serving/serve-clef.sh clef-flash 0 8301 2>&1 | tee exp/logs/clef-flash0.log; sleep 100000"
tmux new-window -t clef -n flash1 "cd $PWD; HF_HOME=$HF_HOME bash analysis/serving/serve-clef.sh clef-flash 1 8303 2>&1 | tee exp/logs/clef-flash1.log; sleep 100000"
tmux new-window -t clef -n clef2 "cd $PWD; HF_HOME=$HF_HOME bash analysis/serving/serve-clef.sh clef 2 8302 2>&1 | tee exp/logs/clef2.log; sleep 100000"
tmux new-window -t clef -n clef3 "cd $PWD; HF_HOME=$HF_HOME bash analysis/serving/serve-clef.sh clef 3 8304 2>&1 | tee exp/logs/clef3.log; sleep 100000"
for port in 8301 8303 8302 8304; do
  until curl -s --noproxy '*' http://127.0.0.1:$port/v1/models | grep -q .; do sleep 15; done
done
log "clef servers up"

FLASH="http://127.0.0.1:8301/v1 http://127.0.0.1:8303/v1"
CLEF="http://127.0.0.1:8302/v1 http://127.0.0.1:8304/v1"
# Screens first (minutes), one model family per pair of GPUs.
$PY exp/clef_screen.py --prefix clef-flash --model clef-flash --api $FLASH --windows $W --ids-file $IDS --concurrency 32 > exp/logs/clef-screen-flash.log 2>&1 &
$PY exp/clef_screen.py --prefix clef --model clef --api $CLEF --windows $W --ids-file $IDS --concurrency 32 > exp/logs/clef-screen-clef.log 2>&1 &
wait
log "screens done"
# Hierarchical labelers on the benchmark, v7 and v8, both models.
$PY exp/clef_hier.py run --bench v2 --name clef-hier-v7 --model clef --api $CLEF --concurrency 12 > exp/logs/clef-hier-v7.log 2>&1 &
$PY exp/clef_hier.py run --bench v2 --name flash-hier-v7 --model clef-flash --api $FLASH --concurrency 12 > exp/logs/flash-hier-v7.log 2>&1 &
wait
$PY exp/clef_hier.py run --bench v3 --name clef-hier-v8 --model clef --api $CLEF --concurrency 12 > exp/logs/clef-hier-v8.log 2>&1 &
$PY exp/clef_hier.py run --bench v3 --name flash-hier-v8 --model clef-flash --api $FLASH --concurrency 12 > exp/logs/flash-hier-v8.log 2>&1 &
wait
log "phase 3 done"
