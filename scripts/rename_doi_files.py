#!/usr/bin/env python3
"""
Rename PDF files from DOI-format (literature_id.0_DOI.pdf) to
Author.etal.Year.Title.pdf format using the literature database.
"""

import os
import re
import unicodedata
import pandas as pd
from pathlib import Path

# Paths
PDF_BASE = "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"
DB_PATH = "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/outputs/literature_review.parquet"


def clean_author_name(author_str):
    """Extract first author's surname from the authors field."""
    if pd.isna(author_str) or not author_str:
        return "Unknown"

    # Format is like: "Surname, F. & Surname2, G. (Year)"
    # Extract first author's surname
    author_str = str(author_str)

    # Remove the year part at the end
    author_str = re.sub(r'\s*\(\d{4}\)\s*$', '', author_str)

    # Get first author (before first &)
    first_author = author_str.split(' & ')[0].strip()

    # Get surname (before the comma)
    surname = first_author.split(',')[0].strip()

    # Clean special characters but keep accents
    # Remove problematic characters
    surname = re.sub(r'[<>:"/\\|?*]', '', surname)
    surname = surname.replace('ñ', 'n').replace('Ñ', 'N')

    # Handle accented characters - normalize to ASCII-friendly
    # Keep the accented version but clean any really weird ones
    cleaned = ''.join(c for c in surname if c.isalnum() or c in ' -.')

    return cleaned if cleaned else "Unknown"


def count_authors(author_str):
    """Count number of authors."""
    if pd.isna(author_str) or not author_str:
        return 0
    author_str = str(author_str)
    # Remove year
    author_str = re.sub(r'\s*\(\d{4}\)\s*$', '', author_str)
    return len(author_str.split(' & '))


def clean_title(title_str, max_words=8):
    """Clean and truncate title for filename."""
    if pd.isna(title_str) or not title_str:
        return "Untitled"

    title_str = str(title_str)

    # Remove problematic characters for filenames
    title_str = re.sub(r'[<>:"/\\|?*]', '', title_str)

    # Replace special chars
    title_str = title_str.replace('–', '-').replace('—', '-')
    title_str = title_str.replace('"', '').replace('"', '').replace('"', '')
    title_str = title_str.replace("'", '').replace("'", '').replace("'", '')

    # Take first N words
    words = title_str.split()
    truncated = ' '.join(words[:max_words])

    # If we truncated, ensure we don't end mid-word
    if len(words) > max_words:
        truncated = truncated.rstrip('.,;:')

    return truncated


def generate_new_filename(row):
    """Generate new filename from database row."""
    surname = clean_author_name(row['authors'])
    num_authors = count_authors(row['authors'])
    year = int(row['year']) if pd.notna(row['year']) else 0
    title = clean_title(row['title'])

    # Format: Author.etal.Year.Title.pdf or Author.Year.Title.pdf
    if num_authors > 1:
        new_name = f"{surname}.etal.{year}.{title}.pdf"
    else:
        new_name = f"{surname}.{year}.{title}.pdf"

    return new_name


def find_doi_format_files(base_path):
    """Find all files with DOI-format naming (literature_id.0_DOI.pdf)."""
    doi_files = []
    pattern = re.compile(r'^(\d+\.0)_10\.')

    for root, dirs, files in os.walk(base_path):
        for f in files:
            if f.endswith('.pdf') and pattern.match(f):
                doi_files.append(os.path.join(root, f))

    return doi_files


def main():
    print("Loading database...")
    df = pd.read_parquet(DB_PATH)
    print(f"Database has {len(df)} entries")

    print("\nFinding DOI-format files...")
    doi_files = find_doi_format_files(PDF_BASE)
    print(f"Found {len(doi_files)} DOI-format files to rename")

    rename_log = []
    errors = []

    for filepath in doi_files:
        filename = os.path.basename(filepath)
        dirname = os.path.dirname(filepath)

        # Extract literature_id from filename
        lit_id = filename.split('_')[0]  # e.g., "27716.0"

        # Look up in database
        row = df[df['literature_id'] == lit_id]

        if len(row) == 0:
            errors.append(f"NOT FOUND: {filename} (lit_id={lit_id})")
            continue

        row = row.iloc[0]
        new_filename = generate_new_filename(row)
        new_filepath = os.path.join(dirname, new_filename)

        # Check if target already exists
        if os.path.exists(new_filepath):
            # Add lit_id suffix to avoid collision
            base, ext = os.path.splitext(new_filename)
            new_filename = f"{base}_{lit_id}{ext}"
            new_filepath = os.path.join(dirname, new_filename)

        try:
            os.rename(filepath, new_filepath)
            rename_log.append({
                'old_name': filename,
                'new_name': new_filename,
                'lit_id': lit_id,
                'title': row['title'][:50] if pd.notna(row['title']) else 'NA'
            })
            print(f"Renamed: {filename}")
            print(f"     -> {new_filename}")
        except Exception as e:
            errors.append(f"RENAME ERROR: {filename} -> {str(e)}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Successfully renamed: {len(rename_log)} files")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")

    # Return log for further processing
    return rename_log, errors


if __name__ == "__main__":
    rename_log, errors = main()
