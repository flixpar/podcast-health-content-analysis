#!/bin/bash
# GLM quality variants (v8 headline) on the chosen server config; then score.
cd /scratch/fparker9/podcasts/pha-v8-exp
while ! grep -q CHAIN2_DONE exp/logs/chain2.log 2>/dev/null; do sleep 10; done
TAG=Q SEQS=${SEQS:-256} SPEC="${SPEC:-{\"method\":\"mtp\",\"num_speculative_tokens\":2}}" EXTRA="${EXTRA:---enable-mamba-shared-prefix-checkpoint --api-server-count 4 --async-scheduling}" exp/serve-glm.sh
exp/wait-server.sh exp/logs/glm-server-Q.log || exit 1
mkdir -p exp/tmp
for m in incremental submit lookup; do
  .venv/bin/python exp/toollabel.py --bench v3 --mode $m --name smoke-$m --out-dir exp/tmp/smoke-$m --strata health_dense --limit 3 > exp/logs/smoke-$m.log 2>&1 &
done
.venv/bin/python exp/xlabel.py --bench v3 --name smoke-nothink --out-dir exp/tmp/smoke-nothink --model glm53-w4 --strata health_dense --limit 3 --effort low --prefill-nothink > exp/logs/smoke-nothink.log 2>&1 &
wait
echo SMOKE_DONE
while [ ! -f exp/tmp/GO ]; do sleep 10; done
for g in ${GROUPS:-effort effort2 ablate tools}; do
  exp/phase6.sh $g
  for r in benchmark/v3/runs/v8g-*; do
    [ -f $r/score.json ] || BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark score --alias exp/alias-v8-to-v7.json $r > /dev/null 2>&1 || echo "score failed $r"
  done
  echo "GROUP $g scored"
done
echo CHAIN3_DONE
