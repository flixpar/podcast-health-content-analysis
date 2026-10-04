# What capping DeepSeek-V4-Flash's thinking loses

Runs: `dev-high-chat-lenient` (no budget, repeats 0 and 1) against `dev-high-budget16k-lenient` (repeat 0 only; repeat 1
has no manifest yet), and `s70-high-chat-lenient` against `s70-high-budget{16,12,8,4}k-lenient` (2 repeats each).
Scored with `scoring.score_item` and `matching.assign` against `gold.jsonl`, over the 161 non-contrast dev items (as
`compare.py` does). Scripts: `docs/labeling-experiments/scripts/tb_*.py` (`PYTHONPATH=. .venv/bin/python docs/labeling-experiments/scripts/tb_extract.py <cache.pkl>` builds the cache; the others read it from `$TB_PKL`).
"Chat" means the unbudgeted run. "Lost" means a required gold atom that the unbudgeted run matched and the budget run did not.

## 1. Headline: the loss is real, but the dev 16k repeat overstates it

Full dev (161 items), pooled strict metrics:

| metric | chat r0 | chat r1 | 16k r0 |
|---|---|---|---|
| frame F1 / recall / precision | .773 / .692 / .876 | .771 / .684 / .884 | **.681 / .565** / .856 |
| frame atoms predicted | 339 | 336 | 284 |
| evidence F1 / atoms | .778 / 368 | .794 / 381 | .791 / 315 |
| claim recall / precision / claims | .661 / .912 / 724 | .712 / .890 / 812 | .595 / .909 / 649 |
| topic F1 / precision | .676 / .831 | .673 / .829 | .697 / .862 |

Item bootstrap (2000 draws): frame F1 16k−chat r0 = −.093 [−.132, −.053], while chat r1−chat r0 = −.002 [−.040, .037].
Claim recall 16k−chat r0 = −.065 [−.139, .010], but chat r1−chat r0 = **+.053**, so the claim delta against a single
unbudgeted repeat is within repeat noise. Against the mean of both chat repeats it is −.091 [−.159, −.023].

Within dev r0 the frame loss is spread across items, not a few outliers: 42 items lose frame TPs and 18 gain (chat r0→r1:
30 lose, 29 gain). Even after dropping the 10 worst items for the 16k run (a choice that favours it), frame F1 is still
.713 against .765/.774. Removing the 2 collapsed windows (§7) leaves .685 against .773/.768.

**But it does not replicate at the same size.** The 70 s70 items are a subset of dev, and the run fingerprints match. On
those 70 items there are 4 unbudgeted repeats and 3 16k repeats:

| 70 shared items | frame TP | frame F1 | frame R | frame P | claim R |
|---|---|---|---|---|---|
| dev chat r0 / r1 | 140 / 141 | .791 / .783 | .714 / .701 | .886 / .887 | .684 / .761 |
| s70 chat r0 / r1 | 135 / 137 | .750 / .765 | .685 / .685 | .828 / .867 | .689 / .684 |
| **dev 16k r0** | **106** | **.646** | **.533** | .822 | .598 |
| s70 16k r0 / r1 | 127 / 126 | .743 / .741 | .635 / .630 | .894 / .900 | .686 / .667 |

- All 3 budget repeats sit below all 4 unbudgeted repeats on frame TP and frame recall.
- Dev 16k r0 is 20 frame TPs below the other two 16k repeats. The signed chat-to-chat differences range from −6 to +2,
  so this repeat is unusually low, not ordinary noise.
- On the 91 dev items outside s70 the dev 16k loss is smaller (frame F1 .758/.761 → .710).
- Pooled 3×16k vs 4×chat: frame F1 **−.061 [−.088, −.034]**, frame recall −.097 [−.137, −.059], claim recall −.054
  [−.100, −.008], evidence F1 −.002.
- Without dev 16k r0: frame F1 **−.030 [−.060, .000]**, frame recall **−.064 [−.102, −.027]**, claim recall −.028
  [−.079, +.015].

The best estimate at 16k is therefore a frame **recall** loss of about 0.06–0.10. Part of it comes back as higher frame
precision (s70: .848 → .897), so F1 drops about 0.03–0.06, not 0.09. The only manifest differences between the dev and
s70 runs are concurrency (256 vs 140) and wall-clock time. Dev 16k repeat_1, when it finishes, will show whether r0 was
unlucky or whether something at c256 differs.

## 2. What disappears: frame overlays are omitted, while topic coverage stays

Required frame gold on full dev, found by chat r0 / chat r1 / 16k r0 (largest labels, plus conspiracy-type frames for contrast):

| frame label | required | chat r0 | chat r1 | 16k | change vs chat mean |
|---|---|---|---|---|---|
| misinformation_correction_debunking | 36 | 30 | 27 | **15** | −13.5 |
| naturalness_appeal | 43 | 27 | 33 | **19** | −11 |
| commercialization | 97 | 83 | 83 | 73 | −10 |
| optimization_framing | 25 | 14 | 11 | **6** | −6.5 |
| root_cause_framing | 22 | 15 | 17 | 12 | −4 |
| anti_mainstream_medicine_framing | 29 | 19 | 20 | 16 | −3.5 |
| purity_contamination / toxin | 20 / 16 | 14 / 12 | 11 / 14 | 11 / 11 | −1.5 / −2 |
| government_distrust / big_pharma / conspiracy_cover_up | 19 / 15 / 10 | 8 / 10 / 5 | 6 / 6 / 3 | 9 / 9 / 3 | +2 / +1 / −1 |

The budget run loses the **mild, pervasive frames**: debunking tone, "natural/real food", "optimize", a host plugging a
product. Explicit conspiracy frames ("big pharma", "they're corrupt") survive, because the vocabulary that signals them is
hard to miss. On s70 the same labels lead the budget sweep. naturalness_appeal (19 required) is found 17/13 without a
budget, 11/13 at 16k, 10/8 at 12k, 9/10 at 8k and 3/5 at 4k. At 8k and below commercialization and medical_freedom join them.
Evidence labels barely move at 16k (credential_appeal 29/32 → 25 and weak_evidence 14/15 → 11 are the largest drops).

**How each lost gold atom was missed** (`scoring._miss_class` applied to the budget run's output):

| lost required gold | cross_axis: a topic or evidence detection covers the span, no frame | wrong frame label on the span | span only | nothing there | gained |
|---|---|---|---|---|---|
| frame, chat r0 → 16k | **45** | 22 | 5 | 9 | 26 (lost 81) |
| frame, chat r0 → chat r1 (noise) | 23 | 14 | 5 | 3 | 40 (lost 45) |
| frame, s70 chat → 8k (r0→r0 + r1→r1) | 53 | 19 | 9 | 7 | 23 (lost 88) |
| claim, chat r0 → 16k | — | — | 19 different claim | 143 | 99 (lost 162) |
| claim, chat r0 → chat r1 (noise) | — | — | 18 | 91 | 155 (lost 109) |

So at 16k the typical failure is that **the model still labels the passage's topic but leaves off the cross-cutting
overlay**. Substitutions add a little (22 vs 14 in noise), and they are mostly between neighbouring frames:
purity_contamination→naturalness_appeal (4), →toxin (2), toxin→geo_environment_conspiracy (2).

The other attributes do not change at 16k:
- discourse role on matched frames agrees with gold .936/.936 → .918;
- matched frame span IoU is .698/.724 → .717;
- claim_type agreement is .356/.364 → .415 and certainty agreement .817 → .824;
- 5.1 topic detections per window on both sides, and topic precision rises (.831 → .862).

At 8k and 4k the answers do get worse: frame IoU drops to about .64/.59 and certainty agreement to about .73.

**Claims.** Required claims by gold claim_type, found chat r0 / r1 / 16k: mechanism 248: 160/182/**139**; causal 171:
108/128/**93**; risk_or_safety 71: 52/46/**36**; treatment 143: 92/90/84; diagnosis 93: 63/72/63; other_factual 185:
116/121/110; institutional_or_conspiracy 33: 15/13/18. Sponsor-read (`advertisement`) claims 151: 97/113/**84**. The loss
is concentrated in mechanism and causal claims, which are the dense, many-per-window kinds.

## 3. Examples (gold found by both chat repeats, missed by the budget run)

**E1 `c182721w0002` (health_dense, Dr. Hyman "Pegan Diet: Eat to Boost Mood"; chat reasoning 40.9k/39.7k; 16k capped).** Frame TPs 9/8 → 4.
> [5] "Unfortunately, medical practice is pretty slow to catch up to all the research…" — gold `anti_mainstream_medicine_framing` (4/4 annotators).
> [23–26] "How about we get to the root cause? That's what functional medicine is, right? How do we get to the root cause?" — gold `root_cause_framing` (4/4).
> [76] "…it's about eating real, whole food, which then your body knows what to do with." — gold `naturalness_appeal` (4/4).

Both chat repeats output the frame on each span, e.g. `frame:root_cause_framing 22-26 "How do we get to the root cause? That's the key to healing"`.
At 16k the same spans carry only topics: `topic:natural_alternative_functional_medicine 22-26`,
`topic:diet_tribes_food_ideologies 75-77`, and on [5] `topic:food_nutrition`/`mental_health`. That makes all 5 losses
cross_axis. Chat r0 also shows the claim-section drop from §5 here: 1 claim, against 20 in r1 and 12 at 16k.

**E2 `c179765w0001` (health_dense, Afterpause "Unlock Your Health Equation").** A health-coaching pitch runs through the episode:
> [13] "…how a health coach may be able to help you reach your goals." [26] "A coach can help you sort through the noise…" [36] "That's where a health coach can make all the difference." [59] "And this is where health coaches can make a big difference too."

Gold has 4 `commercialization` atoms (2–3 of 4 annotators each), and both chat repeats found all 4. The 16k run emitted
section-level topics (`sleep 14-27`, `food_nutrition 28-42`, `stress… 43-62`) and **no commercialization at all**. It kept
the `evidence_strength_claim` at [60]. Recognising this frame means seeing that the coaching line recurs across the whole window.

**E3 `c177018w0009` (rare_label, Gary Brecka with Iman Hasan).** Frame TPs 6/5 → 1.
> [36] "a lot of us… are walking around like a toxic soup and don't even realize it" — gold `toxin_framing` (4/4). Chat: `frame:toxin_framing 34-46` / `35-43`. 16k: only `geo_environment_conspiracy 40-42` ("chemtrails").
> [77–79] "Whole fear around red meat, guys. I just want to correct this. High quality red meat is actually incredible for you." — gold `misinformation_correction_debunking` (4/4). Both chat runs found it; the 16k run output no frame there. This is the window's last 3 units, but §4 shows the loss is not generally at the end of windows.

**E4 `c178272w0003` (discourse, Maintenance Phase "RFK Jr. and the Rise of the Anti-Vaxx Movement"; sarcastic rebuttal).**
> [29–34] "You learned so much in that clip, Aubrey… You also learned that the Russians invented Wi-Fi radiation, famously." — gold `misinformation_correction_debunking` (4/4, role mostly `rebutted`).

Both chat runs: `frame:misinformation_correction_debunking 29-41 role=rebutted`. At 16k: `topic:emf_technology_exposure 29-41
role=rebutted` and no frame. So the budget run did recognise the rebuttal (the topic's role is right) but did not add the
debunking overlay. The same pattern cost `toxin_framing` at [18] "all these toxins… can now go into your brain" (reported).
This is the main mechanism behind the discourse stratum's drop: frame F1 .759/.766 → .513 on 13 items with 48 required frames.

**E5 `c181355w0013` (rare_label, SuperLife with Chris Wark): substitution, not omission.**
> [45] "People tend to get into sort of scientism, where they worship science…" — gold `anti_expert_populist_framing`. 16k: `government_institution_distrust 44-50` quoting "the medical establishment is corrupt".
> [65–66] "doctors are actually in this very tightly controlled. System where they're not even allowed to practice medicine" — gold `conspiracy_cover_up`. 16k: `anti_mainstream_medicine_framing 65-67`, same quote.

**E6 `c78401w0009` (rare_label, Jon Stewart "Abortion: Mission Impossible"; s70, 8k, both repeats).**
> [32–35] "Any other law that compels a person ostensibly to save someone else's life?… Could I ever be compelled to do that?" and [43] "mandatory vaccinations… is an intrusion on your bodily autonomy" — gold `medical_freedom` (2/4 and 4/4).

Both chat repeats found both (`frame:medical_freedom 31-39`, `42-64` / `43-43`). The two 8k repeats output 11 and 8 topic
detections covering the same units (`reproductive_sexual_health 31-39`, `vaccines_immunization 41-43`) and **zero
frames**. Here the frame is an argument built across the window, not a keyword.

**E7 `c190562w0004` (health_dense, Thyroid Fixer "Weight Loss Supplements"): claims section cut to its first item.** Chat: 16 and 13 claims (15/13 TP); 16k: 10 detections but **1 claim**, the window's first:
> [6] "The more stress a person is under, the more epinephrine, norepinephrine, and cortisol are secreted."

The run lost 11 required claims that both chat repeats had, for example:
> [12] "L-tyrosine can improve mood because it helps produce dopamine." (both chat runs)
> [47–49] Forskolin activates adenylate cyclase, which increases cyclic AMP (mechanism)
> [61] "It takes 3,500 calories to equal one pound."

**E8 `c184181w0018` (health_dense, School of Greatness with Dr Gundry): collapse after the forced stop.** Chat: 30 and 35 atoms. The 16k run used exactly 16,000 reasoning tokens, then produced a 155-token answer with 1 detection. Its summary leaks the reasoning:
> "A patient is quoted as having avoided coronavirus… Suggesting her diet was the reason. Actually need concise. Let's fix later."

It lost `commercialization` on "For instance, Gundry MD makes a 24 strain probiotic" and "I make Prebio Thrive", plus 5
claims and 4 evidence atoms. `c176979w0018` collapsed the same way: 44 answer tokens and an empty result, against 33/38
atoms without a budget. That one window accounts for 10 lost claims and 6 lost evidence atoms.

## 4. It is the capped windows that lose, not long windows or the end of windows

The unbudgeted model thinks a lot: median 20.1k reasoning tokens per window, maximum 55.6k, and 109 of 176 dev windows
over 16k. How much it thinks is stable across repeats (Spearman .87). It tracks how much there is to label (ρ = .91 with
required gold count), **not window length** (ρ = .07 with word count; all windows are about 900 words).

Split by whether the 16k run hit its cap:

| 16k run | windows | median chat reasoning | frame R | evidence R | claim R | topic R | TP change frame / evid / claim / topic |
|---|---|---|---|---|---|---|---|
| capped at 16,000 | 93 | 28.0k | .69 → .56 | .75 → .70 | .69 → .59 | .57 → .60 | −54 / −23.5 / −99.5 / +30 |
| finished under budget | 68 | 4.1k | .67 → .67 | .75 → .74 | .68 → .65 | .52 → .50 | 0 / −1.5 / −2 / −6.5 |

By unbudgeted thinking need (mean of chat r0/r1; recall chat → 16k):

| chat reasoning | windows | frame R (TP) | claim R (TP) |
|---|---|---|---|
| < 16k | 66 | ~flat (+2.5 TP) | ~flat (−0.5 TP) |
| 16–24k | 32 | .70 → .69 (−1) | .67 → .57 (−25) |
| 24–32k | 35 | .68 → .60 (−11.5) | .73 → .66 (−30) |
| > 32k | 28 | **.72 → .43 (−44)** | .64 → .51 (−46) |

- The windows over 32k account for 44 of the 54 lost frame TPs. Excluding the 2 collapsed windows the drop is still .71 → .45.
- s70 16k shows the same direction but much weaker (>32k bin: frame .70 → .65), again pointing at dev r0.
- At 8k the >32k bin loses frame .70 → .42 and evidence .89 → .54; at 4k, .70 → .32 and .89 → .34.

Because thinking need and gold density move together, per-window TP change correlates about equally with thinking need
(ρ = −.39) and required gold (ρ = −.35). Controlling for required gold, thinking need **still predicts frame loss** (partial
ρ = −.29, p < .001) but **not claim loss** (partial ρ = −.01). This fits the idea that frames need extra whole-window
reasoning, while claims are lost roughly in proportion to how many there are.

**No tail effect.** Required gold found, by third of the window (chat mean → 16k): frames T1 .62→.46, T2 .72→.61, T3
.66→.53; claims T1 .66→.57, T2 .65→.60, T3 .68→.55; topics flat. The frames the budget run does predict are spread the
same way (33% in the last third vs 35%). The capped model does not stop partway through the transcript; it drops a whole
kind of annotation across the window.

## 5. Claims: most of the swing is whole-section drops, which also happen without a budget

The model sometimes emits a nearly empty `verification_candidates` list (≤ 2 claims where the other repeats have ≥ 6):

| comparison | windows | claim TP lost there |
|---|---|---|
| 16k r0 drops (both chat repeats have ≥ 6) | 9 | 84 |
| chat r0 drops (r1 has ≥ 6) | 7 | 72 |
| chat r1 drops (r0 has ≥ 6) | 4 | 40 |
| s70 16k r0 / r1 drops (both chat repeats have ≥ 6) | 0 / 1 | 0 / 14 |

About half of the chat r0/r1 claim-recall gap (.661 vs .712; 32 of 63 net TPs) comes from such events. The dev claim loss at 16k is only somewhat
more of the same instability (E1, E7). The claim-recall metric needs more repeats before a 0.05 delta means anything.

## 6. Budget sweep on s70 (70 items, mean of 2 repeats)

| budget | windows capped | frame F1 / R / P | frames per window | frame IoU | evidence F1 | claim R | topic F1 | certainty agreement | annotations dropped by validation |
|---|---|---|---|---|---|---|---|---|---|
| none | 0 | .758 / .685 / .848 | 2.30 | .70 | .789 | .687 | .684 | .81 | 5 |
| 16k | 41.5 | .742 / .633 / .897 | 2.02 | .68 | .785 | .677 | .701 | .80 | 8 |
| 12k | 49 | .716 / .603 / .882 | 1.93 | .71 | .746 | .669 | .673 | .79 | 16.5 |
| 8k | 51.5 | .655 / .516 / .898 | 1.61 | .64 | .703 | .615 | .667 | .73 | 25.5 |
| 4k | 57 | .573 / .445 / .809 | 1.53 | .59 | .631 | .569 | .624 | .74 | 55.5 |

Frame recall falls steadily from the first cap, and precision holds until 4k. Evidence stays flat through 16k and then
falls. Topics are almost unaffected down to 8k. Tighter budgets also produce more answers that fail validation and get
dropped: `certainty_markers_mismatch`, `mixed_or_unknown_labels` (16–17 per 4k repeat) and `non_verbatim_quote`. That is a
second, smaller way annotations are lost. Answer length does not change: the median non-reasoning output is 1.7–1.8k
tokens at every budget, and only 15.2 → 12.1 atoms per window from no budget to 4k.

## 7. Other observations

- **Forced stops can collapse the answer** (E8). In 2 of 93 capped dev windows the answer was ≤ 155 tokens with 0–1
  atoms, and one summary contains leaked reasoning. Removing those 2 windows changes the frame result very little
  (.685 against .773/.768).
- **The dev 16k r0 anomaly is unexplained.** Its s70 items lose 34 frame TPs against dev chat r0; the s70 16k repeats lose
  8–15 against any unbudgeted repeat. Concurrency (256 vs 140) is the only configuration difference. Dev chat at c256 is not worse than s70 chat at
  c140, but that does not rule out the thinking budget behaving differently under heavier batching. Check dev 16k
  repeat_1 before quoting −0.09.
- **A budget makes the labeler more conservative:** fewer frames but more precise (s70 frame precision .85 → .90 at
  16k and 8k), topic precision up, and claim_type agreement on matched claims slightly up. Scored only on precision, 16k looks better.
- **Practical reading.** 16k costs about 0.06–0.10 frame recall, entirely on the roughly 60% of windows that would think
  past 16k, most of all on the densest windows (>32k). 12k falls between 16k and 8k. 8k is a clear step down on frames, evidence
  and claims. If throughput needs a cap, a recall-oriented second pass over capped windows (frames only) could recover
  most of the loss.
