import argparse
import threading
import time

import pytest

from analysis import usage_limits as limits
from analysis import topic_labeling as labeling


def write_config(tmp_path, body: str):
    path = tmp_path / "usage-limits.toml"
    path.write_text(
        f'[settings]\ndatabase = "{tmp_path / "usage.sqlite"}"\n{body}',
        encoding="utf-8",
    )
    return path


class FakeClock:
    """A clock that only moves when the limiter sleeps, so waits are exact."""

    def __init__(self, start: float = 1_800_000_000.0) -> None:
        self.now = start
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def make_limiter(tmp_path, body: str, experiment: str | None = None):
    clock = FakeClock()
    limiter = limits.UsageLimiter.from_config(
        write_config(tmp_path, body), experiment, clock=clock, sleep=clock.sleep
    )
    return limiter, clock


def spend(limiter, *, input_tokens=0.0, output_tokens=0.0, cached=0.0, record=True):
    with limiter.reserve(
        provider="demo",
        model="m1",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    ) as lease:
        if record:
            lease.record(
                {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "input_tokens_details": {"cached_tokens": cached},
                }
            )
    return lease


def test_reported_usage_replaces_the_reservation(tmp_path):
    limiter, _ = make_limiter(
        tmp_path,
        """
[provider.demo]
tokens_per_day = 10_000
""",
    )
    with limiter.reserve(
        provider="demo", model="m1", input_tokens=1_000, output_tokens=4_000
    ) as lease:
        # Mid-request the whole estimate is held, or concurrent requests would
        # all read the same untouched budget and all pass it.
        assert limiter.status()[0]["used"] == 5_000
        lease.record({"input_tokens": 900, "output_tokens": 100})
    assert limiter.status()[0]["used"] == 1_000
    assert limiter.report(group_by="outcome")[0]["outcome"] == "recorded"


def test_an_unreported_request_keeps_its_estimate(tmp_path):
    """A request that failed after generating was still billed for it."""
    limiter, _ = make_limiter(
        tmp_path,
        """
[provider.demo]
tokens_per_day = 10_000
""",
    )
    with pytest.raises(RuntimeError):
        with limiter.reserve(
            provider="demo", model="m1", input_tokens=1_000, output_tokens=2_000
        ):
            raise RuntimeError("the endpoint timed out")
    assert limiter.status()[0]["used"] == 3_000
    assert limiter.report(group_by="outcome")[0]["outcome"] == "estimated"


def test_a_spent_day_budget_stops_the_run_rather_than_waiting(tmp_path):
    limiter, clock = make_limiter(
        tmp_path,
        """
[provider.demo]
tokens_per_day = 1_000
""",
    )
    spend(limiter, input_tokens=900)
    with pytest.raises(limits.BudgetExceeded) as caught:
        spend(limiter, input_tokens=900)
    assert caught.value.scope == "provider:demo"
    assert caught.value.limit == "tokens_per_day"
    assert clock.slept == []
    # The kind travels with the exception, so the labeling stores can aggregate
    # a run stopped by its budget without parsing the message.
    assert labeling.error_kind(caught.value) == "budget_exceeded"


def test_a_minute_limit_waits_for_its_boundary_instead_of_failing(tmp_path):
    limiter, clock = make_limiter(
        tmp_path,
        """
[provider.demo]
output_tokens_per_minute = 1_000
""",
    )
    start = clock.now
    for _ in range(4):
        spend(limiter, output_tokens=400)
    # Two fit in the first minute; the third waits out the boundary and then
    # the fourth fits beside it, so one boundary covers all four.
    assert clock.slept == [pytest.approx(60, abs=1)]
    assert clock.now - start == pytest.approx(60, abs=1)


def test_a_minute_limit_smaller_than_one_request_fails_immediately(tmp_path):
    """Waiting cannot help, so it is a misconfiguration rather than a rate."""
    limiter, clock = make_limiter(
        tmp_path,
        """
[provider.demo]
output_tokens_per_minute = 100
""",
    )
    with pytest.raises(limits.UsageLimitError, match="smaller than"):
        spend(limiter, output_tokens=4_000)
    assert clock.slept == []


def test_concurrency_holds_across_threads_and_releases_on_failure(tmp_path):
    limiter, _ = make_limiter(
        tmp_path,
        """
max_wait_seconds = 30
poll_seconds = 0.01

[provider.demo]
max_concurrent = 2
""",
    )
    # A real clock: this one is about threads racing, not about windows.
    limiter.clock, limiter.sleep = time.time, time.sleep
    live, peak, guard = [0], [0], threading.Lock()

    def worker(index: int) -> None:
        try:
            with limiter.reserve(provider="demo", model="m1"):
                with guard:
                    live[0] += 1
                    peak[0] = max(peak[0], live[0])
                time.sleep(0.05)
                with guard:
                    live[0] -= 1
                if index == 0:
                    raise RuntimeError("this slot still has to come back")
        except RuntimeError:
            pass

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert peak[0] == 2
    assert limiter._conn.execute("SELECT count(*) FROM leases").fetchone()[0] == 0


def test_an_expired_lease_frees_the_slot_a_dead_process_held(tmp_path):
    limiter, clock = make_limiter(
        tmp_path,
        """
lease_seconds = 60
max_wait_seconds = 300

[provider.demo]
max_concurrent = 1
""",
    )
    # Held by a reference that never releases it, standing in for a process
    # that died mid-request. (Dropping the reference would let the garbage
    # collector close it, which is exactly what a dead process cannot do.)
    abandoned = limiter.reserve(provider="demo", model="m1")
    abandoned.__enter__()
    with limiter.reserve(provider="demo", model="m1"):
        pass
    # Blocked until the abandoned lease expired, then admitted.
    assert sum(clock.slept) >= 60


def test_cost_uses_the_configured_price_and_the_cached_rate(tmp_path):
    limiter, _ = make_limiter(
        tmp_path,
        """
[provider.demo]
cost_per_day = 100.0

[model.demo."m1"]
input_per_mtok = 2.0
output_per_mtok = 10.0
cached_input_per_mtok = 0.2
""",
    )
    spend(limiter, input_tokens=1_000_000, output_tokens=100_000, cached=500_000)
    # 0.5M uncached at $2, 0.5M cached at $0.20, 0.1M output at $10.
    assert limiter.report()[0]["cost_usd"] == pytest.approx(1.0 + 0.1 + 1.0)


def test_a_cost_limit_on_an_unpriced_model_is_refused(tmp_path):
    """Silently costing $0.00 per request is the wrong way to fail."""
    limiter, _ = make_limiter(
        tmp_path,
        """
[provider.demo]
cost_per_day = 10.0
""",
    )
    with pytest.raises(limits.UsageLimitError, match="no price"):
        spend(limiter, input_tokens=10)


def test_experiment_allocations_are_declared_and_spend_across_runs(tmp_path):
    body = """
[provider.demo]
max_concurrent = 4

[model.demo."m1"]
input_per_mtok = 1000.0
output_per_mtok = 1000.0

[experiment.pilot]
cost_total = 0.05
"""
    config = write_config(tmp_path, body)
    first = limits.UsageLimiter.from_config(config, "pilot")
    for _ in range(2):
        spend(first, input_tokens=10)  # $0.01 each
    first.close()

    # A second process picks up the same allocation where the first left it.
    second = limits.UsageLimiter.from_config(config, "pilot")
    remaining = {row["limit"]: row["remaining"] for row in second.status()}
    assert remaining["cost_total"] == pytest.approx(0.03)
    with pytest.raises(limits.BudgetExceeded):
        for _ in range(5):
            spend(second, input_tokens=10)
    assert second.report(experiment="pilot", group_by="experiment")[0]["requests"] >= 4
    second.close()

    with pytest.raises(limits.UsageLimitError, match="not declared"):
        limits.UsageLimiter.from_config(config, "piolt")


def test_an_undeclared_provider_is_an_error_not_an_unmetered_default(tmp_path):
    limiter, _ = make_limiter(tmp_path, "[provider.demo]\n")
    with pytest.raises(limits.UsageLimitError, match="not declared"):
        with limiter.reserve(provider="fireworks", model="m1"):
            pass


def test_config_rejects_a_misspelled_limit(tmp_path):
    with pytest.raises(limits.UsageLimitError, match="unknown setting"):
        limits.load_config(
            write_config(tmp_path, "[provider.demo]\ntokens_per_hour = 5\n")
        )


def test_config_rejects_a_model_declared_outside_a_provider(tmp_path):
    with pytest.raises(limits.UsageLimitError, match="declared per provider"):
        limits.load_config(
            write_config(
                tmp_path, "[provider.demo]\n\n[model.demo]\nmax_concurrent = 2\n"
            )
        )


@pytest.mark.parametrize(
    "usage, expected",
    [
        # Responses API, and Chat Completions.
        (
            {
                "input_tokens": 100,
                "output_tokens": 20,
                "input_tokens_details": {"cached_tokens": 40},
            },
            (100, 20, 40),
        ),
        (
            {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "prompt_tokens_details": {"cached_tokens": 40},
            },
            (100, 20, 40),
        ),
        # Anthropic reports input_tokens *excluding* the cached reads beside it.
        (
            {
                "input_tokens": 60,
                "output_tokens": 20,
                "cache_read_input_tokens": 40,
                "cache_creation_input_tokens": 0,
            },
            (100, 20, 40),
        ),
        ({}, None),
        (None, None),
    ],
)
def test_usage_is_read_from_every_dialect_in_circulation(usage, expected):
    parsed = limits.Usage.parse(usage)
    if expected is None:
        assert parsed is None
    else:
        assert (
            parsed.input_tokens,
            parsed.output_tokens,
            parsed.cached_input_tokens,
        ) == expected
        assert parsed.uncached_input_tokens == expected[0] - expected[2]


def test_a_run_without_limits_is_inert(tmp_path):
    limiter = limits.UsageLimiter.from_config(None)
    assert not limiter.enabled
    with limiter.reserve(provider="anything", model="m1") as lease:
        lease.record({"input_tokens": 5})
    assert limiter.status() == []


def test_labeling_refuses_the_halfway_configurations():
    def args(usage_limits=None, provider=None, experiment=None):
        return argparse.Namespace(
            usage_limits=usage_limits, provider=provider, experiment=experiment
        )

    assert not labeling.build_limiter(args()).enabled
    with pytest.raises(labeling.TopicLabelingError, match="needs --usage-limits"):
        labeling.build_limiter(args(experiment="pilot"))
    with pytest.raises(labeling.TopicLabelingError, match="nothing to do"):
        labeling.build_limiter(args(provider="demo"))
    with pytest.raises(labeling.TopicLabelingError, match="needs --provider"):
        labeling.build_limiter(args(usage_limits="x.toml"))


def test_labeling_charges_every_request_to_the_limiter(tmp_path, monkeypatch):
    limiter, _ = make_limiter(
        tmp_path,
        """
[provider.demo]
tokens_per_day = 1_000_000

[model.demo."local-model"]
input_per_mtok = 3.0
output_per_mtok = 6.0
""",
    )
    client = labeling.ResponsesClient(
        ["http://127.0.0.1:8000/v1"], limiter=limiter, provider="demo"
    )
    sent: list[dict] = []

    def fake_request(self, url, payload=None):
        sent.append(payload)
        return {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "{}"}]}
            ],
            "usage": {"input_tokens": 4_000, "output_tokens": 700},
        }

    monkeypatch.setattr(labeling.ResponsesClient, "_request", fake_request)
    monkeypatch.setattr(labeling, "validate_response", lambda parsed, windows, axes: [])
    client.classify(
        [{"window_id": "w", "units": []}], small_taxonomy(), "local-model", settings()
    )

    used = {row["limit"]: row["used"] for row in limiter.status()}
    assert used["tokens_per_day"] == 4_700
    ledger = limiter.report(group_by="model")[0]
    assert ledger["model"] == "demo/local-model"
    assert ledger["cost_usd"] == pytest.approx(4_000 * 3e-6 + 700 * 6e-6)


def settings():
    return labeling.ModelSettings(max_output_tokens=1_000, reasoning_effort="none")


def small_taxonomy():
    labels = [
        {
            "label_id": "topic:sleep",
            "kind": "topic",
            "axis": "topic",
            "name": "Sleep",
            "definition": "Sleep quality.",
            "concepts": ["sleep"],
        }
    ]
    return {"labels": labels}


def _label_args(tmp_path, config, **overrides):
    taxonomy = small_taxonomy()
    taxonomy["schema_version"] = labeling.SCHEMA_VERSION
    taxonomy["taxonomy_sha256"] = labeling.sha256_bytes(
        labeling.canonical_json(taxonomy["labels"]).encode("utf-8")
    )
    taxonomy_path = tmp_path / "taxonomy.json"
    labeling.write_json(taxonomy_path, taxonomy)
    windows = [
        {
            "window_id": f"episode_1_window_{index:04d}",
            "episode_id": 1,
            "window_index": index,
            "units": [{"unit_id": "u000001", "text": "The guest discusses sleep."}],
        }
        for index in range(1, 7)
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
    return argparse.Namespace(
        output_dir=tmp_path,
        taxonomy=taxonomy_path,
        windows=windows_path,
        prepare_manifest=prepare_manifest_path,
        api_base=["http://127.0.0.1:8000/v1"],
        model=None,
        api_key_env=None,
        env_file=None,
        batch_size=1,
        concurrency=1,
        max_output_tokens=100,
        timeout=10,
        attempts=1,
        reasoning_effort="none",
        temperature=None,
        top_p=None,
        seed=None,
        usage_limits=config,
        provider="demo",
        experiment=None,
        config=tmp_path / "no-config.toml",
        **overrides,
    )


def _stub_endpoint(monkeypatch, output_tokens: int):
    """A server that always answers, so only the limiter can stop the run."""

    def fake_request(self, url, payload=None):
        if url.endswith("/models"):
            return {"data": [{"id": "local-model"}]}
        return {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "{}"}]}
            ],
            "usage": {"input_tokens": 0, "output_tokens": output_tokens},
        }

    monkeypatch.setattr(labeling.ResponsesClient, "_request", fake_request)
    monkeypatch.setattr(
        labeling,
        "validate_response",
        lambda parsed, windows, axes: [
            {
                "window_id": window["window_id"],
                "detections": [],
                "verification_candidates": [],
                "product_mentions": [],
            }
            for window in windows
        ],
    )


def test_a_spent_budget_stops_a_labeling_run_and_a_later_one_resumes(
    tmp_path, monkeypatch
):
    config = write_config(tmp_path, "[provider.demo]\ntokens_per_day = 25_000\n")
    _stub_endpoint(monkeypatch, output_tokens=10_000)

    stopped = labeling.run_label(_label_args(tmp_path, config))
    assert stopped["stopped_by_usage_limit"]
    assert 0 < stopped["windows_labeled"] < 6
    # Only the requests already in flight when the money ran out are recorded
    # as failures; the rest were never submitted and stay simply pending.
    assert 0 < stopped["unresolved_windows"] < 6 - stopped["windows_labeled"] + 1
    assert set(stopped["unresolved_windows_by_kind"]) == {"budget_exceeded"}

    # Raising the allocation and running again finishes the same run: the
    # windows that ran out of money are still pending, not lost.
    write_config(tmp_path, "[provider.demo]\ntokens_per_day = 10_000_000\n")
    finished = labeling.run_label(_label_args(tmp_path, config))
    assert finished["stopped_by_usage_limit"] is None
    assert finished["windows_labeled"] == 6
    assert finished["unresolved_windows"] == 0

    limiter = limits.UsageLimiter.from_config(config)
    assert limiter.report(group_by="provider")[0]["provider"] == "demo"
    assert limiter._conn.execute("SELECT count(*) FROM leases").fetchone()[0] == 0
    limiter.close()


def test_a_long_request_reconciles_into_the_minute_it_started_in(tmp_path):
    """Refunding an over-estimate must not credit a minute that never spent it."""
    limiter, clock = make_limiter(
        tmp_path,
        """
[provider.demo]
output_tokens_per_minute = 1_000
""",
    )
    with limiter.reserve(provider="demo", model="m1", output_tokens=900) as lease:
        clock.now += 180  # a request that outlives its own minute, as these do
        lease.record({"input_tokens": 0, "output_tokens": 100})
    # The refund landed on the first minute; this one is untouched, so it still
    # has its whole allowance rather than 800 tokens of somebody else's.
    assert limiter.status()[0]["used"] == 0
    assert limiter._conn.execute("SELECT min(value) FROM counters").fetchone()[0] == 100
