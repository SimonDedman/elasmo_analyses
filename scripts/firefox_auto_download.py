#!/usr/bin/env python3
"""
Automated Firefox downloader for Elsevier papers via FIU Primo.

Uses xdotool to control Firefox - opens each Primo search,
uses keyboard navigation to find and click Download PDF links.

Usage:
    ./venv/bin/python scripts/firefox_auto_download.py --count 20
"""

import subprocess
import time
import sqlite3
import urllib.parse
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "database" / "download_tracker.db"

PRIMO_BASE = "https://fiu-flvc.primo.exlibrisgroup.com/discovery/search"
VID = "01FALSC_FIU:FIU"

# Timing settings (adjust if too fast/slow)
PAGE_LOAD_WAIT = 5  # seconds to wait for Primo to load
DOWNLOAD_WAIT = 4   # seconds to wait after clicking download
BETWEEN_PAPERS = 2  # seconds between papers


def run_xdotool(*args):
    """Run xdotool command."""
    subprocess.run(['xdotool'] + list(args), capture_output=True)


def type_text(text):
    """Type text using xdotool."""
    subprocess.run(['xdotool', 'type', '--', text], capture_output=True)


def press_key(key):
    """Press a key using xdotool."""
    subprocess.run(['xdotool', 'key', key], capture_output=True)


def open_url_in_firefox(url):
    """Open URL in new Firefox tab."""
    subprocess.run(['firefox', '--new-tab', url], capture_output=True)
    time.sleep(1)
    # Focus the Firefox window
    run_xdotool('search', '--name', 'Mozilla Firefox', 'windowactivate')
    time.sleep(0.5)


def close_tab():
    """Close current Firefox tab with Ctrl+W."""
    press_key('ctrl+w')
    time.sleep(0.5)


def try_find_and_click_download():
    """
    Try to find and click Download PDF or LibKey link using Tab navigation.
    Tab moves between focusable elements (links, buttons).
    """
    # First, make sure we're at the top of the page
    press_key('ctrl+Home')
    time.sleep(0.3)

    # Tab through focusable elements, looking for PDF-related links
    # User confirmed: 17 tabs after Ctrl+Home reaches Download PDF
    for i in range(17):
        press_key('Tab')
        time.sleep(0.1)

    # Now press Enter to click whatever link is focused
    # (Hopefully it's the Download PDF or LibKey link)
    press_key('Return')
    time.sleep(2)

    # Check if a new tab opened or if we're on a PDF page
    # If so, we might need to handle the PDF

    return True


def try_direct_pdf_click():
    """
    Alternative: Use accesskey or search within page.
    """
    # Try clicking via quick find (/ in Firefox)
    press_key('slash')  # Quick find
    time.sleep(0.2)
    type_text('PDF')
    time.sleep(0.3)
    press_key('Escape')
    time.sleep(0.2)
    press_key('Return')
    time.sleep(1)
    return True


def get_pending_elsevier():
    """Get Elsevier papers not yet downloaded."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.doi, p.year, p.title, p.authors
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.paper_id IS NULL
          AND p.doi LIKE '10.1016/%'
        ORDER BY p.year DESC
    ''')
    papers = cursor.fetchall()
    conn.close()
    return papers


def process_paper(doi, title, year, authors, page_load_wait=5):
    """Process a single paper - open Primo, find PDF, download."""
    first_author = (authors or "Unknown").split(';')[0].split(',')[0].strip().split()[-1]
    title_short = (title or "")[:50]

    print(f"  {year} {first_author}: {title_short}...")

    # Build and open Primo search URL
    search_url = f"{PRIMO_BASE}?query=any,contains,{urllib.parse.quote(doi)}&vid={VID}&lang=en"
    open_url_in_firefox(search_url)

    # Wait for page to load
    print(f"    Waiting for page to load...")
    time.sleep(page_load_wait)

    # Try to find and click download link using Tab navigation
    print(f"    Tabbing to Download PDF link...")
    try_find_and_click_download()
    time.sleep(DOWNLOAD_WAIT)

    # If we ended up on a PDF page, might need to save it
    # Try Ctrl+S to save
    press_key('ctrl+s')
    time.sleep(1)
    press_key('Return')  # Confirm save dialog
    time.sleep(2)

    # Check if we're still on Primo or moved to PDF
    # (We can't easily check, so just continue)

    # Close the tab
    print(f"    Closing tab...")
    close_tab()

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=10, help='Number of papers to process')
    parser.add_argument('--start', type=int, default=0, help='Start from paper N')
    parser.add_argument('--wait', type=float, default=5, help='Page load wait time')
    args = parser.parse_args()

    page_load_wait = args.wait

    papers = get_pending_elsevier()

    if args.start:
        papers = papers[args.start:]
    papers = papers[:args.count]

    print("=" * 60)
    print("Firefox Automated Primo Downloader")
    print("=" * 60)
    print(f"Papers to process: {len(papers)}")
    print(f"Page load wait: {page_load_wait}s")
    print()
    print("BEFORE STARTING:")
    print("1. Firefox must be open")
    print("2. You must be logged into FIU Library")
    print("3. Keep Firefox in focus (don't click away)")
    print()

    response = input("Press Enter to start, or 'q' to quit: ")
    if response.lower() == 'q':
        return

    print()
    print("Starting... (don't touch mouse/keyboard!)")
    print()

    success = 0
    for i, (paper_id, doi, year, title, authors) in enumerate(papers):
        print(f"[{i+1}/{len(papers)}]", end=" ")

        try:
            process_paper(doi, title, year, authors, page_load_wait)
            success += 1
        except KeyboardInterrupt:
            print("\nInterrupted!")
            break
        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(BETWEEN_PAPERS)

    print()
    print("=" * 60)
    print(f"Processed: {success}/{len(papers)}")
    print("=" * 60)
    print()
    print("Check Downloads folder for PDFs.")
    print("Run Claude to process and organize them.")


if __name__ == "__main__":
    main()
