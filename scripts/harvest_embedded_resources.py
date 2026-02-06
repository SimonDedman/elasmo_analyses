#!/usr/bin/env python3
"""
Harvest Embedded Resources

Extracts and downloads from resources already present in the database:
1. DOIs embedded in citation text (DOI: 10.xxxx/xxx)
2. Direct PDF URLs in the pdf_url column
3. DOIs from doi.org URLs in pdf_url column

These are low-hanging fruit that don't require external API calls.

Author: Claude
Date: 2026-01-10
"""

import pandas as pd
import requests
import re
from pathlib import Path
import time
import logging
from urllib.parse import urlparse

# Configuration
BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "outputs/papers_without_doi.csv"
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_FILE = BASE_DIR / "logs/harvest_embedded_log.csv"
DISCOVERED_DOIS_FILE = BASE_DIR / "outputs/embedded_dois_discovered.csv"

# Ensure directories exist
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/harvest_embedded.log"),
        logging.StreamHandler()
    ]
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/pdf,*/*',
}

# Domains that block programmatic downloads
BLOCKED_DOMAINS = [
    'researchgate.net',
    'academia.edu',
    'jstor.org',
    'wiley.com',
    'springer.com',
    'sciencedirect.com',
    'tandfonline.com',
    'nature.com',
    'cambridge.org'
]


def extract_doi_from_text(text: str) -> str:
    """Extract DOI from citation text."""
    if pd.isna(text):
        return None

    # Pattern: DOI: 10.xxxx/xxxx or doi.org/10.xxxx/xxxx
    patterns = [
        r'DOI:\s*(10\.\d{4,}/[^\s,]+)',
        r'doi\.org/(10\.\d{4,}/[^\s,\)]+)',
        r'\b(10\.\d{4,}/[^\s,\)]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doi = match.group(1).rstrip('.')
            return doi

    return None


def extract_doi_from_url(url: str) -> str:
    """Extract DOI from doi.org or dx.doi.org URL."""
    if pd.isna(url):
        return None

    match = re.search(r'doi\.org/(10\.\d{4,}/[^\s]+)', url)
    if match:
        return match.group(1)
    return None


def is_direct_pdf_url(url: str) -> bool:
    """Check if URL is a direct PDF link (not from blocked domains)."""
    if pd.isna(url):
        return False

    url_lower = url.lower()

    # Check if it's from a blocked domain
    for domain in BLOCKED_DOMAINS:
        if domain in url_lower:
            return False

    # Check if it's a PDF link
    if url_lower.endswith('.pdf'):
        return True

    # Some URLs have PDF in path but not extension
    if '/pdf/' in url_lower:
        return True

    return False


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
            if b'<html' in content[:1000].lower():
                return {'status': 'html_instead', 'message': 'Got HTML instead of PDF'}
            return {'status': 'invalid', 'message': 'Not a valid PDF'}

        # Check size
        if len(content) < 10000:
            return {'status': 'too_small', 'message': f'PDF too small: {len(content)} bytes'}

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(content)

        return {
            'status': 'success',
            'size_bytes': len(content),
            'filename': output_path.name
        }

    except requests.exceptions.Timeout:
        return {'status': 'timeout', 'message': 'Request timed out'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def get_safe_filename(lit_id, doi_or_title: str) -> str:
    """Create safe filename."""
    if doi_or_title:
        safe_name = re.sub(r'[^\w\-.]', '_', str(doi_or_title))[:60]
    else:
        safe_name = "unknown"

    if pd.notna(lit_id):
        return f"{int(lit_id)}.0_{safe_name}.pdf"
    return f"{safe_name}.pdf"


def get_year_from_db(lit_id, db):
    """Get year for a literature ID from the main database."""
    if pd.isna(lit_id):
        return None

    match = db[db['literature_id'] == lit_id]
    if not match.empty:
        year = match.iloc[0].get('year')
        if pd.notna(year):
            return int(year)
    return None


def main():
    print("=" * 70)
    print("HARVEST EMBEDDED RESOURCES")
    print("=" * 70)

    # Load input data
    if not INPUT_CSV.exists():
        print(f"Error: {INPUT_CSV} not found")
        return

    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df):,} papers without DOI")

    # Load main database for year info
    db = pd.read_parquet(BASE_DIR / 'outputs/literature_review.parquet')

    # Phase 1: Extract DOIs from citation text
    print("\n" + "-" * 70)
    print("PHASE 1: Extracting DOIs from citation text")
    print("-" * 70)

    dois_from_citation = []
    for idx, row in df.iterrows():
        citation = row.get('citation', '')
        doi = extract_doi_from_text(citation)
        if doi:
            dois_from_citation.append({
                'literature_id': row['literature_id'],
                'doi': doi,
                'source': 'citation_text',
                'title': row.get('title', '')
            })

    print(f"Found {len(dois_from_citation)} DOIs embedded in citation text")

    # Phase 2: Extract DOIs from pdf_url column
    print("\n" + "-" * 70)
    print("PHASE 2: Extracting DOIs from doi.org URLs")
    print("-" * 70)

    dois_from_url = []
    for idx, row in df.iterrows():
        url = row.get('pdf_url', '')
        if pd.notna(url) and 'doi.org' in str(url):
            doi = extract_doi_from_url(url)
            if doi:
                # Check if already found
                if not any(d['doi'] == doi for d in dois_from_citation):
                    dois_from_url.append({
                        'literature_id': row['literature_id'],
                        'doi': doi,
                        'source': 'pdf_url_doi',
                        'title': row.get('title', '')
                    })

    print(f"Found {len(dois_from_url)} additional DOIs from doi.org URLs")

    # Combine and save discovered DOIs
    all_discovered = dois_from_citation + dois_from_url
    if all_discovered:
        discovered_df = pd.DataFrame(all_discovered)
        discovered_df.to_csv(DISCOVERED_DOIS_FILE, index=False)
        print(f"\nSaved {len(all_discovered)} discovered DOIs to {DISCOVERED_DOIS_FILE}")

    # Phase 3: Download from direct PDF URLs
    print("\n" + "-" * 70)
    print("PHASE 3: Downloading from direct PDF URLs")
    print("-" * 70)

    direct_pdf_rows = df[df['pdf_url'].apply(is_direct_pdf_url)]
    print(f"Found {len(direct_pdf_rows)} papers with direct PDF URLs")

    results = []
    success = 0
    failed = 0
    skipped = 0

    for idx, row in direct_pdf_rows.iterrows():
        lit_id = row['literature_id']
        url = row['pdf_url']
        title = row.get('title', '')

        # Determine output path
        year = get_year_from_db(lit_id, db)
        if year:
            year_dir = OUTPUT_DIR / str(int(year))
        else:
            year_dir = OUTPUT_DIR / "unknown_year"

        filename = get_safe_filename(lit_id, title)
        output_path = year_dir / filename

        # Skip if exists
        if output_path.exists():
            print(f"[SKIP] Already exists: {filename}")
            skipped += 1
            results.append({
                'literature_id': lit_id,
                'url': url,
                'status': 'already_exists',
                'filename': filename
            })
            continue

        print(f"\n[{success + failed + 1}/{len(direct_pdf_rows)}] {title[:50]}...")
        print(f"  URL: {url}")

        # Download
        result = download_pdf(url, output_path)
        result['literature_id'] = lit_id
        result['url'] = url
        result['title'] = title
        results.append(result)

        if result['status'] == 'success':
            success += 1
            print(f"  [OK] Downloaded: {result.get('filename')} ({result.get('size_bytes', 0):,} bytes)")
        else:
            failed += 1
            print(f"  [FAIL] {result.get('status')}: {result.get('message', '')}")

        # Rate limit
        time.sleep(1)

    # Save results
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nDOIs discovered:")
    print(f"  From citation text: {len(dois_from_citation)}")
    print(f"  From doi.org URLs:  {len(dois_from_url)}")
    print(f"  Total:              {len(all_discovered)}")
    print(f"\nDirect PDF downloads:")
    print(f"  Success:       {success}")
    print(f"  Already exist: {skipped}")
    print(f"  Failed:        {failed}")
    print(f"  Total:         {success + failed + skipped}")

    if all_discovered:
        print(f"\n[!] Next step: Run Unpaywall on the {len(all_discovered)} discovered DOIs")
        print(f"    File: {DISCOVERED_DOIS_FILE}")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
