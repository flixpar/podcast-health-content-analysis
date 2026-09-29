# Deeper US Apple chart data for 2024–2026: scouting report

**Collected 2026-09-04.** Follow-up to `docs/chart-archive-findings.md`, which left
one hole: from 2024-08 our Apple series is dense (464 days, 1-day median gap) but
only **24 ranks deep**, so ranks 25–100 are invisible for the most recent two
years and 199 shows that held a top-24 slot in 2025–26 are outside the population.

**Headline: the prospective problem is solved.** Apple still serves its old
public chart feeds. `rss.marketingtools.apple.com` gives a **top 100** and
`itunes.apple.com/us/rss/toppodcasts` gives a **top 200**, both live today, both
free, both unauthenticated, and both — verified below — the *same* chart in the
*same* order as `podcasts.apple.com/us/charts`.

**The retrospective problem is mostly not solved.** No archive recorded a deep
Apple US chart densely during 2024–2026. The best partial fixes are six
250-deep Rephonic captures and a Podchaser API entitlement we do not currently
hold.

---

## 1. Source table

| # | Source | Works? | Max depth | Date range | Cadence | Format | Auth | Verdict |
|---|---|---|---:|---|---|---|---|---|
| 1 | `itunes.apple.com/us/rss/toppodcasts/limit=N/json` | **YES, live** | **200** | live now | refresh cadence not established | JSON (also `/xml`) | none | **Deepest free live feed.** Carries adamIds. But `robots.txt` disallows it — see §4. |
| 2 | `rss.marketingtools.apple.com/api/v2/us/podcasts/top/100/podcasts.json` | **YES, live** | **100** | live now | refresh cadence not established | JSON (also `.rss`) | none | **Recommended primary daily capture.** Robots-clean, and 100 is exactly our historical population depth. |
| 3 | `podcasts.apple.com/us/charts` (current harvester) | yes | 24 | 2024-08 → now | daily | HTML + `serialized-server-data` JSON | none | Keep as the cross-check; superseded for depth. |
| 4 | `amp-api.podcasts.apple.com/v1/catalog/us/charts` | not pursued | ? | — | — | JSON | bearer token | **Not needed and not clean.** See §4. |
| 5 | **Rephonic** `rephonic.com/charts/apple/united-states/top-podcasts` | **YES (archived)** | **250** | 6 US-overall captures 2024-08 → 2026-04 | irregular | HTML `<table>`, 250 rows | none | Only deep 2024–26 Apple archive found. Six days, no Apple ids. |
| 6 | **Podchaser** GraphQL `charts(platform:APPLE_PODCASTS, day:…)` | **exists, we are blocked** | paginated, unknown | by day, historical | daily | GraphQL | OAuth + entitlement | **Highest-value retrospective lead.** Query is exactly right; our client lacks the permission. |
| 7 | `rss.applemarketingtools.com` (old host) | redirect only | — | — | — | — | — | 301 → `rss.marketingtools.apple.com`. Use the new host. |
| 8 | `ax.itunes.apple.com` legacy RSS | not re-probed | 300 (historical) | pre-2013 mostly | — | XML | none | Historic curiosity; nothing for 2024+. |
| 9 | **Podstatus** `podstatus.com/charts[/applepodcasts]` | NO | 0 | 2024-10 → 2026-08, ~30 captures | — | HTML | login-walled | Fetched a capture: marketing page, **no ranked rows**. 10,788 captures are site chrome. |
| 10 | **Podscribe** `podscribe.com/podcast-rankings` | NO | 0 | 2025-01 → 2026 | — | HTML | — | Fetched a capture: **no ranked rows** in the archived HTML; also its own reach metric, not Apple. |
| 11 | **Podcharts.co** `podcharts.co/charts/us/<date>` | NO (for 2024+) | — | date-keyed URLs but only 2023 captures | — | HTML | login-walled | Promising URL shape (`/charts/us/2023-09-19`), 110 of 362 captures are `/login`. Dead for our window. |
| 12 | `podcastcharts.io` | NO | — | — | — | — | — | **Zero** Wayback captures from 2024. |
| 13 | `livuh.com` | NO | — | — | — | — | — | **Zero** Wayback captures from 2024. |
| 14 | `chartmetric.com/charts` | NO | — | — | — | — | — | **Zero** Wayback captures from 2024. |
| 15 | **Podcast Index** `api.podcastindex.org` | NO (no Apple ranks) | — | — | — | JSON | API key | Ranking endpoint is `/podcasts/trending`, computed from its own index. No Apple chart positions. **Unverified** — docs page is a JS shell, API not probed. |
| 16 | Spotify `podcastcharts.byspotify.com` | (already harvested) | 200 | — | daily | JSON | none | Not re-examined per brief. No deeper variant found. |

---

## 2. Worked example: the two live Apple feeds

### 2a. Legacy iTunes RSS — depth 200

```
$ curl -s 'https://itunes.apple.com/us/rss/toppodcasts/limit=200/json'
```

```json
{"feed":{
  "title":  {"label":"iTunes Store: Top Podcasts"},
  "updated":{"label":"2026-09-04T10:11:43-07:00"},
  "entry":[
    {"im:name":  {"label":"The Daily"},
     "title":    {"label":"The Daily - The New York Times"},
     "id":       {"label":"https://podcasts.apple.com/us/podcast/the-daily/id1200361736?uo=2",
                  "attributes":{"im:id":"1200361736"}},
     "im:artist":{"label":"The New York Times"},
     "category": {"attributes":{"im:id":"1526","term":"Daily News"}},
     "im:releaseDate":{"label":"2026-09-04T03:00:00-07:00"}},
    ...199 more, rank == array position...
  ]}}
```

Every row carries the **Apple adamId** (`id.attributes.im:id`) — the same
identifier the Podbay series uses, so it joins cleanly to the existing
population table. It also carries the show's primary genre.

Depth ladder (probed 2026-09-04):

| `limit=` | 10 | 25 | 50 | 100 | 150 | **200** | 201 | 250 | 300 | 400 |
|---|---|---|---|---|---|---|---|---|---|---|
| result | 10 | 25 | 50 | 100 | 150 | **200** | 400 | 400 | 400 | 400 |

`limit=201` and above return `HTTP 400 — Invalid value for param 'limit'.`
**200 is a hard ceiling.** Arbitrary values below 200 are honoured, so this is a
real `limit` parameter, not a fixed set of prebuilt feeds.

**Genre feeds work at the same depth:**
`https://itunes.apple.com/us/rss/toppodcasts/limit=200/genre=1489/json`
→ 200 entries, `"iTunes Store: Top Podcasts in News"`. This is the only source
found that gives deep *genre* charts live.

### 2b. Apple Marketing Tools — depth 100

```
$ curl -s 'https://rss.marketingtools.apple.com/api/v2/us/podcasts/top/100/podcasts.json'
```

```json
{"feed":{
  "title":"Top Shows",
  "updated":"Fri, 4 Sep 2026 17:12:25 +0000",
  "results":[
    {"id":"1200361736","name":"The Daily","artistName":"The New York Times",
     "kind":"podcasts",
     "genres":[{"genreId":"1489","name":"News"}],
     "url":"https://podcasts.apple.com/us/podcast/the-daily/id1200361736"},
    ...99 more, rank == array position...
  ]}}
```

Depth ladder: 10 / 25 / 50 / 100 all return exactly that many rows; **150 and
200 return `HTTP 500`**. 100 is the ceiling. The genre path
`/top/100/1489/podcasts.json` returns **404** — this host has no genre feed in
that shape.

### 2c. Cross-validation — all three sources are the same chart

Fetched within the same minute on 2026-09-04:

| Comparison | Ranks compared | Exact rank-for-rank match |
|---|---:|---:|
| `podcasts.apple.com/us/charts` "Top Shows" vs legacy RSS | 24 | **24 / 24** |
| `podcasts.apple.com/us/charts` "Top Shows" vs marketingtools | 24 | **24 / 24** |
| marketingtools vs legacy RSS | 100 | **100 / 100** |

The first ten rows, identical across all three:

```
 1 The Daily                      6 Up First from NPR
 2 Crime Junkie                   7 COERCED: The Devotion & Death of Mic…
 3 The Joe Rogan Experience       8 Morbid
 4 Dateline NBC                   9 Pardon My Take
 5 Mick Unplugged                10 REAL AF with Andy Frisella
```

This bears on a doubt left open by the earlier findings doc, which reported only
**30% median overlap** between Podbay and the legacy RSS. *Today* the feed is
rank-for-rank identical to Apple's own chart page, so that 30% is unlikely to
reflect the feed ranking something different. The plausible cause is that the
archived RSS captures mix storefronts, genres and limits — but this was **not
verified**: the 2012–2019 captures were not re-examined here.

**Refresh cadence is not established.** Both feeds' `updated` stamps were within
a minute of the fetch, which is consistent with on-demand generation rather than
a fixed hourly rebuild. Capture daily and log the stamp; the data will tell us.

---

## 3. Worked example: Rephonic (the one retrospective hit)

```
$ curl -s 'https://web.archive.org/web/20250312153935id_/https://rephonic.com/charts/apple/united-states/top-podcasts'
```

`<title>Apple Podcasts Charts - United States - View Rankings for All Shows</title>`,
one `<table>` with a header row and **249 data rows, ranks `# 1` to `# 250`**:

```
# 1    The Mel Robbins Podcast              /podcasts/the-mel-robbins-podcast
# 2    Michelle Obama: The Light Podcast    /podcasts/the-michelle-obama-podcast
# 3    The MeidasTouch Podcast              /podcasts/the-meidastouch-podcast
# 4    The Joe Rogan Experience             /podcasts/the-joe-rogan-experience
…
# 248  TED Talks Daily                      /podcasts/ted-talks-daily
# 250  Handsome                             /podcasts/handsome
```

**Caveats.**
- Only **6 captures** of the US overall chart in our window: `2024-08-05`,
  `2025-03-12`, `2025-03-23`, `2025-04-03`, `2025-05-21`, `2026-04-20`.
  That is six extra days, not a series.
- The page carries **no visible chart date**, so the chart may lag the capture
  timestamp. Treat the capture date as **±1 day**.
- Rows carry **Rephonic slugs, not Apple adamIds** — joining to the population
  needs title/slug matching, the same weakness Chartable had.
- 7,337 Rephonic Apple captures exist for 2024+ across all countries, and ~150
  for US *genre* charts (`/news-politics` 8 captures, `/sports` 5, `/comedy` 5,
  …), so a small amount of extra genre depth is recoverable too.
- **Rephonic is no longer scrapable live**: the chart page is now client-rendered
  (32 KB of Next.js shell, zero `<tr>`), and `robots.txt` has
  `Disallow: /_next/*.json$` — which is precisely the data route. Do not pursue
  it prospectively.

---

## 4. Terms and robots — read before choosing

| Host | `robots.txt` says |
|---|---|
| `rss.marketingtools.apple.com` | Comment line only. **No restrictions.** |
| `itunes.apple.com` | `User-agent: *` … **`Disallow: /*/rss/*`** — this covers the legacy chart feed. |
| `podcasts.apple.com` | `Disallow: /WebObjects/*`, **`/api/*`**, `/includes/*`, **`/v1/*`** |
| `amp-api.podcasts.apple.com` | No `robots.txt` (returns an HTML error page). |

This is the one judgement call in the report, and it belongs to you, not to me:

- **Marketing Tools is unambiguously fine.** No robots restriction, an
  Apple-published feed explicitly built for third-party use, no auth.
- **The legacy RSS feed is disallowed by `itunes.apple.com/robots.txt`.** It is
  public, unauthenticated, still maintained (the `updated` stamp is current), and
  is the same data Marketing Tools serves — but the robots directive is there.
  Using it for research is a decision to make deliberately, not by default.
- **The `amp-api` route was not pursued, and should not be.** Three findings:
  (a) the bearer token is **not** in the server-rendered HTML we fetch — the page
  contains zero JWT-shaped strings (the 20 `eyJ…` hits are base64 `{"src":…}`
  artwork blobs), so obtaining a token means executing or mining the JS bundle;
  (b) `podcasts.apple.com/robots.txt` disallows `/v1/*` and `/api/*`;
  (c) it is **unnecessary** — the RSS feeds already give 200, and Wayback holds
  only 3 incidental `amp-api` chart captures for 2024+ (one of them at
  `limit=24`), so there is nothing retrospective there either.
  Verdict: not ordinary public access, and no longer worth the question.

---

## 5. Negative results, stated plainly

Worth recording so nobody re-checks these:

- **Archived RSS is useless retrospectively.** Our existing CDX index has **8**
  `itunes.apple.com/rss/toppodcasts` captures for 2024+ and **3** marketingtools
  captures — and most are the wrong limit or a genre feed
  (`limit=100/genre=1301`, `limit=10/genre=1314`, `top/10/podcast-episodes.rss`).
  The feed we should have been capturing all along was live the whole time and
  nobody archived it. Two usable days, at best.
- `podcastcharts.io`, `livuh.com`, `chartmetric.com/charts`: **zero** Wayback
  captures from 2024 onward. Not "thin" — zero.
- `podstatus.com`: 10,788 captures 2024+ is the third false positive of this
  kind. The breakdown is `/` (93), `/register` (45), `/about` (43), `/cookies`
  (41) — marketing chrome. `/charts` has 27 captures and `/charts/applepodcasts`
  a handful; a fetched capture of the latter is 9 KB with **no ranked rows and no
  Apple ids**. The product is behind a login.
- `podscribe.com/podcast-rankings`: 42 captures, fetched one, **no ranked rows**
  in the archived HTML. Also ranks by Podscribe's own reach estimate, not Apple.
- `podcharts.co`: date-keyed chart URLs (`/charts/us/2023-09-19`) that would have
  been ideal — but only two such captures exist, both 2023, and 110 of its 362
  captures are the login page.
- `rss.applemarketingtools.com` (the older host name) 301-redirects to
  `rss.marketingtools.apple.com`. Same data; use the current host.
- **Podcast Index** exposes `/podcasts/trending` computed over its own index, not
  Apple chart positions. **Unverified** — from prior knowledge of the API; the
  docs page at `podcastindex-org.github.io/docs-api/` is a 2.6 KB client-rendered
  shell and could not be checked, and the API was not probed with a key.

---

## 6. Podchaser: the entitlement worth asking for

The project's credentials in `downloader/config.json` authenticate fine
(`requestAccessToken` with `CLIENT_CREDENTIALS` returns a token). Schema
introspection shows Podchaser has exactly the query we want:

```graphql
charts(
  platform: ChartPlatform!      # APPLE_PODCASTS | SPOTIFY | …
  day:      Date!               # historical, by day
  category: String
  country:  String
  first:    Int
  page:     Int
): ChartPositionPaginator
```

```graphql
type ChartPosition {
  platform  country  day  position
  change    changeStatus     # rank delta vs previous day
  category  podcastIdentifier
  podcast   # full Podchaser podcast object
}
```

Field description, verbatim from the schema:

> *"Retrieve chart data for Apple Podcasts charts or Spotify charts by country,
> day, and category. **Only available with certain permissions.**"*

Our client does not have them. Both `charts` and `chartCategories` return:

```json
{"errors":[{"message":"Client is not authorized to view podcast charts",
            "extensions":{"category":"user"}}]}
```

This is a paid/entitlement tier, not a bug or a rate limit — the query is
correctly formed and the token is valid. **It is the only route found that could
fill 2024–2026 at depth after the fact, day by day, with rank-change deltas.**
An email to Podchaser describing the research use is a cheap, high-expected-value
next step.

---

## 7. Recommendations

### Prospective — start tomorrow, ~15 lines of code

Capture **both** Apple feeds daily, so losing one does not lose the series:

```
https://rss.marketingtools.apple.com/api/v2/us/podcasts/top/100/podcasts.json   # primary, robots-clean, depth 100
https://itunes.apple.com/us/rss/toppodcasts/limit=200/json                      # supplement, depth 200 — see §4
```

- **Depth 100 alone already closes the gap**, because the historical population
  is defined on the top 100. Depth 200 is a bonus, and comes with the robots
  caveat in §4 — your call whether to take it.
- Store the feed's own `updated` timestamp alongside the fetch time; use it to
  dedupe (the feed refreshes on its own cadence, not on ours).
- Both give **adamIds directly**, so rows join to the Podbay-era population with
  no title matching.
- Add the genre feeds if genre charts matter:
  `itunes.apple.com/us/rss/toppodcasts/limit=200/genre=<id>/json` (genre ids are
  already in `APPLE_GENRES` in `analysis/chart_archive/parse.py`).
- Keep the existing `podcasts.apple.com/us/charts` harvester running. It costs
  nothing, it is robots-clean, and it gives a daily 24-deep cross-check plus the
  four other shelves (Top Subscriber Shows, Top Series, Trending Episodes) that
  the RSS feeds do not carry.
- Parsing is trivial — rank is array position in both feeds. Neither is a new
  parser family; both are flat JSON.

### Retrospective — in order of expected value

1. **Ask Podchaser for the charts entitlement** (§6). The only route to
   day-by-day depth for 2024–2026. Everything else here is scraps.
2. **Harvest the 6 Rephonic captures** (§3). Six days at depth 250, plus ~150
   US genre captures. Small, certain, an afternoon's work — but needs
   title-matching to resolve to adamIds, so treat it as supplementary evidence
   about ranks 25–250, not as population-defining days.
3. **Accept that the 2024–2026 window stays 24-deep** for the ~460 days already
   collected, and say so in the methods section. Prospectively the problem ends;
   retrospectively, absent Podchaser, it does not.

### Not worth further time

`amp-api` (§4), Podstatus, Podscribe, Podcharts.co, Podcastcharts.io, Livuh,
Chartmetric, Podcast Index, live Rephonic scraping, and re-querying the archived
RSS feeds.

---

## 8. What was not done

- `index.commoncrawl.org` was attempted on 2026-09-04 and is **flaky, not down**:
  one `collinfo.json` fetch succeeded (the index list is intact, back to 2008),
  then seven consecutive attempts over the next few minutes — four for
  `collinfo.json`, three for a targeted CDX query — all returned
  `Failed to connect … port 443`. No targeted query completed. **Common Crawl
  remains the one unexamined retrospective avenue**: it does index JSON
  endpoints, so archived `rss.marketingtools.apple.com/api/v2/us/podcasts/top/*`
  and `itunes.apple.com/us/rss/toppodcasts/*` responses may exist there for
  2024–2026. Retry when the host is stable — it is worth a second hour.
- No bulk download was performed anywhere. This is scouting only; every fetch
  above was a single capture or a single live request.
- Podcast Index was assessed from documentation rather than probed with a key.
- Rephonic's non-US and genre captures were counted but not parsed.
