#!/usr/bin/env python3
"""
download_oa_papers_only.py

Target ONLY open access papers for download using multiple OA sources:
- Known OA publishers (MDPI, Frontiers, PLOS, etc.)
- Unpaywall API for OA repository versions
- PubMed Central (PMC)
- bioRxiv/medRxiv preprints
- Europe PMC

This script focuses on high-probability OA papers to maximize success rate.

Usage:
    python3 scripts/download_oa_papers_only.py --max-papers 5000

Author: Simon Dedman
Date: 2025-10-22
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
import argparse
import logging
from tqdm import tqdm
from urllib.parse import urlparse
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import (
    get_pdf_filename,
    OUTPUT_DIR,
    download_pdf
)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
OA_LOG = BASE_DIR / "logs/oa_download_log.csv"

# Known Open Access publishers/domains
OA_PUBLISHERS = {
    'mdpi.com': 'MDPI',
    'frontiersin.org': 'Frontiers',
    'plos.org': 'PLOS',
    'plosone.org': 'PLOS',
    'biomedcentral.com': 'BioMed Central',
    'peerj.com': 'PeerJ',
    'scielo.br': 'SciELO',
    'scielo.org': 'SciELO',
    'hindawi.com': 'Hindawi',
    'elifesciences.org': 'eLife',
    'nature.com/ncomms': 'Nature Communications',
    'nature.com/srep': 'Scientific Reports',
    'noaa.gov': 'NOAA',
    'cmfri.org.in': 'CMFRI',
    'royalsocietypublishing.org': 'Royal Society',
    'cell.com': 'Cell Press OA',
    'oup.com': 'Oxford OA',
}

# API endpoints
UNPAYWALL_API = "https://api.unpaywall.org/v2/{doi}?email=noreply@institution.edu"
PUBMED_CENTRAL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={doi}&format=json"
EUROPE_PMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&format=json"

# Rate limiting
API_DELAY = 1.0
REQUEST_TIMEOUT = 30

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# ============================================================================
# OA DETECTION FUNCTIONS
# ============================================================================

def is_oa_publisher(pdf_url):
    """Check if URL is from a known OA publisher."""
    if not pdf_url or pd.isna(pdf_url):
        return False, None

    try:
        domain = urlparse(pdf_url).netloc.lower()
        for oa_domain, publisher in OA_PUBLISHERS.items():
            if oa_domain in domain:
                return True, publisher
    except:
        pass

    return False, None


def check_unpaywall_oa(doi):
    """
    Check if paper is OA using Unpaywall API.

    Returns:
        dict with 'is_oa', 'pdf_url', 'source' if found
    """
    if not doi:
        return None

    try:
        url = UNPAYWALL_API.format(doi=doi)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()

            if data.get('is_oa'):
                # Get best OA location
                best_oa = data.get('best_oa_location')
                if best_oa and best_oa.get('url_for_pdf'):
                    return {
                        'is_oa': True,
                        'pdf_url': best_oa['url_for_pdf'],
                        'source': f"unpaywall_{best_oa.get('host_type', 'unknown')}",
                        'license': best_oa.get('license', 'unknown'),
                        'version': best_oa.get('version', 'unknown')
                    }

                # Try any OA location
                for location in data.get('oa_locations', []):
                    if location.get('url_for_pdf'):
                        return {
                            'is_oa': True,
                            'pdf_url': location['url_for_pdf'],
                            'source': f"unpaywall_{location.get('host_type', 'unknown')}",
                            'license': location.get('license', 'unknown'),
                            'version': location.get('version', 'unknown')
                        }

        time.sleep(API_DELAY)
        return None

    except Exception as e:
        logging.debug(f"Unpaywall error for {doi}: {e}")
        return None


def check_pmc(doi):
    """
    Check if paper is available in PubMed Central.

    Returns:
        dict with PMC ID and PDF URL if available
    """
    if not doi:
        return None

    try:
        url = PUBMED_CENTRAL.format(doi=doi)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])

            if records and len(records) > 0:
                record = records[0]
                pmcid = record.get('pmcid')

                if pmcid:
                    # Construct PMC PDF URL
                    pmc_id_number = pmcid.replace('PMC', '')
                    pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id_number}/pdf/"

                    return {
                        'is_oa': True,
                        'pdf_url': pdf_url,
                        'source': 'pubmed_central',
                        'pmcid': pmcid
                    }

        time.sleep(API_DELAY)
        return None

    except Exception as e:
        logging.debug(f"PMC error for {doi}: {e}")
        return None


def check_europe_pmc(doi):
    """Check Europe PMC for open access version."""
    if not doi:
        return None

    try:
        url = EUROPE_PMC_API.format(doi=doi)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            results = data.get('resultList', {}).get('result', [])

            if results and len(results) > 0:
                result = results[0]

                # Check if full text is available
                if result.get('isOpenAccess') == 'Y':
                    pmcid = result.get('pmcid')
                    if pmcid:
                        pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
                        return {
                            'is_oa': True,
                            'pdf_url': pdf_url,
                            'source': 'europe_pmc',
                            'pmcid': pmcid
                        }

        time.sleep(API_DELAY)
        return None

    except Exception as e:
        logging.debug(f"Europe PMC error for {doi}: {e}")
        return None


# ============================================================================
# MAIN DOWNLOAD FUNCTION
# ============================================================================

def identify_oa_papers(db, max_papers=None):
    """
    Identify papers that are likely open access.

    Strategy:
    1. Papers from known OA publishers (high probability)
    2. Papers with DOI to check via Unpaywall/PMC
    3. Sort by year (prioritize recent papers)

    Returns:
        DataFrame of OA papers to attempt
    """
    print("\n" + "=" * 80)
    print("IDENTIFYING OPEN ACCESS PAPERS")
    print("=" * 80)

    # Filter out already downloaded papers
    not_downloaded = db[~db['pdf_url'].notna() | (db['pdf_url'] == '')]
    print(f"\n📊 Papers without PDFs: {len(not_downloaded):,}")

    # Priority 1: Known OA publishers
    oa_publisher_papers = []
    for idx, row in not_downloaded.iterrows():
        pdf_url = row.get('pdf_url', '')
        is_oa, publisher = is_oa_publisher(pdf_url)
        if is_oa:
            oa_publisher_papers.append({
                'literature_id': row['literature_id'],
                'doi': row.get('doi'),
                'title': row.get('title'),
                'authors': row.get('authors'),
                'year': row.get('year'),
                'pdf_url': pdf_url,
                'priority': 1,
                'source': f'known_oa_{publisher}'
            })

    print(f"✅ Known OA publishers: {len(oa_publisher_papers):,}")

    # Priority 2: Papers with DOI (check via APIs)
    has_doi = not_downloaded[not_downloaded['doi'].notna() & (not_downloaded['doi'] != '')]

    # Sort by year (recent papers more likely to be OA)
    has_doi_sorted = has_doi.sort_values('year', ascending=False, na_position='last')

    print(f"✅ Papers with DOI to check: {len(has_doi_sorted):,}")

    # Combine and limit
    oa_papers = pd.DataFrame(oa_publisher_papers)

    # Add DOI papers (will check OA status during download)
    doi_papers = []
    for idx, row in has_doi_sorted.iterrows():
        # Skip if already in OA publishers list
        if row['literature_id'] not in [p['literature_id'] for p in oa_publisher_papers]:
            doi_papers.append({
                'literature_id': row['literature_id'],
                'doi': row.get('doi'),
                'title': row.get('title'),
                'authors': row.get('authors'),
                'year': row.get('year'),
                'pdf_url': None,
                'priority': 2,
                'source': 'doi_check'
            })

    doi_df = pd.DataFrame(doi_papers)
    all_oa = pd.concat([oa_papers, doi_df], ignore_index=True)

    # Limit if requested
    if max_papers:
        all_oa = all_oa.head(max_papers)

    print(f"\n📋 Total papers to attempt: {len(all_oa):,}")
    print(f"   Priority 1 (Known OA): {len(oa_papers):,}")
    print(f"   Priority 2 (DOI check): {min(len(doi_df), max_papers - len(oa_papers) if max_papers else len(doi_df)):,}")

    return all_oa


def download_oa_papers(oa_papers, dry_run=False):
    """
    Download open access papers.

    Args:
        oa_papers: DataFrame of OA papers
        dry_run: If True, don't actually download
    """
    print("\n" + "=" * 80)
    print("DOWNLOADING OPEN ACCESS PAPERS")
    print("=" * 80)

    results = []
    success_count = 0

    for idx, row in tqdm(oa_papers.iterrows(), total=len(oa_papers), desc="Downloading"):
        lit_id = row['literature_id']
        doi = row['doi']
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year', 'unknown')

        # Try to get OA version
        oa_info = None
        pdf_url = row.get('pdf_url')

        if pdf_url:
            # Already have URL from known OA publisher
            oa_info = {
                'pdf_url': pdf_url,
                'source': row.get('source', 'known_oa'),
                'is_oa': True
            }
        else:
            # Check OA APIs in order
            oa_info = (
                check_unpaywall_oa(doi) or
                check_pmc(doi) or
                check_europe_pmc(doi)
            )

        if oa_info and oa_info.get('pdf_url'):
            # Attempt download
            if not dry_run:
                # Create output path
                filename = get_pdf_filename(authors, title, year)
                output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Download
                dl_result = download_pdf(
                    oa_info['pdf_url'],
                    output_path,
                    lit_id
                )

                success = (dl_result.get('status') == 'success')

                if success:
                    success_count += 1

                result = {
                    'literature_id': lit_id,
                    'status': dl_result.get('status'),
                    'source': oa_info.get('source'),
                    'pdf_url': oa_info['pdf_url'],
                    'license': oa_info.get('license', 'unknown'),
                    'year': year,
                    'message': dl_result.get('message'),
                    'file_size': dl_result.get('file_size'),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                result = {
                    'literature_id': lit_id,
                    'status': 'would_download',
                    'source': oa_info.get('source'),
                    'pdf_url': oa_info['pdf_url'],
                    'year': year
                }
        else:
            result = {
                'literature_id': lit_id,
                'status': 'not_oa',
                'source': 'none',
                'pdf_url': None,
                'year': year,
                'timestamp': datetime.now().isoformat()
            }

        results.append(result)

    # Save log
    results_df = pd.DataFrame(results)
    results_df.to_csv(OA_LOG, index=False)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✅ Successfully downloaded: {success_count:,}/{len(oa_papers):,}")
    print(f"📊 Success rate: {success_count/len(oa_papers)*100:.1f}%")
    print(f"\nBreakdown by source:")
    for source, group in results_df.groupby('source'):
        successes = len(group[group['status'] == 'success'])
        print(f"  {source}: {successes}/{len(group)} ({successes/len(group)*100:.1f}%)")
    print(f"\n📄 Log saved: {OA_LOG}")
    print("=" * 80)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Download open access papers only")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to attempt")
    parser.add_argument('--dry-run', action='store_true', help="Don't actually download")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("OPEN ACCESS PAPER DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load database
    print(f"\n📖 Loading database...")
    db = pd.read_parquet(DATABASE_PARQUET)
    print(f"✅ Loaded {len(db):,} papers")

    # Identify OA papers
    oa_papers = identify_oa_papers(db, max_papers=args.max_papers)

    if len(oa_papers) == 0:
        print("\n⚠️  No OA papers to download")
        return

    # Download
    if not args.dry_run:
        download_oa_papers(oa_papers, dry_run=args.dry_run)
    else:
        print("\n🔍 DRY RUN - Would attempt to download:")
        print(f"   Total papers: {len(oa_papers):,}")
        print(f"   Known OA publishers: {len(oa_papers[oa_papers['priority'] == 1]):,}")
        print(f"   DOI to check: {len(oa_papers[oa_papers['priority'] == 2]):,}")


if __name__ == "__main__":
    main()
