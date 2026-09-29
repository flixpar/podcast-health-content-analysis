#!/usr/bin/env python3
"""Render the temporal-coverage outputs as a self-contained HTML memo.

Figures are inlined as data URIs so the page has no external dependencies.
The markup is a body fragment (no <html>/<head>/<body>) so it can be published
directly as an Artifact, which supplies that skeleton.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
from datetime import date
from pathlib import Path

import pandas as pd


def read_csv(path: Path):
    return pd.read_csv(path)

DEFAULT_OUTPUT = Path("analysis/output/temporal-coverage")

FIGURES = [
    ("fig1_volume_by_month.png",
     "Monthly volume and episode length",
     "Episodes rise smoothly from a handful a month in 2006 to roughly 2,300 today. "
     "The curve is a retention artefact, not audience history: it traces how much of "
     "each past month survives in today's feeds. Median episode length peaked near "
     "90 minutes in 2013-14 and now sits around 47, though the early years reflect "
     "only a few long-form shows."),
    ("fig3_backcatalog_depth.png",
     "Archive depth and where the mass sits",
     "Half the shows carry five years or more of back catalogue; a quarter carry under "
     "two. On the right, the cumulative curve: three quarters of all episodes were "
     "published after June 2025, so the corpus is far more a record of the present "
     "than of the past."),
    ("fig2_panel_completeness.png",
     "How much of the panel is observed each month",
     "Only in 2026 does the corpus observe more than 90% of its shows in a given month. "
     "Go back to 2020 and roughly 40% of shows are present; to 2015 and it is under 10%. "
     "Cross-show comparisons before about 2023 are drawn from a shrinking, "
     "survivorship-selected panel."),
    ("fig4_coverage_spans.png",
     "Per-show coverage windows",
     "One bar per show, first episode to last, ordered by start date and shaded by "
     "publication density. The staircase is the shape of RSS retention: most shows "
     "expose a few years, a handful expose everything, and almost all of them run to "
     "the collection cut-off."),
    ("fig6_cadence.png",
     "Publication rhythm in the live window",
     "Weekly volume holds near 531 episodes with a sharp dip over the winter holidays "
     "and a step up in July 2026 as new shows entered the panel. Publishing is a "
     "weekday activity: Monday is the heaviest day, and the UTC hour histogram peaks "
     "in the 07:00-10:00 band, matching an overnight US drop."),
    ("fig7_show_month_heatmap.png",
     "Month-to-month consistency of the largest shows",
     "Each row is scaled to its own busiest month, so pale cells mark months where a "
     "show produced well below its own norm. Most rows are even. The Level Up Podcast "
     "is the clear regime change, roughly tripling its output in March 2026."),
    ("fig5_transcript_coverage.png",
     "Transcript availability over time",
     "The transcribed share hovers around the 57% corpus mean in every era from 2018 "
     "on. Whatever governs which episodes get transcribed, it is not the publication "
     "date, so time-sliced comparisons are not confounded by it. The dip in the final "
     "month is transcription still in flight, not a coverage gap."),
]

ATTRIBUTION_FIGURES = [
    ("fig8_coverage_attribution.png",
     "Why a show is missing from any given month",
     "Every show, every month, sorted by why it is or is not in the corpus. The pale "
     "bands are shows that did not exist yet; they account for almost the whole decline. "
     "The thin red band is the only genuine data loss: shows that were publishing but "
     "whose feed no longer carries those episodes."),
    ("fig9_feed_completeness_evidence.png",
     "The evidence behind that split",
     "Left: what can be established about each of the 220 feeds. Right: for the 48 shows "
     "that number their episodes sequentially, where the feed's oldest surviving episode "
     "sits. Forty-two still carry episode 1 — those archives are complete by "
     "construction, not by assumption."),
]

TAKEAWAYS = [
    ("Anchor claims to the live window",
     "The 10 months from October 2025 are the only stretch where the panel is nearly "
     "complete and the sampling rule is known. Prevalence rates and cross-show "
     "comparisons belong here."),
    ("Treat the back catalogue as a young panel, not a censored one",
     "Pre-collection coverage is near-complete for the shows that existed, so it is "
     "sound for tracing a narrative backwards through them. What it cannot support is "
     "a prevalence rate for a past year, because the panel itself is the thing changing."),
    ("Normalise before plotting any trend",
     "Raw episode counts rise partly because more shows are observed and more shows "
     "have joined. Divide by observed shows, or hold the panel fixed."),
    ("Deduplicate first",
     "About 1,900 rows are the same episode published twice under different GUIDs. "
     "They inflate per-period counts for the shows that produce them."),
    ("Run discovery more often than the shortest feed",
     "Short-retention feeds drop episodes between runs and those episodes are then "
     "unrecoverable from RSS. A weekly discover pass would have caught every case "
     "found here."),
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def stat_cells(summary: dict) -> list[tuple[str, str, str]]:
    depth = summary["archive_depth_years"]
    return [
        ("Episodes", f"{summary['episodes_total']:,}", f"{summary['shows_total']} shows"),
        ("Audio", f"{summary['audio_hours'] / 1000:,.1f}k", "hours"),
        ("Window", f"{summary['first_episode'][:4]}–{summary['last_episode'][:4]}",
         f"{summary['months_spanned']} months"),
        ("Live capture", f"{summary['live_window_months']} mo",
         f"{summary['live_episodes']:,} episodes"),
        ("Median depth", f"{depth['median']:.1f} yr", "per show"),
        ("Transcribed", f"{summary['transcribed_pct']:.0f}%",
         f"{summary['transcribed_total']:,} episodes"),
    ]


def render(summary: dict, attribution: dict, validation, figure_dir: Path) -> str:
    stats = "\n".join(
        f'      <div class="stat"><span class="stat-label">{esc(label)}</span>'
        f'<span class="stat-value">{esc(value)}</span>'
        f'<span class="stat-note">{esc(note)}</span></div>'
        for label, value, note in stat_cells(summary)
    )

    def plates(spec):
        out = []
        for filename, title, caption in spec:
            path = figure_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"missing figure: {path}")
            out.append(
                f'    <figure class="plate">\n'
                f'      <h3>{esc(title)}</h3>\n'
                f'      <div class="plate-img"><img src="{data_uri(path)}" '
                f'alt="{esc(title)}"></div>\n'
                f'      <figcaption>{esc(caption)}</figcaption>\n'
                f'    </figure>'
            )
        return "\n".join(out)

    figures = plates(FIGURES)
    attribution_figures = plates(ATTRIBUTION_FIGURES)

    takeaways = "\n".join(
        f'      <li><strong>{esc(head)}</strong><span>{esc(body)}</span></li>'
        for head, body in TAKEAWAYS
    )

    quartiles = summary["quartile_months"]
    reach = summary["shows_reaching_back"]

    checks = "\n".join(
        f'        <tr><td>{esc(r["show"])}</td><td>{esc(r["observed_first"])}</td>'
        f'<td>{esc(r["published_launch"])} <span class="pre">({esc(r["precision"])})</span></td>'
        f'<td class="{"ok" if r["agrees"] else "no"}">{"match" if r["agrees"] else "differs"}</td>'
        f'<td class="pre">{esc(r["verdict"])}</td></tr>'
        for _, r in validation.iterrows()
    )
    v = attribution["verdicts"]
    snap = attribution["month_snapshots"]["2015-01"]

    return TEMPLATE.format(
        stats=stats,
        figures=figures,
        attribution_figures=attribution_figures,
        checks=checks,
        complete=v.get("complete", 0),
        truncated=v.get("truncated", 0),
        unverified=v.get("unverified", 0),
        complete_pct=round(100 * v.get("complete", 0) / attribution["shows"]),
        truncated_pct=round(100 * v.get("truncated", 0) / attribution["shows"]),
        unverified_pct=round(100 * v.get("unverified", 0) / attribution["shows"]),
        snap_absent=snap["absent"],
        snap_truncated=snap["feed_truncated"],
        snap_min=snap["min_missing_share_of_absent"],
        snap_max=snap["max_missing_share_of_absent"],
        agree=attribution["external_agreements"],
        checked=attribution["external_checks"],
        gap_suspects=attribution["live_gap_suspects"],
        live_rate=f"{attribution['median_live_rate_change']:+.1%}",
        takeaways=takeaways,
        generated=date.today().isoformat(),
        first=esc(summary["first_episode"]),
        last=esc(summary["last_episode"]),
        collection_start=esc(summary["collection_start"]),
        live_mean=f"{summary['live_episodes_per_month_mean']:,.0f}",
        live_cv=f"{summary['live_episodes_per_month_cv']:.3f}",
        live_shows=f"{summary['live_shows_per_month_mean']:.0f}",
        q25=esc(quartiles["25"]), q50=esc(quartiles["50"]), q75=esc(quartiles["75"]),
        last12=f"{summary['share_last_12_months_pct']:.0f}",
        reach1=reach["1y"], reach3=reach["3y"], reach5=reach["5y"], reach10=reach["10y"],
        shows=summary["shows_total"],
        stale=summary["shows_stale_over_6_months"],
        current=summary["shows_active_in_final_month"],
        undated=summary["episodes_undated"],
        dupes=f"{summary['duplicate_title_rows']:,}",
        batched=f"{summary['same_timestamp_distinct_title_rows']:,}",
        joiners=summary["shows_joining_after_2026_06"],
        rss=f"{summary['rss_transcripts']:,}",
    )


TEMPLATE = """<title>Podcast Corpus Coverage Audit</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  :root {{
    color-scheme: light;
    --ground:   #f7f8fa;
    --surface:  #ffffff;
    --plate:    #ffffff;
    --ink:      #14171c;
    --ink-2:    #3d454f;
    --muted:    #6b7482;
    --hairline: #e2e6ec;
    --accent:   #2a6fce;
    --accent-soft: #eaf1fb;
    --warn:     #b4501f;
    --warn-soft: #fbeee6;
    --shadow:   0 1px 2px rgba(20, 23, 28, .05), 0 8px 24px rgba(20, 23, 28, .05);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      color-scheme: dark;
      --ground:   #101318;
      --surface:  #171b21;
      --plate:    #f2f3f5;
      --ink:      #eef1f5;
      --ink-2:    #c3cad4;
      --muted:    #8f99a7;
      --hairline: #262c35;
      --accent:   #6ba4f0;
      --accent-soft: #1a2634;
      --warn:     #e08a5c;
      --warn-soft: #2a1f18;
      --shadow:   0 1px 2px rgba(0, 0, 0, .3), 0 8px 24px rgba(0, 0, 0, .28);
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --ground:   #101318;
    --surface:  #171b21;
    --plate:    #f2f3f5;
    --ink:      #eef1f5;
    --ink-2:    #c3cad4;
    --muted:    #8f99a7;
    --hairline: #262c35;
    --accent:   #6ba4f0;
    --accent-soft: #1a2634;
    --warn:     #e08a5c;
    --warn-soft: #2a1f18;
    --shadow:   0 1px 2px rgba(0, 0, 0, .3), 0 8px 24px rgba(0, 0, 0, .28);
  }}

  body {{
    background: var(--ground);
    color: var(--ink);
    font-family: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
    font-size: 16px;
    line-height: 1.62;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{
    max-width: 1000px;
    margin: 0 auto;
    padding: clamp(2rem, 5vw, 4.5rem) clamp(1.1rem, 4vw, 2.5rem) 5rem;
    display: flex;
    flex-direction: column;
    gap: 3.25rem;
  }}
  .prose {{ max-width: 68ch; display: flex; flex-direction: column; gap: 1rem; }}

  h1, h2, h3 {{
    font-family: Newsreader, Georgia, "Times New Roman", serif;
    font-weight: 600;
    letter-spacing: -.012em;
    text-wrap: balance;
    margin: 0;
  }}
  h1 {{ font-size: clamp(2.1rem, 5vw, 3.1rem); line-height: 1.1; }}
  h2 {{ font-size: clamp(1.45rem, 3vw, 1.85rem); line-height: 1.22; }}
  h3 {{ font-size: 1.06rem; font-weight: 600; letter-spacing: 0; }}
  p {{ margin: 0; color: var(--ink-2); }}
  strong {{ color: var(--ink); font-weight: 600; }}
  a {{ color: var(--accent); }}

  .eyebrow {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .74rem;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .dek {{
    font-family: Newsreader, Georgia, serif;
    font-size: clamp(1.1rem, 2.3vw, 1.35rem);
    font-style: italic;
    line-height: 1.5;
    color: var(--ink-2);
    max-width: 60ch;
  }}

  header .meta {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .78rem;
    color: var(--muted);
    border-top: 1px solid var(--hairline);
    padding-top: .85rem;
    display: flex;
    flex-wrap: wrap;
    gap: .35rem 1.5rem;
  }}
  header {{ display: flex; flex-direction: column; gap: 1.15rem; }}

  .stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1px;
    background: var(--hairline);
    border: 1px solid var(--hairline);
    border-radius: 3px;
    overflow: hidden;
  }}
  .stat {{
    background: var(--surface);
    padding: 1rem 1.15rem 1.1rem;
    display: flex;
    flex-direction: column;
    gap: .1rem;
  }}
  .stat-label {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .68rem; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted);
  }}
  .stat-value {{
    font-family: Newsreader, Georgia, serif;
    font-size: 1.85rem; line-height: 1.15; font-variant-numeric: tabular-nums;
    color: var(--ink);
  }}
  .stat-note {{ font-size: .8rem; color: var(--muted); }}

  section {{ display: flex; flex-direction: column; gap: 1.5rem; }}
  section > .prose:first-of-type {{ gap: .85rem; }}

  .plate {{
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: .8rem;
    background: var(--surface);
    border: 1px solid var(--hairline);
    border-radius: 4px;
    padding: 1.35rem 1.35rem 1.2rem;
    box-shadow: var(--shadow);
  }}
  .plate-img {{
    overflow-x: auto;
    background: var(--plate);
    border-radius: 2px;
  }}
  .plate img {{ display: block; width: 100%; min-width: 560px; height: auto; }}
  figcaption {{ font-size: .92rem; color: var(--ink-2); max-width: 76ch; }}

  .callout {{
    border-left: 2px solid var(--accent);
    background: var(--accent-soft);
    padding: 1.1rem 1.3rem;
    border-radius: 0 3px 3px 0;
    font-size: .95rem;
  }}
  .callout.caution {{ border-left-color: var(--warn); background: var(--warn-soft); }}

  ol.takeaways {{
    list-style: none;
    counter-reset: t;
    margin: 0; padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1px;
    background: var(--hairline);
    border: 1px solid var(--hairline);
    border-radius: 3px;
    overflow: hidden;
  }}
  ol.takeaways li {{
    counter-increment: t;
    background: var(--surface);
    padding: 1.15rem 1.3rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: .4rem;
  }}
  ol.takeaways li::before {{
    content: counter(t, decimal-leading-zero);
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .72rem; letter-spacing: .1em;
    color: var(--accent);
  }}
  ol.takeaways strong {{ font-size: 1rem; }}
  ol.takeaways span {{ font-size: .92rem; color: var(--ink-2); }}

  ul.notes {{ margin: 0; padding-left: 1.1rem; display: flex; flex-direction: column; gap: .5rem; }}
  ul.notes li {{ color: var(--ink-2); }}
  ul.notes li::marker {{ color: var(--muted); }}

  table.checks {{
    width: 100%;
    border-collapse: collapse;
    font-size: .88rem;
    font-variant-numeric: tabular-nums;
  }}
  table.checks th, table.checks td {{
    text-align: left;
    padding: .5rem .7rem;
    border-bottom: 1px solid var(--hairline);
  }}
  table.checks th {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .68rem; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted); font-weight: 400;
  }}
  table.checks td.ok {{ color: var(--accent); }}
  table.checks td.no {{ color: var(--warn); }}
  table.checks .pre {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .82em; color: var(--muted);
  }}
  .table-wrap {{ overflow-x: auto; }}

  code {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .86em;
    background: var(--accent-soft);
    padding: .1em .35em;
    border-radius: 2px;
    color: var(--ink);
  }}
  footer {{
    border-top: 1px solid var(--hairline);
    padding-top: 1.1rem;
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: .76rem;
    color: var(--muted);
    line-height: 1.7;
  }}
  :focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
</style>

<div class="wrap">
  <header>
    <span class="eyebrow">Corpus audit &middot; podcast-misinfo</span>
    <h1>What years does this corpus actually cover?</h1>
    <p class="dek">The archive spans two decades but only observes the whole show panel
      for the last ten months. The thinning further back is almost entirely shows that
      had not launched yet &mdash; not feeds that forgot.</p>
    <div class="meta">
      <span>Generated {generated}</span>
      <span>Source: downloader/data/podcast_metadata.db</span>
      <span>Episodes dated {first} &ndash; {last}</span>
    </div>
  </header>

  <div class="stats">
{stats}
  </div>

  <section>
    <div class="prose">
      <h2>Two corpora in one</h2>
      <p>Collection began on <strong>{collection_start}</strong>. Everything published after
        that date was captured as it appeared: a near-complete census of {shows} shows,
        averaging <strong>{live_mean} episodes a month</strong> from {live_shows} distinct
        shows, with a coefficient of variation of just {live_cv}. That stability is the
        pipeline working as intended.</p>
      <p>Everything published <em>before</em> that date arrived in a single sweep of each
        show's RSS feed, and feeds only retain what their publisher chooses to keep. The
        back catalogue is therefore not a sample of what podcasts published &mdash; it is a
        sample of what publishers still expose. The two halves need different statistical
        treatment, and the figures below are mostly about telling them apart.</p>
      <div class="callout">
        <strong>The recency skew is severe.</strong> A quarter of all episodes were
        published after {q25}, half after {q50}, and three quarters after {q75}. The most
        recent twelve months alone account for {last12}% of the corpus.
      </div>
    </div>
{figures}
  </section>

  <section>
    <div class="prose">
      <h2>Why the back catalogue thins out</h2>
      <p>Archive depth is wildly uneven. Of {shows} shows, {reach1} reach back at least a
        year, {reach3} at least three, {reach5} at least five, and only {reach10} a full
        decade. {current} shows were still publishing in the final month; {stale} have been
        silent for six months or more.</p>
      <p>That could mean two very different things. Either the panel is young — these are
        the shows charting <em>now</em>, and most of them are recent — or the shows existed
        and their feeds have quietly dropped the old episodes. The first is a sampling
        property to design around. The second is silent data loss.</p>
      <p><strong>It is overwhelmingly the first.</strong> The test is episode numbering: a
        feed whose oldest surviving episode is numbered 1 reaches the show's launch by
        construction. Where numbering is unusable, an iTunes <code>episode</code> tag of 1,
        a trailer-typed entry, or launch language in the earliest titles does the same job.</p>
      <div class="callout">
        <strong>{complete} of {shows} shows ({complete_pct}%)</strong> have positive
        evidence their feed reaches their first episode. Only <strong>{truncated}
        ({truncated_pct}%)</strong> are demonstrably truncated. The remaining
        {unverified} ({unverified_pct}%) leave no machine-readable trace either way.
      </div>
      <p>In January 2015, {snap_absent} of the {shows} shows are absent from the corpus.
        Just {snap_truncated} of those are absent because of a truncated feed. Even under
        the adversarial assumption that <em>every</em> unverified show is secretly
        truncated, missing data explains at most {snap_max}% of the absence — and the
        honest reading is nearer the {snap_min}% floor.</p>
    </div>
{attribution_figures}
    <div class="prose">
      <h3>Checking that against the world</h3>
      <p>The classification is built entirely from feed-internal evidence, so it could be
        confidently wrong. These are its first-observed dates against independently
        published launch dates — {agree} of {checked} agree, several to the day.</p>
    </div>
    <div class="table-wrap">
      <table class="checks">
        <thead><tr><th>Show</th><th>First observed</th><th>Published launch</th>
          <th>Result</th><th>Classifier</th></tr></thead>
        <tbody>
{checks}
        </tbody>
      </table>
    </div>
    <div class="prose">
      <p>The two mismatches are instructive. <em>This American Life</em> is the method
        working: flagged as truncated, and its feed really does keep only about ten weeks.
        <em>The Bill Simmons Podcast</em> is its blind spot — the feed is complete back to
        its own 2015 start, but the show began in 2007 as <em>The B.S. Report</em> on a
        different feed. No feed-internal evidence can see a rebrand, so shows that migrated
        feeds will always look younger than they are.</p>
      <p>Most reassuring: of the shows marked unverified, five of the six checked
        externally turned out to have complete archives matching their published launch
        date. That bucket is mostly shows that do not announce themselves in a parseable
        way, not shows hiding a truncated archive.</p>
    </div>
  </section>

  <section>
    <div class="prose">
      <h2>Where the data will bite</h2>
    </div>
    <div class="prose">
      <ul class="notes">
        <li><strong>{undated} episodes carry a 1970 timestamp</strong> from a feed with no
          usable <code>pubDate</code>. They are excluded from every series here, and should
          be excluded downstream too.</li>
        <li><strong>{dupes} rows are the same episode twice</strong> &mdash; identical show,
          timestamp and title, but distinct GUIDs, so the pipeline's uniqueness constraint
          did not catch them. A further {batched} rows share a timestamp but differ in
          title; those are legitimate batch drops.</li>
        <li><strong>The panel grows.</strong> {joiners} shows first appear after June 2026,
          which is part of why weekly volume steps up in July. Panel membership follows the
          charts, so it is not fixed over the live window either.</li>
        <li><strong>Transcripts are not the constraint on time coverage.</strong>
          {rss} episodes came with publisher transcripts and the rest are ASR output, but
          the combined share is flat across eras.</li>
        <li><strong>{gap_suspects} shows have a hole in the live window</strong> far larger
          than their own publication interval. Live capture is broadly healthy — the median
          show's rate changed {live_rate} between the year before collection and the live
          window — but a short-retention feed loses anything published between discovery
          runs, permanently. <em>This American Life</em> is the clear case: the corpus holds
          episodes 862&ndash;870 and 887&ndash;895 and nothing in between.</li>
      </ul>
    </div>
    <div class="callout caution">
      <strong>The final month is always partial.</strong> The snapshot cuts off mid-month and
      transcription lags ingestion, so the last bar of every series here is an artefact.
      Drop it before reporting a trend.
    </div>
  </section>

  <section>
    <div class="prose">
      <h2>How to use this corpus</h2>
    </div>
    <ol class="takeaways">
{takeaways}
    </ol>
  </section>

  <footer>
    Reproduce with <code>python analysis/temporal_coverage.py</code>.
    Figures, <code>monthly_coverage.csv</code>, <code>podcast_spans.csv</code> and
    <code>summary.json</code> are written to
    <code>analysis/output/temporal-coverage/</code>.
  </footer>
</div>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    summary = json.loads((args.output_dir / "summary.json").read_text())
    attribution = json.loads((args.output_dir / "attribution_summary.json").read_text())
    validation = read_csv(args.output_dir / "external_launch_checks.csv")
    target = args.output_dir / "coverage_memo.html"
    target.write_text(render(summary, attribution, validation, args.output_dir))
    print(f"wrote {target} ({target.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
