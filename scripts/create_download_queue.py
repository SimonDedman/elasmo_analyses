#!/usr/bin/env python3
"""
Create and initialize the download queue database.

This database serves as a shared queue between:
1. DOI hunting process (adds DOIs to queue)
2. Sci-Hub downloader (processes DOIs from queue)
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# Paths
queue_db = Path("outputs/download_queue.db")
shark_csv = Path("outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv")

def create_queue_database():
    """Create the download queue database."""

    print("Creating download queue database...")

    # Remove existing database if present
    if queue_db.exists():
        queue_db.unlink()
        print(f"Removed existing database: {queue_db}")

    # Create database and tables
    conn = sqlite3.connect(queue_db)
    cursor = conn.cursor()

    # Main queue table
    cursor.execute("""
        CREATE TABLE download_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            literature_id TEXT,
            doi TEXT UNIQUE NOT NULL,
            year INTEGER,
            authors TEXT,
            title TEXT,
            source TEXT,  -- 'existing' or 'doi_hunt'
            priority INTEGER DEFAULT 1,  -- Higher = more recent papers
            status TEXT DEFAULT 'pending',  -- pending, downloading, success, failed, skipped
            added_timestamp TEXT,
            download_timestamp TEXT,
            pdf_path TEXT,
            error_message TEXT
        )
    """)

    # Index for efficient queries
    cursor.execute("CREATE INDEX idx_status ON download_queue(status)")
    cursor.execute("CREATE INDEX idx_priority ON download_queue(priority DESC)")
    cursor.execute("CREATE INDEX idx_doi ON download_queue(doi)")

    # Progress tracking table
    cursor.execute("""
        CREATE TABLE progress (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_timestamp TEXT
        )
    """)

    # Log table
    cursor.execute("""
        CREATE TABLE activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            process TEXT,  -- 'doi_hunter' or 'sci_hub_downloader'
            action TEXT,
            details TEXT
        )
    """)

    conn.commit()
    print("✓ Database schema created")

    return conn

def populate_existing_dois(conn):
    """Populate queue with existing DOIs from shark-references CSV."""

    print("\nLoading shark-references CSV...")
    df = pd.read_csv(shark_csv, low_memory=False)
    print(f"Total papers: {len(df):,}")

    # Filter papers with DOIs
    with_doi = df[df['doi'].notna() & (df['doi'] != '')].copy()
    print(f"Papers with DOIs: {len(with_doi):,}")

    # Prepare data for insertion
    records = []
    for _, row in with_doi.iterrows():
        # Normalize DOI
        doi = str(row['doi']).strip()
        doi = doi.replace('https://doi.org/', '')
        doi = doi.replace('http://doi.org/', '')
        doi = doi.replace('doi.org/', '')
        doi = doi.replace('DOI:', '')
        doi = doi.replace('doi:', '')

        # Priority based on year (more recent = higher priority)
        year = row.get('year', None)
        if pd.notna(year):
            priority = int(year) if year >= 1950 else 1950
        else:
            priority = 1950

        records.append({
            'literature_id': str(row.get('literature_id', '')),
            'doi': doi,
            'year': int(year) if pd.notna(year) else None,
            'authors': str(row.get('authors', ''))[:500],  # Truncate long author lists
            'title': str(row.get('title', ''))[:500],
            'source': 'existing',
            'priority': priority,
            'status': 'pending',
            'added_timestamp': datetime.now().isoformat()
        })

    # Insert into database
    print(f"\nInserting {len(records):,} DOIs into queue...")
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT OR IGNORE INTO download_queue
        (literature_id, doi, year, authors, title, source, priority, status, added_timestamp)
        VALUES (:literature_id, :doi, :year, :authors, :title, :source, :priority, :status, :added_timestamp)
    """, records)

    conn.commit()

    inserted = cursor.rowcount
    print(f"✓ Inserted {inserted:,} DOIs")

    # Update progress
    cursor.execute("""
        INSERT INTO progress (key, value, updated_timestamp)
        VALUES ('initial_dois_loaded', ?, ?)
    """, (str(inserted), datetime.now().isoformat()))

    conn.commit()

    return inserted

def log_activity(conn, process, action, details):
    """Log activity to database."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity_log (timestamp, process, action, details)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().isoformat(), process, action, details))
    conn.commit()

def show_queue_stats(conn):
    """Display queue statistics."""
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("DOWNLOAD QUEUE STATISTICS")
    print("=" * 80)

    # Total count
    cursor.execute("SELECT COUNT(*) FROM download_queue")
    total = cursor.fetchone()[0]
    print(f"\nTotal DOIs in queue: {total:,}")

    # By status
    print("\nBy status:")
    cursor.execute("SELECT status, COUNT(*) FROM download_queue GROUP BY status")
    for status, count in cursor.fetchall():
        print(f"  {status:15s}: {count:>6,}")

    # By source
    print("\nBy source:")
    cursor.execute("SELECT source, COUNT(*) FROM download_queue GROUP BY source")
    for source, count in cursor.fetchall():
        print(f"  {source:15s}: {count:>6,}")

    # By decade
    print("\nBy decade (existing DOIs):")
    cursor.execute("""
        SELECT
            (year / 10) * 10 as decade,
            COUNT(*) as count
        FROM download_queue
        WHERE source = 'existing' AND year IS NOT NULL
        GROUP BY decade
        ORDER BY decade DESC
    """)
    for decade, count in cursor.fetchall():
        print(f"  {int(decade)}s: {count:>6,}")

    # Priority distribution
    print("\nPriority distribution:")
    cursor.execute("""
        SELECT
            CASE
                WHEN priority >= 2020 THEN '2020+'
                WHEN priority >= 2010 THEN '2010-2019'
                WHEN priority >= 2000 THEN '2000-2009'
                WHEN priority >= 1990 THEN '1990-1999'
                ELSE 'Pre-1990'
            END as period,
            COUNT(*) as count
        FROM download_queue
        GROUP BY period
        ORDER BY MIN(priority) DESC
    """)
    for period, count in cursor.fetchall():
        print(f"  {period:15s}: {count:>6,}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    # Create database
    conn = create_queue_database()

    # Populate with existing DOIs
    inserted = populate_existing_dois(conn)

    # Log initialization
    log_activity(conn, 'system', 'initialize', f'Queue created with {inserted:,} existing DOIs')

    # Show statistics
    show_queue_stats(conn)

    print(f"\n✓ Download queue ready: {queue_db}")
    print("\nNext steps:")
    print("  1. Run DOI hunter: ./venv/bin/python scripts/doi_hunter_daemon.py")
    print("  2. Run Sci-Hub downloader: ./venv/bin/python scripts/scihub_downloader_daemon.py")
    print("  3. Monitor progress: ./venv/bin/python scripts/monitor_download_progress.py")

    conn.close()
