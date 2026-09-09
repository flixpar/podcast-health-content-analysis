# Chart archive harvester

Reconstructs historical top-podcast charts from the Wayback Machine and Common
Crawl. Findings and recommendations: `docs/chart-archive-findings.md`.

## Pipeline

```bash
python analysis/chart_archive/cdx_index.py        # Wayback capture listings -> index/*.cdx
./analysis/chart_archive/run_wayback.sh           # download captures  -> raw/
python analysis/chart_archive/parse.py            # -> parsed/chart_rows.parquet

./analysis/chart_archive/run_cc_index.sh          # Common Crawl walk -> cc_index/
python analysis/chart_archive/cc_fetch.py         # WARC ranges       -> raw_cc/
python analysis/chart_archive/parse.py --cc       # -> parsed/chart_rows_cc.parquet

python analysis/chart_archive/analyze.py          # -> parsed/summary/*.csv, findings.json
```

Everything writes under `data/chart-archive/` and every stage is resumable:
downloads skip files already on disk, and the Common Crawl walk caches one
JSONL per (pattern, crawl).

Pass a target name to `fetch_wayback.py` or `parse.py` to work on one source.

## Notes for whoever runs this next

- The CDX API drops **parallel** requests silently — an empty body, not an
  error, which reads as "this URL was never archived". `cdx_index.py` is
  deliberately sequential with backoff. Capture *fetches* (`/web/...id_/`)
  tolerate ~10 workers.
- Fetch the URL exactly as captured, tracking params and all. Requesting a
  cleaned-up URL makes Wayback redirect to the nearest capture of that URL and
  file it under the wrong date; `served_ts` in the manifests records what was
  actually served.
- Chartable changed layout (div grid → table) around 2020 and paginated at
  50/page before, 100 after. Apple rewrapped its embedded JSON in 2025 and
  moved the genre name into the shelf title. `parse.py` handles all four.
- Requires `lxml` (XML parsing), added to `pyproject.toml`. Note that
  `uv sync` now resolves pandas to 3.x; the venv is deliberately held at
  2.3.1, which is what the other analysis scripts were written against.
