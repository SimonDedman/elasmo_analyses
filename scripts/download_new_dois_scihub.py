#!/usr/bin/env python3
"""
download_new_dois_scihub.py

Download newly discovered DOIs via Sci-Hub.

EDUCATIONAL/RESEARCH USE ONLY
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
LOG_FILE = BASE_DIR / "logs/scihub_new_dois_log.csv"

# Sci-Hub mirrors
SCIHUB_MIRRORS = [
    "https://sci-hub.st",
    "https://sci-hub.se",
    "https://sci-hub.ru"
]

# Rate limiting
DELAY_BETWEEN_REQUESTS = 3.0
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/scihub_new_dois.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# DOWNLOAD FUNCTIONS
# ============================================================================

def download_from_scihub(doi: str, literature_id: str) -> dict:
    """Download PDF from Sci-Hub using DOI."""

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

    # Try each mirror
    for mirror in SCIHUB_MIRRORS:
        try:
            url = f"{mirror}/{doi}"
            logging.debug(f"Trying: {url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)

            # Check if we got a PDF
            content_type = response.headers.get('Content-Type', '')

            if 'application/pdf' in content_type:
                # Save PDF
                with open(final_path, 'wb') as f:
                    f.write(response.content)

                file_size = final_path.stat().st_size

                # Verify it's a real PDF
                if file_size < 1024:
                    with open(final_path, 'rb') as f:
                        if f.read(4) != b'%PDF':
                            final_path.unlink()
                            continue

                logging.info(f"Downloaded: {final_filename} ({file_size:,} bytes) from {mirror}")

                return {
                    'status': 'success',
                    'filename': final_filename,
                    'size_bytes': file_size,
                    'mirror': mirror
                }
            else:
                # Got HTML page, not direct PDF
                # Try to extract PDF link from page
                if 'text/html' in content_type:
                    # Look for PDF link in HTML
                    import re
                    pdf_matches = re.findall(r'(https?://[^"\']+\.pdf[^"\']*)', response.text)

                    if pdf_matches:
                        pdf_url = pdf_matches[0]
                        logging.debug(f"Found PDF URL: {pdf_url}")

                        pdf_response = requests.get(pdf_url, headers=headers, timeout=REQUEST_TIMEOUT)

                        if pdf_response.headers.get('Content-Type', '').startswith('application/pdf'):
                            with open(final_path, 'wb') as f:
                                f.write(pdf_response.content)

                            file_size = final_path.stat().st_size

                            if file_size > 1024:
                                logging.info(f"Downloaded: {final_filename} ({file_size:,} bytes)")
                                return {
                                    'status': 'success',
                                    'filename': final_filename,
                                    'size_bytes': file_size,
                                    'mirror': mirror
                                }

        except requests.exceptions.Timeout:
            logging.debug(f"Timeout on {mirror}")
            continue
        except Exception as e:
            logging.debug(f"Error with {mirror}: {e}")
            continue

    return {
        'status': 'not_found',
        'message': 'PDF not available on any mirror'
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download newly discovered DOIs via Sci-Hub")
    parser.add_argument('--test', action='store_true', help="Test mode: 10 DOIs")
    parser.add_argument('--max-dois', type=int, help="Maximum DOIs to process")
    args = parser.parse_args()

    print("=" * 80)
    print("SCI-HUB DOWNLOADER - NEWLY DISCOVERED DOIS")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n⚠️  EDUCATIONAL/RESEARCH USE ONLY ⚠️\n")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load DOIs
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    # Filter out DOIs with direct PDF URLs (download those separately)
    df = df[~((df['pdf_url'].notna()) & (df['pdf_url'] != ''))].copy()

    print(f"📊 Loaded {len(df):,} DOIs for Sci-Hub download")

    # Apply limits
    if args.test:
        df = df.head(10)
        print(f"🧪 Test mode: processing {len(df)} DOIs")
    elif args.max_dois:
        df = df.head(args.max_dois)

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
    print(f"DOWNLOADING {len(df):,} PDFS VIA SCI-HUB")
    print("=" * 80)

    results = existing_results.copy()

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
        doi = row['doi']
        literature_id = row.get('literature_id', '')

        result = {
            'doi': doi,
            'literature_id': literature_id,
            'title': row.get('title', ''),
            'source': row.get('source', ''),
            'timestamp': datetime.now().isoformat()
        }

        try:
            download_result = download_from_scihub(doi, str(literature_id) if literature_id else doi.replace('/', '_'))
            result.update(download_result)
            results.append(result)

        except Exception as e:
            logging.error(f"Error downloading {doi}: {e}")
            result['status'] = 'error'
            result['message'] = str(e)
            results.append(result)

        # Rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)

        # Save progress every 25 DOIs
        if len(results) % 25 == 0:
            results_df = pd.DataFrame(results)
            results_df.to_csv(LOG_FILE, index=False)
            logging.info(f"Progress saved: {len(results)} DOIs processed")

    # Final save
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)

    success = len(results_df[results_df['status'] == 'success'])
    already_exists = len(results_df[results_df['status'] == 'already_exists'])
    not_found = len(results_df[results_df['status'] == 'not_found'])
    total_pdfs = success + already_exists

    print(f"\n✅ New PDFs downloaded: {success:,}")
    print(f"📄 Already existed: {already_exists:,}")
    print(f"📊 Total PDFs: {total_pdfs:,}")
    if len(results) > 0:
        print(f"📈 Success rate: {total_pdfs/len(results)*100:.1f}%")

    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status:30s}: {len(group):>5,}")

    print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
    print(f"📄 Log file: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
