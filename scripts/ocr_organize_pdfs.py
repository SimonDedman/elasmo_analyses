#!/usr/bin/env python3
"""
ocr_organize_pdfs.py

Use OCR/text extraction from PDF first pages to match unorganized PDFs to database.
Particularly useful for root-level and NCBI PDFs with poor metadata.

Usage:
    python3 scripts/ocr_organize_pdfs.py --dry-run
    python3 scripts/ocr_organize_pdfs.py  # Actually move files

Author: Simon Dedman
Date: 2025-10-22
Version: 1.0
"""

import pandas as pd
import subprocess
from pathlib import Path
from datetime import datetime
import re
import shutil
import argparse
from tqdm import tqdm
import difflib
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
OUTPUT_DIR = Path("/home/simon/Documents/Si Work/Papers & Books/SharkPapers")
LOG_FILE = BASE_DIR / "logs/ocr_organization_log.csv"
NCBI_HTML = BASE_DIR / "outputs/manual_downloads/manual_downloads_ncbi_nlm_nih_gov.html"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_filename(text, max_length=100):
    """Convert text to safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '', text)
    safe = re.sub(r'\s+', '.', safe.strip())
    safe = re.sub(r'\.+', '.', safe)

    if len(safe) > max_length:
        safe = safe[:max_length]

    return safe


def extract_first_author(authors_str):
    """Extract first author surname."""
    if pd.isna(authors_str) or not authors_str:
        return "Unknown"

    first_author = authors_str.split('&')[0].split(';')[0].strip()
    parts = re.split(r'[,\(]', first_author)
    surname = parts[0].strip()

    return safe_filename(surname, max_length=20)


def extract_pdf_text(pdf_path, pages=1):
    """
    Extract text from first N pages of PDF using pdftotext.

    Args:
        pdf_path: Path to PDF
        pages: Number of pages to extract (default 1)

    Returns:
        Extracted text string
    """
    try:
        result = subprocess.run(
            ['pdftotext', '-f', '1', '-l', str(pages), str(pdf_path), '-'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return result.stdout

    except Exception as e:
        print(f"  ⚠️  pdftotext failed for {pdf_path.name}: {e}")

    return ""


def parse_title_from_text(text):
    """
    Extract title from PDF text.

    Common patterns:
    - All caps title at top
    - Mixed-case title (first line with capital letter)
    - Title before author names
    - Title after journal info
    """
    if not text:
        return None

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    if len(lines) < 3:
        return None

    # Strategy 1: Look for all-caps title in first 10 lines
    for i, line in enumerate(lines[:10]):
        if len(line) > 20 and line.isupper() and not line.startswith('J.'):
            # Combine ALL consecutive all-caps lines
            title = line
            j = i + 1
            while j < len(lines) and j < i + 5:  # Max 5 lines for title
                if lines[j].isupper() and len(lines[j]) > 10 and not lines[j].startswith(('BY ', 'From ')):
                    title += " " + lines[j]
                    j += 1
                else:
                    break
            return title

    # Strategy 2: Look for mixed-case title (common in newer papers)
    # Skip first few lines (usually journal/page info), then find title
    for i, line in enumerate(lines):
        # Skip very short lines and header info
        if len(line) < 20:
            continue

        # Skip common header patterns
        if line.startswith(('J.', 'Printed', 'With', 'pp.', 'Vol.', 'Department', 'BY ')):
            continue

        # Check if line looks like a title (starts with capital, reasonable length)
        if line[0].isupper() and len(line) > 20:
            # Combine with next line if it looks like title continuation
            title = line
            j = i + 1
            while j < len(lines) and j < i + 3:  # Max 3 lines for title
                next_line = lines[j]
                # Continue if next line also looks like title (starts with capital or lowercase)
                # But not if it's clearly an author line or section header
                if len(next_line) < 10:
                    break
                if next_line.startswith(('By ', 'BY ', 'Department', 'INTRODUCTION', 'Abstract')):
                    break
                # If next line starts with capital or is all lowercase, might be title continuation
                if next_line[0].isupper() or next_line.islower():
                    title += " " + next_line
                    j += 1
                else:
                    break

            return title

    # Strategy 3: Title is often longest line in first 10 lines
    candidates = []
    for i, line in enumerate(lines[:10]):
        if len(line) > 30 and not line.startswith(('BY ', 'From ', 'Department')):
            candidates.append((len(line), i, line))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][2]

    return None


def parse_authors_from_text(text):
    """Extract author names from text."""
    if not text:
        return None

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Look for lines with "BY" or "From"
    for i, line in enumerate(lines):
        if line.startswith('BY '):
            author_text = line.replace('BY ', '')
            # Clean up
            author_text = re.sub(r'\d+', '', author_text)  # Remove numbers
            return author_text

    return None


def parse_year_from_text(text):
    """Extract year from text."""
    if not text:
        return None

    # Look for 4-digit year (19xx or 20xx) in first few lines
    lines = text.split('\n')[:10]
    for line in lines:
        match = re.search(r'\b(19\d{2}|20\d{2})\b', line)
        if match:
            return int(match.group(1))

    return None


def clean_title_for_matching(title):
    """Clean title for fuzzy matching."""
    if not title:
        return ""

    clean = title.lower()
    clean = re.sub(r'[^\w\s]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    return clean


def match_by_ocr_title(pdf_title, db_df, threshold=0.75):
    """
    Match PDF title extracted from OCR against database.

    Args:
        pdf_title: Title extracted from PDF text
        db_df: Database DataFrame
        threshold: Fuzzy matching threshold

    Returns:
        Database index if matched, None otherwise
    """
    if not pdf_title or len(pdf_title) < 15:
        return None

    clean_pdf = clean_title_for_matching(pdf_title)

    # Try exact match first
    for idx, row in db_df.iterrows():
        db_title = clean_title_for_matching(row['title'])
        if clean_pdf == db_title:
            return idx

    # Try fuzzy match
    best_match = None
    best_ratio = threshold

    for idx, row in db_df.iterrows():
        db_title = clean_title_for_matching(row['title'])

        if len(db_title) < 10:
            continue

        ratio = difflib.SequenceMatcher(None, clean_pdf, db_title).ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            best_match = idx

    return best_match


def load_ncbi_html_list(html_path):
    """
    Load NCBI paper list from HTML file.

    Returns:
        DataFrame with literature_id, title, authors, year
    """
    if not html_path.exists():
        return None

    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    papers = []
    for paper_div in soup.find_all('div', class_='paper'):
        paper_id = paper_div.get('id', '').replace('paper-', '')

        title_elem = paper_div.find('div', class_='title')
        authors_elem = paper_div.find('div', class_='authors')
        year_elem = paper_div.find('div', class_='year')

        if paper_id and title_elem:
            papers.append({
                'literature_id': int(paper_id),
                'title': title_elem.text.strip(),
                'authors': authors_elem.text.strip() if authors_elem else '',
                'year': int(re.search(r'\d{4}', year_elem.text).group()) if year_elem else None
            })

    return pd.DataFrame(papers) if papers else None


def match_by_timestamp_to_ncbi_list(pdf_path, ncbi_df, tolerance_seconds=120):
    """
    Match PDF by creation timestamp to NCBI sequential download list.

    PDFs were downloaded sequentially, so timestamps correlate with list order.

    Args:
        pdf_path: Path to PDF
        ncbi_df: DataFrame from NCBI HTML list
        tolerance_seconds: Time window for matching

    Returns:
        literature_id if matched, None otherwise
    """
    if ncbi_df is None or len(ncbi_df) == 0:
        return None

    # Get PDF creation time
    pdf_mtime = pdf_path.stat().st_mtime
    pdf_datetime = datetime.fromtimestamp(pdf_mtime)

    # Find PDFs with similar timestamps
    root_pdfs = list(OUTPUT_DIR.glob("*.pdf"))
    ncbi_pdfs = [p for p in root_pdfs if 'ncbi' in p.name.lower()]

    # Sort by creation time
    ncbi_pdfs.sort(key=lambda p: p.stat().st_mtime)

    # Find position in sequence
    try:
        position = ncbi_pdfs.index(pdf_path)

        # Match to NCBI list (they should be in same order)
        if position < len(ncbi_df):
            return ncbi_df.iloc[position]['literature_id']

    except ValueError:
        pass

    return None


def create_proper_filename(authors, year, title, lit_id):
    """Create proper filename format."""
    first_author = extract_first_author(authors)
    safe_title = safe_filename(title, max_length=80)

    if pd.isna(year) or year == 0:
        year = "unknown"

    filename = f"{first_author}.etal.{year}.{safe_title}.pdf"

    return filename


def organize_pdf(pdf_path, db_row, output_dir, dry_run=False):
    """
    Organize PDF to proper location with proper name.

    Returns:
        tuple: (success, new_path, message)
    """
    try:
        filename = create_proper_filename(
            db_row['authors'],
            db_row['year'],
            db_row['title'],
            db_row['literature_id']
        )

        year = db_row['year']
        if pd.isna(year) or year == 0:
            year_dir = output_dir / "unknown_year"
        else:
            year_dir = output_dir / str(int(year))

        new_path = year_dir / filename

        if new_path.exists():
            return (False, new_path, "Already exists")

        if not dry_run:
            year_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(pdf_path), str(new_path))

        return (True, new_path, "Moved successfully")

    except Exception as e:
        return (False, None, f"Error: {e}")


# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Organize PDFs using OCR/text extraction',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without moving files'
    )

    parser.add_argument(
        '--ncbi-only',
        action='store_true',
        help='Only process NCBI PDFs (root level with ncbi in filename)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("PDF OCR ORGANIZATION TOOL")
    print("=" * 80)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No files will be moved\n")

    # Load database
    print("\n📖 Loading database...")
    db_df = pd.read_parquet(DATABASE_PARQUET)
    print(f"✅ Loaded {len(db_df):,} papers")

    # Load NCBI HTML list
    print("\n📋 Loading NCBI HTML list...")
    ncbi_df = load_ncbi_html_list(NCBI_HTML)
    if ncbi_df is not None:
        print(f"✅ Loaded {len(ncbi_df)} NCBI papers from HTML list")
    else:
        print("⚠️  No NCBI HTML list found")

    # Find unorganized PDFs
    print("\n🔍 Finding unorganized PDFs...")

    if args.ncbi_only:
        # Only process root-level NCBI PDFs
        unorganized_pdfs = [f for f in OUTPUT_DIR.glob("*.pdf") if 'ncbi' in f.name.lower()]
    else:
        # Process all unmatched PDFs
        unorganized_pdfs = []

        # Root level
        root_pdfs = list(OUTPUT_DIR.glob("*.pdf"))
        unorganized_pdfs.extend(root_pdfs)

        # Unknown year folder (unmatched from previous run)
        unknown_dir = OUTPUT_DIR / "unknown_year"
        if unknown_dir.exists():
            # Get unmatched PDFs from logs
            log_file = BASE_DIR / "logs/unmatched_pdfs.csv"
            if log_file.exists():
                unmatched_df = pd.read_csv(log_file)
                for path_str in unmatched_df['original_path']:
                    path = Path(path_str)
                    if path.exists():
                        unorganized_pdfs.append(path)

    print(f"✅ Found {len(unorganized_pdfs)} unorganized PDFs")

    if len(unorganized_pdfs) == 0:
        print("\n🎉 No unorganized PDFs found!")
        return

    # Process each PDF
    print(f"\n📝 Extracting text and matching...\n")

    results = []
    matched_count = 0
    unmatched_count = 0

    for pdf_path in tqdm(unorganized_pdfs, desc="Processing"):
        # Extract text from first page
        text = extract_pdf_text(pdf_path, pages=1)

        # Parse metadata
        ocr_title = parse_title_from_text(text)
        ocr_authors = parse_authors_from_text(text)
        ocr_year = parse_year_from_text(text)

        # Try matching strategies
        idx = None
        match_method = None
        confidence = 0.0

        # Strategy 1: OCR title matching
        if ocr_title:
            idx = match_by_ocr_title(ocr_title, db_df, threshold=0.75)
            if idx is not None:
                match_method = 'ocr_title'
                confidence = 0.85

        # Strategy 2: NCBI timestamp matching (for NCBI files)
        if idx is None and 'ncbi' in pdf_path.name.lower() and ncbi_df is not None:
            lit_id = match_by_timestamp_to_ncbi_list(pdf_path, ncbi_df)
            if lit_id is not None:
                matches = db_df[db_df['literature_id'] == lit_id]
                if len(matches) > 0:
                    idx = matches.index[0]
                    match_method = 'ncbi_timestamp'
                    confidence = 0.75

        # Process match
        if idx is not None:
            db_row = db_df.loc[idx]

            success, new_path, message = organize_pdf(
                pdf_path,
                db_row,
                OUTPUT_DIR,
                dry_run=args.dry_run
            )

            if success:
                matched_count += 1
                status = "matched"
            else:
                unmatched_count += 1
                status = "failed"

            results.append({
                'original_path': str(pdf_path),
                'new_path': str(new_path) if new_path else None,
                'status': status,
                'match_method': match_method,
                'confidence': confidence,
                'literature_id': db_row['literature_id'],
                'title': db_row['title'],
                'authors': db_row['authors'],
                'year': db_row['year'],
                'ocr_title': ocr_title,
                'ocr_year': ocr_year,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
        else:
            # No match found
            unmatched_count += 1

            results.append({
                'original_path': str(pdf_path),
                'new_path': None,
                'status': 'unmatched',
                'match_method': None,
                'confidence': 0.0,
                'literature_id': None,
                'title': None,
                'authors': None,
                'year': None,
                'ocr_title': ocr_title,
                'ocr_year': ocr_year,
                'message': 'No match found',
                'timestamp': datetime.now().isoformat()
            })

    # Save results
    results_df = pd.DataFrame(results)

    if not args.dry_run:
        results_df.to_csv(LOG_FILE, index=False)
        print(f"\n✅ Results saved: {LOG_FILE}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total PDFs processed: {len(unorganized_pdfs)}")
    print(f"✅ Successfully matched: {matched_count} ({matched_count/len(unorganized_pdfs)*100:.1f}%)")
    print(f"❌ Unmatched: {unmatched_count} ({unmatched_count/len(unorganized_pdfs)*100:.1f}%)")

    if matched_count > 0:
        print(f"\n📊 Match methods used:")
        method_dist = results_df[results_df['status'] == 'matched']['match_method'].value_counts()
        for method, count in method_dist.items():
            print(f"   • {method}: {count}")

    if args.dry_run:
        print(f"\n⚠️  DRY RUN - No files were actually moved")
        print(f"Run without --dry-run to move files")

    # Show some examples
    if matched_count > 0:
        print(f"\n📄 Example matches:")
        matched_samples = results_df[results_df['status'] == 'matched'].head(5)
        for _, row in matched_samples.iterrows():
            print(f"\n  {Path(row['original_path']).name}")
            print(f"  → {Path(row['new_path']).name if row['new_path'] else 'N/A'}")
            print(f"  Method: {row['match_method']} ({row['confidence']:.0%})")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
