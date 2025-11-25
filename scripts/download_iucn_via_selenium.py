#!/usr/bin/env python3
"""
download_iucn_via_selenium.py

Download IUCN Red List assessment PDFs using Selenium browser automation.

This script:
1. Loads species names from iucn_species_cleaned.csv
2. Uses Selenium to navigate to IUCN species pages
3. Locates and downloads assessment PDFs
4. Handles dynamic JavaScript content
5. Respects rate limits with delays

Expected success: 60-70% (600-750 PDFs from 1,098 species)

Author: Simon Dedman / Claude
Date: 2025-11-17
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import logging
from typing import Optional, Dict
from tqdm import tqdm
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/iucn_species_cleaned.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
LOG_FILE = BASE_DIR / "logs/iucn_selenium_download_log.csv"

# Rate limiting
DELAY_BETWEEN_REQUESTS = 3.0  # seconds (respectful delay)
PAGE_LOAD_TIMEOUT = 15  # seconds
ELEMENT_WAIT_TIMEOUT = 10  # seconds

# Browser configuration
USE_HEADLESS = True  # Run browser without GUI
BROWSER = "firefox"  # 'chrome' or 'firefox'

# User agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/iucn_selenium.log"),
        logging.StreamHandler()
    ]
)

# ============================================================================
# BROWSER SETUP
# ============================================================================

def create_driver(headless: bool = True):
    """Create and configure Selenium WebDriver."""

    if BROWSER == "chrome":
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument(f"user-agent={USER_AGENT}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Download preferences
        prefs = {
            "download.default_directory": str(OUTPUT_DIR),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)

        # Use webdriver-manager to automatically handle ChromeDriver installation
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

    elif BROWSER == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        options.set_preference("general.useragent.override", USER_AGENT)

        # Download preferences
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", str(OUTPUT_DIR))
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
        options.set_preference("pdfjs.disabled", True)

        # Set Firefox binary path (for Snap-based installations)
        options.binary_location = "/snap/bin/firefox"

        driver = webdriver.Firefox(options=options)

    else:
        raise ValueError(f"Unsupported browser: {BROWSER}")

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


# ============================================================================
# IUCN SCRAPING FUNCTIONS
# ============================================================================

def search_species_on_iucn(driver, genus: str, species: str) -> Optional[str]:
    """
    Search for species on IUCN Red List and return species page URL.

    Returns:
        URL to species page if found, None otherwise
    """
    species_name = f"{genus} {species}"
    search_url = f"https://www.iucnredlist.org/search?query={genus}+{species}"

    try:
        logging.debug(f"Searching for: {species_name}")
        driver.get(search_url)

        # Wait for search results to load
        wait = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT)

        # Look for species link in search results
        # IUCN search results typically have links with class 'scientific-name' or similar
        try:
            # Try to find the first result link
            species_link = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.scientific-name, a[href*='/species/']"))
            )

            species_url = species_link.get_attribute('href')
            logging.debug(f"Found species page: {species_url}")
            return species_url

        except TimeoutException:
            # Try alternative: direct URL construction
            # Pattern: /species/{taxonid}/{assessmentid}
            # Or: /species/{genus}-{species}
            direct_url = f"https://www.iucnredlist.org/species/{genus.lower()}-{species.lower()}"
            logging.debug(f"Trying direct URL: {direct_url}")
            return direct_url

    except Exception as e:
        logging.error(f"Error searching for {species_name}: {e}")
        return None


def find_pdf_on_species_page(driver, species_url: str) -> Optional[str]:
    """
    Navigate to species page and locate PDF download link.

    Returns:
        Direct PDF URL if found, None otherwise
    """
    try:
        driver.get(species_url)
        wait = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT)

        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Strategy 1: Look for explicit "Download PDF" button/link
        pdf_selectors = [
            "a[href$='.pdf']",
            "a[contains(text(), 'Download PDF')]",
            "a[contains(text(), 'PDF')]",
            "button[contains(text(), 'Download')]",
            "a.download-pdf",
            "a.btn-download"
        ]

        for selector in pdf_selectors:
            try:
                pdf_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in pdf_elements:
                    href = element.get_attribute('href')
                    if href and '.pdf' in href.lower():
                        logging.debug(f"Found PDF link: {href}")
                        return href
            except NoSuchElementException:
                continue

        # Strategy 2: Check page source for PDF URLs
        page_source = driver.page_source
        import re
        pdf_urls = re.findall(r'(https?://[^\s<>"]+\.pdf)', page_source)

        if pdf_urls:
            # Return first PDF URL found
            logging.debug(f"Found PDF in page source: {pdf_urls[0]}")
            return pdf_urls[0]

        # Strategy 3: Look for "Assessment" or "Document" links
        try:
            assessment_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Assessment")
            assessment_url = assessment_link.get_attribute('href')

            # Follow assessment link to find PDF
            driver.get(assessment_url)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Try finding PDF again on assessment page
            pdf_elements = driver.find_elements(By.CSS_SELECTOR, "a[href$='.pdf']")
            if pdf_elements:
                pdf_url = pdf_elements[0].get_attribute('href')
                logging.debug(f"Found PDF on assessment page: {pdf_url}")
                return pdf_url

        except NoSuchElementException:
            pass

        logging.debug(f"No PDF found on species page: {species_url}")
        return None

    except Exception as e:
        logging.error(f"Error finding PDF on {species_url}: {e}")
        return None


def download_pdf(pdf_url: str, genus: str, species: str, literature_id: str) -> Dict:
    """
    Download PDF from direct URL.

    Returns:
        Dict with download status
    """
    try:
        # Construct filename
        species_name = f"{genus}_{species}"
        filename = f"{literature_id}_{species_name}.pdf"
        output_path = OUTPUT_DIR / filename

        # Check if already downloaded
        if output_path.exists():
            logging.info(f"PDF already exists: {filename}")
            return {
                'status': 'already_exists',
                'filename': filename,
                'size_bytes': output_path.stat().st_size
            }

        # Download PDF
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(pdf_url, headers=headers, timeout=30, stream=True)

        if response.status_code == 200:
            # Verify it's actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and len(response.content) < 1000:
                # Likely an error page, not a PDF
                return {
                    'status': 'not_pdf',
                    'content_type': content_type,
                    'size_bytes': len(response.content)
                }

            # Save PDF
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = output_path.stat().st_size

            # Verify file is reasonable size (>1KB)
            if file_size < 1024:
                output_path.unlink()  # Delete small/corrupt file
                return {
                    'status': 'too_small',
                    'size_bytes': file_size
                }

            logging.info(f"Downloaded: {filename} ({file_size:,} bytes)")
            return {
                'status': 'success',
                'filename': filename,
                'size_bytes': file_size
            }

        else:
            return {
                'status': 'http_error',
                'status_code': response.status_code
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

def process_species(driver, row) -> Dict:
    """
    Process a single species: search, locate PDF, download.

    Returns:
        Dict with processing results
    """
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
        'extraction_confidence': row['extraction_confidence'],
        'timestamp': datetime.now().isoformat()
    }

    try:
        # Step 1: Search for species page
        species_url = search_species_on_iucn(driver, genus, species)

        if not species_url:
            result['status'] = 'not_found'
            result['message'] = 'Species page not found on IUCN'
            return result

        result['species_url'] = species_url

        # Step 2: Find PDF on species page
        pdf_url = find_pdf_on_species_page(driver, species_url)

        if not pdf_url:
            result['status'] = 'no_pdf'
            result['message'] = 'No PDF found on species page'
            return result

        result['pdf_url'] = pdf_url

        # Step 3: Download PDF
        download_result = download_pdf(pdf_url, genus, species, str(literature_id))

        result['status'] = download_result['status']
        result['filename'] = download_result.get('filename')
        result['size_bytes'] = download_result.get('size_bytes')
        result['message'] = download_result.get('error', 'Success')

        return result

    except Exception as e:
        logging.error(f"Error processing {species_name}: {e}")
        result['status'] = 'error'
        result['message'] = str(e)
        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download IUCN assessments via Selenium")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--test', action='store_true', help="Test mode: only process 10 papers")
    parser.add_argument('--browser', choices=['chrome', 'firefox'], default='firefox', help="Browser to use")
    parser.add_argument('--no-headless', action='store_true', help="Show browser GUI (for debugging)")
    args = parser.parse_args()

    global BROWSER, USE_HEADLESS
    BROWSER = args.browser
    USE_HEADLESS = not args.no_headless

    print("=" * 80)
    print("IUCN RED LIST SELENIUM SCRAPER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Browser: {BROWSER} {'(headless)' if USE_HEADLESS else '(visible)'}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load species list
    if not INPUT_FILE.exists():
        print(f"\n❌ Input file not found: {INPUT_FILE}")
        print("   Please run extract_species_names_iucn.py first")
        return

    df = pd.read_csv(INPUT_FILE)

    # Filter for individual assessments with species names
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
        print(f"📊 Limited to: {args.max_papers:,} species")

    # Load existing results to avoid re-processing
    existing_results = []
    if LOG_FILE.exists():
        existing_df = pd.read_csv(LOG_FILE)
        existing_ids = set(existing_df['literature_id'].values)
        df = df[~df['literature_id'].isin(existing_ids)]
        print(f"✅ Skipping {len(existing_ids):,} already processed")
        print(f"📊 Remaining to process: {len(df):,}")
        existing_results = existing_df.to_dict('records')

    if len(df) == 0:
        print("\n✅ All species already processed!")
        return

    # Initialize browser
    print(f"\n🌐 Starting {BROWSER} browser...")
    driver = create_driver(headless=USE_HEADLESS)

    try:
        print("\n" + "=" * 80)
        print(f"PROCESSING {len(df):,} SPECIES")
        print("=" * 80)

        results = existing_results.copy()

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
            result = process_species(driver, row)
            results.append(result)

            # Save progress every 50 species
            if len(results) % 50 == 0:
                results_df = pd.DataFrame(results)
                results_df.to_csv(LOG_FILE, index=False)
                logging.info(f"Progress saved: {len(results)} species processed")

            # Respectful delay
            time.sleep(DELAY_BETWEEN_REQUESTS)

        # Final save
        results_df = pd.DataFrame(results)
        results_df.to_csv(LOG_FILE, index=False)

        # Summary statistics
        print("\n" + "=" * 80)
        print("DOWNLOAD SUMMARY")
        print("=" * 80)

        processed = len(results) - len(existing_results)
        success = len(results_df[results_df['status'] == 'success'])
        already_exists = len(results_df[results_df['status'] == 'already_exists'])
        total_pdfs = success + already_exists

        print(f"\n📊 Processed this session: {processed:,}")
        print(f"✅ New PDFs downloaded: {success:,}")
        print(f"📄 Total PDFs: {total_pdfs:,}")
        print(f"📈 Success rate: {total_pdfs/len(results)*100:.1f}%")

        print(f"\nBreakdown by status:")
        for status, group in results_df.groupby('status'):
            print(f"  {status:20s}: {len(group):>5,}")

        print(f"\n📂 PDFs saved to: {OUTPUT_DIR}")
        print(f"📄 Log file: {LOG_FILE}")
        print("=" * 80)

    finally:
        # Always close browser
        driver.quit()
        print(f"\n🌐 Browser closed")


if __name__ == "__main__":
    main()
