#!/usr/bin/env python3
"""
Scrapers Retry Downloader

Retries downloads using existing scrapers:
- Archimer (IFREMER repository)
- Scientia Marina (CSIC journal)
- Handle.net (institutional repositories)

Uses the scraper_retry.csv as input.

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
INPUT_CSV = BASE_DIR / "outputs/scraper_retry.csv"
LOG_FILE = BASE_DIR / "logs/scrapers_retry.log"

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
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8',
}


def get_archimer_pdf_url(landing_url: str) -> str:
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
        logging.error(f"Error fetching Archimer {landing_url}: {e}")
        return None


def get_scientia_marina_pdf_url(url: str) -> str:
    """Scientia Marina URLs are direct PDF downloads."""
    return url


def get_handle_net_pdf_url(handle_url: str) -> str:
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
        logging.info(f"Handle redirect: {final_url}")

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
        pdf_patterns = ['bitstream', '/download/', '/files/', '/pdf/', '.pdf']

        for link in soup.find_all('a', href=True):
            href = link['href']
            href_lower = href.lower()

            if any(pattern in href_lower for pattern in pdf_patterns):
                link_text = link.get_text(strip=True).lower()

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
        logging.error(f"Error fetching handle.net {handle_url}: {e}")
        return None


def download_pdf(url: str, output_path: Path, verify_ssl: bool = False) -> bool:
    """Download PDF from URL."""
    try:
        response = requests.get(
            url,
            headers={**HEADERS, 'Accept': 'application/pdf,*/*'},
            timeout=60,
            verify=verify_ssl,
            allow_redirects=True
        )
        response.raise_for_status()

        content = response.content

        # Check magic bytes
        if not content[:4] == b'%PDF':
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


def get_pdf_url_for_publisher(url: str, publisher: str) -> tuple:
    """Route to appropriate PDF URL extractor based on publisher.
    Returns (pdf_url, verify_ssl)
    """
    publisher_lower = publisher.lower()

    if 'archimer' in publisher_lower:
        return get_archimer_pdf_url(url), True
    elif 'scientia' in publisher_lower:
        return get_scientia_marina_pdf_url(url), False  # SSL issues
    elif 'handle' in publisher_lower:
        return get_handle_net_pdf_url(url), False
    else:
        return url, False


def get_safe_filename(doi: str, lit_id) -> str:
    """Create safe filename from DOI."""
    safe_doi = re.sub(r'[^\w\-.]', '_', str(doi))
    if pd.notna(lit_id):
        return f"{int(lit_id)}.0_{safe_doi}.pdf"
    else:
        return f"{safe_doi}.pdf"


def main():
    # Load retry list
    if not INPUT_CSV.exists():
        print(f"Error: {INPUT_CSV} not found")
        return

    retry_df = pd.read_csv(INPUT_CSV)

    # Remove duplicates and rows with missing URLs
    retry_df = retry_df.dropna(subset=['oa_url'])
    retry_df = retry_df.drop_duplicates(subset=['oa_url'])

    print("=" * 70)
    print("SCRAPERS RETRY DOWNLOADER")
    print("=" * 70)
    print(f"Papers to retry: {len(retry_df)}")
    print()

    # Group by publisher
    publisher_counts = retry_df['publisher'].value_counts()
    for pub, count in publisher_counts.items():
        print(f"  {pub}: {count}")
    print()

    # Load database for year info
    db = pd.read_parquet(BASE_DIR / 'outputs/literature_review.parquet')
    id_to_year = dict(zip(
        pd.to_numeric(db['literature_id'], errors='coerce'),
        db['year']
    ))

    success = 0
    failed = 0
    already_exists = 0
    no_pdf = 0

    results = []

    for idx, row in retry_df.iterrows():
        oa_url = row['oa_url']
        doi = row['doi']
        lit_id = row['literature_id']
        publisher = row['publisher']

        print(f"\n[{success + failed + already_exists + no_pdf + 1}/{len(retry_df)}] {publisher}: {doi}")

        # Determine output path
        year = None
        if pd.notna(lit_id):
            year = id_to_year.get(float(lit_id))

        if year and not pd.isna(year):
            year_dir = OUTPUT_DIR / str(int(year))
        else:
            year_dir = OUTPUT_DIR / "unknown_year"

        filename = get_safe_filename(doi, lit_id)
        output_path = year_dir / filename

        # Skip if exists
        if output_path.exists():
            logging.info(f"Already exists: {filename}")
            already_exists += 1
            results.append({'doi': doi, 'publisher': publisher, 'status': 'exists', 'url': oa_url})
            continue

        # Get PDF URL using publisher-specific method
        pdf_url, verify_ssl = get_pdf_url_for_publisher(oa_url, publisher)

        if not pdf_url:
            logging.warning(f"No PDF URL found for {oa_url}")
            no_pdf += 1
            results.append({'doi': doi, 'publisher': publisher, 'status': 'no_pdf_url', 'url': oa_url})
            continue

        logging.info(f"PDF URL: {pdf_url}")

        # Download
        if download_pdf(pdf_url, output_path, verify_ssl=verify_ssl):
            success += 1
            results.append({'doi': doi, 'publisher': publisher, 'status': 'success', 'url': pdf_url})
        else:
            failed += 1
            results.append({'doi': doi, 'publisher': publisher, 'status': 'failed', 'url': pdf_url})

        # Rate limit - longer for Handle.net which hits many different servers
        if 'handle' in publisher.lower():
            time.sleep(2)
        else:
            time.sleep(1)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(BASE_DIR / 'logs/scrapers_retry_results.csv', index=False)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Success: {success}")
    print(f"Already exists: {already_exists}")
    print(f"No PDF found: {no_pdf}")
    print(f"Failed: {failed}")
    print(f"Total: {success + failed + already_exists + no_pdf}")
    print(f"\nNew PDFs downloaded: {success}")


if __name__ == "__main__":
    main()
