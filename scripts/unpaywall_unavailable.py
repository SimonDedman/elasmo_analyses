#!/usr/bin/env python3
"""
Query Unpaywall API for unavailable papers and download OA versions.
"""

import requests
import sqlite3
import time
import re
import os
import shutil
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Configuration
EMAIL = "simon.dedman@ucd.ie"  # Required by Unpaywall API
API_BASE = "https://api.unpaywall.org/v2"
RATE_LIMIT_DELAY = 0.15  # 150ms between requests
MAX_RETRIES = 3

# Paths
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "database" / "download_tracker.db"
SHARKPAPERS_PATH = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = PROJECT_DIR / "logs"
OUTPUT_DIR = PROJECT_DIR / "outputs"

LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def get_unavailable_papers_with_dois():
    """Get unavailable papers that have DOIs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.status = 'unavailable'
        AND p.doi IS NOT NULL
        AND p.doi != ''
    """)
    papers = cursor.fetchall()
    conn.close()
    return papers


def lookup_unpaywall(doi):
    """Query Unpaywall API for a single DOI."""
    url = f"{API_BASE}/{doi}?email={EMAIL}"

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            elif response.status_code == 429:
                print(f"  Rate limited, waiting 60s...")
                time.sleep(60)
                continue
            else:
                return None
        except Exception as e:
            time.sleep(5)

    return None


def download_pdf(url, dest_path):
    """Download PDF from URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type.lower() or url.endswith('.pdf'):
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Verify it's a PDF
                with open(dest_path, 'rb') as f:
                    header = f.read(5)
                    if header == b'%PDF-':
                        return True
                os.remove(dest_path)
        return False
    except Exception as e:
        if dest_path.exists():
            os.remove(dest_path)
        return False


def generate_filename(title, authors, year):
    """Generate proper filename."""
    if authors:
        first_author = authors.split(',')[0].strip()
        parts = first_author.split()
        author_name = parts[-1].replace(' ', '') if parts else "Unknown"
    else:
        author_name = "Unknown"

    title_words = re.sub(r'[^\w\s]', '', title or "Untitled").split()[:8]
    title_part = ' '.join(title_words)

    has_multiple = authors and (',' in authors or '&' in authors or ' and ' in authors.lower())
    etal = ".etal" if has_multiple else ""

    year_str = str(int(year)) if year else "unknown_year"
    return f"{author_name}{etal}.{year_str}.{title_part}.pdf"


def mark_as_downloaded(paper_id, file_path):
    """Mark paper as downloaded in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE download_status
        SET status = 'downloaded',
            download_date = datetime('now'),
            source = 'unpaywall',
            notes = ?
        WHERE paper_id = ?
    """, (str(file_path), paper_id))
    conn.commit()
    conn.close()


def main():
    print("=" * 60)
    print("UNPAYWALL OPEN ACCESS DOWNLOAD")
    print("=" * 60)
    print(f"Started: {datetime.now()}")

    # Get unavailable papers with DOIs
    papers = get_unavailable_papers_with_dois()
    print(f"Found {len(papers)} unavailable papers with DOIs")

    # Track results
    found_oa = 0
    downloaded = 0
    no_oa = 0
    errors = 0

    log_file = LOG_DIR / f"unpaywall_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    with open(log_file, 'w') as log:
        log.write("paper_id,doi,status,oa_url,file_path\n")

        for i, (paper_id, doi, title, authors, year) in enumerate(papers):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(papers)} - Found OA: {found_oa}, Downloaded: {downloaded}")

            # Query Unpaywall
            data = lookup_unpaywall(doi)
            time.sleep(RATE_LIMIT_DELAY)

            if not data or not data.get('is_oa'):
                no_oa += 1
                log.write(f"{paper_id},{doi},no_oa,,\n")
                continue

            found_oa += 1

            # Get best OA URL
            best_oa = data.get('best_oa_location', {}) or {}
            pdf_url = best_oa.get('url_for_pdf') or best_oa.get('url')

            if not pdf_url:
                log.write(f"{paper_id},{doi},no_url,,\n")
                continue

            # Generate filename and path
            filename = generate_filename(title, authors, year)
            year_str = str(int(year)) if year else "unknown_year"
            year_folder = SHARKPAPERS_PATH / year_str
            year_folder.mkdir(parents=True, exist_ok=True)
            dest_path = year_folder / filename

            if dest_path.exists():
                mark_as_downloaded(paper_id, dest_path)
                downloaded += 1
                log.write(f"{paper_id},{doi},already_exists,{pdf_url},{dest_path}\n")
                print(f"  [{i}] Already exists: {filename}")
                continue

            # Download
            print(f"  [{i}] Downloading: {title[:50]}...")
            if download_pdf(pdf_url, dest_path):
                mark_as_downloaded(paper_id, dest_path)
                downloaded += 1
                log.write(f"{paper_id},{doi},downloaded,{pdf_url},{dest_path}\n")
                print(f"       -> {filename}")
            else:
                errors += 1
                log.write(f"{paper_id},{doi},download_failed,{pdf_url},\n")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total papers checked: {len(papers)}")
    print(f"Found with OA:        {found_oa}")
    print(f"Successfully downloaded: {downloaded}")
    print(f"No OA available:      {no_oa}")
    print(f"Download errors:      {errors}")
    print(f"\nLog saved to: {log_file}")


if __name__ == "__main__":
    main()
