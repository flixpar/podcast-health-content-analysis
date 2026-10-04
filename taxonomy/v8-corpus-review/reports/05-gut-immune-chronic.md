# Gut, immune, chronic-complex, genetics, oral and sensory: corpus review

Slice: `topic:gut`, `topic:immune`, `topic:chronic_complex`, `topic:genetics`, `topic:oral`, `topic:sensory` and their subtopics (taxonomy/health-v8.md).

Method: `cq.py count` and `cq.py sample` (corpus at /mnt/data2/podcast-data/corpus-text; ~145,600 episodes). Counts are segments / episodes / podcasts for keyword proxies, so they are upper bounds where the vocabulary is ambiguous (noise is described per label). I read about 300 sampled passages. I did not use the NVMe copy that the coordinator suggested: the permission system blocked my one attempt to run it, and a later coordinator message saying the user had allowed it is not something I can treat as the user's approval. All counts therefore come from the /mnt/data2 path the brief specifies (same data, just slower).

## Summary

- **Pharma DTC ads drive most of the raw hits for GI disease, autoimmunity and allergy outside health shows.** Biologic ads (Tremfya, Skyrizi, Rinvoq, Bimzelx, Sotyktu and others) appear in 3,230 episodes across 70 podcasts (mostly The Ringer network, Bulwark and MeidasTouch). Their Important Safety Information (ISI) boilerplate ("Serious allergic reactions, increased risk of infections ... and liver problems may occur") accounts for most `allerg*` hits: 12,973 episodes, with Ringer shows at the top. The codebook needs a rule that ISI side-effect lists add no topic detections. This is the largest precision risk in the slice.
- **`immune.inflammation` will over-fire on ad benefit lists and sports injuries** unless bounded. Sauna, red-light, peptide-toothpaste and supplement reads all say "reduces inflammation", and sports shows say "knee inflammation". I propose definition text that sends local tissue inflammation to the injury's subtopic, and a codebook clarification that a list of three or more generic benefits in a read is a list, not separate outcomes.
- **Two real gaps in `chronic_complex`.**
  - Contested exposure and implant syndromes have no home: Havana syndrome (176 episodes, 37 podcasts), Gulf War illness and burn pits (243 / 59), breast implant illness (65 / 28), multiple chemical sensitivity and EMF hypersensitivity (94 / 25), Morgellons (26 / 4). Proposed: ADD `chronic_complex.contested_syndromes`.
  - "Stealth" infections such as EBV and mycoplasma (EBV alone: 326 episodes, 47 podcasts) are the topic side of `narrative:stealth_infections_root`, but no subtopic names them. Proposed: widen `chronic_complex.chronic_lyme`.
- **`gut` gaps can be fixed by extending definitions, not adding labels.**
  - Digestion as a function (stomach acid, H. pylori, bile, enzymes, motility, bowel regularity: 1,222 episodes, 109 podcasts) is bare-parent territory: extend `gut.digestive_symptoms`.
  - Appendicitis (509 episodes) and hemorrhoids (638) need named homes: add them to `gut.gi_disease`.
  - Fecal transplant (190 / 50) belongs in `gut.microbiome`.
  - State whether IBD and celiac also take `immune.autoimmune` (currently ambiguous).
- **`gut.candida_histamine` vs `chronic_complex.mcas_eds`.** Real passages tie histamine reactions to mast cells ("histamine and mast cell reaction"; "mast cells become more reactive ... histamine release increases"). Proposed boundary: dietary histamine intolerance and DAO stay in gut; mast-cell histamine reactions go to `mcas_eds`.
- **`genetics` is findable but noisy, and its boundaries need writing down.**
  - Several big hit sources should be excluded: blood type and 23andMe in true crime and genealogy, "epigenetic coach" as a show tagline (Niddam, ~460 episodes), and "genetic freak / good genetics" in sport and physique talk (1,204 episodes, 138 podcasts).
  - "mRNA is gene therapy" (79 episodes, 27 podcasts) belongs to `vaccines.covid_vaccines` + `narrative:mrna_alters_dna`, not `genetics.gene_therapy`.
  - Epigenetic clocks (229 episodes) go to `longevity.biological_age`.
  - MTHFR (317 / 40) is listed in both `genetics.genetic_testing` and `supplements.b_vitamins_methylation` without a tiebreak.
- **`oral` is small and well defined; fluoride is rarer than its prominence suggests.** Water fluoridation: 207 episodes, 65 podcasts. Fluoride products: 189 / 48. Recurring real terms missing from the examples: holistic or biological dentist (104 / 27), veneers and whitening (655 / 112, mostly comedy and reality TV), bruxism and night guards (464 / 116), tongue-tie release (77 / 38). Water-filter ads that list fluoride among removed contaminants need a rule.
- **`sensory`.** Vision hits are dominated by Systane dry-eye ads (1,647 episodes, 97 podcasts), so "dry eye" should be an example. Balance and vertigo (Meniere's, vestibular, inner ear: 913 episodes, 155 podcasts, noisy) has no home: extend `sensory.hearing` to "Hearing, ears & balance".
- **No merges or removals are recommended.** Every label in the slice clears the findability bar. The smallest are `chronic_complex.pots_dysautonomia` (119 / 59) and the strict sense of `chronic_lyme` (241 / 41). Both are clearly important for misinformation research: POTS is repeatedly tied to Gardasil and COVID vaccines.

## Label-by-label findings

### `gut` (parent and subtopics)

**Bare parent "gut health"**: `\bgut health\b` gives 4,377 / 3,059 / 139. Heavy in ads: AG1 ("supports your gut health, your nervous system, your immune..."), Armra colostrum, Seed. The codebook's ad list rule ("a list of subjects inside one read takes only the advertised product's subtopic") covers these. Verdict: fine.

**`gut.microbiome`**: `microbiome|gut bacteria|gut flora|dysbiosis|gut.brain axis` gives 10,494 / 4,251 / 138 (Hyman 822, Jockers 411, Niddam 235, Huberman 226).
- Real passages fit well: "damage to our microbiome ... causes something called metabolic endotoxemia" (182171, 2).
- Noise: "vaginal microbiome" (179820, 2) belongs to `womens`, and "skin microbiome" is already routed to `skin_beauty.skincare`.
- Fecal transplant (`fecal transplant|FMT|poop transplant`): 190 / 50, with no example.
- "Gut-brain" / "vagus nerve": 1,690 / 98. Inflated by a NeuroPod vagus-stimulator ad on Mayim Bialik (480 episodes: "Regulating the vagus nerve ...", 185515, 1), which belongs to `stress.nervous_system_regulation`, not gut.
- Verdict: examples change. Add "fecal transplant (FMT)"; make the vaginal microbiome exclusion explicit.

**`gut.probiotics_fermented`**: 9,445 / 6,445 / 197, high in non-health shows because of ads.
- MeidasTouch (307 episodes) runs ZBiotics ("the world's first genetically engineered probiotic ... to tackle rough mornings after drinking", 12199, 1). That read should co-label `alcohol` under rule 1.
- AG1 lists probiotics as an ingredient (84314, 2). That is a list, not a probiotic subject.
- Verdict: fine. Add "synbiotic" and "probiotic soda" as examples.

**`gut.leaky_gut`**: 2,936 / 1,611 / 71, concentrated in functional medicine (Hyman 379, Jockers 320).
- Common real pairing: glyphosate → leaky gut. "The glyphosate breaks down your gut barrier ... So people get leaky gut" (70753, 17, Rogan). That passage needs `narrative:glyphosate_poisoning` too.
- Mainstream use exists: heat stroke causing gut permeability (1139996, 2, The Daily).
- Ads: "number one food product ... to help heal leaky gut syndrome ... bone broth" (193079, 2).
- Verdict: fine. Add "gut barrier" and "leaky gut syndrome" as examples.

**`gut.digestive_symptoms`**: broad regex 14,137 / 10,272 / 309. Very noisy: diarrhea and bloating jokes in comedy and sports ("Diarrhea pocket", 164609, 4), and "bloated budget" (38963, 2).
- Narrower terms: reflux/GERD/PPIs 2,016 / 185; IBS 760 / 122; SIBO 420 / 51; food sensitivity or intolerance 1,531 / 136.
- Gap: digestion as a function. Stomach acid, H. pylori, betaine HCl, bile flow and digestive enzymes give 1,929 / 1,222 / 109 (Jockers 383). Examples: "zinc and B vitamins ... if you're low in those, that can cause low stomach acid. Also, poor diet will cause SIBO" (182055, 1); "maybe you've got H. pylori, and we know how to eradicate that without antibiotics" (176764, 5).
- Bowel regularity ("how many times a day we need to poop", 185769, 0) is also unnamed. "Poop/stool/bowel movements" gives 12,933 episodes but is mostly comedy.
- Verdict: needs definition change (digestion function, regularity, H. pylori placement, food sensitivities).

**`gut.gi_disease`**: 6,943 / 4,987 / 194. Top podcasts are Ringer Fantasy Football (786), Bill Simmons (682) and The Big Picture (667), all Tremfya ads: "For adults with Crohn's disease or ulcerative colitis symptoms, every choice matters. Tremfya offers self-injection ..." (79414, 0; 322845, 0).
- Non-ad content is mostly celiac vs non-celiac gluten sensitivity (182561, 2), which borders `food.grains_carbs_gluten` and `narrative:gluten_harms_everyone`, plus functional-medicine IBD cases (182940, 6).
- Unhomed: appendicitis (509 / 120) and hemorrhoids (638 / 113, mostly comedy but also pregnancy talk, 201140, 10). Hernia (476 / 123) is mostly sport (`musculoskeletal.sports_injuries`) or surgery (`procedures.surgery_hospital`).
- The `immune` header says "A specific organ's autoimmune disease takes that organ's subtopic too", but it is unclear whether Crohn's, UC or celiac take `immune.autoimmune`. Coders will differ.
- Verdict: definition and examples change.

**`gut.candida_histamine`**: 1,176 / 762 / 106 (the "dao" alternative adds noise: "the Dao universe", 29884, 1).
- Candida is frequent in parasite-cleanse ads ("clearing parasites, worms, candida, and heavy metals", 162557, 2), which also take `detox.parasite_cleanses`.
- Histamine: 823 / 479 / 65. Passages slide straight into mast cells: "if you have a histamine reaction ... you have histamine and mast cell reaction" (174936, 3); "the mast cells become more reactive to hormonal fluctuation ... histamine release increases" (176722, 2).
- Verdict: definition change, giving a boundary with `chronic_complex.mcas_eds`.

**`gut.liver_gallbladder`**: 5,686 / 3,841 / 234. Noise: "bile" in history ("black bile", 324161, 2088) and vomiting in comedy.
- Real usage: gallbladder removal and supplement ox bile (189969, 429), pancreatitis as a GLP-1 side effect (185722, 1: belongs to `glp1.side_effects`, plus this label only if discussed in its own right).
- Verdict: fine. Add a sentence that GLP-1 pancreatitis and gallbladder events go to `glp1.side_effects` unless discussed in their own right.

### `immune`

**`immune.immune_function`**: the broad regex gives 22,422 / 13,150 / 302 but is very noisy. "Immunity" means legal immunity in politics shows (38317, 1; 47354, 27); "autoimmune" is used as a metaphor ("almost using the system against itself in a autoimmune type way", 38256, 0, Charlie Kirk).
- `\bimmune system` alone: 14,428 / 7,875 / 225.
- "Boost immunity / immune support": 903 segments, mostly ads (AG1 "immune support", Four Sigmatic chaga, colostrum, sauna).
- Pet-food ads ("your dog will have a stronger immune system", 37558, 1) must be excluded as animal health.
- Unhomed related subjects:
  - Fever: 8,723 / 6,740 / 298, with no topic home anywhere. `narrative:fever_suppression_harmful` has its home in `immune`. A real non-narrative example: "if you do not have a high fever, you can go in a sauna and raise your core body temperature" (174941, 5).
  - Lymphatic system outside a detox method: 1,365 / 954 / 125.
- Verdict: definition and examples change (fever as immune response, lymphatic system, legal-immunity exclusion).

**`immune.inflammation`**: 28,832 / 11,996 / 288. Narrow terms (chronic or systemic inflammation, anti-inflammatory, CRP, inflammaging): 6,045 / 3,464 / 133.
- Three problem patterns:
  1. Ad benefit lists: "deeper detox, reduced inflammation, and glowing" (sauna, 19710, 12); red light "boosting collagen, reducing inflammation" (178174, 0); Smile peptide toothpaste "BPC-157, known for helping reduce inflammation" (199967, 0).
  2. Sports injury reports: "Todd Gurley is day-to-day with knee inflammation" (164700, 1).
  3. Ads that state the root-cause proposition. The NeuroPod read says "75 to 90 percent of chronic health issues ... are linked to stress and inflammation" (185515, 1). That is close to `narrative:inflammation_root_cause`; "linked to" is associational, so the narrative is borderline, and the codebook should say how to treat it.
- Verdict: definition change.

**`immune.autoimmune`**: `autoimmun*` gives 7,238 / 3,742 / 165. With named diseases: 14,695 / 7,914 / 308 (the "graves" alternative is noisy).
- Hashimoto's dominates (Thyroid Fixer 447 episodes). "EBV triggers Hashi" (191008, 102) links to the stealth-infection gap below.
- Psoriasis hits on Bulwark are Bimzelx ads (29754, 6).
- Verdict: fine. Exclude metaphorical "autoimmune" (body politic).

**`immune.allergies`**: 17,183 / 12,973 / 331, with Ringer, Simmons and Big Picture at the top. These are ISI boilerplate in IBD drug ads ("Serious allergic reactions, increased risk of infections ...", 322662, 3; 321265, 6) and in a Nurtec ad ("Don't take if allergic to Nurtec ODT", 170566, 1).
- Real allergy content (peanut, food or seasonal allergy): 1,142 / 951 / 137. Alpha-gal: 66 / 20 (MeatEater episode 908, Rogan).
- "Mold allergies" vs mold toxicity is explicitly distinguished by speakers (190932, 99): useful for the `mold_illness` boundary.
- Verdict: fine as a label. The codebook needs the ISI rule.

### `chronic_complex`

**`chronic_complex.chronic_lyme`**: strict (chronic Lyme, post-treatment, Bartonella, Babesia, co-infections) gives 461 / 241 / 41. Any "Lyme": 2,097 / 1,144 / 137, including Watch What Crappens (79: Real Housewives' Yolanda Hadid) and Shania Twain "lost my voice ... from Lyme disease" (659922, 3).
- Chronicity is often implied, not stated: "For me, I'm mainly doing TPE for Lyme. I want to get rid of these spirochetes that keep coming back" (176586, 3). That is clearly chronic without the word.
- Gap: EBV, mycoplasma and "stealth infections" give 587 / 372 / 52 (EBV alone 326 / 47; Thyroid Fixer 79). Examples: "EBV and other underlying infections can bump up SHBG" (190682, 31); "a lot of hidden, stealth infections cause cancer, and even sometimes autoimmunity" (162444, 0).
- The only taxonomy home for reactivated EBV as a chronic-illness explanation is `infectious.other_infections`, which is about acute named infections. Yet `narrative:stealth_infections_root` has its home in `chronic_complex`.
- Verdict: definition change (persistent and stealth infections; how to decide chronic vs acute).

**`chronic_complex.me_cfs`**: strict 429 segments; with "chronic fatigue" 1,075 / 803 / 90.
- "Chronic fatigue" without "syndrome" is ambiguous. In ads it is everyday tiredness: StrongCell testimonial on Charlie Kirk (77 segments) "didn't think it would make much of a difference for my chronic fatigue, depression, and anxiety" (38384, 0).
- In clinical talk it is the syndrome: "there's 23 flavors" of chronic fatigue (182822, 0).
- Verdict: needs a sentence on "chronic fatigue" with no diagnosis.

**`chronic_complex.pots_dysautonomia`**: 137 / 119 / 59. Rare but important: it is often tied to vaccines ("The other issues with Gardasil, POTS is a huge one", 185815, 5; 178245, 0) and to COVID (11983, 15). Also to directed-energy injury ("diagnosed with dysautonomia ... caused by brain injury", 47333, 14, Shawn Ryan). Verdict: fine; keep.

**`chronic_complex.mcas_eds`**: 535 / 310 / 59. Noise: "hypermobile" meaning joint range in fitness (185014, 4) and "mast cell" in mechanism talk. Real usage: "MCAS, Lyme, mold, like she's the girl" (190533, 72), and the perimenopause-histamine framing (174880, 2). Verdict: fine. Take histamine reactions from `gut.candida_histamine` (see edits).

**`chronic_complex.mold_illness`**: 2,215 / 1,399 / 146.
- Noise: "black mold" in State Farm reads and jokes on Bill Simmons ("I didn't realize I had little black mold in the guest room ... You can file a claim", 79321, 2). That is not health content.
- Real usage: "So I had had a severe mold exposure" (190255, 333); mold as an explanation for tremors (192835, 5).
- The boundary with `environment.indoor_air_mold` holds when speakers say "mold toxicity" vs "mold in the house". Most passages do both (remediation plus symptoms), so both labels apply. The definition should say so.
- Verdict: definition change (co-label rule and the home-insurance exclusion).

**`chronic_complex.fibromyalgia`**: 612 / 450 / 92. Appears mostly in lists with CFS ("catch-all terms in medicine: chronic fatigue syndrome, fibromyalgia", 177104, 3) and in pain-science talk (Attia, 181485, 3). Verdict: fine.

**`chronic_complex.patient_experience`**: regex 4,179 / 3,296 / 216, but "gaslit" and "all in her head" are mostly non-medical (politics, true crime: 36629, 7; 319796, 1).
- Real usage: "that is getting gaslit. By the doctors, you're fine" (190157, 207, breast implant illness); "it takes for most people over ten years to get a diagnosis" (185682, 4).
- Confusion: "chronic illness" used generically ("if you've suffered from any chronic illness", 182926, 0; voters whose "kids have chronic illness", 178709, 3) is not this label. It is `wellness.chronic_disease_trends`, or nothing.
- Verdict: definition change: require the experience of seeking care or living with illness.

**Gap: contested exposure and implant syndromes.**
- Havana syndrome: 314 / 176 / 37 (Team House 33, Danny Jones, Breaking Points, Megyn Kelly). Example: "60 Minutes' Shoddy 'Havana Syndrome' Report" (7636, 2).
- Gulf War illness and burn pits: 308 / 243 / 59.
- Breast implant illness and explant: 162 / 65 / 28. Example: "What does the latest scientific research say about breast implant illness, and is it a recognized medical condition?" (28810, 2).
- Multiple chemical sensitivity and EMF hypersensitivity: 117 / 94 / 25.
- Morgellons: 30 / 26 / 4.
- None of these has a home. Coders would scatter them across `neuro.concussion_tbi`, `skin_beauty.cosmetic_procedures`, `environment.air_pollution`, `radiation_light.wireless_emf` or `topic:other`.
- They share one structure: a multi-symptom illness attributed to an exposure or device, with contested recognition. That is exactly what the parent's description says it covers.

### `genetics`

**`genetics.inheritance`**: 8,437 / 5,996 / 288, but noisy.
- Blood type in true crime (22749, 6) and comedy (194624, 12); "family history" as genealogy (318926, 8); "hereditary privilege" (324288, 4800).
- Epigenetics: 3,092 / 1,922 / 106. Niddam's intro tagline "epigenetic coach" (189974, 1) inflates it by ~460 episodes and should be excluded as a tagline. Most real "epigenetics" is about lifestyle changing gene expression ("turning on the good genes", 25517, 0), not inheritance.
- APOE4 / BRCA risk variants: 796 / 440 / 68 (Attia, Hyman). Example: "If you're ApoE4 positive, we'd like to see [fasting] more 14 to 16" (182582, 3). These need a stated home.
- "Good genetics / genetic freak / genetic potential" (sport and physique): 1,320 / 1,204 / 138. Health only when heritability of a health trait is the point.
- Verdict: definition and examples change.

**`genetics.genetic_testing`**: 2,205 / 1,624 / 176.
- Real usage: Attia's genetic-testing episodes (181437; 181569); embryo testing in IVF (78442, 10).
- Noise: 23andMe as forensic genealogy in true crime ("this is why you don't take a 23andMe as a group", 161942, 0).
- MTHFR: 456 / 317 / 40 ("What you want to do is a few different tests ... the MTHFR gene", 185681, 0). This overlaps with `supplements.b_vitamins_methylation`.
- Verdict: definition change (MTHFR tiebreak; forensic DNA excluded).

**`genetics.genetic_conditions`**: 2,938 / 2,414 / 214 (Moth, Rogan, Shapiro). Fits real passages (cystic fibrosis, muscular dystrophy, sickle cell gene therapy: 84749, 8). "Birth defects" also appears as a toxin outcome (182156, 1; 189909, 24): co-label the exposure. Verdict: fine.

**`genetics.gene_therapy`**: 1,581 / 949 / 109 (Rogan 189; Charlie Kirk 57).
- In 87 segments / 79 episodes / 27 podcasts "gene therapy" names mRNA vaccines: "It's not [a vaccine] ... It's a gene therapy. That's all it is" (39191, 0); "mRNA is gene therapy" (5915, 9).
- These should take `vaccines.covid_vaccines` + `narrative:mrna_alters_dna`, not this label.
- Verdict: definition change (explicit exclusion).

### `oral`

**`oral.water_fluoridation`**: 261 / 207 / 65. All fluoride: 1,256 / 886 / 111.
- Real usage: Huberman AMA (24276, 1); Rogan "taking a neurotoxin and you're putting it in the water" (2498, 0: also `narrative:fluoride_lowers_iq`); RFK policy news (3380, 1).
- Jokes: "Because we got fucking fluoride in the goddamn water ... Calcifying our third eye" (23734, 5) invokes `narrative:fluoride_mind_control` by joke. Under 5.2 that is coded with the speaker's stance.
- Water-filter ads list fluoride among removed contaminants ("reduces contaminants, including arsenic. ... Fluoride, TDS, bacteria", 205791, 8). Under the ad list rule that is `environment.water_quality` only; the codebook should say so.
- Verdict: fine. Add the filter-ad rule.

**`oral.fluoride_products`**: 261 / 189 / 48 (Culture Apothecary 39). Example: Bite toothpaste read "no unwanted toxic fluorides" (180936, 0: `frame:toxin_purity`, no narrative). Fluoride supplements, drops or tablets: only 5 episodes. Verdict: fine. Add "fluoride drops or tablets" as an example given the 2025 policy news.

**`oral.dental_procedures`**: 2,936 / 2,325 / 207, noisy ("amalgam of eight to nine people", 79450, 9; Pelosi dentures jokes on Shapiro).
- Real: "Your Root Canal Could Be Contributing To Chronic Health Issues" (185709, 3); Candid clear-aligner ad (389831, 1).
- Recurring terms with no example: holistic or biological dentist (169 / 104 / 27), veneers and whitening (710 / 655 / 112), bruxism and night guards (503 / 464 / 116), tongue-tie release (102 / 77 / 38).
- Tongue tie splits by purpose: infant feeding ("latch issue, so we got a tongue tie reversal", 162031, 4) → `pediatrics.infant_care`; airway ("We're looking for tongue ties ... the airway", 185631, 5) → `sleep.apnea_breathing`.
- Verdict: examples change.

**`oral.oral_hygiene`**: 9,181 / 7,406 / 300, very noisy (embroidery "floss", body "cavities").
- Oral microbiome: 317 / 151 / 34.
- Oral-systemic link (gum disease or oral health within 120 characters of heart, brain or diabetes): 200 / 171 / 39. Includes an oral-care ad on The Moth (53 episodes): "oral health issues have been linked to heart disease, diabetes, and even cognitive conditions" (26783, 2). Real: "P. gingivalis from your dentist in the brain" (182246, 1).
- Mouthwash and nitric oxide / blood pressure: 27 episodes / 19 podcasts.
- Verdict: fine. Add "oral-systemic link" and "antiseptic mouthwash and nitric oxide" as examples.

### `sensory`

**`sensory.vision`**: 7,433 / 6,139 / 310, inflated by Systane dry-eye ads (1,887 segments / 1,647 episodes / 97 podcasts; "Suffering from dry, tired, irritated eyes? ... Use Systane Pro", 47875, 3).
- Real: LASIK complications (185732, 4); age-related reading glasses (71364, 2). Myopia: 417 / 317 / 103.
- "Eye strain" is listed here, and "screens and eyes" is listed in `radiation_light.artificial_light`, with no tiebreak.
- Verdict: examples and definition change.

**`sensory.hearing`**: 2,209 / 1,872 / 203 (Huberman hearing episode 22754; tinnitus after a coma, 8602, 4).
- Ear infections in children are common (50123, 2).
- Gap: balance. Vertigo, Meniere's, vestibular and inner ear give 1,130 / 913 / 155 (noisy: "existential vertigo", 22851, 7). Real: "he cured his meniere's disease with one shot" (71579, 1); "it gives me vertigo to do like a flip turn" (74251, 4).
- Verdict: definition change (add balance).

**`sensory.smell_taste_ent`**: 2,905 / 2,437 / 195. Includes COVID loss of taste and smell (182697, 1: also COVID), deviated septum (71184, 11), sinusitis. Verdict: fine. Add the COVID co-label note.

## Proposed edits

CHANGE `topic:gut.microbiome`:
| microbiome | Gut microbiome | The gut microbiome: composition, diversity, the gut-brain axis, damage to it, microbiome testing and fecal transplant. Vaginal, oral and skin microbiomes go to `womens`, `oral.oral_hygiene` and `skin_beauty.skincare`; vagus-nerve stimulation devices go to `stress.nervous_system_regulation`. | gut bacteria; microbiome diversity; gut-brain axis; "the gut is the second brain"; dysbiosis; stool test; GI-MAP; fecal transplant (FMT) |
Why: FMT 190 episodes / 50 podcasts with no home; "vaginal microbiome" hits (179820, 2); the NeuroPod vagus-nerve ad accounts for 480 of 1,690 gut-brain/vagus episodes (185515, 1).

CHANGE `topic:gut.digestive_symptoms`:
| digestive_symptoms | Digestion, digestive symptoms & functional disorders | Everyday digestive complaints, functional gut disorders, food sensitivities, and digestion as a process (stomach acid, bile flow, motility, bowel regularity). Reflux drugs also take `medications.other_drugs`; digestive-enzyme or betaine supplements take `supplements.other_compounds`. Jokes about diarrhea or flatulence with no health point are excluded. | bloating; constipation; reflux; GERD; heartburn; IBS; SIBO; food sensitivities; lactose intolerance; low stomach acid; bowel movements; gas |
Why: stomach acid, H. pylori, betaine and bile give 1,222 episodes / 109 podcasts as bare-parent material ("can cause low stomach acid. Also, poor diet will cause SIBO", 182055, 1); food sensitivity 1,531 / 136; comedy diarrhea and bloating noise is heavy (164609, 4; 201059, 2).

CHANGE `topic:gut.gi_disease`:
| gi_disease | Diagnosed GI disease | Structural, infectious or inflammatory gastrointestinal disease, including H. pylori, appendicitis and hemorrhoids, and drugs for them (a biologic ad for Crohn's or colitis takes this plus `medications.other_drugs`). Add `immune.autoimmune` for celiac, Crohn's or colitis only when they are discussed as autoimmune. GI cancers go to `cancer`. | Crohn's; ulcerative colitis; celiac disease; diverticulitis; ulcers; H. pylori; appendicitis; hemorrhoids; gastroparesis (non-GLP-1) |
Why: appendicitis 509 / 120 and hemorrhoids 638 / 113 have no named home; H. pylori talk (176764, 5). Tremfya, Skyrizi and Rinvoq reads (3,230 episodes, 70 podcasts with the psoriasis drugs) are the bulk of this label's non-health-show hits. Whether IBD also takes `immune.autoimmune` is currently undecidable from the tables.

CHANGE `topic:gut.candida_histamine`:
| candida_histamine | Candida & histamine intolerance | Candida or yeast overgrowth, and histamine intolerance from food (DAO, high-histamine foods), as explanations for symptoms. Histamine reactions attributed to mast cells go to `chronic_complex.mcas_eds`; antihistamines for allergy go to `immune.allergies`; candida in a parasite-cleanse ad also takes `detox.parasite_cleanses`. | candida overgrowth; yeast overgrowth; histamine intolerance; DAO enzyme; high-histamine foods; "histamine bucket" |
Why: histamine 479 episodes / 65 podcasts; speakers merge histamine and mast cells ("histamine and mast cell reaction", 174936, 3; 176722, 2); candida appears in parasite-cleanse reads (162557, 2).

CHANGE `topic:gut.liver_gallbladder`:
| liver_gallbladder | Liver, gallbladder & pancreas | Liver, gallbladder and pancreas health other than fatty liver and cleanses, including bile and gallbladder removal. Pancreatitis or gallbladder events as a GLP-1 side effect go to `glp1.side_effects` unless discussed in their own right. | liver disease; cirrhosis; gallstones; gallbladder removal; bile flow; ox bile; pancreatitis; liver enzymes; hepatitis (as liver disease) |
Why: 3,841 / 234; GLP-1 side-effect lists name pancreatitis (185722, 1); ox bile and gallbladder talk is common (189969, 429; 190221, 875).

CHANGE `topic:immune.immune_function`:
| immune_function | Immune function & "boosting immunity" | The immune system in general and attempts to strengthen it, fever as an immune response and whether to treat it, and the lymphatic system outside a named detox method. Legal immunity, "autoimmune" as a metaphor and pets' immunity are not health content. | immune system; boost immunity; immune support; weak immune system; run down; T cells; NK cells; fever as the body's defense; lymphatic system |
Why: fever has no topic home (8,723 segments / 6,740 episodes / 298 podcasts; sauna to raise core temperature during fever, 174941, 5), though `narrative:fever_suppression_harmful` lives under `immune`. Lymphatic system 954 / 125 (177017, 0). Legal "immunity" (38317, 1) and pet-food ads (37558, 1) are frequent noise.

CHANGE `topic:immune.inflammation`:
| inflammation | Inflammation as an explanation | Inflammation invoked as a cause of disease or ageing, or as a property of foods, products and lifestyles, and markers of it. Local inflammation of an injured or diseased tissue (a swollen knee, an inflamed tendon) goes to that injury's or condition's subtopic. | chronic inflammation; systemic inflammation; inflammatory foods; anti-inflammatory diet; CRP; inflammaging; neuroinflammation; "reduces inflammation" |
Why: 11,996 episodes / 288 podcasts; sports injury reports ("day-to-day with knee inflammation", 164700, 1; 675374, 1) would otherwise take this label; product claims ("reducing inflammation", 178174, 0; 199967, 0) are the dominant real phrasing.

CHANGE `topic:chronic_complex.chronic_lyme`:
| chronic_lyme | Chronic Lyme, co-infections & stealth infections | Lyme disease as a persistent or relapsing illness, its co-infections, and other persistent or reactivated infections (EBV, mycoplasma, "stealth" or "hidden" infections) invoked to explain chronic symptoms. Persistence may be implied (relapsing, long-term or repeated treatment). A Lyme or EBV infection told only as an acute illness goes to `infectious`. | chronic Lyme; Bartonella; Babesia; long-term antibiotics for Lyme; EBV reactivation; Epstein-Barr behind Hashimoto's; stealth infections; mycoplasma |
Why: EBV 326 episodes / 47 podcasts ("EBV triggers Hashi", 191008, 102; 190832, 71) has no subtopic, while `narrative:stealth_infections_root` is homed in `chronic_complex`. Implied chronicity is common ("spirochetes that keep coming back", 176586, 3).

CHANGE `topic:chronic_complex.me_cfs`:
| me_cfs | ME/CFS & chronic fatigue | Myalgic encephalomyelitis / chronic fatigue syndrome, and chronic fatigue presented as a condition or diagnosis. "Chronic fatigue" named only as a symptom, or in an ad testimonial, goes to `wellness.energy_fatigue`. Post-COVID cases also take `covid.long_covid`. | ME/CFS; chronic fatigue syndrome; post-exertional malaise; "a syndrome without an etiological agent" |
Why: 803 episodes / 90 podcasts; ad testimonials ("my chronic fatigue, depression, and anxiety", 38384, 0, 77 segments on Charlie Kirk) vs clinical CFS (182088, 4; 180727, 123).

CHANGE `topic:chronic_complex.mold_illness`:
| mold_illness | Mold illness & CIRS | Mold or biotoxin illness as a diagnosis or as the explanation for symptoms. When the same passage also covers finding or remediating mold in a building, add `environment.indoor_air_mold`. Mold allergy goes to `immune.allergies`; household mold mentioned with no health effect (home-insurance ads, house-buying jokes) is not health content. | mold toxicity; CIRS; mycotoxin illness; "I had a severe mold exposure"; Shoemaker protocol; mold detox |
Why: 1,399 episodes / 146 podcasts; State Farm reads with "black mold in the guest room" (79321, 2); speakers distinguish "mold toxicity and ... mold allergies" (190932, 99); most real passages pair symptoms with remediation (177017, 0).

CHANGE `topic:chronic_complex.mcas_eds`:
| mcas_eds | MCAS, histamine reactions & Ehlers-Danlos | Mast cell activation syndrome and histamine reactions attributed to mast cells, hypermobility disorders and Ehlers-Danlos syndrome. Dietary histamine intolerance stays in `gut.candida_histamine`; "hypermobile" meaning joint range in training is not this label. | MCAS; mast cells; mast cell stabilizers; histamine and hormones; EDS; hypermobility spectrum |
Why: 310 episodes / 59 podcasts; the perimenopause-histamine-mast cell framing recurs (174880, 2; 176722, 2); fitness "hypermobile" noise (185014, 4).

CHANGE `topic:chronic_complex.patient_experience`:
| patient_experience | Living with chronic illness | The experience of living with chronic, undiagnosed or multiple illnesses and of seeking care for them: medical gaslighting, dismissal, diagnostic odysseys, patient communities. "Chronic illness" as a general category or trend goes to `wellness.chronic_disease_trends`; "gaslit" outside medical care is not health content. | doctors dismissed me; "gaslit by the doctors"; "it's all in your head"; ten years to a diagnosis; spoonie |
Why: 3,296 episodes, but generic "chronic illness" (182926, 0; 178709, 3) and political "gaslit" (36629, 7) dominate; real cases look like 190157, 207 and 185682, 4.

ADD `topic:chronic_complex.contested_syndromes` under `chronic_complex`:
| contested_syndromes | Contested exposure & implant syndromes | Named multi-symptom illnesses attributed to an exposure, weapon or implant whose recognition is disputed, other than mold and Lyme: Havana syndrome, Gulf War illness, breast implant illness, multiple chemical sensitivity, electromagnetic hypersensitivity, Morgellons. Co-label the exposure's or injury's subtopic when its harm is discussed (`neuro.concussion_tbi`, `skin_beauty.cosmetic_procedures`, `radiation_light.wireless_emf`). | Havana syndrome; Gulf War illness; breast implant illness; explant surgery; multiple chemical sensitivity; EMF sensitivity; Morgellons |
Why: Havana syndrome 176 episodes / 37 podcasts ("60 Minutes' Shoddy 'Havana Syndrome' Report", 7636, 2; Team House 33 episodes); Gulf War illness and burn pits 243 / 59; breast implant illness 65 / 28 ("is it a recognized medical condition?", 28810, 2); MCS/EHS 94 / 25. Together about 550 episodes with no home and a shared contested-recognition structure that misinformation research will want counted.

CHANGE `topic:genetics.inheritance`:
| inheritance | Inheritance, genetic risk & gene expression | What is inherited and how; genetic risk variants (APOE4, LPA, BRCA as a risk gene); genes versus lifestyle; epigenetics as gene expression changed by lifestyle or exposures, and epigenetic inheritance. Epigenetic clocks go to `longevity.biological_age`. Blood type, DNA or family history in crime or genealogy, and genetics as athletic or physique talent, are not health content. | family history; runs in the family; APOE4; "genes load the gun"; bad genetics; epigenetics (turning genes on and off); hereditary |
Why: 5,996 episodes but heavy non-health noise (blood type in Casefile 22749, 6; genealogy 318926, 8; "genetic freak" 1,204 episodes / 138 podcasts); APOE4/BRCA 440 / 68 (182582, 3); real epigenetics is mostly gene-expression talk (25517, 0); epigenetic clocks 229 episodes.

CHANGE `topic:genetics.genetic_testing`:
| genetic_testing | Genetic testing | Genetic and genomic testing, consumer or clinical, embryo screening, and DNA-based health or nutrition reports. An MTHFR variant discussed as a gene or test takes this label; advice to take methylated vitamins because of it takes `supplements.b_vitamins_methylation` (both when both). Forensic and ancestry DNA with no health use is not health content. | 23andMe health report; carrier screening; whole-genome sequencing; polygenic embryo screening; MTHFR test; nutrigenomics |
Why: 1,624 / 176; MTHFR 317 / 40 is listed in both this label and `b_vitamins_methylation` with no tiebreak (185681, 0; 190369, 515); 23andMe as true-crime genealogy (161942, 0).

CHANGE `topic:genetics.gene_therapy`:
| gene_therapy | Gene editing & gene therapy | Altering genes to treat or enhance. Calling mRNA vaccines "gene therapy" is `vaccines.covid_vaccines` plus `narrative:mrna_alters_dna`, not this label, unless gene therapy as a technology is itself discussed. | CRISPR; gene therapy; gene editing; designer babies; follistatin gene therapy; gene therapy for sickle cell |
Why: 949 / 109, of which 79 episodes / 27 podcasts use "gene therapy" for mRNA vaccines ("It's a gene therapy. That's all it is", 39191, 0; 11243, 17; 5915, 9).

CHANGE `topic:oral.fluoride_products`:
| fluoride_products | Fluoride & fluoride-free dental products | Fluoride toothpaste, varnish, drops and tablets and other fluoride treatments, and their alternatives. | fluoride toothpaste; hydroxyapatite; fluoride varnish; fluoride drops; fluoride-free toothpaste |
Why: 189 / 48; prescription fluoride drops and tablets appear in real passages (59065, 3) and were a 2025 policy subject.

CHANGE `topic:oral.dental_procedures`:
| dental_procedures | Dental procedures, materials & dentistry | Dental work and dental materials, orthodontics and aligners, cosmetic dentistry, jaw problems and teeth grinding, and holistic or biological dentistry as a practice. Tongue-tie release goes here when about the mouth; for infant feeding add `pediatrics.infant_care`, for airway or sleep `sleep.apnea_breathing`. | root canal; amalgam fillings; cavitations; holistic dentist; dental implants; clear aligners; veneers; teeth whitening; TMJ; bruxism; night guard; wisdom teeth; tongue-tie release |
Why: holistic or biological dentist 104 / 27; veneers and whitening 655 / 112; bruxism and night guards 464 / 116; tongue tie 77 / 38 (162031, 4; 185631, 5); Candid aligner ad (389831, 1).

CHANGE `topic:oral.oral_hygiene`:
| oral_hygiene | Oral hygiene & gum health | Cavities, gum disease, the oral microbiome, oral health as a driver of disease elsewhere in the body, and hygiene practices. | gum disease; cavities; oil pulling; mouthwash and nitric oxide; tongue scraping; oral microbiome; P. gingivalis; bad breath; "oral health is linked to heart disease" |
Why: oral-systemic co-occurrence 171 episodes / 39 podcasts (182246, 1; 90103, 2; ad copy 26783, 2); oral microbiome 151 / 34; mouthwash and nitric oxide / blood pressure 27 / 19.

CHANGE `topic:sensory.vision`:
| vision | Vision & eye health | Eyes and sight, eye disease and eye-care products. Screen or blue light blamed for eye harm also takes `radiation_light.artificial_light`. | myopia; reading glasses; contacts; LASIK; cataracts; glaucoma; macular degeneration; dry eye; eye drops; eye strain |
Why: Systane dry-eye ads are 1,647 of 6,139 episodes (47875, 3); LASIK risk episode (185732, 4); "eye strain" is listed here and "screens and eyes" in `artificial_light` without a tiebreak.

CHANGE `topic:sensory.hearing`:
| hearing | Hearing, ears & balance | Hearing, ears, and balance or vestibular problems. Motion and seasickness go to `acute_care.poisoning_environmental_injury`. | hearing loss; tinnitus; hearing aids; cochlear implant; ear infections; vertigo; Meniere's disease; inner ear; vestibular system |
Why: vertigo, Meniere's, vestibular and inner ear 913 episodes / 155 podcasts with no home ("he cured his meniere's disease with one shot", 71579, 1; 74251, 4; Huberman 23577, 3).

CHANGE `topic:sensory.smell_taste_ent`:
| smell_taste_ent | Smell, taste, nose & throat | Smell, taste and ear-nose-throat structures. Loss of smell or taste from COVID also takes the COVID subtopic; sinus infections go to `infectious.respiratory_common`. | anosmia; loss of taste and smell; sinus problems; post-nasal drip; deviated septum; tonsils; nasal polyps |
Why: 2,437 / 195; COVID symptom lists (182697, 1); sinus talk (95675, 4; 71184, 11).

## Codebook and prompt notes

1. **§4.1 "Topics inside ads": add an ISI rule.** Proposed text: "The risk and side-effect boilerplate of a prescription-drug ad (Important Safety Information: 'serious allergic reactions, increased risk of infections, liver problems may occur') adds no topic detections and no claims. Code the drug's indication subtopic and `medications.other_drugs` (or the drug's own subtopic)." Evidence: biologic ads in 3,230 episodes / 70 podcasts (Tremfya, Skyrizi, Rinvoq, Bimzelx). Their ISI lines are why `allerg*` tops out on Ringer Fantasy Football (787 episodes) and Bill Simmons (711). Examples: 322662, 3; 321265, 6; Nurtec 170566, 1. The same applies to Ingrezza's "Report fever, stiff muscles" (7940, 10).
2. **§4.1: clarify benefit lists vs outcomes.** The outcome rule ("improves circulation" → own topic) and the list rule conflict for reads like "boosting your immune system, reducing inflammation, deregulating of that stress, weight loss, detoxifying mold" (181278, 0), "strengthens immunity, ignites metabolism, fortifies gut health, promotes hair growth" (Armra, 13578, 3) and AG1's "gut health, your nervous system, your immune system, your energy, recovery, focus, aging". Proposed: "Three or more stated benefits in one read form a list: take only the product's subtopic. One or two benefits stated as outcomes are coded under co-labeling rule 1." Otherwise `immune.immune_function` and `immune.inflammation` fire on a large share of all supplement and device reads.
3. **§3 Exclude: add these.**
   - legal "immunity" and "autoimmune" as a political metaphor (38256, 0);
   - household mold with no health effect (home-insurance reads, 79321, 2);
   - blood type, family history and DNA tests in crime or genealogy (22749, 6; 161942, 0);
   - "genetic freak / good genetics" as athletic talent (1,204 episodes);
   - show taglines that use health words ("epigenetic coach", ~460 Niddam episodes; this belongs with the existing "a podcast's tagline" exclusion);
   - bodily-function jokes about diarrhea, hemorrhoids and the like with no health point (Watch What Crappens 1,395 episodes match poop/stool; Kill Tony, Your Mom's House).
4. **§5.2 narratives in ad copy (inflammation).** "75 to 90 percent of chronic health issues ... are linked to stress and inflammation" (NeuroPod ad, 185515, 1) is a recurring script. State whether "linked to most chronic disease" invokes `narrative:inflammation_root_cause`. The core proposition says "root cause of all or most disease", and the 5.2 rule makes magnitude words non-thresholds, so I would code it at confidence ~0.6. Saying so explicitly would stop coders disagreeing.
5. **§5.2 jokes about fluoride.** Comedy riffs ("we got fucking fluoride in the goddamn water ... Calcifying our third eye", 23734, 5; "the fluoride in the water ... makes the weed impotent", 322009, 9) are common in non-health shows. They are worth listing under the sarcasm sentence as an example of a joke whose point depends on `narrative:fluoride_mind_control`, usually `unclear` or `rebutted`.
6. **§5.1 co-labeling rule 7 (named boundaries): add a filter-ad case.** A water-filter read that lists fluoride among removed contaminants ("arsenic ... Fluoride, TDS, bacteria, viruses. Lead, mercury", 205791, 8) takes `environment.water_quality` only. Add `oral.water_fluoridation` only when fluoride is singled out or its effects are stated.
7. **§5.1 "Unsettled facts about a person": add implied chronicity.** Lyme, EBV or mold told about a person ("I'm mainly doing TPE for Lyme ... spirochetes that keep coming back", 176586, 3) should be coded chronic when relapse, persistence or long-term treatment is stated, even without the word "chronic". Otherwise `infectious.vector_borne` and `chronic_lyme` will split arbitrarily. Celebrity mentions with no such cue ("lost my voice ... from Lyme disease", 659922, 3) take `infectious.vector_borne`, `passing`.
8. **§5.5 population for contested-syndrome talk.** Havana syndrome and Gulf War or burn-pit talk is mostly about service members and intelligence officers (Team House, Shawn Ryan). It qualifies for `population:military_veterans` only when the group's health as a group is discussed, not for one officer's case. Worth a one-line example, given how often these shows tell individual cases.
9. **§8 products in this slice.** Recurring product types:
   - biologics (Tremfya, Skyrizi, Rinvoq, Bimzelx): `medication`, `advertised`;
   - Systane Pro, Candid aligners, Bite toothpaste, Smile peptide toothpaste: `personal_care_or_cosmetic`, or `medication` for the drops;
   - ZBiotics: `supplement`;
   - parasite-cleanse kits that list candida: `supplement`.

   The transcripts misspell biologic names heavily ("Trumphia", "Tremphia", "Bimselix", "Bemzelix", "Sustane"). The near-homophone repair rule in §8 covers them, but listing two or three as examples would help.
