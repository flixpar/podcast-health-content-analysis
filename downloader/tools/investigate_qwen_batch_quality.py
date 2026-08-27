#!/usr/bin/env python3
"""Audit a Qwen transcript batch and compare it with reference transcripts."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import re
import statistics
from pathlib import Path

import zstandard


MARKER = re.compile(
    r"\[UNTRANSCRIBED_AUDIO_([0-9.]+)-([0-9.]+)s_(?:ASR_FAILURE|LOW_SIGNAL)\]"
)
WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)


def read_transcript(path: Path) -> tuple[dict, list[dict], str]:
    with path.open("rb") as raw:
        with zstandard.ZstdDecompressor().stream_reader(raw) as decoded:
            lines = decoded.read().decode("utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    metadata = records[0]
    segments = [record for record in records[1:] if record.get("type") == "segment"]
    return metadata, segments, " ".join(segment["text"] for segment in segments)


def words(text: str) -> list[str]:
    return [match.group(0).casefold().replace("’", "'") for match in WORD.finditer(text)]


def ngram_set(tokens: list[str], width: int) -> set[tuple[str, ...]]:
    return set(zip(*(tokens[offset:] for offset in range(width))))


def quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(values: list[float]) -> dict:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "p05": quantile(values, 0.05),
        "median": statistics.median(values) if values else None,
        "p95": quantile(values, 0.95),
        "max": max(values) if values else None,
        "mean": statistics.fmean(values) if values else None,
    }


def span_union_seconds(spans: list[tuple[float, float]]) -> float:
    if not spans:
        return 0.0
    total = 0.0
    merged_start, merged_end = sorted(spans)[0]
    for start, end in sorted(spans)[1:]:
        if start <= merged_end:
            merged_end = max(merged_end, end)
        else:
            total += merged_end - merged_start
            merged_start, merged_end = start, end
    return total + merged_end - merged_start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--details", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    manifest_records = [json.loads(line) for line in args.batch.joinpath("manifest.jsonl").read_text().splitlines()]
    batch_record = manifest_records[0]
    episodes = {int(row["episode_id"]): row for row in manifest_records[1:]}
    transcript_paths = sorted(args.batch.joinpath("transcripts").glob("episode_*.jsonl.zst"))
    failures_path = args.batch / "transcription_failures.jsonl"
    failures = []
    if failures_path.exists():
        failures = [json.loads(line) for line in failures_path.read_text().splitlines() if line.strip()]

    reference_paths: dict[int, Path] = {}
    if args.reference:
        reference_paths = {
            int(path.name.removeprefix("episode_").removesuffix(".jsonl.zst")): path
            for path in args.reference.joinpath("transcripts").glob("episode_*.jsonl.zst")
        }

    rows = []
    all_markers = []
    created = []
    for index, path in enumerate(transcript_paths, 1):
        episode_id = int(path.name.removeprefix("episode_").removesuffix(".jsonl.zst"))
        metadata, segments, text = read_transcript(path)
        tokenized = words(text)
        duration = float(metadata["duration"])
        marker_spans = [(float(a), float(b)) for a, b in MARKER.findall(text)]
        marker_seconds_raw = sum(b - a for a, b in marker_spans)
        marker_seconds_union = span_union_seconds(marker_spans)
        metadata_spans = metadata.get("omitted_audio_spans")
        all_markers.extend((episode_id, a, b) for a, b in marker_spans)
        created_at = dt.datetime.fromisoformat(metadata["created_at"])
        created.append(created_at)

        tail = tokenized[-200:]
        tail_dominance = 0.0
        if tail:
            tail_dominance = max(collections.Counter(tail).values()) / len(tail)
        adjacent_duplicate_segments = sum(
            a["text"].strip() == b["text"].strip()
            for a, b in zip(segments, segments[1:])
        )
        fivegrams = ngram_set(tokenized, 5)
        fivegram_count = max(0, len(tokenized) - 4)
        row = {
            "episode_id": episode_id,
            "podcast_title": episodes.get(episode_id, {}).get("podcast_title"),
            "episode_title": episodes.get(episode_id, {}).get("episode_title"),
            "duration": duration,
            "words": len(tokenized),
            "wpm": len(tokenized) / duration * 60,
            "segments": len(segments),
            "chunks": int(metadata["chunks"]),
            "chunks_without_retained_segment": int(metadata["chunks"]) - len(segments),
            "fallback_retries": int(metadata.get("fallback_retries", 0)),
            "omitted_audio_seconds": float(metadata.get("omitted_audio_seconds", 0)),
            "marker_count": len(marker_spans),
            "marker_seconds": marker_seconds_union,
            "marker_seconds_raw": marker_seconds_raw,
            "omission_accounting": (
                "interval_union" if isinstance(metadata_spans, list) else "legacy_overlap_sum"
            ),
            "input_preprocessing": metadata.get("input_preprocessing"),
            "tail_dominance": tail_dominance,
            "adjacent_duplicate_segments": adjacent_duplicate_segments,
            "duplicate_5gram_fraction": (
                1 - len(fivegrams) / fivegram_count if fivegram_count else 0.0
            ),
            "created_at": metadata["created_at"],
        }
        reference_path = reference_paths.get(episode_id)
        if reference_path:
            ref_metadata, _, ref_text = read_transcript(reference_path)
            ref_words = words(ref_text)
            qwen_trigrams = ngram_set(tokenized, 3)
            reference_trigrams = ngram_set(ref_words, 3)
            trigram_union = qwen_trigrams | reference_trigrams
            row.update({
                "reference_model": ref_metadata.get("model"),
                "reference_words": len(ref_words),
                "word_count_ratio": len(tokenized) / len(ref_words) if ref_words else None,
                "duration_ratio": duration / float(ref_metadata["duration"]),
                "reference_trigram_jaccard": (
                    len(qwen_trigrams & reference_trigrams) / len(trigram_union)
                    if trigram_union else None
                ),
            })
        rows.append(row)

    comparable = [row for row in rows if "reference_words" in row and row["reference_words"]]
    missing = sorted(set(episodes) - {row["episode_id"] for row in rows})
    extra = sorted({row["episode_id"] for row in rows} - set(episodes))
    unresolved_failures = sorted(
        {int(failure["episode_id"]) for failure in failures} & set(missing)
    )
    fallback_rows = [row for row in rows if row["fallback_retries"]]
    omitted_rows = [row for row in rows if row["omitted_audio_seconds"]]
    marker_mismatch = [
        row for row in rows
        if abs(row["omitted_audio_seconds"] - (
            row["marker_seconds"] if row["omission_accounting"] == "interval_union"
            else row["marker_seconds_raw"]
        )) > 0.11
    ]
    high_wpm = [row for row in rows if row["wpm"] > 300]
    repetitive_tail = [row for row in rows if row["tail_dominance"] >= 0.60]
    reference_ratios = [row["word_count_ratio"] for row in comparable]
    outlier_ratio_rows = [
        row for row in comparable
        if row["word_count_ratio"] < 0.67 or row["word_count_ratio"] > 1.5
    ]
    low_agreement_rows = [
        row for row in comparable if row["reference_trigram_jaccard"] < 0.10
    ]

    by_podcast = collections.defaultdict(lambda: {"episodes": 0, "fallback": 0, "omitted": 0.0, "failed": 0})
    for row in rows:
        bucket = by_podcast[row["podcast_title"]]
        bucket["episodes"] += 1
        bucket["fallback"] += bool(row["fallback_retries"])
        bucket["omitted"] += row["omitted_audio_seconds"]
    for episode_id in unresolved_failures:
        title = episodes.get(episode_id, {}).get("podcast_title")
        by_podcast[title]["failed"] += 1

    summary = {
        "batch": batch_record,
        "manifest_episodes": len(episodes),
        "transcript_files": len(rows),
        "failure_records": len(failures),
        "unresolved_failure_ids": unresolved_failures,
        "missing_transcript_ids": missing,
        "extra_transcript_ids": extra,
        "created_at": {"first": min(created).isoformat(), "last": max(created).isoformat()} if created else None,
        "total_audio_seconds": sum(row["duration"] for row in rows),
        "fallback": {
            "episodes": len(fallback_rows),
            "retries": sum(row["fallback_retries"] for row in rows),
            "audio_seconds_in_affected_episodes": sum(row["duration"] for row in fallback_rows),
        },
        "omission": {
            "episodes": len(omitted_rows),
            "markers": len(all_markers),
            "metadata_seconds": sum(row["omitted_audio_seconds"] for row in rows),
            "marker_seconds": sum(row["marker_seconds"] for row in rows),
            "legacy_overlap_overcount_seconds": sum(
                row["marker_seconds_raw"] - row["marker_seconds"]
                for row in rows if row["omission_accounting"] == "legacy_overlap_sum"
            ),
            "metadata_marker_mismatches": len(marker_mismatch),
        },
        "retained_anomaly_checks": {
            "over_300_wpm": len(high_wpm),
            "repetitive_200_word_tail": len(repetitive_tail),
            "adjacent_duplicate_segments": sum(row["adjacent_duplicate_segments"] for row in rows),
            "episodes_with_adjacent_duplicate_segments": sum(bool(row["adjacent_duplicate_segments"]) for row in rows),
            "episodes_with_missing_segments": sum(row["chunks_without_retained_segment"] > 0 for row in rows),
            "missing_segments": sum(max(0, row["chunks_without_retained_segment"]) for row in rows),
            "duplicate_5gram_fraction": summarize([row["duplicate_5gram_fraction"] for row in rows]),
        },
        "wpm": summarize([row["wpm"] for row in rows]),
        "reference": {
            "available_files": len(reference_paths),
            "comparable": len(comparable),
            "word_count_ratio": summarize(reference_ratios),
            "outside_0.67_to_1.5": len(outlier_ratio_rows),
            "duration_ratio": summarize([row["duration_ratio"] for row in comparable]),
            "trigram_jaccard": summarize([row["reference_trigram_jaccard"] for row in comparable]),
            "trigram_jaccard_below_0_10": len(low_agreement_rows),
        },
        "worst_word_count_ratios": sorted(
            comparable, key=lambda row: abs(math.log(row["word_count_ratio"])), reverse=True
        )[:30],
        "lowest_reference_agreement": sorted(
            comparable, key=lambda row: row["reference_trigram_jaccard"]
        )[:30],
        "largest_omissions": sorted(omitted_rows, key=lambda row: row["omitted_audio_seconds"], reverse=True)[:30],
        "highest_fallback_counts": sorted(fallback_rows, key=lambda row: row["fallback_retries"], reverse=True)[:30],
        "podcasts_by_omission": [
            {"podcast_title": title, **bucket}
            for title, bucket in sorted(by_podcast.items(), key=lambda item: item[1]["omitted"], reverse=True)[:30]
        ],
        "podcasts_by_fallback_rate": [
            {"podcast_title": title, **bucket, "fallback_rate": bucket["fallback"] / bucket["episodes"]}
            for title, bucket in sorted(
                by_podcast.items(), key=lambda item: item[1]["fallback"] / item[1]["episodes"], reverse=True
            )[:30]
        ],
    }
    if args.details:
        args.details.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    rendered = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.summary:
        args.summary.write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
