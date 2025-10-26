#!/usr/bin/env python3
"""
download_semantic_dois_via_scihub.py

Download the 19 DOIs discovered by Semantic Scholar via Sci-Hub.

This script processes the DOIs found during Semantic Scholar search
that weren't available as direct PDFs from Semantic Scholar.

Author: Simon Dedman / Claude
Date: 2025-10-22
"""

import pandas as pd
from pathlib import Path
import sys

# Add parent for imports
sys.path.append(str(Path(__file__).parent))
from download_via_scihub import (
    check_scihub_availability,
    download_from_scihub,
    get_pdf_filename,
    OUTPUT_DIR
)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
SEMANTIC_DOIS = BASE_DIR / "logs/semantic_scholar_dois_for_scihub.csv"
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
OUTPUT_LOG = BASE_DIR / "logs/semantic_scholar_scihub_log.csv"

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("SEMANTIC SCHOLAR DOIs → SCI-HUB DOWNLOADER")
    print("=" * 80)
    print("⚠️  EDUCATIONAL/RESEARCH USE ONLY")
    print("=" * 80)

    # Check if DOI file exists
    if not SEMANTIC_DOIS.exists():
        print(f"\n❌ DOI file not found: {SEMANTIC_DOIS}")
        print("Run the extraction script first to create this file.")
        return

    # Check Sci-Hub availability
    available_mirrors = check_scihub_availability()

    if not available_mirrors:
        print("\n❌ No Sci-Hub mirrors are available. Exiting.")
        return

    mirror = available_mirrors[0]
    print(f"\n✅ Using mirror: {mirror}")

    # Load DOIs
    print(f"\n📖 Loading DOIs from Semantic Scholar...")
    dois_df = pd.read_csv(SEMANTIC_DOIS)
    print(f"✅ Found {len(dois_df)} DOIs to process")

    # Load database to get metadata
    print(f"\n📖 Loading database for metadata...")
    db = pd.read_parquet(DATABASE_PARQUET)

    # Fix data types for merge - handle NaN and convert to int
    # Use pd.to_numeric to handle string floats like '34947.0', then convert to int
    dois_df['literature_id'] = pd.to_numeric(dois_df['literature_id'], errors='coerce').fillna(-1).astype(int)
    db['literature_id'] = pd.to_numeric(db['literature_id'], errors='coerce').fillna(-1).astype(int)

    # Merge to get full metadata
    dois_with_meta = dois_df.merge(
        db[['literature_id', 'title', 'authors', 'year']],
        on='literature_id',
        how='left'
    )

    print(f"\n{'=' * 80}")
    print(f"DOWNLOADING {len(dois_with_meta)} PAPERS")
    print("=" * 80 + "\n")

    results = []
    success_count = 0

    for idx, row in dois_with_meta.iterrows():
        lit_id = row['literature_id']
        doi = row['doi']
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year', 'unknown')

        print(f"\n[{idx+1}/{len(dois_with_meta)}] {title[:60]}...")
        print(f"   DOI: {doi}")

        # Create output path
        filename = get_pdf_filename(authors, title, year)
        output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download from Sci-Hub
        result = download_from_scihub(doi, mirror, output_path, lit_id)

        # Log result
        results.append({
            'literature_id': lit_id,
            'doi': doi,
            'title': title,
            'authors': authors,
            'year': year,
            'status': result['status'],
            'message': result['message'],
            'file_size': result['file_size']
        })

        if result['status'] == 'success':
            success_count += 1
            print(f"   ✅ Downloaded ({result['file_size']:,} bytes)")
        elif result['status'] == 'not_found':
            print(f"   ❌ Not found on Sci-Hub")
        elif result['status'] == 'timeout':
            print(f"   ⏱️  Timeout")
        else:
            print(f"   ❌ Error: {result['message']}")

    # Save log
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_LOG, index=False)

    # Print summary
    print(f"\n{'=' * 80}")
    print("DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"Total papers: {len(results)}")
    print(f"✅ Success: {success_count} ({success_count/len(results)*100:.1f}%)")
    print(f"❌ Failed: {len(results) - success_count}")
    print(f"\n📊 Results by status:")
    for status, count in results_df['status'].value_counts().items():
        print(f"   {status:15s}: {count:>3}")
    print(f"\n📁 Log saved: {OUTPUT_LOG}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
