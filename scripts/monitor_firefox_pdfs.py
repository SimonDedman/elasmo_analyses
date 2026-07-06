#!/usr/bin/env python3
"""
monitor_firefox_pdfs.py

Monitor Firefox cache for PDFs and automatically extract/rename them.

Run this script BEFORE clicking through the manual download HTML files.
It will watch the Firefox cache directory and extract any PDF files that appear.

Usage:
    python3 scripts/monitor_firefox_pdfs.py

    # Or specify a different cache location
    python3 scripts/monitor_firefox_pdfs.py --cache-dir ~/snap/firefox/common/.cache

Author: Simon Dedman
Date: 2025-10-21
Version: 1.0
"""

import time
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import subprocess

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = Path("/home/simon/Documents/Si Work/Papers & Books/SharkPapers")
CACHE_LOG = BASE_DIR / "logs/firefox_cache_monitor.csv"

# Firefox cache roots, in priority order (DEB/apt first, then snap, then flatpak).
# The correct one is auto-detected in find_cache_dir(); override with --cache-dir.
FIREFOX_CACHE_ROOTS = [
    Path.home() / ".cache/mozilla/firefox",                                  # DEB/apt (default here)
    Path.home() / "snap/firefox/common/.cache/mozilla/firefox",              # snap
    Path.home() / ".var/app/org.mozilla.firefox/cache/mozilla/firefox",      # flatpak
]
# Back-compat: first existing root (used only if --cache-dir not given).
FIREFOX_CACHE = next((r for r in FIREFOX_CACHE_ROOTS if r.exists()), FIREFOX_CACHE_ROOTS[0])

# ============================================================================
# PDF DETECTION
# ============================================================================

def is_pdf(file_path):
    """
    Check if file is a PDF by reading magic bytes.

    Args:
        file_path: Path to file

    Returns:
        True if file is PDF, False otherwise
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(5)
            return header == b'%PDF-'
    except Exception:
        return False

def get_pdf_metadata(file_path):
    """
    Extract title and author from PDF metadata using pdfinfo.

    Args:
        file_path: Path to PDF file

    Returns:
        dict with 'title' and 'author' keys
    """
    try:
        result = subprocess.run(
            ['pdfinfo', str(file_path)],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            metadata = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip().lower()] = value.strip()

            return {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', '')
            }
    except Exception:
        pass

    return {'title': '', 'author': ''}

# ============================================================================
# MONITORING
# ============================================================================

def find_cache_dir():
    """Find the active Firefox cache 'entries' dir across all install types.

    Scans every candidate root (DEB/snap/flatpak) for profiles, then picks the
    profile whose cache2 was modified most recently i.e. the one actually in use
    (a machine can have several profiles; the first glob hit is often stale)."""
    profiles = []
    for root in FIREFOX_CACHE_ROOTS:
        if root.exists():
            profiles.extend(root.glob("*/cache2/entries"))

    if not profiles:
        roots = "\n  ".join(str(r) for r in FIREFOX_CACHE_ROOTS)
        print(f"❌ Firefox cache not found in any of:\n  {roots}")
        print("   (pass --cache-dir /path/to/.cache if your profile lives elsewhere)")
        return None

    # Most recently modified cache2 = the active profile.
    cache_dir = max(profiles, key=lambda p: p.parent.stat().st_mtime)
    if len(profiles) > 1:
        print(f"ℹ️  {len(profiles)} Firefox profiles found; using most recent.")
    print(f"✅ Found cache directory: {cache_dir}")
    return cache_dir

def monitor_cache(cache_dir, check_interval=2):
    """
    Monitor Firefox cache for new PDF files.

    Args:
        cache_dir: Path to Firefox cache entries directory
        check_interval: Seconds between checks
    """
    print("=" * 80)
    print("FIREFOX PDF CACHE MONITOR")
    print("=" * 80)
    print(f"\n📂 Monitoring: {cache_dir}")
    print(f"💾 Output: {OUTPUT_DIR}")
    print(f"\n⏱️  Checking every {check_interval} seconds...")
    print("Press Ctrl+C to stop\n")

    # Track seen files
    seen_files = set(cache_dir.glob("*"))
    pdf_count = 0

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Prepare log file
    CACHE_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not CACHE_LOG.exists():
        with open(CACHE_LOG, 'w') as f:
            f.write("timestamp,cache_file,output_file,file_size,title,author\n")

    try:
        while True:
            time.sleep(check_interval)

            # Get current files
            current_files = set(cache_dir.glob("*"))

            # Check for new files
            new_files = current_files - seen_files

            for file_path in new_files:
                # Skip if too small (likely not a PDF)
                if file_path.stat().st_size < 1024:
                    continue

                # Check if it's a PDF
                if is_pdf(file_path):
                    pdf_count += 1

                    # Get PDF metadata
                    metadata = get_pdf_metadata(file_path)
                    title = metadata.get('title', '')[:50]  # Truncate long titles
                    author = metadata.get('author', '')[:30]

                    # Generate output filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
                    safe_title = safe_title.strip() or 'untitled'

                    output_filename = f"{timestamp}_{pdf_count:04d}_{safe_title}.pdf"
                    output_path = OUTPUT_DIR / output_filename

                    # Copy PDF
                    try:
                        shutil.copy2(file_path, output_path)
                        file_size = output_path.stat().st_size

                        print(f"\n✅ PDF #{pdf_count} extracted:")
                        print(f"   📄 Title: {title or '(no title)'}")
                        print(f"   👤 Author: {author or '(no author)'}")
                        print(f"   💾 Size: {file_size / 1024 / 1024:.2f} MB")
                        print(f"   📁 Saved: {output_filename}")

                        # Log extraction
                        with open(CACHE_LOG, 'a') as f:
                            f.write(f"{datetime.now().isoformat()},"
                                   f"{file_path.name},"
                                   f"{output_filename},"
                                   f"{file_size},"
                                   f"\"{title}\","
                                   f"\"{author}\"\n")

                    except Exception as e:
                        print(f"❌ Error copying PDF: {e}")

            seen_files = current_files

    except KeyboardInterrupt:
        print(f"\n\n🛑 Monitoring stopped.")
        print(f"✅ Total PDFs extracted: {pdf_count}")
        print(f"📂 Output directory: {OUTPUT_DIR}")
        print(f"📋 Log file: {CACHE_LOG}")
        print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description='Monitor Firefox cache for PDFs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--cache-dir',
        type=Path,
        help='Firefox cache directory (auto-detected if not specified)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=2,
        help='Check interval in seconds (default: 2)'
    )

    args = parser.parse_args()

    # Find cache directory
    cache_dir = args.cache_dir
    if not cache_dir:
        cache_dir = find_cache_dir()
        if not cache_dir:
            return

    if not cache_dir.exists():
        print(f"❌ Cache directory not found: {cache_dir}")
        return

    # Start monitoring
    monitor_cache(cache_dir, args.interval)

if __name__ == "__main__":
    main()
