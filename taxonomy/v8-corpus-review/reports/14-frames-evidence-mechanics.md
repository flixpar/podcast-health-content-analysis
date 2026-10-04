# Frames, evidence, population and codebook mechanics: corpus review

All counts are from `cq.py count` over the ~145,600-episode corpus (segments / episodes / podcasts). A segment is a long transcript chunk (often several sentences), so proximity patterns like `X.{0,100}health-word` only approximate "used about health". Quotes are cited as (ep, seg).

## Summary

- **Ad test (c) creates a large false-positive class.** "Zero Sugar" is part of the product name in Coca-Cola, Pepsi and Sprite spots (4,911 segments; the soda-brand set is 7,763 eps / 224 podcasts). Read literally, rule (c) in section 3 makes every one of these spots health content with a product mention. A free-from word that is only part of a brand name should not pass the test.
- **Ad boundaries.** Most reads end with no "back to the show" line: the call to action or legal tail ("Terms apply", "Gambling problem? Call...") runs straight into show content. In (70882, 6), Rogan's Visible ad runs straight into the Wakefield retraction. Ad breaks also chain several spots back to back. Section 4.1 needs rules for where a read ends, for consecutive spots, and for a closing "Brought to you by X" tag (pharma ads put it last).
- **DTC pharma and DSHEA boilerplate is everywhere, and the codebook says nothing about it.** Drug ads in news and comedy shows ("talk to your doctor about...", side-effect lists) appear in ~7.8k eps / 235 podcasts. The supplement disclaimer ("not been evaluated by the FDA...") appears in 1,253 eps. We need rules for whether these take `frame:disclaimer` (recommend yes) and whether mandated safety lists become claims (recommend no).
- **Certainty-marker lists miss high-frequency real markers.** Near health words, the unlisted hedges "I feel like" (2,094 eps) and "in my opinion / my guess is / I suspect / perhaps / presumably" (2,005 eps) are as frequent as the listed "I believe" (1,604). The unlisted boosters "for sure / no doubt / without a doubt / no question" (1,926) and "the reality is / certainly / well established" (2,227) are as common as the listed "definitely" (3,510). The list has "100%", but ASR spells it out more often ("a hundred percent": 38.7k eps vs "100%": 31.5k).
- **Three marker functions are missing from the rules:**
  - Negated boosters ("I can't say for sure", "we really don't know for sure") are hedges, not boosters.
  - Backchannel agreement ("Yeah, for sure.", "A hundred percent.") is not a marker on the other speaker's claim.
  - "Studies suggest" is listed as a hedge but also behaves like a reporting verb (3,013 segments); the rules should settle which.
- **Frame thresholds mostly fit, with three gaps:**
  - `root_cause_framing`: functional-medicine shows use "root cause" as the name of a method ("root cause medicine", 4,113 eps), with the contrast left implicit.
  - `fear_alarm`: real alarm language is "skyrocketing", "through the roof", "explosion", not "ticking time bomb".
  - `toxin_purity`: "toxins" is often neutral physiology ("the liver filters toxins").
- **Strength assertions are overwhelmingly ad copy.** "Clinically proven", "FDA-approved" and "doctor formulated / developed by scientists / scientifically designed" (the last group: 2,819 eps) are all ad language. The example "gold standard" is mostly finance and media talk; drop it.
- **Population is missing a widely studied group: race and ethnicity.** Race/ethnicity groups appear in health contexts in 651 eps / 119 podcasts: Black maternal mortality, Indigenous autoimmune rates, race-specific vaccine schedules, Tuskegee. I propose ADD `population:racial_ethnic_groups`. Real age phrasing also needs mapping rules:
  - "young people" / "youth" with no age cue (1,286 eps with mental-health, gender or social-media words);
  - "women over 40" type phrases (632 eps), which should take both labels;
  - generational labels (381 eps);
  - tweens and middle schoolers.
- **Evidence additions.** Ancestral and traditional-population arguments ("our ancestors", "hunter-gatherers", "Blue Zones": 6,109 eps / 243 podcasts) have no clear evidence home. Extend `evidence:traditional_use` (ancestral) and `evidence:foreign_comparison` (other populations' outcomes).
- **Product types are missing several common ad categories:** exercise and recovery equipment, period products, unbranded disease-awareness campaigns, and retailers advertised with health claims.

## Label-by-label findings

### Frames

**`frame:root_cause_framing`**
- Query `\broot causes?\b`: 6,053 / 4,113 / 190. Hyman 594 eps, Jockers 294, Thyroid Fixer 154.
- Explicit-contrast query (treat/mask/band-aid + symptoms, "sick care"): 1,230 / 1,060 / 141.
- Verdict: **needs definition change.** In health shows, "root cause" mostly names a method or brand of care, with the contrast implicit:
  - "trained in functional medicine to find the root cause of disease" (183016, 6), a house ad;
  - "helping patients heal using real food and functional medicine as your framework for getting to the root cause" (182604, 0), in a Rupa Health read;
  - "experience in functional and root cause medicine" (190493, 4).
- Coders will split on these under the current "needs that contrast" wording. The one-cause-many-diseases branch does occur: "the root cause of everything is stress. Period. End of story." (176668, 1).
- Non-health uses (migration, despair, education) are common; the existing threshold already handles them.

**`frame:fear_alarm`**
- Hyperbolic trend words near disease words: 1,192 segments. "tsunami of / ticking time bomb / poisoning our kids / epidemic of": 2,439 eps / 224 podcasts. "Epidemic of" is mostly descriptive (Walsh: "this epidemic of obesity might be slightly exaggerated", 207870, 2).
- Verdict: **examples change.** The listed "ticking time bomb" is rare. Real alarm language:
  - "the skyrocketing rates of autism and everything else" (177088, 1);
  - "the autism explosion" (185830, 2);
  - "Anxiety is through the roof. Depression is through the roof." (14613, 0);
  - "all these tsunami of chronic" (175355, 92).
- Without a rule, coders will split on "skyrocketed" (hyperbolic) versus "rising" or "doubled" (descriptive).

**`frame:toxin_purity`**
- `\btoxins\b|toxic load|toxic burden|chemical.free|non.?toxic`: 10,736 / 5,890 / 203.
- Verdict: **needs definition change.** About half the "toxins" hits are neutral physiology or concrete toxicology, not framing:
  - "your liver ... performs more than 500 key functions, like filtering toxins" (192686, 0), a liver-supplement ad;
  - "It's how the body clears toxins." (190143, 467);
  - anthrax as a bioweapon (181670, 17).
- The frame proper looks like "the toxic bucket theory ... we're putting toxins into it every day" (193107, 1). In ad copy: "Most feminine product companies ... are terribly toxic for your physical health" and "the cleanest tampons on the market" (185859, 4-5).

**`frame:optimization`**
- `optimi[sz]e|biohack|peak performance|optimal not normal`: 25,362 / 13,269 / 217. Much of it is business ("optimizing your funnel", 162127, 4).
- Verdict: **fine.** The "applied to the body" threshold works.
- Real optimal-not-normal phrasing: "The recommendations by the government are what you need to avoid scurvy ... it's not about optimizing your biology for the long term" (176639, 5). Health uses are typically "optimize their thyroid" (190849, 70) or "optimize detoxification" (176577, 4).

**`frame:naturalness_appeal`**
- `ancestral|we evolved to|body designed|nature intended|mother nature|synthetic`: 11,310 / 8,273 / 268. Mostly non-health ("ancestral land", "ancestral Wuhan strain", sleep-history stories).
- Verdict: **fine.** Real ad form: "Founded on science and inspired by nature, all Bond Charge products adopt ancestral ways of living" (20503, 5).
- See `evidence:traditional_use` for the ancestral-evidence overlap.

**`frame:disclaimer`**
- Personal and episode disclaimers: 5,155 / 4,444 / 238.
- DSHEA statement: 1,298 / 1,253 / 70 (Mindset Mentor 480 eps, Thyroid Fixer 212, Shawn Ryan 108).
- DTC phrasing ("talk to your doctor about", "side effects include", ...): 10,303 / 7,841 / 235.
- Verdict: **examples change, plus a codebook rule** (see notes). Most disclaimers in the corpus are inside ads:
  - "These statements have not been evaluated by the Food and Drug Administration. This product is not intended to diagnose, treat, cure, or prevent any disease." (188820, 0)
  - "Talk to your doctor about OSA ... This information is provided by Lilly USA LLC." (31661, 0)
  - "Consult a healthcare professional if symptoms persist." (180065, 0), Gatorlyte
- Real host forms: "is for educational purposes only and is not intended to replace professional medical advice" (176628, 3); "definitely consult your healthcare practitioner before doing something like this" (192762, 2).
- "For entertainment purposes" is mostly sleep-story and comedy boilerplate (Get Sleepy 689 eps). It is health content only in a health episode.

**`frame:medical_freedom`**
- `medical freedom|health freedom|informed consent|my body my choice|parental rights|bodily autonomy`: 2,628 / 2,163 / 163. Chiro Hustle has 380 eps.
- Verdict: **needs definition change.** Two problems:
  1. Chiro Hustle's show intro repeats "We believe in supporting medical freedom and family health freedom" (186239, 0; 186253, 0). That is tagline boilerplate in ~380 eps, which would swamp the count.
  2. "Informed consent" is often procedural: "require informed consent and shared decision making" (373156, 12), an HHS plan read out; "request from your doctor ... the informed consent, which is a big document" (75383, 6). That is topic `health_system.ethics_law_privacy`. The frame applies only when consent or choice is invoked as a right against pressure, mandates or withheld information: "we're not really given informed consent about how it can affect things long term" (192433, 3).
- "Parental rights" is often custody law (178493, 0), not health.

**`frame:anti_expert_populist`**
- `do your own research|trust your gut|trust the science|experts were wrong|moms know best`: 1,669 / 1,536 / 174.
- Verdict: **examples change.**
  - "Do your own research" is overwhelmingly true-crime boilerplate (Serialously, Rotten Mango). That is not health content.
  - The health form is sarcastic "trust the science": "people are told to trust the science" (205233, 4); "if you trust the science, then you're going to just trust all of this" (206890, 2).
  - It also occurs in ad copy: "fact-check me on this. Go do your own research on NADH" (38168, 1), a StrongCell read.

**`frame:insinuating_questions`**
- 8,202 / 7,512 / 324; mostly politics and sport.
- Verdict: **fine.** Health example: "The NIH awarded a grant to study ... bat coronavirus at the Wuhan Institute of Virology, really makes you wonder" (204679, 5).

**`frame:maha_framing`**
- `make america healthy again|maha|sickest generation`: 1,382 / 978 / 94.
- Verdict: **examples change (consistency).** The examples list "sickest generation", but the definition says one concern alone is not enough. In the corpus the phrase is rare (57 segments) and usually paired with a second element:
  - "We're the sickest country in the world. That's why we have to fire people at CDC" (439182, 1);
  - "the most drugged nation ... the sickest nation" (174978, 4).
- The example should be labeled as one element, not a trigger.

**Distrust family** (`frame:big_pharma`, `frame:big_food`, `frame:industry_distrust`, `frame:government_distrust`, `frame:media_distrust`, `frame:conflict_of_interest`, `frame:censorship_suppression`, `frame:conspiracy_cover_up`, `frame:anti_mainstream_medicine`)

| Label | Query | Segments / eps / podcasts |
| --- | --- | --- |
| `big_pharma` | big pharma, pharma companies | 3,142 / 2,399 / 154 |
| `big_food` | big food, big ag, food industry, food lobby | 2,579 / 1,714 / 168 (Hyman 284 eps) |
| `government_distrust` | agency "is corrupt/lying", "can't trust the CDC" | 788 / 766 / 127 |
| `media_distrust` | mainstream media, fact-checkers, legacy media | 10,479 / 7,948 / 256 (mostly non-health) |
| `conflict_of_interest` | follow the money, industry-funded, conflict of interest | 3,993 / 3,459 / 221 (Attia 451 eps, mostly disclosure talk) |
| `censorship_suppression` | censored, suppressed research, they don't want you to know | 12,741 / 9,173 / 272 (mostly speech politics) |
| `conspiracy_cover_up` | cover-up, hidden agenda, plandemic | 10,381 / 8,447 / 338 (mostly politics) |
| `anti_mainstream_medicine` | doctors won't tell you, Western medicine, medical school and nutrition | 1,284 / 946 / 123 |

- Verdict: **fine.** The language occurs in every frame. The high counts for media, censorship and cover-up are political talk that the health-content gate removes.
- One real overlap: "sick care" occurs with both root-cause and industry-distrust meanings. The current examples split it sensibly (`industry_distrust`: "the sick-care business"). No change.
- Anti-mainstream medicine also occurs inside ad copy: "most people are unaware that these pain meds do more harm than good. Common side effects include ... in rare cases, even death" (192778, 0). The current rules handle it (ads are `asserted_or_endorsed`).

**`frame:political_partisan`, `frame:spiritual_religious`, `frame:correction_debunking`, `frame:commercialization`**
- Counts:
  - partisan: 30,463 / 17,291 / 206
  - spiritual: 3,685 / 2,747 / 188
  - correction ("myth", "misinformation", "debunk"): 24,624 / 17,892 / 400
  - "use code": 66,252 / 43,492 / 388
- Verdict: **fine.** The language exists. Nothing in the samples suggests the thresholds misfire beyond the general health-content gate.

### Evidence

| Label | Query (abridged) | Segments / eps / podcasts | Verdict |
| --- | --- | --- | --- |
| `specific_study` | "a 2019 study", "published in JAMA / Lancet / NEJM / Nature / BMJ" | 2,212 / 1,827 / 151 | fine |
| `vague_research` | "studies show", "research says", "there's data on" | 19,154 / 15,305 / 294 | fine |
| `official_data_documents` | VAERS, package insert, CDC data, FOIA | 1,122 / 923 / 119 | fine |
| `expert_consensus` | "guidelines say", consensus, "the AAP recommends", "most doctors agree" | 674 / 631 / 112 | fine |
| `prestige_institution` | Harvard, Stanford, Mayo, Hopkins, Oxford + study/found; Nobel | 6,645 / 5,451 / 245 | fine |
| `credential_appeal` | "as a physician", "I'm a doctor" | 7,474 / 5,853 / 297 | examples change |
| `clinical_experience` | "in my practice", "my patients", "my clients" | 13,766 / 7,844 / 244 | needs definition change |
| `preclinical_extrapolation` | "in mice", "rat study", "in vitro", "petri dish" | 3,492 / 2,505 / 190 | fine |
| `weak_human_evidence` | "associated with", correlation, observational, case report, preprint | 33,664 / 24,563 / 448 | fine (noisy query) |
| `traditional_use` | "thousands of years", "for centuries", ancient medicine, TCM, Ayurveda | 20,027 / 11,761 / 317 (3,585 with use/remedy words) | needs definition change |
| `foreign_comparison` | "banned in Europe", "other countries don't" | 1,135 / 1,096 / 134 | needs definition change |
| `media_source` | "I saw a video", "I read a book", "I remember reading" | 9,133 / 8,352 / 306 | fine |
| `evidence_limits` | "more research is needed", "we don't know yet", "hasn't been studied", "correlation not causation" | 3,429 / 3,253 / 247 | fine |
| `strength_assertion` | clinically proven, science-backed, third-party tested, doctor recommended, FDA approved, gold standard, peer-reviewed | 18,580 / 14,670 / 330 | examples change |

Details:

- **`strength_assertion`: the ad register dominates.**
  - "Eight Sleep has been clinically proven to add up to one hour of quality sleep per night" (175395, 7)
  - "FDA-approved GLP-1 medications, including the Wegovy pill" (74074, 3), a Hers read
  - "a clinically proven electrolyte blend and no artificial colors or flavors" (187397, 1)
  - "clinically proven to stimulate hair follicle cells" (192534, 0)
  - Anonymous-authority ad formulas ("doctor formulated", "developed by scientists / Swiss researchers", "scientifically designed"): 2,952 / 2,819 / 169. These are missing from the examples.
  - "Gold standard" is mostly finance and media ("took the US off the gold standard", 328844, 511; "Fabrizio is the gold standard", 37730, 0). Remove it as an example.
  - "Has over one hundred peer-reviewed scientific publications" (192472, 0) is a credential, not a strength assertion.
- **`clinical_experience`.** "My clients" picks up life coaches (87370, 9) and interior designers (62918, 4). The "about their health" clause handles that. The definition does not say the experience must be *offered as grounds*, so routine advice like "I'll definitely say to my patients, please don't exercise during any air quality index that's greater than ... 50" (181560, 8) gets coded. The `personal_anecdote` definition already has the as-grounds clause; mirror it.
- **`traditional_use` and ancestral arguments.** Real forms:
  - "mushrooms that have been used for thousands of years in China and Japan" (182128, 0)
  - Ad copy: "Our ancestors had the answer all along: bitter foods. Bitter herbs and plants have been used for centuries" (5239, 8; 5447, 9)
  - Ancestral and traditional-population arguments (`our ancestors|hunter-gatherers|paleolithic|caveman|Hadza|Blue Zones|Okinawans|Inuit|Maasai|Tsimane`): 8,541 / 6,109 / 243. No evidence label clearly covers "hunter-gatherers don't get heart disease" or "look at the Blue Zones" (175901, 6; 195695, 2). Coders will scatter these across `weak_human_evidence`, `traditional_use` and `foreign_comparison`.

### Population

| Phrasing | Query (abridged) | Segments / eps / podcasts |
| --- | --- | --- |
| Race/ethnicity + health | Black / Hispanic / Indigenous / Native American / minority + women / people / communities ... + health words | 694 / 651 / 119 |
| Low income / unhoused + health | low-income, poor communities, food deserts, homeless/unhoused + health words | 1,075 / 986 / 153 |
| First responders + health | first responders / police / firefighters / paramedics + suicide / PTSD / mental health ... | 387 / 373 / 108 |
| Sex + age phrases | "women over 40", "men in their 50s" | 699 / 632 / 144 |
| Menopause-stage women | "postmenopausal / perimenopausal women" | 983 / 696 / 85 |
| Generations + health | boomers, millennials, Gen X, Gen Z, Gen Alpha + health words | 414 / 381 / 104 |
| Young people + health | "young people", "youth" + mental health / suicide / social media / gender / fentanyl | 1,437 / 1,286 / 158 |
| Tweens and middle schoolers | tweens, preteens, middle schoolers, elementary + health words | 196 / 194 / 90 |
| Trans athletes | "trans athletes", "men in women's sports" | 797 / 677 / 59 |

- **Race and ethnicity: no label.**
  - Indigenous women: "Indigenous women in Canada have six times the rate of autoimmune disease" (179083, 1).
  - Maternal mortality: "Black women are three times more likely to die of causes related to pregn[ancy]" (1138805, 3).
  - Race-specific schedules: "Black Americans and White Americans should have totally different vaccine schedules" (166858, 0).
  - BMI by race: "Black women with a high BMI tend to be healthier" (318494, 1).
  - About half of the query hits are health-relevant. Health disparities by race are a core research axis, and nothing in v8 records them (`gender.lgbtq_health` has a disparities clause; nothing else does).
- **Low income and unhoused.** Real but mixed. Homelessness often appears as an *outcome* of illness (29313, 4). Real group content: "Working class people, low income people, do not have access to the kind of healthcare that the rich do" (11483, 0); "people who are suffering mental health crises on the streets" (1137605, 0). This is a weaker case than race; I note it but do not propose a label.
- **First responders.** Example: "we're in an epidemic of suicide in first responders" (695, 1). Some hits are true-crime noise.
- **"Young people" / "youth".** The age is usually unspecified and spans minors and adults:
  - "a national crisis for young people in this country in terms of their mental health" (331474, 0), citing the AAP;
  - "especially in the subset of young people" (181653, 0), on myocarditis;
  - "these young people who transition" (13950, 7).
  - The codebook covers only "young people meaning adults".
- **Sex + age phrases.** Both the women/men examples ("women over 40", "men over 40") and the midlife examples ("over 40") cover these, but no rule says to apply both.
- **Generations.** Example: "it is without a doubt the sickest generation, both mentally, physically, emotionally, nutritionally sick" (37548, 0), about college students (Gen Z). Only Gen Z is mapped.
- **Trans athletes.** Mostly sports-fairness talk; it is health content only when testosterone or physiology is discussed. When it is, it takes `population:lgbtq` + `population:athletes`. A one-line note suffices.
- The existing labels (`infants` to `military_veterans`) all have ample real vocabulary. Verdict: fine, apart from the changes proposed below.

### Certainty markers (codebook section 7)

The table counts marker-group regexes within 100 characters before a health word (cancer, vaccine, insulin, sleep, supplement, disease, inflammation, testosterone, cholesterol, blood sugar, depression, autism, vitamin, protein, seed oil, dementia, obesity, diabetes, estrogen, gut).

| Marker group | Listed in section 7? | Eps |
| --- | --- | --- |
| I think | yes | 17,276 |
| probably | yes | 9,445 |
| obviously / of course / clearly | yes | 8,847 |
| definitely | yes | 3,510 |
| I believe | yes | 1,604 |
| **I feel like** | no | 2,094 |
| **in my opinion / my guess is / I suspect / I assume / I imagine / presumably / perhaps** | no | 2,005 |
| **chances are / odds are / most likely / more than likely** | no | 575 |
| **I'm pretty sure / fairly sure** | no | 208 |
| **I'm convinced / confident, I would argue** | no | 195 |
| **for sure / no doubt / without a doubt / no question / hands down** | partly ("there is no doubt") | 1,926 |
| **the reality is / make no mistake / undeniably / certainly / the science is clear / well established / it's a fact** | no | 2,227 |
| **a hundred percent (spelled forms)** | only "100%" | 892 |
| **I promise you / I guarantee / I'm telling you / trust me / I know for a fact** | "guaranteed" only | 816 |
| **oftentimes / more often than not / nine times out of ten / almost always / rarely / seldom** | partly | 1,230 |
| allegedly / reportedly / supposedly / they say / people say / I've heard | partly | 3,671 |
| **to some degree / in some cases / in a lot of cases / for the most part** | partly | 1,003 |

Corpus-wide, the spelled "a/one hundred percent / 100 percent" (59,403 seg / 38,671 eps) is more common than "100%" (43,841 / 31,483).

Function cases seen in real claims:
- **Negated booster = hedge.**
  - "we just can't say that for sure that the supplement is exactly what's said on the bottle" (24761, 5)
  - "Now, look, I can't say for sure that her holding on to that ... contributed to cancer" (183314, 5)
  - "So we really don't know for sure what exactly is it" (23307, 8)
  - Read by form, these are boosters ("for sure"). They actually weaken the claim.
- **Backchannel ≠ marker.**
  - "Yeah, for sure. So you did a protein sparing modified fast" (192469, 4)
  - "It is a fat, though. Yeah, for sure." (182452, 5), where the interlocutor is agreeing
  - Health-state content, not markers: "he feels a hundred percent" (11960, 3); "not going to give you a hundred percent clarity" (192999, 3)
- **Real boosters:**
  - "whole foods are going to work quicker for sure" (178148, 5)
  - "Yeah, I'm telling you, NAD drip and high dose vitamin C" (11960, 3)
  - "there's no doubt all of those things that you mentioned do cause inflammation" (185121, 2)
  - "the root cause of everything is stress. Period. End of story." (176668, 1)
  - "But the reality is, is that we do all have cancer cells." (190369, 36)
- **Real hedges:**
  - "In my opinion, yes, because I think you know having vitamin D levels between like 40 and 60" (11983, 11)
  - "you will most likely not. Experience much hunger at all" (192469, 6)
  - "They are likely rancid ... they tend to cause us inflammation" (78339, 7)
  - "Can cause inflammation in some individuals" (195756, 3)
  - "especially certain women, that it can increase risk of certain types of cancers" (192391, 3). Here "certain" works like "some". The same sentence also has "the reality is" and "some studies"; by the mixed-marker rule the claim is hedged.
- **"Most likely" doubles as a statistical idiom**, like the already-exempt "more likely to": "most likely to suffer with things like focus and sleep" (54317, 262).
- **"Obviously" / "of course" are often discourse filler:**
  - "I mean, obviously, you need to have protein, but chances are you are getting enough" (178789, 6), where the actual claim carries the hedge "chances are"
  - "Obviously, I this is my opinion." (205344, 2), where a booster form introduces a hedge
  - Genuine booster: "uric acid, of course, leads to gout" (190504, 102)
- **Hearsay beyond product effects:** "apparently it's supposed to cause cancer" (23744, 3). The list has "is supposed to" only for a product's claimed effect.
- **Ad-copy distancing:** "more than 400 bioactive nutrients that they say can work at a foundational level to fortify gut health" (42105, 8), an Armra read.
- **"Suggests" conflict.** "Research / studies / data suggest(s) / indicate(s)" occurs in 3,013 segments / 2,578 eps. Section 7 lists "suggests" as a hedge and also says reporting verbs ("found", "showed") are not markers, so coders will split on "studies suggest X".
- **"There's a lot of evidence that X is a big cause of depression" (23237, 3).** This evidential frame introducing the claim is not classified. Under the "it is proven that" rule it reads as a booster; under the reporting-verb rule it does not.

### Ad reads and the ad test (sections 3 and 4.1)

| Marker | Query (abridged) | Segments / eps / podcasts |
| --- | --- | --- |
| Opening line | "brought to you by" | 86,653 / 48,585 / 319 |
| Opening line, NPR / Daily style | "support for this show comes from", "this episode is sponsored by", "today's sponsor" | 30,241 / 20,668 / 192 |
| Promo code | "use code", "promo code" | 66,252 / 43,492 / 388 |
| URL | "dot com slash", ".com/" | 194,227 / 94,334 / 569 (also show links) |
| Return transition | "back to the show", "we'll be right back", "after the break", "quick break" | 32,280 / 23,438 / 406 |

The return-transition count is a third of the openings, so most reads end with no explicit return. Patterns seen:

1. **Reads end without a transition.**
   - "...use the promo code Rogan. Terms apply. See Visible.com for plan features ... Jamie just pulled it up here. Journal. Retracts 1998 paper linking autism to vaccines" (70882, 6). The next sentence is show content carrying a `rebutted`-stance narrative.
   - "Limited time offer. Rules and restrictions apply. Fucking amazing. I think one thing that might happen..." (21273, 0).
2. **Consecutive spots.** A whole ad break is often several "This episode is brought to you by X" spots in a row with no seam except the next opening (199798, 1; 202451, 0, where a Spanish Gatorade spot runs into a Tidy Cats spot).
3. **Closing tags.** DTC drug spots end with "Brought to you by Argenx" *after* the copy (42250, 7; 41892, 2), and the next spot starts right after. Read as an opening transition, the tag would wrongly attach the drug to the following ad.
4. **A host read carried into the next unit.** A Garnuu read gives the code, then continues in the next unit with "with code spillover ... These are the cleanest tampons on the market" before the interview resumes (185859, 4-5).
5. **Pharma, disease-awareness and DSHEA copy.** Examples: Zepbound side-effect copy (623373, 4); Lilly's unbranded "Don't sleep on OSA" (31661, 0), which names no product; Cologuard, which addresses "If you're 45 or older" (95572, 2) and so is an ad audience list, not a population; Opill "FDA-approved, full prescription strength" (23440, 3).
6. **Ad-test edge cases:**
   - Coca-Cola/Pepsi/Sprite "Zero Sugar" (92955, 6; 32032, 0): the free-from term is only in the product name.
   - Whole Foods: "300 food ingredients banned store-wide. No hydrogenated fats, nothing in store has high fructose corn syrup, and there's a great selection of allergen-friendly options" (89588, 1). These are free-from claims framed as better, but the advertiser is a retailer, and retailers are excluded from product mentions.
   - Parody: "Side effects may include laughing, cheering, and lots of high fives" (1127002, 3), a TV-show ad.
   - Non-health ads around health shows (Sheath underwear, Poshmark, DraftKings with its gambling helpline) are handled correctly by the current test.
7. **Product types seen that section 8 does not place:**
   - exercise and recovery equipment: Peloton/Tonal/Hydrow/Theragun/Hyperice/Normatec/walking pad/vibration plate group is 2,544 / 2,133 / 174 (Theragun, 28504, 2);
   - period products (Garnuu tampons);
   - training apps (RP Hypertrophy app, 175578, 1);
   - doctor-finding apps (Zocdoc, 4501, 1);
   - unbranded disease-awareness campaigns (Lilly OSA);
   - retailers advertised with health claims (Whole Foods).

## Proposed edits

CHANGE `frame:root_cause_framing`:
| root_cause_framing | Root-cause framing | Getting to an underlying cause is contrasted with merely treating symptoms, reversal is promised instead of management, one hidden cause is said to underlie many diseases, or "root cause" is presented as a method or kind of care ("root-cause medicine", "we find the root cause"), where the contrast with symptom management is implied. "The root cause of Y is X" about a single condition, with no method or contrast, is a causal claim, not this frame. | root cause medicine; we get to the root cause; treat the cause not the symptoms; reverse disease; band-aid medicine; the root cause of everything is stress |
Why: "root cause" is 4,113 eps, led by Hyman (594) and Jockers (294). In those shows it mostly names a method ("trained in functional medicine to find the root cause of disease", 183016, 6; "functional and root cause medicine", 190493, 4), and coders will split on this under "needs that contrast".

CHANGE `frame:fear_alarm`:
| fear_alarm | Fear & crisis framing | Health threats are presented in alarmist, catastrophic language meant to provoke alarm. Needs intensification beyond the standard term: "obesity epidemic", "opioid crisis" or "loneliness epidemic" used descriptively is not it, nor are neutral trend words ("rising", "doubled", "on the rise"). Hyperbolic trend words applied to disease rates ("skyrocketing", "through the roof", "exploding", "an explosion of") count. | skyrocketing rates of autism; anxiety is through the roof; the autism explosion; a tsunami of chronic disease; poisoning our children; catastrophe |
Why: 1,192 segments of hyperbolic trend words near disease terms (177088, 1; 185830, 2; 14613, 0). The current lead example "ticking time bomb" is rare. Without a line between "skyrocketing" and "rising", coders will split.

CHANGE `frame:toxin_purity`:
| toxin_purity | Toxin & purity framing | Health problems are framed in terms of toxins, poisons, chemical burden or clean-versus-contaminated bodies and products. Not for "eat clean" as an idiom for healthy eating, a neutral physiological mention ("the liver filters toxins", "how the body clears toxins"), or a specific named toxicant discussed concretely (lead in water, anthrax); those take the topic only. | toxic load; the toxic bucket; toxins are making us sick; poison; non-toxic; chemical-free; the cleanest tampons on the market; "what's really in" |
Why: 5,890 eps. About half the "toxins" hits are neutral physiology (192686, 0; 190143, 467; 78284, 1) or concrete toxicology (181670, 17). Real framing looks like 193107, 1 and 185859, 5.

CHANGE `frame:medical_freedom`:
| medical_freedom | Medical-freedom framing | Health decisions are framed as autonomy, informed consent, parental rights or freedom from mandates, invoked as a right against pressure, mandates or withheld information. Informed consent as a procedure or a policy requirement is the topic `health_system.ethics_law_privacy` without this frame; parental rights in custody or non-health law is not health content. | medical freedom; health freedom; my body my choice; parental rights over vaccines; we were never given informed consent |
Why: 2,163 eps. Procedural uses (373156, 12; 75383, 6) and custody uses (178493, 0) are frequent. In addition, ~380 Chiro Hustle intros carry a tagline (see codebook notes).

CHANGE `frame:anti_expert_populist`:
| anti_expert_populist | Anti-expert / populist framing | Ordinary judgement, lived experience or independent research is elevated over expertise and credentials, including mocking expertise itself (sarcastic "trust the science", "the experts"). "Do your own research" said about a crime case or other non-health matter is not health content. | do your own research; go do your own research on NADH; trust your gut; moms know best; experts got it wrong; "trust the science" said mockingly |
Why: of 1,536 eps, the "do your own research" hits are mostly true-crime boilerplate (160682, 0; 161517, 1). The health form is sarcastic "trust the science" (205233, 4; 206890, 2) and ad copy (38168, 1).

CHANGE `frame:maha_framing`:
| maha_framing | MAHA framing | The Make America Healthy Again framing. Needs at least two of: a chronic-disease crisis, especially in children ("sickest generation", "sickest country" count as this one element); causes in food, chemicals or medicine; corporate or government capture; the movement or its agenda named. The slogan or one concern alone is not it. | Make America Healthy Again; we're the sickest country and the CDC did not do its job; sickest generation plus chemicals in our food; corporate capture of our health |
Why: the old example "sickest generation" contradicted the two-element threshold. Real uses pair it with a second element (439182, 1; 174978, 4).

CHANGE `frame:disclaimer`:
| disclaimer | Disclaimer | The speaker disclaims medical authority or responsibility, or advises consulting a professional, including boilerplate in an episode intro and mandated or legal boilerplate inside an ad (the supplement "not evaluated by the FDA" statement, "talk to your doctor about", "consult a healthcare professional if symptoms persist"). | not medical advice; for educational purposes only; talk to your doctor; I'm not a doctor; these statements have not been evaluated by the FDA; ask your doctor if it is right for you |
Why: DSHEA boilerplate appears in 1,253 eps / 70 podcasts and DTC "talk to your doctor" copy in ~7.8k eps / 235 podcasts (188820, 0; 31661, 0; 180065, 0). The current text does not say whether ad boilerplate counts, so coders will split.

CHANGE `evidence:strength_assertion`:
| strength_assertion | Evidence-strength assertion | An explicit assertion about the evidence or proof behind something (proven, science-backed, FDA approved offered as grounds), an anonymous endorsement or authorship claim ("doctor recommended", "doctor formulated", "developed by scientists"), a certification seal, or "there's no evidence" used as a verdict. Certainty boosters alone ("we know", "clearly") are not this label; a named person's publication record is `evidence:credential_appeal`. | clinically proven; clinically proven to add up to one hour of quality sleep; science-backed; FDA-approved; doctor formulated; developed by scientists; scientifically designed; NSF certified; third-party tested |
Why: 14,670 eps, dominated by ad copy (175395, 7; 74074, 3; 187397, 1). The authorship formulas alone are 2,819 eps / 169 podcasts. "Gold standard" is removed: its hits are mostly finance and media (328844, 511; 37730, 0).

CHANGE `evidence:credential_appeal`:
| credential_appeal | Credential appeal | A named person's title, training, professional identity or publication record is invoked as grounds for believing a claim, including their recommendation given with their title. Anonymous endorsements are `evidence:strength_assertion`. | as a physician; he's an MD; a Harvard-trained doctor; I'm a nutritionist; Dr. X recommends; over 100 peer-reviewed publications |
Why: guest intros cite publication counts as authority (192472, 0). The old wording pushed these toward `strength_assertion`.

CHANGE `evidence:clinical_experience`:
| clinical_experience | Clinical experience | A practitioner's own experience treating, coaching or advising people about their health, licensed or not (doctors, therapists, dietitians, chiropractors, naturopaths, health coaches, trainers), offered as grounds for a claim. Treat the speaker as a practitioner only if the window says so. What the practitioner tells patients (advice) is not experience; another practitioner's results or a relayed patient story is `evidence:personal_anecdote`. | in my practice; my patients do better when; I've treated thousands; we see this all the time in clinic; my clients |
Why: "my patients / my clients / in my practice" is 7,844 eps, and much of it is advice, not grounds ("I'll definitely say to my patients, please don't exercise...", 181560, 8). `personal_anecdote` already has the as-grounds clause.

CHANGE `evidence:traditional_use`:
| traditional_use | Traditional-use or ancestral appeal | Long or traditional use, or what ancestral or traditional peoples ate or did, is offered as evidence that something works or is safe. The appeal to naturalness itself is `frame:naturalness_appeal`; both can apply. | used for thousands of years in China and Japan; our ancestors had the answer all along; bitter herbs used for centuries; hunter-gatherers don't get heart disease; our grandmothers knew |
Why: 6,109 eps / 243 podcasts mention ancestors, hunter-gatherers or traditional peoples, and no evidence label clearly takes them. Real uses: 182128, 0; 5239, 8 (ad copy).

CHANGE `evidence:foreign_comparison`:
| foreign_comparison | Foreign or other-population comparison | Other countries' rules, practices or outcomes, or the outcomes of named present-day populations (Blue Zones, Okinawans), are offered as evidence. | banned in Europe; other countries don't vaccinate newborns; Japan doesn't allow; look at the Blue Zones; Okinawans live longer because |
Why: Blue Zones and long-lived-population arguments recur (175901, 6; 195695, 2; 181412, 3) with no clear home. Grouping them with country comparisons keeps one label for "elsewhere, people do X and fare better".

CHANGE `population:children`:
| children | Children | The health content is specifically about school-age children or "kids" generally: "kids", "children", "school-age", "young girls", "tweens", "preteens", "middle schoolers", "Gen Alpha", and "minors" unless ages 13 to 17 are given. | kids; children; our children; schoolchildren; young girls; tweens; middle schoolers; minors |
Why: tweens, preteens, middle and elementary schoolers appear with health words in 194 eps / 90 podcasts, and the current mapping does not place them.

CHANGE `population:young_adults`:
| young_adults | Young adults | The health content is specifically about young adults (roughly 18 to 30), including "Gen Z", college students, and "young people" or "young men/women" when adults are meant. "Young people" or "youth" with no age cue: use `population:adolescents` when minors are implied (school, parents, under 18, youth gender care), this label when adults are implied (college, dating, work, military), and both when the content covers both (myocarditis in young people). | young adults; Gen Z; college students; twenty-somethings; young men in their twenties |
Why: "young people/youth" with health words is 1,286 eps / 158 podcasts. The age is usually unstated (331474, 0; 181653, 0; 13950, 7), and the codebook covers only the adults case.

CHANGE `population:midlife`:
| midlife | Midlife adults | The health content is specifically about people in midlife (roughly 40 to 64), including "Gen X". A sex-plus-age phrase ("women over 40", "men in their 50s") takes both this label and `population:women` or `population:men`. Menopause or perimenopause with no age word takes `population:women` only. | over 40; after 50; midlife; middle-aged; women over 40; Gen X |
Why: sex-plus-age phrases are 632 eps / 144 podcasts. They currently appear as examples under both `women` and `midlife` with no rule. Perimenopausal or postmenopausal women are 696 eps.

CHANGE `population:older_adults`:
| older_adults | Older adults | The health content is specifically about older adults: 65+ or described as elderly, seniors, ageing parents or boomers. | seniors; elderly; over 65; aging parents; boomers |
Why: generational labels appear with health words in 381 eps; boomers are the older-adult generation.

CHANGE `population:military_veterans`:
| military_veterans | Military, veterans & first responders | The health content is specifically about service members, veterans or first responders (police, firefighters, paramedics) as occupational groups. | troops; soldiers; veterans; the VA; military personnel; first responders; firefighters' cancer rates |
Why: first responders with suicide, PTSD or mental-health words appear in 373 eps / 108 podcasts ("we're in an epidemic of suicide in first responders", 695, 1). The occupational-trauma subject is the same as for veterans and has no other home. If you would rather keep the label narrow, leave it unchanged; the evidence is moderate.

ADD `population:racial_ethnic_groups` under Population axis:
| racial_ethnic_groups | Racial & ethnic groups | The health content is specifically about a racial or ethnic group's health as a group: disparities, group-specific rates, risks or recommendations, and research or medical history concerning the group. One person's race mentioned in their own story takes no label. | Black maternal mortality; Indigenous women's autoimmune rates; Black and white vaccine schedules; Hispanic diabetes rates; Tuskegee |
Why: 694 segments / 651 eps / 119 podcasts of race/ethnicity group terms near health words, about half of them health-relevant ("Indigenous women in Canada have six times the rate of autoimmune disease", 179083, 1; "Black women are three times more likely to die of causes related to pregn[ancy]", 1138805, 3; "Black Americans and White Americans should have totally different vaccine schedules", 166858, 0). Health disparities are a core research dimension, and v8 can only record them by summary text.

## Codebook and prompt notes

**Section 3, ad test (c): brand names.** Add after the (c) examples: "A free-from or nutrient word that is only part of a product's name ('Coca-Cola Zero Sugar', 'Pepsi Zero Sugar', 'Diet Coke', 'Michelob Ultra') does not pass (c); the ad must state the attribute as a benefit." Evidence: the soda-name set is 12,658 seg / 7,763 eps / 224 podcasts ("Zero Sugar" alone: 4,911 segments). Spots like "Grab a Pepsi Zero Sugar today" (32032, 0; 203758, 0) and "Coca-Cola Zero Sugar is so good" (92955, 6) would otherwise all become health content with product mentions.

**Section 3, ads: two more cases.**
- A retailer advertised with health or free-from claims (Whole Foods: "no hydrogenated fats ... allergen-friendly", 89588, 1) passes the test as a topic detection with `relevance: advertisement`. It gets no product mention unless a specific product is named, consistent with the retail-venue exclusion in section 8.
- An unbranded disease-awareness spot ("Don't sleep on the symptoms. Talk to your doctor about OSA ... provided by Lilly USA", 31661, 0) passes test (b). It takes the condition's topic and `frame:disclaimer`, and no product mention. Parody ad copy ("Side effects may include laughing", 1127002, 3) is not health content.

**Section 4.1, delimitation: where a read ends and where the next begins.** Proposed text: "A read ends after its last line of ad copy: the final call to action, URL or code repetition, or legal tail ('Terms apply', 'Rules and restrictions apply', a gambling helpline, a side-effect list), even when no return transition follows. Content after that is show content. A break often holds several spots in a row: each spot is its own read and starts at its own opening line. A 'Brought to you by [company]' tag after a spot's copy (common in drug ads) closes that spot; it does not open the next one. A host read that continues into the next unit (repeating the code, adding endorsements) is part of the read until the show content resumes."
Evidence: return transitions are about a third as frequent as openings (23,438 vs 48,585 + 20,668 eps). Examples: 70882, 6; 21273, 0; 42250, 7; 185859, 4-5.

**Section 4.1, topics inside ads.** Ads often carry topic-bearing population lists ("If you're 45 or older and at average risk", 95572, 2). These are ad audience lists and take no population label, which section 5.5 already says. Worth repeating in the ad paragraph, because Cologuard, Opill and DTC drug spots run in hundreds of non-health shows.

**Section 5.3, recurring show boilerplate.** Add: "A show's recurring intro or mission statement takes `frame:disclaimer` when it is a disclaimer, and no other frame. A value tagline ('we believe in supporting medical freedom and family health freedom') is the podcast's tagline (section 3) and gets no annotation." Without this, Chiro Hustle alone adds ~380 eps of `frame:medical_freedom` (186239, 0; 186253, 0).

**Section 5.3, sarcastic "trust the science".** State that mocking expertise as such ("if you trust the science, then you're going to just trust all of this", 206890, 2) is `frame:anti_expert_populist`. Add `frame:government_distrust` only when an agency or official science is called corrupt, lying or untrustworthy, per the existing target rule.

**Section 5.5, population mapping (age words bullet).** Add:
- "tweens", "preteens", "middle schoolers" → `population:children`;
- "boomers" → `population:older_adults`;
- "Gen X" → `population:midlife`;
- "millennials" → `population:young_adults` only when the window treats them as young, otherwise no age label;
- a sex-plus-age phrase takes both labels;
- "young people" / "youth" with no age cue follow the rule in the proposed `young_adults` row;
- trans athletes discussed for physiology take `population:lgbtq` + `population:athletes`.

**Section 7, marker lists. Add to `absolute`:**
- "for sure" (as a booster), "no doubt", "without a doubt", "no question", "there's no question"
- "hands down", "certainly", "undeniably", "make no mistake"
- "the reality is", "it's a fact", "I know for a fact"
- "I'm telling you", "I promise you", "I guarantee (you)", "trust me"
- "period" and "end of story" (as sentence-final boosters)
- the spelled forms "a hundred percent", "one hundred percent", "100 percent"
- "it's well known that", "it's well established that", "the science is clear that"

**Section 7, marker lists. Add to `hedged`:**
- "I feel like", "in my opinion", "I'm pretty sure", "I would argue"
- "my guess is", "I suspect", "I assume", "presumably"
- "chances are", "odds are", "most likely", "more than likely"
- "oftentimes", "more often than not", "nine times out of ten", "for the most part", "to some degree"
- "in some cases", "in a lot of cases"
- "certain people" / "certain women" (limiting who the claim covers, like "some")

**Section 7, marker lists. Add to `speculative`:** "perhaps", "I imagine".

Frequencies are in the table above. "I feel like" (2,094 eps near health words) and "in my opinion / perhaps / I suspect..." (2,005) are each more common than the listed "I believe" (1,604).

**Section 7, marker rules: add four.**
1. "**Negated boosters** ('I can't say for sure', 'we don't know for sure', 'not a hundred percent', 'not necessarily') are hedges; list the whole phrase." (24761, 5; 183314, 5; 23307, 8.)
2. "**Agreement from another speaker** ('Yeah, for sure.', 'A hundred percent.', 'Totally.') is not a marker on the claim it answers; code the claim as its speaker stated it." (192469, 4; 182452, 5.)
3. "**'Most likely'** is a hedge when it qualifies the claim ('you will most likely not experience hunger') and, like 'more likely to', a statistical idiom when it compares groups ('those people are most likely to suffer')." (192469, 6 vs 54317, 262.)
4. "**'Obviously', 'of course' and 'clearly'** as discourse openers before a hedge or an opinion ('Obviously, this is my opinion') are filler; with mixed markers the hedge wins." (178789, 6; 205344, 2.)

**Section 7, reporting verbs vs "suggests".** "Suggests" is listed as a hedge, yet reporting verbs are not markers. Settle it explicitly: "'X suggests / indicates that' (research, data, a study) is `hedged` with the verb as the marker; 'X shows / found / showed' is a reporting verb and no marker." Evidence: 3,013 segments / 2,578 eps use the suggests/indicates form.
Also state that an evidential frame introducing the claim ("there's a lot of evidence that", "research shows that") is not a certainty marker. Only the listed proof phrases ("it is proven that", "the science is clear that") are `absolute`. (23237, 3.)

**Section 7, hearsay "supposed to".** Extend "is supposed to (of a product's claimed effect)" to "is supposed to / it's supposed to, presenting any effect as hearsay" (23744, 3: "apparently it's supposed to cause cancer").
Ad copy that attributes its own claim ("nutrients that they say can work ... to fortify gut health", 42105, 8) is hearsay distancing → `speculative`, with "they say" as the marker. A one-line example would settle it, since such hedged copy is common in supplement reads.

**Section 7, claims in DTC drug ads.** Add to "Do not extract": "the mandated safety statement in a drug ad (side-effect lists, contraindications, 'can harm an unborn baby'); extract the ad's efficacy claims only." Without this, each DTC spot yields 3-8 risk claims of label boilerplate ("Common side effects include nausea, headache, and tiredness", 42260, 0). These spots recur in thousands of news and comedy episodes, so claim counts would be dominated by drug-label text. If the researchers want these claims, say so instead, and cap them at one claim per spot.

**Section 8, product_type additions.** Add to the guidance:
- exercise and recovery equipment (bikes, rowers, massage guns, compression boots, saunas, cold plunges, red-light panels) → `device_or_wearable`;
- period and sexual-health consumer products (tampons, pads, condoms, lubricants) → `personal_care_or_cosmetic`, or `medication` when regulated as a drug (Opill);
- training, meditation and doctor-booking apps (RP Hypertrophy, Calm, Zocdoc) → `app_or_digital_service`; a coaching or programme subscription delivered in an app stays `program_or_course` only when sold as a course;
- eyewear, contact lenses and hearing aids → `device_or_wearable`;
- an unbranded disease-awareness campaign is not a product;
- a retailer named as an ad's sponsor is not a product unless a specific product is named.

Evidence: the equipment brands alone are 2,133 eps / 174 podcasts (28504, 2). Garnuu tampons (185859, 4), RP Hypertrophy (175578, 1), Zocdoc (4501, 1), Lilly OSA (31661, 0) and Whole Foods (89588, 1) are all real reads the current list does not place.

**Rubric step 1.** "Mark where any delimited ad read starts and ends" should point to the new end-of-read rule. Labelers given transcripts like 70882, 6 will otherwise extend `relevance: advertisement` over the show content that follows the read.
