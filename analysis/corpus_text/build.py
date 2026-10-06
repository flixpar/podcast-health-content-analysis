"""Build a plain-text transcript corpus in a new directory, without GPU access."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
from contextlib import ExitStack, closing
from multiprocessing import get_context
from pathlib import Path

import zstandard

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "downloader/data/transcripts"
OUT = Path(os.environ.get("CORPUS_TEXT_DIR", str(REPO / "local/corpus-text")))
DB = REPO / "downloader/data/podcast_metadata.db"
N = 64
EPISODE_FILE = re.compile(r"episode_(\d+)\.jsonl(?:\.zst)?$")


class CorpusError(RuntimeError):
    pass


def _records(path: Path):
    with ExitStack() as stack:
        raw = stack.enter_context(path.open("rb"))
        stream = raw
        if path.suffix == ".zst":
            stream = stack.enter_context(zstandard.ZstdDecompressor().stream_reader(raw))
        text = stack.enter_context(io.TextIOWrapper(stream, encoding="utf-8"))
        for line in text:
            if line.strip():
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise CorpusError(f"{path}: transcript records must be objects")
                yield record


def work(job: tuple[int, list[tuple[int, Path]], Path]) -> tuple[int, int, int]:
    shard, files, output = job
    segments = 0
    with (output / f"shard_{shard:02d}.tsv").open("w", encoding="utf-8") as out:
        for episode_id, path in files:
            segment_records = 0
            summary = ""
            try:
                for record in _records(path):
                    if record.get("type") == "summary":
                        summary = " ".join((record.get("text") or "").split())
                    if record.get("type") != "segment":
                        continue
                    index = record.get("index", segment_records)
                    if type(index) is not int or index < 0:
                        raise CorpusError(f"{path}: invalid segment index {index!r}")
                    segment_records += 1
                    text = " ".join((record.get("text") or "").split())
                    if text:
                        out.write(f"{episode_id}\t{index}\t{text}\n")
                        segments += 1
                if not segment_records and summary:
                    out.write(f"{episode_id}\t0\t{summary}\n")
                    segments += 1
            except (OSError, ValueError, AttributeError, zstandard.ZstdError) as exc:
                raise CorpusError(f"{path}: {exc}") from exc
    return shard, len(files), segments


def build_corpus(transcripts: Path, database: Path, output: Path, workers: int) -> dict:
    """Publish all shards together; retain failed staging files for inspection."""
    transcripts, database, output = (Path(p).resolve() for p in (transcripts, database, output))
    if output.exists():
        raise CorpusError(f"{output} already exists; choose a new --out-dir")
    if not transcripts.is_dir():
        raise CorpusError(f"Transcript directory does not exist: {transcripts}")
    if workers < 1:
        raise CorpusError("workers must be at least 1")
    files = {}
    # Prefer compressed files when both forms exist, matching benchmark pool.
    for suffix in ("*.jsonl", "*.jsonl.zst"):
        for path in sorted(transcripts.glob(suffix)):
            match = EPISODE_FILE.fullmatch(path.name)
            if match:
                files[int(match[1])] = path
    if not files:
        raise CorpusError(f"No episode transcripts in {transcripts}")
    # mode=ro never creates an empty catalog; as_uri escapes special characters.
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as con:
        metadata = con.execute(
            "SELECT e.id, e.podcast_id, p.title, substr(e.published_date,1,10), e.title "
            "FROM episodes e JOIN podcasts p ON p.id=e.podcast_id ORDER BY e.id"
        ).fetchall()
    missing = set(files) - {row[0] for row in metadata}
    if missing:
        raise CorpusError(f"Transcript episodes missing from catalog: {sorted(missing)[:10]}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    jobs = [(shard, [(ep, path) for ep, path in sorted(files.items()) if ep % N == shard], staging)
            for shard in range(N)]
    manifest = {
        "schema_version": "corpus-text-v1", "complete": False,
        "transcripts": str(transcripts), "metadata_db": str(database),
        "shards": N, "episodes": len(files),
    }
    try:
        with (staging / "episodes.tsv").open("w", encoding="utf-8") as out:
            out.write("episode_id\tpodcast_id\tpodcast\tdate\tepisode_title\n")
            for row in metadata:
                out.write("\t".join(" ".join(str(x if x is not None else "").split()) for x in row) + "\n")
        if workers == 1:
            results = list(map(work, jobs))
        else:
            with get_context("spawn").Pool(min(workers, N)) as pool:
                results = list(pool.imap_unordered(work, jobs))
        manifest.update(complete=True, segments=sum(row[2] for row in results))
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if output.exists():
            raise CorpusError(f"{output} appeared during build; refusing to replace it")
        staging.rename(output)
        return manifest
    except BaseException as exc:
        manifest.update(complete=False, error=str(exc))
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Incomplete corpus retained at {staging}", file=sys.stderr)
        raise


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcripts", type=Path, default=SRC)
    parser.add_argument("--metadata-db", type=Path, default=DB)
    parser.add_argument("--out-dir", type=Path, default=OUT)
    parser.add_argument("--workers", type=_positive, default=min(28, os.cpu_count() or 1))
    args = parser.parse_args(argv)
    try:
        manifest = build_corpus(args.transcripts, args.metadata_db, args.out_dir, args.workers)
        print(f"episodes {manifest['episodes']} segments {manifest['segments']}")
        return 0
    except (CorpusError, OSError, sqlite3.Error) as exc:
        print(f"corpus build: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
