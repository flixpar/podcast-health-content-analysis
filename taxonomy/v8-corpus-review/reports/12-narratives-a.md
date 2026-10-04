# Narratives A (vaccines, COVID, cancer, food): corpus review

Scope: `vaccines_narratives` (24), `covid_narratives` (14), `cancer_narratives` (9), `food_narratives` (23) in `taxonomy/health-v8.md`. Counts are `cq.py count` hits for a regex built from the narrative's core proposition and its real vocabulary (segments / episodes / podcasts). They are rough: proposition-shaped regexes miss paraphrase and catch neighbours, so every verdict below rests on reading samples (8 to 12 per label), not on the count alone. "Proposition-level" means the regex needs the claim, not just the subject.

## Summary

- **Almost every narrative in this slice is voiced in the corpus as a proposition, not just as a subject.** The big ones (proposition-level episodes): ivermectin ~1,100 (all mentions), lab leak ~1,200, pandemic censorship ~1,100, seed oils toxic ~600, vaccines-autism ~520, natural immunity ~520, myocarditis ~600, masks ~470. Most live in about 15 shows (Charlie Kirk, Rogan, Megyn Kelly, Culture Apothecary, Hyman, Jockers, Brecka, Thyroid Fixer, Tucker), but rebuttals are spread widely (Science Vs, Behind the Bastards, Maintenance Phase, MeidasTouch, Pod Save America).
- **Four labels are essentially absent or have a core nobody states:** `cancer_fungus_parasite` (about 3 episodes), `nsaids_worsen_covid` (about 10, all from the March 2020 scare), `sugar_hyperactivity` (a handful; "sugar high" is almost always a figure of speech), and `cancer_epidemic_young`, whose required "ignored or hidden" clause I almost never found. The rise in young-onset cancer is talked about as a mystery ("perplexing everybody", "we don't know why"), which is topic material. I propose removing all four, with routing notes.
- **Ad copy dominates several narratives' raw hits, and the codebook needs clearer rules for it.** "No seed oils" appears in about 4,400 episodes (Nature Raised Farms in 3,588 Watch What Crappens episodes, Masa chips in about 240 Tucker episodes, Forkful). Ivermectin pharmacy and kit ads (All Family Pharmacy, The Wellness Company, Jase) run in about 160 episodes across 11 podcasts. Most of these state no proposition. A few do, e.g. the Wellness Company's "parasite cleanse, ivermectin and mebendazole, has shown success in triggering cancer cell death", which states `antiparasitics_cure_cancer`.
- **The coined term "died suddenly" mostly means nothing more than that someone died suddenly.** About 3 of 12 sampled hits were the vaccine coinage; the rest were obituaries, true crime and history (364 episodes in 122 podcasts). Codebook 5.2 currently says the term always carries the proposition. Likewise "soy boy" is overwhelmingly a political insult, not a claim that soy feminizes, and "jab injured" / "vaccine injured" has no narrative it maps to.
- **The codebook rule "verbs of benefit are interchangeable" ('fights' counts) over-triggers cure narratives.** "Anti-cancer properties/compounds", "cancer-fighting foods" and "starve cancer" (angiogenesis foods, Dr. William Li) appear in about 330 episodes. They describe a property or prevention, not curing an existing cancer.
- **Several cores are narrower than how people say them.** Liability: "the schedule exploded because they can't be sued." Natural immunity: "they refused to recognize natural immunity". Injury hidden: "the vaccine injured are being gaslit." Food dyes: "red dye causes cancer and the FDA banned it." US food vs abroad: "I eat bread in Italy and feel fine." Myocarditis: the mainstream "rare but real" statement needs a boundary. Food engineered: "engineered to make you overeat" is mainstream ultra-processed-food talk and should not take a malice narrative.
- **Gaps found:** (1) Denying that LDL or blood cholesterol causes heart disease (about 170 episodes, 41 podcasts, much of it rebutted by Attia and Kahn). I propose folding it into `saturated_fat_cholesterol_myth`. (2) "COVID is mild for kids, so they don't need the vaccine" (about 70 episodes, 44 podcasts); I propose extending `covid_severity_exaggerated`. (3) "Salt fears are overblown" (about 44 proposition-level episodes, 23 podcasts); a modest ADD.
- **Possible merges, not proposed:** `beef_tallow_healthier` and `seed_oils_toxic` share half their episodes (705 of 1,425 tallow episodes also say "seed oil"), but they are different propositions. I kept them and added a boundary instead. `covid_bioweapon_plandemic` overlaps `covid_lab_leak` through "Fauci funded a bioweapon"; the definition needs a deliberate-release or weapon test.

## Label-by-label findings

### Vaccines `vaccines_narratives`

| label | query (abridged) | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| vaccines_cause_autism | `(vaccin\|vax\|mmr\|jab).{0,80}autis` both orders | 711 / 524 / 91 | fine; examples change |
| vaccine_ingredients_toxic | aluminum, thimerosal, mercury, formaldehyde, fetal cells near vaccin | ~300 / ~240 / ~45 | needs definition change |
| too_many_too_soon | too many shots, 72/76 doses, spacing, slower schedule, bundle | 260 / 242 / 77 | fine |
| hep_b_birth_dose_unneeded | hep B near birth, newborn, baby | 167 / 141 / 50 | examples change |
| vaccines_cause_sids | SIDS co-occurring with vaccin (episode cooc) | 36 eps total; about 15 invoke it | rare but keep |
| vaccines_chronic_disease | vaxxed vs unvaxxed; Henry Ford study; Amish | 38 + 33 + 27 eps | fine |
| vaccines_didnt_end_disease | Dissolving Illusions; DDT and polio | 24 + 16 eps / ~10 pods | definition change (polio) |
| vaccine_injury_hidden | VAERS, Lazarus, underreport | 121 segs / ~100 eps / 24 | definition change |
| vaccine_makers_no_liability | liability, can't sue, 1986 Act, PREP Act | 357 segs / ~300 eps / ~90 | definition change |
| vaccines_not_placebo_tested | saline/inert placebo, never tested | 234 segs (placebo subset) | fine |
| natural_immunity_superior | `natural immunity` | 663 / 524 / 69 | definition change |
| hpv_vaccine_harm | Gardasil, HPV vaccine | 147 / 118 / 44 | fine (many neutral) |
| flu_shot_ineffective_harmful | flu shot plus "gave me the flu", "doesn't work", % effective | 74 / 73 / 40 | fine, modest |
| covid_vaccine_deaths | died suddenly near jab; athletes collapsing | 100 segs; 111 eps athlete-collapse | examples change; codebook note |
| covid_vaccine_myocarditis | `myocarditis` | 777 / 604 / 79 | definition change (boundary) |
| turbo_cancer | `turbo ?cancer` | 67 / 57 / 19 | fine |
| mrna_alters_dna | gene therapy, alter DNA, SV40, DNA contamination | ~440 segs (noisy) / ~90 pods | fine |
| vaccine_shedding | shedding near vaccine or spike | 39 / 38 / 23 | fine (often mocked) |
| covid_vaccine_fertility | vaccine near miscarriage, infertility, menstrual | 171 segs | fine |
| spike_protein_persistent | spike protein persists, detox, nattokinase | 104 / 74 / 28 | definition change |
| covid_vaccine_ineffective | safe and effective; didn't stop transmission | 1,397 / 1,251 / 171 (very noisy) | fine; codebook note |
| measles_harmless | measles near mild, parties, vitamin A, cod liver | 55 / 46 / 24 | definition change |
| vaccine_microchips_5g | microchip near vaccin; graphene oxide; luciferase | 85 segs / ~80 eps | fine; almost always rebutted |
| vaccines_for_profit | vaccine or booster near profit, billions | 277 segs | fine; premise note |

Notes and quotes:

- **Autism.** The real elaborations: the schedule-size argument ("I had seven doses... now there's 72, the rate of autism was about one in ten thousand", ep 186532 seg 1), "the bundle of vaccines... is the trigger for the development of autism" (185634/0), and **the Amish** ("They don't have any SIDS, no autism", 1353/7; "the only Amish that turned out to have autism are the ones that were adopted, and vaccinated", 68328/8; 27 episodes, 16 podcasts). Wakefield appears in 209 episodes, mostly as history or rebuttal. "Lost his words after the vaccines" is rare (36 episodes for regression wording).
- **Ingredients.** Real phrasing: "levels of aluminum in that vaccine that are so off the Richter scale" (185726/4); "we want no mercury in the vaccine. We want no aluminum" (Trump, 314371/0); "thimerosal... It's got lead in it, mercury" (42315/2). Two boundary cases: (a) **Fetal cells as a moral objection** ("I'm not comfortable injecting my two boys with aborted fetal tissue", 37535/3) claims no harm and should not take the narrative. (b) **Contaminants**: SV40 and the polio vaccine causing cancer ("the polio vaccine ended up giving cervical cancer to millions of women", 77368/3; SV40 in 44 episodes, 15 podcasts). This is neither COVID nor turbo cancer, and the definition should name contaminants.
- **Hep B.** People actually say: "Newborns who are obviously participating in the high risk behavior" (sarcasm, 6353/4); "Your brand new perfect baby does not need the Hep B vaccine. That is for somebody who's going to be exposed to prostitutes and STDs and sharing needles" (37294/2). Since December 2025 many hits are news that the CDC or ACIP dropped the newborn recommendation (42259/1, 185624/6). That is a policy topic, not the narrative, unless "unneeded" or "harmful" is said.
- **SIDS.** Rare but present, often tied to the package insert: "a product given to their young infant can cause sudden infant death syndrome" (185794/2); "the big bundle of vaccines, sudden infant death, febrile seizures" (185634/4). Keep it for its research importance.
- **Injury hidden.** Real phrasing goes beyond "underreported": "the vaccine injured are still being gaslit" (37390/0); "Nobody is really admitting that there are vaccine injuries" (39273/1); "a surveillance system that was built to fail" (11412/6). VAERS counts cited for a specific harm ("abundant evidence in VAERS... a signal around miscarriage", 39588/1) are evidence for that harm's narrative (`covid_vaccine_fertility`) plus `evidence:official_data_documents`. They are not this narrative unless underreporting or mass hidden harm is the point.
- **Liability.** The conclusion people draw is often about the schedule or the incentive, not testing: "Why has the childhood vaccine schedule exploded to over seventy shots? Money... because they can't be sued" (185815/1); "once the pharma companies knew you're not going to get sued anymore... they go from" (204866/0); "if you're arguing that all these vaccines are safe... then why do they need the liability protection?" (3732/8). The current core ("unsafe or untested because makers cannot be sued") misses the first two.
- **Natural immunity.** About 90% COVID-specific and tied to mandates: "people that have already had natural immunity and antibodies are still also being forced to take the vaccine" (40349/1); "recognizing natural immunity" (169685/0); "Israel study showed it's 27 times" (13819/8). Many passages claim equivalence ("should count") rather than superiority.
- **Died suddenly and covid_vaccine_deaths.** See the codebook notes. The vaccine coinage appears as "the movie Died Suddenly" (39370/3), "the died suddenly" (204719/8), and "athletes dropping dead on the field" (205362/6, 78264/3). **SADS** ("Turbo cancer and sad sudden arrhythmic death syndrome", 204993/1) is a second coined term worth listing.
- **Myocarditis.** Most passages acknowledge a real, rare risk ("the rare but real risk of myocarditis", 14136/7; "that's how the myocarditis risk was picked up in young men", 325354/8). These are neither assertions nor rebuttals of "common, serious or concealed". Contrast the narrative proper: "something they tried to hide from us" (7865/8); "The CDC repeatedly and consistently downplayed the issue" (8538/4).
- **Spike protein.** Besides persistence there is a distinct "the spike protein is toxic" claim ("the spike proteins are toxic. And the FDA was warned", 40508/1). The remedy talk is "spike protein detox" with "nattokinase, bromelain, curcumin" (8519/7, 318982/9, 195362/3).
- **Measles.** "It's not a fatal infection in a well-nourished nation... let's feed our kids vitamin A foods" (185624/5); "Measles is very well supported. It's a mild illness. Mumps, again, very supportable" (38874/2); "We used to have measles parties, and chickenpox parties" (40058/1). Chickenpox parties recur too (45 episodes, 24 podcasts), mostly nostalgic. The narrative should cover the same claim about other childhood infections.
- **Microchips.** Almost every hit is mockery or a straw man ("Bill Gates is like... You're worried about vaccines and me putting microchips in Indian kids", 322024/6; 175855/2). Under 5.2 these are `rebutted` and must still be coded. One real elaboration missing from the examples: "putting magnets on the site where they got vaccinated" (12690/13).
- **Profit.** A bare revenue fact ("the COVID vaccine is the most profitable medical product in history", 319124/6) is a premise. The narrative needs "pushed for profit" ("How many more billions do we have to give... Pfizer and Moderna before", 40526/2).
- **Flu shot.** Mostly neutral "I got my flu shot". There are 1,039 GoodRx ad hits for "flu shot... if you do get sick", which are not the narrative. The narrative proper ("You can get the flu. That's what they're injecting", 70879/0) appears in about 40 episodes.

### COVID-19 `covid_narratives`

| label | query (abridged) | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| covid_lab_leak | lab leak, Wuhan institute or lab, gain of function | 1,842 / 1,226 / 73 | fine |
| covid_bioweapon_plandemic | plandemic, bioweapon, Event 201, planned pandemic | 752 / 619 / 83 | needs definition change (boundary) |
| ivermectin_covid | ivermectin and ASR variants, horse dewormer | 1,538 / 1,126 / 81 | fine; ad note |
| hcq_covid | hydroxychloroquine, HCQ, Zelenko | (seen in ivermectin samples) | fine |
| early_treatment_suppressed | early treatment; EUA "no other effective treatment"; suppressed treatment | 412 / 320 / 64 | fine; list note |
| hospital_protocols_killed | remdesivir, run death, ventilators killed, paid per COVID patient | 210 / 177 / 52 | fine |
| masks_useless_harmful | masks don't work, cloth masks, masking kids | 542 / 466 / 55 | fine |
| lockdowns_worse_than_virus | lockdowns near "more harm", disaster; school closures near harm | 71 / 68 / 27 (narrow) | fine |
| covid_deaths_inflated | died with not from, cycle threshold, motorcycle | 111 / 104 / 37 | fine |
| covid_severity_exaggerated | just the flu, 99.x% survival | 83 segs with COVID context | needs definition change |
| long_covid_not_real | long COVID near not real, anxiety, vaccine injury | 33 / 30 / 20 | fine, rare |
| vitamin_d_prevents_covid | vitamin D, zinc, quercetin near COVID | 328 / 286 / 50 | fine |
| pandemic_censorship | Twitter files, Great Barrington, censor near COVID or doctors | 1,402 / 1,093 / 96 | fine |
| nsaids_worsen_covid | ibuprofen, Advil, NSAID near COVID | 23 / 21 / 16, about 10 real | remove |

Notes and quotes:

- **Bioweapon vs lab leak.** "Fauci obviously created a bioweapon. He funded a bioweapon. I'm not saying that the gain of function stuff" (205647/2) shows "bioweapon" used loosely for an engineered virus that leaked by accident. The current core ("deliberately made or released") also fits any gain-of-function virus, which is deliberately made. The core needs "as a weapon, or released on purpose, or the pandemic planned".
- **Ivermectin ads.** Example reads: "when your doctor refuses to prescribe medications like ivermectin, even after you've done your research, All Family Pharmacy gives you another option" (42192/5); "The Wellness Company's medical emergency kit includes... ivermectin" (38363/2). These state no COVID proposition, so no narrative applies. They take `frame:anti_mainstream_medicine` and `frame:commercialization` plus a product mention. "Ivermectin and mebendazole... researched for their off-label potential... to support cancer" (42295/2) is the cancer narrative, not COVID.
- **Early treatment.** "We suppressed early treatments. We didn't allow people that get their vitamin D levels up" (39960/3). The list form is common: "You lied about the vaccine. You lied about school closures. You lied about the mask. You lied about early treatments" (38529/2). See the codebook note.
- **Severity.** "Kids have a ninety nine point nine nine seven percent survival rate" (205481/5) is used to argue for no vaccines or mandates for children: "children have a 99.99% survival rate from COVID, and they say that makes the vaccine largely unnecessary for them" (169936/0); "young people do not need a booster" (389455/2). About 70 episodes in 44 podcasts say kids or the young don't need the COVID vaccine. No narrative covers this; the closest is "the response was disproportionate".
- **Long COVID.** The usual form is "long COVID is really vaccine injury" ("seventy percent of all long COVID is really due to the vaccine", 174986/7; "vaccine injured, not that long COVID bullshit", 205014/6). That fits the definition as written.
- **NSAIDs.** Only the 2020 French scare and its debunks (318550/0, 178268/0, 86908/2). Not a recurring narrative.
- **Immune damage from boosters.** "IgG4" and "repeat boosters may actually weaken the immune system" (169690/0, 7806/5) are rare (29 episodes). They fit `covid_vaccine_ineffective` ("make infection worse"); add an example.

### Cancer `cancer_narratives`

| label | query (abridged) | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| cancer_cures_suppressed | cure for cancer near hiding, no money, don't want; cancer industry | 45 / 41 / 28 | fine (often rebutted) |
| antiparasitics_cure_cancer | fenbendazole, fenben, mebendazole, Tippens; ivermectin near cancer | 115 / 101 / 28 | fine; ad note; ASR variants |
| sugar_feeds_cancer | sugar feeds cancer; starve cancer; keto near cancer | 201 / 162 / 37 | definition change (boundary) |
| cancer_metabolic_disease | Seyfried, \bwarburg\b, metabolic disease of cancer | 398 / 288 / 62 (about 60 eps are "Amanda Seyfried") | fine; boundary |
| cancer_fungus_parasite | cancer is a fungus or parasite; Simoncini; baking soda cancer | 7 / 7 / 4 | remove |
| chemo_does_more_harm | chemo is poison or toxic, kills more, oncologists wouldn't take it | 207 / 174 / 67 (mostly analogies and patients) | fine, moderate |
| natural_remedy_cures_cancer | B17, apricot seeds, Gerson, Essiac, Budwig, Rick Simpson oil near cancer | 167 / 149 / 51 | definition change (prevention boundary) |
| cancer_screening_harmful | mammogram or biopsy near causes cancer, spread, radiation, overdiagnosis | 258 segs, 109 of them a Chiro Hustle thermography ad | fine |
| cancer_epidemic_young | young or early-onset near cancer; "nobody asks why" | 341 eps for the rise; proposition near 0 | remove |

Notes and quotes:

- **Antiparasitics.** Real phrasing and ASR variants: "fenbendazole and mebendazole and iver" (176557/1), "membenzol", "mbenbendazole" (48633/3, 48619/3), "Medbendazol" (190479/9). Ads state it outright: "the gold standard parasite cleanse, which is ivermectin and membenzol, has shown success in triggering cancer cell death" (48633/3, Candace; recurs). Tucker: "80% of the people who took ivermectin for their cancer saw either a complete remission" (33371/6).
- **"Starve cancer".** This is not always about sugar. Dr. William Li's "Can We Eat to Starve Cancer?" (183909/0) and the Mayo doctor's "heal the body, starve cancer" (40268/0) mean anti-angiogenic foods. That belongs to `natural_remedy_cures_cancer` only if treatment is claimed, and never to `sugar_feeds_cancer`.
- **Metabolic.** The mainstream "Warburg phenomenon" as a treatment target (Attia, 181570/7) is mechanism talk, not "cancer is not genetic". The narrative proper: "Otto Warburg... the cause of cancer is" (174993/8); "if cancer is a metabolic disease" (190372/152).
- **Fungus or parasite.** The only real hits: "cancer is a bacteria that cannot thrive in an alkaline, oxygen-rich" (Simoncini, misspelled "Simontelli", 176668/1) and "Do I believe that all cancer is parasites? No" (190449/55). Baking soda cures go to `natural_remedy_cures_cancer`, alkaline-body claims to `alkaline_ph`, parasites to `parasites_cause_disease`.
- **Chemo.** "We've been lied to... Saying your only option is chemotherapy and radiation and surgery" (178190/0); "the tools... a mammogram or a PSA test or PET scans... they're all going to cause cancer" (186340/2, which is the screening narrative). "Chemo is poison" is mostly used as a metaphor for politics (438986/3, 323867/7), which is excluded as an idiom.
- **Natural remedy and prevention.** "anti-cancer properties" or "anti-cancer compounds" (Tongkat, berries, modified citrus pectin; 190828/44, 7576/13, 174958/4) and "cancer-fighting foods" appear in about 330 episodes. Under the current "fights counts" rule all of them could be coded as `natural_remedy_cures_cancer`. Proposition-level cure talk ("I got cancer, ditched chemo and healed naturally", 185896; "friends that... cured their own cancer from... a plant-based alkaline diet", 70955/16) is much narrower.
- **Early-onset cancer.** What people say: "younger and younger people are getting colon cancer and it's perplexing everybody. You know, I think I know why" (25957/132); "an unprecedented number of young people that are dying to cancer" (63258/7); "we don't know. Why? There's a lot of looking into that" (196448/7). The "ignored or hidden" clause in the core is essentially never stated. A vaccine cause is `turbo_cancer`; food or chemical causes are causal claims under `cancer.causes_rates`.

### Food & diet `food_narratives`

| label | query (abridged) | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| seed_oils_toxic | seed oils near toxic, inflammatory, cause; avoid or ditch seed oils | 798 / 596 / 65 (all mentions 6,081 eps, about 4,400 "no seed oils" ads) | fine; ad note |
| saturated_fat_cholesterol_myth | Ancel Keys, diet-heart, sat fat myth or demonized, butter is back | 488 / 361 / 51 | definition change (add LDL) |
| sugar_is_toxic | sugar is poison or a drug; more addictive than cocaine | 93 / 89 / 47 | fine |
| sugar_hyperactivity | sugar high or rush; kids near sugar near hyper | 630 segs, nearly all idiom or glucose talk | remove |
| food_dyes_harm_children | red dye, Red 40, food dyes, artificial colors (non-numeric) | 2,284 / 2,004 / 164 (ads inflate) | definition change |
| raw_milk_superior | raw milk, raw dairy | 711 / 524 / 84 | fine; implicature note |
| gmo_harmful | GMO near harm, cancer, sick | 192 segs (all GMO 2,663 eps, mostly "non-GMO" ads) | fine |
| glyphosate_poisoning | glyphosate (and ASR "glyphosphate") | 1,897 segs | fine |
| artificial_sweeteners_harm | aspartame, sucralose, diet soda near cancer, gut, insulin | 407 / 361 / 84 | fine |
| gluten_harms_everyone | gluten or wheat near leaky gut, zonulin, everyone; modern wheat | 831 / 667 / 85 | fine |
| food_engineered_to_harm | they're poisoning us; designed to make you sick or addict | 91 / 91 / 32 | needs definition change (boundary) |
| us_food_banned_elsewhere | banned in Europe; same product, different ingredients | 211 / 200 / 59 | definition and examples change |
| carnivore_cures | carnivore near cured, healed, reversed | 277 / 236 / 54 | fine |
| plants_are_toxic | \boxalates\b, \blectins\b, plant toxins, antinutrients | 855 / 536 / 67 | fine; boundary |
| fasting_cures | fasting or keto near cure, reverse; reverse diabetes | 249 / 225 / 43 | fine |
| alkaline_ph | alkaline water or diet; acidic body; pH balance | 706 / 568 / 108 | fine |
| wellness_waters | structured, hydrogen, EZ water; molecular hydrogen | 1,375 / 631 / 81 ("living water" Bible noise) | fine; ad note |
| soy_feminizes | soy near estrogen or testosterone; soy boy; phytoestrogens | 454 / 363 / 77 | examples change; codebook note |
| beef_tallow_healthier | tallow, lard | 1,824 / 1,436 / 136 (Masa ads, candles in history shows) | fine; boundary |
| red_meat_healthy | red meat not the enemy, demonized | 38 / 35 / 23 (narrow) | fine |
| microwave_radiation_food | microwave near nutrients, radiation, cancer | 198 / 175 / 69 (includes physics) | needs definition change |
| soil_depletion_supplements | soil depleted; can't get it from food | 424 / 377 / 48 (Hyman 170, a recurring read) | fine; ad note |
| alcohol_moderate_protective | French paradox, J-curve, a glass of red wine is good | 279 / 250 / 67 | fine (now mostly rebutted) |

Notes and quotes:

- **Seed oils.** The narrative proper: "chips... Seed oils, for example... can make you feel" (5681/1); "Heart-Healthy Seed Oils Are Actually Poison" (Brecka title). The ad boundary: "three simple ingredients: corn, salt, and 100% grass-fed beef tallow, no garbage, no seed oils. What a relief! And you feel the difference" (Tucker / Masa, 6683/4 and 7518/2). "Garbage" and "you feel the difference" disparage, but there is no harm proposition, so this stays a frame. See the codebook note.
- **LDL denial (gap).** "lean mass hyperresponder phenotype... very metabolically healthy" (192594/2); "no cholesterol doesn't... cause heart" (174986/9). Rebuttals: "if you tell me that cholesterol doesn't matter, let me introduce you" (Joel Kahn, 181216/4); "people like to stop at that and say, 'Well, look, that means LDL doesn't matter'" (Dayspring on Attia, 181853/3). None of the listed narratives covers blood cholesterol. `statins_harmful` covers only the drug.
- **Food dyes.** Cancer is as common as ADHD: "I was called a conspiracy theorist because I said red dye caused cancer, and now FDA has acknowledged that and banned it" (RFK quoted, 204990/6); "linked to behavioral issues, chronic disease, and things like cancer" (78331/3). The harm claimed is not only to children.
- **US food vs abroad.** Besides "banned in Europe", the commonest form is the travel anecdote (26 episodes, 11 podcasts): "you go to Italy and eat a fat bowl of bread and bowl of pasta, and you feel fine" (37622/2); "you eat bread in Europe, you don't feel like shit" (Brecka on Rogan, 6231/2).
- **Food engineered to harm.** "Processed foods are very well engineered to make you overeat" (Mind Pump, 195480/0; also Tim Spector, 72189/1) is mainstream ultra-processed-food talk about hyperpalatability with no malice alleged. The narrative proper: "we're poisoning our kids. We're poisoning them chiefly by food" (182053/0); "The people that are poisoning us with our foods are selling us their snake oil" (189369/1). Rebuttal: "I don't subscribe to the theory that there's an evil wizard behind the curtain that is intentionally trying to make people sick" (Calley Means, 176923/0).
- **Soy.** "soy boy" is an insult ("that's a very soy boy attitude", 14233/11; 5114/4; 90748/4). The claim proper: "the intake of these phytoestrogens... dysregulated her own hormones" (190701/34); rebuttal: "Good quality data says soy doesn't lower" testosterone (181008/1).
- **Plants.** A low-oxalate diet for oxalate sensitivity (192684/1, 192681/3) is not "plants are toxic". The narrative proper: "I don't think we need to be eating gobs of kale... there are plant toxins" (185637/7).
- **Microwave.** The commonest real health claim is plastics: "heating it up in the microwave, and leaching microplastics" (176667/7; 439308/2; 181086/2). That belongs to the environment narratives. The oven-radiation claim exists ("Lon said his wife threw out their microwave... concern that it could cause cancer", 314218/1; "I feel like I'm gonna get cancer if I'm just around a microwave", 52662/12), but it is about the oven, not the food. "Destroys nutrients" is barely voiced.
- **Soil depletion.** A recurring Hyman read: "even when we eat super well, most of us are missing out... Our soils have become depleted" (182661/0). It states the narrative ("that's why I recommend", 182360/1), so it is coded as `advertisement` / `asserted`.
- **Salt (gap).** "Fourth myth is going to be that salt is bad for you" (Jockers, 192531/1); "Demonization of salt over sugar" (176917/5); "he was not sort of part of this salt is bad bandwagon" (Attia, 181765/7). The proposition-level query found 44 episodes in 23 podcasts, and the wider "salt your water / need more salt" talk is much larger.
- **Lab-grown or fake meat** ("ultra-processed garbage", 6155/12; "Bill Gates' fake meat", 8438/3) has about 45 proposition-level hits. I did not propose it; it is food topic material plus `depopulation_agenda` when the Gates/control angle is stated.

## Proposed edits

CHANGE `vaccines_cause_autism`:
| vaccines_cause_autism | Vaccines cause autism | **Vaccines cause autism or developmental regression.** Any vaccine or the schedule (often MMR, or the number of shots) is blamed for autism, the rise in autism, or loss of speech and developmental delays after shots; low autism in unvaccinated groups such as the Amish is offered as proof. | Wakefield; MMR autism; "my son regressed after his shots"; the bundle of vaccines triggers autism; the Amish don't vaccinate and don't have autism | vaccines |
Why: the Amish argument recurs (27 episodes, 16 podcasts; 1353/7, 68328/8, 5194/5) and is the main form in 2024-26 talk. The regression example is rare (36 episodes).

CHANGE `vaccine_ingredients_toxic`:
| vaccine_ingredients_toxic | Vaccine ingredients are toxic | **A vaccine ingredient or contaminant causes harm.** Aluminum, mercury (thimerosal), formaldehyde, PEG, polysorbate or a contaminant such as SV40 is said to cause neurological damage, allergy, cancer or chronic disease. Objecting to fetal cell lines on moral or religious grounds, with no harm claimed, is not this narrative. | aluminum adjuvants neurotoxic; thimerosal is mercury; aluminum levels off the charts; SV40 in the polio vaccine caused cancer | vaccines |
Why: SV40 and polio-vaccine cancer appear in 44 episodes, 15 podcasts (77368/3) with no home. Fetal-cell mentions are often moral objections ("not comfortable injecting my two boys with aborted fetal tissue", 37535/3) that the current wording ("fetal cells... cause harm") invites coders to label.

CHANGE `hep_b_birth_dose_unneeded`:
| hep_b_birth_dose_unneeded | Hep B birth dose unnecessary or harmful | **Newborns of hepatitis-B-negative mothers do not need, or are harmed by, the birth dose.** Reporting that the CDC or ACIP changed the newborn recommendation, without the claim itself, is the topic `vaccines.hep_b`. | newborns aren't sharing needles or having sex; it's for prostitutes and drug users; your perfect baby doesn't need it; low-risk babies | vaccines |
Why: the real phrasing is about sex and drug risk (37294/2, 6353/4). Since December 2025 many hits are policy news (42259/1, 185624/6).

CHANGE `vaccines_didnt_end_disease`:
| vaccines_didnt_end_disease | Vaccines did not end infectious disease | **Vaccines did not end infectious disease.** Infectious diseases are said to have declined because of sanitation or nutrition instead, or polio is said to have been pesticide (DDT) poisoning or to have been redefined out of existence. | mortality fell before vaccines; "Dissolving Illusions"; DDT caused polio; they changed the definition of polio | vaccines |
Why: DDT/polio appears in 16 episodes, 7 podcasts (Humphries on Rogan, 2113/1: "the tonnage of production of DDT absolutely mirrored the diagnosis for polio"; 1353/6). Dissolving Illusions appears in 24 episodes.

CHANGE `vaccine_injury_hidden`:
| vaccine_injury_hidden | Vaccine injury is hidden or underreported | **Vaccine injury is far more common than acknowledged because it is hidden, underreported or dismissed.** VAERS is said to capture a tiny fraction, injured people to be gaslit or ignored, or reporting to be discouraged. VAERS counts cited as evidence for one specific harm take that harm's narrative and `evidence:official_data_documents`, not this narrative, unless underreporting or hidden mass harm is also claimed. | VAERS 1%; Lazarus report; the vaccine injured are gaslit; nobody admits there are vaccine injuries; nurses told not to file VAERS | vaccines |
Why: real phrasing is about denial and gaslighting (37390/0, 39273/1, 318982/9: nurses "let go who were trying to... put these things into VAERS"). VAERS is often cited for a specific harm (39588/1).

CHANGE `vaccine_makers_no_liability`:
| vaccine_makers_no_liability | Vaccine makers have no liability | **Because makers cannot be sued, vaccines are unsafe or untested, or the schedule expanded for profit.** The liability shield (1986 Act, PREP Act) is the premise; saying the shield exists without one of these conclusions is not this narrative. | can't be sued, so the schedule exploded to 70 shots; why do they need liability protection if they're safe; no incentive for safety; 1986 Act | vaccines |
Why: the commonest conclusion is schedule growth (185815/1, 204866/0) or the rhetorical "why do they need protection" (3732/8). Neither fits "unsafe or untested" as written.

CHANGE `natural_immunity_superior`:
| natural_immunity_superior | Natural immunity is superior | **Immunity from infection is as good as or better than vaccination,** so people who have recovered do not need the vaccine and mandates should have recognized it. | natural immunity works; Israeli study, 27 times; already had COVID, why do I need the shot; they refused to recognize natural immunity | vaccines |
Why: 524 episodes, 69 podcasts; equivalence and recognition claims are the norm (40349/1, 169685/0, 199969/4). Pure superiority ("27 times", 13819/8) is the minority.

CHANGE `covid_vaccine_deaths`:
| covid_vaccine_deaths | COVID vaccines kill / died suddenly | **COVID vaccines kill people.** Sudden deaths of young or healthy people and athletes are attributed to them. Add `narrative:excess_deaths_cover_up` only when concealment or ignoring of excess-death data is claimed. A death reported as sudden, or an athlete's collapse, with no vaccine named or implied is not this narrative. | "Died Suddenly" (the film); the died-suddenly phenomenon; athletes dropping dead on the field; SADS; more people died in the vaccine arm | vaccines |
Why: plain "died suddenly" in 364 episodes, 122 podcasts is mostly ordinary language (about 9 of 12 samples). SADS appears in 204993/1. "More people died in the vaccine group than the placebo group" appears in 11412/2.

CHANGE `covid_vaccine_myocarditis`:
| covid_vaccine_myocarditis | COVID vaccine myocarditis is widespread | **COVID vaccine myocarditis is common, serious or concealed.** It is said to be frequent, often fatal or lasting, or downplayed or hidden by officials. Noting the established rare risk (in young men) without any of these claims is the topic, not this narrative. | myocarditis they tried to hide; the CDC downplayed myocarditis; heart damage from the shot; risk higher than the disease for young men | vaccines |
Why: 604 episodes; many state "rare but real risk" (14136/7, 325354/8), and the current core gives no guidance on them. The concealment form appears in 7865/8 and 8538/4.

CHANGE `spike_protein_persistent`:
| spike_protein_persistent | Vaccine spike protein is toxic and persists | **Vaccine-made spike protein is toxic or persists in the body, driving ongoing illness,** so it must be cleared or detoxed. | the spike proteins are toxic; spike protein in the body for years; spikeopathy; spike protein detox with nattokinase and bromelain | vaccines |
Why: "the spike proteins are toxic" (40508/1) and the detox stack (8519/7, 318982/9, 195362/3) are as common as persistence claims (104 segments, 74 episodes).

CHANGE `measles_harmless`:
| measles_harmless | Measles is harmless or manageable without vaccines | **Measles, or another vaccine-preventable childhood infection, is harmless, beneficial or manageable without vaccination.** It is called a mild illness whose deaths are overstated, or vitamin A, cod liver oil, budesonide or good nutrition are said to suffice. | measles parties; chickenpox parties; not fatal in a well-nourished nation; vitamin A for measles; measles builds lifelong immunity | infectious |
Why: 46 episodes, 24 podcasts for measles. The same argument is made about chickenpox and mumps (38874/2 "Mumps, again, very supportable"; 40058/1; 192484/2).

CHANGE `vaccine_microchips_5g`:
| vaccine_microchips_5g | Vaccines contain microchips or 5G technology | **Vaccines contain microchips, 5G components, graphene, magnets or tracking technology.** Usually invoked in mockery; code the mocking stance as `rebutted`. | microchips in the vaccine; Bill Gates microchipping you; magnets stick to the injection site; graphene oxide; luciferase | vaccines |
Why: about 80 episodes, nearly all ridicule (322024/6, 175855/2, 6906/5), so coders may skip them as jokes. The magnet challenge appears in 12690/13.

CHANGE `covid_bioweapon_plandemic`:
| covid_bioweapon_plandemic | Bioweapon / planned pandemic | **The virus was made as a weapon or released on purpose, or the pandemic was planned.** A virus engineered in gain-of-function research that leaked by accident is `narrative:covid_lab_leak` only, even when called a "bioweapon" loosely; code both when deliberate creation as a weapon or deliberate release is asserted. | plandemic; released intentionally; Event 201 rehearsal; it was planned; Fauci funded a bioweapon (with intent alleged) | covid |
Why: "bioweapon" is used loosely for an engineered virus (205647/2; 88102/4 "the Wuhan Bioweapons Laboratory"). The current core ("deliberately made") fits every gain-of-function virus.

CHANGE `covid_severity_exaggerated`:
| covid_severity_exaggerated | COVID is no worse than flu | **COVID was mild or no worse than flu for most people or for some group, so the response was disproportionate.** The response can be lockdowns, mandates, or vaccinating children and young adults ("kids don't need the shot"). | just a flu; 99.9% survival; kids have a 99.99% survival rate so they don't need the vaccine; young healthy people don't need a booster | covid |
Why: about 70 episodes, 44 podcasts say kids or the young don't need the COVID vaccine (169936/0, 389455/2, 13819/7), usually citing survival rates. No current narrative covers it.

REMOVE `nsaids_worsen_covid`
Why: 21 episodes mention ibuprofen and COVID; only about 10 invoke the claim, all tied to the March 2020 French scare and its debunks (318550/0, 178268/0, 86908/2). It is not recurring. A claim that fever reducers blunt immunity during COVID takes `narrative:fever_suppression_harmful`.

REMOVE `cancer_fungus_parasite`
Why: 7 segments in 4 podcasts. Baking-soda cures go to `narrative:natural_remedy_cures_cancer` (9834/120, 319135/3), acid/alkaline cancer to `narrative:alkaline_ph` (176668/1), and parasites as cancer's cause to `narrative:parasites_cause_disease` (190449/55).

REMOVE `cancer_epidemic_young`
Why: the rise in young-onset cancer is discussed often (341 episodes, 77 podcasts), but the core's "ignored or hidden" clause is essentially never stated (proposition query: 60 segments, almost all off-topic). People present it as an open question (25957/132, 196448/7, 63258/7), which is `topic:cancer.causes_rates`. A vaccine cause is `narrative:turbo_cancer`; a cover-up claim is `narrative:excess_deaths_cover_up` or `unlisted_narrative`.

CHANGE `natural_remedy_cures_cancer`:
| natural_remedy_cures_cancer | A natural remedy cures cancer | **A specific herb, food or alternative protocol cures or treats existing cancer.** "Fights", "reverses", "heals", "kills cancer cells" or "shrinks tumours" in a person count. A remedy said only to have "anti-cancer properties", to lower cancer risk or to prevent cancer is not this narrative. Vitamin megadoses are `narrative:vitamin_megadose_cures` and antiparasitic drugs `narrative:antiparasitics_cure_cancer` instead. | B17 and apricot seeds kill cancer cells; Gerson; Budwig protocol; Rick Simpson oil cured; ditched chemo and healed naturally; baking soda and lemon cures cancer | cancer_alt |
Why: "anti-cancer properties", "cancer-fighting foods" and "starve cancer" appear in about 330 episodes (190828/44, 7576/13, 40268/0) and would all qualify under "fights counts". Cure-level claims (185738/0, 70955/16, 175007/0) are the narrative.

CHANGE `sugar_feeds_cancer`:
| sugar_feeds_cancer | Sugar feeds cancer / keto starves it | **Cancer feeds on sugar, so cutting sugar or a ketogenic diet treats it.** The broader claim that cancer is a metabolic rather than genetic disease is `narrative:cancer_metabolic_disease`; code both when both are made. "Starving cancer" by cutting its blood supply with foods (anti-angiogenesis) is not this narrative. | cancer feeds on sugar; starve cancer of glucose; keto cures cancer; cancer cells can't use ketones | cancer_alt |
Why: William Li's anti-angiogenesis "starve cancer" is common (183909/0, 40268/0, 19275/2) and shares the verb with the glucose claim (192841/7).

CHANGE `cancer_metabolic_disease`:
| cancer_metabolic_disease | Cancer is a metabolic disease | **Cancer is fundamentally a metabolic, not a genetic, disease.** Damaged mitochondria are said to drive it, so metabolic or dietary approaches are the real treatment. Discussing the Warburg effect or cancer metabolism as one feature or drug target, without denying the genetic model, is the topic `cancer.causes_rates`. | Seyfried; cancer is a mitochondrial disease; Warburg said the cause of cancer is; somatic mutation theory is wrong | cancer_alt |
Why: mainstream Warburg talk (Attia, 181570/7) sits beside the narrative proper (174993/8, 190372/152). Regex note: "Seyfried" catches Amanda Seyfried (about 60 Big Picture episodes).

CHANGE `saturated_fat_cholesterol_myth`:
| saturated_fat_cholesterol_myth | Saturated fat and cholesterol do not cause heart disease | **Saturated fat, dietary cholesterol or blood (LDL) cholesterol do not cause heart disease.** The diet-heart or lipid hypothesis is called wrong or fraudulent, high LDL on a low-carb diet is called harmless, or high cholesterol is said to mean longer life. Statin harm or uselessness is `narrative:statins_harmful`. | Ancel Keys fraud; butter is back; sugar industry blamed fat; LDL doesn't matter; lean mass hyper-responders are healthy; cholesterol is not the enemy | food |
Why: LDL-causality denial appears in 170 episodes, 41 podcasts (192594/2, 174986/9) and is often rebutted (181216/4, 181853/3). It has no other home and co-occurs with the diet-heart argument.

REMOVE `sugar_hyperactivity`
Why: 630 matching segments, but nearly all are the idiom "sugar high" (politics, markets, 39450/6, 37864/2) or glucose talk. The proposition appears only in a handful of passing lines (182593/1). It is a plain misconception rather than a circulating contested narrative, and the codebook's own unlisted rule excludes those.

CHANGE `food_dyes_harm_children`:
| food_dyes_harm_children | Synthetic food dyes are harmful | **Synthetic food dyes cause harm,** such as hyperactivity, ADHD or behaviour problems in children, or cancer, and are banned elsewhere for that reason. Reporting a ban or phase-out without the harm claim is the topic `food.additives_dyes`. | Red 40 and ADHD; red dye causes cancer; petroleum-based dyes; banned in Europe | food |
Why: cancer claims are as frequent as ADHD claims (204990/6, 78331/3, 183756/6). Also, since 2025 many hits report the FDA phase-out without a claim.

CHANGE `us_food_banned_elsewhere`:
| us_food_banned_elsewhere | US food is more harmful than food abroad | **American food is more harmful than food abroad because it contains ingredients, additives or pesticides banned or restricted there.** The same product with a different recipe abroad, or feeling fine after eating bread or pasta in Europe, are the usual proofs. | banned in Europe; same cereal, different ingredients; I eat pasta in Italy and feel fine; pesticides banned in the EU | food |
Why: the travel anecdote recurs (26 episodes, 11 podcasts; 37622/2, 6231/2, 177114/5) and states the comparison without naming a ban.

CHANGE `food_engineered_to_harm`:
| food_engineered_to_harm | The food supply is engineered to make people sick | **Food companies or the government deliberately make food that sickens or poisons people,** sometimes to create patients for pharma. Saying processed food is engineered to be craveable or to make people overeat, with no intent to harm alleged, is the topic `food.ultra_processed` (with `frame:big_food` if the industry is blamed). | they're poisoning us through our food; designed to make you sick; the food and drug industry are the same companies; food-pharma pipeline | food |
Why: "engineered to make you overeat" is common mainstream talk (195480/0, 195335/1, 72189/1). It meets the current "to addict" wording but is not the malice narrative (182053/0, 189369/1).

CHANGE `soy_feminizes`:
| soy_feminizes | Soy feminizes men | **Soy or phytoestrogens lower testosterone or feminize men.** "Soy boy" used as an insult with no health claim is not this narrative. | soy lowers testosterone; phytoestrogens wreck men's hormones; soy gives men breasts | food |
Why: "soy boy" is overwhelmingly a political insult (14233/11, 5114/4, 90748/4). The claim proper is in 190701/34 and is rebutted in 181008/1.

CHANGE `microwave_radiation_food`:
| microwave_radiation_food | Microwaves are dangerous | **Microwave ovens are dangerous: they leak harmful radiation, cause cancer, or destroy food's nutrients.** Heating food in plastic so chemicals leach is `narrative:household_toxins_poisoning` or `narrative:microplastics_catastrophe`. | microwave causes cancer; don't stand in front of the microwave; microwaving kills nutrients; threw out our microwave | food |
Why: the oven-radiation fear (314218/1, 52662/12, 128834/3) is commoner than the nutrient claim. The leading real health claim is about plastics (176667/7, 439308/2, 181086/2), which belongs elsewhere.

CHANGE `plants_are_toxic`:
| plants_are_toxic | Plants, grains and vegetables are toxic | **Plants, grains or plant compounds are harmful or unnecessary for people in general.** Vegetables, oxalates, lectins, fiber or grains are said to damage health or the gut. Avoiding a compound because of an individual sensitivity (a low-oxalate diet for oxalate issues) is not this narrative. A claim that grains in general are harmful belongs here, and gluten alone is `narrative:gluten_harms_everyone`. | plant toxins; we don't need gobs of kale; lectins are inflammatory; fiber is unnecessary; plants don't want to be eaten | food |
Why: many oxalate and lectin hits are individual elimination advice (192684/1, 192681/3). The narrative proper is in 185637/7 and 192802/0.

CHANGE `beef_tallow_healthier`:
| beef_tallow_healthier | Animal fats are healthier than plant oils | **Animal fats are healthier than plant oils.** Beef tallow, lard or butter are offered as better than seed or vegetable oils, as food or skincare. Add `narrative:seed_oils_toxic` only when seed oils are also said to cause harm. A product attribute ("fried in beef tallow, no seed oils") alone takes `frame:naturalness_appeal` or `frame:toxin_purity`, not this narrative. | fries used to be cooked in tallow, real fat, really good for you; cook in tallow not canola; tallow for your skin | food |
Why: 705 of 1,425 tallow episodes also mention seed oils, mostly the Masa chip read (6683/4, 7518/2). The stated comparison is in 185656/3.

ADD `salt_fears_overblown` under `food_narratives`:
| salt_fears_overblown | Salt fears are overblown | **Dietary salt is not harmful for most people, and advice to cut it is wrong or harmful.** Salt is said not to raise blood pressure, or low-salt diets are said to be dangerous; sugar is often named as the real culprit. Advice to add electrolytes during exercise or fasting, without disputing salt guidance, is not this narrative. | salt is bad is a myth; the demonization of salt; salt doesn't raise your blood pressure; we need more salt | food |
Why: a recurring guideline dispute parallel to saturated fat. The proposition-level query found 44 episodes in 23 podcasts (192531/1 "Fourth myth... salt is bad for you"; 176917/5 "Demonization of salt over sugar"; 181765/7), and looser "need more salt" talk is far larger. Lower priority than the other changes.

## Codebook and prompt notes

1. **5.2, coined terms: restrict "died suddenly".** The term "carries the proposition" only when used as the coinage: the film or hashtag, "the died-suddenly phenomenon", or alongside vaccine or COVID-shot talk. "My dad died suddenly of a heart attack" does not. Evidence: 364 episodes in 122 podcasts, mostly obituaries, true crime and history (440162/0, 5189/0, 1923/7) against 39370/3 and 204719/8. Also clarify **"jab injured" / "vaccine injured"**. Used as an identity ("my vaccine-injured son", 3597/2; "Do you have a vaccine injured child?", 186337/3), it names the subject and does not by itself invoke a specific narrative. Code the narrative whose proposition the passage adds: autism, hidden injury, deaths. Add **"soy boy"** as an example of a coined-sounding insult that invokes nothing.

2. **5.2, implicature rule (a), more ad cases.** Add these worked examples. "No seed oils" (about 4,400 episodes), "non-GMO", "dye-free": frame only. "When your doctor refuses to prescribe ivermectin... All Family Pharmacy gives you another option" (42192/5): no `ivermectin_covid`, which needs ivermectin said to prevent or treat COVID; code `frame:anti_mainstream_medicine` and `frame:commercialization` plus the product. An emergency kit that "includes ivermectin" (38363/2): no narrative. But "ivermectin and mebendazole... has shown success in triggering cancer cell death" (48633/3): `antiparasitics_cure_cancer`, `advertisement`, `asserted_or_endorsed`. The same goes for the Hyman soil-depletion read ("soils have become depleted... that's why I recommend", 182661/0, 182360/1). Borderline: "no garbage, no seed oils... you feel the difference" (6683/4) stays a frame. "Garbage" disparages the oils, but no harm proposition is stated, unlike "ditch the seed oils, they're poison".

3. **5.2, verbs of benefit.** Keep the interchangeability rule but add: a property or prevention claim ("anti-cancer properties", "cancer-fighting foods", "lowers your risk of cancer", "anti-inflammatory") is not a cure-type narrative. The cure narratives need treatment or reversal of an existing disease. Evidence: about 330 episodes of "anti-cancer"/"cancer-fighting"/"starve cancer" phrasing (190828/44, 7576/13, 174958/4, 40268/0).

4. **5.2, lists of grievances.** Add: a litany such as "You lied about the vaccine... school closures... the mask... early treatments" (38529/2, 39501/3) invokes a narrative only for an item that states or plainly implies its proposition. "Lied about masks" plainly implies that masks didn't work, which is `masks_useless_harmful`. "Lied about early treatments" implies treatments were suppressed, which is `early_treatment_suppressed`. "Lied about school closures" names a subject only, which is `frame:government_distrust` and no narrative. The parallel to co-labeling rule 6 for topics should be made explicit.

5. **5.2, policy news vs proposition.** Since 2025 many hits report HHS, CDC or FDA actions (Hep B birth-dose change, red-dye phase-out, the Tylenol announcement). Add: reporting an agency action that implies a narrative's conclusion is `reported_or_quoted` on the narrative only when the official's harm or benefit claim is relayed ("RFK said red dye causes cancer and the FDA banned it", 204990/6). A bare policy change ("the CDC no longer recommends the newborn dose", 185624/6) is a topic only.

6. **5.2, mockery is a rebuttal: emphasize for this slice.** `vaccine_microchips_5g`, `vaccine_shedding`, `cancer_cures_suppressed` and `sugar_is_toxic` are often invoked only in ridicule or by debunkers (322024/6, 175855/2, 84411/6, 71184/11 "they already have a cure for cancer. They just don't want you to have the cure", which Shermer then rebuts). Add one microchip example to the rebuttal bullet so labelers do not drop these as jokes.

7. **5.2 or the table preamble, premise vs narrative examples.** Add `vaccines_for_profit` alongside the existing premise examples: a revenue figure ("the most profitable medical product in history", 319124/6) is not the narrative without "pushed for profit". Do the same for natural-immunity facts reported by mainstream outlets.

8. **Rubric note, ASR variants worth listing for the labeler:** ivermectin / "ivermectan" / "iver"; mebendazole / "membenzol" / "mbenbendazole" / "Medbendazol"; fenbendazole / "fenben"; glyphosate / "glyphosphate"; Simoncini / "Simontelli"; VAERS / "VAERs"; SADS / "sad sudden arrhythmic death". Regex users should also note that "Warburg" matches "Warburton" and "Seyfried" matches Amanda Seyfried. Neither affects LLM labelers, but both affect keyword-based QA.

9. **Search-tool note (process, not codebook).** The faster NVMe copy (`/mnt/internal/felix/podcast-corpus-text/cq.py`) was used for most searches after the permission rule was added. A combined shell loop was blocked by the classifier, so queries were run one per call.
