#!/usr/bin/env python3
"""
download_semantic_direct_urls.py

Download PDFs with direct URLs from Semantic Scholar DOI extraction.

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/newly_discovered_dois.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/semantic_direct_urls_log.csv"

REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/semantic_direct_urls.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# DOWNLOAD FUNCTION
# ============================================================================

def download_pdf_from_url(url: str, doi: str, literature_id: str) -> dict:
    """Download PDF from direct URL."""

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

    # Try downloading with retries
    for attempt in range(MAX_RETRIES):
        try:
            logging.debug(f"Attempt {attempt + 1}/{MAX_RETRIES}: {url}")

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

                # Verify it's a real PDF
                if file_size < 1024:
                    with open(final_path, 'rb') as f:
                        if f.read(4) != b'%PDF':
                            final_path.unlink()
                            logging.warning(f"Invalid PDF: {url}")
                            continue

                logging.info(f"Downloaded: {final_filename} ({file_size:,} bytes)")

                return {
                    'status': 'success',
                    'filename': final_filename,
                    'size_bytes': file_size,
                    'url': url
                }
            else:
                logging.warning(f"Non-PDF content type: {content_type}")
                continue

        except requests.exceptions.Timeout:
            logging.warning(f"Timeout on attempt {attempt + 1}")
            continue
        except Exception as e:
            logging.warning(f"Error on attempt {attempt + 1}: {e}")
            continue

    return {
        'status': 'failed',
        'message': f'Failed after {MAX_RETRIES} attempts'
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("SEMANTIC SCHOLAR DIRECT URL DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load DOIs
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    # Filter for DOIs with PDF URLs
    df = df[(df['pdf_url'].notna()) & (df['pdf_url'] != '')].copy()

    print(f"📊 Found {len(df):,} DOIs with direct PDF URLs\n")

    if len(df) == 0:
        print("⚠️  No DOIs with direct URLs found!")
        return

    # Load existing results
    existing_results = []
    if LOG_FILE.exists():
        existing_df = pd.read_csv(LOG_FILE)
        existing_dois = set(existing_df['doi'].str.upper())
        df = df[~df['doi'].str.upper().isin(existing_dois)]
        print(f"✅ Skipping {len(existing_dois):,} already processed")
        print(f"📊 Remaining: {len(df):,}\n")
        existing_results = existing_df.to_dict('records')

    if len(df) == 0:
        print("✅ All DOIs already processed!")
        return

    print("=" * 80)
    print(f"DOWNLOADING {len(df):,} PDFS")
    print("=" * 80 + "\n")

    results = existing_results.copy()

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
        doi = row['doi']
        pdf_url = row['pdf_url']
        literature_id = row.get('literature_id', '')

        result = {
            'doi': doi,
            'literature_id': literature_id,
            'title': row.get('title', ''),
            'source': row.get('source', ''),
            'pdf_url': pdf_url,
            'timestamp': datetime.now().isoformat()
        }

        try:
            download_result = download_pdf_from_url(
                pdf_url,
                doi,
                str(literature_id) if literature_id else doi.replace('/', '_')
            )
            result.update(download_result)
            results.append(result)

        except Exception as e:
            logging.error(f"Error downloading {doi}: {e}")
            result['status'] = 'error'
            result['message'] = str(e)
            results.append(result)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)

    success = len(results_df[results_df['status'] == 'success'])
    already_exists = len(results_df[results_df['status'] == 'already_exists'])
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
