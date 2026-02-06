#!/usr/bin/env python3
"""
Download Discovered DOIs

Downloads papers for DOIs discovered from embedded resources:
1. First tries Unpaywall for OA versions
2. Falls back to Sci-Hub if no OA version

Input: outputs/embedded_dois_discovered.csv
Output: PDFs to SharkPapers directory

Author: Claude
Date: 2026-01-10
"""

import pandas as pd
import requests
from pathlib import Path
import time
import logging
import re
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "outputs/embedded_dois_discovered.csv"
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_FILE = BASE_DIR / "logs/discovered_dois_download_log.csv"

# Unpaywall config
UNPAYWALL_EMAIL = "your@email.com"  # Replace with your email
UNPAYWALL_API = "https://api.unpaywall.org/v2"

# Sci-Hub mirrors
SCIHUB_MIRRORS = [
    "https://sci-hub.se",
    "https://sci-hub.st",
    "https://sci-hub.ru"
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/discovered_dois_download.log"),
        logging.StreamHandler()
    ]
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/pdf,*/*',
}


def get_unpaywall_pdf_url(doi: str) -> dict:
    """Query Unpaywall for OA PDF URL."""
    try:
        url = f"{UNPAYWALL_API}/{doi}?email={UNPAYWALL_EMAIL}"
        response = requests.get(url, timeout=15)

        if response.status_code == 404:
            return {'status': 'not_found', 'is_oa': False}

        if response.status_code != 200:
            return {'status': 'error', 'message': f'HTTP {response.status_code}'}

        data = response.json()

        if not data.get('is_oa'):
            return {'status': 'closed', 'is_oa': False}

        # Get best OA location
        best_location = data.get('best_oa_location', {})
        pdf_url = best_location.get('url_for_pdf') or best_location.get('url')

        if pdf_url:
            return {
                'status': 'found',
                'is_oa': True,
                'pdf_url': pdf_url,
                'oa_status': data.get('oa_status'),
                'host_type': best_location.get('host_type')
            }

        return {'status': 'no_pdf_url', 'is_oa': True}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def try_scihub(doi: str) -> str:
    """Try to get PDF URL from Sci-Hub."""
    from bs4 import BeautifulSoup

    for mirror in SCIHUB_MIRRORS:
        try:
            url = f"{mirror}/{doi}"
            response = requests.get(url, headers=HEADERS, timeout=30, verify=False)

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for PDF embed
            embed = soup.find('embed', {'type': 'application/pdf'})
            if embed and embed.get('src'):
                pdf_url = embed['src']
                if pdf_url.startswith('//'):
                    pdf_url = 'https:' + pdf_url
                return pdf_url

            # Look for iframe
            iframe = soup.find('iframe', id='pdf')
            if iframe and iframe.get('src'):
                pdf_url = iframe['src']
                if pdf_url.startswith('//'):
                    pdf_url = 'https:' + pdf_url
                return pdf_url

        except Exception:
            continue

    return None


def download_pdf(url: str, output_path: Path) -> dict:
    """Download PDF from URL."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=60,
            verify=False,
            allow_redirects=True
        )
        response.raise_for_status()

        content = response.content

        # Check magic bytes
        if not content[:4] == b'%PDF':
            return {'status': 'not_pdf', 'message': 'Invalid PDF'}

        if len(content) < 10000:
            return {'status': 'too_small', 'message': f'{len(content)} bytes'}

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(content)

        return {'status': 'success', 'size_bytes': len(content)}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def get_safe_filename(doi: str, lit_id) -> str:
    """Create safe filename from DOI."""
    safe_doi = re.sub(r'[^\w\-.]', '_', str(doi))
    if pd.notna(lit_id):
        return f"{int(lit_id)}.0_{safe_doi}.pdf"
    return f"{safe_doi}.pdf"


def main():
    print("=" * 70)
    print("DOWNLOAD DISCOVERED DOIs")
    print("=" * 70)

    if not INPUT_CSV.exists():
        print(f"Error: {INPUT_CSV} not found")
        print("Run harvest_embedded_resources.py first")
        return

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df):,} discovered DOIs")

    # Load main database for year info
    db = pd.read_parquet(BASE_DIR / 'outputs/literature_review.parquet')
    id_to_year = dict(zip(
        pd.to_numeric(db['literature_id'], errors='coerce'),
        db['year']
    ))

    results = []
    success_unpaywall = 0
    success_scihub = 0
    failed = 0
    already_exists = 0

    for idx, row in df.iterrows():
        doi = row['doi']
        lit_id = row['literature_id']
        title = row.get('title', '')[:50]

        print(f"\n[{idx + 1}/{len(df)}] {doi}")
        print(f"  Title: {title}...")

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
            print(f"  [SKIP] Already exists")
            already_exists += 1
            results.append({
                'doi': doi,
                'literature_id': lit_id,
                'status': 'already_exists',
                'source': 'existing',
                'timestamp': datetime.now().isoformat()
            })
            continue

        # Try Unpaywall first
        print(f"  Checking Unpaywall...")
        unpaywall = get_unpaywall_pdf_url(doi)

        if unpaywall.get('status') == 'found':
            pdf_url = unpaywall['pdf_url']
            print(f"  [OA] {unpaywall.get('oa_status')} - {unpaywall.get('host_type')}")

            result = download_pdf(pdf_url, output_path)

            if result['status'] == 'success':
                print(f"  [OK] Downloaded via Unpaywall ({result['size_bytes']:,} bytes)")
                success_unpaywall += 1
                results.append({
                    'doi': doi,
                    'literature_id': lit_id,
                    'status': 'success',
                    'source': 'unpaywall',
                    'oa_status': unpaywall.get('oa_status'),
                    'size_bytes': result['size_bytes'],
                    'timestamp': datetime.now().isoformat()
                })
                time.sleep(1)
                continue
            else:
                print(f"  [FAIL] Unpaywall download failed: {result.get('message')}")

        # Try Sci-Hub
        print(f"  Trying Sci-Hub...")
        scihub_url = try_scihub(doi)

        if scihub_url:
            result = download_pdf(scihub_url, output_path)

            if result['status'] == 'success':
                print(f"  [OK] Downloaded via Sci-Hub ({result['size_bytes']:,} bytes)")
                success_scihub += 1
                results.append({
                    'doi': doi,
                    'literature_id': lit_id,
                    'status': 'success',
                    'source': 'scihub',
                    'size_bytes': result['size_bytes'],
                    'timestamp': datetime.now().isoformat()
                })
                time.sleep(2)
                continue

        # Both failed
        print(f"  [FAIL] Not available")
        failed += 1
        results.append({
            'doi': doi,
            'literature_id': lit_id,
            'status': 'not_found',
            'source': 'none',
            'unpaywall_status': unpaywall.get('status'),
            'timestamp': datetime.now().isoformat()
        })

        time.sleep(1)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total DOIs processed: {len(df)}")
    print(f"Already existed:      {already_exists}")
    print(f"Downloaded (Unpaywall): {success_unpaywall}")
    print(f"Downloaded (Sci-Hub):   {success_scihub}")
    print(f"Not available:        {failed}")
    print(f"\nNew PDFs downloaded: {success_unpaywall + success_scihub}")
    print(f"Log saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()
