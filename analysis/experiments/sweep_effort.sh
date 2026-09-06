#!/usr/bin/env bash
set -uo pipefail
EXP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
run () {  # name effort max_out
  EVAL_DIR="$EXP/eval120" bash "$EXP/run_variant.sh" "$1" \
    --reasoning-effort "$2" --max-output-tokens "$3" \
    --batch-size 4 --concurrency 24 --attempts 2 \
    > "$EXP/runs/$1.log" 2>&1
  echo "== finished $1 at $(date +%H:%M:%S)"
}
run eff-none   none    8000
run eff-low    low    16000
run eff-medium medium 28000
run eff-high   high   44000
echo "SWEEP COMPLETE"
