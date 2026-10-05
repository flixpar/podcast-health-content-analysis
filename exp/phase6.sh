#!/bin/bash
# GLM-5.3-Flash request variants on the v8 headline items (160), 4 runs at a time.
# Usage: exp/phase6.sh <group>   (groups: effort, ablate, tools, v7)
set -u
cd /scratch/fparker9/podcasts/pha-v8-exp
PY=.venv/bin/python
H="--strata health_dense mixed null ad_read discourse"
run() {  # name, args...
  local name=$1; shift
  $PY exp/xlabel.py --bench v3 --name $name --model glm53-w4 $H --concurrency 160 "$@" > exp/logs/$name.log 2>&1
}
trun() {
  local name=$1; shift
  $PY exp/toollabel.py --bench v3 --name $name --model glm53-w4 $H --concurrency 160 --priority "$@" > exp/logs/$name.log 2>&1
}
case $1 in
  effort)
    run v8g-low --effort low &
    run v8g-max --effort max &
    run v8g-b8k --budget 8000 &
    run v8g-b4k --budget 4000 &
    wait ;;
  effort2)
    run v8g-sp-eff --note-file exp/note-efficient.md &
    run v8g-nothink --effort low --prefill-nothink &
    run v8g-noclaims --drop claims &
    run v8g-nonarr --drop narrative &
    run v8g-nofep --drop frame,evidence,population &
    run v8g-topiconly --drop claims,products,narrative,frame,evidence,population &
    wait ;;
  ablate)
    ;;
  tools)
    trun v8g-tool-inc --mode incremental &
    trun v8g-tool-submit --mode submit &
    trun v8g-tool-lookup --mode lookup &
    run v8g-high-r2 &
    wait ;;
esac
echo GROUP_DONE $1
