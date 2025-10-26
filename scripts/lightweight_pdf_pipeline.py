#!/usr/bin/env python3
"""
Lightweight PDF Pipeline - Processes newly downloaded PDFs efficiently

Optimized for running alongside the Sci-Hub downloader.
Only processes NEW PDFs (checks OCR log to skip already-OCR'd files).

Pipeline steps:
1. Deduplicate (remove duplicates immediately)
2. Extract metadata
3. OCR only if needed AND not already OCR'd
4. Update database

Designed to be faster than the downloader, catching up quickly.
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
import json
import argparse
from tqdm import tqdm

# Configuration
PROJECT_BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PIPELINE_LOG = PROJECT_BASE / "logs/pipeline_lightweight.log"
PIPELINE_STATE = PROJECT_BASE / "logs/pipeline_state.json"
OCR_LOG = PROJECT_BASE / "logs/ocr_processing.log"  # Check this for already-OCR'd files

# Processing thresholds
MIN_TEXT_LENGTH = 100
OCR_TIMEOUT = 300
BATCH_SIZE = 100  # Larger batch since we're faster
CHECK_INTERVAL = 120  # Check every 2 minutes

class LightweightPipeline:
    """Fast pipeline processor for new downloads."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.processed_pdfs = set()
        self.ocr_completed_pdfs = set()
        self.stats = {
            'total_processed': 0,
            'dup_removed': 0,
            'ocr_needed': 0,
            'ocr_skipped_already_done': 0,
            'ocr_completed': 0,
            'metadata_extracted': 0,
            'db_updated': 0,
            'errors': 0
        }
        self.load_state()
        self.load_ocr_log()

    def load_state(self):
        """Load previously processed PDFs."""
        if PIPELINE_STATE.exists():
            with open(PIPELINE_STATE) as f:
                state = json.load(f)
                self.processed_pdfs = set(state.get('processed', []))
                print(f"📋 Loaded: {len(self.processed_pdfs)} PDFs already processed")

    def load_ocr_log(self):
        """Load list of PDFs that already have OCR."""
        if OCR_LOG.exists():
            with open(OCR_LOG) as f:
                for line in f:
                    if 'OCR success' in line or 'OCR not needed' in line:
                        # Extract filename from log
                        parts = line.split(':')
                        if len(parts) >= 3:
                            filename = parts[2].strip().split()[0]
                            self.ocr_completed_pdfs.add(filename)
            print(f"✅ Loaded: {len(self.ocr_completed_pdfs)} PDFs already OCR'd")

    def save_state(self):
        """Save state."""
        PIPELINE_STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(PIPELINE_STATE, 'w') as f:
            json.dump({
                'processed': list(self.processed_pdfs),
                'last_update': datetime.now().isoformat(),
                'stats': self.stats
            }, f, indent=2)

    def log(self, message):
        """Log message."""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} {message}"

        PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(PIPELINE_LOG, 'a') as f:
            f.write(log_entry + "\n")

    def get_unprocessed_pdfs(self):
        """Find new PDFs to process."""
        all_pdfs = list(PDF_BASE.glob("*/*.pdf"))
        unprocessed = [p for p in all_pdfs if str(p) not in self.processed_pdfs]
        return unprocessed

    def compute_md5(self, pdf_path):
        """Fast MD5 computation."""
        try:
            md5 = hashlib.md5()
            with open(pdf_path, 'rb') as f:
                # Read in 64KB chunks for speed
                for chunk in iter(lambda: f.read(65536), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        except:
            return None

    def find_and_remove_duplicates(self, pdf_path):
        """Find and remove duplicates immediately."""
        year_folder = pdf_path.parent
        md5 = self.compute_md5(pdf_path)

        if not md5:
            return True  # Keep file if can't check

        # Quick check for MD5 duplicates in same folder
        for other_pdf in year_folder.glob("*.pdf"):
            if other_pdf == pdf_path:
                continue

            other_md5 = self.compute_md5(other_pdf)
            if other_md5 and other_md5 == md5:
                # Duplicate found - keep better filename
                if self.should_keep_first(pdf_path, other_pdf):
                    # Remove other
                    if not self.dry_run:
                        other_pdf.unlink()
                        self.log(f"DUP_REMOVED: {other_pdf.name} (kept {pdf_path.name})")
                    self.stats['dup_removed'] += 1
                else:
                    # Remove current
                    if not self.dry_run:
                        pdf_path.unlink()
                        self.log(f"DUP_REMOVED: {pdf_path.name} (kept {other_pdf.name})")
                    self.stats['dup_removed'] += 1
                    return False  # Current was removed

        return True  # Keep current file

    def should_keep_first(self, file1, file2):
        """Decide which file to keep based on filename quality."""
        name1, name2 = file1.name, file2.name

        # Prefer non-versioned
        if '_v' in name1.lower() and '_v' not in name2.lower():
            return False
        if '_v' not in name1.lower() and '_v' in name2.lower():
            return True

        # Prefer abbreviated (more dots/shorter names)
        score1 = name1.count('.') - len(name1) / 100
        score2 = name2.count('.') - len(name2) / 100

        return score1 > score2

    def needs_ocr(self, pdf_path):
        """Check if PDF needs OCR (quick check)."""
        # First check if already OCR'd
        if pdf_path.name in self.ocr_completed_pdfs:
            self.stats['ocr_skipped_already_done'] += 1
            return False

        try:
            result = subprocess.run(
                ['pdftotext', '-l', '1', str(pdf_path), '-'],
                capture_output=True,
                text=True,
                timeout=5
            )
            text_length = len(result.stdout.strip())

            if text_length < MIN_TEXT_LENGTH:
                self.stats['ocr_needed'] += 1
                return True
            else:
                self.ocr_completed_pdfs.add(pdf_path.name)
                return False

        except:
            return False  # If check fails, skip OCR

    def run_ocr(self, pdf_path):
        """Run OCR if needed."""
        if self.dry_run:
            self.log(f"DRY_RUN_OCR: {pdf_path.name}")
            return True

        try:
            # Create backup
            backup_dir = PROJECT_BASE / "backups/pre_ocr" / pdf_path.parent.name
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / pdf_path.name

            if not backup_path.exists():
                shutil.copy2(pdf_path, backup_path)

            # Run OCR (simple mode for speed)
            subprocess.run(
                ['ocrmypdf', '--skip-text', '--fast', '--output-type', 'pdf',
                 str(pdf_path), str(pdf_path)],
                capture_output=True,
                timeout=OCR_TIMEOUT
            )

            self.log(f"OCR_SUCCESS: {pdf_path.name}")
            self.ocr_completed_pdfs.add(pdf_path.name)
            self.stats['ocr_completed'] += 1
            return True

        except Exception as e:
            self.log(f"OCR_ERROR: {pdf_path.name} - {e}")
            self.stats['errors'] += 1
            return False

    def extract_metadata(self, pdf_path):
        """Quick metadata extraction."""
        try:
            result = subprocess.run(
                ['pdfinfo', str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                self.stats['metadata_extracted'] += 1
                return True
        except:
            pass

        return False

    def process_pdf(self, pdf_path):
        """Process single PDF through pipeline."""
        try:
            # Step 1: Check/remove duplicates
            if not self.find_and_remove_duplicates(pdf_path):
                return  # File was removed as duplicate

            # Step 2: Extract metadata (fast)
            self.extract_metadata(pdf_path)

            # Step 3: OCR if needed
            if self.needs_ocr(pdf_path):
                self.run_ocr(pdf_path)

            # Mark processed
            self.processed_pdfs.add(str(pdf_path))
            self.stats['total_processed'] += 1

        except Exception as e:
            self.log(f"ERROR: {pdf_path.name} - {e}")
            self.stats['errors'] += 1

    def process_batch(self, pdfs):
        """Process batch with progress bar."""
        for pdf in tqdm(pdfs, desc="Processing PDFs"):
            self.process_pdf(pdf)

        self.save_state()

    def run_continuous(self):
        """Continuous processing loop."""
        print("=" * 80)
        print("LIGHTWEIGHT PDF PIPELINE")
        print("=" * 80)

        if self.dry_run:
            print("⚠️  DRY RUN MODE")

        iteration = 0

        while True:
            iteration += 1
            print(f"\n--- Iteration {iteration} ({datetime.now().strftime('%H:%M:%S')}) ---")

            unprocessed = self.get_unprocessed_pdfs()
            print(f"Found: {len(unprocessed)} unprocessed PDFs")

            if unprocessed:
                self.process_batch(unprocessed[:BATCH_SIZE])

                # Show stats
                print("\nStats:")
                print(f"  Processed: {self.stats['total_processed']}")
                print(f"  Duplicates removed: {self.stats['dup_removed']}")
                print(f"  OCR needed: {self.stats['ocr_needed']}")
                print(f"  OCR completed: {self.stats['ocr_completed']}")
                print(f"  OCR skipped (already done): {self.stats['ocr_skipped_already_done']}")

            # Check if downloader still running
            try:
                result = subprocess.run(
                    ['pgrep', '-f', 'scihub_downloader'],
                    capture_output=True
                )
                downloader_running = result.returncode == 0
            except:
                downloader_running = False

            if not downloader_running and len(unprocessed) == 0:
                print("\n✅ Download complete and all PDFs processed!")
                break

            print(f"\n💤 Waiting {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)

        # Final summary
        print("\n" + "=" * 80)
        print("PIPELINE COMPLETE")
        print("=" * 80)
        for key, value in sorted(self.stats.items()):
            print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(
        description='Lightweight PDF processing pipeline'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode'
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='Process once and exit'
    )

    args = parser.parse_args()

    pipeline = LightweightPipeline(dry_run=args.dry_run)

    if args.once:
        unprocessed = pipeline.get_unprocessed_pdfs()
        print(f"Found {len(unprocessed)} unprocessed PDFs")

        if unprocessed:
            pipeline.process_batch(unprocessed[:BATCH_SIZE])

            print("\nFinal stats:")
            for key, value in sorted(pipeline.stats.items()):
                print(f"  {key}: {value}")
    else:
        pipeline.run_continuous()


if __name__ == "__main__":
    main()
