#!/usr/bin/env python3
"""
download_google_scholar.py

Search Google Scholar for PDF links and download papers without DOIs or failed downloads.

Strategy:
1. Search Google Scholar with title + authors
2. Extract PDF links from search results
3. Download PDFs (prefer institutional repos, author uploads)
4. Respectful rate limiting to avoid blocking

Author: Simon Dedman / Claude
Date: 2025-11-19
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm
import logging
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import random

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
PAPERS_FILE = BASE_DIR / "outputs/papers_without_dois.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/google_scholar_download_log.csv"

# Google Scholar configuration
SCHOLAR_BASE_URL = "https://scholar.google.com/scholar"
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

# Rate limiting (IMPORTANT: Be respectful to avoid IP bans)
MIN_DELAY = 3.0  # Minimum delay between requests
MAX_DELAY = 8.0  # Maximum delay (randomized)
REQUEST_TIMEOUT = 20
MAX_RETRIES = 2

# PDF download settings
MAX_PDF_SIZE_MB = 50  # Skip PDFs larger than this
MIN_PDF_SIZE_KB = 10  # Skip PDFs smaller than this (likely not real papers)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/google_scholar.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# GOOGLE SCHOLAR FUNCTIONS
# ============================================================================

def build_search_query(title: str, authors: str = "") -> str:
    """Build Google Scholar search query."""
    # Clean title
    title = re.sub(r'[^\w\s-]', '', title).strip()

    # If authors provided, extract first author's last name
    first_author = ""
    if authors and isinstance(authors, str):
        # Try to extract last name from "Lastname, Firstname" format
        author_parts = authors.split(',')[0].strip()
        if author_parts:
            first_author = author_parts.split()[-1]  # Get last word (last name)

    # Build query
    if first_author:
        query = f'"{title}" author:"{first_author}"'
    else:
        query = f'"{title}"'

    return query


def search_google_scholar(query: str, session: requests.Session) -> list:
    """
    Search Google Scholar and extract PDF links.

    Returns list of dicts with:
    - pdf_url: Direct link to PDF
    - pdf_source: Source of PDF (e.g., 'researchgate.net', 'arxiv.org')
    - title: Matched title from Scholar
    """

    try:
        params = {
            'q': query,
            'hl': 'en',
            'as_sdt': '0,5',  # Include patents and citations
        }

        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = session.get(
            SCHOLAR_BASE_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 429:
            logging.warning("Rate limited by Google Scholar - waiting longer")
            time.sleep(60)  # Wait 1 minute if rate limited
            return []

        if response.status_code != 200:
            logging.warning(f"Scholar returned status {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        # Check for CAPTCHA
        if 'unusual traffic' in response.text.lower():
            logging.error("CAPTCHA detected - stopping to avoid ban")
            return []

        # Extract PDF links
        pdf_links = []

        # Method 1: Look for [PDF] links (direct PDF links from Scholar)
        for link in soup.find_all('a'):
            if link.get_text(strip=True) == '[PDF]':
                pdf_url = link.get('href')
                if pdf_url:
                    # Extract source domain
                    source = re.search(r'https?://([^/]+)', pdf_url)
                    source_domain = source.group(1) if source else 'unknown'

                    pdf_links.append({
                        'pdf_url': pdf_url,
                        'pdf_source': source_domain,
                        'method': 'direct_pdf_link'
                    })

        # Method 2: Look for links to known repositories
        repo_domains = [
            'researchgate.net',
            'academia.edu',
            'arxiv.org',
            'biorxiv.org',
            'zenodo.org',
            'figshare.com',
            'osf.io',
            'ssrn.com'
        ]

        for result in soup.find_all('div', class_='gs_r'):
            links = result.find_all('a')
            for link in links:
                href = link.get('href', '')
                for domain in repo_domains:
                    if domain in href and 'pdf' in href.lower():
                        pdf_links.append({
                            'pdf_url': href,
                            'pdf_source': domain,
                            'method': 'repository_link'
                        })

        return pdf_links[:3]  # Return top 3 results

    except Exception as e:
        logging.error(f"Error searching Scholar: {e}")
        return []


def download_pdf_from_url(url: str, literature_id: str, title: str) -> dict:
    """Download PDF from URL."""

    # Construct filename
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
    final_filename = f"{literature_id}_{safe_title}_GS.pdf"
    final_path = OUTPUT_DIR / final_filename

    # Check if already exists
    if final_path.exists():
        return {
            'status': 'already_exists',
            'filename': final_filename,
            'size_bytes': final_path.stat().st_size
        }

    try:
        logging.debug(f"Downloading from: {url}")

        headers = {
            'User-Agent': random.choice(USER_AGENTS)
        }

        # Stream download to check size first
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)

        # Check content type
        content_type = response.headers.get('Content-Type', '')

        if 'application/pdf' not in content_type and 'pdf' not in url.lower():
            logging.debug(f"Not a PDF: {content_type}")
            return {'status': 'not_pdf', 'content_type': content_type}

        # Check file size
        content_length = response.headers.get('Content-Length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > MAX_PDF_SIZE_MB:
                logging.warning(f"PDF too large: {size_mb:.1f} MB")
                return {'status': 'too_large', 'size_mb': size_mb}

        # Download PDF
        with open(final_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = final_path.stat().st_size

        # Verify it's a real PDF
        if file_size < MIN_PDF_SIZE_KB * 1024:
            final_path.unlink()
            return {'status': 'too_small', 'size_bytes': file_size}

        with open(final_path, 'rb') as f:
            if f.read(4) != b'%PDF':
                final_path.unlink()
                return {'status': 'invalid_pdf'}

        logging.info(f"Downloaded: {final_filename} ({file_size:,} bytes)")

        return {
            'status': 'success',
            'filename': final_filename,
            'size_bytes': file_size,
            'download_url': url
        }

    except requests.exceptions.Timeout:
        return {'status': 'timeout'}
    except Exception as e:
        logging.error(f"Download error: {e}")
        return {'status': 'error', 'error_message': str(e)}


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download PDFs via Google Scholar search")
    parser.add_argument('--test', action='store_true', help="Test mode: 20 papers only")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    args = parser.parse_args()

    print("=" * 80)
    print("GOOGLE SCHOLAR PDF DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    print("⚠️  Using respectful rate limiting to avoid IP bans")
    print(f"   Delay between requests: {MIN_DELAY}-{MAX_DELAY} seconds")
    print("")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load papers database
    if not PAPERS_FILE.exists():
        print(f"❌ Papers file not found: {PAPERS_FILE}")
        return

    df = pd.read_csv(PAPERS_FILE)

    # Filter for papers without PDFs
    # Assume papers without 'pdf_path' or with empty 'pdf_path' need downloading
    if 'pdf_path' in df.columns:
        df = df[df['pdf_path'].isna() | (df['pdf_path'] == '')]

    print(f"📊 Loaded {len(df):,} papers without PDFs")

    # Apply limits
    if args.test:
        df = df.head(20)
        print(f"🧪 Test mode: processing {len(df)} papers")
    elif args.max_papers:
        df = df.head(args.max_papers)

    # Load existing results
    existing_results = []
    if LOG_FILE.exists():
        existing_df = pd.read_csv(LOG_FILE)
        existing_ids = set(existing_df['literature_id'].astype(str))
        df = df[~df['literature_id'].astype(str).isin(existing_ids)]
        print(f"✅ Skipping {len(existing_ids):,} already processed")
        print(f"📊 Remaining: {len(df):,}")
        existing_results = existing_df.to_dict('records')

    if len(df) == 0:
        print("\n✅ All papers already processed!")
        return

    print("\n" + "=" * 80)
    print(f"SEARCHING GOOGLE SCHOLAR FOR {len(df):,} PAPERS")
    print("=" * 80)
    print("")

    # Create session for connection reuse
    session = requests.Session()

    results = existing_results.copy()
    pdfs_found = 0
    pdfs_downloaded = 0

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        literature_id = row['literature_id']
        title = row.get('title', '')
        authors = row.get('authors', '')

        if not title or pd.isna(title):
            continue

        result = {
            'literature_id': literature_id,
            'title': title,
            'authors': authors,
            'timestamp': datetime.now().isoformat()
        }

        # Build search query
        query = build_search_query(title, authors)
        result['search_query'] = query

        # Search Google Scholar
        pdf_links = search_google_scholar(query, session)

        result['pdf_links_found'] = len(pdf_links)

        if pdf_links:
            pdfs_found += 1

            # Try each PDF link until one succeeds
            for pdf_link in pdf_links:
                download_result = download_pdf_from_url(
                    pdf_link['pdf_url'],
                    str(literature_id),
                    title
                )

                if download_result.get('status') == 'success':
                    result.update(download_result)
                    result['pdf_source'] = pdf_link['pdf_source']
                    pdfs_downloaded += 1
                    break
            else:
                # None succeeded
                result['status'] = 'found_but_failed_download'
                result['last_attempt_url'] = pdf_links[0]['pdf_url']
        else:
            result['status'] = 'no_pdf_found'

        results.append(result)

        # Respectful rate limiting
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        # Save progress every 10 papers
        if len(results) % 10 == 0:
            results_df = pd.DataFrame(results)
            results_df.to_csv(LOG_FILE, index=False)
            logging.info(f"Progress saved: {len(results)} papers processed, {pdfs_downloaded} PDFs downloaded")

    # Final save
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("GOOGLE SCHOLAR DOWNLOAD SUMMARY")
    print("=" * 80)

    total_processed = len(results_df)
    pdfs_success = len(results_df[results_df['status'] == 'success'])
    pdfs_already = len(results_df[results_df['status'] == 'already_exists'])
    total_pdfs = pdfs_success + pdfs_already

    print(f"\n📊 Papers processed: {total_processed:,}")
    print(f"🔍 PDF links found: {pdfs_found:,} ({pdfs_found/total_processed*100:.1f}%)")
    print(f"📥 New PDFs downloaded: {pdfs_success:,}")
    print(f"📄 Already existed: {pdfs_already:,}")
    print(f"📊 Total PDFs obtained: {total_pdfs:,}")

    if pdfs_found > 0:
        print(f"📈 Download success rate (when PDF found): {total_pdfs/pdfs_found*100:.1f}%")

    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status:30s}: {len(group):>5,}")

    print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
    print(f"📄 Log file: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
