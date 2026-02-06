#!/usr/bin/env python3
"""
Assisted Firefox downloader - opens each Primo search, you click Download PDF,
press Enter to continue to next.

Much faster than fully manual (1 click + Enter per paper instead of 2 clicks).
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


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=0, help='Number of papers (0=all)')
    parser.add_argument('--start', type=int, default=0, help='Start from paper N')
    args = parser.parse_args()

    papers = get_pending_elsevier()

    if args.start:
        papers = papers[args.start:]
    if args.count:
        papers = papers[:args.count]

    print("=" * 60)
    print(f"Assisted Elsevier Downloader - {len(papers)} papers")
    print("=" * 60)
    print()
    print("For each paper:")
    print("  1. Primo search opens in Firefox")
    print("  2. YOU click 'Download PDF' or LibKey link")
    print("  3. Press Enter here to open next paper")
    print()
    print("Commands: Enter=next, s=skip, q=quit")
    print()

    input("Press Enter to start...")

    downloaded = 0
    skipped = 0

    for i, (paper_id, doi, year, title, authors) in enumerate(papers):
        first_author = (authors or "Unknown").split(';')[0].split(',')[0].strip().split()[-1]
        title_short = (title or "")[:55]

        print(f"\n[{i+1}/{len(papers)}] {year} {first_author}: {title_short}")

        # Open Primo search
        search_url = f"{PRIMO_BASE}?query=any,contains,{urllib.parse.quote(doi)}&vid={VID}&lang=en"
        subprocess.Popen(['firefox', '--new-tab', search_url],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for user
        cmd = input("  → Click Download PDF, then Enter (s=skip, q=quit): ").strip().lower()

        if cmd == 'q':
            print("Quitting...")
            break
        elif cmd == 's':
            skipped += 1
        else:
            downloaded += 1

    print()
    print("=" * 60)
    print(f"Done: {downloaded} downloaded, {skipped} skipped")
    print("=" * 60)
    print()
    print("Tell Claude to process Downloads folder when ready.")


if __name__ == "__main__":
    main()
