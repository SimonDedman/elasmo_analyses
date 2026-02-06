#!/usr/bin/env python3
"""
Scientia Marina Downloader

Downloads PDFs from Scientia Marina (CSIC journal).
These URLs are direct PDF downloads but require SSL verification bypass.

Author: Claude
Date: 2026-01-09
"""

import pandas as pd
import requests
from pathlib import Path
import time
import logging
import re
import urllib3

# Disable SSL warnings (the server has certificate issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_FILE = BASE_DIR / "logs/scientia_marina_download.log"

# Ensure log directory exists
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/pdf,*/*',
}


def download_pdf(url: str, output_path: Path) -> bool:
    """Download PDF from URL with SSL verification disabled."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=60,
            verify=False,  # Skip SSL verification
            allow_redirects=True
        )
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if 'pdf' not in content_type.lower():
            logging.warning(f"Not a PDF: {content_type}")
            return False

        content = response.content

        # Check magic bytes
        if not content[:4] == b'%PDF':
            logging.warning(f"Invalid PDF magic bytes")
            return False

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(content)

        logging.info(f"Downloaded: {output_path.name} ({len(content):,} bytes)")
        return True

    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")
        return False


def get_safe_filename(doi: str, lit_id) -> str:
    """Create safe filename from DOI."""
    safe_doi = re.sub(r'[^\w\-.]', '_', str(doi))
    if pd.notna(lit_id):
        return f"{int(lit_id)}.0_{safe_doi}.pdf"
    else:
        return f"{safe_doi}.pdf"


def main():
    # Load Scientia Marina URLs from Unpaywall failures
    log = pd.read_csv(BASE_DIR / 'logs/unpaywall_download_log.csv')
    scientia = log[
        log['oa_url'].str.contains('scientiamarina', na=False) &
        (log['status'] == 'failed')
    ].copy()

    # Get unique URLs
    scientia = scientia.drop_duplicates(subset=['oa_url'])

    print("=" * 70)
    print("SCIENTIA MARINA DOWNLOADER")
    print("=" * 70)
    print(f"Papers to download: {len(scientia)}")
    print()

    # Load database for year info
    db = pd.read_parquet(BASE_DIR / 'outputs/literature_review.parquet')
    id_to_year = dict(zip(
        pd.to_numeric(db['literature_id'], errors='coerce'),
        db['year']
    ))

    success = 0
    failed = 0

    for idx, row in scientia.iterrows():
        url = row['oa_url']
        doi = row['doi']
        lit_id = row['literature_id']

        print(f"\n[{success + failed + 1}/{len(scientia)}] {doi}")

        # Determine output path
        year = id_to_year.get(float(lit_id)) if pd.notna(lit_id) else None
        if year and not pd.isna(year):
            year_dir = OUTPUT_DIR / str(int(year))
        else:
            year_dir = OUTPUT_DIR / "unknown_year"

        filename = get_safe_filename(doi, lit_id)
        output_path = year_dir / filename

        # Skip if exists
        if output_path.exists():
            logging.info(f"Already exists: {filename}")
            success += 1
            continue

        # Download
        if download_pdf(url, output_path):
            success += 1
        else:
            failed += 1

        # Rate limit
        time.sleep(1)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    print(f"Total: {success + failed}")


if __name__ == "__main__":
    main()
