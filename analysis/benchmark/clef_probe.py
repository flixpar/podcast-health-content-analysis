"""Probe how localization questions should be put to a Clef model.

The TypeSafe method's localization request was shaped for Jev: one request per
passage grid holding every fanned-out label's questions, with definitions in
the state under `subjects`. Clef decides the questions of one forward pass
jointly, so the shape of a request may matter to it in ways it did not to Jev.
This holds the window and the labels to localize fixed (those a stored run
fanned out to), asks them in several shapes, and reads each shape by unit-level
average precision against the gold's tight spans -- the signal composition
thresholds have to work with -- and by tokens per window.

    .venv/bin/python -m analysis.benchmark.clef_probe benchmark/runs/flash-v1 \
        --endpoint http://127.0.0.1:8301/v1 --model clef-flash --windows 40 \
        --shapes grid per_label

Read on dev only; the shapes that win go into a full benchmark run.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Sequence

from analysis import typesafe_labeling as typesafe
from analysis.benchmark import GOLD_PATH, ITEMS_PATH
from analysis.benchmark import items as items_mod
from analysis.benchmark import references as refs_mod
from analysis.benchmark.clef_screen import ask as http_ask
from analysis.benchmark.clef_screen import auroc
from analysis.benchmark.clef_signal import average_precision
from analysis.benchmark.taxonomy import label_axes, load_benchmark_taxonomy
from analysis.benchmark.typesafe_tune import load_judgments

STRATA = ("health_dense", "mixed", "ad_read", "discourse", "rare_label")
CREDITED = ("required", "acceptable")

# A shape: (window, labels to localize, taxonomy, policy) -> requests, each a
# (state, questions, collect) where collect maps the answers to
# {name: per-passage probabilities} and the passage size used.
Request = tuple[Any, dict[str, Any], Callable[[dict[str, Any]], dict[str, tuple[list[float], int]]]]


def _subject(label: dict[str, Any], examples: bool = False) -> dict[str, Any]:
    subject = {"name": label["name"], "definition": label["definition"]}
    if examples and label.get("concepts"):
        subject["example_terms"] = list(label["concepts"][:12])
    return subject


def _grid_request(window, names, sizes, subjects, question_for) -> list[Request]:
    """One request per passage size holding every name's questions (the method's shape)."""
    by_size: dict[int, list[str]] = defaultdict(list)
    for name in names:
        by_size[sizes[name]].append(name)
    requests = []
    for size, group in by_size.items():
        passages = typesafe._passages(window, size)
        state = {
            "note": typesafe.PASSAGE_NOTE,
            **typesafe._passage_state(window, passages),
            "subjects": {subjects[name][0]: subjects[name][1] for name in group if name in subjects},
        }
        questions = {f"{name}|{key}": question_for(name, key) for name in group for key, _ in passages}

        def collect(answers, group=group, passages=passages, size=size):
            return {
                name: ([answers[f"{name}|{key}"]["noul"] for key, _ in passages], size) for name in group
            }

        requests.append((state, questions, collect))
    return requests


FOCUS_QUESTION = {
    "topic": "Is the PASSAGE part of a stretch of the conversation that discusses or mentions this health subject?",
    "frame": "Does the speaker in the PASSAGE use this framing?",
    "evidence": "Does the speaker in the PASSAGE invoke this kind of evidence or authority?",
}
FOCUS_CLAIM = {
    "question": "Does the PASSAGE state a factual claim about health that could be checked against outside evidence?",
    "include": typesafe.CLAIM_UNIT_QUESTION["include"],
    "exclude": typesafe.CLAIM_UNIT_QUESTION["exclude"],
}
FOCUS_BEFORE_UNITS = 2
FOCUS_AFTER_UNITS = 1


def focus_state(window, indexes: list[int]) -> str:
    """One passage as the thing judged, with a little context that is not."""
    units = window["units"]
    before = units[max(0, indexes[0] - FOCUS_BEFORE_UNITS) : indexes[0]]
    after = units[indexes[-1] + 1 : indexes[-1] + 1 + FOCUS_AFTER_UNITS]
    parts = []
    if before:
        parts.append("BEFORE (context only): " + " ".join(unit["text"] for unit in before))
    parts.append("PASSAGE: " + " ".join(units[index]["text"] for index in indexes))
    if after:
        parts.append("AFTER (context only): " + " ".join(unit["text"] for unit in after))
    return "\n".join(parts)


def _focus_requests(window, names, sizes, labels, examples: bool) -> list[Request]:
    """One request per passage; every question is about THE passage, so nothing points."""
    by_size: dict[int, list[str]] = defaultdict(list)
    for name in names:
        by_size[sizes[name]].append(name)
    requests = []
    for size, group in by_size.items():
        passages = typesafe._passages(window, size)
        for position, (key, indexes) in enumerate(passages):
            questions = {}
            for name in group:
                if name == "claim":
                    questions[name] = {"type": "noul", "instructions": FOCUS_CLAIM}
                else:
                    label = labels[name]
                    instructions = {"question": FOCUS_QUESTION[label["axis"]], **_subject(label, examples)}
                    questions[name] = {"type": "noul", "instructions": instructions}

            def collect(answers, group=group, position=position, count=len(passages), size=size):
                out = {}
                for name in group:
                    probs = [0.0] * count
                    probs[position] = answers[name]["noul"]
                    out[name] = (probs, size)
                return out

            requests.append((focus_state(window, indexes), questions, collect))
    return requests


CHOICE_QUESTION = {
    "topic": "Which entry of `passages` is part of a stretch of the conversation that discusses or mentions the health subject described in `subjects.{subject}`?",
    "frame": "In which entry of `passages` does the speaker use the framing described in `subjects.{subject}`?",
    "evidence": "In which entry of `passages` does the speaker invoke the kind of evidence or authority described in `subjects.{subject}`?",
}
NONE_OPTION = "No passage does."


def _choice_requests(window, label_ids, sizes, subjects, labels) -> list[Request]:
    """One choice per label over the passages: a localization for the price of one question.

    The softmax makes passages compete, so a label discussed in two places
    splits its mass; probabilities are read as a ranking within the label.
    """
    by_size: dict[int, list[str]] = defaultdict(list)
    for name in label_ids:
        by_size[sizes[name]].append(name)
    requests = []
    for size, group in by_size.items():
        passages = typesafe._passages(window, size)
        state = {
            "note": "Each question asks which one entry of `passages` best fits; answer `none` if none does.",
            **typesafe._passage_state(window, passages),
            "subjects": {subjects[name][0]: subjects[name][1] for name in group},
        }
        criteria = {key: None for key, _ in passages}
        criteria["none"] = NONE_OPTION
        questions = {
            name: {
                "type": "choice",
                "instructions": CHOICE_QUESTION[labels[name]["axis"]].format(subject=subjects[name][0]),
                "criteria": criteria,
            }
            for name in group
        }

        def collect(answers, group=group, passages=passages, size=size):
            return {
                name: ([answers[name]["probabilities"][key] for key, _ in passages], size) for name in group
            }

        requests.append((state, questions, collect))
    return requests


def build(shape: str, window, label_ids, taxonomy, claims: bool) -> list[Request]:
    labels = {label["label_id"]: label for label in taxonomy["labels"]}
    unit_axes = shape.endswith("_units")
    base = shape.removesuffix("_units")
    sizes = {
        label_id: 1 if unit_axes else typesafe.Policy().passage_units[labels[label_id]["axis"]]
        for label_id in label_ids
    }
    examples = base in ("grid_examples", "per_label_examples")
    subjects = {label_id: (f"s{n:02d}", _subject(labels[label_id], examples)) for n, label_id in enumerate(label_ids)}

    def method_question(name, key):
        if name == "claim":
            return typesafe.claim_question(key)
        return typesafe.passage_question(labels[name]["axis"], key, subjects[name][0])

    def named_question(name, key):
        if name == "claim":
            return typesafe.claim_question(key)
        axis = labels[name]["axis"]
        what = {
            "topic": f"Is `passages.{key}` part of a stretch of the conversation that discusses or mentions {labels[name]['name']} (defined in `subjects.{subjects[name][0]}`)?",
            "frame": f"Does the speaker in `passages.{key}` use the framing \"{labels[name]['name']}\" (defined in `subjects.{subjects[name][0]}`)?",
            "evidence": f"Does the speaker in `passages.{key}` invoke {labels[name]['name']} as evidence or authority (defined in `subjects.{subjects[name][0]}`)?",
        }[axis]
        return {"type": "noul", "instructions": what}

    names = list(label_ids) + (["claim"] if claims else [])
    sizes["claim"] = 1
    if base == "choice":
        # Labels by choice; claims stay one noul per unit (a window holds many).
        requests = _choice_requests(window, list(label_ids), sizes, subjects, labels)
        if claims:
            requests.extend(_grid_request(window, ["claim"], sizes, subjects, method_question))
        return requests
    if base in ("focus", "focus_examples"):
        return _focus_requests(window, names, sizes, labels, examples=base == "focus_examples")
    if base in ("grid", "grid_examples"):
        return _grid_request(window, names, sizes, subjects, method_question)
    if base == "grid_named":
        return _grid_request(window, names, sizes, subjects, named_question)
    if base in ("per_label", "per_label_examples", "per_label_named"):
        question = named_question if base == "per_label_named" else method_question
        requests = []
        for name in names:
            requests.extend(_grid_request(window, [name], sizes, subjects, question))
        return requests
    if base == "per_axis":
        requests = []
        axes = defaultdict(list)
        for name in names:
            axes["claim" if name == "claim" else labels[name]["axis"]].append(name)
        for group in axes.values():
            requests.extend(_grid_request(window, group, sizes, subjects, method_question))
        return requests
    raise ValueError(shape)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path, help="A System One run whose fan-out decides the labels")
    parser.add_argument("--endpoint", nargs="+", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--windows", type=int, default=40)
    parser.add_argument("--shapes", nargs="+", default=["grid", "per_label"])
    parser.add_argument("--policy", default="{}", help="Policy JSON for the wire (short_ids, noul_options)")
    parser.add_argument("--fanout", type=float, default=0.3)
    parser.add_argument("--oracle", action="store_true", help="Localize the gold's labels too, as if the screen found them")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    taxonomy = load_benchmark_taxonomy()
    axes = label_axes(taxonomy)
    gold = refs_mod.load_gold(GOLD_PATH)
    stored = load_judgments(args.run_dir)[0]
    items = [
        item for item in items_mod.load_items(ITEMS_PATH)
        if item["split"] == "dev" and item["stratum"] in STRATA and item["window_id"] in stored
        and any(atom.tier in CREDITED for atom in gold.get(item["item_id"], []))
    ][: args.windows]
    policy = typesafe.Policy.from_mapping(json.loads(args.policy))
    results = []
    for shape in args.shapes:
        pooled: dict[str, tuple[list[float], list[bool]]] = defaultdict(lambda: ([], []))
        tokens = 0
        requests_sent = 0

        def one(index_item):
            index, item = index_item
            judgments = stored[item["window_id"]]
            atoms = [atom for atom in gold[item["item_id"]] if atom.tier in CREDITED]
            present = defaultdict(list)
            for atom in atoms:
                present[atom.label if atom.kind == "detection" else atom.kind].append(atom.tight)
            label_ids = [label_id for label_id, p in judgments["window"].items() if p >= args.fanout]
            if args.oracle:
                label_ids = sorted(set(label_ids) | {name for name in present if name in axes})
            endpoint = args.endpoint[index % len(args.endpoint)]
            session = typesafe._Session(lambda state, qs: http_ask(endpoint, args.model, state, qs), policy)
            probs = {}
            for state, questions, collect in build(shape, item, label_ids, taxonomy, claims=True):
                for name, (passage_probs, size) in collect(session.answers(state, questions, "localize")).items():
                    if name in probs:
                        # A focus request fills one passage; the rest are zeros.
                        passage_probs = [max(a, b) for a, b in zip(probs[name][0], passage_probs)]
                    probs[name] = (passage_probs, size)
            return item, present, probs, session.usage

        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            for item, present, probs, usage in pool.map(one, enumerate(items)):
                tokens += usage["input_tokens"]
                requests_sent += usage["requests"]
                count = len(item["units"])
                # A fanned-out label the gold does not hold contributes only
                # negatives: localization has to stay quiet on it too.
                for name, (passage_probs, size) in probs.items():
                    key = "claim" if name == "claim" else axes[name]
                    unit_probs = [p for p in passage_probs for _ in range(size)][:count]
                    inside = [False] * count
                    for start, end in present.get(name, []):
                        for unit in range(start, min(end, count - 1) + 1):
                            inside[unit] = True
                    pooled[key][0].extend(unit_probs)
                    pooled[key][1].extend(inside)
                    # The same units scored relative to the label's best unit,
                    # for shapes (a choice) whose scale is per label.
                    top = max(unit_probs, default=0.0) or 1.0
                    pooled[key + "_rel"][0].extend(p / top for p in unit_probs)
                    pooled[key + "_rel"][1].extend(inside)
        row = {"shape": shape, "policy": json.loads(args.policy), "model": args.model, "windows": len(items),
               "tokens_per_window": tokens / max(len(items), 1), "requests_per_window": requests_sent / max(len(items), 1)}
        line = f"{shape:22s} {row['tokens_per_window']:>8,.0f} tok/window {row['requests_per_window']:>5.1f} req/window"
        for key in ("topic", "frame", "evidence", "claim"):
            for variant in (key, key + "_rel"):
                scores, labels = pooled.get(variant, ([], []))
                ap = average_precision(scores, labels)
                area = auroc(scores, labels)
                row[variant] = {"ap": ap, "auroc": area, "units": len(labels), "positive": sum(labels)}
            line += f"  {key} AP {row[key]['ap'] or float('nan'):.3f}/{row[key + '_rel']['ap'] or float('nan'):.3f}"
        print(line, flush=True)
        results.append(row)
        if args.out:
            with open(args.out, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
