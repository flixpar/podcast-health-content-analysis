#!/bin/bash
# Queued after phase2.sh has restarted the server: keyword-hint variants.
cd "$(dirname "$0")/.."
until grep -q queued exp/logs/phase2.log 2>/dev/null; do sleep 30; done
PY=.venv/bin/python
tmux new-window -t vllm -n v7-hints "cd $PWD; $PY exp/xlabel.py --bench v2 --name v7-hints-llm --mode hints --lexicon exp/lexicon-llm-v2.json --concurrency 128 2>&1 | tee exp/logs/v7-hints-llm.log"
tmux new-window -t vllm -n v8-hints "cd $PWD; $PY exp/xlabel.py --bench v3 --name v8-hints-llm --mode hints --lexicon exp/lexicon-llm-v3.json --concurrency 128 2>&1 | tee exp/logs/v8-hints-llm.log"
echo "[$(date +%T)] hints queued"
