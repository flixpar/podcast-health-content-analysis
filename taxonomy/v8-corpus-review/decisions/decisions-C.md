# Group C decisions: reports 04 (metabolic, cardio) and 06 (cancer, neuro, acute)

Patch: `patch-C.jsonl`. It has 42 changes, 3 adds, 0 removes and 1 parent edit (`topic:acute_care`). It validates with `apply_patches.py` (output `check-C.md`) and with `compile_taxonomy`. All 53 backticked references resolve after the patch.

## Report 04: cardiovascular, metabolic, weight, GLP-1, endocrine, kidney/lung

ACCEPT  topic:cardiovascular.heart_disease  Atherosclerosis and ASCVD with no site named are common (907 episodes, 130 podcasts), and the anatomical rule cannot be applied to them. I dropped the proposed clause "heart attack as cause of death also takes death_dying", because it conflicts with the 06 death_dying rule adopted below (cause's subtopic only).
ACCEPT  topic:cardiovascular.blood_circulation  Narrowed to vessels and circulation, with nitric oxide added (748 episodes). Renamed "Blood vessels & circulation" now that clots have moved out. The ID is unchanged.
ACCEPT  topic:cardiovascular.clots_blood_disorders (ADD)  Clots appear in 1,819 episodes and 185 podcasts, 516 of them with vaccine terms. Anemia and blood disorders appear in 1,321 episodes and 167 podcasts. Both are distinct from "boosts circulation" copy and important for the vaccine-clot narrative. Modified: "blood thinners" is removed from the examples because `medications.other_drugs` already lists it, and the iron pointer now names the real ID `supplements.other_vitamins_minerals` (there is no iron subtopic).
ACCEPT  topic:cardiovascular.blood_pressure  Low BP occurs, BP-support supplement ads are frequent, and BP drugs appear in 785 episodes. Amlodipine is dropped from the examples for length.
MODIFY  topic:metabolic.insulin_glucose  I accept the content: hypoglycemia (842 episodes, 126 podcasts), metabolic flexibility (581 episodes, 49 podcasts) and the fructose/uric-acid account. The definition is compressed to two sentences, with a gout pointer to joints.
ACCEPT  topic:metabolic.fatty_liver  Uric acid moves out (its hits are gout in history shows or the metabolic account). MASLD and ALT are added.
ACCEPT  topic:weight.body_composition  Resolves the "slow metabolism" ambiguity. CICO (505 episodes, 65 podcasts) and metabolism-boost claims now have a home.
MODIFY  topic:weight.diet_pills_fat_burners  I accept the GLP-1-substitute co-label pointer and Contrave. The brand example "Lean supplement" is dropped, because a common word makes a poor example.
MODIFY  topic:glp1.use_results  I accept approved oral forms and celebrity speculation. Of the ASR variants, only "GLP one" (the spoken form) is kept in the examples; the others ("Ozempik", "Wagovi") go to the codebook ASR glossary.
ACCEPT  topic:glp1.access_compounding  Telehealth ads that state results now take `use_results` as well. The old "takes this alone" contradicted the ad-outcome rule.
MODIFY  topic:glp1.new_offlabel_uses  I accept the move of approved oral forms to `use_results` (1,454 of 1,606 matching episodes are Hers Wegovy-pill reads). "Orforglipron (pre-approval)" is dropped from the examples because its approval status changes over time; the definition's "not yet approved" carries the rule.
ACCEPT  topic:glp1.natural_alternatives  The real phrasing is "GLP-1 booster" or "natural GLP-1". The Akkermansia example, which pulled in plain microbiome talk, is removed, and companion products are excluded.
MODIFY  topic:endocrine.cortisol_adrenal  Accepted, but the stress pointer is made specific: `stress.stress_burnout` rather than the bare `stress`.
ACCEPT  topic:endocrine.other_hormones  "Love hormone" oxytocin (1,277 episodes, led by relationship shows) goes to `cognition.neurochemistry_talk`.
ACCEPT  topic:kidney_lung.kidney_urinary  States the UTI boundary with `infectious.other_infections` (the Wisp ad runs in 324 Giggly Squad episodes) and adds the `mens.prostate` pointer.

## Report 06: cancer, cancer_alt, neuro, dementia_ageing, musculoskeletal, acute_care, procedures

ACCEPT  topic:cancer.causes_rates  Prevention phrasing appears in 958 episodes and 104 podcasts. Adds the boundary with `cancer_alt`: risk in people without cancer goes here, treatment of an existing cancer goes there.
MODIFY  topic:cancer.screening_diagnosis  Cologuard and stool DNA tests are added (2,248 episodes). Full-body MRI is NOT added as an example, because `self_tracking.body_scans` already owns Prenuvo and full-body MRI. Instead there is a pointer: a scan takes body_scans, plus this subtopic when it is discussed as cancer screening.
ACCEPT  topic:cancer.colorectal_cancer (ADD)  About 810 non-ad episodes in 146 podcasts, comparable to the skin and prostate cancer subtopics. It carries the early-onset storyline, and the 2,248 Cologuard-ad episodes need a type home.
ACCEPT  topic:cancer.prostate_cancer  Bare "PSA" is mostly public service announcements or card grading, so the example becomes "PSA test" or "PSA level".
ACCEPT  topic:cancer.other_specific_cancers  Colon cancer leaves for the new subtopic. Glioblastoma, ovarian cancer and myeloma are added.
ACCEPT  topic:cancer.conventional_treatment  Cancer vaccines, supportive care (cold cap), cancer centers, and chemo for non-cancer disease are now handled.
ACCEPT  topic:cancer_alt.repurposed_drugs  The definition now requires cancer to be named. Ivermectin/mebendazole pharmacy ads go to `medications.repurposed_offlabel`, and fenbendazole inside parasite cleanses goes to `detox.parasite_cleanses`.
MODIFY  topic:cancer_alt.natural_remedies  I accept the mind/faith-healing routing (the existing subtopics plus the bare `cancer_alt` parent) and the ASR-aware examples. The ASR spellings ("vitamin B seventeen", "sour sap") go to the codebook glossary rather than the examples, and "cannabis oil" is kept.
ACCEPT  topic:cancer_alt.clinics_protocols  Hyperthermia now counts only as a cancer therapy; heat illness goes to poisoning_environmental_injury. Hope4Cancer is added.
ACCEPT  topic:cancer_alt.refusing_standard_care  Adds real phrasing and the false-friend boundary: "no chemo needed" judged by the oncologist is conventional care.
ACCEPT  topic:cancer_alt.integrative_adjuncts  A conventional drug added to chemo, and supportive care, go to conventional_treatment. This fixes the Cancer Research UK ad, which accounts for 86 of 216 episodes.
MODIFY  topic:neuro.concussion_tbi  Sport concussions take this subtopic only (750 "concussion protocol" episodes). The second boundary is reworded to "a brain injury ... rather than trauma_fractures for that injury", so that a crash with both a fracture and a TBI can still take both.
MODIFY  topic:neuro.headache_migraine  Accepted, except that the idiom sentence ("a headache meaning a hassle") is moved to the codebook, since scope rules stay out of the label set. Nurtec is added as an example.
MODIFY  topic:neuro.nerve_spinal  Sleep paralysis goes to the `sleep` parent, and the Neuralink example becomes "Neuralink for paralysis". The "paralyzed by fear" idiom and the rule that BCI-as-tech is not health content go to the codebook.
ACCEPT  topic:neuro.other_neurological  Tourette's is the most frequent named item, and tinnitus goes to `sensory.hearing`. "Tics in adults" is widened to "tics" (rule 2 handles children).
MODIFY  topic:dementia_ageing.dementia_alzheimers  "Cognitive decline" meaning dementia risk now belongs here, and the leader-sharpness boundary with cognitive_ageing is stated. The sentence pointing at the codebook's unsettled-facts rule is left out of the row and recorded under Codebook instead.
ACCEPT  topic:dementia_ageing.cognitive_ageing  Superagers are added, and political sharpness debate with no dementia claim goes here.
ACCEPT  topic:dementia_ageing.elder_care  The bare "caregiving" example is replaced, because it matched child caregivers. Falls and long-term care are added.
ACCEPT  topic:musculoskeletal.joints_arthritis  States the boundary with `immune.autoimmune` for rheumatoid and psoriatic arthritis (1,010 episodes, 123 podcasts).
MODIFY  topic:musculoskeletal.sports_injuries  "An athlete's unspecified injury" is removed, the definition now requires named injuries, and there is a concussion pointer. The "injured/out/questionable is not health content" sentence is a scope rule and goes to the codebook. Evidence: 8,887 episodes dominated by fantasy football, mostly bare mentions.
ACCEPT  topic:musculoskeletal.chronic_pain  Mind-body pain (132 episodes, 60 podcasts) is added, with a fibromyalgia pointer.
ACCEPT  topic:musculoskeletal.rehab_manual_therapy  Pelvic-floor PT goes to `womens.pelvic_floor`. The example "rehab" becomes "rehab after surgery" to avoid confusion with addiction rehab.
REJECT  topic:acute_care.crime_war_injuries (ADD)  This is a scope rule dressed as a label. The report's own rationale is that the subtopic exists so analysis can exclude it, and the brief puts crime narration in the codebook. Forensic narration (16,519 episodes, 466 podcasts) has no value for health-misinformation research, and labeling it would spend detections and coder effort on content that is filtered out anyway. It is replaced by a tightened section 3 rule (see Codebook, item C1) plus the `acute_care` parent edit.
MODIFY  topic:acute_care.trauma_fractures  The crime clause is removed and combat wounds and amputation are added, as proposed. The reference to the rejected subtopic is replaced by "a wound told only as part of a crime or war story is not this subtopic". "Also takes death_dying" is dropped to match the new death_dying rule. A brain-injury pointer to concussion_tbi is added.
MODIFY  topic:acute_care.violence_abuse  I accept the pattern/survivor scope and the exclusion of allegations as news. Evidence: 12,334 episodes led by Megyn Kelly, Shapiro, MeidasTouch and Walsh, with allegation talk. The pointer to the crime rule is now stated in the row as a boundary rather than as a nonexistent label.
ACCEPT  topic:acute_care.wounds_first_aid  CPR now has a single home: bystander CPR here, hospital resuscitation in emergency_critical_care. Sport stitches go to sports_injuries.
MODIFY  topic:acute_care.poisoning_environmental_injury  The food-poisoning boundary and the hyperthermia example are accepted. "Poisoning of pets is excluded" is dropped, because the codebook's animal-health exclusion already covers it.
ACCEPT  topic:acute_care.death_dying  "MAID" becomes "medical assistance in dying" (bare "maid" collides with "maid of honor"). The bare example "autopsy" is replaced by "autopsy findings of disease, overdose or neglect". The rule that a biographical death takes the cause's subtopic alone is adopted, which keeps "died of cancer" (6,307 episodes) out of this label. This replaces 04's suggestion to add death_dying for a heart attack as cause of death.
MODIFY  topic:acute_care.near_death_experiences (ADD)  Accepted as an ADD. The exact phrase appears in 1,084 episodes across 166 podcasts, about half of them real accounts (Mayim Bialik 93, Attia, Shawn Ryan). It is a contested claims area with no current home, and it would mix badly with hospice care inside death_dying. The definition was tightened slightly.
ACCEPT  topic:procedures.surgery_hospital  A procedure named only as the treatment of a condition takes that condition's subtopic (21,279 episodes dominated by cosmetic, gender and sports surgery). The "knee surgery" example is dropped for consistency.
MODIFY  topic:procedures.imaging_diagnostics  I accept the boundaries for prenatal ultrasound and Preborn ads (990 episodes) and for MRI as a research method. I added an elective full-body scan pointer to `self_tracking.body_scans`.
PARENT  topic:acute_care  (Editor's op, required by the C1 decision.) The parent definition said crime injuries take trauma_fractures and death_dying. It now states the tightened rule. **This must ship together with the codebook section 3 edit (C1)**; otherwise the label set and codebook contradict each other.

## Codebook

Sound suggestions, with their source and evidence:

**C1. Section 3, "Violence, crime, war and death": replace the paragraph** (06 note 1; the reason crime_war_injuries was rejected). Suggested text:
> In true crime, news, war or history, a killing, wound, method of death, cause of death, autopsy or casualty count told as part of the story is not health content: "shot in the back of the head", "29 stab wounds", "raped and strangled", "the autopsy confirmed". It becomes health content when the medical side is itself described: medical care, survival, recovery or disability ("hospitalized for weeks", "lost the use of his legs"); a medical explanation of how the injury harms or kills; or an autopsy finding of disease, overdose, poisoning, starvation or neglect. Then label `acute_care.trauma_fractures`, `acute_care.emergency_critical_care`, `acute_care.death_dying` or the condition's own subtopic. A sexual assault or rape told as an event in a crime story follows the same test; it is not "sexual assault as the subject". Use `acute_care.violence_abuse` when violence or abuse is discussed as a pattern, risk, prevention or public-health issue, or for a survivor's harm and recovery. An allegation, charge or trial of a named person discussed as news or legal process is not health content. Fiction, legend and scripture follow the same test.

Evidence: forensic vocabulary appears in 16,519 episodes across 466 podcasts (48 Hours, Morbid, MFM, Dateline, Crime Junkie). The ambiguous cases this resolves are Casefile 23838/3 and Morbid 5322/3. The positive cases it keeps are Fresh Air 25321/0 (starvation in jail), Breaking Points 330416/158 (Gaza hospital injuries) and the war-starvation reports. Also update section 10 ("bare crime words") to read "crime narration, including wounds and causes of death told as story".

**C2. Section 3: a sports-injury parallel** (06 note 2):
> An athlete named as injured, out, questionable or banged up, with no body part, diagnosis or treatment, is not health content. A named injury is one `passing` detection, and an injury-report list in one stretch is one detection with the named injuries' subtopics. Sports concussions take `neuro.concussion_tbi` only.

Evidence: 8,887 episodes (Fantasy Footballers 1,383, PMT 1,042); "he's had bad luck with injuries" (79995/6).

**C3. Section 3 idiom list additions** (06 note 3, 04 note 4):
- "a headache" meaning a hassle (bare "headache" appears in 10,399 episodes versus 3,251 tight);
- "paralyzed" by fear;
- "stroke of luck";
- "searches and seizures" and asset seizures;
- "drowning in" work;
- "transplant" meaning relocate;
- "first aid" or "CPR" for non-medical problems;
- "a cancer on…";
- Cancer the zodiac sign (about 694 episodes together with the idiom);
- "concussion grenade";
- "near-death experience" meaning a close call;
- hyperbolic deaths ("work until you die of a heart attack at 33", 629264/1);
- "gets my blood pressure going" (194630/11);
- brain-computer interfaces discussed only as technology.

**C4. Section 4.1 / 3: drug-ad mandated safety information** (04 note 1). Adverse effects listed in a drug ad's required safety statement do not get their own topic detections; the ad takes the drug's subject and its claimed benefit. Evidence: Nurtec's "High blood pressure and Raynaud's" makes Hidden Brain the top "blood pressure" podcast (515 episodes); Rexulti's list would add three metabolic and cardio topics.

**C5. Section 3, ad test: eligibility lists in non-health ads fail the test** (04 note 2). Example: SelectQuote's "Have high blood pressure, diabetes, or heart disease?" (frequent on MeidasTouch). No health product is sold and no health effect is claimed.

**C6. Section 5.1, a real person's cancer or death** (06 note 5, 04 note 4, reconciled). A real person's cancer or death named as a biographical fact ("died of cancer", "beat cancer", "died of a heart attack", "died from an aneurysm") is one `passing` detection of the cause's subtopic (bare `topic:cancer` when no type is named). It does not add `acute_care.death_dying` unless dying or end-of-life care is discussed. Evidence: 6,307 episodes across 324 podcasts of untyped biographical cancer. This matches the new death_dying row.

**C7. Section 5.1, "Unsettled facts about a person": extend to dementia and GLP-1 speculation** (06 note 4, 04 note 8):
- A named public figure said to have dementia or "cognitive decline", with no diagnosis in the window, takes `dementia_ageing.dementia_alzheimers` (or `cognitive_ageing` when only sharpness is debated) at confidence 0.6 or less, with "unconfirmed" in the summary, when symptoms or fitness are argued for at least a sentence. A one-word jab ("it's just dementia") is an insult and is excluded. Evidence: IHIP 464 and MeidasTouch 265 episodes.
- "Is she on Ozempic" names the drug, so it takes `glp1.use_results` as `passing`.

**C8. Section 5.1, co-labeling rule 1: procedures** (06 note 7). A procedure named only as the treatment of a condition with its own subtopic takes that subtopic, not also `procedures.surgery_hospital`; add surgery_hospital when the operation, recovery or stay is itself discussed. This matches the new surgery_hospital row.

**C9. Section 5.1, "General talk" additions** (04 note 5): "cortisol" used as a word for stress goes to `stress.stress_burnout`, and oxytocin as "the love hormone" goes to `cognition.neurochemistry_talk`.

**C10. Section 4.1, worked examples for high-volume ad reads** (06 note 6, 04 note 7):

| Read | Episodes | Coding |
| --- | --- | --- |
| Cologuard | 2,248 | `cancer.screening_diagnosis` + `cancer.colorectal_cancer` |
| MSK and Cancer Research UK | — | `cancer.conventional_treatment`, plus the named cancer when a result is stated |
| Preborn ultrasound appeals | 990 | `fertility.abortion`, not imaging |
| Relief Factor | 603 | the product's subject (`musculoskeletal.chronic_pain` + supplement subtopic); the list rule applies to the joints |
| Nurtec | — | `neuro.headache_migraine` |
| Ivermectin/mebendazole pharmacy kits | — | `medications.repurposed_offlabel`, never `cancer_alt` |
| Lean weight-loss supplement | — | `weight.diet_pills_fat_burners` + `glp1.natural_alternatives` + `metabolic.insulin_glucose` |
| Hers/Ro GLP-1 telehealth | — | `glp1.access_compounding`, plus `use_results` when a result is stated |

**C11. Section 2 / prompt glossary of ASR forms** (04 note 6, 06 note 9):

| ASR form | Meaning |
| --- | --- |
| "GLP one", "Ozempik", "Wagovi/Wegovi/Wigovi", "Monjaro", "semi glutide", "terzepatide" | GLP-1 drugs |
| "Lp little a" | Lp(a) |
| "uric acid A", "urate and A", "urea thion A" | urolithin A, not uric acid |
| Coligar, Colgard, ColiGuard | Cologuard |
| "Nertech ODT Remajipant" | Nurtec ODT rimegepant |
| "sour sap" | soursop |
| "vitamin B seventeen" | laetrile/B17 |
| "Hope for Cancer" | Hope4Cancer |
| "maid" | MAID: ambiguous, so code only from context |

A product name repaired from these forms takes confidence 0.7 or less.

**C12. "Died suddenly"** (04 note 6). It carries the vaccine narrative only as the coined term (the film or account, or a "died suddenly" trend). As an ordinary obituary phrase it carries nothing (1135310/1). This is worth one example in section 5.2.

**C13. Analysis docs, not the prompt** (04 note 3). Dynamic ad insertion puts 2025–26 GLP-1 ads into back-catalogue episodes (a 2018 Happier episode carries a 2026 Hers read). GLP-1 trend analysis must split out `relevance: advertisement` and must not date ads by episode date.

## Cross-slice notes

These touch labels outside my reports' slices. I did not patch them.

- `cognition.neurochemistry_talk`: its definition or examples should name oxytocin as "love hormone", to match the new `endocrine.other_hormones` pointer.
- `self_tracking.body_scans`: could note "adding `cancer.screening_diagnosis` when discussed as cancer screening", to mirror the new screening row.
- `medications.other_drugs` lists "blood thinners". Under rule 1, blood thinners for clots should co-label with the new `cardiovascular.clots_blood_disorders`; consider "blood thinners (also the clot subtopic when clots are discussed)".
- `infectious.other_infections` already lists "UTI as infection", which is consistent with the new kidney_urinary boundary. No change is needed.
- `sleep` has no subtopic for sleep paralysis (325 episodes, 61 podcasts, mostly Morbid and Last Podcast). The bare parent is used for now; the sleep reviewer could add it to an examples list.
- `pregnancy.pregnancy_health` could list "prenatal ultrasound" to receive the imaging boundary.
- `narrative:chemo_does_more_harm`: the chemo-damages-mitochondria elaboration (Habits & Hustle 14525/1) should be one of its examples. "Emotions cause or the mind cures cancer" (Dispenza; about 83 podcasts on a noisy query) is a candidate narrative for the narrative reviewers, which 06 deliberately did not propose.
- `musculoskeletal.bone_health`: bone density used as a sex difference in trans-athlete arguments is gender content (06 note). This is a question for the gender reviewers.
- The new `cancer.colorectal_cancer` is relevant to `narrative:cancer_epidemic_young`, whose early-onset storyline is mostly told through colorectal cancer. No change is needed there.
