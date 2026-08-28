# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A podcast transcription pipeline: fetch top podcasts, record episodes from RSS,
download audio (archived as 24 kbps Opus), ingest publisher transcripts where
feeds offer them, and transcribe the rest with NVIDIA Parakeet (NeMo). State
lives in SQLite; transcripts are zstd-compressed JSONL. The output feeds the
misinformation analysis in `../fact-check`.

## Key Instructions

- Use the virtual environment at `../.venv` (managed by `uv` from the repository
  root's `pyproject.toml`). Run commands from this directory.
- This is a research project, so do not be afraid to make breaking changes to
  the code. Don't worry about backwards compatibility -- except for the data:
  the database and archive are large and must keep working.
- The code does not have to be production-ready, so ensure the code fails loudly
  and with a clear error message. Don't try to catch errors or suppress them.
  Per-item failures (one bad feed, one failed download) are recorded on the row
  and the run continues; anything else should propagate.
- Please ask questions if you are unsure about what to do.

## Running

```bash
python -m podcast_pipeline --help
python -m podcast_pipeline stats
python -m podcast_pipeline fetch-podcasts --limit 100              # Apple US overall
python -m podcast_pipeline fetch-podcasts --genre 1512 --limit 50  # Apple US Health & Fitness
python -m podcast_pipeline fetch-podcasts --source spotify --limit 100
python -m podcast_pipeline discover
python -m podcast_pipeline fetch-rss-transcripts
python -m podcast_pipeline download            # resumable; re-run after an interruption
python -m podcast_pipeline transcribe
python -m podcast_pipeline convert-audio --dry-run
python -m podcast_pipeline audit --fix
python -m podcast_pipeline export-audio-batch /path/to/transfer-disk --dry-run
python -m podcast_pipeline ingest-audio-batch /path/to/audio-batch.tar /remote/work
python -m podcast_pipeline transcribe-audio-batch /remote/work/audio-batch-ID
python -m podcast_pipeline export-transcript-batch /remote/work/audio-batch-ID /path/to/return
python -m podcast_pipeline import-transcript-batch /path/to/transcript-batch.tar --dry-run
pytest tests
```

Every command prints a JSON summary and logs to `logs/pipeline.log`.

## Layout

- `podcast_pipeline/cli.py` -- argparse subcommands; dispatches to `pipeline/*.run(config, conn, ...)`.
- `podcast_pipeline/config.py` -- dataclass config. **Every default lives here and
  nowhere else.** `Config.load` rejects unknown keys. `config.example.json` must
  be kept in sync when keys change.
- `podcast_pipeline/db.py` -- schema and the write helpers stages share
  (`upsert_podcast`, `insert_episode`, `record_download`, `record_transcript`, ...).
  Helpers never commit; the caller owns the transaction.
- `podcast_pipeline/models.py` -- `PodcastRecord`, `FeedEpisode`, `Segment`.
- `podcast_pipeline/rss.py`, `sources/` -- network readers that return models.
  One `fetch-podcasts` run reads one chart; the collection is the union of
  several runs, and `podcast_charts` records which chart each podcast came
  from so a subset can be selected later.
- `podcast_pipeline/audio/` -- `download.py` (resume via `.part` files),
  `naming.py` (slug + GUID hash), `ffmpeg.py` (the only module that shells out
  to ffmpeg/ffprobe), `disk.py` (`DiskSpaceError`).
- `podcast_pipeline/transcripts/` -- `store.py` is the single writer/reader of
  the transcript format; `parsers.py` handles publisher formats.
- `podcast_pipeline/asr/` -- `chunking.py` is pure and unit-tested;
  `parakeet.py` imports torch/NeMo and is only imported inside `transcribe`.
- `podcast_pipeline/pipeline/` -- one module per command. Workers (threads) do
  network/GPU/ffmpeg work and return results; **all database writes happen on
  the main thread** as results arrive.
- `pipeline/export_audio_batch.py` -- read-only SQLite snapshot to an
  uncompressed, checksummed transfer tar. Completed receipts under
  `data/audio_batches/manifests` prevent duplicate batches.
- `batches.py`, `pipeline/{ingest_audio_batch,transcribe_audio_batch,
  export_transcript_batch,import_transcript_batch}.py` -- the verified remote
  transcription round trip. The audio manifest is the immutable identity
  contract; the remote machine never receives or constructs the source DB.
- `tests/` -- pytest; fakes are injected at module boundaries (`monkeypatch.setattr(discover, "fetch_feed", ...)`).
- `tools/ab_format_test.py` -- the MP3-vs-Opus measurement behind the storage policy.

## Rules That Exist Because Something Broke

- **Never share a `sqlite3.Connection` between threads.** The stages avoid the
  question entirely: worker threads return results, the main thread writes.
  Sharing one connection produced "cannot start a transaction within a
  transaction" and "API misuse" errors in the 2025-10-14 run.
- **`DiskSpaceError` is fatal on purpose.** `download` and `convert-audio` set a
  stop flag and wind down. A full disk previously produced thousands of
  zero-byte files and a corrupted SQLite session. Do not catch and continue.
- **Never delete an original on the strength of an unverified conversion.**
  `ffmpeg.encode_opus` probes the output and compares its duration to the
  source; `convert-audio` commits the DB row *before* unlinking the MP3, so an
  interruption can only leave a converted file that is still recorded.
- **Never compare audio windows obtained by seeking** (`ffmpeg`/`librosa`
  offsets are frame-approximate on MP3, sample-accurate on Opus). `decode_pcm`
  decodes from sample zero; slice identical sample ranges and cross-correlate.
  A seek-based comparison once reported 24% WER from misalignment alone.
- **Audio naming checks both schemes.** New files are
  `{title-slug}_{md5(guid)[:8]}.{ext}`; most of the archive is `{title-slug}.{ext}`.
  `naming.find_existing_audio` checks both stems and both `.ogg`/`.mp3` before
  declaring an episode missing. Checking only the configured extension would
  re-download the entire MP3 archive.
- **Podcast upserts key on the source id and fall back to the Apple id.** The
  old pipeline wrote `podchaser_id = NULL` and used `INSERT OR REPLACE`, which
  would have orphaned every episode on a re-run. Keep podcast ids stable.
- **Do not run a writing stage while `download` is running.** `download` takes
  days. A concurrent `discover` + `fetch-rss-transcripts` pass held the write
  lock past the old 60 s busy timeout and killed it with "database is locked"
  after an hour. `db.BUSY_TIMEOUT_SECONDS` is now 300 s, which absorbs a burst,
  but the rule stands: queue write stages between download runs, not during one.
  Read-only `stats` is always safe.
- **Batch export is intentionally not database state.** It can run alongside
  `download`; only rows with a finalized audio path are selected. Do not move
  its completed-manifest ledger into SQLite or select `.part` files.
- **Transcript batch import is a writing stage.** Pause `download` before it.
  Never accept a return batch unless it matches the retained source audio
  manifest, per-episode audio hashes, database episode GUID/podcast identity,
  transcript metadata, and both archive/member checksums.
- **A throttled iTunes search is not a podcast without a feed.** The search
  API (used to give Spotify's chart, which carries no RSS URLs, a feed) answers
  403 after ~20 requests a minute and stays throttled for many minutes. The
  first Spotify run burned the quota in under 30 seconds and recorded 41
  charting shows -- The Ezra Klein Show, This American Life -- as feedless.
  Searches are paced by `spotify.search_delay_seconds`; a throttle that
  outlasts the retries raises `SpotifyResolveError` and stops the run.
- **Apple's per-genre charts need the old endpoint.** The Marketing Tools feed
  (`rss.marketingtools.apple.com`) takes no genre and caps at 100. Genre charts
  come from `itunes.apple.com/{cc}/rss/toppodcasts/limit=N/genre=G/json`, whose
  ordering was verified position-for-position against the Health & Fitness
  chart on podcasts.apple.com.
- **Re-run `tools/ab_format_test.py` before changing the Opus bitrate.** Current
  result: 1.26% WER / 0.85% CER divergence vs MP3 for an 82.7% size saving.

## Transcription

- Long audio is chunked (`chunk_duration_seconds`, `overlap_seconds`) and merged
  on word timestamps at each overlap's midpoint (`asr/chunking.py`). The model
  must return word timestamps (`timestamps=True`); it is an error if it does not.
- The GPU is a 12 GB card shared with other services (~6 GB usable). 300 s chunks
  need `batch_size: 1` (5 GB peak; batch 2 OOMs). RTF is ~0.004, so the GPU is
  not the bottleneck.
- NeMo accepts numpy arrays directly; audio is decoded with ffmpeg to memory and
  never cached on disk.
- Optional Silero VAD runs on that same decoded 16 kHz audio and produces
  absolute-time speech spans. Each speech span is chunked independently so
  skipped silence is not reintroduced and transcript timestamps remain on the
  original episode timeline.

## Database

`data/podcast_metadata.db` (`data` is a symlink to the big volume; disk space is
the binding constraint).

- `podcasts.status`: `pending` -> `discovered` | `error` (feed errors are retried next `discover`).
- `podcast_charts`: (podcast_id, chart, rank). Charts recorded so far:
  `apple_us_top_20251013` (the original 100), `apple_us_top`,
  `apple_us_genre_1512` (health), `spotify_us_top`.
- `episodes.status`: `pending` -> `downloaded` -> `transcribed`, or `error`. An
  `error` row *with* `audio_file_path` failed transcription; *without* it, download.
  `has_rss_transcript = 1` rows are never downloaded.
- `transcripts.metadata.source`: `asr` or `rss`.

```bash
sqlite3 data/podcast_metadata.db "SELECT status, COUNT(*) FROM episodes GROUP BY status;"
```
