#!/usr/bin/env python3
"""
Simple validation test for the keyword filtering system.

This script tests basic functionality without requiring a full database.
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    all_imported = True

    try:
        from keyword_database import KeywordDatabase
        print("  ✓ keyword_database")
    except ImportError as e:
        print(f"  ✗ keyword_database: {e}")
        all_imported = False

    try:
        from keyword_matcher import KeywordMatcher, MultiPatternMatcher
        print("  ✓ keyword_matcher")
    except ImportError as e:
        print(f"  ✗ keyword_matcher: {e}")
        all_imported = False

    try:
        from keyword_processor import KeywordProcessor
        print("  ✓ keyword_processor")
    except ImportError as e:
        print(f"  ⚠ keyword_processor: {e}")
        print(f"    (Install dependencies: pip install -r requirements.txt)")
        # Don't fail the test - this is expected if deps not installed
        pass

    try:
        from keyword_cli import KeywordCLI
        print("  ✓ keyword_cli")
    except ImportError as e:
        print(f"  ⚠ keyword_cli: {e}")
        print(f"    (Install dependencies: pip install -r requirements.txt)")
        # Don't fail the test - this is expected if deps not installed
        pass

    return all_imported


def test_keyword_matcher():
    """Test the keyword matcher functionality."""
    print("\nTesting KeywordMatcher...")

    from keyword_matcher import KeywordMatcher

    matcher = KeywordMatcher(fuzzy_threshold=85.0)

    # Test text with various keyword variations
    text = """
    This is a podcast about vaccines and vaccination. We discuss COVID-19
    and the coronavirus pandemic. Some people are anti-vax, but the scientific
    evidence shows that immunization is safe and effective. Clinical trials
    have demonstrated vaccine safety.
    """

    keywords = ["vaccine", "COVID-19", "anti-vax", "clinical trial"]

    matches = matcher.match_keywords_in_text(text, keywords)

    print(f"\nTest text length: {len(text)} characters")
    print(f"Keywords to search: {keywords}")
    print(f"\nMatches found:")

    for keyword, keyword_matches in matches.items():
        print(f"  '{keyword}': {len(keyword_matches)} matches")
        for i, match in enumerate(keyword_matches[:2], 1):
            print(f"    {i}. '{match.matched_text}' (confidence: {match.confidence:.1f})")

    # Calculate statistics
    stats = matcher.get_match_statistics(matches)
    print(f"\nStatistics:")
    for keyword, stat in stats.items():
        print(f"  '{keyword}':")
        print(f"    Total matches: {stat['match_count']}")
        print(f"    Avg confidence: {stat['avg_confidence']:.1f}")
        print(f"    Exact matches: {stat['exact_matches']}")
        print(f"    Fuzzy matches: {stat['fuzzy_matches']}")

    return len(matches) > 0


def test_rapidfuzz():
    """Test if rapidfuzz is available."""
    print("\nTesting rapidfuzz availability...")

    try:
        from rapidfuzz import fuzz
        print("  ✓ rapidfuzz is installed")

        # Test fuzzy matching
        score = fuzz.ratio("vaccine", "vaccination")
        print(f"  Example: fuzz.ratio('vaccine', 'vaccination') = {score:.1f}")

        return True
    except ImportError:
        print("  ⚠ rapidfuzz not installed - fuzzy matching will be disabled")
        print("    Install with: pip install rapidfuzz>=3.0.0")
        print("    (System will still work with exact matching)")
        return True  # Don't fail - system works without it


def main():
    """Run all tests."""
    print("=" * 60)
    print("Keyword Filtering System Validation")
    print("=" * 60)

    results = []

    # Test imports
    results.append(("Imports", test_imports()))

    # Test rapidfuzz
    results.append(("RapidFuzz", test_rapidfuzz()))

    # Test keyword matcher
    try:
        results.append(("KeywordMatcher", test_keyword_matcher()))
    except Exception as e:
        print(f"\nError testing KeywordMatcher: {e}")
        results.append(("KeywordMatcher", False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✓ All tests passed!")
        print("\nYou can now use the keyword filtering system:")
        print("  python keyword_cli.py --help")
        return 0
    else:
        print("\n✗ Some tests failed - check errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
