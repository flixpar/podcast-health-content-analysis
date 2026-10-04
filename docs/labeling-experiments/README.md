# Labeling throughput and quality experiments (2026-09-12 to 09-14)

What was tried to make the transcript labeler faster without making it worse,
on the local vLLM servers, scored with `python -m analysis.benchmark` (benchmark
round 2, 260 items, 4 annotators). The shipped result is in
`analysis/topic-labeling.toml` and `docs/topic-labeling-method.md`; this page is
the record of how it was reached. Run directories are under `benchmark/runs/`
(gitignored); the three analysis reports next to this file were written from
them, and their scripts are in `scripts/` (run from the repository root, they
read `benchmark/runs/`).

Unless noted: DeepSeek-V4-Flash-0731, high effort, one window per request,
deltas are paired-bootstrap 95% intervals from `compare`, "dev" is the 176-item
dev split with two repeats, "s70" is a stratified 70-item dev sample
(`sample-dev70.jsonl`: 16 health_dense, 14 mixed, 10 null, 8 ad_read,
8 discourse, 10 rare_label, 4 synthetic) with two repeats.

## 1. Serving: the server was CPU-bound

With batch-4 requests and several runs at once the server held 900-1,800
decode tokens/s whatever the concurrency, with GPUs at ~35% and EngineCore at
one full core; a 1,800 s client timeout then abandoned requests the server kept
generating (about 73% of five hours of generation). py-spy showed 92% of
EngineCore time in `is_reasoning_end`: vLLM 0.29's parser-engine reasoning
adapters rescan each structured-output request's whole token history on every
decode step while it is still thinking. `analysis/serving/fast_reasoning_end_plugin.py`
checks only the step's new tokens.

Aggregate decode on one 4x H100 node (`benchmark/runs/loadtest.py`, labeling-shaped
requests, high effort, 16k-32k outputs):

| concurrent requests | before | after |
| --- | --- | --- |
| 64 | 1.9k tok/s | 3.4k tok/s |
| 128 | -- | 5.3k |
| 192 | -- | 6.3k |
| 256 | -- | 7.3k (KV 46-57%) |
| 512 | -- | 10.3k (KV 92% at 32k outputs, no preemption) |

## 2. Request shape and validation

- Batching (4 windows per request) is gone: at 44k output tokens batch-4 requests
  truncated on dense windows, and one bad annotation or truncation discarded all
  four; 61% of output tokens went to rejected responses.
- One window per request with an 80k output budget and `--validation lenient`
  (repair a quote just outside its span, drop unrepairable annotations) on s70:
  32.8k -> 24.0k output tokens per accepted window (-27%), first-attempt
  acceptance 75% -> 97%, no significant quality change. Lenient widened 63 spans
  and dropped 6 annotations across 140 windows.
- A prompt telling the model to keep quotes inside spans did not reduce
  rejections (36 vs 38). Asking for short quotes, summaries and rationales cut
  tokens 14% but cost claim recall -0.105 [-0.19, -0.02] under lenient.

## 3. Reasoning

| setting | tokens per window | quality against high, unbounded |
| --- | --- | --- |
| thinking off (s70) | 1.9k | topic F1 -0.16, frame -0.39, evidence -0.47, claim recall -0.23 |
| `low` effort (s70) | 10.6k | topic recall -0.16, claim recall -0.14, precision up |
| budget 4k (s70) | 5.2k | topic F1 -0.07, frame -0.18, evidence -0.17, claims -0.14 |
| budget 8k (s70) | 8.4k | frame -0.10, evidence -0.09, claim recall -0.09 |
| budget 12k (s70) | 11.4k | evidence -0.05, others trending down |
| budget 16k (dev) | 13.7k | frame F1 -0.073 [-0.106, -0.040], claim recall -0.057 [-0.109, -0.009] |
| budget 24k (dev, codebook prompt) | 19.3k vs 22.6k | no significant change (claim precision -0.023) |

`--thinking-token-budget` works only on Chat Completions; Chat Completions and
Responses label indistinguishably (s70 control). The 16k loss sits entirely on
windows whose unbounded thinking ran past 16k, mostly mild frames
(debunking, naturalness, commercialization) left off spans that keep their
topic; see `thinking-budget.md`. Thinking length tracks how much a window
contains (r = 0.89 with the reference annotation count), not its ambiguity.

## 4. Prompt

The hand-written rubric paraphrased the benchmark codebook and never listed the
`claim_type` or `product_type` values. Using `analysis/benchmark/codebook.md`
verbatim as the rubric (dev, unbounded thinking):

| metric | old rubric | codebook | delta |
| --- | --- | --- | --- |
| topic F1 | 0.674 | 0.723 | +0.049 [+0.025, +0.072] |
| topic recall | 0.568 | 0.676 | +0.108 [+0.076, +0.141] |
| topic precision | 0.830 | 0.777 | -0.053 [-0.087, -0.022] |
| claim recall | 0.687 | 0.770 | +0.083 [+0.045, +0.121] |
| frame, evidence, product F1, claim precision | | | not significant |

Claim type agreement went from 0.36 to 0.81 and product type from 0.60 to 0.96,
at the same token cost. This is now the production rubric.

A co-label rule on top of the codebook ("label both the intervention and the
outcome topic; add a population topic", `analysis/prompts/rubric-codebook-colabel.md`),
dev, four repeats per arm, 24k budget: topic F1 +0.043 [+0.030, +0.056], recall
+0.118, precision -0.040, nothing else moved, same tokens. It was **not
adopted**: the rule copies the Opus annotators' habit, and the gain is
agreement with Opus (topic F1 against opus-r1/r2 0.665/0.647 -> 0.684/0.683)
bought with agreement with Sonnet (0.621/0.606 -> 0.547/0.536); mean pairwise
agreement with the four annotators fell 0.635 -> 0.612. It becomes a candidate
if the gold stops letting the two Opus passes form required atoms on their own.

Whether a much more detailed per-category codebook would help is analysed in
`spec-vs-model.md`: DeepSeek already agrees with individual annotators at the
cross-family (Opus vs Sonnet) level on every axis, 78% of required gold is in
labels where it is within 0.05 of that, and 77% of the atoms no model finds are
supported only by the two Opus passes. The remaining gap is mostly how
exhaustively to label, run-to-run noise and span granularity, not missing
definitions.

## 5. Other models

Same s70 sample, lenient validation, against DeepSeek high (`cross-model.md`):

| model | tokens per window | decode at c=256 | quality |
| --- | --- | --- | --- |
| gpt-oss-120b, high (TP4) | 11.2k | 10.0k tok/s | topic F1 -0.18, frame -0.42, evidence -0.31, claims -0.17 |
| gpt-oss-120b, medium | 3.0k | | worse still |
| Qwen3.5-35B-A3B-FP8, thinking (DP4) | 10.3k | 11.7k tok/s | topic recall 0.28 vs 0.59, frame -0.36, claims -0.37 |
| Qwen3.5-35B-A3B-FP8, no thinking | 1.3k | | far worse |
| Gemma-4-26B-A4B-it (DP4, Chat Completions) | 41.7k incl. 80% waste | 11.3k tok/s | frame -0.35, evidence -0.36, claims -0.23; 29% of attempts ran away to 80k |
| Qwen3.8-Flash-Next-FP8 | -- | ~12 tok/s | OOM at startup when compiled; eager with PLE CPU offload unusable |

All of them mostly under-label: they tag the topic and leave frames and
evidence off. Gemma 4 fails on vLLM's Responses endpoint (truncation reported
at a few thousand tokens); gpt-oss needs `TIKTOKEN_ENCODINGS_BASE` on nodes that
cannot reach the tiktoken blob store.

## 6. Production throughput

1,859 windows prepared from 120 random episodes of the 2026-09-04 corpus, one
DeepSeek node, 384 concurrent requests, lenient, old rubric:

| config | wall time | steady windows/hour | mean tokens per window |
| --- | --- | --- | --- |
| no budget | 38.9 min | ~3,900 | 6.8k (median 1.3k; 54% of windows get no labels) |
| 16k budget | 24.0 min | ~4,750 | 5.5k |

Real windows are far cheaper than benchmark windows; only 6% think past 24k.
Replaying the unbounded run's reasoning tokens under a cap predicts the 16k run
within 1% (5,558 vs 5,487) and puts 24k at ~6.4k tokens per window. With the
codebook prompt (~3% more tokens) that is ~4,000 windows/hour per node. The
corpus is 132,412 episodes and about 2.03M windows (15.4 per episode, from a
1,000-episode `prepare`), so a full labeling pass is ~510 node-hours: about
three weeks on one node, 10-11 days on two.
