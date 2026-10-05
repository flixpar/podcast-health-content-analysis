#!/bin/bash
# DFlash2-G drafter for GLM-5.3-Flash (TP4): KV pool and a short throughput run.
cd /scratch/fparker9/podcasts/pha-v8-exp
while ! grep -q CHAIN5_DONE exp/logs/chain5.log 2>/dev/null; do sleep 10; done
TAG=dflash MAXLEN=131071 SPEC='{"method":"dflash","model":"/tmp/huggingface2/hub/models--canada-quant--GLM-5.3-Flash-DFlash2-G/snapshots/b8ba68b022d612958d1a9c447f294f148a156ed1","num_speculative_tokens":4}' EXTRA="--enable-mamba-shared-prefix-checkpoint --api-server-count 4" exp/serve-glm.sh
if exp/wait-server.sh exp/logs/glm-server-dflash.log; then
  grep -h "GPU KV cache size" exp/logs/glm-server-dflash.log | head -1
  exp/tprun.sh glm-dflash 12 --max-tokens 40000
else
  echo DFLASH_BOOT_FAILED
fi
echo CHAIN8_DONE
