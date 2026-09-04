"""Typed configuration loaded from ``config.json``.

Every tunable has exactly one default, declared on the dataclass below. The
loader rejects unknown keys so a typo in ``config.json`` fails immediately
instead of silently falling back to a default.
"""

from __future__ import annotations

import dataclasses
import json
import os
import typing
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"
LOG_DIR = PROJECT_ROOT / "logs"


class ConfigError(ValueError):
    """config.json is malformed or contains a key the pipeline does not know."""


@dataclass
class FetcherConfig:
    type: str = "apple"               # "apple" (no auth), "spotify" (no auth), or "podchaser"
    filter_health_only: bool = False  # keep only health-related podcasts from the charts
    default_limit: int = 100          # podcasts to fetch when --limit is not given
    country: str = "us"               # storefront / chart region
    genre: str | None = None          # Apple genre id (e.g. "1512" = Health & Fitness); None = overall chart


@dataclass
class PodchaserConfig:
    client_id: str = ""
    client_secret: str = ""
    api_url: str = "https://api.podchaser.com/graphql"


@dataclass
class SpotifyConfig:
    """Spotify's public podcast chart (podcastcharts.byspotify.com).

    The chart carries no RSS URLs, so each show is resolved to its Apple
    listing by title to obtain a feed; ``match_candidates`` is how many iTunes
    search results are considered before giving up on a show.
    """

    chart_url: str = "https://podcastcharts.byspotify.com/api/charts/top-podcasts"
    match_candidates: int = 10
    # The iTunes search API throttles with 403 at roughly 20 requests/minute
    # and stays throttled for far longer than it took to trip it, so searches
    # are paced rather than retried out of trouble.
    search_delay_seconds: float = 6.0
    search_attempts: int = 5


@dataclass
class DiscoveryConfig:
    max_episodes_per_podcast: int = 5000  # newest N episodes of each feed are recorded
    max_parallel_feeds: int = 8
    feed_timeout_seconds: int = 60


@dataclass
class DownloadConfig:
    max_workers: int = 8
    timeout_seconds: int = 600
    # Halt before the audio volume fills. A full disk once produced thousands
    # of zero-byte files and a corrupted SQLite session.
    min_free_gb: float = 100.0


@dataclass
class CompressionConfig:
    """Re-encode downloaded audio to mono Opus/OGG.

    Validated with tools/ab_format_test.py: 24 kbps Opus diverges from the
    source MP3 by ~1.3% WER, far below the ASR model's own error rate. Re-run
    that tool before changing ``bitrate``.
    """

    enabled: bool = True
    size_threshold_mb: float = 50.0   # smaller files are kept as-is
    bitrate: str = "24k"
    keep_original: bool = False


@dataclass
class TranscriptionConfig:
    backend: str = "parakeet"        # "parakeet" or "qwen_vllm"
    model_name: str = "nvidia/parakeet-tdt-0.6b-v2"
    gpu_ids: list[int] = field(default_factory=lambda: [0])
    # Audio chunks per forward pass. Attention memory grows with chunk length
    # squared times batch: 300 s chunks peak at ~5 GB with batch 1 and OOM at 2
    # on a 12 GB card shared with other services.
    batch_size: int = 1
    chunk_duration_seconds: int = 300 # long audio is split into chunks of this length...
    overlap_seconds: int = 30         # ...overlapping by this much, then merged on word timestamps
    # When enabled, Silero VAD finds speech on decoded 16 kHz audio and only
    # those absolute-time spans are sent to ASR. Two seconds of silence closes
    # a region so ordinary conversational pauses retain useful ASR context and
    # do not become hundreds of tiny inference requests.
    vad_enabled: bool = False
    vad_threshold: float = 0.5
    vad_min_speech_duration_ms: int = 250
    vad_min_silence_duration_ms: int = 2000
    vad_speech_pad_ms: int = 30
    # Optional output from tools/plan_pyannote_vad.py. The planner runs in an
    # isolated environment because its legacy PyTorch stack conflicts with the
    # ASR environment. Precomputed plans are currently supported by the remote
    # Qwen batch workflow only.
    vad_plan_path: str | None = None
    use_cuda_graphs: bool = True
    # NeMo model instances are not safe to drive concurrently from Python
    # threads on multiple GPUs. Process isolation gives each GPU its own CUDA
    # runtime state and is recommended for multi-GPU batch jobs.
    isolated_gpu_workers: bool = False
    # Batch transcription can decode upcoming episodes concurrently so GPU
    # workers do not sit idle waiting for ffmpeg. Zero keeps the simple
    # per-GPU decode path used by the local/database pipeline.
    decode_workers: int = 0
    decode_prefetch: int = 8
    # Qwen3-ASR is served out of process. More than one URL is supported for
    # independent replicas, while native vLLM data parallel uses one URL.
    vllm_urls: list[str] = field(default_factory=lambda: ["http://127.0.0.1:8100"])
    vllm_request_concurrency: int = 32
    vllm_language: str = "en"
    vllm_timeout_seconds: int = 1800
    # Bounds pathological decoder loops without constraining normal speech.
    # Set per deployment because the safe value depends on chunk duration.
    vllm_max_completion_tokens: int | None = None
    # Some podcast OGGs contain a one-frame Theora cover-art stream. FFmpeg's
    # fast input seeking then seeks against that stream and silently returns
    # audio from time zero for every later chunk. When set, Qwen losslessly
    # remuxes such inputs to an audio-only cache once before chunking them.
    vllm_audio_remux_cache_dir: str | None = None
    # Targeted recovery control for abnormally quiet source media. The gain is
    # applied only while preparing the lossless FLAC request and is recorded in
    # transcript provenance. Keep zero for ordinary production batches.
    vllm_audio_gain_db: float = 0.0


@dataclass
class StorageConfig:
    transcript_compression_level: int = 3   # zstd level for transcript files


@dataclass
class BatchExportConfig:
    # Decimal GB matches transfer-disk and archive-size conventions. The tar is
    # uncompressed because the MP3/Opus payload is already compressed.
    target_size_gb: float = 250.0


@dataclass
class Config:
    data_dir: str = "data"            # relative paths resolve against the project root
    fetcher: FetcherConfig = field(default_factory=FetcherConfig)
    podchaser: PodchaserConfig = field(default_factory=PodchaserConfig)
    spotify: SpotifyConfig = field(default_factory=SpotifyConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    audio_compression: CompressionConfig = field(default_factory=CompressionConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    batch_export: BatchExportConfig = field(default_factory=BatchExportConfig)

    # --- derived paths -----------------------------------------------------

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def audio_dir(self) -> Path:
        return self.data_path / "audio"

    @property
    def transcript_dir(self) -> Path:
        return self.data_path / "transcripts"

    @property
    def db_path(self) -> Path:
        return self.data_path / "podcast_metadata.db"

    @property
    def batch_export_dir(self) -> Path:
        """Small, persistent receipts used to avoid exporting an episode twice."""
        return self.data_path / "audio_batches"

    # --- loading -------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str = DEFAULT_CONFIG_PATH) -> "Config":
        path = Path(path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {path} "
                              f"(copy config.example.json to config.json to start)")
        with open(path) as f:
            try:
                raw = json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigError(f"{path} is not valid JSON: {e}") from e
        config = cls.from_dict(raw)

        # Credentials may come from the environment instead of the file.
        env_id = os.getenv("PODCHASER_CLIENT_ID")
        env_secret = os.getenv("PODCHASER_CLIENT_SECRET")
        if env_id:
            config.podchaser.client_id = env_id
        if env_secret:
            config.podchaser.client_secret = env_secret
        return config

    @classmethod
    def from_dict(cls, raw: dict) -> "Config":
        return _build(cls, raw, where="config")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _build(cls, raw, where: str):
    """Construct dataclass ``cls`` from ``raw``, recursing into nested dataclasses."""
    if not isinstance(raw, dict):
        raise ConfigError(f"{where} must be a JSON object, got {type(raw).__name__}")
    known = {f.name for f in fields(cls)}
    unknown = set(raw) - known
    if unknown:
        raise ConfigError(f"Unknown key(s) in {where}: {sorted(unknown)}. "
                          f"Valid keys: {sorted(known)}")
    # Annotations are strings under ``from __future__ import annotations``;
    # resolve them to find the nested dataclasses.
    types = typing.get_type_hints(cls)
    kwargs = {}
    for name, value in raw.items():
        field_type = types[name]
        if is_dataclass(field_type):
            kwargs[name] = _build(field_type, value, where=f"{where}.{name}")
        else:
            kwargs[name] = value
    return cls(**kwargs)
