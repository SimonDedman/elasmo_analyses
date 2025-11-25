#!/usr/bin/env python3
"""
download_iucn_ssg.py

Download IUCN Shark Specialist Group (SSG) publications.

The SSG website (https://www.iucnssg.org) hosts regional assessment reports
and other publications as direct PDF downloads without Cloudflare protection.

This script:
1. Scrapes all SSG publication pages
2. Extracts PDF download URLs
3. Matches PDFs to papers in our database
4. Downloads PDFs with proper naming

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/iucn_regional_reports.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/iucn_ssg_download_log.csv"

# SSG publication pages to scrape
SSG_PAGES = [
    "https://www.iucnssg.org/publications-status-reports.html",
    "https://www.iucnssg.org/publications-fisheries-management.html",
    "https://www.iucnssg.org/publications-conservation-strategies.html",
    "https://www.iucnssg.org/publications-migratory-species.html",
    "https://www.iucnssg.org/publications-identification-guides.html",
    "https://www.iucnssg.org/publications-trade.html",
]

# Base URL for constructing full PDF links
SSG_BASE_URL = "https://www.iucnssg.org"

# Rate limiting
DELAY_BETWEEN_REQUESTS = 2.0  # seconds

# User agent
USER_AGENT = "SharkResearchBot/1.0 (mailto:simondedman@gmail.com; Research purposes)"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/iucn_ssg.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# SSG SCRAPING FUNCTIONS
# ============================================================================

def scrape_ssg_page(url: str) -> list:
    """
    Scrape a single SSG publication page for PDF links.

    Returns:
        List of dicts with {title, year, url, pdf_url}
    """
    try:
        logging.info(f"Scraping: {url}")
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            logging.error(f"Failed to fetch {url}: HTTP {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        publications = []

        # Find all PDF links
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.IGNORECASE))

        for link in pdf_links:
            pdf_url = link.get('href')

            # Convert relative URLs to absolute
            if pdf_url.startswith('/'):
                pdf_url = SSG_BASE_URL + pdf_url

            # Extract filename
            filename = pdf_url.split('/')[-1]

            # Try to extract year and title from filename
            # Pattern: "YEAR_-_title.pdf"
            year_match = re.match(r'^(\d{4})', filename)
            year = int(year_match.group(1)) if year_match else None

            # Get title from link text or nearby text
            title = link.get_text(strip=True)
            if not title or len(title) < 10:
                # Try to find title in nearby elements
                parent = link.find_parent('div')
                if parent:
                    title_elem = parent.find('strong')
                    if title_elem:
                        title = title_elem.get_text(strip=True)

            # Clean filename for better title extraction
            if not title or title == "Picture":
                # Extract from filename
                title_from_file = filename.replace('.pdf', '').replace('_-_', ' - ')
                title_from_file = re.sub(r'^\d{4}\s*-\s*', '', title_from_file)
                title_from_file = title_from_file.replace('_', ' ').strip()
                title = title_from_file

            publications.append({
                'title': title,
                'year': year,
                'url': url,
                'pdf_url': pdf_url,
                'filename': filename
            })

        logging.info(f"Found {len(publications)} PDFs on {url}")
        return publications

    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return []


def scrape_all_ssg_pages() -> pd.DataFrame:
    """Scrape all SSG publication pages."""

    all_publications = []

    for page_url in SSG_PAGES:
        pubs = scrape_ssg_page(page_url)
        all_publications.extend(pubs)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    df = pd.DataFrame(all_publications)

    # Remove duplicates (same PDF might be listed on multiple pages)
    df = df.drop_duplicates(subset=['pdf_url'])

    return df


# ============================================================================
# MATCHING FUNCTIONS
# ============================================================================

def match_to_database(ssg_df: pd.DataFrame, db_df: pd.DataFrame) -> pd.DataFrame:
    """
    Match SSG publications to papers in our database.

    Uses title similarity and year matching.
    """

    def normalize_title(title):
        """Normalize title for comparison."""
        if not title:
            return ""
        # Convert to lowercase
        title = str(title).lower()
        # Remove special characters
        title = re.sub(r'[^\w\s]', ' ', title)
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    # Add normalized titles
    ssg_df['title_norm'] = ssg_df['title'].apply(normalize_title)
    db_df['title_norm'] = db_df['title'].apply(normalize_title)

    matches = []

    for idx, ssg_row in ssg_df.iterrows():
        best_match = None
        best_score = 0

        for _, db_row in db_df.iterrows():
            # Check year match (if available)
            year_match = (
                ssg_row['year'] is None or
                db_row['year'] is None or
                abs(ssg_row['year'] - db_row['year']) <= 1
            )

            if not year_match:
                continue

            # Simple word overlap score
            ssg_words = set(ssg_row['title_norm'].split())
            db_words = set(db_row['title_norm'].split())

            if not ssg_words or not db_words:
                continue

            # Jaccard similarity
            intersection = len(ssg_words & db_words)
            union = len(ssg_words | db_words)
            score = intersection / union if union > 0 else 0

            if score > best_score:
                best_score = score
                best_match = db_row

        if best_match is not None and best_score > 0.3:  # 30% word overlap
            matches.append({
                'literature_id': best_match['literature_id'],
                'db_title': best_match['title'],
                'db_year': best_match['year'],
                'ssg_title': ssg_row['title'],
                'ssg_year': ssg_row['year'],
                'pdf_url': ssg_row['pdf_url'],
                'filename': ssg_row['filename'],
                'match_score': best_score
            })
        else:
            # No match in database, but still downloadable
            matches.append({
                'literature_id': None,
                'db_title': None,
                'db_year': None,
                'ssg_title': ssg_row['title'],
                'ssg_year': ssg_row['year'],
                'pdf_url': ssg_row['pdf_url'],
                'filename': ssg_row['filename'],
                'match_score': 0
            })

    return pd.DataFrame(matches)


# ============================================================================
# DOWNLOAD FUNCTIONS
# ============================================================================

def download_pdf(pdf_url: str, literature_id: str, filename: str) -> dict:
    """Download a single PDF."""

    try:
        # Construct output filename
        if literature_id:
            output_filename = f"{literature_id}_{filename}"
        else:
            output_filename = filename

        output_path = OUTPUT_DIR / output_filename

        # Check if already exists
        if output_path.exists():
            logging.info(f"Already exists: {output_filename}")
            return {
                'status': 'already_exists',
                'filename': output_filename,
                'size_bytes': output_path.stat().st_size
            }

        # Download
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(pdf_url, headers=headers, timeout=60, stream=True)

        if response.status_code == 200:
            # Verify it's a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower():
                # Check first bytes for PDF signature
                first_bytes = response.content[:4]
                if first_bytes != b'%PDF':
                    return {
                        'status': 'not_pdf',
                        'content_type': content_type
                    }

            # Save PDF
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = output_path.stat().st_size

            # Verify size
            if file_size < 1024:  # Less than 1KB
                output_path.unlink()
                return {
                    'status': 'too_small',
                    'size_bytes': file_size
                }

            logging.info(f"Downloaded: {output_filename} ({file_size:,} bytes)")
            return {
                'status': 'success',
                'filename': output_filename,
                'size_bytes': file_size
            }

        else:
            return {
                'status': 'http_error',
                'status_code': response.status_code
            }

    except Exception as e:
        logging.error(f"Error downloading {pdf_url}: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("IUCN SHARK SPECIALIST GROUP PUBLICATION DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Step 1: Scrape all SSG pages
    print("📡 Scraping IUCN SSG website...")
    ssg_df = scrape_all_ssg_pages()
    print(f"✅ Found {len(ssg_df)} unique PDFs on SSG website\n")

    # Step 2: Load database
    if INPUT_FILE.exists():
        print("📖 Loading database of IUCN papers...")
        db_df = pd.read_csv(INPUT_FILE)
        print(f"✅ Loaded {len(db_df)} papers from database\n")

        # Step 3: Match to database
        print("🔗 Matching SSG PDFs to database...")
        matches_df = match_to_database(ssg_df, db_df)
        matched_count = len(matches_df[matches_df['literature_id'].notna()])
        print(f"✅ Matched {matched_count}/{len(matches_df)} PDFs to database papers\n")
    else:
        print(f"⚠️  Database file not found: {INPUT_FILE}")
        print("   Downloading all SSG PDFs without database matching\n")
        matches_df = ssg_df.copy()
        matches_df['literature_id'] = None

    # Step 4: Download PDFs
    print("=" * 80)
    print(f"DOWNLOADING {len(matches_df)} PDFs")
    print("=" * 80 + "\n")

    results = []

    for idx, row in tqdm(matches_df.iterrows(), total=len(matches_df), desc="Downloading"):
        result = download_pdf(
            row['pdf_url'],
            row.get('literature_id'),
            row['filename']
        )

        results.append({
            'literature_id': row.get('literature_id'),
            'ssg_title': row.get('ssg_title'),
            'year': row.get('ssg_year'),
            'pdf_url': row['pdf_url'],
            'filename': result.get('filename'),
            'status': result['status'],
            'size_bytes': result.get('size_bytes'),
            'match_score': row.get('match_score', 0),
            'timestamp': datetime.now().isoformat()
        })

        # Respectful delay
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(LOG_FILE, index=False)

    # Summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)

    success = len(results_df[results_df['status'] == 'success'])
    already_exists = len(results_df[results_df['status'] == 'already_exists'])
    total_pdfs = success + already_exists

    print(f"\n✅ New PDFs downloaded: {success}")
    print(f"📄 Already existed: {already_exists}")
    print(f"📊 Total PDFs: {total_pdfs}")

    print(f"\nBreakdown by status:")
    for status, group in results_df.groupby('status'):
        print(f"  {status:20s}: {len(group):>5,}")

    # Show matched vs unmatched
    matched = len(results_df[results_df['literature_id'].notna()])
    print(f"\n🔗 Matched to database: {matched}/{len(results_df)}")

    print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
    print(f"📄 Log file: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
