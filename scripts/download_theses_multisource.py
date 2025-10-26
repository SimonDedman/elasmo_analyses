#!/usr/bin/env python3
"""
download_theses_multisource.py

Download thesis and dissertation PDFs using multiple sources:
1. Google Scholar (primary - best coverage)
2. OATD web scraping (secondary - no API available)
3. Direct institutional repository links

OATD.org doesn't provide a public API, so we use careful web scraping
with respectful rate limiting.

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
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Add parent for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import get_pdf_filename, OUTPUT_DIR

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "outputs/papers_without_doi.csv"
LOG_FILE = BASE_DIR / "logs/thesis_download_log.csv"

# Rate limiting (be very conservative to avoid blocks)
DELAY_GOOGLE_SCHOLAR = 5.0  # seconds (Google is strict)
DELAY_OATD = 2.0  # seconds (be respectful)
DELAY_REPOSITORY = 1.0  # seconds
REQUEST_TIMEOUT = 30

# User agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Thesis keywords for identification
THESIS_KEYWORDS = [
    'thesis', 'dissertation', 'phd', 'ph.d', 'ph d',
    'master', 'msc', 'm.sc', 'bachelor', 'bsc', 'b.sc',
    'doctoral', 'doctorate', 'graduate thesis',
    'undergraduate thesis', 'honours thesis'
]

# ============================================================================
# THESIS IDENTIFICATION
# ============================================================================

def is_thesis(title, journal=None):
    """
    Identify if a paper is likely a thesis/dissertation.

    Args:
        title: Paper title
        journal: Journal/source name

    Returns:
        bool
    """
    if not title:
        return False

    title_lower = str(title).lower()
    journal_lower = str(journal).lower() if journal else ""

    # Check title for thesis keywords
    for keyword in THESIS_KEYWORDS:
        if keyword in title_lower or keyword in journal_lower:
            return True

    return False


# ============================================================================
# GOOGLE SCHOLAR SEARCH
# ============================================================================

def search_google_scholar(title, authors=None, year=None):
    """
    Search Google Scholar for a thesis.

    WARNING: Google Scholar is strict about rate limiting.
    Use with caution and respect delays.

    Args:
        title: Paper title
        authors: Author string (optional)
        year: Publication year (optional)

    Returns:
        dict with PDF URL if found
    """
    if not title:
        return None

    try:
        # Build search query
        query = title.strip()

        # Add author if available
        if authors:
            # Extract first author surname
            author_parts = authors.split(',')[0].split('&')[0].split('.')
            if author_parts:
                first_author = author_parts[0].strip()
                query = f"{query} {first_author}"

        # Google Scholar search URL
        url = "https://scholar.google.com/scholar"
        params = {
            'q': query,
            'hl': 'en',
            'as_sdt': '0,5'  # Include patents=0, exclude citations=5
        }

        if year:
            params['as_ylo'] = str(year)
            params['as_yhi'] = str(year)

        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for PDF links in results
            # Google Scholar shows [PDF] links to freely available papers
            for result in soup.select('.gs_r.gs_or.gs_scl'):
                # Check for [PDF] link
                pdf_link = result.select_one('.gs_or_ggsm a')
                if pdf_link and pdf_link.get('href'):
                    pdf_url = pdf_link['href']

                    # Verify it's actually a PDF URL
                    if '.pdf' in pdf_url.lower() or 'pdf' in urlparse(pdf_url).path.lower():
                        # Get result title for matching
                        result_title_elem = result.select_one('.gs_rt a')
                        result_title = result_title_elem.get_text() if result_title_elem else ""

                        # Simple title matching
                        title_words = set(title.lower().split()[:10])  # First 10 words
                        result_words = set(result_title.lower().split()[:10])

                        if len(title_words) > 0:
                            overlap = len(title_words & result_words) / len(title_words)

                            if overlap >= 0.5:  # At least 50% match
                                return {
                                    'pdf_url': pdf_url,
                                    'source': 'google_scholar',
                                    'matched_title': result_title,
                                    'match_score': overlap,
                                    'found': True
                                }

            # Check if we got blocked (CAPTCHA)
            if 'unusual traffic' in response.text.lower() or 'captcha' in response.text.lower():
                logging.warning("⚠️  Google Scholar CAPTCHA detected - rate limit hit")
                return {'status': 'blocked', 'source': 'google_scholar'}

        return None

    except Exception as e:
        logging.debug(f"Google Scholar error for '{title[:50]}...': {e}")
        return None


# ============================================================================
# OATD WEB SCRAPING
# ============================================================================

def search_oatd(title, authors=None):
    """
    Search OATD.org via web scraping (no API available).

    Args:
        title: Paper title
        authors: Author string (optional)

    Returns:
        dict with repository URL if found
    """
    if not title:
        return None

    try:
        # OATD search URL
        url = "https://oatd.org/oatd/search"
        params = {
            'q': title.strip(),
            'start': 0
        }

        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse search results
            # OATD results typically have links to institutional repositories
            for result in soup.select('.result'):
                # Get title
                title_elem = result.select_one('.title a')
                if not title_elem:
                    continue

                result_title = title_elem.get_text(strip=True)
                result_url = title_elem.get('href')

                # Match title
                title_words = set(title.lower().split()[:10])
                result_words = set(result_title.lower().split()[:10])

                if len(title_words) > 0:
                    overlap = len(title_words & result_words) / len(title_words)

                    if overlap >= 0.6:  # 60% match
                        return {
                            'repository_url': result_url,
                            'source': 'oatd',
                            'matched_title': result_title,
                            'match_score': overlap,
                            'found': True
                        }

        elif response.status_code == 403:
            logging.warning("⚠️  OATD blocked request (403) - may need to slow down")
            return {'status': 'blocked', 'source': 'oatd'}

        return None

    except Exception as e:
        logging.debug(f"OATD error for '{title[:50]}...': {e}")
        return None


# ============================================================================
# INSTITUTIONAL REPOSITORY PDF DOWNLOAD
# ============================================================================

def download_pdf_from_repository(url, output_path):
    """
    Download PDF from institutional repository.

    Many repositories require following links to get actual PDF.

    Args:
        url: Repository URL (may be landing page)
        output_path: Where to save PDF

    Returns:
        dict with status
    """
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/pdf,text/html,application/xhtml+xml'
        }

        # First, check if URL is direct PDF
        if url.lower().endswith('.pdf'):
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                with open(output_path, 'wb') as f:
                    f.write(response.content)

                # Verify PDF
                with open(output_path, 'rb') as f:
                    if f.read(4) == b'%PDF':
                        return {
                            'status': 'success',
                            'file_size': output_path.stat().st_size,
                            'method': 'direct_pdf'
                        }
                    else:
                        output_path.unlink()

        # Otherwise, try to find PDF link on landing page
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for PDF download links
            # Common patterns in institutional repositories
            pdf_links = []

            # Direct PDF links
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text(strip=True).lower()

                if (href.lower().endswith('.pdf') or
                    'download' in link_text or
                    'pdf' in link_text or
                    'fulltext' in link_text.lower()):

                    # Make absolute URL
                    pdf_url = urljoin(url, href)
                    pdf_links.append(pdf_url)

            # Try each PDF link
            for pdf_url in pdf_links:
                try:
                    pdf_response = requests.get(pdf_url, headers=headers, timeout=REQUEST_TIMEOUT)

                    if (pdf_response.status_code == 200 and
                        'application/pdf' in pdf_response.headers.get('Content-Type', '')):

                        with open(output_path, 'wb') as f:
                            f.write(pdf_response.content)

                        # Verify PDF
                        with open(output_path, 'rb') as f:
                            if f.read(4) == b'%PDF':
                                return {
                                    'status': 'success',
                                    'file_size': output_path.stat().st_size,
                                    'method': 'repository_page',
                                    'pdf_url': pdf_url
                                }
                            else:
                                output_path.unlink()
                except:
                    continue

        return {
            'status': 'no_pdf_found',
            'message': 'Could not locate downloadable PDF'
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download theses from multiple sources")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--test', action='store_true', help="Test mode: only process 10 papers")
    parser.add_argument('--skip-google', action='store_true', help="Skip Google Scholar (if blocked)")
    parser.add_argument('--skip-oatd', action='store_true', help="Skip OATD scraping")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("THESIS & DISSERTATION DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load papers without DOIs
    print(f"\n📖 Loading papers...")
    df = pd.read_csv(INPUT_CSV)
    print(f"✅ Loaded {len(df):,} papers")

    # Filter for thesis papers
    print(f"\n🔍 Identifying thesis/dissertation papers...")
    df['is_thesis'] = df.apply(lambda row: is_thesis(row.get('title'), row.get('journal')), axis=1)
    thesis_papers = df[df['is_thesis']].copy()
    print(f"✅ Found {len(thesis_papers):,} potential thesis/dissertation papers")

    # Show breakdown by journal
    if len(thesis_papers) > 0:
        print(f"\nTop sources:")
        journal_counts = thesis_papers['journal'].value_counts().head(10)
        for journal, count in journal_counts.items():
            print(f"  {journal[:60]:60s}: {count:>4,}")

    # Limit if requested
    if args.test:
        thesis_papers = thesis_papers.head(10)
        print(f"\n🧪 Test mode: processing {len(thesis_papers)} papers")
    elif args.max_papers:
        thesis_papers = thesis_papers.head(args.max_papers)
        print(f"\n📊 Limited to: {args.max_papers:,} papers")

    if len(thesis_papers) == 0:
        print("\n⚠️  No thesis papers to process")
        return

    # Process papers
    print(f"\n{'=' * 80}")
    print(f"SEARCHING {len(thesis_papers):,} THESIS PAPERS")
    print("=" * 80)

    if not args.skip_google:
        print("\n⚠️  WARNING: Google Scholar is strict about rate limiting!")
        print(f"   Using {DELAY_GOOGLE_SCHOLAR} second delay between requests")
        print(f"   Estimated time: ~{len(thesis_papers) * DELAY_GOOGLE_SCHOLAR / 60:.0f} minutes")

    results = []
    found_count = 0
    pdf_count = 0
    blocked_google = False
    blocked_oatd = False

    for idx, row in tqdm(thesis_papers.iterrows(), total=len(thesis_papers), desc="Searching"):
        lit_id = row['literature_id']
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year')
        journal = row.get('journal', '')

        pdf_downloaded = False
        result_data = {
            'literature_id': lit_id,
            'title': title,
            'authors': authors,
            'year': year,
            'journal': journal,
            'timestamp': datetime.now().isoformat()
        }

        # Try Google Scholar first (if not blocked)
        if not args.skip_google and not blocked_google:
            scholar_result = search_google_scholar(title, authors, year)

            if scholar_result:
                if scholar_result.get('status') == 'blocked':
                    blocked_google = True
                    logging.warning("⚠️  Google Scholar blocked - skipping remaining Scholar searches")
                elif scholar_result.get('found'):
                    found_count += 1

                    # Try to download PDF
                    filename = get_pdf_filename(authors, title, year)
                    output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    download_result = download_pdf_from_repository(
                        scholar_result['pdf_url'],
                        output_path
                    )

                    if download_result['status'] == 'success':
                        pdf_count += 1
                        pdf_downloaded = True

                    result_data.update({
                        'source': 'google_scholar',
                        'matched_title': scholar_result.get('matched_title'),
                        'match_score': scholar_result.get('match_score'),
                        'pdf_url': scholar_result.get('pdf_url'),
                        'pdf_status': download_result['status'],
                        'file_size': download_result.get('file_size', 0)
                    })

            time.sleep(DELAY_GOOGLE_SCHOLAR)

        # Try OATD if Scholar failed (and not blocked)
        if not pdf_downloaded and not args.skip_oatd and not blocked_oatd:
            oatd_result = search_oatd(title, authors)

            if oatd_result:
                if oatd_result.get('status') == 'blocked':
                    blocked_oatd = True
                    logging.warning("⚠️  OATD blocked - skipping remaining OATD searches")
                elif oatd_result.get('found'):
                    if not result_data.get('source'):  # Only if Scholar didn't find it
                        found_count += 1

                    # Try to download PDF
                    if not pdf_downloaded:
                        filename = get_pdf_filename(authors, title, year)
                        output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
                        output_path.parent.mkdir(parents=True, exist_ok=True)

                        download_result = download_pdf_from_repository(
                            oatd_result['repository_url'],
                            output_path
                        )

                        if download_result['status'] == 'success':
                            pdf_count += 1
                            pdf_downloaded = True

                        result_data.update({
                            'source': 'oatd',
                            'matched_title': oatd_result.get('matched_title'),
                            'match_score': oatd_result.get('match_score'),
                            'repository_url': oatd_result.get('repository_url'),
                            'pdf_status': download_result['status'],
                            'file_size': download_result.get('file_size', 0)
                        })

            time.sleep(DELAY_OATD)

        # If nothing found
        if not result_data.get('source'):
            result_data.update({
                'source': 'none',
                'pdf_status': 'not_found',
                'file_size': 0
            })

        results.append(result_data)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✅ Found online: {found_count:,}/{len(thesis_papers):,} ({found_count/len(thesis_papers)*100:.1f}%)")
    print(f"📥 PDFs downloaded: {pdf_count:,}/{len(thesis_papers):,} ({pdf_count/len(thesis_papers)*100:.1f}%)")

    if len(results) > 0:
        print(f"\nBreakdown by source:")
        for source, group in results_df.groupby('source'):
            print(f"  {source:25s}: {len(group):>5,}")

        print(f"\nBreakdown by PDF status:")
        for status, group in results_df.groupby('pdf_status'):
            print(f"  {status:25s}: {len(group):>5,}")

    if blocked_google:
        print(f"\n⚠️  WARNING: Google Scholar blocked our requests")
        print(f"   Consider running again later with --skip-google")

    if blocked_oatd:
        print(f"\n⚠️  WARNING: OATD blocked our requests")
        print(f"   Consider running again later with --skip-oatd")

    print(f"\n📄 Full log: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
