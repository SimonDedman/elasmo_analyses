#!/usr/bin/env python3
"""
retry_unpaywall_failures.py

Retry Unpaywall failed downloads with improved strategies:
1. Try direct PDF URLs from Unpaywall
2. Handle different content types (HTML pages with PDF links)
3. Follow redirects more aggressively
4. Try alternative URL patterns

Author: Simon Dedman / Claude
Date: 2025-11-20
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm
import logging
from bs4 import BeautifulSoup
import re

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/unpaywall_failed_for_retry.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/unpaywall_retry_log.csv"

REQUEST_TIMEOUT = 60  # Increased timeout
MAX_RETRIES = 5  # More retries
DELAY_BETWEEN_REQUESTS = 2.0

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/unpaywall_retry.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# DOWNLOAD FUNCTIONS
# ============================================================================

def extract_pdf_from_html(html_content: str, base_url: str) -> str:
    """Extract PDF link from HTML page."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Look for PDF links
        pdf_patterns = [
            r'\.pdf$',
            r'\.pdf\?',
            r'download.*pdf',
            r'pdf.*download'
        ]

        for link in soup.find_all('a', href=True):
            href = link['href']
            for pattern in pdf_patterns:
                if re.search(pattern, href, re.IGNORECASE):
                    # Make absolute URL
                    if href.startswith('http'):
                        return href
                    elif href.startswith('/'):
                        from urllib.parse import urlparse
                        parsed = urlparse(base_url)
                        return f"{parsed.scheme}://{parsed.netloc}{href}"

        # Look for meta tags with PDF URLs
        for meta in soup.find_all('meta'):
            content = meta.get('content', '')
            if '.pdf' in content:
                return content

        return None
    except:
        return None


def download_pdf_improved(url: str, doi: str, literature_id: str) -> dict:
    """Download PDF with improved strategies."""

    # Construct filename
    safe_doi = doi.replace('/', '_').replace('.', '_')
    final_filename = f"{literature_id}_{safe_doi}.pdf"
    final_path = OUTPUT_DIR / final_filename

    # Check if already exists
    if final_path.exists():
        return {
            'status': 'already_exists',
            'filename': final_filename,
            'size_bytes': final_path.stat().st_size
        }

    for attempt in range(MAX_RETRIES):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }

            # Try direct download
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT,
                                   allow_redirects=True, stream=True)

            content_type = response.headers.get('Content-Type', '').lower()

            # Strategy 1: Direct PDF
            if 'application/pdf' in content_type:
                with open(final_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                file_size = final_path.stat().st_size

                # Verify PDF
                if file_size > 1024:
                    with open(final_path, 'rb') as f:
                        if f.read(4) == b'%PDF':
                            logging.info(f"✓ Direct download: {final_filename} ({file_size:,} bytes)")
                            return {
                                'status': 'success',
                                'method': 'direct',
                                'filename': final_filename,
                                'size_bytes': file_size
                            }

                final_path.unlink()
                continue

            # Strategy 2: Check if content is PDF despite content-type
            content_start = response.content[:4] if len(response.content) >= 4 else b''
            if content_start == b'%PDF':
                with open(final_path, 'wb') as f:
                    f.write(response.content)

                file_size = final_path.stat().st_size
                if file_size > 1024:
                    logging.info(f"✓ PDF despite wrong content-type: {final_filename}")
                    return {
                        'status': 'success',
                        'method': 'content_check',
                        'filename': final_filename,
                        'size_bytes': file_size
                    }
                final_path.unlink()
                continue

            # Strategy 3: Parse HTML for PDF link
            if 'text/html' in content_type:
                pdf_link = extract_pdf_from_html(response.text, url)
                if pdf_link:
                    logging.info(f"Found PDF link in HTML: {pdf_link}")
                    # Recursively try the extracted link
                    time.sleep(1)
                    return download_pdf_improved(pdf_link, doi, literature_id)

            # Strategy 4: Try DOI resolution directly
            if attempt == MAX_RETRIES - 2 and url != f"https://doi.org/{doi}":
                logging.info(f"Trying DOI redirect: {doi}")
                time.sleep(2)
                return download_pdf_improved(f"https://doi.org/{doi}", doi, literature_id)

            logging.warning(f"Attempt {attempt + 1}: Non-PDF content-type: {content_type}")
            time.sleep(2 ** attempt)

        except requests.exceptions.Timeout:
            logging.warning(f"Attempt {attempt + 1}: Timeout")
            time.sleep(2 ** attempt)
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1}: {e}")
            time.sleep(2 ** attempt)

    return {
        'status': 'failed',
        'method': 'all_strategies_failed',
        'message': f'Failed after {MAX_RETRIES} attempts'
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("UNPAYWALL RETRY - IMPROVED STRATEGIES")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load failed downloads
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    failed_df = pd.read_csv(INPUT_FILE)
    print(f"📊 Loaded {len(failed_df)} failed downloads to retry\n")

    # Load existing log if it exists
    if LOG_FILE.exists():
        log_df = pd.read_csv(LOG_FILE)
        processed_dois = set(log_df['doi'].values)
        print(f"✅ Skipping {len(processed_dois)} already processed")
        failed_df = failed_df[~failed_df['doi'].isin(processed_dois)]
    else:
        log_df = pd.DataFrame()

    print(f"📊 Remaining: {len(failed_df)}\n")

    if len(failed_df) == 0:
        print("✅ All failed downloads already retried!")
        return

    # Process each failed download
    results = []
    success_count = 0

    for idx, row in tqdm(failed_df.iterrows(), total=len(failed_df), desc="Retrying downloads"):
        doi = row['doi']
        # Handle NaN literature_id
        try:
            literature_id = str(int(row['literature_id']))
        except (ValueError, TypeError):
            literature_id = str(idx)
        oa_url = row['oa_url']

        # Try download
        result = download_pdf_improved(oa_url, doi, literature_id)

        # Record result
        result_row = {
            'doi': doi,
            'literature_id': literature_id,
            'title': row.get('title', ''),
            'oa_status': row.get('oa_status', ''),
            'oa_url': oa_url,
            'timestamp': datetime.now().isoformat(),
            **result
        }
        results.append(result_row)

        if result['status'] == 'success':
            success_count += 1

        # Save progress every 10 papers
        if len(results) % 10 == 0:
            results_df = pd.DataFrame(results)
            if not log_df.empty:
                results_df = pd.concat([log_df, results_df], ignore_index=True)
            results_df.to_csv(LOG_FILE, index=False)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Final save
    results_df = pd.DataFrame(results)
    if not log_df.empty:
        results_df = pd.concat([log_df, results_df], ignore_index=True)
    results_df.to_csv(LOG_FILE, index=False)

    print("\n" + "=" * 80)
    print("RETRY COMPLETE")
    print("=" * 80)
    print(f"✅ Successful: {success_count}/{len(failed_df)} ({success_count/len(failed_df)*100:.1f}%)")
    print(f"❌ Failed: {len(failed_df) - success_count}/{len(failed_df)}")
    print(f"\nLog saved to: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
