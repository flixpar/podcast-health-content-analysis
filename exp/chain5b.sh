#!/bin/bash
# GLM (G1 server, already up): topic-only fixed horizon, complete runs of the variants; then DeepSeek.
cd /scratch/fparker9/podcasts/pha-v8-exp
curl -sf --noproxy '*' http://127.0.0.1:8222/v1/models > /dev/null || exit 1
CONC=384 exp/tprun.sh glm-G1-topiconly 20 --drop claims,products,narrative,frame,evidence,population
CONC=384 exp/fullrun.sh glm-noclaims --drop claims
CONC=384 exp/fullrun.sh glm-topiconly --drop claims,products,narrative,frame,evidence,population
CONC=384 exp/fullrun.sh glm-b8k --budget 8000
export MODEL_NAME=deepseek-ai/DeepSeek-V4-Flash-0731
TAG=ds1 exp/serve-ds.sh; exp/wait-server.sh exp/logs/ds-server-ds1.log && {
  exp/tprun.sh ds-high 20
  exp/tprun.sh ds-low 20 --effort low
  exp/fullrun.sh ds-high
}
TAG=ds-mtp EXTRA="--speculative-config '{\"method\":\"mtp\",\"num_speculative_tokens\":1}'" exp/serve-ds.sh
exp/wait-server.sh exp/logs/ds-server-ds-mtp.log && exp/tprun.sh ds-high-mtp1 20
echo CHAIN5_DONE
