"""Validate analysis/fast/lexicon.json: label names, regex compilation, duplicates.

Run: .venv/bin/python analysis/fast/validate_lexicon.py
"""
import json, re, sys, collections
from pathlib import Path

base = Path(__file__).resolve().parent
repo = base.parent.parent
lex = json.loads((base / "lexicon.json").read_text())
sys.path.insert(0, str(repo / "analysis"))

import topic_labeling as t
tax = t.compile_taxonomy(repo / "topics.md")
valid = {l["label_id"].split(":",1)[1]: l for l in tax["labels"]}
topic_keys = {k for k,l in valid.items() if l["kind"]=="topic"}
frame_keys = {k for k,l in valid.items() if l["axis"]=="frame"}
ev_keys = {k for k,l in valid.items() if l["axis"]=="evidence"}
errs=[]
for sec, keys in [("topics",topic_keys),("frames",frame_keys),("evidence",ev_keys)]:
    got=set(lex[sec])
    if got-keys: errs.append(f"{sec}: unknown labels {sorted(got-keys)}")
    if keys-got: errs.append(f"{sec}: missing labels {sorted(keys-got)}")
REGEX_CHARS = set("()|?[]\\")
counts=collections.Counter(); nterms=0; bad=[]
def check(terms, where):
    global nterms
    seen=set()
    for term in terms:
        nterms+=1
        if term in seen: bad.append(f"duplicate term {term!r} in {where}")
        seen.add(term)
        if not term.islower() and term.lower()!=term: bad.append(f"non-lowercase {term!r} in {where}")
        pat = term if REGEX_CHARS & set(term) else re.escape(term)
        try: re.compile(r"\b(?:"+pat+r")\b")
        except re.error as e: bad.append(f"bad regex in {where}: {term!r}: {e}")
for sec in ["topics","frames","evidence","narratives","products"]:
    counts[sec]=len(lex[sec])
    for k,v in lex[sec].items():
        assert v["terms"], k
        if len(v["terms"])<5 and sec in ("topics",): bad.append(f"{sec}:{k} has <5 terms")
        check(v["terms"], f"{sec}:{k}")
for k,v in lex["narratives"].items():
    if v["topic"] not in topic_keys: errs.append(f"narrative {k}: bad topic {v['topic']}")
    for f in ("description","note","terms","topic"):
        if f not in v: errs.append(f"narrative {k} missing {f}")
types={"supplement","medication","food or beverage","device or wearable","test","app or digital service","clinic or practitioner service","programme or course","book or media","personal care","other"}
for k,v in lex["products"].items():
    if v["type"] not in types: errs.append(f"product {k}: bad type {v['type']}")
    if not isinstance(v["health_related"], bool): errs.append(f"product {k}: health_related not bool")
check(lex["commercial"]["terms"],"commercial"); counts["commercial"]=len(lex["commercial"]["terms"])
for k in lex["certainty"]: check(lex["certainty"][k]["terms"], f"certainty:{k}"); counts["certainty:"+k]=len(lex["certainty"][k]["terms"])
check(lex["distrust"]["terms"],"distrust"); counts["distrust"]=len(lex["distrust"]["terms"])
check(lex["correction"]["terms"],"correction"); counts["correction"]=len(lex["correction"]["terms"])
print("sections:", dict(counts))
print("total terms:", nterms)
print("term span:", {s: (min(len(v["terms"]) for v in lex[s].values()), max(len(v["terms"]) for v in lex[s].values())) for s in ["topics","frames","evidence","narratives","products"]})
print("health_related products:", sum(1 for v in lex["products"].values() if v["health_related"]), "of", len(lex["products"]))
print("ERRORS:", errs or "none")
print("TERM ISSUES:", bad or "none")
sys.exit(1 if (errs or bad) else 0)
