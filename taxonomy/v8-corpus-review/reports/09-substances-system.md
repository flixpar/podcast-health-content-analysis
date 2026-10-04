# Substances, medications, health system and policy: corpus review

Slice: `topic:drugs_addiction`, `topic:psychoactives`, `topic:alcohol`, `topic:stimulants`,
`topic:medications`, `topic:health_system`, `topic:policy` and their subtopics.

Method: about 75 `cq.py count` and `sample` queries over the 145.6k-episode corpus, run one at a time
(through `/mnt/data2/podcast-data/corpus-text/cq.py`; see the note at the end). I read about
200 sampled passages and checked the benchmark-v2 gold (`benchmark/v2/gold.jsonl`: 305 gold detections in
this slice) to see how the reference annotators drew the lines. Counts are given as segments / episodes /
podcasts. Keyword counts are upper bounds: sampling shows how much of each is noise.

## Summary

- **The recreational-use line is the main problem in this slice, and the codebook does not draw it.**
  Alcohol words (`alcohol|drunk|booze|hangover|hungover`) appear in 40,376 episodes across 538 podcasts,
  cannabis words in 28,293 episodes, `cocaine|meth…` in 10,705, `cigarettes|tobacco…` in 16,536 and coffee
  nearly everywhere. The top podcasts are comedy and reality-TV recap shows (Watch What Crappens, Pardon My
  Take, KILL TONY, Theo Von). In comedy samples about 1 in 10 "drunk/hungover" hits and 2 in 10
  cocaine/edibles hits say anything about the substance (an effect, harm, pattern or quitting). The rest
  are scenery ("get drunk and see tits", "a drunk text", "a lot of pool parties, a lot of cocaine") or
  figurative. The v2 gold codes such scenery as `passing` (`alcohol.drinking_culture` for "Our whole office
  went out for drinks, and I got totally plastered"; three labels for "you're smoking cigarettes, you're
  drinking scotch"). Applied to the whole corpus, that would put a substances label on more than a third
  of all episodes, almost all of it noise. **Recommendation:** a section 3 rule, parallel to the violence
  rule: substance use counts as health content when an effect, risk, amount or pattern, dependence,
  quitting, policy or a product sold for its effect is stated. A one-off intoxication told as part of a
  story does not count.
- **Figurative and lookalike vocabulary is common.** Of 12 random "addicted/addiction" hits, 4 were
  figurative ("an addiction that this party has", "my addiction to popcorn bowls"). "Alcoholic" is often
  the adjective ("an alcoholic drink") or a simile ("like some alcoholic stepfather"). "Non-alcoholic"
  occurs mostly as non-alcoholic fatty liver disease (156 episodes, all in health shows), which is not
  `alcohol.alternatives`. "Cartels" is mostly crime, immigration or film talk (0 of 10 samples were about
  drugs as health). Most "Celsius" hits are temperatures, and "Molly" is usually a person's name
  (Radiolab and Fresh Air credits).
- **Drug crime in true crime and news needs the same treatment as violence.** Drug-crime words ("drug
  dealer", "drug deal gone wrong", "drug trafficking", "cartel") appear in 7,538 episodes. The gold labels
  "selling meth out of the bar" as `drug_policy`. Proposed rule: a drug crime named only as an event is
  not health content; `drug_policy` applies when laws, enforcement or supply are discussed as an issue, or
  when the crime is tied to use, overdose or addiction.
- **Generic drug talk with no named drug is frequent and has no stated home.** "Doing drugs", "on drugs",
  "drug use", "drug problem", "hard drugs" and "substance abuse" appear in 11,562 episodes across 384
  podcasts. The bare parent `topic:drugs_addiction` is the right code. Say so in the codebook's
  "General talk" paragraph; no new subtopic is needed.
- **Boundary fixes, each backed by real collisions:** "microdosing" now often means GLP-1s (154 episodes
  across 36 podcasts, against 403 episodes / 95 podcasts for psychedelics; one Thyroid Fixer episode is
  titled "Microdosing GLP's"). "Smoking" in comedy is very often weed (5,894 episodes say "smoke weed /
  a joint / a blunt"). Tobacco-industry and tobacco-regulation talk (788 episodes) has no stated home.
  Drink-driving (3,657 episodes) and alcohol policy (drinking age, warning labels) have none either.
  Sobriety and recovery language overlaps between `alcohol.alcohol_use_disorder` and
  `drugs_addiction.addiction_recovery` (AA is listed under the drugs subtopic).
- **The ad test is silent on substance products, and the volumes are large.** Examples: a McDonald's
  "Red Bull Dragonberry Energizer" ad (2,087 episodes, 32 podcasts, with no effect stated), Lucy
  nicotine-pouch reads (177 episodes, 125 of them on Pardon My Take), hemp-THC gummy reads and
  hangover-pill reads in comedy shows. Proposed: nicotine, cannabis/hemp-THC and kratom products always
  pass as drugs. Alcohol, coffee and energy drinks pass only when an effect is stated, and a product name
  ("Energizer") is not one. Prescription-drug ads are huge too: the Tremfya read alone is in 2,838 episodes
  across 35 podcasts, mostly Ringer sports and film shows. They will dominate `medications.other_drugs`
  counts. That is correct coding, but researchers should be told.
- **`health_system` and `policy` subtopics are all findable and mostly well defined.** One gap and one
  boundary:
  - **Gap:** health-care fraud (Medicare, Medicaid and hospice fraud; 270 episodes, 58 podcasts) is a
    recurring 2025–26 news subject with no named home. Add it to `health_system.costs_insurance`.
  - **Boundary:** 6 of 10 sampled RFK Jr. hits are about his 2024 candidacy or cabinet politics, with no
    health subject. `policy.hhs_leadership` needs a line saying that a health figure's name or campaign is
    not health content by itself.
- **FDA boilerplate in ads is not about regulators.** Telehealth and supplement reads carry "FDA-approved
  GLP-1 medications" and "compounded drug products, which the FDA does not approve" (the disclaimer
  phrases alone are in 1,025 episodes). They should not trigger `health_system.regulators`.
- **No merges or removals.** Every subtopic in the slice clears the frequency bar. The rarest are
  `psychoactives.microdosing` (about 400 psychedelic episodes once GLP-1 and other microdosing are
  removed), `drugs_addiction.harm_reduction` (706 episodes, 134 podcasts) and
  `policy.regulation_chemicals_food_drugs` (its own phrases: 225 episodes, 56 podcasts). All three are
  distinct and worth counting.

## Label-by-label findings

### Where the health-content line falls in comedy (cross-cutting)

Samples restricted to KILL TONY, Pardon My Take, Bad Friends, Theo Von, Flagrant, Are You Garbage and
Matt and Shane.

- `\b(drunk|hungover|wasted|blackout|blacked out)\b`: 6,838 segments in those shows. Of 10 samples, 1 was
  health content (a hangover-pill ad: "see if you could drink and not get hungover with these pills",
  ep 322108 seg 8). One was a characterization ("This guy's just a dope and he's drunk", 77332/2). The rest
  were scenery or figurative: "get drunk and see tits" (194812/7), "late night drunk text to your ex"
  (128662/8), "allegations of looking drunk" (128292/0), "He gets like really, really drunk, and he
  falls asleep… everyone's super hungover" (52587/5), and "no one's drunk anymore" about crypto (321867/0).
- `\b(cocaine|coke|shrooms|edibles?|molly|acid|adderall)\b`: 5,017 segments. Of 10 samples, 2 were health:
  - "my limbs were starting to go numb… I think I was about to have a heart attack, so I just stopped
    doing cocaine" (194691/9);
  - "Jake did ask if cocaine makes you pee a lot" (128498/14).

  The rest were scenery ("A lot of pool parties, a lot of cocaine", 77492/2), jokes ("buried with an
  eight ball… that cocaine baby", 77481/7), Coca-Cola sponsorships (51828/4), a football play called
  "cocaine" (128748/7) and a person named Molly (24318/10).
- Reality-TV recaps are a distinct case. The cast are real people, so their DUIs, rehab stints and sobriety
  are real health facts, not fiction: "found guilty of drunk driving… she went to a recovery center"
  (90996/4); "she openly admitted that she's on pills still… the doctors at the rehab center gave her
  pills" (96619/2). These should be `passing`, which the codebook's fiction exclusion does not make clear.
- Coffee in comedy and recap shows: of 10 samples, 0 were health ("doing the normal walk down the street
  with the coffee", 96260/6). Cigarettes and smoking in comedy and true crime: about 2 of 10 were health,
  and several were weed ("I smoke weed; I'm good at smoking weed", 77210/3).

Verdict: a codebook rule is needed (see the notes below). The gold set already contradicts the rule I
propose in a few items (c178291w0010 "got totally plastered", c95062w0004, c3505w0007 "our water bottle
of a little of every alcohol my father had"). Re-adjudicate those once the rule is decided.

### `drugs_addiction`

| label | query | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| `opioids_fentanyl` | `fentanyl\|heroin\|oxycontin\|oxycodone\|opioids?\|opiates?\|percocet\|vicodin\|xylazine\|hydrocodone` | 17,348 / 11,994 / 350 | fine; add "pain pills", "percs" to examples |
| `stimulants_illicit` | `cocaine\|methamphetamine\|crack cocaine\|crystal meth` | 15,104 / 10,705 / 330 | examples change (non-prescribed Adderall has no home) |
| `addiction_recovery` | `addict(ed\|ion)?\|rehab\|relapse\|12 steps\|AA\|NA\|suboxone\|methadone\|in recovery\|sober(ity)?` | 58,728 / 34,443 / 504 (inflated by figurative use and "Money Rehab") | needs definition change (alcohol overlap, figurative use) |
| `harm_reduction` | `narcan\|naloxone\|needle exchange\|safe supply\|safe injection\|test strips\|harm reduction` | 894 / 706 / 134 | fine; rarer but clearly important |
| `drug_policy` | `overdose deaths\|overdoses\|decriminali[sz]\|war on drugs\|measure 110\|cartels?\|drug (policy\|laws\|trafficking\|dealers?\|war)\|precursor` | 15,305 / 10,241 / 346 | needs definition change; "cartels" is a misleading example |
| (bare parent) | `doing drugs\|did drugs\|on drugs\|drug use\|drug habit\|drug problem\|hard drugs\|recreational drugs\|party drugs\|substance (ab)use` | 15,082 / 11,562 / 384 | codebook note: generic drug talk → bare `topic:drugs_addiction` |
| (overdose) | `overdosed\|overdoses?\|overdosing` | 6,009 / 4,759 / 282 | covered by `drug_policy` plus `opioids_fentanyl` |
| (drug crime) | `drug (dealers?\|deals?\|busts?\|money\|trafficking\|smuggling\|cartels?\|lords?\|charges)` | 10,172 / 7,538 / 335 | codebook rule: not health by itself |

Notes:

- **Figurative "addicted".** Of 12 random hits, 4 were figurative: "It's an addiction that this party has"
  (10945/4), "my addiction to popcorn bowls on high shelves" (91961/4), "she's addicted to like just knowing
  things about people" (94525/4), "Becca's shoe addiction" (320061/3). One was a behavioral addiction
  ("their addiction to it", social media, 19566/1). The rest were real: "addicted to heroin" (3257/94),
  "the ones who are already addicted are turning to the street drugs" (186291/2), "addicted to nicotine
  gum" (77329/10).
- **Alcohol versus addiction.** `addiction_recovery` says "from any substance" and lists AA, while
  `alcohol.alcohol_use_disorder` covers "alcoholism and its treatment", so an AA meeting can go to either.
  The gold coded "Al-Anon meetings… codependency meetings" (c77624w0013) as `addiction_recovery`. Most
  sobriety talk in recap shows is about drinking: "Another person falls into sobriety on Bravo" (91414/2);
  "I haven't drank in a few weeks… four sobriety moments" (90794/3). Proposed: alcohol-only dependence →
  `alcohol.alcohol_use_disorder`; drugs or several substances → `addiction_recovery`.
- **Prescription-drug misuse.** Pattern `xanax|benzos|percs|percocet|codeine|pill popping` gives
  3,525 / 2,824 / 222. Most hits concern benzodiazepines, which already live in `mental.psychiatric_drugs`
  (including withdrawal): "I'd run out of Xanax, which I've been taking for like six months… I had like a
  psychotic breakdown" (16231/6); "your cousin is addicted to Xanax" (5545/3); "I'm selling Xanax bars"
  (a joke, 194820/4). Non-prescribed Adderall ("now they're all on Adderall", 663/6) is the gap: the only
  home is `neurodevelopment.adhd`, which would miscount it as ADHD content. Add it to
  `stimulants_illicit`.
- **Drug crime.** True-crime samples were all crime-plot mentions: "a drug deal gone wrong" (9510/115);
  "she owed an out of state drug dealer three hundred bucks" (23822/3); "playing drug dealer" (30776/6).
  A cartel sample (7,051 segments) had 0 of 10 health passages: "a cartel member is not going to hit that
  front door" (42172/11); "Mexican drug cartels dictate and control our immigration policy" (38479/1).
  The gold also coded 2025–26 boat-strike talk ("drone strikes and airstrikes against old drug boats",
  c154859w0023) as `drug_policy` substantive. That is defensible only when supply or overdose harms are
  the stated rationale.
- **Drug testing.** `drug (tests?|tested|testing|screen)` gives 1,802 segments. Sports anti-doping
  ("USADA… randomly drug test fighters", 21080/6) belongs to `peds`. Employment and probation testing
  ("hair follicle drug test", 201743/6) is marginal; treat it as `drug_policy` `passing` at most.

### `psychoactives`

| label | query | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| `cannabis` | `weed\|marijuana\|cannabis\|thc\|cbd\|edibles?\|stoned\|blunts?\|delta-8\|dispensar(y\|ies)\|hemp` | 44,750 / 28,293 / 494 (top: Watch What Crappens, 3,015 eps) | examples and boundary change |
| `psychedelic_therapy` | `psilocybin\|psychedelics?\|magic mushrooms\|shrooms\|lsd\|acid trip\|ayahuasca\|ibogaine\|dmt\|5-meo\|mescaline\|peyote` | 12,964 / 6,799 / 271 | fine; add recreational vocabulary |
| (therapy-specific) | `psychedelic-assisted\|psilocybin therapy\|mdma-assisted\|psychedelic therapy\|ibogaine treatment` | 494 / 310 / 65 | therapy is a small share; a split is not needed |
| `ketamine` | `ketamine\|spravato\|esketamine\|k-hole` | 2,116 / 1,513 / 163 | fine (includes Musk-ketamine news, e.g. IHIP News 119 eps) |
| `microdosing` | `micro-?dos` | 2,012 / 1,380 / 142; with a psychedelic within 80 chars: 488 / 403 / 95; with a GLP-1 term: 206 / 154 / 36 | needs a boundary |
| `novel_substances` | `kratom\|7-oh\|7-hydroxy\|tianeptine\|gas station heroin` | 740 / 548 / 96 | fine; add GHB and "gas-station heroin" |
| (MDMA) | `molly\|ecstasy\|mdma` | 12,343 / 8,377 / 292, mostly the name Molly | fold MDMA, ecstasy and molly into `psychedelic_therapy` examples |

Notes:

- Microdosing collisions:
  - GLP-1s: "We're microdosing. We're not hitting you with a sledgehammer" (GLP-1, 190581/64);
    "a lot of clinics saying they're microdosing" (semaglutide, Mind Pump 195746/4); retatrutide
    "microdosing level" (78235/10).
  - THC: "a microdose of THC" in a CBD/CBN gummy ad (87499/0).
  - Exercise: "They microdose it" about strength training (195703/2).
  - Psychedelics, the actual subject: "I've been microdosing… My mental health. Yeah, I'm genuinely happy"
    (Bad Friends 161116/2).

  `glp1.new_offlabel_uses` already lists "microdosing GLP-1", so a boundary sentence in `microdosing` is
  enough.
- Kratom and 7-OH are real recurring subjects, with misinformation relevance:
  - "kratom… It is an opiate. There's no doubt about it" (Rogan 71000/1);
  - "it says right here, kratom may be addictive… And they're telling people it's not addictive"
    (Shawn Ryan 5957/12, an episode titled about 7-OH sold at gas stations);
  - "Isn't kratom fake weed?" (90562/5).

  `novel` with nitrous, poppers and kava was noisy ("whippet" the dog breed; kava belongs to
  `supplements.sleep_mood_supplements`).
- Cannabis vocabulary in real use: "weed", "smoke a joint", "edibles", "gummies", "stoned", "THC",
  "hemp-derived THC", "CBN". Smoking weed (5,894 eps) must not be coded `stimulants.smoking`.
  THC beverages are rare (90 eps, mostly MeidasTouch sponsor copy).

### `alcohol`

| label | query | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| (all alcohol) | `alcohol\|drunk\|booze\|hangover\|hungover` | 70,852 / 40,376 / 538 | see the comedy line above |
| `health_effects` | gold: 13 detections; fits real usage ("no amount of alcohol is good for you", c177172w0006; "sick quitters", c178291w0010) | | fine |
| `drinking_culture` | `dry january\|sober-curious\|binge drink\|quit/stopped drinking\|gave up drinking\|don't drink anymore` | 4,439 / 3,742 / 229 | needs definition change (drink-driving, alcohol policy, scenery) |
| `alcohol_use_disorder` | `alcoholics?\|alcoholism\|alcohol use disorder\|alcohol abuse\|alcohol withdrawal\|delirium tremens\|functioning alcoholic` | 13,055 / 10,092 / 322 | examples and boundary change |
| `alternatives` | `non-?alcoholic\|mocktails?\|athletic brewing\|thc drinks\|hemp-derived\|alcohol-free` | 1,424 / 1,191 / 154; includes NAFLD 183 / 156 / 32 | boundary change |
| (drink-driving) | `drunk driv\|dui\|dwi\|driving drunk\|drinking and driving` | 4,330 / 3,657 / 225 | no home; add to `drinking_culture` |
| (alcohol policy) | `drinking age\|alcohol tax\|alcohol warning label\|alcohol laws/guidelines` | 473 / 445 / 122 | no home; add to `drinking_culture` |

Notes:

- `alcohol_use_disorder` samples, 10 hits:
  - real and person-level, 3: "my father was an alcoholic and drug abuser" (1136468/1); "he was a
    functional alcoholic" (205821/2); "a dry drunk" (74458/4, from the drunk/hangover sample);
  - societal list items, 2: "Alcoholism, drug usage, mental health issues are accelerated dramatically"
    (41123/4);
  - non-health, 5: "an alcoholic drink" (156833/4), "like some fucking alcoholic stepfather" (197083/2),
    "non-alcoholic drinks", and fiction-character descriptions (Bond, 197686/5).
- `alternatives`: 4 of 10 samples were real (mocktails, Athletic Brewing, non-alcoholic retailers, "the
  growing movement for non-alcoholic drinking", 204013/2). Two were non-alcoholic fatty liver disease
  (192475/1, 192977/1). The rest were frozen-fruit-bar ad copy suggesting "a sexy mocktail" (fails the ad
  test).
- Drink-driving: real public-health framing exists ("we addressed the culture, especially around drunk
  driving", Something You Should Know 86267/4). Most hits are legal events ("four years of you getting
  divorced and a DUI", 92068/4; Hegseth "DUI hire", 29286/1), which are not health content by the crime
  rule.
- Alcohol policy is mostly drinking-age chatter (comedy) plus some 2025 cancer-warning-label news. Small
  but real. Fold it into `drinking_culture` rather than adding a subtopic.
- The v2 gold coded 12 `drinking_culture` and 13 `health_effects` detections; about half of the
  `drinking_culture` ones are scenery or passing.

### `stimulants`

| label | query | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| `smoking` | `cigarettes?\|cigs\|tobacco\|chain smok\|quit smoking` | 23,726 / 16,536 / 436 | definition change (weed boundary, tobacco industry and regulation) |
| (tobacco industry / regulation) | `big tobacco\|tobacco compan(y\|ies)\|philip morris\|menthol ban\|flavored vape ban\|vape ban` | 970 / 788 / 127 | no home; add to `smoking` |
| `vaping` | `vapes?\|vaping\|juul\|e-cigs?\|elf bar` | 3,309 / 2,664 / 191 | fine |
| `nicotine_products` | `zyn\|nicotine pouch\|snus\|nicotine` | 3,206 / 2,395 / 175 | examples change (smokeless tobacco, Lucy) |
| `caffeine` | `caffeine\|caffeinated\|decaf\|matcha` | 9,721 / 7,381 / 252 (coffee itself is far more) | definition change (inclusion threshold) |
| `energy_drinks` | `energy drinks?\|red bull\|monster energy\|pre-?workout\|bang\|ghost energy\|alani nu\|c4` | 8,183 / 6,372 / 218 (626 eps Pardon My Take) | fine; ad rule needed |

Notes:

- Nicotine, real usage: "I used to dip… nicotine was just part of the day" (Shawn Ryan
  44378/8, inside a nicotine-pouch read); "nicotine… is protective against Parkinson's and Alzheimer's… So I chew Nicorette all day"
  (Huberman 24239/11). The latter needs a co-label with `neuro` (rule 1). Smokeless tobacco (dip, chew,
  snuff) has no explicit home and belongs in `nicotine_products`.
- Nicotine ads: Lucy is "the official nicotine pouch partner of Barstool Sports" (19383/4, 27240/7).
  Lucy-specific reads: 177 episodes. "Quit with Jones" (c89759w0004) is in the gold as
  `nicotine_products` + `vaping` + `addiction_recovery`, which is reasonable.
- Smoking samples: "You're still smoking cigarettes? Uh, I'm vaping a lot more… How much cigarettes you
  smoke a day? Half pack" (17397/12, health, a pattern). "We were at the cigar lounge" (204967/7) and "lit a
  cigarette, and blew smoke in her dead grandmother's face" (29640/4) are scenery.
- Caffeine: the gold treats "I've already made three cups of coffee and it's not even helping" as
  `passing` (a functional effect). That is fine, but coffee as an errand or setting (0 of 10 comedy
  samples were health) must be excluded under the existing food-as-taste exclusion. Say so in the
  definition.
- Energy drinks: the "Red Bull Dragonberry Energizer… now at McDonald's" ad is in 2,087 episodes across
  32 podcasts (Meditation for Anxiety 509, Hidden Brain 193). It states no effect. Whether it is health
  content decides about 2k episodes; see the ad note below.

### `medications`

| label | query | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| `pain_relievers` | `tylenol\|acetaminophen\|paracetamol\|ibuprofen\|advil\|motrin\|aspirin\|aleve\|naproxen\|nsaids?\|excedrin` | 4,572 / 3,799 / 229 | fine |
| `overmedication` | `overmedicat\|polypharmacy\|over-?prescrib\|pills for everything\|black-box warning\|drug recalls?` | 781 / 689 / 131 (plus generic "side effects" talk) | fine; gold shows it is used for "medication for everything" rhetoric |
| `repurposed_offlabel` | `ivermectin\|low-dose naltrexone\|ldn\|metformin\|methylene blue\|dmso\|off-label` | 4,249 / 2,313 / 141 (Charlie Kirk 303 eps: ivermectin) | fine |
| `other_drugs` | `blood thinners\|eliquis\|warfarin\|prednisone\|ppis\|accutane\|biologics\|humira\|dupixent\|cortisone\|muscle relaxers\|ambien\|sleeping pills` | 4,710 / 3,573 / 223 | fine; DTC drug ads dominate |
| (DTC drug ads) | `tremfya\|trumphia\|tremphia` | 3,655 / 2,838 / 35 | note for researchers |

Notes:

- DTC prescription ads are frequent outside health shows. Of 8 "ask your doctor / is a prescription
  medicine" samples, 5 were Tremfya ("Tremfya is a prescription medicine used to treat adults with
  moderately to severely active Crohn's disease", 322819/1). The others were Cologuard (→
  `cancer.screening_diagnosis`) and Beyfortus (a monoclonal antibody against RSV, 30489/4). The gold already
  codes Tremfya → `other_drugs` advertisement. Under the ad rule the condition is only the purpose, so no
  `gut` label is added. That is consistent, but it means ad volume will dominate `other_drugs`, so
  analysts should split by `relevance`. Beyfortus has no clear home (not a vaccine, not a listed drug). Add
  "preventive antibodies (nirsevimab)" to `other_drugs` examples, plus the infection's subtopic.
- ASR variants worth listing: "Trumphia"/"Tremphia" (Tremfya), "AstaPro" (Astepro), "adderol"
  (Adderall), "methyl and blue" (methylene blue, c190168w0014).

### `health_system`

| label | query | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| `costs_insurance` | `health insurance\|insurance compan(y\|ies)\|medicaid\|medicare\|obamacare\|aca\|medical debt\|medical bills\|drug prices\|unitedhealth\|prior authorization\|single-payer\|universal health care` | 38,719 / 24,906 / 431 (noisy: car and life insurance ads, e.g. NJM "insuranoia", 162694/2) | definition change (fraud) |
| (Medicaid cuts / ACA subsidies) | `medicaid (cuts\|work requirements\|expansion)\|cuts to medicaid\|aca subsidies` | 1,015 / 815 / 44 | covered by `costs_insurance` plus `policy.partisan_politics` |
| (health-care fraud) | `medicare fraud\|medicaid fraud\|health care fraud\|hospice fraud\|defrauding medicare/medicaid` | 324 / 270 / 58 | gap; fold into `costs_insurance` |
| `pharma_industry` | `big pharma\|pharma(ceutical) compan(y\|ies)/industry/lobby\|drug compan(y\|ies)\|purdue pharma\|sacklers?` | 8,490 / 5,910 / 237 | fine |
| `doctors_profession` | `medical school\|med school\|residency\|doctor burnout\|second opinion\|doctors don't learn` | 9,231 / 6,596 / 302 | fine |
| `hospitals_access` | `hospital closures\|wait times\|rural hospitals\|primary care\|urgent care` | 4,764 / 4,073 / 214 (some ad noise) | fine |
| `regulators` | `fda\|cdc\|nih\|world health organization` | 21,859 / 14,474 / 323 (Armchair Expert 945 eps, mostly ad copy) | fine; codebook note on ad boilerplate |
| `research_system` | `peer review\|retracted\|retraction\|preprints\|clinical trials\|replication crisis\|industry-funded` | 9,211 / 6,572 / 248 | fine |
| `dtc_telehealth` | `telehealth\|telemedicine\|concierge medicine\|compounding pharmac(y\|ies)\|direct primary care` | 2,345 / 1,832 / 152 (plus brand names Hims, Hers, Ro) | fine |
| `medical_errors` | `malpractice\|medical errors\|misdiagnos\|iatrogenic\|medical negligence` | 2,562 / 2,176 / 207 | fine |
| `ethics_law_privacy` | `informed consent\|hipaa\|medical ethics\|right to try\|medical freedom` | 2,216 / 1,788 / 178 (Chiro Hustle 385, "medical freedom") | fine; "medical freedom" is common real phrasing, add to examples |
| `global_health` | `usaid\|pepfar\|global health\|malaria nets\|bed nets\|gavi` | 2,196 / 1,504 / 130 | fine |
| `disability_access` | `disabilit(y\|ies)\|wheelchairs?\|americans with disabilities` | 11,917 / 9,322 / 339 (Ramsey Show 493: disability insurance as personal finance) | fine; disability insurance as finance is not health |
| (nursing shortage, VA hospitals, PBMs) | `nursing shortage\|veterans affairs\|va hospitals?\|pharmacy benefit managers?\|pbms` | 750 / 633 / 120 | covered (`hospitals_access`, `costs_insurance`); no new subtopic |

Notes:

- Health-care fraud is a distinct recurring news subject in 2025–26 (Minnesota and California fraud
  stories, Oz at CMS):
  - "House Republicans in the Oversight Committee have launched an investigation into alleged hospice
    fraud in California" (Morning Wire 167361/1);
  - "so much of the fraud in our system is people who defrauding Medicare… Doctor Oz… found…"
    (Charlie Kirk 33543/114).

  The gold coded "committed Medicaid fraud" (c38054w0004) and a CMS fraud-detection line as
  `costs_insurance`. Make that explicit. At 270 episodes it is below the bar for its own subtopic.
- Ad boilerplate: "Featured products include compounded drug products, which the FDA does not approve
  or verify for safety, effectiveness, or quality" (Hims, Danny Jones 318827/1); "Weight loss by Hers
  gives you access to FDA-approved GLP-1 medications" (Armchair 73652/6). The first is a disclaimer. The
  second is `evidence:strength_assertion` in ad copy. Neither is the regulators topic.

### `policy`

| label | query | segs / eps / pods | verdict |
| --- | --- | --- | --- |
| `hhs_leadership` | `rfk\|robert f. kennedy\|hhs secretary\|health secretary\|surgeon general\|makary\|bhattacharya` | 7,814 / 4,977 / 195 | needs a boundary (campaign and name-only mentions) |
| `maha_movement` | `maha\|make america healthy again` | 1,091 / 774 / 84 (some "Maha" names, e.g. 201563/2, 652952/1) | fine |
| `public_health_authority` | `public health\|health officials\|dietary guidelines\|emergency powers` | 8,228 / 5,855 / 228 | fine |
| `regulation_chemicals_food_drugs` | `precautionary principle\|banned in europe\|banned in other countries\|eu bans?` | 244 / 225 / 56 | rare but distinct; keep |
| `health_law_courts` | (gold: 2 detections) | | fine |
| `partisan_politics` | (gold: 4 detections) | | fine |

Notes:

- RFK Jr. samples, 10 hits:
  - pure 2024 campaign or cabinet politics with no health subject, 6: "I don't think you'd pick RFK
    Junior [as a spoiler]" (330869/121); "the attempt by the Biden team to bar RFK Jr." from the debate
    stage (388740/3); "RFK Jr. Donald Trump nominates to lead the Health and Human Services Department"
    (14581/0, a cabinet-picks list); "Robert F. Kennedy flagged this when he went to the border" (87963/4);
  - health substance, 3: "RFK Junior… pills, powders, pricks, and potions" (29002/100); "RFK Jr.… going to
    help straighten out" chiropractic (186041/2); "Even the Surgeon General finally came out and said…
    Social media is bad for kids" (60291/1, → `cognition.digital_media_brain` plus
    `evidence:expert_consensus`, not `hhs_leadership`);
  - comedy, 1 (KILL TONY 194564/7).

  Name-only or campaign mentions should not be health content. The nomination itself ("RFK Jr. to lead
  HHS") is `hhs_leadership` `passing` only when HHS is named.
- MAHA is used as an adjective for a policy position ("a very non-MAHA solution… an Ozempic for all as
  part of Medicare for all", 330378/287). That is `glp1.access_compounding` + `costs_insurance` +
  `partisan_politics`, and `maha_movement` only if the movement itself is characterized.

## Proposed edits

CHANGE `topic:drugs_addiction.opioids_fentanyl`:
| opioids_fentanyl | Opioids & fentanyl | Opioid use, prescribing and overdose when opioids are named, including prescription pain pills taken or sold outside medical use. | fentanyl; heroin; OxyContin; Percocet; percs; pain pills; Purdue; pill mills; xylazine |
Why: the gold codes "too many people that are getting prescribed pain pills" (c71184w0031) as opioids; "percs" and "pain pills" are the real slang (benzos/percs query 2,824 eps).

CHANGE `topic:drugs_addiction.stimulants_illicit`:
| stimulants_illicit | Cocaine, meth & non-prescribed stimulants | Cocaine and methamphetamine, and prescription stimulants taken without a prescription (to study, work or party). Prescribed ADHD medication goes to `neurodevelopment.adhd`. | cocaine; coke; crack; meth; crystal meth; Adderall to study; Adderall without a prescription |
Why: 10,705 eps for cocaine/meth terms. Non-prescribed Adderall ("now they're all on Adderall, man", 663/6) has no home other than `neurodevelopment.adhd`, which would miscount it as ADHD.

CHANGE `topic:drugs_addiction.addiction_recovery`:
| addiction_recovery | Addiction & recovery | Addiction to drugs, or to substances in general, as a condition, and its treatment and recovery, when addiction or treatment is discussed. Dependence on alcohol alone goes to `alcohol.alcohol_use_disorder`; compulsive behaviours to `mental.behavioral_addictions`. "Addicted to" a food, show, habit or object as a figure of speech is not health content. | addict; addicted to heroin; rehab; got clean; relapse; Narcotics Anonymous; 12 steps; Suboxone; methadone; sober (from drugs) |
Why: 4 of 12 "addicted/addiction" samples were figurative (10945/4, 91961/4, 94525/4, 320061/3). AA is currently listed here while `alcohol_use_disorder` covers alcoholism, so sobriety talk (mostly about drinking, e.g. 91414/2, 90794/3) splits arbitrarily.

CHANGE `topic:drugs_addiction.drug_policy`:
| drug_policy | Drug policy, supply & overdose crisis | Drug laws, enforcement, trafficking, supply and drug testing as issues, and overdose counts and trends (add `drugs_addiction.opioids_fentanyl` only when opioids are named). A drug crime named only as an event in a story (a dealer, a drug deal gone wrong, a bust) is not health content, and neither are cartels discussed only as crime, immigration or security. The drugs' effects go to the drug's own subtopic. | overdose deaths; decriminalization; war on drugs; Measure 110; fentanyl trafficking; precursor chemicals; border fentanyl; workplace drug testing |
Why: drug-crime words in 7,538 eps, mostly plot ("a drug deal gone wrong", 9510/115; "an out of state drug dealer", 23822/3). 0 of 10 "cartel" samples were about drugs as health (42172/11, 38479/1), so "cartels" as a bare example misleads.

CHANGE `topic:psychoactives.cannabis`:
| cannabis | Cannabis & cannabinoids | Cannabis, THC, CBD and hemp products, including smoking cannabis (which is not `stimulants.smoking`). THC drinks marketed instead of alcohol also take `alcohol.alternatives`. | weed; marijuana; THC; CBD; CBN; edibles; gummies; delta-8; hemp-derived THC; dispensary; cannabis psychosis; legalization |
Why: 28,293 eps. "Smoke weed / a joint / a blunt" appears in 5,894 eps and collides with `stimulants.smoking` (77210/3, 92086/4).

CHANGE `topic:psychoactives.psychedelic_therapy`:
| psychedelic_therapy | Psychedelics & psychedelic therapy | Psychedelics and MDMA, recreationally or therapeutically. | psilocybin; magic mushrooms; shrooms; LSD; acid; MDMA; ecstasy; molly; MDMA therapy; ayahuasca; ibogaine; DMT; 5-MeO-DMT |
Why: 6,799 eps; real usage is "shrooms", "acid", "molly" (e.g. "what's the right amount of shrooms to take", gold c77624w0014). MDMA has no other home. "Molly" is mostly a person's name, so labelers need context.

CHANGE `topic:psychoactives.microdosing`:
| microdosing | Microdosing psychedelics | Taking sub-perceptual doses of psychedelics. Microdosed GLP-1s go to `glp1.new_offlabel_uses`; low-dose THC products to `psychoactives.cannabis`; "microdosing" exercise is not health-drug use. | microdosing psilocybin; microdosing mushrooms; microdosing LSD; microdose capsules |
Why: 403 eps / 95 podcasts with a psychedelic nearby, against 154 eps / 36 podcasts with a GLP-1 nearby ("We're microdosing. We're not hitting you with a sledgehammer", 190581/64; Mind Pump 195746/4). Also a THC microdose gummy ad (87499/0) and "they microdose" strength training (195703/2).

CHANGE `topic:psychoactives.novel_substances`:
| novel_substances | Kratom & novel substances | Kratom, 7-OH and other legal-high, gas-station or novel substances, and party drugs with no other home. | kratom; 7-OH; gas-station heroin; phenibut; tianeptine; nitrous oxide; whippets; poppers; GHB |
Why: kratom/7-OH/tianeptine in 548 eps / 96 podcasts ("kratom may be addictive… And they're telling people it's not addictive", 5957/12). GHB ("raping girls using GHB", 74510/5) has no home.

CHANGE `topic:alcohol.drinking_culture`:
| drinking_culture | Drinking patterns, culture & alcohol policy | How much, how often and why people drink, cutting back or quitting without a disorder framing, sober-curious culture and temporary abstinence, drink-driving as a risk, and alcohol policy (drinking age, taxes, warning labels). A single episode of being drunk or hungover told as part of a story is not health content. | Dry January; Sober October; sober curious; binge drinking; drinking less; quit drinking; drunk driving; drinking age; alcohol warning label |
Why: drink-driving (3,657 eps) and alcohol policy (445 eps) have no home ("we addressed the culture, especially around drunk driving", 86267/4). Scenery mentions are the bulk of comedy hits (194812/7, 52587/5) and the gold currently codes them here.

CHANGE `topic:alcohol.alcohol_use_disorder`:
| alcohol_use_disorder | Alcohol use disorder | Alcohol dependence and its treatment and recovery, including a person described as an alcoholic or problem drinker. "Alcoholic" meaning a drink that contains alcohol, "non-alcoholic fatty liver disease" (→ `metabolic.fatty_liver`) and "alcoholic" as an insult or simile are not this. | alcoholism; alcoholic (person); functional alcoholic; dry drunk; AA; Al-Anon; withdrawal; DTs; naltrexone |
Why: 10,092 eps for the keyword set. Half of the samples were non-health ("an alcoholic drink", 156833/4; "like some fucking alcoholic stepfather", 197083/2). Real person-level uses: "he was a functional alcoholic" (205821/2), "a dry drunk" (74458/4).

CHANGE `topic:alcohol.alternatives`:
| alternatives | Alcohol alternatives | Non-alcoholic drinks and products marketed or chosen instead of alcohol. THC drinks also take `psychoactives.cannabis`. "Non-alcoholic fatty liver disease" is not this (→ `metabolic.fatty_liver`). | non-alcoholic beer; NA beer; Athletic Brewing; mocktails; alcohol-free spirits; THC seltzers |
Why: 1,191 eps for the keyword set; NAFLD accounts for 156 eps in health shows (Dr. Jockers 192475/1, 192977/1).

CHANGE `topic:stimulants.smoking`:
| smoking | Smoking & tobacco | Cigarettes, cigars and tobacco smoking, including tobacco companies and tobacco regulation (menthol and flavour bans, tobacco settlements). Smoking cannabis goes to `psychoactives.cannabis`. | cigarettes; smoking; smoker; pack a day; quitting smoking; cigars; secondhand smoke; Big Tobacco; menthol ban |
Why: 16,536 eps. Tobacco-industry and regulation talk (788 eps / 127 podcasts, e.g. "Trump makes corrupt deal with Big Tobacco", 330071/5) has no home: `health_system.pharma_industry` excludes tobacco firms.

CHANGE `topic:stimulants.nicotine_products`:
| nicotine_products | Nicotine pouches, smokeless tobacco & nicotine as a nootropic | Nicotine without smoking or vaping: pouches, gum, lozenges, dip, chew and snus. | Zyn; Lucy; nicotine pouches; nicotine gum; Nicorette; dip; chewing tobacco; snus; nicotine for focus |
Why: 2,395 eps. Dip and chew have no home ("I used to dip… nicotine was just part of the day", 44378/8; "Dipping's bad for you because you can get mouth cancer… I chew Nicorette all day", 24239/11). Lucy pouch ads appear in 177 eps.

CHANGE `topic:stimulants.caffeine`:
| caffeine | Coffee, tea & caffeine | Caffeine and the drinks that carry it, when caffeine, its effects, dose, timing or dependence, or the drink's health effects are discussed. Coffee or tea as an order, errand, taste or setting is not health content. | caffeine; coffee and sleep; caffeine timing; cups a day; decaf; matcha; green tea benefits; caffeine crash |
Why: 0 of 10 coffee samples in comedy and recap shows were health ("the normal walk down the street with the coffee", 96260/6). The gold's caffeine detections are all effect, dose or timing talk (c78305w0011, c179429w0018).

CHANGE `topic:medications.other_drugs`:
| other_drugs | Other named medications | Any other named drug or drug class, including therapeutic Botox, biologics, preventive antibodies and muscle relaxers. Allergy drugs go to `immune.allergies`. | blood thinners; PPIs; steroids (medical); Accutane; Botox for migraine; biologics; Tremfya; nirsevimab (Beyfortus); muscle relaxers |
Why: DTC ads for Tremfya (2,838 eps, 35 podcasts) and Beyfortus (30489/4) are frequent; Beyfortus has no stated home. "Muscle relaxers" is in the gold (c128911w0034).

CHANGE `topic:health_system.costs_insurance`:
| costs_insurance | Costs, insurance & health-care fraud | What care costs and who pays, including public programmes and fraud against them. Car, life and disability insurance as personal finance is not health content. | health insurance; claim denials; UnitedHealthcare; Medicaid; Medicare; ACA subsidies; medical debt; drug prices; Medicaid cuts; Medicare fraud; hospice fraud |
Why: health-care fraud in 270 eps / 58 podcasts ("alleged hospice fraud in California", 167361/1; Oz on Medicare fraud, 33543/114). The gold already puts Medicaid fraud here (c38054w0004). Insurance keywords are noisy with non-health insurance ads (162694/2).

CHANGE `topic:health_system.ethics_law_privacy`:
| ethics_law_privacy | Medical ethics, law & privacy | Consent, privacy, autonomy and ethics of medical practice as principles, including "medical freedom" claims. Prosecutions and lawsuits go to `policy.health_law_courts`. | informed consent; HIPAA; medical ethics; medical freedom; bodily autonomy; right to try; conscientious objection |
Why: "medical freedom" is the commonest real phrasing in this cluster (Chiro Hustle alone 385 eps; 1,788 eps for the cluster).

CHANGE `topic:policy.hhs_leadership`:
| hhs_leadership | HHS leadership & federal health politics | Who runs federal health agencies and what they are doing politically: RFK Jr. as HHS secretary, appointments, firings, reorganizations, hearings, and leaders' fraud or spending drives. A health figure's name, election campaign or non-health politics is not health content unless a health subject or the health post is discussed. | RFK Jr. confirmation; HHS layoffs; CDC director fired; Senate hearing; Makary at FDA; Oz at CMS |
Why: 4,977 eps; 6 of 10 RFK samples were 2024 campaign or cabinet politics with no health content (330869/121, 388740/3, 87963/4).

## Codebook and prompt notes

1. **Section 3, new paragraph after "Violence, crime, war and death": "Alcohol, drugs, tobacco and
   caffeine in everyday talk."** Proposed text:
   > Substance use is health content when the window says something about the substance as a substance:
   > an effect on body or mind, a risk or harm, an amount or pattern of use ("half a pack a day", "drunk all
   > the time", "six months on Xanax"), dependence, quitting or sobriety, a policy, or a product sold for
   > its effect. A third person's ongoing use, addiction or rehab stated as a fact about them is `passing`,
   > including reality-TV cast, who are real people. A single episode of being drunk, high or hungover told
   > as part of a story ("we got drunk and went out"), a drink, cigarette or joint as scenery, and coffee as
   > an errand or taste are not health content. A drug crime named only as an event (a dealer, a deal gone
   > wrong, a bust) follows the violence rule: not health content unless use, overdose, addiction or drug
   > policy is discussed.

   Evidence: the comedy samples above (1–2 in 10 health); 7,538 eps of drug-crime words; the gold items
   c178291w0010, c95062w0004 and c3505w0007 would change.
2. **Section 3, idioms list.** Add: "addicted to" a non-substance ("my addiction to popcorn bowls"); "drunk
   on power"; "high on life"; "like he's on crack"; "that's dope"; "alcoholic" as a simile or insult; and
   lookalikes the labeler should not trip on: Coke (the soda), Molly (a name), Celsius (temperature),
   "non-alcoholic fatty liver" (a liver condition, not a drink). Evidence: 10945/4, 91961/4, 197083/2,
   51828/4, 24318/10.
3. **Section 3, ads.** Add: "Products whose purpose is a drug effect (nicotine pouches and vapes,
   cannabis or hemp-THC products, kratom) pass the ad test as health products. Alcohol, coffee, energy
   drinks and alcohol alternatives pass only under (b) or (c): a stated effect ('energy', 'focus', 'take the
   edge off', 'no hangover') or a health-framed free-from claim. A product name ('Energizer') is not a
   stated effect." Evidence: Red Bull Dragonberry (2,087 eps, no effect stated), Lucy (177 eps), Soul
   hemp-THC gummies ("Take the edge off a little bit", 201756/4), hangover pills (322108/8). Also,
   section 8: there is no `product_type` for cannabis or hemp products. Either widen `nicotine_or_tobacco`
   to `nicotine_tobacco_or_cannabis` or state that ingestible hemp products are `supplement`.
4. **Section 5.1, "General talk takes the parent".** Add: "drug use in general ('doing drugs', 'on
   drugs', 'drug problem', 'hard drugs', 'substance abuse') with no drug named is
   `topic:drugs_addiction`." Evidence: 11,562 eps / 384 podcasts. In lists such as "Alcoholism, drug usage,
   mental health issues are accelerated dramatically" (41123/4), rule 6 applies: one `passing` detection,
   adding `wellness.chronic_disease_trends` only if the point is a general rise.
5. **Section 5.1, rule 8 (substances keep their own home).** Add the substance pairings that came up:
   - non-medical use of a prescription drug keeps the drug's home (benzodiazepines →
     `mental.psychiatric_drugs`; opioid pills → `opioids_fentanyl`), except non-prescribed stimulants →
     `drugs_addiction.stimulants_illicit`;
   - add `drugs_addiction.addiction_recovery` (or `alcohol.alcohol_use_disorder`) when dependence is
     discussed;
   - smoking cannabis → `cannabis`, not `stimulants.smoking`;
   - THC drinks → `cannabis` + `alcohol.alternatives`;
   - nicotine for brain disease ("protective against Parkinson's", 24239/11) → `nicotine_products` +
     `neuro.neurodegenerative` (rule 1).
6. **Section 5.1, rule 4 (institutions).** Add: "Regulatory boilerplate in ad copy ('FDA-approved',
   'compounded products the FDA does not approve', 'not evaluated by the FDA') does not make
   `health_system.regulators`; 'FDA-approved' offered as grounds is `evidence:strength_assertion`, and a
   disclaimer is no signal." Evidence: 1,025 eps carry the disclaimer phrases; Hims (318827/1) and Hers
   (73652/6) reads.
7. **Section 5.1, rule 3 (policy).** Add: "A health figure's name or election campaign is not health
   content by itself; RFK Jr.'s 2024 candidacy is health content only where a health position is
   discussed (`policy.partisan_politics` plus the subject)." Evidence: 6 of 10 RFK samples.
8. **Section 4.1, `relevance` for drug ads (note for analysts, not labelers).** Prescription-drug ads
   (Tremfya 2,838 eps, Cologuard, Beyfortus) and McDonald's Red Bull reads will dominate raw counts of
   `medications.other_drugs` and `stimulants.energy_drinks` if the ad test lets them in. Report these
   labels split by `relevance`.

Process note: partway through, the coordinator asked me to switch to
`/mnt/internal/felix/podcast-corpus-text/cq.py`. The permission classifier blocked running and reading
from that path in this session, both before and after the reported permission rule. All counts and
samples here come from the original `/mnt/data2/podcast-data/corpus-text/cq.py` (byte-identical data per
the coordinator), under heavy shared load (load average ~146), so the counts are complete but sample
sizes were kept small.
