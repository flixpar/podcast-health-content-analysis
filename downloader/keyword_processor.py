"""
Main keyword processing pipeline for tagging podcast episodes.

This module coordinates transcript reading, keyword matching, and database storage
for efficient at-scale keyword analysis of podcast content.
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

from transcript_processor import TranscriptProcessor
from keyword_database import KeywordDatabase
from keyword_matcher import KeywordMatcher, KeywordMatch

logger = logging.getLogger(__name__)


class KeywordProcessor:
    """
    Processes podcast transcripts to find and tag keyword matches.

    Supports:
    - Fuzzy keyword matching for transcription errors
    - Incremental processing (only new episodes or new keywords)
    - Batch processing for efficiency
    - Progress tracking and error handling
    """

    def __init__(self,
                 db_path: str = "data/podcast_metadata.db",
                 transcript_dir: str = "data/transcripts",
                 fuzzy_threshold: float = 85.0,
                 context_chars: int = 100,
                 max_workers: int = 4,
                 batch_size: int = 100):
        """
        Initialize the keyword processor.

        Args:
            db_path: Path to SQLite database
            transcript_dir: Directory containing transcript files
            fuzzy_threshold: Minimum similarity score for fuzzy matches (0-100)
            context_chars: Characters of context to extract around matches
            max_workers: Number of parallel workers for processing
            batch_size: Number of episodes to process before committing to DB
        """
        self.db_path = db_path
        self.transcript_dir = Path(transcript_dir)
        self.max_workers = max_workers
        self.batch_size = batch_size

        self.keyword_db = KeywordDatabase(db_path)
        self.transcript_processor = TranscriptProcessor(transcript_dir)
        self.keyword_matcher = KeywordMatcher(
            fuzzy_threshold=fuzzy_threshold,
            context_chars=context_chars
        )

        logger.info(f"Initialized KeywordProcessor with fuzzy_threshold={fuzzy_threshold}")

    def process_keywords(self,
                        keywords: List[str],
                        category: Optional[str] = None,
                        incremental: bool = True,
                        force_reprocess: bool = False) -> Dict:
        """
        Process keywords across all transcribed episodes.

        Args:
            keywords: List of keywords to search for
            category: Optional category for organizing keywords
            incremental: If True, only process episodes not yet tagged with these keywords
            force_reprocess: If True, reprocess all episodes even if already tagged

        Returns:
            Dictionary with processing statistics
        """
        start_time = time.time()

        # Add keywords to database
        logger.info(f"Adding {len(keywords)} keywords to database...")
        keyword_ids = self.keyword_db.add_keywords(keywords, category=category)

        if not keyword_ids:
            logger.warning("No valid keywords to process")
            return {'status': 'no_keywords', 'processed': 0}

        # Get episodes to process
        if force_reprocess:
            episode_ids = self._get_all_transcribed_episodes()
            logger.info(f"Force reprocess mode: processing all {len(episode_ids)} episodes")
        elif incremental:
            episode_ids = self.keyword_db.get_untagged_episodes(keyword_ids)
            logger.info(f"Incremental mode: processing {len(episode_ids)} untagged episodes")
        else:
            episode_ids = self._get_all_transcribed_episodes()
            logger.info(f"Full scan mode: processing {len(episode_ids)} episodes")

        if not episode_ids:
            logger.info("No episodes to process")
            return {
                'status': 'no_episodes',
                'keywords_added': len(keyword_ids),
                'processed': 0,
                'duration_seconds': time.time() - start_time
            }

        # Process episodes in parallel
        stats = self._process_episodes_parallel(episode_ids, keywords, keyword_ids)

        stats['duration_seconds'] = time.time() - start_time
        stats['episodes_per_second'] = stats['processed'] / stats['duration_seconds'] if stats['duration_seconds'] > 0 else 0

        logger.info(f"Processing complete: {stats['processed']} episodes in {stats['duration_seconds']:.2f}s "
                   f"({stats['episodes_per_second']:.2f} eps/s)")

        return stats

    def _process_episodes_parallel(self,
                                   episode_ids: List[int],
                                   keywords: List[str],
                                   keyword_ids: List[int]) -> Dict:
        """
        Process episodes in parallel using thread pool.

        Args:
            episode_ids: List of episode IDs to process
            keywords: Keywords to search for
            keyword_ids: Corresponding keyword tag IDs

        Returns:
            Statistics dictionary
        """
        stats = {
            'processed': 0,
            'matched': 0,
            'errors': 0,
            'total_matches': 0,
            'keyword_stats': {}
        }

        # Create keyword -> ID mapping
        keyword_to_id = {}
        for keyword, kid in zip(keywords, keyword_ids):
            keyword_lower = keyword.lower().strip()
            keyword_to_id[keyword_lower] = kid

        # Process in batches with progress bar
        with tqdm(total=len(episode_ids), desc="Processing episodes", unit="ep") as pbar:
            for i in range(0, len(episode_ids), self.batch_size):
                batch = episode_ids[i:i + self.batch_size]

                # Process batch
                batch_results = []
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(self._process_single_episode, ep_id, keywords):
                        ep_id for ep_id in batch
                    }

                    for future in as_completed(futures):
                        ep_id = futures[future]
                        try:
                            result = future.result()
                            if result:
                                batch_results.append(result)
                        except Exception as e:
                            logger.error(f"Error processing episode {ep_id}: {e}")
                            stats['errors'] += 1

                        pbar.update(1)

                # Store batch results in database
                self._store_batch_results(batch_results, keyword_to_id, stats)

                stats['processed'] += len(batch)

        return stats

    def _process_single_episode(self,
                               episode_id: int,
                               keywords: List[str]) -> Optional[Dict]:
        """
        Process a single episode to find keyword matches.

        Args:
            episode_id: Episode ID to process
            keywords: Keywords to search for

        Returns:
            Dictionary with episode_id and matches, or None if error
        """
        try:
            # Load transcript
            transcript_data = self.transcript_processor.load_transcript(episode_id)
            if not transcript_data:
                logger.debug(f"No transcript found for episode {episode_id}")
                return None

            # Extract full text from summary
            text = ""
            for line in transcript_data:
                if line.get('type') == 'summary':
                    text = line.get('text', '')
                    break

            if not text:
                logger.debug(f"No text content in transcript for episode {episode_id}")
                return None

            # Find keyword matches
            matches = self.keyword_matcher.match_keywords_in_text(text, keywords)

            if not matches:
                return None

            return {
                'episode_id': episode_id,
                'matches': matches
            }

        except Exception as e:
            logger.error(f"Error processing episode {episode_id}: {e}")
            return None

    def _store_batch_results(self,
                            batch_results: List[Dict],
                            keyword_to_id: Dict[str, int],
                            stats: Dict):
        """
        Store batch results in database.

        Args:
            batch_results: List of episode results with matches
            keyword_to_id: Mapping of keyword -> keyword_tag_id
            stats: Statistics dictionary to update
        """
        for result in batch_results:
            episode_id = result['episode_id']
            matches = result['matches']

            stats['matched'] += 1

            for keyword, keyword_matches in matches.items():
                keyword_lower = keyword.lower().strip()
                keyword_tag_id = keyword_to_id.get(keyword_lower)

                if not keyword_tag_id:
                    logger.warning(f"No keyword_tag_id found for '{keyword}'")
                    continue

                # Calculate statistics
                match_count = len(keyword_matches)
                avg_confidence = sum(m.confidence for m in keyword_matches) / match_count

                # Prepare matched positions (store first 10 for space efficiency)
                positions = [
                    {
                        'position': m.position,
                        'confidence': m.confidence,
                        'matched_text': m.matched_text,
                        'context': m.context
                    }
                    for m in keyword_matches[:10]  # Limit stored matches
                ]

                # Store in database
                try:
                    self.keyword_db.add_episode_keyword(
                        episode_id=episode_id,
                        keyword_tag_id=keyword_tag_id,
                        match_count=match_count,
                        confidence_score=avg_confidence,
                        matched_positions=positions
                    )

                    # Update stats
                    stats['total_matches'] += match_count

                    if keyword_lower not in stats['keyword_stats']:
                        stats['keyword_stats'][keyword_lower] = {
                            'episodes': 0,
                            'total_matches': 0
                        }

                    stats['keyword_stats'][keyword_lower]['episodes'] += 1
                    stats['keyword_stats'][keyword_lower]['total_matches'] += match_count

                except Exception as e:
                    logger.error(f"Error storing keyword match for episode {episode_id}, "
                               f"keyword '{keyword}': {e}")

    def _get_all_transcribed_episodes(self) -> List[int]:
        """Get all episode IDs that have been transcribed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id FROM episodes
                WHERE status = 'transcribed'
                ORDER BY id
            """)
            return [row[0] for row in cursor.fetchall()]

    def get_processing_status(self) -> Dict:
        """
        Get current processing status and statistics.

        Returns:
            Dictionary with various statistics about the keyword tagging system
        """
        with sqlite3.connect(self.db_path) as conn:
            # Count total keywords
            cursor = conn.execute("SELECT COUNT(*) FROM keyword_tags")
            total_keywords = cursor.fetchone()[0]

            # Count total tagged episodes
            cursor = conn.execute("SELECT COUNT(DISTINCT episode_id) FROM episode_keywords")
            tagged_episodes = cursor.fetchone()[0]

            # Count total transcribed episodes
            cursor = conn.execute("SELECT COUNT(*) FROM episodes WHERE status = 'transcribed'")
            total_episodes = cursor.fetchone()[0]

            # Count total tags
            cursor = conn.execute("SELECT COUNT(*) FROM episode_keywords")
            total_tags = cursor.fetchone()[0]

            # Get category breakdown
            cursor = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM keyword_tags
                GROUP BY category
            """)
            categories = {row[0] or 'uncategorized': row[1] for row in cursor.fetchall()}

        return {
            'total_keywords': total_keywords,
            'total_episodes': total_episodes,
            'tagged_episodes': tagged_episodes,
            'untagged_episodes': total_episodes - tagged_episodes,
            'total_tags': total_tags,
            'categories': categories,
            'coverage_percent': (tagged_episodes / total_episodes * 100
                               if total_episodes > 0 else 0)
        }

    def reprocess_keyword(self, keyword: str) -> Dict:
        """
        Reprocess a single keyword across all episodes.

        Useful for when you want to update the threshold or matching logic
        for a specific keyword.

        Args:
            keyword: The keyword to reprocess

        Returns:
            Processing statistics
        """
        return self.process_keywords(
            keywords=[keyword],
            incremental=False,
            force_reprocess=True
        )

    def remove_keyword_tags(self, keyword: str) -> bool:
        """
        Remove all tags for a specific keyword.

        Args:
            keyword: The keyword to remove

        Returns:
            True if removed, False if not found
        """
        return self.keyword_db.delete_keyword(keyword)
