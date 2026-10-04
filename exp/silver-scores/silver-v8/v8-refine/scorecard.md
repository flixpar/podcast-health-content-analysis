# Benchmark scorecard: v8-refine

Model `deepseek-ai/DeepSeek-V4-Flash-0731` | api `None` | effort `None` | prompt `granular-v8:445123e19aed0c47` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.922 | 0.931 |
| Topic F1 (soft) | 0.897 | 0.912 |
| Topic F1 (adjacent credit) | 0.922 | 0.931 |
| Topic recall (required) | 0.924 | 0.953 |
| Topic precision | 0.921 | 0.910 |
| Narrative F1 (soft) | 0.864 | 0.818 |
| Narrative F1 (strict) | 0.870 | 0.875 |
| Frame F1 (soft) | 0.885 | 0.882 |
| Evidence F1 (soft) | 0.868 | 0.830 |
| Population F1 (soft) | 0.928 | 0.847 |
| Claim recall (required) | 0.937 | 0.956 |
| Claim precision | 0.920 | 0.858 |
| Product F1 (soft) | 0.914 | 0.954 |
| Topic yield ratio | 0.846 | 0.913 |
| Claim yield ratio | 0.882 | 0.985 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.921 / 0.924 / 0.922 | 0.931 | 0.796 | 0.832 |
| parent | 0.924 / 0.931 / 0.928 | 0.933 | 0.815 | 0.845 |
| domain | 0.931 / 0.921 / 0.926 | 0.926 | 0.820 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.796 | 0.745 (0.736 to 0.754) | - |
| detection:narrative | 0.822 | 0.799 (0.785 to 0.818) | - |
| detection:frame | 0.817 | 0.784 (0.778 to 0.792) | - |
| detection:evidence | 0.763 | 0.735 (0.721 to 0.742) | - |
| detection:population | 0.845 | 0.809 (0.782 to 0.841) | - |
| claim | 0.816 | 0.785 (0.783 to 0.787) | - |
| product | 0.924 | 0.913 (0.906 to 0.924) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.810 / 0.867 / 0.837 | 0.840 | 0.864 | 0.925 | 0.875 | 0.841 | 0.855 / 0.875 / 0.865 | 0.941 |
| ds-r1 | 160 | 0.846 / 0.848 / 0.847 | 0.851 | 0.826 | 0.789 | 0.895 | 0.800 | 0.868 / 0.835 / 0.851 | 0.946 |
| ds-r2 | 160 | 0.824 / 0.802 / 0.813 | 0.816 | 0.768 | 0.871 | 0.882 | 0.801 | 0.857 / 0.849 / 0.853 | 0.978 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- frame:correction_debunking -> frame:anti_mainstream_medicine: 3
- evidence:preclinical_extrapolation -> evidence:specific_study: 2
- frame:disclaimer -> frame:commercialization: 2
- frame:toxin_purity -> frame:commercialization: 1
- topic:food.micronutrients_food -> topic:cancer_alt.metabolic_dietary: 1
- evidence:preclinical_extrapolation -> evidence:mechanistic_explanation: 1
- evidence:specific_study -> evidence:mechanistic_explanation: 1
- narrative:hrt_fears_overblown -> narrative:hrt_dangerous: 1
- topic:cognition.focus_productivity -> topic:cognition.nootropics: 1
- topic:infectious.measles -> topic:vaccines.safety_injury: 1
- topic:weight.weight_gain_causes -> topic:weight: 1
- frame:toxin_purity -> frame:correction_debunking: 1

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
| claim:claim_type | 684.0 | 0.901 | 0.883 | - | 0.804 |
| claim:discourse_role | 684.0 | 0.991 | 0.986 | - | 0.800 |
| claim:expressed_certainty | 684.0 | 0.972 | 0.969 | 0.922 | 0.860 |
| claim:relevance | 684.0 | 0.980 | 0.971 | - | 0.789 |
| detection:discourse_role | 1629.0 | 0.993 | 0.989 | - | 0.767 |
| detection:relevance | 1629.0 | 0.953 | 0.944 | - | 0.779 |
| product:mention_role | 106.0 | 0.962 | 0.940 | - | 0.866 |
| product:product_name | 106.0 | 0.972 | 0.972 | - | 0.813 |
| product:product_type | 106.0 | 0.981 | 0.972 | - | 0.975 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.100 atoms per window, share with any output 0.075
- Contrast pairs: targeted pass rate 0.556 over 15 pairs; decoy pass rate 1.000; collateral change 0.405 vs no-op 0.250; 3 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 1.000, 1.000 requests per accepted window, rejected by kind {}; annotations repaired {'span_widened_for_certainty_marker': 1, 'span_widened_for_quote': 108}, dropped {'non_verbatim_quote': 15}
- Cost: 20749 output tokens per accepted window, - USD per accepted window, 1087.600 s per request
- Calibration: confidence AUROC 0.755 (TP mean 0.833, FP mean 0.746)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.955 | 0.922 | 0.918 | 0.862 | 0.911 |
| contrast | 15.0 | 0.863 | 0.743 | 0.933 | 0.858 | 0.989 |
| discourse | 20.0 | 0.886 | 0.768 | 0.928 | 0.922 | 0.718 |
| health_dense | 40.0 | 0.899 | 0.882 | 0.953 | 0.897 | 0.977 |
| mixed | 40.0 | 0.894 | 0.919 | 0.947 | 0.857 | 0.855 |
| narrative | 60.0 | 0.853 | 0.844 | 0.946 | 0.883 | 0.986 |
| null | 40.0 | 0.933 | 0.750 | 1.000 | 1.000 | - |
| rare_label | 70.0 | 0.894 | 0.851 | 0.956 | 0.877 | 0.980 |
| synthetic | 15.0 | 0.926 | 1.021 | 0.970 | 0.878 | 1.000 |

## Error classes (headline strata, first repeat)

- false_positive:detection:topic:same_axis_wrong_label: 44.0
- false_positive:claim:spurious: 42.0
- miss:detection:topic:same_axis_wrong_label: 33.0
- false_positive:detection:evidence:cross_axis: 27.0
- false_positive:detection:topic:span_only: 26.0
- miss:detection:topic:span_only: 26.0
- false_positive:claim:different_claim: 24.0
- miss:claim:different_claim: 24.0
- false_positive:detection:evidence:same_axis_wrong_label: 12.0
- false_positive:detection:frame:cross_axis: 11.0
- false_positive:detection:frame:same_axis_wrong_label: 11.0
- miss:claim:nothing_predicted: 11.0
- false_positive:detection:evidence:span_only: 9.0
- false_positive:product:different_product: 9.0
- false_positive:detection:narrative:cross_axis: 8.0
- miss:detection:frame:cross_axis: 8.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.893 | 0.870 | 0.886 | 0.836 | 0.906 | 0.884 | 0.946 |
| ds-r1 | 0.758 | 0.815 | 0.785 | 0.723 | 0.791 | 0.787 | 0.912 |
| ds-r2 | 0.738 | 0.782 | 0.779 | 0.729 | 0.839 | 0.776 | 0.913 |
| ref ds-r0|ds-r1 | 0.754 | 0.818 | 0.792 | 0.742 | 0.806 | 0.787 | 0.908 |
| ref ds-r0|ds-r2 | 0.743 | 0.785 | 0.781 | 0.741 | 0.841 | 0.783 | 0.906 |
| ref ds-r1|ds-r2 | 0.736 | 0.795 | 0.778 | 0.721 | 0.782 | 0.786 | 0.924 |
