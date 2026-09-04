import argparse
import csv
import json
from pathlib import Path

from analysis import topic_labeling as labeling


ROOT = Path(__file__).resolve().parents[2]


def small_taxonomy():
    labels = [
        {
            "label_id": "topic:sleep",
            "kind": "topic",
            "axis": "topic",
            "name": "Sleep",
            "definition": "Sleep quality, duration and disorders.",
            "concepts": ["sleep", "circadian rhythm"],
        },
        {
            "label_id": "cross_cutting:scientific_study",
            "kind": "cross_cutting",
            "axis": "evidence",
            "name": "Scientific study",
            "definition": "A study or trial is invoked as support.",
            "concepts": ["study shows", "clinical trial"],
        },
    ]
    return {
        "schema_version": labeling.SCHEMA_VERSION,
        "source_path": "synthetic",
        "source_sha256": "0" * 64,
        "taxonomy_sha256": labeling.sha256_bytes(
            labeling.canonical_json(labels).encode("utf-8")
        ),
        "labels": labels,
    }


def test_compiles_only_canonical_topics_tables():
    taxonomy = labeling.compile_taxonomy(ROOT / "topics.md")
    assert len(taxonomy["labels"]) == 84
    assert {row["kind"] for row in taxonomy["labels"]} == {"topic", "cross_cutting"}
    assert {row["axis"] for row in taxonomy["labels"]} == {"topic", "frame", "evidence"}
    ids = {row["label_id"] for row in taxonomy["labels"]}
    assert "topic:vaccines_immunization" in ids
    assert "topic:sleep" in ids
    assert "topic:other_health_topic" in ids
    assert "cross_cutting:misinformation_correction_debunking" in ids
    assert len(ids) == len(taxonomy["labels"])
    assert all(row["definition"].strip() for row in taxonomy["labels"])


def test_axis_comes_from_the_table_not_from_the_label_name(tmp_path):
    """Renaming a row must not silently move it between axes."""
    source = tmp_path / "topics.md"
    source.write_text(
        "## GPT Enhanced Table:\n\n"
        "| Parent topic | Definition | Concepts |\n| :---- | :---- | :---- |\n"
        "| Sleep | Sleep and its disorders. | sleep; snoring |\n\n"
        "## GPT Derived Table 2 - Other Goals:\n\n"
        "| Cross-cutting label | Axis | Definition | Terms |\n"
        "| :---- | :---- | :---- | :---- |\n"
        "| Renamed study signal | evidence | A study is invoked. | study shows |\n"
        "| Toxin framing | frame | Toxins as a general cause. | toxins |\n",
        encoding="utf-8",
    )
    taxonomy = labeling.compile_taxonomy(source)
    axes = {row["name"]: row["axis"] for row in taxonomy["labels"]}
    assert axes == {
        "Sleep": "topic",
        "Renamed study signal": "evidence",
        "Toxin framing": "frame",
    }


def test_compile_rejects_an_unknown_cross_cutting_axis(tmp_path):
    source = tmp_path / "topics.md"
    source.write_text(
        "## GPT Enhanced Table:\n\n"
        "| Parent topic | Definition | Concepts |\n| :---- | :---- | :---- |\n"
        "| Sleep | Sleep and its disorders. | sleep |\n\n"
        "## GPT Derived Table 2 - Other Goals:\n\n"
        "| Cross-cutting label | Axis | Definition | Terms |\n"
        "| :---- | :---- | :---- | :---- |\n"
        "| Toxin framing | rhetoric | Toxins as a general cause. | toxins |\n",
        encoding="utf-8",
    )
    try:
        labeling.compile_taxonomy(source)
    except labeling.TopicLabelingError as exc:
        assert "expected one of" in str(exc)
    else:
        raise AssertionError("an unknown axis was accepted")


def test_sentence_units_retain_offsets_and_bound_runons():
    text = "First sentence. " + " ".join(f"word{i}" for i in range(11)) + "! Last one?"
    units = labeling.split_text_units(text, max_words=5)
    assert [unit.text for unit in units] == [
        "First sentence.",
        "word0 word1 word2 word3 word4",
        "word5 word6 word7 word8 word9",
        "word10!",
        "Last one?",
    ]
    assert all(text[unit.char_start : unit.char_end] == unit.text for unit in units)


def test_windows_reuse_global_units_for_overlap():
    units = [
        {
            "unit_id": f"u{index:06d}",
            "text": "one two three",
            "start_seconds": float(index),
            "end_seconds": float(index + 1),
            "timing_quality": "segment",
            "source_segment_index": index,
        }
        for index in range(1, 8)
    ]
    windows = list(labeling.make_windows(units, window_words=9, overlap_words=3))
    assert [[row["unit_id"] for row in window] for _, window in windows] == [
        ["u000001", "u000002", "u000003"],
        ["u000003", "u000004", "u000005"],
        ["u000005", "u000006", "u000007"],
    ]


def test_prepare_writes_fingerprinted_compressed_windows(tmp_path):
    transcript_dir = tmp_path / "transcripts"
    transcript_dir.mkdir()
    transcript_path = transcript_dir / "episode_7.jsonl.zst"
    labeling.write_jsonl_atomic(
        transcript_path,
        [
            {
                "type": "metadata",
                "episode_id": 7,
                "source": "asr",
                "model": "test-asr",
            },
            {"type": "summary", "language": "en"},
            {
                "type": "segment",
                "index": 0,
                "start": 0,
                "end": 60,
                "text": "Sleep matters. A new study shows a circadian effect.",
            },
        ],
    )
    output = tmp_path / "output"
    args = argparse.Namespace(
        output_dir=output,
        topics=ROOT / "topics.md",
        transcripts=transcript_dir,
        limit=None,
        manifest=None,
        metadata_db=None,
        max_unit_words=45,
        window_words=900,
        overlap_words=150,
    )
    manifest = labeling.run_prepare(args)
    windows = list(labeling.iter_jsonl(output / "windows.jsonl.zst"))
    assert manifest["episodes_prepared"] == 1
    assert manifest["windows"] == 1
    assert (
        labeling.sha256_file(output / "windows.jsonl.zst") == manifest["windows_sha256"]
    )
    assert windows[0]["episode_id"] == 7
    assert windows[0]["timing_quality"] == "interpolated"
    assert [unit["unit_id"] for unit in windows[0]["units"]] == ["u000001", "u000002"]


def test_responses_client_uses_strict_responses_schema_and_validates_quotes():
    taxonomy = small_taxonomy()
    window = {
        "window_id": "episode_1_window_0001",
        "units": [
            {"unit_id": "u000001", "text": "The guest discusses sleep."},
            {"unit_id": "u000002", "text": "A clinical trial was mentioned."},
        ],
    }
    model_result = {
        "results": [
            {
                "window_id": window["window_id"],
                "detections": [
                    {
                        "start_unit_id": "u000001",
                        "end_unit_id": "u000002",
                        "axis": "topic",
                        "label_ids": ["topic:sleep"],
                        "relevance": "substantive",
                        "discourse_role": "asserted_or_endorsed",
                        "confidence": 0.9,
                        "summary": "Sleep is discussed with a trial reference.",
                        "evidence_quote": "clinical trial was mentioned",
                    },
                    {
                        "start_unit_id": "u000002",
                        "end_unit_id": "u000002",
                        "axis": "evidence",
                        "label_ids": ["cross_cutting:scientific_study"],
                        "relevance": "substantive",
                        "discourse_role": "reported_or_quoted",
                        "confidence": 0.85,
                        "summary": "A clinical trial is invoked.",
                        "evidence_quote": "clinical trial",
                    },
                ],
                "verification_candidates": [],
                "product_mentions": [],
            }
        ]
    }

    class FakeClient(labeling.ResponsesClient):
        def _request(self, url, payload=None):
            self.seen_url = url
            self.seen_payload = payload
            return {
                "id": "resp_test",
                "status": "completed",
                "model": "local-model",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps(model_result)}
                        ],
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 40},
            }

    client = FakeClient("http://localhost:8000/v1", attempts=1)
    results, meta = client.classify(
        [window], taxonomy, "local-model", 1000, reasoning_effort=None, temperature=None
    )
    assert client.seen_url == "http://localhost:8000/v1/responses"
    assert client.seen_payload["text"]["format"]["type"] == "json_schema"
    assert client.seen_payload["text"]["format"]["strict"] is True
    assert client.seen_payload["input"][0]["content"][0]["type"] == "input_text"
    assert results[0]["detections"][0]["confidence"] == 0.9
    assert meta["response_id"] == "resp_test"


def test_response_validation_rejects_non_verbatim_evidence():
    taxonomy = small_taxonomy()
    window = {
        "window_id": "episode_1_window_0001",
        "units": [{"unit_id": "u000001", "text": "The guest discusses sleep."}],
    }
    result = {
        "window_id": window["window_id"],
        "detections": [
            {
                "start_unit_id": "u000001",
                "end_unit_id": "u000001",
                "axis": "topic",
                "label_ids": ["topic:sleep"],
                "relevance": "substantive",
                "discourse_role": "asserted_or_endorsed",
                "confidence": 0.7,
                "summary": "Sleep is discussed.",
                "evidence_quote": "a quote that is absent",
            }
        ],
        "verification_candidates": [],
        "product_mentions": [],
    }
    try:
        labeling.validate_window_result(
            result, window, {row["label_id"]: row["axis"] for row in taxonomy["labels"]}
        )
    except labeling.TopicLabelingError as exc:
        assert "not verbatim" in str(exc)
    else:
        raise AssertionError("non-verbatim evidence was accepted")


def _window_with(text):
    return {
        "window_id": "episode_1_window_0001",
        "units": [{"unit_id": "u000001", "text": text}],
    }


def _claim(**overrides):
    base = {
        "start_unit_id": "u000001",
        "end_unit_id": "u000001",
        "topic_ids": ["topic:sleep"],
        "frame_ids": [],
        "evidence_signal_ids": [],
        "discourse_role": "asserted_or_endorsed",
        "claim_type": "causal",
        "claim_text": "Magnesium probably improves deep sleep.",
        "expressed_certainty": "hedged",
        "certainty_markers": ["probably"],
        "evidence_quote": "magnesium probably improves deep sleep",
        "confidence": 0.8,
        "rationale": "Checkable treatment effect.",
    }
    return {**base, **overrides}


def _validate(result_fields):
    taxonomy = small_taxonomy()
    window = _window_with("I think magnesium probably improves deep sleep.")
    result = {
        "window_id": window["window_id"],
        "detections": [],
        "verification_candidates": [],
        "product_mentions": [],
        **result_fields,
    }
    return labeling.validate_window_result(
        result, window, {row["label_id"]: row["axis"] for row in taxonomy["labels"]}
    )


def _rejection_kind(result_fields):
    try:
        _validate(result_fields)
    except labeling.TopicLabelingError as exc:
        return exc.kind
    raise AssertionError("invalid result was accepted")


def test_expressed_certainty_must_be_grounded_in_verbatim_markers():
    accepted = _validate({"verification_candidates": [_claim()]})
    claim = accepted["verification_candidates"][0]
    assert claim["expressed_certainty"] == "hedged"
    assert claim["certainty_markers"] == ["probably"]
    # An unhedged claim carries no markers; a hedge the model cannot point to
    # is not a hedge; a marker must be verbatim inside the span.
    assert (
        _rejection_kind(
            {
                "verification_candidates": [
                    _claim(
                        expressed_certainty="unhedged", certainty_markers=["probably"]
                    )
                ]
            }
        )
        == "certainty_markers_mismatch"
    )
    assert (
        _rejection_kind({"verification_candidates": [_claim(certainty_markers=[])]})
        == "certainty_markers_mismatch"
    )
    assert (
        _rejection_kind(
            {"verification_candidates": [_claim(certainty_markers=["perhaps"])]}
        )
        == "non_verbatim_quote"
    )
    assert (
        _rejection_kind(
            {"verification_candidates": [_claim(expressed_certainty="certain")]}
        )
        == "invalid_field"
    )
    unhedged = _claim(expressed_certainty="unhedged", certainty_markers=[])
    assert (
        _validate({"verification_candidates": [unhedged]})["verification_candidates"][
            0
        ]["certainty_markers"]
        == []
    )


def test_product_mentions_are_validated_like_other_annotations():
    mention = {
        "start_unit_id": "u000001",
        "end_unit_id": "u000001",
        "product_name": "Magnesium Breakthrough",
        "product_type": "supplement",
        "mention_role": "advertised",
        "evidence_quote": "magnesium probably",
        "confidence": 0.9,
    }
    accepted = _validate({"product_mentions": [mention]})
    assert accepted["product_mentions"][0]["product_name"] == "Magnesium Breakthrough"
    assert (
        _rejection_kind(
            {
                "product_mentions": [
                    {**mention, "evidence_quote": "Magnesium Breakthrough"}
                ]
            }
        )
        == "non_verbatim_quote"
    )
    assert (
        _rejection_kind({"product_mentions": [{**mention, "product_type": "gadget"}]})
        == "invalid_field"
    )
    assert (
        _rejection_kind({"product_mentions": [{**mention, "product_name": "  "}]})
        == "invalid_field"
    )
    assert (
        _rejection_kind(
            {
                "product_mentions": [
                    mention,
                    {**mention, "product_name": "magnesium-breakthrough"},
                ]
            }
        )
        == "duplicate_annotation"
    )
    missing_field = {
        key: value for key, value in mention.items() if key != "mention_role"
    }
    assert _rejection_kind({"product_mentions": [missing_field]}) == "schema_shape"


def test_product_mentions_merge_only_when_spans_touch_and_names_match():
    def mention(start, end, name, confidence, window_id):
        return {
            "start_order": start,
            "end_order": end,
            "product_name": name,
            "product_type": "supplement",
            "mention_role": "advertised",
            "evidence_quote": name,
            "confidence": confidence,
            "window_id": window_id,
        }

    groups = labeling.merge_product_mentions(
        [
            mention(2, 3, "AG-1", 0.7, "w1"),
            mention(3, 4, "ag1", 0.9, "w2"),
            mention(3, 3, "LMNT", 0.8, "w2"),
            mention(20, 20, "AG1", 0.9, "w3"),
        ]
    )
    assert [
        (group["product_key"], group["start_order"], group["end_order"])
        for group in groups
    ] == [
        ("ag1", 2, 4),
        ("lmnt", 3, 3),
        ("ag1", 20, 20),
    ]
    assert groups[0]["best"]["product_name"] == "ag1"
    assert len(groups[0]["mentions"]) == 2


def test_overlap_detections_merge_and_keep_label_union():
    candidates = [
        {
            "start_order": 2,
            "end_order": 4,
            "start_unit_id": "u000002",
            "end_unit_id": "u000004",
            "axis": "topic",
            "label_ids": ["topic:sleep"],
            "discourse_role": "asserted_or_endorsed",
            "confidence": 0.8,
            "relevance": "substantive",
            "summary": "one",
            "evidence_quote": "one",
            "window_id": "w1",
        },
        {
            "start_order": 3,
            "end_order": 5,
            "start_unit_id": "u000003",
            "end_unit_id": "u000005",
            "axis": "topic",
            "label_ids": ["topic:sleep"],
            "discourse_role": "asserted_or_endorsed",
            "confidence": 0.9,
            "relevance": "substantive",
            "summary": "two",
            "evidence_quote": "two",
            "window_id": "w2",
        },
    ]
    groups = labeling.merge_detection_candidates(candidates)
    assert len(groups) == 1
    assert (groups[0]["start_order"], groups[0]["end_order"]) == (2, 5)
    assert groups[0]["label_ids"] == {"topic:sleep"}


def test_merge_emits_one_clip_for_duplicate_window_detections(tmp_path):
    taxonomy = small_taxonomy()
    taxonomy_path = tmp_path / "taxonomy.json"
    labeling.write_json(taxonomy_path, taxonomy)
    common = {
        "schema_version": labeling.SCHEMA_VERSION,
        "episode_id": 1,
        "podcast_id": 2,
        "podcast_title": "Test show",
        "episode_title": "Test episode",
        "published_date": "2026-01-01",
        "source_transcript": "episode_1.jsonl.zst",
        "source_transcript_sha256": "a" * 64,
    }
    units = [
        {
            "unit_id": f"u{index:06d}",
            "text": text,
            "start_seconds": float(index * 10),
            "end_seconds": float(index * 10 + 9),
            "timing_quality": "segment",
            "source_segment_index": index,
        }
        for index, text in enumerate(
            [
                "Intro only.",
                "Sleep is important, and the Oura ring tracks it.",
                "A clinical trial proves everyone needs exactly eight hours of sleep.",
                "Outro.",
            ],
            1,
        )
    ]
    windows = [
        {
            **common,
            "window_id": "episode_1_window_0001",
            "window_index": 1,
            "units": units[:3],
        },
        {
            **common,
            "window_id": "episode_1_window_0002",
            "window_index": 2,
            "units": units[1:],
        },
    ]
    windows_path = tmp_path / "windows.jsonl.zst"
    labeling.write_jsonl_atomic(windows_path, windows)
    run_manifest = {
        "run_fingerprint": "b" * 64,
        "model": "local-model",
        "taxonomy_sha256": taxonomy["taxonomy_sha256"],
    }
    store = labeling.LabelStore(tmp_path / "labels.sqlite", run_manifest)
    store.record_success(
        windows,
        [
            {
                "window_id": windows[0]["window_id"],
                "detections": [
                    {
                        "start_unit_id": "u000002",
                        "end_unit_id": "u000003",
                        "axis": "topic",
                        "label_ids": ["topic:sleep"],
                        "relevance": "substantive",
                        "discourse_role": "asserted_or_endorsed",
                        "confidence": 0.8,
                        "summary": "Sleep and research are discussed.",
                        "evidence_quote": "Sleep is important",
                    }
                ],
                "verification_candidates": [
                    {
                        "start_unit_id": "u000003",
                        "end_unit_id": "u000003",
                        "topic_ids": ["topic:sleep"],
                        "frame_ids": [],
                        "evidence_signal_ids": ["cross_cutting:scientific_study"],
                        "discourse_role": "asserted_or_endorsed",
                        "claim_type": "risk_or_safety",
                        "claim_text": "Every person needs exactly eight hours of sleep.",
                        "expressed_certainty": "absolute",
                        "certainty_markers": ["everyone", "exactly"],
                        "evidence_quote": "everyone needs exactly eight hours of sleep",
                        "confidence": 0.8,
                        "rationale": "The universal sleep-duration claim is externally checkable.",
                    }
                ],
                "product_mentions": [
                    {
                        "start_unit_id": "u000002",
                        "end_unit_id": "u000002",
                        "product_name": "Oura Ring",
                        "product_type": "device_or_wearable",
                        "mention_role": "recommended",
                        "evidence_quote": "Oura ring tracks it",
                        "confidence": 0.9,
                    }
                ],
            },
            {
                "window_id": windows[1]["window_id"],
                "detections": [
                    {
                        "start_unit_id": "u000002",
                        "end_unit_id": "u000003",
                        "axis": "topic",
                        "label_ids": ["topic:sleep"],
                        "relevance": "substantive",
                        "discourse_role": "asserted_or_endorsed",
                        "confidence": 0.9,
                        "summary": "Sleep is linked to a trial.",
                        "evidence_quote": "clinical trial proves",
                    },
                    {
                        "start_unit_id": "u000003",
                        "end_unit_id": "u000003",
                        "axis": "evidence",
                        "label_ids": ["cross_cutting:scientific_study"],
                        "relevance": "substantive",
                        "discourse_role": "asserted_or_endorsed",
                        "confidence": 0.9,
                        "summary": "A clinical trial is invoked.",
                        "evidence_quote": "clinical trial",
                    },
                ],
                "verification_candidates": [
                    {
                        "start_unit_id": "u000003",
                        "end_unit_id": "u000003",
                        "topic_ids": ["topic:sleep"],
                        "frame_ids": [],
                        "evidence_signal_ids": ["cross_cutting:scientific_study"],
                        "discourse_role": "asserted_or_endorsed",
                        "claim_type": "risk_or_safety",
                        "claim_text": "Everyone requires exactly eight hours of sleep.",
                        "expressed_certainty": "absolute",
                        "certainty_markers": ["everyone"],
                        "evidence_quote": "everyone needs exactly eight hours of sleep",
                        "confidence": 0.9,
                        "rationale": "This universal sleep claim can be checked.",
                    }
                ],
                "product_mentions": [
                    {
                        "start_unit_id": "u000002",
                        "end_unit_id": "u000002",
                        "product_name": "oura-ring",
                        "product_type": "device_or_wearable",
                        "mention_role": "neutral",
                        "evidence_quote": "the Oura ring",
                        "confidence": 0.7,
                    }
                ],
            },
        ],
        {"response_id": "resp", "response_model": "local-model", "usage": None},
    )
    store.close()
    label_manifest_path = tmp_path / "label_manifest.json"
    labeling.write_json(label_manifest_path, run_manifest)
    summary = labeling.run_merge(
        argparse.Namespace(
            output_dir=tmp_path,
            taxonomy=taxonomy_path,
            windows=windows_path,
            label_manifest=label_manifest_path,
            allow_incomplete=False,
        )
    )
    clips = list(labeling.iter_jsonl(tmp_path / "clips.jsonl"))
    claims = list(labeling.iter_jsonl(tmp_path / "verification_candidates.jsonl"))
    products = list(labeling.iter_jsonl(tmp_path / "product_mentions.jsonl"))
    assert summary["complete"] is True
    assert summary["topic_clips"] == 1
    assert summary["label_annotations"] == 2
    assert summary["verification_candidates"] == 1
    assert summary["product_mentions"] == 1
    # The two spellings merge into one mention; the higher-confidence name wins.
    assert products[0]["product_name"] == "Oura Ring"
    assert products[0]["product_key"] == "ouraring"
    assert products[0]["mention_role"] == "recommended"
    assert products[0]["mention_roles"] == ["neutral", "recommended"]
    assert products[0]["supporting_extraction_count"] == 2
    assert clips[0]["mentions_specific_product"] is True
    assert clips[0]["product_mention_ids"] == [products[0]["mention_id"]]
    assert clips[0]["product_names"] == ["Oura Ring"]
    assert clips[0]["claim_certainty_counts"]["absolute"] == 1
    assert claims[0]["expressed_certainty"] == "absolute"
    assert claims[0]["certainty_markers"] == ["everyone"]
    # The product is named one unit before the claim, inside its context window.
    assert claims[0]["mentions_specific_product"] is True
    assert claims[0]["product_names"] == ["Oura Ring"]
    assert {row["label_id"] for row in clips[0]["topics"]} == {"topic:sleep"}
    assert clips[0]["possible_misinformation"] is True
    assert clips[0]["supporting_window_ids"] == [
        "episode_1_window_0001",
        "episode_1_window_0002",
    ]
    assert claims[0]["context_start_unit_id"] == "u000001"
    assert claims[0]["context_end_unit_id"] == "u000004"
    assert claims[0]["context_text"].startswith("Intro only.")
    sample_summary = labeling.run_sample(
        argparse.Namespace(
            output_dir=tmp_path,
            taxonomy=taxonomy_path,
            windows=windows_path,
            annotations=tmp_path / "label_annotations.jsonl",
            candidates=tmp_path / "verification_candidates.jsonl",
            product_mentions=tmp_path / "product_mentions.jsonl",
            label_manifest=label_manifest_path,
            per_label=1,
            per_claim_type=5,
            per_product_type=5,
            random_windows=1,
            seed=123,
        )
    )
    assert sample_summary["sample_units"] == 3
    assert sample_summary["claim_sample"]["sampled"] == 1
    assert sample_summary["product_sample"]["sampled"] == 1
    product_rows = list(
        csv.DictReader((tmp_path / "product_sample_blinded.csv").open())
    )
    product_key_rows = list(
        csv.DictReader((tmp_path / "product_sample_key.csv").open())
    )
    assert product_rows[0]["product_name"] == "Oura Ring"
    assert "model_product_type" not in product_rows[0]
    assert product_key_rows[0]["model_product_type"] == "device_or_wearable"
    claim_rows = list(csv.DictReader((tmp_path / "claim_sample_blinded.csv").open()))
    claim_key_rows = list(csv.DictReader((tmp_path / "claim_sample_key.csv").open()))
    assert claim_rows[0]["claim_text"] and claim_rows[0]["evidence_quote"]
    assert claim_rows[0]["human_claim_faithful_to_quote"] == ""
    assert "claim_type" not in claim_rows[0]
    assert "expressed_certainty" not in claim_rows[0]
    assert claim_rows[0]["human_expressed_certainty"] == ""
    assert claim_key_rows[0]["claim_type"] == "risk_or_safety"
    assert claim_key_rows[0]["model_expressed_certainty"] == "absolute"

    episodes = list(labeling.iter_jsonl(tmp_path / "episodes.jsonl"))
    assert episodes[0]["window_count"] == 2
    assert episodes[0]["labeled_window_count"] == 2
    assert episodes[0]["unresolved_window_count"] == 0
    assert episodes[0]["unit_count"] == 4
    assert episodes[0]["word_count"] == sum(len(unit["text"].split()) for unit in units)
    assert episodes[0]["distinct_claim_key_count"] == 1
    assert episodes[0]["product_mention_count"] == 1
    assert episodes[0]["distinct_product_key_count"] == 1
    assert episodes[0]["claim_certainty_counts"] == {
        "absolute": 1,
        "unhedged": 0,
        "hedged": 0,
        "speculative": 0,
    }
    assert claims[0]["claim_key"] and claims[0]["quote_key"]
    assert claims[0]["supporting_extraction_count"] == 2
    blind_rows = list(
        csv.DictReader((tmp_path / "validation_sample_blinded.csv").open())
    )
    key_rows = list(csv.DictReader((tmp_path / "validation_sample_key.csv").open()))
    assert len(blind_rows) == len(key_rows) == 3
    assert all("model_label_ids" not in row for row in blind_rows)


def test_one_bad_window_does_not_fail_its_whole_batch(tmp_path, monkeypatch):
    """A batch that fails as a whole is retried window by window."""
    taxonomy = small_taxonomy()
    taxonomy_path = tmp_path / "taxonomy.json"
    labeling.write_json(taxonomy_path, taxonomy)
    windows = [
        {
            "window_id": f"episode_1_window_{index:04d}",
            "episode_id": 1,
            "window_index": index,
            "units": [{"unit_id": "u000001", "text": "The guest discusses sleep."}],
        }
        for index in (1, 2, 3)
    ]
    windows_path = tmp_path / "windows.jsonl.zst"
    _, windows_sha256 = labeling.write_jsonl_atomic(windows_path, windows)
    prepare_manifest_path = tmp_path / "prepare_manifest.json"
    labeling.write_json(
        prepare_manifest_path,
        {
            "windows_sha256": windows_sha256,
            "taxonomy_sha256": taxonomy["taxonomy_sha256"],
        },
    )

    poison = "episode_1_window_0002"
    calls: list[list[str]] = []

    def fake_classify(self, batch, taxonomy_arg, model, *rest):
        ids = [window["window_id"] for window in batch]
        calls.append(ids)
        if poison in ids:
            raise labeling.TopicLabelingError(
                "evidence quote is not verbatim", kind="non_verbatim_quote"
            )
        results = [
            {
                "window_id": window_id,
                "detections": [],
                "verification_candidates": [],
                "product_mentions": [],
            }
            for window_id in ids
        ]
        return results, {"response_id": "r", "response_model": model, "usage": None}

    monkeypatch.setattr(labeling.ResponsesClient, "classify", fake_classify)
    summary = labeling.run_label(
        argparse.Namespace(
            output_dir=tmp_path,
            taxonomy=taxonomy_path,
            windows=windows_path,
            prepare_manifest=prepare_manifest_path,
            api_base="http://127.0.0.1:8000/v1",
            model="local-model",
            api_key_env=None,
            batch_size=3,
            concurrency=1,
            max_output_tokens=100,
            timeout=10,
            attempts=1,
            reasoning_effort=None,
            temperature=None,
        )
    )
    # First the whole batch, then each window alone.
    assert calls[0] == [window["window_id"] for window in windows]
    assert sorted(calls[1:]) == [[window["window_id"]] for window in windows]
    assert summary["windows_labeled"] == 2
    assert summary["unresolved_windows"] == 1
    assert summary["unresolved_windows_by_kind"] == {"non_verbatim_quote": 1}
    assert summary["batches_isolated_this_invocation"] == 1
    assert summary["windows_recovered_by_isolation"] == 2


def test_verify_uses_only_validated_evidence_packets_and_checkpoints_results(
    tmp_path, monkeypatch
):
    candidate = {
        "schema_version": labeling.SCHEMA_VERSION,
        "candidate_id": "episode_1_claim_0001",
        "claim_text": "Every person needs exactly eight hours of sleep.",
        "evidence_quote": "everyone needs exactly eight hours of sleep",
        "context_text": "A guest says everyone needs exactly eight hours of sleep.",
        "discourse_role": "asserted_or_endorsed",
        "claim_type": "risk_or_safety",
        "expressed_certainty": "absolute",
        "certainty_markers": ["everyone", "exactly"],
        "topic_ids": ["topic:sleep"],
        "frame_ids": [],
        "evidence_signal_ids": ["cross_cutting:scientific_study"],
        "possible_misinformation": True,
        "verification_status": "unverified",
    }
    corpus_validation_manifest = {
        "schema_version": labeling.EVIDENCE_CORPUS_MANIFEST_VERSION,
        "corpus_id": "validated-health-corpus",
        "corpus_version": "2026-08-30",
        "corpus_sha256": "1" * 64,
        "validation_status": "validated",
        "validated_at": "2026-08-30T12:00:00+00:00",
        "validator": "corpus-review-team",
        "validation_method": "Source policy and document-level review.",
        "document_count": 100,
    }
    corpus_validation_path = tmp_path / "evidence_corpus_validation_manifest.json"
    labeling.write_json(corpus_validation_path, corpus_validation_manifest)
    packet = {
        "candidate_id": candidate["candidate_id"],
        "corpus": {
            "corpus_id": "validated-health-corpus",
            "corpus_version": "2026-08-30",
            "corpus_sha256": "1" * 64,
            "validation_manifest_sha256": labeling.sha256_file(corpus_validation_path),
        },
        "retrieval": {
            "method": "hybrid-bm25-embedding",
            "retriever_version": "retriever-v1",
            "query": candidate["claim_text"],
            "top_k": 3,
        },
        "passages": [
            {
                "passage_id": "sleep-guideline:p12",
                "document_id": "sleep-guideline",
                "title": "Sleep duration guideline",
                "source": "Validated source",
                "published_date": "2025-01-01",
                "locator": "page 12",
                "text": "Sleep needs vary by age and individual circumstances.",
            }
        ],
    }
    labeling.validate_evidence_packet(packet)
    candidates_path = tmp_path / "verification_candidates.jsonl"
    packets_path = tmp_path / "evidence_packets.jsonl.zst"
    labeling.write_jsonl_atomic(candidates_path, [candidate])
    labeling.write_jsonl_atomic(packets_path, [packet])

    class FakeVerificationClient:
        def __init__(self, api_base, api_key, timeout, attempts):
            assert api_key is None

        def verify(
            self,
            pairs,
            model,
            max_output_tokens,
            reasoning_effort,
            temperature,
        ):
            assert pairs == [{"candidate": candidate, "evidence_packet": packet}]
            assert model == "local-model"
            return [
                {
                    "candidate_id": candidate["candidate_id"],
                    "verdict": "contradicted",
                    "confidence": 0.91,
                    "supporting_passage_ids": [],
                    "contradicting_passage_ids": ["sleep-guideline:p12"],
                    "rationale": "The evidence says sleep needs vary.",
                    "limitations": "One retrieved guideline passage.",
                }
            ], {
                "response_id": "resp_verify",
                "response_model": "local-model",
                "usage": {"input_tokens": 200, "output_tokens": 50},
            }

    monkeypatch.setattr(labeling, "ResponsesClient", FakeVerificationClient)
    output_dir = tmp_path / "verification"
    summary = labeling.run_verify(
        argparse.Namespace(
            candidates=candidates_path,
            evidence_packets=packets_path,
            corpus_validation_manifest=corpus_validation_path,
            output_dir=output_dir,
            api_base="http://localhost:8000/v1",
            model="local-model",
            api_key_env=None,
            batch_size=4,
            concurrency=1,
            max_output_tokens=6000,
            timeout=60,
            attempts=1,
            reasoning_effort=None,
            temperature=None,
        )
    )
    results = list(labeling.iter_jsonl(output_dir / "verification_results.jsonl.zst"))
    assert summary["candidates_verified"] == 1
    assert summary["unresolved_candidates"] == 0
    assert results[0]["verdict"] == "contradicted"
    assert results[0]["contradicting_passage_ids"] == ["sleep-guideline:p12"]
    assert results[0]["response_id"] == "resp_verify"


def test_verification_rejects_citations_outside_the_candidate_packet():
    pair = {
        "candidate": {"candidate_id": "candidate-1"},
        "evidence_packet": {"passages": [{"passage_id": "allowed-passage"}]},
    }
    parsed = {
        "results": [
            {
                "candidate_id": "candidate-1",
                "verdict": "supported",
                "confidence": 0.8,
                "supporting_passage_ids": ["invented-passage"],
                "contradicting_passage_ids": [],
                "rationale": "The evidence supports the claim.",
                "limitations": "",
            }
        ]
    }
    try:
        labeling.validate_verification_response(parsed, [pair])
    except labeling.TopicLabelingError as exc:
        assert "invalid passage citations" in str(exc)
    else:
        raise AssertionError("a citation outside the evidence packet was accepted")
