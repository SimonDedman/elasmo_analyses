#!/usr/bin/env python3
"""
find_noaa_dois_crossref.py

Find DOIs for NOAA Fishery Bulletin papers using CrossRef API.

CrossRef is more reliable than web scraping for DOI discovery.

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm
import logging
import requests
from urllib.parse import quote

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/noaa_fishery_bulletin_papers.csv"
OUTPUT_FILE = BASE_DIR / "outputs/noaa_fishery_bulletin_dois.csv"
LOG_FILE = BASE_DIR / "logs/noaa_crossref_doi_discovery.log"

# Rate limiting
API_DELAY = 1.0  # Be nice to CrossRef

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ============================================================================
# CROSSREF API
# ============================================================================

def search_crossref_for_doi(title: str, year: str, journal: str = "Fishery Bulletin") -> dict:
    """
    Search CrossRef API for DOI matching title and year.

    CrossRef API: https://api.crossref.org/works
    Query parameters:
        - query.title: search in titles
        - query.container-title: search in journal names
        - filter: year, type, etc.
    """
    try:
        # Clean title
        clean_title = title.strip().rstrip('.')

        # Build query
        base_url = "https://api.crossref.org/works"

        params = {
            'query.title': clean_title,
            'query.container-title': journal,
            'rows': 5  # Get top 5 results
        }

        # Add year filter if available
        if year and str(year) != 'nan':
            params['filter'] = f'from-pub-date:{int(float(year))},until-pub-date:{int(float(year))}'

        # Make request
        headers = {
            'User-Agent': 'SharkPaperDownloader/1.0 (mailto:research@example.com)'
        }

        response = requests.get(base_url, params=params, headers=headers, timeout=30)

        if response.status_code != 200:
            return {
                'found': False,
                'error': f'api_error_{response.status_code}'
            }

        data = response.json()

        if data['message']['total-results'] == 0:
            return {
                'found': False,
                'error': 'no_results'
            }

        # Check top results
        for item in data['message']['items']:
            result_title = item.get('title', [''])[0].lower() if item.get('title') else ''
            query_title = clean_title.lower()

            doi = item.get('DOI', '')
            logging.debug(f"  Checking: {doi} - {result_title[:60]}")

            # Check if titles match (fuzzy)
            # Remove punctuation and compare
            result_clean = ''.join(c for c in result_title if c.isalnum() or c.isspace())
            query_clean = ''.join(c for c in query_title if c.isalnum() or c.isspace())

            # Calculate similarity (simple word overlap)
            result_words = set(result_clean.split())
            query_words = set(query_clean.split())

            if len(query_words) == 0:
                logging.debug(f"    No query words")
                continue

            overlap = len(result_words & query_words) / len(query_words)
            logging.debug(f"    Overlap: {overlap:.1%} (threshold: 70%)")

            if overlap > 0.7:  # 70% word overlap
                # Verify it's a Fishery Bulletin DOI
                if doi.startswith('10.7755/FB.') or doi.startswith('10.7755/fb.'):
                    logging.info(f"  Found DOI: {doi} (overlap: {overlap:.1%})")
                    return {
                        'found': True,
                        'doi': doi.upper(),  # Normalize to uppercase
                        'match_score': overlap,
                        'result_title': result_title
                    }
                else:
                    logging.debug(f"    DOI doesn't match Fishery Bulletin pattern: {doi}")

        # No good matches
        return {
            'found': False,
            'error': 'no_good_match',
            'top_result': data['message']['items'][0].get('title', [''])[0] if data['message']['items'] else ''
        }

    except requests.exceptions.Timeout:
        return {'found': False, 'error': 'timeout'}
    except Exception as e:
        logging.error(f"Error searching CrossRef: {e}")
        return {'found': False, 'error': str(e)}


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Find DOIs using CrossRef API")
    parser.add_argument('--test', action='store_true', help="Test mode: 20 papers")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    args = parser.parse_args()

    print("=" * 80)
    print("NOAA FISHERY BULLETIN DOI DISCOVERY (CROSSREF)")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load papers
    if not INPUT_FILE.exists():
        print(f"\n❌ Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    print(f"\n📊 Loaded {len(df):,} Fishery Bulletin papers")

    # Apply limits
    if args.test:
        df = df.head(20)
        print(f"🧪 Test mode: processing {len(df)} papers")
    elif args.max_papers:
        df = df.head(args.max_papers)

    # Load existing results
    existing_results = []
    if OUTPUT_FILE.exists():
        existing_df = pd.read_csv(OUTPUT_FILE)
        existing_ids = set(existing_df['literature_id'].values)
        df = df[~df['literature_id'].isin(existing_ids)]
        print(f"✅ Skipping {len(existing_ids):,} already processed")
        print(f"📊 Remaining: {len(df):,}")
        existing_results = existing_df.to_dict('records')

    if len(df) == 0:
        print("\n✅ All papers already processed!")
        # Still show summary
        if existing_results:
            results_df = pd.DataFrame(existing_results)
            found = len(results_df[results_df['status'] == 'found'])
            print(f"\n📊 Total DOIs found: {found:,} / {len(results_df):,}")
        return

    print("\n" + "=" * 80)
    print(f"SEARCHING CROSSREF FOR {len(df):,} DOIS")
    print("=" * 80)

    results = existing_results.copy()

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Searching"):
        literature_id = row['literature_id']
        title = row['title']
        year = row.get('year', '')

        result = {
            'literature_id': literature_id,
            'title': title,
            'authors': row.get('authors', ''),
            'year': year,
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Search CrossRef
            doi_info = search_crossref_for_doi(title, str(year))
            time.sleep(API_DELAY)

            if doi_info.get('found'):
                result['doi'] = doi_info['doi']
                result['status'] = 'found'
                result['match_score'] = doi_info.get('match_score', '')
                result['result_title'] = doi_info.get('result_title', '')
            else:
                result['status'] = 'not_found'
                result['error'] = doi_info.get('error', '')
                result['top_result'] = doi_info.get('top_result', '')

            results.append(result)

        except Exception as e:
            logging.error(f"Error processing {literature_id}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            results.append(result)

        # Save progress every 10 papers
        if len(results) % 10 == 0:
            results_df = pd.DataFrame(results)
            results_df.to_csv(OUTPUT_FILE, index=False)
            logging.info(f"Progress saved: {len(results)} papers processed")

    # Final save
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("DOI DISCOVERY SUMMARY")
    print("=" * 80)

    found = len(results_df[results_df['status'] == 'found'])
    not_found = len(results_df[results_df['status'] == 'not_found'])

    print(f"\n✅ DOIs found: {found:,}")
    print(f"❌ Not found: {not_found:,}")
    if len(results) > 0:
        print(f"📈 Success rate: {found/len(results)*100:.1f}%")

    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status:30s}: {len(group):>5,}")

    if found > 0:
        print(f"\n📝 Sample DOIs found:")
        sample = results_df[results_df['status'] == 'found'].head(5)
        for _, row in sample.iterrows():
            print(f"  {row['doi']:30s} - {row['title'][:50]}...")

    print(f"\n📄 Results saved to: {OUTPUT_FILE}")
    print(f"📋 Log file: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
