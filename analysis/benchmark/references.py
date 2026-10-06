"""Reference annotations and their aggregation into a soft gold.

``benchmark/annotators.json`` registers annotators (model, method, authority).
``benchmark/references/<item_id>/<annotator>.json`` holds one validated window
result per annotator per item, plus the pre-repair ``raw`` output when the
annotator was an agent that repaired its own validator errors.

``aggregate`` clusters the annotators' atoms per item into gold atoms with a
support tier, a span envelope and per-attribute vote distributions, then
applies the adjudication overlay. Pairwise agreement between annotators is
computed with the same matching a candidate is scored with, so a candidate's
agreement with each annotator can be read against the annotators' own.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from analysis import topic_labeling as tl
from analysis.benchmark import (
    ADJUDICATION_PATH,
    AGREEMENT_PATH,
    ANNOTATORS_PATH,
    BENCHMARK_VERSION,
    GOLD_PATH,
    REFERENCES_DIR,
)
from analysis.benchmark import stats
from analysis.benchmark.matching import (
    Atom,
    GoldAtom,
    WindowIndex,
    assign,
    explode,
    match_score,
)
from analysis.benchmark.taxonomy import label_axes

# An atom is required gold once this much annotator authority stands behind it
# (two ordinary annotators, or one whose registered authority is 2). A count,
# not a share, so adding annotators never demotes what two already agreed on.
REQUIRED_WEIGHT = 2.0 - 1e-9
CLAIM_OPTIONAL_FIELDS = ("relevance",)
VOTED_ATTRIBUTES = {
    "detection": ("relevance", "discourse_role"),
    "claim": ("discourse_role", "claim_type", "expressed_certainty", "relevance"),
    "product": ("product_type", "mention_role", "product_name"),
}


# --------------------------------------------------------------------------
# Validation: the pipeline validator, plus the benchmark's optional fields
# --------------------------------------------------------------------------


def validate_result(result: dict[str, Any], window: dict[str, Any], axes: dict[str, str]) -> dict[str, Any]:
    """``validate_window_result`` with claim ``relevance`` allowed on top.

    Main's validator rejects unknown claim fields; the benchmark codebook asks
    for the v6 ``relevance`` on claims, so it is lifted off before validation
    and put back on the normalized claim afterwards.
    """
    if not isinstance(result, dict):
        raise tl.TopicLabelingError("result must be an object", kind="schema_shape")
    claims = result.get("verification_candidates")
    lifted: list[dict[str, Any]] = []
    stripped_claims = []
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, dict):
                extra = {k: claim[k] for k in CLAIM_OPTIONAL_FIELDS if k in claim}
                lifted.append(extra)
                stripped_claims.append({k: v for k, v in claim.items() if k not in CLAIM_OPTIONAL_FIELDS})
            else:
                lifted.append({})
                stripped_claims.append(claim)
    to_validate = {**result, "verification_candidates": stripped_claims if isinstance(claims, list) else claims}
    normalized = tl.validate_window_result(to_validate, window, axes)
    for claim, extra in zip(normalized["verification_candidates"], lifted):
        relevance = extra.get("relevance")
        if relevance is not None and relevance not in tl.ALLOWED_RELEVANCE:
            raise tl.TopicLabelingError("invalid claim relevance", kind="invalid_field")
        claim["relevance"] = relevance
    return normalized


# --------------------------------------------------------------------------
# Annotators and reference files
# --------------------------------------------------------------------------


def load_annotators(path: Path = ANNOTATORS_PATH) -> dict[str, dict[str, Any]]:
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def register_annotator(annotator: dict[str, Any], path: Path = ANNOTATORS_PATH) -> None:
    for key in ("annotator_id", "model", "method"):
        if not annotator.get(key):
            raise tl.TopicLabelingError(f"annotator needs {key}")
    annotators = load_annotators(path)
    annotators[annotator["annotator_id"]] = {
        "authority": 1.0,
        "registered_at": tl.utc_now(),
        **annotators.get(annotator["annotator_id"], {}),
        **annotator,
    }
    tl.write_json(Path(path), dict(sorted(annotators.items())))


def reference_path(item_id: str, annotator_id: str, root: Path = REFERENCES_DIR) -> Path:
    return Path(root) / item_id / f"{annotator_id}.json"


def store_reference(
    item_id: str,
    annotator_id: str,
    result: dict[str, Any],
    raw: dict[str, Any] | None,
    provenance: dict[str, Any],
    root: Path = REFERENCES_DIR,
) -> Path:
    path = reference_path(item_id, annotator_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tl.write_json(
        path,
        {
            "benchmark_version": BENCHMARK_VERSION,
            "item_id": item_id,
            "annotator_id": annotator_id,
            "stored_at": tl.utc_now(),
            "provenance": provenance,
            "result": result,
            "raw": raw,
        },
    )
    return path


def load_references(root: Path = REFERENCES_DIR) -> dict[str, dict[str, dict[str, Any]]]:
    """item_id -> annotator_id -> stored reference."""
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for path in sorted(Path(root).glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        out[record["item_id"]][record["annotator_id"]] = record
    return dict(out)


def repair_delta(raw: dict[str, Any] | None, final: dict[str, Any]) -> dict[str, int]:
    """How much an annotator's validator-driven repair changed the output."""
    if not raw:
        return {}
    delta = {}
    for key in ("detections", "verification_candidates", "product_mentions"):
        before = len(raw.get(key) or []) if isinstance(raw.get(key), list) else 0
        after = len(final.get(key) or [])
        delta[key] = after - before
    return delta


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def _atoms_for(reference: dict[str, Any], index: WindowIndex) -> list[Atom]:
    return explode(reference["result"], index)


def cluster_atoms(
    per_annotator: dict[str, list[Atom]],
) -> list[dict[str, Any]]:
    """Greedy agglomeration across annotators, in fixed annotator order.

    Each annotator's atoms are matched one-to-one against the clusters so far
    (with the same rules a prediction is matched with); unmatched atoms open
    new clusters. Deterministic given the annotator order.
    """
    clusters: list[dict[str, Any]] = []
    for annotator_id in sorted(per_annotator):
        atoms = per_annotator[annotator_id]
        golds = [_cluster_as_gold(cluster, index) for index, cluster in enumerate(clusters)]
        matched = assign(atoms, golds)
        taken: set[int] = set()
        for pred_index, gold_index, _ in matched:
            clusters[gold_index]["members"].append((annotator_id, atoms[pred_index]))
            taken.add(pred_index)
        for atom_index, atom in enumerate(atoms):
            if atom_index not in taken:
                clusters.append({"members": [(annotator_id, atom)]})
    return clusters


def _cluster_as_gold(cluster: dict[str, Any], number: int, total_annotators: int = 1) -> GoldAtom:
    members: list[tuple[str, Atom]] = cluster["members"]
    first = members[0][1]
    spans = [(atom.start, atom.end) for _, atom in members]
    tight = min(spans, key=lambda s: (s[1] - s[0], s[0]))
    envelope = (min(s[0] for s in spans), max(s[1] for s in spans))
    votes: dict[str, dict[str, int]] = {}
    for attribute in VOTED_ATTRIBUTES[first.kind]:
        counter: Counter[str] = Counter()
        for _, atom in members:
            value = atom.product_name if attribute == "product_name" else atom.attributes.get(attribute)
            if value is not None:
                counter[str(value)] += 1
        if counter:
            votes[attribute] = dict(counter)
    annotators = sorted({annotator for annotator, _ in members})
    return GoldAtom(
        gold_id=f"g{number:04d}",
        kind=first.kind,
        tight=tight,
        envelope=envelope,
        axis=first.axis,
        label=first.label,
        tier="singleton",
        support=len(annotators) / max(1, total_annotators),
        annotators=annotators,
        votes=votes,
        quotes=[atom.quote for _, atom in members if atom.quote],
        quote_ranges=[atom.quote_range for _, atom in members if atom.quote_range],
        claim_texts=[atom.claim_text for _, atom in members if atom.claim_text],
        product_keys=sorted({atom.product_key for _, atom in members if atom.product_key}),
        product_names=sorted({atom.product_name for _, atom in members if atom.product_name}),
        members=sorted(atom.member_key(annotator) for annotator, atom in members),
    )


def gold_for_item(
    item: dict[str, Any],
    references: dict[str, dict[str, Any]],
    annotators: dict[str, dict[str, Any]],
) -> list[GoldAtom]:
    index = WindowIndex(item)
    per_annotator = {
        annotator_id: _atoms_for(reference, index) for annotator_id, reference in references.items()
    }
    clusters = cluster_atoms(per_annotator)
    total_weight = sum(float(annotators.get(a, {}).get("authority", 1.0)) for a in per_annotator)
    golds: list[GoldAtom] = []
    for number, cluster in enumerate(clusters):
        gold = _cluster_as_gold(cluster, number, len(per_annotator))
        weight = sum(float(annotators.get(a, {}).get("authority", 1.0)) for a in gold.annotators)
        gold.support = weight / total_weight if total_weight else 0.0
        gold.tier = "required" if weight >= REQUIRED_WEIGHT else "singleton"
        golds.append(gold)
    return golds


def load_adjudication(path: Path = ADJUDICATION_PATH) -> dict[tuple[str, str], dict[str, Any]]:
    """Verdicts keyed by (item_id, member key); legacy rows without a member key by (item_id, gold_id)."""
    if not Path(path).exists():
        return {}
    out = {}
    for row in tl.iter_jsonl(Path(path)):
        out[(row["item_id"], row.get("member") or row["gold_id"])] = row
    return out


def apply_overlay(item_id: str, golds: list[GoldAtom], overlay: dict[tuple[str, str], dict[str, Any]]) -> list[GoldAtom]:
    """Apply adjudication verdicts to the singletons they were made about.

    A verdict is attached to one annotator's atom. It only matters while that
    atom still stands alone: once another annotator agrees with it the atom is
    required on its own merits, and the verdict is moot.
    """
    for gold in golds:
        if gold.tier != "singleton":
            continue
        decision = overlay.get((item_id, gold.members[0])) if gold.members else None
        if decision is None:
            decision = overlay.get((item_id, gold.gold_id))
        if decision and decision.get("tier") in ("acceptable", "rejected"):
            gold.tier = decision["tier"]
    return golds


def gold_record(item: dict[str, Any], gold: GoldAtom) -> dict[str, Any]:
    units = item["units"]
    return {
        "item_id": item["item_id"],
        "gold_id": gold.gold_id,
        "kind": gold.kind,
        "axis": gold.axis,
        "label": gold.label,
        "tier": gold.tier,
        "support": round(gold.support, 4),
        "annotators": gold.annotators,
        "tight": [units[gold.tight[0]]["unit_id"], units[gold.tight[1]]["unit_id"]],
        "envelope": [units[gold.envelope[0]]["unit_id"], units[gold.envelope[1]]["unit_id"]],
        "tight_index": list(gold.tight),
        "envelope_index": list(gold.envelope),
        "votes": gold.votes,
        "quotes": gold.quotes,
        "quote_ranges": [list(r) for r in gold.quote_ranges],
        "claim_texts": gold.claim_texts,
        "product_keys": gold.product_keys,
        "product_names": gold.product_names,
        "members": gold.members,
    }


def gold_from_record(record: dict[str, Any]) -> GoldAtom:
    return GoldAtom(
        gold_id=record["gold_id"],
        kind=record["kind"],
        tight=tuple(record["tight_index"]),
        envelope=tuple(record["envelope_index"]),
        axis=record.get("axis"),
        label=record.get("label"),
        tier=record["tier"],
        support=float(record["support"]),
        annotators=list(record["annotators"]),
        votes=record.get("votes", {}),
        quotes=record.get("quotes", []),
        quote_ranges=[tuple(r) for r in record.get("quote_ranges", [])],
        claim_texts=record.get("claim_texts", []),
        product_keys=record.get("product_keys", []),
        product_names=record.get("product_names", []),
        members=list(record.get("members", [])),
    )


def load_gold(path: Path = GOLD_PATH) -> dict[str, list[GoldAtom]]:
    """Gold atoms per item, with an empty list for every covered item that has none."""
    out: dict[str, list[GoldAtom]] = defaultdict(list)
    if not Path(path).exists():
        return {}
    agreement_path = Path(path).with_name(AGREEMENT_PATH.name)
    if agreement_path.exists():
        for item_id in json.loads(agreement_path.read_text(encoding="utf-8")).get("gold_items", []):
            out[item_id] = []
    for record in tl.iter_jsonl(Path(path)):
        out[record["item_id"]].append(gold_from_record(record))
    return dict(out)


# --------------------------------------------------------------------------
# Pairwise agreement and attribute alpha
# --------------------------------------------------------------------------


def pairwise_f1(a_atoms: list[Atom], b_atoms: list[Atom]) -> dict[str, dict[str, float]]:
    """F1 of B against A treated as gold, per kind and per detection axis.

    One-to-one matching makes this symmetric up to the score tie-breaks, so it
    is reported once per unordered pair.
    """
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    a_gold = [_single_gold(atom, i) for i, atom in enumerate(a_atoms)]
    matched = assign(b_atoms, a_gold)
    matched_b = {i for i, _, _ in matched}
    matched_a = {j for _, j, _ in matched}
    for i, atom in enumerate(b_atoms):
        key = _group(atom)
        counts[key]["tp" if i in matched_b else "fp"] += 1
    for j, atom in enumerate(a_atoms):
        if j not in matched_a:
            counts[_group(atom)]["fn"] += 1
    return {
        group: {
            "tp": c["tp"], "fp": c["fp"], "fn": c["fn"], "f1": stats.f1(c["tp"], c["fp"], c["fn"]),
        }
        for group, c in counts.items()
    }


def _group(atom: Atom) -> str:
    return f"detection:{atom.axis}" if atom.kind == "detection" else atom.kind


def _single_gold(atom: Atom, number: int) -> GoldAtom:
    return _cluster_as_gold({"members": [("a", atom)]}, number)


def attribute_units(golds: Sequence[GoldAtom]) -> dict[str, list[list[str]]]:
    """Per attribute, the coder values on every gold atom with >= 2 annotators."""
    units: dict[str, list[list[str]]] = defaultdict(list)
    for gold in golds:
        if len(gold.annotators) < 2:
            continue
        for attribute, votes in gold.votes.items():
            values: list[str] = []
            for value, count in votes.items():
                values.extend([value] * count)
            if len(values) >= 2:
                units[f"{gold.kind}:{attribute}"].append(values)
    return units


MIN_ANNOTATORS = 2


def aggregate(
    items: Sequence[dict[str, Any]],
    references: dict[str, dict[str, dict[str, Any]]],
    annotators: dict[str, dict[str, Any]],
    overlay: dict[tuple[str, str], dict[str, Any]],
    min_annotators: int = MIN_ANNOTATORS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Gold records for every item with enough references, plus the agreement report.

    An item labeled by fewer than ``min_annotators`` yields no gold: with one
    annotator every atom would count as agreed, which is the opposite of what
    the tiers mean. Such items are counted in the report instead.
    """
    records: list[dict[str, Any]] = []
    gold_items: list[str] = []
    skipped_items = 0
    pair_counts: dict[tuple[str, str], dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    alpha_units: dict[str, list[list[str]]] = defaultdict(list)
    tiers: Counter[str] = Counter()
    coverage: Counter[int] = Counter()
    per_annotator_atoms: Counter[str] = Counter()
    repairs: dict[str, Counter[str]] = defaultdict(Counter)
    for item in items:
        refs = references.get(item["item_id"])
        if not refs:
            continue
        coverage[len(refs)] += 1
        if len(refs) < min_annotators:
            skipped_items += 1
            continue
        golds = apply_overlay(item["item_id"], gold_for_item(item, refs, annotators), overlay)
        gold_items.append(item["item_id"])
        for gold in golds:
            tiers[gold.tier] += 1
            records.append(gold_record(item, gold))
        for attribute, units in attribute_units(golds).items():
            alpha_units[attribute].extend(units)
        index = WindowIndex(item)
        atoms = {a: _atoms_for(r, index) for a, r in refs.items()}
        for annotator_id, ref in refs.items():
            per_annotator_atoms[annotator_id] += len(atoms[annotator_id])
            for key, value in repair_delta(ref.get("raw"), ref["result"]).items():
                repairs[annotator_id][key] += value
        ids = sorted(atoms)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                for group, counts in pairwise_f1(atoms[a], atoms[b]).items():
                    for field in ("tp", "fp", "fn"):
                        pair_counts[(a, b)][group][field] += counts[field]
    agreement = {
        "benchmark_version": BENCHMARK_VERSION,
        "items_with_references": sum(coverage.values()),
        "items_in_gold": sum(coverage.values()) - skipped_items,
        # Every item the gold covers, including those whose gold is empty (a
        # null window all annotators left empty is gold too: its correct
        # answer is nothing, and it must be scored).
        "gold_items": gold_items,
        "items_below_min_annotators": skipped_items,
        "min_annotators": min_annotators,
        "annotators_per_item": dict(sorted(coverage.items())),
        "tiers": dict(tiers),
        "atoms_per_annotator": dict(per_annotator_atoms),
        "repair_delta_per_annotator": {a: dict(c) for a, c in repairs.items()},
        "pairwise": {
            f"{a}|{b}": {
                group: {**c, "f1": round(stats.f1(c["tp"], c["fp"], c["fn"]), 4)}
                for group, c in sorted(groups.items())
            }
            for (a, b), groups in sorted(pair_counts.items())
        },
        "krippendorff_alpha": {
            attribute: {
                "alpha": None if (value := stats.krippendorff_alpha(
                    units,
                    metric="ordinal" if attribute.endswith("expressed_certainty") else "nominal",
                    levels=list(tl.ALLOWED_EXPRESSED_CERTAINTY),
                )) is None else round(value, 4),
                "units": len(units),
            }
            for attribute, units in sorted(alpha_units.items())
        },
    }
    return records, agreement


# --------------------------------------------------------------------------
# Synthetic plants
# --------------------------------------------------------------------------

PLANT_ATTRIBUTES = {
    "detections": ("relevance", "discourse_role"),
    "claims": ("expressed_certainty", "discourse_role", "claim_type"),
    "products": ("product_type", "mention_role"),
}


def check_plants(items: Sequence[dict[str, Any]], records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare each synthetic item's planted annotations with its gold.

    A plant is *found* when a gold atom of the same kind (and label, for
    detections) overlaps its span; it is *supported* when that atom is
    ``required``; each planted attribute is checked against the plurality
    vote. A plant that is missing or contradicted means either the passage is
    ambiguous or the codebook reading behind the plant is not shared, and the
    item should be fixed or dropped before it is trusted.
    """
    by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_item[record["item_id"]].append(record)
    report: list[dict[str, Any]] = []
    for item in items:
        planted = item.get("planted")
        if not planted:
            continue
        order = {u["unit_id"]: i for i, u in enumerate(item["units"])}
        golds = by_item.get(item["item_id"], [])
        for kind_key, kind in (("detections", "detection"), ("claims", "claim"), ("products", "product")):
            for plant in planted.get(kind_key) or []:
                start, end = order[plant["start_unit_id"]], order[plant["end_unit_id"]]
                labels = plant.get("labels") or [None]
                for label in labels:
                    candidates = [
                        g for g in golds
                        if g["kind"] == kind
                        and (kind != "detection" or g.get("label") == label)
                        and g["envelope_index"][0] <= end and start <= g["envelope_index"][1]
                    ]
                    best = max(candidates, key=lambda g: (g["tier"] == "required", g["support"]), default=None)
                    entry: dict[str, Any] = {
                        "item_id": item["item_id"],
                        "kind": kind,
                        "label": label,
                        "span": [plant["start_unit_id"], plant["end_unit_id"]],
                        "found": best is not None,
                        "tier": best["tier"] if best else None,
                        "support": best["support"] if best else 0.0,
                        "attribute_mismatches": {},
                    }
                    if best:
                        for attribute in PLANT_ATTRIBUTES[kind_key]:
                            expected = plant.get(attribute)
                            votes = best.get("votes", {}).get(attribute) or {}
                            if expected is None or not votes:
                                continue
                            plurality = max(sorted(votes), key=lambda v: votes[v])
                            if plurality != expected:
                                entry["attribute_mismatches"][attribute] = {"planted": expected, "plurality": plurality, "votes": votes}
                    if not best:
                        verdict = "missing"
                    elif best["tier"] != "required":
                        verdict = "singleton"
                    elif not entry["attribute_mismatches"]:
                        verdict = "ok"
                    elif all(
                        m["votes"].get(m["planted"], 0) == 0 and sum(m["votes"].values()) >= 2
                        for m in entry["attribute_mismatches"].values()
                    ):
                        verdict = "contradicted"
                    else:
                        verdict = "split"
                    entry["verdict"] = verdict
                    entry["ok"] = verdict == "ok"
                    report.append(entry)
    return report


# --------------------------------------------------------------------------
# Label adjacency and the leave-one-out ceiling
# --------------------------------------------------------------------------

ADJACENCY_MIN_COUNT = 3


def label_adjacency(
    items: Sequence[dict[str, Any]],
    references: dict[str, dict[str, dict[str, Any]]],
    min_count: int = ADJACENCY_MIN_COUNT,
) -> list[dict[str, Any]]:
    """Same-axis label pairs the annotators put on the same span in each other's place.

    Counted once per (item, annotator pair, span) where annotator A used
    label X and annotator B used label Y on a span at least 80% shared, and
    neither used the other's label there. Pairs seen ``min_count`` times or
    more are the benchmark's adjacency table: a candidate that lands on the
    other side of one of these is making a disagreement the references make
    themselves, and adjacent-credit F1 says how much of its error is that.
    """
    from analysis.benchmark.matching import overlap_coefficient

    counts: Counter[tuple[str, str, str]] = Counter()
    for item in items:
        refs = references.get(item["item_id"])
        if not refs or len(refs) < 2:
            continue
        index = WindowIndex(item)
        atoms = {a: [x for x in _atoms_for(r, index) if x.kind == "detection"] for a, r in refs.items()}
        ids = sorted(atoms)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                for x in atoms[a]:
                    if any(y.label == x.label and overlap_coefficient((x.start, x.end), (y.start, y.end)) >= 0.5 for y in atoms[b]):
                        continue
                    for y in atoms[b]:
                        if y.axis != x.axis or y.label == x.label:
                            continue
                        if overlap_coefficient((x.start, x.end), (y.start, y.end)) < 0.8:
                            continue
                        if any(z.label == y.label and overlap_coefficient((z.start, z.end), (y.start, y.end)) >= 0.5 for z in atoms[a]):
                            continue
                        first, second = sorted((x.label, y.label))
                        counts[(x.axis, first, second)] += 1
    return [
        {"axis": axis, "labels": [first, second], "count": n}
        for (axis, first, second), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if n >= min_count
    ]


def adjacency_set(table: Sequence[dict[str, Any]]) -> set[tuple[str, str]]:
    return {tuple(sorted(row["labels"])) for row in table}


HEADLINE_STRATA = ("health_dense", "mixed", "null", "ad_read", "discourse")


def leave_one_out(
    items: Sequence[dict[str, Any]],
    references: dict[str, dict[str, dict[str, Any]]],
    annotators: dict[str, dict[str, Any]],
    overlay: dict[tuple[str, str], dict[str, Any]],
    aliases: dict[str, str] | None = None,
    adjacency: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Each annotator scored, as if it were a candidate, against gold built from the others.

    This is the ceiling a labeler of reference quality reaches on the same
    scorecard: gold is rebuilt without the held-out annotator (so its own
    atoms cannot vote), the adjudication overlay still applies to whatever
    singletons remain (verdicts are keyed by atom), and the score is the
    headline strata only.
    """
    from analysis.benchmark import scoring

    ids = sorted({a for refs in references.values() for a in refs})
    head = [item for item in items if item.get("stratum") in HEADLINE_STRATA and item["item_id"] in references]
    out: dict[str, Any] = {}
    for held in ids:
        rest = {iid: {a: r for a, r in refs.items() if a != held} for iid, refs in references.items()}
        records, _ = aggregate(head, rest, annotators, overlay)
        gold: dict[str, list[GoldAtom]] = defaultdict(list)
        for record in records:
            gold[record["item_id"]].append(gold_from_record(record))
        rows = []
        for item in head:
            ref = references[item["item_id"]].get(held)
            if ref is None or len(rest[item["item_id"]]) < MIN_ANNOTATORS:
                continue
            rows.append(scoring.score_item(item, ref["result"], gold.get(item["item_id"], []), aliases, adjacency))
        summary = scoring.summarize(rows)
        out[held] = {"items": len(rows), "groups": summary.get("groups", {})}
    return out
