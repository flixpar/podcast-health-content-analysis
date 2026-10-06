#!/usr/bin/env bash
# Retry incomplete crawl walks; cc_index.py caches the crawl list and each query.
set -u
cd "$(dirname "$0")/../.."
mkdir -p data/chart-archive/cc_index || exit 1
for ((attempt = 1; attempt <= 24; attempt++)); do
  if .venv/bin/python analysis/chart_archive/cc_index.py; then
    echo "CC index complete $(date -Is)"
    exit 0
  fi
  echo "attempt $attempt: CC index incomplete $(date -Is)" >&2
  if ((attempt < 24)); then
    sleep 300
  fi
done
echo "CC index still incomplete after 24 attempts $(date -Is)" >&2
exit 1
