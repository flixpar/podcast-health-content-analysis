"""Build a tiny transcript corpus into a new output directory."""

import multiprocessing
import runpy
import sqlite3
from pathlib import Path

import zstandard


ROOT = Path(__file__).resolve().parents[2]


def test_build_creates_output_before_workers_and_exports_corpus(tmp_path, monkeypatch):
    script = tmp_path / "analysis" / "corpus_text" / "build.py"
    script.parent.mkdir(parents=True)
    script.write_text((ROOT / "analysis" / "corpus_text" / "build.py").read_text())
    transcripts = tmp_path / "downloader" / "data" / "transcripts"
    transcripts.mkdir(parents=True)
    (transcripts / "episode_1.jsonl.zst").write_bytes(
        zstandard.ZstdCompressor().compress(
            b'{"type":"metadata"}\n'
            b'{"type":"segment","index":0,"text":"Sleep  matters.\\nRest well."}\n'
        )
    )
    with sqlite3.connect(transcripts.parent / "podcast_metadata.db") as con:
        con.executescript(
            "CREATE TABLE podcasts (id INTEGER, title TEXT);"
            "CREATE TABLE episodes (id INTEGER, podcast_id INTEGER, published_date TEXT, title TEXT);"
            "INSERT INTO podcasts VALUES (2, 'Test show');"
            "INSERT INTO episodes VALUES (1, 2, '2026-01-01T00:00:00Z', 'Test episode');"
        )
    output = tmp_path / "new" / "corpus"
    monkeypatch.setenv("CORPUS_TEXT_DIR", str(output))

    class SerialPool:
        def __init__(self, processes):
            assert output.is_dir(), "output must exist before workers start"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def imap_unordered(self, worker, shards):
            return map(worker, shards)

    monkeypatch.setattr(multiprocessing, "Pool", SerialPool)
    # Repeat the build to ensure creating the directory is also safe on reruns.
    for _ in range(2):
        runpy.run_path(str(script), run_name="__main__")
        assert len(list(output.glob("shard_*.tsv"))) == 64
        assert (output / "shard_01.tsv").read_text() == "1\t0\tSleep matters. Rest well.\n"
        assert (output / "episodes.tsv").read_text() == (
            "episode_id\tpodcast_id\tpodcast\tdate\tepisode_title\n"
            "1\t2\tTest show\t2026-01-01\tTest episode\n"
        )
