# Health-content taxonomy v8 (granular)

This file is the single source of the v8 label set. `analysis/topic_labeling.py
taxonomy --topics taxonomy/health-v8.md` compiles it into `taxonomy.json`; the
compiler reads only the headings and tables below, so prose between them is
commentary for human readers.

The taxonomy has five axes. Each detection carries labels from one axis only.

| axis | what it records | labels |
| --- | --- | --- |
| topic | the specific subject being discussed | parent topics (`topic:<parent>`) and their subtopics (`topic:<parent>.<leaf>`) |
| narrative | a specific, recurring, contested health proposition being invoked, in any stance | `narrative:<id>` |
| frame | the rhetorical framing applied to health content | `frame:<id>` |
| evidence | how support or authority is invoked | `evidence:<id>` |
| population | whose health the content is specifically about | `population:<id>` |

## How the topic hierarchy is used

Topics are a two-level tree grouped into domains. A labeler applies the most
specific **subtopic** that fits (`topic:vaccines.hep_b`). The **parent** ID on
its own (`topic:vaccines`) means "this parent topic, but no listed subtopic
fits, or the parent is discussed only as a whole"; the summary then names the
aspect. Parents, and domains above them, are derived from subtopics for
analysis, so a labeler never needs to apply a parent and one of its subtopics to
the same span.

A subtopic names a subject, not a stance: `topic:vaccines.hep_b` applies equally
to a pediatrician defending the birth dose and to a guest arguing against it.
Stance lives in `discourse_role`; specific contested propositions live on the
narrative axis; rhetoric lives on the frame axis.

Format rules the compiler enforces: every ID is lowercase `[a-z0-9_]`, unique
within its parent; every row has a definition; every narrative names a home
topic parent that exists.

## Topic axis

### Domain: Vaccines & infectious disease `vaccines_infectious`

#### Vaccines & Immunization `vaccines`
Vaccines themselves: specific vaccines, the schedule, safety, ingredients, mandates, uptake and development. Apply whatever the stance. Infection with the disease a vaccine prevents goes to that disease's subtopic (e.g. measles outbreaks to `infectious.measles`).

| id | name | definition | examples |
| --- | --- | --- | --- |
| childhood_schedule | Childhood vaccine schedule | The infant and childhood schedule as a whole: how many shots, at what ages, combination shots, delayed or alternative schedules, ACIP/CDC schedule changes, well-child visits as vaccination occasions. | CDC schedule; 72 doses; spacing out shots; alternative schedule; Dr. Bob schedule; ACIP vote on schedule |
| hep_b | Hepatitis B vaccine | The hepatitis B vaccine, including the newborn birth dose and arguments about who needs it. | Hep B birth dose; hepatitis B shot at the hospital; low-risk mothers |
| mmr | MMR vaccine | The measles-mumps-rubella vaccine (and MMRV): efficacy, safety, timing, boosters, titers. The measles disease itself goes to `infectious.measles`. | MMR shot; measles vaccine; MMR booster; titers |
| covid_vaccines | COVID-19 vaccines | COVID-19 vaccines and boosters of any platform: efficacy, side effects, approvals, recommendations, who should get them. COVID vaccine side effects take this alone unless injury systems (VAERS, compensation) are discussed, which add `vaccines.safety_injury`. | mRNA vaccine; Pfizer; Moderna; booster; J&J shot; Novavax; "the jab" |
| hpv_vaccine | HPV vaccine | The HPV vaccine (Gardasil): age, efficacy against cancer, alleged harms, litigation. | Gardasil; HPV shot; cervical cancer vaccine |
| flu_vaccine | Influenza vaccine | Seasonal flu shots: effectiveness, recommendations, who gets them. | flu shot; flu vaccine effectiveness; high-dose flu shot |
| other_vaccines | Other specific vaccines | A named vaccine not listed above. | RSV vaccine; Tdap; DTaP; pertussis vaccine; polio vaccine; chickenpox; shingles; tetanus shot; rotavirus; pneumococcal; mpox vaccine; travel vaccines |
| safety_injury | Vaccine safety, injury & surveillance | Vaccine adverse events and injury as a subject, and the systems that monitor or compensate them. Vaccine-linked myocarditis also takes `cardiovascular.heart_disease`. | adverse events; vaccine injury; VAERS; Vaccine Safety Datalink; VICP; vaccine court; 1986 Act; liability shield; package insert |
| ingredients | Vaccine ingredients & contaminants | What is in vaccines and claims about those components. | aluminum adjuvant; thimerosal; mercury; formaldehyde; fetal cell lines; polysorbate 80; SV40; DNA contamination; lipid nanoparticles |
| mandates_exemptions | Mandates, exemptions & passports | Requirements to vaccinate and ways out of them: school and employer mandates, religious and medical exemptions, vaccine passports, mandate politics. | vaccine mandate; school requirements; religious exemption; vaccine passport; no jab no job |
| uptake_hesitancy | Uptake, hesitancy & vaccine decisions | Vaccination rates, hesitancy, trust in vaccines, how parents decide, pediatricians dismissing unvaccinated families, informed consent for vaccines. | vaccination rates falling; vaccine hesitant; vax-free kids; pediatrician fired us |
| development_approval | Vaccine development, trials & approval | How vaccines are developed, tested and approved: trial design, placebo controls, emergency use authorization as a process, ACIP and FDA advisory processes, manufacturers' role. Vaccine-maker economics go to `health_system.pharma_industry`. | placebo-controlled trial; EUA; Operation Warp Speed; ACIP committee; VRBPAC |
| efficacy_response | Vaccine effectiveness & immune response | How well vaccines work in general, what affects the immune response to them, and vaccination programmes and funding as a whole. | vaccine effectiveness; immune response to vaccines; sleep and vaccine response; antibody response; Gavi; vaccination programme funding |

#### COVID-19 & Pandemic Response `covid`
SARS-CoV-2, COVID-19 illness and the pandemic response other than vaccines. COVID vaccines go to `vaccines.covid_vaccines`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| illness_severity | COVID illness & severity | COVID-19 as an illness: who gets sick and how badly, symptoms, risk factors, variants, hospitalizations, death rates, reinfection, immunity after infection. Anything taken or done to prevent or treat it goes to `covid.treatments`. | COVID symptoms; IFR; comorbidities; natural immunity after infection; COVID deaths; Omicron; Delta variant |
| origins | Origins of SARS-CoV-2 | Where the virus came from: lab leak, natural spillover, wet market, gain-of-function research, EcoHealth, the Wuhan Institute of Virology. | lab leak; Wuhan lab; gain of function; EcoHealth Alliance; wet market; Proximal Origin |
| treatments | COVID treatments & early treatment | Anything taken or done to prevent or treat COVID-19, or claimed to worsen it, and fights over them. | ivermectin; hydroxychloroquine; Paxlovid; remdesivir; monoclonal antibodies; ventilators; early treatment protocol; vitamin D and zinc for COVID; diet to prevent COVID; ibuprofen and COVID |
| masks_distancing | Masks, distancing & quarantine | Non-pharmaceutical measures applied to people: masks, social distancing, and individual quarantine and isolation rules. Stay-at-home and closure measures go to `covid.lockdowns_closures`. | mask mandates; N95; cloth masks; six feet; quarantine; isolation period |
| lockdowns_closures | Lockdowns & school closures | Lockdowns, stay-at-home orders, business and school closures and their costs. Individual quarantine and isolation rules go to `covid.masks_distancing`. | lockdown; school closures; learning loss; shutdowns |
| testing_counting | Testing & case/death counting | PCR and rapid testing, case counts, how deaths were attributed ("with" vs "from"), hospital incentives. | PCR cycle threshold; rapid test; died with COVID; case counts |
| long_covid | Long COVID | Persistent symptoms after COVID-19 infection, its existence, mechanisms and treatment. | long COVID; long haulers; post-COVID syndrome |
| pandemic_institutions | Pandemic leadership & accountability | How institutions and officials ran the pandemic and were held to account: Fauci, CDC/NIH/WHO decisions, Great Barrington Declaration, inquiries, pardons, future pandemic preparedness and treaties. | Fauci; Great Barrington; WHO pandemic treaty; COVID inquiry; pandemic preparedness |

#### Infectious Diseases & Outbreaks (non-COVID) `infectious`
Infections other than COVID-19: diseases, outbreaks, transmission and treatment. General talk about "infections" takes this parent. Vaccines against them go to `vaccines`. STIs and HIV go to `sexual.stis_hiv`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| measles | Measles | Measles as a disease and its outbreaks, complications and treatment. | measles outbreak; West Texas outbreak; measles deaths; vitamin A for measles; measles parties |
| influenza_avian | Influenza & avian flu | Seasonal influenza and avian/pandemic flu as diseases. | flu season; H5N1; bird flu; avian flu in cattle; Tamiflu |
| emerging_outbreaks | Emerging & exotic outbreaks | Outbreaks of emerging, rare or exotic pathogens and pandemic threats other than flu. | Ebola; Marburg; hantavirus; mpox; Disease X; New World screwworm; Nipah |
| foodborne | Foodborne illness | Infections and poisonings from food. | E. coli; Salmonella; Listeria; food poisoning; botulism; raw-milk pathogens; Cyclospora |
| respiratory_common | Common respiratory infections | Everyday respiratory infections. | common cold; RSV; whooping cough; strep throat; pneumonia; sinus infection |
| vector_borne | Vector-borne infections | Infections carried by ticks, mosquitoes and other vectors, including acute Lyme disease. Chronic Lyme as a contested illness goes to `chronic_complex.chronic_lyme`. | Lyme disease; tick bites; West Nile; dengue; malaria; Zika |
| parasitic_infections | Parasitic infections (clinical) | Parasitic infections and claims about their prevalence or diagnosis, including fringe diagnostics, and on-label antiparasitic drugs. Protocols or products to expel parasites go to `detox.parasite_cleanses`; an ad with both takes both. | worms; pinworms; giardia; tapeworm; scabies; toxoplasmosis; live blood test for parasites; antiparasitic drugs (on-label) |
| antibiotics_resistance | Antibiotics & resistance | Antibiotic use and overuse, side effects, resistance, superbugs. | antibiotics; overprescribing; C. diff; MRSA; superbugs; antibiotic resistance |
| germ_theory_hygiene | Germs, hygiene & germ theory | Contagion and hygiene as subjects: handwashing, sanitation, the hygiene hypothesis, and germ theory versus terrain theory as an argument. | germ theory; terrain theory; hygiene hypothesis; handwashing; sanitizer; contagion |
| other_infections | Other infections | A named infection not listed above. | tuberculosis; hepatitis C; sepsis from infection; fungal infection; staph infection; UTI as infection |

### Domain: Nutrition, diet & supplements `nutrition`

#### Foods, Nutrients & Food Quality `food`
Foods, drinks and nutrients as eaten, and the quality and safety of the food supply. A named dietary pattern goes to `diets`; a nutrient taken as a pill, powder or dose goes to `supplements`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| ultra_processed | Ultra-processed & processed food | Processed and ultra-processed foods, fast food and junk food, food engineering and hyperpalatability. | ultra-processed food; UPF; junk food; fast food; bliss point; "food-like products" |
| sugar_sweeteners | Sugar & sweeteners | Sugar, fructose and syrups, and non-sugar sweeteners. | sugar; high-fructose corn syrup; fructose; aspartame; sucralose; stevia; monk fruit; sugar alcohols |
| fats_oils | Fats & cooking oils | Dietary fats and oils: seed and vegetable oils, saturated fat, trans fat, dietary cholesterol, butter, tallow, olive oil, frying. | seed oils; canola; soybean oil; saturated fat; trans fats; dietary cholesterol; beef tallow (as food); olive oil; ghee |
| meat_animal_foods | Meat, eggs & fish | Meat, poultry, eggs, fish and organ meats as foods, and their health effects. | red meat; processed meat; eggs; organ meats; liver; sardines; grass-fed beef |
| dairy_raw_milk | Dairy & raw milk | Milk and dairy products as food, including raw (unpasteurized) milk and whole milk. | raw milk; pasteurization; whole milk; cheese; A2 milk; dairy intolerance |
| grains_carbs_gluten | Grains, carbohydrates & gluten | Grains, bread, flour, gluten as a food component, and carbohydrates as a macronutrient. | gluten; wheat; refined flour; bread; rice; carbs; glycemic load |
| protein_intake | Protein intake | How much protein people need and where they get it from food, including protein bars. Protein powders go to `supplements.protein_powders`. | protein targets; grams per pound; protein-maxxing; amino acids from food; leucine threshold; protein bars |
| plant_foods_fiber | Fruits, vegetables, fiber & plant compounds | Produce, legumes, nuts and seeds, fiber, soy, and plant compounds said to help or harm. | vegetables; fruit; fiber; fibermaxxing; legumes; soy; oxalates; lectins; polyphenols; cruciferous |
| additives_dyes | Additives, dyes & preservatives | Specific food additives, including their regulation and bans and the GRAS process for food. Cross-product regulatory philosophy goes to `policy.regulation_chemicals_food_drugs`. | food dyes; Red 40; titanium dioxide; preservatives; emulsifiers; MSG; GRAS; "banned in Europe" ingredients |
| organic_gmo | Organic, GMO & farming practices | How food is produced as a health question: organic versus conventional, GMOs, regenerative agriculture, soil quality. Pesticide residue in food goes to `food.food_contaminants`. | organic; GMO; regenerative farming; soil depletion; grass-fed vs grain-fed; bioengineered |
| beverages_hydration | Water, hydration & beverages | Drinking water as hydration, electrolytes in drinks, soda, juice, and "wellness waters". Caffeine goes to `stimulants`; alcohol to `alcohol`; electrolyte powders to `supplements.other_vitamins_minerals`. | hydration; how much water; soda; juice; alkaline water; structured water; hydrogen water; mineral water |
| micronutrients_food | Vitamins & minerals from food | Vitamins and minerals from named food sources, nutrient density, and deficiency diseases explained through diet. Nutrient status (levels, deficiency, testing, "you need more X") with no form stated goes to the nutrient's `supplements` subtopic. | vitamin C in fruit; scurvy; iron-rich foods; nutrient density; bioavailability |
| eating_behavior | Eating behavior, appetite & cravings | When and how people eat: meal timing, breakfast, snacking, cravings, food addiction, mindful or intuitive eating. Named fasting regimens go to `diets.fasting`. | skipping breakfast; cravings; food addiction; satiety; snacking; intuitive eating |
| food_system_access | Food system, access & school food | The food system and access to food as health issues: school meals, food deserts, food assistance, food prices, agriculture policy, the food industry's structure. | school lunch; SNAP; food deserts; food insecurity; farm subsidies |
| food_contaminants | Contaminants in food | Any unintended contaminant in a specific food: heavy metals, microplastics, mold or pesticide residue. Add `environment.pesticides_herbicides` when the chemical's health effects are discussed; contaminants in general go to `environment`. | heavy metals in baby food; lead in cinnamon; mycotoxins in coffee; arsenic in rice; microplastics in bottled water; pesticide residue on produce |
| general_nutrition | General nutrition & healthy eating | Healthy eating, "real food", balanced diet, food as medicine, and macronutrient balance in general, with no specific food, nutrient or named diet. | eating healthy; well-balanced diet; eat real food; food as medicine; healthy eating; fat and carb balance |

#### Named Diets & Eating Patterns `diets`
Named dietary patterns, protocols and the identities around them. A single food or nutrient on its own merits goes to `food`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| low_carb_keto | Low-carb & ketogenic | Low-carbohydrate and ketogenic diets and ketosis. | keto; ketosis; low-carb; Atkins; ketones |
| carnivore_animal_based | Carnivore & animal-based | All-meat and animal-based diets. | carnivore diet; animal-based; lion diet; beef and butter |
| plant_based | Vegan, vegetarian & plant-based | Diets excluding or minimizing animal foods. | vegan; vegetarian; plant-based; whole-food plant-based |
| fasting | Fasting & time-restricted eating | Intermittent, extended and water fasting, time-restricted eating, fasting-mimicking diets, one meal a day. | intermittent fasting; 16:8; OMAD; water fast; fasting-mimicking |
| ancestral_paleo | Paleo, ancestral & traditional diets | Diets defined by an ancestral or traditional ideal. | paleo; ancestral diet; Weston A. Price; traditional foods; "eat like your great-grandmother" |
| mediterranean_whole_food | Mediterranean & whole-food patterns | Mediterranean, DASH, Blue Zones and named "whole foods" eating patterns. Healthy eating with no named pattern goes to `food.general_nutrition`. | Mediterranean diet; DASH; Blue Zones diet; whole-food diet |
| elimination_therapeutic | Elimination & therapeutic diets | Diets that remove foods to treat symptoms or conditions. | elimination diet; low-FODMAP; AIP; gluten-free (as a regimen); anti-inflammatory diet; low-histamine; GAPS |
| calorie_counting | Calorie & macro counting | Dieting by calories or macronutrient targets. | calories in calories out; macro tracking; calorie deficit; counting points |
| raw_food_juicing | Raw-food & juicing diets | Diets built on raw foods or juices, and the "living food" ideas behind them. | raw vegan; raw food diet; juice fasting as a diet; fruitarian; living foods |

#### Supplements, Vitamins & Nutraceuticals `supplements`
Products taken as pills, powders, drinks or doses: what they contain, what they are claimed to do, dosing and quality, and a nutrient's levels, deficiency or testing when no form is stated. The subtopic follows the substance (L-tyrosine is an amino acid wherever it is taken for); code the outcome it is used for as well when the passage discusses that outcome (e.g. melatonin for sleep also takes `sleep`).

| id | name | definition | examples |
| --- | --- | --- | --- |
| vitamin_d | Vitamin D | Vitamin D supplements and dosing, and vitamin D levels and deficiency when no form is stated. Vitamin D made from sunlight also takes `radiation_light.sunlight_uv`. | vitamin D3; 5,000 IU; vitamin D levels; D3 with K2; vitamin D deficiency |
| magnesium | Magnesium | Magnesium supplements and forms. | magnesium glycinate; magnesium threonate; magnesium deficiency |
| b_vitamins_methylation | B vitamins, folate & methylation | B-vitamin supplements, folate and methylfolate, and methylation-driven supplementation including MTHFR. Leucovorin for autism takes this and `neurodevelopment.autism_treatment`. | B12; methylfolate; folic acid; MTHFR; methylated vitamins; leucovorin (as folate) |
| vitamin_c | Vitamin C | Vitamin C supplements, including high doses and IV vitamin C outside cancer treatment. | vitamin C megadose; liposomal vitamin C; IV vitamin C |
| other_vitamins_minerals | Other vitamins, minerals & electrolytes | Any other vitamin or mineral supplement, multivitamins and electrolyte products. | zinc; iron; iodine; selenium; vitamin A; vitamin K2; multivitamin; electrolyte powder; LMNT; potassium |
| omega3 | Omega-3 & fish oil | Fish oil, krill oil and omega-3 supplements, and omega-3 status with no form stated. | fish oil; EPA/DHA; krill oil; omega-3 index |
| creatine | Creatine | Creatine supplementation for any purpose. | creatine monohydrate; loading phase; creatine for the brain |
| protein_powders | Protein powders, collagen & amino acids | Protein powders, collagen supplements and amino-acid products, including single amino acids taken as supplements. Protein bars go to `food.protein_intake`. | whey; collagen peptides; BCAAs; EAAs; glycine; L-tyrosine; taurine |
| greens_whole_food | Greens & whole-food powders | Greens powders and encapsulated fruit-and-vegetable products. A whole-fruit powder taken for one nutrient (camu camu for vitamin C) goes to that nutrient's subtopic. | AG1; greens powder; Balance of Nature; superfood blends |
| herbal_adaptogens | Herbal, fungal, algal & bee supplements | Botanical, fungal, algal and bee-derived supplements. | ashwagandha; turmeric/curcumin; berberine; medicinal mushrooms; lion's mane; sea moss; rhodiola; black seed oil; colostrum; shilajit; spirulina; chlorella; propolis; royal jelly; bee pollen |
| organ_glandular | Organ & glandular supplements | Desiccated organ and glandular products. | beef liver capsules; desiccated organs; glandulars; Heart & Soil |
| other_compounds | Other compounds & enzymes | Non-botanical supplement compounds not covered above: antioxidants, phospholipids, enzymes and similar. | glutathione; NAC; CoQ10; alpha-lipoic acid; PQQ; quercetin; phosphatidylcholine; phospholipids; urolithin A; L-carnitine; digestive enzymes; proteolytic enzymes; serrapeptase |
| sleep_mood_supplements | Sleep, calm & mood supplements | Supplements taken for sleep, calm or mood. | melatonin; L-theanine; GABA; 5-HTP; valerian; saffron; kava |
| industry_quality | Supplement industry, quality & regulation | Supplements as a category or industry: whether they work in general, third-party testing, contamination, labeling, regulation, multi-level marketing. | supplement regulation; DSHEA; third-party tested; proprietary blend; MLM supplements |

### Domain: Body systems & chronic conditions `conditions`

#### Heart, Blood Pressure & Lipids `cardiovascular`
Cardiovascular and blood health, their markers and drugs. General "heart health" or "cardiovascular health" takes this parent. Diabetes and insulin go to `metabolic`; stroke to `neuro.stroke`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| cholesterol_lipids | Cholesterol & lipids | Blood lipids and lipoproteins and what they mean for heart disease. | LDL; HDL; ApoB; Lp(a); triglycerides; cholesterol hypothesis; lean mass hyper-responders |
| statins_lipid_drugs | Statins & lipid-lowering drugs | Statins and other cholesterol-lowering drugs: benefits, side effects, who should take them. | statins; Lipitor; Crestor; ezetimibe; Zetia; PCSK9 inhibitors |
| blood_pressure | Blood pressure | Hypertension and blood pressure control. | high blood pressure; hypertension; BP medication; salt and blood pressure |
| heart_disease | Heart disease & cardiac events | Coronary and cardiac disease and events and their testing. Vessels elsewhere, endothelium, calcification outside the coronaries and peripheral plaque go to `cardiovascular.blood_circulation`; vaccine-linked myocarditis takes this plus the vaccine subtopic. | heart attack; coronary artery disease; coronary plaque; calcium score; heart failure; AFib; arrhythmia; myocarditis; sudden cardiac arrest; stents |
| blood_circulation | Blood vessels, clots & circulation | Blood vessels outside the heart (endothelium, arterial stiffness and calcification, peripheral artery disease), blood clots, circulation and blood disorders. | DVT; pulmonary embolism; blood clots; circulation; varicose veins; anemia; bleeding disorders; blood thinning; endothelial function; arterial stiffness; arterial calcification; peripheral artery disease; plaque in leg arteries |

#### Blood Sugar, Diabetes & Metabolic Health `metabolic`
Glucose regulation, insulin, diabetes and metabolic dysfunction. Body weight as such goes to `weight`; GLP-1 drugs to `glp1`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| insulin_glucose | Insulin resistance & blood glucose | Insulin resistance, blood-sugar spikes and control, prediabetes, insulin's role in fat storage, and "metabolic health" outside diagnosed diabetes. "Metabolic dysfunction" meaning cellular energy goes to `metabolic.mitochondria_energy`. | insulin resistance; blood sugar spikes; glucose crash; prediabetes; HbA1c; metabolic dysfunction; hyperinsulinemia; insulin as the fat-storage hormone |
| diabetes | Diabetes | Diagnosed type 1 or type 2 diabetes and its management, drugs and complications. Metformin outside diabetes goes to `medications.repurposed_offlabel` plus the condition's subtopic. | type 2 diabetes; type 1; insulin injections; metformin (for diabetes); diabetic neuropathy; diabetes reversal |
| fatty_liver | Fatty liver & liver metabolism | Fatty liver disease and metabolic liver function. Other liver disease goes to `gut.liver_gallbladder`. | NAFLD; MASLD; fatty liver; liver fat; uric acid |
| mitochondria_energy | Mitochondria & cellular energy | Mitochondrial function, ATP and cellular energy production, NAD/PARP metabolism, and "metabolic dysfunction" meaning cellular energy, outside an ageing frame. Mitochondria framed as a cause of ageing go to `longevity.cellular_ageing`. | mitochondrial health; mitochondrial dysfunction; ATP; cell danger response; underpowered cells; PARP; cellular energy |

#### Body Weight & Obesity `weight`
Body weight, fat and body composition. Weight-loss drugs go to `glp1`; named diets to `diets`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| obesity_rates | Obesity & its prevalence | Obesity as a condition and a population trend, and how it is measured. | obesity epidemic; BMI; childhood obesity; obesity rates |
| weight_gain_causes | Causes of weight gain | Why people gain fat or cannot lose it: hormones, stress, sleep, medications, metabolism blamed for weight gain. Where fat sits and what it does goes to `weight.body_composition`. | weight gain; can't lose weight; weight-loss resistance; stubborn belly fat |
| weight_loss_methods | Weight-loss methods (non-drug) | Strategies and programmes for losing fat or weight without drugs or surgery, coaching and results. Any pill, powder or supplement taken for weight loss goes to `weight.diet_pills_fat_burners`. | fat loss; cutting; weight-loss plan; losing 30 pounds; Noom; WeightWatchers |
| body_composition | Metabolism & body composition | Metabolic rate and energy expenditure as such, where fat sits and what it does (visceral fat, fat making estrogen), muscle-to-fat ratio and their measurement. | slow metabolism; energy expenditure; thermic effect of food; visceral fat; body fat percentage; DEXA scan; set point; metabolic adaptation |
| body_image_stigma | Body image & weight stigma | How bodies are judged: body positivity, fatphobia, weight stigma, Health at Every Size. Eating disorders go to `mental.eating_disorders`. | body positivity; fat acceptance; HAES; weight stigma |
| weight_loss_surgery | Bariatric surgery | Surgical weight-loss procedures. | gastric sleeve; gastric bypass; lap band; bariatric surgery |
| diet_pills_fat_burners | Weight-loss pills & supplements (non-GLP-1) | Any pill, powder or supplement taken for weight loss other than GLP-1 drugs: fat burners, diet drugs, slimming teas and supplements. | fat burners; phentermine; skinny tea; detox tea for weight; Hydroxycut; forskolin; weight-loss supplements |

#### GLP-1 & Incretin Drugs `glp1`
GLP-1 and related incretin drugs specifically. Code `weight` or `metabolic` subtopics as well when the passage discusses the weight or diabetes outcome itself.

| id | name | definition | examples |
| --- | --- | --- | --- |
| use_results | GLP-1 use & results | Taking GLP-1 drugs and their weight and glycemic effects in any population: weight loss, who takes them, celebrity use, effects on appetite and cravings. | Ozempic; Wegovy; Mounjaro; Zepbound; semaglutide; tirzepatide; food noise |
| side_effects | GLP-1 side effects & risks | Adverse effects and risks of GLP-1 drugs. | nausea; muscle loss; Ozempic face; gastroparesis; pancreatitis; thyroid cancer warning; suicidality; regain after stopping |
| access_compounding | GLP-1 access, cost & compounding | How people get GLP-1s: prices, insurance, shortages, compounded and telehealth versions, counterfeits. A telehealth service selling GLP-1s takes this alone; add `health_system.dtc_telehealth` only when the DTC or telehealth model itself is discussed. | compounded semaglutide; Hims; telehealth GLP-1; cost per month; shortage list; counterfeit Ozempic |
| new_offlabel_uses | New, microdosed & off-label GLP-1 use | New agents and uses for conditions other than weight and blood sugar (addiction, PCOS fertility, fatty liver, inflammation, longevity), which also take the condition's subtopic; microdosing; oral and next-generation drugs. | microdosing GLP-1; retatrutide; orforglipron; GLP-1 for addiction; GLP-1 for alcohol; GLP-1 for PCOS |
| natural_alternatives | "Natural" GLP-1 alternatives | Foods, supplements and products marketed as substitutes for GLP-1 drugs or as boosting GLP-1 naturally. | berberine "nature's Ozempic"; GLP-1 boosting foods; GLP-1 probiotic; Akkermansia |

#### Digestive Health & Microbiome `gut`
The gut microbiome, digestion and gastrointestinal and liver conditions. General "gut health" takes this parent.

| id | name | definition | examples |
| --- | --- | --- | --- |
| microbiome | Gut microbiome | The gut microbiome: composition, diversity, the gut-brain axis, damage to it, microbiome testing. | gut bacteria; microbiome diversity; gut-brain axis; dysbiosis; stool test |
| probiotics_fermented | Probiotics, prebiotics & fermented food | Probiotic and prebiotic supplements and fermented foods eaten for the gut. | probiotics; prebiotics; kefir; sauerkraut; kombucha; spore-based probiotics |
| leaky_gut | Leaky gut & intestinal permeability | Intestinal permeability as a condition or explanation. | leaky gut; intestinal permeability; zonulin; gut lining |
| digestive_symptoms | Digestive symptoms & functional disorders | Everyday digestive complaints and functional gut disorders. | bloating; constipation; reflux; GERD; heartburn; IBS; SIBO; food intolerance; gas |
| gi_disease | Diagnosed GI disease | Structural or inflammatory gastrointestinal disease. GI cancers go to `cancer`. | Crohn's; ulcerative colitis; celiac disease; diverticulitis; ulcers; gastroparesis (non-GLP-1) |
| candida_histamine | Candida & histamine intolerance | Candida overgrowth and histamine intolerance as explanations for symptoms. | candida overgrowth; yeast overgrowth; histamine intolerance; DAO enzyme |
| liver_gallbladder | Liver, gallbladder & pancreas | Liver, gallbladder and pancreas health other than fatty liver and cleanses. | liver disease; cirrhosis; gallstones; gallbladder removal; bile; pancreatitis; liver enzymes |

#### Immune System, Inflammation & Allergy `immune`
Immune function and its disorders, inflammation, and allergy. A specific organ's autoimmune disease takes that organ's subtopic too (Hashimoto's also takes `endocrine.thyroid`).

| id | name | definition | examples |
| --- | --- | --- | --- |
| immune_function | Immune function & "boosting immunity" | The immune system in general and attempts to strengthen it. | immune system; boost immunity; weak immune system; immune support; T cells |
| inflammation | Inflammation as an explanation | Inflammation invoked as a cause of disease or ageing, or as a property of foods and lifestyles, and markers of it. | chronic inflammation; inflammatory foods; CRP; "inflammation is the root of all disease"; inflammaging; neuroinflammation |
| autoimmune | Autoimmune disease | Diagnosed autoimmune disease and its causes and treatment. Psoriasis also takes `skin_beauty.skin_conditions` and MS also takes `neuro.neurodegenerative`. | autoimmune disease; lupus; rheumatoid arthritis; psoriasis; multiple sclerosis; Hashimoto's (as autoimmune); type 1 (as autoimmune) |
| allergies | Allergies & anaphylaxis | Seasonal, food and drug allergies, anaphylaxis and allergy treatment, including allergy drugs (which take this label alone). | food allergies; peanut allergy; hay fever; EpiPen; anaphylaxis; allergy shots; alpha-gal; antihistamines; allergy nasal spray |

#### Hormones, Thyroid & Adrenal `endocrine`
Endocrine function outside reproductive hormones. Sex hormones go to `womens` or `mens` when the sex is specified, otherwise to `endocrine.hormone_balance`; stress experience and regulation practices to `stress`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| hormone_balance | Hormone balance (general) | Hormones in general, "hormone balance" talk spanning several hormones, and sex hormones discussed with no sex specified. | hormone imbalance; balancing hormones; endocrine system; hormone panel |
| thyroid | Thyroid | Thyroid function and disease and its treatment. | hypothyroidism; Hashimoto's; Graves'; levothyroxine; Armour thyroid; T3/T4; iodine and thyroid |
| cortisol_adrenal | Cortisol & adrenal function | Cortisol as a hormone and adrenal function and disorders. | cortisol levels; adrenal fatigue; adrenal burnout; Addison's; cortisol face; cortisol rhythm |
| other_hormones | Other hormones | Growth hormone, IGF-1, DHEA, pregnenolone, oxytocin, melatonin as a hormone, leptin, ghrelin and similar. A hormone used for physique or performance also takes its `peds` subtopic; insulin goes to `metabolic.insulin_glucose`. | growth hormone; IGF-1; DHEA; pregnenolone; oxytocin; leptin; ghrelin |

#### Kidneys, Bladder & Lungs `kidney_lung`
Kidney, urinary and lung health. Respiratory infections go to `infectious`; allergies to `immune.allergies`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| kidney_urinary | Kidneys & urinary tract | Kidney disease, kidney stones, dialysis, bladder and urinary problems, incontinence. | kidney stones; chronic kidney disease; dialysis; overactive bladder; incontinence |
| lungs_breathing | Lungs & breathing | Lung disease and lung function. | asthma; COPD; emphysema; lung capacity; pulmonary fibrosis; inhalers |

#### Cancer `cancer`
Cancer as a disease: causes, rates, screening, diagnosis and conventional treatment. Alternative remedies go to `cancer_alt`; tobacco, sun or chemical exposures also take their own subtopics.

| id | name | definition | examples |
| --- | --- | --- | --- |
| causes_rates | Cancer causes, risk & rates | What causes cancer and how common it is: carcinogens, risk factors, trends, early-onset cancer, cancer as a "metabolic" disease. | carcinogen; cancer rates rising; cancer in young people; risk factors; metabolic theory of cancer |
| screening_diagnosis | Cancer screening & diagnosis | Detecting cancer: screening tests and diagnostic workups. | mammogram; colonoscopy; PSA test; Pap smear (for cancer); liquid biopsy; Galleri; biopsy; staging |
| conventional_treatment | Conventional cancer treatment | Standard oncology: chemotherapy, radiation, surgery, immunotherapy, targeted drugs, survivorship. | chemotherapy; radiation; mastectomy; immunotherapy; oncologist; remission |
| breast_cancer | Breast cancer | Breast cancer specifically. | breast cancer; BRCA; breast density |
| skin_cancer | Skin cancer | Melanoma and other skin cancers. | melanoma; basal cell; skin checks |
| prostate_cancer | Prostate cancer | Prostate cancer specifically. | prostate cancer; PSA; Gleason score |
| other_specific_cancers | Other named cancers | Any other named cancer type. | colon cancer; pancreatic cancer; leukemia; lymphoma; brain tumor; lung cancer; cervical cancer; thyroid cancer |

#### Alternative Cancer Treatments `cancer_alt`
Non-standard cancer treatments, complementary add-ons to standard care, and refusals of standard care. The suppressed-cure storyline is a narrative (`narrative:cancer_cures_suppressed`).

| id | name | definition | examples |
| --- | --- | --- | --- |
| repurposed_drugs | Repurposed drugs for cancer | Off-label drugs promoted for cancer. | ivermectin for cancer; fenbendazole; mebendazole; metformin for cancer; dipyridamole; repurposed drug cocktails |
| metabolic_dietary | Dietary & metabolic cancer approaches | Diets and fasting presented as treating or starving cancer. Used alongside standard treatment, they go to `cancer_alt.integrative_adjuncts`. | keto for cancer; starving cancer of sugar; press-pulse |
| natural_remedies | Natural & IV cancer remedies | Herbal, vitamin, IV and folk remedies for cancer. | high-dose IV vitamin C; laetrile/B17; apricot seeds; mistletoe; cannabis oil; baking soda; Essiac tea |
| clinics_protocols | Alternative cancer clinics & protocols | Clinics and named protocols outside standard oncology. | Mexico cancer clinic; Gerson therapy; hyperthermia; ozone for cancer; insulin-potentiated therapy |
| refusing_standard_care | Refusing or delaying standard treatment | Choosing to forgo or delay chemotherapy, surgery or radiation, and the outcomes. | refused chemo; declined surgery; chose natural treatment instead |
| integrative_adjuncts | Integrative add-ons to standard cancer care | Complementary therapies used alongside chemotherapy, radiation or surgery (hyperbaric oxygen, supplements, fasting or ketosis around treatment, melatonin), as opposed to replacements for them. | fasting during chemo; hyperbaric with radiation; supplements alongside chemo; melatonin during radiotherapy; integrative oncology |

#### Neurological Conditions `neuro`
Conditions of the brain and nervous system. Dementia goes to `dementia_ageing`; mental-health conditions to `mental`; cognitive performance to `cognition`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| stroke | Stroke & cerebrovascular disease | Stroke, aneurysm and other cerebrovascular events. | stroke; TIA; aneurysm; brain bleed |
| seizures_epilepsy | Seizures & epilepsy | Seizure disorders. | epilepsy; seizures; convulsions; febrile seizure |
| headache_migraine | Headache & migraine | Headaches and migraine. | migraine; cluster headache; tension headache |
| concussion_tbi | Concussion & brain injury | Traumatic brain injury and its long-term effects. | concussion; TBI; CTE; head trauma; blast injury |
| neurodegenerative | Neurodegenerative & movement disorders | Progressive neurological disease other than dementia. MS also takes `immune.autoimmune`. | Parkinson's; ALS; Huntington's; multiple sclerosis |
| nerve_spinal | Nerves, spinal cord & paralysis | Peripheral nerve and spinal cord problems, and neural implants. | neuropathy; spinal cord injury; paralysis; Bell's palsy; sciatica (nerve); nerve damage; neural implants; Neuralink |
| other_neurological | Other neurological conditions | Named neurological conditions not listed above. | restless legs; dystonia; spasmodic dysphonia; essential tremor; tics in adults; syncope; fainting |

#### Dementia, Ageing & Elder Care `dementia_ageing`
Age-related cognitive change and decline, and the care of older people. Longevity protocols go to `longevity`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| dementia_alzheimers | Alzheimer's & dementia | Dementia and Alzheimer's: what it is, causes, diagnosis, drugs, prevention claims. Normal age-related cognitive change goes to `dementia_ageing.cognitive_ageing`. | Alzheimer's; dementia; amyloid; lecanemab; "type 3 diabetes" |
| elder_care | Elder care & frailty | Caring for older people and age-related frailty. | caregiving; nursing home; assisted living; falls in the elderly; frailty |
| cognitive_ageing | Normal cognitive ageing | Age-related cognitive change and mental capacity in older people short of dementia. | cognitive decline with age; fluid intelligence in old age; sharp at 91; senior moments |

#### Pain, Bones, Joints & Muscles `musculoskeletal`
Musculoskeletal pain, injury and rehabilitation. Acute trauma goes to `acute_care`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| back_neck_posture | Back pain, neck pain & posture | Spinal pain and posture. | lower back pain; herniated disc; neck pain; posture; tech neck |
| joints_arthritis | Joints & arthritis | Joint pain and joint disease. | osteoarthritis; knee pain; hip replacement; gout; joint supplements (as joint care) |
| bone_health | Bone health & osteoporosis | Bone density and bone strength. | osteoporosis; bone density; osteopenia; bone loss in menopause |
| sports_injuries | Sports & overuse injuries | Injuries from sport, training or repetitive use, whoever the person, an athlete's unspecified injury, and their rehabilitation. Injuries from a fall, crash or assault go to `acute_care.trauma_fractures`. | ACL tear; Achilles tear from sport; tendonitis; rotator cuff; tennis elbow; hamstring pull; repetitive strain |
| chronic_pain | Chronic pain & pain management | Persistent pain and how it is managed, other than opioids. | chronic pain; pain science; NSAIDs for pain; pain management; fascia pain |
| rehab_manual_therapy | Physical therapy & rehabilitation | Physical therapy, rehabilitation, exercise prescribed to recover from an injury or pain, and conventional manual therapy. General stretching goes to `fitness.mobility_flexibility`; chiropractic to `alt_medicine.chiropractic`. | physical therapy; rehab; massage therapy; dry needling; mobility rehab; stretches for back pain |
| muscle_loss | Muscle mass & sarcopenia | Muscle mass as a health outcome: losing, keeping or building it for health (with age, disuse, fasting or drugs), and muscle as an organ of health. How to train goes to `fitness.strength_training`. | sarcopenia; muscle loss with age; "muscle is the organ of longevity"; building muscle for health |

#### Injuries, Emergencies & End of Life `acute_care`
Acute injury and emergency care, and death and dying. In crime, news or history, a described injury takes `acute_care.trauma_fractures` and a death or its cause `acute_care.death_dying`; a crime named only as "murder" or "killed" is not health content.

| id | name | definition | examples |
| --- | --- | --- | --- |
| wounds_first_aid | Wounds, burns & first aid | Cuts, burns, bites and what is done about them immediately. | stitches; burns; dog bite; first aid; tourniquet; CPR; Heimlich |
| trauma_fractures | Injuries & trauma | Physical injuries from a fall, crash, assault or other non-sport cause, an unspecified injury, and injuries described in news, crime or history. A death or its cause also takes `acute_care.death_dying`. | broken leg; car crash injuries; gunshot wound; shot in the chest; trauma surgery; "I got injured" |
| violence_abuse | Violence & abuse | Interpersonal violence and abuse discussed as a pattern, risk or health and safety issue (sexual assault, domestic violence, child abuse and neglect, gun violence as a public-health matter, elder abuse), including emotional or psychological abuse in relationships as harm. A single crime told as an event takes `acute_care.trauma_fractures` or `acute_care.death_dying`; therapy-speak as a social phenomenon goes to `mental.pop_psychology`. | sexual assault; domestic violence; child abuse; gun violence epidemic; intimate partner violence; strangulation; coercive control; narcissistic abuse |
| emergency_critical_care | Emergency & critical care | Emergency departments, ICUs, sepsis, shock, resuscitation, organ failure. | ER; ICU; sepsis; septic shock; intubation; code blue |
| poisoning_environmental_injury | Poisoning, environmental & motion injury | Poisoning, overdoses of non-drugs-of-abuse, heat stroke, hypothermia, drowning, choking, altitude, G-forces, motion and seasickness. | poisoning; carbon monoxide; heat stroke; hypothermia; drowning; altitude sickness; G-force blackout; seasickness; motion sickness |
| death_dying | Death, dying & end-of-life care | How people die and end-of-life care: causes of death as medical fact, autopsies, hospice, euthanasia and assisted dying. | cause of death; autopsy; hospice; palliative care; MAID; assisted suicide; sudden death |

#### Surgery & Medical Procedures `procedures`
Operations, clinical procedures, clinical lab tests and blood or cell therapies that are not cosmetic, weight-loss or cancer-specific.

| id | name | definition | examples |
| --- | --- | --- | --- |
| surgery_hospital | Surgery & hospital stays | Operations, recovery and the experience of being hospitalized. | surgery; operation; post-op; hospital stay; knee surgery; appendectomy |
| anesthesia | Anesthesia | Anesthesia and sedation. | general anesthesia; epidural (outside birth); sedation; waking up during surgery |
| transplants_donation | Transplants & donation | Organ and tissue transplant and blood or organ donation. | kidney transplant; organ donor; blood donation; bone marrow |
| imaging_diagnostics | Imaging & diagnostic procedures | Medical imaging and diagnostic procedures outside cancer screening, and radiation dose from them. Blood and lab tests go to `procedures.lab_testing`. | MRI; CT scan; X-ray; endoscopy; ultrasound |
| lab_testing | Clinical lab testing & blood work | Clinician-ordered blood and lab tests, panels, reference ranges and their interpretation. Tests a consumer orders or buys directly go to `self_tracking.consumer_lab_tests`. | blood work; lab panel; reference ranges; normal labs; fasting insulin test; serology; doctor-ordered blood test |
| regenerative_medicine | Regenerative medicine (non-cosmetic) | Stem-cell, platelet, exosome and similar therapies, and supplements claimed to mobilize stem cells, used for healing, orthopedic or systemic disease rather than appearance. | stem cell therapy for joints; PRP for tendons; exosomes for recovery; stem cells in Mexico or Panama; stem cell supplements |
| blood_cell_therapies | Blood, plasma & cell therapies | Therapeutic plasma exchange, transfusion, cord-blood banking and cell infusions (NK cells), conventional or experimental. Used as a longevity protocol, they also take `longevity.protocols_clinics`. | plasma exchange; blood transfusion; cord blood banking; NK cell infusion; therapeutic apheresis |

#### Eyes, Ears & Senses `sensory`
The senses and their loss, correction and aids.

| id | name | definition | examples |
| --- | --- | --- | --- |
| vision | Vision & eye health | Eyes and sight. | myopia; glasses; contacts; LASIK; cataracts; glaucoma; macular degeneration; eye strain; sunglasses |
| hearing | Hearing & tinnitus | Hearing and ears. | hearing loss; tinnitus; hearing aids; cochlear implant; ear infections |
| smell_taste_ent | Smell, taste, nose & throat | Smell, taste and ear-nose-throat structures. | anosmia; loss of taste; sinus; deviated septum; tonsils; nasal polyps |

#### Oral & Dental Health `oral`
Teeth, gums and the mouth, including fluoride.

| id | name | definition | examples |
| --- | --- | --- | --- |
| water_fluoridation | Water fluoridation | Fluoride added to public water: its effects and the policy fights over it. | community water fluoridation; fluoride in tap water; removing fluoride; fluoride and IQ studies |
| fluoride_products | Fluoride & fluoride-free dental products | Fluoride toothpaste, varnish and treatments and their alternatives. | fluoride toothpaste; hydroxyapatite; fluoride varnish; fluoride-free toothpaste |
| dental_procedures | Dental procedures & materials | Dental work and dental materials, orthodontics and jaw problems. | root canal; amalgam fillings; mercury fillings; extractions; cavitations; dental implants; braces; TMJ; wisdom teeth |
| oral_hygiene | Oral hygiene & gum health | Cavities, gum disease, the oral microbiome and hygiene practices. | gum disease; cavities; oil pulling; mouthwash; tongue scraping; oral microbiome; bad breath |

#### Genetics & Heredity `genetics`
Heredity and genetic explanation, testing and therapy.

| id | name | definition | examples |
| --- | --- | --- | --- |
| inheritance | Inheritance & genes vs environment | What is inherited and how; genes versus lifestyle; epigenetic inheritance. | hereditary; family history; blood type; recessive; "genes load the gun"; epigenetics |
| genetic_testing | Genetic testing | Genetic and genomic testing, consumer or clinical, and embryo screening. | 23andMe; carrier screening; whole-genome sequencing; polygenic embryo screening; MTHFR test |
| genetic_conditions | Genetic & congenital conditions | Conditions with a genetic or congenital cause. | Down syndrome; cystic fibrosis; sickle cell; birth defects; congenital heart defect |
| gene_therapy | Gene editing & gene therapy | Altering genes to treat or enhance. | CRISPR; gene therapy; gene editing; designer babies |

#### Contested & Complex Chronic Illness `chronic_complex`
Chronic, hard-to-diagnose or contested multi-symptom illnesses and the patient communities around them. Long COVID goes to `covid.long_covid`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| chronic_lyme | Chronic Lyme & co-infections | Lyme disease as a persistent chronic illness and co-infections. | chronic Lyme; Bartonella; Babesia; long-term antibiotics for Lyme |
| me_cfs | ME/CFS & chronic fatigue | Myalgic encephalomyelitis / chronic fatigue syndrome and chronic fatigue as a condition. Everyday tiredness goes to `wellness.energy_fatigue`. | ME/CFS; chronic fatigue syndrome; post-exertional malaise |
| pots_dysautonomia | POTS & dysautonomia | Autonomic dysfunction. | POTS; dysautonomia; orthostatic intolerance |
| mcas_eds | MCAS & Ehlers-Danlos | Mast cell activation syndrome, hypermobility and Ehlers-Danlos syndrome. | MCAS; mast cells; EDS; hypermobility |
| mold_illness | Mold illness & CIRS | Mold or biotoxin illness as a diagnosis. Mold as an indoor exposure goes to `environment.indoor_air_mold`. | mold toxicity; CIRS; mycotoxin illness; Shoemaker protocol |
| fibromyalgia | Fibromyalgia | Fibromyalgia. | fibromyalgia; widespread pain syndrome |
| patient_experience | Living with chronic illness | The experience of chronic, undiagnosed or multiple illnesses: medical gaslighting, diagnostic odysseys, patient communities. | doctors dismissed me; "it's all in your head"; years to diagnosis; spoonie |

### Domain: Mind, brain & behavior `mind`

#### Mental Health & Psychiatry `mental`
Psychiatric conditions, their diagnosis and treatment, and psychological wellbeing. Autism and ADHD go to `neurodevelopment`; stress physiology and regulation practices to `stress`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| depression | Depression | Depression as a condition, when depression or a depressive state is named. Low mood short of that goes to `mental.wellbeing_grief_loneliness`. | depression; major depressive disorder; treatment-resistant depression |
| anxiety | Anxiety & panic | Anxiety disorders and panic. | anxiety; panic attacks; generalized anxiety; social anxiety |
| trauma_ptsd | Trauma & PTSD | Psychological trauma and its effects. | PTSD; CPTSD; childhood trauma; ACEs; trauma response |
| serious_mental_illness | Bipolar, psychosis & schizophrenia | Serious mental illness. | bipolar disorder; psychosis; schizophrenia; mania; delusions |
| ocd_personality | OCD, intrusive thoughts & personality disorders | OCD, intrusive thoughts, and clinically framed personality disorders and traits (pathological lying, narcissistic traits). Insults such as calling someone a "narcissist" are not health content. | OCD; intrusive thoughts; borderline personality disorder; narcissistic personality disorder (as diagnosis); pathological lying |
| suicide_self_harm | Suicide & self-harm | Suicide, suicidal ideation and self-harm. | suicide rates; suicidal ideation; self-harm; 988 |
| eating_disorders | Eating disorders | Eating disorders and disordered eating. | anorexia; bulimia; binge eating; orthorexia; ARFID |
| psychiatric_drugs | Psychiatric medications | Psychiatric drugs: effects, side effects, withdrawal, prescribing. ADHD stimulants go to `neurodevelopment.adhd`. | SSRIs; antidepressants; Lexapro; benzodiazepines; Xanax; antipsychotics; lithium; withdrawal; tapering |
| therapy | Psychotherapy & counseling | Talk therapy of all kinds and access to it. | therapy; CBT; DBT; EMDR; counseling; finding a therapist; BetterHelp |
| wellbeing_grief_loneliness | Wellbeing, mood, grief & loneliness | Psychological wellbeing in general: happiness, loneliness, grief, purpose, resilience, burnout as emotional state, and mood (low or good mood, mood swings, irritability) short of a diagnosed disorder. | loneliness epidemic; grief; happiness; resilience; emotional health; mental wellness; improve your mood; mood swings; irritability |
| pop_psychology | Pop psychology & self-diagnosis | Popular psychological vocabulary (therapy-speak) and self-diagnosis as a social phenomenon. Abuse in a relationship discussed as harm goes to `acute_care.violence_abuse`. | therapy-speak; self-diagnosing on TikTok; attachment styles; trauma bonding; "everyone has ADHD now" |
| behavioral_addictions | Behavioral addictions | Compulsive behaviors treated as addictions. | porn addiction; gambling addiction; phone addiction; gaming addiction; shopping addiction |
| causes_models | Causes & models of mental illness | General theories of what causes mental illness (trauma, perception, inflammation, chemical imbalance, social determinants) not tied to one disorder. | chemical imbalance theory; root of mental illness; social determinants of mental health; poverty and mental illness; biopsychosocial model |

#### Autism, ADHD & Neurodevelopment `neurodevelopment`
Autism, ADHD and other neurodevelopmental conditions.

| id | name | definition | examples |
| --- | --- | --- | --- |
| autism_causes_prevalence | Autism causes & prevalence | Why autism occurs and how common it is: genetics, environmental causes, diagnostic changes, the "autism epidemic", the HHS autism report. | autism rates; 1 in 31; autism causes; diagnostic expansion; autism epidemic |
| autism_treatment | Autism treatment & cure claims | Therapies and claimed treatments or cures for autism. Leucovorin for autism takes this and `supplements.b_vitamins_methylation`. | ABA; leucovorin for autism; chelation for autism; autism diet; "recovered from autism"; stem cells for autism |
| adhd | ADHD | ADHD diagnosis, prevalence and treatment, including stimulant medication. | ADHD; Adderall; Ritalin; Vyvanse; stimulant shortage; ADHD overdiagnosis |
| neurodiversity | Neurodiversity & neurodivergent identity | Neurodivergence as identity, culture and accommodation. | neurodivergent; neurodiversity; masking; autistic identity |
| developmental_delays | Developmental, learning & intellectual disability | Speech, motor and learning delays, learning disabilities and intellectual disability. | speech delay; dyslexia; developmental milestones missed; learning disability; intellectual disability; tics; Tourette's |

#### Stress & Nervous-System Regulation `stress`
Stress as an experience and the practices sold or taught to regulate it. Cortisol as a hormone goes to `endocrine.cortisol_adrenal`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| stress_burnout | Stress & burnout | Stress, chronic stress and burnout and their effects on health. | chronic stress; burnout; stress kills; good stress vs bad stress |
| nervous_system_regulation | Nervous-system regulation | The vocabulary and practices of nervous-system regulation. | vagus nerve; fight or flight; polyvagal; somatic therapy; dysregulated nervous system; tapping |
| breathwork | Breathwork | Breathing practices for stress, performance or healing. Breathing during sleep goes to `sleep.apnea_breathing`. | breathwork; box breathing; Wim Hof breathing; physiological sigh; holotropic breathing |
| meditation_mindfulness | Meditation & mindfulness | Meditation, mindfulness and contemplative practice. | meditation; mindfulness; yoga nidra; NSDR; prayer as practice |
| nature_grounding | Nature exposure & grounding | Time outdoors and contact with the earth as health practices. | grounding; earthing; forest bathing; barefoot; nature time |
| mind_body | Mind-body connection | Emotions, beliefs, social connection and psychological state said to affect physical illness, immunity or recovery (psychoneuroimmunology). | molecules of emotion; isolation weakens immunity; psychoneuroimmunology; emotions and illness; beliefs and healing |

#### Sleep `sleep`
Sleep quality, duration, timing and disorders, and products and practices aimed at them.

| id | name | definition | examples |
| --- | --- | --- | --- |
| sleep_duration_quality | Sleep duration & quality | How much and how well people sleep, naps, and sleep as the outcome of a factor. | eight hours; deep sleep; REM; sleep debt; sleep deprivation; naps |
| insomnia | Insomnia & sleep medication | Trouble falling or staying asleep and its treatment. | insomnia; CBT-I; Ambien; trazodone; sleeping pills |
| apnea_breathing | Breathing, airway & sleep apnea | Breathing during sleep, daytime mouth breathing and airway development. | sleep apnea; CPAP; snoring; mouth taping; nasal breathing at night; mouth breathing; airway development |
| circadian_light | Circadian rhythm & light timing | Body clocks, and light at night or light timing affecting sleep or melatonin. Daytime effects of screens and LED light on the eyes, mood or health go to `radiation_light.artificial_light`. | circadian rhythm; morning sunlight; blue light at night; blue blockers; shift work; jet lag |
| sleep_hygiene_environment | Sleep hygiene & sleep environment | Practices and products for sleep: bedtime routines (children's included) and the bedroom (mattresses, temperature, darkness, noise, devices in bed). Newborn sleep safety goes to `pediatrics.infant_care`. | sleep hygiene; bedroom temperature; mattress; blackout curtains; cooling sheets; Eight Sleep; kids' bedtime routine |

#### Cognitive Performance & Brain Optimization `cognition`
Focus, memory and brain performance in healthy people, and the substances and routines aimed at them. General "brain health" or "brain function" takes this parent.

| id | name | definition | examples |
| --- | --- | --- | --- |
| focus_productivity | Focus & productivity | Concentration, attention and productivity as health topics. | focus; deep work; attention span; flow state |
| nootropics | Nootropics & smart drugs | Substances taken to enhance cognition. Methylene blue for other purposes goes to `medications.repurposed_offlabel`. | nootropics; modafinil; racetams; Alpha Brain; methylene blue for cognition; lion's mane for focus |
| memory_learning | Memory & learning | Memory and learning in healthy people. Age-related change goes to `dementia_ageing.cognitive_ageing`. | memory; learning; neuroplasticity; recall |
| brain_fog | Brain fog | Brain fog as a symptom and its causes. | brain fog; mental fog; can't think clearly |
| neurochemistry_talk | Dopamine & neurotransmitter talk | Popular talk about dopamine, serotonin and other neurotransmitters as levers of behavior. | dopamine detox; dopamine fasting; dopamine hits; serotonin "happy hormone" |
| digital_media_brain | Screens, social media & the brain | Effects of phones, screens and social media on attention, mood and development. Compulsive use as an addiction goes to `mental.behavioral_addictions`. | screen time; social media and teens; smartphones and attention; brain rot |

### Domain: Reproductive, sexual & sex-specific health `reproductive`

#### Women's Hormonal & Gynecological Health `womens`
Female reproductive endocrinology and gynecology across the life course. Pregnancy goes to `pregnancy`; fertility, contraception and abortion to `fertility`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| menstrual_cycle | Menstrual cycle & periods | The cycle and its problems. Age at first period and early puberty go to `pediatrics.puberty_adolescence`. | menstrual cycle; PMS; PMDD; cycle syncing; irregular periods; heavy bleeding; period pain |
| female_hormones | Female sex hormones | Estrogen, progesterone and testosterone in women: levels, ratios and testing in any context except menopause. Prescribed hormones go to `womens.hormone_therapy`; progesterone for conception also takes `fertility.infertility_treatment`. | estrogen dominance; low progesterone; testosterone in women; hormone ratios; DUTCH test (as hormone testing) |
| menopause | Perimenopause & menopause | The menopausal transition and its symptoms, including genitourinary symptoms. | perimenopause; menopause; hot flashes; menopause brain fog; vaginal atrophy; vaginal dryness; GSM |
| hormone_therapy | Menopausal hormone therapy | Prescribed hormones for menopause and testosterone for women, including bioidentical hormones. | HRT; MHT; estrogen patch; progesterone; bioidentical hormones; testosterone pellets for women; WHI study; black-box warning |
| pcos | PCOS | Polycystic ovary syndrome. | PCOS; polycystic ovaries |
| gynecological_conditions | Gynecological conditions & care | Other gynecological conditions and care, including vaginal atrophy or dryness outside menopause. | endometriosis; fibroids; ovarian cysts; yeast infection; vaginal microbiome; Pap smear (routine care); pelvic pain; vaginal dryness |
| period_products | Period products & their safety | Tampons, pads, cups and claims about their contents. | tampons; heavy metals in tampons; organic pads; menstrual cup; toxic shock |
| pelvic_floor | Pelvic floor | Pelvic floor function and therapy in any sex. | pelvic floor; Kegels; pelvic floor therapy; prolapse |

#### Pregnancy, Birth & Postpartum `pregnancy`
From conception onward: pregnancy, birth, the postpartum period and infant feeding.

| id | name | definition | examples |
| --- | --- | --- | --- |
| pregnancy_health | Pregnancy health & complications | Prenatal care and complications of pregnancy. | prenatal care; gestational diabetes; preeclampsia; miscarriage; morning sickness; prenatal vitamins |
| exposures_in_pregnancy | Medications & exposures in pregnancy | What is safe to take or encounter while pregnant. | Tylenol in pregnancy; SSRIs in pregnancy; alcohol in pregnancy; fish and mercury in pregnancy; vaccines in pregnancy |
| birth_delivery | Birth & delivery | How babies are born and the choices around it. | C-section; home birth; freebirth; midwife; doula; epidural; induction; birth trauma |
| postpartum | Postpartum | The postpartum period. | postpartum depression; postpartum recovery; placenta encapsulation; fourth trimester; diastasis recti |
| infant_feeding | Breastfeeding & formula | Feeding infants milk. | breastfeeding; formula; donor milk; seed oils in formula; tongue tie |
| maternal_mortality_access | Maternal mortality & maternity care access | Maternal deaths and access to maternity care. | maternal mortality; maternity care deserts; obstetric violence |

#### Fertility, Contraception & Abortion `fertility`
Getting and not getting pregnant: fertility and its treatment, contraception, abortion, and birth rates.

| id | name | definition | examples |
| --- | --- | --- | --- |
| infertility_treatment | Infertility & fertility treatment | Female or couple infertility and assisted reproduction. | infertility; IVF; egg freezing; IUI; ovarian reserve; AMH |
| male_fertility | Male fertility & sperm | Sperm health and male infertility. | sperm count; sperm quality; male infertility; sperm decline |
| conception_general | Conception & general fertility | How conception works, age-related fertility decline, and nutrition or lifestyle "for fertility", outside clinical infertility. | how conception works; fertility declines with age; eating for fertility; trying to conceive; sperm and egg |
| contraception | Contraception | Birth control of any kind, including hormonal contraceptives taken for acne or PCOS. | the pill; IUD; implant; condoms; vasectomy; natural family planning; fertility awareness; the pill for acne |
| abortion | Abortion | Abortion procedures, pills, safety and the law. | abortion; mifepristone; misoprostol; abortion pill; Roe; Dobbs; abortion bans |
| birth_rates | Birth rates & demographics | Falling birth rates and pronatalism as health or social questions. | birth rate decline; fertility rate; pronatalism; population collapse |

#### Sexual Health & STIs `sexual`
Sexual function and sexually transmitted infections.

| id | name | definition | examples |
| --- | --- | --- | --- |
| stis_hiv | STIs & HIV | Sexually transmitted infections and HIV, prevention and treatment. | HIV; AIDS; PrEP; herpes; syphilis; chlamydia; HPV infection |
| sexual_function | Sexual function & libido | Desire, arousal and performance in any sex. | erectile dysfunction; Viagra; libido; low sex drive; orgasm; sexual pain |

#### Men's Hormonal & Urological Health `mens`
Male hormones and male-specific organs. Male fertility goes to `fertility.male_fertility`; sexual function to `sexual.sexual_function`; hair loss to `skin_beauty.hair_loss_hair`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| testosterone | Testosterone & TRT | Testosterone levels, decline, boosting and replacement therapy in men. | low T; TRT; testosterone boosters; declining testosterone; estrogen in men; enclomiphene |
| prostate | Prostate health | Non-cancer prostate health. | enlarged prostate; BPH; prostate exam; frequent urination |
| genital_health | Testicular & penile health | Testicular and penile health. | testicles; varicocele; circumcision; Peyronie's |

#### Masculinity Subcultures & Looksmaxxing `manosphere`
Health and body practices drawn from online masculinity subcultures, and their vocabulary.

| id | name | definition | examples |
| --- | --- | --- | --- |
| semen_retention_nofap | Semen retention & NoFap | Abstaining from ejaculation or masturbation for claimed health benefits. | semen retention; NoFap; no nut November; monk mode |
| looksmaxxing | Looksmaxxing & appearance hacks | Practices to change facial or bodily appearance. | looksmaxxing; mewing; bone smashing; jawline; heightmaxxing; leg lengthening |
| masculinity_ideology | Masculinity ideology & health | Red-pill / alpha framing of male health and "soy boy" style rhetoric about men's bodies. | alpha male; red pill; black pill; soy boys; "men are being feminized" |
| male_body_image | Male body image & muscle dysmorphia | Pressure on men's bodies and muscle dysmorphia. | bigorexia; muscle dysmorphia; male body image |

#### Transgender & Gender-Affirming Care `gender`
Gender-affirming care, transgender health and debates over them.

| id | name | definition | examples |
| --- | --- | --- | --- |
| youth_gender_medicine | Gender medicine for minors | Any intervention for minors, social transition included: puberty blockers, cross-sex hormones and surgery, and laws and reviews concerning them. Add `gender.gender_identity_science` when whether children can know or should be affirmed is also argued. | puberty blockers; Cass Review; gender clinics for children; bans on youth transition; social transition |
| adult_transition | Adult transition care | Hormones and surgery for transgender adults. | HRT for trans adults; top surgery; bottom surgery |
| detransition | Detransition & regret | Detransition and regret after transition. | detransitioners; regret rates |
| gender_identity_science | Gender identity & dysphoria (explanations) | What gender dysphoria is, why it occurs, its prevalence and diagnosis, whether children can know or should be affirmed, and desistance. | gender dysphoria; ROGD; social contagion; intersex; brain sex; desistance |
| lgbtq_health | LGBTQ health & disparities | Health issues and disparities of LGBTQ people outside transition care. A specific condition (suicide, HIV) also takes its own subtopic. | LGBTQ mental health; conversion therapy; trans suicide statistics |

### Domain: Substances `substances`

#### Illicit Drugs, Opioids & Addiction `drugs_addiction`
Drugs of misuse other than alcohol, nicotine, caffeine, cannabis and psychedelics, and addiction and recovery from any substance.

| id | name | definition | examples |
| --- | --- | --- | --- |
| opioids_fentanyl | Opioids & fentanyl | Opioid use, prescribing and overdose when opioids are named. | fentanyl; heroin; OxyContin; Purdue; pill mills; xylazine |
| stimulants_illicit | Cocaine & methamphetamine | Illicit stimulant use. | meth; cocaine; crack |
| addiction_recovery | Addiction & recovery | Addiction as a condition and its treatment, from any substance, when addiction or treatment is discussed. | addiction; rehab; AA; 12 steps; Suboxone; methadone; relapse; sobriety (drugs) |
| harm_reduction | Harm reduction | Reducing the harms of ongoing drug use. | Narcan; naloxone; safe supply; needle exchange; fentanyl test strips; safe injection site |
| drug_policy | Drug policy, supply & overdose crisis | Drug laws, enforcement, trafficking and supply, and overdose counts and trends (add `drugs_addiction.opioids_fentanyl` only when opioids are named). The drugs' effects go to the drug's own subtopic. | overdose deaths; decriminalization; war on drugs; Measure 110; cartels; precursor chemicals; border fentanyl |

#### Cannabis, Psychedelics & Novel Psychoactives `psychoactives`
Cannabis, psychedelics and other psychoactive substances, therapeutic or recreational.

| id | name | definition | examples |
| --- | --- | --- | --- |
| cannabis | Cannabis & cannabinoids | Cannabis, THC, CBD and hemp products. | marijuana; THC; CBD; delta-8; edibles; cannabis psychosis; legalization |
| psychedelic_therapy | Psychedelics & psychedelic therapy | Psychedelics recreationally or therapeutically. | psilocybin; magic mushrooms; MDMA therapy; LSD; ayahuasca; ibogaine; DMT; 5-MeO-DMT |
| ketamine | Ketamine | Ketamine and esketamine, clinical or recreational. | ketamine therapy; Spravato; ketamine infusion |
| microdosing | Microdosing | Taking sub-perceptual doses of psychedelics. | microdosing psilocybin; microdosing LSD |
| novel_substances | Kratom & novel substances | Kratom and other legal-high or novel substances. | kratom; 7-OH; phenibut; tianeptine; nitrous oxide; poppers |

#### Alcohol `alcohol`
Alcohol and its effects, drinking culture and sobriety.

| id | name | definition | examples |
| --- | --- | --- | --- |
| health_effects | Health effects of alcohol | What alcohol does to the body. | alcohol and cancer; "no safe amount"; liver damage; red wine and heart; hangovers |
| drinking_culture | Drinking culture & moderation | How and why people drink, cutting back, sober-curious culture. | Dry January; sober curious; binge drinking; drinking less |
| alcohol_use_disorder | Alcohol use disorder | Alcoholism and its treatment. | alcoholism; alcohol use disorder; withdrawal; naltrexone |
| alternatives | Alcohol alternatives | Non-alcoholic drinks and products marketed instead of alcohol. | non-alcoholic beer; mocktails; kava drinks; THC seltzers |

#### Nicotine, Caffeine & Stimulant Drinks `stimulants`
Nicotine products, caffeine and energy drinks.

| id | name | definition | examples |
| --- | --- | --- | --- |
| smoking | Smoking | Cigarettes, cigars and smoking. | cigarettes; smoking; quitting smoking; cigars |
| vaping | Vaping | E-cigarettes and vaping. | vaping; Juul; e-cigarettes; disposable vapes |
| nicotine_products | Nicotine pouches & nicotine as a nootropic | Nicotine without smoking. | Zyn; nicotine pouches; nicotine gum; nicotine for focus |
| caffeine | Coffee, tea & caffeine | Caffeine and the drinks that carry it. | coffee; caffeine; tea; matcha; caffeine timing |
| energy_drinks | Energy drinks & pre-workout | Energy drinks and stimulant pre-workouts. | energy drinks; Celsius; Prime; pre-workout |

### Domain: Medicine & the health system `medicine_system`

#### Medications (not covered elsewhere) `medications`
Prescription and over-the-counter drugs not covered by a more specific subtopic (statins, GLP-1s, psychiatric drugs, ADHD stimulants, antibiotics, hormone therapy and contraception each have their own).

| id | name | definition | examples |
| --- | --- | --- | --- |
| pain_relievers | Pain relievers | Over-the-counter pain relievers and NSAIDs outside pregnancy. | Tylenol; acetaminophen; ibuprofen; Advil; aspirin |
| overmedication | Overmedication & side effects | Drugs in general: overprescribing, polypharmacy, side effects, drug dependence, recalls. | overmedicated; pills for everything; side effects; polypharmacy; drug recall; black-box warning |
| repurposed_offlabel | Repurposed & off-label drugs (general) | Off-label or repurposed drug use not covered by COVID or cancer, including metformin outside diabetes and methylene blue outside cognition (plus the condition's subtopic). | ivermectin (off-label); low-dose naltrexone; metformin off-label; methylene blue; DMSO (as drug) |
| other_drugs | Other named medications | Any other named drug or drug class, including therapeutic Botox and biologics. Allergy drugs go to `immune.allergies`. | blood thinners; PPIs; steroids (medical); Accutane; Botox for migraine; biologics; Tremfya |

#### Health-Care System & Medical Institutions `health_system`
Medicine's institutions, costs, incentives and practitioners discussed as subjects. Distrust expressed as rhetoric is coded on the frame axis instead.

| id | name | definition | examples |
| --- | --- | --- | --- |
| costs_insurance | Costs & insurance | What care costs and who pays. | health insurance; claim denials; UnitedHealthcare; Medicaid; Medicare; ACA; medical debt; drug prices |
| pharma_industry | Pharmaceutical & health-product industry | Drug, vaccine, formula, consumer-health, device and supplement companies as actors: marketing, lawsuits, profits, lobbying, TV drug ads, vaccine-maker economics. | Pfizer settlement; pharma ads; drug company lobbying; Purdue (as company); Abbott formula records; Kenvue |
| doctors_profession | Doctors & the medical profession | Physicians and their training, incentives and trustworthiness as a subject. | medical school; doctors don't learn nutrition; doctor burnout; physician trust; second opinions |
| hospitals_access | Hospitals, clinics & access to care | Where and how care is delivered and who can get it. | hospital closures; wait times; rural hospitals; primary care shortage; urgent care |
| regulators | Health regulators & agencies | FDA, CDC, NIH, CMS, WHO and other agencies as institutions (approvals, inspections, labeling, guidance, funding, staffing, reform). Vaccine-specific committee work goes to `vaccines.development_approval`; dietary guidelines to `policy.public_health_authority`. | FDA approval process; CDC guidance; NIH funding; WHO; revolving door; FDA inspection |
| research_system | Medical research & publishing | How medical science is produced: trials, journals, peer review, retractions, funding sources, replication. | peer review; journal retraction; clinical trial design; industry-funded research; preprints |
| dtc_telehealth | Telehealth, DTC & compounding | Telehealth, DTC companies, concierge medicine, cash-pay clinics, and compounding pharmacies and their regulation for any drug. | Hims & Hers; telehealth; concierge medicine; compounding pharmacy; compounded B12; compounded finasteride |
| medical_errors | Medical errors & malpractice | Harm from medical care. | medical error; malpractice; misdiagnosis; "third leading cause of death"; iatrogenic harm |
| ethics_law_privacy | Medical ethics, law & privacy | Consent, privacy and ethics of medical practice as principles. Prosecutions and lawsuits go to `policy.health_law_courts`. | informed consent; HIPAA; medical ethics; right to try; conscientious objection |
| global_health | Global health & aid | Health in other countries and international health programmes. | USAID; PEPFAR; global health funding; malaria nets; WHO programmes abroad |
| disability_access | Disability & accessibility | Disability as a health-care and social subject: accommodation, accessibility, services and disability rights. | disability rights; wheelchair access; ADA; disability services; accommodations |

#### Health Policy, Politics & Public Health `policy`
Government health policy and the politics of health as subjects. A policy about a subject with its own subtopic (vaccine mandates, fluoridation, food dyes, abortion law, youth gender medicine, drug policy) takes that subtopic; add a `policy` subtopic only when the political process, leadership or movement is itself discussed.

| id | name | definition | examples |
| --- | --- | --- | --- |
| hhs_leadership | HHS leadership & federal health politics | Who runs federal health agencies and what they are doing politically: RFK Jr. as HHS secretary, appointments, firings, reorganizations, hearings. | RFK Jr. confirmation; HHS layoffs; CDC director fired; Senate hearing |
| maha_movement | MAHA movement | Make America Healthy Again as a movement and programme: its figures, report, agenda and coalition. | MAHA report; MAHA moms; Make America Healthy Again commission |
| public_health_authority | Public health authority & guidance | Public health as an institution and practice in general: guidelines (dietary guidelines and their committees included), recommendations, emergency powers, trust in public health. | public health officials; health guidelines; emergency powers; dietary guidelines; Dietary Guidelines Advisory Committee |
| regulation_chemicals_food_drugs | Regulation of chemicals, food & drugs (general) | Regulatory philosophy across products (precautionary principle, EU versus US rules, deregulation) when no product-specific subtopic applies. Specific food additives and the GRAS process go to `food.additives_dyes`. | precautionary principle; EU bans; deregulation; burden of proof |
| health_law_courts | Health laws & court cases | Health legislation, prosecutions and lawsuits not covered by a specific subtopic. | Supreme Court health case; state health law; right-to-try law; HIPAA indictment |
| partisan_politics | Partisan politics of health | Health as an electoral or partisan issue: party positions, campaigns, polls, health in culture-war debates. | Democrats on health care; campaign health promises; health polling |

### Domain: Fitness, performance & optimization `optimization`

#### Exercise & Fitness `fitness`
Exercise itself: modality, dose, programming, technique and fitness metrics.

| id | name | definition | examples |
| --- | --- | --- | --- |
| strength_training | Strength & resistance training | Lifting and resistance training: how to train. Muscle mass as a health outcome goes to `musculoskeletal.muscle_loss`. | weightlifting; hypertrophy; progressive overload; squats; women lifting |
| cardio_endurance | Cardio, endurance & VO2 max | Aerobic training and fitness. | Zone 2; VO2 max; running; marathon; cycling; HIIT |
| daily_movement | Walking & daily movement | Steps, walking and incidental activity, and sitting. | 10,000 steps; walking after meals; rucking; sitting is the new smoking; standing desks |
| mobility_flexibility | Mobility, flexibility, yoga & Pilates | General mobility, stretching and flexibility practice and mind-body exercise. Exercise prescribed to recover from injury or pain goes to `musculoskeletal.rehab_manual_therapy`. | stretching; mobility; yoga; Pilates; tai chi |
| sports_performance | Athletic performance & training | Training and performance of athletes and sport-specific fitness. | athletic performance; training camp; overtraining; sports science |
| exercise_general | Exercise benefits & dose (general) | Exercise in general: how much, why, for whom. | exercise is medicine; minimum effective dose; exercise for longevity |

#### Recovery & Physical Modalities `recovery`
Heat, cold, light, pressure and bodywork modalities used to recover or feel better physically.

| id | name | definition | examples |
| --- | --- | --- | --- |
| cold_exposure | Cold exposure | Cold plunges, ice baths, cryotherapy. | cold plunge; ice bath; cold shower; cryotherapy; Wim Hof (cold) |
| heat_sauna | Heat & sauna | Sauna and heat therapy. | sauna; infrared sauna; hot tub; heat shock proteins |
| red_light | Light therapy & photobiomodulation | Red, near-infrared and blue LED therapy and low-level lasers, for body, skin, acne or hair. | red light therapy; photobiomodulation; red light panel; LED mask; blue light acne mask; laser cap for hair; low-level laser therapy |
| hyperbaric | Hyperbaric oxygen | Hyperbaric oxygen therapy. | hyperbaric chamber; HBOT |
| bodywork_compression | Massage, compression & bodywork tools | Massage devices, compression and bodywork used for recovery. | massage gun; compression boots; foam rolling; percussion |

#### Performance-Enhancing Drugs `peds`
Anabolic and performance drugs used to build muscle or performance.

| id | name | definition | examples |
| --- | --- | --- | --- |
| steroids_sarms | Steroids, SARMs & anabolic agents | Anabolic steroids, SARMs and cycles, myostatin inhibitors, and growth hormone or EPO used for physique or performance (which also take the hormone's home). | steroids; SARMs; anabolic; cycle; PCT; tren; myostatin inhibitors; HGH for muscle; EPO |
| doping_sport | Doping in sport & "natty or not" | Drug use in sport and fitness culture. | doping; drug testing in sport; natty or not; Enhanced Games |
| fat_loss_drugs_ped | Stimulant & fat-loss PEDs | Drugs used to strip fat for physique. | clenbuterol; DNP; ephedrine; T3 for cutting |

#### Peptides & Research Compounds `peptides`
Research peptides and growth-hormone secretagogues. Incretin peptides go to `glp1`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| healing_peptides | Healing & recovery peptides | Peptides used for injury, gut or tissue healing. | BPC-157; TB-500; Wolverine stack |
| gh_secretagogues | Growth-hormone secretagogues | Peptides and compounds to raise growth hormone. | ipamorelin; CJC-1295; sermorelin; tesamorelin; MK-677 |
| other_peptides | Other peptides | Any other research peptide. | GHK-Cu; MOTS-c; thymosin alpha-1; epitalon; Semax; Selank; KPV |
| peptide_sourcing_regulation | Peptide sourcing & regulation | Where peptides come from and how they are regulated. | research chemicals; "not for human consumption"; FDA category 2; compounding ban; gray market |

#### Longevity & Anti-Aging `longevity`
Lifespan and healthspan extension aimed explicitly at ageing.

| id | name | definition | examples |
| --- | --- | --- | --- |
| ageing_science | Ageing & healthspan (general) | How and why we age, lifespan and healthspan as outcomes, and age-reversal studies. | healthspan; lifespan; hallmarks of aging; centenarians; Blue Zones (as longevity); age reversal |
| longevity_drugs | Longevity drugs | Drugs taken to slow ageing. | rapamycin; metformin for longevity; senolytics; acarbose |
| nad_sirtuins | NAD+, NMN & sirtuin compounds | NAD precursors and sirtuin-related compounds, for any purpose; code the outcome separately. | NAD+; NMN; NR; resveratrol; sirtuins; NAD IV; nicotinamide |
| biological_age | Biological age testing | Measuring biological age. | epigenetic clock; biological age test; TruAge; DunedinPACE |
| cellular_ageing | Cellular ageing mechanisms | Cellular processes (autophagy, senescence, telomeres, mitochondria) discussed as levers of ageing. Mitochondria or cellular energy with no ageing frame go to `metabolic.mitochondria_energy`. | mitochondria and ageing; autophagy; telomeres; senescent cells; stem cells (ageing) |
| protocols_clinics | Longevity protocols & clinics | Longevity medicine as a field or practice, named whole-life longevity protocols, personal protocols and the clinics selling them. | Bryan Johnson; Blueprint; Don't Die; longevity clinic; longevity medicine; young blood |

#### Biohacking & Self-Optimization `biohacking`
Self-experimentation and systematic self-optimization as a practice and identity. Where a specific modality is the subject, prefer that modality's subtopic.

| id | name | definition | examples |
| --- | --- | --- | --- |
| practice_culture | Biohacking practice & culture | Biohacking as identity and method. | biohacker; N-of-1; self-experimentation; quantified self; optimal not normal |
| devices_gadgets | Biohacking devices & gadgets | Consumer devices used to optimize the body, other than wearables and recovery modalities. | PEMF mat; vibration plate; neurostimulation; Apollo; light glasses; ozone generator |
| stacks_protocols | Stacks & daily protocols | Combined routines of supplements and practices. | morning routine; supplement stack; daily protocol |

#### Wearables, Self-Tracking & Consumer Testing `self_tracking`
Devices, tests and scans people buy to measure their own bodies.

| id | name | definition | examples |
| --- | --- | --- | --- |
| wearables | Wearables & trackers | Wearable trackers and their metrics. | Oura; Whoop; Apple Watch; Garmin; HRV; recovery score; sleep score |
| glucose_monitors | Continuous glucose monitors | CGMs, including in people without diabetes. | CGM; Levels; Dexcom; Libre; glucose monitor |
| consumer_lab_tests | Consumer lab & functional tests | Lab tests a consumer orders or buys directly, or a functional practitioner's proprietary panel sold to the client. Clinician-ordered tests go to `procedures.lab_testing`. | Function Health; at-home blood test; hormone panel; food sensitivity test; hair mineral analysis; organic acids test; GI-MAP |
| body_scans | Full-body scans & elective imaging | Elective imaging to find disease early. | Prenuvo; full-body MRI; elective CT; DEXA (as screening) |

#### AI & Digital Health Information `digital_health`
Artificial intelligence and online information as sources of health advice.

| id | name | definition | examples |
| --- | --- | --- | --- |
| ai_advice | AI health advice & chatbots | Patients or consumers using AI for health advice, diagnosis or therapy. Clinicians' or institutions' use goes to `digital_health.ai_in_medicine`; take both only when both uses are described. | ChatGPT diagnosis; AI therapist; AI doctor |
| ai_in_medicine | AI in clinical medicine & research | AI used inside medicine, research and regulators. | AI radiology; AI drug discovery; AI at FDA |
| online_health_information | Health information & misinformation | Health information on social media and from influencers, and health misinformation as a subject, online or offline, including its moderation. | TikTok health trends; wellness influencers; YouTube medical misinformation; content moderation of health claims; politicians spreading health misinformation |
| health_apps | Health apps & digital therapeutics | Apps for health other than wearables and therapy services. | health apps; period apps; meditation apps; digital therapeutics |

### Domain: Alternative medicine & detox `alternative`

#### Alternative, Functional & Traditional Medicine `alt_medicine`
Alternative, integrative, traditional and spiritual systems of care and their practitioners and remedies. The anti-mainstream rhetoric that often comes with them is a frame.

| id | name | definition | examples |
| --- | --- | --- | --- |
| functional_medicine | Functional & integrative medicine | Functional and integrative medicine (East-West included) as an approach and profession. Add `alt_medicine.acupuncture_tcm` only when TCM practices are discussed. | functional medicine; integrative doctor; root-cause medicine (as practice); functional lab ranges |
| naturopathy_homeopathy | Naturopathy & homeopathy | Naturopathic and homeopathic practice and remedies. | naturopath; homeopathy; homeopathic remedies |
| chiropractic | Chiropractic | Chiropractic care and claims. | chiropractor; adjustment; subluxation |
| acupuncture_tcm | Acupuncture & Chinese medicine | Acupuncture and traditional Chinese medicine. | acupuncture; TCM; cupping; qi; herbal formulas (TCM) |
| herbalism_traditional | Herbalism, Ayurveda & folk remedies | Herbal, Ayurvedic, Indigenous and folk medicine. | herbalism; Ayurveda; tinctures; folk remedies; soursop tea; castor oil (ingested) |
| energy_spiritual_healing | Energy & spiritual healing | Healing by energy, frequency, faith or ritual. | Reiki; energy medicine; frequency healing; sound healing; crystals; faith healing; prayer healing; exorcism as healing |
| fringe_ingested_remedies | Fringe ingested chemical remedies | Ingesting or applying industrial or household chemicals as remedies. | MMS/chlorine dioxide; borax; turpentine; DMSO; colloidal silver; hydrogen peroxide therapy; urine therapy; kerosene |
| iv_ozone_therapies | IV drips, ozone & infusion therapies | Non-oncology IV vitamin drips, ozone and similar infusions. | IV drip bar; Myers cocktail; ozone therapy; EBOO; glutathione IV |
| essential_oils | Essential oils & aromatherapy | Essential oils used for health. | essential oils; oregano oil; aromatherapy; diffuser |

#### Detox, Cleanses & Parasite Protocols `detox`
Detox, cleanse and antiparasitic protocols as practices: what to take, how and why.

| id | name | definition | examples |
| --- | --- | --- | --- |
| parasite_cleanses | Parasite cleanses | Protocols and products to expel parasites assumed to be present. Prevalence or diagnosis claims go to `infectious.parasitic_infections`. | parasite cleanse; ivermectin as dewormer for everyone; papaya seeds; wormwood; black walnut; full moon cleanse |
| heavy_metal_detox | Heavy-metal detox & chelation | Removing metals from the body. | chelation; heavy metal detox; provoked urine test; cilantro chlorella |
| organ_cleanses | Liver, colon & juice cleanses | A named cleanse protocol or product for the liver, colon or kidneys, and juice or tea detoxes. | liver flush; coffee enema; colonic; juice cleanse; detox tea |
| binders_drainage | Binders, drainage & castor oil | A binder, clay, lymphatic-drainage, sweating or pack-based detox method. | binders; zeolite; activated charcoal; bentonite clay; lymphatic drainage; castor oil packs; ionic foot bath; detox baths |
| spike_protein_detox | Spike-protein & vaccine detox | Protocols to remove spike protein or "detox" from vaccines. | spike detox; nattokinase; bromelain protocol; vaccine detox |
| toxic_load_general | Detox & toxic load (general) | Detoxification as a general concept (the body's detox pathways, "toxic load", sweating out toxins), or detox through an unrelated modality such as sauna or fasting, which also takes the modality's subtopic. | detox pathways; toxic burden; "your body can't detox"; glutathione and detox |

### Domain: Environment & exposures `environment_domain`

#### Environmental & Chemical Exposures `environment`
Health effects attributed to named environmental and chemical exposures. Fluoride goes to `oral`; radiation and light to `radiation_light`; contaminants in specific foods to `food.food_contaminants`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| microplastics | Microplastics & nanoplastics | Microplastics in bodies and the environment. | microplastics in the brain; microplastics in testicles; nanoplastics |
| pfas | PFAS & forever chemicals | Per- and polyfluoroalkyl substances. | PFAS; forever chemicals; Teflon; non-stick pans |
| endocrine_disruptors | Endocrine disruptors & plastics chemicals | Hormone-disrupting chemicals. | BPA; phthalates; parabens; xenoestrogens; endocrine disruptors |
| pesticides_herbicides | Pesticides & herbicides | Agricultural chemicals as exposures, including the health effects of residue in food (which also takes `food.food_contaminants`). | glyphosate; Roundup; atrazine; pesticides; paraquat |
| heavy_metals | Heavy metals (exposure) | Lead, mercury, arsenic, cadmium and other metals as exposures. | lead pipes; lead in Stanley cups; mercury; arsenic; cadmium; aluminum (exposure) |
| air_pollution | Air pollution & smoke | Outdoor air quality. | air pollution; wildfire smoke; PM2.5; train derailment chemicals |
| water_quality | Drinking-water contamination & filtration | Contaminants in tap or well water and water filtration. | tap water contaminants; chlorine; water filters; reverse osmosis |
| indoor_air_mold | Indoor air, mold & building materials | Air quality and materials at home: mold, VOCs, gas stoves, asbestos and building materials. | mold in the house; VOCs; gas stoves; air purifier; asbestos; building materials |
| household_personal_care | Household & personal-care chemicals | Chemicals in household goods, cosmetics and clothing as exposures. | toxic candles; cleaning products; fragrance; synthetic clothing; toxic makeup; aluminum in deodorant |
| geoengineering | Chemtrails & geoengineering | Geoengineering, cloud seeding and "chemtrails" as a subject. | chemtrails; cloud seeding; solar geoengineering; weather modification |
| climate_heat | Climate & heat | Climate change and extreme heat as health issues. | heat waves; climate and health; heat deaths |

#### Radiation, Light & EMF Exposure `radiation_light`
Electromagnetic and light exposures as health factors.

| id | name | definition | examples |
| --- | --- | --- | --- |
| wireless_emf | Wireless & electromagnetic fields | Phones, Wi-Fi, 5G, Bluetooth, power lines and "dirty electricity". | 5G; EMF; Wi-Fi; cell phone radiation; AirPods; dirty electricity |
| emf_protection | EMF protection products & practices | Products and practices sold to block or reduce EMF. | EMF blockers; shielding; Faraday bags; airplane mode at night; EMF meters |
| sunlight_uv | Sunlight & UV exposure | Sun exposure as a health factor: benefits, harms, tanning, sun avoidance. Sunscreen goes to `skin_beauty.sunscreen`. | sun exposure; sunbathing; tanning; UV; sun avoidance; sunburn |
| artificial_light | Artificial light | Screens and LED or blue light affecting the eyes, mood or health in the daytime. Light at night or light timing affecting sleep goes to `sleep.circadian_light`; blue-light glasses take whichever effect is discussed. | blue light; LED lighting; screens and eyes; flicker |
| ionizing_radiation | Ionizing & nuclear radiation | Radiation from nuclear sources, radon and medical imaging dose. | radon; nuclear radiation; Fukushima; X-ray dose |

### Domain: Skin, hair & beauty `beauty`

#### Skin, Hair & Beauty `skin_beauty`
Skin, hair and cosmetic concerns and the products and procedures aimed at them. Chemical toxicity of products goes to `environment.household_personal_care`.

| id | name | definition | examples |
| --- | --- | --- | --- |
| acne | Acne | Acne and its treatment. | acne; Accutane (for acne); benzoyl peroxide; hormonal acne |
| skin_conditions | Skin conditions | Other skin diseases. Psoriasis also takes `immune.autoimmune`. | eczema; psoriasis; rosacea; dermatitis; hives |
| skincare | Skincare products & routines | Skincare routines and products, and the skin microbiome. | retinol; tretinoin; moisturizer; tallow skincare; slugging; K-beauty; skin barrier; skin microbiome |
| sunscreen | Sunscreen | Sunscreen: use, ingredients, safety. | sunscreen; SPF; mineral sunscreen; oxybenzone; zinc oxide |
| hair_loss_hair | Hair loss & hair care | Hair loss in any sex and hair care. | balding; finasteride; minoxidil; hair transplant; thinning hair; shampoo |
| skin_ageing | Skin ageing & appearance | Wrinkles, collagen and the look of ageing skin. | wrinkles; collagen loss; anti-aging skincare; skin elasticity |
| cosmetic_procedures | Cosmetic surgery & injectables | Cosmetic surgery and injectables, including genital cosmetic surgery and loose-skin or body-contouring procedures after weight loss or pregnancy. Therapeutic Botox goes to `medications.other_drugs`. | Botox; fillers; facelift; BBL; breast implants; buccal fat removal; lip filler; labiaplasty; tummy tuck; skin removal after weight loss |
| regenerative_aesthetics | Regenerative aesthetics | Platelet, stem-cell, exosome and related treatments for appearance (skin, hair, face), injected or topical. The same therapies for healing or disease go to `procedures.regenerative_medicine`. | PRP; PRF; exosomes; topical exosomes; salmon sperm/PDRN; polynucleotides; microneedling; stem cell injections |

### Domain: Children's health `children_domain`

#### Infant & Child Health (pediatric-specific) `pediatrics`
Subjects that exist only in infancy and childhood. Use the population axis, not this parent, for content about children on a subject that has its own subtopic (childhood vaccines take `vaccines`; children's diets take `food` or `diets`).

| id | name | definition | examples |
| --- | --- | --- | --- |
| infant_care | Newborn & infant care | Caring for newborns and infants, including newborn sleep safety (SIDS, sleep position). Children's sleep routines go to `sleep.sleep_hygiene_environment`. | newborn care; vitamin K shot; safe infant sleep; SIDS; colic; tummy time; circumcision of newborns |
| child_development | Child development & parenting | Normal child development, including emotional development, resilience and parenting approaches. | milestones; growth charts; early childhood development; resilience in kids; gentle parenting; parenting styles |
| pediatric_care | Pediatric care | The experience of children's medical care: pediatric visits, children's dosing and pediatrician relationships. A childhood illness takes its own subtopic plus a population label. | pediatrician; well-child visit; children's dosing; kids' medications; finding a pediatrician |
| baby_food_child_nutrition | Baby food & child feeding | Feeding babies and young children solid food. | baby food; starting solids; picky eaters; toddler snacks |
| puberty_adolescence | Puberty & adolescent development | Puberty, its timing (age at first period included) and adolescent physical development. | puberty timing; early puberty; age at first period; teen growth |

### Domain: General wellness & other `general`

#### General Wellness & Lifestyle `wellness`
Health as a whole rather than one subject.

| id | name | definition | examples |
| --- | --- | --- | --- |
| lifestyle_pillars | Lifestyle as a whole | Several lifestyle pillars treated together as the route to health. | sleep, diet, exercise and stress; five pillars; healthy lifestyle |
| chronic_disease_trends | Chronic disease trends (general) | Rising chronic disease in general, across conditions. | chronic disease epidemic; sickest generation; "60% of kids have a chronic condition" |
| habits_behavior_change | Habits & behavior change | Building health habits, motivation, coaching. | habit stacking; health coaching; motivation; accountability |
| life_expectancy | Life expectancy & mortality statistics | Population life expectancy and mortality trends. | life expectancy falling; excess mortality (general); leading causes of death |
| energy_fatigue | Energy & everyday fatigue | Tiredness, low energy and afternoon crashes as symptoms, outside ME/CFS or a diagnosed condition. | low energy; always tired; afternoon crash; fatigue; boost your energy |

#### Other health topic `other`
Health, medicine or wellness content, substantive or passing, that no parent topic fits. Name the subject in the summary. Never use it beside a listed topic on the same span; it exists to make gaps in the taxonomy visible.

| id | name | definition | examples |
| --- | --- | --- | --- |

## Narrative axis

Narratives are specific, recurring, contested health propositions. Each
definition opens with the narrative's core proposition in bold; the rest of the
definition and the examples are typical elaborations. Apply a narrative label
wherever the core proposition is invoked, whatever the stance: asserted,
questioned, reported or rebutted. `discourse_role` records the stance. An
elaboration or a premise alone does not invoke the narrative, and discussing the
subject without the proposition is a topic, not a narrative.

### Vaccines `vaccines_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| vaccines_cause_autism | Vaccines cause autism | **Vaccines cause autism or developmental regression.** Any vaccine or the schedule (often MMR) is blamed for autism, the rise in autism, or loss of speech and developmental delays after shots. | Wakefield; MMR autism; "my son regressed after his shots"; lost his words after the vaccines; vaccine-autism link | vaccines |
| vaccine_ingredients_toxic | Vaccine ingredients are toxic | **A vaccine ingredient causes harm.** Aluminum, mercury, formaldehyde, fetal cells, PEG or another component is said to cause neurological damage, allergy or chronic disease. | aluminum adjuvants neurotoxic; thimerosal; "neurotoxins in vaccines" | vaccines |
| too_many_too_soon | Too many vaccines too soon | **The number or timing of childhood vaccines causes harm.** The schedule is said to overload the immune system, so spacing shots out is safer; a spacing preference with no harm claimed is not this narrative. | 72 shots; immune overload; delayed schedule is safer | vaccines |
| hep_b_birth_dose_unneeded | Hep B birth dose unnecessary or harmful | **Newborns of hepatitis-B-negative mothers do not need, or are harmed by, the birth dose.** | why give a newborn a sex-disease vaccine; low-risk babies | vaccines |
| vaccines_cause_sids | Vaccines cause SIDS or infant death | **Vaccines cause sudden infant death or other infant deaths.** | SIDS after shots; infant deaths after vaccination | vaccines |
| vaccines_chronic_disease | Vaccines drive chronic illness | **Vaccines cause the rise in chronic disease.** Allergies, autoimmunity or the "sickest generation" are blamed on vaccines, and unvaccinated children are said to be healthier. | vaxxed vs unvaxxed; chronic disease rose with the schedule | vaccines |
| vaccines_didnt_end_disease | Vaccines did not end infectious disease | **Vaccines did not end infectious disease.** Infectious diseases are said to have declined because of sanitation or nutrition instead. | mortality fell before vaccines; "Dissolving Illusions" | vaccines |
| vaccine_injury_hidden | Vaccine injury is hidden or underreported | **Vaccine injury is hidden or vastly underreported.** VAERS is said to capture only a tiny fraction, or its counts are said to prove mass harm. | VAERS 1%; Lazarus report; hidden injuries; "they won't report it" | vaccines |
| vaccine_makers_no_liability | Vaccine makers have no liability | **Vaccines are unsafe or untested because makers cannot be sued.** The liability shield (1986 Act, PREP Act) is the premise; saying the shield exists without the "therefore unsafe or untested" conclusion is not this narrative. | liability shield means no incentive for safety; can't sue Pfizer so why test; 1986 Act | vaccines |
| vaccines_not_placebo_tested | Vaccines not properly tested | **Vaccines were never properly tested.** They are said to lack true placebo controls or adequate study. "Safe and effective was a lie" alone is `narrative:covid_vaccine_ineffective`. | no saline placebo; never tested; rushed | vaccines |
| natural_immunity_superior | Natural immunity is superior | **Immunity from infection is better than vaccination,** making vaccination unnecessary. | natural immunity; Israeli study; recovered don't need the shot | vaccines |
| hpv_vaccine_harm | HPV vaccine is harmful | **The HPV vaccine causes serious harm,** such as infertility, POTS, autoimmunity or death. | Gardasil injury; Gardasil lawsuit | vaccines |
| flu_shot_ineffective_harmful | Flu shots don't work or cause harm | **Flu vaccines are useless or harmful,** including causing the flu. | flu shot gave me the flu; 10% effective | vaccines |
| covid_vaccine_deaths | COVID vaccines kill / died suddenly | **COVID vaccines kill people.** Sudden deaths of young or healthy people and athletes are attributed to them. Add `narrative:excess_deaths_cover_up` only when concealment or ignoring of excess-death data is claimed. | died suddenly; athletes collapsing; vaccine deaths; excess deaths from the jab | vaccines |
| covid_vaccine_myocarditis | COVID vaccine myocarditis is widespread | **COVID vaccine myocarditis is common, serious or concealed.** | myocarditis in young men; heart damage from the shot | vaccines |
| turbo_cancer | Turbo cancer | **COVID vaccines cause or accelerate cancers ("turbo cancer").** | turbo cancer; cancers exploding since the vaccine | vaccines |
| mrna_alters_dna | mRNA vaccines alter DNA or are gene therapy | **mRNA vaccines alter DNA or are gene therapy rather than vaccines.** They are said to integrate into the genome or be contaminated with DNA. | gene therapy not a vaccine; DNA contamination; SV40 promoter; reverse transcription | vaccines |
| vaccine_shedding | Vaccine shedding | **Vaccinated people shed vaccine material or spike protein that harms others.** | shedding; spike protein through sweat; menstrual changes from proximity | vaccines |
| covid_vaccine_fertility | COVID vaccines harm fertility or pregnancy | **COVID vaccines harm fertility or pregnancy,** causing infertility, miscarriage or menstrual damage. | miscarriages after the jab; fertility collapse from vaccine | vaccines |
| spike_protein_persistent | Spike protein persists and causes disease | **Vaccine-made spike protein persists in the body and drives ongoing illness,** which must be detoxed. | spike protein in the body for years; spikeopathy | vaccines |
| covid_vaccine_ineffective | COVID vaccines don't work | **COVID vaccines don't work.** They are said not to prevent infection, transmission, hospitalization or death, or to make infection worse; "safe and effective was a lie" belongs here. | negative efficacy; didn't stop transmission; "safe and effective" was a lie | vaccines |
| measles_harmless | Measles is harmless or manageable without vaccines | **Measles is harmless, beneficial or manageable without vaccination.** It is called a mild childhood illness whose deaths are overstated, or vitamin A, budesonide or antibiotics are said to suffice. | measles parties; vitamin A cures measles; measles builds immunity; budesonide for measles | infectious |
| vaccine_microchips_5g | Vaccines contain microchips or 5G technology | **Vaccines contain microchips, 5G components, graphene or tracking technology.** | microchips in the vaccine; shooting people up with 5G; graphene oxide; tracking chip | vaccines |
| vaccines_for_profit | Vaccines are pushed for profit | **Vaccines and boosters are pushed mainly for profit by their makers or funders.** Recurring boosters, variant shots and vaccination programmes (often Gates-funded) are cast as revenue schemes. The general claim that medicine keeps people sick is `narrative:pharma_creates_customers`. | Gates vaccine profits; boosters forever; new variants for profit; vaccines are a cash cow | vaccines |

### COVID-19 `covid_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| covid_lab_leak | Lab-leak origin | **SARS-CoV-2 came from a laboratory accident or research in Wuhan.** Contested, not necessarily false. | lab leak; Wuhan Institute of Virology; gain of function | covid |
| covid_bioweapon_plandemic | Bioweapon / planned pandemic | **The virus was deliberately made or released, or the pandemic was planned.** | plandemic; bioweapon; Event 201; planned | covid |
| ivermectin_covid | Ivermectin treats COVID | **Ivermectin prevents or treats COVID-19.** It is often said to have been suppressed; the suppression on its own is `narrative:early_treatment_suppressed`. | ivermectin works; horse dewormer smear | covid |
| hcq_covid | Hydroxychloroquine treats COVID | **Hydroxychloroquine prevents or treats COVID-19.** It is often said to have been suppressed; the suppression on its own is `narrative:early_treatment_suppressed`. | HCQ; Zelenko protocol | covid |
| early_treatment_suppressed | Early treatment was suppressed | **Effective early COVID treatments were deliberately suppressed,** to enable vaccine authorization or for profit, including punishing doctors who used them. Silencing of people or information is `narrative:pandemic_censorship`. | EUA needed no alternatives; suppressed early treatment; doctors punished for ivermectin | covid |
| hospital_protocols_killed | Hospital protocols killed patients | **Hospital protocols killed COVID patients.** Remdesivir, ventilators or hospital incentives are blamed, sometimes with hospitals said to be paid for it. | remdesivir "run death"; ventilators killed; hospitals paid per COVID death | covid |
| masks_useless_harmful | Masks don't work or cause harm | **Masks do not reduce transmission, or they harm wearers** (oxygen, CO2, child development). | masks don't work; cloth masks useless; masks harm kids | covid |
| lockdowns_worse_than_virus | Lockdowns did more harm than good | **Lockdowns and closures caused more harm than they prevented.** Listing their costs without weighing them against what they prevented is not this narrative. | lockdowns killed more; school closures were a disaster | covid |
| covid_deaths_inflated | COVID deaths and cases were inflated | **COVID deaths or cases were overcounted.** Deaths "with" rather than "from" COVID and false-positive PCR tests are the usual elaborations. | died with not from; PCR cycle thresholds; motorcycle death counted as COVID | covid |
| covid_severity_exaggerated | COVID is no worse than flu | **COVID was mild or no worse than flu for most people,** so the response was disproportionate. | just a flu; 99.9% survival | covid |
| long_covid_not_real | Long COVID is not real | **Long COVID is not a real post-infection illness.** It is called psychosomatic, fabricated or actually vaccine injury. | long COVID is anxiety; long COVID is vaccine injury | covid |
| vitamin_d_prevents_covid | Vitamin D or zinc prevents COVID | **Vitamin D, zinc, quercetin or similar supplements prevent or treat COVID-19.** | vitamin D levels and COVID deaths; zinc and quercetin | covid |
| pandemic_censorship | Pandemic dissent was censored | **Accurate COVID information or dissenting scientists were censored.** Officials, platforms or media are said to have silenced or smeared them, often in coordination. Suppression of a treatment is `narrative:early_treatment_suppressed`. | Twitter files; censored doctors; Great Barrington smeared | covid |
| nsaids_worsen_covid | NSAIDs worsen COVID | **Ibuprofen or other NSAIDs worsen COVID-19.** | don't take ibuprofen for COVID; Advil makes COVID worse | covid |

### Cancer `cancer_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| cancer_cures_suppressed | Cancer cures are suppressed | **Effective cancer cures exist but are suppressed** by pharma, doctors or government for profit. | they don't want a cure; cancer industry; cure would end profits | cancer_alt |
| antiparasitics_cure_cancer | Antiparasitics cure cancer | **Antiparasitic drugs (ivermectin, fenbendazole, mebendazole) cure or treat cancer.** Antiparasitics take this narrative, not `narrative:natural_remedy_cures_cancer`; a combined protocol takes each narrative whose remedy is named. | fenbendazole; Joe Tippens protocol; ivermectin kills cancer | cancer_alt |
| sugar_feeds_cancer | Sugar feeds cancer / keto starves it | **Cancer feeds on sugar, so cutting sugar or a ketogenic diet treats it.** The broader claim that cancer is a metabolic rather than genetic disease is `narrative:cancer_metabolic_disease`; code both when both are made. | cancer feeds on sugar; starve cancer; keto cures cancer | cancer_alt |
| cancer_metabolic_disease | Cancer is a metabolic disease | **Cancer is fundamentally a metabolic, not a genetic, disease.** Damaged mitochondria are said to drive it, so metabolic or dietary approaches are the real treatment. | Seyfried; Warburg effect; cancer is a mitochondrial disease; somatic mutation theory is wrong | cancer_alt |
| cancer_fungus_parasite | Cancer is a fungus or parasite | **Cancer is really a fungus or a parasite,** treatable by baking soda or antifungals. Parasites as a cause of cancer are `narrative:parasites_cause_disease`. | cancer is a fungus; Simoncini; cancer is a parasite | cancer_alt |
| chemo_does_more_harm | Chemotherapy does more harm than good | **Chemotherapy does more harm than good.** It is said to rarely work, kill more than it cures, or spread the cancer. | chemo is poison; 2% benefit; oncologists wouldn't take it | cancer |
| natural_remedy_cures_cancer | A natural remedy cures cancer | **A specific herb, food or alternative protocol cures or treats cancer.** "Fights", "reverses" and "heals" count as cures. Vitamin megadoses are `narrative:vitamin_megadose_cures` and antiparasitic drugs `narrative:antiparasitics_cure_cancer` instead. | B17; apricot seeds; Gerson; cannabis oil cured; soursop kills cancer cells | cancer_alt |
| cancer_screening_harmful | Cancer screening causes harm | **Cancer screening causes or spreads cancer, or does more harm than good.** | mammograms cause cancer; biopsy spreads cancer | cancer |
| cancer_epidemic_young | Unexplained cancer surge in young people | **Cancer, especially in young people, is surging for a cause that is being ignored or hidden.** A rise in early-onset cancer reported without the "ignored or hidden" claim is a topic, not this narrative. | young people getting cancer and nobody asks why; pancreatic cancer in 30-year-olds | cancer |

### Food & diet `food_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| seed_oils_toxic | Seed oils are toxic | **Seed and vegetable oils drive chronic disease,** inflammation or obesity. | hateful eight; seed oils are poison; linoleic acid | food |
| saturated_fat_cholesterol_myth | Saturated fat and cholesterol are not harmful | **Saturated fat and dietary cholesterol do not cause heart disease.** The diet-heart hypothesis is called wrong or fraudulent. | Ancel Keys fraud; butter is back; sugar industry blamed fat | food |
| sugar_is_toxic | Sugar is poison | **Sugar is uniquely toxic.** Sugar or fructose is said to be addictive like drugs and to drive most chronic disease. | sugar is poison; sugar is more addictive than cocaine | food |
| sugar_hyperactivity | Sugar makes children hyperactive | **Sugar makes children hyperactive.** | sugar high; kids bouncing off the walls after cake | food |
| food_dyes_harm_children | Food dyes harm children | **Synthetic food dyes harm children,** causing hyperactivity, ADHD or other harm, and are banned elsewhere for that reason. | Red 40 and ADHD; banned in Europe | food |
| raw_milk_superior | Raw milk is superior and safe | **Raw milk is healthier or safer than pasteurized milk.** It is said to cure allergies or asthma, or pasteurization is said to destroy its value. | raw milk cures; pasteurization kills nutrients | food |
| gmo_harmful | GMOs are harmful | **Genetically modified foods damage health.** | GMO cancer rats; Frankenfood | food |
| glyphosate_poisoning | Glyphosate is poisoning the population | **Glyphosate in food is poisoning the population,** driving gut damage, cancer, gluten intolerance or chronic disease. | Roundup in everything; glyphosate causes leaky gut | environment |
| artificial_sweeteners_harm | Artificial sweeteners cause cancer or harm | **Artificial sweeteners cause cancer or other harm,** such as metabolic damage or microbiome harm. | aspartame cancer; diet soda worse than sugar | food |
| gluten_harms_everyone | Gluten harms everyone | **Gluten or modern wheat harms everyone,** not only people with celiac disease. A claim that grains in general are harmful is `narrative:plants_are_toxic`. | zonulin; modern wheat; gluten causes leaky gut in everyone | food |
| food_engineered_to_harm | The food supply is engineered to make people sick | **Food companies or the government deliberately engineer food to addict or sicken people,** sometimes to create patients for pharma. | they poison the food; designed to make you sick; food-pharma pipeline | food |
| us_food_banned_elsewhere | US food contains ingredients banned abroad | **American food contains ingredients, additives or pesticides banned abroad, or more chemicals than abroad, which shows it is dangerous.** | banned in Europe; same cereal, different ingredients; pesticides banned in the EU | food |
| carnivore_cures | Carnivore cures disease | **An all-meat diet cures or reverses disease** such as autoimmune disease, depression or diabetes. "Treats", "heals" and "improves [a disease]" count. | carnivore healed me; carnivore reversed my autoimmunity | diets |
| plants_are_toxic | Plants, grains and vegetables are toxic | **Plants, grains or plant compounds are harmful or unnecessary.** Vegetables, oxalates, lectins, fiber or grains are said to damage health or the gut. | oxalates; lectins; plant defense chemicals; fiber is unnecessary; grains damage the gut | food |
| fasting_cures | Fasting or keto cures disease | **Fasting or a ketogenic diet cures or reverses disease** such as diabetes, autoimmunity, dementia or chronic disease generally. "Treats", "heals" and "improves [a disease]" count; the specific mechanism that sugar feeds cancer is `narrative:sugar_feeds_cancer`. | fasting heals everything; reverse diabetes with keto; fasting eats tumors | diets |
| alkaline_ph | Alkaline diet or water changes body pH | **Alkaline food or water changes blood pH and prevents disease,** or disease thrives in an acidic body. | alkaline water; acidic body causes cancer | food |
| wellness_waters | Structured, hydrogen or raw water | **Structured, hydrogen-rich, raw or "living" water has special health properties.** | structured water; EZ water; hydrogen water; raw water | food |
| soy_feminizes | Soy feminizes men | **Soy or phytoestrogens lower testosterone or feminize men.** | soy boys; phytoestrogens | food |
| beef_tallow_healthier | Animal fats are healthier than plant oils | **Animal fats are healthier than plant oils.** Beef tallow, lard or butter are offered as replacements for seed oils, as food or skincare. | cook in tallow; tallow fries | food |
| red_meat_healthy | Red meat is healthy | **Red meat is healthy, and warnings that it causes heart disease, cancer or early death are wrong.** | red meat is not the enemy; meat causes cancer is a myth | food |
| microwave_radiation_food | Microwaving destroys food or is dangerous | **Microwaving destroys nutrients or makes food dangerous.** | microwave kills nutrients | food |
| soil_depletion_supplements | Depleted soil means everyone needs supplements | **Soil depletion means people need supplements.** Modern soil is said to be so depleted that food no longer supplies enough nutrients; depleted soil without "so you need supplements" said or plainly implied is not this narrative. | soil has no minerals anymore so you have to supplement; you can't get it from food | food |
| alcohol_moderate_protective | Moderate drinking is protective | **Moderate drinking, especially red wine, protects the heart or extends life.** The French paradox and the J-curve are the usual support. | French paradox; a glass of red wine a day; moderate drinkers live longer | alcohol |

### Pharmaceuticals & conventional medicine `pharma_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| statins_harmful | Statins are harmful or useless | **Statins do more harm than good or are useless.** They are said to deplete CoQ10, cause diabetes or dementia, or exist for profit. | statins are poison; relative risk trick | cardiovascular |
| antidepressants_ineffective | Antidepressants don't work | **Antidepressants do not work or are no better than placebo.** Claims about the serotonin theory are `narrative:chemical_imbalance_myth`. | barely better than placebo; Kirsch meta-analysis; antidepressants don't work | mental |
| chemical_imbalance_myth | The chemical-imbalance theory is a myth | **The serotonin or "chemical imbalance" theory of depression is false or was a lie.** Whether the drugs work is `narrative:antidepressants_ineffective`. | chemical imbalance debunked; serotonin review; depression isn't low serotonin | mental |
| ssris_cause_violence | SSRIs cause violence or shootings | **Psychiatric drugs, especially SSRIs, cause violence, mass shootings or suicide.** | school shooters on SSRIs; akathisia | mental |
| therapy_harms_children | Therapy culture harms children | **Therapy culture and over-protection harm children's resilience.** | bad therapy; therapists pathologize normal childhood; coddled kids; over-diagnosing anxiety in kids | mental |
| tylenol_autism | Acetaminophen in pregnancy causes autism | **Acetaminophen in pregnancy or infancy causes autism or ADHD.** | Tylenol autism; HHS announcement | pregnancy |
| leucovorin_autism_treatment | Leucovorin treats autism | **Leucovorin (folinic acid) treats or reverses autism.** | folinic acid autism; cerebral folate deficiency | neurodevelopment |
| fever_suppression_harmful | Fever reducers are harmful | **Fever reducers suppress immunity and prolong illness, so fevers should be left untreated.** | let the fever run; Tylenol blunts the immune response; fever is your friend | immune |
| birth_control_harms | Hormonal birth control causes serious harm | **Hormonal birth control causes serious harm.** Typical harms named are infertility, depression, cancer, personality or partner-choice change, lowered testosterone, libido loss and sexual pain. | the pill made me depressed; birth control infertility; the pill killed my libido | fertility |
| abortion_pill_dangerous | The abortion pill is dangerous | **Medication abortion is dangerous,** or causes breast cancer, infertility or depression. | mifepristone dangerous; abortion breast cancer link | fertility |
| hrt_dangerous | Menopausal hormone therapy is dangerous | **Menopausal hormone therapy causes serious harm and should be avoided,** such as breast cancer or heart disease. A passage arguing the WHI scare was wrong takes `narrative:hrt_fears_overblown` only; add this narrative (rebutted) only when the harm proposition is stated and argued against separately. | HRT causes breast cancer; WHI showed harm | womens |
| hrt_fears_overblown | HRT fears were overblown | **The WHI-era scare about menopausal hormone therapy was wrong or exaggerated,** and HRT is safe or broadly protective. | WHI was misread; black box removed; estrogen's undeserved bad rep | womens |
| glp1_dangers | GLP-1 drugs are dangerous | **GLP-1 drugs cause serious harm or trap users for life.** Muscle wasting, blindness, suicide or cancer are the usual harms; saying neutrally that people stay on them long term is not this narrative. | Ozempic eats your muscle; hooked on it for life; NAION | glp1 |
| adhd_meds_harmful | ADHD drugs are harmful or overprescribed | **ADHD stimulants are harmful or overprescribed.** They are called speed, or said to be given to normal children or adults for convenience. | drugging boys; Adderall is meth | neurodevelopment |
| pharma_creates_customers | Medicine keeps people sick for profit | **Medicine treats symptoms instead of curing so that patients stay lifelong customers.** Vaccine-profit claims are `narrative:vaccines_for_profit`; lowered cholesterol thresholds also take `narrative:statins_harmful` only when statin harm or uselessness is stated. | customers for life; sick care; no money in cures | health_system |
| medical_errors_leading_cause | Medicine is a leading cause of death | **Medical care or prescription drugs are a leading cause of death** (e.g. the third). | third leading cause of death; iatrogenic deaths | health_system |
| fluoride_lowers_iq | Fluoride lowers IQ / harms the brain | **Water fluoridation lowers IQ, harms brain development or is a neurotoxin.** | NTP report; fluoride neurotoxin; fluoride and brain development | oral |
| fluoride_mind_control | Fluoride is used for control | **Fluoride is added to pacify or control people,** often by calcifying the pineal gland. | pineal gland; Nazis used fluoride | oral |
| root_canals_amalgams_illness | Dental work causes systemic disease | **Root canals, amalgams, cavitations or metal implants cause chronic or systemic disease.** | root canals cause cancer; mercury fillings; cavitations; titanium implants | oral |
| sunscreen_harmful | Sunscreen is harmful | **Sunscreen does more harm than good.** It is said to cause cancer, be toxic or block needed vitamin D; sunscreen must be named, and avoiding the sun in general is `narrative:sun_exposure_cures`. | sunscreen causes cancer; oxybenzone hormone disruptor | skin_beauty |
| sun_exposure_cures | Sun exposure is a cure-all | **Sun exposure prevents or cures many diseases, and avoiding or blocking sunlight causes disease.** Skin cancer is often included, and sunglasses or covering up count as blocking; sunscreen named as harmful is `narrative:sunscreen_harmful`. | sun deficiency; sun avoidance kills more than smoking; sunglasses make you sick | radiation_light |
| deodorant_breast_cancer | Antiperspirant causes breast cancer | **Aluminum antiperspirants cause breast cancer.** | aluminum deodorant cancer | environment |

### Alternative health & wellness `wellness_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| germ_theory_denial | Germ theory is false / terrain theory | **Germs do not cause disease.** Viruses are said not to exist or not to be contagious, and the "terrain" is what matters. | terrain theory; viruses don't exist; Pasteur recanted | infectious |
| parasites_cause_disease | Hidden parasites cause chronic disease | **Hidden parasites cause chronic disease in most people,** including cancer, so routine cleansing or deworming is needed. | everyone has parasites; deworm twice a year; parasites cause cancer | detox |
| heavy_metal_toxicity_widespread | Hidden heavy-metal toxicity is widespread | **Undiagnosed heavy-metal burden causes widespread chronic illness,** autism or fatigue, and needs chelation. | heavy metal toxicity; chelation for autism | detox |
| mold_toxicity_widespread | Hidden mold toxicity is widespread | **Hidden household mold is widespread and drives chronic illness,** including bowel disease. | mold is making you sick; most homes have toxic mold; mycotoxins cause IBD | chronic_complex |
| stealth_infections_root | Hidden infections cause chronic disease | **Hidden chronic infections underlie most chronic disease.** EBV, mycoplasma, Lyme co-infections or other "stealth" pathogens are blamed; Lyme alone is `narrative:chronic_lyme_widespread`. | stealth infections; EBV is behind everything; mycoplasma; hidden viruses cause chronic illness | chronic_complex |
| metabolic_dysfunction_root | Metabolic dysfunction is the root of all disease | **Mitochondrial or metabolic dysfunction is the root cause of nearly all chronic disease.** | one root cause: bad energy; underpowered cells; all chronic disease is metabolic | metabolic |
| inflammation_root_cause | Inflammation is the root of all disease | **Chronic inflammation is the root cause of all or most disease.** Inflammation as the cause of one specific disease is not this narrative. | inflammation is the root of all disease; every chronic disease is inflammation | immune |
| detox_needed | The body needs help to detox | **The body accumulates toxins it cannot clear on its own.** Cleanses, detox products or protocols are the usual remedy, but none needs to be named. | toxins build up; cleanse your liver; your body can't keep up with the toxins | detox |
| leaky_gut_root_cause | Leaky gut is the root of disease | **Leaky gut is the root of disease,** such as autoimmune disease, mental illness, weak immunity or most chronic disease. | leaky gut causes autoimmunity; all disease begins in the gut | gut |
| candida_overgrowth_widespread | Systemic candida is widespread | **Hidden candida or yeast overgrowth causes chronic illness in many people,** such as fatigue and brain fog. | candida overgrowth; yeast causes everything | gut |
| adrenal_fatigue_real | Adrenal fatigue is a real condition | **Stress exhausts the adrenal glands, causing "adrenal fatigue".** | adrenal fatigue; adrenal burnout | endocrine |
| chronic_lyme_widespread | Chronic Lyme is widespread and needs long treatment | **Persistent Lyme infection explains much chronic illness** and needs long-term antibiotics or alternative protocols; it is sometimes called a bioweapon. | chronic Lyme; Plum Island; Lyme is a bioweapon | chronic_complex |
| mthfr_explains_illness | MTHFR explains chronic illness | **MTHFR variants cause illness or require methylated supplements.** | MTHFR mutation; can't methylate; you need methylated B12 | supplements |
| vitamin_megadose_cures | Megadose vitamins cure disease | **High-dose vitamins cure serious disease** such as sepsis, cancer or autoimmunity. Vitamin megadoses for cancer take this narrative only. | vitamin C for sepsis; 50,000 IU vitamin D cured; IV vitamin C cures cancer | supplements |
| vitamin_a_toxicity | Vitamin A is a toxin | **Dietary vitamin A (retinol) is a toxin that accumulates and drives chronic disease.** | vitamin A toxicity; retinol poisoning; low-vitamin-A diet | supplements |
| methylene_blue_miracle | Methylene blue is a wonder drug | **Methylene blue broadly enhances cognition, mitochondria or longevity.** | methylene blue; mitochondrial booster | cognition |
| red_light_cure_all | Red light therapy heals broadly | **Red light therapy heals or prevents a wide range of conditions.** | red light for everything | recovery |
| grounding_heals | Grounding heals | **Contact with the earth heals,** transferring electrons that reduce inflammation. | earthing; free electrons | stress |
| peptides_safe_miracle | Peptides are safe miracle healers | **Research peptides are safe and broadly healing** despite little human evidence. Either half invokes it, including the claim that they are safe to take indefinitely. | BPC-157 heals anything; peptides are natural; safe to stay on forever | peptides |
| nad_reverses_ageing | NAD+ boosters reverse ageing | **NAD+ boosters or sirtuin activators reverse ageing or broadly restore health.** | NAD reverses aging; NMN; resveratrol activates longevity genes | longevity |
| fringe_chemical_cures | Ingested chemicals cure disease | **Ingested industrial or household chemicals cure disease.** MMS/chlorine dioxide, borax, turpentine, DMSO or colloidal silver are said to cure infections, cancer or autism. | MMS; borax; turpentine; colloidal silver; DMSO | alt_medicine |
| energy_frequency_healing | Energy or frequency devices heal | **Frequency, energy or scalar devices and modalities cure disease.** A device said to heal through combined "frequencies" takes this; add `narrative:grounding_heals` or `narrative:red_light_cure_all` only if their own healing claim is made. | Rife machine; frequency healing; scalar energy | alt_medicine |
| heart_not_pump | The heart is not a pump | **The heart is not a pump, so conventional cardiology is wrong about circulation.** Vortex or hydraulic-ram models are offered instead. | the heart is not a pump; structured water moves the blood; hydraulic ram | cardiovascular |
| alzheimers_reversible | Alzheimer's is reversible | **Alzheimer's disease can be reversed with lifestyle or metabolic protocols.** Bredesen's protocol and "type 3 diabetes" are the usual elaborations. | Bredesen protocol; ReCODE; Alzheimer's is type 3 diabetes; reverse cognitive decline | dementia_ageing |
| autism_recoverable | Autism is recoverable | **Autism can be reversed or "recovered" through diet, detox or biomedical protocols.** Leucovorin alone is `narrative:leucovorin_autism_treatment`. | recovered from autism; biomedical treatment; GFCF diet cured autism | neurodevelopment |
| glasses_worsen_vision | Glasses worsen eyesight | **Glasses weaken eyesight, and vision can be restored naturally.** | Bates method; throw away your glasses; eye exercises restore vision | sensory |
| chiropractic_stroke_risk | Chiropractic adjustments cause strokes | **Chiropractic neck adjustments cause strokes.** | neck adjustment stroke; artery dissection after the chiropractor | alt_medicine |
| emf_5g_harm | EMF and 5G cause disease | **Wireless radiation causes disease** such as cancer, infertility, insomnia or COVID. | 5G caused COVID; phone in pocket lowers sperm; Wi-Fi in schools | radiation_light |
| chemtrails | Chemtrails | **Aircraft are spraying chemicals or metals on the population.** | chemtrails; they're spraying us | environment |
| microplastics_catastrophe | Microplastics are proven to cause serious disease | **Microplastics are established causes of serious disease** such as infertility, dementia, cancer or heart attacks. | spoon of plastic in your brain; microplastics cause heart attacks | environment |
| household_toxins_poisoning | Everyday products are poisoning families | **Ordinary household and personal-care products are poisoning people.** Candles, fragrance, cookware, clothing, food packaging and plastic bottles are the usual culprits. | toxic candles; your home is poisoning you; plastic bottles leach poison | environment |
| tampon_toxins | Period products contain dangerous toxins | **Tampons or pads contain toxins, such as heavy metals or dioxins, that cause harm.** | lead in tampons; dioxins in pads | womens |
| baby_food_metals_harm | Heavy metals in baby food damage children | **Heavy metals in baby food or infant formula damage children,** causing autism or brain damage. | toxic baby food; lead in baby food; heavy metals in formula | food |

### Hormones, men's & reproductive health `hormone_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| testosterone_collapse | Testosterone collapse | **Men's testosterone has collapsed across generations.** Most men are said to need boosting or TRT. | testosterone down 1% a year; men today have their grandfathers' T | mens |
| sperm_count_collapse | Sperm counts are collapsing | **Sperm counts are collapsing toward a fertility crisis,** usually blamed on chemicals. | sperm counts halved; Shanna Swan; Count Down | fertility |
| semen_retention_benefits | Semen retention gives special benefits | **Abstaining from ejaculation gives special benefits,** such as higher testosterone, energy or magnetism. | NoFap superpowers; retention boosts T | manosphere |
| endocrine_disruptors_feminizing | Chemicals are feminizing men or children | **Endocrine-disrupting chemicals are feminizing men or children.** Atrazine or plastics chemicals are blamed for changed sex characteristics, early puberty, genital malformation or transgender identity. | atrazine frogs; chemicals turning kids trans; early puberty from plastics | environment |
| gender_care_harmful_youth | Youth gender care is harmful and unsupported | **Gender medicine for minors is harmful and unsupported.** Puberty blockers or transition are called irreversible harms with no supporting evidence, dysphoria is said to resolve on its own, or social contagion is given as a reason not to treat. Claims about what trans identity is are `narrative:trans_identity_disorder`. Contested. | Cass Review; puberty blockers sterilize; most kids desist | gender |
| gender_care_lifesaving | Youth gender care is lifesaving | **Gender-affirming care for minors is lifesaving or safe.** It is said to prevent suicide and be well supported, withholding it to kill, or puberty blockers to be reversible. Contested. | affirm or suicide; lifesaving care; puberty blockers are reversible | gender |
| trans_identity_disorder | Transgender identity is a disorder or contagion | **Transgender identity is a disorder, delusion or social contagion rather than a real identity.** ROGD, "gender ideology" and "nobody is born in the wrong body" belong here; claims about treating minors are `narrative:gender_care_harmful_youth`. Contested; code rebuttals too. | gender ideology; trans is a mental illness; ROGD; social contagion of trans identity | gender |
| abortion_infanticide | Abortion supporters endorse infanticide | **Abortion supporters endorse killing infants born alive.** Babies born alive after abortion are said to be left to die. | born-alive babies left to die; post-birth abortion; Born-Alive Act | fertility |

### Health system, policy & society `system_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| sickest_generation | Children are the sickest generation | **Today's children are the sickest generation in history, with chronic illness unprecedented or at majority levels.** Food, chemicals, drugs or vaccines are blamed. `frame:maha_framing` needs the wider MAHA package; a passage can take both. | sickest generation; 60% of kids chronically ill | wellness |
| autism_epidemic_environmental | The autism rise is a real environmental epidemic | **The rise in autism is a real increase caused by an environmental exposure,** not diagnostic change. | autism epidemic; 1 in 10,000 to 1 in 31 | neurodevelopment |
| fda_captured | Regulators are captured by industry | **Health agencies are controlled by the industries they oversee.** The FDA, CDC, NIH, USDA or their committees are said to be paid, staffed or owned by industry, which may be implied. Usually co-occurs with `frame:government_distrust`. | revolving door; FDA funded by pharma; agency capture; the guidelines committee is bought | health_system |
| doctors_paid_to_prescribe | Doctors are paid to push vaccines or drugs | **Doctors are paid bonuses, perks or kickbacks to vaccinate or prescribe.** | pediatricians' bonuses for vaccination rates; kickbacks; pharma perks for doctors | health_system |
| depopulation_agenda | Elite depopulation or control agenda | **Elites, globalists or governments are deliberately reducing the population or controlling people.** Vaccines, food, medicine or pandemics are the means; a control plan with no depopulation claim (Great Reset, "eat the bugs") counts. | depopulation; Gates wants fewer people; great reset; you'll eat bugs and own nothing | policy |
| outbreak_engineered | Outbreaks are engineered, leaked or staged | **An emerging outbreak (bird flu, Ebola, mpox) was engineered, leaked from a lab, or staged or hyped as the next "plandemic".** SARS-CoV-2 origins are `narrative:covid_lab_leak` or `narrative:covid_bioweapon_plandemic`. | next plandemic; bird flu scare; Ebola came from a lab | infectious |
| excess_deaths_cover_up | Excess deaths are being covered up | **Unexplained excess deaths since 2021 are being ignored or concealed,** often blamed on vaccines. Deaths attributed to vaccines without a concealment claim are `narrative:covid_vaccine_deaths`. | excess mortality cover-up; insurance data | wellness |
| assisted_dying_expansion | Assisted dying spreads beyond the terminally ill | **Legal euthanasia spreads to young, non-terminal or depressed people.** | MAID for depression; Canada's euthanasia slippery slope; euthanasia instead of care | acute_care |
| fentanyl_foreign_attack | Fentanyl is foreign warfare | **A foreign state, usually China, deliberately supplies fentanyl or its precursors as an attack on the United States.** | China's fentanyl war; chemical warfare on Americans; reverse opium war | drugs_addiction |

### Other `other_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| unlisted_narrative | Unlisted contested narrative | **A recurring, contested health proposition that no listed narrative covers.** It circulates beyond this conversation; name the proposition in the summary. Do not use it for one-off claims, personal opinions, plain misconceptions or ordinary health advice. | name the proposition in the summary | other |

## Frame axis

| id | name | definition | examples |
| --- | --- | --- | --- |
| anti_mainstream_medicine | Anti-mainstream-medicine framing | Conventional medicine or ordinary doctors are portrayed as ignorant, captured, harmful or unable to help. Discussing the health system as a subject is a topic; this is the rhetoric. The target decides: doctors or medicine as a practice take this frame, pharma as an actor `frame:big_pharma`, and a worldview critique ("pharma religion") both. | doctors won't tell you; your doctor doesn't know this; medical school teaches nothing about nutrition; Western medicine failed me |
| root_cause_framing | Root-cause framing | Getting to an underlying cause is contrasted with merely treating symptoms, reversal is promised instead of management, or one hidden cause is said to underlie many diseases. Needs that contrast or that claim: "X is at the root of Y" about a single disease is a causal claim, not this frame. | root cause; treat the cause not the symptoms; reverse disease; band-aid medicine |
| big_pharma | Big Pharma framing | The pharmaceutical industry is cast as a self-interested actor shaping medicine against patients' interests. Criticism of doctors or medicine as a practice is `frame:anti_mainstream_medicine`. | Big Pharma; pharma profits; pharma owns the media; drug pushers |
| big_food | Big Food framing | The food industry is cast as deliberately or negligently harming health. | Big Food; food lobby; processed-food giants; Big Ag |
| industry_distrust | Health-industry distrust | Health-adjacent industries other than pharma and food (insurers, hospital systems, "the healthcare system" as a business, cosmetics, chemical and tech companies, philanthropic funders) are cast as self-interested actors harming health. | insurers profit from denying care; the sick-care business; cosmetics create the problems they sell; the Gates Foundation's agenda; chemical companies knew |
| government_distrust | Government & agency distrust | Public agencies, regulators or official science are portrayed as corrupt, lying or untrustworthy. Criticism of current leaders' decisions is not this frame unless the agency or official science is called corrupt, lying or untrustworthy. | FDA is corrupt; CDC lied; you can't trust the government on health |
| media_distrust | Media & platform distrust | Mainstream media, fact-checkers or tech platforms are portrayed as lying about or manipulating health information. | mainstream media lies; fact-checkers are paid; legacy media covered it up |
| conflict_of_interest | Conflict-of-interest framing | A finding, guideline, institution or person is discounted because of who funds, employs or profits from them. A profit or cost motive with no actor named takes this frame only. | industry-funded study; follow the money; paid by Pfizer; they don't want you to do it because it costs money |
| censorship_suppression | Censorship & suppression framing | Information, research, treatments or people are described as censored, suppressed, buried or silenced. "They never talk about X" with no question is this frame, not `frame:insinuating_questions`. | they don't want you to know; censored; banned from YouTube; suppressed study; they never talk about this |
| conspiracy_cover_up | Conspiracy / cover-up | A coordinated, hidden and malign effort is alleged. Requires an actual allegation of coordination or concealment; criticism, distrust, incompetence, concealment by one named person or firm without coordination, or documented misconduct narrated as fact is not enough. | cover-up; they planned it; coordinated; hidden agenda |
| insinuating_questions | Insinuating questions ("just asking") | A suspicion is advanced through leading questions or "makes you wonder" insinuation rather than asserted. Requires a question or a "makes you wonder" phrase. | makes you wonder; I'm just asking questions; why won't they test that? coincidence? |
| fear_alarm | Fear & crisis framing | Health threats are presented in alarmist, catastrophic language meant to provoke alarm. Needs intensification beyond the standard term: "obesity epidemic", "opioid crisis" or "loneliness epidemic" used descriptively is not it. | ticking time bomb; poisoning our children; exploding; catastrophe; a tsunami of disease |
| medical_freedom | Medical-freedom framing | Health decisions are framed as autonomy, informed consent, parental rights or freedom from mandates. | medical freedom; my body my choice; parental rights; informed consent |
| anti_expert_populist | Anti-expert / populist framing | Ordinary judgement, lived experience or independent research is elevated over expertise and credentials. | do your own research; trust your gut; moms know best; experts got it wrong |
| naturalness_appeal | Naturalness & ancestral appeal | Something is recommended or condemned because it is natural, ancestral, traditional, evolutionary, artificial or synthetic, including design language without God or spirit. "Toxic", "clean", "chemicals" and "poison" are `frame:toxin_purity`. | natural; ancestral; we evolved to; synthetic; no artificial ingredients; the body is designed perfectly |
| toxin_purity | Toxin & purity framing | Health problems are framed in terms of toxins, poisons, chemical burden or clean-versus-contaminated bodies and products. Not for "eat clean" as an idiom for healthy eating. | toxins; toxic load; poison; clean; non-toxic; chemical-free; "what's really in" |
| optimization | Optimization & biohacking framing | Health is framed as performance to maximize through protocols, stacks, metrics and hacks. Needs maximizing language applied to the body; everyday "optimal" and lab ranges are not it. | optimize your levels; hack; protocol; stack; peak performance; optimal not normal |
| maha_framing | MAHA framing | The Make America Healthy Again framing. Needs at least two of: a chronic-disease crisis, especially in children; causes in food, chemicals or medicine; corporate or government capture; the movement or its agenda named. The slogan or one concern alone is not it. | Make America Healthy Again; sickest generation; corporate capture of our health |
| political_partisan | Partisan framing | A health issue is framed through partisan or culture-war identity: a party or a culture-war camp ("the left", "woke medicine", "gender ideology activists") is blamed or praised as a political camp, even when no party is named. | the left wants; woke medicine; Republicans are killing; MAGA health; gender ideology activists |
| spiritual_religious | Spiritual & religious framing | Health is framed in religious or spiritual terms: divine design, sin, faith, prayer or spiritual causes of illness. Design language without God or spirit is `frame:naturalness_appeal`. | God designed the body; spiritual attack; faith healed me; demonic |
| commercialization | Commercialization | The passage sells or monetizes: sponsorship, discount codes, affiliate links, or the speaker's own product, clinic, programme or book. Apply to a host's own products as well as paid reads. | use code; link in the show notes; my supplement line; sponsored by |
| disclaimer | Disclaimer | The speaker disclaims medical authority or responsibility, or advises consulting a professional. | not medical advice; talk to your doctor; I'm not a doctor; for entertainment purposes |
| correction_debunking | Correction & debunking | The speaker corrects, fact-checks or debunks a health claim, whether or not the correction is itself accurate. | that's a myth; the evidence doesn't support; this is misinformation; here's what the science says |

## Evidence axis

| id | name | definition | examples |
| --- | --- | --- | --- |
| specific_study | Specific study citation | An identifiable study is invoked: a finding plus at least one of a named author or research group, journal, institution, or trial or dataset name, or a year together with a design. A design, sample size or year alone with a finding is `evidence:vague_research`. | a 2019 JAMA study found; the Minnesota Coronary Experiment; Dr. Smith's trial found; the WHI trial |
| vague_research | Vague research appeal | Research or experts are invoked without enough to identify a study: "studies show", a study given only by design, size or year, a named scientist's theory or body of work, or unnamed experts. Agreement among experts is `evidence:expert_consensus`; a media source is `evidence:media_source`. | studies show; research says; science has proven; there's data on this; a study of 1,000 teens found; experts told me; Warburg showed |
| official_data_documents | Official data & documents | Government or official data, records, documents or findings are invoked as evidence: numbers, databases, regulated labels (drug label, package insert), filings, and an official body's assessment or finding. An official recommendation or advisory is `evidence:expert_consensus`. | VAERS data; CDC numbers; package insert; FDA label; FOIA emails; court documents; insurance data; FDA inspection found; the administration admits |
| expert_consensus | Consensus, guideline & official-recommendation appeal | Expert agreement, a guideline, an official recommendation or advisory, or a classification decision is invoked as support, including a journal named as a guideline's source. Unnamed experts without asserted agreement are `evidence:vague_research`. | scientific consensus; the guidelines say; the AAP recommends; Surgeon General's advisory; IOM recommended; DSM removed it; most doctors agree |
| prestige_institution | Prestige-institution invocation | A prestigious institution, journal or award is named to lend authority rather than a finding discussed on its content. | Harvard; Stanford; Mayo Clinic; NEJM; Nobel Prize |
| credential_appeal | Credential appeal | A named person's title, training or professional identity is invoked as grounds for believing a claim, including their recommendation given with their title. Anonymous endorsements are `evidence:strength_assertion`. | as a physician; he's an MD; a Harvard-trained doctor; I'm a nutritionist; Dr. X recommends |
| clinical_experience | Clinical experience | A practitioner's own experience treating, coaching or advising people about their health, licensed or not (doctors, therapists, dietitians, chiropractors, naturopaths, health coaches, trainers). Treat the speaker as a practitioner only if the window says so; another practitioner's results or a relayed patient story is `evidence:personal_anecdote`. | in my practice; my patients; I've treated thousands; we see this all the time in clinic; my clients |
| personal_anecdote | Personal anecdote & testimonial | Personal or second-hand experience is offered as grounds for a general conclusion, including relayed patient stories and non-health professional or eyewitness experience. | this worked for me; my friend's son; I healed myself; testimonials; before and after |
| mechanistic_explanation | Mechanistic explanation | A biological mechanism is used to explain a claim or make it plausible. It can co-occur with study signals. | it blocks the receptor; spikes insulin; mitochondria; crosses the blood-brain barrier |
| strength_assertion | Evidence-strength assertion | An explicit assertion about the evidence or proof behind something (proven, science-backed, FDA approved offered as grounds), an anonymous endorsement or certification seal, or "there's no evidence" used as a verdict. Certainty boosters alone ("we know", "clearly") are not this label. | proven; clinically proven; science-backed; FDA approved; doctor recommended; NSF certified; third-party tested; gold standard |
| preclinical_extrapolation | Preclinical extrapolation | Animal, cell or lab evidence is offered as support for a claim about humans. | in mice; rat study; in a petri dish; cell culture; in vitro |
| weak_human_evidence | Preliminary or observational human evidence | Preliminary, observational or single-case human evidence is offered: association, small pilot, case report, preprint, survey, or unattributed statistics or survey figures. Code the kind offered, not your opinion of a plain citation. | observational study; associated with; small pilot; case report; preprint; a survey found; three quarters of people say |
| traditional_use | Traditional-use appeal | Long or traditional use is offered as evidence. | used for thousands of years; ancient medicine; our grandmothers knew |
| foreign_comparison | Foreign-comparison appeal | Other countries' rules, practices or outcomes are offered as evidence. | banned in Europe; other countries don't vaccinate newborns; Japan doesn't allow |
| media_source | Media or social source | A media source, named or not, is offered as where the speaker learned something: a book, documentary, news report, video, podcast or podcast guest's statement, quote, social-media post, historical document, biography, or private email or letter. "Research" or "studies" as the source is `evidence:vague_research`. | I saw a video; a documentary showed; I read in a book; a post on X; I remember reading something; reports say; an insider email; his biography |
| evidence_limits | Evidence limitations acknowledged | The speaker acknowledges limits or uncertainty in the evidence, including saying evidence is absent when acknowledging uncertainty rather than giving a verdict. | more research is needed; it was a small study; we don't know yet; correlation not causation; it hasn't been studied |

## Population axis

| id | name | definition | examples |
| --- | --- | --- | --- |
| infants | Infants & toddlers | The health content is specifically about babies or toddlers (under about 3): "babies", "toddlers", "under 3". | newborns; babies; infants; toddlers |
| children | Children | The health content is specifically about school-age children or "kids" generally: "kids", "children", "school-age", "young girls", and "minors" unless ages 13 to 17 are given. | kids; children; our children; schoolchildren; young girls; minors |
| adolescents | Adolescents & teens | The health content is specifically about teenagers or adolescents: "teens", "adolescents", ages 13 to 17. | teens; teenagers; adolescents; high schoolers |
| young_adults | Young adults | The health content is specifically about young adults (roughly 18 to 30), including "Gen Z" and "young people" when adults are meant. | young adults; Gen Z; college students; twenty-somethings |
| pregnant_postpartum | Pregnant & postpartum people | The health content is specifically about pregnant or postpartum people. Pregnancy or postpartum content takes this label only, not `population:women`. | pregnant women; expecting mothers; new moms |
| women | Women | The health content is specifically about women's health as women. | women; women over 40; female athletes |
| men | Men | The health content is specifically about men's health as men. | men; guys; men over 40 |
| midlife | Midlife adults | The health content is specifically about people in midlife (roughly 40 to 64). | over 40; after 50; midlife; middle-aged |
| older_adults | Older adults | The health content is specifically about older adults: 65+ or described as elderly, seniors or ageing parents. | seniors; elderly; over 65; aging parents |
| lgbtq | LGBTQ people | The health content is specifically about LGBTQ or transgender people. | trans kids; gay men; LGBTQ youth |
| athletes | Athletes & highly active people | The health content is specifically about athletes or the highly active. | athletes; NFL players; runners |
| military_veterans | Military & veterans | The health content is specifically about service members or veterans. | troops; soldiers; veterans; the VA; military personnel |
