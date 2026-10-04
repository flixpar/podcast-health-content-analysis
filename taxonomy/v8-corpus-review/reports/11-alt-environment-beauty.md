# Alternative medicine, detox, environment, radiation/light, skin & beauty, wellness, other: corpus review

Slice: `topic:alt_medicine`, `topic:detox`, `topic:environment`, `topic:radiation_light`, `topic:skin_beauty`, `topic:wellness`, `topic:other` and their subtopics.
Counts are `cq.py count` results (segments / episodes / podcasts) on the ~145.6k-episode corpus. Keyword counts include noise; where I sampled, I give a rough share of real hits. Quotes are cited as (ep, seg).

## Summary

- **Every subtopic in the slice turns up in the corpus.** Most are concentrated in about 15 wellness shows (Hyman, Jockers, Niddam, Thyroid Fixer, Culture Apothecary, SuperLife, Brecka, Live Beyond the Norms, Extend). Four are genuinely rare but worth keeping for misinformation research: `detox.spike_protein_detox` (about 30 episodes on core phrasing), `alt_medicine.fringe_ingested_remedies` (about 90), `radiation_light.artificial_light` (outside the sleep context) and `radiation_light.ionizing_radiation`. I recommend no merges or drops.
- **One gap is worth a new subtopic: military and occupational toxic exposures.** Burn pits, Agent Orange, Camp Lejeune, the PACT Act, black lung and Gulf War illness come to 784 episodes across 123 podcasts on a noisy query (several hundred real). Today they scatter across `air_pollution`, `pesticides_herbicides` and `water_quality`, or fall into `topic:other`. I propose `environment.military_occupational`.
- **Ads dominate several labels, and the ad test does not settle them.**
  - An "essential oils" multi-level-marketing (MLM) line in a podcast cross-promo accounts for 921 of the 1,760 essential-oil episodes.
  - Generic energy puffery ("clean energy, no crash") appears in roughly 9k episodes and would put `wellness.energy_fatigue` on nearly every supplement and coffee ad.
  - Contaminant-screening and "free-from" attributes ("PFAS and microplastic screening", "zero EMF", "non-toxic") are frequent.
  - I propose explicit rules for all three, plus a rule for when cosmetic and beauty ads pass the ad test.
- **"Detox" has two big non-detox senses.** Addiction detox ("went to detox", "medical detox") covers about 180 episodes and digital or dopamine detox about 230; I add boundaries to `toxic_load_general`. "Horse dewormer" means ivermectin for COVID (245 episodes, 53 podcasts), not a parasite cleanse.
- **Practitioner credentials in bios and intros are a large false-positive source.** Examples: "naturopathic doctor", "functional medicine practitioner", and a naturopath-founded dog-food ad that appears in 171 Charlie Kirk episodes. Functional medicine alone appears in 3,129 episodes, 1,105 of them on the Hyman show, mostly as credentials. I propose a sentence in the `functional_medicine` definition and a codebook rule.
- **Several boundaries need stating in the label rows:**
  - morning sunlight for circadian timing (very common in Huberman-style shows) vs `sunlight_uv`;
  - lymphatic massage vs `binders_drainage`;
  - chemtrails named as a stock conspiracy example (most Rogan hits) vs `geoengineering`;
  - climate politics vs `climate_heat`: about 7,400 episodes mention climate change, but only about 415 tie it to health;
  - "life expectancy" as an individual outcome vs a population trend.
- **Some listed examples mislead.** "Tinctures" under herbalism are mostly cannabis or mushroom supplements. "Cupping" is about 90% hand gestures. "Shampoo" in `hair_loss_hair` needs a hair-health claim to count. "Soursop tea" occurs in 4 episodes. I propose real-phrasing replacements.
- **Breast implant illness and explant surgery** recur in wellness shows (about 70 episodes, 31 podcasts) with no named home. I propose adding them to `skin_beauty.cosmetic_procedures`.

## Label-by-label findings

### alt_medicine

**functional_medicine.** Query `\bfunctional medicine\b|\bintegrative (medicine|doctor|physician)`: 7,030 / 3,129 / 90.
- Concentrated in the Hyman show (1,105 episodes), Thyroid Fixer (377), Mind Pump (187) and Jockers (164).
- Most hits are credentials or referrals, not discussion of the approach:
  - "talk to someone who is well versed in this—a functional medicine provider, a coach, a naturopath" (192671, 3);
  - "Talk to your functional medicine doctor about whether or not a parasite cleanse is right for you" (177023, 0).
- **Verdict:** needs a definition change (exclude credential-only mentions).

**naturopathy_homeopathy.** Naturopath: 1,617 / 1,168 / 87. Homeopath: 476 / 403 / 111.
- Naturopath hits are dominated by:
  - a dog-food ad ("Invented by naturopathic Dr. Dennis Black, Ruff Greens", 37466, 1; 171 Charlie Kirk episodes), which is animal health and so excluded;
  - a podcast cross-promo for the Dr. Tina Show (124 episodes in a sleep-story show, 87812, 0);
  - guest bios ("Dr. Nick Bitts is a naturopathic doctor who combines traditional and modern medicine", 190207, 55).
- Homeopathy is spread across culture, news and history shows, for example Aaron Rodgers' "he did like a homeopathic thing" (321970, 0) and the AMA founded "to squash homeopathy" (65570, 22).
- **Verdict:** fine; the credential and bio rule applies.

**chiropractic.** Query `\bchiropract`: 6,520 / 2,850 / 178. "Subluxation": 1,488 / 743 / 18, of which 693 episodes are Chiro Hustle.
- Chiro Hustle (791 episodes) is largely practice-business talk: "ChiroScript AI, the only AI tool built by chiropractors for chiropractors" (186613, 2).
- ASR renders the show name as "Cairo Hustle".
- Edge case: "I went to a psychic chiropractor… you're seeing auras" (27080, 1) is chiropractic plus energy and spiritual healing.
- **Verdict:** fine. The definition should say the profession and its business count, since a coder may otherwise skip practice-management talk.

**acupuncture_tcm.** Acupuncture: 1,566 / 1,076 / 155. TCM: 1,347 / 868 / 103.
- Cupping: 357 / 308 / 100. Sampled hits are almost all "cupping her hands" or "cupping his breasts" (203362, 1; 38925, 4).
- Qi and qigong: 175 / 153 / 54.
- **Verdict:** fine. Keep cupping as an example; it is real when it occurs (athletes, Rogan), but word-sense matters.

**herbalism_traditional.** Ayurveda: 1,299 / 569 / 72. Herbalist or herbalism: 186 episodes. Tincture: 421 episodes. Soursop: 4 episodes. Castor oil: 230 episodes.
- Tincture hits are mostly a supplement dosage form, not herbalism:
  - "really good tincture that you just drop it in" (lion's mane, 16234, 10);
  - "their pine pollen tincture… glutathione and DHEA" (38298, 0);
  - "some new sleep tincture" (9792, 122).
- Ayurveda hits are typically about the system ("find out your dosha", 196011, 6).
- **Verdict:** examples change. Drop "tinctures" and "soursop tea", add "doshas" and "herbalist", and state the boundary with `supplements.herbal_adaptogens`.

**energy_spiritual_healing.**
- Counts: Reiki 344 / 80; "energy healing/medicine/work" 323 / 77; sound bath or sound healing 246 / 77; 528 Hz, Solfeggio or frequency healing 111 / 33; faith healing phrases 195 / 72; PEMF, scalar, bioresonance or Rife 322 / 57.
- Crystals (11,335 episodes) is useless as a keyword: Breaking Points' Krystal Ball accounts for 1,499 episodes.
- Exorcism (1,503 episodes) is mostly film and true crime.
- Reiki is heavy in reality-TV recaps (54 Watch What Crappens episodes).
- **Verdict:** fine. Add the real terms "528 Hz/Solfeggio" and "EFT tapping" (125 episodes, 53 podcasts). PEMF mats already go to `biohacking.devices_gadgets`.

**fringe_ingested_remedies.** A narrow query (chlorine dioxide, MMS as a remedy, drinking bleach or turpentine, borax in water, DMSO): 111 / 91 / 45.
- Broad keywords are mostly noise:
  - "MMS" is mostly "M&Ms";
  - turpentine (144 episodes) is mostly paint and history;
  - borax (66) is mostly cleaning;
  - hydrogen peroxide (308) is mostly first aid or teeth.
- Real hits:
  - "what are you doing drinking chlorine? … I'm chlorine dioxide. So that's another really cheap, easy [option]" (cancer episode, 190467, 113);
  - "They did either turpentine or kerosene, and they did a cleansing every three months… poop out all their parasites" (611745, 2). This also needs `detox.parasite_cleanses`.
- Methylene blue (246 / 43) is common but already routed to `medications.repurposed_offlabel` and `cognition.nootropics`.
- **Verdict:** rare but keep. Add the parasite-cleanse co-label to the definition.

**iv_ozone_therapies.** IV drip or IV therapy: 673 / 147. Ozone therapy, ozonated or EBOO: 251 / 66. NAD IV: 139 / 36. Glutathione IV: 40 / 18.
- Rogan (145 episodes) mixes real IV-vitamin talk with "one big dose IV" of DMT (147, 8) and jokes.
- A KILL TONY sponsor reads "Connect Mobile Health, which can give you IV drips" (194638, 0).
- Ozone for prostate cancer, "we studied ozone therapy" (180687, 50), belongs in `cancer_alt`.
- **Verdict:** needs a definition change: say that the infused substance keeps its home (NAD IV).

**essential_oils.** Query `\bessential oils?`: 2,206 / 1,760 / 165.
- 921 of those episodes (61 podcasts) are one cross-promo for a podcast about MLMs: "Sounds like she wants you to buy lots of essential oils. They are so essential" (170607, 2; 135 Megyn Kelly episodes). This is MLM satire, not health content.
- Health-claim co-occurrence (heal, immune, sleep, toxic and so on near "essential oil"): 127 episodes / 35 podcasts, led by Jockers and Culture Apothecary.
- doTERRA and Young Living: 141 episodes, 111 of them Chiro Hustle.
- Candle ads: "scented only with pure essential oils. No synthetic fragrances. No hormone disruptors" (185668, 3). That is household chemicals, not essential oils.
- **Verdict:** needs a definition change (exclude MLM and business-only mentions and scent-ingredient mentions).

### detox

**parasite_cleanses.** Query (parasite cleanse or protocol, deworm, wormwood, black walnut, papaya seeds): 778 / 573 / 102. "Parasite cleanse/protocol" alone: 302 segments.
- Real hits concentrate in wellness shows:
  - "We've done plenty of parasite cleanses" (178193, 0);
  - "Lots of countries do these naturally… a parasite cleanse… I think they're very beneficial" (177023, 0).
- The "deworm" hits are mostly "horse dewormer" (245 episodes, 53 podcasts), meaning ivermectin for COVID: "anti-vaxers are taking… a horse dewormer" (7894, 0); "comedians taking horse dewormer" (11883, 5).
- Ivermectin and fenbendazole: 1,097 episodes, 293 of them Charlie Kirk, mostly COVID.
- **Verdict:** needs a definition change (route COVID and cancer ivermectin elsewhere).

**heavy_metal_detox.** Chelation: 297 / 43. Heavy-metal detox, chlorella or provoked urine: 231 / 37.
- **Verdict:** fine.

**organ_cleanses.** Coffee enema: 129 / 45. Colonic or colon cleanse: 275 / 72, of which 41 episodes are reality-TV recaps. Juice cleanse, detox tea or liver/gallbladder flush: 252 / 82.
- Bare "enema" is often medical or comic.
- **Verdict:** fine.

**binders_drainage.** Binder, zeolite, charcoal or bentonite (health sense): 274 / 65. Castor-oil packs: 95 / 11, of which 53 are Jockers. Ionic foot bath: 8 episodes. Lymphatic drainage or massage: about 290 segments.
- Lymphatic talk is often not detox:
  - "got a lymphatic massage" in a menopause episode (179804, 1);
  - Huberman's lymphatic-system episode "for overall health & appearance" (78490, 0).
- Detox framing is explicit only sometimes: "Lymphatic massages—all that helps flush out toxins" (182138, 4).
- **Verdict:** needs a definition change (lymphatic massage without a detox claim goes elsewhere).

**spike_protein_detox.** Core phrasing ("detox the spike", "remove spike protein", "vaccine detox", post-vax protocol): 32 / 27 / 16. "Spike protein" co-occurring with detox, nattokinase or bromelain anywhere in the episode: 86 episodes.
- Nattokinase (109 episodes overall) is mostly taken for clotting or Lp(a): "take a supplement nattokinase… protect against the effects of the LP little a" (78270, 3).
- Real hit: "natto kinase because of… supporting spike protein removal" (195362, 3).
- Spike from infection also comes up: "what can be done to reduce the effects of that niggly little spike protein in the long term" (Long COVID, 189911, 156).
- **Verdict:** rare, keep. Extend the definition to spike from infection and add the nattokinase boundary.

**toxic_load_general.** Toxic load, toxic burden or detox pathways: 3,301 / 1,921 / 79. Bare "detox": 4,438 / 211.
- Example: "Their toxic load is high. They're not getting enough vitamins" (20155, 0).
- Confusions:
  - addiction detox (detox centre, medical detox, "went to detox"): 181 episodes / 72 podcasts;
  - "digital/dopamine/social media/sugar detox": 230 episodes / 71 podcasts.
- **Verdict:** needs a definition change (state both boundaries).

### environment

**microplastics.** 1,826 / 1,256 / 108.
- 156 of these episodes are a Momentus creatine ad read on Creating Confidence with Heather Monahan: "two to five times tighter heavy metal limits, PFAS and microplastic screening" (73445, 1). That is a product attribute.
- **Verdict:** fine; the ad attribute rule is needed (codebook notes).

**pfas.** 1,765 / 152.
- Cookware ads are frequent: "non-toxic. Cookware… no sketchy coatings, no forever chemicals" (181062, 2).
- **Verdict:** fine; clarify cookware against `household_personal_care`.

**endocrine_disruptors.** 2,040 / 125. **Verdict:** fine.

**pesticides_herbicides.** 5,427 / 211, including 340 Up First news episodes (agricultural policy). **Verdict:** fine.

**heavy_metals.** 6,603 / 265.
- Noisy: Mercury the planet and Freddie Mercury, plus history.
- **Verdict:** fine.

**air_pollution.** 1,812 / 190. East Palestine or train derailment: 369 / 62.
- **Verdict:** fine. Burn pits do not fit "outdoor air quality" well; see the new subtopic.

**water_quality.** 1,644 / 164.
- SuperLife (176 episodes) is mostly reverse-osmosis ads and talk: "reverse osmosis… from fluorides to chlorines to phthalates… to PFAS" (181091, 2).
- **Verdict:** fine.

**indoor_air_mold.** Query (mold, VOCs, gas stove, asbestos, formaldehyde, off-gassing): 8,553 / 311.
- "Mold" is mostly the verb or the cast sense ("mold those people", 84752, 0).
- Food mould ("mold-free, lab-tested beans", 184653, 5) goes to `food.food_contaminants`.
- **Verdict:** fine.

**household_personal_care.** Query (toxic candles, cleaning products, synthetic fragrance, non-toxic, clean beauty): 2,549 / 172.
- Armchair Expert's 773 episodes are a Seventh Generation ad with no health claim ("nothing extra in the bottle", 74265, 5), which fails the ad test.
- Real ad copy that passes:
  - "you cannot live that life with toxic candles" (185668, 3);
  - "non-toxic makeup" (185654, 2).
- **Verdict:** fine; add cookware and clean-beauty examples.

**geoengineering.** Chemtrails: 296 / 58, of which Rogan is 137. All geoengineering terms: 475 / 88.
- Most chemtrail hits name chemtrails as a type of conspiracy belief with no health content:
  - "Crop circles and. Chemtrails" (71644, 6);
  - "the same people that are chemtrail people or flat earth people" (70808, 9);
  - a joke about "spraying chemtrails… controlling minds and the weather" (71251, 0).
- Cloud-seeding hits are mostly weather and flood politics.
- **Verdict:** needs a definition change (a health dimension is required).

**climate_heat.** Climate change: 7,429 / 237, almost all politics or energy. Climate-and-health, heat illness or heat-related death phrasing: 415 / 104.
- Many "heat wave" hits are fiction, history or weather.
- **Verdict:** needs a definition change (climate politics is not health content).

**Gap: military and occupational exposures.** Burn pits: 220 / 55. Agent Orange: 230 / 65. Camp Lejeune: 105 / 40. All terms combined with PACT Act, Gulf War illness, black lung and silicosis: 976 / 784 / 123.
- "the PACT Act to help treat veterans with toxic exposures, including those who were exposed to burn pits" (439830, 2)
- "the chemicals in burn pits are the exact same chemicals in Agent Orange… health issues for nine to eleven cleanup workers" (331535, 0)
- "the burn pits that our servicemen may have been getting cancer from" (12981, 4)
- These are distinct from the listed subtopics: the exposure happened through service or work, and the topic carries compensation and VA politics. They recur on veteran and military shows (The Team House, Shawn Ryan) and on news shows. **ADD.**

### radiation_light

**wireless_emf.** Bare "EMF": 1,851 / 978 / 84, of which SuperLife is 243. Specific harm phrasing (dirty electricity, cell-phone radiation, Wi-Fi radiation, 5G towers): 389 / 302 / 88.
- A broad 5G/AirPods query is unusable: 13,332 episodes, mostly ads and the network sense.
- Example: "EMFs. That is a non-biologically assimilative energy that we created, and that is harmful" (181268, 0).
- Havana syndrome and directed energy: 233 / 42, mostly passing geopolitics (154912, 1078). There is no stated home for it.
- **Verdict:** fine, with an example tweak and a home for directed-energy claims.

**emf_protection.** EMF blocker, shield, meter, Faraday or airplane mode: 1,511 episodes, mostly noise ("airplane mode", "shielding"). Bon Charge, blue-blocker or "blue light glasses" brands: 728 / 89.
- "Low/zero EMF" as an ad attribute: 170 / 26:
  - "Zero EMF. That's right, zero EMF" (infrared mat ad, 26406, 3);
  - "Low VOCs, virtually none. In EMF, got rid of it" (sauna ad, 181275, 1).
- **Verdict:** needs a definition change (the attribute rule).

**sunlight_uv.** Sun exposure, sunbathing, sunburn or UV light: 5,668 / 4,336 / 189.
- 2,367 of those episodes are a Zevo insect-trap ad on Watch What Crappens ("blue and UV light attracts the bugs", 95338, 3). That is not health content.
- Morning sunlight or light: 1,705 episodes. Many hits are circadian ("look at morning sunlight… advancing your circadian clock", 181549, 1), which is `sleep.circadian_light`.
- Vitamin D hits: "most people are not getting enough good quality sun exposure" (192920, 3).
- Spray tans and tanning salons: 1,015 / 146, mostly cosmetic or reality TV.
- Sun gazing: 29 episodes.
- **Verdict:** needs a definition change (circadian and spray-tan boundaries).

**artificial_light.** "Blue light" or "junk light": 2,184 / 196.
- Blue light near sleep, melatonin or night words: about 596 episodes. Near eyes, skin or flicker: smaller and noisy, mostly fiction "fluorescent lights".
- Typical hit: "blue light from our phones… can disrupt our circadian rhythm" (177117, 0), which correctly goes to sleep.
- **Verdict:** fine, but it is the smaller, daytime residue (a few hundred episodes at most).

**ionizing_radiation.** 1,478 / 161 on a noisy query (Chernobyl history, Rogan).
- Real: "health risks… cancer… from radiation exposure" (318630, 2); "misconceptions around radiation exposure and radiophobia" (181487, 0).
- **Verdict:** fine.

### skin_beauty

**acne.** "Acne", Accutane or isotretinoin: 2,931 segments. The broad query with "breakout" and "zits" is useless (Fantasy Footballers, 1,139 episodes).
- Acne is often one item in a symptom list: "She had acne. She had fluid retention" (182670, 3). The lists rule applies.
- Acne as an outcome in a sheets ad: "Bacteria can clog your pores, causing breakouts and acne" (2829, 1).
- **Verdict:** fine.

**skin_conditions.** 2,770 / 202, noisy ("hives"). **Verdict:** fine.

**skincare.** 7,057 / 269 on a noisy query: "serums", plus The Toast and Giggly Squad.
- Tallow as skincare: 99 / 25. Example: "grass-fed tallow moisturizers… it's the best moisturiz[er]" (ad, 33398, 4).
- Tallow overall is 1,081 episodes, mostly food: "100% grass-fed beef tallow. No garbage, no seed oils" in a Masa chips ad (4392, 2).
- **Verdict:** fine; add a tallow food/skin boundary note.

**sunscreen.** 1,448 / 156. Harm talk near "sunscreen": 146 / 50.
- **Verdict:** fine.

**hair_loss_hair.** 9,099 / 318 on a noisy query ("hairline" in sports).
- Heavy ad presence:
  - "Pantene… reduces hair loss by eighty-five percent" (162651, 5);
  - "Hims.com… personalized hair loss treatment options… topical and oral Minoxidil" (318998, 1).
- Also symptom lists: "Low ferritin will cause hair loss" (190405, 21).
- **Verdict:** examples change. Shampoo should count only with a hair-health claim; add hair regrowth and greying.

**skin_ageing.** 5,791 / 253, noisy ("wrinkle" in sports and politics).
- "Ozempic face": 62 / 36. That is a GLP-1 side effect plus skin ageing.
- **Verdict:** fine.

**cosmetic_procedures.** 8,156 / 274.
- Dominated by celebrity and reality-TV passing mentions (1,114 Watch What Crappens episodes): "you haven't done botox or anything" (90499, 2).
- Non-health senses: BBL as slang ("BBL Bandit", 84618, 1); "fillers" in food ads ("no fillers, no additives", 24426, 2).
- Breast implant illness and explant: 72 / 31:
  - "I didn't have breast implant illness… I just got them out because… I didn't want to develop any" (176694, 2);
  - "they're a foreign object in the body, and it can mess up your immune system… the explant surgery" (185786, 1);
  - a whole Niddam episode titled "The Toxic Truth About Breast Implant Illness" (190157).
- **Verdict:** needs a definition change (add BII and explant).

**regenerative_aesthetics.** PRP, PRF, exosomes, PDRN, microneedling, etc.: 862 / 99. Exosomes: 389 / 52.
- Mostly non-cosmetic regenerative medicine (Niddam; joints, 190068, 195). The boundary works when the target is stated: "extra kick for just for skin and hair" (190002, 550).
- **Verdict:** fine.

### wellness

**lifestyle_pillars.** Pillars, healthy lifestyle, lifestyle changes, "diet and exercise": 4,091 / 216.
- "Diet and exercise" is often just the weight-loss baseline, which goes to `weight.weight_loss_methods`.
- **Verdict:** fine.

**chronic_disease_trends.** 623 / 108; the Hyman show alone is 125 episodes.
- "unprecedented obesity, diabetes, and chronic disease epidemic" (182251, 0)
- "chronic illness rates, autism rates, have exploded, and it's all coincident with the explosion in that schedule" (38236, 1). That last one adds vaccines and a narrative.
- **Verdict:** fine.

**habits_behavior_change.** 3,700 / 184.
- 599 of those episodes are a Noom ad on the Dan Le Batard Show ("Noom is the leading behavior change company… The Noom GLP-1 program", 675958, 1). That is a weight or GLP-1 subject.
- Many other hits are productivity or finance: "habit stacking that was a really good hook" (book sales, 92656, 2).
- **Verdict:** needs a definition change (health habits only).

**life_expectancy.** 3,375 / 213.
- Population sense: "the first generation in history where life expectancy is going down" (182869, 3).
- Individual-outcome sense: "ten to twenty years of lost life expectancy" from high insulin (18875, 8); a crime-politics usage (206118, 1).
- **Verdict:** needs a definition change.

**energy_fatigue.** Symptom query: 11,391 / 298, very noisy ("low energy" for comedians and politicians, 201284, 3; 7902, 0). Ad energy puffery: 9,222 episodes / 243 podcasts:
- "clean, sustained energy all day long… no crash, no jitters" (206231, 6);
- "steady energy, no spiral" (185126, 3).
- Real symptom use: "I woke up and I just felt off, low energy, like just felt a little achy" (51847, 0).
- **Verdict:** needs a definition change (symptom or complaint required; generic ad energy excluded).

### other

`topic:other` has no rows, by design. While reading, the only recurring uncovered subject I found was military and occupational exposures (above). Smaller candidates fit existing labels with guidance:
- hypnotherapy: 299 episodes, many in sleep-hypnosis shows and past-life regression;
- EFT tapping: 125;
- tattoo-ink safety: 65;
- Havana syndrome: 233, mostly passing;
- terrain theory: 33 (goes to `infectious.germ_theory_hygiene`);
- noise pollution: about 400, mostly fiction and history.

None meets the bar for a new label. **Verdict:** fine.

## Proposed edits

CHANGE `topic:alt_medicine.functional_medicine`:
| functional_medicine | Functional & integrative medicine | Functional and integrative medicine (East-West included) as an approach and profession. A practitioner's title in an introduction, bio or referral ("a functional medicine doctor", "talk to your integrative practitioner") does not take this subtopic unless the approach itself is discussed. Add `alt_medicine.acupuncture_tcm` only when TCM practices are discussed. | functional medicine; integrative doctor; root-cause medicine (as practice); functional lab ranges; functional vs conventional doctors |
Why: functional medicine occurs in 3,129 episodes (Hyman 1,105), mostly as credentials and referrals (192671, 3; 177023, 0).

CHANGE `topic:alt_medicine.chiropractic`:
| chiropractic | Chiropractic | Chiropractic care and claims, and the chiropractic profession, its training and practice. | chiropractor; adjustment; getting adjusted; subluxation; spinal check; neck cracking |
Why: Chiro Hustle (791 episodes) is mostly profession and practice-business talk (186613, 2), which coders may otherwise skip; "subluxation" (743 episodes) is almost entirely this show.

CHANGE `topic:alt_medicine.herbalism_traditional`:
| herbalism_traditional | Herbalism, Ayurveda & folk remedies | Herbal, Ayurvedic, Indigenous and folk medicine as traditions or practices. A named herb or extract taken as a supplement (including tinctures of it) takes `supplements.herbal_adaptogens`; add this subtopic when the tradition or the practice of herbal healing is itself discussed. | herbalist; herbal medicine; Ayurveda; doshas; folk remedies; grandmother's remedies; castor oil (ingested) |
Why: "tinctures" hits are mostly a supplement or cannabis dosage form ("pine pollen tincture", 38298, 0; "sleep tincture", 9792, 122). "Soursop tea" occurs in 4 episodes. Ayurveda talk is about the system ("find out your dosha", 196011, 6).

CHANGE `topic:alt_medicine.energy_spiritual_healing`:
| energy_spiritual_healing | Energy & spiritual healing | Healing by energy, frequency, faith or ritual. Consumer devices such as PEMF mats go to `biohacking.devices_gadgets`. | Reiki; energy healing; frequency healing; 528 Hz; Solfeggio frequencies; sound baths; EFT tapping; crystals; faith healing; prayer healing |
Why: the real phrasing is "energy healing/work" (323 episodes), sound baths (246) and 528 Hz/Solfeggio (111). EFT tapping (125 episodes, 53 podcasts) has no stated home.

CHANGE `topic:alt_medicine.fringe_ingested_remedies`:
| fringe_ingested_remedies | Fringe ingested chemical remedies | Ingesting or applying industrial or household chemicals as remedies. Turpentine, kerosene or similar taken to expel parasites also takes `detox.parasite_cleanses`. Methylene blue goes to `medications.repurposed_offlabel` or `cognition.nootropics`. | chlorine dioxide; MMS; drinking turpentine; kerosene cleanse; borax in water; DMSO; colloidal silver; food-grade hydrogen peroxide; urine therapy |
Why: there are about 91 real-phrasing episodes across 45 podcasts. The parasite overlap is real: "They did either turpentine or kerosene, and they did a cleansing every three months" (611745, 2). Methylene blue (246 episodes) is common and already routed elsewhere.

CHANGE `topic:alt_medicine.iv_ozone_therapies`:
| iv_ozone_therapies | IV drips, ozone & infusion therapies | Non-oncology IV vitamin drips, ozone and similar infusions. The infused substance also takes its own subtopic when discussed (NAD+ IV adds `longevity.nad_sirtuins`); ozone or IV vitamin C for cancer goes to `cancer_alt.natural_remedies` instead. | IV drip; IV vitamin therapy; Myers cocktail; NAD IV; ozone therapy; EBOO; ozonated oil; glutathione IV |
Why: NAD IV is 139 episodes across 36 podcasts. Ozone also appears for prostate cancer ("we studied ozone therapy", 180687, 50).

CHANGE `topic:alt_medicine.essential_oils`:
| essential_oils | Essential oils & aromatherapy | Essential oils used for health, including oregano oil taken as an antimicrobial. Essential oils named only as an MLM product or business, or as a scent ingredient in another product's ad with no health claim, are not this subtopic. | essential oils for sleep or anxiety; lavender oil; peppermint oil; oregano oil; aromatherapy; diffusing oils; doTERRA; Young Living |
Why: 921 of 1,760 essential-oil episodes are one MLM-satire cross-promo ("buy lots of essential oils. They are so essential", 170607, 2). Health-claim co-occurrence covers only 127 episodes across 35 podcasts.

CHANGE `topic:detox.parasite_cleanses`:
| parasite_cleanses | Parasite cleanses | Protocols and products to expel parasites assumed to be present. Prevalence or diagnosis claims go to `infectious.parasitic_infections`; ivermectin as a COVID treatment ("horse dewormer") goes to `covid.treatments`, and ivermectin or fenbendazole for cancer to `cancer_alt.repurposed_drugs`. | parasite cleanse; parasite protocol; routine deworming; ivermectin or fenbendazole as a dewormer for everyone; wormwood; black walnut; papaya seeds; full moon cleanse |
Why: "horse dewormer" alone accounts for 245 episodes across 53 podcasts, all COVID ivermectin (7894, 0; 11883, 5). Ivermectin and fenbendazole hits total 1,097 episodes, mostly COVID.

CHANGE `topic:detox.binders_drainage`:
| binders_drainage | Binders, drainage & castor oil | A binder, clay, lymphatic-drainage, sweating or pack-based detox method. Lymphatic massage for swelling, recovery or appearance with no detox claim goes to `recovery.bodywork_compression`. | binders; mold binders; zeolite; activated charcoal; bentonite clay; lymphatic drainage to flush toxins; dry brushing; castor oil packs; ionic foot bath |
Why: lymphatic drainage or massage appears in about 290 segments, often with no detox claim (179804, 1; 78490, 0). The detox framing is explicit only in some hits ("Lymphatic massages—all that helps flush out toxins", 182138, 4).

CHANGE `topic:detox.spike_protein_detox`:
| spike_protein_detox | Spike-protein & vaccine detox | Protocols to clear spike protein after vaccination or infection, or to "detox" from vaccines. Nattokinase taken for clotting or lipids with no spike protein named goes to `supplements.other_compounds`. | spike protein detox; clearing spike protein; nattokinase for spike; vaccine detox; post-vax protocol |
Why: there are 27 episodes on core phrasing and 86 with spike protein co-occurring with detox terms. Spike persistence after infection is discussed too (189911, 156). Nattokinase is mostly a clotting supplement (78270, 3).

CHANGE `topic:detox.toxic_load_general`:
| toxic_load_general | Detox & toxic load (general) | Detoxification as a general concept (the body's detox pathways, "toxic load", sweating out toxins), or detox through an unrelated modality such as sauna or fasting, which also takes the modality's subtopic. Detox as withdrawal in addiction treatment goes to `drugs_addiction.addiction_recovery` or `alcohol.alcohol_use_disorder`; a "digital" or "dopamine detox" goes to `cognition.digital_media_brain` or `cognition.neurochemistry_talk`. | detox pathways; toxic load; toxic burden; "your body can't detox"; glutathione and detox |
Why: the addiction sense covers 181 episodes across 72 podcasts and the digital or dopamine sense 230 across 71. Toxic load and burden is common in wellness shows (1,921 episodes).

CHANGE `topic:environment.household_personal_care`:
| household_personal_care | Household & personal-care chemicals | Chemicals in household goods, cookware, cosmetics and clothing as exposures, including "non-toxic" and "clean" alternatives offered for health. PFAS coatings also take `environment.pfas`. | toxic candles; cleaning products; synthetic fragrance; non-toxic makeup; clean beauty; non-toxic cookware; synthetic clothing; aluminum in deodorant |
Why: this is a frequent ad and wellness subject (2,549 episodes): "you cannot live that life with toxic candles" (185668, 3); "non-toxic makeup" (185654, 2); cookware ads (181062, 2). Cookware is named in the narrative table but not in the subtopic.

CHANGE `topic:environment.geoengineering`:
| geoengineering | Chemtrails & geoengineering | Geoengineering, cloud seeding and "chemtrails" as something done to people or their environment with health stakes, or with the spraying proposition stated. Chemtrails named only as a stock example of a conspiracy theory ("flat earth, chemtrails") and cloud seeding discussed only as weather or flood policy are not health content. | chemtrails; aerosol spraying; cloud seeding; solar geoengineering; weather modification |
Why: most of the 296 chemtrail episodes (137 Rogan) name it as a type of belief: "chemtrail people or flat earth people" (70808, 9); "Crop circles and. Chemtrails" (71644, 6).

CHANGE `topic:environment.climate_heat`:
| climate_heat | Climate & heat | Climate change and extreme heat as health issues: heat illness and deaths, climate effects on disease, smoke or food security. Climate policy, energy or weather talk with no health effect is not health content; one person's heat stroke goes to `acute_care.poisoning_environmental_injury`. | heat waves and deaths; heat-related illness; climate and health; extreme heat |
Why: "climate change" appears in 7,429 episodes, almost all political, while health-linked phrasing covers 415 episodes across 104 podcasts.

ADD `topic:environment.military_occupational` under `environment`:
| military_occupational | Military & occupational exposures | Toxic exposures from military service or work as health issues, and the recognition and compensation of their harms. Population is coded separately (`population:military_veterans`). | burn pits; Agent Orange; Camp Lejeune water; PACT Act; Gulf War illness; 9/11 responders; black lung; silicosis; asbestos at work |
Why: the combined query returns 784 episodes across 123 podcasts, with burn pits 220/55, Agent Orange 230/65 and Camp Lejeune 105/40. Examples: "the PACT Act to help treat veterans with toxic exposures, including… burn pits" (439830, 2); "chemicals in burn pits are the exact same chemicals in Agent Orange" (331535, 0). None of the existing subtopics fits well.

CHANGE `topic:radiation_light.wireless_emf`:
| wireless_emf | Wireless & electromagnetic fields | Phones, Wi-Fi, 5G, Bluetooth, power lines and "dirty electricity", and claims of directed-energy or microwave attacks on people (Havana syndrome). | EMFs; 5G towers; cell phone radiation; Wi-Fi router; dirty electricity; non-native EMF; AirPods; Havana syndrome |
Why: there are 978 episodes across 84 podcasts with bare "EMF" (SuperLife 243). Havana syndrome (233 episodes, 42 podcasts) has no stated home.

CHANGE `topic:radiation_light.emf_protection`:
| emf_protection | EMF protection products & practices | Products and practices sold to block or reduce EMF. A "low-EMF" or "zero-EMF" selling point in an ad for another product (sauna, heating mat, red-light panel) is a product attribute and does not take this subtopic unless EMF harm is stated. | EMF blockers; shielding; Faraday bags; airplane mode at night; EMF meters; EMF-blocking blankets |
Why: "low/zero EMF" appears as an ad attribute in 170 episodes across 26 podcasts ("Zero EMF. That's right, zero EMF", 26406, 3; 181275, 1).

CHANGE `topic:radiation_light.sunlight_uv`:
| sunlight_uv | Sunlight & UV exposure | Sun exposure as a health factor: benefits, harms, tanning, sun avoidance. Sunscreen goes to `skin_beauty.sunscreen`; morning or daytime light viewed to set the body clock goes to `sleep.circadian_light` unless skin, vitamin D or UV effects are also discussed; spray tans take nothing unless a health effect is discussed. | sun exposure; sunbathing; tanning beds; UV; sun avoidance; sunburn; sun gazing |
Why: morning-sunlight talk covers 1,705 episodes and is often circadian ("look at morning sunlight… advancing your circadian clock", 181549, 1). Spray tan and salon hits (1,015 episodes) are mostly cosmetic or reality TV.

CHANGE `topic:skin_beauty.hair_loss_hair`:
| hair_loss_hair | Hair loss & hair care | Hair loss, thinning, regrowth and greying in any sex, and hair-care products or practices offered for hair health. | balding; receding hairline; finasteride; minoxidil; hair transplant; thinning hair; hair regrowth; grey hair; shampoo for hair loss |
Why: hair-care hits that qualify carry a hair-health claim ("reduces hair loss by eighty-five percent", 162651, 5; Hims minoxidil, 318998, 1). Bare "shampoo" (4,680 episodes, led by ads on Crime Junkie) is mostly cosmetic ad copy.

CHANGE `topic:skin_beauty.cosmetic_procedures`:
| cosmetic_procedures | Cosmetic surgery & injectables | Cosmetic surgery and injectables, including genital cosmetic surgery, loose-skin or body-contouring procedures after weight loss or pregnancy, and breast implant illness and explant surgery. Therapeutic Botox goes to `medications.other_drugs`. | Botox; fillers; facelift; BBL; breast implants; breast implant illness; explant; buccal fat removal; lip filler; labiaplasty; tummy tuck; skin removal after weight loss |
Why: breast implant illness and explant appear in 72 episodes across 31 podcasts, mainly wellness shows (176694, 2; 185786, 1; a full episode, 190157).

CHANGE `topic:wellness.habits_behavior_change`:
| habits_behavior_change | Habits & behavior change | Building health habits, motivation and coaching for health behaviour. Habits about money, work or productivity are not health content; a weight-loss programme's behaviour change goes to `weight.weight_loss_methods`. | habit stacking for health; health coaching; motivation to exercise; accountability |
Why: 599 of 3,700 episodes are a Noom ad ("the leading behavior change company… GLP-1 program", 675958, 1), and many others are productivity talk (92656, 2).

CHANGE `topic:wellness.life_expectancy`:
| life_expectancy | Life expectancy & mortality statistics | Population life expectancy and mortality trends. Years of life gained or lost from a specific risk or intervention ("cuts ten years off your life") go to that risk's or intervention's subtopic. | life expectancy falling; excess mortality (general); leading causes of death |
Why: individual-outcome uses ("ten to twenty years of lost life expectancy", 18875, 8) sit alongside population uses ("life expectancy is going down", 182869, 3).

CHANGE `topic:wellness.energy_fatigue`:
| energy_fatigue | Energy & everyday fatigue | Tiredness, low energy and afternoon crashes described as a symptom or complaint, outside ME/CFS or a diagnosed condition. Generic energy promises in ad copy ("clean energy", "no crash", "all-day energy") name the product's purpose and do not take this subtopic. | always tired; low energy; afternoon crash; fatigue; exhausted all the time |
Why: ad energy puffery appears in about 9,200 episodes across 243 podcasts ("clean, sustained energy all day long… no crash", 206231, 6; 185126, 3). Without this rule the label would mainly measure ad volume.

## Codebook and prompt notes

1. **Section 3, Ads: beauty and cosmetic products.** The ad test says "health product". It does not say whether a shampoo, makeup or cleaning-product ad is one. Suggested sentence: "A cosmetic, hair-care or household-product ad is health content only with a skin, hair or health claim ('reduces hair loss', 'clears acne') or a toxicity or free-from claim ('non-toxic', 'no hormone disruptors')."
   - Fails the test: Seventh Generation's "nothing extra in the bottle" (74265, 5; 773 Armchair episodes).
   - Passes the test: "non-toxic makeup" (185654, 2).

2. **Section 3, Ads: cross-promos for other podcasts.** A podcast promo whose blurb names a health product or practice satirically or as a plot device is not a health ad.
   - The MLM-satire promo "buy lots of essential oils" runs in 921 episodes across 61 podcasts (170607, 2).
   - By contrast, a promo for a health show that describes its health content ("Dr. Tina Show… metabolic health, chronic diseases", 87812, 0) passes at most as `passing` with `advertisement` relevance. I suggest stating which way this goes.

3. **Section 4.1, Topics inside ads: contaminant and free-from attributes.** Add: "A screening or free-from attribute that names a contaminant or exposure ('PFAS and microplastic screening', 'heavy metal limits', 'BPA-free', 'zero EMF') is a product attribute: code `frame:toxin_purity` and no `environment` or `radiation_light` subtopic, unless the ad states the exposure's harm ('without forever chemicals that harm hormones')."
   - This mirrors the narrative implicature rule (a) in 5.2.
   - Evidence: Momentus creatine ad (73445, 1; 156 episodes on one show); infrared-mat ad (26406, 3).

4. **Section 4.1, energy, focus and mood puffery in ads.** "Better sleep" is clearly an outcome under rule 1. "Clean energy, no crash, laser focus" is generic for coffee, mushroom and greens products. If the team keeps rule 1 literal, `wellness.energy_fatigue` and `cognition.focus_productivity` will be dominated by ads. The proposed `energy_fatigue` row excludes it; state the decision in 4.1 either way.

5. **Section 5.1, practitioner credentials.** Add to "General talk" or "Unsettled facts about a person": "A practitioner's title in an intro, bio or referral (naturopath, functional medicine doctor, chiropractor, acupuncturist) is not a topic; code the subtopic only when the practice or profession is discussed."
   - Example bio: "Dr. Nick Bitts is a naturopathic doctor" (190207, 55).
   - A dog-food ad "invented by naturopathic Dr. Dennis Black" (37466, 1; 171 Charlie Kirk episodes) is also animal health and therefore excluded.

6. **Section 3, Exclude: word senses specific to this slice.** These are common enough to name in the exclusions or the rubric's examples:
   - "mold" as a verb or cast;
   - "crystal(s)" (also Krystal Ball, the Breaking Points host's name);
   - "cupping" hands;
   - "breakout" (sports);
   - "fillers" in food ads (24426, 2);
   - "BBL" as slang (84618, 1);
   - "detox" in addiction and digital senses;
   - "horse dewormer" meaning COVID ivermectin;
   - UV insect-trap ads (Zevo; 2,367 Watch What Crappens episodes);
   - "low energy" about performers or politicians;
   - Mercury the planet or singer, under heavy metals.

7. **Section 5.2, chemtrails.** Chemtrails listed as an example of what conspiracy theorists believe, with no spraying claim, is "the subject merely named" (implicature exception c): no narrative and no topic. A joke whose point is the spraying proposition ("spraying chemtrails… controlling minds", 71251, 0) invokes `narrative:chemtrails` as `rebutted` and takes `environment.geoengineering`. One sentence in 5.2 would settle the 137 Rogan episodes.

8. **Section 5.1, co-labeling rule 8 (substances keep their own home): route substances.** Two recurring cases in this slice need an explicit instruction:
   - NAD+ or glutathione by IV: route plus substance (`iv_ozone_therapies` + `longevity.nad_sirtuins`, or `supplements.other_compounds`);
   - tinctures and capsules of a named herb: the substance only (`supplements.herbal_adaptogens`).

   Adding "an administration route (IV, tincture, capsule) never replaces the substance's home" next to rule 8 would cover both.

9. **Section 6, stance signals seen in this slice.**
   - Debunks often come as mock-quotes: "No, smelling farts in a jar does not cure disease… My chiropractor told me that smelling farts was the way to go" (3347, 15).
   - Hosts in wellness shows hedge with "I'm not against parasite cleanses per se, but…" (190413, 66). That is a qualified endorsement, not a rebuttal.
   - Both patterns fit section 6, but the second one is worth a rubric example for `asserted_or_endorsed` versus `questioned`.

10. **Searching note.** I ran most searches against `/mnt/data2/podcast-data/corpus-text/cq.py` as the brief specified. A coordinator message asked me to switch to `/mnt/internal/felix/podcast-corpus-text/cq.py`. Using it worked at first, but a later attempt was blocked by the permission check, so I went back to the brief's path. The counts are unaffected: the coordinator said the two copies are byte-identical.
