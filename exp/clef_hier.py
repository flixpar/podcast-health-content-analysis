"""Hierarchical TypeSafe cascade for the granular v7/v8 label sets, on local Clef.

The flat cascade (analysis/typesafe_labeling.py) asks one screening question per
label. The granular sets have 577 (v7) or 630 (v8) labels at ~116 tokens a
question on Clef, which does not fit one 64k request and would cost ~70k tokens
of prefill a window. So the screen is asked down the tree:

1. gates (health / claim / product), stop below the health gate;
2. screen-1: one question per topic parent (60), per narrative family (9) and per
   frame, evidence signal and population;
3. screen-2: the subtopics of the parents that reached `parent_threshold` (top
   `max_parents`) and the narratives of the families that reached
   `family_threshold`;
4. localize, draft spans, attributes and compose with the flat method's own code,
   with narrative and population added as axes; a parent with no subtopic above
   the fan-out threshold is labeled with the bare parent ID (the codebook's
   "no listed subtopic fits").

Every probability is kept in judgments.jsonl so composition thresholds can be
re-tuned offline (`tune`).

    python exp/clef_hier.py run --bench v2 --name clef-hier-v7 --api http://127.0.0.1:8302/v1
    python exp/clef_hier.py tune benchmark/v2/runs/clef-hier-v7
"""
from __future__ import annotations

import argparse
import itertools
import json
import sqlite3
import sys
import threading
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from analysis import topic_labeling as tl  # noqa: E402
from analysis import typesafe_labeling as ts  # noqa: E402
from analysis.benchmark.clef_screen import HEALTH_BROAD  # noqa: E402

METHOD = "typesafe-hier-v2"
AXES5 = ("topic", "narrative", "frame", "evidence", "population")

# The flat method's tables, extended to the two new axes.
ts.SCREEN_QUESTION.update({
    "narrative": "Does any speaker in `transcript` voice, question, report or rebut this contested health claim?",
    "population": "Is any of the health content in `transcript` specifically about this group of people?",
})
ts.PASSAGE_QUESTION.update({
    "narrative": "Does a speaker in `passages.{key}` voice, question, report or rebut the contested claim described in `subjects.{subject}`?",
    "population": "Is the health content in `passages.{key}` specifically about the group of people described in `subjects.{subject}`?",
})
ts.OTHER_TOPIC = "topic:other"
ts.MAX_DETECTIONS = 60

FAMILY_QUESTION = (
    "Does any speaker in `transcript` voice, question, report or rebut one of the contested health "
    "claims listed in this family?"
)


def make_policy(**overrides: Any) -> ts.Policy:
    """The clef-tuned flat policy with every per-axis table extended to five axes."""
    def five(topic, narrative, frame, evidence, population):
        return {"topic": topic, "narrative": narrative, "frame": frame, "evidence": evidence, "population": population}

    base = ts.Policy(
        passage_units={"topic": 3, "narrative": 3, "frame": 1, "evidence": 1, "population": 3},
        window_threshold=five(0.1, 0.3, 0.1, 0.1, 0.3),
        seed_threshold=five(0.6, 0.6, 0.5, 0.6, 0.6),
        extend_threshold=five(0.5, 0.5, 0.2, 0.2, 0.5),
        bridge_units={"topic": 0, "narrative": 1, "frame": 1, "evidence": 1, "population": 0},
        pregate=True,
        refine=True,
        claim_threshold=0.4,
        product_name_threshold=0.5,
        fanout_threshold=0.3,
        max_fanout_labels=30,
        health_gate_threshold=0.5,
    )
    return replace(base, **overrides)


HIER = {"parent_threshold": 0.3, "max_parents": 8, "family_threshold": 0.3, "max_families": 4}


def tree(taxonomy: Mapping[str, Any]) -> dict[str, Any]:
    labels = {label["label_id"]: label for label in taxonomy["labels"]}
    children: dict[str, list[str]] = defaultdict(list)
    families: dict[str, list[str]] = defaultdict(list)
    family_names: dict[str, str] = {}
    for label_id, label in labels.items():
        if label["axis"] == "topic" and label.get("level") == "subtopic":
            children[label["parent"]].append(label_id)
        if label["axis"] == "narrative":
            families[label["family"]].append(label_id)
            family_names[label["family"]] = label.get("family_name") or label["family"]
    parents = [label_id for label_id, label in labels.items() if label["axis"] == "topic" and label.get("level") == "parent"]
    flat = [label_id for label_id, label in labels.items() if label["axis"] in ("frame", "evidence", "population")]
    return {"labels": labels, "children": children, "families": families, "family_names": family_names, "parents": parents, "flat": flat}


def screen(window: Mapping[str, Any], t: dict[str, Any], policy: ts.Policy, session: ts._Session) -> dict[str, Any]:
    labels = t["labels"]
    transcript = {"transcript": " ".join(unit["text"] for unit in window["units"])}
    # The broad gate (analysis/benchmark/clef_screen.py) decides whether the window
    # is labeled at all: the method's own health gate is precise rather than
    # exhaustive and drops ~13% of substantive content on real windows.
    gate_q = {f"gate|{name}": q for name, q in {**ts.GATE_QUESTIONS, "broad": HEALTH_BROAD}.items()}
    answers = session.answers(transcript, gate_q, "gate")
    gates = {name: ts._noul(answers[f"gate|{name}"]) for name in [*ts.GATE_QUESTIONS, "broad"]}
    gates["health_precise"], gates["health"] = gates["health"], gates["broad"]
    probs: dict[str, float] = {}
    level1: dict[str, float] = {}
    if gates["health"] >= policy.health_gate_threshold:
        q1: dict[str, Any] = {}
        for parent in t["parents"]:
            label = labels[parent]
            instructions = {"question": ts.SCREEN_QUESTION["topic"], "name": label["name"], "definition": label["definition"]}
            kids = [labels[k]["name"] for k in t["children"].get(parent, [])]
            if kids:
                instructions["includes_subtopics"] = kids[:14]
            q1[f"parent|{parent}"] = {"type": "noul", "instructions": instructions}
        for family, members in t["families"].items():
            q1[f"family|{family}"] = {"type": "noul", "instructions": {
                "question": FAMILY_QUESTION, "family": t["family_names"][family],
                "claims": [labels[m]["name"] for m in members][:30]}}
        for label_id in t["flat"]:
            q1[f"label|{label_id}"] = ts.screen_question(labels[label_id], policy.screen_examples)
        a1 = session.answers(transcript, q1, "screen1")
        for key, value in a1.items():
            kind, name = key.split("|", 1)
            p = ts._noul(value)
            if kind == "label":
                probs[name] = p
            else:
                level1[name] = p
        top_parents = sorted((p for p in t["parents"] if level1[p] >= HIER["parent_threshold"]), key=lambda p: -level1[p])[: HIER["max_parents"]]
        top_families = sorted((f for f in t["families"] if level1[f] >= HIER["family_threshold"]), key=lambda f: -level1[f])[: HIER["max_families"]]
        q2: dict[str, Any] = {}
        for parent in top_parents:
            for kid in t["children"].get(parent, []):
                q2[f"label|{kid}"] = ts.screen_question(labels[kid], policy.screen_examples)
        for family in top_families:
            for member in t["families"][family]:
                q2[f"label|{member}"] = ts.screen_question(labels[member], policy.screen_examples)
        if q2:
            for key, value in session.answers(transcript, q2, "screen2").items():
                probs[key.split("|", 1)[1]] = ts._noul(value)
        # The bare parent stands for "this parent, no listed subtopic fits".
        for parent in top_parents:
            best_child = max((probs.get(k, 0.0) for k in t["children"].get(parent, [])), default=0.0)
            if best_child < policy.fanout_threshold:
                probs[parent] = level1[parent]
    return {"gates": gates, "level1": level1, "window": probs}


def localize(window, t, policy, session, judgments) -> None:
    labels = t["labels"]
    probs = judgments["window"]
    healthy = judgments["gates"]["health"] >= policy.health_gate_threshold
    fanout = sorted((k for k, p in probs.items() if healthy and p >= policy.fanout_threshold), key=lambda k: -probs[k])[: policy.max_fanout_labels]
    subjects = {k: (f"s{n:02d}", {"name": labels[k]["name"], "definition": labels[k]["definition"]}) for n, k in enumerate(fanout)}
    grids: dict[int, dict[str, Any]] = {}
    for label_id in fanout:
        axis = labels[label_id]["axis"]
        grids.setdefault(policy.passage_units[axis], {})[label_id] = (
            lambda key, axis=axis, subject=subjects[label_id][0]: ts.passage_question(axis, key, subject))
    gates = judgments["gates"]
    if healthy and gates["claim"] >= policy.gate_threshold:
        grids.setdefault(1, {})["claim"] = ts.claim_question
    if healthy and gates["product"] >= policy.gate_threshold:
        subjects["product"] = ("product", ts.PRODUCT_SUBJECT)
        grids.setdefault(1, {})["product"] = lambda key: ts.passage_question("product", key, "product")
    for size, builders in grids.items():
        if policy.refine and size == 1:
            ts._localize_coarse_to_fine(window, builders, subjects, policy, session, judgments)
            continue
        passages = ts._passages(window, size)
        state = {"note": ts.PASSAGE_NOTE, **ts._passage_state(window, passages),
                 "subjects": {subjects[n][0]: subjects[n][1] for n in builders if n in subjects}}
        questions = {f"{name}|{key}": build(key) for name, build in builders.items() for key, _ in passages}
        answers = session.answers(state, questions, f"localize_{size}")
        for name in builders:
            judgments["units" if name in ("claim", "product") else "labels"][name] = [ts._noul(answers[f"{name}|{key}"]) for key, _ in passages]


def compose(window, taxonomy, judgments, policy) -> dict[str, Any]:
    """The validated window result (as `run` stores it) for stored judgments under `policy`."""
    result = _compose(window, taxonomy, judgments, policy)
    axes = {label["label_id"]: label["axis"] for label in taxonomy["labels"]}
    return tl.validate_response_lenient(result, window, axes)[0]


def _compose(window, taxonomy, judgments, policy) -> dict[str, Any]:
    result = ts.compose_result(window, taxonomy, judgments, policy)
    # v7/v8 claims carry narrative links and relevance.
    index = {unit["unit_id"]: n for n, unit in enumerate(window["units"])}
    axes = {label["label_id"]: label["axis"] for label in taxonomy["labels"]}
    spans = [(index[d["start_unit_id"]], index[d["end_unit_id"]], d) for d in result["detections"]]
    for claim in result["verification_candidates"]:
        s, e = index[claim["start_unit_id"]], index[claim["end_unit_id"]]
        over = [d for a, b, d in spans if a <= e and s <= b]
        claim["narrative_ids"] = sorted({l for d in over for l in d["label_ids"] if axes.get(l) == "narrative"})
        rel = [d["relevance"] for d in over if axes.get(d["label_ids"][0]) == "topic"]
        claim["relevance"] = max(set(rel), key=rel.count) if rel else "substantive"
    return result


def label_window(window, taxonomy, t, policy, ask) -> tuple[dict[str, Any], dict[str, Any]]:
    session = ts._Session(ask, policy)
    judgments = screen(window, t, policy, session)
    judgments.update({"method_version": METHOD, "window_id": window["window_id"],
                      "passage_units": dict(policy.passage_units), "labels": {}, "units": {}, "attributes": {}})
    localize(window, t, policy, session, judgments)
    draft = ts.draft_annotations(window, taxonomy, judgments, policy)
    judgments["attributes"] = ts.judge_attributes(window, taxonomy, draft, policy, session)
    judgments["usage"] = {**session.usage, "input_tokens_by_stage": dict(session.by_stage)}
    return _compose(window, taxonomy, judgments, policy), judgments


def make_ask(apis: list[str], model: str = "clef"):
    counter = itertools.count()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def ask(state, questions):
        api = apis[next(counter) % len(apis)]
        body = json.dumps({"state": state, "model": model, "questions": questions}).encode()
        for attempt in range(4):
            try:
                request = urllib.request.Request(api + ts.ROUTE, data=body, headers={"Content-Type": "application/json"})
                with opener.open(request, timeout=1800) as response:
                    return json.loads(response.read())
            except Exception:  # noqa: BLE001
                if attempt == 3:
                    raise
                time.sleep(5)
    return ask


def load_windows(bench: str, windows_path: str | None, ids_file: str | None, split: str) -> list[dict[str, Any]]:
    if windows_path:
        ws = list(tl.iter_jsonl(Path(windows_path)))
        if ids_file:
            wanted = set(Path(ids_file).read_text().split())
            ws = [w for w in ws if w["window_id"] in wanted]
        return ws
    items = [json.loads(line) for line in open(REPO / f"benchmark/{bench}/items.jsonl")]
    return [i for i in items if split == "all" or i["split"] == split]


def cmd_run(args) -> int:
    taxonomy = json.loads((REPO / f"benchmark/{args.bench}/taxonomy.json").read_text())
    t = tree(taxonomy)
    policy = make_policy()
    HIER.update({k: getattr(args, k) for k in HIER if getattr(args, k, None) is not None})
    ask = make_ask(args.api, args.model)
    axes = {label["label_id"]: label["axis"] for label in taxonomy["labels"]}
    run_dir = Path(args.out_dir) if args.out_dir else REPO / f"benchmark/{args.bench}/runs/{args.name}"
    repeat = run_dir / "repeat_0"
    repeat.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(json.dumps({
        "name": args.name, "model": args.model, "provider": "local", "method": METHOD,
        "policy": asdict(policy), "hier": HIER, "bench": args.bench, "created_at": tl.utc_now()}, indent=2, default=str))
    con = sqlite3.connect(repeat / "labels.sqlite", check_same_thread=False)
    con.execute("CREATE TABLE IF NOT EXISTS window_labels (window_id TEXT PRIMARY KEY, result_json TEXT NOT NULL)")
    done = {r[0] for r in con.execute("SELECT window_id FROM window_labels")}
    lock = threading.Lock()
    log = open(repeat / "attempts.jsonl", "a")
    sidecar = open(repeat / "judgments.jsonl", "a")
    windows = [w for w in load_windows(args.bench, args.windows, args.ids_file, args.split) if w["window_id"] not in done]

    def one(window):
        started = time.monotonic()
        try:
            result, judgments = label_window(window, taxonomy, t, policy, ask)
            result, changes = tl.validate_response_lenient(result, window, axes)  # already valid; recorded for the log
            usage = judgments["usage"]
            with lock:
                con.execute("INSERT OR REPLACE INTO window_labels VALUES (?, ?)", (window["window_id"], json.dumps(result)))
                con.commit()
                sidecar.write(json.dumps(judgments) + "\n"); sidecar.flush()
                log.write(json.dumps({"attempt": 0, "ok": True, "window_id": window["window_id"], "seconds": round(time.monotonic() - started, 2),
                                      "usage": {"input_tokens": usage["input_tokens"], "output_tokens": 0}, "typesafe_usage": usage,
                                      "validation": {"mode": "lenient", **changes}}) + "\n"); log.flush()
            return True
        except Exception as error:  # noqa: BLE001
            with lock:
                log.write(json.dumps({"attempt": 0, "ok": False, "window_id": window["window_id"], "kind": getattr(error, "kind", type(error).__name__), "error": str(error)[:300]}) + "\n"); log.flush()
            return False

    started = time.monotonic()
    ok = 0
    with ThreadPoolExecutor(args.concurrency) as pool:
        futures = [pool.submit(one, w) for w in windows]
        for n, f in enumerate(as_completed(futures), 1):
            ok += f.result()
            if n % 20 == 0 or n == len(futures):
                print(f"done={n}/{len(futures)} ok={ok} elapsed={time.monotonic() - started:.0f}s", flush=True)
    return 0


def cmd_tune(args) -> int:
    """Sweep composition thresholds per axis on the dev split; write the best as a recomposed run."""
    import os
    os.environ.setdefault("BENCHMARK_DIR", f"benchmark/{args.bench}")
    from analysis.benchmark import references as refs_mod, scoring

    bench = REPO / f"benchmark/{args.bench}"
    taxonomy = json.loads((bench / "taxonomy.json").read_text())
    items = [json.loads(line) for line in open(bench / "items.jsonl")]
    gold = refs_mod.load_gold(bench / "gold.jsonl")
    run_dir = Path(args.run_dir)
    judg = {}
    for line in open(run_dir / "repeat_0/judgments.jsonl"):
        row = json.loads(line)
        judg[row["window_id"]] = row
    by_id = {i["window_id"]: i for i in items}
    dev = [i for i in items if i["split"] == "dev" and i["stratum"] in ("health_dense", "mixed", "null", "ad_read", "discourse", "rare_label", "narrative")]

    def evaluate(policy, subset):
        results = {i["window_id"]: compose(i, taxonomy, judg[i["window_id"]], policy) for i in subset if i["window_id"] in judg}
        report = scoring.score_run(subset, results, gold, {}, False)
        return report["all"]["groups"] if "all" in report else report["headline"]["groups"]

    policy = make_policy()
    grid = {"window_threshold": [0.1, 0.2, 0.3, 0.5, 0.7], "seed_threshold": [0.4, 0.5, 0.6, 0.7, 0.8], "extend_threshold": [0.2, 0.35, 0.5]}
    for axis in AXES5:
        best = None
        for w, s, e in itertools.product(grid["window_threshold"], grid["seed_threshold"], grid["extend_threshold"]):
            if e > s:
                continue
            p = replace(policy, window_threshold={**policy.window_threshold, axis: w}, seed_threshold={**policy.seed_threshold, axis: s}, extend_threshold={**policy.extend_threshold, axis: e})
            f1 = (evaluate(p, dev).get(f"detection:{axis}") or {}).get("f1_strict") or 0.0
            if best is None or f1 > best[0]:
                best = (f1, w, s, e)
        print(axis, best, flush=True)
        policy = replace(policy, window_threshold={**policy.window_threshold, axis: best[1]}, seed_threshold={**policy.seed_threshold, axis: best[2]}, extend_threshold={**policy.extend_threshold, axis: best[3]})
    best = None
    for c in [0.3, 0.4, 0.5, 0.6, 0.7]:
        p = replace(policy, claim_threshold=c)
        f1 = (evaluate(p, dev).get("claim") or {}).get("f1_strict") or 0.0
        if best is None or f1 > best[0]:
            best = (f1, c)
    print("claim", best)
    policy = replace(policy, claim_threshold=best[1])
    out = Path(args.out or str(run_dir) + "-tuned")
    results = {wid: compose(by_id[wid], taxonomy, j, policy) for wid, j in judg.items() if wid in by_id}
    sys.path.insert(0, str(REPO / "exp"))
    from keywords import write_run
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    manifest.update(name=out.name, policy=asdict(policy), tuned_on="dev")
    write_run(out, manifest, [results])
    import shutil
    shutil.copy(run_dir / "repeat_0/attempts.jsonl", out / "repeat_0/attempts.jsonl")
    print("wrote", out)
    return 0


def policy_from(manifest_path: Path) -> ts.Policy:
    stored = json.loads(Path(manifest_path).read_text())["policy"]
    return ts.Policy(**{k: v for k, v in stored.items() if k in {f.name for f in __import__("dataclasses").fields(ts.Policy)}})


def cmd_apply(args) -> int:
    """Recompose a run's stored judgments under the policy another (tuned) run recorded."""
    bench = REPO / f"benchmark/{args.bench}"
    taxonomy = json.loads((bench / "taxonomy.json").read_text())
    items = {i["window_id"]: i for i in map(json.loads, open(bench / "items.jsonl"))}
    policy = policy_from(Path(args.policy_run) / "run_manifest.json")
    run_dir = Path(args.run_dir)
    judg = {r["window_id"]: r for r in map(json.loads, open(run_dir / "repeat_0/judgments.jsonl"))}
    results = {w: compose(items[w], taxonomy, j, policy) for w, j in judg.items() if w in items}
    sys.path.insert(0, str(REPO / "exp"))
    from keywords import write_run
    import shutil
    out = Path(args.out)
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    manifest.update(name=out.name, policy=asdict(policy), policy_from=str(args.policy_run))
    write_run(out, manifest, [results])
    shutil.copy(run_dir / "repeat_0/attempts.jsonl", out / "repeat_0/attempts.jsonl")
    print("wrote", out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--bench", default="v2")
    r.add_argument("--name", required=True)
    r.add_argument("--api", nargs="+", default=["http://127.0.0.1:8302/v1"])
    r.add_argument("--model", default="clef")
    r.add_argument("--split", default="all")
    r.add_argument("--windows")
    r.add_argument("--ids-file")
    r.add_argument("--out-dir")
    r.add_argument("--concurrency", type=int, default=16)
    for k in HIER:
        r.add_argument("--" + k.replace("_", "-"), dest=k, type=type(HIER[k]))
    u = sub.add_parser("tune")
    u.add_argument("run_dir")
    u.add_argument("--bench", default="v2")
    u.add_argument("--out")
    a = sub.add_parser("apply")
    a.add_argument("run_dir")
    a.add_argument("--policy-run", required=True)
    a.add_argument("--bench", default="v3")
    a.add_argument("--out", required=True)
    args = parser.parse_args()
    return {"run": cmd_run, "tune": cmd_tune, "apply": cmd_apply}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
