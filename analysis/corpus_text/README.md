# Plain-text transcript corpus and keyword search

`build.py` reads compressed transcripts from `downloader/data/transcripts/`
and the read-only metadata database, then writes 64 text shards and
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

The tools remain useful for inspecting taxonomy coverage. The completed v8
review's working reports and patches are preserved under `local/`; the
maintained scheme is described in `docs/labeling.md`.
