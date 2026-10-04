# Mind, brain and sleep (`mental`, `neurodevelopment`, `stress`, `sleep`, `cognition`): corpus review

Method: `cq.py count` / `sample` / `cooc` over the ~145,600-episode corpus. All counts are segments / episodes / podcasts for the query shown. Keyword counts are upper bounds: for most terms in this slice, loose or figurative use is a large share of hits, and the samples below estimate that share. (Note: all searches used the brief's original `/mnt/data2/podcast-data/corpus-text/cq.py`. A switch to an NVMe copy was blocked by the permission classifier, so I did not use it.)

## Summary

- **Every parent in this slice is heavily present.** "mental health" 36.5k segs / 23.8k eps / 391 podcasts; "sleep" 60k eps / 654 podcasts; "stress" 51k eps / 575 podcasts; depression 29k eps; anxiety 40k eps; therapy terms 42k eps. No label in the slice is absent. The rarest listed example is "dopamine detox/fasting", at only 76 eps.
- **Most hits are loose or figurative, not just a minority.** Of 14 random "narcissis*" hits, 12 are insults or character judgements. Of 14 "psychopath/sociopath" hits, 12 are praise, insult or crime-character description. "Intrusive thought" is now sports-talk slang for a hot take (65 eps on The Ringer Fantasy Football Show alone). "Anxious", "depressed", "traumatized", "grief" and "dopamine hit" are mostly ordinary emotion talk, crime narration or metaphor. The codebook's three examples ("narcissist", "psycho", "OCD about my desk") cover only a fraction of this. Section 3 needs a general test plus corpus-attested examples (see Codebook notes 1-3).
- **Mental-health ads are the single most common mental-health content outside health shows.** BetterHelp alone has 9,927 segs; BetterHelp/Talkspace/Cerebral/Headspace/Calm/NOCD reach 13.5k eps on 300 podcasts. Add Talkiatry (psychiatric telehealth), NOCD's Howie Mandel OCD read (~600 eps of Killer Stories), Bend Health and the Zepbound sleep-apnea ads (262 eps of The Bulwark Daily). Mental-health ad language for non-health products ("that uneasy, anxious feeling... about your insurance company") must be excluded. Gambling-helpline boilerplate ("Gambling problem? Call 1-800-GAMBLER") dominates the 5,000 "gambling problem" episodes and is already excluded. Both need explicit worked lines.
- **Gap 1, ADD `mental.psychiatric_care`.** Covers psychiatric hospitalization, involuntary commitment, asylums and deinstitutionalization, the insanity defense and competency, non-drug psychiatric treatments (ECT, TMS, SGB, lobotomy history) and access to psychiatrists. About 4,050 eps / 256 podcasts for the hospital, commitment and system terms, plus 1,312 eps / 136 podcasts for insanity-defense and competency terms (true crime). None of the 13 `mental` subtopics fits, and the involuntary-commitment policy debate is research-relevant.
- **Gap 2, ADD `sleep.dreams_parasomnias`.** Covers dreams, lucid dreaming, nightmares, sleep paralysis, sleepwalking, night terrors and narcolepsy. Sleep paralysis: 325 eps / 61 podcasts, often attributed to demons or the paranormal. Lucid dreaming and dream meaning: 587 eps / 124 podcasts. Narcolepsy: 322 eps / 110 podcasts. All of it currently falls to bare `topic:sleep`.
- **Definition boundaries that real passages break:**
  - `neurodevelopment.adhd` versus non-medical Adderall use. Most of the 2,039 Adderall episodes are party or study use and jokes.
  - `neurodevelopment.neurodiversity`, which has no home for autistic lived experience (late diagnosis, nonverbal kids, autism parents; a whole show, Tony Mantor, is about this).
  - `stress.stress_burnout` versus `endocrine.cortisol_adrenal`. "Cortisol" is now slang for stress: "You don't want to spike your cortisol".
  - `cognition.focus_productivity`, where most hits are business or productivity talk ("attention span of the average voter").
  - `cognition.memory_learning`, which has no place for IQ as a health outcome (fluoride or lead or pandemic "IQ points" claims).
- **Several examples are poor search anchors.** "tapping", "grounding", "mind-body connection" and "brain rot" mostly hit figurative uses or ad copy: intentional grounding, a Wayfair chair that "felt grounding", GNC's pre-workout "intense mind-body connection", "populist brain rot". "dopamine detox" is rare while "dopamine hit" is common. I propose more specific examples.
- **Codebook additions.** (a) Real people's emotions narrated as story (grief, loneliness, fear in crime and news) are excluded, mirroring the fiction rule. (b) Armchair diagnosis of public figures: an insult is excluded; a sustained claim that a named person has a condition is health content at low confidence. (c) Guided practices (meditation scripts, sleep stories, sleep hypnosis) get one practice detection, not labels for the imagery.

## Label-by-label findings

### `topic:mental` (parent)
- `\bmental health\b`: 36,511 / 23,849 / 391. Top shows include MeidasTouch (951 eps) and Last Podcast On The Left (782), driven by therapy ads. Fine as parent.

### `mental.depression`
- `\bdepress(ion|ed|ive)\b`: 46,509 / 29,454 / 504. Includes "Great Depression" and "economically depressed" (ep 183323 s0, ep 44355 s3).
- Loose use is common. `so depressed|I'm depressed|that's depressing`: 2,825 / 2,684 / 209. For example "Rick Ross looks so depressed to be flying with y'all junkies" (ep 84625 s8), against a real state in "she wanted to jump off the ship because she was so depressed" (ep 661143 s2).
- The definition ("when depression or a depressive state is named") would capture every "I'm depressed". **Needs definition change.**
- Real-world cross-topic causes: "hypothyroidism. People can become depressed" (ep 33413 s7). Demonic versus "natural" causes appear in an exorcist interview.

### `mental.anxiety`
- `anxiety|panic attacks?|anxious`: 68,248 / 39,836 / 574. The top show is Meditation for Anxiety (1,477 eps of guided scripts).
- Samples show ordinary emotion and ad copy: "that uneasy, anxious feeling you get when you think about dealing with your insurance company" (ep 194710 s6, repeated across many shows); "your daily anxiety disappears" (finance ad, ep 36260 s0); "the man looks anxious" (crime narration, ep 161868 s3).
- Real uses: "I'd get like social anxiety" (ep 70831 s2). **Needs definition change** (a condition or ongoing state, not a momentary feeling).

### `mental.trauma_ptsd`
- PTSD-family terms: 10,826 / 7,959 / 309. `\bptsd\b`: 5,705 eps / 275 podcasts.
- Loose use: "I've had PTSD from toasted cheese sandwiches" (ep 9545 s71); "Yeah, PTSD" about a near-miss in a car (ep 192219 s5, borderline). "Trauma" also hits traumatic brain injury (ep 7577 s11, which belongs to `neuro.concussion_tbi`) and physical trauma.
- Repressed and recovered memories, and satanic panic: 554 eps / 92 podcasts. Example: a detective who "had also conducted extensive research on the subject of repressed memories" (Casefile, ep 22210 s3). These have no named home.
- "The body keeps the score": recurring and contested ("Now, a new guy has a book says the body doesn't…", ep 159164 s3).
- **Needs definition and examples change.**

### `mental.serious_mental_illness`
- 14,909 / 10,360 / 341. "psychotic" and "schizo" are often insults, and "bipolar" is used for weather or people. Fine apart from the general loose-use rule. Postpartum psychosis (821 eps for postpartum depression, psychosis or anxiety) appears heavily via the Lindsay Clancy trial. Code it here plus `pregnancy`.

### `mental.ocd_personality`
- OCD and intrusive thoughts: 4,508 / 3,528 / 223. 617 of those eps are the NOCD / Howie Mandel read on Killer Stories (ep 324842 s0): "people throw the term around like it's no big deal".
- Loose OCD (`little bit OCD|so OCD|I'm OCD|my OCD`): 378 eps / 94 podcasts, e.g. "because I'm a little bit OCD" (ep 155184 s1173).
- "Intrusive thought(s)" as slang: "this was actually going to be one of my intrusive thoughts later, but I think teams should be more willing to bench their starter" (ep 322333 s5), and "the intrusive thought crept in" (ep 17720 s5). The Ringer Fantasy Football Show is the #1 show for the phrase (65 eps). Real clinical use: postpartum intrusive thoughts (ep 177452 s3).
- Personality disorders and psychopathy terms: 14,710 / 10,825 / 337. "sociopath*|psychopath*" alone: 12,357 segs. In samples the clinical sense is rare. "Sociopaths have no conscience. They'll just blow right through a polygraph exam" (ep 55156 s22) counts. "He's just an absolute psychopath, just like stone cold" (praise of an athlete, ep 128765 s10) does not.
- Armchair diagnosis: `malignant narcissis*|Goldwater rule|armchair diagnos*` gives 450 eps / 67 podcasts, led by MeidasTouch (147) and IHIP News (101). For example "it's the behavior of a sociopath. It's the behavior of a malignant narcissist" about Trump (ep 15967 s7), and "the old Goldwater rule about not wanting to diagnose a candidate's physical or mental health from afar" (ep 6892 s3).
- **Needs examples and definition change** (psychopathy as a clinical construct; slang exclusions).

### `mental.suicide_self_harm`
- 32,663 / 21,348 / 484 (the "988" and "killed himself" terms are broad). True-crime suicides dominate, along with veteran and gun-suicide policy (ep 39721 s0, "why is that so many Alaskans are committing suicide"). Fine.

### `mental.eating_disorders`
- 4,386 / 3,152 / 215. Watch What Crappens leads (reality-TV gossip about cast members). Mind Pump is second (fitness-industry disordered eating). Fine.

### `mental.psychiatric_drugs`
- 10,165 / 7,005 / 269. Loose and comedic uses: "Give me a Xanax" (ep 90670 s4); "Xanax and boxed wine are being delivered to the MSNBC studios" (ep 6193 s9); "lithium deposits" (ep 71629 s0).
- Real content includes SSRIs versus exercise (ep 4009 s3), methylene blue after failed SSRIs (ep 192421 s3) and Amanita as a benzo-taper aid (ep 318908 s3, an ad). Fine.
- Talkiatry ads (2,460 eps / 206 podcasts for Talkiatry, Cerebral and Done terms) are psychiatric medication-management services. They fit the proposed `mental.psychiatric_care` better than `therapy`.

### `mental.therapy`
- `therapist|therapy|CBT|DBT|EMDR|counseling|BetterHelp|Talkspace`: 73,978 / 42,020 / 543. "therapy" also hits physical, hormone and light therapy, but labelers can handle that.
- BetterHelp alone: 9,927 segs. Its reads are near-identical across hundreds of shows: "Think about therapy as your editorial partner" (ep 128333 s0). Fine. See codebook note 4 on ad coding.

### `mental.wellbeing_grief_loneliness`
- 35,309 / 23,642 / 547. Much of it is grief narrated as an event in true crime and news: "Our entire community is filled with grief following today's officer-involved shooting" (ep 389696 s1); "He doesn't show any grief" (ep 603490 s3).
- Real wellbeing talk exists: "we are really suffering from a crisis of loneliness" (ep 178881 s0). **Needs a codebook rule** (note 2) rather than a table change. Add one exclusion clause to the definition.

### `mental.pop_psychology`
- `therapy-speak|attachment style|anxious/avoidant attach*|trauma bond*|self-diagnos*|love bomb*`: 2,723 / 1,950 / 184.
- Narcissist-spotting self-help: `narcissistic abuse/parent/ex|covert narcissist|dating a narcissist|narcissists do…`: 246 eps / 75 podcasts. Examples: "2 Secrets to Handling a Narcissist" (Mel Robbins, ep 2817 s2) and "You Don't Have to Forgive the Narcissist | Dr. Ramani" (ep 183533 s5).
- Overdiagnosis and pathologizing claims (`everyone has ADHD/anxiety…|overdiagnos*|overmedicat*|pathologiz*`): 826 eps / 137 podcasts.
- Reality-TV loose use is heavy ("I'm not a love bomber", ep 90239 s4).
- The coder confusion is three-way: `ocd_personality` for NPD as a diagnosis, `acute_care.violence_abuse` for "narcissistic abuse", and this label for therapy-speak. **Needs a definition change** that names where narcissist self-help goes.

### `mental.behavioral_addictions`
- Named behavioral addictions: 1,426 eps / 171 podcasts. Porn addiction: 596 eps / 112 podcasts. Phone, social-media and gaming addiction: 624 eps / 114 podcasts.
- `gambling addiction/problem…`: 5,023 eps / 161 podcasts, but samples are almost all sportsbook boilerplate (6 of 8). Real: "I know a lot of people that are addicted to gambling. Pornography." (ep 63156 s10).
- The boundary with `cognition.digital_media_brain` ("compulsive use as an addiction goes here") will pull every casual "I'm addicted to my phone" into this label. **Needs a definition change.**

### `mental.causes_models`
- `chemical imbalance|social determinants of mental|root of mental|biopsychosocial|mental illness is`: 943 / 778 / 141.
- Nutritional and metabolic psychiatry ("Brain Energy", keto for bipolar): 288 eps / 58 podcasts, e.g. "Dr. Chris Palmer: Can Fixing Your Diet Help Treat Mental Illness?" (ep 176667 s5). This fits here (plus rule 1 for the diet). Add it as an example. Otherwise fine.

### `topic:neurodevelopment` and subtopics
- Autism terms: 11,569 / 6,434 / 256. Loose and insult use: "He's so autistic" (KILL TONY, ep 194739 s2); "some guy who's on the autism spectrum, who's filled up with SSRIs" (stereotype, ep 70775 s15).
- `autism_causes_prevalence`: 433 eps / 89 podcasts for causes, rates and epidemic terms. The example "1 in 31" occurs, mostly as ASR words: "one in thirty-one", 241 eps across the ratio variants. Tylenol and autism co-occur in 227 eps, already covered by `narrative:tylenol_autism`. Fine.
- `autism_treatment`: ABA, leucovorin, chelation and "recovered" terms: 246 eps / 61 podcasts. Fine.
- `neurodiversity`: `neurodivergen*|neurodiver*|neurotypical|stimming`: 753 eps / 144 podcasts. ("masking" alone is swamped by COVID masks.) Late diagnosis, adult autism or ADHD, autism parents and nonverbal: 1,447 eps / 190 podcasts (noisy). Examples: "Navigating Late Autism Diagnosis" (ep 156638 s23); "nonverbal autistic people" (ep 156467 s8); autism-mom burnout (ep 156500 s49). None of the three autism subtopics clearly takes lived experience, parenting or support needs. **Needs a definition change.**
- `adhd`: 8,881 / 6,312 / 232 (without "ADD"). Killer Stories (617) is the Talkiatry ad. Adderall alone: 2,039 eps / 158 podcasts, mostly non-medical: "They still have Adderall" for studying (ep 195985 s3); "I feel like I literally took an Adderall. I'm like wired" (simile, ep 94824 s0); KILL TONY jokes. The label says ADHD stimulants go here, but study, party and recreational use is not ADHD. **Needs a boundary.**
- `developmental_delays`: 3,081 eps / 239 podcasts. Tourette's: 546 segs, including functional "TikTok tics" (ep 9660 s318). Down syndrome and cerebral palsy (373 eps) belong to `genetics.genetic_conditions`, and KILL TONY jokes are frequent. The name omits tics, which are listed only in its examples; the name should say so (small change).

### `topic:stress`
- `stress_burnout`: 17,208 / 13,360 / 355. Lots of everyday "stressed out" (Watch What Crappens is the top show for "stress"). Colloquial cortisol: "You don't want to spike your cortisol… I can't have my cortisol spiking" about horror films (ep 156799 s3). Spike/raise/lower-cortisol phrasing: 597 eps / 104 podcasts, mixed literal and slang. **Needs a definition change** (cortisol slang goes here; the hormone goes to endocrine).
- `nervous_system_regulation`: 11,250 eps / 329 podcasts, but "tapping" is mostly non-health ("tapping into that", BJJ tapping). Real: EFT tapping (ep 96388 s0) and wearable vagus-nerve stimulators, i.e. NeuroPod ads ("It stimulates the vagus nerve through the ear… The goal is nervous system regulation", ep 185281 s1) and Apollo Neuro. Apollo is also listed in `biohacking.devices_gadgets`. **Examples change.**
- `breathwork`: 2,083 eps / 155 podcasts (Rogan, Huberman, Brecka). Fine.
- `meditation_mindfulness`: 16,668 eps / 325 podcasts. Includes whole shows of guided practice: "You breathe in slowly. And gently embrace your fear" (Meditation for Anxiety, ep 203191 s1). Fine as a label; it needs a codebook note on delivered practice (note 6).
- `nature_grounding`: "grounding" is mostly figurative: a Wayfair read that "felt grounding" (ep 87395 s0), "a very grounding experience" (ep 4958 s1), NFL "intentional grounding". Real: "grounding his feet in buckets of dirt for electrical balance" (ep 196333 s8). Earthing, forest-bathing and nature-time terms: 1,195 eps, of which the 273 Call Her Daddy eps are a vacation-rental ad. **Examples change.**
- `mind_body`: psychoneuroimmunology, stored emotions and "body keeps the score" terms: 1,159 eps / 112 podcasts, but 486 of those are Pardon My Take's GNC pre-workout read: "now with harder hitting energy, an intense mind-body connection" (ep 21013 s10). Real: "It can absolutely eventually affect your physical health as well… because the body keeps the score" (ep 159164 s3). **Examples change.**

### `topic:sleep`
- `sleep_duration_quality`: 25,653 eps / 471 podcasts (noisy because of "naps"). Includes ads: "What if the secret to better sleep is already on your wrist? Apollo Neuro" (ep 200717 s0). Fine.
- `insomnia`: 3,950 eps / 244 podcasts. Melatonin: 2,249 eps (supplements home). Boring History For Sleep (202 eps) is show framing, not insomnia talk. Fine.
- `apnea_breathing`: 4,223 eps / 234 podcasts. OSA ads: 499 eps / 76 podcasts, 262 of them on The Bulwark Daily ("undiagnosed with moderate to severe obstructive sleep apnea or OSA in adults with obesity", ep 93959 s0), which should take this label plus `glp1`. Mattress Firm reads list "snoring" (Giggly Squad). Mouth taping and mouth or nasal breathing: 694 eps / 111 podcasts. Fine.
- `circadian_light`: 5,602 eps / 263 podcasts. "morning light" in sleep-story narration is noise (ep 324349 s15). Fine.
- `sleep_hygiene_environment`: 12,863 eps / 333 podcasts, overwhelmingly mattress, sheet and Eight Sleep ads. Real: "set your air conditioning… 68 degrees" (ep 192616 s1). Fine.
- **Gap, dreams and parasomnias.** Combined dreams/parasomnia terms: 2,335 eps / 210 podcasts (noisy). Sleep paralysis: 325 eps / 61 podcasts, mostly true-crime, creepy and paranormal shows. Examples: "'My Sleep Paralysis Demons Remind Me to Engage in Self Care'" (Morbid, ep 1822 s1); "doesn't this feel like sleep paralysis… the witch sitting on him" (ep 161771 s8); a clinical treatment, "Sleep paralysis is possible, but it could be another kind of sleep disorder too, like narcolepsy or confusional arousal" (Short Wave, ep 609379 s1). Lucid dreaming, recurring nightmares and dream meaning: 587 eps / 124 podcasts. Narcolepsy: 322 / 110. The meme "sleep paralysis demon" (ep 44442 s2, about Roy Cohn) is figurative and excluded.

### `topic:cognition`
- Parent ("brain health", "brain function", "your brain on"): 4,244 eps / 202 podcasts. Many hits are ad benefit lists, e.g. krill oil "support healthy blood pressure, circulation, brain health" (ep 83816 s1). Fine.
- `focus_productivity`: 6,079 eps / 236 podcasts, but samples are mostly non-health: "the attention span of the average voter is pretty short" (ep 33545 s230); "do some deep work in terms of like some really good questions" (coaching, ep 47894 s2); "get into flow state" (marketing, ep 20750 s0). **Needs definition tightening.**
- `nootropics`: 1,662 eps / 125 podcasts. Alpha Brain and Onnit reads (ep 325339 s0), Magic Mind reads ("adaptogens, nootropics. Such as lion's mane, ashwagandha", ep 187378 s2), and methylene blue. Fine. Add study-drug Adderall.
- `memory_learning`: 8,102 eps / 320 podcasts (noisy because of "memorize"). IQ: 5,608 eps / 246 podcasts, overwhelmingly insults ("Theo Van is a low IQ conspiracist", ep 48612 s1). But IQ is also a recurring health outcome: "It lowers IQ in kids by as much as seven points" (fluoride, ep 55207 s15); "children lost twenty two IQ points during the pandemic" (ep 11412 s1). Exposure-plus-IQ phrasing: 564 eps / 95 podcasts (noisy). Rule 1 needs an outcome home for IQ. **Definition change.**
- `brain_fog`: 4,336 segs / 3,218 eps / 168 podcasts. Mostly a symptom in lists for menopause (ep 190541 s9, ep 181980 s4), long COVID, NAD and ads (Good Ranchers "get rid of brain fog", ep 39138 s2; C60 "kick fatigue and brain fog to the curb", ep 192608 s0). The rule-6 list rule and the ad-outcome rule decide most cases. Clarify co-labeling with the cause.
- `neurochemistry_talk`: dopamine 5,346 eps / 215 podcasts. `dopamine hit/rush/spike|hit of dopamine|cheap dopamine`: 1,335 eps / 158 podcasts. "dopamine detox/fasting": only 76 eps / 32 podcasts. Many uses are metaphor: "the dopamine fuel of clicks and fake outrage" (politics, ep 331089 s360); "your brain feels that hit of dopamine" about paying off debt (ep 58383 s10). Substantive: "What is the main driver of mood? Serotonin… we make them right here in the gut" (ep 176888 s4). **Examples change**, plus a loose-use note.
- `digital_media_brain`: 3,456 eps / 217 podcasts. "screen time" often means TV airtime (ep 322508 s1); "doomscrolling" appears in show CTAs; "brain rot" is used as an insult ("populist brain rot", ep 325198 s12). Real policy: "Australia… the first social media ban for kids under the age of 16" (ep 204177 s0). **Examples change.**

### Gap evidence for `mental.psychiatric_care`
- Hospital, commitment and system terms (`involuntary commit*|5150|Baker Act|psych ward|psychiatric hospital/ward/facility/hold/care/beds|mental hospital/institution|deinstitutionaliz*|mental health system/care/services/treatment`): 5,063 / 4,053 / 256.
- Insanity defense and competency or psych evaluation: 1,624 / 1,312 / 136.
- Somatic treatments and history (TMS, ECT, electroshock, neurofeedback, DBS, SGB, lobotomy, SPECT): 1,319 eps / 166 podcasts. This is noisy ("lobotomized" as an insult, "ect").
- Quotes:
  - "Eric Adams… has now suggested you might need involuntary commitment of the mentally ill who are not threatening to others" (ep 389193 s2).
  - "He was actually hospitalized in a children's psych ward. For a couple weeks" (ep 178088 s0).
  - "locked up, lobotomized, didn't need to be there" (Up First, "Lost Mental Hospitals, Lost Patients", ep 4112 s2).
  - "committed himself to a local psychiatric ward, he's probably trying to buy time to set it up as a insanity defense" (ep 70157 s2).
  - Talkiatry read: "provide ongoing medication management… can treat anxiety, ADHD, depression" (ep 324916 s0).
- Today this content lands on bare `topic:mental`, on `health_system.hospitals_access` (which is generic), or nowhere.

## Proposed edits

CHANGE `topic:mental.depression`:
| depression | Depression | Depression as a condition or a sustained depressive state, named as such (diagnosis, episodes, symptoms, treatment, rates). A momentary reaction ("I'm so depressed we lost", "he looks so depressed") is loose description and not health content; low mood discussed as a state short of depression goes to `mental.wellbeing_grief_loneliness`. | depression; major depressive disorder; treatment-resistant depression; depressive episode; "I've struggled with depression"; postpartum depression (plus `pregnancy`) |
Why: 2,684 eps contain "so depressed / I'm depressed / that's depressing", mostly as reactions ("Rick Ross looks so depressed", ep 84625 s8). The current "when… a depressive state is named" would make each one a detection.

CHANGE `topic:mental.anxiety`:
| anxiety | Anxiety & panic | Anxiety disorders, panic attacks and anxiety as an ongoing condition or symptom ("my anxiety", social anxiety, health anxiety). Ordinary worry or nervousness about an event, and anxiety words in ad copy for non-health products, are not health content. | anxiety disorder; panic attacks; generalized anxiety; social anxiety; "my anxiety"; health anxiety |
Why: 39,836 eps. Samples are dominated by momentary feelings and non-health ad copy ("that uneasy, anxious feeling… your insurance company", ep 194710 s6; "your daily anxiety disappears", ep 36260 s0).

CHANGE `topic:mental.trauma_ptsd`:
| trauma_ptsd | Trauma & PTSD | Psychological trauma and its effects, including PTSD, childhood adversity, trauma said to be held in the body, and repressed or recovered memories of trauma (and recovered-memory therapy). Traumatic brain injury goes to `neuro.concussion_tbi`; physical injury to `acute_care.trauma_fractures`. Hyperbole ("PTSD from toasted cheese sandwiches") is not health content. | PTSD; CPTSD; childhood trauma; ACEs; trauma response; "the body keeps the score"; repressed memories; combat PTSD |
Why: 7,959 eps. "Trauma" hits TBI (ep 7577 s11) and physical trauma. Repressed and recovered memory, including satanic panic, appears in 554 eps / 92 podcasts with no stated home (ep 22210 s3). "The body keeps the score" is recurring and contested (ep 159164 s3, ep 58568 s0).

CHANGE `topic:mental.ocd_personality`:
| ocd_personality | OCD, intrusive thoughts & personality disorders | OCD, clinically meant intrusive thoughts, and personality disorders and traits used as clinical categories (diagnosis, assessment, how the disorder works, prevalence), including psychopathy and sociopathy. Not health content: insults and character judgements ("narcissist", "psychopath", "malignant narcissist" about a politician), "a little OCD" about tidiness, and "intrusive thought" as slang for an impulsive idea or hot take. | OCD; exposure and response prevention; postpartum intrusive thoughts; borderline personality disorder; narcissistic personality disorder (as diagnosis); psychopathy checklist; antisocial personality disorder; pathological lying |
Why: about 12,357 psychopath/sociopath segs and 10,408 narcissist segs, mostly insults (12 of 14 sampled in each). "Intrusive thoughts" is sports slang (ep 322333 s5; Ringer Fantasy Football is the top show at 65 eps). There are 378 eps of "a little / so OCD". Clinical uses exist ("Sociopaths have no conscience. They'll just blow right through a polygraph exam", ep 55156 s22).

CHANGE `topic:mental.wellbeing_grief_loneliness`:
| wellbeing_grief_loneliness | Wellbeing, mood, grief & loneliness | Psychological wellbeing as a subject: happiness, loneliness, grief and bereavement, purpose, resilience, burnout as emotional state, and mood (low or good mood, mood swings, irritability) short of a diagnosed disorder. A real person's grief or loneliness narrated as part of a story (a grieving family in a crime case) is not health content unless how grief or loneliness works, or its effects, is discussed. | loneliness epidemic; grief; grieving process; happiness; resilience; emotional health; mental wellness; improve your mood; mood swings; irritability |
Why: 23,642 eps. Grief as narrative event dominates the samples ("Our entire community is filled with grief", ep 389696 s1; "He doesn't show any grief", ep 603490 s3).

CHANGE `topic:mental.pop_psychology`:
| pop_psychology | Pop psychology & self-diagnosis | Popular psychological vocabulary (therapy-speak) and self-diagnosis as a social phenomenon, self-help about spotting and handling "narcissists" or "toxic" partners, attachment styles, and claims that mental-health diagnoses are over-applied (overdiagnosis, pathologizing normal feelings). Abuse in a relationship discussed as harm goes to `acute_care.violence_abuse`; narcissistic personality disorder as a diagnosis to `mental.ocd_personality`; the words used as insults or reality-TV description are not health content. | therapy-speak; self-diagnosing on TikTok; attachment styles; trauma bonding; love bombing; how to spot a narcissist; "everyone has ADHD now"; overdiagnosis |
Why: narcissist self-help covers 246 eps / 75 podcasts (Mel Robbins ep 2817 s2, Dr. Ramani ep 183533 s5). Overdiagnosis and pathologizing claims cover 826 eps / 137 podcasts. The three-way narcissist boundary is not stated anywhere.

CHANGE `topic:mental.behavioral_addictions`:
| behavioral_addictions | Behavioral addictions | Compulsive behaviors treated as an addiction or disorder (loss of control, harm, withdrawal, treatment, recovery). Casual "I'm addicted to my phone" about heavy use goes to `cognition.digital_media_brain`; sportsbook responsible-gambling boilerplate is not health content. | porn addiction; gambling addiction; sports-betting addiction; gaming disorder; shopping addiction; NoFap (as addiction recovery) |
Why: "gambling problem" terms hit 5,023 eps, but 6 of 8 samples were "Gambling problem? Call 1-800-GAMBLER". Phone, social-media and gaming addiction phrasing hits 624 eps, most of it casual. The current boundary sends all of it here.

ADD `topic:mental.psychiatric_care` under `mental`:
| psychiatric_care | Psychiatric care, hospitalization & mental-health system | Where and how psychiatric care is delivered and enforced: psychiatric hospitals and holds, involuntary commitment, asylums and deinstitutionalization, access to psychiatrists (including psychiatric telehealth), non-drug psychiatric treatments (ECT, TMS, stellate ganglion block, lobotomy as history), and mental illness in the courts (insanity defense, competency). Drugs go to `mental.psychiatric_drugs`; talk therapy to `mental.therapy`. | psych ward; 5150; Baker Act; involuntary commitment; state mental hospital; deinstitutionalization; insanity defense; competent to stand trial; ECT; TMS; Talkiatry |
Why: about 4,050 eps / 256 podcasts for hospital, commitment and system terms, plus 1,312 eps / 136 podcasts for insanity defense and competency. Examples: Adams' involuntary commitment (ep 389193 s2), a child in a psych ward (ep 178088 s0), "locked up, lobotomized" (ep 4112 s2), an insanity-defense setup (ep 70157 s2), Talkiatry reads (ep 324916 s0). No existing subtopic covers this. Involuntary commitment of the homeless is an active policy subject.

CHANGE `topic:mental.causes_models`:
| causes_models | Causes & models of mental illness | General theories of what causes mental illness (trauma, perception, inflammation, metabolism and diet, chemical imbalance, social determinants, spiritual or demonic causes) not tied to one disorder. | chemical imbalance theory; root of mental illness; metabolic psychiatry; nutritional psychiatry; social determinants of mental health; biopsychosocial model |
Why: metabolic and nutritional psychiatry appears in 288 eps / 58 podcasts (Chris Palmer, ep 176667 s5) and is not in the examples. Demonic versus "natural" causes come up in religious shows (ep 33413 s7).

CHANGE `topic:neurodevelopment.adhd`:
| adhd | ADHD | ADHD diagnosis, prevalence and treatment, including prescribed stimulant medication, shortages and prescribing. Stimulants taken without ADHD to study or work go to `cognition.nootropics`; party or recreational use to `drugs_addiction.stimulants_illicit`; similes ("like I took an Adderall") are not health content. | ADHD; adult ADHD; Adderall; Ritalin; Vyvanse; stimulant shortage; ADHD overdiagnosis |
Why: most of the 2,039 Adderall eps are non-medical: study use (ep 195985 s3), party use and jokes (KILL TONY, 113 eps), and similes (ep 94824 s0).

CHANGE `topic:neurodevelopment.neurodiversity`:
| neurodiversity | Neurodiversity & living with autism | Neurodivergence as identity, culture and accommodation, and the everyday experience of autistic people and their families: adult and late diagnosis, masking, support needs, nonverbal communication, school and work. Causes and rates go to `neurodevelopment.autism_causes_prevalence`; therapies to `neurodevelopment.autism_treatment`. | neurodivergent; neurodiversity; autistic masking; late autism diagnosis; nonverbal autistic child; autism mom; autistic identity |
Why: lived-experience content has no clear home. Late diagnosis, adult autism and ADHD, autism parents and nonverbal: 1,447 eps / 190 podcasts (noisy). There is a dedicated show (Tony Mantor, 234 autism eps; ep 156638 s23, ep 156467 s8, ep 156500 s49).

CHANGE `topic:neurodevelopment.developmental_delays`:
| developmental_delays | Developmental delays, learning disabilities & tic disorders | Speech, motor and learning delays, learning disabilities, intellectual disability, and childhood-onset tic disorders (Tourette's, functional tics). Genetic syndromes (Down syndrome) go to `genetics.genetic_conditions`. | speech delay; dyslexia; developmental milestones missed; learning disability; intellectual disability; Tourette's; TikTok tics |
Why: Tourette's has 546 segs, including functional "TikTok tics" (ep 9660 s318), but tics are missing from the name. Down syndrome (373 eps) collides with genetics.

CHANGE `topic:stress.stress_burnout`:
| stress_burnout | Stress & burnout | Stress, chronic stress and burnout and their effects on health, including "cortisol" used colloquially to mean stress ("don't spike your cortisol"). Cortisol measured or discussed as a hormone goes to `endocrine.cortisol_adrenal`; a passing "I'm stressed" about an event is not health content. | chronic stress; burnout; stress kills; good stress vs bad stress; "spiking my cortisol" |
Why: spike/raise/lower-cortisol phrasing is in 597 eps / 104 podcasts, much of it as slang ("You don't want to spike your cortisol", ep 156799 s3). Everyday "stressed" dominates the 51k "stress" episodes.

CHANGE `topic:stress.nervous_system_regulation`:
| nervous_system_regulation | Nervous-system regulation | The vocabulary and practices of nervous-system regulation, including vagus-nerve stimulation devices worn for calm or sleep (also `biohacking.devices_gadgets`). | vagus nerve; fight or flight; polyvagal; somatic therapy; dysregulated nervous system; EFT tapping; vagus nerve stimulator; NeuroPod |
Why: the bare example "tapping" mostly matches non-health uses ("tapping into that", BJJ tapping). The many vagus-device reads (NeuroPod, ep 185281 s1; Apollo Neuro, ep 200717 s0) are not mentioned.

CHANGE `topic:stress.nature_grounding`:
| nature_grounding | Nature exposure & grounding | Time outdoors and physical contact with the earth (earthing) as health practices, and products sold for it. "Grounding" meaning calming or stabilizing is not this label. | earthing; grounding mat; grounding sheets; forest bathing; barefoot on the grass; nature time; green space |
Why: of 10 sampled "grounding" hits, only one was earthing ("grounding his feet in buckets of dirt for electrical balance", ep 196333 s8). The rest were figurative ("felt grounding", ep 87395 s0) or NFL "intentional grounding".

CHANGE `topic:stress.mind_body`:
| mind_body | Mind-body connection | Emotions, beliefs, trauma, social connection and psychological state said to affect physical illness, immunity or recovery (psychoneuroimmunology, psychosomatic illness). "Mind-body connection" as product slogan or as a description of yoga or lifting technique is not this label. | molecules of emotion; isolation weakens immunity; psychoneuroimmunology; psychosomatic illness; emotions stored in the body; beliefs and healing |
Why: 486 of the 1,159 mind-body-term episodes are one GNC pre-workout read ("an intense mind-body connection", ep 21013 s10). Real uses: ep 159164 s3, ep 181023 s2 ("I do believe in psychosomatic illness").

ADD `topic:sleep.dreams_parasomnias` under `sleep`:
| dreams_parasomnias | Dreams, parasomnias & narcolepsy | Dreams and dreaming (lucid dreaming, nightmares, dream meaning as a sleep or mental phenomenon), parasomnias (sleep paralysis, sleepwalking, night terrors, sleep talking) and narcolepsy. The meme "sleep paralysis demon" for a person is not health content. Restless legs goes to `neuro.other_neurological`. | lucid dreaming; recurring nightmares; sleep paralysis; sleepwalking; night terrors; narcolepsy |
Why: sleep paralysis 325 eps / 61 podcasts, often given demonic or paranormal readings (Morbid ep 1822 s1; Rotten Mango ep 161771 s8; a clinical take on Short Wave ep 609379 s1). Lucid dreaming, nightmares and dream meaning: 587 eps / 124 podcasts. Narcolepsy: 322 / 110. All of it now falls to bare `topic:sleep`.

CHANGE `topic:cognition.focus_productivity`:
| focus_productivity | Focus & attention | Concentration and attention as a capacity of the brain that is trained, impaired or improved (by sleep, diet, practices, substances or devices). Productivity methods, work habits and "attention span" as a cultural complaint with no health claim are not health content. | focus; ability to concentrate; attention span (as brain capacity); flow state (as brain state); mental clarity; executive function |
Why: of 12 samples, about 9 were non-health ("attention span of the average voter", ep 33545 s230; coaching "deep work", ep 47894 s2; marketing "flow state", ep 20750 s0).

CHANGE `topic:cognition.memory_learning`:
| memory_learning | Memory, learning & intelligence | Memory, learning and intelligence (IQ) in healthy people, including IQ as an outcome of an exposure (also the exposure's subtopic). Age-related change goes to `dementia_ageing.cognitive_ageing`; "low IQ" as an insult is not health content. | memory; learning; neuroplasticity; recall; IQ points; intelligence research |
Why: rule 1 needs an outcome home for recurring IQ-harm claims ("It lowers IQ in kids by as much as seven points", ep 55207 s15; "children lost twenty two IQ points during the pandemic", ep 11412 s1). Exposure-plus-IQ phrasing: 564 eps / 95 podcasts. Most of the 5,608 IQ episodes are insults (ep 48612 s1).

CHANGE `topic:cognition.nootropics`:
| nootropics | Nootropics & smart drugs | Substances and branded blends taken to enhance cognition, including prescription stimulants or modafinil used without a diagnosis to study or work. A single herb or compound keeps its `supplements` home as well (rule 8). Methylene blue for other purposes goes to `medications.repurposed_offlabel`. | nootropics; modafinil; racetams; Alpha Brain; Magic Mind; Adderall to study; methylene blue for cognition; lion's mane for focus |
Why: matches the `adhd` change. Branded blends dominate the 1,662 episodes (Alpha Brain, ep 325339 s0; Magic Mind, ep 187378 s2).

CHANGE `topic:cognition.brain_fog`:
| brain_fog | Brain fog | Brain fog as a symptom and its causes. When the fog is discussed in its own right alongside its cause (menopause, long COVID, a diet), also code the cause's subtopic; as one item in a symptom or ad-benefit list it follows the list rules. | brain fog; mental fog; can't think clearly; foggy |
Why: 3,218 eps, mostly in menopause, long-COVID and NAD symptom lists (ep 190541 s9, ep 181980 s4) and ad benefit lists (ep 39138 s2, ep 192608 s0). The current definition gives no co-labeling guidance.

CHANGE `topic:cognition.neurochemistry_talk`:
| neurochemistry_talk | Dopamine & neurotransmitter talk | Popular talk about dopamine, serotonin and other neurotransmitters as levers of behavior or mood, when the brain chemistry is the point. "Dopamine hit" as a metaphor for a reward feeling (paying off debt, getting clicks) is not health content. | dopamine hit; cheap dopamine; dopamine detox; dopamine fasting; serotonin "happy hormone"; "90% of serotonin is made in the gut" |
Why: "dopamine hit / cheap dopamine" phrasing is in 1,335 eps / 158 podcasts, while the listed "dopamine detox/fasting" is in only 76 eps. Many uses are metaphor (ep 331089 s360, ep 58383 s10).

CHANGE `topic:cognition.digital_media_brain`:
| digital_media_brain | Screens, social media & the brain | Effects of phones, screens and social media on attention, mood, sleep-independent wellbeing and development, and the policies aimed at them (phone-free schools, age limits and bans for children). Compulsive use treated as an addiction or disorder goes to `mental.behavioral_addictions`. "Screen time" meaning TV airtime and "brain rot" as an insult are not health content. | screen time (kids); social media and teens; The Anxious Generation; phone-free schools; under-16 social media ban; smartphones and attention |
Why: about 3,456 eps. Noise includes "screen time" as TV airtime (ep 322508 s1) and "populist brain rot" (ep 325198 s12). The policy content (ep 204177 s0, Haidt in ep 29343 s1) is not mentioned.

## Codebook and prompt notes

1. **Section 3, "Exclude", psychiatric words (replace the single bullet with a test plus examples).** Proposed text: "Psychiatric or medical words used as insults, character judgements, slang or exaggeration are not health content. The test: is the speaker stating that a real person has, or had, a condition or state (health content, usually `passing`), or using the word to evaluate, intensify or joke? Excluded examples, all common in the corpus: 'narcissist', 'psycho', 'sociopath', 'malignant narcissist' about a politician or celebrity; 'a little OCD'; 'one of my intrusive thoughts' (a hot take); 'PTSD from that game'; 'I'm so depressed we lost'; 'give me a Xanax'; 'like I took an Adderall'; 'so autistic' as a jab; 'low IQ'; 'brain rot'; 'lobotomized'; 'sleep paralysis demon'; 'dopamine hit' for any pleasure." Evidence: insults or slang in 12 of 14 sampled narcissist hits and 12 of 14 psychopath/sociopath hits; Ringer Fantasy Football "intrusive thoughts" (65 eps); 378 eps of "a little OCD"; 2,684 eps of "so/I'm depressed"; ep 9545 s71, ep 90670 s4, ep 94824 s0, ep 194739 s2, ep 48612 s1, ep 44442 s2.

2. **Section 3, real people's emotions in narration.** Extend the fiction bullet: "Likewise, emotions of real people narrated as part of a story (a grieving family, a nervous suspect, a 'traumatized' witness) are not health content unless the window discusses the psychological state itself, names a condition, or describes care for it." Evidence: grief, anxiety and trauma words in true crime and news dominate the samples (ep 389696 s1, ep 603490 s3, ep 161868 s3, ep 24989 s8).

3. **Section 5.1, "Unsettled facts about a person", armchair diagnosis.** Add: "A psychiatric or cognitive diagnosis attributed to a public figure from afar ('he has dementia', 'clinically a malignant narcissist') is health content only when stated as a factual claim about the person's health, not as an insult. Code the condition's subtopic, `passing` unless argued, confidence 0.6 or less, and the summary says 'speaker's attribution'. Debate about whether diagnosing from afar is legitimate (the Goldwater rule) is `health_system.ethics_law_privacy`." Evidence: 450 eps / 67 podcasts of malignant-narcissist, Goldwater and armchair talk, concentrated in political shows (ep 15967 s7, ep 6892 s3).

4. **Section 3, "Ads", and 4.1, mental-health ads.** Add a worked line: "A therapy or psychiatric-telehealth read (BetterHelp, Talkspace, Talkiatry, NOCD) is `mental.therapy` or `mental.psychiatric_care`, `advertisement`; the conditions it lists ('can treat anxiety, ADHD, depression') are a list inside one read and take no extra topic. Emotion words in ads for non-health products ('that uneasy, anxious feeling about your insurance', 'your daily anxiety disappears') fail the ad test." Evidence: BetterHelp 9,927 segs; therapy-app reads in 13.5k eps / 300 podcasts; the insurance ad's "anxious feeling" line recurs across Dateline, Hidden Brain and KILL TONY (ep 194710 s6, ep 170492 s3, ep 159384 s0); the Talkiatry list (ep 324916 s0).

5. **Section 3, sportsbook boilerplate.** Gambling-helpline boilerplate is already excluded. Add that "Gambling problem? Call 1-800-GAMBLER" is the most frequent form, since it appears in about 5,000 eps of sports, comedy and self-help shows (Passion Struck 592, Bill Simmons 591, Pardon My Take 548).

6. **New short rule (section 3 or 5.1), delivered practices.** "When the window delivers a practice to the listener (a guided meditation, breathing exercise, sleep hypnosis or sleep story) rather than talking about it, code one detection for the practice (`stress.meditation_mindfulness`, `stress.breathwork`, and `sleep.sleep_duration_quality` only when sleep is the stated purpose), `substantive`, over the delivered stretch. Do not label the script's imagery words (fear, grief, inner child) as separate topics. Show taglines and sleep-induction cues alone ('as you drift deeper into sleep tonight') get nothing." Evidence: Meditation for Anxiety (1,479 eps; ep 203191 s1, ep 202860 s1); Boring History For Sleep (ep 324266 s2839); Sleep Magic hypnosis (123 eps).

7. **Section 5.1 co-labeling rule 1, ads with a condition indication.** The Zepbound OSA read ("moderate to severe obstructive sleep apnea… in adults with obesity", 262 eps on The Bulwark Daily) should take `glp1.use_results` (or the GLP-1 subtopic for indications) plus `sleep.apnea_breathing`. The approved indication is the ad's subject, not a "purpose" mention. A one-line worked example would settle it.

8. **Section 5.1, "General talk".** Add "'mental health' in general is `topic:mental`" next to the existing "brain health" line. It is the most common phrasing in the slice (23,849 eps) and currently has no stated rule.

9. **Narrative note (for the narrative reviewers).** "Mass shootings are a mental-health problem, not a gun problem" recurs: mental illness or mental health within 80 characters of shooting or gun terms gives 577 eps / 106 podcasts (ep 39721 s0, ep 9271 s2). So does "the body keeps the score" (trauma stored in the body) (about 780 eps of related phrasing, contested in-corpus, ep 159164 s3). Neither is a listed narrative, and both would currently go to `unlisted_narrative`. I am not proposing them here, because narratives are outside this slice.
