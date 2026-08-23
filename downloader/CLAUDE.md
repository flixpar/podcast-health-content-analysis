# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a high-performance podcast transcription pipeline designed to fetch, download, and transcribe health podcasts at scale using NVIDIA NeMo ASR models with multi-GPU support. The system stores transcripts in compressed JSONL format (zstd) for efficient storage.

## Key Instructions

- Ensure the Python virtual environment in `.venv/` is activated.
- This is a research project, so do not be afraid to make breaking changes to the code. Don'y worry about backwards compatibility.
- The code does not have to be production-ready, so ensure the code fails loudly and with a clear error message. Don't try to catch errors or suppress them.
- Please ask questions if you are unsure about what to do.

## Setup and Installation

```bash
# Initial setup (requires uv package manager)
./setup.sh

# Activate environment
source .venv/bin/activate
```

## Running the Pipeline

The pipeline operates in three distinct phases that can be run independently or together:

```bash
# Show current statistics
python main.py --stats

# Phase 1: Fetch podcast metadata (using Apple RSS or Podchaser API)
python main.py --phase 1 --limit 100

# Phase 2: Parse RSS feeds and download audio files
python main.py --phase 2 --max-episodes 5

# Phase 2 (discovery only): record new episode metadata, download nothing
python main.py --phase 2 --discover-only

# Phase 2b: download episodes already in the DB (the resumable path)
python main.py --phase 2b

# Phase 3: Transcribe downloaded audio files
python main.py --phase 3

# Run complete pipeline (will prompt before transcription)
python main.py --phase all --limit 100 --max-episodes 5
```

To resume a partial download, use `--phase 2b`, not `--phase 2`. Phase 2
re-parses every feed; Phase 2b works straight off `episodes.status`.

## Maintenance Tools

```bash
python tools/audit_audio.py --fix          # reconcile DB against disk, re-queue broken rows
python tools/fetch_rss_transcripts.py      # ingest transcripts publishers already provide
python tools/ab_format_test.py             # measure MP3 vs Opus transcription divergence
python convert_existing_audio.py --reconcile-only   # record conversions an interrupted run left
```

## Testing

```bash
# Run test suite
python test_suite.py
```

## Configuration

Edit `config.json` to configure:
- **Fetcher type**: `"apple"` (default, no auth) or `"podchaser"` (requires API credentials)
- **Download settings**: parallel workers, episode limits, timeouts
- **GPU configuration**: `num_gpus`, `gpu_ids` array, `batch_size`
- **Transcription parameters**: chunk duration, overlap for long audio files
- **Storage options**: compression level, whether to keep processed audio

## Architecture Overview

### Three-Phase Pipeline Architecture

The system is built around a phased execution model in `main.py`:

1. **Phase 1 (Metadata Collection)**: Fetch top podcasts from either Apple RSS API or Podchaser GraphQL API, store metadata in SQLite
2. **Phase 2 (Download)**: Parse RSS feeds, detect existing transcripts, download audio files (only if no RSS transcript exists)
3. **Phase 3 (Transcription)**: Multi-GPU batch transcription with automatic chunking for long audio

Each phase updates the SQLite database with status tracking, enabling resume capability.

### Concurrency Rules (important)

- **Never share a `sqlite3.Connection` between threads.** Phase 2 runs one
  worker per podcast; each calls `self._thread_conn()` for a connection of its
  own. The database is opened in WAL mode with a 60s busy timeout.
- **Commit per episode, not per feed.** A feed can hold thousands of episodes;
  one long-lived transaction meant a single failure discarded all of it.
- **`DiskSpaceError` is fatal on purpose.** It sets `self._stop_requested`, and
  every worker winds down. Do not catch and continue -- a full disk previously
  produced thousands of zero-byte files and a corrupted SQLite session.

### Storage Format

Audio is archived as 24kbps mono Opus/OGG. This was validated with
`tools/ab_format_test.py` before adopting it: transcribing the same audio from MP3
and from its Opus re-encode diverges by 1.26% WER / 0.85% CER, against an 82.7%
size saving. That is well under Parakeet's own ~6% benchmark WER, so re-encoding
is treated as ASR-transparent. Re-run the tool before changing `bitrate` in
`config.json`.

Two rules follow from how that measurement went wrong the first time:

- Never compare windows obtained by **seeking** into both formats -- librosa's
  `offset=` is frame-approximate on MP3 and sample-accurate on Opus, which made an
  early run report 24% WER from pure misalignment. Decode fully, slice identical
  sample ranges, and cross-correlate to confirm.
- Never delete an original on the strength of an **unverified** conversion. Always
  compare the encoded duration against the source first.

### Audio File Naming

New downloads are named `{normalized-title}_{md5(guid)[:8]}.{ext}`. Most of the
existing archive predates the GUID hash and uses `{normalized-title}.{ext}`, so
`AudioDownloader._find_existing()` checks both schemes and both extensions
before deciding an episode needs downloading. Checking only the configured
output extension would treat the whole existing MP3 archive as missing.

### Database Schema

SQLite database at `data/podcast_metadata.db` with 4 tables:

- **podcasts**: Podcast metadata with status tracking (`pending`, `downloaded`, `error`)
- **episodes**: Episode details, audio paths, transcript paths, status per episode
- **transcripts**: Transcript metadata (word count, confidence, duration, format)
- **processing_logs**: Historical processing events (not heavily used currently)

Key relationships:
- `episodes.podcast_id` → `podcasts.id`
- `transcripts.episode_id` → `episodes.id` (one-to-one)

### Module Responsibilities

**Core Pipeline (`main.py` - 711 lines)**
- Orchestrates all three phases
- Manages SQLite database initialization and schema
- Implements `PodcastPipeline` class with methods: `phase1_fetch_metadata()`, `phase2_download_audio()`, `phase3_transcribe()`
- Handles compressed transcript saving via `_save_transcript()`

**Podcast Fetching**
- `apple_podcast_fetcher.py`: Uses Apple RSS API (free, no auth), filters for health podcasts by keywords/categories
- `podcast_fetcher.py`: Podchaser GraphQL API client (requires auth), supports pagination

**RSS Parsing (`rss_parser.py`)**
- Uses `feedparser` to extract episode metadata
- Detects existing transcripts in RSS feeds (Podcast 2.0 namespace support)
- Extracts audio URLs, durations, publication dates

**Audio Download (`audio_downloader.py`)**
- Parallel download with ThreadPoolExecutor
- Resume support (checks existing files)
- Retry strategy with exponential backoff
- Creates directory structure: `data/audio/{podcast_id}/{episode_id}.mp3`
- Uses `utils.normalize_id()` to create filesystem-safe IDs

**Transcription (`transcriber.py` - 694 lines)**
- **Multi-GPU support**: Distributes batches across GPUs using ThreadPoolExecutor, load-balanced by audio duration
- **Long audio handling**: Automatically chunks audio longer than `chunk_duration_seconds` (default 1200s/20min) with overlap
- **Audio preprocessing**: Converts to 16kHz mono WAV (required by Parakeet) using librosa/pydub
- **Output normalization**: `_normalize_transcription_output()` handles various NeMo return formats (strings, Hypothesis objects, dicts)
- **Known issue**: For long audio chunks, NeMo may return Hypothesis objects even when `return_hypotheses=False`, causing TypeError when joining text
- **Preprocessing cache**: `/tmp/processed_audio/` is keyed by filename stem *plus a hash of the full path*. The stem alone collides between identically titled episodes in different podcasts, and between an episode's `.mp3` and `.ogg`.

**Transcript Storage (`transcript_processor.py`)**
- JSONL format with zstd compression (level 3 by default)
- Structure: metadata line → summary line (full text) → segment lines (with timestamps)
- Each file: `data/transcripts/episode_{id}.jsonl.zst`

**Additional Components**
- `api_server.py`: Flask REST API for transcript access (rate limiting, caching, JWT auth)
- `monitoring_dashboard.py`: Real-time monitoring with GPU metrics, Flask + SocketIO
- `utils.py`: String normalization for filesystem-safe IDs

### Data Flow

```
Podcast API → SQLite (podcasts table)
    ↓
RSS Feed → SQLite (episodes table) → Audio Download
    ↓
Audio Files → Transcription (multi-GPU) → Compressed JSONL
    ↓
SQLite (episodes + transcripts tables)
```

## Debugging

### Audio Preprocessing

Audio files are preprocessed to `/tmp/processed_audio/` as 16kHz mono WAV files. These are temporary and can accumulate if transcription fails. The transcriber uses both librosa and pydub as fallbacks.

### Episode Status Tracking

Episodes have status values: `pending`, `downloaded`, `transcribed`, `error`. To inspect:

```bash
# View status distribution
sqlite3 data/podcast_metadata.db "SELECT status, COUNT(*) FROM episodes GROUP BY status;"

# View errors
sqlite3 data/podcast_metadata.db "SELECT title, error_message FROM episodes WHERE status='error';"
```

## Storage

**Storage locations**:
- Audio: `data/audio/` (organized by podcast subdirectories)
- Transcripts: `data/transcripts/` (flat structure)
- Database: `data/podcast_metadata.db`
- Logs: `podcast_pipeline.log`

## Development Notes

- SQLite connection uses `check_same_thread=False` for multi-threaded access
- The `fetcher.type` config determines which API to use (`"apple"` or `"podchaser"`)
- RSS feeds that already contain transcripts are detected and those episodes are not downloaded/transcribed
- Database uses AUTOINCREMENT for all primary keys and proper foreign key constraints
- Normalized text output in transcriber requires defensive handling due to NeMo's inconsistent return types
