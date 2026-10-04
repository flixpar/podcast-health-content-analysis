# Codebook v8 changes from the corpus review

Files changed: `taxonomy/codebook-v8.md` (7,925 → about 14,200 words) and
`analysis/prompts/rubric-v8.md` (procedure step 1 and step 5 only; the worked
example is unchanged and still validates against both the installed and the
merged label set). Sources: reports `NN-*.md` (cited as "report NN, note n")
and decision logs `decisions-*.md` (cited as "A3" = decisions-A, Codebook
item 3). Reports 02 and 10 did not exist when this was written; decisions-B
(report 03) arrived mid-edit and is incorporated.

## Section 2, ground rules

- "died suddenly" and "jab injured" removed from the list of coined terms that
  carry a proposition (F1-1; report 12 note 1).
- New lists of recurring mishearings and ambiguous words, merged from A6,
  B8, C11, D (08 note 3), E15, F1-8; reports 01 note 5, 03 note 8, 04 note 6,
  05 note 9, 06 note 9, 08 note 3, 11 note 6, 12 note 8. Lookalike word senses
  that were scattered across the exclusion proposals (Cancer the zodiac sign,
  Mercury, Coke, Molly, Celsius, "mold", "parasite", "miscarriage of
  justice", "maternity ward", "BBL", "detox" senses, "non-alcoholic fatty
  liver") moved here. Keyword-search noise (`\bepa\b`, "Warburton",
  "Poughkeepsie", etc.) left out: it is analyst tooling, not labeling.

## Section 3, health-content scope (restructured into 3.1-3.4)

- Opening test ("about a body, a mind… as such") with the old "would a
  researcher want this counted" question moved up (G2 evidence: 22% of blind
  hits not health content, report 15).
- 3.2 boundary tests, each with a test and corpus examples:
  - COVID/pandemic/lockdown/quarantine as a time marker (A1; report 01 note 1:
    8 of 14 samples, ~43k episodes; lockdowns_closures row).
  - Violence, crime, war and death rewritten to match the `topic:acute_care`
    parent definition in merged-partial word for word on the core sentence
    (C1; report 06 note 1: 16,519 episodes of forensic vocabulary). Added:
    rape told as a crime event is the event test; allegations and trials are
    not health content; death with no cause excluded (G2-5); a death or
    illness from a named disease is one `passing` detection of that disease in
    any genre, without `death_dying` (C6; report 04 note 4; matches the
    merged `death_dying` row); historical epidemics follow the history default
    (A7); circumcision in Bible reading (D, 08 note 6).
  - Sports injuries and "healthy" meaning available (C2, G2-2; 8,887 and
    3,683 episodes).
  - Alcohol, drugs, tobacco and caffeine in everyday talk (E1, E2; report 09
    note 1: 1-2 in 10 comedy hits are health content). Note for the benchmark
    owner: E1 says gold items c178291w0010, c95062w0004, c3505w0007 and
    c154859w0023 need re-adjudication under this rule.
  - Psychiatric and emotion words: one test plus attested include/exclude
    examples (D 07 note 1; 12 of 14 narcissist and psychopath samples were
    insults); real people's emotions in a story (D 07 note 2); pointers to
    armchair diagnosis (5.1) and generic "mental health" (G2-1).
  - Political issue lists (D 08 note 1: ~70% of sampled abortion hits; E7 RFK
    candidacy; G2-7 "healthcare" as a list item; G1-7 trans athletes, now
    `gender.trans_athletes`).
  - Self-help "healing" (G2-3) and delivered practices (G2-4, D 07 note 6).
    Resolved the conflict between them: one `passing` detection per window
    (G2), sleep stories to `sleep.sleep_hygiene_environment` (G2), imagery
    unlabeled and induction cues alone get nothing (07).
- 3.3 ads: brand names are not claims ("Zero Sugar", G1-1; 7,763 episodes);
  substance products (E3); cosmetic, hair and household products (E10);
  mattresses pass only with a stated benefit (my reading of the existing test
  (b), consistent with report 07's `sleep_hygiene_environment` finding);
  failing cases gathered into one bullet: eligibility lists (C5), insurance
  marketplaces and non-health insurance (G2-6, E9), emotion words in
  non-health ads (D 07 note 4), parody copy (G1-4), gambling helpline (D),
  satirical or policy cross-promos (E11, D 08 note 2e), insect traps and spray
  tans (E15), household mold (A5); passing cases: retailers (G1-2), unbranded
  awareness spots with `frame:commercialization` kept (G1-3), advocacy reads
  (D 08 note 2c), health-show promos (E11), meat "never antibiotics" (A4).
- 3.4 exclusions: idiom list extended and grouped (A5, C3, E2, E15, F1-9, G2
  item 12); show taglines and mission statements (A5, G1-5); frame vocabulary
  outside health (G1-6); crime and genealogy DNA (A5); BCI as technology (C3);
  pet-food ads under animal health (E14).

## Section 4.1, detections and ads

- Ad delimitation: a read ends after its last line of copy; back-to-back
  spots; "Brought to you by" tags; host reads that continue (G1-8; report 14:
  return transitions a third as frequent as openings). Dynamic insertion:
  never use the episode date or subject (B7, C13; reports 03 note 7, 04 note
  3), phrased as a labeling rule.
- Topics inside ads: multi-ingredient rule (B1); benefit lists of three or
  more take only the product's subtopic (A3, signed off here); energy and focus
  puffery (E13); clinic reads with distinct treatments vs bare service lists
  (B6); therapy and telehealth condition lists (D 07 note 4); drug-ad safety
  information adds no topics, claims or narratives (A2, C4, F2-5, G1-32);
  regulatory boilerplate is not `regulators` or `industry_quality` (E6, B5);
  contaminant attributes are `frame:toxin_purity` only (E12); audience lists
  (G1-10).
- Worked ad table (C10, D 07 notes 4 and 7, D 08 note 2, A4, A12, B
  electrolyte split, report 07 mattress volume, E3 substance products). Drug
  ads code the indication plus `medications.other_drugs` consistently (A2,
  report 05 note 1), so Nurtec gains `medications.other_drugs` relative to the
  C10 table.

## Section 5.1, topics

- Rule 1: fluoride and IQ (D cross-slice); outbreak blamed on low vaccination
  (report 01 note 6); approved indication as outcome (D 07 note 7);
  procedures (C8).
- Rule 3: miscarriage and ectopic care under bans (D 08 note 5); MAHA as an
  adjective and nominations (E7); pointer to 3.2 for issue lists.
- Rule 4: ad boilerplate (E6). Rule 5: functional foods, using B3's
  narrower version (vehicle only when discussed). Rule 6: societal lists (E4)
  and supplement routines (B10). Rule 8: homes outside supplements (B2),
  administration routes (E17), prescription drugs used non-medically, cannabis
  smoking, THC drinks (E5, G2-10). Rule 9: reproductive cases (D 08 note 4).
- General talk: "mental health" → `topic:mental` (G2-1, D 07 note 8; 23,849
  episodes); generic drug use (E4); cortisol and oxytocin (C9); supplement
  retailers and bare "peptides" (B4); practitioner titles (E14, D 08 note 6);
  caregiving (G2-9).
- Worked tie-breaks: possession, somatic memory, endocannabinoid (G2-11);
  political testosterone talk (D 08 note 7).
- Unsettled facts: tumours (G2-8, kept at the existing 0.6 cap), dementia
  speculation (C7), armchair diagnosis and Goldwater debate (D 07 note 3, G2-1),
  "is she on Ozempic" (C7), implied chronicity (A8).

## Section 5.2, narratives

- Coined terms vs slogans: "died suddenly" only as the coinage, "vaccine
  injured" as identity, and the slogan list "sick care", "gender ideology",
  "Great Reset", "terrain theory", "type 3 diabetes", "NoFap", "soy boy",
  chemtrails and flat earth as bywords (F1-1, F2-2, C12, D 08 note 9, E16).
- Verbs of benefit: property and prevention claims are not cure narratives
  (F1-3). Root-of-all-disease narratives vs single disease; leaky gut allowed
  a single disease (F2-8); NeuroPod "75-90 percent" ad copy at ~0.6 (A9).
- Ads: frame-only attributes vs disparaging copy, pharmacy ivermectin kits
  (F1-2, F2-5). Side effects and presence findings (F2-4). Folk use (F2-1).
  Grievance lists (F1-4). Policy news (F1-5). "They want us sick" routing
  (F2-3). Jokes and mockery with microchip, shedding, fluoride and chemtrails
  examples (F1-6, A10, E16); stimulant comedy (F2-6). Premise examples:
  `vaccines_for_profit` (F1-7) and "nutrient gap" lead-ins (B6). Co-occurrence
  (F2-9, D 08 note 7). `unlisted_narrative` examples: unpatentable remedies
  (B9) and mass shootings as mental health (D cross-slice, report 07 note 9).

## Section 5.3-5.5, frames, evidence, population

- Synced with the merged frame rows (G1-11 to G1-17): root cause as a method,
  neutral vs hyperbolic trend words, toxin_purity exclusions, new
  medical_freedom and anti_expert_populist bullets, "sickest generation",
  disclaimer covering ad boilerplate (side-effect list is not a disclaimer),
  commercialization on awareness spots, recurring taglines.
- Evidence (G1-18 to G1-20, B5, report 03 note 6): doctor-formulated and
  similar authorship formulas, "NSF certified for sport", "clinically
  studied", publication records as credentials, clinical experience "as
  grounds" and advice not counted, traditional_use vs foreign_comparison by
  past vs living populations, host testimonials in ads as anecdote.
- Population (G1-21, G1-22, D 08 note 8, A11, G1-7): new age words and the
  "young people" rule, sex plus age takes both, `racial_ethnic_groups`, trans
  kids, detransitioner stories, Havana syndrome, trans athletes.

## Section 6, discourse role

- Parody voicing is `rebutted` (F2-7); mock-quotes (report 11 note 9);
  qualified endorsement "I'm not against… per se, but" (E18).

## Section 7, claims and certainty

- Markers added (G1-23 to G1-25, report 14): absolute "for sure", "no doubt",
  "hands down", "certainly", "the reality is", "I'm telling you", "trust me",
  "a hundred percent", "it's well established that", "the science is clear
  that", sentence-final "period", etc.; hedged "I feel like", "in my opinion",
  "I'm pretty sure", "my guess is", "I suspect", "chances are", "most likely",
  "oftentimes", "in some cases", "certain people", etc.; speculative "perhaps",
  "I imagine".
- New rules: clause scope for "obviously/of course/clearly" (G1-29, the
  editor's generalization), negated boosters (G1-26), another speaker's
  agreement and health-state "a hundred percent" (G1-28), "suggests/indicates"
  hedged vs "shows/found" no marker, evidential frames not markers (G1-30,
  resolving the old conflict), "most likely" (G1-27), hearsay "supposed to"
  and ad "they say" (G1-31). Attribution rule (a) updated because "it's well
  known that" is now an absolute marker.
- Do not extract: drug-ad mandated safety statements (G1-32), host
  testimonials, volume testimonials and self-hedging copy (B6), speculation
  about a person's undiagnosed illness (G2-1), delivered-practice
  instructions (G2-4).

## Section 8, products

- product_type mapping for new kinds of product without changing the enum
  (G1-33, A12, E3, B electrolyte split, D 08 note 2): exercise and recovery
  equipment, eyewear and hearing aids → `device_or_wearable`; period and
  sexual-health products, toothpaste and aligners →
  `personal_care_or_cosmetic`; Opill, Systane, biologics, ivermectin kits →
  `medication`; ingestible hemp, CBD, THC and kratom → `supplement`, cannabis
  flower and vapes → `other_product`; apps and GoodRx →
  `app_or_digital_service`.
- Not products: retailers as sponsors, unbranded awareness campaigns,
  charities and advocacy organizations unless a service is offered (G1-33,
  D 08 note 2c). Branded equipment for a generic practice is a product.
- ASR repair examples (A6, C11, report 05 note 9).

## Section 10, common errors

- Rewritten around the review's volume findings: non-health uses of health
  words, ad reads leaking past their end, drug-ad safety statements and
  benefit lists, slogans as narratives, negated boosters and backchannel
  agreement; "bare crime words" replaced by "crime and war narration" (C1).

## Rubric (analysis/prompts/rubric-v8.md)

- Step 1: removed the stale "bare crime words ('murdered')" wording, added the
  3.2 boundary checklist (G2-12) and the end-of-read pointer (G1-9).
- Step 5: added racial and ethnic groups to the population list (G1-22).
- Worked example checked against the new rules (two sleep outcomes stay
  under the list threshold; "magnesium sleep drink" stays `supplement`); no
  change needed.

## Not adopted or deferred

- B6 "do your own research inside ad copy is not a frame by itself": the
  merged `frame:anti_expert_populist` row lists "go do your own research on
  NADH" as an example, so the codebook says nothing that contradicts the row.
  The label owner should settle it.
- Analyst-only notes (E8 DTC ads dominating `other_drugs`; C13/B7 dating ads
  by ingestion date; search-noise lists in F2-10, B8, F1-8) are not labeling
  rules and are not in the codebook.
- Report 03 note 6 "nutrient gap" check and note 9 narrative went in as 5.2
  examples only; no label references were invented for them.

## Second pass: report 10 (optimization) and the coordinator's ruling

Source: `10-optimization.md`, "Codebook and prompt notes" (cited "10-n").
New labels proposed by report 10 are not referenced.

- Section 2: ambiguous words "DNP", "AI" (aromatase inhibitor), "Tren",
  "Whoop", "don't die", and "Brian Johnson"/"Aura ring" read as Bryan Johnson
  and Oura for topics too (10-4; "Aura ring" 712 eps vs "Oura" 94).
- Section 3.2: new "Sports and exercise beyond injuries" test. Sports talk
  counts only when it describes a body (training, conditioning, recovery,
  weight cutting, eating, PEDs, physiology); training camp, pitch counts,
  workload, roster talk and "out of shape" do not; exercise as a setting
  ("before I hit the gym", "yoga pants") does not (10-1, 10-2; ~13,000
  sports-show eps; gym/workout/yoga in 25k/48k/9k eps).
- Section 3.4: "X on steroids" idiom (2,311 eps) and "health and longevity"
  sign-offs (10-3); the old "sports purely as competition" bullet now points
  to 3.2.
- Section 3.3: payment-accessory device mentions and workout-setting apparel
  ads fail; fitness services pass (10-5).
- Section 4.1: compliance lines (Hyman's Function Health employment
  disclaimer → `frame:disclaimer` only; Hers "AI responses" line adds no
  `digital_health.ai_advice`); "add it to your morning routine" is not an
  outcome (10-5, 10-6); longevity-clinic modality lists take only the clinic's
  subject, `longevity.protocols_clinics` (10-9, reconciled with B6's
  bare-service-list rule instead of coding each modality).
- Section 5.1: rule 1 example for "good for longevity" as a purpose vs
  lifespan discussed (10-7); senolytic supplements add
  `longevity.longevity_drugs` (10-8).
- Section 5.3: `frame:optimization` excludes "optimal ranges" in
  functional-lab talk (10-10). Coordinator ruling: ad copy saying "go do your
  own research" is not `frame:anti_expert_populist` on its own (the
  coordinator will remove that example from the frame row). This settles the
  B6 open item noted above.
- Section 5.5: one player's conditioning or PED accusation takes no
  `population:athletes`; leaguewide talk does (10-11).
- Section 10: training camp, workload and gym-as-setting added to the
  non-health uses.
- Rubric: the empty-output example adds "he'll get a full workload after
  training camp" (10-1).
- Not adopted: 10-6's outcome coding depends on the proposed
  `recovery.training_recovery` label (not referenced); 10-8's "NAD ad promising
  more energy → `wellness.energy_fatigue`" conflicts with the energy-puffery
  rule (E13) and was left out.

## Third pass: installed label set, recovery rule, report 02 (food/diets)

The merged label set is now installed as `taxonomy/health-v8.md`, so the six
merged-only references resolve. The codebook never referenced
`sleep.other_sleep_disorders`, so that merge needs no change.

- 4.1 stated outcomes: recovery claimed as an outcome ("post-workout
  recovery", "muscle recovery", "recovery and stamina") →
  `recovery.training_recovery` under rule 1, subject to the three-benefit list
  rule (report 10 note 6, held back until the label existed). The "morning
  routine" sentence moved here from the compliance-line bullet.
- Report 02 notes, cited "02-n":
  - 4.1 free-from lists: product's own subject only (chicken →
    `food.meat_animal_foods`, meal service → `food.general_nutrition`), never
    one topic per item; frames only where the language occurs (02-1; lists in
    5,408 eps, 654 outside ads; Nature Raised Farms alone is 3,594 of 5,878
    "seed oils" episodes). The 3.3 meat-brand bullet now points here.
  - 3.3 fails: meal-kit menu-variety lists with no stated benefit (02-2; Cook
    Unity ~1,950 Shapiro eps). This narrows ad test (c): "gluten-free" or
    "high protein" as menu options is composition, not a healthier claim.
  - 3.4 animal health: pet-food ads stay excluded even when they generalize
    about processed food (02-3; 2,597 eps, the only UPF vocabulary in them).
  - Section 2 ambiguous words: "juicing" (steroid slang, 749 eps), "fiber",
    "MSG", "Whole Foods" the store, "fasting insulin/glucose" as lab values
    (`metabolic.insulin_glucose`), religious fasting and Lent (02-4). "Soy boy"
    was already in 5.2.
  - 3.4 taglines: recurring intro or outro boilerplate that lists health
    practices is excluded (02-5; LONGEVITY intro, 457 eps). I chose exclusion
    over the report's "at most passing" for consistency with the tagline rule.
  - Rule 5: bioavailability and sulforaphane follow the form (02-6).
  - Rule 1: a diet's effect on appetite or overeating, and sugar cravings, add
    `food.eating_behavior` (02-7).
  - 5.2 `unlisted_narrative` examples: "calories in, calories out is a myth"
    and "they want you to eat bugs" (02-8). The food-pyramid proposition is
    the installed `dietary_guidelines_caused_obesity`, so it points there.
  - 4.1 delimitation: a change of register alone delimits a read with no
    transition, code or URL (02-9; Pardon My Take's ONE bar read, 128564/3).
- Rubric unchanged in this pass.
