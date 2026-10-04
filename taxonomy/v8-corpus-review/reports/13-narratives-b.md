# Narratives B (pharma, wellness, hormone, system, other): corpus review

**Status: complete.** All five families were reviewed with counts and read samples. This
includes the 13 wellness labels that the first pass covered only by counts, and a
word-boundary `\bcandida\b` rerun.

- Pharma counts come from the /mnt/data2 copy of cq.py.
- Everything else comes from `/mnt/internal/felix/podcast-corpus-text/cq.py`. The coordinator
  says the two copies are byte-identical.
- Counts are segments / episodes / podcasts from proposition-shaped regexes unless the text says
  "subject". Treat them as rough: every query was hand-built and noise-checked by reading
  samples.

## Summary

- **Findability.**
  - Almost every label's core proposition is voiced in the corpus by several podcasts.
  - Two are essentially absent and are proposed for removal:
    - `vitamin_a_toxicity`: 1 asserting episode and 1 questioning episode, both on longevity
      shows.
    - `heart_not_pump`: about 3 episodes across 2 podcasts.
  - Rare but worth keeping (classic or topical):
    - `deodorant_breast_cancer`: 19 eps / 10 podcasts.
    - `glasses_worsen_vision`: ~10 eps / 4 podcasts, mostly Rogan 2015-16.
    - `chiropractic_stroke_risk`: ~10 real eps.
    - `leucovorin_autism_treatment`: 22 eps / 13 podcasts.
    - `fever_suppression_harmful`: 29 eps / 19 podcasts.
- **Three ADDs, all well above the bar:**
  - `social_media_youth_mental_health`, the Haidt lead, now verified: 469 eps / 137 podcasts.
    The proposition is voiced ("Social media is to blame for causing a mental health crisis";
    "Instagram … causing massive depression amongst … young girls") and openly contested.
  - `mental_illness_not_real`: 61 eps / 38 podcasts on a narrow query ("depression isn't real",
    "ADHD is not a real disease").
  - `pharma_ads_control_media`: 164 eps / 52 podcasts. The claim is "the largest advertiser of
    the media is Big Pharma … this is why"; `fda_captured` covers agencies only.
- **Coined terms and slogans that do NOT carry the proposition.** These are the biggest source of
  likely over-labelling. Each label's examples or definition should say so.
  - "sick care": 154 eps; usually just "reactive, not preventive".
  - "gender ideology": ~1,700 episodes on the wider query; mostly culture-war politics, which is
    a frame, not the `trans_identity_disorder` proposition.
  - "Great Reset": mostly economic or political, with no health means.
  - "terrain theory": usually "the terrain matters too", not "germs don't cause disease".
  - "type 3 diabetes": mechanism only, not reversibility.
  - "NoFap": porn abstinence, not semen-retention benefits.
  - "chemtrails" used as a byword for conspiracy belief in comedy lists.
- **"They want us sick" needs an actor and motive rule.** The phrase splits across
  `pharma_creates_customers` (profit), `food_engineered_to_harm` (food industry) and
  `depopulation_agenda` (control).
- **Ads are the main volume driver for many wellness narratives.** Parasite cleanses, mold-free
  coffee, non-toxic cookware and candles, EMF blockers, red-light panels, grounding mats,
  "quantum frequency" devices, Little Spoon and Cerebelly baby food. The codebook's
  product-attribute rule (5.2a) and its disparaging-imperative rule collide in ad copy ("Stop
  cooking with toxic cookware"). A tie-breaker is proposed.
- **Presence versus harm.** For `microplastics_catastrophe` and `baby_food_metals_harm` the
  usual statement is presence ("found in the brain", "lead and arsenic in baby food"), not
  disease causation.
  - The narrative's "proven/established" wording describes almost nothing actually said: 17
    episodes make a causal claim.
  - Redefine as "microplastics are causing serious disease", and state that presence alone is a
    topic.
- **Boundary tightenings from real passages:**
  - Age-related testosterone decline (andropause, women's T) is not `testosterone_collapse`.
  - A single-disease cause (EBV in Hashimoto's or MS) is not `stealth_infections_root`.
  - Toxic shock syndrome is not `tampon_toxins`.
  - Population-level obesity statistics alone are not `sickest_generation`.
  - "Abortion up until the moment of birth" (170 eps) is as frequent as "born alive" (142 eps).
    Fold it into `abortion_infanticide`.
- **Pharma findings from the first pass still stand:**
  - Near-miss volume for antidepressants ("don't work for everyone"), chemical imbalance (folk
    use), Adderall (comedy and recreation) and GLP-1 (ads, muscle-loss mitigation).
  - Fluoride: pineal calcification goes to `fluoride_lowers_iq` unless a control purpose is
    stated.

## Label-by-label findings

### pharma_narratives

**statins_harmful.** Query: `statins?` near poison, harm, useless, CoQ10, diabetes, dementia,
"don't work", scam, lie, profit.

- Counts: 225 eps / 45 podcasts. Subject total: 1,098 eps / 96 podcasts.
- Verdict: fine. Voiced as "they don't work as well as you think … a plethora of side effects"
  (189403/2).
- Boundary: "statins … are overused" (190052/626) is overuse, not harm or uselessness.

**antidepressants_ineffective.**

- Counts: 100 eps / 37 podcasts. Subject: 3,676 eps / 215 podcasts.
- Verdict: examples change plus a note.
- Assertions: "Placebo was almost as efficacious as the antidepressant" (318878/1);
  "Antidepressants Are Placebos" (title, 185844).
- Non-narrative uses: "SSRIs don't work for everyone" (185586/1); "it's overused" (175579/6).

**chemical_imbalance_myth.**

- Counts: 128 eps / 46 podcasts (phrase alone: 397 eps / 106).
- Verdict: fine, with a codebook note.
- Assertions: "the biggest big pharma scam … depression is rooted in a chemical imbalance"
  (206327/1); "the chemical imbalance theory is not based in real science" (15011/2).
- Most bare uses are folk explanation (39199/2, 88184/2).

**ssris_cause_violence.**

- Counts: 153 eps / 51 podcasts. SSRIs near suicide: 94 eps / 42. "Akathisia": only 13 eps.
- Verdict: fine; examples change.
- Real phrasing: "How many of these mass shooters are on psychiatric drugs? … the majority"
  (3956/6); "two hundred milligrams a day of Zoloft" (33656/18).
- Rebuttal: 329057/348.

**therapy_harms_children.**

- Counts: "bad therapy" or Shrier, 138 eps / 27 podcasts. "Therapy culture", 226 / 68 (some
  reality-TV noise). Over-diagnosis of kids, 43 / 26.
- Verdict: definition change (young people; over-diagnosis).
- Real phrasing: 175763/0 (Gen Z girls); "Overdiagnosing of kids is basically just a cop out"
  (33791/3).

**tylenol_autism.**

- Counts: 79 eps / 41 podcasts. Glutathione elaboration: 25 eps / 15.
- Verdict: fine.
- Real phrasing: "Tylenol … decreases something called glutathione" (33783/5); "Tylenol 'Tism"
  (163096).

**leucovorin_autism_treatment.** Counts: 22 eps / 13 podcasts (subject). Verdict: rare but
topical; keep.

**fever_suppression_harmful.**

- Counts: 29 eps / 19 podcasts.
- Verdict: rare; examples change.
- Real phrasing: "fevers are good for you" (185784/8); "reduce the fever artificially … sicker
  for longer" (178212/4).

**birth_control_harms.**

- Counts: ~155 matching segments on health and politics shows. A recurring Title X ad on The
  Daily inflates the raw count (593 eps).
- Verdict: examples change.
- Real phrasing: "makes you fat, doubles risk of depression … triples risk of suicide" (38344/1);
  "the pill … women are attracted to men with lower testosterone" (5161/14).
- Clot risk stated as known fact: 190883/129.

**abortion_pill_dangerous.** Counts: 102 eps / 29 podcasts (subject near safety words). Abortion
near breast cancer: 16 eps / 11. Verdict: fine.

**hrt_dangerous / hrt_fears_overblown.**

- Counts: harm words, 340 eps / 59 podcasts. WHI or black-box talk, 407 / 68.
- Verdict: fine.
- `hrt_fears_overblown` dominates (50114/6, 54359/5). The harm side appears mostly as the
  rebutted premise (190557/150), which the existing rule handles.

**glp1_dangers.**

- Counts: 216 eps / 67 podcasts.
- Verdict: definition or example change.
- Real phrasing: "stomach paralysis" (33519/151).
- Non-narrative volume: ad boilerplate (83880/1, 81114/2) and mitigation episodes (176587/3).
- The opposite pole ("GLP-1s are a miracle drug") is 38 eps / 28 podcasts, mostly passing.
  Watch it; no ADD.

**adhd_meds_harmful.**

- Counts: broad, 635 eps, mostly recreational and comic. Narrow, 59 eps / 30 podcasts.
- Verdict: note and examples.
- Real phrasing: "overmedicating children" (70786/11); "giving them baby meth" (74526/2).

**pharma_creates_customers.**

- Counts: 383 eps / 73 podcasts. "Sick care": 154 / 46.
- Verdict: definition and examples change.
- "Sick care" is mostly the reactive-care critique (87972/6, 183006/0).
- The proposition: "incentives … to keep us sick" (6660/0); "the reason they want us sick is so
  they can make the money on the pharmaceuticals" (10589/5).
- Control variant: 195939/0.

**medical_errors_leading_cause.** Counts: 117 eps / 42 podcasts. Verdict: examples ("the fourth
leading cause of death is medications", 186171/2).

**fluoride_lowers_iq / fluoride_mind_control.**

- Counts: IQ or brain, 111 eps / 40 podcasts. Control or pineal, 46 / 21.
- Verdict: boundary change.
- Pineal claim without control: 181242/4. Control: "dumb kids down" (14582/0).

**root_canals_amalgams_illness.**

- Counts: 223 eps / 53 podcasts.
- Verdict: examples change.
- "Cavitation" also means chiropractic joint popping (186205/2), shockwave (186018/0) and
  ballistics.

**sunscreen_harmful / sun_exposure_cures.**

- Counts: 241 eps / 74 podcasts and 254 / 86 (noisy).
- Verdict: fine. Examples: 128268/6, 447683, 195334/2 ("Avoiding the sun … as bad for you as
  smoking").

**deodorant_breast_cancer.** Counts: 19 eps / 10 podcasts. Verdict: rare; keep.

### wellness_narratives

**germ_theory_denial.**

- Counts: denial-shaped query ("terrain theory", "viruses don't exist", "germ theory is bogus",
  Pasteur recanted, Béchamp): 54 eps / 26 podcasts. SuperLife has 12.
- Verdict: definition change. "Terrain theory" is mostly the soft claim that the body's terrain
  matters ("What we can do with our terrain", 181309/0; "we are moving towards this whole
  terrain theory", 190046/72).
- Hard denial: "it's all based on a bogus theory called the germ theory" (185982/2, Chiro
  Hustle).
- Reported: "weird ones like viruses don't exist" (177543/1).

**parasites_cause_disease.**

- Counts: 192 eps / 32 podcasts ("parasite cleanse", "parasite pandemic", "everyone has
  parasites"). Ads inflate this: Miss Understood 37 and Candace 26 (Parify and Wellness Company
  reads).
- Verdict: examples change plus an ad note.
- Real phrasing:
  - "Most people don't know they have parasites" (192397/0).
  - "you most likely need to do a parasite cleanse, even if you don't [have them], especially if
    you're chronically sick" (78216/4).
  - "parasite cleanse at least once a year as preventive measure" (48614/2, ad).
  - "The Worm Queen … the Parasite Pandemic" (178183).

**heavy_metal_toxicity_widespread.**

- Counts: 493 eps / 67 podcasts (subject: heavy-metal toxicity, detox, chelation).
- Verdict: fine. Undiagnosed burden is voiced: "Just heavy metal toxicity prevents [thyroid
  hormone] from getting into the cell" (190949/62); "the best tests to understand … heavy metal
  toxicity" (180761/13).
- Noise: true-crime poisoning (170861/4), occupational exposure (190145/168) and superfood
  "chelation ability" copy (184028/0). None of these is the narrative.

**mold_toxicity_widespread.**

- Counts: 963 eps / 102 podcasts (subject).
- Verdict: fine, plus an ad note. Strongly present on functional-medicine shows: "we're just
  swimming in this stuff and mold and mycotoxins" (192472/3); "Mold Doctor" episodes.
- Mold or mycotoxin near coffee: 223 eps / 41 podcasts, mostly "tested for mold and
  mycotoxins" coffee ads (Candace 47, Matt Walsh, MeidasTouch, 175055/5). That is a product
  attribute, not the narrative.

**stealth_infections_root.**

- Counts: 570 eps / 63 podcasts (subject: EBV, mycoplasma, stealth or hidden infection).
- Verdict: definition change (add a single-disease exclusion).
- Broad claim: "It's all about viruses. It's all about the Epstein-Barr virus" (184196/2,
  Medical Medium); "Undiagnosed Infections Are Silently Causing Chronic Disease" (181883 title).
- Single-disease claim: "the reactivation of EBV … causing the trouble for Hashimoto's patients"
  (190832/70). Hidden jaw infections also overlap `root_canals_amalgams_illness` (181044/2,
  192642/2).

**metabolic_dysfunction_root.**

- Counts: 67 segments on a narrow query (avoid "bad energy", which is reality-TV noise).
- Verdict: fine.
- Real phrasing: "metabolic dysfunction, which is really the root driver of almost all chronic
  illnesses" (180683/3); "mitochondrial dysfunction is at the root of literally every single"
  (190074/152); "[insulin resistance] underpins every chronic disease we know" (176517/1).

**inflammation_root_cause.**

- Counts: 124 eps / 26 podcasts. 67 are Dr. Jockers, much of it a repeated turmeric sponsor
  line: "chronic inflammation is at the root of every degenerative condition" (192849/2).
- Verdict: fine.
- Shares spans with the metabolic label: "insulin resistance and inflammation … at the root of
  all chronic metabolic diseases" (182016/1) takes both.

**detox_needed.**

- Counts: 889 eps / 111 podcasts ("toxic load/burden", "toxins build up", "body can't keep up").
- Verdict: examples change.
- "Toxic load" is the dominant coined term ("He had a really high toxic load", 193087/7). It also
  appears with PFAS: "once in your body, you can't get rid of. Yeah, they build up" (15553/4).
- PFAS bioaccumulation is a documented property. When a specific chemical is named, prefer
  `household_toxins_poisoning` or a claim over this narrative.

**leaky_gut_root_cause.**

- Counts: 1,345 eps / 70 podcasts (subject).
- Verdict: fine. Usually a single-disease cause, which the definition allows: "leaky gut
  syndrome, that's probably a reason why a lot of people have autoimmune diseases" (71204/2).
- Many mentions treat leaky gut only as a diagnosis or test result (192361/3, ad). That is
  subject only.

**candida_overgrowth_widespread.**

- Counts with `\bcandida\b|yeast overgrowth|systemic yeast`: 524 eps / 64 podcasts (subject).
- Verdict: fine, plus a boundary note.
- Usually one item in a burden list: "parasites and candida, or yeast overgrowth … can cause"
  (193105/1); "candida, parasites, SIBO" (192979/4).
- A single patient's yeast overgrowth (182842/2) is not the widespread claim.

**adrenal_fatigue_real.**

- Counts: 257 eps / 43 podcasts. The coined term carries the proposition.
- Verdict: fine; examples.
- Practitioners hedge or rename while keeping the concept: "we call it adrenal fatigue … That's
  not really what's happening. You're down-regulating" (190909/134); "you put in hypothalamic HPA
  axis dysfunction … They just rename a thing" (190889/67).

**chronic_lyme_widespread.**

- Counts: "chronic Lyme", Plum Island, bioweapon: 188 eps / 40 podcasts.
- Verdict: fine.
- Real phrasing: "patient after patient who struggled … for decades, with chronic Lyme" (182471/1);
  "the traditional medical establishment doesn't quite buy chronic Lyme … post-treatment Lyme
  disease syndrome" (181883/3).
- "Long Lyme" (438897/1) is a newer term. Reality-TV coverage (Yolanda Hadid, Watch What
  Crappens) is mostly mocking.

**mthfr_explains_illness.**

- Counts: 1,105 eps / 73 podcasts (subject; "methylation" is broad).
- Verdict: fine. Proposition: "you'll have a different child … if your child has this MTHFR gene
  mutation" (16730/8).
- Rebuttal: "even if you have completely suboptimal MTHFR, it doesn't mean anything terrible"
  (190369/515).
- "Methylated B vitamins" in a general stack (176633/8) is a premise only.

**vitamin_megadose_cures.**

- Counts: 246 eps / 60 podcasts (broad); 120 segments narrow (IV vitamin C, cancer, sepsis).
- Verdict: fine.
- Real phrasing: "High dose IV vitamin C" as a cancer option (182553/1, 192638/3); "Linus Pauling …
  a cure for cancer. We wish" (85986/4, rebutted).

**vitamin_a_toxicity.**

- Counts: 41 eps match, but 23 are MeatEater mentions of a person named Garrett Smith, and others
  are polar-bear-liver history.
- The proposition appears in 1 episode (180821, Live Beyond the Norms, "The Vitamin A Toxicity
  Epidemic") and is questioned in 1 (190214/285, 297).
- Verdict: REMOVE (rare and unimportant). `unlisted_narrative` covers the odd case.

**methylene_blue_miracle.**

- Counts: 247 eps / 43 podcasts (subject). Niddam has 62.
- Verdict: fine; mostly protocol and dosing talk. The broad-enhancer claim appears in episode
  titles ("Two Game-Changers For Better Energy, Focus", 190061).

**red_light_cure_all.**

- Counts: 554 eps / 76 podcasts on a broad query. Habits and Hustle has 115, mostly sponsor
  reads.
- Verdict: fine, with an ad note. Ad lists of several specific benefits ("muscle preserving, good
  for skin, can also accelerate healing", 195331/11) are a borderline case. Broad claims: "red
  light therapy can help reduce fever … help the body with healing" (185806/2).

**grounding_heals.**

- Counts with `\bearthing\b` (unbounded "earthing" matches "unearthing"): 325 eps / 65 podcasts.
  SuperLife has 113, largely a recurring ad for a multi-modality pad.
- Verdict: fine. "Research on … earthing … what it does to your inflammatory markers"
  (176548/2).

**peptides_safe_miracle.**

- Counts: 918 eps / 78 podcasts (broad); 81 segments narrow.
- Verdict: definition change.
- Broad claims: "the two of the most profound healing peptides on the planet" (180897/462); the
  "Wolverine stack … accelerate healing" (195282/3); "naturally made by the body" (78334/6).
- Single-use claims: "BPC-157 … speeds up gut healing" (190501/30); "BPC and TB500 post-surgery"
  (190550/62).

**nad_reverses_ageing.**

- Counts: 204 eps / 36 podcasts (broad, ad-inflated); 37 segments narrow.
- Verdict: fine. "NMN … a great supplement to reverse aging" (190610/89).
- Rebuttal episode: "Debunking Longevity Myths" (181176, Brenner).

**fringe_chemical_cures.**

- Counts: 343 eps / 88 podcasts, mostly non-health (turpentine and borax in history and hunting
  shows, true crime).
- Verdict: fine but rare in proposition form. Chlorine dioxide for cancer or autism: 190478/17,
  190462/59 (questioned), 81097/1 (reported, rebutted).

**energy_frequency_healing.**

- Counts: 366 eps / 48 podcasts. SuperLife has 120 and Biohack-it 31, largely ads ("Lila Quantum
  Tech is leading the way in quantum frequency healing", 178180/4).
- Verdict: examples change. Add "quantum" devices. PEMF includes cleared medical uses, so it
  counts only with a broad cure claim.

**heart_not_pump.**

- Counts: 22 segments, of which about 3 episodes are real (Niddam 189960; Rogan 70858/0; Niddam
  190300/321).
- Verdict: REMOVE (essentially absent).

**alzheimers_reversible.**

- Counts: 438 eps / 64 podcasts.
- Verdict: definition change ("type 3 diabetes" alone).
- Real phrasing: "MCT oil reverses Alzheimer's" (195926/7, 14840/3); "even if one person can
  reverse dementia" (182198/4).
- "Alzheimer's is type three diabetes" with no reversal claim: 190596/30.

**autism_recoverable.**

- Counts: 76 eps / 37 podcasts.
- Verdict: fine.
- Real phrasing: "three kids who fully reversed their autism" (185612/6).
- Many rebuttals: Behind the Bastards, "The Bleach Hunters" (163002/1).

**glasses_worsen_vision.**

- Counts: 17 segments / ~10 eps / 4 podcasts. Rogan 2015-16 is most of it; also SuperLife 181134
  and Niddam's "END MYOPIA" episode.
- Verdict: rare. Keep only if cheap.

**chiropractic_stroke_risk.**

- Counts: 25 eps / 10 podcasts. Chiro Hustle's 15 are mostly "dissection lab" in chiropractic
  school, so roughly 10 real episodes.
- Verdict: rare; keep.
- Real phrasing: "had gone for a neck adjustment … Ended up with a dissection of her artery"
  (23987/6).

**emf_5g_harm.**

- Counts: 771 eps / 150 podcasts (broad, with heavy true-crime "cell tower" noise); 106 segments
  narrow.
- Verdict: fine, with an ad note (EMF-blocker ads).
- Real phrasing: "five countries with 5G towers … how … did it get" (15626/18, reported);
  "getting away from EMFs … with my brain cancer history" (185700/1).

**chemtrails.**

- Counts: 492 eps / 91 podcasts. Rogan has 162.
- Verdict: definition change. Most hits use "chemtrails" as a byword for conspiracy belief ("I
  hang out with people that believe in chemtrails", 71667/8; "Chemtrails, Tower Seven … UFO",
  71255/19).
- Few passages make a health claim: "some mild … chemtrails hitting your food" (18696/1).

**microplastics_catastrophe.**

- Counts: subject, 1,256 eps / 108 podcasts. Explicit causal claims ("cause", "linked to",
  "leads to" plus a disease): 17 eps / 13 podcasts.
- Verdict: definition change.
- Typical statements are presence or alarm: "found in lungs, heart, brain, penis" (20037/0); "the
  nanoplastic data … even more terrifying" (182112/2).
- Causal claims: "now being linked to infertility, heart disease, cancer" (192435/0);
  "microplastic accumulation leads to Alzheimer's" (25957/30); "a whole credit cards worth of
  plastic every week" (182141/0).

**household_toxins_poisoning.**

- Counts: 387 eps / 52 podcasts. The Toast's 91 are Caraway cookware ads; Culture Apothecary 71
  and SuperLife 69 are largely ads.
- Verdict: fine, with an ad rule.
- Real phrasing: "Everything from toxic candles to seed oils … contributing to rising
  infertility" (185907/5); "Stop cooking with toxic cookware" (175060/4, ad imperative).

**tampon_toxins.**

- Counts: 139 eps / 55 podcasts (broad).
- Verdict: definition change. Much of it is toxic shock syndrome (23920/0, 21232/0-1), which is a
  bacterial risk, not toxins.
- Proposition: "these are the chemicals that you want to completely avoid. That's tampons and
  pads" (191020/26).

**baby_food_metals_harm.**

- Counts: 182 eps match, but "formula" is noisy. About 33 segments mention baby food with metals;
  many are ads (Little Spoon or Cerebelly on MeidasTouch and The Toast).
- Verdict: rare as a harm claim. Speakers state presence or regulation ("He's taking lead and
  arsenic out of baby food", 174978/5), seldom that the metals cause autism or brain damage.
- Keep, but presence alone is a topic.

### hormone_narratives

**testosterone_collapse.**

- Counts: 983 eps / 115 podcasts on a broad query. Much of it is age-related decline
  (andropause 175006/0, women 179777/0) or "testosterone drops when men become fathers"
  (19563/13).
- Verdict: definition change.
- Proposition: "Total collapse of testosterone levels in America" (1139901/0, quoting Tucker);
  "Does anyone know why testosterone levels have dropped so much?" (7785/8); "testosterone levels
  are dropping, sperm counts are dropping" (78771/7).

**sperm_count_collapse.**

- Counts: ~150 eps on the narrow query ("countdown" unbounded catches sports).
- Verdict: fine. "Sperm counts are down 50% over the last five decades" (388617/5); "male sperm
  count is plummeting" (37896/1).
- Usually co-occurs with `testosterone_collapse`. A span stating both takes both.

**semen_retention_benefits.**

- Counts: 148 eps / 44 podcasts, heavily comedy (Pardon My Take 23).
- Verdict: examples change. "NoFap" often means porn abstinence with no benefit claimed
  (28542/5, 197055/1).
- Benefit claims: "That's why we retaining our semen, so we not picking the partner"
  (86732/13); "Holding your seed" (200849/6); "Taoists … semen retention for longevity"
  (185343/3).
- Rebuttal or mixed: Science Vs episode (318348/2).

**endocrine_disruptors_feminizing.**

- Counts: 1,214 eps / 133 podcasts (broad, includes "feminize").
- Verdict: examples change.
- Coined term "gay frogs" (318940/23, 14753/6); "male frogs became female, and they actually
  laid eggs" (51857/0).
- Deliberate variant: "they've put atrazine in the water for twenty … years to make them have
  low test" (64192/4). That also takes `depopulation_agenda` if control is the stated point.
- Atrazine named in a pesticide list (181100/9, 4953/3) is not the narrative.
- "Turning kids trans" can be about teachers, not chemicals (24909/1).

**gender_care_harmful_youth.**

- Counts: 1,294 eps / 100 podcasts. Matt Walsh 284 and Charlie Kirk 283.
- Verdict: examples change. The dominant vocabulary is "mutilation", "butchery" and "chemical
  castration": "the butchery of our children through gender-affirming care" (37403/1);
  "Gender affirming care is butchery" (37402/3).

**gender_care_lifesaving.**

- Counts: 76 segments narrow.
- Verdict: examples change. The proposition appears overwhelmingly as `rebutted` on right-leaning
  shows, and the coined form is "Would you rather have a dead daughter or a living son?"
  (8069/1, 39709/1 "moral blackmail", 7458/4).
- Assertion is rare and mostly quoted: "gender-affirming care … can be life-saving" quoted from
  the AMA (389030/2).
- Coding note: 206490/7 and 388506/5 are a Daily Wire promo in which a speaker voices the
  lifesaving proposition, plainly in parody. Code it `rebutted`.

**trans_identity_disorder.**

- Counts: 1,709 eps / 96 podcasts on a query that includes "gender ideology". "Gender ideology"
  alone dominates (Matt Walsh 404).
- Verdict: examples change.
- Most "gender ideology" uses are culture-war politics with no proposition about what trans
  identity is: "find a middle ground in the war over gender ideology" (207055/0); "woke, pride,
  progress, gender ideology, crap" (389035/1).
- Proposition proper: "it's become a social contagion" (12240/6); "if they really can be born in
  the wrong body…" (38972/0, mocking).

**abortion_infanticide.**

- Counts:
  - Born-alive or post-birth: 142 eps / 23 podcasts.
  - "Abortion up until the moment of birth" or "through the ninth month": 170 eps / 18.
  - "Infanticide" alone: noisy (dolphins, China).
- Verdict: definition change (fold in up-to-birth).
- Real phrasing: "legalizing post-birth abortion" (206074/4); "legalized abortion nationwide up
  until the moment of birth" (39661/1); "abortion all the way up to birth, all the way through the
  ninth month" (40339/3).

### system_narratives

**sickest_generation.**

- Counts: chronic-disease-in-kids phrasing, 59 eps / 24 podcasts. A broad query with obesity
  statistics gives 91 / 27.
- Verdict: definition change.
- Proposition: "forty percent of American kids have a chronic disease" (84749/4); "the most
  depressed, suicidal … sick generation in history" (37752/2).
- Obesity statistics alone ("forty percent of kids are overweight", 182354/0, 183382/2) are not
  the proposition.

**autism_epidemic_environmental.**

- Counts: 71 eps / 28 podcasts.
- Verdict: fine.
- The coined statistic "one in ten thousand … to one in 31/36" carries the real-increase claim
  (38924/4, 4003/0, 175340/189, 388757/1).
- Co-occurs with `vaccines_cause_autism`: "autism rates, have exploded, and it's all coincident
  with the explosion in that schedule" (38236/1).

**fda_captured.**

- Counts: 116 segments narrow. "Revolving door" and "regulatory capture" are mostly non-health
  (DOJ, sports, FAA).
- Verdict: examples change.
- Real phrasing: "Forty-six percent of the FDA's budget comes directly from user fees" (182536/0);
  "The majority of research … out of the NIH is funded by pharma" (7981/2); "regulators are owned
  by the industry they're supposed to regulate" (205194/4); "They're bought out by pharmaceutical
  companies" (7035/2).

**doctors_paid_to_prescribe.**

- Counts: ~111 eps / 47 podcasts (broad).
- Verdict: definition change.
- Proposition: "doctors are getting paid to vaccinate kids" (7922/3); "These doctors are
  incentivized to prescribe" (63035/10).
- Noise: public vaccination incentives such as donuts and lotteries (1139332/0, 15811/1), and
  documented opioid kickbacks narrated as history (175114/7).

**depopulation_agenda.**

- Counts: the full count query timed out; samples show 1,430 segments for depopulation, Great
  Reset, "eat the bugs", "own nothing", useless eaters.
- Verdict: definition change. Many hits have no health means:
  - "The Great Reset is fascistic" (11916/5).
  - "the great reset's coming" (39939/3, eschatology).
  - Literal rural or historical depopulation (175785/3, 466139/10).
- Health-linked uses: "Agenda 2030: The Great Reset … Covid nineteen … Bill Ga[tes]" (13094/5);
  "make us eat bugs" (7405/4).

**outbreak_engineered.**

- Counts: 68 eps / 34 podcasts.
- Verdict: fine.
- Real phrasing: "McCullough … linking the virus's rapid spread to gain of function research"
  (11128/1, ad copy); "Ebola … It was manufactured" (71523/14); "He's really trying to scare the
  crap out of you" about H5N1 (205005/0).

**excess_deaths_cover_up.**

- Counts: 549 eps / 132 podcasts (broad: "excess deaths", "died suddenly", insurance data). The
  concealment-shaped subset is 58 segments.
- Verdict: fine.
- Real phrasing: "Indiana Life Insurance CEO says deaths are up 40%" (40064/1); "He commits the
  crime of noticing" (38820/0, Ed Dowd).

**assisted_dying_expansion.**

- Counts: 80 eps / 32 podcasts. Matt Walsh has 23.
- Verdict: fine. "euthanasia against just terminally ill is wrong, and actually, poor people even
  should be allowed" (649353/3); "This wonderful socialist system kept rejecting her … signing up
  for MAID" (42052/5).

**fentanyl_foreign_attack.**

- Counts: 51 eps / 20 podcasts.
- Verdict: fine. "Reverse opium war" (205723/12, 7664/6); "we'll weaken the West with fentanyl"
  (37374/1).
- The December 2025 WMD designation is reported news (330257/228, 206230/4).

### other_narratives

**unlisted_narrative.**

- Verdict: keep. Three recurring propositions found in this slice's areas should get their own
  labels (see ADDs).
- Watched but not proposed:
  - "GLP-1s are miracle drugs": 38 eps / 28 podcasts, mostly passing.
  - "Depression is a moral or spiritual problem, not a disease": folded into
    `mental_illness_not_real`.
  - "Statins are overused": a variant of `statins_harmful` that does not meet its core.

**Gap: social media and youth mental health.**

- Query: phones, social media, Instagram or TikTok near cause or drive plus mental-health
  crisis, anxiety, depression or suicide; *The Anxious Generation*; "great rewiring";
  "phone-based childhood".
- Counts: 469 eps / 137 podcasts (Charlie Kirk 29, Rogan 23, PBD 21, Modern Wisdom 14).
- Proposition voiced:
  - "Social media is to blame for causing a mental health crisis" (318387/2, Science Vs, which
    examines it).
  - "Instagram … causing massive depression amongst huge swaths of young girls" (12301/6).
  - "the most anxious, depressed generation in the history. Read … The Anxious Generation"
    (175438/6).
  - Oprah with Haidt (323154/5).
- Contested in the research literature, and the topic `cognition.digital_media_brain` exists
  without a narrative. Proposed ADD.

**Gap: mental illness is not real.**

- Query: depression, anxiety, mental illness or ADHD near "is not/isn't a disease, disorder,
  illness, real"; psychiatry is a fraud; the DSM is made up.
- Counts: 61 eps / 38 podcasts.
- Real phrasing:
  - "ADHD is not a real disease. It's a concept invented by the medical industry" (206905/1).
  - "he said depression isn't real" (12761/5, Andrew Tate).
  - "Anytime you tell someone who claims to have ADHD that it isn't real" (206410/4).
  - Rebuttal: "people on X that are like, oh, mental illness isn't real" (185633/1).
- Distinct from `chemical_imbalance_myth` (mechanism), `antidepressants_ineffective` (drugs)
  and `therapy_harms_children` (culture). Proposed ADD.

**Gap: pharma advertising controls the media.**

- Query: pharma or drug-company ads near news, media, networks, control, silence; New Zealand DTC
  ads.
- Counts: 164 eps / 52 podcasts (Rogan 31, PBD 16, Charlie Kirk 10).
- Real phrasing:
  - "the largest advertiser of the media is Big Pharma … This is why" (175095/0).
  - "the pharmaceutical companies got smart. They started buying advertising on CNN" (40281/3).
  - "yank all the pharma ads off of TV, which is what's controlling [the news]" (178198/3).
  - "We've never been able to influence media" (84749/6, Makary relaying a CEO).
- `fda_captured` covers agencies only, and `frame:media_distrust` plus `frame:big_pharma` carry
  only the rhetoric. Proposed ADD.

## Proposed edits

### Pharma family (from the first pass, unchanged)

CHANGE `narrative:pharma_creates_customers`:
| pharma_creates_customers | Medicine keeps people sick for profit | **Medicine or the drug industry keeps people sick, or treats symptoms instead of curing, so that patients stay lifelong customers.** Calling the system "sick care" or reactive takes this only when a profit or keep-them-sick motive is stated or plainly implied. "They want us sick" with a control or dependence motive and no profit is `narrative:depopulation_agenda`; with the food industry as actor it is `narrative:food_engineered_to_harm`. Vaccine-profit claims are `narrative:vaccines_for_profit`; lowered cholesterol thresholds also take `narrative:statins_harmful` only when statin harm or uselessness is stated. | they want us sick so they can sell drugs; incentive to keep us sick; customers for life; no money in cures | health_system |
Why: "sick care" (154 eps / 46 podcasts) is mostly a reactive-care critique (87972/6, 183006/0). The proposition is voiced as "they want us sick" (6660/0, 10589/5).

CHANGE `narrative:antidepressants_ineffective`:
| antidepressants_ineffective | Antidepressants don't work | **Antidepressants do not work or are no better than placebo.** Saying they do not work for everyone, or are overprescribed, is not this narrative. Claims about the serotonin theory are `narrative:chemical_imbalance_myth`. | barely better than placebo; placebo was almost as effective; antidepressants are placebos; Kirsch meta-analysis | mental |
Why: 100 eps / 37 podcasts. Frequent non-narrative uses: 185586/1, 175579/6.

CHANGE `narrative:chemical_imbalance_myth`:
| chemical_imbalance_myth | The chemical-imbalance theory is a myth | **The serotonin or "chemical imbalance" theory of depression is false or was a lie.** Describing someone's depression as "a chemical imbalance" without addressing the theory's validity is not this narrative in any stance. Whether the drugs work is `narrative:antidepressants_ineffective`; that depression is not a real illness at all is `narrative:mental_illness_not_real`. | chemical imbalance debunked; the chemical imbalance theory is not based in real science; biggest pharma scam is that depression is a chemical imbalance; serotonin review | mental |
Why: 128 eps / 46 podcasts state or debate the claim. Most of the 397 episodes containing the phrase are folk usage (39199/2, 88184/2).

CHANGE `narrative:ssris_cause_violence`:
| ssris_cause_violence | SSRIs cause violence or shootings | **Psychiatric drugs, especially SSRIs, cause violence, mass shootings or suicide.** Pointing out that a shooter took psychiatric drugs counts when it is offered as the explanation. | most mass shooters are on psychiatric drugs; the shooter was on Zoloft; psych meds; akathisia | mental |
Why: 153 eps / 51 podcasts (3956/6, 33656/18). "Akathisia" appears in only 13 eps.

CHANGE `narrative:therapy_harms_children`:
| therapy_harms_children | Therapy culture harms children | **Therapy culture, over-diagnosis and over-protection harm the resilience of children and young people.** | Bad Therapy; therapy culture; therapists pathologize normal childhood; over-diagnosing anxiety and ADHD in kids; coddled kids | mental |
Why: 138 eps / 27 podcasts for "bad therapy" or Shrier, and 43 / 26 for over-diagnosis. Covers Gen Z (175763/0, 33791/3).

CHANGE `narrative:tylenol_autism`:
| tylenol_autism | Acetaminophen in pregnancy causes autism | **Acetaminophen in pregnancy or infancy causes autism or ADHD.** Glutathione depletion is the usual mechanism offered. | Tylenol autism; Tylenol 'tism; Tylenol depletes glutathione; HHS announcement | pregnancy |
Why: 79 eps / 41 podcasts. The glutathione elaboration appears in 25 eps (33783/5).

CHANGE `narrative:fever_suppression_harmful`:
| fever_suppression_harmful | Fever reducers are harmful | **Fever reducers suppress immunity and prolong illness, so fevers should be left untreated.** "Fever is good" counts when it is offered as a reason not to treat the fever. | fevers are good for you; let the fever run; don't give your baby Tylenol for a fever; reducing the fever makes kids sicker longer | immune |
Why: 29 eps / 19 podcasts (185784/8, 178212/4).

CHANGE `narrative:birth_control_harms`:
| birth_control_harms | Hormonal birth control causes serious harm | **Hormonal birth control causes serious harm.** Typical harms named are infertility, depression, suicide, cancer, weight gain, personality or partner-choice change, lowered testosterone, libido loss and sexual pain. A labelled side effect (such as clot risk) stated as known prescribing information, with no wider harm claim, is a topic. | the pill made me depressed; birth control makes you fat; the pill changes who women are attracted to; birth control infertility | fertility |
Why: 38344/1 (weight, suicide), 5161/14 (partner choice), 190883/129 (clots as known fact).

CHANGE `narrative:glp1_dangers`:
| glp1_dangers | GLP-1 drugs are dangerous | **GLP-1 drugs cause serious harm or trap users for life.** Muscle wasting, stomach paralysis, blindness, suicide or cancer are the usual harms. Saying neutrally that people stay on them long term, advising protein or lifting to limit muscle loss, and the boxed-warning boilerplate in GLP-1 ads are not this narrative. | stomach paralysis; Ozempic eats your muscle; hooked on it for life; NAION | glp1 |
Why: 216 eps / 67 podcasts. Lay term: 33519/151. Non-narrative volume: 83880/1, 176587/3.

CHANGE `narrative:adhd_meds_harmful`:
| adhd_meds_harmful | ADHD drugs are harmful or overprescribed | **ADHD stimulants are harmful or overprescribed.** They are called speed, or said to be given to normal children or adults for convenience. Comparing Adderall to cocaine or meth in a story about recreational use or a joke is not this narrative unless the point is that prescribing it is harmful. That ADHD is not a real condition is `narrative:mental_illness_not_real`. | drugging boys; overmedicating children; giving hyper kids baby meth; Adderall is meth | neurodevelopment |
Why: ~635 broad hits are mostly comic (18771/5, 63118/16). Narrow: 59 eps / 30 podcasts.

CHANGE `narrative:medical_errors_leading_cause`:
| medical_errors_leading_cause | Medicine is a leading cause of death | **Medical care or prescription drugs are a leading cause of death** (e.g. the third or fourth). | third leading cause of death; medications are the fourth leading cause of death; iatrogenic deaths | health_system |
Why: 117 eps / 42 podcasts (186171/2, 3972/3).

CHANGE `narrative:fluoride_lowers_iq`:
| fluoride_lowers_iq | Fluoride lowers IQ / harms the brain | **Water fluoridation lowers IQ, harms brain development or is a neurotoxin.** Calcification of the pineal gland claimed as harm, with no control purpose, belongs here. | NTP report; fluoride neurotoxin; fluoride and brain development; fluoride calcifies the pineal gland | oral |
Why: 111 eps / 40 podcasts. Pineal claim without control: 181242/4.

CHANGE `narrative:fluoride_mind_control`:
| fluoride_mind_control | Fluoride is used for control | **Fluoride is added to pacify, dumb down or control people.** The pineal gland is often the mechanism, but pineal harm without a stated purpose is `narrative:fluoride_lowers_iq`. | fluoride to dumb kids down; makes citizens easier to control; Nazis used fluoride | oral |
Why: 46 eps / 21 podcasts (14582/0, 438716/0).

CHANGE `narrative:root_canals_amalgams_illness`:
| root_canals_amalgams_illness | Dental work causes systemic disease | **Root canals, amalgams, jawbone cavitations or metal implants cause chronic or systemic disease.** "Cavitation" also names joint popping and shockwave effects, which are not this narrative. | root canals cause cancer; mercury fillings; jawbone cavitations; your teeth are making you sick | oral |
Why: 223 eps / 53 podcasts. "Cavitation" is ambiguous (186205/2, 186018/0).

### Wellness family

CHANGE `narrative:germ_theory_denial`:
| germ_theory_denial | Germ theory is false / terrain theory | **Germs do not cause disease.** Viruses are said not to exist or not to be contagious, and the "terrain" is all that matters. Saying only that the body's terrain also matters, or naming terrain theory as an approach, is not this narrative. | germ theory is bogus; viruses don't exist; contagion is a myth; Pasteur recanted | infectious |
Why: 54 eps / 26 podcasts on denial phrasing. "Terrain theory" is mostly the soft version (181309/0, 190046/72); hard denial: 185982/2.

CHANGE `narrative:parasites_cause_disease`:
| parasites_cause_disease | Hidden parasites cause chronic disease | **Hidden parasites cause chronic disease in most people,** including cancer, so routine cleansing or deworming is needed. Advice that everyone should cleanse regularly, even without symptoms, counts. | most people don't know they have parasites; do a parasite cleanse once a year; parasite pandemic; parasites cause cancer | detox |
Why: 192 eps / 32 podcasts (192397/0, 78216/4, 48614/2, 178183).

CHANGE `narrative:stealth_infections_root`:
| stealth_infections_root | Hidden infections cause chronic disease | **Hidden chronic infections underlie most chronic disease.** EBV, mycoplasma, Lyme co-infections or other "stealth" pathogens are blamed; Lyme alone is `narrative:chronic_lyme_widespread`. A hidden infection as the cause of one named disease (EBV in Hashimoto's or MS) is not this narrative. | stealth infections; it's all about the Epstein-Barr virus; undiagnosed infections silently causing chronic disease; mycoplasma | chronic_complex |
Why: 570 eps / 63 podcasts (subject). Broad: 184196/2, 181883. Single-disease: 190832/70.

CHANGE `narrative:detox_needed`:
| detox_needed | The body needs help to detox | **The body accumulates toxins it cannot clear on its own.** "Toxic load", "toxic burden" or an overflowing toxic bucket that must be cleared invokes it; cleanses, detox products or protocols are the usual remedy, but none needs to be named. | toxic load; toxins build up; your body can't keep up with the toxins; cleanse your liver | detox |
Why: 889 eps / 111 podcasts. "Toxic load" is the dominant coined term (193087/7, 180711/516).

CHANGE `narrative:adrenal_fatigue_real`:
| adrenal_fatigue_real | Adrenal fatigue is a real condition | **Stress exhausts the adrenal glands, causing "adrenal fatigue".** The same concept renamed "HPA axis dysfunction" or "fried adrenals" counts. | adrenal fatigue; adrenal burnout; fried adrenals; HPA axis dysfunction (as the lay renaming) | endocrine |
Why: 257 eps / 43 podcasts. Practitioners rename it while keeping the concept (190909/134, 190889/67).

CHANGE `narrative:peptides_safe_miracle`:
| peptides_safe_miracle | Peptides are safe miracle healers | **Research peptides are safe and broadly healing** despite little human evidence. Either half invokes it, including the claim that they are safe to take indefinitely or are natural because the body makes them. One specific use claim (BPC-157 for a tendon) is a claim, not this narrative. | BPC-157 heals anything; the Wolverine stack; the most profound healing peptides on the planet; peptides are natural; safe to stay on forever | peptides |
Why: 918 eps / 78 podcasts (broad). Broad claims: 180897/462, 195282/3, 78334/6. Single-use claims: 190501/30.

CHANGE `narrative:energy_frequency_healing`:
| energy_frequency_healing | Energy or frequency devices heal | **Frequency, energy, quantum or scalar devices and modalities cure disease.** A device said to heal through combined "frequencies" takes this; add `narrative:grounding_heals` or `narrative:red_light_cure_all` only if their own healing claim is made. PEMF for its cleared uses (bone healing) is a topic. | Rife machine; frequency healing; quantum frequency healing; scalar energy | alt_medicine |
Why: 366 eps / 48 podcasts. "Quantum frequency healing" ad copy recurs (178180/4, 178197/2).

CHANGE `narrative:alzheimers_reversible`:
| alzheimers_reversible | Alzheimer's is reversible | **Alzheimer's disease can be reversed with lifestyle, dietary or metabolic protocols.** Bredesen's protocol and "type 3 diabetes" are the usual elaborations; calling Alzheimer's "type 3 diabetes" without a reversal or cure claim is not this narrative. | Bredesen protocol; ReCODE; MCT oil reverses Alzheimer's; reverse cognitive decline | dementia_ageing |
Why: 438 eps / 64 podcasts. "MCT oil reverses Alzheimer's" (195926/7, 14840/3). "Type 3 diabetes" without a reversal claim: 190596/30.

CHANGE `narrative:chemtrails`:
| chemtrails | Chemtrails | **Aircraft are spraying chemicals or metals on the population.** "Chemtrails" used only as a byword for conspiracy belief (in a list of theories or as a label for a person) does not invoke it; real geoengineering or cloud-seeding programmes discussed as policy are a topic. | chemtrails; they're spraying us; chemtrails hitting your food | environment |
Why: 492 eps / 91 podcasts, mostly list tokens or mockery (71667/8, 71255/19). Spraying or health claims are few (18696/1).

CHANGE `narrative:microplastics_catastrophe`:
| microplastics_catastrophe | Microplastics are causing serious disease | **Microplastics are causing serious disease** such as infertility, dementia, cancer or heart attacks. "Linked to" counts when a disease is named; finding microplastics in the brain, blood or placenta, without a disease claim, is a topic. | credit card of plastic a week; microplastics linked to infertility, heart disease, cancer; microplastic accumulation leads to Alzheimer's | environment |
Why: subject 1,256 eps / 108 podcasts, but only 17 eps make causal claims (192435/0, 25957/30). Presence talk dominates (20037/0, 182112/2). The "proven/established" wording matches almost nothing said.

CHANGE `narrative:household_toxins_poisoning`:
| household_toxins_poisoning | Everyday products are poisoning families | **Ordinary household and personal-care products are poisoning people.** Candles, fragrance, cookware, clothing, food packaging and plastic bottles are the usual culprits. A "non-toxic" product attribute alone is `frame:toxin_purity`; an ad that says the ordinary product harms you ("stop cooking with toxic cookware") invokes it. | toxic candles; your home is poisoning you; stop cooking with toxic cookware; plastic bottles leach poison | environment |
Why: 387 eps / 52 podcasts, about half ads (Caraway on The Toast, 91 eps). Real claims: 185907/5. Ad imperative: 175060/4.

CHANGE `narrative:tampon_toxins`:
| tampon_toxins | Period products contain dangerous toxins | **Tampons or pads contain toxins, such as heavy metals or dioxins, that cause harm.** Toxic shock syndrome, a bacterial risk, is a topic, not this narrative. | lead in tampons; dioxins in pads; chemicals in tampons and pads you want to avoid | womens |
Why: 139 eps / 55 podcasts, much of it TSS (23920/0, 21232/0). Proposition: 191020/26.

CHANGE `narrative:baby_food_metals_harm`:
| baby_food_metals_harm | Heavy metals in baby food damage children | **Heavy metals in baby food or infant formula damage children,** causing autism or brain damage. Reporting that baby food contains lead or arsenic, or that it should be tested, without a harm claim, is a topic. | toxic baby food causes autism; heavy metals in formula damage brains | food |
Why: about 33 relevant segments, many of them ads (Little Spoon or Cerebelly). Speakers state presence or regulation (174978/5, 15714/0), seldom harm.

REMOVE `narrative:vitamin_a_toxicity`
Why: essentially absent. One asserting episode (180821, Live Beyond the Norms) and one questioning
segment (190214/285). The other hits are a MeatEater person named Garrett Smith and polar-bear
history. `unlisted_narrative` covers the rare case.

REMOVE `narrative:heart_not_pump`
Why: about 3 episodes across 2 podcasts (189960, 70858/0, 190300/321). This is below any
recurrence bar, and `unlisted_narrative` covers it.

### Hormone family

CHANGE `narrative:testosterone_collapse`:
| testosterone_collapse | Testosterone collapse | **Men's testosterone has collapsed across generations.** Most men are said to need boosting or TRT. Normal age-related decline (andropause, women's testosterone in midlife) is not this narrative. | total collapse of testosterone levels; testosterone down 1% a year; men today have their grandfathers' T | mens |
Why: broad hits (983 eps) mix in age-related decline (175006/0, 179777/0). Proposition: 1139901/0, 7785/8, 78771/7.

CHANGE `narrative:semen_retention_benefits`:
| semen_retention_benefits | Semen retention gives special benefits | **Abstaining from ejaculation gives special benefits,** such as higher testosterone, energy, magnetism or better choices. Abstaining from pornography ("NoFap") with no benefit of retention claimed is not this narrative. | NoFap superpowers; holding your seed; retention boosts T; retaining semen for longevity | manosphere |
Why: 148 eps / 44 podcasts, much of it NoFap as porn abstinence (28542/5, 197055/1). Benefit claims: 86732/13, 200849/6, 185343/3.

CHANGE `narrative:endocrine_disruptors_feminizing`:
| endocrine_disruptors_feminizing | Chemicals are feminizing men or children | **Endocrine-disrupting chemicals are feminizing men or children.** Atrazine or plastics chemicals are blamed for changed sex characteristics, low testosterone, early puberty, genital malformation or transgender identity. Atrazine named only as one pesticide in a list is not this narrative. | gay frogs; atrazine turned male frogs female; chemicals turning kids trans; early puberty from plastics | environment |
Why: 1,214 eps / 133 podcasts (broad). Coined "gay frogs" (318940/23, 14753/6); 51857/0; 64192/4. List-only atrazine: 181100/9.

CHANGE `narrative:gender_care_harmful_youth`:
| gender_care_harmful_youth | Youth gender care is harmful and unsupported | **Gender medicine for minors is harmful and unsupported.** Puberty blockers or transition are called irreversible harms (mutilation, butchery, chemical castration) with no supporting evidence, dysphoria is said to resolve on its own, or social contagion is given as a reason not to treat. Claims about what trans identity is are `narrative:trans_identity_disorder`. Contested. | Cass Review; puberty blockers sterilize; mutilating children; chemical castration; most kids desist | gender |
Why: 1,294 eps / 100 podcasts. "Butchery" and "mutilation" are the dominant words (37403/1, 37402/3).

CHANGE `narrative:gender_care_lifesaving`:
| gender_care_lifesaving | Youth gender care is lifesaving | **Gender-affirming care for minors is lifesaving or safe.** It is said to prevent suicide and be well supported, withholding it to kill, or puberty blockers to be reversible. "Would you rather have a dead daughter or a living son?" states it, usually to rebut it. Contested. | affirm or suicide; dead daughter or living son; lifesaving care; puberty blockers are reversible | gender |
Why: 76 segments narrow, overwhelmingly rebutted via the "dead daughter or living son" line (8069/1, 39709/1, 7458/4, 11954/4).

CHANGE `narrative:trans_identity_disorder`:
| trans_identity_disorder | Transgender identity is a disorder or contagion | **Transgender identity is a disorder, delusion or social contagion rather than a real identity.** ROGD and "nobody is born in the wrong body" belong here. "Gender ideology" used as a political label, without a claim about what trans identity is, is `frame:political_partisan`, not this narrative. Claims about treating minors are `narrative:gender_care_harmful_youth`. Contested; code rebuttals too. | trans is a mental illness; ROGD; social contagion of trans identity; nobody is born in the wrong body | gender |
Why: "gender ideology" dominates ~1,700 matching episodes and is mostly culture-war politics (207055/0, 389035/1, 14792/15). The proposition: 12240/6, 38972/0.

CHANGE `narrative:abortion_infanticide`:
| abortion_infanticide | Abortion supporters endorse infanticide | **Abortion supporters endorse killing infants at or after birth.** Babies born alive after abortion are said to be left to die, or abortion is said to be legal or sought "up until the moment of birth". | born-alive babies left to die; post-birth abortion; abortion up until the moment of birth; through the ninth month | fertility |
Why: born-alive or post-birth phrasing is 142 eps / 23 podcasts, and up-to-birth phrasing is 170 / 18, on the same shows with the same "infanticide" rhetoric (39661/1, 40339/3, 206074/4).

### System family

CHANGE `narrative:sickest_generation`:
| sickest_generation | Children are the sickest generation | **Today's children are the sickest generation in history, with chronic illness unprecedented or at majority levels.** Food, chemicals, drugs or vaccines are blamed. A prevalence figure for one condition (obesity) without the general chronic-illness claim is a topic. `frame:maha_framing` needs the wider MAHA package; a passage can take both. | sickest generation; 40 percent of kids have a chronic disease; 60% of kids chronically ill | wellness |
Why: 59 eps / 24 podcasts on chronic-disease phrasing (84749/4, 37752/2). Obesity statistics alone are common and different (182354/0, 183382/2).

CHANGE `narrative:fda_captured`:
| fda_captured | Regulators are captured by industry | **Health agencies are controlled by the industries they oversee.** The FDA, CDC, NIH, USDA or their committees are said to be paid, staffed or owned by industry, which may be implied. Media capture by pharma advertising is `narrative:pharma_ads_control_media`. Usually co-occurs with `frame:government_distrust`. | FDA funded by pharma user fees; NIH research funded by pharma; regulators owned by the industry they regulate; revolving door | health_system |
Why: 116 segments narrow (182536/0, 7981/2, 205194/4). Bare "revolving door" and "regulatory capture" are mostly non-health.

CHANGE `narrative:doctors_paid_to_prescribe`:
| doctors_paid_to_prescribe | Doctors are paid to push vaccines or drugs | **Doctors are generally paid bonuses, perks or kickbacks to vaccinate or prescribe.** A specific documented scheme narrated as history (an opioid speaker-fee case) and public incentives for patients to get vaccinated are not this narrative. | pediatricians' bonuses for vaccination rates; doctors paid to vaccinate kids; doctors incentivized to prescribe | health_system |
Why: ~111 eps / 47 podcasts (7922/3, 63035/10). Noise: 1139332/0 (patient incentives), 175114/7 (documented opioid kickbacks).

CHANGE `narrative:depopulation_agenda`:
| depopulation_agenda | Elite depopulation or control agenda | **Elites, globalists or governments are deliberately reducing the population or controlling people through health means.** Vaccines, food, medicine, chemicals or pandemics are the means; a control plan with no depopulation claim counts when a health means is named ("make us eat bugs", "they want us sick and dependent"). The Great Reset as an economic or political plan with no health means is not this narrative. | depopulation; Gates wants fewer people; you'll eat bugs and own nothing; they want us sick, weak and dependent | policy |
Why: 1,430 matching segments, many without health content (11916/5, 39939/3) or meaning literal depopulation (175785/3). Health-linked uses: 13094/5, 7405/4, 195939/0.

### ADDs

ADD `narrative:social_media_youth_mental_health` under `system_narratives`:
| social_media_youth_mental_health | Phones and social media caused the youth mental-health crisis | **Smartphones and social media are the main cause of rising anxiety, depression, self-harm or suicide among young people.** The Anxious Generation's "great rewiring" and a phone-based childhood are the usual elaborations. Screen-time effects on attention or sleep with no mental-health crisis claim are a topic (`cognition.digital_media_brain`). Contested. | The Anxious Generation; social media is causing the teen mental health crisis; Instagram causes depression in girls; phone-based childhood | mental |
Why: 469 eps / 137 podcasts. Examples: "Social media is to blame for causing a mental health crisis" (318387/2, Science Vs testing it); "Instagram … causing massive depression amongst … young girls" (12301/6).

ADD `narrative:mental_illness_not_real` under `pharma_narratives`:
| mental_illness_not_real | Common mental illnesses are not real | **Depression, anxiety, ADHD or other common psychiatric diagnoses are not real illnesses** but inventions of the medical industry, moral or spiritual failings, or ordinary life. The serotonin theory alone is `narrative:chemical_imbalance_myth`; whether the drugs work is `narrative:antidepressants_ineffective`. | depression isn't real; ADHD is not a real disease; a concept invented by the medical industry; mental illness isn't real | mental |
Why: 61 eps / 38 podcasts (206905/1, 12761/5, 206410/4). A rebuttal from the other side: 185633/1.

ADD `narrative:pharma_ads_control_media` under `system_narratives`:
| pharma_ads_control_media | Pharma advertising controls the media | **Drug-company advertising money controls or silences news coverage of health.** The United States and New Zealand being the only countries that allow drug ads is the usual premise; that fact alone, without the control claim, is a topic. | pharma is the largest advertiser so the news won't report it; pharma ads control the networks; yank pharma ads off TV | health_system |
Why: 164 eps / 52 podcasts (175095/0, 40281/3, 178198/3, 84749/6). This is distinct from `fda_captured` (agencies), and frames carry only the rhetoric.

## Codebook and prompt notes

1. **5.2, a "folk use is not a stance" rule.** When a speaker uses the opposite of a narrative's
   proposition as an everyday explanation ("he has a chemical imbalance"), the narrative is not
   invoked. Code `rebutted` only when the proposition is itself present and argued against.
   Evidence: 397 eps say "chemical imbalance", mostly folk usage.
2. **5.2, slogans that do not carry the proposition.** The coined-term rule invites
   over-application. List explicit counter-examples:
   - "sick care" (reactive care; 154 eps).
   - "gender ideology" (political label; ~1,700 eps).
   - "the Great Reset" (economic or political).
   - "terrain theory" (soft "terrain matters").
   - "type 3 diabetes" (mechanism, not reversal).
   - "NoFap" (porn abstinence).
   - "chemtrails" or "flat earth" used as bywords for conspiracy belief.

   The test is whether the term's ordinary use in the corpus commits the speaker to the
   proposition. "Turbo cancer" does; these mostly do not.
3. **5.2, actor and motive decide among "they want us sick" narratives.**
   - Profit with pharma or medicine as actor: `pharma_creates_customers`.
   - Food industry: `food_engineered_to_harm`.
   - Elites or government with a control motive: `depopulation_agenda`.
   - Unspecified "they": a distrust frame only, with `frame:conspiracy_cover_up` if coordination
     is alleged.
   - Examples: 6660/0, 10589/5, 195939/0, 64192/4 (atrazine "to make them have low test" also
     takes `endocrine_disruptors_feminizing`).
4. **5.2, side effects and presence findings versus harm narratives.**
   - A documented side effect stated as prescribing information, or discussed as something to
     manage, does not invoke a harm narrative (190883/129, 176587/3).
   - A finding that a contaminant is present (microplastics in the brain, lead in baby food,
     PFAS in blood) does not invoke a disease narrative unless a disease is attributed to it
     (20037/0, 174978/5).
5. **5.2(a) and the imperative rule in ads, a tie-breaker.**
   - Wellness ads dominate several narratives' raw volume: parasite cleanse, mold-free coffee,
     non-toxic cookware and candles, EMF blockers, red light, grounding mats, quantum devices,
     baby food.
   - Suggested rule:
     - A "non-toxic", "tested for X" or "free of X" attribute: frame only.
     - Copy that says the ordinary product or condition harms you ("stop cooking with toxic
       cookware", 175060/4; "parasites … that sabotage your energy and digestion", 162533/2;
       "a parasite cleanse at least once a year as preventive measure", 48614/2): invokes the
       narrative, `asserted_or_endorsed`.
   - Pharma ad safety boilerplate ("serious side effects and boxed warning", 83880/1) invokes no
     narrative.
6. **3 and 5.2, recreational drug comedy.** Comparing prescription stimulants to street drugs in
   anecdotes or jokes invokes no narrative unless prescribing practice is the point (18771/5,
   63118/16).
7. **6, parody voicing.** A speaker voicing a proposition in obvious parody to mock it (the Daily
   Wire promo "gender-affirming care is healthcare … suicide prevention", 206490/7, 388506/5) is
   `rebutted`, not `asserted_or_endorsed`. The existing sarcasm sentence in 5.2 could cite this
   case.
8. **5.2, single-disease versus root-of-all-disease.** `inflammation_root_cause` already says a
   single disease is not enough. Apply the same sentence to `stealth_infections_root` and
   `metabolic_dysfunction_root` (190832/70). `leaky_gut_root_cause` deliberately allows a single
   disease such as autoimmunity, so say so to avoid inconsistent coding.
9. **Search notes for future passes.**
   - Use `\bcandida\b` ("candidate").
   - Use `\bearthing\b` ("unearthing").
   - "cleanse" matches scripture podcasts.
   - "kirsch" matches Steve Kirsch.
   - `\bwhi\b` is ASR noise.
   - "pause button" pollutes "blockers are a pause button".
   - "count ?down" catches sports.
   - "odgers" matches Rodgers and Dodgers.
   - "formula" is mostly non-infant.
   - "revolving door" and "regulatory capture" are mostly non-health.
   - "bad energy" is reality TV.
   - "Garrett Smith" is also a MeatEater regular.
   - Recurring ad reads inflate counts by tens to hundreds of episodes: The Daily (Title X),
     Casefile (ShipStation), Jockers (turmeric), Habits and Hustle (red light), The Toast
     (Caraway), SuperLife (multi-modality pad).
