# Benchmark scorecard: v7-qwen397-b24k

Model `Qwen/Qwen3.5-397B-A17B-GPTQ-Int4` | api `chat_completions` | effort `high` | prompt `granular-v7:0406a404e1c06f54` | repeats 1 | items scored 320

## Headline against the gold (corpus strata, mean over repeats)

Gold = atoms at least two annotators agreed on; singletons are unscored.

| metric | dev | test |
| --- | --- | --- |
| Topic F1 (strict) | 0.606 | 0.581 |
| Topic F1 (soft) | 0.584 | 0.562 |
| Topic F1 (adjacent credit) | 0.610 | 0.592 |
| Topic recall (required) | 0.515 | 0.508 |
| Topic precision | 0.736 | 0.677 |
| Narrative F1 (soft) | 0.549 | 0.290 |
| Narrative F1 (strict) | 0.559 | 0.303 |
| Frame F1 (soft) | 0.529 | 0.512 |
| Evidence F1 (soft) | 0.457 | 0.353 |
| Population F1 (soft) | 0.591 | 0.496 |
| Claim recall (required) | 0.592 | 0.671 |
| Claim precision | 0.671 | 0.716 |
| Product F1 (soft) | 0.772 | 0.763 |
| Topic yield ratio | 0.527 | 0.572 |
| Claim yield ratio | 0.706 | 0.747 |

## Topic F1 by level of the topic tree

The same references re-clustered at each level: a subtopic error under the right parent counts at the parent level. Read each level against its own leave-one-out ceiling (mean over reference annotators).

| level | dev P / R / F1 | test F1 | candidate vs references | leave-one-out F1 (mean) |
| --- | --- | --- | --- | --- |
| subtopic | 0.736 / 0.515 / 0.606 | 0.581 | 0.561 | 0.827 |
| parent | 0.731 / 0.531 / 0.615 | 0.642 | 0.610 | 0.844 |
| domain | 0.762 / 0.571 / 0.653 | 0.639 | 0.634 | 0.845 |

## Ceiling and noise floor (pairwise F1, like for like)

Candidate vs each reference annotator, the annotators vs each other, and the candidate vs its own repeat, all with the same one-to-one atom matching. A candidate inside the reference range is at ceiling on that axis.

| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |
| --- | --- | --- | --- |
| detection:topic | 0.561 | 0.742 (0.737 to 0.747) | - |
| detection:narrative | 0.513 | 0.794 (0.790 to 0.796) | - |
| detection:frame | 0.493 | 0.771 (0.766 to 0.779) | - |
| detection:evidence | 0.454 | 0.735 (0.732 to 0.739) | - |
| detection:population | 0.609 | 0.801 (0.788 to 0.809) | - |
| claim | 0.612 | 0.798 (0.791 to 0.808) | - |
| product | 0.763 | 0.914 (0.911 to 0.918) | - |

## Reference annotators scored against the others' gold (leave one out)

Each reference annotator scored as a candidate against gold rebuilt without it, on the headline strata with the same scoring. This is what a labeler of reference quality scores on this scorecard; a candidate at these numbers is at ceiling.

| annotator | items | topic P / R / F1 | topic F1 adjacent | narrative F1 | population F1 | frame F1 | evidence F1 | claim P / R / F1 | product F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 160 | 0.803 / 0.843 / 0.822 | 0.834 | 0.879 | 0.846 | 0.895 | 0.806 | 0.851 / 0.893 / 0.872 | 0.968 |
| ds-r1 | 160 | 0.768 / 0.880 / 0.820 | 0.830 | 0.879 | 0.818 | 0.845 | 0.818 | 0.877 / 0.909 / 0.893 | 0.938 |
| ds-r2 | 160 | 0.839 / 0.839 / 0.839 | 0.845 | 0.861 | 0.849 | 0.906 | 0.812 | 0.843 / 0.874 / 0.858 | 0.942 |

## Top label confusions (same-axis false positives, predicted -> nearest gold label)

Pairs marked * are ones the reference annotators confuse among themselves (the adjacency table); they earn adjacent credit.

- frame:optimization -> frame:commercialization: 7
- evidence:specific_study -> evidence:vague_research: 4 *
- evidence:prestige_institution -> evidence:specific_study: 3 *
- topic:food -> topic:digital_health.online_health_information: 3
- frame:medical_freedom -> frame:commercialization: 2
- population:older_adults -> population:women: 2
- evidence:strength_assertion -> evidence:vague_research: 2 *
- frame:insinuating_questions -> frame:fear_alarm: 2
- frame:conflict_of_interest -> frame:big_pharma: 2
- topic:health_system.dtc_telehealth -> topic:alt_medicine.functional_medicine: 2
- topic:food.protein_intake -> topic:supplements.protein_powders: 2
- topic:weight.weight_loss_methods -> topic:glp1.use_results: 2

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
| claim:claim_type | 501.0 | 0.741 | 0.725 | - | 0.803 |
| claim:discourse_role | 501.0 | 0.956 | 0.946 | - | 0.804 |
| claim:expressed_certainty | 501.0 | 0.752 | 0.752 | 0.520 | 0.838 |
| claim:relevance | 501.0 | 0.930 | 0.933 | - | 0.821 |
| detection:discourse_role | 893.0 | 0.950 | 0.943 | - | 0.738 |
| detection:relevance | 893.0 | 0.846 | 0.855 | - | 0.781 |
| product:mention_role | 92.0 | 0.859 | 0.861 | - | 0.913 |
| product:product_name | 92.0 | 0.902 | 0.902 | - | 0.855 |
| product:product_type | 92.0 | 0.978 | 0.971 | - | 0.971 |

## Null windows, contrast, validity, cost

- Null windows: 40.0 scored, 0.075 atoms per window, share with any output 0.050
- Contrast pairs: targeted pass rate 0.750 over 15 pairs; decoy pass rate 0.500; collateral change 0.891 vs no-op 0.533; 1 pairs excluded (target not in gold)
- Validity: first-attempt acceptance 0.997, 1.003 requests per accepted window, rejected by kind {'output_truncated': 1}; annotations repaired {'certainty_set_unhedged': 51, 'span_widened_for_certainty_marker': 14, 'span_widened_for_quote': 490}, dropped {'certainty_markers_mismatch': 155, 'duplicate_annotation': 1, 'mixed_or_unknown_labels': 37, 'non_verbatim_quote': 375, 'reversed_span': 5, 'span_out_of_window': 39}
- Cost: 5749 output tokens per accepted window, - USD per accepted window, 1256.700 s per request
- Calibration: confidence AUROC 0.610 (TP mean 0.872, FP mean 0.844)

## Per stratum (topic soft F1 / claim required recall / yield)

| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |
| --- | --- | --- | --- | --- | --- | --- |
| ad_read | 20.0 | 0.592 | 0.664 | 0.705 | 0.550 | 0.818 |
| contrast | 15.0 | 0.571 | 0.557 | 0.443 | 0.713 | 0.755 |
| discourse | 20.0 | 0.535 | 0.536 | 0.598 | 0.667 | 0.409 |
| health_dense | 40.0 | 0.592 | 0.497 | 0.603 | 0.792 | 0.771 |
| mixed | 40.0 | 0.562 | 0.808 | 0.718 | 0.424 | 0.826 |
| narrative | 60.0 | 0.595 | 0.575 | 0.619 | 0.750 | 0.817 |
| null | 40.0 | 0.308 | 0.118 | 0.500 | 1.000 | - |
| rare_label | 70.0 | 0.563 | 0.536 | 0.601 | 0.729 | 0.781 |
| synthetic | 15.0 | 0.709 | 0.602 | 0.671 | 0.770 | 0.667 |

## Error classes (headline strata, first repeat)

- miss:detection:topic:same_axis_wrong_label: 305.0
- miss:claim:nothing_predicted: 177.0
- false_positive:detection:topic:same_axis_wrong_label: 163.0
- false_positive:claim:spurious: 150.0
- miss:detection:evidence:cross_axis: 105.0
- miss:claim:different_claim: 96.0
- miss:detection:topic:nothing_predicted: 62.0
- miss:detection:topic:span_only: 59.0
- false_positive:claim:different_claim: 52.0
- miss:detection:frame:cross_axis: 52.0
- false_positive:detection:frame:same_axis_wrong_label: 50.0
- miss:detection:evidence:same_axis_wrong_label: 41.0
- false_positive:detection:evidence:cross_axis: 41.0
- false_positive:detection:frame:cross_axis: 41.0
- miss:detection:topic:cross_axis: 34.0
- miss:detection:frame:same_axis_wrong_label: 31.0

## Candidate as a fourth annotator (pairwise F1 with each reference)

| annotator | topic | narrative | frame | evidence | population | claim | product |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ds-r0 | 0.559 | 0.507 | 0.490 | 0.458 | 0.609 | 0.611 | 0.774 |
| ds-r1 | 0.557 | 0.522 | 0.500 | 0.453 | 0.619 | 0.609 | 0.768 |
| ds-r2 | 0.565 | 0.509 | 0.490 | 0.451 | 0.599 | 0.616 | 0.748 |
| ref ds-r0|ds-r1 | 0.737 | 0.790 | 0.767 | 0.735 | 0.805 | 0.808 | 0.911 |
| ref ds-r0|ds-r2 | 0.747 | 0.796 | 0.779 | 0.732 | 0.809 | 0.791 | 0.912 |
| ref ds-r1|ds-r2 | 0.743 | 0.796 | 0.766 | 0.739 | 0.788 | 0.796 | 0.918 |
