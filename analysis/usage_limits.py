#!/usr/bin/env python3
"""Client-side usage limits and per-experiment budgets for paid model APIs.

A local vLLM server bills nothing, so the labeling pipeline never had to count
what it sends. A paid endpoint changes that: a retry loop, a mistyped batch
size, or two experiments started in two terminals can spend real money with
nothing standing in the way. This module is what stands in the way.

The whole system is one idea applied three times. Every request is charged to a
set of *scopes* -- the provider, the specific model, and the experiment when the
run names one -- and a scope carries limits. Per-provider, per-model and
per-experiment limits are therefore the same mechanism with three different
keys, which is why there is so little code here.

A limit is named ``<meter>_<window>``:

    meters   requests, input_tokens, uncached_input_tokens, output_tokens,
             tokens (input + output), cost (US dollars)
    windows  per_minute, per_day, total

plus ``max_concurrent``, which counts in-flight requests rather than a window.
So ``cost_per_day``, ``output_tokens_per_minute`` and ``cost_total`` all mean
what they look like they mean, and Fireworks' three published serverless limits
map onto ``input_tokens_per_minute`` (their total prompt TPM),
``uncached_input_tokens_per_minute`` and ``output_tokens_per_minute``.

Rates and budgets fail differently, because their remedies differ:

  * ``max_concurrent`` and ``*_per_minute`` are rates. Hitting one parks the
    caller until the window rolls over -- that is what a throttle is for.
  * ``*_per_day`` and ``*_total`` are budgets. Hitting one raises
    ``BudgetExceeded`` at once, because sleeping until midnight is not a useful
    thing for a run to do. Every caller in this repository checkpoints, so the
    answer to a spent budget is to stop and resume later.

Token counts are only known *after* a request, so a reservation is taken before
it from the caller's estimate and reconciled against the reported usage
afterwards. Without the reservation a hundred concurrent requests would all read
the same nearly-exhausted budget and all pass it. A request that never reports
usage keeps its estimate: over-counting a failure is the safe direction, since
a request that timed out server-side was still generated and still billed.

State lives in one SQLite file, so a limit holds across threads, across
processes and across days. Two tables do two jobs: ``counters`` is the
enforcement state -- one indexed row per (scope, limit, window bucket) -- and
``requests`` is the audit ledger, one row per request, which is what the
``report`` command reads and the thing to trust when the two ever disagree.

Nothing here is specific to one provider or to the labeling pipeline:

    limiter = UsageLimiter.from_config(Path("analysis/usage-limits.toml"),
                                       experiment="topic-pilot-a")
    with limiter.reserve(provider="fireworks", model="...",
                         input_tokens=est_in, output_tokens=budget) as lease:
        response = call_the_api()
        lease.record(response.get("usage"))

Commands:

    python analysis/usage_limits.py status
    python analysis/usage_limits.py report --experiment topic-pilot-a
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import threading
import time
import tomllib
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence


DEFAULT_CONFIG = Path("analysis/usage-limits.toml")
DEFAULT_DATABASE = Path("analysis/output/usage-limits.sqlite")
# A reservation only has to land in the right ballpark -- the reported usage
# replaces it as soon as the request returns -- so callers with nothing better
# may size one from the payload. Four characters per token is the usual rule of
# thumb for English prose and errs high on transcript text.
CHARS_PER_TOKEN = 4

METERS = (
    "requests",
    "input_tokens",
    "uncached_input_tokens",
    "output_tokens",
    "tokens",
    "cost",
)
WINDOW_SUFFIXES = {"per_minute": "minute", "per_day": "day", "total": "total"}
# Windows that clear on their own, so a caller can wait one out. Everything else
# is a budget, and waiting for it is the operator's decision, not the run's.
RATE_WINDOWS = ("minute",)
CONCURRENCY_LIMIT = "max_concurrent"
LIMIT_WINDOWS = {
    f"{meter}_{suffix}": (meter, window)
    for meter in METERS
    for suffix, window in WINDOW_SUFFIXES.items()
}
PRICE_KEYS = ("input_per_mtok", "output_per_mtok", "cached_input_per_mtok")
SETTINGS_KEYS = ("database", "lease_seconds", "max_wait_seconds", "poll_seconds")
SECTIONS = ("settings", "provider", "model", "experiment")
# Ledger value for a request no experiment claimed. Stored rather than NULL so
# that grouping and the "did anything escape attribution" question are one query.
UNATTRIBUTED = "(unattributed)"
# Minute counters are dead the moment their minute passes. Kept well beyond any
# plausible request timeout all the same, because a request reconciles into the
# minute it started in, and that bucket has to still be there when it does.
MINUTE_COUNTER_GRACE = 7200.0
PRUNE_EVERY = 512

SCHEMA = """
CREATE TABLE IF NOT EXISTS counters (
    scope  TEXT NOT NULL,
    meter  TEXT NOT NULL,
    window TEXT NOT NULL,
    bucket TEXT NOT NULL,
    value  REAL NOT NULL,
    PRIMARY KEY (scope, meter, window, bucket)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS leases (
    lease_id   TEXT NOT NULL,
    scope      TEXT NOT NULL,
    expires_at REAL NOT NULL,
    PRIMARY KEY (lease_id, scope)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_leases_scope ON leases(scope);

CREATE TABLE IF NOT EXISTS requests (
    request_id          TEXT PRIMARY KEY,
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    day                 TEXT NOT NULL,
    experiment          TEXT NOT NULL,
    provider            TEXT NOT NULL,
    model               TEXT NOT NULL,
    outcome             TEXT NOT NULL,
    input_tokens        REAL NOT NULL,
    cached_input_tokens REAL NOT NULL,
    output_tokens       REAL NOT NULL,
    cost_usd            REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_requests_day ON requests(day);
CREATE INDEX IF NOT EXISTS idx_requests_experiment ON requests(experiment, day);
"""


class UsageLimitError(RuntimeError):
    """A limit stopped a request, or the limiter is misconfigured.

    ``kind`` mirrors ``topic_labeling.TopicLabelingError``: the labeling stores
    aggregate failures by kind, so a run stopped by its budget is legible in the
    manifest without reading a thousand free-text messages.
    """

    kind = "usage_limit"


class BudgetExceeded(UsageLimitError):
    """A per-day or lifetime allocation is spent; waiting will not help."""

    kind = "budget_exceeded"

    def __init__(self, message: str, *, scope: str, limit: str) -> None:
        super().__init__(message)
        self.scope = scope
        self.limit = limit


class RateLimitTimeout(UsageLimitError):
    """A rate limit did not clear inside ``max_wait_seconds``."""

    kind = "rate_limit_timeout"


@dataclass(frozen=True)
class Price:
    """What a model costs, in US dollars per million tokens.

    Prices are configuration, never a built-in table: a stale hardcoded price
    would silently mis-state every budget in the file, and providers change them
    without asking.
    """

    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float | None = None

    def cost(self, usage: Usage) -> float:
        billed_input = usage.input_tokens
        total = 0.0
        if self.cached_input_per_mtok is not None:
            billed_input -= usage.cached_input_tokens
            total += usage.cached_input_tokens * self.cached_input_per_mtok
        total += billed_input * self.input_per_mtok
        total += usage.output_tokens * self.output_per_mtok
        return total / 1_000_000


@dataclass(frozen=True)
class Usage:
    """Tokens attributable to one request.

    ``input_tokens`` is the whole prompt, cached part included, which is how
    OpenAI-compatible providers report it and how Fireworks' "total prompt"
    limit counts it. ``parse`` converts the other conventions into this one.
    """

    input_tokens: float = 0.0
    output_tokens: float = 0.0
    cached_input_tokens: float = 0.0

    @property
    def uncached_input_tokens(self) -> float:
        return max(self.input_tokens - self.cached_input_tokens, 0.0)

    def meters(self, price: Price | None) -> dict[str, float]:
        """Every meter this usage moves, keyed as the limit names key them."""
        values = {
            "requests": 1.0,
            "input_tokens": self.input_tokens,
            "uncached_input_tokens": self.uncached_input_tokens,
            "output_tokens": self.output_tokens,
            "tokens": self.input_tokens + self.output_tokens,
        }
        if price is not None:
            values["cost"] = price.cost(self)
        return values

    @classmethod
    def parse(cls, usage: Any) -> Usage | None:
        """Read a provider's usage object, whichever dialect it speaks.

        Three are in circulation: the Responses API's ``input_tokens`` with
        ``input_tokens_details.cached_tokens``, Chat Completions'
        ``prompt_tokens``/``completion_tokens``, and Anthropic's, where
        ``input_tokens`` *excludes* the cached reads reported beside it. Getting
        that last one wrong would under-count a cached prompt by its whole
        cached prefix, so it is detected rather than assumed.

        Cache *writes* are billed above the uncached rate on some providers and
        are counted here at the uncached rate, which understates a cache-heavy
        first request slightly. Returns None when there is nothing usable, which
        leaves the caller's reservation standing.
        """
        if not isinstance(usage, Mapping):
            return None

        def number(value: Any) -> float:
            return (
                float(value)
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else 0.0
            )

        if "cache_read_input_tokens" in usage or "cache_creation_input_tokens" in usage:
            cached = number(usage.get("cache_read_input_tokens"))
            written = number(usage.get("cache_creation_input_tokens"))
            return cls(
                input_tokens=number(usage.get("input_tokens")) + cached + written,
                output_tokens=number(usage.get("output_tokens")),
                cached_input_tokens=cached,
            )
        details = (
            usage.get("input_tokens_details")
            or usage.get("prompt_tokens_details")
            or {}
        )
        cached = (
            number(details.get("cached_tokens"))
            if isinstance(details, Mapping)
            else 0.0
        )
        input_tokens = number(usage.get("input_tokens")) or number(
            usage.get("prompt_tokens")
        )
        output_tokens = number(usage.get("output_tokens")) or number(
            usage.get("completion_tokens")
        )
        if not (input_tokens or output_tokens):
            return None
        return cls(input_tokens, output_tokens, min(cached, input_tokens))


@dataclass(frozen=True)
class Scope:
    """One key requests are charged to, and the limits it carries."""

    key: str
    limits: Mapping[str, float]


@dataclass(frozen=True)
class Violation:
    scope: str
    limit: str
    window: str
    allowed: float
    current: float
    requested: float

    @property
    def is_budget(self) -> bool:
        return self.window not in RATE_WINDOWS and self.window != "concurrent"

    def describe(self) -> str:
        return (
            f"{self.scope} {self.limit}: {_number_text(self.current)} used"
            f" + {_number_text(self.requested)} requested exceeds"
            f" {_number_text(self.allowed)}"
        )


@dataclass(frozen=True)
class LimitsConfig:
    path: Path
    database: Path
    lease_seconds: float
    max_wait_seconds: float
    poll_seconds: float
    providers: Mapping[str, Mapping[str, float]]
    models: Mapping[str, Mapping[str, float]]
    prices: Mapping[str, Price]
    experiments: Mapping[str, Mapping[str, float]]

    def scopes(self, provider: str, model: str, experiment: str | None) -> list[Scope]:
        """The scopes one request is charged to, outermost first.

        An undeclared provider or experiment is an error rather than an
        unlimited default. The point of the file is that spending is deliberate,
        and a typo in ``--provider`` must not be the thing that buys an
        unmetered run.
        """
        if provider not in self.providers:
            raise UsageLimitError(
                f"{self.path}: provider {provider!r} is not declared; add a "
                f"[provider.{provider}] table (an empty one means no limits)"
            )
        scopes = [Scope(f"provider:{provider}", self.providers[provider])]
        key = f"{provider}/{model}"
        if key in self.models:
            scopes.append(Scope(f"model:{key}", self.models[key]))
        if experiment:
            if experiment not in self.experiments:
                raise UsageLimitError(
                    f"{self.path}: experiment {experiment!r} is not declared; add an "
                    f'[experiment."{experiment}"] table with its allocation'
                )
            scopes.append(
                Scope(f"experiment:{experiment}", self.experiments[experiment])
            )
        return scopes

    def declared_scopes(self) -> list[Scope]:
        """Every scope in the file, for reporting."""
        return [
            *(
                Scope(f"provider:{name}", limits)
                for name, limits in self.providers.items()
            ),
            *(Scope(f"model:{name}", limits) for name, limits in self.models.items()),
            *(
                Scope(f"experiment:{name}", limits)
                for name, limits in self.experiments.items()
            ),
        ]


def _number(section: str, key: str, value: Any, *, minimum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UsageLimitError(
            f"{section}: {key} must be a number, not {type(value).__name__}"
        )
    if value < minimum:
        raise UsageLimitError(
            f"{section}: {key} must be at least {minimum}, not {value}"
        )
    return float(value)


def _read_table(
    section: str, table: Mapping[str, Any], *, priced: bool
) -> tuple[dict[str, float], Price | None]:
    """Split one scope's table into its limits and, for a model, its price."""
    limits: dict[str, float] = {}
    price_values: dict[str, float] = {}
    for key, value in table.items():
        if key == CONCURRENCY_LIMIT:
            limit = _number(section, key, value, minimum=1)
            if limit != int(limit):
                raise UsageLimitError(
                    f"{section}: {key} must be a whole number of requests"
                )
            limits[key] = limit
        elif key in LIMIT_WINDOWS:
            limits[key] = _number(section, key, value, minimum=0)
            if limits[key] <= 0:
                raise UsageLimitError(f"{section}: {key} must be positive")
        elif priced and key in PRICE_KEYS:
            price_values[key] = _number(section, key, value, minimum=0)
        else:
            known = sorted(
                {CONCURRENCY_LIMIT, *LIMIT_WINDOWS, *(PRICE_KEYS if priced else ())}
            )
            raise UsageLimitError(
                f"{section}: unknown setting {key!r}; expected one of {known}"
            )
    price = None
    if price_values:
        missing = {"input_per_mtok", "output_per_mtok"} - set(price_values)
        if missing:
            raise UsageLimitError(f"{section}: a price also needs {sorted(missing)}")
        price = Price(**price_values)
    return limits, price


def load_config(path: Path) -> LimitsConfig:
    """Read and fully validate the limits file.

    Everything is checked here rather than at the first request, because the
    first request may be an hour into a run and the failure it would produce is
    the expensive kind.
    """
    path = Path(path)
    try:
        with path.open("rb") as handle:
            parsed = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise UsageLimitError(f"{path} is not valid TOML: {exc}") from exc
    unknown = sorted(set(parsed) - set(SECTIONS))
    if unknown:
        raise UsageLimitError(
            f"{path}: unknown table(s) {unknown}; expected {list(SECTIONS)}"
        )

    settings = parsed.get("settings", {})
    unknown = sorted(set(settings) - set(SETTINGS_KEYS))
    if unknown:
        raise UsageLimitError(f"{path}: unknown [settings] key(s) {unknown}")
    # Relative to the working directory, as every other path in this
    # repository's config files is; the commands are all run from the root.
    location = settings.get("database", DEFAULT_DATABASE)
    if not isinstance(location, (str, Path)):
        raise UsageLimitError(
            f"{path}: [settings] database must be a path, not "
            f"{type(location).__name__}"
        )
    database = Path(location)

    providers: dict[str, dict[str, float]] = {}
    for name, table in parsed.get("provider", {}).items():
        if not isinstance(table, Mapping):
            raise UsageLimitError(f"{path}: [provider.{name}] must be a table")
        providers[name], _ = _read_table(
            f"{path} [provider.{name}]", table, priced=False
        )

    models: dict[str, dict[str, float]] = {}
    prices: dict[str, Price] = {}
    for provider, entries in parsed.get("model", {}).items():
        if not isinstance(entries, Mapping) or any(
            not isinstance(value, Mapping) for value in entries.values()
        ):
            raise UsageLimitError(
                f"{path}: models are declared per provider, as "
                f'[model.{provider}."<model id>"]'
            )
        if provider not in providers:
            raise UsageLimitError(
                f"{path}: [model.{provider}.*] names a provider with no "
                f"[provider.{provider}] table"
            )
        for model, table in entries.items():
            section = f'{path} [model.{provider}."{model}"]'
            key = f"{provider}/{model}"
            models[key], price = _read_table(section, table, priced=True)
            if price is not None:
                prices[key] = price

    experiments: dict[str, dict[str, float]] = {}
    for name, table in parsed.get("experiment", {}).items():
        if not isinstance(table, Mapping):
            raise UsageLimitError(f"{path}: [experiment.{name}] must be a table")
        experiments[name], _ = _read_table(
            f'{path} [experiment."{name}"]', table, priced=False
        )

    return LimitsConfig(
        path=path,
        database=database,
        lease_seconds=_number(
            str(path), "lease_seconds", settings.get("lease_seconds", 1800), minimum=1
        ),
        max_wait_seconds=_number(
            str(path),
            "max_wait_seconds",
            settings.get("max_wait_seconds", 900),
            minimum=0,
        ),
        poll_seconds=_number(
            str(path), "poll_seconds", settings.get("poll_seconds", 0.25), minimum=0.01
        ),
        providers=providers,
        models=models,
        prices=prices,
        experiments=experiments,
    )


def bucket_key(window: str, now: float) -> str:
    """The counter row a charge lands in.

    Fixed calendar buckets rather than sliding windows: one indexed row per
    limit instead of a scan over an event log, and "tokens per day" then means
    the same UTC day the reports group by. The price is the usual fixed-window
    burst -- a run can spend a minute's allowance either side of a boundary --
    which is the right trade for a client-side guard whose job is to keep
    spending in the right order of magnitude, not to shape traffic to the
    provider's own meter.
    """
    if window == "total":
        return "*"
    stamp = datetime.fromtimestamp(now, UTC)
    return stamp.strftime("%Y-%m-%d" if window == "day" else "%Y-%m-%dT%H:%M")


class Lease:
    """One request's claim on every scope that limits it.

    Created by ``UsageLimiter.reserve`` with the caller's estimate already
    charged. ``record`` supplies the truth; closing reconciles the difference,
    releases the concurrency slots and closes the ledger row -- one transaction,
    whether the request succeeded or raised.
    """

    def __init__(
        self,
        limiter: UsageLimiter | None = None,
        *,
        lease_id: str = "",
        scopes: Sequence[Scope] = (),
        price: Price | None = None,
        estimate: Usage = Usage(),
        reserved_at: float = 0.0,
    ) -> None:
        self._limiter = limiter
        self.lease_id = lease_id
        self.reserved_at = reserved_at
        self._scopes = tuple(scopes)
        self._price = price
        self._estimate = estimate
        self._actual: Usage | None = None
        self._closed = False

    def record(self, usage: Any) -> Usage | None:
        """Replace the estimate with what the provider says it charged.

        Takes a raw usage object in any of the dialects ``Usage.parse`` knows,
        or a ``Usage``. Unparseable usage is ignored, which leaves the estimate
        standing.
        """
        parsed = usage if isinstance(usage, Usage) else Usage.parse(usage)
        if parsed is not None:
            self._actual = parsed
        return parsed

    @property
    def charged(self) -> Usage:
        return self._actual if self._actual is not None else self._estimate

    def close(self) -> None:
        if self._closed or self._limiter is None:
            self._closed = True
            return
        self._closed = True
        self._limiter._release(self)


class UsageLimiter:
    """Enforces the limits in one config file against one shared ledger.

    Safe to share across threads, and correct across processes: every check and
    charge happens inside one ``BEGIN IMMEDIATE`` transaction, so two runs
    cannot both read the same remaining budget and both spend it. Constructed
    without a config it is inert, which is what keeps free local endpoints free
    of all of this.
    """

    def __init__(
        self,
        config: LimitsConfig | None,
        experiment: str | None = None,
        *,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.experiment = experiment or None
        self.clock = clock
        self.sleep = sleep
        self._lock = threading.Lock()
        self._acquisitions = 0
        self._conn: sqlite3.Connection | None = None
        if config is None:
            if self.experiment:
                raise UsageLimitError(
                    "an experiment needs a usage-limits config to declare its allocation"
                )
            return
        if self.experiment and self.experiment not in config.experiments:
            raise UsageLimitError(
                f"{config.path}: experiment {self.experiment!r} is not declared; add an "
                f'[experiment."{self.experiment}"] table with its allocation'
            )
        config.database.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            config.database, check_same_thread=False, isolation_level=None
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        # The ledger is the record of money spent; a lost write is an
        # under-count, which is the direction that costs something.
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._conn.executescript(SCHEMA)
        self._prune(self.clock())

    @classmethod
    def from_config(
        cls, path: Path | None, experiment: str | None = None, **kwargs: Any
    ) -> UsageLimiter:
        """Build a limiter from a config file, or an inert one from ``None``.

        A path that was asked for and does not exist is an error: silently
        running unmetered is the failure this module exists to prevent.
        """
        if path is None:
            return cls(None, experiment, **kwargs)
        path = Path(path)
        if not path.exists():
            raise UsageLimitError(f"usage limits config {path} does not exist")
        return cls(load_config(path), experiment, **kwargs)

    @property
    def enabled(self) -> bool:
        return self._conn is not None

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- reservation -------------------------------------------------------

    @contextmanager
    def reserve(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: float = 0.0,
        output_tokens: float = 0.0,
        cached_input_tokens: float = 0.0,
        ttl: float | None = None,
    ) -> Iterator[Lease]:
        """Hold a slot and an estimated charge for the duration of one request.

        Blocks while a rate limit is in the way, raises ``BudgetExceeded`` when
        an allocation is spent, and always releases -- the estimate stands
        unless the body calls ``lease.record``.
        """
        if self.config is None:
            yield Lease()
            return
        estimate = Usage(
            float(input_tokens), float(output_tokens), float(cached_input_tokens)
        )
        scopes = self.config.scopes(provider, model, self.experiment)
        price = self.config.prices.get(f"{provider}/{model}")
        if price is None and any(
            LIMIT_WINDOWS.get(name, (None,))[0] == "cost"
            for scope in scopes
            for name in scope.limits
        ):
            raise UsageLimitError(
                f"a cost limit applies to {provider}/{model} but the model has no price; "
                f'add input_per_mtok and output_per_mtok under [model.{provider}."{model}"] '
                f"in {self.config.path}"
            )
        lease = self._acquire(scopes, provider, model, price, estimate, ttl)
        try:
            yield lease
        finally:
            lease.close()

    def _acquire(
        self,
        scopes: Sequence[Scope],
        provider: str,
        model: str,
        price: Price | None,
        estimate: Usage,
        ttl: float | None,
    ) -> Lease:
        assert self.config is not None and self._conn is not None
        amounts = estimate.meters(price)
        self._check_satisfiable(scopes, amounts)
        lease_id = uuid.uuid4().hex
        expiry = float(ttl if ttl is not None else self.config.lease_seconds)
        deadline = self.clock() + self.config.max_wait_seconds
        while True:
            now = self.clock()
            blocked = self._try_acquire(
                scopes, amounts, lease_id, now, expiry, provider, model, price, estimate
            )
            if blocked is None:
                return Lease(
                    self,
                    lease_id=lease_id,
                    scopes=scopes,
                    price=price,
                    estimate=estimate,
                    reserved_at=now,
                )
            budgets = [violation for violation in blocked if violation.is_budget]
            if budgets:
                raise BudgetExceeded(
                    "usage budget exhausted -- "
                    + "; ".join(v.describe() for v in budgets),
                    scope=budgets[0].scope,
                    limit=budgets[0].limit,
                )
            remaining = deadline - now
            if remaining <= 0:
                raise RateLimitTimeout(
                    f"waited {self.config.max_wait_seconds:g}s for a rate limit to clear -- "
                    + "; ".join(v.describe() for v in blocked)
                )
            self.sleep(min(self._backoff(blocked, now), remaining))

    def _backoff(self, blocked: Sequence[Violation], now: float) -> float:
        """How long to wait before looking again.

        A minute limit clears exactly on the minute, so sleep to the boundary
        instead of polling through it. A concurrency limit clears whenever some
        other request finishes, which nothing here can predict, so poll.
        """
        assert self.config is not None
        if any(violation.window == "minute" for violation in blocked):
            return max(60.0 - (now % 60.0) + 0.01, self.config.poll_seconds)
        return self.config.poll_seconds

    def _check_satisfiable(
        self, scopes: Sequence[Scope], amounts: Mapping[str, float]
    ) -> None:
        """Refuse a request no empty window could ever admit.

        Without this, a per-minute limit smaller than one request's estimate
        would park the caller until ``max_wait_seconds`` and then fail, once per
        request, forever -- a misconfiguration wearing a rate limit's clothes.
        """
        for scope in scopes:
            for name, allowed in scope.limits.items():
                if name == CONCURRENCY_LIMIT:
                    continue
                meter, window = LIMIT_WINDOWS[name]
                requested = amounts.get(meter)
                if (
                    requested is not None
                    and requested > allowed
                    and window in RATE_WINDOWS
                ):
                    raise UsageLimitError(
                        f"{scope.key} {name} is {_number_text(allowed)}, smaller than the "
                        f"{_number_text(requested)} this single request needs"
                    )

    def _try_acquire(
        self,
        scopes: Sequence[Scope],
        amounts: Mapping[str, float],
        lease_id: str,
        now: float,
        expiry: float,
        provider: str,
        model: str,
        price: Price | None,
        estimate: Usage,
    ) -> list[Violation] | None:
        """One atomic check-and-charge. Returns the violations, or None on success."""
        assert self.config is not None and self._conn is not None
        conn = self._conn
        with self._lock:
            conn.execute("BEGIN IMMEDIATE")
            try:
                # A process that died mid-request leaves its lease behind; the
                # expiry is what stops that from retiring a slot permanently.
                conn.execute("DELETE FROM leases WHERE expires_at <= ?", (now,))
                blocked = self._violations(scopes, amounts, now)
                if blocked:
                    conn.execute("ROLLBACK")
                    return blocked
                self._charge(scopes, amounts, now, sign=1.0)
                conn.executemany(
                    "INSERT INTO leases(lease_id, scope, expires_at) VALUES (?, ?, ?)",
                    [(lease_id, scope.key, now + expiry) for scope in scopes],
                )
                conn.execute(
                    """INSERT INTO requests(request_id, started_at, finished_at, day,
                           experiment, provider, model, outcome, input_tokens,
                           cached_input_tokens, output_tokens, cost_usd)
                       VALUES (?, ?, NULL, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
                    (
                        lease_id,
                        _timestamp(now),
                        bucket_key("day", now),
                        self.experiment or UNATTRIBUTED,
                        provider,
                        model,
                        estimate.input_tokens,
                        estimate.cached_input_tokens,
                        estimate.output_tokens,
                        price.cost(estimate) if price else 0.0,
                    ),
                )
                self._acquisitions += 1
                if self._acquisitions % PRUNE_EVERY == 0:
                    self._prune(now, in_transaction=True)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return None

    def _release(self, lease: Lease) -> None:
        """Reconcile the estimate against the truth and give the slots back."""
        assert self.config is not None and self._conn is not None
        conn = self._conn
        now = self.clock()
        recorded = lease._actual is not None
        actual = lease.charged
        before = lease._estimate.meters(lease._price)
        after = actual.meters(lease._price)
        delta = {meter: after[meter] - before[meter] for meter in after}
        with self._lock:
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Into the buckets the reservation went into, not the ones the
                # clock is in now. A request outlives the minute it started in,
                # so refunding an over-estimate against the current minute would
                # hand a later minute rate allowance it never earned, and could
                # drive that minute's counter below zero.
                self._charge(lease._scopes, delta, lease.reserved_at, sign=1.0)
                conn.execute("DELETE FROM leases WHERE lease_id = ?", (lease.lease_id,))
                conn.execute(
                    """UPDATE requests SET finished_at = ?, outcome = ?, input_tokens = ?,
                           cached_input_tokens = ?, output_tokens = ?, cost_usd = ?
                       WHERE request_id = ?""",
                    (
                        _timestamp(now),
                        "recorded" if recorded else "estimated",
                        actual.input_tokens,
                        actual.cached_input_tokens,
                        actual.output_tokens,
                        lease._price.cost(actual) if lease._price else 0.0,
                        lease.lease_id,
                    ),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    # -- counters ----------------------------------------------------------

    def _violations(
        self, scopes: Sequence[Scope], amounts: Mapping[str, float], now: float
    ) -> list[Violation]:
        assert self._conn is not None
        blocked: list[Violation] = []
        for scope in scopes:
            for name, allowed in sorted(scope.limits.items()):
                if name == CONCURRENCY_LIMIT:
                    active = self._active_leases(scope.key)
                    if active + 1 > allowed:
                        blocked.append(
                            Violation(scope.key, name, "concurrent", allowed, active, 1)
                        )
                    continue
                meter, window = LIMIT_WINDOWS[name]
                requested = amounts.get(meter)
                if requested is None:
                    continue
                current = self._counter(
                    scope.key, meter, window, bucket_key(window, now)
                )
                if current + requested > allowed:
                    blocked.append(
                        Violation(scope.key, name, window, allowed, current, requested)
                    )
        return blocked

    def _charge(
        self,
        scopes: Sequence[Scope],
        amounts: Mapping[str, float],
        now: float,
        *,
        sign: float,
    ) -> None:
        """Move every counter a declared limit watches.

        Only limited (scope, meter, window) triples get a counter: an unlimited
        meter would be dead weight in the hot path, and the ledger answers
        "what did this actually use" better than a counter would.
        """
        assert self._conn is not None
        for scope in scopes:
            for name in scope.limits:
                if name == CONCURRENCY_LIMIT:
                    continue
                meter, window = LIMIT_WINDOWS[name]
                amount = amounts.get(meter)
                if not amount:
                    continue
                self._conn.execute(
                    """INSERT INTO counters(scope, meter, window, bucket, value)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(scope, meter, window, bucket)
                       DO UPDATE SET value = value + excluded.value""",
                    (scope.key, meter, window, bucket_key(window, now), sign * amount),
                )

    def _counter(self, scope: str, meter: str, window: str, bucket: str) -> float:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT value FROM counters WHERE scope = ? AND meter = ? AND window = ? AND bucket = ?",
            (scope, meter, window, bucket),
        ).fetchone()
        return float(row[0]) if row else 0.0

    def _active_leases(self, scope: str) -> int:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT count(*) FROM leases WHERE scope = ?", (scope,)
        ).fetchone()
        return int(row[0])

    def _prune(self, now: float, *, in_transaction: bool = False) -> None:
        assert self._conn is not None
        cutoff = bucket_key("minute", now - MINUTE_COUNTER_GRACE)
        statements = (
            ("DELETE FROM counters WHERE window = 'minute' AND bucket < ?", (cutoff,)),
            ("DELETE FROM leases WHERE expires_at <= ?", (now,)),
        )
        if in_transaction:
            for sql, params in statements:
                self._conn.execute(sql, params)
            return
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                for sql, params in statements:
                    self._conn.execute(sql, params)
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise

    # -- reporting ---------------------------------------------------------

    def status(self) -> list[dict[str, Any]]:
        """Every declared limit, with what is currently against it."""
        if self.config is None or self._conn is None:
            return []
        now = self.clock()
        self._prune(now)
        rows: list[dict[str, Any]] = []
        with self._lock:
            for scope in self.config.declared_scopes():
                for name, allowed in sorted(scope.limits.items()):
                    if name == CONCURRENCY_LIMIT:
                        window, bucket = "concurrent", "now"
                        used = float(self._active_leases(scope.key))
                    else:
                        meter, window = LIMIT_WINDOWS[name]
                        bucket = bucket_key(window, now)
                        used = self._counter(scope.key, meter, window, bucket)
                    rows.append(
                        {
                            "scope": scope.key,
                            "limit": name,
                            "window": window,
                            "bucket": bucket,
                            "used": used,
                            "allowed": allowed,
                            "remaining": max(allowed - used, 0.0),
                            "used_pct": f"{100 * used / allowed:.1f}%"
                            if allowed
                            else "-",
                        }
                    )
        return rows

    def report(
        self,
        *,
        experiment: str | None = None,
        since: str | None = None,
        group_by: str = "day",
    ) -> list[dict[str, Any]]:
        """Spend from the ledger, which is the record of what really happened."""
        if self._conn is None:
            return []
        if group_by not in {"day", "model", "provider", "experiment", "outcome"}:
            raise UsageLimitError(f"cannot group a report by {group_by!r}")
        column = "provider || '/' || model" if group_by == "model" else group_by
        where, params = [], []
        if experiment:
            where.append("experiment = ?")
            params.append(experiment)
        if since:
            where.append("day >= ?")
            params.append(since)
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            query = self._conn.execute(
                f"""SELECT {column} AS grouped, count(*), sum(input_tokens),
                        sum(cached_input_tokens), sum(output_tokens), sum(cost_usd)
                    FROM requests{clause} GROUP BY grouped ORDER BY grouped""",
                params,
            ).fetchall()
        return [
            {
                group_by: row[0],
                "requests": int(row[1]),
                "input_tokens": float(row[2] or 0.0),
                "cached_input_tokens": float(row[3] or 0.0),
                "output_tokens": float(row[4] or 0.0),
                "cost_usd": float(row[5] or 0.0),
            }
            for row in query
        ]


def _timestamp(now: float) -> str:
    return (
        datetime.fromtimestamp(now, UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _number_text(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    if value and value < 1:
        return f"{value:.4f}"
    return f"{value:.0f}" if float(value).is_integer() else f"{value:.2f}"


def _print_table(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    if not rows:
        print("(nothing to report)")
        return
    cells = [[_cell(row[column]) for column in columns] for row in rows]
    widths = [
        max(len(str(column)), *(len(row[i]) for row in cells))
        for i, column in enumerate(columns)
    ]
    print("  ".join(column.ljust(widths[i]) for i, column in enumerate(columns)))
    for row in cells:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


def _cell(value: Any) -> str:
    if isinstance(value, float):
        return _number_text(value)
    return str(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON instead of a table"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Every declared limit and what is against it")

    report = subparsers.add_parser("report", help="Spend from the request ledger")
    report.add_argument("--experiment")
    report.add_argument("--since", help="Earliest UTC day to include, as YYYY-MM-DD")
    report.add_argument(
        "--by",
        default="day",
        choices=("day", "model", "provider", "experiment", "outcome"),
        dest="group_by",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    limiter = None
    try:
        limiter = UsageLimiter.from_config(args.config)
        if args.command == "status":
            rows = limiter.status()
            columns = (
                "scope",
                "limit",
                "bucket",
                "used",
                "allowed",
                "remaining",
                "used_pct",
            )
        else:
            rows = limiter.report(
                experiment=args.experiment, since=args.since, group_by=args.group_by
            )
            columns = (
                args.group_by,
                "requests",
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "cost_usd",
            )
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            _print_table(rows, columns)
        return 0
    except (UsageLimitError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        if limiter is not None:
            limiter.close()


if __name__ == "__main__":
    raise SystemExit(main())
