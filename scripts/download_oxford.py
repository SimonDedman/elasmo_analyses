#!/usr/bin/env python3
"""
download_oxford.py

Download papers from Oxford Academic (DOIs starting with 10.1093/).

Oxford Academic hosts various journals including ICES Journal of Marine Science,
Fisheries Research, and others. Many papers are open access or have free PDFs
available through publisher-hosted open access.

This script:
1. Queries the database for Oxford Academic papers (10.1093/%) not yet downloaded
2. Checks Unpaywall API for open access versions
3. Attempts direct PDF extraction from Oxford Academic pages
4. Uses Selenium for JavaScript-rendered content when needed

Author: Simon Dedman / Claude
Date: 2025-01-06
"""

import re
import time
import sqlite3
import logging
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "database" / "download_tracker.db"
SHARK_PAPERS_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = PROJECT_ROOT / "logs"

# Request configuration
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 3.0  # Seconds between downloads

# Unpaywall API configuration (email required for API access)
UNPAYWALL_EMAIL = "simondedman@gmail.com"  # Update with your email
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

# User agent for HTTP requests
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# University proxy configuration (FIU OpenAthens)
PROXY_ENABLED = False  # Set via --proxy flag
PROXY_BASE = "academic-oup-com.eu1.proxy.openathens.net"
ORIGINAL_BASE = "academic.oup.com"


def to_proxy_url(url: str) -> str:
    """Convert Oxford URL to university proxy URL."""
    if PROXY_ENABLED and url:
        return url.replace(ORIGINAL_BASE, PROXY_BASE).replace("http://", "https://")
    return url


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging with file and console handlers."""
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"oxford_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Log file: {log_file}")
    return logger


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clean_title(title: str) -> str:
    """
    Clean title for use in filename.

    Args:
        title: Raw title string

    Returns:
        Cleaned title suitable for filename (max 80 chars, safe characters only)
    """
    if not title:
        return "Untitled"

    # Normalize unicode and remove problematic characters
    cleaned = unicodedata.normalize('NFKD', title)
    cleaned = re.sub(r'[<>:"/\\|?*\[\]{}();,]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Truncate to reasonable length (first ~8 words or 80 chars)
    words = cleaned.split()
    result = []
    length = 0
    for word in words:
        if length + len(word) + 1 > 80:
            break
        result.append(word)
        length += len(word) + 1

    return ' '.join(result) if result else "Untitled"


def get_first_author(authors: str) -> str:
    """
    Extract first author's last name from authors string.

    Args:
        authors: Authors string (may be semicolon or comma separated)

    Returns:
        First author's last name
    """
    if not authors:
        return "Unknown"

    # Split by various separators
    first = authors
    for sep in [';', ' and ', '&']:
        if sep in first:
            first = first.split(sep)[0].strip()
            break

    # Handle "Last, First" format
    if ',' in first:
        first = first.split(',')[0].strip()

    # Get last name (last word if "First Last" format)
    parts = first.split()
    if parts:
        # Return last word as surname
        return parts[-1] if len(parts) > 1 else parts[0]
    return "Unknown"


def generate_filename(authors: str, title: str, year: int) -> str:
    """
    Generate standard filename for paper.

    Format: FirstAuthor.etal.YEAR.Title words.pdf

    Args:
        authors: Authors string
        title: Paper title
        year: Publication year

    Returns:
        Standardized filename
    """
    author = get_first_author(authors)
    # Clean author name for filename
    author = re.sub(r'[^a-zA-Z\-]', '', author)
    clean_t = clean_title(title)

    # Check if there are multiple authors (use .etal.)
    authors_str = str(authors) if authors else ''
    if any(sep in authors_str for sep in [',', ';', ' and ', '&']) and len(authors_str) > len(author) + 10:
        return f"{author}.etal.{int(year)}.{clean_t}.pdf"
    return f"{author}.{int(year)}.{clean_t}.pdf"


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_pending_oxford_papers(db_path: Path) -> list:
    """
    Get Oxford Academic papers that haven't been downloaded yet.

    Args:
        db_path: Path to SQLite database

    Returns:
        List of tuples: (id, doi, title, authors, year)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE p.doi LIKE '10.1093/%'
          AND (ds.status IS NULL OR ds.status NOT IN ('downloaded', 'exists'))
        ORDER BY p.year DESC
    """)

    papers = cur.fetchall()
    conn.close()
    return papers


def mark_downloaded(
    db_path: Path,
    paper_id: int,
    filename: str,
    source: str = "oxford_academic"
) -> None:
    """
    Mark a paper as successfully downloaded in the database.

    Args:
        db_path: Path to SQLite database
        paper_id: Paper ID from papers table
        filename: Saved filename
        source: Download source identifier
    """
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


def mark_failed(
    db_path: Path,
    paper_id: int,
    error: str,
    source: str = "oxford_academic"
) -> None:
    """
    Mark a paper download as failed in the database.

    Args:
        db_path: Path to SQLite database
        paper_id: Paper ID from papers table
        error: Error message
        source: Download source identifier
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if record exists
    cur.execute("SELECT id, attempts FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()

    if existing:
        attempts = (existing[1] or 0) + 1
        cur.execute("""
            UPDATE download_status
            SET status = 'failed', source = ?,
                last_attempt = datetime('now'), notes = ?, attempts = ?
            WHERE paper_id = ?
        """, (source, error[:500], attempts, paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, last_attempt, notes, attempts)
            VALUES (?, 'failed', ?, datetime('now'), ?, 1)
        """, (paper_id, source, error[:500]))

    conn.commit()
    conn.close()


def mark_unavailable(
    db_path: Path,
    paper_id: int,
    reason: str,
    source: str = "oxford_academic"
) -> None:
    """
    Mark a paper as unavailable (not open access).

    Args:
        db_path: Path to SQLite database
        paper_id: Paper ID from papers table
        reason: Reason for unavailability
        source: Download source identifier
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if record exists
    cur.execute("SELECT id FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE download_status
            SET status = 'unavailable', source = ?,
                last_attempt = datetime('now'), notes = ?
            WHERE paper_id = ?
        """, (source, reason[:500], paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, last_attempt, notes)
            VALUES (?, 'unavailable', ?, datetime('now'), ?)
        """, (paper_id, source, reason[:500]))

    conn.commit()
    conn.close()


# ============================================================================
# UNPAYWALL API
# ============================================================================

def query_unpaywall(
    doi: str,
    logger: logging.Logger,
    email: str = UNPAYWALL_EMAIL
) -> dict:
    """
    Query Unpaywall API for open access PDF URL.

    Args:
        doi: DOI string
        logger: Logger instance
        email: Email for Unpaywall API

    Returns:
        Dict with keys: is_oa, pdf_url, oa_status, error
    """
    url = f"{UNPAYWALL_BASE_URL}/{doi}"
    params = {'email': email}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': USER_AGENT}
            )

            if response.status_code == 200:
                data = response.json()
                result = {
                    'is_oa': data.get('is_oa', False),
                    'oa_status': data.get('oa_status', 'unknown'),
                    'pdf_url': None,
                    'error': None
                }

                if data.get('is_oa'):
                    best_oa = data.get('best_oa_location', {})
                    result['pdf_url'] = best_oa.get('url_for_pdf') or best_oa.get('url')

                return result

            elif response.status_code == 404:
                return {
                    'is_oa': False,
                    'oa_status': 'not_found',
                    'pdf_url': None,
                    'error': 'DOI not found in Unpaywall'
                }
            else:
                logger.debug(f"Unpaywall HTTP {response.status_code} for {doi}")
                time.sleep(2 ** attempt)

        except requests.exceptions.Timeout:
            logger.debug(f"Unpaywall timeout (attempt {attempt + 1})")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.debug(f"Unpaywall error: {e}")
            return {
                'is_oa': False,
                'oa_status': 'error',
                'pdf_url': None,
                'error': str(e)
            }

    return {
        'is_oa': False,
        'oa_status': 'failed',
        'pdf_url': None,
        'error': 'Failed after retries'
    }


# ============================================================================
# PDF DOWNLOAD FUNCTIONS
# ============================================================================

def download_pdf_direct(
    url: str,
    logger: logging.Logger,
    session: Optional[requests.Session] = None
) -> Tuple[bool, Optional[bytes], str]:
    """
    Download PDF directly via HTTP request.

    Args:
        url: PDF URL
        logger: Logger instance
        session: Optional requests session (for using browser cookies)

    Returns:
        Tuple of (success, content, message)
    """
    if session is None:
        session = requests.Session()

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/pdf,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                stream=True
            )

            if response.status_code == 200:
                # Download in chunks
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content += chunk

                # Check if it's actually a PDF
                content_type = response.headers.get('Content-Type', '').lower()
                if 'pdf' in content_type or (len(content) > 1000 and content[:4] == b'%PDF'):
                    return True, content, "Success"
                else:
                    return False, None, f"Not PDF: {content_type[:50]}"

            elif response.status_code == 403:
                return False, None, "Access denied (403)"
            elif response.status_code == 404:
                return False, None, "Not found (404)"
            elif response.status_code == 429:
                logger.warning("Rate limited, waiting...")
                time.sleep(10 * (attempt + 1))
            else:
                logger.debug(f"HTTP {response.status_code}")
                time.sleep(2 ** attempt)

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout (attempt {attempt + 1})")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.debug(f"Download error: {e}")
            time.sleep(2 ** attempt)

    return False, None, "Failed after retries"


# ============================================================================
# SELENIUM BROWSER AUTOMATION
# ============================================================================

def setup_selenium_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Setup Chrome WebDriver with appropriate options.

    Args:
        headless: Run browser in headless mode

    Returns:
        Configured Chrome WebDriver
    """
    options = Options()

    if headless:
        options.add_argument('--headless=new')

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(f'--user-agent={USER_AGENT}')

    # Disable automation detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def download_via_selenium(
    driver: webdriver.Chrome,
    doi: str,
    logger: logging.Logger
) -> Tuple[bool, Optional[bytes], str]:
    """
    Download PDF using Selenium browser automation.

    Navigates to the Oxford Academic article page and extracts PDF URL.

    Args:
        driver: Selenium WebDriver
        doi: DOI string
        logger: Logger instance

    Returns:
        Tuple of (success, content, message)
    """
    # Navigate via DOI.org redirect
    article_url = f"https://doi.org/{doi}"

    try:
        driver.get(article_url)
        time.sleep(3)  # Wait for redirects

        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        current_url = driver.current_url
        logger.debug(f"Redirected to: {current_url}")

        # Look for PDF link on Oxford Academic page
        pdf_url = None

        # Method 1: Look for PDF download link
        try:
            pdf_links = driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '.pdf') or contains(@href, '/pdf/')]"
            )
            for link in pdf_links:
                href = link.get_attribute('href')
                if href and ('academic.oup.com' in href or 'oxford' in href.lower()):
                    pdf_url = href
                    logger.debug(f"Found PDF link: {pdf_url}")
                    break
        except Exception:
            pass

        # Method 2: Look for "PDF" text in links
        if not pdf_url:
            try:
                pdf_buttons = driver.find_elements(
                    By.XPATH,
                    "//a[contains(text(), 'PDF') or contains(@class, 'pdf') or contains(@aria-label, 'PDF')]"
                )
                for btn in pdf_buttons:
                    href = btn.get_attribute('href')
                    if href:
                        pdf_url = href
                        logger.debug(f"Found PDF button: {pdf_url}")
                        break
            except Exception:
                pass

        # Method 3: Look for full-text links
        if not pdf_url:
            try:
                full_text = driver.find_elements(
                    By.XPATH,
                    "//a[contains(text(), 'Full Text') or contains(@class, 'full-text')]"
                )
                for link in full_text:
                    href = link.get_attribute('href')
                    if href and 'pdf' in href.lower():
                        pdf_url = href
                        break
            except Exception:
                pass

        # Method 4: Construct URL for ICES Journal
        if not pdf_url and 'icesjms' in current_url:
            # ICES URLs: https://academic.oup.com/icesjms/article/82/1/fsaf001/...
            # PDF might be at: https://academic.oup.com/icesjms/article-pdf/...
            try:
                pdf_url = current_url.replace('/article/', '/article-pdf/') + '.pdf'
            except Exception:
                pass

        if not pdf_url:
            return False, None, "No PDF link found on page"

        # Apply proxy URL transformation if enabled
        pdf_url = to_proxy_url(pdf_url)

        # Navigate to PDF page to get any required cookies
        driver.get(pdf_url)
        time.sleep(2)

        # Get cookies and download via requests
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        # Download with session cookies
        success, content, msg = download_pdf_direct(pdf_url, logger, session)

        if success:
            return success, content, msg

        # If direct download failed, try with JavaScript extraction
        # Some sites embed PDF viewers
        try:
            # Check if we're on a PDF viewer page
            iframe = driver.find_elements(By.TAG_NAME, 'iframe')
            for frame in iframe:
                src = frame.get_attribute('src')
                if src and 'pdf' in src.lower():
                    success, content, msg = download_pdf_direct(src, logger, session)
                    if success:
                        return success, content, msg
        except Exception:
            pass

        return False, None, f"Failed to download from {pdf_url}"

    except TimeoutException:
        return False, None, "Page load timeout"
    except WebDriverException as e:
        return False, None, f"Browser error: {str(e)[:50]}"
    except Exception as e:
        return False, None, f"Error: {str(e)[:50]}"


# ============================================================================
# MAIN DOWNLOAD LOGIC
# ============================================================================

def download_paper(
    paper: tuple,
    driver: Optional[webdriver.Chrome],
    logger: logging.Logger,
    stats: dict,
    unpaywall_email: str = UNPAYWALL_EMAIL
) -> bool:
    """
    Attempt to download a single paper.

    Tries multiple methods:
    1. Unpaywall API for open access URL
    2. Direct download if URL found
    3. Selenium browser automation

    Args:
        paper: Tuple of (id, doi, title, authors, year)
        driver: Selenium WebDriver (optional)
        logger: Logger instance
        stats: Statistics dictionary
        unpaywall_email: Email for Unpaywall API

    Returns:
        True if download successful, False otherwise
    """
    paper_id, doi, title, authors, year = paper

    # Generate filename and output path
    filename = generate_filename(authors, title, year)
    year_folder = SHARK_PAPERS_BASE / str(int(year)) if year else SHARK_PAPERS_BASE / 'unknown_year'
    year_folder.mkdir(exist_ok=True)
    dest_path = year_folder / filename

    # Check if already exists
    if dest_path.exists():
        logger.info(f"  EXISTS: {filename}")
        mark_downloaded(DB_PATH, paper_id, filename, "exists")
        stats['existed'] += 1
        return True

    # Method 1: Try Unpaywall API
    logger.debug("  Checking Unpaywall...")
    unpaywall = query_unpaywall(doi, logger, unpaywall_email)

    if unpaywall['is_oa'] and unpaywall['pdf_url']:
        logger.info(f"  Unpaywall: OA via {unpaywall['oa_status']}")
        success, content, msg = download_pdf_direct(unpaywall['pdf_url'], logger)

        if success and content:
            with open(dest_path, 'wb') as f:
                f.write(content)
            size_kb = len(content) / 1024
            logger.info(f"  OK (Unpaywall): {filename} ({size_kb:.0f}KB)")
            mark_downloaded(DB_PATH, paper_id, filename, f"unpaywall-{unpaywall['oa_status']}")
            stats['downloaded'] += 1
            return True
        else:
            logger.debug(f"  Unpaywall download failed: {msg}")

    # Method 2: Try Selenium browser automation
    if driver:
        logger.debug("  Trying Selenium...")
        for attempt in range(MAX_RETRIES):
            success, content, msg = download_via_selenium(driver, doi, logger)

            if success and content:
                with open(dest_path, 'wb') as f:
                    f.write(content)
                size_kb = len(content) / 1024
                logger.info(f"  OK (Selenium): {filename} ({size_kb:.0f}KB)")
                mark_downloaded(DB_PATH, paper_id, filename, "oxford-selenium")
                stats['downloaded'] += 1
                return True
            elif attempt < MAX_RETRIES - 1:
                logger.debug(f"  Retry {attempt + 2}/{MAX_RETRIES}: {msg}")
                time.sleep(2)

        logger.warning(f"  FAIL: {msg}")

    # Mark as unavailable or failed
    if not unpaywall['is_oa']:
        logger.info(f"  UNAVAILABLE: Not open access ({unpaywall.get('oa_status', 'unknown')})")
        mark_unavailable(DB_PATH, paper_id, "Not open access", "oxford_academic")
        stats['unavailable'] += 1
    else:
        logger.warning(f"  FAIL: OA but download failed")
        mark_failed(DB_PATH, paper_id, "OA but download failed", "oxford_academic")
        stats['failed'] += 1

    return False


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Oxford Academic papers (10.1093/)"
    )
    parser.add_argument(
        '--test', type=int, default=0,
        help="Test mode: download only N papers"
    )
    parser.add_argument(
        '--visible', action='store_true',
        help="Run browser visibly (not headless)"
    )
    parser.add_argument(
        '--no-selenium', action='store_true',
        help="Skip Selenium, use only Unpaywall"
    )
    parser.add_argument(
        '--delay', type=float, default=DELAY_BETWEEN_REQUESTS,
        help=f"Delay between downloads (default: {DELAY_BETWEEN_REQUESTS}s)"
    )
    parser.add_argument(
        '--email', type=str, default=None,
        help=f"Email for Unpaywall API (default: {UNPAYWALL_EMAIL})"
    )
    parser.add_argument(
        '--proxy', action='store_true',
        help="Use university library proxy (FIU OpenAthens) for authenticated access"
    )
    parser.add_argument(
        '--pause-for-login', action='store_true',
        help="Pause after browser opens for manual library login (use with --proxy)"
    )
    args = parser.parse_args()

    # Set proxy if requested
    global PROXY_ENABLED
    if args.proxy:
        PROXY_ENABLED = True

    # Get email (use argument or default)
    unpaywall_email = args.email if args.email else UNPAYWALL_EMAIL

    # Setup logging
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("OXFORD ACADEMIC DOWNLOADER")
    logger.info("=" * 60)
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Output: {SHARK_PAPERS_BASE}")
    logger.info(f"Unpaywall email: {unpaywall_email}")
    logger.info(f"Delay: {args.delay}s")
    logger.info(f"Selenium: {'disabled' if args.no_selenium else 'enabled'}")
    logger.info(f"Proxy: {'ENABLED (FIU OpenAthens)' if PROXY_ENABLED else 'disabled'}")

    # Get pending papers
    papers = get_pending_oxford_papers(DB_PATH)
    logger.info(f"Found {len(papers)} pending Oxford Academic papers")

    if args.test > 0:
        papers = papers[:args.test]
        logger.info(f"Test mode: downloading {args.test} papers")

    if not papers:
        logger.info("No papers to download")
        return

    # Setup Selenium driver if needed
    driver = None
    if not args.no_selenium:
        logger.info("Starting Chrome browser...")
        try:
            driver = setup_selenium_driver(headless=not args.visible)
        except Exception as e:
            logger.warning(f"Failed to start Selenium: {e}")
            logger.warning("Continuing with Unpaywall only")

    # Statistics
    stats = {
        'downloaded': 0,
        'existed': 0,
        'failed': 0,
        'unavailable': 0
    }

    try:
        for i, paper in enumerate(papers, 1):
            paper_id, doi, title, authors, year = paper
            logger.info(f"[{i}/{len(papers)}] {doi}")

            download_paper(paper, driver, logger, stats, unpaywall_email)

            # Delay between requests
            if i < len(papers):
                time.sleep(args.delay)

            # Progress report every 20 papers
            if i % 20 == 0:
                logger.info(
                    f"Progress: {i}/{len(papers)} - "
                    f"{stats['downloaded']} OK, {stats['existed']} exist, "
                    f"{stats['failed']} fail, {stats['unavailable']} unavailable"
                )

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    finally:
        if driver:
            driver.quit()

    # Final report
    logger.info("")
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Downloaded:   {stats['downloaded']}")
    logger.info(f"  Already existed: {stats['existed']}")
    logger.info(f"  Unavailable (not OA): {stats['unavailable']}")
    logger.info(f"  Failed:       {stats['failed']}")
    total_processed = sum(stats.values())
    if total_processed > 0:
        success_rate = (stats['downloaded'] + stats['existed']) / total_processed * 100
        logger.info(f"  Success rate: {success_rate:.1f}%")


if __name__ == "__main__":
    main()
