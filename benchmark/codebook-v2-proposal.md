# Codebook v2 proposal

What the v1 reference passes, the adjudication and the label-confusion
analysis say the codebook should settle. Nothing here changes v1: every
round-2 annotation still uses `analysis/benchmark/codebook.md` as it stands,
so items stay comparable. Adopting any of these is a new `benchmark_version`
and, for rules that change how existing atoms would be coded, a re-annotation
of the affected attribute.

Evidence base: 65 corpus and synthetic reference bundles from one Opus and
two Sonnet passes (each reported the ambiguities it hit), 18 adjudication
bundles over 1,622 singletons (90 rejected, with grounds), and the same-axis
label pairs different annotators put on the same span
(`agreement.json: label_adjacency`).

## 1. Certainty markers

The single largest source of attribute disagreement (expressed_certainty
alpha 0.70; three annotators coded the modal "can" three different ways).

Proposed rules:

- **Bare "can" / "could" as capacity** ("magnesium can help", "can kill
  you") is not a certainty marker. Code `unhedged` unless another marker
  is present. "Could" / "might" / "may" as epistemic possibility stay
  `speculative`.
- **Quantifier hedges** ("in most people", "most of the time", "a lot of
  people", "tends to", "generally", "often", "usually") are `hedged`.
  "Some people say" / "I've heard" are `speculative` (they attribute rather
  than soften).
- **Approximators and ASR filler** ("like forty minutes", "basically",
  "kind of", "up to X%", "something like") are not markers.
- **Boosters** add "we know that", "there is no doubt", "clearly",
  "every single time", "the number one", "guaranteed"; "very good
  evidence that" is an evidence-strength signal, not a booster.
- **Statistical idioms** that contain a marker word ("twice as likely",
  "more likely to") are not hedges.
- **Mixed markers in one span**: a hedge wins over a booster; a
  `speculative` marker wins over a `hedged` one. State this ordering.
- **Hedges inside quoted speech** code the quoted speaker's rendering (the
  claim is `reported_or_quoted` on the discourse axis); do not re-hedge
  for the reporter.

## 2. Topics that are missing or that list the same term

Confusion pairs seen at least four times, and annotators' fallback to
`other_health_topic` for real gaps.

- Add **Endocrine & Thyroid** (thyroid disease, hormone replacement outside
  the gendered topics, adrenal, cortisol); today thyroid content lands in
  Autoimmune (via Hashimoto's), Supplements, or the catch-all.
- Add **Allergy & Immunology** (seasonal and food allergies, anaphylaxis),
  or fold allergies explicitly into Autoimmune / Immune Health.
- Add **Bone & Joint** examples (osteoporosis, TMJ, orthodontics) to Pain /
  Musculoskeletal, and referred pain to Cardiometabolic or Pain by the
  organ referred from; say so.
- **Food & Nutrition vs Functional Nutrition & Supplements** (7 confusions):
  a nutrient discussed as consumed in food is Food & Nutrition; a nutrient
  discussed as a pill, powder, drink mix, dose or deficiency to correct is
  Supplements; electrolyte and protein powders, melatonin gummies and zinc
  deficiency are Supplements. Remove "electrolytes" and "melatonin" from
  the Food and Sleep example lists.
- **Cardiometabolic vs Weight Loss / Metabolic** (6): weight, body
  composition, calories, insulin resistance discussed as a weight matter
  are Weight Loss; heart, blood pressure, lipids, diabetes as disease are
  Cardiometabolic. Move "insulin resistance" to one list only.
- **COVID vs Health-Care System** (5): pandemic-era policy and institutional
  conduct about COVID stay COVID; general trust in doctors or hospitals is
  Health-Care System.
- **Food & Nutrition vs MAHA politics** (5): the food itself (seed oils,
  dyes) is Food & Nutrition even in MAHA vocabulary; the movement, its
  figures and policy asks are MAHA. The MAHA frames carry the vocabulary.
- **Supplements vs Longevity** (5): a compound discussed for ageing (NR,
  NAD, rapamycin) is Longevity; the same compound as a product to buy is
  Supplements. Keep both where both are discussed.
- **Vaccines vs Public-Health Policy**: vaccine mandates are Vaccines; drop
  "mandates" from the policy list.
- **Sleep vs EMF** for blue light: Sleep. Remove blue light from EMF.
- **Hair loss**: Dermatology unless hormones are discussed.
- `other_health_topic` is never a second label on a span that carries a
  listed topic (the most common adjudication rejection); it is only for
  health content no listed topic covers, with the subject named in the
  summary.

## 3. What counts as health content

No minimum-content threshold exists today, and annotators split on it.

- **Include as `passing`**: a named condition, injury, treatment, drug or
  body process mentioned as a fact about a person or event (a public
  figure's AFib, an athlete's Achilles, a character's hospitalisation) even
  in true crime or sports.
- **Exclude**: idiomatic uses ("a healthy diet of both", "my brain is
  fried"), psychiatric words as insults ("narcissist", "psycho"), a body
  part named in a joke with no procedure or condition, comedic weight
  numbers, "health" as a bare hypothetical reason, a podcast's tagline.
- **Ads for non-health products inside health shows** are not health
  content and yield no product mention; a health-adjacent product in a
  non-health show (a baby monitor, an emergency food kit) is not either
  unless a health effect is claimed.

## 4. Product mentions

- A product is a **thing a listener could buy or sign up for**: goods,
  supplements, apps, services, clinics, practitioners, books, courses.
  Not: retail venues, social platforms, a hospital as an institutional
  actor, a charity, a person, a podcast's own episode.
- **Own-product pitches**: a host's own supplement, programme, membership
  or free guide is `own_product`; relevance is `advertisement` only inside
  a delimited read (sponsor framing, code, URL, "back to the show").
- **Unsponsored personal recommendation** of a brand is `recommended`; a
  brand the host uses but does not push is `neutral`; Commercialization is
  not applied to either.
- **Product types**: add `nicotine_or_tobacco`, `cookware_or_household`,
  `service_membership`; say that a media personality's brand is
  `book_or_media`.
- **ASR-garbled brand names** are repaired only when the repair is a
  spelling of what was clearly said ("A G one" to AG1); a name that needs
  outside knowledge to reconstruct is recorded as transcribed with lowered
  confidence; two garbled forms of one name in one stretch are one mention.

## 5. Discourse role on the topic axis

Annotators disagree whether a topic detection inherits the role of the
claim inside it (alpha 0.57, the lowest attribute).

- The **topic detection's role is the speaker's stance toward the
  passage**: `reported_or_quoted` when the whole stretch relays someone
  else's view, `rebutted` when the stretch is the host arguing against a
  claim, `questioned` when it is raised as an open question, otherwise
  `asserted_or_endorsed`. Individual claims inside keep their own role.
- A **debunking passage** is one `asserted_or_endorsed` topic detection
  with the correction frame; the corrected claim is a `rebutted` claim.
- A speaker who voices both sides and then endorses one is
  `asserted_or_endorsed` on the topic; the relayed side is a
  `reported_or_quoted` claim.

## 6. Claim extraction

- **Not claims**: ad puffery with no health proposition ("switch therapists
  at no charge", "six mattress models"), pure political rhetoric ("the
  agency is captured"), imperatives ("do not take the shot"), retracted
  jokes, a preference ("I really like resveratrol"), a personal result
  ("my plaque went from X to Y") unless a general proposition is stated
  alongside it.
- **Claim text must be self-contained and no sharper than the transcript**:
  resolve the referent, add nothing the speaker did not say (a date, a
  named cause). A claim whose substance sits outside its span is invalid.
- **Claim types**: `institutional_or_conspiracy` requires an allegation of
  concealment, falsification, suppression or purchase; inaction, legal
  arrangements and grant funding are `other_factual`. Adverse effects
  stated as X causes Y are `causal`; statements about how likely or severe
  a harm is are `risk_or_safety`. A product's stated composition or dose
  is `other_factual`, not `mechanism`.
- **Compound sentences** that mix a prevalence claim with a causal or
  institutional one are split into one claim per proposition.

## 7. Frames and evidence signals

- A frame is applied only where the **rhetoric itself** occurs, not as a
  comment on the people named ("these biohackers have lost the plot" is
  not biohacking framing), and not where it is denied ("no big pharma
  conspiracy here").
- `conspiracy_cover_up` requires an allegation of coordination or
  concealment; vague "they know what they're doing" is
  `government_institution_distrust`.
- `scientific_study_citation` needs a study, trial or paper; a Nobel prize
  or a physician's title is `prestige_science_invocation` or
  `credential_appeal`; "doctor recommended" and "dermatologist recommended"
  are `evidence_strength_claim` (say so once, in one place).
- `weak_evidence_extrapolation_signal` codes the kind of evidence the
  speaker offers (animal, in vitro, anecdote, preliminary), never the
  annotator's doubt about a plain citation.
- `personal_experience_evidence` requires the experience to be offered as
  grounds for a general conclusion; a clinician's "my patients" counts,
  an experience the speaker disclaims as evidence does not.
- The evidence quote must carry the labeled material; one quote is not
  reused for several labels on the same span.

## 8. Spans and quotes

- Quotes may cross a unit boundary but not a speaker turn.
- A topic detection is split only at unrelated material of more than one
  unit; a teaser that names several topics in one breath is one `passing`
  detection per topic.
- Duplicate mentions of one product inside one continuous stretch are one
  mention; an unrelated segment of at least two units between them makes
  two.

## What to re-annotate if adopted

Sections 1, 5 and 6 change attribute values on existing atoms
(expressed_certainty, discourse_role, claim_type, claim inclusion) and would
need a re-coding pass on those attributes; sections 2, 3, 4, 7 and 8 change
which atoms exist and would need the full reference passes rerun on affected
items. A cheaper first step is a v1.1 that adopts only section 1 (markers)
and the `other_health_topic` rule, re-codes certainty on the existing
claims, and re-adjudicates the 90 rejected singletons against the clarified
text.
