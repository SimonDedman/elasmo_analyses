#!/usr/bin/env python3
"""
Shark-References Bulk Download - Year-by-Year Strategy (Newest First)

Downloads entire database year-by-year, starting with 2025 (most recent).
Benefits:
1. Most relevant papers first
2. Natural checkpointing by year
3. Easy to update (just download recent years)
4. If interrupted, still have the most important data

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shark_references_bulk_year.log'),
        logging.StreamHandler()
    ]
)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "shark_references_bulk"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

CHECKPOINT_FILE = OUTPUT_DIR / "year_progress.json"


class YearByYearDownloader:
    """Downloads shark-references database year-by-year, newest first"""

    def __init__(self, delay=4):
        self.base_url = "https://shark-references.com/index.php/search/search"
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://shark-references.com/search'
        })

    def download_year(self, year, query=""):
        """
        Download all papers from a specific year

        Args:
            year: Year to download
            query: Search query (empty for all papers)

        Returns:
            List of paper dictionaries
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

                # Request with retries
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
                           f"Total: {len(all_papers):,}/{total_items:,} "
                           f"({100*len(all_papers)/total_items if total_items else 0:.1f}%)")

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
            logging.info(f"  Partial results: {len(all_papers):,} papers")
            return all_papers

    def download_all_years(self, query="", year_start=2025, year_end=1950, resume_year=None):
        """
        Download all papers year-by-year, newest first

        Args:
            query: Search query (empty for all)
            year_start: Start year (newest, default 2025)
            year_end: End year (oldest, default 1950)
            resume_year: Year to resume from if interrupted

        Returns:
            List of all papers
        """
        logging.info(f"\n{'='*80}")
        logging.info(f"BULK DOWNLOAD - YEAR BY YEAR STRATEGY")
        logging.info(f"={'='*80}")
        logging.info(f"Years: {year_start} → {year_end} (newest first)")
        logging.info(f"Total years: {year_start - year_end + 1}")
        if resume_year:
            logging.info(f"Resuming from: {resume_year}")
        logging.info(f"{'='*80}\n")

        # Load checkpoint if resuming
        start_year = year_start if not resume_year else resume_year
        all_papers = []
        years_completed = []

        try:
            # Download year by year, newest first
            for year in range(start_year, year_end - 1, -1):
                years_done = len(years_completed)
                years_total = start_year - year_end + 1

                logging.info(f"📊 Progress: {years_done}/{years_total} years ({100*years_done/years_total:.1f}%)")

                # Download this year
                year_papers = self.download_year(year, query)

                if year_papers:
                    all_papers.extend(year_papers)
                    years_completed.append(year)

                    # Save checkpoint
                    self.save_checkpoint(year, years_completed, len(all_papers))

                # Pause between years
                time.sleep(2)

            logging.info(f"\n{'='*80}")
            logging.info(f"✅ ALL YEARS DOWNLOADED")
            logging.info(f"{'='*80}")
            logging.info(f"Years completed: {len(years_completed)} ({year_start} → {min(years_completed)})")
            logging.info(f"Total papers: {len(all_papers):,}")
            logging.info(f"Average per year: {len(all_papers)/len(years_completed):.0f}")
            logging.info(f"{'='*80}\n")

            return all_papers

        except KeyboardInterrupt:
            logging.warning(f"\n⚠️  Download interrupted by user")
            logging.info(f"Years completed: {years_completed}")
            logging.info(f"Papers collected: {len(all_papers):,}")
            if years_completed:
                next_year = years_completed[-1] - 1
                logging.info(f"\nResume with: --resume-year {next_year}")
            return all_papers

        except Exception as e:
            logging.error(f"\n❌ Error: {e}")
            logging.info(f"Years completed: {years_completed}")
            logging.info(f"Papers collected: {len(all_papers):,}")
            if years_completed:
                next_year = years_completed[-1] - 1
                logging.info(f"\nResume with: --resume-year {next_year}")
            return all_papers

    def save_checkpoint(self, last_year, years_completed, total_papers):
        """Save progress checkpoint"""
        checkpoint = {
            'last_year_completed': last_year,
            'years_completed': years_completed,
            'total_papers': total_papers,
            'timestamp': datetime.now().isoformat()
        }

        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        logging.info(f"  💾 Checkpoint saved - {total_papers:,} papers from {len(years_completed)} years")

    def load_checkpoint(self):
        """Load checkpoint if exists"""
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    checkpoint = json.load(f)

                last_year = checkpoint['last_year_completed']
                years_done = len(checkpoint['years_completed'])
                papers = checkpoint['total_papers']

                logging.info(f"✓ Checkpoint found:")
                logging.info(f"  Last year completed: {last_year}")
                logging.info(f"  Years completed: {years_done}")
                logging.info(f"  Papers collected: {papers:,}")
                logging.info(f"  To resume from: {last_year - 1}")

                return last_year

            except Exception as e:
                logging.warning(f"Could not load checkpoint: {e}")

        return None

    def save_to_csv(self, papers, filepath=None):
        """Save papers to CSV"""
        if not filepath:
            filepath = OUTPUT_DIR / f"shark_references_complete_{datetime.now().strftime('%Y%m%d')}.csv"

        df = pd.DataFrame(papers)

        # Sort by year (newest first) then by authors
        df = df.sort_values(['year', 'authors'], ascending=[False, True])

        df.to_csv(filepath, index=False, encoding='utf-8')

        size_mb = filepath.stat().st_size / (1024 * 1024)
        logging.info(f"✓ Saved {len(papers):,} papers to {filepath.name} ({size_mb:.1f} MB)")

        return filepath


def filter_for_techniques(bulk_csv, techniques_excel):
    """Filter bulk download for all techniques (local, instant)"""
    logging.info(f"\n{'='*80}")
    logging.info(f"FILTERING FOR TECHNIQUES")
    logging.info(f"{'='*80}\n")

    # Load bulk download
    logging.info(f"Loading: {bulk_csv.name}")
    df_all = pd.read_csv(bulk_csv)
    logging.info(f"  Papers: {len(df_all):,}")

    # Load techniques
    logging.info(f"\nLoading techniques...")
    df_tech = pd.read_excel(techniques_excel, sheet_name='Full_List')
    df_tech = df_tech[df_tech['search_query'].notna() & (df_tech['search_query'] != '')]
    logging.info(f"  Techniques: {len(df_tech)}")

    # Output directory
    output_dir = PROJECT_ROOT / "outputs" / "shark_references_filtered"
    output_dir.mkdir(exist_ok=True, parents=True)

    stats = {'total': len(df_tech), 'with_results': 0, 'total_papers': 0}

    # Filter for each technique
    for idx, row in df_tech.iterrows():
        disc = row['discipline_code']
        tech = row['technique_name']
        query = row['search_query']
        cat = row.get('category_name', '')

        # Parse required terms
        required = []
        for term in query.split():
            if term.startswith('+'):
                clean = term[1:].replace('*', '').lower()
                if clean:
                    required.append(clean)

        if not required:
            continue

        # Filter papers
        mask = df_all['full_text'].str.lower().str.contains(required[0], na=False)
        for term in required[1:]:
            mask &= df_all['full_text'].str.lower().str.contains(term, na=False)

        df_filtered = df_all[mask]

        if len(df_filtered) == 0:
            logging.info(f"[{idx+1}/{len(df_tech)}] {disc} - {tech}: 0 papers")
            continue

        # Save
        clean_tech = tech.replace(' ', '_').replace('/', '_').lower()
        if cat:
            clean_cat = cat.replace(' ', '_').replace('/', '_').lower()
            filename = f"{disc}-{clean_cat}-{clean_tech}_{datetime.now().strftime('%Y%m%d')}.csv"
        else:
            filename = f"{disc}-{clean_tech}_{datetime.now().strftime('%Y%m%d')}.csv"

        df_filtered.to_csv(output_dir / filename, index=False)

        stats['with_results'] += 1
        stats['total_papers'] += len(df_filtered)

        logging.info(f"[{idx+1}/{len(df_tech)}] {disc} - {tech}: {len(df_filtered)} papers → {filename}")

    # Summary
    logging.info(f"\n{'='*80}")
    logging.info(f"FILTERING COMPLETE")
    logging.info(f"{'='*80}")
    logging.info(f"Techniques: {stats['total']}")
    logging.info(f"With results: {stats['with_results']}")
    logging.info(f"Total papers matched: {stats['total_papers']}")
    logging.info(f"Average per technique: {stats['total_papers']/stats['with_results']:.1f}")
    logging.info(f"Output: {output_dir}")
    logging.info(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Bulk download shark-references year-by-year (newest first)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check for checkpoint
  python3 shark_references_bulk_download_by_year.py --check

  # Download all years (2025 → 1950)
  python3 shark_references_bulk_download_by_year.py --download

  # Resume from checkpoint
  python3 shark_references_bulk_download_by_year.py --download --resume

  # Download + filter
  python3 shark_references_bulk_download_by_year.py --all

  # Update: download only recent years
  python3 shark_references_bulk_download_by_year.py --download --year-start 2025 --year-end 2024
        """
    )

    parser.add_argument('--check', action='store_true',
                       help='Check for checkpoint and show status')
    parser.add_argument('--download', action='store_true',
                       help='Download all years')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint')
    parser.add_argument('--filter', action='store_true',
                       help='Filter bulk download for techniques')
    parser.add_argument('--all', action='store_true',
                       help='Download + filter (complete workflow)')
    parser.add_argument('--year-start', type=int, default=2025,
                       help='Start year (newest, default: 2025)')
    parser.add_argument('--year-end', type=int, default=1950,
                       help='End year (oldest, default: 1950)')
    parser.add_argument('--delay', type=float, default=4.0,
                       help='Delay between requests (default: 4s)')
    parser.add_argument('--query', type=str, default='',
                       help='Search query (default: empty = all papers)')

    args = parser.parse_args()

    downloader = YearByYearDownloader(delay=args.delay)

    if args.check or (not any([args.download, args.filter, args.all])):
        # Check mode
        last_year = downloader.load_checkpoint()
        if last_year:
            print(f"\n✓ You can resume from year {last_year - 1}")
            print(f"  Command: python3 {Path(__file__).name} --download --resume")
        else:
            print("\n✗ No checkpoint found")
            print(f"  Start fresh: python3 {Path(__file__).name} --download")
        return 0

    if args.download or args.all:
        # Download mode
        resume_year = None
        if args.resume:
            last_year = downloader.load_checkpoint()
            if last_year:
                resume_year = last_year - 1
                logging.info(f"Resuming from year {resume_year}")

        # Download
        all_papers = downloader.download_all_years(
            query=args.query,
            year_start=args.year_start,
            year_end=args.year_end,
            resume_year=resume_year
        )

        # Save
        csv_file = downloader.save_to_csv(all_papers)

        # Clean up checkpoint
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()

    if args.filter or args.all:
        # Filter mode
        csv_files = list(OUTPUT_DIR.glob("shark_references_complete_*.csv"))
        if not csv_files:
            logging.error("No bulk download found. Run with --download first")
            return 1

        bulk_csv = max(csv_files, key=lambda p: p.stat().st_mtime)  # Most recent

        techniques_excel = PROJECT_ROOT / "data" / "Techniques DB for Panel Review.xlsx"
        if not techniques_excel.exists():
            logging.error(f"Techniques database not found: {techniques_excel}")
            return 1

        filter_for_techniques(bulk_csv, techniques_excel)

    return 0


if __name__ == "__main__":
    exit(main())
