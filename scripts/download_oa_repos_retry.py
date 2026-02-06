#!/usr/bin/env python3
"""
OA Repository Retry Downloader

Retries downloads from open access repositories:
- PubMed Central (PMC)
- Zenodo
- PeerJ
- Figshare
- BioMed Central
- PLOS

Uses repository-specific strategies to improve success rates.

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
INPUT_CSV = BASE_DIR / "outputs/oa_repos_retry.csv"
LOG_FILE = BASE_DIR / "logs/oa_repos_retry.log"

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


def get_pmc_pdf_url(pmc_url: str) -> str:
    """Extract PDF URL from PubMed Central page."""
    try:
        # Convert various PMC URL formats to PDF URL
        # e.g., https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567
        # -> https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567/pdf/

        # Handle old format: /pmc/articles/1234567
        if '/pmc/articles/' in pmc_url:
            match = re.search(r'/pmc/articles/(?:PMC)?(\d+)', pmc_url)
            if match:
                pmc_id = match.group(1)
                return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"

        # Handle pmc.ncbi format with direct PDF link
        if 'pmc.ncbi.nlm.nih.gov' in pmc_url and '/pdf/' in pmc_url:
            return pmc_url

        # Fetch the page and look for PDF link
        response = requests.get(pmc_url, headers=HEADERS, timeout=30, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for PDF link in the page
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/pdf/' in href or href.endswith('.pdf'):
                if href.startswith('http'):
                    return href
                return urljoin(pmc_url, href)

        return None
    except Exception as e:
        logging.error(f"Error getting PMC PDF URL: {e}")
        return None


def get_zenodo_pdf_url(zenodo_url: str) -> str:
    """Extract PDF URL from Zenodo record page."""
    try:
        response = requests.get(zenodo_url, headers=HEADERS, timeout=30, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for files download section
        # Zenodo typically has links like /record/XXXXX/files/filename.pdf
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/files/' in href and '.pdf' in href.lower():
                if href.startswith('http'):
                    return href
                return urljoin(zenodo_url, href)

        # Alternative: look for any PDF link
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf'):
                if href.startswith('http'):
                    return href
                return urljoin(zenodo_url, href)

        return None
    except Exception as e:
        logging.error(f"Error getting Zenodo PDF URL: {e}")
        return None


def get_peerj_pdf_url(peerj_url: str) -> str:
    """Get direct PDF URL from PeerJ."""
    try:
        # Handle preprints: peerj.com/preprints/XXX -> peerj.com/preprints/XXX.pdf
        if '/preprints/' in peerj_url:
            # Remove version suffix if present (v1, v2, etc.)
            base_url = re.sub(r'v\d+$', '', peerj_url.rstrip('/'))
            return base_url + '.pdf'

        # Handle regular articles: peerj.com/articles/XXXX -> peerj.com/articles/XXXX.pdf
        if '/articles/' in peerj_url:
            base_url = peerj_url.rstrip('/').replace('.pdf', '')
            return base_url + '.pdf'

        # Handle DOI redirect
        if 'doi.org' in peerj_url:
            response = requests.get(peerj_url, headers=HEADERS, timeout=30, allow_redirects=True)
            final_url = response.url
            if 'peerj.com' in final_url:
                return get_peerj_pdf_url(final_url)

        # Direct PDF link
        if peerj_url.endswith('.pdf'):
            return peerj_url

        return peerj_url + '.pdf'
    except Exception as e:
        logging.error(f"Error getting PeerJ PDF URL: {e}")
        return None


def get_figshare_pdf_url(figshare_url: str) -> str:
    """Extract PDF URL from Figshare page."""
    try:
        response = requests.get(figshare_url, headers=HEADERS, timeout=30, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for download button/link
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text(strip=True).lower()

            # Look for download links
            if 'download' in link_text or 'ndownloader' in href:
                if href.startswith('http'):
                    return href
                return urljoin(figshare_url, href)

        # Look for files section
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '.pdf' in href.lower():
                if href.startswith('http'):
                    return href
                return urljoin(figshare_url, href)

        return None
    except Exception as e:
        logging.error(f"Error getting Figshare PDF URL: {e}")
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
            logging.warning(f"Invalid PDF magic bytes: {content[:20]}")
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


def get_pdf_url_for_publisher(url: str, publisher: str) -> str:
    """Route to appropriate PDF URL extractor based on publisher."""
    publisher_lower = publisher.lower()

    if 'pubmed' in publisher_lower or 'pmc' in publisher_lower:
        return get_pmc_pdf_url(url)
    elif 'zenodo' in publisher_lower:
        return get_zenodo_pdf_url(url)
    elif 'peerj' in publisher_lower:
        return get_peerj_pdf_url(url)
    elif 'figshare' in publisher_lower:
        return get_figshare_pdf_url(url)
    else:
        # Generic: try to use the URL directly or fetch and scrape
        return url


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
    print("OA REPOSITORY RETRY DOWNLOADER")
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

    results = []

    for idx, row in retry_df.iterrows():
        oa_url = row['oa_url']
        doi = row['doi']
        lit_id = row['literature_id']
        publisher = row['publisher']

        print(f"\n[{success + failed + already_exists + 1}/{len(retry_df)}] {publisher}: {doi}")

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
            results.append({'doi': doi, 'status': 'exists', 'url': oa_url})
            continue

        # Get PDF URL using publisher-specific method
        pdf_url = get_pdf_url_for_publisher(oa_url, publisher)

        if not pdf_url:
            logging.warning(f"No PDF URL found for {oa_url}")
            failed += 1
            results.append({'doi': doi, 'status': 'no_pdf_url', 'url': oa_url})
            continue

        logging.info(f"PDF URL: {pdf_url}")

        # Download
        if download_pdf(pdf_url, output_path):
            success += 1
            results.append({'doi': doi, 'status': 'success', 'url': pdf_url})
        else:
            failed += 1
            results.append({'doi': doi, 'status': 'failed', 'url': pdf_url})

        # Rate limit
        time.sleep(1)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(BASE_DIR / 'logs/oa_repos_retry_results.csv', index=False)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Success: {success}")
    print(f"Already exists: {already_exists}")
    print(f"Failed: {failed}")
    print(f"Total: {success + failed + already_exists}")
    print(f"\nNew PDFs downloaded: {success}")


if __name__ == "__main__":
    main()
