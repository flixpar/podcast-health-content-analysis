# Podcast Transcription Pipeline

Fetches the top podcasts, records every episode from their RSS feeds, downloads
the audio (archived as 24 kbps Opus), and transcribes it with NVIDIA Parakeet.
Publisher-provided transcripts are ingested directly when a feed offers them.
Everything is tracked in a SQLite database so each stage can be re-run and
resumed independently.

## Layout

```
downloader/
├── podcast_pipeline/        the package; run with `python -m podcast_pipeline`
│   ├── cli.py               argparse subcommands -> pipeline stages
│   ├── config.py            typed config (one default per setting, unknown keys rejected)
│   ├── db.py                schema + the shared write helpers
│   ├── models.py            PodcastRecord / FeedEpisode / Segment dataclasses
│   ├── http.py, log.py      retrying requests session; logging setup
│   ├── rss.py               feed -> FeedEpisode list
│   ├── sources/             apple.py (overall + genre charts), spotify.py (chart + title match), podchaser.py (GraphQL)
│   ├── audio/               download.py, naming.py, ffmpeg.py (probe/encode/decode), disk.py
│   ├── transcripts/         store.py (JSONL+zstd format), parsers.py (SRT/VTT/JSON/HTML)
│   ├── asr/                 chunking.py (pure), parakeet.py (NeMo model on one GPU)
│   └── pipeline/            one module per command: fetch_podcasts, discover, download,
│                            rss_transcripts, transcribe, convert_audio, audit,
│                            reset_transcripts, export_audio_batch, stats
├── tests/                   pytest suite (no network, no GPU; ffmpeg tests skip if absent)
├── tools/ab_format_test.py  MP3-vs-Opus ASR divergence measurement
├── config.json              local settings (gitignored); config.example.json is the template
├── data -> /mnt/data2/...   audio/, transcripts/, podcast_metadata.db
└── logs/                    pipeline.log, audit_report.json (gitignored)
```

## Setup

Dependencies are managed by `uv` from the repository root (`../pyproject.toml`):

```bash
cd ..            # repository root
uv sync          # creates .venv with torch, NeMo, etc.; add --group dev for pytest
cd downloader
source ../.venv/bin/activate
cp config.example.json config.json     # then edit
```

`ffmpeg`/`ffprobe` must be on `PATH` (`apt install ffmpeg`); the pipeline shells
out to them for every conversion and for ASR decoding.

## Commands

All commands run from `downloader/` as `python -m podcast_pipeline <command>` and
print a JSON summary when done. `--config PATH` and `--log-level` are global.

| Command | What it does |
|---|---|
| `fetch-podcasts [--limit N] [--source apple\|spotify\|podchaser] [--genre ID] [--country CC]` | Record the top podcasts from one chart. Additive: re-running refreshes metadata without changing ids, and records the podcast's rank in `podcast_charts`. |
| `discover [--max-episodes N]` | Read every podcast feed and record its episodes. Downloads nothing. |
| `fetch-rss-transcripts [--limit N]` | Fetch transcripts publishers attach to their feeds (SRT/VTT/JSON/timestamped text/HTML). No GPU. |
| `download [--limit N] [--workers N] [--skip-errors]` | Download audio for every pending episode. Resumable; re-run after an interruption. |
| `transcribe [--limit N] [--retry-errors]` | Transcribe downloaded audio with Parakeet, one worker per configured GPU. |
| `convert-audio [--dry-run] [--reconcile-only] [--threshold MB] [--limit N]` | Re-encode existing MP3s to Opus/OGG, verifying each before deleting the original. |
| `audit [--fix] [--skip-probe] [--newer-than 'YYYY-MM-DD HH:MM']` | Reconcile the database against files on disk; `--fix` re-queues broken rows. |
| `reset-transcripts (--all \| --episode-ids 1,2 \| --podcast-ids 3) [--dry-run]` | Delete ASR transcripts so `transcribe` runs again. Never touches publisher transcripts. |
| `export-audio-batch OUTPUT_DIR [--target-gb GB] [--dry-run]` | Create a checksummed tar of completed audio that has no transcript and has not been exported before. |
| `ingest-audio-batch ARCHIVE WORKSPACE` | On the remote server, checksum, safely extract, and verify every audio member. |
| `transcribe-audio-batch BATCH_DIR [--retry-errors]` | Resumably transcribe a prepared batch without needing the source SQLite database. |
| `export-transcript-batch BATCH_DIR OUTPUT_DIR` | Create a checksummed return tar; refuses an incomplete batch unless explicitly allowed. |
| `import-transcript-batch ARCHIVE [--dry-run]` | Verify returned provenance and transcripts, then idempotently register them in the source dataset. |
| `stats` | Counts by status, transcript totals, storage used. |

Recommended refresh cycle:

```bash
python -m podcast_pipeline fetch-podcasts          # refresh the podcast list
python -m podcast_pipeline discover                # catalogue new episodes
python -m podcast_pipeline fetch-rss-transcripts   # take publisher transcripts for free
python -m podcast_pipeline download                # fetch the audio that's left
python -m podcast_pipeline audit --fix             # reconcile DB against disk
python -m podcast_pipeline transcribe
```

Fetching publisher transcripts before downloading matters: an episode whose
feed carries a transcript never needs its audio fetched or transcribed.

### Transfer batches for transcription

Point the exporter at a mounted transfer disk. Previewing is cheap and writes
nothing:

```bash
python -m podcast_pipeline export-audio-batch /media/$USER/transfer --dry-run
python -m podcast_pipeline export-audio-batch /media/$USER/transfer
```

The default target is 250 decimal GB of audio payload. Override it for a smaller
disk or test run with `--target-gb 50`. The resulting uncompressed tar is only
slightly larger than the selected payload; MP3 and Opus are already compressed,
so gzip/zstd would mostly add time. The command also writes a standard
`<archive>.sha256` sidecar. After copying both files, verify and extract them:

```bash
sha256sum -c audio-batch-*.tar.sha256
tar -xf audio-batch-*.tar
```

Each archive extracts into its own batch directory. `manifest.jsonl` contains a
batch header followed by one record per audio file, including the source
database `episode_id`, podcast/episode metadata, byte size, archive path, and
SHA-256. That manifest is the job list for the transcription computer.

Selection requires all of the following at the snapshot taken by the command:

- episode status is `downloaded`, or `error` with completed audio (a prior
  transcription failure);
- `audio_file_path` points to a regular file of plausible size;
- neither the episode nor `transcripts` table records a transcript; and
- the episode ID is absent from every completed batch manifest.

The exporter is safe while `download` continues: unfinished audio remains a
`.part` file and is not marked downloaded. It never writes SQLite. Completed
receipts are kept under `data/audio_batches/manifests/`, so the next invocation
selects the next backlog rather than duplicating the last batch. Keep this small
directory with the source dataset. `--include-exported` intentionally bypasses
that ledger when a replacement copy is needed.

Only one exporter may run at once. It checks destination free space before
starting, computes each audio checksum while writing, detects source files that
change mid-export, writes through a hidden `.partial` archive, and exposes the
final tar only after a successful close. If the output is on the audio
filesystem, it additionally preserves `download.min_free_gb` for the ongoing
download job.

The complete remote round trip is documented in
[`docs/remote-batch-transcription.md`](docs/remote-batch-transcription.md). In
short: transfer the audio `.tar` and `.tar.sha256`, ingest and transcribe it on
the remote server, export and transfer the transcript `.tar` and sidecar, then
run a source-side import dry-run before the real import. Unlike audio export,
transcript import writes SQLite and must wait until the long-running downloader
is paused.

### Charts

The collection is not a single chart. `fetch-podcasts` reads one chart per run
and the runs accumulate:

```bash
python -m podcast_pipeline fetch-podcasts --limit 100              # Apple US overall
python -m podcast_pipeline fetch-podcasts --genre 1512 --limit 50  # Apple US Health & Fitness
python -m podcast_pipeline fetch-podcasts --source spotify --limit 100
```

Apple's overall chart comes from the Marketing Tools feed, which takes no
genre and never returns more than 100; per-genre charts come from the older
iTunes `toppodcasts` RSS feed, the only public endpoint that filters by genre.

Spotify's chart publishes no RSS URL, so each show is matched to its Apple
listing by title to recover a feed. That search API throttles at roughly 20
requests a minute, hence `spotify.search_delay_seconds`; a show it genuinely
has no listing for is recorded with a NULL `rss_url` and skipped by
`discover`.

Chart membership is recorded per run:

```bash
sqlite3 data/podcast_metadata.db \
  "SELECT chart, COUNT(*) FROM podcast_charts GROUP BY chart;"
```

## Configuration (`config.json`)

| Section | Keys |
|---|---|
| top level | `data_dir` (default `data`, relative to this directory) |
| `fetcher` | `type` (`apple`, `spotify`, or `podchaser`), `filter_health_only`, `default_limit`, `country`, `genre` (Apple genre id) |
| `spotify` | `chart_url`, `match_candidates`, `search_delay_seconds`, `search_attempts` |
| `podchaser` | `client_id`, `client_secret`, `api_url` (or `PODCHASER_CLIENT_ID`/`_SECRET` env vars) |
| `discovery` | `max_episodes_per_podcast`, `max_parallel_feeds`, `feed_timeout_seconds` |
| `download` | `max_workers`, `timeout_seconds`, `min_free_gb` (downloads halt below this much free space) |
| `audio_compression` | `enabled`, `size_threshold_mb`, `bitrate`, `keep_original` |
| `transcription` | `model_name`, `gpu_ids`, `batch_size`, `chunk_duration_seconds`, `overlap_seconds` |
| `storage` | `transcript_compression_level` (zstd) |
| `batch_export` | `target_size_gb` (default 250 decimal GB of audio payload) |

Unknown keys are rejected at startup, so a typo cannot silently fall back to a default.

## Data

**Database** (`data/podcast_metadata.db`, SQLite in WAL mode):

- `podcasts` — status `pending` → `discovered` | `error`; `podchaser_id` holds the
  source id (`apple_<id>`, `spotify_<id>`, or the Podchaser id) and is the upsert key.
- `podcast_charts` — which chart each podcast came from and at what rank. The
  collection is assembled from several charts fetched on different days, so
  this is what lets an analysis select a subset later.
- `episodes` — status `pending` → `downloaded` → `transcribed`, or `error`
  (an error row with `audio_file_path` set failed at transcription, one without
  failed at download). `has_rss_transcript = 1` rows are never downloaded.
- `transcripts` — one row per transcribed episode; `metadata.source` is `asr` or `rss`.

```bash
sqlite3 data/podcast_metadata.db "SELECT status, COUNT(*) FROM episodes GROUP BY status;"
sqlite3 data/podcast_metadata.db "SELECT title, error_message FROM episodes WHERE status='error';"
```

**Audio** is stored as `data/audio/{podcast-slug}/{episode-slug}_{md5(guid)[:8]}.ogg`
(or `.mp3` below the compression threshold). Most of the existing archive predates
the GUID hash and is named by title alone; lookups check both schemes.

**Transcripts** are `data/transcripts/episode_{id}.jsonl.zst`: a metadata line, a
summary line with the full text, then one line per segment with `start`/`end`
seconds (null for untimed publisher transcripts) and `text`. ASR segments are
sentences with word-accurate timestamps.

## Storage policy: Opus, not MP3

Audio is archived as 24 kbps mono Opus. Before adopting that, `tools/ab_format_test.py`
transcribed identical windows of 20 episodes from both the MP3 and its Opus
re-encode and compared the outputs:

| Measure | Result |
|---|---|
| Aggregate WER (Opus vs MP3) | **1.26%** |
| Aggregate CER | **0.85%** |
| Median / max per-episode WER | 1.16% / 3.34% |
| Size reduction | **82.7%** (1698 MB → 293 MB) |

Parakeet's own benchmark WER is around 6%, so format-induced divergence sits well
below the model's error floor. Re-run the tool before changing `bitrate`.

Two rules learned while measuring this are now enforced in code:

- **Never compare windows obtained by seeking.** Seeks are frame-approximate on
  MP3 and sample-accurate on Opus; an early run reported 24% WER from pure
  misalignment. `decode_pcm` always decodes from sample zero, and the tool
  cross-correlates every window pair and refuses to score a misaligned one.
- **Verify a conversion before deleting its original.** An interrupted run once
  encoded files while their MP3 was still downloading. `encode_opus` compares the
  encoded duration against the source and removes any output that falls short.

## Transcription notes

- Long audio is split into `chunk_duration_seconds` chunks overlapping by
  `overlap_seconds`; word timestamps from the model resolve each overlap at its
  midpoint, so nothing is transcribed twice or dropped.
- On the 12 GB GPU this runs on (shared with other services), 300 s chunks fit
  only at `batch_size: 1` (~5 GB peak). That still transcribes an hour of audio
  in about 15 s; the GPU is not the bottleneck.
- Audio is decoded straight to memory with ffmpeg; there is no preprocessing cache.

## Troubleshooting

**Full disk.** `download` and `convert-audio` halt with `DiskSpaceError` before the
volume fills. To clean up after an older run that did not:

```bash
find data/audio -name '*.ogg' -size 0 -delete             # empty files ffmpeg left behind
python -m podcast_pipeline convert-audio --reconcile-only  # record finished conversions
python -m podcast_pipeline audit --fix                     # re-queue missing/truncated rows
python -m podcast_pipeline download                        # resume
```

**A podcast has no episodes.** Check `podcasts.status` (feed errors are marked
`error` and retried on the next `discover`) and `logs/pipeline.log`.

## Tests

```bash
pytest tests            # from downloader/, with the venv active
```

The suite needs no network or GPU; the ffmpeg tests generate their own audio and
skip when ffmpeg is missing. Stages are tested end-to-end against a temporary
data directory with the network and model replaced at the module boundary.
