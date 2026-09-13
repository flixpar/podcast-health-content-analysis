"""Command line for the labeling benchmark: python -m analysis.benchmark <cmd>."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from analysis import topic_labeling as tl
from analysis.benchmark import (
    ADJUDICATION_PATH,
    AGREEMENT_PATH,
    ANNOTATORS_PATH,
    BENCHMARK_VERSION,
    CONFIG_PATH,
    GOLD_PATH,
    ITEMS_PATH,
    MANIFEST_PATH,
    POOL_DIR,
    REFERENCES_DIR,
    REPO_ROOT,
    RUNS_DIR,
    TAXONOMY_PATH,
)
from analysis.benchmark import items as items_mod
from analysis.benchmark import references as refs_mod
from analysis.benchmark import report as report_mod
from analysis.benchmark import runner as runner_mod
from analysis.benchmark import scoring as scoring_mod
from analysis.benchmark import synthetic as synth_mod
from analysis.benchmark import tasks as tasks_mod
from analysis.benchmark.taxonomy import (
    alias_map,
    compile_benchmark_taxonomy,
    label_axes,
    load_benchmark_taxonomy,
)

VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _items_by_window(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["window_id"]: item for item in items}


# --------------------------------------------------------------------------
# Items
# --------------------------------------------------------------------------


def cmd_taxonomy(args: argparse.Namespace) -> int:
    config = items_mod.load_config(args.config)
    taxonomy = compile_benchmark_taxonomy(items_mod.resolve_path(config["paths"]["topics"]), args.out)
    _print({"labels": len(taxonomy["labels"]), "taxonomy_sha256": taxonomy["taxonomy_sha256"], "out": str(args.out)})
    return 0


def cmd_pool(args: argparse.Namespace) -> int:
    config = items_mod.load_config(args.config)
    _print(items_mod.build_pool(config, args.out_dir, args.seed, log=sys.stderr))
    return 0


def cmd_select(args: argparse.Namespace) -> int:
    config = items_mod.load_config(args.config)
    existing = items_mod.load_items(args.items) if args.grow else []
    selected = items_mod.select_items(config, args.pool, args.screening, existing=existing, seed=args.seed)
    count, sha = items_mod.write_items(args.items, selected)
    _print({**items_mod.composition(selected), "written": count, "file_sha256": sha})
    return 0


def cmd_screen_tasks(args: argparse.Namespace) -> int:
    config = items_mod.load_config(args.config)
    pool = list(tl.iter_jsonl(args.pool))
    if args.strata:
        pool = [row for row in pool if row["pool_stratum"] in args.strata]
    run_dir = tasks_mod.screening_bundles(pool, args.bundle_size, args.run_id, args.seed or config["benchmark"]["seed"])
    manifest = json.loads((run_dir / "manifest.json").read_text())
    _print({"run_dir": str(run_dir), "bundles": len(manifest["bundles"]), "windows": len(pool)})
    return 0


def cmd_screen_ingest(args: argparse.Namespace) -> int:
    pool = list(tl.iter_jsonl(args.pool))
    rows, problems = tasks_mod.ingest_screening(args.run_dir, {row["window_id"] for row in pool})
    for problem in problems:
        print(f"problem: {problem}", file=sys.stderr)
    existing = items_mod.load_screening(args.out) if args.out.exists() else {}
    for row in rows:
        existing[row["window_id"]] = row
    count, _ = tl.write_jsonl_atomic(args.out, sorted(existing.values(), key=lambda r: r["window_id"]))
    _print({"ingested": len(rows), "total": count, "verdicts": dict(Counter(r["verdict"] for r in existing.values())), "problems": len(problems)})
    return 0 if not problems else 2


# --------------------------------------------------------------------------
# Synthetic and contrast
# --------------------------------------------------------------------------


def cmd_synthetic_tasks(args: argparse.Namespace) -> int:
    run_dir = synth_mod.synthetic_bundles(args.run_id, args.per_bundle)
    _print({"run_dir": str(run_dir), "specs": len(synth_mod.SYNTHETIC_SPECS)})
    return 0


def cmd_synthetic_ingest(args: argparse.Namespace) -> int:
    items = items_mod.load_items(args.items)
    by_id = {item["item_id"]: item for item in items}
    added = 0
    problems = []
    for path, parsed in tasks_mod.read_bundle_outputs(args.run_dir, "synthetic.json"):
        if not isinstance(parsed, list):
            problems.append(f"{path}: not a JSON array")
            continue
        for entry in parsed:
            try:
                item = synth_mod.synthetic_item(entry)
            except (items_mod.BenchmarkError, KeyError, TypeError, ValueError) as exc:
                problems.append(f"{path}: {entry.get('slug') if isinstance(entry, dict) else '?'}: {exc}")
                continue
            by_id[item["item_id"]] = item
            added += 1
    for problem in problems:
        print(f"problem: {problem}", file=sys.stderr)
    config = items_mod.load_config(args.config)
    unsplit = [item for item in by_id.values() if not item.get("split")]
    if unsplit:
        items_mod.assign_split(unsplit, float(config["split"]["test_fraction"]), int(config["benchmark"]["seed"]) + 7)
    count, _ = items_mod.write_items(args.items, by_id.values())
    _print({"added": added, "items": count, "problems": len(problems)})
    return 0 if not problems else 2


def cmd_contrast_tasks(args: argparse.Namespace) -> int:
    import random

    config = items_mod.load_config(args.config)
    items = items_mod.load_items(args.items)
    gold = refs_mod.load_gold(args.gold) if args.gold.exists() else {}
    rng = random.Random(int(config["benchmark"]["seed"]) + 11)
    plan = synth_mod_plan(items, gold, args.pairs, rng)
    run_dir = synth_mod.contrast_bundles(plan, args.run_id, args.per_bundle)
    _print({"run_dir": str(run_dir), "pairs": len(plan), "perturbations": dict(Counter(p for _, p in plan))})
    return 0


def synth_mod_plan(items, gold, pairs, rng):
    """Choose (base item, perturbation) pairs whose gold has a suitable target."""
    from analysis.benchmark.synthetic import PERTURBATIONS

    def has(item_id, kind, field=None, values=None):
        for atom in gold.get(item_id, []):
            if atom.kind != kind or atom.tier != "required":
                continue
            if field is None:
                return True
            if str(atom.plurality(field)) in (values or []):
                return True
        return False

    candidates = [i for i in items if i.get("source") == "corpus" and i.get("split") == "dev" and i["stratum"] != "null"]
    rng.shuffle(candidates)
    plan = []
    used = set()
    names = list(PERTURBATIONS)
    # One pair per perturbation first (so decoys and the no-op are always
    # present), then a second round in table order until the quota is met.
    rounds = [(name, 1) for name in names] + [(name, 2) for name in names]
    for name, round_number in rounds:
        if len(plan) >= pairs:
            break
        spec = PERTURBATIONS[name]
        exp = spec["expect"]
        taken = 0
        per = 1
        for item in candidates:
            if item["item_id"] in used or taken >= per:
                continue
            ok = True
            if exp.get("kind") == "claim":
                ok = has(item["item_id"], "claim", exp.get("field"), exp.get("from"))
                if "hold" in exp:
                    ok = ok and has(item["item_id"], "claim", "discourse_role", exp["hold"]["discourse_role"])
            elif exp.get("kind") == "product":
                ok = has(item["item_id"], "product", exp.get("field"), exp.get("from")) if exp.get("field") else has(item["item_id"], "product")
            elif exp.get("kind") == "detection":
                ok = has(item["item_id"], "detection")
            if not gold:
                ok = item["stratum"] in ("health_dense", "ad_read", "discourse", "mixed")
            if ok:
                plan.append((item, name))
                used.add(item["item_id"])
                taken += 1
    return plan[:pairs]


def cmd_contrast_ingest(args: argparse.Namespace) -> int:
    items = items_mod.load_items(args.items)
    by_id = {item["item_id"]: item for item in items}
    added = 0
    problems = []
    for path, parsed in tasks_mod.read_bundle_outputs(args.run_dir, "twins.json"):
        if not isinstance(parsed, list):
            problems.append(f"{path}: not a JSON array")
            continue
        for entry in parsed:
            try:
                base = by_id[entry["base_item_id"]] if "base_item_id" in entry else by_id[entry["pair_id"].split("--")[0]]
                twin = synth_mod.contrast_item(entry, base)
            except (items_mod.BenchmarkError, KeyError, TypeError, ValueError) as exc:
                problems.append(f"{path}: {entry.get('pair_id') if isinstance(entry, dict) else '?'}: {exc}")
                continue
            by_id[twin["item_id"]] = twin
            added += 1
    for problem in problems:
        print(f"problem: {problem}", file=sys.stderr)
    count, _ = items_mod.write_items(args.items, by_id.values())
    _print({"added": added, "items": count, "problems": len(problems)})
    return 0 if not problems else 2


# --------------------------------------------------------------------------
# References and gold
# --------------------------------------------------------------------------


def cmd_validate_result(args: argparse.Namespace) -> int:
    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    bundle_items = json.loads((args.bundle / "items.json").read_text(encoding="utf-8"))
    report = tasks_mod.validate_results_file(args.results, bundle_items, label_axes(taxonomy))
    bad = 0
    for window_id, kind, message in report:
        if kind is None:
            print(f"{window_id}: ok")
        else:
            bad += 1
            print(f"{window_id}: REJECTED {kind}: {message}")
    print(f"{len(report) - bad} ok, {bad} rejected")
    return 0 if bad == 0 else 2


def cmd_reference_tasks(args: argparse.Namespace) -> int:
    config = items_mod.load_config(args.config)
    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    items = items_mod.load_items(args.items)
    # Contrast twins are left out unless asked for by stratum: they exist to be
    # compared with their base, but annotating them too lets the perturbation
    # spec be checked against the annotators themselves.
    if args.strata:
        items = [i for i in items if i["stratum"] in args.strata]
    else:
        items = [i for i in items if i.get("source") != "contrast"]
    if args.only_missing:
        existing = refs_mod.load_references()
        items = [i for i in items if args.annotator not in existing.get(i["item_id"], {})]
    validate_command = (
        f"cd {REPO_ROOT} && {VENV_PYTHON} -m analysis.benchmark validate-result "
        f"<bundle_dir>/results.json --bundle <bundle_dir>"
    )
    seed = int(config["benchmark"]["seed"]) + sum(ord(c) for c in args.annotator)
    run_dir = tasks_mod.reference_bundles(
        items, args.annotator, args.bundle_size, args.null_bundle_size, args.run_id, seed, taxonomy, validate_command
    )
    # Substitute the real bundle path into each bundle's instructions.
    for bundle_dir in sorted(run_dir.glob("bundle_*")):
        path = bundle_dir / "INSTRUCTIONS.md"
        path.write_text(path.read_text(encoding="utf-8").replace("<bundle_dir>", str(bundle_dir)), encoding="utf-8")
    manifest = json.loads((run_dir / "manifest.json").read_text())
    _print({"run_dir": str(run_dir), "bundles": len(manifest["bundles"]), "items": len(items)})
    return 0


def cmd_reference_ingest(args: argparse.Namespace) -> int:
    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    items = items_mod.load_items(args.items)
    stored, problems = tasks_mod.ingest_references(args.run_dir, args.annotator, _items_by_window(items), label_axes(taxonomy))
    for problem in problems:
        print(f"problem: {problem}", file=sys.stderr)
    refs_mod.register_annotator({"annotator_id": args.annotator, "model": args.model, "method": args.method, "authority": args.authority})
    _print({"stored": stored, "problems": len(problems)})
    return 0 if not problems else 2


def cmd_reference_add_run(args: argparse.Namespace) -> int:
    """Register a benchmark run's first repeat as a reference annotator."""
    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    items = items_mod.load_items(args.items)
    run = runner_mod.load_run(args.run_dir)
    results = run["repeats"][args.repeat] if run["repeats"] else {}
    stored = 0
    for item in items:
        result = results.get(item["window_id"])
        if result is None:
            continue
        normalized = refs_mod.validate_result(result, item, label_axes(taxonomy))
        refs_mod.store_reference(item["item_id"], args.annotator, normalized, None, {"run_dir": str(args.run_dir), "repeat": args.repeat, "run_fingerprint": run["manifest"].get("run_fingerprint")})
        stored += 1
    refs_mod.register_annotator({"annotator_id": args.annotator, "model": run["manifest"].get("model"), "method": f"run:{run['manifest'].get('name')}", "authority": args.authority})
    _print({"stored": stored})
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    items = items_mod.load_items(args.items)
    references = refs_mod.load_references(args.references)
    annotators = refs_mod.load_annotators()
    overlay = refs_mod.load_adjudication(args.adjudication)
    records, agreement = refs_mod.aggregate(items, references, annotators, overlay)
    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    aliases = alias_map(taxonomy, None)
    agreement["label_adjacency"] = refs_mod.label_adjacency(items, references)
    adjacency = refs_mod.adjacency_set(agreement["label_adjacency"])
    agreement["leave_one_out"] = refs_mod.leave_one_out(items, references, annotators, overlay, aliases, adjacency)
    from analysis.benchmark.contrast import annotator_contrast_validity

    gold_atoms: dict[str, list] = {}
    for record in records:
        gold_atoms.setdefault(record["item_id"], []).append(refs_mod.gold_from_record(record))
    agreement["contrast_validity"] = annotator_contrast_validity(items, references, aliases, gold_atoms)
    plants = refs_mod.check_plants(items, records)
    agreement["synthetic_plants"] = {
        "checked": len(plants),
        "ok": sum(1 for p in plants if p["ok"]),
        "missing": [p for p in plants if p["verdict"] == "missing"],
        "singleton": [p for p in plants if p["verdict"] == "singleton"],
        "contradicted": [p for p in plants if p["verdict"] == "contradicted"],
        "split": [p for p in plants if p["verdict"] == "split"],
    }
    count, sha = tl.write_jsonl_atomic(args.gold, records)
    tl.write_json(args.agreement, agreement)
    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "created_at": tl.utc_now(),
        "items": len(items),
        "items_hash": items_mod.items_hash(items),
        "composition": items_mod.composition(items),
        "taxonomy_sha256": taxonomy["taxonomy_sha256"],
        "annotators": sorted(annotators),
        "gold_atoms": count,
        "gold_sha256": sha,
        "tiers": agreement["tiers"],
    }
    tl.write_json(MANIFEST_PATH, manifest)
    summary = {
        "gold_atoms": count,
        "gold_sha256": sha,
        "tiers": agreement["tiers"],
        "items_with_references": agreement["items_with_references"],
        "annotators_per_item": agreement["annotators_per_item"],
        "synthetic_plants": {k: (v if isinstance(v, int) else len(v)) for k, v in agreement["synthetic_plants"].items()},
        "label_adjacency_pairs": len(agreement["label_adjacency"]),
        "leave_one_out_topic_f1": {a: (v["groups"].get("detection:topic") or {}).get("f1_strict") for a, v in agreement["leave_one_out"].items()},
    }
    _print(summary)
    for plant in agreement["synthetic_plants"]["missing"]:
        print(f"plant missing: {plant['item_id']} {plant['kind']} {plant['label'] or ''} {plant['span']}", file=sys.stderr)
    for verdict in ("singleton", "contradicted", "split"):
        for plant in agreement["synthetic_plants"][verdict]:
            detail = {k: (v["planted"], v["plurality"]) for k, v in plant["attribute_mismatches"].items()}
            print(f"plant {verdict}: {plant['item_id']} {plant['kind']} {plant['label'] or ''} {plant['span']} {detail or ''}", file=sys.stderr)
    return 0


def cmd_adjudicate_tasks(args: argparse.Namespace) -> int:
    config = items_mod.load_config(args.config)
    items = items_mod.load_items(args.items)
    records = list(tl.iter_jsonl(args.gold))
    run_dir = tasks_mod.adjudication_bundles(items, records, args.run_id, args.per_bundle, int(config["benchmark"]["seed"]))
    manifest = json.loads((run_dir / "manifest.json").read_text())
    _print({"run_dir": str(run_dir), "bundles": len(manifest["bundles"]), "singletons": sum(1 for r in records if r["tier"] == "singleton")})
    return 0


def cmd_adjudicate_ingest(args: argparse.Namespace) -> int:
    records = list(tl.iter_jsonl(args.gold))
    valid = {(r["item_id"], r["gold_id"]): r["members"][0] for r in records if r["tier"] == "singleton"}
    rows, problems = tasks_mod.ingest_adjudication(args.run_dir, valid)
    for problem in problems:
        print(f"problem: {problem}", file=sys.stderr)
    existing = {(r["item_id"], r.get("member") or r["gold_id"]): r for r in tl.iter_jsonl(args.out)} if args.out.exists() else {}
    for row in rows:
        existing[(row["item_id"], row["member"])] = row
    count, _ = tl.write_jsonl_atomic(args.out, sorted(existing.values(), key=lambda r: (r["item_id"], r.get("member") or r["gold_id"])))
    _print({"ingested": len(rows), "total": count, "tiers": dict(Counter(r["tier"] for r in existing.values())), "problems": len(problems)})
    return 0 if not problems else 2


# --------------------------------------------------------------------------
# Runs and scoring
# --------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    items = items_mod.load_items(args.items)
    if args.split != "all":
        items = [i for i in items if i.get("split") == args.split]
    if args.strata:
        items = [i for i in items if i["stratum"] in args.strata]
    if args.limit:
        items = items[: args.limit]
    label_argv = list(args.label_args or [])
    if label_argv and label_argv[0] == "--":
        label_argv = label_argv[1:]
    pipeline_args = runner_mod.label_args(label_argv, args.pipeline_config)
    manifest = runner_mod.run_benchmark(
        items, taxonomy, pipeline_args, args.name, args.repeats, args.rubric_file, args.runs_dir, args.notes, log=sys.stderr
    )
    _print({k: manifest[k] for k in ("name", "run_fingerprint", "model", "reasoning_effort", "items", "repeats", "repeat_summaries", "stopped_by_usage_limit")})
    return 0 if not manifest.get("stopped_by_usage_limit") else 2


def _score(run_dir: Path, items, gold, taxonomy, aliases, references, hide_test: bool, usage_limits: Path | None) -> dict[str, Any]:
    run = runner_mod.load_run(run_dir)
    manifest = run["manifest"]
    repeats = run["repeats"]
    agreement = json.loads(AGREEMENT_PATH.read_text()) if AGREEMENT_PATH.exists() else {}
    adjacency = refs_mod.adjacency_set(agreement.get("label_adjacency", []))
    per_repeat = [scoring_mod.score_run(items, results, gold, aliases, hide_test, adjacency) for results in repeats]
    mean = _mean_reports(per_repeat)
    ceiling = _ceiling(agreement)
    prices = runner_mod.model_prices(usage_limits or (Path(manifest["usage_limits"]) if manifest.get("usage_limits") else None), manifest.get("provider"), manifest.get("model"))
    contrast = scoring_contrast(items, repeats, aliases, gold)
    return {
        "name": manifest.get("name"),
        "manifest": manifest,
        "items_scored": per_repeat[0]["items_scored"] if per_repeat else 0,
        "repeats": [{k: v for k, v in r.items() if k != "per_item"} for r in per_repeat],
        "per_item": per_repeat[0].get("per_item", []) if per_repeat else [],
        "mean": mean,
        "repeat_agreement": scoring_mod.repeat_agreement(items, repeats, aliases),
        "agreement_with_annotators": scoring_mod.agreement_with_annotators(items, repeats[0], references, aliases) if repeats else {},
        "reference_pairwise": agreement.get("pairwise", {}),
        "reference_alpha": agreement.get("krippendorff_alpha", {}),
        "leave_one_out": agreement.get("leave_one_out", {}),
        "contrast_validity": agreement.get("contrast_validity", {}),
        "label_adjacency": agreement.get("label_adjacency", []),
        "ceiling": ceiling,
        "contrast": contrast,
        "usage": runner_mod.usage_summary(run["attempts"], prices),
    }


def _mean_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Average numeric leaves over repeats (structure taken from the first)."""
    if not reports:
        return {}

    def merge(values):
        first = values[0]
        if isinstance(first, dict):
            keys = set().union(*(v.keys() for v in values if isinstance(v, dict)))
            return {k: merge([v.get(k) for v in values if isinstance(v, dict) and k in v]) for k in keys}
        if isinstance(first, (int, float)) and not isinstance(first, bool):
            nums = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
            return round(sum(nums) / len(nums), 4) if nums else None
        return first

    stripped = [{k: v for k, v in r.items() if k != "per_item"} for r in reports]
    return merge(stripped)


def _ceiling(agreement: dict[str, Any]) -> dict[str, Any]:
    """Mean and range of reference-reference pairwise F1 per group."""
    out: dict[str, dict[str, float]] = {}
    pairwise = agreement.get("pairwise", {})
    groups = set(g for pair in pairwise.values() for g in pair)
    for group in groups:
        values = [pair[group]["f1"] for pair in pairwise.values() if group in pair]
        if values:
            out[group] = {"f1": round(sum(values) / len(values), 4), "min": min(values), "max": max(values)}
    return out


def scoring_contrast(items, repeats, aliases, gold=None) -> dict[str, Any]:
    from analysis.benchmark.contrast import evaluate_contrast

    if not repeats:
        return {}
    return evaluate_contrast(items, repeats[0], aliases, gold)


def cmd_score(args: argparse.Namespace) -> int:
    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    items = items_mod.load_items(args.items)
    gold = refs_mod.load_gold(args.gold)
    references = refs_mod.load_references(args.references)
    aliases = alias_map(taxonomy, args.alias)
    score = _score(args.run_dir, items, gold, taxonomy, aliases, references, not args.show_test, args.usage_limits)
    tl.write_json(args.run_dir / "score.json", score)
    (args.run_dir / "scorecard.md").write_text(report_mod.scorecard(score), encoding="utf-8")
    print(report_mod.scorecard(score))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from analysis.benchmark.compare import compare_runs

    taxonomy = load_benchmark_taxonomy(args.taxonomy)
    items = items_mod.load_items(args.items)
    gold = refs_mod.load_gold(args.gold)
    comparison = compare_runs(args.run_a, args.run_b, items, gold, alias_map(taxonomy, args.alias), args.iterations)
    text = report_mod.compare_markdown(args.run_a.name, args.run_b.name, comparison)
    out = args.out or (args.run_b / f"compare_{args.run_a.name}.md")
    out.write_text(text, encoding="utf-8")
    tl.write_json(out.with_suffix(".json"), comparison)
    print(text)
    return 0


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="analysis.benchmark", description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--items", type=Path, default=ITEMS_PATH)
    parser.add_argument("--taxonomy", type=Path, default=TAXONOMY_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    taxonomy = sub.add_parser("taxonomy", help="Compile the benchmark taxonomy from its topics file")
    taxonomy.add_argument("--out", type=Path, default=TAXONOMY_PATH)
    taxonomy.set_defaults(func=cmd_taxonomy)

    pool = sub.add_parser("pool", help="Draw candidate windows per stratum from the corpus")
    pool.add_argument("--out-dir", type=Path, default=POOL_DIR)
    pool.add_argument("--seed", type=int)
    pool.set_defaults(func=cmd_pool)

    select = sub.add_parser("select", help="Fill the strata quotas from the pool")
    select.add_argument("--pool", type=Path, default=POOL_DIR / "pool.jsonl")
    select.add_argument("--screening", type=Path, default=POOL_DIR / "screening.jsonl")
    select.add_argument("--seed", type=int)
    select.add_argument("--grow", action="store_true", help="Keep existing items and add to them")
    select.set_defaults(func=cmd_select)

    screen = sub.add_parser("screen", help="Sonnet screening of the pool (task bundles)")
    screen_sub = screen.add_subparsers(dest="screen_command", required=True)
    st = screen_sub.add_parser("tasks")
    st.add_argument("--pool", type=Path, default=POOL_DIR / "pool.jsonl")
    st.add_argument("--bundle-size", type=int, default=25)
    st.add_argument("--run-id", default=tasks_mod.utc_stamp())
    st.add_argument("--seed", type=int)
    st.add_argument("--strata", nargs="*")
    st.set_defaults(func=cmd_screen_tasks)
    si = screen_sub.add_parser("ingest")
    si.add_argument("run_dir", type=Path)
    si.add_argument("--pool", type=Path, default=POOL_DIR / "pool.jsonl")
    si.add_argument("--out", type=Path, default=POOL_DIR / "screening.jsonl")
    si.set_defaults(func=cmd_screen_ingest)

    synthetic = sub.add_parser("synthetic", help="Synthetic items (task bundles)")
    synthetic_sub = synthetic.add_subparsers(dest="synthetic_command", required=True)
    syt = synthetic_sub.add_parser("tasks")
    syt.add_argument("--run-id", default=tasks_mod.utc_stamp())
    syt.add_argument("--per-bundle", type=int, default=5)
    syt.set_defaults(func=cmd_synthetic_tasks)
    syi = synthetic_sub.add_parser("ingest")
    syi.add_argument("run_dir", type=Path)
    syi.set_defaults(func=cmd_synthetic_ingest)

    contrast = sub.add_parser("contrast", help="Contrast twins (task bundles)")
    contrast_sub = contrast.add_subparsers(dest="contrast_command", required=True)
    ct = contrast_sub.add_parser("tasks")
    ct.add_argument("--run-id", default=tasks_mod.utc_stamp())
    ct.add_argument("--pairs", type=int, default=15)
    ct.add_argument("--per-bundle", type=int, default=5)
    ct.add_argument("--gold", type=Path, default=GOLD_PATH)
    ct.set_defaults(func=cmd_contrast_tasks)
    ci = contrast_sub.add_parser("ingest")
    ci.add_argument("run_dir", type=Path)
    ci.set_defaults(func=cmd_contrast_ingest)

    validate = sub.add_parser("validate-result", help="Validate a results.json against its bundle")
    validate.add_argument("results", type=Path)
    validate.add_argument("--bundle", type=Path, required=True)
    validate.set_defaults(func=cmd_validate_result)

    reference = sub.add_parser("reference", help="Reference annotations (task bundles)")
    reference_sub = reference.add_subparsers(dest="reference_command", required=True)
    rt = reference_sub.add_parser("tasks")
    rt.add_argument("--annotator", required=True)
    rt.add_argument("--run-id", default=tasks_mod.utc_stamp())
    rt.add_argument("--bundle-size", type=int, default=5)
    rt.add_argument("--null-bundle-size", type=int, default=10)
    rt.add_argument("--strata", nargs="*")
    rt.add_argument("--only-missing", action="store_true")
    rt.set_defaults(func=cmd_reference_tasks)
    ri = reference_sub.add_parser("ingest")
    ri.add_argument("run_dir", type=Path)
    ri.add_argument("--annotator", required=True)
    ri.add_argument("--model", required=True)
    ri.add_argument("--method", default="claude-code-agent")
    ri.add_argument("--authority", type=float, default=1.0)
    ri.set_defaults(func=cmd_reference_ingest)
    ra = reference_sub.add_parser("add-run", help="Register a benchmark run as an annotator")
    ra.add_argument("run_dir", type=Path)
    ra.add_argument("--annotator", required=True)
    ra.add_argument("--repeat", type=int, default=0)
    ra.add_argument("--authority", type=float, default=1.0)
    ra.set_defaults(func=cmd_reference_add_run)

    aggregate = sub.add_parser("aggregate", help="Build gold.jsonl and agreement.json from the references")
    aggregate.add_argument("--references", type=Path, default=REFERENCES_DIR)
    aggregate.add_argument("--adjudication", type=Path, default=ADJUDICATION_PATH)
    aggregate.add_argument("--gold", type=Path, default=GOLD_PATH)
    aggregate.add_argument("--agreement", type=Path, default=AGREEMENT_PATH)
    aggregate.set_defaults(func=cmd_aggregate)

    adjudicate = sub.add_parser("adjudicate", help="Opus review of singleton gold atoms (task bundles)")
    adjudicate_sub = adjudicate.add_subparsers(dest="adjudicate_command", required=True)
    at = adjudicate_sub.add_parser("tasks")
    at.add_argument("--run-id", default=tasks_mod.utc_stamp())
    at.add_argument("--per-bundle", type=int, default=8)
    at.add_argument("--gold", type=Path, default=GOLD_PATH)
    at.set_defaults(func=cmd_adjudicate_tasks)
    ai = adjudicate_sub.add_parser("ingest")
    ai.add_argument("run_dir", type=Path)
    ai.add_argument("--gold", type=Path, default=GOLD_PATH)
    ai.add_argument("--out", type=Path, default=ADJUDICATION_PATH)
    ai.set_defaults(func=cmd_adjudicate_ingest)

    run = sub.add_parser("run", help="Label the items with a candidate configuration")
    run.add_argument("--name", required=True)
    run.add_argument("--pipeline-config", type=Path, default=None, help="TOML with [model]/[label]/[usage] tables")
    run.add_argument("--repeats", type=int, default=2)
    run.add_argument("--split", choices=("dev", "test", "all"), default="all")
    run.add_argument("--strata", nargs="*")
    run.add_argument("--limit", type=int)
    run.add_argument("--rubric-file", type=Path)
    run.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    run.add_argument("--notes")
    run.add_argument("label_args", nargs=argparse.REMAINDER, help="Pipeline label flags after --")
    run.set_defaults(func=cmd_run)

    score = sub.add_parser("score", help="Score a run against the gold")
    score.add_argument("run_dir", type=Path)
    score.add_argument("--gold", type=Path, default=GOLD_PATH)
    score.add_argument("--references", type=Path, default=REFERENCES_DIR)
    score.add_argument("--alias", help="Label alias set for a run on another taxonomy (e.g. v5-84)")
    score.add_argument("--show-test", action="store_true")
    score.add_argument("--usage-limits", type=Path)
    score.set_defaults(func=cmd_score)

    compare = sub.add_parser("compare", help="Paired comparison of two runs")
    compare.add_argument("run_a", type=Path)
    compare.add_argument("run_b", type=Path)
    compare.add_argument("--gold", type=Path, default=GOLD_PATH)
    compare.add_argument("--alias")
    compare.add_argument("--iterations", type=int, default=2000)
    compare.add_argument("--out", type=Path)
    compare.set_defaults(func=cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (items_mod.BenchmarkError, tl.TopicLabelingError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
