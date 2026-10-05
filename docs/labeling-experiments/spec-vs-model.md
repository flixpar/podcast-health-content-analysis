# Spec or model? Where DeepSeek-vs-gold disagreement comes from

Question: would a much more detailed per-category specification (definitions, keywords, examples,
boundary rules), given to both the candidate and the annotators, raise accuracy and agreement a lot?
Or is most disagreement model noise, differing readings, or ambiguity that no spec can remove? And
would a clearer spec shorten DeepSeek's thinking?

Everything here is read-only on existing runs. Scripts are `docs/labeling-experiments/scripts/sva_*.py` (see the end).

## Bottom line

1. **The candidate was not reading the annotators' spec, and fixing that is the big, proven win.**
   `SYSTEM_RUBRIC` never names the `claim_type` or `product_type` values. They exist only in the
   JSON schema, which is enforced by constrained decoding and is not in the prompt text. Those are
   exactly the two attributes where DeepSeek was near chance: claim_type 0.36 exact against gold
   (DeepSeek's self-agreement 0.39; annotators 0.80), product_type 0.60 (annotators 0.96). The run
   `s70-high-codebook-lenient`, which uses the annotators' `codebook.md` as the rubric (repeat_0, 70
   items), brings claim_type to **0.81** and product_type to **0.96**. It also lifts topic recall from
   0.56 to 0.69 (+0.13, 95% CI [+0.09, +0.18]) and topic F1 by +0.056 [+0.025, +0.086]. Frame and
   evidence do not move (−0.01), claims gain +0.03 F1 (n.s.) and products +0.05 F1 (n.s.).
2. **Beyond that, detections are near the annotators' own ceiling.** With the old rubric DeepSeek
   already agreed with individual annotators about as well as annotators from different model families
   agree with each other: topic 0.62 vs 0.61, frame 0.67 vs 0.65, evidence 0.66 vs 0.61, claims 0.66
   vs 0.61, products 0.74 vs 0.75. 78% of required gold sits in labels where DeepSeek is within 0.05 of
   cross-family agreement. Only 15% sits in labels the annotators themselves disagree on (cross-family
   F1 < 0.55), and only 6% in labels where DeepSeek differs consistently from annotators who agree.
3. **The residual gap is exhaustiveness and co-labeling, which is partly spec-sensitive.** Topic atoms
   per window: Opus 7.4–7.9, Sonnet 4.0–4.2, DeepSeek 5.1 (dev); on the s70 windows DeepSeek goes from 4.8 to 6.7 with the codebook.
   DeepSeek matches unanimous (4/4) topic gold 83% of the time and Opus-pair-only gold 30% of the time;
   46% of its detection misses are atoms only the two Opus passes found. Both Claude families had the
   same codebook, so the text alone does not produce Opus-level exhaustiveness. Under the codebook,
   22% of topic gold is still missed by co-labeling (DeepSeek puts one of two gold labels on a span),
   against 25% before.
4. **Sampled errors (60, weighted by error volume):** 33% spec gap (3% were rubric omissions), 35% model
   did not follow a clear spec (25% stochastic, 10% systematic), 19% matching or span artifact, 8% gold
   debatable, 5% genuine subjectivity. A better spec addresses roughly a third of the errors.
5. **Thinking length is set by how much there is to label, not by ambiguity.** Reasoning tokens
   correlate 0.89 with gold atom count (log–log R² 0.88). Annotator disagreement adds nothing (partial
   ρ −0.17). DeepSeek's own instability adds 3–10%. The 13k-character codebook rubric produced the
   same mean thinking as the old rubric (18.9k vs 19.1k tokens) while emitting more atoms. Budget runs
   show thinking is not wasted: an 8k cap costs 0.09–0.10. A clearer spec will not buy throughput.
6. **Recommendation.** Adopt the codebook as the rubric; it needs no re-annotation because it is the
   text the gold was built from. Confirm with repeat_1 and the full dev set. Then add a short,
   gold-checked set of co-label and boundary rules (co-label upper bound: topic F1 +0.06). A full
   per-category rewrite is unlikely to be worth it: most remaining detection disagreement is threshold,
   noise and span granularity, not definitions. Realistic topic F1 is about 0.74–0.78, not the 0.87
   exhaustive-annotator ceiling.

## Data and method

- Decomposition items: 151 dev corpus windows (headline strata plus rare_label) labeled by
  `dev-high-chat-lenient`, all with the old `SYSTEM_RUBRIC`. DeepSeek samples: its 2 repeats, plus 6
  more (three s70 runs × 2 repeats) on the 66 s70 corpus items. Pair statistics are averaged within an
  item before pooling.
- (a) Annotator agreement: pairwise F1 with the scoring matcher, split into Opus–Opus, Sonnet–Sonnet
  and cross-family. Cross-family is the fairest measure of spec ambiguity, because same-family pairs
  share model habits.
- (b) DeepSeek self-agreement: the same pairwise F1 between samples. (c) DeepSeek vs gold uses
  `score_item`; DeepSeek vs each annotator is like for like with (a).
- Per required gold atom, p = the share of samples matching it. The miss rate E[1−p] splits into a
  stochastic part E[p(1−p)] (unbiased estimate) and a systematic part (the rest).
- Codebook check: `s70-high-codebook-lenient` repeat_0 (repeat_1 was still running, with no manifest)
  against `s70-high-chat-lenient` (same API, 2 repeats), with a paired item bootstrap
  (`sva_codebook_run.py`).

## 1. The candidate prompt was a lossy copy of the codebook

| in `codebook.md` (annotators) | in `SYSTEM_RUBRIC` | old rubric | codebook as rubric | annotators |
| --- | --- | --- | --- | --- |
| seven `claim_type` values defined; "by what the claim asserts, not the subject" | "claim_type -- the kind of proposition being asserted." (no values named) | 0.36 | **0.81** | 0.80–0.86 |
| full `product_type` list | "the kind of offering; other_product only when no listed kind fits" | 0.60 | **0.96** | 0.96–0.99 |
| "Be exhaustive … Under-labeling is as much an error as over-labeling" | absent | topic yield 0.51 | 0.71 | – |
| "Sponsor copy makes checkable claims too … must be extracted" | absent | claim R 0.68 | 0.73 | – |
| `passing` covers jokes and quiz items; own-product pitch is not `advertisement` | shorter | relevance 0.86 | 0.91 | – |

Attribute columns are exact agreement with the gold plurality on matched atoms, s70 corpus items.

The old failure mode was one-directional. On 297 unanimous gold claims DeepSeek said `causal` for
mechanism (20.5), treatment (16.6), other_factual (13.9) and prevalence (12.8). Between its own
repeats it flipped causal↔mechanism 29 times in 169 quote-identical claims. It typed "Tremfya is a
prescription medicine used to treat adults with Crohn's disease" (gold: treatment 4/4) as
`diagnosis_or_prevalence`, and "Beam Dream Sleep Tea has zero added sugar" (gold: mechanism 3/3) as
`institutional_or_conspiracy`. Its old claim_type distribution was 35% causal and 6% other_factual;
under the codebook it is 12% and 25%, close to the annotators' 16% and 16–21%. `other_product` went
from 39% of product mentions to 9% (annotators 6–8%).

Topic, old rubric vs codebook (s70 corpus): topic detections per window 4.3 → 5.6, labels per detection
1.11 → 1.19, precision 0.88 → 0.80, recall 0.56 → 0.69. Among missed required topic gold,
substitutions fell from 5.6% to 1.9% and span-only misses from 9.9% to 5.8%, but co-label misses
stayed at 25% → 22%.

## 2. Decomposing disagreement (old rubric)

### 2.1 By axis

| group | required | ann O–O | ann S–S | ann cross | DS self | DS vs ann | DS P | DS R | DS F1 | miss: systematic | miss: stochastic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| topic | 1054 | 0.81 | 0.71 | 0.61 | 0.70 | 0.62 | 0.84 | 0.55 | 0.66 | 0.33 | 0.12 |
| frame | 400 | 0.84 | 0.71 | 0.65 | 0.73 | 0.67 | 0.87 | 0.66 | 0.75 | 0.23 | 0.12 |
| evidence | 349 | 0.84 | 0.65 | 0.61 | 0.74 | 0.66 | 0.82 | 0.72 | 0.77 | 0.17 | 0.11 |
| claim | 900 | 0.84 | 0.71 | 0.61 | 0.72 | 0.66 | 0.90 | 0.72 | 0.80 | 0.21 | 0.14 |
| product | 193 | 0.91 | 0.90 | 0.75 | 0.83 | 0.74 | 0.84 | 0.82 | 0.83 | 0.14 | 0.08 |

DeepSeek's self-agreement (0.70–0.83) is in the Sonnet–Sonnet range (0.65–0.90). Its agreement with
annotators equals the cross-family figure, so it behaves like a third model family whose labeling
volume sits between Sonnet and Opus. 60–73% of its miss rate is systematic: the same atom is missed
in every sample.

Support pattern of required gold, with DeepSeek's mean match rate in brackets (OO = only the two
Opus passes, OS = one of each family):

| group | 4 of 4 | 3 of 4 | OO | SS | OS |
| --- | --- | --- | --- | --- | --- |
| topic | 374 (0.83) | 280 (0.52) | 309 (0.30) | 13 (0.45) | 78 (0.35) |
| frame | 173 (0.85) | 90 (0.64) | 109 (0.45) | 2 | 26 (0.27) |
| evidence | 122 (0.93) | 97 (0.74) | 105 (0.51) | 2 | 23 (0.64) |
| claim | 333 (0.84) | 214 (0.68) | 289 (0.44) | 10 (0.39) | 54 (0.50) |
| product | 119 (0.94) | 17 (0.85) | 52 (0.42) | 3 | 2 |

### 2.2 Anatomy of misses and false positives

Misses, as a share of required gold × samples:

| group | matched | co-label missing (DS put another *gold* label on the span) | same label, span mismatch | substitution | nothing on that axis | other cross-cutting axis |
| --- | --- | --- | --- | --- | --- | --- |
| topic | 0.55 | **0.23** | 0.09 | 0.08 | 0.05 | – |
| frame | 0.66 | 0.11 | 0.02 | 0.02 | **0.18** | 0.02 |
| evidence | 0.72 | 0.04 | 0.02 | 0.02 | **0.13** | 0.07 |
| claim | 0.65 | – | – | 0.06 (different claim) | **0.29** | – |
| product | 0.78 | – | – | 0.08 (different product) | **0.15** | – |

The scorecard's largest topic error class, `same_axis_wrong_label` (196), is mostly co-labeling rather
than confusion. The most frequent missing co-labels (gold label missed / DeepSeek label present):
public_health_policy / vaccines (6.0); childrens_health / lgbtq (4.6), food (2.9), sleep (2.9);
weight_loss / glp_1 (4.0); optimization_framing / commercialization (3.9); surgery / beauty (3.8);
cardiometabolic / weight_loss (3.5); conflict_of_interest / big_pharma (3.2);
cancer / cancer_alternative (3.0). These are population, policy and intervention topics added on top
of the main subject. The rule "apply both only when the passage genuinely does both" does not settle
them, and Opus (1.36 labels per detection) and Sonnet (1.15) read it differently.

False positives (333 sample-weighted; 11 hit an adjudicated-rejected singleton): topic 63% same label
with a span mismatch (65% of them recur in at least half of the other samples: systematic splitting
differences), 31% wrong label; frame 44% wrong label, 30% span, 19% cross-axis; evidence 39% wrong label,
38% frame↔evidence, 23% span; claims 70% overlap a gold claim but split, merge or quote it differently.

### 2.3 Regimes per label (by required gold volume)

A = cross-family F1, C = DeepSeek vs annotators, S = DeepSeek self; labels with at least 5 required
atoms. Per-label numbers are in `sva_labels.json`.

| regime | rule | labels | required gold | largest members |
| --- | --- | --- | --- | --- |
| R1 spec ambiguous | A < 0.55 | 22 | 415 (15%) | personal_experience_evidence (A 0.49), credential_appeal (0.53), childrens_health (0.48), health_care_system (0.53), optimization_framing (0.49), public_health_policy (0.42), fitness_exercise (0.45), other_health_topic (0.27), purity_contamination (0.34), surgery (0.44) |
| R2 DS at annotator level | C ≥ A − 0.05 | 38 | 2223 (78%) | claims, products, mechanistic language, commercialization, food, study citation, mental health, supplements, sleep |
| R3 systematic DS gap | C < A − 0.05, S ≥ 0.65 | 13 | 169 (6%) | government_institution_distrust (C 0.51 vs A 0.67), conflict_of_interest (0.49 vs 0.63), genetics (0.41 vs 0.61), hearing_vision (0.32 vs 0.61), beauty, gut, big_pharma |
| R4 DS noise | C < A − 0.05, S < 0.65 | 4 | 43 (2%) | peptides (S 0.35), regenerative_aesthetic (0.44), anti_expert_populist (0.40) |

### 2.4 Attributes (exact agreement on matched atoms, old rubric)

| attribute | ann O–O | ann S–S | ann cross | DS self | DS vs ann | DS vs unanimous gold (n) | DS on split gold (vote share) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| claim:claim_type | 0.86 | 0.83 | 0.80 | **0.39** | **0.37** | **0.40** (297) | 0.28 |
| product:product_type | 0.99 | 0.98 | 0.96 | **0.79** | **0.68** | **0.68** (120) | 0.42 |
| claim:expressed_certainty | 0.86 | 0.85 | 0.81 | 0.86 | 0.82 | 0.93 (311) | 0.50 |
| claim:discourse_role | 0.97 | 0.95 | 0.94 | 0.97 | 0.91 | 0.94 (388) | 0.52 |
| detection:discourse_role | 0.95 | 0.92 | 0.92 | 0.93 | 0.90 | 0.95 (751) | 0.50 |
| detection:relevance | 0.94 | 0.91 | 0.91 | 0.90 | 0.90 | 0.94 (744) | 0.55 |
| product:mention_role | 0.96 | 0.89 | 0.90 | 0.93 | 0.91 | 0.99 (104) | 0.58 |

Certainty, discourse role, relevance and mention role were already at ceiling: DeepSeek agrees 93–99%
with unanimous gold and splits where the annotators split. The residual confusions are small:
relevance substantive→passing (31 of 546), discourse role asserted→reported (31 of 720), certainty
unhedged→absolute (8.5 of 248). Codebook-v2 certainty rules would polish these, not transform them.

### 2.5 Upper bounds on top of the old rubric (dev run, 2 repeats, 151 items)

| what-if (perfect uptake, no new false positives) | topic F1 | frame F1 | evidence F1 | product F1 |
| --- | --- | --- | --- | --- |
| now | 0.678 | 0.772 | 0.781 | 0.824 |
| span-only misses and duplicates resolved (splitting rule or many-to-one scoring) | 0.769 | 0.801 | 0.810 | – |
| missing co-labels supported by 3–4 annotators added | 0.742 | 0.797 | 0.792 | – |
| all missing co-labels added (including Opus-only) | 0.833 | 0.835 | 0.807 | – |
| product_type = gold plurality | – | – | – | 0.867 |

## 3. Sixty sampled errors (old rubric)

Sample: `dev-high-chat-lenient` repeat_0, dev corpus items, seeded random, at most two per window.
Each error was read against its transcript, gold members, non-supporting annotators, the codebook and
DeepSeek's other samples (`sva_error_dossiers.txt`; codes with a one-line reason each are in
`sva_error_labels.py`).

| group (misses + FPs) | n | i spec gap | ii not followed | iii gold debatable | iv matching/span | v subjective |
| --- | --- | --- | --- | --- | --- | --- |
| topic (8+6) | 14 | 4 | 3 | 2 | 5 | 0 |
| frame (6+4) | 10 | 3 | 4 | 0 | 1 | 2 |
| evidence (6+4) | 10 | 1 | 4 | 2 | 2 | 1 |
| claim (10+6) | 16 | 5 | 7 | 1 | 2 | 1 |
| product (6+4) | 10 | 3 | 4 | 1 | 2 | 0 |
| **all** | 60 | 16 (27%) | 22 (37%) | 6 (10%) | 12 (20%) | 4 (7%) |
| **weighted by error volume** | | 33% | 35% | 8% | 19% | 5% |

Of the 22 "not followed", 17 are stochastic (the atom was matched in other samples, or the false
positive did not recur) and 5 systematic. Caveat: for the 85 non-s70 windows only one other sample
exists, so "0/1 recurrence" is weak evidence and the stochastic share may be overstated. Of the 16 spec
gaps, 2 are rubric omissions.

**(i) Spec gap.**
- E23, frame FP: "the whole medical profession has been brainwashed into thinking chiropractic's
  dangerous or it's quackery". DeepSeek labeled `misinformation_correction_debunking`, which fits its
  definition ("corrects … a health claim … regardless of whether the correction is itself accurate").
  All four annotators coded `anti_mainstream_medicine_framing` only; across all gold, 1 of 45 required
  anti-mainstream atoms also carries debunking. E21 is the same case ("we've been told forever … that
  UV is bad for the eyes, and in fact …").
- E40, claim miss (rubric omission): Eight Sleep read, "there's no better way to be alert, productive
  and happy than by sleeping well". Three annotators extracted it under the sponsor-copy rule;
  DeepSeek, without the rule, did not (0/2).

**(ii) Clear spec, not followed.**
- E35, systematic (0/2): "when we make enough room for the teeth … they're way less likely to collapse
  in". A plain treatment claim; 3 of 4 annotators extracted it.
- E28, stochastic (6/8): a daughter's genetics anecdote offered as evidence
  (`personal_experience_evidence`); found in six other samples.

**(iii) Gold debatable.**
- E27: "Casey is his brilliant surgeon sister, who is author of this New York Times bestseller" in an
  introduction. Only the Opus pair coded `credential_appeal`, which the definition ties to support for a
  claim.

**(iv) Matching or span artifact.**
- E13: DeepSeek split a substance-use passage where the discourse role changed to `questioned`, as the
  splitting rule says. Gold has one span, so one-to-one matching turns the second detection into a
  false positive.

**(v) Genuine subjectivity.**
- E19: a speaker describes, then dismisses, the "big powerful people … the CDC and this company"
  mindset. Annotators spread across distrust, big-pharma and conspiracy frames.

## 4. Throughput: does ambiguity drive thinking?

Mean reasoning tokens per window (133 windows with gold):

| predictor | Spearman ρ | partial ρ \| gold atom count |
| --- | --- | --- |
| gold atoms / DeepSeek output atoms | +0.89 / +0.90 | – |
| window word count | −0.06 (n.s.) | +0.05 |
| annotator disagreement (1 − mean pairwise F1) | −0.11 (n.s.) | −0.17 (p 0.05) |
| singleton share of gold | +0.22 | +0.01 |
| screening "ambiguity" score | +0.45 | +0.05 |
| DeepSeek self-disagreement | +0.18 | +0.12; +0.30 (p < 0.001) controlling DS output atoms |

- log(reasoning) ~ log(1 + gold atoms) gives R² 0.879. Adding annotator disagreement moves it to 0.884,
  with a negative coefficient. DeepSeek's self-disagreement accounts for +3.5% tokens across its
  interquartile range and +10% from the 10th to the 90th percentile.
- Only 5% of log-variance is within a window (median CV 0.24). Null-content windows use about 250
  tokens; content windows a median of about 24k: ~820 per gold atom, 1,350 per emitted atom, 9.6× the JSON.
- Within a window, samples that think longer score higher (ρ +0.23, p < 10⁻⁶). Budget caps: 8k costs
  0.09–0.10 on frame F1, evidence F1 and claim recall; 4k costs 0.14–0.18; 24k equals unbounded.
- The codebook rubric (13k characters, more specific) produced the same mean thinking as the old
  rubric: 18.9k vs 19.1k tokens on the same 70 windows.

The thinking is per-annotation work, not deliberation over what the categories mean. A clearer spec
does not shorten it. Throughput levers are output-side: fewer or shorter fields per atom, or no
quotes and summaries for low-value atoms.

## 5. Recommendation

**Is a detailed per-category codebook likely to give a significant gain?** The measurable gain came
from making the candidate read the same spec as the annotators. That is already demonstrated:
claim_type 0.36 → 0.81, product_type 0.60 → 0.96, topic F1 +0.056. A further per-category expansion
(longer definitions, keyword lists) targets the 15% of gold in R1 labels and the co-label rule.
Most of what remains is threshold (Opus vs Sonnet volume), run-to-run noise, and span granularity
under one-to-one matching, which definitions do not fix. Label definitions are already specific:
median 23 words and 11 example terms.

| step | expected gain | gold impact |
| --- | --- | --- |
| 1. Make `rubric-codebook-v1.md` the rubric (finish repeat_1; run on the full dev set) | claim_type ≈ annotator level; topic F1 +0.06 (CI +0.03 to +0.09); claims and products +0.03–0.05 (n.s.) | none: it is the text the gold was made from |
| 2. Co-label and boundary rules checked against gold co-occurrence (below) | co-label upper bound: topic F1 +0.06 with 3–4-annotator co-labels; frames +0.02 | none, if every rule matches the existing required tier |
| 3. Splitting rule, or many-to-one span credit in scoring | up to topic F1 +0.09 (upper bound) | scoring change, or a re-cluster |
| 4. Codebook-v2 rules that change codes (certainty "can", composition → other_factual, institutional inaction, topic discourse role, product scope, new Endocrine/Allergy topics) | small for the candidate; raises annotator alpha | re-code those attributes; new benchmark_version if atoms change |
| 5. Two samples per window: union recovers stochastic misses (~25% of errors) at a precision cost; intersection raises precision and cuts recall | recall or precision, not agreement with the spec | none |

**Illustrative spec additions.**
- *Co-label rule (modelled on the Opus passes, whose agreement forms the OO-required gold):* "When a
  passage discusses an intervention for an outcome, label both topics: yoga for sleep →
  `fitness_exercise` + `sleep`; melatonin pills → `functional_nutrition_supplements` + `sleep`; GLP-1s
  for weight → `glp_1_incretin_drugs` + `weight_loss_metabolic_health`. Add a population topic
  (`childrens_health`, `pregnancy_…`) whenever the passage is about that population."
- *Boundary rule (verified: 1 of 45 anti-mainstream gold atoms also carry debunking):* "Debunking
  corrects a claim presented as false or fringe. A speaker who 'corrects' mainstream medical advice
  ('we've been told UV is bad for the eyes, in fact …') is `anti_mainstream_medicine_framing`, not
  debunking."
- *claim_type examples (v1 definitions, gold-consistent):* "Decide by what the proposition asserts:
  causes/worsens → `causal`; helps/treats/prevents → `treatment_or_prevention`; harmful/safe →
  `risk_or_safety`; how common or how recognised → `diagnosis_or_prevalence`; how it works or what it
  contains → `mechanism`. 'Tremfya is a prescription medicine used to treat Crohn's' →
  treatment_or_prevention; 'the tea has zero added sugar' → mechanism."

**Realistic ceiling.** Cross-family annotator agreement (topic 0.61, frame 0.65, evidence 0.61, claims
0.61, products 0.75) is where DeepSeek already was. Opus–Opus (0.81–0.91) is what one consistent
reading achieves. Against gold, a conservative reference scores topic F1 about 0.66 and an exhaustive
one about 0.87. The codebook rubric reaches 0.74 on s70. With gold-checked co-label rules and a
splitting fix, 0.76–0.78 is plausible. Beyond that DeepSeek would need to label like Opus. Precision
already fell from 0.88 to 0.80 as recall rose, so each further push trades precision.

**Does the gold need re-annotation?** Not for steps 1–3. Step 1 is the gold's own text. Rules that
codify the required tier (co-labels Opus agrees on; exclusive anti-mainstream coding) leave the gold
valid. Re-running annotators under a richer spec moves gold in two directions. *Exhaustiveness and
co-label rules* make Sonnet catch up with Opus: OO atoms become 3–4-annotator atoms, required volume
barely changes, the candidate's target is unchanged, and the tiers get firmer. *Threshold-tightening
rules* (minimum content, jokes and idioms excluded, platforms not products; codebook-v2 §3–4) pull Opus
back: fewer atoms become required, candidate recall rises with no candidate change, and the affected
references must be re-run. v2 rules that reverse existing codes (certainty "can", composition as other_factual) need attribute
re-coding.

## Reproduction

From `docs/labeling-experiments/scripts/`: `sva_decompose.py`, `sva_tables.py` (§2.1, 2.2, 2.4), `sva_extra.py`, `sva_regimes.py` (§2.3),
`sva_gains.py` (§2.5), `sva_errors.py` + `sva_error_labels.py` (§3), `sva_throughput.py` (§4), `sva_codebook_run.py` (§1).
