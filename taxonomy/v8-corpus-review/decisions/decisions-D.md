# Group D decisions: reports 07 (mind, sleep) and 08 (reproductive, gender, pediatrics)

Patch: `patch-D.jsonl` (43 changes, 3 adds, 0 removes, 1 parent edit). Validated with
`apply_patches.py` into `check-D.md` and `tl.compile_taxonomy`. Every backticked reference
resolves after the patch.

## Report 07: mind, brain and sleep

ACCEPT  parent topic:mental  (not a numbered proposal; from codebook note 8) added "General "mental health" with nothing more specific takes this parent", matching the cardiovascular and gut parents. "mental health" is the slice's most common phrase (23,849 eps).
MODIFY  topic:mental.depression  accepted the momentary-reaction exclusion (2,684 eps of "so/I'm depressed"). Removed the backtick from the examples cell; the postpartum co-label now sits in `pregnancy.postpartum`.
MODIFY  topic:mental.anxiety  accepted "ongoing condition or symptom" plus the ordinary-worry exclusion. Left the non-health ad-copy clause out of the row because the codebook ad test already handles it.
MODIFY  topic:mental.trauma_ptsd  accepted repressed and recovered memories (554 eps / 92 podcasts), "the body keeps the score", and the TBI and physical-trauma boundaries. Replaced the hyperbole clause with a pointer to `stress.mind_body` for trauma said to cause physical illness, so the two labels split cleanly.
MODIFY  topic:mental.ocd_personality  accepted psychopathy and the insult/slang exclusions (12 of 14 samples were insults; "intrusive thoughts" is used as sports slang). Merged in report 08's routing of general body dysmorphia here: BDD is an OCD-related disorder and has 633 eps with no home.
MODIFY  topic:mental.wellbeing_grief_loneliness  added bereavement examples and one short story-narration clause. The general rule goes to the codebook (note 07-2).
MODIFY  topic:mental.pop_psychology  accepted narcissist self-help (246 eps / 75 podcasts) and overdiagnosis claims (826 eps / 137 podcasts), with the three-way narcissist boundary. Added that overdiagnosis of one disorder also takes that disorder's subtopic, so it does not clash with the `adhd` example "ADHD overdiagnosis".
MODIFY  topic:mental.behavioral_addictions  accepted the disorder threshold and the casual-phone-use boundary. Dropped the NoFap example because it collides with `manosphere.semen_retention_nofap`. Sportsbook boilerplate is codebook material (already excluded).
ACCEPT  topic:mental.psychiatric_care (ADD)  ~4,050 eps / 256 podcasts for hospital, commitment and system terms, plus 1,312 eps / 136 podcasts for insanity defense and competency. Distinct from every existing subtopic, and involuntary commitment is an active policy subject. Added a boundary sending ketamine and psychedelics to `psychoactives`.
MODIFY  topic:mental.causes_models  added metabolic and nutritional psychiatry (288 eps / 58 podcasts). Did not add "spiritual or demonic causes": it rests on a single exorcist interview, and the cited episode is actually about hypothyroidism.
ACCEPT  topic:neurodevelopment.adhd  boundary for non-medical stimulant use: study use to `cognition.nootropics`, party use to `drugs_addiction.stimulants_illicit`, and similes are not health content. Most of the 2,039 Adderall eps are non-medical.
ACCEPT  topic:neurodevelopment.neurodiversity  lived experience of autism, late diagnosis and autism parents (1,447 eps / 190 podcasts, noisy). Changed the name only; the ID is unchanged.
MODIFY  topic:neurodevelopment.developmental_delays  added tic disorders to the name and the Down syndrome → genetics boundary. Added that adult-onset tics go to `neuro.other_neurological`, which already lists "tics in adults".
MODIFY  topic:stress.stress_burnout  accepted colloquial "cortisol" (597 eps / 104 podcasts) with the hormone boundary. Left the "passing I'm stressed" clause out of the row because it is codebook material (loose emotion words).
ACCEPT  topic:stress.nervous_system_regulation  replaced the bare example "tapping" with "EFT tapping" and added the vagus-nerve devices (NeuroPod, Apollo), co-labeled with `biohacking.devices_gadgets`.
ACCEPT  topic:stress.nature_grounding  only 1 of 10 "grounding" samples was earthing; added the figurative-use exclusion and more specific examples.
ACCEPT  topic:stress.mind_body  added psychosomatic illness and stored emotions, and excluded the slogan sense (486 eps come from one GNC read).
MODIFY  topic:sleep.dreams_parasomnias (ADD)  sleep paralysis (325 eps / 61 podcasts, often given demonic readings), dreams (587 / 124) and narcolepsy (322 / 110): a recurring, distinct subject with misinformation interest. Added "whatever explanation is offered" and "recounting what happened in a dream is not health content", so that ordinary "I had a dream…" talk does not flood the label. The "sleep paralysis demon" meme moved to the codebook idiom list.
MODIFY  topic:cognition.focus_productivity  tightened to attention as a brain capacity (about 9 of 12 samples were non-health) and renamed to "Focus & attention". The ID is kept, since it is not actively misleading.
ACCEPT  topic:cognition.memory_learning  IQ becomes an outcome home under rule 1 (fluoride and pandemic IQ claims; 564 eps / 95 podcasts). Renamed, plus a boundary to `developmental_delays` for intellectual disability.
ACCEPT  topic:cognition.nootropics  branded blends (Magic Mind) and study-drug stimulant use, consistent with the `adhd` change. Did not restate rule 8 in the row.
MODIFY  topic:cognition.brain_fog  kept the co-label sentence and dropped the list-rule sentence, which only repeats codebook rule 6.
ACCEPT  topic:cognition.neurochemistry_talk  "dopamine hit" phrasing (1,335 eps) replaces the rare "dopamine detox" (76 eps) at the head of the examples, plus a metaphor exclusion.
MODIFY  topic:cognition.digital_media_brain  accepted the policy scope (phone-free schools, under-16 bans) and the noise exclusions. Removed the garbled "sleep-independent wellbeing" and the "brain rot" example.

## Report 08: reproductive, gender, pediatrics

ACCEPT  topic:womens.hormone_therapy  "HRT" acronym boundary: HRT co-occurs with TRT in 314 of 609 HRT episodes, and it also means trans HRT. Added vaginal estrogen. Dropped the "bioidentical non-hormone drug" clause because it is a single instance.
ACCEPT  topic:womens.menstrual_cycle  amenorrhea and RED-S (98 eps / 33 podcasts).
ACCEPT  topic:womens.pcos  PMOS, the condition's new name, as an example.
MODIFY  topic:womens.period_products  replaced the near-absent example "heavy metals in tampons" (2 eps) with the phrasing that actually occurs. Kept the jokes and "Tampon Tim" political exclusion out of the row, since it belongs to the political-token codebook rule.
MODIFY  topic:womens.pelvic_floor  added leaks and stress incontinence. Scoped incontinence to pelvic-floor weakness and pointed other bladder problems to `kidney_lung.kidney_urinary`, which already lists "incontinence".
MODIFY  topic:pregnancy.pregnancy_health  added pregnancy loss, stillbirth, ectopic pregnancy and the abortion-law co-label (5643/0, 84267/4). Moved "miscarriage of justice" (an idiom) to the codebook.
ACCEPT  topic:pregnancy.postpartum  co-label pointers for postpartum depression, psychosis and hair loss (about 1,020 eps of postpartum mental illness).
MODIFY  topic:pregnancy.maternal_mortality_access  absorbs infant mortality (548 eps / 104 podcasts, usually paired with maternal mortality). Dropped the absent examples (maternity care deserts: 2 eps; obstetric violence: 1) and the uncounted "labor and delivery closures". The SimpliSafe "maternity ward" line is ad-test material for the codebook.
ACCEPT  topic:fertility.contraception  Opill, the male pill and Title X access programmes.
MODIFY  topic:fertility.abortion  added access and arguments over abortion itself, plus the miscarriage and ectopic co-label. The electoral-token exclusion (about 13 of 18 samples) goes to the codebook, not the row, as the brief requires.
ACCEPT  topic:sexual.sexual_function  porn-induced ED (1,189 eps of porn near ED, libido or addiction) with the porn-addiction boundary, plus "ED treatments" (Hims reads).
MODIFY  topic:mens.testosterone  added andropause (148 eps) and "HRT for men". The political-trope boundary now reads "named only as a marker of manhood or politics", so stated claims about declining levels still take this label. Fantasy-football "low T" goes to the codebook idiom list.
MODIFY  topic:mens.genital_health  newborn circumcision now goes only to `pediatrics.infant_care`, ending the double listing. The scripture exclusion is already covered by the codebook fiction/scripture rule.
ACCEPT  topic:manosphere.semen_retention_nofap  dropped "monk mode" (62 eps, a productivity idea).
MODIFY  topic:manosphere.looksmaxxing  dropped "heightmaxxing" (4 eps) and added "mogging" and "leg lengthening surgery".
ACCEPT  topic:manosphere.masculinity_ideology  requires a claim about men's bodies or health. Only ~161 of 4,070 raw episodes are health-linked.
MODIFY  topic:manosphere.male_body_image  general body dysmorphia now goes to `mental.ocd_personality`, merged with the 07 change. Narrowed the trans-debate pointer to "invoked to explain gender dysphoria".
ACCEPT  topic:gender.youth_gender_medicine  added WPATH, Skrmetti, "gender-affirming care for kids" and guidelines. Cass Review alone appears in only 12 eps.
ACCEPT  topic:gender.adult_transition  added "sex change", the common lay term, and the rule that procedures with no age stated go here.
ACCEPT  topic:gender.lgbtq_health  added claims about the origins of sexual orientation (437 eps / 119 podcasts, broad query). Widening an existing label is better than adding a new one.
MODIFY  topic:gender.trans_athletes (ADD)  333 eps across 10+ podcasts discuss trans athletes with physiology, and no current label fits. Renamed to "Transgender & DSD athletes" and kept one threshold sentence so that the bare slogan stays out.
ACCEPT  topic:pediatrics.infant_care  added NICU, co-sleeping and newborn circumcision, plus the infant-mortality-rate boundary.
MODIFY  topic:pediatrics.pediatric_care  accepted the vaccine boundary to `vaccines.uptake_hesitancy` (1,081 of 1,908 pediatrician episodes mention vaccines). Dropped the example "pediatric chiropractic" because chiropractic belongs to `alt_medicine.chiropractic`.
REJECT  topic:fertility.birth_rates  "swap pronatalism for declining birth rate phrasing": the report itself calls this cosmetic and makes no proposal. Not patched.

## Codebook

From 07 (mind, sleep):
- **§3 Exclude: test for psychiatric words** (07 note 1). Insults, character judgements, slang and exaggeration are excluded. The test is whether the speaker states that a real person has a condition or uses the word to evaluate, intensify or joke. Add corpus-attested examples: "narcissist", "sociopath", "malignant narcissist" about a politician, "a little OCD", "one of my intrusive thoughts", "PTSD from that game", "I'm so depressed we lost", "give me a Xanax", "like I took an Adderall", "so autistic" as a jab, "low IQ", "brain rot", "lobotomized", "sleep paralysis demon", "dopamine hit" for any pleasure. Evidence: 12 of 14 samples were insults for both the narcissist and psychopath terms; 65 eps of "intrusive thoughts" on Ringer Fantasy Football; 2,684 eps of "so/I'm depressed".
- **§3: real people's emotions narrated in a story** (07 note 2). Grief, fear or trauma words in true crime and news are not health content unless the state itself is discussed, a condition is named, or care is described. This mirrors the fiction rule. Evidence: ep 389696 s1, 603490 s3, 161868 s3.
- **§5.1 Unsettled facts: armchair diagnosis** (07 note 3). A sustained factual attribution of a condition to a public figure is coded at ≤0.6 confidence and the summary says "speaker's attribution"; an insult is excluded; Goldwater-rule debate goes to `health_system.ethics_law_privacy`. 450 eps / 67 podcasts.
- **§3 Ads: mental-health reads** (07 note 4). BetterHelp, Talkspace, Talkiatry and NOCD reads are `mental.therapy` or `mental.psychiatric_care` with relevance `advertisement`; conditions listed inside the read take no extra topic. Anxiety words in ads for non-health products ("that uneasy, anxious feeling about your insurance") fail the ad test. Therapy-app reads appear in 13.5k eps / 300 podcasts.
- **§3: sportsbook boilerplate** (07 note 5). Name "Gambling problem? Call 1-800-GAMBLER" as the common form (~5,000 eps).
- **Delivered practices** (07 note 6). A guided meditation, breathing exercise, sleep hypnosis or sleep story gets one practice detection over the delivered stretch, and the script's imagery takes no labels. Meditation for Anxiety has 1,479 eps.
- **Rule 1 worked example: an approved indication in an ad** (07 note 7). The Zepbound OSA read takes `glp1.use_results` + `sleep.apnea_breathing` (262 eps on The Bulwark Daily).
- **"General talk": "mental health" → `topic:mental`** (07 note 8). Also added to the parent definition in the patch.

From 08 (reproductive, gender, pediatrics):
- **§3: political-token exclusion** (08 note 1; highest priority in this slice). Abortion, trans issues, "men in women's sports", birth rates and "Tampon Tim" named only as electoral issues or list items, with nothing about a procedure, access, the body or a health consequence, are not health content. A legal or moral argument about the subject itself is health content. Evidence: abortion matches 11,826 eps, ~13 of 18 samples were electoral; trans sports matches 691 eps, about half with no physiology.
- **§3 Ads: worked outcomes** (08 note 2). MIDI Health menopause telehealth → `womens.menopause` with relevance `advertisement` and a `clinic_or_practitioner_service` product. Hims and Roman ED reads → `sexual.sexual_function`. A Planned Parenthood Title X advocacy read passes the ad test (`fertility.contraception`) but records no product unless a service is offered to the listener. A Garnu organic-tampon read → `womens.period_products` + `frame:naturalness_appeal`, not `narrative:tampon_toxins` (implicature rule (a)). A non-health show cross-promo that names "bans on conversion therapy" fails the ad test; without this rule it inflates `lgbtq_health`, since Pod Save America accounts for 363 of its eps.
- **Ambiguous terms and ASR list** (08 note 3). "HRT" can mean Hostage Rescue Team; "PrEP" can mean meal prep; "low T" is fantasy-football slang; "Plan B" and "the pill" are also idioms; "miscarriage of justice" (396 eps); "maternity ward" is a SimpliSafe slogan (275 eps); "HIV" can be an ASR error for HEV light; "Calman" is an ASR error for Kallmann; PMOS is PCOS's new name.
- **Rule 9 reproductive cases** (08 note 4). Postpartum depression or psychosis → `pregnancy.postpartum` + the `mental` subtopic. Postpartum hair loss → + `skin_beauty.hair_loss_hair`. Infertility named once as a cancer-treatment side effect falls under rule 6.
- **Rule 3: miscarriage or ectopic care under abortion bans** → `fertility.abortion` + `pregnancy.pregnancy_health` (08 note 5). This is also stated in both rows.
- **§3 fiction and scripture: circumcision in Bible-reading podcasts as an example** (08 note 6; 305 eps). An OB-GYN credential in an intro is `evidence:credential_appeal` when it is offered as grounds, never a `womens` topic.
- **Political testosterone talk** (08 note 7). "They want weak men… our testosterone rates are going down" takes `narrative:testosterone_collapse` + `frame:political_partisan`, with topic `manosphere.masculinity_ideology`. I differ from the report on one point: add `mens.testosterone` when levels or treatment are discussed beyond the slogan.
- **§5.5: trans debates** (08 note 8). "Trans kids" takes `population:lgbtq` + `population:children` or `population:adolescents`. A single detransitioner's own story takes neither.

## Cross-slice notes

- `narrative:trans_identity_disorder` (narratives slice; 08 note 9). Its row says "gender ideology" belongs to the narrative. Used as a plain political noun ("corporations that promoted gender ideology", 206372/5), it should take only `frame:political_partisan`, not the narrative. The row and its example need a boundary sentence. Not patched.
- Candidate narratives for the narrative reviewers (07 note 9). (a) "Mass shootings are a mental-health problem, not a gun problem": 577 eps / 106 podcasts with mental illness or mental health near shooting terms. (b) "Trauma is stored in the body / the body keeps the score": ~780 eps of related phrasing, contested in the corpus. Both currently fall to `unlisted_narrative`.
- `kidney_lung.kidney_urinary` lists "incontinence". The pelvic_floor change claims pelvic-floor and stress incontinence. The kidney_urinary owner may want a reciprocal sentence ("leaks from pelvic-floor weakness go to `womens.pelvic_floor`").
- `biohacking.devices_gadgets` lists Apollo. The `stress.nervous_system_regulation` row now says wearable vagus-nerve devices take both labels; the biohacking row could say the same.
- `acute_care.violence_abuse` lists "narcissistic abuse". The new pop_psychology boundary keeps it there when abuse is discussed as harm and sends "how to spot a narcissist" self-help to pop_psychology. This is consistent, so no change is needed.
- `oral.water_fluoridation` lists "fluoride and IQ studies". Under rule 1, fluoride-IQ claims now also take `cognition.memory_learning`. The codebook rule 1 examples could name it.
- `health_system.dtc_telehealth` vs the new `mental.psychiatric_care` (Talkiatry): a psychiatric telehealth read takes psychiatric_care alone, adding dtc_telehealth only when the DTC model itself is discussed. This mirrors the glp1.access_compounding rule; the codebook or the dtc_telehealth row could state it.
