# Historical podcast chart archive: what is recoverable, and what it supports

**Collected 2026-09-03/04.** 14,193 archived chart captures from the Wayback
Machine and Common Crawl, parsed into **1,375,824 ranked rows** spanning
**2008-12-23 to 2026-08-31**. Everything lives under `data/chart-archive/`;
the harvesters and parsers are in `analysis/chart_archive/`.

The question this answers: *can we reconstruct historical top-podcast lists well
enough to define a study population, and which series should define it?*

Short answer: **the Apple US top 100 is recoverable, near-continuously, from
mid-2012 to the present** — through three different third parties, none of them
Apple. Spotify is recoverable daily for 2024 and patchily otherwise. The two
platforms rank differently enough that the choice of platform decides the
sample.

---

## 1. What was downloaded

| Archive | Source | Captures | Rows | Range | Max depth |
|---|---|---:|---:|---|---:|
| Wayback | `podcasts.apple.com/us/charts` | 6,131 | 361,782 | 2024-08-19 → 2026-08-31 | 24 |
| Wayback | **Podbay** (`podbay.fm/browse/*`) | 2,833 | 473,814 | 2012-07-15 → 2019-08-27 | 100+ |
| Wayback | Chartable Apple charts | 1,118 | 107,214 | 2018-11-30 → 2024-12-09 | 500 |
| Wayback | Chartable Spotify charts | 1,376 | 64,146 | 2019-04-09 → 2024-12-05 | 200 |
| Wayback | Chartable reach/trending charts | 847 | 132,844 | 2020-05-11 → 2024-11-30 | 200 |
| Wayback | Spotify chart API | 1,128 | 178,631 | 2021-05-01 → 2026-08-06 | 200 |
| Wayback | Legacy iTunes RSS (both hosts) | 222 | 10,676 | 2008-12-23 → 2025-12-14 | 300 |
| Common Crawl | Chartable Apple charts | 478 | 39,377 | 2018-11-21 → 2024-11-08 | 500 |
| Common Crawl | `podcasts.apple.com/us/charts` | 60 | 7,340 | 2024-09-18 → 2026-07-13 | 24 |

## 2. Podbay closes the pre-2019 gap

`podbay.fm` was an Apple Podcasts front-end that mirrored the US iTunes charts
from 2012 until it was rebuilt in 2019. Its `/browse/top` and `/browse/<genre>`
pages are plain server-rendered HTML carrying **rank, show title, publisher and
the Apple adamId** — better identifiers than Chartable, which used its own
slugs.

- **361 snapshot days, every one of them a complete top 100**, 2012-07-15 →
  2019-08-27.
- **72 of 86 months covered (84%)**, median gap **4 days** — better than
  monthly for 2015-2018 (47, 88, 84 and 80 days respectively).
- Genre charts too, and deep ones: news-and-politics 188 days / 59 months,
  health 117 days / 62 months, science-and-medicine 124 days / 60 months.
- 2,506 distinct Apple ids in the overall chart alone.

Two other candidates hold up less well. The legacy `ax.itunes.apple.com` RSS
host adds 117 captures reaching back to **2008-12-23** — the earliest chart data
anywhere in this collection — but it is scattered across storefronts, genres and
limits, so it is a curiosity rather than a series. Everything else probed
(`player.fm`, `itunescharts.net`, `podcastchart.com`, `toppodcast.com`,
`podtail`, `podsearch`, `castbox`, `stitcher`, `blubrry`, `podchaser`,
`podtrac`, Triton, and Apple's own `apple.com/itunes/charts` and
`MZStoreServices` endpoints) has either no pre-2019 captures at all or a large
capture count that turns out to be per-podcast profile pages, not chart lists —
`podcastchart.com` looks like a 148,000-capture goldmine and is in fact 148,000
user profiles.

## 3. The decision table

A *usable top-100 day* means ≥95 of ranks 1-100 are present for that date.

| Series | Snapshot days | Range | Months covered | Depth | Usable top-100 days | Median gap |
|---|---:|---|---:|---:|---:|---:|
| **Apple via Podbay** | 361 | 2012-07 → 2019-08 | 72 of 86 (84%) | 100 | **361** | 4 d |
| Apple via Chartable | 140 | 2018-11 → 2024-12 | 56 of 74 (76%) | 100 (to 500) | **124** | 7 d |
| Apple's own charts page | 464 | 2024-08 → 2026-08 | 25 of 25 (100%) | **24 only** | 0 | 1 d |
| Apple legacy RSS | 96 | 2008-12 → 2025-11 | 63 of 204 (31%) | 10-300 | 18 | 24 d |
| Spotify chart API | 277 | 2021-05 → 2026-08 | 38 of 64 (59%) | 200 | **277** | 1 d |
| Spotify via Chartable | 90 | 2019-04 → 2024-12 | 43 of 69 (62%) | 50 | 2 | 9 d |
| Chartable reach charts | 18 | 2020-09 → 2024-09 | 17 of 49 (35%) | 200 | 18 | 66 d |

Snapshot days per year:

| Series | '08-'11 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Apple via Podbay | 0 | 6 | 23 | 8 | 47 | 88 | 84 | 80 | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Apple via Chartable | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 12 | 25 | 13 | 48 | 17 | 23 | 0 | 0 |
| Apple charts page (24 deep) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 59 | 183 | 222 |
| Apple legacy RSS | 41 | 17 | 15 | 4 | 3 | 6 | 2 | 0 | 0 | 1 | 0 | 1 | 0 | 1 | 5 | 0 |
| Spotify chart API | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 7 | 20 | 230 | 10 | 4 |
| Spotify via Chartable | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 10 | 15 | 31 | 10 | 19 | 0 | 0 |

The three Apple sources tile the whole period with only one thin patch —
2014 and 2019-2021, where Podbay is fading and Chartable has not yet ramped up.

## 4. Do the sources agree?

Same-day (±1 day) comparisons, matching shows across sources by normalised
title. Spearman is computed over the shows *both* charts hold that day.

| Comparison | Depth | Days matched | Median overlap | Median Spearman |
|---|---:|---:|---:|---:|
| Apple via Chartable vs Apple's own page | 24 | 10 | 85.4% | 0.911 |
| Apple via Podbay vs Apple via Chartable | 100 | 2 | 97.0% | 0.896 |
| Apple via Podbay vs Apple legacy RSS | 100 | 5 | 30.0% | 0.893 |
| Spotify API vs Spotify via Chartable | 50 | 21 | 92.0% | 0.983 |
| **Apple vs Spotify** | 50 | 18 | **44.0%** | **0.246** |

Chartable against Apple's own page, day by day, is 83-100% overlap with ρ
between 0.86 and 1.00 on seven of ten days, with three outliers: 2024-10-07
(33%, ρ=0.10) and the two days before Chartable shut down (42% and 46%).
Excluding that final week the median is 87.5% overlap at ρ=0.926. So
**Chartable tracks Apple closely but individual captures can be stale** — worth
a sanity check on any single date a claim rests on.

The Podbay/Chartable comparison has only two overlapping days (their windows
barely touch) but agrees on 97% of the top 100 at ρ=0.90, which is the evidence
that the two halves of the Apple record are the same measurement. The low
overlap against the legacy RSS feed is an artefact: the RSS captures on those
days are `limit=10` feeds, so only ten shows can possibly match — the ρ of 0.89
on those ten is the meaningful number.

Apple and Spotify remain **not interchangeable**: fewer than half the top 50 in
common, and the shared shows ranked close to independently.

## 5. How much does a chart move? (Is monthly resolution enough?)

Measured on every pair of snapshots within each series, bucketed by the gap
between them. `retain` is the share of shows in that rank band still in the top
100 (top 24 for Apple's page) after the gap.

| Series | Gap | Jaccard | Median rank move | Retain top-10 | Retain 11-50 | Retain 51-100 |
|---|---|---:|---:|---:|---:|---:|
| Spotify API | 1 day | 0.93 | 2 | 1.00 | 1.00 | 0.93 |
| | ~1 week | 0.71 | 7 | 1.00 | 0.95 | 0.69 |
| | ~2 weeks | 0.59 | 9 | 1.00 | 0.88 | 0.58 |
| | **~1 month** | **0.52** | **11** | **0.91** | **0.83** | **0.52** |
| | 2-3 months | 0.44 | 13 | 0.82 | 0.76 | 0.46 |
| Apple via Podbay | 1 day | 0.80 | 4 | 1.00 | 1.00 | 0.78 |
| | ~1 week | 0.63 | 8 | 1.00 | 0.93 | 0.60 |
| | **~1 month** | **0.48** | **10** | **0.90** | **0.80** | **0.48** |
| | 2-3 months | 0.42 | 11 | 0.90 | 0.74 | 0.42 |
| Apple via Chartable | 1 day | 0.89 | 4 | 1.00 | 1.00 | 0.88 |
| | ~1 week | 0.63 | 10 | 1.00 | 0.93 | 0.60 |
| | **~1 month** | **0.45** | **12** | **0.90** | **0.75** | **0.48** |
| | 2-3 months | 0.39 | 13 | 0.70 | 0.65 | 0.44 |
| Apple charts page (24 deep) | 1 day | 0.78 | 1 | 1.00 | 0.79 | — |
| | ~1 month | 0.50 | 3 | 0.90 | 0.53 | — |

Three independent series, three different eras (2012-19, 2018-24, 2021-26), two
platforms — and the curves agree to within a few points at every gap. That
consistency is itself the strongest result here: turnover in a podcast top 100
is a stable structural property, not an artefact of one source.

What it means for sampling:

- **The top 10 is effectively fixed.** Retention is 1.00 out to two weeks and
  0.90 at a month. Monthly sampling loses nothing at the head.
- **Ranks 11-50 are stable enough.** 0.75-0.83 retention over a month; a
  monthly sample sees three-quarters of them.
- **Ranks 51-100 are half noise.** About **half** the shows sitting in 51-100
  today are outside the top 100 a month later, in every series.
- **A single snapshot sees 54-63% of the month's chart.** In months with four
  or more snapshots, the union of the top 100 across the month is **159-184
  distinct shows** for 100 slots, and the median single snapshot covers 54%
  (Podbay), 61% (Spotify) or 63% (Chartable) of that union.

So: **monthly resolution is sufficient for a top-50-defined population and
insufficient for a top-100-defined one.** If the study population is "the shows
that charted", monthly snapshots undercount the real membership by roughly
40%, and almost all of the shortfall is in the bottom half of the chart.

## 6. The study population

### The rule

> A podcast is in scope if its **estimated time in the chart is at least 90
> days**, on at least **3 observations**, between 2012-07-15 and 2026-08-31 —
> counting rank ≤50 where the mirrors publish 100 places, and rank ≤24 from
> 2024-08 where only Apple's own page survives.

Three design choices, each forced by something the archive turned out to be.

**Identity is the Apple id, resolved before counting.** 76 of these shows
charted under more than one title (The Dave Ramsey Show → The Ramsey Show;
Radiolab under three). A title key counts those as separate shows sharing one
feed, so every title is mapped to an `adamId` first and observations are pooled
across a show's titles before any threshold applies.

**Exposure is weighted, because sampling density varies sevenfold.** Counting
snapshot days measures tenure × sampling rate, not tenure:

| Year | Trusted days | One snapshot every | Days of real tenure for 10 hits |
|---|---:|---:|---:|
| 2012 | 6 | 61 d | more than a year |
| 2014 | 8 | 46 d | more than a year |
| 2016 | 88 | 4.1 d | ~41 days |
| 2018 | 80 | 4.6 d | ~46 days |
| 2021 | 13 | 28 d | ~281 days |
| 2024 | 20 | 18 d | ~182 days |

So each snapshot instead carries a weight equal to the calendar time closer to
it than to any neighbouring snapshot; the 941 weights sum exactly to the
5,160-day span. A show's weighted sum estimates the days it actually spent in
the chart, and the threshold is set on that.

**The window runs to 2026, at mixed depth.** Stopping when Chartable died in
December 2024 discarded two years of Apple's own chart and excluded every show
that rose after it. Apple's page publishes 24 places, so from 2024-08 a show has
to reach the top 24 to be seen at all — which understates recent tenure relative
to the 100-deep era. `deep_obs` and `shallow_obs` in `population.csv` record
which era each show's evidence comes from, and a uniform top-24 scoring of the
whole period is written alongside as a sensitivity check.

### What it produces

**342 shows**, 315 (92%) carrying an Apple id. Median estimated tenure 239 days
over 26 observations. The threshold curve, under each depth policy:

| min est. days | mixed (recommended) | top-24 throughout | top-10 throughout |
|---:|---:|---:|---:|
| 30 | 621 | 340 | 148 |
| 60 | 437 | 220 | 103 |
| **90** | **342** | 163 | 72 |
| 120 | 271 | 129 | 54 |
| 180 | 196 | 96 | 41 |
| 365 | 121 | 62 | 26 |

Composition: 249 distinct publishers (NPR 24, audiochuck 9, Gimlet 7, then a
long tail), 93 still charting in 2025-2026, 77 last charted before 2018, 10
qualifying purely on Apple's 24-deep era. Genre where Podbay labels it:
society-and-culture 57, news-and-politics 50, comedy 38, arts 15, business 13,
health 11. **77 are already in the corpus.**

### What changed, and why it matters

Against the previous count-based rule over the 2012-2024 window (346 shows):
**258 unchanged, 88 dropped, 84 added.**

The drops are overwhelmingly from the densely sampled years — 68 of 88 last
charted between 2016 and 2018 — and they are shows the old rule admitted on thin
evidence: *Worldly* (10 snapshots, 14 estimated days), *What Trump Can Teach Us
About Con Law* (18 days), *Part-Time Genius* (19 days).

The additions are the shows the old rule structurally could not see: those that
charted during sparse windows (*Prosecuting Donald Trump*, 3 snapshots but 183
estimated days; *The Rise and Fall of Mars Hill*, 162; *America's Test Kitchen
Radio*, 184) and those that rose after Chartable died (**Good Hang with Amy
Poehler** 500 days, **The Tucker Carlson Show** 338, **Candace** 275, **The
MeidasTouch Podcast** 240, **The Weekly Show with Jon Stewart** 230, *The
Telepathy Tapes* 148).

That last group is the substantive gain. A population defined the old way
omitted most of the current US podcast landscape, and disproportionately the
political shows a misinformation study exists to examine.

## 6a. How much of the population can actually be collected

Every one of the 342 was resolved to an RSS feed and tested: does the feed still
exist, do its episodes reach back over the show's charting window, and does the
audio fetch? Per-show results in `population/recoverability.csv`, method in
`analysis/chart_archive/recoverability.py`.

| Verdict | Shows |
|---|---:|
| `fully_recoverable` — live feed spanning the window, audio fetches | 226 |
| `recent_only` — live feed, oldest episode postdates the window | 74 |
| `archive_only` — feed gone, Wayback captures and old enclosures resolve | 4 |
| `transcript_only` — publisher transcripts cover the era, audio does not | 1 |
| `not_recoverable` | 37 |

**231 of 342 (68%) are usable for their charting era.** Requiring the feed to
reach back only as far as the study window rather than to the show's first
charting date: 74% from 2018 (197 of 265), 77% from 2020, 82% from 2022, 86%
from 2024. It plateaus in the mid-eighties rather than converging.

By era of last charting:

| Era | Full | Recent only | Archive | Transcript | Not rec. | Total |
|---|---:|---:|---:|---:|---:|---:|
| pre-2018 | 28 | 33 | 0 | 0 | 16 | 77 |
| 2018-2021 | 63 | 14 | 1 | 0 | 12 | 90 |
| 2022-2024 | 63 | 9 | 1 | 1 | 8 | 82 |
| 2025-2026 | 72 | 18 | 2 | 0 | 1 | 93 |

Four findings behind those numbers:

- **Rolling-window feeds, not decay, are the binding constraint.** Of the 68
  failures at 2018+, 33 are live feeds whose oldest episode postdates the window
  and 21 have no live feed. Shows publishing daily or more fail at **38%**,
  against 12-18% at every lower frequency, because a fixed episode cap becomes a
  short time window: Up First carries 500 episodes reaching back only to
  2025-05, NPR Politics 1,750 back to 2020-03, The Daily 59 back to 2021-10,
  This American Life 15.
- **Pre-2018 is where it breaks.** Median window coverage for shows last
  charting before 2018 is **0.00** — over half have feeds that do not reach
  their charting window at all.
- **Long chart tenure predicts worse recoverability.** Only 41 of the 76
  multi-title shows (54%) are fully recoverable, against 185 of 266 single-title
  shows (70%). The shows that charted longest have had their feeds pruned
  hardest.
- **The Wayback fallback mostly fails, structurally.** Wayback archived each
  feed at the URL it uses *today*, while a 2014 show served it from a Feedburner
  or Podtrac address Apple has since replaced. Old *enclosures* survive well —
  35 feeds yielded a working charting-era file — so the bottleneck is finding the
  historical feed URL, not the audio.

Extending the window to 2026 paid off: of the 93 shows last charting in
2025-2026, 72 are fully recoverable and one is unrecoverable, and nine of the
ten that qualify solely on Apple's 24-deep era are usable. The overall usable
fraction stayed at 68% only because the 88 shows the exposure weighting removed
were disproportionately well-preserved ones — the two effects cancel.

Six shows expose no feed by any route: three Spotify-owned (StartUp, Homecoming,
The Clearing — RSS withdrawn after acquisition) and three still publishing in
2026 (CounterClock, Dark History, Losing 100 Pounds), where only Apple's failure
to expose a feed is established. Five more are video-only feeds whose enclosures
fetch fine but which `rss.py` will drop for lacking an `audio/*` enclosure.

The spot-check was calibrated against the 77 population members already in the
corpus: 74 have audio on disk and it called 73 of those fetchable, the single
miss being a CDN that rejects ranged requests.

## 7. Genre charts

The pre-2019 genre picture is transformed by Podbay, which archived every
iTunes genre chart alongside the overall one:

| Series | Genre | Days | Months | Range | Median depth |
|---|---|---:|---:|---|---:|
| Apple via Podbay | news-and-politics | 188 | 59 | 2012-07 → 2019-07 | 74 |
| Apple via Podbay | society-and-culture | 166 | 63 | 2012-07 → 2019-07 | 90 |
| Apple via Podbay | science-and-medicine | 124 | 60 | 2012-07 → 2019-07 | 81 |
| Apple via Podbay | health | 117 | 62 | 2012-07 → 2019-08 | 95 |
| Apple charts page | News | 190 | 25 | 2024-08 → 2026-08 | 24 |
| Apple charts page | Health & Fitness | 187 | 24 | 2024-08 → 2026-08 | 24 |
| Apple via Chartable | news-commentary | 44 | 9 | 2020-08 → 2024-09 | 50 |
| Apple via Chartable | politics | 36 | 27 | 2020-05 → 2024-12 | 50 |
| Apple via Chartable | health-fitness | 10 | 10 | 2019-09 → 2024-09 | 50 |
| Apple via Chartable | alternative-health | 9 | 9 | 2019-08 → 2024-09 | 50 |

Health at ~95 deep across 62 months of 2012-2019, and News & Politics at ~74
deep across 59 months, are strong enough for trend work. The weak window is
**2019-2024**, where only Chartable covers genres and only ~10 snapshots exist
for health.

## 8. Common Crawl and truncated captures

Common Crawl stops fetching at 1 MB, which cut 53 of 60 Apple chart pages
mid-JSON. The shelves we want sit early in the document, so a brace-counting
walk over the unterminated JSON recovers them intact: the parser now falls back
to that whenever the `serialized-server-data` script has no closing tag.
**All 60 CC Apple captures parse, up from 48, a 38% gain in rows.**

The honest caveat is that this buys coverage of 2024-09 onward, which Wayback
already covers at 464 days — it is not a fix for anything that was missing. The
same salvage does matter for Wayback, where a handful of captures are truncated
too, and it removes a silent failure mode from the parser.

The Common Crawl crawl walk is still **incomplete**: `index.commoncrawl.org`
began refusing connections partway through, so only two of seven URL patterns
were enumerated; `analysis/chart_archive/run_cc_index.sh` retries in the
background.

## 9. What is still missing

- **Apple's own top 100 is archived nowhere.** The `podcasts.apple.com` page
  server-renders 24 items per shelf; "see all" is an `amp-api` call needing a
  bearer token. Every route to Apple's full 100 runs through a third party —
  Podbay, then Chartable, then nothing.
- **2019-2021 is the thinnest stretch of the Apple record**: Podbay stops in
  August 2019, Chartable is only just ramping, and 2019 has 25 + 12 days
  between them.
- **Spotify before 2021 does not exist** — its chart site launched in 2021.
- **Nobody archived the iTunes RSS feed systematically.** 222 captures over
  seventeen years, most of them one-off genre or `limit=10` requests.

## 10. Caveats

- **Capture date ≈ chart date.** Nothing on these pages states which day's
  chart it is; the Wayback timestamp is the only date. Both Podbay and
  Chartable refreshed daily, so this is accurate to within a day.
- **All three Apple sources are third-party mirrors** and can go stale — see
  the 2024-10-07 Chartable outlier in §4. Podbay's stability is inferred from
  its internal turnover curve matching Chartable's and Spotify's, not from a
  large direct overlap; only two days overlap.
- **Chartable paginated at 50 rows before ~2020 and 100 after**, Podbay at 100
  (300 in 2013). The `full_top100` flag marks which days are complete.
- **Cross-source matching is by normalised title**, since the sources share no
  id space. Podbay and Apple's page carry adamIds; Chartable does not.
- **Rank is array position** for the Spotify API and Apple page sources, and an
  explicit rank number for Podbay and Chartable.
- **Turnover figures use one capture per day**, the deepest, rather than
  merging same-day captures.
- `lxml` was added to `pyproject.toml`. `uv sync` now resolves pandas to 3.x;
  the venv is pinned back to the 2.3.1 the other analysis scripts assume.

## 11. Recommendations

**1. Define the population by estimated chart tenure, not snapshot count:
≥90 estimated days on ≥3 observations, 2012-2026, mixed depth.** That is 342
shows, 92% carrying an Apple id. Counting raw snapshots confounds tenure with
the archive's sampling rate, which varies sevenfold across the period. The depth cut matters more than the
threshold: ranks 51-100 turn over about 50% per month, so at this archive's
cadence a top-100 population is substantially a sample of chart noise, while
top-50 retains 75-83% month over month.

**2. Treat the threshold as a dial, not a law.** §6 has the full curve; 60
estimated days gives 437 shows, 180 days gives 196.

**2a. Plan around 231 collectable shows, not 342.** A third of the population
cannot be obtained for its charting era (§6a), and the loss is concentrated in
daily news shows. Decide early whether `recent_only` shows belong in the study
as forward-looking subjects or should be dropped.

**3. Use Podbay for the historical backbone.** It carries Apple ids, covers
2012-2019 at a 4-day median gap, and includes genre charts deep enough for the
health and news questions. Chartable takes over 2019-2024; Apple's own page
2024 onward, at depth 24.

**4. Treat 2024-08 as a regime boundary** (depth 100 → 24), and 2019-2021 as
the thin patch.

**5. Start capturing the live endpoints daily — and note that Apple's own top
100 is still being published.** `rss.marketingtools.apple.com/api/v2/us/podcasts/top/100/podcasts.json`
returns the full ranked top 100 with Apple ids, no auth, robots-permitted; the
legacy `itunes.apple.com/us/rss/toppodcasts/limit=200/json` goes to 200 and is
the only source of deep genre charts, but is disallowed by that host's
robots.txt. All three Apple sources were cross-checked within the same minute
and agree exactly (100/100 against each other, 24/24 against the charts page).
So the 24-deep regime is an artefact of what was *archived*, not of what Apple
publishes: nobody captured the feed that was live the whole time. Capture it
daily, alongside `podcastcharts.byspotify.com/api/charts/top-podcasts?region=us`
and the charts page for genre and episode charts. Scouting report:
[`docs/chart-2024-sources.md`](chart-2024-sources.md).

**6. Backfill `podcast_charts` from the parsed table.** Podbay rows can be
inserted directly on their Apple id; Chartable rows need an iTunes Search
lookup on the slug.

---

### Files

| Path | Contents |
|---|---|
| `data/chart-archive/index/*.cdx`, `probe.json` | Wayback capture listings; candidate-source sweep |
| `data/chart-archive/raw/<source>/<url-slug>/<ts>.<ext>.gz` | Wayback captures |
| `data/chart-archive/raw_cc/…` | Common Crawl captures |
| `data/chart-archive/manifest/*.jsonl` | One row per fetch, with result and served timestamp |
| `data/chart-archive/parsed/chart_rows*.parquet` | 1,375,824 ranked rows, one per (capture, rank) |
| `data/chart-archive/parsed/summary/within_month_*.csv` | Turnover by gap; per-month union and coverage |
| `data/chart-archive/parsed/summary/*.csv`, `findings.json` | Coverage, cadence, gaps, genre, agreement |
