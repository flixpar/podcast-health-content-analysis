"""Qwen3-ASR transcription through one or more vLLM HTTP endpoints."""

from __future__ import annotations

import difflib
import itertools
import logging
import math
import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from podcast_pipeline.asr import SAMPLE_RATE
from podcast_pipeline.asr.chunking import chunk_spans
from podcast_pipeline.asr.vad import SileroVoiceActivityDetector, speech_chunk_spans
from podcast_pipeline.audio.ffmpeg import (EncodeError, decode_pcm, probe_audio_codec,
                                           probe_duration, probe_stream_types)
from podcast_pipeline.config import TranscriptionConfig
from podcast_pipeline.models import Segment

logger = logging.getLogger(__name__)

MIN_AUDIO_SECONDS = 1.0
OVERLAP_WORD_WINDOW = 100
MIN_OVERLAP_MATCH_WORDS = 3
MAX_PLAUSIBLE_WORDS_PER_MINUTE = 300
REPETITION_WINDOW_WORDS = 200
REPETITION_DOMINANCE = 0.60
REPEATED_NGRAM_WORDS = 5
MIN_WORDS_FOR_NGRAM_CHECK = 30
MAX_DUPLICATE_NGRAM_FRACTION = 0.50
MAX_LOW_SIGNAL_MEAN_VOLUME_DB = -50.0
FALLBACK_CHUNK_SECONDS = 120
MIN_FALLBACK_CHUNK_SECONDS = 30
FALLBACK_DURATION_EPSILON_SECONDS = 1e-6
_OGG_AUDIO_CODECS = frozenset({"opus", "vorbis", "flac", "speex"})
_NORMALIZE_WORD = re.compile(r"[^\w']+", re.UNICODE)
_TRANSCRIPT_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)
_FAILURE_MARKER_WORD = re.compile(
    r"^\[UNTRANSCRIBED_AUDIO_[0-9.]+-[0-9.]+s_(?:ASR_FAILURE|LOW_SIGNAL|NO_AUDIO)\]$"
)
_MEAN_VOLUME = re.compile(rb"mean_volume:\s+(-?inf|[-0-9.]+) dB")
_N_SAMPLES = re.compile(rb"n_samples:\s+(\d+)")


class TranscriptionError(RuntimeError):
    pass


@dataclass
class TranscriptionResult:
    segments: list[Segment]
    duration_seconds: float
    chunk_count: int
    transcription_seconds: float
    fallback_retries: int = 0
    omitted_audio_spans: tuple[tuple[float, float], ...] = ()
    input_preprocessing: str | None = None
    detected_speech_spans: tuple[tuple[float, float], ...] = ()
    vad_provenance: dict | None = None

    @property
    def text(self) -> str:
        return " ".join(segment.text for segment in self.segments)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def rtf(self) -> float:
        return self.transcription_seconds / self.duration_seconds

    @property
    def omitted_audio_seconds(self) -> float:
        return _span_union_seconds(self.omitted_audio_spans)

    @property
    def detected_speech_seconds(self) -> float:
        return _span_union_seconds(self.detected_speech_spans)


@dataclass(frozen=True)
class TranscriptionPlan:
    path: Path
    duration_seconds: float
    spans: list[tuple[float, float]]
    seek_after_input: bool = False
    input_preprocessing: str | None = None
    detected_speech_spans: tuple[tuple[float, float], ...] = ()
    vad_provenance: dict | None = None


@dataclass(frozen=True)
class ChunkResult:
    text: str
    start: float
    end: float
    transcription_seconds: float
    fallback_retries: int = 0
    omitted_audio_spans: tuple[tuple[float, float], ...] = ()

    @property
    def omitted_audio_seconds(self) -> float:
        return _span_union_seconds(self.omitted_audio_spans)


@dataclass(frozen=True)
class SpanResult:
    text: str
    fallback_retries: int = 0
    omitted_audio_spans: tuple[tuple[float, float], ...] = ()

    @property
    def omitted_audio_seconds(self) -> float:
        return _span_union_seconds(self.omitted_audio_spans)


@dataclass(frozen=True)
class EncodedAudio:
    data: bytes
    mean_volume_db: float | None
    # Samples ffmpeg actually read for this span. Zero means the span lies past
    # the source's real audio; see ``_encode_flac_chunk``.
    sample_count: int | None = None


def _normalized(words: list[str]) -> list[str]:
    return [_NORMALIZE_WORD.sub("", word).casefold() for word in words]


def _span_union_seconds(spans: tuple[tuple[float, float], ...]) -> float:
    """Return covered seconds without double-counting fallback overlap."""
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


def trim_repeated_prefix(previous_text: str, current_text: str) -> str:
    """Remove the duplicated prefix created by overlapping untimed chunks.

    Qwen3-ASR's serving endpoint returns text but no timestamps. Search only a
    bounded suffix/prefix window and require a multi-word exact normalized
    match. If no safe anchor exists, retain both texts rather than risk dropping
    speech.
    """
    previous = previous_text.split()
    current = current_text.split()
    left = previous[-OVERLAP_WORD_WINDOW:]
    right = current[:OVERLAP_WORD_WINDOW]
    matcher = difflib.SequenceMatcher(None, _normalized(left), _normalized(right), autojunk=False)
    # An overlap anchor must be near both relevant boundaries. Otherwise a
    # common phrase in the middle of two chunks could delete unique speech.
    boundary_slack = 30
    matches = [block for block in matcher.get_matching_blocks()
               if block.size >= MIN_OVERLAP_MATCH_WORDS
               and len(left) - (block.a + block.size) <= boundary_slack
               and block.b <= boundary_slack]
    if not matches:
        return current_text.strip()
    # Prefer the longest anchor, then one nearest the old suffix/new prefix.
    match = max(matches, key=lambda block: (
        block.size,
        -(len(left) - block.a - block.size),
        -block.b,
    ))
    cut = match.b + match.size
    # A marker can precede the repeated speech used as the overlap anchor.
    # Never discard such a marker unless the identical interval is already in
    # the previous chunk; it represents source time, not duplicate prose.
    previous_markers = {
        word for word in previous if _FAILURE_MARKER_WORD.fullmatch(word)
    }
    removed_markers = [
        word for word in current[:cut]
        if _FAILURE_MARKER_WORD.fullmatch(word) and word not in previous_markers
    ]
    return " ".join([*removed_markers, *current[cut:]]).strip()


def is_implausible_transcript(text: str, duration_seconds: float) -> bool:
    """Detect impossible density and degenerate decoder repetition."""
    # Split on punctuation as well as whitespace. Qwen occasionally emits
    # runaway CJK tokens separated only by Chinese punctuation; ``str.split``
    # treated the entire run as one word and let those hallucinations through.
    words = [
        match.group(0).replace("’", "'")
        for match in _TRANSCRIPT_WORD.finditer(text)
    ]
    plausible_limit = max(
        50,
        math.ceil(duration_seconds / 60 * MAX_PLAUSIBLE_WORDS_PER_MINUTE),
    )
    if len(words) > plausible_limit:
        return True
    tail = [word for word in _normalized(words[-REPETITION_WINDOW_WORDS:]) if word]
    if len(tail) >= 50:
        counts = {word: tail.count(word) for word in set(tail)}
        if max(counts.values(), default=0) / len(tail) >= REPETITION_DOMINANCE:
            return True
    normalized = [word for word in _normalized(words) if word]
    if len(normalized) < MIN_WORDS_FOR_NGRAM_CHECK:
        return False
    ngrams = list(zip(*(normalized[index:] for index in range(REPEATED_NGRAM_WORDS))))
    duplicate_fraction = 1 - len(set(ngrams)) / len(ngrams)
    return duplicate_fraction >= MAX_DUPLICATE_NGRAM_FRACTION


def _stream_types_or_raise(path: Path) -> tuple[str, ...]:
    try:
        stream_types = probe_stream_types(path)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EncodeError(f"ffprobe failed to inspect streams in {path}: {exc}") from exc
    if stream_types is None:
        raise EncodeError(f"ffprobe could not inspect streams in {path}")
    if "audio" not in stream_types:
        raise EncodeError(f"no audio stream found in {path}")
    return stream_types


def _audio_only_container(path: Path) -> tuple[str, str]:
    """Pick a muxer that can carry this file's audio codec without re-encoding.

    Ogg accepts only a handful of codecs. Remuxing an MP3 into it fails with
    "Unsupported codec id in stream 0", which discarded every cover-art MP3
    before the container was chosen from the codec. Matroska carries anything.
    """
    codec = probe_audio_codec(path)
    if codec is None:
        raise EncodeError(f"ffprobe could not read the audio codec in {path}")
    if codec in _OGG_AUDIO_CODECS:
        return "ogg", "ogg"
    return "matroska", "mka"


def _audio_only_remux(path: Path, cache_dir: Path, duration: float) -> Path:
    """Losslessly cache the first audio stream, atomically and resumably."""
    source_stat = path.stat()
    cache_dir.mkdir(parents=True, exist_ok=True)
    muxer, suffix = _audio_only_container(path)
    target = cache_dir / (
        f"{path.stem}-{source_stat.st_size}-{source_stat.st_mtime_ns}"
        f".audio-only.{suffix}"
    )
    if target.exists():
        cached_duration = probe_duration(target)
        if (cached_duration is not None and cached_duration >= duration * 0.999
                and probe_stream_types(target) == ("audio",)):
            return target
        target.unlink()
    temporary = target.with_name(
        f".{target.name}.{os.getpid()}-{threading.get_ident()}.partial"
    )
    try:
        proc = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
             "-i", str(path), "-map", "0:a:0", "-vn", "-sn", "-dn",
             "-map_metadata", "-1", "-c:a", "copy", "-f", muxer, "-y",
             str(temporary)],
            capture_output=True, timeout=max(120, int(duration)),
        )
        if proc.returncode != 0:
            raise EncodeError(
                f"ffmpeg failed to remux {path}: "
                f"{proc.stderr.decode(errors='replace')[-500:]}"
            )
        cached_duration = probe_duration(temporary)
        if cached_duration is None or cached_duration < duration * 0.999:
            raise EncodeError(
                f"audio-only remux of {path} is short: {cached_duration} vs {duration}"
            )
        if probe_stream_types(temporary) != ("audio",):
            raise EncodeError(f"audio-only remux of {path} has unexpected streams")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def _encode_flac_chunk(path: Path, start: float, end: float,
                       seek_after_input: bool = False) -> EncodedAudio:
    duration = end - start
    # FLAC's STREAMINFO stores the total sample count. When ffmpeg writes to a
    # pipe it cannot seek back to fill that field, and vLLM/libsndfile treats
    # the unknown sentinel as a fantastically long clip. A completed local
    # file has the correct header and is removed immediately after reading.
    with tempfile.TemporaryDirectory(prefix="qwen-asr-flac-") as temporary:
        target = Path(temporary) / "chunk.flac"
        try:
            input_args = ["-i", str(path), "-ss", f"{start:.6f}"] if seek_after_input else [
                "-ss", f"{start:.6f}", "-i", str(path)
            ]
            proc = subprocess.run(
                [
                    "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "info",
                    *input_args, "-t", f"{duration:.6f}",
                    "-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "-1",
                    "-ac", "1", "-ar", str(SAMPLE_RATE), "-sample_fmt", "s16",
                    "-af", "volumedetect", "-c:a", "flac", "-y", str(target),
                ],
                capture_output=True,
                timeout=max(120, int(duration * 2)),
            )
        except subprocess.TimeoutExpired as exc:
            raise EncodeError(
                f"ffmpeg timed out preparing {path} at {start:.1f}-{end:.1f}s"
            ) from exc
        if proc.returncode != 0:
            raise EncodeError(
                f"ffmpeg failed to prepare {path} at {start:.1f}-{end:.1f}s: "
                f"{proc.stderr.decode(errors='replace')[-500:]}"
            )
        audio = target.read_bytes()
        if not audio:
            raise EncodeError(f"ffmpeg produced an empty chunk for {path} at {start:.1f}s")
        match = _MEAN_VOLUME.search(proc.stderr)
        mean_volume_db = None
        if match:
            value = match.group(1).decode("ascii")
            mean_volume_db = -math.inf if value == "-inf" else float(value)
        # A span past the source's real audio -- routine when an MP3 header
        # overstates its duration -- still exits 0 and writes a header-only
        # FLAC. FLAC stores "unknown" as a zero sample count, which libsndfile
        # reports to vLLM as 2**63 samples and vLLM rejects as a 5.8e14 second
        # clip, discarding the whole episode over an empty tail. volumedetect
        # counts what ffmpeg actually read; it also logs a zero at filter
        # init, so only the largest count describes the span.
        counts = [int(found.group(1)) for found in _N_SAMPLES.finditer(proc.stderr)]
        return EncodedAudio(audio, mean_volume_db, max(counts) if counts else None)


class QwenVLLMTranscriber:
    """Thread-safe client whose calls are globally balanced across endpoints."""

    def __init__(self, config: TranscriptionConfig):
        if not config.vllm_urls:
            raise TranscriptionError("transcription.vllm_urls cannot be empty")
        self.config = config
        self.urls = [url.rstrip("/") for url in config.vllm_urls]
        self._url_counter = itertools.count()
        self._url_lock = threading.Lock()
        self._local = threading.local()
        self._vad_plan = None
        self._vad = None
        if config.vad_enabled and config.vad_plan_path:
            from podcast_pipeline.asr.vad_plan import PrecomputedVADPlan
            self._vad_plan = PrecomputedVADPlan.load(config.vad_plan_path)
        elif config.vad_enabled:
            self._vad = SileroVoiceActivityDetector(config)
        self._vad_lock = threading.Lock()

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            # Cluster proxy variables must never intercept node-local vLLM.
            session.trust_env = False
            adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1)
            session.mount("http://", adapter)
            self._local.session = session
        return session

    def _next_url(self) -> str:
        with self._url_lock:
            return self.urls[next(self._url_counter) % len(self.urls)]

    def _request(self, audio: bytes, label: str,
                 max_completion_tokens: int | None = None) -> str:
        fields = {"model": self.config.model_name}
        if self.config.vllm_language:
            fields["language"] = self.config.vllm_language
        if max_completion_tokens is None:
            max_completion_tokens = self.config.vllm_max_completion_tokens
        if max_completion_tokens is not None:
            fields["max_completion_tokens"] = str(
                max_completion_tokens
            )
        url = f"{self._next_url()}/v1/audio/transcriptions"
        try:
            response = self._session().post(
                url,
                data=fields,
                files={"file": (f"{label}.flac", audio, "audio/flac")},
                timeout=self.config.vllm_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            detail = ""
            if getattr(exc, "response", None) is not None:
                detail = f": {exc.response.text[-1000:]}"
            raise TranscriptionError(f"vLLM request failed for {label}: {exc}{detail}") from exc
        text = body.get("text")
        if not isinstance(text, str):
            raise TranscriptionError(f"vLLM returned no transcript text for {label}: {body!r}")
        return text.strip()

    def plan_file(self, path: Path) -> TranscriptionPlan:
        try:
            duration = probe_duration(path)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EncodeError(f"ffprobe failed on {path}: {exc}") from exc
        if duration is None:
            raise EncodeError(f"ffprobe could not read duration from {path}")
        if duration < MIN_AUDIO_SECONDS:
            raise TranscriptionError(f"audio is only {duration:.2f}s long")
        stream_types = _stream_types_or_raise(path)
        needs_audio_only_input = stream_types != ("audio",)
        transcription_path = path
        # Fast input seeking is unsafe for some containers with sparse cover-art
        # streams. Output seeking is slower but correct when no cache is set.
        seek_after_input = needs_audio_only_input
        preprocessing = "safe_output_seek_for_extra_streams" if seek_after_input else None
        if needs_audio_only_input and self.config.vllm_audio_remux_cache_dir:
            transcription_path = _audio_only_remux(
                path, Path(self.config.vllm_audio_remux_cache_dir).expanduser(), duration,
            )
            seek_after_input = False
            preprocessing = "lossless_audio_stream_remux"
        vad_provenance = None
        if self._vad_plan is not None:
            detection = self._vad_plan.detect(path, duration)
            detected_speech_spans = detection.spans
            spans = speech_chunk_spans(
                detection.spans,
                self.config.chunk_duration_seconds,
                self.config.overlap_seconds,
            )
            vad_provenance = self._vad_plan.transcript_metadata()
        elif self._vad is None:
            detected_speech_spans = ((0.0, duration),)
            spans = chunk_spans(
                duration,
                self.config.chunk_duration_seconds,
                self.config.overlap_seconds,
            )
        else:
            # Silero keeps recurrent state during one file. Decode and detect
            # under one lock so concurrent batch planning cannot retain many
            # full podcast waveforms in RAM while waiting for the shared model.
            with self._vad_lock:
                audio = decode_pcm(transcription_path, SAMPLE_RATE)
                detection = self._vad.detect(audio)
            detected_speech_spans = detection.spans
            spans = speech_chunk_spans(
                detection.spans,
                self.config.chunk_duration_seconds,
                self.config.overlap_seconds,
            )
        return TranscriptionPlan(
            transcription_path, duration, spans, seek_after_input, preprocessing,
            detected_speech_spans, vad_provenance,
        )

    def transcribe_chunk(self, plan: TranscriptionPlan, index: int) -> ChunkResult:
        start, end = plan.spans[index]
        started = time.monotonic()
        span_result = self._transcribe_span(
            plan.path, start, end, f"{plan.path.stem}-{index:04d}",
            plan.seek_after_input,
        )
        return ChunkResult(
            span_result.text,
            start,
            end,
            time.monotonic() - started,
            span_result.fallback_retries,
            span_result.omitted_audio_spans,
        )

    def _transcribe_span(self, path: Path, start: float, end: float,
                         label: str, seek_after_input: bool = False) -> SpanResult:
        duration = end - start
        encoded = _encode_flac_chunk(path, start, end, seek_after_input)
        if encoded.sample_count == 0:
            # Distinct from LOW_SIGNAL: silent audio was present and measured,
            # whereas here the container simply has nothing at this offset.
            logger.warning(
                "Omitting %.1fs span %s: the source holds no audio there "
                "(its declared duration overstates its decodable audio)",
                duration, label,
            )
            marker = f"[UNTRANSCRIBED_AUDIO_{start:.1f}-{end:.1f}s_NO_AUDIO]"
            return SpanResult(marker, omitted_audio_spans=((start, end),))
        if (encoded.mean_volume_db is not None
                and encoded.mean_volume_db <= MAX_LOW_SIGNAL_MEAN_VOLUME_DB):
            logger.warning(
                "Omitting %.1fs low-signal span %s (mean volume %.1f dB)",
                duration, label, encoded.mean_volume_db,
            )
            marker = f"[UNTRANSCRIBED_AUDIO_{start:.1f}-{end:.1f}s_LOW_SIGNAL]"
            return SpanResult(marker, omitted_audio_spans=((start, end),))
        configured_max = self.config.vllm_max_completion_tokens
        if configured_max is None:
            max_tokens = None
        else:
            max_tokens = max(
                256,
                math.ceil(configured_max * duration / self.config.chunk_duration_seconds),
            )
        text = self._request(encoded.data, label, max_tokens)
        if text and not is_implausible_transcript(text, duration):
            return SpanResult(text)
        # ``chunk_spans`` adds decimal offsets repeatedly, so a nominal 30s
        # terminal span can be a few ulps greater than 30. Without a tolerance
        # that span is split into itself forever when the model repeats the
        # same implausible output.
        if duration <= (
            MIN_FALLBACK_CHUNK_SECONDS + FALLBACK_DURATION_EPSILON_SECONDS
        ):
            logger.warning(
                "Omitting %.1fs span %s after Qwen remained implausible at minimum size",
                duration, label,
            )
            # Keep this a single token so overlap de-duplication cannot merge
            # adjacent failure markers that share descriptive words.
            marker = f"[UNTRANSCRIBED_AUDIO_{start:.1f}-{end:.1f}s_ASR_FAILURE]"
            return SpanResult(
                marker, fallback_retries=1, omitted_audio_spans=((start, end),),
            )

        target = (
            FALLBACK_CHUNK_SECONDS
            if duration > FALLBACK_CHUNK_SECONDS * 1.5
            else MIN_FALLBACK_CHUNK_SECONDS
        )
        overlap = min(self.config.overlap_seconds, target / 6)
        logger.warning(
            "Qwen output for %s is implausible (%d words over %.1fs); retrying %.0fs spans",
            label, len(text.split()), duration, target,
        )
        parts: list[str] = []
        previous = ""
        retries = 1
        omitted_spans: list[tuple[float, float]] = []
        for sub_index, (relative_start, relative_end) in enumerate(
            chunk_spans(duration, target, overlap)
        ):
            sub_result = self._transcribe_span(
                path,
                start + relative_start,
                start + relative_end,
                f"{label}-retry-{sub_index:02d}",
                seek_after_input,
            )
            part = sub_result.text
            retries += sub_result.fallback_retries
            omitted_spans.extend(sub_result.omitted_audio_spans)
            if previous:
                part = trim_repeated_prefix(previous, part)
            if part:
                parts.append(part)
                previous = " ".join(f"{previous} {part}".split()[-OVERLAP_WORD_WINDOW:])
        combined = " ".join(parts)
        retained_speech = " ".join(
            word for word in combined.split()
            if not _FAILURE_MARKER_WORD.fullmatch(word)
        )
        if retained_speech and is_implausible_transcript(retained_speech, duration):
            logger.warning(
                "Omitting %.1fs span %s after combined fallback output remained implausible",
                duration, label,
            )
            marker = f"[UNTRANSCRIBED_AUDIO_{start:.1f}-{end:.1f}s_ASR_FAILURE]"
            return SpanResult(
                marker, retries + 1,
                tuple([*omitted_spans, (start, end)]),
            )
        return SpanResult(combined, retries, tuple(omitted_spans))

    def assemble(self, plan: TranscriptionPlan,
                 chunks: list[ChunkResult]) -> TranscriptionResult:
        if len(chunks) != len(plan.spans):
            raise TranscriptionError(
                f"received {len(chunks)} chunks for {len(plan.spans)} spans in {plan.path}"
            )
        segments: list[Segment] = []
        previous_text = ""
        previous_end: float | None = None
        for chunk in chunks:
            text = chunk.text
            overlaps_previous = previous_end is not None and chunk.start < previous_end
            if previous_text and overlaps_previous:
                text = trim_repeated_prefix(previous_text, text)
            if text:
                segments.append(Segment(text=text, start=chunk.start, end=chunk.end))
            if overlaps_previous:
                previous_text = f"{previous_text} {text}"
            else:
                previous_text = text
            # Only the suffix can participate in the next overlap.
            previous_text = " ".join(previous_text.split()[-OVERLAP_WORD_WINDOW:])
            previous_end = chunk.end
        return TranscriptionResult(
            segments=segments,
            duration_seconds=plan.duration_seconds,
            chunk_count=len(chunks),
            transcription_seconds=sum(chunk.transcription_seconds for chunk in chunks),
            fallback_retries=sum(chunk.fallback_retries for chunk in chunks),
            omitted_audio_spans=tuple(
                span for chunk in chunks for span in chunk.omitted_audio_spans
            ),
            input_preprocessing=plan.input_preprocessing,
            detected_speech_spans=plan.detected_speech_spans,
            vad_provenance=getattr(plan, "vad_provenance", None),
        )

    def transcribe_file(self, path: Path) -> TranscriptionResult:
        plan = self.plan_file(path)
        chunks = [self.transcribe_chunk(plan, index) for index in range(len(plan.spans))]
        return self.assemble(plan, chunks)
