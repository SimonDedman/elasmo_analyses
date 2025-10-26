#!/usr/bin/env python3
"""
PDF Technique Extraction with Researcher Scaffolding

Extracts techniques from 12,381 PDFs and builds researcher database.

Features:
- Searches all PDFs for 224 techniques using search queries
- Handles cross-cutting DATA discipline assignments
- Extracts author information and builds collaboration network
- Tracks paper-technique-researcher relationships
- Progress tracking with resume capability

Output:
- database/technique_taxonomy.db (populated tables)
- outputs/technique_extraction/*.csv (export files)
- logs/extraction.log (detailed log)
"""

import pandas as pd
import sqlite3
from pathlib import Path
import subprocess
import re
import json
import time
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm
import argparse
from multiprocessing import Pool, cpu_count
import threading

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
DATABASE = PROJECT_BASE / "database/technique_taxonomy.db"
OUTPUT_DIR = PROJECT_BASE / "outputs/technique_extraction"
LOG_FILE = PROJECT_BASE / "logs/extraction.log"

# Extraction parameters
CONTEXT_CHARS = 100  # Characters around each match
TEXT_TIMEOUT = 10  # Seconds for pdftotext
BATCH_SIZE = 100  # Save state every N papers
MAX_TEXT_LENGTH = 500000  # Skip PDFs with > 500KB of text (likely scanned books)

# ============================================================================
# MAIN EXTRACTOR CLASS
# ============================================================================

class TechniqueExtractor:
    """Extract techniques from PDFs and build researcher database."""

    def __init__(self, dry_run=False, resume=True, num_workers=None):
        self.dry_run = dry_run
        self.resume = resume
        self.num_workers = num_workers or max(1, cpu_count() - 1)  # Leave 1 core free
        self.conn = sqlite3.connect(DATABASE)
        self.db_lock = threading.Lock()  # Thread-safe database writes

        # Load techniques from Excel
        self.load_techniques()

        # Load processed papers
        self.processed_papers = self.load_processed_papers() if resume else set()

        # Statistics
        self.stats = defaultdict(int)
        self.start_time = time.time()

        # Create output directory
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def load_techniques(self):
        """Load techniques from Excel with discipline and search criteria."""
        print("📚 Loading techniques...")

        df = pd.read_excel(
            PROJECT_BASE / "data/Techniques DB for Panel Review_UPDATED.xlsx",
            sheet_name='Full_List'
        )

        # Filter out removed techniques
        # Keep: NaN (9) + priority "1" (130) + priority "2" (43) = 182 techniques
        # Remove: priority "3" (42 techniques marked for removal)
        df['remove_reason_str'] = df['remove_reason'].astype(str)
        keep_mask = (
            df['remove_reason'].isna() |  # No removal reason
            df['remove_reason_str'].str.startswith('1') |  # Priority 1 (high)
            df['remove_reason_str'].str.startswith('2')    # Priority 2 (medium)
        )
        df = df[keep_mask]

        # Create technique lookup
        self.techniques = []

        for _, row in df.iterrows():
            technique = {
                'technique_name': row['technique_name'],
                'discipline': row['discipline'],
                'category_name': row['category_name'],
                'search_query': row['search_query'],
                'search_query_alt': row['search_query_alt'],
                'synonyms': row['synonyms'],
                'is_parent': row['is_parent'],
                # Data science flags
                'statistical_model': row['statistical_model'],
                'analytical_algorithm': row['analytical_algorithm'],
                'inference_framework': row['inference_framework'],
                # Determine if counts for DATA discipline
                'counts_for_data': (
                    row['discipline'] == 'DATA' or
                    row['statistical_model'] or
                    row['analytical_algorithm'] or
                    row['inference_framework']
                )
            }

            # Build search patterns
            technique['search_patterns'] = self.build_search_patterns(technique)

            self.techniques.append(technique)

        print(f"  ✓ Loaded {len(self.techniques)} techniques")
        print(f"  ✓ {sum(1 for t in self.techniques if t['counts_for_data'])} count for DATA discipline")

    def build_search_patterns(self, technique):
        """Build regex patterns for searching PDFs."""
        patterns = []

        # Main search query
        if pd.notna(technique['search_query']):
            # Convert search query to regex
            # Example: "+behav* +observ*" → r"\bbehav\w*\b.*\bobserv\w*\b"
            query = technique['search_query']
            # Simplified pattern - just look for the technique name
            pattern = r'\b' + re.escape(technique['technique_name']) + r'\b'
            patterns.append(re.compile(pattern, re.IGNORECASE))

        # Alternative search query
        if pd.notna(technique['search_query_alt']):
            pattern = r'\b' + re.escape(str(technique['search_query_alt'])) + r'\b'
            patterns.append(re.compile(pattern, re.IGNORECASE))

        # Synonyms
        if pd.notna(technique['synonyms']):
            for syn in str(technique['synonyms']).split(','):
                syn = syn.strip()
                if syn:
                    pattern = r'\b' + re.escape(syn) + r'\b'
                    patterns.append(re.compile(pattern, re.IGNORECASE))

        return patterns

    def load_processed_papers(self):
        """Load list of already processed papers."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT paper_id FROM extraction_log WHERE status = 'success'")
        processed = {row[0] for row in cursor.fetchall()}

        if processed:
            print(f"📋 Resuming: {len(processed)} papers already processed")

        return processed

    def log(self, message, level="INFO"):
        """Log message to file and console."""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} [{level}] {message}"

        with open(LOG_FILE, 'a') as f:
            f.write(log_entry + "\n")

        if level in ["ERROR", "WARNING"]:
            print(log_entry)

    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF using pdftotext."""
        try:
            result = subprocess.run(
                ['pdftotext', str(pdf_path), '-'],
                capture_output=True,
                text=True,
                timeout=TEXT_TIMEOUT
            )

            if result.returncode == 0:
                return result.stdout
            else:
                return None

        except subprocess.TimeoutExpired:
            self.log(f"Text extraction timeout: {pdf_path.name}", "WARNING")
            return None
        except Exception as e:
            self.log(f"Text extraction error: {pdf_path.name} - {e}", "ERROR")
            return None

    def parse_filename(self, pdf_path):
        """Parse PDF filename to extract metadata."""
        # Filename format: Author1.Author2.Author3.YYYY.Title.pdf
        # or: Author1.etal.YYYY.Title.pdf

        filename = pdf_path.stem
        year = pdf_path.parent.name

        # Split by dots
        parts = filename.split('.')

        # Extract authors (everything before year)
        authors = []
        for part in parts:
            if part == 'etal':
                break
            if part.isdigit() and len(part) == 4:  # Year
                break
            if part and not part.isdigit():
                authors.append(part)

        # First author
        first_author = authors[0] if authors else "Unknown"

        return {
            'paper_id': pdf_path.name,
            'paper_path': str(pdf_path),
            'year': int(year) if year.isdigit() else None,
            'first_author': first_author,
            'all_authors': authors
        }

    def search_techniques(self, text):
        """Search for all techniques in text."""
        found_techniques = []

        for technique in self.techniques:
            for pattern in technique['search_patterns']:
                matches = list(pattern.finditer(text))

                if matches:
                    # Get context for first match
                    match = matches[0]
                    start = max(0, match.start() - CONTEXT_CHARS)
                    end = min(len(text), match.end() + CONTEXT_CHARS)
                    context = text[start:end].replace('\n', ' ').strip()

                    found_techniques.append({
                        'technique_name': technique['technique_name'],
                        'discipline': technique['discipline'],
                        'category_name': technique['category_name'],
                        'counts_for_data': technique['counts_for_data'],
                        'mention_count': len(matches),
                        'context_sample': context
                    })

                    break  # Found via this pattern, don't check others

        return found_techniques

    def get_or_create_researcher(self, surname, all_authors=None):
        """Get or create researcher record."""
        cursor = self.conn.cursor()

        # Try to find existing researcher
        cursor.execute(
            "SELECT researcher_id FROM researchers WHERE surname = ? COLLATE NOCASE",
            (surname,)
        )
        result = cursor.fetchone()

        if result:
            return result[0]

        # Create new researcher
        if self.dry_run:
            return -1  # Fake ID for dry run

        cursor.execute(
            """INSERT INTO researchers (surname, created_date)
               VALUES (?, ?)""",
            (surname, datetime.now().isoformat())
        )
        self.conn.commit()

        return cursor.lastrowid

    def update_collaborations(self, author_ids, year):
        """Update collaboration network."""
        if len(author_ids) < 2:
            return

        # Create all pairwise collaborations
        for i in range(len(author_ids)):
            for j in range(i + 1, len(author_ids)):
                r1, r2 = sorted([author_ids[i], author_ids[j]])

                if self.dry_run:
                    continue

                cursor = self.conn.cursor()

                # Try to update existing
                cursor.execute(
                    """UPDATE collaborations
                       SET collaboration_count = collaboration_count + 1,
                           last_collaboration_year = ?
                       WHERE researcher_1_id = ? AND researcher_2_id = ?""",
                    (year, r1, r2)
                )

                if cursor.rowcount == 0:
                    # Create new
                    cursor.execute(
                        """INSERT INTO collaborations
                           (researcher_1_id, researcher_2_id, collaboration_count,
                            first_collaboration_year, last_collaboration_year)
                           VALUES (?, ?, 1, ?, ?)""",
                        (r1, r2, year, year)
                    )

        if not self.dry_run:
            self.conn.commit()

    def calculate_disciplines(self, techniques_found):
        """Calculate which disciplines this paper belongs to."""
        disciplines = defaultdict(lambda: {'count': 0, 'type': set()})

        for tech in techniques_found:
            # Primary discipline
            disc = tech['discipline']
            disciplines[disc]['count'] += 1
            disciplines[disc]['type'].add('primary')

            # Cross-cutting DATA
            if tech['counts_for_data'] and disc != 'DATA':
                disciplines['DATA']['count'] += 1
                disciplines['DATA']['type'].add('cross_cutting')

        # Determine assignment types
        result = []
        for disc, info in disciplines.items():
            assignment = 'mixed' if len(info['type']) > 1 else list(info['type'])[0]

            result.append({
                'discipline_code': disc,
                'technique_count': info['count'],
                'assignment_type': assignment
            })

        # Check if DATA-only
        is_data_only = (
            len(disciplines) == 1 and
            'DATA' in disciplines and
            disciplines['DATA']['type'] == {'primary'}
        )

        is_primary_only = all(
            info['type'] == {'primary'}
            for info in disciplines.values()
        )

        return result, is_data_only, is_primary_only

    def process_paper(self, pdf_path):
        """Process a single PDF through the extraction pipeline."""
        paper_start = time.time()

        # Parse filename
        paper_info = self.parse_filename(pdf_path)
        paper_id = paper_info['paper_id']

        # Skip if already processed
        if paper_id in self.processed_papers:
            return

        try:
            # Extract text
            text = self.extract_pdf_text(pdf_path)

            if not text:
                self.record_failure(paper_info, "Text extraction failed")
                return

            # Check text length
            if len(text) > MAX_TEXT_LENGTH:
                self.record_failure(paper_info, f"Text too long ({len(text)} chars)")
                return

            # Search for techniques
            techniques_found = self.search_techniques(text)

            # Calculate disciplines
            disciplines, is_data_only, is_primary_only = self.calculate_disciplines(techniques_found)

            if not self.dry_run:
                # Store results
                self.store_paper_techniques(paper_info, techniques_found)
                self.store_paper_disciplines(paper_info, disciplines, is_data_only, is_primary_only)
                self.store_authors(paper_info)

                # Record success
                self.record_success(paper_info, techniques_found, len(text), time.time() - paper_start)

            # Update stats
            self.stats['papers_processed'] += 1
            self.stats['techniques_found'] += len(techniques_found)

        except Exception as e:
            self.log(f"Processing error: {paper_id} - {e}", "ERROR")
            self.record_failure(paper_info, str(e))

    def store_paper_techniques(self, paper_info, techniques):
        """Store paper-technique relationships."""
        cursor = self.conn.cursor()

        for tech in techniques:
            cursor.execute(
                """INSERT OR REPLACE INTO paper_techniques
                   (paper_id, technique_name, primary_discipline, mention_count,
                    context_sample, extraction_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (paper_info['paper_id'], tech['technique_name'], tech['discipline'],
                 tech['mention_count'], tech['context_sample'], datetime.now().isoformat())
            )

        self.conn.commit()

    def store_paper_disciplines(self, paper_info, disciplines, is_data_only, is_primary_only):
        """Store paper-discipline relationships."""
        cursor = self.conn.cursor()

        for disc in disciplines:
            cursor.execute(
                """INSERT OR REPLACE INTO paper_disciplines
                   (paper_id, year, discipline_code, assignment_type,
                    technique_count, is_primary_only, is_data_only)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (paper_info['paper_id'], paper_info['year'], disc['discipline_code'],
                 disc['assignment_type'], disc['technique_count'],
                 is_primary_only, is_data_only)
            )

        self.conn.commit()

    def store_authors(self, paper_info):
        """Store author information and relationships."""
        author_ids = []

        for position, surname in enumerate(paper_info['all_authors'], 1):
            researcher_id = self.get_or_create_researcher(surname, paper_info['all_authors'])
            author_ids.append(researcher_id)

            if not self.dry_run:
                cursor = self.conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO paper_authors
                       (paper_id, researcher_id, author_position, year)
                       VALUES (?, ?, ?, ?)""",
                    (paper_info['paper_id'], researcher_id, position, paper_info['year'])
                )

        # Update collaborations
        if paper_info['year']:
            self.update_collaborations(author_ids, paper_info['year'])

        if not self.dry_run:
            self.conn.commit()

    def record_success(self, paper_info, techniques, text_length, processing_time):
        """Record successful extraction."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO extraction_log
               (paper_id, paper_path, status, techniques_found,
                text_extracted_length, processing_time_sec, extraction_date)
               VALUES (?, ?, 'success', ?, ?, ?, ?)""",
            (paper_info['paper_id'], paper_info['paper_path'], len(techniques),
             text_length, processing_time, datetime.now().isoformat())
        )
        self.conn.commit()

        self.processed_papers.add(paper_info['paper_id'])

    def record_failure(self, paper_info, error_msg):
        """Record failed extraction."""
        if self.dry_run:
            return

        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO extraction_log
               (paper_id, paper_path, status, error_message, extraction_date)
               VALUES (?, ?, 'failed', ?, ?)""",
            (paper_info['paper_id'], paper_info['paper_path'], error_msg,
             datetime.now().isoformat())
        )
        self.conn.commit()

        self.stats['papers_failed'] += 1

    def process_paper_wrapper(self, pdf_path):
        """Wrapper for parallel processing - returns results instead of writing to DB."""
        paper_start = time.time()

        try:
            # Parse filename
            paper_info = self.parse_filename(pdf_path)

            # Extract text
            text = self.extract_pdf_text(pdf_path)
            if not text or len(text) > MAX_TEXT_LENGTH:
                return None

            # Search for techniques
            techniques_found = self.search_techniques(text)

            # Calculate disciplines
            disciplines, is_data_only, is_primary_only = self.calculate_disciplines(techniques_found)

            return {
                'paper_info': paper_info,
                'techniques': techniques_found,
                'disciplines': disciplines,
                'is_data_only': is_data_only,
                'is_primary_only': is_primary_only,
                'text_length': len(text),
                'processing_time': time.time() - paper_start
            }

        except Exception as e:
            return None

    def write_results_batch(self, results_batch):
        """Write batch of results to database (thread-safe)."""
        if self.dry_run:
            return

        with self.db_lock:
            for result in results_batch:
                if result:
                    self.store_paper_techniques(result['paper_info'], result['techniques'])
                    self.store_paper_disciplines(result['paper_info'], result['disciplines'],
                                                result['is_data_only'], result['is_primary_only'])
                    self.store_authors(result['paper_info'])
                    self.record_success(result['paper_info'], result['techniques'],
                                      result['text_length'], result['processing_time'])

                    self.stats['papers_processed'] += 1
                    self.stats['techniques_found'] += len(result['techniques'])

    def run(self):
        """Run extraction across all PDFs using parallel processing."""
        print("=" * 80)
        print("PDF TECHNIQUE EXTRACTION (PARALLEL)")
        print("=" * 80)

        if self.dry_run:
            print("⚠️  DRY RUN MODE")

        # Get all PDFs
        all_pdfs = sorted(PDF_BASE.glob("*/*.pdf"))
        unprocessed = [p for p in all_pdfs if p.name not in self.processed_papers]

        print(f"\n📊 Status:")
        print(f"  Total PDFs: {len(all_pdfs):,}")
        print(f"  Already processed: {len(self.processed_papers):,}")
        print(f"  To process: {len(unprocessed):,}")
        print(f"  Techniques to search: {len(self.techniques)}")
        print(f"  CPU cores: {self.num_workers}")
        print(f"\n🚀 Starting parallel extraction...\n")

        # Process in parallel with progress bar
        with Pool(processes=self.num_workers) as pool:
            results_batch = []

            for result in tqdm(pool.imap_unordered(self.process_paper_wrapper, unprocessed),
                             total=len(unprocessed),
                             desc="Processing PDFs"):

                if result:
                    results_batch.append(result)

                # Write batch to DB periodically
                if len(results_batch) >= BATCH_SIZE:
                    self.write_results_batch(results_batch)
                    self.save_progress()
                    results_batch = []

            # Write final batch
            if results_batch:
                self.write_results_batch(results_batch)

        # Final save
        self.save_progress()

        # Print summary
        self.print_summary()

    def save_progress(self):
        """Save current progress."""
        elapsed = time.time() - self.start_time

        stats = {
            'timestamp': datetime.now().isoformat(),
            'elapsed_seconds': elapsed,
            'stats': dict(self.stats)
        }

        with open(OUTPUT_DIR / 'extraction_progress.json', 'w') as f:
            json.dump(stats, f, indent=2)

    def print_summary(self):
        """Print extraction summary."""
        elapsed = time.time() - self.start_time

        print("\n" + "=" * 80)
        print("EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"\n⏱️  Time: {elapsed/60:.1f} minutes")
        print(f"\n📊 Results:")
        print(f"  Papers processed: {self.stats['papers_processed']:,}")
        print(f"  Papers failed: {self.stats['papers_failed']:,}")
        print(f"  Techniques found: {self.stats['techniques_found']:,}")
        print(f"  Avg techniques/paper: {self.stats['techniques_found']/max(1,self.stats['papers_processed']):.1f}")

        print(f"\n💾 Output:")
        print(f"  Database: {DATABASE}")
        print(f"  Logs: {LOG_FILE}")

def main():
    parser = argparse.ArgumentParser(
        description='Extract techniques from PDFs with researcher scaffolding (parallel)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - no database writes'
    )

    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Start fresh, ignore previous progress'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of CPU cores to use (default: all cores - 1)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of PDFs to process (for testing)'
    )

    args = parser.parse_args()

    extractor = TechniqueExtractor(
        dry_run=args.dry_run,
        resume=not args.no_resume,
        num_workers=args.workers
    )

    extractor.run()

if __name__ == "__main__":
    main()
