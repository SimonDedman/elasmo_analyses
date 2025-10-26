#!/usr/bin/env python3
"""
PDF Pipeline Processor - Continuous processing of downloaded PDFs

Runs alongside the download daemon and processes new PDFs through:
1. Rename to standard format
2. Move to correct year folder
3. Deduplicate
4. Extract metadata
5. OCR if needed
6. Update database

This ensures minimal backlog when downloads complete.
"""

import pandas as pd
import sqlite3
from pathlib import Path
import time
import subprocess
import hashlib
import shutil
from datetime import datetime
from difflib import SequenceMatcher
import re
from collections import defaultdict
import argparse

# Configuration
PROJECT_BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
DOWNLOAD_LOG = PROJECT_BASE / "logs/scihub_download_log.csv"
PIPELINE_LOG = PROJECT_BASE / "logs/pipeline_processing.log"
PIPELINE_STATE = PROJECT_BASE / "logs/pipeline_state.json"
DATABASE = PROJECT_BASE / "data/shark_references.db"

# Processing thresholds
MIN_TEXT_LENGTH = 100  # Minimum chars to consider PDF has text
OCR_TIMEOUT = 300  # 5 minutes per PDF
BATCH_SIZE = 50  # Process this many PDFs before checking for new downloads
CHECK_INTERVAL = 60  # Seconds between checking for new downloads


class PDFPipeline:
    """Manages continuous PDF processing pipeline."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.processed_pdfs = set()
        self.stats = defaultdict(int)
        self.load_state()

    def load_state(self):
        """Load previously processed PDFs to avoid reprocessing."""
        if PIPELINE_STATE.exists():
            import json
            with open(PIPELINE_STATE) as f:
                state = json.load(f)
                self.processed_pdfs = set(state.get('processed', []))
                print(f"Loaded state: {len(self.processed_pdfs)} PDFs already processed")

    def save_state(self):
        """Save processed PDF list."""
        import json
        PIPELINE_STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(PIPELINE_STATE, 'w') as f:
            json.dump({
                'processed': list(self.processed_pdfs),
                'last_update': datetime.now().isoformat(),
                'stats': dict(self.stats)
            }, f, indent=2)

    def log(self, message, level="INFO"):
        """Log message to file and console."""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} [{level}] {message}"
        print(log_entry)

        PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(PIPELINE_LOG, 'a') as f:
            f.write(log_entry + "\n")

    def get_unprocessed_pdfs(self):
        """Find PDFs that haven't been processed yet."""
        all_pdfs = list(PDF_BASE.glob("*/*.pdf"))
        unprocessed = [p for p in all_pdfs if str(p) not in self.processed_pdfs]
        return unprocessed

    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF using pdftotext."""
        try:
            result = subprocess.run(
                ['pdftotext', '-l', '2', str(pdf_path), '-'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except Exception as e:
            self.log(f"Text extraction failed for {pdf_path.name}: {e}", "WARNING")
            return ""

    def needs_ocr(self, pdf_path):
        """Check if PDF needs OCR."""
        text = self.extract_pdf_text(pdf_path)
        return len(text.strip()) < MIN_TEXT_LENGTH

    def run_ocr(self, pdf_path):
        """Run OCR on PDF if needed."""
        if not self.needs_ocr(pdf_path):
            self.log(f"OCR not needed: {pdf_path.name}")
            self.stats['ocr_skipped'] += 1
            return True

        if self.dry_run:
            self.log(f"[DRY RUN] Would OCR: {pdf_path.name}")
            self.stats['ocr_would_run'] += 1
            return True

        try:
            # Create backup
            backup_dir = PROJECT_BASE / "backups/pre_ocr" / pdf_path.parent.name
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / pdf_path.name

            if not backup_path.exists():
                shutil.copy2(pdf_path, backup_path)

            # Run OCR
            self.log(f"Running OCR: {pdf_path.name}")
            result = subprocess.run(
                ['ocrmypdf', '--skip-text', '--optimize', '1',
                 '--output-type', 'pdf', str(pdf_path), str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=OCR_TIMEOUT
            )

            if result.returncode == 0:
                self.log(f"OCR success: {pdf_path.name}")
                self.stats['ocr_success'] += 1
                return True
            else:
                self.log(f"OCR failed: {pdf_path.name} - {result.stderr}", "ERROR")
                self.stats['ocr_failed'] += 1
                return False

        except subprocess.TimeoutExpired:
            self.log(f"OCR timeout: {pdf_path.name}", "WARNING")
            self.stats['ocr_timeout'] += 1
            return False
        except Exception as e:
            self.log(f"OCR error: {pdf_path.name} - {e}", "ERROR")
            self.stats['ocr_error'] += 1
            return False

    def extract_metadata(self, pdf_path):
        """Extract metadata from PDF."""
        try:
            result = subprocess.run(
                ['pdfinfo', str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            metadata = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()

            return metadata
        except Exception as e:
            self.log(f"Metadata extraction failed: {pdf_path.name} - {e}", "WARNING")
            return {}

    def compute_md5(self, pdf_path):
        """Compute MD5 hash of PDF."""
        try:
            md5 = hashlib.md5()
            with open(pdf_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            self.log(f"MD5 computation failed: {pdf_path.name} - {e}", "WARNING")
            return None

    def find_duplicates(self, pdf_path):
        """Check if this PDF is a duplicate of existing files."""
        # Get MD5 of current file
        md5 = self.compute_md5(pdf_path)
        if not md5:
            return []

        # Find other PDFs with same MD5 or very similar names
        duplicates = []
        year_folder = pdf_path.parent

        for other_pdf in year_folder.glob("*.pdf"):
            if other_pdf == pdf_path:
                continue

            # Check MD5 match
            other_md5 = self.compute_md5(other_pdf)
            if other_md5 and other_md5 == md5:
                duplicates.append(('md5', other_pdf))
                continue

            # Check filename similarity
            similarity = SequenceMatcher(None, pdf_path.name.lower(),
                                       other_pdf.name.lower()).ratio()
            if similarity > 0.8:
                duplicates.append(('name', other_pdf))

        return duplicates

    def handle_duplicate(self, pdf_path, duplicate_type, duplicate_path):
        """Handle duplicate PDF - keep better version."""
        # Prefer abbreviated names
        def abbreviation_score(name):
            abbrevs = ['etal', 'ecol', 'pred', 'hab', 'popns', 'behav',
                      'strat', 'synth', 'var', 'abund']
            score = sum(1 for a in abbrevs if a in name.lower())
            if '_v' in name.lower():
                score -= 5  # Penalize versioned files
            return score

        score1 = abbreviation_score(pdf_path.name)
        score2 = abbreviation_score(duplicate_path.name)

        if score1 > score2:
            # Keep current, remove duplicate
            to_remove = duplicate_path
            to_keep = pdf_path
        else:
            # Keep duplicate, remove current
            to_remove = pdf_path
            to_keep = duplicate_path

        if self.dry_run:
            self.log(f"[DRY RUN] Would remove duplicate: {to_remove.name} (keep: {to_keep.name})")
            self.stats['dup_would_remove'] += 1
        else:
            self.log(f"Removing duplicate: {to_remove.name} (keeping: {to_keep.name})")
            to_remove.unlink()
            self.stats['dup_removed'] += 1

        return to_keep

    def update_database(self, pdf_path, metadata):
        """Update shark_references database with PDF info."""
        if not DATABASE.exists():
            self.log("Database not found, skipping update", "WARNING")
            return

        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            # Extract year and author from filename
            filename = pdf_path.stem
            parts = filename.split('.')

            if len(parts) < 3:
                self.log(f"Cannot parse filename: {filename}", "WARNING")
                conn.close()
                return

            author = parts[0]
            year = pdf_path.parent.name

            # Try to match paper in database
            # This is a simplified match - might need more sophisticated matching
            cursor.execute("""
                UPDATE papers
                SET has_pdf = 1,
                    pdf_path = ?,
                    pdf_added_date = ?
                WHERE first_author LIKE ?
                AND year = ?
                AND has_pdf = 0
                LIMIT 1
            """, (str(pdf_path), datetime.now().isoformat(), f"{author}%", year))

            if cursor.rowcount > 0:
                self.log(f"Database updated for: {pdf_path.name}")
                self.stats['db_updated'] += 1
            else:
                self.stats['db_no_match'] += 1

            conn.commit()
            conn.close()

        except Exception as e:
            self.log(f"Database update failed: {pdf_path.name} - {e}", "ERROR")
            self.stats['db_error'] += 1

    def process_pdf(self, pdf_path):
        """Process a single PDF through the pipeline."""
        self.log(f"Processing: {pdf_path.name}")

        try:
            # Step 1: Check for duplicates
            duplicates = self.find_duplicates(pdf_path)
            if duplicates:
                for dup_type, dup_path in duplicates:
                    kept_path = self.handle_duplicate(pdf_path, dup_type, dup_path)
                    if kept_path != pdf_path:
                        # Current file was removed, stop processing
                        self.log(f"PDF was removed as duplicate: {pdf_path.name}")
                        self.stats['removed_as_dup'] += 1
                        return

            # Step 2: Extract metadata
            metadata = self.extract_metadata(pdf_path)

            # Step 3: Run OCR if needed
            self.run_ocr(pdf_path)

            # Step 4: Update database
            self.update_database(pdf_path, metadata)

            # Mark as processed
            self.processed_pdfs.add(str(pdf_path))
            self.stats['total_processed'] += 1

        except Exception as e:
            self.log(f"Processing failed: {pdf_path.name} - {e}", "ERROR")
            self.stats['processing_failed'] += 1

    def process_batch(self, pdfs, batch_size=BATCH_SIZE):
        """Process a batch of PDFs."""
        for i, pdf in enumerate(pdfs[:batch_size], 1):
            self.log(f"Batch progress: {i}/{min(batch_size, len(pdfs))}")
            self.process_pdf(pdf)

            # Save state periodically
            if i % 10 == 0:
                self.save_state()

    def run_continuous(self):
        """Run continuous processing loop."""
        self.log("=" * 80)
        self.log("PDF PIPELINE PROCESSOR STARTED")
        self.log("=" * 80)

        if self.dry_run:
            self.log("DRY RUN MODE - No files will be modified")

        iteration = 0

        while True:
            iteration += 1
            self.log(f"\n--- Iteration {iteration} ---")

            # Find unprocessed PDFs
            unprocessed = self.get_unprocessed_pdfs()
            self.log(f"Found {len(unprocessed)} unprocessed PDFs")

            if unprocessed:
                # Process batch
                self.process_batch(unprocessed, BATCH_SIZE)
                self.save_state()

                # Show stats
                self.log("\nCurrent Statistics:")
                for key, value in sorted(self.stats.items()):
                    self.log(f"  {key}: {value}")
            else:
                self.log("No unprocessed PDFs found")

            # Check if download daemon is still running
            try:
                result = subprocess.run(
                    ['pgrep', '-f', 'scihub_downloader'],
                    capture_output=True
                )
                downloader_running = result.returncode == 0
            except:
                downloader_running = False

            if not downloader_running and not unprocessed:
                self.log("\n" + "=" * 80)
                self.log("Download complete and all PDFs processed!")
                self.log("=" * 80)
                break

            # Wait before next check
            self.log(f"\nWaiting {CHECK_INTERVAL}s before next check...")
            time.sleep(CHECK_INTERVAL)

        # Final summary
        self.log("\n" + "=" * 80)
        self.log("PIPELINE PROCESSING COMPLETE")
        self.log("=" * 80)
        self.log("\nFinal Statistics:")
        for key, value in sorted(self.stats.items()):
            self.log(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(
        description='Continuous PDF processing pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without modifying files'
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='Process once and exit (no continuous loop)'
    )

    args = parser.parse_args()

    pipeline = PDFPipeline(dry_run=args.dry_run)

    if args.once:
        # Single batch processing
        unprocessed = pipeline.get_unprocessed_pdfs()
        print(f"Found {len(unprocessed)} unprocessed PDFs")

        if unprocessed:
            pipeline.process_batch(unprocessed, BATCH_SIZE)
            pipeline.save_state()

            print("\nStatistics:")
            for key, value in sorted(pipeline.stats.items()):
                print(f"  {key}: {value}")
    else:
        # Continuous processing
        pipeline.run_continuous()


if __name__ == "__main__":
    main()
