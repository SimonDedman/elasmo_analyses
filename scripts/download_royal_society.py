#!/usr/bin/env python3
"""
download_royal_society.py

Download papers from Royal Society Publishing (DOIs starting with 10.1098/).

Royal Society has multiple journals with varying open access policies:
- Proceedings B (rspb): Biology papers, many open access
- Royal Society Open Science (rsos): Fully open access
- Philosophical Transactions A & B: Mixed access

NOTE: Royal Society uses Cloudflare protection which blocks simple HTTP requests.
This script tries multiple strategies:
1. Direct PDF URLs (often blocked by Cloudflare)
2. Unpaywall API for alternative OA locations (repositories, PubMed Central, etc.)
3. Optional: Selenium browser automation (--use-browser flag)

For best results with Cloudflare-protected sites, use --use-browser mode
which requires: pip install selenium undetected-chromedriver

Usage:
    ./venv/bin/python scripts/download_royal_society.py
    ./venv/bin/python scripts/download_royal_society.py --test 5
    ./venv/bin/python scripts/download_royal_society.py --use-browser
    ./venv/bin/python scripts/download_royal_society.py --email your@email.com

Author: Simon Dedman / Claude
Date: 2026-01-06
"""

import argparse
import logging
import os
import re
import sqlite3
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Optional imports for browser-based downloading
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE = BASE_DIR / "database/download_tracker.db"
SHARKPAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = BASE_DIR / "logs"

# Royal Society DOI prefix
DOI_PREFIX = "10.1098/%"

# API Configuration
UNPAYWALL_EMAIL = "simon.dedman@ucd.ie"  # Required by Unpaywall API
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

# Request settings
DELAY_BETWEEN_REQUESTS = 2.0  # Be polite to servers
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/pdf,text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# University proxy configuration (FIU OpenAthens)
PROXY_ENABLED = False  # Set via --proxy flag
PROXY_BASE = "royalsocietypublishing-org.eu1.proxy.openathens.net"
ORIGINAL_BASE = "royalsocietypublishing.org"


def to_proxy_url(url: str) -> str:
    """Convert Royal Society URL to university proxy URL."""
    if PROXY_ENABLED and url:
        return url.replace(ORIGINAL_BASE, PROXY_BASE).replace("http://", "https://")
    return url


# ============================================================================
# HELPERS
# ============================================================================


def setup_logging(timestamp: str) -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"royal_society_{timestamp}.log"

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
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    # Remove special characters except spaces
    text = re.sub(r"[^\w\s-]", "", text)
    # Take first 8 words
    words = text.split()[:8]
    return " ".join(words)


def get_first_author(authors_str: str) -> str:
    """Extract first author's last name from authors string."""
    if not authors_str:
        return "Unknown"

    authors = str(authors_str)

    # Handle different separator patterns
    for sep in [" & ", ";", ",", " and "]:
        if sep in authors:
            first = authors.split(sep)[0].strip()
            break
    else:
        first = authors.strip()

    # Extract last name (usually first word or word before comma)
    parts = first.replace(",", " ").split()
    return parts[0] if parts else "Unknown"


def has_multiple_authors(authors_str: str) -> bool:
    """Check if there are multiple authors."""
    if not authors_str:
        return False
    authors = str(authors_str)
    return any(sep in authors for sep in [" & ", ";", " and ", ", "])


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


def get_pending_papers() -> list[tuple]:
    """
    Get Royal Society papers from database that haven't been downloaded.

    Returns list of tuples: (id, doi, title, authors, year)
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        WHERE p.doi LIKE ?
        AND p.id NOT IN (
            SELECT paper_id FROM download_status WHERE status = 'downloaded'
        )
        ORDER BY p.year DESC
    """,
        (DOI_PREFIX,),
    )

    papers = cur.fetchall()
    conn.close()
    return papers


def mark_status(
    paper_id: int, status: str, source: str, notes: str = ""
) -> None:
    """Update download status in database."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR REPLACE INTO download_status
        (paper_id, status, source, download_date, notes)
        VALUES (?, ?, ?, datetime('now'), ?)
    """,
        (paper_id, status, source, notes),
    )

    conn.commit()
    conn.close()


# ============================================================================
# DOWNLOAD FUNCTIONS
# ============================================================================


def build_royal_society_pdf_url(doi: str) -> Optional[str]:
    """
    Build direct PDF URL for Royal Society papers.

    Royal Society PDF URLs follow patterns like:
    - https://royalsocietypublishing.org/doi/pdf/10.1098/rspb.2024.2192
    """
    url = f"https://royalsocietypublishing.org/doi/pdf/{doi}"
    return to_proxy_url(url)


def download_pdf(
    url: str, output_path: Path, logger: logging.Logger
) -> dict:
    """
    Download PDF from URL.

    Returns dict with status and details.
    """
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Attempt {attempt + 1}: {url}")

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()

                # Check if it's actually a PDF
                if "pdf" in content_type or response.content[:4] == b"%PDF":
                    # Save PDF
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    file_size = output_path.stat().st_size

                    # Verify it's a real PDF (at least 10KB to avoid error pages)
                    if file_size < 10240:
                        with open(output_path, "rb") as f:
                            if f.read(4) != b"%PDF":
                                output_path.unlink()
                                return {
                                    "status": "failed",
                                    "message": "Invalid PDF (too small or wrong format)",
                                }

                    return {
                        "status": "success",
                        "size_bytes": file_size,
                        "url": url,
                    }
                else:
                    return {
                        "status": "failed",
                        "message": f"Not PDF: {content_type[:50]}",
                    }

            elif response.status_code == 403:
                return {"status": "failed", "message": "Access denied (403)"}
            elif response.status_code == 404:
                return {"status": "failed", "message": "Not found (404)"}
            else:
                logger.warning(
                    f"HTTP {response.status_code} on attempt {attempt + 1}"
                )
                time.sleep(2**attempt)
                continue

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}")
            time.sleep(2**attempt)
            continue
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
            time.sleep(2**attempt)
            continue
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}: {e}")
            return {"status": "failed", "message": str(e)[:50]}

    return {"status": "failed", "message": f"Failed after {MAX_RETRIES} attempts"}


def query_unpaywall(doi: str, email: str, logger: logging.Logger) -> dict:
    """
    Query Unpaywall API for open access PDF URLs.

    Returns dict with is_oa, pdf_urls (list), and oa_status.
    """
    url = f"{UNPAYWALL_BASE_URL}/{doi}"
    params = {"email": email}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                result = {
                    "is_oa": data.get("is_oa", False),
                    "oa_status": data.get("oa_status", "unknown"),
                    "pdf_urls": [],
                }

                if data.get("is_oa"):
                    # Collect all OA locations, not just the best one
                    oa_locations = data.get("oa_locations", [])
                    best_oa = data.get("best_oa_location", {})

                    # Add best location first if it has a PDF URL
                    if best_oa:
                        pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
                        if pdf_url:
                            result["pdf_urls"].append({
                                "url": pdf_url,
                                "host_type": best_oa.get("host_type", "unknown"),
                            })
                            result["host_type"] = best_oa.get("host_type", "")

                    # Add other locations
                    for loc in oa_locations:
                        pdf_url = loc.get("url_for_pdf") or loc.get("url")
                        if pdf_url and pdf_url not in [u["url"] for u in result["pdf_urls"]]:
                            result["pdf_urls"].append({
                                "url": pdf_url,
                                "host_type": loc.get("host_type", "unknown"),
                            })

                return result

            elif response.status_code == 404:
                logger.debug(f"DOI not found in Unpaywall: {doi}")
                return {"is_oa": False, "oa_status": "not_found", "pdf_urls": []}
            else:
                logger.warning(f"Unpaywall returned {response.status_code}")
                time.sleep(2**attempt)
                continue

        except requests.exceptions.Timeout:
            logger.warning(f"Unpaywall timeout on attempt {attempt + 1}")
            time.sleep(2**attempt)
            continue
        except Exception as e:
            logger.error(f"Unpaywall error for {doi}: {e}")
            return {"is_oa": False, "oa_status": "error", "error": str(e), "pdf_urls": []}

    return {"is_oa": False, "oa_status": "failed_after_retries", "pdf_urls": []}


def setup_browser(download_dir: Path, logger: logging.Logger) -> Optional[object]:
    """
    Set up undetected Chrome browser for downloading PDFs.

    Returns browser instance or None if setup fails.
    """
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium not available. Install: pip install selenium undetected-chromedriver")
        return None

    try:
        # Configure Chrome options
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # Set download preferences
        prefs = {
            "download.default_directory": str(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_settings.popups": 0,
        }
        options.add_experimental_option("prefs", prefs)

        # Create browser
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(60)

        logger.info("Browser initialized successfully")
        return driver

    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        return None


def download_with_browser(
    doi: str,
    output_path: Path,
    driver: object,
    logger: logging.Logger,
) -> dict:
    """
    Download PDF using browser automation to bypass Cloudflare.

    Returns dict with status and details.
    """
    pdf_url = f"https://royalsocietypublishing.org/doi/pdf/{doi}"
    pdf_url = to_proxy_url(pdf_url)
    temp_dir = output_path.parent / ".temp_downloads"
    temp_dir.mkdir(exist_ok=True)

    try:
        # Clear temp directory
        for f in temp_dir.glob("*.pdf"):
            f.unlink()

        # Update download directory
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(temp_dir),
        })

        # Navigate to PDF URL
        logger.debug(f"Browser navigating to: {pdf_url}")
        driver.get(pdf_url)

        # Wait for potential Cloudflare challenge
        time.sleep(5)

        # Check if we got a PDF or if we're on an error page
        current_url = driver.current_url

        # If redirected to PDF viewer or download started
        if "pdf" in current_url.lower() or ".pdf" in current_url.lower():
            # Wait for download to complete
            wait_time = 0
            max_wait = 30
            downloaded_file = None

            while wait_time < max_wait:
                pdf_files = list(temp_dir.glob("*.pdf"))
                partial_files = list(temp_dir.glob("*.crdownload"))

                if pdf_files and not partial_files:
                    downloaded_file = pdf_files[0]
                    break

                time.sleep(1)
                wait_time += 1

            if downloaded_file and downloaded_file.exists():
                file_size = downloaded_file.stat().st_size

                if file_size > 10240:  # At least 10KB
                    # Move to final location
                    downloaded_file.rename(output_path)
                    return {
                        "status": "success",
                        "size_bytes": file_size,
                        "url": pdf_url,
                    }
                else:
                    downloaded_file.unlink()
                    return {"status": "failed", "message": "Downloaded file too small"}

        return {"status": "failed", "message": "Browser download failed"}

    except Exception as e:
        logger.error(f"Browser download error: {e}")
        return {"status": "failed", "message": str(e)[:50]}


def build_alternative_urls(doi: str) -> list[dict]:
    """
    Build alternative PDF URLs for Royal Society papers.

    Royal Society papers can sometimes be accessed via different URL patterns.
    """
    urls = []

    # Pattern 1: Standard PDF URL
    urls.append({
        "url": to_proxy_url(f"https://royalsocietypublishing.org/doi/pdf/{doi}"),
        "source": "royal_society_pdf",
    })

    # Pattern 2: EPUB full (redirects to PDF sometimes)
    urls.append({
        "url": to_proxy_url(f"https://royalsocietypublishing.org/doi/epdf/{doi}"),
        "source": "royal_society_epdf",
    })

    # Pattern 3: Full text HTML (might have PDF link)
    urls.append({
        "url": to_proxy_url(f"https://royalsocietypublishing.org/doi/full/{doi}"),
        "source": "royal_society_full",
    })

    return urls


def download_paper(
    paper: tuple,
    email: str,
    logger: logging.Logger,
    stats: dict,
    driver: Optional[object] = None,
) -> None:
    """
    Download a single paper using multiple strategies.

    Tries:
    1. Browser-based download (if driver provided)
    2. Direct Royal Society PDF URLs (multiple patterns)
    3. All Unpaywall OA locations
    """
    paper_id, doi, title, authors, year = paper

    # Determine output path
    year_val = int(year) if year else 0
    year_dir = SHARKPAPERS / str(year_val) if year_val else SHARKPAPERS / "unknown_year"
    year_dir.mkdir(parents=True, exist_ok=True)

    filename = generate_filename(authors, title, year_val)
    output_path = year_dir / filename

    # Check if already exists
    if output_path.exists():
        logger.info(f"EXISTS: {filename}")
        mark_status(paper_id, "downloaded", "royal_society-exists")
        stats["skipped"] += 1
        return

    logger.info(f"Processing: {doi}")

    # Track all attempts for error reporting
    attempts_log = []

    # Strategy 1: Browser-based download (best for Cloudflare-protected sites)
    if driver is not None:
        result = download_with_browser(doi, output_path, driver, logger)
        attempts_log.append(f"browser: {result.get('message', result['status'])}")

        if result["status"] == "success":
            logger.info(f"OK (browser): {filename} ({result['size_bytes'] // 1024}KB)")
            mark_status(paper_id, "downloaded", "royal_society_browser")
            stats["downloaded"] += 1
            return

        time.sleep(1)

    # Strategy 2: Try direct Royal Society URLs (may be blocked by Cloudflare)
    direct_urls = build_alternative_urls(doi)
    for url_info in direct_urls:
        result = download_pdf(url_info["url"], output_path, logger)
        attempts_log.append(f"{url_info['source']}: {result.get('message', result['status'])}")

        if result["status"] == "success":
            logger.info(f"OK ({url_info['source']}): {filename} ({result['size_bytes'] // 1024}KB)")
            mark_status(paper_id, "downloaded", url_info["source"])
            stats["downloaded"] += 1
            return

        time.sleep(0.5)  # Brief delay between attempts

    # Strategy 3: Try Unpaywall API (all locations - repositories, PMC, etc.)
    unpaywall_result = query_unpaywall(doi, email, logger)
    time.sleep(0.5)

    pdf_urls = unpaywall_result.get("pdf_urls", [])
    if unpaywall_result.get("is_oa") and pdf_urls:
        for url_info in pdf_urls:
            pdf_url = url_info["url"]
            host_type = url_info.get("host_type", "unknown")

            logger.debug(f"Trying Unpaywall URL ({host_type}): {pdf_url}")
            result = download_pdf(pdf_url, output_path, logger)
            attempts_log.append(f"unpaywall-{host_type}: {result.get('message', result['status'])}")

            if result["status"] == "success":
                source = f"unpaywall-{host_type}"
                logger.info(f"OK ({source}): {filename} ({result['size_bytes'] // 1024}KB)")
                mark_status(paper_id, "downloaded", source)
                stats["downloaded"] += 1
                return

            time.sleep(0.5)

    # All strategies failed
    oa_status = unpaywall_result.get("oa_status", "unknown")
    notes = f"oa_status: {oa_status}; tried {len(attempts_log)} sources"
    mark_status(paper_id, "unavailable", "royal_society", notes)
    logger.warning(f"FAIL: {doi} - OA: {oa_status}, attempts: {len(attempts_log)}")
    stats["failed"] += 1


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download papers from Royal Society Publishing"
    )
    parser.add_argument(
        "--test", type=int, metavar="N", help="Test mode: process only N papers"
    )
    parser.add_argument(
        "--email",
        type=str,
        default=UNPAYWALL_EMAIL,
        help="Email for Unpaywall API (required by their TOS)",
    )
    parser.add_argument(
        "--use-browser",
        action="store_true",
        help="Use browser automation to bypass Cloudflare (requires selenium)",
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Use FIU university proxy (royalsocietypublishing-org.eu1.proxy.openathens.net)",
    )
    parser.add_argument(
        "--pause-for-login",
        action="store_true",
        help="Pause after starting browser to allow manual university login",
    )
    args = parser.parse_args()

    # Set global proxy flag
    global PROXY_ENABLED
    PROXY_ENABLED = args.proxy

    # Setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = setup_logging(timestamp)

    logger.info("=" * 70)
    logger.info("ROYAL SOCIETY PUBLISHING DOWNLOADER")
    logger.info("=" * 70)
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Database: {DATABASE}")
    logger.info(f"Output: {SHARKPAPERS}")
    logger.info(f"Unpaywall email: {args.email}")
    logger.info(f"Browser mode: {args.use_browser}")
    logger.info(f"Using FIU proxy: {args.proxy}")

    # Check database exists
    if not DATABASE.exists():
        logger.error(f"Database not found: {DATABASE}")
        return

    # Get pending papers
    papers = get_pending_papers()
    logger.info(f"Found {len(papers)} Royal Society papers pending download")

    if not papers:
        logger.info("No papers to download!")
        return

    # Apply test limit
    if args.test:
        papers = papers[: args.test]
        logger.info(f"Test mode: processing {len(papers)} papers")

    # Initialize browser if requested
    driver = None
    if args.use_browser:
        if not SELENIUM_AVAILABLE:
            logger.error(
                "Browser mode requested but selenium not installed. "
                "Install with: pip install selenium undetected-chromedriver"
            )
            return
        driver = setup_browser(SHARKPAPERS, logger)
        if driver is None:
            logger.warning("Browser setup failed, continuing without browser")
        elif args.pause_for_login:
            logger.info("=" * 60)
            logger.info("PAUSE FOR LOGIN")
            logger.info("=" * 60)
            logger.info("Please log in to your university library in the browser window.")
            if args.proxy:
                login_url = f"https://{PROXY_BASE}/"
                logger.info(f"Navigate to: {login_url}")
                logger.info("(This will redirect through your university authentication)")
            else:
                login_url = "https://royalsocietypublishing.org/"
                logger.info(f"Navigate to: {login_url}")
            driver.get(login_url)
            input("Press ENTER when you have logged in and are ready to continue...")
            logger.info("Continuing with downloads...")

    # Statistics
    stats = {"downloaded": 0, "failed": 0, "skipped": 0}

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"PROCESSING {len(papers)} PAPERS")
    logger.info("=" * 70)
    logger.info("")

    start_time = time.time()

    try:
        for i, paper in enumerate(papers, 1):
            download_paper(paper, args.email, logger, stats, driver)

            # Progress report every 10 papers
            if i % 10 == 0:
                logger.info(
                    f"Progress: {i}/{len(papers)} - "
                    f"{stats['downloaded']} OK, {stats['failed']} fail, "
                    f"{stats['skipped']} skip"
                )

            # Rate limiting
            time.sleep(DELAY_BETWEEN_REQUESTS)

    finally:
        # Clean up browser
        if driver is not None:
            try:
                driver.quit()
                logger.info("Browser closed")
            except Exception:
                pass

    # Summary
    elapsed = time.time() - start_time

    logger.info("")
    logger.info("=" * 70)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Papers processed: {len(papers)}")
    logger.info(f"Downloaded: {stats['downloaded']}")
    logger.info(f"Already existed: {stats['skipped']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Time elapsed: {elapsed / 60:.1f} minutes")

    if len(papers) > 0:
        success_rate = (stats["downloaded"] + stats["skipped"]) / len(papers) * 100
        logger.info(f"Success rate: {success_rate:.1f}%")

    logger.info(f"Output directory: {SHARKPAPERS}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
