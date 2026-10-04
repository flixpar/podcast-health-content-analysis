# Benchmark scorecard: v7-hints-llm

Model `deepseek-ai/DeepSeek-V4-Flash-0731` | api `None` | effort `None` | prompt `granular-v7:0406a404e1c06f54` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.814 | 0.816 |
| Topic F1 (soft) | 0.793 | 0.791 |
| Topic F1 (adjacent credit) | 0.814 | 0.819 |
| Topic recall (required) | 0.806 | 0.820 |
| Topic precision | 0.821 | 0.812 |
| Narrative F1 (soft) | 0.838 | 0.813 |
| Narrative F1 (strict) | 0.862 | 0.857 |
| Frame F1 (soft) | 0.844 | 0.802 |
| Evidence F1 (soft) | 0.817 | 0.788 |
| Population F1 (soft) | 0.868 | 0.875 |
| Claim recall (required) | 0.819 | 0.850 |
| Claim precision | 0.926 | 0.911 |
| Product F1 (soft) | 0.925 | 0.951 |
| Topic yield ratio | 0.795 | 0.796 |
| Claim yield ratio | 0.730 | 0.762 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.821 / 0.806 / 0.814 | 0.816 | 0.723 | 0.827 |
| parent | 0.832 / 0.822 / 0.827 | 0.843 | 0.752 | 0.844 |
| domain | 0.843 / 0.822 / 0.833 | 0.844 | 0.762 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.723 | 0.742 (0.737 to 0.747) | - |
| detection:narrative | 0.771 | 0.794 (0.790 to 0.796) | - |
| detection:frame | 0.758 | 0.771 (0.766 to 0.779) | - |
| detection:evidence | 0.735 | 0.735 (0.732 to 0.739) | - |
| detection:population | 0.807 | 0.801 (0.788 to 0.809) | - |
| claim | 0.793 | 0.798 (0.791 to 0.808) | - |
| product | 0.909 | 0.914 (0.911 to 0.918) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.803 / 0.843 / 0.822 | 0.834 | 0.879 | 0.846 | 0.895 | 0.806 | 0.851 / 0.893 / 0.872 | 0.968 |
| ds-r1 | 160 | 0.768 / 0.880 / 0.820 | 0.830 | 0.879 | 0.818 | 0.845 | 0.818 | 0.877 / 0.909 / 0.893 | 0.938 |
| ds-r2 | 160 | 0.839 / 0.839 / 0.839 | 0.845 | 0.861 | 0.849 | 0.906 | 0.812 | 0.843 / 0.874 / 0.858 | 0.942 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- topic:food.sugar_sweeteners -> topic:sleep.sleep_duration_quality: 1
- topic:food.ultra_processed -> topic:food.eating_behavior: 1
- topic:diets.plant_based -> topic:cancer_alt.metabolic_dietary: 1
- topic:diets.raw_food_juicing -> topic:cancer_alt.natural_remedies: 1
- topic:diets.plant_based -> topic:diets.ancestral_paleo: 1
- evidence:mechanistic_explanation -> evidence:credential_appeal: 1
- evidence:preclinical_extrapolation -> evidence:mechanistic_explanation: 1
- evidence:personal_anecdote -> evidence:mechanistic_explanation: 1
- evidence:personal_anecdote -> evidence:credential_appeal: 1
- topic:endocrine -> topic:cardiovascular.heart_disease: 1
- topic:endocrine.hormone_balance -> topic:endocrine.other_hormones: 1
- topic:supplements.magnesium -> topic:endocrine.other_hormones: 1

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
| claim:claim_type | 673.0 | 0.822 | 0.821 | - | 0.803 |
| claim:discourse_role | 673.0 | 0.969 | 0.965 | - | 0.804 |
| claim:expressed_certainty | 673.0 | 0.923 | 0.914 | 0.837 | 0.838 |
| claim:relevance | 673.0 | 0.964 | 0.953 | - | 0.821 |
| detection:discourse_role | 1533.0 | 0.975 | 0.972 | - | 0.738 |
| detection:relevance | 1533.0 | 0.892 | 0.886 | - | 0.781 |
| product:mention_role | 104.0 | 0.952 | 0.942 | - | 0.913 |
| product:product_name | 104.0 | 0.952 | 0.952 | - | 0.855 |
| product:product_type | 104.0 | 0.971 | 0.965 | - | 0.971 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.350 atoms per window, share with any output 0.175
- Contrast pairs: targeted pass rate 0.636 over 15 pairs; decoy pass rate 1.000; collateral change 0.428 vs no-op 0.300; 1 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 1.000, 1.000 requests per accepted window, rejected by kind {}; annotations repaired {'certainty_marker_dropped': 1, 'span_widened_for_certainty_marker': 3, 'span_widened_for_quote': 162}, dropped {'invalid_field': 2, 'non_verbatim_quote': 28, 'span_out_of_window': 44}
- Cost: 20626 output tokens per accepted window, - USD per accepted window, 2531.400 s per request
- Calibration: confidence AUROC 0.634 (TP mean 0.838, FP mean 0.799)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.805 | 0.821 | 0.872 | 0.861 | 0.982 |
| contrast | 15.0 | 0.833 | 0.822 | 0.771 | 0.923 | 0.966 |
| discourse | 20.0 | 0.766 | 0.795 | 0.822 | 0.923 | 0.730 |
| health_dense | 40.0 | 0.795 | 0.795 | 0.830 | 0.931 | 0.942 |
| mixed | 40.0 | 0.807 | 0.783 | 0.795 | 0.939 | 0.826 |
| narrative | 60.0 | 0.760 | 0.752 | 0.771 | 0.936 | 0.890 |
| null | 40.0 | 0.818 | 0.706 | 0.500 | 1.000 | - |
| rare_label | 70.0 | 0.787 | 0.808 | 0.813 | 0.924 | 0.957 |
| synthetic | 15.0 | 0.810 | 0.815 | 0.824 | 0.959 | 0.857 |

## Error classes (headline strata, first repeat)

- false_positive:detection:topic:same_axis_wrong_label: 112.0
- miss:detection:topic:same_axis_wrong_label: 112.0
- miss:claim:nothing_predicted: 80.0
- false_positive:detection:topic:span_only: 51.0
- miss:claim:different_claim: 42.0
- miss:detection:topic:span_only: 41.0
- false_positive:claim:different_claim: 31.0
- miss:detection:evidence:cross_axis: 29.0
- false_positive:claim:spurious: 20.0
- miss:detection:topic:nothing_predicted: 20.0
- miss:detection:frame:same_axis_wrong_label: 18.0
- miss:detection:frame:cross_axis: 18.0
- false_positive:detection:evidence:cross_axis: 16.0
- false_positive:detection:evidence:same_axis_wrong_label: 12.0
- false_positive:detection:frame:same_axis_wrong_label: 10.0
- miss:detection:narrative:cross_axis: 9.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.728 | 0.764 | 0.761 | 0.723 | 0.826 | 0.787 | 0.914 |
| ds-r1 | 0.724 | 0.777 | 0.743 | 0.749 | 0.805 | 0.805 | 0.902 |
| ds-r2 | 0.719 | 0.773 | 0.769 | 0.732 | 0.789 | 0.787 | 0.910 |
| ref ds-r0|ds-r1 | 0.737 | 0.790 | 0.767 | 0.735 | 0.805 | 0.808 | 0.911 |
| ref ds-r0|ds-r2 | 0.747 | 0.796 | 0.779 | 0.732 | 0.809 | 0.791 | 0.912 |
| ref ds-r1|ds-r2 | 0.743 | 0.796 | 0.766 | 0.739 | 0.788 | 0.796 | 0.918 |
