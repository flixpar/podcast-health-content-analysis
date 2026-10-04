# Granular labeling scheme, revision v8

v8 is the current revision of the granular scheme described in
`docs/labeling-v7.md`: the same five axes, file format, pipeline and result
schema (`topic-labeling-v5`), with the label set and codebook revised in two
passes: first from what the benchmark-v2 reference annotators reported (their
~3,400 ambiguity notes, synthesized in `benchmark/v2/codebook-v8-proposal.md`),
then from a review of the whole transcript corpus (see "Corpus review" below).

| file | what |
| --- | --- |
| `taxonomy/health-v8.md` | the label set |
| `taxonomy/codebook-v8.md` | the task definition (prompt and annotators) |
| `analysis/prompts/rubric-v8.md` | procedure, calibration, worked example |
| `benchmark/v3/` | the benchmark for v8 (reference labels pending) |

The taxonomy file selects its own prompt files: `health-vN.md` is compiled with
`taxonomy_version: vN`, and `prompt_files()` returns `rubric-vN.md` and
`codebook-vN.md`. The prompt identity is `granular-v8:<hash>`; v7 keeps
`granular-v7:<hash>` unchanged, and a compiled taxonomy saved without a version
is treated as v7.

## The label set

| axis | v8 | v7 |
| --- | --- | --- |
| topic parents | 60 | 60 |
| topic subtopics | 373 | 349 |
| narratives | 145 | 121 |
| frames | 23 | 22 |
| evidence | 16 | 16 |
| populations | 13 | 9 |

The bullets below are the first pass; the corpus review's changes are listed
in its own section.

- **Thirteen new subtopics** for the largest gaps the annotators sent to bare
  parents or `topic:other`: `metabolic.mitochondria_energy`,
  `procedures.lab_testing`, `food.general_nutrition`,
  `vaccines.efficacy_response`, `stress.mind_body`, `mental.causes_models`,
  `wellness.energy_fatigue`, `fertility.conception_general`,
  `procedures.blood_cell_therapies`, `cancer_alt.integrative_adjuncts`,
  `dementia_ageing.cognitive_ageing`, `neuro.other_neurological`,
  `health_system.disability_access`; about twenty definitions extended, double
  listings removed, and boundary sentences added for the topic pairs coders
  could not separate.
- **Narratives state a bold core proposition** followed by elaborations; a
  narrative applies when its core is invoked, and a premise without the
  contested conclusion does not invoke it. Twenty-one narratives added (each
  coded `unlisted_narrative` independently by more than one annotator, e.g.
  `alcohol_moderate_protective`, `stealth_infections_root`,
  `vaccines_for_profit`, `alzheimers_reversible`), three renamed or split
  (`outbreak_engineered`, `doctors_paid_to_prescribe`,
  `antidepressants_ineffective` + `chemical_imbalance_myth`).
- **`frame:industry_distrust`** for insurers, hospital systems, cosmetics,
  chemical and tech companies and philanthropic funders; explicit thresholds
  for frames coders triggered on single words (root cause, fear, MAHA,
  optimization, toxins).
- **Populations** `young_adults`, `midlife`, `military_veterans`, with age-word
  mappings.

## The codebook

The rules that moved the most disagreement in the v2 notes:

- **Certainty markers by function, not form**: minimizing "only", scope
  "every", factual superlatives and "a lot of" counting studies are not
  markers; about forty more boosters and hedges are listed; approximated
  universals are hedged; attribution is a marker only when the speaker does not
  vouch for it, and never for a rebutted claim.
- **Narrative implicature**: product attributes and timing alone do not
  invoke a narrative; coined terms do.
- **Discourse role** for mockery, played clips, relayed rebuttals and
  retracted jokes; the topic detection of a debunk is asserted.
- **Evidence**: a study is specific only with a finding plus a named author,
  journal, institution, dataset, or a year with a design; who counts as a
  practitioner; officials' findings, endorsements, certifications and "no
  evidence".
- **Ads and scope**: what delimits an ad read; the health-content test for
  ads; true crime and war only when an injury or cause of death is described;
  commercialization for any present speaker's offering.
- **Claims and products**: second-hand cases extracted as the general claim
  they support; claim types for testing, associations and contamination;
  narrative links for negations; one product mention per offering; spelling
  repair; product-type guidance.

## Corpus review

The first pass was driven by 320 benchmark windows. The second checked every
label against the corpus itself: 15 Opus agents searched all ~145.6k transcribed
episodes (~700 podcasts) with keyword queries (`analysis/corpus_text/cq.py`) and
read real passages, one agent per slice of the label set plus an open-ended
coverage audit; editor agents then accepted, modified or rejected each proposal.
Everything is in `taxonomy/v8-corpus-review/` (reports, decisions, patches).

What it found:

- **Every label is findable**, but for many the raw keyword volume is dominated
  by talk that is not health content: COVID as a time marker (~43k episodes),
  recreational alcohol and cannabis as scenery (~40k and ~28k), true-crime
  injury and death narration (~16.5k), sports injury reports and "healthy" meaning
  available to play, loose psychiatric words ("narcissist", "PTSD from…"),
  political issue lists (abortion appears in ~11.8k episodes, mostly election
  lists), and repeated ads (biologics in ~3.2k episodes, a single chicken ad in
  ~3.6k, "Zero Sugar" brand names, drug-ad safety boilerplate). The coverage
  audit of 160 blind-sampled health passages found 66% fit a subtopic cleanly,
  8% needed a bare parent or `topic:other`, 16% were ambiguous and 10% sat on an
  unclear health-content boundary: most misses are boundary rules, not missing
  subjects.
- So most of the codebook change is **section 3**: a boundary test with real
  include/exclude examples for each of those high-volume cases, an expanded ad
  test (3.3) with a worked table for the highest-volume ad types, read-ending and
  back-to-back rules (4.1), and that prescription-drug safety statements add no
  topics or claims. Certainty markers gained the common real forms the lists
  missed ("I feel like", "for sure", "a hundred percent", "most likely"); coined
  terms were separated from slogans that carry no proposition ("sick care",
  "gender ideology", "Great Reset", "terrain theory"); section 2 lists recurring
  speech-recognition variants ("Aura ring" for Oura, ACIP heard as "ASAP").
- **Label set**: 305 label definitions, names or example lists revised to match how people
  actually talk, with boundary sentences for the confusions seen in real
  passages. Added 12 subtopics (`food.salt_sodium`,
  `cardiovascular.clots_blood_disorders`, `cancer.colorectal_cancer`,
  `chronic_complex.persistent_infections`, `chronic_complex.exposure_syndromes`,
  `acute_care.near_death_experiences`, `mental.psychiatric_care`,
  `sleep.dreams_parasomnias`, `sexual.sex_education`, `gender.trans_athletes`,
  `recovery.training_recovery`, `environment.military_occupational`), 8
  narratives (`social_media_youth_mental_health`, `mental_illness_not_real`,
  `pharma_ads_control_media`, `salt_fears_overblown`,
  `dietary_guidelines_caused_obesity`, `mind_cures_disease`,
  `normal_labs_miss_disease`, `trauma_stored_in_body`) and
  `population:racial_ethnic_groups`. Removed six narratives that are essentially
  never voiced (`vitamin_a_toxicity`, `heart_not_pump`, `nsaids_worsen_covid`,
  `cancer_fungus_parasite`, `cancer_epidemic_young`, `sugar_hyperactivity`) and
  merged `peds.fat_loss_drugs_ped` into `weight.diet_pills_fat_burners`.

**Prompt size.** The assembled v8 prompt is about 356k characters (roughly 85k
to 90k tokens): the codebook grew from ~7.9k to ~15k words and the label
definitions carry more boundary sentences. It is identical for every window,
so it is prompt-cached; but a local vLLM server needs `--max-model-len` of
about 196608 or more to leave room for the window and high-effort reasoning.
