#!/usr/bin/env python3
"""
Download MDPI papers using undetected-chromedriver to bypass Cloudflare.
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
import undetected_chromedriver as uc
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

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"mdpi_undetected_{timestamp}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def clean_title(title: str) -> str:
    """Clean title for filename."""
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
    """Generate standard filename for paper."""
    clean_author = re.sub(r'[^a-zA-Z\-]', '', first_author.split(',')[0])
    clean_t = clean_title(title)
    return f"{clean_author}.etal.{int(year)}.{clean_t}.pdf"


def get_first_author(authors: str) -> str:
    """Extract first author from authors string."""
    if not authors:
        return "Unknown"
    first = authors.split(';')[0].split(',')[0].strip()
    parts = first.split()
    if parts:
        return parts[-1] if len(parts) > 1 else parts[0]
    return "Unknown"


def get_pending_mdpi_papers(db_path: Path):
    """Get MDPI papers that haven't been downloaded yet."""
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


def mark_downloaded(db_path: Path, paper_id: int, filename: str, source: str = "mdpi_undetected"):
    """Mark a paper as downloaded in the database."""
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
    """Mark a paper download as failed."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, attempts FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()
    if existing:
        attempts = (existing[1] or 0) + 1
        cur.execute("""
            UPDATE download_status
            SET status = 'failed', source = 'mdpi_undetected',
                last_attempt = datetime('now'), notes = ?, attempts = ?
            WHERE paper_id = ?
        """, (error[:500], attempts, paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, last_attempt, notes, attempts)
            VALUES (?, 'failed', 'mdpi_undetected', datetime('now'), ?, 1)
        """, (paper_id, error[:500]))
    conn.commit()
    conn.close()


def setup_driver(headless: bool = False):
    """Setup undetected Chrome WebDriver."""
    options = uc.ChromeOptions()

    if headless:
        options.add_argument('--headless=new')

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    # Create driver with undetected-chromedriver
    driver = uc.Chrome(options=options, use_subprocess=True)

    return driver


def download_pdf_via_browser(driver, doi: str, dest_path: Path, timeout: int = 45) -> bool:
    """
    Download an MDPI PDF by navigating to the article page and downloading the PDF.
    """
    article_url = f"https://doi.org/{doi}"

    try:
        # Navigate to article page via DOI redirect
        driver.get(article_url)
        time.sleep(4)  # Wait for redirect and any Cloudflare challenge

        # Wait for page to load
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Give time for any JavaScript challenges to complete
        time.sleep(3)

        # Get the final URL after redirect
        current_url = driver.current_url

        # Construct PDF URL from article URL
        # MDPI article URLs look like: https://www.mdpi.com/2076-2615/10/2/284
        # PDF URL is: https://www.mdpi.com/2076-2615/10/2/284/pdf
        if 'mdpi.com' in current_url:
            base_url = current_url.split('?')[0].rstrip('/')
            pdf_url = f"{base_url}/pdf"
        else:
            logger.warning(f"  Not redirected to MDPI: {current_url}")
            return False

        # Navigate to PDF URL directly
        driver.get(pdf_url)
        time.sleep(5)  # Wait for PDF page to load

        # Get cookies and download via requests
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        headers = {
            'User-Agent': driver.execute_script("return navigator.userAgent"),
            'Referer': current_url,
            'Accept': 'application/pdf,*/*'
        }

        response = session.get(pdf_url, headers=headers, timeout=120, stream=True)

        if response.status_code == 200:
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk

            if len(content) > 10000 and content[:4] == b'%PDF':
                with open(dest_path, 'wb') as f:
                    f.write(content)
                return True
            else:
                logger.warning(f"  Not a PDF (size: {len(content)}, starts: {content[:20] if content else 'empty'})")
        else:
            logger.warning(f"  HTTP {response.status_code}")

        return False

    except TimeoutException:
        logger.error(f"  Timeout loading page")
        return False
    except Exception as e:
        logger.error(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download MDPI papers via undetected-chromedriver")
    parser.add_argument('--test', type=int, default=0, help="Test mode: download only N papers")
    parser.add_argument('--headless', action='store_true', help="Run browser in headless mode")
    parser.add_argument('--delay', type=float, default=8.0, help="Delay between downloads (seconds)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("MDPI UNDETECTED DOWNLOADER")
    logger.info("=" * 60)

    papers = get_pending_mdpi_papers(DB_PATH)
    logger.info(f"Found {len(papers)} pending MDPI papers")

    if args.test > 0:
        papers = papers[:args.test]
        logger.info(f"Test mode: downloading {args.test} papers")

    if not papers:
        logger.info("No papers to download")
        return

    logger.info("Starting undetected Chrome browser...")
    driver = setup_driver(headless=args.headless)

    stats = {'downloaded': 0, 'failed': 0, 'existed': 0}

    try:
        for i, (paper_id, doi, title, authors, year) in enumerate(papers, 1):
            first_author = get_first_author(authors)
            filename = get_paper_filename(first_author, year, title)
            year_folder = SHARK_PAPERS_BASE / str(int(year))
            year_folder.mkdir(exist_ok=True)
            dest_path = year_folder / filename

            logger.info(f"[{i}/{len(papers)}] {doi}")

            if dest_path.exists():
                logger.info(f"  EXISTS: {filename}")
                mark_downloaded(DB_PATH, paper_id, filename, "exists")
                stats['existed'] += 1
                continue

            # Try to download with retries
            max_retries = 2
            success = False
            for attempt in range(max_retries):
                success = download_pdf_via_browser(driver, doi, dest_path)
                if success and dest_path.exists():
                    break
                if attempt < max_retries - 1:
                    logger.info(f"  Retry {attempt + 2}/{max_retries}...")
                    time.sleep(3)

            if success and dest_path.exists():
                size_kb = dest_path.stat().st_size / 1024
                logger.info(f"  OK: {filename} ({size_kb:.0f}KB)")
                mark_downloaded(DB_PATH, paper_id, filename)
                stats['downloaded'] += 1
            else:
                logger.warning(f"  FAIL: {doi}")
                mark_failed(DB_PATH, paper_id, "Download failed")
                stats['failed'] += 1

            if i < len(papers):
                time.sleep(args.delay)

            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(papers)} - {stats['downloaded']} OK, {stats['failed']} fail")

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
