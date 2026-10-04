# Benchmark scorecard: v8-none

Model `deepseek-ai/DeepSeek-V4-Flash-0731` | api `chat_completions` | effort `none` | prompt `granular-v8:445123e19aed0c47` | repeats 2 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.536 | 0.549 |
| Topic F1 (soft) | 0.520 | 0.537 |
| Topic F1 (adjacent credit) | 0.536 | 0.550 |
| Topic recall (required) | 0.467 | 0.486 |
| Topic precision | 0.629 | 0.630 |
| Narrative F1 (soft) | 0.520 | 0.339 |
| Narrative F1 (strict) | 0.518 | 0.377 |
| Frame F1 (soft) | 0.452 | 0.451 |
| Evidence F1 (soft) | 0.361 | 0.204 |
| Population F1 (soft) | 0.474 | 0.213 |
| Claim recall (required) | 0.501 | 0.502 |
| Claim precision | 0.773 | 0.724 |
| Product F1 (soft) | 0.698 | 0.646 |
| Topic yield ratio | 0.584 | 0.613 |
| Claim yield ratio | 0.534 | 0.549 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.629 / 0.467 / 0.536 | 0.549 | 0.498 | 0.832 |
| parent | 0.662 / 0.514 / 0.578 | 0.584 | 0.539 | 0.845 |
| domain | 0.682 / 0.556 / 0.612 | 0.573 | 0.565 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.498 | 0.745 (0.736 to 0.754) | 0.443 |
| detection:narrative | 0.481 | 0.799 (0.785 to 0.818) | 0.379 |
| detection:frame | 0.421 | 0.784 (0.778 to 0.792) | 0.342 |
| detection:evidence | 0.348 | 0.735 (0.721 to 0.742) | 0.356 |
| detection:population | 0.430 | 0.809 (0.782 to 0.841) | 0.395 |
| claim | 0.558 | 0.785 (0.783 to 0.787) | 0.536 |
| product | 0.641 | 0.913 (0.906 to 0.924) | 0.624 |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.810 / 0.867 / 0.837 | 0.840 | 0.864 | 0.925 | 0.875 | 0.841 | 0.855 / 0.875 / 0.865 | 0.941 |
| ds-r1 | 160 | 0.846 / 0.848 / 0.847 | 0.851 | 0.826 | 0.789 | 0.895 | 0.800 | 0.868 / 0.835 / 0.851 | 0.946 |
| ds-r2 | 160 | 0.824 / 0.802 / 0.813 | 0.816 | 0.768 | 0.871 | 0.882 | 0.801 | 0.857 / 0.849 / 0.853 | 0.978 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- evidence:specific_study -> evidence:vague_research: 5 *
- topic:alcohol.drinking_culture -> topic:alcohol.health_effects: 4
- frame:disclaimer -> frame:commercialization: 4
- topic:musculoskeletal.chronic_pain -> topic:infectious.other_infections: 2
- topic:womens.female_hormones -> topic:endocrine.hormone_balance: 2
- topic:cognition.neurochemistry_talk -> topic:endocrine.hormone_balance: 2
- topic:womens.hormone_therapy -> topic:endocrine.other_hormones: 2
- evidence:expert_consensus -> evidence:vague_research: 2
- frame:disclaimer -> frame:correction_debunking: 2
- frame:toxin_purity -> frame:correction_debunking: 2
- evidence:personal_anecdote -> evidence:preclinical_extrapolation: 2
- evidence:personal_anecdote -> evidence:clinical_experience: 2 *

## Contrast pairs on the reference annotators themselves

Each annotator's own labels of base and twin, scored like a candidate. A perturbation no annotator passes is a twin or spec problem, not a labeler failure.

| annotator | pass rate | decoy pass | collateral | no-op collateral |
| --- | --- | --- | --- | --- |
| ds-r0 | 0.667 | 1.000 | 0.461 | 0.348 |
| ds-r1 | 0.444 | 1.000 | 0.463 | 0.552 |
| ds-r2 | 0.444 | 0.500 | 0.449 | 0.474 |

## Attribute agreement on matched atoms

| attribute | n | exact | vote share | weighted kappa | reference alpha |
| --- | --- | --- | --- | --- | --- |
| claim:claim_type | 341.0 | 0.692 | 0.683 | - | 0.804 |
| claim:discourse_role | 341.0 | 0.943 | 0.943 | - | 0.800 |
| claim:expressed_certainty | 341.0 | 0.642 | 0.641 | 0.323 | 0.860 |
| claim:relevance | 341.0 | 0.971 | 0.961 | - | 0.789 |
| detection:discourse_role | 709.5 | 0.945 | 0.943 | - | 0.767 |
| detection:relevance | 709.5 | 0.884 | 0.887 | - | 0.779 |
| product:mention_role | 70.5 | 0.863 | 0.882 | - | 0.866 |
| product:product_name | 70.5 | 0.839 | 0.839 | - | 0.813 |
| product:product_type | 70.5 | 0.914 | 0.907 | - | 0.975 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.125 atoms per window, share with any output 0.050
- Contrast pairs: targeted pass rate 0.667 over 15 pairs; decoy pass rate 0.000; collateral change 1.056 vs no-op 1.214; 3 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 1.000, 1.000 requests per accepted window, rejected by kind {}; annotations repaired {'certainty_marker_dropped': 2, 'certainty_set_unhedged': 48, 'span_widened_for_certainty_marker': 116, 'span_widened_for_quote': 628}, dropped {'certainty_markers_mismatch': 169, 'duplicate_annotation': 157, 'invalid_field': 4, 'mixed_or_unknown_labels': 139, 'non_verbatim_quote': 315, 'reversed_span': 84, 'span_out_of_window': 102}
- Cost: 1983 output tokens per accepted window, - USD per accepted window, 1234.000 s per request
- Calibration: confidence AUROC 0.511 (TP mean 0.880, FP mean 0.872)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.614 | 1.005 | 0.525 | 0.593 | 0.675 |
| contrast | 15.0 | 0.477 | 0.603 | 0.591 | 0.704 | 0.723 |
| discourse | 20.0 | 0.383 | 0.514 | 0.471 | 0.822 | 0.309 |
| health_dense | 40.0 | 0.562 | 0.558 | 0.521 | 0.793 | 0.793 |
| mixed | 40.0 | 0.371 | 0.649 | 0.289 | 0.373 | 0.221 |
| narrative | 60.0 | 0.474 | 0.536 | 0.425 | 0.797 | 0.688 |
| null | 40.0 | 0.000 | 0.625 | 0.500 | 0.500 | - |
| rare_label | 70.0 | 0.454 | 0.494 | 0.459 | 0.748 | 0.608 |
| synthetic | 15.0 | 0.514 | 0.593 | 0.545 | 0.820 | 0.691 |

## Error classes (headline strata, first repeat)

- miss:detection:topic:same_axis_wrong_label: 266.5
- miss:claim:nothing_predicted: 236.0
- false_positive:detection:topic:same_axis_wrong_label: 146.0
- miss:detection:topic:nothing_predicted: 124.5
- miss:detection:evidence:cross_axis: 94.5
- false_positive:detection:topic:span_only: 72.5
- miss:claim:different_claim: 72.0
- false_positive:claim:spurious: 67.5
- miss:detection:frame:cross_axis: 46.5
- miss:detection:frame:nothing_predicted: 43.0
- miss:detection:topic:span_only: 43.0
- miss:detection:evidence:same_axis_wrong_label: 40.0
- miss:detection:topic:cross_axis: 39.5
- false_positive:detection:topic:spurious: 33.0
- false_positive:claim:different_claim: 32.5
- false_positive:detection:frame:same_axis_wrong_label: 31.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.496 | 0.494 | 0.424 | 0.350 | 0.408 | 0.556 | 0.630 |
| ds-r1 | 0.501 | 0.477 | 0.421 | 0.339 | 0.434 | 0.557 | 0.648 |
| ds-r2 | 0.497 | 0.472 | 0.418 | 0.354 | 0.448 | 0.559 | 0.645 |
| ref ds-r0|ds-r1 | 0.754 | 0.818 | 0.792 | 0.742 | 0.806 | 0.787 | 0.908 |
| ref ds-r0|ds-r2 | 0.743 | 0.785 | 0.781 | 0.741 | 0.841 | 0.783 | 0.906 |
| ref ds-r1|ds-r2 | 0.736 | 0.795 | 0.778 | 0.721 | 0.782 | 0.786 | 0.924 |
