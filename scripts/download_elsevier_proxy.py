#!/usr/bin/env python3
"""
Download Elsevier papers via FIU library proxy (OpenAthens).

Usage:
    ./venv/bin/python scripts/download_elsevier_proxy.py

The script will:
1. Open Chrome with a persistent profile
2. Navigate to FIU library login
3. Wait for you to authenticate
4. Then download each Elsevier paper via the proxy
"""

import os
import sys
import re
import time
import sqlite3
import logging
import argparse
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests

# Setup paths
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "database" / "download_tracker.db"
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = PROJECT_DIR / "logs"
CHROME_PROFILE = Path.home() / ".config" / "chrome-elsevier-proxy"

# Proxy configuration
PROXY_BASE = "www-sciencedirect-com.eu1.proxy.openathens.net"
FIU_LOGIN_URL = "https://login.openathens.net/saml/2/sso/fiu.edu"

# Setup logging
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"elsevier_proxy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def clean_title(title: str, max_len: int = 80) -> str:
    """Clean title for filename."""
    if not title:
        return "Untitled"
    cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    words = cleaned.split()
    result = []
    length = 0
    for word in words:
        if length + len(word) + 1 > max_len:
            break
        result.append(word)
        length += len(word) + 1
    return ' '.join(result) if result else "Untitled"


def get_first_author(authors: str) -> str:
    """Extract first author's last name."""
    if not authors:
        return "Unknown"
    first = authors.split(';')[0].split(',')[0].strip()
    parts = first.split()
    return parts[-1] if parts else "Unknown"


def get_elsevier_papers():
    """Get all Elsevier papers needing download."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.id, p.doi, p.authors, p.year, p.title
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.paper_id IS NULL
          AND p.doi LIKE '10.1016/%'
        ORDER BY p.year DESC
    ''')

    papers = cursor.fetchall()
    conn.close()
    return papers


def update_status(paper_id: int, status: str, source: str, notes: str = None):
    """Update download status in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM download_status WHERE paper_id = ?', (paper_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE download_status
            SET status = ?, source = ?, download_date = ?, notes = ?
            WHERE paper_id = ?
        ''', (status, source, datetime.now().isoformat(), notes, paper_id))
    else:
        cursor.execute('''
            INSERT INTO download_status (paper_id, status, source, download_date, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (paper_id, status, source, datetime.now().isoformat(), notes))

    conn.commit()
    conn.close()


def setup_browser():
    """Setup Chrome with persistent profile."""
    CHROME_PROFILE.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,900")

    # Set download preferences
    prefs = {
        "download.default_directory": str(Path.home() / "Downloads"),
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver


def doi_to_sciencedirect_url(doi: str, use_proxy: bool = True) -> str:
    """Convert DOI to ScienceDirect URL."""
    # Direct DOI URL that will redirect
    if use_proxy:
        return f"https://{PROXY_BASE}/science/article/pii/via-doi/{doi}"
    return f"https://doi.org/{doi}"


def check_existing_pdf(authors: str, year: int, title: str) -> Path | None:
    """Check if PDF already exists."""
    author_prefix = get_first_author(authors).lower()
    year_str = str(int(year)) if year else "unknown"
    year_folder = OUTPUT_DIR / year_str

    if year_folder.exists():
        title_words = clean_title(title)[:40].lower() if title else ""
        for pdf in year_folder.glob("*.pdf"):
            pdf_lower = pdf.stem.lower()
            if author_prefix in pdf_lower:
                if title_words and any(word in pdf_lower for word in title_words.split()[:3] if len(word) > 3):
                    return pdf
    return None


def download_via_browser(driver, paper_id: int, doi: str, authors: str, year: int, title: str) -> bool:
    """Download a single paper via browser."""

    # Check if already exists
    existing = check_existing_pdf(authors, year, title)
    if existing:
        logger.info(f"  EXISTS: {existing.name}")
        update_status(paper_id, 'downloaded', 'existing', str(existing))
        return True

    try:
        # Navigate to article via proxy
        url = f"https://{PROXY_BASE}/science/article/pii/S{doi.replace('10.1016/', '').replace('.', '').replace('/', '')}"

        # Actually, let's use the DOI resolver through proxy
        # First go to the DOI via proxy
        proxy_doi_url = f"https://doi-org.eu1.proxy.openathens.net/{doi}"

        logger.info(f"  Navigating to: {proxy_doi_url}")
        driver.get(proxy_doi_url)
        time.sleep(3)

        # Look for PDF download link
        pdf_selectors = [
            "//a[contains(@href, '/pdfft')]",
            "//a[contains(@href, 'pdf')]",
            "//a[contains(text(), 'Download PDF')]",
            "//a[contains(@class, 'pdf')]",
            "//button[contains(text(), 'PDF')]",
            "//a[contains(@aria-label, 'PDF')]",
        ]

        pdf_link = None
        for selector in pdf_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    href = elem.get_attribute('href') or ''
                    if 'pdf' in href.lower():
                        pdf_link = href
                        break
                if pdf_link:
                    break
            except:
                continue

        if pdf_link:
            logger.info(f"  Found PDF link: {pdf_link[:80]}...")
            driver.get(pdf_link)
            time.sleep(5)
            return True
        else:
            logger.warning(f"  No PDF link found")
            return False

    except Exception as e:
        logger.error(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Download Elsevier papers via FIU proxy')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of papers (0=all)')
    parser.add_argument('--start', type=int, default=0, help='Start from paper N')
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Elsevier Proxy Downloader")
    logger.info("=" * 70)

    papers = get_elsevier_papers()
    if args.start:
        papers = papers[args.start:]
    if args.limit:
        papers = papers[:args.limit]

    logger.info(f"Found {len(papers)} Elsevier papers to download")

    if not papers:
        return

    # Setup browser
    logger.info("Starting browser...")
    driver = setup_browser()

    try:
        # First, navigate to FIU library for authentication
        logger.info("Navigating to FIU library login...")
        driver.get("https://library.fiu.edu")

        input("\n>>> Please log in to FIU library, then press Enter to continue... <<<\n")

        # Now go to ScienceDirect via proxy to establish session
        logger.info("Establishing ScienceDirect proxy session...")
        driver.get(f"https://{PROXY_BASE}")
        time.sleep(3)

        input("\n>>> If prompted for university selection, complete it now. Press Enter when ready... <<<\n")

        # Download papers
        downloaded = 0
        failed = 0
        existed = 0

        for i, (paper_id, doi, authors, year, title) in enumerate(papers, 1):
            logger.info(f"\n[{i}/{len(papers)}] {doi}")
            logger.info(f"  Title: {title[:60]}..." if title and len(title) > 60 else f"  Title: {title}")

            # Check existing
            existing = check_existing_pdf(authors, year, title)
            if existing:
                logger.info(f"  EXISTS: {existing.name}")
                update_status(paper_id, 'downloaded', 'existing', str(existing))
                existed += 1
                continue

            # Try to download
            success = download_via_browser(driver, paper_id, doi, authors, year, title)

            if success:
                downloaded += 1
            else:
                failed += 1
                update_status(paper_id, 'failed', 'elsevier_proxy', 'Could not download')

            # Progress update
            if i % 10 == 0:
                logger.info(f"\nProgress: {i}/{len(papers)} - {downloaded} OK, {existed} exist, {failed} failed")

            time.sleep(2)

        logger.info("\n" + "=" * 70)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Downloaded: {downloaded}")
        logger.info(f"Already existed: {existed}")
        logger.info(f"Failed: {failed}")
        logger.info("=" * 70)

    finally:
        input("\n>>> Press Enter to close browser... <<<\n")
        driver.quit()


if __name__ == "__main__":
    main()
