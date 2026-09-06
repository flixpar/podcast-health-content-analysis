#!/usr/bin/env bash
# Everything left, on one build of the code so each comparison varies one thing.
#
#   quotediag2 -- the same one-attempt run as quotediag, now with span repair.
#                 quotediag is the before: 7 batches isolated, 13 windows, 9 of
#                 them non_verbatim_quote, 3 windows lost outright.
#   oh-v4tax / oh-v6tax -- 84 labels against 91 on the 120 pilot windows that
#                 could only be called other_health_topic. Same prompt, same
#                 effort, same windows; the taxonomy is the only difference.
#   prod-candidate -- v6 prompt + 91 labels at high effort, the setting the
#                 sweep argues for, to price the recommendation.
set -uo pipefail
EXP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

EVAL_DIR=$EXP/eval120 bash "$EXP/run_variant.sh" quotediag2 \
  --batch-size 4 --concurrency 24 --attempts 1 \
  --reasoning-effort medium --max-output-tokens 28000 > "$EXP/runs/quotediag2.log" 2>&1
echo "== finished quotediag2 at $(date +%T)"

EVAL_DIR=$EXP/otherhealth-v4 EVAL_TAXONOMY=$EXP/eval/taxonomy.json \
  bash "$EXP/run_variant.sh" oh-v4tax \
  --batch-size 4 --concurrency 24 --attempts 2 \
  --reasoning-effort medium --max-output-tokens 28000 > "$EXP/runs/oh-v4tax.log" 2>&1
echo "== finished oh-v4tax at $(date +%T)"

EVAL_DIR=$EXP/otherhealth EVAL_TAXONOMY=$EXP/taxonomy_v6.json \
  bash "$EXP/run_variant.sh" oh-v6tax \
  --batch-size 4 --concurrency 24 --attempts 2 \
  --reasoning-effort medium --max-output-tokens 28000 > "$EXP/runs/oh-v6tax.log" 2>&1
echo "== finished oh-v6tax at $(date +%T)"

EVAL_DIR=$EXP/eval120-v6 EVAL_TAXONOMY=$EXP/taxonomy_v6.json \
  bash "$EXP/run_variant.sh" prod-candidate \
  --batch-size 4 --concurrency 24 --attempts 2 \
  --reasoning-effort high --max-output-tokens 44000 > "$EXP/runs/prod-candidate.log" 2>&1
echo "== finished prod-candidate at $(date +%T)"
