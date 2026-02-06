#!/usr/bin/env python3
"""
download_cambridge.py

Download papers from Cambridge University Press (DOIs starting with 10.1017/).

Cambridge has some open access content available directly on cambridge.org,
and we also check the Unpaywall API for OA versions.

Usage:
    ./venv/bin/python scripts/download_cambridge.py
    ./venv/bin/python scripts/download_cambridge.py --test 5
    ./venv/bin/python scripts/download_cambridge.py --email your@email.com
    ./venv/bin/python scripts/download_cambridge.py --retry-unavailable

Author: Simon Dedman / Claude
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
from typing import Optional

import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE = BASE_DIR / "database/download_tracker.db"
SHARKPAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = BASE_DIR / "logs"

# API Configuration
UNPAYWALL_EMAIL = "user@example.com"  # Update via --email argument
UNPAYWALL_BASE_URL = "https://api.unpaywall.org/v2"

# Request Configuration
DELAY_BETWEEN_REQUESTS = 2.0  # Be polite to servers
TIMEOUT = 60  # Timeout for PDF downloads
MAX_RETRIES = 3
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Cambridge specific
CAMBRIDGE_DOI_PREFIX = "10.1017/%"

# University proxy configuration (FIU OpenAthens)
PROXY_ENABLED = False  # Set via --proxy flag
PROXY_BASE = "www-cambridge-org.eu1.proxy.openathens.net"
ORIGINAL_BASE = "www.cambridge.org"


def to_proxy_url(url: str) -> str:
    """Convert Cambridge URL to university proxy URL."""
    if PROXY_ENABLED and url:
        return url.replace(ORIGINAL_BASE, PROXY_BASE).replace("http://", "https://")
    return url


# ============================================================================
# LOGGING SETUP
# ============================================================================


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"cambridge_{timestamp}.log"

    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
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
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    # Remove special characters except spaces and hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    # Take first 8 words for title
    words = text.split()[:8]
    return " ".join(words)


def get_first_author(authors_str: str) -> str:
    """Extract first author surname from authors string."""
    if not authors_str:
        return "Unknown"

    authors_str = str(authors_str).strip()

    # Handle various separators
    for sep in [" & ", ";", ",", " and "]:
        if sep in authors_str:
            first = authors_str.split(sep)[0].strip()
            break
    else:
        first = authors_str

    # Extract surname (usually first word)
    parts = first.replace(",", " ").split()
    if parts:
        # Clean up and return first part (surname)
        surname = "".join(c for c in parts[0] if c.isalnum())
        return surname if surname else "Unknown"
    return "Unknown"


def has_multiple_authors(authors_str: str) -> bool:
    """Check if there are multiple authors."""
    if not authors_str:
        return False
    indicators = [",", ";", " and ", "&", " et al"]
    return any(ind in str(authors_str).lower() for ind in indicators)


def generate_filename(authors: str, title: str, year: int) -> str:
    """
    Generate PDF filename from paper metadata.

    Format: FirstAuthor.etal.YEAR.Title words.pdf
            or FirstAuthor.YEAR.Title words.pdf (single author)
    """
    author = get_first_author(authors)
    title_clean = clean_for_filename(title)

    if has_multiple_authors(authors):
        return f"{author}.etal.{int(year)}.{title_clean}.pdf"
    return f"{author}.{int(year)}.{title_clean}.pdf"


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================


def get_pending_papers(
    retry_unavailable: bool = False,
) -> list[tuple[int, str, str, str, int]]:
    """
    Get Cambridge papers that haven't been downloaded.

    Args:
        retry_unavailable: If True, also retry papers marked as unavailable

    Returns:
        List of tuples: (id, doi, title, authors, year)
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    if retry_unavailable:
        # Get papers not downloaded (including unavailable)
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
            (CAMBRIDGE_DOI_PREFIX,),
        )
    else:
        # Get only papers with no download attempt or pending
        cur.execute(
            """
            SELECT p.id, p.doi, p.title, p.authors, p.year
            FROM papers p
            WHERE p.doi LIKE ?
            AND p.id NOT IN (
                SELECT paper_id FROM download_status
                WHERE status IN ('downloaded', 'unavailable')
            )
            ORDER BY p.year DESC
        """,
            (CAMBRIDGE_DOI_PREFIX,),
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

    # Check if record exists
    cur.execute(
        "SELECT id FROM download_status WHERE paper_id = ?", (paper_id,)
    )
    existing = cur.fetchone()

    if existing:
        cur.execute(
            """
            UPDATE download_status
            SET status = ?, source = ?, download_date = datetime('now'),
                notes = ?, attempts = attempts + 1, last_attempt = datetime('now')
            WHERE paper_id = ?
        """,
            (status, source, notes, paper_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO download_status
            (paper_id, status, source, download_date, notes, attempts, last_attempt)
            VALUES (?, ?, ?, datetime('now'), ?, 1, datetime('now'))
        """,
            (paper_id, status, source, notes),
        )

    conn.commit()
    conn.close()


# ============================================================================
# UNPAYWALL API
# ============================================================================


def query_unpaywall(doi: str, logger: logging.Logger) -> dict:
    """
    Query Unpaywall API for open access PDF.

    Returns dict with:
    - is_oa: boolean
    - pdf_url: URL to PDF if available
    - source: 'unpaywall'
    - error: error message if failed
    """
    # Unpaywall wants the DOI in the URL path, not URL-encoded
    # The API handles the DOI directly
    url = f"{UNPAYWALL_BASE_URL}/{doi}"
    params = {"email": UNPAYWALL_EMAIL}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url, params=params, timeout=30, headers={"User-Agent": USER_AGENT}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("is_oa"):
                    best_oa = data.get("best_oa_location", {})
                    pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
                    if pdf_url:
                        return {
                            "is_oa": True,
                            "pdf_url": pdf_url,
                            "source": "unpaywall",
                            "oa_status": data.get("oa_status", "unknown"),
                            "host_type": best_oa.get("host_type", "unknown"),
                        }
                return {"is_oa": False, "error": "not_open_access"}

            elif response.status_code == 404:
                logger.debug(f"DOI not found in Unpaywall: {doi}")
                return {"is_oa": False, "error": "not_in_unpaywall"}

            elif response.status_code == 429:
                logger.warning(f"Rate limited by Unpaywall, waiting...")
                time.sleep(10 * (attempt + 1))
                continue

            else:
                logger.warning(
                    f"Unpaywall returned {response.status_code} for {doi}"
                )
                time.sleep(2**attempt)
                continue

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout querying Unpaywall (attempt {attempt + 1})")
            time.sleep(2**attempt)
            continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error querying Unpaywall: {e}")
            time.sleep(2**attempt)
            continue

    return {"is_oa": False, "error": "failed_after_retries"}


# ============================================================================
# CAMBRIDGE DIRECT ACCESS
# ============================================================================


def get_cambridge_pdf_url(doi: str, logger: logging.Logger) -> Optional[str]:
    """
    Try to get direct PDF URL from Cambridge University Press.

    Cambridge has various URL patterns:
    - https://www.cambridge.org/core/services/aop-cambridge-core/content/view/{doi}
    - https://www.cambridge.org/core/journals/.../article/.../... (HTML page)

    Returns PDF URL if found, None otherwise.
    """
    # Try DOI redirect first to get the article page
    doi_url = f"https://doi.org/{doi}"

    try:
        response = requests.get(
            doi_url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
            allow_redirects=True,
        )

        if response.status_code != 200:
            logger.debug(f"DOI redirect failed: {response.status_code}")
            return None

        final_url = response.url

        # If we're on Cambridge, try to find PDF link
        if "cambridge.org" in final_url:
            # If redirected to /abs/ page, it's likely not open access
            # (Cambridge redirects to /abs/ for paywalled content)
            if "/abs/" in final_url:
                logger.debug(f"Redirected to abstract page (likely paywalled): {final_url}")
                return None

            # Check if the page indicates open access
            content = response.text.lower()
            is_open_access = (
                "open access" in content
                or "open-access" in content
                or "cc by" in content
                or "creative commons" in content
            )

            if not is_open_access:
                logger.debug(f"No OA indicator found on Cambridge page: {final_url}")
                return None

            # For true OA content, construct PDF URL
            # Remove any trailing slashes and add /pdf
            if "/article/" in final_url and "/pdf" not in final_url:
                # Standard article URL format
                pdf_url = final_url.rstrip("/") + "/pdf"
                return pdf_url

            logger.debug(f"Cambridge OA page but couldn't construct PDF URL: {final_url}")
            return None

    except requests.exceptions.RequestException as e:
        logger.debug(f"Error checking Cambridge: {e}")
        return None

    return None


def check_cambridge_open_access(doi: str, logger: logging.Logger) -> dict:
    """
    Check if Cambridge paper is open access and get PDF URL.

    Returns dict with:
    - is_oa: boolean
    - pdf_url: URL if available
    - source: 'cambridge'
    """
    pdf_url = get_cambridge_pdf_url(doi, logger)
    if pdf_url:
        return {
            "is_oa": True,
            "pdf_url": pdf_url,
            "source": "cambridge",
        }
    return {"is_oa": False, "error": "not_open_access_on_cambridge"}


# ============================================================================
# PDF DOWNLOAD
# ============================================================================


def download_pdf(
    url: str, output_path: Path, logger: logging.Logger
) -> dict:
    """
    Download PDF from URL.

    Returns dict with:
    - success: boolean
    - size_bytes: file size if successful
    - error: error message if failed
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,application/octet-stream,*/*",
    }

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Download attempt {attempt + 1}: {url}")

            response = requests.get(
                url,
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=True,
                stream=True,
            )

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()

                # Read content
                content = response.content

                # Verify it's a PDF
                if b"%PDF" in content[:1024] or "pdf" in content_type:
                    # Save to file
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(output_path, "wb") as f:
                        f.write(content)

                    file_size = output_path.stat().st_size

                    # Verify file size (PDFs should be at least 1KB)
                    if file_size < 1024:
                        output_path.unlink()
                        return {
                            "success": False,
                            "error": f"File too small ({file_size} bytes)",
                        }

                    return {"success": True, "size_bytes": file_size}

                else:
                    return {
                        "success": False,
                        "error": f"Not a PDF (content-type: {content_type[:50]})",
                    }

            elif response.status_code == 403:
                return {"success": False, "error": "403 Forbidden (paywall)"}

            elif response.status_code == 404:
                return {"success": False, "error": "404 Not Found"}

            elif response.status_code == 429:
                logger.warning("Rate limited, waiting...")
                time.sleep(30 * (attempt + 1))
                continue

            else:
                logger.warning(f"HTTP {response.status_code} on attempt {attempt + 1}")
                time.sleep(2**attempt)
                continue

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}")
            time.sleep(2**attempt)
            continue

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
            time.sleep(5 * (attempt + 1))
            continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {"success": False, "error": str(e)[:100]}

    return {"success": False, "error": f"Failed after {MAX_RETRIES} attempts"}


# ============================================================================
# MAIN DOWNLOAD LOGIC
# ============================================================================


def download_paper(
    paper_id: int,
    doi: str,
    title: str,
    authors: str,
    year: int,
    logger: logging.Logger,
) -> dict:
    """
    Attempt to download a single Cambridge paper.

    Tries:
    1. Cambridge direct (for OA papers)
    2. Unpaywall API

    Returns dict with status and details.
    """
    result = {
        "paper_id": paper_id,
        "doi": doi,
        "title": title,
        "year": year,
        "status": "failed",
        "source": None,
        "notes": "",
    }

    # Generate output path
    filename = generate_filename(authors, title, year)
    year_dir = SHARKPAPERS / str(int(year)) if year else SHARKPAPERS / "unknown_year"
    output_path = year_dir / filename

    # Check if already exists
    if output_path.exists():
        result["status"] = "already_exists"
        result["notes"] = f"File exists: {output_path}"
        result["filename"] = str(output_path)
        logger.info(f"EXISTS: {filename}")
        mark_status(paper_id, "downloaded", "exists", str(output_path))
        return result

    # Strategy 1: Try Cambridge direct
    logger.debug(f"Checking Cambridge for: {doi}")
    cambridge_result = check_cambridge_open_access(doi, logger)

    if cambridge_result.get("is_oa") and cambridge_result.get("pdf_url"):
        pdf_url = to_proxy_url(cambridge_result["pdf_url"])
        logger.info(f"Found OA on Cambridge: {doi}")
        logger.debug(f"Cambridge PDF URL: {pdf_url}")

        download_result = download_pdf(pdf_url, output_path, logger)

        if download_result.get("success"):
            result["status"] = "downloaded"
            result["source"] = "cambridge"
            result["filename"] = str(output_path)
            result["size_bytes"] = download_result.get("size_bytes", 0)
            logger.info(
                f"OK (Cambridge): {filename} ({download_result['size_bytes']//1024}KB)"
            )
            mark_status(paper_id, "downloaded", "cambridge", pdf_url)
            return result
        else:
            logger.warning(
                f"Cambridge PDF download failed: {download_result.get('error')}"
            )

    # Strategy 2: Try Unpaywall
    time.sleep(DELAY_BETWEEN_REQUESTS)
    logger.debug(f"Checking Unpaywall for: {doi}")
    unpaywall_result = query_unpaywall(doi, logger)

    if unpaywall_result.get("is_oa") and unpaywall_result.get("pdf_url"):
        pdf_url = unpaywall_result["pdf_url"]
        logger.info(
            f"Found OA via Unpaywall ({unpaywall_result.get('host_type')}): {doi}"
        )

        download_result = download_pdf(pdf_url, output_path, logger)

        if download_result.get("success"):
            result["status"] = "downloaded"
            result["source"] = f"unpaywall-{unpaywall_result.get('host_type', 'unknown')}"
            result["filename"] = str(output_path)
            result["size_bytes"] = download_result.get("size_bytes", 0)
            logger.info(
                f"OK (Unpaywall): {filename} ({download_result['size_bytes']//1024}KB)"
            )
            mark_status(
                paper_id,
                "downloaded",
                f"unpaywall-{unpaywall_result.get('host_type')}",
                pdf_url,
            )
            return result
        else:
            logger.warning(
                f"Unpaywall URL failed: {download_result.get('error')}"
            )

    # Failed to download
    result["status"] = "unavailable"
    result["notes"] = "No open access version found"
    logger.warning(f"UNAVAILABLE: {doi} - {title[:50]}...")
    mark_status(paper_id, "unavailable", "no_oa", "Checked Cambridge and Unpaywall")

    return result


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    global UNPAYWALL_EMAIL, DELAY_BETWEEN_REQUESTS

    parser = argparse.ArgumentParser(
        description="Download Cambridge University Press papers (DOI 10.1017/)"
    )
    parser.add_argument(
        "--test",
        type=int,
        metavar="N",
        help="Test mode: process only N papers",
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help=f"Email for Unpaywall API (default: {UNPAYWALL_EMAIL})",
    )
    parser.add_argument(
        "--retry-unavailable",
        action="store_true",
        help="Retry papers previously marked as unavailable",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help=f"Delay between requests in seconds (default: {DELAY_BETWEEN_REQUESTS})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Use university library proxy (FIU OpenAthens) for authenticated access",
    )
    parser.add_argument(
        "--pause-for-login",
        action="store_true",
        help="Pause after browser opens for manual library login (use with --proxy)",
    )
    args = parser.parse_args()

    # Update global config if provided
    global PROXY_ENABLED
    if args.email:
        UNPAYWALL_EMAIL = args.email
    if args.delay is not None:
        DELAY_BETWEEN_REQUESTS = args.delay
    if args.proxy:
        PROXY_ENABLED = True

    # Setup logging
    logger = setup_logging(verbose=args.verbose)

    print("=" * 70)
    print("CAMBRIDGE UNIVERSITY PRESS PAPER DOWNLOADER")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DATABASE}")
    print(f"Output: {SHARKPAPERS}")
    print(f"Unpaywall email: {UNPAYWALL_EMAIL}")
    print(f"Delay: {DELAY_BETWEEN_REQUESTS}s between requests")
    print(f"Proxy: {'ENABLED (FIU OpenAthens)' if PROXY_ENABLED else 'disabled'}")
    print("")

    if UNPAYWALL_EMAIL == "user@example.com":
        print("WARNING: Please provide your email via --email argument")
        print("   Unpaywall requires an email for courtesy contact")
        print("   Example: python download_cambridge.py --email you@university.edu")
        print("")

    # Get pending papers
    papers = get_pending_papers(retry_unavailable=args.retry_unavailable)
    logger.info(f"Found {len(papers)} Cambridge papers to process")

    if args.test:
        papers = papers[: args.test]
        logger.info(f"Test mode: processing {len(papers)} papers")

    if not papers:
        print("No papers to download!")
        return

    print(f"\nProcessing {len(papers)} papers...")
    print("-" * 70)

    # Statistics
    stats = {
        "downloaded": 0,
        "already_exists": 0,
        "unavailable": 0,
        "failed": 0,
    }

    start_time = time.time()

    for i, (paper_id, doi, title, authors, year) in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] {doi}")

        result = download_paper(paper_id, doi, title, authors, year, logger)

        stats[result["status"]] = stats.get(result["status"], 0) + 1

        # Progress update
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed * 60 if elapsed > 0 else 0
            logger.info(
                f"Progress: {i}/{len(papers)} - "
                f"{stats['downloaded']} downloaded, "
                f"{stats['unavailable']} unavailable "
                f"({rate:.1f} papers/min)"
            )

        # Rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Summary
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"\nTotal papers processed: {len(papers)}")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"\nResults:")
    print(f"  Downloaded:      {stats['downloaded']}")
    print(f"  Already existed: {stats['already_exists']}")
    print(f"  Unavailable:     {stats['unavailable']}")
    print(f"  Failed:          {stats['failed']}")

    success_rate = (
        (stats["downloaded"] + stats["already_exists"]) / len(papers) * 100
        if papers
        else 0
    )
    print(f"\nSuccess rate: {success_rate:.1f}%")
    print(f"\nPDFs saved to: {SHARKPAPERS}")
    print("=" * 70)

    logger.info(
        f"Completed: {stats['downloaded']} downloaded, "
        f"{stats['already_exists']} existed, "
        f"{stats['unavailable']} unavailable"
    )


if __name__ == "__main__":
    main()
