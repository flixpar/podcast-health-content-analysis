# Decisions F2: report 13 (narratives B: pharma, wellness, hormone, system, other)

Patch: `patch-F2.jsonl` (38 changes, 3 adds, 2 removes, 0 parent edits). It was validated with
`apply_patches.py`, which wrote `check-F2.md`, and with `tl.compile_taxonomy`. Every backticked
reference in the patched rows resolves after the patch.

## Pharma family

- ACCEPT  narrative:pharma_creates_customers  "Sick care" (154 eps) is mostly a reactive-care critique. The row adds an actor and motive split (profit vs control vs food industry) and drops "sick care" from the examples. Tightened to 3 sentences.
- ACCEPT  narrative:antidepressants_ineffective  The "doesn't work for everyone" and "overprescribed" exclusion is backed by 185586/1 and 175579/6. Examples are real phrasing.
- ACCEPT  narrative:chemical_imbalance_myth  The folk-use exclusion is backed by evidence: 397 eps contain the phrase, while 128 state or debate the theory. Now points to the new `mental_illness_not_real`.
- MODIFY  narrative:ssris_cause_violence  Accepted the "offered as the explanation" sentence. Dropped the bare "psych meds" example because it does not carry the proposition, and kept "school shooters on SSRIs".
- ACCEPT  narrative:therapy_harms_children  Widened to young people and over-diagnosis (138 eps / 27 podcasts; 43 / 26).
- ACCEPT  narrative:tylenol_autism  Glutathione mechanism added (25 eps / 15 podcasts).
- MODIFY  narrative:fever_suppression_harmful  Accepted the "fever is good" counting sentence. Merged examples and kept "Tylenol blunts the immune response".
- ACCEPT  narrative:birth_control_harms  Harms list extended. Clot risk stated as prescribing information is now a topic (190883/129).
- ACCEPT  narrative:glp1_dangers  Added "stomach paralysis" plus exclusions for ad boilerplate and muscle-loss mitigation (83880/1, 176587/3).
- MODIFY  narrative:adhd_meds_harmful  Accepted. Merged the comedy exclusion and the `mental_illness_not_real` pointer into one sentence to stay at 3 sentences.
- ACCEPT  narrative:medical_errors_leading_cause  Examples only (186171/2).
- ACCEPT  narrative:fluoride_lowers_iq  The pineal-harm-without-control boundary is clean (181242/4).
- ACCEPT  narrative:fluoride_mind_control  The mirror boundary (14582/0).
- MODIFY  narrative:root_canals_amalgams_illness  Accepted the "cavitation" ambiguity sentence. Kept the "titanium implants" example, because metal implants are still in the core.
- NO CHANGE  statins_harmful, leucovorin_autism_treatment, abortion_pill_dangerous, hrt_dangerous, hrt_fears_overblown, sunscreen_harmful, sun_exposure_cures, deodorant_breast_cancer  The report found each fine or rare-but-keep. I agree: deodorant_breast_cancer (19 eps / 10 podcasts) and leucovorin (22 / 13) are classic or topical misinformation and stay.
- ACCEPT  ADD narrative:mental_illness_not_real (pharma_narratives, home mental)  61 eps / 38 podcasts on a narrow query (206905/1, 12761/5, 206410/4, rebuttal 185633/1). Distinct from the chemical-imbalance, antidepressant and therapy-culture narratives. The add's own text lightly copy-edited.

## Wellness family

- ACCEPT  narrative:germ_theory_denial  "Terrain theory" is mostly the soft claim (181309/0, 190046/72). Hard denial is rarer (54 eps / 26 podcasts). Dropped "terrain theory" as a bare example.
- ACCEPT  narrative:parasites_cause_disease  Routine-cleanse advice counts (192397/0, 78216/4, 48614/2).
- ACCEPT  narrative:stealth_infections_root  Single-disease exclusion added (190832/70), matching `inflammation_root_cause`.
- ACCEPT  narrative:detox_needed  "Toxic load" is the dominant coined term (889 eps / 111 podcasts).
- MODIFY  narrative:adrenal_fatigue_real  Accepted the renaming sentence. Replaced the parenthetical example "HPA axis dysfunction (as the lay renaming)" with a phrase people actually say, so that clinical HPA-axis talk is not pulled in.
- ACCEPT  narrative:peptides_safe_miracle  Single-use exclusion added (190501/30). "Natural because the body makes them" added (78334/6).
- ACCEPT  narrative:energy_frequency_healing  Added "quantum" (178180/4). PEMF for cleared uses is a topic.
- ACCEPT  narrative:alzheimers_reversible  "Type 3 diabetes" alone is not reversal (190596/30). Example replaced with "MCT oil reverses Alzheimer's".
- ACCEPT  narrative:chemtrails  The byword-for-conspiracy exclusion fits the evidence (492 eps, mostly list tokens or mockery).
- ACCEPT  narrative:microplastics_catastrophe  "Proven/established" wording matched almost nothing: 17 causal eps against 1,256 subject eps. Presence alone is now a topic. The name now reads "causing", and the ID is kept as not actively misleading.
- ACCEPT  narrative:household_toxins_poisoning  Product-attribute vs disparaging-ad boundary (175060/4).
- ACCEPT  narrative:tampon_toxins  Toxic shock syndrome excluded (23920/0, 21232/0).
- ACCEPT  narrative:baby_food_metals_harm  Presence or regulation alone is a topic (174978/5). Dropped the presence-only examples.
- NO CHANGE  heavy_metal_toxicity_widespread, mold_toxicity_widespread, metabolic_dysfunction_root, inflammation_root_cause, leaky_gut_root_cause, candida_overgrowth_widespread, chronic_lyme_widespread, mthfr_explains_illness, vitamin_megadose_cures, methylene_blue_miracle, red_light_cure_all, grounding_heals, nad_reverses_ageing, fringe_chemical_cures, autism_recoverable, emf_5g_harm  The report found each fine. Ad-volume notes go to the codebook.
- KEEP (no op)  narrative:glasses_worsen_vision  About 10 eps / 4 podcasts. A classic, cheap narrative; keep.
- KEEP (no op)  narrative:chiropractic_stroke_risk  About 10 real eps, and the risk is real and contested; keep.
- ACCEPT  REMOVE narrative:vitamin_a_toxicity  1 asserting and 1 questioning episode in about 145k transcripts. The remaining hits are a MeatEater person and polar-bear liver history; real hypervitaminosis talk would be mislabeled by this row. The measles/vitamin A debate stays in `measles_harmless`. `unlisted_narrative` covers the rare case. It is not used in any benchmark gold (only the compiled `benchmark/v3/taxonomy.json` lists it).
- ACCEPT  REMOVE narrative:heart_not_pump  About 3 episodes across 2 podcasts (189960, 70858/0, 190300/321). Removed only because the corpus shows it is essentially absent. `unlisted_narrative` covers it. It is not used in any benchmark gold.

## Hormone family

- ACCEPT  narrative:testosterone_collapse  Excludes age-related decline (175006/0, 179777/0).
- ACCEPT  narrative:semen_retention_benefits  "NoFap" as porn abstinence is excluded (28542/5, 197055/1).
- ACCEPT  narrative:endocrine_disruptors_feminizing  Adds the coined "gay frogs" (318940/23, 14753/6) and excludes atrazine named only in a list (181100/9).
- ACCEPT  narrative:gender_care_harmful_youth  Dominant vocabulary ("butchery", "mutilation", "chemical castration") added as elaborations and examples.
- MODIFY  narrative:gender_care_lifesaving  Accepted the "dead daughter or living son" coined form. Folded it into the second sentence to keep 3 sentences.
- ACCEPT  narrative:trans_identity_disorder  Removed "gender ideology" from the definition and examples. As a bare political label it points to `frame:political_partisan` (about 1,700 matching eps, mostly culture-war politics).
- ACCEPT  narrative:abortion_infanticide  Folds in "up until the moment of birth" (170 eps / 18 podcasts; same shows and rhetoric as born-alive, 142 / 23). ID and name kept.
- NO CHANGE  narrative:sperm_count_collapse  Fine. The co-occurrence note goes to the codebook.

## System family

- MODIFY  narrative:sickest_generation  Accepted the obesity-statistic exclusion and merged it into the second sentence (3 sentences). Added the real phrase "the most depressed, sick generation in history" (37752/2).
- ACCEPT  narrative:fda_captured  Examples are now real phrasing (182536/0, 7981/2, 205194/4). Points to the new `pharma_ads_control_media`.
- MODIFY  narrative:doctors_paid_to_prescribe  Accepted both exclusions: patient incentives (1139332/0) and documented opioid kickbacks as history (175114/7). Kept "pharma perks for doctors" as an example.
- ACCEPT  narrative:depopulation_agenda  Requires a health means. The Great Reset as economics or politics is excluded (11916/5, 39939/3).
- NO CHANGE  autism_epidemic_environmental, outbreak_engineered, excess_deaths_cover_up, assisted_dying_expansion, fentanyl_foreign_attack  The report found each fine.
- MODIFY  ADD narrative:social_media_youth_mental_health (system_narratives, home mental)  469 eps / 137 podcasts, voiced and openly contested. Changed the core from "the main cause" to "are causing the rise", because the codebook says magnitude words are not thresholds. The topic reference now uses the full form `topic:cognition.digital_media_brain`.
- MODIFY  ADD narrative:pharma_ads_control_media (system_narratives, home health_system)  164 eps / 52 podcasts (175095/0, 40281/3, 178198/3, 84749/6). Distinct from `fda_captured`. The premise-only case now names its topic, `topic:health_system.pharma_industry`. Added the boundary with `fda_captured` and the example "they started buying advertising on CNN".

## Other

- NO CHANGE  narrative:unlisted_narrative  Keep. The watched-but-not-proposed items (GLP-1 miracle drug, 38 eps / 28 podcasts mostly passing; statins overused) are not added.

## Codebook

These are the report-13 suggestions I judge sound. None is encoded as a label.

1. **5.2, folk use is not a stance.** A speaker who uses the opposite of a narrative as an everyday explanation ("he has a chemical imbalance") does not invoke the narrative. Code `rebutted` only when the proposition is present and argued against. Evidence: 397 eps contain "chemical imbalance" and 128 state or debate it. Already encoded in the `chemical_imbalance_myth` row; the general rule belongs in 5.2.
2. **5.2, slogans that do not carry the proposition.** These are counter-examples to the coined-term rule:
   - "sick care" (154 eps)
   - "gender ideology" (about 1,700 eps)
   - "the Great Reset"
   - "terrain theory"
   - "type 3 diabetes"
   - "NoFap"
   - "chemtrails" and "flat earth" used as bywords for conspiracy belief

   The test is whether the term's ordinary use in the corpus commits the speaker to the proposition. Sound; the affected rows already say so individually.
3. **5.2, actor and motive decide among "they want us sick" narratives.**
   - Profit, with pharma or medicine as actor: `pharma_creates_customers`.
   - Food industry: `food_engineered_to_harm`.
   - Elites or government with a control motive: `depopulation_agenda`.
   - Unspecified "they": a distrust frame only, plus `conspiracy_cover_up` if coordination is alleged.

   Evidence: 6660/0, 10589/5, 195939/0. Encoded in the pharma_creates_customers and depopulation_agenda rows; a codebook line would make it visible.
4. **5.2, side effects and presence findings versus harm narratives.**
   - Labelled side effects stated as prescribing information, or as something to manage, invoke no harm narrative (190883/129, 176587/3).
   - Contaminant presence (microplastics in the brain, lead in baby food, PFAS in blood) invokes no disease narrative unless a disease is attributed (20037/0, 174978/5).
5. **5.2(a) and the disparaging-imperative rule in ads, a tie-breaker.**
   - A "non-toxic", "tested for X" or "free of X" attribute is a frame only.
   - Copy saying the ordinary product or condition harms you invokes the narrative as `asserted_or_endorsed`. Examples: "stop cooking with toxic cookware" (175060/4); "parasites … that sabotage your energy" (162533/2); "a parasite cleanse at least once a year" (48614/2).
   - Pharma ad safety boilerplate (83880/1) invokes no narrative.

   Ads drive the raw volume of the parasite, mold-coffee, cookware, EMF, red-light, grounding, quantum-device and baby-food labels.
6. **Section 3 and 5.2, recreational drug comedy.** Comparing prescription stimulants to street drugs in jokes or anecdotes invokes no narrative unless prescribing is the point (18771/5, 63118/16). Encoded in the adhd_meds_harmful row as well.
7. **Section 6, parody voicing.** A proposition voiced in obvious parody to mock it is `rebutted`. Example: the Daily Wire promo voicing gender-affirming care as suicide prevention (206490/7, 388506/5). Worth citing next to the existing sarcasm sentence in 5.2.
8. **5.2, single disease versus root of all disease.**
   - `inflammation_root_cause` and now `stealth_infections_root` exclude a single disease.
   - `metabolic_dysfunction_root` should get the same sentence. I did not change it because the report proposed no row edit; its core already says "nearly all chronic disease".
   - `leaky_gut_root_cause` deliberately allows a single disease such as autoimmunity. Say so in the codebook to avoid inconsistent coding.
9. **Co-occurrence.**
   - `sperm_count_collapse` and `testosterone_collapse` both apply when one span states both.
   - Atrazine "to make them have low test" (64192/4) takes `endocrine_disruptors_feminizing`, plus `depopulation_agenda` when control is the stated point.
   - `inflammation_root_cause` and `metabolic_dysfunction_root` can share a span (182016/1).
10. **Search notes for future corpus passes** (tooling, not labelling). Use word boundaries on `\bcandida\b` and `\bearthing\b`. Known noisy terms:
    - "cleanse" (scripture)
    - "kirsch" (Steve Kirsch)
    - `\bwhi\b` (ASR noise)
    - "count ?down" (sports)
    - "odgers" (Rodgers, Dodgers)
    - "formula" (mostly non-infant)
    - "revolving door" and "regulatory capture" (mostly non-health)
    - "bad energy" (reality TV)
    - "Garrett Smith" (MeatEater)

    Recurring ad reads inflate counts: The Daily (Title X), Jockers (turmeric), Habits and Hustle (red light), The Toast (Caraway), SuperLife (multi-modality pad).

## Cross-slice notes

- **`frame:big_pharma`.** Its examples include "pharma owns the media", which is now the core of `narrative:pharma_ads_control_media`. The frame owner may want to keep it as rhetoric and add a pointer such as "the claim that drug advertising controls coverage is `narrative:pharma_ads_control_media`". It could also add "pharma ads" to `frame:media_distrust`'s neighbour note.
- **`topic:cognition.digital_media_brain`.** It has an example "social media and teens", and its definition covers mood. The mind-slice group may want a sentence pointing to `narrative:social_media_youth_mental_health` for the causal crisis claim.
- **`frame:industry_distrust`.** Its examples include "the sick-care business". That is consistent with the new rule that "sick care" alone is not `pharma_creates_customers`, so no change is needed. Noted for the frame editor.
- **`topic:health_system.regulators`.** It lists "revolving door" as an example; `fda_captured` keeps it as an example too. That is consistent with codebook rule 4 (subject vs rhetoric), but the report found bare "revolving door" mostly non-health.
- **Benchmark impact.** `benchmark/v3/taxonomy.json` (compiled) lists the two removed narratives. No gold file uses them.
