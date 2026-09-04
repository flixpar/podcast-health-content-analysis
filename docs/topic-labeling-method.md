# Podcast clip labeling and claim-verification method

## What the pipeline measures

`analysis/topic_labeling.py` exhaustively labels timestamped transcript spans
using the 83 labels in the two final tables of `topics.md`. It keeps the
following dimensions independent:

| Dimension | Values | Interpretation |
| --- | --- | --- |
| Topic | 49 parent health topics | What the span discusses |
| Frame | 27 cross-cutting labels | How it is framed, including conspiracy, correction, MAHA, and commercialization |
| Evidence signal | 7 cross-cutting labels | How evidence or authority is invoked, including academic studies, mechanisms, extrapolation, experience, and credentials |
| Claim review | Atomic factual claims | High-recall candidates for later evidence verification |

Every label and claim also records `discourse_role` as
`asserted_or_endorsed`, `questioned`, `reported_or_quoted`, `rebutted`, or
`unclear`. Labels record `relevance` as `substantive`, `passing`, or
`advertisement`; claims record a claim type such as causal, treatment,
risk/safety, mechanism, or institutional/conspiracy.

These are deliberately separate. A conspiracy frame is not necessarily a false
claim. Citing academic research does not make a claim true. Reporting or
rebutting a questionable claim is not endorsement.

`possible_misinformation=true` means only that a material, externally checkable
claim was selected for evidence review. The first model does not predict truth.
This high-recall definition avoids asking a model with no evidence corpus to
decide which claims merely sound suspicious. A claim becomes a verified
misinformation finding only after the separate evidence step and any required
human review.

## Five-stage design

### 1. Prepare every transcript window

`prepare` compiles only the two canonical tables in `topics.md` and freezes
their SHA-256. It sends every transcript through the same segmentation path;
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

The same response extracts atomic claims whose falsity, exaggeration, or missing
context would materially affect health understanding or behavior. It includes
claims being quoted, questioned, or rebutted, retaining their discourse role so
later analysis can distinguish exposure from endorsement. Pure opinions, jokes,
and vague suspicions are excluded unless they contain a testable factual claim.

The client rejects omitted windows, unknown or mixed-axis labels, reversed or
out-of-window spans, duplicate annotations, non-verbatim quotes, incomplete
Responses, and malformed JSON. Failed batches are durable and retryable; they
never become implicit negatives.

### 3. Merge overlap duplicates without collapsing axes

`merge` deduplicates overlapping window decisions deterministically. It writes
one-label canonical annotations for topic, frame, and evidence axes, preserving
each dimension's exact span and discourse role. Topic clips attach overlapping
frame/evidence annotations and claim IDs for convenience, while the independent
annotation file remains authoritative.

Similar atomic claims are merged when their spans overlap and their verbatim
quotes match or their normalized claim texts are sufficiently similar. Each
candidate retains transcript context, unit/time bounds, claim type, discourse
role, taxonomy labels, model provenance, and all supporting window IDs.

### 4. Validate labels and screening recall

`sample` creates a deterministic blinded sample with model-positive annotations
from all three label axes plus an independent uniform sample of successfully
labeled windows. The former estimates precision and span quality; the latter is
needed to audit false negatives. Candidate extraction and evidence-verification
verdicts should receive their own held-out human samples.

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

## Runbook

No authentication header is sent unless `--api-key-env` is explicitly given.
Start with a separate smoke directory:

```bash
.venv/bin/python analysis/topic_labeling.py prepare \
  --transcripts downloader/data/transcripts \
  --metadata-db downloader/data/podcast_metadata.db \
  --output-dir /tmp/topic-labeling-smoke \
  --limit 100

.venv/bin/python analysis/topic_labeling.py label \
  --output-dir /tmp/topic-labeling-smoke \
  --taxonomy /tmp/topic-labeling-smoke/taxonomy.json \
  --windows /tmp/topic-labeling-smoke/windows.jsonl.zst \
  --prepare-manifest /tmp/topic-labeling-smoke/prepare_manifest.json \
  --api-base http://127.0.0.1:8000/v1 \
  --model YOUR_LOCAL_MODEL_ID

.venv/bin/python analysis/topic_labeling.py merge \
  --output-dir /tmp/topic-labeling-smoke \
  --taxonomy /tmp/topic-labeling-smoke/taxonomy.json \
  --windows /tmp/topic-labeling-smoke/windows.jsonl.zst \
  --label-manifest /tmp/topic-labeling-smoke/label_manifest.json

.venv/bin/python analysis/topic_labeling.py sample \
  --output-dir /tmp/topic-labeling-smoke \
  --per-label 20 \
  --random-windows 500
```

Inspect omission/error rates, label frequency, span boundaries, claim-screening
recall, and audio-aligned examples before a full run. Use a fresh output
directory whenever the model, taxonomy, prompt, windowing, batch size, reasoning
effort, or temperature changes.

For the full corpus, the shorter default-path form is:

```bash
.venv/bin/python analysis/topic_labeling.py prepare \
  --metadata-db downloader/data/podcast_metadata.db

.venv/bin/python analysis/topic_labeling.py label \
  --api-base http://127.0.0.1:8000/v1 \
  --model YOUR_LOCAL_MODEL_ID

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
  --candidates analysis/output/topic-labeling/verification_candidates.jsonl \
  --evidence-packets analysis/output/topic-labeling/evidence_packets.jsonl.zst \
  --corpus-validation-manifest \
    analysis/output/topic-labeling/evidence_corpus_validation_manifest.json \
  --output-dir analysis/output/topic-labeling/verification \
  --api-base http://127.0.0.1:8000/v1 \
  --model YOUR_LOCAL_MODEL_ID
```

`verify` is independently fingerprinted and resumable through
`verification/verification.sqlite`. It exits with status 2 for failed model
requests or candidates missing packets. Those states must not be counted as
verified negatives.

## Artifact contracts

| Artifact | Contract |
| --- | --- |
| `taxonomy.json` | Frozen 83-label taxonomy with topic/frame/evidence axes and source hashes |
| `prepare_manifest.json` | Input paths, windowing settings, counts, and windows SHA-256 |
| `windows.jsonl.zst` | All line-addressable transcript windows with source provenance |
| `labels.sqlite` | Crash-safe raw-label response checkpoints keyed by window ID |
| `label_manifest.json` | Model, endpoint, prompt/settings fingerprint, and completion counts |
| `window_labels.jsonl.zst` | Validated raw window decisions |
| `label_annotations.jsonl` | Canonical one-label spans across all three taxonomy axes |
| `clips.jsonl` | Topic clips with overlapping frame/evidence annotations and claim IDs |
| `verification_candidates.jsonl` | Atomic unverified possible-misinformation review candidates |
| `episodes.jsonl` | Episode rollups including zero-clip denominators |
| `review_queue.csv` | Human-readable topic clip queue |
| `validation_sample_blinded.csv` | Model-blinded human label/span coding sheet |
| `validation_sample_key.csv` | Held-back model decisions and sample strata |
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

The repeated taxonomy/instruction prefix is about 6,600 tokens. Confirm prefix
cache hits in server metrics before scaling. A several-hundred-episode pilot
should measure input/output tokens, windows/hour, latency, retries, malformed or
omitted results, GPU utilization, label prevalence, and candidate yield.

## Validation and analysis rules

Before publication or downstream prevalence analysis:

1. Freeze the taxonomy, prompts, models, corpus version, retrieval method, and
   release gates before evaluating held-out data.
2. Double-code the blinded label sample across topic, frame, evidence, relevance,
   discourse role, and span acceptability. Audit uniform windows for misses.
3. Separately sample material factual claims to measure candidate-extraction
   recall; candidate precision is less important because verification is the
   deliberate second stage.
4. Double-review a stratified sample of all six verification verdicts, including
   evidence sufficiency and whether every citation actually supports the stated
   rationale.
5. Report errors by topic, discourse role, ASR source, show, date, claim type,
   and evidence-signal/frame combinations. Model confidence is not a calibrated
   probability.
6. Count `contradicted` or `misleading_or_missing_context` as potential factual
   misinformation only under a preregistered rule and with discourse role kept
   separate. Do not count quoted, questioned, or rebutted exposure as host
   endorsement.
7. Never treat `possible_misinformation`, `insufficient_evidence`, missing
   packets, failed requests, or `not_verifiable` as confirmed misinformation.
8. Retain zero-clip episodes in denominators, follow the live-window/panel rules
   in `docs/corpus-issues.md`, and propagate measured label/retrieval/verdict
   error into uncertainty estimates.

If a held-out gate fails, revise under a new fingerprint and evaluate a new
held-out sample. Do not patch historical outputs in place.
