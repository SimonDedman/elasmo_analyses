#!/usr/bin/env python3
"""
organize_unmatched_pdfs.py

Organize unmatched PDFs from unknown_year/ and root level by matching them
to the database using multiple strategies.

This script handles PDFs that couldn't be automatically matched during
initial download, using more sophisticated matching techniques.

Usage:
    python3 scripts/organize_unmatched_pdfs.py

    # Dry run (don't move files)
    python3 scripts/organize_unmatched_pdfs.py --dry-run

    # Be more aggressive with partial matches
    python3 scripts/organize_unmatched_pdfs.py --fuzzy

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

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
OUTPUT_DIR = Path("/home/simon/Documents/Si Work/Papers & Books/SharkPapers")
LOG_FILE = BASE_DIR / "logs/pdf_organization_log.csv"
UNMATCHED_REPORT = BASE_DIR / "logs/unmatched_pdfs.csv"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_filename(text, max_length=100):
    """
    Convert text to safe filename.

    Args:
        text: Text to convert
        max_length: Maximum filename length

    Returns:
        Safe filename string
    """
    # Remove or replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '', text)
    safe = re.sub(r'\s+', '.', safe.strip())
    safe = re.sub(r'\.+', '.', safe)

    # Truncate if too long
    if len(safe) > max_length:
        safe = safe[:max_length]

    return safe


def extract_first_author(authors_str):
    """Extract first author surname from authors string."""
    if pd.isna(authors_str) or not authors_str:
        return "Unknown"

    # Split by '&' or ';' to get first author
    first_author = authors_str.split('&')[0].split(';')[0].strip()

    # Extract surname (before comma or parenthesis)
    parts = re.split(r'[,\(]', first_author)
    surname = parts[0].strip()

    return safe_filename(surname, max_length=20)


def extract_pdf_metadata(pdf_path):
    """
    Extract metadata from PDF using pdfinfo.

    Args:
        pdf_path: Path to PDF file

    Returns:
        dict with 'title', 'author', 'subject', 'keywords'
    """
    metadata = {
        'title': None,
        'author': None,
        'subject': None,
        'keywords': None
    }

    try:
        result = subprocess.run(
            ['pdfinfo', str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Title:'):
                    metadata['title'] = line.split(':', 1)[1].strip()
                elif line.startswith('Author:'):
                    metadata['author'] = line.split(':', 1)[1].strip()
                elif line.startswith('Subject:'):
                    metadata['subject'] = line.split(':', 1)[1].strip()
                elif line.startswith('Keywords:'):
                    metadata['keywords'] = line.split(':', 1)[1].strip()
    except Exception as e:
        print(f"  ⚠️  pdfinfo failed for {pdf_path.name}: {e}")

    return metadata


def clean_title_for_matching(title):
    """Clean title for fuzzy matching."""
    if not title:
        return ""

    # Lowercase
    clean = title.lower()

    # Remove common problematic characters
    clean = re.sub(r'[^\w\s]', ' ', clean)

    # Remove extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()

    return clean


def extract_year_from_filename(filename):
    """Try to extract year from filename."""
    # Look for 4-digit year (19xx or 20xx)
    match = re.search(r'\b(19\d{2}|20\d{2})\b', filename)
    if match:
        return int(match.group(1))
    return None


def match_by_doi_from_filename(filename, db_df):
    """
    Extract DOI from filename and match to database.

    Patterns:
    - PeerJ_peerj-2041.pdf → 10.7717/peerj.2041
    - other patterns as needed
    """
    # PeerJ pattern: peerj-XXXX
    peerj_match = re.search(r'peerj-(\d+)', filename, re.IGNORECASE)
    if peerj_match:
        article_id = peerj_match.group(1)
        doi = f"10.7717/peerj.{article_id}"

        # Search database for this DOI
        matches = db_df[db_df['doi'] == doi]
        if len(matches) > 0:
            return matches.index[0]

    # Generic DOI pattern in filename: 10.XXXX/YYYY
    doi_match = re.search(r'10\.\d{4,}/[^\s]+', filename)
    if doi_match:
        doi = doi_match.group(0).rstrip('.pdf')
        matches = db_df[db_df['doi'] == doi]
        if len(matches) > 0:
            return matches.index[0]

    return None


def match_by_url_pattern(filename, db_df):
    """
    Extract URL patterns from filename and match to database URL field.

    Examples:
    - NCBI_jphysiol00852-0018.pdf → match URL containing "jphysiol00852"
    """
    # Extract potential identifiers from filename
    # Remove prefix like "NCBI_", "PeerJ_", "scielo_"
    clean_name = re.sub(r'^(NCBI|PeerJ|scielo|document)_?', '', filename, flags=re.IGNORECASE)
    clean_name = clean_name.replace('.pdf', '')

    if len(clean_name) < 5:
        return None

    # Search for this pattern in PDF URLs
    for idx, row in db_df.iterrows():
        if pd.isna(row['pdf_url']):
            continue

        url = row['pdf_url'].lower()
        if clean_name.lower() in url:
            return idx

    return None


def match_by_title_exact(pdf_title, db_df):
    """Try exact title match."""
    clean_pdf = clean_title_for_matching(pdf_title)

    if len(clean_pdf) < 10:
        return None

    for idx, row in db_df.iterrows():
        db_title = clean_title_for_matching(row['title'])
        if clean_pdf == db_title:
            return idx

    return None


def match_by_title_fuzzy(pdf_title, db_df, threshold=0.85):
    """Try fuzzy title match using difflib."""
    clean_pdf = clean_title_for_matching(pdf_title)

    if len(clean_pdf) < 15:
        return None

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


def match_by_title_substring(pdf_title, db_df, min_length=40):
    """Try substring match for longer titles."""
    clean_pdf = clean_title_for_matching(pdf_title)

    if len(clean_pdf) < min_length:
        return None

    # Use first 40 characters for matching
    pdf_start = clean_pdf[:40]

    for idx, row in db_df.iterrows():
        db_title = clean_title_for_matching(row['title'])

        if pdf_start in db_title or db_title[:40] in clean_pdf:
            return idx

    return None


def match_by_filename_patterns(filename, db_df):
    """Try to extract author/year from filename and match."""
    # Look for patterns like "Author.etal.YEAR" or "Author_YEAR"

    # Extract year
    year = extract_year_from_filename(filename)

    if not year:
        return None

    # Extract potential author surname (first word before . or _)
    author_match = re.match(r'^([A-Za-z]+)', filename)
    if not author_match:
        return None

    author = author_match.group(1).lower()

    # Search for papers with matching year and author
    year_matches = db_df[db_df['year'] == year]

    for idx, row in year_matches.iterrows():
        if pd.isna(row['authors']):
            continue

        # Check if author surname appears in authors string
        if author in row['authors'].lower():
            return idx

    return None


def match_pdf_to_database(pdf_path, db_df, use_fuzzy=False):
    """
    Try multiple strategies to match PDF to database.

    Args:
        pdf_path: Path to PDF
        db_df: Database DataFrame
        use_fuzzy: Whether to use fuzzy matching

    Returns:
        tuple: (matched_index, match_method, confidence) or (None, None, 0)
    """
    filename = pdf_path.name

    # Strategy 1: DOI from filename (highest confidence)
    idx = match_by_doi_from_filename(filename, db_df)
    if idx is not None:
        return (idx, 'doi_filename', 1.0)

    # Strategy 2: URL pattern from filename
    idx = match_by_url_pattern(filename, db_df)
    if idx is not None:
        return (idx, 'url_pattern', 0.95)

    # Extract metadata
    metadata = extract_pdf_metadata(pdf_path)

    # Strategy 3: Exact title match
    if metadata['title'] and len(metadata['title']) > 10:
        idx = match_by_title_exact(metadata['title'], db_df)
        if idx is not None:
            return (idx, 'exact_title', 0.9)

    # Strategy 4: Substring match for longer titles
    if metadata['title'] and len(metadata['title']) > 40:
        idx = match_by_title_substring(metadata['title'], db_df)
        if idx is not None:
            return (idx, 'substring_title', 0.85)

    # Strategy 5: Fuzzy match (if enabled)
    if use_fuzzy and metadata['title'] and len(metadata['title']) > 15:
        idx = match_by_title_fuzzy(metadata['title'], db_df)
        if idx is not None:
            return (idx, 'fuzzy_title', 0.8)

    # Strategy 6: Filename pattern matching
    idx = match_by_filename_patterns(filename, db_df)
    if idx is not None:
        return (idx, 'filename_pattern', 0.7)

    return (None, None, 0.0)


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

    Args:
        pdf_path: Current PDF path
        db_row: Matching database row
        output_dir: Output directory
        dry_run: If True, don't actually move files

    Returns:
        tuple: (success, new_path, message)
    """
    try:
        # Create filename
        filename = create_proper_filename(
            db_row['authors'],
            db_row['year'],
            db_row['title'],
            db_row['literature_id']
        )

        # Determine year folder
        year = db_row['year']
        if pd.isna(year) or year == 0:
            year_dir = output_dir / "unknown_year"
        else:
            year_dir = output_dir / str(int(year))

        new_path = year_dir / filename

        # Check if already exists
        if new_path.exists():
            return (False, new_path, "Already exists")

        if not dry_run:
            # Create directory
            year_dir.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(pdf_path), str(new_path))

        return (True, new_path, "Moved successfully")

    except Exception as e:
        return (False, None, f"Error: {e}")


# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Organize unmatched PDFs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without moving files'
    )

    parser.add_argument(
        '--fuzzy',
        action='store_true',
        help='Use fuzzy matching (more aggressive, may have false positives)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("PDF ORGANIZATION TOOL")
    print("=" * 80)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No files will be moved\n")

    # Load database
    print("\n📖 Loading database...")
    db_df = pd.read_parquet(DATABASE_PARQUET)
    print(f"✅ Loaded {len(db_df):,} papers")

    # Find unorganized PDFs
    print("\n🔍 Finding unorganized PDFs...")

    unorganized_pdfs = []

    # Check unknown_year folder
    unknown_dir = OUTPUT_DIR / "unknown_year"
    if unknown_dir.exists():
        unorganized_pdfs.extend(list(unknown_dir.glob("*.pdf")))

    # Check root level
    root_pdfs = [f for f in OUTPUT_DIR.glob("*.pdf")]
    unorganized_pdfs.extend(root_pdfs)

    print(f"✅ Found {len(unorganized_pdfs)} unorganized PDFs")

    if len(unorganized_pdfs) == 0:
        print("\n🎉 No unorganized PDFs found!")
        return

    # Process each PDF
    print(f"\n📝 Processing PDFs (fuzzy={'enabled' if args.fuzzy else 'disabled'})...\n")

    results = []
    matched_count = 0
    unmatched_count = 0

    for pdf_path in tqdm(unorganized_pdfs, desc="Matching"):
        # Try to match
        idx, method, confidence = match_pdf_to_database(
            pdf_path,
            db_df,
            use_fuzzy=args.fuzzy
        )

        if idx is not None:
            # Match found
            db_row = db_df.loc[idx]

            # Organize PDF
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
                'match_method': method,
                'confidence': confidence,
                'literature_id': db_row['literature_id'],
                'title': db_row['title'],
                'authors': db_row['authors'],
                'year': db_row['year'],
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
        else:
            # No match found
            unmatched_count += 1

            # Get PDF metadata for report
            metadata = extract_pdf_metadata(pdf_path)

            results.append({
                'original_path': str(pdf_path),
                'new_path': None,
                'status': 'unmatched',
                'match_method': None,
                'confidence': 0.0,
                'literature_id': None,
                'title': metadata['title'],
                'authors': metadata['author'],
                'year': extract_year_from_filename(pdf_path.name),
                'message': 'No match found',
                'timestamp': datetime.now().isoformat()
            })

    # Save results
    results_df = pd.DataFrame(results)

    if not args.dry_run:
        results_df.to_csv(LOG_FILE, index=False)
        print(f"\n✅ Results saved: {LOG_FILE}")

    # Save unmatched report
    unmatched_df = results_df[results_df['status'] == 'unmatched']
    if len(unmatched_df) > 0:
        unmatched_df.to_csv(UNMATCHED_REPORT, index=False)
        print(f"✅ Unmatched report: {UNMATCHED_REPORT}")

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

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
