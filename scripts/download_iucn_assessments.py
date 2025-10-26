#!/usr/bin/env python3
"""
download_iucn_assessments.py

Download IUCN Red List assessments for shark species.

The IUCN Red List provides free access to species assessments.
This script extracts species names from paper titles and downloads
available assessment PDFs.

Author: Simon Dedman / Claude
Date: 2025-10-22
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
import re
from tqdm import tqdm
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "outputs/papers_without_doi.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/iucn_download_log.csv"

# IUCN Red List API
# Get free API key from: https://apiv3.iucnredlist.org/api/v3/token
IUCN_API_KEY = None  # User needs to provide this
IUCN_API_BASE = "https://apiv3.iucnredlist.org/api/v3"

# Rate limiting
DELAY_BETWEEN_REQUESTS = 0.5  # seconds
REQUEST_TIMEOUT = 30

# User agent
USER_AGENT = "SharkResearchBot/1.0 (mailto:simondedman@gmail.com; Research purposes)"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_species_name(title):
    """
    Extract species name from IUCN assessment title.

    IUCN titles typically follow patterns like:
    - "Carcharodon carcharias"
    - "Carcharhinus leucas (Bull Shark)"
    - "Sphyrna mokarran - Assessed in 2019"
    """
    if not title:
        return None

    # Pattern: Genus species (two capitalized words)
    pattern = r'\b([A-Z][a-z]+)\s+([a-z]+)\b'
    match = re.search(pattern, str(title))

    if match:
        genus = match.group(1)
        species = match.group(2)
        return f"{genus}_{species}"

    return None


def search_iucn_species(species_name, api_key):
    """
    Search IUCN Red List for species assessment.

    Args:
        species_name: Scientific name (e.g., "Carcharodon_carcharias")
        api_key: IUCN API key

    Returns:
        dict with assessment data or None
    """
    if not api_key:
        logging.error("IUCN API key not provided")
        return None

    # Format species name for API (replace underscore with space)
    species_query = species_name.replace('_', ' ')

    try:
        # IUCN API species endpoint
        url = f"{IUCN_API_BASE}/species/{species_query}"
        params = {'token': api_key}
        headers = {'User-Agent': USER_AGENT}

        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            result = data.get('result', [])

            if result and len(result) > 0:
                assessment = result[0]
                return {
                    'taxon_id': assessment.get('taxonid'),
                    'scientific_name': assessment.get('scientific_name'),
                    'category': assessment.get('category'),
                    'assessment_date': assessment.get('assessment_date'),
                    'found': True
                }

        return None

    except Exception as e:
        logging.debug(f"IUCN API error for {species_query}: {e}")
        return None


def download_iucn_pdf(taxon_id, species_name, output_path, api_key):
    """
    Download IUCN assessment PDF.

    Note: IUCN doesn't provide direct PDF downloads via API.
    Instead, we construct the URL to the assessment page.
    PDFs may need to be accessed via the web interface.

    Returns:
        dict with download status
    """
    # IUCN assessment URLs follow pattern:
    # https://www.iucnredlist.org/species/{taxon_id}

    assessment_url = f"https://www.iucnredlist.org/species/{taxon_id}"

    # Attempt to scrape PDF link from assessment page
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(assessment_url, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            # Look for PDF download link in HTML
            # IUCN sometimes provides "Download PDF" links
            if 'pdf' in response.text.lower() or 'download' in response.text.lower():
                # TODO: Parse HTML to find actual PDF URL
                # For now, just return the assessment page URL
                return {
                    'status': 'assessment_page',
                    'url': assessment_url,
                    'message': 'Assessment page found (PDF may require manual download)'
                }

        return {
            'status': 'not_found',
            'url': assessment_url,
            'message': 'Assessment page not accessible'
        }

    except Exception as e:
        return {
            'status': 'error',
            'url': assessment_url,
            'message': str(e)
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download IUCN Red List assessments")
    parser.add_argument('--api-key', type=str, help="IUCN API key (get from https://apiv3.iucnredlist.org/api/v3/token)")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--test', action='store_true', help="Test mode: only process 10 papers")
    args = parser.parse_args()

    if not args.api_key:
        print("\n" + "=" * 80)
        print("ERROR: IUCN API key required")
        print("=" * 80)
        print("\nGet a free API key from:")
        print("https://apiv3.iucnredlist.org/api/v3/token")
        print("\nThen run:")
        print("  python scripts/download_iucn_assessments.py --api-key YOUR_KEY")
        print("=" * 80)
        return

    print("\n" + "=" * 80)
    print("IUCN RED LIST ASSESSMENT DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load papers without DOIs
    print(f"\n📖 Loading papers...")
    df = pd.read_csv(INPUT_CSV)

    # Filter for IUCN papers
    iucn_papers = df[df['journal'].str.contains('IUCN', case=False, na=False)]
    print(f"✅ Found {len(iucn_papers):,} IUCN papers")

    # Limit if requested
    if args.test:
        iucn_papers = iucn_papers.head(10)
        print(f"🧪 Test mode: processing {len(iucn_papers)} papers")
    elif args.max_papers:
        iucn_papers = iucn_papers.head(args.max_papers)
        print(f"📊 Limited to: {args.max_papers:,} papers")

    if len(iucn_papers) == 0:
        print("\n⚠️  No IUCN papers to process")
        return

    # Process papers
    print(f"\n{'=' * 80}")
    print(f"PROCESSING {len(iucn_papers):,} IUCN PAPERS")
    print("=" * 80)

    results = []
    found_count = 0

    for idx, row in tqdm(iucn_papers.iterrows(), total=len(iucn_papers), desc="Processing"):
        lit_id = row['literature_id']
        title = row.get('title', '')
        year = row.get('year')

        # Extract species name
        species_name = extract_species_name(title)

        if not species_name:
            results.append({
                'literature_id': lit_id,
                'title': title,
                'species_name': None,
                'taxon_id': None,
                'status': 'no_species_name',
                'url': None,
                'message': 'Could not extract species name from title',
                'timestamp': datetime.now().isoformat()
            })
            continue

        # Search IUCN
        assessment = search_iucn_species(species_name, args.api_key)

        if assessment and assessment.get('found'):
            found_count += 1
            taxon_id = assessment['taxon_id']

            # Attempt to download/locate PDF
            download_result = download_iucn_pdf(taxon_id, species_name, None, args.api_key)

            results.append({
                'literature_id': lit_id,
                'title': title,
                'species_name': species_name,
                'taxon_id': taxon_id,
                'status': download_result['status'],
                'url': download_result.get('url'),
                'message': download_result.get('message'),
                'category': assessment.get('category'),
                'assessment_date': assessment.get('assessment_date'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            results.append({
                'literature_id': lit_id,
                'title': title,
                'species_name': species_name,
                'taxon_id': None,
                'status': 'not_found_in_iucn',
                'url': None,
                'message': 'Species not found in IUCN database',
                'timestamp': datetime.now().isoformat()
            })

        # Respectful delay
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✅ Found in IUCN database: {found_count:,}/{len(iucn_papers):,}")
    print(f"📊 Success rate: {found_count/len(iucn_papers)*100:.1f}%")

    if found_count > 0:
        print(f"\nBreakdown by status:")
        for status, group in results_df.groupby('status'):
            print(f"  {status:30s}: {len(group):>5,}")

        # Show assessment URLs
        assessment_pages = results_df[results_df['url'].notna()]
        if len(assessment_pages) > 0:
            print(f"\n📄 Assessment page URLs available: {len(assessment_pages):,}")
            print(f"   (Manual PDF download may be required from these pages)")

    print(f"\n📄 Full log: {LOG_FILE}")
    print("=" * 80)
    print("\n💡 Note: IUCN PDFs often require manual download from assessment pages.")
    print("   The log file contains direct URLs to each assessment.")


if __name__ == "__main__":
    main()
