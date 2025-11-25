#!/usr/bin/env python3
"""
find_noaa_dois.py

Discover DOIs for NOAA Fishery Bulletin papers by searching the NOAA website.

Strategy:
1. Search NOAA site with paper title and first author
2. Extract DOI from search results or article page
3. Save DOIs to CSV for use by downloader

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm
import logging
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/noaa_fishery_bulletin_papers.csv"
OUTPUT_FILE = BASE_DIR / "outputs/noaa_fishery_bulletin_dois.csv"
LOG_FILE = BASE_DIR / "logs/noaa_doi_discovery.log"

# Rate limiting
SEARCH_DELAY = 2.0

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
# HELPER FUNCTIONS
# ============================================================================

def extract_first_author(authors_str: str) -> str:
    """Extract first author's last name from author string."""
    if pd.isna(authors_str):
        return ""

    # Format: "LastName, F.I. & SecondAuthor, F.I. (YEAR)"
    # Extract first author's last name
    match = re.match(r'^([^,&]+)', authors_str)
    if match:
        return match.group(1).strip()
    return ""


def create_browser(headless: bool = True):
    """Create browser for searching."""
    options = uc.ChromeOptions()

    if headless:
        options.add_argument('--headless=new')

    driver = uc.Chrome(options=options)
    return driver


# ============================================================================
# DOI DISCOVERY
# ============================================================================

def search_noaa_for_doi(driver, title: str, first_author: str, year: str) -> dict:
    """
    Search NOAA website for paper and extract DOI.

    Strategy:
    1. Search with title and author
    2. Look for DOI in search results or article page
    3. Validate DOI format (10.7755/FB.*)
    """
    try:
        # Clean title for search (remove special characters)
        clean_title = re.sub(r'[^\w\s-]', '', title).strip()

        # Build search query
        search_query = f"{clean_title} {first_author}"
        search_url = f"https://spo.nmfs.noaa.gov/search/node/{search_query.replace(' ', '%20')}"

        logging.info(f"Searching: {search_query[:60]}...")

        driver.get(search_url)
        time.sleep(SEARCH_DELAY)

        # Check for Cloudflare
        if "Just a moment" in driver.title or "Cloudflare" in driver.title:
            return {'found': False, 'error': 'cloudflare_blocked'}

        page_source = driver.page_source

        # Look for DOI in page
        # NOAA Fishery Bulletin DOI format: 10.7755/FB.{volume}.{issue}.{article}
        doi_matches = re.findall(r'10\.7755/FB\.\d+\.\d+\.\d+', page_source)

        if doi_matches:
            # Return first matching DOI
            doi = doi_matches[0]
            logging.info(f"  Found DOI: {doi}")
            return {
                'found': True,
                'doi': doi,
                'search_url': search_url
            }

        # Alternative: Look for article links
        article_links = re.findall(r'href="(/content/[^"]+)"', page_source)

        if article_links:
            # Navigate to first article result
            article_url = f"https://spo.nmfs.noaa.gov{article_links[0]}"
            logging.info(f"  Checking article page: {article_url[:60]}...")

            driver.get(article_url)
            time.sleep(SEARCH_DELAY)

            # Look for DOI on article page
            page_source = driver.page_source
            doi_matches = re.findall(r'10\.7755/FB\.\d+\.\d+\.\d+', page_source)

            if doi_matches:
                doi = doi_matches[0]
                logging.info(f"  Found DOI on article page: {doi}")
                return {
                    'found': True,
                    'doi': doi,
                    'article_url': article_url,
                    'search_url': search_url
                }

        # Try Google Scholar search as fallback
        # Search: "title" "fishery bulletin" site:doi.org
        google_query = f'"{clean_title[:50]}" "fishery bulletin" site:doi.org'
        google_url = f"https://scholar.google.com/scholar?q={google_query.replace(' ', '+')}"

        logging.info(f"  Trying Google Scholar...")
        driver.get(google_url)
        time.sleep(SEARCH_DELAY)

        page_source = driver.page_source
        doi_matches = re.findall(r'10\.7755/FB\.\d+\.\d+\.\d+', page_source)

        if doi_matches:
            doi = doi_matches[0]
            logging.info(f"  Found DOI via Google Scholar: {doi}")
            return {
                'found': True,
                'doi': doi,
                'method': 'google_scholar',
                'search_url': google_url
            }

        logging.warning(f"  No DOI found")
        return {
            'found': False,
            'error': 'no_doi_in_results',
            'search_url': search_url
        }

    except Exception as e:
        logging.error(f"Error searching for DOI: {e}")
        return {
            'found': False,
            'error': str(e)
        }


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Find DOIs for NOAA Fishery Bulletin papers")
    parser.add_argument('--test', action='store_true', help="Test mode: 20 papers")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--headless', action='store_true', default=True, help="Run browser in headless mode")
    args = parser.parse_args()

    print("=" * 80)
    print("NOAA FISHERY BULLETIN DOI DISCOVERY")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load papers
    if not INPUT_FILE.exists():
        print(f"\n❌ Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    print(f"\n📊 Loaded {len(df):,} Fishery Bulletin papers")

    # Extract first author
    df['first_author'] = df['authors'].apply(extract_first_author)

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
        return

    # Initialize browser
    print(f"\n🌐 Starting Chrome browser...")
    driver = create_browser(headless=args.headless)

    try:
        print("\n" + "=" * 80)
        print(f"SEARCHING FOR {len(df):,} DOIS")
        print("=" * 80)

        results = existing_results.copy()

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Searching"):
            literature_id = row['literature_id']
            title = row['title']
            first_author = row['first_author']
            year = row.get('year', '')

            result = {
                'literature_id': literature_id,
                'title': title,
                'authors': row['authors'],
                'year': year,
                'timestamp': datetime.now().isoformat()
            }

            try:
                # Search for DOI
                doi_info = search_noaa_for_doi(driver, title, first_author, str(year))

                if doi_info.get('found'):
                    result['doi'] = doi_info['doi']
                    result['status'] = 'found'
                    result['method'] = doi_info.get('method', 'noaa_search')
                    result['search_url'] = doi_info.get('search_url', '')
                else:
                    result['status'] = 'not_found'
                    result['error'] = doi_info.get('error', '')
                    result['search_url'] = doi_info.get('search_url', '')

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

        print(f"\n📄 Results saved to: {OUTPUT_FILE}")
        print(f"📋 Log file: {LOG_FILE}")
        print("=" * 80)

    finally:
        driver.quit()
        print(f"\n🌐 Browser closed")


if __name__ == "__main__":
    main()
