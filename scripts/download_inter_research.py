#!/usr/bin/env python3
"""
download_inter_research.py

Download papers from Inter-Research journals (DOIs starting with 10.3354/).
Supports: Marine Ecology Progress Series (MEPS), Endangered Species Research (ESR),
          Climate Research, and other Inter-Research publications.

Strategy:
1. Query CrossRef API to get the exact PDF URL for each paper
2. Use undetected_chromedriver to bypass bot protection
3. Download PDFs with browser session cookies

Usage:
    ./venv/bin/python scripts/download_inter_research.py
    ./venv/bin/python scripts/download_inter_research.py --test 5
    ./venv/bin/python scripts/download_inter_research.py --headless

Author: Claude
Date: 2026-01-06
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
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE = BASE_DIR / "database/download_tracker.db"
SHARKPAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = BASE_DIR / "logs"

# Rate limiting - be polite to the server
MIN_DELAY = 2.0  # Minimum seconds between requests
MAX_DELAY = 4.0  # Maximum seconds (adds jitter)
CROSSREF_DELAY = 0.5  # Delay between CrossRef API calls
PAGE_LOAD_TIMEOUT = 30  # Seconds to wait for page load
PDF_DOWNLOAD_TIMEOUT = 120  # Seconds for PDF download

# University proxy configuration (FIU OpenAthens)
PROXY_ENABLED = False  # Set via --proxy flag
PROXY_BASE = "www-int--res-com.eu1.proxy.openathens.net"
ORIGINAL_BASE = "www.int-res.com"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5.0


def to_proxy_url(url: str) -> str:
    """Convert Inter-Research URL to university proxy URL."""
    if PROXY_ENABLED and url:
        return url.replace(ORIGINAL_BASE, PROXY_BASE).replace("http://", "https://")
    return url

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# CrossRef API
CROSSREF_API = "https://api.crossref.org/works/{doi}"
CROSSREF_EMAIL = "research@example.com"  # Polite pool


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"inter_research_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Logging to: {log_file}")
    return logger


# ============================================================================
# FILENAME HELPERS
# ============================================================================

def clean_for_filename(text: str) -> str:
    """Clean text for use in filename."""
    if not text:
        return ""
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    # Remove special characters except alphanumeric, spaces, and hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    # Take first 8 words
    words = text.split()[:8]
    return " ".join(words)


def get_first_author(authors_str: Optional[str]) -> str:
    """Extract first author's surname from authors string."""
    if not authors_str:
        return "Unknown"

    # Handle various separator formats
    authors = str(authors_str)
    for sep in [";", " and ", "&"]:
        if sep in authors:
            first = authors.split(sep)[0].strip()
            break
    else:
        first = authors.strip()

    # Extract surname (typically last part or first part if comma-separated)
    if "," in first:
        # "Smith, John" format
        surname = first.split(",")[0].strip()
    else:
        # "John Smith" format - take last word as surname
        parts = first.split()
        surname = parts[-1] if parts else "Unknown"

    # Clean up
    surname = re.sub(r"[^\w-]", "", surname)
    return surname if surname else "Unknown"


def generate_filename(authors: Optional[str], title: Optional[str], year: Optional[int]) -> str:
    """Generate standardized filename for the paper."""
    author = get_first_author(authors)
    title_clean = clean_for_filename(title) if title else "Untitled"
    year_str = str(int(year)) if year else "unknown"

    # Determine if multiple authors
    authors_str = str(authors) if authors else ""
    has_multiple = any(sep in authors_str for sep in [",", ";", " and ", "&"])

    if has_multiple:
        return f"{author}.etal.{year_str}.{title_clean}.pdf"
    return f"{author}.{year_str}.{title_clean}.pdf"


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def get_pending_papers(doi_pattern: str = "10.3354/%") -> list:
    """Get papers matching DOI pattern that haven't been downloaded."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        WHERE p.doi LIKE ?
        AND p.id NOT IN (
            SELECT paper_id FROM download_status
            WHERE status = 'downloaded'
        )
        ORDER BY p.year DESC, p.id
    """, (doi_pattern,))
    papers = cur.fetchall()
    conn.close()
    return papers


def mark_status(
    paper_id: int,
    status: str,
    source: str,
    notes: str = ""
) -> None:
    """Update download status in database."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Check if status record exists
    cur.execute("SELECT id, attempts FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()

    if existing:
        attempts = (existing[1] or 0) + 1 if status in ("failed", "unavailable") else existing[1]
        cur.execute("""
            UPDATE download_status
            SET status = ?, source = ?, download_date = datetime('now'),
                notes = ?, attempts = ?, last_attempt = datetime('now')
            WHERE paper_id = ?
        """, (status, source, notes[:500], attempts, paper_id))
    else:
        attempts = 1 if status in ("failed", "unavailable") else 0
        cur.execute("""
            INSERT INTO download_status
            (paper_id, status, source, download_date, notes, attempts, last_attempt)
            VALUES (?, ?, ?, datetime('now'), ?, ?, datetime('now'))
        """, (paper_id, status, source, notes[:500], attempts))

    conn.commit()
    conn.close()


# ============================================================================
# CROSSREF API
# ============================================================================

def is_open_access_url(pdf_url: str) -> bool:
    """
    Check if a PDF URL indicates Open Access.

    Inter-Research Open Access patterns:
    - _oa/ in URL (e.g., meps_oa/)
    - /feature/ in URL (feature articles are often OA)
    """
    if not pdf_url:
        return False
    return "_oa/" in pdf_url or "/feature/" in pdf_url


def get_pdf_url_from_crossref(
    doi: str,
    logger: logging.Logger
) -> Tuple[Optional[str], bool]:
    """
    Query CrossRef API to get the PDF URL for a paper.

    Returns (pdf_url, is_open_access) tuple.
    """
    try:
        url = CROSSREF_API.format(doi=doi)
        headers = {
            "User-Agent": f"ResearchDownloader/1.0 (mailto:{CROSSREF_EMAIL})"
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            message = data.get("message", {})

            # Look for PDF links
            links = message.get("link", [])
            for link in links:
                if link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL")
                    if pdf_url:
                        is_oa = is_open_access_url(pdf_url)
                        logger.debug(f"  CrossRef PDF URL: {pdf_url} (OA: {is_oa})")
                        return pdf_url, is_oa

            # No PDF link found
            return None, False

        elif response.status_code == 404:
            logger.debug(f"  DOI not found in CrossRef: {doi}")
            return None, False
        else:
            logger.warning(f"  CrossRef API error: HTTP {response.status_code}")
            return None, False

    except requests.Timeout:
        logger.warning(f"  CrossRef API timeout for {doi}")
        return None, False
    except Exception as e:
        logger.warning(f"  CrossRef API error: {e}")
        return None, False


def construct_pdf_url(doi: str, year: Optional[int]) -> Optional[str]:
    """
    Construct a PDF URL from DOI pattern when CrossRef doesn't provide one.

    Inter-Research URL patterns:
    - MEPS: https://www.int-res.com/articles/meps{year}/{vol}/m{vol}p{start}.pdf
    - ESR: https://www.int-res.com/articles/esr{year}/{vol}/n{vol}p{start}.pdf
    """
    # Parse DOI to extract journal and article info
    # Example DOIs: 10.3354/meps14765, 10.3354/esr01234
    match = re.match(r"10\.3354/([a-z]+)(\d+)", doi)
    if not match:
        return None

    journal_code = match.group(1)  # e.g., 'meps', 'esr'
    article_num = match.group(2)  # e.g., '14765'

    # We can't reliably construct URLs without volume/page info
    # These are typically in the CrossRef response
    return None


# ============================================================================
# BROWSER AUTOMATION
# ============================================================================

def setup_driver(headless: bool = False, max_retries: int = 3, use_profile: bool = False) -> uc.Chrome:
    """Setup undetected Chrome WebDriver with retry logic.

    Args:
        headless: Run browser in headless mode
        max_retries: Number of retry attempts
        use_profile: Use existing Chrome profile (preserves university login cookies)
    """
    options = uc.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    # Use existing Chrome profile for university authentication
    if use_profile:
        chrome_profile = Path.home() / ".config/google-chrome"
        if chrome_profile.exists():
            options.add_argument(f"--user-data-dir={chrome_profile}")
            options.add_argument("--profile-directory=Default")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")

    last_error = None
    for attempt in range(max_retries):
        try:
            driver = uc.Chrome(options=options, use_subprocess=True)
            return driver
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry

    raise RuntimeError(f"Failed to start browser after {max_retries} attempts: {last_error}")


def download_pdf_with_browser(
    driver: uc.Chrome,
    pdf_url: str,
    dest_path: Path,
    logger: logging.Logger,
    timeout: int = PDF_DOWNLOAD_TIMEOUT
) -> Tuple[bool, str]:
    """
    Download PDF using browser to bypass bot protection.

    Returns (success, message).
    """
    try:
        # Navigate to PDF URL
        driver.get(pdf_url)
        time.sleep(3)  # Wait for bot check/redirect

        # Wait for page to load
        try:
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            return False, "Page load timeout"

        # Additional wait for any JavaScript challenges
        time.sleep(2)

        # Get cookies from browser session
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie["name"], cookie["value"])

        # Download with browser cookies
        headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent"),
            "Referer": pdf_url,
            "Accept": "application/pdf,*/*"
        }

        response = session.get(pdf_url, headers=headers, timeout=timeout, stream=True)

        if response.status_code == 200:
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk

            # Verify PDF content
            if len(content) > 10000 and content[:4] == b"%PDF":
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(content)
                return True, f"Downloaded {len(content) // 1024}KB"
            elif content[:4] == b"%PDF":
                return False, f"PDF too small ({len(content)} bytes)"
            elif b"<!DOCTYPE html>" in content[:100] or b"<html" in content[:100]:
                return False, "Bot check page received"
            else:
                return False, f"Not a PDF (size: {len(content)})"

        elif response.status_code == 401:
            return False, "401 Unauthorized - not open access"
        elif response.status_code == 403:
            return False, "403 Forbidden - access denied"
        elif response.status_code == 404:
            return False, "404 Not Found"
        else:
            return False, f"HTTP {response.status_code}"

    except requests.Timeout:
        return False, "Download timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, str(e)[:100]


def try_alternative_urls(
    driver: uc.Chrome,
    doi: str,
    dest_path: Path,
    logger: logging.Logger
) -> Tuple[bool, str]:
    """
    Try downloading from DOI redirect page if direct PDF URL fails.

    Returns (success, message).
    """
    try:
        # Navigate to DOI redirect
        doi_url = f"https://doi.org/{doi}"
        driver.get(doi_url)
        time.sleep(4)  # Wait for redirect

        # Wait for page load
        try:
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            return False, "DOI redirect timeout"

        time.sleep(2)

        # Look for PDF link on the page
        page_source = driver.page_source

        # Pattern 1: Direct PDF link in href
        pdf_patterns = [
            r'href="([^"]+\.pdf)"',
            r'href="([^"]+/pdf[^"]*)"',
            r"data-pdf-url=\"([^\"]+)\"",
        ]

        pdf_url = None
        for pattern in pdf_patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                # Filter for int-res.com URLs
                for match in matches:
                    if "int-res.com" in match and ".pdf" in match:
                        pdf_url = match if match.startswith("http") else f"https://www.int-res.com{match}"
                        break
            if pdf_url:
                break

        if pdf_url:
            pdf_url = to_proxy_url(pdf_url)
            logger.debug(f"  Found PDF link on page: {pdf_url}")
            return download_pdf_with_browser(driver, pdf_url, dest_path, logger)

        return False, "No PDF link found on article page"

    except Exception as e:
        return False, f"Alternative URL error: {str(e)[:50]}"


# ============================================================================
# MAIN DOWNLOAD LOGIC
# ============================================================================

def download_paper(
    driver: uc.Chrome,
    paper_id: int,
    doi: str,
    title: Optional[str],
    authors: Optional[str],
    year: Optional[int],
    logger: logging.Logger,
    oa_only: bool = False
) -> Tuple[bool, str]:
    """
    Download a single paper.

    Args:
        driver: Chrome WebDriver instance
        paper_id: Database paper ID
        doi: Paper DOI
        title: Paper title
        authors: Paper authors string
        year: Publication year
        logger: Logger instance
        oa_only: If True, skip papers that are not Open Access

    Returns (success, message).
    """
    import random

    # Generate filename and destination path
    filename = generate_filename(authors, title, year)
    year_dir = SHARKPAPERS / str(int(year)) if year else SHARKPAPERS / "unknown_year"
    dest_path = year_dir / filename

    # Check if already exists
    if dest_path.exists():
        mark_status(paper_id, "downloaded", "inter_research-exists")
        return True, f"Already exists: {filename}"

    # Step 1: Get PDF URL from CrossRef
    pdf_url, is_oa = get_pdf_url_from_crossref(doi, logger)
    time.sleep(CROSSREF_DELAY)

    # Skip non-OA papers if oa_only mode
    if oa_only and not is_oa:
        if pdf_url:
            mark_status(paper_id, "skipped", "inter_research", "Not Open Access")
            return False, "Skipped: Not Open Access (paywalled)"
        else:
            mark_status(paper_id, "skipped", "inter_research", "No PDF URL in CrossRef")
            return False, "Skipped: No PDF URL in CrossRef"

    # Step 2: Try to download from PDF URL
    if pdf_url:
        pdf_url = to_proxy_url(pdf_url)
        logger.debug(f"  Using URL: {pdf_url}")
        for attempt in range(MAX_RETRIES):
            success, msg = download_pdf_with_browser(driver, pdf_url, dest_path, logger)

            if success:
                source = "inter_research-oa" if is_oa else "inter_research"
                mark_status(paper_id, "downloaded", source, filename)
                return True, f"OK: {filename} - {msg}"

            if attempt < MAX_RETRIES - 1:
                logger.debug(f"  Retry {attempt + 2}/{MAX_RETRIES}: {msg}")
                time.sleep(RETRY_DELAY)

    # Step 3: Try alternative approach via DOI redirect
    if not dest_path.exists():
        logger.debug(f"  Trying DOI redirect approach...")
        success, msg = try_alternative_urls(driver, doi, dest_path, logger)

        if success:
            mark_status(paper_id, "downloaded", "inter_research-redirect", filename)
            return True, f"OK (via redirect): {filename} - {msg}"

    # Failed to download
    mark_status(paper_id, "unavailable", "inter_research", msg)
    return False, msg


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download Inter-Research journal papers (DOI: 10.3354/*)"
    )
    parser.add_argument(
        "--test",
        type=int,
        default=0,
        help="Test mode: download only N papers"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=MIN_DELAY,
        help=f"Base delay between downloads in seconds (default: {MIN_DELAY})"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Skip the first N papers"
    )
    parser.add_argument(
        "--oa-only",
        action="store_true",
        help="Only download Open Access papers (skip paywalled)"
    )
    parser.add_argument(
        "--use-profile",
        action="store_true",
        help="Use existing Chrome profile (preserves university login cookies) - Chrome must be closed first"
    )
    parser.add_argument(
        "--pause-for-login",
        action="store_true",
        help="Pause after starting browser to allow manual university login"
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Use FIU university proxy (www-int--res-com.eu1.proxy.openathens.net)"
    )
    args = parser.parse_args()

    # Set global proxy flag
    global PROXY_ENABLED
    PROXY_ENABLED = args.proxy

    # Setup logging
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("INTER-RESEARCH JOURNAL DOWNLOADER")
    logger.info("=" * 60)
    logger.info(f"Delay: {args.delay}-{args.delay + 2}s between downloads")
    logger.info(f"Headless mode: {args.headless}")
    logger.info(f"Open Access only: {args.oa_only}")
    logger.info(f"Using Chrome profile: {args.use_profile}")
    logger.info(f"Using FIU proxy: {args.proxy}")

    # Get pending papers
    papers = get_pending_papers("10.3354/%")
    logger.info(f"Found {len(papers)} pending Inter-Research papers")

    if args.start_from > 0:
        papers = papers[args.start_from:]
        logger.info(f"Starting from paper #{args.start_from + 1}")

    if args.test > 0:
        papers = papers[:args.test]
        logger.info(f"Test mode: downloading {len(papers)} papers")

    if not papers:
        logger.info("No papers to download!")
        return

    # Initialize browser
    logger.info("Starting Chrome browser...")
    driver = setup_driver(headless=args.headless, use_profile=args.use_profile)

    # Pause for manual login if requested
    if args.pause_for_login:
        logger.info("=" * 60)
        logger.info("PAUSE FOR LOGIN")
        logger.info("=" * 60)
        logger.info("Please log in to your university library in the browser window.")
        if args.proxy:
            login_url = "https://www-int--res-com.eu1.proxy.openathens.net/"
            logger.info(f"Navigate to: {login_url}")
            logger.info("(This will redirect through your university authentication)")
        else:
            login_url = "https://www.int-res.com/"
            logger.info(f"Navigate to: {login_url}")
        logger.info("Complete any authentication required.")
        driver.get(login_url)
        input("Press ENTER when you have logged in and are ready to continue...")
        logger.info("Continuing with downloads...")

    # Statistics
    stats = {
        "downloaded": 0,
        "existed": 0,
        "failed": 0,
        "skipped": 0,
    }

    start_time = time.time()

    try:
        for i, (paper_id, doi, title, authors, year) in enumerate(papers, 1):
            logger.info(f"[{i}/{len(papers)}] {doi}")

            try:
                success, msg = download_paper(
                    driver, paper_id, doi, title, authors, year, logger,
                    oa_only=args.oa_only
                )

                if success:
                    if "exists" in msg.lower():
                        stats["existed"] += 1
                    else:
                        stats["downloaded"] += 1
                    logger.info(f"  {msg}")
                elif "skipped" in msg.lower():
                    stats["skipped"] += 1
                    logger.info(f"  {msg}")
                else:
                    stats["failed"] += 1
                    logger.warning(f"  FAIL: {msg}")

            except Exception as e:
                stats["failed"] += 1
                logger.error(f"  ERROR: {e}")
                mark_status(paper_id, "failed", "inter_research", str(e)[:200])

            # Progress update every 20 papers
            if i % 20 == 0:
                elapsed = (time.time() - start_time) / 60
                logger.info(
                    f"Progress: {i}/{len(papers)} - "
                    f"{stats['downloaded']} OK, {stats['failed']} fail, "
                    f"{elapsed:.1f}min elapsed"
                )

            # Rate limiting with jitter
            if i < len(papers):
                import random
                delay = args.delay + random.uniform(0, 2.0)
                time.sleep(delay)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")

    finally:
        driver.quit()
        logger.info("Browser closed")

    # Summary
    elapsed = (time.time() - start_time) / 60
    logger.info("")
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Downloaded: {stats['downloaded']}")
    logger.info(f"  Already existed: {stats['existed']}")
    logger.info(f"  Skipped (not OA): {stats['skipped']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info(f"  Time elapsed: {elapsed:.1f} minutes")
    logger.info("")

    if papers:
        processed = stats["downloaded"] + stats["existed"] + stats["skipped"] + stats["failed"]
        success_rate = (stats["downloaded"] + stats["existed"]) / processed * 100 if processed else 0
        logger.info(f"  Success rate: {success_rate:.1f}%")


if __name__ == "__main__":
    main()
