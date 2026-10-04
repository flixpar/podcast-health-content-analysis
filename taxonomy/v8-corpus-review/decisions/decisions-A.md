# Group A decisions (reports 01 vaccines-infectious, 05 gut-immune-chronic)

Patch: `patch-A.jsonl`, with 34 changes, 2 adds, 0 removes and 1 parent edit. It validates with `apply_patches.py` (output `check-A.md`) and `tl.compile_taxonomy`. Every backticked reference resolves.

## EBV / "hidden infections" overlap (01 ADD vs 05 widening chronic_lyme)

One treatment for both reports: ADD `topic:chronic_complex.persistent_infections`. I rejected both original forms:
- 01's `infectious.chronic_hidden_infections` would put the subject in a parent defined by acute infection. It would also separate it from its narrative (`narrative:stealth_infections_root`, homed in `chronic_complex`) and from its closest sibling, `chronic_lyme`.
- 05's plan to widen `chronic_lyme` would make that ID misleading for EBV and mycoplasma, and would merge two subjects researchers will want to count separately.

The resulting pattern is consistent. An acute infection goes to `infectious.*` (`vector_borne`, or `other_infections` for mono or a shingles outbreak). A persistent or reactivated infection offered as the explanation for chronic illness goes to `chronic_complex.chronic_lyme` (Lyme) or `chronic_complex.persistent_infections` (everything else).

The topic is worded neutrally: infections "invoked to explain" chronic symptoms. The contested claim that they underlie most chronic disease stays on the narrative, and the row points to it.

Evidence:
- 01 found 436 episodes across 67 podcasts on the narrow query, and 893 episodes across 105 podcasts on the broad one.
- 05 found 372 episodes across 52 podcasts, with EBV alone at 326 episodes across 47 podcasts.

That clears the ADD bar. I also edited the `chronic_complex` parent definition so the parent covers persistent infections offered as a cause.

## Report 01: vaccines, covid, infectious

- MODIFY  topic:vaccines.covid_vaccines  Fixed the contradiction with `safety_injury`. A side effect now takes this label plus the condition's subtopic (myocarditis: `cardiovascular.heart_disease`); `safety_injury` is added only when vaccine injury itself is the subject (288 of 327 "vaccine injury" episodes are COVID contexts). Removed "approvals", which overlapped `development_approval`. Added the real slang ("the vax", "vaxxed and unvaxxed", "fully vaccinated") and kept "the jab" with a boxing caveat. The 2021-23 "bare 'the vaccine'" sentence went to the codebook because it is a reading rule.
- MODIFY  topic:vaccines.safety_injury  Made it "injury in general as a subject", including the vaccine-injured. A single named side effect of one vaccine takes that vaccine's subtopic and the condition's subtopic without this label. The example is now "vaccine package insert", because the bare form matched drug leaflets. The "Vair system" ASR variant went to the codebook, not the examples.
- MODIFY  topic:vaccines.childhood_schedule  Accepted the ACIP split rule and the country-schedule comparisons (385 episodes, 88 podcasts). Examples use the real phrasing. The ASR variants "ASAP" and "ACP" went to the codebook, because "ASAP" is too common to list as an example.
- ACCEPT  topic:vaccines.development_approval  Added the mRNA platform as such (203 episodes, 50 podcasts) and ACIP and VRBPAC as bodies. The name now includes "platforms".
- MODIFY  topic:vaccines.uptake_hesitancy  Accepted the anti-vaccine movement, access and coverage, and VFC. Also folded in 01's codebook note 6 (an outbreak blamed on falling vaccination takes the disease subtopic plus this label) as a boundary sentence. The "anti-vax as epithet" exclusion went to the codebook, because it is an insult-word scope rule.
- MODIFY  topic:covid.masks_distancing  Accepted: individual quarantine stays here, and "the quarantine" as the 2020 period moves to lockdowns. Renamed to "Masks, distancing & isolation".
- MODIFY  topic:covid.lockdowns_closures  Accepted "the quarantine" as a period, and health, social and economic costs. The time-marker exclusion went to the codebook.
- ACCEPT  topic:covid.origins  Kept the boundary that "China virus" used as a name is not origins talk (1,074 episodes), and pointed non-COVID gain-of-function work to `emerging_outbreaks`.
- ACCEPT  topic:infectious.emerging_outbreaks  Added biosecurity, bioweapons and non-COVID gain-of-function work (about 400 episodes with no COVID word). This gives `narrative:outbreak_engineered` a topic.
- ACCEPT  topic:infectious.foodborne  Added stomach bugs, norovirus and "stomach flu" (580 episodes, 134 podcasts, previously without a home).
- ACCEPT  topic:infectious.influenza_avian  Added a person's own flu and the 1918 flu, plus boundaries for "stomach flu" and "cold and flu season".
- ACCEPT  topic:infectious.antibiotics_resistance  Livestock and "raised without antibiotics" claims go to `food.organic_gmo` (about 1,056 episodes, mostly meat ads).
- MODIFY  topic:infectious.other_infections  Accepted: sepsis goes to `acute_care.emergency_critical_care`, historical epidemics are included, and yeast infections go to `womens`. Added a pointer to the new `chronic_complex.persistent_infections` and "mono" as an example.
- MODIFY  ADD infectious.chronic_hidden_infections  Merged with 05 into ADD `chronic_complex.persistent_infections` (see above).
- ACCEPT  (no removals proposed)  Every subtopic is well attested.

## Report 05: gut, immune, chronic_complex, genetics, oral, sensory

- ACCEPT  topic:gut.microbiome  Added fecal transplant (190 episodes, 50 podcasts) and routed the vaginal, oral and skin microbiomes and vagus-nerve devices elsewhere. The vaginal microbiome goes to `womens.gynecological_conditions`, the real ID that lists it.
- MODIFY  topic:gut.digestive_symptoms  Accepted digestion as a process and food sensitivities (1,222 episodes, 109 podcasts). Bile goes to `liver_gallbladder` and H. pylori to `gi_disease`, so no term has two homes. The diarrhea-joke exclusion went to the codebook.
- MODIFY  topic:gut.gi_disease  Accepted H. pylori, appendicitis (509 episodes) and hemorrhoids (638), the biologic co-label, and the rule that IBD and celiac take `immune.autoimmune` only "when discussed as autoimmune". Added a boundary sending stomach bugs to `infectious.foodborne`, to match 01's foodborne change.
- ACCEPT  topic:gut.candida_histamine  Histamine reactions attributed to mast cells go to `mcas_eds`, consistent with the `mcas_eds` change. The parasite-cleanse co-label is kept.
- MODIFY  topic:gut.liver_gallbladder  Accepted the GLP-1 pancreatitis boundary. Dropped the proposed example "hepatitis (as liver disease)", which collides with viral hepatitis in `infectious.other_infections`.
- MODIFY  topic:immune.immune_function  Accepted fever as an immune response (6,740 episodes, no home, and the home of `narrative:fever_suppression_harmful`) and the lymphatic system (954 episodes), with a pointer to `detox.binders_drainage`. Added a rule that a fever reported only as a symptom takes the illness's subtopic. Legal immunity, the metaphor use and pets went to the codebook, which already excludes animal health and idioms.
- ACCEPT  topic:immune.inflammation  Local tissue inflammation goes to the injury's or condition's subtopic. Dropped the narrative-worded example "inflammation is the root of all disease"; `narrative:inflammation_root_cause` carries that claim.
- MODIFY  topic:chronic_complex.chronic_lyme  Accepted that chronicity may be implied (relapse, long or repeated treatment), with a pointer to `infectious.vector_borne` for acute Lyme. Rejected the widening to EBV and stealth infections; those moved to the new `persistent_infections`.
- MODIFY  topic:chronic_complex.me_cfs  Accepted: "chronic fatigue" as a symptom or in an ad testimonial goes to `wellness.energy_fatigue`, and post-COVID cases add `covid.long_covid`. Dropped the odd example "a syndrome without an etiological agent".
- MODIFY  topic:chronic_complex.mold_illness  Accepted the `indoor_air_mold` co-label and the mold-allergy boundary. The home-insurance and joke exclusion went to the codebook.
- ACCEPT  topic:chronic_complex.mcas_eds  Covers histamine reactions attributed to mast cells (310 episodes, 59 podcasts), with the "hypermobile" training boundary.
- MODIFY  topic:chronic_complex.patient_experience  Accepted the requirement to be about seeking care or living with illness, and the routing of generic "chronic illness" to `wellness.chronic_disease_trends`. The non-medical "gaslit" exclusion went to the codebook.
- MODIFY  ADD chronic_complex.contested_syndromes  Accepted as ADD `chronic_complex.exposure_syndromes`, "Exposure & implant syndromes". The ID and name are more neutral and descriptive than "contested", and recognition status sits in the definition. Evidence: Havana syndrome 176 episodes / 37 podcasts; Gulf War illness and burn pits 243 / 59; breast implant illness 65 / 28; multiple chemical sensitivity and EMF hypersensitivity 94 / 25; Morgellons 26 / 4. That is about 550 episodes in all, they currently scatter across unrelated labels, and they matter for misinformation research (directed energy, EHS and 5G).
- MODIFY  topic:genetics.inheritance  Accepted risk variants (APOE4, BRCA; 440 episodes, 68 podcasts) and epigenetics as gene expression. Epigenetic clocks go to `longevity.biological_age`. Removed "blood type" from the examples. The crime, genealogy and athletic-"genetics" exclusions went to the codebook.
- MODIFY  topic:genetics.genetic_testing  Accepted the MTHFR tiebreak against `supplements.b_vitamins_methylation` and the DNA-based nutrition reports. The forensic and ancestry DNA exclusion went to the codebook.
- ACCEPT  topic:genetics.gene_therapy  "mRNA is gene therapy" (79 episodes, 27 podcasts) goes to `vaccines.covid_vaccines` plus `narrative:mrna_alters_dna`.
- ACCEPT  topic:oral.fluoride_products  Added drops and tablets.
- MODIFY  topic:oral.dental_procedures  Accepted holistic dentistry, veneers and whitening, bruxism and tongue-tie release. The report's infant-feeding co-label pointed to `pediatrics.infant_care`; I changed it to `pregnancy.infant_feeding`, which already lists tongue tie.
- ACCEPT  topic:oral.oral_hygiene  Added the oral-systemic link (171 episodes, 39 podcasts) and mouthwash and nitric oxide.
- ACCEPT  topic:sensory.vision  Added dry eye and eye drops (Systane ads appear in 1,647 episodes) and a co-label with `radiation_light.artificial_light` for screens.
- ACCEPT  topic:sensory.hearing  Added balance and vestibular problems (913 episodes, 155 podcasts). Renamed to "Hearing, ears & balance".
- ACCEPT  topic:sensory.smell_taste_ent  Added the COVID co-label (`covid.illness_severity`) and routed sinus infections to `infectious.respiratory_common`.
- ACCEPT  (no removals or merges proposed)  `pots_dysautonomia` and strict `chronic_lyme` are small but important.

Rejected outright: none. Partial rejections and redirections are noted above: the 01 placement, the 05 `chronic_lyme` widening, the `contested_syndromes` ID, and several scope sentences moved to the codebook.

## Codebook

All of these are judged sound.

1. **Section 3 Exclude, COVID as a time marker** (01 note 1). Exclude "COVID", "the pandemic", "lockdown" or "quarantine" named only as a period or backdrop. In a sample of 14 hits, 8 were this kind, out of about 43,000 episodes (ep 192241 seg 7, ep 79682 seg 8, ep 128502 seg 8). This is the largest over-labeling risk in either slice.
2. **Section 4.1, drug-ad safety boilerplate / ISI rule** (01 note 2 and 05 note 1, merged). The risk and side-effect boilerplate of a prescription-drug ad ("serious allergic reactions", "increased risk of infections", "tell your doctor if you need a vaccine", "live vaccines", tuberculosis testing, hepatitis B reactivation) adds no topic detections and no claims; code only the drug's indication and drug subtopic. Evidence: vaccine boilerplate in 2,904 episodes, infection boilerplate in 2,985, biologic ads in 3,230 episodes across 70 podcasts. The ISI is why `allerg*` hits top out on Ringer shows (322572 seg 0; 322662 seg 3; Nurtec 170566 seg 1).
3. **Section 4.1, benefit lists vs outcomes** (05 note 2). Proposed rule: three or more stated benefits in one read form a list and take only the product's subtopic; one or two benefits stated as outcomes are coded under co-label rule 1. Evidence: AG1, Armra and sauna reads (181278 seg 0; 13578 seg 3). Without this rule, `immune.immune_function` and `immune.inflammation` fire on a large share of supplement reads. Sound, but it changes the existing ad-outcome rule, so it needs the editor's sign-off.
4. **Section 3 Ads, calibration examples** (01 note 3). GoodRx "discounted flu shots" (971 episodes) takes `vaccines.flu_vaccine` as an advertisement. Meat-brand "never use antibiotics" (about 1,000 episodes) takes a food subtopic only. A water-filter read that lists fluoride among contaminants takes `environment.water_quality` only (05 note 6; 205791 seg 8).
5. **Section 3 Exclude, slice-specific idioms, insults and noise** (01 note 4 and 05 note 3, merged). The cases:
   - "anti-vax" or "anti-vaxxer" as an epithet for a person (314371 seg 0; 175707 seg 2);
   - "looks like mpox patient zero";
   - "like germ theory or something" as an analogy;
   - "long Trump";
   - "parasite" meaning a person or the film;
   - "contagious" laughter;
   - "seventy-two shots" fired;
   - legal "immunity" and political "autoimmune" (38256 seg 0);
   - household mold in home-insurance reads (79321 seg 2);
   - blood type, family history and 23andMe in crime or genealogy (22749 seg 6; 161942 seg 0);
   - "genetic freak" or "good genetics" as athletic talent (1,204 episodes);
   - the "epigenetic coach" show tagline (about 460 Niddam episodes);
   - "gaslit" outside medical care;
   - bodily-function jokes with no health point.
6. **Section 2, ASR and slang list** (01 note 5; 05 note 9 product misspellings):
   - ACIP heard as "ASAP" or "ACP" (167703 seg 0, 167680 seg 0);
   - VAERS heard as "Vair system" (931 seg 7);
   - MMR heard as "measles, momps and rebelt" (329107 seg 105);
   - "thimerisol";
   - "the vax", "vaxxed/unvaxed" and "fully vaxxed" in 2021-23 mean COVID vaccines, and a bare "the vaccine" in that period usually does, confirmed from the window;
   - "the jab" is often a boxing punch;
   - biologic names transcribed as "Tremphia", "Trumphia" and "Bimselix".
7. **Section 3 Violence, crime, war and death: historical epidemics** (01 note 7). Plague, smallpox and the 1918 flu in history and Bible shows (3,006 segments) follow the history default.
8. **Section 5.1 Unsettled facts: implied chronicity** (05 note 7). Lyme, EBV or mold told about a person is coded chronic when relapse, persistence or long-term treatment is stated (176586 seg 3); otherwise it takes the acute `infectious` subtopic as `passing` (659922 seg 3). This is partly encoded in the `chronic_lyme` row.
9. **Section 5.2, ad copy and inflammation_root_cause** (05 note 4). Say whether "75-90% of chronic issues are linked to stress and inflammation" (NeuroPod read, 185515 seg 1) invokes the narrative. I suggest yes at confidence about 0.6, given the magnitude-word rule.
10. **Section 5.2, fluoride jokes** (05 note 5). Example riffs: "calcifying our third eye" (23734 seg 5) and "makes the weed impotent" (322009 seg 9). They invoke `narrative:fluoride_mind_control` when the joke depends on the proposition, usually as `unclear` or `rebutted`.
11. **Section 5.5, military population** (05 note 8). Havana syndrome and burn-pit talk takes `population:military_veterans` only when the group's health as a group is discussed, not for one officer's case.
12. **Section 8, product types in this slice** (05 note 9). Biologics are `medication` and `advertised`. Systane drops are `medication`. Candid, Bite and Smile toothpaste are `personal_care_or_cosmetic`. ZBiotics and parasite-cleanse kits are `supplement`.

## Cross-slice notes

These touch other groups' labels and are not patched here:

- `narrative:stealth_infections_root` (narratives group): it could name its new topic home, `chronic_complex.persistent_infections`, and drop "Lyme co-infections" from its blamed pathogens, which overlaps `narrative:chronic_lyme_widespread`. No change is strictly needed.
- `food.organic_gmo`: add the example "raised without antibiotics" or "no antibiotics or hormones" to match the new `antibiotics_resistance` boundary.
- `acute_care.emergency_critical_care`: it already lists sepsis, so no change is needed. `other_infections` now defers to it.
- `supplements.b_vitamins_methylation`: mirror the MTHFR tiebreak. Gene or test talk goes to `genetics.genetic_testing`, methylated-vitamin advice goes here, and both apply when both occur. `narrative:mthfr_explains_illness` already exists.
- `pregnancy.infant_feeding`: it already lists tongue tie, and `oral.dental_procedures` now co-labels it.
- `radiation_light.wireless_emf`: could point EMF hypersensitivity as an illness to `chronic_complex.exposure_syndromes`.
- `skin_beauty.cosmetic_procedures` (breast implants): could point breast implant illness to `chronic_complex.exposure_syndromes`.
- `neuro.concussion_tbi`: Havana syndrome and directed-energy brain-injury talk co-labels `exposure_syndromes`.
- `womens.gynecological_conditions`: it already lists the vaginal microbiome, matching the `gut.microbiome` boundary.
- `health_system.global_health` vs `vaccines.efficacy_response` (Gavi): 01 flagged this overlap as low priority and I made no change.
- `wellness.energy_fatigue`: could add "chronic fatigue (as a symptom)", mirroring `me_cfs`.
