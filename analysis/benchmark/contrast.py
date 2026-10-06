"""Contrast-pair evaluation: did the targeted annotation move as the spec says?

Pass is judged on the *targeted* atom only. Collateral change (atoms outside
the edited units that differ between base and twin) is reported separately
and read against the no-op twins, whose collateral rate is the run's own
noise floor. Decoys are scored separately from real perturbations.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from analysis.benchmark.matching import CERTAINTY_ORDER, Atom, WindowIndex, assign, explode, overlaps


TARGET_MARGIN = 1  # units either side of the target: annotators' spans rarely coincide with the editor's


def _atoms_touching(atoms: Sequence[Atom], unit_indexes: Sequence[int], margin: int = TARGET_MARGIN) -> list[Atom]:
    lo, hi = min(unit_indexes) - margin, max(unit_indexes) + margin
    return [a for a in atoms if overlaps((a.start, a.end), (lo, hi))]


def _match_atoms(base_atoms: Sequence[Atom], twin_atoms: Sequence[Atom]) -> list[tuple[int, int, float]]:
    """One-to-one matching of twin atoms to base atoms with the scoring rules (spans, labels, quotes)."""
    from analysis.benchmark.references import _single_gold

    golds = [_single_gold(atom, i) for i, atom in enumerate(base_atoms)]
    return assign(twin_atoms, golds)


def _collateral(base_atoms: Sequence[Atom], twin_atoms: Sequence[Atom], edited: Sequence[int], matched: Sequence[tuple[int, int, float]]) -> tuple[int, int]:
    """(changed, total): atoms outside the edited units with no counterpart in the other labeling.

    Matching is the scoring match, not exact identity, so two labelings that
    mark the same phenomenon at slightly different extents do not count as a
    change; only atoms one side has and the other lacks do.
    """
    lo, hi = (min(edited), max(edited)) if edited else (-1, -1)

    def outside(atom: Atom) -> bool:
        return not overlaps((atom.start, atom.end), (lo, hi))

    matched_twin = {i for i, _, _ in matched}
    matched_base = {j for _, j, _ in matched}
    changed = sum(1 for i, a in enumerate(twin_atoms) if outside(a) and i not in matched_twin)
    changed += sum(1 for j, a in enumerate(base_atoms) if outside(a) and j not in matched_base)
    total = max(1, sum(1 for a in base_atoms if outside(a)))
    return changed, total


def _certainty_rank(value: Any) -> int | None:
    return CERTAINTY_ORDER.get(str(value)) if value is not None else None


def evaluate_pair(
    base: dict[str, Any],
    twin: dict[str, Any],
    base_result: dict[str, Any] | None,
    twin_result: dict[str, Any] | None,
    aliases: dict[str, str] | None,
    base_gold: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Did the targeted atom move as the perturbation spec says?

    - real perturbations: the atom of the expected kind at the target must
      exist in the base labeling and, in the twin, carry the expected value
      (for expressed_certainty: move in the expected direction from wherever
      the base put it, since annotators disagree about the base level);
    - ``absent`` perturbations: the base atom must exist and no atom of that
      kind may remain at the target;
    - decoys and the no-op: the atoms at the target must match one-to-one
      between base and twin with the guarded attributes unchanged; changes
      elsewhere are collateral, reported separately.
    ``base_gold`` (the base item's gold atoms, if known) says whether the
    twin's target is something the references agree exists: a pair whose
    target is not in gold is reported as ``target_in_gold: false`` and left
    out of the pass rate, since it tests the editor's reading, not the labeler.
    """
    expect = twin["expected_delta"]
    head = {"pair_id": twin["pair_id"], "perturbation": twin["perturbation"], "decoy": bool(expect.get("decoy")), "noop": bool(expect.get("noop"))}
    base_index = WindowIndex(base)
    edited = [base_index.order[u] for u in twin.get("edited_unit_ids", []) if u in base_index.order]
    target_units = [base_index.order[u] for u in (twin.get("target") or {}).get("unit_ids", []) if u in base_index.order] or edited
    kind = expect.get("kind")
    target_in_gold = None
    if base_gold is not None and target_units and kind:
        lo, hi = min(target_units) - TARGET_MARGIN, max(target_units) + TARGET_MARGIN
        target_in_gold = any(
            g.kind == kind and g.tier in ("required", "acceptable") and overlaps(g.envelope, (lo, hi)) for g in base_gold
        )
    if base_result is None or twin_result is None:
        return {**head, "scored": False, "target_in_gold": target_in_gold}
    twin_index = WindowIndex(twin)
    base_atoms = explode(base_result, base_index, aliases)
    twin_atoms = explode(twin_result, twin_index, aliases)
    matched = _match_atoms(base_atoms, twin_atoms)
    changed, total = _collateral(base_atoms, twin_atoms, edited, matched)
    out = {**head, "scored": True, "target_in_gold": target_in_gold, "collateral_changed": changed, "collateral_total": total}
    base_target = [a for a in _atoms_touching(base_atoms, target_units) if not kind or a.kind == kind]
    twin_target = [a for a in _atoms_touching(twin_atoms, target_units) if not kind or a.kind == kind]
    if expect.get("unchanged"):
        # Decoy or no-op: nothing the perturbation could have tricked may move at the target.
        # Claims at the target must correspond one-to-one with their certainty and role intact;
        # detections that correspond must keep relevance and role. A detection one labeling
        # has and the other lacks is collateral (independent labelings differ that way even
        # on identical text), reported separately, not a targeted failure.
        guarded = list(expect.get("hold") or {}) or ["expressed_certainty", "discourse_role", "relevance"]
        twin_to_base = {i: j for i, j, _ in matched}
        base_target_ids = {id(a) for a in base_target}
        twin_target_ids = {id(a) for a in twin_target}
        problems = 0
        for i, atom in enumerate(twin_atoms):
            if id(atom) not in twin_target_ids:
                continue
            j = twin_to_base.get(i)
            if j is None:
                problems += atom.kind == "claim"
                continue
            other = base_atoms[j]
            if any(str(atom.attributes.get(f)) != str(other.attributes.get(f)) for f in guarded if f in atom.attributes or f in other.attributes):
                problems += 1
        matched_base = set(twin_to_base.values())
        problems += sum(1 for j, atom in enumerate(base_atoms) if id(atom) in base_target_ids and atom.kind == "claim" and j not in matched_base)
        out["passed"] = problems == 0
        out["target_atoms"] = [len(base_target), len(twin_target)]
        return out
    if expect.get("absent"):
        out["base_had_target"] = bool(base_target)
        out["passed"] = bool(base_target) and not twin_target
        return out
    field = expect.get("field")
    to_values = set(expect.get("to") or [])
    from_values = set(expect.get("from") or [])
    base_values = {str(a.attributes.get(field)) for a in base_target}
    twin_values = {str(a.attributes.get(field)) for a in twin_target}
    out["base_values"] = sorted(base_values)
    out["twin_values"] = sorted(twin_values)
    if field == "expressed_certainty" and to_values and from_values:
        # Direction of the intended move, read off the spec's from/to sets.
        up = min(_certainty_rank(v) for v in to_values) < min(_certainty_rank(v) for v in from_values)
        base_ranks = [r for r in (_certainty_rank(v) for v in base_values) if r is not None]
        twin_ranks = [r for r in (_certainty_rank(v) for v in twin_values) if r is not None]
        out["base_had_target"] = bool(base_ranks)
        moved = bool(base_ranks and twin_ranks) and ((min(twin_ranks) < min(base_ranks)) if up else (max(twin_ranks) > max(base_ranks)))
    else:
        out["base_had_target"] = bool(base_target and (not from_values or base_values & from_values))
        moved = bool(twin_target) and bool(twin_values & to_values)
    hold_ok = True
    for hold_field, allowed in (expect.get("hold") or {}).items():
        hold_ok = hold_ok and all(str(a.attributes.get(hold_field)) in allowed for a in twin_target)
    out["passed"] = bool(out["base_had_target"]) and moved and hold_ok
    return out


def evaluate_contrast(
    items: Sequence[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    aliases: dict[str, str] | None,
    gold: dict[str, list[Any]] | None = None,
) -> dict[str, Any]:
    by_id = {item["item_id"]: item for item in items}
    twins = [item for item in items if item.get("source") == "contrast"]
    if not twins:
        return {}
    rows = []
    for twin in twins:
        base = by_id.get(twin["base_item_id"])
        if base is None:
            continue
        base_gold = gold.get(base["item_id"]) if gold is not None else None
        rows.append(evaluate_pair(base, twin, results.get(base["window_id"]), results.get(twin["window_id"]), aliases, base_gold))
    # A twin whose target the references do not recognise tests the editor, not the labeler.
    scored = [r for r in rows if r["scored"] and r.get("target_in_gold") is not False]
    invalid = [r["pair_id"] for r in rows if r.get("target_in_gold") is False]
    real = [r for r in scored if not r["decoy"] and not r["noop"]]
    decoys = [r for r in scored if r["decoy"]]
    noops = [r for r in scored if r["noop"]]
    with_target = [r for r in real if r.get("base_had_target", True)]

    def rate(group: Sequence[dict[str, Any]], key: str) -> float | None:
        return round(sum(1 for r in group if r.get(key)) / len(group), 3) if group else None

    def collateral(group: Sequence[dict[str, Any]]) -> float | None:
        changed = sum(r["collateral_changed"] for r in group)
        total = sum(r["collateral_total"] for r in group)
        return round(changed / total, 3) if total else None

    by_perturbation: dict[str, dict[str, Any]] = {}
    for name in sorted({r["perturbation"] for r in scored}):
        group = [r for r in scored if r["perturbation"] == name]
        by_perturbation[name] = {"pairs": len(group), "pass_rate": rate(group, "passed"), "collateral": collateral(group)}
    return {
        "pairs": len(rows),
        "scored": len(scored),
        "target_not_in_gold": invalid,
        "pass_rate": rate(with_target, "passed"),
        "pass_rate_all": rate(real, "passed"),
        "base_target_found_rate": rate(real, "base_had_target"),
        "decoy_pass_rate": rate(decoys, "passed"),
        "collateral_rate": collateral(real),
        "noop_collateral_rate": collateral(noops),
        "by_perturbation": by_perturbation,
        "pairs_detail": rows,
    }


def annotator_contrast_validity(
    items: Sequence[dict[str, Any]],
    references: dict[str, dict[str, dict[str, Any]]],
    aliases: dict[str, str] | None,
    gold: dict[str, list[Any]] | None = None,
) -> dict[str, Any]:
    """Each reference annotator run through the contrast pairs as if it were a candidate.

    A perturbation that no annotator passes is a bad twin or a bad spec, not
    a labeler failure; the per-perturbation rates here are the ceiling the
    candidate's contrast numbers are read against.
    """
    by_id = {item["item_id"]: item for item in items}
    out: dict[str, Any] = {}
    for annotator in sorted({a for refs in references.values() for a in refs}):
        results = {by_id[iid]["window_id"]: refs[annotator]["result"] for iid, refs in references.items() if annotator in refs and iid in by_id}
        report = evaluate_contrast(items, results, aliases, gold)
        if report:
            out[annotator] = {k: v for k, v in report.items() if k != "pairs_detail"}
    return out
