# Temporal coverage audit

`temporal_coverage.py` characterises *when* the collected corpus covers, reading
`downloader/data/podcast_metadata.db` read-only. It separates the live-capture
window from the RSS back catalogue swept at collection time, because the two
have very different sampling properties.

```bash
python analysis/temporal_coverage.py
python analysis/render_temporal_html.py
```

Outputs under `analysis/output/temporal-coverage/`:

- `fig1_volume_by_month.png`: episodes and median episode length per month.
- `fig2_panel_completeness.png`: share of shows observed in each month.
- `fig3_backcatalog_depth.png`: archive depth per show, and cumulative episode mass.
- `fig4_coverage_spans.png`: first-to-last episode window for every show.
- `fig5_transcript_coverage.png`: transcribed vs audio-only by month.
- `fig6_cadence.png`: weekly, weekday and hourly publication rhythm (timestamps are UTC).
- `fig7_show_month_heatmap.png`: per-show monthly output, scaled to each show's own peak.
- `monthly_coverage.csv`, `podcast_spans.csv`, `summary.json`, `series.json`: the tables
  behind the figures.
- `findings.md` and `coverage_memo.html`: the written memo.

`coverage_attribution.py` answers the follow-up question: *why* does coverage
thin out going back in time? It classifies each feed by whether it still carries
the show's first episode (sequential episode numbering, iTunes `episode` tags,
trailer entries, launch language) and decomposes each historical month into
shows that had not launched, shows whose feed is truncated, and shows covered.

```bash
python analysis/coverage_attribution.py
```

Additional outputs:

- `fig8_coverage_attribution.png`: per-month decomposition of why each show is absent.
- `fig9_feed_completeness_evidence.png`: what can be established about each feed.
- `feed_completeness.csv`: per-show verdict and the evidence behind it.
- `coverage_attribution.csv`, `live_window_gaps.csv`, `external_launch_checks.csv`.
- `attribution_findings.md`, `attribution_summary.json`.

Result: 97-98% of the shows absent from any given past month had simply not
launched. Only 6 of 220 feeds (3%) are demonstrably truncated. Validated against
published launch dates for 8 shows, 6 of which match (the exceptions are *This
American Life*, correctly flagged as truncated, and *The Bill Simmons Podcast*,
a 2015 rebrand of a 2007 show — a failure mode no feed-internal evidence can
detect). A separate finding: 10 shows have live-window holes caused by
short-retention feeds dropping episodes between `discover` runs.

Actionable issues and constraints found by both scripts are collected in
[`docs/corpus-issues.md`](../docs/corpus-issues.md).

Headline result: the corpus spans 2006-2026, but only the 10 months from
2025-10-13 observe the full show panel. Three quarters of all episodes were
published after June 2025. Pre-collection depth is set mostly by show age --
today's charts are dominated by recent shows -- not by feed retention, so trends
computed on raw counts track panel growth rather than publishing behaviour.

## Usage limits for paid APIs

`usage_limits.py` is a client-side spending guard for runs pointed at a paid
model API. It is off unless a run asks for it, so the local vLLM pipeline is
unaffected.

Every request is charged to three scopes -- its provider, its model, and the
experiment that claimed it -- and each scope carries limits declared in
[`usage-limits.toml`](usage-limits.toml):

| Limit | Meaning | On being hit |
| :---- | :---- | :---- |
| `max_concurrent` | in-flight requests | the request waits |
| `<meter>_per_minute` | a rate | the request waits for the next minute |
| `<meter>_per_day` | a budget for one UTC day | the run stops |
| `<meter>_total` | a lifetime allocation | the run stops |

`<meter>` is one of `requests`, `input_tokens`, `uncached_input_tokens`,
`output_tokens`, `tokens` or `cost` (US dollars, from prices declared per
model). Fireworks' three published serverless limits are
`input_tokens_per_minute`, `uncached_input_tokens_per_minute` and
`output_tokens_per_minute`.

Budgets stop rather than wait because every command that spends money
checkpoints: a stopped run resumes tomorrow, or under a raised allocation, from
where the money ran out. Limits are held in one SQLite ledger, so they hold
across threads, across concurrent runs and across days.

```bash
# Point a labeling run at a paid endpoint, under an allocation:
python analysis/topic_labeling.py label \
    --usage-limits analysis/usage-limits.toml \
    --provider fireworks --experiment topic-pilot-a
# or set the same three in the [usage] table of analysis/topic-labeling.toml.

python analysis/usage_limits.py status
python analysis/usage_limits.py report --experiment topic-pilot-a --by model
```

Authentication for such a run is `api_key_env` in the `[model]` table, which
names the environment variable holding the key rather than the key itself. It is
read from the environment, or from the git-ignored `.env` (see `.env.example`)
when the environment does not set it, and resolved before any work starts so a
missing key fails immediately. Without it no `Authorization` header is sent at
all, which is what the local vLLM endpoints want.

An undeclared provider or experiment is an error rather than an unmetered
default, so a typo cannot buy an unbudgeted run. A run with no `--experiment`
is still limited by its provider and model, and is recorded as
`(unattributed)`.
