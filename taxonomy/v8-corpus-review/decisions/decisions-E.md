# Group E decisions: reports 09 (substances, medications, system, policy) and 11 (alt medicine, detox, environment, radiation/light, beauty, wellness)

Patch: `patch-E.jsonl` (40 changes, 1 add, 0 removes, 1 parent edit). It applies cleanly to
health-v8.md (`check-E.md`) and compiles with `tl.compile_taxonomy`. Every backticked reference
resolves after the patch.

General editing choice: wherever a proposed row added a sentence that is really a health-content
scope rule (a single drunk night told as a story, drug crime narrated as plot, figurative
"addicted to", "alcoholic" as an adjective or insult, coffee as an errand, non-health insurance,
spray tans, a health figure's name alone), I left it out of the row and listed it under Codebook.
Label-specific boundaries that point to a neighbouring label stayed in the rows.

## Report 09: substances, medications, health system, policy

MODIFY  topic:drugs_addiction (parent)  The parent definition said "addiction and recovery from any substance", which contradicts the accepted alcohol/drug split. It now says "any substance other than alcohol alone", with alcohol-only dependence going to `alcohol`.
ACCEPT  topic:drugs_addiction.opioids_fentanyl  Added prescription pain pills used outside medicine, plus "percs" and "pain pills" (gold c71184w0031; 2,824 eps on the benzos/percs query).
ACCEPT  topic:drugs_addiction.stimulants_illicit  Non-prescribed Adderall had no home except ADHD, which would inflate ADHD counts ("now they're all on Adderall", 663/6). Added the boundary to `neurodevelopment.adhd` and used the real phrasing as an example.
MODIFY  topic:drugs_addiction.addiction_recovery  Accepted the split: alcohol alone → `alcohol.alcohol_use_disorder`, behaviours → `mental.behavioral_addictions`. Moved AA to the alcohol row. Kept "any substance other than alcohol alone", so nicotine dependence still lands here, as the gold has it ("Quit with Jones"). Moved the figurative "addicted to" sentence to the codebook (4 of 12 samples were figurative).
MODIFY  topic:drugs_addiction.drug_policy  Dropped "cartels" (0 of 10 samples were health), added drug testing as an issue and routed sport testing to `peds.doping_sport`. Moved the "drug crime as a story event" sentence to the codebook as a crime-narration scope rule (7,538 eps).
ACCEPT  topic:psychoactives.cannabis  Smoking cannabis now routes away from `stimulants.smoking` (5,894 eps of "smoke weed / a joint"). THC drinks also take `alcohol.alternatives`. Changed "gummies" to "THC gummies" to avoid vitamin gummies.
ACCEPT  topic:psychoactives.psychedelic_therapy  MDMA, ecstasy and molly had no home, and the street vocabulary (shrooms, acid) is what speakers actually say.
MODIFY  topic:psychoactives.microdosing  Kept the GLP-1 boundary (154 eps / 36 podcasts) and the THC boundary. Dropped the "microdosing exercise" clause because it names no neighbouring label and is just a word sense.
ACCEPT  topic:psychoactives.novel_substances  Added GHB, whippets, gas-station heroin and "party drugs with no other home" (kratom/7-OH/tianeptine: 548 eps / 96 podcasts).
MODIFY  topic:alcohol.drinking_culture  Added drink-driving as a risk (3,657 eps) and alcohol policy (445 eps). Moved the "single drunk episode in a story" sentence to the codebook.
MODIFY  topic:alcohol.alcohol_use_disorder  Added a person described as an alcoholic, AA, Al-Anon and dry drunk, with a boundary back to `addiction_recovery`. The "alcoholic drink" and insult/simile senses went to the codebook. The NAFLD boundary went to `alternatives`, where the collision actually happens.
ACCEPT  topic:alcohol.alternatives  Added the NAFLD boundary (156 eps) and the THC co-label. Kept "kava drinks", which are a genuine alcohol substitute (kava bars).
ACCEPT  topic:stimulants.smoking  Tobacco industry and regulation (788 eps / 127 podcasts) had no home because `pharma_industry` does not cover tobacco. Added the cannabis boundary.
ACCEPT  topic:stimulants.nicotine_products  Dip, chew and snus had no home (44378/8, 24239/11). Added Lucy (177 eps of ads).
MODIFY  topic:stimulants.caffeine  Kept the inclusion condition (caffeine, effect, dose, timing or a health effect discussed). Moved "coffee as an order, errand or setting is not health content" to the codebook (0 of 10 comedy samples were health).
ACCEPT  topic:medications.other_drugs  Preventive antibodies (Beyfortus, 30489/4) had no home; muscle relaxers are in the gold (c128911w0034).
MODIFY  topic:health_system.costs_insurance  Added health-care fraud (270 eps / 58 podcasts; the gold already puts it here, c38054w0004) and the matching name. Moved the "car, life and disability insurance" exclusion to the codebook as a scope rule.
MODIFY  topic:health_system.ethics_law_privacy  Added "medical freedom" and bodily autonomy as principles (1,788 eps). Added a boundary to `frame:medical_freedom`, which already exists for the rhetorical use; the report did not mention that frame.
MODIFY  topic:policy.hhs_leadership  Added fraud and spending drives plus Makary and Oz examples. Replaced "a name or campaign is not health content" with a label boundary: a campaign takes `policy.partisan_politics` only when health positions are discussed. The name-only rule went to the codebook (6 of 10 RFK samples were campaign politics).

No ADD, REMOVE or MERGE was proposed in report 09. I agree: harm_reduction, microdosing and regulation_chemicals_food_drugs are rare but distinct.

## Report 11: alt medicine, detox, environment, radiation/light, beauty, wellness

MODIFY  topic:alt_medicine.functional_medicine  Kept a short label-specific exclusion for titles in bios, intros and referrals (3,129 eps, mostly credentials: 192671/3, 177023/0). The general practitioner-credential rule is also listed for the codebook. Added the example "functional vs conventional doctors".
ACCEPT  topic:alt_medicine.chiropractic  Covers the profession and practice business (Chiro Hustle 791 eps) and adds "getting adjusted", "neck cracking" and "spinal check".
ACCEPT  topic:alt_medicine.herbalism_traditional  Dropped "tinctures" (mostly a supplement dosage form) and "soursop tea" (4 eps). Added the `supplements.herbal_adaptogens` boundary, consistent with codebook rule 8.
MODIFY  topic:alt_medicine.energy_spiritual_healing  Added 528 Hz, Solfeggio, sound baths, EFT tapping (125 eps / 53 podcasts) and the PEMF boundary. Kept "exorcism as healing", which the report's row dropped: the qualifier already filters out the film senses.
ACCEPT  topic:alt_medicine.fringe_ingested_remedies  Added the parasite-cleanse co-label (611745/2) and routed methylene blue out to its existing homes.
ACCEPT  topic:alt_medicine.iv_ozone_therapies  The infused substance keeps its home (NAD IV, 139 eps / 36 podcasts). Oncology ozone and IV vitamin C go to `cancer_alt.natural_remedies`, whose definition already covers IV cancer remedies.
MODIFY  topic:alt_medicine.essential_oils  Accepted the exclusions for MLM-only and scent-ingredient mentions (921 of 1,760 eps are one MLM-satire promo), with the wording shortened.
ACCEPT  topic:detox.parasite_cleanses  "Horse dewormer" goes to `covid.treatments` (245 eps / 53 podcasts) and ivermectin or fenbendazole for cancer to `cancer_alt.repurposed_drugs`.
ACCEPT  topic:detox.binders_drainage  Lymphatic massage with no detox claim goes to `recovery.bodywork_compression` (about 290 segments, mostly without a detox claim).
ACCEPT  topic:detox.spike_protein_detox  Extended to spike protein from infection (189911/156) and added the nattokinase boundary to `supplements.other_compounds`, which already lists enzymes. Kept the "bromelain protocol" example.
ACCEPT  topic:detox.toxic_load_general  Added boundaries for addiction detox (181 eps / 72 podcasts) and digital or dopamine detox (230 / 71).
MODIFY  topic:environment.household_personal_care  Added cookware and clean beauty. I scoped the PFAS co-label to "PFAS discussed as an exposure" so that it agrees with the codebook note that a free-from attribute alone takes no environment subtopic. The ad for a non-toxic product still takes this subtopic, because it is the advertised product's own subject (codebook 4.1).
MODIFY  topic:environment.geoengineering  Requires health stakes or a stated spraying claim, and excludes chemtrails used as a stock conspiracy example (most of the 296 eps, 137 of them Rogan). Added the example "they're spraying us" from the narrative row.
ACCEPT  topic:environment.climate_heat  Climate politics without a health effect is excluded (7,429 eps against 415 that are health-linked). Added the boundary for one person's heat stroke.
ACCEPT  topic:environment.military_occupational (ADD)  784 eps / 123 podcasts on the combined query, with strong components (burn pits 220/55, Agent Orange 230/65, Camp Lejeune 105/40). The subject is distinct: exposure through service or work, plus a recognition and compensation politics (PACT Act) that `air_pollution`, `pesticides_herbicides` and `water_quality` do not capture. It is also relevant for contested-illness research (Gulf War illness). I added a boundary to `environment.indoor_air_mold` for asbestos at home.
ACCEPT  topic:radiation_light.wireless_emf  Havana syndrome and directed-energy claims had no home (233 eps / 42 podcasts). Added "non-native EMF".
ACCEPT  topic:radiation_light.emf_protection  A low- or zero-EMF selling point on another product does not take this subtopic (170 eps / 26 podcasts).
MODIFY  topic:radiation_light.sunlight_uv  Accepted the circadian boundary, which agrees with `sleep.circadian_light` (1,705 eps on "morning sunlight"). Dropped the spray-tan sentence: spray tans are not sun exposure, so they never belonged here. The non-health uses went to the codebook. Added "tanning beds" and "sun gazing".
ACCEPT  topic:skin_beauty.hair_loss_hair  Requires a hair-health claim for hair care. Dropped bare "shampoo" (4,680 eps, mostly cosmetic ad copy) and added regrowth and greying.
ACCEPT  topic:skin_beauty.cosmetic_procedures  Added breast implant illness and explant (72 eps / 31 podcasts, including a whole episode, 190157).
ACCEPT  topic:wellness.habits_behavior_change  Health habits only. Noom goes to `weight.weight_loss_methods`, which already lists it (599 of 3,700 eps are a Noom ad).
ACCEPT  topic:wellness.life_expectancy  Years of life lost or gained from a specific risk go to that risk's subtopic (18875/8 against 182869/3).
ACCEPT  topic:wellness.energy_fatigue  Requires a symptom or complaint. Generic ad energy puffery is excluded (about 9,200 eps / 243 podcasts). Dropped "boost your energy" as an example. Codebook 4.1 should state the same decision (see below).
REJECT  topic:skin_beauty.skincare (tallow food/skin note, a verdict line only)  The row already says "tallow skincare", and tallow eaten naturally goes to `food.fats_oils`. No change needed.
REJECT  topic:environment.pfas (cookware clarification, a verdict line only)  This is handled in the `household_personal_care` row, so `pfas` needs no change.

No REMOVE or MERGE was proposed in report 11. I agree: spike_protein_detox, fringe_ingested_remedies, artificial_light and ionizing_radiation are rare but important. The `topic:other` candidates (hypnotherapy, tattoo ink, noise pollution, terrain theory) stay unlabelled: none clears the bar, and each fits an existing label.

## Codebook

From report 09:

1. **Section 3, new paragraph on substances in everyday talk** (09 note 1). Substance use is health content when the window says something about the substance as a substance: an effect, a risk, an amount or pattern, dependence, quitting or sobriety, a policy, or a product sold for its effect. A third person's ongoing use, addiction or rehab is `passing`, and that includes reality-TV cast, who are real people. A single episode of being drunk or high told as a story, a drink, cigarette or joint as scenery, and coffee as an errand or taste are excluded. A drug crime named only as an event (a dealer, a deal gone wrong, a bust) or cartels as crime or immigration follow the violence rule. DUIs as legal events are excluded; drink-driving as a risk is `alcohol.drinking_culture`.
   - Evidence: 1–2 in 10 comedy hits are health content; 7,538 eps of drug-crime words.
   - Re-adjudicate gold items c178291w0010, c95062w0004 and c3505w0007, and the boat-strike item c154859w0023.
2. **Section 3, idioms and lookalikes** (09 note 2):
   - "addicted to" a non-substance;
   - "drunk on power", "high on life", "like he's on crack";
   - "alcoholic" as an adjective, simile or insult;
   - Coke (the soda), Molly (a name), Celsius (temperature), "non-alcoholic fatty liver", a play named "cocaine".
   - Evidence: 10945/4, 91961/4, 197083/2, 51828/4, 24318/10.
3. **Section 3, ad test for substance products** (09 note 3). Nicotine, cannabis or hemp-THC and kratom products pass as health products. Alcohol, coffee, energy drinks and alcohol alternatives pass only with a stated effect or a health-framed free-from claim. A product name ("Energizer") is not a stated effect.
   - Evidence: Red Bull Dragonberry (2,087 eps, no effect stated), Lucy (177 eps), hemp gummies (201756/4), hangover pills (322108/8).
   - Section 8 also needs a `product_type` decision for cannabis and hemp products: either widen `nicotine_or_tobacco`, or state that ingestible hemp products are `supplement`.
4. **Section 5.1, "General talk"** (09 note 4). Generic drug use with no drug named ("doing drugs", "drug problem", "substance abuse") is the bare `topic:drugs_addiction` (11,562 eps / 384 podcasts). Rule 6 applies to societal lists.
5. **Section 5.1, rule 8 pairings** (09 note 5):
   - non-medical use of a prescription drug keeps the drug's home (benzodiazepines → `mental.psychiatric_drugs`; opioid pills → `opioids_fentanyl`), except non-prescribed stimulants → `stimulants_illicit`;
   - add `addiction_recovery` or `alcohol_use_disorder` when dependence is discussed;
   - cannabis smoking → `cannabis`;
   - THC drinks → `cannabis` + `alcohol.alternatives`;
   - nicotine for Parkinson's → `nicotine_products` + `neuro.neurodegenerative` (24239/11).
6. **Section 5.1, rule 4, regulatory boilerplate in ads** (09 note 6). "FDA-approved", "compounded products the FDA does not approve" and "not evaluated by the FDA" in ad copy do not make `health_system.regulators`. "FDA-approved" offered as grounds is `evidence:strength_assertion`; a disclaimer is no signal. Evidence: 1,025 eps; Hims 318827/1, Hers 73652/6.
7. **Section 5.1, rule 3, health figures in politics** (09 note 7). A health figure's name, or an election campaign with no health position, is not health content. A nomination is `hhs_leadership` `passing` only when the health post is named. MAHA used as an adjective takes `maha_movement` only when the movement itself is characterized (330378/287). Evidence: 6 of 10 RFK samples.
8. **Analyst note** (09 note 8). DTC drug ads (Tremfya 2,838 eps / 35 podcasts) and McDonald's Red Bull reads will dominate `medications.other_drugs` and `stimulants.energy_drinks`. Report these labels split by `relevance`. This is not a labeler rule.
9. **Non-health insurance** (from the 09 costs_insurance row). Car, life and disability insurance as personal finance is not health content (NJM 162694/2; Ramsey Show 493 eps).

From report 11:

10. **Section 3, ads for cosmetic, hair-care and household products** (11 note 1). These are health content only with a skin, hair or health claim, or a toxicity or free-from claim. Seventh Generation's "nothing extra in the bottle" (773 Armchair eps) fails; "non-toxic makeup" (185654/2) passes.
11. **Section 3, cross-promos for other podcasts** (11 note 2). A promo that names a health product satirically or as a plot device is not a health ad (the MLM promo, 921 eps / 61 podcasts). A promo for a health show that describes its health content is at most `passing` with `advertisement`. The codebook should state this one way or the other.
12. **Section 4.1, contaminant and free-from attributes** (11 note 3). "PFAS and microplastic screening", "heavy metal limits", "BPA-free" and "zero EMF" on an unrelated product take `frame:toxin_purity` and no environment or radiation subtopic, unless the ad states the harm. This mirrors 5.2 implicature (a). Evidence: Momentus ad (156 eps), infrared-mat ad 26406/3.
13. **Section 4.1, energy and focus puffery** (11 note 4). "Clean energy, no crash, laser focus" names the product's purpose; it is not an outcome under rule 1. This matches the new `energy_fatigue` row. The same decision is needed for `cognition.focus_productivity`.
14. **Section 5.1, practitioner credentials** (11 note 5). A title in an intro, bio or referral (naturopath, functional medicine doctor, chiropractor, acupuncturist) is not a topic. Code the subtopic only when the practice or profession is discussed. Evidence: 190207/55; the Ruff Greens dog-food ad, 171 eps, which is also excluded as animal health.
15. **Section 3, word senses** (11 note 6):
    - "mold" as a verb;
    - Krystal Ball and "crystals";
    - "cupping" hands;
    - "breakout" in sports;
    - "fillers" in food ads;
    - "BBL" as slang;
    - "detox" in its addiction and digital senses;
    - "horse dewormer" meaning COVID ivermectin;
    - UV insect-trap ads (Zevo, 2,367 eps);
    - "low energy" said about performers;
    - Mercury the planet or singer;
    - spray tans and tanning salons (1,015 eps) with no health effect.
16. **Section 5.2, chemtrails as a stock example** (11 note 7). Naming chemtrails as a type of conspiracy belief is implicature exception (c). A joke whose point depends on the spraying proposition invokes `narrative:chemtrails`, usually `rebutted`, plus `environment.geoengineering` (71251/0).
17. **Rule 8, administration routes** (11 note 8). An administration route (IV, tincture, capsule) never replaces the substance's home: NAD IV → `iv_ozone_therapies` + `longevity.nad_sirtuins`; a herb tincture → `supplements.herbal_adaptogens`.
18. **Section 6, rubric example** (11 note 9). "I'm not against parasite cleanses per se, but…" (190413/66) is a qualified `asserted_or_endorsed`, not `questioned`.

## Cross-slice notes (not patched)

- `neurodevelopment.adhd`: add the reverse boundary, "Stimulants taken without a prescription go to `drugs_addiction.stimulants_illicit`." Today its example "Adderall" invites miscounting.
- `mental.psychiatric_drugs`: benzodiazepine misuse ("addicted to Xanax", 5545/3) stays here, plus `addiction_recovery` when dependence is discussed. Consider adding the example "Xanax bars".
- `health_system.pharma_industry`: add "Tobacco companies go to `stimulants.smoking`" to match the new smoking row.
- `recovery.bodywork_compression`: add "lymphatic massage" as an example, since `binders_drainage` now routes non-detox lymphatic massage there. The current definition says "used for recovery", which does not quite cover appearance or swelling. Consider widening it.
- `supplements.other_compounds`: add "nattokinase" as an example (routed there from `spike_protein_detox`).
- `covid.treatments`: add "horse dewormer" as an example. The narrative `ivermectin_covid` already mentions the "horse dewormer smear".
- `cognition.digital_media_brain`: add "digital detox" as an example. `neurochemistry_talk` already has "dopamine detox".
- `kidney_lung.lungs_breathing`: "black lung" and silicosis, when the disease is discussed, take it alongside `environment.military_occupational` (rule 1).
- `glp1.new_offlabel_uses` already lists "microdosing GLP-1", so it needs no change.
- `stress.mind_body` and `mental.therapy`: hypnotherapy (299 eps) has no stated home. It is probably `mental.therapy`; worth an example there.
- `peds.doping_sport`: already covers sport drug testing. It now receives that boundary from `drug_policy`.
- `metabolic.fatty_liver`: already covers NAFLD. The lookalike is noted in the codebook item above.
