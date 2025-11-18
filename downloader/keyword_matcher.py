"""
Efficient fuzzy keyword matching for podcast transcripts.

This module provides fast keyword matching with fuzzy matching support to handle
transcription inconsistencies. Uses RapidFuzz for efficient string matching.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import logging

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logging.warning("rapidfuzz not available, falling back to exact matching only")

logger = logging.getLogger(__name__)


@dataclass
class KeywordMatch:
    """Represents a keyword match in text."""
    keyword: str
    matched_text: str
    position: int
    confidence: float  # 0-100 similarity score
    context: str  # Surrounding text for context


class KeywordMatcher:
    """
    Fast fuzzy keyword matching with configurable similarity thresholds.

    Handles various transcription inconsistencies like:
    - "COVID-19" vs "COVID 19" vs "covid nineteen"
    - "vaccine" vs "vaccination" vs "vaccinate"
    - Misspellings and OCR errors
    """

    def __init__(self,
                 fuzzy_threshold: float = 85.0,
                 context_chars: int = 100,
                 case_sensitive: bool = False,
                 use_fuzzy: bool = True):
        """
        Initialize the keyword matcher.

        Args:
            fuzzy_threshold: Minimum similarity score (0-100) for fuzzy matches
            context_chars: Number of characters to include in match context
            case_sensitive: Whether to match case-sensitively
            use_fuzzy: Whether to use fuzzy matching (requires rapidfuzz)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.context_chars = context_chars
        self.case_sensitive = case_sensitive
        self.use_fuzzy = use_fuzzy and RAPIDFUZZ_AVAILABLE

        if use_fuzzy and not RAPIDFUZZ_AVAILABLE:
            logger.warning("Fuzzy matching requested but rapidfuzz not available, "
                         "falling back to exact matching")

    def match_keywords_in_text(self, text: str, keywords: List[str],
                               max_matches_per_keyword: Optional[int] = None) -> Dict[str, List[KeywordMatch]]:
        """
        Find all keyword matches in text with fuzzy matching support.

        Args:
            text: The text to search in
            keywords: List of keywords to search for
            max_matches_per_keyword: Optional limit on matches per keyword

        Returns:
            Dictionary mapping keywords to list of matches
        """
        if not text or not keywords:
            return {}

        matches = {}

        # Prepare text
        search_text = text if self.case_sensitive else text.lower()

        for keyword in keywords:
            search_keyword = keyword if self.case_sensitive else keyword.lower()
            keyword_matches = []

            # First, try exact substring matching (fast path)
            exact_matches = self._find_exact_matches(search_text, search_keyword, text)
            keyword_matches.extend(exact_matches)

            # If fuzzy matching is enabled and we want more matches
            if self.use_fuzzy and (max_matches_per_keyword is None or
                                   len(keyword_matches) < max_matches_per_keyword):
                # Find fuzzy matches (avoiding duplicates with exact matches)
                exact_positions = {m.position for m in exact_matches}
                fuzzy_matches = self._find_fuzzy_matches(
                    search_text, search_keyword, text, exact_positions
                )
                keyword_matches.extend(fuzzy_matches)

            # Limit matches if requested
            if max_matches_per_keyword:
                keyword_matches = keyword_matches[:max_matches_per_keyword]

            if keyword_matches:
                matches[keyword] = keyword_matches

        return matches

    def _find_exact_matches(self, search_text: str, keyword: str,
                          original_text: str) -> List[KeywordMatch]:
        """Find all exact substring matches."""
        matches = []
        start = 0

        while True:
            pos = search_text.find(keyword, start)
            if pos == -1:
                break

            # Get context around match
            context = self._extract_context(original_text, pos, len(keyword))
            matched_text = original_text[pos:pos + len(keyword)]

            matches.append(KeywordMatch(
                keyword=keyword,
                matched_text=matched_text,
                position=pos,
                confidence=100.0,
                context=context
            ))

            start = pos + 1

        return matches

    def _find_fuzzy_matches(self, search_text: str, keyword: str,
                          original_text: str,
                          exclude_positions: Set[int]) -> List[KeywordMatch]:
        """
        Find fuzzy matches using word-level and n-gram matching.

        This is more efficient than comparing against every substring.
        """
        matches = []

        # Split text into words and create n-grams around keyword length
        words = re.findall(r'\b\w+\b', search_text)
        keyword_words = len(keyword.split())

        # Generate n-grams (sequences of words) of similar length to keyword
        n_gram_size = max(1, keyword_words)

        for i in range(len(words) - n_gram_size + 1):
            n_gram = ' '.join(words[i:i + n_gram_size + 1])  # Slightly larger window

            # Quick check: if completely different length, skip
            len_diff = abs(len(n_gram) - len(keyword))
            if len_diff > len(keyword) * 0.5:  # More than 50% length difference
                continue

            # Calculate similarity
            similarity = fuzz.ratio(keyword, n_gram)

            if similarity >= self.fuzzy_threshold:
                # Find position of this n-gram in original text
                # This is approximate since we're working with words
                n_gram_pattern = re.escape(' '.join(words[i:i + n_gram_size + 1]))
                match_obj = re.search(n_gram_pattern, search_text)

                if match_obj:
                    pos = match_obj.start()

                    # Skip if too close to an exact match
                    if any(abs(pos - ep) < len(keyword) for ep in exclude_positions):
                        continue

                    # Extract actual matched text
                    matched_text = original_text[pos:pos + len(n_gram)]
                    context = self._extract_context(original_text, pos, len(matched_text))

                    matches.append(KeywordMatch(
                        keyword=keyword,
                        matched_text=matched_text,
                        position=pos,
                        confidence=similarity,
                        context=context
                    ))

        # Sort by confidence and remove overlapping matches
        matches = self._deduplicate_matches(matches)

        return matches

    def _extract_context(self, text: str, position: int, match_length: int) -> str:
        """Extract context around a match."""
        start = max(0, position - self.context_chars)
        end = min(len(text), position + match_length + self.context_chars)

        context = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        return context

    def _deduplicate_matches(self, matches: List[KeywordMatch]) -> List[KeywordMatch]:
        """Remove overlapping fuzzy matches, keeping highest confidence."""
        if not matches:
            return []

        # Sort by position first, then by confidence descending
        sorted_matches = sorted(matches, key=lambda m: (m.position, -m.confidence))

        deduplicated = []
        last_end_pos = -1

        for match in sorted_matches:
            # If this match doesn't overlap with the last kept match
            if match.position >= last_end_pos:
                deduplicated.append(match)
                last_end_pos = match.position + len(match.matched_text)

        return deduplicated

    def get_match_statistics(self, matches: Dict[str, List[KeywordMatch]]) -> Dict[str, Dict]:
        """
        Calculate statistics for keyword matches.

        Args:
            matches: Dictionary of keyword matches from match_keywords_in_text()

        Returns:
            Dictionary with statistics per keyword
        """
        stats = {}

        for keyword, keyword_matches in matches.items():
            if not keyword_matches:
                continue

            confidences = [m.confidence for m in keyword_matches]

            stats[keyword] = {
                'match_count': len(keyword_matches),
                'avg_confidence': sum(confidences) / len(confidences),
                'min_confidence': min(confidences),
                'max_confidence': max(confidences),
                'exact_matches': sum(1 for c in confidences if c == 100.0),
                'fuzzy_matches': sum(1 for c in confidences if c < 100.0)
            }

        return stats

    def batch_match_keywords(self, texts: List[str], keywords: List[str],
                           max_matches_per_keyword: Optional[int] = None) -> List[Dict[str, List[KeywordMatch]]]:
        """
        Match keywords across multiple texts efficiently.

        Args:
            texts: List of texts to search
            keywords: Keywords to search for
            max_matches_per_keyword: Optional limit per keyword per text

        Returns:
            List of match dictionaries, one per input text
        """
        return [
            self.match_keywords_in_text(text, keywords, max_matches_per_keyword)
            for text in texts
        ]


class MultiPatternMatcher:
    """
    Optimized matcher for multiple keyword patterns.

    Useful when you have groups of related keywords (e.g., vaccine-related,
    COVID-related, etc.) and want to categorize matches.
    """

    def __init__(self, fuzzy_threshold: float = 85.0, context_chars: int = 100):
        """
        Initialize multi-pattern matcher.

        Args:
            fuzzy_threshold: Minimum similarity score for fuzzy matches
            context_chars: Characters of context to extract
        """
        self.matcher = KeywordMatcher(
            fuzzy_threshold=fuzzy_threshold,
            context_chars=context_chars
        )
        self.patterns: Dict[str, List[str]] = {}

    def add_pattern(self, pattern_name: str, keywords: List[str]):
        """
        Add a named pattern (group of keywords).

        Args:
            pattern_name: Name for this pattern group (e.g., "vaccines")
            keywords: List of keywords in this pattern
        """
        self.patterns[pattern_name] = keywords

    def match_patterns(self, text: str) -> Dict[str, Dict[str, List[KeywordMatch]]]:
        """
        Match all patterns against text.

        Args:
            text: Text to search in

        Returns:
            Nested dict: pattern_name -> keyword -> list of matches
        """
        results = {}

        for pattern_name, keywords in self.patterns.items():
            matches = self.matcher.match_keywords_in_text(text, keywords)
            if matches:
                results[pattern_name] = matches

        return results

    def get_pattern_coverage(self, text: str) -> Dict[str, float]:
        """
        Calculate what percentage of each pattern's keywords match.

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping pattern names to coverage percentage (0-100)
        """
        coverage = {}

        for pattern_name, keywords in self.patterns.items():
            matches = self.matcher.match_keywords_in_text(text, keywords)
            matched_keywords = len(matches)
            total_keywords = len(keywords)
            coverage[pattern_name] = (matched_keywords / total_keywords * 100
                                     if total_keywords > 0 else 0)

        return coverage
