"""Contrast-pair evaluation: did the targeted annotation move as the spec says?

Pass is judged on the *targeted* atom only. Collateral change (atoms outside
the edited units that differ between base and twin) is reported separately
and read against the no-op twins, whose collateral rate is the run's own
noise floor. Decoys are scored separately from real perturbations.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from analysis.benchmark.matching import Atom, WindowIndex, explode, overlaps


def _atoms_touching(atoms: Sequence[Atom], unit_indexes: Sequence[int]) -> list[Atom]:
    lo, hi = min(unit_indexes), max(unit_indexes)
    return [a for a in atoms if overlaps((a.start, a.end), (lo, hi))]


def _collateral(base_atoms: Sequence[Atom], twin_atoms: Sequence[Atom], edited: Sequence[int]) -> tuple[int, int]:
    """(changed, total) atoms outside the edited units, by key."""
    lo, hi = (min(edited), max(edited)) if edited else (-1, -1)

    def outside(atom: Atom) -> bool:
        return not overlaps((atom.start, atom.end), (lo, hi))

    base_keys = Counter(a.key() for a in base_atoms if outside(a))
    twin_keys = Counter(a.key() for a in twin_atoms if outside(a))
    changed = sum((base_keys - twin_keys).values()) + sum((twin_keys - base_keys).values())
    total = max(1, sum(base_keys.values()))
    return changed, total


def evaluate_pair(base: dict[str, Any], twin: dict[str, Any], base_result: dict[str, Any] | None, twin_result: dict[str, Any] | None, aliases: dict[str, str] | None) -> dict[str, Any]:
    expect = twin["expected_delta"]
    if base_result is None or twin_result is None:
        return {"pair_id": twin["pair_id"], "perturbation": twin["perturbation"], "decoy": expect.get("decoy"), "noop": expect.get("noop"), "scored": False}
    base_index = WindowIndex(base)
    twin_index = WindowIndex(twin)
    base_atoms = explode(base_result, base_index, aliases)
    twin_atoms = explode(twin_result, twin_index, aliases)
    edited = [base_index.order[u] for u in twin.get("edited_unit_ids", []) if u in base_index.order]
    target_units = [base_index.order[u] for u in (twin.get("target") or {}).get("unit_ids", []) if u in base_index.order] or edited
    changed, total = _collateral(base_atoms, twin_atoms, edited)
    out = {
        "pair_id": twin["pair_id"],
        "perturbation": twin["perturbation"],
        "decoy": bool(expect.get("decoy")),
        "noop": bool(expect.get("noop")),
        "scored": True,
        "collateral_changed": changed,
        "collateral_total": total,
    }
    kind = expect.get("kind")
    if expect.get("unchanged"):
        # Nothing should move anywhere: pass when the atom sets agree by key.
        base_keys = Counter(a.key() for a in base_atoms)
        twin_keys = Counter(a.key() for a in twin_atoms)
        out["passed"] = base_keys == twin_keys
        return out
    base_target = [a for a in _atoms_touching(base_atoms, target_units) if a.kind == kind]
    twin_target = [a for a in _atoms_touching(twin_atoms, target_units) if a.kind == kind]
    if expect.get("absent"):
        out["passed"] = bool(base_target) and not twin_target
        out["base_had_target"] = bool(base_target)
        return out
    field = expect.get("field")
    to_values = set(expect.get("to") or [])
    from_values = set(expect.get("from") or [])
    base_values = {str(a.attributes.get(field)) for a in base_target}
    twin_values = {str(a.attributes.get(field)) for a in twin_target}
    out["base_had_target"] = bool(base_target and (not from_values or base_values & from_values))
    moved = bool(twin_target) and bool(twin_values & to_values)
    hold_ok = True
    for hold_field, allowed in (expect.get("hold") or {}).items():
        hold_ok = hold_ok and all(str(a.attributes.get(hold_field)) in allowed for a in twin_target)
    out["passed"] = bool(out["base_had_target"]) and moved and hold_ok
    out["base_values"] = sorted(base_values)
    out["twin_values"] = sorted(twin_values)
    return out


def evaluate_contrast(items: Sequence[dict[str, Any]], results: dict[str, dict[str, Any]], aliases: dict[str, str] | None) -> dict[str, Any]:
    by_id = {item["item_id"]: item for item in items}
    twins = [item for item in items if item.get("source") == "contrast"]
    if not twins:
        return {}
    rows = []
    for twin in twins:
        base = by_id.get(twin["base_item_id"])
        if base is None:
            continue
        rows.append(evaluate_pair(base, twin, results.get(base["window_id"]), results.get(twin["window_id"]), aliases))
    scored = [r for r in rows if r["scored"]]
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
        "pass_rate": rate(with_target, "passed"),
        "pass_rate_all": rate(real, "passed"),
        "base_target_found_rate": rate(real, "base_had_target"),
        "decoy_pass_rate": rate(decoys, "passed"),
        "collateral_rate": collateral(real),
        "noop_collateral_rate": collateral(noops),
        "by_perturbation": by_perturbation,
        "pairs_detail": rows,
    }
