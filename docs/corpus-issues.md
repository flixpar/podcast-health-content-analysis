# Corpus issues and next steps

Action register from the temporal-coverage audit of `downloader/data/podcast_metadata.db`,
2026-08-30. Corpus state at time of writing: 132,541 episodes, 220 shows,
131,873 hours, publication dates 2006-05-05 to 2026-08-28.

Supporting analysis:

- `analysis/temporal_coverage.py` -> `analysis/output/temporal-coverage/findings.md`
- `analysis/coverage_attribution.py` -> `analysis/output/temporal-coverage/attribution_findings.md`
- Memo: https://claude.ai/code/artifact/c45e5d6c-c2ff-4c1f-b98f-62fd68ce2115

## Open issues

| ID | Severity | Issue | Owner area |
| --- | --- | --- | --- |
| C1 | **High** | Short-retention feeds lose episodes between `discover` runs, unrecoverably | pipeline |
| C2 | Medium | 1,944 duplicate episode rows survive the GUID uniqueness constraint | pipeline / db |
| C3 | Low | 5 episodes stored with a 1970 epoch publication date | pipeline / rss |
| C4 | Low | 6 podcasts have no RSS URL and zero episodes | pipeline |
| C5 | Low | 87 episodes stuck in `error` on dead audio URLs | pipeline |
| C6 | Low | `max_episodes_per_podcast` will start binding within ~5 months | config |
| C7 | Decision | 57,009 episodes (52,247 hours) downloaded but not transcribed | ASR |

---

### C1 — Episodes lost between discovery runs (High)

**What happens.** A minority of publishers run rolling feeds that carry only the
last N items. If `discover` runs less often than that window, every episode
published in between falls off the feed and is gone: RSS has no way to ask for
it later.

**Evidence.** *This American Life* holds episodes 862-870 and 887-895 in the
corpus and nothing in between — a seven-month hole covering episodes 871-886.
Its live feed carried **15 items** when checked on 2026-08-30, consistent with
the publisher's documented ~10-week retention. Ten shows show the same
signature (a live-window gap at least 6x their own publication interval and at
least 45 days long); see `analysis/output/temporal-coverage/live_window_gaps.csv`.

Some entries on that list are legitimate hiatuses — `20/20`, `Dateline
Originals` and `Bone Valley` are seasonal or limited-run. The ones to act on are
the weekly shows with month-scale holes: *This American Life*, *Therapuss with
Jake Shane*, *the bossbabe podcast*, *The Peter Attia Drive*, *The Money
Mondays*, *Afterpause*.

**Scope check.** Live capture is otherwise healthy: the median show's
publication rate changed by **+2.1%** between the year before collection and the
live window, and only 4 shows lost more than 40%. This is confined to
short-retention feeds, not a general failure.

**Actions.**

1. Run `discover` on a fixed weekly schedule. That is shorter than any retention
   window observed and would have caught every case found here. It is a writing
   stage, so it must be queued between `download` runs, not during one
   (`downloader/CLAUDE.md`, "Do not run a writing stage while `download` is
   running").
2. Record per-feed retention so the risk is visible. On each `discover` pass,
   store the feed's item count and its oldest item date on the `podcasts` row.
   A feed whose oldest item moves forward between runs is a rolling feed.
3. Add a gap alarm: after each run, flag any show whose newest recorded episode
   is older than 3x its median publication interval.
4. Decide about backfill. The missing *This American Life* episodes are not
   recoverable from RSS, but the publisher states the full archive is free on
   their website. Recovering them means scraping outside the RSS path — a
   deliberate scope decision, not an obvious yes.

---

### C2 — Duplicate episode rows (Medium)

**What happens.** 1,944 rows share a show, a publication timestamp **and** a
title, but carry distinct GUIDs, so the `episode_guid UNIQUE` constraint does not
catch them. One *PBD Podcast* episode is stored four times.

A further 1,027 rows share a show and timestamp but differ in title. Those are
ordinary batch drops and must **not** be collapsed.

**Impact.** Inflates per-period episode counts for affected shows, and means the
same audio may be transcribed more than once.

**Actions.**

1. Add a dedup pass keyed on `(podcast_id, published_date, title)`, keeping the
   earliest-inserted row. Verify against the audio archive before deleting rows
   that have a downloaded file.
2. Until that lands, deduplicate on that key in any analysis that counts
   episodes per period.
3. Consider a secondary uniqueness index to stop new duplicates arriving.

---

### C3 — Epoch publication dates (Low)

5 episodes (all *PBD Podcast*, and themselves near-duplicates — see C2) are
stored as `1970-01-01T00:3x:xx`. `rss._iso_date` builds a datetime from
`published_parsed`, and a feed entry with a zero or unparseable `pubDate` lands
on the epoch rather than `NULL`.

**Action.** Treat a pre-1995 parse result as no date and store `NULL`, so the
distinction between "undated" and "published in 1970" survives into the data.
All analyses currently filter these out by hand.

---

### C4 — Podcasts that were never discovered (Low)

6 of 226 podcast rows have no RSS URL and therefore no episodes: `Spotify Live`,
`soundbuttonsspace`, `JYP Podcast`, `Nourish Move Love Home Workouts`,
`Petty POV with Charlotte Dobre`, `Rotten Mango Video`.

The first three look like non-podcast chart artefacts. The last three are real
shows whose RSS lookup failed.

**Action.** Retry RSS resolution for the three real shows; drop or explicitly
mark the artefacts so the panel size (220 vs 226) stops being ambiguous.

---

### C5 — Episodes stuck in `error` (Low)

87 episodes failed download, 116 hours in total. Causes are almost entirely
publisher-side dead links: 66 are HTTP 404/403/410 on the audio URL, the rest are
connection failures and one zero-byte response. 46 of the 87 belong to
*The Joe Budden Podcast*, which suggests that show moved its back catalogue
behind a paywall rather than that anything went wrong locally.

**Action.** One retry sweep to clear transient connection failures, then accept
the remainder as permanently unavailable and record them as such so they stop
being re-attempted.

---

### C6 — The 5000-episode discovery cap will start binding (Low)

`discovery.max_episodes_per_podcast` is 5000, and `discover.run` keeps the newest
N per feed. Two shows are approaching it at their current rate:

| Show | Episodes | Live rate | Reaches 5000 in |
| --- | ---: | ---: | ---: |
| The MeidasTouch Podcast | 4,290 | ~1,790/yr | **~5 months** |
| The Charlie Kirk Show | 4,393 | ~513/yr | ~1.2 years |

**This is less dangerous than it looks.** The cap applies at discovery time and
`insert_episode` uses `INSERT OR IGNORE`, so episodes already recorded are not
deleted when a feed grows past the cap — they simply stop being re-seen. The real
exposure is a *newly added* show whose feed already exceeds 5000 items, which
would be silently truncated at its oldest end.

**Action.** Raise the cap or remove it. Feed sizes are already in the tens of
thousands of items for the largest shows and the pipeline handles them
(`Stuff You Should Know` parses a 10 MB feed with 2,870 items without trouble).

---

### C7 — Transcription backlog (Decision)

| Status | Episodes | Hours |
| --- | ---: | ---: |
| Transcribed | 75,390 | 79,520 |
| Downloaded, not transcribed | 57,009 | 52,247 |

43% of the corpus has audio but no transcript. Critically, **the transcribed
share is flat across eras** (46-60% every year since 2015), so this is not a
temporal confound — but it does halve the effective corpus for any text-based
analysis.

**Action.** Decide whether to clear the backlog before the next analysis round.
52,247 hours is the number to plan GPU capacity against; the remote batch route
in `downloader/docs/remote-batch-transcription.md` exists for exactly this.

---

## Ruled out — do not re-investigate

Recorded so these hypotheses are not re-opened later.

- **RSS pagination is not being missed.** `rss.fetch_feed` reads a single URL and
  does not follow `<atom:link rel="next">`. Nine feeds were checked on
  2026-08-30, including all six known-truncated ones: **none advertises
  pagination**. The missing support costs nothing today. Re-check if a new
  publisher is added.
- **The pipeline extracts what the feeds offer.** Live item counts match our
  stored counts almost exactly — Joe Rogan 2744/2744, Last Podcast On The Left
  1198/1198, LONGEVITY 464/464, The Basement Yard 576/576, Stuff You Should Know
  2870/2869, Something You Should Know 1324/1323, Radiolab 668/667. Where a feed
  is short, that is the publisher's doing, not ours. (*Habits and Hustle*: feed
  carries 300, we hold 343 — we have accumulated past its rolling window.)
- **Feeds are not capped at round item counts.** Per-show episode counts show no
  clustering at 100/200/300/500/1000.
- **Back-catalogue thinning is not feed truncation.** 97-98% of shows absent from
  any past month had not launched yet; only 6 of 220 feeds (3%) are demonstrably
  truncated. Validated against published launch dates for 8 shows, 6 matching,
  several to the day.

## Known blind spot

**Feed rebrands cannot be detected from feed-internal evidence.** *The Bill
Simmons Podcast* has a complete feed back to its own 2015 start, but the show
began in 2007 as *The B.S. Report* on a different feed. Any show that migrated
feeds will look younger than it is, and the classifier in
`coverage_attribution.py` will call it complete. If show age matters to a
result, check that show externally.

## Constraints for downstream analysis

Carry these into any study built on this corpus.

1. **Anchor prevalence claims to the live window** (2025-10-13 onward). It is the
   only stretch with a near-complete panel and a known sampling rule: 2,284
   episodes/month from ~198 shows, coefficient of variation 0.067.
2. **The back catalogue is a young panel, not a censored one.** It is sound for
   tracing a narrative backwards through the shows that existed. It cannot
   support a prevalence rate for a past year — the panel itself is what changes.
3. **Normalise before plotting any trend.** Raw counts rise partly because more
   shows are observed and more shows have joined; 5 shows entered after
   2026-06-01 alone. Divide by observed shows, or hold the cohort fixed.
4. **Drop the trailing month.** The snapshot cuts off mid-month and transcription
   lags ingestion, so the last point of every series is an artefact.
5. **Deduplicate first** (C2), and **exclude epoch-dated rows** (C3).

## Suggested follow-ups

- **Feed retention census.** Fetch all 220 feeds once, recording item count and
  oldest item date. This converts the 69 "unverified" shows into measured ones,
  gives each feed a required discovery cadence for C1, and costs one pass.
- **External launch dates.** The Podcast Index API carries launch dates and would
  settle the remaining unverified shows without the manual web checks used here.
- **Re-run the audit after the next collection quarter** to confirm the weekly
  `discover` schedule closed the C1 gaps.
