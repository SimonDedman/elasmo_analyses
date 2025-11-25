#!/usr/bin/env python3
"""
download_in_press_papers.py

Download papers that were marked "in press" but now have DOIs.
These are likely now published and available.

Uses Unpaywall API to find open access versions.

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

# Configuration
BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/in_press_with_dois_for_download.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/in_press_download_log.csv"

UNPAYWALL_EMAIL = "simondedman@gmail.com"
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"
DELAY = 1.5
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/in_press_download.log"),
        logging.StreamHandler()
    ]
)


def query_unpaywall(doi: str) -> dict:
    """Query Unpaywall API for OA version."""
    url = f"{UNPAYWALL_BASE_URL}/{doi}"
    params = {'email': UNPAYWALL_EMAIL}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {'is_oa': False, 'oa_status': 'not_found'}
            else:
                time.sleep(2 ** attempt)
                continue

        except requests.exceptions.Timeout:
            time.sleep(2 ** attempt)
            continue
        except Exception as e:
            logging.error(f"Error querying Unpaywall for {doi}: {e}")
            return {'is_oa': False, 'oa_status': 'error', 'error': str(e)}

    return {'is_oa': False, 'oa_status': 'failed_after_retries'}


def download_pdf(url: str, doi: str, literature_id: str) -> dict:
    """Download PDF from URL."""
    safe_doi = doi.replace('/', '_').replace('.', '_')
    final_filename = f"{literature_id}_{safe_doi}.pdf"
    final_path = OUTPUT_DIR / final_filename

    if final_path.exists():
        return {
            'status': 'already_exists',
            'filename': final_filename,
            'size_bytes': final_path.stat().st_size
        }

    for attempt in range(MAX_RETRIES):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT,
                                   allow_redirects=True, stream=True)

            content_type = response.headers.get('Content-Type', '')

            if 'application/pdf' in content_type or response.content[:4] == b'%PDF':
                with open(final_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                file_size = final_path.stat().st_size

                if file_size > 1024:
                    with open(final_path, 'rb') as f:
                        if f.read(4) == b'%PDF':
                            logging.info(f"✓ Downloaded: {final_filename} ({file_size:,} bytes)")
                            return {
                                'status': 'success',
                                'filename': final_filename,
                                'size_bytes': file_size
                            }

                final_path.unlink()

            time.sleep(2 ** attempt)

        except Exception as e:
            logging.warning(f"Attempt {attempt + 1}: {e}")
            time.sleep(2 ** attempt)

    return {
        'status': 'failed',
        'message': f'Failed after {MAX_RETRIES} attempts'
    }


def main():
    print("=" * 80)
    print("'IN PRESS' PAPER DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    papers_df = pd.read_csv(INPUT_FILE)
    print(f"📊 Loaded {len(papers_df)} 'in press' papers with DOIs\n")

    # Load existing log
    if LOG_FILE.exists():
        log_df = pd.read_csv(LOG_FILE)
        processed_dois = set(log_df['doi'].values)
        print(f"✅ Skipping {len(processed_dois)} already processed")
        papers_df = papers_df[~papers_df['doi'].isin(processed_dois)]
    else:
        log_df = pd.DataFrame()

    print(f"📊 Remaining: {len(papers_df)}\n")

    if len(papers_df) == 0:
        print("✅ All papers already processed!")
        return

    results = []
    success_count = 0
    oa_found_count = 0

    for idx, row in tqdm(papers_df.iterrows(), total=len(papers_df), desc="Processing"):
        doi = row['doi']
        # Handle NaN literature_id
        try:
            literature_id = str(int(row['literature_id']))
        except (ValueError, TypeError):
            literature_id = str(idx)

        # Query Unpaywall
        oa_data = query_unpaywall(doi)

        result_row = {
            'doi': doi,
            'literature_id': literature_id,
            'title': row.get('title', ''),
            'findspot': row.get('findspot', ''),
            'timestamp': datetime.now().isoformat(),
            'is_oa': oa_data.get('is_oa', False),
            'oa_status': oa_data.get('oa_status', 'unknown')
        }

        # Try to download if OA
        if oa_data.get('is_oa') and oa_data.get('best_oa_location'):
            oa_found_count += 1
            pdf_url = oa_data['best_oa_location'].get('url_for_pdf') or \
                      oa_data['best_oa_location'].get('url')

            if pdf_url:
                download_result = download_pdf(pdf_url, doi, literature_id)
                result_row.update(download_result)
                result_row['oa_url'] = pdf_url

                if download_result['status'] == 'success':
                    success_count += 1
            else:
                result_row['status'] = 'no_pdf_url'
        else:
            result_row['status'] = 'not_open_access'

        results.append(result_row)

        # Save progress every 10
        if len(results) % 10 == 0:
            results_df = pd.DataFrame(results)
            if not log_df.empty:
                results_df = pd.concat([log_df, results_df], ignore_index=True)
            results_df.to_csv(LOG_FILE, index=False)

        time.sleep(DELAY)

    # Final save
    results_df = pd.DataFrame(results)
    if not log_df.empty:
        results_df = pd.concat([log_df, results_df], ignore_index=True)
    results_df.to_csv(LOG_FILE, index=False)

    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE")
    print("=" * 80)
    print(f"📊 Papers checked: {len(papers_df)}")
    print(f"✅ Open access found: {oa_found_count} ({oa_found_count/len(papers_df)*100:.1f}%)")
    print(f"✅ PDFs downloaded: {success_count} ({success_count/len(papers_df)*100:.1f}%)")
    print(f"\nLog saved to: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
