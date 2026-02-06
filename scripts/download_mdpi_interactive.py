#!/usr/bin/env python3
"""
Interactive MDPI downloader - opens browser for you to click through Cloudflare.
Pauses at each paper for you to complete the challenge, then auto-downloads.
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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests

# Setup
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "download_tracker.db"
SHARK_PAPERS_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"mdpi_interactive_{timestamp}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def clean_title(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    words = cleaned.split()
    result = []
    length = 0
    for word in words:
        if length + len(word) + 1 > 80:
            break
        result.append(word)
        length += len(word) + 1
    return ' '.join(result) if result else "Untitled"


def get_paper_filename(first_author: str, year: int, title: str) -> str:
    clean_author = re.sub(r'[^a-zA-Z\-]', '', first_author.split(',')[0])
    clean_t = clean_title(title)
    return f"{clean_author}.etal.{int(year)}.{clean_t}.pdf"


def get_first_author(authors: str) -> str:
    if not authors:
        return "Unknown"
    first = authors.split(';')[0].split(',')[0].strip()
    parts = first.split()
    if parts:
        return parts[-1] if len(parts) > 1 else parts[0]
    return "Unknown"


def get_pending_mdpi_papers(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE p.doi LIKE '10.3390/%'
          AND (ds.status IS NULL OR ds.status NOT IN ('downloaded', 'exists'))
        ORDER BY p.year DESC
    """)
    papers = cur.fetchall()
    conn.close()
    return papers


def mark_downloaded(db_path: Path, paper_id: int, filename: str, source: str = "mdpi_interactive"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()
    if existing:
        cur.execute("""
            UPDATE download_status
            SET status = 'downloaded', source = ?, download_date = datetime('now'), notes = ?
            WHERE paper_id = ?
        """, (source, filename, paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, download_date, notes)
            VALUES (?, 'downloaded', ?, datetime('now'), ?)
        """, (paper_id, source, filename))
    conn.commit()
    conn.close()


def mark_failed(db_path: Path, paper_id: int, error: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, attempts FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()
    if existing:
        attempts = (existing[1] or 0) + 1
        cur.execute("""
            UPDATE download_status
            SET status = 'failed', source = 'mdpi_interactive',
                last_attempt = datetime('now'), notes = ?, attempts = ?
            WHERE paper_id = ?
        """, (error[:500], attempts, paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, last_attempt, notes, attempts)
            VALUES (?, 'failed', 'mdpi_interactive', datetime('now'), ?, 1)
        """, (paper_id, error[:500]))
    conn.commit()
    conn.close()


def setup_driver():
    """Setup visible Chrome browser for interactive use."""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1200,900')
    options.add_argument('--window-position=100,100')

    # Set download preferences
    prefs = {
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver


def wait_for_cloudflare(driver, timeout: int = 120):
    """Wait for user to complete Cloudflare challenge."""
    start = time.time()
    while time.time() - start < timeout:
        # Check if we're past Cloudflare
        if "challenge" not in driver.page_source.lower() and "cf-browser-verification" not in driver.page_source:
            # Check if we're on MDPI site
            if "mdpi.com" in driver.current_url:
                return True
        time.sleep(0.5)
    return False


def download_pdf(driver, doi: str, dest_path: Path) -> bool:
    """Navigate to article and download PDF."""
    try:
        # Navigate to article via DOI
        article_url = f"https://doi.org/{doi}"
        driver.get(article_url)
        time.sleep(2)

        # Check for Cloudflare and wait
        if "challenge" in driver.page_source.lower() or "cf-browser-verification" in driver.page_source:
            logger.info("  >>> CLOUDFLARE DETECTED - Please click to verify <<<")
            print("\n" + "="*60)
            print("CLOUDFLARE CHALLENGE - Please click the checkbox in browser")
            print("="*60 + "\n")

            if not wait_for_cloudflare(driver, timeout=120):
                logger.warning("  Cloudflare timeout - skipping")
                return False

            logger.info("  Cloudflare passed!")
            time.sleep(2)

        # Get the final URL
        current_url = driver.current_url

        # Construct PDF URL
        if 'mdpi.com' not in current_url:
            logger.warning(f"  Not on MDPI site: {current_url}")
            return False

        base_url = current_url.split('?')[0].rstrip('/')
        pdf_url = f"{base_url}/pdf"

        # Navigate to PDF page
        driver.get(pdf_url)
        time.sleep(2)

        # Check for Cloudflare on PDF page
        if "challenge" in driver.page_source.lower() or "cf-browser-verification" in driver.page_source:
            logger.info("  >>> CLOUDFLARE on PDF page - Please verify <<<")
            if not wait_for_cloudflare(driver, timeout=120):
                logger.warning("  Cloudflare timeout on PDF page")
                return False
            time.sleep(2)

        # Download via requests with browser cookies
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        headers = {
            'User-Agent': driver.execute_script("return navigator.userAgent"),
            'Referer': current_url,
            'Accept': 'application/pdf,*/*'
        }

        response = session.get(pdf_url, headers=headers, timeout=60, stream=True)

        if response.status_code == 200:
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk

            if len(content) > 10000 and content[:4] == b'%PDF':
                with open(dest_path, 'wb') as f:
                    f.write(content)
                return True

        logger.warning(f"  HTTP {response.status_code}")
        return False

    except Exception as e:
        logger.error(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Interactive MDPI downloader")
    parser.add_argument('--start', type=int, default=0, help="Start from paper N")
    parser.add_argument('--limit', type=int, default=0, help="Limit to N papers (0=all)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("MDPI INTERACTIVE DOWNLOADER")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This will open a visible browser window.")
    logger.info("When Cloudflare challenge appears, click the checkbox.")
    logger.info("The download will continue automatically after each verification.")
    logger.info("")

    papers = get_pending_mdpi_papers(DB_PATH)
    logger.info(f"Found {len(papers)} pending MDPI papers")

    if args.start > 0:
        papers = papers[args.start:]
        logger.info(f"Starting from paper {args.start}")

    if args.limit > 0:
        papers = papers[:args.limit]
        logger.info(f"Limited to {args.limit} papers")

    if not papers:
        logger.info("No papers to download")
        return

    input("Press ENTER to start browser...")

    driver = setup_driver()
    stats = {'downloaded': 0, 'failed': 0, 'existed': 0}

    try:
        for i, (paper_id, doi, title, authors, year) in enumerate(papers, 1):
            first_author = get_first_author(authors)
            filename = get_paper_filename(first_author, year, title)
            year_folder = SHARK_PAPERS_BASE / str(int(year))
            year_folder.mkdir(exist_ok=True)
            dest_path = year_folder / filename

            logger.info(f"[{i}/{len(papers)}] {doi}")
            logger.info(f"  Title: {title[:60]}...")

            if dest_path.exists():
                logger.info(f"  EXISTS: {filename}")
                mark_downloaded(DB_PATH, paper_id, filename, "exists")
                stats['existed'] += 1
                continue

            success = download_pdf(driver, doi, dest_path)

            if success and dest_path.exists():
                size_kb = dest_path.stat().st_size / 1024
                logger.info(f"  OK: {filename} ({size_kb:.0f}KB)")
                mark_downloaded(DB_PATH, paper_id, filename)
                stats['downloaded'] += 1
            else:
                logger.warning(f"  FAIL: {doi}")
                mark_failed(DB_PATH, paper_id, "Download failed")
                stats['failed'] += 1

            # Brief pause between papers
            time.sleep(1)

            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(papers)} - {stats['downloaded']} OK, {stats['failed']} fail")

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    finally:
        driver.quit()

    logger.info("")
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Downloaded: {stats['downloaded']}")
    logger.info(f"  Already existed: {stats['existed']}")
    logger.info(f"  Failed: {stats['failed']}")


if __name__ == "__main__":
    main()
