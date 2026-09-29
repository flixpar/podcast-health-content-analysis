# Chart archive harvester

Reconstructs historical top-podcast charts from the Wayback Machine and Common
Crawl. Findings and recommendations: `docs/chart-archive-findings.md`.

## Pipeline

Run from the repository root after `uv sync`; activate `.venv` so the Python
commands and shell runners use the same locked environment. The analysis needs
pandas, pyarrow (Parquet), and lxml (XML), all present in the lockfile. Population
and turnover analysis have been checked with the locked pandas 3.0.5.

```bash
source .venv/bin/activate
python analysis/chart_archive/cdx_index.py        # Wayback capture listings -> index/*.cdx
./analysis/chart_archive/run_wayback.sh           # download captures  -> raw/
python analysis/chart_archive/parse.py            # -> parsed/chart_rows.parquet

./analysis/chart_archive/run_cc_index.sh          # Common Crawl walk -> cc_index/
python analysis/chart_archive/cc_fetch.py         # WARC ranges       -> raw_cc/
python analysis/chart_archive/parse.py --cc       # -> parsed/chart_rows_cc.parquet

python analysis/chart_archive/analyze.py          # -> parsed/summary/*.csv, findings.json
python analysis/chart_archive/within_month.py     # -> parsed/summary/within_month_*
python analysis/chart_archive/population.py       # -> parsed/population/*.csv, summary.json
python analysis/chart_archive/recoverability.py   # -> population/recoverability.csv and .md
```

Everything writes under `data/chart-archive/` and every stage is resumable:
downloads skip files already on disk, and the Common Crawl walk caches one
JSONL per (pattern, crawl).

Pass a target name to `fetch_wayback.py` or `parse.py` to work on one source.

Recoverability phases can be run separately (`lookup`, `feeds`, `audio`,
`verify`, `wayback`, `report`). `report` uses cached measurements and can be
provisional. Failed lookup/search/feed requests retry on the next run. Old
missing lookup records are retried once because their caches did not distinguish
request failures from successful empty responses. Wayback probes are re-run
when their policy or charting window changes or a fetch fails. A probe can reuse
saved capture metadata for unchanged feed URLs, but it re-fetches
the snapshot and re-probes enclosures; old enclosure counts are never reused.
This permits rechecking known snapshots when CDX is unavailable. The default
Wayback budget is 30 minutes; raise it with `--wayback-budget SECONDS` or rerun
`wayback report` until the report has no pending fallback probes. Report dates
are generation dates; cached measurements may be older.

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
- Wayback indexes are cached only after validating the CDX records. HTTP errors,
  malformed responses, and ambiguous empty bodies retry; an unsuccessful index
  run exits nonzero so it cannot silently look complete.
