# Decisions F1: report 12-narratives-a.md (vaccines, COVID, cancer, food narratives)

Patch: `patch-F1.jsonl` (27 change, 1 add, 4 remove, 0 parent). Validated with
`apply_patches.py` (output `check-F1.md`) and `tl.compile_taxonomy`; every
backticked reference in the patched rows resolves in `check-F1.md`. Topic
references inside narrative rows use the full `topic:parent.leaf` form.

## Proposals

### Vaccines
ACCEPT  narrative:vaccines_cause_autism  Amish "unvaccinated have no autism" argument recurs (27 eps, 16 pods); kept "vaccine-autism link" example.
MODIFY  narrative:vaccine_ingredients_toxic  Accepted SV40/contaminant scope (44 eps, 15 pods) and fetal-cell moral-objection exclusion; added a boundary sending DNA contamination of mRNA vaccines to `narrative:mrna_alters_dna` (its row already lists the SV40 promoter).
ACCEPT  narrative:hep_b_birth_dose_unneeded  Real phrasing (sex/needle risk) as examples; policy-news boundary to `topic:vaccines.hep_b`; kept "sex-disease vaccine" example.
MODIFY  narrative:vaccines_didnt_end_disease  Added DDT/polio (16 eps, 7 pods). Dropped "polio redefined out of existence": no count or quote in the report.
ACCEPT  narrative:vaccine_injury_hidden  Gaslighting/denial phrasing evidenced (37390/0, 39273/1, 11412/6); VAERS-for-one-harm boundary added.
ACCEPT  narrative:vaccine_makers_no_liability  Commonest conclusion is schedule growth or "why do they need protection" (185815/1, 204866/0, 3732/8); premise rule kept, consistent with codebook 5.2.
MODIFY  narrative:natural_immunity_superior  Accepted equivalence wording (524 eps, 69 pods, mostly "should count"); ID kept, name changed to "as good as or better than vaccination" so it no longer misstates the scope.
ACCEPT  narrative:covid_vaccine_deaths  Added non-vaccine sudden-death boundary, film/SADS/vaccine-arm examples (364 eps of plain "died suddenly", ~3/12 the coinage).
ACCEPT  narrative:covid_vaccine_myocarditis  "Rare but real" boundary (14136/7, 325354/8) routed to `topic:vaccines.safety_injury`; concealment examples added.
MODIFY  narrative:spike_protein_persistent  Accepted "toxic or persists" plus detox (104 segs, 74 eps); added boundary to `narrative:vaccine_shedding`.
MODIFY  narrative:measles_harmless  Widened to other childhood infections (chickenpox parties 45 eps, 24 pods; mumps); ID kept, name widened to match.
MODIFY  narrative:vaccine_microchips_5g  Added magnets and examples; dropped the proposed "code mocking as rebutted" sentence, which is a stance rule already in codebook 5.2 (moved to Codebook below).
ACCEPT  narrative:vaccines_for_profit  (Report's "premise note", applied as a row boundary) A bare revenue figure is a premise, parallel to the liability row (319124/6 vs 40526/2).
ACCEPT  narrative:covid_vaccine_ineffective  (Report note) Added "boosters weaken the immune system" / IgG4 examples (29 eps; 169690/0, 7806/5).
NO CHANGE  too_many_too_soon, vaccines_cause_sids, vaccines_chronic_disease, vaccines_not_placebo_tested, hpv_vaccine_harm, flu_shot_ineffective_harmful, turbo_cancer, mrna_alters_dna, vaccine_shedding, covid_vaccine_fertility  Report verdict "fine"; SIDS kept as rare but important, as the report recommends.

### COVID-19
MODIFY  narrative:covid_bioweapon_plandemic  Accepted weapon/deliberate-release core and lab-leak boundary (205647/2, 88102/4); replaced the example "Fauci funded a bioweapon (with intent alleged)" with plain examples, since a bare "bioweapon" is now explicitly lab leak.
MODIFY  narrative:covid_severity_exaggerated  Accepted widening to "kids/young don't need the vaccine" (~70 eps, 44 pods; 169936/0, 389455/2); widened rather than ADD per brief; name changed to "COVID's danger was exaggerated" to fit (ID kept).
ACCEPT  remove narrative:nsaids_worsen_covid  ~10 real episodes, all the March 2020 scare and its debunks; not recurring; the corpus-level research value is negligible. Fever-reducer-blunts-immunity claims route to `narrative:fever_suppression_harmful`.
NO CHANGE  covid_lab_leak, ivermectin_covid, hcq_covid, early_treatment_suppressed, hospital_protocols_killed, masks_useless_harmful, lockdowns_worse_than_virus, covid_deaths_inflated, long_covid_not_real, vitamin_d_prevents_covid, pandemic_censorship  Report verdict "fine"; ad and list issues go to the codebook.

### Cancer
ACCEPT  remove narrative:cancer_fungus_parasite  7 segs, 4 pods. The harmful practice it captured (baking-soda cures) stays coded via `natural_remedy_cures_cancer` (example added), parasites-cause-cancer via `parasites_cause_disease` (whose row already says "including cancer"), acid-body cancer via `alkaline_ph`. Kept-for-importance test fails because its harmful content has homes.
ACCEPT  remove narrative:cancer_epidemic_young  Subject frequent (341 eps) but the "ignored or hidden" core almost never stated; the rise is discussed as an open question, which `topic:cancer.causes_rates` already names ("early-onset cancer"). Vaccine cause = `turbo_cancer`; cover-up = `excess_deaths_cover_up`. See cross-slice note on benchmark gold.
MODIFY  narrative:natural_remedy_cures_cancer  Accepted the prevention/property boundary (~330 eps of "anti-cancer properties", "cancer-fighting", "starve cancer"); reworded so the treatment verbs count only "when said of existing cancer" and "cancer-fighting" in general does not, to avoid contradicting itself; added baking-soda example from the removed fungus label; kept soursop.
ACCEPT  narrative:sugar_feeds_cancer  Anti-angiogenesis "starve cancer" boundary (183909/0, 40268/0, 19275/2); bare "starve cancer" example replaced with "starve cancer of glucose".
ACCEPT  narrative:cancer_metabolic_disease  Mainstream Warburg-as-target boundary to `topic:cancer.causes_rates` (181570/7 vs 174993/8, 190372/152).
NO CHANGE  cancer_cures_suppressed, antiparasitics_cure_cancer, chemo_does_more_harm, cancer_screening_harmful  Report verdict "fine"; ad and idiom notes go to the codebook.

### Food & diet
MODIFY  narrative:saturated_fat_cholesterol_myth  Folded LDL-causality denial (170 eps, 41 pods; no other home) as the report proposed, rather than a separate ADD: it co-occurs with the diet-heart argument and keeps the same direction. Name updated to "do not cause heart disease". Statin boundary kept.
ACCEPT  remove narrative:sugar_hyperactivity  630 hits nearly all idiom ("sugar high") or glucose talk; the proposition appears in a handful of passing lines; a plain misconception, not a circulating contested narrative.
ACCEPT  narrative:food_dyes_harm_children  Widened to cancer (204990/6, 78331/3, 183756/6) and added policy-news boundary to `topic:food.additives_dyes`. ID kept (not actively misleading given the definition); name changed to "Synthetic food dyes are harmful".
MODIFY  narrative:us_food_banned_elsewhere  Accepted travel-anecdote scope (26 eps, 11 pods); core reworded to "more harmful ... because of ingredients ... other countries ban or restrict" so the anecdote (which names no ban) still fits; name updated, ID kept.
ACCEPT  narrative:food_engineered_to_harm  Hyperpalatability-without-malice boundary to `topic:food.ultra_processed` / `frame:big_food` (195480/0, 72189/1 vs 182053/0, 189369/1); examples paraphrase the quoted samples.
ACCEPT  narrative:soy_feminizes  "Soy boy" insult exclusion (14233/11, 5114/4, 90748/4); "soy boys" example dropped.
MODIFY  narrative:microwave_radiation_food  Accepted re-scoping to the oven-radiation fear (314218/1, 52662/12); home topic moved from `food` to `radiation_light` because the main voiced claim is radiation, not nutrients; plastics boundary points only to `narrative:household_toxins_poisoning` (whose row covers food packaging), not `microplastics_catastrophe` (whose core is "established cause of serious disease").
MODIFY  narrative:plants_are_toxic  Accepted individual-sensitivity exclusion (192684/1, 192681/3); compressed the grain/gluten boundary into one clause.
ACCEPT  narrative:beef_tallow_healthier  Product-attribute boundary and seed-oil co-coding rule (705/1,425 tallow eps also mention seed oils, mostly Masa reads).
ACCEPT  add narrative:salt_fears_overblown  44 proposition-level eps in 23 pods (192531/1, 176917/5, 181765/7); distinct guideline dispute parallel to saturated fat; electrolyte-advice exclusion kept. Home `food`.
NO CHANGE  seed_oils_toxic, sugar_is_toxic, raw_milk_superior, gmo_harmful, glyphosate_poisoning, artificial_sweeteners_harm, gluten_harms_everyone, carnivore_cures, fasting_cures, alkaline_ph, wellness_waters, red_meat_healthy, soil_depletion_supplements, alcohol_moderate_protective  Report verdict "fine".

### Not proposed by the report (recorded)
REJECT  merge beef_tallow_healthier + seed_oils_toxic  Report itself declined: different propositions; boundary added instead.
REJECT  add lab-grown / fake meat narrative  Report did not propose (~45 eps); topic material plus `depopulation_agenda` when the control angle is stated.

## Codebook

Sound suggestions from 12-narratives-a.md, for codebook-v8 section 5.2 (none encoded as labels):

1. **Coined terms: restrict "died suddenly" and drop "jab injured".** 5.2 says "died suddenly" and "jab injured" always carry the proposition. Evidence: "died suddenly" in 364 eps / 122 pods, ~9 of 12 samples obituaries, true crime or history (440162/0, 5189/0, 1923/7) against the coinage (39370/3, 204719/8). The term counts only as the coinage (the film, "the died-suddenly phenomenon", or alongside vaccine talk). "Vaccine injured" / "jab injured" used as an identity (3597/2, 186337/3) names a subject and maps to no single narrative; code the narrative whose proposition the passage adds. "Soy boy" is a worked example of an insult that invokes nothing. The `covid_vaccine_deaths` and `soy_feminizes` rows now carry matching boundaries.
2. **Implicature rule (a), ad cases.** Add worked examples: "no seed oils" (~4,400 eps), "non-GMO", "dye-free" are frame only; "when your doctor refuses to prescribe ivermectin... All Family Pharmacy" (42192/5) and emergency kits that "include ivermectin" (38363/2) state no COVID proposition (frames `anti_mainstream_medicine` + `commercialization` + product); but "ivermectin and mebendazole... triggering cancer cell death" (48633/3) is `antiparasitics_cure_cancer` as `advertisement`; the Hyman soil-depletion read (182661/0, 182360/1) states its narrative. "No garbage, no seed oils... you feel the difference" (6683/4) stays a frame.
3. **Verbs of benefit.** Keep interchangeability, but add: a property or prevention claim ("anti-cancer properties", "cancer-fighting foods", "lowers your risk", "anti-inflammatory") does not invoke a cure-type narrative; cure narratives need treatment or reversal of an existing disease. Evidence ~330 eps (190828/44, 7576/13, 174958/4, 40268/0). The `natural_remedy_cures_cancer` row now says this for cancer; the general rule belongs in 5.2.
4. **Lists of grievances.** A litany ("You lied about the vaccine... school closures... the mask... early treatments", 38529/2, 39501/3) invokes a narrative only for items that state or plainly imply its proposition ("lied about masks" -> `masks_useless_harmful`; "lied about early treatments" -> `early_treatment_suppressed`; "lied about school closures" -> `frame:government_distrust` only). Parallel to the topic co-labeling rule on political issue lists.
5. **Policy news vs proposition.** Reporting an agency action (Hep B birth-dose change, red-dye phase-out, Tylenol announcement) is a topic only; the narrative is `reported_or_quoted` only when the official's harm or benefit claim is relayed ("RFK said red dye causes cancer and the FDA banned it", 204990/6 vs 185624/6). The hep B and food-dye rows now carry this boundary.
6. **Mockery is a rebuttal: add a microchip example.** `vaccine_microchips_5g`, `vaccine_shedding`, `cancer_cures_suppressed`, `sugar_is_toxic` are often invoked only in ridicule (322024/6, 175855/2, 84411/6, 71184/11). Add a microchip joke to the sarcasm sentence so labelers do not drop these as jokes (moved here from the proposed microchip row).
7. **Premise examples.** Add `vaccines_for_profit` beside the liability and soil examples in the premise sentence (revenue figure alone is a premise; 319124/6). Applied to the row as well.
8. **ASR variants for the labeler rubric:** ivermectin / "ivermectan" / "iver"; mebendazole / "membenzol" / "mbenbendazole" / "Medbendazol"; fenbendazole / "fenben"; glyphosate / "glyphosphate"; Simoncini / "Simontelli"; SADS / "sad sudden arrhythmic death". (Regex QA note: "Warburg" matches "Warburton", "Seyfried" matches Amanda Seyfried.)
9. **Idiom exclusion already covers** "chemo is poison" as a political metaphor (438986/3, 323867/7) and "sugar high" for markets or politics; worth naming as examples in section 3's idiom rule.

Rejected as codebook material: item 9 of the report (search-tool process note) is not codebook content.

## Cross-slice notes

- **Benchmark gold uses removed labels.** `benchmark/v2/gold.jsonl` has 2 `narrative:cancer_fungus_parasite` detections (item c174944w0003, a parasite-to-tumor progression; under v8 these are `parasites_cause_disease`) and 2 `narrative:cancer_epidemic_young` (item c178194w0005, "I never saw pancreatic cancers in 30 year olds... since 2021", which under rule (b) is topic-only unless the vaccine is implied). Gold v2 is v7/v8-era; whoever rebuilds the benchmark for the post-review label set needs to remap these. Also 2 hits each of `nsaids_worsen_covid` and `sugar_hyperactivity` appear in benchmark reference/taxonomy files (not gold).
- **`parasites_cause_disease` (other_narratives / detox home):** after removing `cancer_fungus_parasite`, its examples could add "a parasite becomes a tumor" (from the gold item above). Not patched.
- **`fever_suppression_harmful`:** the routing target for any residual NSAID/COVID immunity claim; its definition need not change.
- **`topic:cardiovascular.cholesterol_lipids`** already lists "cholesterol hypothesis; lean mass hyper-responders", consistent with the widened `saturated_fat_cholesterol_myth`. `topic:cardiovascular.blood_pressure` covers "salt and blood pressure", the topic for `salt_fears_overblown` passages.
- **`topic:radiation_light`** has no subtopic for microwave ovens; passages for `microwave_radiation_food` will take the parent or `food` topics. A coverage group may want "microwave ovens" added to an existing radiation subtopic's examples.
- **`cancer_screening_harmful`:** 109 of 258 hits are a Chiro Hustle thermography ad; ad-rule worked example (codebook item 2) covers it.
