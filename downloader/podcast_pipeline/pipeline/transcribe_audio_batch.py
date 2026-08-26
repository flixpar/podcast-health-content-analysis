"""Resumably transcribe an extracted audio batch without the source database."""

from __future__ import annotations

import fcntl
import json
import logging
import os
import queue
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from tqdm import tqdm

from podcast_pipeline.batches import (AudioEpisode, BatchFormatError,
                                      validate_audio_batch_directory)
from podcast_pipeline.config import Config
from podcast_pipeline.transcripts.store import TranscriptStore

logger = logging.getLogger(__name__)

_DONE = object()


class AudioBatchTranscriptionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Job:
    episode: AudioEpisode
    audio_path: Path


@dataclass
class Outcome:
    job: Job
    result: object = None
    error: Exception | None = None


@dataclass
class WorkerFinished:
    gpu_id: int
    error: Exception | None = None


def _load_failures(path: Path) -> set[int]:
    failed: set[int] = set()
    if not path.exists():
        return failed
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
                failed.add(int(record["episode_id"]))
            except (ValueError, KeyError) as exc:
                raise AudioBatchTranscriptionError(
                    f"Invalid failure log {path} at line {line_number}: {exc}"
                ) from exc
    return failed


def _append_failure(path: Path, job: Job, error: Exception) -> None:
    record = {
        "record_type": "transcription_failure",
        "episode_id": job.episode.episode_id,
        "failed_at": datetime.now(UTC).isoformat(),
        "error_type": type(error).__name__,
        "error": str(error)[:2000],
    }
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_batch_transcript(path: Path, episode: AudioEpisode, batch_id: str,
                              store: TranscriptStore | None = None):
    store = store or TranscriptStore(path.parent)
    try:
        transcript = store.load(path)
    except Exception as exc:
        raise BatchFormatError(f"Cannot read transcript for episode {episode.episode_id}: {path}: {exc}") from exc
    metadata = transcript.metadata
    if transcript.episode_id != episode.episode_id:
        raise BatchFormatError(
            f"Transcript {path} says episode {transcript.episode_id}, expected {episode.episode_id}"
        )
    if metadata.get("source") != "asr":
        raise BatchFormatError(f"Batch transcript {path} is not marked source=asr")
    if metadata.get("source_audio_batch_id") != batch_id:
        raise BatchFormatError(f"Transcript {path} belongs to a different audio batch")
    if metadata.get("source_audio_sha256") != episode.sha256:
        raise BatchFormatError(f"Transcript {path} belongs to different audio bytes")
    model = metadata.get("model")
    if not isinstance(model, str) or not model:
        raise BatchFormatError(f"Transcript {path} has no ASR model provenance")
    return transcript


def run(config: Config, batch_dir: Path, limit: int | None = None,
        retry_errors: bool = False, verify_audio_hashes: bool = False) -> dict:
    if limit is not None and limit < 0:
        raise AudioBatchTranscriptionError("limit must be non-negative")
    batch_dir = Path(batch_dir).expanduser()
    manifest = validate_audio_batch_directory(batch_dir, verify_hashes=verify_audio_hashes)
    transcripts_dir = batch_dir / "transcripts"
    transcripts_dir.mkdir(exist_ok=True)
    store = TranscriptStore(transcripts_dir, config.storage.transcript_compression_level)
    failures_path = batch_dir / "transcription_failures.jsonl"
    failed_ids = _load_failures(failures_path)

    already_complete = 0
    skipped_failed = 0
    jobs: list[Job] = []
    for episode in manifest.episodes.values():
        transcript_path = store.path_for(episode.episode_id)
        if transcript_path.exists():
            validate_batch_transcript(transcript_path, episode, manifest.batch_id, store)
            already_complete += 1
            continue
        if episode.episode_id in failed_ids and not retry_errors:
            skipped_failed += 1
            continue
        audio_path = batch_dir.joinpath(*PurePosixPath(episode.archive_path).parts)
        jobs.append(Job(episode, audio_path))
    if limit is not None:
        jobs = jobs[:limit]

    result = {
        "batch_id": manifest.batch_id,
        "episodes": len(manifest.episodes),
        "already_transcribed": already_complete,
        "queued": len(jobs),
        "transcribed": 0,
        "failed": 0,
        "skipped_failed": skipped_failed,
        "not_attempted": 0,
    }
    if not jobs:
        return result

    lock_path = batch_dir / "transcribe.lock"
    with lock_path.open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AudioBatchTranscriptionError(
                f"Another transcription process is using {batch_dir}"
            ) from exc

        work: queue.Queue = queue.Queue()
        outcomes: queue.Queue = queue.Queue()
        for job in jobs:
            work.put(job)
        for _ in config.transcription.gpu_ids:
            work.put(_DONE)
        threads = [threading.Thread(
            target=_gpu_worker, args=(config, gpu_id, work, outcomes),
            name=f"batch-gpu-{gpu_id}", daemon=True,
        ) for gpu_id in config.transcription.gpu_ids]
        if not threads:
            raise AudioBatchTranscriptionError("transcription.gpu_ids cannot be empty")
        for thread in threads:
            thread.start()

        finished = 0
        handled = 0
        worker_errors: list[str] = []
        with tqdm(total=len(jobs), desc="Transcribing batch", unit="ep") as progress:
            while finished < len(threads):
                item = outcomes.get()
                if isinstance(item, WorkerFinished):
                    finished += 1
                    if item.error is not None:
                        worker_errors.append(f"GPU {item.gpu_id}: {item.error}")
                    continue
                outcome: Outcome = item
                handled += 1
                progress.update(1)
                if outcome.error is not None:
                    logger.error("Batch transcription failed for %r: %s",
                                 outcome.job.episode.episode_title, outcome.error)
                    _append_failure(failures_path, outcome.job, outcome.error)
                    result["failed"] += 1
                    continue
                model_result = outcome.result
                store.save(outcome.job.episode.episode_id, model_result.segments, {
                    "source": "asr",
                    "model": config.transcription.model_name,
                    "source_audio_batch_id": manifest.batch_id,
                    "source_audio_manifest_sha256": manifest.sha256,
                    "source_audio_sha256": outcome.job.episode.sha256,
                    "duration": model_result.duration_seconds,
                    "chunks": model_result.chunk_count,
                    "rtf": round(model_result.rtf, 4),
                    "episode_title": outcome.job.episode.episode_title,
                })
                result["transcribed"] += 1

        for thread in threads:
            thread.join()
        result["not_attempted"] = len(jobs) - handled
        if result["not_attempted"]:
            details = "; ".join(worker_errors) or "all workers exited early"
            raise AudioBatchTranscriptionError(
                f"{result['not_attempted']} episodes were not attempted because workers ended: {details}. "
                "Completed transcripts are durable; fix the worker error and rerun."
            )
    return result


def _gpu_worker(config: Config, gpu_id: int, work: queue.Queue, outcomes: queue.Queue) -> None:
    from podcast_pipeline.asr.parakeet import ParakeetTranscriber, TranscriptionError
    from podcast_pipeline.audio.ffmpeg import EncodeError

    fatal: Exception | None = None
    try:
        transcriber = ParakeetTranscriber(config.transcription, gpu_id)
        while True:
            job = work.get()
            if job is _DONE:
                break
            try:
                outcomes.put(Outcome(job, result=transcriber.transcribe_file(job.audio_path)))
            except (TranscriptionError, EncodeError) as exc:
                outcomes.put(Outcome(job, error=exc))
    except Exception as exc:
        fatal = exc
        logger.exception("Batch GPU %s worker died", gpu_id)
    finally:
        outcomes.put(WorkerFinished(gpu_id, fatal))
