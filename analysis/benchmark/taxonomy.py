"""The benchmark's frozen taxonomy and the alias map to other label sets.

The gold is built on the v6 91-label taxonomy (``benchmark/topics-v6.md``).
A run made on main's 84-label taxonomy has no way to say ``topic:cancer``, so
scoring collapses the seven added topics onto the label the older taxonomy
would have used -- on both sides, so the comparison is symmetric.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis import topic_labeling as tl
from analysis.benchmark import BENCHMARK_VERSION, TAXONOMY_PATH

# v6 topic -> the 84-label topic that absorbed that content before v6 added it.
# From the boundary notes in topics-v6.md and the v6 findings doc: wounds had
# been forced into Pain / Musculoskeletal, dementia into Brain / Cognition,
# the rest into the explicit gap label.
LABEL_ALIASES_V5: dict[str, str] = {
    "topic:cancer": "topic:other_health_topic",
    "topic:neurology_seizures_brain_conditions": "topic:other_health_topic",
    "topic:dementia_cognitive_decline_ageing": "topic:brain_cognition_productivity",
    "topic:injury_wound_care_first_aid": "topic:pain_musculoskeletal_health",
    "topic:surgery_medical_procedures": "topic:other_health_topic",
    "topic:hearing_vision_sensory_health": "topic:other_health_topic",
    "topic:genetics_inheritance": "topic:other_health_topic",
}


# Scoring levels of the v7 topic tree. Gold is built from the subtopics the
# annotators chose; the coarser levels re-cluster the same references with
# these alias maps, so "right parent, wrong subtopic" is visible as a number.
LEVELS = ("subtopic", "parent", "domain")


def hierarchy_aliases(taxonomy: dict[str, Any], level: str) -> dict[str, str]:
    """Topic label -> its label at ``level``; other axes are left alone.

    ``parent`` maps every subtopic to its parent topic (parents map to
    themselves). ``domain`` maps every topic label to a pseudo-label
    ``topic:@<domain_id>`` on the same axis, so a domain match is still a
    same-axis topic match for the scorer.
    """
    if level == "subtopic":
        return {}
    if level not in LEVELS:
        raise tl.TopicLabelingError(f"unknown scoring level {level!r}; have {LEVELS}")
    aliases: dict[str, str] = {}
    for label in taxonomy["labels"]:
        if label["axis"] != "topic":
            continue
        if level == "parent":
            if label.get("parent"):
                aliases[label["label_id"]] = label["parent"]
        else:
            aliases[label["label_id"]] = f"topic:@{label['domain']}"
    return aliases


def compile_benchmark_taxonomy(topics_path: Path, out_path: Path = TAXONOMY_PATH) -> dict[str, Any]:
    taxonomy = tl.compile_taxonomy(Path(topics_path))
    label_ids = {label["label_id"] for label in taxonomy["labels"]}
    if tl.is_hierarchical(taxonomy):
        label_aliases = {level: hierarchy_aliases(taxonomy, level) for level in LEVELS[1:]}
    else:
        for source, target in LABEL_ALIASES_V5.items():
            if source not in label_ids or target not in label_ids:
                raise tl.TopicLabelingError(f"alias {source} -> {target} names an unknown label")
        label_aliases = {"v5-84": LABEL_ALIASES_V5}
    taxonomy = {
        **taxonomy,
        "benchmark_version": BENCHMARK_VERSION,
        "label_aliases": label_aliases,
    }
    tl.write_json(Path(out_path), taxonomy)
    return taxonomy


def load_benchmark_taxonomy(path: Path = TAXONOMY_PATH) -> dict[str, Any]:
    taxonomy = json.loads(Path(path).read_text(encoding="utf-8"))
    if taxonomy.get("schema_version") not in tl.SUPPORTED_TAXONOMY_SCHEMAS:
        raise tl.TopicLabelingError(f"{path} has schema {taxonomy.get('schema_version')}")
    return taxonomy


def scoring_levels(taxonomy: dict[str, Any]) -> tuple[str, ...]:
    """The topic levels a benchmark is scored at: all three under v7, one before."""
    return LEVELS if tl.is_hierarchical(taxonomy) else ("subtopic",)


def label_axes(taxonomy: dict[str, Any]) -> dict[str, str]:
    return {label["label_id"]: label["axis"] for label in taxonomy["labels"]}


def alias_map(taxonomy: dict[str, Any], name: str | None) -> dict[str, str]:
    """The collapse map for a named alias set, or empty for none."""
    if not name:
        return {}
    aliases = taxonomy.get("label_aliases", {})
    if name not in aliases:
        raise tl.TopicLabelingError(f"unknown label alias set {name!r}; have {sorted(aliases)}")
    return dict(aliases[name])
