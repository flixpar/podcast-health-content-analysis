# Preliminary vaccination-content scan

> Exploratory model-assisted triage of noisy ASR—not prevalence measurement, fact-checking, or a validated content analysis.

## Snapshot

- Candidate clips screened: **7,247**
- Clips retained as relevant: **6,336** (87.4% of candidates)
- Routine promotional clips set aside: **818**
- Analysis-oriented clips after that exclusion: **5,518** in **2,309 episodes**
- Potential-misinformation triage flags: **2,327 clips**
- Corrective-context tags: **901 clips**

Counts below describe retrieved and model-filtered clips, not the full population rate.

## Clip tags

- Content type: passing_mention=2829, substantive_discussion=1895, advertisement_or_psa=734, metaphor_or_false_positive=36, asr_unclear=24
- Apparent stance: mixed=3529, neutral=1268, supportive=576, critical=145
- Topics: covid19=4106, conspiracy_or_institutional_trust=2940, safety_or_side_effects=2484, misinformation_or_fact_checking=2295, mandates_or_policy=2030, efficacy_or_immunity=1660, personal_decision_or_uptake=1221, development_or_approval=843, childhood_schedule=383, other_vaccine=291, access_or_equity=237, mmr_measles=212, influenza=184, polio=116, hpv=65

## Concentrated episodes

| Clips | Podcast | Episode | Review flags |
|---:|---|---|---|
| 32 | The Joe Rogan Experience | #2294 - Dr. Suzanne Humphries | potential-misinfo |
| 32 | The Joe Rogan Experience | #1717 - Alex Berenson | potential-misinfo, corrective |
| 26 | The Joe Rogan Experience | #1757 - Dr. Robert Malone, MD | potential-misinfo |
| 24 | The Joe Rogan Experience | #1864 - Alex Berenson | potential-misinfo |
| 23 | The Joe Rogan Experience | #1747 - Dr. Peter A. McCullough | potential-misinfo |
| 22 | The Joe Rogan Experience | #1919 - Bret Weinstein | potential-misinfo |
| 20 | The Joe Rogan Experience | #1999 - Robert Kennedy, Jr. | potential-misinfo |
| 19 | The Joe Rogan Experience | #1718 - Dr. Sanjay Gupta | potential-misinfo, corrective |
| 18 | The Joe Rogan Experience | #2335 - Dr. Mary Talley Bowden | potential-misinfo |
| 18 | The Tucker Carlson Show | Bill Gates, Truth About Vaccines, & Big Pharma’s Plot to Destroy Doctors Who Question ”The Science” | potential-misinfo |
| 18 | The Joe Rogan Experience | #1780 - Maajid Nawaz | potential-misinfo, corrective |
| 17 | The Joe Rogan Experience | #1671 - Bret Weinstein & Dr. Pierre Kory | potential-misinfo, corrective |
| 17 | The Joe Rogan Experience | #1261 - Peter Hotez | corrective |
| 16 | The Joe Rogan Experience | #2101 - Bret Weinstein | potential-misinfo |
| 16 | The Tucker Carlson Show | Aaron Siri: Everything You Should Know About the Polio Vaccine, & Its Link to the Abortion Industry | potential-misinfo |

## Podcast titles with the most retrieved analysis clips

| Clips | Episodes | Podcast |
|---:|---:|---|
| 1748 | 518 | The Joe Rogan Experience |
| 1249 | 445 | The Megyn Kelly Show |
| 546 | 248 | Pod Save America |
| 500 | 246 | REAL AF with Andy Frisella |
| 307 | 89 | The Tucker Carlson Show |
| 219 | 142 | The MeidasTouch Podcast |
| 189 | 111 | Candace |
| 113 | 80 | Wait Wait... Don't Tell Me! |
| 113 | 71 | Matt and Shane's Secret Podcast |
| 105 | 53 | The Shawn Ryan Show |
| 60 | 35 | The Diary Of A CEO with Steven Bartlett |
| 53 | 43 | Up First from NPR |

## High-priority clips for human review

### 1. Pod Save America — “CPAC: The Fascist & The Furious” (with Katie Porter & Dr. Vivek Murthy)

- Episode 7148; estimated 0:59:30; score 5/5; confidence 1.00
- Tags: neutral; covid19, efficacy_or_immunity, safety_or_side_effects, development_or_approval, personal_decision_or_uptake; corrective context
- Model summary: Dr. Murthy discusses booster criteria, waning immunity, J&J efficacy against Delta, and strategies to increase uptake.
- ASR excerpt near retrieval term: “…that Pfizer will be holding a briefing with you and other public health officials to make their case as to why they're seeking FDA authorization for a booster shot for COVID nineteen. Dr. Fauci was on the Sunday shows yesterday, saying he doesn't believe a booster is required at this time. Meanwhile, countries like…”
- Candidate ID: `episode_7148_clip_7`; source segment 0:59:30–1:09:30

### 2. The Joe Rogan Experience — Fight Companion - September 6, 2025

- Episode 338; estimated 1:10:09; score 5/5; confidence 0.99
- Tags: mixed; childhood_schedule, mmr_measles, safety_or_side_effects, efficacy_or_immunity, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Speakers debate MMR-autism links, Hep B timing, lack of placebo trials, and attribute disease decline to sanitation over vaccines.
- ASR excerpt near retrieval term: “…kids, who's a boy in California, has autism now? Because that's what's going on. That's what's going on in California. Which has one of the strictest fucking vaccine policies, one in twelve. Did I say vaccines cause autism? Maybe I will have to look into that. Yeah, yeah, yeah. And now Florida doesn't demand…”
- Candidate ID: `episode_338_clip_2`; source segment 1:09:25–1:19:25

### 3. Up First from NPR — The Week In Politics, The Week In Free Speech, The Week In Vaccines

- Episode 600; estimated 0:11:19; score 5/5; confidence 0.99
- Tags: mixed; covid19, mmr_measles, childhood_schedule, safety_or_side_effects, mandates_or_policy, conspiracy_or_institutional_trust; potential-misinfo triage, corrective context, politicized
- Model summary: Reports on committee changes to MMRV and COVID vaccine policies under new leadership, citing safety concerns and political tension.
- ASR excerpt near retrieval term: “…of public life, and especially about the nation's most powerful and prominent public officials. And here's David Folkenflik. Thanks so much. You bet. COVID shots weren't the only vaccines under the microscope this week, as a panel that advises the federal government held chaotic and at times tense meetings…”
- Candidate ID: `episode_600_clip_2`; source segment 0:09:55–0:19:50

### 4. Up First from NPR — RFK Jr. Grilled, Europeans Pledge Troops to Ukraine, DC Sues Trump Admin

- Episode 729; estimated 0:00:00; score 5/5; confidence 0.99
- Tags: mixed; covid19, influenza, childhood_schedule, mmr_measles, mandates_or_policy, safety_or_side_effects, efficacy_or_immunity, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, corrective context, politicized
- Model summary: Senate hearing covers RFK Jr.'s vaccine policies, booster access barriers, and allegations of pharma corruption versus scientific consensus.
- ASR excerpt near retrieval term: “Health and Human Services Secretary Robert F. Kennedy Jr. defended his position on vaccines in a contentious Senate hearing. Now, parents who decide that they do want their children vaccinated, I'm not making stuff up. So, what did he have to say about who can get vaccines? I'm Michelle Martin. That's A Martinez, and…”
- Candidate ID: `episode_729_clip_1`; source segment 0:00:00–0:10:00

### 5. The Joe Rogan Experience — #2344 - Amjad Masad

- Episode 931; estimated 0:53:00; score 5/5; confidence 0.99
- Tags: mixed; covid19, safety_or_side_effects, efficacy_or_immunity, mandates_or_policy, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Speakers claim vaccines don't stop spread, cause heart conditions in young men, and were pushed for profit via coercion.
- ASR excerpt near retrieval term: “…got better. But and and I could feel the fatigue get better. No, I could feel marginal improvement, but the fatigue did not did not get better. And we vaccinated. No. No, good for you. That's hard to do in Silicon Valley. Yeah, yeah. I tend to have a negative reaction to anyone forcing me to do something.…”
- Candidate ID: `episode_931_clip_2`; source segment 0:49:35–0:59:35

### 6. The MeidasTouch Podcast — Trump Has Awful Friday Over More Bad News for Him

- Episode 1708; estimated 0:00:00; score 5/5; confidence 0.99
- Tags: mixed; mmr_measles, other_vaccine, safety_or_side_effects, misinformation_or_fact_checking, personal_decision_or_uptake; potential-misinfo triage, corrective context, politicized
- Model summary: Host critiques Trump's social media post advising separate MMR/chickenpox shots and avoiding Tylenol in pregnancy.
- ASR excerpt near retrieval term: “…Don't give Tylenol to your young child for virtually any reason. Break up the MMR shot into three totally separate shots, not mixed! Exclamation point. Take chickenpox shot separately. Take hepatitis B shot." At 12 year old or older, and importantly, take vaccine in separate medical visits. President D J T. He's…”
- Candidate ID: `episode_1708_clip_1`; source segment 0:00:00–0:10:00

### 7. The MeidasTouch Podcast — MeidasTouch Full Podcast - 9/23/25

- Episode 2039; estimated 0:01:04; score 5/5; confidence 0.99
- Tags: mixed; mmr_measles, polio, safety_or_side_effects, efficacy_or_immunity, conspiracy_or_institutional_trust, misinformation_or_fact_checking; corrective context, politicized
- Model summary: Host critiques Trump's claims linking Tylenol and vaccines to autism and firing of CDC experts.
- ASR excerpt near retrieval term: “…they're spreading like debunked quackery, far right wing podcast insanity stuff that's not reflective of peer review. Medical information. They've fired the vaccine advisory board. They fired all of the people in the CDC. And honestly, just as an American, what just transpired? It's one of the most, maybe the most…”
- Candidate ID: `episode_2039_clip_1`; source segment 0:00:00–0:10:00

### 8. The Charlie Kirk Show — The Democrats' Terrible, Horrible, Unfathomably Awful New Fight Song

- Episode 3597; estimated 0:26:24; score 5/5; confidence 0.99
- Tags: supportive; mmr_measles, safety_or_side_effects, efficacy_or_immunity, mandates_or_policy, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Guest claims childhood diseases like measles are not deadly, herd immunity is a myth, and government vaccine mandates could kill children.
- ASR excerpt near retrieval term: “…This is the facts based on the records we have. From Medicare and Medicaid. And so, what would you say to some people that are concerned that if we have lower vaccination rates, we'll see higher rates of otherwise preventable diseases? Please, Mary Holland from the Children's Health Defense. Listen, we don't. We like…”
- Candidate ID: `episode_3597_clip_5`; source segment 0:19:50–0:29:50

### 9. The Tucker Carlson Show — Bill Gates, Truth About Vaccines, & Big Pharma’s Plot to Destroy Doctors Who Question ”The Science”

- Episode 3909; estimated 0:49:35; score 5/5; confidence 0.99
- Tags: mixed; covid19, safety_or_side_effects, development_or_approval, conspiracy_or_institutional_trust, mandates_or_policy, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Guest describes giving saline shots instead of vaccines, claims product data sheets were blank, and alleges animal studies showed 100% mortality.
- ASR excerpt near retrieval term: “…they were requiring people to get a transplant. If you want a transplant, you need a kidney transplant in order to survive. You've got to go get the COVID vaccine. The official story on nine eleven is a complete lie. The nine eleven report is a joke. You have CIA following two men. All over the planet, and then…”
- Candidate ID: `episode_3909_clip_7`; source segment 0:49:35–0:59:35

### 10. Pod Save America — Kimmel Wins, Tylenol Loses

- Episode 4028; estimated 0:53:32; score 5/5; confidence 0.99
- Tags: mixed; childhood_schedule, mmr_measles, safety_or_side_effects, efficacy_or_immunity, misinformation_or_fact_checking; potential-misinfo triage, corrective context, politicized
- Model summary: Discussion of ACIP changing MMRV schedule to separate shots, potentially reducing uptake, and debunking Tylenol-autism links.
- ASR excerpt near retrieval term: “…And when Trump goes out there and just riffs and is like, "Did I get that right? Did I nail that stat?" It's like, buddy, you're giving guidance about. Vaccine intakes, use of medicine for pregnant women—that people are going to follow. Like half the country is going to treat as gospel, and you're just winging…”
- Candidate ID: `episode_4028_clip_3`; source segment 0:49:35–0:59:35

### 11. The Megyn Kelly Show — Immigration Crackdown Coming to Chicago, Trump Backs RFK, CBS Changes Editing Policy: AM Update 9/8

- Episode 4165; estimated 0:04:22; score 5/5; confidence 0.99
- Tags: mixed; covid19, mandates_or_policy, development_or_approval, safety_or_side_effects, conspiracy_or_institutional_trust; potential-misinfo triage, politicized
- Model summary: Reports RFK Jr. ending mRNA funding, firing CDC head, and claiming US had worst COVID outcomes due to ignoring science.
- ASR excerpt near retrieval term: “…Jr. facing mounting calls to resign following a fiery hearing before the Senate Finance Committee late last week on Capitol Hill. Some highlights here: the mRNA technology is about continuing the research to be ready. I'm happy to have a detailed discussion with you about it. You're so wrong on your facts. You're…”
- Candidate ID: `episode_4165_clip_1`; source segment 0:00:00–0:10:00

### 12. The Megyn Kelly Show — Lisa Cook Investigation Grows, RFK vs. Senators, and Bari Weiss CBS News Rumblings, with Glenn Greenwald

- Episode 4179; estimated 1:19:58; score 5/5; confidence 0.99
- Tags: mixed; covid19, safety_or_side_effects, efficacy_or_immunity, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, corrective context, politicized
- Model summary: Discussion on COVID death counts, vaccine efficacy data, and alleged links between vaccines and myocarditis.
- ASR excerpt near retrieval term: “…these are model studies. You don't know the answer of how many Americans died from COVID. This is the Secretary of Health and Human Services. Do you think the vaccine did anything to prevent additional deaths? Again, I would like to see the data and talk about the data. You have had this job for eight months, and you…”
- Candidate ID: `episode_4179_clip_2`; source segment 1:19:20–1:29:20

### 13. The Tucker Carlson Show — RFK Jr. Provides an Update on His Mission to End Skyrocketing Autism and Declassifying Kennedy Files

- Episode 4558; estimated 0:05:51; score 5/5; confidence 0.99
- Tags: mixed; childhood_schedule, safety_or_side_effects, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: RFK Jr. alleges CDC used fraudulent techniques to hide a link between vaccines and autism and ignored recommended studies.
- ASR excerpt near retrieval term: “…The problem is that the Institute of Medicine. In which is part of the National Academy of Sciences, had said in two thousand one that the link between autism vaccine is biologically plausible, and they they were highly critical of the way that CDC was making the decisions about the vaccine schedule. That it was, you…”
- Candidate ID: `episode_4558_clip_1`; source segment 0:00:00–0:10:00

### 14. The Shawn Ryan Show — #163 Gary Brecka - Biohacking Secrets to Longevity, Aging Myths and the Science of Nutrition

- Episode 8519; estimated 0:42:00; score 5/5; confidence 0.99
- Tags: supportive; childhood_schedule, safety_or_side_effects, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Alleges newborns receive unnecessary Hepatitis B vaccines, links increased vaccine schedules to autism and chronic disease pandemics.
- ASR excerpt near retrieval term: “…longest, then why were we trying to push this compound down? I mean, cholesterol medication is one of the most profitable pharmaceutical compounds until the vaccine came along. One of the most. Profitable compounds to ever hit modern humanity. I mean, in in in the fifties and sixties, the you know cholesterol…”
- Candidate ID: `episode_8519_clip_2`; source segment 0:39:40–0:49:40

### 15. Candace — INSANE UPDATE! Brigitte, Blake Lively, And The Globalized Press. | Ep 226

- Episode 10554; estimated 0:24:42; score 5/5; confidence 0.99
- Tags: mixed; covid19, safety_or_side_effects, misinformation_or_fact_checking; potential-misinfo triage
- Model summary: Ad claims COVID vaccines caused fertility issues and egg count reduction, promoting a detox supplement to clear spike proteins.
- ASR excerpt near retrieval term: “…to talk to you about the wellness company because there have been a lot of people who are struggling to conceive. Maybe you're somebody that took the COVID vaccine and you have cause for concern, and you're not alone, by the way. A recent study that was led by a Danish researcher named Dr. Menichi analyzed birth…”
- Candidate ID: `episode_10554_clip_1`; source segment 0:19:50–0:29:50

### 16. The Shawn Ryan Show — #125 Gina Carano - Disney Crumbles After Mandalorian Star Uses Beep, Bop, Boop for Pronouns

- Episode 11125; estimated 2:38:45; score 5/5; confidence 0.99
- Tags: mixed; covid19, mandates_or_policy, safety_or_side_effects, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Guest links forced vaccinations to Satanic influence, criticizes ADHD meds and climate change efforts as playing God.
- ASR excerpt near retrieval term: “…because I knew that internally I couldn't not speak. I didn't have children, and I want—I didn't want it to get to the place where there would be forced vaccinations and forced all this, all the things that did happen. I didn't want to get to the point where people who had families were losing their jobs, and…”
- Candidate ID: `episode_11125_clip_3`; source segment 2:38:40–2:48:40

### 17. Candace — BANNED! My Interview With Tristan Tate

- Episode 11185; estimated 0:39:43; score 5/5; confidence 0.99
- Tags: mixed; covid19, hpv, polio, conspiracy_or_institutional_trust, safety_or_side_effects, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Guest describes leaving the 'cult of science,' claims Gardasil caused seizures, and contrasts modern vaccines with Jonas Salk's polio vaccine.
- ASR excerpt near retrieval term: “…a lot, a lot of. What scientists have discovered over the years, and you know, there's there's good scientists and there's bad scientists. There's the COVID vaccine, and there's Jonas Salk with his polio vaccine, which is maybe slightly more moral than the. We go down this rabbit hole if you like, slightly a more…”
- Candidate ID: `episode_11185_clip_1`; source segment 0:39:40–0:49:40

### 18. REAL AF with Andy Frisella — 796. Andy & DJ CTI: Trump Challenging Election Results?, North Carolina Hurricane Recovery Team Relocated & New Cancer Treatment Protocol

- Episode 11500; estimated 0:54:08; score 5/5; confidence 0.99
- Tags: supportive; covid19, mandates_or_policy, conspiracy_or_institutional_trust, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Alleges government officials planned pandemic response to control society and that PCR tests were manipulated to inflate cases.
- ASR excerpt near retrieval term: “…If he does, because I think Trump is going to fucking get involved in this. And it's going to be a sticky situation because he went along with the fucking vaccine shit. Yeah, bro. Yeah, that that that's still to me one of the most interesting. I don't like it, dude. I fucking hate it. But it's like the thing is,…”
- Candidate ID: `episode_11500_clip_2`; source segment 0:49:35–0:59:35

### 19. REAL AF with Andy Frisella — 773. Andy & DJ CTI: Georgia School Shooter, Commanders Suspend VP For Comments & Right-Wing Influencers Duped

- Episode 11709; estimated 0:29:45; score 5/5; confidence 0.99
- Tags: supportive; covid19, mandates_or_policy, conspiracy_or_institutional_trust; potential-misinfo triage, politicized
- Model summary: Speaker alleges Democrats wanted to jail unvaccinated people to disarm the population and eliminate resistance.
- ASR excerpt near retrieval term: “…to ban guns the most. Now, during COVID, who was saying you don't deserve to be in society? What are we going to do with all these people that won't take the vaccine? You're a fucking grandma killer. You deserve to be in jail. You You deserve to be in a camp. Who was saying that? Democrats. Okay. Now, those are the…”
- Candidate ID: `episode_11709_clip_2`; source segment 0:29:45–0:39:45

### 20. Habits and Hustle — Episode 453: Dave Asprey: Biohacking Secrets - Testosterone, Peptides, and Daily Routines for Optimal Human Performance

- Episode 14840; estimated 0:49:35; score 5/5; confidence 0.99
- Tags: supportive; childhood_schedule, mmr_measles, hpv, polio, safety_or_side_effects, efficacy_or_immunity, conspiracy_or_institutional_trust, personal_decision_or_uptake, misinformation_or_fact_checking; potential-misinfo triage, politicized
- Model summary: Guest links vaccines to autism, rejects most schedules, claims polio was chemical-induced, and asserts natural infection provides better immunity.
- ASR excerpt near retrieval term: “…privacy is theirs, not mine. So they're teenagers, and they they get to decide what they disclose or don't disclose. Okay. So, are you a believer of vacc vaccines now? I have always been very concerned because this whole autism thing, and I've interviewed even back in the in the '90s. I started an autism…”
- Candidate ID: `episode_14840_clip_2`; source segment 0:49:35–0:59:35

## Caveats and next checks

- Retrieval uses vaccine-focused lexical patterns; euphemistic discussion without those terms may be missed.
- Clip timestamps are estimated within 10-minute ASR chunks. Always inspect the source segment/audio before quoting.
- ASR can garble names, negation, speaker changes, and advertisements; the transcripts have no diarization.
- Stance and potential-misinformation tags are model judgments requiring human validation. The latter is a review queue, not a factual verdict.
- Repeated ads, previews, or syndicated excerpts can make clips non-independent.
- The brief sets aside low-notability, unflagged vaccine ads/PSAs; they remain tagged in `clip_tags.jsonl`.
- Ten-minute windows may contain an ad plus later discussion; treat the model's content-type label as provisional.
- Spot checks found inconsistent stance polarity (for example, `supportive` sometimes meant support for a speaker's skeptical argument rather than support for vaccination); do not interpret stance as pro/anti without recoding.
