#!/usr/bin/env python3
"""Create a copy of the HTML memo with an integrated research agenda appended."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from vaccine_tagging import DEFAULT_MANIFEST, DEFAULT_OUTPUT, load_manifest, read_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_OUTPUT / "analysis_document.html",
        help="Existing HTML memo; it is never modified.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT / "analysis_document_with_research_agenda.html",
    )
    parser.add_argument("--tags", type=Path, default=DEFAULT_OUTPUT / "clip_tags.jsonl")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pitch", type=Path, default=Path("project-pitch.md"))
    return parser.parse_args()


def number(value: int | float) -> str:
    return f"{value:,}"


def percent(part: int | float, whole: int | float) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "—"


def main() -> None:
    args = parse_args()
    base = args.input.read_text(encoding="utf-8")
    if 'id="research-agenda"' in base:
        raise SystemExit("input already contains the research-agenda section")
    if not args.pitch.exists():
        raise SystemExit(f"project pitch not found: {args.pitch}")

    tags = read_jsonl(args.tags)
    manifest, _ = load_manifest(args.manifest)
    relevant = [row for row in tags if row.get("relevant")]
    promotions = {
        row["candidate_id"]
        for row in relevant
        if row["content_type"] == "advertisement_or_psa"
        and row["notable_score"] <= 2
        and not row["potential_misinformation"]
        and not row["corrective_context"]
    }
    clips = [row for row in relevant if row["candidate_id"] not in promotions]
    episode_count = len({row["episode_id"] for row in clips})
    topics = Counter(topic for row in clips for topic in row["topics"])
    show_counts = Counter(row.get("podcast_title") or "(unknown)" for row in clips)
    top_five_count = sum(count for _, count in show_counts.most_common(5))

    corpus_by_year: dict[str, list[dict]] = defaultdict(list)
    clips_by_year: Counter[str] = Counter()
    for episode in manifest.values():
        corpus_by_year[(episode.get("published_date") or "unknown")[:4]].append(episode)
    for row in clips:
        clips_by_year[(row.get("published_date") or "unknown")[:4]] += 1

    def rate_per_100_hours(year: str) -> float:
        hours = sum(float(row.get("duration_seconds") or 0) for row in corpus_by_year[year]) / 3600
        return 100 * clips_by_year[year] / hours if hours else 0

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    agenda = f"""
<section id="research-agenda">
<h2>8. Integrated research agenda</h2>
<p class="subtitle">Added {generated}. This section combines lessons from the vaccination pilot with the broader questions in <code>project-pitch.md</code>.</p>

<h3>8.1 Recommended organizing question</h3>
<div class="summary"><p><strong>How do health-misinformation claims move from specific factual assertions into broader narratives about institutional trust and political identity; who produces, circulates, monetizes, and challenges them across the podcast ecosystem?</strong></p></div>
<p>This formulation preserves the pitch's central questions about prevalence, topics, high-impact podcasts, automated detection, monetization, diffusion, and recurring individuals. It also reflects an important lesson from the pilot: podcast misinformation is not one homogeneous content class. The observable process has at least three stages:</p>
<ol>
<li><strong>Production and elaboration:</strong> hosts or guests state, qualify, narrate, or legitimize a claim, often over a long conversation.</li>
<li><strong>Circulation and transformation:</strong> claims recur across guests, shows, advertisements, social media, news, and political events, sometimes changing meaning or scope.</li>
<li><strong>Adjudication:</strong> other speakers quote, question, contextualize, rebut, or fact-check the claim. Quotation is not endorsement, but it may still amplify the underlying narrative.</li>
</ol>

<h3>8.2 What the pilot taught us</h3>
<ul>
<li><strong>The unit of analysis is consequential.</strong> The {number(len(clips))} analysis-oriented clips in {number(episode_count)} episodes are not {number(len(clips))} independent events. Adjacent windows can be one discussion; the same advertisement can recur; and one claim may be quoted and rebutted several times. Future work should distinguish discussion, claim, speech act, speaker, episode, and show.</li>
<li><strong>The material is concentrated.</strong> The five shows with the most retained clips account for {number(top_five_count)} clips ({percent(top_five_count, len(clips))}). Corpus hours and release frequency explain part of this, but recurring high-intensity episodes and guests suggest a meaningful network structure.</li>
<li><strong>Vaccination is often a proxy for institutional conflict.</strong> COVID-19 appears on {number(topics['covid19'])} clips ({percent(topics['covid19'], len(clips))}); institutional-trust or conspiracy framing on {number(topics['conspiracy_or_institutional_trust'])} ({percent(topics['conspiracy_or_institutional_trust'], len(clips))}); safety or side effects on {number(topics['safety_or_side_effects'])} ({percent(topics['safety_or_side_effects'], len(clips))}); and mandates or policy on {number(topics['mandates_or_policy'])} ({percent(topics['mandates_or_policy'], len(clips))}). These overlapping frames connect medical assertions to autonomy, censorship, expertise, government, and pharmaceutical power.</li>
<li><strong>The normalized temporal pattern is consistent with persistence after the acute pandemic.</strong> The retrieval rate rose from {rate_per_100_hours('2019'):.1f} clips per 100 corpus hours in 2019 to {rate_per_100_hours('2021'):.1f} in 2021, then declined to {rate_per_100_hours('2024'):.1f} in 2024 and {rate_per_100_hours('2025'):.1f} in the available 2025 material. This is not yet a causal trend because the composition of shows changes over time, but it motivates studying whether acute COVID discourse became durable institutional distrust.</li>
<li><strong>Editorial functions differ.</strong> Long-form skeptical conversations, hybrid debates, corrective news coverage, incidental mentions, public-health promotion, and commercial vaccine-injury marketing should not be collapsed into one count.</li>
<li><strong>Advertising is both a methodological artifact and a research subject.</strong> Repeated flu-shot advertisements inflated lexical retrieval, while some wellness advertisements used alleged vaccine injury to sell products. Monetization should include the content of advertisements, sponsor relationships, subscription models, video-platform revenue, and audience incentives.</li>
<li><strong>LLMs are currently more useful for retrieval than measurement.</strong> Relevance and short claim summaries were useful for triage. Stance polarity was inconsistent, and potential-misinformation flags sometimes covered quoted or rebutted claims. Human validation and a decomposed pipeline are prerequisites for defensible quantitative estimates.</li>
</ul>

<h3>8.3 Research directions, including the project pitch</h3>
<div class="tablewrap"><table><thead><tr><th>Direction</th><th>Research question</th><th>What the pilot contributes</th><th>Additional requirement</th></tr></thead><tbody>
<tr><td>Prevalence and topic distribution</td><td>How much misinformation appears in podcasts, and on which topics?</td><td>A candidate-retrieval pipeline, corpus denominators, and an initial health taxonomy.</td><td>A representative or explicitly bounded sample, validated claim labels, time-weighted units, and uncertainty estimates.</td></tr>
<tr><td>Claim-level detection</td><td>How accurately can misinformation be detected in long-form audio?</td><td>Hard examples involving multiple speakers, quotation, rebuttal, advertisements, and ASR error.</td><td>A gold standard and separate evaluation of relevance, claim extraction, attribution, endorsement, evidence retrieval, and veracity.</td></tr>
<tr><td>Method comparison</td><td>Which approach works best: classifier, zero/few-shot LLM, fine-tuning, retrieval augmentation, or explicit reasoning?</td><td>A realistic evaluation corpus and an operational baseline.</td><td>Locked train/development/test splits; common metrics; cost, latency, and calibration analysis; ablations for transcript context and retrieved evidence.</td></tr>
<tr><td>Claim taxonomy and severity</td><td>Can misinformation be categorized by subject, evidence style, harm, specificity, and level of uncertainty?</td><td>Model summaries and recurring topic combinations that can seed claim-family discovery.</td><td>A human-developed codebook separating factual falsity, unsupported inference, conspiracy allegation, policy disagreement, and personal anecdote.</td></tr>
<tr><td>Origination and diffusion</td><td>Do claims originate on podcasts, and how quickly do they spread between shows and into other media?</td><td>Timestamped episodes, recurring claims, and concentrated long-form discussions.</td><td>Entity resolution, claim matching, publication-time correction, and external news/social/video/search data. “Origin” should mean earliest observed instance, not proven invention.</td></tr>
<tr><td>Fringe-to-mainstream amplification</td><td>How often do claims move from smaller or ideologically concentrated shows into larger or mainstream programs?</td><td>Contrasting claim-intensive, debate, and corrective ecosystems.</td><td>Audience/reach measures, an operational definition of fringe and mainstream, and quotation-versus-endorsement coding.</td></tr>
<tr><td>Communities and super-spreaders</td><td>Are there stable communities of shows, guests, and claims? Are apparent super-spreaders prolific, influential, or merely frequent publishers?</td><td>Strong concentration by episode, show, and recurring guest names.</td><td>A host–guest–show–claim graph, exposure weighting, centrality measures, and sensitivity tests using episode length and output volume.</td></tr>
<tr><td>Host versus guest influence</td><td>Who introduces and endorses recurring narratives?</td><td>Episode titles identify many prominent guests, and concentrated interviews provide a tractable validation set.</td><td>Diarization, speaker identification, quoted-audio detection, and speech-act annotation.</td></tr>
<tr><td>Legitimation strategies</td><td>How are claims introduced—through disclaimers, uncertainty, credentials, studies, anecdotes, numbers, or source citation?</td><td>Long windows preserve rhetorical setup and response.</td><td>A discourse codebook covering hedges, “just asking questions,” source types, appeals to suppressed knowledge, and host alignment.</td></tr>
<tr><td>Monetization</td><td>Does monetization predict the prevalence or type of misinformation?</td><td>Clear examples of both routine vaccine promotion and products marketed through vaccine-injury claims.</td><td>Segment-level sponsor detection, sponsor identity, ad category, subscriptions, platform presence, audience size, and temporal ordering. Associations should not be interpreted causally without design work.</td></tr>
<tr><td>Episode/show predictors</td><td>Which observable factors predict the presence of check-worthy claims?</td><td>Podcast, episode, date, duration, frequency, and content tags.</td><td>Publisher/category/ratings/audience/guest covariates; train/test separation by show and time to prevent leakage.</td></tr>
<tr><td>Early detection</td><td>Can emerging claim clusters be identified before they become widespread?</td><td>Timestamped candidate and claim streams.</td><td>Prospective evaluation, novelty detection, minimum-support rules, and comparison against later cross-show growth. Retrospective discovery alone cannot establish early-warning performance.</td></tr>
<tr><td>Audience effects and “stickiness”</td><td>Are podcast claims more trusted or memorable than comparable social-media claims?</td><td>The corpus identifies realistic stimuli and exposure contexts.</td><td>Survey or experimental data. Content analysis alone cannot establish persuasion, trust, recall, or behavioral effects.</td></tr>
</tbody></table></div>

<h3>8.4 Recommended near-term work packages</h3>
<h4>Work package 1: validation and codebook</h4>
<ol>
<li>Create a stratified set of approximately 400 retrieved passages: potential-flag-only, corrective or mixed, ordinary relevant, advertisements, and model-rejected candidates.</li>
<li>Review approximately 100 unmatched transcript segments to estimate lexical miss rate.</li>
<li>Have two coders label relevance, exact claim span, speaker role, assertion versus quotation, endorsement, correction, topic, evidence style, and whether external fact-checking is warranted.</li>
<li>Report inter-coder agreement and error by show, content type, ASR quality, and context length; revise the codebook before treating model outputs as measurements.</li>
</ol>

<h4>Work package 2: construct defensible units</h4>
<ol>
<li>Merge adjacent windows into continuous discussion units.</li>
<li>Deduplicate repeated advertisements, previews, syndicated audio, and repeated claim formulations.</li>
<li>Estimate vaccine-discussion minutes, share of episode time, number of distinct discussions, and number of distinct claims.</li>
<li>Add host, guest, advertisement, quoted speaker, and unknown speaker roles for a high-priority subset.</li>
</ol>

<h4>Work package 3: benchmark a decomposed detector</h4>
<p>Do not ask one model call to decide everything. Evaluate a sequence: retrieval → claim extraction → speaker attribution → endorsement/quotation/correction → evidence retrieval → factual assessment. Compare simple lexical and supervised baselines with zero-shot, few-shot, fine-tuned, and retrieval-augmented LLM approaches. Use show-held-out and time-held-out tests so that memorizing recurring speakers or claims does not masquerade as generalization.</p>

<h4>Work package 4: claim families and network analysis</h4>
<ol>
<li>Cluster model summaries into roughly 20–40 human-reviewed claim families.</li>
<li>Build a host–guest–show–claim network and examine repeated guests, cross-show movement, and changing claim formulations.</li>
<li>Track claims by corpus hour and episode rather than raw clip count.</li>
<li>Select 25–30 full episodes spanning claim-intensive interviews, debates, corrective coverage, policy events, and commercial messages for qualitative analysis.</li>
</ol>

<h4>Work package 5: expand beyond the current corpus</h4>
<ol>
<li>Define the target population and sampling frame before making prevalence claims.</li>
<li>Add audience and reach measures for exposure-weighted analysis.</li>
<li>Collect sponsor/platform/subscription information for monetization research.</li>
<li>Link claim families to timestamped news, social-media, video, and search sources for diffusion and earliest-observed-instance analysis.</li>
<li>Conduct a formal literature review and verify the pitch's novelty and audience-statistic claims against the linked primary sources before external use.</li>
</ol>

<h3>8.5 Immediate sequence and decisions</h3>
<p><strong>Recommended sequence:</strong> freeze the pilot outputs → define the target population and unit of analysis → write and test the codebook → double-code the validation sample → merge/deduplicate discussions → rerun and calibrate the detector → construct claim families and speaker networks → add external diffusion and monetization data.</p>
<p>The kickoff should decide three matters first:</p>
<ol>
<li><strong>Primary estimand:</strong> prevalence of false claims, amount of exposure time, number of distinct narratives, or structure of diffusion. These are different projects.</li>
<li><strong>Primary unit:</strong> claim, discussion, episode, speaker, show, or listener exposure.</li>
<li><strong>Initial scope:</strong> vaccination as a methodological case study, health misinformation more broadly, or a topic-general podcast misinformation detector.</li>
</ol>

<h3>8.6 Claims that should not yet be made</h3>
<ul>
<li>The current 10.7% episode share is not a population prevalence estimate.</li>
<li>The {number(sum(row['potential_misinformation'] for row in clips))} model flags are not verified instances of misinformation.</li>
<li>Raw show rankings do not measure audience exposure or causal influence.</li>
<li>The current stance labels should not be interpreted as pro- or anti-vaccination.</li>
<li>The earliest podcast occurrence in this corpus would not prove that a claim originated there.</li>
<li>Associations between advertising and content would not, by themselves, show that monetization caused misinformation.</li>
<li>Content analysis alone cannot establish that podcast misinformation is more trusted, persuasive, or “sticky” than social-media misinformation.</li>
</ul>
</section>
"""

    if "</nav>" in base:
        base = base.replace(
            "</nav>",
            '<a href="#research-agenda">Research agenda</a></nav>',
            1,
        )
    insertion = base.find("<footer>")
    if insertion < 0:
        raise SystemExit("could not locate <footer> insertion point")
    combined = base[:insertion] + agenda + "\n" + base[insertion:]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(combined, encoding="utf-8")
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "input_unchanged": str(args.input),
                "output": str(args.output),
                "pitch_considered": str(args.pitch),
                "research_agenda_added": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
