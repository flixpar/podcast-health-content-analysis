# Labeling benchmark

`analysis/benchmark/` is a fixed evaluation set for the transcript labeler in
`analysis/topic_labeling.py`, with reference labels from several annotators
and a scorer that reports every number next to the annotators' own
agreement. It exists so that a change to the model, prompt, reasoning
effort, batch size, windowing or labeling method can be read as "better" or
"worse" before the expert human validation sample exists, and so that the
subjectivity of the task is measured rather than hidden.

Run everything from the repository root with the project venv:

```bash
.venv/bin/python -m analysis.benchmark <command>
```

## What is in `benchmark/`

| file | what |
| --- | --- |
| `config.toml` | strata quotas, seeds, caps, genre mapping, rare-label list |
| `topics-v6.md`, `taxonomy.json` | the frozen 91-label taxonomy the gold is built on, with `label_aliases` for scoring runs made on the 84-label taxonomy |
| `items.jsonl` | the item set: windows in the pipeline's own shape plus `item_id`, `stratum`, `split`, `source`, `tags`, `provenance` |
| `annotators.json` | who produced references (model, method, authority) |
| `references/<item_id>/<annotator>.json` | one validated window result per annotator per item, plus the pre-repair `raw` output |
| `gold.jsonl` | aggregated gold atoms with tier, support, span envelope and vote distributions |
| `agreement.json` | pairwise agreement between annotators and Krippendorff's alpha per attribute |
| `adjudication.jsonl` | optional overlay: tier decisions on disputed atoms |
| `manifest.json` | benchmark version, item hash, composition, gold hash |
| `runs/` (gitignored) | candidate runs, each with `run_manifest.json`, per-repeat `labels.sqlite` and `attempts.jsonl`, `score.json`, `scorecard.md` |
| `pool/` (gitignored) | the candidate pool and screening verdicts the items were selected from |

`analysis/benchmark/codebook.md` is the task definition the references are
anchored to. Prompts are attempts to make a model do that task; the codebook
is what "right" means. Changing the codebook is a new benchmark version.

## Items

One item is one 900-word window exactly as `prepare` would emit it for that
episode (same units, IDs, timing, metadata), so any labeler that consumes
`windows.jsonl.zst` consumes the benchmark unchanged. Corpus items were
drawn from the whole corpus using the lexical scan's per-episode counts to
choose episodes and the same lexicon over each window's units to choose
windows, then screened by Sonnet agents for fit, phenomena and ambiguity.

| stratum | n | what it tests |
| --- | --- | --- |
| health_dense | 40 | wellness shows; many annotations per window; recall and span quality |
| mixed | 30 | non-health shows with a little health content; boundary and precision |
| null | 40 | no health content; the correct answer is empty; the false-positive floor (about 70% of the corpus looks like this) |
| ad_read | 20 | sponsor reads for health products; relevance, mention role, Commercialization |
| discourse | 20 | debunking and interview shows; quoted, questioned and rebutted claims |
| rare_label | 20 | keyword-retrieved windows for rare topics and frames; reported separately |
| synthetic | 15 | scripted passages with one planted phenomenon each; reported separately |
| contrast | 15 | minimally edited twins of dev items with an expected change known by construction |

Items carry a stratified `dev`/`test` split (about 2:1). Per-item results
for `test` are hidden by default (`score --show-test` reveals them) so that
prompt iteration on `dev` cannot quietly overfit the whole set. The set can
grow: `select --grow` keeps existing items, and every run records the item
hash it was scored on, so `compare` only ever compares shared items.

## References and gold

Three annotators labeled every base item independently against the
codebook: one Opus pass and two Sonnet passes, each as a Claude Code agent
working from a bundle directory that contains only the items, the codebook,
the output schema and the validation command. Agents write their first
complete answer to `results.raw.json`, then repair only what the pipeline
validator rejects; both are stored, and `agreement.json` reports the repair
delta per annotator so a repair habit that drops hard annotations is visible.

`aggregate` clusters the annotators' atoms per item. An atom is one
(axis, label, span) for a detection, one claim, or one product mention;
clustering uses the same matching rules a candidate is scored with. Each gold
atom records:

- `tier`: `required` (annotator authority of at least 2 behind it, i.e.
  two ordinary annotators, however many there are in total), `singleton`
  (one), or, through the adjudication overlay, `acceptable` or `rejected`;
- `members`: one `<annotator>:<atom hash>` per contributing atom. An
  adjudication verdict is keyed by the singleton's member, not by the
  cluster's position, so it survives re-clustering when annotators are
  added, and it lapses on its own once a second annotator agrees with the
  atom (the atom is then required on its merits);
- the tightest and widest reference span (the envelope);
- per-attribute vote distributions (discourse role, relevance, certainty,
  claim type, product type, mention role, product name).

Synthetic items carry the author's `planted` annotations. `aggregate`
checks each plant against the gold and reports it as `ok`, `singleton`
(found by one annotator only), `missing`, `split` (the plurality disagrees
on an attribute but not unanimously) or `contradicted` (every annotator
read an attribute differently). A missing or singleton core plant means the
passage does not do what it was written to do and should be fixed or
dropped; a contradicted peripheral attribute is corrected in the plant with
a note under `provenance.plant_revisions`, since the plant is a check on the
item, not part of the gold.

`aggregate` also derives two things from the references that scoring reads
back:

- a **label adjacency table** (`agreement.json: label_adjacency`): same-axis
  label pairs that different annotators put on the same span in each
  other's place at least three times. A candidate that lands on the other
  side of one of these pairs is making a disagreement the references make
  themselves; the scorecard reports an adjacent-credit F1 beside strict F1
  (never in its place), and marks such pairs in its confusion list;
- a **leave-one-out ceiling** (`agreement.json: leave_one_out`): each
  annotator scored as a candidate against gold rebuilt without it, with
  the same scoring and the overlay still applied. This is what a labeler
  of reference quality scores on the scorecard, in the scorecard's own
  units, and is the ceiling to read the headline numbers against.

- a **contrast validity table** (`agreement.json: contrast_validity`): once
  the twins are reference-labeled too, each annotator's own labels of base
  and twin are run through the contrast evaluation as if it were a
  candidate. A perturbation no annotator passes is a bad twin or a bad
  spec, and a twin whose target the gold does not recognise is excluded
  from every pass rate (`target_not_in_gold`). The candidate's contrast
  numbers are read against these rates, and the annotators' no-op
  collateral is the noise floor of independent labeling itself.

Contrast pairs are judged on the targeted atom with the scoring match, not
by exact identity: the target is read with a one-unit margin, certainty
perturbations pass when the level moves in the intended direction from
wherever the base labeling put it, decoys and the no-op pass when no claim
at the target appears, disappears or changes certainty or role, and
everything else that differs between base and twin is collateral.

The mechanical gold is reproducible from the references; the overlay is
applied on top, never edited in. A future human expert pass is just another
annotator: register it in `annotators.json` with a higher `authority`,
store its results under `references/`, and re-run `aggregate`.

## Scoring

Predictions are exploded to atoms the same way as references, so a
detection carrying three labels is three atoms and an extra wrong label is an
extra false positive. Matching is optimal one-to-one per kind:

- detection: same axis and label; span IoU >= 0.5 against the tightest
  reference span, or the shorter of the two spans at least half inside the
  longer (annotators mark the same phenomenon at different extents, and
  extent is reported separately as mean span IoU over matches), or contained
  in the envelope with at least half the tight span's length;
- claim: spans overlap and the evidence quotes overlap (both are verbatim
  transcript text); claim-text similarity only as a tiebreak;
- product: spans overlap and the product key or type matches; name
  correctness against the annotators' alias set is a separate attribute.

Tiers decide credit. Matching `required` or adjudicated-`acceptable` is a
true positive; matching an unadjudicated `singleton` is unscored (neither TP
nor FP); matching `rejected` or nothing is a false positive. Recall is over
`required` (strict) and support-weighted over required plus singletons (soft).

The scorecard (`runs/<name>/scorecard.md`) reports, for `dev` and `test`:

- precision, strict and soft recall, F1 per axis and for claims and products;
- yield ratio (predicted / gold atoms), the direct read-out of over- or
  under-calling;
- attribute agreement on matched atoms: exact agreement with the plurality
  and vote share (the fraction of annotators who chose the same value, so a
  defensible minority reading scores one third rather than zero); expressed
  certainty as linear-weighted kappa; the annotators' Krippendorff's alpha
  beside each as the attribute ceiling;
- null-window false positives (atoms per null window, share with any output);
- contrast sensitivity: the targeted atom moves as the perturbation table
  says; collateral change reported against the no-op twins' rate; decoys
  separately;
- error classes: same-axis wrong label, cross-axis, span-only, spurious,
  nothing predicted;
- validity and cost from the attempts log: first-attempt acceptance,
  rejections by kind, requests per accepted window, output tokens and dollars
  per accepted window (prices from `analysis/usage-limits.toml`);
- consistency: with `--repeats 2` (the default), self-agreement between
  repeats is the noise floor quoted beside every comparison;
- calibration: AUROC of `confidence` for predicting a true positive.

Rare-label, synthetic and contrast items are excluded from the headline
numbers and reported per stratum.

**Ceiling.** Gold-based numbers are the primary read, but they are not
comparable with inter-annotator agreement: the gold is a consensus (atoms two
of three annotators agreed on, singletons unscored), which is an easier target
than any single annotator. The scorecard therefore carries a like-for-like
table of pairwise F1 with the same one-to-one atom matching: the candidate vs
each reference annotator, the annotators vs each other, and the candidate vs
its own repeat. A candidate whose mean pairwise F1 sits inside the
reference-reference range is at ceiling on that axis; a candidate that agrees
with itself far more than with the references is consistent but biased; and
the per-annotator rows show family bias (agreeing with one annotator far more
than the others).

**Comparison.** `compare` runs a paired bootstrap over (item, repeat) for
each headline metric between two runs and reports the delta with a 95%
interval, per-stratum deltas and the items that moved most, so a prompt
change reads as "helped discourse role on interview windows, hurt precision
on null windows".

## Running a candidate

A benchmark run is configured exactly like a production run, with the same
TOML tables and flags:

```bash
.venv/bin/python -m analysis.benchmark run --name ds-low \
    --pipeline-config benchmark/pipeline-deepseek.toml --repeats 2
# typed flags after -- win over the config
.venv/bin/python -m analysis.benchmark run --name ds-high \
    --pipeline-config benchmark/pipeline-deepseek.toml -- --reasoning-effort high --max-output-tokens 44000
# a prompt variant: the rubric file replaces SYSTEM_RUBRIC; the codebook JSON is appended as usual
.venv/bin/python -m analysis.benchmark run --name v7-rubric --rubric-file analysis/prompts/rubric-v7.md ...
.venv/bin/python -m analysis.benchmark score benchmark/runs/ds-high
.venv/bin/python -m analysis.benchmark compare benchmark/runs/ds-low benchmark/runs/ds-high
```

Runs made on the 84-label taxonomy score through `--alias v5-84`, which
collapses the seven v6 topics onto the labels the older taxonomy would have
used, on both sides.

Every run manifest records the pipeline fingerprint, the rubric sha256, the
taxonomy sha256, the sha256 of the validator's source (the validator is not in
the pipeline's own fingerprint), the benchmark version and item hash, and the
git commit. The item hash is recorded but not fingerprinted: when items are
added, `run --name <same name>` resumes the run and labels only the windows
its store does not hold yet, so an old run and a new one compare over their
shared items rather than starting over.

## Building and extending the benchmark

Growing the item set: raise the quotas in a config (see
`benchmark/config-grow.toml`, which also narrows the rare-label lists to the
labels round 1 covered thinly and raises the per-label caps), build a pool
with `--config <that file> pool --out-dir benchmark/pool-grow`, screen the
strata that need filling, then `select --grow`, which keeps every existing
item and its split and only fills strata below quota. New items then get
reference passes with `reference tasks --annotator <id> --only-missing`.

The agent-driven steps all use the same mechanism: the CLI writes
self-contained bundles under `../podcast-misinfo-benchmark-tasks/` (or
`$BENCHMARK_TASKS_DIR`), agents fill them in, `ingest` validates every output
before it enters `benchmark/`.

```bash
# corpus items
.venv/bin/python -m analysis.benchmark pool            # candidate windows per stratum
.venv/bin/python -m analysis.benchmark screen tasks    # Sonnet screening bundles
.venv/bin/python -m analysis.benchmark screen ingest <run_dir>
.venv/bin/python -m analysis.benchmark select          # fill quotas, assign split
# synthetic and contrast items
.venv/bin/python -m analysis.benchmark synthetic tasks ; ... ; synthetic ingest <run_dir>
.venv/bin/python -m analysis.benchmark contrast tasks  ; ... ; contrast ingest <run_dir>
# references
.venv/bin/python -m analysis.benchmark reference tasks --annotator opus-r1
.venv/bin/python -m analysis.benchmark reference ingest <run_dir> --annotator opus-r1 --model claude-opus-5
.venv/bin/python -m analysis.benchmark reference add-run benchmark/runs/<name> --annotator <id>   # a run as an annotator
.venv/bin/python -m analysis.benchmark aggregate
```

To grow the set: raise quotas in `config.toml`, re-run `pool` and
`select --grow`, then `reference tasks --only-missing` per annotator and
`aggregate`. New items carry `added_in`.

## Validation of the benchmark

Benchmark v1 was built on 2026-09-09: 200 items (170 corpus windows from 82
shows, 15 synthetic passages, 15 contrast twins), three reference passes
(one Opus, two Sonnet, all as Claude Code agents against the codebook) on
every corpus and synthetic item, an Opus adjudication pass over every
singleton, and two candidate runs of DeepSeek-V4-Flash through the hosted
API on the dev split, at `low` and `high` reasoning effort, two repeats
each. The validation budget was $20 and was spent to the cap.

### The reference set

| | value |
| --- | --- |
| items with three annotators | 185 (all corpus and synthetic items) |
| gold atoms | 3,870 |
| required (two or three annotators) | 2,248 |
| singletons, adjudicated acceptable | 1,532 |
| singletons, adjudicated rejected | 90 |
| null windows whose gold is empty | 30 of 40 |

Opus finds more than Sonnet (about 21 atoms per item against 15), so most
singletons are Opus atoms the Sonnet passes did not make, and the
adjudicators kept 94% of them. Rejections cluster on a few grounds: the
catch-all topic used where a listed topic applies, a span or quote that
does not carry the labeled material, ad copy or political rhetoric
extracted as a checkable claim, a generic substance coded as a product, and
a claim text sharpened beyond what was said.

Reference-reference agreement (pairwise F1, one-to-one atom matching):

| axis | Opus vs Sonnet-1 | Opus vs Sonnet-2 | Sonnet-1 vs Sonnet-2 |
| --- | --- | --- | --- |
| topic | 0.630 | 0.628 | 0.684 |
| frame | 0.668 | 0.668 | 0.720 |
| evidence | 0.628 | 0.625 | 0.645 |
| claim | 0.635 | 0.662 | 0.727 |
| product | 0.750 | 0.755 | 0.867 |

The two Sonnet passes agree more with each other than either does with
Opus, which is the family effect the per-annotator columns exist to show.
Attribute alphas run from 0.57 (discourse role on topic detections) to 0.94
(product type); expressed certainty is 0.70. Ten of the fifteen synthetic
items had every planted annotation confirmed as `required` gold; the rest
had their core plant confirmed and a peripheral attribute overruled (see the
plant check above).

### Low vs high reasoning effort

Paired comparison over the 105 dev items both runs labeled (191
item-repeat rows, corpus strata, pooled; `compare val-low val-high`):

| metric | low | high | delta (95% CI, paired bootstrap) |
| --- | --- | --- | --- |
| topic F1 (strict) | 0.707 | 0.773 | +0.066 [+0.034, +0.100] |
| topic recall (required) | 0.578 | 0.691 | +0.112 [+0.068, +0.159] |
| topic precision | 0.908 | 0.877 | -0.030 [-0.067, +0.006] |
| evidence F1 (strict) | 0.690 | 0.770 | +0.080 [+0.037, +0.128] |
| frame F1 (strict) | 0.708 | 0.746 | +0.038 [-0.015, +0.087] |
| claim recall (required) | 0.590 | 0.654 | +0.064 [+0.022, +0.102] |
| claim precision | 0.964 | 0.942 | -0.022 [-0.046, +0.001] |
| product F1 (strict) | 0.849 | 0.893 | +0.044 [-0.017, +0.109] |

From each run's own scorecard (dev split, mean of two repeats):

| metric | low | high |
| --- | --- | --- |
| topic yield ratio | 0.43 | 0.53 |
| null windows: atoms per window, share with any output | 0.10, 6% | 0.10, 6% |
| first-attempt acceptance | 0.795 | 0.725 |
| requests per accepted window | 1.37 | 1.55 |
| output tokens per accepted window | 14k | 40k |
| cost per accepted window | $0.019 | $0.054 |
| seconds per request | 79 | 200 |

The pass criteria held: `high` beats `low` beyond the noise floor on topic
recall, evidence detection and claim recall, with confidence intervals that
exclude zero; the cost is a small, not significant, loss of precision. The
paired bootstrap also shows where the gain lives: the `mixed` stratum
(general shows where health content is a minority) moves from a topic F1 of
0.35 to 0.67 and claim recall from 0.40 to 0.85, while `ad_read` and
`rare_label` claim recall do not move. Both efforts under-call relative to
the references (yield ratio about half), and both are quiet on null
windows (one atom per ten windows; 6% of null windows get any output), so
the false-positive floor is not what separates them.

Read against the ceiling, `high` is at the reference range on topics
(0.640 against 0.628 to 0.684) and evidence signals, above it on products,
and below it on frames and claims. The candidate agrees more with the two
Sonnet passes than with Opus on every axis, as the Sonnet passes do with
each other. Self-agreement between repeats is 0.71 (topic) to 0.88
(product), above every reference pair, so run-to-run noise is smaller than
annotator disagreement and a two-repeat mean is a stable estimate.

The dominant residual errors at both efforts are missed claims (nothing
predicted where the gold has a claim) and same-axis wrong topic labels; at
`high`, span-only topic false positives grow as it labels more.

Observations about the hosted API that the runs surfaced, and that the
validator now tolerates: fenced JSON, bare arrays, trailing commas and
empty outputs despite a strict schema; quotes that differ from the
transcript only in punctuation or an ASR stutter; and at `high` effort 69
of 251 responses truncated at a 44k output budget, which is the main reason
its first-attempt acceptance is lower.

## Round 2 (2026-09-12): a second Opus pass, 60 more items, twins as items

Round 1 left three things visible in the data: the gold was tilted toward
what the two Sonnet passes agreed on (Opus labels about twice as
exhaustively, and the adjudicators accepted 94% of its extras), five labels
had no required gold at all and nineteen had fewer than five atoms, and the
contrast twins had never been checked against anyone. Round 2 addressed
each with about the same agent budget as round 1.

### What changed in the design

- **Four annotators, two per family.** A second Opus pass (`opus-r2`, a
  different bundle grouping) labeled every item. "Required" became an
  authority count of two rather than a two-thirds share, so agreement
  between the two Opus passes is gold on the same terms as agreement
  between the two Sonnet passes.
- **Verdicts keyed by atom.** Adjudication verdicts attach to the singleton
  atom's own identity and lapse once another annotator agrees with it, so
  adding annotators re-clusters gold without invalidating the overlay.
- **Adjacent-credit F1 and a leave-one-out ceiling** on the scorecard, both
  derived from the references (see above).
- **Contrast evaluation with the scoring match**, validated on the
  annotators themselves.
- **Sixty new corpus windows** for the labels round 1 covered thinly (50
  rare-label windows across 21 labels, 10 mixed), screened by Sonnet and
  labeled by all four annotators.

### The reference set after round 2

| | round 1 | round 2 |
| --- | --- | --- |
| items | 200 | 260 |
| annotators per base item | 3 | 4 |
| gold atoms | 3,870 | 6,786 |
| required | 2,248 | 5,061 |
| adjudicated acceptable / rejected | 1,532 / 90 | 1,572 / 153 |
| labels with no required atoms | 5 | 1 (manosphere) |
| labels with fewer than five | 19 | 5 |
| labels with twenty or more | 25 | 53 |

Every singleton left after the fourth annotator was adjudicated by Opus
agents (1,185 verdicts across two passes, about 91% acceptable); the
rejection grounds match round 1: the catch-all topic used where a listed
topic applies, spans or quotes that do not carry the label, anecdotes,
opinions, sponsor terms and political rhetoric extracted as claims, and
generic substances or incidental brands recorded as products.

Pairwise topic F1 by family: Opus vs Opus 0.81, Sonnet vs Sonnet 0.70,
Opus vs Sonnet 0.60 to 0.63. Opus is internally consistent and
exhaustive; the Sonnet passes under-call by about half. The leave-one-out
table makes this the benchmark's most important reading:

| annotator | topic P / R / F1 | claim F1 | product F1 |
| --- | --- | --- | --- |
| opus-r1 | 0.85 / 0.89 / 0.87 | 0.90 | 0.92 |
| opus-r2 | 0.81 / 0.94 / 0.87 | 0.89 | 0.95 |
| sonnet-r1 | 0.92 / 0.53 / 0.67 | 0.65 | 0.77 |
| sonnet-r2 | 0.94 / 0.50 / 0.65 | 0.67 | 0.78 |

A labeler that finds what one careful exhaustive annotator finds scores
about 0.87 on topics; one that finds what a careful conservative annotator
finds scores about 0.66 with precision above 0.9. The DeepSeek runs sit in
the second group.

### The candidate runs against the round-2 gold

Same runs as round 1, re-scored (dev split, corpus strata, mean of two
repeats):

| metric | low | high |
| --- | --- | --- |
| topic F1 (strict) | 0.602 | 0.655 |
| topic F1 (adjacent credit) | 0.617 | 0.676 |
| topic recall (required) | 0.443 | 0.514 |
| topic precision | 0.940 | 0.903 |
| claim recall (required) | 0.429 | 0.483 |
| claim precision | 0.979 | 0.975 |
| product F1 (soft) | 0.775 | 0.829 |
| topic yield ratio | 0.37 | 0.45 |

The numbers fell from round 1 because the gold grew, not because the runs
changed: recall is now measured against everything two of four annotators
found. The ordering and the paired-bootstrap conclusions are unchanged
(high beats low on topic recall, evidence detection and claim recall with
intervals excluding zero; precision falls slightly). Against the
leave-one-out table, high effort at 0.655 is at the ceiling of a
conservative annotator and 0.21 below an exhaustive one, and its whole
deficit is recall.

### Contrast twins on the annotators

With all four annotators labeling the 15 twins, the contrast evaluation
could be checked on them. Per annotator, targeted pass rates run 0.67 to
0.89, decoy pass rates 0.5 to 1.0, collateral change 0.32 to 0.60 of
atoms outside the edit, and no-op collateral 0.20 to 0.64. That last
number is the noise floor of independent labeling itself: two labelings
of a window that differs by one reworded filler sentence still disagree
on a fifth to two thirds of atoms outside the edit, and a candidate's
collateral rate should be read against it. Two twins are defective and
are excluded or flagged: the brand-to-generic twin keeps the sponsor's URL
and promo code, so every annotator still records a product; the
de-healthed twin's target was never a gold atom in the base. Both are
fixed in the next authoring round.

### Codebook findings, round 2

The round-2 annotators reported the same themes as round 1, now with a
fourth voice, and added: the `topic:cancer` definition routes alternative
remedies to a label that does not exist; hepatobiliary, renal and
thyroid content has no home; "can" was again coded every possible way;
the product-mention rule pulls in incidental brands, retailers and
platforms that no one thinks are health offerings; and the ad-read rules
say nothing about a host's own product inside a delimited read
(`advertised` and `own_product` are both right and only one fits). All of
it is folded into `benchmark/codebook-v2-proposal.md`.

### What is not yet validated

- The synthetic and contrast strata have reference labels but no candidate
  labels: the budget ran out (and the API account's balance with it) before
  the runs could be resumed over the 25 dev items added after the first
  pass. Resuming `val-low` and `val-high` over them costs about $1 and $3
  and fills the contrast and synthetic rows of the scorecard.
- The test split has never been labeled by a candidate; the dev numbers
  above are the only ones, and prompt iteration on them can overfit.
- The references are all Claude-family; a non-Anthropic or human pass would
  make the ceiling less of a Claude-consistency measure.

### Where the codebook runs out

Every reference annotator was asked to report the codebook ambiguities it
hit. Across the 65 corpus and synthetic bundles the same themes recur, and
they are the first things a codebook revision (a new `benchmark_version`)
should settle. They also explain most of the attribute disagreement in
`agreement.json`, so a candidate's errors on these points should be read
against the reference alpha, not as plain mistakes.

- **Certainty markers outside the example lists.** The modal "can"
  ("magnesium can help") was coded three ways (unhedged, hedged,
  speculative) by different annotators, and Opus and Sonnet disagree
  systematically. The same goes for "clearly", "we know that", "basically",
  "up to X%", "a lot of", ASR filler "like" before a number, and statistical
  idioms ("twice as likely") that contain a listed marker word. Two more gaps:
  a hedge and a booster in one span, and a hedge inside quoted speech.
- **Missing topics.** Thyroid and other endocrine conditions, allergies,
  osteoporosis, Crohn's and colitis, TMJ and orthodontics, referred pain,
  sun exposure, and "energy" theories of organ function all fell to
  `other_health_topic` or were split across neighbours.
- **Topics that list the same term.** Hair loss (dermatology vs men's
  health), fluoride and pesticide policy (fluoride / environmental vs public
  health policy), vaccine mandates (vaccines vs policy), blue light (sleep vs
  EMF), electrolytes and melatonin (nutrition vs supplements vs sleep), zinc
  deficiency. The "more specific label wins" rule does not say which is more
  specific, and Opus double-labels where Sonnet picks one.
- **What counts as health content at all.** Passing mentions in true crime
  (gunshot wounds, hospital scenes), sports injury reports, biographical
  lists of a public figure's conditions, colloquial psychiatric terms
  ("narcissist", "fragile mental state"), idiomatic "healthy", figurative
  "my brain is fried", a podcast's own tagline, and jokes that name a body
  part. Annotators split on whether these get a `passing` detection or
  nothing; there is no minimum-content threshold.
- **Product-mention scope.** The literal rule ("any product named inside
  health content") pulled in retail venues, social platforms, a hospital
  under criticism, a charity, a podcast's own membership, cookware and
  nicotine pouches (which fit no `product_type`). Unsponsored personal brand
  recommendations sit between `recommended` and `neutral`, and a host's own
  free guide between `advertisement` and `substantive` plus Commercialization.
- **Discourse role on the topic axis.** When a passage reports, questions or
  rebuts a claim, annotators disagree whether the *topic detection* takes the
  claim's role or stays `asserted_or_endorsed`; the same for a debunking
  span (the correction is asserted, the corrected claim is rebutted) and for
  a speaker who voices both sides.
- **Claim type edges.** Institutional inaction, grant-funded outcomes and
  legal arrangements ("protects Big Pharma from liability") strain
  `institutional_or_conspiracy`; adverse effects sit between `causal` and
  `risk_or_safety`; a product's stated composition between `mechanism` and
  `other_factual`; compound sentences mixing prevalence and blame have no
  splitting rule.
- **Anecdotes with checkable content.** A personal story that carries a
  general mechanism claim, a clinician's "my patients" experience, and a
  quantified personal result ("my plaque went from X to Y") are excluded or
  extracted depending on the annotator.
- **ASR damage.** Brand names garbled beyond the "A G one" repair rule are
  included at low confidence, left as transcribed, or dropped.
