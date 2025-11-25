#!/usr/bin/env python3
"""Extract NOAA Fishery Bulletin papers for PDF download."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/papers_without_dois.csv"
OUTPUT_FILE = BASE_DIR / "outputs/noaa_fishery_bulletin_papers.csv"

# Load papers
df = pd.read_csv(INPUT_FILE)

# Filter for Fishery Bulletin specifically
fishery_bulletin = df[df['journal'].str.contains('Fishery Bulletin', case=False, na=False)].copy()

print(f"Total Fishery Bulletin papers: {len(fishery_bulletin)}")

# Show sample
print("\nSample papers:")
for idx, row in fishery_bulletin.head(10).iterrows():
    print(f"\nLit ID: {row['literature_id']}")
    print(f"Year: {row['year']}")
    print(f"Title: {row['title'][:80]}...")
    print(f"Authors: {row['authors']}")

# Save
fishery_bulletin.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Saved {len(fishery_bulletin)} papers to: {OUTPUT_FILE}")
