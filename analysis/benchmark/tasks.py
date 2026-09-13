"""Task bundles: the one mechanism through which agents feed the benchmark.

A step (``screen``, ``reference``, ``synthetic``, ``contrast``, ``adjudicate``,
``judge``) writes bundles: self-contained directories under the scratchpad,
each with the inputs an agent needs (items, codebook, schema, instructions)
and nothing else -- no repo paths, no metadata that could leak what the
answer "should" be. An agent writes its output files into the bundle; the
step's ``ingest`` validates every output before anything enters ``benchmark/``.

Bundles are deliberately outside the repository so an agent told to work only
inside its bundle has nothing else to read there.
"""

from __future__ import annotations

import json
import os
import random
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from analysis import topic_labeling as tl
from analysis.benchmark import BENCHMARK_VERSION, CODEBOOK_PATH, REPO_ROOT

TASKS_ROOT_ENV = "BENCHMARK_TASKS_DIR"


def tasks_root() -> Path:
    """Where bundles live: $BENCHMARK_TASKS_DIR, else a sibling of the repo."""
    override = os.environ.get(TASKS_ROOT_ENV)
    if override:
        return Path(override)
    return REPO_ROOT.parent / "podcast-misinfo-benchmark-tasks"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def chunk(rows: Sequence[Any], size: int) -> list[list[Any]]:
    return [list(rows[index : index + size]) for index in range(0, len(rows), size)]


def write_bundles(
    step: str,
    run_id: str,
    bundles: Sequence[Sequence[dict[str, Any]]],
    instructions: str,
    extra_files: dict[str, str] | None = None,
    item_filename: str = "items.json",
    clean: bool = False,
) -> Path:
    """Write one directory per bundle; returns the run directory."""
    root = tasks_root() / step / run_id
    if clean and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "step": step,
        "run_id": run_id,
        "benchmark_version": BENCHMARK_VERSION,
        "created_at": tl.utc_now(),
        "bundles": [],
    }
    for number, rows in enumerate(bundles, 1):
        bundle_dir = root / f"bundle_{number:03d}"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / item_filename).write_text(
            json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        (bundle_dir / "INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")
        for name, text in (extra_files or {}).items():
            (bundle_dir / name).write_text(text, encoding="utf-8")
        manifest["bundles"].append(
            {"dir": str(bundle_dir), "count": len(rows), "ids": [row.get("id") for row in rows]}
        )
    tl.write_json(root / "manifest.json", manifest)
    return root


def read_bundle_outputs(run_dir: Path, pattern: str) -> list[tuple[Path, Any]]:
    """Every output file matching ``pattern`` under the run's bundles, parsed."""
    outputs: list[tuple[Path, Any]] = []
    for path in sorted(Path(run_dir).glob(f"bundle_*/{pattern}")):
        try:
            outputs.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except json.JSONDecodeError as exc:
            outputs.append((path, {"__error__": f"malformed JSON: {exc}"}))
    return outputs


def taxonomy_tables(taxonomy: dict[str, Any]) -> str:
    """The label tables as markdown, one per axis, from the frozen taxonomy."""
    lines: list[str] = ["# Label tables", ""]
    for axis, title in (("topic", "Topic axis"), ("frame", "Frame axis"), ("evidence", "Evidence axis")):
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| label_id | name | definition | example terms |")
        lines.append("| --- | --- | --- | --- |")
        for label in taxonomy["labels"]:
            if label["axis"] != axis:
                continue
            examples = "; ".join(label.get("concepts", []))
            definition = label["definition"].replace("|", "\\|")
            lines.append(f"| `{label['label_id']}` | {label['name']} | {definition} | {examples} |")
        lines.append("")
    return "\n".join(lines)


def codebook_text(taxonomy: dict[str, Any] | None = None) -> str:
    """The codebook, with the label tables appended from the frozen taxonomy."""
    text = CODEBOOK_PATH.read_text(encoding="utf-8")
    if taxonomy is None:
        from analysis.benchmark.taxonomy import load_benchmark_taxonomy

        taxonomy = load_benchmark_taxonomy()
    return text + "\n" + taxonomy_tables(taxonomy)


def shuffled(rows: Sequence[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    out = list(rows)
    random.Random(seed).shuffle(out)
    return out


# --------------------------------------------------------------------------
# Screening
# --------------------------------------------------------------------------

SCREEN_INSTRUCTIONS = """\
# Screening task

You are screening candidate transcript windows for a labeling benchmark. Each
entry in `items.json` is one ~900-word window of a podcast transcript (ASR
output; expect missing punctuation, mis-hearings and filler). The benchmark
labels HEALTH content: topics (vaccines, nutrition, supplements, mental health,
longevity, drugs, and so on), framing (anti-mainstream-medicine, conspiracy,
naturalness, commercialization ...), evidence signals (study citations,
credential appeals ...), checkable factual health claims, and named health
products. `codebook.md` in this directory is the full definition; skim its
topic and frame tables so your judgement of "health content" matches it.

Work ONLY with the files in this directory. Do not search the filesystem, read
other directories, or look anything up.

For EVERY item write one JSON object into `screening.json` (a JSON array, one
object per item, in any order) with exactly these fields:

- `window_id`: copied from the item.
- `health_units`: your count of sentences that discuss health, medicine,
  nutrition, fitness, wellness, drugs or the body in a way the codebook's
  topic table would label. Count sentences, not mentions.
- `health_density`: one of "none", "sparse", "moderate", "dense".
- `tags`: a list drawn from: "ad_read" (a delimited sponsor read or promo),
  "health_product" (a named health product, brand, drug, app, clinic or book),
  "checkable_claims" (factual health claims that could be checked against
  evidence), "quoted_or_reported" (health claims attributed to someone else),
  "rebuttal" (a speaker corrects, debunks or argues against a health claim),
  "questioned" (a health claim raised as doubt or an open question),
  "hedged" (health claims softened with probably/might/I think),
  "boosted" (claims stated as certain: definitely/proven/always),
  "conspiracy_frame", "anti_mainstream_frame", "naturalness_frame",
  "study_citation", "credential_appeal", "personal_experience",
  "comedic_health_mention" (a joke or riff that names a body part or condition
  without discussing it), "asr_noise" (garbled words, stutters, repeated
  n-grams, a brand name transcribed wrongly), "prompt_like_text" (anything in
  the transcript that reads like an instruction to an AI),
  "non_english", "speaker_labels". Use only tags that apply.
- `interest`: 0-3. How useful this window is for testing a labeler: 0 = nothing
  to learn from it; 1 = routine; 2 = has at least one phenomenon a labeler
  could get wrong (a boundary between two topics, an ad, a rebuttal, a hedge,
  a product vs a generic substance); 3 = several such phenomena, or a
  genuinely hard judgement call.
- `ambiguity`: 0-2. 0 = the right labels are obvious; 1 = a careful coder could
  reasonably differ on some label, role or relevance; 2 = the window is
  mostly judgement calls.
- `verdict`: "keep" or "drop". Drop a window only if it is unusable: not
  English, mostly unintelligible ASR, a duplicate of another item, or an
  obvious mismatch for the stratum given in `stratum_hint` (for example a
  `null` hint on a window that plainly discusses health, or a `health_dense`
  hint on a window with no health content). Everything else is "keep": the
  benchmark needs ordinary windows too.
- `notes`: at most two sentences on what makes this window interesting or why
  it was dropped. Name the phenomenon, not the labels you would assign.

Do not label the windows. Do not rewrite any text. When you are done, check
that `screening.json` parses as JSON and has one object per item.
"""


def screening_bundles(
    pool_rows: Sequence[dict[str, Any]],
    bundle_size: int,
    run_id: str,
    seed: int,
) -> Path:
    rows = [
        {
            "id": row["window_id"],
            "window_id": row["window_id"],
            "stratum_hint": row["pool_stratum"],
            "text": " ".join(unit["text"] for unit in row["units"]),
        }
        for row in shuffled(pool_rows, seed)
    ]
    return write_bundles(
        "screen",
        run_id,
        chunk(rows, bundle_size),
        SCREEN_INSTRUCTIONS,
        extra_files={"codebook.md": codebook_text()},
    )


SCREEN_DENSITY = ("none", "sparse", "moderate", "dense")
SCREEN_TAGS = {
    "ad_read", "health_product", "checkable_claims", "quoted_or_reported", "rebuttal",
    "questioned", "hedged", "boosted", "conspiracy_frame", "anti_mainstream_frame",
    "naturalness_frame", "study_citation", "credential_appeal", "personal_experience",
    "comedic_health_mention", "asr_noise", "prompt_like_text", "non_english",
    "speaker_labels",
}


def ingest_screening(run_dir: Path, expected_ids: set[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate screening.json files; returns (rows, problems)."""
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    seen: set[str] = set()
    for path, parsed in read_bundle_outputs(run_dir, "screening.json"):
        if not isinstance(parsed, list):
            problems.append(f"{path}: {parsed.get('__error__', 'not a JSON array') if isinstance(parsed, dict) else 'not a JSON array'}")
            continue
        for entry in parsed:
            if not isinstance(entry, dict) or "window_id" not in entry:
                problems.append(f"{path}: entry without window_id")
                continue
            window_id = entry["window_id"]
            if window_id not in expected_ids:
                problems.append(f"{path}: unknown window_id {window_id}")
                continue
            if window_id in seen:
                problems.append(f"{path}: duplicate window_id {window_id}")
                continue
            errors = []
            if entry.get("health_density") not in SCREEN_DENSITY:
                errors.append("health_density")
            if entry.get("verdict") not in ("keep", "drop"):
                errors.append("verdict")
            tags = entry.get("tags")
            if not isinstance(tags, list) or any(tag not in SCREEN_TAGS for tag in tags):
                errors.append("tags")
            for field, upper in (("interest", 3), ("ambiguity", 2)):
                value = entry.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= upper:
                    errors.append(field)
            if not isinstance(entry.get("health_units"), int):
                errors.append("health_units")
            if errors:
                problems.append(f"{path}: {window_id} invalid fields {errors}")
                continue
            seen.add(window_id)
            rows.append(
                {
                    "window_id": window_id,
                    "health_units": entry["health_units"],
                    "health_density": entry["health_density"],
                    "tags": sorted(set(tags)),
                    "interest": entry["interest"],
                    "ambiguity": entry["ambiguity"],
                    "verdict": entry["verdict"],
                    "notes": str(entry.get("notes", ""))[:500],
                    "bundle": path.parent.name,
                }
            )
    missing = sorted(expected_ids - seen)
    if missing:
        problems.append(f"{len(missing)} windows without a screening entry: {missing[:10]}...")
    return rows, problems


# --------------------------------------------------------------------------
# Reference labeling
# --------------------------------------------------------------------------

REFERENCE_INSTRUCTIONS = """\
# Reference labeling task

You are one of several independent expert coders producing reference labels
for a benchmark. Your labels will be compared with the other coders' to find
where careful readers agree and disagree, so work carefully and independently:
take the reading a careful colleague would defend, be exhaustive, and do not
guess. Quality matters far more than speed.

Work ONLY with the files in this directory, plus the one validation command
below. Do not search the filesystem, read other directories, or look anything
up. Do not use any other knowledge of how these transcripts might have been
labeled before.

## Files

- `codebook.md`: the task definition. Read all of it before starting,
  including the label tables at the end: those are the only label IDs you may
  use, spelled exactly as listed (`topic:...`, `cross_cutting:...`).
- `items.json`: the windows to label. Each has `window_id` and `units`
  (`unit_id`, `text`). Label each window on its own.
- `schema.json`: the JSON Schema of one result object.

## Procedure

1. Read `codebook.md` fully.
2. For each window, in order: read the whole window first, then produce one
   result object following the codebook. Work through the three tasks
   (detections, verification candidates, product mentions) for the window.
   Choose spans by unit IDs from that window. Copy quotes and certainty
   markers verbatim from the units.
3. Write all result objects, one per window, as a JSON array to
   `results.raw.json`. This is your first complete answer; do not edit it
   afterwards.
4. Copy it to `results.json` and validate:

       {validate_command}

   The command prints, for each window, either `ok` or the rejection kinds and
   messages. Fix ONLY what it reports (a quote that is not verbatim, a unit ID
   outside the window, a reversed span, certainty markers that do not agree
   with the level, a duplicate) by correcting `results.json`, and re-run until
   every window is `ok`. Do not drop an annotation just because it was
   rejected; fix its quote or span. Do not add or remove annotations for any
   other reason.
5. Stop when every window validates. Report the number of windows, the total
   detections, candidates and product mentions, and anything in the codebook
   you found ambiguous (one line each).

## Reminders

- Empty arrays are the correct answer for a window with no health content.
- One detection carries labels from one axis only; split across axes.
- `expressed_certainty` is coded from the marker words: `unhedged` means an
  empty `certainty_markers` list; every other level needs verbatim markers.
- Claims carry `relevance` too (`substantive`, `passing`, `advertisement`).
- Quotes are one unbroken run of the transcript, under 30 words where possible.
"""


def result_schema(taxonomy: dict[str, Any]) -> dict[str, Any]:
    """One result object's schema, with the benchmark's claim ``relevance``."""
    result = json.loads(json.dumps(tl.response_schema(taxonomy)))
    claim = result["properties"]["verification_candidates"]["items"]
    claim["properties"]["relevance"] = {"type": "string", "enum": list(tl.ALLOWED_RELEVANCE)}
    claim["required"].append("relevance")
    return result


def reference_bundles(
    items: Sequence[dict[str, Any]],
    annotator_id: str,
    bundle_size: int,
    null_bundle_size: int,
    run_id: str,
    seed: int,
    taxonomy: dict[str, Any],
    validate_command: str,
) -> Path:
    """Bundles of items for one annotator; null windows bundle separately."""
    ordered = shuffled(items, seed)
    nulls = [item for item in ordered if item.get("stratum") == "null"]
    others = [item for item in ordered if item.get("stratum") != "null"]

    def rows(group: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": item["item_id"],
                "window_id": item["window_id"],
                "units": [{"unit_id": u["unit_id"], "text": u["text"]} for u in item["units"]],
            }
            for item in group
        ]

    bundles = [rows(group) for group in chunk(others, bundle_size)] + [
        rows(group) for group in chunk(nulls, null_bundle_size)
    ]
    instructions = REFERENCE_INSTRUCTIONS.replace("{validate_command}", validate_command)
    return write_bundles(
        "reference",
        f"{annotator_id}-{run_id}",
        bundles,
        instructions,
        extra_files={
            "codebook.md": codebook_text(taxonomy),
            "schema.json": json.dumps(result_schema(taxonomy), indent=1),
        },
    )


def validate_results_file(
    path: Path, bundle_items: Sequence[dict[str, Any]], axes: dict[str, str]
) -> list[tuple[str, str | None, str | None]]:
    """(window_id, kind, message) per window; kind None when valid."""
    from analysis.benchmark.references import validate_result

    try:
        parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [("*", "malformed_json", str(exc))]
    if not isinstance(parsed, list):
        return [("*", "schema_shape", "results file must be a JSON array of result objects")]
    by_id = {item["window_id"]: item for item in bundle_items}
    seen: set[str] = set()
    report: list[tuple[str, str | None, str | None]] = []
    for result in parsed:
        window_id = result.get("window_id") if isinstance(result, dict) else None
        if window_id not in by_id:
            report.append((str(window_id), "window_id_mismatch", "not a window in this bundle"))
            continue
        if window_id in seen:
            report.append((window_id, "duplicate_annotation", "window appears twice"))
            continue
        seen.add(window_id)
        try:
            validate_result(result, by_id[window_id], axes)
            report.append((window_id, None, None))
        except tl.TopicLabelingError as exc:
            report.append((window_id, exc.kind, str(exc)))
    for window_id in by_id:
        if window_id not in seen:
            report.append((window_id, "omitted_windows", "no result for this window"))
    return report


def ingest_references(
    run_dir: Path,
    annotator_id: str,
    items_by_window: dict[str, dict[str, Any]],
    axes: dict[str, str],
) -> tuple[int, list[str]]:
    """Store every valid final result as a reference; returns (stored, problems)."""
    from analysis.benchmark.references import store_reference, validate_result

    stored = 0
    problems: list[str] = []
    for bundle_dir in sorted(Path(run_dir).glob("bundle_*")):
        final_path = bundle_dir / "results.json"
        raw_path = bundle_dir / "results.raw.json"
        if not final_path.exists():
            problems.append(f"{bundle_dir.name}: no results.json")
            continue
        bundle_items = json.loads((bundle_dir / "items.json").read_text(encoding="utf-8"))
        expected = {row["window_id"] for row in bundle_items}
        raw_by_id: dict[str, Any] = {}
        if raw_path.exists():
            try:
                raw_list = json.loads(raw_path.read_text(encoding="utf-8"))
                if isinstance(raw_list, list):
                    raw_by_id = {r.get("window_id"): r for r in raw_list if isinstance(r, dict)}
            except json.JSONDecodeError:
                problems.append(f"{bundle_dir.name}: results.raw.json is malformed (kept going)")
        try:
            final_list = json.loads(final_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{bundle_dir.name}: results.json malformed: {exc}")
            continue
        if not isinstance(final_list, list):
            problems.append(f"{bundle_dir.name}: results.json is not an array")
            continue
        seen: set[str] = set()
        for result in final_list:
            window_id = result.get("window_id") if isinstance(result, dict) else None
            item = items_by_window.get(window_id)
            if item is None or window_id not in expected:
                problems.append(f"{bundle_dir.name}: unknown window {window_id}")
                continue
            if window_id in seen:
                problems.append(f"{bundle_dir.name}: duplicate window {window_id}")
                continue
            seen.add(window_id)
            try:
                normalized = validate_result(result, item, axes)
            except tl.TopicLabelingError as exc:
                problems.append(f"{bundle_dir.name}: {window_id} rejected ({exc.kind}): {exc}")
                continue
            store_reference(
                item["item_id"],
                annotator_id,
                normalized,
                raw_by_id.get(window_id),
                {"run_dir": str(run_dir), "bundle": bundle_dir.name, "ingested_at": tl.utc_now()},
            )
            stored += 1
        for window_id in sorted(expected - seen):
            problems.append(f"{bundle_dir.name}: no result for {window_id}")
    return stored, problems


# --------------------------------------------------------------------------
# Adjudication of singleton gold atoms
# --------------------------------------------------------------------------

ADJUDICATE_INSTRUCTIONS = """\
# Adjudication task

Three independent coders labeled each window in `items.json` against
`codebook.md`. Where two or more agreed, the annotation is settled. Each entry
in `items.json` lists the annotations only ONE coder produced (`singletons`),
with the window text and the settled annotations for context. Decide, for
each singleton, whether it is a defensible reading of the codebook.

Read `codebook.md` first, including the label tables at the end. Work only
with the files in this directory.

For every singleton write one object into `adjudication.json` (a JSON array):

```json
{"item_id": "...", "gold_id": "...", "tier": "acceptable" | "rejected", "note": "one sentence"}
```

- `acceptable`: a careful coder could defend it under the codebook, even if
  it is not the reading you would take. A candidate labeler that produces it
  will get credit.
- `rejected`: the codebook does not support it (wrong label for the
  definition, a generic substance coded as a product, an opinion coded as a
  checkable claim, a comedic aside coded substantive, a span that does not
  contain the labeled material). A candidate labeler that produces it will be
  penalised.

Judge the annotation, not the coder. Do not add annotations of your own and
do not revisit the settled ones. When unsure, prefer `acceptable`: the cost of
rejecting a defensible reading is higher than the cost of accepting a weak one.
"""


def adjudication_bundles(
    items: Sequence[dict[str, Any]],
    gold_records: Sequence[dict[str, Any]],
    run_id: str,
    per_bundle: int = 8,
    seed: int = 0,
) -> Path:
    by_item: dict[str, list[dict[str, Any]]] = {}
    for record in gold_records:
        by_item.setdefault(record["item_id"], []).append(record)
    rows: list[dict[str, Any]] = []
    for item in items:
        records = by_item.get(item["item_id"], [])
        singletons = [r for r in records if r["tier"] == "singleton"]
        if not singletons:
            continue
        units = item["units"]
        order = {u["unit_id"]: i for i, u in enumerate(units)}

        def span_text(record: dict[str, Any]) -> str:
            a, b = order[record["envelope"][0]], order[record["envelope"][1]]
            return " ".join(u["text"] for u in units[a : b + 1])

        def describe(record: dict[str, Any]) -> dict[str, Any]:
            return {
                "gold_id": record["gold_id"],
                "kind": record["kind"],
                "label": record.get("label"),
                "span": record["envelope"],
                "span_text": span_text(record),
                "quotes": record.get("quotes", []),
                "claim_texts": record.get("claim_texts", []),
                "product_names": record.get("product_names", []),
                "attributes": {k: max(v, key=v.get) for k, v in record.get("votes", {}).items()},
                "coders": len(record.get("annotators", [])),
            }

        rows.append(
            {
                "id": item["item_id"],
                "item_id": item["item_id"],
                "window_text": " ".join(f"[{u['unit_id']}] {u['text']}" for u in units),
                "settled": [describe(r) for r in records if r["tier"] != "singleton"],
                "singletons": [describe(r) for r in singletons],
            }
        )
    rows = shuffled(rows, seed)
    return write_bundles(
        "adjudicate",
        run_id,
        chunk(rows, per_bundle),
        ADJUDICATE_INSTRUCTIONS,
        extra_files={"codebook.md": codebook_text()},
    )


def ingest_adjudication(run_dir: Path, valid_ids: dict[tuple[str, str], str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Verdict rows from every bundle; ``valid_ids`` maps (item_id, gold_id) of each singleton to its member key."""
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for path, parsed in read_bundle_outputs(run_dir, "adjudication.json"):
        if not isinstance(parsed, list):
            problems.append(f"{path}: not a JSON array")
            continue
        for entry in parsed:
            if not isinstance(entry, dict):
                problems.append(f"{path}: non-object entry")
                continue
            key = (entry.get("item_id"), entry.get("gold_id"))
            if key not in valid_ids:
                problems.append(f"{path}: unknown singleton {key}")
                continue
            if entry.get("tier") not in ("acceptable", "rejected"):
                problems.append(f"{path}: {key} bad tier {entry.get('tier')!r}")
                continue
            rows.append({"item_id": key[0], "gold_id": key[1], "member": valid_ids[key], "tier": entry["tier"], "note": str(entry.get("note", ""))[:300], "bundle": path.parent.name, "decided_at": tl.utc_now()})
    return rows, problems
