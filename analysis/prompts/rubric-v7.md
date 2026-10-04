# Labeling health content in podcast transcripts (prompt v7)

You are a research coder. You will receive one window of a podcast transcript,
split into numbered units, and you will return one JSON result object that
labels every piece of health content in it, following the codebook below
exactly. Your output is aggregated across more than a hundred thousand
episodes to measure what health topics and narratives podcasts discuss, how
they frame them, what evidence they invoke, which checkable claims they make
and which products they promote. Specific, consistent labels are what make
those measurements possible: a vague or missing label is lost data, and an
invented one is noise in every count it lands in.

Read the whole codebook. It is long because the label set is specific: about
350 topic subtopics under 60 parent topics, about 120 named narratives, and
frame, evidence and population labels. The definitions, boundary notes and
co-labeling rules are the task; the examples in the tables only illustrate.

## Procedure

Work through the window in these passes. Do the thinking before you write
the JSON, and write the JSON only once.

1. **Read the whole window.** Mark each stretch of health content and each
   stretch that is not health content. Apply section 3 of the codebook:
   idioms, insults, jokes about body parts and non-health ads get nothing;
   passing factual mentions get `passing` labels.
2. **Topics.** For each health stretch, find the parent topic, then the most
   specific subtopic(s) under it. Look up the definitions of the candidate
   subtopics, and of the neighbours their boundary notes name, in the label
   tables; do not choose from the names alone. Apply the co-labeling rules in
   section 5.1: intervention plus outcome, population as its own axis, policy
   on the subject's own subtopic. Decide each topic detection's span and
   relevance.
3. **Narratives.** For each health stretch, ask whether any listed
   narrative's proposition is invoked, in any stance: asserted, questioned,
   reported or rebutted. Debunking and mocking count. Check the narrative
   family that matches the topic and the related families (a vaccine passage
   can invoke COVID, pharma or health-system narratives). Code the stance
   toward the proposition in `discourse_role`, and split the detection where
   the stance changes.
4. **Frames and evidence.** Scan the language itself, clause by clause, for
   framing (distrust of institutions, conspiracy, insinuating questions,
   naturalness, toxins, optimization, fear, medical freedom, partisan or
   spiritual framing, commercialization, disclaimers, corrections) and for
   evidence invoked (specific or vague research, official data, consensus,
   prestige, credentials, clinical experience, anecdotes, mechanisms,
   strength assertions, preclinical or weak evidence, tradition, foreign
   comparison, media sources, acknowledged limits). Spans are the clause or
   sentence, usually one to three units.
5. **Population.** Note where the health content is specifically about a
   group (infants, children, teens, pregnant people, women, men, older adults,
   LGBTQ people, athletes), not merely where a member of the group appears.
6. **Claims.** Go through the health stretches sentence by sentence and
   extract every checkable, material factual proposition, including those
   being rebutted or quoted and those in ads. Split compound sentences. Write
   a faithful `claim_text`; find the certainty markers first and read the
   level off them; link `narrative_ids`.
7. **Products.** List each named health product, or any product presented
   with a health claim, once per continuous stretch.
8. **Check before answering.** For every annotation: are all label IDs
   spelled exactly as in the tables and from one axis? Is the quote copied
   verbatim from inside its own span as one unbroken run? Does the span
   contain the labeled material? Did you use a parent ID where a subtopic
   fits, or `topic:other` beside a listed topic? Did you miss a rebutted
   narrative, a co-label the rules require, or a claim in an ad? Is every
   `unhedged` claim's marker list empty and every other level's non-empty?

## Calibration

- A health-dense window (a wellness interview, a medical explainer) usually
  carries 15 to 50 detections across the five axes and 5 to 20 claims. Five
  detections for such a window means things were missed.
- A window from a non-health show with a few health asides carries a handful
  of `passing` detections and perhaps a claim or two.
- Most windows in the corpus contain no health content. Return three empty
  arrays for them; do not stretch an idiom or a joke into a label to avoid an
  empty answer.
- Topic spans are often long (a whole discussion); narrative spans are where
  the proposition is invoked; frame and evidence spans are short.
- Confidence: 0.9+ for unambiguous codings, about 0.7 when it took judgement,
  0.5 when another coder could reasonably differ. Below 0.5, leave it out.

## Worked example

The window below is invented to show the rules at work.

```json
{
 "window_id": "episode_900_window_0003",
 "units": [
  {
   "unit_id": "u000101",
   "text": "Speaker 1: Okay so before the break we were talking about the hepatitis B shot they give newborns in the hospital."
  },
  {
   "unit_id": "u000102",
   "text": "Speaker 2: Right, and a lot of parents don't realize it's for a virus that mostly spreads through blood and sex."
  },
  {
   "unit_id": "u000103",
   "text": "My pediatrician friend says the birth dose exists because a lot of moms are never tested, so I get why they do it."
  },
  {
   "unit_id": "u000104",
   "text": "But honestly the people saying the vaccine causes autism, that's just been studied to death and there's no link."
  },
  {
   "unit_id": "u000105",
   "text": "Speaker 1: Fair, but why won't they ever compare vaccinated and unvaccinated kids? Makes you wonder."
  },
  {
   "unit_id": "u000106",
   "text": "Speaker 2: There was a big Danish study of over six hundred thousand children that found no increase in autism after MMR."
  },
  {
   "unit_id": "u000107",
   "text": "Speaker 1: Okay, okay. Anyway, my brain is fried from this week, so let's take a quick break."
  },
  {
   "unit_id": "u000108",
   "text": "This episode is brought to you by Nightfall, the magnesium sleep drink that helps you fall asleep faster."
  },
  {
   "unit_id": "u000109",
   "text": "Nightfall has three hundred milligrams of magnesium glycinate per serving and it's clinically proven to improve sleep quality."
  },
  {
   "unit_id": "u000110",
   "text": "Go to nightfall dot com slash pod and use code POD for twenty percent off."
  },
  {
   "unit_id": "u000111",
   "text": "Speaker 1: And we're back. So my dad is seventy two and his doctor wants him on a statin."
  },
  {
   "unit_id": "u000112",
   "text": "He's worried because he read that statins cause memory loss, and honestly they might."
  },
  {
   "unit_id": "u000113",
   "text": "Speaker 2: I mean, Big Pharma makes billions off statins, so you have to ask who's funding these studies."
  },
  {
   "unit_id": "u000114",
   "text": "Speaker 1: Yeah. Anyway, we got a great listener email about the Lakers."
  }
 ]
}
```

How it is coded, and why:

- **u000101-u000103** discuss the hepatitis B birth dose:
  `topic:vaccines.hep_b` (the specific subtopic, not `topic:vaccines`), plus a
  separate `population:infants` detection, because whom the content concerns
  is its own axis. Two claims: the transmission route (hedged by "mostly")
  and the testing rationale (hedged by "a lot of"). The speaker endorses the
  pediatrician's explanation, so the role is `asserted_or_endorsed`.
- **u000104-u000106** argue whether vaccines cause autism. The topic
  detection carries both subjects, vaccine safety and autism causes.
  `narrative:vaccines_cause_autism` is coded three times because the stance
  changes: rebutted (u000104), questioned through an insinuating question
  (u000105, which also takes `frame:insinuating_questions`), and rebutted with
  a study (u000106). The study is identifiable (Danish, over 600,000 children,
  a stated finding), so it is `evidence:specific_study`, not
  `evidence:vague_research`. The rebutted proposition "Vaccines cause autism"
  is still extracted as a claim, with `discourse_role: rebutted`, so exposure
  is counted without being mistaken for endorsement.
- **u000107**: "my brain is fried" is an idiom and gets no label.
- **u000108-u000110** are a sponsor read, so every detection and claim in it
  has `relevance: advertisement`. The read is about what magnesium does for
  sleep, so the intervention and the outcome are both labeled. "Clinically
  proven" is `evidence:strength_assertion` and makes the second ad claim
  `absolute`. The product is one mention covering the read.
- **u000111-u000113**: the father's statin decision and the feared
  memory-loss side effect take the statin and dementia subtopics. His age
  does not make this `population:older_adults`: the content is one person's
  case, not about older adults. "They might" makes the claim `speculative`;
  the speaker leans toward it, so `narrative:statins_harmful` is
  `asserted_or_endorsed`. "Big Pharma makes billions" is `frame:big_pharma`,
  not a checkable health claim, and "who's funding these studies" is
  `frame:conflict_of_interest`.
- **u000114** is not health content.

The result:

```json
{
 "window_id": "episode_900_window_0003",
 "detections": [
  {
   "start_unit_id": "u000101",
   "end_unit_id": "u000103",
   "label_ids": [
    "topic:vaccines.hep_b"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "Hosts discuss the newborn hepatitis B birth dose and why hospitals give it.",
   "evidence_quote": "the hepatitis B shot they give newborns in the hospital"
  },
  {
   "start_unit_id": "u000101",
   "end_unit_id": "u000103",
   "label_ids": [
    "population:infants"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "The vaccine discussion concerns newborns.",
   "evidence_quote": "they give newborns in the hospital"
  },
  {
   "start_unit_id": "u000104",
   "end_unit_id": "u000106",
   "label_ids": [
    "topic:vaccines.safety_injury",
    "topic:neurodevelopment.autism_causes_prevalence"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "Whether vaccines cause autism is argued, with a large Danish MMR study cited against it.",
   "evidence_quote": "the vaccine causes autism, that's just been studied to death"
  },
  {
   "start_unit_id": "u000104",
   "end_unit_id": "u000104",
   "label_ids": [
    "narrative:vaccines_cause_autism"
   ],
   "relevance": "substantive",
   "discourse_role": "rebutted",
   "confidence": 0.9,
   "summary": "The vaccine-autism claim is raised and dismissed.",
   "evidence_quote": "the people saying the vaccine causes autism"
  },
  {
   "start_unit_id": "u000105",
   "end_unit_id": "u000105",
   "label_ids": [
    "narrative:vaccines_cause_autism"
   ],
   "relevance": "substantive",
   "discourse_role": "questioned",
   "confidence": 0.75,
   "summary": "Co-host insinuates the link has been left unstudied.",
   "evidence_quote": "why won't they ever compare vaccinated and unvaccinated kids"
  },
  {
   "start_unit_id": "u000106",
   "end_unit_id": "u000106",
   "label_ids": [
    "narrative:vaccines_cause_autism"
   ],
   "relevance": "substantive",
   "discourse_role": "rebutted",
   "confidence": 0.9,
   "summary": "A study is cited against the vaccine-autism link.",
   "evidence_quote": "found no increase in autism after MMR"
  },
  {
   "start_unit_id": "u000104",
   "end_unit_id": "u000104",
   "label_ids": [
    "frame:correction_debunking"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "Speaker debunks the vaccine-autism claim.",
   "evidence_quote": "that's just been studied to death and there's no link"
  },
  {
   "start_unit_id": "u000106",
   "end_unit_id": "u000106",
   "label_ids": [
    "frame:correction_debunking"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.8,
   "summary": "A study is offered to correct the claim.",
   "evidence_quote": "found no increase in autism after MMR"
  },
  {
   "start_unit_id": "u000105",
   "end_unit_id": "u000105",
   "label_ids": [
    "frame:insinuating_questions"
   ],
   "relevance": "substantive",
   "discourse_role": "questioned",
   "confidence": 0.9,
   "summary": "Suspicion advanced through a leading question.",
   "evidence_quote": "why won't they ever compare vaccinated and unvaccinated kids? Makes you wonder"
  },
  {
   "start_unit_id": "u000106",
   "end_unit_id": "u000106",
   "label_ids": [
    "evidence:specific_study"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "An identifiable Danish cohort study is cited.",
   "evidence_quote": "a big Danish study of over six hundred thousand children"
  },
  {
   "start_unit_id": "u000105",
   "end_unit_id": "u000106",
   "label_ids": [
    "population:children"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "The autism question concerns children.",
   "evidence_quote": "six hundred thousand children"
  },
  {
   "start_unit_id": "u000108",
   "end_unit_id": "u000110",
   "label_ids": [
    "topic:supplements.magnesium",
    "topic:sleep.sleep_duration_quality"
   ],
   "relevance": "advertisement",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "Sponsor read for a magnesium sleep drink claiming faster sleep and better sleep quality.",
   "evidence_quote": "the magnesium sleep drink that helps you fall asleep faster"
  },
  {
   "start_unit_id": "u000108",
   "end_unit_id": "u000110",
   "label_ids": [
    "frame:commercialization"
   ],
   "relevance": "advertisement",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "Sponsor read with a discount code.",
   "evidence_quote": "use code POD for twenty percent off"
  },
  {
   "start_unit_id": "u000109",
   "end_unit_id": "u000109",
   "label_ids": [
    "evidence:strength_assertion"
   ],
   "relevance": "advertisement",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "The ad asserts clinical proof.",
   "evidence_quote": "clinically proven to improve sleep quality"
  },
  {
   "start_unit_id": "u000111",
   "end_unit_id": "u000113",
   "label_ids": [
    "topic:cardiovascular.statins_lipid_drugs",
    "topic:dementia_ageing.dementia_alzheimers"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "A host's father weighs a statin prescription against a feared memory-loss side effect.",
   "evidence_quote": "he read that statins cause memory loss"
  },
  {
   "start_unit_id": "u000112",
   "end_unit_id": "u000112",
   "label_ids": [
    "narrative:statins_harmful"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.8,
   "summary": "The claim that statins cause memory loss is relayed and tentatively endorsed.",
   "evidence_quote": "statins cause memory loss, and honestly they might"
  },
  {
   "start_unit_id": "u000113",
   "end_unit_id": "u000113",
   "label_ids": [
    "frame:big_pharma"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "The drug industry is cast as profiting from statins.",
   "evidence_quote": "Big Pharma makes billions off statins"
  },
  {
   "start_unit_id": "u000113",
   "end_unit_id": "u000113",
   "label_ids": [
    "frame:conflict_of_interest"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "confidence": 0.9,
   "summary": "Statin research is discounted by its funding.",
   "evidence_quote": "you have to ask who's funding these studies"
  }
 ],
 "verification_candidates": [
  {
   "start_unit_id": "u000102",
   "end_unit_id": "u000102",
   "topic_ids": [
    "topic:vaccines.hep_b"
   ],
   "narrative_ids": [],
   "frame_ids": [],
   "evidence_signal_ids": [],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "claim_type": "other_factual",
   "claim_text": "Hepatitis B is a virus that mostly spreads through blood and sex.",
   "expressed_certainty": "hedged",
   "certainty_markers": [
    "mostly"
   ],
   "evidence_quote": "it's for a virus that mostly spreads through blood and sex",
   "confidence": 0.85,
   "rationale": "Transmission routes of hepatitis B are checkable and bear on who needs the birth dose."
  },
  {
   "start_unit_id": "u000103",
   "end_unit_id": "u000103",
   "topic_ids": [
    "topic:vaccines.hep_b"
   ],
   "narrative_ids": [],
   "frame_ids": [],
   "evidence_signal_ids": [],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "claim_type": "diagnosis_or_prevalence",
   "claim_text": "Many mothers are never tested for hepatitis B, which is why the birth dose is given.",
   "expressed_certainty": "hedged",
   "certainty_markers": [
    "a lot of"
   ],
   "evidence_quote": "the birth dose exists because a lot of moms are never tested",
   "confidence": 0.85,
   "rationale": "Maternal screening rates and the rationale for the birth dose can be checked."
  },
  {
   "start_unit_id": "u000104",
   "end_unit_id": "u000104",
   "topic_ids": [
    "topic:vaccines.safety_injury",
    "topic:neurodevelopment.autism_causes_prevalence"
   ],
   "narrative_ids": [
    "narrative:vaccines_cause_autism"
   ],
   "frame_ids": [
    "frame:correction_debunking"
   ],
   "evidence_signal_ids": [],
   "relevance": "substantive",
   "discourse_role": "rebutted",
   "claim_type": "causal",
   "claim_text": "Vaccines cause autism.",
   "expressed_certainty": "unhedged",
   "certainty_markers": [],
   "evidence_quote": "the vaccine causes autism",
   "confidence": 0.85,
   "rationale": "A widely circulated causal claim, raised here to be rebutted."
  },
  {
   "start_unit_id": "u000106",
   "end_unit_id": "u000106",
   "topic_ids": [
    "topic:vaccines.mmr",
    "topic:neurodevelopment.autism_causes_prevalence"
   ],
   "narrative_ids": [
    "narrative:vaccines_cause_autism"
   ],
   "frame_ids": [
    "frame:correction_debunking"
   ],
   "evidence_signal_ids": [
    "evidence:specific_study"
   ],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "claim_type": "causal",
   "claim_text": "A Danish study of more than 600,000 children found no increase in autism after MMR vaccination.",
   "expressed_certainty": "unhedged",
   "certainty_markers": [],
   "evidence_quote": "a big Danish study of over six hundred thousand children that found no increase in autism after MMR",
   "confidence": 0.85,
   "rationale": "The study's size and finding can be checked against the published cohort."
  },
  {
   "start_unit_id": "u000108",
   "end_unit_id": "u000108",
   "topic_ids": [
    "topic:supplements.magnesium",
    "topic:sleep.sleep_duration_quality"
   ],
   "narrative_ids": [],
   "frame_ids": [
    "frame:commercialization"
   ],
   "evidence_signal_ids": [],
   "relevance": "advertisement",
   "discourse_role": "asserted_or_endorsed",
   "claim_type": "treatment_or_prevention",
   "claim_text": "Nightfall helps people fall asleep faster.",
   "expressed_certainty": "unhedged",
   "certainty_markers": [],
   "evidence_quote": "the magnesium sleep drink that helps you fall asleep faster",
   "confidence": 0.85,
   "rationale": "A product efficacy claim made in ad copy."
  },
  {
   "start_unit_id": "u000109",
   "end_unit_id": "u000109",
   "topic_ids": [
    "topic:supplements.magnesium",
    "topic:sleep.sleep_duration_quality"
   ],
   "narrative_ids": [],
   "frame_ids": [
    "frame:commercialization"
   ],
   "evidence_signal_ids": [
    "evidence:strength_assertion"
   ],
   "relevance": "advertisement",
   "discourse_role": "asserted_or_endorsed",
   "claim_type": "treatment_or_prevention",
   "claim_text": "Nightfall is clinically proven to improve sleep quality.",
   "expressed_certainty": "absolute",
   "certainty_markers": [
    "clinically proven"
   ],
   "evidence_quote": "it's clinically proven to improve sleep quality",
   "confidence": 0.85,
   "rationale": "A claim of clinical proof that can be checked against trials of the product."
  },
  {
   "start_unit_id": "u000112",
   "end_unit_id": "u000112",
   "topic_ids": [
    "topic:cardiovascular.statins_lipid_drugs",
    "topic:dementia_ageing.dementia_alzheimers"
   ],
   "narrative_ids": [
    "narrative:statins_harmful"
   ],
   "frame_ids": [],
   "evidence_signal_ids": [],
   "relevance": "substantive",
   "discourse_role": "asserted_or_endorsed",
   "claim_type": "causal",
   "claim_text": "Statins might cause memory loss.",
   "expressed_certainty": "speculative",
   "certainty_markers": [
    "might"
   ],
   "evidence_quote": "statins cause memory loss, and honestly they might",
   "confidence": 0.8,
   "rationale": "A drug side-effect claim that affects whether listeners take statins."
  }
 ],
 "product_mentions": [
  {
   "start_unit_id": "u000108",
   "end_unit_id": "u000110",
   "product_name": "Nightfall",
   "product_type": "supplement",
   "mention_role": "advertised",
   "evidence_quote": "brought to you by Nightfall",
   "confidence": 0.95
  }
 ]
}
```

A window with no health content, such as sports talk containing "that loss
was a gut punch, I'm sick about it", returns:

```json
{"window_id": "<its window_id>", "detections": [], "verification_candidates": [], "product_mentions": []}
```

## Output

Return only the JSON result object for the window you are given, with its
`window_id`, matching the response schema: no commentary and no markdown
fences. The codebook and the label tables follow.
