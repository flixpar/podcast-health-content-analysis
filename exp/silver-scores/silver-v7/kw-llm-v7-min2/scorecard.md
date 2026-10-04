# Benchmark scorecard: kw-llm-v7-min2

Model `keywords` | api `None` | effort `None` | prompt `None` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.288 | 0.301 |
| Topic F1 (soft) | 0.282 | 0.298 |
| Topic F1 (adjacent credit) | 0.299 | 0.335 |
| Topic recall (required) | 0.257 | 0.292 |
| Topic precision | 0.329 | 0.310 |
| Narrative F1 (soft) | 0.241 | 0.176 |
| Narrative F1 (strict) | 0.247 | 0.200 |
| Frame F1 (soft) | 0.118 | 0.237 |
| Evidence F1 (soft) | 0.085 | 0.084 |
| Population F1 (soft) | 0.352 | 0.156 |
| Claim recall (required) | 0.000 | 0.000 |
| Claim precision | - | - |
| Product F1 (soft) | 0.000 | 0.000 |
| Topic yield ratio | 0.573 | 0.691 |
| Claim yield ratio | 0.000 | 0.000 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.329 / 0.257 / 0.288 | 0.301 | 0.289 | 0.827 |
| parent | 0.405 / 0.344 / 0.372 | 0.404 | 0.390 | 0.844 |
| domain | 0.434 / 0.407 / 0.420 | 0.415 | 0.424 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.289 | 0.742 (0.737 to 0.747) | - |
| detection:narrative | 0.218 | 0.794 (0.790 to 0.796) | - |
| detection:frame | 0.152 | 0.771 (0.766 to 0.779) | - |
| detection:evidence | 0.095 | 0.735 (0.732 to 0.739) | - |
| detection:population | 0.409 | 0.801 (0.788 to 0.809) | - |
| claim | 0.000 | 0.798 (0.791 to 0.808) | - |
| product | 0.000 | 0.914 (0.911 to 0.918) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.803 / 0.843 / 0.822 | 0.834 | 0.879 | 0.846 | 0.895 | 0.806 | 0.851 / 0.893 / 0.872 | 0.968 |
| ds-r1 | 160 | 0.768 / 0.880 / 0.820 | 0.830 | 0.879 | 0.818 | 0.845 | 0.818 | 0.877 / 0.909 / 0.893 | 0.938 |
| ds-r2 | 160 | 0.839 / 0.839 / 0.839 | 0.845 | 0.861 | 0.849 | 0.906 | 0.812 | 0.843 / 0.874 / 0.858 | 0.942 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- topic:sleep -> topic:sleep.sleep_duration_quality: 10
- topic:endocrine -> topic:endocrine.thyroid: 7
- topic:alcohol -> topic:alcohol.health_effects: 7
- topic:endocrine -> topic:endocrine.other_hormones: 5
- topic:metabolic -> topic:metabolic.insulin_glucose: 5 *
- topic:supplements -> topic:supplements.other_compounds: 4
- topic:other -> topic:alt_medicine.functional_medicine: 4
- topic:stress -> topic:endocrine.cortisol_adrenal: 4
- population:women -> population:lgbtq: 4
- topic:skin_beauty -> topic:skin_beauty.hair_loss_hair: 3
- topic:cognition.neurochemistry_talk -> topic:endocrine.other_hormones: 3
- topic:food -> topic:food.fats_oils: 3

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
| detection:discourse_role | 412.0 | 0.959 | 0.955 | - | 0.738 |
| detection:relevance | 412.0 | 0.731 | 0.725 | - | 0.781 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 1.525 atoms per window, share with any output 0.600
- Contrast pairs: targeted pass rate - over 15 pairs; decoy pass rate 0.500; collateral change 0.000 vs no-op 0.000; 1 pairs excluded (target not in gold)
- Validity: first-attempt acceptance -, - requests per accepted window, rejected by kind {}
- Cost: None output tokens per accepted window, - USD per accepted window, - s per request
- Calibration: confidence AUROC 0.532 (TP mean 0.779, FP mean 0.765)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.282 | 1.060 | 0.000 | - | 0.000 |
| contrast | 15.0 | 0.332 | 0.770 | 0.000 | - | 0.000 |
| discourse | 20.0 | 0.227 | 0.565 | 0.000 | - | 0.000 |
| health_dense | 40.0 | 0.334 | 0.602 | 0.000 | - | 0.000 |
| mixed | 40.0 | 0.083 | 0.200 | 0.000 | - | 0.000 |
| narrative | 60.0 | 0.296 | 0.609 | 0.000 | - | 0.000 |
| null | 40.0 | 0.000 | 1.176 | 0.000 | - | - |
| rare_label | 70.0 | 0.280 | 0.558 | 0.000 | - | 0.000 |
| synthetic | 15.0 | 0.267 | 0.472 | 0.000 | - | 0.000 |

## Error classes (headline strata, first repeat)

- miss:claim:nothing_predicted: 716.0
- false_positive:detection:topic:same_axis_wrong_label: 433.0
- miss:detection:topic:same_axis_wrong_label: 421.0
- miss:detection:topic:nothing_predicted: 211.0
- miss:detection:evidence:cross_axis: 132.0
- miss:detection:frame:cross_axis: 123.0
- miss:product:nothing_predicted: 103.0
- miss:detection:evidence:nothing_predicted: 93.0
- miss:detection:frame:nothing_predicted: 71.0
- false_positive:detection:topic:span_only: 50.0
- false_positive:detection:topic:spurious: 43.0
- miss:detection:narrative:cross_axis: 37.0
- false_positive:detection:frame:spurious: 32.0
- miss:detection:topic:cross_axis: 31.0
- false_positive:detection:population:spurious: 30.0
- miss:detection:topic:span_only: 28.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.290 | 0.215 | 0.156 | 0.086 | 0.420 | 0.000 | 0.000 |
| ds-r1 | 0.286 | 0.221 | 0.150 | 0.105 | 0.392 | 0.000 | 0.000 |
| ds-r2 | 0.291 | 0.220 | 0.150 | 0.095 | 0.414 | 0.000 | 0.000 |
| ref ds-r0|ds-r1 | 0.737 | 0.790 | 0.767 | 0.735 | 0.805 | 0.808 | 0.911 |
| ref ds-r0|ds-r2 | 0.747 | 0.796 | 0.779 | 0.732 | 0.809 | 0.791 | 0.912 |
| ref ds-r1|ds-r2 | 0.743 | 0.796 | 0.766 | 0.739 | 0.788 | 0.796 | 0.918 |
