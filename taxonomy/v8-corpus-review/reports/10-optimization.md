# Fitness, performance & optimization (fitness, recovery, peds, longevity, biohacking, self_tracking, digital_health): corpus review

Method. One pass of `cq.py sample` with a union of every slice term (317,525 matching segments) was saved locally and split per term. Spot checks used `cq.py count/sample`. Counts are segments / episodes / podcasts. Segments are long (often several minutes of speech), so segment counts are coarse. Many raw counts are inflated by recurring sponsor reads or cross-promos, and these are flagged where they dominate. "Health-sense" shares are judged from samples I read, not measured.

## Summary

- **The sport-vs-health line needs explicit wording.** About 13,000 episodes come from sports shows (Pardon My Take, Fantasy Footballers, Ringer, Simmons, McAfee). Their "training"-type vocabulary is overwhelmingly competition talk. "Training camp" means the calendar (PMT 792 eps, Fantasy Footballers 635 eps). So do "workload", "snap count" and "pitch count" (player usage), and "he's way out of shape" (an evaluation). Yet `fitness.sports_performance` lists "training camp" as an example. I propose a section-3 rule saying what makes sports talk health content, and a rewritten `sports_performance` row. The real health talk in sports shows is about weight cutting, conditioning regimens, TB12/pliability, PED accusations and injuries.
- **Incidental exercise mentions are the biggest false-positive risk in the slice.** "Gym", "workout" and "yoga" appear in 25k, 48k and 9k episodes across 430–530 podcasts. Most of these are scene-setting ("before I hit the gym" in a YouTube ad, "yoga pants", "gym rat"), idiom ("how's that working out") or bedtime stories. The codebook has no rule for exercise named only as a setting.
- **Idioms and acronyms that collide with slice labels.** "X on steroids" is an intensifier (2,311 eps, 200 pods). "Tren" is mostly Tren de Aragua. "DNP" in sports shows means "did not play". "AI" in TRT talk means aromatase inhibitor. "Whoop" is mostly an interjection. "Don't die" (1,808 eps) is almost never Bryan Johnson. "Longevity" is very often a purpose word or tagline ("good for longevity", "praying for your health and longevity"). These belong in the codebook's exclusion examples.
- **ASR variants decide findability for named products.** "Oura" appears literally in 94 eps, but "Aura ring" brings it to 712 eps / 102 pods. "Bryan Johnson" appears in 7 eps, against 509 for "Brian Johnson" (some are other people). The examples should carry these spellings.
- **Ad copy drives the digital_health and self_tracking counts.** Amazon Health AI ads alone run in 3,022 eps / 43 pods (School of Greatness 1,962). Hers' "AI responses … do not constitute a medical diagnosis" disclaimer runs about 900 Armchair Expert eps. NeuroPod (an ear-worn vagus-nerve stimulator) and iRestore red-light ads each run about 460–490 Mayim Bialik eps. Hyman's boilerplate naming Function Health runs about 355 eps. Organic consumer-AI-for-health talk is small (about 100 segments). The codebook should say that boilerplate disclaimers naming a company or AI do not trigger these subtopics.
- **One new subtopic: `recovery.training_recovery`.** Recovery from exercise as such (soreness, DOMS, deload, rest days, "post-workout recovery" as an ad outcome) recurs in about 1,100–1,500 eps / 110–148 pods and has no home. The recovery parent covers only modalities. Ads use it constantly as a stated outcome (protein shakes, creatine, sleep supplements, NAD+ "for recovery and stamina").
- **Merge `peds.fat_loss_drugs_ped` into `weight.diet_pills_fat_burners`.** After removing "DNP = did not play", genuine clenbuterol, DNP or ephedrine talk is under 100 eps, and much of that is not PED use (cold-medicine pseudoephedrine, history). The weight subtopic already covers "any pill … taken for weight loss".
- **Example fixes with evidence.** In `heat_sauna`, "hot tub" is mostly a social setting (2,466 eps). In `practice_culture`, "optimal not normal" is functional-lab-range talk (378 eps). In `devices_gadgets`, "light glasses" conflict with the sleep and light tables. In `body_scans`, DEXA is overwhelmingly body-fat or bone-density talk (530 eps). In `stacks_protocols`, "morning routine" is mostly self-help and ads (3,041 eps). `health_apps`' "digital therapeutics" appears in 9 eps.
- **`digital_health.ai_advice` should cover chatbot mental-health harms.** That means AI psychosis, chatbot-linked suicide and AI companions, about 140–350 eps across about 90 pods, including Pivot, Fresh Air, Today Explained and The Journal. `online_health_information` should name "Dr. Google"/WebMD searching (353 eps / 115 pods) and fitness influencers.
- **Cross-slice gap for the gender owner: trans athletes in women's sports.** This runs to 1,799 eps / 106 pods, and 1,081 eps co-occur with physiology or injury terms (testosterone, puberty, bone density, injury). There is no label for it. A proposed row is given below.

## Label-by-label findings

### topic:fitness (Exercise & Fitness)

**`fitness.strength_training`**
- Query: `\b(weight ?lifting|lifting weights|lift(ing)? (heavy|weights)|resistance training|strength training|hypertrophy|progressive overload|deadlifts?|bench press(ing)?|kettlebells?|powerlifting)\b`.
- Counts: 16,762 / 8,564 / 256 (JRE 1,137; Mind Pump 934; Modern Wisdom 360; Pardon My Take 317; Huberman 244).
- Bodybuilding, physique and bulking: 8,255 / 4,889 / 226.
- Verdict: **fine, examples change.** "Women lifting" is rare (30 eps / 22 pods). The real phrasing is "lift heavy", "resistance training", "bodybuilding" and "bulking".
- The muscle_loss boundary holds in the samples. Example: "lifting weights" as a lever for muscle with age (55275/2194).
- Not health content: a true-crime suspect "running sprints, doing yoga, lifting weights … practicing jumping" to stage an escape (23196/5). This is exercise as plot.

**`fitness.cardio_endurance`**
- Counts:
  - Cardio, aerobic, HIIT, interval training, Zone 2, VO2: 9,230 / 5,526 / 199.
  - Zone 2: 792 / 503 / 73.
  - VO2 max: 1,004 / 548 / 59 (Attia, JRE, Hyman, Niddam, Huberman).
  - Running terms: 12,854 / 10,066 / 365, noisy ("marathon" is mostly TV binge talk on Watch What Crappens).
- Verdict: **fine.** Real phrasing includes "zone two cardio … 150 to 180 minutes" (78773/11).
- VO2 max is very often framed as a longevity predictor ("VO2 max decreases as individuals age", 175189/2). Rule 1 then requires `longevity.ageing_science` as well. The current example "exercise for longevity" in `exercise_general` invites coders to skip that co-label (see the proposed edit).

**`fitness.daily_movement`**
- Query: steps, walking after meals, rucking, sedentary, standing desk, "new smoking".
- Counts: 4,032 / 2,891 / 182.
  - Steps: 853 eps / 115 pods.
  - Walk after meals: 176 / 53.
  - Rucking: 143 / 35 (Attia, JRE, Team House, Shawn Ryan).
  - "Sitting is the new smoking": 70 / 35.
  - Weighted vest: 198 eps / 63 pods (Brecka, JRE, Habits and Hustle). It is not listed.
- Verdict: **fine; add "weighted vest".**

**`fitness.mobility_flexibility`**
- Counts:
  - Yoga: 9,432 eps / 288 pods.
  - Pilates: 1,511 / 160.
  - Tai chi: 372 / 98.
  - Stretching: 5,772 / 280.
  - Mobility: 3,938 / 234 (noisy: social mobility, history).
- Verdict: **fine as a label.** A large share of yoga and Pilates hits are incidental. Get Sleepy stories account for 692 yoga eps and Watch What Crappens for 475. Examples: "I do like you doing yoga" (74621/4), a Lululemon ad for "a lightweight, low compression yoga solution" (94338/1), and Housewives scenes. See the codebook note on incidental exercise.

**`fitness.sports_performance`**
- Query: athletic performance, overtraining, sports science, training camp.
- Counts: 6,512 / 4,472 / 175, with sports shows dominant (PMT 792, Fantasy Footballers 635, Ringer FF 268).
- Verdict: **needs a definition and examples change.** In every sports-show sample I read, "training camp" was a calendar or roster event ("Watch him in training camp because…", 323069/4; "near the end of training camp", 163598/1).
- Genuine sport-health material this label should catch:
  - Weight cutting for weigh-ins. Query `weight cut(ting)?|cutting weight`: 844 / 520 / 56, JRE 357. Examples: "We just got done cutting weight" (13523/7); "make that weight cut … eating as many carbs as possible" (28984/3). Note that "making weight" is mostly a Farmer's Dog ad ("making weight management easy", 10879/1), which is animal health and excluded.
  - Overtraining. Example: "Junior Dos Santos was overtrained … they had measured his creatine levels" (71160/12).
  - Athletes' body-care regimens: TB12 and pliability appear in 293 eps / 59 pods, 74 of them PMT and 46 Simmons. Examples: "the pliability and the way he takes care of his body, I actually think he is a faster person now" (322938/2); "he's got TB12. He sells … potions" (79743/7).
- Not health content: "I know you're on the pitch count" (80076/10), "he's going to get a full workload" (322922/0), and "He's. Way out of shape, and it doesn't totally affect him" (79233/1, an evaluation).
- Borderline: "I lost ten pounds to get to two ninety … 250, which is what I played at" (79674/2). This is a weight change as a fact about a person, which existing 5.1 makes bare `topic:weight` passing.

**`fitness.exercise_general`**
- Counts:
  - "Exercise": 61,487 / 34,437 / 479, very noisy ("exercise caution", "exercising powers"; Ben Shapiro 2,160 eps).
  - "Physical activity": 2,095 / 1,675 / 194.
  - "Minimum effective dose": 164 / 137 / 36.
  - "Exercise is medicine": 33 / 30 / 12, rare.
- Verdict: **examples change.** Use real phrasing, and remove "exercise for longevity" so it no longer reads as covering the longevity outcome by itself.

**Grip strength** (a fitness metric with no example): 654 / 496 / 80 (Mind Pump 103, Attia 32). Add it as an example to `strength_training`, the "fitness metrics" in the parent definition.

### topic:recovery (Recovery & Physical Modalities)

**`recovery.cold_exposure`**
- Counts:
  - Plunge, ice bath, cryotherapy, immersion, "cold exposure": 4,632 / 3,233 / 166.
  - Cold showers: 1,334 / 1,064 / 136.
  - Wim Hof: 662 / 497 / 69.
- Verdict: **fine.** Real phrasing includes "deliberate cold exposure" (Huberman) and "cold plunge, hot sauna" as a pair.
- Huberman's newsletter boilerplate lists "deliberate cold exposure" among toolkits in many episodes (24474/20). It is a lead-magnet list, so under rule 6 it takes no topic per item.

**`recovery.heat_sauna`**
- Counts: sauna or heat shock: 6,356 / 4,028 / 196; heat shock proteins: 250 eps / 41 pods.
- Verdict: **examples change.** "Hot tub" (2,980 / 2,466 / 211) is overwhelmingly a social setting: Watch What Crappens 551 eps ("Kristen was in the hot tub drinking alone", 95931/2) and true crime (161056/1).

**`recovery.red_light`**
- Counts: 7,519 / 5,055 / 249, noisy ("run a red light").
- The iRestore LED mask ad runs in about 460 Mayim Bialik eps: "The LED light therapy makes a noticeable difference in lines" (185168/3). That is skin plus light therapy.
- Laser cap (12 eps) and LED mask (15 eps) are rare as phrases but present in ads.
- Verdict: **fine.**

**`recovery.hyperbaric`**
- Counts: 1,779 / 854 / 112.
- Verdict: **fine.** It often sits inside clinic bundles: "The Longevity Circuit at Next Health using hyperbaric oxygen. Sauna, cryotherapy, and LED light" (176678/6). That bundle takes the modalities plus `longevity.protocols_clinics`.

**`recovery.bodywork_compression`**
- Counts: 471 / 365 / 77; compression boots 23 eps.
- Verdict: **rare but fine.** The Theragun founder (28504/2) and foam rollers in ads (189254/1) appear.

**Gap: training recovery.**
- Query `(muscle|post-?workout|workout|exercise|active) recovery|recovery (days?|tools?|scores?|modalities)`: 1,256 / 1,092 / 110.
- Query `doms|delayed onset muscle soreness|muscle soreness|sore muscles|post-workout recovery|muscle recovery|recovery days?|rest days?|deload`: 1,788 / 1,567 / 148.
- It is very common as an ad outcome:
  - "Post-workout recovery is a big factor. Core Power Protein Shakes help…" (502516/15).
  - A sleep supplement: "my post-workout muscle recovery has been incredible" (176979/5).
  - Creatine "for improving strength, muscle recovery" (175582/3).
  - "NAD plus for recovery and stamina" (24298/3).
- Today a coder has no subtopic for this. Under 4.1 such an outcome needs a topic, so coders would fall back on bare `topic:recovery` or `topic:other`. See ADD.

**Float tanks / sensory deprivation:** 335 eps / 48 pods, of which JRE has 243. Too concentrated for a subtopic, so bare `topic:recovery` is acceptable. **Hormesis:** 766 / 524 / 50, mostly as the stated rationale for cold, heat and light ("light therapy can be hormetic", 182366/6). See the `practice_culture` edit.

### topic:peds (Performance-Enhancing Drugs)

**`peds.steroids_sarms`**
- Raw "steroid, SARMs, anabolic, myostatin" counts: 11,302 / 7,229 / 249, but they mix three senses:
  - The idiom "on steroids": 2,479 / 2,311 / 200. Example: "They do stupid on steroids" (62447/1), Ramsey.
  - Medical corticosteroids: `prednisone|corticosteroid|cortisone|steroid shot` gives 293 eps / 77 pods. Example: "He's clearly on steroids … like prednisone" (7791/2), about Putin.
  - Anabolic use: `anabolic steroids?|sarms|on (steroids|gear|a cycle)|juic(ed|ing)|gear|post.?cycle` gives 2,999 eps / 207 pods, still somewhat noisy.
- Myostatin: 108 eps / 22 pods. PCT: 42 eps, noisy.
- Verdict: **needs a definition change** to send corticosteroids elsewhere and to name the idiom.
- A PED accusation about a public figure ("He's on steroids. Look at his face. That's a roid rage", 205572/2, about a governor) is passing `peds.steroids_sarms`, because it asserts drug use about a real person.

**`peds.doping_sport`**
- Counts:
  - Doping: 564 eps / 113 pods.
  - "PEDs": 348 / 53.
  - "Performance-enhancing": 828 / 103.
  - Enhanced Games: 68 / 28.
  - "Natty": 543 / 90 (PMT 138). The sense is mixed: one Mind Pump hit was a nickname ("All right, Natty", 195274/9). I did not verify the rest.
- "Drug test" (1,518 eps / 177 pods) includes many workplace tests (Home Service Expert 119 eps) and cannabis tests, which are not sport.
- Verdict: **fine; definition tweak.**
- Examples: EPO explained on JRE ("EPO is … a performance enhancing drug that cyclists are very fond of", 71724/10); Lance Armstrong (438505/2).

**`peds.fat_loss_drugs_ped`**
- Counts for `clenbuterol|clen|dnp|ephedrine`: 212 / 197 / 47, but 46 Fantasy Footballers and 25 Simmons eps are "DNP" meaning did not play ("you might even get some DNP's", 79540/5).
- Outside sports shows: 109 / 99 / 42. That includes non-PED senses: pseudoephedrine cold medicine (17247/4), ephedrine history (319864/0), military supplements (20511/8).
- Real hits: "it's called DNP … it's in dynamite" (195419/3, Mind Pump); "DNP … in the hundreds died" (176528/1).
- Verdict: **rare, and covered by `weight.diet_pills_fat_burners`** ("any pill … for weight loss"). MERGE.

**HGH/EPO boundary.** "Growth hormone/HGH" appears in 2,755 / 1,748 / 119. In samples it is mostly physiology: sleep, fasting or sauna raising GH ("Testosterone is right next to HGH, our most sleep duration-dependent hormone", 175791/0). That belongs in `endocrine.other_hormones`, as its row already says. Physique use is rarer ("What about human growth hormone? … waste of time", 71095/5). The current rule-8 wording works.

### topic:longevity

**`longevity.ageing_science`**
- Counts:
  - "Longevity, lifespan, healthspan": 23,651 / 11,350 / 271. The Rest Is History contributes 573 eps of "longevity of empires".
  - Anti-aging phrases: 172 eps / 43.
  - Centenarians and Blue Zones: 914 / 102.
- Verdict: **needs a definition change.** "Longevity" is very often a purpose word or tagline:
  - "it's good for your bones … brain, and it's good for longevity" (174862/0);
  - "we're praying in faith for your health and longevity" (175014/6);
  - show intros ("optimizing performance, health, longevity", 181840/0).
- Under rule 1 the purpose word alone should not add this subtopic. In sports shows, "longevity" means career length (the TB12 talk). That is `sports_performance`, not ageing.

**`longevity.longevity_drugs`**
- Counts:
  - Rapamycin, senolytics, acarbose: 962 / 410 / 52.
  - Rapamycin: 282 eps / 46 pods.
  - Metformin in an ageing context: 139 eps / 35 pods.
  - Senolytic: 157 eps / 28 pods. Of these, 52 eps are the Qualia Senolytic supplement ad (41 MeidasTouch): "Qualia Senolytic is a groundbreaking supplement made with nine plant-based nutrients" (6305/5).
- Verdict: **definition change.** Senolytic supplements are sold as longevity agents, but the row says "drugs". Under rule 8 they keep their substance home (supplements) plus this purpose subtopic. Say so.

**`longevity.nad_sirtuins`**
- Counts: NAD/NMN: 3,577 / 1,447 / 109. Resveratrol: 694 / 490 / 55.
- A Charlie Kirk NAD ad accounts for 257 eps: "NAD just might be your secret weapon for more energy" (38781/1). Under rule 1 that adds `wellness.energy_fatigue`.
- NAD also appears in skin care (189916/110) and in men's-clinic ads (24298/3).
- Verdict: **fine.**

**`longevity.biological_age`**
- Counts: 1,560 / 915 / 93.
- "TruAge" is not findable (the "true age" matches are noise). DunedinPACE appears in 9 eps.
- The real phrasing is "biological age test" and "epigenetic age is eight years older" (189910/255).
- A Lancôme ad promises "visible biological age reversal" for skin (194917/4). That belongs in `skin_beauty.skin_ageing`, not here.
- Verdict: **examples change** plus a boundary for skin claims.

**`longevity.cellular_ageing`**
- Counts: autophagy, telomeres, senescence: 4,423 / 1,851 / 102. Mitochondria: 9,115 / 3,345 / 108.
- The mitochondria boundary with `metabolic.mitochondria_energy` is already written.
- Verdict: **fine.**

**`longevity.protocols_clinics`**
- Counts:
  - "Bryan Johnson": 7 eps. ASR "Brian Johnson": 629 / 509 / 101. That includes other people (a Moth storyteller, Kevin Smith's friend, likely the AC/DC singer on sports shows), but Modern Wisdom 42, Live Beyond the Norms 25 and Extend 17 are him. Example: "I hear about Brian Johnson taking 120 supplements" (182062/6).
  - "Don't die": 1,808 eps / 179 pods, nearly all the ordinary phrase.
  - "Young blood": 177 eps, mostly non-health.
  - "Longevity clinic/doctor/medicine/protocol/space/industry": 734 / 553 / 65.
- Verdict: **examples change** (ASR spelling; warn that "Don't Die" counts only as Johnson's slogan or project).

**Stem cells** (6,617 / 2,465 / 162) and exosomes (389 eps) mostly fit `procedures.regenerative_medicine` or `skin_beauty.regenerative_aesthetics`, as the existing boundaries say.

### topic:biohacking

**`biohacking.practice_culture`**
- Counts:
  - "Biohack*": 6,834 / 2,765 / 117. Outside the six biohacking-branded shows it is still 1,585 eps / 111 pods.
  - N-of-1: 309 / 51.
  - "Quantified self": 59 / 24.
  - "Optimal not normal" or "optimal ranges": 378 eps / 42 pods. Thyroid Fixer has 134, and nearly all are about functional lab reference ranges: "I want to be optimal, and oftentimes optimal ranges are too high on on lab values" (195691/0). Those belong in `procedures.lab_testing` or `self_tracking.consumer_lab_tests`, not biohacking identity.
- The word "biohack" is often just a synonym for "health tip": "One of my favorite biohacks outside of breathwork … is mineral salts, Baja Gold" (177094/3); "Gary Brecka's top five biohacks … free" (176927/0).
- Verdict: **definition and examples change.**

**`biohacking.devices_gadgets`**
- Counts:
  - PEMF: 205 / 34 (Darin Olien 65).
  - Vibration plate: 76 / 33.
  - Apollo device: 144 / 14 (mostly Dylan Gemelli ads).
  - NeuroPod ear vagus-nerve stimulator: about 490 Mayim Bialik eps of ad: "a wearable neurotech device … stimulates the vagus nerve through the ear" (185315/10).
- The definition's "other than wearables" wrongly excludes wearable stimulators. The intended exclusion is trackers.
- "Light glasses" conflicts with `sleep.circadian_light` and `radiation_light.artificial_light`, which both claim blue-light glasses (390 eps / 78 pods for blue blockers or light glasses).
- Multi-modality mats ("PEMF … red light … infrared heat … earthing", 181128/0) belong here.
- Verdict: **definition and examples change.**

**`biohacking.stacks_protocols`**
- Counts:
  - "Morning routine": 3,751 / 3,041 / 190. Mindset Mentor 640, School of Greatness 109, and AG1 ads "a great thing to add to your morning routine" (30860/1). Self-help routines: "how to develop a strong morning routine" (183916/0).
  - "Supplement, nootropic or peptide stack": 150 / 137 / 38.
  - "My, daily or longevity protocol": 376 / 306 / 56.
- Verdict: **definition and examples change.** A morning routine is not health content unless it contains body practices.

### topic:self_tracking

**`self_tracking.wearables`**
- Counts:
  - Union: 9,833 / 7,286 / 275, very noisy.
  - Apple Watch: 1,472 eps, mostly Apple Pay ads ("your credit or debit card right on your iPhone or your Apple Watch", 163494/2). Fantasy Footballers alone has 257.
  - Oura: 94 eps literally, 712 eps / 102 pods with the ASR "Aura ring".
  - Whoop as a device (Whoop band, strap, data; my/your Whoop): 700 / 115.
  - HRV: 1,197 / 92.
  - Garmin: 211 / 83.
  - Fitbit: 480 / 119.
- Verdict: **examples change** (ASR form) plus a note on payment-device mentions.

**`self_tracking.glucose_monitors`**
- Counts: 1,656 / 917 / 91, of which 849 eps / 90 pods are outside diabetes shows. Levels: 65 / 29.
- Diabetic CGM use ("the feedback loop between the pump and the Dexcom", 183064/3) also needs `metabolic.diabetes`. The definition already says "including in people without diabetes".
- Verdict: **fine.**

**`self_tracking.consumer_lab_tests`**
- Counts:
  - Named consumer tests: 1,851 / 1,141 / 67.
  - Function Health: 552 eps, 355 of them Hyman, mostly the disclaimer "my work at Cleveland Clinic and Function Health, where I'm the chief medical officer" (182218/7).
  - GI-MAP: 222 / 26.
  - Hair mineral analysis or HTMA: 31 / 11.
  - The DUTCH test appears beside an organic acids test (185720/5).
  - LabCorp OnDemand is advertised in fantasy football (163818/0).
- Verdict: **fine; examples change** (add DUTCH and LabCorp OnDemand-style DTC testing), plus a codebook note on disclaimers.

**`self_tracking.body_scans`**
- Counts:
  - DEXA: 750 / 530 / 58 (Mind Pump 139). It is mostly body-fat measurement ("I've had three DEXA scans … it pissed me off", 195546/8) or bone density ("I am recommending DEXA scans … bone density", 174911/3).
  - Prenuvo or full-body MRI or scan: 204 / 178 / 64. Example: "it's an important reason we use full body MRI" (176657/2).
- Verdict: **examples change.** Drop DEXA here, because `weight.body_composition` already lists "DEXA scan".

### topic:digital_health

**`digital_health.ai_advice`**
- Organic consumer use is small: "I put in all my symptoms, I enter in all my lab data … tell me what's wrong" (182262/3); "Paging Dr. ChatGPT" (203911/1).
- Ads dominate:
  - Amazon Health AI: 3,358 / 3,022 / 43. "Amazon Health AI can connect your symptoms with your medical history" (85045/0).
  - Hers' disclaimer, about 886 Armchair eps: "AI responses in the Hers app are AI generated and do not constitute a medical diagnosis" (74155/0).
- Chatbot mental-health harms:
  - Narrow query (AI psychosis, or chatbot near suicide, psychosis or delusion): 141 segments.
  - Broad query adding AI companions: 486 / 359 / 92, though that includes HP "AI Companion" ads.
  - Examples: Character.AI teen suicide (30239/1); chatbot psychosis (439230/1).
- "AI" also collides with aromatase inhibitor in TRT talk: "I would never prescribe AI for my male patients" (195691/4).
- Verdict: **definition change** to cover chatbot harms and AI-mediated care services, plus a codebook note.

**`digital_health.ai_in_medicine`**
- Query: AI in healthcare or medicine, medical AI, AI doctor or scribe.
- Counts: 101 / 83 / 43; AI radiology 27 eps; AI with FDA or drug discovery 21 eps.
- Verdict: **rare but keep.** It matters for research and is distinct from ai_advice.

**`digital_health.online_health_information`**
- Counts:
  - Health misinformation as a subject (health term within 60 characters of mis/disinformation): 895 / 769 / 97, politics-heavy (Meidas, Megyn Kelly, JRE, Breaking Points, Kirk). Examples: "Governor DeSantis spreading COVID disinformation" (84358/6); "none of the things I said were actually misinformation, as they like to say about the vaccine" (168766/0).
  - Social media near health or fitness advice: 331 / 90.
  - Wellness or fitness influencer: 465 / 96 (Mind Pump 107: "social media fitness influencers like thirty days", 195358/0).
  - Dr. Google or WebMD: 353 / 115 ("reading online, Dr. Google, some kind of blog", 191000/80).
- Verdict: **examples change** (add Dr. Google, WebMD, fitness influencers).

**`digital_health.health_apps`**
- Counts: named apps (Headspace, Calm, Noom, MyFitnessPal, Strava, Flo, Apple Health, "health app"): 4,062 / 3,656 / 225, mostly ads. "Digital therapeutics": 9 eps. Period apps: 75 eps, noisy.
- Verdict: **examples change.**

**Telehealth** (1,807 / 1,522 / 141) is correctly in `health_system.dtc_telehealth`. No change.

### Cross-slice gap: trans athletes

- Query `(trans|transgender|biological (men|males)) (athletes?|swimmers?|…)|men in women's sports|women's sports`.
- Counts: 2,312 / 1,799 / 106 (Megyn Kelly 244, Kirk 225, Walsh 173, Morning Wire 157, Shapiro 120, JRE 87).
- `cooc` with `testosterone|bone density|muscle mass|male puberty|injur…|physiolog…|lung capacity|advantage`: 1,081 eps.
- Samples are mostly fairness and policy talk ("your population doesn't want men playing in women's sports", 5939/7). Physiology arguments also appear ("transition from a man to a woman, and you want to compete in women's sports … how fair is that", 204936/4).
- Nothing in `gender` or `fitness` covers it. Coders would scatter it across `gender.lgbtq_health`, `policy.partisan_politics` and `topic:other`.

## Proposed edits

CHANGE `topic:fitness.sports_performance`
| sports_performance | Athletic performance & training | How athletes train, condition, cut weight, fuel and recover, and physiological explanations of athletic performance, including an athlete's body-care regimen and career longevity. Roster, usage and schedule talk (training camp as a calendar event, snap or pitch counts, workload), and a passing verdict that a player is in or out of shape, are not health content. | overtraining; fight camp; weight cutting for a weigh-in; conditioning programme; TB12 and pliability; altitude training; sports science |

Why: "training camp" in 4,472 sports-performance-term episodes is calendar talk in every sports-show sample (163598/1, 323069/4). Weight cutting (520 eps / 56 pods) and TB12/pliability (293 eps / 59 pods) are the recurring health content of sports shows and have no named example.

CHANGE `topic:fitness.strength_training`
| strength_training | Strength & resistance training | Lifting and resistance training and bodybuilding as training practice: how to train, programming, technique and strength measures. Muscle mass as a health outcome goes to `musculoskeletal.muscle_loss`. | weightlifting; lifting heavy; resistance training; hypertrophy; progressive overload; squats and deadlifts; bodybuilding; bulking; grip strength |

Why: "women lifting" appears in 30 eps. Bodybuilding, physique and bulking appear in 4,889 eps / 226 pods, and grip strength in 496 / 80, with no listed home.

CHANGE `topic:fitness.exercise_general`
| exercise_general | Exercise benefits & dose (general) | Exercise in general: how much, why, for whom, and its effects when no modality is specified. When an outcome (longevity, mood, glucose) is discussed in its own right, add the outcome's subtopic under co-labeling rule 1. | physical activity; how much exercise; minimum effective dose; exercise is medicine; move more; exercise for depression |

Why: "exercise for longevity" as an example invites single-labeling of an outcome that rule 1 says to co-label. "Physical activity" (1,675 eps / 194 pods) and "minimum effective dose" (137 / 36) are the real phrasing.

CHANGE `topic:fitness.daily_movement`
| daily_movement | Walking & daily movement | Steps, walking and incidental activity, and sitting. | 10,000 steps; steps a day; walking after meals; rucking; weighted vest; sedentary; sitting is the new smoking; standing desks |

Why: weighted vests appear in 198 eps / 63 pods (Brecka, JRE, Habits and Hustle), unlisted.

CHANGE `topic:recovery.heat_sauna`
| heat_sauna | Heat & sauna | Sauna and deliberate heat exposure. A hot tub or bath named only as a social setting is not health content. | sauna; infrared sauna; sauna bathing; heat shock proteins; hot and cold contrast |

Why: "hot tub" (2,466 eps / 211 pods) is mostly scene-setting (Watch What Crappens 551 eps; 95931/2, 161056/1).

ADD `topic:recovery.training_recovery` under `recovery`
| training_recovery | Recovery from training | Recovery from exercise as an outcome or practice when no listed modality is the subject: muscle soreness, rest and deload, recovery between sessions, and recovery claimed for a product. A named modality takes its own subtopic; overtraining in athletes goes to `fitness.sports_performance`. | DOMS; muscle soreness; rest days; deload week; post-workout recovery; muscle recovery |

Why: the training-recovery terms occur in 1,092 eps / 110 pods, and soreness, DOMS, deload and rest-day terms in 1,567 eps / 148 pods. Ads state it as a product outcome: "Post-workout recovery is a big factor. Core Power Protein Shakes…" (502516/15); "my post-workout muscle recovery has been incredible" (176979/5); "NAD plus for recovery and stamina" (24298/3). The recovery parent covers only modalities, so these outcomes have no home under 4.1. (The parent's prose should then read "…modalities used to recover, and recovery from training itself".)

CHANGE `topic:peds.steroids_sarms`
| steroids_sarms | Steroids, SARMs & anabolic agents | Anabolic steroids, SARMs and cycles, myostatin inhibitors, and growth hormone or EPO used for physique or performance (which also take the hormone's home), including claims that a named person uses them. Corticosteroids (prednisone, steroid shots, inhalers) go to the condition or `medications.other_drugs`; "X on steroids" as an intensifier is an idiom. | anabolic steroids; SARMs; cycle; PCT; trenbolone; roid rage; myostatin inhibitors; HGH for muscle; EPO |

Why: "on steroids" as an idiom covers 2,311 eps / 200 pods ("stupid on steroids", 62447/1), and corticosteroid talk 293 eps (7791/2). Accusations about public figures ("That's a roid rage", 205572/2) need a stated home.

CHANGE `topic:peds.doping_sport`
| doping_sport | Doping in sport & "natty or not" | Drug use and drug testing in sport and fitness culture, and accusations that an athlete or physique is enhanced. Workplace, legal or cannabis drug tests go to the substance's subtopic. | doping; PEDs; drug testing in sport; EPO in cycling; Lance Armstrong; natty or not; Enhanced Games |

Why: "drug test" (1,518 eps) includes many workplace tests (Home Service Expert 119 eps). Doping (564 / 113) and PEDs (348 / 53) are the real vocabulary.

MERGE `topic:peds.fat_loss_drugs_ped` into `topic:weight.diet_pills_fat_burners`
Why: genuine hits are under 100 eps. Of 197 raw episodes, the sports-show "DNP" is "did not play" (79540/5), and the remaining 99 eps outside sports shows include cold medicine and history (17247/4, 319864/0). `weight.diet_pills_fat_burners` already covers "any pill … taken for weight loss". Add "clenbuterol; DNP; T3 for cutting" to its examples, and keep rule 8's instruction to add `peds.steroids_sarms` only when the drug is part of an anabolic cycle.

CHANGE `topic:longevity.ageing_science`
| ageing_science | Ageing & healthspan (general) | How and why we age, lifespan and healthspan as outcomes, and age-reversal studies. "Longevity" used only as a purpose or tagline ("good for longevity", "health and longevity") does not add this subtopic; an athlete's career longevity is `fitness.sports_performance`. | healthspan; lifespan; hallmarks of aging; centenarians; Blue Zones (as longevity); age reversal; VO2 max predicts lifespan |

Why: "longevity" appears in 11,350 eps / 271 pods, with frequent purpose and tagline uses (174862/0, 175014/6, 181840/0). Rest Is History contributes 573 eps of non-health "longevity". Sports shows use it for careers (322938/2).

CHANGE `topic:longevity.longevity_drugs`
| longevity_drugs | Longevity drugs & senolytics | Drugs, and supplements sold as senolytics or longevity agents, taken to slow ageing. A supplement also takes its substance's `supplements` subtopic under rule 8. | rapamycin; metformin for longevity; senolytics; senolytic supplement; acarbose |

Why: senolytic appears in 157 eps / 28 pods, 52 of them a supplement ad ("Qualia Senolytic is a groundbreaking supplement made with nine plant-based nutrients", 6305/5) that "drugs" does not cover.

CHANGE `topic:longevity.biological_age`
| biological_age | Biological age testing | Measuring biological or epigenetic age. Skin-care "biological age" claims go to `skin_beauty.skin_ageing`. | biological age test; epigenetic age; epigenetic clock; "biologically ten years younger"; DunedinPACE |

Why: "TruAge" is not findable (the "true age" matches are noise) and DunedinPACE appears in 9 eps. The real phrasing is "biological age test" and "epigenetic age" (189910/255). A Lancôme ad sells "visible biological age reversal" (194917/4).

CHANGE `topic:longevity.protocols_clinics`
| protocols_clinics | Longevity protocols & clinics | Longevity medicine as a field or practice, named whole-life longevity protocols, personal protocols and the clinics selling them. "Don't die" counts only as Bryan Johnson's slogan or project. | Bryan Johnson (often transcribed Brian Johnson); Blueprint; Don't Die; longevity clinic; longevity doctor; young blood transfusions |

Why: "Bryan Johnson" appears in 7 eps versus "Brian Johnson" in 509 (182062/6). "Don't die" appears in 1,808 eps, almost all ordinary speech.

CHANGE `topic:biohacking.practice_culture`
| practice_culture | Biohacking practice & culture | Biohacking as identity, method and community, and hormesis as a general principle. A single tip called "a biohack" takes the tip's own subtopic; functional "optimal ranges" for labs go to `procedures.lab_testing` or `self_tracking.consumer_lab_tests`. | biohacker; biohacking conference; N-of-1; self-experimentation; quantified self; hormesis |

Why: "optimal not normal" or "optimal ranges" (378 eps / 42 pods) is lab-range talk (195691/0). "Biohack" is often just a synonym for a tip (177094/3, 176927/0). Hormesis (524 eps / 50 pods) has no home.

CHANGE `topic:biohacking.devices_gadgets`
| devices_gadgets | Biohacking devices & gadgets | Consumer devices used to stimulate or optimize the body, including wearable stimulators, other than measuring devices (`self_tracking`) and recovery modalities. Blue-light glasses go to `sleep.circadian_light` or `radiation_light.artificial_light`. | PEMF mat; vibration plate; vagus nerve stimulator; Apollo; neurostimulation headset; ozone generator |

Why: the NeuroPod ear-worn vagus-nerve stimulator ad runs in about 490 Mayim Bialik eps (185315/10), and "other than wearables" excludes it. "Light glasses" duplicates the sleep and light tables' blue-light-glasses rule (390 eps / 78 pods).

CHANGE `topic:biohacking.stacks_protocols`
| stacks_protocols | Stacks & daily protocols | Combined regimens of supplements and body practices. A productivity or self-help routine with no health practice is not health content, and "add it to your morning routine" in an ad does not add this subtopic. | supplement stack; my daily protocol; morning routine of sunlight, cold plunge and supplements; peptide stack |

Why: "morning routine" (3,041 eps / 190 pods) is mostly self-help and ad copy (183916/0, 30860/1). Real stacks are rarer (supplement, nootropic or peptide stack: 137 eps / 38).

CHANGE `topic:self_tracking.wearables`
| wearables | Wearables & trackers | Wearable trackers and their metrics. A device named only as a payment or phone accessory is not health content. | Oura (often transcribed Aura ring); Whoop band; Apple Watch health features; Garmin; Fitbit; HRV; recovery score; sleep score |

Why: Oura appears in 94 eps literally against 712 with "Aura ring". Apple Watch's 1,472 eps are mostly Apple Pay copy (163494/2).

CHANGE `topic:self_tracking.consumer_lab_tests`
| consumer_lab_tests | Consumer lab & functional tests | Lab tests a consumer orders or buys directly, or a functional practitioner's proprietary panel sold to the client. Clinician-ordered tests go to `procedures.lab_testing`. | Function Health; LabCorp OnDemand; at-home blood test; hormone panel; DUTCH test; food sensitivity test; hair mineral analysis; organic acids test; GI-MAP |

Why: DUTCH appears beside organic acids in real speech (185720/5) and LabCorp OnDemand is advertised in sports shows (163818/0). GI-MAP is real (222 eps / 26).

CHANGE `topic:self_tracking.body_scans`
| body_scans | Full-body scans & elective imaging | Elective imaging bought to find disease early. DEXA for body fat goes to `weight.body_composition`; for bone density to `musculoskeletal.bone_health`. | Prenuvo; full-body MRI; whole-body scan; elective CT |

Why: DEXA (530 eps / 58 pods) is body composition (195546/8) or bone density (174911/3), and `weight.body_composition` already lists "DEXA scan".

CHANGE `topic:digital_health.ai_advice`
| ai_advice | AI health advice, chatbots & AI-mediated care | Patients or consumers using AI for health advice, diagnosis, therapy or companionship, consumer AI health services, and the mental-health effects of chatbot use (co-label the condition). Clinicians' or institutions' use goes to `digital_health.ai_in_medicine`. "AI" meaning aromatase inhibitor is `mens.testosterone`. | asking ChatGPT about symptoms; AI therapist; AI doctor; Amazon Health AI; AI companions; AI psychosis; chatbot-linked suicide |

Why: chatbot harms run to 141 narrow segments and 359 eps / 92 pods broadly (30239/1, 439230/1), and no label covers harm from companionship. Amazon Health AI (3,022 eps / 43 pods) is AI-mediated care. The aromatase-inhibitor collision appears at 195691/4.

CHANGE `topic:digital_health.online_health_information`
| online_health_information | Health information & misinformation | Health information on social media, search engines and from influencers, and health misinformation as a subject, online or offline, including its moderation. | wellness and fitness influencers; Dr. Google; WebMD; TikTok health trends; COVID misinformation; content moderation of health claims; politicians spreading health misinformation |

Why: Dr. Google or WebMD appears in 353 eps / 115 pods (191000/80), and wellness or fitness influencers in 465 / 96 (195358/0).

CHANGE `topic:digital_health.health_apps`
| health_apps | Health apps | Apps for health other than wearables and therapy services. | meditation apps (Calm, Headspace); calorie-tracking apps; MyFitnessPal; period-tracking apps; Apple Health app |

Why: "digital therapeutics" appears in 9 eps. The named consumer apps appear in 3,656 eps / 225 pods (mostly ads).

ADD `topic:gender.trans_athletes` under `gender` (cross-slice; for the gender reviewer)
| trans_athletes | Transgender athletes in sport | Transgender athletes' participation in sport when bodies are discussed: male-puberty advantage, testosterone limits, physiology and injury risk to competitors. Eligibility talk with no physiological content is not health content. | trans athletes; men in women's sports; testosterone limits; male puberty advantage; injury risk to female athletes |

Why: 1,799 eps / 106 pods mention it, and 1,081 eps co-occur with physiology or injury terms. There is no label (5939/7, 204936/4).

## Codebook and prompt notes

1. **Section 3, Exclude: replace "sports talked about purely as competition…" with an operational rule.** Proposed text:

   > Sports talk is health content only when it describes a body: an injury, illness or medical care; how an athlete trains, conditions, recovers, cuts weight or eats; drug use or a PED accusation; or a physiological explanation of performance. Usage and schedule talk (training camp as an event, snap or pitch counts, "workload", minutes), roster and contract talk, and evaluative remarks ("he's out of shape", "freak athlete") are not.

   Evidence: training camp (163598/1), pitch count (80076/10), workload (322922/0) and "way out of shape" (79233/1) contrast with weight cutting (13523/7), overtraining (71160/12) and TB12 (322938/2). With about 13,000 sports-show episodes in the corpus, this sentence decides a large share of the slice's precision. Add a sports example to the rubric next to "that loss was a gut punch": "he'll get a full workload after training camp" → empty output.

2. **Section 3, Exclude: incidental exercise.** Proposed text:

   > Exercise named only as an activity, setting or schedule ("before I hit the gym", "after yoga", "gym rat", "yoga pants", "how's that working out") is not health content. A person's own training stated as a health practice ("I lift four days a week for my back") is a passing detection.

   Evidence: "gym", "workout" and "yoga" occur in 25k, 48k and 9k episodes across 430–530 podcasts. Most hits in non-health shows are scene-setting or idiom (1140035/2, 94338/1, 74621/4, 95753/4). True-crime plot exercise (23196/5) follows the fiction and plot rule.

3. **Section 3, idioms list: add "X on steroids" and "longevity" taglines.**
   - "On steroids" as an intensifier appears in 2,311 eps / 200 pods (62447/1, 194690/5).
   - "Health and longevity" as a sign-off or show tagline (175014/6, 181840/0) belongs with "'health' as a bare hypothetical or a podcast's tagline".

4. **Section 2, "General knowledge is for understanding words": add slice collisions as worked examples.**
   - "DNP" is "did not play" in sports talk (79540/5) and a fat-loss drug in fitness talk (195419/3).
   - "AI" can be an aromatase inhibitor in TRT talk (195691/4).
   - "Tren" can be Tren de Aragua (Megyn Kelly, Morning Wire, Kirk).
   - "Whoop" is usually an interjection.
   - "Brian Johnson" or "Aura ring" are likely ASR for Bryan Johnson or Oura when the context is longevity or tracking. Section 8 already repairs "Aura ring" for products; topics need the same reading.

5. **Section 4.1, topics inside ads: boilerplate does not trigger a topic.**
   - A host's employment disclaimer naming a company (Hyman's "my work at … Function Health", 182218/7, about 355 eps) is `frame:disclaimer` only.
   - A compliance line in a telehealth ad ("AI responses in the Hers app … do not constitute a medical diagnosis", 74155/0, about 886 eps) does not add `digital_health.ai_advice`. The advertised service takes its own subtopic.
   - A device named as a payment accessory (Apple Pay on Apple Watch, 163494/2) and apparel or gear ads that mention a workout as the setting fail the ad test.
   - Fitness services (class apps, programmes) pass it as health products.

6. **Section 4.1, outcomes in ads.** "Post-workout recovery", "recovery and stamina" and "muscle recovery" are stated outcomes, so they take the proposed `recovery.training_recovery` under rule 1 (502516/15, 176979/5, 24298/3). "Add it to your morning routine" is a usage instruction, not an outcome (30860/1).

7. **Section 5.1, co-labeling rule 1: worked example for longevity as a purpose.**
   - "Strength training is good for your bones … good for longevity" (174862/0) takes `fitness.strength_training`, `musculoskeletal.bone_health` only if bones are discussed, and no `longevity.ageing_science` unless lifespan or healthspan is itself discussed.
   - VO2 max presented as a predictor of lifespan does take `longevity.ageing_science`.

8. **Section 5.1, rule 8: senolytic supplements and NAD in ads.** A senolytic supplement takes its substance subtopic plus `longevity.longevity_drugs` (6305/5). An NAD ad promising "more energy" takes `longevity.nad_sirtuins` plus `wellness.energy_fatigue` (38781/1).

9. **Section 5.1, clinic bundles.** A clinic offering "hyperbaric oxygen, sauna, cryotherapy and LED light" (176678/6) is one span with each modality's subtopic plus `longevity.protocols_clinics`. Under rule 6 the modalities are listed nouns, so this applies only when the bundle itself is the product being described. Otherwise it takes the clinic subtopic alone. This is worth one sentence because these lists recur in longevity-show ads.

10. **Section 5.3, `frame:optimization`.** The current text already excludes lab reference ranges. Add that "optimal ranges" in functional-lab talk (378 eps; 195691/0) is the lab subtopic and not the frame, unless maximizing language is applied to the body ("I have no desire to be normal. I want to be optimal" would qualify).

11. **Section 5.5, population.** A sports show discussing one player's conditioning or PED accusation takes no `population:athletes` (one person's own case). Leaguewide talk does ("players in this league are all juicing", doping in cycling).
