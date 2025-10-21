#!/usr/bin/env python3
"""
Shark-References Complete Download with ALL Fields
Downloads basic info + fetches detailed info (abstract, keywords, taxa) for EVERY paper

This takes ~40 hours for full database but provides complete information
including abstracts which are essential for technique identification.

Author: Simon Dedman
Date: 2025-10-20
"""

import requests
import pandas as pd
import time
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shark_references_complete.log'),
        logging.StreamHandler()
    ]
)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "shark_references_bulk"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

CHECKPOINT_FILE = OUTPUT_DIR / "complete_progress.json"


class CompleteDownloader:
    """Downloads shark-references with complete details for every paper"""

    def __init__(self, delay=4, detail_delay=2):
        """
        Args:
            delay: Seconds between list page requests
            detail_delay: Seconds between detail requests
        """
        self.base_url = "https://shark-references.com/index.php/search/search"
        self.detail_url = "https://shark-references.com/literature/detailAjax"
        self.delay = delay
        self.detail_delay = detail_delay

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://shark-references.com/search'
        })

    def fetch_paper_details(self, lit_id):
        """
        Fetch detailed information for a specific paper via AJAX

        Args:
            lit_id: Literature ID

        Returns:
            Dictionary with detailed fields
        """
        url = f"{self.detail_url}/{lit_id}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            details = {}

            # Extract labeled fields (Keyword time, Keyword place, etc.)
            labels = soup.find_all('span', class_='label')
            for label in labels:
                label_text = label.get_text(strip=True).rstrip(':')
                # Get the text that follows this label (up to next <br> or label)
                value_parts = []
                for sibling in label.next_siblings:
                    if sibling.name == 'br':
                        break
                    if sibling.name == 'span' and 'label' in sibling.get('class', []):
                        break
                    if isinstance(sibling, str):
                        text = sibling.strip()
                        if text:
                            value_parts.append(text)
                    elif sibling.name:
                        text = sibling.get_text(strip=True)
                        if text:
                            value_parts.append(text)

                value = ' '.join(value_parts).strip()
                if value:
                    details[label_text.lower().replace(' ', '_')] = value

            # Look for download links (PDF, ResearchGate, etc.)
            download_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if any(x in href.lower() for x in ['.pdf', 'researchgate', 'academia.edu', 'doi.org']):
                    download_links.append(href)

            if download_links:
                details['download_links'] = '|'.join(download_links)

            return details

        except Exception as e:
            logging.warning(f"Failed to fetch details for {lit_id}: {e}")
            return {}

    def download_year_complete(self, year, query="", limit=None):
        """
        Download all papers from a year WITH complete details

        Args:
            year: Year to download
            query: Search query
            limit: Limit number of papers (for testing)

        Returns:
            List of complete paper dictionaries
        """
        data = {
            'query_fulltext': query,
            'year_from': str(year),
            'year_to': str(year)
        }

        logging.info(f"\n{'='*80}")
        logging.info(f"DOWNLOADING YEAR: {year} (WITH COMPLETE DETAILS)")
        logging.info(f"{'='*80}")

        all_papers = []
        page = 0
        total_pages = None
        total_items = None
        papers_processed = 0

        try:
            # First, get the list of papers
            while True:
                data_with_page = data.copy()
                data_with_page['page'] = page

                # Fetch list page
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

                if not response:
                    raise Exception(f"Failed to fetch page {page}")

                # Parse JSON
                json_data = response.json()

                # Get metadata on first page
                if page == 0:
                    total_items = int(json_data.get('itemCount', 0))
                    total_pages = int(json_data.get('pageCount', 0))

                    logging.info(f"  Papers in {year}: {total_items:,}")
                    logging.info(f"  Pages: {total_pages:,}")

                    if limit:
                        logging.info(f"  LIMIT ACTIVE: Will stop after {limit} papers")

                    if total_items == 0:
                        logging.info(f"  No papers in {year}")
                        return []

                # Parse results HTML
                results_html = json_data.get('results', '')
                if not results_html or not results_html.strip():
                    break

                soup = BeautifulSoup(results_html, 'html.parser')
                entries = soup.find_all('div', class_='list-entry')

                if not entries:
                    break

                logging.info(f"\n  Page {page+1}/{total_pages}: Processing {len(entries)} papers...")

                # Parse each entry
                for entry in entries:
                    # Extract literature ID from the info icon
                    img = entry.find('img', class_='lit-img-info')
                    lit_id = None
                    if img and img.get('data-ajax'):
                        ajax_url = img['data-ajax']
                        lit_id = ajax_url.split('/')[-1]

                    # Extract PDF download link from green download arrow
                    pdf_url = None
                    list_images = entry.find('div', class_='list-images')
                    if list_images:
                        download_link = list_images.find('a', href=True)
                        if download_link:
                            # Check if this link contains the download.png image
                            download_img = download_link.find('img', src='/images/download.png')
                            if download_img:
                                pdf_url = download_link.get('href', '')

                    # Extract basic info from list
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

                    # Extract title (everything before the journal)
                    title = ''
                    if list_text_div:
                        # Get text between authors and findspot
                        text_parts = []
                        for content in list_text_div.contents:
                            if isinstance(content, str):
                                text = content.strip()
                                if text and text not in ['DOI:']:
                                    text_parts.append(text)
                            elif content.name == 'span' and 'lit-findspot' in content.get('class', []):
                                break
                            elif content.name == 'br':
                                continue
                        title = ' '.join(text_parts).strip()

                    doi_link = entry.find('a', href=lambda x: x and 'doi.org' in x)
                    doi = doi_link.get_text(strip=True) if doi_link else ''

                    findspot_span = entry.find('span', class_='lit-findspot')
                    findspot = findspot_span.get_text(strip=True) if findspot_span else ''

                    paper = {
                        'year': year,
                        'literature_id': lit_id,
                        'authors': authors,
                        'title': title,
                        'citation': citation,
                        'findspot': findspot,
                        'doi': doi,
                        'pdf_url': pdf_url if pdf_url else '',
                    }

                    # Fetch detailed information
                    if lit_id:
                        pdf_indicator = "📄 PDF" if pdf_url else ""
                        logging.info(f"    [{papers_processed+1}] Fetching details for ID {lit_id}... {pdf_indicator}")
                        details = self.fetch_paper_details(lit_id)
                        paper.update(details)
                        time.sleep(self.detail_delay)
                    else:
                        logging.warning(f"    [{papers_processed+1}] No literature ID found")

                    all_papers.append(paper)
                    papers_processed += 1

                    # Check limit
                    if limit and papers_processed >= limit:
                        logging.info(f"\n  ✓ Reached limit of {limit} papers")
                        return all_papers

                # Progress
                logging.info(f"  Page {page+1}/{total_pages} complete - Total: {len(all_papers):,}/{total_items:,}")

                # Check if done
                page += 1
                if total_pages and page >= total_pages:
                    break

                # Polite delay between pages
                time.sleep(self.delay)

            logging.info(f"\n  ✓ Year {year} complete: {len(all_papers):,} papers with full details\n")
            return all_papers

        except Exception as e:
            logging.error(f"  ❌ Error downloading {year}: {e}")
            logging.info(f"  Partial results: {len(all_papers):,} papers")
            return all_papers

    def save_to_csv(self, papers, filepath=None):
        """Save papers to CSV"""
        if not filepath:
            filepath = OUTPUT_DIR / f"shark_references_complete_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

        df = pd.DataFrame(papers)

        # Sort by year (newest first) then by authors
        if 'year' in df.columns:
            df = df.sort_values(['year', 'authors'], ascending=[False, True])

        df.to_csv(filepath, index=False, encoding='utf-8')

        size_mb = filepath.stat().st_size / (1024 * 1024)
        logging.info(f"✓ Saved {len(papers):,} papers to {filepath.name} ({size_mb:.2f} MB)")

        return filepath


def main():
    parser = argparse.ArgumentParser(
        description='Complete download with all fields including abstracts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 5 papers from 2025
  python3 shark_references_complete_download.py --year 2025 --limit 5

  # Download complete year with all details
  python3 shark_references_complete_download.py --year 2025

  # Download all years (takes ~40 hours!)
  python3 shark_references_complete_download.py --year-start 2025 --year-end 1950
        """
    )

    parser.add_argument('--year', type=int,
                       help='Download single year')
    parser.add_argument('--year-start', type=int, default=2025,
                       help='Start year (newest)')
    parser.add_argument('--year-end', type=int, default=2025,
                       help='End year (oldest)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of papers (for testing)')
    parser.add_argument('--delay', type=float, default=4.0,
                       help='Delay between list requests (default: 4s)')
    parser.add_argument('--detail-delay', type=float, default=2.0,
                       help='Delay between detail requests (default: 2s)')
    parser.add_argument('--query', type=str, default='',
                       help='Search query (default: empty = all papers)')

    args = parser.parse_args()

    downloader = CompleteDownloader(delay=args.delay, detail_delay=args.detail_delay)

    if args.year:
        # Single year
        logging.info(f"Downloading {args.year} with complete details")
        if args.limit:
            logging.info(f"LIMIT: {args.limit} papers")

        papers = downloader.download_year_complete(
            args.year,
            query=args.query,
            limit=args.limit
        )

        if papers:
            downloader.save_to_csv(papers)
    else:
        # Multiple years - save incrementally!
        logging.info(f"\nMultiple years: {args.year_start} → {args.year_end}")
        logging.info(f"Strategy: Save each year separately + create master CSV\n")

        # Create year-specific subdirectory
        year_dir = OUTPUT_DIR / "by_year"
        year_dir.mkdir(exist_ok=True)

        all_papers = []
        years_completed = []

        for year in range(args.year_start, args.year_end - 1, -1):
            papers = downloader.download_year_complete(
                year,
                query=args.query,
                limit=args.limit
            )

            if papers:
                # Save this year immediately (checkpoint)
                year_file = year_dir / f"year_{year}.csv"
                df_year = pd.DataFrame(papers)
                df_year.to_csv(year_file, index=False, encoding='utf-8')
                logging.info(f"  💾 Saved year {year} to {year_file.name}\n")

                all_papers.extend(papers)
                years_completed.append(year)

                # Also save cumulative master CSV after each year (safe checkpoint)
                master_file = OUTPUT_DIR / f"master_cumulative_{args.year_start}_to_{year}.csv"
                df_master = pd.DataFrame(all_papers)
                df_master = df_master.sort_values(['year', 'authors'], ascending=[False, True])
                df_master.to_csv(master_file, index=False, encoding='utf-8')
                size_mb = master_file.stat().st_size / (1024 * 1024)
                logging.info(f"  ✓ Master CSV updated: {len(all_papers):,} papers ({size_mb:.1f} MB)")
                logging.info(f"    Years completed: {years_completed[0]} → {years_completed[-1]}\n")

            time.sleep(2)

        # Final master CSV
        if all_papers:
            final_file = OUTPUT_DIR / f"shark_references_complete_{args.year_start}_to_{args.year_end}_{datetime.now().strftime('%Y%m%d')}.csv"
            df_final = pd.DataFrame(all_papers)
            df_final = df_final.sort_values(['year', 'authors'], ascending=[False, True])
            df_final.to_csv(final_file, index=False, encoding='utf-8')
            size_mb = final_file.stat().st_size / (1024 * 1024)

            logging.info(f"\n{'='*80}")
            logging.info(f"✅ DOWNLOAD COMPLETE")
            logging.info(f"{'='*80}")
            logging.info(f"Final CSV: {final_file.name}")
            logging.info(f"Total papers: {len(all_papers):,}")
            logging.info(f"Total years: {len(years_completed)}")
            logging.info(f"Size: {size_mb:.1f} MB")
            logging.info(f"{'='*80}\n")

    return 0


if __name__ == "__main__":
    exit(main())
