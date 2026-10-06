"""Regenerate the sentence-level lexical sampling tables used by benchmark pool.

Run from the repository root with ``python -m analysis.lexical_scan --help``.
See docs/lexical-scan.md for the output contract and study-manifest support.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from contextlib import ExitStack, closing
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import zstandard

from analysis.benchmark import CONFIG_PATH
from analysis.benchmark.items import load_config, resolve_path, transcript_path
from analysis.benchmark.lexicon import Matcher, SPEAKER_RE

# Preserve the original scan's sentence boundaries, not the labeler's units.
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\[])")
SCHEMAS = {
    "episodes": pa.schema([
        ("episode_id", pa.int64()), ("source", pa.string()), ("n_seg", pa.int32()),
        ("n_sent", pa.int32()), ("n_words", pa.int32()), ("duration", pa.float32()),
        ("speaker_prefixed_segs", pa.int32()),
    ]),
    "counts": pa.schema([
        ("episode_id", pa.int64()), ("section", pa.string()), ("label", pa.string()),
        ("term", pa.string()), ("n_sent", pa.int32()),
    ]),
    "sentences": pa.schema([
        ("episode_id", pa.int64()), ("seg", pa.int32()), ("start", pa.float32()),
        ("sent_idx", pa.int32()), ("speaker", pa.string()), ("labels", pa.string()),
        ("text", pa.string()),
    ]),
}
_MATCHER: Matcher | None = None


class ScanError(RuntimeError):
    pass


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _init_worker(lexicon: dict[str, Any]) -> None:
    global _MATCHER
    _MATCHER = Matcher(lexicon)


def scan_transcript(episode_id: int, path: Path, matcher: Matcher) -> dict[str, list]:
    """Count each distinct (section, label, term) once per sentence.

    Sentence rows deduplicate labels, while counts retain overlapping terms.
    Streaming decompression bounds memory to one episode's matched rows.
    """
    n_words = n_sent = n_seg = speaker_prefixes = 0
    duration = 0.0
    source = ""
    counts: Counter[tuple[str, str, str]] = Counter()
    sentences = []

    def add_segment(record: dict[str, Any]) -> None:
        nonlocal n_words, n_sent, n_seg, speaker_prefixes, duration
        text = record.get("text") or ""
        start = record.get("start")
        if record.get("end") is not None:
            duration = max(duration, float(record["end"]))
        speaker = None
        prefix = SPEAKER_RE.match(text)
        if prefix:
            speaker_prefixes += 1
            speaker = prefix.group(0).strip().rstrip(":").strip()
            text = text[prefix.end():]
        for sentence in SENT_SPLIT.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
            hits = set(matcher.match(sentence))
            counts.update(hits)
            if hits:
                labels = "|".join(sorted({f"{s}:{label}" for s, label, _ in hits}))
                sentences.append((episode_id, n_seg, start, n_sent, speaker, labels, sentence[:600]))
            n_sent += 1
            n_words += len(sentence.split())
        n_seg += 1

    summary_text = ""
    with ExitStack() as stack:
        raw = stack.enter_context(path.open("rb"))
        stream = raw
        if path.suffix == ".zst":
            stream = stack.enter_context(zstandard.ZstdDecompressor().stream_reader(raw))
        handle = stack.enter_context(io.TextIOWrapper(stream, encoding="utf-8"))
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("type") == "metadata":
                source = record.get("source") or ""
                continue
            if record.get("type") == "summary":
                summary_text = record.get("text") or ""
            elif record.get("type") == "segment":
                add_segment(record)
    # The labeler also supports untimed transcripts containing only summary text.
    if not n_seg and summary_text:
        add_segment({"text": summary_text})
    return {
        "episodes": [(episode_id, source, n_seg, n_sent, n_words, duration, speaker_prefixes)],
        "counts": [(episode_id, *key, count) for key, count in sorted(counts.items())],
        "sentences": sentences,
    }


def _scan_job(job: tuple[int, Path]) -> tuple[int, dict | None, str | None]:
    episode_id, path = job
    try:
        assert _MATCHER is not None
        return episode_id, scan_transcript(episode_id, path, _MATCHER), None
    except (OSError, ValueError, TypeError, AttributeError, zstandard.ZstdError) as exc:
        return episode_id, None, f"{type(exc).__name__}: {exc}"


def catalog_jobs(database: Path, transcripts: Path) -> list[tuple[int, Path]]:
    """Read catalog IDs; use the same relocated file layout as benchmark pool."""
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        ids = connection.execute("SELECT episode_id FROM transcripts ORDER BY episode_id").fetchall()
    return [(int(row[0]), transcript_path(transcripts, int(row[0]))) for row in ids]


def study_jobs(manifest: Path) -> tuple[list[tuple[int, Path]], dict[str, Any]]:
    """Consume PR #8's revision-pinned CSV; no study tables or live queries."""
    selected: dict[int, str] = {}
    identities: set[tuple[str, int]] = set()
    manifest_bytes = manifest.read_bytes()
    with io.StringIO(manifest_bytes.decode("utf-8"), newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"study", "revision", "episode_id", "transcript_path"}
        if not required <= set(reader.fieldnames or []):
            raise ScanError(f"{manifest}: required columns: {sorted(required)}")
        for row in reader:
            study, revision, episode_id = row["study"], int(row["revision"]), int(row["episode_id"])
            if not study or revision < 1 or episode_id < 1:
                raise ScanError(f"{manifest}: invalid study, revision or episode ID")
            identities.add((study, revision))
            value = row["transcript_path"]
            if value and not Path(value).is_absolute():
                raise ScanError(f"{manifest}: transcript_path must be absolute (study export contract)")
            if episode_id in selected and selected[episode_id] != value:
                raise ScanError(f"{manifest}: conflicting paths for episode {episode_id}")
            selected[episode_id] = value
    if len(identities) != 1:
        raise ScanError(f"{manifest}: expected exactly one study and revision")
    study, revision = next(iter(identities))
    jobs = [(eid, Path(value)) for eid, value in sorted(selected.items()) if value]
    return jobs, {
        "kind": "study", "study": study, "revision": revision,
        "manifest": str(manifest), "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "selected_episodes": len(selected), "without_transcript": len(selected) - len(jobs),
    }


def run_scan(
    jobs: list[tuple[int, Path]], lexicon: Path, output: Path, *, workers: int,
    provenance: dict[str, Any], config: Path | None = None,
) -> dict[str, Any]:
    """Stage complete tables together; refuse replacement and incomplete scans."""
    output = output.resolve()
    if output.exists():
        raise ScanError(f"{output} already exists; choose a new --out-dir")
    if not jobs:
        raise ScanError("No transcripts selected; no scan was written")
    if workers < 1:
        raise ScanError("workers must be at least 1")
    if len({eid for eid, _ in jobs}) != len(jobs):
        raise ScanError("Duplicate episode IDs in scan selection")
    lexicon_bytes = lexicon.read_bytes()
    lex = json.loads(lexicon_bytes)
    # Validate in the parent before creating workers or output.
    Matcher(lex)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    totals = {name: 0 for name in SCHEMAS}
    buffers: dict[str, list] = {name: [] for name in SCHEMAS}
    errors = []
    started = time.monotonic()
    try:
        with ExitStack() as stack:
            writers = {
                name: stack.enter_context(pq.ParquetWriter(staging / f"{name}.parquet", schema, compression="zstd"))
                for name, schema in SCHEMAS.items()
            }

            def flush() -> None:
                for name, rows in buffers.items():
                    if rows:
                        columns = dict(zip(SCHEMAS[name].names, zip(*rows)))
                        writers[name].write_table(pa.table(columns, schema=SCHEMAS[name]))
                        totals[name] += len(rows)
                        rows.clear()

            if workers == 1:
                _init_worker(lex)
                results = map(_scan_job, jobs)
            else:
                # Arrow can start threads; avoid forking their state into workers.
                pool = stack.enter_context(get_context("spawn").Pool(
                    workers, initializer=_init_worker, initargs=(lex,)
                ))
                results = pool.imap_unordered(_scan_job, jobs, chunksize=8)
            for index, (eid, rows, error) in enumerate(results, 1):
                if error:
                    errors.append({"episode_id": eid, "error": error})
                else:
                    for name in buffers:
                        buffers[name].extend(rows[name])
                if len(buffers["episodes"]) >= 2000 or len(buffers["counts"]) >= 100_000 or len(buffers["sentences"]) >= 100_000:
                    flush()
                if index % 2000 == 0:
                    print(f"{index}/{len(jobs)} transcripts, {time.monotonic() - started:.0f}s", file=sys.stderr)
            flush()
        (staging / "errors.json").write_text(json.dumps(errors, indent=2) + "\n")
        manifest = {
            "schema_version": "lexical-scan-v1", "complete": not errors,
            "selection": provenance, "transcripts_attempted": len(jobs), "failures": len(errors),
            "lexicon": str(lexicon), "lexicon_sha256": hashlib.sha256(lexicon_bytes).hexdigest(),
            "config": str(config) if config else None,
            "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest() if config else None,
            "workers": workers, "rows": totals,
            "selection_sha256": hashlib.sha256(json.dumps(
                [(eid, str(path)) for eid, path in jobs], separators=(",", ":")
            ).encode()).hexdigest(),
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if errors:
            raise ScanError(f"{len(errors)} transcripts failed; diagnostics at {staging}; {output} was not published")
        if output.exists():
            raise ScanError(f"{output} appeared during scanning; refusing to replace it")
        staging.rename(output)
        return manifest
    except BaseException:
        # Keep the failed staging directory for diagnostics; never publish partial tables.
        print(f"Incomplete scan retained at {staging}", file=sys.stderr)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="benchmark TOML supplying [paths]")
    parser.add_argument("--metadata-db", type=Path, help="read-only catalog database")
    parser.add_argument("--transcripts", type=Path, help="catalog transcript directory, as used by benchmark pool")
    parser.add_argument("--lexicon", type=Path, help="sampling lexicon JSON")
    parser.add_argument("--out-dir", type=Path, help="new directory for scan tables (default: config paths.scan_dir)")
    parser.add_argument("--study-manifest", type=Path, help="revision-pinned episodes.csv from study export")
    parser.add_argument("--workers", type=_positive, default=min(28, os.cpu_count() or 1))
    parser.add_argument("--limit", type=_positive, help="scan the first N selected IDs, for a smoke test")
    args = parser.parse_args(argv)
    try:
        config = resolve_path(str(args.config))
        paths = load_config(config)["paths"]
        lexicon = resolve_path(str(args.lexicon or paths["lexicon"]))
        output = resolve_path(str(args.out_dir or paths["scan_dir"]))
        if args.study_manifest:
            if args.metadata_db or args.transcripts:
                parser.error("--study-manifest supplies paths; do not combine with --metadata-db or --transcripts")
            jobs, provenance = study_jobs(resolve_path(str(args.study_manifest)))
        else:
            database = resolve_path(str(args.metadata_db or paths["metadata_db"]))
            transcripts = resolve_path(str(args.transcripts or paths["transcripts"]))
            jobs = catalog_jobs(database, transcripts)
            provenance = {"kind": "catalog", "metadata_db": str(database), "transcripts": str(transcripts)}
        if args.limit:
            jobs = jobs[:args.limit]
        provenance["limit"] = args.limit
        manifest = run_scan(jobs, lexicon, output, workers=args.workers, provenance=provenance, config=config)
        print(json.dumps({"output": str(output), "rows": manifest["rows"]}))
        return 0
    except (ScanError, OSError, ValueError, KeyError, sqlite3.Error) as exc:
        print(f"lexical scan: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
