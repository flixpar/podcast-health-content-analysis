# Benchmark scorecard: v8-hints-llm

Model `deepseek-ai/DeepSeek-V4-Flash-0731` | api `None` | effort `None` | prompt `granular-v8:445123e19aed0c47` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.814 | 0.822 |
| Topic F1 (soft) | 0.794 | 0.797 |
| Topic F1 (adjacent credit) | 0.816 | 0.825 |
| Topic recall (required) | 0.786 | 0.794 |
| Topic precision | 0.843 | 0.851 |
| Narrative F1 (soft) | 0.816 | 0.743 |
| Narrative F1 (strict) | 0.825 | 0.815 |
| Frame F1 (soft) | 0.794 | 0.886 |
| Evidence F1 (soft) | 0.801 | 0.728 |
| Population F1 (soft) | 0.853 | 0.920 |
| Claim recall (required) | 0.815 | 0.911 |
| Claim precision | 0.918 | 0.916 |
| Product F1 (soft) | 0.903 | 0.978 |
| Topic yield ratio | 0.770 | 0.753 |
| Claim yield ratio | 0.735 | 0.799 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.843 / 0.786 / 0.814 | 0.822 | 0.734 | 0.832 |
| parent | 0.867 / 0.809 / 0.837 | 0.843 | 0.760 | 0.845 |
| domain | 0.881 / 0.809 / 0.843 | 0.842 | 0.769 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.734 | 0.745 (0.736 to 0.754) | - |
| detection:narrative | 0.802 | 0.799 (0.785 to 0.818) | - |
| detection:frame | 0.769 | 0.784 (0.778 to 0.792) | - |
| detection:evidence | 0.728 | 0.735 (0.721 to 0.742) | - |
| detection:population | 0.810 | 0.809 (0.782 to 0.841) | - |
| claim | 0.794 | 0.785 (0.783 to 0.787) | - |
| product | 0.906 | 0.913 (0.906 to 0.924) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.810 / 0.867 / 0.837 | 0.840 | 0.864 | 0.925 | 0.875 | 0.841 | 0.855 / 0.875 / 0.865 | 0.941 |
| ds-r1 | 160 | 0.846 / 0.848 / 0.847 | 0.851 | 0.826 | 0.789 | 0.895 | 0.800 | 0.868 / 0.835 / 0.851 | 0.946 |
| ds-r2 | 160 | 0.824 / 0.802 / 0.813 | 0.816 | 0.768 | 0.871 | 0.882 | 0.801 | 0.857 / 0.849 / 0.853 | 0.978 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- evidence:preclinical_extrapolation -> evidence:specific_study: 2
- evidence:preclinical_extrapolation -> evidence:mechanistic_explanation: 2
- topic:weight -> topic:glp1.use_results: 2 *
- topic:cancer.causes_rates -> topic:endocrine.other_hormones: 2
- topic:peds.doping_sport -> topic:endocrine.other_hormones: 2
- topic:sleep.sleep_duration_quality -> topic:sleep.sleep_hygiene_environment: 2
- topic:supplements -> topic:skin_beauty.hair_loss_hair: 1
- topic:self_tracking.wearables -> topic:sleep.insomnia: 1
- topic:alt_medicine.iv_ozone_therapies -> topic:cancer_alt.metabolic_dietary: 1
- topic:supplements.vitamin_c -> topic:cancer_alt.metabolic_dietary: 1
- topic:food.micronutrients_food -> topic:cancer_alt.metabolic_dietary: 1
- evidence:specific_study -> evidence:mechanistic_explanation: 1

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
| claim:claim_type | 572.0 | 0.816 | 0.805 | - | 0.804 |
| claim:discourse_role | 572.0 | 0.979 | 0.975 | - | 0.800 |
| claim:expressed_certainty | 572.0 | 0.956 | 0.953 | 0.863 | 0.860 |
| claim:relevance | 572.0 | 0.963 | 0.959 | - | 0.789 |
| detection:discourse_role | 1339.0 | 0.985 | 0.982 | - | 0.767 |
| detection:relevance | 1339.0 | 0.921 | 0.916 | - | 0.779 |
| product:mention_role | 95.0 | 0.979 | 0.954 | - | 0.866 |
| product:product_name | 95.0 | 0.947 | 0.947 | - | 0.813 |
| product:product_type | 95.0 | 0.968 | 0.965 | - | 0.975 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.125 atoms per window, share with any output 0.050
- Contrast pairs: targeted pass rate 0.556 over 15 pairs; decoy pass rate 1.000; collateral change 0.452 vs no-op 0.143; 3 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 1.000, 1.000 requests per accepted window, rejected by kind {}; annotations repaired {'certainty_marker_dropped': 2, 'span_widened_for_certainty_marker': 3, 'span_widened_for_quote': 183}, dropped {'certainty_markers_mismatch': 1, 'non_verbatim_quote': 35, 'span_out_of_window': 37}
- Cost: 19070 output tokens per accepted window, - USD per accepted window, 2476.300 s per request
- Calibration: confidence AUROC 0.620 (TP mean 0.833, FP mean 0.799)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.826 | 0.902 | 0.853 | 0.897 | 0.969 |
| contrast | 15.0 | 0.780 | 0.760 | 0.808 | 0.913 | 0.884 |
| discourse | 20.0 | 0.811 | 0.791 | 0.843 | 0.935 | 0.812 |
| health_dense | 40.0 | 0.780 | 0.741 | 0.844 | 0.913 | 0.926 |
| mixed | 40.0 | 0.866 | 0.784 | 0.895 | 0.944 | 0.797 |
| narrative | 60.0 | 0.802 | 0.796 | 0.832 | 0.931 | 0.960 |
| null | 40.0 | 0.667 | 0.500 | 1.000 | 1.000 | - |
| rare_label | 70.0 | 0.775 | 0.828 | 0.821 | 0.905 | 0.920 |
| synthetic | 15.0 | 0.852 | 0.866 | 0.746 | 0.877 | 0.900 |

## Error classes (headline strata, first repeat)

- miss:detection:topic:same_axis_wrong_label: 123.0
- false_positive:detection:topic:same_axis_wrong_label: 78.0
- miss:claim:nothing_predicted: 48.0
- false_positive:detection:topic:span_only: 48.0
- miss:detection:topic:span_only: 48.0
- miss:claim:different_claim: 47.0
- false_positive:claim:different_claim: 29.0
- miss:detection:evidence:cross_axis: 26.0
- false_positive:detection:evidence:cross_axis: 21.0
- false_positive:claim:spurious: 18.0
- miss:detection:frame:cross_axis: 17.0
- false_positive:detection:evidence:span_only: 15.0
- miss:detection:narrative:cross_axis: 14.0
- miss:detection:topic:nothing_predicted: 14.0
- miss:detection:frame:same_axis_wrong_label: 13.0
- miss:detection:evidence:same_axis_wrong_label: 12.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.743 | 0.795 | 0.776 | 0.731 | 0.818 | 0.801 | 0.899 |
| ds-r1 | 0.737 | 0.811 | 0.762 | 0.733 | 0.781 | 0.791 | 0.909 |
| ds-r2 | 0.723 | 0.801 | 0.768 | 0.721 | 0.831 | 0.789 | 0.910 |
| ref ds-r0|ds-r1 | 0.754 | 0.818 | 0.792 | 0.742 | 0.806 | 0.787 | 0.908 |
| ref ds-r0|ds-r2 | 0.743 | 0.785 | 0.781 | 0.741 | 0.841 | 0.783 | 0.906 |
| ref ds-r1|ds-r2 | 0.736 | 0.795 | 0.778 | 0.721 | 0.782 | 0.786 | 0.924 |
