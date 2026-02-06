#!/usr/bin/env python3
"""
download_authenticated.py

Unified script for downloading paywalled papers using institutional authentication.

This script:
1. Opens a visible browser window
2. Navigates to a publisher login page
3. Waits for you to complete FIU Shibboleth/SSO authentication
4. Downloads papers using your authenticated session

Supported Publishers:
- Oxford Academic (10.1093/%)
- Cambridge University Press (10.1017/%)
- Taylor & Francis (10.1080/%)
- Nature/Springer (10.1038/%)
- Wiley (10.1111/%, 10.1002/%)
- Royal Society (10.1098/%)
- Inter-Research (10.3354/%)
- Elsevier/ScienceDirect (10.1016/%)
- MDPI (10.3390/%) - Open Access but Cloudflare protected

Usage:
    # Download from all publishers with paywalled papers
    ./venv/bin/python scripts/download_authenticated.py

    # Download from specific publisher
    ./venv/bin/python scripts/download_authenticated.py --publisher oxford

    # Test mode (5 papers)
    ./venv/bin/python scripts/download_authenticated.py --test 5

    # Skip login prompt (if already authenticated in a previous session)
    ./venv/bin/python scripts/download_authenticated.py --skip-login

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
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

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
COOKIE_DIR = BASE_DIR / "browser_data"  # Persist cookies between sessions

# Current browser download directory (set by setup_browser, used by check_browser_downloads)
BROWSER_DOWNLOAD_DIR: Optional[Path] = None

# Publisher configurations
PUBLISHERS = {
    "oxford": {
        "name": "Oxford Academic",
        "doi_prefix": "10.1093/%",
        "login_url": "https://academic.oup.com/my-account/signin",
        "pdf_patterns": [
            "https://academic.oup.com/{journal}/article-pdf/{path}",
        ],
        "article_url": "https://doi.org/{doi}",
    },
    "cambridge": {
        "name": "Cambridge University Press",
        "doi_prefix": "10.1017/%",
        "login_url": "https://www.cambridge.org/core/login",
        "article_url": "https://doi.org/{doi}",
    },
    "taylor": {
        "name": "Taylor & Francis",
        "doi_prefix": "10.1080/%",
        "login_url": "https://www.tandfonline.com/action/ssostart",
        "article_url": "https://doi.org/{doi}",
    },
    "nature": {
        "name": "Nature/Springer",
        "doi_prefix": "10.1038/%",
        "login_url": "https://idp.nature.com/authorize",
        "article_url": "https://doi.org/{doi}",
    },
    "wiley": {
        "name": "Wiley",
        "doi_prefix": "10.1111/%",  # Also 10.1002/%
        "login_url": "https://onlinelibrary.wiley.com/action/ssostart",
        "article_url": "https://doi.org/{doi}",
    },
    "royal_society": {
        "name": "Royal Society",
        "doi_prefix": "10.1098/%",
        "login_url": "https://royalsocietypublishing.org/action/ssostart",
        "article_url": "https://doi.org/{doi}",
    },
    "inter_research": {
        "name": "Inter-Research",
        "doi_prefix": "10.3354/%",
        "login_url": "https://www.int-res.com/",  # May not support Shibboleth
        "article_url": "https://doi.org/{doi}",
    },
    "elsevier": {
        "name": "Elsevier/ScienceDirect",
        "doi_prefix": "10.1016/%",
        "login_url": "https://www.sciencedirect.com/user/login",
        "article_url": "https://doi.org/{doi}",
    },
    "mdpi": {
        "name": "MDPI",
        "doi_prefix": "10.3390/%",
        "login_url": "https://www.mdpi.com/",  # No login needed - just Cloudflare bypass
        "article_url": "https://doi.org/{doi}",
        "note": "Open Access but Cloudflare protected - manual challenge may be needed",
    },
}

# FIU-specific configuration
FIU_ENTITY_ID = "https://shibboleth.fiu.edu/idp/shibboleth"
FIU_LOGIN_KEYWORDS = ["fiu.edu", "florida international", "panther"]

# Request settings
DELAY_BETWEEN_PAPERS = 1.5  # Seconds between downloads
PAGE_LOAD_TIMEOUT = 30
DOWNLOAD_WAIT_TIMEOUT = 20


# ============================================================================
# HELPERS
# ============================================================================


def setup_logging(timestamp: str) -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"authenticated_download_{timestamp}.log"

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


def get_paywalled_papers(doi_prefix: str, limit: Optional[int] = None) -> list[tuple]:
    """
    Get papers marked as unavailable (paywalled) for a specific publisher.
    Excludes papers that have already been downloaded.

    Returns list of tuples: (id, doi, title, authors, year)
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    query = """
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        JOIN download_status ds ON p.id = ds.paper_id
        WHERE p.doi LIKE ?
        AND ds.status = 'unavailable'
        AND p.id NOT IN (
            SELECT paper_id FROM download_status WHERE status = 'downloaded'
        )
        ORDER BY p.year DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query, (doi_prefix,))
    papers = cur.fetchall()
    conn.close()
    return papers


def get_pending_papers(doi_prefix: str, limit: Optional[int] = None) -> list[tuple]:
    """
    Get papers that haven't been attempted yet for a specific publisher.

    Returns list of tuples: (id, doi, title, authors, year)
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    query = """
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        WHERE p.doi LIKE ?
        AND p.id NOT IN (SELECT paper_id FROM download_status)
        ORDER BY p.year DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query, (doi_prefix,))
    papers = cur.fetchall()
    conn.close()
    return papers


def get_all_unavailable_papers(limit: Optional[int] = None) -> list[tuple]:
    """
    Get all papers marked as unavailable across all publishers.

    Returns list of tuples: (id, doi, title, authors, year, publisher_key)
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Build query for all known publishers
    conditions = []
    for key, config in PUBLISHERS.items():
        prefix = config["doi_prefix"]
        conditions.append(f"(p.doi LIKE '{prefix}' AND '{key}' AS publisher)")

    # Simpler approach - get all unavailable and determine publisher later
    query = """
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.status = 'unavailable'
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


def get_mdpi_papers(limit: Optional[int] = None) -> list[tuple]:
    """
    Get MDPI papers that haven't been successfully downloaded.

    Only returns pending and failed papers (not 'unavailable' - those have been tried).
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    query = """
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE p.doi LIKE '10.3390/%'
        AND (ds.status IS NULL OR ds.status IN ('pending', 'failed'))
        ORDER BY p.year DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    papers = cur.fetchall()
    conn.close()
    return papers


def get_publisher_stats() -> dict:
    """Get count of papers needing download by publisher."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    stats = {}
    for key, config in PUBLISHERS.items():
        if key == "mdpi":
            # MDPI is OA - count all not-downloaded papers
            cur.execute("""
                SELECT COUNT(*) FROM papers p
                LEFT JOIN download_status ds ON p.id = ds.paper_id
                WHERE p.doi LIKE ?
                AND (ds.status IS NULL OR ds.status IN ('pending', 'failed', 'unavailable'))
            """, (config["doi_prefix"],))
        else:
            # Other publishers - count unavailable (paywalled)
            cur.execute("""
                SELECT COUNT(*) FROM papers p
                JOIN download_status ds ON p.id = ds.paper_id
                WHERE p.doi LIKE ? AND ds.status = 'unavailable'
            """, (config["doi_prefix"],))
        count = cur.fetchone()[0]
        if count > 0:
            stats[key] = {"name": config["name"], "count": count}

    conn.close()
    return stats


# ============================================================================
# BROWSER FUNCTIONS
# ============================================================================


def setup_browser(logger: logging.Logger, headless: bool = False, publisher_key: str = "default") -> Optional[uc.Chrome]:
    """
    Set up Chrome browser with persistent profile for cookie storage.

    Uses undetected_chromedriver to avoid bot detection.
    Uses a publisher-specific Chrome profile to allow parallel downloads.
    """
    try:
        # Use a publisher-specific profile directory to allow parallel downloads
        profile_dir = COOKIE_DIR / f"chrome_profile_{publisher_key}"
        profile_dir.mkdir(parents=True, exist_ok=True)

        options = uc.ChromeOptions()

        if headless:
            options.add_argument("--headless=new")

        # Use completely separate user data directory (avoids conflicts with main Chrome)
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument(f"--profile-directory=PaperDownloader_{publisher_key}")

        # Standard options
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1400,900")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Use a different remote debugging port to avoid conflicts
        options.add_argument("--remote-debugging-port=0")  # Auto-select available port

        # Create a publisher-specific temp download directory for browser
        temp_download_dir = COOKIE_DIR / f"downloads_{publisher_key}"
        temp_download_dir.mkdir(parents=True, exist_ok=True)

        # Download preferences - FORCE PDF download instead of viewing
        prefs = {
            # Download settings
            "download.default_directory": str(temp_download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,

            # PDF settings - force download, never view
            "plugins.always_open_pdf_externally": True,
            "plugins.always_open_pdf_internally": False,
            "plugins.plugins_disabled": ["Chrome PDF Viewer"],

            # Allow automatic downloads
            "profile.default_content_settings.popups": 0,
            "download.extensions_to_open": "",
            "profile.default_content_setting_values.automatic_downloads": 1,

            # Disable PDF plugin extension
            "plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}],
        }
        options.add_experimental_option("prefs", prefs)

        # Disable Chrome's PDF viewer completely via command line
        options.add_argument("--disable-pdf-viewer")

        logger.info("Starting Chrome with separate profile (won't conflict with your browser)...")
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

        # Set global download directory for check_browser_downloads function
        global BROWSER_DOWNLOAD_DIR
        BROWSER_DOWNLOAD_DIR = temp_download_dir

        logger.info("Browser initialized successfully")
        return driver

    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        logger.error("If Chrome is already running, try closing all Chrome windows first,")
        logger.error("or the script will use a separate profile that shouldn't conflict.")
        return None


def wait_for_login(driver: uc.Chrome, logger: logging.Logger, publisher_key: str) -> bool:
    """
    Navigate to publisher login and wait for user to complete FIU authentication.

    Returns True if login appears successful.
    """
    config = PUBLISHERS.get(publisher_key)
    if not config:
        logger.error(f"Unknown publisher: {publisher_key}")
        return False

    login_url = config["login_url"]
    publisher_name = config["name"]

    print("\n" + "=" * 70)
    print(f"INSTITUTIONAL LOGIN - {publisher_name}")
    print("=" * 70)
    print(f"\nA browser window will open to: {login_url}")
    print("\nPlease complete these steps:")
    print("  1. Look for 'Login via institution' or 'Access through your institution'")
    print("  2. Search for 'Florida International University' or 'FIU'")
    print("  3. Complete the FIU Shibboleth login (username + password + DUO)")
    print("  4. Wait until you see your account page or the main site")
    print("\nThe browser window will stay open - do NOT close it!")
    print("=" * 70)

    input("\nPress Enter to open the browser...")

    try:
        logger.info(f"Navigating to login: {login_url}")
        driver.get(login_url)

        print("\n>>> Complete the login in the browser window <<<")
        print(">>> When done, come back here and press Enter <<<\n")

        input("Press Enter when login is complete...")

        # Check if we're logged in by looking for common indicators
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()

        # Signs of successful login
        logged_in_indicators = [
            "sign out", "log out", "logout", "my account",
            "my profile", "welcome", "signed in"
        ]

        for indicator in logged_in_indicators:
            if indicator in page_source:
                logger.info(f"Login appears successful (found: '{indicator}')")
                return True

        # If redirected away from login page, probably successful
        if "login" not in current_url and "signin" not in current_url:
            logger.info("Login appears successful (redirected from login page)")
            return True

        logger.warning("Could not confirm login status - proceeding anyway")
        return True  # Proceed anyway, user confirmed

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return False


def download_paper_authenticated(
    driver: uc.Chrome,
    paper: tuple,
    logger: logging.Logger,
    stats: dict,
    temp_dir: Path,
) -> bool:
    """
    Download a paper using the authenticated browser session.

    Strategy:
    1. Navigate to DOI URL (resolves to publisher page)
    2. Look for PDF download link
    3. Download PDF
    4. Verify and save
    """
    paper_id, doi, title, authors, year = paper

    # Determine output path
    year_val = int(year) if year else 0
    year_dir = SHARKPAPERS / str(year_val) if year_val else SHARKPAPERS / "unknown_year"
    year_dir.mkdir(parents=True, exist_ok=True)

    filename = generate_filename(authors, title, year_val)
    output_path = year_dir / filename

    # Check if already exists (exact filename)
    if output_path.exists() and output_path.stat().st_size > 10240:
        logger.info(f"  EXISTS: {filename}")
        update_status(paper_id, "downloaded", "authenticated-exists")
        stats["existed"] += 1
        return True

    # Also check for similar files (in case filename generation changed)
    title_prefix = (title or "")[:20].lower()
    for existing_pdf in year_dir.glob("*.pdf"):
        if title_prefix and title_prefix in existing_pdf.name.lower():
            if existing_pdf.stat().st_size > 10240:
                logger.info(f"  EXISTS (similar): {existing_pdf.name[:60]}")
                update_status(paper_id, "downloaded", "authenticated-exists-similar")
                stats["existed"] += 1
                return True

    logger.info(f"  Downloading: {doi}")
    logger.info(f"    Title: {title[:60]}...")

    # Clear temp directory AND browser download directory
    for f in temp_dir.glob("*.pdf"):
        try:
            f.unlink()
        except:
            pass
    clear_browser_downloads(logger)  # Clear browser's download folder too
    for f in temp_dir.glob("*.crdownload"):
        try:
            f.unlink()
        except:
            pass

    # Set download directory
    try:
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(temp_dir),
        })
    except:
        pass  # May fail in some Chrome versions

    try:
        # Navigate to DOI
        doi_url = f"https://doi.org/{doi}"
        driver.get(doi_url)
        time.sleep(3)

        # Get current URL after redirect
        current_url = driver.current_url
        logger.debug(f"    Landed on: {current_url}")

        # Try to find and click PDF download link
        pdf_downloaded = False

        # FIRST: Check if Chrome auto-downloaded a PDF (happens with new prefs)
        if check_browser_downloads(output_path, logger, timeout=3):
            logger.info(f"  SUCCESS: PDF auto-downloaded for {doi}")
            update_status(paper_id, "downloaded", "authenticated")
            stats["downloaded"] += 1
            close_extra_tabs(driver, logger)
            return True

        # SECOND: Check if we landed on a PDF URL directly
        if check_page_is_pdf(driver, temp_dir, output_path, logger):
            logger.info(f"  SUCCESS: Direct PDF URL for {doi}")
            update_status(paper_id, "downloaded", "authenticated")
            stats["downloaded"] += 1
            close_extra_tabs(driver, logger)
            return True

        # Common PDF link patterns
        pdf_selectors = [
            # Oxford Academic - cr-icon-button download (from dev tools inspection)
            "cr-icon-button#download",          # The actual OUP download button!
            "cr-icon-button[title='Download']", # By title
            "#download",                        # By ID
            "[title='Download']",               # Any element with Download title
            # Oxford Academic - other patterns
            "a.al-link.pdf",                    # Common OUP PDF link class
            "a[class*='pdf'][class*='link']",   # PDF link variations
            "a.article-pdfLink",                # Article PDF link
            "a[href*='/article-pdf/']",         # Direct PDF URL
            "a[data-track-action='download pdf']",
            "a[title*='PDF']",                  # Title containing PDF
            "a[aria-label*='PDF']",             # Aria label containing PDF
            "button[class*='pdf']",             # PDF buttons
            # Cambridge
            "a[href*='/core/services/aop-cambridge-core/content/view']",
            "a.pdf-link",
            # Taylor & Francis
            "a[href*='/doi/pdf/']",
            "a[href*='pdf'][class*='download']",
            # Nature/Springer
            "a[data-track-action='download pdf']",
            "a[href*='.pdf']",
            # Wiley
            "a[href*='/epdf/']",
            "a[href*='/pdfdirect/']",
            # Royal Society
            "a[href*='/doi/pdf/']",
            "a[href*='/doi/epdf/']",
            # MDPI
            "a.download-pdf",
            "a[href*='/pdf/']",
            "a.UD_ArticlePDF",
            # Generic
            "a[href$='.pdf']",
            "a[title*='PDF']",
            "a[aria-label*='PDF']",
            "button[data-track*='pdf']",
        ]

        # First, try text-based search for "PDF" or "View PDF" links (OUP style)
        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for elem in all_links:
                text = (elem.text or "").strip().upper()
                if text in ["PDF", "VIEW PDF", "GET PDF", "DOWNLOAD PDF"]:
                    href = elem.get_attribute("href")
                    logger.info(f"    Found PDF text link: {text} -> {href[:60] if href else 'click'}...")
                    try:
                        elem.click()
                        time.sleep(3)
                        close_extra_tabs(driver, logger)  # Clean up tabs after each click
                        pdf_downloaded = wait_for_download(temp_dir, logger)
                        if not pdf_downloaded:
                            pdf_downloaded = check_browser_downloads(output_path, logger, timeout=5)
                        if not pdf_downloaded:
                            pdf_downloaded = check_page_is_pdf(driver, temp_dir, output_path, logger)
                        if pdf_downloaded:
                            break
                    except:
                        if href:
                            driver.get(href)
                            time.sleep(3)
                            close_extra_tabs(driver, logger)  # Clean up tabs after navigation
                            pdf_downloaded = wait_for_download(temp_dir, logger)
                            if not pdf_downloaded:
                                pdf_downloaded = check_browser_downloads(output_path, logger, timeout=5)
                            if not pdf_downloaded:
                                pdf_downloaded = check_page_is_pdf(driver, temp_dir, output_path, logger)
                            if pdf_downloaded:
                                break
        except Exception as e:
            logger.debug(f"    Text-based PDF search failed: {e}")

        # Then try CSS selectors
        if not pdf_downloaded:
            for selector in pdf_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        href = elem.get_attribute("href")
                        tag = elem.tag_name.lower()
                        title = elem.get_attribute("title") or ""

                        # For cr-icon-button or buttons with Download title, just click
                        if tag in ["cr-icon-button", "button"] or "download" in title.lower():
                            logger.info(f"    Found download button: {tag} title='{title}'")
                            try:
                                elem.click()
                                time.sleep(3)
                                close_extra_tabs(driver, logger)  # Clean up tabs after click
                                # Check temp dir OR browser auto-download
                                pdf_downloaded = wait_for_download(temp_dir, logger)
                                if not pdf_downloaded:
                                    pdf_downloaded = check_browser_downloads(output_path, logger, timeout=5)
                                if pdf_downloaded:
                                    break
                            except Exception as click_err:
                                logger.debug(f"    Click failed: {click_err}")
                                close_extra_tabs(driver, logger)
                                continue
                        # For links with PDF in href
                        elif href and "pdf" in href.lower():
                            logger.debug(f"    Found PDF link: {href[:80]}...")
                            try:
                                elem.click()
                                time.sleep(2)
                                close_extra_tabs(driver, logger)  # Clean up tabs after click
                            except:
                                driver.get(href)
                                time.sleep(2)
                                close_extra_tabs(driver, logger)  # Clean up tabs after navigation
                            # Check temp dir OR browser auto-download
                            pdf_downloaded = wait_for_download(temp_dir, logger)
                            if not pdf_downloaded:
                                pdf_downloaded = check_browser_downloads(output_path, logger, timeout=5)
                            # Also try direct download from PDF URL
                            if not pdf_downloaded:
                                pdf_downloaded = check_page_is_pdf(driver, temp_dir, output_path, logger)
                            if pdf_downloaded:
                                break

                except Exception as e:
                    continue

                if pdf_downloaded:
                    break

        # If no PDF link found, try constructing PDF URL directly
        if not pdf_downloaded:
            # Try common PDF URL patterns based on current URL
            pdf_attempts = []

            if "academic.oup.com" in current_url:
                # Oxford: Look for PDF link in page source instead of URL manipulation
                # Oxford PDF URLs are complex and embedded in the page
                # Try to find the PDF URL from page elements
                try:
                    pdf_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='article-pdf']")
                    for elem in pdf_elements:
                        href = elem.get_attribute("href")
                        if href and "article-pdf" in href:
                            pdf_attempts.append(href)
                            break
                except:
                    pass
                # Fallback: try DOI-based URL pattern
                if "/article/" in current_url:
                    # Extract parts and construct PDF URL
                    pdf_url = current_url.replace("/article/", "/article-pdf/")
                    pdf_attempts.append(pdf_url)

            elif "cambridge.org" in current_url:
                # Cambridge: various patterns
                if "/article/" in current_url:
                    pdf_url = current_url.replace("/article/", "/article/pdf/")
                    pdf_attempts.append(pdf_url)

            elif "tandfonline.com" in current_url:
                # T&F: /doi/full/ -> /doi/pdf/
                pdf_url = current_url.replace("/doi/full/", "/doi/pdf/")
                pdf_url = pdf_url.replace("/doi/abs/", "/doi/pdf/")
                pdf_attempts.append(pdf_url)

            elif "nature.com" in current_url:
                # Nature: /articles/ -> /articles/.pdf
                if not current_url.endswith(".pdf"):
                    pdf_attempts.append(current_url + ".pdf")

            elif "royalsocietypublishing.org" in current_url:
                # Royal Society
                pdf_url = current_url.replace("/doi/full/", "/doi/pdf/")
                pdf_url = pdf_url.replace("/doi/abs/", "/doi/pdf/")
                pdf_attempts.append(pdf_url)

            elif "mdpi.com" in current_url:
                # MDPI: https://www.mdpi.com/JOURNAL/VOLUME/ISSUE/ARTICLE/pdf
                if "/htm" in current_url:
                    pdf_url = current_url.replace("/htm", "/pdf")
                    pdf_attempts.append(pdf_url)
                else:
                    pdf_attempts.append(current_url + "/pdf")

            for pdf_url in pdf_attempts:
                try:
                    logger.debug(f"    Trying constructed URL: {pdf_url[:80]}...")
                    driver.get(pdf_url)
                    time.sleep(3)

                    pdf_downloaded = wait_for_download(temp_dir, logger)
                    if pdf_downloaded:
                        break

                    # Check if page itself is a PDF
                    if check_page_is_pdf(driver, temp_dir, output_path, logger):
                        pdf_downloaded = True
                        break

                except Exception as e:
                    logger.debug(f"    URL attempt failed: {e}")
                    continue

        # Process downloaded file
        if pdf_downloaded:
            # Find the downloaded file
            pdf_files = list(temp_dir.glob("*.pdf"))
            if pdf_files:
                downloaded_file = pdf_files[0]
                file_size = downloaded_file.stat().st_size

                if file_size > 10240:  # At least 10KB
                    # Verify it's a real PDF
                    with open(downloaded_file, "rb") as f:
                        if f.read(4) == b"%PDF":
                            # Move to final location
                            downloaded_file.rename(output_path)
                            logger.info(f"    OK: {filename} ({file_size:,} bytes)")
                            update_status(paper_id, "downloaded", "authenticated")
                            stats["downloaded"] += 1
                            close_extra_tabs(driver, logger)
                            return True

                # Invalid PDF
                downloaded_file.unlink()

        # Clean up extra tabs before moving to next paper
        close_extra_tabs(driver, logger)

        # Failed
        logger.warning(f"    FAIL: Could not download PDF")
        update_status(paper_id, "unavailable", "authenticated-failed", "No PDF found with auth")
        stats["failed"] += 1
        return False

    except TimeoutException:
        logger.warning(f"    FAIL: Page load timeout")
        close_extra_tabs(driver, logger)
        stats["failed"] += 1
        return False
    except Exception as e:
        logger.error(f"    FAIL: {e}")
        close_extra_tabs(driver, logger)
        stats["failed"] += 1
        return False


def wait_for_download(temp_dir: Path, logger: logging.Logger, timeout: int = DOWNLOAD_WAIT_TIMEOUT) -> bool:
    """Wait for a PDF file to appear in temp directory."""
    start = time.time()

    while time.time() - start < timeout:
        pdf_files = list(temp_dir.glob("*.pdf"))
        partial_files = list(temp_dir.glob("*.crdownload"))

        if pdf_files and not partial_files:
            # Download complete
            return True

        if partial_files:
            # Download in progress
            time.sleep(1)
            continue

        time.sleep(0.5)

    return False


def check_page_is_pdf(driver: uc.Chrome, temp_dir: Path, output_path: Path, logger: logging.Logger) -> bool:
    """Check if current page is a PDF and save it if so."""
    import requests

    try:
        current_url = driver.current_url

        # Check if URL looks like a PDF
        if ".pdf" in current_url.lower() or "article-pdf" in current_url.lower():
            logger.info(f"    PDF URL detected: {current_url[:60]}...")

            # Get cookies from browser session
            cookies = {c["name"]: c["value"] for c in driver.get_cookies()}

            # Download using requests with browser cookies
            response = requests.get(
                current_url,
                cookies=cookies,
                headers={
                    "User-Agent": driver.execute_script("return navigator.userAgent;"),
                    "Accept": "application/pdf,*/*",
                    "Referer": current_url,
                },
                timeout=60,
                allow_redirects=True,
            )

            if response.status_code == 200 and response.content[:4] == b"%PDF":
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"    Downloaded via direct URL: {len(response.content):,} bytes")
                return True
            else:
                logger.debug(f"    Direct download failed: HTTP {response.status_code}")

        # Also check content type via JavaScript
        content_type = driver.execute_script(
            "return document.contentType || document.querySelector('embed')?.type || '';"
        )

        if "pdf" in content_type.lower():
            cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
            response = requests.get(
                current_url,
                cookies=cookies,
                headers={"User-Agent": driver.execute_script("return navigator.userAgent;")},
                timeout=60,
            )

            if response.status_code == 200 and response.content[:4] == b"%PDF":
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True

    except Exception as e:
        logger.debug(f"PDF check failed: {e}")

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
        # Check for .crdownload files (download in progress)
        partial_files = list(browser_download_dir.glob("*.crdownload"))
        if partial_files:
            time.sleep(0.5)
            continue

        # Look for PDF files
        pdf_files = sorted(browser_download_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if pdf_files:
            newest_pdf = pdf_files[0]
            # Check if it's a valid PDF
            with open(newest_pdf, "rb") as f:
                if f.read(4) == b"%PDF":
                    # Move to final destination
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(newest_pdf), str(output_path))
                    logger.info(f"    Auto-downloaded PDF moved to: {output_path.name}")
                    return True
            # Not a valid PDF
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


def close_extra_tabs(driver: uc.Chrome, logger: logging.Logger) -> None:
    """Close all tabs except the first one to prevent tab accumulation."""
    try:
        handles = driver.window_handles
        if len(handles) > 1:
            # Keep the first tab, close all others
            main_handle = handles[0]
            for handle in handles[1:]:
                try:
                    driver.switch_to.window(handle)
                    driver.close()
                except Exception:
                    pass
            # Switch back to main tab
            driver.switch_to.window(main_handle)
            logger.debug(f"Closed {len(handles) - 1} extra tab(s)")
    except Exception as e:
        logger.debug(f"Tab cleanup error: {e}")


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Download paywalled papers using FIU institutional authentication"
    )
    parser.add_argument(
        "--publisher",
        type=str,
        choices=list(PUBLISHERS.keys()),
        help="Download from specific publisher only",
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
        "--include-pending",
        action="store_true",
        help="Also try papers that haven't been attempted yet",
    )
    args = parser.parse_args()

    # Warn about headless mode
    if args.headless and not args.skip_login:
        print("WARNING: Headless mode requires --skip-login (can't do interactive login)")
        print("         Use visible mode for initial login, then headless with --skip-login")
        return

    # Setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = setup_logging(timestamp)

    logger.info("=" * 70)
    logger.info("AUTHENTICATED PAPER DOWNLOADER")
    logger.info("=" * 70)
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Institution: Florida International University")
    logger.info(f"Database: {DATABASE}")
    logger.info(f"Output: {SHARKPAPERS}")

    # Show available papers
    print("\n" + "=" * 70)
    print("PAYWALLED PAPERS BY PUBLISHER")
    print("=" * 70)

    stats_by_publisher = get_publisher_stats()
    total_available = 0

    for key, info in sorted(stats_by_publisher.items(), key=lambda x: -x[1]["count"]):
        print(f"  {info['name']}: {info['count']} papers")
        total_available += info["count"]

    print(f"\n  TOTAL: {total_available} paywalled papers potentially accessible")
    print("=" * 70)

    if total_available == 0:
        logger.info("No paywalled papers to download!")
        return

    # Determine which publishers to process
    if args.publisher:
        publishers_to_process = [args.publisher]
    else:
        # Process all publishers with paywalled papers
        publishers_to_process = list(stats_by_publisher.keys())

    # Initialize browser (use first publisher key for profile name)
    first_publisher = publishers_to_process[0] if publishers_to_process else "default"
    logger.info("\nInitializing browser...")
    driver = setup_browser(logger, headless=args.headless, publisher_key=first_publisher)

    if driver is None:
        logger.error("Failed to initialize browser")
        return

    # Create temp directory for downloads
    temp_dir = SHARKPAPERS / ".temp_authenticated"
    temp_dir.mkdir(exist_ok=True)

    # Statistics
    stats = {"downloaded": 0, "failed": 0, "existed": 0}

    try:
        # Process each publisher
        for pub_key in publishers_to_process:
            config = PUBLISHERS[pub_key]
            pub_name = config["name"]
            doi_prefix = config["doi_prefix"]

            # Get papers for this publisher
            if pub_key == "mdpi":
                # MDPI is Open Access - get all undownloaded papers
                papers = get_mdpi_papers(limit=args.test)
            else:
                papers = get_paywalled_papers(doi_prefix, limit=args.test)

                if args.include_pending:
                    pending = get_pending_papers(doi_prefix, limit=args.test)
                    papers.extend(pending)

            if not papers:
                logger.info(f"\nNo papers to download from {pub_name}")
                continue

            logger.info(f"\n{'=' * 70}")
            logger.info(f"PROCESSING {pub_name}: {len(papers)} papers")
            logger.info(f"{'=' * 70}")

            # Handle login/Cloudflare based on publisher
            if pub_key == "mdpi":
                # MDPI doesn't need login - just Cloudflare bypass
                if not args.skip_login:
                    print("\n" + "=" * 70)
                    print("MDPI - CLOUDFLARE BYPASS")
                    print("=" * 70)
                    print("\nMDPI is Open Access but protected by Cloudflare.")
                    print("The browser will navigate to MDPI - you may need to")
                    print("complete a Cloudflare challenge (checkbox/puzzle).")
                    print("\nAfter the MDPI page loads, press Enter to continue.")
                    print("=" * 70)
                    input("\nPress Enter to open MDPI...")

                    try:
                        driver.get("https://www.mdpi.com/")
                        time.sleep(3)
                        input("Complete any Cloudflare challenge, then press Enter...")
                    except Exception as e:
                        logger.warning(f"Error loading MDPI: {e}")
            elif not args.skip_login:
                # Standard publisher login
                success = wait_for_login(driver, logger, pub_key)
                if not success:
                    logger.warning(f"Login may have failed for {pub_name}, but proceeding...")

            # Download papers
            for i, paper in enumerate(papers, 1):
                logger.info(f"\n[{i}/{len(papers)}] Processing paper...")

                download_paper_authenticated(driver, paper, logger, stats, temp_dir)

                # Rate limiting
                time.sleep(DELAY_BETWEEN_PAPERS)

                # Progress report
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(papers)} - {stats['downloaded']} OK, {stats['failed']} fail")

            # Ask about next publisher
            if len(publishers_to_process) > 1 and pub_key != publishers_to_process[-1]:
                print(f"\nCompleted {pub_name}. Continue to next publisher?")
                response = input("Press Enter to continue, or 'q' to quit: ")
                if response.lower() == 'q':
                    break

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

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Downloaded: {stats['downloaded']}")
    logger.info(f"Already existed: {stats['existed']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Output: {SHARKPAPERS}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
