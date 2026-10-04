# Labeling with Cloudflare's Clef models

[Clef and Clef-flash](https://blog.cloudflare.com/clef-decision-models/) are
open-weight (Apache-2.0) decision models from Cloudflare: a Qwen backbone
(Qwen3.8-27B for Clef, Qwen3.5-9B for Clef-flash) with a small joint schema
head that returns a probability for every option of every typed question in
one forward pass. Their request and response bodies are TypeSafe's System One
API, so the TypeSafe labeling method (`docs/typesafe-labeling.md`) runs on them
unchanged once a local server speaks that API. This document is what they
measured on the benchmark and on real corpus windows (2026-10-03, GPUs 0-1 of
gpu313, one H100 per model), what was tried to make them work, and where they
fit.

## The short version

| | Clef-flash (9B) | Clef (27B) | Jev (`ts-v1`) | DeepSeek-V4-Flash, codebook rubric, 24k budget |
| --- | --- | --- | --- | --- |
| Topic F1, test (dev) | 0.595 (0.550) | 0.670 (0.672) | 0.641 (0.678) | - (0.731) |
| Frame F1, test (dev) | 0.557 (0.493) | 0.552 (0.555) | 0.661 (0.594) | - (0.763) |
| Evidence F1, test (dev) | 0.599 (0.616) | 0.631 (0.665) | 0.644 (0.688) | - (0.777) |
| Claim recall / precision, test | 0.61 / 0.63 | 0.71 / 0.67 | 0.79 / 0.62 | - (0.75 / 0.88 dev) |
| Product F1, test (dev) | 0.533 (0.555) | 0.535 (0.581) | 0.580 (0.580) | - (0.869) |
| Repeat self-agreement | 1.000 | 1.000 | 0.95 | 0.72 |
| Labeling, real corpus windows per hour | - | ~2,300 per H100 | hosted API, ~$3 per 1,000 | ~1,000 per H100 (3.9k per 4-GPU node) |
| Screening, corpus windows per second per H100 | **14.8** | 5.1 | - | - |

Clef columns are the TypeSafe method with its composition thresholds re-tuned
on dev for each model (`typesafe_tune`); the test numbers are free of that
tuning. Clef's is the shipped configuration, `benchmark/policies/clef-tuned.toml`
(pre-gate and coarse-to-fine localization); Clef-flash's is the method's own
questions re-tuned (`flash-v1`). Jev's numbers are from `ts-v1`, scored on its
own machine before the benchmark scoring fix in `c1c59f9`, so they are
approximate here. DeepSeek's are its best local configuration, re-scored with
the fixed scorer, and exist for dev only.

Three findings:

1. **Clef (27B) is a Jev-class labeler, not an LLM-class one.** Under the
   method built for Jev it is level with Jev on topics (test F1 0.67-0.70
   across configurations against 0.64, at precision 0.78-0.83) and on claims,
   and trails it on frames and products. It is well below the current best
   DeepSeek configuration on every axis but topic precision. Clef-flash is a
   step below both on everything that needs localization.
2. **As a full labeler it is fast only where it is conservative.** Clef has no
   generation, but the method asks hundreds of typed questions a window, and
   Clef's schema format costs ~116 tokens a question, 32 of them the question.
   On real corpus windows the shipped policy averages 11k tokens a window,
   ~2,300 windows an hour on an H100, because 74% of windows stop at the
   method's health gate. That gate is precise, not exhaustive: on the corpus it
   keeps only 86.5% of DeepSeek's substantive detections. A recall-oriented
   gate passes about 67% of windows, which puts Clef at ~1,000 windows an hour,
   no faster per GPU than DeepSeek and below it in quality.
3. **Clef-flash is a viable fast screen in front of the LLM labeler.** One
   1.4k-token question per window, ~53,000 windows an hour on one H100 (the
   whole 328k-window corpus in about six GPU-hours). On 6,723 real corpus
   windows that DeepSeek had labeled, the broad health gate at 0.2 passes 58%
   of windows and keeps 99.2% of substantive detections, 99.5% of claims,
   99.5% of ad detections and 98.8% of products. What it loses is passing
   mentions (95.7% kept). The 42% of windows it skips are the cheap ones for
   DeepSeek too, so the saving is about a quarter of DeepSeek's decode work,
   not 42%. Clef (27B) is no better at this: corpus AUROC 0.870 against 0.901,
   at a third of the speed.

## Running Clef locally

`analysis/serving/clef_server.py` serves one model on one GPU at
`/v1/systemone`, wrapping the model card's own `joint_schema_model.py`. Three
things in the release code had to be worked around:

- **Silent state truncation.** `encode_record` cuts the *state* to fit
  `max_length` (default 16,384) without a word. A localization request is
  30-60k tokens, so the transcript would have been cut and the questions about
  its missing passages answered anyway. The server encodes at the 64k context
  and never accepts a record at the length limit; a request too long for one
  pass is split into the fewest passes that fit, each holding the whole state.
- **The processor needs torchvision** for its video path. Text requests only
  need the tokenizer, so only that is loaded.
- **Kernel autotuning stalls.** The linear-attention kernels
  (`flash-linear-attention`) autotune per length bucket and per batch size,
  about ten seconds each, which put ten-second stalls into the first windows of
  every run. The server warms every bucket and batch size before serving and
  `TRITON_CACHE_AUTOTUNING=1` keeps the results across restarts.

Short requests are batched (up to 16, 32k padded tokens); long ones run alone,
where one sequence already saturates the GPU. Steady-state prefill is ~19k
tokens/s for Clef-flash and ~7k for Clef. Clef-flash takes ~20 GB of memory
plus activations (28 GB peak at 63k tokens); Clef ~54 GB plus activations, one
model per H100. Outputs are deterministic: two repeats of the benchmark agreed
exactly.

Differences from Jev that matter to the method:

- Clef decides the questions of one pass **jointly** (the head attends across
  fields), where Jev answers each independently. How questions are grouped
  into requests can therefore change answers. It mattered less than expected
  (below).
- The state is rendered with sorted keys, so state key order is not a lever
  as it was on Jev (`note`, `passages`, `subjects` happen to sort into the
  method's order).
- Each question's id is part of the prompt, and every `noul` carries default
  descriptions for `true` and `false`.

## Labeling quality

All runs use the benchmark's v6 taxonomy and `typesafe-cascade-v1` questions;
`benchmark/runs/<name>/scorecard.md` has each in full.

| run | policy | topic F1 dev / test | frame | evidence | claim R / P (dev) | product | tokens / window |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `flash-v1` | Jev's, unchanged | 0.531 / 0.569 | 0.504 | 0.479 | 0.40 / 0.75 | 0.509 | 95k |
| `flash-v1` | re-tuned | 0.550 / 0.595 | 0.493 | 0.616 | 0.61 / 0.65 | 0.555 | 95k |
| `flash-v3` | fan-out 0.1, pre-gate, refine; re-tuned | 0.537 / 0.568 | 0.499 | 0.582 | 0.57 / 0.67 | 0.525 | 98k |
| `clef-v1` | Jev's, unchanged | 0.660 / 0.697 | 0.451 | 0.516 | 0.52 / 0.73 | 0.519 | 80k |
| `clef-v1` | re-tuned | 0.660 / 0.697 | 0.542 | 0.638 | 0.69 / 0.68 | 0.531 | 80k |
| `clef-v2` | fan-out 0.1, pre-gate; re-tuned | 0.669 / 0.671 | 0.537 | 0.653 | 0.68 / 0.69 | 0.561 | 116k |
| `clef-eff` | pre-gate, refine; re-tuned (`clef-tuned.toml`) | 0.672 / 0.670 | 0.555 | 0.665 | 0.71 / 0.67 | 0.581 | 63k |
| `clef-eff-short` | as `clef-eff`, plus `short_ids` and short `noul` options; re-tuned (dev only) | 0.645 / - | 0.561 | 0.695 | 0.72 / 0.65 | 0.596 | 53k (dev) |

Frame, evidence and product columns are dev soft F1 as in the scorecard.
Tokens are the mean over the benchmark's corpus strata, which are much denser
in health content than the corpus.

What re-tuning changed for Clef: Clef's probabilities run lower than Jev's.
On `clef-v1` the frame and evidence seeds fell from 0.6/0.7 to 0.5 and the
claim threshold from 0.6 to 0.4, and nothing moved on topics, where Jev's
thresholds were already Clef's best. On `clef-eff`, with the window-threshold
grid extended below Jev's 0.3, every axis took a window threshold of 0.1 and
the claim threshold 0.4 again; those overrides are
`benchmark/policies/clef-tuned.toml`. Composition thresholds are free to
re-tune from stored judgments (`typesafe_tune`, `clef_quick`).

### Where the errors come from

`analysis/benchmark/clef_signal.py` reads each stage's raw probabilities
against the gold before any threshold (dev):

| stage | Clef-flash | Clef |
| --- | --- | --- |
| health gate, AUROC (window has gold; dev incl. rare-label windows) | 0.987 | 0.982 |
| label screen, AUROC (window x label) | 0.969 | 0.958 |
| gold labels kept at fan-out 0.3 | 82% | 75% |
| unit-level AP: topic / frame / evidence / claim | 0.62 / 0.38 / 0.48 / 0.67 | 0.71 / 0.49 / 0.55 / 0.73 |

Window-level judgments are as good as Jev's (0.98 and 0.96-0.98 in its
document). The weak stage is localization: which passages carry a label. That
is where Clef beats Clef-flash, and where both lose to the LLM.

The fan-out looked like a second limit (at Jev's 0.3, Clef localizes only 75%
of the gold labels, against Jev's 96-98%), so `clef-v2` lowered it to 0.1
(94% kept). Topic recall rose from 0.54 to 0.61, but precision fell from 0.77
to 0.70, test F1 went down, and a window cost 1.5x the tokens: the labels the
screen half-saw are mostly ones whose spans localization then gets wrong.

### Request shapes that did not help

Clef decides a pass jointly and reads ids and keys as text, so the request
shapes the method inherited from Jev were tested against alternatives on 40 dev
health windows with the localized labels held fixed
(`analysis/benchmark/clef_probe.py`, Clef-flash, unit-level AP):

| shape | tokens / window | topic | frame | evidence | claim |
| --- | --- | --- | --- | --- | --- |
| the method's (one request per passage grid, all labels) | 125k | 0.532 | 0.300 | 0.364 | 0.649 |
| one request per label | 148k | 0.494 | 0.287 | 0.400 | 0.674 |
| one request per passage, passage as the whole state, definition inline | 154k | 0.548 | 0.317 | 0.335 | 0.549 |
| one `choice` per label over the passage keys | 36k | 0.305 | 0.227 | 0.387 | 0.674 |

None is better overall. Pointer resolution is not the problem (the focus shape,
which has no pointers, scores the same), mixing labels in one joint decision is
not the problem (per-label requests score the same), and a `choice` over
passage keys does not localize -- the counterpart of Jev's array-index finding.
Splitting the 94-label screen into one request per axis made no difference
either (label AUROC 0.963 against 0.962).

## Throughput and cost

Clef bills nothing, but it is not free: everything is prefill, and the method
asks a great many questions. Clef's schema format wraps each in a field header
and two option descriptions, so a localization `noul` costs ~116 tokens of
which the question is 32; a claim question 194; a screening question 189.

| stage (Clef, `clef-v1`, per benchmark window) | tokens |
| --- | --- |
| screen (94 labels + 3 gates) | 18.7k |
| localize topics (3-unit passages) | 22.0k |
| localize frames, evidence, claims, products (unit by unit) | 45.6k |
| attributes | 8.9k |

Three policy options (`typesafe_labeling.Policy`, all off by default, so Jev
runs and fingerprints are unchanged) reduce this:

- `pregate`: the three window gates are asked alone first (1.5k tokens) and a
  window under the health gate stops there instead of after the 18.7k-token
  screen. The gate is also better asked alone (benchmark AUROC 0.980 against
  0.957 beside the 94 labels).
- `refine`: frames, evidence, claims and products are localized over 3-unit
  passages first and unit by unit only inside passages at `refine_threshold`
  (0.2). On Clef-flash dev it cut unit-localization tokens from 65.8k to
  41.6k a window (-21% per window overall) for about -0.015 F1 on frames,
  claims and products before re-tuning.
- `short_ids` and `noul_options = "short"`: question ids sent as `q0000` and
  the `noul` options as "Yes." / "No.", which takes a localization question
  from ~116 to ~96 tokens. On Clef dev, both runs re-tuned, it cut 17.5% of the
  tokens (64k to 53k a window) and traded evenly: topics -0.027, evidence
  +0.030, the rest within 0.015. Kept as options; not in `clef-tuned.toml`,
  since topics are Clef's strongest axis.

The benchmark over-states what a corpus pass costs: its strata are far denser
in health content than the corpus. `analysis/benchmark/clef_corpus_cost.py`
labels consecutive windows of real episodes under the production 84-label
taxonomy (which this also validated end to end: 300 windows, strict
validation, no rejections). With `clef-efficient.toml` on Clef:

| | real corpus windows (300, whole episodes) |
| --- | --- |
| stopped at the gate (1.5k tokens each) | 73.7% |
| tokens per window that went on | 37.5k |
| tokens per window, all | 11.0k |
| at Clef's ~7k tokens/s | ~1.6 s, ~2,300 windows an hour per H100 |
| windows with any output | 19.7% (DeepSeek's run: 35.0%) |

That speed is the method's health gate doing the work, and on the corpus that
gate is not exhaustive. Asked alone at 0.2 (the pre-gate), Clef's keeps
86.5% of DeepSeek's substantive detections, 93.2% of its claims, 77.4% of its
products and 65.6% of its passing mentions (`screen-clef-report.md`). The gate
is the same inside the method's ordinary screen, so this applies to `clef-v1`
too, and plausibly to Jev, whose document measured its gate on the benchmark,
where empty windows are few and chosen. With the broad gate below at 0.2
instead, ~67% of corpus windows would go on: at most ~26k tokens a window
(the extra windows are marginal ones, likely cheaper than 37.5k), about 1,000
to 1,500 windows an hour per H100 -- DeepSeek's rate per GPU, at lower quality.

## Screening in front of the LLM labeler

The question is whether one cheap request per window can decide which windows
go on to full labeling. `analysis/benchmark/clef_screen.py` measures screen
designs against two references: the benchmark gold (160 windows of the corpus
strata, 30 without gold) and 6,723 real corpus windows from 447 whole episodes
that DeepSeek-V4-Flash labeled at high effort (the `topic-clips-claims-products-v5`
prompt, `podcast-misinfo/outputs/fullrun`), 30% of which got any annotation.

| screen (Clef-flash) | tokens | benchmark AUROC | corpus AUROC |
| --- | --- | --- | --- |
| the method's health gate inside the full 94-label screen | 18.7k | 0.957 | - |
| the method's three gates, alone | 1.5k | 0.980 | 0.886 |
| the method's health gate alone | 1.3k | 0.969 | - |
| broad health gate (below) | 1.4k | 0.983 | 0.901 |

The method's gate was written to be precise: it names physical health, and its
"false" option says incidental health words do not count. On the corpus that
cost recall where it matters to a screen: three quarters of the DeepSeek
annotations it dropped were passing mentions, and half were mental health
(therapy, trauma, "gaslighting" in relationship-advice shows), a subject the
question never names. The broad gate names mental health, therapy, sleep, sex
and reproduction, drugs and alcohol, counts passing mentions and excludes only
idioms. Corpus atoms kept by what DeepSeek said they were:

| broad gate | corpus windows passed | substantive | ad | passing | claims | products |
| --- | --- | --- | --- | --- | --- | --- |
| 0.1 | 77.0% | 99.9% | 100.0% | 99.1% | 100.0% | 100.0% |
| **0.2** | **58.3%** | **99.2%** | **99.5%** | **95.7%** | **99.5%** | **98.8%** |
| 0.3 | 46.7% | 97.3% | 96.7% | 90.4% | 98.0% | 90.1% |

On the benchmark gold the same gate at 0.2 keeps 99.8% of gold atoms (96% of
gold windows) and passes 6 of the 30 empty windows. The windows it passes that
DeepSeek left empty are mostly not health content that DeepSeek missed: a host
sleeping on a couch, *Oregon Trail*'s "Health is good", a picky eater on a date.
The corpus AUROC of 0.90 is a fair figure for the gate, not an artefact of the
reference.

Clef (27B) is not a better screen. Its broad gate scores a little higher on
the benchmark (AUROC 0.987) but lower on the corpus (0.870); at the same
corpus pass rate (gate 0.3, 59.7% passed) it keeps 98.6% of substantive
detections and 99.0% of claims, against Clef-flash's 99.2% and 99.5% at 58.3%,
and it screens 5.1 windows a second to Clef-flash's 14.8.

Throughput: 6,723 windows in 453 s on one H100 (14.8 a second), compute-bound
at ~22k tokens/s, so the 328k-window corpus is about six GPU-hours. At 0.2 it
skips 42% of windows, but those are the windows DeepSeek labels most cheaply:
in that run an empty window still cost 5.4k output tokens (mostly reasoning)
against 15.8k for a labeled one, so the skipped windows carry 25% of its output
tokens (13% at gate 0.1, 35% at 0.3). DeepSeek is decode-bound, so that is
about a quarter of its GPU time: ~85 of ~340 GPU-hours for the corpus at the
measured 3.9k windows an hour per four-GPU node, for six GPU-hours of
screening. (That run batched four windows a request, so its per-window usage
is approximate.)

## Where it fits

1. **A screen, yes, deliberately.** Clef-flash with the broad gate is cheap,
   fast, deterministic and measured. The pipeline's stated design has no gate
   (`docs/typesafe-labeling.md`), so adopting one is a decision rather than a
   default; the evidence for it is the table above, and its misses can be
   audited on any sample by labeling what it rejected. The reference here is
   DeepSeek's older v5 prompt; the codebook prompt labels more (topic recall
   0.66 against 0.51 on the benchmark), so the operating point should be
   re-checked against a corpus sample labeled with it before adoption.
2. **A full labeler, no.** Clef is at Jev's level, Clef-flash below it, both
   well below the current DeepSeek configuration. Clef is about twice
   DeepSeek's corpus rate per GPU only with the method's precise gate, which
   drops a seventh of DeepSeek's substantive detections; with a gate that
   keeps them, it is no faster. The case Jev's document makes for an
   exhaustive detection layer at $3 per thousand windows does not carry over:
   Clef's cost is GPU time, and the method asks too many questions for that to
   be small.
3. **Topic prevalence, maybe.** Clef's topic detection is its best axis (test
   F1 0.67-0.70 at precision 0.78-0.83, no run-to-run noise). If window-level
   label presence is enough -- prevalence estimates, routing -- the screen
   request alone (label AUROC 0.96 on dev, 18.7k tokens) is a quarter of a
   full benchmark window's cost, and needs no localization at all.
4. **Re-check the method's own gate before a corpus run, on any model.** On
   real windows the TypeSafe method's health gate at 0.2 drops 13.5% of
   DeepSeek's substantive detections and a third of its passing mentions
   (measured on Clef; Jev's gate was only measured on the benchmark). The
   broad wording in `clef_screen.HEALTH_BROAD` is the obvious replacement; it
   is not wired into the method, because it changes Jev's question set.

## Running it

```bash
# serve (one model per GPU; the first start warms the kernels, ~10 minutes)
analysis/serving/serve-clef.sh clef-flash 0 8301
analysis/serving/serve-clef.sh clef 1 8302

# benchmark, score, re-tune, quick re-scores from stored probabilities
.venv/bin/python -m analysis.benchmark run --name clef-eff \
    --pipeline-config benchmark/pipeline-clef.toml --repeats 1 \
    -- --typesafe-policy benchmark/policies/clef-efficient.toml
.venv/bin/python -m analysis.benchmark score benchmark/runs/clef-eff --show-test
.venv/bin/python -m analysis.benchmark.typesafe_tune benchmark/runs/clef-eff --out /tmp/tuned.json
.venv/bin/python -m analysis.benchmark.clef_quick benchmark/runs/clef-eff --policy @/tmp/tuned.json

# stage diagnostics and request-shape probes
.venv/bin/python -m analysis.benchmark.clef_signal benchmark/runs/clef-eff --split dev
.venv/bin/python -m analysis.benchmark.clef_probe benchmark/runs/clef-eff \
    --endpoint http://127.0.0.1:8302/v1 --model clef --shapes grid focus

# screening: benchmark gold and corpus windows, then the report
.venv/bin/python -m analysis.benchmark.clef_screen run --source corpus \
    --endpoint http://127.0.0.1:8301/v1 --model clef-flash --variants broad \
    --corpus /scratch/fparker9/podcasts/podcast-misinfo/outputs/fullrun \
    --out benchmark/runs/clef/screen-flash-corpus.jsonl
.venv/bin/python -m analysis.benchmark.clef_screen report benchmark/runs/clef/screen-*.jsonl \
    --store /scratch/fparker9/podcasts/podcast-misinfo/outputs/fullrun/labels.sqlite
```

Production labeling uses `analysis/topic-labeling-typesafe.toml` with
`api_base` pointed at the local servers and `model` set to `clef` or
`clef-flash`; a local endpoint needs no key. The serving dependencies are the
`clef` dependency group (`flash-linear-attention`, `accelerate`).
