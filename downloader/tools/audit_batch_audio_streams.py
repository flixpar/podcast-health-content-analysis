#!/usr/bin/env python3
"""Inventory container streams and correlate them with transcript audit rows."""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import json
import statistics
import subprocess
from pathlib import Path, PurePosixPath


def probe(item: tuple[int, Path]) -> tuple[int, list[dict]]:
    episode_id, path = item
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=index,codec_type,codec_name,duration", "-of", "json", str(path),
        ],
        capture_output=True,
        check=True,
        text=True,
        timeout=120,
    )
    return episode_id, json.loads(result.stdout)["streams"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("--audio-batch", type=Path)
    parser.add_argument("--quality-details", type=Path)
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()
    audio_batch = args.audio_batch or args.batch

    records = [json.loads(line) for line in args.batch.joinpath("manifest.jsonl").read_text().splitlines()]
    episodes = {int(record["episode_id"]): record for record in records[1:]}
    items = [
        (
            episode_id,
            audio_batch.joinpath(*PurePosixPath(record["archive_path"]).parts),
        )
        for episode_id, record in episodes.items()
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        stream_rows = dict(executor.map(probe, items))

    quality = {}
    if args.quality_details:
        quality = {
            int(row["episode_id"]): row
            for line in args.quality_details.read_text().splitlines()
            if (row := json.loads(line))
        }
    failures_path = args.batch / "transcription_failures.jsonl"
    failed_ids = set()
    if failures_path.exists():
        failed_ids = {
            int(json.loads(line)["episode_id"])
            for line in failures_path.read_text().splitlines() if line.strip()
        }

    codec_layouts = collections.Counter()
    video_ids = set()
    video_codecs = collections.Counter()
    for episode_id, streams in stream_rows.items():
        layout = tuple((stream["codec_type"], stream["codec_name"]) for stream in streams)
        codec_layouts[layout] += 1
        videos = [stream for stream in streams if stream["codec_type"] == "video"]
        if videos:
            video_ids.add(episode_id)
            video_codecs.update(stream["codec_name"] for stream in videos)

    def group(ids: set[int]) -> dict:
        rows = [quality[episode_id] for episode_id in ids if episode_id in quality]
        comparable = [row for row in rows if row.get("word_count_ratio") is not None]
        long_rows = [row for row in rows if row["duration"] > 600]
        def distribution(field: str, selected: list[dict] = rows) -> dict:
            values = sorted(row[field] for row in selected if row.get(field) is not None)
            return {
                "count": len(values),
                "min": values[0] if values else None,
                "p05": values[round((len(values) - 1) * 0.05)] if values else None,
                "median": statistics.median(values) if values else None,
                "p95": values[round((len(values) - 1) * 0.95)] if values else None,
                "max": values[-1] if values else None,
            }
        return {
            "manifest_episodes": len(ids),
            "successful_transcripts": len(rows),
            "failed_transcripts": len(ids & failed_ids),
            "over_600_seconds": len(long_rows),
            "audio_hours": sum(row["duration"] for row in rows) / 3600,
            "audio_beyond_first_600_hours": sum(max(0, row["duration"] - 600) for row in rows) / 3600,
            "fallback_episodes": sum(bool(row["fallback_retries"]) for row in rows),
            "fallback_retries": sum(row["fallback_retries"] for row in rows),
            "omission_episodes": sum(bool(row["omitted_audio_seconds"]) for row in rows),
            "omitted_audio_seconds": sum(row["omitted_audio_seconds"] for row in rows),
            "duplicate_segment_episodes": sum(bool(row["adjacent_duplicate_segments"]) for row in rows),
            "adjacent_duplicate_segments": sum(row["adjacent_duplicate_segments"] for row in rows),
            "episodes_with_missing_segments": sum(row["chunks_without_retained_segment"] > 0 for row in rows),
            "missing_segments": sum(max(0, row["chunks_without_retained_segment"]) for row in rows),
            "duplicate_5gram_fraction": distribution("duplicate_5gram_fraction"),
            "reference_comparisons": len(comparable),
            "reference_ratio_below_0_67": sum(row["word_count_ratio"] < 0.67 for row in comparable),
            "reference_ratio_above_1_5": sum(row["word_count_ratio"] > 1.5 for row in comparable),
            "reference_word_count_ratio": distribution("word_count_ratio", comparable),
            "reference_trigram_jaccard": distribution("reference_trigram_jaccard", comparable),
            "reference_trigram_jaccard_below_0_10": sum(
                row["reference_trigram_jaccard"] < 0.10 for row in comparable
            ),
        }

    audio_only_ids = set(episodes) - video_ids
    by_podcast = collections.defaultdict(lambda: {"episodes": 0, "video": 0, "video_long": 0})
    for episode_id, episode in episodes.items():
        bucket = by_podcast[episode["podcast_title"]]
        bucket["episodes"] += 1
        bucket["video"] += episode_id in video_ids
        bucket["video_long"] += episode_id in video_ids and quality.get(episode_id, {}).get("duration", 0) > 600

    output = {
        "codec_layouts": [
            {"streams": layout, "episodes": count}
            for layout, count in codec_layouts.most_common()
        ],
        "video_codecs": video_codecs,
        "video_episode_ids": sorted(video_ids),
        "with_video": group(video_ids),
        "audio_only": group(audio_only_ids),
        "all_failures_with_video": failed_ids <= video_ids,
        "failed_without_video": sorted(failed_ids - video_ids),
        "podcasts_by_video_count": [
            {"podcast_title": title, **counts}
            for title, counts in sorted(by_podcast.items(), key=lambda item: item[1]["video"], reverse=True)
            if counts["video"]
        ],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
