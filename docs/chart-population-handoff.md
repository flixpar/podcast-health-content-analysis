# Handoff: building the historical chart population into the pipeline

**For the agent picking this up.** You do not need to read the research
conversation. The archive is already collected, parsed and analysed; what
follows is the rule it produced, the files it produced, and how to land both in
`downloader/`. Background and the evidence behind each choice:
[`docs/chart-archive-findings.md`](chart-archive-findings.md).

There are two separable jobs: **backfill** (load 2012-2024 chart history into
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
  Apple never published its own top 100 anywhere an archive could reach, so
  there is no first-party alternative for the deep era and no deep source at all
  after 2024.
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
  title is mapped to an Apple id where any id-bearing source knows one, and the
  id is the identity**. 76 shows charted under more than one title; keying on
  title alone splits them into separate "shows" that share one feed. Pool
  observations across a show's titles **before** applying the threshold.

```python
# analysis/chart_archive/population.py is the reference implementation
days    = trusted_days()                       # 941 rows: date, series, depth cut
weights = midpoint_weights(days["date"])       # fractional days, sums to the span
obs     = chart_observations(df, days)         # rank <= that day's cut
# entity = the Apple id where any source knows one, else "title:<key>".
# Resolving identity BEFORE scoring is what keeps renamed shows as one show.
obs["entity"] = obs["key"].map(key_to_apple_id).fillna("title:" + obs["key"])
per_day = obs.groupby(["entity", "date"])["rank"].min().reset_index()
per_day["w"] = per_day["date"].map(weights)
g = per_day.groupby("entity").agg(est_days=("w", "sum"), n_obs=("date", "nunique"))
population = g[(g.est_days >= 90) & (g.n_obs >= 3)].index      # 342 shows
```

Re-run with `python analysis/chart_archive/population.py`; `DEEP_CUT`,
`SHALLOW_CUT`, `MIN_DAYS` and `MIN_OBS` are module constants at the top.

## 2. What the rule produces

**342 podcasts**, of which **315 (92%) already carry an Apple id** from the
archive itself.

| | |
|---|---:|
| Population | 342 |
| With an Apple `adamId` | 315 |
| Charted under more than one title | 76 |
| Distinct publishers | 249 |
| Median estimated days in the chart | 239 |
| Median observations | 26 |
| Qualifying only on the 24-deep era (2024-08+) | 10 |
| Never seen in the 24-deep era | 241 |
| Still charting in 2025-2026 | 93 |
| Last charted before 2018 | 77 |
| Already in the current 226-podcast corpus | 77 |

Genre, where Podbay's genre charts label it: society-and-culture 57,
news-and-politics 50, comedy 38, arts 15, business 13, health 11,
science-and-medicine 10. Publisher concentration is low — NPR 24 shows,
audiochuck 9, Gimlet 7, then a long tail.

Against the earlier count-based rule over a 2012-2024 window (346 shows): 258
unchanged, 88 dropped, 84 added. The drops are concentrated in 2016-2018, the
densely sampled years the old rule over-weighted; the additions are shows that
charted in sparse windows or rose after Chartable died — Good Hang with Amy
Poehler, The Tucker Carlson Show, Candace, The MeidasTouch Podcast, The Weekly
Show with Jon Stewart.

**77 of 342 are already collected.** Before planning the other 265, read §4:
not all of them can be obtained.

## 3. Moving the dial

`population/threshold_curve.csv` — shows qualifying at each threshold, under
each depth policy:

| min estimated days | mixed (recommended) | top-24 throughout | top-10 throughout |
|---:|---:|---:|---:|
| 30 | 621 | 340 | 148 |
| 60 | 437 | 220 | 103 |
| **90** | **342** | 163 | 72 |
| 120 | 271 | 129 | 54 |
| 180 | 196 | 96 | 41 |
| 365 | 121 | 62 | 26 |

The `top-24 throughout` column is the sensitivity check: it scores the whole
2012-2026 period at the depth Apple's page allows, so nothing depends on the
depth changing mid-series. If a finding survives only under `mixed`, say so.

If you loosen the threshold, re-run the recoverability audit — the shows a
looser rule adds are short-tenure ones whose feeds have not been tested.

## 4. How much of it can actually be collected

A separate audit resolved every one of the 342 to a feed and tested whether the
feed reaches back over the show's charting window. Full method and per-show
results: `population/recoverability.csv` (342 rows), the 88 shows dropped by the
rule change frozen in `recoverability_dropped.csv`, and
`population/recoverability.md`; the script is
`analysis/chart_archive/recoverability.py`, which is resumable and re-runs from
cache without refetching.

| Verdict | Shows | Meaning |
|---|---:|---|
| `fully_recoverable` | 226 | live feed spanning the charting window, audio fetches |
| `recent_only` | 74 | live feed, but its oldest episode postdates the window |
| `archive_only` | 4 | feed gone; Wayback captures and old enclosures resolve |
| `transcript_only` | 1 | publisher transcripts cover the era, audio does not fetch |
| `not_recoverable` | 37 | none of the above |

**231 of 342 (68%) are usable for their charting era.** Restricting the study
window raises it but does not fix it: 74% from 2018, 77% from 2020, 82% from
2022, 86% from 2024.

Five things the implementer needs to act on:

- **Rolling-window feeds are the dominant failure, worst for daily shows.**
  Shows publishing daily or more fail at 38%, against 12-18% at lower
  frequencies, because a fixed episode cap converts to a short time window: Up
  First carries 500 episodes reaching back only to 2025-05, NPR Politics 1,750
  back to 2020-03, The Daily 59 back to 2021-10, This American Life 15.
  Several serve older pages behind a `?page=` or `before=` parameter; a
  paginated fetch is the obvious first thing to try.
- **Pre-2018 has median window coverage of 0.00.** Over half of those 77 shows
  have feeds that do not reach their charting window at all.
- **Long chart tenure predicts worse recoverability** — 54% of multi-title
  shows are fully recoverable against 70% of single-title ones.
- **Five shows are video-only feeds** (`video_sourced` in the CSV): TEDTalks
  (video) and (hd), MSNBC Rachel Maddow (video), Sesame Street Podcast, Know
  How... (HD). Their enclosures fetch fine and the pipeline transcodes to Opus
  anyway, but **`downloader/podcast_pipeline/rss.py` requires an `audio/*`
  enclosure and will drop every episode in them**. Either widen that check or
  exclude these five deliberately.
- **Wayback is a weak fallback, and the reason points at the fix.** Wayback
  archived each feed at the URL it uses today, while a 2014 show served it from
  a Feedburner or Podtrac address Apple has since replaced. Old *enclosures*
  survive well — 35 feeds yielded a working charting-era file — so recovering
  historical *feed URLs* is the highest-value unexplored route for the 37
  unrecoverable shows.

## 5. Inputs

| File | Contents |
|---|---|
| `data/chart-archive/parsed/population/population.csv` | The 342 shows: `entity` (identity key — the Apple id, or `title:<key>`), `name` (modal title), `titles`, `key`, `publisher`, `n_obs`, `est_days`, `deep_obs`, `shallow_obs`, `best_rank`, `median_rank`, `first_seen`, `last_seen`, `span_days`, `first_year`, `last_year`, `apple_id`, `podbay_genre` |
| `…/population/all_scores.csv` | Every show that ever appeared, scored — the ones below the line included |
| `…/population/threshold_curve.csv` | Population size at each threshold under each depth policy |
| `…/population/scores_top24_uniform.csv` | The sensitivity variant: whole period scored at depth 24 |
| `…/population/recoverability.csv` | Per-show feed resolution, window coverage, audio spot-check, Wayback fallback and `verdict` |
| `…/parsed/chart_rows*.parquet` | All ranked rows, one per (capture, rank) — the raw material for backfill |
| `…/summary/flagship_daily_snapshots.csv` | Per-day depth and the `full_top100` flag |

Column semantics worth stating: **`entity` is the identity key, not `key`.**
`key` is a normalised title and 76 shows have more than one; do not persist it
as a join key. **`apple_id` is authoritative when present** and is the right
upsert key. `est_days` is an estimate of calendar time in the chart, not a count
of anything observed directly — it is only as good as the snapshot spacing
around each show's run, so treat it as an ordering, not a measurement.

## 6. Landing it in `downloader/`

### Schema

`podcast_charts` is keyed `(podcast_id, chart)` — one row per podcast per chart
— so it cannot hold 482 daily snapshots without 482 chart names. Add a history
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

1. Read `population.csv`. For the 333 rows with an `apple_id`, upsert a podcast
   with source id `apple_<adamId>` — `upsert_podcast` already keys on the source
   id and falls back to the Apple id, so re-running is safe and will merge with
   the 63 already present rather than duplicating them.
2. Resolve feeds with the existing `fetch-podcasts` path (iTunes lookup by id →
   `feedUrl`). Expect failures in the pre-2018 tail; record them on the row and
   continue, per the repo's per-item failure convention.
3. For the 13 without an Apple id (§7), resolve by hand or with one iTunes
   Search call each — do not build a general search fallback for 13 rows.
4. Insert `podcast_chart_history` from `chart_rows*.parquet`, filtered to the
   trusted days. Do this for the overall chart first, then the genre charts if
   wanted; the genre rows are the same shape.
5. Insert the `apple_us_top_2012_2026` rows into `podcast_charts`.

### Capture

The archive will not backfill and both historical mirrors are dead — Podbay's
chart pages are gone and Chartable shut down in December 2024. From here the
series only grows if we capture it. **Apple's own legacy chart feeds are still
live and still serve the full depth the population rule was built on**, which
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

- **Cross-mirror matching is by title.** 96 shows changed title while charting;
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
- **`lxml` is in `pyproject.toml`; the venv holds pandas 2.3.1 while the lock
  resolves 3.x.** Don't `uv sync` casually.

## 8. Shows without an Apple id

27 of the 342 have no `adamId` anywhere in the archive — all charted only in the
Chartable era (2019+), where the mirror recorded its own slugs rather than
Apple's ids. An iTunes Search on the title should find most of them; two were
checked individually during the recoverability audit and produced no feed by any
route (see §9). Full list with tenure in `population.csv` where `apple_id` is
null; the largest are:

| Show | Publisher | Est. days | Obs |
|---|---|---:|---:|
| We Can Do Hard Things with Glennon Doyle | Glennon Doyle & Cadence13 | 822 | 67 |
| The Problem With Jon Stewart | Apple TV+ | 299 | 11 |
| Murdaugh Murders Podcast | Mandy Matney | 294 | 15 |
| Supernatural with Ashley Flowers | Parcast Network | 267 | 11 |
| Murder, Mystery & Makeup | Audioboom Studios | 244 | 16 |
| Joe Rogan Experience Review podcast | Adam Thorne | 208 | 11 |
| The Thing About Pam | NBC News | 203 | 10 |
| Prosecuting Donald Trump | MSNBC | 184 | 3 |
| The Tucker Carlson Podcast | Tucker Carlson Network | 129 | 5 |

## 9. Shows with no RSS feed by any route

Eight shows are still listed by Apple but expose no `feedUrl`, and none produced
a feed via `country=gb`/`ca`, an archived lookup response, or our own database.
They split into two kinds needing different treatment:

- **Six are Spotify-owned and structurally uncollectable** — Gimlet (StartUp,
  Homecoming, Mogul, The Clearing) and Spotify Studios (Cults, Unsolved
  Murders). RSS was withdrawn after acquisition. Write these off.
- **Two are still publishing in 2026** — CounterClock (audiochuck) and Losing
  100 Pounds (Corinne Crabtree). A feed almost certainly exists; only Apple's
  failure to expose one is established. Worth a manual look.

A ninth, **The Ben Shapiro Show**, was initially misfiled here: Apple omits its
`feedUrl`, but the feed exists at `feeds.megaphone.fm/BVDWV5370667266` and the
show is fully recoverable. Where Apple's lookup returns no feed, check the
pipeline database before concluding the show is uncollectable.

Counting shows Apple no longer lists at all, 36 of the 342 have no feed URL
from any source; all 36 are in `not_recoverable`.

## 10. Verification

After backfill:

```sql
-- 342 population members, 77 of which existed before
SELECT COUNT(*) FROM podcast_charts WHERE chart = 'apple_us_top_2012_2026';

-- the overall-chart history: 941 trusted days (361+121 at 100 deep, 459 at 24)
SELECT COUNT(*), COUNT(DISTINCT captured_on)
FROM podcast_chart_history WHERE source IN ('podbay','chartable') AND chart = 'us_top';
-- expect ~59,000 rows across 941 dates

-- reproduce the rule from the database alone
SELECT COUNT(*) FROM (
  SELECT podcast_id FROM podcast_chart_history
  WHERE chart = 'us_top' AND rank <= 50
  GROUP BY podcast_id HAVING COUNT(DISTINCT captured_on) >= 10);
-- NB this reproduces the *old* count-based rule, not the current one: the
-- exposure weighting cannot be expressed in SQL without the snapshot weights.
-- Load population.csv and check the row count is 342 instead.
```

If the population table holds fewer than 342 shows, the gap is entity resolution, not the
rule — check how many `population.csv` rows failed to upsert.
