"""Part 2: manual categorisation of the 60 sampled errors (see sva_error_dossiers.txt) and weighting.

Categories: i spec gap/ambiguity; ii clear spec, model did not follow (s = stochastic: the model
got it right in other samples / FP does not recur in >=50% of other samples; y = systematic);
iii gold debatable or wrong; iv matching/span artifact; v genuine subjectivity.
'rubric' marks a gap the annotator codebook settles but the candidate rubric omits.
"""

from collections import Counter, defaultdict

L = {
    # topic misses
    1: ("i", "melatonin supplements: Sleep lists melatonin, Supplements label missing co-label"),
    2: ("iv", "Opus split one mental-health treatment into sub-spans; DS one wide span matched another cluster"),
    3: ("ii-s", "AFib in a list of conditions -> other_health_topic although a listed topic applies (1/2)"),
    4: ("iv", "peptides: DS one 78-unit span, gold has several sub-span clusters"),
    5: ("i", "at-home genetic test: wearables (definition) vs genetics; annotators split 2/2"),
    6: ("i", "yoga study for sleep: intervention topic co-label (fitness) not required by rule; Opus only"),
    7: ("i", "symptom list 'trouble tasting or smelling' in a rhetorical pitch: no minimum-content rule"),
    8: ("ii-y", "ancestral/organic diet overhaul inside autism story: DS coded frames but no diet topic (0/2)"),
    # topic FPs
    9: ("iv", "extra same-label sub-span inside a gold span (7/7 samples)"),
    10: ("iv", "resumed EMF discussion as a second same-label detection"),
    11: ("iii", "StemRegen plant-blend study: Supplements defensible, no annotator coded it"),
    12: ("ii-s", "'health coach' tagged natural/alternative medicine (0/7 recurrence)"),
    13: ("iv", "DS split at a discourse-role change (as the rule says); gold one span"),
    14: ("iii", "pregnancy used as an analogy: codebook says analogies are passing detections"),
    # frame misses
    15: ("ii-y", "'Fauciism', 'smeared as a death cult': unanimous institution distrust, DS 1/8"),
    16: ("v", "'layer different things' on patients as optimization framing (2 of 4)"),
    17: ("ii-y", "'no seed oils' in an ad: definition lists seed oils; DS used purity instead (0/2)"),
    18: ("ii-s", "'God's retainer... God's plan' naturalness appeal, 4/4 (DS 1/2)"),
    19: ("v", "speaker rebuts a conspiracy mindset: which of distrust/big pharma/conspiracy frames"),
    20: ("i", "guest bio 'visionary biohacker ... peak performance': frame as description of a person"),
    # frame FPs
    21: ("i", "correcting mainstream advice (UV bad for eyes): debunking by definition, annotators coded anti-mainstream only"),
    22: ("ii-s", "'break the lock on fat burning' as optimization framing (0/1)"),
    23: ("i", "'medical profession brainwashed ... chiropractic dangerous': same debunking vs anti-mainstream boundary"),
    24: ("iv", "second medical_freedom detection inside the gold envelope (6/7)"),
    # evidence misses
    25: ("ii-s", "unanimous mechanistic language (arch width, epigenetic), DS 1/2"),
    26: ("iv", "gold holds two clusters for one personal-experience passage (Opus short, Sonnet long span)"),
    27: ("iii", "intro 'brilliant surgeon sister' with no claim: credential appeal needs a claim"),
    28: ("ii-s", "daughter's genes anecdote as evidence, DS 6/8"),
    29: ("v", "'how our cells power themselves' as mechanistic language (Opus only)"),
    30: ("ii-s", "patient anecdote coded weak_evidence instead of personal_experience in this sample (7/8)"),
    # evidence FPs
    31: ("iv", "same label split into sub-spans of a 44-unit gold span (6/7)"),
    32: ("i", "'guidelines called clinical trials limited': a negative evidence-strength statement, examples only list positive ones"),
    33: ("iii", "'we know there's good documentation that...' fits evidence_strength_claim; gold has citation only (6/7)"),
    34: ("ii-s", "vets in a pet telehealth ad as credential appeal (1/7)"),
    # claim misses
    35: ("ii-y", "'extra room for teeth -> less likely to collapse' checkable, 3/4, DS 0/2"),
    36: ("ii-s", "rebutted 'keep us sick to make money' claim, DS 1/2"),
    37: ("i", "1986 Vaccine Injury Act passed: legal history as a health claim? Opus only"),
    38: ("ii-s", "'eating fat cuts cravings' DS 5/8"),
    39: ("i", "compound 7h sleep / 90 min REM / 1h deep: splitting rule; two annotators also merged"),
    40: ("i-rubric", "sponsor copy 'no better way to be alert than sleeping well': codebook says extract sponsor claims, rubric omits it"),
    41: ("iii", "'nothing else falls into place without restorative sleep' is rhetoric more than a checkable claim"),
    42: ("ii-s", "'one bad night can throw off food choices' DS 5/8"),
    43: ("i", "'coleus is a plant in the mint family containing forskolin': composition fact, threshold unclear"),
    44: ("ii-s", "ad claim 'poor sleep drains cell battery' 4/4, DS 5/8"),
    # claim FPs
    45: ("ii-s", "'optimize VO2 max with HIIT' from a list of online advice (0/7)"),
    46: ("v", "perimenopause cycle-length description as a checkable claim"),
    47: ("iv", "DS split '15 calories and zero added sugar' into atomic claims; one-to-one leaves one unmatched"),
    48: ("i", "joke 'every doctor is busy shooting people up with 5G' (7/7; adjudicated rejected): no rule for jokes"),
    49: ("ii-s", "personal health-record anecdote (one gummy, not effective) extracted (0/1)"),
    50: ("iv", "claim text equals an acceptable singleton but a different quote fragment was cited"),
    # product misses
    51: ("iii", "'leave a review on iTunes' recorded as a product"),
    52: ("i-rubric", "own free guide named by URL and typed other_product; type fallback would match book_or_media"),
    53: ("ii-s", "'Athletic BBL' procedure, DS 7/8"),
    54: ("ii-s", "guest's own book 'Good Energy', DS 1/2"),
    55: ("iv", "gold duplicated as 'Eight Sleep' and 'Pod 5' clusters; DS matched one"),
    56: ("iv", "'Weight loss by Hers' vs 'Hers', type program vs 2/2 tie in gold"),
    # product FPs
    57: ("ii-y", "second Mitopure mention inside one continuous read (rule: one mention)"),
    58: ("ii-s", "black salve, a generic remedy, as a product (0/1)"),
    59: ("i", "named peptide compound 'Livogen': generic substance or product?"),
    60: ("i", "'YouTube channel' as a product; literal v1 rule includes it, annotators did not"),
}
GROUP = {**{k: "topic" for k in range(1, 15)}, **{k: "frame" for k in range(15, 25)}, **{k: "evidence" for k in range(25, 35)},
         **{k: "claim" for k in range(35, 51)}, **{k: "product" for k in range(51, 61)}}
TYPE = {k: "miss" for k in list(range(1, 9)) + list(range(15, 21)) + list(range(25, 31)) + list(range(35, 45)) + list(range(51, 57))}
POOL = {("topic", "miss"): 471, ("topic", "fp"): 130, ("frame", "miss"): 130, ("frame", "fp"): 42, ("evidence", "miss"): 102,
        ("evidence", "fp"): 61, ("claim", "miss"): 320, ("claim", "fp"): 59, ("product", "miss"): 42, ("product", "fp"): 24}


def major(c):
    return c.split("-")[0]


counts = defaultdict(Counter)
for k, (c, _) in L.items():
    counts[GROUP[k]][major(c)] += 1
    counts["all"][major(c)] += 1
cats = ["i", "ii", "iii", "iv", "v"]
print("| group | n | " + " | ".join(cats) + " |")
for g in ["topic", "frame", "evidence", "claim", "product", "all"]:
    n = sum(counts[g].values())
    print(f"| {g} | {n} | " + " | ".join(str(counts[g][c]) for c in cats) + " |")
sub = Counter(c for c, _ in L.values())
print("sub-codes", dict(sub))
# weight each sampled error by its stratum pool size / stratum sample size
w = Counter()
strata_n = Counter((GROUP[k], TYPE.get(k, "fp")) for k in L)
for k, (c, _) in L.items():
    key = (GROUP[k], TYPE.get(k, "fp"))
    w[c] += POOL[key] / strata_n[key]
tot = sum(w.values())
print("volume-weighted shares:", {c: round(v / tot, 2) for c, v in sorted(w.items())})
wm = Counter()
for c, v in w.items():
    wm[major(c)] += v
print("volume-weighted major:", {c: round(v / tot, 2) for c, v in sorted(wm.items())})
