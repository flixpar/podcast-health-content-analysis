# Benchmark scorecard: v7-low-b24k

Model `deepseek-ai/DeepSeek-V4-Flash-0731` | api `chat_completions` | effort `low` | prompt `granular-v7:0406a404e1c06f54` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.820 | 0.800 |
| Topic F1 (soft) | 0.783 | 0.776 |
| Topic F1 (adjacent credit) | 0.822 | 0.800 |
| Topic recall (required) | 0.742 | 0.748 |
| Topic precision | 0.917 | 0.860 |
| Narrative F1 (soft) | 0.851 | 0.704 |
| Narrative F1 (strict) | 0.865 | 0.733 |
| Frame F1 (soft) | 0.824 | 0.825 |
| Evidence F1 (soft) | 0.757 | 0.757 |
| Population F1 (soft) | 0.791 | 0.816 |
| Claim recall (required) | 0.802 | 0.792 |
| Claim precision | 0.909 | 0.931 |
| Product F1 (soft) | 0.942 | 0.914 |
| Topic yield ratio | 0.618 | 0.691 |
| Claim yield ratio | 0.718 | 0.698 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.917 / 0.742 / 0.820 | 0.800 | 0.721 | 0.827 |
| parent | 0.945 / 0.721 / 0.818 | 0.815 | 0.748 | 0.844 |
| domain | 0.950 / 0.712 / 0.814 | 0.849 | 0.756 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.721 | 0.742 (0.737 to 0.747) | - |
| detection:narrative | 0.774 | 0.794 (0.790 to 0.796) | - |
| detection:frame | 0.752 | 0.771 (0.766 to 0.779) | - |
| detection:evidence | 0.703 | 0.735 (0.732 to 0.739) | - |
| detection:population | 0.790 | 0.801 (0.788 to 0.809) | - |
| claim | 0.777 | 0.798 (0.791 to 0.808) | - |
| product | 0.901 | 0.914 (0.911 to 0.918) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.803 / 0.843 / 0.822 | 0.834 | 0.879 | 0.846 | 0.895 | 0.806 | 0.851 / 0.893 / 0.872 | 0.968 |
| ds-r1 | 160 | 0.768 / 0.880 / 0.820 | 0.830 | 0.879 | 0.818 | 0.845 | 0.818 | 0.877 / 0.909 / 0.893 | 0.938 |
| ds-r2 | 160 | 0.839 / 0.839 / 0.839 | 0.845 | 0.861 | 0.849 | 0.906 | 0.812 | 0.843 / 0.874 / 0.858 | 0.942 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- topic:covid -> topic:covid.illness_severity: 2
- evidence:credential_appeal -> evidence:strength_assertion: 2
- topic:supplements.omega3 -> topic:cognition: 2
- topic:food.protein_intake -> topic:supplements.protein_powders: 2
- frame:naturalness_appeal -> frame:commercialization: 2
- topic:alcohol.drinking_culture -> topic:alcohol: 2
- topic:infectious.respiratory_common -> topic:infectious.influenza_avian: 1
- topic:diets.raw_food_juicing -> topic:cancer_alt.natural_remedies: 1
- topic:diets.plant_based -> topic:diets.ancestral_paleo: 1
- evidence:preclinical_extrapolation -> evidence:mechanistic_explanation: 1
- topic:womens.menopause -> topic:longevity.nad_sirtuins: 1
- topic:endocrine.other_hormones -> topic:cardiovascular.heart_disease: 1

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
| claim:claim_type | 643.0 | 0.827 | 0.807 | - | 0.803 |
| claim:discourse_role | 643.0 | 0.974 | 0.965 | - | 0.804 |
| claim:expressed_certainty | 643.0 | 0.902 | 0.896 | 0.799 | 0.838 |
| claim:relevance | 643.0 | 0.950 | 0.946 | - | 0.821 |
| detection:discourse_role | 1352.0 | 0.965 | 0.964 | - | 0.738 |
| detection:relevance | 1352.0 | 0.899 | 0.900 | - | 0.781 |
| product:mention_role | 99.0 | 0.950 | 0.946 | - | 0.913 |
| product:product_name | 99.0 | 0.950 | 0.950 | - | 0.855 |
| product:product_type | 99.0 | 0.939 | 0.939 | - | 0.971 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.275 atoms per window, share with any output 0.150
- Contrast pairs: targeted pass rate 0.636 over 15 pairs; decoy pass rate 1.000; collateral change 0.564 vs no-op 0.333; 1 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 0.994, 1.006 requests per accepted window, rejected by kind {'empty_output': 1, 'window_id_mismatch': 1}; annotations repaired {'certainty_marker_dropped': 1, 'span_widened_for_certainty_marker': 1, 'span_widened_for_quote': 249}, dropped {'invalid_field': 4, 'non_verbatim_quote': 49, 'span_out_of_window': 78}
- Cost: 13720 output tokens per accepted window, - USD per accepted window, 1873.300 s per request
- Calibration: confidence AUROC 0.619 (TP mean 0.846, FP mean 0.808)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.829 | 0.716 | 0.769 | 0.923 | 0.982 |
| contrast | 15.0 | 0.777 | 0.563 | 0.736 | 0.945 | 0.943 |
| discourse | 20.0 | 0.767 | 0.594 | 0.810 | 0.904 | 0.750 |
| health_dense | 40.0 | 0.776 | 0.644 | 0.808 | 0.924 | 0.920 |
| mixed | 40.0 | 0.796 | 0.650 | 0.718 | 0.875 | 0.921 |
| narrative | 60.0 | 0.718 | 0.554 | 0.748 | 0.936 | 0.923 |
| null | 40.0 | 0.742 | 0.529 | 0.500 | 1.000 | - |
| rare_label | 70.0 | 0.772 | 0.636 | 0.809 | 0.946 | 0.896 |
| synthetic | 15.0 | 0.686 | 0.528 | 0.600 | 0.981 | 0.857 |

## Error classes (headline strata, first repeat)

- miss:detection:topic:same_axis_wrong_label: 155.0
- miss:claim:nothing_predicted: 90.0
- miss:detection:topic:span_only: 60.0
- false_positive:detection:topic:same_axis_wrong_label: 57.0
- miss:claim:different_claim: 54.0
- miss:detection:evidence:cross_axis: 49.0
- false_positive:claim:spurious: 28.0
- false_positive:claim:different_claim: 24.0
- miss:detection:evidence:same_axis_wrong_label: 21.0
- false_positive:detection:topic:span_only: 20.0
- miss:detection:frame:same_axis_wrong_label: 18.0
- miss:detection:topic:nothing_predicted: 17.0
- miss:detection:frame:cross_axis: 16.0
- miss:detection:narrative:cross_axis: 16.0
- false_positive:detection:frame:cross_axis: 13.0
- miss:detection:topic:cross_axis: 10.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.721 | 0.764 | 0.765 | 0.701 | 0.787 | 0.778 | 0.912 |
| ds-r1 | 0.716 | 0.781 | 0.748 | 0.709 | 0.791 | 0.780 | 0.888 |
| ds-r2 | 0.726 | 0.777 | 0.744 | 0.699 | 0.790 | 0.773 | 0.904 |
| ref ds-r0|ds-r1 | 0.737 | 0.790 | 0.767 | 0.735 | 0.805 | 0.808 | 0.911 |
| ref ds-r0|ds-r2 | 0.747 | 0.796 | 0.779 | 0.732 | 0.809 | 0.791 | 0.912 |
| ref ds-r1|ds-r2 | 0.743 | 0.796 | 0.766 | 0.739 | 0.788 | 0.796 | 0.918 |
