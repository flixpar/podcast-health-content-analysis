"""Prompt and schema variants of the v7/v8 labeling request.

`build(taxonomy, drop=..., ...)` returns (instructions, schema, label_axes) for
a request that labels only part of the task: dropped detection axes lose their
codebook section, label table and schema enum entries; dropped claims or
products lose their codebook sections and their output array is forced empty
(maxItems 0). A short scope note at the top says what is out of scope, since
the rubric's procedure and worked example still mention every part.

Components: claims, products, narrative, frame, evidence, population.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from analysis import topic_labeling as tl  # noqa: E402

AXES = ("narrative", "frame", "evidence", "population")
SECTIONS = {
    "claims": ("### 4.2 Verification candidates", "## 7. Verification candidates in detail"),
    "products": ("### 4.3 Product mentions", "## 8. Product mentions in detail"),
    "narrative": ("### 5.2 Narrative",),
    "frame": ("### 5.3 Frame",),
    "evidence": ("### 5.4 Evidence",),
    "population": ("### 5.5 Population",),
}
TABLE_HEADINGS = {"narrative": "## Narrative axis", "frame": "## Frame axis", "evidence": "## Evidence axis", "population": "## Population axis"}
SCOPE_TEXT = {
    "claims": "verification candidates (claims): return `verification_candidates` as an empty array",
    "products": "product mentions: return `product_mentions` as an empty array",
    "narrative": "the narrative axis: no `narrative:` detections, and empty `narrative_ids` on claims",
    "frame": "the frame axis: no `frame:` detections, and empty `frame_ids` on claims",
    "evidence": "the evidence axis: no `evidence:` detections, and empty `evidence_signal_ids` on claims",
    "population": "the population axis: no `population:` detections",
}


def drop_sections(text: str, headings: list[str]) -> str:
    lines = text.split("\n")
    out: list[str] = []
    skip_level = 0
    for line in lines:
        m = re.match(r"^(#{1,6}) ", line)
        if m:
            level = len(m.group(1))
            if skip_level and level <= skip_level:
                skip_level = 0
            if not skip_level and any(line.startswith(h) for h in headings):
                skip_level = level
                continue
        if not skip_level:
            out.append(line)
    return "\n".join(out)


def _empty_array(node: dict[str, Any]) -> None:
    node["maxItems"] = 0
    node.pop("minItems", None)


def build(taxonomy: dict[str, Any], drop: set[str], scope_note: bool = True) -> tuple[str, dict[str, Any], dict[str, str]]:
    unknown = drop - set(SECTIONS)
    if unknown:
        raise ValueError(f"unknown components {unknown}")
    full_schema = tl.response_schema(taxonomy)
    rubric_path, codebook_path = tl.prompt_files(taxonomy)
    rubric = Path(rubric_path).read_text(encoding="utf-8").rstrip()
    codebook = Path(codebook_path).read_text(encoding="utf-8").rstrip()
    tables = tl.render_label_tables(taxonomy)
    codebook = drop_sections(codebook, [h for c in drop for h in SECTIONS[c]])
    tables = drop_sections(tables, [TABLE_HEADINGS[c] for c in drop if c in TABLE_HEADINGS])
    if scope_note and drop:
        note = (
            "**Scope of this run.** This run annotates only part of the codebook. Leave out "
            + "; ".join(SCOPE_TEXT[c] for c in sorted(drop))
            + ". The procedure, calibration and worked example below still mention these parts; skip them, "
            "and spend no thinking on them. Everything else is labeled exactly as the codebook says.\n\n"
        )
        rubric = rubric.replace("\n## Procedure", "\n" + note + "## Procedure", 1)
    instructions = f"{rubric}\n\n{codebook}\n\n{tables}"

    schema = copy.deepcopy(full_schema)
    dropped_ids = {l["label_id"] for l in taxonomy["labels"] if l["axis"] in drop}
    det = schema["properties"]["detections"]["items"]
    enum = det["properties"]["label_ids"]["items"]["enum"]
    det["properties"]["label_ids"]["items"]["enum"] = [x for x in enum if x not in dropped_ids]
    if "axis" in det["properties"] and "enum" in det["properties"]["axis"]:
        det["properties"]["axis"]["enum"] = [a for a in det["properties"]["axis"]["enum"] if a not in drop]
    claim = schema["properties"]["verification_candidates"]
    for field, axis in (("narrative_ids", "narrative"), ("frame_ids", "frame"), ("evidence_signal_ids", "evidence")):
        if axis in drop and field in claim["items"]["properties"]:
            _empty_array(claim["items"]["properties"][field])
    if "claims" in drop:
        _empty_array(claim)
    if "products" in drop:
        _empty_array(schema["properties"]["product_mentions"])
    # Validate against the full label set: the validator infers the claim
    # shape (v7 fields such as narrative_ids) from which axes exist, and the
    # schema already keeps dropped labels out of the output.
    label_axes = {l["label_id"]: l["axis"] for l in taxonomy["labels"]}
    return instructions, schema, label_axes


if __name__ == "__main__":
    import json

    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(next(Path("/tmp/huggingface2/hub/models--canada-quant--GLM-5.3-Flash-W4A16-MTP/snapshots").glob("*/tokenizer.json"))))
    tax = json.loads((REPO / f"benchmark/{sys.argv[1]}/taxonomy.json").read_text())
    for spec in sys.argv[2:]:
        drop = set(filter(None, spec.split(",")))
        ins, schema, axes = build(tax, drop)
        print(f"{spec or '(full)':45s} prompt tokens {len(tok.encode(ins).ids):6d}  labels {len(axes)}")
