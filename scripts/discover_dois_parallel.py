#!/usr/bin/env python3
"""
discover_dois_parallel.py

PARALLEL version - Discover DOIs for papers using multiple sources with concurrent processing.

Uses ThreadPoolExecutor to process multiple papers simultaneously while respecting API rate limits.
Expected to be 5-10x faster than sequential version.

Author: Simon Dedman / Claude
Date: 2025-11-17
Version: 2.0 (Parallel)
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "outputs/papers_without_dois.csv"
OUTPUT_LOG = BASE_DIR / "logs/doi_discovery_log.csv"

# API endpoints
CROSSREF_API = "https://api.crossref.org/works"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"

# Parallel processing
MAX_WORKERS = 10  # Number of concurrent threads
BATCH_SIZE = 100  # Save progress every N papers

# Rate limiting (global across all threads)
REQUESTS_PER_SECOND = 4  # Conservative: 4 requests/second across all threads
MIN_REQUEST_INTERVAL = 1.0 / REQUESTS_PER_SECOND  # 0.25 seconds

# Matching thresholds
MIN_TITLE_SIMILARITY = 0.85
MIN_YEAR_DIFF = 2
REQUEST_TIMEOUT = 15

# User agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) SharkReferences/1.0 (mailto:your@email.com)"

# Thread-safe rate limiter
class RateLimiter:
    """Thread-safe rate limiter to ensure we don't exceed API limits."""
    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.lock = threading.Lock()
        self.last_request_time = 0

    def wait(self):
        """Wait if necessary to respect rate limit."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()

# Global rate limiter
rate_limiter = RateLimiter(MIN_REQUEST_INTERVAL)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / 'logs/doi_discovery_parallel.log')
    ]
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles using word overlap."""
    if not title1 or not title2:
        return 0.0

    t1_words = set(title1.lower().split())
    t2_words = set(title2.lower().split())

    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were'}
    t1_words = t1_words - stop_words
    t2_words = t2_words - stop_words

    if not t1_words or not t2_words:
        return 0.0

    intersection = len(t1_words & t2_words)
    union = len(t1_words | t2_words)

    return intersection / union if union > 0 else 0.0


def extract_first_author(authors_string: str) -> str:
    """Extract first author surname from authors string."""
    if pd.isna(authors_string) or not authors_string:
        return ""

    authors = authors_string.split('&')[0].split(',')[0].strip()
    authors = ''.join(char for char in authors if char.isalpha() or char.isspace())

    return authors.strip().split()[0] if authors.strip() else ""


# ============================================================================
# DOI DISCOVERY FUNCTIONS (with rate limiting)
# ============================================================================

def search_crossref(title: str, authors: str, year: Optional[int] = None) -> Optional[Dict]:
    """Search CrossRef API with rate limiting."""
    if not title:
        return None

    rate_limiter.wait()  # Thread-safe rate limiting

    query_parts = [title]
    first_author = extract_first_author(authors)
    if first_author:
        query_parts.append(first_author)

    query = ' '.join(query_parts)

    params = {
        'query': query,
        'rows': 5,
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
                for item in data['message']['items']:
                    found_title = item.get('title', [''])[0] if item.get('title') else ''
                    similarity = calculate_title_similarity(title, found_title)

                    if similarity < MIN_TITLE_SIMILARITY:
                        continue

                    if year:
                        pub_year = None
                        if item.get('published-print'):
                            pub_year = item['published-print'].get('date-parts', [[None]])[0][0]
                        elif item.get('published-online'):
                            pub_year = item['published-online'].get('date-parts', [[None]])[0][0]

                        if pub_year and abs(pub_year - year) > MIN_YEAR_DIFF:
                            continue

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
        logging.debug(f"CrossRef API error: {str(e)[:100]}")
        return None


def search_semantic_scholar(title: str, year: Optional[int] = None) -> Optional[Dict]:
    """Search Semantic Scholar API with rate limiting."""
    if not title:
        return None

    rate_limiter.wait()  # Thread-safe rate limiting

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
                    found_title = item.get('title', '')
                    similarity = calculate_title_similarity(title, found_title)

                    if similarity < MIN_TITLE_SIMILARITY:
                        continue

                    if year and item.get('year'):
                        if abs(item['year'] - year) > MIN_YEAR_DIFF:
                            continue

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
        logging.debug(f"Semantic Scholar API error: {str(e)[:100]}")
        return None


def discover_doi_for_paper(row: pd.Series) -> Dict:
    """
    Try to discover DOI for a single paper using multiple sources.
    This function will be called by multiple threads in parallel.
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

    # Try CrossRef first
    crossref_result = search_crossref(title, authors, year)
    if crossref_result:
        result.update(crossref_result)
        result['status'] = 'found'
        result['message'] = f'Found via CrossRef (similarity: {crossref_result["similarity"]:.2f})'
        return result

    # Try Semantic Scholar if CrossRef failed
    ss_result = search_semantic_scholar(title, year)
    if ss_result:
        result.update(ss_result)
        result['status'] = 'found'
        result['message'] = f'Found via Semantic Scholar (similarity: {ss_result["similarity"]:.2f})'
        return result

    result['status'] = 'not_found'
    result['message'] = 'DOI not found in any source'
    return result


# ============================================================================
# MAIN EXECUTION (Parallel)
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Discover DOIs for papers without them (PARALLEL)')
    parser.add_argument('--max-papers', type=int, help='Maximum papers to process (for testing)')
    parser.add_argument('--start-from', type=int, default=0, help='Start from this row number')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS, help=f'Number of parallel workers (default: {MAX_WORKERS})')
    parser.add_argument('--test', action='store_true', help='Test mode: process only 50 papers')

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
        df = df.head(50)
        logging.info("TEST MODE: Processing only 50 papers")
    elif args.max_papers:
        df = df.iloc[args.start_from:args.start_from + args.max_papers]
        logging.info(f"Processing papers {args.start_from} to {args.start_from + args.max_papers}")
    elif args.start_from > 0:
        df = df.iloc[args.start_from:]
        logging.info(f"Processing papers from {args.start_from} onwards")

    # Process papers in parallel
    results = []
    found_count = 0

    logging.info(f"\n{'='*80}")
    logging.info(f"PARALLEL DOI DISCOVERY")
    logging.info(f"{'='*80}")
    logging.info(f"Papers to process: {len(df):,}")
    logging.info(f"Parallel workers: {args.workers}")
    logging.info(f"Rate limit: {REQUESTS_PER_SECOND} requests/second")
    logging.info(f"Expected runtime: ~{len(df) / (REQUESTS_PER_SECOND * 60):.1f} minutes")
    logging.info(f"Log file: {OUTPUT_LOG}")
    logging.info(f"{'='*80}\n")

    start_time = time.time()

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        future_to_row = {
            executor.submit(discover_doi_for_paper, row): idx
            for idx, row in df.iterrows()
        }

        # Process completed tasks with progress bar
        with tqdm(total=len(df), desc="Discovering DOIs") as pbar:
            for future in as_completed(future_to_row):
                result = future.result()
                results.append(result)

                if result['status'] == 'found':
                    found_count += 1
                    logging.info(f"  ✅ [{found_count}] Found DOI: {result['doi'][:40]}... (lit_id: {result['literature_id']})")

                pbar.update(1)

                # Save progress every BATCH_SIZE papers
                if len(results) % BATCH_SIZE == 0:
                    results_df = pd.DataFrame(results)
                    results_df.to_csv(OUTPUT_LOG, index=False)
                    elapsed = time.time() - start_time
                    rate = len(results) / elapsed
                    eta = (len(df) - len(results)) / rate if rate > 0 else 0
                    logging.info(f"  💾 Progress: {len(results)}/{len(df)} ({len(results)/len(df)*100:.1f}%) | Found: {found_count} | ETA: {eta/60:.1f}m")

    # Save final results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_LOG, index=False)

    # Calculate statistics
    elapsed_time = time.time() - start_time
    papers_per_second = len(results) / elapsed_time

    # Print summary
    print("\n" + "="*80)
    print("PARALLEL DOI DISCOVERY COMPLETE")
    print("="*80)
    print(f"\nTotal papers processed: {len(results):,}")
    print(f"DOIs found: {found_count:,} ({found_count/len(results)*100:.1f}%)")
    print(f"\nBreakdown by source:")
    print(results_df[results_df['status'] == 'found']['source'].value_counts())
    print(f"\nPerformance:")
    print(f"  Time elapsed: {elapsed_time/60:.1f} minutes")
    print(f"  Processing rate: {papers_per_second:.2f} papers/second")
    print(f"  Speedup vs sequential (~0.3 papers/s): {papers_per_second/0.3:.1f}x")
    print(f"\nResults saved to: {OUTPUT_LOG}")
    print("="*80)


if __name__ == "__main__":
    main()
