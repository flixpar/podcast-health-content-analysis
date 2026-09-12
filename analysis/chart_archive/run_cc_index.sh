#!/usr/bin/env bash
# index.commoncrawl.org rate-limits hard; keep retrying the crawl walk until it
# lets us back in, then hand off to cc_index.py (which caches per crawl).
set -u
cd "$(dirname "$0")/../.."
for attempt in $(seq 1 24); do
  if curl -sf --max-time 120 https://index.commoncrawl.org/collinfo.json \
       -o data/chart-archive/cc_index/collinfo.json; then
    echo "=== crawl list fetched on attempt $attempt $(date -Is)"
    .venv/bin/python analysis/chart_archive/cc_index.py && break
  fi
  echo "attempt $attempt: index.commoncrawl.org unavailable $(date -Is)"
  sleep 300
done
echo "=== CC INDEX DONE $(date -Is)"
