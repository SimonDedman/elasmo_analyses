#!/usr/bin/env python3
"""
Archimer Repository Scraper

Downloads PDFs from Archimer (IFREMER's institutional repository) by:
1. Fetching the landing page
2. Extracting the citation_pdf_url meta tag
3. Downloading the actual PDF

Author: Claude
Date: 2026-01-09
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import logging
import re
import sys

# Configuration
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_FILE = BASE_DIR / "logs/archimer_download.log"

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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def get_pdf_url_from_archimer(landing_url: str) -> str:
    """Extract PDF URL from Archimer landing page."""
    try:
        response = requests.get(landing_url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for citation_pdf_url meta tag
        pdf_meta = soup.find('meta', {'name': 'citation_pdf_url'})
        if pdf_meta and pdf_meta.get('content'):
            return pdf_meta['content']

        # Fallback: look for direct PDF links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('.pdf'):
                if href.startswith('http'):
                    return href
                else:
                    return f"https://archimer.ifremer.fr{href}"

        return None

    except Exception as e:
        logging.error(f"Error fetching {landing_url}: {e}")
        return None


def download_pdf(url: str, output_path: Path) -> bool:
    """Download PDF from URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if 'pdf' not in content_type.lower() and not url.endswith('.pdf'):
            logging.warning(f"Not a PDF: {content_type}")
            return False

        # Check magic bytes
        content = response.content
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
    # Load Archimer URLs from Unpaywall failures
    log = pd.read_csv(BASE_DIR / 'logs/unpaywall_download_log.csv')
    archimer = log[
        log['oa_url'].str.contains('archimer', na=False) &
        (log['status'] == 'failed')
    ].copy()

    # Get unique URLs with their paper info
    archimer = archimer.drop_duplicates(subset=['oa_url'])

    print("=" * 70)
    print("ARCHIMER REPOSITORY SCRAPER")
    print("=" * 70)
    print(f"Papers to download: {len(archimer)}")
    print()

    # Load database for year info
    db = pd.read_parquet(BASE_DIR / 'outputs/literature_review.parquet')
    id_to_year = dict(zip(
        pd.to_numeric(db['literature_id'], errors='coerce'),
        db['year']
    ))

    success = 0
    failed = 0

    for idx, row in archimer.iterrows():
        landing_url = row['oa_url']
        doi = row['doi']
        lit_id = row['literature_id']

        print(f"\n[{success + failed + 1}/{len(archimer)}] {doi}")

        # Get PDF URL from landing page
        pdf_url = get_pdf_url_from_archimer(landing_url)

        if not pdf_url:
            logging.warning(f"No PDF URL found for {landing_url}")
            failed += 1
            continue

        logging.info(f"Found PDF: {pdf_url}")

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
        if download_pdf(pdf_url, output_path):
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
