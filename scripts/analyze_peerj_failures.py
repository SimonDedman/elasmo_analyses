#!/usr/bin/env python3
"""Analyze PeerJ download failures and extract papers for retry."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "outputs/peerj_papers_to_download.csv"

# Load from full literature review CSV
csv_file = BASE_DIR / "outputs/literature_review_sample.csv"

if not csv_file.exists():
    print(f"❌ Could not find file: {csv_file}")
    exit(1)

df_all = pd.read_csv(csv_file)

# Filter for PeerJ papers
df = df_all[df_all['journal'].str.contains('PeerJ', case=False, na=False)].copy()

print("=" * 80)
print("PEERJ PAPERS ANALYSIS")
print("=" * 80)

print(f"\nTotal PeerJ papers in database: {len(df)}")

# Check which have DOIs
with_doi = df[df['doi'].notna()]
without_doi = df[df['doi'].isna()]

print(f"\nWith DOI: {len(with_doi)}")
print(f"Without DOI: {len(without_doi)}")

# Check which have PDF URLs
with_pdf_url = df[df['pdf_url'].notna()]
without_pdf_url = df[df['pdf_url'].isna()]

print(f"\nWith PDF URL: {len(with_pdf_url)}")
print(f"Without PDF URL: {len(without_pdf_url)}")

# Sample papers
print("\n" + "=" * 80)
print("SAMPLE PEERJ PAPERS")
print("=" * 80)

for idx, row in df.head(10).iterrows():
    print(f"\nID: {row['literature_id']}")
    print(f"Title: {row['title'][:80]}...")
    print(f"DOI: {row['doi']}")
    print(f"PDF URL: {row['pdf_url'][:80] if pd.notna(row['pdf_url']) else 'None'}...")

# Save papers for download
df.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Saved {len(df)} PeerJ papers to: {OUTPUT_FILE}")

# Analyze DOI patterns
if len(with_doi) > 0:
    print("\n" + "=" * 80)
    print("DOI PATTERNS")
    print("=" * 80)

    sample_dois = with_doi['doi'].head(10).tolist()
    for doi in sample_dois:
        print(f"  {doi}")

    # PeerJ DOI pattern: 10.7717/peerj.XXXX
    peerj_pattern = with_doi['doi'].str.contains('10.7717/peerj', na=False)
    print(f"\nPeerJ standard DOI pattern (10.7717/peerj.*): {peerj_pattern.sum()}")

print("\n" + "=" * 80)
