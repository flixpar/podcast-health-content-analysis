#!/usr/bin/env python3
"""
Command-line interface for keyword-based podcast episode filtering.

This CLI provides tools for:
- Adding keywords and processing episodes
- Searching episodes by keywords
- Viewing statistics and managing keywords
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from typing import List, Optional
import csv

from keyword_processor import KeywordProcessor
from keyword_database import KeywordDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KeywordCLI:
    """Command-line interface for keyword tagging system."""

    def __init__(self, db_path: str = "data/podcast_metadata.db",
                 transcript_dir: str = "data/transcripts"):
        """
        Initialize the CLI.

        Args:
            db_path: Path to SQLite database
            transcript_dir: Directory containing transcripts
        """
        self.db_path = db_path
        self.transcript_dir = transcript_dir
        self.keyword_db = KeywordDatabase(db_path)
        self.processor = KeywordProcessor(db_path, transcript_dir)

    def add_keywords(self, keywords: List[str], category: Optional[str] = None,
                    process: bool = True, incremental: bool = True,
                    fuzzy_threshold: float = 85.0) -> None:
        """
        Add keywords and optionally process episodes.

        Args:
            keywords: List of keywords to add
            category: Optional category for grouping
            process: Whether to immediately process episodes
            incremental: Whether to only process untagged episodes
            fuzzy_threshold: Similarity threshold for fuzzy matching
        """
        print(f"\n{'='*60}")
        print(f"Adding {len(keywords)} keywords...")
        print(f"{'='*60}\n")

        for kw in keywords:
            print(f"  - {kw}")

        if category:
            print(f"\nCategory: {category}")

        # Add keywords
        keyword_ids = self.keyword_db.add_keywords(keywords, category=category)
        print(f"\n✓ Added {len(keyword_ids)} keywords to database")

        # Process episodes if requested
        if process:
            print(f"\nProcessing episodes with fuzzy_threshold={fuzzy_threshold}...")
            print(f"Mode: {'Incremental (new episodes only)' if incremental else 'Full scan'}")

            stats = self.processor.process_keywords(
                keywords=keywords,
                category=category,
                incremental=incremental,
                force_reprocess=not incremental
            )

            self._print_processing_stats(stats)

    def add_keywords_from_file(self, file_path: str, category: Optional[str] = None,
                              process: bool = True, incremental: bool = True) -> None:
        """
        Add keywords from a text file (one per line).

        Args:
            file_path: Path to file containing keywords
            category: Optional category
            process: Whether to process episodes
            incremental: Whether to use incremental processing
        """
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found: {file_path}")
            return

        with open(path, 'r') as f:
            keywords = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        if not keywords:
            print("No keywords found in file")
            return

        self.add_keywords(keywords, category=category, process=process, incremental=incremental)

    def search_episodes(self, keywords: List[str], logic: str = 'any',
                       output_format: str = 'table', output_file: Optional[str] = None,
                       limit: Optional[int] = None) -> None:
        """
        Search for episodes containing keywords.

        Args:
            keywords: Keywords to search for
            logic: 'any' or 'all' - whether episodes must match any or all keywords
            output_format: 'table', 'json', or 'csv'
            output_file: Optional file to write results to
            limit: Optional limit on number of results
        """
        print(f"\n{'='*60}")
        print(f"Searching for episodes with {logic.upper()} of: {', '.join(keywords)}")
        print(f"{'='*60}\n")

        # Get episodes
        if logic == 'any':
            episodes = self.keyword_db.get_episodes_with_any_keyword(keywords)
        elif logic == 'all':
            episodes = self.keyword_db.get_episodes_with_all_keywords(keywords)
        else:
            print(f"Error: Invalid logic '{logic}'. Must be 'any' or 'all'")
            return

        if limit:
            episodes = episodes[:limit]

        if not episodes:
            print("No episodes found matching criteria")
            return

        print(f"Found {len(episodes)} episodes\n")

        # Output results
        if output_format == 'json':
            self._output_json(episodes, output_file)
        elif output_format == 'csv':
            self._output_csv(episodes, output_file)
        else:
            self._output_table(episodes, output_file)

    def list_keywords(self, category: Optional[str] = None, show_stats: bool = True) -> None:
        """
        List all keywords, optionally filtered by category.

        Args:
            category: Optional category to filter by
            show_stats: Whether to show statistics
        """
        if category:
            keywords = self.keyword_db.get_keywords_by_category(category)
            print(f"\nKeywords in category '{category}':")
        else:
            keywords = self.keyword_db.get_all_keywords()
            print(f"\nAll keywords:")

        if not keywords:
            print("  (none)")
            return

        if show_stats:
            stats = self.keyword_db.get_keyword_statistics()
            stats_map = {s['keyword']: s for s in stats}

            print(f"\n{'Keyword':<30} {'Category':<20} {'Episodes':<12} {'Matches':<12}")
            print("-" * 74)

            for kw in keywords:
                keyword_text = kw['keyword']
                category_text = kw['category'] or '-'
                stat = stats_map.get(keyword_text, {})
                ep_count = stat.get('episode_count', 0)
                match_count = stat.get('total_matches', 0)

                print(f"{keyword_text:<30} {category_text:<20} {ep_count:<12} {match_count:<12}")
        else:
            for kw in keywords:
                category_text = f" [{kw['category']}]" if kw['category'] else ""
                print(f"  - {kw['keyword']}{category_text}")

        print(f"\nTotal: {len(keywords)} keywords")

    def show_statistics(self) -> None:
        """Show overall system statistics."""
        print(f"\n{'='*60}")
        print("Keyword Tagging System Statistics")
        print(f"{'='*60}\n")

        # Overall stats
        status = self.processor.get_processing_status()

        print(f"Episodes:")
        print(f"  Total transcribed: {status['total_episodes']}")
        print(f"  Tagged: {status['tagged_episodes']}")
        print(f"  Untagged: {status['untagged_episodes']}")
        print(f"  Coverage: {status['coverage_percent']:.1f}%")

        print(f"\nKeywords:")
        print(f"  Total keywords: {status['total_keywords']}")
        print(f"  Total tags: {status['total_tags']}")

        if status['categories']:
            print(f"\nCategories:")
            for category, count in sorted(status['categories'].items()):
                print(f"  {category}: {count} keywords")

        # Top keywords
        print(f"\nTop Keywords by Episode Count:")
        keyword_stats = self.keyword_db.get_keyword_statistics()
        top_keywords = sorted(keyword_stats, key=lambda x: x['episode_count'], reverse=True)[:10]

        if top_keywords:
            print(f"\n{'Keyword':<30} {'Episodes':<12} {'Total Matches':<15} {'Avg Confidence':<15}")
            print("-" * 72)
            for stat in top_keywords:
                keyword = stat['keyword']
                ep_count = stat['episode_count'] or 0
                total = stat['total_matches'] or 0
                avg_conf = stat['avg_confidence'] or 0
                print(f"{keyword:<30} {ep_count:<12} {total:<15} {avg_conf:<15.1f}")

    def show_episode_keywords(self, episode_id: int) -> None:
        """
        Show all keywords tagged on a specific episode.

        Args:
            episode_id: Episode ID to query
        """
        keywords = self.keyword_db.get_episode_keywords(episode_id)

        if not keywords:
            print(f"No keywords found for episode {episode_id}")
            return

        print(f"\nKeywords for episode {episode_id}:")
        print(f"\n{'Keyword':<30} {'Category':<20} {'Matches':<12} {'Confidence':<12}")
        print("-" * 74)

        for kw in keywords:
            keyword = kw['keyword']
            category = kw['category'] or '-'
            matches = kw['match_count']
            conf = kw['confidence_score'] or 0

            print(f"{keyword:<30} {category:<20} {matches:<12} {conf:<12.1f}")

            # Show match positions if available
            if kw['matched_positions']:
                positions = json.loads(kw['matched_positions'])
                print(f"\n  Sample matches:")
                for i, pos in enumerate(positions[:3], 1):
                    context = pos['context'][:100] + "..." if len(pos['context']) > 100 else pos['context']
                    print(f"    {i}. \"{context}\"")
                print()

    def remove_keyword(self, keyword: str) -> None:
        """
        Remove a keyword and all its tags.

        Args:
            keyword: Keyword to remove
        """
        confirm = input(f"Remove keyword '{keyword}' and all its episode tags? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled")
            return

        if self.keyword_db.delete_keyword(keyword):
            print(f"✓ Removed keyword '{keyword}'")
        else:
            print(f"Keyword '{keyword}' not found")

    def reprocess_keyword(self, keyword: str) -> None:
        """
        Reprocess a keyword across all episodes.

        Args:
            keyword: Keyword to reprocess
        """
        print(f"\nReprocessing keyword '{keyword}' across all episodes...")

        stats = self.processor.reprocess_keyword(keyword)
        self._print_processing_stats(stats)

    def _print_processing_stats(self, stats: Dict) -> None:
        """Print processing statistics."""
        print(f"\n{'='*60}")
        print("Processing Results")
        print(f"{'='*60}\n")

        print(f"Episodes processed: {stats.get('processed', 0)}")
        print(f"Episodes matched: {stats.get('matched', 0)}")
        print(f"Total matches: {stats.get('total_matches', 0)}")
        print(f"Errors: {stats.get('errors', 0)}")

        if stats.get('duration_seconds'):
            print(f"Duration: {stats['duration_seconds']:.2f}s")
            print(f"Speed: {stats.get('episodes_per_second', 0):.2f} episodes/sec")

        keyword_stats = stats.get('keyword_stats', {})
        if keyword_stats:
            print(f"\nPer-Keyword Results:")
            print(f"\n{'Keyword':<30} {'Episodes':<12} {'Total Matches':<15}")
            print("-" * 57)
            for keyword, kw_stat in sorted(keyword_stats.items()):
                print(f"{keyword:<30} {kw_stat['episodes']:<12} {kw_stat['total_matches']:<15}")

    def _output_table(self, episodes: List[Dict], output_file: Optional[str] = None) -> None:
        """Output episodes in table format."""
        lines = []
        lines.append(f"{'ID':<8} {'Podcast':<30} {'Episode Title':<50} {'Matches':<10}")
        lines.append("-" * 98)

        for ep in episodes:
            ep_id = str(ep['id'])
            podcast = ep['podcast_title'][:28] if ep.get('podcast_title') else '-'
            title = ep['title'][:48] if ep['title'] else '-'
            matches = str(ep.get('total_matches') or ep.get('match_count', 0))

            lines.append(f"{ep_id:<8} {podcast:<30} {title:<50} {matches:<10}")

        output = '\n'.join(lines)

        if output_file:
            Path(output_file).write_text(output)
            print(f"Results written to {output_file}")
        else:
            print(output)

    def _output_json(self, episodes: List[Dict], output_file: Optional[str] = None) -> None:
        """Output episodes in JSON format."""
        output = json.dumps(episodes, indent=2, default=str)

        if output_file:
            Path(output_file).write_text(output)
            print(f"Results written to {output_file}")
        else:
            print(output)

    def _output_csv(self, episodes: List[Dict], output_file: Optional[str] = None) -> None:
        """Output episodes in CSV format."""
        if not episodes:
            return

        # Determine fields
        fields = ['id', 'podcast_title', 'title', 'published_date',
                 'matched_keywords', 'total_matches']

        # Write CSV
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(episodes)

        result = output.getvalue()

        if output_file:
            Path(output_file).write_text(result)
            print(f"Results written to {output_file}")
        else:
            print(result)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Keyword-based filtering for podcast episodes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add keywords and process episodes
  %(prog)s add "vaccine" "vaccination" "immunization" --category health

  # Add keywords from file
  %(prog)s add-file keywords.txt --category misinformation

  # Search for episodes (any keyword)
  %(prog)s search "vaccine" "covid" --output results.json

  # Search for episodes (all keywords)
  %(prog)s search "vaccine" "safety" --logic all

  # List all keywords with statistics
  %(prog)s list --stats

  # Show system statistics
  %(prog)s stats

  # Show keywords for an episode
  %(prog)s episode-keywords 123
        """
    )

    parser.add_argument('--db', default='data/podcast_metadata.db',
                       help='Path to database (default: data/podcast_metadata.db)')
    parser.add_argument('--transcripts', default='data/transcripts',
                       help='Path to transcripts directory (default: data/transcripts)')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Add keywords command
    add_parser = subparsers.add_parser('add', help='Add keywords and process episodes')
    add_parser.add_argument('keywords', nargs='+', help='Keywords to add')
    add_parser.add_argument('--category', help='Category for keywords')
    add_parser.add_argument('--no-process', action='store_true',
                           help='Do not process episodes immediately')
    add_parser.add_argument('--full-scan', action='store_true',
                           help='Process all episodes (not just new ones)')
    add_parser.add_argument('--fuzzy-threshold', type=float, default=85.0,
                           help='Fuzzy match threshold 0-100 (default: 85)')

    # Add from file command
    file_parser = subparsers.add_parser('add-file', help='Add keywords from file')
    file_parser.add_argument('file', help='File containing keywords (one per line)')
    file_parser.add_argument('--category', help='Category for keywords')
    file_parser.add_argument('--no-process', action='store_true',
                            help='Do not process episodes immediately')
    file_parser.add_argument('--full-scan', action='store_true',
                            help='Process all episodes (not just new ones)')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search episodes by keywords')
    search_parser.add_argument('keywords', nargs='+', help='Keywords to search for')
    search_parser.add_argument('--logic', choices=['any', 'all'], default='any',
                              help='Match any or all keywords (default: any)')
    search_parser.add_argument('--output', help='Output file path')
    search_parser.add_argument('--format', choices=['table', 'json', 'csv'],
                              default='table', help='Output format (default: table)')
    search_parser.add_argument('--limit', type=int, help='Limit number of results')

    # List keywords command
    list_parser = subparsers.add_parser('list', help='List all keywords')
    list_parser.add_argument('--category', help='Filter by category')
    list_parser.add_argument('--stats', action='store_true',
                            help='Show statistics for each keyword')

    # Statistics command
    subparsers.add_parser('stats', help='Show system statistics')

    # Episode keywords command
    ep_kw_parser = subparsers.add_parser('episode-keywords',
                                        help='Show keywords for an episode')
    ep_kw_parser.add_argument('episode_id', type=int, help='Episode ID')

    # Remove keyword command
    remove_parser = subparsers.add_parser('remove', help='Remove a keyword')
    remove_parser.add_argument('keyword', help='Keyword to remove')

    # Reprocess command
    reprocess_parser = subparsers.add_parser('reprocess',
                                            help='Reprocess a keyword across all episodes')
    reprocess_parser.add_argument('keyword', help='Keyword to reprocess')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize CLI
    cli = KeywordCLI(db_path=args.db, transcript_dir=args.transcripts)

    # Execute command
    try:
        if args.command == 'add':
            cli.add_keywords(
                keywords=args.keywords,
                category=args.category,
                process=not args.no_process,
                incremental=not args.full_scan,
                fuzzy_threshold=args.fuzzy_threshold
            )

        elif args.command == 'add-file':
            cli.add_keywords_from_file(
                file_path=args.file,
                category=args.category,
                process=not args.no_process,
                incremental=not args.full_scan
            )

        elif args.command == 'search':
            cli.search_episodes(
                keywords=args.keywords,
                logic=args.logic,
                output_format=args.format,
                output_file=args.output,
                limit=args.limit
            )

        elif args.command == 'list':
            cli.list_keywords(category=args.category, show_stats=args.stats)

        elif args.command == 'stats':
            cli.show_statistics()

        elif args.command == 'episode-keywords':
            cli.show_episode_keywords(args.episode_id)

        elif args.command == 'remove':
            cli.remove_keyword(args.keyword)

        elif args.command == 'reprocess':
            cli.reprocess_keyword(args.keyword)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
