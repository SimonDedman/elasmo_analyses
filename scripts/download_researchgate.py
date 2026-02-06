#!/usr/bin/env python3
"""
download_researchgate.py

Download PDFs from ResearchGate for papers that couldn't be obtained elsewhere.

This script:
1. Queries the database for papers marked as 'unavailable'
2. Uses undetected_chromedriver to bypass bot detection
3. Searches ResearchGate for each paper by title
4. Downloads publicly available PDFs (not requiring author request)
5. Saves to /media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/{YEAR}/
6. Updates database with download status

Usage:
    # Download all unavailable papers (using environment variables - avoids bash escaping issues)
    export RG_USERNAME='your@email.com'
    export RG_PASSWORD='yourp@ss!word'
    ./venv/bin/python scripts/download_researchgate.py

    # Or use command line (single quotes avoid bash ! expansion)
    ./venv/bin/python scripts/download_researchgate.py --username 'EMAIL' --password 'PASS'

    # Test mode (5 papers)
    ./venv/bin/python scripts/download_researchgate.py --test 5

    # Skip login prompt (use existing session)
    ./venv/bin/python scripts/download_researchgate.py --skip-login

Author: Simon Dedman / Claude
Date: 2026-01-06
"""

import argparse
import logging
import os
import re
import shutil
import sqlite3
import time
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote_plus, urljoin

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("ERROR: Selenium not installed. Run: pip install selenium undetected-chromedriver")
    exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE = BASE_DIR / "database/download_tracker.db"
SHARKPAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = BASE_DIR / "logs"
COOKIE_DIR = BASE_DIR / "browser_data"

# Current browser download directory
BROWSER_DOWNLOAD_DIR: Optional[Path] = None

# ResearchGate URLs
RG_BASE_URL = "https://www.researchgate.net"
RG_LOGIN_URL = f"{RG_BASE_URL}/login"
RG_SEARCH_URL = f"{RG_BASE_URL}/search/publication"

# Request settings
DELAY_BETWEEN_PAPERS = 2.5  # Longer delay for ResearchGate (be respectful)
PAGE_LOAD_TIMEOUT = 30
DOWNLOAD_WAIT_TIMEOUT = 20
SEARCH_WAIT_TIMEOUT = 10

# PDF validation
MAX_PDF_SIZE_MB = 50
MIN_PDF_SIZE_KB = 10


# ============================================================================
# HELPERS
# ============================================================================


def setup_logging(timestamp: str) -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"researchgate_download_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Log file: {log_file}")
    return logger


def clean_for_filename(text: str) -> str:
    """Clean text for use in filename."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text)
    words = text.split()[:8]
    return " ".join(words)


def get_first_author(authors_str: str) -> str:
    """Extract first author's last name."""
    if not authors_str:
        return "Unknown"
    authors = str(authors_str)
    for sep in [" & ", ";", ",", " and "]:
        if sep in authors:
            first = authors.split(sep)[0].strip()
            break
    else:
        first = authors.strip()
    parts = first.replace(",", " ").split()
    return parts[0] if parts else "Unknown"


def has_multiple_authors(authors_str: str) -> bool:
    """Check if there are multiple authors."""
    if not authors_str:
        return False
    return any(sep in str(authors_str) for sep in [" & ", ";", " and ", ", "])


def normalize_title(title: str) -> str:
    """Normalize title for comparison - lowercase, remove punctuation, collapse whitespace."""
    if not title:
        return ""
    # Remove punctuation and normalize
    title = unicodedata.normalize("NFKD", title.lower())
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two titles.
    Returns a score between 0.0 and 1.0.
    """
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    if not norm1 or not norm2:
        return 0.0

    # Use SequenceMatcher for fuzzy matching
    return SequenceMatcher(None, norm1, norm2).ratio()


def generate_filename(authors: str, title: str, year: int) -> str:
    """Generate standardized filename: FirstAuthor.etal.YEAR.Title words.pdf"""
    author = get_first_author(authors)
    title_clean = clean_for_filename(title)
    if has_multiple_authors(authors):
        return f"{author}.etal.{int(year)}.{title_clean}.pdf"
    return f"{author}.{int(year)}.{title_clean}.pdf"


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================


def get_unavailable_papers(limit: Optional[int] = None) -> list[tuple]:
    """
    Get papers marked as unavailable (couldn't be downloaded from publishers).

    Returns list of tuples: (id, doi, title, authors, year)
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    query = """
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.status = 'unavailable'
        AND p.id NOT IN (
            SELECT paper_id FROM download_status WHERE status = 'downloaded'
        )
        ORDER BY p.year DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    papers = cur.fetchall()
    conn.close()
    return papers


def update_status(paper_id: int, status: str, source: str, notes: str = "") -> None:
    """Update download status in database (prevents duplicates)."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Delete any existing records for this paper first (prevents duplicates)
    cur.execute("DELETE FROM download_status WHERE paper_id = ?", (paper_id,))

    # Insert new record
    cur.execute("""
        INSERT INTO download_status (paper_id, status, source, download_date, notes)
        VALUES (?, ?, ?, datetime('now'), ?)
    """, (paper_id, status, source, notes))

    conn.commit()
    conn.close()


# ============================================================================
# BROWSER FUNCTIONS
# ============================================================================


def setup_browser(logger: logging.Logger, headless: bool = False) -> Optional[uc.Chrome]:
    """
    Set up Chrome browser with persistent profile for cookie storage.

    Uses undetected_chromedriver to avoid ResearchGate bot detection.
    """
    try:
        profile_dir = COOKIE_DIR / "chrome_profile_researchgate"
        profile_dir.mkdir(parents=True, exist_ok=True)

        options = uc.ChromeOptions()

        if headless:
            options.add_argument("--headless=new")

        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--profile-directory=ResearchGate")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1400,900")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--remote-debugging-port=0")

        # Create temp download directory
        temp_download_dir = COOKIE_DIR / "downloads_researchgate"
        temp_download_dir.mkdir(parents=True, exist_ok=True)

        # Download preferences
        prefs = {
            "download.default_directory": str(temp_download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
            "plugins.always_open_pdf_internally": False,
            "profile.default_content_settings.popups": 0,
            "download.extensions_to_open": "",
            "profile.default_content_setting_values.automatic_downloads": 1,
        }
        options.add_experimental_option("prefs", prefs)
        options.add_argument("--disable-pdf-viewer")

        logger.info("Starting Chrome for ResearchGate...")
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

        # Set global download directory
        global BROWSER_DOWNLOAD_DIR
        BROWSER_DOWNLOAD_DIR = temp_download_dir

        logger.info("Browser initialized successfully")
        return driver

    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        return None


def login_to_researchgate(driver: uc.Chrome, username: str, password: str, logger: logging.Logger) -> bool:
    """
    Login to ResearchGate and maintain session.

    Returns True if login successful.
    """
    try:
        logger.info("Navigating to ResearchGate login page...")
        driver.get(RG_LOGIN_URL)
        time.sleep(3)

        # Find login form fields
        try:
            email_field = driver.find_element(By.NAME, "login")
            password_field = driver.find_element(By.NAME, "password")

            # Enter credentials
            email_field.clear()
            email_field.send_keys(username)
            time.sleep(0.5)

            password_field.clear()
            password_field.send_keys(password)
            time.sleep(0.5)

            # Find and click login button
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            time.sleep(5)  # Wait for login to complete

            # Check if login successful
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()

            # Signs of successful login
            if "login" not in current_url and ("profile" in page_source or "logout" in page_source):
                logger.info("Successfully logged in to ResearchGate")
                return True
            else:
                logger.error("Login may have failed - please check manually")
                return False

        except Exception as e:
            logger.error(f"Error finding login form: {e}")
            logger.info("Please complete login manually in the browser window")
            input("Press Enter when login is complete...")

            # Check login status after manual login
            page_source = driver.page_source.lower()
            if "profile" in page_source or "logout" in page_source:
                logger.info("Login appears successful")
                return True
            return False

    except Exception as e:
        logger.error(f"Login error: {e}")
        return False


def search_researchgate(
    driver: uc.Chrome,
    title: str,
    logger: logging.Logger,
    authors: str = None,
    min_similarity: float = 0.70,
) -> Tuple[Optional[str], float]:
    """
    Search ResearchGate for a paper using author + title strategy.

    Strategy:
    1. First try: Lead author surname + first few title words
    2. Second try: Title-only search (first 80 chars)
    3. Verify results by title similarity matching

    Returns:
        Tuple of (publication_url, similarity_score) or (None, 0.0) if not found.
    """
    # Get lead author surname for search
    lead_author = get_first_author(authors) if authors else ""

    # Clean title - keep key words
    clean_title = re.sub(r'[^\w\s-]', ' ', title).strip()
    title_words = clean_title.split()[:8]  # First 8 words
    title_query = ' '.join(title_words)

    # Search strategies to try
    search_queries = []

    # Strategy 1: Author + title words (most specific)
    if lead_author and lead_author != "Unknown":
        search_queries.append(f"{lead_author} {title_query}")

    # Strategy 2: Title only (first 80 chars)
    search_queries.append(clean_title[:80])

    # Strategy 3: Just first few significant title words
    if len(title_words) > 3:
        search_queries.append(' '.join(title_words[:5]))

    best_match_url = None
    best_similarity = 0.0

    for query in search_queries:
        try:
            search_url = f"{RG_SEARCH_URL}?q={quote_plus(query)}"
            logger.debug(f"Trying search: {query[:50]}...")

            driver.get(search_url)
            time.sleep(SEARCH_WAIT_TIMEOUT)

            # Updated CSS selectors for current ResearchGate (2025/2026)
            # ResearchGate frequently changes their CSS classes
            selectors = [
                # Current selectors (as of 2026)
                "a[href*='/publication/'][class*='nova']",
                "div[class*='search-result'] a[href*='/publication/']",
                "div[class*='PublicationItem'] a[href*='/publication/']",
                # Generic fallbacks
                "a[href*='/publication/']",
                # Legacy selectors
                "div.nova-legacy-e-link-color--theme a[href*='/publication/']",
                "div.nova-legacy-o-stack__item a[href*='/publication/']",
                "div.nova-v-publication-item a[href*='/publication/']",
            ]

            found_publications = []

            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements[:10]:  # Check first 10 results
                        try:
                            pub_url = elem.get_attribute("href")
                            if pub_url and "/publication/" in pub_url:
                                # Try to get the title text from the element or parent
                                result_title = elem.text.strip()
                                if not result_title:
                                    # Try parent element
                                    parent = elem.find_element(By.XPATH, "./..")
                                    result_title = parent.text.strip()

                                if result_title and pub_url not in [p[0] for p in found_publications]:
                                    found_publications.append((pub_url, result_title))
                        except Exception:
                            continue
                except Exception:
                    continue

            # Score each found publication by title similarity
            for pub_url, result_title in found_publications:
                sim = title_similarity(title, result_title)
                logger.debug(f"  Result: {result_title[:50]}... (similarity: {sim:.2f})")

                if sim > best_similarity:
                    best_similarity = sim
                    best_match_url = pub_url

            # If we found a good match, stop searching
            if best_similarity >= min_similarity:
                logger.debug(f"Found good match (similarity: {best_similarity:.2f})")
                break

        except Exception as e:
            logger.debug(f"Search error for query '{query[:30]}...': {e}")
            continue

    if best_match_url and best_similarity >= min_similarity:
        logger.debug(f"Best match: {best_match_url} (similarity: {best_similarity:.2f})")
        return best_match_url, best_similarity
    elif best_match_url:
        logger.debug(f"Low similarity match ({best_similarity:.2f}) - skipping: {best_match_url}")
        return None, best_similarity
    else:
        logger.debug("No publication found in search results")
        return None, 0.0


def search_only_researchgate(
    driver: uc.Chrome,
    paper: tuple,
    logger: logging.Logger,
    stats: dict,
    results: list,
) -> dict:
    """
    Search ResearchGate for a paper without downloading.

    Returns dict with search results for CSV output.
    """
    paper_id, doi, title, authors, year = paper

    result = {
        "paper_id": paper_id,
        "doi": doi,
        "title": title[:100] if title else "",
        "authors": authors[:50] if authors else "",
        "year": year,
        "found": False,
        "has_pdf": False,
        "requires_request": False,
        "url": "",
        "similarity": 0.0,
    }

    lead_author = get_first_author(authors) if authors else "Unknown"
    logger.info(f"  Searching: {lead_author} - {title[:50]}...")

    try:
        # Search for paper using author + title strategy
        pub_url, similarity = search_researchgate(driver, title, logger, authors=authors)

        if not pub_url:
            logger.info(f"    NOT FOUND (best similarity: {similarity:.2f})")
            stats["not_found"] += 1
            result["similarity"] = similarity
            results.append(result)
            return result

        result["found"] = True
        result["url"] = pub_url
        result["similarity"] = similarity
        stats["found"] += 1

        # Navigate to publication page to check PDF availability
        driver.get(pub_url)
        time.sleep(3)

        page_source = driver.page_source.lower()

        # Check for public PDF
        if "download full-text" in page_source or "download pdf" in page_source:
            result["has_pdf"] = True
            stats["has_pdf"] += 1
            logger.info(f"    FOUND (sim={similarity:.2f}) - PDF AVAILABLE: {pub_url[:60]}")
        elif "request full-text" in page_source:
            result["requires_request"] = True
            stats["requires_request"] += 1
            logger.info(f"    FOUND (sim={similarity:.2f}) - Requires request: {pub_url[:60]}")
        else:
            logger.info(f"    FOUND (sim={similarity:.2f}) - No PDF detected: {pub_url[:60]}")

        results.append(result)
        return result

    except Exception as e:
        logger.error(f"    ERROR: {e}")
        stats["errors"] += 1
        results.append(result)
        return result


def download_from_researchgate(
    driver: uc.Chrome,
    paper: tuple,
    logger: logging.Logger,
    stats: dict,
    temp_dir: Path,
) -> bool:
    """
    Download a paper from ResearchGate.

    Strategy:
    1. Search ResearchGate for the paper by title
    2. Navigate to publication page
    3. Look for public PDF download (not "Request full-text")
    4. Download and verify PDF
    """
    paper_id, doi, title, authors, year = paper

    # Determine output path
    year_val = int(year) if year else 0
    year_dir = SHARKPAPERS / str(year_val) if year_val else SHARKPAPERS / "unknown_year"
    year_dir.mkdir(parents=True, exist_ok=True)

    filename = generate_filename(authors, title, year_val)
    output_path = year_dir / filename

    # Check if already exists
    if output_path.exists() and output_path.stat().st_size > 10240:
        logger.info(f"  EXISTS: {filename}")
        update_status(paper_id, "downloaded", "researchgate-exists")
        stats["existed"] += 1
        return True

    # Check for similar files
    title_prefix = (title or "")[:20].lower()
    for existing_pdf in year_dir.glob("*.pdf"):
        if title_prefix and title_prefix in existing_pdf.name.lower():
            if existing_pdf.stat().st_size > 10240:
                logger.info(f"  EXISTS (similar): {existing_pdf.name[:60]}")
                update_status(paper_id, "downloaded", "researchgate-exists-similar")
                stats["existed"] += 1
                return True

    lead_author = get_first_author(authors) if authors else "Unknown"
    logger.info(f"  Searching ResearchGate for: {lead_author} - {title[:50]}...")

    # Clear temp directories
    for f in temp_dir.glob("*.pdf"):
        try:
            f.unlink()
        except:
            pass
    clear_browser_downloads(logger)

    try:
        # Search for paper using author + title strategy
        pub_url, similarity = search_researchgate(driver, title, logger, authors=authors)

        if not pub_url:
            logger.warning(f"  NOT FOUND on ResearchGate (best similarity: {similarity:.2f})")
            update_status(paper_id, "unavailable", "researchgate", f"Not found (sim={similarity:.2f})")
            stats["not_found"] += 1
            return False

        # Navigate to publication page
        logger.info(f"  Found publication (similarity: {similarity:.2f}), checking for PDF...")
        driver.get(pub_url)
        time.sleep(5)

        # Look for PDF download options
        pdf_downloaded = False

        # Common ResearchGate PDF download patterns
        pdf_selectors = [
            "a.research-detail-header-section__button[href*='Download']",
            "a[href*='download'][href*='pdf']",
            "button[data-testid='download-full-text']",
            "div.research-detail-middle-section__action a",
            "a.nova-legacy-c-button-group__item",
        ]

        # Also look for text-based download links
        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for elem in all_links:
                text = (elem.text or "").strip().upper()
                # Look for "Download" but NOT "Request"
                if "DOWNLOAD" in text and "REQUEST" not in text and "FULL" in text:
                    href = elem.get_attribute("href")
                    logger.info(f"  Found download link: {text}")

                    # Check if this is a direct PDF link or requires clicking
                    if href and "pdf" in href.lower():
                        driver.get(href)
                    else:
                        elem.click()

                    time.sleep(3)
                    pdf_downloaded = wait_for_download(temp_dir, logger)
                    if not pdf_downloaded:
                        pdf_downloaded = check_browser_downloads(output_path, logger, timeout=5)
                    if pdf_downloaded:
                        break
        except Exception as e:
            logger.debug(f"Text-based search failed: {e}")

        # Try CSS selectors
        if not pdf_downloaded:
            for selector in pdf_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        try:
                            elem.click()
                            time.sleep(3)
                            pdf_downloaded = wait_for_download(temp_dir, logger)
                            if not pdf_downloaded:
                                pdf_downloaded = check_browser_downloads(output_path, logger, timeout=5)
                            if pdf_downloaded:
                                break
                        except:
                            continue
                except:
                    continue

                if pdf_downloaded:
                    break

        # Check if we got a "Request full-text" instead of download
        page_source = driver.page_source.lower()
        if "request full-text" in page_source and not pdf_downloaded:
            logger.warning(f"  REQUIRES REQUEST: PDF not publicly available")
            update_status(paper_id, "unavailable", "researchgate", "Requires author request")
            stats["requires_request"] += 1
            return False

        # Process downloaded file
        if pdf_downloaded:
            pdf_files = list(temp_dir.glob("*.pdf"))
            if pdf_files:
                downloaded_file = pdf_files[0]
                file_size = downloaded_file.stat().st_size

                if file_size > MIN_PDF_SIZE_KB * 1024:
                    # Verify it's a real PDF
                    with open(downloaded_file, "rb") as f:
                        if f.read(4) == b"%PDF":
                            # Move to final location
                            downloaded_file.rename(output_path)
                            logger.info(f"  SUCCESS: {filename} ({file_size:,} bytes)")
                            update_status(paper_id, "downloaded", "researchgate")
                            stats["downloaded"] += 1
                            return True

                    # Invalid PDF
                    downloaded_file.unlink()
                    logger.warning(f"  FAIL: Invalid PDF format")
                else:
                    downloaded_file.unlink()
                    logger.warning(f"  FAIL: PDF too small ({file_size} bytes)")

        # Failed
        logger.warning(f"  FAIL: Could not download PDF from ResearchGate")
        update_status(paper_id, "unavailable", "researchgate", "No public PDF found")
        stats["failed"] += 1
        return False

    except Exception as e:
        logger.error(f"  ERROR: {e}")
        stats["failed"] += 1
        return False


def wait_for_download(temp_dir: Path, logger: logging.Logger, timeout: int = DOWNLOAD_WAIT_TIMEOUT) -> bool:
    """Wait for a PDF file to appear in temp directory."""
    start = time.time()

    while time.time() - start < timeout:
        pdf_files = list(temp_dir.glob("*.pdf"))
        partial_files = list(temp_dir.glob("*.crdownload"))

        if pdf_files and not partial_files:
            return True

        if partial_files:
            time.sleep(1)
            continue

        time.sleep(0.5)

    return False


def check_browser_downloads(output_path: Path, logger: logging.Logger, timeout: int = 10) -> bool:
    """
    Check the browser's download directory for auto-downloaded PDFs.
    Move any new PDF to the output path.
    """
    if BROWSER_DOWNLOAD_DIR is None or not BROWSER_DOWNLOAD_DIR.exists():
        return False
    browser_download_dir = BROWSER_DOWNLOAD_DIR

    start = time.time()
    while time.time() - start < timeout:
        partial_files = list(browser_download_dir.glob("*.crdownload"))
        if partial_files:
            time.sleep(0.5)
            continue

        pdf_files = sorted(browser_download_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if pdf_files:
            newest_pdf = pdf_files[0]
            with open(newest_pdf, "rb") as f:
                if f.read(4) == b"%PDF":
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(newest_pdf), str(output_path))
                    logger.info(f"    Auto-downloaded PDF moved to: {output_path.name}")
                    return True
            newest_pdf.unlink()

        time.sleep(0.5)

    return False


def clear_browser_downloads(logger: logging.Logger) -> None:
    """Clear any existing PDFs from browser download directory."""
    if BROWSER_DOWNLOAD_DIR is None or not BROWSER_DOWNLOAD_DIR.exists():
        return
    browser_download_dir = BROWSER_DOWNLOAD_DIR
    if browser_download_dir.exists():
        for pdf in browser_download_dir.glob("*.pdf"):
            try:
                pdf.unlink()
            except Exception:
                pass
        for partial in browser_download_dir.glob("*.crdownload"):
            try:
                partial.unlink()
            except Exception:
                pass


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Download PDFs from ResearchGate for papers marked as unavailable",
        epilog="Credentials can also be set via RG_USERNAME and RG_PASSWORD environment variables."
    )
    parser.add_argument(
        "--username",
        type=str,
        default=os.environ.get("RG_USERNAME"),
        help="ResearchGate email/username (or set RG_USERNAME env var)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=os.environ.get("RG_PASSWORD"),
        help="ResearchGate password (or set RG_PASSWORD env var)",
    )
    parser.add_argument(
        "--test",
        type=int,
        metavar="N",
        help="Test mode: process only N papers",
    )
    parser.add_argument(
        "--skip-login",
        action="store_true",
        help="Skip login prompt (use existing session cookies)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (not recommended for login)",
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Search ResearchGate and report findings without downloading",
    )
    args = parser.parse_args()

    # Validate credentials (not needed for search-only mode)
    if not args.search_only and not args.skip_login and (not args.username or not args.password):
        print("ERROR: --username and --password required (or set RG_USERNAME/RG_PASSWORD env vars)")
        print("       Alternatively, use --skip-login if you have an existing session")
        print("       Or use --search-only to just search without downloading")
        return

    # Warn about headless mode (doesn't apply to search-only)
    if args.headless and not args.skip_login and not args.search_only:
        print("WARNING: Headless mode requires --skip-login (can't do interactive login)")
        print("         Use visible mode for initial login, then headless with --skip-login")
        return

    # Setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = setup_logging(timestamp)

    logger.info("=" * 70)
    logger.info("RESEARCHGATE PDF DOWNLOADER")
    logger.info("=" * 70)
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Database: {DATABASE}")
    logger.info(f"Output: {SHARKPAPERS}")

    # Get unavailable papers
    papers = get_unavailable_papers(limit=args.test)

    if not papers:
        logger.info("No unavailable papers to search for on ResearchGate!")
        return

    logger.info(f"\nFound {len(papers)} papers marked as unavailable")

    # Initialize browser
    logger.info("\nInitializing browser...")
    driver = setup_browser(logger, headless=args.headless)

    if driver is None:
        logger.error("Failed to initialize browser")
        return

    # Create temp directory
    temp_dir = SHARKPAPERS / ".temp_researchgate"
    temp_dir.mkdir(exist_ok=True)

    # Statistics - different stats for search-only vs download mode
    if args.search_only:
        stats = {
            "found": 0,
            "not_found": 0,
            "has_pdf": 0,
            "requires_request": 0,
            "errors": 0,
        }
        search_results = []
    else:
        stats = {
            "downloaded": 0,
            "failed": 0,
            "existed": 0,
            "not_found": 0,
            "requires_request": 0,
        }

    try:
        # Login to ResearchGate (skip for search-only mode)
        if args.search_only:
            logger.info("Search-only mode - no login required")
        elif not args.skip_login:
            print("\n" + "=" * 70)
            print("RESEARCHGATE LOGIN")
            print("=" * 70)
            print("\nLogging in to ResearchGate...")
            print("Be respectful with requests to avoid account suspension!")
            print("=" * 70)

            success = login_to_researchgate(driver, args.username, args.password, logger)
            if not success:
                logger.warning("Login may have failed, but proceeding anyway...")
        else:
            logger.info("Skipping login (using existing session)")

        # Process papers
        logger.info(f"\n{'=' * 70}")
        if args.search_only:
            logger.info(f"SEARCH-ONLY: Checking ResearchGate for {len(papers)} papers")
        else:
            logger.info(f"SEARCHING RESEARCHGATE FOR {len(papers)} PAPERS")
        logger.info(f"{'=' * 70}\n")

        for i, paper in enumerate(papers, 1):
            logger.info(f"[{i}/{len(papers)}] Processing paper...")

            if args.search_only:
                search_only_researchgate(driver, paper, logger, stats, search_results)
            else:
                download_from_researchgate(driver, paper, logger, stats, temp_dir)

            # Rate limiting (be respectful to ResearchGate)
            time.sleep(DELAY_BETWEEN_PAPERS)

            # Progress report
            if i % 50 == 0:
                if args.search_only:
                    logger.info(f"Progress: {i}/{len(papers)} - {stats['found']} found, {stats['has_pdf']} with PDF")
                else:
                    logger.info(f"Progress: {i}/{len(papers)} - {stats['downloaded']} OK, {stats['failed']} fail")

    finally:
        # Cleanup
        try:
            driver.quit()
            logger.info("Browser closed")
        except:
            pass

        # Remove temp directory contents
        for f in temp_dir.glob("*"):
            try:
                f.unlink()
            except:
                pass

    # Summary and output
    logger.info("\n" + "=" * 70)
    if args.search_only:
        logger.info("RESEARCHGATE SEARCH SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total searched: {len(papers)}")
        logger.info(f"Found on ResearchGate: {stats['found']}")
        logger.info(f"  - With public PDF: {stats['has_pdf']}")
        logger.info(f"  - Requires request: {stats['requires_request']}")
        logger.info(f"Not found: {stats['not_found']}")
        logger.info(f"Errors: {stats['errors']}")

        # Save results to CSV
        import csv
        csv_path = BASE_DIR / "outputs" / f"researchgate_search_{timestamp}.csv"
        csv_path.parent.mkdir(exist_ok=True)
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["paper_id", "doi", "title", "authors", "year", "found", "has_pdf", "requires_request", "url", "similarity"])
            writer.writeheader()
            writer.writerows(search_results)
        logger.info(f"\nResults saved to: {csv_path}")

        # Summary of downloadable papers
        downloadable = [r for r in search_results if r["has_pdf"]]
        if downloadable:
            logger.info(f"\n{len(downloadable)} papers have public PDFs available for download!")
    else:
        logger.info("RESEARCHGATE DOWNLOAD SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Downloaded: {stats['downloaded']}")
        logger.info(f"Already existed: {stats['existed']}")
        logger.info(f"Not found: {stats['not_found']}")
        logger.info(f"Requires request: {stats['requires_request']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Output: {SHARKPAPERS}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
