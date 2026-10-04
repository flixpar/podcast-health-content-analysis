# Cancer, alternative cancer care, neuro, dementia and ageing, musculoskeletal, acute care, procedures: corpus review

Slice: `topic:cancer`, `topic:cancer_alt`, `topic:neuro`, `topic:dementia_ageing`,
`topic:musculoskeletal`, `topic:acute_care`, `topic:procedures` and their subtopics.

Method note: all searches used `/mnt/data2/podcast-data/corpus-text/cq.py`, the tool the
brief specifies. The permission classifier blocked the NVMe copy
(`/mnt/internal/felix/podcast-corpus-text/cq.py`) that the coordinator suggested, and an
agent message cannot authorize it, so I did not retry it. All counts below are
regex hits: segments / episodes / podcasts out of about 145,600 episodes. Unless a
count is called "tight", the query is noisy and the count is an upper bound. I read
samples for every count.

## Summary

- **The section 3 crime rule would make injury and death the most frequent health topic in the corpus.**
  Forensic injury and death vocabulary ("shot in the", "stab wounds", "blunt force",
  "strangled", "cause of death", "autopsy", "bled out") appears in **16,519 episodes
  across 466 podcasts**, led by 48 Hours, Morbid, My Favorite Murder, Dateline,
  Last Podcast, Crime Junkie and Snapped. Applied as written, nearly every true-crime
  episode gets `acute_care.trauma_fractures` and `acute_care.death_dying`, so those two
  subtopics would mostly count crime narration rather than injury or end-of-life health
  talk. I propose a separate subtopic for injuries and deaths told as part of a crime,
  war or news story. It keeps coding consistent, stays easy to filter out, and keeps
  `trauma_fractures`/`death_dying` meaningful. Sexual-assault allegations in political
  and celebrity news need the same treatment.
- **Sports injury reports have the same volume problem.** Injury vocabulary hits 8,887
  episodes. Fantasy Footballers (1,383), Pardon My Take (1,042), Bill Simmons (800) and
  Ringer Fantasy Football (641) dominate. `sports_injuries` currently includes "an
  athlete's unspecified injury", so "he's had bad luck with injuries" counts as health
  content. Bare "injured/injury" in sports talk should be treated like bare "murdered".
  Sports concussions (750 episodes with "concussion protocol / out with a concussion")
  need an explicit home: `neuro.concussion_tbi`, not also `sports_injuries`.
- **Most cancer mentions are a person's unspecified cancer** ("died of cancer", "beat
  cancer", "diagnosed with cancer"; 6,307 episodes, 324 podcasts). No rule names the
  bare parent for this. The codebook should say it is a bare `topic:cancer` passing
  detection, with no `death_dying` unless dying itself is discussed.
- **Colorectal cancer deserves its own subtopic.** It has about 810 non-ad episodes
  across 146 podcasts (comparable to skin and prostate cancer), and early-onset
  colorectal cancer is a recurring storyline. A Cologuard read also runs in **2,248
  episodes** (2,194 of them Watch What Crappens), the largest single block of cancer
  content in the corpus. All of it is advertisement-relevance colorectal screening.
- **Recurring health ads in non-health shows** need worked examples because each runs
  in hundreds of episodes:
  - Cologuard;
  - Memorial Sloan Kettering ads (The Daily, 214 episodes);
  - Cancer Research UK ads (The Rest Is History, 86 episodes);
  - Preborn "free ultrasound" ads (990 episodes, 45 podcasts; Charlie Kirk 529,
    Candace 174);
  - Relief Factor joint-pain ads (603 episodes);
  - Nurtec migraine ads (Hidden Brain 509, transcribed "Nertech ODT Remajipant");
  - ivermectin/mebendazole pharmacy ads (Megyn Kelly, Bongino) that never mention cancer.
- **`cancer_alt` labels are findable but rare** (roughly 60 to 600 episodes each), and
  several boundaries leak:
  - ivermectin ads with no cancer mention;
  - fenbendazole inside parasite cleanses;
  - "hyperthermia" that is usually heat illness;
  - charity-ad copy ("another drug alongside chemotherapy") that looks like an
    integrative add-on;
  - "no chemo needed" said by an oncologist, which looks like refusal.

  Mind and faith healing of cancer (Dispenza, prayer) has no home.
- **Politicians' alleged dementia is a large block of dementia hits.** IHIP News (464
  episodes) and MeidasTouch (265) are among the top shows for dementia terms. The
  codebook needs a rule that separates speculation about a named leader's cognitive
  health (the existing "unsettled facts" rule, confidence 0.6 or less) from the insult
  use ("it's just dementia"). It also needs a rule for "cognitive decline", which
  speakers use both for dementia risk and for normal ageing.
- **Near-death experiences are a recurring, contested subject with no home** ("near-death
  experience" in 1,084 episodes across 166 podcasts; Mayim Bialik alone 93). About
  half the uses are true reports of clinical death or out-of-body experiences; the rest
  are loose "close call" usage. I propose a subtopic under `acute_care`.
- **Smaller boundary fixes:**
  - inflammatory arthritis goes to `immune.autoimmune`;
  - fibromyalgia goes to `chronic_complex.fibromyalgia`;
  - pelvic-floor PT goes to `womens.pelvic_floor`;
  - prenatal ultrasound and MRI-as-research-method are not `imaging_diagnostics`;
  - food poisoning goes to `infectious.foodborne`;
  - bystander CPR has one home, not two;
  - a surgery named only as the treatment of a condition takes the condition's subtopic.
- **Idioms are the main source of noise and should be listed in section 3:**
  - "a headache" meaning a hassle;
  - "paralyzed" by fear;
  - "stroke of luck";
  - "searches and seizures";
  - "drowning in";
  - "transplant" meaning relocate;
  - "first aid" for non-medical problems;
  - "a cancer on";
  - Cancer the zodiac sign;
  - "maid" (the ASR form of MAID) colliding with "maid of honor".

## Label-by-label findings

### Cancer

**Parent and overall volume.** `\bcancers?\b` gives 47,704 / 27,746 / 465. Watch What Crappens (2,453 episodes) leads because of the Cologuard read.
- Personal or biographical cancer with no type: `(diagnosed with cancer|died (of|from) cancer|battl(e|ing) (with )?cancer|beat cancer|cancer survivor|had cancer|has cancer|got cancer|...|stage (one..four))` gives 7,765 / **6,307 / 324**.
- This is the most common kind of cancer content in the corpus. True-crime and comedy shows contribute a lot of it:
  - Morbid 1249/5: "Janice's mother Isabel actually died from cancer";
  - Ramsey 58022/6: "My baby's got cancer".
- None of this fits a subtopic, so it goes to the bare parent. The codebook should say so (see notes).
- Idiom and astrology noise: "a cancer on…", "I'm a Cancer", "cancer season" gives 694 episodes / 155 podcasts.
  - PBD 205594/5: "we are a cancer, and there's no cure".

**`cancer.causes_rates`.** Query `carcinogen|causes? cancer|cancer rates?|cancer risk|early-onset…|cancer in young` gives 3,315 / 2,505 / 169. Verdict: **needs a definition change (prevention).**
- Real use is mostly "X causes cancer" about a named exposure, which co-labels with the exposure's subtopic:
  - Determined Society 28270/3: "nail gel dip … apparently that causes cancer now";
  - Pivot 93589/4: "marijuana doesn't cause cancer. Alcohol does";
  - Attia 181578/14: "no data to support that [testosterone] causes cancer".
- Prevention is a second large use that the definition does not name. `prevent(s|ing) cancer|cancer prevention|anti-cancer|reduces … cancer|cancer-fighting|fights cancer` gives 958 episodes / 104 podcasts:
  - SYSK 23692/5: "Allicin, the cancer-fighting enzyme found in garlic";
  - Axe 174954/3: episode titled "How to Prevent CANCER: 15 Proven Ways";
  - Thyroid Fixer 190462/86: "statin has been known to be anti-cancer".
- Coders will hesitate between this label and `cancer_alt.natural_remedies` when a food "fights cancer". Proposed rule: lowering risk in people without cancer goes here; treating an existing cancer goes to `cancer_alt`.
- "Feeds cancer" claims made about healthy people also belong here:
  - Hyman 182737/5: "IGF-1 … feeds cancer cells. So I would definitely eliminate dairy".
- Early-onset cancer as an explicit phrase is rare: 54 episodes / 27 podcasts. The rise is usually told through colorectal cancer (see below).

**`cancer.screening_diagnosis`.** Query `mammogram|colonoscopy|PSA test|pap smear|galleri|liquid biopsy|cancer screening|full-body MRI|prenuvo|ezra` gives 3,996 / 3,077 / 219. Verdict: **examples change.**
- The Daily (603 episodes) leads because of a Planned Parenthood ad ("funds birth control, cancer screenings").
- Boring History (107) has a full-body-scan ad ("Know what lies beneath").
- Cologuard and stool tests are the biggest screening content of all: `colo?[gq]u?ard|coli ?gu?ard|screen for colon cancer` gives 2,911 / **2,248 / 19**. ASR spells it Coligar, Colgard, ColiGuard and Coligard (WWC 96571/0, 96553/5, 91704/4).
- Add Cologuard and full-body MRI (Prenuvo, Ezra) to the examples. Attia has a full episode on full-body MRI as cancer screening (181577).

**`cancer.conventional_treatment`.** Query `chemo|chemotherapy|radiation therapy|immunotherapy|mastectomy|oncologist|in remission|CAR-T|keytruda` gives 5,975 / 4,343 / 261. Verdict: **fine, with a small examples change.**
- Traps to note:
  - chemo for a dog is veterinary and excluded (Ramsey 1135945/3: "ten thousand dollars on chemo for the German Shepherd");
  - chemo for non-cancer disease (Dateline 2225/0: "Lupus, chemotherapy involved in that") takes the disease's topic.
- Supportive care during treatment is common and fits under "survivorship":
  - Wiser Than Me 611525/0: "The cold cap is something you can do to keep you from losing hair during chemo".
- Cancer vaccines and mRNA cancer therapy are rare but politically salient: 70 episodes / 38 podcasts (Rogan, Megyn Kelly, IHIP).
- Cancer-center brand ads fall here with `relevance: advertisement`. `(md anderson|sloan.kettering|city of hope|cancer treatment centers…|dana.farber)` gives 551 episodes, The Daily 214:
  - Daily 1140195/2: "This podcast is supported by Memorial Sloan Kettering Cancer Center … treatment for metastatic triple-negative breast cancer".

**`cancer.breast_cancer`.** `breast cancer|brca|breast density` gives 4,951 / 3,013 / 207. Verdict: **fine.**
- Ads inflate the count:
  - MSK triple-negative ad in The Daily;
  - Pardon My Take 128290/15: "This Breast Cancer Awareness Month, join Touch, the Black Breast Cancer Alliance".

**`cancer.skin_cancer`.** `melanoma|basal cell|squamous cell|skin cancer` gives 1,379 / 968 / 149. Verdict: **fine.**

**`cancer.prostate_cancer`.** Verdict: **fine, but the bare "PSA" example is misleading.**
- Bare `\bpsa\b` means public service announcement or PSA card grading in most hits (Trading Cards podcast 70 episodes, Pardon My Take 267).
- With the term restricted (`prostate cancer|gleason|PSA test/level/score|prostate-specific antigen`): 1,698 / 1,292 / 173.
- Change the example "PSA" to "PSA test".

**`cancer.other_specific_cancers`.** Verdict: **split out colorectal; refresh the examples.**
- Episode counts by type:
  - colon/colorectal/rectal/bowel: 3,208, mostly the Cologuard ad; the non-ad colorectal query gives **810 episodes / 146 podcasts**;
  - brain tumour/glioblastoma: 1,529;
  - lung: 1,250;
  - leukemia: 1,025;
  - pancreatic: 736;
  - lymphoma: 569;
  - thyroid: 418;
  - ovarian: 338;
  - cervical: 225.
- Without colorectal, the remaining types still total about 7,000 episodes, more than breast cancer. Colorectal on its own is comparable to skin (968) and prostate (1,292).
- Colorectal is also the vehicle for the early-onset story:
  - DOAC 19824/1: "four times more likely to be diagnosed with rectal cancer during their lifetime than my parents were";
  - Niddam 428521/140: "Every other cancer is on the decline except for colorectal cancer";
  - Brecka 177075/0: ultra-processed foods "linked to higher risks of … colorectal cancer, which is on the rise".

### Alternative cancer treatments

**`cancer_alt.repurposed_drugs`.** Query `fenbendazole|fenben|mebendazole|ivermectin…cancer|joe tippens|metformin…cancer|dipyridamole|repurposed drugs` gives 170 / **130 / 42**. Verdict: **needs a definition change.**
- Many hits are ads for ivermectin/mebendazole "preparedness" kits that never mention cancer:
  - Megyn Kelly 4077/1: "ivermectin and mebendazole are 25% off … code MEGAN10";
  - Bongino 656001/0: "Get 10 off ivermectin, hydroxychloroquine, mebendazole".
  These should take `medications.repurposed_offlabel`, not `cancer_alt`.
- Fenbendazole also appears inside parasite cleanses (Brecka 177028/7: "Para One … mixed with Fenbendazole or Ivermectin"). That is `detox.parasite_cleanses`.
- True cancer use:
  - Culture Apothecary 185726/6: "if ivermectin is the cure for cancer, they will never say" (also takes `narrative:antiparasitics_cure_cancer` and `narrative:cancer_cures_suppressed`);
  - Attia 181484/10: "ivermectin for cancer. Actually, I'm glad you brought that up".

**`cancer_alt.metabolic_dietary`.** Query `cancer…(sugar|glucose|keto|fasting)` within 40 characters, plus press-pulse, Seyfried, Warburg, gives 852 / 602 / 97. Verdict: **fine.**
- The count is inflated by Amanda Seyfried the actress (Big Picture 59 episodes).
- Real hits:
  - Jockers 192617/3: "we know sugar feeds cancer and iron tends to feed cancer as well";
  - DOAC 55163/76: "Warburg had clearly shown…".
- Diet-as-cause talk about healthy people belongs in `causes_rates`.

**`cancer_alt.natural_remedies`.** Tight query `laetrile|apricot seeds|mistletoe therapy…|iscador|essiac|soursop|graviola|rick simpson|baking soda…cancer|high-dose IV vitamin C` gives 119 / **103 / 43**. Verdict: **examples change; mind and faith healing needs a home.**
- Bare "mistletoe" is almost all Christmas, and "B17" matches football shows.
- ASR and real phrasing:
  - Axe 174925/1: "vitamin B seventeen and apricot seeds";
  - Axe 174941/3: "sour sap or graviola";
  - Thyroid Fixer 190493/73: "mistletoe is really great in cancers";
  - Axe 174954/3: "medicinal mushrooms. Like shiitake and maitake … reishi" to "fight cancer".
- Mind, faith or energy healing of cancer recurs and fits no subtopic. A loose query gives about 236 episodes / 83 podcasts:
  - School of Greatness 183616/6 (Dispenza): "No drug trial, no chemo, no radiation, no surgery … And now they're up there with no evidence of cancer";
  - Rotten Mango 161723/3: "she cured her own cancer back in the day by prayer alone";
  - Behind the Bastards 328902/8: "Thousands are being healed of cancer through the life and ministry of…".

**`cancer_alt.clinics_protocols`.** Query `gerson|mexico…clinic/cancer|tijuana…|hyperthermia|ozone…cancer|insulin-potentiated|hope4cancer|oasis of hope` gives 614 / 534 / 92, almost all noise. Verdict: **examples change.**
- Noise sources:
  - the surname Gerson (sponsor lists, show credits);
  - "hyperthermia" as heat illness (Huberman 22953/1: "symptoms … for hyperthermia? … transitioning into heat stroke").
- Real hits:
  - Jockers 192433/1: "I went to Hope for Cancer for two weeks";
  - Culture Apothecary 185920/0: "certified Gerson practitioner";
  - Jockers 193082/4: "hyperbaric, radiation, hyperthermia, IV vitamins".
- Write the example as "hyperthermia (as cancer therapy)".

**`cancer_alt.refusing_standard_care`.** Tight query gives 61 / **59 / 37**. Verdict: **rare but important; examples change.**
- Real phrasing is "no chemo, no radiation", "instead of chemo and radiation", "didn't do Western medicine":
  - Axe 174979/1: "instead of chemo and radiation, he chose a root cause approach";
  - 10% Happier 179608/1: "initially I didn't do any Western allopathic medicine … No chemo, radiation";
  - Brecka 177030/3: "So no chemo, no radiation, and now post-surgery images are good".
- False friend: Joe Budden 87204/13, "Hopefully, no chemo or radiation after this". Here the doctors judged it unnecessary, which is conventional care, not refusal.

**`cancer_alt.integrative_adjuncts`.** Query gives 262 / 216 / 45. Verdict: **needs a definition clarification.**
- The Rest Is History contributes 86 episodes through a Cancer Research UK ad: "giving another drug alongside chemotherapy nearly halved the number of children losing their hearing" (41174/3). That is a conventional drug combination, not an integrative add-on.
- Real hits:
  - Extend 176608/3: "the fasting mimicking diet during chemotherapy";
  - Extend 176608/2: "whole food, plant based nutrition during chemotherapy";
  - Danny Jones 319216/10: hyperbaric with radiation and keto.
- Cold caps and anti-nausea care are conventional supportive care and go to `conventional_treatment`.

### Neurological conditions

**`neuro.stroke`.** Tight query `had a stroke|stroke risk/patients|mini-stroke|aneurysm|brain bleed|…stroke` gives 2,490 / 2,250 / 236. Verdict: **fine, small examples change.**
- Biographical mentions are common in true crime and comedy:
  - Snook 320063/10: "She had a stroke and spent an agonizing month and a half";
  - Mindset Mentor 188260/1: "a mini stroke … A TIA is what it was called".
- Bare "stroke" is noisy ("stroke of luck", Get Sleepy 180120/1; golf and swimming strokes).

**`neuro.seizures_epilepsy`.** Bare `seizures?|epilep|convulsions` gives 4,793 episodes but is dominated by legal seizures. Tight query gives 2,094 / **1,662 / 202**. Verdict: **fine.**
- Noise:
  - Charlie Kirk 38529/0: "unreasonable searches and seizures";
  - Shapiro 388412/3: "property seizures, bank levies";
  - "Julius seizure" (JRE 7920/20).
- Real hit: MFM 9846/202, "having had epilepsy since I was twenty seven".

**`neuro.headache_migraine`.** Bare `migraines?|headaches?` gives 10,399 episodes, mostly the hassle idiom. Tight query gives 5,025 / **3,251 / 208**. Verdict: **fine; idiom and ad notes.**
- Hassle idiom:
  - Ramsey 62291/3: timeshares "go up four percent every year with headaches";
  - PBD 205513/0: "a lot of problems and headaches".
- Hidden Brain's 509 episodes are a Nurtec ad (170205/1: "supported by Nertech ODT Remajipant … migraine doesn't wait").

**`neuro.concussion_tbi`.** `concussions?|tbi|traumatic brain|cte|head trauma|blast injury` gives 8,613 / 6,139 / 243. Verdict: **needs a definition change (sport and military boundary).**
- Sport dominates: Fantasy Footballers 750 episodes, Pardon My Take 477, Simmons 354. "Concussion protocol / out with a concussion" alone gives 750 episodes / 75 podcasts:
  - FF 163684/3: "if he passes the concussion protocol";
  - PMT 128700/6: "he does have concussion history".
- Military and blast TBI is a substantive second cluster. TBI/blast/CTE gives 2,226 episodes / 186 podcasts:
  - Team House 154982/17: "Is SOCOM Trying to Bury the Truth About TBI's?";
  - Shawn Ryan 14765/10: "people who sustain concussions, even one. Have a higher incidence of Parkinson's dementia and Alzheimer's".
- Noise: JRE 71065/4, "concussion grenade".
- The definition does not say that a sport concussion takes only this label, not also `musculoskeletal.sports_injuries`. Coders will differ.

**`neuro.neurodegenerative`.** Parkinson's: 2,269 episodes / 185 podcasts. MS/ALS: 1,409 / 184. Huntington's: 201 / 71. Verdict: **fine.**
- Parkinson's mostly appears in disease lists in health shows (Hyman 182000/0: "heart disease, you got Alzheimer's, you got Parkinson's disease, you got cancer"). List rule 6 handles these.
- Exposure claims co-label with the exposure: Tucker 36560/2, "if you're exposed to Paraquat. Your chance of Parkinson's doubles".
- KILL TONY's 81 ALS episodes are a recurring comedian with ALS. These are biographical passing mentions.

**`neuro.nerve_spinal`.** Bare query gives 9,703 episodes, mostly figurative "paralyzed". Tight `neuropathy|nerve damage|sciatica|spinal cord|bell's palsy` gives 2,947 / **2,327 / 210**. Verdict: **needs a definition clarification.**
- Figurative noise: Mindset Mentor 189026/1, "it actually paralyzes them".
- Sleep paralysis (325 episodes / 61 podcasts, mostly Morbid and Last Podcast; Morbid 1767/2) is a sleep phenomenon, not a nerve disorder.
- Neuralink and brain implants: 832 episodes / 92 podcasts, mostly Rogan and Lex Fridman. Most of that is technology talk. Only patient use (paralysis, restoring function) is health content.

**`neuro.other_neurological`.** `restless legs|dystonia|essential tremor|tourette|syncope|vertigo|trigeminal|narcolepsy|tinnitus` gives 1,670 / 1,381 / 179. Verdict: **examples change.**
- Tourette's and tics are the most frequent named item and appear in the examples only as "tics in adults":
  - Modern Wisdom 176072/1: "TikTok-induced Tourette's";
  - DOAC 21995/2: Lewis Capaldi on Tourette's.
- Vertigo is common, often figurative (Office Hours 187396/4: "you're going to get some vertigo doing that").
- Tinnitus belongs to `sensory.hearing` (Drop the Needle 21362/4).

### Dementia, ageing and elder care

**`dementia_ageing.dementia_alzheimers`.** `alzheimer|dementia|amyloid|lecanemab|leqembi|aducanumab|donanemab|type 3 diabetes` gives 13,676 / **8,391 / 289**. Verdict: **needs a codebook rule for public figures.**
- Political speculation is a large block (IHIP News 464 episodes, MeidasTouch 265, Megyn Kelly 195). It mixes substantive symptom talk with insults:
  - MeidasTouch 4804/0: "Donald Trump has continued this week to show massive deterioration and dementia-like symptoms";
  - Bongino 656485/4: "Biden's got some kind of dementia";
  - IHIP 165977/2: "It's just dementia".
- A confirmed celebrity diagnosis is ordinary passing content: Megyn Kelly 5209/4, "Bruce Willis has aphasia … a form of dementia".
- Brain-health ads appear too: Megyn Kelly 7811/0, "up to 45 of dementia cases may be prevented or delayed by managing risk factors".

**`dementia_ageing.cognitive_ageing`.** `cognitive decline|senior moments|age-related cognitive/memory|losing his/her mind|sharp as a tack` gives 2,651 episodes, mostly idiom and political. "Cognitive decline" alone gives 1,663 / 1,220 / 115, with MeidasTouch 98 and Megyn Kelly 84 at the top. Verdict: **needs a definition change.**
- "Cognitive decline" is used for dementia risk in health shows (Habits & Hustle 14763/6: saunas "reduced risk for cognitive decline") and for leaders' fitness (IHIP 166610/0: "massive cognitive decline").
- Normal-ageing examples that do occur: JRE 4272/8, "superagers … The slope of cognitive decline is not as steep".
- "Sharp as a tack" and "losing his mind" are mostly political or idiom (Tucker 7642/1, Behind the Bastards 328858/151).

**`dementia_ageing.elder_care`.** Tight `nursing homes?|assisted living|memory care|elder care|long-term care` gives 4,348 / **3,643 / 258**. Verdict: **examples change.**
- The bare "caregiv" query is polluted by child caregivers (School of Greatness 183994/2: "between children and their caregivers") and by Ramsey finance calls.
- Typical real use is biographical: Wait Wait 1136601/0, "my father's in a nursing home with Alzheimer's disease".
- Falls in older people (fall risk, hip fracture) are rare: 294 episodes / 90 podcasts. Most hip-fracture talk is in menopause and bone shows and belongs in `bone_health`.

### Musculoskeletal

**`musculoskeletal.back_neck_posture`.** Query gives 4,321 / 3,533 / 205. Verdict: **fine.**
- Chiro Hustle (348) leads.
- Ads mention back pain as a product benefit:
  - Shapiro 388588/3: Helix mattress, "I get back pain if the mattress is. Too soft";
  - Bongino 657632/5: Teeter inversion table.

**`musculoskeletal.joints_arthritis`.** Query gives 7,293 / 5,415 / 245. Verdict: **needs a boundary note.**
- Charlie Kirk (384 episodes) is mostly Relief Factor ads (603 episodes in all): 39206/1, "100% drug-free knee pain, back pain, joint pain, elbow pain".
- Rheumatoid and psoriatic arthritis (1,010 episodes / 123 podcasts) overlap with `immune.autoimmune`, whose examples already list rheumatoid arthritis:
  - Today in True Crime 601016/0: psoriatic arthritis drug ad;
  - Jockers 192452/0: "rheumatoid arthritis or some other autoimmune condition".

**`musculoskeletal.bone_health`.** Query gives 3,288 / 1,830 / 151. Verdict: **fine.**
- Menopause shows are core (Mel Robbins 33139/7: "in menopause … this cycle of bone loss").
- Trans-athlete arguments use bone density as a sex difference (Charlie Kirk 39072/4). That passage is gender content, not bone health.

**`musculoskeletal.sports_injuries`.** Query gives 13,033 / **8,887 / 253**, dominated by fantasy and sports shows. Verdict: **needs a definition change.**
- A filtered sample of sports shows (`injur|torn|sprain|concussion|out for the season|IR`) gives 33,790 segments. Most mention an injury with no body part or detail:
  - Simmons 79995/6: "he's had bad luck with injuries";
  - PMT 52599/11: "coming off the injury";
  - FF 164532/3: "dealing with injury now".
- Named injuries are real passing content: Ringer 322779/2, "Michael Thomas had a high ankle sprain".
- Plantar fasciitis, carpal tunnel and similar are fairly common (about 1,578 episodes with hernia and bunion noise; Radiolab 59527/5 on carpal tunnel). They fit the "repetitive strain" clause.

**`musculoskeletal.chronic_pain`.** Query gives 4,530 / 3,503 / 243. Verdict: **needs a boundary note and examples change.**
- Fibromyalgia hits belong to `chronic_complex.fibromyalgia` (Mayim Bialik 185162/5).
- Mind-body pain (Sarno, pain reprocessing) recurs: 132 episodes / 60 podcasts, Mayim Bialik 28. Example: MFM 9981/34 promoting "The Cure for Chronic Pain" with Nicole Sachs.

**`musculoskeletal.rehab_manual_therapy`.** Tight `physical therap|physiotherap|dry needling|massage therap|rehabbing my knee…` gives 3,834 / **3,070 / 232**. Verdict: **needs a boundary note.**
- My first query matched "physiology", so ignore its count.
- "Please Me! A Sexuality Podcast" (127 episodes) and The Toast 31184/1 ("starting physical therapy … pelvic floor") show that pelvic-floor PT is common. It belongs to `womens.pelvic_floor`.

**`musculoskeletal.muscle_loss`.** Query gives 5,119 / 2,979 / 156; sarcopenia, muscle loss and "losing muscle" alone give 1,237 / 85. Verdict: **fine.**
- GLP-1 muscle-loss talk co-labels as rule 1 says (Hyman 182347/1).
- Protein ads state muscle mass as a benefit (Biohack-it 178171/3: "support my skeletal muscle mass").

### Injuries, emergencies and end of life

**Testing the section 3 crime rule.** I sampled forensic vocabulary corpus-wide (24,567 / **16,519 / 466**) and within true-crime shows (10,256 segments).
- What the rule yields on typical passages:
  - Snapped 23865/0: "It was clear that she had been shot. The gunshot wound was to the back of her head. The blood had not coagulated yet" → `trauma_fractures` + `death_dying`.
  - 48 Hours 70225/2: "shot three times. She also had 29 stab wounds" → both labels.
  - Serialously 160863/1: "killed by multiple stab wounds, and William also suffered from blunt force trauma" → both labels.
  - 48 Hours 70357/1: "The family declined an autopsy" → `death_dying`.
  - Casefile 23838/3: "She'd been raped and strangled". Coders could read sexual assault as "the subject" and add `violence_abuse`, or not; the rule is ambiguous here. The same applies to Morbid 5322/3: "he raped and strangled her to death".
- These detections carry no health information beyond the crime. Their volume would make `trauma_fractures` and `death_dying` two of the most frequent subtopics in the corpus.
- The rule works where the medical side is the point:
  - Fresh Air 25321/0: "the autopsy ruled it a death by protein-calorie malnutrition" in jail;
  - Breaking Points 330416/158: "what type of injuries were coming in" at a Gaza hospital;
  - Last Podcast 23261/2: a disputed claim of 23 stab wounds checked against hospital records (forensic).
- War casualty counts with no medical detail (Breaking Points 330864/316, 330181/64) follow the "killed" test and are not health content. Starvation ("babies who are starving to death") is health content.

**`acute_care.trauma_fractures`.**
- Accidental and everyday injuries, tight query (`broke my/his/her [bone]|car crash … injur/hospital|fractured skull/spine/hip`): 3,579 / 3,258 / 244.
  - Survival 590691/3: "Violet had suffered a fractured skull";
  - KILL TONY 194510/9: "I got hit by a drunk driver and broke my neck, and this is physical therapy".
- Combat wounds and amputation: 3,109 episodes / 227 podcasts (Team House, Shawn Ryan):
  - Megyn Kelly 42141/5: "16 pieces of shrapnel in his body";
  - Team House 155035/258: "taking shrapnel to your legs".
- Verdict: **needs a definition change.** Move the crime-narrative clause out, and add combat wounds and amputation as examples.

**`acute_care.violence_abuse`.** `domestic violence|sexual assault|child abuse|intimate partner|coercive control|narcissistic abuse|gun violence` gives 17,150 / **12,334 / 381**. Verdict: **needs a definition change.**
- The top shows are political and news (Megyn Kelly 545, Shapiro 528, MeidasTouch 476, Walsh 418). Most of that is allegations against named people as legal or political news:
  - Shapiro 390374/5: "Why is sexual assault or sexual misbehavior any different than any other crime?";
  - Walsh 207412/1: "he wasn't accused of rape or sexual assault".
- The pattern use the label is meant for:
  - Ramsey 57960/8: "if you were in a domestic violence situation, one of the things the abuser convinces the person of is that they don't have any choices";
  - This Feels Criminal 323291/3: "victims of intimate partner violence oftentimes don't tell anybody".
- Hotline boilerplate at episode end: Burden of Guilt 611948/218, "call the Child Help National Child Abuse Hotline".

**`acute_care.emergency_critical_care`.** Query gives 11,537 / 8,996 / 348. Verdict: **fine.**
- Noise: "septic tank" (Big Picture 321236/2), "antiseptic".
- COVID ICU capacity (Shapiro 389925/5: "the status of ICU beds") is `covid.illness_severity` or `health_system.hospitals_access`.
- Biographical ER visits are common in comedy (YMH 200824/3).

**`acute_care.wounds_first_aid`.** Query gives 6,817 / 5,446 / 296. Verdict: **needs a definition clarification.**
- CPR is listed here, while "resuscitation" is listed under `emergency_critical_care`:
  - Theo Von 77656/3: "He had a cardiac arrest, and we were doing CPR";
  - Simmons 79372/0: "he got CPR in the field".
- Figurative uses:
  - SYSK 25810/0: "the first aid approach" for speaking anxiety;
  - Right About Now 15731/0: a PR "CPR method".
- Boxing stitches (JRE 16060/15: "a two-centimeter cut on his ear that took seven stitches") are sport injuries.

**`acute_care.poisoning_environmental_injury`.** Query gives 13,763 / 10,764 / 357, mostly noise. Verdict: **needs a boundary note.**
- Figurative "drowning": Habits & Hustle 483001/4, "we're drowning information".
- Food poisoning (Bad Friends 161277/6) is already an example under `infectious.foodborne`, so the two labels conflict.
- Pet poison control is veterinary (The Toast 29610/2).
- Real uses: survival hypothermia (MrBallen 19111/0) and fluoride-toothpaste poison-control warnings (Brecka 177152/1).

**`acute_care.death_dying`.** Verdict: **examples change.**
- `\bmaid\b` is mostly the household maid or "maid of honor" (The Toast 94861/5). ASR gives no way to tell MAID apart, so the example should be the full phrase.
- Tight `hospice|palliative|end-of-life care|euthanasia|assisted dying/suicide|medical assistance in dying|death with dignity|death doula` gives 2,741 / **2,163 / 232**:
  - Today Explained 438961/0: "The rise of death doulas";
  - Miss Understood 162763/4: "his advance healthcare directive … making his end of life decisions".

**Near-death experiences (no current label).** `near-death experience` gives 1,534 / **1,084 / 166**. A wider query with NDE and "flatlined" gives 1,599 / 195. Mayim Bialik 93 episodes, School of Greatness 43, Danny Jones 42, Shawn Ryan 23.
- About half are reports of clinical death:
  - Mayim Bialik 185313/1: "The Scientific Basis For NDEs";
  - Attia 181647/12: "I started to look into near-death experiences … an awful lot of people see the black pit";
  - Please Me 186931/2: "I died and came back to life".
- The other half are loose "close call" uses:
  - Hidden Brain 170111/0: a crash;
  - JRE 10502/17: "It's not like a near-death experience".
- None of the existing subtopics fits: `death_dying` is end-of-life care, and `alt_medicine.energy_spiritual_healing` is healing.

### Surgery and procedures

**`procedures.surgery_hospital`.** `surgery|surgeries|post-op|hospital stay|appendectomy|appendix` gives 31,284 / **21,279 / 429**, the largest count in the slice. Verdict: **needs a co-labeling clarification.**
- Most hits are surgeries that have a more specific home:
  - plastic surgery (WWC 95701/2) → `skin_beauty.cosmetic_procedures`;
  - "gender surgeries for kids" (Morning Wire 168898/1, Shapiro 389301/2) → `gender.youth_gender_medicine`;
  - athletes' surgery dates (FF 163468/1);
  - laser eye surgery (Modern Wisdom 175812/1) → `sensory.vision`.
- Rule 1 (intervention plus outcome) would double-label all of these with `surgery_hospital`.

**`procedures.anesthesia`.** Query gives 3,130 / 2,615 / 249. Verdict: **fine.**
- Ketamine as an anesthetic (Pivot 31834/0) also takes `psychoactives.ketamine`.
- Consciousness under anesthesia is a recurring philosophical aside (SYSK 85367/0).

**`procedures.transplants_donation`.** Query gives 5,500 / 3,975 / 249. Verdict: **fine.**
- Noise: "transplant" meaning relocate (Breaking Points 330871/120); bone marrow in immunology talk (Megyn Kelly 13439/6).

**`procedures.imaging_diagnostics`.** Query gives 11,836 / 8,745 / 309. Verdict: **needs a boundary note.**
- Charlie Kirk (596) and Candace (233) are mostly Preborn ads (990 episodes / 45 podcasts): Charlie Kirk 39322/1, "you can give a free ultrasound session to a woman or a girl who might otherwise choose to end…".
- MRI as a research method is evidence talk, not a procedure: On Purpose 84802/8, "through MRI studies we know every single person is born with circuits in the brain for spiritual awareness".
- Imaging for heart risk (Brecka 177100/6: "carotid intima media thickness … non invasive ultrasound") also takes `cardiovascular.heart_disease`.

**`procedures.lab_testing`.** Query gives 8,398 / 5,624 / 241. Verdict: **fine.**
- The boundary with `self_tracking.consumer_lab_tests` matters: InsideTracker (Lex 325338/1) and Function (Mel Robbins 486/4) ads are consumer tests.

**`procedures.regenerative_medicine`.** `stem cells?|prp|platelet-rich|exosomes?` gives 7,833 / 2,738 / 170. Verdict: **fine.**
- Exosome skin serum (Mind Pump 195417/5) belongs to `skin_beauty.regenerative_aesthetics`.

**`procedures.blood_cell_therapies`.** `plasma exchange|plasmapheresis|apheresis|transfusion|cord blood|NK cells` gives 1,228 / 958 / 159. Verdict: **fine.**
- A Next Health ad with plasma exchange as a longevity offer runs on Extend (61 episodes; 176629/6: "longevity optimization plan using advanced. Tools like ozone, plasma exchange, and peptides"). The existing co-label with `longevity.protocols_clinics` covers it.
- Transfusions in crime stories (Dateline 159418/2) fall under the crime rule.

## Proposed edits

CHANGE `topic:cancer.causes_rates`:
| causes_rates | Cancer causes, risk, prevention & rates | What causes cancer, what lowers the risk of getting it, and how common it is: carcinogens and exposures, foods, drugs or habits said to cause, promote ("feeds cancer") or prevent cancer in people who do not have it, risk factors, trends, early-onset cancer, cancer as a "metabolic" disease. Treating an existing cancer with a diet, food or remedy goes to `cancer_alt`. | carcinogen; "X causes cancer"; cancer rates rising; cancer in young people; lowers cancer risk; anti-cancer foods; cancer-fighting; risk factors; metabolic theory of cancer |
Why: prevention phrasing gives 958 episodes / 104 podcasts and is not named in the definition. Axe 174954/3 "How to Prevent CANCER"; SYSK 23692/5 "the cancer-fighting enzyme found in garlic". Without the boundary, coders split these between this label and `cancer_alt.natural_remedies`.

CHANGE `topic:cancer.screening_diagnosis`:
| screening_diagnosis | Cancer screening & diagnosis | Detecting cancer: screening tests, full-body scans sold as cancer screening, and diagnostic workups. | mammogram; colonoscopy; Cologuard (stool DNA test); PSA test; Pap smear (for cancer); Galleri; full-body MRI (Prenuvo, Ezra); biopsy; staging |
Why: the Cologuard ad alone runs in 2,248 episodes, transcribed as Coligar, Colgard and ColiGuard (WWC 96571/0, 91704/4). Full-body MRI is discussed as cancer screening (Attia 181577) and advertised ("Know what lies beneath", Boring History).

ADD `topic:cancer.colorectal_cancer` under `cancer`:
| colorectal_cancer | Colorectal cancer | Colon, rectal and bowel cancer specifically, including the rise in early-onset colorectal cancer. Screening tests for it also take `cancer.screening_diagnosis`. | colon cancer; colorectal cancer; rectal cancer; bowel cancer; early-onset colorectal cancer; Cologuard |
Why: about 810 non-ad episodes / 146 podcasts, comparable to skin cancer (968) and prostate cancer (1,292), plus 2,248 Cologuard-ad episodes. It carries the early-onset storyline: DOAC 19824/1 "four times more likely to be diagnosed with rectal cancer … than my parents were"; Niddam 428521/140 "Every other cancer is on the decline except for colorectal cancer".

CHANGE `topic:cancer.prostate_cancer`:
| prostate_cancer | Prostate cancer | Prostate cancer specifically, including PSA testing for it. | prostate cancer; PSA test; PSA level; Gleason score; prostatectomy |
Why: bare "PSA" is mostly public service announcement or card grading (Trading Cards podcast 70 episodes, Pardon My Take 267). The term needs its noun.

CHANGE `topic:cancer.other_specific_cancers`:
| other_specific_cancers | Other named cancers | Any other named cancer type. | pancreatic cancer; leukemia; lymphoma; brain tumor; glioblastoma; lung cancer; ovarian cancer; cervical cancer; thyroid cancer; multiple myeloma |
Why: colon cancer moves to the new colorectal subtopic. Glioblastoma and ovarian cancer are frequent (brain tumour or glioblastoma 1,529 episodes; ovarian 338).

CHANGE `topic:cancer.conventional_treatment`:
| conventional_treatment | Conventional cancer treatment | Standard oncology: chemotherapy, radiation, surgery, immunotherapy, targeted drugs, cancer vaccines and cell therapies, supportive care for treatment side effects, cancer centers, survivorship. Chemotherapy for a non-cancer disease takes that disease's topic. | chemotherapy; radiation; mastectomy; immunotherapy; CAR-T; mRNA cancer vaccine; cold cap; oncologist; remission |
Why: cold caps and side-effect care (Wiser Than Me 611525/0) need a home that is not `integrative_adjuncts`. Cancer vaccines appear in 70 episodes / 38 podcasts. Chemo for lupus (Dateline 2225/0) is not cancer.

CHANGE `topic:cancer_alt.repurposed_drugs`:
| repurposed_drugs | Repurposed drugs for cancer | Off-label drugs promoted for cancer, when cancer is named. The same drugs sold or discussed with no cancer mentioned go to `medications.repurposed_offlabel`, and in a parasite protocol to `detox.parasite_cleanses`. | ivermectin for cancer; fenbendazole (fenben) for cancer; mebendazole; Joe Tippens protocol; metformin for cancer; dipyridamole; repurposed drug cocktails |
Why: many hits are ivermectin/mebendazole pharmacy ads with no cancer mention (Megyn Kelly 4077/1, Bongino 656001/0) or fenbendazole in parasite cleanses (Brecka 177028/7). Only about 130 episodes / 42 podcasts have the drug and cancer in the same segment.

CHANGE `topic:cancer_alt.natural_remedies`:
| natural_remedies | Natural & IV cancer remedies | Herbal, mushroom, vitamin, IV and folk remedies for cancer. Mind, faith or energy healing of cancer takes `stress.mind_body` or `alt_medicine.energy_spiritual_healing` plus the bare `topic:cancer_alt`. | high-dose IV vitamin C; laetrile/B17 ("vitamin B seventeen"); apricot seeds; mistletoe therapy; medicinal mushrooms (turkey tail, reishi); soursop/graviola; Rick Simpson oil; baking soda; Essiac tea |
Why: the real phrasing has ASR forms ("vitamin B seventeen", Axe 174925/1; "sour sap", Axe 174941/3) and mushrooms (Axe 174954/3). Bare "mistletoe" and "B17" are noise. Mind and faith healing recurs (about 236 episodes / 83 podcasts on a loose query; Dispenza, School of Greatness 183616/6; Rotten Mango 161723/3 "cured her own cancer … by prayer alone") and has no rule.

CHANGE `topic:cancer_alt.clinics_protocols`:
| clinics_protocols | Alternative cancer clinics & protocols | Clinics and named protocols outside standard oncology. Hyperthermia counts here only as a cancer therapy; heat illness goes to `acute_care.poisoning_environmental_injury`. | Mexico or Tijuana cancer clinic; Hope4Cancer; Gerson therapy; hyperthermia (as cancer therapy); ozone for cancer; insulin-potentiated therapy |
Why: most "hyperthermia" hits are heat illness (Huberman 22953/1). Real clinic talk names Hope for Cancer (Jockers 192433/1).

CHANGE `topic:cancer_alt.refusing_standard_care`:
| refusing_standard_care | Refusing or delaying standard treatment | Choosing to forgo or delay chemotherapy, surgery or radiation, and the outcomes. Treatment the oncologist judged unnecessary is `cancer.conventional_treatment`. | refused chemo; "no chemo, no radiation"; "instead of chemo and radiation"; didn't do Western medicine; declined surgery; chose natural treatment instead |
Why: real phrasing comes from Axe 174979/1, 10% Happier 179608/1 and Brecka 177030/3. False friend: Joe Budden 87204/13, "Hopefully, no chemo or radiation after this", which reflects the doctors' judgment. The tight query gives 59 episodes / 37 podcasts.

CHANGE `topic:cancer_alt.integrative_adjuncts`:
| integrative_adjuncts | Integrative add-ons to standard cancer care | Complementary therapies used alongside chemotherapy, radiation or surgery (hyperbaric oxygen, supplements, fasting or ketosis around treatment, melatonin), as opposed to replacements for them. A conventional drug added to chemotherapy, and standard supportive care, go to `cancer.conventional_treatment`. | fasting during chemo; fasting-mimicking diet during chemo; hyperbaric with radiation; supplements alongside chemo; melatonin during radiotherapy; integrative oncology |
Why: 86 of 216 episodes in this query come from a Cancer Research UK ad about "another drug alongside chemotherapy" (Rest Is History 41174/3). Real hits: Extend 176608/3 and Danny Jones 319216/10.

CHANGE `topic:neuro.concussion_tbi`:
| concussion_tbi | Concussion & brain injury | Traumatic brain injury and its long-term effects, from any cause. Concussions in sport take this subtopic only, not also `musculoskeletal.sports_injuries`; a head injury from a crash or assault takes this subtopic rather than `acute_care.trauma_fractures`. | concussion; concussion protocol; TBI; CTE; head trauma; blast injury; blast overpressure |
Why: 6,139 episodes, most of them sports. "Concussion protocol / out with a concussion" gives 750 episodes (FF 163684/3). Military TBI gives 2,226 episodes / 186 podcasts (Team House 154982/17). Without the boundary, coders will split on double-labeling.

CHANGE `topic:neuro.headache_migraine`:
| headache_migraine | Headache & migraine | Headaches and migraine as symptoms or conditions. "A headache" meaning a hassle is not health content. | migraine; cluster headache; tension headache; migraine drugs (Nurtec, Ubrelvy); "I got the worst migraine" |
Why: bare "headache" gives 10,399 episodes, mostly the hassle idiom (Ramsey 62291/3, PBD 205513/0); the tight query gives 3,251. Hidden Brain's 509 hits are a Nurtec ad that ASR renders "Nertech ODT Remajipant" (170205/1).

CHANGE `topic:neuro.nerve_spinal`:
| nerve_spinal | Nerves, spinal cord & paralysis | Peripheral nerve and spinal cord problems, paralysis as a medical condition, and neural implants used as treatment. Sleep paralysis goes to `topic:sleep`; "paralyzed" by fear is not health content. | neuropathy; spinal cord injury; paralysis; quadriplegic; Bell's palsy; sciatica (nerve); nerve damage; Neuralink for paralysis |
Why: bare "paralyz/paralys" dominates the 9,703-episode count and is mostly figurative (Mindset Mentor 189026/1) or sleep paralysis (325 episodes / 61 podcasts; Morbid 1767/2). The tight query gives 2,327 episodes. Neuralink (832 episodes) is mostly technology talk.

CHANGE `topic:neuro.other_neurological`:
| other_neurological | Other neurological conditions | Named neurological conditions not listed above. Tinnitus goes to `sensory.hearing`. | Tourette's and tics; restless legs; dystonia; spasmodic dysphonia; essential tremor; vertigo (as a condition); syncope; fainting |
Why: Tourette's is the most frequent named item (Modern Wisdom 176072/1 "TikTok-induced Tourette's"; DOAC 21995/2), but the examples only list "tics in adults". Tinnitus is among the hits (Drop the Needle 21362/4) but belongs elsewhere.

CHANGE `topic:dementia_ageing.dementia_alzheimers`:
| dementia_alzheimers | Alzheimer's & dementia | Dementia and Alzheimer's: what it is, causes, diagnosis, drugs, prevention claims, and the risk of "cognitive decline" when used to mean dementia risk. A named public figure's alleged dementia follows the codebook rule for unsettled facts about a person. Normal age-related cognitive change goes to `dementia_ageing.cognitive_ageing`. | Alzheimer's; dementia; amyloid; lecanemab; "type 3 diabetes"; reduce your risk of dementia; aphasia (as dementia) |
Why: 8,391 episodes. Health shows use "cognitive decline" as dementia risk (Habits & Hustle 14763/6). Political speculation is a large block (IHIP News 464 episodes, MeidasTouch 265; MeidasTouch 4804/0 "dementia-like symptoms").

CHANGE `topic:dementia_ageing.cognitive_ageing`:
| cognitive_ageing | Normal cognitive ageing | Age-related cognitive change and mental capacity in older people short of dementia, including debate over an older leader's mental sharpness when no dementia is claimed. | cognitive decline with age; superagers; fluid intelligence in old age; sharp at 91; senior moments; "is he still sharp?" |
Why: "cognitive decline" gives 1,220 episodes, led by MeidasTouch (98) and Megyn Kelly (84). JRE 4272/8 "superagers" is the real normal-ageing vocabulary.

CHANGE `topic:dementia_ageing.elder_care`:
| elder_care | Elder care & frailty | Caring for older people, long-term care, and age-related frailty and falls. Caregivers of children, and caregiving as a job or business with no health content, are not this subtopic. | caring for aging parents; nursing home; assisted living; memory care; long-term care; caregiver burnout; falls in the elderly; frailty |
Why: the tight query gives 3,643 episodes / 258 podcasts. The bare "caregiv" query is polluted by child caregivers (School of Greatness 183994/2) and Ramsey finance calls.

CHANGE `topic:musculoskeletal.joints_arthritis`:
| joints_arthritis | Joints & arthritis | Joint pain and joint disease. Rheumatoid, psoriatic and other inflammatory arthritis go to `immune.autoimmune`, adding this subtopic when joint symptoms or damage are discussed. | osteoarthritis; knee pain; hip replacement; knee replacement; meniscus; gout; joint supplements (as joint care) |
Why: rheumatoid or psoriatic arthritis gives 1,010 episodes / 123 podcasts. `immune.autoimmune` already lists rheumatoid arthritis, so the two labels conflict (Today in True Crime 601016/0 psoriatic arthritis ad; Jockers 192452/0).

CHANGE `topic:musculoskeletal.sports_injuries`:
| sports_injuries | Sports & overuse injuries | Named injuries from sport, training or repetitive use, whoever the person, and their rehabilitation and surgery. An athlete described only as injured, hurt, banged up or questionable, with no body part, diagnosis or treatment, is not health content. Concussions go to `neuro.concussion_tbi`; injuries from a fall, crash or assault to `acute_care.trauma_fractures`. | ACL tear; Achilles tear from sport; high ankle sprain; hamstring strain; tendonitis; rotator cuff; tennis elbow; plantar fasciitis; carpal tunnel; repetitive strain |
Why: 8,887 episodes, dominated by Fantasy Footballers (1,383), Pardon My Take (1,042), Simmons (800) and Ringer Fantasy Football (641). Bare mentions carry no health information: Simmons 79995/6 "he's had bad luck with injuries"; FF 164532/3 "dealing with injury now". Named injuries are real: Ringer 322779/2 "Michael Thomas had a high ankle sprain".

CHANGE `topic:musculoskeletal.chronic_pain`:
| chronic_pain | Chronic pain & pain management | Persistent pain and how it is managed, other than opioids, including mind-body approaches to pain. Fibromyalgia goes to `chronic_complex.fibromyalgia`. | chronic pain; pain science; NSAIDs for pain; pain management; pain reprocessing; Sarno (mind-body pain); fascia pain |
Why: mind-body pain gives 132 episodes / 60 podcasts (MFM 9981/34 on "The Cure for Chronic Pain"; Mayim Bialik 28 episodes). Fibromyalgia hits need the boundary (Mayim Bialik 185162/5).

CHANGE `topic:musculoskeletal.rehab_manual_therapy`:
| rehab_manual_therapy | Physical therapy & rehabilitation | Physical therapy, rehabilitation, exercise prescribed to recover from an injury or pain, and conventional manual therapy. General stretching goes to `fitness.mobility_flexibility`; chiropractic to `alt_medicine.chiropractic`; pelvic-floor therapy to `womens.pelvic_floor`. | physical therapy; physio; rehab after surgery; massage therapy; dry needling; stretches for back pain |
Why: pelvic-floor PT is a frequent physical-therapy context ("Please Me!" 127 episodes; The Toast 31184/1). Note that "rehab" also means addiction treatment, which goes to `drugs_addiction`.

ADD `topic:acute_care.crime_war_injuries` under `acute_care`:
| crime_war_injuries | Injuries & deaths in crime, war and news stories | Injuries, causes of death, autopsy and medical-examiner findings and casualty descriptions told as part of a crime, war, disaster or news story, without discussion of their medical care or consequences. When the victim's treatment, recovery, disability or the medical explanation is itself discussed, use `acute_care.trauma_fractures`, `acute_care.death_dying` or the condition's own subtopic instead. | gunshot wound to the head; 29 stab wounds; blunt force trauma; strangled; bled out; the autopsy found; the medical examiner ruled; cause of death undetermined |
Why: forensic vocabulary appears in 16,519 episodes across 466 podcasts (48 Hours 597, Morbid 526, MFM 515, Dateline 440). Under the current rule, nearly every true-crime episode gets both `trauma_fractures` and `death_dying` (Snapped 23865/0 "The gunshot wound was to the back of her head"; Serialously 160863/1 "multiple stab wounds … blunt force trauma"). A separate subtopic keeps coding consistent and lets analysis exclude it. Health-relevant cases stay in the main labels (Fresh Air 25321/0, autopsy finding of starvation in jail).

CHANGE `topic:acute_care.trauma_fractures`:
| trauma_fractures | Injuries & trauma | Physical injuries from a fall, crash, assault, combat or other non-sport cause, and an unspecified injury to a real person, when the injury, its treatment or recovery is described. Injuries told only as part of a crime or war story go to the proposed crime_war_injuries subtopic. A death or its cause also takes `acute_care.death_dying`. | broken leg; "broke my neck"; fractured skull; car crash injuries; gunshot wound treated in hospital; shrapnel wounds; amputation; trauma surgery; "I got injured" |
Why: everyday and combat injuries are frequent in their own right (broken bones and crash injuries 3,258 episodes; combat wounds and amputation 3,109 episodes / 227 podcasts; Megyn Kelly 42141/5 "16 pieces of shrapnel in his body"). The crime clause moves to the new subtopic.

CHANGE `topic:acute_care.violence_abuse`:
| violence_abuse | Violence & abuse | Interpersonal violence and abuse discussed as a pattern, risk, prevention or health and safety issue (sexual assault, domestic violence, child abuse and neglect, gun violence as a public-health matter, elder abuse), a survivor's harm and recovery, and emotional or psychological abuse in relationships as harm. An allegation, charge or trial of a named person discussed as news or legal process is not health content; a single crime told as an event follows the codebook crime rule; therapy-speak as a social phenomenon goes to `mental.pop_psychology`. | sexual assault statistics; domestic violence; child abuse; gun violence epidemic; intimate partner violence; strangulation as a risk factor; coercive control; narcissistic abuse; survivor's trauma |
Why: 12,334 episodes / 381 podcasts, led by political and news shows (Megyn Kelly 545, Shapiro 528, MeidasTouch 476, Walsh 418) discussing allegations (Shapiro 390374/5; Walsh 207412/1). The pattern use is distinct: Ramsey 57960/8; This Feels Criminal 323291/3 "victims of intimate partner violence oftentimes don't tell anybody".

CHANGE `topic:acute_care.wounds_first_aid`:
| wounds_first_aid | Wounds, burns & first aid | Cuts, burns, bites and what bystanders do about them or about collapse, choking or bleeding immediately, before professional care. Resuscitation in hospital goes to `acute_care.emergency_critical_care`; injuries in sport to `musculoskeletal.sports_injuries`. | stitches; burns; dog bite; snake bite; first aid; tourniquet; bystander CPR; AED; Heimlich |
Why: CPR is split today between this label and "resuscitation" under `emergency_critical_care` (Theo Von 77656/3; Simmons 79372/0 "he got CPR in the field"). Boxing stitches (JRE 16060/15) are sport injuries.

CHANGE `topic:acute_care.poisoning_environmental_injury`:
| poisoning_environmental_injury | Poisoning, environmental & motion injury | Poisoning, overdoses of non-drugs-of-abuse, heat illness, hypothermia, drowning, choking, altitude, G-forces, motion and seasickness. Food poisoning goes to `infectious.foodborne`; poisoning of pets is excluded. | poisoning; poison control; carbon monoxide; antifreeze poisoning; heat stroke; hyperthermia; hypothermia; drowning; altitude sickness; G-force blackout; motion sickness |
Why: "food poisoning" is already an example under `infectious.foodborne` (Bad Friends 161277/6), so the two labels conflict. Heat-illness "hyperthermia" lands here (Huberman 22953/1). Figurative "drowning" is common noise (Habits & Hustle 483001/4).

CHANGE `topic:acute_care.death_dying`:
| death_dying | Death, dying & end-of-life care | How people die and end-of-life care: causes of death as medical fact, autopsies that establish disease or neglect, hospice, palliative care, advance directives, death doulas, euthanasia and assisted dying. A death named only as a fact about a person ("died of cancer") takes the cause's subtopic only. | cause of death; hospice; palliative care; advance directive; death doula; medical assistance in dying; assisted suicide; sudden death |
Why: "MAID" is unusable as an ASR example because `\bmaid\b` is mostly "maid of honor" or household help (The Toast 94861/5). The tight query gives 2,163 episodes / 232 podcasts and shows death doulas (Today Explained 438961/0) and advance directives (Miss Understood 162763/4). "Died of cancer" is very frequent (part of the 6,307 biographical cancer episodes) and should not inflate this label.

ADD `topic:acute_care.near_death_experiences` under `acute_care`:
| near_death_experiences | Near-death experiences | Reported experiences during clinical death, cardiac arrest or near-fatal events (out-of-body, tunnel or light, life review) and claims about what they show about consciousness or death. "A near-death experience" meaning a close call with no experience described is a passing mention of the event's own subject. | near-death experience; NDE; "I died and came back"; out-of-body experience during surgery; flatlined and saw |
Why: 1,084 episodes / 166 podcasts with the exact phrase, about half of them true accounts (Mayim Bialik 93 episodes, 185313/1 "The Scientific Basis For NDEs"; Attia 181647/12; Please Me 186931/2 "I died and came back to life"). It is a contested claims area (consciousness surviving death) with no current home. If this feels too thin, the fallback is a clause in `acute_care.death_dying`, but that would mix afterlife claims with hospice care.

CHANGE `topic:procedures.surgery_hospital`:
| surgery_hospital | Surgery & hospital stays | Operations, recovery and the experience of being hospitalized, when the operation or stay is itself discussed. A procedure named only as the treatment of a condition with its own subtopic ("had ACL surgery", "gender surgeries", "plastic surgery", "LASIK") takes that subtopic instead. | surgery; operation; post-op; recovering from surgery; hospital stay; appendectomy; surgical complications |
Why: this is the largest count in the slice (21,279 episodes / 429 podcasts), mostly surgeries with a specific home: plastic surgery (WWC 95701/2), gender surgeries (Morning Wire 168898/1), athletes' surgery dates (FF 163468/1), laser eye surgery (Modern Wisdom 175812/1). Co-label rule 1 would otherwise double-label all of them.

CHANGE `topic:procedures.imaging_diagnostics`:
| imaging_diagnostics | Imaging & diagnostic procedures | Medical imaging and diagnostic procedures outside cancer screening, and radiation dose from them. Prenatal ultrasound goes to `pregnancy.pregnancy_health` (and `fertility.abortion` in pregnancy-center appeals); imaging cited as a research method ("MRI studies show") is evidence, not this topic; blood and lab tests go to `procedures.lab_testing`. | MRI; CT scan; X-ray; endoscopy; ultrasound; PET scan; radiation from CT scans |
Why: Preborn "free ultrasound" ads run in 990 episodes / 45 podcasts (Charlie Kirk 39322/1), and MRI as a research method is common (On Purpose 84802/8). Both inflate the 8,745-episode count.

## Codebook and prompt notes

1. **Section 3, violence, crime, war and death: replace the paragraph.** Evidence is in
   the acute-care findings above: 16,519 episodes / 466 podcasts with forensic
   vocabulary. Suggested text:
   > In true crime, news or history, a crime named only as "murder", "killed",
   > "assault" or "raped", and a bare casualty count, is not health content. An injury,
   > cause of death, autopsy or medical-examiner finding described as part of the story
   > ("shot in the back of the head", "29 stab wounds", "the autopsy found") takes one
   > `passing` crime_war_injuries detection per stretch (proposed subtopic). Use
   > `acute_care.trauma_fractures`, `acute_care.death_dying`,
   > `acute_care.emergency_critical_care`, a poisoning or a condition's own subtopic
   > only when the medical side is itself discussed: treatment, recovery or disability,
   > a medical explanation of how the injury kills, an autopsy finding of disease,
   > starvation or neglect, or poisoning by a named substance. Use
   > `acute_care.violence_abuse` for violence or abuse discussed as a pattern, risk,
   > prevention or public-health issue, or for a survivor's harm and recovery; an
   > allegation, charge or trial of a named person discussed as news or legal process
   > is not health content.

   If the new subtopic is rejected, keep the current routing but add "one `passing`
   detection per stretch, never `substantive`, unless the medical side is discussed",
   and state explicitly that "raped" in a crime narrative is the event test, not
   "sexual assault is the subject". The current wording leaves Casefile 23838/3
   ("She'd been raped and strangled") and Morbid 5322/3 to coder judgement.

2. **Section 3, sports.** Add a parallel to the crime rule:
   > An athlete named as injured, out, questionable or banged up with no body part,
   > diagnosis or treatment is not health content. A named injury ("torn ACL",
   > "hamstring", "concussion") is one `passing` detection, and an injury-report list of
   > several players in one stretch is one detection with the named injuries'
   > subtopics. Sports concussions take `neuro.concussion_tbi` only.

   Evidence: 8,887 episodes in the injury query, dominated by fantasy football; sport
   concussion 750 episodes.

3. **Section 3, idioms to add to the exclusion list.** Evidence for each:
   - "a headache" meaning a hassle (Ramsey 62291/3; bare "headache" gives 10,399 episodes);
   - "paralyzed" by fear (Mindset Mentor 189026/1);
   - "stroke of luck" (Get Sleepy 180120/1);
   - "searches and seizures" and asset "seizures" (Charlie Kirk 38529/0, Shapiro 388412/3);
   - "drowning in" work or information (Habits & Hustle 483001/4);
   - "transplant" meaning relocate (Breaking Points 330871/120);
   - "first aid" for non-medical problems (SYSK 25810/0);
   - "is a cancer on…" (PBD 205594/5);
   - Cancer the zodiac sign (about 694 episodes for idiom and astrology together);
   - "concussion grenade" (JRE 71065/4);
   - "near-death experience" meaning a close call, unless an experience is described.

4. **Section 5.1, unsettled facts about a person: extend to dementia.** Suggested addition:
   > A named public figure said to have dementia, Alzheimer's or "cognitive decline",
   > not diagnosed in the window, takes `dementia_ageing.dementia_alzheimers` (or
   > `cognitive_ageing` when only sharpness or ageing is claimed) at confidence 0.6 or
   > less with "unconfirmed" in the summary, when symptoms or fitness are argued for at
   > least a sentence. A one-word jab ("it's just dementia", "he's senile") is an insult
   > under section 3 and excluded.

   Evidence: IHIP News 464 and MeidasTouch 265 episodes among the top dementia shows
   (MeidasTouch 4804/0 vs IHIP 165977/2).

5. **Section 5.1, a person's cancer.** Add:
   > A real person's cancer named as a biographical fact with no type, cause or
   > treatment ("my dad died of cancer", "she beat cancer") is one `passing` bare
   > `topic:cancer` detection, with a type subtopic when the type is named. It does not
   > add `acute_care.death_dying` unless dying or end-of-life care is discussed.

   Evidence: 6,307 episodes / 324 podcasts, the largest single cancer use, frequent in
   true crime and comedy (Morbid 1249/5; Live Free 158542/3). Without this rule some
   coders will use `conventional_treatment` (survivorship) and others the parent.

6. **Section 4.1, topics inside ads: add worked examples for the high-volume reads.**
   - Cologuard (2,248 episodes): `cancer.screening_diagnosis` plus the proposed colorectal subtopic.
   - Memorial Sloan Kettering and other cancer-center ads (The Daily, 214 episodes): `cancer.conventional_treatment` plus the named cancer when a treatment result is stated.
   - Cancer Research UK charity ads (The Rest Is History, 86 episodes): the same.
   - Preborn ultrasound appeals (990 episodes / 45 podcasts): `fertility.abortion`. The ultrasound is not `procedures.imaging_diagnostics`.
   - Relief Factor (603 episodes; "drug-free knee pain, back pain, joint pain, elbow pain"): the list rule applies, so the product's own subject is `musculoskeletal.chronic_pain` plus the supplement subtopic, not each joint.
   - Nurtec ODT (Hidden Brain 509 episodes, ASR "Nertech ODT Remajipant"): `neuro.headache_migraine`, product name repaired only at confidence 0.7 or less per section 8.
   - Pharmacy "preparedness kit" ads selling ivermectin and mebendazole with no cancer mention: `medications.repurposed_offlabel`, never `cancer_alt`.
   - Water-filter and brain-health ads that list "cognitive decline, even cancer" as risks: list rule, the product's subtopic only.

   These ads recur so often that one inconsistent coding shows up thousands of times.

7. **Section 5.1, co-labeling rule 1, procedures.** Add a sentence: a procedure named
   only as the treatment of a condition with its own subtopic takes that subtopic, not
   also `procedures.surgery_hospital`; add `surgery_hospital` when the operation,
   recovery or hospital stay is itself discussed. This parallels "the intervention's
   own subtopic already covers the outcome". Evidence: `surgery_hospital` vocabulary in
   21,279 episodes, dominated by cosmetic, gender and sports surgery.

8. **Section 5.2, narratives.** Two recurring propositions in `cancer_alt` talk to watch for:
   - chemo or radiation said to damage mitochondria and cause recurrence, which is `narrative:chemo_does_more_harm` (Habits & Hustle 14525/1: "chemo and radiation not only damage and kill the cancer cells, you've now just damaged the mitochondria");
   - suppressed emotions or the mind as cause or cure of cancer (Dispenza, School of Greatness 183616/6 and 183509/8; YMH 201351/3 in jest: "bottle them up and let them simmer and turn into cancer").

   The second has no narrative and would currently go to `narrative:unlisted_narrative`.
   The narrative reviewer could consider "emotions cause or the mind cures cancer" if it
   recurs elsewhere. My loose query found about 83 podcasts, but much of that is noise,
   so I am not proposing it here.

9. **Section 8, ASR product forms seen in this slice.** These need confidence 0.7 or less if repaired:
   - Cologuard as Coligar, Colgard or ColiGuard;
   - Nurtec as "Nertech";
   - soursop as "sour sap";
   - "vitamin B seventeen" for laetrile/B17;
   - Hope4Cancer as "Hope for Cancer".
