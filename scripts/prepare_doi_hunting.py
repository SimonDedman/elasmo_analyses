#!/usr/bin/env python3
"""
Prepare papers without DOIs for hunting.

Extract papers that lack DOIs from the main CSV and prepare for DOI hunting.
"""

import pandas as pd
from pathlib import Path

# Paths
input_csv = Path("outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv")
output_csv = Path("outputs/papers_without_doi.csv")

print("Loading shark-references database...")
df = pd.read_csv(input_csv, low_memory=False)
print(f"Total papers: {len(df):,}")

# Find papers without DOIs
no_doi = df[df['doi'].isna() | (df['doi'] == '')]
print(f"Papers without DOIs: {len(no_doi):,}")

# Select relevant columns for DOI hunting
columns_to_keep = [
    'literature_id',
    'year',
    'authors',
    'title',
    'citation',
    'pdf_url'
]

# Filter columns that exist
columns_to_keep = [col for col in columns_to_keep if col in no_doi.columns]

# Prepare output
output_df = no_doi[columns_to_keep].copy()

# Sort by year (recent first - more likely to have DOIs)
output_df = output_df.sort_values('year', ascending=False, na_position='last')

# Save
output_df.to_csv(output_csv, index=False)

print(f"\nSaved {len(output_df):,} papers to: {output_csv}")

# Summary statistics
print("\nBreakdown by decade:")
if 'year' in output_df.columns:
    for decade_start in range(2020, 1940, -10):
        decade_end = decade_start + 9
        count = len(output_df[(output_df['year'] >= decade_start) & (output_df['year'] <= decade_end)])
        if count > 0:
            print(f"  {decade_start}-{decade_end}: {count:>5,} papers")

print("\nPriority recommendations:")
print("  - Papers from 2010+ are most likely to have DOIs added")
print("  - Papers from 2000-2009 have moderate chance")
print("  - Papers pre-2000 have low chance (not digitized)")
