"""Benchmark v2: the granular v7 taxonomy, scored at three levels of the topic tree."""

import argparse
import json
from pathlib import Path

import pytest

from analysis import topic_labeling as tl
from analysis.benchmark import __main__ as cli
from analysis.benchmark import matching, references, scoring, runner
from analysis.benchmark.taxonomy import hierarchy_aliases, label_axes, scoring_levels

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY = tl.compile_taxonomy(ROOT / "taxonomy" / "health-v7.md")
AXES = label_axes(TAXONOMY)


def test_merged_generative_benchmark_retains_hierarchical_schema_and_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(tl.ResponsesClient, "served_models", lambda self: {"http://test": "stub"})
    monkeypatch.setattr(tl, "resolve_api_key", lambda args: None)
    args = runner.label_args(["--model", "stub", "--api-base", "http://test"], config=None)
    manifest = runner.run_benchmark([], TAXONOMY, args, "granular", repeats=0, runs_dir=tmp_path)
    assert manifest["schema_version"] == TAXONOMY["schema_version"]
    assert manifest["prompt_version"] == tl.prompt_version(TAXONOMY)
    assert manifest["schema_version"] != tl.SCHEMA_VERSION

UNITS = [
    "Welcome back to the show everybody.",
    "My kid got the hepatitis B shot at birth and the whole schedule after that.",
    "Some people say that vaccines cause autism but that has been studied a lot.",
    "Anyway the game last night was wild.",
]


def make_item(item_id="c1w0001", stratum="health_dense", split="dev"):
    units = [
        {"unit_id": f"u{i + 1:06d}", "text": t, "start_seconds": None, "end_seconds": None,
         "timing_quality": "unavailable", "source_segment_index": 0}
        for i, t in enumerate(UNITS)
    ]
    return {"window_id": f"episode_1_window_{item_id[-4:]}", "episode_id": 1, "window_index": 1,
            "units": units, "item_id": item_id, "stratum": stratum, "split": split, "source": "corpus",
            "provenance": {"podcast_id": 1}}


def detection(start, end, labels, quote, role="asserted_or_endorsed"):
    return {"start_unit_id": start, "end_unit_id": end, "label_ids": labels, "relevance": "substantive",
            "discourse_role": role, "confidence": 0.9, "summary": "s", "evidence_quote": quote}


def claim(narratives=("narrative:vaccines_cause_autism",)):
    return {"start_unit_id": "u000003", "end_unit_id": "u000003", "topic_ids": ["topic:vaccines.safety_injury"],
            "narrative_ids": list(narratives), "frame_ids": [], "evidence_signal_ids": [], "relevance": "substantive",
            "discourse_role": "rebutted", "claim_type": "causal", "claim_text": "Vaccines cause autism.",
            "expressed_certainty": "speculative", "certainty_markers": ["Some people say"],
            "evidence_quote": "vaccines cause autism", "confidence": 0.8, "rationale": "r"}


def raw(item, topic):
    return {
        "window_id": item["window_id"],
        "detections": [
            detection("u000002", "u000002", [topic], "hepatitis B shot at birth"),
            detection("u000003", "u000003", ["narrative:vaccines_cause_autism"], "vaccines cause autism", "rebutted"),
        ],
        "verification_candidates": [claim()],
        "product_mentions": [],
    }


def labeled(item, topic):
    return references.validate_result(raw(item, topic), item, AXES)


def test_hierarchy_aliases_map_subtopics_to_parent_and_domain():
    parent = hierarchy_aliases(TAXONOMY, "parent")
    domain = hierarchy_aliases(TAXONOMY, "domain")
    assert parent["topic:vaccines.hep_b"] == "topic:vaccines"
    assert "topic:vaccines" not in parent
    assert domain["topic:vaccines.hep_b"] == domain["topic:vaccines"] == "topic:@vaccines_infectious"
    assert "narrative:vaccines_cause_autism" not in parent and "narrative:vaccines_cause_autism" not in domain
    assert hierarchy_aliases(TAXONOMY, "subtopic") == {}
    assert scoring_levels(TAXONOMY) == ("subtopic", "parent", "domain")


def test_v7_reference_validation_requires_claim_relevance_in_the_pipeline_contract():
    item = make_item()
    normalized = labeled(item, "topic:vaccines.hep_b")
    assert normalized["verification_candidates"][0]["narrative_ids"] == ["narrative:vaccines_cause_autism"]
    bad = raw(item, "topic:vaccines.hep_b")
    del bad["verification_candidates"][0]["relevance"]
    with pytest.raises(tl.TopicLabelingError):
        references.validate_result(bad, item, AXES)


def test_sibling_subtopics_split_at_the_leaf_and_agree_at_the_parent():
    item = make_item()
    refs = {item["item_id"]: {
        "a": {"result": labeled(item, "topic:vaccines.hep_b")},
        "b": {"result": labeled(item, "topic:vaccines.childhood_schedule")},
    }}
    leaf, _ = references.aggregate([item], refs, {}, {})
    leaf_topics = [r for r in leaf if r["kind"] == "detection" and r["axis"] == "topic"]
    assert sorted(r["tier"] for r in leaf_topics) == ["singleton", "singleton"]
    narrative = [r for r in leaf if r["axis"] == "narrative"]
    assert len(narrative) == 1 and narrative[0]["tier"] == "required"

    parent, _ = references.aggregate([item], refs, {}, {}, aliases=hierarchy_aliases(TAXONOMY, "parent"))
    parent_topics = [r for r in parent if r["kind"] == "detection" and r["axis"] == "topic"]
    assert [(r["label"], r["tier"]) for r in parent_topics] == [("topic:vaccines", "required")]

    # A candidate with a third sibling misses at the leaf but is credited at the parent.
    candidate = labeled(item, "topic:vaccines.mmr")
    leaf_gold = [references.gold_from_record(r) for r in leaf]
    parent_gold = [references.gold_from_record(r) for r in parent]
    at_leaf = scoring.score_item(item, candidate, leaf_gold)
    at_parent = scoring.score_item(item, candidate, parent_gold, hierarchy_aliases(TAXONOMY, "parent"))
    assert at_leaf["counts"]["detection:topic"]["tp"] == 0
    assert at_parent["counts"]["detection:topic"]["tp"] == 1
    assert at_parent["counts"]["detection:narrative"]["tp"] == 1


def test_a_subtopic_verdict_still_applies_at_the_parent_level():
    item = make_item()
    refs = {item["item_id"]: {
        "a": {"result": labeled(item, "topic:vaccines.hep_b")},
        "b": {"result": {**labeled(item, "topic:vaccines.hep_b"), "detections": labeled(item, "topic:vaccines.hep_b")["detections"][1:]}},
    }}
    leaf, _ = references.aggregate([item], refs, {}, {})
    single = next(r for r in leaf if r["tier"] == "singleton" and r["axis"] == "topic")
    overlay = {(item["item_id"], single["members"][0]): {"tier": "rejected", "member": single["members"][0]}}
    parent, _ = references.aggregate([item], refs, {}, overlay, aliases=hierarchy_aliases(TAXONOMY, "parent"))
    topic = next(r for r in parent if r["axis"] == "topic")
    assert topic["label"] == "topic:vaccines" and topic["tier"] == "rejected"
    assert topic["members"] == single["members"]


def test_assemble_result_keeps_the_first_complete_answer_and_validates(tmp_path, monkeypatch, capsys):
    item = make_item()
    bundle = tmp_path / "bundle_001"
    (bundle / "windows").mkdir(parents=True)
    (bundle / "items.json").write_text(json.dumps([{"id": item["item_id"], "window_id": item["window_id"], "units": item["units"]}]))
    taxonomy_path = tmp_path / "taxonomy.json"
    tl.write_json(taxonomy_path, TAXONOMY)
    first = raw(item, "topic:vaccines.hep_b")
    first["detections"][0]["evidence_quote"] = "not in the window"
    (bundle / "windows" / f"{item['window_id']}.json").write_text(json.dumps(first))
    args = argparse.Namespace(bundle=bundle, taxonomy=taxonomy_path)
    assert cli.cmd_assemble_result(args) == 2
    assert "non_verbatim_quote" in capsys.readouterr().out
    fixed = raw(item, "topic:vaccines.hep_b")
    (bundle / "windows" / f"{item['window_id']}.json").write_text(json.dumps(fixed))
    assert cli.cmd_assemble_result(args) == 0
    first_answer = json.loads((bundle / "results.raw.json").read_text())
    final = json.loads((bundle / "results.json").read_text())
    assert first_answer[0]["detections"][0]["evidence_quote"] == "not in the window"
    assert final[0]["detections"][0]["evidence_quote"] == "hepatitis B shot at birth"


def test_explode_keeps_the_chosen_label_as_the_atom_identity():
    item = make_item()
    index = matching.WindowIndex(item)
    result = labeled(item, "topic:vaccines.hep_b")
    leaf = matching.explode(result, index)
    parent = matching.explode(result, index, hierarchy_aliases(TAXONOMY, "parent"))
    leaf_topic = next(a for a in leaf if a.axis == "topic")
    parent_topic = next(a for a in parent if a.axis == "topic")
    assert parent_topic.label == "topic:vaccines" and parent_topic.origin_label == "topic:vaccines.hep_b"
    assert parent_topic.member_key("x") == leaf_topic.member_key("x")


def test_benchmark_runs_use_the_v7_prompt_and_a_rubric_file_replaces_only_the_rubric(tmp_path):
    from analysis.benchmark import runner

    instructions, version, _ = runner.build_instructions(TAXONOMY, None)
    assert instructions == tl.taxonomy_instructions(TAXONOMY)
    assert version == tl.prompt_version(TAXONOMY)
    rubric = tmp_path / "rubric-x.md"
    rubric.write_text("# A different procedure\n")
    variant, variant_version, rubric_sha = runner.build_instructions(TAXONOMY, rubric)
    assert variant.startswith("# A different procedure")
    assert tl.DEFAULT_V7_CODEBOOK.read_text(encoding="utf-8").strip()[:200] in variant
    assert "topic:vaccines.hep_b" in variant
    assert variant_version.startswith("file:rubric-x.md:") and variant_version != version
    assert rubric_sha == tl.sha256_bytes(rubric.read_bytes())
