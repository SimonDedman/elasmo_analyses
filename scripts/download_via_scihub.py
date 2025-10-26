#!/usr/bin/env python3
"""
download_via_scihub.py

EDUCATIONAL/RESEARCH USE ONLY - Download papers via Sci-Hub as last resort.

⚠️  IMPORTANT LEGAL NOTICE ⚠️
This script accesses Sci-Hub, which may violate copyright laws in some jurisdictions.
Use only for:
- Educational research purposes
- Papers not available through legitimate channels
- Jurisdictions where this is legally permissible

Author: Simon Dedman / Claude
Date: 2025-10-22
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
import argparse
from tqdm import tqdm
import logging
import sys

# Add parent for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import get_pdf_filename, OUTPUT_DIR

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
SCIHUB_LOG = BASE_DIR / "logs/scihub_download_log.csv"

# Sci-Hub mirrors (check https://sci-hub.st for current mirrors)
SCIHUB_MIRRORS = [
    "https://sci-hub.st",
    "https://sci-hub.se",
    "https://sci-hub.ru"
]

# Rate limiting (be respectful!)
DELAY_BETWEEN_REQUESTS = 3.0  # seconds
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2

# User agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# ============================================================================
# SCI-HUB FUNCTIONS
# ============================================================================

def check_scihub_availability():
    """Check which Sci-Hub mirrors are available."""
    print("\n🔍 Checking Sci-Hub mirror availability...")
    available = []

    for mirror in SCIHUB_MIRRORS:
        try:
            response = requests.get(mirror, timeout=10, headers={'User-Agent': USER_AGENT})
            if response.status_code == 200:
                available.append(mirror)
                print(f"✅ {mirror} - Available")
            else:
                print(f"❌ {mirror} - HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {mirror} - {str(e)[:50]}")

    return available


def download_from_scihub(doi, mirror, output_path, lit_id):
    """
    Download paper from Sci-Hub using DOI.

    Args:
        doi: Paper DOI
        mirror: Sci-Hub mirror URL
        output_path: Where to save PDF
        lit_id: Literature ID

    Returns:
        dict with status, message, file_size
    """
    if not doi:
        return {'status': 'no_doi', 'message': 'No DOI available', 'file_size': 0}

    # Construct Sci-Hub URL using DOI format: http://dx.doi.org/DOI
    doi_url = f"http://dx.doi.org/{doi}"
    scihub_url = f"{mirror}/{doi_url}"

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    for attempt in range(MAX_RETRIES):
        try:
            # Get Sci-Hub page
            response = requests.get(scihub_url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '').lower()

                # Check if we got a PDF directly
                if 'application/pdf' in content_type:
                    # Save PDF
                    with open(output_path, 'wb') as f:
                        f.write(response.content)

                    file_size = output_path.stat().st_size

                    # Verify PDF
                    with open(output_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            return {
                                'status': 'success',
                                'message': 'Downloaded via Sci-Hub',
                                'file_size': file_size
                            }
                        else:
                            output_path.unlink()
                            return {
                                'status': 'error',
                                'message': 'Not a valid PDF',
                                'file_size': 0
                            }

                # Got HTML page - look for PDF link in response
                elif 'text/html' in content_type:
                    # Check for "article is missing" message (Russian and English, case-insensitive)
                    response_lower = response.text.lower()
                    if 'отсутствует в базе' in response_lower or 'article not found' in response_lower or 'article is not found' in response_lower:
                        return {
                            'status': 'not_in_scihub',
                            'message': 'Article missing from Sci-Hub database',
                            'file_size': 0
                        }

                    # Use BeautifulSoup for reliable HTML parsing
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')

                    pdf_url = None

                    # Look for embed tag with PDF
                    embed_tag = soup.find('embed', {'type': 'application/pdf'})
                    if embed_tag and embed_tag.get('src'):
                        pdf_url = embed_tag['src']

                    # Look for iframe with PDF
                    if not pdf_url:
                        iframe_tag = soup.find('iframe', src=lambda x: x and '.pdf' in x)
                        if iframe_tag and iframe_tag.get('src'):
                            pdf_url = iframe_tag['src']

                    # Look for any tag with PDF src
                    if not pdf_url:
                        for tag in soup.find_all(src=True):
                            if '.pdf' in tag['src']:
                                pdf_url = tag['src']
                                break

                    if pdf_url:
                        # Make absolute URL if relative
                        if pdf_url.startswith('//'):
                            pdf_url = f"https:{pdf_url}"
                        elif not pdf_url.startswith('http'):
                            pdf_url = f"{mirror}/{pdf_url.lstrip('/')}"

                        # Download PDF from this URL
                        pdf_response = requests.get(pdf_url, headers=headers, timeout=REQUEST_TIMEOUT)
                        if pdf_response.status_code == 200:
                            with open(output_path, 'wb') as f:
                                f.write(pdf_response.content)

                            file_size = output_path.stat().st_size

                            # Verify PDF
                            with open(output_path, 'rb') as f:
                                header = f.read(4)
                                if header == b'%PDF':
                                    return {
                                        'status': 'success',
                                        'message': 'Downloaded via Sci-Hub (extracted link)',
                                        'file_size': file_size
                                    }
                                else:
                                    output_path.unlink()

                    return {
                        'status': 'error',
                        'message': 'Could not extract PDF from Sci-Hub page',
                        'file_size': 0
                    }

            elif response.status_code == 404:
                return {
                    'status': 'not_found',
                    'message': 'Not found on Sci-Hub',
                    'file_size': 0
                }
            else:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'file_size': 0
                }

        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return {
                'status': 'timeout',
                'message': 'Request timed out',
                'file_size': 0
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Unexpected error: {str(e)}',
                'file_size': 0
            }

    return {
        'status': 'error',
        'message': 'Max retries exceeded',
        'file_size': 0
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Download papers via Sci-Hub (educational use only)")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to attempt")
    parser.add_argument('--start-year', type=int, help="Start from this year")
    parser.add_argument('--end-year', type=int, help="End at this year")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("SCI-HUB DOWNLOADER")
    print("=" * 80)
    print("⚠️  EDUCATIONAL/RESEARCH USE ONLY")
    print("⚠️  Check local laws regarding copyright and access")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check Sci-Hub availability
    available_mirrors = check_scihub_availability()

    if not available_mirrors:
        print("\n❌ No Sci-Hub mirrors are available. Exiting.")
        return

    mirror = available_mirrors[0]
    print(f"\n✅ Using mirror: {mirror}")

    # Load database
    print(f"\n📖 Loading database...")
    db = pd.read_parquet(DATABASE_PARQUET)
    print(f"✅ Loaded {len(db):,} papers")

    # Filter papers without PDFs and with DOIs
    needs_pdf = db[~db['pdf_url'].notna() | (db['pdf_url'] == '')]
    has_doi = needs_pdf[needs_pdf['doi'].notna() & (needs_pdf['doi'] != '')]

    print(f"📊 Papers without PDFs: {len(needs_pdf):,}")
    print(f"📊 Papers with DOI: {len(has_doi):,}")

    # Apply year filters
    if args.start_year or args.end_year:
        if args.start_year:
            has_doi = has_doi[has_doi['year'] >= args.start_year]
        if args.end_year:
            has_doi = has_doi[has_doi['year'] <= args.end_year]
        print(f"📊 After year filter: {len(has_doi):,}")

    # Sort by year (recent first)
    has_doi = has_doi.sort_values('year', ascending=False, na_position='last')

    # Limit if requested
    if args.max_papers:
        has_doi = has_doi.head(args.max_papers)
        print(f"📊 Limited to: {args.max_papers:,} papers")

    if len(has_doi) == 0:
        print("\n⚠️  No papers to download")
        return

    # Download
    print(f"\n{'=' * 80}")
    print(f"DOWNLOADING {len(has_doi):,} PAPERS")
    print("=" * 80)

    results = []
    success_count = 0

    for idx, row in tqdm(has_doi.iterrows(), total=len(has_doi), desc="Downloading"):
        lit_id = row['literature_id']
        doi = row['doi']
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year', 'unknown')

        # Create output path
        filename = get_pdf_filename(authors, title, year)
        output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download from Sci-Hub
        result = download_from_scihub(doi, mirror, output_path, lit_id)

        if result['status'] == 'success':
            success_count += 1

        results.append({
            'literature_id': lit_id,
            'doi': doi,
            'status': result['status'],
            'message': result['message'],
            'file_size': result['file_size'],
            'year': year,
            'timestamp': datetime.now().isoformat()
        })

        # Respectful delay
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save log
    results_df = pd.DataFrame(results)
    results_df.to_csv(SCIHUB_LOG, index=False)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✅ Successfully downloaded: {success_count:,}/{len(has_doi):,}")
    print(f"📊 Success rate: {success_count/len(has_doi)*100:.1f}%")
    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status}: {len(group):,}")
    print(f"\n📄 Log saved: {SCIHUB_LOG}")
    print("=" * 80)


if __name__ == "__main__":
    main()
