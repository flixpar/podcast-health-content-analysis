# Open-ended coverage audit (no label slice): corpus review

Method. I sampled passages using broad health-signalling words that are not the taxonomy's own vocabulary ("my doctor", "diagnosed", "symptoms", "my body", "healing", "protocol", "the science", "feel better", "energy", "game changer", "hospital", "pills", "health", "sick", "medicine", "nervous system", "my mom was diagnosed/passed"). I ran the samples separately for comedy, wellness and health, parenting and women's lifestyle, true crime, news, business, culture and interview, sports, conservative talk, left and centre politics, history and science, self-help and meditation, and reality, religion and military shows. I added one unfiltered random draw. I read each hit with its neighbouring segments and coded it against v8 as a labeler would. In the blind sample I read 204 passages. 44 were not health content under codebook section 3. The other 160 health passages come from about 75 podcasts. A further 16-hit sample checked generic "mental health" mentions. I clustered the misses and sized each cluster with targeted `count`, `cooc` and `sample` queries. The coding log is at `scratchpad/corpus-review/cov15/log.md`.

## Summary

- **v8 covers most of what people actually say.** Of 160 health passages coded blind, 66% fit a listed subtopic cleanly. 8% needed a bare parent or `topic:other`. 16% were ambiguous between two labels. 10% fell on an unclear health-content boundary (section 3). Most misses are boundary and tie-break problems, not missing subjects.
- **Biggest volume problem: generic "mental health".** The phrase appears in 23,849 episodes on 391 podcasts. In a 16-hit sample, about a third of the health hits forced a choice between bare `topic:mental` and `mental.wellbeing_grief_loneliness` ("mental health issues", "mental health awareness", "his mental health is declining"). The codebook's "general talk takes the parent" rule lists heart, brain and gut health, but not mental health. Add it.
- **Section 3 lacks three boundary rules, and each has large volume:**
  - a sports player being "healthy" in the sense of available to play (3,683 episodes on 199 podcasts, mostly sports shows);
  - self-help and personal-development psychology (self-talk, shame, "healing", "train your nervous system" used as metaphor);
  - guided meditation and sleep-hypnosis scripts themselves (whole shows of this: Meditation for Anxiety, Radio Headspace, Get Sleepy).
  Bare death mentions ("my dad passed away") and insurance ads that list health insurance also need a ruling.
- **Three new subtopics are warranted:**
  - `mental.psychiatric_care_forensic`: psych wards, 5150 and Baker Act holds, commitment, insanity pleas, competency. 3,418 episodes on 242 podcasts, mostly true crime. Today it has no home.
  - `sleep.other_sleep_disorders`: narcolepsy, sleep paralysis, sleepwalking, REM behaviour disorder. About 1,700 episodes on 189 podcasts, roughly half of them literal (the rest is the idiom "sleepwalking through").
  - `sexual.sex_education`: about 1,000 episodes on 150 podcasts; a culture-war subject in schools with no home.
- **Four definitions need to widen:**
  - `immune.inflammation` should take oxidative stress and free radicals (2,032 episodes on 79 podcasts; today the concept has no home).
  - `health_system.costs_insurance` should take Medicare and Medicaid fraud (270 episodes on 58 podcasts).
  - `mental.ocd_personality` should take factitious disorder and Munchausen by proxy (358 episodes on 83 podcasts).
  - `policy.partisan_politics` should name the fights over inclusive medical language ("birthing people", "vulva owners").
- **Recurring contested propositions with no narrative:**
  - "the food pyramid and low-fat advice caused the obesity epidemic" (149 episodes co-occurring);
  - "high LDL does not cause heart disease" (107 episodes on 28 podcasts with a strict pattern; distinct from the dietary `saturated_fat_cholesterol_myth`);
  - "the mind can cure serious disease" (Dispenza alone appears in 325 episodes on 54 podcasts);
  - "normal labs miss disease, so you need optimal ranges" (190 thyroid-pattern episodes; 1,035 episodes mention reference or optimal ranges);
  - "trauma is stored in the body" (423 episodes on 85 podcasts). This is the weakest case.
  Also widen `germ_theory_denial` to cover HIV/AIDS denial (59 episodes, mostly Rogan).
- **Smaller tie-break fixes, all codebook notes:** food sensitivities (`gut.digestive_symptoms` vs `immune.allergies`); family caregiving outside old age; tumours of unstated malignancy ("brain tumor", 827 episodes); "healthcare" as one item in a list of political issues; non-medical use of prescription sedatives; somatic-memory talk.

## Label-by-label findings

(Coverage audit: this section gives the coverage sample and the clusters of misses instead of per-label rows.)

### Coverage sample

Key to the columns:

- **Coded**: health passages only; passages that are not health content (X) are counted separately.
- **Covered**: a listed subtopic fits cleanly, including legitimate co-labels.
- **Bare/other**: the labeler needs a bare parent or `topic:other`.
- **Ambiguous**: two labels fit and the codebook does not decide.
- **Boundary**: section 3 does not settle whether the passage is health content.

| podcast type (batch) | passages coded | fully covered | bare parent / other | ambiguous | boundary unclear | non-health hits read |
| --- | --- | --- | --- | --- | --- | --- |
| Comedy (Rogan, Theo Von, Bad Friends, YMH, Stavvy, Flagrant, Smosh, Are You Garbage) | 15 | 10 (67%) | 2 (13%) | 3 (20%) | 0 | 3 |
| Wellness and health (Hyman, Jockers, Thyroid Fixer, Mind Pump, Brecka, Niddam, Lyon, Extend, Diabetes Nerd, Culture Apothecary, Rooted, SoG, Attia, Huberman) | 28 | 20 (71%) | 2 (7%) | 6 (21%) | 0 | 2 |
| Parenting and women's lifestyle (Delony, Mayim Bialik, Giggly Squad, Call Her Daddy, Not Skinny) | 14 | 11 (79%) | 1 (7%) | 1 (7%) | 1 (7%) | 6 |
| True crime (MFM, Morbid, Casefile, Crime Junkie, Today in TC, Murder With My Husband) | 8 | 4 (50%) | 2 (25%) | 1 (13%) | 1 (13%) | 2 |
| News (The Daily, Today Explained, Up First, Morning Wire) | 9 | 6 (67%) | 0 | 2 (22%) | 1 (11%) | 1 |
| Business (DOAC, Ramsey, YAP) | 5 | 4 (80%) | 0 | 0 | 1 (20%) | 4 |
| Culture and interview (Armchair, Shetty, Conan, Oprah, This American Life) | 9 | 5 (56%) | 1 (11%) | 3 (33%) | 0 | 1 |
| Sports (PMT, Simmons, Le Batard, Fantasy Footballers) | 8 | 4 (50%) | 1 (13%) | 0 | 3 (38%) | 2 |
| Conservative talk (Walsh, Megyn Kelly, Kirk, Danny Jones, Dorey) | 7 | 5 (71%) | 0 | 2 (29%) | 0 | 3 |
| Mixed culture and crime talk (Dillon, Tucker, Candace, Frisella, CHD, Theo Von) | 12 | 9 (75%) | 0 | 2 (17%) | 1 (8%) | 0 |
| Left and centre politics (Pod Save America, Breaking Points, MeidasTouch, IHIP, Daily Show) | 10 | 7 (70%) | 0 | 2 (20%) | 1 (10%) | 0 |
| History and science (Behind the Bastards, LPOTL, Something You Should Know) | 6 | 4 (67%) | 0 | 1 (17%) | 1 (17%) | 4 |
| Self-help and meditation (Mindset Mentor, Meditation for Anxiety, Mel Robbins, Shetty) | 8 | 2 (25%) | 1 (13%) | 1 (13%) | 4 (50%) | 1 |
| Reality, religion, outdoors and military (Shawn Ryan, Team House, MeatEater, WWC) | 5 | 5 (100%) | 0 | 0 | 0 | 5 |
| Family-illness talk, all shows | 6 | 3 (50%) | 1 (17%) | 0 | 2 (33%) | 6 |
| Unfiltered random draw, all shows | 10 | 6 (60%) | 1 (10%) | 2 (20%) | 1 (10%) | 4 |
| **Total** | **160** | **105 (66%)** | **13 (8%)** | **26 (16%)** | **16 (10%)** | **44** |

The batches differ in a pattern. Health shows are well covered, and their misses are ambiguity on mechanism words (oxidative stress, detox diets, bioavailability, the endocannabinoid system). True crime and self-help have the highest miss rates. True crime fails on generic "mental health" and psychiatric or forensic care. Self-help fails on whether emotional "healing" talk is health content at all. Sports misses are almost all boundary cases: "healthy" meaning available to play.

### Clusters of misses

**1. Generic "mental health" with no condition: bare `topic:mental` or `wellbeing`?** (types a and b)
- Query `\bmental health\b`: 36,511 segments, 23,849 episodes, 391 podcasts. Top shows are MeidasTouch, LPOTL, Delony, Killer Stories, Ramsey and Rogan; many are BetterHelp reads.
- In a 16-hit sample (seed 81): 3 idioms ("mental health moment", "mental health day"); 8 that fit a subtopic (therapy, `serious_mental_illness`, microbiome, access to care); 5 that left a coder choosing between bare `topic:mental` and `wellbeing_grief_loneliness`.
- Blind-sample instances: 9728/218 MFM "if it was like mental illness... that little boy went untreated"; 4086/2 Morbid "a lot of like mental health issues going on there that maybe just never got diagnosed"; 22589/9 PMT "the mental health awareness stuff... makes people that feel like they're alone realize they're not alone"; 175685/2 Modern Wisdom "most people are depressed, poor, lonely, sexless, angry, have mental health issues"; 161451/6 Rotten Mango "his mental health is declining".
- Verdict: needs a codebook rule; no new label (see notes).

**2. Psychiatric hospitalization and forensic psychiatry: no home** (type a)
- Query `insanity (plea|defen[cs]e)|by reason of insanity|competen(t|cy) to stand trial|psych(iatric)? (eval|evaluation|hold)|psych ward|psychiatric (hospital|ward|unit|facility)|5150|baker act|involuntar* commit*|committed to a mental...|mental (hospital|institution)`: 4,340 segments, 3,418 episodes, 242 podcasts. Led by MFM 193, Killer Stories 145, LPOTL 135, True Crime All The Time 129, Morbid 126, Rotten Mango 112 and Rogan 107.
- Samples are mostly literal: 8 of 13 read are real; the rest are "insane asylum" jibes.
- Quotes: 319909/2 Snook "placed under a 72-hour psychiatric hold and subsequently transferred to a mental health facility"; 44694/444 MFM "acquitted by reason of insanity... committed to the Hawaii State Psychiatric Hospital"; 21276/0 DOAC (Steve-O) "You were manhandled into a psych ward"; 218/5 Crime Junkie, a 1970s psychiatrist at Highland Hospital.
- `mental.therapy` is talk therapy and `health_system.hospitals_access` is general care delivery, so coders split or fall back to bare `topic:mental`.
- Verdict: ADD.

**3. Sleep disorders other than insomnia and apnea** (type a)
- Query `sleep paralysis|night terrors?|narcolep*|parasomnia|REM behaviour disorder|sleepwalk*`: 2,244 segments, 1,707 episodes, 189 podcasts. Rogan 98, PMT 92, Morbid, LPOTL, Snook.
- In sports shows about half are the idiom ("the Bears were sleepwalking"); elsewhere they are mostly literal.
- Quotes: 71536/5 Rogan (Birbiglia) "I'm diagnosed with REM behavior disorder"; 191737/6 Smosh "textbook sleep paralysis hallucination", plus a Montpellier study of violent sleepwalking; 192239/8 Therapuss "that's narcolepsy. Now I have all this medicine and stimulants"; 323256/5 This Feels Criminal, a sleepwalking-killer defence.
- No sleep subtopic fits (`insomnia` covers trouble sleeping, `apnea_breathing` covers breathing).
- Verdict: ADD.

**4. Oxidative stress and free radicals as an explanation** (type a)
- Query `oxidative stress|free radicals?|reactive oxygen species`: 3,829 segments, 2,032 episodes, 79 podcasts. Jockers 447, Hyman 295, Niddam 186, SuperLife 134, Thyroid Fixer 88, Brecka 82, Attia 48, Rogan 41.
- "Antioxidants" adds 3,612 episodes on 145 podcasts, inflated by Kirk and Meidas ads.
- Quotes: 192586/1 Jockers "reduce this inflammation, reduce these free radicals, and get back your cellular energy"; 190055/209 Niddam "if we can help to manage inflammation, if we can help to manage oxidative stress"; 303391/214 Niddam "producing reactive oxygen species".
- Only antioxidant supplements have a home (`supplements.other_compounds`). The mechanism itself lands on `immune.inflammation`, `metabolic.mitochondria_energy` or nothing.
- Verdict: change `immune.inflammation`. It already holds the parallel "explanation" concept and co-occurs with oxidative stress in nearly every hit.

**5. Health-care fraud** (type b: `costs_insurance` vs `policy.health_law_courts` vs `medical_errors`)
- Query `(medicare|medicaid|health ?care|hospice|autism|billing) fraud|billed medicare`: 322 segments, 270 episodes, 58 podcasts. Morning Wire 40, MeidasTouch 37, Rogan 19, Kirk 18, Breaking Points 17. The broader pattern including "insurance fraud" gives 663 episodes, about half of it non-health insurance fraud.
- Quotes: 167290/0 Morning Wire "a massive, sprawling Medicaid fraud scheme in the red state of Ohio"; 33734/19 Kirk "another medicaid fraud Minnesota. Medicaid has fourteen waiver programs"; 329162/12 Behind the Bastards on fake-doctor NPI-number scams.
- Verdict: change `costs_insurance`; a prosecution or trial also takes `health_law_courts`.

**6. Factitious disorder and Munchausen by proxy** (type a)
- Query `munchausen|munchhausen|factitious`: 487 segments, 358 episodes, 83 podcasts. WWC 49 (mostly loose jibes), Walsh 31 (often as an analogy for masking children), Armchair 27, MFM 20.
- Real uses: 70055/4 48 Hours "The condition is called Munchausen syndrome by proxy"; 197579/8 "conditions like PTSD or factitious disorder, where someone might fake victimization"; 661561/0 Sympathy Pains (a whole series); 323634/0 Stavvy "hospital fantasy... Gypsy Rose".
- Verdict: change `mental.ocd_personality`, whose "pathological lying" is the nearest neighbour. Medical child abuse also takes `acute_care.violence_abuse`.

**7. Sex education** (type a)
- Query `sex ed|sex education|sexual education|health class|comprehensive sexuality`: 1,199 segments, 1,024 episodes, 150 podcasts. Please Me! 109, Kirk 84, Walsh 61, Shapiro 37, Megyn Kelly 37, Rogan 34. Netflix's *Sex Education* adds noise in film shows.
- Quotes: 12698/0 Megyn Kelly "You cannot do sex education on homo homosexual lifestyle... at the K through three levels"; 175561/6 Modern Wisdom "teen content that children are witnessing as their sex education"; 196427/4 Two Hot Takes "I didn't get a proper sex education talk... I wasn't on birth control"; 190589/86 Thyroid Fixer "sex education, health education is really failing us" on fertility.
- `sexual.*` has only STIs and sexual function. A school-curriculum fight lands on bare `topic:sexual` or `partisan_politics`.
- Verdict: ADD.

**8. Self-help psychology and emotional "healing"** (type c)
- Blind instances: 188022/2 Mindset Mentor "if you don't invest the time to heal yourself, you might begin self-sabotaging"; 342/4 Mel Robbins "There's a better way. It's called healing. It's called grace."; 187636/1 "training your nervous system to stop panicking at no" (rejection-therapy dares); 187472/0 "healing as an adult requires us to say..."; 177284/3 Delony, a parent's anger and need for control.
- Self-help and meditation batches had 50% boundary-unclear passages, and the shows are large: Mindset Mentor 1,927 listed episodes, Mel Robbins 441, School of Greatness 1,995, Jay Shetty 883.
- Verdict: codebook rule (see notes).

**9. Guided practice scripts** (type c)
- 203253/1 Meditation for Anxiety "So breathe and feel one with your calm. Breathe and heal." Whole shows consist of delivered practice: Meditation for Anxiety 1,482, Radio Headspace 1,751, Get Sleepy 787, Nothing Much Happens 510 and Sleep Magic 271 listed episodes.
- Without a rule, every window of a script could take `stress.meditation_mindfulness`, or none could.
- Verdict: codebook rule.

**10. Sports "health" as availability** (type c)
- Query `(stay|stays|staying|stayed) healthy|if (he|they|she) (is|are) healthy|health (issues|concerns) (with|for)`: 4,224 segments, 3,683 episodes, 199 podcasts. Simmons 469, Fantasy Footballers 467, PMT 323, Ringer Fantasy 206.
- Instances: 165304/3 "any chance Jordan Cameron leads them all? ...no, because of health"; 79799/1 "There's no health issues; there's nothing like that"; 163577/4 "if you're not worried at all about the the health".
- Verdict: codebook rule.

**11. Recurring contested propositions with no narrative** (type d)
- *Dietary guidelines caused obesity.*
  - `cooc '(food pyramid|dietary guidelines|low.fat ...)' '(obesity epidemic|made us fat|grain lobby|sugar industry ...)'` gives 149 episodes (Hyman 46, Rogan 15, Maintenance Phase 8 as rebuttal). A strict same-segment pattern gives 42 episodes on 22 podcasts.
  - Quotes: 27849/3 Passion Struck (Makary) "We said the food pyramid was the way to eat that ignited the modern-day obesity epidemic"; 37896/0 Kirk (Means) "Where did the food pyramid come from? It was a lobbying instrument"; 37691/2 Kirk "blow up the food pyramid, and make the lobbyists for Kellogg's and Nestle not have a back door".
  - Not covered by `saturated_fat_cholesterol_myth` (fat is harmless) or `food_engineered_to_harm` (deliberate engineering).
- *LDL is not harmful.*
  - A strict pattern (`ldl|cholesterol|lipid hypothesis` within 80 characters of "not the cause / doesn't matter / myth / is a lie") gives 119 segments, 107 episodes, 28 podcasts. Hyman 29, Attia 13 (mostly rebutting), Rogan 9, Jockers 7, Niddam 6.
  - Quotes: 6254/5 Megyn Kelly "If high cholesterol, high LDLs, doesn't cause a heart attack..."; 189966 Niddam episode titled "The Plaque LIE"; 190242/785 Niddam "that lousy cholesterol is a beacon and not a... problem to be attacked"; 41926/8 Megyn Kelly "Insulin resistance is a greater marker for cardiovascular disease... than LDL cholesterol".
  - The existing narratives cover dietary saturated fat and cholesterol (`saturated_fat_cholesterol_myth`) and statins (`statins_harmful`), not blood LDL causality.
- *The mind cures disease.*
  - A strict pattern gives 136 episodes on 51 podcasts; "Dispenza" alone gives 389 segments, 325 episodes, 54 podcasts (SoG 69, Chiro Hustle 27, Mayim 23).
  - Quotes: 183327/4 SoG "you have the power to heal yourself of absolutely. Anything"; 84769/0 Shetty (Dispenza) "the chemo isn't working. The surgeries didn't work... they're kind of left with their belief in themselves"; 186986/1 Beyond Well "if you heal yourself of cancer".
  - `stress.mind_body` covers the subject but no narrative carries the cure claim.
- *Normal labs miss disease.*
  - A thyroid pattern (TSH or thyroid near "only test", "full panel", "undiagnosed", "reference range", "optimal range", "told me it was normal") gives 253 segments, 190 episodes, 27 podcasts. Thyroid Fixer 94, Hyman 35, Jockers 9, Hello Hormones 6. Generic "reference/optimal/normal range" gives 1,035 episodes on 130 podcasts.
  - Quotes: 190653/50 "working with conventional medicine who has you on T4 only and is only testing TSH"; 176545/3 Extend "these incredibly tight optimal ranges... they actually do get their lives back"; 191004/0 "my thyroid was undiagnosed by six different doctors".
- *Trauma is stored in the body.*
  - Query `body keeps the score|stored in the body|trauma (is )?stored|issues in the tissues`: 482 segments, 423 episodes, 85 podcasts. SoG 41, Mayim 23, Armchair 20, Delony 20.
  - Quotes: 176945/1 Brecka "how trauma is stored in the body"; 191081/1 Psychology of your 20s "it is stored in your body. If you have ever read The Body Keeps the Score".
  - Contested, but often said in passing. This is the weakest of the five.
- *Hidden mast cell activation.* 221 episodes on 45 podcasts; 176913/1 Brecka "Up to 17 to 20% of the population may have mast cell syndrome and not know it". The topic `chronic_complex.mcas_eds` covers it. Too narrow for its own narrative; `unlisted_narrative` will do.
- *HIV/AIDS denial.* 59 episodes on 11 podcasts (Rogan 38): 11112/5 Rogan (Malone) "Tony Fauci canceling the esteemed virologist Peter Duesberg because he was raising questions about... HIV and its role"; 71639/3 Rogan "we have found a molecular biologist to debate Dr. Peter G. Duesberg". Fold into `germ_theory_denial`.

**12. Smaller ambiguities seen in the blind sample** (type b; codebook notes, no new labels)
- *Food sensitivities* (1,235 episodes, 129 podcasts): 185518/3 Mayim "I don't want to say allergic, but so highly sensitive to... beans, nuts, tofu" can be read as `immune.allergies`, `gut.digestive_symptoms` (which lists "food intolerance") or `diets.elimination_therapeutic`.
- *Family caregiving outside old age* (2,543 "caregiv*" episodes, many meaning childcare or attachment): 178026/0 Delony "my kid has cancer... medication change or a new test result"; 179137/5 10% Happier (Robin Roberts) "my caregiver, and now I'm hers". `elder_care` names caregiving but only for older people.
- *Tumours of unstated malignancy* (827 "brain tumor" episodes, 163 podcasts): 74507/4 Armchair "my wife almost died... of a brain tumor".
- *"Healthcare" as a political list item*: 578001/0 Daily Show "every other issue—healthcare, taxes"; 165440/2 IHIP "universal healthcare, or universal pre-K, or childcare".
- *Non-medical prescription sedatives* (Xanax family: 2,490 episodes, 207 podcasts, mostly prescribed or anxiolytic contexts): 323909/7 Stavvy "These are Xanax. These are hypno pills... I like to get fucked up" can be read as `psychiatric_drugs` (which lists Xanax) or the `drugs_addiction` parent.
- *Inclusive medical language* (434 raw episodes on 95 podcasts, many plain "pregnant people"): 8365/9 Megyn Kelly "vulva owners". `partisan_politics` ("health in culture-war debates") covers it but has no example, so a blind coder reached for `topic:other`.
- *Somatic memory*: 25951/50 Shetty "it's reverberating through your brain and your body... stop having some of those somatic symptoms" can be read as `stress.mind_body`, `stress.nervous_system_regulation` (which lists somatic therapy) or `mental.trauma_ptsd`.
- *Endocannabinoid system* (173 episodes, 51 podcasts): 23899/4 Huberman "anandamide might be more of a tonic molecule" can be read as `psychoactives.cannabis` or `cognition.neurochemistry_talk`.
- *Detox diets*: 175291/928 Rooted "I put a lot of people in the detox" can be read as `detox.toxic_load_general`, `organ_cleanses` or an elimination diet.
- *Honey eaten as food*: 185665/1 Culture Apothecary can be read as bee products in `supplements.herbal_adaptogens` or `food.sugar_sweeteners`.
- *Possession versus mental illness*: 205415/1 PBD (exorcist) "They're schizophrenic. They're bipolar. They're on drugs." Code the mental subtopics plus `frame:spiritual_religious`.

## Proposed edits

ADD `topic:mental.psychiatric_care_forensic` under `mental`:
| psychiatric_care_forensic | Psychiatric hospitalization & forensic psychiatry | Inpatient and crisis psychiatric care and the legal side of mental illness: psych wards, 72-hour holds (5150, Baker Act), involuntary commitment, state hospitals and asylums, insanity pleas, competency to stand trial and court-ordered psychiatric evaluations. Talk therapy goes to `mental.therapy`; the person's condition also takes its own subtopic. | psych ward; 72-hour hold; 5150; Baker Act; involuntary commitment; not guilty by reason of insanity; competent to stand trial; psychiatric evaluation; state psychiatric hospital; institutionalized |
Why: 3,418 episodes on 242 podcasts (true crime above all: MFM 193, Killer Stories 145, LPOTL 135); 8 of 13 sampled hits literal. 319909/2 "placed under a 72-hour psychiatric hold and subsequently transferred to a mental health facility"; 44694/444 "acquitted by reason of insanity... committed to the Hawaii State Psychiatric Hospital". No listed subtopic fits, so coders currently use bare `topic:mental`.

ADD `topic:sleep.other_sleep_disorders` under `sleep`:
| other_sleep_disorders | Narcolepsy, parasomnias & other sleep disorders | Sleep disorders other than insomnia and sleep-disordered breathing: narcolepsy and hypersomnia, sleepwalking, night terrors, sleep paralysis, REM sleep behaviour disorder and other parasomnias. "Sleepwalking through" something as an idiom is not health content. | narcolepsy; sleep paralysis; sleepwalking; night terrors; REM behavior disorder; parasomnia; sleepwalking defense |
Why: 1,707 episodes on 189 podcasts (roughly half literal, the rest idiom in sports shows). 71536/5 "I'm diagnosed with REM behavior disorder"; 191737/6 "textbook sleep paralysis hallucination". Neither `sleep.insomnia` nor `sleep.apnea_breathing` fits.

ADD `topic:sexual.sex_education` under `sexual`:
| sex_education | Sex education | Sexual-health education at school, at home or from media and pornography, and fights over curricula and age-appropriateness. Gender-identity lessons go to `gender.gender_identity_science`; contraception content also takes `fertility.contraception`. | sex ed; comprehensive sex education; health class; the talk with parents; porn as sex education; age-appropriate curriculum |
Why: 1,024 episodes on 150 podcasts (Kirk 84, Walsh 61, Shapiro 37, Megyn Kelly 37, Please Me! 109; minus some *Sex Education* TV mentions). 12698/0 "You cannot do sex education on homo homosexual lifestyle... at the K through three levels"; 175561/6 "teen content that children are witnessing as their sex education". There is no home now.

CHANGE `topic:immune.inflammation`:
| inflammation | Inflammation & oxidative stress as explanations | Inflammation or oxidative stress invoked as a cause of disease or ageing, or as a property of foods and lifestyles, and markers of them. Antioxidant supplements go to `supplements.other_compounds`; antioxidant foods to `food.plant_foods_fiber`. | chronic inflammation; inflammatory foods; CRP; "inflammation is the root of all disease"; inflammaging; neuroinflammation; oxidative stress; free radicals; reactive oxygen species; NRF2 |
Why: oxidative stress, free radicals and ROS appear in 2,032 episodes on 79 podcasts (Jockers 447, Hyman 295, Niddam 186) with no topic home. 192586/1 "reduce this inflammation, reduce these free radicals"; 190055/209 "manage inflammation... manage oxidative stress".

CHANGE `topic:health_system.costs_insurance`:
| costs_insurance | Costs, insurance & billing fraud | What care costs and who pays, including fraud and improper payments in public and private insurance. A prosecution or trial also takes `policy.health_law_courts`. | health insurance; claim denials; UnitedHealthcare; Medicaid; Medicare; ACA; medical debt; drug prices; Medicare fraud; Medicaid fraud scheme |
Why: 270 episodes on 58 podcasts with health-care fraud (Morning Wire 40, MeidasTouch 37, Kirk 18). 167290/0 "a massive, sprawling Medicaid fraud scheme"; coders split it three ways (`costs_insurance`, `health_law_courts`, `medical_errors`).

CHANGE `topic:mental.ocd_personality`:
| ocd_personality | OCD, intrusive thoughts, personality & factitious disorders | OCD, intrusive thoughts, clinically framed personality disorders and traits (pathological lying, narcissistic traits), and factitious disorder (Munchausen syndrome). Munchausen by proxy also takes `acute_care.violence_abuse` as medical child abuse. Insults such as calling someone a "narcissist", and "Munchausen" as a loose jibe, are not health content. | OCD; intrusive thoughts; borderline personality disorder; narcissistic personality disorder (as diagnosis); pathological lying; Munchausen syndrome; Munchausen by proxy; factitious disorder |
Why: 358 episodes on 83 podcasts. 70055/4 "The condition is called Munchausen syndrome by proxy"; 197579/8 "PTSD or factitious disorder, where someone might fake victimization". No home today.

CHANGE `topic:policy.partisan_politics`:
| partisan_politics | Partisan politics of health | Health as an electoral or partisan issue: party positions, campaigns, polls, health in culture-war debates, including fights over inclusive medical language. | Democrats on health care; campaign health promises; health polling; "birthing people"; "pregnant people" in official documents; "chestfeeding" |
Why: 434 raw episodes on 95 podcasts (Megyn Kelly 51, Kirk 50, Shapiro 28, Walsh 22). A blind coder sent 8365/9 ("vulva owners") to `topic:other`; 83816/0 covers a state ban on "pregnant people" and "birth giver".

CHANGE `topic:gut.digestive_symptoms`:
| digestive_symptoms | Digestive symptoms & functional disorders | Everyday digestive complaints and functional gut disorders, including non-allergic food sensitivities and intolerances. Allergic reactions to food go to `immune.allergies`; food-sensitivity test kits go to `self_tracking.consumer_lab_tests`. | bloating; constipation; reflux; GERD; heartburn; IBS; SIBO; food intolerance; food sensitivities; lactose intolerance; gas |
Why: 1,235 episodes on 129 podcasts (Hyman 230, Jockers 120, Mind Pump 71). 185518/3 "I don't want to say allergic, but so highly sensitive to... beans, nuts, tofu" splits between allergies, digestive symptoms and elimination diets.

ADD `narrative:dietary_guidelines_caused_obesity` under Food & diet:
| dietary_guidelines_caused_obesity | Official diet advice caused the obesity epidemic | **Official dietary guidance (the food pyramid, low-fat advice) caused the obesity and chronic-disease epidemic,** often because grain, sugar or food-industry lobbying shaped it. That dietary fat is harmless is `narrative:saturated_fat_cholesterol_myth`; deliberate engineering of food is `narrative:food_engineered_to_harm`. | the food pyramid made us fat; the low-fat era caused obesity; the grain lobby wrote the pyramid; dietary guidelines bought by Big Food | policy |
Why: 149 episodes co-occurring; 42 episodes on 22 podcasts in a strict same-segment pattern (Hyman, Rogan, Kirk, Megyn Kelly, Maintenance Phase rebutting). 27849/3 "the food pyramid was the way to eat that ignited the modern-day obesity epidemic"; 37896/0 "Where did the food pyramid come from? It was a lobbying instrument".

ADD `narrative:ldl_not_harmful` under Pharmaceuticals & conventional medicine:
| ldl_not_harmful | High LDL cholesterol is not harmful | **High LDL or blood cholesterol does not cause heart disease;** the lipid hypothesis is called wrong, cholesterol is called a repair "beacon", and lowering it is said to be unnecessary. Dietary fat and cholesterol claims are `narrative:saturated_fat_cholesterol_myth`; statin harm or uselessness is `narrative:statins_harmful`. | LDL doesn't matter; the plaque lie; cholesterol is not the bad guy; insulin, not LDL, causes heart disease; lipid hypothesis is wrong | cardiovascular |
Why: 107 episodes on 28 podcasts with a strict pattern (Hyman 29, Attia 13 mostly rebutting, Rogan 9, Niddam 6). 6254/5 "If high cholesterol, high LDLs, doesn't cause a heart attack..."; 190242/785 "cholesterol is a beacon and not a... problem to be attacked". It is a central cardiometabolic misinformation claim, separate from the dietary narrative.

ADD `narrative:mind_cures_disease` under Alternative health & wellness:
| mind_cures_disease | The mind can cure serious disease | **Thoughts, beliefs or emotional release can cure serious physical disease such as cancer,** making medical treatment secondary; remissions are credited to mindset, meditation or manifesting. That emotions affect health in general is the topic `stress.mind_body`, not this narrative. | heal yourself of anything; spontaneous remission through belief; meditated the tumor away; healings at Dispenza retreats | stress |
Why: 136 episodes on 51 podcasts with a strict pattern; Dispenza is named in 325 episodes on 54 podcasts (SoG 69, Chiro Hustle 27, Mayim 23). 183327/4 "you have the power to heal yourself of absolutely. Anything"; 84769/0 "the chemo isn't working... they're kind of left with their belief in themselves".

ADD `narrative:normal_labs_miss_disease` under Health system, policy & society:
| normal_labs_miss_disease | "Normal" lab results hide real disease | **Standard lab tests and reference ranges miss most hormone, thyroid or metabolic dysfunction,** so patients told they are normal are really sick; full panels and narrow "optimal ranges" are said to be needed. | TSH-only testing misses hypothyroidism; optimal ranges versus reference ranges; your labs are normal but you're not; demand a full thyroid panel | procedures |
Why: 190 episodes on 27 podcasts with the thyroid pattern (Thyroid Fixer 94, Hyman 35, Jockers 9, Hello Hormones 6); "reference/optimal/normal range" gives 1,035 episodes on 130 podcasts. 190653/50 "conventional medicine who has you on T4 only and is only testing TSH"; 191004/0 "my thyroid was undiagnosed by six different doctors". This is the signature functional-medicine diagnostic claim and drives `consumer_lab_tests` sales.

ADD `narrative:trauma_stored_in_body` under Alternative health & wellness:
| trauma_stored_in_body | Trauma is stored in the body | **Psychological trauma is physically stored in the body's tissues and causes physical symptoms or illness until released,** usually through somatic, breath or bodywork practices. | the body keeps the score; trauma stored in the hips; issues in the tissues; releasing stored trauma | stress |
Why: 423 episodes on 85 podcasts (SoG 41, Mayim 23, Armchair 20, Delony 20, Brecka). 176945/1 "how trauma is stored in the body"; 191081/1 "it is stored in your body. If you have ever read The Body Keeps the Score". Lower priority than the four above: the claim is often made in passing and is only partly contested.

CHANGE `narrative:germ_theory_denial`:
| germ_theory_denial | Germ theory is false / terrain theory | **Germs do not cause disease.** Viruses are said not to exist or not to be contagious, and the "terrain" is what matters; also denial that a specific pathogen causes its disease (HIV does not cause AIDS). | terrain theory; viruses don't exist; Pasteur recanted; HIV doesn't cause AIDS; Duesberg | infectious |
Why: HIV/AIDS denial appears in 59 episodes on 11 podcasts, mostly Rogan (38): 11112/5 "Fauci canceling the esteemed virologist Peter Duesberg because he was raising questions about... HIV and its role". No narrative covers it today, and it is not common enough for its own.

## Codebook and prompt notes

1. **Section 5.1, "General talk takes the parent": add mental health.** Suggested text: "'mental health' in general, undiagnosed 'mental health issues', mental-health awareness or stigma, and a society's or person's mental health declining with no condition named are `topic:mental`; `mental.wellbeing_grief_loneliness` is for mood, happiness, loneliness, grief and burnout as emotion." Evidence: 23,849 episodes on 391 podcasts. In a 16-hit sample, 5 of 13 health hits had no tie-break. Blind examples: 4086/2, 9728/218, 22589/9, 175685/2. Also add: speculation that a real person (a suspect, a public figure) has undiagnosed mental illness is a `passing` `topic:mental` detection with no claim.

2. **Section 3, new exclusion: sports availability.** Suggested text: "'healthy', 'health' or 'health issues' meaning an athlete is available to play, with no injury, condition or treatment named, is not health content; a named injury or 'injury stuff' is `musculoskeletal.sports_injuries` (`passing`)." Evidence: 3,683 episodes on 199 podcasts (Simmons 469, Fantasy Footballers 467, PMT 323); 165304/3, 79799/1, 163577/4.

3. **Section 3, new boundary: self-help and relationship psychology.** Suggested text: "Personal-development and relationship talk (confidence, mindset, self-talk, shame, 'healing' in a moral or relational sense, attachment, 'train your nervous system' as a metaphor for courage) is health content only when it names a mental-health condition, symptom, treatment or practice offered for mental or physical health ('therapy', 'anxiety', 'depression', 'trauma', 'meditation'). Then code that subject; otherwise exclude." Evidence: the self-help batch was 50% boundary-unclear (188022/2, 342/4, 187636/1, 187472/0), and the shows are large (SoG 1,995, Mindset Mentor 1,927, Shetty 883 listed episodes).

4. **Section 3, new rule: delivered guided practice.** Suggested text: "A guided meditation, breathing exercise, sleep story or hypnosis script delivered to the listener takes one `passing` detection of its practice per window (`stress.meditation_mindfulness`, `stress.breathwork`, `sleep.sleep_hygiene_environment`). Health claims about the practice ('this will calm your anxiety') are coded normally; the scripted instructions themselves are not claims." Evidence: Meditation for Anxiety (1,482 listed episodes), Radio Headspace (1,751), Get Sleepy (787), Nothing Much Happens (510), Sleep Magic (271); 203253/1.

5. **Section 3, death without cause.** Extend the violence and death paragraph: "A death named with no cause, illness, injury or care ('my dad passed away last May', 'the day my dad died') is not health content; grief over it is `mental.wellbeing_grief_loneliness` only when the grief is discussed." Evidence: 58451/8 Ramsey, 6595/7 Tucker; the family-illness batch had 2 of 6 boundary-unclear.

6. **Section 3, ads: insurance marketplaces.** Suggested text: "An insurance or financial ad that lists health insurance among several products fails test (a) unless health coverage is the featured product." Evidence: Ramsey's recurring insurance-hub read "life insurance. Health insurance, identity theft protection" (57986/9, 57596/10).

7. **Section 5.1, co-labeling rule 6 (lists) and rule 3 (policy): "healthcare" as a political list item.** Suggested text: "'Healthcare' named as one issue among non-health issues takes no detection; a stated position or claim about coverage or cost takes `health_system.costs_insurance`, plus `policy.partisan_politics` when party positions or campaigns are themselves discussed." Evidence: 578001/0, 165440/2, 330395/137.

8. **Section 5.1, unsettled facts: tumours of unstated malignancy.** Suggested text: "A 'tumor' with no cancer word or type takes the organ's cancer subtopic (`cancer.other_specific_cancers` for brain tumours) at confidence 0.7 or less; a tumour stated to be benign (meningioma, fibroid, lipoma) takes the organ system's subtopic." Evidence: "brain tumor" in 827 episodes on 163 podcasts; 74507/4.

9. **Section 5.1, caregiving.** Suggested text: "Caring for a family member with a named illness takes that illness's subtopic, plus `stress.stress_burnout` or `mental.wellbeing_grief_loneliness` for the carer's strain; `dementia_ageing.elder_care` only when the person cared for is old or frail." Evidence: 178026/0, 179137/5.

10. **Section 5.1, rule 8 (substances keep their own home): prescription drugs used non-medically.** Suggested text: "Prescription opioids used recreationally are `drugs_addiction.opioids_fentanyl`; benzodiazepines and sleeping pills are `mental.psychiatric_drugs` or `sleep.insomnia`, plus `drugs_addiction.addiction_recovery` when addiction or treatment is discussed." Evidence: 323909/7 ("These are Xanax... I like to get fucked up"), 163340/4 ("fucked up on pills"); Xanax-family terms in 2,490 episodes on 207 podcasts.

11. **Label-table nudges, no new labels:**
    - add "endocannabinoid system; anandamide" to `psychoactives.cannabis` examples (173 episodes, 51 podcasts);
    - add "trauma stored in the body; somatic symptoms of trauma" to `stress.nervous_system_regulation` examples, and say there that physical illness attributed to emotions also takes `stress.mind_body`;
    - add "honey and bee pollen eaten as food go to `food.sugar_sweeteners`" to `supplements.herbal_adaptogens`;
    - add "detox diets ('put people on a detox for three weeks')" to `detox.organ_cleanses`.

12. **Rubric (`analysis/prompts/rubric-v8.md`), step 1.** Add a short boundary checklist for the four high-volume non-content patterns: sports availability, self-help metaphor, a bare death, and idioms built on medical words ("sick man of Europe", "sleepwalking through", "mental health day"). In the blind sample, 44 of 204 hits (22%) were not health content, and these patterns made up most of the borderline ones.
