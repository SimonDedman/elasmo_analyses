#!/usr/bin/env python3
"""
Rename DOI-formatted PDFs to Author.Year.Title.pdf format.

Uses the shark-references CSV to map DOI → metadata.
"""

import pandas as pd
import re
from pathlib import Path
import shutil

# Paths
csv_path = Path("outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv")
pdf_base = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
log_file = Path("logs/doi_rename_log.txt")

# Create log
log_file.parent.mkdir(exist_ok=True)
log_entries = []

def normalize_doi(doi):
    """Normalize DOI for matching (remove https://, doi.org/, etc.)"""
    if pd.isna(doi) or not doi:
        return None

    doi = str(doi).strip()
    # Remove common prefixes
    doi = doi.replace('https://doi.org/', '')
    doi = doi.replace('http://doi.org/', '')
    doi = doi.replace('doi.org/', '')
    doi = doi.replace('DOI:', '')
    doi = doi.replace('doi:', '')

    # Replace / with _ for filename matching
    doi_filename = doi.replace('/', '_')
    return doi, doi_filename

def clean_filename(text, max_length=50):
    """Clean text for use in filename."""
    if pd.isna(text) or not text:
        return "Unknown"

    # Convert to string and strip
    text = str(text).strip()

    # Remove problematic characters
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    text = re.sub(r'[\n\r\t]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0]

    return text.strip()

def extract_first_author(authors):
    """Extract first author's last name."""
    if pd.isna(authors) or not authors:
        return "Unknown"

    authors = str(authors).strip()

    # Split by & or ,
    parts = re.split(r'[&,]', authors)
    if not parts:
        return "Unknown"

    first_author = parts[0].strip()

    # Extract last name (after last space, before any parentheses)
    # Handle formats like "Smith, J." or "Smith J." or "Smith, J.R. (2020)"
    first_author = re.sub(r'\([^)]*\)', '', first_author)  # Remove parentheses
    first_author = first_author.strip()

    # If comma format: "Smith, J." → "Smith"
    if ',' in first_author:
        last_name = first_author.split(',')[0].strip()
    else:
        # Space format: "John Smith" → "Smith"
        parts = first_author.split()
        last_name = parts[-1] if parts else "Unknown"

    return clean_filename(last_name, max_length=20)

def create_new_filename(row):
    """Create Author.Year.Title.pdf filename from metadata."""
    author = extract_first_author(row['authors'])
    year = str(row['year']) if pd.notna(row['year']) else "Unknown"
    title = clean_filename(row['title'], max_length=60)

    # Handle multiple authors
    if '&' in str(row['authors']) or ',' in str(row['authors']):
        author = f"{author}.etal"

    return f"{author}.{year}.{title}.pdf"

def rename_doi_pdfs():
    """Main renaming function."""

    print("Loading shark-references CSV...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df):,} papers")

    # Create DOI lookup dictionary
    print("\nCreating DOI lookup...")
    doi_lookup = {}

    for _, row in df.iterrows():
        doi_norm = normalize_doi(row['doi'])
        if doi_norm:
            doi_clean, doi_filename = doi_norm
            doi_lookup[doi_filename] = row

    print(f"Created lookup for {len(doi_lookup):,} DOIs")

    # Find all DOI-named PDFs
    print("\nScanning for DOI-named PDFs...")
    doi_pdfs = list(pdf_base.glob("*/10.*.pdf"))
    print(f"Found {len(doi_pdfs):,} DOI-named PDFs")

    # Process renames
    print("\nProcessing renames...")
    renamed = 0
    not_found = 0
    errors = 0

    for pdf_path in doi_pdfs:
        # Extract DOI from filename
        doi_filename = pdf_path.stem  # Filename without .pdf

        if doi_filename in doi_lookup:
            # Found metadata
            row = doi_lookup[doi_filename]
            new_name = create_new_filename(row)
            new_path = pdf_path.parent / new_name

            # Check if target already exists
            if new_path.exists():
                # Add suffix to avoid collision
                suffix = 1
                while new_path.exists():
                    new_name_parts = new_name.rsplit('.pdf', 1)
                    new_name = f"{new_name_parts[0]}_v{suffix}.pdf"
                    new_path = pdf_path.parent / new_name
                    suffix += 1

            try:
                pdf_path.rename(new_path)
                renamed += 1
                log_entries.append(f"RENAMED: {pdf_path.name} → {new_name}")

                if renamed % 100 == 0:
                    print(f"  Renamed {renamed:,} PDFs...")

            except Exception as e:
                errors += 1
                log_entries.append(f"ERROR: {pdf_path.name} - {e}")
                print(f"  Error renaming {pdf_path.name}: {e}")
        else:
            not_found += 1
            log_entries.append(f"NOT_FOUND: {pdf_path.name} - DOI not in database")

            if not_found <= 10:  # Show first 10
                print(f"  Metadata not found for: {pdf_path.name}")

    # Write log
    with open(log_file, 'w') as f:
        f.write(f"DOI PDF Renaming Log\n")
        f.write(f"Date: {pd.Timestamp.now()}\n")
        f.write(f"=" * 80 + "\n\n")
        f.write(f"Summary:\n")
        f.write(f"  Total DOI PDFs found: {len(doi_pdfs):,}\n")
        f.write(f"  Successfully renamed: {renamed:,}\n")
        f.write(f"  Metadata not found: {not_found:,}\n")
        f.write(f"  Errors: {errors:,}\n")
        f.write(f"\n" + "=" * 80 + "\n\n")
        f.write("Details:\n")
        f.write("-" * 80 + "\n")
        for entry in log_entries:
            f.write(entry + "\n")

    print("\n" + "=" * 80)
    print("RENAMING COMPLETE")
    print("=" * 80)
    print(f"Total DOI PDFs found: {len(doi_pdfs):,}")
    print(f"Successfully renamed: {renamed:,}")
    print(f"Metadata not found: {not_found:,}")
    print(f"Errors: {errors:,}")
    print(f"\nLog saved to: {log_file}")

    # Show some examples
    if renamed > 0:
        print("\nExample renames:")
        for entry in log_entries[:10]:
            if entry.startswith("RENAMED:"):
                print(f"  {entry}")

if __name__ == "__main__":
    rename_doi_pdfs()
