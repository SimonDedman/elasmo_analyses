#!/usr/bin/env python3
"""
hunt_dois.py

Hunt for DOIs for papers that don't have them in the database.
Many papers may have DOIs added by journals after original publication.

Strategies:
1. CrossRef API - search by title/author
2. DataCite API - search by title
3. Journal website scraping (for common journals)
4. Google Scholar scraping (careful with rate limits)

Author: Simon Dedman / Claude
Date: 2025-10-22
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
import re
from urllib.parse import quote
from tqdm import tqdm
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "outputs/papers_without_doi.csv"
OUTPUT_CSV = BASE_DIR / "outputs/papers_with_found_dois.csv"
LOG_FILE = BASE_DIR / "logs/doi_hunting_log.csv"

# Rate limiting
DELAY_BETWEEN_REQUESTS = 1.0  # seconds
REQUEST_TIMEOUT = 10

# User agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) SharkResearchBot/1.0 (mailto:simondedman@gmail.com)"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# ============================================================================
# DOI HUNTING FUNCTIONS
# ============================================================================

def clean_title_for_search(title):
    """Clean title for searching."""
    if not title:
        return ""
    # Remove special characters but keep spaces
    title = re.sub(r'[^\w\s-]', '', str(title))
    # Remove extra whitespace
    title = ' '.join(title.split())
    return title.strip()


def search_crossref(title, authors=None, year=None):
    """
    Search CrossRef API for DOI.

    CrossRef is the most comprehensive DOI database.
    API docs: https://github.com/CrossRef/rest-api-doc
    """
    if not title:
        return None

    try:
        # Build query
        query = clean_title_for_search(title)

        # CrossRef API endpoint
        url = "https://api.crossref.org/works"
        params = {
            'query.title': query,
            'rows': 5  # Get top 5 results
        }

        if year:
            params['filter'] = f'from-pub-date:{year},until-pub-date:{year}'

        headers = {'User-Agent': USER_AGENT}

        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            items = data.get('message', {}).get('items', [])

            if not items:
                return None

            # Check each result for title match
            for item in items:
                result_title = item.get('title', [''])[0].lower()
                query_lower = query.lower()

                # Fuzzy match: check if 70% of query words are in result
                query_words = set(query_lower.split())
                result_words = set(result_title.split())

                if len(query_words) > 0:
                    match_ratio = len(query_words & result_words) / len(query_words)

                    if match_ratio >= 0.7:
                        doi = item.get('DOI')
                        if doi:
                            return {
                                'doi': doi,
                                'source': 'crossref',
                                'confidence': match_ratio,
                                'matched_title': result_title
                            }

        return None

    except Exception as e:
        logging.debug(f"CrossRef search error: {e}")
        return None


def search_datacite(title, year=None):
    """
    Search DataCite API for DOI.

    DataCite specializes in research data DOIs.
    API docs: https://support.datacite.org/docs/api
    """
    if not title:
        return None

    try:
        query = clean_title_for_search(title)

        url = "https://api.datacite.org/dois"
        params = {
            'query': query,
            'page[size]': 5
        }

        if year:
            params['published'] = year

        headers = {'User-Agent': USER_AGENT}

        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            items = data.get('data', [])

            for item in items:
                attributes = item.get('attributes', {})
                result_title = attributes.get('titles', [{}])[0].get('title', '').lower()
                query_lower = query.lower()

                # Fuzzy match
                query_words = set(query_lower.split())
                result_words = set(result_title.split())

                if len(query_words) > 0:
                    match_ratio = len(query_words & result_words) / len(query_words)

                    if match_ratio >= 0.7:
                        doi = item.get('id')
                        if doi:
                            return {
                                'doi': doi,
                                'source': 'datacite',
                                'confidence': match_ratio,
                                'matched_title': result_title
                            }

        return None

    except Exception as e:
        logging.debug(f"DataCite search error: {e}")
        return None


def search_doi_from_url(pdf_url):
    """
    Extract DOI from URL if it contains one.
    Some pdf_url fields might have DOI links we missed.
    """
    if not pdf_url:
        return None

    patterns = [
        r'doi\.org/([0-9]{2}\.[0-9]{4,}/[^\s]+)',
        r'dx\.doi\.org/([0-9]{2}\.[0-9]{4,}/[^\s]+)',
        r'/doi/([0-9]{2}\.[0-9]{4,}/[^\s]+)',
        r'doi=([0-9]{2}\.[0-9]{4,}/[^\s]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, str(pdf_url))
        if match:
            doi = match.group(1).rstrip('.,;)]}>\'" ')
            return {
                'doi': doi,
                'source': 'url_extraction',
                'confidence': 1.0,
                'matched_title': 'N/A'
            }

    return None


def hunt_doi(row):
    """
    Hunt for DOI using multiple strategies.

    Args:
        row: DataFrame row with paper metadata

    Returns:
        dict with DOI result or None
    """
    title = row.get('title')
    authors = row.get('authors')
    year = row.get('year')
    pdf_url = row.get('pdf_url')

    # Strategy 1: Check URL for DOI (fast, high confidence)
    result = search_doi_from_url(pdf_url)
    if result:
        return result

    # Strategy 2: CrossRef search (most comprehensive)
    result = search_crossref(title, authors, year)
    if result and result.get('confidence', 0) >= 0.8:
        return result

    # Strategy 3: DataCite search (research data)
    result_datacite = search_datacite(title, year)
    if result_datacite and result_datacite.get('confidence', 0) >= 0.8:
        return result_datacite

    # Return best result even if confidence < 0.8
    if result:
        return result
    if result_datacite:
        return result_datacite

    return None


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hunt for DOIs in papers without them")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--min-year', type=int, help="Only process papers from this year onwards")
    parser.add_argument('--test', action='store_true', help="Test mode: only process 10 papers")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("DOI HUNTING")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load papers without DOIs
    print(f"\n📖 Loading papers without DOIs...")
    df = pd.read_csv(INPUT_CSV)
    print(f"✅ Loaded {len(df):,} papers")

    # Filter by year if requested
    if args.min_year:
        df = df[df['year'] >= args.min_year]
        print(f"📊 After year filter (>= {args.min_year}): {len(df):,}")

    # Sort by year (recent first - more likely to have DOIs)
    df = df.sort_values('year', ascending=False, na_position='last')

    # Limit if requested
    if args.test:
        df = df.head(10)
        print(f"🧪 Test mode: processing {len(df)} papers")
    elif args.max_papers:
        df = df.head(args.max_papers)
        print(f"📊 Limited to: {args.max_papers:,} papers")

    if len(df) == 0:
        print("\n⚠️  No papers to process")
        return

    # Hunt for DOIs
    print(f"\n{'=' * 80}")
    print(f"HUNTING DOIS FOR {len(df):,} PAPERS")
    print("=" * 80)

    results = []
    found_count = 0

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Hunting"):
        lit_id = row['literature_id']
        title = row.get('title', '')
        year = row.get('year')

        # Hunt for DOI
        result = hunt_doi(row)

        if result:
            found_count += 1
            results.append({
                'literature_id': lit_id,
                'title': title,
                'year': year,
                'found_doi': result['doi'],
                'source': result['source'],
                'confidence': result['confidence'],
                'matched_title': result['matched_title'],
                'timestamp': datetime.now().isoformat()
            })
        else:
            results.append({
                'literature_id': lit_id,
                'title': title,
                'year': year,
                'found_doi': None,
                'source': 'not_found',
                'confidence': 0.0,
                'matched_title': '',
                'timestamp': datetime.now().isoformat()
            })

        # Respectful delay
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save results
    results_df = pd.DataFrame(results)

    # Save log (all results)
    results_df.to_csv(LOG_FILE, index=False)

    # Save papers with found DOIs
    found_df = results_df[results_df['found_doi'].notna()]
    if len(found_df) > 0:
        found_df.to_csv(OUTPUT_CSV, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✅ DOIs found: {found_count:,}/{len(df):,}")
    print(f"📊 Success rate: {found_count/len(df)*100:.1f}%")

    if found_count > 0:
        print(f"\nBreakdown by source:")
        for source, group in found_df.groupby('source'):
            print(f"  {source:20s}: {len(group):>5,}")

        print(f"\nConfidence distribution:")
        print(f"  High (≥0.9):     {len(found_df[found_df['confidence'] >= 0.9]):>5,}")
        print(f"  Medium (0.7-0.9): {len(found_df[(found_df['confidence'] >= 0.7) & (found_df['confidence'] < 0.9)]):>5,}")
        print(f"  Low (<0.7):      {len(found_df[found_df['confidence'] < 0.7]):>5,}")

    print(f"\n📄 Full log: {LOG_FILE}")
    if found_count > 0:
        print(f"📄 Found DOIs: {OUTPUT_CSV}")
    print("=" * 80)


if __name__ == "__main__":
    main()
