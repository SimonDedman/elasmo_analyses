#!/usr/bin/env python3
"""
download_open_access.py

Download papers from Open Access publishers with predictable PDF URLs.
Supports: PLOS, Frontiers, PeerJ, MDPI

Usage:
    ./venv/bin/python scripts/download_open_access.py --publisher plos
    ./venv/bin/python scripts/download_open_access.py --publisher frontiers
    ./venv/bin/python scripts/download_open_access.py --publisher peerj
    ./venv/bin/python scripts/download_open_access.py --publisher mdpi
    ./venv/bin/python scripts/download_open_access.py --publisher all
"""

import argparse
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
import time
import re
import unicodedata
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import random

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE = BASE_DIR / "database/download_tracker.db"
SHARKPAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = BASE_DIR / "logs"

DELAY = 2.0  # Seconds between requests (be polite to OA servers)
TIMEOUT = 60  # Longer timeout for large PDFs
MAX_WORKERS = 3  # Parallel downloads

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Publisher configurations
PUBLISHERS = {
    'plos': {
        'name': 'PLOS ONE',
        'doi_pattern': '10.1371/journal.pone%',
        'pdf_url': lambda doi: f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable",
        'headers': {'User-Agent': USER_AGENT},
    },
    'plos_biology': {
        'name': 'PLOS Biology',
        'doi_pattern': '10.1371/journal.pbio%',
        'pdf_url': lambda doi: f"https://journals.plos.org/plosbiology/article/file?id={doi}&type=printable",
        'headers': {'User-Agent': USER_AGENT},
    },
    'frontiers': {
        'name': 'Frontiers',
        'doi_pattern': '10.3389/%',
        'pdf_url': lambda doi: f"https://www.frontiersin.org/articles/{doi}/pdf",
        'headers': {'User-Agent': USER_AGENT, 'Accept': 'application/pdf'},
    },
    'peerj': {
        'name': 'PeerJ',
        'doi_pattern': '10.7717/peerj%',
        'pdf_url': lambda doi: f"https://peerj.com/articles/{doi.split('.')[-1]}.pdf",
        'headers': {'User-Agent': USER_AGENT},
    },
    'mdpi': {
        'name': 'MDPI',
        'doi_pattern': '10.3390/%',
        # MDPI URL: https://www.mdpi.com/{journal}/{volume}/{issue}/{article_id}/pdf
        # Easier to get from DOI redirect
        'pdf_url': lambda doi: f"https://www.mdpi.com/{doi.replace('10.3390/', '')}/pdf",
        'headers': {'User-Agent': USER_AGENT},
    },
}

# Thread-safe stats
stats_lock = Lock()
stats = {'downloaded': 0, 'failed': 0, 'skipped': 0}
db_lock = Lock()

# ============================================================================
# HELPERS
# ============================================================================

def clean_for_filename(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\w\s-]', '', text)
    words = text.split()[:8]
    return ' '.join(words)

def get_first_author(authors_str):
    if not authors_str:
        return "Unknown"
    for sep in [';', ',', ' and ', '&']:
        if sep in str(authors_str):
            first = str(authors_str).split(sep)[0].strip()
            break
    else:
        first = str(authors_str).strip()
    parts = first.replace(',', ' ').split()
    return parts[0] if parts else "Unknown"

def generate_filename(authors, title, year):
    author = get_first_author(authors)
    title_clean = clean_for_filename(title)
    authors_str = str(authors) if authors else ''

    if any(sep in authors_str for sep in [',', ';', ' and ']):
        return f"{author}.etal.{int(year)}.{title_clean}.pdf"
    return f"{author}.{int(year)}.{title_clean}.pdf"

def mark_status(paper_id, status, source, notes=''):
    """Thread-safe database update."""
    with db_lock:
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO download_status (paper_id, status, source, download_date, notes)
            VALUES (?, ?, ?, datetime('now'), ?)
        ''', (paper_id, status, source, notes))
        conn.commit()
        conn.close()

def get_pending_papers(doi_pattern):
    """Get papers matching DOI pattern that haven't been downloaded."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('''
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        WHERE p.doi LIKE ?
        AND p.id NOT IN (SELECT paper_id FROM download_status WHERE status = 'downloaded')
        ORDER BY p.year DESC
    ''', (doi_pattern,))
    papers = cur.fetchall()
    conn.close()
    return papers

def download_pdf(url, headers, timeout=TIMEOUT):
    """Download PDF from URL. Returns (success, content, message)."""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

        if resp.status_code == 200:
            # Check if it's actually a PDF
            content_type = resp.headers.get('Content-Type', '').lower()
            if 'pdf' in content_type or resp.content[:4] == b'%PDF':
                return True, resp.content, "Success"
            else:
                return False, None, f"Not PDF: {content_type[:30]}"
        elif resp.status_code == 404:
            return False, None, "404 Not Found"
        elif resp.status_code == 429:
            return False, None, "Rate limited"
        else:
            return False, None, f"HTTP {resp.status_code}"

    except requests.Timeout:
        return False, None, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, None, "Connection error"
    except Exception as e:
        return False, None, str(e)[:30]

def download_paper(paper, config, logger):
    """Download a single paper."""
    paper_id, doi, title, authors, year = paper

    # Generate PDF URL
    pdf_url = config['pdf_url'](doi)

    # Download
    success, content, msg = download_pdf(pdf_url, config['headers'])

    if success and content:
        # Generate filename and save
        filename = generate_filename(authors, title, year)
        year_dir = SHARKPAPERS / str(int(year)) if year else SHARKPAPERS / 'unknown_year'
        year_dir.mkdir(exist_ok=True)
        output_path = year_dir / filename

        if output_path.exists():
            with stats_lock:
                stats['skipped'] += 1
            mark_status(paper_id, 'downloaded', config['name'].lower() + '-exists')
            logger.info(f"EXISTS: {filename}")
            return True
        else:
            with open(output_path, 'wb') as f:
                f.write(content)
            with stats_lock:
                stats['downloaded'] += 1
            mark_status(paper_id, 'downloaded', config['name'].lower())
            logger.info(f"OK: {filename} ({len(content)//1024}KB)")
            return True
    else:
        with stats_lock:
            stats['failed'] += 1
        mark_status(paper_id, 'unavailable', config['name'].lower(), msg)
        logger.warning(f"FAIL: {doi} - {msg}")
        return False

# ============================================================================
# MAIN
# ============================================================================

def download_publisher(publisher_key, test_count=None, logger=None):
    """Download all pending papers from a publisher."""
    config = PUBLISHERS[publisher_key]

    logger.info(f"\n{'='*60}")
    logger.info(f"Downloading: {config['name']}")
    logger.info(f"{'='*60}")

    # Get pending papers
    papers = get_pending_papers(config['doi_pattern'])
    logger.info(f"Found {len(papers)} pending papers")

    if test_count:
        papers = papers[:test_count]
        logger.info(f"Test mode: {len(papers)} papers")

    if not papers:
        logger.info("No papers to download!")
        return

    # Reset stats
    with stats_lock:
        stats['downloaded'] = 0
        stats['failed'] = 0
        stats['skipped'] = 0

    # Download with rate limiting
    start_time = time.time()

    for i, paper in enumerate(papers):
        download_paper(paper, config, logger)

        # Progress
        if (i + 1) % 20 == 0:
            with stats_lock:
                logger.info(f"Progress: {i+1}/{len(papers)} - {stats['downloaded']} OK, {stats['failed']} fail")

        # Rate limiting
        time.sleep(DELAY + random.uniform(0, 1))  # Add jitter

    # Summary
    elapsed = time.time() - start_time
    with stats_lock:
        logger.info(f"\n{config['name']} Complete:")
        logger.info(f"  Downloaded: {stats['downloaded']}")
        logger.info(f"  Already existed: {stats['skipped']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Time: {elapsed/60:.1f} minutes")

def main():
    parser = argparse.ArgumentParser(description="Download from Open Access publishers")
    parser.add_argument('--publisher', required=True,
                        choices=['plos', 'frontiers', 'peerj', 'mdpi', 'all'],
                        help="Publisher to download from")
    parser.add_argument('--test', type=int, help="Test with N papers")
    parser.add_argument('--workers', type=int, default=1, help="Parallel workers (be careful!)")
    args = parser.parse_args()

    # Setup logging
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"open_access_{args.publisher}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger()

    logger.info("="*60)
    logger.info("OPEN ACCESS DOWNLOADER")
    logger.info("="*60)
    logger.info(f"Publisher: {args.publisher}")
    logger.info(f"Delay: {DELAY}s between requests")
    logger.info(f"Log: {log_file}")

    if args.publisher == 'all':
        for pub in ['plos', 'frontiers', 'peerj', 'mdpi']:
            download_publisher(pub, args.test, logger)
    else:
        download_publisher(args.publisher, args.test, logger)

    logger.info("\n" + "="*60)
    logger.info("ALL DOWNLOADS COMPLETE")
    logger.info("="*60)

if __name__ == '__main__':
    main()
