import types

import pytest

pytest.importorskip("torch")

from analysis.serving import clef_server


class FakeRelease:
    """The release's encode_record, reduced to what planning depends on.

    Like the real one it silently cuts the state to make room for the schema:
    one token per state character, ten per question.
    """

    QUESTION_TYPES = {"noul": 0, "choice": 1, "score": 2}

    @staticmethod
    def encode_record(tokenizer, record, max_length):
        schema = 10 * len(record["questions"])
        if schema > max_length:
            raise ValueError("schema requires more tokens than the maximum")
        state = min(len(record["state"]), max_length - schema)
        return types.SimpleNamespace(input_ids=[0] * (state + schema), questions=list(record["questions"]))


def server(max_tokens, max_questions=None):
    made = clef_server.ClefServer.__new__(clef_server.ClefServer)
    made.max_tokens = max_tokens
    made.max_questions = max_questions
    made.release = FakeRelease
    made.tokenizer = None
    return made


def test_a_request_too_long_for_one_pass_is_split_and_never_truncated():
    questions = {f"q{number}": {"type": "noul"} for number in range(10)}
    passes = server(max_tokens=120).plan("x" * 50, questions)
    # 50 state tokens + 100 question tokens do not fit in 120; two passes of
    # five questions (100 tokens each) do, and each holds the whole state.
    assert [list(item.questions) for item in passes] == [
        [f"q{number}" for number in range(5)],
        [f"q{number}" for number in range(5, 10)],
    ]
    assert all(len(item.encoded.input_ids) == 100 for item in passes)


def test_a_state_that_cannot_fit_with_one_question_is_refused():
    with pytest.raises(clef_server.RequestError, match="does not fit"):
        server(max_tokens=60).plan("x" * 55, {"q": {"type": "noul"}})


def test_max_questions_bounds_what_is_decided_jointly():
    questions = {f"q{number}": {"type": "noul"} for number in range(7)}
    passes = server(max_tokens=10_000, max_questions=3).plan("x", questions)
    assert [len(item.questions) for item in passes] == [3, 3, 1]
