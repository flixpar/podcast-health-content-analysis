# Decisions H: report 10 (fitness, recovery, peds, longevity, biohacking, self_tracking, digital_health)

Patch: `patch-H.jsonl` (21 change, 1 add, 1 remove, 1 parent). Written against
`merged-partial.md`; applies cleanly (`check-H.md`) and compiles. Every
backticked reference in the new rows resolves.

## Proposals

ACCEPT  topic:fitness.strength_training  bodybuilding/bulking 4,889 eps / 226 pods and grip strength 496 / 80 had no listed home; "women lifting" (30 eps) dropped for real phrasing.
ACCEPT  topic:fitness.daily_movement  weighted vest (198 eps / 63 pods) added, plus "steps a day" and "sedentary".
MODIFY  topic:fitness.sports_performance  "training camp" removed (calendar sense in every sports-show sample); weight cutting (520 eps / 56 pods), overtraining and TB12/pliability (293 / 59) named; career-extending regimens included to receive career longevity. The roster/usage/workload exclusion sentence left out of the row: it is a scope rule and is already in codebook 3.2 ("Sports and exercise beyond injuries"). "Recover" left out so training recovery goes to the new subtopic; injury boundary to `musculoskeletal.sports_injuries` added. Unattested examples ("fight camp", "altitude training") not used.
MODIFY  topic:fitness.exercise_general  removed "exercise for longevity" so the outcome is co-labeled under rule 1; "physical activity" (1,675 eps / 194 pods) added. Did not add the proposed "exercise for depression" example, which recreates the same single-label trap.
ACCEPT  topic:fitness.cardio_endurance  no change proposed (VO2 max co-labeling handled in ageing_science and codebook).
ACCEPT  topic:fitness.mobility_flexibility  no change proposed; incidental yoga/Pilates is a codebook scope rule.
ACCEPT  topic:fitness (grip strength as a metric)  folded into strength_training examples.
MODIFY  topic:recovery.heat_sauna  "hot tub" (2,466 eps, mostly a social setting) dropped from examples; the "social setting is not health content" sentence kept out of the row (scope rule, covered by the exercise-as-setting rule in 3.2). Proposed "hot and cold contrast" written as "contrast therapy".
ACCEPT  topic:recovery.training_recovery (ADD)  1,092 eps / 110 pods (recovery terms) and 1,567 / 148 (soreness, DOMS, deload, rest days), very frequent as an ad outcome (502516/15, 176979/5, 24298/3), and no existing home. Distinct from modalities and from sports_performance.
ACCEPT  topic:recovery (parent definition)  extended with "and recovery from training itself" to match the new subtopic.
ACCEPT  topic:recovery.cold_exposure / red_light / hyperbaric / bodywork_compression  no change proposed.
MODIFY  topic:peds.steroids_sarms  corticosteroids (293 eps) routed to `medications.other_drugs` (which already lists "steroids (medical)") or the condition; PED claims about a public figure stated (205572/2). "X on steroids" idiom sentence dropped from the row: already in codebook 3.4. Examples use attested anabolic phrasing (anabolic steroids, on a cycle, juicing, roid rage, trenbolone) instead of bare "steroids"/"tren".
MODIFY  topic:peds.doping_sport  "drug test" noise (workplace 119 eps) routed to `drugs_addiction.drug_policy`, which already claims workplace testing and points sport testing here; added the rule for when to add `peds.steroids_sarms` so the accusation overlap between the two peds rows is resolved. "EPO in cycling" not added (EPO stays in steroids_sarms to avoid a two-home example).
ACCEPT  topic:peds.fat_loss_drugs_ped (MERGE into weight.diet_pills_fat_burners)  genuine hits under 100 eps after removing "DNP = did not play" and cold-medicine/history senses; the weight row already covers "any pill... taken for weight loss", so the two labels duplicated coverage. Executed as remove + change of the target row.
MODIFY  topic:weight.diet_pills_fat_burners  merge target; built on the merged-partial row (patch-C's GLP-1 sentence and Contrave/metabolism-booster examples kept), adding physique fat-loss drugs with the anabolic-cycle rule and clenbuterol, DNP, T3 for cutting.
MODIFY  topic:longevity.ageing_science  purpose-word boundary ("good for longevity") and career-longevity pointer added; the tagline/sign-off case dropped from the row as it is already in codebook 3.4. Example "VO2 max as a predictor of lifespan" (175189/2).
ACCEPT  topic:longevity.longevity_drugs  senolytic supplements (52 of 157 senolytic eps are a supplement ad) covered; name "Longevity drugs & senolytics". The "under rule 8" wording replaced by a plain pointer to the ingredients' `supplements` subtopic.
ACCEPT  topic:longevity.biological_age  TruAge removed (not findable), epigenetic-age phrasing added, skin-care age-reversal routed to `skin_beauty.skin_ageing` (194917/4).
MODIFY  topic:longevity.protocols_clinics  ASR spelling added to examples (Brian Johnson 509 eps vs 7); "Don't Die" qualified in the example rather than with a word-sense sentence (that sense note is already in codebook section 2).
ACCEPT  topic:longevity.nad_sirtuins / cellular_ageing  no change proposed.
MODIFY  topic:biohacking.practice_culture  "optimal not normal" (378 eps, lab-range talk) removed; tip-called-a-biohack rule and hormesis (524 eps / 50 pods) added. Optimal lab ranges pointed to `procedures.lab_testing` only (one destination; `self_tracking.consumer_lab_tests` applies anyway when the panel is consumer-bought).
ACCEPT  topic:biohacking.devices_gadgets  "other than wearables" fixed to exclude only measuring devices, so ear-worn vagus stimulators (NeuroPod, ~490 ad eps) fit, matching `stress.nervous_system_regulation`, which already sends them here; "light glasses" removed, pointing to the sleep/light rows as `radiation_light.artificial_light` already does.
MODIFY  topic:biohacking.stacks_protocols  "morning routine" (3,041 eps, mostly self-help and ad copy) narrowed to routines with body practices; daily supplement routine included to match co-labeling rule 6; the ad sentence kept out (codebook 3.3/4.1 already has "add it to your morning routine").
MODIFY  topic:self_tracking.wearables  ASR "Aura ring" added (94 vs 712 eps), "Apple Watch health features" specified; the payment-accessory sentence kept out of the row (already in codebook 3.3).
ACCEPT  topic:self_tracking.consumer_lab_tests  DUTCH test and LabCorp OnDemand added; disclaimer handling is codebook (already present).
ACCEPT  topic:self_tracking.glucose_monitors  no change proposed.
ACCEPT  topic:self_tracking.body_scans  DEXA (530 eps, body fat or bone density) removed and routed to `weight.body_composition` / `musculoskeletal.bone_health`.
MODIFY  topic:digital_health.ai_advice  widened to companionship, consumer AI health services (Amazon Health AI) and chatbot-linked mental-health harms (141 narrow segments; 359 eps / 92 pods broad); kept the existing "take both only when both uses are described" clause. The aromatase-inhibitor collision dropped from the row (word-sense note, already in codebook section 2).
ACCEPT  topic:digital_health.ai_in_medicine  keep, no change.
ACCEPT  topic:digital_health.online_health_information  "search engines" and Dr. Google/WebMD (353 eps / 115 pods) and fitness influencers (465 / 96) added; existing examples kept.
ACCEPT  topic:digital_health.health_apps  "digital therapeutics" (9 eps) dropped from name and examples (ID unchanged); named app examples added.
ACCEPT  topic:health_system.dtc_telehealth  no change proposed.
REJECT  topic:gender.trans_athletes (ADD)  already added by the gender reviewer (present in merged-partial with a physiology-focused definition matching this proposal); no duplicate op.
REJECT  float tanks, hormesis, stem cells as separate subtopics  report itself proposes none (float tanks too concentrated: JRE 243 of 335 eps); hormesis went into practice_culture.

## Codebook

Most of report 10's notes are already in the working-copy codebook (`taxonomy/codebook-v8.md`); I checked each.

1. Report 10 note 1 (sports talk is health content only when it describes a body; training camp, pitch count, workload, "out of shape" excluded). Sound; already in 3.2 "Sports and exercise beyond injuries" with the same examples. Still worth the rubric example "he'll get a full workload after training camp" → empty output, if not yet added.
2. Note 2 (exercise named only as setting: gym, yoga pants, "how's that working out"). Sound (25k/48k/9k episodes); already in 3.2 and 3.4. Extend the example list with a hot tub as a social setting (2,466 eps, 95931/2), since that sentence was taken out of `heat_sauna`.
3. Note 3 ("X on steroids" 2,311 eps / 200 pods; "health and longevity" sign-off). Sound; both already in 3.4.
4. Note 4 (DNP, AI = aromatase inhibitor, Tren, Whoop, Brian Johnson, Aura ring). Sound; already in section 2. "Don't die" (1,808 eps, almost all ordinary) also present.
5. Note 5 (boilerplate disclaimers: Hyman/Function Health ~355 eps, Hers AI disclaimer ~886 eps, Apple Pay on Apple Watch). Sound; already in 3.3/4.1.
6. Note 6 (ad outcomes "post-workout recovery", "recovery and stamina" take `recovery.training_recovery`; "add it to your morning routine" is not an outcome). Sound; the second half is in 4.1. The first half should now name `recovery.training_recovery` explicitly (502516/15, 176979/5, 24298/3) once this patch lands.
7. Note 7 (longevity as a purpose word does not add `longevity.ageing_science`; VO2 max as a lifespan predictor does). Sound; worth a rule-1 worked example (174862/0, 175189/2). Partly encoded in the new ageing_science row.
8. Note 8 (senolytic supplement → substance subtopic + `longevity.longevity_drugs`; NAD ad promising energy → `longevity.nad_sirtuins` + `wellness.energy_fatigue`). Sound; fits rule 8's "code both" clause.
9. Note 9 (longevity clinic bundles: modalities + `longevity.protocols_clinics` only when the bundle is the product). Sound; appears already present near line 488.
10. Note 10 (`frame:optimization`: functional "optimal ranges" are the lab subtopic, not the frame). Sound and consistent with the frame row ("lab ranges are not it"). Note the frame row's example "optimal not normal" now conflicts with that 378-eps finding; see cross-slice.
11. Note 11 (one player's conditioning or PED accusation takes no `population:athletes`; leaguewide talk does). Sound; add to 5.5 if absent.

## Cross-slice notes

- `topic:weight.diet_pills_fat_burners`: patch-C also changes this row. My op is built on the merged-partial (patch-C) version and only adds the merged fat-loss PED content, so the resolved file should take patch-H's op for this id.
- `topic:peds.fat_loss_drugs_ped` removed: it appears in `benchmark/v2/taxonomy.json` and `benchmark/v3/taxonomy.json` (label lists only; no gold item found using it by grep). Rubric/prompt label lists compiled from the taxonomy will drop it automatically.
- `frame:optimization` examples include "optimal not normal", which the corpus shows is mostly functional lab-range talk (378 eps / 42 pods, Thyroid Fixer 134). The frame owner may want to drop or qualify that example.
- `alt_medicine.functional_medicine` lists "functional lab ranges" as an example; the new practice_culture row sends "optimal ranges" to `procedures.lab_testing`. The two are compatible (approach vs test), but the functional_medicine owner may want a pointer.
- `skin_beauty.skin_ageing` could add "biological age reversal (skin-care claims)" as an example to receive the boundary from `longevity.biological_age` (Lancôme ad, 194917/4).
- `gender.trans_athletes` (gender reviewer) already covers report 10's cross-slice gap; report 10's counts (1,799 eps / 106 pods; 1,081 co-occurring with physiology or injury terms) support it.
