# Labeling benchmark

`analysis/benchmark/` evaluates transcript labeling against independent
reference annotations. It measures topics, framing, evidence signals,
checkable health claims, expressed certainty, and named products. The granular
scheme also measures narratives and populations. Agreement among reference
annotators provides context for candidate scores; it does not establish that
an annotation is objectively correct.

## Specifications and local artifacts

The repository contains the maintained inputs and evaluation code. Large
transcript exports, model answers, gold, screening results, compiled taxonomies,
and historical experiment reports live under ignored `local/`.

| Specification selector | Scheme | Artifact directory |
| --- | --- | --- |
| `benchmark` (default) | flat v6, 91 labels | `local/benchmark/` |
| `benchmark/v2` | granular v7, 577 labels | `local/benchmark/v2/` |
| `benchmark/v3` | granular v8, 630 labels | `local/benchmark/v3/` |

Set `BENCHMARK_DIR` to select a specification directory. Its `config.toml`
defines quotas, seeds, corpus paths, taxonomy source, and `[benchmark] data_dir`.
`BENCHMARK_OUTPUT_DIR` overrides the artifact directory without changing the
selected scheme. Relative paths resolve from the repository root.

Tracked source files include `benchmark/topics-v6.md`, `benchmark/lexicon-v2.json`,
the configs, annotator rosters, `analysis/benchmark/codebook.md`, and the versioned
taxonomy/codebook/rubric. Synthetic authoring specifications and controlled
contrast edits are maintained in `analysis/benchmark/synthetic.py`.
Annotator registration seeds from the tracked roster and writes its updated
copy to the local artifact directory.

| Local artifact | Purpose |
| --- | --- |
| `taxonomy.json` | Compiled labels and scoring aliases |
| `items.jsonl` | Corpus windows and authored items with split/provenance |
| `references/<item_id>/<annotator>.json` | Validated model annotations |
| `gold.jsonl`, `gold-parent.jsonl`, `gold-domain.jsonl` | Consensus gold at supported topic levels |
| `adjudication.jsonl` | Reviewed singleton verdicts |
| `agreement.json`, `manifest.json` | Agreement and dataset provenance |
| `pool/`, `runs/` | Candidate windows, screening, and candidate model runs |

Task bundles default to `local/benchmark-tasks/`; `BENCHMARK_TASKS_DIR` can
select another location. Bundles contain the codebook, label tables, schema,
and inputs needed for one task. Ingestion validates every returned record.

## Start from a fresh checkout

Run from the repository root with the project environment. Taxonomy generation
and tests are offline and need no corpus or model answers:

```bash
export BENCHMARK_DIR=benchmark/v3
.venv/bin/python -m analysis.benchmark taxonomy
.venv/bin/python -m pytest analysis/tests
```

The first command writes `local/benchmark/v3/taxonomy.json` using the benchmark
compiler, including parent/domain alias maps. Select `benchmark/v2` for v7. For the flat scheme, unset
`BENCHMARK_DIR` or select `benchmark` instead. A compiled taxonomy is a generated
run input; changing its source requires a new benchmark version and references.

TypeSafe is a flat-scheme candidate only: select `BENCHMARK_DIR=benchmark` and
`--pipeline-config benchmark/pipeline-typesafe.toml`. It does not accept a
rubric replacement or hierarchical v7/v8. Raw probabilities live in each
repeat's `typesafe_judgments.jsonl`; offline tuning uses
`python -m analysis.benchmark.typesafe_tune local/benchmark/runs/RUN` with the
same benchmark selection. See [the TypeSafe method](typesafe-labeling.md) for
the historical flat evaluation and its limitations.

To resume an existing dataset, copy its preserved artifacts into the selected
local artifact directory. During repository cleanup, byte-for-byte copies were
preserved under `local/pr-cleanup-archive/pr-9/benchmark/`, with an
`archive-manifest.json` recording original paths, destination paths, sizes, and
SHA-256 hashes. The v3 items and v8 review artifacts are preserved under
`local/pr-cleanup-archive/pr-10/`, with its own checksum manifest. Historical
method reports and revision proposals are in these archives too. These local archives are not part of a fresh checkout.

The v3 specification can reuse the archived 320 v2 input windows by copying
only `items.jsonl` into `local/benchmark/v3/`. Generate the v3 taxonomy and
collect new reference annotations against its v8 codebook; v2 reference
answers and gold do not evaluate the changed v8 rules. V3 reference annotation
and candidate evaluation remain to be performed.

To build a new corpus benchmark, first make the transcripts, metadata database,
and lexical scan available and configure `[paths]` in the selected spec.
`transcripts` and `metadata_db` use the downloader's local data layout; set
`scan_dir` to your lexical scan directory. Use
[the lexical scanner](lexical-scan.md) to regenerate the sampling tables from
the same selected specification. Its output must be a new directory;
configure the selected spec's `scan_dir` when choosing another location.
A limited smoke scan is not a complete sampling frame. Then draw and screen
candidate windows:

```bash
.venv/bin/python -m analysis.lexical_scan --workers 1
.venv/bin/python -m analysis.benchmark pool
.venv/bin/python -m analysis.benchmark screen tasks --run-id screening
# Complete each screening bundle, then ingest its outputs:
.venv/bin/python -m analysis.benchmark screen ingest local/benchmark-tasks/screen/screening
.venv/bin/python -m analysis.benchmark select
```

Use `synthetic tasks` / `synthetic ingest` to author planted cases and
`contrast tasks` / `contrast ingest` for controlled edits to existing windows.
These commands prepare or validate bundles; generating model answers is a
separate step. Selected corpus windows retain stable units, timestamps,
provenance, strata, and deterministic dev/test splits.

## Reference annotation and adjudication

At least two independent annotators are needed for consensus gold. Prepare
bundles for each annotator, label only the supplied inputs, and assemble each
bundle's per-window output before ingestion:

```bash
.venv/bin/python -m analysis.benchmark reference tasks --annotator opus-a --run-id reference
# For each bundle:
.venv/bin/python -m analysis.benchmark assemble-result --bundle <bundle-directory>
.venv/bin/python -m analysis.benchmark reference ingest \
    local/benchmark-tasks/reference/opus-a-reference --annotator opus-a --model <model-id>
# Repeat for other independent annotators, then:
.venv/bin/python -m analysis.benchmark aggregate
.venv/bin/python -m analysis.benchmark adjudicate tasks --run-id adjudication
.venv/bin/python -m analysis.benchmark adjudicate ingest local/benchmark-tasks/adjudicate/adjudication
.venv/bin/python -m analysis.benchmark aggregate
```

Aggregation clusters matching atoms into required, acceptable, singleton, or
rejected tiers. Required atoms have agreement from at least two ordinary
annotators; an annotator with authority 2 can also make an atom required.
Adjudicated acceptable atoms earn precision credit without adding required
recall targets. Raw pre-repair annotations are retained for audit.

## Candidate runs and scoring

Candidate labeling uses the production pipeline and selected scheme's prompt.
Model, API, reasoning, sampling, validation mode, and rubric changes belong
to the run fingerprint; server endpoints represent interchangeable capacity. Hosted inference incurs the provider's normal costs.

```bash
.venv/bin/python -m analysis.benchmark run --name candidate \
    --pipeline-config benchmark/pipeline-deepseek.toml -- --reasoning-effort high
.venv/bin/python -m analysis.benchmark score local/benchmark/v3/runs/candidate
.venv/bin/python -m analysis.benchmark compare <run-a> <run-b> --level parent
```

Use the selected artifact directory in run paths (for flat v1 this is
`local/benchmark/runs/`). `score` writes `score.json` and `scorecard.md` beside
the run. Test-item details stay hidden unless `--show-test` is requested.
`compare` uses paired bootstrap intervals on matching items.

Granular scores report topics at subtopic, parent, and domain levels. Coarser
gold is built by re-clustering references using the hierarchy, so sibling
subtopics can agree at their parent. Narrative, population, frame, evidence,
claim, and product scores retain their own axes. `--alias parent` and
`--alias domain` are available on hierarchical benchmarks; `--alias v5-84`
maps flat v6 topics to the older 84-label scheme symmetrically.

## Historical v2 results

The archived v2 evaluation used 320 windows and three independent Opus 5.5
passes, yielding 10,121 gold atoms. Pairwise topic F1 was about 0.86 at the
subtopic level and 0.87 at the parent level; strict leave-one-out topic F1 was
about 0.92. All references and adjudication came from one model family, so
these numbers measure consistency with that codebook and model. Historical
reports, detailed metrics, and the v8 revision proposal remain in the local
archive; they are not required to run the maintained code or tests.
