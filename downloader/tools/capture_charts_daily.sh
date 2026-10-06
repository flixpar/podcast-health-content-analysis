#!/usr/bin/env bash
# Capture today's live charts (Apple Marketing Tools top 100, Spotify top 200)
# and add newly charting Apple podcasts to the catalog. Meant for cron, once a
# day: a missed day cannot be recovered. Extra arguments go to capture-charts
# (e.g. --sources spotify_api, --no-catalog).
#
# Exits nonzero if any source failed; the sources that worked are still
# recorded. Output goes to logs/capture-charts.log (the pipeline also logs to
# logs/pipeline.log). Example crontab line (not installed by this script):
#   20 14 * * * /path/to/downloader/tools/capture_charts_daily.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PY=../.venv/bin/python
mkdir -p logs
LOG=logs/capture-charts.log

echo "=== capture-charts start $(date -u +%FT%TZ) ===" >>"$LOG"
status=0
"$PY" -m podcast_pipeline capture-charts "$@" >>"$LOG" 2>&1 || status=$?
echo "=== capture-charts end $(date -u +%FT%TZ) exit=$status ===" >>"$LOG"
if [ "$status" -ne 0 ]; then
    echo "capture-charts failed (exit $status); see $(pwd)/$LOG" >&2
fi
exit "$status"
