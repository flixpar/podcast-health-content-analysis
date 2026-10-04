# Cardiovascular, metabolic, weight, GLP-1, endocrine, kidney/lung: corpus review

Slice: `topic:cardiovascular`, `topic:metabolic`, `topic:weight`, `topic:glp1`, `topic:endocrine`, `topic:kidney_lung` and their subtopics (taxonomy/health-v8.md).
Method: about 60 `cq.py` count, sample and cooc runs (the later ones on the NVMe copy). Counts are segments / episodes / podcasts. Episode counts are more meaningful than segment counts, because some shows (Thyroid Fixer, LONGEVITY, Boring History) are segmented per sentence. Every subtopic in the slice is findable: none is near-absent. Bariatric surgery is the smallest at about 490 episodes.

## Summary

- **The `glp1` counts are dominated by dynamic-insertion ads, and the v8 examples send those ads to the wrong subtopic.** Hers ("FDA-approved GLP-1 medications that now includes the Wegovy pill and the Wegovy pen"), Ro ("the first FDA-approved GLP-1 pill for weight loss"), the Noom GLP-1 programme and Mochi run in hundreds of non-health episodes, including old ones (a 2018 Happier episode carries the 2026 Hers ad). The top `glp1` podcasts are ad carriers: Armchair Expert 948 episodes, Le Batard 634, Happier 591, MeidasTouch 413. 1,606 episodes hit "oral/pill" GLP-1 terms, 1,454 of them from two podcasts. `glp1.new_offlabel_uses` lists "oral and next-generation drugs", so every Wegovy-pill ad would land there. Approved oral forms should move to `use_results`.
- **Drug-ad safety boilerplate inflates this slice's topics.** Mandated safety lists in pharma ads name `blood_pressure`, `insulin_glucose`, `cholesterol_lipids` and `weight` subjects. Nurtec's "High blood pressure and Raynaud's syndrome can occur" makes Hidden Brain (515 episodes) the top podcast for "blood pressure". Rexulti's list is "High blood sugar can lead to coma or death. Weight gain, increased cholesterol…". The codebook needs a rule that these side-effect lists do not create topic detections.
- **The `heart_disease` / `blood_circulation` boundary by anatomy fails for generic atherosclerosis** (907 episodes, 130 podcasts): "atherosclerosis is driven by smoking, high blood pressure, and high apoB"; plastics in carotid plaque linked to "heart attacks and strokes". Atherosclerosis and ASCVD in general should go to `heart_disease`.
- **`blood_circulation` is a grab-bag of three subjects.** It covers vessel/"circulation"/nitric-oxide wellness talk (about 6,300 episodes, noisy), blood clots (1,819 episodes, 185 podcasts; 516 of those episodes also have vaccine terms) and anemia/blood disorders (1,321 episodes, 167 podcasts). I propose splitting clots and blood disorders into `cardiovascular.clots_blood_disorders`, so that vaccine-clot and other clot talk is countable apart from "boosts circulation" copy.
- **`metabolic.fatty_liver` lists "uric acid", but real uric-acid talk is a different subject.** It is the Perlmutter/Johnson "fructose → uric acid → metabolic dysfunction" account (an `insulin_glucose` subject), plus gout (already `musculoskeletal.joints_arthritis`). "Uric acid A" is also an ASR mishearing of urolithin A. Move uric acid to `insulin_glucose`, and add metabolic flexibility (581 episodes, 49 podcasts) and hypoglycemia / low blood sugar (842 episodes, 126 podcasts) there too.
- **The "slow metabolism" boundary is ambiguous.** `weight.body_composition` lists "slow metabolism" as an example, while `weight_gain_causes` covers "metabolism blamed for weight gain", and both readings occur. Calories-in-calories-out talk (505 episodes) has no stated home.
- **`glp1.natural_alternatives` is real and growing, but its "Akkermansia" example misleads.** Real phrasing is "natural GLP-1 alternative", "GLP-1 booster" (Veracity, Biomega ads), "Nature's Ozempic" and "the natural GLP-1" (said of protein). Most Akkermansia hits are plain microbiome talk. Weight-loss supplement ads (Lean) explicitly pitch against "painful weekly injections".
- **Endocrine boundary notes.** Most oxytocin talk (1,277 episodes) is "love hormone" relationship pop-science, which fits `cognition.neurochemistry_talk` better than `endocrine.other_hormones`. "Cortisol" is often loose shorthand for stress ("always kind of cortisol levels, the stress levels"), which should go to `stress`. Both need a sentence in the definitions.
- **`kidney_urinary` overlaps with `infectious.other_infections` on UTIs.** The top podcast for bladder/UTI terms (Giggly Squad, 324 episodes) is a repeated Wisp UTI telehealth ad. `kidney_urinary` says "bladder and urinary problems", while `infectious.other_infections` lists "UTI as infection". State the boundary in `kidney_urinary`.
- **No new subtopic is warranted beyond the clots split.** Candidates checked: anemia (handled by the split), POTS (81 episodes, already `chronic_complex`), sleep apnea (already `sleep`), gout (already joints), GLP-1 "companion" foods (164 episodes in 22 podcasts, ad-driven).

## Label-by-label findings

### `topic:cardiovascular` (parent)
- Query: `heart health|cardiovascular health|healthy heart|cardiovascular disease|heart disease` → 10,784 / 6,630 / 233 (top: Hyman 811, Jockers 316).
- Verdict: fine. Bare-parent uses are mostly supplement-purpose phrases: magnesium "helps with … cardiovascular health" (182014/3), cycling "lots of benefit for cardiovascular health" (24761/15). Those are purpose words and correctly take the parent at most.

### `cardiovascular.cholesterol_lipids`
- Queries: `cholesterol` → 6,279 / 3,632 / 206; `ldl|hdl|apo b|triglycerides` → 3,210 / 1,572 / 94; Lp(a) variants → 357 / 221 / 37; lean mass hyper-responders → 120 / 81 / 17.
- Verdict: fine. The examples occur. Lp(a) appears as "lp little a" in ASR.
- Boundary seen: lipid-panel talk used as an indirect insulin-resistance marker ("gives you an insulin resistance score", 182519/6). That takes this label plus `metabolic.insulin_glucose`. A specific test (Cardio IQ, NMR) may also take `procedures.lab_testing`.

### `cardiovascular.statins_lipid_drugs`
- Query: statin brand/generic names, PCSK9, Zetia → 2,068 / 1,187 / 103.
- Verdict: fine. Real passages are clear: "is there any dispute in the efficacy of statins in secondary prevention" (181872/9); "more than fifty percent … will stop the statin within two years" (183022/2). Statins in drinking water (182712/0) is an environment subject, with this label only in passing.

### `cardiovascular.blood_pressure`
- Queries: `blood pressure|hypertension|hypotension` → 11,235 / 7,441 / 285; BP drugs → 909 / 785 / 124.
- Verdict: definition fine; counts heavily inflated by ads and idioms.
  - Ad safety lists: Hidden Brain is the #1 podcast (515 episodes) because of the Nurtec ODT read, "High blood pressure and Raynaud's syndrome can occur" (170345/0, 184540/3).
  - Supplement ad outcomes: SuperBeets, "clinically shown to be two times as effective at supporting normal blood pressure" (15105/3). This correctly takes the label as an ad outcome.
  - Idioms: "Gets my blood pressure going, dude" (194630/11); "your blood pressure was 400 over" (22780/0).
- Real phrasing: low blood pressure appears (175443/4: "His blood pressure is dangerously low"), but the definition names only hypertension.

### `cardiovascular.heart_disease`
- Queries: heart attack / cardiac arrest / coronary / heart failure / AFib / arrhythmia / myocarditis / stents / calcium score → 14,660 / 10,889 / 356; atherosclerosis / ASCVD / clogged arteries / carotid → 1,314 / 907 / 130.
- Verdict: needs a definition change.
  - A large share of hits are causes of death in true crime and history: "suffered a heart attack. He died three days later" (21556/4); "her husband had died … from a heart attack" (160947/1). Others are hyperbole: "working until you die of a heart attack when you're 33" (629264/1).
  - The definition sends "vessels elsewhere, calcification outside the coronaries and peripheral plaque" to `blood_circulation`. Generic atherosclerosis talk is common and anatomically unspecified: "atherosclerosis is driven by … smoking, high blood pressure, and high apoB" (175903/9). Carotid plaque is framed as heart-attack and stroke risk: "they found that more than half had plastics in their arteries … fourfold risk of heart attacks and strokes" (199/1). A coder cannot tell which label applies.
- Recommendation: atherosclerosis and ASCVD in general → `heart_disease`; `blood_circulation` only for explicitly non-cardiac vessels.

### `cardiovascular.blood_circulation`
- Queries:
  - Broad (circulation, blood flow, nitric oxide, endothelium, vasodilation): 11,053 / 6,310 / 249.
  - Nitric oxide alone: 1,925 / 748 / 64.
  - Clots (blood clots, clotting, DVT, PE, thrombosis, embolism, blood thinners): 2,250 / 1,819 / 185.
  - Blood disorders (anemia, hemochromatosis, iron overload, sickle cell, hemophilia, bleeding disorder): 1,648 / 1,321 / 167.
  - Clots co-occurring with vaccine / jab / AstraZeneca / J&J / spike protein: 516 of 1,500 clot episodes (Rogan 87, Charlie Kirk 48, Megyn Kelly 31).
- Verdict: needs a split or a definition change. The label mixes three subjects that researchers would count separately.
  - "Circulation" as wellness benefit copy: "increased microvascular circulation" from red light (6231/8); sleep-story ASMR "restoring circulation" (324193/3172). There is also non-health noise ("books removed from circulation", 207620/5).
  - Endothelium and nitric oxide mechanism talk: "Glucose … causes endothelial cell dysfunction … interferes with nitric oxide" (19315/1). Nitric oxide (748 episodes) is not in the examples.
  - Clots: about a third of clot episodes also discuss vaccines, which is a core misinformation subject.
  - Anemia and iron, where coders also need the iron co-label: "he uses the terms anemia and iron deficiency interchangeably" (190612/156); a menopause lab list asks for "the iron and anemia panel" (174864/2).
- Sickle cell is listed under `genetics.genetic_conditions` and is also implied by "blood disorders" here. Name it as a double label.

### `topic:metabolic` and `metabolic.insulin_glucose`
- Queries: insulin resistance / sensitivity, blood sugar / glucose, spikes, prediabetes, A1c, hyperinsulinemia, fasting insulin, HOMA-IR → 15,963 / 6,549 / 240. "Metabolic health / metabolically healthy / metabolic dysfunction / syndrome / disease" → 4,936 / 2,685 / 107.
- Verdict: definition fine; examples need additions.
  - Low blood sugar / hypoglycemia: 1,052 / 842 / 126. It is not named, and the definition says only "spikes and control".
  - Metabolic flexibility / fat adapted: 972 / 581 / 49 (Jockers 177). It has no home: "you lose metabolic flexibility, right? You actually don't get very tolerant of carbohydrates" (176575/3).
  - Uric acid as a metabolic driver: "fructose, which is metabolized into uric acid … Alzheimer's is primarily a metabolic issue" (192544/3, 192639/3).
- Quote: "If you're insulin resistant too, and leptin resistant … you will not lose weight" (190708/63). This takes `insulin_glucose` + `endocrine.other_hormones` (leptin) + `weight.weight_gain_causes`.
- Ad outcome phrasing to recognise: "keeps your blood sugar steady, so no more energy crashes" (Lean ad, 388313/3); "help regulate blood sugar, curb cravings, and boost metabolism" (Verso ad, 318970/1).

### `metabolic.diabetes`
- Query: `type (2|two|1|one) diabet*|diabetics?|diabetes` → 16,392 / 9,495 / 302.
- Verdict: fine, but counts carry two known artefacts.
  - MeidasTouch is the #2 podcast with 432 episodes. Its hits are Ro GLP-1 ads ("non-diabetics with obesity", 84414/8), SelectQuote life-insurance ads ("Have high blood pressure, diabetes, or heart disease?", 63837/3), and insulin-price-cap politics (18345/0). Price caps take this label plus `health_system.costs_insurance` under the policy rule.
  - Diabetes appears in chronic-disease lists ("Diabetes, metabolic syndrome, dementia, cancer", 20553/10). Rule 6 applies to these.
- Type 1 lived-experience shows exist (Diabetes Nerd: "I live with type one diabetes", 183070/3).

### `metabolic.fatty_liver`
- Query (strict): fatty liver / NAFLD / MASLD / liver fat / Rezdiffra / steatohepatitis → 1,299 / 802 / 88. A broader query that included NASH/MASH/fructose was swamped by Steve Nash and M*A*S*H (Bill Simmons 390 episodes, Conan 332).
- Verdict: needs an examples change.
  - The renaming is discussed ("they changed the name … to metabolic associated fatty liver disease", 23259/13), and ALT is used as the marker (181871/2).
  - Uric acid does not belong here: "uric acid / gout" → 1,069 / 771 / 121. The top podcasts are Boring History (67), SYSK, Last Podcast, i.e. gout in historical figures. The health-show hits are the fructose / uric-acid metabolic account.
- ASR note: "uric acid A" / "urate and A" / "urea thion A" are mis-hearings of the supplement urolithin A (78329/1, 78241/6).

### `metabolic.mitochondria_energy`
- Queries: broad (mitochondria*, ATP, NAD, PARP, cellular energy) → 16,204 / 5,058 / 177, noisy (Charlie Kirk 292 is mostly "ATP"/NAD noise); strict (mitochondrial health / dysfunction / function / biogenesis, cell danger response, cellular energy) → 3,818 / 2,033 / 66.
- Verdict: fine. Real use is broad and mostly wellness framing: "the first one though is mitochondrial health … the centerpiece of the energy production of our cells" (51484/1); Lyme "rebuilding cellular energy is really important. This is mitochondria" (181884/1). The boundary with `longevity.cellular_ageing` is visible ("as I look to slow the clock", 78241/6) and the existing rule handles it.

### `topic:weight` (parent) and `weight.obesity_rates`
- Queries: `obes*|bmi|body mass index|overweight` → 20,023 / 12,916 / 322; obesity epidemic / rates / crisis / childhood obesity / morbidly obese → 1,793 / 1,515 / 135.
- Verdict: fine.
- Noise sources:
  - Pet-food ads ("dogs who maintain a healthy weight", 71869/0), which are excluded as animal health.
  - "BMI" the songwriters' organisation (94314/3).
  - Insults and comedic weight ("morbidly obese" joke, 5558/0).
  - GLP-1 ad eligibility copy ("non-diabetics with obesity or overweight").
- Medical-framing passage: obesity as a disease in the Novo Nordisk / body-positivity debate (198733/3) takes `obesity_rates` + `body_image_stigma`.

### `weight.weight_gain_causes`
- Query: gain weight / weight gain / can't lose weight / belly fat / stubborn fat / weight-loss resistance / put on weight → 8,934 / 6,064 / 239 (top: Thyroid Fixer 525).
- Verdict: fine. Real causes blamed: cortisol (86101/0: "causes negative thinking, weight gain"), mold (195856/3), low vitamin D (191012/1), inflammation and autoimmunity (190817/43). "Weight loss resistant" is the common practitioner term (50134/1, 190547/3). The overlap with `body_composition` is covered below.

### `weight.weight_loss_methods`
- Query: lose weight / losing weight / lost N pounds / weight loss / fat loss / calorie deficit / Noom / WeightWatchers → 25,068 / 15,300 / 315.
- Verdict: fine, but the top podcasts (Armchair 945, Le Batard 626, MeidasTouch 623) are GLP-1 ad carriers. Many "weight loss" hits are glp1 ads, not non-drug methods.
- Real non-drug content is fasting and protein-sparing modified fast (192445/6), sprinting for fat loss (195850/6) and carnivore (16263/14). Named diets correctly go to `diets`.
- "Calories in, calories out / CICO / energy balance" → 671 / 505 / 65. It has no named home; I suggest `body_composition`.

### `weight.body_composition`
- Queries: broad (metabolism, BMR, visceral fat, body fat, DEXA, set point, NEAT) → 27,811 / 15,734 / 357, noisy; strict (slow metabolism, metabolic rate, BMR, TDEE, energy expenditure, visceral fat, body fat percent, DEXA, set point, metabolic adaptation, damaged metabolism) → 4,446 / 2,552 / 142 (Mind Pump 525).
- Verdict: needs a definition change.
  - "Slow metabolism" is used both as a physiological concept (182173/2: "some people are born with a slow metabolism") and as an explanation for weight gain (190812/25: "I was blaming my slow metabolism"). The latter is `weight_gain_causes` by that label's own wording, yet "slow metabolism" is listed here as an example.
  - Metabolism-boosting claims in ads ("these may help boost your metabolism", Juni drink, 26191/84) need a stated home.

### `weight.body_image_stigma`
- Query: body positivity / fat acceptance / shaming / phobia / weight stigma / HAES / body image / body shaming → 3,041 / 2,477 / 195 (top: Watch What Crappens 178, Rogan 176).
- Verdict: fine. Much of it is comedy and reality-TV banter ("We're not body shaming Jordan", 22956/4), which the codebook already handles. Substantive cases exist: "Some people call that fat shaming, but I think fat shaming works for me" (14682/9).

### `weight.weight_loss_surgery`
- Query: bariatric / gastric sleeve / bypass / band / balloon / lap band / weight-loss surgery → 608 / 488 / 101.
- Verdict: fine; the smallest label in the slice but clearly recurring. Seen as:
  - comparison with GLP-1s ("It's just below bariatric surgery", 20597/0);
  - diabetes reversal (181815/11);
  - teen surgery (The Daily, 1140104/6);
  - B12 malabsorption after bypass (192451/2). That case takes the B12 supplement label; surgery only in passing.

### `weight.diet_pills_fat_burners`
- Query: fat burners / phentermine / diet pills / skinny tea / detox tea / Hydroxycut / weight-loss supplements or pills / Contrave / Qsymia / orlistat / garcinia → 817 / 712 / 117.
- Verdict: examples change. The top podcasts are Morning Wire (83) and Megyn Kelly (73), i.e. Daily Wire network ads for "Lean" ("doctors created a weight loss supplement called Lean … lower your blood sugar, burn fat … curb your appetite", 165425/0) and Verso "Cell Being" (318970/1).
  - These ads now position themselves against GLP-1s: "not interested in painful weekly injections".
  - Rule 1 gives `diet_pills_fat_burners` + `insulin_glucose` (stated outcome) + `glp1.natural_alternatives` when positioned as a GLP-1 substitute.
  - "Skinny tea"/"Tummy tea" also occurs in culture talk (156985/4).

### `topic:glp1` (parent) and `glp1.use_results`
- Queries: GLP-1 drug names → 9,977 / 6,739 / 235; ASR variants (GLP one, Ozempik, Wagovi, Monjaro, semi glutide, terzepatide, etc.) → 3,270 / 2,242 / 164; "food noise" → 256 / 183 / 56.
- Verdict: fine as a label; examples need ASR forms. In a random sample of 14 hits, 6 were ads (Hers, Ro, Noom, Mochi, a meal-delivery service's "GLP-1 … meals").
  - Organic use is celebrity speculation ("I would say no Ozempic … with her", 162826/3; Oprah, 63195/1), workplace coverage (203761/0) and comedy.
  - The codebook rule "an unnamed drug that sounds like a GLP-1 is `topic:weight`" matches what I saw: the Lilly OSA campaign never names the drug in-window, "moderate to severe obstructive sleep apnea or OSA in adults with obesity" (3178/1, 29475/2).

### `glp1.side_effects`
- Query: Ozempic face / butt / feet, gastroparesis, NAION, stomach paralysis → 203 / 154 / 60. Broader side-effect talk is not captured by named terms.
- Verdict: fine. Seen: thyroid cancer risk debated ("They saw an uptick in thyroid cancer in the GLP-1 group", 190533/175); muscle loss ("these GLP-1 drugs are eating away muscle tissue", 190662/52); "Ozempic face" (63195/1). Gastroparesis hits are often non-GLP-1 (182342/1), which correctly go to `gut.gi_disease`.

### `glp1.access_compounding`
- Query: compounded semaglutide / tirzepatide / GLP / version, compounding pharmacy → 613 / 406 / 74.
- Verdict: fine; examples change. "Compounding pharmacy" is mostly non-GLP-1 (minoxidil 181832/3, peptides 23757/3, hormones). Real GLP-1 access phrasing is ad copy: "oral medication kits or compounded GLP one injections … $69 a month" (Hers, 8501/2, 13110/4); "Go to Ro.co/journey to see if you qualify" (158483/0).

### `glp1.new_offlabel_uses`
- Queries: microdosing / retatrutide / orforglipron / CagriSema / amycretin / oral semaglutide / Wegovy pill → 2,141 / 1,606 / 47. Armchair (864) and Happier (590) account for 1,454 of those episodes, all Hers "Wegovy pill" reads. Microdosing co-occurring with GLP-1 terms: 395 episodes. GLP-1 within 60 characters of addiction / alcohol / Alzheimer's / inflammation / longevity / PCOS / kidney / CVD / sleep apnea → 180 / 153 / 51.
- Verdict: needs a definition change. Organic content is real: microdosing ("using it at a fifth of the starting dose, compounded droplets … microdosing GLP-1s in their clinics", 182037/3) and off-label uses ("GLP-1s Beyond Weight Loss: Can They Heal Your Gut", Thyroid Fixer). But "oral … drugs" sweeps in every ad for the approved Wegovy pill and Ro's "first FDA-approved GLP-1 pill".

### `glp1.natural_alternatives`
- Query: Nature's Ozempic / natural Ozempic / poor man's Ozempic / natural GLP / boost GLP / GLP-1 booster, probiotic or supplement / Akkermansia → 374 / 307 / 44.
- Verdict: examples change. Real phrasing:
  - "the number one doctor-recommended GLP-1 booster and a natural GLP-1 alternative" (Veracity ad, 42046/9);
  - "designed to increase your body's natural GLP-1 production" (Biomega ad, 606600/4);
  - "This is really like the natural GLP-1" (said of protein, 192469/6);
  - "Nature's Ozempic: Eat These Foods To Kill Cravings" (174934/1).
- Akkermansia hits are mostly plain microbiome talk with no GLP-1 claim (182659/2, 192838/3, 182189/2). As a bare example it pulls microbiome passages into this label.
- Companion products ("GLP-1 friendly" meals, a meal service listing "GLP-1, low-carb meals", 185355/3): 164 episodes in 22 podcasts, ad-driven. These are not substitutes and should not take this label.

### `endocrine.hormone_balance`
- Query: hormone imbalance / balance / panel / health, hormonal imbalance, balancing hormones, endocrine system, endocrinologist → 3,645 / 2,545 / 151.
- Verdict: fine. A sex-specified case correctly goes elsewhere: menstrual cramps from "some sort of issue with hormone balance … estrogen, progesterone" (192905/1) → `womens`.

### `endocrine.thyroid`
- Query: thyroid / hypo- and hyperthyroid / Hashimoto's / Graves' disease / levothyroxine / Synthroid / Armour / reverse T3 → 19,081 / 3,677 / 202 (Thyroid Fixer 658 episodes).
- Verdict: fine. Real nuance: functional "optimal thyroid" talk (190514/48), ferritin for T4→T3 conversion (191024/42, which also takes iron), and T2 as a "forgotten thyroid hormone" that raises basal metabolic rate (190591/72, plus `weight.body_composition`).

### `endocrine.cortisol_adrenal`
- Queries: cortisol / adrenals / adrenal fatigue / burnout / Addison's / Cushing's / HPA axis → 10,404 / 5,467 / 200; adrenal fatigue / burnout / exhaustion alone → 361 / 255 / 43.
- Verdict: needs a definition change.
  - "Cortisol" is often used loosely as a synonym for stress in non-health shows: "you're always kind of cortisol levels, the stress levels are always there" (Morning Brew, 204561/2); "cortisol and adrenaline … predicted whether the couple would get divorced" (185210/9).
  - Health shows use it physiologically: "your cortisol timing" (180774/282); fasted training "driving that cortisol level really high" (179775/1).

### `endocrine.other_hormones`
- Queries: GH / HGH / IGF-1 → 2,999 / 1,864 / 122; leptin / ghrelin → 1,054 / 582 / 61; oxytocin → 1,899 / 1,277 / 129 (top: School of Greatness, SYSK, Modern Wisdom, Please Me!); DHEA and pregnenolone are mostly Thyroid Fixer.
- Verdict: definition change for oxytocin. Oxytocin hits are dominated by bonding and "love hormone" talk in relationship content: "the love hormone gets secreted" (196316/4); "sex and orgasm … release oxytocin … undergirds the attachment bond" (176247/2). That is the same register as `cognition.neurochemistry_talk` (dopamine, serotonin "happy hormone"). Leptin and ghrelin as "hunger hormones" (192909/2) fit here, plus `food.eating_behavior` when appetite is the point.

### `kidney_lung.kidney_urinary`
- Queries: kidney disease / stones / failure / function / damage / transplant, CKD, dialysis, incontinence, overactive bladder, urinary tract, UTI → 4,680 / 3,670 / 230. Split: CKD / stones / dialysis → 2,581 / 2,059 / 196; bladder / UTI / incontinence → 1,938 / 1,553 / 170.
- Verdict: definition change (UTI boundary).
  - Giggly Squad (324 episodes) is a recurring Wisp telehealth ad: "I'd only think about my health when something went wrong—a UTI, a breakout" (157052/3, 156955/3).
  - Pardon My Take (143 episodes) is a host's own kidney stones: "I've still got like ten kidney stones in my body" (128606/12), a correct `passing` use.
  - Noise: "uti possidetis juris" (37495/3).
  - UTIs are listed under `infectious.other_infections` ("UTI as infection"), while this label says "bladder and urinary problems". Coders will split inconsistently.

### `kidney_lung.lungs_breathing`
- Queries: asthma → 2,651 / 2,143 / 194; COPD / emphysema / pulmonary fibrosis / lung function / capacity / health / damage → 871 / 758 / 140.
- Verdict: fine. Seen: mold and asthma (185658/6), salt therapy for "asthma, bronchitis" (195975/5), and historical asthma (324486/4756). "Lung exercises" in sports banter is borderline and was a joke (128684/6).

## Proposed edits

CHANGE `cardiovascular.heart_disease`:
| heart_disease | Heart disease & cardiac events | Coronary and cardiac disease and events and their testing, and atherosclerosis or ASCVD discussed in general (plaque, "clogged arteries") without a non-cardiac site. Plaque explicitly in leg or other peripheral arteries goes to `cardiovascular.blood_circulation`; vaccine-linked myocarditis takes this plus the vaccine subtopic; a heart attack named as a cause of death also takes `acute_care.death_dying`. | heart attack; coronary artery disease; atherosclerosis; ASCVD; clogged arteries; coronary plaque; calcium score; CT angiography; heart failure; AFib; arrhythmia; myocarditis; sudden cardiac arrest; stents |

Why: atherosclerosis vocabulary appears in 907 episodes (130 podcasts), usually with no anatomical site ("atherosclerosis is driven by … smoking, high blood pressure, and high apoB", 175903/9). Carotid plaque is framed as heart-attack risk (199/1). The current anatomical rule cannot be applied to these passages.

CHANGE `cardiovascular.blood_circulation`:
| blood_circulation | Blood vessels & circulation | Blood vessels outside the heart (endothelium, nitric oxide, arterial stiffness, peripheral artery disease, varicose veins) and "circulation" or blood flow as a health subject or product benefit. Atherosclerosis in general goes to `cardiovascular.heart_disease`; clots and blood disorders to `cardiovascular.clots_blood_disorders`. | circulation; blood flow; endothelial function; nitric oxide; arterial stiffness; peripheral artery disease; plaque in leg arteries; varicose veins; Raynaud's |

Why: "circulation" talk (about 6,300 episodes) is mostly wellness and benefit language ("increased microvascular circulation", 6231/8). Nitric oxide (748 episodes, 64 podcasts) is a frequent mechanism subject missing from the examples.

ADD `cardiovascular.clots_blood_disorders` under `cardiovascular`:
| clots_blood_disorders | Blood clots & blood disorders | Blood clots and clotting (DVT, pulmonary embolism, thrombosis, blood thinning), anemia and other disorders of the blood itself (bleeding disorders, iron overload). Iron status also takes the iron supplement subtopic; sickle cell and hemophilia also take `genetics.genetic_conditions`; vaccine-linked clots also take the vaccine subtopic. | blood clots; DVT; pulmonary embolism; thrombosis; blood thinners; anemia; iron-deficiency anemia; hemochromatosis; bleeding disorders; sickle cell |

Why: clot terms appear in 1,819 episodes (185 podcasts), and 516 of those episodes also contain vaccine / jab / AstraZeneca / J&J / spike-protein terms. Anemia and blood disorders appear in 1,321 episodes (167 podcasts): "he uses the terms anemia and iron deficiency interchangeably" (190612/156). Inside a label dominated by "circulation" benefit talk, neither is countable.

CHANGE `cardiovascular.blood_pressure`:
| blood_pressure | Blood pressure | High or low blood pressure and its control, including blood-pressure drugs and products claimed to support blood pressure. | high blood pressure; hypertension; low blood pressure; BP medication; lisinopril; amlodipine; salt and blood pressure; beet supplements for blood pressure |

Why: low blood pressure occurs (175443/4) but the definition says only hypertension. BP-support supplement ads are frequent ("supporting normal blood pressure", 15105/3). BP drugs: 785 episodes, 124 podcasts.

CHANGE `metabolic.insulin_glucose`:
| insulin_glucose | Insulin resistance & blood glucose | Insulin resistance, blood-sugar spikes, crashes and control, low blood sugar outside diabetes, prediabetes, insulin's role in fat storage, metabolic flexibility, uric acid as a metabolic marker, and "metabolic health" or metabolic syndrome outside diagnosed diabetes. "Metabolic dysfunction" meaning cellular energy goes to `metabolic.mitochondria_energy`; gout goes to `musculoskeletal.joints_arthritis`. | insulin resistance; blood sugar spikes; glucose crash; low blood sugar; hypoglycemia; prediabetes; HbA1c; fasting insulin; metabolic syndrome; metabolic flexibility; fat adapted; fructose and uric acid; hyperinsulinemia; insulin as the fat-storage hormone |

Why:
- Hypoglycemia / low blood sugar: 842 episodes, 126 podcasts.
- Metabolic flexibility / fat adapted: 581 episodes, 49 podcasts ("you lose metabolic flexibility", 176575/3).
- The uric-acid content is the fructose-to-uric-acid metabolic account (192544/3), not fatty liver.

CHANGE `metabolic.fatty_liver`:
| fatty_liver | Fatty liver & liver metabolism | Fatty liver disease (NAFLD, MASLD, NASH, MASH) and metabolic liver function, including liver enzymes read as a fatty-liver sign. Other liver disease goes to `gut.liver_gallbladder`; uric acid to `metabolic.insulin_glucose`. | NAFLD; MASLD; MASH; fatty liver; liver fat; elevated ALT; fructose and the liver |

Why: "uric acid" hits are gout in history shows (Boring History tops 771 episodes) or the fructose metabolic account. Some are urolithin A misheard (78329/1). The MASLD rename and ALT are how the subject is discussed (23259/13, 181871/2). Strict fatty-liver terms: 802 episodes, 88 podcasts.

CHANGE `weight.body_composition`:
| body_composition | Metabolism & body composition | Metabolic rate and energy expenditure as physiology, energy balance (calories in, calories out), claims that something boosts metabolism, where fat sits and what it does (visceral fat, fat making estrogen), muscle-to-fat ratio and their measurement. A slow metabolism blamed for someone's weight gain goes to `weight.weight_gain_causes`. | metabolic rate; BMR; energy expenditure; calories in calories out; boost your metabolism; thermic effect of food; visceral fat; body fat percentage; DEXA scan; set point; metabolic adaptation |

Why: "slow metabolism" is used both as physiology (182173/2) and as a weight-gain explanation (190812/25: "I was blaming my slow metabolism"). CICO / energy balance (505 episodes, 65 podcasts) and metabolism-boost ad claims (26191/84, 318970/1) have no stated home.

CHANGE `weight.diet_pills_fat_burners`:
| diet_pills_fat_burners | Weight-loss pills & supplements (non-GLP-1) | Any pill, powder or supplement taken for weight loss other than GLP-1 drugs: fat burners, prescription diet drugs, slimming teas and supplements. One marketed as a substitute for or booster of GLP-1 drugs also takes `glp1.natural_alternatives`. | fat burners; phentermine; Contrave; skinny tea; detox tea for weight; Hydroxycut; forskolin; weight-loss supplements; Lean supplement; metabolism booster pills |

Why: the most frequent real instances are network-wide supplement ads (Lean on Morning Wire and Megyn Kelly). They pitch against GLP-1s: "not interested in painful weekly injections … weight loss supplement called Lean" (165425/0).

CHANGE `glp1.use_results`:
| use_results | GLP-1 use & results | Taking GLP-1 drugs, including approved oral forms, and their weight and glycemic effects in any population: weight loss, who takes them, celebrity use and speculation, effects on appetite and cravings. | Ozempic; Wegovy; Wegovy pill; Mounjaro; Zepbound; semaglutide; tirzepatide; "is she on Ozempic"; food noise; GLP one; Ozempik; Wagovi |

Why: there are 2,242 episodes of ASR variants (164 podcasts). The Wegovy pill is an approved product advertised in hundreds of episodes ("FDA-approved GLP-1 medications that now includes the Wegovy pill", 194224/1). Celebrity speculation is a common organic use (162826/3).

CHANGE `glp1.access_compounding`:
| access_compounding | GLP-1 access, cost & compounding | How people get GLP-1s: prices, insurance and employer coverage, shortages, compounded and telehealth versions, counterfeits. A telehealth service selling GLP-1s takes this, plus `glp1.use_results` only when weight or glucose results are stated; add `health_system.dtc_telehealth` only when the DTC or telehealth model itself is discussed. | compounded semaglutide; compounded GLP-1 injections; Hers; Ro; Noom GLP-1; telehealth GLP-1; cost per month; employer coverage; shortage list; counterfeit Ozempic |

Why: telehealth ads (Hers, Ro, Noom, Mochi) are the bulk of GLP-1 mentions in non-health shows. Many state results ("14 to 20% average weight loss in one year", 158483/0), which the current "takes this alone" wording forbids labeling.

CHANGE `glp1.new_offlabel_uses`:
| new_offlabel_uses | Investigational, microdosed & off-label GLP-1 use | Investigational and not-yet-approved agents, microdosing, and uses for conditions other than weight and blood sugar (addiction, PCOS fertility, fatty liver, inflammation, longevity), which also take the condition's subtopic. Approved oral forms such as the Wegovy pill go to `glp1.use_results`. | microdosing GLP-1; retatrutide; orforglipron (pre-approval); CagriSema; GLP-1 for addiction; GLP-1 for alcohol; GLP-1 for PCOS; GLP-1 for inflammation |

Why: of the 1,606 episodes matching oral and next-generation terms, 1,454 come from two podcasts, all Hers Wegovy-pill reads. Genuine content here is microdosing (395 episodes co-occur) and off-label uses (153 episodes for a narrow proximity query), e.g. "using it at a fifth of the starting dose, compounded droplets" (182037/3).

CHANGE `glp1.natural_alternatives`:
| natural_alternatives | "Natural" GLP-1 alternatives | Foods, supplements and products marketed or described as substitutes for GLP-1 drugs or as boosting GLP-1 naturally. Products sold to people taking GLP-1s (GLP-1-friendly meals) are not substitutes and take the product's own subtopic. A microbe named with no GLP-1 claim goes to `gut.microbiome`. | berberine "nature's Ozempic"; natural GLP-1 alternative; GLP-1 booster; GLP-1 probiotic; foods that boost GLP-1; protein as "the natural GLP-1" |

Why: real phrasing is "GLP-1 booster and a natural GLP-1 alternative" (42046/9), "increase your body's natural GLP-1 production" (606600/4) and "the natural GLP-1" (192469/6). Most Akkermansia hits make no GLP-1 claim (182659/2, 192838/3), and GLP-1-friendly meal ads (185355/3) are companion products, not substitutes.

CHANGE `endocrine.cortisol_adrenal`:
| cortisol_adrenal | Cortisol & adrenal function | Cortisol as a hormone (its levels, rhythm, testing and effects such as belly fat) and adrenal function and disorders. "Cortisol" used only as a word for feeling stressed goes to `stress`. | cortisol levels; high cortisol; cortisol and belly fat; cortisol rhythm; HPA axis; adrenal fatigue; adrenal burnout; Addison's; Cushing's; cortisol face |

Why: cortisol appears in 5,467 episodes (200 podcasts), many with loose stress-shorthand uses ("always kind of cortisol levels, the stress levels are always there", 204561/2). Physiological uses look different ("your cortisol timing", 180774/282; cortisol "causes … weight gain", 86101/0).

CHANGE `endocrine.other_hormones`:
| other_hormones | Other hormones | Growth hormone, IGF-1, DHEA, pregnenolone, oxytocin, melatonin as a hormone, leptin, ghrelin and similar, when the hormone's levels, physiology or use are discussed. A hormone used for physique or performance also takes its `peds` subtopic; insulin goes to `metabolic.insulin_glucose`; oxytocin as the "love hormone" in talk about bonding goes to `cognition.neurochemistry_talk`. | growth hormone; IGF-1; DHEA; pregnenolone; oxytocin therapy; leptin resistance; ghrelin; hunger hormones |

Why: oxytocin appears in 1,277 episodes (129 podcasts), led by relationship and self-help shows. Typical use is "the love hormone gets secreted" (196316/4), which is the dopamine / serotonin "happy hormone" register already defined in `cognition.neurochemistry_talk`.

CHANGE `kidney_lung.kidney_urinary`:
| kidney_urinary | Kidneys & urinary tract | Kidney disease and function, kidney stones, dialysis, and bladder and urinary problems such as incontinence and overactive bladder. A urinary tract infection as an infection goes to `infectious.other_infections`; add this label only when bladder or urinary health beyond the infection is discussed. Prostate-related urination goes to `mens.prostate`. | kidney stones; chronic kidney disease; kidney function; dialysis; overactive bladder; incontinence; bladder leaks |

Why: bladder / UTI hits total 1,553 episodes. The top podcast is a recurring Wisp UTI ad (Giggly Squad, 324 episodes; 157052/3). The two existing definitions both claim UTIs.

## Codebook and prompt notes

1. **Section 4.1, "Topics inside ads": drug-ad safety information.** Add a rule along these lines: "In a drug ad's mandated safety information (side effects, warnings, 'tell your doctor if…'), listed adverse effects do not get their own topic detections. The ad takes the advertised drug's subject and any benefit it claims." Evidence:
   - Nurtec's "High blood pressure and Raynaud's syndrome can occur" makes Hidden Brain the #1 "blood pressure" podcast (515 episodes; 170345/0).
   - Rexulti's "High blood sugar can lead to coma or death. Weight gain, increased cholesterol" (165245/3) would otherwise add three topics from this slice.
   - Ro's "To stay informed about serious side effects" closes every GLP-1 read.
2. **Section 3, "Ads": eligibility lists in non-health ads.** Life-insurance ads list conditions as eligibility: "Have high blood pressure, diabetes, or heart disease? SelectQuote has partners…" (63837/3, 81707/1, frequent on MeidasTouch). Say whether these fail the ad test or take one `passing` advertisement detection. I suggest they fail: no health effect is claimed and no health product is sold.
3. **Section 4.1 / analysis: GLP-1 ad saturation.** Dynamic ad insertion places 2025–26 GLP-1 ads into old back-catalogue episodes (a 2018 Happier episode, 194224/1, carries the 2026 Hers Wegovy-pill read). Any GLP-1 trend analysis must split `relevance: advertisement` out, and episode dates do not date the ads. Worth a line in the analysis docs. The labeler needs the subtopic rule in the `access_compounding` edit above to code these reads consistently.
4. **Section 3, "Violence, crime, war and death": heart attack as cause of death.** True crime and history are a large share of heart-attack hits ("suffered a heart attack. He died three days later", 21556/4). State whether the condition's subtopic is added to `acute_care.death_dying`. I suggest yes, as `passing` (`cardiovascular.heart_disease`), and the same for strokes and aneurysms ("died suddenly from an aneurysm", 319462/2). Add hyperbolic deaths ("work until you die of a heart attack when you're 33", 629264/1) and "gets my blood pressure going" (194630/11) to the idiom examples in the exclude list.
5. **Section 5.1, "General talk takes the parent": stress words.** Add "cortisol" used as a word for stress, and "the love hormone" for oxytocin, to the general-talk guidance, with pointers to `stress` and `cognition.neurochemistry_talk` (see the edits above).
6. **Section 2 (ASR) or a prompt glossary.** Useful variants:
   - GLP-1: "GLP one", "G L P one", "Ozempik", "Wagovy" / "Wegovi" / "Wigovi", "Monjaro", "semi glutide", "terzepatide" (2,242 episodes).
   - Lp(a): "Lp little a".
   - Urolithin A: "uric acid A", "urate and A", "urea thion A". Don't code these as uric acid.
   - Damar Hamlin and "died suddenly" appear in sports and politics shows. "Died Suddenly" as an account or film name (6327/9) carries the vaccine narrative under section 5.2's coined-term rule. As an ordinary obituary phrase ("the director of the class play died suddenly", 1135310/1) it carries nothing.
7. **Section 5.1, co-labeling rule 1 example: ads that pitch a supplement as a GLP-1 substitute.** "Doctors created a weight loss supplement called Lean … lower your blood sugar, burn fat … curb your appetite" (165425/0) should be coded as `weight.diet_pills_fat_burners` + `glp1.natural_alternatives` (positioned against "painful weekly injections") + `metabolic.insulin_glucose` (stated outcome). This read recurs on Daily Wire shows and IHIP News and is a good worked example for the prompt.
8. **Section 5.1, "Unsettled facts about a person".** The GLP-1 rule ("an unnamed drug that sounds like a GLP-1 is `topic:weight` unless a GLP-1 term appears") fits celebrity weight-loss gossip well. Extend the example to speculation: "is she on Ozempic" names the drug, so it takes `glp1.use_results` at `passing` (162826/3). "He lost forty pounds, must be on something" stays `topic:weight`.
