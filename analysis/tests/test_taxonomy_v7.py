"""The granular v7 taxonomy: compilation, prompt, response contract and merge."""

import argparse
import csv
import json
import re
from pathlib import Path

import pytest

from analysis import topic_labeling as labeling


ROOT = Path(__file__).resolve().parents[2]
V7_SOURCE = ROOT / "taxonomy" / "health-v7.md"


@pytest.fixture(scope="module")
def v7():
    return labeling.compile_taxonomy(V7_SOURCE)


def test_v7_compiles_five_axes_with_a_topic_tree(v7):
    labels = v7["labels"]
    assert v7["format"] == labeling.HIERARCHICAL_FORMAT
    assert v7["schema_version"] == labeling.HIERARCHICAL_SCHEMA_VERSION
    assert {row["axis"] for row in labels} == set(labeling.HIERARCHICAL_AXES)
    ids = {row["label_id"] for row in labels}
    assert len(ids) == len(labels)
    parents = {row["label_id"] for row in labels if row.get("level") == "parent"}
    subtopics = [row for row in labels if row.get("level") == "subtopic"]
    assert len(parents) >= 50 and len(subtopics) >= 300
    for row in subtopics:
        assert row["parent"] in parents
        assert row["label_id"].startswith(row["parent"] + ".")
        assert labeling.topic_parent(row["label_id"]) == row["parent"]
        assert row["definition"].strip()
    domains = {d["domain_id"] for d in v7["domains"]}
    assert all(row["domain"] in domains for row in labels if row["axis"] == "topic")
    narratives = [row for row in labels if row["axis"] == "narrative"]
    assert len(narratives) >= 100
    assert all(row["home_topic"] in parents for row in narratives)
    assert all(re.fullmatch(r"[a-z]+:[a-z0-9_]+(\.[a-z0-9_]+)?", label) for label in ids)


def test_v7_cross_references_name_real_labels(v7):
    """A boundary note that points at a label that does not exist misroutes coders."""
    ids = {row["label_id"] for row in v7["labels"]}
    texts = [row["definition"] for row in v7["labels"]]
    texts.append(labeling.DEFAULT_V7_CODEBOOK.read_text(encoding="utf-8"))
    for text in texts:
        for token in re.findall(r"`([a-z0-9_]+(?::[a-z0-9_.]+|\.[a-z0-9_]+))`", text):
            assert token in ids or f"topic:{token}" in ids, token


def test_flat_taxonomy_keeps_its_schema_and_prompt_identity():
    flat = labeling.compile_taxonomy(ROOT / "topics.md")
    assert flat["schema_version"] == labeling.SCHEMA_VERSION
    assert "format" not in flat
    assert labeling.prompt_version(flat).startswith(labeling.PROMPT_VERSION + ":")
    schema = labeling.response_schema(flat)
    claim = schema["properties"]["verification_candidates"]["items"]
    assert "narrative_ids" not in claim["properties"]
    assert schema["properties"]["detections"]["maxItems"] == 40


def _source(tmp_path, body):
    path = tmp_path / "taxonomy.md"
    path.write_text(body, encoding="utf-8")
    return path


MINIMAL = """\
## Topic axis

### Domain: Sleep and rest `rest`

#### Sleep `sleep`
Sleep and its disorders.

| id | name | definition | examples |
| --- | --- | --- | --- |
| apnea | Sleep apnea | Breathing during sleep. | CPAP; snoring |

#### Other `other`
Anything else.

| id | name | definition | examples |
| --- | --- | --- | --- |

## Narrative axis

### Sleep `sleep_narratives`

| id | name | definition | examples | home topic |
| --- | --- | --- | --- | --- |
| eight_hours | Everyone needs eight hours | Every adult needs exactly eight hours. | eight hours | {home} |

## Frame axis

| id | name | definition | examples |
| --- | --- | --- | --- |
| fear_alarm | Fear | Alarmist language. | crisis |

## Evidence axis

| id | name | definition | examples |
| --- | --- | --- | --- |
| vague_research | Vague research | Studies show. | studies show |

## Population axis

| id | name | definition | examples |
| --- | --- | --- | --- |
| children | Children | About kids. | kids |
"""


def test_minimal_v7_source_compiles_and_an_empty_parent_table_is_allowed(tmp_path):
    taxonomy = labeling.compile_taxonomy(_source(tmp_path, MINIMAL.format(home="sleep")))
    ids = [row["label_id"] for row in taxonomy["labels"]]
    assert ids == [
        "topic:sleep",
        "topic:sleep.apnea",
        "topic:other",
        "narrative:eight_hours",
        "frame:fear_alarm",
        "evidence:vague_research",
        "population:children",
    ]


def test_v7_compile_fails_closed(tmp_path):
    with pytest.raises(labeling.TopicLabelingError, match="home topic"):
        labeling.compile_taxonomy(_source(tmp_path, MINIMAL.format(home="nonexistent")))
    with pytest.raises(labeling.TopicLabelingError, match="lowercase"):
        labeling.compile_taxonomy(
            _source(tmp_path, MINIMAL.format(home="sleep").replace("| apnea |", "| Apnea |"))
        )
    with pytest.raises(labeling.TopicLabelingError, match="definition"):
        labeling.compile_taxonomy(
            _source(tmp_path, MINIMAL.format(home="sleep").replace("Sleep and its disorders.\n", ""))
        )
    with pytest.raises(labeling.TopicLabelingError, match="population"):
        labeling.compile_taxonomy(
            _source(tmp_path, MINIMAL.format(home="sleep").split("## Population axis")[0])
        )


def test_v7_prompt_embeds_rubric_codebook_and_every_label(v7, tmp_path):
    instructions = labeling.taxonomy_instructions(v7)
    assert instructions.startswith(labeling.DEFAULT_V7_RUBRIC.read_text(encoding="utf-8").rstrip())
    assert "# Codebook v7" in instructions
    for row in v7["labels"]:
        assert f"`{row['label_id']}`" in instructions
    version = labeling.prompt_version(v7)
    assert version.startswith(labeling.HIERARCHICAL_PROMPT_VERSION + ":")
    rubric = tmp_path / "rubric.md"
    rubric.write_text("A different rubric.", encoding="utf-8")
    other = labeling.hierarchical_instructions(v7, rubric_path=rubric)
    assert labeling.prompt_version(v7, other) != version


def _worked_example():
    rubric = labeling.DEFAULT_V7_RUBRIC.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", rubric, re.DOTALL)
    window, result = (json.loads(block) for block in blocks[:2])
    return window, result


def test_the_rubric_worked_example_is_a_valid_v7_result(v7):
    window, result = _worked_example()
    axes = {row["label_id"]: row["axis"] for row in v7["labels"]}
    normalized = labeling.validate_window_result(result, window, axes)
    used = {axes[label] for row in normalized["detections"] for label in row["label_ids"]}
    assert used == set(labeling.HIERARCHICAL_AXES)
    assert all("narrative_ids" in row for row in normalized["verification_candidates"])


def test_v7_schema_and_validation_require_claim_narratives_and_relevance(v7):
    window, result = _worked_example()
    axes = {row["label_id"]: row["axis"] for row in v7["labels"]}
    schema = labeling.response_schema(v7)
    claim_schema = schema["properties"]["verification_candidates"]["items"]
    assert {"narrative_ids", "relevance"} <= set(claim_schema["required"])
    assert schema["properties"]["detections"]["maxItems"] == 60
    product_types = schema["properties"]["product_mentions"]["items"]["properties"]["product_type"]["enum"]
    assert "household_or_home" in product_types and "nicotine_or_tobacco" in product_types

    missing_relevance = json.loads(json.dumps(result))
    del missing_relevance["verification_candidates"][0]["relevance"]
    with pytest.raises(labeling.TopicLabelingError) as error:
        labeling.validate_window_result(missing_relevance, window, axes)
    assert error.value.kind == "schema_shape"

    topic_as_narrative = json.loads(json.dumps(result))
    topic_as_narrative["verification_candidates"][0]["narrative_ids"] = ["topic:vaccines.hep_b"]
    with pytest.raises(labeling.TopicLabelingError) as error:
        labeling.validate_window_result(topic_as_narrative, window, axes)
    assert error.value.kind == "mixed_or_unknown_labels"

    mixed_axes = json.loads(json.dumps(result))
    mixed_axes["detections"][0]["label_ids"].append("population:infants")
    with pytest.raises(labeling.TopicLabelingError) as error:
        labeling.validate_window_result(mixed_axes, window, axes)
    assert error.value.kind == "mixed_or_unknown_labels"


def test_v7_merge_carries_parents_narratives_and_populations(v7, tmp_path):
    window, result = _worked_example()
    for offset, product_name, product_type in [
        (115, "Nicotine pouch", "nicotine_or_tobacco"),
        (116, "Home air purifier", "household_or_home"),
    ]:
        unit_id = f"u{offset:06d}"
        window["units"].append({"unit_id": unit_id, "text": product_name})
        result["product_mentions"].append(
            {
                "start_unit_id": unit_id,
                "end_unit_id": unit_id,
                "product_name": product_name,
                "product_type": product_type,
                "mention_role": "neutral",
                "evidence_quote": product_name,
                "confidence": 0.9,
            }
        )
    taxonomy_path = tmp_path / "taxonomy.json"
    labeling.write_json(taxonomy_path, v7)
    common = {
        "schema_version": labeling.SCHEMA_VERSION,
        "episode_id": 900,
        "podcast_id": 2,
        "podcast_title": "Test show",
        "episode_title": "Test episode",
        "published_date": "2026-01-01",
        "source_transcript": "episode_900.jsonl.zst",
        "source_transcript_sha256": "a" * 64,
    }
    units = [
        {
            **unit,
            "start_seconds": float(index * 10),
            "end_seconds": float(index * 10 + 9),
            "timing_quality": "segment",
            "source_segment_index": index,
        }
        for index, unit in enumerate(window["units"])
    ]
    windows = [{**common, "window_id": window["window_id"], "window_index": 3, "units": units}]
    windows_path = tmp_path / "windows.jsonl.zst"
    labeling.write_jsonl_atomic(windows_path, windows)
    run_manifest = {
        "run_fingerprint": "b" * 64,
        "model": "local-model",
        "taxonomy_sha256": v7["taxonomy_sha256"],
    }
    store = labeling.LabelStore(tmp_path / "labels.sqlite", run_manifest)
    store.record_success(windows[0], result, {"response_id": "r", "response_model": "m", "usage": None})
    store.close()
    manifest_path = tmp_path / "label_manifest.json"
    labeling.write_json(manifest_path, run_manifest)
    summary = labeling.run_merge(
        argparse.Namespace(
            output_dir=tmp_path,
            taxonomy=taxonomy_path,
            windows=windows_path,
            label_manifest=manifest_path,
            allow_incomplete=False,
        )
    )
    assert summary["complete"] is True
    annotations = list(labeling.iter_jsonl(tmp_path / "label_annotations.jsonl"))
    topic_rows = [row for row in annotations if row["axis"] == "topic"]
    assert all(row["parent_topic_id"] == labeling.topic_parent(row["label_id"]) for row in topic_rows)
    assert all(row["schema_version"] == labeling.HIERARCHICAL_SCHEMA_VERSION for row in annotations)
    assert {row["axis"] for row in annotations} == set(labeling.HIERARCHICAL_AXES)
    clips = list(labeling.iter_jsonl(tmp_path / "clips.jsonl"))
    assert any(clip["narrative_annotations"] for clip in clips)
    assert any(clip["population_annotations"] for clip in clips)
    claims = list(labeling.iter_jsonl(tmp_path / "verification_candidates.jsonl"))
    rebutted = next(c for c in claims if c["discourse_role"] == "rebutted")
    assert rebutted["narrative_ids"] == ["narrative:vaccines_cause_autism"]
    assert rebutted["narrative_names"] == ["Vaccines cause autism"]
    assert "topic:neurodevelopment" in rebutted["parent_topic_ids"]
    assert any(c["relevance"] == ["advertisement"] for c in claims)
    products = list(labeling.iter_jsonl(tmp_path / "product_mentions.jsonl"))
    assert len(products) == 3
    assert all(row["schema_version"] == labeling.HIERARCHICAL_SCHEMA_VERSION for row in products)
    assert {"nicotine_or_tobacco", "household_or_home"} <= {
        row["product_type"] for row in products
    }
    with (tmp_path / "review_queue.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert "narrative_ids" in rows[0] and "population_ids" in rows[0]
    assert any("narrative:vaccines_cause_autism" in row["narrative_ids"] for row in rows)
