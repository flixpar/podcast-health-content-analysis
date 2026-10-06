# Downloader development guidance

Run from `downloader/` with the repository's `../.venv` interpreter (managed
by root `pyproject.toml`). In a worktree without its own environment, use an
existing repository environment explicitly. Operator commands and setup are
in [README.md](README.md); study definitions and scope are in
[docs/studies.md](../docs/studies.md); the remote batch protocol is in
[docs/remote-batch-transcription.md](docs/remote-batch-transcription.md).

## Project constraints

- This is a research pipeline. Prefer small, clear changes and loud failures;
  compatibility with the large existing database and archive is essential.
- Per-item network/ASR failures are recorded and processing continues. Disk,
  database, configuration and programming errors propagate.
- Tunable defaults belong in `podcast_pipeline/config.py`; keep
  `config.example.json` synchronized. Unknown configuration keys are rejected.
- Keep generated reports, benchmarks, scratch outputs and handoff evidence
  under ignored repository `local/` or the configured data volume.
- Ask when an unresolved choice could compromise data or research validity.

## Source map

- `cli.py` parses commands and dispatches into `pipeline/`, `studies/`,
  `charts/`, and `catalog/`.
- `db.py` owns schema and shared write helpers. Helpers never commit; callers
  own transactions. `models.py` defines podcast, feed-episode and segment data.
- `rss.py` and `sources/` read feeds/charts. `catalog/` resolves chart entities
  and records identity evidence. Apple genre charts use the legacy iTunes
  endpoint; Marketing Tools is the overall chart, capped at 100.
- `studies/base.py` defines `Study`, `Member`, and `Window`; register each
  definition in `studies/__init__.py`. `materialize.py` maintains membership,
  `scope.py` applies filters, and status/export/gaps/quality derive diagnostics.
- `charts/` imports historical charts and captures live raw responses.
  `archive/wayback.py` and `pipeline/discover_archived.py` recover old episodes.
- `paths.py` owns conversion between portable stored paths and archive paths.
- `audio/` owns download, naming, ffmpeg conversion/decode, and disk checks.
  `transcripts/` owns the JSONL/zstd format and publisher transcript parsers.
- `asr/` imports GPU dependencies lazily. `batches.py` and batch stages own
  the verified remote round trip.
- `tools/alternate_sources/` and `tools/tal_archive.py` produce importable
  JSONL with evidence. `tools/audit/` reads the catalog for quality diagnostics.
  Retain `tools/ab_format_test.py` for validating changes to audio bitrate.

## Data and concurrency invariants

- Never share a SQLite connection between threads. Workers return results;
  all catalog writes happen on the main thread.
- Queue writing stages between long `download` runs. The 300-second busy
  timeout absorbs short bursts, not concurrent writing workflows. Batch audio
  export is read-only and may run alongside downloads; transcript import writes.
- Podcast upserts preserve IDs: key on source ID, then Apple ID. Never use
  `INSERT OR REPLACE` to replace a podcast and orphan its episodes. Reuse
  existing current/historical feed owners when resolving new identities.
- Manual entity links override automatic rules, including a NULL decision
  marking an entity unresolvable. Keep their evidence intact.
- Studies select; the catalog owns audio, transcripts and episode state.
  Refresh only rewrites its study membership tables. Bump a study's `version`
  when selection logic changes. Revision changes include members, windows,
  selected episodes and their assignments, even when there are no episodes.
- `discover` and `download` default to the union of studies. `--all` widens to
  the full catalog; `--study` narrows. Refresh after chart, identity or episode
  changes. RSS transcript collection, ASR and batch export default to all
  eligible episodes unless a study is requested.
- File paths stored on episodes/transcripts are relative to `Config.data_path`.
  Writers use `paths.to_stored`, readers use `paths.resolve`, including tools
  and downstream analysis. Keep `migrate-paths` and `path_migration_backup` for
  legacy datasets; never silently remap a personal path in an individual reader.
- `DiskSpaceError` is fatal. Wind down workers and preserve consistent state.
- Verify audio conversion before deleting the original; commit the converted
  path before unlinking. Match both legacy title-only names and GUID-hashed
  names, across archive formats, before declaring audio absent.
- Batch manifests are immutable identity contracts. Retain completed source
  receipts outside SQLite and validate batch/episode identity, audio hashes,
  returned metadata, archive checksums and member checksums before import.
- Pace iTunes searches through shared `catalog/itunes_search.py`; exhausted
  throttling raises instead of recording the show as feedless. Wayback CDX
  requests are sequential; retain successful listings and raw captures.

## Audio and transcription invariants

- Decode from sample zero before selecting windows. Seeking MP3 and Opus
  independently can misalign comparisons. Re-run the format A/B tool before
  changing the 24 kbps Opus policy.
- Choose remux containers from codecs; MP3 plus cover art requires a container
  such as Matroska, rather than Ogg.
- Declared duration is not decoded duration. Count decoded samples for chunk
  preparation and omit empty tails as `NO_AUDIO` instead of making ASR requests.
- Chunk long audio and merge by word timestamps at overlap midpoints. Model
  responses must include word timestamps; missing timestamps are an error.
- Preserve original episode timestamps after VAD. Inline Silero is intended
  for targeted recovery; precomputed pyannote plans belong to a separate GPU
  environment and must pass batch/audio/plan validation before use.
- Explicit Qwen markers and `omitted_audio_spans` record `ASR_FAILURE`,
  `LOW_SIGNAL`, and `NO_AUDIO`. Consumers treat these as gaps in speech.
- Targeted gain applies only to prepared ASR audio, never the archive; record
  preprocessing in transcript provenance. Measure volume after gain and limit
  peaks. Heavy NeMo/torch imports must stay off ordinary CLI startup paths.

## Validation

Use `../.venv/bin/python -m pytest -q tests` for the full downloader suite, or
select the relevant files. Fixtures use temporary catalogs, faked network and
model boundaries, and generated audio; ffmpeg tests skip when unavailable.
Never use the production database or archive as a test fixture. Keep path
migration, import, identity and batch-contract tests when changing shared data
handling.
