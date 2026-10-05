# Benchmark scorecard: v8-qwen397-b24k

Model `Qwen/Qwen3.5-397B-A17B-GPTQ-Int4` | api `chat_completions` | effort `high` | prompt `granular-v8:445123e19aed0c47` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.601 | 0.648 |
| Topic F1 (soft) | 0.590 | 0.633 |
| Topic F1 (adjacent credit) | 0.605 | 0.648 |
| Topic recall (required) | 0.504 | 0.578 |
| Topic precision | 0.745 | 0.737 |
| Narrative F1 (soft) | 0.577 | 0.246 |
| Narrative F1 (strict) | 0.586 | 0.240 |
| Frame F1 (soft) | 0.511 | 0.410 |
| Evidence F1 (soft) | 0.451 | 0.384 |
| Population F1 (soft) | 0.580 | 0.597 |
| Claim recall (required) | 0.639 | 0.714 |
| Claim precision | 0.605 | 0.639 |
| Product F1 (soft) | 0.739 | 0.788 |
| Topic yield ratio | 0.544 | 0.625 |
| Claim yield ratio | 0.877 | 0.894 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.745 / 0.504 / 0.601 | 0.648 | 0.558 | 0.832 |
| parent | 0.779 / 0.558 / 0.650 | 0.691 | 0.611 | 0.845 |
| domain | 0.761 / 0.588 / 0.663 | 0.710 | 0.640 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.558 | 0.745 (0.736 to 0.754) | - |
| detection:narrative | 0.539 | 0.799 (0.785 to 0.818) | - |
| detection:frame | 0.493 | 0.784 (0.778 to 0.792) | - |
| detection:evidence | 0.440 | 0.735 (0.721 to 0.742) | - |
| detection:population | 0.589 | 0.809 (0.782 to 0.841) | - |
| claim | 0.595 | 0.785 (0.783 to 0.787) | - |
| product | 0.752 | 0.913 (0.906 to 0.924) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.810 / 0.867 / 0.837 | 0.840 | 0.864 | 0.925 | 0.875 | 0.841 | 0.855 / 0.875 / 0.865 | 0.941 |
| ds-r1 | 160 | 0.846 / 0.848 / 0.847 | 0.851 | 0.826 | 0.789 | 0.895 | 0.800 | 0.868 / 0.835 / 0.851 | 0.946 |
| ds-r2 | 160 | 0.824 / 0.802 / 0.813 | 0.816 | 0.768 | 0.871 | 0.882 | 0.801 | 0.857 / 0.849 / 0.853 | 0.978 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- frame:optimization -> frame:commercialization: 6
- evidence:vague_research -> evidence:weak_human_evidence: 5 *
- frame:conflict_of_interest -> frame:big_pharma: 3
- evidence:expert_consensus -> evidence:strength_assertion: 3
- evidence:specific_study -> evidence:vague_research: 2 *
- topic:supplements.other_compounds -> topic:cognition.focus_productivity: 2
- evidence:mechanistic_explanation -> evidence:vague_research: 2 *
- topic:supplements.other_compounds -> topic:longevity.nad_sirtuins: 2
- evidence:official_data_documents -> evidence:expert_consensus: 2
- topic:weight.weight_loss_methods -> topic:endocrine.thyroid: 2
- topic:womens.female_hormones -> topic:weight.body_composition: 2
- topic:food.general_nutrition -> topic:digital_health.online_health_information: 2

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
| claim:claim_type | 467.0 | 0.728 | 0.724 | - | 0.804 |
| claim:discourse_role | 467.0 | 0.979 | 0.974 | - | 0.800 |
| claim:expressed_certainty | 467.0 | 0.799 | 0.796 | 0.504 | 0.860 |
| claim:relevance | 467.0 | 0.949 | 0.940 | - | 0.789 |
| detection:discourse_role | 832.0 | 0.959 | 0.954 | - | 0.767 |
| detection:relevance | 832.0 | 0.886 | 0.890 | - | 0.779 |
| product:mention_role | 83.0 | 0.879 | 0.883 | - | 0.866 |
| product:product_name | 83.0 | 0.928 | 0.928 | - | 0.813 |
| product:product_type | 83.0 | 0.868 | 0.872 | - | 0.975 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.025 atoms per window, share with any output 0.025
- Contrast pairs: targeted pass rate 0.444 over 15 pairs; decoy pass rate 0.500; collateral change 0.701 vs no-op 0.815; 3 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 1.000, 1.000 requests per accepted window, rejected by kind {}; annotations repaired {'certainty_set_unhedged': 88, 'span_widened_for_certainty_marker': 17, 'span_widened_for_quote': 475}, dropped {'certainty_markers_mismatch': 104, 'duplicate_annotation': 2, 'mixed_or_unknown_labels': 47, 'non_verbatim_quote': 427, 'reversed_span': 28, 'span_out_of_window': 17}
- Cost: 5841 output tokens per accepted window, - USD per accepted window, 1188.600 s per request
- Calibration: confidence AUROC 0.619 (TP mean 0.872, FP mean 0.847)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.645 | 0.765 | 0.787 | 0.414 | 0.837 |
| contrast | 15.0 | 0.603 | 0.486 | 0.615 | 0.627 | 0.727 |
| discourse | 20.0 | 0.547 | 0.611 | 0.640 | 0.681 | 0.408 |
| health_dense | 40.0 | 0.616 | 0.513 | 0.648 | 0.722 | 0.775 |
| mixed | 40.0 | 0.594 | 0.878 | 0.789 | 0.250 | 0.598 |
| narrative | 60.0 | 0.570 | 0.562 | 0.624 | 0.708 | 0.831 |
| null | 40.0 | 0.000 | 0.250 | 0.000 | - | - |
| rare_label | 70.0 | 0.556 | 0.584 | 0.613 | 0.611 | 0.742 |
| synthetic | 15.0 | 0.608 | 0.619 | 0.687 | 0.676 | 0.900 |

## Error classes (headline strata, first repeat)

- miss:detection:topic:same_axis_wrong_label: 267.0
- false_positive:claim:spurious: 185.0
- false_positive:detection:topic:same_axis_wrong_label: 139.0
- miss:claim:nothing_predicted: 126.0
- miss:detection:evidence:cross_axis: 86.0
- miss:claim:different_claim: 82.0
- false_positive:claim:different_claim: 70.0
- miss:detection:frame:cross_axis: 62.0
- miss:detection:topic:span_only: 61.0
- miss:detection:topic:nothing_predicted: 53.0
- miss:detection:topic:cross_axis: 43.0
- miss:detection:evidence:same_axis_wrong_label: 38.0
- false_positive:detection:frame:cross_axis: 38.0
- false_positive:detection:frame:same_axis_wrong_label: 32.0
- false_positive:detection:evidence:same_axis_wrong_label: 29.0
- false_positive:detection:evidence:cross_axis: 28.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.559 | 0.545 | 0.493 | 0.429 | 0.575 | 0.593 | 0.737 |
| ds-r1 | 0.553 | 0.548 | 0.493 | 0.455 | 0.577 | 0.596 | 0.763 |
| ds-r2 | 0.564 | 0.523 | 0.492 | 0.434 | 0.615 | 0.597 | 0.757 |
| ref ds-r0|ds-r1 | 0.754 | 0.818 | 0.792 | 0.742 | 0.806 | 0.787 | 0.908 |
| ref ds-r0|ds-r2 | 0.743 | 0.785 | 0.781 | 0.741 | 0.841 | 0.783 | 0.906 |
| ref ds-r1|ds-r2 | 0.736 | 0.795 | 0.778 | 0.721 | 0.782 | 0.786 | 0.924 |
