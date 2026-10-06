# Handoff: building the historical chart population into the pipeline

**For the agent picking this up.** You do not need to read the research
conversation. The archive is already collected, parsed and analysed; what
follows is the rule it produced, the files it produced, and how to land both in
`downloader/`. Background and the evidence behind each choice:
[`docs/chart-archive-findings.md`](chart-archive-findings.md).

**Population and recovery refreshed 2026-09-29; recovery is provisional where
Wayback probes remain pending.**

**Archive-policy caveat (PR review fixes).** The counts and generated files
described here predate retaining repeated capture timestamps, coherent daily
capture/page selection, and Marketing Tools JSON parsing. Regenerate them in
the order documented in `analysis/chart_archive/README.md` before backfilling
or validating population membership against these historical counts.

There are two separable jobs: **backfill** (load 2012-2026 chart history into
the database and select the study population) and **capture** (a daily job so
the series keeps growing). Do them in that order; they share nothing but the
schema.

---

## 1. The inclusion rule

> A podcast is in the study population if its **estimated time in the US Apple
> Podcasts overall chart is at least 90 days**, on at least **3 observations**,
> between 2012-07-15 and 2026-08-31 — counting rank **≤50** where the archived
> mirrors publish 100 places, and rank **≤24** from 2024-08 where only Apple's
> own page survives.

Unpacked:

- **Source series, in three eras.** Podbay (2012-07 → 2019-08, 361 days, 100
  deep), Chartable (2018-11 → 2024-12, 121 days, 100 deep), and Apple's own
  charts page (2024-08 → 2026-08, 459 days, 24 deep). 941 snapshot days in all.
  No adequate archived first-party top-100 series was found for the deep era
  or after 2024. The September 4 endpoint probes did find live top-100 feeds
  (§6); the 24-deep limit describes this archive, not Apple's live publication.
- **Trusted snapshot day.** A date on which one series was captured — with at
  least 95 of ranks 1-100 present for the 100-deep mirrors, or the full 24 for
  Apple's page — minus five Chartable dates whose content disagrees with Apple's
  own chart that day (2024-10-07, 2024-12-06 through 2024-12-09). Where two
  series cover the same date, the deeper one is used and the other ignored, so
  no day is double-counted.
- **Exposure weighting, not snapshot counting.** The archive's sampling rate
  varies sevenfold — one snapshot every 4 days in 2016, every 61 days in 2012 —
  so a raw count measures tenure × sampling rate. Each snapshot instead carries
  a weight equal to the calendar time closer to it than to any neighbouring
  snapshot (a midpoint or Voronoi partition of the timeline). The weights sum
  exactly to the 5,160-day span, and a show's weighted sum estimates the days it
  spent in the chart. **Keep the weights fractional**: flooring each of the ~940
  gaps to whole days loses about 3% of total exposure and moves the population
  by a dozen shows.
- **Mixed depth.** ≤50 in the Podbay and Chartable eras, ≤24 in the Apple-page
  era. This understates recent tenure relative to the deep era — a show ranked
  30 in 2025 is invisible — so `deep_obs` and `shallow_obs` record where each
  show's evidence came from, and `scores_top24_uniform.csv` scores the whole
  period at 24 as a sensitivity check.
- **Entity resolution.** Podbay and Apple's page carry Apple `adamId`s;
  Chartable carries only its own slugs. Titles are matched across mirrors by
  normalisation (lowercase, strip everything except `[a-z0-9]`), then **every
  title can use a genuine Apple podcast id as fallback, while a direct id on
  the observation takes precedence**. Only Podbay, Apple chart pages, and
  iTunes RSS podcast rows supply IDs; numeric Chartable slugs and episode or
  channel IDs are excluded. 74 shows charted under more than one title; keying on
  title alone splits them into separate "shows" that share one feed. Pool
  observations across a show's titles **before** applying the threshold.

```python
# analysis/chart_archive/population.py is the reference implementation
days    = trusted_days()                       # 941 rows: date, series, depth cut
weights = midpoint_weights(days["date"])       # fractional days, sums to the span
obs     = chart_observations(df, days)         # rank <= that day's cut
# entity = the Apple id where any source knows one, else "title:<key>".
# Resolving identity BEFORE scoring is what keeps renamed shows as one show.
obs = resolve_entities(df, obs)  # direct IDs first, then title-based fallback
per_day = obs.groupby(["entity", "date"])["rank"].min().reset_index()
per_day["w"] = per_day["date"].map(weights)
g = per_day.groupby("entity").agg(est_days=("w", "sum"), n_obs=("date", "nunique"))
population = g[(g.est_days >= 90) & (g.n_obs >= 3)].index      # 340 shows
```

Re-run with `python analysis/chart_archive/population.py`; `DEEP_CUT`,
`SHALLOW_CUT`, `MIN_DAYS` and `MIN_OBS` are module constants at the top.

## 2. What the rule produces

**340 podcasts**, of which **312 (92%) carry a genuine Apple podcast ID**
from the archive itself.

| Metric | Value |
|---|---:|
| Population | 340 |
| With an Apple podcast ID | 312 |
| Charted under more than one title | 74 |
| Distinct publishers | 249 |
| Median estimated days in the chart | 241.5 |
| Median observations | 26.5 |
| Qualifying solely on the 24-deep era | 10 |
| Never seen in the 24-deep era | 239 |
| Still charting in 2025-2026 | 93 |
| Last charted before 2018 | 76 |
| Matching the pipeline corpus by Apple ID | 76 |

The original September 4 run selected 342 shows. The change to 340 comes from
correcting identity evidence, including the numeric Chartable slug `1619` and
Apple episode IDs. The inclusion threshold and exposure weights are unchanged.
Before planning collection for the remaining 264 shows, read §4.

## 3. Moving the dial

`population/threshold_curve.csv` — shows qualifying at each threshold, under
each depth policy:

| min estimated days | mixed (recommended) | top-24 throughout | top-10 throughout |
|---:|---:|---:|---:|
| 30 | 621 | 340 | 148 |
| 60 | 437 | 219 | 103 |
| **90** | **340** | 163 | 72 |
| 120 | 269 | 129 | 54 |
| 180 | 196 | 96 | 41 |
| 365 | 121 | 62 | 26 |

The `top-24 throughout` column is the sensitivity check: it scores the whole
2012-2026 period at the depth Apple's page allows, so nothing depends on the
depth changing mid-series. If a finding survives only under `mixed`, say so.

If you loosen the threshold, re-run the recoverability audit — the shows a
looser rule adds are short-tenure ones whose feeds have not been tested.

## 4. How much of it can actually be collected

**Refreshed 2026-09-29 against the corrected population.** Lookup misses,
newly resolved feeds, and audio samples were refreshed. Successful older
measurements remain cached, so this is not a new measurement of every feed.
The CSV contains 340 shows; 35 still have no resolved feed URL.
Full method and per-show evidence are in
`data/chart-archive/parsed/population/recoverability.csv` and
`recoverability.md`; run `analysis/chart_archive/recoverability.py` to update them.

| Verdict | Shows | Evidence |
|---|---:|---|
| `fully_recoverable` | 226 | live feed, working sampled audio, ≥80% window coverage and not hollow |
| `recent_only` | 72 | live feed and working audio, but insufficient charting-window coverage |
| `archive_only` | 5 | archived feed captures span the window and a sampled era enclosure resolves |
| `transcript_only` | 1 | publisher transcript entries reach the era; sampled audio does not resolve |
| `not_recoverable` | 36 | no qualifying recovery evidence in the current cache |

**232 of 340 (68%) have evidence supporting use for their charting era.**
64 current-policy Wayback probes are complete; 50 fallback candidates
still need a current probe (35 first need a feed URL, and
15 have known feed URLs but no current capture-discovery result).
Wayback CDX requests timed out during the refresh;
known archived snapshots were replayed using saved capture metadata.
These counts are provisional. Pending or failed requests do not establish
that a show is unrecoverable, and a sampled enclosure does not prove that
every episode in the era can be collected.

| era (`last_year`) | fully recoverable | recent only | archive only | transcript only | no qualifying evidence | total |
|---|---:|---:|---:|---:|---:|---:|
| pre-2018 | 28 | 32 | 0 | 0 | 16 | 76 |
| 2018-2021 | 62 | 14 | 1 | 0 | 12 | 89 |
| 2022-2024 | 63 | 10 | 1 | 1 | 7 | 82 |
| 2025-2026 | 73 | 16 | 3 | 0 | 1 | 93 |

Collection priorities:

- Fixed episode caps and feeds frozen mid-run can leave parts of the
  charting window uncovered. Check `coverage_gap`, `months_covered`,
  `hollow_feed`, and pagination before treating a live feed as sufficient.
- 5 feeds use video enclosures; 5 have working sampled bytes.
  The audit handles them separately, but the downloader RSS parser still
  requires an audio enclosure. Decide how to collect these shows explicitly.
- Historical feed URLs remain a useful recovery route: the current feed
  URL may have replaced the one used during the charting era.
- Inspect pending measurements before excluding a show from the study.

## 5. Inputs

| File | Contents |
|---|---|
| `data/chart-archive/parsed/population/population.csv` | The 340 shows: `entity` (identity key — the Apple id, or `title:<key>`), `name` (modal title), `titles`, `key`, `publisher`, `n_obs`, `est_days`, `deep_obs`, `shallow_obs`, `best_rank`, `median_rank`, `first_seen`, `last_seen`, `span_days`, `first_year`, `last_year`, `apple_id`, `podbay_genre` |
| `…/population/all_scores.csv` | Every show that ever appeared, scored — the ones below the line included |
| `…/population/threshold_curve.csv` | Population size at each threshold under each depth policy |
| `…/population/scores_top24_uniform.csv` | The sensitivity variant: whole period scored at depth 24 |
| `…/population/recoverability.csv` | Per-show feed resolution, window coverage, audio spot-check, Wayback fallback and `verdict` |
| `…/parsed/chart_rows*.parquet` | All ranked rows, one per (capture, rank) — the raw material for backfill |
| `…/summary/flagship_daily_snapshots.csv` | Per-day depth and the `full_top100` flag |

Column semantics worth stating: **`entity` is the identity key, not `key`.**
`key` is a normalised title and 74 shows have more than one; do not persist it
as a join key. **`apple_id` is authoritative when present** and is the right
upsert key. `est_days` is an estimate of calendar time in the chart, not a count
of anything observed directly — it is only as good as the snapshot spacing
around each show's run, so treat it as an ordering, not a measurement.

## 6. Landing it in `downloader/`

### Schema

`podcast_charts` is keyed `(podcast_id, chart)` — one row per podcast per chart
— so it cannot hold 941 daily snapshots without 941 chart names. Add a history
table instead and leave the existing one meaning what it means today:

```sql
CREATE TABLE podcast_chart_history (
    podcast_id   INTEGER NOT NULL,
    source       TEXT NOT NULL,   -- 'podbay' | 'chartable' | 'apple' | 'spotify'
    chart        TEXT NOT NULL,   -- 'us_top' | 'us_genre_health' | ...
    captured_on  DATE NOT NULL,   -- the capture date; chart date to within a day
    rank         INTEGER NOT NULL,
    PRIMARY KEY (podcast_id, source, chart, captured_on),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);
CREATE INDEX idx_chart_history_date ON podcast_chart_history(captured_on);
CREATE INDEX idx_chart_history_chart ON podcast_chart_history(source, chart);
```

Then give every population member one `podcast_charts` row with chart
`apple_us_top_2012_2026` and `rank` = its best rank, so existing subset-selection
queries keep working unchanged.

### Backfill

1. Read `population.csv`. For the 312 rows with an `apple_id`, upsert a podcast
   with source id `apple_<adamId>` — `upsert_podcast` already keys on the source
   id and falls back to the Apple id, so re-running is safe and will merge with
   the 76 already present rather than duplicating them.
2. Resolve feeds with the existing `fetch-podcasts` path (iTunes lookup by id →
   `feedUrl`). Expect failures in the pre-2018 tail; record them on the row and
   continue, per the repo's per-item failure convention.
3. For the 28 without an Apple id (§8), resolve by hand or with one iTunes
   Search call each — do not build a general search fallback for these rows.
4. Insert `podcast_chart_history` from `chart_rows*.parquet`, filtered to the
   trusted days. Do this for the overall chart first, then the genre charts if
   wanted; the genre rows are the same shape.
5. Insert the `apple_us_top_2012_2026` rows into `podcast_charts`.

### Capture

The archive will not backfill and both historical mirrors are dead — Podbay's
chart pages are gone and Chartable shut down in December 2024. From here the
series only grows if we capture it. **The September 4 probes found live Apple chart feeds
serving the full depth the population rule was built on**, which
means the 24-deep regime ends the day capture starts:

| Endpoint | Depth | Auth | robots | Notes |
|---|---:|---|---|---|
| `https://rss.marketingtools.apple.com/api/v2/us/podcasts/top/100/podcasts.json` | **100** | none | permits | Carries Apple `adamId` directly. **Use this one.** |
| `https://itunes.apple.com/us/rss/toppodcasts/limit=200/json` | **200** | none | `Disallow: /*/rss/*` | Deeper, and the only source of deep *genre* charts (`genre=1489` → 200 rows), but disallowed by robots — a deliberate choice, not a default |
| `https://podcastcharts.byspotify.com/api/charts/top-podcasts?region=us` | 200 | none | permits | Spotify, for the cross-platform check |
| `https://podcasts.apple.com/us/charts` (+ `?genre=`) | 24 | none | permits | Keep capturing: it is the only source of the per-genre top 24 and of episode charts |

The three Apple sources were cross-validated on 2026-09-04 within the same
minute and agree exactly — charts page vs legacy RSS 24/24, charts page vs
marketing tools 24/24, marketing tools vs legacy RSS 100/100. They are one
chart, published three ways.

Marketing Tools maxes out at 100 (150 and 200 return HTTP 500) and its
per-genre path 404s; the legacy RSS feed hard-caps at 200 (201+ returns
`400 Invalid value for param 'limit'`). Full scouting report, including what
does not work and why, in [`docs/chart-2024-sources.md`](chart-2024-sources.md).

Run daily, write into `podcast_chart_history` with `captured_on = today`, and
**store the raw response alongside** — parsing can be redone, a missed day
cannot. Note for whoever maintains the population rule afterwards: once daily
capture starts, the record gains a *third* depth regime (100 again), so
`SHALLOW_CUT` applies only to the 2024-08 → capture-start window.

## 7. Sharp edges

- **Cross-mirror matching is by title.** 74 current members changed title while charting;
  a title-keyed join splits those into two entities, and two shows with the same
  normalised title would merge into one. `apple_id` is the fix wherever it
  exists — prefer it and fall back to title only for Chartable-era rows.
- **Chartable slugs are not stable ids.** They look like ids and are not.
- **Capture date ≈ chart date**, ±1 day. Nothing on these pages states which
  day's chart they show.
- **`full_top100` ≠ trusted.** The five excluded Chartable dates are complete
  and wrong. If you re-derive the day list yourself, carry the exclusion.
- **Depth changes at 2024-08.** After Chartable dies, the only Apple source is
  Apple's own page at depth 24. A longitudinal claim crossing that date has to
  survive the change.
- **2019-2021 is the thin patch** of the Apple record — Podbay stops in August
  2019, Chartable is only ramping up.
- **Use the locked environment.** lxml, pandas 3.0.5, and pyarrow are
  available there; population and turnover generation passed with pandas 3.0.5.
- **Errors are retryable.** Failed lookup/search/feed requests retry, and
  Wayback probes retry when their policy or window changes or a fetch fails.
- **Report completeness is computed from the cache.** Report dates are
  generation dates, and pending probes must be reviewed before exclusion.

## 8. Shows without an Apple id

28 of the 340 current members have no genuine Apple podcast ID in the
archive. Resolve them by title and publisher before upserting; do not
treat a numeric Chartable slug as an Apple ID. Full list: `population.csv`
where `apple_id` is null. The largest by estimated tenure are:

| Show | Publisher | Est. days | Obs |
|---|---|---:|---:|
| We Can Do Hard Things with Glennon Doyle | Glennon Doyle & Cadence13 | 821.5 | 67 |
| The Problem With Jon Stewart | Apple TV+ | 298.5 | 11 |
| Murdaugh Murders Podcast | Mandy Matney | 293.5 | 15 |
| Supernatural with Ashley Flowers | Parcast Network | 267.0 | 11 |
| Murder, Mystery & Makeup | Audioboom Studios | 243.5 | 16 |
| Joe Rogan Experience Review podcast | Adam Thorne | 207.5 | 11 |
| The Thing About Pam | NBC News | 202.5 | 10 |
| Prosecuting Donald Trump | MSNBC | 183.5 | 3 |
| The Piketon Massacre | iHeartRadio | 138.5 | 11 |

## 9. Shows with no resolved RSS feed

35 current members have no resolved feed URL. 6 have a cached
individual verification record covering US/GB/CA lookups, archived
lookup responses, and the pipeline database where available.
These are unresolved by the routes tried; ownership or catalogue
listing alone does not prove structural uncollectability.

| Show with cached verification | Verdict |
|---|---|
| CounterClock | `not_recoverable` |
| StartUp Podcast | `not_recoverable` |
| Homecoming | `not_recoverable` |
| Dark History | `not_recoverable` |
| Losing 100 Pounds with Phit-n-Phat: Real diet talk from someone who defeated a lifetime of obesity and now teaches you. | `not_recoverable` |
| The Clearing | `not_recoverable` |

Check the pipeline database before concluding that a missing Apple
`feedUrl` makes a show unreachable. See the per-show lookup, feed, and
Wayback columns for missing measurements and retry state.

## 10. Verification

After backfill:

```sql
-- 340 population members, 76 matching existing Apple IDs
SELECT COUNT(*) FROM podcast_charts WHERE chart = 'apple_us_top_2012_2026';

-- the overall-chart history: 941 trusted days (361+121 at 100 deep, 459 at 24)
SELECT COUNT(*), COUNT(DISTINCT captured_on)
FROM podcast_chart_history WHERE source IN ('podbay','chartable','apple') AND chart = 'us_top';
-- expect ~59,000 rows across 941 dates

-- reproduce the rule from the database alone
SELECT COUNT(*) FROM (
  SELECT podcast_id FROM podcast_chart_history
  WHERE chart = 'us_top' AND rank <= 50
  GROUP BY podcast_id HAVING COUNT(DISTINCT captured_on) >= 10);
-- NB this reproduces the *old* count-based rule, not the current one: the
-- exposure weighting cannot be expressed in SQL without the snapshot weights.
-- Load population.csv and check the row count is 340 instead.
```

If the population table holds fewer than 340 shows, the gap is entity resolution, not the
rule — check how many `population.csv` rows failed to upsert.
