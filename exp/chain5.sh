#!/bin/bash
# After the GLM variant groups: capped GLM configs on the corpus, a GLM complete run,
# then DeepSeek throughput configs and a complete run.
cd /scratch/fparker9/podcasts/pha-v8-exp
while ! grep -q CHAIN6_DONE exp/logs/chain6.log 2>/dev/null; do sleep 10; done
CK="--enable-mamba-shared-prefix-checkpoint --api-server-count 4 --async-scheduling --trust-request-chat-template"
TAG=G2 SPEC='{"method":"mtp","num_speculative_tokens":2}' SEQS=48 EXTRA="$CK" exp/serve-glm.sh
exp/wait-server.sh exp/logs/glm-server-G2.log && CONC=192 exp/tprun.sh glm-G2-mtp2-seq48 20
TAG=G1 SPEC=none SEQS=128 EXTRA="$CK" exp/serve-glm.sh
exp/wait-server.sh exp/logs/glm-server-G1.log && {
  CONC=384 exp/tprun.sh glm-G1-nospec-seq128 20
  CONC=384 exp/fullrun.sh glm-high
  CONC=384 exp/tprun.sh glm-G1-b8k 20 --budget 8000
  CONC=384 exp/tprun.sh glm-G1-speff-b8k 20 --budget 8000 --note-file exp/note-efficient.md
  CONC=384 exp/tprun.sh glm-G1-noclaims 20 --drop claims
  CONC=384 exp/tprun.sh glm-G1-topiconly 20 --drop claims,products,narrative,frame,evidence,population
}
export MODEL_NAME=deepseek-ai/DeepSeek-V4-Flash-0731
TAG=ds1 exp/serve-ds.sh; exp/wait-server.sh exp/logs/ds-server-ds1.log && {
  exp/tprun.sh ds-high 20
  exp/tprun.sh ds-low 20 --effort low
  exp/fullrun.sh ds-high
}
TAG=ds-mtp EXTRA="--speculative-config '{\"method\":\"mtp\",\"num_speculative_tokens\":1}'" exp/serve-ds.sh
exp/wait-server.sh exp/logs/ds-server-ds-mtp.log && exp/tprun.sh ds-high-mtp1 20
echo CHAIN5_DONE
