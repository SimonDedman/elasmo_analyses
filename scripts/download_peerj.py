#!/usr/bin/env python3
"""
Download PeerJ Open Access papers.

PeerJ is fully Open Access, all papers should be freely available.
Uses Unpaywall API to find PDF URLs, then downloads directly.
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
INPUT_FILE = BASE_DIR / "outputs/peerj_papers_to_download.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/peerj_download_log.csv"

# Unpaywall API - free, no registration needed
UNPAYWALL_EMAIL = "simon@example.com"  # Required by Unpaywall
UNPAYWALL_URL = "https://api.unpaywall.org/v2/{doi}?email={email}"

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/peerj.log"),
        logging.StreamHandler()
    ]
)

def get_pdf_url_from_unpaywall(doi: str) -> dict:
    """Get PDF URL from Unpaywall API."""
    try:
        url = UNPAYWALL_URL.format(doi=doi, email=UNPAYWALL_EMAIL)
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Check if OA
            if data.get('is_oa'):
                # Try to get best OA location
                best_oa = data.get('best_oa_location')
                if best_oa and best_oa.get('url_for_pdf'):
                    return {
                        'found': True,
                        'pdf_url': best_oa['url_for_pdf'],
                        'source': 'unpaywall'
                    }

            return {'found': False, 'error': 'no_oa_pdf'}

        return {'found': False, 'error': f'http_{response.status_code}'}

    except Exception as e:
        logging.error(f"Unpaywall error for {doi}: {e}")
        return {'found': False, 'error': str(e)}


def download_pdf(url: str, output_path: Path, timeout: int = 30) -> dict:
    """Download PDF from URL."""
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True)

        if response.status_code == 200:
            # Verify it's a PDF
            content_type = response.headers.get('Content-Type', '')

            if 'pdf' in content_type.lower() or response.content[:4] == b'%PDF':
                with open(output_path, 'wb') as f:
                    f.write(response.content)

                file_size = output_path.stat().st_size

                if file_size < 1024:
                    output_path.unlink()
                    return {'status': 'too_small', 'size_bytes': file_size}

                return {'status': 'success', 'size_bytes': file_size}

            return {'status': 'not_pdf', 'content_type': content_type}

        return {'status': f'http_{response.status_code}'}

    except Exception as e:
        logging.error(f"Download error: {e}")
        return {'status': 'error', 'error': str(e)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download PeerJ papers")
    parser.add_argument('--test', action='store_true', help="Test mode: 10 papers")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    args = parser.parse_args()

    print("=" * 80)
    print("PEERJ OPEN ACCESS DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load paper list
    if not INPUT_FILE.exists():
        print(f"\n❌ Input file not found: {INPUT_FILE}")
        print("   Run find_peerj_papers.py first")
        return

    df = pd.read_csv(INPUT_FILE)

    print(f"\n📊 Loaded {len(df):,} PeerJ papers")

    # Apply limits
    if args.test:
        df = df.head(10)
        print(f"🧪 Test mode: processing {len(df)} papers")
    elif args.max_papers:
        df = df.head(args.max_papers)

    # Load existing results
    existing_results = []
    if LOG_FILE.exists():
        existing_df = pd.read_csv(LOG_FILE)
        existing_ids = set(existing_df['literature_id'].values)
        df = df[~df['literature_id'].isin(existing_ids)]
        print(f"✅ Skipping {len(existing_ids):,} already processed")
        print(f"📊 Remaining: {len(df):,}")
        existing_results = existing_df.to_dict('records')

    if len(df) == 0:
        print("\n✅ All papers already processed!")
        return

    print(f"\n{'=' * 80}")
    print(f"PROCESSING {len(df):,} PAPERS")
    print("=" * 80)

    results = existing_results.copy()

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
        literature_id = row['literature_id']
        doi = row['doi']

        result = {
            'literature_id': literature_id,
            'doi': doi,
            'year': row['year'],
            'title': row['title'],
            'timestamp': datetime.now().isoformat()
        }

        # Step 1: Get PDF URL from Unpaywall
        pdf_info = get_pdf_url_from_unpaywall(doi)
        time.sleep(REQUEST_DELAY)

        if not pdf_info.get('found'):
            result['status'] = 'pdf_url_not_found'
            result['message'] = pdf_info.get('error', 'Unknown error')
            results.append(result)
            continue

        pdf_url = pdf_info['pdf_url']
        result['pdf_url'] = pdf_url

        # Construct filename
        article_id = doi.split('.')[-1]
        filename = f"{literature_id}_peerj_{article_id}.pdf"
        output_path = OUTPUT_DIR / filename

        # Check if already exists
        if output_path.exists():
            result['status'] = 'already_exists'
            result['filename'] = filename
            result['size_bytes'] = output_path.stat().st_size
            results.append(result)
            continue

        # Step 2: Download PDF
        download_result = download_pdf(pdf_url, output_path)

        result.update(download_result)
        if download_result.get('status') == 'success':
            result['filename'] = filename
            logging.info(f"Downloaded: {filename} ({download_result['size_bytes']:,} bytes)")

        results.append(result)

        # Save progress every 10 papers
        if len(results) % 10 == 0:
            results_df = pd.DataFrame(results)
            results_df.to_csv(LOG_FILE, index=False)

    # Final save
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
    print(f"📈 Success rate: {total_pdfs/len(results)*100:.1f}%")

    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status:30s}: {len(group):>5,}")

    print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
    print(f"📄 Log file: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
