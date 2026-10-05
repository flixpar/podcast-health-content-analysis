#!/bin/bash
# Server-config throughput chain (GLM, v8 high b24k, 20-minute fixed horizon each).
cd /scratch/fparker9/podcasts/pha-v8-exp
while pgrep -f "tp-glm-C-nospec" >/dev/null; do sleep 10; done
try() {  # tag spec extra
  local tag=$1 spec=$2 extra=$3
  TAG=$tag SPEC="$spec" EXTRA="$extra --async-scheduling" exp/serve-glm.sh
  if ! exp/wait-server.sh exp/logs/glm-server-$tag.log; then
    echo "$tag: async failed, retrying without" ; TAG=$tag SPEC="$spec" EXTRA="$extra" exp/serve-glm.sh
    exp/wait-server.sh exp/logs/glm-server-$tag.log || { echo "$tag FAILED"; return 1; }
  fi
  exp/tprun.sh glm-$tag 20
}
CK="--enable-mamba-shared-prefix-checkpoint --api-server-count 4"
try B2-mtp2 '{"method":"mtp","num_speculative_tokens":2}' "$CK"
try D-mtp1 '{"method":"mtp","num_speculative_tokens":1}' "$CK"
echo CHAIN1_DONE
