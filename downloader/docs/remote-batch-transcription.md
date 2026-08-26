# Remote batch transcription round trip

This workflow moves only immutable audio and manifest data to the remote GPU
server. The source SQLite database stays on the source machine. Every transfer
has an outer SHA-256, every audio/transcript member has its own SHA-256, and the
return manifest binds each transcript to the exact source batch, episode ID,
episode identity, and audio bytes.

Commands below run from `downloader/`. Global options such as `--config` must
come before the command name.

## 1. Create an audio batch on the source machine

Preview the selection, then write directly to a transfer disk:

```bash
../.venv/bin/python -m podcast_pipeline export-audio-batch /mnt/transfer --dry-run
../.venv/bin/python -m podcast_pipeline export-audio-batch /mnt/transfer
```

Transfer both generated files:

```text
audio-batch-<ID>.tar
audio-batch-<ID>.tar.sha256
```

Do not delete `data/audio_batches/manifests/` on the source machine. It prevents
duplicate outbound work and is the retained identity/provenance receipt needed
to accept returned transcripts.

Audio export is read-only with respect to SQLite and may run while downloads
continue. `.part` downloads are never selected.

## 2. Prepare the remote server

The remote machine needs this repository/environment, `ffmpeg`/`ffprobe`, the
Python dependencies, and a CUDA GPU supported by the configured NeMo/PyTorch
versions. A source database is not needed.

```bash
cd podcast-misinfo
uv sync
cd downloader
```

If `config.json` is absent, remote commands use the built-in defaults. To use
different GPUs or transcription parameters, create a config and pass it as a
global option:

```bash
../.venv/bin/python -m podcast_pipeline --config remote-config.json \
  transcribe-audio-batch /srv/podcast-work/audio-batch-<ID>
```

Keep the model name, chunk duration, overlap, and batch size stable within a
batch. The exact model is recorded in every transcript.

## 3. Ingest and verify the audio batch remotely

Put the tar and checksum sidecar together, then run:

```bash
../.venv/bin/python -m podcast_pipeline ingest-audio-batch \
  /mnt/transfer/audio-batch-<ID>.tar /srv/podcast-work
```

The command performs safe extraction without trusting tar paths or links. In a
single sequential pass it verifies the outer archive SHA-256 and every audio
member's path, size, and SHA-256 against `manifest.jsonl`. It exposes the final
batch directory only after all checks pass:

```text
/srv/podcast-work/audio-batch-<ID>/
├── audio/
├── transcripts/
├── manifest.jsonl
├── README.txt
└── ingest_receipt.json
```

Ingest is idempotent: rerunning it for an already prepared batch checks the
existing manifest/receipt and returns `already_prepared: true`. The `.sha256`
sidecar is required by default. `--skip-archive-checksum` is an explicit escape
hatch for a lost sidecar; member checks still run, but this weakens the outer
transfer-integrity evidence.

After successful ingest, the outbound tar can be removed if remote disk space
is needed. Keep the prepared batch directory until the return archive is safely
created and copied away.

## 4. Transcribe resumably

```bash
../.venv/bin/python -m podcast_pipeline transcribe-audio-batch \
  /srv/podcast-work/audio-batch-<ID>
```

The command uses the configured GPU IDs exactly like the main transcription
pipeline, but reads jobs from the batch manifest rather than SQLite. Each
successful transcript is atomically saved as
`transcripts/episode_<source-db-id>.jsonl.zst`; that file is its durable success
marker. Interrupting the process is safe—rerun the same command and completed
files are validated and skipped.

Per-episode ASR failures are appended to `transcription_failures.jsonl` and are
skipped on an ordinary rerun. After correcting the cause, retry them with:

```bash
../.venv/bin/python -m podcast_pipeline transcribe-audio-batch \
  /srv/podcast-work/audio-batch-<ID> --retry-errors
```

Useful controls:

- `--limit N` processes only the next N currently eligible episodes.
- `--verify-audio-hashes` rehashes all audio before loading the model. Ingest
  already did this once, so it is normally only needed after suspected disk
  corruption.
- A model/GPU worker crash fails loudly and reports how many jobs were not
  attempted. Transcripts completed before the crash remain resumable.

## 5. Export the transcript return batch

Preview completion first:

```bash
../.venv/bin/python -m podcast_pipeline export-transcript-batch \
  /srv/podcast-work/audio-batch-<ID> /mnt/return --dry-run
```

By default, export refuses to claim success while any source episode lacks a
valid transcript. Once complete:

```bash
../.venv/bin/python -m podcast_pipeline export-transcript-batch \
  /srv/podcast-work/audio-batch-<ID> /mnt/return
```

If some episodes cannot be transcribed, `--allow-partial` creates an explicitly
partial return archive. Its manifest records every missing episode ID; it never
silently reports a partial batch as complete.

Transfer both return files back:

```text
transcript-batch-<ID>.tar
transcript-batch-<ID>.tar.sha256
```

Transcript files are already zstd-compressed, so the outer tar is uncompressed.

## 6. Validate and import on the source machine

Transcript import writes the source SQLite database. Pause the long-running
`download` command before proceeding.

First run the full non-mutating validation:

```bash
../.venv/bin/python -m podcast_pipeline import-transcript-batch \
  /mnt/return/transcript-batch-<ID>.tar --dry-run
```

Then import:

```bash
../.venv/bin/python -m podcast_pipeline import-transcript-batch \
  /mnt/return/transcript-batch-<ID>.tar
```

Before writing anything, the importer verifies:

1. outer archive checksum and safe member paths;
2. every transcript's size and SHA-256;
3. the exact retained outbound audio manifest hash;
4. episode membership, podcast ID, GUID, and source-audio SHA-256;
5. compressed transcript readability, episode ID, source batch, ASR model,
   word count, duration, timestamps, and embedded provenance; and
6. absence of a different existing transcript.

Validated files are copied atomically to the canonical transcript store and
registered through the normal database helper. A receipt is written under
`data/audio_batches/imports/`. Import commits per episode, so interruption is
safe: rerunning recognizes exact prior imports and completes the remainder.
It will never overwrite a different local or publisher transcript.

After import, `stats` should show the episodes as transcribed:

```bash
../.venv/bin/python -m podcast_pipeline stats
```

Only after the returned archive has been verified, imported, and backed up as
needed should the corresponding remote batch directory be removed.
