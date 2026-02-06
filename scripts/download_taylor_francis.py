#!/usr/bin/env python3
"""
download_taylor_francis.py

Download papers from Taylor & Francis (DOIs starting with 10.1080/).

Strategy:
1. Query database for T&F papers not yet downloaded
2. Check if paper is Open Access via DOI redirect to tandfonline.com
3. Use Unpaywall API as fallback for OA versions
4. Use Selenium for JavaScript-heavy pages when needed

Author: Simon Dedman / Claude
Date: 2025-01-06
"""

import argparse
import sqlite3
import requests
import re
import time
import unicodedata
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

# Selenium imports
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
DATABASE = PROJECT_ROOT / "database" / "download_tracker.db"
SHARKPAPERS_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = PROJECT_ROOT / "logs"

# API Configuration
UNPAYWALL_EMAIL = "simon.dedman@ucd.ie"  # Replace with your email
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

# Request settings
DELAY_BETWEEN_REQUESTS = 3.0  # Seconds between requests
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Taylor & Francis domains
TF_DOMAINS = ["tandfonline.com", "taylor", "routledge"]

# University proxy configuration (FIU OpenAthens)
PROXY_ENABLED = False  # Set via --proxy flag
PROXY_BASE = "www-tandfonline-com.eu1.proxy.openathens.net"
ORIGINAL_BASE = "www.tandfonline.com"


def to_proxy_url(url: str) -> str:
    """Convert Taylor & Francis URL to university proxy URL."""
    if PROXY_ENABLED and url:
        return url.replace(ORIGINAL_BASE, PROXY_BASE).replace("http://", "https://")
    return url


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging with timestamp-based log file."""
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"taylor_francis_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
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

def clean_for_filename(text: str) -> str:
    """Clean text for use in filename."""
    if not text:
        return ""
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    # Remove problematic characters
    text = re.sub(r'[<>:"/\\|?*\[\]{}]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Take first 8 words, max 80 chars
    words = text.split()[:8]
    result = ' '.join(words)
    return result[:80]


def get_first_author(authors_str: str) -> str:
    """Extract first author surname from authors string."""
    if not authors_str:
        return "Unknown"

    # Handle various separators
    authors_str = str(authors_str)
    for sep in [" & ", ";", ",", " and "]:
        if sep in authors_str:
            first_author = authors_str.split(sep)[0].strip()
            break
    else:
        first_author = authors_str.strip()

    # Extract surname (typically first part before comma or last word)
    first_author = first_author.strip("()")
    if "," in first_author:
        # Format: "Surname, FirstName"
        surname = first_author.split(",")[0].strip()
    else:
        # Format: "FirstName Surname" - take last word
        parts = first_author.split()
        surname = parts[-1] if parts else "Unknown"

    # Clean surname
    surname = re.sub(r'[^a-zA-Z\-]', '', surname)
    return surname if surname else "Unknown"


def generate_filename(authors: str, year: int, title: str) -> str:
    """Generate standardized filename: FirstAuthor.etal.YEAR.Title words.pdf"""
    first_author = get_first_author(authors)
    title_clean = clean_for_filename(title)

    # Check if multiple authors
    authors_str = str(authors) if authors else ""
    has_multiple = any(sep in authors_str for sep in [",", ";", " & ", " and "])

    if has_multiple:
        return f"{first_author}.etal.{int(year)}.{title_clean}.pdf"
    return f"{first_author}.{int(year)}.{title_clean}.pdf"


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_pending_papers(db_path: Path) -> list:
    """Get Taylor & Francis papers that haven't been downloaded."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE p.doi LIKE '10.1080/%'
          AND (ds.status IS NULL OR ds.status NOT IN ('downloaded', 'exists'))
        ORDER BY p.year DESC
    """)

    papers = cur.fetchall()
    conn.close()
    return papers


def mark_downloaded(
    db_path: Path,
    paper_id: int,
    source: str,
    notes: str = ""
) -> None:
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
        """, (source, notes, paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, download_date, notes)
            VALUES (?, 'downloaded', ?, datetime('now'), ?)
        """, (paper_id, source, notes))

    conn.commit()
    conn.close()


def mark_failed(
    db_path: Path,
    paper_id: int,
    source: str,
    error: str
) -> None:
    """Mark a paper download as failed."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id, attempts FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()

    if existing:
        attempts = (existing[1] or 0) + 1
        cur.execute("""
            UPDATE download_status
            SET status = 'failed', source = ?, last_attempt = datetime('now'),
                notes = ?, attempts = ?
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
    source: str,
    notes: str
) -> None:
    """Mark a paper as unavailable (paywalled, no OA version found)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE download_status
            SET status = 'unavailable', source = ?, last_attempt = datetime('now'), notes = ?
            WHERE paper_id = ?
        """, (source, notes, paper_id))
    else:
        cur.execute("""
            INSERT INTO download_status (paper_id, status, source, last_attempt, notes)
            VALUES (?, 'unavailable', ?, datetime('now'), ?)
        """, (paper_id, source, notes))

    conn.commit()
    conn.close()


# ============================================================================
# UNPAYWALL API
# ============================================================================

def query_unpaywall(doi: str, logger: logging.Logger) -> dict:
    """Query Unpaywall API for open access PDF URL."""
    url = f"{UNPAYWALL_BASE_URL}/{doi}"
    params = {"email": UNPAYWALL_EMAIL}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT}
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.debug(f"DOI not found in Unpaywall: {doi}")
                return {"is_oa": False, "oa_status": "not_found"}
            else:
                logger.warning(f"Unpaywall returned {response.status_code} for {doi}")
                time.sleep(2 ** attempt)

        except requests.exceptions.Timeout:
            logger.warning(f"Unpaywall timeout (attempt {attempt + 1})")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Unpaywall error: {e}")
            return {"is_oa": False, "oa_status": "error", "error": str(e)}

    return {"is_oa": False, "oa_status": "failed_after_retries"}


def get_unpaywall_pdf_url(doi: str, logger: logging.Logger) -> Optional[str]:
    """Get PDF URL from Unpaywall if available."""
    data = query_unpaywall(doi, logger)

    if data.get("is_oa"):
        best_oa = data.get("best_oa_location", {})
        # Prefer direct PDF URL
        pdf_url = best_oa.get("url_for_pdf")
        if pdf_url:
            return pdf_url
        # Fallback to landing page URL
        return best_oa.get("url")

    return None


# ============================================================================
# PDF DOWNLOAD FUNCTIONS
# ============================================================================

def download_pdf(
    url: str,
    headers: dict,
    timeout: int = REQUEST_TIMEOUT
) -> Tuple[bool, Optional[bytes], str]:
    """Download PDF from URL. Returns (success, content, message)."""
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
            stream=True
        )

        if response.status_code == 200:
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk

            # Verify it's a PDF
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" in content_type or (len(content) > 1000 and content[:4] == b"%PDF"):
                return True, content, "Success"
            else:
                return False, None, f"Not PDF: {content_type[:30]}"
        elif response.status_code == 403:
            return False, None, "403 Forbidden (paywalled)"
        elif response.status_code == 404:
            return False, None, "404 Not Found"
        elif response.status_code == 429:
            return False, None, "429 Rate Limited"
        else:
            return False, None, f"HTTP {response.status_code}"

    except requests.Timeout:
        return False, None, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, None, "Connection error"
    except Exception as e:
        return False, None, str(e)[:50]


def save_pdf(content: bytes, dest_path: Path, logger: logging.Logger) -> bool:
    """Save PDF content to file with validation."""
    try:
        # Verify content is valid PDF
        if len(content) < 1000:
            logger.warning(f"PDF too small: {len(content)} bytes")
            return False

        if content[:4] != b"%PDF":
            logger.warning("Content is not a valid PDF")
            return False

        # Ensure year directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "wb") as f:
            f.write(content)

        return True

    except Exception as e:
        logger.error(f"Error saving PDF: {e}")
        return False


# ============================================================================
# SELENIUM BROWSER AUTOMATION
# ============================================================================

def setup_driver(headless: bool = False) -> webdriver.Chrome:
    """Setup Chrome WebDriver with appropriate options."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={USER_AGENT}")

    # Disable automation detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def check_tf_open_access_selenium(
    driver: webdriver.Chrome,
    doi: str,
    logger: logging.Logger
) -> Optional[str]:
    """
    Use Selenium to check if T&F paper is Open Access and get PDF URL.
    Returns PDF URL if OA, None otherwise.
    """
    article_url = f"https://doi.org/{doi}"

    try:
        driver.get(article_url)
        time.sleep(3)  # Wait for redirect

        # Wait for page load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        current_url = driver.current_url
        logger.debug(f"Redirected to: {current_url}")

        # Check if it's a tandfonline page
        if "tandfonline.com" not in current_url:
            logger.debug(f"Not T&F domain: {current_url}")
            return None

        # Look for Open Access indicators
        page_source = driver.page_source.lower()

        # Check for OA badge/label
        oa_indicators = [
            "open access",
            "openaccess",
            "free access",
            "free-access",
            "unlocked",
        ]

        is_oa = any(indicator in page_source for indicator in oa_indicators)

        # Also check for OA icon elements
        try:
            oa_elements = driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'open') or contains(@class, 'access') or contains(@class, 'unlocked')]"
            )
            if oa_elements:
                is_oa = True
        except Exception:
            pass

        if not is_oa:
            logger.debug("No OA indicators found")
            return None

        logger.info("  Open Access detected on T&F")

        # Try to find PDF link
        pdf_url = None

        # Method 1: Look for PDF download link
        try:
            pdf_links = driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '.pdf') or contains(@href, '/pdf') or contains(text(), 'PDF')]"
            )
            for link in pdf_links:
                href = link.get_attribute("href")
                if href and ("pdf" in href.lower() or "epdf" in href.lower()):
                    pdf_url = href
                    break
        except Exception:
            pass

        # Method 2: Look for download button
        if not pdf_url:
            try:
                download_btns = driver.find_elements(
                    By.XPATH,
                    "//a[contains(@class, 'download') or contains(@title, 'PDF')]"
                )
                for btn in download_btns:
                    href = btn.get_attribute("href")
                    if href:
                        pdf_url = href
                        break
            except Exception:
                pass

        # Method 3: Construct PDF URL from article URL
        # T&F pattern: https://www.tandfonline.com/doi/full/10.1080/xxx
        # PDF pattern: https://www.tandfonline.com/doi/pdf/10.1080/xxx
        if not pdf_url and "tandfonline.com/doi" in current_url:
            pdf_url = current_url.replace("/doi/full/", "/doi/pdf/")
            pdf_url = pdf_url.replace("/doi/abs/", "/doi/pdf/")
            if "/doi/pdf/" not in pdf_url:
                # Construct from DOI
                pdf_url = f"https://www.tandfonline.com/doi/pdf/{doi}"

        return pdf_url

    except TimeoutException:
        logger.warning(f"Timeout loading T&F page for {doi}")
        return None
    except Exception as e:
        logger.error(f"Selenium error: {e}")
        return None


def download_via_selenium(
    driver: webdriver.Chrome,
    pdf_url: str,
    dest_path: Path,
    logger: logging.Logger
) -> bool:
    """Download PDF via Selenium browser session."""
    try:
        # Navigate to PDF URL
        driver.get(pdf_url)
        time.sleep(3)

        # Get cookies from browser session
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie["name"], cookie["value"])

        headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent"),
            "Referer": pdf_url,
            "Accept": "application/pdf,*/*"
        }

        # Download with session cookies
        response = session.get(
            pdf_url,
            headers=headers,
            timeout=120,
            allow_redirects=True,
            stream=True
        )

        if response.status_code == 200:
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk

            if len(content) > 5000 and content[:4] == b"%PDF":
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(content)
                return True
            else:
                logger.warning(f"Not a valid PDF (size: {len(content)})")
        else:
            logger.warning(f"HTTP {response.status_code}")

        return False

    except Exception as e:
        logger.error(f"Selenium download error: {e}")
        return False


# ============================================================================
# MAIN DOWNLOAD LOGIC
# ============================================================================

def download_paper(
    paper: tuple,
    driver: Optional[webdriver.Chrome],
    logger: logging.Logger,
    use_selenium: bool = True
) -> Tuple[str, str]:
    """
    Attempt to download a single paper.
    Returns (status, message) where status is 'downloaded', 'failed', 'unavailable', 'exists'.
    """
    paper_id, doi, title, authors, year = paper

    # Generate filename and path
    filename = generate_filename(authors, year, title)
    year_dir = SHARKPAPERS_BASE / str(int(year)) if year else SHARKPAPERS_BASE / "unknown_year"
    dest_path = year_dir / filename

    # Check if already exists
    if dest_path.exists():
        mark_downloaded(DATABASE, paper_id, "exists", filename)
        return "exists", f"Already exists: {filename}"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,*/*"
    }

    # Strategy 1: Check Unpaywall for OA version
    logger.debug("  Checking Unpaywall...")
    unpaywall_url = get_unpaywall_pdf_url(doi, logger)

    if unpaywall_url:
        logger.info(f"  Unpaywall OA URL found")
        success, content, msg = download_pdf(unpaywall_url, headers)

        if success and content:
            if save_pdf(content, dest_path, logger):
                mark_downloaded(DATABASE, paper_id, "unpaywall", filename)
                return "downloaded", f"Downloaded via Unpaywall: {filename}"

    # Strategy 2: Try direct T&F PDF URL
    tf_pdf_url = f"https://www.tandfonline.com/doi/pdf/{doi}"
    tf_pdf_url = to_proxy_url(tf_pdf_url)
    logger.debug(f"  Trying direct T&F URL: {tf_pdf_url}")

    success, content, msg = download_pdf(tf_pdf_url, headers)
    if success and content:
        if save_pdf(content, dest_path, logger):
            mark_downloaded(DATABASE, paper_id, "taylor_francis_direct", filename)
            return "downloaded", f"Downloaded directly from T&F: {filename}"

    # Strategy 3: Use Selenium to check for OA and bypass any JS
    if use_selenium and driver:
        logger.debug("  Checking T&F via Selenium...")
        pdf_url = check_tf_open_access_selenium(driver, doi, logger)

        if pdf_url:
            pdf_url = to_proxy_url(pdf_url)
            logger.info(f"  Found PDF URL via Selenium: {pdf_url}")
            if download_via_selenium(driver, pdf_url, dest_path, logger):
                mark_downloaded(DATABASE, paper_id, "taylor_francis_selenium", filename)
                return "downloaded", f"Downloaded via Selenium: {filename}"

    # No OA version found
    mark_unavailable(DATABASE, paper_id, "taylor_francis", "No OA version found")
    return "unavailable", "No open access version found"


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Download Taylor & Francis papers (DOI 10.1080/)"
    )
    parser.add_argument(
        "--test", type=int, default=0,
        help="Test mode: process only N papers"
    )
    parser.add_argument(
        "--visible", action="store_true",
        help="Run browser visibly (not headless)"
    )
    parser.add_argument(
        "--no-selenium", action="store_true",
        help="Disable Selenium browser automation"
    )
    parser.add_argument(
        "--delay", type=float, default=DELAY_BETWEEN_REQUESTS,
        help=f"Delay between requests in seconds (default: {DELAY_BETWEEN_REQUESTS})"
    )
    parser.add_argument(
        "--email", type=str, default=UNPAYWALL_EMAIL,
        help="Email for Unpaywall API"
    )
    parser.add_argument(
        "--proxy", action="store_true",
        help="Use FIU university proxy (www-tandfonline-com.eu1.proxy.openathens.net)"
    )
    parser.add_argument(
        "--pause-for-login", action="store_true",
        help="Pause after starting browser to allow manual university login"
    )
    args = parser.parse_args()

    # Set global proxy flag
    global PROXY_ENABLED
    PROXY_ENABLED = args.proxy

    # Setup logging
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("TAYLOR & FRANCIS DOWNLOADER")
    logger.info("=" * 60)
    logger.info(f"Database: {DATABASE}")
    logger.info(f"Output: {SHARKPAPERS_BASE}")
    logger.info(f"Unpaywall email: {args.email}")
    logger.info(f"Use Selenium: {not args.no_selenium}")
    logger.info(f"Delay: {args.delay}s")
    logger.info(f"Using FIU proxy: {args.proxy}")

    # Update email if provided via command line
    unpaywall_email = args.email

    # Get pending papers
    papers = get_pending_papers(DATABASE)
    logger.info(f"\nFound {len(papers)} pending Taylor & Francis papers")

    if args.test > 0:
        papers = papers[:args.test]
        logger.info(f"Test mode: processing {args.test} papers")

    if not papers:
        logger.info("No papers to download")
        return

    # Initialize Selenium if enabled
    driver = None
    if not args.no_selenium:
        logger.info("\nStarting Chrome browser...")
        try:
            driver = setup_driver(headless=not args.visible)
            logger.info("Browser started successfully")

            # Pause for manual login if requested
            if args.pause_for_login and driver:
                logger.info("=" * 60)
                logger.info("PAUSE FOR LOGIN")
                logger.info("=" * 60)
                logger.info("Please log in to your university library in the browser window.")
                if args.proxy:
                    login_url = f"https://{PROXY_BASE}/"
                    logger.info(f"Navigate to: {login_url}")
                    logger.info("(This will redirect through your university authentication)")
                else:
                    login_url = "https://www.tandfonline.com/"
                    logger.info(f"Navigate to: {login_url}")
                driver.get(login_url)
                input("Press ENTER when you have logged in and are ready to continue...")
                logger.info("Continuing with downloads...")

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            logger.info("Continuing without Selenium")

    # Statistics
    stats = {
        "downloaded": 0,
        "exists": 0,
        "unavailable": 0,
        "failed": 0
    }

    try:
        for i, paper in enumerate(papers, 1):
            paper_id, doi, title, authors, year = paper

            logger.info(f"\n[{i}/{len(papers)}] {doi}")
            logger.info(f"  Title: {title[:60]}...")

            try:
                status, message = download_paper(
                    paper, driver, logger,
                    use_selenium=not args.no_selenium
                )

                stats[status] = stats.get(status, 0) + 1
                logger.info(f"  Result: {message}")

            except Exception as e:
                logger.error(f"  Error: {e}")
                mark_failed(DATABASE, paper_id, "taylor_francis", str(e))
                stats["failed"] += 1

            # Progress report
            if i % 20 == 0:
                logger.info(
                    f"\nProgress: {i}/{len(papers)} - "
                    f"Downloaded: {stats['downloaded']}, "
                    f"Exists: {stats['exists']}, "
                    f"Unavailable: {stats['unavailable']}, "
                    f"Failed: {stats['failed']}"
                )

            # Rate limiting
            if i < len(papers):
                time.sleep(args.delay)

    finally:
        if driver:
            driver.quit()
            logger.info("\nBrowser closed")

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Total processed: {len(papers)}")
    logger.info(f"  Downloaded: {stats['downloaded']}")
    logger.info(f"  Already existed: {stats['exists']}")
    logger.info(f"  Unavailable (paywalled): {stats['unavailable']}")
    logger.info(f"  Failed: {stats['failed']}")

    if stats['downloaded'] > 0:
        logger.info(f"\nPDFs saved to: {SHARKPAPERS_BASE}")


if __name__ == "__main__":
    main()
