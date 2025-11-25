#!/usr/bin/env python3
"""
extract_semantic_scholar_dois.py

Extract DOIs from Semantic Scholar and DOI discovery logs that weren't in the original database.

Strategy:
1. Load original papers database to get existing DOIs
2. Load Semantic Scholar log to find DOIs discovered via API
3. Load DOI discovery log to find DOIs discovered via parallel search
4. Combine and deduplicate all newly discovered DOIs
5. Output for Sci-Hub download

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
PAPERS_FILE = BASE_DIR / "outputs/papers_with_found_dois.csv"
SEMANTIC_LOG = BASE_DIR / "logs/semantic_scholar_log.csv"
DOI_DISCOVERY_LOG = BASE_DIR / "logs/doi_discovery_log.csv"
OUTPUT_FILE = BASE_DIR / "outputs/newly_discovered_dois.csv"

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    print("=" * 80)
    print("SEMANTIC SCHOLAR DOI EXTRACTOR")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load original papers database
    print(f"\n📊 Loading original papers database...")
    papers_df = pd.read_csv(PAPERS_FILE)

    # Check if column is 'doi' or 'found_doi'
    doi_col = 'found_doi' if 'found_doi' in papers_df.columns else 'doi'
    original_dois = set(papers_df[papers_df[doi_col].notna()][doi_col].str.upper())
    print(f"   Original papers: {len(papers_df):,}")
    print(f"   Papers with DOIs: {len(original_dois):,}")

    # Load Semantic Scholar log
    print(f"\n📊 Loading Semantic Scholar log...")
    if SEMANTIC_LOG.exists():
        semantic_df = pd.read_csv(SEMANTIC_LOG)
        print(f"   Semantic Scholar searches: {len(semantic_df):,}")

        # Extract DOIs that were found
        semantic_dois = semantic_df[semantic_df['doi'].notna()]['doi'].str.upper().unique()
        print(f"   DOIs found via Semantic Scholar: {len(semantic_dois):,}")
    else:
        print(f"   ⚠️  Semantic Scholar log not found")
        semantic_dois = []

    # Load DOI discovery log
    print(f"\n📊 Loading DOI discovery log...")
    if DOI_DISCOVERY_LOG.exists():
        doi_df = pd.read_csv(DOI_DISCOVERY_LOG)
        print(f"   DOI discovery searches: {len(doi_df):,}")

        # Extract DOIs that were found
        discovery_dois = doi_df[doi_df['doi'].notna()]['doi'].str.upper().unique()
        print(f"   DOIs found via discovery: {len(discovery_dois):,}")
    else:
        print(f"   ⚠️  DOI discovery log not found")
        discovery_dois = []

    # Combine all discovered DOIs
    all_discovered = set(semantic_dois) | set(discovery_dois)
    print(f"\n📊 Total DOIs discovered: {len(all_discovered):,}")

    # Find NEW DOIs (not in original database)
    new_dois = all_discovered - original_dois
    print(f"📊 NEW DOIs (not in original database): {len(new_dois):,}")

    if len(new_dois) == 0:
        print("\n⚠️  No new DOIs found!")
        print("   All discovered DOIs were already in the database")
        return

    # Create output dataframe
    results = []

    # Add metadata from Semantic Scholar
    if SEMANTIC_LOG.exists():
        semantic_df['doi_upper'] = semantic_df['doi'].str.upper()
        for doi in new_dois:
            matches = semantic_df[semantic_df['doi_upper'] == doi]
            if len(matches) > 0:
                row = matches.iloc[0]
                results.append({
                    'doi': doi,
                    'literature_id': row.get('literature_id', ''),
                    'title': row.get('matched_title', row.get('title', '')),
                    'source': 'semantic_scholar',
                    'semantic_scholar_id': row.get('semantic_scholar_id', ''),
                    'pdf_url': row.get('pdf_url', ''),
                    'citations': row.get('citations', '')
                })

    # Add metadata from DOI discovery
    if DOI_DISCOVERY_LOG.exists():
        doi_df['doi_upper'] = doi_df['doi'].str.upper()
        for doi in new_dois:
            # Skip if already added from Semantic Scholar
            if any(r['doi'] == doi for r in results):
                continue

            matches = doi_df[doi_df['doi_upper'] == doi]
            if len(matches) > 0:
                row = matches.iloc[0]
                results.append({
                    'doi': doi,
                    'literature_id': row.get('literature_id', ''),
                    'title': row.get('matched_title', row.get('original_title', '')),
                    'source': row.get('source', 'doi_discovery'),
                    'semantic_scholar_id': '',
                    'pdf_url': '',
                    'citations': ''
                })

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Save to CSV
    results_df.to_csv(OUTPUT_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("EXTRACTION SUMMARY")
    print("=" * 80)

    print(f"\n📊 NEW DOIs discovered: {len(results_df):,}")

    print(f"\nBreakdown by source:")
    for source, group in results_df.groupby('source'):
        print(f"  {source:30s}: {len(group):>5,}")

    # Count DOIs with PDF URLs
    with_pdf = len(results_df[results_df['pdf_url'].notna() & (results_df['pdf_url'] != '')])
    print(f"\n📄 DOIs with PDF URLs: {with_pdf:,}")
    print(f"📥 DOIs for Sci-Hub: {len(results_df) - with_pdf:,}")

    print(f"\n✅ Results saved to: {OUTPUT_FILE}")
    print("=" * 80)

    # Show sample
    print(f"\n📝 Sample newly discovered DOIs:")
    for idx, row in results_df.head(10).iterrows():
        print(f"\n  DOI: {row['doi']}")
        title = row['title'] if isinstance(row['title'], str) else ''
        print(f"  Title: {title[:70]}...")
        print(f"  Source: {row['source']}")
        if row.get('pdf_url') and isinstance(row['pdf_url'], str) and row['pdf_url']:
            print(f"  PDF: {row['pdf_url'][:60]}...")


if __name__ == "__main__":
    main()
