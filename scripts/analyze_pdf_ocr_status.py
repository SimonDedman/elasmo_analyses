#!/usr/bin/env python3
"""
Analyze PDFs to determine which lack OCR/searchable text.

Tests PDFs to see if they contain extractable text or if they're just scanned images.
"""

import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd
from tqdm import tqdm
import multiprocessing as mp
from functools import partial

# Paths
pdf_base = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
output_csv = Path("outputs/pdf_ocr_status.csv")
output_summary = Path("outputs/pdf_ocr_summary.txt")

# Configuration
MIN_TEXT_LENGTH = 100  # Minimum characters to consider "has text"
TEST_PAGES = 2  # Test first N pages
SAMPLE_SIZE = 500  # Set to number to test subset, None for all


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


def check_pdf_file(pdf_path):
    """
    Check a single PDF file for OCR status.

    Returns dict with file info and OCR status.
    """
    has_text, text_length, error = extract_text_from_pdf(pdf_path, pages=TEST_PAGES)

    # Get file info
    stat = pdf_path.stat()
    file_size_mb = stat.st_size / (1024 * 1024)

    # Extract year from path (folder name)
    year_folder = pdf_path.parent.name
    if year_folder.isdigit():
        year = int(year_folder)
    else:
        year = None

    return {
        'file_path': str(pdf_path),
        'filename': pdf_path.name,
        'year': year,
        'file_size_mb': round(file_size_mb, 2),
        'has_text': has_text,
        'text_length': text_length,
        'needs_ocr': not has_text,
        'error': error,
        'checked_timestamp': datetime.now().isoformat()
    }


def analyze_all_pdfs(sample_size=None):
    """
    Analyze all PDFs in the directory.
    """
    print("=" * 80)
    print("PDF OCR STATUS ANALYZER")
    print("=" * 80)

    # Find all PDFs
    print("\nFinding all PDFs...")
    all_pdfs = list(pdf_base.glob("*/*.pdf"))
    print(f"Found {len(all_pdfs):,} PDFs")

    # Sample if requested
    if sample_size and sample_size < len(all_pdfs):
        import random
        all_pdfs = random.sample(all_pdfs, sample_size)
        print(f"Analyzing sample of {len(all_pdfs):,} PDFs")

    # Process PDFs (with progress bar)
    print(f"\nAnalyzing PDFs (checking first {TEST_PAGES} pages)...")

    # Use multiprocessing for speed
    num_cores = mp.cpu_count() - 1  # Leave one core free

    with mp.Pool(num_cores) as pool:
        results = list(tqdm(
            pool.imap(check_pdf_file, all_pdfs),
            total=len(all_pdfs),
            desc="Processing"
        ))

    # Convert to DataFrame
    df = pd.DataFrame(results)

    return df


def generate_summary(df):
    """Generate summary statistics."""

    total = len(df)
    has_text = df['has_text'].sum()
    needs_ocr = df['needs_ocr'].sum()
    errors = df['error'].notna().sum()

    summary = []
    summary.append("=" * 80)
    summary.append("PDF OCR STATUS SUMMARY")
    summary.append("=" * 80)
    summary.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append(f"\nTotal PDFs analyzed: {total:,}")
    summary.append(f"\nOCR Status:")
    summary.append(f"  ✅ Has searchable text:  {has_text:>6,} ({has_text/total*100:5.1f}%)")
    summary.append(f"  ❌ Needs OCR:            {needs_ocr:>6,} ({needs_ocr/total*100:5.1f}%)")
    summary.append(f"  ⚠️  Errors:              {errors:>6,} ({errors/total*100:5.1f}%)")

    # By decade
    if 'year' in df.columns:
        summary.append("\n" + "-" * 80)
        summary.append("OCR Status by Decade:")
        summary.append("-" * 80)

        for decade_start in range(2020, 1940, -10):
            decade_end = decade_start + 9
            decade_df = df[(df['year'] >= decade_start) & (df['year'] <= decade_end)]

            if len(decade_df) > 0:
                decade_total = len(decade_df)
                decade_has_text = decade_df['has_text'].sum()
                decade_needs_ocr = decade_df['needs_ocr'].sum()

                summary.append(f"\n{decade_start}s ({decade_total:,} PDFs):")
                summary.append(f"  Has text:  {decade_has_text:>5,} ({decade_has_text/decade_total*100:5.1f}%)")
                summary.append(f"  Needs OCR: {decade_needs_ocr:>5,} ({decade_needs_ocr/decade_total*100:5.1f}%)")

    # File size stats
    summary.append("\n" + "-" * 80)
    summary.append("File Size Statistics:")
    summary.append("-" * 80)

    avg_size_with_text = df[df['has_text']]['file_size_mb'].mean()
    avg_size_needs_ocr = df[df['needs_ocr']]['file_size_mb'].mean()

    summary.append(f"\nAverage file size:")
    summary.append(f"  PDFs with text:    {avg_size_with_text:.2f} MB")
    summary.append(f"  PDFs needing OCR:  {avg_size_needs_ocr:.2f} MB")

    # Text length distribution (for PDFs with text)
    if has_text > 0:
        summary.append("\n" + "-" * 80)
        summary.append("Text Length Distribution (PDFs with text):")
        summary.append("-" * 80)

        text_lengths = df[df['has_text']]['text_length']

        summary.append(f"\nText characters extracted (first {TEST_PAGES} pages):")
        summary.append(f"  Minimum:   {text_lengths.min():>8,}")
        summary.append(f"  Maximum:   {text_lengths.max():>8,}")
        summary.append(f"  Mean:      {text_lengths.mean():>8,.0f}")
        summary.append(f"  Median:    {text_lengths.median():>8,.0f}")

    # Common errors
    if errors > 0:
        summary.append("\n" + "-" * 80)
        summary.append("Common Errors:")
        summary.append("-" * 80)

        error_counts = df[df['error'].notna()]['error'].value_counts()
        for error, count in error_counts.head(10).items():
            summary.append(f"  {error[:60]:60s}: {count:>5,}")

    # Sampling note
    if SAMPLE_SIZE:
        summary.append("\n" + "-" * 80)
        summary.append(f"⚠️  NOTE: This is based on a SAMPLE of {SAMPLE_SIZE:,} PDFs")
        summary.append(f"To analyze all PDFs, set SAMPLE_SIZE = None in script")
        summary.append("-" * 80)

    summary.append("\n" + "=" * 80)
    summary.append("Detailed results saved to: " + str(output_csv))
    summary.append("=" * 80)

    return "\n".join(summary)


def main():
    """Main function."""

    # Check if pdftotext is available
    try:
        subprocess.run(['pdftotext', '-v'], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ ERROR: pdftotext not found!")
        print("\nInstall with:")
        print("  sudo apt-get install poppler-utils")
        return

    # Analyze PDFs
    df = analyze_all_pdfs(sample_size=SAMPLE_SIZE)

    # Save results
    print(f"\nSaving results to {output_csv}...")
    output_csv.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(output_csv, index=False)
    print(f"✅ Saved {len(df):,} results")

    # Generate and display summary
    summary = generate_summary(df)
    print("\n" + summary)

    # Save summary
    print(f"\nSaving summary to {output_summary}...")
    with open(output_summary, 'w') as f:
        f.write(summary)
    print(f"✅ Summary saved")

    # Quick recommendations
    needs_ocr = df['needs_ocr'].sum()
    if needs_ocr > 0:
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print(f"\n{needs_ocr:,} PDFs need OCR processing.")
        print("\nOptions:")
        print("  1. OCR with Tesseract (free, open source)")
        print("     - Install: sudo apt-get install tesseract-ocr")
        print("     - Process: ocrmypdf input.pdf output.pdf")
        print("\n  2. Adobe Acrobat (commercial, best quality)")
        print("\n  3. Cloud services (Google Drive, etc.)")
        print("\nEstimated time for OCR:")
        print(f"  ~{needs_ocr * 2 / 60:.0f} hours (assuming 2 min/PDF with ocrmypdf)")
        print("=" * 80)


if __name__ == "__main__":
    main()
