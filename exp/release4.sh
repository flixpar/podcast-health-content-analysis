#!/bin/bash
# Release phase 4 once the v7 Clef runs (both models) and phase 3 are done.
cd "$(dirname "$0")/.."
until grep -q "phase 3 done" exp/logs/phase3.log 2>/dev/null && [ -f benchmark/v2/runs/flash-hier-v7/run_manifest.json ] && ! pgrep -f 'clef_hier[.]py run' >/dev/null; do sleep 60; done
rm -f exp/HOLD_PHASE4; echo "[$(date +%T)] released"
