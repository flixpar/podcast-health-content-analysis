#!/usr/bin/env python3
"""Render vaccine-tagging outputs as a self-contained internal HTML memo."""

from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vaccine_tagging import (
    DEFAULT_MANIFEST,
    DEFAULT_OUTPUT,
    format_time,
    load_manifest,
    matched_excerpt,
    read_jsonl,
    select_diverse_clips,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--example-count", type=int, default=12)
    return parser.parse_args()


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def num(value: int | float) -> str:
    return f"{value:,}"


def pct(part: int | float, whole: int | float, digits: int = 1) -> str:
    return f"{100 * part / whole:.{digits}f}%" if whole else "—"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def distribution(counter: Counter[str], denominator: int, multi: bool = False) -> str:
    maximum = max(counter.values(), default=1)
    rows = "".join(
        "<tr>"
        f"<td>{esc(label.replace('_', ' '))}</td>"
        f"<td class='n'>{num(count)}</td><td class='n'>{pct(count, denominator)}</td>"
        f"<td class='barcell'><span class='bar' style='width:{100 * count / maximum:.1f}%'></span></td>"
        "</tr>"
        for label, count in counter.most_common()
    )
    note = "<p class='note'>Multi-label field; percentages sum to more than 100%.</p>" if multi else ""
    return (
        "<table><thead><tr><th>Label</th><th class='n'>Clips</th><th class='n'>Share</th>"
        "<th aria-label='relative frequency'></th></tr></thead><tbody>"
        + rows
        + "</tbody></table>"
        + note
    )


def badges(row: dict[str, Any]) -> str:
    labels = [row.get("stance"), *row.get("topics", [])]
    if row.get("potential_misinformation"):
        labels.append("potential-misinformation review flag")
    if row.get("corrective_context"):
        labels.append("corrective context")
    if row.get("politicized"):
        labels.append("politicized")
    return " ".join(f"<span class='badge'>{esc(label)}</span>" for label in labels if label)


def main() -> None:
    args = parse_args()
    out = args.output_dir
    html_path = args.html or out / "analysis_document.html"
    scan = json.loads((out / "scan_summary.json").read_text(encoding="utf-8"))
    tagging = json.loads((out / "tagging_summary.json").read_text(encoding="utf-8"))
    tags = read_jsonl(out / "clip_tags.jsonl")
    shows = read_csv(out / "podcast_summary.csv")
    episodes = read_csv(out / "episodes.csv")
    manifest, batch = load_manifest(args.manifest)

    relevant = [row for row in tags if row.get("relevant")]
    promotions = [
        row
        for row in relevant
        if row["content_type"] == "advertisement_or_psa"
        and row["notable_score"] <= 2
        and not row["potential_misinformation"]
        and not row["corrective_context"]
    ]
    promotion_ids = {row["candidate_id"] for row in promotions}
    clips = [row for row in relevant if row["candidate_id"] not in promotion_ids]
    clip_episode_count = len({row["episode_id"] for row in clips})
    content_types = Counter(row["content_type"] for row in clips)
    stances = Counter(row["stance"] for row in clips)
    topics = Counter(topic for row in clips for topic in row["topics"])
    flagged = [row for row in clips if row["potential_misinformation"]]
    corrective = [row for row in clips if row["corrective_context"]]
    both = [row for row in clips if row["potential_misinformation"] and row["corrective_context"]]
    advice = [row for row in clips if row["personal_medical_advice"]]
    politicized = [row for row in clips if row["politicized"]]
    top_five_clips = sum(int(row["analysis_clip_count"]) for row in shows[:5])
    show_index = {row["podcast_title"]: row for row in shows}

    def show_value(title: str, field: str) -> int:
        return int(show_index.get(title, {}).get(field, 0))

    def show_share(title: str) -> str:
        return pct(show_value(title, "analysis_episode_count"), show_value(title, "corpus_episode_count"))

    corpus = list(manifest.values())
    hours = sum(float(row.get("duration_seconds") or 0) for row in corpus) / 3600
    show_count = len({row.get("podcast_title") for row in corpus})
    dates = [row["published_date"] for row in corpus if row.get("published_date")]
    failure_path = out / "tagging_failures.jsonl"
    failures = read_jsonl(failure_path) if failure_path.exists() else []
    complete = len(tags) == int(scan["candidate_clips"]) and not failures
    status = "Complete preliminary pass" if complete else "Partial preliminary pass"
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    concentrated = sorted(
        episodes,
        key=lambda row: (-int(row["relevant_clip_count"]), -int(row["max_notable_score"])),
    )[:15]
    episode_table = "".join(
        "<tr>"
        f"<td class='n'>{esc(row['relevant_clip_count'])}</td>"
        f"<td>{esc(row['podcast_title'])}</td><td>{esc(row['episode_title'])}</td>"
        f"<td>{'yes' if row['potential_misinformation'] == 'True' else ''}</td>"
        f"<td>{'yes' if row['corrective_context'] == 'True' else ''}</td></tr>"
        for row in concentrated
    )
    show_table = "".join(
        "<tr>"
        f"<td>{esc(row['podcast_title'])}</td>"
        f"<td class='n'>{esc(row['corpus_episode_count'])}</td>"
        f"<td class='n'>{esc(row['corpus_duration_hours'])}</td>"
        f"<td class='n'>{esc(row['candidate_episode_count'])}</td>"
        f"<td class='n'>{esc(row['analysis_episode_count'])}</td>"
        f"<td class='n'>{pct(int(row['analysis_episode_count']), int(row['corpus_episode_count']))}</td>"
        f"<td class='n'>{esc(row['analysis_clip_count'])}</td>"
        f"<td class='n'>{esc(row['routine_promotional_clip_count'])}</td>"
        f"<td class='n'>{esc(row['potential_misinformation_flag_count'])}</td>"
        f"<td class='n'>{esc(row['corrective_context_clip_count'])}</td></tr>"
        for row in shows
    )

    examples = []
    for index, row in enumerate(select_diverse_clips(clips, args.example_count), 1):
        examples.append(
            f"""<article class="clip"><h3>{index}. {esc(row.get('podcast_title'))}: {esc(row.get('episode_title'))}</h3>
<p class="meta">Episode {esc(row['episode_id'])}; published {esc((row.get('published_date') or '')[:10])};
estimated {esc(format_time(row.get('clip_start_seconds_estimated')))}–{esc(format_time(row.get('clip_end_seconds_estimated')))};
parent segment {esc(format_time(row.get('segment_start_seconds')))}–{esc(format_time(row.get('segment_end_seconds')))};
notability {esc(row['notable_score'])}/5; model confidence {esc(row['confidence'])}.</p>
<p>{badges(row)}</p><p><strong>Model-generated summary:</strong> {esc(row.get('claim_summary') or row.get('rationale'))}</p>
<blockquote>{esc(matched_excerpt(row))}</blockquote>
<p class="meta">Candidate <code>{esc(row['candidate_id'])}</code>. ASR text; verify against audio before quotation.</p></article>"""
        )

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Preliminary analysis of vaccination-related podcast content</title>
<style>
:root{{--ink:#17212b;--muted:#596675;--line:#d8dee5;--soft:#f4f6f8;--accent:#315b7d}}
*{{box-sizing:border-box}} body{{margin:0;color:var(--ink);font:15px/1.58 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1120px;margin:auto;padding:42px 32px 80px}} h1{{font:600 34px/1.15 Georgia,serif;margin:0 0 10px}}
h2{{font:600 24px/1.25 Georgia,serif;border-bottom:1px solid var(--line);padding-bottom:8px;margin:46px 0 18px}}
h3{{font-size:16px;margin:25px 0 8px}} p{{max-width:84ch}} a{{color:var(--accent)}} .meta,.note,.subtitle{{color:var(--muted)}}
.status,.badge{{display:inline-block;border:1px solid var(--line);background:var(--soft);padding:2px 7px;font-size:12px}}
.summary{{border-left:4px solid var(--accent);background:var(--soft);padding:13px 18px;margin:24px 0}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:20px 0}}
.metric{{border:1px solid var(--line);padding:12px 14px}} .metric strong{{display:block;font-size:23px}} .metric span{{color:var(--muted);font-size:13px}}
nav{{margin:24px 0;padding:11px 15px;border:1px solid var(--line)}} nav a{{margin-right:16px;white-space:nowrap}}
table{{width:100%;border-collapse:collapse;margin:14px 0 6px;font-size:13px}} th,td{{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:7px 8px}}
th{{background:var(--soft);font-weight:600}} .n{{text-align:right;font-variant-numeric:tabular-nums}} .barcell{{width:28%}} .bar{{display:block;height:9px;background:var(--accent);min-width:2px}}
.tablewrap{{overflow-x:auto;border:1px solid var(--line)}} .tablewrap table{{margin:0;min-width:980px}} .badge{{margin:2px 3px 2px 0}}
.clip{{border-top:1px solid var(--line);margin-top:22px;padding-top:2px}} blockquote{{max-width:84ch;margin:10px 0;padding:10px 14px;border-left:3px solid var(--line);background:#fafbfc}}
code{{background:var(--soft);padding:1px 4px}} .warning{{border:1px solid #d9c5a4;background:#fffaf0;padding:12px 16px}} ol.steps>li{{margin-bottom:14px}}
footer{{margin-top:50px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}}
@media print{{main{{max-width:none;padding:15mm}}nav{{display:none}}.clip{{break-inside:avoid}}}}
</style></head><body><main>
<header><h1>Preliminary analysis of vaccination-related podcast content</h1>
<p class="subtitle">Internal exploratory analysis of a batch of automatically transcribed podcasts</p>
<p><span class="status">{esc(status)}</span> &nbsp; Generated {esc(generated)}</p></header>
<nav><a href="#summary">Summary</a><a href="#data">Data</a><a href="#methods">Methods</a><a href="#results">Results</a><a href="#examples">Clips</a><a href="#limitations">Limitations</a></nav>

<section id="summary"><h2>Summary</h2><div class="summary"><p>This analysis used a high-recall lexical screen followed by structured classification with
<code>{esc(tagging['model'])}</code>. Its purpose is to identify episodes and passages for human review. It is not a prevalence estimate, a representative survey of podcasts, or a fact-check.</p></div>
<div class="metrics"><div class="metric"><strong>{num(len(corpus))}</strong><span>corpus episodes</span></div>
<div class="metric"><strong>{num(round(hours))}</strong><span>metadata hours</span></div><div class="metric"><strong>{num(scan['candidate_clips'])}</strong><span>candidate clips</span></div>
<div class="metric"><strong>{num(len(clips))}</strong><span>analysis-oriented clips</span></div><div class="metric"><strong>{num(clip_episode_count)}</strong><span>episodes retained</span></div>
<div class="metric"><strong>{num(len(flagged))}</strong><span>potential-misinformation review flags</span></div></div>
<p>The queue contains several distinct forms of content: long-form skeptical or critical conversations; policy and political reporting that quotes contested claims; corrective coverage; personal decisions and anecdotes; and repeated advertising. These forms should be analyzed separately.</p></section>

<section id="data"><h2>1. Data</h2>
<p>The source was batch <code>{esc(batch.get('batch_id'))}</code>, created {esc(batch.get('created_at'))}. The manifest contains {num(len(corpus))} episodes from {num(show_count)} podcast titles and {num(round(hours))} hours by episode metadata. Publication dates range from {esc(min(dates)[:10])} through {esc(max(dates)[:10])}. The manifest describes selection as <code>{esc(batch.get('selection_order'))}</code> until approximately {num(round(batch.get('audio_bytes',0)/1e9))} GB was reached.</p>
<p>The analysis read the canonical recovered transcript directory recorded in <code>scan_summary.json</code>. Transcripts were produced with <code>Qwen/Qwen3-ASR-1.7B</code> as compressed JSON Lines. Files contain a full-episode summary and timestamped segments of approximately ten minutes with five seconds of overlap. Only timestamped segment records were searched; summaries were excluded because they duplicate content and lack passage locations.</p>
<p class="warning"><strong>Sampling implication.</strong> This is a constructed batch of 65 titles, not a probability sample of podcasting. Show duration, release frequency, advertising, and batch inclusion affect counts. Show comparisons are descriptive and should use the denominators below.</p></section>

<section id="methods"><h2>2. Methods</h2><ol class="steps">
<li><strong>Inventory and join.</strong> Transcript episode IDs were joined to podcast, episode, date, duration, and archive metadata. Validation and quarantine directories were excluded to avoid duplicated episodes.</li>
<li><strong>High-recall retrieval.</strong> Each ASR segment was searched case-insensitively for vaccine, vaccination, vaccinated, vax and anti-vax variants; immunize and immunization variants; mRNA, VAERS, Gardasil, myocarditis, and pericarditis; disease-qualified shot, jab, and booster phrases; and herd immunity, vaccine passport, and medical exemption. Generic uses of <em>shot</em>, <em>jab</em>, and <em>booster</em> were insufficient. Matches within 2,400 characters were merged, retaining at most 1,800 characters on each side.</li>
<li><strong>Passage location.</strong> Because ASR times apply to ten-minute segments rather than words, clip times were estimated by linear character position within a segment. Exact parent-segment boundaries were also retained and are the reliable location for returning to audio.</li>
<li><strong>Structured model coding.</strong> Candidate windows were sent in batches of 12 at temperature 0 to <code>{esc(tagging['model'])}</code> on local vLLM, using 48 concurrent requests and a strict JSON schema. Required fields were relevance, confidence, content type, apparent stance, topics, claim type, a short neutral summary, review flags, and a 1–5 notability score. The prompt barred outside fact retrieval and defined potential misinformation as triage, not a truth judgment.</li>
<li><strong>Promotional rule.</strong> Vaccine-focused advertisements remained relevant in the raw tags. The brief set aside a clip as routine promotion only if it was labeled <code>advertisement_or_psa</code>, scored 1 or 2, and had neither a potential-misinformation nor corrective-context flag. All such records remain in <code>clip_tags.jsonl</code>.</li>
<li><strong>Aggregation.</strong> Remaining clips were counted by episode, show, stance, content type, topic, and flag. Topics are not mutually exclusive. Counts describe retrieved/model-coded passages, not statistically estimated incidence.</li></ol>
<h3>Principal label definitions</h3><dl>
<dt><strong>Relevance</strong></dt><dd>Vaccination is the focus of at least one meaningful sentence, including vaccine-focused promotion.</dd>
<dt><strong>Stance</strong></dt><dd>The apparent stance of speech in the excerpt, not the model's view.</dd>
<dt><strong>Potential misinformation</strong></dt><dd>A check-worthy assertion questioning safety or efficacy, alleging concealment or conspiracy, or making a strongly misleading-sounding causal claim. It is not validation that a statement is false.</dd>
<dt><strong>Corrective context</strong></dt><dd>The excerpt challenges, contextualizes, or rebuts a vaccine-related misconception or contested claim.</dd>
<dt><strong>Notability</strong></dt><dd>1 (incidental or poor quality) through 5 (specific, consequential, unusual, or particularly useful for review).</dd></dl></section>

<section id="results"><h2>3. Results</h2><h3>Retrieval and filtering</h3>
<p>The lexical pass searched {num(scan['episodes_scanned'])} transcripts and retrieved {num(scan['candidate_clips'])} candidates from {num(scan['episodes_with_candidates'])} episodes ({pct(scan['episodes_with_candidates'],scan['episodes_scanned'])}). Qwen retained {num(len(relevant))} clips as relevant. The reporting rule set aside {num(len(promotions))} routine promotions, leaving {num(len(clips))} analysis-oriented clips in {num(clip_episode_count)} episodes ({pct(clip_episode_count,len(corpus))} of corpus episodes). This last percentage is procedural and descriptive, not a corrected prevalence estimate.</p>
<h3>Content type</h3>{distribution(content_types,len(clips))}<p class="note">A window can contain an ad and later discussion, making content type less reliable than summaries and review flags.</p>
<h3>Interpretive observations</h3>
<ol>
<li><strong>Retrieved content is concentrated by show.</strong> The five titles with the most analysis clips account for {num(top_five_clips)} of {num(len(clips))} clips ({pct(top_five_clips,len(clips))}). This partly reflects corpus hours and release volume, but concentration is also visible using episode denominators. For example, the procedure retained clips from {show_share('The Joe Rogan Experience')} of Joe Rogan episodes and {show_share('The Tucker Carlson Show')} of Tucker Carlson episodes, compared with {show_share('Up First from NPR')} of <em>Up First</em> episodes.</li>
<li><strong>COVID-19 is the dominant vaccine context.</strong> It appears on {num(topics['covid19'])} clips ({pct(topics['covid19'],len(clips))}). Institutional trust or conspiracy framing appears on {num(topics['conspiracy_or_institutional_trust'])} ({pct(topics['conspiracy_or_institutional_trust'],len(clips))}), safety or side effects on {num(topics['safety_or_side_effects'])} ({pct(topics['safety_or_side_effects'],len(clips))}), and mandates or policy on {num(topics['mandates_or_policy'])} ({pct(topics['mandates_or_policy'],len(clips))}). These labels overlap.</li>
<li><strong>Critical claims and corrective coverage occupy different show-level patterns.</strong> The model assigned {num(show_value('The Joe Rogan Experience','potential_misinformation_flag_count'))} potential-misinformation review flags and {num(show_value('The Joe Rogan Experience','corrective_context_clip_count'))} corrective clips to Joe Rogan; the corresponding counts were {num(show_value('REAL AF with Andy Frisella','potential_misinformation_flag_count'))} and {num(show_value('REAL AF with Andy Frisella','corrective_context_clip_count'))} for <em>REAL AF</em>. By contrast, <em>Pod Save America</em> had {num(show_value('Pod Save America','potential_misinformation_flag_count'))} flagged clips and {num(show_value('Pod Save America','corrective_context_clip_count'))} corrective clips; <em>The MeidasTouch Podcast</em> had {num(show_value('The MeidasTouch Podcast','potential_misinformation_flag_count'))} and {num(show_value('The MeidasTouch Podcast','corrective_context_clip_count'))}. These are model-coded review categories, not verified truth or endorsement measures.</li>
<li><strong>Advertising is a material retrieval confound.</strong> The post-processing rule set aside {num(len(promotions))} routine promotional clips. In <em>Crime Junkie</em>, {num(show_value('Crime Junkie','candidate_episode_count'))} episodes produced candidates, while {num(show_value('Crime Junkie','routine_promotional_clip_count'))} clips were classified as routine promotion and only {num(show_value('Crime Junkie','analysis_clip_count'))} remained analysis-oriented. This demonstrates why unfiltered keyword-hit rates would be misleading.</li>
<li><strong>Some episodes contain sustained rather than incidental discussion.</strong> The leading episodes yield 20–32 retained windows, especially long-form interviews. Adjacent windows are not independent, but they identify episodes where full-episode qualitative review is likely more efficient than isolated-clip review.</li>
</ol>
<h3>Apparent stance</h3>{distribution(stances,len(clips))}
<p class="warning"><strong>Do not interpret this as a pro-/anti-vaccination distribution.</strong> In spot checks, the model sometimes used <em>supportive</em> to mean support for the speaker's skeptical argument, although the prompt defined stance relative to vaccination. The absence of any <em>hesitant</em> or <em>unclear</em> labels is another warning sign. Stance requires human recoding before substantive use.</p>
<h3>Topics</h3>{distribution(topics,len(clips),True)}
<h3>Review flags</h3><table><thead><tr><th>Flag</th><th class="n">Clips</th><th class="n">Share</th></tr></thead><tbody>
<tr><td>Potential-misinformation triage</td><td class="n">{num(len(flagged))}</td><td class="n">{pct(len(flagged),len(clips))}</td></tr>
<tr><td>Corrective context</td><td class="n">{num(len(corrective))}</td><td class="n">{pct(len(corrective),len(clips))}</td></tr>
<tr><td>Both fields</td><td class="n">{num(len(both))}</td><td class="n">{pct(len(both),len(clips))}</td></tr>
<tr><td>Personal medical advice</td><td class="n">{num(len(advice))}</td><td class="n">{pct(len(advice),len(clips))}</td></tr>
<tr><td>Politicized</td><td class="n">{num(len(politicized))}</td><td class="n">{pct(len(politicized),len(clips))}</td></tr></tbody></table>
<p>Potential-misinformation and corrective-context fields can coexist when a passage quotes a contested claim before challenging it. A flag therefore cannot be read as episode-level endorsement.</p>
<h3>Episodes with the most retained clips</h3><table><thead><tr><th class="n">Clips</th><th>Podcast</th><th>Episode</th><th>Potential-misinfo</th><th>Corrective</th></tr></thead><tbody>{episode_table}</tbody></table>
<p class="note">Adjacent windows may represent one continuous conversation. Clip count is a review-priority measure, not an independent-event count.</p>
<h3>Show-level descriptive table</h3><div class="tablewrap"><table><thead><tr><th>Podcast</th><th class="n">Corpus episodes</th><th class="n">Hours</th><th class="n">Candidate episodes</th><th class="n">Analysis episodes</th><th class="n">Analysis share</th><th class="n">Analysis clips</th><th class="n">Routine promos</th><th class="n">Potential-misinfo flags</th><th class="n">Corrective clips</th></tr></thead><tbody>{show_table}</tbody></table></div>
<p class="note">Ordered by analysis-clip count. Shares are unadjusted for episode length, date, guest mix, or repeated material.</p></section>

<section id="examples"><h2>4. Selected clips for human review</h2><p>Examples are selected by model notability and confidence, allowing no more than one per episode and two per podcast for breadth. They are not random. The full score-sorted queue is <code>review_queue.csv</code>.</p>{''.join(examples)}</section>

<section id="limitations"><h2>5. Limitations</h2><ul>
<li><strong>Corpus selection:</strong> the titles are not representative of all podcasts, audiences, genres, or dates.</li>
<li><strong>Retrieval recall:</strong> lexical search misses euphemistic discussion and retrieves some unrelated or garbled passages.</li>
<li><strong>ASR:</strong> names, numbers, technical terms, negation, and speaker turns may be wrong. There is no diarization.</li>
<li><strong>Timestamps:</strong> clip times are character-based estimates within ten-minute segments.</li>
<li><strong>Model error:</strong> all labels came from one model and prompt without a human-coded validation set. Confidence is not a calibrated probability.</li>
<li><strong>Stance polarity:</strong> diagnostic spot checks found inconsistent reference points for <em>supportive</em> and <em>critical</em>. The stance field should not be used analytically until human recoding or a validated rerun.</li>
<li><strong>No fact-checking:</strong> the potential-misinformation field does not establish falsity, harm, intent, or endorsement.</li>
<li><strong>Context mixing:</strong> a window can contain advertising, setup, quotation, rebuttal, and multiple speakers.</li>
<li><strong>Non-independence:</strong> repeated ads, previews, syndicated material, and adjacent windows inflate clip counts.</li>
<li><strong>Exploratory decisions:</strong> lexicon, window, taxonomy, and filtering rules were selected rapidly and not preregistered.</li></ul>
<h2>6. Recommended next steps</h2><ol>
<li>Draw a stratified validation sample including retained clips, model rejections, routine promotions, stances, and flag combinations.</li>
<li>Use two independent human coders for relevance, speaker role, stance, claim boundaries, endorsement versus quotation, and need for fact-checking; report agreement.</li>
<li>Verify high-priority passages against audio and wider context before quotation or circulation.</li>
<li>Deduplicate recurring ads and syndicated excerpts, and merge adjacent clips belonging to one discussion.</li>
<li>Review a random sample of unmatched segments to estimate lexical miss rate; compare with semantic retrieval.</li>
<li>Revise the taxonomy and prompt using validation errors, rerun, and report uncertainty rather than treating tags as ground truth.</li></ol></section>

<section><h2>7. Reproducibility and files</h2><ul>
<li><code>vaccine_tagging.py</code>: retrieval, structured tagging, and aggregation.</li><li><code>candidates.jsonl</code>: lexical candidates with metadata, text, terms, and times.</li>
<li><code>clip_tags.jsonl</code>: candidates plus model labels and model ID.</li><li><code>review_queue.csv</code>: score-sorted human-review queue.</li>
<li><code>episodes.csv</code> and <code>podcast_summary.csv</code>: episode and show aggregations.</li><li>JSON summaries and <code>tagging_failures.jsonl</code>: run audit trail.</li></ul>
<pre><code>python analysis/vaccine_tagging.py scan
python analysis/vaccine_tagging.py tag --batch-size 12 --concurrency 48
python analysis/vaccine_tagging.py report
python analysis/render_vaccine_html.py</code></pre></section>
<footer>Internal exploratory document. {esc(status)}. Generated {esc(generated)}.</footer></main></body></html>"""

    html_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = html_path.with_suffix(html_path.suffix + ".tmp")
    temporary.write_text(document, encoding="utf-8")
    temporary.replace(html_path)
    print(json.dumps({"html": str(html_path), "status": status, "tagged": len(tags), "analysis_clips": len(clips)}, indent=2))


if __name__ == "__main__":
    main()
