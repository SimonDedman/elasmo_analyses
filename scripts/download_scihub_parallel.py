#!/usr/bin/env python3
"""
download_scihub_parallel.py

Parallel Sci-Hub downloader using multiple workers.
Each worker uses a different mirror and maintains its own rate limit.

Usage:
    ./venv/bin/python scripts/download_scihub_parallel.py --workers 4 --max-year 2023

EDUCATIONAL/RESEARCH USE ONLY
"""

import argparse
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
import time
import re
import unicodedata
from bs4 import BeautifulSoup
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import queue
import random

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE = BASE_DIR / "database/download_tracker.db"
SHARKPAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_DIR = BASE_DIR / "logs"

# Multiple mirrors for parallel access
SCIHUB_MIRRORS = [
    "https://sci-hub.ru",
    "https://sci-hub.se",
    "https://sci-hub.st",
    "https://sci-hub.ee",
]

DELAY_PER_WORKER = 5.0  # Each worker waits 5s between requests
TIMEOUT = 45
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

# Thread-safe counters
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

def download_from_scihub(doi, mirror):
    """Download PDF from Sci-Hub. Returns (success, content, message)."""
    try:
        url = f"{mirror}/{doi}"
        resp = requests.get(url, timeout=TIMEOUT, headers={'User-Agent': USER_AGENT})

        if resp.status_code != 200:
            return False, None, f"HTTP {resp.status_code}"

        if 'application/pdf' in resp.headers.get('Content-Type', ''):
            if resp.content[:4] == b'%PDF':
                return True, resp.content, "Direct PDF"
            return False, None, "Invalid PDF"

        text_lower = resp.text.lower()
        if 'article not found' in text_lower or 'отсутствует' in text_lower:
            return False, None, "Not on Sci-Hub"

        # Find PDF URL
        pdf_url = None

        # Method 1: /storage/ paths
        storage_match = re.search(r'["\'](/storage/[^"\']+\.pdf)["\']', resp.text)
        if storage_match:
            pdf_url = storage_match.group(1)

        # Method 2: Any .pdf in quotes
        if not pdf_url:
            pdf_match = re.search(r'["\']([^"\']*\.pdf)["\']', resp.text, re.IGNORECASE)
            if pdf_match:
                pdf_url = pdf_match.group(1)

        # Method 3: embed/iframe
        if not pdf_url:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup.find_all(['embed', 'iframe', 'object'], src=True):
                if '.pdf' in tag.get('src', ''):
                    pdf_url = tag['src']
                    break

        if not pdf_url:
            return False, None, "No PDF link"

        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            pdf_url = mirror + pdf_url

        pdf_resp = requests.get(pdf_url, timeout=TIMEOUT, headers={'User-Agent': USER_AGENT})
        if pdf_resp.status_code == 200 and pdf_resp.content[:4] == b'%PDF':
            return True, pdf_resp.content, "Success"

        return False, None, "PDF download failed"

    except requests.Timeout:
        return False, None, "Timeout"
    except Exception as e:
        return False, None, str(e)[:30]

def mark_status(paper_id, status, source='scihub', notes=''):
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

def worker(worker_id, paper_queue, mirror, logger):
    """Worker thread that processes papers from the queue."""
    while True:
        try:
            paper = paper_queue.get(timeout=1)
        except queue.Empty:
            break

        paper_id, doi, title, authors, year = paper

        # Download
        success, content, msg = download_from_scihub(doi, mirror)

        with stats_lock:
            if success and content:
                # Save file
                filename = generate_filename(authors, title, year)
                year_dir = SHARKPAPERS / str(int(year)) if year else SHARKPAPERS / 'unknown_year'
                year_dir.mkdir(exist_ok=True)
                output_path = year_dir / filename

                if output_path.exists():
                    stats['skipped'] += 1
                    mark_status(paper_id, 'downloaded', 'scihub-exists')
                    logger.info(f"[W{worker_id}] EXISTS: {filename}")
                else:
                    with open(output_path, 'wb') as f:
                        f.write(content)
                    stats['downloaded'] += 1
                    mark_status(paper_id, 'downloaded', 'scihub')
                    logger.info(f"[W{worker_id}] OK: {filename} ({len(content)//1024}KB)")
            else:
                stats['failed'] += 1
                mark_status(paper_id, 'unavailable', 'scihub', msg)
                logger.debug(f"[W{worker_id}] FAIL: {doi[:30]}... - {msg}")

        paper_queue.task_done()
        time.sleep(DELAY_PER_WORKER)

def get_untried_papers(max_year=2023):
    """Get papers that haven't been tried yet."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute('''
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        WHERE p.doi IS NOT NULL AND p.doi != ''
        AND p.year <= ?
        AND p.id NOT IN (SELECT paper_id FROM download_status)
        ORDER BY p.year DESC
    ''', (max_year,))

    papers = cur.fetchall()
    conn.close()
    return papers

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Parallel Sci-Hub downloader")
    parser.add_argument('--workers', type=int, default=4, help="Number of parallel workers")
    parser.add_argument('--max-year', type=int, default=2023, help="Maximum year to download")
    parser.add_argument('--test', type=int, help="Test with N papers")
    args = parser.parse_args()

    # Setup logging
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"scihub_parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger()

    logger.info("=" * 70)
    logger.info("PARALLEL SCI-HUB DOWNLOADER")
    logger.info("EDUCATIONAL/RESEARCH USE ONLY")
    logger.info("=" * 70)
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Max year: {args.max_year}")
    logger.info(f"Delay per worker: {DELAY_PER_WORKER}s")
    logger.info(f"Effective rate: ~{DELAY_PER_WORKER/args.workers:.1f}s per paper")

    # Get papers
    papers = get_untried_papers(args.max_year)
    logger.info(f"Found {len(papers):,} untried papers")

    if args.test:
        papers = papers[:args.test]
        logger.info(f"Test mode: {len(papers)} papers")

    if not papers:
        logger.info("No papers to download!")
        return

    # Check mirrors
    working_mirrors = []
    for mirror in SCIHUB_MIRRORS:
        try:
            r = requests.get(mirror, timeout=10, headers={'User-Agent': USER_AGENT})
            if r.status_code == 200:
                working_mirrors.append(mirror)
                logger.info(f"Mirror OK: {mirror}")
        except:
            logger.warning(f"Mirror FAIL: {mirror}")

    if not working_mirrors:
        logger.error("No working mirrors!")
        return

    # Use only as many workers as we have mirrors (to distribute load)
    num_workers = min(args.workers, len(working_mirrors))
    logger.info(f"Using {num_workers} workers across {len(working_mirrors)} mirrors")

    # Create queue
    paper_queue = queue.Queue()
    for paper in papers:
        paper_queue.put(paper)

    # Estimate time
    est_seconds = len(papers) * DELAY_PER_WORKER / num_workers
    est_hours = est_seconds / 3600
    logger.info(f"Estimated time: {est_hours:.1f} hours")
    logger.info("=" * 70)

    # Start workers
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for i in range(num_workers):
            mirror = working_mirrors[i % len(working_mirrors)]
            future = executor.submit(worker, i, paper_queue, mirror, logger)
            futures.append(future)
            time.sleep(1)  # Stagger start

        # Progress reporting
        total = len(papers)
        while not paper_queue.empty():
            with stats_lock:
                done = stats['downloaded'] + stats['failed'] + stats['skipped']

            if done > 0 and done % 100 == 0:
                elapsed = time.time() - start_time
                rate = done / elapsed * 3600
                remaining = (total - done) / rate if rate > 0 else 0
                logger.info(f"Progress: {done:,}/{total:,} ({done/total*100:.1f}%) - "
                           f"{stats['downloaded']} OK, {stats['failed']} fail - "
                           f"ETA: {remaining:.1f}h")
            time.sleep(5)

        # Wait for completion
        for future in futures:
            future.result()

    # Final stats
    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info("COMPLETE")
    logger.info(f"  Downloaded: {stats['downloaded']:,}")
    logger.info(f"  Already existed: {stats['skipped']:,}")
    logger.info(f"  Failed: {stats['failed']:,}")
    logger.info(f"  Total: {len(papers):,}")
    logger.info(f"  Time: {elapsed/3600:.1f} hours")
    logger.info(f"  Rate: {len(papers)/elapsed*3600:.0f} papers/hour")
    logger.info(f"  Log: {log_file}")
    logger.info("=" * 70)

if __name__ == '__main__':
    main()
