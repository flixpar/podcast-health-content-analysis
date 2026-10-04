# Granular labeling scheme (taxonomy v7, prompt v7)

The v7 scheme replaces the flat 84/91-label taxonomy with a two-level topic
tree, adds named contested narratives and a population axis, and comes with a
much more detailed prompt. It runs through the same pipeline
(`analysis/topic_labeling.py`); the flat taxonomy keeps working unchanged.

| file | what |
| --- | --- |
| `taxonomy/health-v7.md` | the label set: one source for all five axes |
| `taxonomy/codebook-v7.md` | the task definition; reference annotators label against it and the prompt embeds it |
| `analysis/prompts/rubric-v7.md` | labeler-specific preamble: purpose, an eight-pass procedure, calibration, a validated worked example |
| `benchmark/v2/` | the benchmark built on this scheme (see `docs/benchmark.md`) |

## Why more granular

The research questions are about exactly what is discussed: which vaccine,
which supplement, which cancer remedy, which storyline. A flat label such as
"Vaccines & Immunization" or "Functional Nutrition & Supplements" cannot answer
them, and the v1 benchmark showed that the broad labels were also where coders
disagreed: the biggest topic error was missing co-labels on stacked broad
topics (population, policy, intervention), and the least reliable labels were
the broadest (`other_health_topic`, `public_health_policy`, `childrens_health`,
`purity_contamination`, `optimization_framing`). Specific subtopics with
written boundaries give a coder something concrete to recognise instead of a
judgement about how far a broad category reaches.

The pilot bears this out (12 windows, two independent Opus coders, before the
codebook revision): agreement on topic **subtopics** was F1 0.85 and on parent
topics 0.87, against 0.81 for the best v1 pair (Opus vs Opus) on the coarser
v6 labels; narratives 0.91, claims 0.87, products 0.97, populations 1.00.
Evidence signals were the weakest axis (0.74), and the codebook revision
targeted it.

The full benchmark (`benchmark/v2`, 320 windows, three independent Opus 5.5
passes after the revision) confirms it: pairwise topic F1 0.86 at the
subtopic level and 0.87 at the parent level, narratives 0.87, frames 0.87,
evidence 0.86 (up from 0.74), populations 0.87 to 0.89, claims 0.89,
products 0.94. See `docs/benchmark.md`, Version 2.

## The five axes

| axis | labels | what it answers |
| --- | --- | --- |
| topic | 60 parents in 13 domains, 349 subtopics (`topic:<parent>.<subtopic>`) | what specifically is discussed |
| narrative | 121 named propositions in 9 families (`narrative:<id>`) | which recurring contested claims come up, and in what stance |
| frame | 22 (`frame:<id>`) | how it is framed: distrust by target, conspiracy, insinuating questions, naturalness, toxins, optimization, fear, medical freedom, partisan and spiritual framing, MAHA, commercialization, disclaimers, corrections |
| evidence | 16 (`evidence:<id>`) | what support is invoked: specific vs vague research, official data, consensus, prestige, credentials, clinical experience, anecdotes, mechanisms, preclinical or weak evidence, tradition, foreign comparison, media sources, acknowledged limits |
| population | 9 (`population:<id>`) | whose health it is about |

Design decisions, each made to remove a disagreement the v1 data showed:

- **Labelers apply the most specific subtopic.** The bare parent ID means "this
  parent, no listed subtopic fits" and doubles as a per-parent gap detector:
  its summaries say what the taxonomy is missing. Parents and domains are
  derived, never coded alongside a subtopic.
- **Population is its own axis.** Children's, women's and men's health were
  stacked onto every subject in v1 and coded inconsistently. Now
  `topic:vaccines.childhood_schedule` + `population:infants` says both things
  once; population-defined parents (`pediatrics`, `womens`, `mens`) keep only
  subjects that exist only for that group.
- **Narratives are single propositions, coded in any stance.** The narrative
  axis measures exposure (`discourse_role` gives endorse / question / report /
  rebut), so a debunking show and a promoting show both register, and can be
  told apart. Two-sided debates are two narratives (`hrt_dangerous` /
  `hrt_fears_overblown`), so the role always means the same thing. The list is
  seeded from the 80 lexicon narratives the fast scan validated on the corpus
  (88.7% precision) plus MAHA-era and wellness narratives; `unlisted_narrative`
  surfaces new ones.
- **Topical conspiracies moved from frames to narratives.** v6's
  `covid_conspiracy`, `cancer_conspiracy`, `food_conspiracy`... were
  propositions, not rhetoric. Frames are now rhetoric only, with distrust split
  by target (agencies, medicine, pharma, food industry, media).
- **Explicit co-labeling rules** (codebook 5.1) for intervention + outcome,
  policy on the subject's own subtopic, institutions as subject vs rhetoric,
  substances keep their own home, population-specific subtopics + condition.
- **Claims link to narratives** (`narrative_ids`) and carry `relevance`, so a
  checkable claim can be traced to its storyline and ad copy is separable.
- **Certainty-marker rules** settle the cases coders split on in v1 and in the
  pilot: capacity "can", quantifier hedges, unnamed attribution, intensifiers,
  ranges, superlatives and universal negations.

## The prompt

The v7 prompt is the rubric, then the codebook verbatim, then the label tables
rendered as markdown grouped by domain and parent. The codebook-throughput
experiments found that using the codebook itself as the prompt raised topic F1
by 0.05 and made claim and product types far more consistent; v7 builds on
that. The rubric adds an eight-pass procedure (health stretches, topics,
narratives, frames and evidence, population, claims, products, a self-check),
calibration (expected yields, empty answers), and a worked example whose output
is validated by the test suite. The assembled prefix is about 180k characters,
roughly 45k tokens, prompt-cached across requests.

That length has one operational consequence: on a local vLLM server the
`--max-model-len 65536` used for v6 leaves too little room for high-effort
reasoning. Serve v7 with `--max-model-len 131072` or more (DeepSeek-V4-Flash
supports 1M), and keep prefix caching on.

The prompt's identity in the run fingerprint is `granular-v7:<hash>`, a hash of
the assembled text, so editing the rubric, codebook or taxonomy is always a
new run.

## Running it

```bash
.venv/bin/python analysis/topic_labeling.py prepare --topics taxonomy/health-v7.md \
    --metadata-db downloader/data/podcast_metadata.db --output-dir analysis/output/topic-labeling-v7
.venv/bin/python analysis/topic_labeling.py label --output-dir analysis/output/topic-labeling-v7
.venv/bin/python analysis/topic_labeling.py merge --output-dir analysis/output/topic-labeling-v7
```

Results use schema `topic-labeling-v5`. Merged outputs add, under v7:
`parent_topic_id` and `domain` on topic annotations; `narrative_annotations`
and `population_annotations` on clips; `narrative_ids`, `narrative_names`,
`parent_topic_ids` and `relevance` on verification candidates; and
`narrative_ids` / `population_ids` columns in `review_queue.csv`. The per-window
caps are 60 detections, 30 claims and 30 products. Product types add
`nicotine_or_tobacco` and `household_or_home`.

## Changing the taxonomy

Edit `taxonomy/health-v7.md`; the compiler fails closed on malformed rows,
missing definitions, unknown narrative home topics and missing axes, and the
test suite checks that every backticked cross-reference in definitions and the
codebook names a real label. A changed label set is a new benchmark version:
recompile `benchmark/v2/taxonomy.json` only together with re-annotation.
