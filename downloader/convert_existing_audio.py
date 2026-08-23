#!/usr/bin/env python3
"""
Retroactive Audio Compression Script
Converts existing downloaded audio files to Opus in OGG format
"""

import os
import sys
import json
import logging
import argparse
import shutil
import sqlite3
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project structure
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "podcast_metadata.db"
CONFIG_FILE = PROJECT_ROOT / "config.json"

# Stop converting rather than filling the volume; a full disk is what stranded
# the previous run halfway through.
MIN_FREE_GB = 20.0

# A conversion must retain at least this fraction of the source duration.
DURATION_TOLERANCE = 0.98


class DiskFull(RuntimeError):
    """Raised when the audio volume is too full to keep converting."""


def probe_duration(path: Path) -> Optional[float]:
    """Decoded duration in seconds, or None if ffprobe cannot read the file."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=120,
        )
        if out.returncode != 0:
            return None
        value = out.stdout.strip()
        return float(value) if value and value != "N/A" else None
    except (subprocess.TimeoutExpired, ValueError):
        return None


class AudioConverter:
    """Handles retroactive conversion of existing audio files"""

    def __init__(self, config_path: Path = CONFIG_FILE):
        """Initialize converter with configuration"""
        self.config = self._load_config(config_path)
        self.compression_config = self.config.get('audio_compression', {})
        self.db_path = DB_PATH

        # Stats
        self._local = threading.local()
        self.stats = {
            'total_files': 0,
            'converted': 0,
            'reused': 0,
            'skipped': 0,
            'failed': 0,
            'total_saved_mb': 0,
            'total_original_mb': 0,
            'total_compressed_mb': 0
        }

    def _load_config(self, config_path: Path) -> dict:
        """Load configuration from JSON file"""
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            sys.exit(1)

        with open(config_path, 'r') as f:
            return json.load(f)

    def get_files_to_convert(self, min_size_mb: Optional[float] = None,
                             reconcile_only: bool = False) -> List[Dict]:
        """
        Query database for audio files that need conversion

        Args:
            min_size_mb: Minimum file size threshold (overrides config)
            reconcile_only: Only return files that have already been converted
                but never recorded -- the leftovers of an interrupted run.
                Nothing is re-encoded in this mode.

        Returns:
            List of file info dicts
        """
        if min_size_mb is None:
            min_size_mb = self.compression_config.get('size_threshold_mb', 50)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get all episodes with audio files
        cursor.execute("""
            SELECT e.id, e.audio_file_path, e.is_compressed, e.original_file_size_mb
            FROM episodes e
            WHERE e.audio_file_path IS NOT NULL
              AND e.status != 'error'
        """)

        files_to_convert = []

        for episode_id, audio_path, is_compressed, original_size in cursor.fetchall():
            file_path = Path(audio_path)

            # Skip if already compressed
            if is_compressed:
                logger.debug(f"Skipping already compressed file: {file_path}")
                continue

            # Skip if file doesn't exist
            if not file_path.exists():
                logger.warning(f"File not found in database but missing on disk: {file_path}")
                continue

            # Get actual file size
            file_size_mb = file_path.stat().st_size / (1024 ** 2)

            if reconcile_only:
                # Only pick up work a previous run already did but never recorded
                converted = file_path.with_suffix('.ogg')
                if not (converted.exists() and converted.stat().st_size > 0):
                    continue
            elif file_size_mb < min_size_mb:
                logger.debug(f"Skipping file below threshold: {file_path} ({file_size_mb:.1f}MB)")
                continue

            files_to_convert.append({
                'episode_id': episode_id,
                'input_path': file_path,
                'file_size_mb': file_size_mb
            })

        conn.close()

        self.stats['total_files'] = len(files_to_convert)
        logger.info(f"Found {len(files_to_convert)} files to convert")

        return files_to_convert

    def convert_file(self, file_info: Dict) -> Dict:
        """
        Convert a single audio file

        Args:
            file_info: Dict with episode_id, input_path, file_size_mb

        Returns:
            Dict with conversion results
        """
        episode_id = file_info['episode_id']
        input_path = Path(file_info['input_path'])
        original_size_mb = file_info['file_size_mb']

        # Generate output path (.ogg extension)
        output_path = input_path.with_suffix('.ogg')

        result = {
            'episode_id': episode_id,
            'input_path': input_path,
            'output_path': output_path,
            'original_size_mb': original_size_mb,
            'success': False
        }

        try:
            # A previous interrupted run may have produced the .ogg already but
            # never recorded it. Verify and reuse it instead of re-encoding.
            if output_path.exists():
                existing_mb = output_path.stat().st_size / (1024 ** 2)
                existing_duration = probe_duration(output_path)
                source_duration = probe_duration(input_path)
                # An interrupted run converted some files while their source was
                # still downloading, leaving an .ogg far shorter than the .mp3.
                # Reusing one of those would discard most of the episode, so the
                # durations must agree before we trust it.
                if (existing_mb >= 0.1 and existing_duration is not None
                        and source_duration
                        and existing_duration >= source_duration * DURATION_TOLERANCE):
                    logger.debug(f"Reusing existing conversion: {output_path}")
                    result['compressed_size_mb'] = existing_mb
                    result['compression_ratio'] = (original_size_mb / existing_mb
                                                   if existing_mb > 0 else 1.0)
                    result['saved_mb'] = original_size_mb - existing_mb
                    result['reused'] = True
                    result['success'] = True
                    return result
                if existing_duration is not None and source_duration:
                    logger.warning(f"Discarding short conversion {output_path.name}: "
                                   f"{existing_duration:.0f}s vs source {source_duration:.0f}s")
                output_path.unlink()

            free_gb = shutil.disk_usage(output_path.parent).free / (1024 ** 3)
            if free_gb < MIN_FREE_GB:
                raise DiskFull(f"Only {free_gb:.1f}GB free, need {MIN_FREE_GB}GB")

            # Build ffmpeg command
            bitrate = self.compression_config.get('bitrate', '24k')
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-c:a', 'libopus',
                '-b:a', bitrate,
                '-vbr', 'on',
                '-ac', '1',  # mono
                '-y',  # overwrite
                str(output_path)
            ]

            # Run ffmpeg with output suppression
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            if process.returncode != 0:
                result['error'] = f"ffmpeg failed: {process.stderr[:200]}"
                # ffmpeg creates the output before encoding, so a failed run
                # leaves an empty file that later passes mistake for a success.
                output_path.unlink(missing_ok=True)
                if 'No space left on device' in process.stderr:
                    raise DiskFull(f"Disk full while converting {input_path}")
                return result

            # Verify output file
            if not output_path.exists():
                result['error'] = "Output file not created"
                return result

            compressed_size_mb = output_path.stat().st_size / (1024 ** 2)

            if compressed_size_mb < 0.1:
                result['error'] = f"Output file suspiciously small: {compressed_size_mb:.2f}MB"
                output_path.unlink()
                return result

            # Never delete an original on the strength of a file we have not
            # decoded. Compare durations so a truncated encode is caught here.
            encoded_duration = probe_duration(output_path)
            if encoded_duration is None:
                result['error'] = "Converted file is not decodable"
                output_path.unlink(missing_ok=True)
                return result

            source_duration = probe_duration(input_path)
            if source_duration and encoded_duration < source_duration * DURATION_TOLERANCE:
                result['error'] = (f"Converted file is short: {encoded_duration:.0f}s "
                                   f"vs source {source_duration:.0f}s")
                output_path.unlink(missing_ok=True)
                return result

            result['compressed_size_mb'] = compressed_size_mb
            result['compression_ratio'] = original_size_mb / compressed_size_mb if compressed_size_mb > 0 else 1.0
            result['saved_mb'] = original_size_mb - compressed_size_mb
            result['success'] = True

            return result

        except subprocess.TimeoutExpired:
            result['error'] = "ffmpeg timeout (600s)"
            output_path.unlink(missing_ok=True)
            return result
        except DiskFull:
            raise
        except Exception as e:
            result['error'] = str(e)
            output_path.unlink(missing_ok=True)
            return result

    def _thread_conn(self) -> sqlite3.Connection:
        """One SQLite connection per worker thread; sharing one is not safe."""
        conn = getattr(self._local, 'conn', None)
        if conn is None:
            conn = sqlite3.connect(str(self.db_path), timeout=60.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=60000")
            self._local.conn = conn
        return conn

    def commit_conversion(self, result: Dict, keep_original: bool = False) -> bool:
        """
        Record one conversion and then delete its original.

        Order matters: the database is committed before the MP3 is unlinked, so
        an interruption can only ever leave a converted file that is still
        recorded correctly -- never a deleted original with no record of where
        its replacement went. The previous version converted every file first
        and updated the database at the very end, so being killed midway lost
        the bookkeeping for thousands of already-converted files.
        """
        conn = self._thread_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE episodes
            SET audio_file_path = ?,
                original_file_size_mb = ?,
                compressed_file_size_mb = ?,
                compression_ratio = ?,
                is_compressed = 1
            WHERE id = ?
        """, (
            str(result['output_path']),
            result['original_size_mb'],
            result['compressed_size_mb'],
            result['compression_ratio'],
            result['episode_id'],
        ))
        conn.commit()

        if not keep_original:
            try:
                result['input_path'].unlink()
            except FileNotFoundError:
                pass
            except OSError as e:
                logger.warning(f"Failed to delete original {result['input_path']}: {e}")
        return True

    def convert_all(self, files: List[Dict], workers: int = None,
                    dry_run: bool = False, keep_original: bool = False):
        """
        Convert files, committing each one as it finishes.

        Args:
            files: List of file info dicts
            workers: Number of parallel workers (default: min(cpu_count, 8))
            dry_run: If True, don't actually convert or update database
            keep_original: If True, keep original files after conversion
        """
        if not files:
            logger.info("No files to convert")
            return

        if workers is None:
            workers = min(cpu_count(), 8)  # Cap at 8 to avoid overwhelming the system

        if dry_run:
            logger.info("DRY RUN MODE - No files will be modified")
            total_mb = sum(f['file_size_mb'] for f in files)
            for file_info in files[:20]:
                logger.info(f"Would convert: {file_info['input_path']} ({file_info['file_size_mb']:.1f}MB)")
            if len(files) > 20:
                logger.info(f"... and {len(files) - 20} more")
            logger.info(f"Would process {len(files)} files totalling {total_mb / 1024:.1f}GB")
            return

        logger.info(f"Converting {len(files)} files using {workers} workers...")
        stop = threading.Event()
        lock = threading.Lock()

        def handle(file_info: Dict):
            if stop.is_set():
                return
            try:
                result = self.convert_file(file_info)
            except DiskFull as e:
                logger.error(f"Halting: {e}")
                stop.set()
                return

            if not result['success']:
                with lock:
                    self.stats['failed'] += 1
                logger.error(f"Conversion failed for episode {result['episode_id']}: "
                             f"{result.get('error', 'Unknown error')}")
                return

            self.commit_conversion(result, keep_original)
            with lock:
                self.stats['converted'] += 1
                self.stats['reused'] += int(result.get('reused', False))
                self.stats['total_saved_mb'] += result['saved_mb']
                self.stats['total_original_mb'] += result['original_size_mb']
                self.stats['total_compressed_mb'] += result['compressed_size_mb']

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(tqdm(pool.map(handle, files), total=len(files),
                      desc="Converting", unit="file"))

        if stop.is_set():
            logger.error("Stopped early on low disk space -- free space and re-run; "
                         "already-converted files will be picked up where they left off")

        self.print_summary()

    def print_summary(self):
        """Print conversion summary statistics"""
        print("\n" + "=" * 60)
        print("CONVERSION SUMMARY")
        print("=" * 60)
        print(f"Total files:         {self.stats['total_files']}")
        print(f"Converted:           {self.stats['converted']}"
              f"  (of which reused from an earlier run: {self.stats['reused']})")
        print(f"Failed:              {self.stats['failed']}")
        print(f"Skipped:             {self.stats['skipped']}")
        print(f"-" * 60)
        print(f"Original size:       {self.stats['total_original_mb']:.1f} MB")
        print(f"Compressed size:     {self.stats['total_compressed_mb']:.1f} MB")
        print(f"Space saved:         {self.stats['total_saved_mb']:.1f} MB ({self.stats['total_saved_mb']/1024:.2f} GB)")
        if self.stats['total_original_mb'] > 0:
            compression_pct = (self.stats['total_saved_mb'] / self.stats['total_original_mb']) * 100
            print(f"Compression ratio:   {compression_pct:.1f}%")
        print("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Convert existing podcast audio files to compressed Opus/OGG format'
    )
    parser.add_argument(
        '--reconcile-only',
        action='store_true',
        help='Only record conversions a previous interrupted run already produced, '
             'and delete their originals. Never re-encodes anything.'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        help='Minimum file size in MB to convert (overrides config)',
        default=None
    )
    parser.add_argument(
        '--workers',
        type=int,
        help='Number of parallel workers (default: CPU count)',
        default=None
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be converted without actually converting'
    )
    parser.add_argument(
        '--keep-original',
        action='store_true',
        help='Keep original files after conversion'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of files to convert (for testing)',
        default=None
    )

    args = parser.parse_args()

    # Check ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.error("ffmpeg not found. Please install ffmpeg.")
        sys.exit(1)

    # Initialize converter
    converter = AudioConverter()

    # Get files to convert
    files = converter.get_files_to_convert(min_size_mb=args.threshold,
                                           reconcile_only=args.reconcile_only)

    if not files:
        logger.info("No files need conversion")
        return

    # Limit if specified
    if args.limit:
        files = files[:args.limit]
        logger.info(f"Limited to {args.limit} files")

    # Convert
    converter.convert_all(
        files,
        workers=args.workers,
        dry_run=args.dry_run,
        keep_original=args.keep_original
    )


if __name__ == "__main__":
    main()
