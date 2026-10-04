"""The v8 revision of the granular taxonomy: its own codebook, rubric and prompt identity."""

import json
import re
from pathlib import Path

import pytest

from analysis import topic_labeling as labeling


ROOT = Path(__file__).resolve().parents[2]
V8_SOURCE = ROOT / "taxonomy" / "health-v8.md"


@pytest.fixture(scope="module")
def v8():
    return labeling.compile_taxonomy(V8_SOURCE)


def test_v8_compiles_and_selects_its_own_prompt_files(v8):
    assert v8["format"] == labeling.HIERARCHICAL_FORMAT
    assert v8["taxonomy_version"] == "v8"
    rubric, codebook = labeling.prompt_files(v8)
    assert rubric.name == "rubric-v8.md" and codebook.name == "codebook-v8.md"
    assert {row["axis"] for row in v8["labels"]} == set(labeling.HIERARCHICAL_AXES)
    parents = {row["label_id"] for row in v8["labels"] if row.get("level") == "parent"}
    narratives = [row for row in v8["labels"] if row["axis"] == "narrative"]
    assert all(row["home_topic"] in parents for row in narratives)


def test_v8_narratives_state_a_bold_core_proposition(v8):
    for row in v8["labels"]:
        if row["axis"] == "narrative" and row["label_id"] != "narrative:unlisted_narrative":
            assert row["definition"].startswith("**"), row["label_id"]


def test_v8_cross_references_name_real_labels(v8):
    ids = {row["label_id"] for row in v8["labels"]}
    texts = [row["definition"] for row in v8["labels"]]
    texts.append(labeling.prompt_files(v8)[1].read_text(encoding="utf-8"))
    texts.append(labeling.prompt_files(v8)[0].read_text(encoding="utf-8"))
    for text in texts:
        for token in re.findall(r"`([a-z0-9_]+(?::[a-z0-9_.]+|\.[a-z0-9_]+))`", text):
            assert token in ids or f"topic:{token}" in ids, token


def test_v8_prompt_identity_is_its_own_and_v7_is_unchanged(v8):
    v7 = labeling.compile_taxonomy(ROOT / "taxonomy" / "health-v7.md")
    instructions = labeling.taxonomy_instructions(v8)
    assert instructions.startswith(labeling.prompt_files(v8)[0].read_text(encoding="utf-8").rstrip())
    assert "# Codebook v8" in instructions
    for row in v8["labels"]:
        assert f"`{row['label_id']}`" in instructions
    assert labeling.prompt_version(v8).startswith("granular-v8:")
    assert labeling.prompt_version(v7).startswith(labeling.HIERARCHICAL_PROMPT_VERSION + ":")
    # A compiled taxonomy saved before the version was recorded is v7.
    legacy = {key: value for key, value in v7.items() if key != "taxonomy_version"}
    assert labeling.prompt_files(legacy) == (labeling.DEFAULT_V7_RUBRIC, labeling.DEFAULT_V7_CODEBOOK)
    assert labeling.prompt_version(legacy) == labeling.prompt_version(v7)


def test_the_v8_worked_example_is_a_valid_result(v8):
    rubric = labeling.prompt_files(v8)[0].read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", rubric, re.DOTALL)
    window, result = (json.loads(block) for block in blocks[:2])
    axes = {row["label_id"]: row["axis"] for row in v8["labels"]}
    normalized = labeling.validate_window_result(result, window, axes)
    used = {axes[label] for row in normalized["detections"] for label in row["label_ids"]}
    assert used == set(labeling.HIERARCHICAL_AXES)
    evidence = [row for row in normalized["detections"] if axes[row["label_ids"][0]] == "evidence"]
    order = {unit["unit_id"]: index for index, unit in enumerate(window["units"])}
    for claim in normalized["verification_candidates"]:
        for label in claim["evidence_signal_ids"]:
            assert any(
                label in row["label_ids"]
                and order[row["start_unit_id"]] <= order[claim["end_unit_id"]]
                and order[claim["start_unit_id"]] <= order[row["end_unit_id"]]
                for row in evidence
            ), (claim["claim_text"], label)
