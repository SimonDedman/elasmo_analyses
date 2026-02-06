#!/usr/bin/env python3
"""
download_jeb.py

Download papers from Journal of Experimental Biology / Company of Biologists
(DOIs starting with 10.1242/).

JEB hosts journals including:
- Journal of Experimental Biology (JEB)
- Disease Models & Mechanisms
- Development
- Journal of Cell Science
- Biology Open

This script:
1. Queries database for JEB papers (10.1242/%) not yet downloaded
2. Checks Unpaywall API for open access versions
3. Attempts direct PDF extraction from JEB pages
4. Uses Selenium for JavaScript-rendered content when needed
5. Supports university library proxy (FIU OpenAthens) for authenticated access

Usage:
    ./venv/bin/python scripts/download_jeb.py
    ./venv/bin/python scripts/download_jeb.py --test 5
    ./venv/bin/python scripts/download_jeb.py --proxy --pause-for-login

Author: Simon Dedman / Claude
Date: 2026-01-07
"""

import argparse
import logging
import re
import sqlite3
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import requests

# Try to import browser-based tools
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


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

# Unpaywall API configuration
UNPAYWALL_EMAIL = "simondedman@gmail.com"
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

# User agent for HTTP requests
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# JEB DOI prefix
JEB_DOI_PREFIX = "10.1242/%"

# University proxy configuration (FIU OpenAthens)
PROXY_ENABLED = False  # Set via --proxy flag
PROXY_BASE = "journals-biologists-com.eu1.proxy.openathens.net"
ORIGINAL_BASE = "journals.biologists.com"


def to_proxy_url(url: str) -> str:
    """Convert JEB URL to university proxy URL."""
    if PROXY_ENABLED and url:
        return url.replace(ORIGINAL_BASE, PROXY_BASE).replace("http://", "https://")
    return url


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging with file and console handlers."""
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"jeb_{timestamp}.log"

    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
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
    """Clean title for use in filename."""
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
    """Extract first author's last name from authors string."""
    if not authors:
        return "Unknown"

    # Split by various separators
    first = authors
    for sep in [';', ' and ', '&', ',']:
        if sep in first:
            first = first.split(sep)[0].strip()
            break

    # Handle "Last, First" format
    if ',' in first:
        first = first.split(',')[0].strip()

    # Get last name (last word if "First Last" format)
    parts = first.split()
    if parts:
        return parts[-1] if len(parts) > 1 else parts[0]
    return "Unknown"


def has_multiple_authors(authors: str) -> bool:
    """Check if there are multiple authors."""
    if not authors:
        return False
    indicators = [",", ";", " and ", "&"]
    return any(ind in str(authors) for ind in indicators)


def generate_filename(authors: str, title: str, year: int) -> str:
    """Generate standard filename for paper."""
    author = get_first_author(authors)
    author = re.sub(r'[^a-zA-Z\-]', '', author)
    clean_t = clean_title(title)

    if has_multiple_authors(authors):
        return f"{author}.etal.{int(year)}.{clean_t}.pdf"
    return f"{author}.{int(year)}.{clean_t}.pdf"


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_pending_jeb_papers(
    db_path: Path,
    retry_unavailable: bool = False
) -> list:
    """Get JEB papers that haven't been downloaded yet."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    if retry_unavailable:
        cur.execute("""
            SELECT p.id, p.doi, p.title, p.authors, p.year
            FROM papers p
            WHERE p.doi LIKE ?
            AND p.id NOT IN (
                SELECT paper_id FROM download_status WHERE status = 'downloaded'
            )
            ORDER BY p.year DESC
        """, (JEB_DOI_PREFIX,))
    else:
        cur.execute("""
            SELECT p.id, p.doi, p.title, p.authors, p.year
            FROM papers p
            WHERE p.doi LIKE ?
            AND p.id NOT IN (
                SELECT paper_id FROM download_status
                WHERE status IN ('downloaded', 'unavailable')
            )
            ORDER BY p.year DESC
        """, (JEB_DOI_PREFIX,))

    papers = cur.fetchall()
    conn.close()
    return papers


def mark_downloaded(
    db_path: Path,
    paper_id: int,
    filename: str,
    source: str = "jeb"
) -> None:
    """Mark a paper as successfully downloaded in the database."""
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


def mark_unavailable(
    db_path: Path,
    paper_id: int,
    reason: str,
    source: str = "jeb"
) -> None:
    """Mark a paper as unavailable (not open access)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE download_status
            SET status = 'unavailable', source = ?, last_attempt = datetime('now'), notes = ?
            WHERE paper_id = ?
        """, (source, reason[:500], paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, last_attempt, notes)
            VALUES (?, 'unavailable', ?, datetime('now'), ?)
        """, (paper_id, source, reason[:500]))

    conn.commit()
    conn.close()


def mark_failed(
    db_path: Path,
    paper_id: int,
    error: str,
    source: str = "jeb"
) -> None:
    """Mark a paper download as failed in the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

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


# ============================================================================
# UNPAYWALL API
# ============================================================================

def query_unpaywall(
    doi: str,
    logger: logging.Logger,
    email: str = UNPAYWALL_EMAIL
) -> dict:
    """Query Unpaywall API for open access PDF URL."""
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

def build_jeb_pdf_url(doi: str) -> str:
    """
    Construct PDF URL from JEB DOI.

    JEB URLs follow pattern:
    - Article: https://journals.biologists.com/jeb/article/226/1/jeb249715/...
    - PDF: https://journals.biologists.com/jeb/article-pdf/226/1/jeb249715/...

    DOI format: 10.1242/jeb.249715
    """
    # Extract journal and article ID from DOI
    # DOI: 10.1242/jeb.249715 -> journal=jeb, id=249715
    doi_suffix = doi.replace("10.1242/", "")

    # JEB PDF URL pattern
    base_url = f"https://journals.biologists.com/{doi_suffix.replace('.', '/article-pdf/')}"

    # Apply proxy if enabled
    return to_proxy_url(base_url)


def download_pdf_direct(
    url: str,
    logger: logging.Logger,
    session: Optional[requests.Session] = None
) -> Tuple[bool, Optional[bytes], str]:
    """Download PDF directly via HTTP request."""
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
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content += chunk

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

def setup_selenium_driver(headless: bool = True, use_profile: bool = False) -> 'uc.Chrome':
    """Setup undetected Chrome WebDriver."""
    if not SELENIUM_AVAILABLE:
        return None

    options = uc.ChromeOptions()

    if headless:
        options.add_argument('--headless=new')

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    if use_profile:
        options.add_argument('--user-data-dir=/home/simon/.config/google-chrome')
        options.add_argument('--profile-directory=Default')

    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver


def download_via_selenium(
    driver: 'uc.Chrome',
    doi: str,
    logger: logging.Logger
) -> Tuple[bool, Optional[bytes], str]:
    """Download PDF using Selenium browser automation."""
    # Navigate via DOI.org redirect
    article_url = f"https://doi.org/{doi}"

    try:
        driver.get(article_url)
        time.sleep(3)

        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        current_url = driver.current_url
        logger.debug(f"Redirected to: {current_url}")

        # Look for PDF link on JEB page
        pdf_url = None

        # Method 1: Look for PDF download link
        try:
            pdf_links = driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '.pdf') or contains(@href, '/pdf/') or contains(@href, 'article-pdf')]"
            )
            for link in pdf_links:
                href = link.get_attribute('href')
                if href and ('biologists.com' in href or 'pdf' in href.lower()):
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
                    "//a[contains(text(), 'PDF') or contains(@class, 'pdf')]"
                )
                for btn in pdf_buttons:
                    href = btn.get_attribute('href')
                    if href:
                        pdf_url = href
                        logger.debug(f"Found PDF button: {pdf_url}")
                        break
            except Exception:
                pass

        # Method 3: Construct URL from current page
        if not pdf_url and 'biologists.com' in current_url:
            try:
                # Try to convert article URL to PDF URL
                pdf_url = current_url.replace('/article/', '/article-pdf/')
                if not pdf_url.endswith('.pdf'):
                    pdf_url = pdf_url + '.pdf'
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
    driver: Optional['uc.Chrome'],
    logger: logging.Logger,
    stats: dict,
    unpaywall_email: str = UNPAYWALL_EMAIL
) -> bool:
    """Attempt to download a single paper."""
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

    # Method 2: Try direct JEB URL
    logger.debug("  Trying direct JEB URL...")
    direct_url = build_jeb_pdf_url(doi)
    success, content, msg = download_pdf_direct(direct_url, logger)

    if success and content:
        with open(dest_path, 'wb') as f:
            f.write(content)
        size_kb = len(content) / 1024
        logger.info(f"  OK (JEB direct): {filename} ({size_kb:.0f}KB)")
        mark_downloaded(DB_PATH, paper_id, filename, "jeb-direct")
        stats['downloaded'] += 1
        return True
    else:
        logger.debug(f"  Direct URL failed: {msg}")

    # Method 3: Try Selenium browser automation
    if driver:
        logger.debug("  Trying Selenium...")
        for attempt in range(MAX_RETRIES):
            success, content, msg = download_via_selenium(driver, doi, logger)

            if success and content:
                with open(dest_path, 'wb') as f:
                    f.write(content)
                size_kb = len(content) / 1024
                logger.info(f"  OK (Selenium): {filename} ({size_kb:.0f}KB)")
                mark_downloaded(DB_PATH, paper_id, filename, "jeb-selenium")
                stats['downloaded'] += 1
                return True
            elif attempt < MAX_RETRIES - 1:
                logger.debug(f"  Retry {attempt + 2}/{MAX_RETRIES}: {msg}")
                time.sleep(2)

        logger.warning(f"  FAIL: {msg}")

    # Mark as unavailable or failed
    if not unpaywall['is_oa']:
        logger.info(f"  UNAVAILABLE: Not open access ({unpaywall.get('oa_status', 'unknown')})")
        mark_unavailable(DB_PATH, paper_id, "Not open access", "jeb")
        stats['unavailable'] += 1
    else:
        logger.warning(f"  FAIL: OA but download failed")
        mark_failed(DB_PATH, paper_id, "OA but download failed", "jeb")
        stats['failed'] += 1

    return False


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Main entry point."""
    global PROXY_ENABLED

    parser = argparse.ArgumentParser(
        description="Download JEB / Company of Biologists papers (10.1242/)"
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
        help="Skip Selenium, use only Unpaywall and direct URLs"
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
    parser.add_argument(
        '--use-profile', action='store_true',
        help="Use existing Chrome profile (may have cookies from previous login)"
    )
    parser.add_argument(
        '--retry-unavailable', action='store_true',
        help="Retry papers previously marked as unavailable"
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help="Enable verbose/debug logging"
    )
    args = parser.parse_args()

    # Set proxy if requested
    if args.proxy:
        PROXY_ENABLED = True

    # Get email
    unpaywall_email = args.email if args.email else UNPAYWALL_EMAIL

    # Setup logging
    logger = setup_logging(verbose=args.verbose)

    logger.info("=" * 60)
    logger.info("JEB / COMPANY OF BIOLOGISTS DOWNLOADER")
    logger.info("=" * 60)
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Output: {SHARK_PAPERS_BASE}")
    logger.info(f"Unpaywall email: {unpaywall_email}")
    logger.info(f"Delay: {args.delay}s")
    logger.info(f"Selenium: {'disabled' if args.no_selenium else 'enabled'}")
    logger.info(f"Proxy: {'ENABLED (FIU OpenAthens)' if PROXY_ENABLED else 'disabled'}")

    # Get pending papers
    papers = get_pending_jeb_papers(DB_PATH, retry_unavailable=args.retry_unavailable)
    logger.info(f"Found {len(papers)} pending JEB papers (10.1242/*)")

    if args.test > 0:
        papers = papers[:args.test]
        logger.info(f"Test mode: downloading {args.test} papers")

    if not papers:
        logger.info("No papers to download")
        return

    # Setup Selenium driver if needed
    driver = None
    if not args.no_selenium and SELENIUM_AVAILABLE:
        logger.info("Starting Chrome browser...")
        try:
            driver = setup_selenium_driver(
                headless=not args.visible,
                use_profile=args.use_profile
            )

            if args.pause_for_login and PROXY_ENABLED:
                # Navigate to proxy login page
                login_url = "https://library.fiu.edu"
                logger.info(f"Opening {login_url} for authentication...")
                driver.get(login_url)
                input("\n>>> Please log in to FIU library, then press Enter to continue... <<<\n")
                logger.info("Continuing with proxy authentication...")

        except Exception as e:
            logger.warning(f"Failed to start Selenium: {e}")
            logger.warning("Continuing with Unpaywall only")

    elif not SELENIUM_AVAILABLE and not args.no_selenium:
        logger.warning("undetected-chromedriver not installed - browser bypass disabled")
        logger.warning("Install with: pip install undetected-chromedriver selenium")

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
