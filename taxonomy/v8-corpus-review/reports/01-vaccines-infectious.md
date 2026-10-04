# Vaccines & infectious disease (`vaccines`, `covid`, `infectious`): corpus review

Method: keyword counts with `cq.py count` (segments / episodes / podcasts) and
random samples (`cq.py sample`, 6-14 passages per label group, read in full).
Counts are rough ceilings: most queries include some noise, which is noted
where it matters. Early queries ran on `/mnt/data2/podcast-data/corpus-text`.
Later ones ran on the NVMe copy at `/mnt/internal/felix/podcast-corpus-text`,
which holds the same data. The permission classifier blocked several commands
until the exact command form was allowed. Every search in this report did run.

## Summary

- **Every subtopic in this slice is well attested.** The rarest are
  `vaccines.hpv_vaccine` (about 117 episodes, 46 podcasts) and
  `vaccines.hep_b` (127 episodes, 40 podcasts). No label should be dropped.
  Vaccine talk is concentrated in political and news shows (Charlie Kirk,
  Rogan, Megyn Kelly, Shapiro, MeidasTouch, Culture Apothecary), not health
  shows.
- **The biggest error source is non-health use of COVID words, not taxonomy
  gaps.** About 43,000 episodes say "covid", "coronavirus" or "pandemic". In a
  random sample of 14, about 8 used COVID or "the pandemic" only as a time
  marker or an economic backdrop ("during COVID I watched a docuseries", "we
  moved in the middle of COVID"). "Quarantine" and "lockdown" behave the same
  way ("as soon as the quarantine hit…"). The codebook has no rule for this.
  It needs one in section 3.
- **Drug-ad safety boilerplate puts vaccine and infection words into about
  3,000 episodes.** Examples: "tell your doctor if you … need a vaccine",
  "live vaccines", "get checked for infections and tuberculosis". Most of
  these are Ringer shows. GoodRx "discounted flu shots" reads add about 970
  more episodes. None of this boilerplate should create a `vaccines` or
  `infectious` detection. The ad rule in 4.1 should say so explicitly.
- **COVID vaccine injury vs `vaccines.safety_injury` is the most frequent
  boundary in the slice, and the current text contradicts itself.** 288 of the
  327 episodes that say "vaccine injury/injured" are COVID contexts.
  `covid_vaccines` says side effects take it alone, but `safety_injury` holds
  the myocarditis co-label instruction. Proposal: "vaccine injury" or "the
  vaccine-injured" as a subject adds `safety_injury`, and the myocarditis rule
  moves to `covid_vaccines`.
- **One new subtopic: `infectious.chronic_hidden_infections`.** It covers
  Epstein-Barr reactivation, herpesviruses, and "hidden" or "stealth"
  infections as root causes of chronic illness. These recur in functional
  medicine: about 436 episodes and 67 podcasts on the narrow query, about 890
  on the broader one. Right now they scatter across `other_infections`,
  `chronic_complex.*` and `endocrine.thyroid`.
- **Extend three definitions to cover recurring orphans:**
  - `infectious.emerging_outbreaks` should also take bioweapons, biosecurity
    and gain-of-function research outside COVID origins (about 400 episodes
    with no COVID word).
  - `infectious.foodborne` should also take stomach bugs, norovirus and
    "stomach flu" (580 episodes, 134 podcasts, currently homeless).
  - `vaccines.development_approval` should also take the mRNA platform as such
    (BARDA funding cuts, state mRNA bans, mRNA flu and cancer vaccines; about
    200 episodes).
- **Boundary notes, all from real passages:**
  - Antibiotics in meat ("never use growth hormones or antibiotics") appear in
    about 1,056 episodes, mostly meat-brand ads. They belong to `food`, not
    `infectious.antibiotics_resistance`.
  - Sepsis is listed in both `infectious.other_infections` and
    `acute_care.emergency_critical_care`.
  - "Quarantine" is split between `covid.masks_distancing` and
    `covid.lockdowns_closures`. In lay use it means the 2020 stay-at-home
    period.
- **Speech-recognition variants worth listing:**
  - ACIP comes out as "ASAP" or "ACP".
  - VAERS comes out as "Vair system".
  - MMR comes out as "measles, momps and rebelt".
  - "The jab" is mostly boxing in Rogan and fight shows.
  - In 2021-23 talk, "the vax", "vaxxed/unvaxed" and "fully vaccinated" are
    the everyday words for COVID vaccines.

## Label-by-label findings

### `topic:vaccines` (parent)
- Query `\b(vaccin\w*|unvaccinated|anti-?vax\w*)\b`: 27,565 segments, 16,295
  episodes, 284 podcasts. About 2,900 of those episodes are drug-ad
  boilerplate (`need a vaccine|live vaccines|…scheduled to receive a vaccine`:
  2,904 episodes, 66 podcasts; Ringer Fantasy Football 786, Bill Simmons 681,
  The Big Picture 666). Example: ep 322572 seg 0, "Tell your doctor if you
  have an infection, flu-like symptoms. Or need a vaccine? … Ask your doctor
  about Tremphia today."
- Bare-parent territory seen: vaccine policy in general under RFK Jr. ("they
  will not take away vaccines", ep 328938 seg 399), and "anti-vaxxer" used as
  an epithet (below).

### `vaccines.childhood_schedule`
- Query: schedule terms, "72 shots", "alternative schedule", "spacing out
  shots". 482 segments, 385 episodes, 88 podcasts. ACIP alone: 105 segments,
  78 episodes, 24 podcasts. ACIP speech-recognition variants plus
  Denmark/UK-schedule comparisons: 62 episodes.
- **Verdict:** fine; examples need updating. Real phrasing: "taking the
  childhood recommended vaccine schedule from over. Seventy down to I don't
  know what is it eleven" (ep 388208 seg 6). "I'm looking at the U.K. vaccine
  schedule, and that one seems a little more reasonable" (ep 185687 seg 0).
  ACIP mis-transcribed: "ASAP, that's the panel RFK replaced that sets the
  vaccine schedule" (ep 167703 seg 0); "A CDC vaccine panel known as ACP"
  (ep 167680 seg 0).
- **Ambiguity:** "ACIP" appears in the examples of both `childhood_schedule`
  and `development_approval`. Real ACIP talk is mostly about who sits on the
  committee (RFK firing members) or a vote on one vaccine (hep B, MMRV,
  COVID). That needs a split rule (see edits).
- **Noise:** "seventy-two shots" also refers to gunfire (ep 7586 seg 6).

### `vaccines.hep_b`
- Query `hep(atitis)? ?b (vaccine|shot|…)|birth dose`: 171 segments, 127
  episodes, 40 podcasts.
- **Verdict:** fine. The passages are clear: "giving everybody a birth dose of
  hepatitis B vaccine" (ep 81441 seg 1); "250 micrograms of aluminum … in that
  hepatitis B vaccine" (ep 185726 seg 4), which also takes `ingredients`.
- **Ad boilerplate:** "hepatitis B reactivation" in drug ads is not this
  label.

### `vaccines.mmr`
- Query `\bMMR\b|measles (vaccine|shot|vaccination)`: 541 segments, 379
  episodes, 81 podcasts.
- **Verdict:** fine. "Measles, mumps, rubella" said as a vaccine list takes
  `mmr` (ep 37578 seg 3, "I'm not talking about measles, mumps, rubella. I'm
  not talking about Tdap"). Speech-recognition form: "measles, momps and
  rebelt" (ep 329107 seg 105).

### `vaccines.covid_vaccines`
- Query: COVID/mRNA/Pfizer/Moderna + vaccine/shot/jab/booster, plus "the jab"
  and Novavax. 3,667 segments, 2,722 episodes, 147 podcasts. That is an
  undercount, because most talk just says "the vaccine", "the vax" or "the
  shot". Slang query (`the jab|jabbed|vaxxed|unvaxed|clot shot|pureblood|the
  vax`): 1,711 segments.
- **Verdict:** needs a definition change.
  - "The jab" is ambiguous: in Rogan and MMA shows it is mostly boxing
    (ep 8906 seg 19, "hit the jab, switching to a southpaw").
  - The real words are "the vax", "vaxxed/unvaxed" and "fully vaccinated":
    "We have to protect the vax from the unvaxed" (ep 389545 seg 5); "all
    fully vaxxed, and I got COVID from a fully vaxxed individual"
    (ep 8438 seg 14).
- **Main boundary with `safety_injury`:** 288 of 327 "vaccine injury"
  episodes are COVID contexts. Example: "I've had people on the show have had
  serious vaccine injuries, who said that basically … the CDC cut off contact
  with them" (ep 13040 seg 8). Under the current text a coder would apply
  `covid_vaccines` alone, because no "injury system" is named, even though
  vaccine injury is plainly the subject.
- **Contradiction:** the myocarditis co-label instruction sits in
  `safety_injury`, but `covid_vaccines` says side effects take
  `covid_vaccines` alone.
- **Approval overlap:** `covid_vaccines` lists "approvals" while
  `development_approval` lists EUA and Warp Speed, so COVID EUA talk has two
  plausible homes.

### `vaccines.hpv_vaccine`
- Query `gardasil|hpv (vaccine|shot)|cervical cancer vaccine`: 146 segments,
  117 episodes, 46 podcasts. Candace 13, Megyn Kelly 12, Afterpause 11.
- **Verdict:** fine; rare but well defined.

### `vaccines.flu_vaccine`
- Query `\bflu (shot|vaccine|jab)s?\b|influenza vaccin\w*`: 1,963 segments,
  1,764 episodes, 126 podcasts. 971 of those episodes (8 podcasts: Crime
  Junkie 357, Wait Wait 289, The Deck 180, SmartLess 115) are GoodRx reads.
  Example: ep 436 seg 1, "Discounted flu shots for the whole family … Save on
  a flu shot today."
- **Verdict:** fine. The GoodRx read sells flu-shot discounts, so it is
  correctly `flu_vaccine` with `relevance: advertisement` plus
  `health_system.costs_insurance`. Labelers should expect it and not miss it.
  Organic talk is about 800 episodes. One real study context: "we gave all of
  them … a flu shot" to measure the immune response to meditation
  (ep 179621 seg 1). That is `flu_vaccine` + `efficacy_response`.

### `vaccines.other_vaccines`
- Query: RSV/shingles/polio/chickenpox/Tdap/…/mpox + vaccine/shot, plus
  Shingrix and Prevnar. 967 segments, 771 episodes, 129 podcasts.
- **Verdict:** fine. Note that "shingles vaccine" includes the
  shingles-vaccine-and-dementia story, which takes
  `dementia_ageing.dementia_alzheimers` too under co-label rule 1.

### `vaccines.safety_injury`
- Query: vaccine injury, VAERS, vaccine court, VSD, VICP, 1986 Act, liability
  shield, "jab injured". 708 segments, 528 episodes, 66 podcasts. Charlie Kirk
  alone has 135 episodes.
- **Verdict:** needs a definition change. Real phrasing: "the Vair system
  that we have is completely rigged" (ep 931 seg 7, speech recognition for
  VAERS); "I'd like to separate autism from vaccine injury" (ep 185681 seg 4).
- The "package insert" example also catches drug package inserts generally
  (ep 29002 seg 6, a cancer-drug leaflet). It should say "vaccine package
  insert".

### `vaccines.ingredients`
- Query: adjuvant, thimerosal, fetal cells, polysorbate, SV40, DNA
  contamination, lipid nanoparticles, mercury/aluminum/formaldehyde near
  vaccine. 395 segments, 292 episodes, 70 podcasts.
- **Noise:** "adjuvant" is cancer therapy in Peter Attia (27 segments,
  20 episodes, for example ep 181663 seg 8, "adjuvant therapy"), and
  "adjuvant compound for depression" appears in Mind Pump (ep 195595 seg 4).
- **Verdict:** fine. Real phrasing: "they took it out and then they put in
  aluminum, which is eighty times more toxic to brain tissue than mercury"
  (ep 185654 seg 5); "aborted fetal cells in the development of the vaccine"
  (ep 40102 seg 3).

### `vaccines.mandates_exemptions`
- Query: vaccine mandate/passport, mandating the shot,
  religious/medical/philosophical exemption, "no jab no job". 2,374 segments,
  1,748 episodes, 77 podcasts, heavily political (Kirk 357, Shapiro 201,
  Morning Wire 165).
- **Verdict:** fine. "Fired people for not getting the vax" (ep 389213 seg 3)
  is a mandate passage that never says "mandate".

### `vaccines.uptake_hesitancy`
- Query: hesitancy, vaccination rates, uptake, unvaccinated, anti-vax,
  vaccine skeptic, exemption rates. 3,806 segments, 2,666 episodes,
  143 podcasts.
- **Verdict:** examples change and a codebook note.
  - "Anti-vax" is very often a bare epithet for a person: "having a anti-vax
    Kennedy. The helm of of HHS" (ep 314371 seg 0); "Remember when Nicki Minaj
    went anti-vax for a couple of weeks" (ep 175707 seg 2). With nothing said
    about vaccines, this is like an insult word and should not create a
    detection, or at most a passing one.
  - Access and coverage have no clear home: "Over fifty percent of kids … get
    their vaccines through the Vaccines for Children program. If the ACIP
    says … the VFC won't buy it" (ep 4041 seg 1). This fits here.

### `vaccines.development_approval`
- Precise query (Operation Warp Speed, EUA, VRBPAC, vaccine
  trial/development/approval, saline/true placebo or placebo near vaccine):
  1,029 segments, 805 episodes, 84 podcasts. The broader query with bare
  "warp speed" or "placebo-controlled" is inflated by idioms and non-vaccine
  trials (1,441 episodes).
- **Verdict:** needs a definition change to take the mRNA platform as such.
  - mRNA platform query (`mrna technology|platform|cancer vaccine|mRNA in
    food|vaccinating cattle`): 239 segments, 203 episodes, 50 podcasts.
    Examples: "RFK Cuts mRNA Vax Funding" (BARDA; ep 4520 seg 0); "we still
    are pushing mRNA technology" (ep 422435 seg 10); "Moderna had developed a
    groundbreaking vaccine for seasonal flu … uses the mRNA technology"
    (ep 89411 seg 2).
  - None of this is COVID-specific, so it fits neither `covid_vaccines` nor
    `flu_vaccine` well.

### `vaccines.efficacy_response`
- Query: vaccine effectiveness/efficacy, Gavi, antibody response, "vaccines
  work". 582 segments. The Gavi vaccine alliance is rare (22 episodes,
  16 podcasts), and "Gavi" is mostly personal names (ep 31875 seg 4,
  ep 90010 seg 5).
- **Verdict:** fine. "Gavi" and "vaccination programme funding" overlap with
  `health_system.global_health` (USAID, PEPFAR). Moving them to
  `global_health` would remove a cross-domain overlap, but this is low
  priority. Specific vaccines' efficacy (COVID "if the vaccine works so well,
  why do you need boosters", ep 40426 seg 3) correctly goes to the specific
  subtopic.

### `topic:covid` (parent) and time markers
- `\b(covid|corona ?virus|sars.cov|pandemic)\b`: 83,577 segments, 43,283
  episodes, 393 podcasts. The Ramsey Show (986 episodes) and Pardon My Take
  (1,160) are in the top six, almost entirely as era references.
- Sample of 14: 8 were non-health time or economy references.
  - ep 192241 seg 7: "that happened to me for a brief moment during COVID. I
    watched a short series".
  - ep 79682 seg 8: "the biggest company in the world these days, given
    COVID".
  - ep 128502 seg 8: "It was COVID. Twenty-two for twenty-three", a sports
    season.
- **Verdict:** add a codebook exclusion (see notes).

### `covid.illness_severity`
- Query: COVID symptoms/deaths, IFR, Omicron, Delta, comorbidities, "got/had
  COVID", "died of COVID". 6,495 segments, 4,768 episodes, 209 podcasts.
- **Verdict:** fine. A frequent passing form is a person's own infection
  ("I took a COVID test", "got COVID"). COVID compared with flu ("view this
  the same as the flu", ep 440583 seg 0) is this label, plus
  `narrative:covid_severity_exaggerated` when the proposition is present.

### `covid.origins`
- Query: lab leak, Wuhan lab/institute, gain of function, EcoHealth, wet
  market, Proximal Origin, Daszak. 2,024 segments, 1,344 episodes,
  80 podcasts.
- **Verdict:** fine, with one note. "China virus", "Chinese coronavirus" and
  "kung flu" are mostly a name for the virus, not origin talk (1,074 episodes
  for the combined slang query, 458 of them Charlie Kirk). Example:
  ep 40599 seg 3, "This was the Chinese coronavirus, the China virus. Joe
  Biden didn't mention once that this likely came from the Wuhan Institute".
  That one does go on to origins. The name alone should not trigger
  `origins` (frame axis: `frame:political_partisan` if anything).

### `covid.treatments`
- Query: ivermectin, HCQ, Paxlovid, remdesivir, monoclonal antibodies, early
  treatment, FLCCC. 2,384 segments, 1,707 episodes, 107 podcasts.
- **Verdict:** fine. The boundaries with `medications.repurposed_offlabel`
  (ivermectin off-label) and `cancer_alt.repurposed_drugs` are already
  stated.

### `covid.masks_distancing` and `covid.lockdowns_closures`
- Masks, distancing and quarantine query: 15,860 segments, 10,491 episodes,
  299 podcasts. Lockdown and school-closure query: 9,329 segments, 7,049
  episodes, 256 podcasts.
- Both are heavily inflated by era use.
  - "As soon as the quarantine hit, I dove in" (ep 194801 seg 1).
  - "We're all more isolated and cut off and quarantined" (ep 1139102 seg 0).
  - Boris Johnson "partygate" during lockdown (ep 1139545 seg 0) is politics,
    not health.
  - Individual quarantine is rarer: "She's in quarantine because she took her
    dad to the doctor. He had a fever" (ep 1139307 seg 1).
- **Verdict:** needs definition changes. In lay usage "quarantine" mostly
  means the general stay-at-home period, so it belongs in
  `lockdowns_closures`. The current definitions put "quarantine" under
  `masks_distancing`.
- Also seen: "the COVID lockdowns that caused the depression" (ep 207604
  seg 8). Economic costs of lockdowns are in scope by the definition ("their
  costs"). Pure business commentary that names COVID is not.

### `covid.testing_counting`
- Query: PCR, cycle threshold, rapid/antigen test, COVID test, "died with
  COVID", case counts. 1,706 segments, 1,428 episodes, 145 podcasts.
- **Verdict:** fine. "PCR" also appears for DNA testing in true crime. A
  routine "I took a COVID test" is passing; the label fits.

### `covid.long_covid`
- Broad query: 2,129 segments and 1,681 episodes, inflated by the "post-COVID
  era" sense. Tight query (long COVID, long haulers near COVID/symptoms,
  post-COVID syndrome, PASC, post-viral syndrome or fatigue): 997 segments,
  656 episodes, 104 podcasts. Hyman 55, Niddam 41.
- **Verdict:** fine. Real talk lumps it with ME/CFS, mold, MCAS and viral
  reactivation: "histamine problems, long COVID, Epstein Barr and Lyme
  reactivated, herpes viruses reactivated" (ep 677833 seg 0). The EBV part
  has no home; see the ADD below.
- Jokes such as "I am much more worried about long Trump than I am about long
  COVID" (ep 6893 seg 2) are figures of speech.

### `covid.pandemic_institutions`
- Query: Fauci, Great Barrington, pandemic treaty, COVID inquiry, pandemic
  preparedness. 5,980 segments, 3,923 episodes, 130 podcasts.
- **Verdict:** fine. Fauci named as a political villain in passing is very
  frequent. It is a passing detection here, plus `frame:government_distrust`
  only if the framing occurs.

### `topic:infectious` (parent)
- Bare-parent territory seen: generic "infections", "viruses", "getting sick
  this season", and historical epidemics.
- Historical epidemic query (Black Death, bubonic, Spanish flu, 1918,
  smallpox, cholera, typhus): 3,006 segments. History shows dominate (Boring
  History, The Rest Is History, Stuff You Missed in History Class). Example:
  "smallpox, for instance, was the native population had no immunity"
  (ep 200082 seg 4).
- These are mostly `passing` or excluded under the history default (section
  3). No new subtopic is needed, but `other_infections` should list plague,
  smallpox and cholera so they are coded consistently.

### `infectious.measles`
- `\bmeasles\b`: 1,443 segments, 1,101 episodes, 124 podcasts. MeidasTouch
  101, Rogan 82, Pod Save America 41.
- **Verdict:** fine. Outbreak talk is usually tied to hesitancy ("instances of
  measles outbreaks, a rise in vaccine skepticism", ep 1140048 seg 0), which
  calls for `measles` + `vaccines.uptake_hesitancy`. Historical "measles and
  the flu wiped out" indigenous groups (ep 318778 seg 2) is passing.

### `infectious.influenza_avian`
- Query: bird/avian flu, H5N1, flu season, influenza, Tamiflu. 3,235
  segments, 2,733 episodes, 163 podcasts, including GoodRx and HelloFresh
  "cold and flu season" ad copy. Sample on `the flu|a flu|stomach flu|flu
  season|influenza`: 6,435 segments.
- **Verdict:** examples change. Most organic hits are a person's own illness
  ("He had the flu over the weekend", ep 12944 seg 4) or the 1918 flu as
  history (ep 74395 seg 5; ep 1136558 seg 0). The examples list neither.
- "Stomach flu" is not influenza and has no home (see the foodborne edit).

### `infectious.emerging_outbreaks`
- Query: Ebola, Marburg, hantavirus, mpox/monkeypox, Disease X, screwworm,
  Nipah, Zika, H5N1. 1,917 segments, 1,512 episodes, 158 podcasts. There is
  comedic noise (Kill Tony 44 episodes, Watch What Crappens 52), and insults
  such as "it looks like MPOX patient zero" (ep 4214 seg 6) should be
  excluded.
- **Gap: bioweapons and biosecurity.** Query for bioweapons, biological
  weapons, biolabs, bioterror, gain of function, dual-use research: 1,459
  episodes, of which 1,055 also mention COVID. That leaves about 400 episodes
  of non-COVID biosecurity talk:
  - "the dream of the Soviets was to create this chimera weapon … make bubonic
    plague into a super weapon" (ep 318835 seg 14);
  - "the cost-benefit of a gain-of-function research" (ep 325294 seg 15,
    Lex Fridman);
  - CIA biological-weapons interviews (ep 155390 seg 5).
- `covid.origins` holds gain of function only for SARS-CoV-2.
  `narrative:outbreak_engineered` is homed in `infectious`, but no subtopic
  names the subject. Extend this one.

### `infectious.foodborne`
- Query: E. coli, Salmonella, Listeria, food poisoning, botulism, Cyclospora,
  norovirus, stomach bug/flu. 2,816 segments, 2,405 episodes, 202 podcasts,
  much of it personal and comedic.
- Stomach bug, stomach flu, norovirus, gastroenteritis and stomach virus:
  637 segments, 580 episodes, 134 podcasts. That is gastroenteritis from any
  source, not necessarily food, and it fits no subtopic (`gut` is
  functional/chronic).
- **Verdict:** extend the definition.

### `infectious.respiratory_common`
- Query: common cold, RSV, whooping cough, pertussis, strep, pneumonia, sinus
  infection, bronchitis, ear infection, "the flu", head cold. 8,514 segments,
  6,966 episodes, 285 podcasts. This query included "the flu", which belongs
  to `influenza_avian`.
- **Verdict:** fine. Pneumonia appears often as a cause of death, which also
  takes `acute_care.death_dying`. "Cold and flu season" ad copy lands here or
  in `influenza_avian` inconsistently; the examples should settle it.

### `infectious.vector_borne`
- Query: Lyme, tick bites, West Nile, dengue, malaria, chikungunya, tick- or
  mosquito-borne. 3,887 segments, 2,500 episodes, 196 podcasts. Hyman 185,
  Thyroid Fixer 78, Jockers 73.
- **Verdict:** fine, but the functional-medicine bulk is chronic Lyme or
  co-infection talk, which the table already routes to
  `chronic_complex.chronic_lyme`.

### `infectious.parasitic_infections`
- Query: parasites, pinworm, tapeworm, giardia, toxoplasma, worms near
  gut/body, antiparasitic. 5,084 segments, 3,570 episodes, 190 podcasts.
- **Noise:** the film *Parasite* (ep 321322 seg 1); "the government is a
  parasite" (ep 57827 seg 1).
- **Verdict:** fine. Functional-medicine lists such as "a detox of parasites,
  heavy metals, radiation, mold" (ep 178169 seg 3) are
  `detox.parasite_cleanses` under the table's rule. Diagnostic and prevalence
  talk ("children … even parasites where they've had ADHD", ep 181989 seg 3)
  is this label.

### `infectious.antibiotics_resistance`
- `\bantibiotics?\b|superbugs?|MRSA|C. diff|antimicrobial resistance`:
  6,995 segments, 4,951 episodes, 225 podcasts.
- About 1,056 episodes (102 podcasts) are antibiotics in livestock or meat,
  mostly meat-brand ads: "They never use growth hormones or antibiotics"
  (ep 42229 seg 4); "the chicken won't have any antibiotics" (ep 204381
  seg 1). By the ad test these are free-from claims about food.
- Antibiotics harming the microbiome ("drugs that we take, like antibiotics
  and acid blockers", ep 182490 seg 0) correctly takes this label plus
  `gut.microbiome`.
- **Verdict:** add a boundary sentence.

### `infectious.germ_theory_hygiene`
- Query: germ theory, terrain theory, hygiene hypothesis, handwashing,
  sanitizer, contagio-. 8,118 segments, 6,711 episodes, 277 podcasts. This is
  dominated by figurative "contagious" (laughter, energy) and must not be read
  as a frequency.
- Narrow query (germ theory, terrain theory, hygiene hypothesis, "viruses
  don't exist", "never been isolated"): 402 segments.
  - Many are analogies: "I feel like I discovered it in the world, like germ
    theory or something" (ep 193221 seg 3); "the germ theory of disease. It's
    a system for explaining…" (ep 207418 seg 3).
  - Real cases: "it's all based on a bogus theory called the germ theory"
    (ep 185982 seg 2, Chiro Hustle), which also takes
    `narrative:germ_theory_denial`.
- **Verdict:** fine, but note that analogy use is excluded.

### `infectious.other_infections`
- First query: TB, sepsis, hep C, fungal, staph, UTI, polio, chickenpox,
  shingles, meningitis, cholera, leprosy, smallpox, plague. 16,512 segments,
  11,664 episodes. This was swamped by drug-ad boilerplate ("get checked for
  infections and tuberculosis"; the infection-boilerplate query alone hits
  2,985 episodes) and by "plague" in Bible and history shows.
- Narrower query (sepsis, hep C, fungal, staph, UTI, meningitis, cellulitis,
  necrotizing): 2,769 segments, 2,304 episodes, 207 podcasts. Giggly Squad
  has 324 of those episodes, almost all from one recurring women's-health ad
  ("a UTI, a breakout, whatever", ep 156844 seg 2).
- **Verdict:** needs a definition change. Sepsis is listed both here and in
  `acute_care.emergency_critical_care`.

## Proposed edits

CHANGE `vaccines.covid_vaccines`:
| covid_vaccines | COVID-19 vaccines | COVID-19 vaccines and boosters of any platform: efficacy, side effects, recommendations, who should get them. In 2021-2023 talk a bare "the vaccine", "the vax" or "the shot" usually means this; confirm from the window. Side effects alone take this label; add `vaccines.safety_injury` when vaccine injury itself is the subject (the "vaccine-injured", injury reporting, VAERS, compensation), `cardiovascular.heart_disease` for myocarditis, and `vaccines.development_approval` only when trials, EUA or the approval process are discussed. | mRNA vaccine; Pfizer; Moderna; booster; J&J shot; Novavax; the vax; vaxxed and unvaxxed; fully vaccinated; clot shot; "the jab" (not the boxing punch) |

Why: 288 of 327 "vaccine injury" episodes are COVID contexts, and the current
text sends them to `covid_vaccines` alone unless an injury system is named. Two
examples: "people on the show have had serious vaccine injuries" (ep 13040
seg 8) and "protect the vax from the unvaxed" (ep 389545 seg 5). "The jab" is
mostly boxing in fight shows (ep 8906 seg 19). This also resolves the
"approvals" overlap with `development_approval`.

CHANGE `vaccines.safety_injury`:
| safety_injury | Vaccine safety, injury & surveillance | Vaccine adverse events and injury as a subject (including people described as vaccine-injured), and the systems that monitor or compensate them. A specific vaccine's injuries also take that vaccine's subtopic. | adverse events; vaccine injury; vaccine-injured; VAERS (also transcribed "Vair system"); Vaccine Safety Datalink; VICP; vaccine court; 1986 Act; liability shield; vaccine package insert |

Why: the myocarditis instruction moves to `covid_vaccines`, where the cases
are. "Package insert" alone also matched drug leaflets (ep 29002 seg 6). VAERS
is transcribed as "the Vair system" (ep 931 seg 7). Counts: 528 episodes,
66 podcasts.

CHANGE `vaccines.childhood_schedule`:
| childhood_schedule | Childhood vaccine schedule | The infant and childhood schedule as a whole: how many shots, at what ages, combination shots, delayed or alternative schedules, comparisons with other countries' schedules, ACIP/CDC changes to the schedule as a whole, well-child visits as vaccination occasions. An ACIP vote on one vaccine takes that vaccine's subtopic; ACIP membership and firings take `vaccines.development_approval`. | CDC schedule; 72 shots; cut from 72 to 11; spacing out shots; alternative schedule; Dr. Bob schedule; Denmark or UK schedule; ACIP (also transcribed "ASAP", "ACP") |

Why: 385 episodes and 88 podcasts. ACIP appears in two subtopics' examples
with no split rule. Real phrasing: "from over. Seventy down to … eleven"
(ep 388208 seg 6), "looking at the U.K. vaccine schedule" (ep 185687 seg 0),
"ASAP, that's the panel RFK replaced" (ep 167703 seg 0).

CHANGE `vaccines.development_approval`:
| development_approval | Vaccine development, trials, platforms & approval | How vaccines are developed, tested and approved: trial design, placebo controls, emergency use authorization as a process, ACIP and FDA advisory committees as bodies (membership, firings, procedure), manufacturers' role, and the mRNA platform as such (research funding, state mRNA bans, mRNA vaccines for flu or cancer). Vaccine-maker economics go to `health_system.pharma_industry`. | placebo-controlled trial; saline placebo; EUA; Operation Warp Speed; ACIP committee; VRBPAC; mRNA technology; BARDA mRNA contracts cancelled; mRNA cancer vaccine |

Why: about 203 episodes and 50 podcasts discuss mRNA as a platform outside
COVID, with no home today: "RFK Cuts mRNA Vax Funding" (ep 4520 seg 0), "we
still are pushing mRNA technology" (ep 422435 seg 10). The precise
development query has 805 episodes and 84 podcasts.

CHANGE `vaccines.uptake_hesitancy`:
| uptake_hesitancy | Uptake, hesitancy, access & vaccine decisions | Vaccination rates, hesitancy, trust in vaccines, the anti-vaccine movement, how parents decide, pediatricians dismissing unvaccinated families, informed consent for vaccines, and access and coverage (Vaccines for Children, insurance coverage, pharmacy rules). "Anti-vax" used only as an epithet for a person, with nothing said about vaccines, is not this label. | vaccination rates falling; vaccine hesitant; anti-vax movement; unvaccinated kids; pediatrician fired us; Vaccines for Children program; vaccine coverage by insurers |

Why: 2,666 episodes and 143 podcasts. "Anti-vax Kennedy" (ep 314371 seg 0)
and "Nicki Minaj went anti-vax" (ep 175707 seg 2) are epithets. VFC and
coverage talk (ep 4041 seg 1) currently has no explicit home.

CHANGE `covid.masks_distancing`:
| masks_distancing | Masks, distancing & isolation | Non-pharmaceutical measures applied to individuals: masks, social distancing, and quarantine or isolation of an exposed or infected person. "Quarantine" meaning the 2020 stay-at-home period goes to `covid.lockdowns_closures`. | mask mandates; N95; cloth masks; six feet; quarantine after exposure; isolation period |

Why: the combined query has 10,491 episodes, and lay "quarantine" mostly means
the stay-at-home era ("as soon as the quarantine hit", ep 194801 seg 1).
Individual quarantine (ep 1139307 seg 1) is the minority.

CHANGE `covid.lockdowns_closures`:
| lockdowns_closures | Lockdowns & school closures | Lockdowns, stay-at-home orders ("the quarantine" as a period), business and school closures, and their health, social and economic costs. COVID or lockdown named only as a time marker is not health content. | lockdown; "during quarantine"; school closures; learning loss; shutdowns; lockdown depression |

Why: 7,049 episodes with heavy era use. Real cost talk ("the COVID lockdowns
that caused the depression", ep 207604 seg 8) is in scope; time markers are
not.

CHANGE `covid.origins`:
| origins | Origins of SARS-CoV-2 | Where the virus came from: lab leak, natural spillover, wet market, gain-of-function research on coronaviruses, EcoHealth, the Wuhan Institute of Virology. Calling it the "China virus" or "Chinese coronavirus" without discussing where it came from is not this label. Gain-of-function and bioweapons outside SARS-CoV-2 go to `infectious.emerging_outbreaks`. | lab leak; Wuhan lab; gain of function; EcoHealth Alliance; wet market; Proximal Origin; Daszak |

Why: 1,344 episodes for origins. The "China virus" family of names hits 1,074
episodes, 458 of them Charlie Kirk, where it is mostly a name rather than a
claim about origin.

CHANGE `infectious.emerging_outbreaks`:
| emerging_outbreaks | Emerging outbreaks, pandemic threats & biosecurity | Outbreaks of emerging, rare or exotic pathogens and pandemic threats other than flu, and biosecurity: bioweapons, biolabs, and gain-of-function or dual-use pathogen research outside the SARS-CoV-2 origins debate. | Ebola; Marburg; hantavirus; mpox; Disease X; New World screwworm; Nipah; bioweapons; biolabs; anthrax attacks; gain-of-function research (non-COVID) |

Why: about 400 episodes of non-COVID biosecurity talk (1,459 with the terms,
1,055 with a COVID word). Examples: the Soviet plague "super weapon"
(ep 318835 seg 14) and gain-of-function cost-benefit (ep 325294 seg 15). This
gives `narrative:outbreak_engineered` a matching topic.

CHANGE `infectious.foodborne`:
| foodborne | Foodborne illness & stomach bugs | Infections and poisonings from food, and acute infectious gastroenteritis whatever its source. | E. coli; Salmonella; Listeria; food poisoning; botulism; raw-milk pathogens; Cyclospora; norovirus; stomach bug; stomach flu |

Why: stomach bug, stomach flu and norovirus appear in 580 episodes across
134 podcasts and fit no listed subtopic. Influenza does not fit them, and
`gut.digestive_symptoms` is for functional complaints.

CHANGE `infectious.influenza_avian`:
| influenza_avian | Influenza & avian flu | Seasonal influenza and avian or pandemic flu as diseases, including someone's own bout of "the flu" and historical flu pandemics. "Stomach flu" goes to `infectious.foodborne`; "cold and flu season" with no specific illness goes to `infectious.respiratory_common`. | flu season; had the flu; H5N1; bird flu; avian flu in cattle; Tamiflu; 1918 Spanish flu |

Why: 2,733 episodes. The sampled organic hits were mostly personal ("He had
the flu over the weekend", ep 12944 seg 4) or 1918 history (ep 74395 seg 5),
and neither appears in the examples.

CHANGE `infectious.antibiotics_resistance`:
| antibiotics_resistance | Antibiotics & resistance | Antibiotic use and overuse in people, side effects (microbiome damage included, with `gut.microbiome`), resistance, superbugs. Antibiotics in livestock or "raised without antibiotics" meat claims go to `food.organic_gmo`; add this label only when resistance or human exposure is discussed. | antibiotics; overprescribing; C. diff; MRSA; superbugs; antibiotic resistance |

Why: about 1,056 of 4,951 antibiotic episodes are livestock or meat claims,
mostly ads ("They never use growth hormones or antibiotics", ep 42229 seg 4),
which the ad test treats as food free-from claims.

CHANGE `infectious.other_infections`:
| other_infections | Other infections | A named infection not listed above, including historical epidemics. Sepsis and septic shock go to `acute_care.emergency_critical_care`, plus the infection's subtopic when the source infection is named. Yeast infections go to `womens.gynecological_conditions`. | tuberculosis; hepatitis B or C infection; fungal infection; staph infection; UTI; cellulitis; meningitis; plague; smallpox; cholera |

Why: sepsis was listed in two parents. Historical epidemics (3,006 segments)
had no stated home. UTI is common: 324 Giggly Squad episodes alone from one
ad read.

ADD `infectious.chronic_hidden_infections` under `infectious`:
| chronic_hidden_infections | Latent, reactivated & "hidden" infections | Persistent or reactivated viral and other infections offered as causes of chronic symptoms or disease: Epstein-Barr and other herpesvirus reactivation, "stealth" or "hidden" infections, infection as a root cause of thyroid, autoimmune or fatigue conditions. Chronic Lyme and its co-infections go to `chronic_complex.chronic_lyme`; long COVID to `covid.long_covid`; add the condition's own subtopic under co-label rule 1. | Epstein-Barr reactivation; EBV and Hashimoto's; stealth infections; hidden infections; herpes viruses reactivated; viral load; chronic infections |

Why: the narrow query (EBV, stealth or hidden infections, viral reactivation,
herpesviruses) hits 690 segments, 436 episodes and 67 podcasts. The top shows
are Thyroid Fixer (81), Hyman (60), Jockers (41) and Niddam (33); the broader
query has 893 episodes and 105 podcasts. Example quotes: "I literally have
never seen a person not have Epstein-Barr virus" (ep 190399 seg 52) and
"Ninth pillar is bugs and hidden infections" (ep 190889 seg 141). These are
functional-medicine causal claims that researchers would want counted, and
today they scatter across `other_infections`, `chronic_complex` and
`endocrine.thyroid`.

## Codebook and prompt notes

1. **Section 3 (Exclude): COVID as a time marker.** Add a bullet: "COVID, the
   pandemic, lockdown or quarantine named only as a period or backdrop ('during
   COVID we moved', 'since the pandemic', 'business was hit by COVID', a sports
   season) with no illness, measure or health consequence discussed." In a
   sample of 14 hits on `covid|coronavirus|the pandemic`, 8 were of this kind
   (ep 192241 seg 7, ep 79682 seg 8, ep 128502 seg 8, ep 388543 seg 1). Across
   43,000 episodes this is the largest over-labeling risk in the slice.

2. **Section 4.1 (Topics inside ads): drug-ad safety boilerplate.** Add:
   "Safety boilerplate in a drug ad (infections, tuberculosis testing,
   hepatitis B reactivation, live vaccines, 'tell your doctor if you need a
   vaccine') takes no topic of its own; only the advertised drug's subtopic
   applies." Vaccine boilerplate appears in 2,904 episodes and infection
   boilerplate in 2,985, mostly Ringer shows (ep 322572 seg 0, ep 320733
   seg 0). The current list rule ("cholesterol to testosterone…") is about
   product benefit lists and does not obviously cover warnings.

3. **Section 3 (Ads): flu-shot and meat ads as calibration examples.**
   - GoodRx "discounted flu shots for the whole family" (971 episodes) passes
     the ad test as a health product: `vaccines.flu_vaccine`, advertisement.
   - Meat-brand "never use growth hormones or antibiotics" (about 1,000
     episodes) is a free-from claim framed as healthier: a food subtopic only,
     not `infectious.antibiotics_resistance`.

   Both are high-volume and worth naming in the ad paragraph or rubric
   examples.

4. **Section 3 (Exclude, insults and figures of speech): slice-specific
   cases.**
   - "Anti-vax" or "anti-vaxxer" as an epithet for a named person
     (ep 314371 seg 0).
   - "Looks like mpox patient zero" (ep 4214 seg 6).
   - "Like germ theory or something" used as an analogy (ep 193221 seg 3).
   - "Long Trump" jokes (ep 6893 seg 2).
   - "Parasite" for a person or the film (ep 57827 seg 1, ep 321322 seg 1).
   - "Contagious" laughter or energy.
   - "Seventy-two shots" fired (ep 7586 seg 6).

5. **Section 2 (General knowledge for understanding words): speech-recognition
   and slang list for this slice.** These are useful in the rubric:
   - ACIP comes out as "ASAP" or "ACP" (ep 167703 seg 0, ep 167680 seg 0).
   - VAERS comes out as "Vair system" (ep 931 seg 7).
   - MMR comes out as "measles, momps and rebelt" (ep 329107 seg 105).
   - "the vax", "vaxxed/unvaxed" and "fully vaxxed" mean COVID vaccines in
     2021-23.
   - "The jab" is often the boxing punch, so check context.
   - "Thimerosal" is also transcribed "thimerisol".

6. **Section 5.1 (co-labeling): measles and hesitancy.** Outbreak passages
   often blame falling vaccination ("measles outbreaks, a rise in vaccine
   skepticism", ep 1140048 seg 0). A rule-1-style line would stop coders from
   choosing only one: "an outbreak attributed to low vaccination takes the
   disease's subtopic plus `vaccines.uptake_hesitancy`."

7. **Section 3 (Violence, crime, war and death → history): historical
   epidemics.** Plague, smallpox and 1918 flu in history and Bible shows
   (3,006 segments) follow the history default: exclude unless the disease or
   its health toll is the point. Otherwise they are `passing` under
   `infectious.other_infections` or `influenza_avian`. The current history
   sentence mentions war history only.
