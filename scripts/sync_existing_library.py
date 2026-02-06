#!/usr/bin/env python3
"""
Sync existing paper library with SharkPapers and database.
Optimized version with year+author indexing for faster matching.
"""

import os
import re
import shutil
import sqlite3
from pathlib import Path
from difflib import SequenceMatcher
from typing import Optional, Tuple, Dict, List
import unicodedata
from collections import defaultdict

# Paths
LIBRARY_PATH = Path("/home/simon/Dropbox/Galway/Papers/")
SHARKPAPERS_PATH = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/")
DB_PATH = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/database/download_tracker.db")

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text.lower())
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_first_author_surname(authors: str) -> str:
    """Extract first author's surname."""
    if not authors:
        return ""
    first_author = authors.split(',')[0].strip()
    parts = first_author.split()
    if parts:
        # Get last word (surname), handle "de la Cruz" etc
        return normalize_text(parts[-1])
    return ""

def extract_info_from_filename(filename: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Extract author, year, title from filename."""
    name = Path(filename).stem

    # Try pattern: Author.etal.YYYY.Title or Author.YYYY.Title
    patterns = [
        r'^([A-Za-z\-]+)\.etal\.(\d{4})\.(.+)$',
        r'^([A-Za-z\-]+)\.(\d{4})\.(.+)$',
        r'^([A-Za-z\-]+)_etal_(\d{4})_(.+)$',
        r'^([A-Za-z\-]+)_(\d{4})_(.+)$',
        r'^([A-Za-z\-]+)\s+et\s+al\.?\s*(\d{4})(.*)$',
    ]

    for pattern in patterns:
        match = re.match(pattern, name, re.IGNORECASE)
        if match:
            author = normalize_text(match.group(1))
            year = int(match.group(2))
            title = match.group(3).replace('_', ' ').replace('.', ' ')
            return author, year, title

    # Try to find year anywhere in filename
    year_match = re.search(r'[^\d](\d{4})[^\d]', name)
    if not year_match:
        year_match = re.search(r'^(\d{4})[^\d]', name)
    if not year_match:
        year_match = re.search(r'[^\d](\d{4})$', name)
    year = int(year_match.group(1)) if year_match else None

    # Try to get first word as author
    words = re.split(r'[._\s\-]+', name)
    author = normalize_text(words[0]) if words else None

    return author, year, name

def text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    if not norm1 or not norm2:
        return 0.0
    return SequenceMatcher(None, norm1, norm2).ratio()

def build_paper_index(papers: list) -> Dict[str, List[tuple]]:
    """Build index by year_author for fast lookup."""
    index = defaultdict(list)
    for paper in papers:
        paper_id, doi, db_title, db_authors, db_year = paper
        author_surname = get_first_author_surname(db_authors)

        # Index by year_author
        if db_year and author_surname:
            key = f"{db_year}_{author_surname}"
            index[key].append(paper)

        # Also index by just year (for fallback)
        if db_year:
            index[f"year_{db_year}"].append(paper)

        # Index by just author (for fallback)
        if author_surname:
            index[f"author_{author_surname}"].append(paper)

    return index

def match_pdf_to_paper(pdf_path: Path, index: Dict[str, List[tuple]]) -> Optional[Tuple[int, float, str]]:
    """Try to match a PDF to a paper using indexed lookup."""
    author, year, title_hint = extract_info_from_filename(pdf_path.name)

    candidates = []

    # First try year + author exact match
    if year and author:
        key = f"{year}_{author}"
        candidates = index.get(key, [])

    # If no candidates, try just year
    if not candidates and year:
        candidates = index.get(f"year_{year}", [])

    # If still no candidates, try just author
    if not candidates and author:
        candidates = index.get(f"author_{author}", [])

    if not candidates:
        return None

    best_match = None
    best_score = 0.0
    best_title = ""

    for paper in candidates:
        paper_id, doi, db_title, db_authors, db_year = paper
        score = 0.0

        # Year match gives bonus
        if year and db_year and year == db_year:
            score += 0.2

        # Author match
        db_author = get_first_author_surname(db_authors)
        if author and db_author:
            if author == db_author:
                score += 0.3
            elif author in db_author or db_author in author:
                score += 0.15

        # Title similarity
        if title_hint and db_title:
            title_sim = text_similarity(title_hint, db_title)
            score += title_sim * 0.5

        if score > best_score:
            best_score = score
            best_match = paper_id
            best_title = db_title

    if best_score >= 0.45:
        return best_match, best_score, best_title
    return None

def generate_filename(title: str, authors: str, year: int) -> str:
    """Generate proper filename from paper info."""
    if authors:
        first_author = authors.split(',')[0].strip()
        parts = first_author.split()
        if parts:
            author_name = parts[-1].replace(' ', '')
        else:
            author_name = "Unknown"
    else:
        author_name = "Unknown"

    # Clean title for filename
    title_words = re.sub(r'[^\w\s]', '', title or "Untitled").split()[:8]
    title_part = ' '.join(title_words)

    # Determine if etal needed
    has_multiple = authors and (',' in authors or '&' in authors or ' and ' in authors.lower())
    etal = ".etal" if has_multiple else ""

    year_str = str(int(year)) if year else "unknown_year"
    return f"{author_name}{etal}.{year_str}.{title_part}.pdf"

def main():
    print("=" * 60)
    print("SYNCING EXISTING LIBRARY WITH SHARKPAPERS")
    print("=" * 60)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get unavailable papers
    cursor.execute("""
        SELECT p.id, p.doi, p.title, p.authors, p.year
        FROM papers p
        JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.status = 'unavailable'
    """)
    unavailable = cursor.fetchall()
    print(f"\nFound {len(unavailable)} unavailable papers in database")

    # Build index
    print("Building search index...")
    index = build_paper_index(unavailable)
    print(f"Index built with {len(index)} keys")

    # Get all library PDFs
    library_pdfs = list(LIBRARY_PATH.rglob("*.pdf"))
    print(f"Found {len(library_pdfs)} PDFs in existing library")

    # Track matches
    matched_ids = set()
    results = []

    print("\nMatching papers...")
    for i, pdf_path in enumerate(library_pdfs):
        if i % 500 == 0:
            print(f"  Processing {i}/{len(library_pdfs)}... ({len(results)} matched)")

        result = match_pdf_to_paper(pdf_path, index)
        if result:
            paper_id, score, db_title = result
            if paper_id not in matched_ids:
                matched_ids.add(paper_id)
                results.append((pdf_path, paper_id, score, db_title))

    print(f"\nFound {len(results)} matches")

    # Copy and mark
    print("\nCopying papers and updating database...")
    copied = 0
    for pdf_path, paper_id, score, db_title in results:
        # Get paper info
        cursor.execute("SELECT title, authors, year FROM papers WHERE id = ?", (paper_id,))
        row = cursor.fetchone()
        if not row:
            continue

        title, authors, year = row
        new_filename = generate_filename(title, authors, year)

        year_str = str(int(year)) if year else "unknown_year"
        year_folder = SHARKPAPERS_PATH / year_str
        year_folder.mkdir(parents=True, exist_ok=True)

        dest_path = year_folder / new_filename

        # Check if already exists
        if not dest_path.exists():
            shutil.copy2(pdf_path, dest_path)
            print(f"  [{score:.2f}] Copied: {new_filename}")
            copied += 1
        else:
            print(f"  [{score:.2f}] Already exists: {new_filename}")

        # Update database
        cursor.execute("""
            UPDATE download_status
            SET status = 'downloaded',
                download_date = datetime('now'),
                source = 'existing_library',
                notes = ?
            WHERE paper_id = ?
        """, (str(pdf_path), paper_id))

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Library PDFs scanned:   {len(library_pdfs)}")
    print(f"Matched to database:    {len(results)}")
    print(f"New copies made:        {copied}")
    print(f"Already existed:        {len(results) - copied}")

if __name__ == "__main__":
    main()
