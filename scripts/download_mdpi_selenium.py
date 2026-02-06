#!/usr/bin/env python3
"""
Download MDPI papers using Selenium browser automation.
MDPI has Cloudflare protection that blocks direct requests.
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
        logging.FileHandler(LOG_DIR / f"mdpi_selenium_{timestamp}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def clean_title(title: str) -> str:
    """Clean title for filename."""
    # Remove problematic characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Truncate to reasonable length
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
    # Authors might be comma-separated or semicolon-separated
    first = authors.split(';')[0].split(',')[0].strip()
    # Take last name (first word if "Last, First" format, or last word otherwise)
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


def mark_downloaded(db_path: Path, paper_id: int, filename: str, source: str = "mdpi_selenium"):
    """Mark a paper as downloaded in the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if record exists
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

    # Check if record exists
    cur.execute("SELECT id, attempts FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()

    if existing:
        attempts = (existing[1] or 0) + 1
        cur.execute("""
            UPDATE download_status
            SET status = 'failed', source = 'mdpi_selenium',
                last_attempt = datetime('now'), notes = ?, attempts = ?
            WHERE paper_id = ?
        """, (error[:500], attempts, paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, last_attempt, notes, attempts)
            VALUES (?, 'failed', 'mdpi_selenium', datetime('now'), ?, 1)
        """, (paper_id, error[:500]))

    conn.commit()
    conn.close()


def setup_driver(headless: bool = True, download_dir: str = None):
    """Setup Chrome WebDriver with appropriate options."""
    options = Options()

    if headless:
        options.add_argument('--headless=new')

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # Set download preferences
    if download_dir:
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,  # Don't open PDF in browser
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)

    # Disable automation detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def download_pdf_via_browser(driver, doi: str, dest_path: Path, timeout: int = 30) -> bool:
    """
    Download an MDPI PDF by navigating to the article page via DOI and finding the PDF link.
    """
    # Use DOI.org to redirect to MDPI article page
    article_url = f"https://doi.org/{doi}"

    try:
        # Navigate to article page via DOI redirect
        driver.get(article_url)
        time.sleep(3)  # Wait for redirect and Cloudflare check

        # Wait for page to load
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check for Cloudflare challenge
        if "challenge" in driver.page_source.lower() or "cf-browser-verification" in driver.page_source:
            logger.info("  Waiting for Cloudflare challenge...")
            time.sleep(5)

        # Get the final URL after redirect
        current_url = driver.current_url

        # Find PDF download link - MDPI has a PDF button
        pdf_link = None

        # Method 1: Look for PDF link in href (MDPI uses /pdf suffix)
        try:
            pdf_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/pdf')]")
            for elem in pdf_elements:
                href = elem.get_attribute('href')
                if href and 'mdpi.com' in href:
                    pdf_link = href
                    break
        except:
            pass

        # Method 2: Look for download button with PDF text
        if not pdf_link:
            try:
                download_btns = driver.find_elements(By.XPATH, "//a[contains(text(), 'PDF') or contains(@class, 'pdf')]")
                for btn in download_btns:
                    href = btn.get_attribute('href')
                    if href and ('pdf' in href.lower() or 'mdpi.com' in href):
                        pdf_link = href
                        break
            except:
                pass

        # Method 3: Construct PDF URL from article URL
        # MDPI article URLs look like: https://www.mdpi.com/2076-2615/10/2/284
        # PDF URL is: https://www.mdpi.com/2076-2615/10/2/284/pdf
        if not pdf_link and 'mdpi.com' in current_url:
            # Remove any query strings and add /pdf
            base_url = current_url.split('?')[0].rstrip('/')
            pdf_link = f"{base_url}/pdf"

        # Navigate directly to PDF URL through browser to bypass Cloudflare
        if pdf_link:
            driver.get(pdf_link)
            time.sleep(3)

            # Check for Cloudflare challenge on PDF page
            if "challenge" in driver.page_source.lower() or "cf-browser-verification" in driver.page_source:
                logger.info("  Waiting for Cloudflare challenge on PDF...")
                time.sleep(8)

            # Now try to download via requests with fresh cookies
            cookies = driver.get_cookies()
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])

            headers = {
                'User-Agent': driver.execute_script("return navigator.userAgent"),
                'Referer': current_url,
                'Accept': 'application/pdf,*/*'
            }

            # Use streaming to handle large files
            response = session.get(pdf_link, headers=headers, timeout=120, allow_redirects=True, stream=True)

            if response.status_code == 200:
                # Download in chunks
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content += chunk

                # Check if it's actually a PDF
                if len(content) > 10000 and content[:4] == b'%PDF':
                    with open(dest_path, 'wb') as f:
                        f.write(content)
                    return True
                else:
                    logger.warning(f"  Response is not a PDF or too small (size: {len(content)}, starts with: {content[:20] if content else 'empty'})")
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
    parser = argparse.ArgumentParser(description="Download PeerJ papers via Selenium")
    parser.add_argument('--test', type=int, default=0, help="Test mode: download only N papers")
    parser.add_argument('--visible', action='store_true', help="Run browser visibly (not headless)")
    parser.add_argument('--delay', type=float, default=5.0, help="Delay between downloads (seconds)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("MDPI SELENIUM DOWNLOADER")
    logger.info("=" * 60)

    # Get pending papers
    papers = get_pending_mdpi_papers(DB_PATH)
    logger.info(f"Found {len(papers)} pending MDPI papers")

    if args.test > 0:
        papers = papers[:args.test]
        logger.info(f"Test mode: downloading {args.test} papers")

    if not papers:
        logger.info("No papers to download")
        return

    # Setup browser
    logger.info("Starting Chrome browser...")
    driver = setup_driver(headless=not args.visible)

    stats = {'downloaded': 0, 'failed': 0, 'existed': 0}

    try:
        for i, (paper_id, doi, title, authors, year) in enumerate(papers, 1):
            first_author = get_first_author(authors)
            filename = get_paper_filename(first_author, year, title)
            year_folder = SHARK_PAPERS_BASE / str(int(year))
            year_folder.mkdir(exist_ok=True)
            dest_path = year_folder / filename

            logger.info(f"[{i}/{len(papers)}] {doi}")

            # Check if already exists
            if dest_path.exists():
                logger.info(f"  EXISTS: {filename}")
                mark_downloaded(DB_PATH, paper_id, filename, "exists")
                stats['existed'] += 1
                continue

            # Try to download with retries
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                success = download_pdf_via_browser(driver, doi, dest_path)
                if success and dest_path.exists():
                    break
                if attempt < max_retries - 1:
                    logger.info(f"  Retry {attempt + 2}/{max_retries}...")
                    time.sleep(2)

            if success and dest_path.exists():
                size_kb = dest_path.stat().st_size / 1024
                logger.info(f"  OK: {filename} ({size_kb:.0f}KB)")
                mark_downloaded(DB_PATH, paper_id, filename)
                stats['downloaded'] += 1
            else:
                logger.warning(f"  FAIL: {doi}")
                mark_failed(DB_PATH, paper_id, "Download failed")
                stats['failed'] += 1

            # Delay between requests
            if i < len(papers):
                time.sleep(args.delay)

            # Progress report every 10 papers
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(papers)} - {stats['downloaded']} OK, {stats['failed']} fail")

    finally:
        driver.quit()

    # Final report
    logger.info("")
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Downloaded: {stats['downloaded']}")
    logger.info(f"  Already existed: {stats['existed']}")
    logger.info(f"  Failed: {stats['failed']}")


if __name__ == "__main__":
    main()
