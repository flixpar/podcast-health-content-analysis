# topic:food and topic:diets: corpus review

Method note. The shared machine was overloaded (load average ~120 on 32 cores). Running one cq.py query per label took up to 5 minutes, so I made a single cq.py pass with a literal superset of every term in this slice, about 300 food and diet stems. That pass matched 549,782 segments, which I stored at /mnt/internal/felix/podcast-corpus-text/work/fd-food/. I then applied the precise per-label regexes to that subset locally.

Each count below is given two ways:

- **Total:** segments / episodes / podcasts.
- **Non-ad:** the same count after dropping any segment containing ad markers ("brought to you by", "promo code", "use code", "% off", ".com/", "first order" and similar). Segments are long (about 5 KB), so non-ad is a conservative floor.

Citations use the form ep/seg.

## Summary

- **Recurring sponsor reads dominate the raw counts for several food labels.** A Nature Raised Farms chicken ad ("free from gluten, dairy, and soy. There are no seed oils and no artificial ingredients") runs in all ~3,600 Watch What Crappens episodes. That single read accounts for 3,594 of the 5,878 episodes that say "seed oils". Cook Unity's menu list ("high-protein options, gluten-free meals") appears in ~1,950 Ben Shapiro episodes. About 75% of "gluten-free" mentions are ad or menu copy (5,553 episodes in total, 1,419 non-ad). Free-from lists ("gluten-free … dairy-free", "no seed oils … no artificial") appear in 5,408 episodes, only 654 of them outside ads. The codebook needs an explicit rule that a free-from list inside a food ad does not create one topic per listed item.
- **Pet-food ads are the largest false trigger for `food.ultra_processed`.** In 2,597 episodes across 25 podcasts, "ultra-processed"/"processed food" appears only inside Farmer's Dog, Ollie or Mave reads ("kibble is an ultra-processed food", 18685/0). That is 2,521 Rogan episodes. Genuine UPF talk is 3,208 non-ad episodes across 145 podcasts. Section 3 should name pet-food ads as excluded (veterinary).
- **Every label in the slice is findable.** All 25 labels clear the 30-episode / 3-podcast bar in non-ad text, mostly by a wide margin:
  - Smallest: `diets.raw_food_juicing` (strict raw-food terms 193 episodes / 66 podcasts; green juice 780 episodes; juice cleanse 235 episodes), `diets.elimination_therapeutic` (921 non-ad episodes), `diets.mediterranean_whole_food` (1,105).
  - Largest: `food.beverages_hydration` (12,158 non-ad episodes), `food.grains_carbs_gluten` (10,053), `food.plant_foods_fiber` (7,219).
  - I recommend no merges or drops.
- **Three recurring subjects have no clear home,** and each clears the bar:
  - Dietary salt and sodium intake: 636 non-ad episodes / 102 podcasts.
  - Official dietary advice (dietary guidelines, food pyramid, MyPlate): 573 / 100. This is central to MAHA-era talk ("flipped the food pyramid").
  - Meat alternatives (lab-grown meat, "eat the bugs", Beyond/Impossible): 322 / 82 for bugs and lab meat; 564 episodes for plant-based meat brands.
  - Low-fat diets are a weaker fourth: 407 / 94.
  - I propose extending existing definitions rather than adding subtopics: salt → `micronutrients_food`, guidelines → `general_nutrition`, alternatives → `meat_animal_foods`, low-fat → `fats_oils`. `food.salt_sodium` is the one ADD I would accept if salt narratives matter to the research.
- **Boundary conflicts with neighbouring labels:**
  - `diets.low_carb_keto` lists "ketones", but exogenous ketones now belong to `supplements.other_compounds` (296 episodes, e.g. "ketone IQ", 437282/4).
  - `food.dairy_raw_milk` lists "dairy intolerance", while `gut.digestive_symptoms` owns lactose intolerance (485 episodes).
  - `diets.raw_food_juicing` ("juice fasting") overlaps `detox.organ_cleanses` ("juice cleanse") and `diets.fasting`.
  - `diets.elimination_therapeutic` lists "anti-inflammatory diet", but most uses are a general healthy pattern, not removal ("Eat an anti-inflammatory diet. Lots of fruits and vegetables", 182423/1).
- **Dead or misleading examples:**
  - "protein-maxxing": 14 episodes. "fibermaxxing": 1 episode. "UPF" as an abbreviation: 30 episodes.
  - "bioavailability" under `micronutrients_food`: most of its 1,666 episodes are about supplement forms ("what is the form of the vitamin, how bioavailable is it", 182442/5).
  - "counting points" under `calorie_counting`: this is WeightWatchers, which `weight.weight_loss_methods` already owns.
- **Non-health senses that coders will meet:**
  - "fasting insulin/glucose" (lab values; 676 episodes / 50 podcasts).
  - Religious fasting and Lent abstinence (283 episodes; "Fridays in Lent … I can't eat meat", 38261/3).
  - "juicing" as steroid slang (749 episodes; "stopped testing people if they're juicing", 202054/1).
  - "fiber" (internet, "every fiber of their humanity"), "soy boy" as an insult, "MSG" (Madison Square Garden).
  - Show-intro boilerplate: LONGEVITY's intro "ancestral health practices" is in 457 episodes.

## Label-by-label findings

Counts are total eps/pods, then non-ad eps/pods. Each query was run with known ad templates excluded (Nature Raised Farms, Cook Unity, Magic Spoon, pet-food reads) where noted.

### `topic:food.ultra_processed`

- **Query:** `ultra[- ]?processed|\bupfs?\b|bliss point|hyper[- ]?palatab|food[- ]like (products?|substances?)|highly processed|processed (foods?|junk)`, with pet-food reads excluded.
- **Counts:** 4,621 / 153 total; 3,208 / 145 non-ad.
  - Pet-food-only uses: 2,597 episodes / 25 podcasts.
  - "junk food|fast food": 6,228 / 269 total; 4,466 / 247 non-ad. Much of this is restaurant or comedy chatter ("Fast foods would be like McDonald's, Wendy's", 200940/7), which section 3 already excludes.
  - "UPF": 30 episodes. "food-like products/substances": 77 episodes / 21 podcasts.
- **Verdict:** examples change. Real phrasing is "processed garbage/junk", "highly processed", "NOVA" ("Ultra-processed foods, as defined by NOVA", 6155/4), "edible food-like substances".

### `topic:food.sugar_sweeteners`

- **Queries:**
  - Sugar (health-framed): added/refined sugar, sugar addiction, cutting sugar, HFCS, fructose, sugary drinks.
  - Sweeteners: aspartame|sucralose|stevia|monk fruit|sugar alcohols|erythritol|xylitol|allulose.
- **Counts:**
  - Sugar: 4,934 / 187 total; 2,413 / 166 non-ad.
  - Sweeteners: 2,297 / 143 total; 1,140 / 129 non-ad. Sweetener mentions are heavily "no artificial sweeteners" ad copy.
- **Verdict:** fine. Boundary seen: "sugar cravings" takes both this label and `food.eating_behavior` ("what people almost call like the sugar cravings", 19857/11).

### `topic:food.fats_oils`

- **Query:** seed oils, canola, soybean/vegetable oil, saturated/trans fat, dietary cholesterol, tallow, olive oil, ghee, linoleic, omega-6, hydrogenated.
- **Counts:**
  - All terms: 6,774 / 215 (Nature Raised Farms excluded); 4,139 / 200 non-ad.
  - Seed oils alone: 1,559 / 125 non-ad (2,303 episodes total after removing the Nature Raised Farms ad).
  - Tallow: 1,076 episodes total, 475 non-ad. Tallow is mostly ad copy (masa chips: "corn, salt, and 100% grass-fed beef tallow. No garbage. No seed oils", 5187/3).
- **Verdict:** needs a definition change. "Low-fat diet" (407 non-ad episodes / 94 podcasts) has no named home, and it is mostly told as history of the low-fat era ("That's the last thing you want is a low-fat diet", 190903/67; "dietary guidelines and the demonization of saturated fat", 180781/353). "PUFAs" is common real vocabulary ("these PUFAs … worse than sugar", 190897/114).

### `topic:food.meat_animal_foods`

- **Query:** red/processed/organ meat, offal, nose-to-tail, eating (red) meat, egg yolks, sardines, beef liver.
- **Counts:** 6,983 / 243 total; 5,025 / 226 non-ad.
- **Noise:** Lent abstinence (38261/3) and comedy meat talk.
- **Verdict:** needs a definition change to give meat alternatives a home:
  - Lab-grown meat, "eat the bugs", insect protein: 322 / 82 non-ad.
  - Beyond/Impossible and plant-based meat: 564 / 100 total.
  - Quotes: "you're supposed to be eating bugs anyway… I will not eat the bugs" (207075/6); "Italy, I think, is the first country to ban lab-grown meat" (196144/1); "Impossible Burger, which is… a lab-produced meat, a fake meat" (182893/3).
  - Many mentions are jokes, so they need the usual health-dimension test.
  - Bone broth (858 episodes / 93 podcasts) also fits here as food.

### `topic:food.dairy_raw_milk`

- **Query:** raw milk, pasteurization, whole milk, A2 milk, dairy, lactose, full-fat dairy, cow's milk.
- **Counts:**
  - All terms: 7,273 / 248 (Nature Raised Farms excluded); 4,528 / 225 non-ad.
  - Raw milk: 487 / 82 total; 347 / 72 non-ad (Culture Apothecary 50, Rogan 48).
- **Verdict:** examples change. "Dairy intolerance" collides with `gut.digestive_symptoms` (lactose intolerance: 485 / 106). Passing jokes are common ("Maybe he's lactose intolerant", 322391/6). Real usage includes "full fat dairy back on the top of the pyramid" (181911/4).

### `topic:food.grains_carbs_gluten`

- **Query:** gluten, wheat, refined flour/carbs, white bread/rice, glycemic, carbs, carbohydrates, whole grains, starch.
- **Counts:** 16,421 / 287 total; 10,053 / 261 non-ad.
- **Verdict:** fine, but broad.
  - Inflated by ads: Watch What Crappens 3,608 episodes, Shapiro 1,951, all "gluten-free" menu or free-from lists.
  - Boundary with `diets.elimination_therapeutic`: "people just get rid of the wheat. Or the gluten, but they don't rebuild the gut" (182594/3) is celiac → `gut.gi_disease` plus this label.

### `topic:food.protein_intake`

- **Query:** grams of protein, protein target/intake/needs, protein bars, leucine, high-protein, grams per pound/kilo, enough protein, protein-rich.
- **Counts:** 7,682 / 224 total; 4,543 / 188 non-ad.
  - Pardon My Take's "non-ad" 727 is an unmarked ONE protein bar read: "all protein bars generally taste the same, but not ONE bars" (128564/3).
  - "Protein bars": 2,463 episodes, mostly ads.
  - "protein-maxxing": 14 episodes.
- **Verdict:** examples change. Replace protein-maxxing with real phrasing: "high-protein diet", "enough protein", "grams of protein a day" ("getting enough protein", 195869/11).

### `topic:food.plant_foods_fiber`

- **Query:** oxalates, lectins, polyphenols, cruciferous, legumes, soy, phytoestrogens, sulforaphane, broccoli sprouts, fruits and vegetables, phytonutrients, fiber. Non-food fiber senses were excluded.
- **Counts:**
  - All terms: 11,686 / 304 total; 7,219 / 274 non-ad.
  - Fiber: 7,453 / 261. Oxalates: 275 / 47. Lectins: 264 / 44. Soy: 2,222 / 184.
  - "Fibermaxxing": 1 episode.
- **Verdict:** examples change. Drop fibermaxxing.
- **Noise to flag:**
  - "Fiber" in non-food senses: "100% fiber internet" (95787/0), "every single fiber of their humanity" (71468/14), "hair and fiber experts" (63016/6).
  - "soy boy" as an insult (205585/8).
  - Sulforaphane is a whole-food subject here ("broccoli sprouts to my green juice", 193019/2), but `supplements.other_compounds` lists it, so code by form (rule 5).

### `topic:food.additives_dyes`

- **Queries:**
  - Dyes: food dye, `\bred (dye )?(no|number )?(40|forty)`, red dye, yellow 5/6, artificial colours, synthetic or petroleum dyes, titanium dioxide.
  - Other additives: emulsifiers, preservatives, MSG, GRAS, carrageenan, bromate, food additives, artificial flavours.
- **Counts:**
  - Dyes: 1,993 / 160 total; 812 / 135 non-ad.
  - Other additives: 4,439 / 208 total; 2,020 / 181 non-ad.
  - GRAS: 214 / 75.
- **Verdict:** examples change. Real forms: "red dye three", "red dye number three" (175808/0, 78375/8). GRAS is transcribed "a grass": "they called it a grass. Generally recognized as safe" (181944/2).
- **Noise:** "MSG" often means Madison Square Garden. Unbounded "red forty" matches "hundred forty".

### `topic:food.organic_gmo`

- **Query:** GMO/non-GMO, genetically modified/engineered, regenerative, grass-fed, bioengineered, organic food/produce, pasture-raised, factory farm, soil depletion.
- **Counts:** 8,969 / 227 total; 3,848 / 189 non-ad. "Non-GMO" is ad copy in most episodes.
- **Verdict:** fine. Gregg Braden's "GMO seeds, GMO insects… big pharma and big agriculture" (183384/1) shows this label sitting with `frame:big_food`.

### `topic:food.beverages_hydration`

- **Query:** (de)hydration, soda, soft drinks, alkaline/structured/hydrogen/mineral water, drink more water, water intake, fruit juice, diet soda, sugary drinks.
- **Counts:**
  - All terms: 21,714 / 401 total; 12,158 / 369 non-ad.
  - Wellness waters: 571 / 87 total; 426 / 74 non-ad (Ultimate Human 113).
- **Verdict:** fine; very broad. "Make sure you hydrate" asides are mostly passing (1664/5). The ad side is electrolyte drinks (Element, Liquid I.V.); the supplements row now splits powders (supplements) from ready-to-drink (here).

### `topic:food.micronutrients_food`

- **Query:** nutrient-dense, bioavailability, scurvy, iron-rich, anti-nutrients, nutrient deficiency, "rich in / good source of" a vitamin or mineral.
- **Counts:** 4,249 / 166 total; 2,383 / 137 non-ad.
  - "Bioavailab-": 1,666 episodes; only ~615 have a food word nearby, and the rest are mostly supplement forms (182442/5).
  - "Nutrient-dense": 1,771 episodes, the dominant real phrase ("the most nutritious food, most nutrient-dense food… steak", 11534/9).
- **Verdict:** needs a definition change to qualify bioavailability and take in dietary salt.
- **Salt evidence:** salt intake, low-sodium/low-salt, too much salt, salt and blood pressure, Celtic or unrefined salt, "salt your food": 866 / 116 total; 636 / 102 non-ad.
  - "salt your food. Add the sodium. Zinc and sodium are the two most important things you need to make your own stomach acid" (190406/89).
  - "If you have too much salt, it can kill you" (12867/4).
  - Sodium as a blood lab value is not food (15113/1).

### `topic:food.eating_behavior`

- **Query:** skipping breakfast, cravings, food addiction, satiety, snacking, intuitive/mindful/emotional eating, meal timing, food noise, stress eating, overeating, binge eating, late-night eating, hunger hormones, ghrelin, leptin.
- **Counts:** 5,619 / 228 total; 3,842 / 208 non-ad. Meal timing and late eating: 1,137 / 146. Binge eating: 356 / 97.
- **Verdict:** examples change; add the real terms:
  - overeating: "you can't overeat" on carnivore (6441/17), which takes the diet label plus this one;
  - ghrelin and leptin;
  - late-night eating.
- **Boundaries:**
  - Binge-eating disorder goes to `mental.eating_disorders`.
  - "Food noise" is `glp1` vocabulary but also appears in supplement ads (190471/62).

### `topic:food.food_system_access`

- **Query:** school lunch/meals, SNAP benefits or ban, food stamps, food deserts, food insecurity, farm subsidies, farm bill, food banks, food or egg prices, food system, big food, food industry, WIC.
- **Counts:** 6,736 / 252 total; 4,280 / 233 non-ad.
  - School lunch: 1,254 / 143. SNAP: 1,747 / 169. Egg prices: 571 / 79.
- **Verdict:** fine; examples change. Much SNAP talk is shutdown or benefit politics with no health dimension (166196/0, 81594/0). The health-relevant core is SNAP and soda: "seventy plus percent… goes to junk food… ten percent goes just to soda" (182412/5). Add "SNAP soda restrictions" and "price of eggs".

### `topic:food.food_contaminants`

- **Query:** heavy metals in, lead in cinnamon/baby food/chocolate/spices/protein, arsenic in rice/food, mycotoxins, aflatoxin, microplastics in food/water, pesticide residue, mold in coffee/grains, dirty dozen, mercury in fish, glyphosate in/on, baby food.
- **Counts:** 1,281 / 138 total; 896 / 124 non-ad.
- **Verdict:** fine.
- **Boundaries seen:**
  - Household mold or mycotoxin illness ("we finally had the villain when we got that mold and mycotoxin back", 176919/1) is environmental, not food.
  - Arsenic murders in true crime are poisoning (170972/4), not contamination.

### `topic:food.general_nutrition`

- **Query:** eat healthy, healthy eating/diet/food, balanced diet, real food, food as/is medicine, clean eating, nutrition advice/science, poor nutrition, bad diet.
- **Counts:** 8,877 / 255 total; 5,857 / 234 non-ad.
- **Verdict:** needs a definition change. Official dietary advice has no stated home:
  - Food pyramid, dietary guidelines, MyPlate, USDA guidelines: 814 / 112 total; 573 / 100 non-ad.
  - "the body of literature that pointed towards the food pyramid, was quite shoddy" (181856/15).
  - "if you go off the food pyramid, you're going to be fat, obese" (7607/3).
  - "the new dietary guidelines… put full fat dairy back on the top of the pyramid" (181911/4).
  - "Standard American diet": 520 / 58.

### `topic:diets.low_carb_keto`

- **Query:** keto, ketosis, ketogenic, low-carb, Atkins, ketones, carb cycling. "fasting insulin/glucose" was excluded.
- **Counts:** 5,626 / 212 total; 3,706 / 194 non-ad.
  - Exogenous ketones and ketone esters: 296 / 34.
  - Carb cycling and high-carb diet: 203 / 36.
- **Verdict:** examples change. "Ketones" must mean ketones from diet, since `supplements.other_compounds` owns exogenous ketones ("ketone supplements. Like I could see something like ketone IQ", 437282/4).
- **Noise:** "keto" also turns up in a BJJ ASR ("comes out the keto with the death touch", 71396/5) and in "keto-friendly" ad lists.

### `topic:diets.carnivore_animal_based`

- **Query:** carnivore, animal-based diet, lion diet, meat-only, all-meat, zero-carb.
- **Counts:** 2,731 / 171 total (excluding the Carnivore Club ad); 1,795 / 155 non-ad.
- **Noise:**
  - 343 Something You Should Know episodes are a PC ad naming "Uncle Mike's carnivore diet".
  - "carnivores will starve" in a nature documentary (324129/1243).
- **Verdict:** fine.

### `topic:diets.plant_based`

- **Query:** vegan, veganism, vegetarian, plant-based diet, whole-food plant-based, pescatarian, flexitarian. "Vegan leather" and the Cook Unity read were excluded.
- **Counts:** 9,951 / 289 total; 5,885 / 253 non-ad.
- **Noise:** jokes and identity talk ("Is there a vegan option?", 197854/4) and "plant-based preparations that contain DMT" (68336/10).
- **Verdict:** fine; add pescatarian. Low-fat plant-based programmes (Esselstyn, Ornish, McDougall) belong here (181082/1).

### `topic:diets.fasting`

- **Query:** intermittent fasting, fasting, OMAD, one meal a day, time-restricted, water fast, fasting-mimicking, eating/feeding window, extended or prolonged fast, 16:8. "fasting insulin/glucose/blood/levels" were excluded.
- **Counts:**
  - Fasting: 4,864 / 192 total; 3,571 / 179 non-ad.
  - Lab-value phrases ("fasting insulin/glucose"): 676 / 50.
  - Religious fasting: Bible in a Year alone has 137 episodes with "fasting"; Lent, Ramadan and Yom Kippur appear with "fast" in 283 episodes / 79 podcasts.
- **Verdict:** needs a definition change for exclusions. Religious fasting with a health point does belong here: "once a year, maybe on Yom Kippur or during Lent or during Ramadan, he'll have a little bit longer fast" (181815/15).

### `topic:diets.ancestral_paleo`

- **Query:** paleo, ancestral diet/eating/health, Weston A. Price, traditional foods/diets, primal diet, eat like our ancestors, pegan.
- **Counts:** 3,004 / 134 total; 1,829 / 117 non-ad. This is inflated by LONGEVITY's intro ("new technology to ancestral health practices", 190347/1) in 457 episodes.
- **Verdict:** examples change; add "pegan" (114 episodes / 11 podcasts, Hyman).

### `topic:diets.mediterranean_whole_food`

- **Query:** Mediterranean diet, DASH diet, Blue Zones, Okinawan diet, MIND diet, whole-food diet, Nordic diet.
- **Counts:** 1,442 / 120 total; 1,105 / 106 non-ad.
- **Verdict:** needs a definition change. Blue Zones are often discussed as a longevity lifestyle rather than a diet ("one of the big lessons that come from the blue zones… the environment", 189446/3; "This is where yah blue zones were. They're not in stress", 611702/4). Those mentions should not take a diet label. The general "anti-inflammatory diet" also fits here better than under elimination.

### `topic:diets.elimination_therapeutic`

- **Query:** elimination diet, FODMAP, AIP, autoimmune protocol, gluten-free diet, going gluten-free, anti-inflammatory diet, low-histamine, GAPS, Whole30, SCD, low-oxalate, low-lectin, Plant Paradox, cutting out gluten or dairy.
- **Counts:**
  - All terms: 1,231 / 120 total; 921 / 104 non-ad.
  - Bare "gluten-free": 5,553 / 177 total but only 1,419 non-ad.
  - Anti-inflammatory diet: 235 / 40.
  - Whole30: 149 / 60.
- **Verdict:** needs a definition change.
  - Therapeutic use is the core: "a low FODMAP diet… a lot of my clients have… SIBO" (193071/1); "You can do the AIP diet for a short period of time" (190499/92).
  - Anti-inflammatory diet is split. It is a regimen in 192823/3 ("for 30 days") but a general pattern in 182423/1.

### `topic:diets.calorie_counting`

- **Query:** calorie deficit, calories in calories out, counting calories, counting/tracking macros, IIFYM, calorie surplus, energy balance, MyFitnessPal.
- **Counts:** 2,291 / 135 total; 1,789 / 123 non-ad (Mind Pump 469).
- **Verdict:** examples change. "Counting points" is WeightWatchers, which `weight.weight_loss_methods` lists (commercial programmes: 1,081 / 135).
- **Contested use:** CICO is often disputed ("calories in, calories out… it's your fault", 182898/1), so the label is used in contested talk, not only practical talk.

### `topic:diets.raw_food_juicing`

- **Queries and counts:**
  - Strict raw-food terms (raw vegan, raw food diet, raw foodist, fruitarian, living foods): 193 / 66 total; 154 / 60 non-ad.
  - Celery juice and Medical Medium: 94 / 39.
  - Green juice: 780 / 119, mostly lifestyle asides and ads.
  - Juice cleanse/fast/detox: 235 / 81.
  - "Juicing": 749 / 119, frequently PED slang (202054/1) or non-health ("juicing the tracklist", 89062/8).
- **Verdict:** rare but keep. The coverage of the medical-medium and raw-vegan healing claims is worth having ("How Raw Foods and Juicing Save…", 176995/3). The definition needs a boundary with `detox.organ_cleanses` ("I did the juice cleanse… I was so hungry for meat", 128112/10).

## Proposed edits

CHANGE `topic:food.ultra_processed`:
| ultra_processed | Ultra-processed & processed food | Processed and ultra-processed foods, fast food and junk food as a health subject, food engineering and hyperpalatability. Fast food talked about only as restaurants, taste or prices is not health content; pet-food ads that call kibble ultra-processed are excluded (veterinary). | ultra-processed food; highly processed food; processed junk; junk food; fast food (as a health subject); NOVA classification; bliss point; hyperpalatable; edible food-like substances |
Why: 3,208 non-ad episodes / 145 podcasts use the real phrases. "UPF" occurs in only 30 episodes. In 2,597 episodes the only processed-food vocabulary is a pet-food ad (18685/0, "kibble is… an ultra-processed food").

CHANGE `topic:food.fats_oils`:
| fats_oils | Fats & cooking oils | Dietary fats and oils: seed and vegetable oils, saturated fat, trans fat, dietary cholesterol, butter, tallow, olive oil, frying, the omega-6 to omega-3 balance in food, and low-fat diets and the low-fat era. A low-fat plant-based programme also takes `diets.plant_based`. | seed oils; canola; soybean oil; PUFAs; hydrogenated oils; saturated fat; trans fats; dietary cholesterol; beef tallow (as food); olive oil; ghee; low-fat diet |
Why: "Low-fat diet" and related terms appear in 407 non-ad episodes / 94 podcasts with no named home, mostly as fat history ("That's the last thing you want is a low-fat diet", 190903/67). "PUFAs" is real usage (190897/114).

CHANGE `topic:food.meat_animal_foods`:
| meat_animal_foods | Meat, eggs & fish | Meat, poultry, eggs, fish, organ meats and bone broth as foods and their health effects, and alternatives to them: plant-based meat substitutes, lab-grown or cultivated meat, and insects as food. Abstaining from meat for religious observance with no health point is not health content. | red meat; processed meat; eggs; organ meats; liver; sardines; grass-fed beef; bone broth; lab-grown meat; Beyond Meat or Impossible Burger; "eat the bugs" |
Why: lab-grown meat and bugs give 322 non-ad episodes / 82 podcasts; plant-based meat brands give 564 / 100. Neither has a home. Examples: "you're supposed to be eating bugs anyway… I will not eat the bugs" (207075/6); "Impossible Burger, which is… a lab-produced meat" (182893/3); Lent abstinence (38261/3).

CHANGE `topic:food.dairy_raw_milk`:
| dairy_raw_milk | Dairy & raw milk | Milk and dairy products as food, including raw (unpasteurized) milk, whole and full-fat dairy, and cutting out dairy. Lactose intolerance as a digestive symptom goes to `gut.digestive_symptoms`; add this label when dairy itself is discussed. | raw milk; pasteurization; whole milk; full-fat dairy; cheese; A2 milk; going dairy-free |
Why: "dairy intolerance" collides with `gut.digestive_symptoms`, which lists lactose intolerance (485 episodes / 106 podcasts, many of them passing jokes, 322391/6). "Full-fat dairy" is a live guidelines topic (181911/4).

CHANGE `topic:food.protein_intake`:
| protein_intake | Protein intake | How much protein people need and where they get it from food, including high-protein diets and protein bars. Protein powders go to `supplements.protein_powders`. | protein targets; grams of protein a day; grams per pound; high-protein diet; getting enough protein; amino acids from food; leucine threshold; protein bars |
Why: "protein-maxxing" appears in 14 episodes. The real phrases ("enough protein", "high protein", "grams of protein") are in 4,543 non-ad episodes / 188 podcasts (195869/11).

CHANGE `topic:food.plant_foods_fiber`:
| plant_foods_fiber | Fruits, vegetables, fiber & plant compounds | Produce, legumes, nuts and seeds, fiber, soy as food, and plant compounds eaten in food said to help or harm. "Soy boy" as an insult with no claim about soy is not health content. | vegetables; fruit; fiber; legumes; soy; phytoestrogens; oxalates; lectins; polyphenols; phytonutrients; cruciferous; broccoli sprouts |
Why: "fibermaxxing" appears in 1 episode. Plant compounds as eaten have 7,219 non-ad episodes / 274 podcasts. "Soy boy" insults appear (205585/8).

CHANGE `topic:food.additives_dyes`:
| additives_dyes | Additives, dyes & preservatives | Specific food additives, including their regulation and bans and the GRAS process for food. Cross-product regulatory philosophy goes to `policy.regulation_chemicals_food_drugs`. | food dyes; Red 40 (also "red forty", "red dye number three"); titanium dioxide; preservatives; emulsifiers; MSG; GRAS (transcribed "a grass"); brominated vegetable oil; potassium bromate; "banned in Europe" ingredients |
Why: Dyes appear in 812 non-ad episodes / 135 podcasts and other additives in 2,020 / 181. The ASR forms are real: "red dye three" (175808/0) and "they called it a grass. Generally recognized as safe" (181944/2).

CHANGE `topic:food.micronutrients_food`:
| micronutrients_food | Vitamins, minerals & salt from food | Vitamins and minerals from named food sources, nutrient density, the bioavailability of nutrients in food, deficiency diseases explained through diet, and dietary salt and sodium intake. Nutrient status (levels, deficiency, testing, "you need more X") with no form stated goes to the nutrient's `supplements` subtopic; the bioavailability of supplement forms goes to that supplement; salt's effect on blood pressure also takes `cardiovascular.blood_pressure`. | vitamin C in fruit; scurvy; iron-rich foods; heme iron; nutrient-dense foods; salt intake; low-sodium diet; Celtic or unrefined salt; "salt your food" |
Why: dietary salt has 636 non-ad episodes / 102 podcasts and no home ("salt your food. Add the sodium", 190406/89; "too much salt, it can kill you", 12867/4). Most "bioavailability" mentions (1,666 episodes) are about supplement forms (182442/5). If researchers want salt counted separately, add `food.salt_sodium` instead with the same evidence.

CHANGE `topic:food.eating_behavior`:
| eating_behavior | Eating behavior, appetite & cravings | When and how people eat: meal timing, breakfast, snacking, overeating, cravings, hunger and satiety signals, food addiction, mindful or intuitive eating. Named fasting regimens go to `diets.fasting`; binge-eating disorder to `mental.eating_disorders`. | skipping breakfast; late-night eating; cravings; overeating; satiety; ghrelin and leptin; food addiction; snacking; intuitive eating |
Why: 3,842 non-ad episodes / 208 podcasts. Overeating, satiety and hunger hormones are the most frequent real vocabulary ("you can't overeat", 6441/17). Binge eating appears in 356 episodes and needs pointing to `mental.eating_disorders`.

CHANGE `topic:food.food_system_access`:
| food_system_access | Food system, access & school food | The food system and access to food as health issues: school meals, food deserts, food assistance and what it may buy, food prices, agriculture policy, the food industry's structure. Food-assistance budget politics with no nutrition or health point is not health content. | school lunch; SNAP soda and candy restrictions; food stamps; food deserts; food insecurity; food banks; farm subsidies; price of eggs |
Why: 4,280 non-ad episodes / 233 podcasts. Much SNAP talk is shutdown politics with no health dimension (166196/0). The health core is "ten percent goes just to soda" (182412/5).

CHANGE `topic:food.general_nutrition`:
| general_nutrition | General nutrition & healthy eating | Healthy eating, "real food", balanced diet, food as medicine, the standard American diet, macronutrient balance in general, and official dietary advice as a whole (dietary guidelines, the food pyramid, MyPlate), with no specific food, nutrient or named diet. Guidance about one food takes that food's subtopic; add `policy` subtopics only when the political process is itself discussed. | eating healthy; well-balanced diet; eat real food; food as medicine; standard American diet; food pyramid; dietary guidelines; MyPlate |
Why: official dietary advice has 573 non-ad episodes / 100 podcasts and no stated home ("the body of literature that pointed towards the food pyramid, was quite shoddy", 181856/15; "if you go off the food pyramid, you're going to be fat", 7607/3). "Standard American diet" appears in 520 episodes / 58 podcasts.

CHANGE `topic:diets.low_carb_keto`:
| low_carb_keto | Low-carb & ketogenic | Low-carbohydrate and ketogenic diets, carb cycling, and ketosis from eating. Exogenous ketone products go to `supplements.other_compounds`. | keto; ketosis; low-carb; Atkins; carb cycling; ketones from diet |
Why: `supplements.other_compounds` now owns exogenous ketones (296 episodes / 34 podcasts; "ketone IQ", 437282/4). The bare "ketones" example contradicts that. Carb cycling appears in 203 episodes / 36 podcasts.

CHANGE `topic:diets.plant_based`:
| plant_based | Vegan, vegetarian & plant-based | Diets excluding or minimizing animal foods, including low-fat plant-based programmes. Vegan as a material ("vegan leather") or a menu option with no health point is not health content. | vegan; vegetarian; plant-based; whole-food plant-based; pescatarian; Esselstyn or Ornish programme |
Why: 5,885 non-ad episodes / 253 podcasts. Non-diet uses are common ("vegan leather cover", 30647/0; Cook Unity menu lists).

CHANGE `topic:diets.fasting`:
| fasting | Fasting & time-restricted eating | Intermittent, extended and water fasting, time-restricted eating, fasting-mimicking diets, one meal a day, and religious fasting when its health effects are discussed. Fasting blood tests (fasting insulin, fasting glucose) go to `metabolic`; juice cleanses to `detox.organ_cleanses`. | intermittent fasting; 16:8; eating window; OMAD; water fast; 24-hour fast; fasting-mimicking; autophagy from fasting |
Why: 3,571 non-ad episodes / 179 podcasts. "Fasting insulin/glucose" adds 676 episodes / 50 podcasts of lab-value false hits. Religious fasting appears in 283 episodes / 79 podcasts and only sometimes has a health point (181815/15 vs 330563/379).

CHANGE `topic:diets.ancestral_paleo`:
| ancestral_paleo | Paleo, ancestral & traditional diets | Diets defined by an ancestral or traditional ideal. A show's intro listing "ancestral health practices" is not health content. | paleo; pegan; ancestral diet; nose-to-tail eating; Weston A. Price; traditional foods; "eat like your great-grandmother" |
Why: 1,829 non-ad episodes / 117 podcasts. "Pegan" appears in 114 episodes. LONGEVITY's intro boilerplate accounts for 457 episodes (190347/1).

CHANGE `topic:diets.mediterranean_whole_food`:
| mediterranean_whole_food | Mediterranean & whole-food patterns | Mediterranean, DASH, MIND, Blue Zones and named "whole foods" or anti-inflammatory eating patterns followed as a general way of eating. Healthy eating with no named pattern goes to `food.general_nutrition`; Blue Zones discussed only for purpose, community or longevity goes to `longevity`, not here. | Mediterranean diet; DASH; MIND diet; Blue Zones diet; whole-food diet; anti-inflammatory diet (as a general pattern) |
Why: 1,105 non-ad episodes / 106 podcasts. Blue Zones are often lifestyle, not diet (189446/3, 611702/4). The general anti-inflammatory diet means "lots of fruits and vegetables, antioxidants" (182423/1), not removal.

CHANGE `topic:diets.elimination_therapeutic`:
| elimination_therapeutic | Elimination & therapeutic diets | Diets that remove foods to treat symptoms or conditions, including an anti-inflammatory diet when foods are removed for a set period to treat something. "Gluten-free" or "dairy-free" as a product attribute in an ad or menu is not a regimen. | elimination diet; low-FODMAP; AIP; Whole30; going gluten-free (as a regimen); low-histamine; low-oxalate; GAPS |
Why: 921 non-ad episodes / 104 podcasts. 75% of "gluten-free" mentions are ad or menu copy (5,553 episodes in total, 1,419 non-ad). Anti-inflammatory diet is a regimen in 192823/3 but a general pattern in 182423/1. Whole30 appears in 149 episodes / 60 podcasts.

CHANGE `topic:diets.calorie_counting`:
| calorie_counting | Calorie & macro counting | Dieting by calories or macronutrient targets, and the energy-balance idea itself. Named commercial programmes (WeightWatchers, Noom) go to `weight.weight_loss_methods`. | calories in calories out; calorie deficit; counting macros; IIFYM; MyFitnessPal; energy balance |
Why: 1,789 non-ad episodes / 123 podcasts. "Counting points" duplicates WeightWatchers under weight (commercial programmes: 1,081 episodes). CICO is itself contested (182898/1, 182104/0).

CHANGE `topic:diets.raw_food_juicing`:
| raw_food_juicing | Raw-food & juicing diets | Diets built on raw foods or juices as an ongoing way of eating, and the "living food" ideas behind them. A time-limited juice cleanse or detox goes to `detox.organ_cleanses`; "juicing" meaning steroid use goes to `peds`. | raw vegan; raw food diet; fruitarian; living foods; celery juice; daily green juice |
Why: this label is rare: 154 non-ad episodes / 60 podcasts on strict raw-food terms, celery juice in 94 / 39. Juice cleanses (235 / 81) overlap `detox.organ_cleanses`, and "juicing" is often PED slang (749 episodes; 202054/1).

## Codebook and prompt notes

1. **Section 3 (ad test) and 4.1 ("Topics inside ads"): free-from lists.** A free-from list inside a food or supplement read is the product's attributes. Topic the advertised product's own subject only: chicken → `food.meat_animal_foods`, a meal service → `food.general_nutrition`. Do not add one topic per list item.
   - The free-from claims are coded only as `frame:toxin_purity` or `frame:naturalness_appeal` when that language occurs (5.2 already says the narrative does not apply).
   - Evidence: such lists appear in 5,408 episodes, 654 outside ads.
     - Nature Raised Farms in ~3,600 Watch What Crappens episodes (91764/9).
     - Whole Foods' "300 food ingredients banned… No hydrogenated fats… no high fructose corn syrup" (90054/0).
     - Paleo Valley's "no preservatives, gluten, soy, sugar, dairy, or GMOs" (10833/2).
   - Without this rule, a labeler following "be exhaustive" adds `fats_oils` + `dairy_raw_milk` + `grains_carbs_gluten` + `plant_foods_fiber` + `additives_dyes` to one chicken ad.
2. **Section 3: menu-variety lists.** Say whether a meal-kit menu list passes ad test (c). Examples: "high-protein options, gluten-free meals, pescatarian dishes, Mediterranean food" (Cook Unity, ~1,950 Shapiro episodes, 390755/0); Factor's "Mediterranean diet options" (191529/2). I suggest it fails (menu composition, not framed as healthier) unless a health benefit is stated.
3. **Section 3 exclusions: pet-food ads.** Add pet-food ads to the "animal and veterinary health" bullet, including when they generalize ("eating highly processed food for every meal isn't optimal… kibble is an ultra-processed food", 18685/0; Ollie 89791/4; Mave 25200/1). In 2,597 episodes this is the only processed-food vocabulary.
4. **Section 3 idioms and non-health senses: name this slice's recurring false triggers.**
   - "juicing" (steroids or slang).
   - "fiber" (internet, "every fiber of my being").
   - "soy boy" (insult; it invokes `narrative:soy_feminizes` only if the phytoestrogen claim is made).
   - "MSG" (Madison Square Garden), "in the red", "Whole Foods" (the store).
   - "fasting insulin/glucose" (a lab test → `metabolic`).
   - Religious fasting and abstinence ("Fridays in Lent… I can't eat meat", 38261/3) unless a health effect is discussed.
5. **Section 3, "'health' as a podcast's tagline": extend to recurring intro or outro boilerplate that lists health practices.** Example: LONGEVITY's "ancestral health practices… peptides and bioregulators" (457 episodes, 190347/1). These are excluded, or at most one `passing` detection, but never `substantive`.
6. **Section 5.1, rule 5 (specific beats general):** add one line: "bioavailability" follows the form (supplement form → that supplement; food → `food.micronutrients_food`). Same for sulforaphane: broccoli sprouts are food, a capsule is a supplement. Evidence: 182442/5 and 193019/2.
7. **Section 5.1, co-labeling rule 1:** a diet's effect on appetite or overeating takes the diet plus `food.eating_behavior` ("the interesting thing about the carnivore diet is you can't overeat", 6441/17). "Sugar cravings" takes `food.sugar_sweeteners` + `food.eating_behavior`.
8. **Section 5.2, narratives (for the narrative reviewer).** Three recurring contested propositions in this slice have no narrative:
   - "calories in, calories out is a food-industry myth / calories don't matter" (182104/0, 182898/1, 182350/4).
   - "they want you to eat bugs / fake meat" (207075/6, 205347/3, 7405/4). This is more WEF or control conspiracy than health.
   - "the food pyramid / dietary guidelines made Americans sick" (7607/3, 180781/353). This partly overlaps `saturated_fat_cholesterol_myth`.
   - The first and third clear the "recurring across podcasts" bar from the samples I read. Until narratives exist, coders should use `narrative:unlisted_narrative` with the proposition named in the summary.
9. **Section 4.1 (`relevance`): unmarked reads.** Some recurring sponsor reads have no "brought to you by", code or URL in the transcript segment. An example is Pardon My Take's ONE protein bar read, introduced with "All right. So, Jake, all protein bars generally taste the same, but not ONE bars" (128564/3). The "scripted change of register into ad copy" criterion should be stressed for these; a model reading the window alone will otherwise score them `substantive`.
