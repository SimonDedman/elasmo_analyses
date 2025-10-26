#!/usr/bin/env python3
"""
Sci-Hub Downloader Daemon - Continuously downloads PDFs from queue via Sci-Hub.

This process:
1. Reads pending DOIs from the shared download queue
2. Downloads PDFs via Sci-Hub (using Tor)
3. Updates queue status (success/failed)
4. Runs until queue is empty or DOI hunter completes
"""

import sqlite3
import requests
import time
from pathlib import Path
from datetime import datetime
import re

# Paths
queue_db = Path("outputs/download_queue.db")
pdf_base = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")

# Configuration
SCI_HUB_URLS = [
    'https://sci-hub.se',
    'https://sci-hub.st',
    'https://sci-hub.ru'
]
DELAY_BETWEEN_DOWNLOADS = 3.0  # Respectful delay
BATCH_SIZE = 100  # Update progress every N downloads
MAX_RETRIES = 2  # Retry failed downloads
TIMEOUT = 30  # Request timeout
USE_TOR = True  # Use Tor proxy

class SciHubDownloader:
    def __init__(self):
        self.conn = sqlite3.connect(queue_db)
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.processed_count = 0
        self.current_scihub = SCI_HUB_URLS[0]

        # Tor proxy configuration
        self.proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        } if USE_TOR else None

    def log_activity(self, action, details):
        """Log activity to database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO activity_log (timestamp, process, action, details)
            VALUES (?, 'sci_hub_downloader', ?, ?)
        """, (datetime.now().isoformat(), action, details))
        self.conn.commit()

    def get_pending_dois(self, limit=100):
        """Get pending DOIs from queue, ordered by priority."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, literature_id, doi, year, authors, title
            FROM download_queue
            WHERE status = 'pending'
            ORDER BY priority DESC, id ASC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()

    def update_status(self, queue_id, status, pdf_path=None, error_message=None):
        """Update download status in queue."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE download_queue
            SET status = ?,
                download_timestamp = ?,
                pdf_path = ?,
                error_message = ?
            WHERE id = ?
        """, (status, datetime.now().isoformat(), pdf_path, error_message, queue_id))
        self.conn.commit()

    def clean_filename(self, text, max_length=50):
        """Clean text for use in filename."""
        if not text:
            return "Unknown"

        text = str(text).strip()
        # Remove problematic characters
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'[\n\r\t]', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0]

        return text.strip()

    def extract_first_author(self, authors):
        """Extract first author's last name."""
        if not authors:
            return "Unknown"

        authors = str(authors).strip()

        # Split by & or ,
        parts = re.split(r'[&,]', authors)
        if not parts:
            return "Unknown"

        first_author = parts[0].strip()

        # Remove parentheses
        first_author = re.sub(r'\([^)]*\)', '', first_author).strip()

        # If comma format: "Smith, J." → "Smith"
        if ',' in first_author:
            last_name = first_author.split(',')[0].strip()
        else:
            # Space format: "John Smith" → "Smith"
            parts = first_author.split()
            last_name = parts[-1] if parts else "Unknown"

        return self.clean_filename(last_name, max_length=20)

    def create_filename(self, authors, year, title):
        """Create Author.Year.Title.pdf filename."""
        author = self.extract_first_author(authors)
        year_str = str(year) if year else "Unknown"
        title_clean = self.clean_filename(title, max_length=60)

        # Handle multiple authors
        if authors and ('&' in str(authors) or ',' in str(authors)):
            author = f"{author}.etal"

        return f"{author}.{year_str}.{title_clean}.pdf"

    def get_year_folder(self, year):
        """Get folder for year."""
        if year:
            year_folder = pdf_base / str(year)
        else:
            year_folder = pdf_base / "unknown_year"

        year_folder.mkdir(exist_ok=True)
        return year_folder

    def download_pdf(self, doi, year, authors, title):
        """Download PDF from Sci-Hub."""

        # Check if already downloaded
        year_folder = self.get_year_folder(year)
        filename = self.create_filename(authors, year, title)
        pdf_path = year_folder / filename

        if pdf_path.exists():
            print(f"  ✓ Already exists: {pdf_path.name}")
            return 'success', str(pdf_path), None

        # Try downloading from Sci-Hub
        for attempt in range(MAX_RETRIES):
            try:
                # Build Sci-Hub URL
                scihub_url = f"{self.current_scihub}/{doi}"

                print(f"  Downloading from {self.current_scihub}...")

                # Get Sci-Hub page
                response = requests.get(
                    scihub_url,
                    proxies=self.proxies,
                    timeout=TIMEOUT,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )

                if response.status_code != 200:
                    print(f"  ✗ Sci-Hub returned {response.status_code}")
                    continue

                # Extract PDF URL from page
                pdf_url = self.extract_pdf_url(response.text, scihub_url)

                if not pdf_url:
                    print(f"  ✗ No PDF URL found in Sci-Hub response")
                    continue

                # Download PDF
                print(f"  Downloading PDF from {pdf_url[:50]}...")
                pdf_response = requests.get(
                    pdf_url,
                    proxies=self.proxies,
                    timeout=TIMEOUT,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )

                if pdf_response.status_code != 200:
                    print(f"  ✗ PDF download returned {pdf_response.status_code}")
                    continue

                # Check if response is actually a PDF
                content_type = pdf_response.headers.get('Content-Type', '')
                if 'pdf' not in content_type.lower() and not pdf_response.content.startswith(b'%PDF'):
                    print(f"  ✗ Response is not a PDF (Content-Type: {content_type})")
                    continue

                # Save PDF
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_response.content)

                print(f"  ✓ Saved: {pdf_path.name}")
                return 'success', str(pdf_path), None

            except requests.exceptions.Timeout:
                print(f"  ✗ Timeout (attempt {attempt + 1}/{MAX_RETRIES})")
                continue

            except requests.exceptions.ProxyError:
                print(f"  ✗ Tor proxy error - is Tor running?")
                return 'failed', None, 'Tor proxy error'

            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue

        # All attempts failed
        return 'failed', None, f'Failed after {MAX_RETRIES} attempts'

    def extract_pdf_url(self, html, base_url):
        """Extract PDF URL from Sci-Hub HTML."""
        import re

        # Pattern 1: Direct PDF link
        match = re.search(r'<iframe[^>]*src="([^"]+)"', html)
        if match:
            url = match.group(1)
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = base_url.rstrip('/') + url
            return url

        # Pattern 2: Embedded PDF URL
        match = re.search(r'location\.href\s*=\s*["\']([^"\']+)["\']', html)
        if match:
            url = match.group(1)
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = base_url.rstrip('/') + url
            return url

        # Pattern 3: Direct PDF button
        match = re.search(r'<button[^>]*onclick="[^"]*location\.href=\'([^\']+)\'', html)
        if match:
            url = match.group(1)
            if url.startswith('//'):
                url = 'https:' + url
            return url

        return None

    def run(self):
        """Main download loop."""
        print("=" * 80)
        print("SCI-HUB DOWNLOADER DAEMON")
        print("=" * 80)
        print(f"\nConfiguration:")
        print(f"  Sci-Hub URL: {self.current_scihub}")
        print(f"  Using Tor: {USE_TOR}")
        print(f"  Delay: {DELAY_BETWEEN_DOWNLOADS}s")
        print(f"  Timeout: {TIMEOUT}s")
        print(f"  PDF storage: {pdf_base}")

        self.log_activity('start', f'Starting download daemon (Tor: {USE_TOR})')

        start_time = time.time()
        last_stats_time = start_time

        while True:
            # Get pending DOIs
            pending = self.get_pending_dois(limit=100)

            if not pending:
                # Check if DOI hunter is still running
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT value FROM progress WHERE key = 'doi_hunter_complete'
                """)
                result = cursor.fetchone()

                if result:
                    print("\n✓ No more pending DOIs and DOI hunter complete. Exiting.")
                    break
                else:
                    print("\n⏸ No pending DOIs. Waiting for DOI hunter to add more...")
                    time.sleep(30)  # Wait 30 seconds before checking again
                    continue

            print(f"\n{'=' * 80}")
            print(f"Processing batch of {len(pending)} DOIs...")
            print(f"{'=' * 80}")

            for queue_id, literature_id, doi, year, authors, title in pending:
                self.processed_count += 1

                print(f"\n[{self.processed_count}] {title[:60]}...")
                print(f"  DOI: {doi}")
                print(f"  Year: {year}")

                # Mark as downloading
                self.update_status(queue_id, 'downloading')

                # Download
                status, pdf_path, error_message = self.download_pdf(doi, year, authors, title)

                # Update status
                self.update_status(queue_id, status, pdf_path, error_message)

                if status == 'success':
                    self.success_count += 1
                elif status == 'failed':
                    self.failed_count += 1

                # Delay between downloads
                time.sleep(DELAY_BETWEEN_DOWNLOADS)

                # Show stats every BATCH_SIZE downloads
                if self.processed_count % BATCH_SIZE == 0:
                    elapsed = time.time() - start_time
                    rate = self.processed_count / elapsed
                    self.show_progress_stats(rate)

                # Show hourly stats
                if time.time() - last_stats_time >= 3600:
                    elapsed = time.time() - start_time
                    rate = self.processed_count / elapsed
                    self.show_progress_stats(rate)
                    last_stats_time = time.time()

        # Final statistics
        elapsed = time.time() - start_time
        self.show_final_stats(elapsed)

        self.log_activity('complete', f'Download complete: {self.success_count} successful, {self.failed_count} failed')

    def show_progress_stats(self, rate):
        """Display progress statistics."""
        print(f"\n{'=' * 80}")
        print(f"PROGRESS UPDATE")
        print(f"{'=' * 80}")
        print(f"Processed: {self.processed_count:,}")
        print(f"Success: {self.success_count:,} ({self.success_count/self.processed_count*100:.1f}%)")
        print(f"Failed: {self.failed_count:,} ({self.failed_count/self.processed_count*100:.1f}%)")
        print(f"Rate: {rate:.1f} downloads/sec ({rate*3600:.0f}/hour)")
        print(f"{'=' * 80}")

    def show_final_stats(self, elapsed):
        """Display final statistics."""
        print("\n" + "=" * 80)
        print("DOWNLOAD COMPLETE")
        print("=" * 80)
        print(f"\nTotal processed: {self.processed_count:,}")
        print(f"Successful: {self.success_count:,} ({self.success_count/self.processed_count*100:.1f}%)")
        print(f"Failed: {self.failed_count:,} ({self.failed_count/self.processed_count*100:.1f}%)")
        print(f"\nElapsed time: {elapsed/3600:.1f} hours")
        print(f"Rate: {self.processed_count/elapsed:.1f} downloads/sec")
        print(f"\nPDFs saved to: {pdf_base}")
        print("=" * 80)

    def close(self):
        """Close database connection."""
        self.conn.close()

if __name__ == "__main__":
    downloader = SciHubDownloader()
    try:
        downloader.run()
    finally:
        downloader.close()
