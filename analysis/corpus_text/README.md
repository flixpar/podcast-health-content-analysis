# Plain-text transcript corpus and keyword search

`build.py` reads compressed or plain JSONL transcripts from `downloader/data/transcripts/`
and the read-only metadata database, then writes 64 text shards, a completion manifest and
`episodes.tsv`. Each shard line is `episode_id<TAB>segment_index<TAB>text`;
the shard number is `episode_id % 64`. All generated data defaults to the
ignored repository directory `local/corpus-text/`.

Run from the repository root:

```bash
.venv/bin/python analysis/corpus_text/build.py
.venv/bin/python analysis/corpus_text/cq.py count '\b(ozempic|wegovy)\b'
.venv/bin/python analysis/corpus_text/cq.py sample '\bseed oils?\b' -n 12 --ctx 1
.venv/bin/python analysis/corpus_text/cq.py sample 'pattern' --podcast 'huberman'
.venv/bin/python analysis/corpus_text/cq.py ctx EPISODE SEGMENT -k 4
.venv/bin/python analysis/corpus_text/cq.py cooc 'pattern A' 'pattern B'
```

`cq.py` requires ripgrep. Patterns are matched case-insensitively against
segment text. Set `CORPUS_TEXT_DIR` for both commands to use an external
volume; the existing full-corpus export is about 8 GB:

```bash
export CORPUS_TEXT_DIR=/path/to/corpus-text
.venv/bin/python analysis/corpus_text/build.py
.venv/bin/python analysis/corpus_text/cq.py count 'pattern'
```

Builds require a new destination. All shards are staged together and published
only after every selected transcript succeeds. Missing catalog membership,
corrupt JSON/compression and invalid segment indexes fail loudly; a failed
staging directory is retained for inspection. Existing corpora are never
overwritten. Compressed transcripts take precedence when both formats exist;
summary-only transcripts become one untimed segment with index zero.

Use `build.py --help` to select `--transcripts`, `--metadata-db`, `--out-dir`
and `--workers`. For a small exported study, point at its linked transcript
directory and the corresponding shared catalog. Select the same
`CORPUS_TEXT_DIR` when querying an output built with `--out-dir`.

Every query requires a `corpus-text-v1` manifest with `complete: true`,
all 64 declared shards, and `episodes.tsv`. Failed staging directories,
missing shards and malformed manifests are rejected before any results are
printed. Older exports without a completion manifest must be rebuilt in a
new directory from their source transcripts; retain the original export
while validating the replacement.

Search patterns use syntax supported by both Python regex and ripgrep. They
match segment text only, including when anchored with `^`; anchored queries
scan every segment without the ripgrep prefilter. Missing corpus files,
invalid patterns and ripgrep failures return a nonzero exit code. Hit counts
refer to the selected corpus, without a fixed historical population count.

The tools remain useful for inspecting taxonomy coverage. The completed v8
review's working reports and patches are preserved under `local/`; the
maintained scheme is described in `docs/labeling.md`.
