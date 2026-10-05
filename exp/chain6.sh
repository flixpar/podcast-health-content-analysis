#!/bin/bash
# GLM quality variants (v8 headline) on the chosen server config; then score.
cd /scratch/fparker9/podcasts/pha-v8-exp
while ! grep -q CHAIN4_DONE exp/logs/chain4.log 2>/dev/null; do sleep 10; done
TAG=Q SEQS=${SEQS:-256} SPEC="${SPEC:?set SPEC}" EXTRA="${EXTRA:---enable-mamba-shared-prefix-checkpoint --api-server-count 4 --async-scheduling --trust-request-chat-template}" exp/serve-glm.sh
exp/wait-server.sh exp/logs/glm-server-Q.log || exit 1
for g in ${VARIANT_GROUPS:-effort effort2 ablate tools}; do
  exp/phase6.sh $g
  for r in benchmark/v3/runs/v8g-*; do
    [ -f $r/score.json ] || BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark score --alias exp/alias-v8-to-v7.json $r > /dev/null 2>&1 || echo "score failed $r"
  done
  echo "GROUP $g scored"
done
echo CHAIN6_DONE
