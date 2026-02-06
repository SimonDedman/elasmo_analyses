#!/usr/bin/env python3
"""
download_nature.py

Download papers from Nature Publishing Group (DOIs starting with 10.1038/).

Nature has several access pathways:
1. Open Access papers - directly downloadable
2. SharedIt links - free read access via special links
3. Unpaywall API - finds OA versions from repositories
4. PDF extraction from article pages

Usage:
    ./venv/bin/python scripts/download_nature.py
    ./venv/bin/python scripts/download_nature.py --test 5
    ./venv/bin/python scripts/download_nature.py --email your@email.com
    ./venv/bin/python scripts/download_nature.py --headless  # Use browser for Cloudflare

Author: Simon Dedman / Claude
Date: 2025-01-06
"""

import argparse
import sqlite3
import requests
import re
import time
import logging
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

# Try to import browser-based tools for Cloudflare bypass
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATABASE = PROJECT_ROOT / "database" / "download_tracker.db"
SHARKPAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = PROJECT_ROOT / "logs"

# Default email for Unpaywall API (required by their terms)
DEFAULT_EMAIL = "user@example.com"

# Rate limiting
DELAY_BETWEEN_REQUESTS = 2.0  # Be polite to Nature servers
UNPAYWALL_DELAY = 1.0  # Unpaywall allows 100k/day but be respectful
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

# User agent mimicking a real browser
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# University proxy configuration (FIU OpenAthens)
PROXY_ENABLED = False  # Set via --proxy flag
PROXY_BASE = "www-nature-com.eu1.proxy.openathens.net"
ORIGINAL_BASE = "www.nature.com"


def to_proxy_url(url: str) -> str:
    """Convert Nature URL to university proxy URL."""
    if PROXY_ENABLED and url:
        return url.replace(ORIGINAL_BASE, PROXY_BASE).replace("http://", "https://")
    return url


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Paper:
    """Paper metadata from database."""
    id: int
    doi: str
    title: str
    authors: str
    year: int


@dataclass
class DownloadResult:
    """Result of a download attempt."""
    success: bool
    source: str
    message: str
    filename: Optional[str] = None
    file_size: int = 0


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"nature_{timestamp}.log"

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


logger = setup_logging()


# ============================================================================
# FILENAME GENERATION
# ============================================================================

def clean_for_filename(text: str, max_length: int = 80) -> str:
    """
    Clean text for use in filename.

    Args:
        text: Input text (title)
        max_length: Maximum length for the cleaned text

    Returns:
        Cleaned string safe for filenames
    """
    if not text:
        return "Untitled"

    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)

    # Remove problematic characters
    text = re.sub(r'[<>:"/\\|?*\[\]{}()\'`~!@#$%^&+=;,.]', ' ', text)

    # Collapse whitespace
    text = " ".join(text.split())

    # Take first N words that fit within max_length
    words = text.split()
    result = []
    length = 0
    for word in words:
        if length + len(word) + 1 > max_length:
            break
        result.append(word)
        length += len(word) + 1

    return " ".join(result) if result else "Untitled"


def get_first_author(authors_str: str) -> str:
    """
    Extract first author surname from authors string.

    Handles various formats:
    - "Smith, J. & Jones, B."
    - "Smith, John; Jones, Bob"
    - "John Smith, Bob Jones"

    Args:
        authors_str: Full author string

    Returns:
        First author surname
    """
    if not authors_str:
        return "Unknown"

    # Split by common separators to get first author
    for sep in [" & ", "; ", ", ", " and "]:
        if sep in authors_str:
            first = authors_str.split(sep)[0].strip()
            break
    else:
        first = authors_str.strip()

    # Handle "Surname, FirstName" format
    if ", " in first:
        surname = first.split(",")[0].strip()
    else:
        # Handle "FirstName Surname" format - take last word
        parts = first.split()
        surname = parts[-1] if parts else "Unknown"

    # Clean up surname
    surname = re.sub(r"[^a-zA-Z\-]", "", surname)
    return surname if surname else "Unknown"


def has_multiple_authors(authors_str: str) -> bool:
    """Check if there are multiple authors."""
    if not authors_str:
        return False
    indicators = [";", " & ", " and ", ","]
    return any(ind in authors_str for ind in indicators)


def generate_filename(authors: str, title: str, year: int) -> str:
    """
    Generate PDF filename from paper metadata.

    Format: FirstAuthor.etal.YEAR.Title words.pdf
            or FirstAuthor.YEAR.Title words.pdf (single author)

    Args:
        authors: Authors string
        title: Paper title
        year: Publication year

    Returns:
        Filename string
    """
    first_author = get_first_author(authors)
    clean_title = clean_for_filename(title)

    if has_multiple_authors(authors):
        return f"{first_author}.etal.{int(year)}.{clean_title}.pdf"
    return f"{first_author}.{int(year)}.{clean_title}.pdf"


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def get_pending_nature_papers() -> list[Paper]:
    """
    Get Nature papers (DOI 10.1038/*) that haven't been downloaded.

    Returns:
        List of Paper objects
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        WHERE p.doi LIKE '10.1038/%'
          AND p.id NOT IN (
              SELECT paper_id FROM download_status
              WHERE status IN ('downloaded', 'exists')
          )
        ORDER BY p.year DESC
    """)
    rows = cur.fetchall()
    conn.close()

    papers = [
        Paper(id=row[0], doi=row[1], title=row[2], authors=row[3], year=row[4])
        for row in rows
    ]
    return papers


def mark_downloaded(
    paper_id: int,
    filename: str,
    source: str = "nature"
) -> None:
    """Mark a paper as downloaded in the database."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Check for existing record
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
    paper_id: int,
    source: str,
    notes: str
) -> None:
    """Mark a paper as unavailable (couldn't download)."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("SELECT id, attempts FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()

    if existing:
        attempts = (existing[1] or 0) + 1
        cur.execute("""
            UPDATE download_status
            SET status = 'unavailable', source = ?, last_attempt = datetime('now'),
                notes = ?, attempts = ?
            WHERE paper_id = ?
        """, (source, notes[:500], attempts, paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, last_attempt, notes, attempts)
            VALUES (?, 'unavailable', ?, datetime('now'), ?, 1)
        """, (paper_id, source, notes[:500]))

    conn.commit()
    conn.close()


# ============================================================================
# UNPAYWALL API
# ============================================================================

def query_unpaywall(doi: str, email: str) -> Dict[str, Any]:
    """
    Query Unpaywall API for open access PDF URL.

    Args:
        doi: Paper DOI
        email: Email for Unpaywall API (required)

    Returns:
        Dict with is_oa, pdf_url, oa_status, source
    """
    url = f"https://api.unpaywall.org/v2/{doi}"
    params = {"email": email}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                result = {
                    "is_oa": data.get("is_oa", False),
                    "oa_status": data.get("oa_status", "unknown"),
                    "pdf_url": None,
                    "source": None
                }

                if data.get("is_oa"):
                    best_oa = data.get("best_oa_location", {})
                    if best_oa:
                        # Prefer url_for_pdf, fall back to url
                        result["pdf_url"] = best_oa.get("url_for_pdf") or best_oa.get("url")
                        result["source"] = best_oa.get("host_type", "unknown")
                        result["version"] = best_oa.get("version", "unknown")

                return result

            elif response.status_code == 404:
                logger.debug(f"DOI not found in Unpaywall: {doi}")
                return {"is_oa": False, "oa_status": "not_found"}

            else:
                logger.warning(f"Unpaywall returned {response.status_code} for {doi}")
                time.sleep(2 ** attempt)
                continue

        except requests.exceptions.Timeout:
            logger.warning(f"Unpaywall timeout for {doi}, attempt {attempt + 1}")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Unpaywall error for {doi}: {e}")
            return {"is_oa": False, "oa_status": "error", "error": str(e)}

    return {"is_oa": False, "oa_status": "failed_after_retries"}


# ============================================================================
# NATURE-SPECIFIC PDF EXTRACTION
# ============================================================================

def get_nature_pdf_url_from_page(doi: str, session: requests.Session) -> Optional[str]:
    """
    Try to extract PDF URL from Nature article page.

    Nature article pages may have:
    - Direct PDF links for OA papers
    - SharedIt links for view access

    Args:
        doi: Paper DOI
        session: Requests session with cookies

    Returns:
        PDF URL if found, None otherwise
    """
    if not BS4_AVAILABLE:
        logger.debug("BeautifulSoup not available, skipping page scraping")
        return None

    article_url = f"https://doi.org/{doi}"

    try:
        response = session.get(
            article_url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        if response.status_code != 200:
            logger.debug(f"Article page returned {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Look for PDF download link
        # Nature uses various link patterns
        pdf_patterns = [
            # Direct PDF link
            {"href": re.compile(r"\.pdf$", re.I)},
            {"href": re.compile(r"/pdf/", re.I)},
            # Download link with PDF in text
            {"class": re.compile(r"pdf", re.I)},
            {"data-track-action": "download pdf"},
        ]

        for pattern in pdf_patterns:
            link = soup.find("a", pattern)
            if link and link.get("href"):
                href = link["href"]
                # Make absolute URL
                if href.startswith("/"):
                    parsed = urlparse(response.url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                elif not href.startswith("http"):
                    href = urljoin(response.url, href)
                return href

        # Look for meta tag with PDF URL
        meta_pdf = soup.find("meta", {"name": "citation_pdf_url"})
        if meta_pdf and meta_pdf.get("content"):
            return meta_pdf["content"]

        return None

    except Exception as e:
        logger.debug(f"Error parsing article page: {e}")
        return None


def construct_nature_pdf_url(doi: str) -> Optional[str]:
    """
    Construct likely PDF URL based on DOI pattern.

    Nature Scientific Reports: 10.1038/s41598-YYY-XXXXX-X
    Nature Communications: 10.1038/s41467-YYY-XXXXX-X
    Nature main: 10.1038/nature12345 or 10.1038/sXXXXX

    Args:
        doi: Paper DOI

    Returns:
        Constructed PDF URL or None
    """
    # Extract article identifier from DOI
    doi_suffix = doi.replace("10.1038/", "")

    # Different Nature journals have different URL patterns
    patterns = [
        # Scientific Reports, Nature Communications, etc.
        f"https://www.nature.com/articles/{doi_suffix}.pdf",
        # Alternative pattern
        f"https://www.nature.com/articles/{doi}.pdf",
    ]

    return to_proxy_url(patterns[0])  # Return first pattern, caller will verify


# ============================================================================
# PDF DOWNLOAD
# ============================================================================

def download_pdf(
    url: str,
    dest_path: Path,
    session: Optional[requests.Session] = None
) -> Tuple[bool, str]:
    """
    Download PDF from URL.

    Args:
        url: PDF URL
        dest_path: Destination file path
        session: Optional requests session with cookies

    Returns:
        Tuple of (success, message)
    """
    if session is None:
        session = requests.Session()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,*/*",
        "Accept-Language": "en-US,en;q=0.9",
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
                content_type = response.headers.get("Content-Type", "").lower()

                # Read content
                content = b""
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content += chunk

                # Verify it's a PDF
                if content[:4] != b"%PDF":
                    # Check if it's HTML (paywall or challenge)
                    if b"<!DOCTYPE" in content[:100] or b"<html" in content[:100]:
                        return False, "Got HTML instead of PDF (paywall/challenge)"
                    return False, f"Not a valid PDF (content-type: {content_type})"

                # Check minimum size (avoid empty/error PDFs)
                if len(content) < 5000:
                    return False, f"PDF too small ({len(content)} bytes)"

                # Save file
                with open(dest_path, "wb") as f:
                    f.write(content)

                return True, f"Downloaded {len(content):,} bytes"

            elif response.status_code == 403:
                return False, "Access forbidden (paywall)"
            elif response.status_code == 404:
                return False, "PDF not found (404)"
            elif response.status_code == 429:
                wait_time = 2 ** (attempt + 2)
                logger.warning(f"Rate limited, waiting {wait_time}s")
                time.sleep(wait_time)
                continue
            else:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return False, f"HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return False, "Request timeout"
        except requests.exceptions.ConnectionError as e:
            if "cloudflare" in str(e).lower():
                return False, "Cloudflare challenge detected"
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return False, f"Connection error: {str(e)[:50]}"
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"

    return False, f"Failed after {MAX_RETRIES} attempts"


# ============================================================================
# BROWSER-BASED DOWNLOAD (CLOUDFLARE BYPASS)
# ============================================================================

def download_via_browser(
    doi: str,
    dest_path: Path,
    driver: Any
) -> Tuple[bool, str]:
    """
    Download PDF using browser to bypass Cloudflare.

    Args:
        doi: Paper DOI
        dest_path: Destination file path
        driver: Selenium WebDriver instance

    Returns:
        Tuple of (success, message)
    """
    article_url = f"https://doi.org/{doi}"

    try:
        # Navigate to article page
        driver.get(article_url)
        time.sleep(4)

        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)

        current_url = driver.current_url

        # Check if we're on a Nature page
        if "nature.com" not in current_url:
            return False, f"Not redirected to Nature: {current_url[:50]}"

        # Try to find PDF link on page
        pdf_url = None

        # Look for PDF link
        try:
            pdf_link = driver.find_element(
                By.CSS_SELECTOR,
                'a[data-track-action="download pdf"], a[href*=".pdf"], a.c-pdf-download__link'
            )
            pdf_url = pdf_link.get_attribute("href")
        except Exception:
            pass

        if not pdf_url:
            # Construct PDF URL from article URL
            article_id = current_url.split("/articles/")[-1].split("?")[0].split("#")[0]
            pdf_url = f"https://www.nature.com/articles/{article_id}.pdf"

        # Navigate to PDF URL to get cookies
        driver.get(pdf_url)
        time.sleep(5)

        # Transfer cookies to requests session
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie["name"], cookie["value"])

        # Download with cookies
        headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent"),
            "Referer": current_url,
            "Accept": "application/pdf,*/*"
        }

        response = session.get(pdf_url, headers=headers, timeout=120, stream=True)

        if response.status_code == 200:
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk

            if len(content) > 5000 and content[:4] == b"%PDF":
                with open(dest_path, "wb") as f:
                    f.write(content)
                return True, f"Downloaded via browser {len(content):,} bytes"
            else:
                return False, f"Invalid PDF (size: {len(content)})"
        else:
            return False, f"HTTP {response.status_code}"

    except TimeoutException:
        return False, "Browser timeout"
    except Exception as e:
        return False, f"Browser error: {str(e)[:50]}"


def setup_browser(headless: bool = False) -> Any:
    """Setup undetected Chrome browser."""
    if not SELENIUM_AVAILABLE:
        return None

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver


# ============================================================================
# MAIN DOWNLOAD LOGIC
# ============================================================================

def download_paper(
    paper: Paper,
    email: str,
    session: requests.Session,
    driver: Optional[Any] = None
) -> DownloadResult:
    """
    Attempt to download a single paper using multiple strategies.

    Strategy order:
    1. Unpaywall API (legal OA sources)
    2. Direct Nature PDF URL
    3. Scrape article page for PDF link
    4. Browser-based download (Cloudflare bypass)

    Args:
        paper: Paper metadata
        email: Email for Unpaywall API
        session: Requests session
        driver: Optional browser driver for Cloudflare bypass

    Returns:
        DownloadResult with success status and details
    """
    # Create output directory
    year_dir = SHARKPAPERS / str(int(paper.year)) if paper.year else SHARKPAPERS / "unknown_year"
    year_dir.mkdir(parents=True, exist_ok=True)

    filename = generate_filename(paper.authors, paper.title, paper.year)
    dest_path = year_dir / filename

    # Check if already exists
    if dest_path.exists():
        file_size = dest_path.stat().st_size
        return DownloadResult(
            success=True,
            source="exists",
            message="Already downloaded",
            filename=filename,
            file_size=file_size
        )

    # Strategy 1: Unpaywall API
    logger.debug(f"Trying Unpaywall for {paper.doi}")
    unpaywall_result = query_unpaywall(paper.doi, email)
    time.sleep(UNPAYWALL_DELAY)

    if unpaywall_result.get("is_oa") and unpaywall_result.get("pdf_url"):
        pdf_url = unpaywall_result["pdf_url"]
        logger.debug(f"Unpaywall found OA URL: {pdf_url}")

        success, msg = download_pdf(pdf_url, dest_path, session)
        if success:
            return DownloadResult(
                success=True,
                source=f"unpaywall-{unpaywall_result.get('source', 'unknown')}",
                message=msg,
                filename=filename,
                file_size=dest_path.stat().st_size
            )
        logger.debug(f"Unpaywall download failed: {msg}")

    # Strategy 2: Construct direct Nature PDF URL
    logger.debug(f"Trying direct Nature URL for {paper.doi}")
    direct_url = construct_nature_pdf_url(paper.doi)
    if direct_url:
        time.sleep(DELAY_BETWEEN_REQUESTS)
        success, msg = download_pdf(direct_url, dest_path, session)
        if success:
            return DownloadResult(
                success=True,
                source="nature-direct",
                message=msg,
                filename=filename,
                file_size=dest_path.stat().st_size
            )
        logger.debug(f"Direct URL failed: {msg}")

    # Strategy 3: Scrape article page for PDF link
    logger.debug(f"Scraping article page for {paper.doi}")
    time.sleep(DELAY_BETWEEN_REQUESTS)
    page_pdf_url = get_nature_pdf_url_from_page(paper.doi, session)
    if page_pdf_url:
        success, msg = download_pdf(page_pdf_url, dest_path, session)
        if success:
            return DownloadResult(
                success=True,
                source="nature-page",
                message=msg,
                filename=filename,
                file_size=dest_path.stat().st_size
            )
        logger.debug(f"Page scrape download failed: {msg}")

    # Strategy 4: Browser-based download (Cloudflare bypass)
    if driver is not None:
        logger.debug(f"Trying browser download for {paper.doi}")
        time.sleep(DELAY_BETWEEN_REQUESTS)
        success, msg = download_via_browser(paper.doi, dest_path, driver)
        if success:
            return DownloadResult(
                success=True,
                source="nature-browser",
                message=msg,
                filename=filename,
                file_size=dest_path.stat().st_size
            )
        logger.debug(f"Browser download failed: {msg}")
        return DownloadResult(
            success=False,
            source="all-strategies-failed",
            message=f"Final: {msg}"
        )

    return DownloadResult(
        success=False,
        source="all-strategies-failed",
        message="All download strategies exhausted (no browser fallback)"
    )


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download papers from Nature Publishing Group (10.1038/*)"
    )
    parser.add_argument(
        "--test",
        type=int,
        default=0,
        help="Test mode: download only N papers"
    )
    parser.add_argument(
        "--email",
        type=str,
        default=DEFAULT_EMAIL,
        help="Email for Unpaywall API (required by their terms)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Disable browser-based Cloudflare bypass"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DELAY_BETWEEN_REQUESTS,
        help=f"Delay between requests in seconds (default: {DELAY_BETWEEN_REQUESTS})"
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Use university library proxy (FIU OpenAthens) for authenticated access"
    )
    parser.add_argument(
        "--pause-for-login",
        action="store_true",
        help="Pause after browser opens for manual library login (use with --proxy)"
    )
    args = parser.parse_args()

    # Set proxy if requested
    global PROXY_ENABLED
    if args.proxy:
        PROXY_ENABLED = True

    # Banner
    logger.info("=" * 70)
    logger.info("NATURE PUBLISHING GROUP DOWNLOADER")
    logger.info("=" * 70)
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Database: {DATABASE}")
    logger.info(f"Output: {SHARKPAPERS}")
    logger.info(f"Email: {args.email}")
    logger.info(f"Proxy: {'ENABLED (FIU OpenAthens)' if PROXY_ENABLED else 'disabled'}")
    logger.info("")

    # Check email
    if args.email == DEFAULT_EMAIL:
        logger.warning("Using default email for Unpaywall API.")
        logger.warning("Consider providing your email via --email for better service.")
        logger.warning("")

    # Check dependencies
    if not BS4_AVAILABLE:
        logger.warning("BeautifulSoup not installed - page scraping disabled")
        logger.warning("Install with: pip install beautifulsoup4")

    if not SELENIUM_AVAILABLE and not args.no_browser:
        logger.warning("undetected-chromedriver not installed - browser bypass disabled")
        logger.warning("Install with: pip install undetected-chromedriver selenium")

    # Get pending papers
    papers = get_pending_nature_papers()
    logger.info(f"Found {len(papers)} pending Nature papers (10.1038/*)")

    if args.test > 0:
        papers = papers[:args.test]
        logger.info(f"Test mode: processing {len(papers)} papers")

    if not papers:
        logger.info("No papers to download!")
        return

    # Setup browser if available and not disabled
    driver = None
    if SELENIUM_AVAILABLE and not args.no_browser:
        logger.info("Starting browser for Cloudflare bypass...")
        driver = setup_browser(headless=args.headless)
        logger.info("Browser ready")

    # Setup session
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Statistics
    stats = {
        "downloaded": 0,
        "existed": 0,
        "failed": 0,
        "sources": {}
    }

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"DOWNLOADING {len(papers)} PAPERS")
    logger.info("=" * 70)
    logger.info("")

    try:
        for i, paper in enumerate(papers, 1):
            logger.info(f"[{i}/{len(papers)}] {paper.doi}")
            logger.info(f"  Title: {paper.title[:60]}...")

            result = download_paper(paper, args.email, session, driver)

            if result.success:
                if result.source == "exists":
                    stats["existed"] += 1
                    logger.info(f"  EXISTS: {result.filename}")
                    mark_downloaded(paper.id, result.filename, "nature-exists")
                else:
                    stats["downloaded"] += 1
                    logger.info(f"  OK: {result.filename} ({result.file_size:,} bytes)")
                    logger.info(f"  Source: {result.source}")
                    mark_downloaded(paper.id, result.filename, result.source)

                # Track source statistics
                source_key = result.source.split("-")[0]
                stats["sources"][source_key] = stats["sources"].get(source_key, 0) + 1
            else:
                stats["failed"] += 1
                logger.warning(f"  FAIL: {result.message}")
                mark_unavailable(paper.id, result.source, result.message)

            # Progress update
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(papers)} - "
                           f"{stats['downloaded']} OK, {stats['existed']} exist, "
                           f"{stats['failed']} fail")

            # Rate limiting between papers
            if i < len(papers):
                time.sleep(args.delay)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    finally:
        if driver:
            logger.info("Closing browser...")
            driver.quit()

    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Total processed: {stats['downloaded'] + stats['existed'] + stats['failed']}")
    logger.info(f"  Downloaded: {stats['downloaded']}")
    logger.info(f"  Already existed: {stats['existed']}")
    logger.info(f"  Failed: {stats['failed']}")
    logger.info("")
    logger.info("Sources breakdown:")
    for source, count in sorted(stats["sources"].items(), key=lambda x: -x[1]):
        logger.info(f"  {source}: {count}")
    logger.info("")
    logger.info(f"PDFs saved to: {SHARKPAPERS}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
