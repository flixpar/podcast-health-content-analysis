# Benchmark scorecard: kw-llm-v7

Model `keywords` | api `None` | effort `None` | prompt `None` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.274 | 0.259 |
| Topic F1 (soft) | 0.273 | 0.259 |
| Topic F1 (adjacent credit) | 0.282 | 0.281 |
| Topic recall (required) | 0.554 | 0.557 |
| Topic precision | 0.182 | 0.169 |
| Narrative F1 (soft) | 0.264 | 0.202 |
| Narrative F1 (strict) | 0.264 | 0.209 |
| Frame F1 (soft) | 0.226 | 0.242 |
| Evidence F1 (soft) | 0.219 | 0.203 |
| Population F1 (soft) | 0.269 | 0.115 |
| Claim recall (required) | 0.000 | 0.000 |
| Claim precision | - | - |
| Product F1 (soft) | 0.000 | 0.000 |
| Topic yield ratio | 2.198 | 2.346 |
| Claim yield ratio | 0.000 | 0.000 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.182 / 0.554 / 0.274 | 0.259 | 0.272 | 0.827 |
| parent | 0.219 / 0.748 / 0.339 | 0.304 | 0.323 | 0.844 |
| domain | 0.212 / 0.802 / 0.336 | 0.296 | 0.321 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.272 | 0.742 (0.737 to 0.747) | - |
| detection:narrative | 0.253 | 0.794 (0.790 to 0.796) | - |
| detection:frame | 0.250 | 0.771 (0.766 to 0.779) | - |
| detection:evidence | 0.234 | 0.735 (0.732 to 0.739) | - |
| detection:population | 0.313 | 0.801 (0.788 to 0.809) | - |
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

- topic:sleep -> topic:sleep.sleep_duration_quality: 21
- topic:endocrine -> topic:endocrine.other_hormones: 17
- topic:cognition.neurochemistry_talk -> topic:endocrine.other_hormones: 16
- topic:endocrine -> topic:endocrine.thyroid: 14
- frame:optimization -> frame:commercialization: 12
- topic:longevity -> topic:longevity.ageing_science: 12 *
- topic:alcohol -> topic:alcohol.health_effects: 12
- topic:skin_beauty -> topic:skin_beauty.acne: 9
- topic:glp1.new_offlabel_uses -> topic:longevity.ageing_science: 8
- topic:glp1.new_offlabel_uses -> topic:immune.inflammation: 8
- topic:immune -> topic:immune.inflammation: 8
- topic:other -> topic:alt_medicine.functional_medicine: 7

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
| detection:discourse_role | 975.0 | 0.950 | 0.947 | - | 0.738 |
| detection:relevance | 975.0 | 0.453 | 0.449 | - | 0.781 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 9.275 atoms per window, share with any output 1.000
- Contrast pairs: targeted pass rate - over 15 pairs; decoy pass rate 0.500; collateral change 0.000 vs no-op 0.000; 1 pairs excluded (target not in gold)
- Validity: first-attempt acceptance -, - requests per accepted window, rejected by kind {}
- Cost: None output tokens per accepted window, - USD per accepted window, - s per request
- Calibration: confidence AUROC 0.612 (TP mean 0.649, FP mean 0.596)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.188 | 3.299 | 0.000 | - | 0.000 |
| contrast | 15.0 | 0.270 | 2.322 | 0.000 | - | 0.000 |
| discourse | 20.0 | 0.273 | 2.096 | 0.000 | - | 0.000 |
| health_dense | 40.0 | 0.308 | 2.001 | 0.000 | - | 0.000 |
| mixed | 40.0 | 0.237 | 2.108 | 0.000 | - | 0.000 |
| narrative | 60.0 | 0.277 | 2.255 | 0.000 | - | 0.000 |
| null | 40.0 | 0.023 | 9.824 | 0.000 | - | - |
| rare_label | 70.0 | 0.280 | 2.224 | 0.000 | - | 0.000 |
| synthetic | 15.0 | 0.284 | 2.231 | 0.000 | - | 0.000 |

## Error classes (headline strata, first repeat)

- false_positive:detection:topic:same_axis_wrong_label: 1842.0
- miss:claim:nothing_predicted: 716.0
- false_positive:detection:topic:spurious: 364.0
- miss:detection:topic:same_axis_wrong_label: 333.0
- false_positive:detection:topic:span_only: 193.0
- false_positive:detection:population:spurious: 160.0
- false_positive:detection:evidence:spurious: 140.0
- false_positive:detection:frame:spurious: 135.0
- miss:detection:evidence:cross_axis: 130.0
- false_positive:detection:evidence:cross_axis: 119.0
- miss:product:nothing_predicted: 103.0
- false_positive:detection:narrative:cross_axis: 100.0
- miss:detection:frame:cross_axis: 96.0
- false_positive:detection:population:cross_axis: 85.0
- false_positive:detection:frame:cross_axis: 57.0
- false_positive:detection:population:span_only: 53.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.272 | 0.245 | 0.252 | 0.236 | 0.308 | 0.000 | 0.000 |
| ds-r1 | 0.275 | 0.257 | 0.250 | 0.234 | 0.317 | 0.000 | 0.000 |
| ds-r2 | 0.269 | 0.258 | 0.247 | 0.233 | 0.314 | 0.000 | 0.000 |
| ref ds-r0|ds-r1 | 0.737 | 0.790 | 0.767 | 0.735 | 0.805 | 0.808 | 0.911 |
| ref ds-r0|ds-r2 | 0.747 | 0.796 | 0.779 | 0.732 | 0.809 | 0.791 | 0.912 |
| ref ds-r1|ds-r2 | 0.743 | 0.796 | 0.766 | 0.739 | 0.788 | 0.796 | 0.918 |
