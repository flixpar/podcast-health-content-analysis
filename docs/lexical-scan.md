# Lexical scan for benchmark sampling

`analysis.lexical_scan` regenerates the whole-corpus scan tables consumed by
`analysis.benchmark pool`. It extracts the reusable scanner from PR #4 and
uses the matcher in `analysis/benchmark/lexicon.py` with the existing
`benchmark/lexicon-v2.json`. The old report, its uncommitted audit inputs and
the hosted-DeepSeek pilot remain historical work on `analysis/fast-lexical-scan`.

The scan is a sampling aid. Hits are keyword matches, not model annotations,
health-content decisions, claim endorsements or prevalence estimates. The
production labeler still processes every selected transcript window without a
lexical gate. A no-hit sentence can contain health content.

## Run

Use the repository's Python 3.13 environment with the `analysis` dependency
group (`pyarrow`, `pandas`, `scipy`) and `zstandard`. From the repository root:

```bash
# Smoke test in a new, ignored directory. Do not use this subset to build a full pool.
.venv/bin/python -m analysis.lexical_scan \
  --config benchmark/config.toml --limit 10 --workers 1 \
  --out-dir local/lexical-scan-smoke

# Regenerate the full sampling tables in a new location.
.venv/bin/python -m analysis.lexical_scan \
  --config benchmark/config.toml --workers 28 \
  --out-dir local/fast-analysis/scan_v2
```

The config's `[paths]` supplies `metadata_db`, `transcripts`, `lexicon` and
`scan_dir`. `--metadata-db`, `--transcripts`, `--lexicon` and `--out-dir` override
them. Relative paths resolve against the repository root, matching the
benchmark CLI. There are no scanner-specific machine paths or environment
variables to maintain. Omitting `--out-dir` uses the config's `scan_dir`, which
must not already exist. The tracked config uses the ignored
`local/fast-analysis/scan_v2`, matching the benchmark pool consumer. The catalog database is opened read-only; the scanner
reads IDs from `transcripts` and locates `episode_<id>.jsonl.zst` (or plain
`.jsonl`) in the configured transcript directory, just as the pool builder
does. Old absolute database file paths are not used.

After checking the scan, point `paths.scan_dir` in your benchmark config at
the new directory and run the pool builder with that same config. For example,
copy `benchmark/config.toml` to `local/benchmark-scan.toml`, update its paths,
then run:

```bash
.venv/bin/python -m analysis.benchmark \
  --config local/benchmark-scan.toml pool --out-dir local/benchmark-pool-new
```

Existing benchmark items, references, gold and candidate runs can be used
without regenerating the scan. Scan generation is needed when rebuilding or
growing the candidate pool.

## Studies and taxonomy versions

`study export` produces an `episodes.csv` pinned to one study revision,
with absolute `transcript_path` values. To scan that exported selection:

```bash
.venv/bin/python -m analysis.lexical_scan \
  --study-manifest /path/to/study/rev3/episodes.csv \
  --out-dir local/lexical-scan-study-rev3
```

This reads the exported membership, not live study tables, and needs no
downloader migration. The CSV must contain `study`, `revision`, `episode_id`
and `transcript_path`. Rows without transcripts are counted in the scan
manifest and skipped; conflicting duplicate episode paths or mixed revisions
are rejected. If building a pool for that study, also set the pool config's
`transcripts` to the directory produced by `study export --link-transcripts`.

The v2/v3 benchmark configs retain the sampling lexicon even though their
reference labels use granular v7/v8 taxonomies. Pass `--config
benchmark/v2/config.toml` or `benchmark/v3/config.toml`, or set `BENCHMARK_DIR`
to select that specification for both the scanner and benchmark commands.
Sampling keys are independent of the taxonomy being scored; no
keyword-to-v8-label mapping is implied.

Tracked benchmark specifications select generated artifacts under
`local/benchmark/` and scan inputs under `local/fast-analysis/scan_v2`.
`BENCHMARK_OUTPUT_DIR` changes benchmark artifacts, while `--out-dir` or
`paths.scan_dir` selects the scanner's output.

[Corpus search](../analysis/corpus_text/README.md) provides interactive keyword
search and context; it does not produce the tables needed by `pool`. The
scanner has no provider, model or serving configuration. TypeSafe and GLM
serving therefore share the same sampling inputs.

## Output contract and failures

Each successful scan directory contains:

| File | Contents |
| --- | --- |
| `episodes.parquet` | One row per successful transcript, including `episode_id`, `source`, segment/sentence/word counts, duration and speaker-prefix count |
| `counts.parquet` | `episode_id`, `section`, `label`, `term`, `n_sent`: each distinct term hit counted once per sentence |
| `sentences.parquet` | Matching sentences with segment and sentence indexes, segment start, speaker, sorted pipe-separated labels and up to 600 characters of text |
| `manifest.json` | Completion status, input config and lexicon hashes, selected-ID/path hash, row counts, worker count and catalog or study provenance |
| `errors.json` | Empty on success; per-episode errors in a failed staging directory |

The Parquet columns retain PR #4's contract. The pool builder reads the first
two tables; empty hit tables still have typed schemas, and transcripts with
zero hits retain their denominator row. Sentence splitting follows the old
scan's punctuation heuristic; word counts use whitespace splitting. Like the
current labeler, summary-only transcripts are treated as one untimed segment;
summary text is ignored when real segments exist. Counts
can exceed sentence totals because terms and labels overlap. Matching semantics,
including the existing rule that regex patterns are evaluated only after a
literal hit, are shared with the pool matcher. Output row order can vary with
worker scheduling; the selection and table contents do not.

All tables are staged beside the requested destination and the directory is
published by rename only after every selected file succeeds. Any unreadable,
corrupt or malformed transcript makes the command exit nonzero and leaves
diagnostics in the printed staging directory. An interruption also leaves
staging files for inspection. Existing scan directories are never replaced.
Choose a new destination to retry; failed scans cannot silently become the
pool's complete input.

The manifest hashes the exact config bytes parsed before selection and scanning,
so subsequent config edits, replacements or deletion do not alter provenance.
It pins configuration and selection, not an immutable copy of the
corpus. Transcript files and a live catalog can change between runs. Preserve
the source corpus or exported study artifacts when exact reproduction matters.
