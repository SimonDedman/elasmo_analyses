#!/usr/bin/env python3
"""
download_researchgate.py

Download available PDFs from ResearchGate using authenticated session.

Strategy:
1. Login to ResearchGate with user credentials
2. Search for papers by title + authors
3. Download PDFs that are publicly available (not requiring author request)
4. Respectful rate limiting to avoid account suspension

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
LOG_FILE = BASE_DIR / "logs/researchgate_download_log.csv"

# ResearchGate configuration
RG_BASE_URL = "https://www.researchgate.net"
RG_LOGIN_URL = f"{RG_BASE_URL}/login"
RG_SEARCH_URL = f"{RG_BASE_URL}/search/publication"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

# Rate limiting (IMPORTANT: Be respectful to avoid account suspension)
MIN_DELAY = 2.0  # Minimum delay between requests
MAX_DELAY = 5.0  # Maximum delay (randomized)
REQUEST_TIMEOUT = 20
MAX_RETRIES = 2

# PDF download settings
MAX_PDF_SIZE_MB = 50
MIN_PDF_SIZE_KB = 10

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/researchgate.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# RESEARCHGATE AUTHENTICATION
# ============================================================================

def login_to_researchgate(email: str, password: str, session: requests.Session) -> bool:
    """
    Login to ResearchGate and maintain session.

    Returns True if login successful, False otherwise.
    """
    try:
        # Get login page to extract CSRF token
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        response = session.get(RG_LOGIN_URL, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            logging.error(f"Failed to access login page: {response.status_code}")
            return False

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract CSRF token (ResearchGate uses various token names)
        csrf_token = None
        for name in ['authenticity_token', 'csrf_token', '_csrf']:
            token_input = soup.find('input', {'name': name})
            if token_input:
                csrf_token = token_input.get('value')
                break

        if not csrf_token:
            logging.warning("Could not find CSRF token, attempting login without it")

        # Prepare login data
        login_data = {
            'login': email,
            'password': password,
        }

        if csrf_token:
            login_data['authenticity_token'] = csrf_token

        # Submit login
        login_headers = headers.copy()
        login_headers['Referer'] = RG_LOGIN_URL
        login_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        response = session.post(
            RG_LOGIN_URL,
            data=login_data,
            headers=login_headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        # Check if login successful
        if 'login' in response.url.lower():
            logging.error("Login failed - still on login page")
            return False

        # Verify we're logged in by checking for user profile link
        if 'profile' in response.text.lower() or 'logout' in response.text.lower():
            logging.info("✅ Successfully logged in to ResearchGate")
            return True
        else:
            logging.error("Login status unclear - may have failed")
            return False

    except Exception as e:
        logging.error(f"Login error: {e}")
        return False


# ============================================================================
# RESEARCHGATE SEARCH AND DOWNLOAD
# ============================================================================

def search_researchgate(title: str, authors: str, session: requests.Session) -> list:
    """
    Search ResearchGate for a paper.

    Returns list of dicts with:
    - publication_url: Link to paper page
    - pdf_url: Direct PDF link (if available)
    - title: Matched title
    - availability: 'public', 'request', 'unavailable'
    """
    try:
        # Clean and build search query
        clean_title = re.sub(r'[^\w\s-]', '', title).strip()
        query = clean_title[:100]  # Limit query length

        params = {
            'q': query,
            'type': 'publication'
        }

        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': RG_BASE_URL,
        }

        response = session.get(
            RG_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            logging.warning(f"ResearchGate search returned {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        results = []

        # Find publication items in search results
        # ResearchGate structure: div.nova-legacy-o-stack__item containing publication info
        for item in soup.find_all('div', class_=re.compile(r'publication-item|nova-legacy-o-stack__item')):

            # Extract publication link
            pub_link = item.find('a', href=re.compile(r'/publication/\d+'))
            if not pub_link:
                continue

            pub_url = urljoin(RG_BASE_URL, pub_link['href'])
            matched_title = pub_link.get_text(strip=True)

            # Check for PDF availability
            # Look for "Download full-text PDF" button
            pdf_button = item.find('a', text=re.compile(r'Download|PDF', re.I))

            if pdf_button and 'request' not in pdf_button.get_text().lower():
                # PDF is publicly available
                pdf_url = urljoin(RG_BASE_URL, pdf_button.get('href', ''))
                availability = 'public'
            elif 'request' in item.get_text().lower():
                availability = 'request'
                pdf_url = None
            else:
                availability = 'unavailable'
                pdf_url = None

            results.append({
                'publication_url': pub_url,
                'pdf_url': pdf_url,
                'matched_title': matched_title,
                'availability': availability
            })

            # Only return top 3 results
            if len(results) >= 3:
                break

        return results

    except Exception as e:
        logging.error(f"Error searching ResearchGate: {e}")
        return []


def download_pdf_from_researchgate(pdf_url: str, literature_id: str, title: str, session: requests.Session) -> dict:
    """Download PDF from ResearchGate."""

    # Construct filename
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
    final_filename = f"{literature_id}_{safe_title}_RG.pdf"
    final_path = OUTPUT_DIR / final_filename

    # Check if already exists
    if final_path.exists():
        return {
            'status': 'already_exists',
            'filename': final_filename,
            'size_bytes': final_path.stat().st_size
        }

    try:
        logging.debug(f"Downloading from: {pdf_url}")

        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': RG_BASE_URL,
        }

        # Stream download
        response = session.get(pdf_url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)

        # Check content type
        content_type = response.headers.get('Content-Type', '')

        if 'application/pdf' not in content_type and 'pdf' not in pdf_url.lower():
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
            'download_url': pdf_url
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

    parser = argparse.ArgumentParser(description="Download PDFs from ResearchGate")
    parser.add_argument('--username', type=str, required=True, help="ResearchGate email/username")
    parser.add_argument('--password', type=str, required=True, help="ResearchGate password")
    parser.add_argument('--test', action='store_true', help="Test mode: 20 papers only")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    args = parser.parse_args()

    print("=" * 80)
    print("RESEARCHGATE PDF DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Username: {args.username}")
    print("")
    print("⚠️  Using authenticated session - be respectful to avoid account suspension")
    print(f"   Delay between requests: {MIN_DELAY}-{MAX_DELAY} seconds")
    print("")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Create session and login
    session = requests.Session()

    print("🔐 Logging in to ResearchGate...")
    if not login_to_researchgate(args.username, args.password, session):
        print("❌ Login failed. Please check your credentials.")
        return

    print("✅ Login successful!\n")

    # Load papers database
    if not PAPERS_FILE.exists():
        print(f"❌ Papers file not found: {PAPERS_FILE}")
        return

    df = pd.read_csv(PAPERS_FILE)
    print(f"📊 Loaded {len(df):,} papers without DOIs")

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
    print(f"SEARCHING RESEARCHGATE FOR {len(df):,} PAPERS")
    print("=" * 80)
    print("")

    results = existing_results.copy()
    papers_found = 0
    pdfs_available = 0
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

        # Search ResearchGate
        search_results = search_researchgate(title, authors, session)

        result['papers_found'] = len(search_results)

        if search_results:
            papers_found += 1

            # Try to download from first publicly available result
            for search_result in search_results:
                result['matched_title'] = search_result['matched_title']
                result['publication_url'] = search_result['publication_url']
                result['availability'] = search_result['availability']

                if search_result['availability'] == 'public' and search_result['pdf_url']:
                    pdfs_available += 1

                    download_result = download_pdf_from_researchgate(
                        search_result['pdf_url'],
                        str(literature_id),
                        title,
                        session
                    )

                    if download_result.get('status') == 'success':
                        result.update(download_result)
                        pdfs_downloaded += 1
                        break
                elif search_result['availability'] == 'request':
                    result['status'] = 'requires_author_request'
                    break
            else:
                # No public PDFs found
                if not result.get('status'):
                    result['status'] = 'found_but_no_public_pdf'
        else:
            result['status'] = 'not_found_on_researchgate'

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
    print("RESEARCHGATE DOWNLOAD SUMMARY")
    print("=" * 80)

    total_processed = len(results_df)
    pdfs_success = len(results_df[results_df['status'] == 'success'])
    pdfs_already = len(results_df[results_df['status'] == 'already_exists'])
    total_pdfs = pdfs_success + pdfs_already

    print(f"\n📊 Papers processed: {total_processed:,}")
    print(f"🔍 Papers found on RG: {papers_found:,} ({papers_found/total_processed*100:.1f}%)")
    print(f"📂 Public PDFs available: {pdfs_available:,}")
    print(f"📥 New PDFs downloaded: {pdfs_success:,}")
    print(f"📄 Already existed: {pdfs_already:,}")
    print(f"📊 Total PDFs obtained: {total_pdfs:,}")

    if pdfs_available > 0:
        print(f"📈 Download success rate (when public PDF available): {total_pdfs/pdfs_available*100:.1f}%")

    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status:40s}: {len(group):>5,}")

    print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
    print(f"📄 Log file: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
