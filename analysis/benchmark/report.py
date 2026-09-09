"""Scorecards and comparisons as markdown, from score.json files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from analysis.benchmark import stats

HEADLINE_ROWS: list[tuple[str, str, str]] = [
    # (label, group, field)
    ("Topic F1 (strict)", "detection:topic", "f1_strict"),
    ("Topic F1 (soft)", "detection:topic", "f1_soft"),
    ("Topic recall (required)", "detection:topic", "recall_strict"),
    ("Topic precision", "detection:topic", "precision"),
    ("Frame F1 (soft)", "detection:frame", "f1_soft"),
    ("Evidence F1 (soft)", "detection:evidence", "f1_soft"),
    ("Claim recall (required)", "claim", "recall_strict"),
    ("Claim precision", "claim", "precision"),
    ("Product F1 (soft)", "product", "f1_soft"),
    ("Topic yield ratio", "detection:topic", "yield_ratio"),
    ("Claim yield ratio", "claim", "yield_ratio"),
]


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _group_value(summary: dict[str, Any], group: str, field: str) -> Any:
    return summary.get("groups", {}).get(group, {}).get(field)


def scorecard(score: dict[str, Any]) -> str:
    """Markdown scorecard for one run's score.json."""
    lines: list[str] = []
    manifest = score.get("manifest", {})
    lines.append(f"# Benchmark scorecard: {manifest.get('name', '?')}")
    lines.append("")
    lines.append(
        f"Model `{manifest.get('model')}` | effort `{manifest.get('reasoning_effort')}` | "
        f"batch {manifest.get('batch_size')} | prompt `{manifest.get('prompt_version')}` | "
        f"repeats {len(score.get('repeats', []))} | items scored {score.get('items_scored')}"
    )
    lines.append("")
    ceiling = score.get("ceiling", {})
    noise = score.get("repeat_agreement", {})
    lines.append("## Headline against the gold (corpus strata, mean over repeats)")
    lines.append("")
    lines.append("Gold = atoms at least two annotators agreed on; singletons are unscored.")
    lines.append("")
    lines.append("| metric | dev | test |")
    lines.append("| --- | --- | --- |")
    dev = score.get("mean", {}).get("by_split", {}).get("dev", {})
    test = score.get("mean", {}).get("by_split", {}).get("test", {})
    for label, group, field in HEADLINE_ROWS:
        lines.append(
            f"| {label} | {_fmt(_group_value(dev, group, field))} | {_fmt(_group_value(test, group, field))} |"
        )
    lines.append("")
    lines.append("## Ceiling and noise floor (pairwise F1, like for like)")
    lines.append("")
    lines.append(
        "Candidate vs each reference annotator, the annotators vs each other, and the "
        "candidate vs its own repeat, all with the same one-to-one atom matching. A "
        "candidate inside the reference range is at ceiling on that axis."
    )
    lines.append("")
    lines.append("| axis | candidate vs references (mean) | reference vs reference (mean, range) | candidate vs own repeat |")
    lines.append("| --- | --- | --- | --- |")
    agreement = score.get("agreement_with_annotators", {})
    for group in ("detection:topic", "detection:frame", "detection:evidence", "claim", "product"):
        values = [g.get(group, {}).get("f1") for g in agreement.values() if g.get(group)]
        candidate = sum(values) / len(values) if values else None
        ref = ceiling.get(group, {})
        ref_text = f"{_fmt(ref.get('f1'))} ({_fmt(ref.get('min'))} to {_fmt(ref.get('max'))})" if ref else "-"
        lines.append(f"| {group} | {_fmt(candidate)} | {ref_text} | {_fmt(noise.get(group, {}).get('f1'))} |")
    attributes = score.get("mean", {}).get("headline", {}).get("attributes", {})
    lines.append("")
    lines.append("## Attribute agreement on matched atoms")
    lines.append("")
    lines.append("| attribute | n | exact | vote share | weighted kappa | reference alpha |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    alphas = score.get("reference_alpha", {})
    for key, entry in sorted(attributes.items()):
        alpha = alphas.get(key, {}).get("alpha")
        lines.append(
            f"| {key} | {entry.get('n')} | {_fmt(entry.get('exact'))} | {_fmt(entry.get('vote_share'))} | {_fmt(entry.get('weighted_kappa'))} | {_fmt(alpha)} |"
        )
    null = score.get("mean", {}).get("all", {}).get("null", {})
    lines.append("")
    lines.append("## Null windows, contrast, validity, cost")
    lines.append("")
    lines.append(f"- Null windows: {null.get('windows')} scored, {_fmt(null.get('atoms_per_window'))} atoms per window, share with any output {_fmt(null.get('share_with_output'))}")
    contrast = score.get("contrast", {})
    if contrast:
        lines.append(
            f"- Contrast pairs: targeted pass rate {_fmt(contrast.get('pass_rate'))} over {contrast.get('pairs')} pairs; "
            f"decoy pass rate {_fmt(contrast.get('decoy_pass_rate'))}; collateral change {_fmt(contrast.get('collateral_rate'))} vs no-op {_fmt(contrast.get('noop_collateral_rate'))}"
        )
    usage = score.get("usage", {})
    lines.append(
        f"- Validity: first-attempt acceptance {_fmt(usage.get('first_attempt_validity'))}, "
        f"{_fmt(usage.get('requests_per_accepted_window'))} requests per accepted window, rejected by kind {usage.get('rejected_by_kind', {})}"
    )
    lines.append(
        f"- Cost: {usage.get('output_tokens_per_accepted_window')} output tokens per accepted window, "
        f"{_fmt(usage.get('cost_per_accepted_window'))} USD per accepted window, {_fmt(usage.get('mean_seconds_per_request'))} s per request"
    )
    calibration = score.get("mean", {}).get("headline", {}).get("calibration", {})
    lines.append(f"- Calibration: confidence AUROC {_fmt(calibration.get('auroc'))} (TP mean {_fmt(calibration.get('mean_confidence_tp'))}, FP mean {_fmt(calibration.get('mean_confidence_fp'))})")
    lines.append("")
    lines.append("## Per stratum (topic soft F1 / claim required recall / yield)")
    lines.append("")
    lines.append("| stratum | items | topic F1 soft | topic yield | claim recall | claim precision | product F1 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for stratum, entry in sorted(score.get("mean", {}).get("by_stratum", {}).items()):
        g = entry.get("groups", {})
        lines.append(
            f"| {stratum} | {entry.get('items')} | {_fmt(g.get('detection:topic', {}).get('f1_soft'))} | {_fmt(g.get('detection:topic', {}).get('yield_ratio'))} | "
            f"{_fmt(g.get('claim', {}).get('recall_strict'))} | {_fmt(g.get('claim', {}).get('precision'))} | {_fmt(g.get('product', {}).get('f1_soft'))} |"
        )
    errors = score.get("mean", {}).get("headline", {}).get("errors", {})
    if errors:
        lines.append("")
        lines.append("## Error classes (headline strata, first repeat)")
        lines.append("")
        for key, count in sorted(errors.items(), key=lambda kv: -kv[1])[:16]:
            lines.append(f"- {key}: {count}")
    if agreement:
        lines.append("")
        lines.append("## Candidate as a fourth annotator (pairwise F1 with each reference)")
        lines.append("")
        lines.append("| annotator | topic | frame | evidence | claim | product |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for annotator, groups in sorted(agreement.items()):
            lines.append(
                f"| {annotator} | " + " | ".join(
                    _fmt(groups.get(g, {}).get("f1")) for g in ("detection:topic", "detection:frame", "detection:evidence", "claim", "product")
                ) + " |"
            )
        pairwise = score.get("reference_pairwise", {})
        for pair, groups in sorted(pairwise.items()):
            lines.append(
                f"| ref {pair} | " + " | ".join(
                    _fmt(groups.get(g, {}).get("f1")) for g in ("detection:topic", "detection:frame", "detection:evidence", "claim", "product")
                ) + " |"
            )
    return "\n".join(lines) + "\n"


def compare_markdown(name_a: str, name_b: str, comparison: dict[str, Any]) -> str:
    lines = [f"# Benchmark comparison: {name_a} -> {name_b}", ""]
    lines.append(f"Paired bootstrap over {comparison.get('rows')} item-repeat rows ({comparison.get('items')} shared items); positive delta favours {name_b}.")
    lines.append("")
    lines.append("| metric | A | B | delta | 95% CI | P(B>A) |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in comparison.get("metrics", []):
        lines.append(
            f"| {row['metric']} | {_fmt(row['a'])} | {_fmt(row['b'])} | {_fmt(row['delta'])} | [{_fmt(row['low'])}, {_fmt(row['high'])}] | {_fmt(row['share_positive'])} |"
        )
    lines.append("")
    lines.append("## Per stratum delta (topic soft F1, claim recall)")
    lines.append("")
    lines.append("| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |")
    lines.append("| --- | --- | --- | --- | --- |")
    for stratum, row in sorted(comparison.get("by_stratum", {}).items()):
        lines.append(f"| {stratum} | {_fmt(row['topic_a'])} | {_fmt(row['topic_b'])} | {_fmt(row['claim_a'])} | {_fmt(row['claim_b'])} |")
    moved = comparison.get("moved_items", [])
    if moved:
        lines.append("")
        lines.append("## Items that moved most (dev split)")
        lines.append("")
        for row in moved[:15]:
            lines.append(f"- {row['item_id']} ({row['stratum']}): topic tp {row['a_tp']}->{row['b_tp']}, fp {row['a_fp']}->{row['b_fp']}, fn {row['a_fn']}->{row['b_fn']}")
    return "\n".join(lines) + "\n"
