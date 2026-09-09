"""Atoms, spans and matching rules shared by gold construction and scoring.

A window result is exploded into *atoms*: one per (axis, label, span) for
detections, one per claim, one per product mention. Scoring a detection that
carries three labels as three atoms means an extra wrong label is an extra
false positive, so label-stuffing cannot buy recall for free.

Spans are unit index ranges inside the window (inclusive). Quotes are located
as character ranges in the window text, which is what lets two claims be
compared on the grounded text they cite rather than on a paraphrase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from analysis import topic_labeling as tl

DETECTION_SPAN_IOU = 0.5
# Two spans of the same label also match when the shorter lies at least this
# far inside the longer: annotators mark the same phenomenon at different
# extents (a clause vs the passage around it), and extent is scored separately
# as mean span IoU rather than as a miss plus a false positive.
DETECTION_SPAN_OVERLAP = 0.5
ENVELOPE_MIN_LENGTH_SHARE = 0.5
CLAIM_TEXT_SIMILARITY = 0.6
KINDS = ("detection", "claim", "product")
CERTAINTY_ORDER = {value: index for index, value in enumerate(tl.ALLOWED_EXPRESSED_CERTAINTY)}
_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass
class Atom:
    kind: str
    start: int
    end: int
    # detections
    axis: str | None = None
    label: str | None = None
    # attributes voted on across annotators
    attributes: dict[str, Any] = field(default_factory=dict)
    # claims and products: grounded text
    quote: str = ""
    quote_range: tuple[int, int] | None = None
    claim_text: str = ""
    product_key: str = ""
    product_name: str = ""
    confidence: float = 0.0
    # which source annotation this came from (index into the result list)
    source_index: int = -1
    # multi-label bookkeeping for claims: label sets by axis
    labels: dict[str, list[str]] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    def key(self) -> tuple[Any, ...]:
        """A stable identity used for diffs and repeat agreement."""
        if self.kind == "detection":
            return (self.kind, self.axis, self.label, self.start, self.end)
        if self.kind == "claim":
            return (self.kind, self.start, self.end, tl._normalized_quote(self.quote))
        return (self.kind, self.start, self.end, self.product_key)


class WindowIndex:
    """Unit positions and window text for one item, for locating spans and quotes."""

    def __init__(self, window: dict[str, Any]) -> None:
        self.units = window["units"]
        self.order = {unit["unit_id"]: index for index, unit in enumerate(self.units)}
        bounds: list[tuple[int, int]] = []
        cursor = 0
        for unit in self.units:
            bounds.append((cursor, cursor + len(unit["text"])))
            cursor += len(unit["text"]) + 1
        self.bounds = bounds
        self.text = " ".join(unit["text"] for unit in self.units)
        self.words = [(m.group(0).casefold(), m.start(), m.end()) for m in _WORD.finditer(self.text)]

    def span(self, start_id: str, end_id: str) -> tuple[int, int]:
        return self.order[start_id], self.order[end_id]

    def locate(self, quote: str, start: int, end: int) -> tuple[int, int] | None:
        """Character range of ``quote``'s word sequence inside units [start, end]."""
        quote_words = [m.group(0).casefold() for m in _WORD.finditer(quote)]
        if not quote_words:
            return None
        lo_char = self.bounds[start][0]
        hi_char = self.bounds[end][1]
        candidates = [w for w in self.words if w[1] >= lo_char and w[2] <= hi_char]
        n = len(quote_words)
        for index in range(len(candidates) - n + 1):
            if [w[0] for w in candidates[index : index + n]] == quote_words:
                return candidates[index][1], candidates[index + n - 1][2]
        # Fall back to the whole window: a repaired span may have moved.
        n_all = len(self.words)
        for index in range(n_all - n + 1):
            if [w[0] for w in self.words[index : index + n]] == quote_words:
                return self.words[index][1], self.words[index + n - 1][2]
        return None


def explode(result: dict[str, Any], index: WindowIndex, aliases: dict[str, str] | None = None) -> list[Atom]:
    """Atoms of one validated window result."""
    aliases = aliases or {}
    atoms: list[Atom] = []
    for position, detection in enumerate(result.get("detections", [])):
        start, end = index.span(detection["start_unit_id"], detection["end_unit_id"])
        quote_range = index.locate(detection.get("evidence_quote", ""), start, end)
        for label in sorted({aliases.get(l, l) for l in detection["label_ids"]}):
            atoms.append(
                Atom(
                    kind="detection",
                    start=start,
                    end=end,
                    axis=detection.get("axis"),
                    label=label,
                    attributes={
                        "relevance": detection.get("relevance"),
                        "discourse_role": detection.get("discourse_role"),
                    },
                    quote=detection.get("evidence_quote", ""),
                    quote_range=quote_range,
                    confidence=float(detection.get("confidence", 0.0)),
                    source_index=position,
                )
            )
    for position, claim in enumerate(result.get("verification_candidates", [])):
        start, end = index.span(claim["start_unit_id"], claim["end_unit_id"])
        atoms.append(
            Atom(
                kind="claim",
                start=start,
                end=end,
                attributes={
                    "discourse_role": claim.get("discourse_role"),
                    "claim_type": claim.get("claim_type"),
                    "expressed_certainty": claim.get("expressed_certainty"),
                    "relevance": claim.get("relevance"),
                },
                quote=claim.get("evidence_quote", ""),
                quote_range=index.locate(claim.get("evidence_quote", ""), start, end),
                claim_text=claim.get("claim_text", ""),
                confidence=float(claim.get("confidence", 0.0)),
                source_index=position,
                labels={
                    "topic": sorted({aliases.get(l, l) for l in claim.get("topic_ids", [])}),
                    "frame": sorted(claim.get("frame_ids", [])),
                    "evidence": sorted(claim.get("evidence_signal_ids", [])),
                },
            )
        )
    for position, product in enumerate(result.get("product_mentions", [])):
        start, end = index.span(product["start_unit_id"], product["end_unit_id"])
        atoms.append(
            Atom(
                kind="product",
                start=start,
                end=end,
                attributes={
                    "product_type": product.get("product_type"),
                    "mention_role": product.get("mention_role"),
                },
                quote=product.get("evidence_quote", ""),
                quote_range=index.locate(product.get("evidence_quote", ""), start, end),
                product_key=tl._product_key(product.get("product_name", "")),
                product_name=product.get("product_name", ""),
                confidence=float(product.get("confidence", 0.0)),
                source_index=position,
            )
        )
    return atoms


# --------------------------------------------------------------------------
# Span arithmetic
# --------------------------------------------------------------------------


def iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)
    union = (a[1] - a[0] + 1) + (b[1] - b[0] + 1) - inter
    return inter / union if union else 0.0


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return not (a[1] < b[0] or a[0] > b[1])


def overlap_coefficient(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Overlap of two unit spans as a share of the shorter one."""
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)
    shorter = min(a[1] - a[0] + 1, b[1] - b[0] + 1)
    return inter / shorter if shorter > 0 else 0.0


def char_overlap(a: tuple[int, int] | None, b: tuple[int, int] | None) -> float:
    """Overlap of two character ranges as a share of the shorter one."""
    if not a or not b:
        return 0.0
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    shorter = min(a[1] - a[0], b[1] - b[0])
    return inter / shorter if shorter > 0 else 0.0


def text_similarity(left: str, right: str) -> float:
    return tl._claim_similarity(left, right)


# --------------------------------------------------------------------------
# Gold clusters: what a prediction is matched against
# --------------------------------------------------------------------------


@dataclass
class GoldAtom:
    """One aggregated reference atom (see references.aggregate)."""

    gold_id: str
    kind: str
    tight: tuple[int, int]
    envelope: tuple[int, int]
    axis: str | None
    label: str | None
    tier: str  # required | acceptable | singleton | rejected
    support: float  # share of annotators
    annotators: list[str]
    votes: dict[str, dict[str, int]]  # attribute -> value -> count
    quotes: list[str]
    quote_ranges: list[tuple[int, int]]
    claim_texts: list[str]
    product_keys: list[str]
    product_names: list[str]

    def plurality(self, attribute: str) -> Any:
        votes = self.votes.get(attribute) or {}
        if not votes:
            return None
        return max(sorted(votes), key=lambda value: votes[value])

    def vote_share(self, attribute: str, value: Any) -> float:
        votes = self.votes.get(attribute) or {}
        total = sum(votes.values())
        return votes.get(value, 0) / total if total else 0.0


def match_score(pred: Atom, gold: GoldAtom) -> float:
    """0 when the pair does not match, else a score in (0, 1] for assignment."""
    if pred.kind != gold.kind:
        return 0.0
    p = (pred.start, pred.end)
    if pred.kind == "detection":
        if pred.axis != gold.axis or pred.label != gold.label:
            return 0.0
        tight_iou = iou(p, gold.tight)
        if tight_iou >= DETECTION_SPAN_IOU:
            return tight_iou
        if overlap_coefficient(p, gold.tight) >= DETECTION_SPAN_OVERLAP:
            return max(tight_iou, 0.01)
        inside = gold.envelope[0] <= p[0] and p[1] <= gold.envelope[1]
        tight_len = gold.tight[1] - gold.tight[0] + 1
        if inside and pred.length >= ENVELOPE_MIN_LENGTH_SHARE * tight_len:
            return max(tight_iou, 0.01)
        return 0.0
    if pred.kind == "claim":
        if not overlaps(p, gold.envelope):
            return 0.0
        quote = max((char_overlap(pred.quote_range, r) for r in gold.quote_ranges), default=0.0)
        text = max((text_similarity(pred.claim_text, t) for t in gold.claim_texts), default=0.0)
        if quote > 0:
            return 0.5 + 0.5 * quote + 0.25 * text if quote < 1 else 1.0
        if text >= CLAIM_TEXT_SIMILARITY:
            return 0.25 + 0.25 * text
        return 0.0
    if pred.kind == "product":
        if not overlaps(p, gold.envelope):
            return 0.0
        if pred.product_key in gold.product_keys:
            return 1.0
        if pred.attributes.get("product_type") == gold.plurality("product_type"):
            return 0.5
        return 0.0
    return 0.0


def assign(preds: Sequence[Atom], golds: Sequence[GoldAtom]) -> list[tuple[int, int, float]]:
    """Optimal one-to-one matching; returns (pred_index, gold_index, score) triples."""
    if not preds or not golds:
        return []
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    matrix = np.zeros((len(preds), len(golds)))
    for i, pred in enumerate(preds):
        for j, gold in enumerate(golds):
            matrix[i, j] = match_score(pred, gold)
    if not matrix.any():
        return []
    rows, cols = linear_sum_assignment(-matrix)
    return [(int(i), int(j), float(matrix[i, j])) for i, j in zip(rows, cols) if matrix[i, j] > 0]


def near_miss_class(pred: Atom, golds: Sequence[GoldAtom]) -> str:
    """Why an unmatched prediction did not match: what the nearest gold looks like."""
    p = (pred.start, pred.end)
    same_kind = [g for g in golds if g.kind == pred.kind and overlaps(p, g.envelope)]
    if pred.kind == "detection":
        if any(g.axis == pred.axis and g.label == pred.label for g in same_kind):
            return "span_only"
        if any(g.axis == pred.axis for g in same_kind):
            return "same_axis_wrong_label"
        if same_kind:
            return "cross_axis"
        return "spurious"
    if same_kind:
        return "different_" + pred.kind
    return "spurious"
