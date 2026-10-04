# Benchmark scorecard: v7-high-nobudget

Model `deepseek-ai/DeepSeek-V4-Flash-0731` | api `chat_completions` | effort `high` | prompt `granular-v7:0406a404e1c06f54` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.828 | 0.841 |
| Topic F1 (soft) | 0.797 | 0.806 |
| Topic F1 (adjacent credit) | 0.833 | 0.844 |
| Topic recall (required) | 0.787 | 0.813 |
| Topic precision | 0.873 | 0.870 |
| Narrative F1 (soft) | 0.853 | 0.767 |
| Narrative F1 (strict) | 0.870 | 0.849 |
| Frame F1 (soft) | 0.881 | 0.801 |
| Evidence F1 (soft) | 0.838 | 0.772 |
| Population F1 (soft) | 0.849 | 0.861 |
| Claim recall (required) | 0.840 | 0.846 |
| Claim precision | 0.913 | 0.879 |
| Product F1 (soft) | 0.961 | 0.885 |
| Topic yield ratio | 0.700 | 0.728 |
| Claim yield ratio | 0.764 | 0.787 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.873 / 0.787 / 0.828 | 0.841 | 0.746 | 0.827 |
| parent | 0.898 / 0.809 / 0.852 | 0.848 | 0.774 | 0.844 |
| domain | 0.901 / 0.818 / 0.857 | 0.851 | 0.780 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.746 | 0.742 (0.737 to 0.747) | - |
| detection:narrative | 0.789 | 0.794 (0.790 to 0.796) | - |
| detection:frame | 0.779 | 0.771 (0.766 to 0.779) | - |
| detection:evidence | 0.754 | 0.735 (0.732 to 0.739) | - |
| detection:population | 0.814 | 0.801 (0.788 to 0.809) | - |
| claim | 0.796 | 0.798 (0.791 to 0.808) | - |
| product | 0.908 | 0.914 (0.911 to 0.918) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.803 / 0.843 / 0.822 | 0.834 | 0.879 | 0.846 | 0.895 | 0.806 | 0.851 / 0.893 / 0.872 | 0.968 |
| ds-r1 | 160 | 0.768 / 0.880 / 0.820 | 0.830 | 0.879 | 0.818 | 0.845 | 0.818 | 0.877 / 0.909 / 0.893 | 0.938 |
| ds-r2 | 160 | 0.839 / 0.839 / 0.839 | 0.845 | 0.861 | 0.849 | 0.906 | 0.812 | 0.843 / 0.874 / 0.858 | 0.942 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- evidence:weak_human_evidence -> evidence:vague_research: 3
- frame:toxin_purity -> frame:naturalness_appeal: 2
- topic:food.micronutrients_food -> topic:cognition: 2
- topic:radiation_light.sunlight_uv -> topic:cancer.skin_cancer: 2
- topic:alcohol.drinking_culture -> topic:alcohol: 2
- topic:health_system.dtc_telehealth -> topic:mental.therapy: 2
- topic:covid.pandemic_institutions -> topic:covid.illness_severity: 1
- topic:covid.lockdowns_closures -> topic:drugs_addiction: 1
- topic:covid.lockdowns_closures -> topic:covid.pandemic_institutions: 1
- topic:diets.plant_based -> topic:cancer_alt.metabolic_dietary: 1
- topic:diets.raw_food_juicing -> topic:cancer_alt.metabolic_dietary: 1
- topic:diets.plant_based -> topic:diets.ancestral_paleo: 1

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
| claim:claim_type | 688.0 | 0.839 | 0.825 | - | 0.803 |
| claim:discourse_role | 688.0 | 0.974 | 0.970 | - | 0.804 |
| claim:expressed_certainty | 688.0 | 0.908 | 0.905 | 0.804 | 0.838 |
| claim:relevance | 688.0 | 0.968 | 0.957 | - | 0.821 |
| detection:discourse_role | 1482.0 | 0.976 | 0.971 | - | 0.738 |
| detection:relevance | 1482.0 | 0.912 | 0.902 | - | 0.781 |
| product:mention_role | 103.0 | 0.981 | 0.953 | - | 0.913 |
| product:product_name | 103.0 | 0.913 | 0.913 | - | 0.855 |
| product:product_type | 103.0 | 0.952 | 0.945 | - | 0.971 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.475 atoms per window, share with any output 0.200
- Contrast pairs: targeted pass rate 0.700 over 15 pairs; decoy pass rate 1.000; collateral change 0.478 vs no-op 0.318; 1 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 0.994, 1.006 requests per accepted window, rejected by kind {'transport': 2}; annotations repaired {'span_widened_for_certainty_marker': 3, 'span_widened_for_quote': 262}, dropped {'certainty_markers_mismatch': 1, 'invalid_field': 4, 'non_verbatim_quote': 35, 'span_out_of_window': 47}
- Cost: 21800 output tokens per accepted window, - USD per accepted window, 2216.700 s per request
- Calibration: confidence AUROC 0.645 (TP mean 0.834, FP mean 0.790)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.787 | 0.694 | 0.859 | 0.893 | 0.931 |
| contrast | 15.0 | 0.852 | 0.764 | 0.764 | 0.899 | 0.989 |
| discourse | 20.0 | 0.780 | 0.724 | 0.822 | 0.894 | 0.710 |
| health_dense | 40.0 | 0.806 | 0.708 | 0.861 | 0.901 | 0.957 |
| mixed | 40.0 | 0.832 | 0.675 | 0.718 | 0.966 | 0.978 |
| narrative | 60.0 | 0.783 | 0.704 | 0.826 | 0.915 | 0.929 |
| null | 40.0 | 0.640 | 0.941 | 0.500 | 1.000 | - |
| rare_label | 70.0 | 0.806 | 0.700 | 0.844 | 0.917 | 0.941 |
| synthetic | 15.0 | 0.824 | 0.787 | 0.776 | 0.985 | 0.857 |

## Error classes (headline strata, first repeat)

- miss:detection:topic:same_axis_wrong_label: 124.0
- miss:claim:nothing_predicted: 78.0
- false_positive:detection:topic:same_axis_wrong_label: 65.0
- miss:detection:topic:span_only: 49.0
- false_positive:claim:different_claim: 36.0
- miss:claim:different_claim: 35.0
- false_positive:detection:topic:span_only: 30.0
- false_positive:claim:spurious: 30.0
- miss:detection:evidence:same_axis_wrong_label: 17.0
- miss:detection:topic:nothing_predicted: 15.0
- false_positive:detection:evidence:cross_axis: 14.0
- miss:detection:evidence:cross_axis: 14.0
- false_positive:detection:topic:spurious: 11.0
- false_positive:detection:evidence:same_axis_wrong_label: 11.0
- miss:detection:frame:same_axis_wrong_label: 10.0
- miss:detection:frame:cross_axis: 9.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.745 | 0.778 | 0.778 | 0.764 | 0.827 | 0.796 | 0.911 |
| ds-r1 | 0.742 | 0.784 | 0.764 | 0.749 | 0.801 | 0.798 | 0.905 |
| ds-r2 | 0.751 | 0.806 | 0.793 | 0.749 | 0.815 | 0.792 | 0.906 |
| ref ds-r0|ds-r1 | 0.737 | 0.790 | 0.767 | 0.735 | 0.805 | 0.808 | 0.911 |
| ref ds-r0|ds-r2 | 0.747 | 0.796 | 0.779 | 0.732 | 0.809 | 0.791 | 0.912 |
| ref ds-r1|ds-r2 | 0.743 | 0.796 | 0.766 | 0.739 | 0.788 | 0.796 | 0.918 |
