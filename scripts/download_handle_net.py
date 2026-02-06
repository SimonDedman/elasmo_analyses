#!/usr/bin/env python3
"""
Handle.net Redirect Scraper

Downloads PDFs from Handle.net URLs by:
1. Following the redirect to the institutional repository
2. Scraping the landing page for PDF links
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
from urllib.parse import urljoin, urlparse
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_FILE = BASE_DIR / "logs/handle_net_download.log"

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
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def get_pdf_url_from_landing_page(handle_url: str) -> str:
    """Follow handle.net redirect and extract PDF URL from landing page."""
    try:
        # Follow redirects to get to the actual repository page
        response = requests.get(
            handle_url,
            headers=HEADERS,
            timeout=30,
            verify=False,
            allow_redirects=True
        )
        response.raise_for_status()

        final_url = response.url
        logging.info(f"Redirected to: {final_url}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Strategy 1: Look for citation_pdf_url meta tag (common in DSpace)
        pdf_meta = soup.find('meta', {'name': 'citation_pdf_url'})
        if pdf_meta and pdf_meta.get('content'):
            return pdf_meta['content']

        # Strategy 2: Look for DC.identifier with PDF
        for meta in soup.find_all('meta', {'name': 'DC.identifier'}):
            content = meta.get('content', '')
            if content.endswith('.pdf'):
                return content

        # Strategy 3: Look for direct PDF links in the page
        base_url = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}"

        # Common patterns for repository PDF links
        pdf_patterns = [
            'bitstream',  # DSpace
            '/download/',
            '/files/',
            '/pdf/',
            '.pdf'
        ]

        for link in soup.find_all('a', href=True):
            href = link['href']
            href_lower = href.lower()

            # Check if it's a PDF link
            if any(pattern in href_lower for pattern in pdf_patterns):
                # Get link text
                link_text = link.get_text(strip=True).lower()

                # Prioritize links that mention PDF, download, or full text
                if any(term in link_text for term in ['pdf', 'download', 'full text', 'fulltext', 'open access']):
                    if href.startswith('http'):
                        return href
                    else:
                        return urljoin(final_url, href)

        # Strategy 4: Look for any .pdf link
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf'):
                if href.startswith('http'):
                    return href
                else:
                    return urljoin(final_url, href)

        # Strategy 5: Look for bitstream links (DSpace)
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'bitstream' in href.lower():
                if href.startswith('http'):
                    return href
                else:
                    return urljoin(final_url, href)

        return None

    except Exception as e:
        logging.error(f"Error fetching {handle_url}: {e}")
        return None


def download_pdf(url: str, output_path: Path) -> bool:
    """Download PDF from URL."""
    try:
        response = requests.get(
            url,
            headers={**HEADERS, 'Accept': 'application/pdf,*/*'},
            timeout=60,
            verify=False,
            allow_redirects=True
        )
        response.raise_for_status()

        content = response.content

        # Check magic bytes
        if not content[:4] == b'%PDF':
            # Sometimes servers return HTML error pages
            if b'<html' in content[:1000].lower():
                logging.warning(f"Got HTML instead of PDF")
                return False
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
    # Load Handle.net URLs from Unpaywall failures
    log = pd.read_csv(BASE_DIR / 'logs/unpaywall_download_log.csv')
    handles = log[
        log['oa_url'].str.contains('handle.net', na=False) &
        (log['status'] == 'failed')
    ].copy()

    # Get unique URLs
    handles = handles.drop_duplicates(subset=['oa_url'])

    print("=" * 70)
    print("HANDLE.NET REDIRECT SCRAPER")
    print("=" * 70)
    print(f"Papers to download: {len(handles)}")
    print()

    # Load database for year info
    db = pd.read_parquet(BASE_DIR / 'outputs/literature_review.parquet')
    id_to_year = dict(zip(
        pd.to_numeric(db['literature_id'], errors='coerce'),
        db['year']
    ))

    success = 0
    failed = 0
    no_pdf = 0

    for idx, row in handles.iterrows():
        handle_url = row['oa_url']
        doi = row['doi']
        lit_id = row['literature_id']

        print(f"\n[{success + failed + no_pdf + 1}/{len(handles)}] {doi}")

        # Get PDF URL from landing page
        pdf_url = get_pdf_url_from_landing_page(handle_url)

        if not pdf_url:
            logging.warning(f"No PDF URL found for {handle_url}")
            no_pdf += 1
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
        time.sleep(1.5)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    print(f"No PDF found: {no_pdf}")
    print(f"Total: {success + failed + no_pdf}")


if __name__ == "__main__":
    main()
