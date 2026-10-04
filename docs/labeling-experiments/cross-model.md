# Cross-model error analysis: dev70, lenient validation, 2 repeats

Scope: `sample-dev70.jsonl`, 7 runs × 2 repeats, scored with `scoring.score_item`. Numbers are **all
70 items, mean per repeat**, matching the brief's baseline (DeepSeek topic F1 .69, frame .76, evidence
.80, claim R .71). Credit gold = required + acceptable (topic 659, frame 254, evidence 200, claim 528,
product 97). Scripts: `docs/labeling-experiments/scripts/xmodel_*.py`.

Data limits: lenient runs log drop *counts* only; the strict `s70-none`/`s70-high` runs keep one
rejection `message` per attempt. Every Gemma truncation has `output_excerpt: null`, because
`topic_labeling.py` checks for truncation (~l.2391) before it extracts text, so §4 relies on usage.

## 1. Headline (strict P / R / F1; atoms predicted per repeat)

| run | topic | frame | evidence | claim | product | det/win | claims/win | dropped | AUROC |
|---|---|---|---|---|---|---|---|---|---|
| DeepSeek high | .83/.59/**.69** (372) | .87/.67/**.76** (154) | .83/.76/**.80** (148) | .89/.71/.79 (352) | .82/.74/.78 (76) | 8.7 | 5.0 | 0% | .62 |
| gpt-oss high | .71/.40/.51 (286) | .81/.21/.33 (50) | .78/.36/.49 (70) | .78/.54/.64 (300) | .57/.63/.59 (92) | 5.7 | 4.3 | 8% | .50 |
| gpt-oss medium | .76/.22/.34 (145) | .85/.11/.19 (24) | .67/.19/.29 (42) | .81/.42/.55 (218) | .62/.46/.53 (60) | 3.0 | 3.1 | 14% | .52 |
| Qwen3.5 think | **.94**/.28/.43 (150) | .65/.29/.40 (85) | .81/.32/.46 (59) | .85/.34/.49 (168) | .64/.61/.62 (80) | 4.1 | 2.4 | 18% | .53 |
| Qwen3.5 none | .73/.18/.29 (123) | .51/.05/.10 (20) | .39/.05/.09 (19) | .84/.20/.32 (96) | .47/.38/.42 (66) | 1.9 (med 0.5) | 1.4 | **36%** | .47 |
| Gemma 4 think* | .84/.50/.62 (300) | .67/.28/.39 (76) | .76/.31/.44 (58) | .85/.49/.62 (230) | .72/.62/.66 (68) | 6.2 | 3.4 | 8% | .54 |
| DeepSeek none | .66/.46/.54 (368) | .52/.28/.37 (105) | .61/.23/.33 (56) | .80/.42/.55 (218) | .53/.63/.58 (98) | 7.4 | 3.1 | 13% | .53 |

"dropped" = annotations removed by lenient validation ÷ (kept + dropped). Gold carries 15.9 credit
detection atoms per window. *Gemma's pool leaves out its 5 unresolved window-repeats (104 + 15
required atoms). Counted as misses, its recall falls to topic .48, frame .26, evidence .29, claim .47.

**The gap is recall, not precision.** Precision stays at .65–.94 on most axes while frame and
evidence recall drops to .05–.36: all six under-call. DS-none also loses precision (topic .66, frame .52).

## 2. Why frames and evidence collapse

Not wrong content, and not frames filed as topics. **The models cover the passage with a topic
detection and skip the cross-cutting layer on top.**

| run | frame atoms / 254 | windows with frame gold but 0 frame preds | frame misses: cross_axis / nothing / wrong label | evidence misses: cross_axis / nothing / wrong label | frame R, consensus atoms (n=121) | evidence R, consensus (n=83) |
|---|---|---|---|---|---|---|
| DeepSeek high | 154 | 17/104 | 28 / 9 / 28 | 21 / 6 / 8 | **.76** | **.84** |
| gpt-oss high | 50 | 52/104 | **77** / 54 / 21 | 50 / 33 / 14 | .26 | .43 |
| gpt-oss medium | 24 | 70/104 | 65 / **84** / 20 | 47 / 62 / 13 | .14 | .22 |
| Qwen think | 85 | 32/104 | 40 / 59 / 33 | 44 / 42 / 16 | .35 | .38 |
| Qwen none | 20 | 82/104 | 48 / **124** / 7 | 39 / 96 / 5 | .06 | .06 |
| Gemma think | 76 | 40/100 | 62 / 45 / 32 | 59 / 35 / 13 | .34 | .32 |
| DeepSeek none | 105 | 47/104 | 62 / 49 / 26 | 68 / 36 / 11 | .34 | .31 |

`cross_axis` = a detection on another axis (almost always a topic) covers the span, but no
frame/evidence atom exists. "Consensus" = ≥3 annotators including at least one Sonnet, so the gap
is not an artefact of Opus-only gold (§5).

- **Topic covered, frame layer missing.** On `c192950w0002` (an anti-inflammatory diet talk; 9
  frame + 3 evidence gold atoms), gpt-oss-high emits **zero frames in both repeats**. In r1 it tags
  units 33–52 `topic:food_nutrition` + `topic:inflammation_as_a_general_health_narrative`, and in r0
  nothing covers 43–50. The frames it skips: *"Conventionally raised meat and dairy; these things can
  be loaded with toxins"* (toxin_framing, purity), *"really stick with grass-fed, organic animal
  products"* (naturalness), *"Inflammation is at the root"* (root_cause). DeepSeek gets 7 of the 9
  in each repeat. gpt-oss-medium's whole output is 6 detections: 5 topics and 1 mechanistic evidence.
- **The implicit or rhetorical labels go first; the keyword-like ones survive.** Label counts
  (emitted per repeat, gold in its own column):

  | label | gold | DS high | gpt-oss hi | gpt-oss med | Qwen think | Gemma | DS none |
  |---|---|---|---|---|---|---|---|
  | commercialization | 57 | 42 | 19.5 | 9 | 28 | 10.5 | 29 |
  | naturalness_appeal | 29 | 19 | 4 | 2 | 4.5 | 9 | 8.5 |
  | misinformation_correction_debunking | 21 | 15.5 | 1.5 | 0 | 2.5 | 5 | 3.5 |
  | personal_experience_evidence | 43 | 28 | 10 | 1.5 | 9 | 6.5 | 9.5 |
  | scientific_study_citation | 25 | 20 | 16.5 | 6.5 | 12.5 | 8.5 | 7.5 |
  | prestige_science_invocation | 4 | 2.5 | **5** | **7** | 4 | 4 | 1 |

  Study citation (an explicit "a study found") keeps 33–83% of DeepSeek's volume. Debunking,
  naturalness and personal experience fall to 0–47% (mostly under 35%). Prestige is the one label the
  alternatives **over**-call: they tag any named institution.
- **Frames "in the topic axis" happen only as mixed-axis detections, which get dropped.**
  `mixed_or_unknown_labels` drops: DS-none 76, Qwen-none 75, Qwen-think 26, Gemma 26, gpt-oss ≤2. In
  the strict DeepSeek runs **30 of 30** such rejections are topic + `cross_cutting:` in one detection,
  e.g. `['cross_cutting:mechanistic_scientific_language', 'topic:gut_health_microbiome']`
  (commercialization 8, mechanistic 7, study citation 6). For Qwen and Gemma the kind is unbroken and
  also fires on claims with wrong-axis ids, so some of those drops are claims.
- **Gemma does not link the axes on claims.** It emits 76 frame + 58 evidence detections per repeat,
  yet only 1% of its claims carry any `frame_ids`/`evidence_signal_ids`, against 37% for DeepSeek
  and 13–17% for gpt-oss and Qwen-think. It treats claim labeling and cross-cutting detection as
  separate tasks.
- **Emitted frames have loose semantics** (precision .51–.67 for Qwen, Gemma, DS-none). Qwen-think
  applies MAHA labels as keywords (its summary: "Reference to real foods aligns with MAHA food
  vocabulary"). Gemma puts `optimization_framing` on *"What is biohacking"*. DS-none puts
  `big_food_food_system_distrust` over units 16–83 of a migration rant. Three models tag
  `root_cause_framing` on *"leaky gut is the cause of a weak immune system"*, a plain causal claim.

## 3. Failure modes by model

**gpt-oss-120b high: moderate under-calling, noisy claims and products, flat confidence.**
- Validation: 146 drops, **112 of them `non_verbatim_quote`** (paraphrased quotes), plus 19
  span_out_of_window.
- Claims: 68 FP per repeat, 38.5 of them `spurious` (the most of any model). Many are ad copy or
  non-health: *"Fanduel offers online sports wagering in Kansas…"*, *"Waymo reduces social anxiety
  for users"* (from *"as someone with social anxiety, this is incredible"*), *"Methylene blue
  improves mood"* (from the anecdote *"She felt like her mood was better"*, which the codebook
  excludes as experience).
- Products: 40 FP per repeat, generic or non-health (`red light therapy`, `topical finasteride`,
  `Kansas Star Casino LLC`); **78% typed `other_product`** (94% at medium, DeepSeek 41%; type agreement .38).
- Null windows: 2.20 atoms per window, the worst. A sex-comedy null window (`c321803w0028`) draws 19
  `topic:reproductive_sexual_health` FPs over both repeats (*"your dick game is okay, or what"*), one
  spanning units 15–135.
- Discourse role defaults to `asserted_or_endorsed` (reported→asserted 10.5, rebutted→asserted 7
  per repeat). Confidence is 0.9 on 95% of atoms (AUROC .50).

**gpt-oss-120b medium: the same model at about half the effort.**
- Median 2 detections and 3.1 claims per window; output median 3.0k tokens against 10.6k at high.
- Frame misses are mostly `nothing_predicted` (84): it simply stops at one topic per subject.
  Example: `c177172w0003` (13 frame gold atoms) gets 6 topic detections and nothing else in r0.
- Drops rise to 14% (117 non-verbatim quotes).
- Claims turn into ad and legal boilerplate: *"Wegovy is a registered trademark of Novo Nordisk AS"*,
  *"You can try the Helix mattress for 100 nights risk-free"* (typed `diagnosis_or_prevalence`).
  It records `semaglutide` as a product (`other_product`, `recommended`), though the codebook names
  semaglutide as a non-product.

**Qwen3.5-35B-A3B thinking: a precise but sparse labeler, and it loses whole windows to unit ids.**
- Topic precision .94 on only 150 atoms (4.1 detections per window).
- **84 `span_out_of_window` drops.** In 10 of its 11 window-repeats with ≥5 gold atoms but no detections,
  validation drops explain the emptiness: `c192950w0002` r0 came back 0 detections / 0 claims after
  16 dropped annotations, `c178272w0003` was empty in both repeats (17 and 18 drops). It also has
  91 non-verbatim quotes and 37 certainty-marker mismatches.
- Claim recall .34 at 2.4 claims per window, the lowest of the thinking runs.
- **Discourse role over-hedged** (claim agreement .76 against DeepSeek's .92): sponsor copy and
  ordinary talk become `reported_or_quoted`, e.g. *"The Q Four Support System helps relieve aches and
  back pain"* (gold 4/4 asserted).

**Qwen3.5 no thinking: mostly format failure.**
- 36% of emitted annotations are dropped: span_out_of_window 105, non_verbatim 82, mixed labels 75,
  certainty 49. The worst single repeat lost 30 annotations in one window (`c163105w0009`).
- 46 of 116 window-repeats with ≥5 gold atoms have no detections, and 21 are completely empty.
- What survives leans to product FPs (27 spurious: `Talk Money to Me`, `OnlyFans`, `Cameo`, `The
  Bachelorette`, `T-Mobile for Business`) and claims that are not claims (*"Leverage is always
  being used on different people, so to control them…a thousand percent"*).

**Gemma-4-26B-A4B thinking: labels reasonably when it finishes, but it often doesn't (see §4).**
- The best alternative on topic (F1 .62) and products (.66).
- Topic errors are mostly wrong labels (32 same-axis FPs per repeat): `topic:childrens_health` on
  *"all the shit with the kids"*, `covid_19_pandemic_health` over units 57–77 (vaccine-injury court
  content), `environmental_health_chemical_exposures` on *"Pam Bondi is now not following up the
  Pfizer thing"*.
- Over-uses claim_type `institutional_or_conspiracy` (27.5 per repeat, against DeepSeek's 16) on
  ordinary facts: *"Approximately 100,000 Americans die every year from the drug problem"*, *"Food
  dyes are banned in Europe"*, *"Providing free ultrasounds has led more than 8,000 women to follow
  Christ"*.

**DeepSeek-V4-Flash, thinking off: over-produces, with bad spans and loops.** The same weights
without thinking lose on every axis.
- **Topic spans fragment**: median topic span 2 units against gold 4 and DS-high 5. Result: 84
  `span_only` topic FPs per repeat (DS-high 45.5), e.g. `topic:sleep` on units 62–63, *"she'd start
  yawning and like rubbing her eyes"*.
- **Frames on the wrong content** (precision .52): `government_institution_distrust` on
  *"Definitely needs to be held"*, `optimization_framing` on *"When it comes to cancer, he's got
  the answers"*, `commercialization` on a LifeLock identity-theft ad.
- **Format**: 76 mixed-axis detections (topic and cross_cutting labels together, §2), 61
  certainty-marker mismatches, 48 duplicates. **38 of the duplicates come from one response**
  (`c41217w0001` r1), a repetition loop.
- Products: 46 FP per repeat, most of any run (33.5 spurious: `Quince`, `Bet Rivers`, `Brook
  Insurance`, `Ghost Mountain Boys`). Null windows: 50% of window-repeats produce output (DS-high
  15%).
- Claim recall .42: it emits 218 claims against 352, several of them opinion (*"Everybody that was
  talking that crap needs to be held accountable"*, *"Obama is literally a Manchurian candidate"*).

## 4. Gemma 4 runaway generation

- 56 of 192 attempts (29%) hit `max_tokens=80000`, plus 1 `empty_output` (16,182 reasoning tokens,
  no content). 35 of 70 windows truncated at least once. After 3 attempts, 5 window-repeats were
  still unresolved (`c78310w0001`, `c4558w0003`, `c176579w0010` in r0; `c77624w0013`, `c29218w0006`
  in r1).
- **Output length is bimodal, with nothing in between.** Accepted responses: median 9.0k
  completion tokens (about 80% reasoning), maximum 18.3k. Truncated responses: exactly 80k, of
  which the server counts only 2–16k (median 7.2k) as reasoning. So ~65–78k tokens per runaway
  are counted as neither reasoning nor returned content. No accepted response falls between 18.3k
  and 80k.
- **It is stochastic, not tied to the window**: retries of the same window succeed at normal
  length (`c4558w0003` r1 attempt 2: 9.5k tokens after 5 straight truncations). It hits every
  stratum (7 rare_label, 7 health_dense, 7 ad_read, 6 mixed, 5 discourse, 2 synthetic, 1 null).
  Truncated windows have only slightly more gold (26 atoms against 23).
- One truncation (`c176579w0010` r0 attempt 2) reports **2** reasoning tokens against 80k
  completion (content null), so the runaway did not all happen inside the reasoning count.
- Cost: a truncated attempt averages 723 s against 92 s for an accepted one. The runaways take
  ~77% of Gemma's generation time.
- The longest accepted responses look normal (18–19 detections, no duplicate keys). Seeing the
  loop needs the runner to save partial text or reasoning on truncation.

## 5. Where the alternatives beat DeepSeek, and errors everyone shares

**Alternatives rarely beat DeepSeek.** Credit gold atoms found in every repeat of the alternative and
neither DeepSeek repeat, against the reverse:

| | gpt-oss hi | gpt-oss med | Qwen think | Qwen none | Gemma | DS none |
|---|---|---|---|---|---|---|
| alt-only / DS-only | 48 / 276 | 23 / 414 | 29 / 346 | 12 / 536 | 57 / 260 | 38 / 277 |

The alternatives' wins are scattered omissions, not a pattern. Five of six models extract
*"Bee pollen is one of nature's best multivitamins…"* (`c182738w0001`), a sponsor-read claim
DeepSeek skips in both repeats while extracting the neighbouring royal-jelly claim. Gemma's wins
are mostly topic (35 of 57), e.g. `topic:autoimmune_immune_health` on *"Have you struggled with a
weak immune system"*.

**Shared misses mostly trace to Opus-only gold.** 267 credit atoms are found by no model in any
repeat. **206 of them (77%) come from Opus annotators alone**: 84 Opus-pair `required`, 122
Opus-singleton `acceptable`. Recall by who supports the atom:

| atom support | n | DS high | gpt-oss hi | Qwen think | Gemma | DS none |
|---|---|---|---|---|---|---|
| all 4 annotators | 505 | .87 | .58 | .50 | .62 | .55 |
| opus-r1 + opus-r2 only (`required`) | 412 | .43 | .24 | .16 | .25 | .21 |
| one Opus only (`acceptable`) | 355 | .22 | .14 | .08 | .16 | .15 |

44% of frame credit gold (111 of 254) and 45% of evidence gold (90 of 200) is Opus-only. The two
Opus runs agree with each other at pairwise F1 .81–.84 (topic to claim), against .58–.71 for other pairs, so
the "≥2 authority" rule lets two near-identical runs of one model create `required` gold. Recall
ceilings are therefore partly an Opus-exhaustiveness target, and DeepSeek looks best partly because
its style is closest to Opus. This does not explain the frame collapse, which holds on consensus
atoms (§2).

**Errors 4–7 models share on the same span**, tagged *[spec]*, *[scoring]* or *[model]* (a shared model weakness):
- *[spec]* **Non-health ads inside health-adjacent episodes.** `Indeed` 7/7 models, `Michelob Ultra` 6/7,
  `LinkedIn Hiring Pro` 6/7, `Fanduel` 4/7 are all FPs against empty gold. The codebook's "record
  any product of any kind that is named inside a stretch of health content, including inside
  advertising reads" does not settle whether an unrelated ad break counts. It needs one explicit
  sentence.
- *[scoring]* **Product identity mismatches.** DeepSeek's `The Wellness Company RX parasite cleanse` (7/7
  models `different_product`) misses the gold aliases `RX Parasite Cleanse` / `The Wellness Company
  Parasite Cleanse`. Every model names `drkaryjones.com/backslashmyths` where gold has `The Top
  Seven Perimenopause Myths guide`. Product matching needs an exact key or a type match, so a
  near-identical name counts as both an FP and a miss. This is a scoring or alias-set issue, not a
  model issue.
- *[model]* **Sarcasm.** *"every doctor is busy shooting people up with 5G"* (`c128911w0034`): 6/7 models
  extract it as a claim, which adjudication `rejected`, yet all 7 miss the `topic:vaccines_immunization`
  that 4/4 annotators put there.
- *[model; worth a codebook example]* **Implicit self-promotion.** A host's coaching pitch (*"A coach can help you sort through the
  noise…"*, `c179765w0001`, 3 annotators × 3 spans of `commercialization`) is missed by every model
  in every repeat. A worked example in the codebook would help.
- *[model]* **Generic drugs as products.** `minoxidil` 6/7, `finasteride` 4/7, but not DeepSeek. The codebook
  rule here is explicit, so this is a model error. A prompt example would still help.
- *[scoring]* **Claim-matching artefact (minor).** 5–10 claim FPs per repeat per model sit on an
  unmatched gold claim's span but quote another fragment: *"Skipping meals is especially not good
  for fertility"* (unit 27, 6/7 models) against gold quoting unit 26, text similarity .38.

## 6. Other observations

- **Null windows** (10 items): atoms per window DS .65, gpt-oss-high **2.20**, DS-none 1.10,
  Qwen-think .95, Gemma .80. Much of it is borderline and credited (a yeast-infection claim); the
  real FPs are gpt-oss's sex-comedy topics and DS-none's sponsor products.
- **Calibration is uninformative for every model except DeepSeek-high** (AUROC .62). The rest sit
  at .47–.54 with TP and FP confidence within .01. gpt-oss puts 0.9 on 95% of atoms and Gemma on
  94%.
- **Discourse role splits in two directions**: gpt-oss under-marks (recovers 22/56 and 10/27 of
  non-asserted gold); Qwen and Gemma over-mark `reported_or_quoted` (predicted non-asserted 86 and
  98 against 26 and 54 gold). DeepSeek over-marks too (122 predicted against 71), but its matched
  agreement stays at .92.
- gpt-oss almost never uses `speculative` (3.5 of 300 claims per repeat, DeepSeek 25 of 352;
  certainty agreement .72/.66 against .81). DeepSeek-high also truncated 4 attempts at 80k, all resolved on retry.

## Implications

1. Frames/evidence: add a second cross-cutting pass over the topic detections, or worked examples
   for commercialization, naturalness, debunking and personal experience. Both target `cross_axis`.
2. Validation: window-local unit-id lists and verbatim reminders (Qwen loses 18–36%); split
   mixed-axis detections rather than dropping them.
3. Gold: count the two Opus runs as one authority, or report consensus recall; clarify non-health
   ad breaks; widen product aliases.
4. Runner: capture the excerpt or reasoning on truncation; cap Gemma's `max_tokens` near 20k.
