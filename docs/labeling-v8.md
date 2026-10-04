# Granular labeling scheme, revision v8

v8 is the current revision of the granular scheme described in
`docs/labeling-v7.md`: the same five axes, file format, pipeline and result
schema (`topic-labeling-v5`), with the label set and codebook revised from what
the benchmark-v2 reference annotators reported. Their ~3,400 ambiguity notes are
synthesized in `benchmark/v2/codebook-v8-proposal.md`; v8 applies it.

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
| topic subtopics | 362 | 349 |
| narratives | 143 | 121 |
| frames | 23 | 22 |
| evidence | 16 | 16 |
| populations | 12 | 9 |

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
