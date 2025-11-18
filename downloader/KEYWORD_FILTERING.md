# Keyword Filtering System

A scalable, efficient keyword-based tagging system for podcast transcripts with fuzzy matching support to handle transcription inconsistencies.

## Overview

The keyword filtering system allows you to:
- Tag podcast episodes with keywords using fuzzy matching
- Search and filter episodes by keywords
- Track keyword statistics across your podcast collection
- Re-run analysis with different keyword sets without losing previous data
- Handle transcription inconsistencies (e.g., "COVID-19" vs "COVID 19")

## Architecture

The system consists of four main components:

### 1. Database Layer (`keyword_database.py`)

Manages two new SQLite tables:

- **`keyword_tags`**: Stores keywords with optional categories
  - `id`, `keyword`, `category`, `description`, `created_at`, `metadata`

- **`episode_keywords`**: Links episodes to keywords with match statistics
  - `episode_id`, `keyword_tag_id`, `match_count`, `confidence_score`, `matched_positions`

The database supports efficient queries for:
- Finding all episodes with a specific keyword
- Finding episodes with ANY keyword from a set (OR logic)
- Finding episodes with ALL keywords from a set (AND logic)
- Getting keyword statistics (episode counts, match counts, etc.)

### 2. Keyword Matcher (`keyword_matcher.py`)

Provides fast fuzzy keyword matching:

- **Exact matching**: Fast substring search
- **Fuzzy matching**: Uses RapidFuzz for similarity-based matching
- **Configurable threshold**: Default 85% similarity (adjustable)
- **Context extraction**: Stores surrounding text for each match
- **Deduplication**: Removes overlapping matches intelligently

**Key features:**
- Handles transcription inconsistencies
- Case-insensitive by default
- Word-level n-gram matching for efficiency
- Returns match confidence scores (0-100)

### 3. Keyword Processor (`keyword_processor.py`)

Orchestrates the processing pipeline:

- **Parallel processing**: Uses thread pools for speed
- **Batch processing**: Processes episodes in configurable batches
- **Incremental updates**: Only processes new episodes or new keywords
- **Progress tracking**: Real-time progress bars
- **Error handling**: Continues processing on errors

**Performance:**
- Processes multiple episodes concurrently
- Efficient transcript loading (compressed JSONL)
- Batch database commits
- Typical speed: 1-10 episodes/second (depending on transcript length and keyword count)

### 4. CLI Interface (`keyword_cli.py`)

User-friendly command-line interface with commands for:
- Adding keywords
- Searching episodes
- Viewing statistics
- Managing keywords

## Installation

1. Install the additional dependency:
```bash
pip install rapidfuzz>=3.0.0
```

Or install from requirements:
```bash
pip install -r requirements.txt
```

2. Make the CLI executable:
```bash
chmod +x keyword_cli.py
```

## Usage

### Adding Keywords

Add keywords directly:
```bash
python keyword_cli.py add "vaccine" "vaccination" "immunization" --category health
```

Add keywords from a file (one per line):
```bash
# Create keywords file
cat > keywords.txt << EOF
vaccine
vaccination
COVID-19
coronavirus
pandemic
misinformation
EOF

python keyword_cli.py add-file keywords.txt --category health
```

**Options:**
- `--category CATEGORY`: Group keywords by category
- `--no-process`: Add keywords without processing episodes
- `--full-scan`: Process all episodes (not just untagged ones)
- `--fuzzy-threshold THRESHOLD`: Set fuzzy match threshold (0-100, default: 85)

### Searching Episodes

Find episodes with ANY of the keywords (OR logic):
```bash
python keyword_cli.py search "vaccine" "vaccination"
```

Find episodes with ALL keywords (AND logic):
```bash
python keyword_cli.py search "vaccine" "safety" --logic all
```

Export results in different formats:
```bash
# JSON format
python keyword_cli.py search "vaccine" --format json --output results.json

# CSV format
python keyword_cli.py search "vaccine" --format csv --output results.csv

# Limit results
python keyword_cli.py search "vaccine" --limit 50
```

### Viewing Statistics

Show overall system statistics:
```bash
python keyword_cli.py stats
```

Output includes:
- Total keywords and episodes
- Tagged vs untagged episodes
- Coverage percentage
- Category breakdown
- Top keywords by episode count

List all keywords with statistics:
```bash
python keyword_cli.py list --stats
```

Filter by category:
```bash
python keyword_cli.py list --category health --stats
```

### Episode Details

Show all keywords tagged on a specific episode:
```bash
python keyword_cli.py episode-keywords 123
```

This displays:
- All matched keywords
- Match counts and confidence scores
- Sample match contexts

### Managing Keywords

Remove a keyword and all its tags:
```bash
python keyword_cli.py remove "vaccine"
```

Reprocess a keyword with new settings:
```bash
python keyword_cli.py reprocess "vaccine"
```

## Configuration

### Fuzzy Matching Threshold

The fuzzy matching threshold determines how similar text must be to match:
- **100**: Exact matches only
- **90-99**: Very similar (minor typos)
- **85-89**: Similar (default - handles transcription errors well)
- **80-84**: Moderately similar (more lenient)
- **<80**: Very lenient (may have false positives)

Example with custom threshold:
```bash
python keyword_cli.py add "vaccine" --fuzzy-threshold 90
```

### Processing Modes

**Incremental mode** (default):
- Only processes episodes not yet tagged with the given keywords
- Fast for adding new keywords or processing new episodes
- Recommended for regular use

**Full scan mode**:
- Processes all transcribed episodes
- Use when you want to reprocess with different settings
- Use `--full-scan` flag

### Database and Transcript Paths

Specify custom paths:
```bash
python keyword_cli.py --db /path/to/db.db --transcripts /path/to/transcripts search "vaccine"
```

## Python API

You can also use the system programmatically:

```python
from keyword_processor import KeywordProcessor
from keyword_database import KeywordDatabase

# Initialize
processor = KeywordProcessor(
    db_path="data/podcast_metadata.db",
    transcript_dir="data/transcripts",
    fuzzy_threshold=85.0
)

# Add and process keywords
keywords = ["vaccine", "vaccination", "immunization"]
stats = processor.process_keywords(
    keywords=keywords,
    category="health",
    incremental=True
)

print(f"Processed {stats['processed']} episodes")
print(f"Found {stats['matched']} episodes with matches")

# Search for episodes
db = KeywordDatabase()
episodes = db.get_episodes_with_any_keyword(["vaccine", "COVID"])

for ep in episodes[:10]:
    print(f"{ep['title']} - {ep['matched_keywords']}")
```

## Performance Optimization

The system is designed for efficiency:

1. **Parallel Processing**: Uses thread pools (default: 4 workers)
2. **Batch Operations**: Database commits in batches (default: 100 episodes)
3. **Efficient Matching**:
   - Fast exact substring search first
   - Fuzzy matching only for non-exact matches
   - Word-level n-grams instead of character-level scanning
4. **Compressed Storage**: Transcripts stored as .jsonl.zst files
5. **Database Indices**: Optimized for common query patterns

### Tuning Performance

Adjust worker count and batch size:

```python
processor = KeywordProcessor(
    max_workers=8,      # More parallel processing
    batch_size=200      # Larger batches
)
```

Trade-offs:
- More workers = faster but more memory
- Larger batches = fewer DB commits but more memory
- Lower fuzzy threshold = faster but less accurate

## Database Schema

### keyword_tags

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| keyword | TEXT | Keyword (unique, lowercase) |
| category | TEXT | Optional grouping category |
| description | TEXT | Optional description |
| created_at | TEXT | ISO timestamp |
| metadata | TEXT | JSON for additional data |

### episode_keywords

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| episode_id | INTEGER | Foreign key to episodes |
| keyword_tag_id | INTEGER | Foreign key to keyword_tags |
| match_count | INTEGER | Number of matches found |
| confidence_score | REAL | Average similarity (0-100) |
| matched_positions | TEXT | JSON array of match details |
| created_at | TEXT | ISO timestamp |
| metadata | TEXT | JSON for additional data |

**Constraints:**
- Unique(episode_id, keyword_tag_id) - prevents duplicate tags
- Foreign keys with CASCADE delete

**Indices:**
- `idx_episode_keywords_episode` on `episode_id`
- `idx_episode_keywords_keyword` on `keyword_tag_id`
- `idx_keyword_tags_keyword` on `keyword`

## Example Workflows

### Initial Setup for Misinformation Detection

```bash
# 1. Define keywords for different misinformation categories
cat > vaccine_misinfo.txt << EOF
vaccine
vaccination
immunization
antivax
anti-vax
vaccine safety
vaccine injury
EOF

cat > covid_topics.txt << EOF
COVID-19
COVID
coronavirus
pandemic
lockdown
mask
EOF

# 2. Process keywords
python keyword_cli.py add-file vaccine_misinfo.txt --category vaccines
python keyword_cli.py add-file covid_topics.txt --category covid

# 3. View results
python keyword_cli.py stats

# 4. Find episodes discussing both vaccines and COVID
python keyword_cli.py search "vaccine" "COVID" --logic all --format csv --output results.csv
```

### Adding New Keywords to Existing System

```bash
# Add new keywords - only untagged episodes will be processed
python keyword_cli.py add "delta variant" "omicron" "booster" --category covid

# Check statistics
python keyword_cli.py stats
```

### Researching Specific Topics

```bash
# Find all episodes mentioning vaccine safety
python keyword_cli.py search "vaccine safety" "vaccine injury" --format json --output vaccine_safety.json

# View details for a specific episode
python keyword_cli.py episode-keywords 42
```

### Cleaning Up

```bash
# Remove a keyword that's too broad
python keyword_cli.py remove "health"

# Reprocess with stricter threshold
python keyword_cli.py add "COVID" --fuzzy-threshold 95 --full-scan
```

## Troubleshooting

### "rapidfuzz not available" warning

Install rapidfuzz:
```bash
pip install rapidfuzz>=3.0.0
```

Without rapidfuzz, the system falls back to exact matching only.

### "No episodes found"

Make sure you have:
1. Downloaded podcasts: `python main.py --phase1 --phase2`
2. Transcribed episodes: `python main.py --phase3`
3. Episodes in status 'transcribed' in the database

### Slow processing

Try:
1. Increasing `--fuzzy-threshold` (less fuzzy matching = faster)
2. Using more workers in the Python API
3. Processing smaller batches of keywords at a time
4. Using incremental mode instead of full scans

### High memory usage

Reduce:
1. `max_workers` parameter (fewer parallel episodes)
2. `batch_size` parameter (more frequent DB commits)
3. Number of keywords processed at once

## Future Enhancements

Potential improvements:
- [ ] GPU-accelerated fuzzy matching for very large datasets
- [ ] Semantic similarity search using embeddings
- [ ] Web UI for keyword management
- [ ] Automated keyword extraction from episode clusters
- [ ] Multi-language support
- [ ] Temporal analysis (keyword trends over time)
- [ ] Co-occurrence analysis (keywords that appear together)

## License

Same as the parent project.
