import argparse
import csv
import json
from pathlib import Path

import pytest

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
        "window_id": window["window_id"],
        "detections": [
            {
                "start_unit_id": "u000001",
                "end_unit_id": "u000002",
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
    result, meta = client.classify(
        window,
        taxonomy,
        "local-model",
        labeling.ModelSettings(max_output_tokens=1000, reasoning_effort="none"),
    )
    assert client.seen_url == "http://localhost:8000/v1/responses"
    assert client.seen_payload["text"]["format"]["type"] == "json_schema"
    assert client.seen_payload["text"]["format"]["strict"] is True
    assert client.seen_payload["input"][0]["content"][0]["type"] == "input_text"
    assert client.seen_payload["max_output_tokens"] == 1000
    # Always explicit: on a thinking model an absent effort means "think".
    assert client.seen_payload["reasoning"] == {"effort": "none"}
    assert "include_reasoning" not in client.seen_payload
    # One window per request: the user message is that window's record, and
    # the schema is its result object with no array around it.
    user_text = client.seen_payload["input"][0]["content"][0]["text"]
    assert user_text == labeling.window_input(window)
    assert user_text.startswith("Label this window:\n")
    assert json.loads(user_text.split("\n", 1)[1]) == window
    schema = client.seen_payload["text"]["format"]["schema"]
    assert schema == labeling.response_schema(taxonomy)
    assert "results" not in schema["properties"]
    assert set(schema["required"]) == {
        "window_id",
        "detections",
        "verification_candidates",
        "product_mentions",
    }
    assert result["window_id"] == window["window_id"]
    assert result["detections"][0]["confidence"] == 0.9
    assert meta["response_id"] == "resp_test"


def write_config(tmp_path):
    config = tmp_path / "topic-labeling.toml"
    config.write_text(
        "\n".join(
            [
                "[model]",
                'api_base = "http://127.0.0.1:8000/v1"',
                'api = "chat_completions"',
                'model = "deepseek-ai/DeepSeek-V4-Flash-0731"',
                'reasoning_effort = "high"',
                "top_p = 0.95",
                "",
                "[label]",
                "concurrency = 3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return config


def test_config_supplies_shared_model_settings_to_label_and_verify(tmp_path):
    config = write_config(tmp_path)
    parser = labeling.build_parser()

    label = parser.parse_args(
        labeling.expand_config_args(["label", "--config", str(config)])
    )
    assert label.model == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert label.reasoning_effort == "high"
    assert label.api == "chat_completions"
    assert label.top_p == 0.95
    assert label.concurrency == 3

    verify = parser.parse_args(
        labeling.expand_config_args(["verify", "--config", str(config)])
    )
    assert verify.model == "deepseek-ai/DeepSeek-V4-Flash-0731"
    # [model] reaches both commands, so the API cannot drift between them.
    assert verify.api == "chat_completions"
    assert verify.top_p == 0.95
    # [label] is not [verify]: its concurrency must not leak across.
    assert verify.concurrency == 8

    # A command that takes no model settings is left alone.
    assert labeling.expand_config_args(["prepare", "--config", str(config)]) == [
        "prepare",
        "--config",
        str(config),
    ]


def test_typed_flags_override_the_config(tmp_path):
    config = write_config(tmp_path)
    args = labeling.build_parser().parse_args(
        labeling.expand_config_args(
            ["label", "--config", str(config), "--reasoning-effort", "none"]
        )
    )
    assert args.reasoning_effort == "none"
    assert args.model == "deepseek-ai/DeepSeek-V4-Flash-0731"


def test_config_fails_loudly_on_bad_input(tmp_path):
    missing = tmp_path / "absent.toml"
    with pytest.raises(labeling.TopicLabelingError, match="does not exist"):
        labeling.expand_config_args(["label", "--config", str(missing)])

    unknown = tmp_path / "unknown.toml"
    unknown.write_text("[labl]\nconcurrency = 2\n", encoding="utf-8")
    with pytest.raises(labeling.TopicLabelingError, match="unknown table"):
        labeling.expand_config_args(["label", "--config", str(unknown)])

    loose = tmp_path / "loose.toml"
    loose.write_text('model = "x"\n', encoding="utf-8")
    with pytest.raises(labeling.TopicLabelingError, match="inside a table"):
        labeling.expand_config_args(["label", "--config", str(loose)])

    # An unusable setting is an unrecognized flag, reported by argparse itself.
    stray = tmp_path / "stray.toml"
    stray.write_text("[label]\nnot_a_flag = 1\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        labeling.build_parser().parse_args(
            labeling.expand_config_args(["label", "--config", str(stray)])
        )


def env_args(name="FIREWORKS_API_KEY", env_file=None):
    return argparse.Namespace(api_key_env=name, env_file=env_file)


def test_no_api_key_env_means_no_auth_header():
    assert labeling.resolve_api_key(env_args(name=None)) is None


def test_env_file_supplies_the_key(tmp_path, monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        '# a comment\n\nexport OTHER=ignored\nFIREWORKS_API_KEY = "fw-secret"\n',
        encoding="utf-8",
    )
    assert labeling.resolve_api_key(env_args(env_file=env_file)) == "fw-secret"


def test_environment_wins_over_the_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("FIREWORKS_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("FIREWORKS_API_KEY", "from-environment")
    assert labeling.resolve_api_key(env_args(env_file=env_file)) == "from-environment"


def test_default_env_file_is_found_in_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / labeling.DEFAULT_ENV_FILE).write_text(
        "FIREWORKS_API_KEY=fw-default\n", encoding="utf-8"
    )
    assert labeling.resolve_api_key(env_args()) == "fw-default"

    (tmp_path / labeling.DEFAULT_ENV_FILE).unlink()
    with pytest.raises(labeling.TopicLabelingError, match="there is no .env"):
        labeling.resolve_api_key(env_args())


def test_missing_key_is_an_error_before_the_run_starts(tmp_path, monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    absent = tmp_path / "absent.env"
    with pytest.raises(labeling.TopicLabelingError, match="does not exist"):
        labeling.resolve_api_key(env_args(env_file=absent))

    silent = tmp_path / ".env"
    silent.write_text("SOMETHING_ELSE=x\n", encoding="utf-8")
    with pytest.raises(labeling.TopicLabelingError, match="does not set it either"):
        labeling.resolve_api_key(env_args(env_file=silent))


def test_env_file_values_are_taken_literally(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("HASH_KEY=sk-abc#def\nPADDED=' spaced '\n", encoding="utf-8")
    values = labeling.load_env_file(env_file)
    # An unquoted '#' belongs to the secret; quotes preserve whitespace.
    assert values == {"HASH_KEY": "sk-abc#def", "PADDED": " spaced "}


def test_env_file_fails_loudly_on_bad_input(tmp_path):
    malformed = tmp_path / "malformed.env"
    malformed.write_text("FIREWORKS_API_KEY\n", encoding="utf-8")
    with pytest.raises(labeling.TopicLabelingError, match="expected KEY=value"):
        labeling.load_env_file(malformed)

    repeated = tmp_path / "repeated.env"
    repeated.write_text("K=one\nK=two\n", encoding="utf-8")
    with pytest.raises(labeling.TopicLabelingError, match="set twice"):
        labeling.load_env_file(repeated)


def test_env_file_is_configurable_and_reaches_label_and_verify(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(
        '[model]\napi_key_env = "FIREWORKS_API_KEY"\nenv_file = "secrets/.env"\n',
        encoding="utf-8",
    )
    parser = labeling.build_parser()
    for command in ("label", "verify"):
        args = parser.parse_args(
            labeling.expand_config_args([command, "--config", str(config)])
        )
        assert args.api_key_env == "FIREWORKS_API_KEY"
        assert args.env_file == Path("secrets/.env")


def test_thinking_settings_reach_the_payload_and_reasoning_output_is_ignored():
    taxonomy = small_taxonomy()
    window = {
        "window_id": "episode_1_window_0001",
        "units": [{"unit_id": "u000001", "text": "The guest discusses sleep."}],
    }
    model_result = {
        "window_id": window["window_id"],
        "detections": [],
        "verification_candidates": [],
        "product_mentions": [],
    }

    class FakeClient(labeling.ResponsesClient):
        def _request(self, url, payload=None):
            self.seen_payload = payload
            return {
                "id": "resp_test",
                "status": "completed",
                "model": "local-model",
                "output": [
                    # A thinking model emits its reasoning as its own item; the
                    # JSON contract lives only in the message that follows.
                    {
                        "type": "reasoning",
                        "content": [
                            {"type": "reasoning_text", "text": "not the answer"}
                        ],
                    },
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps(model_result)}
                        ],
                    },
                ],
            }

    client = FakeClient("http://localhost:8000/v1", attempts=1)
    settings = labeling.ModelSettings(
        max_output_tokens=200000,
        reasoning_effort="max",
        temperature=1.0,
        top_p=0.95,
        seed=7,
    )
    result, _ = client.classify(window, taxonomy, "local-model", settings)
    assert client.seen_payload["reasoning"] == {"effort": "max"}
    assert client.seen_payload["include_reasoning"] is False
    assert client.seen_payload["temperature"] == 1.0
    assert client.seen_payload["top_p"] == 0.95
    assert client.seen_payload["seed"] == 7
    assert settings.fingerprint()["reasoning_effort"] == "max"
    assert result["window_id"] == window["window_id"]


def test_chat_completions_flavor_sends_the_same_request_in_chat_shape():
    taxonomy = small_taxonomy()
    window = {
        "window_id": "episode_1_window_0001",
        "units": [
            {"unit_id": "u000001", "text": "The guest discusses sleep."},
            {"unit_id": "u000002", "text": "A clinical trial was mentioned."},
        ],
    }
    model_result = {
        "window_id": window["window_id"],
        "detections": [
            {
                "start_unit_id": "u000001",
                "end_unit_id": "u000002",
                "label_ids": ["topic:sleep"],
                "relevance": "substantive",
                "discourse_role": "asserted_or_endorsed",
                "confidence": 0.9,
                "summary": "Sleep is discussed with a trial reference.",
                "evidence_quote": "clinical trial was mentioned",
            }
        ],
        "verification_candidates": [],
        "product_mentions": [],
    }

    class FakeClient(labeling.ResponsesClient):
        def _request(self, url, payload=None):
            self.seen_url = url
            self.seen_payload = payload
            return {
                "id": "chatcmpl_test",
                "model": "local-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            # vLLM returns the thinking beside the content; the
                            # JSON contract lives only in the content.
                            "reasoning_content": "not the answer",
                            "content": json.dumps(model_result),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 40},
            }

    client = FakeClient("http://localhost:8000/v1", attempts=1, api="chat_completions")
    result, meta = client.classify(
        window,
        taxonomy,
        "local-model",
        labeling.ModelSettings(
            max_output_tokens=1000, reasoning_effort="high", top_p=0.95
        ),
    )
    assert client.seen_url == "http://localhost:8000/v1/chat/completions"
    payload = client.seen_payload
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert "window_id" in payload["messages"][1]["content"]
    assert payload["response_format"]["type"] == "json_schema"
    json_schema = payload["response_format"]["json_schema"]
    assert json_schema["strict"] is True
    assert json_schema["schema"] == labeling.response_schema(taxonomy)
    # The chat spellings, not the Responses ones.
    assert payload["max_tokens"] == 1000
    assert payload["reasoning_effort"] == "high"
    assert payload["top_p"] == 0.95
    assert "max_output_tokens" not in payload
    assert "reasoning" not in payload
    assert "include_reasoning" not in payload
    assert payload["messages"][1]["content"] == labeling.window_input(window)
    assert result["detections"][0]["confidence"] == 0.9
    assert meta["response_id"] == "chatcmpl_test"
    # Chat Completions echoes no decoding settings, so there is nothing to read
    # back -- a run on this flavor has to pin them to know what produced it.
    assert meta["effective_sampling"] == {}


def test_verify_builds_its_own_request_on_either_api():
    """`verify` has its own rubric and schema, so it needs its own shape check.

    The run_verify test below stubs the whole client, so nothing else exercises
    the verification payload -- and a break would only show on one flavor.
    """
    candidate = {
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
    }
    packet = {
        "candidate_id": candidate["candidate_id"],
        "corpus": {"corpus_id": "validated-health-corpus"},
        "retrieval": {"method": "hybrid-bm25-embedding"},
        "passages": [
            {
                "passage_id": "sleep-guideline:p12",
                "text": "Sleep needs vary by age and individual circumstances.",
            }
        ],
    }
    model_result = {
        "candidate_id": candidate["candidate_id"],
        "verdict": "contradicted",
        "confidence": 0.91,
        "supporting_passage_ids": [],
        "contradicting_passage_ids": ["sleep-guideline:p12"],
        "rationale": "The evidence says sleep needs vary.",
        "limitations": "One retrieved guideline passage.",
    }
    bodies = {
        "responses": {
            "id": "resp_verify",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps(model_result)}
                    ],
                }
            ],
        },
        "chat_completions": {
            "id": "chatcmpl_verify",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": json.dumps(model_result)},
                }
            ],
        },
    }

    class FakeClient(labeling.ResponsesClient):
        def _request(self, url, payload=None):
            self.seen_url = url
            self.seen_payload = payload
            return bodies[self.flavor.name]

    for api, route, schema_at, rubric_at, input_at in (
        (
            "responses",
            "/responses",
            lambda p: p["text"]["format"],
            lambda p: p["instructions"],
            lambda p: p["input"][0]["content"][0]["text"],
        ),
        (
            "chat_completions",
            "/chat/completions",
            lambda p: p["response_format"]["json_schema"],
            lambda p: p["messages"][0]["content"],
            lambda p: p["messages"][1]["content"],
        ),
    ):
        client = FakeClient("http://localhost:8000/v1", attempts=1, api=api)
        result, meta = client.verify(
            {"candidate": candidate, "evidence_packet": packet},
            "local-model",
            labeling.ModelSettings(max_output_tokens=6000, reasoning_effort="none"),
        )
        assert client.seen_url == "http://localhost:8000/v1" + route
        # The verification schema, not the labeling one.
        assert schema_at(client.seen_payload)["name"] == "podcast_claim_verification"
        assert schema_at(client.seen_payload)["strict"] is True
        # The verification rubric, not the labeling one, and the candidate
        # with its packet -- wherever this flavor carries them.
        assert rubric_at(client.seen_payload) == labeling.VERIFICATION_RUBRIC
        assert input_at(client.seen_payload).startswith("Verify this candidate:\n")
        # One candidate per request, so the record is an object, not an array.
        record = json.loads(input_at(client.seen_payload).split("\n", 1)[1])
        assert record["candidate"]["candidate_id"] == candidate["candidate_id"]
        assert "results" not in schema_at(client.seen_payload)["schema"]["properties"]
        assert candidate["claim_text"] in input_at(client.seen_payload)
        assert "sleep-guideline:p12" in input_at(client.seen_payload)
        assert result["verdict"] == "contradicted"
        assert meta["response_id"] == bodies[api]["id"]


def test_an_endpoint_written_with_its_route_still_resolves(monkeypatch):
    responses = labeling.ResponsesClient("http://localhost:8000/v1/responses")
    chat = labeling.ResponsesClient(
        "http://localhost:8000/v1/chat/completions", api="chat_completions"
    )
    assert responses.roots == chat.roots == ["http://localhost:8000/v1"]


def test_chat_truncation_is_distinguishable_from_an_empty_message():
    # With a reasoning parser configured, a response truncated mid-thought comes
    # back with a null content: the useful kind is the truncation, not the gap.
    truncated = {"choices": [{"finish_reason": "length", "message": {"content": None}}]}
    with pytest.raises(labeling.TopicLabelingError) as truncation:
        labeling.raise_for_chat_status(truncated)
    assert truncation.value.kind == "output_truncated"

    with pytest.raises(labeling.TopicLabelingError) as filtered:
        labeling.raise_for_chat_status(
            {"choices": [{"finish_reason": "content_filter", "message": {}}]}
        )
    assert filtered.value.kind == "api_incomplete"

    with pytest.raises(labeling.TopicLabelingError) as empty:
        labeling.extract_chat_output_text(
            {"choices": [{"finish_reason": "stop", "message": {"content": ""}}]}
        )
    assert empty.value.kind == "empty_output"

    labeling.raise_for_chat_status(
        {"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]}
    )


def test_the_spend_reservation_reads_the_budget_under_either_spelling():
    taxonomy = small_taxonomy()
    schema = labeling.response_schema(taxonomy)
    settings = labeling.ModelSettings(max_output_tokens=4321, reasoning_effort="none")
    for flavor in labeling.API_FLAVORS.values():
        payload = flavor.payload("rubric", "window text", "name", schema, settings)
        # A budget read as 0 would under-reserve output on every paid request.
        assert flavor.reserved_output_tokens(payload) == 4321
        # The schema is billed as prompt tokens, so the estimate must count it.
        assert flavor.payload_characters(payload) > len(labeling.canonical_json(schema))


def test_truncation_is_distinguishable_from_other_incomplete_responses():
    truncated = {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
    }
    with pytest.raises(labeling.TopicLabelingError) as truncation:
        labeling.raise_for_response_status(truncated)
    assert truncation.value.kind == "output_truncated"

    with pytest.raises(labeling.TopicLabelingError) as other:
        labeling.raise_for_response_status({"status": "failed"})
    assert other.value.kind == "api_incomplete"

    labeling.raise_for_response_status({"status": "completed"})


def test_manifest_without_episode_rows_fails_loudly(tmp_path):
    # A transcript-batch manifest keys on record_type=transcript; loading it as
    # episode metadata used to yield an empty dict and no complaint.
    manifest = tmp_path / "manifest.jsonl"
    labeling.write_jsonl_atomic(
        manifest,
        [
            {"record_type": "transcript_batch", "transcript_count": 2},
            {"record_type": "transcript", "episode_id": 191687, "word_count": 14700},
        ],
    )
    with pytest.raises(labeling.TopicLabelingError, match="record_type=episode"):
        labeling.load_manifest_metadata(manifest)

    assert labeling.load_manifest_metadata(None) == {}


def test_detection_axis_is_derived_from_the_labels(tmp_path):
    taxonomy = small_taxonomy()
    label_axes = {row["label_id"]: row["axis"] for row in taxonomy["labels"]}
    window = {
        "window_id": "episode_1_window_0001",
        "units": [{"unit_id": "u000001", "text": "A clinical trial studied sleep."}],
    }

    def detection(label_ids):
        return {
            "start_unit_id": "u000001",
            "end_unit_id": "u000001",
            "label_ids": label_ids,
            "relevance": "substantive",
            "discourse_role": "asserted_or_endorsed",
            "confidence": 0.9,
            "summary": "Sleep research is discussed.",
            "evidence_quote": "A clinical trial studied sleep",
        }

    # The model never states an axis, so it can never contradict its own labels.
    assert (
        "axis"
        not in labeling.response_schema(taxonomy)["properties"]["detections"]["items"][
            "properties"
        ]
    )

    result = {
        "window_id": window["window_id"],
        "detections": [detection(["cross_cutting:scientific_study"])],
        "verification_candidates": [],
        "product_mentions": [],
    }
    validated = labeling.validate_window_result(result, window, label_axes)
    assert validated["detections"][0]["axis"] == "evidence"

    # A label set straddling two axes is still the error that matters.
    mixed = {
        "window_id": window["window_id"],
        "detections": [detection(["topic:sleep", "cross_cutting:scientific_study"])],
        "verification_candidates": [],
        "product_mentions": [],
    }
    with pytest.raises(labeling.TopicLabelingError) as exc:
        labeling.validate_window_result(mixed, window, label_axes)
    assert exc.value.kind == "mixed_or_unknown_labels"


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
    for labeled_window, result in zip(
        windows,
        [
            {
                "window_id": windows[0]["window_id"],
                "detections": [
                    {
                        "start_unit_id": "u000002",
                        "end_unit_id": "u000003",
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
        strict=True,
    ):
        store.record_success(
            labeled_window,
            result,
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


def test_each_window_is_its_own_request_so_one_bad_window_fails_alone(
    tmp_path, monkeypatch
):
    """A rejected window is recorded unresolved without touching the others."""
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
    calls: list[str] = []

    def fake_classify(self, window, taxonomy_arg, model, *rest, **kwargs):
        calls.append(window["window_id"])
        if window["window_id"] == poison:
            raise labeling.TopicLabelingError(
                "evidence quote is not verbatim", kind="non_verbatim_quote"
            )
        result = {
            "window_id": window["window_id"],
            "detections": [],
            "verification_candidates": [],
            "product_mentions": [],
        }
        return result, {"response_id": "r", "response_model": model, "usage": None}

    monkeypatch.setattr(labeling.ResponsesClient, "classify", fake_classify)
    monkeypatch.setattr(
        labeling.ResponsesClient,
        "served_models",
        lambda self: {root: "local-model" for root in self.roots},
    )
    summary = labeling.run_label(
        argparse.Namespace(
            output_dir=tmp_path,
            taxonomy=taxonomy_path,
            windows=windows_path,
            prepare_manifest=prepare_manifest_path,
            api_base=["http://127.0.0.1:8000/v1"],
            api=labeling.DEFAULT_API,
            model="local-model",
            api_key_env=None,
            env_file=None,
            concurrency=1,
            max_output_tokens=100,
            timeout=10,
            attempts=1,
            reasoning_effort="none",
            temperature=None,
            top_p=None,
            seed=None,
            validation="strict",
            usage_limits=None,
            provider=None,
            experiment=None,
            config=tmp_path / "no-config.toml",
        )
    )
    # One request per window, and no second pass over any of them.
    assert sorted(calls) == [window["window_id"] for window in windows]
    assert summary["requests_completed_this_invocation"] == 3
    assert summary["requests_failed_this_invocation"] == 1
    assert summary["windows_labeled"] == 2
    assert summary["unresolved_windows"] == 1
    assert summary["unresolved_windows_by_kind"] == {"non_verbatim_quote": 1}
    assert "batch_size" not in summary
    assert not any("isolat" in key for key in summary)


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
        def __init__(self, api_base, api_key, timeout, attempts, **kwargs):
            assert api_key is None
            assert api_base == ["http://localhost:8000/v1"]
            assert not kwargs["limiter"].enabled

        def served_models(self):
            return {"http://localhost:8000/v1": "local-model"}

        def verify(self, pair, model, settings):
            assert pair == {"candidate": candidate, "evidence_packet": packet}
            assert model == "local-model"
            return {
                "candidate_id": candidate["candidate_id"],
                "verdict": "contradicted",
                "confidence": 0.91,
                "supporting_passage_ids": [],
                "contradicting_passage_ids": ["sleep-guideline:p12"],
                "rationale": "The evidence says sleep needs vary.",
                "limitations": "One retrieved guideline passage.",
            }, {
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
            output_dir=tmp_path,
            verification_dir=output_dir,
            api_base=["http://localhost:8000/v1"],
            api=labeling.DEFAULT_API,
            model="local-model",
            api_key_env=None,
            env_file=None,
            concurrency=1,
            max_output_tokens=6000,
            timeout=60,
            attempts=1,
            reasoning_effort="none",
            temperature=None,
            top_p=None,
            seed=None,
            usage_limits=None,
            provider=None,
            experiment=None,
            config=tmp_path / "no-config.toml",
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
        "candidate_id": "candidate-1",
        "verdict": "supported",
        "confidence": 0.8,
        "supporting_passage_ids": ["invented-passage"],
        "contradicting_passage_ids": [],
        "rationale": "The evidence supports the claim.",
        "limitations": "",
    }
    try:
        labeling.validate_verification_response(parsed, pair)
    except labeling.TopicLabelingError as exc:
        assert "invalid passage citations" in str(exc)
    else:
        raise AssertionError("a citation outside the evidence packet was accepted")


def test_verification_result_must_be_one_object_for_the_candidate_asked_about():
    pair = {
        "candidate": {"candidate_id": "candidate-1"},
        "evidence_packet": {"passages": [{"passage_id": "allowed-passage"}]},
    }
    result = {
        "candidate_id": "candidate-1",
        "verdict": "supported",
        "confidence": 0.8,
        "supporting_passage_ids": ["allowed-passage"],
        "contradicting_passage_ids": [],
        "rationale": "The evidence supports the claim.",
        "limitations": "",
    }
    assert labeling.validate_verification_response(result, pair)["verdict"] == "supported"
    for wrong in (
        {"results": [result]},
        [result],
        {**result, "candidate_id": "candidate-2"},
    ):
        with pytest.raises(labeling.TopicLabelingError):
            labeling.validate_verification_response(wrong, pair)


def test_fenced_json_output_is_parsed_and_other_garbage_is_not():
    parsed = labeling.parse_json_output('```json\n{"detections": []}\n```')
    assert parsed == {"detections": []}
    assert labeling.parse_json_output('{"detections": []}') == {"detections": []}
    assert labeling.parse_json_output('{"detections": [{"a": 1,},],}') == {"detections": [{"a": 1}]}
    # No envelope is invented around a bare array any more: with one window per
    # request the schema is a single object, and validation rejects the array.
    assert labeling.parse_json_output('[{"window_id": "w"}]') == [{"window_id": "w"}]
    with pytest.raises(json.JSONDecodeError):
        labeling.parse_json_output('Here you go:\n```json\n{"detections": []}\n```')


def test_response_is_one_result_object_for_the_one_window_sent():
    taxonomy = small_taxonomy()
    label_axes = {row["label_id"]: row["axis"] for row in taxonomy["labels"]}
    window = {
        "window_id": "episode_1_window_0001",
        "units": [{"unit_id": "u000001", "text": "A clinical trial studied sleep."}],
    }
    result = {
        "window_id": window["window_id"],
        "detections": [
            {
                "start_unit_id": "u000001",
                "end_unit_id": "u000001",
                "label_ids": ["topic:sleep"],
                "relevance": "substantive",
                "discourse_role": "asserted_or_endorsed",
                "confidence": 0.9,
                "summary": "Sleep research is discussed.",
                "evidence_quote": "A clinical trial studied sleep",
            }
        ],
        "verification_candidates": [],
        "product_mentions": [],
    }
    validated = labeling.validate_response(result, window, label_axes)
    assert validated["window_id"] == window["window_id"]
    assert validated["detections"][0]["axis"] == "topic"

    # The batch envelope, a bare array, and a result with a missing or extra
    # field are all the wrong shape.
    for wrong in (
        {"results": [result]},
        [result],
        {key: value for key, value in result.items() if key != "window_id"},
        {**result, "extra": True},
    ):
        with pytest.raises(labeling.TopicLabelingError) as shape:
            labeling.validate_response(wrong, window, label_axes)
        assert shape.value.kind == "schema_shape"

    # window_id stays as a check that the answer is for the window asked about.
    with pytest.raises(labeling.TopicLabelingError) as mismatch:
        labeling.validate_response(
            {**result, "window_id": "episode_1_window_0002"}, window, label_axes
        )
    assert mismatch.value.kind == "window_id_mismatch"


def test_a_benchmark_item_builds_a_single_window_request_and_validates():
    """Offline shape check on a real benchmark window and the real codebook."""
    taxonomy = labeling.load_taxonomy(ROOT / "benchmark" / "taxonomy.json")
    label_axes = {row["label_id"]: row["axis"] for row in taxonomy["labels"]}
    item = next(labeling.iter_jsonl(ROOT / "benchmark" / "items.jsonl"))
    window = {key: item[key] for key in ("window_id", "units")}
    settings = labeling.ModelSettings(max_output_tokens=1000, reasoning_effort="none")
    for flavor in labeling.API_FLAVORS.values():
        payload = flavor.payload(
            labeling.taxonomy_instructions(taxonomy),
            labeling.window_input(window),
            "podcast_topic_clips",
            labeling.response_schema(taxonomy),
            settings,
        )
        assert labeling.canonical_json(labeling.window_input(window)) in (
            labeling.canonical_json(payload)
        )
    record = json.loads(labeling.window_input(window).split("\n", 1)[1])
    assert record == {
        "window_id": item["window_id"],
        "units": [
            {"unit_id": unit["unit_id"], "text": unit["text"]} for unit in item["units"]
        ],
    }

    first = item["units"][0]
    topic = next(row["label_id"] for row in taxonomy["labels"] if row["axis"] == "topic")
    response = json.dumps(
        {
            "window_id": item["window_id"],
            "detections": [
                {
                    "start_unit_id": first["unit_id"],
                    "end_unit_id": first["unit_id"],
                    "label_ids": [topic],
                    "relevance": "passing",
                    "discourse_role": "unclear",
                    "confidence": 0.5,
                    "summary": "A hand-made detection for the shape check.",
                    "evidence_quote": " ".join(first["text"].split()[:5]),
                }
            ],
            "verification_candidates": [],
            "product_mentions": [],
        }
    )
    validated = labeling.validate_response(
        labeling.parse_json_output(response), item, label_axes
    )
    assert validated["window_id"] == item["window_id"]
    assert validated["detections"][0]["label_ids"] == [topic]


def test_quotes_match_on_word_sequence_not_punctuation():
    text = "It’s proven, they said, that magnesium helps."
    assert labeling.locate_quote("it's proven they said", text) == "It’s proven, they said"
    assert labeling.locate_quote("magnesium helps a lot", text) is None
    assert labeling.locate_quote("proven ... magnesium", text) is None
    stutter = "and were healing my healing my body at the same time"
    assert labeling.locate_quote("were healing my body at the same", stutter) == "were healing my healing my body at the same"
    assert labeling.locate_quote("healing my healing my body", stutter) == "healing my healing my body"


# --------------------------------------------------------------------------
# Lenient validation
# --------------------------------------------------------------------------

LENIENT_UNITS = [
    "Welcome back, today we talk about sleep.",
    "I think magnesium improves deep sleep.",
    "A clinical trial found it adds forty minutes.",
    "Try Vitalyx magnesium tonight.",
    "Anyway, we talk about sleep again later.",
]


def _lenient_window():
    return {
        "window_id": "episode_1_window_0001",
        "units": [
            {"unit_id": f"u{index:06d}", "text": text}
            for index, text in enumerate(LENIENT_UNITS, 1)
        ],
    }


def _detection(**overrides):
    base = {
        "start_unit_id": "u000002",
        "end_unit_id": "u000002",
        "label_ids": ["topic:sleep"],
        "relevance": "substantive",
        "discourse_role": "asserted_or_endorsed",
        "confidence": 0.9,
        "summary": "Magnesium and sleep.",
        "evidence_quote": "magnesium improves deep sleep",
    }
    return {**base, **overrides}


def _lenient_claim(**overrides):
    base = {
        "start_unit_id": "u000002",
        "end_unit_id": "u000002",
        "topic_ids": ["topic:sleep"],
        "frame_ids": [],
        "evidence_signal_ids": [],
        "discourse_role": "asserted_or_endorsed",
        "claim_type": "causal",
        "claim_text": "Magnesium improves deep sleep.",
        "expressed_certainty": "hedged",
        "certainty_markers": ["I think"],
        "evidence_quote": "magnesium improves deep sleep",
        "confidence": 0.8,
        "rationale": "Checkable treatment effect.",
    }
    return {**base, **overrides}


def _product(**overrides):
    base = {
        "start_unit_id": "u000004",
        "end_unit_id": "u000004",
        "product_name": "Vitalyx",
        "product_type": "supplement",
        "mention_role": "advertised",
        "evidence_quote": "Vitalyx magnesium",
        "confidence": 0.9,
    }
    return {**base, **overrides}


def _response(**fields):
    return {
        "window_id": "episode_1_window_0001",
        "detections": [],
        "verification_candidates": [],
        "product_mentions": [],
        **fields,
    }


def _axes():
    return {row["label_id"]: row["axis"] for row in small_taxonomy()["labels"]}


def _lenient(**fields):
    return labeling.validate_response_lenient(
        _response(**fields), _lenient_window(), _axes()
    )


def _strict_kind(**fields):
    with pytest.raises(labeling.TopicLabelingError) as exc:
        labeling.validate_response(_response(**fields), _lenient_window(), _axes())
    return exc.value.kind


def test_lenient_widens_a_span_to_a_verbatim_quote_just_outside_it():
    after = _detection(evidence_quote="a clinical trial found")
    before = _product(evidence_quote="we talk about sleep")
    # Strict rejects both: the quotes are in the window, not in their spans.
    assert _strict_kind(detections=[after]) == "non_verbatim_quote"
    assert _strict_kind(product_mentions=[before]) == "non_verbatim_quote"

    result, changes = _lenient(detections=[after], product_mentions=[before])
    detection = result["detections"][0]
    assert (detection["start_unit_id"], detection["end_unit_id"]) == ("u000002", "u000003")
    # The stored quote is still the transcript's own wording.
    assert detection["evidence_quote"] == "A clinical trial found"
    # "we talk about sleep" is said in u000001 and u000005; the span grows
    # towards the copy beside it, not the first one in the window.
    mention = result["product_mentions"][0]
    assert (mention["start_unit_id"], mention["end_unit_id"]) == ("u000004", "u000005")
    assert changes == {"repaired": {"span_widened_for_quote": 2}, "dropped": {}}
    # Nothing is added to the stored result.
    assert set(result) == {
        "window_id",
        "detections",
        "verification_candidates",
        "product_mentions",
    }
    assert set(detection) == set(
        labeling.validate_response(
            _response(detections=[_detection()]), _lenient_window(), _axes()
        )["detections"][0]
    )


def test_lenient_drops_a_quote_that_is_nowhere_in_the_window():
    paraphrase = _detection(evidence_quote="magnesium makes sleep deeper")
    good = _detection(label_ids=["cross_cutting:scientific_study"], evidence_quote="I think")
    result, changes = _lenient(detections=[paraphrase, good])
    assert [row["label_ids"] for row in result["detections"]] == [
        ["cross_cutting:scientific_study"]
    ]
    assert changes == {"repaired": {}, "dropped": {"non_verbatim_quote": 1}}


def test_lenient_certainty_markers_widen_drop_and_must_still_agree():
    # A marker in the window but outside the span widens the span to it.
    widened, changes = _lenient(
        verification_candidates=[
            _lenient_claim(
                start_unit_id="u000003",
                end_unit_id="u000003",
                evidence_quote="adds forty minutes",
            )
        ]
    )
    claim = widened["verification_candidates"][0]
    assert (claim["start_unit_id"], claim["end_unit_id"]) == ("u000002", "u000003")
    assert claim["certainty_markers"] == ["I think"]
    assert changes == {"repaired": {"span_widened_for_certainty_marker": 1}, "dropped": {}}

    # A marker nowhere in the window is dropped on its own when another stays.
    kept, changes = _lenient(
        verification_candidates=[_lenient_claim(certainty_markers=["I think", "perhaps"])]
    )
    assert kept["verification_candidates"][0]["certainty_markers"] == ["I think"]
    assert kept["verification_candidates"][0]["expressed_certainty"] == "hedged"
    assert changes == {"repaired": {"certainty_marker_dropped": 1}, "dropped": {}}

    # Every marker it named was missing: the hedge may be real but misquoted,
    # so the candidate goes rather than being recoded.
    _, changes = _lenient(
        verification_candidates=[_lenient_claim(certainty_markers=["perhaps"])]
    )
    assert changes == {"repaired": {}, "dropped": {"certainty_markers_mismatch": 1}}

    # It named none: an ungrounded hedge is recoded to the grounded default.
    recoded, changes = _lenient(
        verification_candidates=[_lenient_claim(certainty_markers=[])]
    )
    claim = recoded["verification_candidates"][0]
    assert (claim["expressed_certainty"], claim["certainty_markers"]) == ("unhedged", [])
    assert changes == {"repaired": {"certainty_set_unhedged": 1}, "dropped": {}}

    # Unhedged with a marker that really is there is ambiguous, and dropped.
    _, changes = _lenient(
        verification_candidates=[_lenient_claim(expressed_certainty="unhedged")]
    )
    assert changes == {"repaired": {}, "dropped": {"certainty_markers_mismatch": 1}}

    # Strict still rejects these with today's kinds.
    assert (
        _strict_kind(verification_candidates=[_lenient_claim(certainty_markers=["perhaps"])])
        == "non_verbatim_quote"
    )
    assert (
        _strict_kind(verification_candidates=[_lenient_claim(certainty_markers=[])])
        == "certainty_markers_mismatch"
    )


def test_lenient_drops_unknown_labels_only_when_the_rest_stand_on_one_axis():
    partly_unknown = _detection(label_ids=["topic:sleep", "topic:not_a_label"])
    all_unknown = _detection(label_ids=["topic:not_a_label"], summary="Other.")
    mixed = _detection(
        label_ids=["topic:sleep", "cross_cutting:scientific_study", "topic:not_a_label"],
        summary="Mixed.",
    )
    assert _strict_kind(detections=[partly_unknown]) == "mixed_or_unknown_labels"
    result, changes = _lenient(detections=[partly_unknown, all_unknown, mixed])
    assert [row["label_ids"] for row in result["detections"]] == [["topic:sleep"]]
    assert changes == {
        "repaired": {"unknown_label_dropped": 1},
        "dropped": {"mixed_or_unknown_labels": 2},
    }


def test_lenient_drops_invalid_annotations_under_their_strict_kind_and_keeps_the_first_duplicate():
    first = _detection()
    bad = {
        "span_out_of_window": _detection(end_unit_id="u000099"),
        "reversed_span": _detection(start_unit_id="u000003", end_unit_id="u000002"),
        "invalid_field": _detection(relevance="central"),
        "duplicate_annotation": _detection(summary="The same detection again."),
        "schema_shape": {"start_unit_id": "u000002"},
    }
    for kind, row in bad.items():
        assert _strict_kind(detections=[first, row]) == kind
    result, changes = _lenient(
        detections=[
            first,
            *bad.values(),
            _detection(confidence=1.5),
            _detection(summary="  "),
        ],
        verification_candidates=[_lenient_claim(claim_type="anecdote")],
        product_mentions=[_product(product_name=""), _product()],
    )
    assert result["detections"] == labeling.validate_response(
        _response(detections=[first]), _lenient_window(), _axes()
    )["detections"]
    assert result["verification_candidates"] == []
    assert [row["product_name"] for row in result["product_mentions"]] == ["Vitalyx"]
    assert changes == {
        "repaired": {},
        "dropped": {
            "duplicate_annotation": 1,
            "invalid_field": 5,
            "reversed_span": 1,
            "schema_shape": 1,
            "span_out_of_window": 1,
        },
    }


def test_lenient_truncates_past_the_per_window_caps():
    detections = []
    for index in range(42):
        # A distinct (span, labels, relevance, role) for each, so none is a
        # duplicate of another and only the cap removes any.
        unit = index % 5
        detections.append(
            _detection(
                start_unit_id=f"u{unit + 1:06d}",
                end_unit_id=f"u{unit + 1:06d}",
                label_ids=[("topic:sleep", "cross_cutting:scientific_study")[index // 5 % 2]],
                relevance=labeling.ALLOWED_RELEVANCE[index // 10 % 3],
                discourse_role=labeling.ALLOWED_DISCOURSE_ROLES[index // 30],
                summary=f"Detection {index}.",
                evidence_quote=LENIENT_UNITS[unit],
            )
        )
    assert _strict_kind(detections=detections) == "schema_shape"
    result, changes = _lenient(detections=detections)
    assert [row["summary"] for row in result["detections"]] == [
        f"Detection {index}." for index in range(40)
    ]
    assert changes == {"repaired": {}, "dropped": {"over_cap": 2}}


def test_lenient_still_rejects_a_malformed_response():
    window, axes = _lenient_window(), _axes()
    for wrong, kind in (
        ({"results": []}, "schema_shape"),
        (_response(window_id="episode_1_window_0002"), "window_id_mismatch"),
        (_response(detections={"not": "a list"}), "schema_shape"),
        (_response(product_mentions=None), "schema_shape"),
    ):
        with pytest.raises(labeling.TopicLabelingError) as exc:
            labeling.validate_response_lenient(wrong, window, axes)
        assert exc.value.kind == kind


def _classify_with(validation, model_result, on_attempt=None):
    class FakeClient(labeling.ResponsesClient):
        def _request(self, url, payload=None):
            return {
                "id": "resp_lenient",
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

    return FakeClient("http://localhost:8000/v1", attempts=1).classify(
        _lenient_window(),
        small_taxonomy(),
        "local-model",
        labeling.ModelSettings(max_output_tokens=1000, reasoning_effort="none"),
        on_attempt=on_attempt,
        validation=validation,
    )


def test_classify_returns_the_lenient_sidecar_in_meta_and_the_attempt_record():
    model_result = _response(
        detections=[
            _detection(evidence_quote="a clinical trial found"),
            _detection(evidence_quote="not said anywhere", summary="Paraphrase."),
        ]
    )
    records = []
    result, meta = _classify_with("lenient", model_result, records.append)
    expected = {
        "mode": "lenient",
        "repaired": {"span_widened_for_quote": 1},
        "dropped": {"non_verbatim_quote": 1},
    }
    assert meta["validation"] == expected
    # Accepted, drops and all, and the attempts log carries the same summary.
    assert [record["ok"] for record in records] == [True]
    assert records[0]["validation"] == expected
    assert len(result["detections"]) == 1 and "validation" not in result

    # Strict rejects the same response as it always has, and reports nothing
    # changed in a response it accepts.
    records = []
    with pytest.raises(labeling.TopicLabelingError) as exc:
        _classify_with("strict", model_result, records.append)
    assert exc.value.kind == "non_verbatim_quote"
    assert records[0]["ok"] is False and "validation" not in records[0]
    _, meta = _classify_with("strict", _response(detections=[_detection()]))
    assert meta["validation"] == {"mode": "strict", "repaired": {}, "dropped": {}}

    with pytest.raises(labeling.TopicLabelingError, match="unknown validation mode"):
        _classify_with("loose", model_result)


def test_validation_mode_is_a_label_setting_and_part_of_the_run_fingerprint(
    tmp_path, monkeypatch
):
    config = tmp_path / "config.toml"
    config.write_text('[model]\nvalidation = "lenient"\n', encoding="utf-8")
    parser = labeling.build_parser()
    assert parser.parse_args(["label"]).validation == "strict"
    assert (
        parser.parse_args(
            labeling.expand_config_args(["label", "--config", str(config)])
        ).validation
        == "lenient"
    )
    # verify validates no labels, so the shared table has nothing to tell it.
    verify = parser.parse_args(
        labeling.expand_config_args(["verify", "--config", str(config)])
    )
    assert not hasattr(verify, "validation")
    with pytest.raises(SystemExit):
        parser.parse_args(["label", "--validation", "loose"])

    taxonomy = small_taxonomy()
    taxonomy_path = tmp_path / "taxonomy.json"
    labeling.write_json(taxonomy_path, taxonomy)
    windows = [{**_lenient_window(), "episode_id": 1, "window_index": 1}]
    windows_path = tmp_path / "windows.jsonl.zst"
    _, windows_sha256 = labeling.write_jsonl_atomic(windows_path, windows)
    prepare_manifest_path = tmp_path / "prepare_manifest.json"
    labeling.write_json(
        prepare_manifest_path,
        {"windows_sha256": windows_sha256, "taxonomy_sha256": taxonomy["taxonomy_sha256"]},
    )
    modes: list[str] = []

    def fake_classify(self, window, taxonomy_arg, model, settings, validation="strict"):
        modes.append(validation)
        changes = (
            {"repaired": {"span_widened_for_quote": 2}, "dropped": {"non_verbatim_quote": 1}}
            if validation == "lenient"
            else {"repaired": {}, "dropped": {}}
        )
        return _response(), {
            "response_id": "r",
            "response_model": model,
            "usage": None,
            "validation": {"mode": validation, **changes},
        }

    monkeypatch.setattr(labeling.ResponsesClient, "classify", fake_classify)
    monkeypatch.setattr(
        labeling.ResponsesClient,
        "served_models",
        lambda self: {root: "local-model" for root in self.roots},
    )

    def run(output_dir, validation):
        return labeling.run_label(
            argparse.Namespace(
                output_dir=output_dir,
                taxonomy=taxonomy_path,
                windows=windows_path,
                prepare_manifest=prepare_manifest_path,
                api_base=["http://127.0.0.1:8000/v1"],
                api=labeling.DEFAULT_API,
                model="local-model",
                api_key_env=None,
                env_file=None,
                concurrency=1,
                max_output_tokens=100,
                timeout=10,
                attempts=1,
                reasoning_effort="none",
                temperature=None,
                top_p=None,
                seed=None,
                validation=validation,
                usage_limits=None,
                provider=None,
                experiment=None,
                config=tmp_path / "no-config.toml",
            )
        )

    strict = run(tmp_path / "strict", "strict")
    lenient = run(tmp_path / "lenient", "lenient")
    assert modes == ["strict", "lenient"]
    assert (strict["validation"], lenient["validation"]) == ("strict", "lenient")
    assert strict["run_fingerprint"] != lenient["run_fingerprint"]
    assert strict["annotations_repaired_this_invocation"] == {}
    assert lenient["annotations_repaired_this_invocation"] == {"span_widened_for_quote": 2}
    assert lenient["annotations_dropped_this_invocation"] == {"non_verbatim_quote": 1}
    # A store labeled under one mode refuses to be resumed under the other.
    with pytest.raises(labeling.TopicLabelingError, match="different run"):
        run(tmp_path / "strict", "lenient")


def test_thinking_token_budget_is_chat_only_and_fingerprinted_only_when_set():
    unbounded = labeling.ModelSettings(max_output_tokens=1000, reasoning_effort="high")
    budgeted = labeling.ModelSettings(
        max_output_tokens=1000, reasoning_effort="high", thinking_token_budget=24000
    )
    assert "thinking_token_budget" not in unbounded.fingerprint()
    assert "thinking_token_budget" not in unbounded.chat_payload()
    assert budgeted.fingerprint()["thinking_token_budget"] == 24000
    assert budgeted.chat_payload()["thinking_token_budget"] == 24000
    with pytest.raises(labeling.TopicLabelingError, match="chat_completions"):
        budgeted.responses_payload()
    args = labeling.build_parser().parse_args(
        ["label", "--thinking-token-budget", "12000"]
    )
    assert labeling.ModelSettings.from_args(args).thinking_token_budget == 12000


def test_rubric_is_the_benchmark_codebook():
    codebook = labeling.CODEBOOK_PATH.read_text(encoding="utf-8")
    assert labeling.SYSTEM_RUBRIC == codebook
    # Enumerations the model has to choose from are spelled out in the prompt
    # text, not only in the response schema it is constrained by.
    for value in ("treatment_or_prevention", "diagnosis_or_prevalence", "other_product"):
        assert value in labeling.SYSTEM_RUBRIC
    taxonomy = {
        "labels": [
            {
                "label_id": "topic:sleep",
                "axis": "topic",
                "name": "Sleep",
                "definition": "Sleep.",
                "concepts": ["insomnia"],
            }
        ]
    }
    assert labeling.taxonomy_instructions(taxonomy).startswith(codebook)
