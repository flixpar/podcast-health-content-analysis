"""One Parakeet model on one GPU, transcribing whole episodes.

Audio is decoded straight to memory with ffmpeg and handed to NeMo as numpy
arrays, so there is no preprocessing cache on disk to go stale or collide.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from nemo.collections.asr.models import ASRModel

from podcast_pipeline.asr import SAMPLE_RATE
from podcast_pipeline.asr.chunking import Word, chunk_spans, merge_chunk_words, words_to_segments
from podcast_pipeline.asr.vad import SileroVoiceActivityDetector, speech_chunk_spans
from podcast_pipeline.audio.ffmpeg import decode_pcm
from podcast_pipeline.config import TranscriptionConfig
from podcast_pipeline.models import Segment

logger = logging.getLogger(__name__)

# NeMo cannot transcribe essentially empty audio; treat it as an error upstream.
MIN_AUDIO_SECONDS = 1.0


class TranscriptionError(RuntimeError):
    pass


@dataclass
class TranscriptionResult:
    segments: list[Segment]
    duration_seconds: float
    chunk_count: int
    transcription_seconds: float
    detected_speech_spans: tuple[tuple[float, float], ...] = ()

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.segments)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def rtf(self) -> float:
        """Real-time factor: seconds of compute per second of audio."""
        return self.transcription_seconds / self.duration_seconds

    @property
    def detected_speech_seconds(self) -> float:
        return sum(end - start for start, end in self.detected_speech_spans)


class ParakeetTranscriber:
    def __init__(self, config: TranscriptionConfig, gpu_id: int):
        self.config = config
        self.gpu_id = gpu_id
        self.vad = SileroVoiceActivityDetector(config) if config.vad_enabled else None
        self.device = torch.device(f"cuda:{gpu_id}")
        torch.cuda.set_device(self.device)
        logger.info(f"Loading {config.model_name} on GPU {gpu_id}")
        self.model = ASRModel.from_pretrained(model_name=config.model_name,
                                              map_location=str(self.device))
        self.model.eval()
        if not config.use_cuda_graphs:
            self.model.disable_cuda_graphs()
        logger.info(f"GPU {gpu_id}: model ready "
                    f"({torch.cuda.memory_allocated(self.device) / 1e9:.1f} GB allocated)")

    def transcribe_file(self, path: Path) -> TranscriptionResult:
        audio = decode_pcm(path, SAMPLE_RATE)

        return self.transcribe_audio(audio)

    def transcribe_audio(self, audio: np.ndarray) -> TranscriptionResult:
        """Transcribe already-decoded 16 kHz mono PCM.

        Batch workflows use this entry point to overlap CPU decoding of future
        episodes with inference on the current episode.
        """
        duration = len(audio) / SAMPLE_RATE
        if duration < MIN_AUDIO_SECONDS:
            raise TranscriptionError(f"audio is only {duration:.2f}s long")

        if self.vad is None:
            detected_speech_spans = ((0.0, duration),)
            spans = chunk_spans(
                duration, self.config.chunk_duration_seconds, self.config.overlap_seconds,
            )
        else:
            detection = self.vad.detect(audio)
            detected_speech_spans = detection.spans
            spans = speech_chunk_spans(
                detection.spans,
                self.config.chunk_duration_seconds,
                self.config.overlap_seconds,
            )
        clips = [audio[int(s * SAMPLE_RATE):int(e * SAMPLE_RATE)] for s, e in spans]

        started = time.time()
        hypotheses = []
        if clips:
            torch.cuda.set_device(self.device)
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                hypotheses = self.model.transcribe(clips, batch_size=self.config.batch_size,
                                                   timestamps=True, return_hypotheses=True,
                                                   verbose=False)
        elapsed = time.time() - started

        chunks = []
        for (span_start, span_end), hyp in zip(spans, hypotheses):
            if not getattr(hyp, "timestamp", None) or "word" not in hyp.timestamp:
                raise TranscriptionError(f"{self.config.model_name} returned no word timestamps; "
                                         f"chunk merging needs them")
            words = [Word(text=w["word"], start=w["start"] + span_start, end=w["end"] + span_start)
                     for w in hyp.timestamp["word"]]
            chunks.append((span_start, span_end, words))

        segments = words_to_segments(merge_chunk_words(chunks))
        return TranscriptionResult(segments=segments, duration_seconds=duration,
                                   chunk_count=len(spans), transcription_seconds=elapsed,
                                   detected_speech_spans=detected_speech_spans)
