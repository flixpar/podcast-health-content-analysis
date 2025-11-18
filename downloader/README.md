# Podcast Transcription System

A high-performance system for fetching, downloading, and transcribing the top 100 health podcasts using NVIDIA Parakeet TDT 0.6B V2 model on multi-GPU setup.

## Features

- **Podchaser API Integration**: Automatically fetches top health podcasts
- **RSS Feed Processing**: Detects existing transcripts in podcast feeds
- **Parallel Downloads**: Efficient multi-threaded audio downloading
- **Multi-GPU Transcription**: Utilizes multiple GPUs for fast transcription
- **Compressed Storage**: JSONL format with zstd compression for efficient storage
- **Phased Execution**: Run metadata collection, download, and transcription separately
- **Resume Support**: Continue interrupted downloads and transcriptions
- **SQLite Database**: Comprehensive metadata tracking
- **Keyword Filtering**: Fuzzy keyword-based tagging and filtering system for misinformation detection

## Requirements

- Python 3.8+
- NVIDIA GPUs
- CUDA 11.8+
- 32GB+ RAM recommended
- 500GB+ storage for audio files

## Installation

1. Clone the repository
2. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Edit `config.json` with your Podchaser API credentials

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

## Keyword Filtering and Tagging

The system includes a powerful keyword filtering tool for detecting and analyzing potential misinformation at scale. It supports fuzzy matching to handle transcription inconsistencies.

### Quick Start

Add keywords and tag episodes:
```bash
python keyword_cli.py add "vaccine" "COVID-19" "misinformation" --category health
```

Search for episodes:
```bash
python keyword_cli.py search "vaccine" "safety" --logic any --format json --output results.json
```

View statistics:
```bash
python keyword_cli.py stats
```

### Key Features

- **Fuzzy Matching**: Handles transcription errors (e.g., "COVID-19" vs "COVID 19")
- **Incremental Processing**: Only processes new episodes or new keywords
- **Category Organization**: Group keywords by topic
- **Flexible Queries**: Find episodes with ANY or ALL keywords
- **Export Options**: JSON, CSV, or table formats
- **Detailed Statistics**: Track keyword usage across your collection

For complete documentation, see [KEYWORD_FILTERING.md](KEYWORD_FILTERING.md)

## Configuration

Edit `config.json` to customize:
- API credentials
- Download settings
- GPU configuration
- Batch sizes
- Storage options

## Database Schema

- **podcasts**: Podcast metadata
- **episodes**: Episode information
- **transcripts**: Transcript metadata
- **processing_logs**: Processing history
- **keyword_tags**: Keyword definitions and categories
- **episode_keywords**: Episode-keyword associations with match statistics

## API Limits

- Podchaser API: Check your plan limits
- Be respectful of podcast hosting servers
