#!/usr/bin/env python3
"""
download_via_scihub_tor.py

Tor-enabled Sci-Hub downloader to bypass IP blocking.

Routes all requests through Tor network for anonymity and to avoid IP bans.
Includes automatic identity rotation and robust error handling.

EDUCATIONAL/RESEARCH USE ONLY

Author: Simon Dedman / Claude
Date: 2025-10-23
"""

import pandas as pd
import requests
import socks
import socket
from pathlib import Path
from datetime import datetime
import time
import argparse
from tqdm import tqdm
import logging
import sys
from bs4 import BeautifulSoup

# Tor control for identity rotation
try:
    from stem import Signal
    from stem.control import Controller
    TOR_CONTROL_AVAILABLE = True
except ImportError:
    print("⚠️  stem not installed - identity rotation disabled")
    print("   Install with: pip install stem")
    TOR_CONTROL_AVAILABLE = False

# Add parent for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import get_pdf_filename, OUTPUT_DIR

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
SCIHUB_LOG_ORIGINAL = BASE_DIR / "logs/scihub_download_log.csv"
SCIHUB_TOR_LOG = BASE_DIR / "logs/scihub_tor_download_log.csv"

# Sci-Hub mirrors (prioritized by speed/reliability)
SCIHUB_MIRRORS = [
    "https://sci-hub.se",
    "https://sci-hub.ru",
    "https://sci-hub.wf",
    "https://sci-hub.st",
    "https://sci-hub.cat",
    "https://sci-hub.ren"
]

# Use first mirror by default (can be changed via --mirror argument)
SCIHUB_MIRROR = SCIHUB_MIRRORS[0]

# Tor configuration
TOR_PROXY_HOST = "localhost"
TOR_PROXY_PORT = 9050
TOR_CONTROL_PORT = 9051

# Rate limiting (more conservative with Tor)
DELAY_BETWEEN_REQUESTS = 5.0  # seconds (slower for safety)
REQUEST_TIMEOUT = 45  # seconds (Tor is slower)
MAX_RETRIES = 2

# Identity rotation
ROTATE_IDENTITY_EVERY = 100  # Successful downloads before rotating

# User agent rotation (appear more human-like)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / 'logs/scihub_tor_detailed.log')
    ]
)

# ============================================================================
# TOR FUNCTIONS
# ============================================================================

def setup_tor_proxy():
    """Configure requests to use Tor SOCKS proxy."""
    try:
        socks.set_default_proxy(socks.SOCKS5, TOR_PROXY_HOST, TOR_PROXY_PORT)
        socket.socket = socks.socksocket
        logging.info("✅ Tor proxy configured")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to configure Tor proxy: {e}")
        return False


def test_tor_connection():
    """Test if Tor is working by checking current IP."""
    try:
        # Get IP via Tor
        response = requests.get("https://api.ipify.org?format=json", timeout=30)
        tor_ip = response.json()['ip']
        logging.info(f"✅ Connected via Tor - IP: {tor_ip}")
        return True
    except Exception as e:
        logging.error(f"❌ Tor connection test failed: {e}")
        return False


def rotate_tor_identity():
    """Rotate Tor identity to get new exit node."""
    if not TOR_CONTROL_AVAILABLE:
        logging.warning("⚠️  Cannot rotate identity - stem not installed")
        return False

    try:
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            logging.info("🔄 Tor identity rotated")
            time.sleep(5)  # Wait for new circuit
            return True
    except Exception as e:
        logging.warning(f"⚠️  Could not rotate identity: {e}")
        return False


def get_user_agent():
    """Get random user agent for this request."""
    import random
    return random.choice(USER_AGENTS)


# ============================================================================
# SCI-HUB FUNCTIONS
# ============================================================================

def download_from_scihub(doi, mirror, output_path, lit_id):
    """
    Download paper from Sci-Hub using DOI via Tor.

    Args:
        doi: Paper DOI
        mirror: Sci-Hub mirror URL
        output_path: Where to save PDF
        lit_id: Literature ID

    Returns:
        dict with status, message, file_size
    """
    if not doi:
        return {'status': 'no_doi', 'message': 'No DOI available', 'file_size': 0}

    # Construct Sci-Hub URL - try simple format first
    scihub_url = f"{mirror}/{doi}"

    headers = {
        'User-Agent': get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    for attempt in range(MAX_RETRIES):
        try:
            # Get Sci-Hub page
            response = requests.get(scihub_url, headers=headers, timeout=REQUEST_TIMEOUT,
                                   allow_redirects=True)

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '').lower()

                # Check if we got a PDF directly
                if 'application/pdf' in content_type or response.content[:4] == b'%PDF':
                    # Save PDF
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(response.content)

                    file_size = output_path.stat().st_size

                    # Verify PDF
                    with open(output_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'%PDF':
                            return {
                                'status': 'success',
                                'message': 'Downloaded via Sci-Hub (Tor)',
                                'file_size': file_size
                            }
                        else:
                            output_path.unlink()
                            return {
                                'status': 'error',
                                'message': 'Not a valid PDF',
                                'file_size': 0
                            }

                # Got HTML page
                elif 'text/html' in content_type:
                    # Check for error messages
                    if len(response.content) < 100:
                        # Short response like "ERROR"
                        return {
                            'status': 'error',
                            'message': f'Short response: {response.text[:50]}',
                            'file_size': 0
                        }

                    # Check for "article is missing" message
                    response_lower = response.text.lower()
                    if ('отсутствует в базе' in response_lower or
                        'article not found' in response_lower or
                        'article is not found' in response_lower or
                        'not found' in response_lower[:500]):  # Check early in response
                        return {
                            'status': 'not_in_scihub',
                            'message': 'Article missing from Sci-Hub database',
                            'file_size': 0
                        }

                    # Parse HTML for PDF link
                    soup = BeautifulSoup(response.text, 'html.parser')

                    pdf_url = None

                    # Look for embed tag with PDF
                    embed_tag = soup.find('embed', {'type': 'application/pdf'})
                    if embed_tag and embed_tag.get('src'):
                        pdf_url = embed_tag['src']

                    # Look for iframe with PDF
                    if not pdf_url:
                        iframe_tag = soup.find('iframe', src=lambda x: x and '.pdf' in x)
                        if iframe_tag and iframe_tag.get('src'):
                            pdf_url = iframe_tag['src']

                    # Look for any PDF link
                    if not pdf_url:
                        for tag in soup.find_all(['a', 'embed', 'iframe', 'object'], src=True):
                            src = tag.get('src', '') or tag.get('href', '')
                            if '.pdf' in src or 'pdf' in src.lower():
                                pdf_url = src
                                break

                    # Try button with onclick location
                    if not pdf_url:
                        button = soup.find('button', id='save')
                        if button and button.get('onclick'):
                            onclick = button['onclick']
                            # Extract URL from location.href='...'
                            import re
                            match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                            if match:
                                pdf_url = match.group(1)

                    if pdf_url:
                        # Make absolute URL if relative
                        if pdf_url.startswith('//'):
                            pdf_url = f"https:{pdf_url}"
                        elif pdf_url.startswith('/'):
                            pdf_url = f"{mirror}{pdf_url}"
                        elif not pdf_url.startswith('http'):
                            pdf_url = f"{mirror}/{pdf_url}"

                        # Download PDF from this URL
                        time.sleep(1)  # Brief pause before PDF download
                        pdf_response = requests.get(pdf_url, headers=headers,
                                                   timeout=REQUEST_TIMEOUT)

                        if pdf_response.status_code == 200 and pdf_response.content[:4] == b'%PDF':
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, 'wb') as f:
                                f.write(pdf_response.content)

                            file_size = output_path.stat().st_size

                            # Verify PDF
                            with open(output_path, 'rb') as f:
                                header = f.read(4)
                                if header == b'%PDF':
                                    return {
                                        'status': 'success',
                                        'message': 'Downloaded via Sci-Hub (Tor, extracted link)',
                                        'file_size': file_size
                                    }
                                else:
                                    output_path.unlink()

                    # Could not extract PDF
                    return {
                        'status': 'error',
                        'message': 'Could not extract PDF from Sci-Hub page',
                        'file_size': 0
                    }

            elif response.status_code == 403:
                if attempt < MAX_RETRIES - 1:
                    logging.warning(f"403 Forbidden for {doi}, rotating identity and retrying...")
                    rotate_tor_identity()
                    time.sleep(3)
                    continue
                return {
                    'status': 'forbidden',
                    'message': 'HTTP 403 - Forbidden',
                    'file_size': 0
                }
            elif response.status_code == 404:
                return {
                    'status': 'not_found',
                    'message': 'HTTP 404 - Not found',
                    'file_size': 0
                }
            else:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'file_size': 0
                }

        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                logging.warning(f"Timeout for {doi}, retrying...")
                time.sleep(2 ** attempt)
                continue
            return {
                'status': 'timeout',
                'message': 'Request timed out',
                'file_size': 0
            }
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logging.warning(f"Error for {doi}: {str(e)[:50]}, retrying...")
                time.sleep(2 ** attempt)
                continue
            return {
                'status': 'error',
                'message': f'Error: {str(e)[:100]}',
                'file_size': 0
            }

    return {
        'status': 'error',
        'message': 'Max retries exceeded',
        'file_size': 0
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Download papers via Sci-Hub through Tor network"
    )
    parser.add_argument('--max-papers', type=int, help="Maximum papers to attempt")
    parser.add_argument('--start-year', type=int, help="Start from this year")
    parser.add_argument('--end-year', type=int, help="End at this year")
    parser.add_argument('--mirror', type=str, choices=range(len(SCIHUB_MIRRORS)),
                       help=f"Mirror index (0-{len(SCIHUB_MIRRORS)-1})")
    parser.add_argument('--test-mode', action='store_true',
                       help="Test mode - sample 10 papers from different years")
    parser.add_argument('--resume', action='store_true',
                       help="Resume from previous run (skip already processed)")
    args = parser.parse_args()

    # Select mirror
    global SCIHUB_MIRROR
    if args.mirror is not None:
        SCIHUB_MIRROR = SCIHUB_MIRRORS[int(args.mirror)]

    print("\n" + "=" * 80)
    print("SCI-HUB TOR DOWNLOADER")
    print("=" * 80)
    print("⚠️  EDUCATIONAL/RESEARCH USE ONLY")
    print("⚠️  All downloads routed through Tor network")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mirror: {SCIHUB_MIRROR}")

    # Setup Tor
    print("\n🔧 Configuring Tor proxy...")
    if not setup_tor_proxy():
        print("\n❌ Failed to setup Tor proxy")
        print("Make sure Tor is installed and running:")
        print("  sudo apt-get install tor")
        print("  sudo systemctl start tor")
        return

    # Test Tor connection
    print("🧪 Testing Tor connection...")
    if not test_tor_connection():
        print("\n❌ Tor connection test failed")
        print("Check if Tor is running: sudo systemctl status tor")
        return

    # Load database
    print(f"\n📖 Loading database...")

    # Load original Sci-Hub log to get papers that need retrying
    if SCIHUB_LOG_ORIGINAL.exists():
        original_log = pd.read_csv(SCIHUB_LOG_ORIGINAL)
        failed_papers = original_log[
            (original_log['status'] == 'error') |
            (original_log['status'] == 'forbidden')
        ]
        print(f"✅ Found {len(failed_papers):,} previously failed papers to retry")

        # If resuming, check what we've already processed
        already_processed = set()
        if args.resume and SCIHUB_TOR_LOG.exists():
            tor_log = pd.read_csv(SCIHUB_TOR_LOG)
            already_processed = set(tor_log['doi'].dropna())
            print(f"📋 Resuming - already processed {len(already_processed):,} papers")

        # Filter out already processed
        papers_to_try = failed_papers[~failed_papers['doi'].isin(already_processed)]
        print(f"📊 Papers remaining to try: {len(papers_to_try):,}")

    else:
        print("⚠️  No original Sci-Hub log found, will try all papers with DOIs")
        # Fallback to trying all papers (requires database)
        # Note: This assumes database loading works - may need fixing
        papers_to_try = None

    if papers_to_try is None or len(papers_to_try) == 0:
        print("\n⚠️  No papers to download")
        return

    # Test mode - sample papers
    if args.test_mode:
        print("\n🧪 TEST MODE - Sampling 10 papers from different years")
        papers_to_try = papers_to_try.sample(min(10, len(papers_to_try)))

    # Apply filters
    if args.start_year or args.end_year:
        if 'year' in papers_to_try.columns:
            if args.start_year:
                papers_to_try = papers_to_try[papers_to_try['year'] >= args.start_year]
            if args.end_year:
                papers_to_try = papers_to_try[papers_to_try['year'] <= args.end_year]
            print(f"📊 After year filter: {len(papers_to_try):,}")

    # Limit if requested
    if args.max_papers:
        papers_to_try = papers_to_try.head(args.max_papers)
        print(f"📊 Limited to: {args.max_papers:,} papers")

    # Download
    print(f"\n{'=' * 80}")
    print(f"DOWNLOADING {len(papers_to_try):,} PAPERS VIA TOR")
    print("=" * 80)

    results = []
    success_count = 0
    identity_rotation_counter = 0

    for idx, row in tqdm(papers_to_try.iterrows(), total=len(papers_to_try),
                        desc="Downloading"):
        lit_id = row.get('literature_id', 'unknown')
        doi = row['doi']

        # Get title/authors/year from row or original log
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year', 'unknown')

        # Create output path
        if authors and title:
            filename = get_pdf_filename(authors, title, year)
        else:
            # Fallback filename
            filename = f"{doi.replace('/', '_')}.pdf"

        output_path = OUTPUT_DIR / str(year if year else 'unknown_year') / filename

        # Skip if already exists
        if output_path.exists():
            logging.info(f"⏭️  Skipping {doi} - already exists")
            continue

        # Download from Sci-Hub via Tor
        result = download_from_scihub(doi, SCIHUB_MIRROR, output_path, lit_id)

        if result['status'] == 'success':
            success_count += 1
            identity_rotation_counter += 1

            # Rotate identity periodically
            if identity_rotation_counter >= ROTATE_IDENTITY_EVERY:
                logging.info(f"🔄 Rotating Tor identity after {identity_rotation_counter} successes")
                rotate_tor_identity()
                identity_rotation_counter = 0

        results.append({
            'literature_id': lit_id,
            'doi': doi,
            'status': result['status'],
            'message': result['message'],
            'file_size': result['file_size'],
            'year': year,
            'timestamp': datetime.now().isoformat()
        })

        # Save progress periodically
        if len(results) % 50 == 0:
            results_df = pd.DataFrame(results)
            results_df.to_csv(SCIHUB_TOR_LOG, index=False)

        # Respectful delay
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save final log
    results_df = pd.DataFrame(results)
    results_df.to_csv(SCIHUB_TOR_LOG, index=False)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✅ Successfully downloaded: {success_count:,}/{len(papers_to_try):,}")
    print(f"📊 Success rate: {success_count/len(papers_to_try)*100:.1f}%")
    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status}: {len(group):,}")

    if success_count > 0:
        total_size = results_df[results_df['status'] == 'success']['file_size'].sum()
        print(f"\n💾 Total data downloaded: {total_size / (1024**3):.2f} GB")

    print(f"\n📄 Log saved: {SCIHUB_TOR_LOG}")
    print("=" * 80)


if __name__ == "__main__":
    main()
