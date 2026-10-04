# Reproductive, sex-specific, gender and pediatric health (`womens`, `pregnancy`, `fertility`, `sexual`, `mens`, `manosphere`, `gender`, `pediatrics`): corpus review

All counts are keyword hits from `cq.py count` (segments / episodes / podcasts) over the ~145,600-episode corpus. They are upper bounds: I read samples for every label, and the noise I found is described with each count. Quotes are cited as (ep, seg).

## Summary

- **Every label in the slice is findable, but for this slice the main problem is volume from non-health political talk, not missing subjects.** `abortion` matches 11,826 episodes in 268 podcasts, mostly as an election or culture-war issue named in a list ("immigration, abortion, gay marriage", 89482/1). The gender terms (1,000 to 3,000 episodes each) are mostly on Matt Walsh, Charlie Kirk, Ben Shapiro, Megyn Kelly and Morning Wire. "Men in women's sports" matches 691 episodes. The codebook has a "bare crime word" exclusion but no matching rule for abortion or trans issues used only as political tokens. This is my top codebook recommendation.
- **ADD `gender.trans_athletes`.** Trans athletes and sex-based physical advantage come up in 691 episodes; in 333 of them (≥10 podcasts) the same episode also mentions physiology (male puberty, testosterone suppression, muscle or bone density, injury). No label fits, so coders currently scatter this among `adult_transition`, `gender_identity_science`, `peds.doping_sport` and `other`.
- **The "HRT" acronym is ambiguous enough to need a boundary in `womens.hormone_therapy`.** HRT co-occurs with testosterone or TRT in 314 of the 609 episodes that use it (male TRT, e.g. Mind Pump 195494/1). It also means trans HRT, and "Hostage Rescue Team" (The Team House 155248/5).
- **Several examples are essentially absent from the corpus:** "maternity care deserts" (2 episodes), "obstetric violence" (1), "heavy metals in tampons" (2), "heightmaxxing" (4), "Cass Review" (12, though "WPATH" or "Cass" together reach 123), "bigorexia/muscle dysmorphia" (14). I propose replacing them with the phrasing that actually occurs.
- **`pregnancy.maternal_mortality_access` should absorb infant mortality.** "Infant mortality" appears in 548 episodes (104 podcasts) and has no home; it is usually paired with maternal mortality (5643/0, 7081/6). Separately, the "maternity ward" hits are almost all a SimpliSafe ad slogan (275 Last Podcast on the Left episodes).
- **Three manosphere labels need tightening.**
  - "Manosphere / red pill / black pill" talk is overwhelmingly about politics and culture, so `masculinity_ideology` must require a claim about men's bodies or health.
  - "Monk mode" (62 episodes) is not semen retention, so it should come out of the `semen_retention_nofap` examples.
  - `male_body_image` is rare (70 episodes). Body dysmorphia in general (633 episodes) has no home and should be routed to `mental`.
- **`pediatrics.pediatric_care` collides with vaccines.** 1,081 of the 1,908 episodes that mention a pediatrician also mention vaccines or shots, and most of those passages are about vaccine advice ("every pediatrician that we've had has recommended… the COVID vaccine", 5851/2). This needs an explicit boundary to `vaccines.uptake_hesitancy`.
- **Recurring ad formats in this slice need ad-test guidance:**
  - menopause telehealth: MIDI Health on NPR, 340 Up First and 102 Wait Wait episodes;
  - Hims ED and weight-loss reads;
  - Opill;
  - a Planned Parenthood "Title X" advocacy ad: about 626 The Daily episodes;
  - Garnu "organic tampons… doesn't fund Planned Parenthood": 63 Culture Apothecary episodes;
  - a Strict Scrutiny cross-promo that names "bans on conversion therapy": most of Pod Save America's 363 `lgbtq_health` hits.
- **Smaller fixes:**
  - add amenorrhea/RED-S to `menstrual_cycle` (98 episodes, 33 podcasts);
  - add "PMOS" (the new name for PCOS) to `pcos`;
  - add pregnancy loss and a boundary for ectopic pregnancy or miscarriage care under abortion bans to `pregnancy_health`;
  - add andropause to `mens.testosterone` (148 episodes);
  - make newborn circumcision belong to `pediatrics.infant_care` only;
  - add the origins of sexual orientation to `gender.lgbtq_health` (about 437 episodes, 119 podcasts, broad query).

## Label-by-label findings

### `womens`

**`womens.menstrual_cycle`**
- Query: `\b(menstrual|menstruat\w*|PMS|PMDD|cycle syncing|luteal phase|follicular phase|irregular periods?|heavy periods?|period cramps|period pain)\b` → 4,009 / 2,534 / 188.
- "My period" talk is common in comedy and chat shows (The Toast, KILL TONY) and is usually passing.
- Example check: "cycle syncing" 26 episodes / 14 podcasts, "PMDD" 82 / 36. Both fine but niche.
- Missing: loss of periods from under-eating or over-training. `amenorrh\w*|hypothalamic amenorrhea|RED-S|relative energy deficiency|female athlete triad|lost my period` → 115 / 98 / 33 (Mind Pump, Gabrielle Lyon, Huberman, Attia). Example: "Since I quit birth control in 2016… I had amenorrhea" (196057/7).
- Verdict: **examples change** (add amenorrhea / RED-S).

**`womens.female_hormones`**
- Query: estrogen dominance, low progesterone, DUTCH test, testosterone in women → 6,125 / 2,224 / 114 (broad, includes "progesterone").
- Example check: "estrogen dominance" 415 / 35 and "DUTCH test" 210 / 28. Both real and concentrated in functional-medicine shows (Thyroid Fixer, Hyman, Jockers): "For most women, they get an imbalance. We call that estrogen dominance" (192599/0).
- Confusion: male–female testosterone comparisons in trans and political debates ("if women are lower in testosterone… wouldn't that… play into the idea that there are natural differences", Charlie Kirk 38132/2). These are not `female_hormones`; they belong to `gender.*` (see the proposed `trans_athletes`) or to the manosphere.
- Verdict: **fine**. The boundary sentence on `hormone_therapy` covers the rest.

**`womens.menopause`**
- Query: `peri ?menopaus\w*|menopaus\w*|hot flash\w*|vaginal atrophy|vaginal dryness|genitourinary syndrome` → 9,971 / 4,075 / 204. "GSM / genitourinary syndrome" 73 / 31.
- A large share is MIDI Health ad copy on NPR: "MIDI Health provides specialized care for perimenopause and menopause, covered by insurance" (5742/4; Up First 340 episodes, Wait Wait 102).
- Verdict: **fine**. See the codebook note on telehealth ads.

**`womens.hormone_therapy`**
- Query: `hormone replacement|bioidentical|estradiol|black box warning|women's health initiative|HRT|MHT` → 5,276 / 2,081 / 137.
- Real confusions:
  - "HRT" for men = TRT: "My brother and I were talking about HRT. We were not talking about… bodybuilder doses" (195494/1). HRT co-occurs with testosterone or TRT in 314 of 609 HRT episodes.
  - "HRT" for trans people.
  - Hostage Rescue Team: "HRT is deployed. We go to the rest stop" (155248/5).
  - "Bioidentical" applied to drugs: "semaglutide is almost bioidentical to GLP-1" (182053/3).
- Verdict: **needs definition change** (acronym boundary).

**`womens.pcos`**
- Query: `\b(pcos|pmos|polycystic)\b` → 1,644 / 843 / 89.
- The new name appears already: "your PMS PMOS journey" (191028/120, episode titled "The psychology of PMOS/PCOS").
- Verdict: **examples change** (add PMOS).

**`womens.gynecological_conditions`**
- Query: endometriosis, fibroids, ovarian cysts, yeast infection, Pap smear, BV, hysterectomy, gynecolog*, OB-GYN → 3,997 / 2,719 / 210.
- Noise:
  - "OB-GYN" as a credential in intros (174886/0) is not a topic;
  - "hysterectomies" inside trans-care rhetoric (33562/53) is `gender.*`;
  - historical or true-crime careers (324918/3) are not health.
- Verdict: **fine**. Codebook note: a credential alone is evidence (`credential_appeal`), not a topic.

**`womens.period_products`**
- Query: `tampons?|menstrual cups?|period underwear|knix|thinx|toxic shock` → 1,821 / 1,522 / 162.
- Most hits are not health: jokes, plus "Tampon Tim" or "tampons in boys' bathrooms" political talk ("Tim Walz's tampon thing", 5171/1).
- Health-specific (`(tampons?|pads|period products?).{0,80}(toxic|heavy metals?|lead|arsenic|chemicals?|dioxins?|organic|pfas)|toxic shock|menstrual cups?|period underwear`) → 223 / 209 / 64.
- 63 of those episodes are one Garnu ad on Culture Apothecary: "Garnu offers 100% organic. Tampons… most tampon brands fund Planned Parenthood" (185922/1).
- Real harm talk: "has to be organic tampons because ladies, you do not want to put bleach" (181132/5). Leak-proof underwear ads: "Maybe it's day one of your period" (329966/5).
- The example "heavy metals in tampons" occurs in 2 episodes.
- Verdict: **examples change**. The label is small (about 150 genuine episodes) but worth keeping because `narrative:tampon_toxins` points to it.

**`womens.pelvic_floor`**
- Query: `pelvic floor|kegels?|organ prolapse|urinary incontinence|incontinence|bladder leak\w*` → 1,218 / 804 / 123. "Kegels" 259 / 74.
- Many hits are intimate-health ads: "leaks when I sneeze… frequent UTIs, incontinence" (422233/0) and postpartum "leaky leaks" (94347/2).
- Verdict: **fine**. Add "bladder leaks" as an example.

### `pregnancy`

**`pregnancy.pregnancy_health`**
- Query: `prenatal|gestational diabetes|pre ?eclampsia|miscarr\w*|morning sickness|stillbirths?|ectopic|hyperemesis|high-risk pregnancy` → 4,538 / 3,457 / 261.
- Noise: "miscarriage(s) of justice" accounts for 396 episodes / 92 podcasts. True miscarriage or pregnancy loss is 2,413 / 240.
- Boundary case: miscarriage and ectopic pregnancy care under abortion bans. "She had a miscarriage, needed an abortion to protect herself, couldn't get one" (5643/0); "a doctor to provide the health care needed in situations like ectopic pregnancies" (84267/4). Coders will split between `pregnancy_health` and `fertility.abortion`.
- Ads: prenatal vitamins (89704/1); a health-sharing plan covering "prenatal care, delivery, and postpartum" (185658/7).
- Verdict: **definition change** (boundary; add pregnancy loss and ectopic pregnancy).

**`pregnancy.exposures_in_pregnancy`**
- Query: substance near "while pregnant / during pregnancy / pregnant women" → 258 / 212 / 60 (narrow co-mention query; real volume is higher).
- Fits well: Tylenol and autism (198364/0, 185687/3); "SSRIs are safe in pregnancy" (81060/2); mRNA vaccines in pregnancy (39243/3); caffeine (185676/4).
- Verdict: **fine**.

**`pregnancy.birth_delivery`**
- Query: C-section, cesarean, home birth, freebirth, midwife, doula, epidural, birth trauma, birth plan → 3,361 / 2,525 / 242.
- Noise: history-sleep shows (171 episodes) and "purpose doula" as metaphor (72237/0). "Freebirth" 52 / 30 is real.
- Prenatal chiropractic: "the midwifery community knows about us. The doulas community… lactation consultants" (186718/3).
- Verdict: **fine**.

**`pregnancy.postpartum`**
- Query: `post ?partum|postnatal|placenta encapsulation|fourth trimester|diastasis` → 3,116 / 2,099 / 219.
- Postpartum depression / psychosis / anxiety → 1,020 / 180.
- Placenta encapsulation or eating the placenta is rare (29 / 19).
- Recurring ads: postpartum hair loss (89641/4), postpartum leaks (94347/2), GLP-1 after pregnancy (30384/5).
- Postpartum mental illness in a murder trial (159272/20) needs a co-label.
- Verdict: **examples change**, plus co-label guidance.

**`pregnancy.infant_feeding`**
- Query: breastfeeding, breast milk, infant formula, donor milk, tongue tie, lactation, breast pump → 4,256 / 3,306 / 217.
- Example check: "tongue tie" 210 / 92 and "seed oils… formula" 29 / 14. Both real.
- Comedy dominates the raw count (KILL TONY 195177/3).
- Verdict: **fine**.

**`pregnancy.maternal_mortality_access`**
- Raw query 760 / 719 / 127. 275 of those episodes are SimpliSafe ad copy ("at the maternity ward where the criminals are born", 25850/7).
- Strict `maternal (mortality|deaths?|health)|maternity care deserts?|obstetric violence|died (in|during) childbirth` → 410 / 383 / 107.
- Example check: "maternity care deserts" 2 episodes, "obstetric violence" 1.
- "Infant mortality / infant deaths / child mortality" → 599 / 548 / 104 with no home. It is often paired with maternal mortality: "some of the worst maternal mortality and morbidity rates and infant mortality rates" (7081/6); "highest infant mortality rate… highest maternal mortality rate" (20618/4).
- Verdict: **definition and examples change** (absorb infant mortality).

### `fertility`

**`fertility.infertility_treatment`**
- Query: infertil*, IVF, egg freezing, IUI, ovarian reserve, AMH, surrogacy → 5,028 / 3,412 / 216.
- Real: "I was on my sixth round of IVF" (84810/1); "freeze your eggs" (622123/889).
- Noise: a Cancer Research UK ad ("lifelong side effects like infertility", 41195/3). That is infertility as an outcome, which gets co-labeled.
- Verdict: **fine**.

**`fertility.male_fertility`**
- Query: sperm count, sperm quality, motility, male infertility, low sperm, semen analysis → 847 / 556 / 101 (Rogan, Huberman, Hyman, DOAC, Modern Wisdom).
- Verdict: **fine**.

**`fertility.conception_general`**
- Query: trying to conceive, ovulation, fertile window, biological clock → 2,548 / 1,720 / 175.
- "Ovulating" also appears in menopause and cycle talk (438894/0), which should not take this label.
- Verdict: **fine**.

**`fertility.contraception`**
- Query: birth control, on/off the pill, IUD, contracept*, vasectomy, NFP, fertility awareness, Nexplanon, morning-after pill, tubes tied → 7,337 / 5,392 / 251. "Condoms" adds 3,418 episodes, mostly jokes.
- "Plan B" and "the pill" are too ambiguous to search on.
- About 626 of The Daily's episodes are one Planned Parenthood ad: "the Trump administration is going after Title X family planning, a program that funds birth control, cancer screenings" (1140151/1).
- Other real material: the Opill ad (24026/0), the male pill (318454/2), birth control and thyroid (190869/23).
- Verdict: **examples change** (add Opill, the male pill).

**`fertility.abortion`**
- Query: `abortions?|mifepristone|misoprostol|dobbs` → 19,065 / 11,826 / 268. Charlie Kirk 1,460 episodes, Shapiro 1,067, Walsh 823.
- In two random samples (n = 18), roughly 13 were purely electoral, moral or partisan ("abortion landmines for GOP presidential candidates", 169244/0; "the new right obsesses over… abortion or the Jews or physical fitness", 175685/6).
- Only a few concerned procedures, pills, law or access. Examples: mifepristone history (162988/0); "giving young women abortion procedures via the pill" (37912/1).
- Verdict: **fine as a label, needs a scope rule** (see Codebook notes).

**`fertility.birth_rates`**
- Query: birth rates, fertility rates, pronatalism, population collapse, demographic decline, replacement rate → 2,055 / 1,567 / 140 (Kirk 230, Modern Wisdom 117).
- "Pronatalism" itself is rare (19 / 11).
- Health-framed: "fertility is a huge crisis… declining birth rates" (182156/4). Many are purely racial or political (390268/4).
- Verdict: **fine**. Swap "pronatalism" for "declining birth rate" phrasing (cosmetic, not proposed below).

### `sexual`

**`sexual.stis_hiv`**
- Query `HIV|PrEP|herpes|…` → 17,455 episodes, but "prep" (meal or sports prep) dominates.
- Without bare "PrEP": 7,365 / 5,637 / 270, mostly comedy ("I'm gonna fucking fire it up… HIV positive", 196886/5).
- ASR: "HIV" for HEV light ("we call it HIV high energy visible light", 190160/488).
- Verdict: **fine**. ASR note only.

**`sexual.sexual_function`**
- Query: erectile, Viagra, Cialis, libido, sex drive, orgasm, premature ejaculation, impotence, vaginismus, painful sex → 12,162 / 8,167 / 254.
- Real: "I developed vaginismus, a sexual pain condition" (319953/1).
- Hims ED reads: "through Hims you can get access to personalized ED treatments" (12282/1).
- Porn and sexual function or the brain: porn within 60 characters of erectile, dopamine, libido or addiction → 1,466 / 1,189 / 147. ED from porn has no listed example; porn addiction goes to `mental.behavioral_addictions`.
- Verdict: **examples change**.

### `mens`

**`mens.testosterone`**
- Query: `testosterone|low t|TRT|enclomiphene|clomid` → 15,705 / 7,893 / 221.
- Noise:
  - "Low T" is fantasy-football slang ("I'm going to go super low T and go with Mike's dynasty team", 163955/2; Fantasy Footballers 345 episodes).
  - Testosterone as a political or culture-war trope: "young women want high testosterone men" (episode "The High-T Right vs The Soy Boy Left", 36802/1); "they want weak men… Our testosterone rates are going down" (38523/2). The second invokes `narrative:testosterone_collapse`, but the subject is masculinity ideology.
- "Andropause / male menopause" → 190 / 148 / 43 (Jockers, Modern Wisdom, Hyman, Lyon), not in the examples.
- Example check: "enclomiphene" 15 / 8, rare but real.
- Verdict: **examples and boundary change**.

**`mens.prostate`**
- Query: `prostate|BPH` → 2,507 / 1,820 / 186. Most hits are prostate cancer (goes to `cancer`) or jokes.
- Non-cancer use: "using something like Cialis on a daily basis to keep a healthy prostate" (190777/74); finasteride as "a prostate medicine" (74120/6).
- Verdict: **fine but small**.

**`mens.genital_health`**
- Query: testic*, varicocele, circumcis*, Peyronie's, foreskin, penile → 5,057 / 4,007 / 211.
- Circumcision: 1,164 / 117 overall, but The Bible in a Year (209) and The Bible Recap (96) are scripture. Infant context → 370 / 326 / 68.
- "Circumcision" is listed both here and in `pediatrics.infant_care`.
- Example check: "Peyronie's" 21 / 13 and "varicocele" 15 / 8, both rare.
- Verdict: **boundary change** (newborn circumcision → `infant_care`).

### `manosphere`

**`manosphere.semen_retention_nofap`**
- Strict query (semen retention, NoFap, no nut November, "retaining your seed") → 157 / 128 / 38.
- "Monk mode" (75 / 62 / 19) is a productivity or abstinence-from-distraction idea: "I'd first learned about monk mode… 2018" (175815/5); "going monk mode at age 13. Focusing on reading… the gym" (175877/4). It is not semen retention.
- Verdict: **examples change** (drop monk mode).

**`manosphere.looksmaxxing`**
- Query: looksmax*, mewing, bone smashing, heightmax*, leg lengthening, canthal tilt → 337 / 247 / 73.
- Mostly commentary on a 2026 looksmaxxing influencer (75938/2; "some people are actually breaking jaws", 322322/8).
- Example check: "heightmaxxing" 4 episodes; "bone smashing" 31 / 16.
- Verdict: **examples change** (minor). Rare but distinct.

**`manosphere.masculinity_ideology`**
- Query: alpha male, red pill, black pill, soy boy, manosphere, feminiz*, beta male → 5,144 / 4,070 / 208. Almost all of it is political or cultural:
  - "the manosphere. That's like red-pilled men who blame women" (3998/3);
  - "no black pill" about vote counts (39408/6);
  - "feminization of marriage" (185707/5).
- Health-linked version (soy boy / feminiz* / emasculat* within 100 characters of testosterone, estrogen, soy, plastics, hormones or sperm) → 175 / 161 / 56.
- Verdict: **definition change** (require a claim about men's bodies or health).

**`manosphere.male_body_image`**
- Query: male body image, men's body image, muscle dysmorphia, bigorexia → 80 / 70 / 34 ("bigorexia / muscle dysmorphia" alone 14 episodes). Example: "male body dysmorphia is on track to overtake female body dysmorphia" (175523/4).
- "Body dysmorphia" in general → 737 / 633 / 126. Much of it is not male: an eating disorder (78264/4), a film character (23654/1), trans-debate rhetoric (8703/6).
- Verdict: **rare; definition change** (route general BDD to `mental`).

### `gender`

**`gender.youth_gender_medicine`**
- Query: puberty blockers, Cass Review, gender clinics, social transition, trans kids, gender-affirming care, Skrmetti → 2,695 / 1,971 / 94. Found reliably, in both stances:
  - "puberty blockers, which are completely reversible" (sarcastic, 207269/0);
  - "We know they're not safe… WPATH" (4156/4);
  - "end all gender affirming care… for people under nineteen" (328941/8).
- Example check: "Cass Review" 14 / 12; "Cass review|Hilary Cass|WPATH" 160 / 123 / 18.
- Verdict: **examples change**.

**`gender.adult_transition`**
- Query: top surgery, bottom surgery, sex change, gender reassignment, vaginoplasty, phalloplasty, cross-sex hormones → 1,314 / 1,083 / 95.
- "Sex change" is the common lay term (Rogan 71370/5) and is not listed.
- Most hits are about procedures in general or minors, with age often unstated ("explaining how a phalloplasty is done", 207200/2).
- Verdict: **examples change**, plus a boundary for when age is unstated.

**`gender.detransition`**
- `\bdetrans\w*` → 431 / 307 / 25.
- Verdict: **fine** (concentrated in 5 shows).

**`gender.gender_identity_science`**
- Query: gender dysphoria, ROGD, rapid-onset gender, social contagion, intersex, gender identity, gender ideology → 4,433 / 3,103 / 147. "ROGD / rapid-onset gender" 69 / 13.
- "Gender ideology" is mostly a political label (206372/5), which is narrative (`trans_identity_disorder`) or frame (`political_partisan`) territory.
- "Intersex" in a film review (*Conclave*, 388474/3) is fiction, not health.
- A real policy case with no clear home: the military's trans service ban ("disqualify people from service due to a mental health condition like gender dysphoria", 328804/458).
- Verdict: **fine**. Codebook note on the political use.

**`gender.lgbtq_health`**
- Query: conversion therapy, trans suicide, LGBTQ youth or mental health, suicide near trans or LGBT → 1,234 / 1,062 / 104.
- 363 of the episodes are Pod Save America, mostly a repeated cross-promo: "whether bans on conversion therapy for LGBTQ kids count as censorship" (4153/9, 6090/8).
- Real: "the trans suicide rate is somewhere around forty percent" (207007/2).
- Gap: the origins of sexual orientation. "gay gene|born gay|born this way|sexual orientation… genetic, biological, hormonal" → 482 / 437 / 119 (broad). Examples: "studies… looking at sexual orientation and… hormones and brain development… in utero" (27183/3); "homosexual orientation is largely, if not entirely, genetic" (390284/3); "the left claims that homosexuality is biological" (207415/0).
- Verdict: **definition change** (add orientation origins).

**Gap: transgender athletes and sex differences in sport**
- Query: trans athletes, men or biological males in women's sports, Lia Thomas, Imane Khelif, Fallon Fox, sex testing, testosterone suppression → 691 episodes. With a physiology term in the same episode (male puberty, bone density, muscle mass, testosterone, lung capacity, advantage, injury) → 333 episodes (Megyn Kelly 74, Rogan 50, Walsh 34, Kirk 23, Behind the Bastards 18, Shapiro 15, REAL AF 13, Morning Wire 13, Modern Wisdom 10, Pod Save 9).
- Examples: "the Olympic Committee… you don't even need to suppress your testosterone" (40118/2); "notwithstanding their male body parts, their testosterone" (8178/7); "I don't know how much gets taken away by that sex change, but not enough" (71370/5).
- Verdict: **ADD** (below), with a scope rule so the bare slogan is not health content.

### `pediatrics`

**`pediatrics.infant_care`**
- Query: newborn, SIDS, sudden infant, safe sleep, co-sleeping, colic, tummy time, vitamin K shot, swaddle, NICU, bassinet → 5,461 / 4,691 / 291 (raw "newborn" is broad).
- Real: SIDS (25117/0); NICU stays (207478/4); unexpected infant death in a co-sleeping debate (318651/2).
- Example check: "vitamin K shot" near newborn or baby → 15 / 11 / 8. Rare, but it is a contested subject (Culture Apothecary, Candace, Dr. Hyman).
- Verdict: **fine**. Take over newborn circumcision.

**`pediatrics.child_development`**
- Raw query 4,022 / 3,553 / 259, but "milestones" is mostly non-health. Strict phrases → 952 segments.
- Noise: self-help shows using "early childhood development" (187900/0) and parenting-style typologies (189556/25).
- Real: daycare and attachment (19563/4).
- Verdict: **fine**.

**`pediatrics.pediatric_care`**
- "Pediatrician(s)" → 2,365 / 1,908 / 197. 1,081 of those episodes also mention vaccines or shots; within 120 characters → 252 / 194 / 55.
- Real overlaps:
  - "every pediatrician that we've had has recommended that we get them the COVID vaccine. We didn't" (5851/2);
  - "the pediatrician says you got to get this for your kid to attend school" (36591/6).
- "Children's hospital" is mostly an institution name (10088/144, 313969/2).
- Pediatric chiropractic: "Instead of waiting for the wheels to fall off and going to the pediatrician" (186579/2).
- Verdict: **definition change** (vaccine boundary).

**`pediatrics.baby_food_child_nutrition`**
- Query: baby food, starting solids, picky eater, baby-led weaning → 904 / 847 / 140, overwhelmingly jokes and travel or pet ads ("picky eaters will clean their plates", 128211/14).
- Real health hits are mostly ads for kids' gummy vitamins "for the picky eater in your life… formulated with the help of pediatricians" (31062/4). Those take `supplements` plus this label only when feeding is the point.
- Verdict: **rare in substance; keep**.

**`pediatrics.puberty_adolescence`**
- Raw `puberty` 5,602 / 4,536 / 244 is dominated by puberty blockers.
- Strict (early or precocious puberty, age at puberty or menarche, first period, growth spurt, going through puberty) → 1,406 / 1,276 / 176, with sports "growth spurt" chatter.
- Real: "having had precocious puberty" (27107/2); Kallmann syndrome, transcribed as "Calman syndrome" (77543/1).
- Verdict: **fine**.

## Proposed edits

CHANGE `topic:womens.hormone_therapy`:
| hormone_therapy | Menopausal hormone therapy | Prescribed hormones for menopause and testosterone for women, including bioidentical hormones and vaginal estrogen. "HRT" said of men means testosterone replacement (`mens.testosterone`); said of transgender people, `gender.adult_transition`; "bioidentical" applied to a non-hormone drug is not this label. | HRT; MHT; estrogen patch; vaginal estrogen; progesterone; bioidentical hormones; testosterone pellets for women; WHI study; black-box warning |
Why: HRT co-occurs with testosterone or TRT in 314 of 609 HRT episodes (male TRT, e.g. 195494/1). It also means trans HRT, and Hostage Rescue Team (155248/5). "Bioidentical" was also applied to semaglutide (182053/3).

CHANGE `topic:womens.menstrual_cycle`:
| menstrual_cycle | Menstrual cycle & periods | The cycle and its problems, including lost or absent periods from under-eating, over-training or stopping the pill. Age at first period and early puberty go to `pediatrics.puberty_adolescence`. | menstrual cycle; PMS; PMDD; irregular periods; heavy bleeding; period pain; amenorrhea; lost my period; RED-S; cycle syncing |
Why: amenorrhea / RED-S / female athlete triad / "lost my period" → 98 episodes in 33 podcasts (Mind Pump, Lyon, Huberman, Attia), with no listed example. Example: "Since I quit birth control in 2016… I had amenorrhea" (196057/7). "Cycle syncing" is only 26 episodes, so it moves to the end of the list.

CHANGE `topic:womens.pcos`:
| pcos | PCOS | Polycystic ovary syndrome, under either name. | PCOS; polycystic ovaries; PMOS; insulin-resistant PCOS |
Why: the renamed condition already appears in the corpus: "your PMS PMOS journey" (191028/120).

CHANGE `topic:womens.period_products`:
| period_products | Period products & their safety | Tampons, pads, cups and period underwear and claims about their contents or safety. Tampons named in jokes or political talk ("tampons in bathrooms") are not health content. | tampons; organic tampons; bleach or chemicals in tampons; period underwear; leak-proof underwear; menstrual cup; toxic shock |
Why: 1,522 raw episodes, of which only about 209 (64 podcasts) are health-specific. The rest are jokes or "Tampon Tim" (5171/1). "Heavy metals in tampons" occurs in 2 episodes. The real phrasing is "has to be organic tampons… you do not want to put bleach" (181132/5) and "100% organic tampons" ads (185922/1).

CHANGE `topic:womens.pelvic_floor`:
| pelvic_floor | Pelvic floor | Pelvic floor function and therapy in any sex, including urinary leaking and incontinence. | pelvic floor; Kegels; pelvic floor therapy; prolapse; incontinence; bladder leaks; leaking when I sneeze |
Why: 804 episodes in 123 podcasts. Many are intimate-health and postpartum reads phrased as leaks ("leaks when I sneeze… incontinence", 422233/0; "leaky leaks", 94347/2), and "leak" is not in the examples.

CHANGE `topic:pregnancy.pregnancy_health`:
| pregnancy_health | Pregnancy health & complications | Prenatal care and complications of pregnancy, including pregnancy loss and ectopic pregnancy. Treatment of miscarriage or ectopic pregnancy under abortion laws also takes `fertility.abortion`. "Miscarriage of justice" is not health content. | prenatal care; prenatal vitamins; gestational diabetes; preeclampsia; miscarriage; pregnancy loss; stillbirth; ectopic pregnancy; morning sickness; hyperemesis |
Why: miscarriage or pregnancy loss in 2,413 episodes (240 podcasts), plus 396 episodes of "miscarriage(s) of justice" noise. Political shows discuss miscarriage and ectopic care under bans ("She had a miscarriage, needed an abortion… couldn't get one", 5643/0; 84267/4), and coders will split between the two homes without a rule.

CHANGE `topic:pregnancy.postpartum`:
| postpartum | Postpartum | The postpartum period and recovery. Postpartum depression or psychosis also takes the `mental` subtopic; postpartum hair loss also takes `skin_beauty.hair_loss_hair`. | postpartum depression; postpartum psychosis; baby blues; postpartum recovery; postpartum hair loss; fourth trimester; diastasis recti; placenta encapsulation |
Why: postpartum depression / psychosis / anxiety appears in about 1,020 episodes (180 podcasts), including a murder trial on postpartum mental state (159272/20). Postpartum hair-loss reads recur (89641/4). Placenta encapsulation is rare (29 episodes) and moves to the end.

CHANGE `topic:pregnancy.maternal_mortality_access`:
| maternal_mortality_access | Maternal & infant mortality and maternity care access | Maternal and infant deaths and their rates, and access to maternity care. Sudden infant death in an individual case goes to `pediatrics.infant_care`; "maternity ward" in ad copy is not health content. | maternal mortality; infant mortality rate; dying in childbirth; maternal health outcomes; hospitals closing labor and delivery units |
Why: true maternal-mortality talk is 383 episodes (107 podcasts). "Infant mortality / infant deaths / child mortality" adds 548 episodes (104 podcasts) with no home and is often paired with it (7081/6, 20618/4). "Maternity care deserts" (2 episodes) and "obstetric violence" (1) are essentially absent. The 275 Last Podcast on the Left hits are a SimpliSafe slogan (25850/7). The unit-closure example comes from the access subject in the definition rather than from a counted search.

CHANGE `topic:fertility.contraception`:
| contraception | Contraception | Birth control of any kind, including hormonal contraceptives taken for acne or PCOS, male contraceptives, and birth-control access programmes. | the pill; Opill; IUD; implant; condoms; vasectomy; male birth control pill; natural family planning; fertility awareness; Title X family planning; the pill for acne |
Why: 5,392 episodes (251 podcasts). Recurring real items are not listed: the Opill read (24026/0), the male pill (318454/2), and the Title X / Planned Parenthood read in about 626 episodes of The Daily (1140151/1).

CHANGE `topic:fertility.abortion`:
| abortion | Abortion | Abortion procedures, pills, safety, access and the law, and arguments about abortion as a health or medical matter. Abortion named only as an electoral issue or one item in a list of political issues is not health content. Miscarriage or ectopic care under abortion laws also takes `pregnancy.pregnancy_health`. | abortion; mifepristone; abortion pill; late-term abortion; abortion bans; Dobbs; Roe; abortion access |
Why: 11,826 episodes in 268 podcasts (Kirk 1,460, Shapiro 1,067, Walsh 823). In random samples about 13 of 18 were purely electoral or partisan mentions ("abortion landmines for GOP presidential candidates", 169244/0; "abortion or the Jews or physical fitness", 175685/6).

CHANGE `topic:sexual.sexual_function`:
| sexual_function | Sexual function & libido | Desire, arousal and performance in any sex, including claimed effects of pornography on sexual function. Porn addiction as a compulsion goes to `mental.behavioral_addictions`. | erectile dysfunction; ED meds; Viagra; Cialis; libido; low sex drive; orgasm; premature ejaculation; vaginismus; sexual pain; porn-induced ED |
Why: 8,167 episodes (254 podcasts). Porn near ED, libido, dopamine or addiction → 1,189 episodes (147 podcasts) with no example. Hims "ED treatments" reads recur (12282/1). Vaginismus occurs (319953/1).

CHANGE `topic:mens.testosterone`:
| testosterone | Testosterone & TRT | Testosterone levels, decline, boosting and replacement therapy in men, including "HRT" for men and andropause. Testosterone used as a political or masculinity trope ("high-T men", "soy boys") goes to `manosphere.masculinity_ideology`; "low T" as sports slang is not health content. | low T; TRT; HRT for men; testosterone boosters; declining testosterone; andropause; male menopause; estrogen in men; enclomiphene |
Why: 7,893 episodes (221 podcasts). "Andropause / male menopause" → 148 episodes (43 podcasts), unlisted. Fantasy-football "low T" slang (163955/2). Political use ("The High-T Right vs The Soy Boy Left", 36802/1).

CHANGE `topic:mens.genital_health`:
| genital_health | Testicular & penile health | Testicular and penile health in boys and men. Newborn circumcision goes to `pediatrics.infant_care`; circumcision as scripture or religious ritual with no health point is not health content. | testicles; testicular pain; varicocele; circumcision (adult or as a health question); foreskin; Peyronie's |
Why: "circumcision" is listed both here and in `infant_care`. Of 1,164 circumcision episodes, 305 are Bible podcasts and 326 are infant or son contexts.

CHANGE `topic:manosphere.semen_retention_nofap`:
| semen_retention_nofap | Semen retention & NoFap | Abstaining from ejaculation or masturbation for claimed health, energy or hormonal benefits. "Monk mode" as general focus or abstinence from distractions is not this label. | semen retention; NoFap; no nut November; retaining your seed |
Why: strict query 128 episodes (38 podcasts). "Monk mode" (62 episodes, 19 podcasts) is used for productivity regimes (175815/5, 175877/4), not semen retention.

CHANGE `topic:manosphere.looksmaxxing`:
| looksmaxxing | Looksmaxxing & appearance hacks | Practices to change facial or bodily appearance promoted in online male subcultures, and their "-maxxing" vocabulary. | looksmaxxing; mewing; bone smashing; jawline; mogging; leg lengthening surgery |
Why: 247 episodes (73 podcasts), mostly about one influencer (75938/2, 322322/8). "Heightmaxxing" occurs in 4 episodes.

CHANGE `topic:manosphere.masculinity_ideology`:
| masculinity_ideology | Masculinity ideology & health | Red-pill / alpha framing of male health: claims that men's bodies, hormones or fertility are being weakened or feminized, "soy boy" style rhetoric about men's bodies, and testosterone used as a marker of manhood or politics. The manosphere or red pill discussed only as a political or cultural movement is not health content. | alpha male biology; soy boys; "men are being feminized"; high-T men; low-T men; turning men into women |
Why: 4,070 raw episodes, almost all political or cultural ("red-pilled men who blame women", 3998/3; "no black pill" about vote counts, 39408/6). Only about 161 episodes (56 podcasts) tie the rhetoric to hormones, soy, plastics or sperm.

CHANGE `topic:manosphere.male_body_image`:
| male_body_image | Male body image & muscle dysmorphia | Pressure on men's bodies and muscle dysmorphia. Body dysmorphia in general or in women goes to `mental.ocd_personality`, or to `mental.eating_disorders` when it is about eating; body dysmorphia invoked in transgender debates goes to `gender.gender_identity_science`. | muscle dysmorphia; male body dysmorphia; male body image; bigorexia |
Why: the male label is rare (70 episodes, 34 podcasts). "Body dysmorphia" in general (633 episodes, 126 podcasts) has no home and shows up in eating-disorder (78264/4), film (23654/1) and trans-debate (8703/6) contexts.

CHANGE `topic:gender.youth_gender_medicine`:
| youth_gender_medicine | Gender medicine for minors | Any intervention for minors, social transition included: puberty blockers, cross-sex hormones and surgery, and laws, reviews and guidelines concerning them. Add `gender.gender_identity_science` when whether children can know or should be affirmed is also argued. | puberty blockers; gender-affirming care for kids; WPATH; Cass Review; gender clinics for children; bans on youth transition; Skrmetti; social transition |
Why: 1,971 episodes (94 podcasts). The "Cass Review" example occurs in only 12 episodes. WPATH and Cass together reach 123 (Walsh, Shapiro, Kelly, Kirk, Morning Wire), and Skrmetti is the main legal reference (167828/1).

CHANGE `topic:gender.adult_transition`:
| adult_transition | Adult transition care | Hormones and surgery for transgender adults, and transition procedures discussed with no age stated. When the passage is about minors, use `gender.youth_gender_medicine`. | sex change; gender reassignment surgery; HRT for trans adults; top surgery; bottom surgery; vaginoplasty; phalloplasty |
Why: 1,083 episodes (95 podcasts). "Sex change" (e.g. 71370/5) is the most common lay term and is missing. Most procedure talk gives no age (207200/2).

CHANGE `topic:gender.lgbtq_health`:
| lgbtq_health | LGBTQ health, disparities & orientation | Health issues and disparities of LGBTQ people outside transition care, conversion therapy, and claims about the origins of sexual orientation (genetic, hormonal, chosen). A specific condition (suicide, HIV) also takes its own subtopic. | LGBTQ mental health; conversion therapy; trans suicide statistics; gay gene; born this way; homosexuality is biological |
Why: the origins of orientation (broad query 437 episodes, 119 podcasts) has no home. Examples: "sexual orientation and… hormones and brain development… in utero" (27183/3); "largely, if not entirely, genetic" (390284/3); "the left claims that homosexuality is biological" (207415/0).

ADD `topic:gender.trans_athletes` under `gender`:
| trans_athletes | Transgender athletes & sex differences in sport | Physical sex differences as they bear on transgender and intersex/DSD athletes: male-puberty advantage, testosterone suppression rules, sex testing and injury risk to competitors. A slogan about "men in women's sports" with no physical or health content is not health content. | male puberty advantage; testosterone suppression; sex testing; Lia Thomas; Imane Khelif; Fallon Fox; injuries to female athletes |
Why: 691 episodes match the sports terms. 333 of them (Megyn Kelly 74, Rogan 50, Walsh 34, Kirk 23, Behind the Bastards 18, Shapiro 15, REAL AF 13, Morning Wire 13, Modern Wisdom 10, Pod Save 9) also discuss physiology. Examples: "you don't even need to suppress your testosterone" (40118/2); "notwithstanding their male body parts, their testosterone" (8178/7). No current subtopic fits.

CHANGE `topic:pediatrics.infant_care`:
| infant_care | Newborn & infant care | Caring for newborns and infants, including newborn procedures (vitamin K shot, newborn circumcision), NICU care and newborn sleep safety (SIDS, sleep position, co-sleeping). Infant mortality rates go to `pregnancy.maternal_mortality_access`; children's sleep routines go to `sleep.sleep_hygiene_environment`. | newborn care; NICU; vitamin K shot; newborn circumcision; safe infant sleep; co-sleeping; SIDS; colic; tummy time; swaddling |
Why: SIDS and co-sleeping (25117/0, 318651/2) and NICU stays (207478/4) recur. Circumcision is double-listed today (326 infant-context episodes).

CHANGE `topic:pediatrics.pediatric_care`:
| pediatric_care | Pediatric care | The experience of children's medical care: pediatric visits, children's dosing and pediatrician relationships. A pediatrician's vaccine advice or a family's vaccine dispute with a pediatrician goes to `vaccines.uptake_hesitancy`, plus this label only when the care relationship itself is discussed. A childhood illness takes its own subtopic plus a population label. | pediatrician; well-child visit; children's dosing; kids' medications; finding a pediatrician; pediatric chiropractic |
Why: 1,081 of the 1,908 episodes mentioning a pediatrician also mention vaccines or shots. Examples: "every pediatrician that we've had has recommended… the COVID vaccine" (5851/2); "the pediatrician says you got to get this for your kid to attend school" (36591/6). Pediatric chiropractic recurs (186579/2).

## Codebook and prompt notes

1. **§3 (What counts as health content): add a political-token exclusion parallel to the crime-word rule.**
   - Proposed wording: "Abortion, transgender issues, 'men in women's sports', birth rates and similar subjects named only as electoral issues, campaign positions or items in a list of political issues, with nothing said about a procedure, its safety, access, the body or a health consequence, are not health content. A moral or legal argument about the subject itself (abortion law, youth transition bans) is health content."
   - Evidence: `abortion` 11,826 episodes, of which about 70% of sampled hits are list or horse-race mentions (89482/1, 169244/0, 175685/6). "Men in women's sports" 691 episodes, about half with no physiology (37515/1, 81428/1). "Gender ideology" as a political label (206372/5, 13983/0). Without this rule the reproductive and gender domains will be dominated by Kirk, Shapiro and Walsh campaign talk.

2. **§3 Ads: give the recurring formats in this slice explicit outcomes.**
   - (a) Menopause telehealth: "MIDI Health provides specialized care for perimenopause and menopause" (5742/4; about 440 NPR episodes). It is health content: `womens.menopause` as `advertisement`, with a `clinic_or_practitioner_service` product.
   - (b) Hims or Roman ED and weight-loss reads (12282/1, 611798/2): `sexual.sexual_function` and/or `glp1`, `advertisement`.
   - (c) Advocacy and nonprofit reads about health services: the Planned Parenthood Title X read, "a program that funds birth control, cancer screenings, and more" (1140151/1; about 626 The Daily episodes). These state a health service, so they pass the ad test. The codebook should say whether the advocacy organization counts as a product. I suggest no product mention unless a service is offered to the listener.
   - (d) Values-based period-product ads: "Garnu… 100% organic… most tampon brands fund Planned Parenthood" (185922/1, 185802/5). Code `womens.period_products` with `advertisement` and `frame:naturalness_appeal`; "organic" alone does not invoke `narrative:tampon_toxins` (implicature rule (a)).
   - (e) Cross-promos for non-health shows that name a health-policy case: "whether bans on conversion therapy for LGBTQ kids count as censorship" (4153/9; most of Pod Save America's 363 `lgbtq_health` hits). Under the current ad test this fails (no health product or effect). Say explicitly that it is excluded, or it will inflate `lgbtq_health`.

3. **§2 (ASR) or a new "ambiguous terms" list in the rubric for this slice:**
   - "HRT" (Hostage Rescue Team, 155248/5; male TRT; trans HRT);
   - "PrEP" vs meal or sports "prep" (bare PrEP matches about 12,000 extra episodes);
   - "low T" as fantasy-football slang (163955/2);
   - "Plan B" and "the pill" as idioms;
   - "miscarriage of justice" (396 episodes);
   - "maternity ward" as a SimpliSafe slogan (25850/7);
   - "HIV" for HEV light (190160/488);
   - "Calman" for Kallmann syndrome (77543/1);
   - "PMOS" as PCOS's new name (191028/120).

4. **§5.1 co-labeling rule 9 (population-specific subtopics plus the condition): name the reproductive cases.**
   - Postpartum depression or psychosis → `pregnancy.postpartum` + `mental.depression` or `mental.serious_mental_illness` (159272/20).
   - Postpartum hair loss → `pregnancy.postpartum` + `skin_beauty.hair_loss_hair` (89641/4).
   - Trans suicide statistics is already listed.
   - Infertility as a side effect of cancer treatment → the cancer subtopic + `fertility.infertility_treatment` only if fertility is discussed beyond the one word (41195/3 is a list item; rule 6 applies).

5. **§5.1 policy rule 3: add "miscarriage or ectopic care under abortion bans → `fertility.abortion` + `pregnancy.pregnancy_health`".** Evidence: 5643/0 and 84267/4. These are frequent on Pod Save America and MeidasTouch and will otherwise split.

6. **§3 fiction and scripture:**
   - Circumcision in Bible-reading podcasts (305 episodes) and "intersex" in a film review (388474/3) are the dominant non-health hits for those terms. The existing "fiction, legend, scripture… default to exclusion" sentence covers them, but a circumcision example would help.
   - Credential intros ("a board-certified obstetrician and gynecologist", 174886/0) are evidence (`credential_appeal`) when used as grounds, never a `womens` topic on their own.

7. **§5.2 narratives, stance on political testosterone talk.** "They want weak men in this country… Our testosterone rates are going down" (38523/2) invokes `narrative:testosterone_collapse` (asserted) and takes `frame:political_partisan` ("they" are the political opponents). The topic is `manosphere.masculinity_ideology`, not `mens.testosterone`, unless levels or treatment are discussed. Without this guidance coders will put every "soy boy" jab on `mens.testosterone`.

8. **§5.5 population: transgender debates.** Passages about "trans kids" take `population:lgbtq` + `population:children` (or `adolescents`), since the content is about the group's health as a group. A single named detransitioner telling their story takes neither (one person's own condition), even though it is the typical format on Kelly and Walsh (8307/6, 167828/1). This follows from the current rule; an example would make it explicit.

9. **§5.3 frames: "gender ideology".** The phrase is the right-wing shows' standard noun for the subject. It invokes `narrative:trans_identity_disorder` only when the proposition that trans identity is a disorder or contagion is stated or plainly implied. Used as a political noun ("boycotted corporations that promoted gender ideology", 206372/5), it takes `frame:political_partisan` and no narrative. The trans_identity_disorder row currently says "'gender ideology'… belong here", which will make every use of the noun a narrative hit.
