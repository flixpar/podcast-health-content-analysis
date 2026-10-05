"""Tool-calling labelers: the model submits labels through tools and may
interleave reasoning with tool calls, getting validation feedback back.

Modes:
  incremental  add_detections / add_claims / add_products as it works through
               the window (each call is validated item by item and answered with
               what was accepted and why anything was rejected), then finish.
  submit       one submit_annotation call with the whole result; the harness
               validates it and returns every problem; the model may resubmit
               (up to --max-submits) or finish.
  lookup       like submit, but the system prompt carries only a label index
               (IDs and names); full definitions come from lookup_labels.

Reasoning is passed back on every assistant turn (`reasoning_content`), which
the GLM chat template keeps for turns after the last user message, so the
thinking is continuous across tool calls. Results are written in the
benchmark run layout, like exp/xlabel.py.

    python exp/toollabel.py --bench v3 --mode incremental --name v8-glm-tool-inc --model glm53-w4 --strata health_dense mixed null ad_read discourse
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "exp"))
from analysis import topic_labeling as tl  # noqa: E402
from xlabel import Store, load_windows, start_metrics_sampler  # noqa: E402
import xlabel  # noqa: E402

KEYS = {"detection": "detections", "claim": "verification_candidates", "product": "product_mentions"}
ITEM_SCHEMAS: dict[str, dict[str, Any]] = {}  # filled in main() from the response schema

INCREMENTAL_PROTOCOL = """

## Output protocol for this run (replaces "Output" above)

You do not write one JSON object at the end. You record annotations with tools, as you go:

- Work through the window in order, a stretch at a time. When you have decided the annotations for a stretch, record them with `add_detections`, `add_claims` and `add_products` (each takes a list; several items per call is normal), then continue reading. Thinking between calls is expected: decide, record, move on.
- Every call is checked against the codebook's mechanical rules (label IDs, unit IDs, quotes, required attributes). The reply says which items were accepted and why any were rejected; fix and re-add rejected items if they are worth keeping. Accepted items are final: do not add them again.
- When the whole window is covered, review what you recorded against step 8 of the procedure (missed narratives, co-labels, claims in ads, rebuttals), add anything missing, then call `finish`.
- A window with no health content: call `finish` without adding anything.
"""

SUBMIT_PROTOCOL = """

## Output protocol for this run (replaces "Output" above)

Submit your result with the `submit_annotation` tool instead of writing it as text: one call carrying all three arrays (`detections`, `verification_candidates`, `product_mentions`), with the same fields the schema describes. The tool checks the mechanical rules (label IDs, unit IDs, verbatim quotes, required attributes) and replies with every problem it found. If it reports problems, or if checking your submission makes you notice something you missed, call `submit_annotation` again with the complete corrected annotation (it replaces the previous one). When the submission is right, call `finish`. A window with no health content: submit three empty arrays, then finish.
"""

LOOKUP_NOTE = """

## Label lookup for this run

The label tables below list only each label's ID and name. Before you use a label, and for every candidate you are choosing between, call `lookup_labels` with the IDs (or a parent topic ID, which returns the parent and all its subtopics, or a narrative family name) to read the definitions, boundary notes and examples. The definition decides; do not choose from names alone. You can call it as often as you need.
"""


def strip_big_enums(schema: Any, limit: int = 30) -> Any:
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k == "enum" and isinstance(v, list) and len(v) > limit:
                continue
            out[k] = strip_big_enums(v, limit)
        if schema.get("type") == "string" and "enum" in schema and len(schema["enum"]) > limit:
            out["description"] = "A label ID exactly as spelled in the label tables."
        return out
    if isinstance(schema, list):
        return [strip_big_enums(x, limit) for x in schema]
    return schema


def tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required}}}


def build_tools(mode: str, schema: dict[str, Any]) -> list[dict[str, Any]]:
    props = schema["properties"]
    det = strip_big_enums(props["detections"])
    claim = strip_big_enums(props["verification_candidates"])
    prod = strip_big_enums(props["product_mentions"])
    for arr in (det, claim, prod):
        arr.pop("maxItems", None)
    finish = tool("finish", "Call once, when the whole window is annotated.", {}, [])
    if mode == "incremental":
        return [
            tool("add_detections", "Record detections (topic, narrative, frame, evidence and population labels on spans).", {"detections": det}, ["detections"]),
            tool("add_claims", "Record verification candidates (checkable claims).", {"claims": claim}, ["claims"]),
            tool("add_products", "Record product mentions.", {"products": prod}, ["products"]),
            finish,
        ]
    tools = [
        tool(
            "submit_annotation",
            "Submit the complete annotation of the window (replaces any earlier submission). Replies with every rule violation found.",
            {"detections": det, "verification_candidates": claim, "product_mentions": prod},
            ["detections", "verification_candidates", "product_mentions"],
        ),
        finish,
    ]
    if mode == "lookup":
        tools.insert(0, tool(
            "lookup_labels",
            "Return the full definitions, boundary notes and examples for label IDs, for all subtopics of a parent topic ID, or for all narratives of a family name.",
            {"ids": {"type": "array", "items": {"type": "string"}, "description": "Label IDs, parent topic IDs or narrative family names."}},
            ["ids"],
        ))
    return tools


def bullet(label: dict[str, Any]) -> str:
    examples = "; ".join(label.get("concepts") or []) if isinstance(label.get("concepts"), list) else str(label.get("concepts") or "")
    tail = f" Examples: {examples}." if examples else ""
    return f"- `{label['label_id']}` {label['name']}: {label['definition']}{tail}"


def index_tables(taxonomy: dict[str, Any]) -> str:
    """Label tables with names only, grouped like render_label_tables."""
    labels = taxonomy["labels"]
    domain_names = {d["domain_id"]: d["name"] for d in taxonomy.get("domains", [])}
    out = ["# Label index", "", "These are the only label IDs you may use, spelled exactly as listed. Names only: look definitions up with `lookup_labels`.", "", "## Topic axis", ""]
    children: dict[str, list[dict[str, Any]]] = {}
    for label in labels:
        if label["axis"] == "topic" and label.get("parent"):
            children.setdefault(label["parent"], []).append(label)
    current = None
    for label in labels:
        if label["axis"] != "topic" or label.get("parent"):
            continue
        if label["domain"] != current:
            current = label["domain"]
            out += ["", f"### {domain_names.get(current, current)}"]
        subs = ", ".join(f"`{c['label_id'].split('.', 1)[1]}` {c['name']}" for c in children.get(label["label_id"], []))
        out.append(f"- `{label['label_id']}` {label['name']}" + (f" -- subtopics (`{label['label_id']}.<id>`): {subs}" if subs else ""))
    for axis, title in (("narrative", "Narrative axis"), ("frame", "Frame axis"), ("evidence", "Evidence axis"), ("population", "Population axis")):
        out += ["", f"## {title}", ""]
        family = None
        for label in labels:
            if label["axis"] != axis:
                continue
            if axis == "narrative" and label.get("family") != family:
                family = label.get("family")
                out.append(f"Family `{family}` ({label.get('family_name', '')}):")
            out.append(f"- `{label['label_id']}` {label['name']}")
    return "\n".join(out)


class Lookup:
    def __init__(self, taxonomy: dict[str, Any]) -> None:
        self.labels = {l["label_id"]: l for l in taxonomy["labels"]}
        self.children: dict[str, list[str]] = {}
        self.families: dict[str, list[str]] = {}
        for l in taxonomy["labels"]:
            if l.get("parent"):
                self.children.setdefault(l["parent"], []).append(l["label_id"])
            if l["axis"] == "narrative":
                self.families.setdefault(l.get("family", ""), []).append(l["label_id"])

    def __call__(self, ids: list[str]) -> str:
        out, missing = [], []
        for raw in ids[:40]:
            key = str(raw).strip().strip("`")
            if key in self.families:
                out += [bullet(self.labels[i]) for i in self.families[key]]
            elif key in self.labels:
                out.append(bullet(self.labels[key]))
                out += [bullet(self.labels[i]) for i in self.children.get(key, [])]
            else:
                missing.append(key)
        if missing:
            out.append("Unknown IDs (check the index): " + ", ".join(missing))
        return "\n".join(dict.fromkeys(out))


class Session:
    """One window's annotation state and the checks behind the tools."""

    def __init__(self, window: dict[str, Any], label_axes: dict[str, str]) -> None:
        self.window = window
        self.axes = label_axes
        self.acc: dict[str, list[dict[str, Any]]] = {k: [] for k in KEYS.values()}
        self.finished = False
        self.calls = 0
        self.rejected = 0
        self.submits = 0

    def _probe(self, key: str, item: dict[str, Any]) -> dict[str, Any]:
        probe = {"window_id": self.window["window_id"], "detections": list(self.acc["detections"]), "verification_candidates": [], "product_mentions": []}
        if key == "detections":
            probe["detections"] = [item]
        else:
            probe[key] = [item]
        return probe

    def normalize(self, key: str, item: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        """Tool arguments are not schema-constrained: fill omitted empty arrays,
        drop unknown keys, and name any missing required scalar field."""
        spec = ITEM_SCHEMAS[key]
        props, required = spec["properties"], spec.get("required", list(spec["properties"]))
        item = {k: v for k, v in item.items() if k in props}
        for field in required:
            if field not in item and props[field].get("type") == "array":
                item[field] = []
        missing = [f for f in required if f not in item]
        if missing:
            return None, [f"missing required field(s): {', '.join(missing)}"]
        return item, []

    def check(self, key: str, items: list[Any]) -> tuple[list[dict[str, Any]], list[str]]:
        ok, notes = [], []
        for i, raw in enumerate(items):
            if not isinstance(raw, dict):
                notes.append(f"item {i}: not an object")
                continue
            item, problems = self.normalize(key, raw)
            if item is None:
                notes.append(f"item {i}: rejected: " + "; ".join(problems))
                continue
            probe = self._probe(key, item)
            try:
                result = tl.validate_window_result(probe, self.window, self.axes)
                ok.append(result[key][0])
            except Exception as error:  # noqa: BLE001 - every rejection goes back to the model
                report = tl.ValidationReport()
                try:
                    result = tl.validate_window_result(probe, self.window, self.axes, report)
                except Exception:  # noqa: BLE001
                    result = {key: []}
                if result[key]:
                    ok.append(result[key][0])
                    notes.append(f"item {i}: accepted after repair ({error})")
                else:
                    notes.append(f"item {i}: rejected: {error}")
        self.rejected += sum(1 for n in notes if "rejected" in n)
        return ok, notes

    def add(self, key: str, items: Any) -> str:
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except json.JSONDecodeError:
                return "rejected: the argument must be a JSON array of objects"
        if not isinstance(items, list):
            items = [items]
        ok, notes = self.check(key, items)
        self.acc[key] += ok
        return json.dumps({"accepted": len(ok), "of": len(items), "problems": notes, "recorded_so_far": {k: len(v) for k, v in self.acc.items()}}, ensure_ascii=False)

    def submit(self, args: dict[str, Any]) -> str:
        self.submits += 1
        new = {k: [] for k in KEYS.values()}
        notes: list[str] = []
        saved = self.acc
        self.acc = new
        for key in ("detections", "verification_candidates", "product_mentions"):
            items = args.get(key, [])
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except json.JSONDecodeError:
                    notes.append(f"{key}: not a JSON array")
                    items = []
            ok, problems = self.check(key, items if isinstance(items, list) else [items])
            new[key] = ok
            notes += [f"{key} {p}" for p in problems]
        del saved
        if notes:
            return json.dumps({"status": "submitted with problems; the accepted items are kept unless you resubmit", "accepted": {k: len(v) for k, v in new.items()}, "problems": notes}, ensure_ascii=False)
        return json.dumps({"status": "submitted; no rule violations found", "accepted": {k: len(v) for k, v in new.items()}, "next": "call finish, or resubmit the complete annotation if you want to change it"})

    def result(self) -> tuple[dict[str, Any], dict[str, Any]]:
        merged = {"window_id": self.window["window_id"], **self.acc}
        return tl.validate_response_lenient(merged, self.window, self.axes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="v3")
    ap.add_argument("--name", required=True)
    ap.add_argument("--mode", required=True, choices=("incremental", "submit", "lookup"))
    ap.add_argument("--split", default="all")
    ap.add_argument("--strata", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--windows")
    ap.add_argument("--ids-file")
    ap.add_argument("--out-dir")
    ap.add_argument("--model", default="glm53-w4")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--budget", type=int, default=24000, help="thinking budget per turn (0 = none)")
    ap.add_argument("--max-tokens", type=int, default=40000, help="per turn")
    ap.add_argument("--max-turns", type=int, default=24)
    ap.add_argument("--max-submits", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=256)
    ap.add_argument("--timeout", type=float, default=7200)
    ap.add_argument("--metrics-log")
    ap.add_argument("--priority", action="store_true", help="send per-turn priority (server needs --scheduling-policy priority)")
    args = ap.parse_args()
    if args.metrics_log:
        start_metrics_sampler(Path(args.metrics_log))

    taxonomy = json.loads((REPO / f"benchmark/{args.bench}/taxonomy.json").read_text())
    label_axes = {l["label_id"]: l["axis"] for l in taxonomy["labels"]}
    schema = tl.response_schema(taxonomy)
    for key in KEYS.values():
        ITEM_SCHEMAS[key] = schema["properties"][key]["items"]
    instructions = tl.taxonomy_instructions(taxonomy)
    lookup = None
    if args.mode == "lookup":
        rubric_path, codebook_path = tl.prompt_files(taxonomy)
        rubric = Path(rubric_path).read_text(encoding="utf-8").rstrip()
        codebook = Path(codebook_path).read_text(encoding="utf-8").rstrip()
        instructions = f"{rubric}\n\n{codebook}\n\n{index_tables(taxonomy)}"
        lookup = Lookup(taxonomy)
    instructions += {"incremental": INCREMENTAL_PROTOCOL, "submit": SUBMIT_PROTOCOL, "lookup": SUBMIT_PROTOCOL + LOOKUP_NOTE}[args.mode]
    tools = build_tools(args.mode, schema)
    settings = {"max_tokens": args.max_tokens, "reasoning_effort": args.effort, "temperature": 1.0, "top_p": 0.95}
    if args.budget:
        settings["thinking_token_budget"] = args.budget

    windows = load_windows(argparse.Namespace(windows=args.windows, ids_file=args.ids_file, limit=args.limit, bench=args.bench, split=args.split, strata=args.strata))
    run_dir = Path(args.out_dir) if args.out_dir else REPO / f"benchmark/{args.bench}/runs/{args.name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_manifest.json").write_text(json.dumps({
        "name": args.name, "model": args.model, "provider": "local", "mode": "tools-" + args.mode, "bench": args.bench,
        "prompt_version": "tools-" + args.mode + "-" + tl.sha256_bytes(instructions.encode())[:12],
        "settings": settings, "max_turns": args.max_turns, "items": len(windows), "repeats": 1, "created_at": tl.utc_now(),
    }, indent=2))
    store = Store(run_dir / "repeat_0")
    transcripts = open(run_dir / "repeat_0" / "transcripts.jsonl", "a", encoding="utf-8")
    transcript_lock = __import__("threading").Lock()

    def one(window: dict[str, Any]) -> bool:
        session = Session(window, label_axes)
        messages: list[dict[str, Any]] = [{"role": "system", "content": instructions}, {"role": "user", "content": tl.window_input(window)}]
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "turns": 0, "cached_tokens": 0}
        record: dict[str, Any] = {"attempt": 0, "window_id": window["window_id"], "t_start": round(time.time(), 3)}
        started = time.monotonic()
        error = None
        try:
            for _turn in range(args.max_turns):
                payload = {"model": args.model, "messages": messages, "tools": tools, "tool_choice": "auto", **settings}
                if args.priority:
                    # With --scheduling-policy priority, later turns of a
                    # conversation go ahead of new windows (lower = sooner).
                    payload["priority"] = -usage["turns"]
                response = None
                for attempt in range(3):
                    try:
                        response = xlabel.post(payload, args.timeout)
                        break
                    except Exception as exc:  # noqa: BLE001
                        error = f"{type(exc).__name__}: {exc}"
                        time.sleep(5 * (attempt + 1))
                if response is None:
                    raise RuntimeError(error)
                u = response.get("usage") or {}
                usage["turns"] += 1
                usage["prompt_tokens"] += u.get("prompt_tokens", 0)
                usage["completion_tokens"] += u.get("completion_tokens", 0)
                usage["reasoning_tokens"] += ((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
                usage["cached_tokens"] += ((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
                msg = response["choices"][0]["message"]
                calls = msg.get("tool_calls") or []
                assistant = {"role": "assistant", "content": msg.get("content") or ""}
                reasoning = msg.get("reasoning_content") or msg.get("reasoning")
                if reasoning:
                    assistant["reasoning_content"] = reasoning
                if calls:
                    assistant["tool_calls"] = [{"id": c["id"], "type": "function", "function": {"name": c["function"]["name"], "arguments": c["function"]["arguments"]}} for c in calls]
                messages.append(assistant)
                if not calls:
                    text = (msg.get("content") or "").strip()
                    if text and not any(session.acc.values()):
                        try:
                            parsed = tl.parse_json_output(text)
                            session.submit(parsed)
                            record["fallback"] = "json_content"
                        except Exception:  # noqa: BLE001
                            pass
                    break
                for c in calls:
                    session.calls += 1
                    name = c["function"]["name"]
                    try:
                        fargs = json.loads(c["function"]["arguments"] or "{}")
                    except json.JSONDecodeError:
                        fargs = None
                    if fargs is None:
                        reply = "rejected: arguments were not valid JSON"
                    elif name == "finish":
                        session.finished = True
                        reply = "done"
                    elif name == "add_detections":
                        reply = session.add("detections", fargs.get("detections", []))
                    elif name == "add_claims":
                        reply = session.add("verification_candidates", fargs.get("claims", []))
                    elif name == "add_products":
                        reply = session.add("product_mentions", fargs.get("products", []))
                    elif name == "submit_annotation":
                        if session.submits >= args.max_submits:
                            reply = "submission limit reached; your last submission stands. Call finish."
                        else:
                            reply = session.submit(fargs)
                    elif name == "lookup_labels" and lookup is not None:
                        ids = fargs.get("ids", [])
                        reply = lookup(ids if isinstance(ids, list) else [ids])
                    else:
                        reply = f"unknown tool {name}"
                    messages.append({"role": "tool", "tool_call_id": c["id"], "content": reply})
                if session.finished:
                    break
            result, changes = session.result()
            store.put(window["window_id"], result)
            record.update(ok=True, finished=session.finished, tool_calls=session.calls, rejected_items=session.rejected, submits=session.submits, validation={"mode": "lenient", **changes})
        except Exception as exc:  # noqa: BLE001
            record.update(ok=False, kind=type(exc).__name__, error=str(exc)[:300])
        record.update(usage={"prompt_tokens": usage["prompt_tokens"], "completion_tokens": usage["completion_tokens"], "completion_tokens_details": {"reasoning_tokens": usage["reasoning_tokens"]}, "turns": usage["turns"], "cached_tokens": usage["cached_tokens"]},
                      t_end=round(time.time(), 3), seconds=round(time.monotonic() - started, 3))
        store.attempt(record)
        with transcript_lock:
            transcripts.write(json.dumps({"window_id": window["window_id"], "messages": messages[1:]}, ensure_ascii=False) + "\n")
            transcripts.flush()
        return bool(record.get("ok"))

    todo = [w for w in windows if w["window_id"] not in store.done()]
    started = time.monotonic()
    ok = 0
    with ThreadPoolExecutor(args.concurrency) as pool:
        futures = [pool.submit(one, w) for w in todo]
        for n, future in enumerate(as_completed(futures), 1):
            ok += bool(future.result())
            if n % 20 == 0 or n == len(futures):
                print(f"done={n}/{len(futures)} ok={ok} elapsed={time.monotonic() - started:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
