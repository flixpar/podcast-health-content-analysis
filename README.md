# Podcast health-content analysis

A research pipeline for collecting podcast episodes, reconstructing historical
chart populations, transcribing audio, and labeling health-related content.
The current label scheme is **taxonomy v8**. Labeling records topics,
narratives, framing, evidence signals and claims; determining whether a claim
is true requires the separate evidence-verification workflow.

## Start here

| Work | Guide | Maintained entry point |
| --- | --- | --- |
| Collect and transcribe episodes | [Downloader](downloader/README.md) | `downloader/podcast_pipeline/` |
| Select and export a reproducible population | [Studies](docs/studies.md) | `podcast_pipeline study` |
| Reconstruct historical chart populations | [Chart archive](analysis/chart_archive/README.md) | `analysis/chart_archive/` |
| Prepare, label, merge and review content | [Labeling](docs/labeling.md) | `analysis/topic_labeling.py` |
| Build sampling tables | [Lexical scan](docs/lexical-scan.md) | `python -m analysis.lexical_scan` |
| Annotate and evaluate a benchmark | [Benchmark](docs/benchmark.md) | `python -m analysis.benchmark` |
| Inspect transcript context | [Corpus search](analysis/corpus_text/README.md) | `analysis/corpus_text/cq.py` |
| Serve GLM for v8 labeling | [Serving](docs/glm53-serving.md) | `analysis/serving/` |
| Use the optional flat-label cascade | [TypeSafe](docs/typesafe-labeling.md) | `analysis/topic-labeling-typesafe.toml` |

## Environment and checks

The locked project targets Python 3.13 on Linux x86-64. Dependencies are
managed by `uv`. Audio tools require `ffmpeg` and `ffprobe`; corpus search
requires `rg` (ripgrep).

For offline development and the full test suite, use a separate environment:

```bash
UV_PROJECT_ENVIRONMENT=local/test-venv uv sync --locked --only-group test
local/test-venv/bin/python -m pytest
```

This installs the CPU test dependencies. Tests replace network and model
clients with local fixtures; they require no credentials or model weights.
Audio tests skip when their required ffmpeg tools/codecs are unavailable.
Test discovery is limited to the maintained analysis and downloader suites.

For collection, local Parakeet transcription and analysis:

```bash
uv sync --locked --group analysis
cp downloader/config.example.json downloader/config.json
# Set paths and the intended ASR backend before collection.
(cd downloader && ../.venv/bin/python -m podcast_pipeline --help)
.venv/bin/python analysis/topic_labeling.py --help
```

The production environment includes PyTorch, NeMo and CUDA dependencies.
Remote Qwen, pyannote VAD and labeling servers have separate setup instructions
in their guides. Keep server/model environments separate from the test
installation. [Development guidance](docs/development.md) describes checks,
configuration conventions and how to extend the pipeline.

## Inputs, state and results

Git contains source code, tests, portable configuration templates, taxonomy
sources, codebooks, rubrics, sampling lexicons and annotator specifications.
The v8 sources are `taxonomy/health-v8.md`, `taxonomy/codebook-v8.md` and
`analysis/prompts/rubric-v8.md`. V7 and flat sources remain for explicitly
selected earlier schemes; TypeSafe supports the flat scheme only.

The shared catalog, audio and transcripts live under the downloader's
configured data directory. Research outputs, compiled taxonomies, benchmark
items/answers/gold, task bundles and run results belong under ignored `local/`
or the configured data volume. Select the current benchmark explicitly:

```bash
BENCHMARK_DIR=benchmark/v3 local/test-venv/bin/python -m analysis.benchmark taxonomy
```

The v3 specification is maintained, but new reference annotation is required
for v8 evaluation. Older gold and dated performance/research findings retain
the scope recorded in their guides. Historical outputs and superseded working
documents are preserved in local archives; a new checkout can generate source
artifacts and run tests without those archives. Original study documents in
`docs/original/` provide historical context and the legacy flat source.
