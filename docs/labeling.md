# Podcast health-content labeling

The current scheme is taxonomy v8. `analysis/topic_labeling.py` labels every
transcript window, merges overlapping detections into clips, and extracts
claims for a separate evidence-verification step. The labeler measures what
was said and how it was framed; it does not decide whether a claim is true.

## Maintained sources

| Source | Purpose |
| --- | --- |
| `taxonomy/health-v8.md` | Label definitions and hierarchy |
| `taxonomy/codebook-v8.md` | Annotation rules shared by the labeler and reference annotators |
| `analysis/prompts/rubric-v8.md` | Labeling procedure, calibration and validated worked example |
| `analysis/topic-labeling.toml` | Pipeline paths, endpoint and inference settings |
| `benchmark/v3/config.toml` | Benchmark specification for v8 |

The v7 source, codebook and rubric remain available for existing experiments.
The original flat taxonomy is also supported when explicitly selected.
Taxonomy versions select matching rubric and codebook files; a compiled
hierarchical taxonomy without a version is interpreted as v7.

The optional TypeSafe cascade uses the explicit flat-source configuration
`analysis/topic-labeling-typesafe.toml` and writes to `local/topic-labeling-typesafe`.
It implements the legacy topic/frame/evidence claim contract and rejects
hierarchical v7/v8 before endpoint discovery or inference. Its historical
91-label evaluation does not validate this granular scheme. See
[the TypeSafe method](typesafe-labeling.md) for its procedure and limits.

## What is recorded

| Axis | v8 labels | Meaning |
| --- | --- | --- |
| Topic | 60 parents and 373 subtopics in 13 domains | What is discussed |
| Narrative | 145 | Which named contested proposition is invoked |
| Frame | 23 | How the passage is framed |
| Evidence | 16 | What support or authority is invoked |
| Population | 13 | Whose health is discussed |

Label the most specific applicable subtopic. Parent topics and domains are
derived; a bare parent means no listed subtopic fits. Narrative exposure is
recorded in every stance, including a rebuttal. `discourse_role` distinguishes
endorsement, questioning, quotation and rebuttal; `relevance` distinguishes
substantive content, passing mentions and advertising.

Atomic claims carry their topic and narrative links, claim type, evidence
signals and expressed certainty, grounded in quoted marker words. Certainty
describes the speaker's wording; model confidence describes coding uncertainty.
Specific products carry a product type and mention role. Neither a frame nor
an evidence signal establishes truth. A misinformation finding requires the
separate evidence step and any required human review.

## Prepare, label and merge

Run from the repository root with the project's Python environment. Set the
transcript and metadata paths and model endpoint in the configuration first.

```bash
.venv/bin/python analysis/topic_labeling.py prepare --topics taxonomy/health-v8.md \
    --output-dir local/topic-labeling-v8
.venv/bin/python analysis/topic_labeling.py label --output-dir local/topic-labeling-v8
.venv/bin/python analysis/topic_labeling.py merge --output-dir local/topic-labeling-v8
```

Use the same output directory for all stages. For another inference
configuration, pass the same `--config` to preparation and labeling. Command
line flags override configuration values. Add `--limit` to preparation for a
small offline corpus check before starting inference.

Preparation uses 900-word windows with 150-word overlap and sentence-like units
of at most 45 words. Stable unit IDs make evidence spans auditable. Timing
quality remains explicit for interpolated or untimed transcripts. Labeling
uses one window per request, validates the response, and checkpoints completed
windows in SQLite. The run fingerprint includes the taxonomy, input windows,
model and output-affecting settings. The hierarchical prompt identity hashes
the assembled rubric, codebook and label tables, so edited instructions require
a new run rather than mixing results into an existing store.

The v8 prompt is approximately 356,000 characters (85,000–90,000 tokens).
Serve it with prefix caching and a context of at least 196,608 tokens to leave
room for input and reasoning. Use explicit model and sampling settings for
reproducible comparisons; server endpoints represent capacity and may change
without changing a run's identity.

### Selecting episodes and labeling order

`prepare` labels every transcript in `--transcripts`. To prepare one study's
episodes from a shared transcript directory, pass `--episode-ids` with a file of
IDs, one per line, or with a study export's `episodes.csv`. The manifest
records how many were requested, found and missing a transcript. Windows are
written, and therefore labeled, in episode-ID order by default. `--order
shuffled` uses a fixed pseudo-random episode order instead. That spreads dense
stretches of a corpus across the run, so partial results are representative
and the rate stays steady. Each episode's windows stay together, which merge
relies on. Windows record their transcript relative to the transcript
directory, so no machine-specific paths reach the outputs.

### Several servers and failures

List one `api_base` per server. `concurrency` is the total across all of them.
Each request goes to the server with the fewest requests in flight. A server
that fails (a transport error, HTTP 5xx or 429) is skipped for 30 seconds, and
the retry goes to another server. A server that is down at startup is skipped
and probed again later, as long as at least one answers. A dropped connection
counts as a transport error and is retried like any other. After the main pass,
windows whose every attempt failed on a server are retried once more
(`--final-retry-passes`, default 1). Windows whose responses were rejected keep
their failure. Rerunning `label` retries every unresolved window.

The progress line reports the recent rate, output tokens per second and an ETA.
Each stored window keeps its lenient-validation repairs and drops, its attempt
count and the output tokens spent on rejected attempts. `label_manifest.json`
totals these over the whole store (`validation_totals`), so the totals survive
resumed runs.

### Sharing a release

`analysis/label_export.py` packages a merged run for analysis elsewhere. It
writes Parquet tables for the labels and for the transcript units that every
span refers to. With `--metadata-db` it adds episode and podcast metadata. With
`--study` it also adds every study episode, the chart evidence per show-month
and coverage statistics. It ships the taxonomy sources and a README (generated
unless `--readme` is given). `MANIFEST.json` holds the provenance and a sha256
of every file:

```bash
.venv/bin/python -m analysis.label_export --run-dir local/topic-labeling-glm53 \
    --out local/releases/top24-v8 --metadata-db downloader/data/podcast_metadata.db \
    --study apple-top24-monthly
```

It refuses merge outputs that no longer match `merge_summary.json`, and a
release directory that is not empty.

Merged artifacts use `topic-labeling-v5`, including product mentions. Topic
annotations carry parent and domain IDs; clips carry narrative and population
annotations. Verification candidates carry narrative links, parent topic IDs
and relevance, and the review queue exposes narrative and population columns.
Validation checks labels, axis consistency, spans, verbatim evidence and
certainty markers. Failures are durable and retryable; missing results do not
mean negative annotations. `--validation strict` rejects invalid responses.
`lenient` repairs only unambiguous span/quote matches and drops unrepairable
annotations, logging both. Report this fingerprinted mode with evaluation
results.

Merging deterministically deduplicates overlapping decisions while preserving
separate annotations on each axis and supporting-window provenance. Claims
merge across overlapping matching passages; products require overlapping or
touching spans and matching normalized names. Later repetitions remain separate.

Use `sample` to create blinded label, claim and product review sheets plus
uniform windows for an independent false-negative audit. Supplement rare-topic
recall with a targeted sample and report its selection bias.

Evidence verification retrieves passages from one frozen, validated corpus.
`verify` checks corpus and validation-manifest identity, candidate/passage IDs,
retrieval limits and citations. Its outcomes include supported, contradicted,
missing context, mixed, insufficient evidence and not verifiable. Insufficient
retrieval is a valid outcome. Use `sample --help` and `verify --help` for setup.

## Change and evaluate the scheme

Edit the taxonomy, codebook and rubric together. Compilation rejects malformed
rows, missing definitions, unknown narrative home topics and missing axes.
Tests validate cross-references, worked examples, version selection and output
schema propagation:

```bash
.venv/bin/python -m pytest analysis/tests -q
export BENCHMARK_DIR=benchmark/v3
.venv/bin/python -m analysis.benchmark taxonomy
```

Benchmark configurations are tracked; compiled taxonomies, selected windows,
reference answers, gold and candidate runs live under ignored `local/`.
See [the benchmark workflow](benchmark.md) for setup, annotation and scoring.
The v3 specification evaluates v8; v2 reference answers are not valid v3 gold
because the coding rules changed. Re-annotation is required.

The v8 review's reports, editing decisions and one-off patch scripts, together
with the superseded version guides, are preserved under `local/`. The committed
taxonomy and codebook contain the accepted outcome of that review.
