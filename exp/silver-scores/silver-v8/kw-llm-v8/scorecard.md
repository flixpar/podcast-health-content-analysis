# Benchmark scorecard: kw-llm-v8

Model `keywords` | api `None` | effort `None` | prompt `None` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.264 | 0.278 |
| Topic F1 (soft) | 0.263 | 0.277 |
| Topic F1 (adjacent credit) | 0.269 | 0.285 |
| Topic recall (required) | 0.536 | 0.540 |
| Topic precision | 0.175 | 0.187 |
| Narrative F1 (soft) | 0.282 | 0.316 |
| Narrative F1 (strict) | 0.275 | 0.327 |
| Frame F1 (soft) | 0.303 | 0.277 |
| Evidence F1 (soft) | 0.196 | 0.215 |
| Population F1 (soft) | 0.247 | 0.120 |
| Claim recall (required) | 0.000 | 0.000 |
| Claim precision | - | - |
| Product F1 (soft) | 0.000 | 0.000 |
| Topic yield ratio | 2.301 | 2.182 |
| Claim yield ratio | 0.000 | 0.000 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.175 / 0.536 / 0.264 | 0.278 | 0.273 | 0.832 |
| parent | 0.213 / 0.744 / 0.331 | 0.353 | 0.328 | 0.845 |
| domain | 0.209 / 0.820 / 0.333 | 0.327 | 0.326 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.273 | 0.745 (0.736 to 0.754) | - |
| detection:narrative | 0.308 | 0.799 (0.785 to 0.818) | - |
| detection:frame | 0.299 | 0.784 (0.778 to 0.792) | - |
| detection:evidence | 0.214 | 0.735 (0.721 to 0.742) | - |
| detection:population | 0.278 | 0.809 (0.782 to 0.841) | - |
| claim | 0.000 | 0.785 (0.783 to 0.787) | - |
| product | 0.000 | 0.913 (0.906 to 0.924) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.810 / 0.867 / 0.837 | 0.840 | 0.864 | 0.925 | 0.875 | 0.841 | 0.855 / 0.875 / 0.865 | 0.941 |
| ds-r1 | 160 | 0.846 / 0.848 / 0.847 | 0.851 | 0.826 | 0.789 | 0.895 | 0.800 | 0.868 / 0.835 / 0.851 | 0.946 |
| ds-r2 | 160 | 0.824 / 0.802 / 0.813 | 0.816 | 0.768 | 0.871 | 0.882 | 0.801 | 0.857 / 0.849 / 0.853 | 0.978 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- topic:other -> topic:mental.therapy: 15
- topic:alcohol -> topic:alcohol.health_effects: 15
- topic:sleep -> topic:sleep.sleep_hygiene_environment: 11
- topic:endocrine -> topic:endocrine.thyroid: 11
- topic:cognition.neurochemistry_talk -> topic:endocrine.other_hormones: 9
- topic:skin_beauty -> topic:skin_beauty.acne: 9
- topic:covid -> topic:covid.pandemic_institutions: 8
- topic:immune -> topic:immune.inflammation: 8
- topic:oral -> topic:oral.dental_procedures: 8
- topic:weight.weight_loss_methods -> topic:glp1.access_compounding: 8
- topic:endocrine -> topic:endocrine.cortisol_adrenal: 7
- topic:food -> topic:food.general_nutrition: 7

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
| detection:discourse_role | 857.0 | 0.960 | 0.958 | - | 0.767 |
| detection:relevance | 857.0 | 0.387 | 0.383 | - | 0.779 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 6.875 atoms per window, share with any output 0.975
- Contrast pairs: targeted pass rate - over 15 pairs; decoy pass rate 0.500; collateral change 0.000 vs no-op 0.000; 3 pairs excluded (target not in gold)
- Validity: first-attempt acceptance -, - requests per accepted window, rejected by kind {}
- Cost: None output tokens per accepted window, - USD per accepted window, - s per request
- Calibration: confidence AUROC 0.611 (TP mean 0.648, FP mean 0.593)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.192 | 3.725 | 0.000 | - | 0.000 |
| contrast | 15.0 | 0.320 | 1.983 | 0.000 | - | 0.000 |
| discourse | 20.0 | 0.222 | 2.185 | 0.000 | - | 0.000 |
| health_dense | 40.0 | 0.325 | 1.857 | 0.000 | - | 0.000 |
| mixed | 40.0 | 0.186 | 3.459 | 0.000 | - | 0.000 |
| narrative | 60.0 | 0.291 | 2.072 | 0.000 | - | 0.000 |
| null | 40.0 | 0.014 | 34.500 | 0.000 | - | - |
| rare_label | 70.0 | 0.269 | 2.346 | 0.000 | - | 0.000 |
| synthetic | 15.0 | 0.302 | 2.165 | 0.000 | - | 0.000 |

## Error classes (headline strata, first repeat)

- false_positive:detection:topic:same_axis_wrong_label: 1614.0
- miss:claim:nothing_predicted: 618.0
- false_positive:detection:topic:spurious: 401.0
- miss:detection:topic:same_axis_wrong_label: 354.0
- false_positive:detection:population:spurious: 202.0
- false_positive:detection:topic:span_only: 186.0
- miss:detection:evidence:cross_axis: 122.0
- miss:product:nothing_predicted: 101.0
- false_positive:detection:frame:spurious: 87.0
- miss:detection:frame:cross_axis: 86.0
- false_positive:detection:population:cross_axis: 81.0
- false_positive:detection:evidence:spurious: 72.0
- false_positive:detection:narrative:cross_axis: 64.0
- false_positive:detection:evidence:cross_axis: 60.0
- false_positive:detection:population:span_only: 58.0
- false_positive:detection:frame:cross_axis: 47.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.273 | 0.303 | 0.305 | 0.210 | 0.283 | 0.000 | 0.000 |
| ds-r1 | 0.272 | 0.304 | 0.300 | 0.230 | 0.263 | 0.000 | 0.000 |
| ds-r2 | 0.276 | 0.317 | 0.294 | 0.204 | 0.288 | 0.000 | 0.000 |
| ref ds-r0|ds-r1 | 0.754 | 0.818 | 0.792 | 0.742 | 0.806 | 0.787 | 0.908 |
| ref ds-r0|ds-r2 | 0.743 | 0.785 | 0.781 | 0.741 | 0.841 | 0.783 | 0.906 |
| ref ds-r1|ds-r2 | 0.736 | 0.795 | 0.778 | 0.721 | 0.782 | 0.786 | 0.924 |
