#!/usr/bin/env python3
"""
Shark-References Automated Literature Search
EEA 2025 Data Panel Project

This script automates literature searches on shark-references.com
and processes results into a structured database.

Usage:
    python shark_references_search.py --test
    python shark_references_search.py --discipline "Movement_Spatial"
    python shark_references_search.py --all

Author: Simon Dedman
Date: 2025-10-02
"""

import requests
import pandas as pd
import sqlite3
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shark_references.log'),
        logging.StreamHandler()
    ]
)

# Search terms by discipline
SEARCH_TERMS = {
    "Biology_Health": [
        "+reproduct* +matur*",
        "+growth +age",
        "+telomere* +aging",
        "+stress +physiol*",
        "+parasit* +disease",
        "+endocrin* +hormone",
        "+metabol* +energetic*"
    ],
    "Behaviour_Sensory": [
        "+behav* +predation",
        "+vision +visual",
        "+electr* +sensory",
        "+olfact* +chemosens*",
        "+magnet* +navigation",
        "+social +aggregation",
        "+learning +cognition"
    ],
    "Trophic_Ecology": [
        "+stable +isotop*",
        "+diet +prey",
        "+trophic +level",
        "+food +web",
        "+stomach +content",
        "+energy +flow",
        "+niche +partition*"
    ],
    "Genetics_Genomics": [
        "+population +geneti*",
        "+genom* +sequenc*",
        "+eDNA +environmental",
        "+phylogeny +molecular",
        "+microsatellite +SNP",
        "+transcriptom* +gene",
        "+conservation +genetic*"
    ],
    "Movement_Spatial": [
        "+telemetry +acoustic",
        "+satellite +tracking",
        "+habitat +model*",
        "+home +range",
        "+SDM +distribution",
        "+spatial +ecology",
        "+migration +movement",
        "+circuit* +connectivity"
    ],
    "Fisheries_Management": [
        "+stock +assessment",
        "+fishery +CPUE",
        "+bycatch +discard*",
        "+mortality +fishing",
        "+catch +per +unit",
        "+surplus +production",
        "+harvest +strategy"
    ],
    "Conservation_Policy": [
        "+conservation +status",
        "+CITES +protection",
        "+MPA +marine +protected",
        "+policy +management",
        "+stakeholder +community",
        "+ecosystem +service*",
        "+human +dimension*"
    ],
    "Data_Science": [
        "+machine +learning",
        "+random +forest",
        "+neural +network",
        "+Bayesian +model*",
        "+AI +artificial",
        "+ensemble +model*",
        "+data +integration",
        "+GAM +generalized"
    ]
}


class SharkReferencesSearcher:
    """Handler for Shark-References database searches"""

    def __init__(self, delay=10, output_dir="./shark_refs_data"):
        """
        Initialize searcher

        Args:
            delay: Seconds between requests (default 10 for conservative approach)
            output_dir: Directory for CSV outputs
        """
        self.base_url = "https://shark-references.com/search"
        self.delay = delay
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()

    def search(self, query_fulltext, year_from=None, year_to=None):
        """
        Execute search on Shark-References

        Args:
            query_fulltext: Search term with operators
            year_from: Start year (optional)
            year_to: End year (optional)

        Returns:
            requests.Response object
        """
        data = {
            "query_fulltext": query_fulltext,
            "clicked_button": "export"
        }

        if year_from:
            data["year_from"] = str(year_from)
        if year_to:
            data["year_to"] = str(year_to)

        logging.info(f"Searching: {query_fulltext}")

        try:
            response = self.session.post(self.base_url, data=data, timeout=30)
            response.raise_for_status()

            # Check if we got CSV or HTML
            content_type = response.headers.get('Content-Type', '')
            logging.debug(f"Response content type: {content_type}")

            return response

        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return None
        finally:
            time.sleep(self.delay)

    def parse_html_results(self, response):
        """
        Parse HTML response to extract reference information

        Args:
            response: requests.Response object with HTML content

        Returns:
            pandas.DataFrame with references
        """
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for reference entries in the HTML
        # This will need adjustment based on actual HTML structure
        references = []

        # Example parsing - adjust based on actual structure
        for item in soup.find_all('div', class_='literature-item'):
            ref = {
                'title': item.find('h3').text if item.find('h3') else None,
                'authors': item.find('span', class_='authors').text if item.find('span', class_='authors') else None,
                'year': item.find('span', class_='year').text if item.find('span', class_='year') else None,
                'journal': item.find('span', class_='journal').text if item.find('span', class_='journal') else None
            }
            references.append(ref)

        if not references:
            logging.warning("No references found in HTML response")
            return pd.DataFrame()

        return pd.DataFrame(references)

    def save_response(self, response, filename):
        """
        Save raw response to file for later parsing

        Args:
            response: requests.Response object
            filename: Output filename
        """
        filepath = self.output_dir / filename

        # Determine if CSV or HTML
        content_type = response.headers.get('Content-Type', '')

        if 'csv' in content_type.lower() or 'text/csv' in content_type:
            filepath = filepath.with_suffix('.csv')
        else:
            filepath = filepath.with_suffix('.html')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response.text)

        logging.info(f"Saved to: {filepath}")
        return filepath


class SharkReferencesDatabase:
    """Handler for SQLite database operations"""

    def __init__(self, db_path="shark_literature.db"):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Create database connection and initialize schema"""
        self.conn = sqlite3.connect(self.db_path)
        self._create_schema()

    def _create_schema(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()

        # Main references table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shark_references (
                ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_term VARCHAR(255),
                discipline VARCHAR(100),
                method_category VARCHAR(100),
                authors TEXT,
                year INTEGER,
                title TEXT,
                journal VARCHAR(255),
                volume VARCHAR(50),
                issue VARCHAR(50),
                pages VARCHAR(50),
                doi VARCHAR(100),
                abstract TEXT,
                keywords TEXT,
                date_retrieved DATE,
                shark_ref_id VARCHAR(100),
                citation_count INTEGER,
                scholar_url TEXT,
                UNIQUE(doi, title)
            )
        """)

        # Search log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_term VARCHAR(255),
                discipline VARCHAR(100),
                result_count INTEGER,
                timestamp DATETIME,
                status VARCHAR(50),
                error_message TEXT
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_discipline
            ON shark_references(discipline)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_year
            ON shark_references(year)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_method
            ON shark_references(method_category)
        """)

        self.conn.commit()
        logging.info(f"Database initialized: {self.db_path}")

    def import_references(self, df, discipline, search_term):
        """
        Import references DataFrame to database

        Args:
            df: pandas.DataFrame with reference data
            discipline: Discipline category
            search_term: Search term used
        """
        if df.empty:
            logging.warning("Empty DataFrame, nothing to import")
            return

        # Add metadata
        df['discipline'] = discipline
        df['search_term'] = search_term
        df['date_retrieved'] = datetime.now().date()

        # Insert into database
        try:
            df.to_sql('shark_references', self.conn,
                     if_exists='append', index=False)
            logging.info(f"Imported {len(df)} references for {discipline}")
        except sqlite3.IntegrityError as e:
            logging.warning(f"Some duplicates skipped: {e}")

    def log_search(self, search_term, discipline, result_count,
                   status='success', error_message=None):
        """
        Log search to database

        Args:
            search_term: Search query used
            discipline: Discipline category
            result_count: Number of results found
            status: 'success' or 'error'
            error_message: Error description if failed
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO search_log
            (search_term, discipline, result_count, timestamp, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (search_term, discipline, result_count,
              datetime.now(), status, error_message))
        self.conn.commit()

    def deduplicate(self):
        """Remove duplicate entries based on DOI/title"""
        cursor = self.conn.cursor()

        cursor.execute("""
            DELETE FROM shark_references
            WHERE ref_id NOT IN (
                SELECT MIN(ref_id)
                FROM shark_references
                GROUP BY COALESCE(doi, ''), COALESCE(title, '')
            )
        """)

        self.conn.commit()
        deleted = cursor.rowcount
        logging.info(f"Removed {deleted} duplicate entries")

    def get_statistics(self):
        """Get summary statistics from database"""
        stats = {}

        # Total references
        stats['total_refs'] = pd.read_sql(
            "SELECT COUNT(*) as count FROM shark_references",
            self.conn
        )['count'][0]

        # By discipline
        stats['by_discipline'] = pd.read_sql("""
            SELECT discipline, COUNT(*) as count
            FROM shark_references
            GROUP BY discipline
            ORDER BY count DESC
        """, self.conn)

        # By year
        stats['by_year'] = pd.read_sql("""
            SELECT year, COUNT(*) as count
            FROM shark_references
            WHERE year IS NOT NULL
            GROUP BY year
            ORDER BY year DESC
            LIMIT 20
        """, self.conn)

        # Search log summary
        stats['search_log'] = pd.read_sql("""
            SELECT discipline, COUNT(*) as searches,
                   SUM(result_count) as total_results,
                   AVG(result_count) as avg_results
            FROM search_log
            WHERE status = 'success'
            GROUP BY discipline
        """, self.conn)

        return stats

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def run_batch_search(disciplines=None, searcher=None, database=None):
    """
    Execute batch searches across disciplines

    Args:
        disciplines: List of discipline names (None = all)
        searcher: SharkReferencesSearcher instance
        database: SharkReferencesDatabase instance
    """
    if searcher is None:
        searcher = SharkReferencesSearcher()
    if database is None:
        database = SharkReferencesDatabase()
        database.connect()

    # Select disciplines
    if disciplines is None:
        disciplines = list(SEARCH_TERMS.keys())
    elif isinstance(disciplines, str):
        disciplines = [disciplines]

    logging.info(f"Starting batch search for {len(disciplines)} disciplines")

    for discipline in disciplines:
        if discipline not in SEARCH_TERMS:
            logging.error(f"Unknown discipline: {discipline}")
            continue

        logging.info(f"\n{'='*60}")
        logging.info(f"Discipline: {discipline}")
        logging.info(f"{'='*60}")

        terms = SEARCH_TERMS[discipline]

        for i, term in enumerate(terms, 1):
            logging.info(f"\n[{i}/{len(terms)}] Search term: {term}")

            try:
                # Execute search
                response = searcher.search(term)

                if response is None:
                    database.log_search(term, discipline, 0,
                                      'error', 'Request failed')
                    continue

                # Save raw response
                filename = f"{discipline}_{i:02d}"
                filepath = searcher.save_response(response, filename)

                # Try to parse (implementation depends on response format)
                # For now, just log success
                database.log_search(term, discipline, 0, 'success')

                logging.info(f"Completed: {term}")

            except Exception as e:
                logging.error(f"Error processing {term}: {e}")
                database.log_search(term, discipline, 0,
                                  'error', str(e))

    logging.info("\nBatch search completed")

    # Show statistics
    stats = database.get_statistics()
    logging.info(f"\nTotal references: {stats['total_refs']}")
    logging.info("\nBy discipline:")
    logging.info(stats['by_discipline'].to_string())


def test_single_search():
    """Test single search to verify functionality"""
    logging.info("Running test search...")

    searcher = SharkReferencesSearcher(delay=5)
    database = SharkReferencesDatabase("test_shark_literature.db")
    database.connect()

    # Test with a simple query
    test_term = "+telemetry +acoustic"
    response = searcher.search(test_term)

    if response:
        filename = "test_search"
        filepath = searcher.save_response(response, filename)
        logging.info(f"Test search saved to: {filepath}")
        logging.info("Please inspect this file to understand the response format")

        database.log_search(test_term, "TEST", 0, 'success')
    else:
        logging.error("Test search failed")
        database.log_search(test_term, "TEST", 0, 'error',
                          'Request returned None')

    database.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Automated Shark-References literature search'
    )
    parser.add_argument('--test', action='store_true',
                       help='Run test search only')
    parser.add_argument('--discipline', type=str,
                       help='Search specific discipline')
    parser.add_argument('--all', action='store_true',
                       help='Search all disciplines')
    parser.add_argument('--delay', type=int, default=10,
                       help='Delay between requests (seconds)')
    parser.add_argument('--output-dir', type=str,
                       default='./shark_refs_data',
                       help='Output directory for data')
    parser.add_argument('--database', type=str,
                       default='shark_literature.db',
                       help='Database file path')

    args = parser.parse_args()

    if args.test:
        test_single_search()
    elif args.all:
        searcher = SharkReferencesSearcher(delay=args.delay,
                                          output_dir=args.output_dir)
        database = SharkReferencesDatabase(args.database)
        database.connect()
        run_batch_search(searcher=searcher, database=database)
        database.close()
    elif args.discipline:
        searcher = SharkReferencesSearcher(delay=args.delay,
                                          output_dir=args.output_dir)
        database = SharkReferencesDatabase(args.database)
        database.connect()
        run_batch_search(disciplines=args.discipline,
                        searcher=searcher, database=database)
        database.close()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
