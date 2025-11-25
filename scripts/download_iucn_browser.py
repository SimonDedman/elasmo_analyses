#!/usr/bin/env python3
"""
download_iucn_browser.py

Download IUCN PDFs using browser automation with Cloudflare bypass.

Strategy:
1. Use undetected-chromedriver to bypass Cloudflare
2. Search for each species to get assessment ID
3. Navigate directly to PDF URL: /species/pdf/{assessmentid}
4. Browser downloads PDF automatically to configured directory
5. Wait for download, then rename file with literature ID

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
import os
import glob

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/iucn_species_cleaned.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
DOWNLOAD_DIR = BASE_DIR / "outputs/iucn_temp_downloads"  # Temp download location
LOG_FILE = BASE_DIR / "logs/iucn_browser_download_log.csv"

# Rate limiting
SEARCH_DELAY = 3.0
PDF_DOWNLOAD_WAIT = 10.0  # Wait for PDF to download

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/iucn_browser.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# BROWSER SETUP
# ============================================================================

def create_browser(headless: bool = False):
    """Create browser with PDF download configuration."""

    # Create temp download directory
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    options = uc.ChromeOptions()

    if headless:
        options.add_argument('--headless=new')

    # Configure automatic PDF downloads
    options.add_experimental_option('prefs', {
        'download.default_directory': str(DOWNLOAD_DIR.absolute()),
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'plugins.always_open_pdf_externally': True,  # Don't open in browser
        'plugins.plugins_disabled': ['Chrome PDF Viewer']
    })

    driver = uc.Chrome(options=options)
    return driver


# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

def get_species_assessment_id(driver, genus: str, species: str) -> dict:
    """Search for species and extract assessment ID."""
    try:
        search_url = f"https://www.iucnredlist.org/search?query={genus}+{species}"

        driver.get(search_url)
        time.sleep(5)

        title = driver.title

        if "Just a moment" in title or "Cloudflare" in title:
            return {'found': False, 'error': 'cloudflare_blocked'}

        # Extract species links
        page_source = driver.page_source
        species_links = re.findall(r'href="(/species/(\d+)/(\d+))"', page_source)

        if species_links:
            relative_url, taxonid, assessmentid = species_links[0]

            return {
                'found': True,
                'taxonid': taxonid,
                'assessmentid': assessmentid,
                'species_url': f"https://www.iucnredlist.org{relative_url}"
            }

        return {'found': False, 'error': 'not_in_search'}

    except Exception as e:
        logging.error(f"Error searching {genus} {species}: {e}")
        return {'found': False, 'error': str(e)}


def download_pdf_with_browser(driver, assessmentid: str, literature_id: str,
                                species_name: str, timeout: int = 15) -> dict:
    """
    Download PDF by navigating to PDF URL with browser.

    Browser automatically downloads PDF to DOWNLOAD_DIR.
    We then wait for download to complete and move file.
    """
    try:
        pdf_url = f"https://www.iucnredlist.org/species/pdf/{assessmentid}"

        # Construct final filename
        safe_species = species_name.replace(' ', '_')
        final_filename = f"{literature_id}_{safe_species}_{assessmentid}.pdf"
        final_path = OUTPUT_DIR / final_filename

        # Check if already exists
        if final_path.exists():
            return {
                'status': 'already_exists',
                'filename': final_filename,
                'size_bytes': final_path.stat().st_size,
                'pdf_url': pdf_url
            }

        # Clear download directory
        for old_file in DOWNLOAD_DIR.glob('*'):
            try:
                old_file.unlink()
            except:
                pass

        # Navigate to PDF URL - browser will download automatically
        driver.get(pdf_url)

        # Wait for download to complete
        # Look for .pdf file in download directory
        download_complete = False
        for _ in range(timeout):
            time.sleep(1)

            # Check for downloaded PDF
            pdf_files = list(DOWNLOAD_DIR.glob('*.pdf'))

            if pdf_files:
                # Found a PDF
                downloaded_file = pdf_files[0]

                # Check if download is complete (file size stable)
                size1 = downloaded_file.stat().st_size
                time.sleep(0.5)
                size2 = downloaded_file.stat().st_size

                if size1 == size2 and size1 > 0:
                    # Download complete
                    download_complete = True
                    break

        if not download_complete:
            return {
                'status': 'download_timeout',
                'pdf_url': pdf_url,
                'message': 'Download did not complete within timeout'
            }

        # Move downloaded file to final location
        downloaded_file = list(DOWNLOAD_DIR.glob('*.pdf'))[0]
        file_size = downloaded_file.stat().st_size

        # Verify it's a real PDF
        if file_size < 1024:
            with open(downloaded_file, 'rb') as f:
                first_bytes = f.read(4)
                if first_bytes != b'%PDF':
                    downloaded_file.unlink()
                    return {
                        'status': 'not_pdf',
                        'size_bytes': file_size,
                        'pdf_url': pdf_url
                    }

        # Move to final location
        downloaded_file.rename(final_path)

        logging.info(f"Downloaded: {final_filename} ({file_size:,} bytes)")

        return {
            'status': 'success',
            'filename': final_filename,
            'size_bytes': file_size,
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

    parser = argparse.ArgumentParser(description="Download IUCN PDFs with browser automation")
    parser.add_argument('--test', action='store_true', help="Test mode: 10 species")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--headless', action='store_true', help="Run browser in headless mode")
    args = parser.parse_args()

    print("=" * 80)
    print("IUCN RED LIST BROWSER DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
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
    print(f"   Download directory: {DOWNLOAD_DIR}")
    driver = create_browser(headless=args.headless)
    browser_restarts = 0
    MAX_BROWSER_RESTARTS = 5

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

            try:
                # Step 1: Get assessment ID
                assessment_info = get_species_assessment_id(driver, genus, species)
                time.sleep(SEARCH_DELAY)

                if not assessment_info.get('found'):
                    result['status'] = 'not_found_in_search'
                    result['message'] = assessment_info.get('error', 'Not found')
                    results.append(result)
                    continue

                # Add assessment info
                result['taxonid'] = assessment_info['taxonid']
                result['assessmentid'] = assessment_info['assessmentid']
                result['species_url'] = assessment_info['species_url']

                # Step 2: Download PDF with browser
                download_result = download_pdf_with_browser(
                    driver,
                    assessment_info['assessmentid'],
                    str(literature_id),
                    species_name
                )

                # Merge results
                result.update(download_result)
                results.append(result)

            except Exception as e:
                error_msg = str(e)

                # Check if it's a browser connection error
                if 'Connection refused' in error_msg or 'chrome not reachable' in error_msg.lower():
                    logging.error(f"Browser crashed: {error_msg}")

                    if browser_restarts < MAX_BROWSER_RESTARTS:
                        browser_restarts += 1
                        logging.warning(f"Attempting browser restart {browser_restarts}/{MAX_BROWSER_RESTARTS}...")

                        try:
                            driver.quit()
                        except:
                            pass

                        time.sleep(5)
                        driver = create_browser(headless=args.headless)
                        logging.info("✅ Browser restarted successfully")

                        # Retry this species
                        result['status'] = 'browser_restarted'
                        result['message'] = f'Browser crash detected and restarted (attempt {browser_restarts})'
                        results.append(result)

                        # Save progress immediately after restart
                        results_df = pd.DataFrame(results)
                        results_df.to_csv(LOG_FILE, index=False)

                        continue
                    else:
                        logging.error(f"Max browser restarts ({MAX_BROWSER_RESTARTS}) exceeded")
                        result['status'] = 'browser_crash'
                        result['message'] = f'Browser crashed too many times: {error_msg}'
                        results.append(result)
                        break
                else:
                    # Other error
                    logging.error(f"Error processing {species_name}: {error_msg}")
                    result['status'] = 'error'
                    result['message'] = error_msg
                    results.append(result)

            # Save progress every 25 species
            if len(results) % 25 == 0:
                results_df = pd.DataFrame(results)
                results_df.to_csv(LOG_FILE, index=False)
                logging.info(f"Progress saved: {len(results)} species processed")

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
        timeouts = len(results_df[results_df['status'] == 'download_timeout'])
        total_pdfs = success + already_exists

        print(f"\n✅ New PDFs downloaded: {success:,}")
        print(f"📄 Already existed: {already_exists:,}")
        print(f"📊 Total PDFs: {total_pdfs:,}")
        print(f"📈 Success rate: {total_pdfs/len(results)*100:.1f}%")

        print(f"\nBreakdown by status:")
        for status, group in results_df.groupby('status'):
            print(f"  {status:30s}: {len(group):>5,}")

        if timeouts > 0:
            print(f"\n⚠️  {timeouts} PDFs timed out during download")
            print("   These may need longer wait time or retry")

        print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
        print(f"📄 Log file: {LOG_FILE}")
        print("=" * 80)

    finally:
        driver.quit()
        print(f"\n🌐 Browser closed")

        # Cleanup temp directory
        for temp_file in DOWNLOAD_DIR.glob('*'):
            try:
                temp_file.unlink()
            except:
                pass


if __name__ == "__main__":
    main()
