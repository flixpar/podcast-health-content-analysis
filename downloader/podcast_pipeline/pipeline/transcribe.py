"""Stage 4: transcribe downloaded audio with Parakeet, one worker thread per GPU.

Each worker loads its own model, pulls episodes from a shared queue, and
hands results back to the main thread, which writes the transcript file and
the database row.
"""

from __future__ import annotations

import logging
import queue
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from podcast_pipeline import db
from podcast_pipeline.config import Config
from podcast_pipeline.models import Segment
from podcast_pipeline.transcripts.store import TranscriptStore

logger = logging.getLogger(__name__)


@dataclass
class Job:
    episode_id: int
    title: str
    audio_path: Path


@dataclass
class Outcome:
    job: Job
    result: object = None        # TranscriptionResult
    error: Exception | None = None


_DONE = object()


def episodes_to_transcribe(conn: sqlite3.Connection, retry_errors: bool, limit: int | None) -> list[Job]:
    statuses = [db.EpisodeStatus.DOWNLOADED] + ([db.EpisodeStatus.ERROR] if retry_errors else [])
    rows = conn.execute(f"""
        SELECT id, title, audio_file_path
        FROM episodes
        WHERE status IN ({",".join("?" * len(statuses))})
          AND audio_file_path IS NOT NULL
          AND (transcript_file_path IS NULL OR transcript_file_path = '')
        ORDER BY published_date DESC
        {"LIMIT ?" if limit else ""}
    """, statuses + ([limit] if limit else [])).fetchall()
    return [Job(row["id"], row["title"], Path(row["audio_file_path"])) for row in rows]


def run(config: Config, conn: sqlite3.Connection, limit: int | None = None,
        retry_errors: bool = False) -> dict:
    jobs = episodes_to_transcribe(conn, retry_errors, limit)
    logger.info(f"Transcribing {len(jobs)} episodes on GPUs {config.transcription.gpu_ids}")
    stats = {"total": len(jobs), "transcribed": 0, "failed": 0, "missing_audio": 0}
    if not jobs:
        return stats

    store = TranscriptStore(config.transcript_dir, config.storage.transcript_compression_level)
    work: queue.Queue = queue.Queue()
    results: queue.Queue = queue.Queue()
    for job in jobs:
        if job.audio_path.exists():
            work.put(job)
        else:
            logger.warning(f"Audio missing for episode {job.episode_id}: {job.audio_path}")
            db.mark_episode_error(conn, job.episode_id, f"audio file missing: {job.audio_path}")
            stats["missing_audio"] += 1
    conn.commit()
    queued = work.qsize()
    for _ in config.transcription.gpu_ids:
        work.put(_DONE)

    threads = [threading.Thread(target=_gpu_worker, args=(config, gpu_id, work, results),
                                name=f"gpu-{gpu_id}", daemon=True)
               for gpu_id in config.transcription.gpu_ids]
    for thread in threads:
        thread.start()

    finished_workers = 0
    handled = 0
    while finished_workers < len(threads):
        item = results.get()
        if item is _DONE:
            finished_workers += 1
            continue
        handled += 1
        outcome: Outcome = item
        if outcome.error is not None:
            logger.error(f"Transcription failed for {outcome.job.title!r}: {outcome.error}")
            db.mark_episode_error(conn, outcome.job.episode_id, f"transcription: {outcome.error}")
            conn.commit()
            stats["failed"] += 1
            continue

        result = outcome.result
        saved = store.save(outcome.job.episode_id, result.segments, {
            "source": "asr", "model": config.transcription.model_name,
            "duration": result.duration_seconds, "chunks": result.chunk_count,
            "rtf": round(result.rtf, 4), "episode_title": outcome.job.title,
        })
        db.record_transcript(conn, outcome.job.episode_id, saved.path, saved.word_count,
                             saved.duration_seconds, has_timestamps=True, has_speakers=False,
                             metadata={"source": "asr", "model": config.transcription.model_name})
        conn.commit()
        stats["transcribed"] += 1
        logger.info(f"[{handled}/{queued}] {outcome.job.title!r}: {saved.word_count} words, "
                    f"{result.duration_seconds / 60:.1f} min, RTF {result.rtf:.3f}")

    for thread in threads:
        thread.join()
    logger.info(f"Transcription complete: {stats}")
    return stats


def _gpu_worker(config: Config, gpu_id: int, work: queue.Queue, results: queue.Queue) -> None:
    """Load a model on ``gpu_id`` and transcribe jobs until the sentinel arrives.

    Per-episode failures are reported as outcomes. Anything else (a model that
    will not load, a CUDA fault) is logged with its traceback and ends this
    worker; the main loop finishes once every worker has signalled.
    """
    from podcast_pipeline.asr.parakeet import ParakeetTranscriber, TranscriptionError

    try:
        transcriber = ParakeetTranscriber(config.transcription, gpu_id)
        while True:
            job = work.get()
            if job is _DONE:
                break
            try:
                results.put(Outcome(job, result=transcriber.transcribe_file(job.audio_path)))
            except TranscriptionError as e:
                results.put(Outcome(job, error=e))
    except Exception:
        logger.exception(f"GPU {gpu_id} worker died")
    finally:
        results.put(_DONE)
