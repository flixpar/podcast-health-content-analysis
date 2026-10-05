"""Experimental labeling harness for the v7/v8 method comparison.

Sends one window per request to an OpenAI-compatible Chat Completions server
(the local vLLM DeepSeek server by default) with the production prompt and
schema from analysis/topic_labeling.py, plus a few variants the production CLI
does not express:

  standard  the production request (sanity check against `benchmark run`)
  hints     production request + keyword-lexicon cues appended to the window
  refine    production request + a first-pass result to review and complete
  screen    a short screening prompt: does the window contain health content?

Results are written in the benchmark run layout (run_manifest.json,
repeat_N/labels.sqlite with window_labels(window_id, result_json),
repeat_N/attempts.jsonl), so `python -m analysis.benchmark score` reads them.
Screen results are stored as {"window_id", "screen": {...}} rows.

    python exp/xlabel.py --bench v2 --name v7-hints --mode hints --lexicon exp/lexicon-v7.json
    python exp/xlabel.py --bench v3 --name corpus-v8 --windows <windows.jsonl.zst> --out-dir exp/corpus/v8
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from analysis import topic_labeling as tl  # noqa: E402

API = "http://127.0.0.1:8222/v1/chat/completions"
MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"

REFINE_NOTE = (
    "\n\nA first-pass annotation of this window follows. It was made quickly and "
    "usually misses things. Review the window against the codebook: add every "
    "topic, narrative, frame, evidence signal, population, checkable claim and "
    "product mention it missed, correct wrong labels, spans and attributes, and "
    "remove anything the codebook excludes. Return the complete corrected "
    "annotation (not just the changes).\n\nFirst pass:\n"
)

HINTS_NOTE = (
    "\n\nLexical cues: an automatic keyword matcher found the terms below in this "
    "window, with the label each term is associated with. They are often wrong "
    "(a keyword is not a topic: ads, metaphors, time markers and passing words "
    "match too) and they are incomplete. Use them only as a checklist of places "
    "to look; label strictly by the codebook.\n"
)

SCREEN_INSTRUCTIONS = """You screen podcast transcript windows for a health-content labeling study.

Health content means talk about human health, medicine, disease, injury as a health matter, mental health, nutrition and diet as health, fitness and the body, drugs and supplements, health products, health policy and the health system, public health, vaccines, health-related conspiracy narratives, or sponsor reads for health or wellness products.

It does NOT include: COVID or a pandemic only as a time marker ("before COVID"); alcohol, cannabis or drugs only as scenery or party talk; true crime or war narration with no injury or cause of death described as a health matter; sports injury reports only as availability news; loose figurative psychiatric words ("that's so OCD", "narcissist" as an insult); political issue lists that merely name abortion or health care; ads for non-health products.

Answer with JSON: {"health": "none" | "passing" | "substantive", "ad": true|false, "reason": "<= 12 words"}.
- "substantive": at least one stretch actually discusses a health subject, makes a health claim, or reads an ad for a health product.
- "passing": health is only mentioned in passing (one sentence, no development).
- "none": no health content as defined above.
"""

SCREEN_BROAD_INSTRUCTIONS = """You screen podcast transcript windows before an expensive health-content labeler. Missing a window that has any health content is much worse than passing one that has none, so when in doubt, pass it.

Answer "substantive" or "passing" if ANY part of the window touches on health in any way, even briefly: physical or mental health, emotions and psychology (stress, anxiety, depression, trauma, therapy, burnout, addiction), illness, injuries (including sports injuries and fight damage), medicine, drugs, alcohol or smoking as a health matter, sleep, diet, nutrition, food as health, weight, fitness and training, the body, sex and reproduction, pregnancy, babies and child development, ageing, death and dying, violence or abuse that harms someone, health policy, insurance, doctors, hospitals, public health, vaccines, health conspiracies, or an advertisement for any product that makes a health, wellness or body claim (supplements, meal kits sold as healthy, sleep products, deodorant "without aluminum", etc.).

Answer "none" only if nothing health-related comes up at all, or health words appear only as idioms ("that's sick", "I'm dying to see it") or as a pure time marker ("back in 2020 during COVID").

Answer with JSON: {"health": "none" | "passing" | "substantive", "ad": true|false, "reason": "<= 12 words"}.
"""

SCREEN_SCHEMA = {
    "type": "object",
    "properties": {
        "health": {"type": "string", "enum": ["none", "passing", "substantive"]},
        "ad": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["health", "ad", "reason"],
    "additionalProperties": False,
}


def load_windows(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.windows:
        windows = list(tl.iter_jsonl(Path(args.windows)))
        if args.ids_file:
            wanted = set(Path(args.ids_file).read_text().split())
            windows = [w for w in windows if w["window_id"] in wanted]
        return windows[: args.limit] if args.limit else windows
    items = [json.loads(line) for line in open(REPO / f"benchmark/{args.bench}/items.jsonl")]
    if args.split != "all":
        items = [i for i in items if i["split"] == args.split]
    if args.strata:
        items = [i for i in items if i["stratum"] in args.strata]
    keep = ("window_id", "episode_id", "units")
    windows = [{k: i[k] for k in keep if k in i} for i in items]
    return windows[: args.limit] if args.limit else windows


def load_results(run_dir: Path, repeat: int) -> dict[str, dict[str, Any]]:
    db = run_dir / f"repeat_{repeat}" / "labels.sqlite"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return {w: json.loads(r) for w, r in con.execute("SELECT window_id, result_json FROM window_labels")}
    finally:
        con.close()


class Store:
    def __init__(self, repeat_dir: Path) -> None:
        repeat_dir.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(repeat_dir / "labels.sqlite", check_same_thread=False)
        self.con.execute("CREATE TABLE IF NOT EXISTS window_labels (window_id TEXT PRIMARY KEY, result_json TEXT NOT NULL)")
        self.con.commit()
        self.log = open(repeat_dir / "attempts.jsonl", "a", encoding="utf-8")
        self.lock = threading.Lock()

    def done(self) -> set[str]:
        return {r[0] for r in self.con.execute("SELECT window_id FROM window_labels")}

    def put(self, window_id: str, result: dict[str, Any]) -> None:
        with self.lock:
            self.con.execute("INSERT OR REPLACE INTO window_labels VALUES (?, ?)", (window_id, json.dumps(result, ensure_ascii=False)))
            self.con.commit()

    def attempt(self, record: dict[str, Any]) -> None:
        with self.lock:
            self.log.write(json.dumps(record) + "\n")
            self.log.flush()


def post(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(API, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read())


METRICS = (
    "vllm:num_requests_running", "vllm:num_requests_waiting", "vllm:kv_cache_usage_perc",
    "vllm:generation_tokens_total", "vllm:prompt_tokens_total", "vllm:prompt_tokens_cached_total",
    "vllm:prefix_cache_hits_total", "vllm:prefix_cache_queries_total", "vllm:num_preemptions_total",
    "vllm:spec_decode_num_accepted_tokens_total", "vllm:spec_decode_num_draft_tokens_total",
)


def scrape_metrics(base: str) -> dict[str, float]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    text = opener.open(base + "/metrics", timeout=10).read().decode()
    out: dict[str, float] = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        name = line.split("{")[0].split(" ")[0]
        if name in METRICS:
            out[name] = out.get(name, 0.0) + float(line.rsplit(" ", 1)[-1])
    return out


def start_metrics_sampler(path: Path, every: float = 5.0) -> None:
    base = API.split("/v1/")[0]

    def loop() -> None:
        with open(path, "a") as handle:
            while True:
                try:
                    handle.write(json.dumps({"t": round(time.time(), 3), **scrape_metrics(base)}) + "\n")
                    handle.flush()
                except Exception:  # noqa: BLE001 - a missed sample is fine
                    pass
                time.sleep(every)

    threading.Thread(target=loop, daemon=True).start()


def nothink_template() -> str:
    """GLM-5.3's chat template with the generation prompt closing an empty think
    block, so the reasoning parser sees the end of thinking in the prompt and
    structured output applies from the first generated token."""
    path = next(Path("/tmp/huggingface2/hub/models--canada-quant--GLM-5.3-Flash-W4A16-MTP/snapshots").glob("*/chat_template.jinja"))
    text = path.read_text()
    tail = "<|assistant|>{{- '<think>' -}}"
    assert tail in text
    return text.replace(tail, "<|assistant|>{{- '<think></think>' -}}")


def lexicon_cues(window: dict[str, Any], matcher: Any, max_cues: int) -> str:
    rows = []
    seen = set()
    for unit in window["units"]:
        for label, term in matcher.match(unit["text"]):
            if (label, term) in seen:
                continue
            seen.add((label, term))
            rows.append(f"- {unit['unit_id']}: \"{term}\" -> {label}")
    if not rows:
        return "\n\nLexical cues: none (no keyword matched this window; it may still contain health content)."
    return HINTS_NOTE + "\n".join(rows[:max_cues])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench", default="v2", help="benchmark dir (v2 = v7 labels, v3 = v8 labels)")
    parser.add_argument("--name", required=True)
    parser.add_argument("--mode", default="standard", choices=("standard", "hints", "refine", "screen", "screen-broad"))
    parser.add_argument("--split", default="all")
    parser.add_argument("--strata", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--windows", help="label these windows (jsonl.zst) instead of benchmark items")
    parser.add_argument("--ids-file")
    parser.add_argument("--out-dir", help="run directory (default benchmark/<bench>/runs/<name>)")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--effort", default="high")
    parser.add_argument("--budget", type=int, default=24000, help="thinking token budget (0 = none)")
    parser.add_argument("--max-tokens", type=int, default=80000)
    parser.add_argument("--concurrency", type=int, default=128)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=7200)
    parser.add_argument("--base-run", help="refine: run dir whose repeat_N results are the first pass")
    parser.add_argument("--lexicon", help="hints: keyword lexicon JSON (exp/keywords.py format)")
    parser.add_argument("--max-cues", type=int, default=60)
    parser.add_argument("--notes", default="")
    parser.add_argument("--model", default=MODEL, help="served model name")
    parser.add_argument("--metrics-log", help="sample the server's /metrics every 5 s into this jsonl")
    parser.add_argument("--note-file", help="text inserted before the rubric's Procedure section")
    parser.add_argument("--prefill-nothink", action="store_true", help="GLM: continue an assistant turn that opens with an empty think block (thinking off)")
    parser.add_argument("--drop", default="", help="comma list of components to leave out (exp/variants.py)")
    parser.add_argument("--extra", default="{}", help="JSON merged into every request body (e.g. chat_template_kwargs)")
    args = parser.parse_args()
    if args.metrics_log:
        start_metrics_sampler(Path(args.metrics_log))

    taxonomy = json.loads((REPO / f"benchmark/{args.bench}/taxonomy.json").read_text())
    label_axes = {label["label_id"]: label["axis"] for label in taxonomy["labels"]}
    if args.mode in ("screen", "screen-broad"):
        instructions = SCREEN_INSTRUCTIONS if args.mode == "screen" else SCREEN_BROAD_INSTRUCTIONS
        schema, schema_name = SCREEN_SCHEMA, "health_screen"
    else:
        instructions, schema, schema_name = tl.taxonomy_instructions(taxonomy), tl.response_schema(taxonomy), "podcast_topic_clips"
        if args.drop:
            sys.path.insert(0, str(REPO / "exp"))
            import variants

            instructions, schema, label_axes = variants.build(taxonomy, set(args.drop.split(",")))
    if args.note_file:
        note = Path(args.note_file).read_text().strip()
        assert "\n## Procedure" in instructions
        instructions = instructions.replace("\n## Procedure", "\n" + note + "\n\n## Procedure", 1)
    settings = tl.ModelSettings(
        max_output_tokens=args.max_tokens,
        reasoning_effort=args.effort,
        temperature=1.0,
        top_p=0.95,
        thinking_token_budget=args.budget or None,
    )
    matcher = None
    if args.mode == "hints":
        sys.path.insert(0, str(REPO / "exp"))
        from keywords import Lexicon

        matcher = Lexicon.load(Path(args.lexicon))
    windows = load_windows(args)
    run_dir = Path(args.out_dir) if args.out_dir else REPO / f"benchmark/{args.bench}/runs/{args.name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": args.name,
        "model": args.model,
        "provider": "local",
        "mode": args.mode,
        "bench": args.bench,
        "prompt_version": tl.prompt_version(taxonomy) if not args.mode.startswith("screen") else args.mode + "-v1",
        "settings": settings.fingerprint(),
        "base_run": args.base_run,
        "lexicon": args.lexicon,
        "drop": args.drop,
        "note_file": args.note_file,
        "prefill_nothink": args.prefill_nothink,
        "extra": json.loads(args.extra),
        "windows": args.windows,
        "items": len(windows),
        "repeats": args.repeats,
        "notes": args.notes,
        "created_at": tl.utc_now(),
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))

    def one(window: dict[str, Any], store: Store, base: dict[str, Any] | None) -> bool:
        user = tl.window_input(window)
        if args.mode == "hints":
            user += lexicon_cues(window, matcher, args.max_cues)
        elif args.mode == "refine":
            first = (base or {}).get(window["window_id"])
            if first is None:
                return False
            user += REFINE_NOTE + tl.canonical_json(first)
        payload = {"model": args.model, **tl.API_FLAVORS["chat_completions"].payload(instructions, user, schema_name, schema, settings), **json.loads(args.extra)}
        if args.prefill_nothink:
            payload["chat_template"] = nothink_template()
            payload.pop("thinking_token_budget", None)
            # The glm45 reasoning parser files everything before an output
            # </think> as reasoning, and a grammar applied there garbles the
            # keys, so this mode asks for JSON in the prompt only and reads
            # the text from whichever field the parser put it in.
            payload.pop("response_format", None)
        for attempt in range(args.attempts):
            started = time.monotonic()
            record: dict[str, Any] = {"attempt": attempt, "window_id": window["window_id"], "t_start": round(time.time(), 3)}
            try:
                response = post(payload, args.timeout)
                record["usage"] = response.get("usage")
                tl.raise_for_chat_status(response)
                if args.prefill_nothink:
                    message = response["choices"][0]["message"]
                    text = message.get("content") or message.get("reasoning_content") or message.get("reasoning") or ""
                else:
                    text = tl.extract_chat_output_text(response)
                parsed = tl.parse_json_output(text)
                if args.mode.startswith("screen"):
                    result = {"window_id": window["window_id"], "screen": parsed}
                    changes: dict[str, Any] = {}
                else:
                    result, changes = tl.validate_response_lenient(parsed, window, label_axes)
                store.put(window["window_id"], result)
                record.update(ok=True, t_end=round(time.time(), 3), seconds=round(time.monotonic() - started, 3), validation={"mode": "lenient", **changes})
                store.attempt(record)
                return True
            except Exception as error:  # noqa: BLE001 - every failure is logged and retried
                record.update(ok=False, seconds=round(time.monotonic() - started, 3), kind=getattr(error, "kind", type(error).__name__), error=str(error)[:300])
                store.attempt(record)
        return False

    for repeat in range(args.repeats):
        store = Store(run_dir / f"repeat_{repeat}")
        base = load_results(Path(args.base_run), repeat) if args.mode == "refine" else None
        todo = [w for w in windows if w["window_id"] not in store.done()]
        started = time.monotonic()
        ok = 0
        with ThreadPoolExecutor(args.concurrency) as pool:
            futures = [pool.submit(one, w, store, base) for w in todo]
            for n, future in enumerate(as_completed(futures), 1):
                ok += bool(future.result())
                if n % 50 == 0 or n == len(futures):
                    print(f"repeat={repeat} done={n}/{len(futures)} ok={ok} elapsed={time.monotonic() - started:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
