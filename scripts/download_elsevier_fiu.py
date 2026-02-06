#!/usr/bin/env python3
"""
Download Elsevier papers via FIU Library Primo search.

Flow:
1. Search FIU Primo by DOI
2. Click "Download PDF" or "Available Online"
3. Follow redirects through authentication
4. Save PDF to Downloads folder

Usage:
    ./venv/bin/python scripts/download_elsevier_fiu.py
"""

import os
import sys
import re
import time
import sqlite3
import logging
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import urllib.parse

# Setup paths
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "database" / "download_tracker.db"
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
DOWNLOAD_DIR = Path.home() / "Downloads"
LOG_DIR = PROJECT_DIR / "logs"
CHROME_PROFILE = Path.home() / ".config" / "chrome-fiu-library"

# FIU Primo search URL
PRIMO_SEARCH_URL = "https://fiu-flvc.primo.exlibrisgroup.com/discovery/search"
PRIMO_VID = "01FALSC_FIU:FIU"

# Setup logging
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"elsevier_fiu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Setup Chrome with persistent profile and download settings."""
    CHROME_PROFILE.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Download preferences - auto-download PDFs
    prefs = {
        "download.default_directory": str(DOWNLOAD_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def check_existing_pdf(authors: str, year: int, title: str) -> Path | None:
    """Check if PDF already exists in library."""
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


def get_recent_pdf_in_downloads(before_time: float) -> Path | None:
    """Find a PDF downloaded after the given time."""
    time.sleep(3)  # Wait for download to complete

    for _ in range(10):  # Check for up to 10 seconds
        for pdf in DOWNLOAD_DIR.glob("*.pdf"):
            if pdf.stat().st_mtime > before_time:
                # Wait a bit more to ensure download is complete
                time.sleep(1)
                size1 = pdf.stat().st_size
                time.sleep(1)
                size2 = pdf.stat().st_size
                if size1 == size2 and size1 > 1000:  # File stopped growing and is non-trivial
                    return pdf
        time.sleep(1)

    return None


def search_and_download(driver, doi: str, title: str) -> bool:
    """Search Primo for DOI and attempt to download PDF."""

    try:
        # Build search URL with DOI
        search_query = urllib.parse.quote(doi)
        search_url = f"{PRIMO_SEARCH_URL}?query=any,contains,{search_query}&vid={PRIMO_VID}&lang=en"

        logger.info(f"  Searching Primo...")
        driver.get(search_url)
        time.sleep(4)

        # Wait for results to load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "prm-brief-result-container"))
            )
        except TimeoutException:
            # Check for no results
            if "no results" in driver.page_source.lower():
                logger.warning("  No results found")
                return False
            logger.warning("  Search results didn't load")
            return False

        time.sleep(2)  # Let dynamic content load

        # Record time before download attempt
        before_download = time.time()

        # FIRST: Look for LibKey links directly on search results page
        # LibKey provides direct PDF access
        libkey_link = None
        try:
            # Use JavaScript to find all links with libkey.io
            links = driver.execute_script("""
                var links = document.querySelectorAll('a[href*="libkey.io"]');
                var hrefs = [];
                links.forEach(function(link) {
                    hrefs.push(link.href);
                });
                return hrefs;
            """)
            if links:
                # Prefer full-text-file links
                for link in links:
                    if 'full-text-file' in link:
                        libkey_link = link
                        break
                if not libkey_link:
                    libkey_link = links[0]
        except Exception as e:
            logger.debug(f"  JS libkey search failed: {e}")

        if libkey_link:
            logger.info(f"  Found LibKey link: {libkey_link[:80]}...")
            driver.get(libkey_link)
            time.sleep(5)

            # LibKey should redirect to PDF or article page
            current_url = driver.current_url

            # If on ScienceDirect, look for PDF download
            if 'sciencedirect.com' in current_url:
                try:
                    pdf_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'pdf') or contains(text(), 'PDF')]"))
                    )
                    pdf_btn.click()
                    time.sleep(5)
                except:
                    pass

            # Check for downloaded file
            new_pdf = get_recent_pdf_in_downloads(before_download)
            if new_pdf:
                logger.info(f"  Downloaded: {new_pdf.name}")
                return True

            # Check if we're on PDF page
            if 'pdf' in driver.current_url.lower() or 'sciencedirectassets.com' in driver.current_url:
                logger.info(f"  On PDF page")
                return True

        # SECOND: Try clicking into result and finding PDF links
        try:
            # Find all links in the results area using JavaScript
            all_links = driver.execute_script("""
                var container = document.querySelector('prm-brief-result-container');
                if (!container) return [];
                var links = container.querySelectorAll('a');
                var result = [];
                links.forEach(function(link) {
                    result.push({href: link.href, text: link.innerText});
                });
                return result;
            """)

            # Look for PDF or full text links
            for link_info in all_links:
                href = link_info.get('href', '')
                text = link_info.get('text', '').lower()
                if 'pdf' in text or 'full text' in text or 'download' in text:
                    logger.info(f"  Found link: {text[:40]} -> {href[:60]}")
                    driver.get(href)
                    time.sleep(5)
                    break

        except Exception as e:
            logger.debug(f"  Link extraction failed: {e}")

        # Check for downloaded file
        new_pdf = get_recent_pdf_in_downloads(before_download)
        if new_pdf:
            logger.info(f"  Downloaded: {new_pdf.name}")
            return True

        # THIRD: Click on result title to go to full display
        try:
            result_title = driver.execute_script("""
                var title = document.querySelector('prm-brief-result-container a');
                if (title) { title.click(); return true; }
                return false;
            """)
            if result_title:
                time.sleep(3)

                # Look for LibKey or PDF on full display page
                links = driver.execute_script("""
                    var links = document.querySelectorAll('a[href*="libkey.io"], a[href*="pdf"], a[href*="full-text"]');
                    var hrefs = [];
                    links.forEach(function(link) { hrefs.push(link.href); });
                    return hrefs;
                """)

                for link in links:
                    if 'libkey.io' in link or 'pdf' in link.lower():
                        logger.info(f"  Following: {link[:80]}")
                        driver.get(link)
                        time.sleep(5)
                        break

        except Exception as e:
            logger.debug(f"  Full display navigation failed: {e}")

        # Final check for downloaded file
        new_pdf = get_recent_pdf_in_downloads(before_download)
        if new_pdf:
            logger.info(f"  Downloaded: {new_pdf.name}")
            return True

        # Check if we ended up on a PDF viewer page
        current_url = driver.current_url
        if 'sciencedirectassets.com' in current_url or 'pdf' in current_url.lower():
            logger.info(f"  PDF page loaded - may need manual save")
            return True

        logger.warning("  Could not download PDF")
        return False

    except Exception as e:
        logger.error(f"  Error: {e}")
        return False


def move_and_rename_pdf(pdf_path: Path, authors: str, year: int, title: str) -> Path:
    """Move PDF to library with proper name."""
    first_author = get_first_author(authors)
    clean_t = clean_title(title)
    new_filename = f"{first_author}.etal.{int(year)}.{clean_t}.pdf"

    year_folder = OUTPUT_DIR / str(int(year))
    year_folder.mkdir(exist_ok=True)
    dest_path = year_folder / new_filename

    shutil.move(str(pdf_path), str(dest_path))
    return dest_path


def main():
    parser = argparse.ArgumentParser(description='Download Elsevier papers via FIU Library')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of papers (0=all)')
    parser.add_argument('--start', type=int, default=0, help='Start from paper N')
    parser.add_argument('--pause', type=int, default=3, help='Pause between papers (seconds)')
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Elsevier FIU Library Downloader")
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
        # Go to FIU library first for login
        logger.info("Navigating to FIU Library...")
        driver.get("https://library.fiu.edu")

        input("\n>>> Please log in to FIU Library if needed, then press Enter to continue... <<<\n")

        # Stats
        downloaded = 0
        existed = 0
        failed = 0

        for i, (paper_id, doi, authors, year, title) in enumerate(papers, 1):
            logger.info(f"\n[{i}/{len(papers)}] {doi}")
            logger.info(f"  Title: {title[:60]}..." if title and len(title) > 60 else f"  Title: {title}")

            # Check if already exists
            existing = check_existing_pdf(authors, year, title)
            if existing:
                logger.info(f"  EXISTS: {existing.name}")
                update_status(paper_id, 'downloaded', 'existing', str(existing))
                existed += 1
                continue

            # Record PDFs before download
            before_time = time.time()

            # Search and download
            success = search_and_download(driver, doi, title)

            if success:
                # Check for new PDF in downloads
                new_pdf = get_recent_pdf_in_downloads(before_time)
                if new_pdf:
                    # Move and rename
                    dest = move_and_rename_pdf(new_pdf, authors, year, title)
                    logger.info(f"  Saved: {dest.name}")
                    update_status(paper_id, 'downloaded', 'fiu_library', str(dest))
                    downloaded += 1
                else:
                    logger.info(f"  PDF may need manual save from browser")
                    downloaded += 1  # Count as success
                    update_status(paper_id, 'downloaded', 'fiu_library', 'browser')
            else:
                update_status(paper_id, 'failed', 'fiu_library', 'Could not find/download')
                failed += 1

            # Progress update
            if i % 10 == 0:
                logger.info(f"\n--- Progress: {i}/{len(papers)} - {downloaded} OK, {existed} exist, {failed} failed ---")

            time.sleep(args.pause)

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Downloaded: {downloaded}")
        logger.info(f"Already existed: {existed}")
        logger.info(f"Failed: {failed}")
        logger.info("=" * 70)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    finally:
        input("\n>>> Press Enter to close browser... <<<\n")
        driver.quit()


if __name__ == "__main__":
    main()
