"""Regexes quoted in the v8 corpus-review reports, attached to the label section they appear in.

    python exp/review_lexicon.py > exp/lexicon-review-v3.json
"""
import json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
taxonomy = json.loads((REPO / "benchmark/v3/taxonomy.json").read_text())
ids = {l["label_id"] for l in taxonomy["labels"]}
REGEXISH = re.compile(r"\\b|\||\(|\\w|\.\{|\?")
labels: dict[str, dict[str, list[str]]] = {}
for report in sorted((REPO / "taxonomy/v8-corpus-review/reports").glob("*.md")):
    current: list[str] = []
    for line in report.read_text().splitlines():
        if line.startswith("#"):
            found = []
            for token in re.findall(r"`([^`]+)`", line):
                for cand in (token, "topic:" + token):
                    if cand in ids:
                        found.append(cand)
                        break
            current = found
            continue
        if not current:
            continue
        for token in re.findall(r"`([^`]+)`", line):
            if token in ids or "topic:" + token in ids or not REGEXISH.search(token):
                continue
            try:
                re.compile(token, re.I)
            except re.error:
                continue
            for label in current:
                labels.setdefault(label, {"terms": [], "regex": []})["regex"].append(token)
print(json.dumps({"source": "v8 corpus review report queries", "labels": labels}, indent=1))
print(len(labels), "labels,", sum(len(v["regex"]) for v in labels.values()), "regexes", file=sys.stderr)
