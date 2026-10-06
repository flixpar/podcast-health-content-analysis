"""Window labeling with TypeSafe's System One API (``label --api typesafe``).

A System One model (Jev) does not generate text. It reads a ``state`` and
answers typed questions about it -- here only ``noul`` (the probability that a
yes/no condition holds) and ``choice`` (a distribution over named options). So
this is not a third request shape for the rubric-and-schema prompt; it is a
different labeling method with the same output contract:

1. **Screen.** One request over the whole window asks one presence question per
   taxonomy label, plus gates for checkable claims and named products. A window
   where nothing clears the fan-out threshold ends here.
2. **Localize.** For every label that cleared it, one question per passage asks
   whether *that passage* carries the label; claims and products are asked per
   unit. Passages are keyed (``passages.p007``) because Jev resolves a named key
   reliably and an array index poorly -- indexing is counting. Definitions go
   into the state once and questions refer to them by key, which halves the
   tokens at no measured cost.
3. **Compose.** Code, not the model, turns per-unit probabilities into spans
   (seed, extend, bridge), which is the codebook's splitting rule made
   deterministic.
4. **Attribute.** One request over the composed spans asks the closed-set
   fields: discourse role, relevance, claim type, expressed certainty, product
   type, mention role, and whether each code-extracted candidate name is a
   product.

Everything the schema wants as free text is either copied from the transcript
or templated: ``evidence_quote`` is the highest-probability unit, ``claim_text``
is the claim's own span verbatim (so pronouns are *not* resolved), and
``summary`` and ``rationale`` are fixed templates. ``certainty_markers`` are
selected from lexicon hits inside the span, never written.

The raw probabilities are returned beside the result (``judgments``) and kept in
a sidecar, because every threshold below is policy: ``compose_result`` rebuilds a
result from stored judgments under a different :class:`Policy` with no requests.

This module deliberately imports nothing from ``topic_labeling``: that file runs
both as a script and as a package module, and importing it from here would load
it twice. The pipeline hands in the one thing this needs, a function that sends
a request.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Callable, Iterable, Mapping, Sequence

METHOD_VERSION = "typesafe-cascade-v1"
DEFAULT_API_BASE = "https://api.typesafe.ai/v1"
# Pinned rather than ``jev-latest``: the alias moves with each release, and the
# thresholds in Policy were tuned against this version's probabilities.
DEFAULT_MODEL = "jev-1.13.0"
ROUTE = "/systemone"

# Jev's documented limits are 64k tokens for state plus all questions and 32k
# for state plus the longest question. Token counts are only known after the
# fact, so requests are packed against a character estimate with headroom.
REQUEST_TOKEN_BUDGET = 52_000
STATE_TOKEN_BUDGET = 26_000
CHARS_PER_TOKEN_ESTIMATE = 3.2
# Tokens a question costs beyond its own text (measured: ~20 for a bare noul).
QUESTION_OVERHEAD_TOKENS = 12

AXES = ("topic", "frame", "evidence")
OTHER_TOPIC = "topic:other_health_topic"

DISCOURSE_ROLES = {
    "asserted_or_endorsed": "The speakers state it as their own view, agree with it, or simply discuss it in the ordinary way.",
    "questioned": "The speakers raise it with doubt or put it as an open question.",
    "reported_or_quoted": "It is attributed to someone else and is neither endorsed nor rejected.",
    "rebutted": "The speakers argue against it, correct it or debunk it.",
    "unclear": "It is genuinely impossible to tell what the speakers do with it.",
}
RELEVANCE = {
    "substantive": "The subject is discussed, explained or argued, not just named.",
    "passing": "The subject is only named in passing: an aside, an analogy, a joke or a one-line mention.",
    "advertisement": "The span is inside an advertising read: a sponsor read, a promo code, or a host reading ad copy.",
}
CLAIM_TYPES = {
    "causal": "X brings about, worsens or prevents Y.",
    "treatment_or_prevention": "Doing or taking X helps, cures or protects.",
    "risk_or_safety": "X is dangerous, harmful or safe.",
    "diagnosis_or_prevalence": "How common a condition is, who has it, or how it is recognised or diagnosed.",
    "mechanism": "How something works in the body, or a stated composition, quantity or physiological process.",
    "institutional_or_conspiracy": "About the conduct of institutions: an agency, company, profession or government hid, falsified, suppressed or was paid for something.",
    "other_factual": "A checkable factual claim that fits none of the other options.",
}
PRODUCT_TYPES = {
    "supplement": "A dietary supplement, vitamin, powder or nutraceutical brand.",
    "medication": "A brand-name drug or prescription product.",
    "food_or_beverage": "A food, drink or meal brand.",
    "device_or_wearable": "A physical device, wearable or piece of equipment.",
    "test_or_diagnostic": "A lab test, screening or diagnostic service.",
    "app_or_digital_service": "An app, online platform or telehealth service.",
    "clinic_or_practitioner_service": "A clinic, practice or practitioner's service.",
    "program_or_course": "A programme, course, membership or coaching offer.",
    "book_or_media": "A book, film, podcast or other media title.",
    "personal_care_or_cosmetic": "A skincare, cosmetic or personal-care product.",
    "other_product": "A specific product of a kind not listed.",
}
MENTION_ROLES = {
    "advertised": "A paid or sponsor read, a discount code or an affiliate offer.",
    "own_product": "The host's or guest's own product, clinic, programme or book.",
    "recommended": "Endorsed or suggested with no sign of payment.",
    "neutral": "Named without a stance, as an example or in passing.",
    "criticized": "Named to warn against it, mock it or dispute it.",
}
CERTAINTY_LEVELS = {
    "absolute": "Boosted or universal: the listed words make the claim certain, total or without exception.",
    "hedged": "Softened but still asserted: the listed words qualify how sure or how general the claim is.",
    "speculative": "Offered only as a possibility or an open question.",
}
UNHEDGED = "unhedged"
UNHEDGED_DESCRIPTION = (
    "A plain statement: none of the listed words boosts or softens the claim itself."
)

# The codebook's marker lists, a little extended. These are candidates only: a
# hit becomes a marker when Jev picks the level it belongs to, so "may" the
# month or "never" in "I never said" costs a question, not an error. "can" is
# left out on purpose -- the reference annotators coded it three ways.
CERTAINTY_MARKERS: dict[str, tuple[str, ...]] = {
    "absolute": (
        "definitely", "always", "never", "every single", "there is no doubt",
        "no doubt", "proven", "100%", "guaranteed", "absolutely", "without question",
        "undeniably", "certainly", "for sure", "completely", "totally", "no question",
        "everyone", "everybody", "nobody", "no one", "the only", "literally every",
    ),
    "hedged": (
        "probably", "likely", "i think", "i believe", "tends to", "tend to",
        "in most people", "generally", "usually", "often", "typically", "seems to",
        "seem to", "appears to", "appear to", "in my opinion", "for the most part",
        "most people", "many people", "pretty much", "suggests", "suggest",
        "in general", "more or less", "i would say", "i'd say",
    ),
    "speculative": (
        "might", "may", "could", "maybe", "perhaps", "possibly", "i wonder",
        "some people say", "i'm not sure", "potentially", "it's possible",
        "supposedly", "allegedly", "who knows", "i don't know",
    ),
}
MAX_CERTAINTY_MARKERS = 6

MAX_DETECTIONS = 40
MAX_CLAIMS = 30
MAX_PRODUCTS = 30
MAX_NAME_CANDIDATES = 24

_SPEAKER_PREFIX = re.compile(r"^\s*(?:Speaker\s*\d+|[A-Z][A-Za-z .'-]{1,40})\s*:\s+")
_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s*$")
_NAME_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'&+-]*")
# Words that are capitalised only because they open a sentence or a turn.
_NAME_STOPWORDS = frozenset(
    """a an and are as at be because but by do does for from had has have he her here
    his how i i'd i'll i'm i've if in is it it's its just let like look my no not now
    of oh ok okay on one or our right she so speaker thank thanks that that's the their
    then there these they this those to today um uh very was we we're well were what
    when where which who why with yeah yes you you're your all also check every get go
    keep try use visit""".split()
)


class TypeSafeMethodError(RuntimeError):
    """A window the method cannot label; ``kind`` aggregates like the pipeline's own."""

    def __init__(self, message: str, kind: str = "typesafe_method") -> None:
        super().__init__(message)
        self.kind = kind


def _per_axis(topic: float, frame: float, evidence: float) -> dict[str, float]:
    return {"topic": topic, "frame": frame, "evidence": evidence}


def require_flat_taxonomy(taxonomy: Mapping[str, Any]) -> None:
    """The cascade implements the flat topic/frame/evidence claim contract."""
    axes = {label["axis"] for label in taxonomy["labels"]}
    if (taxonomy.get("format", "").startswith("hierarchical")
            or taxonomy.get("schema_version", "topic-labeling-v4") != "topic-labeling-v4"
            or not axes.issubset({"topic", "frame", "evidence"})):
        raise TypeSafeMethodError(
            "TypeSafe supports the legacy flat topic/frame/evidence taxonomy only; "
            "hierarchical v7/v8 requires the generative labeling pipeline. "
            "Prepare with --topics docs/original/topics.md or use the flat benchmark spec.",
            kind="unsupported_taxonomy",
        )


@dataclass(frozen=True)
class Policy:
    """Every knob of the method. All of it is in the run fingerprint.

    The first block decides which questions are asked, so changing it means new
    requests. The second only decides how answers become annotations, so a
    stored ``judgments`` sidecar can be recomposed under new values for free.
    The defaults were tuned on the benchmark's dev split (docs/typesafe-labeling.md).
    """

    # -- what is asked ------------------------------------------------------
    # Units per localization passage, by axis. Topics run long, so a coarser
    # grid costs a third of the questions and scores the same; frames and
    # evidence signals are often one clause, so they are asked unit by unit.
    passage_units: dict[str, int] = field(
        default_factory=lambda: {"topic": 3, "frame": 1, "evidence": 1}
    )
    # Example terms from the taxonomy in the screening questions.
    screen_examples: bool = True
    # A label is localized when its screening probability reaches this. Low on
    # purpose: a label dropped here can never be recovered by recomposing.
    fanout_threshold: float = 0.3
    max_fanout_labels: int = 30
    # A window whose "any health content?" gate is below this is empty, and is
    # not localized at all. It is the method's false-positive floor: label
    # presence questions fire on figures of speech ("my brain is fried") that
    # this one question, asked about the window as a whole, does not.
    health_gate_threshold: float = 0.2
    # Claim and product unit questions are asked when their gate reaches this.
    gate_threshold: float = 0.1
    # Units of context shown on each side of a span in the attribute request.
    context_units: int = 2

    # -- how answers become annotations -------------------------------------
    # The screening probability a label needs for any of its spans to be kept.
    window_threshold: dict[str, float] = field(
        default_factory=lambda: _per_axis(0.3, 0.5, 0.7)
    )
    # A span needs one unit at ``seed`` and grows over neighbours at ``extend``.
    seed_threshold: dict[str, float] = field(
        default_factory=lambda: _per_axis(0.6, 0.6, 0.7)
    )
    extend_threshold: dict[str, float] = field(
        default_factory=lambda: _per_axis(0.5, 0.2, 0.2)
    )
    # Spans of one label this many units apart or closer are one span.
    bridge_units: dict[str, int] = field(
        default_factory=lambda: {"topic": 0, "frame": 1, "evidence": 1}
    )
    claim_threshold: float = 0.6
    # A claim unit that does not end a sentence joins the next claim unit.
    max_claim_units: int = 3
    product_threshold: float = 0.6
    product_bridge_units: int = 1
    # A candidate name becomes a product mention at this probability.
    product_name_threshold: float = 0.7
    # Keep a product only where a topic span reaches it. The codebook records
    # products "named inside a stretch of health content"; the product question
    # is about names, not health, so without this every brand in a show is kept
    # (dev precision 0.44 without it, 0.65 with it, recall unchanged).
    product_needs_topic: bool = True

    @classmethod
    def from_mapping(cls, overrides: Mapping[str, Any] | None) -> Policy:
        overrides = dict(overrides or {})
        known = {item.name: item for item in fields(cls)}
        unknown = sorted(set(overrides) - set(known))
        if unknown:
            raise TypeSafeMethodError(
                f"unknown typesafe policy keys: {unknown}", kind="invalid_policy"
            )
        defaults = cls()
        values: dict[str, Any] = {}
        for name, value in overrides.items():
            default = getattr(defaults, name)
            if isinstance(default, dict):
                # A bare number applies to every axis; a table overrides per axis.
                if isinstance(value, Mapping):
                    extra = sorted(set(value) - set(default))
                    if extra:
                        raise TypeSafeMethodError(
                            f"typesafe policy {name}: unknown axes {extra}",
                            kind="invalid_policy",
                        )
                    value = {**default, **value}
                else:
                    value = {axis: value for axis in default}
                value = {axis: type(default[axis])(number) for axis, number in value.items()}
            elif isinstance(default, bool):
                if not isinstance(value, bool):
                    raise TypeSafeMethodError(
                        f"typesafe policy {name} must be true or false",
                        kind="invalid_policy",
                    )
            else:
                value = type(default)(value)
            values[name] = value
        policy = cls(**values)
        if min(policy.passage_units.values()) < 1 or policy.max_claim_units < 1:
            raise TypeSafeMethodError(
                "typesafe policy: passage_units and max_claim_units must be positive",
                kind="invalid_policy",
            )
        if policy.max_fanout_labels < 0:
            raise TypeSafeMethodError(
                "typesafe policy: max_fanout_labels must be non-negative",
                kind="invalid_policy",
            )
        return policy

    def fingerprint(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Questions
# --------------------------------------------------------------------------

# How a label is asked about, by axis. A topic is a subject that is discussed; a
# frame is something the speakers do; an evidence signal is something they
# invoke. Jev reads instructions literally, so "discuss this subject" asked of a
# frame would be a different question from the one the codebook poses.
SCREEN_QUESTION = {
    "topic": "Does any part of `transcript` discuss or mention this health subject?",
    "frame": "Does any speaker in `transcript` use this framing?",
    "evidence": "Does any speaker in `transcript` invoke this kind of evidence or authority?",
}
# Localization asks one short question per (label, passage), hundreds a window,
# so nothing is repeated in them: each label's definition goes into the state
# once under `subjects` and the question names its key, and the instruction to
# judge one passage at a time is a note in the state. Measured on the dev split
# against repeating the definition in every question: the same F1 on every axis
# (better unit-level average precision on topics, 0.62 to 0.80) at under half
# the tokens.
PASSAGE_QUESTION = {
    "topic": "Is `passages.{key}` part of a stretch of the conversation that discusses or mentions the health subject described in `subjects.{subject}`?",
    "frame": "Does the speaker in `passages.{key}` use the framing described in `subjects.{subject}`?",
    "evidence": "Does the speaker in `passages.{key}` invoke the kind of evidence or authority described in `subjects.{subject}`?",
    "product": "Does `passages.{key}` name a specific product or offering of the kind described in `subjects.{subject}`?",
}
PASSAGE_NOTE = (
    "Each question is about one entry of `passages`. Judge that passage only; the "
    "neighbouring passages are there to resolve what it refers to, not to be judged."
)

GATE_QUESTIONS: dict[str, dict[str, Any]] = {
    "health": {
        "type": "noul",
        "instructions": "Does any part of `transcript` discuss health, medicine, nutrition, fitness, the body or wellness?",
        "criteria": {
            "true": "At least one stretch is about a health-related subject, including inside an advertisement.",
            "false": "No health-related subject comes up, or health words appear only as figures of speech.",
        },
    },
    "claim": {
        "type": "noul",
        "instructions": "Does any speaker in `transcript` state a factual claim about health that could be checked against outside evidence?",
        "criteria": {
            "true": "A specific factual proposition about health is stated, quoted, questioned or rebutted, including in ad copy.",
            "false": "Only opinions, personal experience, advice, questions or non-health facts.",
        },
    },
    "product": {
        "type": "noul",
        "instructions": "Does `transcript` name a specific brand, proprietary product, service, clinic, programme, app or book that a listener could buy or seek out?",
        "criteria": {
            "true": "A specific named offering appears.",
            "false": "Only generic substances, categories or practices are named, or nothing is.",
        },
    },
}

# The claim question keeps its boundary cases inline: it is one question per
# unit rather than one per label per unit, and by key it lost claim F1 (0.74 to
# 0.70) for a saving of a few thousand tokens.
CLAIM_UNIT_QUESTION: dict[str, Any] = {
    "question": "Does `passages.{key}` state a factual claim about health that could be checked against outside evidence?",
    "include": (
        "A specific factual proposition about health, medicine, nutrition or the body: "
        "a cause, effect, benefit, risk, mechanism, quantity or prevalence. It counts "
        "whoever makes it, including when it is quoted, questioned, rebutted or part of "
        "advertising copy."
    ),
    "exclude": (
        "Personal experience that is not generalised, opinions, advice with no factual "
        "proposition, vague suspicion, questions, jokes, and facts that are not about health."
    ),
}
PRODUCT_SUBJECT: dict[str, Any] = {
    "include": (
        "A named brand, proprietary product, service, clinic, programme, app, test or "
        "book that a listener could identify and buy, sign up for or seek out."
    ),
    "exclude": (
        "Generic substances, categories and practices (magnesium, semaglutide, a "
        "probiotic, cold plunges), and a company named only as an actor."
    ),
}


def _format(template: Any, **values: str) -> Any:
    if isinstance(template, str):
        return template.format(**values)
    if isinstance(template, dict):
        return {key: _format(value, **values) for key, value in template.items()}
    return template


def screen_question(label: Mapping[str, Any], examples: bool) -> dict[str, Any]:
    instructions: dict[str, Any] = {
        "question": SCREEN_QUESTION[label["axis"]],
        "name": label["name"],
        "definition": label["definition"],
    }
    if examples and label.get("concepts"):
        instructions["example_terms"] = list(label["concepts"][:12])
    return {"type": "noul", "instructions": instructions}


def passage_question(kind: str, key: str, subject: str) -> dict[str, Any]:
    """Whether passage ``key`` carries what `subjects.<subject>` describes.

    ``kind`` is a label's axis, or ``product``.
    """
    return {"type": "noul", "instructions": PASSAGE_QUESTION[kind].format(key=key, subject=subject)}


def claim_question(key: str) -> dict[str, Any]:
    return {"type": "noul", "instructions": _format(CLAIM_UNIT_QUESTION, key=key)}


def questions_sha256() -> str:
    """Identity of every question template, for the run fingerprint.

    The taxonomy hash covers the definitions; this covers the wording wrapped
    around them, which is this method's prompt.
    """
    probe = {"label_id": "x", "axis": "topic", "name": "n", "definition": "d", "concepts": ["c"]}
    templates = {
        "method": METHOD_VERSION,
        "screen": {axis: screen_question({**probe, "axis": axis}, True) for axis in AXES},
        "passage": PASSAGE_QUESTION,
        "passage_note": PASSAGE_NOTE,
        "gates": GATE_QUESTIONS,
        "claim_unit": CLAIM_UNIT_QUESTION,
        "product_subject": PRODUCT_SUBJECT,
        "choices": [DISCOURSE_ROLES, RELEVANCE, CLAIM_TYPES, PRODUCT_TYPES, MENTION_ROLES,
                    CERTAINTY_LEVELS, UNHEDGED_DESCRIPTION],
        "certainty_markers": CERTAINTY_MARKERS,
        "attribute_questions": _attribute_templates(),
    }
    encoded = json.dumps(templates, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------

Ask = Callable[[Any, dict[str, Any]], dict[str, Any]]
"""``ask(state, questions)`` -> the API response body (``answers`` and ``usage``)."""


def _estimate_tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return int(len(text) / CHARS_PER_TOKEN_ESTIMATE) + 1


def pack_questions(state: Any, questions: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Split ``questions`` into as few requests as the token limits allow."""
    state_tokens = _estimate_tokens(state)
    if state_tokens > STATE_TOKEN_BUDGET:
        raise TypeSafeMethodError(
            f"state of ~{state_tokens} tokens exceeds the request limit", kind="state_too_large"
        )
    batches: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    used = state_tokens
    for key, question in questions.items():
        cost = _estimate_tokens(question) + QUESTION_OVERHEAD_TOKENS
        if current and used + cost > REQUEST_TOKEN_BUDGET:
            batches.append(current)
            current, used = {}, state_tokens
        current[key] = question
        used += cost
    if current:
        batches.append(current)
    return batches


class _Session:
    """Sends packed requests for one window and adds up what they cost."""

    def __init__(self, ask: Ask) -> None:
        self.ask = ask
        self.usage: dict[str, Any] = {"input_tokens": 0, "output_tokens": 0, "requests": 0}
        # Input tokens by stage: what a window costs is decided by which stage
        # dominates, and that differs between a null window and a dense one.
        self.by_stage: dict[str, int] = {}
        self.model: str | None = None

    def answers(self, state: Any, questions: Mapping[str, Any], stage: str) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for batch in pack_questions(state, questions):
            response = self.ask(state, batch)
            answers = response.get("answers")
            if not isinstance(answers, dict) or set(answers) != set(batch):
                raise TypeSafeMethodError(
                    "response does not answer exactly the questions asked",
                    kind="typesafe_answers_mismatch",
                )
            usage = response.get("usage") or {}
            self.usage["input_tokens"] += int(usage.get("input_tokens") or 0)
            self.usage["output_tokens"] += int(usage.get("output_tokens") or 0)
            self.usage["requests"] += 1
            self.by_stage[stage] = self.by_stage.get(stage, 0) + int(usage.get("input_tokens") or 0)
            self.model = response.get("model") or self.model
            merged.update(answers)
        return merged


def _noul(answer: Any) -> float:
    try:
        value = float(answer["noul"])
    except (KeyError, TypeError, ValueError):
        raise TypeSafeMethodError("malformed noul answer", kind="typesafe_answers_mismatch") from None
    return min(max(value, 0.0), 1.0)


def _probabilities(answer: Any, options: Iterable[str]) -> dict[str, float]:
    try:
        probabilities = answer["probabilities"]
        return {option: float(probabilities.get(option, 0.0)) for option in options}
    except (KeyError, TypeError, ValueError, AttributeError):
        raise TypeSafeMethodError("malformed choice answer", kind="typesafe_answers_mismatch") from None


# --------------------------------------------------------------------------
# Stages 1 and 2: screen, then localize
# --------------------------------------------------------------------------


def _passages(window: Mapping[str, Any], size: int) -> list[tuple[str, list[int]]]:
    """(key, unit indexes) per passage, in order."""
    count = len(window["units"])
    return [
        (f"p{number:03d}", list(range(start, min(start + size, count))))
        for number, start in enumerate(range(0, count, size))
    ]


def _passage_state(window: Mapping[str, Any], passages: Sequence[tuple[str, list[int]]]) -> dict[str, Any]:
    units = window["units"]
    return {
        "passages": {
            key: " ".join(units[index]["text"] for index in indexes) for key, indexes in passages
        }
    }


def judge_window(
    window: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    policy: Policy,
    session: _Session,
) -> dict[str, Any]:
    """Screen the window and localize whatever cleared the fan-out threshold."""
    labels = {label["label_id"]: label for label in taxonomy["labels"]}
    transcript = {"transcript": " ".join(unit["text"] for unit in window["units"])}
    screen = {
        **{f"label|{label_id}": screen_question(label, policy.screen_examples) for label_id, label in labels.items()},
        **{f"gate|{name}": question for name, question in GATE_QUESTIONS.items()},
    }
    answers = session.answers(transcript, screen, "screen")
    window_probs = {label_id: _noul(answers[f"label|{label_id}"]) for label_id in labels}
    gates = {name: _noul(answers[f"gate|{name}"]) for name in GATE_QUESTIONS}

    healthy = gates["health"] >= policy.health_gate_threshold
    fanout = sorted(
        (label_id for label_id, p in window_probs.items() if healthy and p >= policy.fanout_threshold),
        key=lambda label_id: -window_probs[label_id],
    )[: policy.max_fanout_labels]
    judgments: dict[str, Any] = {
        "method_version": METHOD_VERSION,
        "window_id": window["window_id"],
        "window": window_probs,
        "gates": gates,
        "passage_units": dict(policy.passage_units),
        "labels": {},
        "units": {},
        "attributes": {},
    }

    # What each localization question points at: `subjects.<key>` in the state.
    subjects: dict[str, tuple[str, dict[str, Any]]] = {
        label_id: (
            f"s{number:02d}",
            {"name": labels[label_id]["name"], "definition": labels[label_id]["definition"]},
        )
        for number, label_id in enumerate(fanout)
    }
    # Questions over the same passages share a state, and so share requests:
    # passage size -> {name: (kind, question builder)}.
    grids: dict[int, dict[str, Callable[[str], dict[str, Any]]]] = {}
    for label_id in fanout:
        axis = labels[label_id]["axis"]
        grids.setdefault(policy.passage_units[axis], {})[label_id] = (
            lambda key, axis=axis, subject=subjects[label_id][0]: passage_question(axis, key, subject)
        )
    if healthy and gates["claim"] >= policy.gate_threshold:
        grids.setdefault(1, {})["claim"] = claim_question
    if healthy and gates["product"] >= policy.gate_threshold:
        subjects["product"] = ("product", PRODUCT_SUBJECT)
        grids.setdefault(1, {})["product"] = lambda key: passage_question("product", key, "product")
    for size, builders in grids.items():
        passages = _passages(window, size)
        # Passages first, subjects last. The order is not cosmetic: answers moved
        # by 0.07 on average when the two were swapped, against 0.02 between two
        # sends of the same request. This order had the better unit-level average
        # precision on topics (0.79 against 0.75); F1 was within noise.
        state = {
            "note": PASSAGE_NOTE,
            **_passage_state(window, passages),
            "subjects": {subjects[name][0]: subjects[name][1] for name in builders if name in subjects},
        }
        questions = {f"{name}|{key}": build(key) for name, build in builders.items() for key, _ in passages}
        answers = session.answers(state, questions, f"localize_{size}")
        for name in builders:
            probs = [_noul(answers[f"{name}|{key}"]) for key, _ in passages]
            judgments["units" if name in ("claim", "product") else "labels"][name] = probs
    return judgments


# --------------------------------------------------------------------------
# Stage 3: spans from probabilities
# --------------------------------------------------------------------------


def _unit_probabilities(passage_probs: Sequence[float], size: int, count: int) -> list[float]:
    probs = [p for p in passage_probs for _ in range(size)][:count]
    return probs + [0.0] * (count - len(probs))


def find_spans(probs: Sequence[float], seed: float, extend: float, bridge: int) -> list[tuple[int, int, float]]:
    """(start, end, peak) runs: units at ``extend`` holding one at ``seed``.

    Runs of the same label at most ``bridge`` units apart are joined, which is
    how "resumes after a short aside" stays one detection and "resumes after an
    unrelated stretch" becomes two.
    """
    runs: list[list[float]] = []
    start: int | None = None
    for index, p in enumerate([*probs, -1.0]):
        if p >= extend and start is None:
            start = index
        elif p < extend and start is not None:
            peak = max(probs[start:index])
            if peak >= seed:
                runs.append([start, index - 1, peak])
            start = None
    joined: list[list[float]] = []
    for run in runs:
        if joined and run[0] - joined[-1][1] - 1 <= bridge:
            joined[-1][1] = run[1]
            joined[-1][2] = max(joined[-1][2], run[2])
        else:
            joined.append(run)
    return [(int(a), int(b), float(peak)) for a, b, peak in joined]


def _strip_speaker(text: str) -> str:
    return _SPEAKER_PREFIX.sub("", text, count=1).strip() or text.strip()


_DOMAIN = re.compile(
    r"\b([A-Za-z0-9][A-Za-z0-9-]+)(?:\s+dot\s+|\.)(?:com|co|org|net|io|health|shop|store)\b",
    re.IGNORECASE,
)


def name_candidates(text: str) -> list[str]:
    """Capitalised or alphanumeric token runs that could be a product name.

    Jev cannot write a name, so code proposes and Jev selects. Transcripts are
    cased, and a brand is nearly always capitalised or carries a digit ("AG1",
    "Eight Sleep", "LMNT"). A sponsor read that lower-cases the brand usually
    still spells its site ("eightsleep dot com"), so a domain's name is a
    candidate too. A name that appears only garbled ("A G one") is lost.
    """
    candidates: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        key = re.sub(r"[^a-z0-9]+", "", name.casefold())
        if key and key not in seen and len(name) > 1:
            seen.add(key)
            candidates.append(name)

    for sentence in re.split(r"(?<=[.!?])\s+", _strip_speaker(text)):
        run: list[str] = []
        tokens = [match.group(0) for match in _NAME_TOKEN.finditer(sentence)]
        for position, token in enumerate([*tokens, ""]):
            namelike = bool(token) and (
                token[0].isupper()
                or (any(ch.isdigit() for ch in token) and any(ch.isalpha() for ch in token))
            )
            if namelike and token.casefold() in _NAME_STOPWORDS and (not run or position == 0):
                namelike = False
            # A bare number continues a name ("Pod 5") but never starts one.
            if token.isdigit() and run:
                namelike = True
            if namelike:
                run.append(token)
                continue
            while run and run[-1].casefold() in _NAME_STOPWORDS:
                run.pop()
            if run:
                add(" ".join(run))
            run = []
    for match in _DOMAIN.finditer(text):
        add(match.group(1))
    return candidates[:MAX_NAME_CANDIDATES]


def find_markers(text: str) -> dict[str, list[str]]:
    """Certainty-marker candidates in ``text``, by the level they would justify."""
    found: dict[str, list[str]] = {}
    for level, phrases in CERTAINTY_MARKERS.items():
        hits: list[str] = []
        for phrase in phrases:
            pattern = r"(?<!\w)" + re.escape(phrase).replace(r"\ ", r"\s+").replace("'", "['’]") + r"(?!\w)"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                hits.append(re.sub(r"\s+", " ", match.group(0)))
        if hits:
            found[level] = hits[:MAX_CERTAINTY_MARKERS]
    return found


def _overlaps(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return left["start"] <= right["end"] and left["end"] >= right["start"]


def draft_annotations(
    window: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    judgments: Mapping[str, Any],
    policy: Policy,
) -> dict[str, list[dict[str, Any]]]:
    """Spans for detections, claims and products, before their closed-set fields."""
    units = window["units"]
    count = len(units)
    axes = {label["label_id"]: label["axis"] for label in taxonomy["labels"]}
    sizes = judgments.get("passage_units") or {}
    if judgments["gates"]["health"] < policy.health_gate_threshold:
        return {"detections": [], "claims": [], "products": []}

    detections: list[dict[str, Any]] = []
    unit_label_probs: dict[str, list[float]] = {}
    for label_id, passage_probs in judgments["labels"].items():
        axis = axes.get(label_id)
        if axis is None:
            continue
        probs = _unit_probabilities(passage_probs, int(sizes.get(axis) or 1), count)
        unit_label_probs[label_id] = probs
        if judgments["window"].get(label_id, 0.0) < policy.window_threshold[axis]:
            continue
        for start, end, peak in find_spans(
            probs, policy.seed_threshold[axis], policy.extend_threshold[axis], policy.bridge_units[axis]
        ):
            best = max(range(start, end + 1), key=lambda index: probs[index])
            detections.append(
                {"kind": "detection", "label_id": label_id, "axis": axis, "start": start,
                 "end": end, "confidence": peak, "quote_unit": best}
            )
    topics = [row for row in detections if row["axis"] == "topic"]
    # The catch-all is never a second choice where a listed topic applies.
    rejected = {
        id(row) for row in topics
        if row["label_id"] == OTHER_TOPIC
        and any(other["label_id"] != OTHER_TOPIC and _overlaps(row, other) for other in topics)
    }
    detections = [row for row in detections if id(row) not in rejected]
    detections.sort(key=lambda row: -row["confidence"])
    detections = sorted(detections[:MAX_DETECTIONS], key=lambda row: (row["start"], row["end"], row["label_id"]))

    claims: list[dict[str, Any]] = []
    claim_probs = judgments["units"].get("claim") or []
    index = 0
    while index < len(claim_probs):
        if claim_probs[index] < policy.claim_threshold:
            index += 1
            continue
        end = index
        # A unit cut at the word limit mid-sentence carries half a proposition.
        while (
            end + 1 < len(claim_probs)
            and end - index + 1 < policy.max_claim_units
            and claim_probs[end + 1] >= policy.claim_threshold
            and not _SENTENCE_END.search(units[end]["text"])
        ):
            end += 1
        claims.append(
            {"kind": "claim", "start": index, "end": end,
             "confidence": max(claim_probs[index : end + 1]),
             "quote_unit": max(range(index, end + 1), key=lambda i: claim_probs[i])}
        )
        index = end + 1
    for claim in claims:
        for axis, target in (("topic", "topic_ids"), ("frame", "frame_ids"), ("evidence", "evidence_signal_ids")):
            claim[target] = sorted(
                {row["label_id"] for row in detections if row["axis"] == axis and _overlaps(row, claim)}
            )
        if not claim["topic_ids"]:
            # No topic span reaches the claim: fall back to the likeliest topic
            # on its own units, then to the catch-all. The schema requires one.
            scored = [
                (max(probs[claim["start"] : claim["end"] + 1]), label_id)
                for label_id, probs in unit_label_probs.items() if axes[label_id] == "topic"
            ]
            best_p, best_label = max(scored, default=(0.0, None))
            if best_label is not None and best_p >= policy.extend_threshold["topic"]:
                claim["topic_ids"] = [best_label]
            elif OTHER_TOPIC in axes:
                claim["topic_ids"] = [OTHER_TOPIC]
    claims = [claim for claim in claims if claim["topic_ids"]]
    claims.sort(key=lambda row: -row["confidence"])
    claims = sorted(claims[:MAX_CLAIMS], key=lambda row: row["start"])

    products: list[dict[str, Any]] = []
    product_probs = judgments["units"].get("product") or []
    for start, end, peak in find_spans(
        product_probs, policy.product_threshold, policy.product_threshold, policy.product_bridge_units
    ):
        candidates = name_candidates(" ".join(units[i]["text"] for i in range(start, end + 1)))
        if candidates:
            products.append(
                {"kind": "product", "start": start, "end": end, "confidence": peak, "candidates": candidates}
            )
    products.sort(key=lambda row: -row["confidence"])
    products = sorted(products[:MAX_PRODUCTS], key=lambda row: row["start"])
    return {"detections": detections, "claims": claims, "products": products}


# --------------------------------------------------------------------------
# Stage 4: closed-set attributes of the composed spans
# --------------------------------------------------------------------------


def _attribute_templates() -> dict[str, Any]:
    return {
        "detection_role": "What do the speakers do with {name} in `spans.{key}.text`?",
        "detection_relevance": "How does {name} figure in `spans.{key}.text`?",
        "claim_role": "What do the speakers do with the health claim stated in `spans.{key}.text`?",
        "claim_type": "What kind of factual claim about health does `spans.{key}.text` make? Choose by what it asserts, not by its subject.",
        "claim_certainty": "How firmly is the health claim in `spans.{key}.text` stated by the person making it?",
        "product_name": {
            "question": "In `spans.{key}.text`, is \"{name}\" the name of a specific product or offering?",
            "include": "A named brand, proprietary product, service, clinic, programme, app, test, website or book that a listener could identify and buy, sign up for or seek out.",
            "exclude": "A person, a place, a generic substance or practice, an institution named only as an actor, or an ordinary word that happens to be capitalised.",
        },
        "product_type": "What kind of product or offering does `spans.{key}.text` name?",
        "product_role": "What do the speakers do with the product named in `spans.{key}.text`?",
    }


def attribute_key(row: Mapping[str, Any]) -> str:
    return "|".join(str(part) for part in (row["kind"], row.get("label_id", ""), row["start"], row["end"]))


def _choice(instructions: Any, options: Mapping[str, Any]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "criteria": dict(options)}


def judge_attributes(
    window: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    draft: Mapping[str, Sequence[Mapping[str, Any]]],
    policy: Policy,
    session: _Session,
) -> dict[str, dict[str, dict[str, float]]]:
    units = window["units"]
    labels = {label["label_id"]: label for label in taxonomy["labels"]}
    templates = _attribute_templates()
    # Detections of different labels often share a span; send each span once.
    span_keys: dict[tuple[int, int], str] = {}
    state: dict[str, Any] = {"spans": {}}

    def span_key(row: Mapping[str, Any]) -> str:
        bounds = (row["start"], row["end"])
        if bounds not in span_keys:
            key = f"s{len(span_keys):03d}"
            span_keys[bounds] = key
            before = units[max(0, bounds[0] - policy.context_units) : bounds[0]]
            after = units[bounds[1] + 1 : bounds[1] + 1 + policy.context_units]
            state["spans"][key] = {
                "before": " ".join(unit["text"] for unit in before),
                "text": " ".join(unit["text"] for unit in units[bounds[0] : bounds[1] + 1]),
                "after": " ".join(unit["text"] for unit in after),
            }
        return span_keys[bounds]

    questions: dict[str, Any] = {}
    # question id -> the options of a choice, or None for a noul.
    options: dict[str, list[str] | None] = {}

    def add(row: Mapping[str, Any], field_name: str, question: dict[str, Any]) -> None:
        question_id = f"{attribute_key(row)}#{field_name}"
        questions[question_id] = question
        options[question_id] = list(question["criteria"]) if question["type"] == "choice" else None

    for row in draft["detections"]:
        key = span_key(row)
        name = labels[row["label_id"]]["name"]
        add(row, "discourse_role", _choice(templates["detection_role"].format(name=name, key=key), DISCOURSE_ROLES))
        add(row, "relevance", _choice(templates["detection_relevance"].format(name=name, key=key), RELEVANCE))
    for row in draft["claims"]:
        key = span_key(row)
        add(row, "discourse_role", _choice(templates["claim_role"].format(key=key), DISCOURSE_ROLES))
        add(row, "claim_type", _choice(templates["claim_type"].format(key=key), CLAIM_TYPES))
        markers = find_markers(state["spans"][key]["text"])
        if markers:
            criteria: dict[str, Any] = {
                level: {"what": CERTAINTY_LEVELS[level], "words_present": markers[level]}
                for level in CERTAINTY_LEVELS if level in markers
            }
            criteria[UNHEDGED] = UNHEDGED_DESCRIPTION
            add(row, "expressed_certainty", _choice(templates["claim_certainty"].format(key=key), criteria))
    for row in draft["products"]:
        key = span_key(row)
        # One noul per candidate, not a choice among them: a span can name two
        # products, and a choice would split its probability between them.
        for number, name in enumerate(row["candidates"]):
            add(row, f"name:{number}", {"type": "noul", "instructions": _format(templates["product_name"], key=key, name=name)})
        add(row, "product_type", _choice(templates["product_type"].format(key=key), PRODUCT_TYPES))
        add(row, "mention_role", _choice(templates["product_role"].format(key=key), MENTION_ROLES))
    if not questions:
        return {}
    answers = session.answers(state, questions, "attributes")
    products = {attribute_key(row): row for row in draft["products"]}
    attributes: dict[str, dict[str, dict[str, float]]] = {}
    for question_id, answer in answers.items():
        key, field_name = question_id.rsplit("#", 1)
        choices = options[question_id]
        if choices is None:
            name = products[key]["candidates"][int(field_name.split(":", 1)[1])]
            attributes.setdefault(key, {}).setdefault("product_names", {})[name] = _noul(answer)
        else:
            attributes.setdefault(key, {})[field_name] = _probabilities(answer, choices)
    return attributes


# --------------------------------------------------------------------------
# The result, in the pipeline's schema
# --------------------------------------------------------------------------


def _top(distribution: Mapping[str, float] | None, default: str) -> str:
    if not distribution:
        return default
    return max(distribution, key=lambda option: distribution[option])


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def compose_result(
    window: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    judgments: Mapping[str, Any],
    policy: Policy,
) -> dict[str, Any]:
    """The window result for ``judgments`` under ``policy``; no requests.

    A span with no stored attributes -- one a changed policy created after the
    attribute request was made -- takes the codebook's ordinary-discussion
    defaults, so a threshold sweep can score spans without re-asking. A product
    span with no stored name judgments yields nothing: an unnamed product is
    not a mention.
    """
    require_flat_taxonomy(taxonomy)
    units = window["units"]
    names = {label["label_id"]: label["name"] for label in taxonomy["labels"]}
    draft = draft_annotations(window, taxonomy, judgments, policy)
    attributes = judgments.get("attributes") or {}

    def bounds(start: int, end: int) -> dict[str, str]:
        return {"start_unit_id": units[start]["unit_id"], "end_unit_id": units[end]["unit_id"]}

    detections = []
    for row in draft["detections"]:
        chosen = attributes.get(attribute_key(row)) or {}
        detections.append(
            {
                **bounds(row["start"], row["end"]),
                "label_ids": [row["label_id"]],
                "relevance": _top(chosen.get("relevance"), "substantive"),
                "discourse_role": _top(chosen.get("discourse_role"), "asserted_or_endorsed"),
                "confidence": round(row["confidence"], 4),
                "summary": f"{names[row['label_id']]} ({METHOD_VERSION} span)",
                "evidence_quote": units[row["quote_unit"]]["text"],
            }
        )

    claims = []
    for row in draft["claims"]:
        chosen = attributes.get(attribute_key(row)) or {}
        text = " ".join(unit["text"] for unit in units[row["start"] : row["end"] + 1])
        markers = find_markers(text)
        certainty = _top(chosen.get("expressed_certainty"), UNHEDGED) if markers else UNHEDGED
        if certainty not in markers:
            certainty = UNHEDGED
        claim_type = _top(chosen.get("claim_type"), "other_factual")
        claims.append(
            {
                **bounds(row["start"], row["end"]),
                "topic_ids": row["topic_ids"],
                "frame_ids": row["frame_ids"],
                "evidence_signal_ids": row["evidence_signal_ids"],
                "discourse_role": _top(chosen.get("discourse_role"), "asserted_or_endorsed"),
                "claim_type": claim_type,
                # Verbatim, not normalised: Jev cannot rewrite, so pronouns stay
                # unresolved. Faithful by construction, self-contained by luck.
                "claim_text": _strip_speaker(text),
                "expressed_certainty": certainty,
                "certainty_markers": markers[certainty] if certainty != UNHEDGED else [],
                "evidence_quote": units[row["quote_unit"]]["text"],
                "confidence": round(row["confidence"], 4),
                "rationale": f"Selected as a checkable {claim_type.replace('_', ' ')} health claim ({METHOD_VERSION}).",
            }
        )

    products = []
    for row in draft["products"]:
        chosen = attributes.get(attribute_key(row)) or {}
        accepted: list[tuple[float, str]] = []
        ranked = sorted((chosen.get("product_names") or {}).items(), key=lambda item: -item[1])
        for name, p in ranked:
            if p < policy.product_name_threshold or name not in row["candidates"]:
                continue
            key = _name_key(name)
            # "Eight Sleep" and "eightsleep" (from the URL) are one product.
            if any(key in _name_key(other) or _name_key(other) in key for _, other in accepted):
                continue
            accepted.append((p, name))
        for p, name in accepted:
            # Narrow the run to the units that actually carry this name.
            holding = [
                index for index in range(row["start"], row["end"] + 1)
                if _name_key(name) in _name_key(units[index]["text"])
            ] or [row["start"]]
            span = {"start": holding[0], "end": holding[-1]}
            if policy.product_needs_topic and not any(
                other["axis"] == "topic" and _overlaps(span, other) for other in draft["detections"]
            ):
                continue
            products.append(
                {
                    **bounds(holding[0], holding[-1]),
                    "product_name": name,
                    "product_type": _top(chosen.get("product_type"), "other_product"),
                    "mention_role": _top(chosen.get("mention_role"), "neutral"),
                    "evidence_quote": units[holding[0]]["text"],
                    "confidence": round(min(row["confidence"], p), 4),
                }
            )
    products.sort(key=lambda row: -row["confidence"])
    return {
        "window_id": window["window_id"],
        "detections": detections,
        "verification_candidates": claims,
        "product_mentions": products[:MAX_PRODUCTS],
    }


def label_window(
    window: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    policy: Policy,
    ask: Ask,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """(result, judgments) for one window. ``judgments`` carries ``usage`` and ``model``."""
    require_flat_taxonomy(taxonomy)
    if not window.get("units"):
        raise TypeSafeMethodError(f"window {window.get('window_id')} has no units", kind="empty_window")
    session = _Session(ask)
    judgments = judge_window(window, taxonomy, policy, session)
    draft = draft_annotations(window, taxonomy, judgments, policy)
    judgments["attributes"] = judge_attributes(window, taxonomy, draft, policy, session)
    judgments["usage"] = {**session.usage, "input_tokens_by_stage": dict(session.by_stage)}
    judgments["model"] = session.model
    return compose_result(window, taxonomy, judgments, policy), judgments
