#!/usr/bin/env python3
"""
download_from_researchgate.py

Download papers from ResearchGate using authenticated access.

⚠️  EDUCATIONAL/RESEARCH USE ONLY
This script automates ResearchGate access. Use responsibly and ensure
compliance with ResearchGate's Terms of Service.

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
from bs4 import BeautifulSoup
import re

# Add parent for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import get_pdf_filename, OUTPUT_DIR

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
RG_LOG = BASE_DIR / "logs/researchgate_download_log.csv"

# ResearchGate credentials
RG_EMAIL = "simon.dedman@research.gmit.ie"
RG_PASSWORD = "h5Ea^N$7V9&^FixL1VbgLbm!K8Mab^"

# Rate limiting (be respectful!)
DELAY_BETWEEN_REQUESTS = 3.0  # seconds
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2

# User agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# ============================================================================
# RESEARCHGATE FUNCTIONS
# ============================================================================

class ResearchGateSession:
    """Handle ResearchGate authentication and requests."""

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.logged_in = False

    def login(self):
        """Login to ResearchGate."""
        print("\n🔐 Logging in to ResearchGate...")

        try:
            # Get login page to retrieve CSRF token
            login_page_url = "https://www.researchgate.net/login"
            response = self.session.get(login_page_url, timeout=REQUEST_TIMEOUT)

            if response.status_code != 200:
                print(f"❌ Failed to access login page: HTTP {response.status_code}")
                return False

            # Parse CSRF token from page
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'request-token'})

            if not csrf_input:
                print("❌ Could not find CSRF token in login page")
                return False

            csrf_token = csrf_input.get('value')

            # Prepare login data
            login_data = {
                'login': self.email,
                'password': self.password,
                'request-token': csrf_token
            }

            # Submit login
            login_url = "https://www.researchgate.net/login"
            response = self.session.post(
                login_url,
                data=login_data,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )

            # Check if login successful
            if 'account' in response.url or 'profile' in response.url:
                print("✅ Successfully logged in to ResearchGate")
                self.logged_in = True
                return True
            else:
                print("❌ Login failed - check credentials")
                return False

        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def search_paper(self, doi=None, title=None):
        """
        Search for a paper on ResearchGate.

        Args:
            doi: Paper DOI
            title: Paper title

        Returns:
            dict with paper_url if found
        """
        if not self.logged_in:
            return None

        try:
            # Build search query
            if doi:
                query = doi
            elif title:
                query = title[:100]  # Limit title length
            else:
                return None

            # Search ResearchGate
            search_url = f"https://www.researchgate.net/search/publication?q={requests.utils.quote(query)}"
            response = self.session.get(search_url, timeout=REQUEST_TIMEOUT)

            if response.status_code != 200:
                return None

            # Parse search results
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for publication links
            pub_links = soup.find_all('a', href=re.compile(r'/publication/\d+'))

            if pub_links and len(pub_links) > 0:
                # Get first result
                paper_path = pub_links[0].get('href')
                paper_url = f"https://www.researchgate.net{paper_path}"
                return {
                    'found': True,
                    'paper_url': paper_url
                }

            return None

        except Exception as e:
            logging.debug(f"Search error: {e}")
            return None

    def get_pdf_url(self, paper_url):
        """
        Get PDF download URL from paper page.

        Args:
            paper_url: URL of paper on ResearchGate

        Returns:
            PDF URL if available
        """
        try:
            response = self.session.get(paper_url, timeout=REQUEST_TIMEOUT)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for PDF download link
            # ResearchGate uses various patterns for PDF links
            pdf_patterns = [
                ('a', {'class': re.compile(r'.*download.*pdf.*', re.I)}),
                ('a', {'href': re.compile(r'.*\.pdf$')}),
                ('button', {'class': re.compile(r'.*download.*', re.I)})
            ]

            for tag, attrs in pdf_patterns:
                pdf_link = soup.find(tag, attrs)
                if pdf_link:
                    href = pdf_link.get('href') or pdf_link.get('data-url')
                    if href:
                        if not href.startswith('http'):
                            href = f"https://www.researchgate.net{href}"
                        return href

            return None

        except Exception as e:
            logging.debug(f"PDF URL error: {e}")
            return None

    def download_pdf(self, pdf_url, output_path):
        """
        Download PDF from ResearchGate.

        Args:
            pdf_url: URL of PDF
            output_path: Where to save PDF

        Returns:
            dict with status, message, file_size
        """
        try:
            response = self.session.get(pdf_url, timeout=REQUEST_TIMEOUT, stream=True)

            if response.status_code == 200:
                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()

                if 'application/pdf' in content_type or pdf_url.endswith('.pdf'):
                    # Save PDF
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    file_size = output_path.stat().st_size

                    # Verify PDF
                    with open(output_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            return {
                                'status': 'success',
                                'message': 'Downloaded from ResearchGate',
                                'file_size': file_size
                            }
                        else:
                            output_path.unlink()
                            return {
                                'status': 'error',
                                'message': 'Not a valid PDF',
                                'file_size': 0
                            }
                else:
                    return {
                        'status': 'error',
                        'message': f'Wrong content type: {content_type}',
                        'file_size': 0
                    }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'file_size': 0
                }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Download error: {str(e)}',
                'file_size': 0
            }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Download papers from ResearchGate")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to attempt")
    parser.add_argument('--start-year', type=int, help="Start from this year")
    parser.add_argument('--end-year', type=int, help="End at this year")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("RESEARCHGATE DOWNLOADER")
    print("=" * 80)
    print("⚠️  EDUCATIONAL/RESEARCH USE ONLY")
    print("⚠️  Ensure compliance with ResearchGate Terms of Service")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize ResearchGate session
    rg = ResearchGateSession(RG_EMAIL, RG_PASSWORD)

    if not rg.login():
        print("\n❌ Failed to login. Exiting.")
        return

    # Load database
    print(f"\n📖 Loading database...")
    db = pd.read_parquet(DATABASE_PARQUET)
    print(f"✅ Loaded {len(db):,} papers")

    # Filter papers without PDFs
    needs_pdf = db[~db['pdf_url'].notna() | (db['pdf_url'] == '')]
    print(f"📊 Papers without PDFs: {len(needs_pdf):,}")

    # Apply year filters
    if args.start_year or args.end_year:
        if args.start_year:
            needs_pdf = needs_pdf[needs_pdf['year'] >= args.start_year]
        if args.end_year:
            needs_pdf = needs_pdf[needs_pdf['year'] <= args.end_year]
        print(f"📊 After year filter: {len(needs_pdf):,}")

    # Sort by year (recent first)
    needs_pdf = needs_pdf.sort_values('year', ascending=False, na_position='last')

    # Limit if requested
    if args.max_papers:
        needs_pdf = needs_pdf.head(args.max_papers)
        print(f"📊 Limited to: {args.max_papers:,} papers")

    if len(needs_pdf) == 0:
        print("\n⚠️  No papers to download")
        return

    # Download
    print(f"\n{'=' * 80}")
    print(f"DOWNLOADING {len(needs_pdf):,} PAPERS")
    print("=" * 80)

    results = []
    success_count = 0

    for idx, row in tqdm(needs_pdf.iterrows(), total=len(needs_pdf), desc="Downloading"):
        lit_id = row['literature_id']
        doi = row.get('doi')
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year', 'unknown')

        # Search for paper
        search_result = rg.search_paper(doi=doi, title=title)

        if search_result and search_result.get('found'):
            paper_url = search_result['paper_url']

            # Get PDF URL
            pdf_url = rg.get_pdf_url(paper_url)

            if pdf_url:
                # Create output path
                filename = get_pdf_filename(authors, title, year)
                output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Download PDF
                result = rg.download_pdf(pdf_url, output_path)

                if result['status'] == 'success':
                    success_count += 1

                results.append({
                    'literature_id': lit_id,
                    'doi': doi,
                    'status': result['status'],
                    'message': result['message'],
                    'file_size': result['file_size'],
                    'paper_url': paper_url,
                    'year': year,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                results.append({
                    'literature_id': lit_id,
                    'doi': doi,
                    'status': 'no_pdf',
                    'message': 'Paper found but no PDF available',
                    'file_size': 0,
                    'paper_url': paper_url,
                    'year': year,
                    'timestamp': datetime.now().isoformat()
                })
        else:
            results.append({
                'literature_id': lit_id,
                'doi': doi,
                'status': 'not_found',
                'message': 'Paper not found on ResearchGate',
                'file_size': 0,
                'paper_url': None,
                'year': year,
                'timestamp': datetime.now().isoformat()
            })

        # Respectful delay
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save log
    results_df = pd.DataFrame(results)
    results_df.to_csv(RG_LOG, index=False)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✅ Successfully downloaded: {success_count:,}/{len(needs_pdf):,}")
    print(f"📊 Success rate: {success_count/len(needs_pdf)*100:.1f}%")
    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status}: {len(group):,}")
    print(f"\n📄 Log saved: {RG_LOG}")
    print("=" * 80)


if __name__ == "__main__":
    main()
