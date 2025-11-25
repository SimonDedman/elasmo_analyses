#!/usr/bin/env python3
"""
monitor_peerj_download.py

Monitor the progress of PeerJ PDF download process.

Usage:
    ./venv/bin/python scripts/monitor_peerj_download.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).parent.parent
LOG_FILE = BASE_DIR / "logs/peerj_browser_download_log.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"

def main():
    print("=" * 80)
    print("PEERJ DOWNLOAD PROGRESS MONITOR")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Check if log exists
    if not LOG_FILE.exists():
        print("❌ Download log not found yet - process may not have started")
        print(f"   Looking for: {LOG_FILE}")
        return

    # Load results
    df = pd.read_csv(LOG_FILE)
    total_papers = 89

    # Calculate statistics
    processed = len(df)
    success = len(df[df['status'] == 'success'])
    already_exists = len(df[df['status'] == 'already_exists'])
    timeouts = len(df[df['status'] == 'download_timeout'])
    click_errors = len(df[df['status'] == 'click_error'])
    no_pdf_link = len(df[df['status'] == 'no_pdf_link'])

    total_pdfs = success + already_exists

    # Progress
    progress_pct = (processed / total_papers) * 100
    remaining = total_papers - processed

    print(f"📊 PROGRESS")
    print(f"   Processed: {processed:,} / {total_papers:,} ({progress_pct:.1f}%)")
    print(f"   Remaining: {remaining:,}")
    print()

    print(f"✅ RESULTS")
    print(f"   PDFs downloaded: {total_pdfs:,} ({total_pdfs/processed*100:.1f}% of processed)")
    print(f"   New downloads: {success:,}")
    print(f"   Already existed: {already_exists:,}")
    print()

    if timeouts > 0 or click_errors > 0 or no_pdf_link > 0:
        print(f"⚠️  ISSUES")
        if timeouts > 0:
            print(f"   Download timeouts: {timeouts:,}")
        if click_errors > 0:
            print(f"   Click errors: {click_errors:,}")
        if no_pdf_link > 0:
            print(f"   No PDF link found: {no_pdf_link:,}")
        print()

    # Estimate completion
    if processed > 5:
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
            print(f"   Processing rate: {rate*3600:.1f} papers/hour")
            print(f"   Average time/paper: {elapsed/processed:.1f} seconds")
            print(f"   Estimated completion: {completion_time.strftime('%H:%M:%S')}")
            print(f"   Time remaining: {eta}")
            print()

    # Recent downloads
    recent = df[df['status'] == 'success'].tail(5)
    if len(recent) > 0:
        print(f"🔍 RECENT DOWNLOADS (last 5)")
        for idx, row in recent.iterrows():
            size_mb = row['size_bytes'] / (1024 * 1024)
            article_id = row['doi'].split('.')[-1] if pd.notna(row['doi']) else 'unknown'
            print(f"   • PeerJ {article_id} ({size_mb:.1f} MB)")
        print()

    # Check if process is still running
    import subprocess
    try:
        result = subprocess.run(['pgrep', '-f', 'download_peerj_browser.py'],
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
    print("To view live log: tail -f logs/peerj_full_run.log")
    print("To view download log: tail -f logs/peerj_browser_download_log.csv")
    print("=" * 80)

if __name__ == "__main__":
    main()
