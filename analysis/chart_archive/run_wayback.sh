#!/usr/bin/env bash
# Fetch targets smallest-first so the cheap, high-value sources land early and
# the 6k Apple pages run last.
set -u
cd "$(dirname "$0")/../.."
for t in marketingtools applemarketingtools itunes_rss spotify_api chartable_itunes_us chartable_spotify chartable_reach apple_charts_page; do
  echo "=== $t $(date -Is)"
  .venv/bin/python analysis/chart_archive/fetch_wayback.py "$t"
done
echo "=== ALL DONE $(date -Is)"
