"""Endpoint routing, retries, resumable bookkeeping and prepare selection."""

import argparse
import http.client
import sqlite3

import pytest

from analysis import topic_labeling as labeling
from analysis.tests.test_topic_labeling import ROOT, small_taxonomy

A = "http://node-a:8222/v1"
B = "http://node-b:8222/v1"


def client(*bases, attempts=3):
    return labeling.ResponsesClient(list(bases), attempts=attempts, api="chat_completions")


def transport_error(message="endpoint request failed: RemoteDisconnected"):
    error = labeling.TopicLabelingError(message, kind="transport")
    error.retryable = True
    return error


# ---- transport errors ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        http.client.RemoteDisconnected("Remote end closed connection without response"),
        http.client.IncompleteRead(b"partial"),
        ConnectionResetError(104, "Connection reset by peer"),
    ],
)
def test_a_dropped_connection_is_a_retryable_transport_error(monkeypatch, raw):
    pool = client(A)

    def drop(*_args, **_kwargs):
        raise raw

    monkeypatch.setattr(pool.opener, "open", drop)
    with pytest.raises(labeling.TopicLabelingError) as caught:
        pool._request(A + "/chat/completions", {"model": "m"})
    assert caught.value.kind == "transport"
    assert caught.value.retryable is True
    assert labeling.is_endpoint_fault(caught.value)


def test_only_server_failures_count_as_endpoint_faults():
    def http_error(status):
        error = labeling.TopicLabelingError(f"returned HTTP {status}", kind="http_error")
        error.status = status
        return error

    assert labeling.is_endpoint_fault(transport_error())
    assert labeling.is_endpoint_fault(http_error(503))
    assert labeling.is_endpoint_fault(http_error(429))
    assert not labeling.is_endpoint_fault(http_error(400))
    assert not labeling.is_endpoint_fault(
        labeling.TopicLabelingError("quote is not verbatim", kind="non_verbatim_quote")
    )


# ---- routing ---------------------------------------------------------------------------------


def test_requests_go_to_the_server_with_the_fewest_in_flight():
    pool = client(A, B)
    held = [pool._acquire() for _ in range(4)]
    assert sorted(held) == [A, A, B, B]
    # A finishes two requests; the next two both go to A, not alternately.
    pool._release(A, failed=False)
    pool._release(A, failed=False)
    assert [pool._acquire(), pool._acquire()] == [A, A]


def test_a_failed_server_is_skipped_until_its_cooldown_expires(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(labeling.time, "monotonic", lambda: clock[0])
    pool = client(A, B)
    root = pool._acquire()
    pool._release(root, failed=True)
    other = B if root == A else A
    # The failed server has nothing in flight but must not attract the traffic.
    assert {pool._acquire() for _ in range(5)} == {other}
    clock[0] += labeling.ENDPOINT_COOLDOWN_SECONDS + 1
    assert pool._acquire() == root


def test_every_server_cooling_down_still_routes_somewhere():
    pool = client(A, B)
    for root in (A, B):
        pool._cooldown_until[root] = float("inf")
    assert pool._acquire() in (A, B)


def test_a_server_fault_marks_the_error_and_the_retry_avoids_that_server(monkeypatch):
    pool = client(A, B)
    sent = []

    def send_to(root, payload, model):
        sent.append(root)
        if root == A:
            raise transport_error()
        return {"id": "ok", "usage": {}}

    monkeypatch.setattr(pool, "_send_to", send_to)
    # Force the first request onto A.
    pool._in_flight[B] = 1
    with pytest.raises(labeling.TopicLabelingError) as caught:
        pool._send({}, "m")
    pool._in_flight[B] = 0
    assert caught.value.endpoint == A
    assert pool._send({}, "m", avoid=caught.value.endpoint) == {"id": "ok", "usage": {}}
    assert sent == [A, B]
    assert pool._in_flight[A] == pool._in_flight[B] == 0


def test_content_rejections_do_not_cool_a_server_down(monkeypatch):
    pool = client(A)

    def send_to(root, payload, model):
        raise labeling.TopicLabelingError("bad response", kind="non_verbatim_quote")

    monkeypatch.setattr(pool, "_send_to", send_to)
    with pytest.raises(labeling.TopicLabelingError) as caught:
        pool._send({}, "m")
    assert not hasattr(caught.value, "endpoint")
    assert A not in pool._cooldown_until


# ---- startup with a server down --------------------------------------------------------------


def models_except(down):
    def request(url, payload=None):
        if url.startswith(down):
            raise transport_error("endpoint request failed: URLError")
        return {"data": [{"id": "glm"}]}

    return request


def test_a_server_down_at_startup_is_skipped_only_when_allowed(monkeypatch, capsys):
    pool = client(A, B)
    monkeypatch.setattr(pool, "_request", models_except(B))
    with pytest.raises(labeling.TopicLabelingError):
        pool.served_models()
    pool.allow_unreachable = True
    assert pool.served_models() == {A: "glm"}
    assert pool.unreachable == [B]
    assert pool._acquire() == A
    assert "unreachable endpoint" in capsys.readouterr().err


def test_startup_needs_at_least_one_server(monkeypatch):
    pool = client(A)
    pool.allow_unreachable = True
    monkeypatch.setattr(pool, "_request", models_except(A))
    with pytest.raises(labeling.TopicLabelingError, match="no endpoint is reachable"):
        pool.served_models()


# ---- run_label: final retry, per-window bookkeeping, progress --------------------------------


def label_inputs(tmp_path, count=3):
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
        for index in range(1, count + 1)
    ]
    windows_path = tmp_path / "windows.jsonl.zst"
    _, windows_sha256 = labeling.write_jsonl_atomic(windows_path, windows)
    manifest_path = tmp_path / "prepare_manifest.json"
    labeling.write_json(
        manifest_path,
        {
            "windows_sha256": windows_sha256,
            "taxonomy_sha256": taxonomy["taxonomy_sha256"],
            "windows": count,
        },
    )
    return taxonomy_path, windows_path, manifest_path, windows


def label_args(tmp_path, taxonomy_path, windows_path, manifest_path, **overrides):
    values = dict(
        output_dir=tmp_path,
        taxonomy=taxonomy_path,
        windows=windows_path,
        prepare_manifest=manifest_path,
        api_base=[A],
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
        validation="lenient",
        usage_limits=None,
        provider=None,
        experiment=None,
        config=tmp_path / "no-config.toml",
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def ok_result(window, model, **meta):
    result = {
        "window_id": window["window_id"],
        "detections": [],
        "verification_candidates": [],
        "product_mentions": [],
    }
    return result, {"response_id": "r", "response_model": model, "usage": None, **meta}


def test_windows_that_failed_on_a_server_get_a_final_retry(tmp_path, monkeypatch):
    taxonomy_path, windows_path, manifest_path, _ = label_inputs(tmp_path)
    calls = []

    def fake_classify(self, window, taxonomy, model, *rest, **kwargs):
        calls.append(window["window_id"])
        if window["window_id"] == "episode_1_window_0002" and calls.count(window["window_id"]) == 1:
            raise labeling.TopicLabelingError(
                "classification failed after 1 attempt(s): endpoint request failed",
                kind="transport",
            )
        if window["window_id"] == "episode_1_window_0003":
            raise labeling.TopicLabelingError("not verbatim", kind="non_verbatim_quote")
        return ok_result(window, model)

    monkeypatch.setattr(labeling.ResponsesClient, "classify", fake_classify)
    monkeypatch.setattr(
        labeling.ResponsesClient, "served_models", lambda self: {r: "local-model" for r in self.roots}
    )
    summary = labeling.run_label(label_args(tmp_path, taxonomy_path, windows_path, manifest_path))
    # The server failure was retried and resolved; the content rejection was not.
    assert calls.count("episode_1_window_0002") == 2
    assert calls.count("episode_1_window_0003") == 1
    assert summary["final_retry_windows"] == 1
    assert summary["windows_labeled"] == 2
    assert summary["unresolved_windows_by_kind"] == {"non_verbatim_quote": 1}


def test_final_retry_can_be_disabled(tmp_path, monkeypatch):
    taxonomy_path, windows_path, manifest_path, _ = label_inputs(tmp_path, count=1)

    def fake_classify(self, window, *rest, **kwargs):
        raise labeling.TopicLabelingError("endpoint request failed", kind="transport")

    monkeypatch.setattr(labeling.ResponsesClient, "classify", fake_classify)
    monkeypatch.setattr(
        labeling.ResponsesClient, "served_models", lambda self: {r: "local-model" for r in self.roots}
    )
    summary = labeling.run_label(
        label_args(tmp_path, taxonomy_path, windows_path, manifest_path, final_retry_passes=0)
    )
    assert summary["final_retry_windows"] == 0
    assert summary["unresolved_windows_by_kind"] == {"transport": 1}


def test_validation_and_attempts_are_kept_per_window_and_totalled_over_the_store(
    tmp_path, monkeypatch
):
    taxonomy_path, windows_path, manifest_path, windows = label_inputs(tmp_path, count=2)

    def fake_classify(self, window, taxonomy, model, *rest, **kwargs):
        return ok_result(
            window,
            model,
            usage={"completion_tokens": 50},
            validation={"mode": "lenient", "repaired": {"span_widened_for_quote": 2},
                        "dropped": {"non_verbatim_quote": 1}},
            attempts=2,
            rejected_completion_tokens=30,
        )

    monkeypatch.setattr(labeling.ResponsesClient, "classify", fake_classify)
    monkeypatch.setattr(
        labeling.ResponsesClient, "served_models", lambda self: {r: "local-model" for r in self.roots}
    )
    summary = labeling.run_label(label_args(tmp_path, taxonomy_path, windows_path, manifest_path))
    assert summary["validation_totals"] == {
        "windows_with_validation_record": 2,
        "annotations_repaired": {"span_widened_for_quote": 4},
        "annotations_dropped": {"non_verbatim_quote": 2},
        "windows_by_attempts": {"2": 2},
        "rejected_attempt_completion_tokens": 60,
    }
    row = sqlite3.connect(tmp_path / "labels.sqlite").execute(
        "SELECT attempts, rejected_completion_tokens FROM window_labels LIMIT 1"
    ).fetchone()
    assert row == (2, 30)


def test_an_older_store_gains_the_new_columns(tmp_path):
    path = tmp_path / "labels.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE run (singleton INTEGER PRIMARY KEY, run_fingerprint TEXT NOT NULL,
                          manifest_json TEXT NOT NULL);
        CREATE TABLE window_labels (window_id TEXT PRIMARY KEY, episode_id INTEGER NOT NULL,
            window_index INTEGER NOT NULL, result_json TEXT NOT NULL, response_id TEXT,
            response_model TEXT, usage_json TEXT, labeled_at TEXT NOT NULL);
        INSERT INTO run VALUES (1, 'fp', '{}');
        INSERT INTO window_labels VALUES ('w1', 1, 1, '{}', NULL, NULL, NULL, 'then');
        """
    )
    connection.commit()
    connection.close()
    store = labeling.LabelStore(path, {"run_fingerprint": "fp"})
    try:
        columns = {row[1] for row in store.conn.execute("PRAGMA table_info(window_labels)")}
        assert {"validation_json", "attempts", "rejected_completion_tokens"} <= columns
        assert store.validation_totals()["windows_with_validation_record"] == 0
    finally:
        store.close()


def test_progress_reports_rate_throughput_and_eta():
    progress = labeling.LabelProgress(total_windows=1000)
    assert progress.describe(0, now=0.0) == ""
    for second in range(0, 361, 36):  # 11 windows over 6 minutes, 100 tokens each
        progress.record(100, now=float(second))
    assert progress.describe(500, now=360.0) == "rate=110/h out_tok/s=3 eta=4.5h"


# ---- prepare: episode selection, order, portable paths ---------------------------------------


def write_transcripts(directory, episode_ids):
    directory.mkdir()
    for episode_id in episode_ids:
        labeling.write_jsonl_atomic(
            directory / f"episode_{episode_id}.jsonl.zst",
            [
                {"type": "metadata", "episode_id": episode_id, "source": "asr", "model": "t"},
                {"type": "summary", "language": "en"},
                {"type": "segment", "index": 0, "start": 0, "end": 60,
                 "text": f"Episode {episode_id} discusses sleep."},
            ],
        )


def prepare_args(tmp_path, transcripts, **overrides):
    values = dict(
        output_dir=tmp_path / "output",
        topics=ROOT / labeling.DEFAULT_TOPICS,
        transcripts=transcripts,
        limit=None,
        manifest=None,
        metadata_db=None,
        max_unit_words=45,
        window_words=900,
        overlap_words=150,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


@pytest.mark.parametrize(
    "contents", ["3\n# a comment\n5\n9\n", "episode_id,study_month\n3,2020-01\n5,2020-02\n9,2020-03\n"]
)
def test_prepare_selects_listed_episodes(tmp_path, contents):
    transcripts = tmp_path / "transcripts"
    write_transcripts(transcripts, [1, 3, 5, 7])
    ids = tmp_path / "ids.txt"
    ids.write_text(contents, encoding="utf-8")
    manifest = labeling.run_prepare(prepare_args(tmp_path, transcripts, episode_ids=ids))
    windows = list(labeling.iter_jsonl(tmp_path / "output" / "windows.jsonl.zst"))
    assert [w["episode_id"] for w in windows] == [3, 5]
    assert manifest["episode_filter"]["requested"] == 3
    assert manifest["episode_filter"]["found"] == 2
    assert manifest["episode_filter"]["missing_transcripts"] == 1


def test_bad_episode_list_fails_loudly(tmp_path):
    transcripts = tmp_path / "transcripts"
    write_transcripts(transcripts, [1])
    ids = tmp_path / "ids.txt"
    ids.write_text("one\n", encoding="utf-8")
    with pytest.raises(labeling.TopicLabelingError, match="episode ID"):
        labeling.run_prepare(prepare_args(tmp_path, transcripts, episode_ids=ids))


def test_shuffled_order_is_deterministic_and_keeps_each_episode_together(tmp_path):
    transcripts = tmp_path / "transcripts"
    episode_ids = list(range(1, 21))
    write_transcripts(transcripts, episode_ids)
    orders = []
    for run in ("a", "b"):
        manifest = labeling.run_prepare(
            prepare_args(tmp_path, transcripts, output_dir=tmp_path / run, order="shuffled")
        )
        assert manifest["order"] == "shuffled"
        orders.append(
            [w["episode_id"] for w in labeling.iter_jsonl(tmp_path / run / "windows.jsonl.zst")]
        )
    assert orders[0] == orders[1]
    assert sorted(orders[0]) == episode_ids and orders[0] != episode_ids


def test_windows_record_the_transcript_relative_to_its_directory(tmp_path):
    transcripts = tmp_path / "transcripts"
    write_transcripts(transcripts, [4])
    labeling.run_prepare(prepare_args(tmp_path, transcripts))
    (window,) = labeling.iter_jsonl(tmp_path / "output" / "windows.jsonl.zst")
    assert window["source_transcript"] == "episode_4.jsonl.zst"
