#!/usr/bin/env python3
"""Check download_queue database structure and PeerJ papers."""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_FILE = BASE_DIR / "outputs/download_queue.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Show tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:")
for table in cursor.fetchall():
    print(f"  {table[0]}")

# Show download_queue schema
print("\ndownload_queue schema:")
cursor.execute("PRAGMA table_info(download_queue)")
for col in cursor.fetchall():
    print(f"  {col[1]:20s} {col[2]}")

# Count rows
cursor.execute("SELECT COUNT(*) FROM download_queue")
print(f"\nTotal rows in download_queue: {cursor.fetchone()[0]:,}")

# Sample rows
print("\nSample rows (first 3):")
cursor.execute("SELECT * FROM download_queue LIMIT 3")
for row in cursor.fetchall():
    print(f"  {row}")

# Check if journal column exists
cursor.execute("PRAGMA table_info(download_queue)")
columns = [col[1] for col in cursor.fetchall()]

if 'journal' in columns:
    cursor.execute("SELECT COUNT(*) FROM download_queue WHERE journal LIKE '%PeerJ%'")
    print(f"\nPeerJ papers: {cursor.fetchone()[0]:,}")
else:
    print("\n❌ No 'journal' column found")
    print(f"Available columns: {', '.join(columns)}")

conn.close()
