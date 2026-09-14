"""Scratch: score every cross-model run per item/repeat and keep per-atom match status."""
import json, pickle, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from analysis.benchmark import references as refs_mod, runner as runner_mod
from analysis.benchmark.scoring import score_item, group_of, CREDIT_TIERS
from analysis.benchmark.matching import WindowIndex, explode, assign, near_miss_class
from analysis.benchmark.taxonomy import load_benchmark_taxonomy, alias_map
from analysis.benchmark import AGREEMENT_PATH, TAXONOMY_PATH

RUNS = ["s70-high-lenient", "gptoss-high-lenient", "gptoss-medium-lenient", "q35-think-lenient",
        "q35-none-lenient", "gemma4-think-lenient", "s70-none-lenient"]
root = Path(__file__).resolve().parents[1]
items = [json.loads(l) for l in open(root / "sample-dev70.jsonl")]
gold = refs_mod.load_gold()
taxonomy = load_benchmark_taxonomy(TAXONOMY_PATH)
aliases = alias_map(taxonomy, None)
agreement = json.loads(AGREEMENT_PATH.read_text())
adjacency = refs_mod.adjacency_set(agreement.get("label_adjacency", []))
out = {"items": {i["item_id"]: {k: i[k] for k in ("item_id", "window_id", "stratum", "split")} for i in items}, "runs": {}}
for name in RUNS:
    run = runner_mod.load_run(root / name)
    reps = []
    for results in run["repeats"]:
        per_item = {}
        for item in items:
            golds = gold[item["item_id"]]
            result = results.get(item["window_id"])
            row = score_item(item, result, golds, aliases, adjacency)
            index = WindowIndex(item)
            preds = explode(result, index, aliases) if result else []
            scorable = [g for g in golds if g.tier != "rejected"]
            m = {i: (j, s) for i, j, s in assign(preds, scorable)}
            patoms = []
            for i, p in enumerate(preds):
                st = "fp"
                gid = None
                if i in m:
                    g = scorable[m[i][0]]; gid = g.gold_id
                    st = "tp" if g.tier in CREDIT_TIERS else "unscored"
                patoms.append(dict(group=group_of(p), label=p.label, span=(p.start, p.end), status=st, gold_id=gid,
                                   cls=None if st != "fp" else near_miss_class(p, scorable),
                                   quote=p.quote, claim=p.claim_text, product=p.product_name, conf=p.confidence,
                                   attrs=p.attributes, labels=p.labels))
            matched_ids = {scorable[j].gold_id for j, _ in m.values()}
            per_item[item["item_id"]] = dict(row=row, preds=patoms, matched_gold=matched_ids, labeled=result is not None, result=result)
        reps.append(per_item)
    out["runs"][name] = dict(reps=reps, attempts=run["attempts"], manifest=run["manifest"])
out["gold"] = {iid: [dict(gold_id=g.gold_id, group=group_of(g), label=g.label, tier=g.tier, tight=g.tight, envelope=g.envelope,
                          quotes=g.quotes, claim_texts=g.claim_texts, product_names=g.product_names, support=g.support, votes=g.votes)
                     for g in gold[iid]] for iid in out["items"]}
pickle.dump(out, open(sys.argv[1], "wb"))
print("ok")
