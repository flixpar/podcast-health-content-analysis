"""Window-level lexicon matching, ported from the corpus scan.

The whole-corpus scan (branch ``analysis/fast-lexical-scan``) is the sampling
frame for the item pool, but its sentence rows are hard to align with the
pipeline's units. The pool therefore re-runs the same lexicon over the units of
each candidate window, which gives per-unit hits with no alignment step and
the same term semantics as the scan's per-episode counts.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

REGEX_CHARS = set("()|?[]\\+*{}")
HEALTH_SECTIONS = ("topics", "frames", "evidence", "narratives", "products")
SPEAKER_RE = re.compile(r"^\s*(?:Speaker\s*\d+|[A-Z][A-Za-z .'-]{1,40})\s*:\s+")


def trie_regex(words: Sequence[str]) -> str:
    """Compile literal phrases into one trie-shaped alternation."""
    trie: dict[str, Any] = {}
    for word in words:
        node = trie
        for ch in word:
            node = node.setdefault(ch, {})
        node[""] = True

    def build(node: dict[str, Any]) -> str:
        if "" in node and len(node) == 1:
            return ""
        alts: list[str] = []
        chars: list[str] = []
        for ch, sub in sorted(node.items()):
            if ch == "":
                continue
            rest = build(sub)
            if rest == "":
                chars.append(re.escape(ch))
            else:
                alts.append(re.escape(ch) + rest)
        if chars:
            alts.append(chars[0] if len(chars) == 1 else "[" + "".join(chars) + "]")
        out = alts[0] if len(alts) == 1 else "(?:" + "|".join(alts) + ")"
        return out + "?" if "" in node else out

    return build(trie)


class Matcher:
    """Term matcher over one lexicon file; ``match`` returns (section, label, term) hits."""

    def __init__(self, lexicon: dict[str, Any]) -> None:
        self.literal: dict[str, list[tuple[str, str]]] = {}
        self.regex: list[tuple[re.Pattern[str], str, str, str]] = []
        self.product_health: dict[str, bool] = {}
        for section, body in lexicon.items():
            if section in ("topics", "frames", "evidence", "narratives", "products", "certainty"):
                for label, spec in body.items():
                    if section == "products":
                        self.product_health[label] = bool(spec.get("health_related", True))
                    for term in spec["terms"]:
                        self._add(term, section, label)
            else:
                for term in body["terms"]:
                    self._add(term, section, section)
        self.literal_re = re.compile(
            r"\b(?:" + trie_regex(sorted(self.literal)) + r")\b", re.I
        )

    @classmethod
    def from_path(cls, path: Path) -> Matcher:
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def _add(self, term: str, section: str, label: str) -> None:
        term = term.strip().lower()
        if not term:
            return
        if any(ch in REGEX_CHARS for ch in term):
            self.regex.append((re.compile(term, re.I), section, label, term))
        else:
            self.literal.setdefault(term, []).append((section, label))

    def match(self, text: str) -> list[tuple[str, str, str]]:
        low = SPEAKER_RE.sub("", text).lower()
        hits: list[tuple[str, str, str]] = []
        for found in self.literal_re.finditer(low):
            term = found.group(0)
            for section, label in self.literal.get(term, ()):
                hits.append((section, label, term))
        if hits:
            for pattern, section, label, term in self.regex:
                if pattern.search(low):
                    hits.append((section, label, term))
        return hits

    def window_features(self, units: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Per-window hit summary: units hit per section, labels, terms."""
        section_units: Counter[str] = Counter()
        label_units: Counter[str] = Counter()
        terms: dict[str, set[str]] = {}
        hit_unit_indexes: list[int] = []
        health_product_units = 0
        for index, unit in enumerate(units):
            hits = self.match(unit["text"])
            if not hits:
                continue
            hit_unit_indexes.append(index)
            sections = {section for section, _, _ in hits}
            for section in sections:
                section_units[section] += 1
            for section, label, term in set(hits):
                label_units[f"{section}:{label}"] += 1
                terms.setdefault(f"{section}:{label}", set()).add(term)
            if any(
                section == "products" and self.product_health.get(label, True)
                for section, label, _ in hits
            ):
                health_product_units += 1
        health_units = len(
            {
                index
                for index in hit_unit_indexes
                if any(
                    section in HEALTH_SECTIONS
                    for section, _, _ in self.match(units[index]["text"])
                )
            }
        )
        return {
            "units": len(units),
            "health_units": health_units,
            "health_product_units": health_product_units,
            "section_units": dict(section_units),
            "label_units": dict(label_units),
            "terms": {key: sorted(value) for key, value in terms.items()},
        }


def repeated_ngram_ratio(text: str, n: int = 3) -> float:
    """Share of word n-grams that repeat, a cheap ASR-stutter signal."""
    words = text.lower().split()
    if len(words) < n + 1:
        return 0.0
    grams = Counter(tuple(words[i : i + n]) for i in range(len(words) - n + 1))
    repeated = sum(count - 1 for count in grams.values() if count > 1)
    return repeated / max(1, len(words) - n + 1)
