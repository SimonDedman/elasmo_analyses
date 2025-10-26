#!/usr/bin/env python3
"""
OCR PDFs lacking searchable text and replace originals.

Features:
- Analyzes all PDFs for text content
- OCRs only PDFs that lack searchable text
- Replaces original with OCR'd version (keeping backup)
- Maintains log of processed files (skip already done)
- Can be run repeatedly as new PDFs are added
- Parallel processing for speed

Usage:
    # Test on sample first
    ./venv/bin/python scripts/ocr_missing_pdfs.py --test

    # Run on all PDFs
    ./venv/bin/python scripts/ocr_missing_pdfs.py

    # Run with custom number of parallel jobs
    ./venv/bin/python scripts/ocr_missing_pdfs.py --jobs 4
"""

import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd
from tqdm import tqdm
import multiprocessing as mp
from functools import partial
import shutil
import argparse

# Paths
pdf_base = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
project_base = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
ocr_log = project_base / "logs/ocr_processing_log.csv"
backup_dir = project_base / "backups/pre_ocr"

# Configuration
MIN_TEXT_LENGTH = 100  # Minimum characters to consider "has text"
TEST_PAGES = 2  # Test first N pages
OCRMYPDF_TIMEOUT = 300  # 5 minutes max per PDF


def extract_text_from_pdf(pdf_path, pages=2):
    """
    Extract text from PDF using pdftotext.

    Returns:
        (has_text, text_length, error_message)
    """
    try:
        result = subprocess.run(
            ['pdftotext', '-f', '1', '-l', str(pages), str(pdf_path), '-'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            text = result.stdout.strip()
            text_length = len(text)
            has_text = text_length >= MIN_TEXT_LENGTH

            return (has_text, text_length, None)
        else:
            return (False, 0, f"pdftotext error: {result.stderr[:100]}")

    except subprocess.TimeoutExpired:
        return (False, 0, "Timeout")
    except FileNotFoundError:
        return (False, 0, "pdftotext not installed")
    except Exception as e:
        return (False, 0, str(e)[:100])


def check_if_already_processed(pdf_path, log_df):
    """Check if PDF was already successfully OCR'd."""
    if log_df is None or len(log_df) == 0:
        return False

    # Check if this file was already processed successfully
    matches = log_df[
        (log_df['file_path'] == str(pdf_path)) &
        (log_df['status'] == 'success')
    ]

    return len(matches) > 0


def ocr_pdf(pdf_path, backup_dir, log_df=None):
    """
    OCR a single PDF and replace original.

    Returns:
        dict with processing results
    """
    # Check if already processed
    if check_if_already_processed(pdf_path, log_df):
        return {
            'file_path': str(pdf_path),
            'filename': pdf_path.name,
            'status': 'skipped_already_done',
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

    # Check if needs OCR
    has_text, text_length, error = extract_text_from_pdf(pdf_path, pages=TEST_PAGES)

    if has_text:
        # Already has text, skip
        return {
            'file_path': str(pdf_path),
            'filename': pdf_path.name,
            'status': 'skipped_has_text',
            'text_length': text_length,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

    # Needs OCR
    temp_output = pdf_path.parent / f"{pdf_path.stem}_ocr_temp.pdf"

    try:
        # Run OCR
        result = subprocess.run(
            [
                'ocrmypdf',
                '--deskew',              # Straighten pages
                '--rotate-pages',        # Auto-rotate pages
                '--clean',               # Clean up artifacts
                '--optimize', '1',       # Optimize images
                '--skip-text',           # Skip pages that already have text
                '--output-type', 'pdf',
                str(pdf_path),
                str(temp_output)
            ],
            capture_output=True,
            text=True,
            timeout=OCRMYPDF_TIMEOUT
        )

        if result.returncode == 0:
            # OCR successful

            # Create backup of original
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / pdf_path.name

            # Handle backup name collision
            if backup_path.exists():
                # Add timestamp to backup name
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"{pdf_path.stem}_{timestamp}.pdf"

            # Backup original
            shutil.copy2(pdf_path, backup_path)

            # Replace original with OCR'd version
            shutil.move(str(temp_output), str(pdf_path))

            return {
                'file_path': str(pdf_path),
                'filename': pdf_path.name,
                'status': 'success',
                'backup_path': str(backup_path),
                'error': None,
                'timestamp': datetime.now().isoformat()
            }

        else:
            # OCR failed
            # Clean up temp file if it exists
            if temp_output.exists():
                temp_output.unlink()

            return {
                'file_path': str(pdf_path),
                'filename': pdf_path.name,
                'status': 'failed',
                'error': result.stderr[:200] if result.stderr else 'Unknown error',
                'timestamp': datetime.now().isoformat()
            }

    except subprocess.TimeoutExpired:
        # Clean up temp file
        if temp_output.exists():
            temp_output.unlink()

        return {
            'file_path': str(pdf_path),
            'filename': pdf_path.name,
            'status': 'failed',
            'error': f'Timeout after {OCRMYPDF_TIMEOUT} seconds',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        # Clean up temp file
        if temp_output.exists():
            temp_output.unlink()

        return {
            'file_path': str(pdf_path),
            'filename': pdf_path.name,
            'status': 'failed',
            'error': str(e)[:200],
            'timestamp': datetime.now().isoformat()
        }


def load_existing_log():
    """Load existing OCR log if it exists."""
    if ocr_log.exists():
        try:
            df = pd.read_csv(ocr_log)
            return df
        except Exception as e:
            print(f"⚠️  Warning: Could not load existing log: {e}")
            return None
    return None


def save_results(results, append=True):
    """Save results to log file."""
    df = pd.DataFrame(results)

    ocr_log.parent.mkdir(parents=True, exist_ok=True)

    if append and ocr_log.exists():
        df.to_csv(ocr_log, mode='a', header=False, index=False)
    else:
        df.to_csv(ocr_log, index=False)


def main():
    parser = argparse.ArgumentParser(
        description='OCR PDFs lacking searchable text',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--jobs', '-j',
        type=int,
        default=None,
        help='Number of parallel jobs (default: CPU count - 1)'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: process only 10 PDFs'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without OCRing'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("PDF OCR PROCESSOR")
    print("=" * 80)

    # Check dependencies
    print("\n🔍 Checking dependencies...")
    try:
        subprocess.run(['pdftotext', '-v'], capture_output=True, check=True)
        print("  ✅ pdftotext found")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  ❌ pdftotext not found - install with: sudo apt-get install poppler-utils")
        return

    try:
        subprocess.run(['ocrmypdf', '--version'], capture_output=True, check=True)
        print("  ✅ ocrmypdf found")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  ❌ ocrmypdf not found - install with: sudo apt-get install ocrmypdf")
        return

    # Load existing log
    print("\n📋 Loading existing OCR log...")
    log_df = load_existing_log()

    if log_df is not None:
        print(f"  ✅ Found {len(log_df):,} previously processed PDFs")

        # Show summary of previous runs
        status_counts = log_df['status'].value_counts()
        print("\n  Previous processing summary:")
        for status, count in status_counts.items():
            print(f"    {status:25s}: {count:>6,}")
    else:
        print("  ℹ️  No existing log found - this is first run")

    # Find all PDFs
    print(f"\n🔍 Finding all PDFs in {pdf_base}...")
    all_pdfs = list(pdf_base.glob("*/*.pdf"))
    print(f"  ✅ Found {len(all_pdfs):,} PDFs")

    # Test mode
    if args.test:
        print(f"\n⚠️  TEST MODE - Processing only 10 PDFs")
        import random
        all_pdfs = random.sample(all_pdfs, min(10, len(all_pdfs)))

    if args.dry_run:
        print(f"\n⚠️  DRY RUN MODE - No files will be modified")

    # Determine number of parallel jobs
    if args.jobs:
        num_jobs = args.jobs
    else:
        num_jobs = max(1, mp.cpu_count() - 1)

    print(f"\n⚙️  Configuration:")
    print(f"  Parallel jobs: {num_jobs}")
    print(f"  Min text length: {MIN_TEXT_LENGTH} characters")
    print(f"  Test pages: {TEST_PAGES}")
    print(f"  Timeout per PDF: {OCRMYPDF_TIMEOUT} seconds")
    print(f"  Backup directory: {backup_dir}")

    if args.dry_run:
        print(f"\n📊 Analysis (dry run)...")

        # Quick scan to see what needs OCR
        needs_ocr = []
        has_text_count = 0
        already_done = 0

        for pdf_path in tqdm(all_pdfs, desc="Analyzing"):
            if check_if_already_processed(pdf_path, log_df):
                already_done += 1
                continue

            has_text, text_length, error = extract_text_from_pdf(pdf_path, pages=TEST_PAGES)

            if has_text:
                has_text_count += 1
            else:
                needs_ocr.append(pdf_path)

        print(f"\n📊 Dry run results:")
        print(f"  Total PDFs: {len(all_pdfs):,}")
        print(f"  Already processed: {already_done:,}")
        print(f"  Has text (skip): {has_text_count:,}")
        print(f"  Needs OCR: {len(needs_ocr):,}")

        if len(needs_ocr) > 0:
            print(f"\n  Estimated time: {len(needs_ocr) * 3 / num_jobs / 60:.1f} hours ({num_jobs} parallel jobs)")
            print(f"  Estimated disk usage (temp): {len(needs_ocr) * 9.66:.1f} MB")

        print(f"\n  Run without --dry-run to process files")
        return

    # Process PDFs
    print(f"\n🚀 Processing PDFs...")
    print(f"  (PDFs with text will be skipped automatically)")
    print("")

    start_time = datetime.now()

    # Create partial function with log_df
    ocr_func = partial(ocr_pdf, backup_dir=backup_dir, log_df=log_df)

    # Process in parallel
    with mp.Pool(num_jobs) as pool:
        results = list(tqdm(
            pool.imap(ocr_func, all_pdfs),
            total=len(all_pdfs),
            desc="Processing"
        ))

    # Save results
    print(f"\n💾 Saving results...")
    save_results(results, append=True)
    print(f"  ✅ Results saved to {ocr_log}")

    # Statistics
    elapsed = datetime.now() - start_time

    results_df = pd.DataFrame(results)
    status_counts = results_df['status'].value_counts()

    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)

    print(f"\nTotal PDFs processed: {len(results):,}")
    print(f"Elapsed time: {elapsed}")

    print(f"\nStatus breakdown:")
    for status, count in status_counts.items():
        pct = count / len(results) * 100
        print(f"  {status:25s}: {count:>6,} ({pct:5.1f}%)")

    # Show success details
    success_count = status_counts.get('success', 0)
    if success_count > 0:
        print(f"\n✅ Successfully OCR'd {success_count:,} PDFs")
        print(f"  Originals backed up to: {backup_dir}")
        print(f"  Average time: {elapsed.total_seconds() / success_count:.1f} seconds per PDF")

    # Show failures
    failed_count = status_counts.get('failed', 0)
    if failed_count > 0:
        print(f"\n❌ Failed to OCR {failed_count:,} PDFs")

        failed_pdfs = results_df[results_df['status'] == 'failed']

        print(f"\n  Common errors:")
        if 'error' in failed_pdfs.columns:
            error_counts = failed_pdfs['error'].value_counts()
            for error, count in error_counts.head(5).items():
                error_short = error[:60] if error else 'Unknown'
                print(f"    {error_short:60s}: {count:>3,}")

    # Show skipped
    skipped_has_text = status_counts.get('skipped_has_text', 0)
    skipped_done = status_counts.get('skipped_already_done', 0)

    if skipped_has_text > 0:
        print(f"\n⏭️  Skipped {skipped_has_text:,} PDFs (already have text)")

    if skipped_done > 0:
        print(f"⏭️  Skipped {skipped_done:,} PDFs (already processed previously)")

    print("\n" + "=" * 80)

    # Next steps
    print("\n💡 Next steps:")
    print(f"  1. Check log: cat {ocr_log}")
    print(f"  2. Backups at: {backup_dir}")
    print(f"  3. Run again tomorrow to OCR new PDFs from Sci-Hub downloads")
    print(f"  4. To restore a backup: cp {backup_dir}/filename.pdf <original_location>")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
