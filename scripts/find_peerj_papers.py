#!/usr/bin/env python3
"""Find PeerJ papers in download_queue database."""

import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_FILE = BASE_DIR / "outputs/download_queue.db"
OUTPUT_FILE = BASE_DIR / "outputs/peerj_papers_to_download.csv"

conn = sqlite3.connect(DB_FILE)

# PeerJ DOI pattern: 10.7717/peerj.*
query = """
SELECT
    literature_id,
    doi,
    year,
    authors,
    title,
    status,
    pdf_path,
    error_message
FROM download_queue
WHERE doi LIKE '10.7717/peerj.%'
ORDER BY year DESC
"""

df = pd.read_sql_query(query, conn)
conn.close()

print("=" * 80)
print("PEERJ PAPERS ANALYSIS")
print("=" * 80)

print(f"\nTotal PeerJ papers found: {len(df)}")

if len(df) == 0:
    print("❌ No PeerJ papers found in download queue")
    exit(0)

# Analyze by status
print("\nBreakdown by download status:")
for status, group in df.groupby('status'):
    print(f"  {status:20s}: {len(group):>5}")

# Papers without PDFs
without_pdf = df[df['pdf_path'].isna()]
print(f"\n📊 Papers without PDFs: {len(without_pdf)}")

# Failed downloads
failed = df[df['status'] == 'failed']
print(f"📊 Failed downloads: {len(failed)}")

# Sample failed papers
if len(failed) > 0:
    print("\nSample failed papers:")
    for idx, row in failed.head(5).iterrows():
        article_id = row['doi'].split('.')[-1] if pd.notna(row['doi']) else 'unknown'
        print(f"\n  Literature ID: {row['literature_id']}")
        print(f"  DOI: {row['doi']}")
        print(f"  Article ID: {article_id}")
        print(f"  Title: {row['title'][:70]}...")
        print(f"  Status: {row['status']}")
        print(f"  Error: {row['error_message']}")
        print(f"  Expected PDF: https://peerj.com/articles/{article_id}.pdf")

# Save papers for download
download_list = df[df['pdf_path'].isna()].copy()
download_list['pdf_url'] = download_list['doi'].apply(
    lambda x: f"https://peerj.com/articles/{x.split('.')[-1]}.pdf" if pd.notna(x) else None
)

download_list.to_csv(OUTPUT_FILE, index=False)

print(f"\n✅ Saved {len(download_list)} PeerJ papers for download to: {OUTPUT_FILE}")
print("\nPeerJ PDF URL pattern: https://peerj.com/articles/{article_id}.pdf")
print("Example: DOI 10.7717/peerj.18787 → https://peerj.com/articles/18787.pdf")

print("\n" + "=" * 80)
