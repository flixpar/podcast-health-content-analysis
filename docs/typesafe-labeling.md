# Labeling with TypeSafe's System One API

`label --api typesafe` labels transcript windows with
[TypeSafe](https://docs.typesafe.ai)'s Jev model instead of a generative one. It
writes the same `labels.sqlite` and `window_labels.jsonl.zst`, through the same
validator, so `merge`, `sample` and the benchmark read it unchanged. This
document records the flat-scheme method and its historical benchmark
(2026-09-17, `jev-1.13.0`). The cascade supports only the legacy flat
topic/frame/evidence contract. It rejects hierarchical v7/v8 before endpoint
discovery or inference; the current granular workflow remains the generative
pipeline in [labeling-v7.md](labeling-v7.md).

Recorded results below used the 91-label flat v6 benchmark. They do not validate
the production 84-label source or the granular schemas. The separate production
config explicitly selects `docs/original/topics.md` for the 84-label source.

## The short version

| | DeepSeek-V4-Flash, `high` (hosted) | TypeSafe cascade v1 |
| --- | --- | --- |
| Topic F1 / precision / recall (dev) | 0.655 / 0.90 / 0.51 | 0.678 / 0.77 / 0.61 |
| Frame F1, evidence F1 (dev) | 0.637, 0.682 | 0.602, 0.704 |
| Claim F1 / precision / recall (dev) | 0.646 / 0.98 / 0.48 | 0.684 / 0.64 / 0.74 |
| Product F1 (dev) | 0.786 | 0.575 |
| Mean span IoU on matched topics | 0.74 | 0.39 |
| Null windows: atoms per window, share with output | 0.10, 6% | 0.77, 27% |
| Dev windows left unlabeled | 15 of 105 (mostly the $20 spend cap; a few truncated or rejected) | 0 of 105 (0 of 260 overall) |
| Self-agreement between repeats (topic pairwise F1) | 0.71 | 0.95 |
| Cost per window | $0.054 | $0.003 |
| Seconds per window | ~200 | ~3.5 |
| `claim_text`, product-name repair, `summary` | written by the model | not possible: copied or templated |

Each column is scored over the windows that run labeled, so DeepSeek's is over
90 of the 105; the paired comparison further down, over the items both
labeled, is the like-for-like read and says the same thing.

It finds what the DeepSeek run finds, and more of it, at about one
twentieth of the price and one fiftieth of the time, with nothing rejected or
truncated and almost no run-to-run noise. It pays for that in precision on claims, in span
boundaries, in products, and in everything that has to be *written*. The
held-out test split, which no candidate had been run on before, agrees with
dev (topic F1 0.641, claims 0.695, frames 0.668, evidence 0.652, products
0.542).

Against the benchmark's ceilings it sits where the DeepSeek runs sit: at the
conservative-annotator tier (leave-one-out topic F1 ~0.66) and about 0.2 below
the exhaustive one (~0.87).

## Why it is a method and not a request shape

A System One model does not generate text. A request is a `state` (any JSON)
and a map of typed questions about it; the answer to each is a probability
(`noul`, a yes/no) or a distribution over options you supplied (`choice`).
Questions in one request are answered independently and in parallel, a request
takes about half a second whatever it holds (up to ~64k tokens), and only input
tokens are billed ($0.042 per million).

So there is no rubric-and-schema prompt to send. The labeling task has to be
rebuilt as questions a person could answer at a glance, with code doing
everything else. `analysis/typesafe_labeling.py` does it in four stages:

1. **Screen** (one request). State: the window as plain text. One `noul` per
   taxonomy label ("does any part of `transcript` discuss this health
   subject?", with the label's name, definition and example terms), plus three
   gates: any health content, any checkable claim, any named product. A window
   whose health gate is under 0.2 is empty and stops here.
2. **Localize** (one to three requests). For every label that screened at 0.3
   or more, one `noul` per passage: is `passages.p007` part of a stretch that
   discusses the subject described in `subjects.s03`? Topics are asked over
   three-unit passages; frames, evidence signals, claims and products unit by
   unit.
3. **Compose** (code). Per label, units at the extend threshold that hold one
   at the seed threshold become a span; spans a unit apart are joined. This is
   the codebook's splitting rule made deterministic. The catch-all topic yields
   to a listed topic on the same stretch; a product is kept only where a topic
   span reaches it; a claim unit that does not end its sentence joins the next.
4. **Attribute** (one request). State: the composed spans with two units of
   context each side. A `choice` per closed-set field: discourse role,
   relevance, claim type, product type, mention role. Expressed certainty is a
   `choice` among only the levels whose marker words code found in the span
   (the codebook's own procedure: find the markers, then read the level off
   them; no markers is `unhedged` without asking). Product names are selected,
   not written: code proposes capitalised token runs and URL names, and one
   `noul` per candidate asks whether it names a specific product.

What the schema wants as prose is copied or templated. `evidence_quote` is the
highest-probability unit of the span. **`claim_text` is the claim's own units,
verbatim** -- faithful by construction, but pronouns are not resolved and the
sentence is not self-contained. `summary` and `rationale` are fixed strings
naming the label and the method. `confidence` is Jev's probability for the
span's best unit, so the scorecard's calibration row reads Jev directly (AUROC
0.72 for predicting a true positive; DeepSeek's self-reported confidence
scores 0.65).

Every probability is kept in `<output-dir>/typesafe_judgments.jsonl`.
Each sidecar record is flushed to disk before its window's success checkpoint
is committed. An interrupted checkpoint can append the same window again on
resume; offline recomposition uses its last record.
Thresholds are policy, and `typesafe_labeling.compose_result` rebuilds a result
from stored judgments under a different policy with no requests -- which is how
the thresholds were tuned, and how they can be re-tuned for a different
precision/recall trade without re-labeling a corpus.

## What was learned about asking Jev things

These came out of probing, each measured against the gold on dev items. They
are recorded because the vendor's documentation does not say them and each one
decided part of the design.

- **Array indexes do not localize; keys do.** With the state as
  `{"units": [...]}` and questions about `units[37]`, probabilities were flat
  across the window: every unit got the window-level answer. Indexing is
  counting, and the model card says Jev does not count. With keyed passages
  (`passages.p037`) or inline line tags, the same questions localized sharply.
- **Definitions belong in the state, referred to by key.** Repeating a label's
  definition in each of its ~80 unit questions cost 154k tokens a window.
  Putting definitions under `subjects` once, and the "judge this passage only"
  instruction in a state-level note, cost 74k and scored the same F1 on every
  axis. Claims are the exception (F1 0.74 inline, 0.70 by key), so the claim
  question keeps its include/exclude text inline.
- **State key order moves answers.** Swapping `subjects` before `passages`
  moved probabilities by 0.07 on average; two sends of an identical request
  differ by 0.02 (max 0.09). Jev is not deterministic, but it is close: repeat
  runs agree at 0.93-0.97 pairwise F1, against 0.71 for DeepSeek.
- **Presence questions over-fire on windows with no health content.** Asked
  label by label, the dev null windows averaged three labels at 0.3 or more,
  and all but two had at least one. One window-level question, "does any part
  discuss health...",
  separates windows with gold from empty ones at AUROC 0.98 and removed
  two-thirds of the null-window output at no cost in F1.
- **Letting topics compete hurt.** A `choice` among the topics overlapping a
  span ("which is this mainly about?") raised topic precision to 0.95 and cut
  recall to 0.39: the gold is exhaustive and multi-label, and a choice is not.
  It is not in the method.
- **Passage size barely matters for F1.** Unit-level topic localization scored
  0.670 against 0.668 for three-unit passages, for 26% more tokens.
- **The window screen is strong.** Label presence per window: AUROC 0.98
  (topic, frame), 0.96 (evidence); at the 0.3 fan-out threshold it keeps 96-98%
  of gold labels and about 14 labels a window.

## Reading the numbers

Headline strata, dev split, mean of two repeats; `compare val-high ts-v1` is a
paired bootstrap over the 108 items both labeled.

| metric | DeepSeek `high` | TypeSafe | delta (95% CI) |
| --- | --- | --- | --- |
| topic F1 (strict) | 0.660 | 0.683 | +0.023 [-0.014, +0.065] |
| topic recall (required) | 0.519 | 0.613 | +0.095 [+0.048, +0.143] |
| topic precision | 0.908 | 0.772 | -0.136 [-0.179, -0.093] |
| frame F1 (strict) | 0.629 | 0.600 | -0.029 [-0.076, +0.021] |
| evidence F1 (strict) | 0.679 | 0.707 | +0.028 [-0.030, +0.085] |
| claim recall (required) | 0.478 | 0.709 | +0.231 [+0.186, +0.271] |
| claim precision | 0.971 | 0.645 | -0.326 [-0.357, -0.296] |
| product F1 (strict) | 0.794 | 0.559 | -0.235 [-0.300, -0.165] |

Detection F1 is a tie on all three axes; the two labelers get there from
opposite sides. TypeSafe's gain is concentrated where DeepSeek was weakest:
`mixed` windows (topic F1 0.45 to 0.66) and `ad_read` (0.69 to 0.84).

Caveats that matter when reading this:

- The TypeSafe thresholds were tuned on the dev split; DeepSeek's prompt was
  not. The test-split numbers above are the ones free of that, and they are
  0.02-0.05 lower on topics and evidence, higher on frames and claims. The
  test split has now been seen once by this method: further iteration on it
  has to be judged on dev until there is a fresh held-out set.
- **Span boundaries are coarse.** Mean IoU against the tight reference span is
  0.39 on topics (DeepSeek 0.74). The scorer credits a span that contains, or
  sits inside, the reference, so F1 does not punish this; clip extraction
  would. The largest single error class is `miss: topic: span_only` -- the
  label was found in the window but one long span covered what the references
  split into several detections.
- **Claim precision is 0.64.** A third of extracted claims match no reference
  claim (mostly `different_claim`: a neighbouring sentence, or a claim the
  annotators merged into another). For a high-recall candidate stage feeding
  `verify` that is the cheaper error, but it is not free: verification cost
  scales with candidates.
- Attribute agreement on matched atoms is at the annotators' own level for
  discourse role (0.83-0.93 exact), relevance (0.81), product type (0.91) and
  mention role (0.87), and a little under it for claim type (0.73 against
  alpha 0.79). Expressed certainty agrees exactly 75% of the time but its
  weighted kappa is 0.47 against the annotators' alpha of 0.75: the lexicon
  proposes markers the annotators did not count, and "can" is not in it.
- Products: recall is limited by name candidates (a brand the ASR lower-cased
  and no URL spelled out is never proposed) and nothing repairs a garbled name.
- Null windows still get output 27% of the time (DeepSeek 6%). Eight of the 26
  dev null windows do carry gold, so part of that is correct; most is not.
- Contrast twins: targeted pass rate 0.44-0.56 (annotators 0.67-0.89), decoys
  1.0. Certainty perturbations are where it fails, consistent with the above.

## Cost and throughput

Measured on the benchmark run (260 windows, two repeats, concurrency 8):

| stratum | input tokens / window | requests / window | seconds / window | $ / 1,000 windows |
| --- | --- | --- | --- | --- |
| null | 26,900 | 2.2 | 1.2 | 1.13 |
| mixed | 54,500 | 4.1 | 2.6 | 2.29 |
| health_dense | 97,600 | 4.7 | 4.5 | 4.10 |
| all items | 73,400 | 4.2 | 3.5 | 3.08 |

Tokens by stage on a health window: screen 15k, topic localization 11k, unit
localization 38k, attributes 15k.

For the corpus (about 1.5M windows at the default overlap, roughly 70% of them
without health content) that is on the order of **$3,000 and three days** at
the published limits (1,200 requests a minute, 250k tokens a second), against
about $80,000 for DeepSeek `high` on its hosted API or about a month on the two
local nodes. These are extrapolations from 260 windows: the null share of the
real corpus and TypeSafe's rate limits, which they say move without notice,
both move the figure. The whole evaluation here, probing included, cost about
$5.30.

## Where it fits

Three uses, in the order the evidence supports them:

1. **Screening and triage in front of the generative labeler.** The screen
   request alone (15k tokens, $0.0006, half a second) separates windows with
   health content from those without at AUROC 0.98, and at a gate of 0.2 keeps
   99% of the windows that carry gold while passing 22% of the empty ones (105
   dev windows, 18 of them empty, so the second figure is soft). If ~70% of
   the corpus is empty, that removes roughly half of DeepSeek's bill without
   touching its output. This is a gate, and the pipeline's stated design is
   to have none, so it is a decision to take deliberately rather than a
   default: what separates it from a keyword gate is that its miss rate is
   measured against gold (1 of 87 gold-bearing dev windows at 0.2) and can be
   audited on any sample by labeling what it rejected. It also gives window-level label presence at AUROC
   0.98, which is enough for topic-prevalence estimates and for routing.
2. **The exhaustive detection layer.** For topic, frame and evidence
   prevalence -- the pipeline's first three dimensions -- it matches the
   generative labeler's F1 with higher recall, no truncation, near-perfect
   repeatability and calibrated probabilities, for a whole-corpus price that
   makes re-running under a new taxonomy or new definitions routine rather
   than a budget decision. Where clip boundaries matter, tighten spans with a
   generative pass over the flagged stretches only.
3. **Claim candidates, with a rewrite step.** Recall of 0.74-0.79 is well
   above DeepSeek's 0.48, but `claim_text` is a verbatim sentence, and `verify`
   retrieves evidence with it. Before this feeds verification, a generative
   model has to normalise the selected claims (a few sentences each, not
   windows), and the blinded claim sample has to confirm the precision is
   tolerable.

It is not a replacement for the generative labeler on product mentions, on
anything needing name repair, or wherever `summary` is read by a person.

Known gap in the run loop, shared with the other paid backends: a billing
error (HTTP 402) fails each window in turn and the run carries on to the end,
where a spent usage budget stops it. On a corpus run that is a great many fast
failures; they are durable and resumable, but a 401/402 should stop the run.

Not yet validated: labeling under the production 84-label taxonomy (the
benchmark's 91-label v6 was used throughout); the production `label` command
against the live API (its path is covered by an offline end-to-end test; the
account ran out of credit before a live smoke run); behaviour on `jev-latest`
after the pin moves.

## Running it

```bash
# benchmark: run, score, compare
export BENCHMARK_DIR=benchmark  # flat v1 specs, never benchmark/v2 for TypeSafe
.venv/bin/python -m analysis.benchmark run --name ts-v1 \
    --pipeline-config benchmark/pipeline-typesafe.toml --repeats 2 --split all
.venv/bin/python -m analysis.benchmark score local/benchmark/runs/ts-v1
.venv/bin/python -m analysis.benchmark compare local/benchmark/runs/val-high local/benchmark/runs/ts-v1

# re-tune composition thresholds from that run's stored probabilities (no requests)
.venv/bin/python -m analysis.benchmark.typesafe_tune local/benchmark/runs/ts-v1

# production: prepare a small run from the configured transcript directory
.venv/bin/python analysis/topic_labeling.py prepare \
    --config analysis/topic-labeling-typesafe.toml --output-dir /tmp/ts-smoke --limit 3
.venv/bin/python analysis/topic_labeling.py label \
    --config analysis/topic-labeling-typesafe.toml --output-dir /tmp/ts-smoke
.venv/bin/python analysis/topic_labeling.py merge \
    --config analysis/topic-labeling-typesafe.toml --output-dir /tmp/ts-smoke
```

The flat production taxonomy is compiled from the canonical tables in
`docs/original/topics.md`, selected explicitly by the TypeSafe config. Flat
benchmark inputs and rosters are maintained under `benchmark/`; generated
taxonomy, items, gold and runs live in ignored `local/benchmark/` (or the
configured `BENCHMARK_OUTPUT_DIR`). Follow [benchmark.md](benchmark.md) to
generate/restore those inputs; historical results are not shipped in a fresh
checkout. The local transcript directory must exist before
`prepare`; `label` reads the taxonomy, windows and prepare manifest it creates
in the same output directory.

`TYPESAFE_API_KEY` goes in `.env`. The run fingerprint is the pinned model, the
taxonomy, the sha256 of every question template
(`typesafe_questions_sha256`) and the whole policy; decoding settings are not
part of it. `--typesafe-policy FILE` overrides `typesafe_labeling.Policy` keys
from a TOML file; a bare number for a per-axis key applies to all three axes:

```toml
claim_threshold = 0.75          # fewer, surer claim candidates

[seed_threshold]
topic = 0.7
```

Keys in the first block of `Policy` decide which questions are asked, so
changing them needs a new run. The rest only decide how answers become
annotations. Spending is guarded like any paid endpoint:
`[provider.typesafe]` and `[model.typesafe."jev-1.13.0"]` in
`analysis/usage-limits.toml`, with the client backing off on 429 on a schedule
of its own.
