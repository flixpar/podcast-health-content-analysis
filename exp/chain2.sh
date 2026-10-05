#!/bin/bash
# After chain1: preemption fixes (fewer seqs) and CPU KV offloading.
cd /scratch/fparker9/podcasts/pha-v8-exp
while ! grep -q CHAIN1_DONE exp/logs/chain1.log 2>/dev/null; do sleep 10; done
SPEC_BEST=${SPEC_BEST:-'{"method":"mtp","num_speculative_tokens":2}'}
CK="--enable-mamba-shared-prefix-checkpoint --api-server-count 4 --async-scheduling"
run() { local tag=$1 seqs=$2 extra=$3
  TAG=$tag SEQS=$seqs SPEC="$SPEC_BEST" EXTRA="$CK $extra" exp/serve-glm.sh
  exp/wait-server.sh exp/logs/glm-server-$tag.log && CONC=$((seqs*2)) exp/tprun.sh glm-$tag 20; }
run E-seq96 96 ""
run F-offload 256 "--kv-offloading-size 400 --kv-offloading-backend native"
echo CHAIN2_DONE
