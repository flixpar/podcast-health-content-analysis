"""Command-line entry point: ``python -m podcast_pipeline <command>``."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from podcast_pipeline import db
from podcast_pipeline.config import DEFAULT_CONFIG_PATH, LOG_DIR, Config
from podcast_pipeline.log import configure_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m podcast_pipeline",
        description="Fetch, download, and transcribe podcasts.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH,
                        help=f"path to config.json (default: {DEFAULT_CONFIG_PATH})")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p = sub.add_parser("fetch-podcasts", help="record the top podcasts from a chart source")
    p.add_argument("--limit", type=int, help="number of podcasts (default: fetcher.default_limit)")
    p.add_argument("--source", choices=["apple", "spotify", "podchaser"],
                   help="chart source for this run (default: fetcher.type)")
    p.add_argument("--genre", help="Apple genre id, e.g. 1512 for Health & Fitness "
                                   "(default: fetcher.genre; Apple source only)")
    p.add_argument("--country", help="storefront / chart region (default: fetcher.country)")

    p = sub.add_parser("discover", help="read every podcast feed and record its episodes (no downloads)")
    p.add_argument("--max-episodes", type=int,
                   help="newest episodes to record per feed (default: discovery.max_episodes_per_podcast)")

    p = sub.add_parser("fetch-rss-transcripts", help="fetch transcripts publishers attach to their feeds")
    p.add_argument("--limit", type=int)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--min-words", type=int, default=100,
                   help="reject shorter transcripts as failures")

    p = sub.add_parser("download", help="download audio for pending episodes (resumable)")
    p.add_argument("--limit", type=int, help="stop after this many episodes")
    p.add_argument("--workers", type=int, help="parallel downloads (default: download.max_workers)")
    p.add_argument("--skip-errors", action="store_true",
                   help="only attempt 'pending' episodes, not previously failed ones")
    p.add_argument("--charts", type=_str_list, default=[],
                   help="only podcasts in these charts, comma-separated "
                        "(e.g. apple_us_genre_1512); see the podcast_charts table")

    p = sub.add_parser("transcribe", help="transcribe downloaded audio with Parakeet")
    p.add_argument("--limit", type=int)
    p.add_argument("--retry-errors", action="store_true",
                   help="also retry episodes whose previous transcription failed")

    p = sub.add_parser("convert-audio", help="re-encode existing MP3s to Opus/OGG")
    p.add_argument("--threshold", type=float, help="minimum file size in MB (default: from config)")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--keep-original", action="store_true")
    p.add_argument("--reconcile-only", action="store_true",
                   help="only record conversions an interrupted run already produced; encode nothing")

    p = sub.add_parser("audit", help="reconcile the database against audio on disk")
    p.add_argument("--fix", action="store_true", help="reset broken rows to pending")
    p.add_argument("--newer-than", help="only probe files modified after 'YYYY-MM-DD HH:MM'")
    p.add_argument("--skip-probe", action="store_true", help="skip ffprobe; check existence and size only")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--report", type=Path, default=LOG_DIR / "audit_report.json")

    p = sub.add_parser("reset-transcripts", help="delete ASR transcripts so episodes are transcribed again")
    p.add_argument("--episode-ids", type=_int_list, default=[], help="comma-separated")
    p.add_argument("--podcast-ids", type=_int_list, default=[], help="comma-separated")
    p.add_argument("--all", action="store_true", help="every ASR transcript")
    p.add_argument("--keep-files", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("export-audio-batch",
                       help="package downloaded, transcript-free audio for transfer")
    p.add_argument("output_dir", type=Path,
                   help="destination directory, normally a mounted transfer disk")
    p.add_argument("--target-gb", type=float,
                   help="target audio payload in decimal GB (default: batch_export.target_size_gb)")
    p.add_argument("--include-exported", action="store_true",
                   help="allow episodes recorded in an earlier completed batch")
    p.add_argument("--dry-run", action="store_true",
                   help="select and report a batch without writing files")

    p = sub.add_parser("ingest-audio-batch",
                       help="verify and prepare a transferred audio batch on a remote server")
    p.add_argument("archive", type=Path)
    p.add_argument("workspace_dir", type=Path,
                   help="directory that will receive the verified batch directory")
    p.add_argument("--checksum", type=Path, help="checksum sidecar (default: ARCHIVE.sha256)")
    p.add_argument("--skip-archive-checksum", action="store_true",
                   help="permit a missing sidecar; member hashes are still verified")

    p = sub.add_parser("transcribe-audio-batch",
                       help="resumably transcribe a prepared batch without the source database")
    p.add_argument("batch_dir", type=Path)
    p.add_argument("--limit", type=int)
    p.add_argument("--retry-errors", action="store_true")
    p.add_argument("--verify-audio-hashes", action="store_true",
                   help="rehash all audio before starting (ingest already verifies it)")

    p = sub.add_parser("export-transcript-batch",
                       help="package remote transcripts for return transfer")
    p.add_argument("batch_dir", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("--allow-partial", action="store_true",
                   help="export completed transcripts even though some episodes are unfinished")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("import-transcript-batch",
                       help="verify returned transcripts and register them in the source dataset")
    p.add_argument("archive", type=Path)
    p.add_argument("--checksum", type=Path, help="checksum sidecar (default: ARCHIVE.sha256)")
    p.add_argument("--skip-archive-checksum", action="store_true",
                   help="permit a missing sidecar; member hashes are still verified")
    p.add_argument("--dry-run", action="store_true",
                   help="fully validate without copying transcripts or writing SQLite")

    sub.add_parser("stats", help="show database and storage counts")
    return parser


def _int_list(value: str) -> list[int]:
    return [int(v) for v in value.split(",") if v.strip()]


def _str_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    configure_logging(LOG_DIR / "pipeline.log", args.log_level)
    database_free = {
        "ingest-audio-batch", "transcribe-audio-batch", "export-transcript-batch",
    }
    if args.command in database_free and args.config == DEFAULT_CONFIG_PATH and not args.config.exists():
        config = Config()
    else:
        config = Config.load(args.config)
    conn = None if args.command in database_free else db.connect(config.db_path)
    try:
        result = dispatch(args, config, conn)
    finally:
        if conn is not None:
            conn.close()
    print(json.dumps(result, indent=2))


def dispatch(args: argparse.Namespace, config: Config, conn) -> dict:
    from podcast_pipeline.pipeline import (audit, convert_audio, discover, download,
                                           export_audio_batch, export_transcript_batch,
                                           fetch_podcasts, import_transcript_batch,
                                           ingest_audio_batch, reset_transcripts,
                                           rss_transcripts, stats, transcribe,
                                           transcribe_audio_batch)
    match args.command:
        case "fetch-podcasts":
            # Chart selection is per-run: one collection is assembled from
            # several charts, so overriding beats editing config.json each time.
            if args.source:
                config.fetcher.type = args.source
            if args.genre:
                config.fetcher.genre = args.genre
            if args.country:
                config.fetcher.country = args.country
            return fetch_podcasts.run(config, conn, limit=args.limit)
        case "discover":
            return discover.run(config, conn, max_episodes=args.max_episodes)
        case "fetch-rss-transcripts":
            return rss_transcripts.run(config, conn, limit=args.limit, workers=args.workers,
                                       timeout=args.timeout, min_words=args.min_words)
        case "download":
            return download.run(config, conn, limit=args.limit, retry_errors=not args.skip_errors,
                                workers=args.workers, charts=args.charts)
        case "transcribe":
            return transcribe.run(config, conn, limit=args.limit, retry_errors=args.retry_errors)
        case "convert-audio":
            return convert_audio.run(config, conn, threshold_mb=args.threshold,
                                     reconcile_only=args.reconcile_only, workers=args.workers,
                                     limit=args.limit, dry_run=args.dry_run,
                                     keep_original=True if args.keep_original else None)
        case "audit":
            return audit.run(config, conn, fix=args.fix, newer_than=args.newer_than,
                             workers=args.workers, skip_probe=args.skip_probe, report=args.report)
        case "reset-transcripts":
            return reset_transcripts.run(config, conn, episode_ids=args.episode_ids,
                                         podcast_ids=args.podcast_ids, everything=args.all,
                                         keep_files=args.keep_files, dry_run=args.dry_run)
        case "export-audio-batch":
            return export_audio_batch.run(
                config, conn, output_dir=args.output_dir, target_gb=args.target_gb,
                include_exported=args.include_exported, dry_run=args.dry_run,
            )
        case "ingest-audio-batch":
            return ingest_audio_batch.run(
                args.archive, args.workspace_dir, checksum_path=args.checksum,
                skip_archive_checksum=args.skip_archive_checksum,
            )
        case "transcribe-audio-batch":
            return transcribe_audio_batch.run(
                config, args.batch_dir, limit=args.limit, retry_errors=args.retry_errors,
                verify_audio_hashes=args.verify_audio_hashes,
            )
        case "export-transcript-batch":
            return export_transcript_batch.run(
                args.batch_dir, args.output_dir, allow_partial=args.allow_partial,
                dry_run=args.dry_run,
            )
        case "import-transcript-batch":
            return import_transcript_batch.run(
                config, conn, args.archive, checksum_path=args.checksum,
                skip_archive_checksum=args.skip_archive_checksum, dry_run=args.dry_run,
            )
        case "stats":
            return stats.run(config, conn)
    raise ValueError(f"unhandled command {args.command}")
