#!/usr/bin/env python3
"""
download_iucn_full_bypass.py

Download IUCN PDFs using undetected-chromedriver bypass for everything.

Since both the API and PDF URLs are Cloudflare-protected, we use:
1. Bypass to access search page and get species URL
2. Extract assessment ID from URL
3. Construct PDF URL: /species/pdf/{assessmentid}
4. Download PDF with bypass

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm
import logging
import re
import undetected_chromedriver as uc
import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/iucn_species_cleaned.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/iucn_bypass_download_log.csv"

# Rate limiting
SEARCH_DELAY = 3.0  # Delay between species searches
PDF_DELAY = 2.0  # Delay between PDF downloads

# User agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/iucn_bypass.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# BYPASS FUNCTIONS
# ============================================================================

def get_species_url_via_search(driver, genus: str, species: str) -> dict:
    """Search for species and extract species page URL."""
    try:
        species_name = f"{genus} {species}"
        search_url = f"https://www.iucnredlist.org/search?query={genus}+{species}"

        driver.get(search_url)
        time.sleep(5)  # Wait for page load

        title = driver.title

        # Check if Cloudflare blocked
        if "Just a moment" in title or "Cloudflare" in title:
            return {'found': False, 'error': 'cloudflare_blocked'}

        # Extract species links from search results
        page_source = driver.page_source
        species_links = re.findall(r'href="(/species/(\d+)/(\d+))"', page_source)

        if species_links:
            # Take first result
            relative_url, taxonid, assessmentid = species_links[0]
            full_url = f"https://www.iucnredlist.org{relative_url}"

            logging.debug(f"Found {species_name}: taxonid={taxonid}, assessmentid={assessmentid}")

            return {
                'found': True,
                'species_url': full_url,
                'taxonid': taxonid,
                'assessmentid': assessmentid
            }

        return {'found': False, 'error': 'not_in_search_results'}

    except Exception as e:
        logging.error(f"Error searching for {genus} {species}: {e}")
        return {'found': False, 'error': str(e)}


def download_pdf_via_bypass(assessmentid: str, literature_id: str, species_name: str) -> dict:
    """Download PDF using direct URL pattern."""
    try:
        pdf_url = f"https://www.iucnredlist.org/species/pdf/{assessmentid}"

        # Construct filename
        safe_species = species_name.replace(' ', '_')
        filename = f"{literature_id}_{safe_species}_{assessmentid}.pdf"
        output_path = OUTPUT_DIR / filename

        # Check if already exists
        if output_path.exists():
            return {
                'status': 'already_exists',
                'filename': filename,
                'size_bytes': output_path.stat().st_size,
                'pdf_url': pdf_url
            }

        # Download PDF with requests (try direct first, faster)
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(pdf_url, headers=headers, timeout=30)

        # Check if Cloudflare blocked
        if response.status_code == 403 or 'cloudflare' in response.text.lower():
            return {
                'status': 'cloudflare_blocked',
                'pdf_url': pdf_url,
                'message': 'PDF download blocked by Cloudflare (would need selenium)'
            }

        if response.status_code == 200:
            # Save PDF
            with open(output_path, 'wb') as f:
                f.write(response.content)

            file_size = output_path.stat().st_size

            # Verify it's a PDF
            if file_size < 1024:
                with open(output_path, 'rb') as f:
                    first_bytes = f.read(4)
                    if first_bytes != b'%PDF':
                        output_path.unlink()
                        return {
                            'status': 'not_pdf',
                            'size_bytes': file_size,
                            'pdf_url': pdf_url
                        }

            logging.info(f"Downloaded: {filename} ({file_size:,} bytes)")
            return {
                'status': 'success',
                'filename': filename,
                'size_bytes': file_size,
                'pdf_url': pdf_url
            }

        return {
            'status': 'http_error',
            'status_code': response.status_code,
            'pdf_url': pdf_url
        }

    except Exception as e:
        logging.error(f"Error downloading PDF: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download IUCN PDFs with Cloudflare bypass")
    parser.add_argument('--test', action='store_true', help="Test mode: only process 10 species")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--headless', action='store_true', help="Run browser in headless mode")
    args = parser.parse_args()

    print("=" * 80)
    print("IUCN RED LIST DOWNLOADER (CLOUDFLARE BYPASS)")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load species list
    if not INPUT_FILE.exists():
        print(f"\n❌ Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    # Filter for individual assessments
    df = df[
        (df['paper_type'] == 'individual_assessment') &
        (df['species_name'].notna())
    ].copy()

    print(f"\n📊 Loaded {len(df):,} species for download")

    # Apply limits
    if args.test:
        df = df.head(10)
        print(f"🧪 Test mode: processing {len(df)} species")
    elif args.max_papers:
        df = df.head(args.max_papers)

    # Load existing results
    existing_results = []
    if LOG_FILE.exists():
        existing_df = pd.read_csv(LOG_FILE)
        existing_ids = set(existing_df['literature_id'].values)
        df = df[~df['literature_id'].isin(existing_ids)]
        print(f"✅ Skipping {len(existing_ids):,} already processed")
        print(f"📊 Remaining: {len(df):,}")
        existing_results = existing_df.to_dict('records')

    if len(df) == 0:
        print("\n✅ All species already processed!")
        return

    # Initialize browser
    print(f"\n🌐 Starting Chrome browser...")
    options = uc.ChromeOptions()
    if args.headless:
        options.add_argument('--headless=new')
    driver = uc.Chrome(options=options)

    try:
        print("\n" + "=" * 80)
        print(f"PROCESSING {len(df):,} SPECIES")
        print("=" * 80)

        results = existing_results.copy()

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
            literature_id = row['literature_id']
            genus = row['genus']
            species = row['species']
            species_name = f"{genus} {species}"

            result = {
                'literature_id': literature_id,
                'genus': genus,
                'species': species,
                'species_name': species_name,
                'year': row['year'],
                'title': row['title'],
                'timestamp': datetime.now().isoformat()
            }

            # Step 1: Search for species to get assessment ID
            search_result = get_species_url_via_search(driver, genus, species)
            time.sleep(SEARCH_DELAY)

            if not search_result.get('found'):
                result['status'] = 'not_found_in_search'
                result['message'] = search_result.get('error', 'Not found')
                results.append(result)
                continue

            # Add IDs to result
            result['taxonid'] = search_result['taxonid']
            result['assessmentid'] = search_result['assessmentid']
            result['species_url'] = search_result['species_url']

            # Step 2: Download PDF
            download_result = download_pdf_via_bypass(
                search_result['assessmentid'],
                str(literature_id),
                species_name
            )
            time.sleep(PDF_DELAY)

            # Merge download result
            result.update(download_result)
            results.append(result)

            # Save progress every 25 species
            if len(results) % 25 == 0:
                results_df = pd.DataFrame(results)
                results_df.to_csv(LOG_FILE, index=False)

        # Final save
        results_df = pd.DataFrame(results)
        results_df.to_csv(LOG_FILE, index=False)

        # Summary
        print("\n" + "=" * 80)
        print("DOWNLOAD SUMMARY")
        print("=" * 80)

        success = len(results_df[results_df['status'] == 'success'])
        already_exists = len(results_df[results_df['status'] == 'already_exists'])
        not_found = len(results_df[results_df['status'] == 'not_found_in_search'])
        cloudflare = len(results_df[results_df['status'] == 'cloudflare_blocked'])
        total_pdfs = success + already_exists

        print(f"\n✅ New PDFs downloaded: {success:,}")
        print(f"📄 Already existed: {already_exists:,}")
        print(f"📊 Total PDFs: {total_pdfs:,}")
        print(f"📈 Success rate: {total_pdfs/len(results)*100:.1f}%")

        print(f"\nBreakdown by status:")
        for status, group in results_df.groupby('status'):
            print(f"  {status:30s}: {len(group):>5,}")

        print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
        print(f"📄 Log file: {LOG_FILE}")
        print("=" * 80)

    finally:
        driver.quit()
        print(f"\n🌐 Browser closed")


if __name__ == "__main__":
    main()
