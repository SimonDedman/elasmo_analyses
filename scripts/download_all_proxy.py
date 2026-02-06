#!/usr/bin/env python3
"""
download_all_proxy.py

Unified batch downloader for all publishers requiring university proxy authentication.
Downloads papers from multiple publishers in a single browser session.

Publishers handled (in order):
1. Taylor & Francis (10.1080) - 99 papers
2. Royal Society (10.1098) - 88 papers
3. JEB/Company of Biologists (10.1242) - 57 papers
4. Cambridge University Press (10.1017) - 43 papers
5. Nature (10.1038) - 3 papers
6. Oxford Academic (10.1093) - 1 paper

Usage:
    ./venv/bin/python scripts/download_all_proxy.py
    ./venv/bin/python scripts/download_all_proxy.py --test 5
    ./venv/bin/python scripts/download_all_proxy.py --skip-to jeb

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
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

import requests

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

REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 3.0
DELAY_BETWEEN_PUBLISHERS = 5.0

UNPAYWALL_EMAIL = "simondedman@gmail.com"
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Persistent Chrome profile directory (avoids 2FA each time)
CHROME_PROFILE_DIR = Path.home() / ".config" / "chrome-proxy-downloads"

# Publisher configurations
PUBLISHERS = {
    'inter_research': {
        'name': 'Inter-Research',
        'doi_prefix': '10.3354/%',
        'original_base': 'www.int-res.com',
        'proxy_base': 'www-int--res-com.eu1.proxy.openathens.net',
    },
    'taylor_francis': {
        'name': 'Taylor & Francis',
        'doi_prefix': '10.1080/%',
        'original_base': 'www.tandfonline.com',
        'proxy_base': 'www-tandfonline-com.eu1.proxy.openathens.net',
    },
    'royal_society': {
        'name': 'Royal Society',
        'doi_prefix': '10.1098/%',
        'original_base': 'royalsocietypublishing.org',
        'proxy_base': 'royalsocietypublishing-org.eu1.proxy.openathens.net',
    },
    'jeb': {
        'name': 'JEB/Company of Biologists',
        'doi_prefix': '10.1242/%',
        'original_base': 'journals.biologists.com',
        'proxy_base': 'journals-biologists-com.eu1.proxy.openathens.net',
    },
    'cambridge': {
        'name': 'Cambridge University Press',
        'doi_prefix': '10.1017/%',
        'original_base': 'www.cambridge.org',
        'proxy_base': 'www-cambridge-org.eu1.proxy.openathens.net',
    },
    'nature': {
        'name': 'Nature',
        'doi_prefix': '10.1038/%',
        'original_base': 'www.nature.com',
        'proxy_base': 'www-nature-com.eu1.proxy.openathens.net',
    },
    'oxford': {
        'name': 'Oxford Academic',
        'doi_prefix': '10.1093/%',
        'original_base': 'academic.oup.com',
        'proxy_base': 'academic-oup-com.eu1.proxy.openathens.net',
    },
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Paper:
    id: int
    doi: str
    title: str
    authors: str
    year: int


@dataclass
class PublisherStats:
    downloaded: int = 0
    existed: int = 0
    failed: int = 0
    unavailable: int = 0


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"batch_proxy_{timestamp}.log"

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
    if not title:
        return "Untitled"
    cleaned = unicodedata.normalize('NFKD', title)
    cleaned = re.sub(r'[<>:"/\\|?*\[\]{}();,]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
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
    if not authors:
        return "Unknown"
    first = authors
    for sep in [';', ' and ', '&', ',']:
        if sep in first:
            first = first.split(sep)[0].strip()
            break
    if ',' in first:
        first = first.split(',')[0].strip()
    parts = first.split()
    if parts:
        return parts[-1] if len(parts) > 1 else parts[0]
    return "Unknown"


def has_multiple_authors(authors: str) -> bool:
    if not authors:
        return False
    return any(ind in str(authors) for ind in [",", ";", " and ", "&"])


def generate_filename(authors: str, title: str, year: int) -> str:
    author = get_first_author(authors)
    author = re.sub(r'[^a-zA-Z\-]', '', author)
    clean_t = clean_title(title)
    if has_multiple_authors(authors):
        return f"{author}.etal.{int(year)}.{clean_t}.pdf"
    return f"{author}.{int(year)}.{clean_t}.pdf"


def to_proxy_url(url: str, publisher_config: dict) -> str:
    """Convert publisher URL to proxy URL."""
    if url:
        return url.replace(
            publisher_config['original_base'],
            publisher_config['proxy_base']
        ).replace("http://", "https://")
    return url


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_pending_papers(doi_prefix: str, retry_unavailable: bool = False, retry_failed: bool = False) -> List[Paper]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Build list of statuses to exclude
    exclude_statuses = ['downloaded']
    if not retry_unavailable:
        exclude_statuses.append('unavailable')
    if not retry_failed:
        exclude_statuses.append('failed')

    placeholders = ','.join('?' * len(exclude_statuses))

    cur.execute(f"""
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        WHERE p.doi LIKE ?
        AND p.id NOT IN (
            SELECT paper_id FROM download_status WHERE status IN ({placeholders})
        )
        ORDER BY p.year DESC
    """, (doi_prefix, *exclude_statuses))

    papers = [Paper(*row) for row in cur.fetchall()]
    conn.close()
    return papers


def mark_downloaded(paper_id: int, filename: str, source: str) -> None:
    conn = sqlite3.connect(DB_PATH)
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


def mark_unavailable(paper_id: int, reason: str, source: str) -> None:
    conn = sqlite3.connect(DB_PATH)
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


def mark_failed(paper_id: int, error: str, source: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, attempts FROM download_status WHERE paper_id = ?", (paper_id,))
    existing = cur.fetchone()
    if existing:
        attempts = (existing[1] or 0) + 1
        cur.execute("""
            UPDATE download_status
            SET status = 'failed', source = ?, last_attempt = datetime('now'), notes = ?, attempts = ?
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

def query_unpaywall(doi: str, logger: logging.Logger) -> dict:
    url = f"{UNPAYWALL_BASE_URL}/{doi}"
    params = {'email': UNPAYWALL_EMAIL}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=30, headers={'User-Agent': USER_AGENT})
            if response.status_code == 200:
                data = response.json()
                result = {'is_oa': data.get('is_oa', False), 'oa_status': data.get('oa_status', 'unknown'), 'pdf_url': None}
                if data.get('is_oa'):
                    best_oa = data.get('best_oa_location', {})
                    result['pdf_url'] = best_oa.get('url_for_pdf') or best_oa.get('url')
                return result
            elif response.status_code == 404:
                return {'is_oa': False, 'oa_status': 'not_found', 'pdf_url': None}
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.debug(f"Unpaywall error: {e}")
            time.sleep(2 ** attempt)
    return {'is_oa': False, 'oa_status': 'failed', 'pdf_url': None}


# ============================================================================
# PDF DOWNLOAD
# ============================================================================

def download_pdf_direct(url: str, logger: logging.Logger, session: Optional[requests.Session] = None) -> Tuple[bool, Optional[bytes], str]:
    if session is None:
        session = requests.Session()
    headers = {'User-Agent': USER_AGENT, 'Accept': 'application/pdf,*/*'}

    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True, stream=True)
            if response.status_code == 200:
                content = b''.join(response.iter_content(chunk_size=8192))
                content_type = response.headers.get('Content-Type', '').lower()
                if 'pdf' in content_type or (len(content) > 1000 and content[:4] == b'%PDF'):
                    return True, content, "Success"
                return False, None, f"Not PDF: {content_type[:50]}"
            elif response.status_code in [403, 401]:
                return False, None, f"Access denied ({response.status_code})"
            elif response.status_code == 404:
                return False, None, "Not found (404)"
            time.sleep(2 ** attempt)
        except requests.exceptions.Timeout:
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.debug(f"Download error: {e}")
            time.sleep(2 ** attempt)
    return False, None, "Failed after retries"


# ============================================================================
# SELENIUM BROWSER
# ============================================================================

def setup_browser(headless: bool = False) -> 'uc.Chrome':
    if not SELENIUM_AVAILABLE:
        raise RuntimeError("Selenium not available")

    # Create persistent profile directory
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    options = uc.ChromeOptions()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    # Use persistent profile to remember device/session (avoids 2FA each time)
    options.add_argument(f'--user-data-dir={CHROME_PROFILE_DIR}')

    return uc.Chrome(options=options, use_subprocess=True)


def get_pdf_via_browser(
    driver: 'uc.Chrome',
    paper: Paper,
    publisher_config: dict,
    logger: logging.Logger
) -> Tuple[bool, Optional[bytes], str]:
    """Navigate to paper and download PDF via browser."""

    # Navigate directly to proxy URL for the DOI
    # This ensures we stay in the authenticated proxy session
    proxy_doi_url = f"https://{publisher_config['proxy_base']}/doi/{paper.doi}"

    # For Oxford, the proxy URL pattern is different
    if 'oup' in publisher_config['proxy_base']:
        # Oxford uses DOI directly in article URLs
        proxy_doi_url = f"https://doi.org/{paper.doi}"

    try:
        driver.get(proxy_doi_url)
        time.sleep(4)  # Longer wait for proxy redirect

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        current_url = driver.current_url
        logger.debug(f"Current URL: {current_url}")

        # If we're on the original (non-proxy) site, redirect to proxy
        if publisher_config['original_base'] in current_url:
            proxy_url = to_proxy_url(current_url, publisher_config)
            logger.debug(f"Converting to proxy: {proxy_url}")
            driver.get(proxy_url)
            time.sleep(4)
            current_url = driver.current_url

        # Find PDF link - try multiple strategies
        pdf_url = None
        pdf_element = None

        # For some publishers, we know the exact PDF URL pattern - use it first
        # This avoids following wrong links on the page
        known_pattern_publishers = ['inter_research', 'taylor_francis', 'royal_society', 'jeb', 'oxford']
        publisher_key_detected = None
        for key, config in PUBLISHERS.items():
            if config['proxy_base'] in current_url or config['original_base'] in current_url:
                publisher_key_detected = key
                break

        if publisher_key_detected in known_pattern_publishers:
            pdf_url = construct_pdf_url(current_url, paper.doi, publisher_config)
            if pdf_url:
                logger.debug(f"Using known pattern URL: {pdf_url}")

        # Method 1: Look for PDF download links (most common selectors)
        # Only do this if we don't already have a URL from known patterns
        # IMPORTANT: Only accept links that match the current publisher's domain
        valid_domains = [
            publisher_config['proxy_base'],
            publisher_config['original_base'],
        ]

        pdf_selectors = [
            "//a[contains(@href, '.pdf')]",
            "//a[contains(@href, '/pdf/')]",
            "//a[contains(@href, 'article-pdf')]",
            "//a[contains(@href, '/doi/pdf/')]",
            "//a[contains(@class, 'pdf')]",
            "//a[contains(@class, 'PDF')]",
            "//a[contains(text(), 'PDF')]",
            "//a[contains(text(), 'Download PDF')]",
            "//a[contains(text(), 'Full Text PDF')]",
            "//a[@data-track-action='download pdf']",
            "//a[contains(@aria-label, 'PDF')]",
            "//button[contains(text(), 'PDF')]",
            "//a[contains(@class, 'al-link') and contains(@href, 'pdf')]",
        ]

        # Only search for links if we don't already have a constructed URL
        if not pdf_url:
            for selector in pdf_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        href = elem.get_attribute('href')
                        if not href:
                            continue
                        # CRITICAL: Only accept links from the same publisher domain
                        # This prevents following cross-publisher links that break the session
                        href_lower = href.lower()
                        is_valid_domain = any(domain in href_lower for domain in valid_domains)
                        is_relative = href.startswith('/') and not href.startswith('//')

                        if (is_valid_domain or is_relative) and ('pdf' in href_lower or (elem.text and 'PDF' in elem.text.upper())):
                            pdf_url = href
                            pdf_element = elem
                            logger.debug(f"Found PDF link via selector: {selector} -> {href[:80]}")
                            break
                    if pdf_url:
                        break
                except Exception:
                    continue

        # Method 2: Construct PDF URL based on publisher patterns (fallback)
        if not pdf_url:
            pdf_url = construct_pdf_url(current_url, paper.doi, publisher_config)
            if pdf_url:
                logger.debug(f"Constructed PDF URL: {pdf_url}")

        if not pdf_url:
            return False, None, "No PDF link found on page"

        # Ensure the PDF URL uses the proxy
        if publisher_config['original_base'] in pdf_url:
            pdf_url = to_proxy_url(pdf_url, publisher_config)

        logger.debug(f"Final PDF URL: {pdf_url}")

        # Try clicking the PDF link element directly (if we found one)
        # This preserves the session better than navigating
        if pdf_element:
            try:
                # Scroll element into view and click
                driver.execute_script("arguments[0].scrollIntoView(true);", pdf_element)
                time.sleep(1)
                pdf_element.click()
                time.sleep(3)

                # Check if we're now on a PDF page
                new_url = driver.current_url
                if '.pdf' in new_url.lower() or 'article-pdf' in new_url.lower():
                    pdf_url = new_url
                    logger.debug(f"Clicked to PDF, new URL: {pdf_url}")
            except Exception as e:
                logger.debug(f"Click failed, will navigate: {e}")
                # Navigate directly
                driver.get(pdf_url)
                time.sleep(3)
        else:
            # Navigate to PDF URL
            driver.get(pdf_url)
            time.sleep(3)

        # Wait for PDF to potentially load
        time.sleep(2)
        final_url = driver.current_url

        # Check if page shows "no access" or similar
        page_source = driver.page_source.lower()
        if any(x in page_source for x in ['access denied', 'no access', 'please login', 'sign in required']):
            return False, None, "Access denied - may need to reauthenticate"

        # Get cookies for requests download
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        # Add browser headers
        session.headers.update({
            'User-Agent': driver.execute_script("return navigator.userAgent"),
            'Referer': current_url,
            'Accept': 'application/pdf,*/*',
        })

        # Try to download the PDF
        success, content, msg = download_pdf_direct(final_url, logger, session)

        # If that failed, try the original pdf_url
        if not success and final_url != pdf_url:
            logger.debug(f"Retrying with original URL: {pdf_url}")
            success, content, msg = download_pdf_direct(pdf_url, logger, session)

        return success, content, msg

    except TimeoutException:
        return False, None, "Page timeout"
    except Exception as e:
        return False, None, f"Error: {str(e)[:50]}"


def construct_pdf_url(current_url: str, doi: str, publisher_config: dict) -> Optional[str]:
    """Construct PDF URL based on publisher-specific patterns."""

    publisher_key = None
    for key, config in PUBLISHERS.items():
        if config['original_base'] in current_url or config['proxy_base'] in current_url:
            publisher_key = key
            break

    if not publisher_key:
        return None

    # Publisher-specific URL construction
    if publisher_key == 'inter_research':
        # Inter-Research: DOI 10.3354/meps12345 -> /articles/meps/12345.pdf
        # Extract journal code and article number from DOI
        doi_suffix = doi.replace('10.3354/', '')
        # Split into journal code and number
        import re
        match = re.match(r'([a-z]+)(\d+)', doi_suffix)
        if match:
            journal = match.group(1)
            article_num = match.group(2)
            return f"https://{publisher_config['proxy_base']}/articles/{journal}/{article_num}.pdf"
        return None

    elif publisher_key == 'taylor_francis':
        # T&F: /doi/full/10.1080/xxx -> /doi/pdf/10.1080/xxx
        if '/doi/full/' in current_url:
            return current_url.replace('/doi/full/', '/doi/pdf/')
        elif '/doi/abs/' in current_url:
            return current_url.replace('/doi/abs/', '/doi/pdf/')
        return f"https://{publisher_config['proxy_base']}/doi/pdf/{doi}"

    elif publisher_key == 'royal_society':
        # Royal Society: /doi/10.1098/xxx -> /doi/pdf/10.1098/xxx
        if '/doi/' in current_url and '/pdf/' not in current_url:
            return current_url.replace('/doi/', '/doi/pdf/')
        return f"https://{publisher_config['proxy_base']}/doi/pdf/{doi}"

    elif publisher_key == 'jeb':
        # JEB: /article/ -> /article-pdf/
        if '/article/' in current_url:
            pdf_url = current_url.replace('/article/', '/article-pdf/')
            # Ensure it uses proxy
            if publisher_config['original_base'] in pdf_url:
                pdf_url = pdf_url.replace(publisher_config['original_base'], publisher_config['proxy_base'])
            return pdf_url
        # Construct from DOI: 10.1242/jeb.249715 -> /jeb/article-pdf/doi/10.1242/jeb.249715
        return f"https://{publisher_config['proxy_base']}/jeb/article-pdf/doi/{doi}"

    elif publisher_key == 'cambridge':
        # Cambridge: article page + /pdf
        if '/article/' in current_url and '/pdf' not in current_url:
            return current_url.rstrip('/') + '/pdf'
        return None

    elif publisher_key == 'nature':
        # Nature: /articles/xxx -> /articles/xxx.pdf
        if '/articles/' in current_url and '.pdf' not in current_url:
            return current_url.split('?')[0] + '.pdf'
        return None

    elif publisher_key == 'oxford':
        # Oxford: /article/ -> /article-pdf/
        if '/article/' in current_url:
            pdf_url = current_url.replace('/article/', '/article-pdf/')
            if not pdf_url.endswith('.pdf'):
                pdf_url = pdf_url + '.pdf'
            # Ensure it uses proxy
            if publisher_config['original_base'] in pdf_url:
                pdf_url = pdf_url.replace(publisher_config['original_base'], publisher_config['proxy_base'])
            return pdf_url
        # Construct from DOI - Oxford uses format: /doi/pdf/10.1093/xxx
        return f"https://{publisher_config['proxy_base']}/doi/pdf/{doi}"

    return None


# ============================================================================
# MAIN DOWNLOAD LOGIC
# ============================================================================

def download_paper(
    paper: Paper,
    publisher_key: str,
    publisher_config: dict,
    driver: 'uc.Chrome',
    logger: logging.Logger,
    stats: PublisherStats
) -> bool:
    """Download a single paper."""

    # Generate output path
    filename = generate_filename(paper.authors, paper.title, paper.year)
    year_folder = SHARK_PAPERS_BASE / str(int(paper.year)) if paper.year else SHARK_PAPERS_BASE / 'unknown_year'
    year_folder.mkdir(exist_ok=True)
    dest_path = year_folder / filename

    # Check if exists
    if dest_path.exists():
        logger.info(f"  EXISTS: {filename}")
        mark_downloaded(paper.id, filename, "exists")
        stats.existed += 1
        return True

    # Try Unpaywall first
    logger.debug("  Checking Unpaywall...")
    unpaywall = query_unpaywall(paper.doi, logger)

    if unpaywall.get('is_oa') and unpaywall.get('pdf_url'):
        logger.info(f"  Unpaywall: OA via {unpaywall['oa_status']}")
        success, content, msg = download_pdf_direct(unpaywall['pdf_url'], logger)
        if success and content:
            with open(dest_path, 'wb') as f:
                f.write(content)
            logger.info(f"  OK (Unpaywall): {filename} ({len(content)//1024}KB)")
            mark_downloaded(paper.id, filename, f"unpaywall-{unpaywall['oa_status']}")
            stats.downloaded += 1
            return True

    # Try browser with proxy
    logger.debug("  Trying browser with proxy...")
    success, content, msg = get_pdf_via_browser(driver, paper, publisher_config, logger)

    if success and content:
        with open(dest_path, 'wb') as f:
            f.write(content)
        logger.info(f"  OK (proxy): {filename} ({len(content)//1024}KB)")
        mark_downloaded(paper.id, filename, f"{publisher_key}-proxy")
        stats.downloaded += 1
        return True

    # Failed
    logger.warning(f"  FAIL: {msg}")
    if not unpaywall.get('is_oa'):
        mark_unavailable(paper.id, f"Not OA, proxy failed: {msg}", publisher_key)
        stats.unavailable += 1
    else:
        mark_failed(paper.id, f"OA but failed: {msg}", publisher_key)
        stats.failed += 1

    return False


def process_publisher(
    publisher_key: str,
    publisher_config: dict,
    driver: 'uc.Chrome',
    logger: logging.Logger,
    test_limit: int = 0,
    retry_unavailable: bool = False,
    retry_failed: bool = False
) -> PublisherStats:
    """Process all papers from a single publisher."""

    stats = PublisherStats()

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"PROCESSING: {publisher_config['name']}")
    logger.info(f"DOI prefix: {publisher_config['doi_prefix']}")
    logger.info("=" * 60)

    papers = get_pending_papers(publisher_config['doi_prefix'], retry_unavailable, retry_failed)

    if test_limit > 0:
        papers = papers[:test_limit]

    logger.info(f"Found {len(papers)} papers to process")

    if not papers:
        logger.info("No papers to download")
        return stats

    for i, paper in enumerate(papers, 1):
        logger.info(f"[{i}/{len(papers)}] {paper.doi}")

        download_paper(paper, publisher_key, publisher_config, driver, logger, stats)

        # After first paper of each publisher, pause to allow user to complete any
        # publisher-specific authentication (e.g., selecting university)
        if i == 1:
            logger.info("")
            logger.info("-" * 40)
            input(f">>> First {publisher_config['name']} paper attempted. If you need to select your university or complete additional auth, do it now in the browser, then press Enter... <<<")
            logger.info("-" * 40)
            logger.info("")

        if i < len(papers):
            time.sleep(DELAY_BETWEEN_REQUESTS)

        if i % 20 == 0:
            logger.info(f"Progress: {i}/{len(papers)} - {stats.downloaded} OK, {stats.existed} exist, {stats.failed} fail")

    logger.info(f"Publisher complete: {stats.downloaded} downloaded, {stats.existed} existed, {stats.unavailable} unavailable, {stats.failed} failed")

    return stats


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Batch download papers from all publishers via proxy")
    parser.add_argument('--test', type=int, default=0, help="Test mode: N papers per publisher")
    parser.add_argument('--skip-to', type=str, choices=list(PUBLISHERS.keys()), help="Skip to specific publisher")
    parser.add_argument('--only', type=str, choices=list(PUBLISHERS.keys()), help="Only process this publisher")
    parser.add_argument('--retry-unavailable', action='store_true', help="Retry papers marked as unavailable")
    parser.add_argument('--retry-failed', action='store_true', help="Retry papers marked as failed")
    parser.add_argument('--headless', action='store_true', help="Run browser in headless mode")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose logging")
    args = parser.parse_args()

    logger = setup_logging(verbose=args.verbose)

    logger.info("=" * 70)
    logger.info("BATCH PROXY DOWNLOADER - ALL PUBLISHERS")
    logger.info("=" * 70)
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Output: {SHARK_PAPERS_BASE}")
    logger.info("")

    # Show paper counts
    logger.info("Papers available per publisher:")
    for key, config in PUBLISHERS.items():
        papers = get_pending_papers(config['doi_prefix'], args.retry_unavailable, args.retry_failed)
        logger.info(f"  {config['name']}: {len(papers)}")
    logger.info("")
    logger.info(f"Retry unavailable: {args.retry_unavailable}")
    logger.info(f"Retry failed: {args.retry_failed}")
    logger.info(f"Using persistent Chrome profile: {CHROME_PROFILE_DIR}")
    logger.info("")

    if not SELENIUM_AVAILABLE:
        logger.error("Selenium not available. Install with: pip install undetected-chromedriver selenium")
        return

    # Setup browser
    logger.info("Starting browser...")
    driver = setup_browser(headless=args.headless)

    # Prompt for login
    logger.info("")
    logger.info("Opening FIU library for authentication...")
    driver.get("https://library.fiu.edu")
    input("\n>>> Please log in to FIU library, then press Enter to continue... <<<\n")
    logger.info("Authentication complete. Starting downloads...")

    # Determine which publishers to process
    publishers_to_process = list(PUBLISHERS.keys())

    if args.only:
        publishers_to_process = [args.only]
    elif args.skip_to:
        skip_idx = publishers_to_process.index(args.skip_to)
        publishers_to_process = publishers_to_process[skip_idx:]

    # Overall statistics
    total_stats = {
        'downloaded': 0,
        'existed': 0,
        'failed': 0,
        'unavailable': 0
    }

    try:
        for publisher_key in publishers_to_process:
            publisher_config = PUBLISHERS[publisher_key]

            stats = process_publisher(
                publisher_key,
                publisher_config,
                driver,
                logger,
                test_limit=args.test,
                retry_unavailable=args.retry_unavailable,
                retry_failed=args.retry_failed
            )

            total_stats['downloaded'] += stats.downloaded
            total_stats['existed'] += stats.existed
            total_stats['failed'] += stats.failed
            total_stats['unavailable'] += stats.unavailable

            # Delay between publishers
            if publisher_key != publishers_to_process[-1]:
                logger.info(f"Waiting {DELAY_BETWEEN_PUBLISHERS}s before next publisher...")
                time.sleep(DELAY_BETWEEN_PUBLISHERS)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    finally:
        logger.info("Closing browser...")
        driver.quit()

    # Final summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("BATCH DOWNLOAD COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total downloaded:   {total_stats['downloaded']}")
    logger.info(f"Total existed:      {total_stats['existed']}")
    logger.info(f"Total unavailable:  {total_stats['unavailable']}")
    logger.info(f"Total failed:       {total_stats['failed']}")
    total = sum(total_stats.values())
    if total > 0:
        success_rate = (total_stats['downloaded'] + total_stats['existed']) / total * 100
        logger.info(f"Success rate: {success_rate:.1f}%")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
