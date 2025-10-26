#!/usr/bin/env python3
"""
DOI Hunter Daemon - Continuously hunts for DOIs and adds them to download queue.

This process:
1. Reads papers without DOIs from shark-references CSV
2. Searches CrossRef/DataCite APIs for DOIs
3. Adds found DOIs to the shared download queue
4. Runs until all papers are processed
"""

import sqlite3
import pandas as pd
import requests
import time
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# Paths
queue_db = Path("outputs/download_queue.db")
shark_csv = Path("outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv")
hunt_log = Path("logs/doi_hunting_progress.csv")

# Configuration
MIN_YEAR = 2010  # Only hunt for papers from 2010+
DELAY_BETWEEN_REQUESTS = 1.0  # Respectful API delay
BATCH_SIZE = 50  # Save progress every N papers
CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence for DOI match

class DOIHunter:
    def __init__(self):
        self.conn = sqlite3.connect(queue_db)
        self.found_count = 0
        self.not_found_count = 0
        self.processed_count = 0

    def log_activity(self, action, details):
        """Log activity to database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO activity_log (timestamp, process, action, details)
            VALUES (?, 'doi_hunter', ?, ?)
        """, (datetime.now().isoformat(), action, details))
        self.conn.commit()

    def add_doi_to_queue(self, literature_id, doi, year, authors, title, confidence, matched_title):
        """Add found DOI to download queue."""
        cursor = self.conn.cursor()

        # Normalize DOI
        doi = doi.strip()
        doi = doi.replace('https://doi.org/', '')
        doi = doi.replace('http://doi.org/', '')
        doi = doi.replace('doi.org/', '')

        # Priority based on year
        priority = int(year) if year and year >= 1950 else 1950

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO download_queue
                (literature_id, doi, year, authors, title, source, priority, status, added_timestamp)
                VALUES (?, ?, ?, ?, ?, 'doi_hunt', ?, 'pending', ?)
            """, (
                str(literature_id),
                doi,
                int(year) if year else None,
                str(authors)[:500] if authors else None,
                str(title)[:500] if title else None,
                priority,
                datetime.now().isoformat()
            ))

            self.conn.commit()

            if cursor.rowcount > 0:
                self.found_count += 1
                self.log_activity('doi_found', f'DOI {doi} added to queue (confidence: {confidence:.2f})')
                return True
            else:
                # DOI already in queue
                return False

        except Exception as e:
            print(f"  Error adding DOI to queue: {e}")
            return False

    def normalize_title(self, title):
        """Normalize title for comparison."""
        if not title:
            return ""
        title = str(title).lower()
        # Remove punctuation and extra spaces
        title = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in title)
        title = ' '.join(title.split())
        return title

    def calculate_similarity(self, title1, title2):
        """Calculate similarity between two titles."""
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)

        if not norm1 or not norm2:
            return 0.0

        # Use SequenceMatcher for similarity
        ratio = SequenceMatcher(None, norm1, norm2).ratio()

        return ratio

    def search_crossref(self, title, authors=None, year=None):
        """Search CrossRef API for DOI."""
        try:
            url = "https://api.crossref.org/works"
            params = {
                'query.title': title,
                'rows': 5
            }

            headers = {
                'User-Agent': 'EEA-Panel-Research/1.0 (mailto:research@example.com)'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])

                for item in items:
                    result_title = item.get('title', [''])[0]
                    result_doi = item.get('DOI', '')

                    # Calculate similarity
                    similarity = self.calculate_similarity(title, result_title)

                    if similarity >= CONFIDENCE_THRESHOLD:
                        return {
                            'doi': result_doi,
                            'source': 'crossref',
                            'confidence': similarity,
                            'matched_title': result_title
                        }

            return None

        except Exception as e:
            print(f"  CrossRef API error: {e}")
            return None

    def extract_doi_from_url(self, pdf_url):
        """Try to extract DOI from PDF URL."""
        if not pdf_url or pd.isna(pdf_url):
            return None

        url = str(pdf_url).lower()

        # Common patterns
        if 'doi.org/' in url:
            parts = url.split('doi.org/')
            if len(parts) > 1:
                doi = parts[1].split('?')[0].split('#')[0]
                return {
                    'doi': doi,
                    'source': 'url_extraction',
                    'confidence': 1.0,
                    'matched_title': 'N/A'
                }

        # Other patterns (10.xxxx/yyyy)
        import re
        doi_pattern = r'10\.\d{4,}/[^\s\'"<>]+'
        match = re.search(doi_pattern, url)
        if match:
            return {
                'doi': match.group(),
                'source': 'url_extraction',
                'confidence': 1.0,
                'matched_title': 'N/A'
            }

        return None

    def hunt_doi(self, row):
        """Hunt for DOI for a single paper."""
        literature_id = row.get('literature_id', '')
        title = row.get('title', '')
        authors = row.get('authors', '')
        year = row.get('year', None)
        pdf_url = row.get('pdf_url', '')

        # Try URL extraction first (fastest, most reliable)
        result = self.extract_doi_from_url(pdf_url)
        if result:
            return result

        # Try CrossRef API
        time.sleep(DELAY_BETWEEN_REQUESTS)
        result = self.search_crossref(title, authors, year)
        if result:
            return result

        # Not found
        self.not_found_count += 1
        return None

    def run(self):
        """Main hunting loop."""
        print("=" * 80)
        print("DOI HUNTER DAEMON")
        print("=" * 80)

        # Load papers without DOIs
        print("\nLoading papers without DOIs...")
        df = pd.read_csv(shark_csv, low_memory=False)

        # Filter papers without DOIs
        no_doi = df[df['doi'].isna() | (df['doi'] == '')].copy()
        print(f"Total papers without DOIs: {len(no_doi):,}")

        # Filter by year (2010+)
        no_doi = no_doi[no_doi['year'] >= MIN_YEAR]
        print(f"Papers from {MIN_YEAR}+: {len(no_doi):,}")

        # Sort by year (recent first)
        no_doi = no_doi.sort_values('year', ascending=False)

        print(f"\nStarting DOI hunt...")
        print(f"  Min year: {MIN_YEAR}")
        print(f"  Confidence threshold: {CONFIDENCE_THRESHOLD}")
        print(f"  API delay: {DELAY_BETWEEN_REQUESTS}s")

        self.log_activity('start', f'Starting hunt for {len(no_doi):,} papers ({MIN_YEAR}+)')

        # Prepare log
        hunt_log.parent.mkdir(exist_ok=True)
        log_entries = []

        start_time = time.time()

        # Hunt for DOIs
        for idx, row in no_doi.iterrows():
            self.processed_count += 1

            literature_id = row.get('literature_id', '')
            title = row.get('title', '')
            year = row.get('year', '')

            print(f"\n[{self.processed_count}/{len(no_doi)}] {title[:60]}...")

            result = self.hunt_doi(row)

            if result:
                # Found DOI
                print(f"  ✓ Found: {result['doi']} (source: {result['source']}, confidence: {result['confidence']:.2f})")

                # Add to queue
                added = self.add_doi_to_queue(
                    literature_id,
                    result['doi'],
                    year,
                    row.get('authors', ''),
                    title,
                    result['confidence'],
                    result['matched_title']
                )

                log_entries.append({
                    'literature_id': literature_id,
                    'title': title,
                    'year': year,
                    'found_doi': result['doi'],
                    'source': result['source'],
                    'confidence': result['confidence'],
                    'matched_title': result['matched_title'],
                    'timestamp': datetime.now().isoformat()
                })
            else:
                # Not found
                print(f"  ✗ Not found")

                log_entries.append({
                    'literature_id': literature_id,
                    'title': title,
                    'year': year,
                    'found_doi': '',
                    'source': 'not_found',
                    'confidence': 0.0,
                    'matched_title': '',
                    'timestamp': datetime.now().isoformat()
                })

            # Save progress every BATCH_SIZE papers
            if self.processed_count % BATCH_SIZE == 0:
                self.save_progress(log_entries)
                log_entries = []

                # Show stats
                elapsed = time.time() - start_time
                rate = self.processed_count / elapsed
                remaining = len(no_doi) - self.processed_count
                eta_seconds = remaining / rate if rate > 0 else 0

                print(f"\n  Progress: {self.processed_count}/{len(no_doi)} ({self.processed_count/len(no_doi)*100:.1f}%)")
                print(f"  Found: {self.found_count} | Not found: {self.not_found_count}")
                print(f"  Rate: {rate:.1f} papers/sec | ETA: {eta_seconds/3600:.1f} hours")

        # Save final progress
        if log_entries:
            self.save_progress(log_entries)

        # Final statistics
        elapsed = time.time() - start_time
        self.show_final_stats(elapsed)

        self.log_activity('complete', f'Hunt complete: {self.found_count} DOIs found, {self.not_found_count} not found')

    def save_progress(self, log_entries):
        """Save progress to log file."""
        if not log_entries:
            return

        df = pd.DataFrame(log_entries)

        if hunt_log.exists():
            df.to_csv(hunt_log, mode='a', header=False, index=False)
        else:
            df.to_csv(hunt_log, index=False)

        print(f"  Progress saved to {hunt_log}")

    def show_final_stats(self, elapsed):
        """Display final statistics."""
        print("\n" + "=" * 80)
        print("DOI HUNT COMPLETE")
        print("=" * 80)
        print(f"\nTotal processed: {self.processed_count:,}")
        print(f"DOIs found: {self.found_count:,} ({self.found_count/self.processed_count*100:.1f}%)")
        print(f"Not found: {self.not_found_count:,} ({self.not_found_count/self.processed_count*100:.1f}%)")
        print(f"\nElapsed time: {elapsed/3600:.1f} hours")
        print(f"Rate: {self.processed_count/elapsed:.1f} papers/sec")
        print(f"\nLog saved to: {hunt_log}")
        print("=" * 80)

    def close(self):
        """Close database connection."""
        self.conn.close()

if __name__ == "__main__":
    hunter = DOIHunter()
    try:
        hunter.run()
    finally:
        hunter.close()
