import csv
import hashlib
import json
import sqlite3
from pathlib import Path

import pyarrow.parquet as pq
import pytest
import zstandard

from analysis import lexical_scan as scan
from analysis.benchmark import items
from analysis.benchmark.lexicon import Matcher

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def lexicon(tmp_path):
    value = {
        "topics": {"sleep": {"terms": ["sleep", "magnesium"]}},
        "frames": {}, "evidence": {}, "products": {}, "certainty": {},
        "narratives": {"sleep_claim": {"terms": [r"magnesium.{0,40}sleep"]}},
        "commercial": {"terms": ["promo code"]},
        "distrust": {"terms": ["big pharma"]},
        "correction": {"terms": ["debunking"]},
    }
    path = tmp_path / "lexicon.json"
    path.write_text(json.dumps(value))
    return path


def transcript(path, segments):
    records = [{"type": "metadata", "source": "rss"}]
    records += [{"type": "segment", "text": text, "start": i * 10, "end": (i + 1) * 10}
                for i, text in enumerate(segments)]
    content = ("\n".join(json.dumps(record) for record in records) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(zstandard.ZstdCompressor().compress(content) if path.suffix == ".zst" else content)
    return path


def rows(directory, name):
    return pq.read_table(directory / f"{name}.parquet").to_pylist()


def test_term_counts_sentence_positions_and_plain_compressed_agree(tmp_path, lexicon):
    segments = ["Speaker 1: Magnesium helps sleep, sleep. Nothing relevant here.",
                "Host: Use the promo code. Magnesium aids sleep."]
    matcher = Matcher.from_path(lexicon)
    plain = transcript(tmp_path / "episode_1.jsonl", segments)
    compressed = transcript(tmp_path / "episode_1.jsonl.zst", segments)
    result = scan.scan_transcript(1, compressed, matcher)
    assert result == scan.scan_transcript(1, plain, matcher)
    assert result["episodes"] == [(1, "rss", 2, 4, 14, 20.0, 2)]
    counts = {(s, label, term): count for _, s, label, term, count in result["counts"]}
    assert counts[("topics", "sleep", "sleep")] == 2  # repeated word counts once in a sentence
    assert counts[("topics", "sleep", "magnesium")] == 2
    assert counts[("narratives", "sleep_claim", r"magnesium.{0,40}sleep")] == 2
    assert [row[3] for row in result["sentences"]] == [0, 2, 3]
    assert [row[1] for row in result["sentences"]] == [0, 1, 1]
    assert [row[2] for row in result["sentences"]] == [0, 10, 10]
    assert result["sentences"][0][4:6] == ("Speaker 1", "narratives:sleep_claim|topics:sleep")


def test_long_sentence_is_matched_before_display_truncation(tmp_path, lexicon):
    path = transcript(tmp_path / "episode_1.jsonl.zst", ["word " * 150 + "magnesium improves sleep"])
    result = scan.scan_transcript(1, path, Matcher.from_path(lexicon))
    assert len(result["sentences"][0][-1]) == 600
    assert "topics:sleep" in result["sentences"][0][-2]
    assert result["episodes"][0][4] == 153


def test_summary_only_transcript_matches_labeler_fallback(tmp_path, lexicon):
    path = tmp_path / "episode_1.jsonl"
    path.write_text(json.dumps({"type": "summary", "text": "Sleep helps."}) + "\n")
    matcher = Matcher.from_path(lexicon)
    result = scan.scan_transcript(1, path, matcher)
    assert result["episodes"][0][2:6] == (1, 1, 2, 0.0)
    assert result["sentences"][0][2] is None
    with path.open("a") as handle:
        handle.write(json.dumps({"type": "segment", "text": "The game ended."}) + "\n")
    result = scan.scan_transcript(1, path, matcher)
    assert result["episodes"][0][2:5] == (1, 1, 3)
    assert result["sentences"] == []  # summary is not counted alongside real segments


def test_parallel_and_serial_scans_have_identical_tables(tmp_path, lexicon):
    jobs = [(i, transcript(tmp_path / f"episode_{i}.jsonl.zst", ["Magnesium improves sleep."]))
            for i in range(1, 12)]
    for workers in (1, 2):
        output = tmp_path / f"scan-{workers}"
        manifest = scan.run_scan(jobs, lexicon, output, workers=workers, provenance={"kind": "catalog"})
        assert manifest["complete"] and manifest["rows"]["episodes"] == 11
        assert manifest["lexicon_sha256"] == hashlib.sha256(lexicon.read_bytes()).hexdigest()
        assert json.loads((output / "errors.json").read_text()) == []
    for name in scan.SCHEMAS:
        canonical = lambda directory: sorted(rows(directory, name), key=lambda row: json.dumps(row, sort_keys=True))
        assert canonical(tmp_path / "scan-1") == canonical(tmp_path / "scan-2")


def test_no_hit_scan_retains_denominators_and_typed_empty_tables(tmp_path, lexicon):
    path = transcript(tmp_path / "episode_2.jsonl", ["The game ended yesterday."])
    output = tmp_path / "scan"
    scan.run_scan([(2, path)], lexicon, output, workers=1, provenance={})
    for name in ("counts", "sentences"):
        table = pq.read_table(output / f"{name}.parquet")
        assert table.num_rows == 0 and table.schema == scan.SCHEMAS[name]
    stats, labels = items._episode_stats(output)
    assert stats.loc[2, "n_sent"] == 1 and stats.loc[2, "health_density"] == 0
    assert labels.empty


def test_catalog_relocation_and_database_remains_unchanged(tmp_path):
    database = tmp_path / "catalog ?#.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE transcripts (episode_id INTEGER, file_path TEXT)")
        connection.executemany("INSERT INTO transcripts VALUES (?, ?)",
                               [(2, "transcripts/episode_2.jsonl.zst"), (1, "/old/machine/episode_1.jsonl")])
    directory = tmp_path / "relocated"
    transcript(directory / "episode_1.jsonl", ["Hello."])
    transcript(directory / "episode_2.jsonl.zst", ["Hello."])
    before = database.read_bytes()
    assert scan.catalog_jobs(database, directory) == [
        (1, directory / "episode_1.jsonl"), (2, directory / "episode_2.jsonl.zst")]
    assert database.read_bytes() == before
    with pytest.raises(sqlite3.OperationalError):
        scan.catalog_jobs(tmp_path / "missing.db", directory)
    assert not (tmp_path / "missing.db").exists()


@pytest.mark.parametrize("broken", ["missing", "json", "zstd"])
def test_failed_input_never_publishes_partial_scan(tmp_path, lexicon, broken):
    good = transcript(tmp_path / "episode_1.jsonl", ["Sleep helps."])
    bad = tmp_path / ("episode_2.jsonl.zst" if broken == "zstd" else "episode_2.jsonl")
    if broken != "missing":
        bad.write_bytes(b"not a transcript")
    output = tmp_path / "scan"
    with pytest.raises(scan.ScanError, match="1 transcripts failed"):
        scan.run_scan([(1, good), (2, bad)], lexicon, output, workers=1, provenance={})
    assert not output.exists()
    staging, = tmp_path.glob(".scan-*")
    assert json.loads((staging / "manifest.json").read_text())["complete"] is False
    assert json.loads((staging / "errors.json").read_text())[0]["episode_id"] == 2


def test_existing_output_is_never_replaced(tmp_path, lexicon):
    output = tmp_path / "scan"
    output.mkdir()
    sentinel = output / "manifest.json"
    sentinel.write_text("existing output")
    with pytest.raises(scan.ScanError, match="already exists"):
        scan.run_scan([(1, tmp_path / "missing")], lexicon, output, workers=1, provenance={})
    assert sentinel.read_text() == "existing output"
    assert not list(tmp_path.glob(".scan-*"))


def write_study(path, entries):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["study", "revision", "episode_id", "transcript_path"])
        writer.writeheader()
        writer.writerows(entries)
    return path


def test_study_export_selection_pins_revision_skips_uncollected_and_deduplicates(tmp_path, lexicon):
    path = transcript(tmp_path / "episode_1.jsonl.zst", ["Sleep helps."])
    entry = {"study": "corpus-2025", "revision": 3, "episode_id": 1, "transcript_path": str(path)}
    manifest = write_study(tmp_path / "episodes.csv", [entry, entry, {**entry, "episode_id": 2, "transcript_path": ""}])
    jobs, provenance = scan.study_jobs(manifest)
    assert jobs == [(1, path)]
    assert provenance["study"] == "corpus-2025" and provenance["revision"] == 3
    assert provenance["selected_episodes"] == 2 and provenance["without_transcript"] == 1
    assert provenance["manifest_sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    output = tmp_path / "scan"
    scan.run_scan(jobs, lexicon, output, workers=1, provenance=provenance)
    assert [row["episode_id"] for row in rows(output, "episodes")] == [1]


@pytest.mark.parametrize("change, message", [
    ({"revision": 4, "episode_id": 2}, "exactly one study and revision"),
    ({"study": "other", "episode_id": 2}, "exactly one study and revision"),
    ({"transcript_path": "/other/path"}, "conflicting paths"),
    ({"transcript_path": "relative/path", "episode_id": 2}, "must be absolute"),
])
def test_invalid_study_export_rejected(tmp_path, change, message):
    entry = {"study": "s", "revision": 1, "episode_id": 1, "transcript_path": "/absolute/path"}
    manifest = write_study(tmp_path / "episodes.csv", [entry, {**entry, **change}])
    with pytest.raises(scan.ScanError, match=message):
        scan.study_jobs(manifest)


def test_scanner_to_real_pool_builder_with_current_config(tmp_path, lexicon):
    directory = tmp_path / "transcripts"
    transcript(directory / "episode_1.jsonl.zst", [
        f"Magnesium improves sleep and we discuss the topic number {i} today." for i in range(60)])
    transcript(directory / "episode_2.jsonl", [
        f"The game ended yesterday and we discuss the match number {i} today." for i in range(60)])
    database = tmp_path / "db.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE podcasts (id INTEGER, title TEXT, publisher TEXT, categories TEXT);
            CREATE TABLE episodes (id INTEGER, podcast_id INTEGER, title TEXT, published_date TEXT, duration_seconds REAL);
            CREATE TABLE transcripts (episode_id INTEGER, file_path TEXT, metadata TEXT);
            INSERT INTO podcasts VALUES (1, 'Health', 'p', '["Health & Fitness"]'), (2, 'Sports', 'p', '["Sports"]');
            INSERT INTO episodes VALUES (1, 1, 'Health episode', '2026-09-01', 600), (2, 2, 'Sport episode', '2026-09-01', 600);
            INSERT INTO transcripts VALUES (1, 'transcripts/episode_1.jsonl.zst', '{}'), (2, 'transcripts/episode_2.jsonl', '{}');
        """)
    config = items.load_config(ROOT / "benchmark/config.toml")
    output = tmp_path / "scan"
    scan.run_scan(scan.catalog_jobs(database, directory), lexicon, output, workers=1, provenance={})
    config["paths"].update(metadata_db=str(database), transcripts=str(directory), scan_dir=str(output), lexicon=str(lexicon))
    config["quotas"] = {stratum: int(stratum in ("health_dense", "null")) for stratum in items.STRATA}
    config["pool"]["oversample"] = 1
    config["strata"]["discourse"]["podcast_ids"] = []
    pool_dir = tmp_path / "pool"
    summary = items.build_pool(config, out_dir=pool_dir)
    pool = [json.loads(line) for line in (pool_dir / "pool.jsonl").read_text().splitlines()]
    assert summary["per_stratum"]["health_dense"]["taken"] == 1
    assert summary["per_stratum"]["null"]["taken"] == 1
    assert {item["episode_id"] for item in pool} == {1, 2}
    assert all(item["provenance"]["transcript_sha256"] for item in pool)


def test_cli_config_overrides_limit_and_error_exit(tmp_path, lexicon, monkeypatch, capsys):
    directory = tmp_path / "transcripts"
    for i in (1, 2):
        transcript(directory / f"episode_{i}.jsonl.zst", ["Sleep helps."])
    database = tmp_path / "db.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE transcripts (episode_id INTEGER)")
        connection.executemany("INSERT INTO transcripts VALUES (?)", [(2,), (1,)])
    config = tmp_path / "config.toml"
    config.write_text("[paths]\n" + "\n".join(f"{k} = {json.dumps(str(v))}" for k, v in {
        "metadata_db": database, "transcripts": directory, "scan_dir": tmp_path / "default", "lexicon": lexicon}.items()))
    # Simulate a v2/v3 [paths] config: taxonomy selection is not the sampling vocabulary.
    with config.open("a") as handle:
        handle.write('\ntopics = "taxonomy/health-v8.md"\ncodebook = "taxonomy/codebook-v8.md"\n')
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "override"
    assert scan.main(["--config", str(config), "--out-dir", str(output), "--workers", "1", "--limit", "1"]) == 0
    assert [row["episode_id"] for row in rows(output, "episodes")] == [1]
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["config_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert manifest["selection"]["limit"] == 1
    assert not (tmp_path / "default").exists()
    assert scan.main(["--config", str(config), "--out-dir", str(output)]) == 1
    assert "already exists" in capsys.readouterr().err


@pytest.mark.parametrize("change", ["edit", "replace", "delete"])
def test_cli_config_snapshot_survives_changes_after_loading(tmp_path, lexicon, monkeypatch, change):
    path = transcript(tmp_path / "episode_1.jsonl", ["Sleep helps."])
    output = tmp_path / "scan"
    config = tmp_path / "config.toml"
    original = ("[paths]\n" + "\n".join(f"{key} = {json.dumps(str(value))}" for key, value in {
        "metadata_db": tmp_path / "catalog.sqlite", "transcripts": tmp_path,
        "scan_dir": output, "lexicon": lexicon,
    }.items())).encode()
    config.write_bytes(original)

    def select_jobs(database, transcripts):
        # Change the file immediately after parsing, before even selecting inputs.
        assert database == tmp_path / "catalog.sqlite" and transcripts == tmp_path
        if change == "edit":
            config.write_text('[paths]\nscan_dir = "different-output"\n')
        elif change == "replace":
            replacement = tmp_path / "replacement.toml"
            replacement.write_text('[paths]\nscan_dir = "different-output"\n')
            replacement.replace(config)
        else:
            config.unlink()
        return [(1, path)]

    monkeypatch.setattr(scan, "catalog_jobs", select_jobs)
    assert scan.main(["--config", str(config), "--workers", "1"]) == 0
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["config"] == str(config)
    assert manifest["config_sha256"] == hashlib.sha256(original).hexdigest()
    assert manifest["complete"] and manifest["rows"]["episodes"] == 1
