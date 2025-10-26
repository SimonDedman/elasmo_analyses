#!/usr/bin/env python3
"""
retrieve_papers_multisource.py

Attempt to retrieve PDFs from multiple alternative sources:
- Unpaywall API (open access repository versions)
- Semantic Scholar API (academic search engine)
- CrossRef API (metadata and OA links)
- DOI resolution
- Base-search.net (open access search)

Usage:
    # Try all pending papers
    python3 scripts/retrieve_papers_multisource.py

    # Try specific status
    python3 scripts/retrieve_papers_multisource.py --status forbidden error

    # Limit number of papers
    python3 scripts/retrieve_papers_multisource.py --max-papers 100

Author: Simon Dedman
Date: 2025-10-22
Version: 1.0
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
import argparse
import logging
from tqdm import tqdm
import sys
import re

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import (
    get_pdf_filename,
    OUTPUT_DIR,
    LOG_FILE
)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
MULTISOURCE_LOG = BASE_DIR / "logs/multisource_retrieval_log.csv"

# API Endpoints (all free, no authentication required)
UNPAYWALL_API = "https://api.unpaywall.org/v2/{doi}?email=your.email@institution.edu"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
CROSSREF_API = "https://api.crossref.org/works/{doi}"
BASE_SEARCH_API = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"

# Rate limiting
UNPAYWALL_DELAY = 1.0  # Polite rate: 1 request/second
SEMANTIC_SCHOLAR_DELAY = 3.0  # More conservative
CROSSREF_DELAY = 1.0
REQUEST_TIMEOUT = 30

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============================================================================
# API RETRIEVAL FUNCTIONS
# ============================================================================

def try_unpaywall(doi, email="noreply@institution.edu"):
    """
    Try to get open access PDF from Unpaywall.

    Unpaywall finds legal open access versions from:
    - Publisher sites (gold OA)
    - Institutional repositories (green OA)
    - Subject repositories (arXiv, PubMed Central, etc.)

    Args:
        doi: Paper DOI
        email: Your email (required by Unpaywall API)

    Returns:
        dict with 'pdf_url' and 'source' if found, None otherwise
    """
    if not doi:
        return None

    try:
        url = UNPAYWALL_API.format(doi=doi).replace("your.email@institution.edu", email)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()

            # Check if open access
            if data.get('is_oa'):
                # Try best OA location first
                best_oa = data.get('best_oa_location')
                if best_oa and best_oa.get('url_for_pdf'):
                    return {
                        'pdf_url': best_oa['url_for_pdf'],
                        'source': f"unpaywall_{best_oa.get('host_type', 'unknown')}",
                        'license': best_oa.get('license', 'unknown')
                    }

                # Try any OA location
                for location in data.get('oa_locations', []):
                    if location.get('url_for_pdf'):
                        return {
                            'pdf_url': location['url_for_pdf'],
                            'source': f"unpaywall_{location.get('host_type', 'unknown')}",
                            'license': location.get('license', 'unknown')
                        }

        time.sleep(UNPAYWALL_DELAY)
        return None

    except Exception as e:
        logging.debug(f"Unpaywall error for {doi}: {e}")
        return None


def try_semantic_scholar(doi=None, title=None):
    """
    Try to get PDF from Semantic Scholar.

    Args:
        doi: Paper DOI
        title: Paper title (used if DOI not available)

    Returns:
        dict with 'pdf_url' and 'source' if found, None otherwise
    """
    try:
        if doi:
            # Search by DOI
            url = SEMANTIC_SCHOLAR_API.format(doi=doi)
            params = {'fields': 'title,openAccessPdf,isOpenAccess'}
        elif title:
            # Search by title
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': title[:200],  # Limit title length
                'fields': 'title,openAccessPdf,isOpenAccess',
                'limit': 1
            }
        else:
            return None

        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()

            # Handle search results vs direct lookup
            if 'data' in data and len(data['data']) > 0:
                paper = data['data'][0]
            else:
                paper = data

            # Check for open access PDF
            if paper.get('isOpenAccess') and paper.get('openAccessPdf'):
                pdf_url = paper['openAccessPdf'].get('url')
                if pdf_url:
                    return {
                        'pdf_url': pdf_url,
                        'source': 'semantic_scholar',
                        'license': 'open_access'
                    }

        time.sleep(SEMANTIC_SCHOLAR_DELAY)
        return None

    except Exception as e:
        logging.debug(f"Semantic Scholar error: {e}")
        return None


def try_crossref(doi):
    """
    Try to get open access info from CrossRef.

    Args:
        doi: Paper DOI

    Returns:
        dict with 'pdf_url' and 'source' if found, None otherwise
    """
    if not doi:
        return None

    try:
        url = CROSSREF_API.format(doi=doi)
        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            message = data.get('message', {})

            # Check for open access links
            links = message.get('link', [])
            for link in links:
                if link.get('content-type') == 'application/pdf':
                    return {
                        'pdf_url': link.get('URL'),
                        'source': 'crossref',
                        'license': message.get('license', [{}])[0].get('URL', 'unknown')
                    }

        time.sleep(CROSSREF_DELAY)
        return None

    except Exception as e:
        logging.debug(f"CrossRef error for {doi}: {e}")
        return None


def try_doi_resolution(doi):
    """
    Try to resolve DOI directly and check for PDF.

    Args:
        doi: Paper DOI

    Returns:
        dict with 'pdf_url' and 'source' if PDF found, None otherwise
    """
    if not doi:
        return None

    try:
        # Try doi.org resolution
        doi_url = f"https://doi.org/{doi}"
        response = requests.head(doi_url, allow_redirects=True, timeout=REQUEST_TIMEOUT)

        # Check if redirects to a PDF
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' in content_type.lower():
                return {
                    'pdf_url': response.url,
                    'source': 'doi_resolution',
                    'license': 'unknown'
                }

        return None

    except Exception as e:
        logging.debug(f"DOI resolution error for {doi}: {e}")
        return None


def download_pdf(pdf_url, output_path):
    """Download PDF from URL to output path."""
    try:
        response = requests.get(
            pdf_url,
            headers={'User-Agent': 'Mozilla/5.0 (Research PDF Retrieval)'},
            timeout=REQUEST_TIMEOUT,
            stream=True
        )

        if response.status_code == 200:
            # Check if actually PDF
            content_type = response.headers.get('content-type', '')
            if 'application/pdf' in content_type.lower() or pdf_url.lower().endswith('.pdf'):
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Verify it's a PDF
                with open(output_path, 'rb') as f:
                    header = f.read(5)
                    if header == b'%PDF-':
                        return True

                # Not a PDF, remove
                output_path.unlink()
                return False

        return False

    except Exception as e:
        logging.debug(f"Download error: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


# ============================================================================
# MAIN RETRIEVAL LOGIC
# ============================================================================

def retrieve_paper(row, methods=['unpaywall', 'semantic_scholar', 'crossref', 'doi']):
    """
    Try to retrieve paper from multiple sources.

    Args:
        row: DataFrame row with paper metadata
        methods: List of methods to try

    Returns:
        dict with success status and source info
    """
    doi = row.get('doi')
    title = row.get('title')
    lit_id = row.get('literature_id')
    year = row.get('year')
    authors = row.get('authors')

    # Try each method in order
    for method in methods:
        try:
            result = None

            if method == 'unpaywall':
                result = try_unpaywall(doi)
            elif method == 'semantic_scholar':
                result = try_semantic_scholar(doi=doi, title=title)
            elif method == 'crossref':
                result = try_crossref(doi)
            elif method == 'doi':
                result = try_doi_resolution(doi)

            if result and result.get('pdf_url'):
                # Try to download
                filename = get_pdf_filename(authors, year, title, lit_id)
                output_path = OUTPUT_DIR / str(year) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                if download_pdf(result['pdf_url'], output_path):
                    return {
                        'status': 'success',
                        'source': result['source'],
                        'pdf_url': result['pdf_url'],
                        'output_file': str(output_path),
                        'file_size': output_path.stat().st_size,
                        'license': result.get('license', 'unknown')
                    }

        except Exception as e:
            logging.debug(f"Method {method} failed: {e}")
            continue

    return {'status': 'not_found', 'source': 'none', 'message': 'No open access version found'}


def main():
    parser = argparse.ArgumentParser(
        description='Retrieve PDFs from multiple alternative sources',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--status',
        nargs='+',
        choices=['timeout', 'error', 'forbidden', 'not_found'],
        default=['forbidden', 'error', 'not_found'],
        help='Which status types to retry'
    )

    parser.add_argument(
        '--max-papers',
        type=int,
        help='Maximum number of papers to attempt'
    )

    parser.add_argument(
        '--methods',
        nargs='+',
        choices=['unpaywall', 'semantic_scholar', 'crossref', 'doi'],
        default=['unpaywall', 'semantic_scholar', 'crossref', 'doi'],
        help='Which retrieval methods to use'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("MULTI-SOURCE PDF RETRIEVAL")
    print("=" * 80)

    # Load download log
    log_df = pd.read_csv(LOG_FILE)
    print(f"\nLoaded download log: {len(log_df)} entries")

    # Filter to specified statuses
    retry_df = log_df[log_df['status'].isin(args.status)].copy()
    print(f"Papers to attempt: {len(retry_df)} ({', '.join(args.status)})")

    # Load database for DOI and full metadata
    db_df = pd.read_parquet(DATABASE_PARQUET)

    # Merge to get DOI
    retry_df['literature_id'] = pd.to_numeric(retry_df['literature_id'], errors='coerce').astype('Int64')
    db_df['literature_id'] = pd.to_numeric(db_df['literature_id'], errors='coerce').astype('Int64')

    retry_df = retry_df.merge(
        db_df[['literature_id', 'doi', 'title', 'authors', 'year']],
        on='literature_id',
        how='left',
        suffixes=('', '_db')
    )

    # Filter to papers with DOI or title
    retry_df = retry_df[retry_df['doi'].notna() | retry_df['title'].notna()]

    if args.max_papers:
        retry_df = retry_df.head(args.max_papers)

    print(f"\nPapers with DOI or title: {len(retry_df)}")
    print(f"Methods: {', '.join(args.methods)}")
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Track results
    results = []
    success_count = 0

    # Process papers
    for idx, row in tqdm(retry_df.iterrows(), total=len(retry_df), desc="Retrieving"):
        result = retrieve_paper(row, methods=args.methods)

        result.update({
            'literature_id': row['literature_id'],
            'doi': row['doi'],
            'title': row['title'],
            'original_status': row['status'],
            'timestamp': datetime.now().isoformat()
        })

        results.append(result)

        if result['status'] == 'success':
            success_count += 1
            logging.info(f"✅ {row['literature_id']}: {result['source']}")

        # Save progress every 10 papers
        if len(results) % 10 == 0:
            pd.DataFrame(results).to_csv(MULTISOURCE_LOG, index=False)

    # Final save
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(MULTISOURCE_LOG, index=False)

        # Update main download log
        for _, result_row in results_df[results_df['status'] == 'success'].iterrows():
            lit_id = result_row['literature_id']
            log_df.loc[log_df['literature_id'] == lit_id, 'status'] = 'multisource_success'
            log_df.loc[log_df['literature_id'] == lit_id, 'message'] = f"Retrieved from {result_row['source']}"
            log_df.loc[log_df['literature_id'] == lit_id, 'download_date'] = result_row['timestamp']

        log_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total attempted: {len(retry_df)}")
    print(f"✅ Successfully retrieved: {success_count} ({success_count/len(retry_df)*100:.1f}%)")
    print(f"❌ Not found: {len(results) - success_count}")

    if success_count > 0:
        source_dist = results_df[results_df['status'] == 'success']['source'].value_counts()
        print(f"\n📊 Success by source:")
        for source, count in source_dist.items():
            print(f"   • {source}: {count}")

    print(f"\n✅ Results saved: {MULTISOURCE_LOG}")
    print(f"✅ Download log updated: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
