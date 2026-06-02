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

#### Phase 2: Download Audio Files
```bash
python main.py --phase 2 --max-episodes 5
```

#### Phase 3: Transcribe Audio
```bash
python main.py --phase 3
```

### View Statistics
```bash
python main.py --stats
```

## Configuration

Edit `config.json` to customize:

- **Fetcher settings**:
  - `fetcher.type`: `"apple"` (no auth) or `"podchaser"` (requires credentials)

- **Download settings**:
  - `max_workers`: Parallel download threads (default: 4)
  - `max_episodes_per_podcast`: Episode limit per podcast (default: 5)
  - `timeout`: Download timeout in seconds (default: 300)

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
2. **Phase 2 - Download**: Parses RSS feeds → detects existing transcripts → downloads audio files (skips if transcript exists)
3. **Phase 3 - Transcription**: Multi-GPU batch processing → automatic chunking for long audio → compressed storage

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

## Troubleshooting

### Known Issue: Long Audio Transcription Error

**Symptom**: `TypeError: sequence item 0: expected str instance, Hypothesis found`

**Cause**: NeMo model returns Hypothesis objects for long audio chunks despite `return_hypotheses=False`

**Affected**: Episodes longer than `chunk_duration_seconds` (default 300s/5min)

**Fix**: Already patched in latest commit (a38b447), but failed episodes remain in database.

**To retry failed episodes**:
```bash
# Reset error status to downloaded
sqlite3 data/podcast_metadata.db "UPDATE episodes SET status='downloaded' WHERE status='error';"

# Re-run transcription
python main.py --phase 3
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

## Performance and Storage

**Typical Performance** (single GPU):
- Download: ~5-10 episodes/minute (network dependent)
- Transcription: Real-time factor (RTF) varies by audio length
- Compression ratio: ~97% (1.08MB for 43 transcripts, 525K words)

**Storage Breakdown**:
- Audio files: ~60MB per hour of audio (MP3 format)
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
