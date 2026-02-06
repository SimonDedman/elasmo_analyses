#!/usr/bin/env python3
"""
download_batch_scihub.py

Generic Sci-Hub batch downloader for CSV files with DOIs.
Uses existing Sci-Hub download infrastructure.

Usage:
    ./venv/bin/python scripts/download_batch_scihub.py --input outputs/jfb_scihub_batch.csv

EDUCATIONAL/RESEARCH USE ONLY
"""

import argparse
import pandas as pd
import sqlite3
import requests
from pathlib import Path
from datetime import datetime
import time
import re
import unicodedata
from bs4 import BeautifulSoup
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE = BASE_DIR / "database/download_tracker.db"
SHARKPAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")

SCIHUB_MIRRORS = ["https://sci-hub.ru", "https://sci-hub.se", "https://sci-hub.st"]
DELAY = 5.0
TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

# ============================================================================
# HELPERS
# ============================================================================

def clean_for_filename(text):
    """Clean text for filename use."""
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\w\s-]', '', text)
    words = text.split()[:8]
    return ' '.join(words)

def get_first_author(authors_str):
    """Extract first author's last name."""
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

def generate_filename(row):
    """Generate standard PDF filename."""
    author = get_first_author(row.get('authors', ''))
    raw_year = row.get('year', None)
    year = int(raw_year) if raw_year and str(raw_year) != 'nan' else 'unknown'
    title = clean_for_filename(row.get('title', ''))
    authors_str = str(row.get('authors', ''))

    if any(sep in authors_str for sep in [',', ';', ' and ']):
        return f"{author}.etal.{year}.{title}.pdf"
    return f"{author}.{year}.{title}.pdf"

def download_from_scihub(doi, mirror):
    """Download PDF from Sci-Hub. Returns (success, content, message)."""
    try:
        url = f"{mirror}/{doi}"
        resp = requests.get(url, timeout=TIMEOUT, headers={'User-Agent': USER_AGENT})

        if resp.status_code != 200:
            return False, None, f"HTTP {resp.status_code}"

        # Check for direct PDF
        if 'application/pdf' in resp.headers.get('Content-Type', ''):
            if resp.content[:4] == b'%PDF':
                return True, resp.content, "Direct PDF"
            return False, None, "Invalid PDF"

        # Parse HTML for PDF link
        text_lower = resp.text.lower()

        # Check if not found
        if 'article not found' in text_lower or 'отсутствует' in text_lower:
            return False, None, "Not on Sci-Hub"

        # Find PDF URL - try multiple methods
        pdf_url = None

        # Method 1: Look in JavaScript for /storage/ paths (Sci-Hub's new format)
        storage_match = re.search(r'["\'](/storage/[^"\']+\.pdf)["\']', resp.text)
        if storage_match:
            pdf_url = storage_match.group(1)

        # Method 2: Look for any .pdf URL in quotes
        if not pdf_url:
            pdf_match = re.search(r'["\']([^"\']*\.pdf)["\']', resp.text, re.IGNORECASE)
            if pdf_match:
                pdf_url = pdf_match.group(1)

        # Method 3: Look in embed/iframe tags
        if not pdf_url:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup.find_all(['embed', 'iframe', 'object'], src=True):
                if '.pdf' in tag.get('src', ''):
                    pdf_url = tag['src']
                    break

        if not pdf_url:
            return False, None, "No PDF link found"

        # Fix relative URLs
        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            pdf_url = mirror + pdf_url

        # Download PDF
        pdf_resp = requests.get(pdf_url, timeout=TIMEOUT, headers={'User-Agent': USER_AGENT})
        if pdf_resp.status_code == 200 and pdf_resp.content[:4] == b'%PDF':
            return True, pdf_resp.content, "Extracted PDF"

        return False, None, "PDF download failed"

    except requests.Timeout:
        return False, None, "Timeout"
    except Exception as e:
        return False, None, str(e)[:50]

def mark_downloaded(paper_id, source='scihub'):
    """Mark paper as downloaded in database."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO download_status (paper_id, status, source, download_date)
        VALUES (?, 'downloaded', ?, datetime('now'))
    ''', (paper_id, source))
    conn.commit()
    conn.close()

def mark_unavailable(paper_id, notes=''):
    """Mark paper as unavailable."""
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO download_status (paper_id, status, source, download_date, notes)
        VALUES (?, 'unavailable', 'scihub', datetime('now'), ?)
    ''', (paper_id, notes))
    conn.commit()
    conn.close()

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Download papers from CSV via Sci-Hub")
    parser.add_argument('--input', required=True, help="Input CSV with DOIs")
    parser.add_argument('--test', type=int, help="Test with N papers")
    args = parser.parse_args()

    # Setup logging
    log_name = Path(args.input).stem
    log_file = BASE_DIR / f"logs/{log_name}_scihub.log"
    log_file.parent.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
    )

    logging.info("=" * 60)
    logging.info("SCI-HUB BATCH DOWNLOADER")
    logging.info("EDUCATIONAL/RESEARCH USE ONLY")
    logging.info("=" * 60)

    # Load CSV
    df = pd.read_csv(args.input)
    logging.info(f"Loaded {len(df)} papers from {args.input}")

    if args.test:
        df = df.head(args.test)
        logging.info(f"Test mode: {len(df)} papers")

    # Find working mirror
    mirror = None
    for m in SCIHUB_MIRRORS:
        try:
            r = requests.get(m, timeout=10, headers={'User-Agent': USER_AGENT})
            if r.status_code == 200:
                mirror = m
                logging.info(f"Using mirror: {m}")
                break
        except:
            continue

    if not mirror:
        logging.error("No Sci-Hub mirrors available!")
        return

    # Download loop
    downloaded = 0
    failed = 0

    for i, row in df.iterrows():
        doi = row['doi']
        paper_id = row.get('id')
        year = row.get('year', 'unknown')
        title = row.get('title', '')[:50]

        logging.info(f"[{i+1}/{len(df)}] {year} - {title}...")

        success, content, msg = download_from_scihub(doi, mirror)

        if success and content:
            # Save file
            filename = generate_filename(row)
            year_dir = SHARKPAPERS / str(int(year)) if year != 'unknown' else SHARKPAPERS / 'unknown_year'
            year_dir.mkdir(exist_ok=True)
            output_path = year_dir / filename

            if output_path.exists():
                logging.info(f"  Already exists: {filename}")
                if paper_id:
                    mark_downloaded(paper_id, 'scihub-exists')
                downloaded += 1
            else:
                with open(output_path, 'wb') as f:
                    f.write(content)
                logging.info(f"  Downloaded: {filename} ({len(content)/1024:.0f} KB)")
                if paper_id:
                    mark_downloaded(paper_id, 'scihub')
                downloaded += 1
        else:
            logging.warning(f"  Failed: {msg}")
            if paper_id:
                mark_unavailable(paper_id, msg)
            failed += 1

        time.sleep(DELAY)

        if (i + 1) % 20 == 0:
            logging.info(f"--- Progress: {downloaded} downloaded, {failed} failed ---")

    # Summary
    logging.info("=" * 60)
    logging.info("COMPLETE")
    logging.info(f"  Downloaded: {downloaded}")
    logging.info(f"  Failed: {failed}")
    logging.info(f"  Total: {len(df)}")
    logging.info("=" * 60)

if __name__ == '__main__':
    main()
