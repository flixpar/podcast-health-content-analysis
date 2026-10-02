# Studies: one shared catalog, many selections

The pipeline used to have one implicit population: whatever podcasts the chart
fetches had put in the database. Studies separate *what we know about* from
*what an analysis is about*:

```
 sources ──► catalog ◄── shared work ──► studies ──► analyses
 (charts,     podcasts, episodes,         named,        read a pinned
  archive,    audio, transcripts,         versioned     manifest
  searches,   provenance                  selections
  Wayback)
```

* **Catalog** (shared, append-only): `podcasts`, `episodes`, audio files,
  transcripts. Each artifact exists once. A study never owns audio or
  transcripts; it points at catalog episodes, so work done for one study is
  already done for every other study containing that episode.
* **Provenance**: every podcast and episode records how it got there.
  `podcast_sources` (live chart fetch, live capture, chart archive, study
  resolution), `podcast_feeds` (every feed URL ever known for a show, with what
  its last read saw), `episode_sources` (live feed, archived feed copy,
  archived audio), and `entity_links` (identity decisions: which podcast a bare
  chart title is, with the evidence).
* **Chart history**: `chart_snapshots` / `chart_entries` hold the reconstructed
  2012-2026 archive and the daily live captures in one shape.
* **Studies**: defined in code, materialized into tables, and used as a filter
  by every work stage.

## Defining a study

A study is a Python class in `downloader/podcast_pipeline/studies/`
(see `base.py`), registered in `studies/__init__.py`. Its `select(conn)`
returns members:

| Entity | Meaning | Resolved by |
|---|---|---|
| `podcast:<id>` | a catalog podcast | already resolved |
| `apple:<id>` | an Apple podcast id, e.g. from a chart | `resolve` (iTunes lookup) |
| `title:<key>` | a chart title with no id (Chartable era) | `resolve` (paced iTunes search) |

Each member either takes every episode (`windows=None`) or only those
published inside its windows (e.g. the months a show charted). Study-level
knobs: `max_per_window` (cap per window, preferring already-transcribed
episodes, then spreading evenly in time) and `dedupe` (drop re-issued copies
of an episode under a new GUID, keeping the copy with the most work done).

Why code rather than a config file? Selection rules worth studying are not
declarative: the monthly top-24 needs a time-weighted ranking over a snapshot
timeline. A class is the smallest thing that holds such a rule, its
parameters and its documentation together. Bump `version` when the logic
changes; the stored `definition_hash` records which rule produced a
membership.

## Materializing

`python -m podcast_pipeline study refresh [NAME...]` runs the definition and
writes:

* `study_members`: one row per entity, with `podcast_id` once resolved
  (unresolved members stay listed, visibly);
* `study_windows`: each member's publication-date windows, with their evidence
  (rank, points, snapshot coverage) in `attrs`;
* `study_episodes`: the selected episodes, each with its window and a
  **priority**: the episode's position within its window. Downloads go in
  priority order, so all windows get their first episode before any gets its
  second, and an interrupted run or a full disk leaves coverage spread evenly
  rather than front-loaded;
* `studies` / `study_revisions`: the revision is bumped whenever the episode
  set or the definition changes, and each `study_episodes` row keeps the
  revision that added it.

Refreshing takes seconds. Run it after anything that changes what a study can
see: new chart data, `resolve`, `discover`, `discover-archived`.

## Working a study

```bash
cd downloader
P="../.venv/bin/python -m podcast_pipeline"
$P study refresh apple-top24-monthly
$P study status apple-top24-monthly            # read-only; prints suggested next steps
$P resolve --study apple-top24-monthly          # entities -> podcasts with feeds
$P discover --study apple-top24-monthly         # live feeds -> episodes
$P study refresh apple-top24-monthly
$P discover-archived --study apple-top24-monthly  # Wayback copies of old feeds -> older episodes
$P study refresh apple-top24-monthly
$P fetch-rss-transcripts --study apple-top24-monthly
$P download --study apple-top24-monthly --wayback-fallback
$P export-audio-batch /mnt/transfer --study apple-top24-monthly   # remote ASR round trip
$P study export apple-top24-monthly --link-transcripts ../analysis/work/top24-transcripts
```

Scope rules for stages:

| Stage | Default scope | Narrow / widen |
|---|---|---|
| `discover`, `download` | episodes/podcasts of **any** study | `--study NAME` / `--all` |
| `fetch-rss-transcripts`, `transcribe`, `export-audio-batch` | everything eligible | `--study NAME` |
| `discover-archived`, `resolve` | one study (required) | — |

`discover` and `download` default to the union of studies because they
grow the catalog and spend disk: the catalog can hold every podcast that
ever charted, but only what some study asks for gets fetched.

`study status` reports members (resolved, with feed, feed errors), episodes by
state (transcribed via RSS or ASR, awaiting ASR, awaiting download, failed),
hours, a disk projection measured from this archive's own MB/hour,
window coverage (windows with episodes, with transcripts, imputed from
neighbouring snapshots, gaps live feeds do not reach), provenance mix, overlap
with other studies, and the commands to run next. It is read-only and safe
during a download.

## Analyses

`study export NAME` writes `data/studies/<name>/rev<N>/episodes.csv` (one row
per episode: ids, window, state, transcript path) and `study.json` (the
definition, members and windows with their evidence). Analyses should read the
manifest, not the live tables, and record the revision they used.

`--link-transcripts DIR` fills a directory with symlinks named
`episode_<id>.jsonl.zst`, which is the layout
`analysis/topic_labeling.py --transcripts` already reads. **Follow-up:**
topic labeling's run identity hashes the whole prepared windows file, so a new
study relabels windows another study already labeled. Labels should be cached
per window, keyed by the transcript hash and the windowing, prompt and model
settings, so a study becomes a view over cached labels. That change belongs on
`main`, where the labeling code has moved on.

## Defined studies

### `corpus-2025`

The collection as it stood on 2026-10-02: every podcast from the four live
charts fetched since 2025-10-13 (Apple US top 100 ×2, Apple US Health &
Fitness top 50, Spotify US top 100), with every episode their feeds list. This
is what the existing 131k transcripts, the lexical scan and the labeling
pilots ran on. Podcast membership is frozen (first recorded before
2026-10-03), while episodes keep flowing in from `discover`. 975 re-issued
duplicates are excluded (corpus issue C2).

### `apple-top24-monthly`

Apple US overall chart, top 24 per calendar month from 2016-01, with each
show's episodes from the months it was in the list. The reasoning is in
`studies/apple_top24_monthly.py`. In short:

* **Depth 24 throughout.** That is all Apple's own page shows, and the only
  record between Chartable's shutdown and the start of live capture. A
  uniform depth keeps 2016 and 2026 comparable.
* **Exactly 24 per month, ranked by time-weighted points.** Snapshot density
  ranges from one a month (Chartable, 2019-2023) to daily (2025-26). A union
  of everything seen in the top 24 would give ~24 shows in sparse months and
  ~45 in dense ones. Each snapshot stands for the calendar time nearest to it
  (the midpoint partition the population analysis validated), clipped to the
  month. A show earns days × (25 − rank) per snapshot, and the top 24 scorers
  form the month's list.
* **Gap months are imputed.** Months with no snapshot (16 since 2016) take
  their list from the neighbouring snapshots and are flagged
  (`snapshots_in_month = 0`).
* **Sources.** Apple's chart page and the live Marketing Tools feed come first,
  then Podbay, then Chartable. Known-bad Chartable days are excluded. The
  legacy iTunes RSS chart is excluded because it is a different list.
* **Identity.** Shows are matched by Apple id, then by title through ids seen
  elsewhere in the record, then through `entity_links`, so renamed shows pool.

The list grows by itself as `capture-charts` adds days; refresh the study.

## Chart data

* `import-chart-archive` loads `data/chart-archive/parsed/chart_rows*.parquet`
  (every source, chart and genre, ~1.4M rows) into `chart_snapshots` /
  `chart_entries`. It can be re-run: it replaces archive rows and never
  touches live ones.
* `capture-charts` should run **daily** (`downloader/tools/capture_charts_daily.sh`
  is cron-ready). It stores the raw response, records the snapshot, and adds
  newly charting Apple shows to the catalog. The archive cannot backfill: a day
  not captured is lost.

## Older episodes

Live feeds drop old items, which leaves most pre-2019 charting windows
empty. `discover-archived --study` looks up Wayback Machine copies of each
member's feed URLs, current and historical. It picks captures that list the
missing windows, parses them, and adds the episodes with `wayback_feed`
provenance. Many of their enclosure URLs are dead, so
`download --wayback-fallback` retries a dead enclosure through Wayback's copy
of the audio and records `wayback_audio` provenance on success. The CDX API is
queried strictly sequentially, because parallel requests are silently dropped
and look like "never archived".

## Invariants

* Nothing in the catalog is deleted or rewritten by a study. Refresh rewrites
  only the study's own membership rows.
* Per-episode state stays on `episodes` and `transcripts`. Status is derived,
  never copied into study tables, so it cannot drift.
* `discover`, `discover-archived`, `resolve`, `study refresh` and
  `capture-charts` all write. Queue them between `download` runs, not during
  one. `study status` and `study list` are read-only.
