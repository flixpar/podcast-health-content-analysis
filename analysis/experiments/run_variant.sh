#!/usr/bin/env bash
# Run one labeling variant over the eval slice and score it.
#   run_variant.sh <name> [extra topic_labeling.py label flags...]
# Every variant writes to its own run directory; nothing touches outputs/.
set -euo pipefail

EXP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO=/scratch/fparker9/podcasts/podcast-misinfo
NAME="$1"; shift
RUN="$EXP/runs/$NAME"
TAXONOMY="${EVAL_TAXONOMY:-$EXP/eval/taxonomy.json}"
SLICE="${EVAL_DIR:-$EXP/eval}"

rm -rf "$RUN"; mkdir -p "$RUN"
cd "$REPO"

START=$(date +%s.%N)
set +e
.venv/bin/python analysis/topic_labeling.py label \
  --taxonomy "$TAXONOMY" \
  --windows "$SLICE/windows.jsonl.zst" \
  --prepare-manifest "$SLICE/prepare_manifest.json" \
  --output-dir "$RUN" \
  --config "$EXP/topic-labeling-exp.toml" \
  --model deepseek-ai/DeepSeek-V4-Flash-0731 \
  "$@" > "$RUN/label.stdout" 2> "$RUN/label.stderr"
RC=$?
set -e
END=$(date +%s.%N)

python3 - "$RUN" "$START" "$END" "$RC" <<'PY'
import json, sys
run, start, end, rc = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
json.dump({"wall_seconds": round(end-start,1), "exit_code": rc}, open(f"{run}/timing.json","w"))
PY

echo "--- $NAME (exit $RC, $(python3 -c "import json;print(json.load(open('$RUN/timing.json'))['wall_seconds'])")s) ---"
tail -3 "$RUN/label.stderr" || true
.venv/bin/python "$EXP/score.py" "$RUN" "$SLICE/reference.json" "$NAME" | tee "$RUN/score.json"
