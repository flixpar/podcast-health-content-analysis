# Chart archive harvester

Reconstructs historical top-podcast charts from the Wayback Machine and Common
Crawl. This is research and archive tooling; importing charts into the catalog,
daily live capture, and study collection belong to the downloader.

- [Archive findings](../../docs/chart-archive-findings.md): dated coverage,
  agreement, turnover, and exploratory population/recovery measurements.
- [Apple source investigation](../../docs/chart-2024-sources.md): dated endpoint
  probes, schema examples, and leads for deeper 2024–2026 charts.

These reports preserve the evidence behind the implementation. Their numeric
results predate the latest capture and selection policies and need regeneration.

## Pipeline

Run from the repository root after `uv sync`; activate `.venv` so the Python
commands and shell runners use the same locked environment. The analysis needs
pandas, pyarrow (Parquet), and lxml (XML), all present in the lockfile. Population
and turnover analysis have been checked with the locked pandas 3.0.5.

Run the offline regression checks with:

```bash
.venv/bin/python -m pytest analysis/tests/test_chart_archive.py -q
```

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
Targeted parses write diagnostic shards such as `chart_rows_podbay.parquet`;
analysis, population, and turnover load only `chart_rows.parquet` and
`chart_rows_cc.parquet`. Run a full parse to incorporate a refreshed source.

All capture timestamps are retained even when payloads repeat. CDX indexes
written before this policy are refreshed once, tracked by `index/*.policy.json`.
After upgrading, rerun indexing, downloads, both full parses, and then analysis,
turnover, population, and recoverability in the order above. Existing download
files are reused, but newly retained dates require additional downloads.

Daily analysis chooses the capture with the most distinct top-100 ranks, then
the greatest total depth, breaking ties toward the earliest capture. Chartable
pages are joined only within the same archive and UTC day, within one hour of
the first page, using the closest capture of each additional page. Overlapping
ranks keep the lower-numbered page's row. The same selection precedes the
population's depth cuts and drives completeness checks and turnover analysis.
The one-hour allowance estimates a coherent page set; it cannot establish that
the chart stayed unchanged between page captures.

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
Audio spot-checks retry when no cached probe returned usable bytes, and refresh
when sampled enclosure URLs change; successful unchanged probe sets are reused.

## Population rule and generated outputs

`population.py` implements the exploratory mixed-depth tenure rule: at least
90 estimated days on at least three observations, using ranks 1–50 for Podbay
and Chartable and ranks 1–24 for Apple's page. `DEEP_CUT`, `SHALLOW_CUT`,
`MIN_DAYS`, and `MIN_OBS` define those parameters.

Mirror days need at least 95 distinct ranks in the top 100; Apple-page days
need depth 24. `DISTRUSTED` excludes known stale Chartable dates. On dates
covered by multiple sources, the deeper source takes precedence. Fractional
midpoint weights estimate exposure between neighbouring selected dates.

Apple show IDs take precedence over title matches. Only podcast rows from
Podbay, Apple's page, and iTunes RSS provide direct Apple IDs; Chartable slugs,
episode IDs, and channel IDs do not. Resolve identities and pool renamed shows
before applying thresholds. `entity` is the identity key; `key` is a normalised
title and should not be used as a persistent identity.

| Output under `data/chart-archive/parsed/` | Contents |
|---|---|
| `chart_rows.parquet`, `chart_rows_cc.parquet` | Canonical ranked captures; preserve all timestamps for downstream selection |
| `flagship_us_overall.parquet` | Selected daily US overall charts |
| `summary/flagship_daily_snapshots.csv` | Daily depth and completeness before the population's stale-date exclusions |
| `summary/*.csv`, `summary/findings.json` | Coverage, cadence, agreement, and turnover measurements |
| `population/population.csv` | Qualifying entities with IDs, titles, ranks, estimated days, observation counts, and date ranges |
| `population/all_scores.csv`, `population/threshold_curve.csv` | Scores for all entities and population sizes across thresholds |
| `population/scores_top24_uniform.csv` | Uniform-depth sensitivity check |
| `population/recoverability.csv`, `population/recoverability.md` | Per-show feed, audio, historical-window, and Wayback evidence |

## Integration with downloader studies

The follow-up [studies PR #8](https://github.com/flixpar/podcast-health-content-analysis/pull/8)
adds chart history, daily capture, entity resolution, and collection by study.
Its `apple-top24-monthly` definition selects 24 shows per month at uniform
depth, rather than this exploratory 90-day mixed-depth population. Keep the
two definitions explicit when comparing counts or collecting episodes.

The importer must apply the same coherent capture/page policy as
`snapshots.select_daily()` before forming daily chart entries. It must retain
the page number (or derive it from the saved slug) for Chartable alignment;
combining all ranks from a UTC day recreates the discarded intra-day union.
Pass chart identity columns as the selector's `keys` when importing genres and
other chart types. Canonical Parquet files retain every capture so importers
can choose their daily snapshots without losing the underlying evidence.

After regenerating the archive, compare imported trusted dates with the
regenerated `summary/flagship_daily_snapshots.csv` and `population/summary.json`,
applying `DISTRUSTED` and the source/depth policy. The historical 941-day count
is a dated measurement, not a fixed invariant. Reimport and refresh studies
before using regenerated data for collection. Operational commands and schema
documentation belong with the downloader implementation.

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
- Common Crawl index runs also exit nonzero when any query exhausts retries;
  reruns reuse completed queries and retry only missing caches.
