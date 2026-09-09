#!/usr/bin/env bash
# discover -> publisher transcripts -> download, for the feeds recovered after
# the main expansion (and anything published since the last discover).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=../.venv/bin/python

echo "=== discover === $(date)"
$PY -m podcast_pipeline discover

echo "=== fetch-rss-transcripts === $(date)"
$PY -m podcast_pipeline fetch-rss-transcripts

echo "=== download === $(date)"
$PY -m podcast_pipeline download

echo "=== done === $(date)"
