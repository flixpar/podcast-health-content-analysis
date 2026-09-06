#!/usr/bin/env python3
"""Recall/savings curve for a keyword screen at three vocabulary tiers.

A screen is only worth running if it drops enough windows to matter while
keeping essentially everything the expensive pass would have found. Recall is
reported against two targets: any payload (a substantive detection or a claim),
and the high-value claims that actually reach verification -- editorial,
asserted, unhedged, confident.
"""

from __future__ import annotations

import collections
import io
import json
import re
import sqlite3
from pathlib import Path

import zstandard as zstd

FULLRUN = Path("outputs/fullrun")
STOP = {
    "health", "other", "content", "claims", "general",
    "uncategorised health content", "name the subject in the summary",
}

# Tier 2: ordinary language for bodies, symptoms and care. The pilot's misses
# were conversations about sex drive, spotting a squat and blood types -- health
# content carrying no clinical vocabulary for the taxonomy's terms to match.
BODY_LEXICON = """
ache aches aching allergic allergy ankle antibiotic anxious appetite arm artery
asleep aspirin asthma back bacteria bandage belly bladder bleed bleeding blood
bodies body bone bones bowel brain breast breath breathe breathing bruise burn
calorie calories cancer cavity cell cells cholesterol chronic clinic cold colon
concussion cough cramp cramps cure cured cut dehydrated dentist diagnose
diagnosed diagnosis diet dieting digest digestion disease doctor dose dosage
drink drinking drug drugs ear ears eat eating elbow emergency exercise exhausted
eye eyes faint fat fatigue fever finger fingers fit fitness flu food foot
gene genes genetic germ germs gut hair headache heal healing healed health
healthy heart hip hormone hormones hospital hurt hydrate hydration ill illness
immune infected infection inflamed inflammation injured injury insomnia
intestine itch itchy joint joints kidney knee leg legs liver lung lungs
medication medicine mental migraine mouth muscle muscles nail nausea nauseous
nerve nerves nurse nutrient nutrition obese obesity operation organ pain
painful patient penis period periods pharmacy physical pill pills poison
pregnancy pregnant prescription protein pulse rash recover recovery rehab
remedy rest scar seizure sex sexual shot sick sickness skin sleep sleeping
sleepy smoke smoking sneeze sore sperm spine stomach stress stressed stretch
stroke sugar supplement surgeon surgery swallow sweat swell swelling symptom
symptoms teeth tendon test therapist therapy throat thyroid tired tissue tooth
toxic trauma treat treated treatment tumor tumour urine uterus vaccine vein
virus vitamin vomit vomiting weight wellness workout wound wrist
""".split()

# Tier 3: the wellness/lifestyle register that surrounds health talk.
WELLNESS_LEXICON = """
addiction alcohol beer bourbon breathwork caffeine cannabis cigarette cigarettes
cocktail coffee detox drunk edible edibles energy fast fasting gym hangover
hydrated intoxicated joint keto lifting liquor macro meditate meditation
mindfulness nicotine organic paleo probiotic protein psychedelic recovery
routine sauna sober sobriety sleepschedule smoothie sober stimulant supplement
tequila therapy tobacco vape vaping vegan vitamin weed wellness whiskey wine
workout yoga
""".split()


def taxonomy_terms() -> tuple[set[str], set[str]]:
    tax = json.loads((FULLRUN / "taxonomy.json").read_text())
    words: set[str] = set()
    phrases: set[str] = set()
    for label in tax["labels"]:
        for item in list(label.get("concepts") or []) + re.split(r"[/&,]", label.get("name", "")):
            t = item.strip().strip("“”\"'").lower()
            t = re.sub(r"[^a-z0-9\s\-']", " ", t)
            t = re.sub(r"\s+", " ", t).strip()
            if not t or t in STOP or len(t) < 4:
                continue
            (phrases if " " in t else words).add(t)
    return words, phrases


def compile_screen(words: set[str], phrases: set[str]):
    wre = re.compile(r"\b(" + "|".join(sorted(map(re.escape, words), key=len, reverse=True)) + r")\b")
    pre = (
        re.compile("|".join(sorted(map(re.escape, phrases), key=len, reverse=True)))
        if phrases
        else None
    )

    def hit(text: str) -> bool:
        return bool(wre.search(text)) or bool(pre.search(text) if pre else False)

    return hit


def high_value(result: dict, ad_units: set[int]) -> int:
    """Claims that survive the funnel: editorial, asserted, unhedged, confident."""
    def n(uid: str) -> int:
        d = "".join(c for c in uid if c.isdigit())
        return int(d) if d else -1

    count = 0
    for v in result.get("verification_candidates") or []:
        rng = set(range(n(v["start_unit_id"]), n(v["end_unit_id"]) + 1))
        if rng & ad_units:
            continue
        if v["discourse_role"] != "asserted_or_endorsed":
            continue
        if v["expressed_certainty"] not in ("unhedged", "absolute"):
            continue
        if v["confidence"] < 0.8:
            continue
        count += 1
    return count


def main() -> None:
    tw, tp = taxonomy_terms()
    tiers = {
        "T1 taxonomy only": (set(tw), set(tp)),
        "T2 + body lexicon": (set(tw) | set(BODY_LEXICON), set(tp)),
        "T3 + wellness lexicon": (
            set(tw) | set(BODY_LEXICON) | set(WELLNESS_LEXICON),
            set(tp),
        ),
    }
    screens = {name: compile_screen(w, p) for name, (w, p) in tiers.items()}

    db = sqlite3.connect(FULLRUN / "labels.sqlite")
    truth: dict[str, dict] = {}
    for wid, rj in db.execute("SELECT window_id, result_json FROM window_labels"):
        r = json.loads(rj)

        def n(uid: str) -> int:
            d = "".join(c for c in uid if c.isdigit())
            return int(d) if d else -1

        ad: set[int] = set()
        for d in r.get("detections") or []:
            if d["relevance"] == "advertisement":
                ad.update(range(n(d["start_unit_id"]), n(d["end_unit_id"]) + 1))
        truth[wid] = {
            "sub": sum(1 for d in r.get("detections") or [] if d["relevance"] == "substantive"),
            "claims": len(r.get("verification_candidates") or []),
            "hv": high_value(r, ad),
        }

    stats: dict[str, collections.Counter] = {k: collections.Counter() for k in tiers}
    scanned = 0
    with open(FULLRUN / "windows.jsonl.zst", "rb") as fh:
        stream = io.TextIOWrapper(zstd.ZstdDecompressor().stream_reader(fh), encoding="utf-8")
        for line in stream:
            obj = json.loads(line)
            wid = obj["window_id"]
            t = truth.get(wid)
            if t is None:
                continue
            scanned += 1
            text = " ".join(u["text"] for u in obj["units"]).lower()
            payload = t["sub"] > 0 or t["claims"] > 0
            for name, hit_fn in screens.items():
                s = stats[name]
                hit = hit_fn(text)
                s["kept"] += hit
                if payload:
                    s["pos_payload"] += 1
                    s["rec_payload"] += hit
                if t["hv"]:
                    s["pos_hv"] += t["hv"]
                    s["rec_hv"] += t["hv"] if hit else 0
                    s["pos_hv_win"] += 1
                    s["rec_hv_win"] += hit
            if scanned == len(truth):
                break

    print(f"windows: {scanned}\n")
    header = f"{'tier':24s} {'vocab':>7s} {'kept':>7s} {'dropped':>8s} {'payload recall':>15s} {'high-value recall':>18s}"
    print(header)
    print("-" * len(header))
    for name, (w, p) in tiers.items():
        s = stats[name]
        kept = s["kept"]
        print(
            f"{name:24s} {len(w)+len(p):7d} {kept/scanned:6.1%} {1-kept/scanned:8.1%}"
            f" {s['rec_payload']}/{s['pos_payload']} = {s['rec_payload']/max(s['pos_payload'],1):5.1%}"
            f"   {s['rec_hv']}/{s['pos_hv']} = {s['rec_hv']/max(s['pos_hv'],1):5.1%}"
        )


if __name__ == "__main__":
    main()
