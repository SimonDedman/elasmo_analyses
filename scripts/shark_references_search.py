#!/usr/bin/env python3
"""
Shark-References Automated Literature Search
EEA 2025 Data Panel Project

This script automates literature searches on shark-references.com
reading techniques from the Excel database and saving results as CSVs.

Usage:
    python shark_references_search.py --test
    python shark_references_search.py --discipline MOV
    python shark_references_search.py --all
    python shark_references_search.py --resume
    python shark_references_search.py --limit 5

Author: Simon Dedman
Date: 2025-10-17 (Updated)
"""

import requests
import pandas as pd
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
import re
import openpyxl
from bs4 import BeautifulSoup
import csv
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shark_references_search.log'),
        logging.StreamHandler()
    ]
)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TECHNIQUES_DB = PROJECT_ROOT / "data" / "Techniques DB for Panel Review.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "shark_references_raw"
PROGRESS_FILE = OUTPUT_DIR / "search_progress.csv"


class SharkReferencesSearcher:
    """Handler for Shark-References database searches"""

    def __init__(self, delay=3, output_dir=OUTPUT_DIR, max_pages=None):
        """
        Initialize searcher

        Args:
            delay: Seconds between requests (default 3 for polite crawling)
            output_dir: Directory for CSV outputs
            max_pages: Maximum pages to fetch per search (None = unlimited, for testing use 50)
        """
        self.base_url = "https://shark-references.com/index.php/search/search"
        self.delay = delay
        self.max_pages = max_pages
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://shark-references.com/search'
        })

    def search(self, query_fulltext, year_from=None, year_to=None):
        """
        Execute search on Shark-References AJAX API and parse JSON results to CSV
        Handles pagination to get ALL results

        Args:
            query_fulltext: Search term with operators
            year_from: Start year (optional)
            year_to: End year (optional)

        Returns:
            CSV data as string or None if failed
        """
        data = {
            "query_fulltext": query_fulltext
        }

        if year_from:
            data["year_from"] = str(year_from)
        if year_to:
            data["year_to"] = str(year_to)

        logging.info(f"Searching: {query_fulltext}")

        all_results = []
        page = 0
        total_pages = None
        total_items = None
        max_retries = 3
        base_timeout = 60

        try:
            # Loop through all pages
            while True:
                # Add page parameter
                data_with_page = data.copy()
                data_with_page['page'] = page

                logging.info(f"  Fetching page {page + 1}...")

                # Try with increasing timeouts on retry
                response = None
                last_error = None

                for attempt in range(max_retries):
                    timeout = base_timeout * (attempt + 1)  # 60s, 120s, 180s
                    try:
                        if attempt > 0:
                            logging.info(f"    Retry {attempt + 1}/{max_retries} with {timeout}s timeout...")
                        response = self.session.post(self.base_url, data=data_with_page, timeout=timeout)
                        response.raise_for_status()
                        break  # Success!
                    except requests.exceptions.Timeout as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            logging.warning(f"    Timeout after {timeout}s, retrying...")
                            time.sleep(2)  # Brief pause before retry
                        else:
                            logging.error(f"    Failed after {max_retries} attempts")
                            raise
                    except requests.exceptions.RequestException as e:
                        # For non-timeout errors, don't retry
                        raise

                if response is None:
                    raise last_error

                # Parse JSON response
                try:
                    json_data = response.json()
                except ValueError:
                    logging.error(f"Response is not valid JSON on page {page}")
                    break

                # Extract metadata from first page
                if page == 0:
                    total_items = int(json_data.get('itemCount', 0))
                    total_pages = int(json_data.get('pageCount', 0))

                    logging.info(f"Found {total_items} total results ({total_pages} pages)")

                    if total_items == 0:
                        logging.info("No publications found for this search")
                        return None

                results_html = json_data.get('results', '')

                if not results_html or results_html.strip() == '':
                    # No more results
                    logging.info(f"  No more results on page {page + 1}")
                    break

                # Parse the HTML results
                soup = BeautifulSoup(results_html, 'html.parser')

                # Find individual literature entries
                result_entries = soup.find_all('div', class_='list-entry')

                if not result_entries:
                    logging.warning(f"  No entries found on page {page + 1}")
                    break

                logging.info(f"  Extracted {len(result_entries)} entries from page {page + 1}")

                # Parse each entry to extract bibliographic data
                for entry in result_entries:
                    # Extract full text first for filtering
                    full_text = entry.get_text(separator=' ', strip=True)
                    full_text_lower = full_text.lower()

                    # Filter: Check if ALL search terms are present in the text
                    # Parse search query to extract required terms (those with +)
                    required_terms = []
                    for term in query_fulltext.split():
                        if term.startswith('+'):
                            # Remove + and * wildcards
                            clean_term = term[1:].replace('*', '')
                            if clean_term:
                                required_terms.append(clean_term.lower())

                    # Check if all required terms are present
                    if required_terms:
                        if not all(term in full_text_lower for term in required_terms):
                            # Skip this result - doesn't contain all required terms
                            continue

                    # Extract authors
                    authors_span = entry.find('span', class_='lit-authors')
                    authors = authors_span.get_text(strip=True) if authors_span else ''

                    # Extract full citation text (excluding authors span)
                    list_text_div = entry.find('div', class_='list-text')
                    if list_text_div:
                        # Clone to avoid modifying original
                        list_text_clone = BeautifulSoup(str(list_text_div), 'html.parser')
                        authors_in_clone = list_text_clone.find('span', class_='lit-authors')
                        if authors_in_clone:
                            authors_in_clone.extract()
                        citation = list_text_clone.get_text(separator=' ', strip=True)
                    else:
                        citation = ''

                    # Extract DOI if present
                    doi_link = entry.find('a', href=re.compile(r'doi\.org'))
                    doi = doi_link.get_text(strip=True) if doi_link else ''

                    # Extract findspot (journal/publication info)
                    findspot_span = entry.find('span', class_='lit-findspot')
                    findspot = findspot_span.get_text(strip=True) if findspot_span else ''

                    all_results.append({
                        'authors': authors,
                        'citation': citation,
                        'findspot': findspot,
                        'doi': doi,
                        'full_text': full_text
                    })

                # Check if we've reached the last page
                page += 1
                if total_pages and page >= total_pages:
                    logging.info(f"  Reached last page ({total_pages})")
                    break

                # Check if we've hit max_pages limit (for testing)
                if self.max_pages and page >= self.max_pages:
                    logging.warning(f"  Reached max_pages limit ({self.max_pages}). Stopping pagination.")
                    break

                # Polite delay between page requests
                time.sleep(self.delay)

            if not all_results:
                logging.warning("No results parsed from any page")
                return None

            # Convert to CSV format
            csv_output = io.StringIO()
            fieldnames = ['authors', 'citation', 'findspot', 'doi', 'full_text']
            writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)

            csv_data = csv_output.getvalue()
            logging.info(f"✓ Successfully extracted {len(all_results)} references from {page} page(s)")
            return csv_data

        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed on page {page}: {e}")
            # If we have some results, return them
            if all_results:
                logging.info(f"Returning {len(all_results)} results collected before error")
                csv_output = io.StringIO()
                fieldnames = ['authors', 'citation', 'findspot', 'doi', 'full_text']
                writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_results)
                return csv_output.getvalue()
            return None
        except Exception as e:
            logging.error(f"Error parsing results on page {page}: {e}")
            import traceback
            traceback.print_exc()
            # If we have some results, return them
            if all_results:
                logging.info(f"Returning {len(all_results)} results collected before error")
                csv_output = io.StringIO()
                fieldnames = ['authors', 'citation', 'findspot', 'doi', 'full_text']
                writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_results)
                return csv_output.getvalue()
            return None

    def save_csv(self, csv_data, discipline_code, technique_name, search_query, category_name=''):
        """
        Save CSV data to file with structured naming

        Args:
            csv_data: CSV content as string
            discipline_code: Discipline code (e.g., MOV)
            technique_name: Technique name
            search_query: Search query used
            category_name: Category name (optional)

        Returns:
            Path to saved file
        """
        # Clean names for filename
        clean_technique = re.sub(r'[^\w\s-]', '', technique_name)
        clean_technique = re.sub(r'[-\s]+', '_', clean_technique).lower()

        # Create filename following schema: discipline_code-category_name-technique_name_date.csv
        timestamp = datetime.now().strftime("%Y%m%d")

        if category_name:
            clean_category = re.sub(r'[^\w\s-]', '', category_name)
            clean_category = re.sub(r'[-\s]+', '_', clean_category).lower()
            filename = f"{discipline_code}-{clean_category}-{clean_technique}_{timestamp}.csv"
        else:
            filename = f"{discipline_code}-{clean_technique}_{timestamp}.csv"

        filepath = self.output_dir / filename

        # Save CSV
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(csv_data)

        # Check if we got actual CSV data
        line_count = csv_data.count('\n')
        logging.info(f"Saved to: {filepath} ({line_count} lines)")

        return filepath


def load_techniques_database(excel_path=TECHNIQUES_DB, sheet_name='Full_List'):
    """
    Load techniques from Excel database

    Args:
        excel_path: Path to Excel file
        sheet_name: Sheet name to read

    Returns:
        pandas.DataFrame with technique information
    """
    logging.info(f"Loading techniques from: {excel_path}")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        logging.info(f"Loaded {len(df)} techniques from {sheet_name}")

        # Validate required columns
        required_cols = ['discipline_code', 'technique_name', 'search_query']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Filter out rows without search queries
        df_valid = df[df['search_query'].notna() & (df['search_query'] != '')].copy()
        logging.info(f"Found {len(df_valid)} techniques with search queries")

        return df_valid

    except Exception as e:
        logging.error(f"Failed to load techniques database: {e}")
        raise


def load_progress():
    """
    Load search progress from file

    Returns:
        Set of completed technique IDs (discipline_code + technique_name)
    """
    if not PROGRESS_FILE.exists():
        logging.info("No progress file found - starting fresh")
        return set()

    try:
        progress_df = pd.read_csv(PROGRESS_FILE)
        completed = set(
            progress_df['discipline_code'] + '::' + progress_df['technique_name']
        )
        logging.info(f"Loaded progress: {len(completed)} searches already completed")
        return completed
    except Exception as e:
        logging.warning(f"Could not load progress file: {e}")
        return set()


def save_progress(discipline_code, technique_name, search_query, status, result_count, error_msg=None):
    """
    Append search result to progress file

    Args:
        discipline_code: Discipline code
        technique_name: Technique name
        search_query: Search query used
        status: 'success' or 'error'
        result_count: Number of results (lines in CSV)
        error_msg: Error message if failed
    """
    progress_entry = {
        'timestamp': datetime.now().isoformat(),
        'discipline_code': discipline_code,
        'technique_name': technique_name,
        'search_query': search_query,
        'status': status,
        'result_count': result_count,
        'error_message': error_msg
    }

    # Create DataFrame
    df = pd.DataFrame([progress_entry])

    # Append to file
    if PROGRESS_FILE.exists():
        df.to_csv(PROGRESS_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(PROGRESS_FILE, mode='w', header=True, index=False)


def run_searches(techniques_df, searcher, resume=False, limit=None, discipline_filter=None):
    """
    Execute searches for all techniques

    Args:
        techniques_df: DataFrame with techniques to search
        searcher: SharkReferencesSearcher instance
        resume: If True, skip already completed searches
        limit: Maximum number of searches to perform (for testing)
        discipline_filter: Only search this discipline code (e.g., 'MOV')
    """
    # Load progress if resuming
    completed = load_progress() if resume else set()

    # Filter by discipline if specified
    if discipline_filter:
        techniques_df = techniques_df[
            techniques_df['discipline_code'] == discipline_filter
        ].copy()
        logging.info(f"Filtered to {len(techniques_df)} techniques in discipline {discipline_filter}")

    # Track statistics
    stats = {
        'total': len(techniques_df),
        'attempted': 0,
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'empty_results': 0
    }

    logging.info(f"\n{'='*70}")
    logging.info(f"Starting search execution")
    logging.info(f"Total techniques to process: {stats['total']}")
    if limit:
        logging.info(f"LIMIT ACTIVE: Will stop after {limit} searches")
    if resume:
        logging.info(f"RESUME MODE: {len(completed)} already completed")
    logging.info(f"{'='*70}\n")

    for idx, row in techniques_df.iterrows():
        disc_code = row['discipline_code']
        tech_name = row['technique_name']
        search_query = row['search_query']
        category_name = row.get('category_name', '')

        # Check if already completed
        tech_id = f"{disc_code}::{tech_name}"
        if tech_id in completed:
            stats['skipped'] += 1
            logging.info(f"[{stats['attempted']}/{stats['total']}] SKIP: {disc_code} - {tech_name} (already completed)")
            continue

        # Check limit
        if limit and stats['attempted'] >= limit:
            logging.info(f"\nReached limit of {limit} searches - stopping")
            break

        stats['attempted'] += 1

        logging.info(f"\n[{stats['attempted']}/{stats['total']}] {disc_code} - {tech_name}")
        logging.info(f"Query: {search_query}")

        try:
            # Execute search
            csv_data = searcher.search(search_query)

            if csv_data is None:
                stats['failed'] += 1
                save_progress(disc_code, tech_name, search_query, 'error', 0,
                            'Request returned None')
                logging.error("❌ Search failed - no response")
                continue

            # Count results (approximate - count newlines)
            result_count = csv_data.count('\n')

            if result_count < 2:  # Just header or empty
                stats['empty_results'] += 1
                save_progress(disc_code, tech_name, search_query, 'success', 0,
                            'No results found')
                logging.warning(f"⚠️  No results found ({result_count} lines)")
                continue

            # Save CSV
            filepath = searcher.save_csv(csv_data, disc_code, tech_name, search_query, category_name)

            stats['successful'] += 1
            save_progress(disc_code, tech_name, search_query, 'success', result_count)
            logging.info(f"✓ Success: {result_count} results saved to {filepath.name}")

        except Exception as e:
            stats['failed'] += 1
            error_msg = str(e)
            save_progress(disc_code, tech_name, search_query, 'error', 0, error_msg)
            logging.error(f"❌ Error: {error_msg}")

    # Final statistics
    logging.info(f"\n{'='*70}")
    logging.info(f"SEARCH EXECUTION COMPLETE")
    logging.info(f"{'='*70}")
    logging.info(f"Total techniques:     {stats['total']}")
    logging.info(f"Attempted searches:   {stats['attempted']}")
    logging.info(f"Successful:           {stats['successful']}")
    logging.info(f"Empty results:        {stats['empty_results']}")
    logging.info(f"Failed:               {stats['failed']}")
    logging.info(f"Skipped (resume):     {stats['skipped']}")
    logging.info(f"{'='*70}\n")

    # Show saved files
    csv_files = list(OUTPUT_DIR.glob("*.csv"))
    csv_files = [f for f in csv_files if f.name != 'search_progress.csv']
    logging.info(f"Output directory contains {len(csv_files)} CSV result files")
    logging.info(f"Progress tracked in: {PROGRESS_FILE}")


def test_search():
    """Test search with a single technique"""
    logging.info("Running test search...")

    searcher = SharkReferencesSearcher(delay=2)

    # Test query
    test_query = "+acoustic +telemetry"
    logging.info(f"Test query: {test_query}")

    csv_data = searcher.search(test_query)

    if csv_data:
        # Save test result
        test_file = OUTPUT_DIR / f"TEST_acoustic_telemetry_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(csv_data)

        line_count = csv_data.count('\n')
        logging.info(f"✓ Test successful: {line_count} lines saved to {test_file}")
        logging.info(f"\nFirst 500 characters of response:")
        logging.info(csv_data[:500])

        return True
    else:
        logging.error("❌ Test failed - no response")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Automated Shark-References literature search from Excel database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with single search
  python shark_references_search.py --test

  # Search first 5 techniques (testing)
  python shark_references_search.py --limit 5

  # Search specific discipline
  python shark_references_search.py --discipline MOV

  # Search all techniques
  python shark_references_search.py --all

  # Resume interrupted search
  python shark_references_search.py --resume --all
        """
    )
    parser.add_argument('--test', action='store_true',
                       help='Run single test search to verify functionality')
    parser.add_argument('--discipline', type=str,
                       help='Search specific discipline code (e.g., MOV, BIO, GEN)')
    parser.add_argument('--all', action='store_true',
                       help='Search all techniques in database')
    parser.add_argument('--resume', action='store_true',
                       help='Resume previous search (skip completed)')
    parser.add_argument('--limit', type=int,
                       help='Maximum number of searches (for testing)')
    parser.add_argument('--delay', type=int, default=3,
                       help='Delay between requests in seconds (default: 3)')
    parser.add_argument('--excel', type=str, default=str(TECHNIQUES_DB),
                       help='Path to Excel database file')

    args = parser.parse_args()

    # Validate Excel file exists
    excel_path = Path(args.excel)
    if not args.test and not excel_path.exists():
        logging.error(f"Excel file not found: {excel_path}")
        logging.error(f"Expected location: {TECHNIQUES_DB}")
        return 1

    # Execute based on arguments
    if args.test:
        success = test_search()
        return 0 if success else 1

    elif args.all or args.discipline or args.limit:
        # Load techniques
        techniques_df = load_techniques_database(excel_path)

        # Create searcher
        searcher = SharkReferencesSearcher(delay=args.delay)

        # Run searches
        run_searches(
            techniques_df,
            searcher,
            resume=args.resume,
            limit=args.limit,
            discipline_filter=args.discipline
        )

        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit(main())
