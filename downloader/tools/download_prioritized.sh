#!/usr/bin/env bash
# Download the health chart first, then everything else. The full queue takes
# days, so the ordering is what makes the health subset usable sooner; both
# stages are ordinary resumable `download` runs.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=../.venv/bin/python

echo "=== stage 1: apple_us_genre_1512 (health) === $(date)"
$PY -m podcast_pipeline download --charts apple_us_genre_1512

echo "=== stage 2: everything else === $(date)"
$PY -m podcast_pipeline download

echo "=== done === $(date)"
