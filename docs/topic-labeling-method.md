# Podcast clip labeling and claim-verification method

## What the pipeline measures

`analysis/topic_labeling.py` exhaustively labels timestamped transcript spans
using the 84 labels in the two final tables of `topics.md`. Each table row
carries a written **definition** that governs the label; the keyword column is
examples only. The cross-cutting table carries an explicit **axis** column, so
no label's axis is inferred from its name. The dimensions are independent:

| Dimension | Values | Interpretation |
| --- | --- | --- |
| Topic | 49 parent health topics, plus `other_health_topic` | What the span discusses |
| Frame | 27 cross-cutting labels | How it is framed, including conspiracy, correction, MAHA, and commercialization |
| Evidence signal | 7 cross-cutting labels | How evidence or authority is invoked, including academic studies, mechanisms, extrapolation, experience, and credentials |
| Claim review | Atomic factual claims | High-recall candidates for later evidence verification |
| Expressed certainty | `absolute`, `unhedged`, `hedged`, `speculative` on every claim | How firmly the speaker put the claim, grounded in verbatim marker words |
| Product mentions | Named products with a type and a mention role | Which specific products are named, and whether as an ad, the speaker's own, a recommendation, a neutral mention or a criticism |

Every label and claim also records `discourse_role` as
`asserted_or_endorsed`, `questioned`, `reported_or_quoted`, `rebutted`, or
`unclear`. Labels record `relevance` as `substantive`, `passing`, or
`advertisement`; claims record a claim type such as causal, treatment,
risk/safety, mechanism, or institutional/conspiracy.

These are deliberately separate. A conspiracy frame is not necessarily a false
claim. Citing academic research does not make a claim true. Reporting or
rebutting a questionable claim is not endorsement. Expressed certainty is the
speaker's stance, coded from their words, and is distinct from the model's
`confidence`, which is only how sure the model is of its own coding. A product
mention is a fact about what was named, not a judgement that the passage is
commercial: the Commercialization frame and `relevance=advertisement` still
carry that, and the three can be cross-tabulated.

`possible_misinformation=true` means only that a material, externally checkable
claim was selected for evidence review. The first model does not predict truth.
This high-recall definition avoids asking a model with no evidence corpus to
decide which claims merely sound suspicious. A claim becomes a verified
misinformation finding only after the separate evidence step and any required
human review.

## Five-stage design

### 1. Prepare every transcript window

`prepare` compiles only the two canonical tables in `topics.md` and freezes
their SHA-256. Compilation fails closed on a row with a missing definition, a
cross-cutting row whose axis is not `frame` or `evidence`, or an axis with no
labels at all. It sends every transcript through the same segmentation path;
there is no keyword or embedding retrieval gate that could silently cap topic
or claim recall.

The defaults are 900-word windows, 150 words of overlap, and sentence-like units
of at most 45 words. Stable unit IDs such as `u000123` let the model return
auditable spans. Qwen five-minute-chunk timing is explicitly marked
`interpolated`; untimed publisher transcripts remain `unavailable` rather than
receiving invented timestamps.

### 2. Label independent dimensions and extract claims

`label` submits eight windows per request by default to a local OpenAI
Responses-compatible endpoint. It requests strict JSON Schema output. Each
label detection must contain one axis only and use the narrowest accurate span,
so a brief “a study shows” phrase does not inherit the boundaries of a long
sleep discussion.

The model does not state a detection's axis. Every label in the taxonomy already
carries one, so asking for the axis as well only creates a way for a detection
to contradict itself -- and a model asked for it will sometimes take it. The
axis is derived from the labels during validation, which still rejects a label
set that straddles two axes, the rule that carries the meaning.

The same response extracts atomic claims whose falsity, exaggeration, or missing
context would materially affect health understanding or behavior. It includes
claims being quoted, questioned, or rebutted, retaining their discourse role so
later analysis can distinguish exposure from endorsement. Pure opinions, jokes,
and vague suspicions are excluded unless they contain a testable factual claim.

Each claim carries `expressed_certainty`, a four-level ordinal of how firmly the
proposition was put: `absolute` for boosted or universal statements
("definitely", "always", "proven", "every single"), `unhedged` for a plain
declarative, `hedged` for softened assertions ("probably", "I think", "tends
to"), and `speculative` for possibilities and open questions ("might",
"maybe", "some people say"). It lives on claims rather than on topic spans
because certainty is a property of a proposition; a twenty-unit topic span
mixes many. The coding must be grounded: `certainty_markers` lists the verbatim
words that justify it, the client rejects any marker that is not inside the
span, and it rejects `hedged`, `speculative` or `absolute` with no markers and
`unhedged` with any. The verifier is shown both fields so a hedged claim is not
contradicted merely because its firm version would be.

The same response also lists `product_mentions`: every specific product named
in health content, meaning a brand, proprietary product, service or offering a
listener could identify and buy or seek out. Generic substances and practices
("magnesium", "semaglutide", "cold plunges") are not products, and a company
named only as an actor is not a product mention while its named product is.
Each mention records a listener-recognisable `product_name`, a `product_type`
(supplement, medication, food or beverage, device or wearable, test, app or
digital service, clinic or practitioner service, programme or course, book or
media, personal care, other) and a `mention_role` (`advertised`,
`own_product`, `recommended`, `neutral`, `criticized`), with a verbatim quote
containing the name as transcribed. One continuous stretch naming a product is
one mention, so a sponsor read is one row however often it repeats the name.

The client rejects omitted windows, unknown or mixed-axis labels, reversed or
out-of-window spans, duplicate annotations, non-verbatim quotes, empty required
strings, truncated or incomplete Responses, and malformed JSON. Every rejection carries a `kind`, and
`label_manifest.json` reports `unresolved_windows_by_kind` so a pilot can tell a
prompt problem from a transport problem without reading a thousand messages. A
pilot should watch `certainty_markers_mismatch` in particular: it is the one
rejection that measures whether the model can ground the certainty coding
rather than assert it.

Validation rejects a whole response, so a batch that fails is retried one window
at a time. Without that, a single unlabelable window would keep the rest of its
batch permanently unresolved and the next run would re-batch them together and
fail identically. The manifest reports `batches_isolated_this_invocation` and
`windows_recovered_by_isolation`. Failed batches are durable and retryable; they
never become implicit negatives.

### 3. Merge overlap duplicates without collapsing axes

`merge` deduplicates overlapping window decisions deterministically. It writes
one-label canonical annotations for topic, frame, and evidence axes, preserving
each dimension's exact span and discourse role. Topic clips attach overlapping
frame/evidence annotations and claim IDs for convenience, while the independent
annotation file remains authoritative.

Product mentions merge when their spans overlap or touch and their
`product_key` matches, a case- and punctuation-insensitive form of the name so
"AG-1" and "ag1" are one product. The higher-confidence extraction supplies the
canonical name, type and role; every role seen is kept in `mention_roles`.
Clips record `mentions_specific_product`, `product_mention_ids` and
`product_names` for the mentions inside their span. Claims record the same for
mentions inside their two-unit context window, because "AG1 has everything you
need. It covers all your micronutrients" names the product one sentence before
the checkable proposition. Clips and episodes also carry
`claim_certainty_counts` so the certainty mix of a topic or a show can be read
without a join.

Similar atomic claims are merged when their spans overlap and their verbatim
quotes match or their normalized claim texts are sufficiently similar. Merging
joins overlapping spans only, so a claim repeated later in an episode, or a
sponsor read repeated across a show, stays several candidates: `claim_key` and
`quote_key` let downstream analysis choose between counting claim instances and
counting distinct claims, and it must choose explicitly. Each
candidate retains transcript context, unit/time bounds, claim type, discourse
role, taxonomy labels, model provenance, and all supporting window IDs.

### 4. Validate labels and screening recall

`sample` creates a deterministic blinded sample with model-positive annotations
from all three label axes plus an independent uniform sample of successfully
labeled windows. The former estimates precision and span quality; the latter is
needed to audit false negatives.

It also writes `claim_sample_blinded.csv`, stratified by claim type, asking two
questions a label sample cannot: is the extracted item a material, checkable
factual claim, and is `claim_text` faithful to the quote? A rewrite that drops a
hedge or widens a population turns a true statement into a false one, and every
verdict downstream inherits that error. The coder must see `claim_text` to judge
faithfulness, so that sheet is blind only to claim type, discourse role,
expressed certainty and confidence; the coder's own certainty rating tests
whether the hedge/booster reading can be reproduced from the words alone.

`product_sample_blinded.csv` is stratified by product type. It asks whether the
span names a specific product at all, what a listener would call it, and which
type and mention role apply; it shows `product_name` for the same reason the
claim sheet shows `claim_text`, and is blind to type, role and confidence.

At 20 per label the precision interval is roughly +/-0.1 to 0.2, and 500 uniform
windows contain almost no positives for a rare label, so rare-label recall
cannot be estimated from them. Draw a supplementary keyword-retrieved audit
sample for those: legitimate because it measures misses rather than producing
the dataset, and its bias is known and reportable. Evidence-verification
verdicts still need their own held-out sample.

### 5. Verify against one frozen evidence corpus

Retrieval is intentionally outside the model call. A corpus-specific retriever
uses each `claim_text` to construct one evidence packet. `verify` then gives the
model only the candidate and those passages, instructing it not to browse or use
background knowledge.

Before any requests are sent, `verify` checks that:

- a local corpus-validation manifest says `validation_status=validated`;
- every packet names the same corpus ID, version, and corpus SHA-256;
- every packet contains the exact SHA-256 of that validation manifest;
- candidates, packet IDs, passage IDs, and retrieval limits are valid; and
- model citations refer only to passage IDs in that candidate's packet.

The verifier returns one of:

- `supported`
- `contradicted`
- `misleading_or_missing_context`
- `mixed`
- `insufficient_evidence`
- `not_verifiable`

`insufficient_evidence` is a valid outcome, not a model failure. A validated
corpus does not guarantee that retrieval found passages capable of resolving a
particular claim.

## Serving the labeling model

`label` and `verify` talk to a local vLLM server over the OpenAI Responses API.
The pilot model is
[`deepseek-ai/DeepSeek-V4-Flash-0731`](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731),
a 1M-context mixture-of-experts reasoning model.

```bash
vllm serve deepseek-ai/DeepSeek-V4-Flash-0731 \
  --tokenizer-mode deepseek_v4 \
  --reasoning-parser deepseek_v4 \
  --max-model-len 65536 \
  --tensor-parallel-size 4 \
  --kv-cache-dtype fp8
```

The first three flags are what this pipeline depends on; the rest are sizing.

### Several servers

`--api-base` repeats, and `[model] api_base` in the config takes a list, so a
run can be spread over identical servers:

```toml
api_base = ["http://127.0.0.1:8222/v1", "http://gpu312:8222/v1"]
```

Requests round-robin across them and each retry draws again, so losing a node
slows a run down rather than ending it. Before any work is submitted the client
reads `/v1/models` on every endpoint and refuses to start if they disagree about
the model: endpoints are pooled, so a run split across two checkpoints could not
be attributed afterwards.

The endpoints are deliberately **not** in the run fingerprint -- they are
capacity, not a determinant of the output, and adding or losing a node must not
orphan a half-finished `labels.sqlite`. The model they serve is fingerprinted,
and `label_manifest.json` records the endpoint list under `endpoints`.

- `--tokenizer-mode deepseek_v4` selects the model's own prompt encoding, which
  is a dedicated renderer rather than a Jinja chat template. Without it the
  Responses endpoint does not build V4 prompts correctly.
- `--reasoning-parser deepseek_v4` is what lets thinking and strict JSON Schema
  coexist. vLLM starts applying the schema grammar only once that parser sees
  the end of the reasoning block; with no parser configured the grammar binds
  from the first token and the JSON can be emitted as reasoning content instead
  of as the message.
- Structured outputs need no extra flags. The response schema uses `enum`,
  `pattern`, `minItems`/`maxItems` and numeric bounds, all of which the default
  `xgrammar` backend compiles.
- `--max-model-len` has to cover one whole request, and this is the constraint
  that decides the batch size. A real 900-word window measures about 2,275 input
  tokens, so a batch of eight plus the ~11,500-token instruction prefix is
  roughly 29,700 tokens. At `--max-model-len 65536` that leaves under 36,000 for
  output, which thinking alone can exhaust; the server then rejects the request
  with HTTP 400 rather than truncating. Raising the context is what buys back
  batch size, and batch size is what amortises the per-request reasoning cost.
  Leave automatic prefix caching on so the instruction prefix is not recomputed
  for every batch, and confirm the hit rate in the server metrics before scaling.
- Tool calling is unused, so `--tool-call-parser` and `--enable-auto-tool-choice`
  are unnecessary.
- Throughput flags -- tensor parallelism, fp8 KV cache, and the speculative
  decoding config -- depend on the checkpoint variant and the GPUs. Take them
  from the model card and the vLLM recipe rather than from this example; the
  card and the recipe currently name different draft methods (`dspark` and
  `mtp`), so check which one your checkpoint ships with.

### Thinking is an explicit setting, not an omission

`--reasoning-effort` is sent on every request and is part of the run
fingerprint. Leaving it out of the request body is not neutral on this model:
the V4 renderer reads a missing value as "think, at high effort", so silence
would select the most expensive mode rather than the cheapest. The pipeline
therefore always sends a value, defaulting to `none`.

| `--reasoning-effort` | Effect on DeepSeek-V4 |
| --- | --- |
| `none` (default) | Thinking off |
| `minimal`, `low`, `medium` | Thinks, with no effort preamble |
| `high`, `xhigh` | Thinks, with the high-effort preamble |
| `max` | Thinks, with the maximum-effort preamble; needs `--max-model-len 393216` |

Reasoning tokens come out of the same `--max-output-tokens` budget as the JSON,
and the `high` and `max` preambles instruct the model to write its whole
deliberation out. Raise that budget well above its 12,000 default before turning
thinking on, and watch `output_truncated` in `unresolved_windows_by_kind`: that
kind means the budget ran out before the answer began, and it is reported
separately from `api_incomplete` precisely because a too-small budget fails on
nearly every window while a transport fault does not. A thinking request also
takes far longer to return, so raise `--timeout` from its 600-second default at
the same time. Reasoning text itself is never returned
(`include_reasoning: false`); nothing downstream reads it.

Whether thinking earns its cost is a cost question, but not an open one about
quality. Measured on DeepSeek-V4-Flash-0731 against a single 637-word window,
6-10 samples per setting, one attempt each:

| | `none` | `high` |
| --- | --- | --- |
| Annotations rejected | 13.2% (18 of 136) | 2.5% (3 of 119) |
| Whole responses accepted | ~2 in 10 | 5 in 6 |
| Reasoning tokens | 0 | ~25,000 |
| Total output tokens | ~1,500 | ~28,000 |
| Median latency | 81s | 294s |

The two rows disagree because validation is all-or-nothing: at 17 annotations
per response, a 13% per-annotation error compounds to roughly a 9% chance that
a whole response survives. Cutting per-item error to 2.5% is what turns the
response-level number around. That is one window and one prompt version, so
treat the magnitudes as indicative and re-measure on the pilot -- but the sign
is not in doubt, and it is why the shipped config sets `high`.

Read label prevalence, span quality and candidate yield too, not only the
rejection counts: a setting can be accepted more often and still code worse.

DeepSeek recommends `--temperature 1.0` with `--top-p 1.0`, or `--top-p 0.95`
for the 0731 checkpoint. Every one of these settings is in the fingerprint, so
changing any of them requires a fresh output directory.

`--seed` pins the sampler, at a cost worth knowing: `--attempts` retries resend
the identical payload, so with a fixed seed a window rejected for its content
tends to be rejected the same way on every attempt instead of being recovered by
a different sample. Prefer a seed for a comparison run, not for a production
pass.

### Configuration

`label` and `verify` take the same endpoint and decoding flags, and a long pilot
invites the two to drift apart. `analysis/topic-labeling.toml` states them once
and is read by default from the repository root, so the runbook commands below
carry no endpoint flags at all:

```toml
# Where the run reads and writes; every command takes what applies to it.
[paths]
transcripts = "downloader/data/transcripts"
output_dir = "analysis/output/topic-labeling"

# Shared by `label` and `verify`.
[model]
api_base = "http://127.0.0.1:8000/v1"
model = "deepseek-ai/DeepSeek-V4-Flash-0731"
reasoning_effort = "none"
max_output_tokens = 12000

[label]
batch_size = 8

[verify]
batch_size = 4
```

`[paths]` and `[model]` are shared; a `[label]` or `[verify]` key overrides them
for that command, and any command may have a table of its own. Keys are the flag
names with underscores, so `top_p` is `--top-p`. A shared table only supplies
the flags a command actually has, so `transcripts` reaches `prepare` and is
silently irrelevant to `label`; a key in a command's *own* table that it does not
accept is still an error.

Every artifact that lives inside the run directory -- `taxonomy.json`,
`windows.jsonl.zst`, each manifest, the candidate and product files -- follows
`--output-dir`. Moving a run somewhere else is one flag, not five:

```bash
.venv/bin/python analysis/topic_labeling.py label --output-dir /tmp/pilot
```

`verify` takes the same `--output-dir` as the run directory it reads from and
writes its own results to `<output-dir>/verification`, overridable with
`--verification-dir`.

Config values become ordinary flags before parsing. Three things follow. A flag
typed on the command line lands after them and therefore wins, so a one-off
experiment stays one-off:

```bash
.venv/bin/python analysis/topic_labeling.py label \
  --output-dir /tmp/topic-labeling-thinking --reasoning-effort high
```

Argparse validates the file, so a mistyped key is an unrecognized flag and a
mistyped number is a type error, rather than a setting that silently does
nothing. And the settings reach `label_manifest.json` and the run fingerprint
exactly as typed flags do.

A setting left out of the config is left out of the request body; the client
substitutes nothing. vLLM then resolves it from the model's `generation_config.json`
(temperature 1.0 and top_p 1.0 for this checkpoint) and falls back to its own
neutral defaults only if the model specifies none. Omitting them is therefore the
way to get the model's preferred sampling -- and because the fingerprint would
then record only a null, `label_manifest.json` and `verification_manifest.json`
carry `effective_sampling`, the temperature, top_p and output budget the server
reports it actually decoded with.

Pass `--config` for a different file; an explicit path that does not exist is an
error, while a missing default is simply no config. The manifest records which
file a run used, in `config`. That field is deliberately outside the fingerprint:
the settings it supplied are already in there, and editing a comment must not
orphan an existing `labels.sqlite`.

## Runbook

No authentication header is sent unless `--api-key-env` is explicitly given.
Start with a separate smoke directory:

```bash
SMOKE=/tmp/topic-labeling-smoke

.venv/bin/python analysis/topic_labeling.py prepare \
  --metadata-db downloader/data/podcast_metadata.db \
  --output-dir $SMOKE --limit 100

.venv/bin/python analysis/topic_labeling.py label  --output-dir $SMOKE
.venv/bin/python analysis/topic_labeling.py merge  --output-dir $SMOKE
.venv/bin/python analysis/topic_labeling.py sample --output-dir $SMOKE \
  --per-label 20 --random-windows 500
```

Inspect omission/error rates, label frequency, span boundaries, claim-screening
recall, and audio-aligned examples before a full run. Use a fresh output
directory whenever the model, taxonomy, prompt, windowing, batch size, reasoning
effort, or temperature changes.

For the full corpus, the shorter default-path form is:

```bash
.venv/bin/python analysis/topic_labeling.py prepare \
  --metadata-db downloader/data/podcast_metadata.db

.venv/bin/python analysis/topic_labeling.py label

.venv/bin/python analysis/topic_labeling.py merge
.venv/bin/python analysis/topic_labeling.py sample
```

`label` is resumable. `labels.sqlite` commits each completed response as one
transaction, separately records failures, and exports sorted raw results. The
command exits with status 2 while any window remains unresolved. `merge` also
fails closed unless every window has a successful result; `--allow-incomplete`
must be an explicit exploratory choice.

## Evidence-corpus interface

Create `analysis/output/topic-labeling/evidence_corpus_validation_manifest.json`
after the corpus passes its independent source/document validation. Extra fields
are allowed, but these fields are required:

```json
{
  "schema_version": "evidence-corpus-validation-v1",
  "corpus_id": "validated-health-corpus",
  "corpus_version": "2026-08-30",
  "corpus_sha256": "64-lowercase-hex-characters",
  "validation_status": "validated",
  "validated_at": "2026-08-30T12:00:00+00:00",
  "validator": "corpus-review-team",
  "validation_method": "Document-level source and content validation protocol v3",
  "document_count": 12000
}
```

The retrieval job reads `verification_candidates.jsonl` and writes one line per
retrieved candidate to `evidence_packets.jsonl.zst`:

```json
{
  "candidate_id": "episode_1_claim_0001",
  "corpus": {
    "corpus_id": "validated-health-corpus",
    "corpus_version": "2026-08-30",
    "corpus_sha256": "the-corpus-sha256-from-the-manifest",
    "validation_manifest_sha256": "sha256-of-the-manifest-file"
  },
  "retrieval": {
    "method": "hybrid-bm25-embedding",
    "retriever_version": "retriever-v1",
    "query": "Every person needs exactly eight hours of sleep.",
    "top_k": 8
  },
  "passages": [
    {
      "passage_id": "guideline-42:p12",
      "document_id": "guideline-42",
      "title": "Sleep duration guideline",
      "source": "Validated issuing organization",
      "published_date": "2025-01-01",
      "locator": "page 12",
      "text": "Retrieved evidence text..."
    }
  ]
}
```

All four optional passage metadata values (`title`, `source`, `published_date`,
and `locator`) may be `null`; IDs and text may not. Retrieval may emit an empty
`passages` array with `top_k=0`, which should normally yield
`insufficient_evidence`.

Run verification after generating and auditing the packets:

```bash
.venv/bin/python analysis/topic_labeling.py verify \
  --output-dir analysis/output/topic-labeling
```

`verify` is independently fingerprinted and resumable through
`verification/verification.sqlite`. It exits with status 2 for failed model
requests or candidates missing packets. Those states must not be counted as
verified negatives.

## Artifact contracts

| Artifact | Contract |
| --- | --- |
| `taxonomy.json` | Frozen 84-label taxonomy with topic/frame/evidence axes and source hashes |
| `prepare_manifest.json` | Input paths, windowing settings, counts, and windows SHA-256 |
| `windows.jsonl.zst` | All line-addressable transcript windows with source provenance |
| `labels.sqlite` | Crash-safe raw-label response checkpoints keyed by window ID |
| `label_manifest.json` | Model, endpoint, prompt/settings fingerprint, server-reported effective sampling, and completion counts |
| `window_labels.jsonl.zst` | Validated raw window decisions |
| `label_annotations.jsonl` | Canonical one-label spans across all three taxonomy axes |
| `clips.jsonl` | Topic clips with overlapping frame/evidence annotations and claim IDs |
| `verification_candidates.jsonl` | Atomic unverified possible-misinformation review candidates with expressed certainty and linked product mentions |
| `product_mentions.jsonl` | Canonical product mentions with name, `product_key`, type, mention roles and span |
| `episodes.jsonl` | Episode rollups including zero-clip denominators, window/unit/word counts and duration for per-hour rates |
| `review_queue.csv` | Human-readable topic clip queue |
| `validation_sample_blinded.csv` | Model-blinded human label/span coding sheet |
| `validation_sample_key.csv` | Held-back model decisions and sample strata |
| `claim_sample_blinded.csv` | Claim materiality and `claim_text` faithfulness coding sheet |
| `claim_sample_key.csv` | Held-back claim type, discourse role, expressed certainty, markers and confidence |
| `product_sample_blinded.csv` | Product specificity, name, type and mention-role coding sheet |
| `product_sample_key.csv` | Held-back product type, mention role and confidence |
| `evidence_corpus_validation_manifest.json` | Human/process assertion that the frozen corpus passed validation |
| `evidence_packets.jsonl.zst` | Candidate-specific retrieved evidence with immutable corpus provenance |
| `verification/verification.sqlite` | Crash-safe verification response checkpoints |
| `verification/verification_results.jsonl.zst` | Evidence-bounded verdicts and passage citations |
| `verification/verification_manifest.json` | Candidate/packet/corpus/model hashes and unresolved counts |

## Capacity and operational controls

The corpus snapshot inspected on 2026-08-30 contains 102,477 transcripts,
1,135,691,165 words, and about 99,133 transcript-hours. At the default overlap,
raw transcript input is roughly 1.8 billion model tokens using 1.33 tokens per
word. At aggregate 5,000 tokens/second, transcript prefill alone is about 100
hours. This is a planning estimate: tokenizer behavior, decoding, batching,
prefix-cache hits, and the server's throughput definition all affect runtime.

That estimate covers transcript prefill with thinking off. Any reasoning
effort above `none` adds output tokens per request that no transcript-size
calculation predicts, so measure them in the pilot before extrapolating.

The repeated taxonomy/instruction prefix is about 11,500 tokens -- it grew when
the keyword-list definitions were replaced with written ones, which makes prefix
cache hits matter more, not less. Confirm prefix
cache hits in server metrics before scaling. A several-hundred-episode pilot
should measure input/output tokens, windows/hour, latency, retries, malformed or
omitted results, GPU utilization, label prevalence, and candidate yield.

## Validation and analysis rules

Before publication or downstream prevalence analysis:

1. Freeze the taxonomy, prompts, models, corpus version, retrieval method, and
   release gates before evaluating held-out data.
2. Decide before the run whether the unit of analysis is claim instances or
   distinct claims, and whether advertisement-relevance spans are in or out.
   Both change every headline number, and neither has a neutral default.
3. Double-code the blinded label sample across topic, frame, evidence, relevance,
   discourse role, and span acceptability. Audit uniform windows for misses.
4. Separately sample material factual claims to measure candidate-extraction
   recall; candidate precision is less important because verification is the
   deliberate second stage. Report agreement on expressed certainty as an
   ordinal (weighted kappa), and treat a product sample that disagrees on
   specificity as a codebook problem before a model problem.
5. Double-review a stratified sample of all six verification verdicts, including
   evidence sufficiency and whether every citation actually supports the stated
   rationale.
6. Report errors by topic, discourse role, ASR source, show, date, claim type,
   and evidence-signal/frame combinations. Model confidence is not a calibrated
   probability.
7. Count `contradicted` or `misleading_or_missing_context` as potential factual
   misinformation only under a preregistered rule and with discourse role kept
   separate. Do not count quoted, questioned, or rebutted exposure as host
   endorsement.
8. Never treat `possible_misinformation`, `insufficient_evidence`, missing
   packets, failed requests, or `not_verifiable` as confirmed misinformation.
9. Express rates per hour of speech or per thousand words using the counts in
   `episodes.jsonl`, not per episode: episodes range from minutes to hours.
   Count products by `product_key` for distinct products and by mention for
   exposure, and say which; a sponsor read repeated across a show is many
   mentions of one product.
10. Retain zero-clip episodes in denominators, follow the live-window/panel rules
   in `docs/corpus-issues.md`, and propagate measured label/retrieval/verdict
   error into uncertainty estimates.

If a held-out gate fails, revise under a new fingerprint and evaluate a new
held-out sample. Do not patch historical outputs in place.
