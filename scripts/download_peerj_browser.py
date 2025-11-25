#!/usr/bin/env python3
"""
Download PeerJ papers using browser automation.

PeerJ requires browser interaction to download PDFs.
Uses undetected-chromedriver to navigate to article page and click download.
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
INPUT_FILE = BASE_DIR / "outputs/peerj_papers_to_download.csv"
OUTPUT_DIR = BASE_DIR / "outputs/SharkPapers"
DOWNLOAD_DIR = BASE_DIR / "outputs/peerj_temp_downloads"
LOG_FILE = BASE_DIR / "logs/peerj_browser_download_log.csv"

# Rate limiting
PAGE_LOAD_WAIT = 5.0
PDF_DOWNLOAD_WAIT = 30  # Increased for slower downloads

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / "logs/peerj_browser.log"),
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


def download_peerj_pdf(driver, doi: str, literature_id: str, timeout: int = 30) -> dict:
    """
    Download PeerJ PDF by navigating to article page.

    Strategy:
    1. Navigate to DOI redirect (https://doi.org/{doi})
    2. Dismiss cookie banners and overlays
    3. Look for PDF download button/link
    4. Use JavaScript click to bypass interaction issues
    5. Wait for download
    """
    try:
        # Construct URLs
        article_url = f"https://doi.org/{doi}"
        article_id = doi.split('.')[-1]

        # Construct final filename
        final_filename = f"{literature_id}_peerj_{article_id}.pdf"
        final_path = OUTPUT_DIR / final_filename

        # Check if already exists
        if final_path.exists():
            return {
                'status': 'already_exists',
                'filename': final_filename,
                'size_bytes': final_path.stat().st_size,
                'article_url': article_url
            }

        # Clear download directory
        for old_file in DOWNLOAD_DIR.glob('*'):
            try:
                old_file.unlink()
            except:
                pass

        # Navigate to article page
        driver.get(article_url)
        time.sleep(PAGE_LOAD_WAIT)

        # Try to dismiss cookie banner/overlays
        try:
            # Common cookie banner selectors
            dismiss_selectors = [
                "//button[contains(text(), 'Accept')]",
                "//button[contains(text(), 'OK')]",
                "//button[contains(text(), 'Agree')]",
                "//button[contains(@class, 'cookie')]",
                "//a[contains(@class, 'dismiss')]"
            ]

            for selector in dismiss_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    if buttons:
                        buttons[0].click()
                        time.sleep(0.5)
                        logging.info("Dismissed overlay/banner")
                        break
                except:
                    continue
        except:
            pass

        # Look for PDF download link
        try:
            pdf_link = None
            pdf_url = None

            # Try multiple selectors
            selectors = [
                "//a[contains(@class, 'download-pdf')]",
                "//a[contains(@href, '.pdf')]",
                "//a[contains(text(), 'Download PDF')]",
                "//a[contains(text(), 'PDF')]",
                "//button[contains(@class, 'download')]"
            ]

            for selector in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        pdf_link = elements[0]
                        # Try to get href attribute
                        pdf_url = pdf_link.get_attribute('href')
                        logging.info(f"Found PDF link with selector: {selector}")
                        if pdf_url:
                            logging.info(f"PDF URL: {pdf_url}")
                        break
                except:
                    continue

            if not pdf_link:
                return {
                    'status': 'no_pdf_link',
                    'article_url': article_url,
                    'message': 'Could not find PDF download link on page'
                }

            # Scroll element into view
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pdf_link)
                time.sleep(0.5)
            except:
                pass

            # Try clicking with different methods
            click_success = False

            # Method 1: JavaScript click (most reliable for non-interactable elements)
            try:
                driver.execute_script("arguments[0].click();", pdf_link)
                click_success = True
                logging.info("Clicked PDF link with JavaScript")
            except Exception as e1:
                logging.debug(f"JavaScript click failed: {e1}")

                # Method 2: Wait for clickability then click
                try:
                    wait = WebDriverWait(driver, 5)
                    clickable = wait.until(EC.element_to_be_clickable(pdf_link))
                    clickable.click()
                    click_success = True
                    logging.info("Clicked PDF link with WebDriverWait")
                except Exception as e2:
                    logging.debug(f"WebDriverWait click failed: {e2}")

                    # Method 3: Direct navigation if we have URL
                    if pdf_url and pdf_url.startswith('http'):
                        try:
                            driver.get(pdf_url)
                            click_success = True
                            logging.info("Navigated directly to PDF URL")
                        except Exception as e3:
                            logging.error(f"All click methods failed: JS={e1}, Wait={e2}, Direct={e3}")

            if not click_success:
                return {
                    'status': 'click_error',
                    'error': 'All click methods failed',
                    'article_url': article_url
                }

        except Exception as e:
            logging.error(f"Error finding/clicking PDF link: {e}")
            return {
                'status': 'click_error',
                'error': str(e),
                'article_url': article_url
            }

        # Wait for download to complete
        download_complete = False
        for _ in range(timeout):
            time.sleep(1)

            # Check for downloaded PDF
            pdf_files = list(DOWNLOAD_DIR.glob('*.pdf'))

            if pdf_files:
                downloaded_file = pdf_files[0]

                # Check if download complete (file size stable)
                size1 = downloaded_file.stat().st_size
                time.sleep(0.5)
                size2 = downloaded_file.stat().st_size

                if size1 == size2 and size1 > 0:
                    download_complete = True
                    break

        if not download_complete:
            return {
                'status': 'download_timeout',
                'article_url': article_url,
                'message': 'Download did not complete within timeout'
            }

        # Verify and move file
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
                        'article_url': article_url
                    }

        # Move to final location
        downloaded_file.rename(final_path)

        logging.info(f"Downloaded: {final_filename} ({file_size:,} bytes)")

        return {
            'status': 'success',
            'filename': final_filename,
            'size_bytes': file_size,
            'article_url': article_url
        }

    except Exception as e:
        logging.error(f"Error downloading PDF: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download PeerJ papers with browser automation")
    parser.add_argument('--test', action='store_true', help="Test mode: 10 papers")
    parser.add_argument('--max-papers', type=int, help="Maximum papers to process")
    parser.add_argument('--headless', action='store_true', help="Run browser in headless mode")
    args = parser.parse_args()

    print("=" * 80)
    print("PEERJ BROWSER DOWNLOADER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

    # Load paper list
    if not INPUT_FILE.exists():
        print(f"\n❌ Input file not found: {INPUT_FILE}")
        print("   Run find_peerj_papers.py first")
        return

    df = pd.read_csv(INPUT_FILE)

    print(f"\n📊 Loaded {len(df):,} PeerJ papers")

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

            result = {
                'literature_id': literature_id,
                'doi': doi,
                'year': row['year'],
                'title': row['title'],
                'timestamp': datetime.now().isoformat()
            }

            try:
                # Download PDF
                download_result = download_peerj_pdf(driver, doi, str(literature_id))

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
        total_pdfs = success + already_exists

        print(f"\n✅ New PDFs downloaded: {success:,}")
        print(f"📄 Already existed: {already_exists:,}")
        print(f"📊 Total PDFs: {total_pdfs:,}")
        if len(results) > 0:
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

        # Cleanup temp directory
        for temp_file in DOWNLOAD_DIR.glob('*'):
            try:
                temp_file.unlink()
            except:
                pass


if __name__ == "__main__":
    main()
