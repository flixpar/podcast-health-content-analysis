"""Corpus publication and searches must not hide missing or corrupt inputs."""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
import zstandard

from analysis.corpus_text import build, cq

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def corpus_inputs(tmp_path):
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()
    database = tmp_path / "catalog #test.db"
    with sqlite3.connect(database) as con:
        con.executescript(
            "CREATE TABLE podcasts (id INTEGER, title TEXT);"
            "CREATE TABLE episodes (id INTEGER, podcast_id INTEGER, published_date TEXT, title TEXT);"
            "INSERT INTO podcasts VALUES (2, 'Test show');"
            "INSERT INTO episodes VALUES (1, 2, '2026-01-01T00:00:00Z', 'First');"
            "INSERT INTO episodes VALUES (2, 2, '2026-01-02T00:00:00Z', 'Second');"
        )
    return transcripts, database, tmp_path / "new corpus"


def test_build_publishes_compressed_plain_and_summary_transcripts(corpus_inputs):
    transcripts, database, output = corpus_inputs
    (transcripts / "episode_1.jsonl.zst").write_bytes(zstandard.ZstdCompressor().compress(
        b'{"type":"metadata"}\n'
        b'{"type":"segment","index":0,"text":"Sleep  matters.\\nRest well."}\n'
    ))
    # Duplicated plain exports must not double-count the same episode.
    (transcripts / "episode_1.jsonl").write_text('{"type":"segment","text":"Duplicate"}\n')
    (transcripts / "episode_2.jsonl").write_text('{"type":"summary","text":"Untimed  speech."}\n')
    manifest = build.build_corpus(transcripts, database, output, workers=1)
    assert manifest["complete"] and manifest["episodes"] == manifest["segments"] == 2
    assert len(list(output.glob("shard_*.tsv"))) == 64
    assert (output / "shard_01.tsv").read_text() == "1\t0\tSleep matters. Rest well.\n"
    assert (output / "shard_02.tsv").read_text() == "2\t0\tUntimed speech.\n"
    assert "2\t2\tTest show\t2026-01-02\tSecond\n" in (output / "episodes.tsv").read_text()
    assert json.loads((output / "manifest.json").read_text()) == manifest
    before = (output / "shard_01.tsv").read_bytes()
    with pytest.raises(build.CorpusError, match="already exists"):
        build.build_corpus(transcripts, database, output, workers=1)
    assert (output / "shard_01.tsv").read_bytes() == before


@pytest.mark.parametrize("bad", [b'not json\n', b'[]\n', b'{"type":"segment","index":null,"text":"text"}\n'])
def test_corrupt_transcript_leaves_diagnostics_without_publishing(corpus_inputs, bad):
    transcripts, database, output = corpus_inputs
    (transcripts / "episode_1.jsonl").write_bytes(bad)
    with pytest.raises(build.CorpusError):
        build.build_corpus(transcripts, database, output, workers=1)
    assert not output.exists()
    staging = list(output.parent.glob(".new corpus-*"))
    assert len(staging) == 1
    manifest = json.loads((staging[0] / "manifest.json").read_text())
    assert not manifest["complete"] and manifest["error"]


def test_missing_database_is_not_created(corpus_inputs):
    transcripts, _, output = corpus_inputs
    (transcripts / "episode_1.jsonl").write_text('{"type":"summary","text":"text"}\n')
    absent = output.parent / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        build.build_corpus(transcripts, absent, output, workers=1)
    assert not absent.exists() and not output.exists()


def test_missing_catalog_membership_is_not_silently_indexed(corpus_inputs):
    transcripts, database, output = corpus_inputs
    (transcripts / "episode_99.jsonl").write_text('{"type":"summary","text":"text"}\n')
    with pytest.raises(build.CorpusError, match="missing from catalog"):
        build.build_corpus(transcripts, database, output, workers=1)
    assert not output.exists()


def test_empty_selection_does_not_publish_an_empty_corpus(corpus_inputs):
    transcripts, database, output = corpus_inputs
    with pytest.raises(build.CorpusError, match="No episode transcripts"):
        build.build_corpus(transcripts, database, output, workers=1)
    assert not output.exists()


def test_spawn_workers_use_explicit_inputs_and_destination(corpus_inputs):
    transcripts, database, output = corpus_inputs
    (transcripts / "episode_1.jsonl").write_text('{"type":"segment","text":"Worker speech."}\n')
    result = subprocess.run([
        sys.executable, str(ROOT / "analysis/corpus_text/build.py"),
        "--transcripts", str(transcripts), "--metadata-db", str(database),
        "--out-dir", str(output), "--workers", "2",
    ], cwd=output.parent, check=True, capture_output=True, text=True)
    assert result.stdout.strip() == "episodes 1 segments 1"
    assert (output / "shard_01.tsv").read_text() == "1\t0\tWorker speech.\n"


def test_missing_shards_never_searches_the_repository_or_stdin(monkeypatch):
    monkeypatch.setattr(cq, "SHARDS", [])
    monkeypatch.setattr(cq.subprocess, "Popen", lambda *a, **k: pytest.fail("must not run ripgrep without files"))
    with pytest.raises(cq.CorpusQueryError, match="No corpus shards"):
        list(cq.matches("Sleep"))


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
@pytest.mark.parametrize("pattern,expected", [("Sleep", [1]), ("^Sleep", [1]), ("999", [])])
def test_search_matches_text_only_including_anchors(tmp_path, pattern, expected):
    shard = tmp_path / "shard_01.tsv"
    shard.write_text("1\t0\tSleep matters.\n999\t0\tDifferent text.\n")
    assert [row[0] for row in cq.matches(pattern, [str(shard)])] == expected


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_ripgrep_read_failure_cannot_be_reported_as_zero_hits(tmp_path):
    with pytest.raises(cq.CorpusQueryError, match="search failed"):
        list(cq.matches("Sleep", [str(tmp_path / "absent.tsv")]))


def test_invalid_pattern_is_rejected_before_search(tmp_path):
    with pytest.raises(re.error):
        list(cq.matches("[", [str(tmp_path / "shard.tsv")]))


def test_invalid_metadata_is_not_cached_as_an_empty_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(cq, "ROOT", tmp_path)
    monkeypatch.setattr(cq, "_meta", None)
    (tmp_path / "episodes.tsv").write_text("")
    with pytest.raises(cq.CorpusQueryError, match="metadata header"):
        cq.meta()
    assert cq._meta is None


def test_query_cli_missing_corpus_is_actionable(tmp_path):
    env = {**os.environ, "CORPUS_TEXT_DIR": str(tmp_path / "absent")}
    result = subprocess.run([
        sys.executable, str(ROOT / "analysis/corpus_text/cq.py"), "count", "Sleep",
    ], env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "corpus query:" in result.stderr and "README.md" in result.stderr
    assert "Traceback" not in result.stderr
