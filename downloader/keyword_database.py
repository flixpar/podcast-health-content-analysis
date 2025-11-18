"""
Keyword tagging database management for podcast episodes.

This module handles the database schema and operations for storing and querying
keyword tags on podcast episodes with fuzzy matching support.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class KeywordDatabase:
    """Manages keyword tags and episode-keyword associations in SQLite."""

    def __init__(self, db_path: str = "data/podcast_metadata.db"):
        """
        Initialize the keyword database manager.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Create keyword tagging tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS keyword_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL UNIQUE,
                    category TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS episode_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id INTEGER NOT NULL,
                    keyword_tag_id INTEGER NOT NULL,
                    match_count INTEGER NOT NULL DEFAULT 0,
                    confidence_score REAL,
                    matched_positions TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (keyword_tag_id) REFERENCES keyword_tags(id) ON DELETE CASCADE,
                    UNIQUE(episode_id, keyword_tag_id)
                )
            """)

            # Create indices for efficient querying
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episode_keywords_episode
                ON episode_keywords(episode_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episode_keywords_keyword
                ON episode_keywords(keyword_tag_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_keyword_tags_keyword
                ON keyword_tags(keyword)
            """)

            conn.commit()
            logger.info("Keyword database schema ensured")

    def add_keywords(self, keywords: List[str], category: Optional[str] = None,
                    description: Optional[str] = None) -> List[int]:
        """
        Add keywords to the database.

        Args:
            keywords: List of keyword strings to add
            category: Optional category for grouping keywords
            description: Optional description for the keyword set

        Returns:
            List of keyword_tag_ids that were added or already existed
        """
        keyword_ids = []
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            for keyword in keywords:
                keyword_lower = keyword.lower().strip()
                if not keyword_lower:
                    continue

                try:
                    cursor = conn.execute("""
                        INSERT INTO keyword_tags (keyword, category, description, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (keyword_lower, category, description, timestamp))
                    keyword_ids.append(cursor.lastrowid)
                    logger.info(f"Added keyword: {keyword_lower}")
                except sqlite3.IntegrityError:
                    # Keyword already exists, fetch its ID
                    cursor = conn.execute("""
                        SELECT id FROM keyword_tags WHERE keyword = ?
                    """, (keyword_lower,))
                    result = cursor.fetchone()
                    if result:
                        keyword_ids.append(result[0])
                        logger.debug(f"Keyword already exists: {keyword_lower}")

            conn.commit()

        return keyword_ids

    def get_all_keywords(self) -> List[Dict]:
        """
        Retrieve all keywords from the database.

        Returns:
            List of keyword dictionaries with id, keyword, category, etc.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, keyword, category, description, created_at, metadata
                FROM keyword_tags
                ORDER BY keyword
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_keywords_by_category(self, category: str) -> List[Dict]:
        """Get all keywords in a specific category."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, keyword, category, description, created_at, metadata
                FROM keyword_tags
                WHERE category = ?
                ORDER BY keyword
            """, (category,))
            return [dict(row) for row in cursor.fetchall()]

    def add_episode_keyword(self, episode_id: int, keyword_tag_id: int,
                           match_count: int = 0, confidence_score: Optional[float] = None,
                           matched_positions: Optional[List[Dict]] = None) -> int:
        """
        Associate a keyword with an episode.

        Args:
            episode_id: ID of the episode
            keyword_tag_id: ID of the keyword tag
            match_count: Number of times the keyword was matched
            confidence_score: Average fuzzy match confidence (0-100)
            matched_positions: List of match positions with context

        Returns:
            ID of the episode_keyword record (or existing record ID)
        """
        timestamp = datetime.utcnow().isoformat()
        positions_json = json.dumps(matched_positions) if matched_positions else None

        with sqlite3.connect(self.db_path) as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO episode_keywords
                    (episode_id, keyword_tag_id, match_count, confidence_score,
                     matched_positions, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (episode_id, keyword_tag_id, match_count, confidence_score,
                      positions_json, timestamp))
                record_id = cursor.lastrowid
                conn.commit()
                return record_id
            except sqlite3.IntegrityError:
                # Update existing record
                conn.execute("""
                    UPDATE episode_keywords
                    SET match_count = ?, confidence_score = ?,
                        matched_positions = ?, created_at = ?
                    WHERE episode_id = ? AND keyword_tag_id = ?
                """, (match_count, confidence_score, positions_json,
                      timestamp, episode_id, keyword_tag_id))
                conn.commit()

                # Fetch the existing record ID
                cursor = conn.execute("""
                    SELECT id FROM episode_keywords
                    WHERE episode_id = ? AND keyword_tag_id = ?
                """, (episode_id, keyword_tag_id))
                return cursor.fetchone()[0]

    def get_episodes_with_keyword(self, keyword: str) -> List[Dict]:
        """
        Find all episodes containing a specific keyword.

        Args:
            keyword: The keyword to search for

        Returns:
            List of episode dictionaries with match information
        """
        keyword_lower = keyword.lower().strip()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    e.id, e.podcast_id, e.title, e.description,
                    e.published_date, e.audio_url, e.transcript_file_path,
                    ek.match_count, ek.confidence_score, ek.matched_positions,
                    kt.keyword, kt.category,
                    p.title as podcast_title, p.publisher
                FROM episodes e
                JOIN episode_keywords ek ON e.id = ek.episode_id
                JOIN keyword_tags kt ON ek.keyword_tag_id = kt.id
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE kt.keyword = ?
                ORDER BY ek.match_count DESC, e.published_date DESC
            """, (keyword_lower,))
            return [dict(row) for row in cursor.fetchall()]

    def get_episodes_with_any_keyword(self, keywords: List[str]) -> List[Dict]:
        """
        Find all episodes containing any of the specified keywords.

        Args:
            keywords: List of keywords to search for (OR logic)

        Returns:
            List of episode dictionaries with match information
        """
        if not keywords:
            return []

        keywords_lower = [k.lower().strip() for k in keywords]
        placeholders = ','.join(['?' for _ in keywords_lower])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT DISTINCT
                    e.id, e.podcast_id, e.title, e.description,
                    e.published_date, e.audio_url, e.transcript_file_path,
                    p.title as podcast_title, p.publisher,
                    GROUP_CONCAT(kt.keyword, ', ') as matched_keywords,
                    SUM(ek.match_count) as total_matches
                FROM episodes e
                JOIN episode_keywords ek ON e.id = ek.episode_id
                JOIN keyword_tags kt ON ek.keyword_tag_id = kt.id
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE kt.keyword IN ({placeholders})
                GROUP BY e.id
                ORDER BY total_matches DESC, e.published_date DESC
            """, keywords_lower)
            return [dict(row) for row in cursor.fetchall()]

    def get_episodes_with_all_keywords(self, keywords: List[str]) -> List[Dict]:
        """
        Find episodes containing ALL of the specified keywords.

        Args:
            keywords: List of keywords to search for (AND logic)

        Returns:
            List of episode dictionaries
        """
        if not keywords:
            return []

        keywords_lower = [k.lower().strip() for k in keywords]

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Build query with HAVING clause to ensure all keywords match
            placeholders = ','.join(['?' for _ in keywords_lower])
            cursor = conn.execute(f"""
                SELECT
                    e.id, e.podcast_id, e.title, e.description,
                    e.published_date, e.audio_url, e.transcript_file_path,
                    p.title as podcast_title, p.publisher,
                    GROUP_CONCAT(kt.keyword, ', ') as matched_keywords,
                    SUM(ek.match_count) as total_matches
                FROM episodes e
                JOIN episode_keywords ek ON e.id = ek.episode_id
                JOIN keyword_tags kt ON ek.keyword_tag_id = kt.id
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE kt.keyword IN ({placeholders})
                GROUP BY e.id
                HAVING COUNT(DISTINCT kt.keyword) = ?
                ORDER BY total_matches DESC, e.published_date DESC
            """, (*keywords_lower, len(keywords_lower)))
            return [dict(row) for row in cursor.fetchall()]

    def get_episode_keywords(self, episode_id: int) -> List[Dict]:
        """
        Get all keywords associated with a specific episode.

        Args:
            episode_id: ID of the episode

        Returns:
            List of keyword dictionaries with match information
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    kt.id, kt.keyword, kt.category, kt.description,
                    ek.match_count, ek.confidence_score, ek.matched_positions
                FROM keyword_tags kt
                JOIN episode_keywords ek ON kt.id = ek.keyword_tag_id
                WHERE ek.episode_id = ?
                ORDER BY ek.match_count DESC
            """, (episode_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_untagged_episodes(self, keyword_tag_ids: Optional[List[int]] = None) -> List[int]:
        """
        Get episode IDs that haven't been tagged with specific keywords.

        Args:
            keyword_tag_ids: Optional list of keyword IDs to check against.
                           If None, returns episodes with no tags at all.

        Returns:
            List of episode IDs
        """
        with sqlite3.connect(self.db_path) as conn:
            if keyword_tag_ids:
                # Find episodes that don't have tags for these specific keywords
                placeholders = ','.join(['?' for _ in keyword_tag_ids])
                cursor = conn.execute(f"""
                    SELECT e.id
                    FROM episodes e
                    WHERE e.status = 'transcribed'
                    AND e.id NOT IN (
                        SELECT episode_id
                        FROM episode_keywords
                        WHERE keyword_tag_id IN ({placeholders})
                    )
                    ORDER BY e.id
                """, keyword_tag_ids)
            else:
                # Find episodes with no tags at all
                cursor = conn.execute("""
                    SELECT e.id
                    FROM episodes e
                    WHERE e.status = 'transcribed'
                    AND e.id NOT IN (
                        SELECT DISTINCT episode_id FROM episode_keywords
                    )
                    ORDER BY e.id
                """)

            return [row[0] for row in cursor.fetchall()]

    def get_keyword_statistics(self) -> List[Dict]:
        """
        Get statistics about keyword usage across episodes.

        Returns:
            List of dictionaries with keyword stats (episode_count, total_matches, etc.)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    kt.id, kt.keyword, kt.category,
                    COUNT(DISTINCT ek.episode_id) as episode_count,
                    SUM(ek.match_count) as total_matches,
                    AVG(ek.match_count) as avg_matches_per_episode,
                    AVG(ek.confidence_score) as avg_confidence
                FROM keyword_tags kt
                LEFT JOIN episode_keywords ek ON kt.id = ek.keyword_tag_id
                GROUP BY kt.id
                ORDER BY episode_count DESC, total_matches DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def delete_keyword(self, keyword: str) -> bool:
        """
        Delete a keyword and all its episode associations.

        Args:
            keyword: The keyword to delete

        Returns:
            True if deleted, False if not found
        """
        keyword_lower = keyword.lower().strip()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM keyword_tags WHERE keyword = ?
            """, (keyword_lower,))
            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted keyword: {keyword_lower}")

            return deleted
