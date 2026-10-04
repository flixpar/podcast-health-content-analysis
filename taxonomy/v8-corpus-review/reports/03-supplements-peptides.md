# Supplements and peptides (`topic:supplements`, `topic:peptides`): corpus review

Counts come from `cq.py count` (segments / episodes / podcasts), out of about 145,600 episodes. Regexes are case-insensitive. Where a pattern also caught unrelated words, I say so. Quotes are given as (episode, segment).

## Summary

- **Both parents are very common, and much of the volume is ads.** The bare word "supplement(s)" appears in 17,484 episodes across 273 podcasts. Research-peptide vocabulary appears in 3,532 episodes across 156 podcasts. Supplement ads run all over non-health shows (Charlie Kirk, Ben Shapiro, Megyn Kelly, MeidasTouch, Mindset Mentor, Crime Junkie, Get Sleepy). Most of the hard coding decisions in this slice are about ads, not discussion.
- **Several "substance-home" cases have no rule, and coders will diverge on them.** The biggest are:
  - multi-ingredient formulas such as AG1, Beam Dream (reishi, magnesium, L-theanine, apigenin, melatonin) and StrongCell (NADH, CoQ10, collagen);
  - functional foods with supplement ingredients (mushroom coffee, protein bars with ashwagandha or lion's mane);
  - topical peptide or collagen cosmetics (GHK-Cu creams, OneSkin's "OS-01 peptide");
  - NAD+ supplement ads, which belong to `longevity.nad_sirtuins`;
  - melatonin the body makes, as opposed to melatonin taken as a supplement;
  - prescription desiccated thyroid (NDT);
  - cannabis "functional gummies" that an ad calls "supplements".

  I propose one codebook rule for multi-ingredient products and boundary notes for the rest.
- **`sleep_mood_supplements` is defined by purpose inside a parent that is defined by substance.** Its examples overlap with `protein_powders` (L-theanine, GABA, 5-HTP are amino acids or their derivatives) and `herbal_adaptogens` (valerian, saffron, kava). Under rule 8 a coder could stack three or four labels on one sleep-powder ad. I propose redefining it by substance: melatonin, the neurotransmitter-precursor compounds, and multi-ingredient sleep or calm formulas. Botanicals stay in `herbal_adaptogens`.
- **Most melatonin mentions are not supplements.** About a third of the melatonin samples (2,252 episodes in all) were about melatonin the body makes ("bathing in that darkness to promote sufficient melatonin production"). That belongs to `sleep.circadian_light`. The label needs to say so.
- **Electrolyte products are high-volume and their boundary is unclear.** Electrolyte brands appear in 3,688 episodes (Gatorlyte and Gatorade Zero powders on Get Sleepy, BodyArmor Flash IV on Pardon My Take, LMNT on Huberman). Right now "electrolytes in drinks" goes to `food`, while "electrolyte powder" and LMNT go to supplements, and "Gatorade Zero powders" fits both. I propose following the product form, matching the product_type rule in codebook §8.
- **`industry_quality` will be over-applied in ads.** Most of its trigger phrases occur as selling points ("third-party tested", "NSF certified for sport") or as the regulatory boilerplate in supplement ads ("These statements have not been evaluated by the Food and Drug Administration"). Those are `evidence:strength_assertion` and `frame:disclaimer`, not the industry as a subject. Retailer ads (iHerb) should take the bare parent.
- **Peptides: all four subtopics are findable.** Healing: 609 episodes, 68 podcasts. GH secretagogues: 277, 47. Other named peptides: about 800, 110. Sourcing and regulation: about 490, 65. Bare `topic:peptides` will also be common ("cold plunges, red light masks… peptides" in wellness-trend lists). The parent needs boundaries for collagen peptides, topical and cosmetic peptides, and gray-market "research" GLP-1s such as retatrutide. `other_peptides` needs bioregulators (436 episodes, though 322 are from one show) and the sexual, tanning and fat-loss peptides (PT-141, melanotan, AOD-9604).
- **Peptide sourcing and regulation is a live 2023–2026 policy story** (the FDA compounding list, RFK Jr. "fighting for peptides", "the FDA loosens restrictions on peptides"). It needs a clear boundary with `health_system.dtc_telehealth`, modelled on the existing `glp1.access_compounding` sentence.
- **Two small moves.** Colostrum (heavy ARMRA ad volume) is not herbal, fungal, algal or bee-derived; move it to `organ_glandular`. Prescription desiccated thyroid belongs in `endocrine.thyroid`, not `organ_glandular`.
- **No new subtopics recommended.** Candidates I checked and rejected (absorbed by definition changes instead):
  - functional mushrooms: 1,634 episodes, 130 podcasts; the natural first cut if `herbal_adaptogens` is ever split;
  - IV vitamin drips: 721 episodes, noisy;
  - exogenous ketones: 301 episodes, 35 podcasts;
  - fiber supplements: 402 episodes, 82 podcasts;
  - apple cider vinegar gummies: 725 episodes, 89 podcasts;
  - hangover products (ZBiotics): 749 episodes, 85 podcasts;
  - prenatal vitamins: 127 episodes.

## Label-by-label findings

### Parent `topic:supplements` (generic)
- **Query:** `\bsupplement(s|ing|ation)?\b`. 34,592 / 17,484 / 273. Top shows: Rogan 1,231 episodes, Mindset Mentor 1,009 (nearly all IM8 and iHerb ads), Hyman 975, Charlie Kirk 846 (Balance of Nature ads).
- **Ad shapes seen:**
  - retailer: "iHerb is the one-stop shop for vitamins, supplements, sports nutrition" (189137, 0);
  - all-in-one: "I used to take a handful of different supplements every morning… Since switching to IM8, everything I need is in one simple routine" (189073, 2);
  - general brand: "We Heart Nutrition makes high-quality, research-backed supplements for women and men" (5683, 0);
  - "liver shot": "Dose is a clinically backed supplement that comes as a daily two-ounce shot, helps cleanse your liver" (206206, 4), which takes herbal plus `gut.liver_gallbladder` and `detox`;
  - cannabis: "Forget one-size-fits-all supplements that only get you high. Mood's functional gummies…" (201001, 2), which is cannabis, not supplements.
- **Verdict:** the parent definition needs boundary notes (codebook notes below).

### `supplements.vitamin_d`
- **Query:** `\bvitamin d\b|\bd3\b|vitamin d3`. 7,465 / 4,882 / 175.
- **Verdict:** fine. Status talk ("you're still deficient… with supplementation I get to like 75, 80", 37753, 1) and sunlight ("we need some sunlight in order to make vitamin D", 1057, 3) both fit the existing definition and rule 5.
- **Combination products** such as "vitamin DKE… vitamin D, vitamin A, vitamin K, and a special form of vitamin E" (26219, 27) need the multi-ingredient rule.

### `supplements.magnesium`
- **Query:** `\bmagnesium\b`. 6,791 / 4,351 / 156.
- **Verdict:** fine. Common non-sleep use is constipation ("all I needed was a bit of magnesium", 90981, 3). Magnesium is often one ingredient in sleep powders and electrolyte reads; the multi-ingredient rule handles those.

### `supplements.b_vitamins_methylation`
- **Query:** B12, methylfolate, folate, folic acid, MTHFR, methylated, "b vitamins", "b complex", niacin. 4,565 / 3,015 / 158.
- **Verdict:** examples change (minor). Real talk includes gene panels beyond MTHFR ("a gene mutation called MTR… impaired ability to metabolize… homocysteine", 177177, 2), B12 deficiency ("I was B12 deficient", 190324, 117), and B12 shots or injections. Add homocysteine and B12 injections as examples.

### `supplements.vitamin_c`
- **Query:** `vitamin c\b`. 3,419 / 2,519 / 163.
- **Verdict:** fine. IV vitamin C as a cancer adjunct is already routed out ("Thoughts on IV vitamin C and ozone for adjunct therapies? No good evidence", 175211, 6).

### `supplements.other_vitamins_minerals`
- **Query:** zinc, iodine, selenium, "vitamin a", K2, multivitamin, electrolyte, LMNT, potassium. 16,105 / 10,427 / 238. Top shows include Get Sleepy 689, Meditation for Anxiety 429 and Pardon My Take 421; almost all of these are sports-drink ads.
- **Electrolyte brands:** Liquid I.V., LMNT, Element, Gatorlyte, BodyArmor, DripDrop, Nuun, Pedialyte, "electrolyte powder/packets/mix". 4,052 / 3,688 / 161.
- **Quotes:**
  - "Gator Light with a specialized blend of five electrolytes was scientifically designed to help move fluids into the body faster" (180006, 0);
  - "Gatorade Zero powders have been designed scientifically to help you improve your hydration balance" (203168, 0);
  - "Body Armor Flash IV, with over 2,200 milligrams of electrolytes" (24664, 9).
- **IV nutrient drips:** 837 / 721 / 145, but noisy (hospital IV bags, idioms). Real cases: "I got him an IV vitamin drip" (7870, 19); "if you have like a health clinic and you have an IV lounge" (174947, 7). A generic "vitamin drip" with no single nutrient has no home today.
- **Verdict:** definition change. Split electrolyte products by form, to match codebook §8. Name IV multi-nutrient drips.

### `supplements.omega3`
- **Query:** fish oil, omega-3, krill oil, EPA, DHA. 7,934 / 5,336 / 209. The `\bepa\b` alternative also catches the agency (MeidasTouch 212 episodes), which matters only for keyword counts.
- **Verdict:** small definition change. Omega-3 also comes up as a dietary-fat ratio in seed-oil talk ("they looked at combinations of omega-6 and omega-3", 182365, 3). That belongs to `food.fats_oils` unless a supplement or the person's status is meant.

### `supplements.creatine`
- **Query:** `\bcreatine\b`. 4,450 / 2,678 / 125. Creating Confidence (238 episodes) and Habits and Hustle are Momentous ad reads; Tucker is a Beam "American Strength Bundle" read.
- **Verdict:** fine. Ad copy is the usual "one of the most researched and effective supplements" (73596, 2) and "an absolute must for both men and women who want peak physical and cognitive performance" (14707, 0).

### `supplements.protein_powders`
- **Query:** protein powder, whey, collagen, BCAA, EAA, essential amino, glycine, tyrosine, taurine. 8,231 / 5,026 / 186.
- **Quotes:**
  - collagen ad: "collagen is a proven way to promote youthful health and appearance" (5876, 0);
  - contamination: "Nearly half of the top-selling proteins in the U.S. tested high for lead" (178163, 1).
- **Verdict:** small definition change. Topical collagen (creams) goes to `skin_beauty.skincare`. "Collagen peptides" stay here, not under `peptides`. Add HMB and glutamine, both seen in reads: "HMB to reduce protein breakdown" (63109, 9); "just doing creatine and glutamine" (51827, 4).

### `supplements.greens_whole_food`
- **Queries:** AG1, Athletic Greens, greens powder, Balance of Nature, super greens, Bloom: 3,679 / 3,198 / 112. All-in-one and superfood brands (IM8, Field of Greens, Ka'Chava, Organifi, Huel, "superfood powder/blend"): 1,797 / 1,483 / 74.
- **Real copy:**
  - "Just one scoop combines your multivitamin, pre and probiotics, superfoods, and antioxidants" (1321, 9);
  - "This new generation of AG1 can help fill the nutrient gaps your diet might miss… It's not a miracle" (709, 2);
  - "a superfood powder that gets me real fruits and veggies selected by doctors to help my heart, lungs, metabolism" (25079, 0);
  - "Katchava is an all-in-one plant based super blend made up of superfoods, greens, plant proteins, antioxidants, adaptogens, and probiotics" (194639, 1);
  - "Balance of Nature receives over a thousand success stories every single month" (38289, 0).
- **Verdict:** definition change. The label has become the home of all-in-one daily nutrition drinks, which list vitamins, probiotics, adaptogens, protein and even creatine (AG1 Pro). Say that such a product takes this label alone unless a separate claim is made about one ingredient.

### `supplements.herbal_adaptogens`
- **Query:** 22 botanical, fungal and bee terms. 7,431 / 4,701 / 196. Functional mushrooms alone: 1,995 / 1,634 / 130 (Mayim Bialik's Breakdown 252, Shawn Ryan 155, MeidasTouch 122: MUD\WTR and Ryze ad reads).
- **Quotes:**
  - "Mud Water provides the same morning ritual, but with functional mushrooms and adaptogens instead of that full caffeine hit" (185554, 3);
  - "a jitter-free instant coffee packed with two hundred milligrams of natural caffeine, mood-boosting magnesium, and productivity-enhancing lion's mane" (599000, 6);
  - testosterone herbs: "natural ingredients that support healthy T levels… every batch is third-party tested" (63750, 4).
- **Apple cider vinegar:** 877 / 725 / 89. Mostly Bubs gummy reads ("Bubs Naturals Apple Cider Vinegar Gummies… helps with energy, healthy digestion, your immune system, and your metabolism", 15611, 5) and Jockers recommendations as food.
- **Verdict:** definition change.
  - Remove colostrum: it is bovine, not botanical, fungal, algal or bee-derived.
  - Add tongkat ali, fadogia, maca, ACV gummies, milk thistle and digestive bitters as examples.
  - Add the fortified-food boundary (mushroom coffee).
  - State that psilocybin "mushrooms" go to `psychoactives`.
- **Split considered:** functional mushrooms meet the frequency bar. I do not recommend a split now, because the subject is not distinct in misinformation terms.

### `supplements.organ_glandular`
- **Query:** organ capsules, desiccated, glandulars, Heart & Soil, Ancestral Supplements, bovine organs, plus colostrum and ARMRA. 1,648 / 1,172 / 85.
- **Quotes:**
  - "Paleo Valley Grass Fed Organ Complex… freeze dried blend of liver, heart, and kidney" (185720, 5);
  - "ARMRA Colostrum… strengthen my gut barrier, protecting against toxins" (20890, 3).
- **Desiccated thyroid:** the Thyroid Fixer podcast's "desiccated" hits are mostly prescription thyroid hormone ("any kind of natural desiccated thyroid, NDT, it's roughly 80% T4, 20% T3", 190935, 64). That is `endocrine.thyroid`.
- **Verdict:** definition change. Broaden to animal-derived supplements (add colostrum) and route NDT out.

### `supplements.other_compounds`
- **Query:** glutathione, NAC, CoQ10, ubiquinol, ALA, PQQ, quercetin, phosphatidyl-, urolithin, Mitopure, carnitine, enzymes, serrapeptase, nattokinase, astaxanthin, sulforaphane, spermidine, fisetin, PEA, methylene blue. 8,515 / 5,086 / 206. The `\bpea\b` alternative also catches "pea protein".
- **Charlie Kirk (432 episodes) is mostly StrongCell reads:** "StrongCell is a liquid NADH supplement packed with highly bioavailable CoQ10, marine collagen, and tons of essential vitamins" (38815, 1); "fact-check me on this. Go do your own research on NADH" (38106, 2).
- **NAD+ ads** use the same pattern: "Qualia NAD+… between age 20 and 50, your NAD+ levels are cut in half" (13310, 4). By the table, NAD belongs in `longevity.nad_sirtuins`, but a coder looking under supplements will not find it.
- **Exogenous ketones:** 586 / 301 / 35. No home today.
- **Verdict:** definition change. Add exogenous ketones and PEA, and add an explicit pointer that NAD+, NADH, NMN and NR go to `longevity.nad_sirtuins`.

### `supplements.sleep_mood_supplements`
- **Queries:** melatonin: 3,981 / 2,252 / 154. Other calm and sleep compounds (L-theanine, GABA, 5-HTP, valerian, kava, apigenin, inositol, saffron extract, "sleep supplement/gummies/formula/aid"): 3,134 / 2,115 / 180.
- **Melatonin samples (n=20):** about 7 were melatonin made by the body or affected by light, for example "light that hits your skin will start to wash melatonin away" (190799, 100) and "bathing in that darkness to promote sufficient melatonin production" (190691, 67). Others were non-oral products: "an evening mouthwash, which is infused with melatonin" (89699, 2) and a melatonin hair serum (190116, 484).
- **Typical sleep ad, a multi-ingredient powder:** "Dream contains a powerful, all-natural blend of reishi, magnesium, L-theanine, apigenin, and melatonin to help you fall asleep" (168594, 0). THC "extra strength sleep gummies" (63524, 5) are cannabis.
- **Verdict:** definition change. Define the label by substance (melatonin, calming neurotransmitter precursors, multi-ingredient sleep or calm formulas). Botanicals stay in `herbal_adaptogens`. The body's own melatonin goes to `sleep.circadian_light` or `endocrine.other_hormones`.

### `supplements.industry_quality`
- **Query:** supplement industry/companies/regulation, "(not) regulated", DSHEA, third-party tested, proprietary blend, "not been evaluated by the FDA", NSF certified, Informed Sport, "expensive pee", heavy metals in protein. 4,062 / 3,496 / 150. Top is Mindset Mentor with 462 episodes, all IM8 boilerplate.
- **In 14 samples, about 10 were ad selling points or boilerplate:**
  - "every batch is third-party tested" (63750, 4);
  - "NSF certified for sports, so you know exactly what's in it" (63109, 9);
  - "These statements have not been evaluated by the Food and Drug Administration. This product is not intended to diagnose, treat, cure, or prevent any disease" (189244, 1);
  - "not just another supplement company. They are proudly pro-life" (5927, 5).
- **Genuine subject matter is rarer:**
  - "The supplement industry is truly the wild west. It's unregulated and it's filled with hype and marketing" (176654, 4);
  - "65% of chocolate protein powders tested above legal limits for lead" (190056, 16);
  - "His came from a contaminated supplement" (doping case, 20511, 6).
- **Verdict:** definition change, restricting the label to the industry or quality as a subject.

### Gaps checked in the supplements parent (no new subtopic)
- **Fiber supplements** (psyllium, Metamucil, Benefiber, inulin): 474 / 402 / 82. Route to `gut.probiotics_fermented` as prebiotic supplements.
- **Prenatal vitamins:** 152 / 127 / 50. These fit `other_vitamins_minerals` plus `population:pregnant_postpartum`.
- **Hangover products** (ZBiotics, DHM, Cheers): 824 / 749 / 85. ZBiotics is an engineered probiotic, so it takes `gut.probiotics_fermented` plus `alcohol.health_effects` as the outcome.
- **Fluoride supplementation** (10899, 0) goes to `oral`.

### Parent `topic:peptides` (generic)
- **Query:** named peptides plus `\bpeptides?\b`. 11,167 / 3,532 / 156. Top shows: LONGEVITY with Nathalie Niddam 462, Mind Pump 364, Hyman 170, Rogan 168, Thyroid Fixer 140, Shawn Ryan 137. Generic "peptide(s)" alone: 10,148 segments.
- **Bare-parent uses are common:**
  - in trend lists: "the cold plunges, the red light masks… the matchas and the peptides and the pilates" (57014, 0);
  - in comedy and sports: "2026 peptides. I'm in favor… Are they still called research chemicals?" (52624, 7);
  - in clinic ads: "hormone optimization, peptide therapy, targeted supplements" (33397, 1).
- **Things the parent catches that are not research peptides:**
  - GLP-1s described as peptides: "trozopatide is a glucagon-like peptide" (190426, 112);
  - topical cosmetic peptides: "skincare… with the OS1 peptide" (80989, 3); "Wisp has dermatologist-backed treatments like GHK-CU topical cream" (156816, 2); "Peptides like GHKCU, which boost collagen production by seventy percent" (Entera ad, 195456, 5);
  - collagen peptides (Bubs ads);
  - science talk about endogenous peptides (humanin, 182192, 4).
- **Verdict:** the parent description needs boundaries (codebook notes).

### `peptides.healing_peptides`
- **Query:** `bpc|tb.?500|tb ?4\b|thymosin beta|thymazin beta|wolverine stack|b p c`. 1,424 / 609 / 68. Top shows: Mind Pump 120, Niddam 111, Rogan 53, Pardon My Take present.
- **ASR forms:** "BPC one fifty seven", "BBC one five seven", "Thymazin beta", "TB-4 Frag", "BPC 157".
- **Quotes:**
  - "they call it the Wolverine stack because it's named after the X-Men" (192532, 4);
  - "people will add on GHK copper and call it the Glow stack" (78428, 11);
  - "Do the letters BPC one fifty seven mean anything to you?… Billy got this for for me for my elbow" (24130, 2).
- **Verdict:** examples change (ASR forms, the "Glow stack"). The definition is fine.

### `peptides.gh_secretagogues`
- **Query:** ipamorelin, CJC, sermorelin, tesamorelin, MK-677, ibutamoren, hexarelin, GHRP, secretagogue. 485 / 277 / 47. Call Her Daddy's 30 episodes are one telehealth ad: "PT 141 for actual desire, and Sermorelin plus NAD plus to fix his recovery, focus" (24859, 5).
- **PED context:** "IGF peptide injections, MK six seven seven, which is like a SARM, HGH" (Liver King, 23585, 4) needs `peds.steroids_sarms` as well.
- **Verdict:** fine. Small examples change (GHRP, hexarelin, "sermorelin plus NAD").

### `peptides.other_peptides`
- **Queries:** melanotan, PT-141, AOD-9604, Semax, Selank, MOTS-c, SS-31, KPV, GHK, copper peptides, thymosin alpha, cerebrolysin, dihexa: 1,868 / 828 / 110. This includes skincare ads (Giggly Squad 49) and "Poughkeepsie" noise (Kill Tony). Bioregulators (Khavinson, pinealon, epitalon/"Epitilon", thymalin, cortexin): 2,064 / 436 / 28, of which 322 are Niddam episodes (she sells them).
- **Quotes:**
  - "Epitilon is a great one to use twice a year for longevity… Thymazin alpha is great for immune function" (190777, 62);
  - "Peptides for Fat Loss w/ CanLab: Setmelanotide, AOD 9604, FRAG17691, Tesamorelin" (episode title, 190366);
  - "a peptide that can be prescribed by a doctor… called pinealine" (9068, 15).
- **Verdict:** definition and examples change. Name bioregulators and the purpose families (sexual, tanning, fat-loss, cognitive, immune). Route topical cosmetic use to `skin_beauty`.

### `peptides.peptide_sourcing_regulation`
- **Query:** research chemicals or peptides, "not for human consumption", gray market, peptide vendors/companies/clinics, "category 2". 682 segments, part noise ("Category Two hurricane", Asprey's "category two people", Pardon My Take jokes). Peptides co-occurring with FDA, RFK, ban, category, compounding, illegal or regulation: 835 / 487 / 65.
- **Quotes:**
  - "These peptide companies started selling their products as research chemicals, not for human consumption, right there on the bottle" (178178, 1);
  - "GLP-1s are peptides. Why were they not on the bulks list that got banned by the FDA? Because they've been patented and monetized by Big Pharma" (175605, 2);
  - "I don't recommend people go out and buy gray market or black market peptides because they're not clean of something called lippie polysaccharide" (9068, 15);
  - "the FDA loosens restrictions on peptides" (89920, 4);
  - "through our partners at MPHormones dot com… I don't want people going online and buying these peptides from research chemical labs" (195889, 5).
- **Gray-market GLP-1s:** retatrutide and "research GLP" give only 53 / 45 / 21, but the passages are about exactly this boundary: "Totally gray market… It's a research chemical… Patented as an obesity [drug]" (195693, 1).
- **Verdict:** definition change. Name the policy story, telehealth and clinic access, purity and endotoxin, and the boundaries with `health_system.dtc_telehealth` and `glp1.access_compounding`.

## Proposed edits

CHANGE `supplements.other_vitamins_minerals`:
| other_vitamins_minerals | Other vitamins, minerals & electrolytes | Any other vitamin or mineral supplement, multivitamins and prenatal vitamins, IV nutrient drips with no single nutrient named, and electrolyte products sold as powders, sticks or tablets. Ready-to-drink sports and hydration drinks go to `food.beverages_hydration`. | zinc; iron; iodine; selenium; vitamin A; vitamin K2; multivitamin; prenatal vitamin; electrolyte powder; LMNT; Liquid I.V.; potassium; IV vitamin drip; Myers cocktail |
Why: electrolyte brands appear in 3,688 episodes across 161 podcasts. The current split ("electrolytes in drinks" to food, "electrolyte powder" here) leaves "Gatorade Zero powders" (203168, 0) and "Gator Light… five electrolytes" (180006, 0) ambiguous. Splitting by form matches codebook §8, where electrolyte drinks are food_or_beverage and powders are supplements. IV drips (7870, 19; 174947, 7) and prenatal vitamins (127 episodes) had no stated home.

CHANGE `supplements.greens_whole_food`:
| greens_whole_food | Greens, superfood & all-in-one powders | Greens and superfood powders, encapsulated fruit-and-vegetable products, and all-in-one daily nutrition drinks and shakes. Such a product takes this label alone even when its read lists vitamins, probiotics, adaptogens, protein or creatine; add an ingredient's own subtopic only when a separate claim is made about that ingredient. A whole-fruit powder taken for one nutrient (camu camu for vitamin C) goes to that nutrient's subtopic. | AG1; Athletic Greens; IM8; greens powder; Balance of Nature; Field of Greens; Ka'Chava; Bloom; superfood blend |
Why: the AG1, Balance of Nature, IM8, Field of Greens and Ka'Chava reads are a single product category: 3,198 episodes plus 1,483 more for the other brands. Their copy always lists ingredient classes ("combines your multivitamin, pre and probiotics, superfoods, and antioxidants", 1321, 9; "superfoods, greens, plant proteins, antioxidants, adaptogens, and probiotics", 194639, 1). Without this sentence, coders will add four or five subtopics per read.

CHANGE `supplements.herbal_adaptogens`:
| herbal_adaptogens | Herbal, fungal, algal & bee supplements | Botanical, fungal, algal and bee-derived supplements, including functional-mushroom products and vinegar gummies. A food or drink sold on a botanical or mushroom ingredient (mushroom coffee, a protein bar with ashwagandha) takes this plus the vehicle's own subtopic. Psilocybin and other psychoactive mushrooms go to `psychoactives`; colostrum goes to `supplements.organ_glandular`. | ashwagandha; turmeric/curcumin; berberine; medicinal mushrooms; lion's mane; mushroom coffee; sea moss; rhodiola; tongkat ali; fadogia; maca; black seed oil; shilajit; spirulina; chlorella; milk thistle; apple cider vinegar gummies; propolis; royal jelly; bee pollen |
Why: herbal terms appear in 4,701 episodes across 196 podcasts, and functional mushrooms alone in 1,634 across 130, mostly MUD\WTR and Ryze reads (185554, 3; 599000, 6). Testosterone herbs (63750, 4) and ACV gummies (725 episodes; 15611, 5) had no listed example. Colostrum is bovine and fits none of the four source groups.

CHANGE `supplements.organ_glandular`:
| organ_glandular | Organ, glandular & colostrum supplements | Desiccated organ and glandular products and other animal-derived supplements such as colostrum. Prescription desiccated thyroid (NDT, Armour) goes to `endocrine.thyroid`. | beef liver capsules; organ complex; desiccated organs; glandulars; Heart & Soil; colostrum; ARMRA |
Why: organ products plus colostrum appear in 1,172 episodes across 85 podcasts. ARMRA colostrum reads are heavy on Shawn Ryan, MeidasTouch, Ben Shapiro and Megyn Kelly ("Armra Colostrum… strengthen my gut barrier", 20890, 3). The Thyroid Fixer's "desiccated" hits are prescription NDT (190935, 64), which a substance-keyword reading would misfile here.

CHANGE `supplements.other_compounds`:
| other_compounds | Other compounds & enzymes | Non-botanical supplement compounds not covered above: antioxidants, phospholipids, enzymes, exogenous ketones and similar. NAD+, NADH, NMN, NR and resveratrol go to `longevity.nad_sirtuins` whatever the purpose. | glutathione; NAC; CoQ10; alpha-lipoic acid; PQQ; quercetin; phosphatidylcholine; urolithin A; L-carnitine; PEA; astaxanthin; sulforaphane; nattokinase; digestive enzymes; serrapeptase; ketone esters; exogenous ketones |
Why: these compounds appear in 5,086 episodes across 206 podcasts. Common ad formulas mix this label with NAD (StrongCell NADH plus CoQ10, 38815, 1; Qualia NAD+, 13310, 4), and coders need to be told where NAD lives. Exogenous ketones (301 episodes, 35 podcasts) had no home.

CHANGE `supplements.sleep_mood_supplements`:
| sleep_mood_supplements | Melatonin & sleep or calm formulas | Melatonin taken as a supplement, calming neurotransmitter-precursor compounds, and multi-ingredient sleep or calm formulas (a formula takes this label alone unless a separate claim is made about one ingredient). Botanicals taken for sleep or mood go to `supplements.herbal_adaptogens`; melatonin the body makes, or light affecting it, goes to `sleep.circadian_light`; THC or CBD sleep products go to `psychoactives.cannabis`. | melatonin gummies; L-theanine; GABA; 5-HTP; apigenin; tryptophan; sleep powder; Beam Dream |
Why: melatonin appears in 2,252 episodes, but about a third of sampled hits were about melatonin the body makes ("bathing in that darkness to promote sufficient melatonin production", 190691, 67). The purpose-based definition conflicts with the parent's "subtopic follows the substance" rule and with `protein_powders` (L-theanine, GABA) and `herbal_adaptogens` (valerian, kava, saffron). Typical reads are multi-ingredient: "reishi, magnesium, L-theanine, apigenin, and melatonin" (168594, 0).

CHANGE `supplements.industry_quality`:
| industry_quality | Supplement industry, quality & regulation | Supplements as a category or industry discussed as a subject: whether they work in general, contamination and testing results, labeling accuracy, regulation (DSHEA, FDA oversight), multi-level marketing. A product's own quality selling points ("third-party tested", "NSF certified") and the standard FDA disclaimer in a read do not take this label. | supplement industry is the wild west; supplements aren't regulated; DSHEA; lead in protein powder; contaminated supplement; proprietary blend; MLM supplements |
Why: the trigger phrases hit 3,496 episodes, but about 10 of 14 samples were ad selling points or boilerplate (63750, 4; 63109, 9; 189244, 1). Those are `evidence:strength_assertion` and `frame:disclaimer`. Genuine cases: "The supplement industry is truly the wild west. It's unregulated" (176654, 4); "Nearly half of the top-selling proteins… tested high for lead" (178163, 1).

CHANGE `supplements.omega3`:
| omega3 | Omega-3 & fish oil | Fish oil, krill oil and omega-3 supplements, and omega-3 status with no form stated. The dietary omega-6 to omega-3 balance in foods and oils goes to `food.fats_oils`. | fish oil; EPA/DHA; krill oil; algae oil; omega-3 index |
Why: seed-oil passages discuss omega-3 as a dietary fat ratio ("combinations of omega-6 and omega-3", 182365, 3). Without a boundary, these get coded as supplements.

CHANGE `supplements.protein_powders`:
| protein_powders | Protein powders, collagen & amino acids | Protein powders, collagen supplements and amino-acid products, including single amino acids taken as supplements. Protein bars go to `food.protein_intake`; collagen applied to the skin goes to `skin_beauty.skincare`; collagen peptides stay here, not under `peptides`. | whey; collagen peptides; BCAAs; EAAs; glycine; L-tyrosine; taurine; glutamine; HMB |
Why: "collagen peptides" (Bubs reads; 8669, 8) is the one place where the word "peptide" in a supplement ad does not mean `topic:peptides`. HMB and glutamine appear in real reads and talk (63109, 9; 51827, 4).

CHANGE `supplements.b_vitamins_methylation`:
| b_vitamins_methylation | B vitamins, folate & methylation | B-vitamin supplements and injections, folate and methylfolate, B-vitamin status, and methylation-driven supplementation including MTHFR and related gene variants and homocysteine. Leucovorin for autism takes this and `neurodevelopment.autism_treatment`. | B12; B12 shots; methylfolate; folic acid; MTHFR; homocysteine; methylated vitamins; leucovorin (as folate) |
Why: methylation talk names other genes and homocysteine ("a gene mutation called MTR… impaired ability to metabolize something called homocysteine", 177177, 2). B12 status and injections are common ("I was B12 deficient", 190324, 117).

CHANGE `peptides.healing_peptides`:
| healing_peptides | Healing & recovery peptides | Peptides used for injury, gut or tissue healing, alone or in named stacks. | BPC-157 ("BPC one fifty seven"); TB-500; thymosin beta-4; TB-4 Frag; Wolverine stack; Glow stack |
Why: 609 episodes across 68 podcasts. ASR renders the names as "BPC one fifty seven", "BBC one five seven" and "Thymazin beta" (24130, 2; 78428, 11; 190777, 62). Stacks are named in speech ("they call it the Wolverine stack", 192532, 4; "call it the Glow stack", 78428, 11).

CHANGE `peptides.gh_secretagogues`:
| gh_secretagogues | Growth-hormone secretagogues | Peptides and compounds taken to raise growth hormone. Growth hormone itself goes to `endocrine.other_hormones`, plus `peds.steroids_sarms` for physique or performance. | ipamorelin; CJC-1295; sermorelin; tesamorelin; GHRP-6; hexarelin; MK-677 (ibutamoren) |
Why: 277 episodes across 47 podcasts. It sits next to HGH in PED passages ("IGF peptide injections, MK six seven seven, which is like a SARM, HGH", 23585, 4) and in telehealth reads ("Sermorelin plus NAD plus", 24859, 5).

CHANGE `peptides.other_peptides`:
| other_peptides | Other peptides | Any other research or therapeutic peptide, including bioregulator peptides and peptides taken for sex, tanning, fat loss, cognition or immunity (code the outcome too). A peptide that only appears as an ingredient in a cosmetic cream or serum goes to `skin_beauty.skincare`. | GHK-Cu (injected or as a compound); MOTS-c; SS-31; thymosin alpha-1; epitalon; pinealon; bioregulators; Semax; Selank; KPV; PT-141; melanotan; AOD-9604 |
Why: these named peptides appear in about 800 episodes across about 110 podcasts, and bioregulators in 436 episodes across 28 podcasts. Real talk is organised by purpose ("Peptides for Fat Loss… AOD 9604", 190366; "PT 141 for actual desire", 24859, 5; "Epitilon… for longevity", 190777, 62). Topical GHK-Cu and "OS1 peptide" skincare ads (156816, 2; 195456, 5; 80989, 3) are skincare, not research-peptide use.

CHANGE `peptides.peptide_sourcing_regulation`:
| peptide_sourcing_regulation | Peptide sourcing & regulation | Where peptides come from and how they are regulated: research-chemical and gray-market vendors, purity and contamination, compounding-pharmacy access and FDA restrictions or their loosening, and clinics and telehealth services selling peptides (which take this alone; add `health_system.dtc_telehealth` only when the telehealth model itself is discussed). Gray-market GLP-1s such as retatrutide take `glp1.access_compounding`, plus this label when the research-chemical market itself is discussed. | research chemicals; "not for human consumption"; "for research use only"; peptides from China; gray market; endotoxin or LPS contamination; FDA category 2 list; compounding ban; FDA loosens peptide rules; peptide clinic |
Why: about 490 episodes across 65 podcasts discuss peptides alongside regulation. The 2023 compounding restrictions and the 2025–26 loosening come up across Mind Pump, Huberman, Biohack-it, Pivot and Modern Wisdom (178178, 1; 175605, 2; 89920, 4). Contamination is a recurring safety argument ("not clean of something called lippie polysaccharide", 9068, 15). `health_system.dtc_telehealth` also claims "compounding pharmacies and their regulation for any drug", so the boundary has to be stated.

## Codebook and prompt notes

1. **§4.1 "Topics inside ads": add a multi-ingredient rule.** Proposed text: "A product made of several substances (an all-in-one powder, a sleep formula, a combination capsule) takes its own category's subtopic once (`greens_whole_food`, `sleep_mood_supplements`). Where it has no category, take the subtopic of the substance it is named or sold on (StrongCell NADH → `longevity.nad_sirtuins`; Vitamin DKE → `supplements.vitamin_d`). Add another ingredient's subtopic only when the read makes a separate claim about that ingredient." Evidence: AG1 (1321, 9), Ka'Chava (194639, 1), Beam Dream (168594, 0), StrongCell (38815, 1), Vitamin DKE (26219, 27). Rule 8's "code both" sentence otherwise invites three to five labels per read.

2. **§5.1, rule 8 (substances keep their own home): list the homes that sit outside `supplements` or `peptides`.** Coders search the supplement table first and miss these. Each line below gives the case and where it goes.
   - NAD+, NADH, NMN, NR: `longevity.nad_sirtuins` (Qualia, StrongCell, Aurora NAD+ reads).
   - Melatonin made by the body, or light affecting it: `sleep.circadian_light`.
   - Prescription desiccated thyroid: `endocrine.thyroid`.
   - THC or CBD "functional gummies" an ad calls supplements: `psychoactives.cannabis` (201001, 2; 63524, 5).
   - Kava drinks: `alcohol.alternatives`.
   - Probiotics, prebiotics, fiber supplements and ZBiotics: `gut.probiotics_fermented`.
   - Fluoride supplements: `oral`.
   - Collagen or peptides in creams: `skin_beauty.skincare`.
   - GLP-1s described as "peptides": `glp1`.

3. **§5.1 functional foods.** Add one line: a food or drink sold on a supplement ingredient takes the vehicle's subtopic plus the ingredient's supplement subtopic. Mushroom coffee takes `stimulants.caffeine` (when caffeine is mentioned) plus `herbal_adaptogens`; a protein bar with lion's mane takes `food.protein_intake` plus `herbal_adaptogens`. If only one is wanted, choose the ingredient. Evidence: 599000, 6; 84011, 3; 185554, 3.

4. **§5.1 general talk.** After "'supplements' in general are…", add: "A supplement retailer or subscription read with no specific product (iHerb, 'targeted supplements' in a clinic list) takes the bare `topic:supplements`, as does the bare word 'peptides' in a list of wellness trends (`topic:peptides`)." Evidence: 189137, 0; 57014, 0; 33397, 1.

5. **§5.3 and §5.4: the supplement-ad boilerplate.** The regulatory boilerplate after supplement reads ("These statements have not been evaluated by the Food and Drug Administration. This product is not intended to diagnose, treat, cure, or prevent any disease", 189244, 1; 6590, 9) should be named as `frame:disclaimer` and explicitly not `supplements.industry_quality`. "Third-party tested", "NSF certified for sport", "clinically studied formula" and "doctor-selected" are already `evidence:strength_assertion` under §5.4. Add "NSF certified for sport" and "clinically studied" to its list.

6. **How supplement and peptide ads sound.** Patterns worth adding to the rubric's ad pass:
   - **Host testimonial lines** ("Since I started taking X, I've noticed a serious boost. My focus is sharper", 6229, 0; "I feel great, and one of the reasons… is because I take balance of nature", 38289, 0). These are `evidence:personal_anecdote` and not claims, per §7.
   - **Volume testimonials** ("over a thousand success stories every single month", 38289, 0). These count as puffery.
   - **"Do your own research" inside the ad copy** ("fact-check me on this. Go do your own research on NADH", 38106, 2). This is not a frame by itself.
   - **Self-hedging copy** ("It's not a miracle, but it's a foundational habit", 709, 2). Code certainty from the claim; this line is not a claim.
   - **"Nutrient gap" and "your diet is deficient" lead-ins** ("your modern diet is often deficient in key vitamins and minerals", 388743, 3). Check them against `narrative:soil_depletion_supplements`, which applies only when soil is invoked.
   - **Clinic and telehealth reads that list treatments with effects** ("The P shot for stronger performance, PT 141 for actual desire, and Sermorelin plus NAD plus to fix his recovery", 24859, 5). Each named treatment with a stated effect takes its own subtopic and the outcome. A bare list of services ("hormone optimization, peptide therapy, targeted supplements") takes only the clinic's subject. Clarify this in §4.1, since the current "list of subjects inside one read" sentence assumes one product.

7. **Dynamic ad insertion (analysis note, not a labeling rule).** Back-catalog episodes carry current ads: a 2011 Rogan episode contains a 2026 AG1 Pro read (71801, 6), and a 2018 episode has the same read (70860, 3). Ad-relevance detections should not be dated by episode date. Researchers counting supplement advertising over time need the ingestion date, or should treat ad dates as unknown.

8. **ASR variants for the prompt or lexicon:**
   - BPC-157: "BPC one fifty seven", "BBC one five seven".
   - Thymosin: "Thymazin".
   - Epitalon: "Epitilon", "a pitalon".
   - GHK-Cu: "GHK copper", "GHKCU", "GHKC CU".
   - Pinealon: "pinealine".
   - Ka'Chava: "Katchava".
   - ARMRA: "Armura".
   - AG1: "A G one".
   - Gatorlyte: "Gator Light".
   - Lipopolysaccharide: "lippie polysaccharide".
   - Tongkat ali: "tonga ali".

   Keyword-count noise to warn analysts about: `\bepa\b` (the agency), `\bpea\b` (pea protein), `ghk` (Poughkeepsie), "category two" (hurricanes), "goli" (substring), and "reta" (Greta).

9. **Possible missing narrative (for the narrative reviewers).** Peptide and supplement regulation passages often claim that natural or unpatentable compounds are restricted to protect pharma: "Why did BPC… go on the naughty list… Because [GLP-1s] have been patented and monetized by Big Pharma" (175605, 2); "peptides can oftentimes replace prescription medications. So bye bye, big pharma" (190647, 4). "Can't be patented" phrasing appears in 161 episodes across 55 podcasts, across all subjects. It is neither `peptides_safe_miracle` nor `cancer_cures_suppressed`. For now it is `narrative:unlisted_narrative` plus `frame:big_pharma`. Worth a check on whether it warrants a listed narrative ("natural or unpatentable treatments are suppressed for profit").

10. **Supplement-routine lists.** "Ben Greenfield's 5 daily supplements"-style lists should take `biohacking.stacks_protocols` plus rule 6 (list items only when a claim is attached). A short example in §5.1 rule 6 would help, since these lists are where coders over-label most.
