#!/usr/bin/env python3
"""
search_semantic_scholar.py

Search Semantic Scholar for papers and download available PDFs.

Semantic Scholar provides a free API with generous limits (100 requests/second).
Many papers have open access PDFs available.

API Docs: https://www.semanticscholar.org/product/api

Author: Simon Dedman / Claude
Date: 2025-10-22
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm
import logging
import sys

# Add parent for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import get_pdf_filename, OUTPUT_DIR

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "outputs/papers_without_doi.csv"
LOG_FILE = BASE_DIR / "logs/semantic_scholar_log.csv"

# Semantic Scholar API
API_BASE = "https://api.semanticscholar.org/graph/v1"

# Rate limiting (Semantic Scholar allows 100 requests/second, but be conservative)
DELAY_BETWEEN_REQUESTS = 0.1  # seconds (10 requests/second)
REQUEST_TIMEOUT = 30

# User agent
USER_AGENT = "SharkResearchBot/1.0 (mailto:simondedman@gmail.com; Research purposes)"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# ============================================================================
# SEMANTIC SCHOLAR FUNCTIONS
# ============================================================================

def search_semantic_scholar(title, authors=None, year=None):
    """
    Search Semantic Scholar for a paper.

    Args:
        title: Paper title
        authors: Author string (optional)
        year: Publication year (optional)

    Returns:
        dict with paper data including PDF URL if available
    """
    if not title:
        return None

    try:
        # Build query
        query = title.strip()

        # If author and year available, add them
        if authors:
            # Extract first author surname
            author_parts = authors.split(',')[0].split('&')[0].split('.')
            if author_parts:
                first_author = author_parts[0].strip()
                query = f"{query} {first_author}"

        # Search endpoint
        url = f"{API_BASE}/paper/search"
        params = {
            'query': query,
            'fields': 'title,authors,year,openAccessPdf,externalIds,citationCount',
            'limit': 5  # Get top 5 results
        }

        if year:
            params['year'] = str(year)

        headers = {'User-Agent': USER_AGENT}

        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            papers = data.get('data', [])

            if not papers:
                return None

            # Find best match by title similarity
            title_lower = title.lower()
            title_words = set(title_lower.split())

            best_match = None
            best_score = 0

            for paper in papers:
                paper_title = paper.get('title', '').lower()
                paper_words = set(paper_title.split())

                # Calculate word overlap
                if len(title_words) > 0:
                    overlap = len(title_words & paper_words) / len(title_words)

                    if overlap > best_score and overlap >= 0.6:  # At least 60% match
                        best_score = overlap
                        best_match = paper

            if best_match:
                # Get PDF URL if available
                open_access_pdf = best_match.get('openAccessPdf')
                pdf_url = open_access_pdf.get('url') if open_access_pdf else None

                return {
                    'paper_id': best_match.get('paperId'),
                    'title': best_match.get('title'),
                    'year': best_match.get('year'),
                    'pdf_url': pdf_url,
                    'doi': best_match.get('externalIds', {}).get('DOI'),
                    'citations': best_match.get('citationCount', 0),
                    'match_score': best_score,
                    'found': True
                }

        return None

    except Exception as e:
        logging.debug(f"Semantic Scholar error for '{title[:50]}...': {e}")
        return None


def download_pdf_from_url(url, output_path):
    """Download PDF from a URL."""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            # Check if it's actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' in content_type.lower():
                with open(output_path, 'wb') as f:
                    f.write(response.content)

                file_size = output_path.stat().st_size

                # Verify PDF header
                with open(output_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        return {
                            'status': 'success',
                            'file_size': file_size
                        }
                    else:
                        output_path.unlink()

        return {
            'status': 'error',
            'file_size': 0
        }

    except Exception as e:
        return {
            'status': 'error',
            'file_size': 0,
            'error': str(e)
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Search Semantic Scholar for papers")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--min-year', type=int, help="Only process papers from this year onwards")
    parser.add_argument('--test', action='store_true', help="Test mode: only process 10 papers")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("SEMANTIC SCHOLAR SEARCH")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load papers without DOIs
    print(f"\n📖 Loading papers...")
    df = pd.read_csv(INPUT_CSV)
    print(f"✅ Loaded {len(df):,} papers")

    # Filter by year if requested
    if args.min_year:
        df = df[df['year'] >= args.min_year]
        print(f"📊 After year filter (>= {args.min_year}): {len(df):,}")

    # Sort by year (recent first - more likely to have open access PDFs)
    df = df.sort_values('year', ascending=False, na_position='last')

    # Limit if requested
    if args.test:
        df = df.head(10)
        print(f"🧪 Test mode: processing {len(df)} papers")
    elif args.max_papers:
        df = df.head(args.max_papers)
        print(f"📊 Limited to: {args.max_papers:,} papers")

    if len(df) == 0:
        print("\n⚠️  No papers to process")
        return

    # Search and download
    print(f"\n{'=' * 80}")
    print(f"SEARCHING {len(df):,} PAPERS")
    print("=" * 80)

    results = []
    found_count = 0
    pdf_count = 0

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Searching"):
        lit_id = row['literature_id']
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year')

        # Search Semantic Scholar
        result = search_semantic_scholar(title, authors, year)

        if result and result.get('found'):
            found_count += 1

            # If PDF available, download it
            if result.get('pdf_url'):
                filename = get_pdf_filename(authors, title, year)
                output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                download_result = download_pdf_from_url(result['pdf_url'], output_path)

                if download_result['status'] == 'success':
                    pdf_count += 1

                results.append({
                    'literature_id': lit_id,
                    'title': title,
                    'semantic_scholar_id': result['paper_id'],
                    'matched_title': result['title'],
                    'match_score': result['match_score'],
                    'pdf_url': result['pdf_url'],
                    'pdf_status': download_result['status'],
                    'file_size': download_result.get('file_size', 0),
                    'doi': result.get('doi'),
                    'citations': result.get('citations'),
                    'timestamp': datetime.now().isoformat()
                })
            else:
                results.append({
                    'literature_id': lit_id,
                    'title': title,
                    'semantic_scholar_id': result['paper_id'],
                    'matched_title': result['title'],
                    'match_score': result['match_score'],
                    'pdf_url': None,
                    'pdf_status': 'no_pdf_available',
                    'file_size': 0,
                    'doi': result.get('doi'),
                    'citations': result.get('citations'),
                    'timestamp': datetime.now().isoformat()
                })
        else:
            results.append({
                'literature_id': lit_id,
                'title': title,
                'semantic_scholar_id': None,
                'matched_title': None,
                'match_score': 0,
                'pdf_url': None,
                'pdf_status': 'not_found',
                'file_size': 0,
                'doi': None,
                'citations': None,
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
    print(f"✅ Found in Semantic Scholar: {found_count:,}/{len(df):,} ({found_count/len(df)*100:.1f}%)")
    print(f"📥 PDFs downloaded: {pdf_count:,}/{len(df):,} ({pdf_count/len(df)*100:.1f}%)")

    if found_count > 0:
        print(f"\nBreakdown by PDF status:")
        for status, group in results_df.groupby('pdf_status'):
            print(f"  {status:25s}: {len(group):>5,}")

        # DOIs found
        dois_found = results_df[results_df['doi'].notna()]
        if len(dois_found) > 0:
            print(f"\n💡 DOIs discovered: {len(dois_found):,}")
            print(f"   (These papers can now be added to Sci-Hub queue)")

    print(f"\n📄 Full log: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
