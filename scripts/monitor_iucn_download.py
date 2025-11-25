#!/usr/bin/env python3
"""
monitor_iucn_download.py

Monitor the progress of IUCN PDF download process.

Usage:
    ./venv/bin/python scripts/monitor_iucn_download.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).parent.parent
LOG_FILE = BASE_DIR / "logs/iucn_browser_download_log.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"

def main():
    print("=" * 80)
    print("IUCN DOWNLOAD PROGRESS MONITOR")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Check if log exists
    if not LOG_FILE.exists():
        print("❌ Download log not found yet - process may not have started")
        print(f"   Looking for: {LOG_FILE}")
        return

    # Load results
    df = pd.read_csv(LOG_FILE)
    total_species = 1098

    # Calculate statistics
    processed = len(df)
    success = len(df[df['status'] == 'success'])
    already_exists = len(df[df['status'] == 'already_exists'])
    not_found = len(df[df['status'] == 'not_found_in_search'])
    timeouts = len(df[df['status'] == 'download_timeout'])
    errors = len(df[df['status'] == 'error'])

    total_pdfs = success + already_exists

    # Progress
    progress_pct = (processed / total_species) * 100
    remaining = total_species - processed

    print(f"📊 PROGRESS")
    print(f"   Processed: {processed:,} / {total_species:,} ({progress_pct:.1f}%)")
    print(f"   Remaining: {remaining:,}")
    print()

    print(f"✅ RESULTS")
    print(f"   PDFs downloaded: {total_pdfs:,} ({total_pdfs/processed*100:.1f}% of processed)")
    print(f"   New downloads: {success:,}")
    print(f"   Already existed: {already_exists:,}")
    print()

    if not_found > 0 or timeouts > 0 or errors > 0:
        print(f"⚠️  ISSUES")
        if not_found > 0:
            print(f"   Not found in search: {not_found:,}")
        if timeouts > 0:
            print(f"   Download timeouts: {timeouts:,}")
        if errors > 0:
            print(f"   Errors: {errors:,}")
        print()

    # Estimate completion
    if processed > 25:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        start_time = df['timestamp'].min()
        current_time = df['timestamp'].max()

        elapsed = (current_time - start_time).total_seconds()
        rate = processed / elapsed if elapsed > 0 else 0

        if rate > 0:
            eta_seconds = remaining / rate
            eta = timedelta(seconds=int(eta_seconds))
            completion_time = datetime.now() + eta

            print(f"⏱️  TIMING")
            print(f"   Processing rate: {rate*3600:.1f} species/hour")
            print(f"   Average time/species: {elapsed/processed:.1f} seconds")
            print(f"   Estimated completion: {completion_time.strftime('%H:%M:%S')}")
            print(f"   Time remaining: {eta}")
            print()

    # Recent downloads
    recent = df[df['status'] == 'success'].tail(5)
    if len(recent) > 0:
        print(f"🔍 RECENT DOWNLOADS (last 5)")
        for idx, row in recent.iterrows():
            size_mb = row['size_bytes'] / (1024 * 1024)
            print(f"   • {row['species_name']} ({size_mb:.1f} MB)")
        print()

    # Check if process is still running
    import subprocess
    try:
        result = subprocess.run(['pgrep', '-f', 'download_iucn_browser.py'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Process is RUNNING")
            pids = result.stdout.strip().split('\n')
            print(f"   PID(s): {', '.join(pids)}")
        else:
            print("⚠️  Process not found - may have completed or stopped")
    except:
        pass

    print()
    print("=" * 80)
    print("To view live log: tail -f logs/iucn_full_run.log")
    print("To view download log: tail -f logs/iucn_browser_download_log.csv")
    print("=" * 80)

if __name__ == "__main__":
    main()
