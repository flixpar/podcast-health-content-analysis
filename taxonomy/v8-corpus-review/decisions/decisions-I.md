# Decisions, group I (report 02, food and diets)

Patch: `patch-I.jsonl` (21 changes, 1 add, 0 removes, 0 parent edits). Written
against the installed `taxonomy/health-v8.md` (already carrying the other groups'
merged edits: `gut.digestive_symptoms` now owns lactose intolerance and stomach
acid, `supplements.other_compounds` owns exogenous ketones and sulforaphane
capsules, `supplements.other_vitamins_minerals` sends ready-to-drink sports
drinks to `food.beverages_hydration`, `infectious.antibiotics_resistance` sends
"raised without antibiotics" to `food.organic_gmo`, and the narratives
`salt_fears_overblown` and `dietary_guidelines_caused_obesity` exist). No food or
diets row had been edited by another group, so every CHANGE starts from the
current row. Validated: `apply_patches.py` applied cleanly (`check-I.md`),
`compile_taxonomy` succeeded, and every backticked reference resolves.

General editing rule applied throughout: pure health-content scope sentences
the report put into rows (pet-food ads, fast food as restaurant chatter, SNAP
shutdown politics, "vegan leather" and menu options, Lent abstinence, the
LONGEVITY intro, "soy boy" insults, "gluten-free" as ad copy, "juicing" as
steroid slang) were left out of the label set; they are codebook rules and
codebook-v8 already carries almost all of them (see Codebook). Routing sentences
that name a neighbouring label were kept.

## Proposals

MODIFY  topic:food.ultra_processed  Examples replaced with the real phrasing (3,208 non-ad eps / 145 pods; "UPF" only 30 eps), "NOVA classification" added to the definition (6155/4). The pet-food and restaurant-chatter sentences dropped: codebook 3.4 (pet-food ads) and 3.4 "food talked about purely as taste, cooking or restaurants" already exclude them.
ACCEPT  topic:food.fats_oils  Low-fat diets and the low-fat era (407 non-ad eps / 94 pods) and "PUFAs" (190897/114) added; the omega-6:omega-3 balance mirrors the `supplements.omega3` pointer. Added a `cardiovascular.cholesterol_lipids` pointer so dietary versus blood cholesterol is explicit.
MODIFY  topic:food.meat_animal_foods  Bone broth (858 eps / 93 pods) and meat substitutes (lab-grown meat and bugs 322 / 82; plant-based meat brands 564 / 100) added; name widened to "Meat, eggs, fish & meat substitutes" (ID kept). Lent sentence dropped (codebook section 2 has religious abstinence). Added a `diets.plant_based` boundary for the diet itself.
ACCEPT  topic:food.dairy_raw_milk  "dairy intolerance" removed (it collided with `gut.digestive_symptoms`, which now lists lactose intolerance, 485 eps); full-fat dairy (181911/4) and going dairy-free added.
ACCEPT  topic:food.protein_intake  "protein-maxxing" (14 eps) replaced with "getting enough protein", "grams of protein a day", "high-protein diet" (4,543 non-ad eps / 188 pods; 195869/11).
MODIFY  topic:food.plant_foods_fiber  "fibermaxxing" (1 ep) dropped; phytoestrogens, phytonutrients, broccoli sprouts added; "eaten in food" added with a form boundary (capsule or extract → its `supplements` subtopic; fiber supplements → `gut.probiotics_fermented`, matching rule 5 and 193019/2). The "soy boy" sentence dropped (codebook 5.2 already has it).
MODIFY  topic:food.additives_dyes  ASR forms added ("red forty", "red dye number three" 175808/0, GRAS heard as "a grass" 181944/2), plus brominated vegetable oil and potassium bromate. The report's "Red 40 (also … red dye number three)" conflated Red 40 and Red 3; listed as separate examples.
ACCEPT  topic:food.micronutrients_food (bioavailability part)  Bioavailability qualified to food (most of 1,666 "bioavailab-" eps are supplement forms, 182442/5); supplement-form bioavailability goes to the supplement subtopic. "nutrient-dense" (1,771 eps) is the leading example.
MODIFY  topic:food.micronutrients_food (salt part)  Salt not folded in here; it gets its own subtopic (next line). The row now points dietary salt to `food.salt_sodium`.
ACCEPT  add topic:food.salt_sodium  The report's optional ADD, chosen over folding salt into `micronutrients_food`. Reasons: (1) it clears the bar easily, 636 non-ad eps / 102 pods, 50 pods with 3+ eps (verified in fd/out_r4.txt); (2) salt talk is about an ingredient and a guideline dispute (how much, low-sodium diets, Celtic salt, "salt your food"), not nutrient density from named foods, so folding it in would make about a quarter of `micronutrients_food` a different subject; (3) the new `narrative:salt_fears_overblown` (44 eps / 23 pods in F1) needs a topic denominator, the same pairing the label set already has for sugar, seed oils, raw milk and dyes; folded into micronutrients that denominator could not be counted. Boundaries: blood pressure co-label (`cardiovascular.blood_pressure` already lists "salt and blood pressure"), electrolyte powders and salt tablets to `supplements.other_vitamins_minerals`, "salt, sugar and fat" of processed food to `food.ultra_processed`. Blood sodium as a lab value is outside "dietary salt" by definition.
ACCEPT  topic:food.eating_behavior  Overeating, late-night eating, ghrelin and leptin added (3,842 non-ad eps / 208 pods; 6441/17); binge-eating disorder pointed to `mental.eating_disorders` (356 eps).
MODIFY  topic:food.food_system_access  "what it may buy" and "SNAP soda restrictions" added (182412/5). Rejected the "price of eggs" example: the 571 egg-price eps are mostly inflation talk with no health dimension, and the example would invite false positives. The SNAP budget-politics sentence moved to the codebook list below.
MODIFY  topic:food.general_nutrition  Standard American diet (520 eps / 58 pods) and official dietary advice as a whole (573 non-ad eps / 100 pods; 181856/15, 7607/3) added. The report said guidelines had "no stated home"; in fact `policy.public_health_authority` lists dietary guidelines and their committee. Resolved by the policy parent's own rule: the guidelines' nutritional content goes here, and `policy.public_health_authority` is added only when the guidelines as an institution or process are discussed (named by exact ID instead of the report's vague "`policy` subtopics").
ACCEPT  topic:diets.low_carb_keto  Bare "ketones" replaced by "ketones from diet", with the exogenous-ketone pointer to `supplements.other_compounds` (which already points back; 296 eps / 34 pods, 437282/4); carb cycling added (203 eps / 36 pods).
MODIFY  topic:diets.plant_based  Pescatarian and low-fat plant-based programmes (Esselstyn, Ornish; 181082/1) added. "Vegan leather" and menu-option sentence dropped (codebook: taste, cooking, restaurants; menu-variety lists). Added a meat-substitute pointer to `food.meat_animal_foods` to match that row.
ACCEPT  topic:diets.fasting  Religious fasting included only when health effects are discussed (181815/15); fasting blood tests routed to `metabolic.insulin_glucose` (676 eps / 50 pods of lab-value hits; exact ID used instead of the report's bare `metabolic`); juice cleanses to `detox.organ_cleanses`. Did not add "autophagy from fasting" as an example (autophagy is `longevity.cellular_ageing`; rule 1 handles the co-label).
MODIFY  topic:diets.ancestral_paleo  "pegan" (114 eps / 11 pods) and "nose-to-tail eating" added. The LONGEVITY-intro sentence dropped: codebook 3.4 excludes recurring intro or outro boilerplate (457 eps).
ACCEPT  topic:diets.mediterranean_whole_food  MIND diet and the general anti-inflammatory diet (182423/1) added; Blue Zones as lifestyle or lifespan (189446/3, 611702/4) routed to `longevity.ageing_science`, which already lists "Blue Zones (as longevity)".
MODIFY  topic:diets.elimination_therapeutic  Anti-inflammatory diet split by use (regimen 192823/3 stays here; general pattern 182423/1 goes to `diets.mediterranean_whole_food`); Whole30 (149 eps / 60 pods) and low-oxalate added. The "gluten-free as ad attribute" sentence dropped: codebook 4.1 free-from lists and menu-variety rule cover it.
ACCEPT  topic:diets.calorie_counting  "counting points" dropped (WeightWatchers is `weight.weight_loss_methods`); the energy-balance idea itself added, since CICO is mostly contested talk (182898/1, 182104/0); IIFYM and MyFitnessPal added.
MODIFY  topic:diets.raw_food_juicing  Kept despite rarity (154 non-ad eps / 60 pods; celery juice 94 / 39), with the boundary to `detox.organ_cleanses` for time-limited cleanses (235 eps / 81 pods) and "Medical Medium" added. The steroid-slang "juicing → peds" sentence dropped from the row (codebook section 2 lists it).
ACCEPT  (no merges or drops in this slice)  All 25 labels clear 30 eps / 3 pods in non-ad text.
NO-OP   topic:food.sugar_sweeteners, topic:food.grains_carbs_gluten, topic:food.food_contaminants, topic:diets.carnivore_animal_based  Report verdict "fine"; no edit proposed.

Edits in this slice prompted by other groups' notes (not report 02):

ACCEPT  topic:food.organic_gmo  Added livestock-raising practices and the examples "pasture-raised", "raised without antibiotics", "no added hormones", plus a pointer to `infectious.antibiotics_resistance`, to mirror that row's installed boundary (decisions-A cross-slice note; ~1,056 eps, mostly meat ads).
ACCEPT  topic:food.beverages_hydration  Added "ready-to-drink sports and electrolyte drinks" and the examples "sports drinks; Gatorade" to mirror the installed `supplements.other_vitamins_minerals` split (decisions-B cross-slice note; report 02 also notes the split).

## Codebook

All nine report-02 notes are sound, and codebook-changes.md records that all nine
are already in the installed codebook-v8 (cited there as 02-1 to 02-9):

1. 4.1 free-from lists in a food read: topic the product only, frames only where the language occurs (5,408 eps, 654 outside ads; Nature Raised Farms is 3,594 of 5,878 "seed oils" eps). Installed.
2. 3.3 meal-kit menu-variety lists fail the ad test without a stated benefit (Cook Unity, ~1,950 Shapiro eps, 390755/0). Installed.
3. 3.4 pet-food ads excluded even when they generalize about processed food (2,597 eps / 25 pods, 18685/0). Installed.
4. Section 2 ambiguous words: "juicing", "fiber", "MSG", "Whole Foods", "fasting insulin/glucose", religious fasting and Lent. Installed.
5. 3.4 recurring intro or outro boilerplate (LONGEVITY, 457 eps). Installed as exclusion.
6. Rule 5: bioavailability and sulforaphane follow the form (182442/5, 193019/2). Installed.
7. Rule 1: a diet's effect on appetite and sugar cravings add `food.eating_behavior` (6441/17, 19857/11). Installed.
8. 5.2 `unlisted_narrative` for "CICO is a myth" and "they want you to eat bugs"; the food-pyramid proposition is now `narrative:dietary_guidelines_caused_obesity`. Installed.
9. 4.1: a change of register alone delimits an unmarked read (Pardon My Take ONE bar, 128564/3). Installed.

Two scope items from the report's row proposals that the codebook does not yet carry (sound, small):

- Section 3: food-assistance politics with no nutrition or health point (SNAP lapses in a shutdown, benefit budget fights; 166196/0, 81594/0) is not health content; SNAP restrictions on soda or candy are (182412/5). Belongs with the political-issue-list test.
- Section 2 or 3.4: "vegan" as a material ("vegan leather", 30647/0) is not health content; "vegan option" on a menu is already covered by the taste, cooking or restaurants bullet.

## Cross-slice notes

- `policy.public_health_authority` (policy slice): its definition and examples claim "dietary guidelines" outright, while `food.general_nutrition` now takes official dietary advice as nutrition content. Suggest it say "dietary guidelines as an institution or process (committees, revisions, authority); what they advise goes to `food.general_nutrition` or the food's subtopic", consistent with the policy parent's own rule.
- `cardiovascular.blood_pressure` (cardio slice): already lists "salt and blood pressure"; consistent with the new `food.salt_sodium` co-label rule. No change needed. Optionally add a pointer: "dietary salt as such goes to `food.salt_sodium`".
- `narrative:salt_fears_overblown` (narratives slice): home `food` is fine; its topic counterpart is now `food.salt_sodium`.
- `detox.organ_cleanses` (detox slice): already lists "juice cleanse"; consistent with the new boundaries in `diets.raw_food_juicing` and `diets.fasting`.
- `weight.weight_loss_methods` (weight slice): already lists WeightWatchers and Noom; consistent with `diets.calorie_counting`.
- Possible future narrative (narratives slice): "calories in, calories out is a food-industry myth" (182104/0, 182898/1, 182350/4) recurred in the report's samples; not counted at proposition level, so not proposed here.
