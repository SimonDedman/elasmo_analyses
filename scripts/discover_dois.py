#!/usr/bin/env python3
"""
discover_dois.py

Discover DOIs for papers that lack them using multiple sources:
1. CrossRef API (title + author search)
2. Semantic Scholar API (title search)
3. DOI.org resolution (if partial DOI exists)

Author: Simon Dedman / Claude
Date: 2025-11-17
Version: 1.0
"""

import pandas as pd
import requests
import time
import logging
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import argparse
from typing import Optional, Dict, List
from urllib.parse import quote

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "outputs/papers_without_dois.csv"
OUTPUT_LOG = BASE_DIR / "logs/doi_discovery_log.csv"
UPDATED_DATABASE = BASE_DIR / "outputs/literature_review_with_dois.parquet"

# API endpoints
CROSSREF_API = "https://api.crossref.org/works"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"

# Rate limiting
CROSSREF_DELAY = 1.0  # seconds between requests (polite = 1s)
SEMANTIC_SCHOLAR_DELAY = 1.5  # seconds
REQUEST_TIMEOUT = 15  # seconds

# Matching thresholds
MIN_TITLE_SIMILARITY = 0.85  # Minimum similarity to consider a match
MIN_YEAR_DIFF = 2  # Maximum year difference to accept

# User agents
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) SharkReferences/1.0 (mailto:your@email.com)"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / 'logs/doi_discovery.log')
    ]
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two titles using simple word overlap.
    Returns value between 0 and 1.
    """
    if not title1 or not title2:
        return 0.0

    # Normalize titles
    t1_words = set(title1.lower().split())
    t2_words = set(title2.lower().split())

    # Remove common words that don't add meaning
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were'}
    t1_words = t1_words - stop_words
    t2_words = t2_words - stop_words

    if not t1_words or not t2_words:
        return 0.0

    # Calculate Jaccard similarity
    intersection = len(t1_words & t2_words)
    union = len(t1_words | t2_words)

    return intersection / union if union > 0 else 0.0


def extract_first_author(authors_string: str) -> str:
    """Extract first author surname from authors string."""
    if pd.isna(authors_string) or not authors_string:
        return ""

    # Handle different formats: "Smith, J. & Jones, K." or "Smith J, Jones K"
    authors = authors_string.split('&')[0].split(',')[0].strip()

    # Remove initials and other punctuation
    authors = ''.join(char for char in authors if char.isalpha() or char.isspace())

    return authors.strip().split()[0] if authors.strip() else ""


# ============================================================================
# DOI DISCOVERY FUNCTIONS
# ============================================================================

def search_crossref(title: str, authors: str, year: Optional[int] = None) -> Optional[Dict]:
    """
    Search CrossRef API for a DOI using title, author, and optionally year.

    Returns dict with doi, title, score, year if found, None otherwise.
    """
    if not title:
        return None

    # Build query
    query_parts = [title]
    first_author = extract_first_author(authors)
    if first_author:
        query_parts.append(first_author)

    query = ' '.join(query_parts)

    params = {
        'query': query,
        'rows': 5,  # Get top 5 results
        'select': 'DOI,title,author,published-print,score'
    }

    headers = {'User-Agent': USER_AGENT}

    try:
        response = requests.get(
            CROSSREF_API,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()

            if data.get('message', {}).get('items'):
                # Check each result for best match
                for item in data['message']['items']:
                    # Check title similarity
                    found_title = item.get('title', [''])[0] if item.get('title') else ''
                    similarity = calculate_title_similarity(title, found_title)

                    if similarity < MIN_TITLE_SIMILARITY:
                        continue

                    # Check year if provided
                    if year:
                        pub_year = None
                        if item.get('published-print'):
                            pub_year = item['published-print'].get('date-parts', [[None]])[0][0]
                        elif item.get('published-online'):
                            pub_year = item['published-online'].get('date-parts', [[None]])[0][0]

                        if pub_year and abs(pub_year - year) > MIN_YEAR_DIFF:
                            continue

                    # Found a good match
                    return {
                        'doi': item.get('DOI'),
                        'matched_title': found_title,
                        'similarity': similarity,
                        'score': item.get('score', 0),
                        'year': pub_year if 'pub_year' in locals() else None,
                        'source': 'crossref'
                    }

        return None

    except Exception as e:
        logging.warning(f"CrossRef API error: {str(e)[:100]}")
        return None


def search_semantic_scholar(title: str, year: Optional[int] = None) -> Optional[Dict]:
    """
    Search Semantic Scholar API for a DOI using title.

    Returns dict with doi, title, similarity if found, None otherwise.
    """
    if not title:
        return None

    params = {
        'query': title,
        'limit': 5,
        'fields': 'title,year,externalIds'
    }

    headers = {'User-Agent': USER_AGENT}

    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_API,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()

            if data.get('data'):
                for item in data['data']:
                    # Check title similarity
                    found_title = item.get('title', '')
                    similarity = calculate_title_similarity(title, found_title)

                    if similarity < MIN_TITLE_SIMILARITY:
                        continue

                    # Check year if provided
                    if year and item.get('year'):
                        if abs(item['year'] - year) > MIN_YEAR_DIFF:
                            continue

                    # Check if DOI exists
                    doi = item.get('externalIds', {}).get('DOI')
                    if doi:
                        return {
                            'doi': doi,
                            'matched_title': found_title,
                            'similarity': similarity,
                            'year': item.get('year'),
                            'source': 'semantic_scholar'
                        }

        return None

    except Exception as e:
        logging.warning(f"Semantic Scholar API error: {str(e)[:100]}")
        return None


def discover_doi_for_paper(row: pd.Series) -> Dict:
    """
    Try to discover DOI for a single paper using multiple sources.

    Returns dict with discovery results.
    """
    result = {
        'literature_id': row.get('literature_id'),
        'original_title': row.get('title'),
        'year': row.get('year'),
        'doi': None,
        'matched_title': None,
        'similarity': 0.0,
        'source': None,
        'status': 'not_found',
        'message': '',
        'timestamp': datetime.now().isoformat()
    }

    title = row.get('title', '')
    authors = row.get('authors', '')
    year = row.get('year')

    if not title:
        result['status'] = 'error'
        result['message'] = 'No title provided'
        return result

    # Try CrossRef first (most comprehensive)
    logging.debug(f"Searching CrossRef for: {title[:60]}...")
    crossref_result = search_crossref(title, authors, year)

    if crossref_result:
        result.update(crossref_result)
        result['status'] = 'found'
        result['message'] = f'Found via CrossRef (similarity: {crossref_result["similarity"]:.2f})'
        return result

    time.sleep(CROSSREF_DELAY)

    # Try Semantic Scholar if CrossRef failed
    logging.debug(f"Searching Semantic Scholar for: {title[:60]}...")
    ss_result = search_semantic_scholar(title, year)

    if ss_result:
        result.update(ss_result)
        result['status'] = 'found'
        result['message'] = f'Found via Semantic Scholar (similarity: {ss_result["similarity"]:.2f})'
        return result

    time.sleep(SEMANTIC_SCHOLAR_DELAY)

    # Nothing found
    result['status'] = 'not_found'
    result['message'] = 'DOI not found in any source'
    return result


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Discover DOIs for papers without them')
    parser.add_argument('--max-papers', type=int, help='Maximum papers to process (for testing)')
    parser.add_argument('--start-from', type=int, default=0, help='Start from this row number')
    parser.add_argument('--test', action='store_true', help='Test mode: process only 10 papers')

    args = parser.parse_args()

    # Load papers without DOIs
    if not INPUT_CSV.exists():
        logging.error(f"Input file not found: {INPUT_CSV}")
        logging.error("Please run the extraction script first to create papers_without_dois.csv")
        return

    df = pd.read_csv(INPUT_CSV)
    logging.info(f"Loaded {len(df):,} papers without DOIs")

    # Apply filters
    if args.test:
        df = df.head(10)
        logging.info("TEST MODE: Processing only 10 papers")
    elif args.max_papers:
        df = df.iloc[args.start_from:args.start_from + args.max_papers]
        logging.info(f"Processing papers {args.start_from} to {args.start_from + args.max_papers}")
    elif args.start_from > 0:
        df = df.iloc[args.start_from:]
        logging.info(f"Processing papers from {args.start_from} onwards")

    # Process papers
    results = []
    found_count = 0

    logging.info(f"\nStarting DOI discovery for {len(df)} papers...")
    logging.info(f"Log file: {OUTPUT_LOG}")

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Discovering DOIs"):
        result = discover_doi_for_paper(row)
        results.append(result)

        if result['status'] == 'found':
            found_count += 1
            logging.info(f"  ✅ [{found_count}] Found DOI for lit_id {result['literature_id']}: {result['doi']}")

        # Save progress every 100 papers
        if len(results) % 100 == 0:
            results_df = pd.DataFrame(results)
            results_df.to_csv(OUTPUT_LOG, index=False)
            logging.info(f"  💾 Progress saved: {len(results)} processed, {found_count} found")

    # Save final results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_LOG, index=False)

    # Print summary
    print("\n" + "="*80)
    print("DOI DISCOVERY COMPLETE")
    print("="*80)
    print(f"\nTotal papers processed: {len(results):,}")
    print(f"DOIs found: {found_count:,} ({found_count/len(results)*100:.1f}%)")
    print(f"\nBreakdown by source:")
    print(results_df['source'].value_counts())
    print(f"\nResults saved to: {OUTPUT_LOG}")
    print("="*80)


if __name__ == "__main__":
    main()
