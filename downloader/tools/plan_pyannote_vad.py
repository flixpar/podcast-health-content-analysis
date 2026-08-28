#!/usr/bin/env python3
"""Plan speech spans with pyannote in an isolated GPU environment.

This tool intentionally has no imports from ``podcast_pipeline``. It is meant
to run in a pyannote-specific environment whose PyTorch pins may conflict with
the production ASR environment. The resulting JSONL is validated again by the
production batch transcriber before any ASR request is sent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import os
import subprocess
import tempfile
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = 1
SAMPLE_RATE = 16_000
MODEL = "pyannote/segmentation-3.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a checksum-bound pyannote VAD plan for an audio batch."
    )
    parser.add_argument("batch_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--gpu-ids", default="0", help="comma-separated physical GPU ids")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--min-duration-on", type=float, default=0.25)
    parser.add_argument("--min-duration-off", type=float, default=10.0)
    parser.add_argument("--episode-id", type=int, action="append", default=[])
    parser.add_argument(
        "--episode-ids-file", type=Path,
        help="JSON list, object with selected_ids, or newline-delimited episode ids",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be positive")
    if args.min_duration_on < 0 or args.min_duration_off < 0:
        raise ValueError("minimum durations cannot be negative")
    gpu_ids = [int(value) for value in args.gpu_ids.split(",") if value.strip()]
    if not gpu_ids or any(gpu_id < 0 for gpu_id in gpu_ids):
        raise ValueError("--gpu-ids must contain non-negative integers")

    batch_dir = args.batch_dir.expanduser().resolve()
    manifest_path = batch_dir / "manifest.jsonl"
    manifest_payload = manifest_path.read_bytes()
    header, episodes = _load_manifest(manifest_payload, batch_dir)
    selected_ids = set(args.episode_id)
    if args.episode_ids_file is not None:
        selected_ids.update(_load_episode_ids(args.episode_ids_file))
    if selected_ids:
        missing = selected_ids - episodes.keys()
        if missing:
            raise ValueError(f"Selected episode ids are not in the batch: {sorted(missing)[:10]}")
        episodes = {episode_id: episodes[episode_id] for episode_id in selected_ids}
    if not episodes:
        raise ValueError("No episodes selected")

    output = args.output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to replace existing plan without --overwrite: {output}")

    worker_count = min(args.workers, len(episodes))
    shards = _balanced_shards(list(episodes.values()), worker_count)
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    processes = [
        context.Process(
            target=_worker,
            args=(
                index,
                gpu_ids[index % len(gpu_ids)],
                shard,
                batch_dir,
                args.batch_size,
                args.min_duration_on,
                args.min_duration_off,
                results,
            ),
            name=f"pyannote-vad-{index}-gpu-{gpu_ids[index % len(gpu_ids)]}",
        )
        for index, shard in enumerate(shards)
    ]
    started = time.monotonic()
    for process in processes:
        process.start()

    planned: dict[int, dict] = {}
    finished = 0
    try:
        while finished < len(processes):
            kind, payload = results.get()
            if kind == "episode":
                planned[payload["episode_id"]] = payload
                count = len(planned)
                if count == 1 or count == len(episodes) or count % 10 == 0:
                    elapsed = time.monotonic() - started
                    audio_seconds = sum(item["duration_seconds"] for item in planned.values())
                    rate = audio_seconds / elapsed if elapsed else 0.0
                    print(
                        f"Planned {count}/{len(episodes)} episodes "
                        f"({audio_seconds / 3600:.2f}h, {rate:.1f}x)",
                        flush=True,
                    )
            elif kind == "done":
                finished += 1
            elif kind == "error":
                raise RuntimeError(payload)
            else:
                raise RuntimeError(f"Unknown worker message: {kind!r}")
    except BaseException:
        for process in processes:
            if process.is_alive():
                process.terminate()
        raise
    finally:
        for process in processes:
            process.join()

    crashes = [
        f"{process.name} exited with status {process.exitcode}"
        for process in processes if process.exitcode
    ]
    if crashes:
        raise RuntimeError("; ".join(crashes))
    if planned.keys() != episodes.keys():
        missing = episodes.keys() - planned.keys()
        raise RuntimeError(f"Workers returned an incomplete plan: {sorted(missing)[:10]}")

    wall_seconds = time.monotonic() - started
    plan_header = {
        "record_type": "vad_plan",
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "batch_id": header["batch_id"],
        "source_audio_manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "model": MODEL,
        "sample_rate": SAMPLE_RATE,
        "batch_size": args.batch_size,
        "min_duration_on": args.min_duration_on,
        "min_duration_off": args.min_duration_off,
        "worker_count": worker_count,
        "gpu_ids": gpu_ids,
        "episode_count": len(planned),
        "audio_seconds": round(sum(item["duration_seconds"] for item in planned.values()), 6),
        "detected_speech_seconds": round(
            sum(item["speech_seconds"] for item in planned.values()), 6
        ),
        "decode_process_seconds": round(
            sum(item["decode_seconds"] for item in planned.values()), 6
        ),
        "detector_process_seconds": round(
            sum(item["detector_seconds"] for item in planned.values()), 6
        ),
        "wall_seconds": round(wall_seconds, 6),
    }
    _write_atomic(output, plan_header, planned.values())
    print(json.dumps({
        "plan": str(output),
        "episodes": len(planned),
        "audio_hours": round(plan_header["audio_seconds"] / 3600, 3),
        "wall_seconds": plan_header["wall_seconds"],
        "rtfx": round(plan_header["audio_seconds"] / wall_seconds, 2),
        "speech_fraction": round(
            plan_header["detected_speech_seconds"] / plan_header["audio_seconds"], 6
        ),
    }, indent=2))


def _worker(
    worker_index: int,
    gpu_id: int,
    jobs: list[dict],
    batch_dir: Path,
    batch_size: int,
    min_duration_on: float,
    min_duration_off: float,
    results,
) -> None:
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        import numpy as np
        import torch
        from pyannote.audio import Model
        from pyannote.audio.pipelines import VoiceActivityDetection

        device = torch.device("cuda:0")
        model = Model.from_pretrained(MODEL, use_auth_token=True).to(device)
        pipeline = VoiceActivityDetection(segmentation=model, batch_size=batch_size)
        pipeline.instantiate({
            "min_duration_on": min_duration_on,
            "min_duration_off": min_duration_off,
        })
        for job in jobs:
            audio_path = batch_dir.joinpath(*PurePosixPath(job["archive_path"]).parts)
            decode_started = time.monotonic()
            audio = _decode(audio_path, float(job.get("duration_seconds") or 0), np)
            decode_seconds = time.monotonic() - decode_started
            duration_seconds = len(audio) / SAMPLE_RATE
            file = {
                "waveform": torch.from_numpy(audio.copy()).unsqueeze(0),
                "sample_rate": SAMPLE_RATE,
                "uri": str(job["episode_id"]),
            }
            torch.cuda.synchronize()
            detector_started = time.monotonic()
            annotation = pipeline(file)
            torch.cuda.synchronize()
            detector_seconds = time.monotonic() - detector_started
            spans = list(annotation.get_timeline().support())
            speech_spans = [[span.start, min(span.end, duration_seconds)] for span in spans]
            speech_seconds = sum(end - start for start, end in speech_spans)
            results.put(("episode", {
                "record_type": "episode",
                "episode_id": job["episode_id"],
                "archive_path": job["archive_path"],
                "source_audio_sha256": job["sha256"],
                "duration_seconds": duration_seconds,
                "speech_seconds": speech_seconds,
                "speech_spans": speech_spans,
                "decode_seconds": decode_seconds,
                "detector_seconds": detector_seconds,
                "worker_index": worker_index,
                "gpu_id": gpu_id,
            }))
        results.put(("done", worker_index))
    except BaseException:
        results.put(("error", f"Worker {worker_index} on GPU {gpu_id} failed:\n{traceback.format_exc()}"))


def _decode(path: Path, duration_seconds: float, np):
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
        "-map", "0:a:0", "-vn", "-sn", "-dn", "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "f32le", "pipe:1",
    ]
    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(120, math.ceil(duration_seconds)),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffmpeg timed out decoding {path}") from exc
    if process.returncode:
        detail = process.stderr.decode(errors="replace")[-1000:]
        raise RuntimeError(f"ffmpeg failed decoding {path}: {detail}")
    if not process.stdout or len(process.stdout) % 4:
        raise RuntimeError(f"ffmpeg returned invalid float32 audio for {path}")
    return np.frombuffer(process.stdout, dtype=np.float32)


def _load_manifest(payload: bytes, batch_dir: Path) -> tuple[dict, dict[int, dict]]:
    records = [json.loads(line) for line in payload.splitlines() if line.strip()]
    if not records or records[0].get("record_type") != "batch":
        raise ValueError("Audio manifest must start with a batch record")
    header = records[0]
    if batch_dir.name != header.get("batch_id"):
        raise ValueError("Batch directory name does not match manifest batch_id")
    episodes = {}
    for record in records[1:]:
        if record.get("record_type") != "episode":
            raise ValueError("Audio manifest contains a non-episode detail record")
        episode_id = record.get("episode_id")
        if isinstance(episode_id, bool) or not isinstance(episode_id, int) or episode_id <= 0:
            raise ValueError("Audio manifest contains an invalid episode_id")
        if episode_id in episodes:
            raise ValueError(f"Duplicate episode id: {episode_id}")
        archive_path = record.get("archive_path")
        relative = PurePosixPath(archive_path) if isinstance(archive_path, str) else None
        if (
            relative is None
            or relative.is_absolute()
            or len(relative.parts) != 2
            or relative.parts[0] != "audio"
            or ".." in relative.parts
        ):
            raise ValueError(f"Unsafe archive path for episode {episode_id}")
        audio_path = batch_dir.joinpath(*relative.parts)
        if not audio_path.is_file() or audio_path.stat().st_size != record.get("size_bytes"):
            raise ValueError(f"Audio size/type mismatch for episode {episode_id}")
        digest = record.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"Invalid audio SHA-256 for episode {episode_id}")
        episodes[episode_id] = record
    if header.get("episode_count") != len(episodes):
        raise ValueError("Audio manifest episode_count does not match its records")
    return header, episodes


def _load_episode_ids(path: Path) -> set[int]:
    text = path.read_text()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {int(line) for line in text.splitlines() if line.strip()}
    if isinstance(payload, dict):
        payload = payload.get("selected_ids")
    if not isinstance(payload, list):
        raise ValueError("Episode id file must contain a list or selected_ids object")
    return {int(value) for value in payload}


def _balanced_shards(episodes: list[dict], count: int) -> list[list[dict]]:
    shards = [[] for _ in range(count)]
    durations = [0.0] * count
    for episode in sorted(
        episodes, key=lambda item: float(item.get("duration_seconds") or 0), reverse=True
    ):
        index = min(range(count), key=durations.__getitem__)
        shards[index].append(episode)
        durations[index] += float(episode.get("duration_seconds") or 0)
    return shards


def _write_atomic(output: Path, header: dict, episodes) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(header, separators=(",", ":")) + "\n")
            for episode in sorted(episodes, key=lambda item: item["episode_id"]):
                stream.write(json.dumps(episode, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    main()
