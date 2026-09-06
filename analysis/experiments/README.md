# Labeling experiment harness

The evaluation rig behind `docs/labeling-experiments-2026-09-06.md`. Nothing
here is part of the pipeline; it exists to measure changes to it. Every script
writes to its own run directory and none of them touch `outputs/`.

Run from the repo root with the project venv.

## Building a slice

    .venv/bin/python analysis/experiments/build_slice.py <outdir>

Draws a fixed stratified slice from `outputs/fullrun` — health-dense, ad-heavy,
zero-yield in equal parts — and writes `windows.jsonl.zst`,
`prepare_manifest.json` and `reference.json` (the pilot's existing labels for
those windows). A random draw is ~70% zero-yield and measures almost nothing,
which is why the strata exist.

    .venv/bin/python analysis/experiments/build_otherhealth.py <outdir> <taxonomy.json> [n]

The same, but drawn from the windows the pilot could only label
`other_health_topic` — the slice that can actually test added topics.

Both write the taxonomy SHA into the manifest, so a slice is pinned to the
label set it will be run against; `label` refuses a mismatch.

## Running a variant

    EVAL_DIR=<slice> [EVAL_TAXONOMY=<taxonomy.json>] \
      analysis/experiments/run_variant.sh <name> [label flags...]

Runs `topic_labeling.py label` over the slice into `runs/<name>`, times it, and
scores it. Needs a config naming only live endpoints: config flags are
*prepended* to argv and `--api-base` appends, so a dead endpoint listed in the
tracked config stays in the pool and the run fails on it.

`sweep_effort.sh` and `final_queue.sh` are the batches of variants that were
actually run; `final_queue.sh` still holds the two unfinished ones (the
taxonomy A/B and the production candidate).

## Scoring

    .venv/bin/python analysis/experiments/score.py <run> <slice>/reference.json [name]
    .venv/bin/python analysis/experiments/compare.py <runA> <runB> <reference.json>
    .venv/bin/python analysis/experiments/project_corpus.py <run> <reference.json>

`score.py` compares a run to the pilot reference, in both directions — the
reference is a comparison point, not truth, so a variant that finds something it
missed is a disagreement and not an error.

`compare.py` compares two runs to *each other*, which is the only way to isolate
one variable: scoring against the reference conflates whatever changed with the
v5 prompt it was produced by. It also reports claim-`relevance` agreement.

`project_corpus.py` reweights per-stratum token cost by the pilot's real stratum
shares. The slice costs 2.12x the corpus average per window, so slice figures
projected directly overstate the corpus.

## Screening (closed — negative results)

`keyword_screen.py`, `screen_tiers.py`, `ad_nearmatch.py` and `ad_detect.py` are
the screening experiments. They are kept because the result is a finding: all-
empty batches are 40.6% of the pilot's full batches but 7.0% of its output
tokens, so no screen can pay for itself. See the findings doc.
