#!/usr/bin/env python3
"""
download_all_papers_multisource.py

Comprehensive paper download orchestrator that tries multiple sources in sequence:
1. ResearchGate (with authentication)
2. Academia.edu (with authentication)
3. Sci-Hub (for papers with DOIs)

This script coordinates the entire download process to acquire all ~30,000 papers
from the Shark-References database.

⚠️  EDUCATIONAL/RESEARCH USE ONLY
Use responsibly and ensure compliance with Terms of Service.

Author: Simon Dedman / Claude
Date: 2025-10-22
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
import argparse
from tqdm import tqdm
import logging
import sys

# Add parent for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import get_pdf_filename, OUTPUT_DIR
from download_from_researchgate import ResearchGateSession, RG_EMAIL, RG_PASSWORD
from download_from_academia import AcademiaSession, ACADEMIA_EMAIL, ACADEMIA_PASSWORD
from download_via_scihub import download_from_scihub, check_scihub_availability, SCIHUB_MIRRORS

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
MASTER_LOG = BASE_DIR / "logs/multisource_download_log.csv"

# Rate limiting
DELAY_BETWEEN_REQUESTS = 3.0  # seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_already_downloaded(lit_id, year, authors, title):
    """Check if paper already exists in output directory."""
    try:
        filename = get_pdf_filename(authors, title, year)
        output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename

        if output_path.exists() and output_path.stat().st_size > 0:
            # Verify it's a valid PDF
            with open(output_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    return True, output_path

        return False, None
    except:
        return False, None


def try_researchgate(rg_session, lit_id, doi, title, authors, year):
    """
    Try to download paper from ResearchGate.

    Returns:
        dict with status, source, message, file_size
    """
    try:
        # Search for paper
        search_result = rg_session.search_paper(doi=doi, title=title)

        if search_result and search_result.get('found'):
            paper_url = search_result['paper_url']

            # Get PDF URL
            pdf_url = rg_session.get_pdf_url(paper_url)

            if pdf_url:
                # Create output path
                filename = get_pdf_filename(authors, title, year)
                output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Download PDF
                result = rg_session.download_pdf(pdf_url, output_path)
                result['source'] = 'researchgate'
                return result
            else:
                return {
                    'status': 'no_pdf',
                    'source': 'researchgate',
                    'message': 'Paper found but no PDF available',
                    'file_size': 0
                }
        else:
            return {
                'status': 'not_found',
                'source': 'researchgate',
                'message': 'Paper not found',
                'file_size': 0
            }
    except Exception as e:
        return {
            'status': 'error',
            'source': 'researchgate',
            'message': f'Error: {str(e)}',
            'file_size': 0
        }


def try_academia(academia_session, lit_id, title, authors, year):
    """
    Try to download paper from Academia.edu.

    Returns:
        dict with status, source, message, file_size
    """
    try:
        # Search for paper
        search_result = academia_session.search_paper(title=title, authors=authors)

        if search_result and search_result.get('found'):
            paper_url = search_result['paper_url']

            # Get PDF URL
            pdf_url = academia_session.get_pdf_url(paper_url)

            if pdf_url:
                # Create output path
                filename = get_pdf_filename(authors, title, year)
                output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Download PDF
                result = academia_session.download_pdf(pdf_url, output_path)
                result['source'] = 'academia'
                return result
            else:
                return {
                    'status': 'no_pdf',
                    'source': 'academia',
                    'message': 'Paper found but no PDF available',
                    'file_size': 0
                }
        else:
            return {
                'status': 'not_found',
                'source': 'academia',
                'message': 'Paper not found',
                'file_size': 0
            }
    except Exception as e:
        return {
            'status': 'error',
            'source': 'academia',
            'message': f'Error: {str(e)}',
            'file_size': 0
        }


def try_scihub(doi, lit_id, title, authors, year, scihub_mirror):
    """
    Try to download paper from Sci-Hub.

    Returns:
        dict with status, source, message, file_size
    """
    if not doi:
        return {
            'status': 'no_doi',
            'source': 'scihub',
            'message': 'No DOI available',
            'file_size': 0
        }

    try:
        # Create output path
        filename = get_pdf_filename(authors, title, year)
        output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download from Sci-Hub
        result = download_from_scihub(doi, scihub_mirror, output_path, lit_id)
        result['source'] = 'scihub'
        return result
    except Exception as e:
        return {
            'status': 'error',
            'source': 'scihub',
            'message': f'Error: {str(e)}',
            'file_size': 0
        }


# ============================================================================
# MAIN DOWNLOAD ORCHESTRATOR
# ============================================================================

def download_all_papers(max_papers=None, start_year=None, end_year=None, skip_rg=False, skip_academia=False, skip_scihub=False):
    """
    Main orchestrator for multi-source paper downloads.

    Args:
        max_papers: Maximum papers to attempt
        start_year: Start from this year
        end_year: End at this year
        skip_rg: Skip ResearchGate
        skip_academia: Skip Academia.edu
        skip_scihub: Skip Sci-Hub
    """
    print("\n" + "=" * 80)
    print("MULTI-SOURCE PAPER DOWNLOADER")
    print("=" * 80)
    print("⚠️  EDUCATIONAL/RESEARCH USE ONLY")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize sessions
    rg_session = None
    academia_session = None
    scihub_mirror = None

    # Setup ResearchGate
    if not skip_rg:
        print("\n" + "=" * 80)
        print("INITIALIZING RESEARCHGATE")
        print("=" * 80)
        rg_session = ResearchGateSession(RG_EMAIL, RG_PASSWORD)
        if not rg_session.login():
            print("⚠️  ResearchGate login failed - skipping ResearchGate")
            rg_session = None
        else:
            print("✅ ResearchGate ready")

    # Setup Academia.edu
    if not skip_academia:
        print("\n" + "=" * 80)
        print("INITIALIZING ACADEMIA.EDU")
        print("=" * 80)
        academia_session = AcademiaSession(ACADEMIA_EMAIL, ACADEMIA_PASSWORD)
        if not academia_session.login():
            print("⚠️  Academia.edu login failed - skipping Academia.edu")
            academia_session = None
        else:
            print("✅ Academia.edu ready")

    # Setup Sci-Hub
    if not skip_scihub:
        print("\n" + "=" * 80)
        print("INITIALIZING SCI-HUB")
        print("=" * 80)
        available_mirrors = check_scihub_availability()
        if available_mirrors:
            scihub_mirror = available_mirrors[0]
            print(f"✅ Sci-Hub ready (using {scihub_mirror})")
        else:
            print("⚠️  No Sci-Hub mirrors available - skipping Sci-Hub")

    # Check if any source is available
    if not rg_session and not academia_session and not scihub_mirror:
        print("\n❌ No download sources available. Exiting.")
        return

    # Load database
    print("\n" + "=" * 80)
    print("LOADING DATABASE")
    print("=" * 80)
    db = pd.read_parquet(DATABASE_PARQUET)
    print(f"✅ Total papers in database: {len(db):,}")

    # Filter papers that need downloading
    # We want ALL papers, not just those with pdf_url
    needs_pdf = db.copy()

    print(f"📊 Papers to attempt: {len(needs_pdf):,}")

    # Apply year filters
    if start_year or end_year:
        if start_year:
            needs_pdf = needs_pdf[needs_pdf['year'] >= start_year]
        if end_year:
            needs_pdf = needs_pdf[needs_pdf['year'] <= end_year]
        print(f"📊 After year filter: {len(needs_pdf):,}")

    # Sort by year (recent first)
    needs_pdf = needs_pdf.sort_values('year', ascending=False, na_position='last')

    # Limit if requested
    if max_papers:
        needs_pdf = needs_pdf.head(max_papers)
        print(f"📊 Limited to: {max_papers:,} papers")

    if len(needs_pdf) == 0:
        print("\n⚠️  No papers to download")
        return

    # Download
    print("\n" + "=" * 80)
    print(f"DOWNLOADING {len(needs_pdf):,} PAPERS")
    print("=" * 80)
    print("Strategy: ResearchGate → Academia.edu → Sci-Hub")
    print("=" * 80)

    results = []
    success_count = 0
    already_downloaded_count = 0

    for idx, row in tqdm(needs_pdf.iterrows(), total=len(needs_pdf), desc="Processing"):
        lit_id = row['literature_id']
        doi = row.get('doi')
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year', 'unknown')

        # Check if already downloaded
        already_exists, existing_path = check_already_downloaded(lit_id, year, authors, title)
        if already_exists:
            already_downloaded_count += 1
            results.append({
                'literature_id': lit_id,
                'doi': doi,
                'status': 'already_downloaded',
                'source': 'existing',
                'message': 'Already exists',
                'file_size': existing_path.stat().st_size if existing_path else 0,
                'year': year,
                'timestamp': datetime.now().isoformat()
            })
            continue

        # Try sources in order
        result = None

        # 1. Try ResearchGate
        if rg_session and not result:
            result = try_researchgate(rg_session, lit_id, doi, title, authors, year)
            if result['status'] == 'success':
                success_count += 1
            elif result['status'] in ['not_found', 'no_pdf']:
                result = None  # Try next source
            time.sleep(DELAY_BETWEEN_REQUESTS)

        # 2. Try Academia.edu
        if academia_session and not result:
            result = try_academia(academia_session, lit_id, title, authors, year)
            if result['status'] == 'success':
                success_count += 1
            elif result['status'] in ['not_found', 'no_pdf']:
                result = None  # Try next source
            time.sleep(DELAY_BETWEEN_REQUESTS)

        # 3. Try Sci-Hub
        if scihub_mirror and not result:
            result = try_scihub(doi, lit_id, title, authors, year, scihub_mirror)
            if result['status'] == 'success':
                success_count += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)

        # If still no result, mark as failed
        if not result:
            result = {
                'status': 'failed_all_sources',
                'source': 'none',
                'message': 'Not found in any source',
                'file_size': 0
            }

        # Record result
        results.append({
            'literature_id': lit_id,
            'doi': doi,
            'status': result['status'],
            'source': result.get('source', 'none'),
            'message': result.get('message', ''),
            'file_size': result.get('file_size', 0),
            'year': year,
            'timestamp': datetime.now().isoformat()
        })

        # Save log periodically (every 100 papers)
        if len(results) % 100 == 0:
            temp_df = pd.DataFrame(results)
            temp_df.to_csv(MASTER_LOG, index=False)

    # Save final log
    results_df = pd.DataFrame(results)
    results_df.to_csv(MASTER_LOG, index=False)

    # Print results
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"✅ Already downloaded: {already_downloaded_count:,}")
    print(f"✅ Newly downloaded: {success_count:,}")
    print(f"📊 Total papers attempted: {len(needs_pdf):,}")
    print(f"📊 Success rate (new): {success_count/(len(needs_pdf)-already_downloaded_count)*100:.1f}%")

    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status}: {len(group):,}")

    print(f"\nBreakdown by source:")
    for source, group in results_df.groupby('source'):
        successes = len(group[group['status'] == 'success'])
        print(f"  {source}: {successes}/{len(group)} ({successes/len(group)*100:.1f}%)")

    print(f"\n📄 Master log saved: {MASTER_LOG}")
    print("=" * 80)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Download all papers from multiple sources")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to attempt")
    parser.add_argument('--start-year', type=int, help="Start from this year")
    parser.add_argument('--end-year', type=int, help="End at this year")
    parser.add_argument('--skip-rg', action='store_true', help="Skip ResearchGate")
    parser.add_argument('--skip-academia', action='store_true', help="Skip Academia.edu")
    parser.add_argument('--skip-scihub', action='store_true', help="Skip Sci-Hub")
    args = parser.parse_args()

    download_all_papers(
        max_papers=args.max_papers,
        start_year=args.start_year,
        end_year=args.end_year,
        skip_rg=args.skip_rg,
        skip_academia=args.skip_academia,
        skip_scihub=args.skip_scihub
    )


if __name__ == "__main__":
    main()
