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


def compile_benchmark_taxonomy(topics_path: Path, out_path: Path = TAXONOMY_PATH) -> dict[str, Any]:
    taxonomy = tl.compile_taxonomy(Path(topics_path))
    label_ids = {label["label_id"] for label in taxonomy["labels"]}
    for source, target in LABEL_ALIASES_V5.items():
        if source not in label_ids or target not in label_ids:
            raise tl.TopicLabelingError(f"alias {source} -> {target} names an unknown label")
    taxonomy = {
        **taxonomy,
        "benchmark_version": BENCHMARK_VERSION,
        "label_aliases": {"v5-84": LABEL_ALIASES_V5},
    }
    tl.write_json(Path(out_path), taxonomy)
    return taxonomy


def load_benchmark_taxonomy(path: Path = TAXONOMY_PATH) -> dict[str, Any]:
    taxonomy = json.loads(Path(path).read_text(encoding="utf-8"))
    if taxonomy.get("schema_version") != tl.SCHEMA_VERSION:
        raise tl.TopicLabelingError(f"{path} has schema {taxonomy.get('schema_version')}")
    return taxonomy


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
