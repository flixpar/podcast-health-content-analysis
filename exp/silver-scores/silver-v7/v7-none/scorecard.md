# Benchmark scorecard: v7-none

Model `deepseek-ai/DeepSeek-V4-Flash-0731` | api `chat_completions` | effort `none` | prompt `granular-v7:0406a404e1c06f54` | repeats 2 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.524 | 0.504 |
| Topic F1 (soft) | 0.508 | 0.490 |
| Topic F1 (adjacent credit) | 0.534 | 0.515 |
| Topic recall (required) | 0.451 | 0.467 |
| Topic precision | 0.628 | 0.548 |
| Narrative F1 (soft) | 0.365 | 0.283 |
| Narrative F1 (strict) | 0.367 | 0.327 |
| Frame F1 (soft) | 0.423 | 0.449 |
| Evidence F1 (soft) | 0.369 | 0.367 |
| Population F1 (soft) | 0.441 | 0.239 |
| Claim recall (required) | 0.431 | 0.523 |
| Claim precision | 0.779 | 0.805 |
| Product F1 (soft) | 0.630 | 0.703 |
| Topic yield ratio | 0.548 | 0.637 |
| Claim yield ratio | 0.439 | 0.524 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.628 / 0.451 / 0.524 | 0.504 | 0.457 | 0.827 |
| parent | 0.665 / 0.507 / 0.575 | 0.577 | 0.522 | 0.844 |
| domain | 0.683 / 0.546 / 0.607 | 0.574 | 0.549 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.457 | 0.742 (0.737 to 0.747) | 0.426 |
| detection:narrative | 0.367 | 0.794 (0.790 to 0.796) | 0.289 |
| detection:frame | 0.396 | 0.771 (0.766 to 0.779) | 0.326 |
| detection:evidence | 0.345 | 0.735 (0.732 to 0.739) | 0.375 |
| detection:population | 0.430 | 0.801 (0.788 to 0.809) | 0.278 |
| claim | 0.553 | 0.798 (0.791 to 0.808) | 0.536 |
| product | 0.656 | 0.914 (0.911 to 0.918) | 0.644 |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.803 / 0.843 / 0.822 | 0.834 | 0.879 | 0.846 | 0.895 | 0.806 | 0.851 / 0.893 / 0.872 | 0.968 |
| ds-r1 | 160 | 0.768 / 0.880 / 0.820 | 0.830 | 0.879 | 0.818 | 0.845 | 0.818 | 0.877 / 0.909 / 0.893 | 0.938 |
| ds-r2 | 160 | 0.839 / 0.839 / 0.839 | 0.845 | 0.861 | 0.849 | 0.906 | 0.812 | 0.843 / 0.874 / 0.858 | 0.942 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- evidence:specific_study -> evidence:vague_research: 9 *
- topic:endocrine.hormone_balance -> topic:endocrine.other_hormones: 4
- frame:anti_mainstream_medicine -> frame:correction_debunking: 3 *
- topic:musculoskeletal.joints_arthritis -> topic:oral.dental_procedures: 3
- frame:anti_mainstream_medicine -> frame:anti_expert_populist: 3
- topic:supplements.other_compounds -> topic:food.plant_foods_fiber: 3
- narrative:lockdowns_worse_than_virus -> narrative:pandemic_censorship: 2
- evidence:strength_assertion -> evidence:personal_anecdote: 2
- evidence:clinical_experience -> evidence:mechanistic_explanation: 2
- frame:fear_alarm -> frame:toxin_purity: 2
- frame:anti_expert_populist -> frame:commercialization: 2
- frame:naturalness_appeal -> frame:correction_debunking: 2

## Contrast pairs on the reference annotators themselves

Each annotator's own labels of base and twin, scored like a candidate. A perturbation no annotator passes is a twin or spec problem, not a labeler failure.

| annotator | pass rate | decoy pass | collateral | no-op collateral |
| --- | --- | --- | --- | --- |
| ds-r0 | 0.636 | 1.000 | 0.506 | 0.455 |
| ds-r1 | 0.636 | 0.500 | 0.543 | 0.333 |
| ds-r2 | 0.455 | 0.500 | 0.455 | 0.450 |

## Attribute agreement on matched atoms

| attribute | n | exact | vote share | weighted kappa | reference alpha |
| --- | --- | --- | --- | --- | --- |
| claim:claim_type | 368.5 | 0.736 | 0.721 | - | 0.803 |
| claim:discourse_role | 368.5 | 0.958 | 0.949 | - | 0.804 |
| claim:expressed_certainty | 368.5 | 0.607 | 0.607 | 0.415 | 0.838 |
| claim:relevance | 368.5 | 0.944 | 0.941 | - | 0.821 |
| detection:discourse_role | 763.5 | 0.933 | 0.931 | - | 0.738 |
| detection:relevance | 763.5 | 0.878 | 0.877 | - | 0.781 |
| product:mention_role | 71.5 | 0.895 | 0.909 | - | 0.913 |
| product:product_name | 71.5 | 0.902 | 0.902 | - | 0.855 |
| product:product_type | 71.5 | 0.923 | 0.918 | - | 0.971 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.212 atoms per window, share with any output 0.062
- Contrast pairs: targeted pass rate 0.500 over 15 pairs; decoy pass rate 0.000; collateral change 1.038 vs no-op 1.040; 1 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 1.000, 1.000 requests per accepted window, rejected by kind {}; annotations repaired {'certainty_marker_dropped': 13, 'certainty_set_unhedged': 57, 'span_widened_for_certainty_marker': 123, 'span_widened_for_quote': 585}, dropped {'certainty_markers_mismatch': 234, 'duplicate_annotation': 171, 'mixed_or_unknown_labels': 109, 'non_verbatim_quote': 392, 'reversed_span': 109}
- Cost: 2108 output tokens per accepted window, - USD per accepted window, 1102.800 s per request
- Calibration: confidence AUROC 0.489 (TP mean 0.882, FP mean 0.882)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.456 | 0.783 | 0.513 | 0.639 | 0.624 |
| contrast | 15.0 | 0.519 | 0.632 | 0.525 | 0.801 | 0.665 |
| discourse | 20.0 | 0.460 | 0.624 | 0.466 | 0.848 | 0.380 |
| health_dense | 40.0 | 0.547 | 0.577 | 0.472 | 0.811 | 0.755 |
| mixed | 40.0 | 0.340 | 0.317 | 0.257 | 0.864 | 0.352 |
| narrative | 60.0 | 0.453 | 0.539 | 0.440 | 0.787 | 0.677 |
| null | 40.0 | 0.000 | 0.205 | 0.000 | 0.000 | - |
| rare_label | 70.0 | 0.477 | 0.573 | 0.501 | 0.793 | 0.658 |
| synthetic | 15.0 | 0.411 | 0.514 | 0.482 | 0.880 | 0.610 |

## Error classes (headline strata, first repeat)

- miss:claim:nothing_predicted: 309.5
- miss:detection:topic:same_axis_wrong_label: 281.0
- miss:detection:topic:nothing_predicted: 166.0
- false_positive:detection:topic:same_axis_wrong_label: 163.0
- false_positive:detection:topic:span_only: 106.5
- miss:detection:evidence:cross_axis: 100.5
- miss:claim:different_claim: 76.0
- false_positive:claim:spurious: 55.0
- miss:detection:frame:nothing_predicted: 49.5
- miss:detection:frame:cross_axis: 45.5
- miss:detection:evidence:nothing_predicted: 45.0
- false_positive:detection:frame:same_axis_wrong_label: 43.5
- false_positive:detection:frame:cross_axis: 40.0
- miss:detection:topic:cross_axis: 34.5
- false_positive:claim:different_claim: 33.5
- miss:detection:topic:span_only: 32.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.454 | 0.373 | 0.382 | 0.348 | 0.428 | 0.562 | 0.665 |
| ds-r1 | 0.454 | 0.361 | 0.406 | 0.338 | 0.430 | 0.545 | 0.653 |
| ds-r2 | 0.464 | 0.367 | 0.400 | 0.351 | 0.432 | 0.553 | 0.648 |
| ref ds-r0|ds-r1 | 0.737 | 0.790 | 0.767 | 0.735 | 0.805 | 0.808 | 0.911 |
| ref ds-r0|ds-r2 | 0.747 | 0.796 | 0.779 | 0.732 | 0.809 | 0.791 | 0.912 |
| ref ds-r1|ds-r2 | 0.743 | 0.796 | 0.766 | 0.739 | 0.788 | 0.796 | 0.918 |
