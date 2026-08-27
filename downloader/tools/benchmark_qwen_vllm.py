#!/usr/bin/env python3
"""Prepare and run reproducible Qwen3-ASR vLLM throughput benchmarks.

The preparation step selects deterministic, podcast-diverse windows from an
audio batch.  The run step preloads those clips before starting its monotonic
timer and sends every clip exactly once, so disk reads and duplicate-media
caches do not distort model-serving throughput.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import random
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

import requests

# Make the script runnable directly from any working directory without an
# editable install of the downloader package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from podcast_pipeline.batches import load_audio_manifest
from podcast_pipeline.asr.chunking import chunk_spans


@dataclass(frozen=True)
class Clip:
    clip_id: str
    episode_id: int
    podcast_id: int
    source_path: str
    path: str
    offset_seconds: float
    duration_seconds: float


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _probe_duration(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(proc.stdout.strip())


def _clip_offset(episode_id: int, available: float) -> float:
    if available <= 0:
        return 0.0
    digest = hashlib.sha256(f"qwen-benchmark:{episode_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / (2**64 - 1) * available


def _select_episodes(manifest, batch_dir: Path, count: int, duration: float):
    eligible = [
        episode for episode in manifest.episodes.values()
        if episode.duration_seconds is not None
        and episode.duration_seconds >= duration + 30
    ]
    eligible.sort(key=lambda item: hashlib.sha256(
        f"qwen-benchmark-order:{item.episode_id}".encode()
    ).digest())

    # Prefer one episode per podcast before admitting a second. This prevents
    # one prolific feed from defining the benchmark's acoustic/content mix.
    selected = []
    selected_ids = set()
    seen_podcasts = set()
    for require_new_podcast in (True, False):
        for episode in eligible:
            if episode.episode_id in selected_ids:
                continue
            if require_new_podcast and episode.podcast_id in seen_podcasts:
                continue
            source = batch_dir.joinpath(*PurePosixPath(episode.archive_path).parts)
            actual_duration = _probe_duration(source)
            if actual_duration < duration + 2:
                continue
            selected.append((episode, actual_duration))
            selected_ids.add(episode.episode_id)
            seen_podcasts.add(episode.podcast_id)
            if len(selected) == count:
                return selected
    raise RuntimeError(f"Only {len(selected)} episodes can supply {duration:g}s clips; need {count}")


def prepare(args: argparse.Namespace) -> dict:
    batch_dir = args.batch_dir.resolve()
    manifest = load_audio_manifest(batch_dir / "manifest.jsonl")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = _select_episodes(manifest, batch_dir, args.count, args.duration)

    def encode(index_episode) -> Clip:
        index, (episode, source_duration) = index_episode
        source = batch_dir.joinpath(*PurePosixPath(episode.archive_path).parts)
        available = source_duration - args.duration - 1
        offset = _clip_offset(episode.episode_id, available)
        clip_id = f"clip_{index:04d}_episode_{episode.episode_id}"
        target = output_dir / f"{clip_id}.ogg"
        subprocess.run(
            [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{offset:.6f}", "-i", str(source), "-t", str(args.duration),
                "-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "-1",
                "-ac", "1", "-ar", "16000",
                "-c:a", "libopus", "-b:a", args.bitrate, str(target),
            ],
            check=True,
        )
        actual_duration = _probe_duration(target)
        if actual_duration < args.duration - 0.1:
            raise RuntimeError(
                f"{target} is short: {actual_duration:.3f}s, expected {args.duration:.3f}s"
            )
        return Clip(
            clip_id=clip_id,
            episode_id=episode.episode_id,
            podcast_id=episode.podcast_id,
            source_path=episode.archive_path,
            path=target.name,
            offset_seconds=round(offset, 6),
            duration_seconds=actual_duration,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        clips = list(executor.map(encode, enumerate(selected)))
    clips.sort(key=lambda item: item.clip_id)
    benchmark_manifest = output_dir / "manifest.jsonl"
    records = [{
        "record_type": "benchmark",
        "source_audio_batch_id": manifest.batch_id,
        "source_audio_manifest_sha256": manifest.sha256,
        "count": len(clips),
        "duration_seconds": args.duration,
        "bitrate": args.bitrate,
    }, *(dict(record_type="clip", **asdict(clip)) for clip in clips)]
    benchmark_manifest.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    return {
        "manifest": str(benchmark_manifest),
        "clips": len(clips),
        "audio_hours": sum(item.duration_seconds for item in clips) / 3600,
        "bytes": sum((output_dir / item.path).stat().st_size for item in clips),
    }


def prepare_batch_chunks(args: argparse.Namespace) -> dict:
    """Materialize the exact leading production episodes as lossless chunks."""
    started = time.monotonic()
    batch_dir = args.batch_dir.resolve()
    manifest = load_audio_manifest(batch_dir / "manifest.jsonl")
    episodes = list(manifest.episodes.values())[:args.episodes]
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    plans = []
    for episode in episodes:
        source = batch_dir.joinpath(*PurePosixPath(episode.archive_path).parts)
        duration = _probe_duration(source)
        for index, (start, end) in enumerate(chunk_spans(
            duration, args.chunk_duration, args.overlap,
        )):
            plans.append((episode, source, index, start, end))

    def encode(plan) -> Clip:
        episode, source, index, start, end = plan
        clip_id = f"episode_{episode.episode_id}_chunk_{index:04d}"
        target = output_dir / f"{clip_id}.flac"
        subprocess.run(
            [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{end - start:.6f}",
                "-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "-1",
                "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", "-c:a", "flac",
                str(target),
            ],
            check=True,
        )
        return Clip(
            clip_id=clip_id,
            episode_id=episode.episode_id,
            podcast_id=episode.podcast_id,
            source_path=episode.archive_path,
            path=target.name,
            offset_seconds=start,
            duration_seconds=end - start,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        clips = list(executor.map(encode, plans))
    preparation_wall_seconds = time.monotonic() - started
    benchmark_manifest = output_dir / "manifest.jsonl"
    unique_audio_seconds = sum(_probe_duration(
        batch_dir.joinpath(*PurePosixPath(episode.archive_path).parts)
    ) for episode in episodes)
    records = [{
        "record_type": "benchmark",
        "source_audio_batch_id": manifest.batch_id,
        "source_audio_manifest_sha256": manifest.sha256,
        "episode_count": len(episodes),
        "count": len(clips),
        "chunk_duration_seconds": args.chunk_duration,
        "overlap_seconds": args.overlap,
        "unique_audio_seconds": unique_audio_seconds,
        "preparation_wall_seconds": preparation_wall_seconds,
    }, *(dict(record_type="clip", **asdict(clip)) for clip in clips)]
    benchmark_manifest.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    return {
        "manifest": str(benchmark_manifest),
        "episodes": len(episodes),
        "clips": len(clips),
        "unique_audio_seconds": unique_audio_seconds,
        "chunk_audio_seconds": sum(clip.duration_seconds for clip in clips),
        "preparation_wall_seconds": preparation_wall_seconds,
        "preparation_rtfx": unique_audio_seconds / preparation_wall_seconds,
        "bytes": sum((output_dir / clip.path).stat().st_size for clip in clips),
    }


def _load_clips(path: Path) -> tuple[dict, list[Clip]]:
    records = [json.loads(line) for line in path.read_text().splitlines() if line]
    if not records or records[0].get("record_type") != "benchmark":
        raise RuntimeError(f"Invalid benchmark manifest: {path}")
    return records[0], [
        Clip(**{key: value for key, value in record.items() if key != "record_type"})
        for record in records[1:]
    ]


def run_benchmark(args: argparse.Namespace) -> dict:
    manifest_path = args.manifest.resolve()
    header, clips = _load_clips(manifest_path)
    if args.limit is not None:
        clips = clips[:args.limit]
    random.Random(args.seed).shuffle(clips)
    endpoints = [url.rstrip("/") for url in args.url]
    if not endpoints:
        raise RuntimeError("At least one --url is required")

    # Reading before the timer isolates serving throughput from a cold local
    # filesystem. Production benchmarks can opt into end-to-end I/O separately.
    payloads = {
        clip.clip_id: (manifest_path.parent / clip.path).read_bytes()
        for clip in clips
    }
    local = threading.local()

    def transcribe(assignment):
        index, clip = assignment
        if not hasattr(local, "sessions"):
            local.sessions = {}
        endpoint = endpoints[index % len(endpoints)]
        session = local.sessions.get(endpoint)
        if session is None:
            session = requests.Session()
            session.trust_env = False
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=args.concurrency,
                pool_maxsize=args.concurrency,
            )
            session.mount("http://", adapter)
            local.sessions[endpoint] = session
        started = time.monotonic()
        suffix = Path(clip.path).suffix.lower()
        mime_type = "audio/flac" if suffix == ".flac" else "audio/ogg"
        fields = {"model": args.model, "language": args.language}
        if args.max_completion_tokens is not None:
            fields["max_completion_tokens"] = str(args.max_completion_tokens)
        response = session.post(
            f"{endpoint}/v1/audio/transcriptions",
            data=fields,
            files={"file": (Path(clip.path).name, payloads[clip.clip_id], mime_type)},
            timeout=args.timeout,
        )
        latency = time.monotonic() - started
        response.raise_for_status()
        body = response.json()
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError(f"Empty/invalid response for {clip.clip_id}: {body!r}")
        return clip, latency, text

    # The service is already model-warm, but a few requests compile/profile
    # input-dependent paths. Use clips outside the measured prefix where possible.
    warmup = min(args.warmup, len(clips))
    for index in range(warmup):
        transcribe((index, clips[-1 - index]))

    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(transcribe, enumerate(clips)))
    wall_seconds = time.monotonic() - started
    total_audio_seconds = sum(item.duration_seconds for item in clips)
    latencies = [latency for _, latency, _ in results]
    output = {
        "model": args.model,
        "urls": endpoints,
        "concurrency": args.concurrency,
        "max_completion_tokens": args.max_completion_tokens,
        "requests": len(results),
        "source_audio_batch_id": header.get("source_audio_batch_id"),
        "benchmark_manifest": str(manifest_path),
        "total_audio_seconds": total_audio_seconds,
        "wall_seconds": wall_seconds,
        "rtfx": total_audio_seconds / wall_seconds,
        "requests_per_second": len(results) / wall_seconds,
        "latency_seconds": {
            "mean": sum(latencies) / len(latencies),
            "p50": _percentile(latencies, 0.50),
            "p90": _percentile(latencies, 0.90),
            "p99": _percentile(latencies, 0.99),
            "max": max(latencies),
        },
        "words": sum(len(text.split()) for _, _, text in results),
        "characters": sum(len(text) for _, _, text in results),
    }
    if args.transcripts:
        transcript_path = args.transcripts.resolve()
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text("".join(
            json.dumps({
                "clip_id": clip.clip_id,
                "episode_id": clip.episode_id,
                "latency_seconds": latency,
                "text": text,
            }, ensure_ascii=False, separators=(",", ":")) + "\n"
            for clip, latency, text in results
        ), encoding="utf-8")
        output["transcripts"] = str(transcript_path)
    if args.output:
        args.output.resolve().write_text(json.dumps(output, indent=2) + "\n")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("batch_dir", type=Path)
    prepare_parser.add_argument("output_dir", type=Path)
    prepare_parser.add_argument("--count", type=int, default=128)
    prepare_parser.add_argument("--duration", type=float, default=600)
    prepare_parser.add_argument("--bitrate", default="32k")
    prepare_parser.add_argument("--workers", type=int, default=16)

    batch_parser = subparsers.add_parser("prepare-batch")
    batch_parser.add_argument("batch_dir", type=Path)
    batch_parser.add_argument("output_dir", type=Path)
    batch_parser.add_argument("--episodes", type=int, default=100)
    batch_parser.add_argument("--chunk-duration", type=float, default=600)
    batch_parser.add_argument("--overlap", type=float, default=5)
    batch_parser.add_argument("--workers", type=int, default=32)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("manifest", type=Path)
    run_parser.add_argument("--url", action="append", required=True)
    run_parser.add_argument("--model", default="Qwen/Qwen3-ASR-1.7B")
    run_parser.add_argument("--language", default="en")
    run_parser.add_argument("--concurrency", type=int, required=True)
    run_parser.add_argument("--limit", type=int)
    run_parser.add_argument("--warmup", type=int, default=4)
    run_parser.add_argument("--timeout", type=float, default=1800)
    run_parser.add_argument("--max-completion-tokens", type=int)
    run_parser.add_argument("--seed", type=int, default=20260826)
    run_parser.add_argument("--output", type=Path)
    run_parser.add_argument("--transcripts", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        result = prepare(args)
    elif args.command == "prepare-batch":
        result = prepare_batch_chunks(args)
    else:
        result = run_benchmark(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
