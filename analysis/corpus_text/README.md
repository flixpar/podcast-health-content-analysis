# Plain-text transcript corpus and keyword search

`build.py` flattens every transcript (`downloader/data/transcripts/*.jsonl.zst`)
into 64 shards, one segment per line (`episode_id<TAB>segment_index<TAB>text`,
shard = `episode_id % 64`), plus `episodes.tsv` (podcast, date, title) from the
metadata DB. About 145.6k episodes, 8.1 GB; it takes ~20 minutes.

```bash
CORPUS_TEXT_DIR=/mnt/internal/felix/podcast-corpus-text .venv/bin/python analysis/corpus_text/build.py
```

The output lives outside the repo; the NVMe copy (default `CORPUS_TEXT_DIR`) is
`/mnt/internal/felix/podcast-corpus-text`, with an HDD copy at
`/mnt/data2/podcast-data/corpus-text`. Do not write it to the root volume.

`cq.py` searches it with ripgrep (case-insensitive Rust regexes):

```bash
python3 analysis/corpus_text/cq.py count  '\b(ozempic|wegovy)\b'          # segments, episodes, podcasts
python3 analysis/corpus_text/cq.py sample '\bseed oils?\b' -n 12 --ctx 1   # random hits with context
python3 analysis/corpus_text/cq.py sample 'pattern' --podcast 'huberman'  # restrict to shows
python3 analysis/corpus_text/cq.py ctx EPISODE SEGMENT -k 4
python3 analysis/corpus_text/cq.py cooc 'pattern A' 'pattern B'
```

It was built for the v8 corpus review (`taxonomy/v8-corpus-review/`).
