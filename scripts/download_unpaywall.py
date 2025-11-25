#!/usr/bin/env python3
"""
download_unpaywall.py

Download open access PDFs using the Unpaywall API for newly discovered DOIs.

Unpaywall is a free, legal API that finds open access versions of papers.
More info: https://unpaywall.org/products/api

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

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/newly_discovered_dois.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/unpaywall_download_log.csv"

# Unpaywall API configuration
# Email is required by Unpaywall API (for courtesy contact, not authentication)
UNPAYWALL_EMAIL = "your-email@example.com"  # TODO: Update with your email
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

# Rate limiting (Unpaywall recommends max 100k requests/day)
DELAY_BETWEEN_REQUESTS = 1.0  # Be respectful
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/unpaywall.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# UNPAYWALL API FUNCTIONS
# ============================================================================

def query_unpaywall(doi: str) -> dict:
    """
    Query Unpaywall API for open access PDF.

    Returns dict with:
    - is_oa: boolean
    - best_oa_location: dict with download_url if available
    - oa_status: 'gold', 'green', 'hybrid', 'bronze', or 'closed'
    """

    url = f"{UNPAYWALL_BASE_URL}/{doi}"
    params = {'email': UNPAYWALL_EMAIL}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logging.debug(f"DOI not found in Unpaywall: {doi}")
                return {'is_oa': False, 'oa_status': 'not_found'}
            else:
                logging.warning(f"Unpaywall returned {response.status_code} for {doi}")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue

        except requests.exceptions.Timeout:
            logging.warning(f"Timeout on attempt {attempt + 1} for {doi}")
            time.sleep(2 ** attempt)
            continue
        except Exception as e:
            logging.error(f"Error querying Unpaywall for {doi}: {e}")
            return {'is_oa': False, 'oa_status': 'error', 'error': str(e)}

    return {'is_oa': False, 'oa_status': 'failed_after_retries'}


def download_pdf_from_url(url: str, doi: str, literature_id: str) -> dict:
    """Download PDF from URL."""

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

    # Try downloading
    for attempt in range(MAX_RETRIES):
        try:
            logging.debug(f"Downloading from: {url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)

            # Check if we got a PDF
            content_type = response.headers.get('Content-Type', '')

            if 'application/pdf' in content_type or response.content[:4] == b'%PDF':
                # Save PDF
                with open(final_path, 'wb') as f:
                    f.write(response.content)

                file_size = final_path.stat().st_size

                # Verify it's a real PDF (at least 1KB)
                if file_size < 1024:
                    with open(final_path, 'rb') as f:
                        if f.read(4) != b'%PDF':
                            final_path.unlink()
                            logging.warning(f"Invalid PDF from {url}")
                            continue

                logging.info(f"Downloaded: {final_filename} ({file_size:,} bytes)")

                return {
                    'status': 'success',
                    'filename': final_filename,
                    'size_bytes': file_size,
                    'download_url': url
                }
            else:
                logging.warning(f"Non-PDF content type: {content_type}")
                continue

        except requests.exceptions.Timeout:
            logging.warning(f"Timeout on attempt {attempt + 1}")
            time.sleep(2 ** attempt)
            continue
        except Exception as e:
            logging.warning(f"Error on attempt {attempt + 1}: {e}")
            time.sleep(2 ** attempt)
            continue

    return {
        'status': 'failed',
        'message': f'Failed after {MAX_RETRIES} attempts'
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download open access PDFs via Unpaywall API")
    parser.add_argument('--test', action='store_true', help="Test mode: 10 DOIs only")
    parser.add_argument('--email', type=str, help="Your email for Unpaywall API")
    args = parser.parse_args()

    # Update email if provided
    global UNPAYWALL_EMAIL
    if args.email:
        UNPAYWALL_EMAIL = args.email

    print("=" * 80)
    print("UNPAYWALL OPEN ACCESS DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Email: {UNPAYWALL_EMAIL}")
    print("")

    if UNPAYWALL_EMAIL == "your-email@example.com":
        print("⚠️  WARNING: Please provide your email via --email argument")
        print("   Unpaywall requires an email for courtesy contact")
        print("   Example: python download_unpaywall.py --email you@university.edu")
        return

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load newly discovered DOIs
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)
    print(f"📊 Loaded {len(df):,} newly discovered DOIs")

    # Apply test mode
    if args.test:
        df = df.head(10)
        print(f"🧪 Test mode: processing {len(df)} DOIs")

    # Load existing results
    existing_results = []
    if LOG_FILE.exists():
        existing_df = pd.read_csv(LOG_FILE)
        existing_dois = set(existing_df['doi'].str.upper())
        df = df[~df['doi'].str.upper().isin(existing_dois)]
        print(f"✅ Skipping {len(existing_dois):,} already processed")
        print(f"📊 Remaining: {len(df):,}")
        existing_results = existing_df.to_dict('records')

    if len(df) == 0:
        print("\n✅ All DOIs already processed!")
        return

    print("\n" + "=" * 80)
    print(f"QUERYING UNPAYWALL FOR {len(df):,} DOIS")
    print("=" * 80)
    print("")

    results = existing_results.copy()
    oa_found = 0
    pdfs_downloaded = 0

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        doi = row['doi']
        literature_id = row.get('literature_id', '')

        result = {
            'doi': doi,
            'literature_id': literature_id,
            'title': row.get('title', ''),
            'source': row.get('source', ''),
            'timestamp': datetime.now().isoformat()
        }

        # Query Unpaywall
        unpaywall_data = query_unpaywall(doi)

        result['is_oa'] = unpaywall_data.get('is_oa', False)
        result['oa_status'] = unpaywall_data.get('oa_status', 'unknown')

        if unpaywall_data.get('is_oa'):
            oa_found += 1

            # Get best OA location
            best_oa = unpaywall_data.get('best_oa_location', {})
            pdf_url = best_oa.get('url_for_pdf') or best_oa.get('url')

            result['oa_url'] = pdf_url
            result['oa_version'] = best_oa.get('version', '')
            result['repository'] = best_oa.get('host_type', '')

            if pdf_url:
                # Try to download
                lit_id = str(literature_id) if literature_id else doi.replace('/', '_')
                download_result = download_pdf_from_url(pdf_url, doi, lit_id)

                result.update(download_result)

                if download_result.get('status') == 'success':
                    pdfs_downloaded += 1
            else:
                result['status'] = 'oa_but_no_pdf_url'
        else:
            result['status'] = 'not_open_access'

        results.append(result)

        # Rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)

        # Save progress every 25 DOIs
        if len(results) % 25 == 0:
            results_df = pd.DataFrame(results)
            results_df.to_csv(LOG_FILE, index=False)
            logging.info(f"Progress saved: {len(results)} DOIs processed, {pdfs_downloaded} PDFs downloaded")

    # Final save
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("UNPAYWALL DOWNLOAD SUMMARY")
    print("=" * 80)

    total_processed = len(results_df)
    oa_found_total = len(results_df[results_df['is_oa'] == True])
    pdfs_success = len(results_df[results_df['status'] == 'success'])
    pdfs_already_exists = len(results_df[results_df['status'] == 'already_exists'])
    total_pdfs = pdfs_success + pdfs_already_exists

    print(f"\n📊 DOIs processed: {total_processed:,}")
    print(f"✅ Open access found: {oa_found_total:,} ({oa_found_total/total_processed*100:.1f}%)")
    print(f"📥 New PDFs downloaded: {pdfs_success:,}")
    print(f"📄 Already existed: {pdfs_already_exists:,}")
    print(f"📊 Total PDFs obtained: {total_pdfs:,}")

    if oa_found_total > 0:
        print(f"📈 Download success rate (of OA papers): {total_pdfs/oa_found_total*100:.1f}%")

    print(f"\nBreakdown by OA status:")
    for status, group in results_df.groupby('oa_status'):
        print(f"  {status:30s}: {len(group):>5,}")

    print(f"\nBreakdown by download status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status:30s}: {len(group):>5,}")

    print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
    print(f"📄 Log file: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
