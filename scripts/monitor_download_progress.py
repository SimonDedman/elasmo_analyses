#!/usr/bin/env python3
"""
Monitor download progress in real-time.

Shows statistics from the download queue database.
"""

import sqlite3
import time
from pathlib import Path
from datetime import datetime
import os

# Paths
queue_db = Path("outputs/download_queue.db")

def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_queue_stats(conn):
    """Get current queue statistics."""
    cursor = conn.cursor()

    # Total counts by status
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM download_queue
        GROUP BY status
    """)
    status_counts = dict(cursor.fetchall())

    # Total by source
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM download_queue
        GROUP BY source
    """)
    source_counts = dict(cursor.fetchall())

    # Recent activity (last 100 items)
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM download_queue
        WHERE download_timestamp IS NOT NULL
            AND download_timestamp > datetime('now', '-1 hour')
        GROUP BY status
    """)
    recent_activity = dict(cursor.fetchall())

    # Success rate
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM download_queue
        WHERE status IN ('success', 'failed')
    """)
    result = cursor.fetchone()
    total_processed = result[0] if result[0] else 0
    total_success = result[1] if result[1] else 0
    total_failed = result[2] if result[2] else 0

    # Recent successes
    cursor.execute("""
        SELECT title, year
        FROM download_queue
        WHERE status = 'success'
        ORDER BY download_timestamp DESC
        LIMIT 5
    """)
    recent_successes = cursor.fetchall()

    # Recent failures
    cursor.execute("""
        SELECT title, error_message
        FROM download_queue
        WHERE status = 'failed'
        ORDER BY download_timestamp DESC
        LIMIT 5
    """)
    recent_failures = cursor.fetchall()

    # Activity log (last 10)
    cursor.execute("""
        SELECT timestamp, process, action, details
        FROM activity_log
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    activity_log = cursor.fetchall()

    return {
        'status_counts': status_counts,
        'source_counts': source_counts,
        'recent_activity': recent_activity,
        'total_processed': total_processed,
        'total_success': total_success,
        'total_failed': total_failed,
        'recent_successes': recent_successes,
        'recent_failures': recent_failures,
        'activity_log': activity_log
    }

def format_timestamp(ts_str):
    """Format timestamp for display."""
    if not ts_str:
        return "N/A"
    try:
        ts = datetime.fromisoformat(ts_str)
        return ts.strftime("%H:%M:%S")
    except:
        return ts_str[:8]

def display_stats(stats, refresh_interval=10):
    """Display statistics."""
    clear_screen()

    print("=" * 100)
    print(" " * 35 + "DOWNLOAD PROGRESS MONITOR")
    print("=" * 100)
    print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Refresh interval: {refresh_interval}s | Press Ctrl+C to exit")
    print("=" * 100)

    # Overall counts
    pending = stats['status_counts'].get('pending', 0)
    downloading = stats['status_counts'].get('downloading', 0)
    success = stats['status_counts'].get('success', 0)
    failed = stats['status_counts'].get('failed', 0)
    skipped = stats['status_counts'].get('skipped', 0)

    total = pending + downloading + success + failed + skipped

    print("\nOVERALL STATUS:")
    print(f"  Total in queue:  {total:>6,}")
    print(f"  Pending:         {pending:>6,} ({pending/total*100:5.1f}%)" if total > 0 else "  Pending:         0")
    print(f"  Downloading:     {downloading:>6,}")
    print(f"  Success:         {success:>6,} ({success/total*100:5.1f}%)" if total > 0 else "  Success:         0")
    print(f"  Failed:          {failed:>6,} ({failed/total*100:5.1f}%)" if total > 0 else "  Failed:          0")
    print(f"  Skipped:         {skipped:>6,}")

    # Success rate
    if stats['total_processed'] > 0:
        success_rate = stats['total_success'] / stats['total_processed'] * 100
        print(f"\n  Success rate:    {success_rate:>5.1f}% ({stats['total_success']:,}/{stats['total_processed']:,})")

    # By source
    existing = stats['source_counts'].get('existing', 0)
    doi_hunt = stats['source_counts'].get('doi_hunt', 0)

    print("\nBY SOURCE:")
    print(f"  Existing DOIs:   {existing:>6,}")
    print(f"  DOI Hunt:        {doi_hunt:>6,}")

    # Recent activity (last hour)
    if stats['recent_activity']:
        print("\nRECENT ACTIVITY (last hour):")
        for status, count in stats['recent_activity'].items():
            print(f"  {status:15s}: {count:>6,}")

    # Recent successes
    if stats['recent_successes']:
        print("\nRECENT SUCCESSES:")
        for title, year in stats['recent_successes'][:3]:
            title_truncated = (title[:70] + '...') if len(title) > 70 else title
            print(f"  [{year}] {title_truncated}")

    # Recent failures
    if stats['recent_failures']:
        print("\nRECENT FAILURES:")
        for title, error in stats['recent_failures'][:3]:
            title_truncated = (title[:50] + '...') if len(title) > 50 else title
            error_truncated = (error[:30] + '...') if error and len(error) > 30 else error
            print(f"  {title_truncated}")
            print(f"    Error: {error_truncated}")

    # Activity log
    if stats['activity_log']:
        print("\nACTIVITY LOG (last 10):")
        for timestamp, process, action, details in stats['activity_log'][:5]:
            ts_formatted = format_timestamp(timestamp)
            details_truncated = (details[:60] + '...') if details and len(details) > 60 else details
            print(f"  [{ts_formatted}] {process:20s} {action:15s} {details_truncated}")

    print("\n" + "=" * 100)

def monitor_loop(refresh_interval=10):
    """Main monitoring loop."""
    if not queue_db.exists():
        print(f"Error: Queue database not found at {queue_db}")
        print("Please run: ./venv/bin/python scripts/create_download_queue.py")
        return

    conn = sqlite3.connect(queue_db)

    try:
        while True:
            stats = get_queue_stats(conn)
            display_stats(stats, refresh_interval)
            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    finally:
        conn.close()

if __name__ == "__main__":
    import sys

    refresh_interval = 10
    if len(sys.argv) > 1:
        try:
            refresh_interval = int(sys.argv[1])
        except ValueError:
            print(f"Invalid refresh interval: {sys.argv[1]}")
            print("Usage: python monitor_download_progress.py [refresh_interval_seconds]")
            sys.exit(1)

    monitor_loop(refresh_interval)
