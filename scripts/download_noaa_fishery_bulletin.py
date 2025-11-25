#!/usr/bin/env python3
"""
download_noaa_fishery_bulletin.py

Download NOAA Fishery Bulletin PDFs using browser automation.

Strategy:
1. Use DOI to navigate to article landing page
2. Extract PDF download link from page
3. Download PDF to temp directory
4. Rename with literature ID

Note: NOAA Fishery Bulletin PDFs are in the public domain.

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
from selenium.webdriver.common.by import By

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/noaa_fishery_bulletin_papers.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
DOWNLOAD_DIR = BASE_DIR / "outputs/noaa_temp_downloads"
LOG_FILE = BASE_DIR / "logs/noaa_fishery_bulletin_log.csv"

# Rate limiting
PAGE_LOAD_WAIT = 3.0
PDF_DOWNLOAD_WAIT = 15  # Wait for PDF to download

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/noaa_fishery_bulletin.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# BROWSER SETUP
# ============================================================================

def create_browser(headless: bool = False):
    """Create browser with PDF download configuration."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    options = uc.ChromeOptions()

    if headless:
        options.add_argument('--headless=new')

    # Configure automatic PDF downloads
    options.add_experimental_option('prefs', {
        'download.default_directory': str(DOWNLOAD_DIR.absolute()),
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'plugins.always_open_pdf_externally': True,
        'plugins.plugins_disabled': ['Chrome PDF Viewer']
    })

    driver = uc.Chrome(options=options)
    return driver


# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

def construct_doi(row) -> str:
    """
    Construct DOI from paper metadata.

    NOAA Fishery Bulletin DOI pattern: 10.7755/FB.{volume}.{issue}.{article}

    Try to extract volume/issue from title, year, or other fields.
    If not possible, return None and we'll skip this paper.
    """
    # For now, return None - we'll need to manually add DOIs
    # or find them through another method
    return None


def get_pdf_url_from_doi(driver, doi: str) -> dict:
    """
    Navigate to DOI redirect and extract PDF URL from article page.

    Returns:
        dict with 'found' (bool), 'pdf_url' (str), 'article_url' (str), 'error' (str)
    """
    try:
        # Navigate to DOI
        article_url = f"https://doi.org/{doi}"
        driver.get(article_url)
        time.sleep(PAGE_LOAD_WAIT)

        # Get actual article URL after redirect
        final_url = driver.current_url

        # Extract PDF link from page
        page_source = driver.page_source

        # Look for PDF link pattern
        pdf_matches = re.findall(r'href="(/sites/default/files/pdf-content/fish-bull/[^"]+\.pdf)"', page_source)

        if pdf_matches:
            relative_pdf_url = pdf_matches[0]

            # Construct full URL
            # The page is on fisheries.noaa.gov after redirect
            pdf_url = f"https://www.fisheries.noaa.gov{relative_pdf_url}"

            return {
                'found': True,
                'pdf_url': pdf_url,
                'article_url': final_url
            }

        # Alternative: try finding any PDF link
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")

        if pdf_links:
            pdf_url = pdf_links[0].get_attribute('href')
            return {
                'found': True,
                'pdf_url': pdf_url,
                'article_url': final_url
            }

        return {
            'found': False,
            'error': 'no_pdf_link_found',
            'article_url': final_url
        }

    except Exception as e:
        logging.error(f"Error getting PDF URL for DOI {doi}: {e}")
        return {
            'found': False,
            'error': str(e)
        }


def download_pdf_with_browser(driver, pdf_url: str, literature_id: str,
                                title: str, timeout: int = 15) -> dict:
    """
    Download PDF by navigating to PDF URL with browser.

    Browser automatically downloads PDF to DOWNLOAD_DIR.
    We then wait for download to complete and move file.
    """
    try:
        # Construct final filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
        final_filename = f"{literature_id}_noaa_{safe_title}.pdf"
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
        download_complete = False
        for _ in range(timeout):
            time.sleep(1)

            # Check for downloaded PDF
            pdf_files = list(DOWNLOAD_DIR.glob('*.pdf'))

            if pdf_files:
                downloaded_file = pdf_files[0]

                # Check if download is complete (file size stable)
                size1 = downloaded_file.stat().st_size
                time.sleep(0.5)
                size2 = downloaded_file.stat().st_size

                if size1 == size2 and size1 > 0:
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

    parser = argparse.ArgumentParser(description="Download NOAA Fishery Bulletin PDFs")
    parser.add_argument('--test', action='store_true', help="Test mode: 10 papers")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--headless', action='store_true', help="Run browser in headless mode")
    parser.add_argument('--doi-file', type=str, help="CSV file with DOIs (columns: literature_id, doi)")
    args = parser.parse_args()

    print("=" * 80)
    print("NOAA FISHERY BULLETIN DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load paper list
    if not INPUT_FILE.exists():
        print(f"\n❌ Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    print(f"\n📊 Loaded {len(df):,} Fishery Bulletin papers")

    # Check if DOI file provided
    if args.doi_file:
        doi_file = Path(args.doi_file)
        if doi_file.exists():
            doi_df = pd.read_csv(doi_file)
            # Merge DOIs
            df = df.merge(doi_df[['literature_id', 'doi']], on='literature_id', how='left')
            print(f"✅ Loaded DOIs from {doi_file}")
            print(f"   Papers with DOIs: {df['doi'].notna().sum():,}")
        else:
            print(f"⚠️  DOI file not found: {doi_file}")
            print("   Papers will need DOIs to download")

    # Filter for papers with DOIs
    if 'doi' in df.columns:
        df = df[df['doi'].notna()].copy()
        print(f"📊 Papers with DOIs: {len(df):,}")
    else:
        print("\n❌ No DOI column found!")
        print("   Please provide a DOI file with --doi-file option")
        print("   or manually add DOIs to the input CSV")
        return

    if len(df) == 0:
        print("\n❌ No papers with DOIs to process!")
        return

    # Apply limits
    if args.test:
        df = df.head(10)
        print(f"🧪 Test mode: processing {len(df)} papers")
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
        print("\n✅ All papers already processed!")
        return

    # Initialize browser
    print(f"\n🌐 Starting Chrome browser...")
    print(f"   Download directory: {DOWNLOAD_DIR}")
    driver = create_browser(headless=args.headless)
    browser_restarts = 0
    MAX_BROWSER_RESTARTS = 5

    try:
        print("\n" + "=" * 80)
        print(f"PROCESSING {len(df):,} PAPERS")
        print("=" * 80)

        results = existing_results.copy()

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
            literature_id = row['literature_id']
            doi = row['doi']
            title = row.get('title', '')

            result = {
                'literature_id': literature_id,
                'doi': doi,
                'year': row.get('year', ''),
                'title': title,
                'timestamp': datetime.now().isoformat()
            }

            try:
                # Step 1: Get PDF URL from article page
                pdf_info = get_pdf_url_from_doi(driver, doi)
                time.sleep(PAGE_LOAD_WAIT)

                if not pdf_info.get('found'):
                    result['status'] = 'no_pdf_found'
                    result['message'] = pdf_info.get('error', 'PDF link not found')
                    result['article_url'] = pdf_info.get('article_url', '')
                    results.append(result)
                    continue

                # Add PDF info
                result['pdf_url'] = pdf_info['pdf_url']
                result['article_url'] = pdf_info['article_url']

                # Step 2: Download PDF with browser
                download_result = download_pdf_with_browser(
                    driver,
                    pdf_info['pdf_url'],
                    str(literature_id),
                    title
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

                        # Retry this paper
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
                    logging.error(f"Error processing DOI {doi}: {error_msg}")
                    result['status'] = 'error'
                    result['message'] = error_msg
                    results.append(result)

            # Save progress every 10 papers
            if len(results) % 10 == 0:
                results_df = pd.DataFrame(results)
                results_df.to_csv(LOG_FILE, index=False)
                logging.info(f"Progress saved: {len(results)} papers processed")

        # Final save
        results_df = pd.DataFrame(results)
        results_df.to_csv(LOG_FILE, index=False)

        # Summary
        print("\n" + "=" * 80)
        print("DOWNLOAD SUMMARY")
        print("=" * 80)

        success = len(results_df[results_df['status'] == 'success'])
        already_exists = len(results_df[results_df['status'] == 'already_exists'])
        no_pdf = len(results_df[results_df['status'] == 'no_pdf_found'])
        total_pdfs = success + already_exists

        print(f"\n✅ New PDFs downloaded: {success:,}")
        print(f"📄 Already existed: {already_exists:,}")
        print(f"📊 Total PDFs: {total_pdfs:,}")
        if len(results) > 0:
            print(f"📈 Success rate: {total_pdfs/len(results)*100:.1f}%")

        print(f"\nBreakdown by status:")
        for status, group in results_df.groupby('status'):
            print(f"  {status:30s}: {len(group):>5,}")

        if no_pdf > 0:
            print(f"\n⚠️  {no_pdf} papers had no PDF link on article page")

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
