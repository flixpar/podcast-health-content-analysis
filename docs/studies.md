# Studies: one shared catalog, many selections

Studies select an analysis population from the shared podcast catalog:

```
 sources ──► catalog ◄── shared work ──► studies ──► analyses
 (charts,     podcasts, episodes,         named,        read a pinned
  archive,    audio, transcripts,         versioned     manifest
  searches,   provenance                  selections
  Wayback)
```

* **Catalog** (shared): `podcasts`, `episodes`, audio files,
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

Set `exclude_trailers` to apply the shared trailer/promo/short-item rules.
Bump `version` when selection logic changes; the stored `definition_hash`
records which rule produced a membership.

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
* `studies` / `study_revisions`: the revision advances whenever the selected
  episode set, episode assignment, member/window state, or definition changes.
  This includes unresolved members and empty windows. Each `study_episodes`
  row keeps the revision that first added it.

Refreshing takes seconds. Run it after anything that changes what a study can
see: new chart data, `resolve`, `discover`, `discover-archived`.

## Working a study

```bash
cd downloader
pipeline() { ../.venv/bin/python -m podcast_pipeline "$@"; }
pipeline study refresh apple-top24-monthly
pipeline study status apple-top24-monthly       # prints suggested next steps
pipeline resolve --study apple-top24-monthly    # entities -> podcasts with feeds
pipeline discover --study apple-top24-monthly   # live feeds -> episodes
pipeline study refresh apple-top24-monthly
pipeline discover-archived --study apple-top24-monthly
pipeline study refresh apple-top24-monthly
pipeline fetch-rss-transcripts --study apple-top24-monthly
pipeline download --study apple-top24-monthly --wayback-fallback
pipeline export-audio-batch /path/to/transfer --study apple-top24-monthly
pipeline study export apple-top24-monthly --link-transcripts ../local/top24-transcripts
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
during a download. Pending episodes without positive durations are estimated
at the catalog's mean positive duration, or
`storage.estimated_episode_duration_seconds` when none are available.

Use `link-entity ENTITY --podcast-id ID --note EVIDENCE` to correct an identity,
or `--unresolvable` to record that no defensible match exists. Manual decisions
override automatic resolution and capture; refresh affected studies afterward.

## Analyses

`study export NAME` writes `data/studies/<name>/rev<N>/episodes.csv` (one row
per episode: ids, window, state, transcript path) and `study.json` (the
definition, members and windows with their evidence). Analyses should read the
manifest, not the live tables, and record the revision they used.

`--link-transcripts DIR` fills a directory with symlinks named
`episode_<id>.jsonl.zst`, which is the layout
`analysis/topic_labeling.py --transcripts` reads. Label computation and reuse
remain the analysis pipeline's responsibility.

## Defined studies

### `corpus-2025`

The collection as it stood on 2026-10-02: every podcast from the four live
charts fetched since 2025-10-13 (Apple US top 100 ×2, Apple US Health &
Fitness top 50, Spotify US top 100), with every episode their feeds list. This
is the original collection used by the lexical scan and labeling pilots.
Podcast membership is frozen (first recorded before 2026-10-03), while
episodes keep flowing in from `discover`; re-issued duplicates are excluded.

### `apple-top24-monthly`

Apple US overall chart, top 24 per calendar month from 2016-01, with each
show's episodes from the months it was in the list. The scoring rationale is
in `downloader/podcast_pipeline/studies/apple_top24_monthly.py`:

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
* **Gap months are imputed.** Months with no snapshot take
  their list from the neighbouring snapshots and are flagged
  (`snapshots_in_month = 0`).
* **Sources.** Apple's chart page and the live Marketing Tools feed come first,
  then Podbay, then Chartable. Known-bad Chartable days are excluded. The
  legacy iTunes RSS chart is excluded because it is a different list.
* **Identity.** Shows are matched by Apple id, then by title through ids seen
  elsewhere in the record, then through `entity_links`, so renamed shows pool.

The list grows by itself as `capture-charts` adds days; refresh the study.

## Chart data

* `import-chart-archive` loads the canonical `chart_rows.parquet` and optional
  `chart_rows_cc.parquet` under `data/chart-archive/parsed/` into
  `chart_snapshots` / `chart_entries`. It selects one coherent daily capture or
  nearby Chartable page set using the
  [archive policy](../analysis/chart_archive/README.md), preserving explicit page
  metadata or deriving it from older saved slugs.
  It replaces archive rows and leaves live rows intact. Verification compares
  trusted-day counts with a regenerated `parsed/population/summary.json` using
  the same depth policy; missing, older, malformed or incompatible summaries are reported
  as unavailable. Historical report counts are dated evidence. Regenerate,
  reimport, then refresh studies before collecting from corrected measurements.
* `capture-charts` should run **daily** (`downloader/tools/capture_charts_daily.sh`
  is cron-ready). It stores the raw response, records the snapshot, and adds
  newly charting Apple shows to the catalog, reusing known current/historical
  feed owners. A missed live day cannot be fetched retrospectively.

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

For sources outside known feeds, `downloader/tools/alternate_sources/` and
`downloader/tools/tal_archive.py` produce evidence-bearing JSONL. These tools
read the catalog without writing it; inspect their output before loading it
with `import-episodes PATH --source SOURCE --dry-run`, then the real import.
Keep caches and generated reports under ignored `local/` or the data volume.
Read-only diagnostics live under `downloader/tools/audit/`.

## Invariants

* Nothing in the catalog is deleted or rewritten by a study. Refresh rewrites
  only the study's own membership rows.
* Per-episode state stays on `episodes` and `transcripts`. Status is derived,
  never copied into study tables, so it cannot drift.
* `discover`, `discover-archived`, `resolve`, `study refresh` and
  `capture-charts` all write. Queue them between `download` runs, not during
  one. Manual linking, episode imports, and path migrations also write.
  `study status` and `study list` are read-only apart from normal startup schema
  initialization; use them against an already initialized catalog.
* Stored audio/transcript paths are relative to `Config.data_path`. Use
  `paths.to_stored` for writes and `paths.resolve` for reads. For legacy absolute
  paths, back up the catalog and inspect `migrate-paths --dry-run` before applying
  the migration; original values are retained in `path_migration_backup`.
