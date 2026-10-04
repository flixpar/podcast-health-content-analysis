# Benchmark scorecard: kw-concepts-v7

Model `keywords` | api `None` | effort `None` | prompt `None` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.297 | 0.317 |
| Topic F1 (soft) | 0.290 | 0.308 |
| Topic F1 (adjacent credit) | 0.302 | 0.320 |
| Topic recall (required) | 0.297 | 0.334 |
| Topic precision | 0.297 | 0.302 |
| Narrative F1 (soft) | 0.172 | 0.000 |
| Narrative F1 (strict) | 0.167 | 0.000 |
| Frame F1 (soft) | 0.180 | 0.250 |
| Evidence F1 (soft) | 0.123 | 0.163 |
| Population F1 (soft) | 0.211 | 0.076 |
| Claim recall (required) | 0.000 | 0.000 |
| Claim precision | - | - |
| Product F1 (soft) | 0.000 | 0.000 |
| Topic yield ratio | 0.730 | 0.785 |
| Claim yield ratio | 0.000 | 0.000 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.297 / 0.297 / 0.297 | 0.317 | 0.295 | 0.827 |
| parent | 0.306 / 0.340 / 0.323 | 0.338 | 0.329 | 0.844 |
| domain | 0.317 / 0.388 / 0.349 | 0.358 | 0.369 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.295 | 0.742 (0.737 to 0.747) | - |
| detection:narrative | 0.120 | 0.794 (0.790 to 0.796) | - |
| detection:frame | 0.171 | 0.771 (0.766 to 0.779) | - |
| detection:evidence | 0.109 | 0.735 (0.732 to 0.739) | - |
| detection:population | 0.268 | 0.801 (0.788 to 0.809) | - |
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

- topic:health_system.regulators -> topic:alcohol.health_effects: 8
- topic:health_system.regulators -> topic:mental.wellbeing_grief_loneliness: 8
- topic:mental.wellbeing_grief_loneliness -> topic:longevity.cellular_ageing: 5
- topic:health_system.regulators -> topic:endocrine.other_hormones: 5
- frame:naturalness_appeal -> frame:commercialization: 5
- topic:health_system.regulators -> topic:mental.therapy: 5
- topic:wellness.habits_behavior_change -> topic:mental.wellbeing_grief_loneliness: 4
- topic:health_system.regulators -> topic:drugs_addiction.addiction_recovery: 4
- topic:health_system.regulators -> topic:covid.pandemic_institutions: 3
- topic:health_system.regulators -> topic:skin_beauty.hair_loss_hair: 3
- frame:conspiracy_cover_up -> frame:commercialization: 3
- topic:health_system.regulators -> topic:acute_care.violence_abuse: 3

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
| detection:discourse_role | 452.0 | 0.962 | 0.957 | - | 0.738 |
| detection:relevance | 452.0 | 0.327 | 0.334 | - | 0.781 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 4.775 atoms per window, share with any output 0.925
- Contrast pairs: targeted pass rate - over 15 pairs; decoy pass rate 0.500; collateral change 0.000 vs no-op 0.000; 1 pairs excluded (target not in gold)
- Validity: first-attempt acceptance -, - requests per accepted window, rejected by kind {}
- Cost: None output tokens per accepted window, - USD per accepted window, - s per request
- Calibration: confidence AUROC 0.549 (TP mean 0.606, FP mean 0.584)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.288 | 1.149 | 0.000 | - | 0.000 |
| contrast | 15.0 | 0.318 | 0.724 | 0.000 | - | 0.000 |
| discourse | 20.0 | 0.271 | 0.653 | 0.000 | - | 0.000 |
| health_dense | 40.0 | 0.363 | 0.550 | 0.000 | - | 0.000 |
| mixed | 40.0 | 0.174 | 1.125 | 0.000 | - | 0.000 |
| narrative | 60.0 | 0.306 | 0.622 | 0.000 | - | 0.000 |
| null | 40.0 | 0.016 | 6.588 | 0.000 | - | - |
| rare_label | 70.0 | 0.283 | 0.654 | 0.000 | - | 0.000 |
| synthetic | 15.0 | 0.297 | 0.463 | 0.000 | - | 0.000 |

## Error classes (headline strata, first repeat)

- miss:claim:nothing_predicted: 716.0
- miss:detection:topic:same_axis_wrong_label: 414.0
- false_positive:detection:topic:same_axis_wrong_label: 333.0
- false_positive:detection:topic:spurious: 241.0
- miss:detection:topic:nothing_predicted: 176.0
- miss:detection:evidence:cross_axis: 134.0
- miss:detection:frame:cross_axis: 116.0
- false_positive:detection:population:spurious: 114.0
- false_positive:detection:topic:span_only: 104.0
- miss:product:nothing_predicted: 103.0
- miss:detection:evidence:nothing_predicted: 90.0
- miss:detection:frame:nothing_predicted: 60.0
- miss:detection:narrative:cross_axis: 53.0
- miss:detection:topic:cross_axis: 33.0
- miss:detection:population:cross_axis: 32.0
- miss:detection:topic:span_only: 29.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.290 | 0.107 | 0.169 | 0.112 | 0.272 | 0.000 | 0.000 |
| ds-r1 | 0.297 | 0.130 | 0.172 | 0.108 | 0.267 | 0.000 | 0.000 |
| ds-r2 | 0.298 | 0.124 | 0.171 | 0.107 | 0.266 | 0.000 | 0.000 |
| ref ds-r0|ds-r1 | 0.737 | 0.790 | 0.767 | 0.735 | 0.805 | 0.808 | 0.911 |
| ref ds-r0|ds-r2 | 0.747 | 0.796 | 0.779 | 0.732 | 0.809 | 0.791 | 0.912 |
| ref ds-r1|ds-r2 | 0.743 | 0.796 | 0.766 | 0.739 | 0.788 | 0.796 | 0.918 |
