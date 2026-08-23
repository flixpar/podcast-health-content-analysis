# Podcast Transcription System

A high-performance system for fetching, downloading, and transcribing health podcasts at scale using NVIDIA Parakeet TDT 0.6B V2 model with multi-GPU support. Designed for research applications requiring large-scale podcast analysis.

## Features

- **Dual API Support**: Apple RSS API (no auth required) or Podchaser GraphQL API
- **Smart Transcript Detection**: Skips episodes with existing transcripts in RSS feeds
- **Parallel Downloads**: Multi-threaded audio downloading with retry logic
- **Multi-GPU Transcription**: Automatic load balancing across multiple GPUs
- **Long Audio Handling**: Automatic chunking with overlap for episodes >20 minutes
- **Audio Compression**: Optional re-encode to Opus/OGG above a size threshold (via ffmpeg)
- **Compressed Storage**: JSONL + zstd compression (~97% compression ratio)
- **Phased Execution**: Run metadata fetch, download, and transcription independently
- **Resume Support**: Continue interrupted operations from last checkpoint
- **Publisher Transcript Ingestion**: Fetch transcripts feeds already provide (SRT/VTT/JSON/HTML), normalized into the same storage format as ASR output
- **Integrity Auditing**: Reconcile the database against what is actually on disk
- **Disk Guard**: Downloads and conversions halt cleanly before filling the volume
- **SQLite Database**: Complete metadata and status tracking

## Requirements

- Python 3.8+
- NVIDIA GPUs
- CUDA 11.8+
- 32GB+ RAM recommended
- 500GB+ storage for audio files

## Installation

1. Clone the repository
2. Ensure you have [uv](https://github.com/astral-sh/uv) package manager installed
3. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

4. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

5. Configure your API settings in `config.json`:
   - **For Apple RSS API** (recommended, no auth needed): Set `"fetcher.type": "apple"`
   - **For Podchaser API**: Set `"fetcher.type": "podchaser"` and add your API credentials

Note: Audio re-encoding requires the **ffmpeg** binary on your `PATH` (e.g. `apt install ffmpeg`). The `ffmpeg-python` entry in `requirements.txt` is not sufficient — the pipeline shells out to the `ffmpeg` CLI directly.

## Usage

### Full Pipeline
```bash
python main.py --phase all --limit 100 --max-episodes 5
```

### Individual Phases

#### Phase 1: Fetch Podcast Metadata
```bash
python main.py --phase 1 --limit 100
```

#### Phase 2: Parse RSS and Download Audio
```bash
python main.py --phase 2 --max-episodes 5
```

#### Phase 2 (discover only): Catalogue New Episodes Without Downloading
```bash
python main.py --phase 2 --discover-only
```

Reads every feed and records new episode metadata, downloading nothing. Feed
parsing takes minutes; downloading takes days. Splitting them means you can see
the full backlog immediately and then work through it with resume support.

#### Phase 2b: Download Episodes Already in the Database
```bash
python main.py --phase 2b                  # everything still pending
python main.py --phase 2b --pending-limit 500
python main.py --phase 2b --skip-errors    # don't retry past failures
```

This is the resumable download path. It works off `episodes.status`, so an
interrupted run continues exactly where it stopped without re-parsing feeds.
Prefer it over re-running Phase 2 to finish a partial download.

#### Phase 3: Transcribe Audio
```bash
python main.py --phase 3
```

### View Statistics
```bash
python main.py --stats
```

### Recommended Refresh Cycle

```bash
python main.py --phase 1 --limit 100          # refresh the podcast list
python main.py --phase 2 --discover-only      # catalogue new episodes
python tools/fetch_rss_transcripts.py         # take publisher transcripts for free
python main.py --phase 2b                     # download the audio that's left
python tools/audit_audio.py --fix             # reconcile DB against disk
```

Fetching publisher transcripts before downloading matters: episodes whose feed
carries a transcript never need their audio fetched or transcribed at all.

## Configuration

Edit `config.json` to customize:

- **Fetcher settings**:
  - `fetcher.type`: `"apple"` (no auth) or `"podchaser"` (requires credentials)

- **Download settings**:
  - `max_workers`: Parallel download threads (default: 4)
  - `max_episodes_per_podcast`: Episode limit per podcast (default: 5)
  - `timeout`: Download timeout in seconds (default: 300)
  - `min_free_gb`: Stop downloading when the audio volume drops below this much
    free space (default: 50). A full disk previously produced thousands of
    zero-byte files; the pipeline now halts instead.

- **GPU configuration**:
  - `num_gpus`: Number of GPUs to use
  - `gpu_ids`: Array of GPU device IDs (e.g., `[0, 1, 2, 3]`)
  - `batch_size`: Batch size for transcription (default: 4)

- **Transcription parameters**:
  - `chunk_duration_seconds`: Max chunk length for long audio (default: 300s)
  - `overlap_seconds`: Overlap between chunks (default: 30s)
  - `model_name`: NeMo model (default: `"nvidia/parakeet-tdt-0.6b-v2"`)

- **Audio compression** (`audio_compression`):
  - `enabled`: Re-encode downloaded audio to Opus/OGG (default: true)
  - `size_threshold_mb`: Only re-encode files larger than this (default: 50)
  - `format`/`container`: Codec and container (default: `opus`/`ogg`)
  - `bitrate`: Target audio bitrate (default: `24k`)
  - `keep_original`: Keep the original MP3 after re-encoding (default: false)
  - Requires the `ffmpeg` binary on `PATH`.

- **Storage options**:
  - `compression_level`: Zstd compression level 1-22 (default: 3)
  - `keep_processed_audio`: Whether to keep temporary audio files

## Architecture

The system uses a three-phase pipeline architecture:

1. **Phase 1 - Metadata Collection**: Fetches podcast information from Apple RSS or Podchaser API → stores in SQLite
2. **Phase 2 - Discovery and Download**: Parses RSS feeds → detects existing transcripts → downloads audio files (skips if transcript exists). `--discover-only` records metadata without downloading; **Phase 2b** then downloads from the database with resume support.
3. **Phase 3 - Transcription**: Multi-GPU batch processing → automatic chunking for long audio → compressed storage

**Concurrency and durability**: Phase 2 runs one worker per podcast. Each worker
owns a private SQLite connection (WAL mode, 60s busy timeout) and commits once
per episode. Sharing a single connection across workers, and holding one
transaction open for a whole feed, is what caused the `cannot start a
transaction within a transaction` and `bad parameter or other API misuse`
failures in earlier runs.

**Data Flow**:
```
Podcast API → SQLite (podcasts)
     ↓
RSS Feed → SQLite (episodes) → Audio Download (data/audio/)
     ↓
Audio Files → Multi-GPU Transcription → Compressed JSONL (data/transcripts/)
     ↓
SQLite (episodes + transcripts tables)
```

## Database Schema

SQLite database at `data/podcast_metadata.db`:

- **podcasts**: Podcast metadata (id, title, rss_url, status, etc.)
- **episodes**: Episode details (id, podcast_id, audio_file_path, transcript_file_path, status, error_message)
- **transcripts**: Transcript metadata (episode_id, word_count, confidence_score, duration_seconds)
- **processing_logs**: Historical processing events

**Key Relationships**:
- `episodes.podcast_id` → `podcasts.id` (many-to-one)
- `transcripts.episode_id` → `episodes.id` (one-to-one)

**Episode Status Values**: `pending`, `downloaded`, `transcribed`, `error`

Transcripts carry a `metadata.source` field of either `rss` (fetched from the
publisher's feed) or the ASR model name, so the two provenances stay
distinguishable downstream.

## Database Inspection

```bash
# View overall statistics
python main.py --stats

# Check episode status distribution
sqlite3 data/podcast_metadata.db "SELECT status, COUNT(*) FROM episodes GROUP BY status;"

# View errors
sqlite3 data/podcast_metadata.db "SELECT title, error_message FROM episodes WHERE status='error';"

# See breakdown by podcast
sqlite3 data/podcast_metadata.db "SELECT p.title, COUNT(e.id) as episodes, SUM(CASE WHEN e.status='transcribed' THEN 1 ELSE 0 END) as transcribed FROM podcasts p LEFT JOIN episodes e ON p.id = e.podcast_id GROUP BY p.id;"

# Check storage usage
du -sh data/audio data/transcripts
```

## Tools

Maintenance utilities live in `tools/`. All are safe to re-run.

### `tools/audit_audio.py` — reconcile the database against disk

```bash
python tools/audit_audio.py                              # full audit (ffprobes every file)
python tools/audit_audio.py --skip-probe                 # existence and size only, fast
python tools/audit_audio.py --newer-than '2025-10-14 03:00'   # probe a suspect window
python tools/audit_audio.py --fix                        # re-queue what it found
```

Reports `missing`, `empty`, `unreadable`, `truncated` (decoded duration far
short of the RSS-declared duration), `shared_path` (several episode rows
pointing at one file), and `orphan` (audio on disk no row references). `--fix`
resets the broken rows to `pending`; it never touches an episode that already
has a transcript. Findings are written to `tools/audit_report.json`.

### `tools/fetch_rss_transcripts.py` — take the transcripts publishers already offer

```bash
python tools/fetch_rss_transcripts.py --limit 50   # try a batch first
python tools/fetch_rss_transcripts.py
```

Parses SRT, WebVTT, Podcast 2.0 JSON, timestamped plain text, and HTML
transcript pages into the pipeline's JSONL+zstd format. Costs no GPU time, and
publisher transcripts usually carry speaker labels that ASR does not.

### `tools/ab_format_test.py` — is Opus re-encoding safe for ASR?

```bash
python tools/ab_format_test.py --num-episodes 20
```

Transcribes the same audio from both the original MP3 and its Opus/OGG
re-encode and reports the WER/CER between them. There is no ground truth here;
divergence between the two is the measure. Run this before committing to a
re-encode policy — see *Storage Policy* below for the current result.

### `convert_existing_audio.py` — re-encode the existing archive

```bash
python convert_existing_audio.py --dry-run
python convert_existing_audio.py --reconcile-only   # record work an interrupted run already did
python convert_existing_audio.py
```

Each file is converted, verified with ffprobe against the source duration,
committed to the database, and only then is the original deleted — in that
order, so an interruption can never leave a deleted original with no record of
its replacement. `--reconcile-only` re-encodes nothing; it just records
conversions that already exist on disk and removes their originals.

## Troubleshooting

### Recovering from a Full Disk

A full volume previously produced thousands of zero-byte `.ogg` files and a
cascade of SQLite errors. The pipeline now halts with `DiskSpaceError` before
that happens, but to clean up after an older run:

```bash
# 1. Remove failed conversions (zero-byte files ffmpeg created before failing)
find data/audio -name '*.ogg' -size 0 -delete

# 2. Record conversions that completed but were never written to the database
python convert_existing_audio.py --reconcile-only

# 3. Re-queue rows whose files are missing, truncated, or shared with another episode
python tools/audit_audio.py --fix

# 4. Resume downloading
python main.py --phase 2b
```

### Audio Preprocessing Issues

Temporary audio files are stored in `/tmp/processed_audio/` as 16kHz mono WAV. If transcription fails, these may accumulate:

```bash
# Clean up temporary files
rm -rf /tmp/processed_audio/*
rm -f /tmp/chunk_*.wav
```

### Missing Episodes for a Podcast

If a podcast shows 0 transcribed episodes, check:

1. RSS feed parsing: Check logs for parsing errors
2. Download status: `SELECT * FROM episodes WHERE podcast_id=X;`
3. Audio file existence: `ls -la data/audio/{podcast_name}/`

## Storage Policy

Audio is archived as **24 kbps mono Opus in an OGG container**, not MP3.

That choice was validated before committing to it, with `tools/ab_format_test.py`:
the same 80 windows of audio (20 episodes across 20 podcasts, 2 hours per format)
were transcribed from the original MP3 and from its Opus re-encode, and the two
transcripts compared.

| Measure | Result |
|---|---|
| Aggregate WER (Opus vs MP3) | **1.26%** |
| Aggregate CER | **0.85%** |
| Median / max per-episode WER | 1.16% / 3.34% |
| Size reduction | **82.7%** (1698 MB -> 293 MB) |

For reference, Parakeet TDT 0.6B's own WER on clean benchmarks is around 6%, so
format-induced divergence sits well below the model's own error floor. Re-encoding
is treated as ASR-transparent.

Two cautions learned while measuring this:

- **Do not compare windows obtained by seeking.** `librosa`'s `offset=` falls back
  to audioread for MP3 and lands several seconds away from where the same
  timestamp lands in Opus. An early version of this test reported 24% WER purely
  from that misalignment. `ab_format_test.py` now decodes each file in full and
  slices identical sample ranges, then cross-correlates every window pair and
  refuses to score anything with a non-zero lag.
- **Verify a conversion before deleting its original.** 35 of the `.ogg` files
  left by the interrupted 2025-10-14 run had been encoded while their `.mp3` was
  still downloading, so they held as little as 2% of the episode. Both
  `convert_existing_audio.py` and the inline re-encode now compare the encoded
  duration against the source and refuse to delete the original unless they agree.

## Performance and Storage

**Typical Performance** (single GPU):
- Download: ~5-10 episodes/minute (network dependent)
- Transcription: Real-time factor (RTF) varies by audio length
- Compression ratio: ~97% (1.08MB for 43 transcripts, 525K words)

**Storage Breakdown**:
- Audio files: ~60MB per hour of audio as MP3, ~11MB per hour as 24kbps Opus
- Compressed transcripts: ~25KB per episode average
- Database: <1MB per 1000 episodes

**Multi-GPU Scaling**:
- Batches distributed by total audio duration for load balancing
- Configure in `config.json`: `num_gpus` and `gpu_ids`

## Additional Components

- **API Server** (`api_server.py`): RESTful API with Flask, rate limiting, JWT auth
- **Monitoring Dashboard** (`monitoring_dashboard.py`): Real-time GPU metrics and pipeline progress
- **Test Suite** (`test_suite.py`): Run with `python test_suite.py`

## Notes

- Podchaser API: Check your plan limits
- Be respectful of podcast hosting servers
- Transcripts use JSONL format: metadata line → summary → segments with timestamps
- The system automatically skips episodes that already have transcripts in their RSS feeds
