#!/usr/bin/env python3
"""
retry_peerj_timeouts.py

Retry PeerJ papers that timed out with:
1. Longer timeout (120 seconds vs 30)
2. Better download detection
3. Multiple retry attempts

Author: Simon Dedman / Claude
Date: 2025-11-20
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import time
from tqdm import tqdm
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "outputs/peerj_timeouts_for_retry.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
DOWNLOAD_DIR = BASE_DIR / "outputs/peerj_temp_downloads"
LOG_FILE = BASE_DIR / "logs/peerj_timeout_retry_log.csv"

# INCREASED TIMEOUT
PAGE_LOAD_WAIT = 10.0
PDF_DOWNLOAD_WAIT = 120  # 2 minutes instead of 30 seconds
POLL_INTERVAL = 5  # Check for download every 5 seconds

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/peerj_timeout_retry.log"),
        logging.StreamHandler()
    ]
)

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


def wait_for_download(download_dir: Path, timeout: int = 120, poll_interval: int = 5) -> Path:
    """
    Wait for a file to appear in download directory.
    Poll filesystem every poll_interval seconds.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Check for any new PDF files
        pdf_files = list(download_dir.glob('*.pdf'))

        # Filter out incomplete downloads (.crdownload, .tmp)
        complete_pdfs = [f for f in pdf_files if not f.suffix in ['.crdownload', '.tmp']]

        if complete_pdfs:
            # Return the most recent one
            latest_pdf = max(complete_pdfs, key=lambda f: f.stat().st_mtime)
            return latest_pdf

        time.sleep(poll_interval)

    return None


def download_peerj_pdf_retry(driver, doi: str, literature_id: str, max_attempts: int = 3) -> dict:
    """
    Download PeerJ PDF with improved timeout handling.
    """
    article_url = f"https://doi.org/{doi}"
    article_id = doi.split('.')[-1]

    final_filename = f"{literature_id}_peerj_{article_id}.pdf"
    final_path = OUTPUT_DIR / final_filename

    # Check if already exists
    if final_path.exists():
        return {
            'status': 'already_exists',
            'filename': final_filename,
            'size_bytes': final_path.stat().st_size
        }

    for attempt in range(max_attempts):
        try:
            # Clear download directory
            for old_file in DOWNLOAD_DIR.glob('*'):
                try:
                    old_file.unlink()
                except:
                    pass

            logging.info(f"Attempt {attempt + 1}/{max_attempts}: {article_url}")

            # Navigate to article page
            driver.get(article_url)
            time.sleep(PAGE_LOAD_WAIT)

            # Try multiple PDF download strategies
            download_clicked = False

            # Strategy 1: Direct PDF download button
            try:
                pdf_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href*=".pdf"]'))
                )
                driver.execute_script("arguments[0].click();", pdf_button)
                logging.info("Clicked PDF download button (Strategy 1)")
                download_clicked = True
            except:
                pass

            # Strategy 2: Download menu
            if not download_clicked:
                try:
                    download_link = driver.find_element(By.LINK_TEXT, "Download")
                    driver.execute_script("arguments[0].click();", download_link)
                    time.sleep(2)

                    pdf_option = driver.find_element(By.LINK_TEXT, "PDF")
                    driver.execute_script("arguments[0].click();", pdf_option)
                    logging.info("Clicked Download > PDF (Strategy 2)")
                    download_clicked = True
                except:
                    pass

            # Strategy 3: Any PDF link
            if not download_clicked:
                try:
                    all_links = driver.find_elements(By.TAG_NAME, 'a')
                    for link in all_links:
                        href = link.get_attribute('href')
                        if href and '.pdf' in href.lower():
                            driver.execute_script("arguments[0].click();", link)
                            logging.info(f"Clicked PDF link: {href[:50]}... (Strategy 3)")
                            download_clicked = True
                            break
                except:
                    pass

            if not download_clicked:
                logging.warning(f"Could not find PDF download link")
                continue

            # Wait for download with polling
            logging.info(f"Waiting up to {PDF_DOWNLOAD_WAIT}s for download...")
            downloaded_file = wait_for_download(DOWNLOAD_DIR, timeout=PDF_DOWNLOAD_WAIT, poll_interval=POLL_INTERVAL)

            if downloaded_file and downloaded_file.exists():
                file_size = downloaded_file.stat().st_size

                if file_size > 10240:  # At least 10KB
                    # Move to final location
                    downloaded_file.rename(final_path)

                    logging.info(f"✓ Downloaded: {final_filename} ({file_size:,} bytes)")

                    return {
                        'status': 'success',
                        'filename': final_filename,
                        'size_bytes': file_size,
                        'article_url': article_url,
                        'attempts': attempt + 1
                    }
                else:
                    logging.warning(f"File too small: {file_size} bytes")
                    downloaded_file.unlink()
            else:
                logging.warning(f"Download timeout after {PDF_DOWNLOAD_WAIT}s")

        except Exception as e:
            logging.error(f"Attempt {attempt + 1} error: {e}")
            time.sleep(5)

    return {
        'status': 'failed',
        'message': f'Failed after {max_attempts} attempts',
        'article_url': article_url
    }


def main():
    print("=" * 80)
    print("PEERJ TIMEOUT RETRY")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Timeout increased to: {PDF_DOWNLOAD_WAIT}s\n")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Load timeout papers
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    timeouts_df = pd.read_csv(INPUT_FILE)
    print(f"📊 Loaded {len(timeouts_df)} timeout papers to retry\n")

    # Load existing log if exists
    if LOG_FILE.exists():
        log_df = pd.read_csv(LOG_FILE)
        processed_dois = set(log_df['doi'].values)
        print(f"✅ Skipping {len(processed_dois)} already processed")
        timeouts_df = timeouts_df[~timeouts_df['doi'].isin(processed_dois)]
    else:
        log_df = pd.DataFrame()

    print(f"📊 Remaining: {len(timeouts_df)}\n")

    if len(timeouts_df) == 0:
        print("✅ All timeouts already retried!")
        return

    # Create browser
    print("Starting browser...")
    driver = create_browser(headless=False)

    try:
        results = []
        success_count = 0

        for idx, row in tqdm(timeouts_df.iterrows(), total=len(timeouts_df), desc="Retrying PeerJ"):
            doi = row['doi']
            literature_id = str(int(row['literature_id']))

            # Try download
            result = download_peerj_pdf_retry(driver, doi, literature_id)

            # Record result
            result_row = {
                'doi': doi,
                'literature_id': literature_id,
                'title': row.get('title', ''),
                'year': row.get('year', ''),
                'timestamp': datetime.now().isoformat(),
                **result
            }
            results.append(result_row)

            if result['status'] == 'success':
                success_count += 1

            # Save progress every 5 papers
            if len(results) % 5 == 0:
                results_df = pd.DataFrame(results)
                if not log_df.empty:
                    results_df = pd.concat([log_df, results_df], ignore_index=True)
                results_df.to_csv(LOG_FILE, index=False)

            time.sleep(3)

        # Final save
        results_df = pd.DataFrame(results)
        if not log_df.empty:
            results_df = pd.concat([log_df, results_df], ignore_index=True)
        results_df.to_csv(LOG_FILE, index=False)

    finally:
        driver.quit()

    print("\n" + "=" * 80)
    print("RETRY COMPLETE")
    print("=" * 80)
    print(f"✅ Successful: {success_count}/{len(timeouts_df)} ({success_count/len(timeouts_df)*100:.1f}%)")
    print(f"❌ Failed: {len(timeouts_df) - success_count}/{len(timeouts_df)}")
    print(f"\nLog saved to: {LOG_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
