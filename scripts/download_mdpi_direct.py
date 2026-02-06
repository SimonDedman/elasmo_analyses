#!/usr/bin/env python3
"""
Direct HTTP downloader for MDPI open access papers.
MDPI is fully open access - no authentication needed.
"""

import os
import sys
import re
import time
import sqlite3
import logging
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Setup paths
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "database" / "download_tracker.db"
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = PROJECT_DIR / "logs"

# Setup logging
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"mdpi_direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Request settings
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/pdf,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Clean a string for use as a filename."""
    # Remove/replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.replace('\n', ' ').replace('\r', '')
    # Truncate if needed
    if len(name) > max_length:
        name = name[:max_length].rsplit(' ', 1)[0]
    return name


def format_authors(authors_str: str) -> str:
    """Format authors string for filename."""
    if not authors_str:
        return "Unknown"

    # Split by common separators
    authors = re.split(r'[,;&]|\band\b', authors_str)
    authors = [a.strip() for a in authors if a.strip()]

    if not authors:
        return "Unknown"

    # Get first author's last name
    first_author = authors[0]
    # Try to get last name (handle "Last, First" and "First Last" formats)
    if ',' in first_author:
        last_name = first_author.split(',')[0].strip()
    else:
        parts = first_author.split()
        last_name = parts[-1] if parts else first_author

    if len(authors) == 1:
        return last_name
    elif len(authors) == 2:
        return f"{last_name}.{authors[1].split()[-1] if authors[1].split() else authors[1]}"
    else:
        return f"{last_name}.etal"


def get_pdf_url_from_doi(doi: str) -> str:
    """Construct MDPI PDF URL from DOI."""
    # MDPI DOI format: 10.3390/journalVOLUMEISSUEARTICLE or 10.3390/journal/volumeissue/article
    # PDF URL: https://www.mdpi.com/DOI_SUFFIX/pdf

    doi_suffix = doi.replace('10.3390/', '')
    return f"https://www.mdpi.com/{doi_suffix}/pdf"


def download_pdf(url: str, output_path: Path, session: requests.Session) -> bool:
    """Download PDF from URL."""
    try:
        response = session.get(url, headers=HEADERS, timeout=60, stream=True)

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')

            # Check if it's a PDF
            if 'application/pdf' in content_type or url.endswith('/pdf'):
                # Check content starts with PDF magic bytes
                content = response.content
                if content[:4] == b'%PDF':
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(content)
                    return True
                else:
                    logger.warning(f"Response is not a PDF (no PDF header)")
                    return False
            else:
                logger.warning(f"Unexpected content type: {content_type}")
                return False
        elif response.status_code == 404:
            logger.warning(f"PDF not found (404)")
            return False
        else:
            logger.warning(f"HTTP {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return False
    except Exception as e:
        logger.error(f"Download error: {e}")
        return False


def check_existing_pdf(paper_id: int, authors: str, year: int, title: str) -> Path | None:
    """Check if PDF already exists in the library."""
    author_prefix = format_authors(authors)
    year_str = str(int(year)) if year else "unknown"

    # Check year folder
    year_folder = OUTPUT_DIR / year_str
    if year_folder.exists():
        # Look for matching file
        title_words = sanitize_filename(title)[:50].lower() if title else ""
        for pdf in year_folder.glob("*.pdf"):
            pdf_lower = pdf.stem.lower()
            if author_prefix.lower().split('.')[0] in pdf_lower:
                if title_words and any(word in pdf_lower for word in title_words.split()[:3] if len(word) > 3):
                    return pdf

    return None


def update_download_status(paper_id: int, status: str, source: str, notes: str = None):
    """Update the download status in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO download_status (paper_id, status, download_date, source, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (paper_id, status, datetime.now().isoformat(), source, notes))

    conn.commit()
    conn.close()


def get_mdpi_papers():
    """Get all MDPI papers that need downloading."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.id, p.doi, p.authors, p.year, p.title
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.paper_id IS NULL
          AND p.doi LIKE '10.3390/%'
        ORDER BY p.year DESC
    ''')

    papers = cursor.fetchall()
    conn.close()
    return papers


def main():
    logger.info("=" * 70)
    logger.info("MDPI Direct Downloader")
    logger.info("=" * 70)

    papers = get_mdpi_papers()
    logger.info(f"Found {len(papers)} MDPI papers to download")

    if not papers:
        logger.info("No papers to download!")
        return

    # Create session with connection pooling
    session = requests.Session()

    # Stats
    downloaded = 0
    already_exist = 0
    failed = 0

    for i, (paper_id, doi, authors, year, title) in enumerate(papers, 1):
        logger.info(f"\n[{i}/{len(papers)}] {doi}")
        logger.info(f"  Title: {title[:60]}..." if title and len(title) > 60 else f"  Title: {title}")

        # Check if already exists
        existing = check_existing_pdf(paper_id, authors, year, title)
        if existing:
            logger.info(f"  EXISTS: {existing.name}")
            update_download_status(paper_id, 'downloaded', 'existing', str(existing))
            already_exist += 1
            continue

        # Construct filename
        author_part = format_authors(authors)
        year_str = str(int(year)) if year else "unknown"
        title_part = sanitize_filename(title)[:80] if title else "untitled"
        filename = f"{author_part}.{year_str}.{title_part}.pdf"

        # Output path
        year_folder = OUTPUT_DIR / year_str
        output_path = year_folder / filename

        # Get PDF URL and download
        pdf_url = get_pdf_url_from_doi(doi)
        logger.info(f"  URL: {pdf_url}")

        if download_pdf(pdf_url, output_path, session):
            logger.info(f"  OK: {filename}")
            update_download_status(paper_id, 'downloaded', 'mdpi_direct', str(output_path))
            downloaded += 1
        else:
            # Try alternate URL format
            alt_url = f"https://www.mdpi.com/{doi.replace('10.3390/', '')}/pdf?version=1"
            logger.info(f"  Trying alternate URL...")

            if download_pdf(alt_url, output_path, session):
                logger.info(f"  OK: {filename}")
                update_download_status(paper_id, 'downloaded', 'mdpi_direct', str(output_path))
                downloaded += 1
            else:
                logger.warning(f"  FAILED")
                update_download_status(paper_id, 'failed', 'mdpi_direct', 'Could not download PDF')
                failed += 1

        # Small delay to be nice to servers
        time.sleep(1)

        # Progress update every 10 papers
        if i % 10 == 0:
            logger.info(f"\nProgress: {i}/{len(papers)} - {downloaded} OK, {already_exist} exist, {failed} failed")

    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Downloaded: {downloaded}")
    logger.info(f"Already existed: {already_exist}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total processed: {len(papers)}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
