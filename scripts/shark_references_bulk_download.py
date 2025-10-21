#!/usr/bin/env python3
"""
Shark-References Bulk Download Strategy
Downloads the entire database once, then filters locally for all techniques.

This is MORE EFFICIENT than the technique-by-technique approach because:
1. Each paper is downloaded exactly ONCE (not 5-20 times)
2. Total API calls: ~1,750 vs 18,720
3. Time: 2-2.5 hours vs 10-15 hours
4. Future techniques: instant local query vs 6-minute search

Author: Simon Dedman
Date: 2025-10-20
"""

import requests
import pandas as pd
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
import csv
import io
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shark_references_bulk_download.log'),
        logging.StreamHandler()
    ]
)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "shark_references_bulk"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

BULK_CSV = OUTPUT_DIR / f"shark_references_complete_{datetime.now().strftime('%Y%m%d')}.csv"
CHECKPOINT_FILE = OUTPUT_DIR / "download_checkpoint.txt"


class BulkDownloader:
    """Downloads entire shark-references database"""

    def __init__(self, delay=4):
        """
        Initialize bulk downloader

        Args:
            delay: Seconds between requests (default 4 for safety)
        """
        self.base_url = "https://shark-references.com/index.php/search/search"
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://shark-references.com/search'
        })

    def find_match_all_query(self):
        """
        Test different queries to find one that returns ALL papers
        Returns the query and total count
        """
        logging.info("Testing queries to find 'match all' approach...")

        test_queries = [
            ("", "Empty query"),
            ("*", "Wildcard"),
            ("shark", "Single common term"),
            ("the", "Very common word"),
        ]

        results = []

        for query, description in test_queries:
            try:
                data = {'query_fulltext': query, 'page': 0}
                response = self.session.post(self.base_url, data=data, timeout=30)
                json_data = response.json()
                count = int(json_data.get('itemCount', 0))

                results.append((query, description, count))
                logging.info(f"  '{query}' ({description}): {count:,} results")
                time.sleep(2)

            except Exception as e:
                logging.warning(f"  '{query}' failed: {e}")

        # Return query with highest count
        if results:
            best = max(results, key=lambda x: x[2])
            logging.info(f"\n✓ Best query: '{best[0]}' ({best[1]}) = {best[2]:,} papers")
            return best[0], best[2]
        else:
            logging.error("Could not find a working query!")
            return None, 0

    def download_by_year(self, year, query=""):
        """
        Download all papers from a specific year

        Args:
            year: Year to download
            query: Search query (empty or "*" for all)

        Returns:
            List of paper dictionaries for that year
        """
        data = {
            'query_fulltext': query,
            'year_from': str(year),
            'year_to': str(year)
        }

        logging.info(f"\n{'='*80}")
        logging.info(f"DOWNLOADING YEAR: {year}")
        logging.info(f"{'='*80}")

        all_papers = []
        page = 0
        total_pages = None
        total_items = None

        try:
            while True:
                data_with_page = data.copy()
                data_with_page['page'] = page

                # Try request with retries
                max_retries = 3
                response = None

                for attempt in range(max_retries):
                    try:
                        timeout = 60 * (attempt + 1)
                        response = self.session.post(
                            self.base_url,
                            data=data_with_page,
                            timeout=timeout
                        )
                        response.raise_for_status()
                        break
                    except requests.exceptions.Timeout:
                        if attempt < max_retries - 1:
                            logging.warning(f"  Timeout on page {page}, retry {attempt+1}/{max_retries}")
                            time.sleep(5)
                        else:
                            raise

                if response is None:
                    raise Exception(f"Failed to fetch page {page}")

                # Parse JSON
                json_data = response.json()

                # Get metadata on first page
                if page == 0:
                    total_items = int(json_data.get('itemCount', 0))
                    total_pages = int(json_data.get('pageCount', 0))

                    logging.info(f"  Papers in {year}: {total_items:,}")
                    logging.info(f"  Pages: {total_pages:,}")

                    if total_items == 0:
                        logging.info(f"  No papers found for {year}")
                        return []

                # Parse results HTML
                results_html = json_data.get('results', '')
                if not results_html or results_html.strip() == '':
                    break

                soup = BeautifulSoup(results_html, 'html.parser')
                entries = soup.find_all('div', class_='list-entry')

                if not entries:
                    break

                # Parse each entry
                for entry in entries:
                    full_text = entry.get_text(separator=' ', strip=True)

                    authors_span = entry.find('span', class_='lit-authors')
                    authors = authors_span.get_text(strip=True) if authors_span else ''

                    list_text_div = entry.find('div', class_='list-text')
                    if list_text_div:
                        list_text_clone = BeautifulSoup(str(list_text_div), 'html.parser')
                        authors_in_clone = list_text_clone.find('span', class_='lit-authors')
                        if authors_in_clone:
                            authors_in_clone.extract()
                        citation = list_text_clone.get_text(separator=' ', strip=True)
                    else:
                        citation = ''

                    doi_link = entry.find('a', href=lambda x: x and 'doi.org' in x)
                    doi = doi_link.get_text(strip=True) if doi_link else ''

                    findspot_span = entry.find('span', class_='lit-findspot')
                    findspot = findspot_span.get_text(strip=True) if findspot_span else ''

                    all_papers.append({
                        'year': year,
                        'authors': authors,
                        'citation': citation,
                        'findspot': findspot,
                        'doi': doi,
                        'full_text': full_text
                    })

                # Progress
                logging.info(f"  Page {page+1}/{total_pages} - {len(entries)} entries - "
                           f"Total: {len(all_papers):,}/{total_items:,}")

                # Check if done
                page += 1
                if total_pages and page >= total_pages:
                    break

                # Polite delay
                time.sleep(self.delay)

            logging.info(f"  ✓ Year {year} complete: {len(all_papers):,} papers\n")
            return all_papers

        except Exception as e:
            logging.error(f"  ❌ Error downloading {year}: {e}")
            return all_papers

    def download_all_papers_by_year(self, query="", year_start=2025, year_end=1950, resume_year=None):
        """
        Download all papers year-by-year, newest first

        Args:
            query: Search query (empty or "*" for all)
            year_start: Start year (default 2025, newest)
            year_end: End year (default 1950, oldest)
            resume_year: Year to resume from (if interrupted)

        Returns:
            List of all paper dictionaries
        """
        logging.info(f"\n{'='*80}")
        logging.info(f"BULK DOWNLOAD STARTING")
        logging.info(f"Strategy: Year-by-year, newest first")
        logging.info(f"Years: {year_start} → {year_end}")
        if resume_year:
            logging.info(f"Resuming from: {resume_year}")
        logging.info(f"{'='*80}\n")

        all_papers = []
        page = start_page
        total_pages = None
        total_items = None

        try:
            while True:
                data_with_page = data.copy()
                data_with_page['page'] = page

                # Try request with retries
                max_retries = 3
                response = None

                for attempt in range(max_retries):
                    try:
                        timeout = 60 * (attempt + 1)
                        response = self.session.post(
                            self.base_url,
                            data=data_with_page,
                            timeout=timeout
                        )
                        response.raise_for_status()
                        break
                    except requests.exceptions.Timeout:
                        if attempt < max_retries - 1:
                            logging.warning(f"  Timeout on page {page}, retry {attempt+1}/{max_retries}")
                            time.sleep(5)
                        else:
                            raise

                if response is None:
                    raise Exception(f"Failed to fetch page {page}")

                # Parse JSON
                json_data = response.json()

                # Get metadata on first page
                if page == start_page:
                    total_items = int(json_data.get('itemCount', 0))
                    total_pages = int(json_data.get('pageCount', 0))

                    logging.info(f"Database contains: {total_items:,} papers")
                    logging.info(f"Total pages: {total_pages:,}")
                    logging.info(f"Estimated time: {(total_pages * self.delay) / 3600:.1f} hours\n")

                # Parse results HTML
                results_html = json_data.get('results', '')
                if not results_html or results_html.strip() == '':
                    logging.info(f"No more results at page {page}")
                    break

                soup = BeautifulSoup(results_html, 'html.parser')
                entries = soup.find_all('div', class_='list-entry')

                if not entries:
                    logging.info(f"No entries found on page {page}")
                    break

                # Parse each entry
                for entry in entries:
                    # Extract full text
                    full_text = entry.get_text(separator=' ', strip=True)

                    # Extract authors
                    authors_span = entry.find('span', class_='lit-authors')
                    authors = authors_span.get_text(strip=True) if authors_span else ''

                    # Extract citation
                    list_text_div = entry.find('div', class_='list-text')
                    if list_text_div:
                        list_text_clone = BeautifulSoup(str(list_text_div), 'html.parser')
                        authors_in_clone = list_text_clone.find('span', class_='lit-authors')
                        if authors_in_clone:
                            authors_in_clone.extract()
                        citation = list_text_clone.get_text(separator=' ', strip=True)
                    else:
                        citation = ''

                    # Extract DOI
                    doi_link = entry.find('a', href=lambda x: x and 'doi.org' in x)
                    doi = doi_link.get_text(strip=True) if doi_link else ''

                    # Extract findspot (journal)
                    findspot_span = entry.find('span', class_='lit-findspot')
                    findspot = findspot_span.get_text(strip=True) if findspot_span else ''

                    all_papers.append({
                        'authors': authors,
                        'citation': citation,
                        'findspot': findspot,
                        'doi': doi,
                        'full_text': full_text
                    })

                # Progress logging
                logging.info(f"Page {page+1}/{total_pages} complete - "
                           f"{len(entries)} entries - "
                           f"Total papers: {len(all_papers):,}/{total_items:,} "
                           f"({100*len(all_papers)/total_items:.1f}%)")

                # Save checkpoint every 100 pages
                if (page + 1) % 100 == 0:
                    self.save_checkpoint(page, all_papers)
                    logging.info(f"  ✓ Checkpoint saved at page {page+1}")

                # Check if done
                page += 1
                if total_pages and page >= total_pages:
                    logging.info(f"\n✓ Reached last page ({total_pages})")
                    break

                # Polite delay
                time.sleep(self.delay)

            logging.info(f"\n{'='*80}")
            logging.info(f"DOWNLOAD COMPLETE")
            logging.info(f"Total papers downloaded: {len(all_papers):,}")
            logging.info(f"{'='*80}\n")

            return all_papers

        except KeyboardInterrupt:
            logging.warning(f"\n⚠️  Download interrupted by user at page {page}")
            logging.info(f"Papers collected so far: {len(all_papers):,}")
            self.save_checkpoint(page, all_papers)
            return all_papers

        except Exception as e:
            logging.error(f"\n❌ Error at page {page}: {e}")
            logging.info(f"Papers collected before error: {len(all_papers):,}")
            self.save_checkpoint(page, all_papers)
            return all_papers

    def save_checkpoint(self, page, papers):
        """Save progress checkpoint"""
        with open(CHECKPOINT_FILE, 'w') as f:
            f.write(f"{page}\n{len(papers)}")

        # Save partial CSV
        if papers:
            checkpoint_csv = OUTPUT_DIR / f"checkpoint_page{page}.csv"
            self.save_to_csv(papers, checkpoint_csv)

    def load_checkpoint(self):
        """Load checkpoint if exists"""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    lines = f.readlines()
                    page = int(lines[0].strip())
                    count = int(lines[1].strip())

                # Load checkpoint CSV
                checkpoint_csv = OUTPUT_DIR / f"checkpoint_page{page}.csv"
                if checkpoint_csv.exists():
                    df = pd.read_csv(checkpoint_csv)
                    papers = df.to_dict('records')
                    logging.info(f"✓ Loaded checkpoint: page {page}, {count:,} papers")
                    return page + 1, papers
            except Exception as e:
                logging.warning(f"Could not load checkpoint: {e}")

        return 0, []

    def save_to_csv(self, papers, filepath=None):
        """Save papers to CSV"""
        if filepath is None:
            filepath = BULK_CSV

        df = pd.DataFrame(papers)
        df.to_csv(filepath, index=False, encoding='utf-8')

        size_mb = filepath.stat().st_size / (1024 * 1024)
        logging.info(f"✓ Saved {len(papers):,} papers to {filepath.name} ({size_mb:.1f} MB)")


def filter_for_techniques(bulk_csv, techniques_excel):
    """
    Filter the bulk download for each technique
    This is done LOCALLY without any network requests

    Args:
        bulk_csv: Path to bulk download CSV
        techniques_excel: Path to techniques database Excel
    """
    logging.info(f"\n{'='*80}")
    logging.info(f"FILTERING BULK DOWNLOAD FOR TECHNIQUES")
    logging.info(f"{'='*80}\n")

    # Load bulk download
    logging.info(f"Loading bulk download: {bulk_csv}")
    df_all = pd.read_csv(bulk_csv)
    logging.info(f"  Loaded {len(df_all):,} papers")

    # Load techniques
    logging.info(f"\nLoading techniques: {techniques_excel}")
    df_techniques = pd.read_excel(techniques_excel, sheet_name='Full_List')
    df_techniques = df_techniques[
        df_techniques['search_query'].notna() &
        (df_techniques['search_query'] != '')
    ]
    logging.info(f"  Found {len(df_techniques)} techniques with search queries")

    # Output directory for filtered results
    output_dir = PROJECT_ROOT / "outputs" / "shark_references_filtered"
    output_dir.mkdir(exist_ok=True, parents=True)

    # Process each technique
    stats = {
        'total_techniques': len(df_techniques),
        'techniques_with_results': 0,
        'total_papers_found': 0
    }

    for idx, row in df_techniques.iterrows():
        disc_code = row['discipline_code']
        tech_name = row['technique_name']
        search_query = row['search_query']
        category = row.get('category_name', '')

        logging.info(f"\n[{idx+1}/{len(df_techniques)}] {disc_code} - {tech_name}")
        logging.info(f"  Query: {search_query}")

        # Parse search query for required terms
        required_terms = []
        for term in search_query.split():
            if term.startswith('+'):
                clean_term = term[1:].replace('*', '').lower()
                if clean_term:
                    required_terms.append(clean_term)

        if not required_terms:
            logging.warning(f"  ⚠️  No required terms found in query")
            continue

        logging.info(f"  Required terms: {required_terms}")

        # Filter papers that contain ALL required terms
        mask = df_all['full_text'].str.lower().str.contains(required_terms[0], na=False)
        for term in required_terms[1:]:
            mask &= df_all['full_text'].str.lower().str.contains(term, na=False)

        df_filtered = df_all[mask]

        if len(df_filtered) == 0:
            logging.info(f"  No matching papers found")
            continue

        # Save filtered results
        clean_tech = tech_name.replace(' ', '_').replace('/', '_').lower()
        if category:
            clean_cat = category.replace(' ', '_').replace('/', '_').lower()
            filename = f"{disc_code}-{clean_cat}-{clean_tech}_{datetime.now().strftime('%Y%m%d')}.csv"
        else:
            filename = f"{disc_code}-{clean_tech}_{datetime.now().strftime('%Y%m%d')}.csv"

        filepath = output_dir / filename
        df_filtered.to_csv(filepath, index=False)

        stats['techniques_with_results'] += 1
        stats['total_papers_found'] += len(df_filtered)

        logging.info(f"  ✓ Found {len(df_filtered)} papers → {filename}")

    # Summary
    logging.info(f"\n{'='*80}")
    logging.info(f"FILTERING COMPLETE")
    logging.info(f"{'='*80}")
    logging.info(f"Techniques processed: {stats['total_techniques']}")
    logging.info(f"Techniques with results: {stats['techniques_with_results']}")
    logging.info(f"Total papers matched: {stats['total_papers_found']}")
    logging.info(f"Average papers per technique: {stats['total_papers_found']/stats['techniques_with_results']:.1f}")
    logging.info(f"Output directory: {output_dir}")
    logging.info(f"{'='*80}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Bulk download entire shark-references database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test to find best query
  python3 shark_references_bulk_download.py --test

  # Download everything
  python3 shark_references_bulk_download.py --download

  # Resume interrupted download
  python3 shark_references_bulk_download.py --download --resume

  # Filter downloaded data for techniques
  python3 shark_references_bulk_download.py --filter

  # Do everything (download + filter)
  python3 shark_references_bulk_download.py --all
        """
    )

    parser.add_argument('--test', action='store_true',
                       help='Test queries to find "match all" approach')
    parser.add_argument('--download', action='store_true',
                       help='Download entire database')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint')
    parser.add_argument('--filter', action='store_true',
                       help='Filter bulk download for techniques')
    parser.add_argument('--all', action='store_true',
                       help='Download and filter (complete workflow)')
    parser.add_argument('--delay', type=float, default=4.0,
                       help='Delay between requests (default: 4 seconds)')
    parser.add_argument('--query', type=str, default='',
                       help='Query to use for download (default: empty = all)')

    args = parser.parse_args()

    downloader = BulkDownloader(delay=args.delay)

    if args.test or (not any([args.download, args.filter, args.all])):
        # Test mode - find best query
        query, count = downloader.find_match_all_query()
        if query is not None:
            logging.info(f"\n✓ Use this query for download: '{query}'")
            logging.info(f"  Estimated time: {(count / 20 * args.delay) / 3600:.1f} hours")
        return 0

    if args.download or args.all:
        # Download mode
        start_page = 0
        existing_papers = []

        if args.resume:
            start_page, existing_papers = downloader.load_checkpoint()
            logging.info(f"Resuming from page {start_page} with {len(existing_papers):,} papers")

        # Download
        new_papers = downloader.download_all_papers(
            query=args.query,
            start_page=start_page
        )

        # Combine with existing if resuming
        all_papers = existing_papers + new_papers

        # Save final result
        downloader.save_to_csv(all_papers, BULK_CSV)

        # Clean up checkpoints
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()

    if args.filter or args.all:
        # Filter mode
        if not BULK_CSV.exists():
            logging.error(f"Bulk download not found: {BULK_CSV}")
            logging.error("Run with --download first")
            return 1

        techniques_excel = PROJECT_ROOT / "data" / "Techniques DB for Panel Review.xlsx"
        if not techniques_excel.exists():
            logging.error(f"Techniques database not found: {techniques_excel}")
            return 1

        filter_for_techniques(BULK_CSV, techniques_excel)

    return 0


if __name__ == "__main__":
    exit(main())
