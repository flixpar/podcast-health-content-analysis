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
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from multiprocessing import Pool, cpu_count
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


class AudioConverter:
    """Handles retroactive conversion of existing audio files"""

    def __init__(self, config_path: Path = CONFIG_FILE):
        """Initialize converter with configuration"""
        self.config = self._load_config(config_path)
        self.compression_config = self.config.get('audio_compression', {})
        self.db_path = DB_PATH

        # Stats
        self.stats = {
            'total_files': 0,
            'converted': 0,
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

    def get_files_to_convert(self, min_size_mb: Optional[float] = None) -> List[Dict]:
        """
        Query database for audio files that need conversion

        Args:
            min_size_mb: Minimum file size threshold (overrides config)

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

            # Skip if below threshold
            if file_size_mb < min_size_mb:
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

            result['compressed_size_mb'] = compressed_size_mb
            result['compression_ratio'] = original_size_mb / compressed_size_mb if compressed_size_mb > 0 else 1.0
            result['saved_mb'] = original_size_mb - compressed_size_mb
            result['success'] = True

            return result

        except subprocess.TimeoutExpired:
            result['error'] = "ffmpeg timeout (600s)"
            return result
        except Exception as e:
            result['error'] = str(e)
            return result

    def update_database(self, result: Dict, keep_original: bool = False):
        """
        Update database with conversion results

        Args:
            result: Conversion result dict
            keep_original: If False, delete original file
        """
        if not result['success']:
            return

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Update episode record
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
                result['episode_id']
            ))

            conn.commit()

            # Delete original if configured
            if not keep_original:
                try:
                    result['input_path'].unlink()
                    logger.debug(f"Deleted original: {result['input_path']}")
                except Exception as e:
                    logger.warning(f"Failed to delete original: {e}")

        except Exception as e:
            logger.error(f"Database update failed for episode {result['episode_id']}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def convert_all(self, files: List[Dict], workers: int = None,
                    dry_run: bool = False, keep_original: bool = False):
        """
        Convert all files in parallel

        Args:
            files: List of file info dicts
            workers: Number of parallel workers (default: CPU count)
            dry_run: If True, don't actually convert or update database
            keep_original: If True, keep original files after conversion
        """
        if not files:
            logger.info("No files to convert")
            return

        if workers is None:
            workers = min(cpu_count(), 8)  # Cap at 8 to avoid overwhelming the system

        logger.info(f"Converting {len(files)} files using {workers} workers...")

        if dry_run:
            logger.info("DRY RUN MODE - No files will be modified")
            for file_info in files:
                logger.info(f"Would convert: {file_info['input_path']} ({file_info['file_size_mb']:.1f}MB)")
            return

        # Convert files in parallel
        with Pool(processes=workers) as pool:
            results = list(tqdm(
                pool.imap(self.convert_file, files),
                total=len(files),
                desc="Converting files",
                unit="file"
            ))

        # Update database and collect stats
        logger.info("Updating database...")
        for result in tqdm(results, desc="Updating DB", unit="file"):
            if result['success']:
                self.update_database(result, keep_original)
                self.stats['converted'] += 1
                self.stats['total_saved_mb'] += result['saved_mb']
                self.stats['total_original_mb'] += result['original_size_mb']
                self.stats['total_compressed_mb'] += result['compressed_size_mb']
            else:
                self.stats['failed'] += 1
                logger.error(f"Conversion failed for episode {result['episode_id']}: {result.get('error', 'Unknown error')}")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print conversion summary statistics"""
        print("\n" + "=" * 60)
        print("CONVERSION SUMMARY")
        print("=" * 60)
        print(f"Total files:         {self.stats['total_files']}")
        print(f"Converted:           {self.stats['converted']}")
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
    files = converter.get_files_to_convert(min_size_mb=args.threshold)

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
