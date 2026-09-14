"""Extract per-(run, repeat, item) scoring rows and atom-level matches for the thinking-budget analysis."""
import json, os, pickle, sys
from pathlib import Path
from analysis.benchmark import ITEMS_PATH, GOLD_PATH, TAXONOMY_PATH, AGREEMENT_PATH
from analysis.benchmark import items as im, references as rm, runner, scoring
from analysis.benchmark.matching import WindowIndex, explode, assign
from analysis.benchmark.taxonomy import alias_map, load_benchmark_taxonomy

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "benchmark/runs"
OUT = Path(sys.argv[1])
NAMES = ["dev-high-chat-lenient", "dev-high-budget16k-lenient", "s70-high-chat-lenient", "s70-high-budget16k-lenient",
         "s70-high-budget12k-lenient", "s70-high-budget8k-lenient", "s70-high-budget4k-lenient"]

items = [i for i in im.load_items(ITEMS_PATH) if i.get("split") == "dev" and i.get("source") != "contrast"]
gold = rm.load_gold(GOLD_PATH)
aliases = alias_map(load_benchmark_taxonomy(TAXONOMY_PATH), None)
agreement = json.loads(AGREEMENT_PATH.read_text())
adjacency = rm.adjacency_set(agreement.get("label_adjacency", []))

def atom_dict(a):
    return dict(kind=a.kind, axis=a.axis, label=a.label, start=a.start, end=a.end, attributes=a.attributes,
                quote=a.quote, claim_text=a.claim_text, product=a.product_name, labels=a.labels, conf=a.confidence)

data = {"items": {i["item_id"]: i for i in items}, "gold": {}, "runs": {}}
for i in items:
    data["gold"][i["item_id"]] = [g.__dict__ for g in gold[i["item_id"]]]
for name in NAMES:
    run_dir = RUNS / name
    run = runner.load_run(run_dir)
    for k, results in enumerate(run["repeats"]):
        rep = run_dir / f"repeat_{k}"
        if not (rep / "repeat_manifest.json").exists():
            print("skip incomplete", name, k); continue
        usage = {}
        for line in (rep / "attempts.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r.get("ok"):
                u = r["usage"]
                usage[r["window_id"]] = dict(reasoning=(u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                                             completion=u.get("completion_tokens") or u.get("output_tokens"))
        rows = {}
        for item in items:
            wid = item["window_id"]
            if wid not in results:
                continue
            golds = gold[item["item_id"]]
            row = scoring.score_item(item, results[wid], golds, aliases, adjacency)
            idx = WindowIndex(item)
            preds = explode(results[wid], idx, aliases)
            scorable = [g for g in golds if g.tier != "rejected"]
            m = assign(preds, scorable)
            pred_gold = {pi: scorable[gj].gold_id for pi, gj, _ in m}
            row["preds"] = [dict(atom_dict(p), gold_id=pred_gold.get(n)) for n, p in enumerate(preds)]
            row["matched_gold"] = sorted(set(pred_gold.values()))
            row["usage"] = usage.get(wid)
            row["result"] = results[wid]
            rows[item["item_id"]] = row
        data["runs"][(name, k)] = rows
        print(name, k, len(rows))
pickle.dump(data, open(OUT, "wb"))
