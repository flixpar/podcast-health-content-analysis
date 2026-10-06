import argparse
import json
import sqlite3

import pytest

from analysis import topic_labeling as labeling
from analysis import typesafe_labeling as typesafe


def taxonomy():
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
            "label_id": "topic:other_health_topic",
            "kind": "topic",
            "axis": "topic",
            "name": "Other health topic",
            "definition": "Health content no listed topic fits.",
            "concepts": [],
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
        "taxonomy_sha256": labeling.sha256_bytes(labeling.canonical_json(labels).encode("utf-8")),
        "labels": labels,
    }


UNITS = [
    "Speaker 1: Welcome back to the show everybody.",
    "Today is all about sleep and why it matters.",
    "A Stanford study shows magnesium probably improves deep sleep.",
    "I take Sleep Well 3 every night, you can get it at sleepwell dot com.",
    "Anyway, let's talk about the football game.",
    "It was a great game on Sunday.",
]


def window(units=UNITS):
    return {
        "window_id": "episode_1_window_0000",
        "episode_id": 1,
        "window_index": 0,
        "units": [
            {"unit_id": f"u{index:06d}", "text": text} for index, text in enumerate(units)
        ],
    }


# Passage sizes of one keep the fake's answers readable: passage pNNN is unit N.
UNIT_POLICY = typesafe.Policy.from_mapping({"passage_units": 1})


class FakeJev:
    """Answers questions by id, the way the API does: every id, nothing else."""

    def __init__(self, nouls=None, choices=None):
        self.nouls = nouls or {}
        self.choices = choices or {}
        self.requests = []

    def __call__(self, state, questions):
        self.requests.append((state, questions))
        answers = {}
        for question_id, question in questions.items():
            if question["type"] == "noul":
                answers[question_id] = {"type": "noul", "noul": self.nouls.get(question_id, 0.0)}
            else:
                options = list(question["criteria"])
                field = question_id.rsplit("#", 1)[1]
                picked = self.choices.get(field, options[0])
                answers[question_id] = {
                    "type": "choice",
                    "choice": picked,
                    "probabilities": {option: float(option == picked) for option in options},
                    "confidence": 1.0,
                }
        return {
            "model": "jev-test",
            "answers": answers,
            "usage": {"input_tokens": 100, "output_tokens": 10},
        }


def health_window_answers():
    return {
        "label|topic:sleep": 0.95,
        "label|cross_cutting:scientific_study": 0.9,
        "gate|health": 0.99,
        "gate|claim": 0.9,
        "gate|product": 0.9,
        "topic:sleep|p001": 0.9,
        "topic:sleep|p002": 0.95,
        "topic:sleep|p003": 0.5,
        "cross_cutting:scientific_study|p002": 0.9,
        "claim|p002": 0.9,
        "product|p003": 0.9,
        "product||3|3#name:0": 0.95,  # "Sleep Well 3"
        "product||3|3#name:1": 0.9,  # "sleepwell", the same product by its URL
    }


def test_find_spans_needs_a_seed_and_joins_across_a_short_gap():
    probs = [0.1, 0.5, 0.9, 0.5, 0.1, 0.5, 0.5, 0.1, 0.8]
    # The 0.5/0.5 run never reaches the seed, so it is no span on its own.
    assert typesafe.find_spans(probs, seed=0.7, extend=0.4, bridge=0) == [
        (1, 3, 0.9),
        (8, 8, 0.8),
    ]
    # ...and it cannot act as a stepping stone between two real spans either.
    assert typesafe.find_spans(probs, seed=0.7, extend=0.4, bridge=1) == [
        (1, 3, 0.9),
        (8, 8, 0.8),
    ]
    assert typesafe.find_spans([0.9, 0.1, 0.9], seed=0.7, extend=0.4, bridge=1) == [(0, 2, 0.9)]
    assert typesafe.find_spans([], seed=0.7, extend=0.4, bridge=1) == []


def test_name_candidates_proposes_names_and_never_sentence_openers():
    found = typesafe.name_candidates(
        "Speaker 1: You heard about eight sleep. It's called the Pod 5. "
        "Visit eightsleep dot com slash tucker. All of our probiotics, like Vital Reds and AG1."
    )
    assert found == ["Pod 5", "Vital Reds", "AG1", "eightsleep"]


def test_find_markers_matches_whole_words_and_keeps_the_transcripts_casing():
    found = typesafe.find_markers("I Think it probably helps, maybe. Mayhem is not a hedge.")
    assert found == {"hedged": ["probably", "I Think"], "speculative": ["maybe"]}
    assert typesafe.find_markers("Magnesium improves sleep.") == {}


def test_policy_overrides_are_validated_and_a_number_applies_to_every_axis():
    policy = typesafe.Policy.from_mapping(
        {"seed_threshold": 0.8, "bridge_units": {"topic": 2}, "claim_threshold": "0.7"}
    )
    assert policy.seed_threshold == {"topic": 0.8, "frame": 0.8, "evidence": 0.8}
    assert policy.bridge_units == {**typesafe.Policy().bridge_units, "topic": 2}
    assert policy.claim_threshold == 0.7
    assert policy.fingerprint() != typesafe.Policy().fingerprint()
    with pytest.raises(typesafe.TypeSafeMethodError, match="unknown typesafe policy keys"):
        typesafe.Policy.from_mapping({"seed_treshold": 0.8})
    with pytest.raises(typesafe.TypeSafeMethodError, match="unknown axes"):
        typesafe.Policy.from_mapping({"seed_threshold": {"topics": 0.8}})
    with pytest.raises(typesafe.TypeSafeMethodError, match="must be positive"):
        typesafe.Policy.from_mapping({"passage_units": 0})


def test_questions_are_packed_under_the_request_budget_and_none_is_lost():
    question = {"type": "noul", "instructions": "x" * 3200}  # ~1,000 tokens
    questions = {f"q{index}": question for index in range(120)}
    batches = typesafe.pack_questions({"transcript": "short"}, questions)
    assert len(batches) > 1
    assert [key for batch in batches for key in batch] == list(questions)
    with pytest.raises(typesafe.TypeSafeMethodError) as excinfo:
        typesafe.pack_questions({"transcript": "x" * 200_000}, questions)
    assert excinfo.value.kind == "state_too_large"


@pytest.mark.parametrize("limit", [-1, -30, "-1"])
def test_policy_rejects_negative_fanout_limits(limit):
    with pytest.raises(typesafe.TypeSafeMethodError, match="max_fanout_labels must be non-negative") as excinfo:
        typesafe.Policy.from_mapping({"max_fanout_labels": limit})
    assert excinfo.value.kind == "invalid_policy"


def test_zero_fanout_limit_skips_label_localization():
    policy = typesafe.Policy.from_mapping({"max_fanout_labels": 0})
    jev = FakeJev(health_window_answers())
    _, judgments = typesafe.label_window(window(), taxonomy(), policy, jev)
    assert judgments["labels"] == {}
    assert all(
        not question_id.startswith("topic:sleep|p")
        for _, questions in jev.requests
        for question_id in questions
    )


def test_a_window_where_nothing_screens_in_costs_one_request_and_is_empty():
    jev = FakeJev()
    result, judgments = typesafe.label_window(window(), taxonomy(), UNIT_POLICY, jev)
    assert len(jev.requests) == 1
    assert result == {
        "window_id": "episode_1_window_0000",
        "detections": [],
        "verification_candidates": [],
        "product_mentions": [],
    }
    assert judgments["usage"]["requests"] == 1
    assert set(judgments["window"]) == {label["label_id"] for label in taxonomy()["labels"]}


def test_a_window_below_the_health_gate_is_empty_whatever_its_labels_say():
    """Label questions fire on figures of speech; the window-level gate does not."""
    answers = {**health_window_answers(), "gate|health": 0.05}
    jev = FakeJev(answers)
    result, judgments = typesafe.label_window(window(), taxonomy(), UNIT_POLICY, jev)
    assert len(jev.requests) == 1  # not localized, so it costs the screen only
    assert result["detections"] == [] and result["verification_candidates"] == []
    # Recomposing with the gate off cannot bring back what was never asked.
    open_gate = typesafe.Policy.from_mapping({"passage_units": 1, "health_gate_threshold": 0.0})
    assert typesafe.compose_result(window(), taxonomy(), judgments, open_gate)["detections"] == []


def test_a_health_window_composes_a_result_the_pipeline_validator_accepts():
    jev = FakeJev(
        health_window_answers(),
        {"expressed_certainty": "hedged", "claim_type": "treatment_or_prevention", "mention_role": "recommended"},
    )
    raw, judgments = typesafe.label_window(window(), taxonomy(), UNIT_POLICY, jev)
    axes = {label["label_id"]: label["axis"] for label in taxonomy()["labels"]}
    result = labeling.validate_response(raw, window(), axes)

    spans = {
        (row["label_ids"][0], row["start_unit_id"], row["end_unit_id"]) for row in result["detections"]
    }
    # u000003 is below the seed but above the extend threshold, so it joins.
    assert spans == {
        ("topic:sleep", "u000001", "u000003"),
        ("cross_cutting:scientific_study", "u000002", "u000002"),
    }
    sleep = next(row for row in result["detections"] if row["label_ids"] == ["topic:sleep"])
    # The validator stores the located words, so the closing stop is gone.
    assert sleep["evidence_quote"] == UNITS[2].rstrip(".") and sleep["confidence"] == 0.95

    (claim,) = result["verification_candidates"]
    assert claim["claim_text"] == UNITS[2]  # verbatim: Jev cannot rewrite
    assert claim["topic_ids"] == ["topic:sleep"]
    assert claim["evidence_signal_ids"] == ["cross_cutting:scientific_study"]
    assert claim["expressed_certainty"] == "hedged"
    assert claim["certainty_markers"] == ["probably"]
    assert claim["claim_type"] == "treatment_or_prevention"

    # Two candidate names cleared the bar, but they are one product.
    (product,) = result["product_mentions"]
    assert product["product_name"] == "Sleep Well 3"
    assert product["mention_role"] == "recommended"
    assert (product["start_unit_id"], product["end_unit_id"]) == ("u000003", "u000003")

    # screen, one localization grid (every passage size is 1), attributes
    assert judgments["usage"]["requests"] == 3
    assert judgments["usage"]["input_tokens_by_stage"] == {
        "screen": 100,
        "localize_1": 100,
        "attributes": 100,
    }


def test_localization_points_at_keyed_passages_and_keeps_definitions_in_the_state():
    jev = FakeJev(health_window_answers())
    typesafe.label_window(window(), taxonomy(), typesafe.Policy(), jev)
    topic_state, topic_questions = next(
        (state, questions) for state, questions in jev.requests if "topic:sleep|p000" in questions
    )
    # Three units to a topic passage by default; six units make two passages.
    assert list(topic_state["passages"]) == ["p000", "p001"]
    (subject,) = topic_state["subjects"].values()
    assert subject == {"name": "Sleep", "definition": "Sleep quality, duration and disorders."}
    instructions = topic_questions["topic:sleep|p001"]["instructions"]
    assert "`passages.p001`" in instructions and "`subjects.s00`" in instructions
    # The definition is in the state once, not in every question.
    assert "Sleep quality" not in json.dumps(topic_questions)


def test_an_unmarked_claim_is_unhedged_without_asking():
    answers = {**health_window_answers(), "claim|p002": 0.0, "claim|p001": 0.9}
    jev = FakeJev(answers, {"expressed_certainty": "absolute"})
    raw, _ = typesafe.label_window(window(), taxonomy(), UNIT_POLICY, jev)
    (claim,) = raw["verification_candidates"]
    assert (claim["expressed_certainty"], claim["certainty_markers"]) == ("unhedged", [])
    asked = [question_id for _, questions in jev.requests for question_id in questions]
    assert not any(question_id.endswith("#expressed_certainty") for question_id in asked)


def test_the_catch_all_topic_yields_to_a_listed_topic_on_the_same_stretch():
    answers = {
        **health_window_answers(),
        "label|topic:other_health_topic": 0.9,
        "topic:other_health_topic|p002": 0.9,
        "topic:other_health_topic|p005": 0.9,
    }
    raw, _ = typesafe.label_window(window(), taxonomy(), UNIT_POLICY, FakeJev(answers))
    other = [row for row in raw["detections"] if row["label_ids"] == ["topic:other_health_topic"]]
    assert [(row["start_unit_id"], row["end_unit_id"]) for row in other] == [("u000005", "u000005")]


def test_a_product_outside_any_health_stretch_is_not_a_mention():
    units = [*UNITS, "My truck is a Ford F150 and I love it."]
    answers = {
        **health_window_answers(),
        "product|p006": 0.9,
        "product||6|6#name:0": 0.95,
    }
    raw, _ = typesafe.label_window(window(units), taxonomy(), UNIT_POLICY, FakeJev(answers))
    assert [row["product_name"] for row in raw["product_mentions"]] == ["Sleep Well 3"]
    anywhere = typesafe.Policy.from_mapping({"passage_units": 1, "product_needs_topic": False})
    raw, _ = typesafe.label_window(window(units), taxonomy(), anywhere, FakeJev(answers))
    assert {row["product_name"] for row in raw["product_mentions"]} == {"Sleep Well 3", "Ford F150"}


def test_stored_judgments_recompose_under_a_new_policy_without_requests():
    jev = FakeJev(health_window_answers())
    _, judgments = typesafe.label_window(window(), taxonomy(), UNIT_POLICY, jev)
    sent = len(jev.requests)
    stored = json.loads(json.dumps(judgments))  # as read back from the sidecar
    strict = typesafe.Policy.from_mapping({"passage_units": 1, "extend_threshold": 0.8})
    recomposed = typesafe.compose_result(window(), taxonomy(), stored, strict)
    assert len(jev.requests) == sent
    sleep = next(row for row in recomposed["detections"] if row["label_ids"] == ["topic:sleep"])
    # u000003 (0.5) no longer extends the span; the new span has no stored
    # attributes, so it takes the ordinary-discussion defaults.
    assert (sleep["start_unit_id"], sleep["end_unit_id"]) == ("u000001", "u000002")
    assert (sleep["relevance"], sleep["discourse_role"]) == ("substantive", "asserted_or_endorsed")


def test_answers_that_do_not_match_the_questions_are_an_error():
    def short_answer(state, questions):
        return {"model": "jev-test", "answers": {}, "usage": {}}

    with pytest.raises(typesafe.TypeSafeMethodError) as excinfo:
        typesafe.label_window(window(), taxonomy(), UNIT_POLICY, short_answer)
    assert excinfo.value.kind == "typesafe_answers_mismatch"


# --------------------------------------------------------------------------
# The pipeline side: ``label --api typesafe``
# --------------------------------------------------------------------------


def client(monkeypatch, jev, **kwargs):
    made = labeling.TypeSafeClient(
        "https://api.typesafe.test/v1", "secret", attempts=2, policy=UNIT_POLICY, **kwargs
    )
    calls = []

    def request(url, payload=None):
        calls.append(url)
        if payload is None:
            return {"models": [{"name": "jev-latest"}, {"name": "jev-preview"}]}
        assert payload["model"] == "jev-test"
        return jev(payload["state"], payload["questions"])

    monkeypatch.setattr(made, "_request", request)
    monkeypatch.setattr(labeling.time, "sleep", lambda seconds: None)
    return made, calls


def test_the_client_labels_a_window_and_reports_what_it_cost(monkeypatch):
    made, calls = client(monkeypatch, FakeJev(health_window_answers()))
    attempts = []
    result, meta = made.classify(
        window(), taxonomy(), "jev-test", settings=None, on_attempt=attempts.append
    )
    assert {url.rsplit("/", 1)[1] for url in calls} == {"systemone"}
    assert len(result["detections"]) == 2
    assert all("axis" in row for row in result["detections"])  # through the validator
    assert meta["usage"]["input_tokens"] == 300 and meta["usage"]["requests"] == 3
    assert meta["response_model"] == "jev-test"
    assert meta["judgments"]["window"]["topic:sleep"] == 0.95
    (attempt,) = attempts
    assert attempt["ok"] and attempt["usage"] == meta["usage"]
    assert made.served_models() == {"https://api.typesafe.test/v1": "jev-latest, jev-preview"}
    assert made.discover_model() == typesafe.DEFAULT_MODEL


def test_a_rate_limit_is_waited_out_without_spending_the_windows_attempts(monkeypatch):
    jev = FakeJev()
    made, _ = client(monkeypatch, jev)
    limited = iter([True, True, True, False])

    def request(url, payload=None):
        if next(limited):
            error = labeling.TopicLabelingError("HTTP 429", kind="http_error")
            error.retryable, error.status = True, 429
            raise error
        return jev(payload["state"], payload["questions"])

    monkeypatch.setattr(made, "_request", request)
    # Three 429s against attempts=2: a transport failure would have given up.
    result, _ = made.classify(window(), taxonomy(), "jev-test", settings=None)
    assert result["detections"] == []


def test_a_failed_window_is_logged_with_its_kind_and_raised(monkeypatch):
    made, _ = client(monkeypatch, FakeJev())

    def request(url, payload=None):
        error = labeling.TopicLabelingError("HTTP 401", kind="http_error")
        error.retryable, error.status = False, 401
        raise error

    monkeypatch.setattr(made, "_request", request)
    attempts = []
    with pytest.raises(labeling.TopicLabelingError):
        made.classify(window(), taxonomy(), "jev-test", settings=None, on_attempt=attempts.append)
    assert [(row["ok"], row["kind"]) for row in attempts] == [(False, "http_error")]


def test_the_client_refuses_a_rubric_a_missing_key_and_verification(monkeypatch):
    with pytest.raises(labeling.TopicLabelingError, match="--api-key-env"):
        labeling.TypeSafeClient("https://api.typesafe.test/v1", None)
    made, _ = client(monkeypatch, FakeJev())
    with pytest.raises(labeling.TopicLabelingError, match="no rubric"):
        made.classify(window(), taxonomy(), "jev-test", settings=None, instructions="rubric")
    with pytest.raises(labeling.TopicLabelingError, match="does not verify"):
        made.verify({}, "jev-test", settings=None)


def test_the_fingerprint_is_the_question_set_and_the_policy_not_decoding_settings(monkeypatch):
    made, _ = client(monkeypatch, FakeJev())
    fingerprint = made.fingerprint(taxonomy())
    assert fingerprint["prompt_version"] == typesafe.METHOD_VERSION
    assert fingerprint["typesafe_policy"]["passage_units"] == {"topic": 1, "frame": 1, "evidence": 1}
    assert "reasoning_effort" not in fingerprint and "temperature" not in fingerprint
    monkeypatch.setattr(typesafe, "PASSAGE_NOTE", "A different note.")
    assert made.fingerprint(taxonomy())["typesafe_questions_sha256"] != fingerprint["typesafe_questions_sha256"]


def test_label_accepts_the_typesafe_api_and_verify_does_not(tmp_path):
    parser = labeling.build_parser()
    policy = tmp_path / "policy.toml"
    policy.write_text("claim_threshold = 0.7\n[seed_threshold]\ntopic = 0.8\n", encoding="utf-8")
    args = parser.parse_args(["label", "--api", "typesafe", "--typesafe-policy", str(policy)])
    assert args.api == "typesafe"
    loaded = labeling.load_typesafe_policy(args.typesafe_policy)
    assert loaded.claim_threshold == 0.7 and loaded.seed_threshold["topic"] == 0.8
    with pytest.raises(SystemExit):
        parser.parse_args(["verify", "--api", "typesafe"])

    policy.write_text("no_such_key = 1\n", encoding="utf-8")
    with pytest.raises(labeling.TopicLabelingError, match="unknown typesafe policy keys"):
        labeling.load_typesafe_policy(policy)
    with pytest.raises(labeling.TopicLabelingError, match="does not exist"):
        labeling.load_typesafe_policy(tmp_path / "missing.toml")


def test_a_policy_file_without_the_typesafe_api_is_refused():
    args = argparse.Namespace(
        api="responses", api_base=None, timeout=5, attempts=1, provider=None,
        typesafe_policy="policy.toml",
    )
    with pytest.raises(labeling.TopicLabelingError, match="--api typesafe"):
        labeling.build_label_client(args, None, labeling.UsageLimiter(None))


def test_judgments_are_appended_only_for_the_typesafe_method(tmp_path):
    path = tmp_path / labeling.TYPESAFE_JUDGMENTS
    labeling.append_judgments(path, {"usage": {}})
    assert not path.exists()
    labeling.append_judgments(path, {"judgments": {"window_id": "w1", "window": {}}})
    labeling.append_judgments(path, {"judgments": {"window_id": "w2", "window": {}}})
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["window_id"] for row in rows] == ["w1", "w2"]


@pytest.mark.parametrize("interruption", [None, "append_error", "crash_after_append"])
def test_label_runs_the_typesafe_method_end_to_end_and_merge_reads_its_output(
    tmp_path, monkeypatch, interruption
):
    """``label --api typesafe`` through the store, the sidecar and ``merge``."""
    taxonomy_path = tmp_path / "taxonomy.json"
    labeling.write_json(taxonomy_path, taxonomy())
    # Consecutive, non-overlapping windows of one episode, shaped as prepare emits them.
    common = {
        "schema_version": labeling.SCHEMA_VERSION, "episode_id": 1, "podcast_id": 2,
        "podcast_title": "Test show", "episode_title": "Test episode",
        "published_date": "2026-01-01", "source_transcript": "episode_1.jsonl.zst",
        "source_transcript_sha256": "a" * 64,
    }
    units = [
        {
            "unit_id": f"u{index:06d}", "text": text, "start_seconds": float(index * 10),
            "end_seconds": float(index * 10 + 9), "timing_quality": "segment",
            "source_segment_index": index,
        }
        for index, text in enumerate(UNITS)
    ]
    health = {**common, "window_id": "episode_1_window_0000", "window_index": 0, "units": units[:4]}
    empty = {**common, "window_id": "episode_1_window_0001", "window_index": 1, "units": units[4:]}
    windows_path = tmp_path / "windows.jsonl.zst"
    _, windows_sha256 = labeling.write_jsonl_atomic(windows_path, [health, empty])
    prepare_manifest_path = tmp_path / "prepare_manifest.json"
    labeling.write_json(
        prepare_manifest_path,
        {"windows_sha256": windows_sha256, "taxonomy_sha256": taxonomy()["taxonomy_sha256"]},
    )
    policy_path = tmp_path / "policy.toml"
    policy_path.write_text("passage_units = 1\n", encoding="utf-8")

    healthy = FakeJev(health_window_answers())

    def request(self, url, payload=None):
        if payload is None:
            return {"models": [{"name": "jev-latest"}]}
        # The football window screens out; the health window localizes.
        if "transcript" in payload["state"] and "sleep" not in payload["state"]["transcript"]:
            return FakeJev()(payload["state"], payload["questions"])
        return healthy(payload["state"], payload["questions"])

    monkeypatch.setattr(labeling.TypeSafeClient, "_request", request)
    monkeypatch.setenv("TYPESAFE_TEST_KEY", "secret")
    args = argparse.Namespace(
        output_dir=tmp_path, taxonomy=taxonomy_path, windows=windows_path,
        prepare_manifest=prepare_manifest_path, api_base=None, api="typesafe",
        typesafe_policy=policy_path, model=None, api_key_env="TYPESAFE_TEST_KEY",
        env_file=None, concurrency=2, max_output_tokens=100, timeout=10, attempts=1,
        reasoning_effort="none", temperature=None, top_p=None, seed=None,
        validation="strict", usage_limits=None, provider=None, experiment=None,
        config=tmp_path / "no-config.toml",
    )
    if interruption is not None:
        with monkeypatch.context() as interrupted:
            if interruption == "append_error":
                def fail_append(path, meta):
                    raise OSError("sidecar unavailable")

                interrupted.setattr(labeling, "append_judgments", fail_append)
                failed = labeling.run_label(args)
                assert failed["windows_labeled"] == 0
                assert failed["unresolved_windows"] == 2
                assert not (tmp_path / labeling.TYPESAFE_JUDGMENTS).exists()
            else:
                def crash_before_success(self, *args):
                    raise KeyboardInterrupt("process interrupted before checkpoint")

                interrupted.setattr(labeling.LabelStore, "record_success", crash_before_success)
                with pytest.raises(KeyboardInterrupt):
                    labeling.run_label(args)
                assert (tmp_path / labeling.TYPESAFE_JUDGMENTS).exists()
            # Neither interruption may leave a successful checkpoint that skips resume.
            with sqlite3.connect(tmp_path / "labels.sqlite") as conn:
                assert conn.execute("SELECT count(*) FROM window_labels").fetchone()[0] == 0
    summary = labeling.run_label(args)
    assert summary["windows_labeled"] == 2 and summary["unresolved_windows"] == 0
    assert summary["model"] == typesafe.DEFAULT_MODEL
    assert summary["prompt_version"] == typesafe.METHOD_VERSION
    assert summary["typesafe_policy"]["passage_units"]["topic"] == 1
    assert "reasoning_effort" not in summary
    sidecar = [
        json.loads(line)
        for line in (tmp_path / labeling.TYPESAFE_JUDGMENTS).read_text(encoding="utf-8").splitlines()
    ]
    assert {row["window_id"] for row in sidecar} == {health["window_id"], empty["window_id"]}
    assert len(sidecar) == (3 if interruption == "crash_after_append" else 2)

    # A different policy is a different run: the store refuses to mix them.
    policy_path.write_text("passage_units = 1\nclaim_threshold = 0.9\n", encoding="utf-8")
    with pytest.raises(labeling.TopicLabelingError, match="different run"):
        labeling.run_label(args)

    rows = list(labeling.iter_jsonl(tmp_path / "window_labels.jsonl.zst"))
    labeled = next(row for row in rows if row["window_id"] == health["window_id"])
    assert [row["label_ids"] for row in labeled["detections"]] == [
        ["topic:sleep"],
        ["cross_cutting:scientific_study"],
    ]

    # Downstream stages read the result, not the method: merge needs nothing new.
    assert labeling.main(["merge", "--output-dir", str(tmp_path)]) == 0
    clips = list(labeling.iter_jsonl(tmp_path / "clips.jsonl"))
    assert [[topic["label_id"] for topic in clip["topics"]] for clip in clips] == [["topic:sleep"]]
    candidates = list(labeling.iter_jsonl(tmp_path / "verification_candidates.jsonl"))
    assert [row["claim_text"] for row in candidates] == [UNITS[2]]
