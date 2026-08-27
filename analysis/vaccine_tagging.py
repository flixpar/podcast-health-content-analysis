#!/usr/bin/env python3
"""Preliminary retrieval and LLM tagging of vaccine-related podcast clips.

The scanner is intentionally high-recall. It searches timestamped ASR segments,
not the duplicate episode-level summary, and extracts bounded text windows around
vaccine terms. The tagger sends batches of those windows to an OpenAI-compatible
chat-completions endpoint and produces clip- and episode-level outputs.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import zstandard


DEFAULT_DATA_ROOT = Path("/tmp/fparker9/podcasts")
DEFAULT_BATCH = "audio-batch-20260826T161741Z-cbb43833"
DEFAULT_TRANSCRIPTS = DEFAULT_DATA_ROOT / "qwen3-asr" / DEFAULT_BATCH / "transcripts"
DEFAULT_MANIFEST = DEFAULT_DATA_ROOT / DEFAULT_BATCH / "manifest.jsonl"
DEFAULT_OUTPUT = Path("analysis/output/vaccine-preliminary")
DEFAULT_API_BASE = "http://127.0.0.1:8222/v1"

# Strong terms stand alone. Contextual expressions are restricted to nearby
# vaccine/disease language so that ordinary uses of "shot" and "booster" do not
# swamp the candidate set.
STRONG_RE = re.compile(
    r"(?ix)\b(?:"
    r"vaccin(?:e|es|ated|ating|ation|ations)|"
    r"anti[- ]?vax(?:x|xer|xers|xing)?|vax(?:xed|xing)?|"
    r"unvaccinated|immuni[sz](?:e|ed|es|ing|ation|ations)|"
    r"m\s*[- ]?rna|VAERS|Gardasil|"
    r"myocarditis|pericarditis"
    r")\b"
)
CONTEXT_RE = re.compile(
    r"(?ix)\b(?:"
    r"(?:covid(?:[- ]?19)?|coronavirus|flu|influenza|hpv|measles|mumps|rubella|"
    r"polio|pertussis|whooping cough|tetanus|shingles|smallpox|chickenpox|"
    r"hepatitis|meningitis|pneumococcal|rsv|childhood)\s+(?:shot|shots|jab|jabs|booster|boosters)|"
    r"(?:shot|shots|jab|jabs|booster|boosters)\s+(?:for|against)\s+(?:covid|"
    r"coronavirus|the flu|influenza|hpv|measles|polio|pertussis|tetanus|shingles|rsv)|"
    r"(?:first|second|third|fourth|updated|bivalent)\s+(?:covid\s+(?:shot|jab|booster)|booster)|"
    r"herd immunity|vaccine passport|medical exemption"
    r")\b"
)
FILE_ID_RE = re.compile(r"episode_(\d+)\.jsonl\.zst$")

ALLOWED = {
    "content_type": {
        "substantive_discussion",
        "passing_mention",
        "advertisement_or_psa",
        "metaphor_or_false_positive",
        "asr_unclear",
    },
    "stance": {"supportive", "hesitant", "critical", "mixed", "neutral", "unclear"},
    "claim_type": {"explicit_claim", "personal_anecdote", "question", "none", "unclear"},
}

SYSTEM_PROMPT = """You are coding noisy podcast ASR excerpts for research triage.
Return only JSON matching the requested schema. Analyze what the excerpt says; do
not supply outside facts and do not decide whether a medical claim is actually
true. A clip is relevant when vaccination, immunization, vaccine policy, uptake,
safety, efficacy, development, or vaccine misinformation is genuinely discussed.

Coding guidance:
- Mark relevant=true when vaccination is the focus of at least one meaningful
  sentence. Vaccine-focused advertisements/PSAs count as relevant and must be
  tagged advertisement_or_psa. Incidental timing references ("when I was
  vaccinated") and generic pharmaceutical disclaimers merely saying to tell a
  doctor about vaccines are not relevant.
- Stance is the apparent stance of the speech in the excerpt toward vaccination,
  not your own view. Use neutral for descriptive/news/fact-check framing and mixed
  when multiple views are voiced without a dominant resolution.
- "potential_misinformation" means the excerpt contains a check-worthy factual
  assertion that questions accepted vaccine safety/efficacy, alleges concealment
  or conspiracy, or gives a strongly misleading-sounding causal claim. This is a
  triage flag, NOT a verdict. Do not flag mere hesitancy, policy disagreement, a
  question, or an excerpt explicitly rebutting a claim unless it also endorses it.
- "corrective_context" means the excerpt challenges, contextualizes, or rebuts a
  vaccine-related misconception or contested claim.
- notable_score is 1 (incidental/poor audio) through 5 (specific, consequential,
  unusual, or especially useful for qualitative review).
- Keep claim_summary factual, neutral, and at most 35 words. Use null when there
  is no concrete claim or anecdote. Rationale must be at most 25 words.
- Use only the supplied topic labels.
"""

TOPICS = [
    "covid19",
    "influenza",
    "childhood_schedule",
    "mmr_measles",
    "hpv",
    "polio",
    "other_vaccine",
    "mandates_or_policy",
    "safety_or_side_effects",
    "efficacy_or_immunity",
    "development_or_approval",
    "conspiracy_or_institutional_trust",
    "personal_decision_or_uptake",
    "access_or_equity",
    "misinformation_or_fact_checking",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Retrieve high-recall candidate clips")
    scan.add_argument("--transcripts", type=Path, default=DEFAULT_TRANSCRIPTS)
    scan.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    scan.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    scan.add_argument("--window-chars", type=int, default=1800)
    scan.add_argument("--merge-distance", type=int, default=2400)
    scan.add_argument("--limit", type=int, help="Only scan this many episodes (smoke tests)")

    tag = subparsers.add_parser("tag", help="Classify candidate clips with a local LLM")
    tag.add_argument("--candidates", type=Path, default=DEFAULT_OUTPUT / "candidates.jsonl")
    tag.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    tag.add_argument("--api-base", default=DEFAULT_API_BASE)
    tag.add_argument("--model", help="Model ID; auto-detected from /v1/models by default")
    tag.add_argument("--batch-size", type=int, default=6)
    tag.add_argument("--concurrency", type=int, default=8)
    tag.add_argument("--max-tokens", type=int, default=3500)
    tag.add_argument("--limit", type=int, help="Only tag this many candidates")
    tag.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)

    report = subparsers.add_parser("report", help="Build episode table and Markdown brief")
    report.add_argument("--tags", type=Path, default=DEFAULT_OUTPUT / "clip_tags.jsonl")
    report.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    report.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    report.add_argument("--top-n", type=int, default=20)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def load_manifest(path: Path) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    episodes: dict[int, dict[str, Any]] = {}
    batch: dict[str, Any] = {}
    for record in read_jsonl(path):
        if record.get("record_type") == "batch":
            batch = record
        elif record.get("record_type") == "episode":
            episodes[int(record["episode_id"])] = record
    return episodes, batch


def episode_sort_key(path: Path) -> int:
    match = FILE_ID_RE.search(path.name)
    return int(match.group(1)) if match else sys.maxsize


def iter_segments(path: Path) -> Iterable[dict[str, Any]]:
    decompressor = zstandard.ZstdDecompressor()
    with path.open("rb") as compressed, decompressor.stream_reader(compressed) as reader:
        import io

        with io.TextIOWrapper(reader, encoding="utf-8") as text_stream:
            for line in text_stream:
                record = json.loads(line)
                if record.get("type") == "segment":
                    yield record


def find_matches(text: str) -> list[tuple[int, int, str, str]]:
    matches: list[tuple[int, int, str, str]] = []
    for rule, pattern in (("strong_term", STRONG_RE), ("contextual_term", CONTEXT_RE)):
        matches.extend((m.start(), m.end(), m.group(0), rule) for m in pattern.finditer(text))
    return sorted(matches)


def group_matches(
    matches: list[tuple[int, int, str, str]], merge_distance: int
) -> list[list[tuple[int, int, str, str]]]:
    groups: list[list[tuple[int, int, str, str]]] = []
    for match in matches:
        if not groups or match[0] - groups[-1][-1][1] > merge_distance:
            groups.append([match])
        else:
            groups[-1].append(match)
    return groups


def clean_boundary(text: str, position: int, direction: int) -> int:
    """Move a clip boundary to a nearby whitespace without expensive NLP."""
    if position <= 0:
        return 0
    if position >= len(text):
        return len(text)
    stop = max(0, position - 100) if direction < 0 else min(len(text), position + 100)
    indexes = range(position, stop, direction)
    for index in indexes:
        if text[index - 1 : index].isspace():
            return index
    return position


def approximate_time(segment: dict[str, Any], char_position: int, text_length: int) -> float:
    start = float(segment["start"])
    end = float(segment["end"])
    if not text_length:
        return start
    return start + (end - start) * char_position / text_length


def scan_candidates(args: argparse.Namespace) -> None:
    metadata, batch = load_manifest(args.manifest)
    files = sorted(args.transcripts.glob("episode_*.jsonl.zst"), key=episode_sort_key)
    if args.limit:
        files = files[: args.limit]
    candidates: list[dict[str, Any]] = []
    matched_episodes: set[int] = set()

    for file_number, path in enumerate(files, 1):
        episode_id = episode_sort_key(path)
        episode_clip_index = 0
        for segment in iter_segments(path):
            text = segment.get("text", "")
            matches = find_matches(text)
            for group in group_matches(matches, args.merge_distance):
                left = clean_boundary(text, max(0, group[0][0] - args.window_chars), -1)
                right = clean_boundary(text, min(len(text), group[-1][1] + args.window_chars), 1)
                episode_clip_index += 1
                matched_episodes.add(episode_id)
                meta = metadata.get(episode_id, {})
                clip_start = approximate_time(segment, left, len(text))
                clip_end = approximate_time(segment, right, len(text))
                candidates.append(
                    {
                        "candidate_id": f"episode_{episode_id}_clip_{episode_clip_index}",
                        "episode_id": episode_id,
                        "podcast_id": meta.get("podcast_id"),
                        "podcast_title": meta.get("podcast_title"),
                        "episode_title": meta.get("episode_title") or segment.get("episode_title"),
                        "published_date": meta.get("published_date"),
                        "duration_seconds": meta.get("duration_seconds"),
                        "source_file": str(path),
                        "segment_index": segment.get("index"),
                        "segment_start_seconds": segment.get("start"),
                        "segment_end_seconds": segment.get("end"),
                        "clip_start_seconds_estimated": round(clip_start, 1),
                        "clip_end_seconds_estimated": round(clip_end, 1),
                        "match_terms": sorted({m[2].lower() for m in group}),
                        "retrieval_rules": sorted({m[3] for m in group}),
                        "text": text[left:right].strip(),
                    }
                )
        if file_number % 1000 == 0:
            print(
                f"scanned={file_number}/{len(files)} candidates={len(candidates)} "
                f"matched_episodes={len(matched_episodes)}",
                file=sys.stderr,
            )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "candidates.jsonl", candidates)
    summary = {
        "source_batch": batch,
        "transcript_directory": str(args.transcripts),
        "manifest": str(args.manifest),
        "episodes_scanned": len(files),
        "episodes_with_candidates": len(matched_episodes),
        "candidate_clips": len(candidates),
        "retrieval_note": (
            "High-recall lexical screen over timestamped ASR segments; candidate counts are not "
            "substantive vaccination-content estimates until LLM filtering and human review."
        ),
    }
    (args.output_dir / "scan_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


def make_opener() -> urllib.request.OpenerDirector:
    # Explicitly bypass environment HTTP proxies for the local vLLM server.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 300) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with make_opener().open(request, timeout=timeout) as response:
        return json.load(response)


def discover_model(api_base: str) -> str:
    response = api_json(api_base.rstrip("/") + "/models")
    return response["data"][0]["id"]


def batches(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def batch_prompt(rows: list[dict[str, Any]]) -> str:
    excerpts = [
        {
            "candidate_id": row["candidate_id"],
            "podcast_title": row.get("podcast_title"),
            "episode_title": row.get("episode_title"),
            "published_date": row.get("published_date"),
            "retrieval_terms": row.get("match_terms"),
            "excerpt": row["text"],
        }
        for row in rows
    ]
    return (
        "Code every excerpt below. Topic labels must come from this list: "
        + json.dumps(TOPICS)
        + "\n\nEXCERPTS:\n"
        + json.dumps(excerpts, ensure_ascii=False)
    )


def response_schema() -> dict[str, Any]:
    item = {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string"},
            "relevant": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "content_type": {"type": "string", "enum": sorted(ALLOWED["content_type"])},
            "stance": {"type": "string", "enum": sorted(ALLOWED["stance"])},
            "topics": {"type": "array", "items": {"type": "string", "enum": TOPICS}},
            "claim_type": {"type": "string", "enum": sorted(ALLOWED["claim_type"])},
            "claim_summary": {"type": ["string", "null"]},
            "potential_misinformation": {"type": "boolean"},
            "corrective_context": {"type": "boolean"},
            "personal_medical_advice": {"type": "boolean"},
            "politicized": {"type": "boolean"},
            "notable_score": {"type": "integer", "minimum": 1, "maximum": 5},
            "rationale": {"type": "string"},
        },
        "required": [
            "candidate_id",
            "relevant",
            "confidence",
            "content_type",
            "stance",
            "topics",
            "claim_type",
            "claim_summary",
            "potential_misinformation",
            "corrective_context",
            "personal_medical_advice",
            "politicized",
            "notable_score",
            "rationale",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"results": {"type": "array", "items": item}},
        "required": ["results"],
        "additionalProperties": False,
    }


def classify_batch(
    rows: list[dict[str, Any]], api_base: str, model: str, max_tokens: int
) -> list[dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": batch_prompt(rows)},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "vaccine_clip_tags",
                "strict": True,
                "schema": response_schema(),
            },
        },
    }
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = api_json(api_base.rstrip("/") + "/chat/completions", payload)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            by_id = {result["candidate_id"]: result for result in parsed["results"]}
            missing = [row["candidate_id"] for row in rows if row["candidate_id"] not in by_id]
            if missing:
                raise ValueError(f"model omitted candidate IDs: {missing}")
            return [by_id[row["candidate_id"]] for row in rows]
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(2**attempt)
    raise RuntimeError(f"classification failed after 3 attempts: {last_error}")


def tag_candidates(args: argparse.Namespace) -> None:
    candidates = read_jsonl(args.candidates)
    if args.limit:
        candidates = candidates[: args.limit]
    output_path = args.output_dir / "clip_tags.jsonl"
    existing = read_jsonl(output_path) if args.resume and output_path.exists() else []
    done_ids = {row["candidate_id"] for row in existing}
    remaining = [row for row in candidates if row["candidate_id"] not in done_ids]
    model = args.model or discover_model(args.api_base)
    work = list(batches(remaining, args.batch_size))
    print(
        f"model={model} candidates={len(candidates)} existing={len(existing)} "
        f"remaining={len(remaining)} requests={len(work)}",
        file=sys.stderr,
    )

    new_tags: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(classify_batch, group, args.api_base, model, args.max_tokens): group
            for group in work
        }
        for completed, future in enumerate(concurrent.futures.as_completed(futures), 1):
            group = futures[future]
            try:
                results = future.result()
                for candidate, result in zip(group, results, strict=True):
                    new_tags.append({**candidate, **result, "tagging_model": model})
            except Exception as error:  # retain IDs so failed batches can be retried
                failures.append(
                    {"candidate_ids": [row["candidate_id"] for row in group], "error": str(error)}
                )
            if completed % 10 == 0 or completed == len(work):
                print(
                    f"requests={completed}/{len(work)} tagged={len(new_tags)} failures={len(failures)}",
                    file=sys.stderr,
                )
            if completed % 25 == 0:
                checkpoint = sorted(
                    existing + new_tags,
                    key=lambda row: (row["episode_id"], row["candidate_id"]),
                )
                write_jsonl(output_path, checkpoint)

    all_tags = sorted(existing + new_tags, key=lambda row: (row["episode_id"], row["candidate_id"]))
    write_jsonl(output_path, all_tags)
    write_jsonl(args.output_dir / "tagging_failures.jsonl", failures)
    summary = {
        "model": model,
        "candidates_requested": len(candidates),
        "candidates_tagged": len(all_tags),
        "new_tags": len(new_tags),
        "failed_batches": len(failures),
    }
    (args.output_dir / "tagging_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


def format_time(seconds: float | int | None) -> str:
    if seconds is None:
        return "?"
    seconds = max(0, int(float(seconds)))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def truncate(text: str | None, length: int = 240) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= length else compact[: length - 1].rstrip() + "…"


def matched_excerpt(row: dict[str, Any], length: int = 320) -> str:
    """Show report text near a retrieval term instead of the window's ad-heavy start."""
    compact = re.sub(r"\s+", " ", row.get("text", "")).strip()
    positions = [
        compact.lower().find(term.lower())
        for term in row.get("match_terms", [])
        if compact.lower().find(term.lower()) >= 0
    ]
    if not positions:
        return truncate(compact, length)
    center = min(positions)
    left = max(0, center - length // 2)
    right = min(len(compact), left + length)
    if left:
        first_space = compact.find(" ", left)
        left = first_space + 1 if first_space >= 0 else left
    if right < len(compact):
        last_space = compact.rfind(" ", left, right)
        right = last_space if last_space >= 0 else right
    return ("…" if left else "") + compact[left:right] + ("…" if right < len(compact) else "")


def episode_rows(relevant: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in relevant:
        grouped[int(row["episode_id"])].append(row)
    episodes: list[dict[str, Any]] = []
    for episode_id, clips in grouped.items():
        exemplar = max(clips, key=lambda row: (row["notable_score"], row["confidence"]))
        episodes.append(
            {
                "episode_id": episode_id,
                "podcast_id": exemplar.get("podcast_id"),
                "podcast_title": exemplar.get("podcast_title"),
                "episode_title": exemplar.get("episode_title"),
                "published_date": exemplar.get("published_date"),
                "relevant_clip_count": len(clips),
                "max_notable_score": max(row["notable_score"] for row in clips),
                "max_confidence": max(row["confidence"] for row in clips),
                "stances": ";".join(sorted({row["stance"] for row in clips})),
                "topics": ";".join(sorted({topic for row in clips for topic in row["topics"]})),
                "potential_misinformation": any(row["potential_misinformation"] for row in clips),
                "corrective_context": any(row["corrective_context"] for row in clips),
                "politicized": any(row["politicized"] for row in clips),
                "top_candidate_id": exemplar["candidate_id"],
                "top_clip_start_estimated": exemplar.get("clip_start_seconds_estimated"),
                "top_claim_summary": exemplar.get("claim_summary"),
            }
        )
    return sorted(
        episodes,
        key=lambda row: (
            -int(row["max_notable_score"]),
            -int(row["relevant_clip_count"]),
            -float(row["max_confidence"]),
            int(row["episode_id"]),
        ),
    )


def select_diverse_clips(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """Keep the meeting brief broad; the CSV still retains the full score ordering."""
    ranked = sorted(
        rows,
        key=lambda row: (-row["notable_score"], -row["confidence"], row["episode_id"]),
    )
    selected: list[dict[str, Any]] = []
    seen_episodes: set[int] = set()
    podcast_counts: Counter[str] = Counter()
    for row in ranked:
        podcast = row.get("podcast_title") or "(unknown)"
        if row["episode_id"] in seen_episodes or podcast_counts[podcast] >= 2:
            continue
        selected.append(row)
        seen_episodes.add(row["episode_id"])
        podcast_counts[podcast] += 1
        if len(selected) >= count:
            break
    return selected


def markdown_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def make_report(args: argparse.Namespace) -> None:
    all_tags = read_jsonl(args.tags)
    manifest_episodes, _ = load_manifest(args.manifest)
    relevant = [row for row in all_tags if row.get("relevant")]
    routine_promotions = [
        row
        for row in relevant
        if row["content_type"] == "advertisement_or_psa"
        and row["notable_score"] <= 2
        and not row["potential_misinformation"]
        and not row["corrective_context"]
    ]
    routine_promotion_ids = {row["candidate_id"] for row in routine_promotions}
    analysis_clips = [row for row in relevant if row["candidate_id"] not in routine_promotion_ids]
    episodes = episode_rows(analysis_clips)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = args.output_dir / "episodes.csv"
    if episodes:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(episodes[0]))
            writer.writeheader()
            writer.writerows(episodes)
    else:
        csv_path.write_text("episode_id\n", encoding="utf-8")

    review_rows = []
    for row in sorted(
        analysis_clips,
        key=lambda item: (-item["notable_score"], -item["confidence"], item["episode_id"]),
    ):
        review_rows.append(
            {
                "candidate_id": row["candidate_id"],
                "episode_id": row["episode_id"],
                "podcast_title": row.get("podcast_title"),
                "episode_title": row.get("episode_title"),
                "published_date": row.get("published_date"),
                "clip_start_seconds_estimated": row.get("clip_start_seconds_estimated"),
                "clip_end_seconds_estimated": row.get("clip_end_seconds_estimated"),
                "segment_start_seconds": row.get("segment_start_seconds"),
                "segment_end_seconds": row.get("segment_end_seconds"),
                "notable_score": row["notable_score"],
                "confidence": row["confidence"],
                "content_type": row["content_type"],
                "stance": row["stance"],
                "topics": ";".join(row["topics"]),
                "claim_type": row["claim_type"],
                "claim_summary": row.get("claim_summary"),
                "potential_misinformation": row["potential_misinformation"],
                "corrective_context": row["corrective_context"],
                "personal_medical_advice": row["personal_medical_advice"],
                "politicized": row["politicized"],
                "matched_excerpt": matched_excerpt(row),
                "source_file": row.get("source_file"),
                "segment_index": row.get("segment_index"),
            }
        )
    review_path = args.output_dir / "review_queue.csv"
    if review_rows:
        with review_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
            writer.writeheader()
            writer.writerows(review_rows)
    else:
        review_path.write_text("candidate_id\n", encoding="utf-8")

    corpus_by_podcast: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in manifest_episodes.values():
        corpus_by_podcast[episode.get("podcast_title") or "(unknown)"].append(episode)
    tagged_episode_sets: dict[str, set[int]] = defaultdict(set)
    analysis_episode_sets: dict[str, set[int]] = defaultdict(set)
    promo_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    corrective_counts: Counter[str] = Counter()
    for row in all_tags:
        tagged_episode_sets[row.get("podcast_title") or "(unknown)"].add(row["episode_id"])
    for row in analysis_clips:
        podcast = row.get("podcast_title") or "(unknown)"
        analysis_episode_sets[podcast].add(row["episode_id"])
        flag_counts[podcast] += int(row["potential_misinformation"])
        corrective_counts[podcast] += int(row["corrective_context"])
    for row in routine_promotions:
        promo_counts[row.get("podcast_title") or "(unknown)"] += 1
    podcast_rows = []
    for podcast, corpus_episodes in corpus_by_podcast.items():
        total = len(corpus_episodes)
        analysis_episode_count = len(analysis_episode_sets[podcast])
        podcast_rows.append(
            {
                "podcast_title": podcast,
                "corpus_episode_count": total,
                "corpus_duration_hours": round(
                    sum(float(row.get("duration_seconds") or 0) for row in corpus_episodes) / 3600, 1
                ),
                "candidate_episode_count": len(tagged_episode_sets[podcast]),
                "analysis_episode_count": analysis_episode_count,
                "analysis_episode_share": round(analysis_episode_count / total, 4) if total else 0,
                "analysis_clip_count": sum(
                    1 for row in analysis_clips if (row.get("podcast_title") or "(unknown)") == podcast
                ),
                "routine_promotional_clip_count": promo_counts[podcast],
                "potential_misinformation_flag_count": flag_counts[podcast],
                "corrective_context_clip_count": corrective_counts[podcast],
            }
        )
    podcast_rows.sort(key=lambda row: (-row["analysis_clip_count"], row["podcast_title"]))
    with (args.output_dir / "podcast_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(podcast_rows[0]))
        writer.writeheader()
        writer.writerows(podcast_rows)

    content_types = Counter(row["content_type"] for row in analysis_clips)
    stances = Counter(row["stance"] for row in analysis_clips)
    topics = Counter(topic for row in analysis_clips for topic in row["topics"])
    flagged = [row for row in analysis_clips if row["potential_misinformation"]]
    corrective = [row for row in analysis_clips if row["corrective_context"]]
    notable = select_diverse_clips(analysis_clips, args.top_n)
    concentrated = sorted(
        episodes,
        key=lambda row: (-row["relevant_clip_count"], -row["max_notable_score"], row["episode_id"]),
    )[:15]
    podcast_clip_counts = Counter(row.get("podcast_title") or "(unknown)" for row in analysis_clips)
    podcast_episode_sets: dict[str, set[int]] = defaultdict(set)
    for row in analysis_clips:
        podcast_episode_sets[row.get("podcast_title") or "(unknown)"].add(row["episode_id"])

    lines = [
        "# Preliminary vaccination-content scan",
        "",
        "> Exploratory model-assisted triage of noisy ASR—not prevalence measurement, fact-checking, or a validated content analysis.",
        "",
        "## Snapshot",
        "",
        f"- Candidate clips screened: **{len(all_tags):,}**",
        f"- Clips retained as relevant: **{len(relevant):,}** ({len(relevant) / max(1, len(all_tags)):.1%} of candidates)",
        f"- Routine promotional clips set aside: **{len(routine_promotions):,}**",
        f"- Analysis-oriented clips after that exclusion: **{len(analysis_clips):,}** in **{len(episodes):,} episodes**",
        f"- Potential-misinformation triage flags: **{len(flagged):,} clips**",
        f"- Corrective-context tags: **{len(corrective):,} clips**",
        "",
        "Counts below describe retrieved and model-filtered clips, not the full population rate.",
        "",
        "## Clip tags",
        "",
        "- Content type: " + ", ".join(f"{key}={value}" for key, value in content_types.most_common()),
        "- Apparent stance: " + ", ".join(f"{key}={value}" for key, value in stances.most_common()),
        "- Topics: " + ", ".join(f"{key}={value}" for key, value in topics.most_common()),
        "",
        "## Concentrated episodes",
        "",
        "| Clips | Podcast | Episode | Review flags |",
        "|---:|---|---|---|",
    ]
    for row in concentrated:
        flags = []
        if row["potential_misinformation"]:
            flags.append("potential-misinfo")
        if row["corrective_context"]:
            flags.append("corrective")
        lines.append(
            f"| {row['relevant_clip_count']} | {markdown_cell(row['podcast_title'])} | "
            f"{markdown_cell(row['episode_title'])} | {', '.join(flags)} |"
        )
    lines.extend(
        [
            "",
            "## Podcast titles with the most retrieved analysis clips",
            "",
            "| Clips | Episodes | Podcast |",
            "|---:|---:|---|",
        ]
    )
    for podcast, clip_count in podcast_clip_counts.most_common(12):
        lines.append(f"| {clip_count} | {len(podcast_episode_sets[podcast])} | {markdown_cell(podcast)} |")
    lines.extend(
        [
            "",
        "## High-priority clips for human review",
        "",
        ]
    )
    for index, row in enumerate(notable, 1):
        flags = []
        if row["potential_misinformation"]:
            flags.append("potential-misinfo triage")
        if row["corrective_context"]:
            flags.append("corrective context")
        if row["politicized"]:
            flags.append("politicized")
        lines.extend(
            [
                f"### {index}. {row.get('podcast_title')} — {row.get('episode_title')}",
                "",
                f"- Episode {row['episode_id']}; estimated {format_time(row.get('clip_start_seconds_estimated'))}; "
                f"score {row['notable_score']}/5; confidence {row['confidence']:.2f}",
                f"- Tags: {row['stance']}; {', '.join(row['topics']) or 'no topic'}"
                + (f"; {', '.join(flags)}" if flags else ""),
                f"- Model summary: {row.get('claim_summary') or row['rationale']}",
                f"- ASR excerpt near retrieval term: “{matched_excerpt(row)}”",
                f"- Candidate ID: `{row['candidate_id']}`; source segment "
                f"{format_time(row.get('segment_start_seconds'))}–{format_time(row.get('segment_end_seconds'))}",
                "",
            ]
        )

    lines.extend(
        [
            "## Caveats and next checks",
            "",
            "- Retrieval uses vaccine-focused lexical patterns; euphemistic discussion without those terms may be missed.",
            "- Clip timestamps are estimated within 10-minute ASR chunks. Always inspect the source segment/audio before quoting.",
            "- ASR can garble names, negation, speaker changes, and advertisements; the transcripts have no diarization.",
            "- Stance and potential-misinformation tags are model judgments requiring human validation. The latter is a review queue, not a factual verdict.",
            "- Repeated ads, previews, or syndicated excerpts can make clips non-independent.",
            "- The brief sets aside low-notability, unflagged vaccine ads/PSAs; they remain tagged in `clip_tags.jsonl`.",
            "- Ten-minute windows may contain an ad plus later discussion; treat the model's content-type label as provisional.",
            "- Spot checks found inconsistent stance polarity (for example, `supportive` sometimes meant support for a speaker's skeptical argument rather than support for vaccination); do not interpret stance as pro/anti without recoding.",
            "",
        ]
    )
    (args.output_dir / "preliminary_findings.md").write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "candidate_clips_tagged": len(all_tags),
        "relevant_clips": len(relevant),
        "routine_promotional_clips_set_aside": len(routine_promotions),
        "analysis_oriented_clips": len(analysis_clips),
        "episodes_with_analysis_oriented_clips": len(episodes),
        "potential_misinformation_flags": len(flagged),
        "corrective_context_clips": len(corrective),
        "content_types": dict(content_types),
        "stances": dict(stances),
        "topics": dict(topics),
    }
    (args.output_dir / "findings_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


def main() -> None:
    args = parse_args()
    if args.command == "scan":
        scan_candidates(args)
    elif args.command == "tag":
        tag_candidates(args)
    elif args.command == "report":
        make_report(args)


if __name__ == "__main__":
    main()
