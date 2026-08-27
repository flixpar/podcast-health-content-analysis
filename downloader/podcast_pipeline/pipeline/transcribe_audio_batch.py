"""Resumably transcribe an extracted audio batch without the source database."""

from __future__ import annotations

import fcntl
import json
import logging
import multiprocessing
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from tqdm import tqdm

from podcast_pipeline.batches import (AudioEpisode, BatchFormatError,
                                      validate_audio_batch_directory)
from podcast_pipeline.config import Config
from podcast_pipeline.transcripts.store import TranscriptStore

logger = logging.getLogger(__name__)

_DONE = None


class AudioBatchTranscriptionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Job:
    episode: AudioEpisode
    audio_path: Path


@dataclass(frozen=True)
class DecodedJob:
    job: Job
    audio: object


@dataclass
class Outcome:
    job: Job
    result: object = None
    error: Exception | None = None


@dataclass
class WorkerFinished:
    gpu_id: int
    error: Exception | None = None


@dataclass
class QwenEpisodeState:
    job: Job
    plan: object
    chunks: list[object | None]
    remaining: int
    error: Exception | None = None


def _load_failures(path: Path) -> set[int]:
    failed: set[int] = set()
    if not path.exists():
        return failed
    with path.open("r+b") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        payload = stream.read()
        terminated = payload.endswith(b"\n")
        lines = payload.split(b"\n")
        if terminated:
            lines.pop()
        for index, line in enumerate(lines):
            line_number = index + 1
            try:
                record = json.loads(line)
                failed.add(int(record["episode_id"]))
            except (ValueError, KeyError) as exc:
                if index == len(lines) - 1 and not terminated:
                    # A killed append can leave only the final JSON object
                    # fragment. Remove that fragment while holding the same
                    # advisory lock used by appenders, so the next failure
                    # record starts at a clean JSONL boundary.
                    tail_start = len(payload) - len(line)
                    stream.seek(tail_start)
                    stream.truncate()
                    stream.flush()
                    os.fsync(stream.fileno())
                    logger.warning(
                        "Discarded truncated final failure-log record at %s line %d",
                        path, line_number,
                    )
                    break
                raise AudioBatchTranscriptionError(
                    f"Invalid failure log {path} at line {line_number}: {exc}"
                ) from exc
        else:
            # A complete JSON object can survive while its trailing newline
            # does not. Normalize it before a future append to avoid joining
            # two otherwise valid objects on one line.
            if lines and not terminated:
                stream.seek(0, os.SEEK_END)
                stream.write(b"\n")
                stream.flush()
                os.fsync(stream.fileno())
    return failed


def _append_failure(path: Path, job: Job, error: Exception) -> None:
    record = {
        "record_type": "transcription_failure",
        "episode_id": job.episode.episode_id,
        "failed_at": datetime.now(UTC).isoformat(),
        "error_type": type(error).__name__,
        "error": str(error)[:2000],
    }
    payload = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    with path.open("a+b") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(payload)
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
    if config.transcription.decode_workers < 0:
        raise AudioBatchTranscriptionError("transcription.decode_workers cannot be negative")
    if config.transcription.decode_workers and config.transcription.decode_prefetch < 1:
        raise AudioBatchTranscriptionError(
            "transcription.decode_prefetch must be positive when parallel decoding is enabled"
        )
    backend = config.transcription.backend
    if backend not in {"parakeet", "qwen_vllm"}:
        raise AudioBatchTranscriptionError(
            "transcription.backend must be 'parakeet' or 'qwen_vllm'"
        )
    if backend == "qwen_vllm":
        if config.transcription.vllm_request_concurrency < 1:
            raise AudioBatchTranscriptionError(
                "transcription.vllm_request_concurrency must be positive"
            )
        if not config.transcription.vllm_urls:
            raise AudioBatchTranscriptionError("transcription.vllm_urls cannot be empty")
        if (config.transcription.vllm_max_completion_tokens is not None
                and config.transcription.vllm_max_completion_tokens < 1):
            raise AudioBatchTranscriptionError(
                "transcription.vllm_max_completion_tokens must be positive or null"
            )
    if config.transcription.isolated_gpu_workers:
        gpu_count = len(config.transcription.gpu_ids)
        if not gpu_count:
            raise AudioBatchTranscriptionError("transcription.gpu_ids cannot be empty")
        if config.transcription.decode_workers and (
                config.transcription.decode_workers < gpu_count
                or config.transcription.decode_workers % gpu_count):
            raise AudioBatchTranscriptionError(
                "isolated transcription requires decode_workers to be a multiple of GPU workers"
            )
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

        if backend == "qwen_vllm":
            _run_qwen_vllm(
                config, jobs, store, manifest, failures_path, result,
            )
            return result

        isolated = config.transcription.isolated_gpu_workers
        work = None
        outcomes = None
        decode_threads: list[threading.Thread] = []
        coordinator: threading.Thread | None = None
        if isolated:
            context = multiprocessing.get_context("spawn")
            work = context.Queue()
            outcomes = context.Queue()
            for job in jobs:
                work.put(job)
            sentinel_count = config.transcription.decode_workers or len(config.transcription.gpu_ids)
            for _ in range(sentinel_count):
                work.put(_DONE)
            decoder_count = max(
                1, config.transcription.decode_workers // len(config.transcription.gpu_ids)
            )
            prefetch = max(
                1, config.transcription.decode_prefetch // len(config.transcription.gpu_ids)
            )
            workers = [context.Process(
                target=_isolated_gpu_worker,
                args=(config, gpu_id, work, outcomes, decoder_count, prefetch),
                name=f"batch-worker-{index}-gpu-{gpu_id}",
            ) for index, gpu_id in enumerate(config.transcription.gpu_ids)]
        elif config.transcription.decode_workers:
            work = queue.Queue()
            outcomes = queue.Queue()
            decode_work: queue.Queue = queue.Queue()
            work = queue.Queue(maxsize=config.transcription.decode_prefetch)
            for job in jobs:
                decode_work.put(job)
            for _ in range(config.transcription.decode_workers):
                decode_work.put(_DONE)
            decode_threads = [threading.Thread(
                target=_decode_worker, args=(decode_work, work, outcomes),
                name=f"batch-decode-{index}", daemon=True,
            ) for index in range(config.transcription.decode_workers)]

            def finish_decoding() -> None:
                for thread in decode_threads:
                    thread.join()
                for _ in config.transcription.gpu_ids:
                    work.put(_DONE)

            coordinator = threading.Thread(
                target=finish_decoding, name="batch-decode-coordinator", daemon=True,
            )
        else:
            work = queue.Queue()
            outcomes = queue.Queue()
            for job in jobs:
                work.put(job)
            for _ in config.transcription.gpu_ids:
                work.put(_DONE)
        if not isolated:
            workers = [threading.Thread(
                target=_gpu_worker, args=(config, gpu_id, work, outcomes),
                name=f"batch-gpu-{gpu_id}", daemon=True,
            ) for gpu_id in config.transcription.gpu_ids]
        if not workers:
            raise AudioBatchTranscriptionError("transcription.gpu_ids cannot be empty")
        for thread in decode_threads:
            thread.start()
        if coordinator is not None:
            coordinator.start()
        for worker in workers:
            worker.start()

        finished = 0
        handled = 0
        worker_errors: list[str] = []
        with tqdm(total=len(jobs), desc="Transcribing batch", unit="ep") as progress:
            while finished < len(workers):
                try:
                    item = outcomes.get(timeout=5 if isolated else None)
                except queue.Empty:
                    if all(not worker.is_alive() for worker in workers):
                        break
                    continue
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
                    "batch_size": config.transcription.batch_size,
                    "chunk_duration_seconds": config.transcription.chunk_duration_seconds,
                    "overlap_seconds": config.transcription.overlap_seconds,
                    "use_cuda_graphs": config.transcription.use_cuda_graphs,
                    "source_audio_batch_id": manifest.batch_id,
                    "source_audio_manifest_sha256": manifest.sha256,
                    "source_audio_sha256": outcome.job.episode.sha256,
                    "duration": model_result.duration_seconds,
                    "chunks": model_result.chunk_count,
                    "rtf": round(model_result.rtf, 4),
                    "episode_title": outcome.job.episode.episode_title,
                })
                result["transcribed"] += 1

        for worker in workers:
            worker.join()
        if isolated:
            silent_crashes = [
                f"{worker.name} exited with status {worker.exitcode}"
                for worker in workers if worker.exitcode
            ]
            worker_errors.extend(silent_crashes)
        result["not_attempted"] = len(jobs) - handled
        if result["not_attempted"]:
            details = "; ".join(worker_errors) or "all workers exited early"
            raise AudioBatchTranscriptionError(
                f"{result['not_attempted']} episodes were not attempted because workers ended: {details}. "
                "Completed transcripts are durable; fix the worker error and rerun."
            )
    return result


def _run_qwen_vllm(config: Config, jobs: list[Job], store: TranscriptStore,
                   manifest, failures_path: Path, result: dict) -> None:
    """Globally schedule chunks, then durably assemble episodes in order."""
    from podcast_pipeline.asr.qwen_vllm import QwenVLLMTranscriber, TranscriptionError
    from podcast_pipeline.audio.ffmpeg import EncodeError

    transcriber = QwenVLLMTranscriber(config.transcription)
    started = time.monotonic()
    audio_seconds = 0.0
    omitted_audio_seconds = 0.0

    with ThreadPoolExecutor(
        max_workers=config.transcription.vllm_request_concurrency,
        thread_name_prefix="qwen-vllm",
    ) as executor:
        plan_futures = {
            executor.submit(transcriber.plan_file, job.audio_path): job for job in jobs
        }
        states: dict[int, QwenEpisodeState] = {}
        with tqdm(total=len(jobs), desc="Transcribing batch", unit="ep") as progress:
            for future in as_completed(plan_futures):
                job = plan_futures.pop(future)
                try:
                    plan = future.result()
                except (TranscriptionError, EncodeError) as exc:
                    logger.error(
                        "Batch transcription failed for %r: %s",
                        job.episode.episode_title, exc,
                    )
                    _append_failure(failures_path, job, exc)
                    result["failed"] += 1
                    progress.update(1)
                    continue
                states[job.episode.episode_id] = QwenEpisodeState(
                    job=job,
                    plan=plan,
                    chunks=[None] * len(plan.spans),
                    remaining=len(plan.spans),
                )

            chunk_futures = {}
            for state in states.values():
                for index in range(len(state.chunks)):
                    future = executor.submit(transcriber.transcribe_chunk, state.plan, index)
                    chunk_futures[future] = (state, index)

            for future in as_completed(chunk_futures):
                state, index = chunk_futures.pop(future)
                try:
                    state.chunks[index] = future.result()
                except (TranscriptionError, EncodeError) as exc:
                    if state.error is None:
                        state.error = exc
                state.remaining -= 1
                if state.remaining:
                    continue
                progress.update(1)
                if state.error is not None:
                    logger.error(
                        "Batch transcription failed for %r: %s",
                        state.job.episode.episode_title, state.error,
                    )
                    _append_failure(failures_path, state.job, state.error)
                    result["failed"] += 1
                    del states[state.job.episode.episode_id]
                    continue
                model_result = transcriber.assemble(
                    state.plan,
                    [chunk for chunk in state.chunks if chunk is not None],
                )
                store.save(state.job.episode.episode_id, model_result.segments, {
                    "source": "asr",
                    "backend": "qwen_vllm",
                    "model": config.transcription.model_name,
                    "chunk_duration_seconds": config.transcription.chunk_duration_seconds,
                    "overlap_seconds": config.transcription.overlap_seconds,
                    "language": config.transcription.vllm_language,
                    "vllm_request_concurrency": config.transcription.vllm_request_concurrency,
                    "vllm_max_completion_tokens": (
                        config.transcription.vllm_max_completion_tokens
                    ),
                    "source_audio_batch_id": manifest.batch_id,
                    "source_audio_manifest_sha256": manifest.sha256,
                    "source_audio_sha256": state.job.episode.sha256,
                    "duration": model_result.duration_seconds,
                    "chunks": model_result.chunk_count,
                    "fallback_retries": model_result.fallback_retries,
                    "omitted_audio_seconds": round(model_result.omitted_audio_seconds, 3),
                    "omitted_audio_spans": [
                        [round(start, 3), round(end, 3)]
                        for start, end in model_result.omitted_audio_spans
                    ],
                    "input_preprocessing": model_result.input_preprocessing,
                    "rtf": round(model_result.rtf, 4),
                    "episode_title": state.job.episode.episode_title,
                })
                audio_seconds += model_result.duration_seconds
                omitted_audio_seconds += model_result.omitted_audio_seconds
                result["transcribed"] += 1
                del states[state.job.episode.episode_id]

    wall_seconds = time.monotonic() - started
    result["audio_seconds"] = round(audio_seconds, 3)
    result["wall_seconds"] = round(wall_seconds, 3)
    result["rtfx"] = round(audio_seconds / wall_seconds, 2) if wall_seconds else None
    result["omitted_audio_seconds"] = round(omitted_audio_seconds, 3)


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
                if isinstance(job, DecodedJob):
                    outcomes.put(Outcome(
                        job.job, result=transcriber.transcribe_audio(job.audio)
                    ))
                else:
                    outcomes.put(Outcome(job, result=transcriber.transcribe_file(job.audio_path)))
            except (TranscriptionError, EncodeError) as exc:
                source_job = job.job if isinstance(job, DecodedJob) else job
                outcomes.put(Outcome(source_job, error=exc))
    except Exception as exc:
        fatal = exc
        logger.exception("Batch GPU %s worker died", gpu_id)
    finally:
        outcomes.put(WorkerFinished(gpu_id, fatal))


def _decode_worker(work: queue.Queue, ready: queue.Queue, outcomes: queue.Queue) -> None:
    from podcast_pipeline.audio.ffmpeg import EncodeError, decode_pcm
    from podcast_pipeline.asr import SAMPLE_RATE

    while True:
        job = work.get()
        if job is _DONE:
            return
        try:
            audio = decode_pcm(job.audio_path, SAMPLE_RATE)
        except EncodeError as exc:
            outcomes.put(Outcome(job, error=exc))
            continue
        ready.put(DecodedJob(job, audio))


def _isolated_gpu_worker(config: Config, gpu_id: int, work, outcomes,
                         decoder_count: int, prefetch: int) -> None:
    """Run one CUDA model in its own process with local decode prefetch."""
    ready: queue.Queue = queue.Queue(maxsize=prefetch)
    decoders = [threading.Thread(
        target=_decode_worker, args=(work, ready, outcomes),
        name=f"gpu-{gpu_id}-decode-{index}", daemon=True,
    ) for index in range(decoder_count)]

    def finish_decoding() -> None:
        for decoder in decoders:
            decoder.join()
        ready.put(_DONE)

    for decoder in decoders:
        decoder.start()
    threading.Thread(
        target=finish_decoding, name=f"gpu-{gpu_id}-decode-coordinator", daemon=True,
    ).start()
    _gpu_worker(config, gpu_id, ready, outcomes)
