#!/usr/bin/env python3
"""
copy_dropbox_matches.py

Copy the 423 matched PDFs from Dropbox to organized SharkPapers folders.

Author: Simon Dedman / Claude
Date: 2025-10-22
"""

import pandas as pd
from pathlib import Path
import shutil
from tqdm import tqdm

# Paths
BASE_DIR = Path(__file__).parent.parent
MATCHES_LOG = BASE_DIR / "logs/dropbox_matches.csv"
OUTPUT_DIR = Path("/home/simon/Documents/Si Work/Papers & Books/SharkPapers")
COPY_LOG = BASE_DIR / "logs/dropbox_copy_log.csv"

print("=" * 80)
print("COPY DROPBOX MATCHED PDFs")
print("=" * 80)

# Load matches
print(f"\n📖 Loading matches from {MATCHES_LOG}...")
matches_df = pd.read_csv(MATCHES_LOG)
print(f"✅ Found {len(matches_df)} matched PDFs")

# Process each match
results = []
success_count = 0
skip_count = 0
error_count = 0

print(f"\n📁 Copying PDFs to {OUTPUT_DIR}...")

for idx, row in tqdm(matches_df.iterrows(), total=len(matches_df), desc="Copying"):
    source = Path(row['dropbox_path'])
    year = row['year'] if pd.notna(row['year']) else 'unknown_year'

    # Create destination path
    dest_dir = OUTPUT_DIR / str(year)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / source.name

    # Check if file already exists
    if dest_file.exists():
        # Check if it's the same file (same size)
        if dest_file.stat().st_size == source.stat().st_size:
            skip_count += 1
            results.append({
                'source': str(source),
                'destination': str(dest_file),
                'status': 'skipped',
                'message': 'Already exists with same size',
                'literature_id': row['literature_id'],
                'year': year
            })
            continue

    try:
        # Copy file
        shutil.copy2(source, dest_file)
        success_count += 1
        results.append({
            'source': str(source),
            'destination': str(dest_file),
            'status': 'success',
            'message': 'Copied successfully',
            'literature_id': row['literature_id'],
            'year': year
        })
    except Exception as e:
        error_count += 1
        results.append({
            'source': str(source),
            'destination': str(dest_file),
            'status': 'error',
            'message': str(e),
            'literature_id': row['literature_id'],
            'year': year
        })

# Save log
results_df = pd.DataFrame(results)
results_df.to_csv(COPY_LOG, index=False)

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"✅ Successfully copied: {success_count}")
print(f"⏭️  Skipped (already exist): {skip_count}")
print(f"❌ Errors: {error_count}")
print(f"\n📄 Log saved: {COPY_LOG}")
print("=" * 80)
