# Labeling methods on the granular v7 and v8 label sets (2026-10-04)

What was measured, on gpu313 (4x H100), about how to label transcript windows
with the granular taxonomies: DeepSeek-V4-Flash configurations, ensembles and a
second pass, keyword methods, Clef and Clef-flash, Qwen3.5-397B, and screens in
front of the labeler. Code is in `exp/` on branch `exp/v7-v8-labeling-methods`
(the `labeling-v8` branch plus the serving scripts from
`labeling-codebook-throughput` and the TypeSafe/Clef code from
`feat/clef-labeling`); run directories are under `benchmark/v2/runs/`,
`benchmark/v3/runs/` and `exp/corpus/` (gitignored).

## Summary

1. **DeepSeek-V4-Flash at high effort with a 24k thinking budget is still the
   right single-pass labeler.** On v7: topic F1 0.740 (parent 0.767), claims
   0.798, against a leave-one-out reference ceiling of ~0.92. Unbounded thinking
   is not better (evidence +0.04, nothing else moves, +12% tokens); `low` effort
   costs 0.05 topic F1 and 0.07 claim recall; thinking off is unusable (topic F1
   0.49).
2. **A second "review and complete" pass is the biggest quality lever found.**
   The window plus the first pass's JSON, asked to add what was missed and fix
   what is wrong: topic F1 +0.054 [+0.041, +0.067], claim recall +0.093, evidence
   +0.061, narratives +0.037 on v7 (paired bootstrap), and the same on v8 (+0.046
   topic, +0.100 claim recall, every axis but population significant). It ties
   the union of two independent passes, at the same cost, and beats it on parent
   F1 and claim recall. Refining only windows whose first pass found something
   loses nothing (the second pass almost never finds content the first missed
   entirely) and on real corpus windows costs **~2.2x the decode of one pass**.
3. **v8 behaves as designed.** On the same windows it uses bare parents half as
   often (4.3% -> 2.4% of topics) and `unlisted_narrative` a fifth as often
   (12.3% -> 2.3%), puts output on a quarter as many null-stratum atoms, is
   slightly more self-consistent on topics, frames and narratives, and on real
   corpus windows labels 55% of windows instead of 67% at 18% fewer decode
   tokens; what v7 labels and v8 does not is mostly crime and death narration,
   loose psychiatric words and sports talk, exactly the boundary cases the v8
   corpus review targeted. Against the v7 gold it scores lower (topic 0.678 vs
   0.740), which is the definitional change, not a regression that can be read
   without v8 gold.
4. **Keyword methods are not labelers.** The best lexicon (DeepSeek-authored,
   630 labels, ~18k terms) reaches topic F1 0.34 (parent 0.42), narratives
   0.24-0.32. As hints appended to the window they help a little (v7 topic F1
   +0.024, evidence +0.033, claim recall -0.03), far less than a second pass.
5. **Screens barely pay for DeepSeek on v8.** The best screen, Clef-flash's
   "broad" gate, passes 43% of real windows and keeps 99.2% of the labeler's
   substantive topics and 98.9% of its claims (89% of passing mentions), at ~13
   windows/s per H100; but DeepSeek already spends little on non-health windows
   (median 972 output tokens), so skipping 57% of windows saves only ~9% of its
   decode. Keyword screens look excellent on the benchmark and are much leakier
   on real windows (the benchmark was sampled with the same lexicon).
6. CLEF_SUMMARY
7. QWEN_SUMMARY

What to do with it: label with DeepSeek high/24k plus a refine pass on non-empty
windows if the ~2.2x decode is affordable; otherwise one pass. Do not put a
screen in front of it unless decode is the binding constraint and losing ~10% of
passing mentions is acceptable.

## How each label set was measured

**v7** has a benchmark (`benchmark/v2`: 320 windows, three Opus 5.5 reference
passes, adjudicated gold). Headline numbers are the five corpus strata pooled
over dev and test (160 windows), strict F1 against `required` + adjudicated
`acceptable` gold, mean over repeats; the narrative stratum is reported
separately. The leave-one-out ceiling (an Opus pass scored against the other
two) is 0.92 to 0.94 on every axis. Nothing in the DeepSeek configurations was
tuned on dev, and their order is the same on the test split (table at the end).

**v8** has no gold yet (the v3 reference pass is on hold). It was measured three
ways:

1. **Against the v7 gold, through a label map** (`exp/alias-v8-to-v7.json`, via
   `score --alias <file>`): renamed narratives to their v7 names, new narratives
   to `narrative:unlisted_narrative`, new subtopics to their parent (the v7 bare
   parent), new populations and `frame:industry_distrust` dropped as unscorable.
   This is biased against v8 wherever the v8 codebook deliberately changed a
   decision, so it is read for *differences between v8 methods*, not as v8
   quality.
2. **Silver gold**: three repeats of DeepSeek-high on the v8 prompt registered as
   annotators in a copy of the benchmark (`exp/silver-v8`), gold = 2-of-3, no
   adjudication (`exp/make_silver.sh`, `exp/silver_score.sh`). The same
   construction on v7 (`exp/silver-v7`) reproduces the gold's order when the
   gaps are large (high > low > none > keywords) but compresses them and can
   swap close calls, and it favours DeepSeek-like output; it is used only for
   coarse "how close to DeepSeek-high" reads.
3. **Behaviour that needs no gold**: self-agreement between repeats, use of the
   gap detectors, output on null windows, yields and tokens on real windows.

**Corpus sample.** 2,000 windows drawn at random from the 15,362 windows of
1,000 random episodes (`prod-sample-1000`), labeled by DeepSeek-high under v8
(`exp/corpus/v8-high`); 600 of them also under v7. Screens are read against
these labels for pass rate and retention: benchmark strata are curated, so
benchmark pass rates mean nothing, and the benchmark's corpus items were drawn
with the fast scan's lexicon, which flatters every keyword screen.

## DeepSeek-V4-Flash configurations (v7, benchmark/v2)

Headline strata, 160 windows; one to three repeats (high: 3).

| run | topic P | topic R | topic F1 | parent F1 | narr F1 | frame F1 | evid F1 | pop F1 | claim P | claim R | claim F1 | prod F1 | null atoms/w | out tok/w |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high, 24k budget | 0.858 | 0.636 | 0.740 | 0.767 | 0.803 | 0.796 | 0.695 | 0.828 | 0.881 | 0.720 | 0.798 | 0.854 | 0.35 | 19.5k |
| high, no budget | 0.861 | 0.638 | 0.744 | 0.775 | 0.793 | 0.795 | 0.744 | 0.742 | 0.857 | 0.699 | 0.778 | 0.858 | 0.48 | 21.8k |
| low, 24k budget | 0.875 | 0.587 | 0.715 | 0.731 | 0.759 | 0.765 | 0.655 | 0.794 | 0.878 | 0.676 | 0.770 | 0.860 | 0.28 | 13.7k |
| thinking off | 0.629 | 0.375 | 0.485 | 0.556 | 0.375 | 0.431 | 0.345 | 0.421 | 0.808 | 0.409 | 0.552 | 0.637 | 0.21 | 2.1k |
| high + keyword hints | 0.832 | 0.688 | 0.763 | 0.803 | 0.767 | 0.775 | 0.736 | 0.832 | 0.880 | 0.700 | 0.786 | 0.878 | 0.35 | 20.6k |
| high + refine pass | 0.828 | 0.741 | **0.790** | **0.821** | 0.809 | 0.814 | 0.732 | 0.862 | 0.822 | **0.817** | **0.824** | 0.848 | 0.48 | 19.5k + 22.2k |
| refine only non-empty first passes | 0.831 | 0.739 | 0.790 | 0.819 | 0.809 | 0.813 | 0.732 | 0.855 | 0.823 | 0.817 | 0.824 | 0.851 | 0.40 | |
| union of 2 high repeats | 0.825 | 0.738 | 0.787 | 0.793 | 0.771 | 0.819 | 0.747 | 0.864 | 0.842 | 0.782 | 0.816 | 0.859 | 0.48 | 2 x 19.4k |
| union of 3 | 0.805 | 0.775 | 0.797 | 0.797 | 0.775 | 0.826 | 0.739 | 0.854 | 0.810 | 0.825 | 0.822 | 0.840 | 0.53 | 3 x |
| 2-of-3 vote | 0.907 | 0.625 | 0.748 | 0.757 | 0.839 | 0.802 | 0.724 | 0.817 | 0.918 | 0.705 | 0.802 | 0.865 | 0.33 | 3 x |
| refine + one more repeat (union) | 0.807 | 0.788 | 0.804 | 0.803 | 0.773 | 0.818 | 0.753 | 0.856 | 0.800 | 0.840 | 0.824 | 0.846 | 0.58 | 3 x |

Paired bootstrap against one high repeat (305 shared item-repeat rows; 95% CI):

| metric | refine | union of 2 | no budget | low | keyword hints |
| --- | --- | --- | --- | --- | --- |
| topic F1 | +0.054 [0.041, 0.067] | +0.045 [0.035, 0.056] | +0.001 [-0.015, 0.017] | -0.053 [-0.074, -0.033] | +0.024 [0.004, 0.043] |
| topic recall | +0.109 | +0.094 | +0.004 | -0.073 | +0.055 |
| topic precision | -0.033 | -0.035 | -0.007 | -0.003 | -0.029 |
| narrative F1 | +0.037 [0.011, 0.065] | +0.019 | +0.033 | -0.014 | +0.003 |
| frame F1 | +0.026 [0.009, 0.045] | +0.034 | +0.020 | -0.035 | +0.012 |
| evidence F1 | +0.061 [0.043, 0.079] | +0.065 | +0.037 [0.013, 0.061] | -0.020 | +0.033 |
| claim recall | +0.093 [0.077, 0.108] | +0.070 | -0.011 | -0.070 | -0.031 |
| claim precision | -0.048 | -0.035 | -0.012 | +0.006 | +0.014 |

Refine against union of 2: everything within noise except claim recall +0.022
[0.007, 0.037] for refine.

What the residual error is: under-calling. Precision is 0.83-0.88 everywhere
and recall is where configurations differ; the labels with the lowest recall at
high effort are `evidence:weak_human_evidence` (0.26), `topic:genetics.inheritance`
(0.23), `frame:political_partisan` (0.33), `topic:wellness.lifestyle_pillars`
(0.36) and `evidence:evidence_limits` (0.39), with precision 0.77-1.00. DeepSeek
agrees with itself less (topic 0.74 between repeats) than the three Opus passes
agree with each other (0.86), which is why pooling two passes, or asking a pass
to review another, recovers so much.

The refine prompt is in `exp/xlabel.py` (`REFINE_NOTE`): the production
request, plus "a first-pass annotation follows; it was made quickly and usually
misses things; add every ... it missed, correct wrong labels, spans and
attributes, remove what the codebook excludes; return the complete corrected
annotation". Of the 42 benchmark windows whose first pass was empty, the
refine pass left 37 empty and added a few atoms to five, which is why refining
only non-empty windows scores the same.

## v8

### Against the v7 gold (label map) and with the same methods

| run | topic F1 | parent F1 | narr F1 | frame F1 | evid F1 | pop F1 | claim P | claim R | claim F1 | prod F1 | null atoms/w | out tok/w |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v7 high 24k | 0.740 | 0.767 | 0.803 | 0.796 | 0.695 | 0.828 | 0.881 | 0.720 | 0.798 | 0.854 | 0.35 | 19.5k |
| v8 high 24k | 0.678 | 0.714 | 0.676 | 0.749 | 0.657 | 0.760 | 0.920 | 0.632 | 0.755 | 0.859 | 0.09 | 17.6k |
| v8 thinking off | 0.468 | 0.532 | 0.444 | 0.412 | 0.262 | 0.417 | 0.833 | 0.411 | 0.558 | 0.647 | 0.13 | 2.0k |
| v8 + keyword hints | 0.678 | 0.730 | 0.709 | 0.746 | 0.706 | 0.797 | 0.926 | 0.639 | 0.762 | 0.823 | 0.13 | 19.1k |
| v8 union of 2 | 0.707 | 0.721 | 0.721 | 0.785 | 0.711 | 0.814 | 0.898 | 0.721 | 0.805 | 0.869 | 0.10 | 2 x |
| v8 + refine | 0.720 | 0.764 | 0.736 | 0.789 | 0.717 | 0.794 | 0.883 | 0.723 | 0.802 | 0.910 | 0.10 | 17.6k + 20.7k |

v8 refine against one v8 high repeat (paired): topic F1 +0.046 [0.035, 0.058],
recall +0.078, precision -0.016; narrative +0.049, frame +0.049, evidence
+0.056, product +0.039, claim recall +0.100 [0.081, 0.124], claim precision
-0.043; population within noise. The methods order exactly as on v7.

Where v8 departs from the v7 gold is mostly by design: new subtopics (e.g.
`metabolic.mitochondria_energy`, `food.general_nutrition`) map to a bare parent
where v7 coders had picked a sibling subtopic, and the stricter health-content
boundary removes content the v7 gold kept (mixed-stratum claim recall 0.71 ->
0.48; null-stratum gold atoms are mostly not labeled).

### Behaviour on the same windows

| | v7 | v8 |
| --- | --- | --- |
| bare parent share of topic labels (benchmark, per pass) | 4.3% | 2.4% |
| `unlisted_narrative` share of narratives | 12.3% | 2.3% |
| new v8 labels used per pass (320 windows) | - | 212 |
| null-stratum windows with any output (40) | 7 | 2.5 |
| repeat self-agreement topic / frame / narrative / claim | 0.737 / 0.767 / 0.790 / 0.808 | 0.754 / 0.794 / 0.826 / 0.787 |
| corpus windows with any output (600 windows) | 67.3% | 55.2% |
| corpus output tokens per window, mean / median | 10.9k / 7.5k | 9.0k / 3.1k |
| corpus topic detections / claims per window | 3.66 / 2.78 | 2.85 / 2.13 |

80 of those 600 corpus windows are labeled by v7 and not v8 (6 the other way);
their v7 topics are mostly `acute_care` (crime and death narration), `mental`
(loose psychiatric words), `musculoskeletal` and `fitness` (sports), and two
thirds of their detections are `passing`. The v8 prompt is ~87k tokens (v7
~45k); with prefix caching the prefill is cheap, but decode attends over the
longer context: at 512 concurrent sequences the server held 5.8-6.9k tok/s on
the mixed v7/v8 workload against 10.3k measured earlier with the 12k-token v6
prompt.

### Silver (v8 methods against DeepSeek-high v8)

Silver scores are agreement with DeepSeek-high, not quality; the v7 silver
check shows they preserve large gaps.

| run | topic F1 | parent F1 | narr F1 | frame F1 | evid F1 | claim F1 |
| --- | --- | --- | --- | --- | --- | --- |
| v7 silver: high, no budget | 0.832 | 0.850 | 0.865 | 0.889 | 0.850 | 0.871 |
| v7 silver: low | 0.813 | 0.817 | 0.837 | 0.847 | 0.787 | 0.854 |
| v7 silver: thinking off | 0.518 | 0.576 | 0.357 | 0.437 | 0.383 | 0.582 |
| v7 silver: keyword labeler | 0.269 | 0.327 | 0.250 | 0.234 | 0.215 | - |
| v8 silver: keyword hints | 0.816 | 0.839 | 0.823 | 0.847 | 0.798 | 0.880 |
| v8 silver: thinking off | 0.540 | 0.580 | 0.483 | 0.457 | 0.324 | 0.603 |
| v8 silver: keyword labeler | 0.268 | 0.338 | 0.289 | 0.299 | 0.212 | - |
CLEF_SILVER

## Keyword methods

Three lexicons, all in the `exp/keywords.py` format:

- **concepts**: each label's `concepts` examples from the taxonomy;
- **LLM-authored**: DeepSeek-high wrote 8-40 phrases and up to 6 co-occurrence
  regexes per label from its definition (`exp/keywords.py llm`; 577 / 630
  labels, ~17.5k terms, ~1.7k regexes per version; ~80 requests);
- **corpus review**: the regexes the v8 corpus reviewers quoted in their reports
  (51 labels) and, as a screen, the union of the 1,136 cq.py patterns the
  topic and narrative reviewers actually ran (the query log from the lab
  server).

As labelers (v7 gold, headline):

| lexicon | topic P | topic R | topic F1 | parent F1 | narr F1 | frame F1 | evid F1 | pop F1 | null atoms/w |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| concepts | 0.381 | 0.285 | 0.341 | 0.375 | 0.125 | 0.196 | 0.119 | 0.178 | 4.8 |
| LLM-authored | 0.245 | 0.538 | 0.343 | 0.419 | 0.241 | 0.251 | 0.212 | 0.264 | 9.3 |
| LLM-authored, 2+ hits per span | 0.391 | 0.243 | 0.314 | 0.427 | 0.199 | 0.157 | 0.089 | 0.333 | 1.5 |
| LLM-authored v8 (mapped) | 0.246 | 0.489 | 0.334 | 0.432 | 0.322 | 0.329 | 0.214 | 0.269 | 6.3 |

No claims or products. A keyword hit is not a topic: ads, metaphors, time
markers and passing words all match, and the subtopic choice needs context.
As **hints** (the matched terms and their labels appended to the window as a
checklist, `--mode hints`): see the DeepSeek tables; a small recall gain on
topics and evidence, a small loss on claims.

## Screens

A screen scores each window; windows below a threshold are not labeled. Read on
the 2,000 corpus windows against DeepSeek-high v8 (pass rate = share of windows
sent on; retention = share of the labeler's atoms in passed windows), at the
loosest threshold that keeps 99% (or 98%) of substantive topics plus claims:

| screen | cost | pass rate | substantive topics | claims | passing topics | ad topics | products | labeler decode saved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Clef-flash broad gate >= 0.49 | ~13 windows/s/H100 | **0.431** | 0.992 | 0.989 | 0.891 | 0.963 | 0.977 | 9.0% |
| Clef-flash broad gate >= 0.57 (98%) | | 0.391 | 0.984 | 0.977 | 0.861 | 0.954 | 0.972 | 11.5% |
| Clef (27B) broad gate >= 0.50 | ~4.5 windows/s/H100 | 0.506 | 0.993 | 0.988 | 0.931 | 0.967 | 0.982 | 6.8% |
| DeepSeek, strict screen prompt, "passing" or ad (98%) | ~32 out tokens | 0.487 | 0.983 | 0.978 | 0.881 | 1.000 | 0.982 | 9.9% |
| DeepSeek, broad screen prompt, "passing" | ~32 out tokens | 0.696 | 0.998 | 0.991 | 0.975 | 0.967 | 0.977 | 3.4% |
| DeepSeek strict screen OR lexicon-v2 hit | | 0.511 | 0.991 | 0.982 | 0.915 | 0.917 | 0.967 | 8.4% |
| TF-IDF + logistic regression (episode-grouped CV) | CPU, ms | 0.771 | 0.996 | 0.986 | 0.924 | 0.979 | 0.987 | |
| TF-IDF (98%) | | 0.683 | 0.991 | 0.973 | 0.886 | 0.963 | 0.975 | 7.4% |
| LLM-authored lexicon, 3+ units (98%) | CPU | 0.755 | 0.985 | 0.978 | 0.935 | 0.933 | 0.959 | 5.9% |
| corpus-review queries, 1+ unit (95%) | CPU | 0.762 | 0.976 | 0.977 | 0.934 | 0.933 | 0.924 | |
| lexicon-v2 (fast scan), 1+ unit | CPU | 0.372 | 0.870 | 0.795 | 0.679 | 0.737 | 0.768 | |

Two things decide whether a screen is worth having:

- **The labeler is already cheap on what the screen removes.** DeepSeek v8
  spends a median 972 output tokens on a corpus window (mean 5.5k; 6.7% think
  past 24k); 59% of windows get no labels, and they are the cheap ones. Even a
  perfect screen that dropped exactly the empty windows would save ~10-15% of
  decode. The Clef-flash gate saves 9% for losing ~1% of substantive content and
  ~11% of passing mentions; across the corpus that is ~43 DeepSeek node-hours
  saved for ~11 node-hours of Clef-flash (2.03M windows at ~13/s/GPU).
- **The benchmark cannot measure it.** On the benchmark every keyword screen
  keeps 96-99% at high pass rates (lexicon-v2: 99.7% of substantive topics),
  because the benchmark's corpus items were drawn with that lexicon; on real
  windows lexicon-v2 keeps 87%.

The DeepSeek screen prompts are in `exp/xlabel.py`. The strict one copies v8's
boundary rules and misses mental health, sport and ad-with-a-claim windows the
labeler then labels; the broad one ("when in doubt, pass it") fixes that and
passes 70%.

CLEF_SECTION

QWEN_SECTION

## Cost per window on real traffic (v8, DeepSeek-V4-Flash, one node)

| configuration | output tokens per corpus window | relative |
| --- | --- | --- |
| high, 24k budget, one pass | 5.5k mean (sample of 2,000); 9.0k on the denser 600-window subset | 1.0 |
| + refine on non-empty first passes | +10.8k on the 600-window subset | ~2.2 |
| + Clef-flash screen in front | -9% | ~0.91 |
| v7 prompt instead of v8 | +21% on the 600-window subset | ~1.2 |

At the 5.8-6.9k tok/s this node held with ~87k-token prompts, one v8 pass over
the 2.03M-window corpus is roughly 450-550 node-hours; with refine, about twice
that. These are estimates from a shared, mixed workload, not a clean
single-configuration throughput test.

## Split check (v7 gold; nothing here was tuned on dev)

| run | dev topic F1 | test topic F1 | dev claim F1 | test claim F1 |
| --- | --- | --- | --- | --- |
| v7 high | 0.742 | 0.735 | 0.790 | 0.813 |
| v7 low | 0.711 | 0.721 | 0.772 | 0.765 |
| v7 hints | 0.774 | 0.740 | 0.787 | 0.785 |
| v7 refine | 0.795 | 0.780 | 0.825 | 0.822 |
| v7 union of 2 | 0.785 | 0.791 | 0.808 | 0.832 |
| v8 high | 0.675 | 0.683 | 0.755 | 0.755 |
| v8 refine | 0.717 | 0.727 | 0.790 | 0.825 |

## Caveats

- v8 numbers are not v8 quality. The label map, silver gold and behavioural
  measures say how methods compare under v8 and how v8 differs from v7; whether
  v8's boundary decisions are right needs the v3 reference pass.
- All references are Opus, and silver is DeepSeek; a method of another family
  (Clef, Qwen) is judged against those readings.
- Corpus retention is retention of DeepSeek-high's labels, so a screen is
  credited for keeping DeepSeek's false positives too.
- Throughput was measured on a shared server running several configurations
  at once.

## Reproducing

```bash
# DeepSeek server (v8 needs the longer context)
MAX_NUM_SEQS=512 MAX_MODEL_LEN=196608 analysis/serving/serve-deepseek-v4.sh
# production-path runs
BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark run --name v7-high-b24k \
    --pipeline-config benchmark/pipeline-local.toml --repeats 3 --split all
# variants
.venv/bin/python exp/xlabel.py --bench v2 --name v7-refine --mode refine --base-run benchmark/v2/runs/v7-high-b24k
.venv/bin/python exp/xlabel.py --bench v2 --name v7-hints-llm --mode hints --lexicon exp/lexicon-llm-v2.json
.venv/bin/python exp/combine.py union --out benchmark/v2/runs/v7-union2 benchmark/v2/runs/v7-high-b24k:0 benchmark/v2/runs/v7-high-b24k:1
# v8 against the v7 gold
BENCHMARK_DIR=benchmark/v2 .venv/bin/python -m analysis.benchmark score --alias exp/alias-v8-to-v7.json benchmark/v3/runs/v8-refine
# screens
.venv/bin/python exp/clef_screen.py --prefix clef-flash --model clef-flash --api http://127.0.0.1:8301/v1 --windows <windows> --ids-file exp/corpus/sample4000.ids
.venv/bin/python exp/operating_points.py clef-flash-broad ds-screen tfidf-any
python3 exp/summarize.py benchmark/v2/runs/*
```
