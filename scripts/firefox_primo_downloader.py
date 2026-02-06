#!/usr/bin/env python3
"""
Semi-automated Primo/Elsevier downloader using Firefox.

Opens each search URL in Firefox, waits for you to click Download PDF,
then moves to the next one.

Usage:
    ./venv/bin/python scripts/firefox_primo_downloader.py
"""

import subprocess
import time
import sqlite3
import urllib.parse
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "database" / "download_tracker.db"

PRIMO_BASE = "https://fiu-flvc.primo.exlibrisgroup.com/discovery/search"
VID = "01FALSC_FIU:FIU"


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


def open_in_firefox(url):
    """Open URL in Firefox (new tab in existing window)."""
    subprocess.run(['firefox', '--new-tab', url], capture_output=True)


def main():
    papers = get_pending_elsevier()
    print(f"Found {len(papers)} Elsevier papers to download")
    print()
    print("INSTRUCTIONS:")
    print("1. Make sure Firefox is open and you're logged into FIU Library")
    print("2. For each paper, the Primo search will open")
    print("3. Click 'Download PDF' or the LibKey link")
    print("4. Press Enter here to move to next paper")
    print("5. Press 's' + Enter to skip, 'q' + Enter to quit")
    print()

    input("Press Enter to start...")

    downloaded = 0
    skipped = 0

    for i, (paper_id, doi, year, title, authors) in enumerate(papers):
        first_author = (authors or "Unknown").split(';')[0].split(',')[0].strip().split()[-1]
        title_short = (title or "No title")[:60]

        print(f"\n[{i+1}/{len(papers)}] {year} - {first_author}: {title_short}")
        print(f"  DOI: {doi}")

        # Build Primo search URL
        search_url = f"{PRIMO_BASE}?query=any,contains,{urllib.parse.quote(doi)}&vid={VID}&lang=en"

        # Open in Firefox
        print(f"  Opening Primo search...")
        open_in_firefox(search_url)

        # Wait for user
        response = input("  Press Enter when done (s=skip, q=quit): ").strip().lower()

        if response == 'q':
            print("Quitting...")
            break
        elif response == 's':
            skipped += 1
            print("  Skipped")
        else:
            downloaded += 1
            print(f"  Done! ({downloaded} downloaded)")

    print()
    print("=" * 50)
    print(f"Downloaded: {downloaded}")
    print(f"Skipped: {skipped}")
    print("=" * 50)
    print()
    print("Run Claude to process the Downloads folder when ready.")


if __name__ == "__main__":
    main()
