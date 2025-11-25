#!/usr/bin/env python3
"""
monitor_doi_discovery.py

Monitor the progress of DOI discovery process.

Usage:
    ./venv/bin/python scripts/monitor_doi_discovery.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).parent.parent
LOG_FILE = BASE_DIR / "logs/doi_discovery_log.csv"
FULL_LOG = BASE_DIR / "logs/doi_discovery_parallel.log"

def main():
    print("="*80)
    print("DOI DISCOVERY PROGRESS MONITOR")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Check if log exists
    if not LOG_FILE.exists():
        print("❌ Discovery log not found yet - process may not have started")
        print(f"   Looking for: {LOG_FILE}")
        return

    # Load results
    df = pd.read_csv(LOG_FILE)
    total_papers = 13911

    # Calculate statistics
    processed = len(df)
    found = len(df[df['status'] == 'found'])
    not_found = len(df[df['status'] == 'not_found'])
    errors = len(df[df['status'] == 'error'])

    # Progress
    progress_pct = (processed / total_papers) * 100
    remaining = total_papers - processed

    print(f"📊 PROGRESS")
    print(f"   Processed: {processed:,} / {total_papers:,} ({progress_pct:.1f}%)")
    print(f"   Remaining: {remaining:,}")
    print()

    print(f"✅ RESULTS")
    print(f"   DOIs found: {found:,} ({found/processed*100:.1f}% of processed)")
    print(f"   Not found: {not_found:,} ({not_found/processed*100:.1f}%)")
    if errors > 0:
        print(f"   Errors: {errors:,}")
    print()

    # Breakdown by source
    if found > 0:
        print(f"📚 SOURCES")
        sources = df[df['status'] == 'found']['source'].value_counts()
        for source, count in sources.items():
            print(f"   {source}: {count:,}")
        print()

    # Estimate completion
    if processed > 100:  # Need some data for estimate
        # Get timestamps
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
            print(f"   Processing rate: {rate*60:.1f} papers/minute")
            print(f"   Estimated completion: {completion_time.strftime('%H:%M:%S')}")
            print(f"   Time remaining: {eta}")
            print()

    # Recent discoveries
    recent_found = df[df['status'] == 'found'].tail(5)
    if len(recent_found) > 0:
        print(f"🔍 RECENT DISCOVERIES (last 5)")
        for idx, row in recent_found.iterrows():
            print(f"   • {row['doi'][:50]} ({row['source']})")
        print()

    # Check if process is still running
    import subprocess
    try:
        result = subprocess.run(['pgrep', '-f', 'discover_dois_parallel.py'],
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
    print("="*80)
    print("To view live log: tail -f logs/doi_discovery_parallel.log")
    print("To reattach screen: screen -r doi_discovery")
    print("="*80)

if __name__ == "__main__":
    main()
