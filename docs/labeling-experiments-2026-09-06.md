# Labeling pipeline experiments — 2026-09-06

Work done against the restarted vLLM server (DeepSeek-V4-Flash-0731, TP=4,
`max_model_len` 98304) to refine the labeling pipeline and find throughput.
Every number below is measured, not projected, unless it says otherwise.

Scratch artifacts (scripts, run dirs, per-run `score.json`) live under the
session scratchpad `exp/`; they are reproducible from the scripts named here
but are not part of the repo.

## 1. The evaluation harness

The pilot slice is ~70% zero-yield, so a random draw measures almost nothing.
`build_slice.py` draws a fixed stratified slice — health-dense (top-decile
substantive episodes), ad-heavy, zero-yield — and saves the pilot's existing
`high` labels as `reference.json`. A 120-window slice (40 per stratum) is the
unit every variant below was run on.

**The reference is a comparison point, not ground truth.** It was produced by
the v5 prompt at high effort, and 25% of its windows were labeled at batch 1
through isolation. Both facts matter for reading recall numbers, and both are
handled explicitly below.

- `score.py <run> <reference> [name]` — recall in both directions, ad-span
  Jaccard, per-stratum splits, token accounting deduped by `response_id`,
  isolation counters, wall time.
- `compare.py <runA> <runB> <reference>` — the same metrics **between two
  runs**, which is the only comparison that isolates one variable. Scoring
  every variant against the v5 reference conflates effort with prompt drift.
  Also reports claim-`relevance` agreement.
- `project_corpus.py` — reweights a run's per-stratum token cost by the pilot's
  real stratum shares. **Necessary:** the slice is 1/3 zero-yield, the corpus is
  70%, and the slice runs 2.12x the corpus average cost per window.

## 2. Results

All runs: new code, concurrency 24. Batch 4 unless stated. `sub det` is
substantive detections; `health-dense` is that stratum's share of them.

| run | effort | batch | out tok/win | wall s | labeled | sub det | health-dense | claims | windows isolated |
|---|---|---|---|---|---|---|---|---|---|
| eff-none | none | 4 | 668 | 183 | 110/120 | 64 | 43 | 52 | 36 |
| eff-low | low | 4 | 3,345 | 988 | 120/120 | 59 | 58 | 112 | 27 |
| eff-medium | medium | 4 | 4,278 | 552 | 120/120 | 60 | 58 | 110 | 21 |
| **eff-high** | **high** | **4** | **8,826** | **2,689** | **118/120** | **118** | **106** | **152** | **17** |
| b1-medium | medium | 1 | 3,980 | 445 | 115/120 | 69 | 66 | 124 | 0 |
| b8-medium | medium | 8 | 3,524 | 1,194 | 119/120 | 66 | 62 | 107 | 36 |
| v6tax-medium | medium | 4 | 3,842 | 997 | 120/120 | 76 | 69 | 104 | 20 |
| quotediag | medium | 4 | 3,750 | 535 | 117/120 | 62 | 57 | 96 | 13 |
| quotediag2 | medium | 4 | 3,455 | 553 | 120/120 | 75 | 71 | 116 | 6 |

Reference on the same 120 windows: 107 substantive detections, 116 claims.

### Reasoning effort is the only quality lever, and only `high` reaches parity

`high` is the sole setting that matches the reference on health-dense content
(106 detections vs 105) and it exceeds it overall (118 vs 107, 152 claims vs
116). `low` and `medium` are indistinguishable from each other and both lose
~45% of health-dense detections. `none` is unusable: it under-detects by 60%
*and* fails schema validation often enough to lose 10 windows outright.

Two cautions on reading this table:

- **`low` vs `medium` is noise, not an ordering.** `compare.py` puts their
  mutual coverage at 79.7% / 80.0% — they find *different* ~60s. About 20% of
  detections are run-to-run variance at these efforts, which is larger than
  most of the differences in the table.
- **`eff-high` used the v6 prompt**, so its parity with the reference also
  clears the v6 prompt of having regressed recall. That was the live risk when
  the sweep started.

The config's existing choice of `high` is vindicated, on much better evidence
than the 6–10 sample measurement it cited. Its stated open question — whether
high's extra detections are recall or false positives — is *still open* and
still belongs to the blinded validation sample.

### Batch size does not change decode volume

Output tokens per window are essentially flat across batch size at fixed
effort: 3,980 (batch 1) / 4,278 (batch 4) / 3,524 (batch 8). Input tokens are
where batching pays — 14,158 / 7,562 / 7,462 — because the ~11.5k instruction
prefix is amortized. Input is prefill and largely prefix-cached; decode is the
bottleneck and 93% of it is reasoning.

**A superseded claim, recorded so it is not re-derived:** within a single run,
batch-1 requests appear to carry ~3x the output tokens and ~2x the detections
per window. That is selection, not causation — a batch is isolated *because* it
was rejected, and annotation-rich windows draw rejections. Running the whole
slice at batch 1 (`b1-medium`) collapses the effect to nothing measurable. The
config comment under `[label]` asserts that "batch 4 halves the per-window cost
of thinking, because reasoning is charged per request". That is **not supported
at medium effort** by this measurement. It should be said precisely: the config's
figure was measured at *high* effort on 12 and 8 windows (7,005 tok/window at
batch 1 against 3,236 at batch 4), and no clean batch-1 run at high effort was
made here — so this does not refute the claim at that setting, it refutes the
general mechanism the comment gives as its reason. A batch-1 run at high effort
is the experiment that would settle it.

Batch 8 is neutral-to-negative: quality is unchanged, tokens/window is
unchanged, but rejections nearly double (36 windows isolated vs 21 at batch 4),
which is the config's "model loses track" worry showing up as sloppier quotes
rather than as `omitted_windows` (that appeared once). Batch 8 at *high* effort
would emit ~48k output tokens per request and truncate against any budget that
still fits the context — it was queued and cancelled for this reason.

The context objection to batch 8 is nonetheless obsolete: at `max_model_len`
98304 a batch of 8 is ~29.7k of input and leaves ~66k for thinking. The config
comment citing 65536 has been corrected.

### Screening is closed

Three independent negative results, and one decisive one.

- **Keyword screen** (`keyword_screen.py`, `screen_tiers.py`): taxonomy-derived
  vocabulary (977 terms) keeps 74.3% of windows at 90.4% payload recall; adding
  a body lexicon pushes recall to 99.9% but keeps 98.3% of windows. Best
  operating point drops 17.6% of windows for 3.3% payload loss. The misses are
  ordinary-language health talk — "sex drive", "type O" — with no clinical
  vocabulary to match.
- **Ad near-duplicate detection** (`ad_nearmatch.py`, `ad_detect.py`): 74%
  recall of the model's ad spans, but precision is structurally capped because
  the model only marks *health-relevant* ads, so a real Dell read counts as a
  false positive. Adding a promotional-register filter cuts recall to 56.6%.
- **Ad caching**: only 3.8% of words are repeated copy; zero exact-duplicate
  whole windows.
- **Decisive:** on the pilot's full batches of 4, all-empty batches are **40.6%
  of batches but 7.0% of output tokens** (428 vs 3,878 tokens/window). A perfect
  screen that dropped every zero-yield window would save ~7% of generation. The
  model spends almost nothing reasoning about a window with nothing in it.

This closes screening as a *throughput* lever, including the lighter-model
screening round that motivated the Qwen suggestion. Qwen as a **replacement
labeler** is a different and still-open question — see next steps.

## 2a. Manual audit — are `high`'s extra detections real?

The sweep can only say `high` finds more than `medium`; it cannot say whether the
extra detections are recall or noise, because its only yardstick is another model
run. 61 detections were audited by four independent readers (Sonnet subagents)
against the project's own codebook, blinded: provenance was stripped, the three
arms were shuffled together, and no reader could tell which run produced an item.
`build_audit.py` assembles the set.

| arm | n | true positive | wrong label | not substantive | false positive | defensible |
|---|---|---|---|---|---|---|
| shared (high ∩ reference) | 30 | 26 | 1 | 3 | 0 | **87%** |
| high_only | 22 | 12 | 3 | 7 | 0 | **55%** |
| medium_only | 9 | 8 | 1 | 0 | 0 | 89% |

The `shared` arm is the positive control: at 87% it confirms the audit is
calibrated, so the `high_only` rate can be read.

**The answer: `high`'s extra detections are about half genuine recall.** They are
*not* hallucinations — **zero false positives in 61 items**, and none in any arm.
The model is not inventing health content. What it does at high effort is
over-rate the relevance of real but trivial material: 7 of 22 extra detections
(32%) should have been `passing` rather than `substantive`, and 3 more carry a
wrong topic label.

The over-calls are strikingly concentrated. Four of the seven are the same
comedic bit — hosts joking about a co-host's baldness — labeled *Men's Health &
Male Hormones* as substantive:

> "You don't sound bald. I swear, I hear hairs swishing back and forth as he speaks."
> "I'm the baldest. We will do the tie spin. That's unfair. I'm the baldest."
> "Hey, Wade, what the fuck happened to your hair? … Uh, it's genetic."

**This is a prompt problem, not an effort problem.** The `substantive` definition
— "the subject is discussed, explained or argued, not just named" — is being read
loosely enough to admit a punchline that names a body part. The fix is to sharpen
the substantive/passing boundary with explicit negative examples (a joke, a
one-line quiz item, a comedic riff), not to lower reasoning effort. Effort is
what finds the material; the relevance grade is what is miscoded.

Correcting the yield for audited quality: of `high`'s 118 substantive detections,
roughly 92 are defensible, against `medium`'s 60 (of which ~89% hold). `high`
still wins clearly, but by ~1.5x rather than the ~2x the raw counts imply.

### The wrong-label cases name real taxonomy gaps

Five items carried a wrong topic. Two of them are direct evidence for changes
already made or still needed:

- **D044** — an open foot wound labeled *Pain / Musculoskeletal Health*. This is
  exactly the gap the added **Injury / Wound Care / First Aid** topic fills; the
  audited run used the 84-label taxonomy, which had nowhere else to put it. An
  independent reader flagging it is the clearest validation the new labels have.
- **D024** — GERD and reflux labeled *Gut Health / Microbiome*. Upper-GI and
  digestive-tract conditions have no home in the taxonomy; the microbiome label
  is absorbing them. **A `Digestive / GI Conditions` topic looks warranted** and
  was not among the seven added.

The others (capsaicin/endorphins → *Food & Nutrition*; relationship conflict →
*Mental Health*; substance-use safety → *Mechanistic/scientific language*) are
boundary errors rather than gaps.

## 3. Pipeline changes made

All changes are in the working tree, uncommitted. 35 tests pass.

1. **Partial acceptance.** Validation is now per window: windows that validate
   are kept from the response that carried them, and only rejected ones are
   re-sent alone. Previously one bad window cost its whole batch a
   regeneration. Verified: 19 isolated batches moved 36 windows instead of ~76.
   (`validate_response_partial`, `classify_partial`, rewritten
   `classify_isolating`.)

2. **Word-sequence quote matching.** A quote is located by its word sequence
   rather than its exact characters, and what gets stored is the *transcript's*
   wording, so the stored quote is verbatim by construction. The rejections
   this fixes were never a different quote — a straight apostrophe for a curly
   one, a dropped comma. (`locate_quote`, `locate_quote_span`.)

3. **Span repair.** A span that stops short of its own evidence is widened onto
   it rather than rejected. This was the single largest remaining rejection
   source and it was *not* paraphrase: the quotes were verbatim in the window,
   and only the declared boundary was wrong. Measured at identical settings:

   | | before | after |
   |---|---|---|
   | windows labeled | 117/120 | **120/120** |
   | windows lost outright | 3 | **0** |
   | windows isolated | 13 | **6** |
   | quote rejections | 9 | **4** |
   | output tok/window | 3,750 | 3,455 |

   Grounding is untouched — the quote must still appear contiguous and in order
   *in that window*; only the boundary moves, and only far enough to cover the
   cited evidence.

4. **`relevance` on verification candidates.** Sponsor copy makes checkable
   claims, and in the pilot 53.7% of extracted claims sat inside ad spans with
   no field to filter on. Now every claim carries the same three-value relevance
   as a detection. Measured on runs with 110+ claims: **0 missing, 100%
   agreement** with the relevance of the detection span the claim sits in, 66–69%
   of claims marked `advertisement`. Zero claims sit in an ad span while calling
   themselves substantive — the failure mode that would leak sponsor copy into
   verification does not occur.

5. **`claim_type` definitions in the prompt.** The seven values were previously
   undefined, which is why `institutional_or_conspiracy` became a junk bucket.
   Each now has a written definition, with an explicit instruction that it is
   about institutional *actors*, never merely a surprising or contested claim.

6. **Seven topics added** (84 → 91 labels): Cancer; Neurology / Seizures / Brain
   Conditions; Dementia / Cognitive Decline / Ageing; Injury / Wound Care /
   First Aid; Surgery / Medical Procedures; Hearing / Vision / Sensory Health;
   Genetics / Inheritance.

7. **Isolation-cause instrumentation.** `batches_isolated_by_kind` in the
   manifest names the rejection that sent each batch to isolation. Isolation
   recovers most of those windows, so their cause never reached the failures
   table — the most expensive thing the run does had no cause to tune against.
   Quote rejections now also carry the offending wording in the message, which
   is how the span-repair diagnosis was made at all.

8. **Docs and config comments** updated for all of the above, including the two
   config claims the measurements falsified.

## 3a. What changed in the prompt and the label set

### Prompt (`PROMPT_VERSION` v5 -> v6)

**`claim_type` definitions -- the largest prompt change.** The schema has always
offered seven `claim_type` values and the prompt never defined any of them. The
pilot's consequence was that `institutional_or_conspiracy` became a junk bucket:
with no definition, any claim that felt surprising or contested landed there,
which is precisely the value a misinformation study cannot afford to have noisy.
Each value now carries a written definition, ordered so the discriminating
instruction comes first -- *choose by what the claim asserts, not by the subject
it is about*:

```
  causal                      -- X brings about, worsens or prevents Y
  treatment_or_prevention     -- doing or taking X helps, cures or protects
  risk_or_safety              -- X is dangerous, harmful or safe
  diagnosis_or_prevalence     -- how common a condition is, who has it, how it
                                 is recognised or diagnosed
  mechanism                   -- how something works in the body, or a stated
                                 composition, quantity or physiological process
  institutional_or_conspiracy -- about the conduct of institutions: that an
                                 agency, company, profession or government hid,
                                 falsified, suppressed or was paid for
                                 something. It is about actors, not about
                                 biology. An ordinary factual claim is never
                                 this value merely because it is surprising or
                                 contested
  other_factual               -- checkable, but none of the above
When two fit, take the more specific one; other_factual is the fallback, and
institutional_or_conspiracy is not.
```

The last two lines carry much of the work: they name the fallback explicitly,
and name which value is *not* a fallback.

**`relevance` on claims -- a schema change, not only prompt text.** Added to the
response schema, the `required` list, the validator, and the normalized output.
The prompt explains why the field exists rather than just naming it, because the
instruction is counter-intuitive -- the model must extract sponsor claims rather
than skip them, *and* mark them:

> A sponsor read makes checkable claims like any other speech ("three times the
> electrolytes of the leading sports drink"), and they must be extracted -- but
> mark them advertisement so a later stage can separate what the show says from
> what its advertisers say.

**What was deliberately not changed.** The detection axes, discourse-role values,
certainty ordinal, splitting rule and windowing all stayed as they were. The
audit above suggests one further prompt change is now warranted -- sharpening
`substantive` against `passing` -- but that is a v7 change to make on evidence,
not a guess folded into this round.

### Label set (84 -> 91)

Seven topics were added, each from a visible gap in the pilot output rather than
from a general sense of coverage. Every row carries a definition and an explicit
boundary against the neighbouring label it would otherwise leak into -- the
taxonomy's existing convention, since the definition governs and the keyword
column is examples only:

| added topic | boundary it draws |
|---|---|
| Cancer | suppressed-cure rhetoric to the frame axis; alternative remedies to Natural & Traditional Medicine |
| Neurology / Seizures / Brain Conditions | mental-health conditions to Mental Health; cognitive optimisation to Brain / Cognition / Productivity |
| Dementia / Cognitive Decline / Ageing | longevity protocols to Longevity / Anti-Ageing |
| Injury / Wound Care / First Aid | chronic musculoskeletal pain to Pain / Musculoskeletal Health |
| Surgery / Medical Procedures | -- |
| Hearing / Vision / Sensory Health | -- |
| Genetics / Inheritance | -- |

`Other health topic` was left in place as the gap detector it was designed to be.
On the random slice its share of detections fell 8.6% -> 4.6%, which is
suggestive but under-powered; the purpose-built slice that can test it properly
is described under open questions.

The audit independently supports **Injury / Wound Care / First Aid** (a foot
wound had been forced into *Pain / Musculoskeletal Health*) and points at one gap
still open: **Digestive / GI Conditions**, since GERD and reflux are currently
landing in *Gut Health / Microbiome*.

## 3b. Throughput levers: what was and was not tried

Stated plainly, because batch size got the most attention and is not the most
promising lever left.

**Tested:**

| lever | result |
|---|---|
| reasoning effort (none/low/medium/high) | the dominant decode lever; `high` required for quality |
| `max_output_tokens` (16k/28k/44k) | a tight budget is a *trap*: truncation isolates the whole batch |
| batch size (1/4/8) | no effect on decode volume at medium effort |
| validator efficiency | partial acceptance + span repair halved isolation -- a real win |
| keyword / ad-dedup / near-duplicate screening | four negative results; ceiling is 7% |
| prefix caching | verified already working (79.9% median hit rate); nothing to gain |

**Not tested -- and one of these is probably the best remaining idea:**

- **Concurrency.** Everything above ran at 24 for comparability. That was a gap
  in my coverage, though not unexplored for the project: the config already
  carries a sweep -- c=16 -> 7.7 windows/min, c=32 -> 13.3, c=64 -> 25.0,
  c=128 -> 36.3 -- measured at batch 4, high effort, across **two** nodes. It has
  not been re-validated on one node at the current 98,304 context, and scaling
  was still rising at 128, so the ceiling is not established.
- **Window overlap -- the strongest untested lever, and it needs no model
  change.** Windows are 900 words with 150 of overlap, so the stride is 750 and
  the corpus is walked at 1.2 windows per window's worth of text. Overlap is also
  where the pilot's 20.7% duplicate claims come from.

  | setting | windows for the same corpus | change |
  |---|---|---|
  | 900 / 150 (today) | 327,929 | -- |
  | 900 / 75 | 298,117 | **-9.1%** |
  | 900 / 0 | 273,274 | -16.7% |
  | 1200 / 200 | 245,947 | -25.0% |

  A 9% cut is larger than the entire screening ceiling and is deterministic
  rather than probabilistic. The cost is real and must be measured, not assumed:
  overlap exists so a span straddling a boundary is not lost, so this trades
  boundary recall for throughput and needs an experiment on the eval slice.
- **Speculative decoding / a draft model.** The workload is decode-bound and 93%
  of output is reasoning tokens -- the textbook case for speculative decoding.
  Untested, and plausibly the largest single win available on the current model.
- **Parallelism topology.** The server runs one replica at TP=4. For a
  decode-bound workload with many concurrent sequences, 2 replicas at TP=2 often
  beats 1 at TP=4 by avoiding an all-reduce on every decode step. Untested.
- **Server flags**: `--max-num-seqs` (the config notes the servers pin at 64),
  chunked-prefill tuning, CUDA-graph capture, weight quantization.
- **Prompt length.** The instruction prefix is ~11.5k tokens. It is prefix-cached
  so its direct cost is small, but whether a shorter prompt shortens *reasoning*
  is untested.

## 4. Corpus cost

Basis: the pilot's own corpus-wide cost at high effort is **2,962 output tokens
per window** over 6,723 windows. On the eval slice the pilot cost 6,292
tok/window — the slice runs 2.12x the corpus average, so slice numbers must be
divided down, not projected directly.

`eff-high` (v6 prompt) costs 8,826 tok/window on the same slice the pilot cost
6,292 on — **1.40x**. Scaling the corpus figure: ~4,150 output tokens/window,
or **~1.36B output tokens** for this batch of 327,929 windows, against the
pilot-equivalent ~0.97B. The v6 prompt buys +10% detections and +31% claims for
+40% tokens.

This is a real tradeoff and it is the user's call. It is also the honest
throughput conclusion: **decode volume is set by reasoning effort, effort cannot
be lowered without halving health-dense recall, and no prompt-, batch-, or
screening-level change moves it much.** Going materially faster means more GPUs
or a different model, not tuning.

## 5. Recommendations

1. **Keep `reasoning_effort = "high"`.** It is the only setting that meets the
   exhaustive-labeling goal. Now measured on 120 windows rather than 6–10.
2. **Keep `batch_size = 4`.** Batch 8 doubles rejections for no token saving;
   batch 1 loses the prefix amortization for no measurable quality gain.
3. **Ship the validator changes** (partial acceptance, word-sequence quotes,
   span repair). They cost nothing and recover windows that were being thrown
   away — 3 lost windows to 0, isolation halved, on the diagnostic run.
4. **Ship claim `relevance`.** It is the field that makes the ad problem
   filterable, and it validates at 100% agreement.
5. **Decide on the v6 prompt's +40% token cost** against +10% detections and
   +31% claims. If the budget is tight, the `claim_type` definitions and the
   `relevance` field are the parts carrying the quality; they could be kept
   while trimming prompt verbosity elsewhere.
6. **Raise `max_output_tokens` before lowering effort, never the reverse.** A
   budget set too tight is not a saving: truncation isolates the whole batch. At
   16000, `low` truncated four batches and ran 79% slower than `medium` at 28000
   while emitting 22% fewer tokens.
7. **Sharpen `substantive` against `passing` in a v7 prompt.** The audit's single
   largest finding: 32% of `high`'s extra detections are real health-adjacent
   material over-graded as substantive, dominated by comedic banter. Add explicit
   negative examples — a punchline that names a body part, a one-line quiz item,
   a comedic riff — rather than lowering effort, which is what finds the material
   in the first place.
8. **Add a `Digestive / GI Conditions` topic.** GERD and reflux are landing in
   *Gut Health / Microbiome* for want of anywhere else. This is the same kind of
   gap the seven added topics closed, found the same way.
9. **Test reduced window overlap before any further model-side tuning.** Cutting
   150 → 75 removes 9.1% of all windows, deterministically, and is larger than
   the entire screening ceiling.

## 6. Open questions and next steps

**Unfinished runs** (queued, cancelled when the GPUs were needed; scripts are in
`exp/final_queue.sh` and will re-run as-is):

- `oh-v4tax` / `oh-v6tax` — **the taxonomy A/B.** `build_otherhealth.py` builds a
  120-window slice from the 367 pilot windows that could only be called
  `other_health_topic` (192 such detections). Running 84 labels against 91 on
  those windows, same prompt and effort, is the real test of whether the seven
  added topics earn their place. The random slice cannot answer it — those are
  Reddit-story shows that never discuss cancer or dementia, and the new topics
  were used 4 times there, correctly. On the random slice
  `other_health_topic` fell 8.6% → 4.6% of detections, which is suggestive and
  under-powered.
- `prod-candidate` — v6 prompt + 91 labels at high effort, to price the final
  recommendation.

**Research directions, roughly in value order:**

1. **Qwen3.8-Flash-Next as a replacement labeler, not a screen.** Screening is
   closed, but the whole corpus at a smaller model is untested and is the only
   remaining lever that could move the cost by an order of magnitude. Needs the
   GPU swap. The evaluation harness here (`build_slice.py` + `score.py` +
   `compare.py`) is model-agnostic and would score it directly against
   DeepSeek's output on the same 120 windows.
2. **Extend the blinded validation sample.** The 61-item audit above is a first
   pass, not the full validation: 22 items in the decisive arm, one reader per
   item, and no inter-rater agreement measured. Its headline results — zero
   false positives, 55% vs 87% defensibility — deserve a larger sample with
   overlapping readers before they carry a publication. `eff-high` produced 8 substantive detections in `zero_yield`
   windows where the reference had 0 — those are either recall the pilot missed
   or false positives, and nothing here can tell which. This is the same
   question the config already flags, and it now blocks interpreting the v6
   prompt's +10% detections.
3. **Run-to-run variance is ~20%** and nobody has budgeted for it. Several
   comparisons in the table are inside it. Two runs at identical settings would
   establish the noise floor and make future A/Bs readable.
4. **Sampling.** The pilot's 6,723 windows are a contiguous ID block of
   Reddit-story shows, not a random draw — 368 of 447 episodes are contiguous
   blocks starting at window 1. Prevalence estimates from it are not corpus
   estimates. `podcast_title` is null throughout, so shows cannot currently be
   identified in the output at all.
5. **Overlap duplication.** 20.7% of pilot claims are duplicates from the
   150-word window overlap. `merge` deduplicates detections; claims appear to
   need the same treatment.
6. **ASR artifacts reach the labels.** One rejection traced to a transcript
   stutter ("also known as also known as"), which the model silently corrected
   and the validator then rejected. Span repair does not cover this class —
   worth deciding whether the matcher should absorb adjacent repeated n-grams.
7. **The validator is not fingerprinted.** `run_fingerprint` covers prompt,
   taxonomy, windows, model and batch size, but not validator behavior — and
   span repair changes stored spans. Two runs with the same fingerprint can now
   differ. Worth adding a validator version to the fingerprint.
