#!/usr/bin/env python3
"""
Ingest David Ruiz Garcia's round 2 PDFs into the SharkPapers library.

For each PDF:
  1. Extract DOI and first-page text using pdfminer.six
  2. Search SharkPapers for existing file by author surname + year
  3. Check DOI against the parquet database
  4. If already in library → DELETE from David's folder
  5. If new → extract metadata, rename, MOVE to SharkPapers/{year}/

Usage:
    python scripts/ingest_david_round2.py
"""

import os
import re
import shutil
import unicodedata
from pathlib import Path

import pandas as pd
from pdfminer.high_level import extract_text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOURCE_DIR = Path(
    "/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
    "/database/others_libraries/David/papers_DRG_round2"
)
SHARK_PAPERS = Path(
    "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"
)
PARQUET_PATH = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
    "/outputs/literature_review_enriched.parquet"
)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def normalise_doi(doi: str) -> str:
    """Normalise DOI: lowercase, strip URL prefix, trailing punctuation."""
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    doi = doi.rstrip('.,; ')
    return doi


def strip_accents(s: str) -> str:
    """Remove diacritics for fuzzy matching."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def clean_for_filename(text: str, max_len: int = 60) -> str:
    """Sanitise text for use in a filename."""
    if not text:
        return "Unknown"
    text = str(text).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', text)
    text = re.sub(r'[\n\r\t]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(' ', 1)[0]
    return text.strip() or "Unknown"


# ---------------------------------------------------------------------------
# PDF text and DOI extraction (pdfminer.six)
# ---------------------------------------------------------------------------

def extract_first_pages_text(pdf_path: Path, max_pages: int = 2) -> str:
    """Extract text from the first page(s) of a PDF using pdfminer.six."""
    try:
        text = extract_text(str(pdf_path), maxpages=max_pages)
        return text or ""
    except Exception:
        return ""


def extract_doi_from_text(text: str) -> str:
    """Search text for a DOI. Returns normalised DOI or empty string."""
    if not text:
        return ""

    # Strip everything after references header to avoid matching cited DOIs
    refs_re = re.compile(
        r'^\s*(REFERENCES|References|Bibliography|BIBLIOGRAPHY|'
        r'LITERATURE\s+CITED|Literature\s+Cited|WORKS\s+CITED)\s*$',
        re.MULTILINE
    )
    m = refs_re.search(text)
    if m:
        text = text[:m.start()]

    # DOI: or doi: prefix
    m = re.search(r'(?:doi|DOI)[\s:]*\s*(10\.\d{4,}/[^\s\]>)]+)', text)
    if m:
        return normalise_doi(m.group(1))

    # https://doi.org/ URL
    m = re.search(r'https?://(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s\]>)]+)', text)
    if m:
        return normalise_doi(m.group(1))

    # Bare DOI on first page (risky but first-page context is usually safe)
    m = re.search(r'(10\.\d{4,}/[^\s\]>)]{3,})', text)
    if m:
        return normalise_doi(m.group(1))

    return ""


# ---------------------------------------------------------------------------
# Metadata extraction from PDF text
# ---------------------------------------------------------------------------

def extract_year_from_text(text: str) -> str:
    """Extract publication year from first-page text."""
    if not text:
        return ""

    # Look for common date patterns: "(2024)", "2025", "Received ... 2024"
    # Prefer years in the first ~2000 chars (header area)
    header = text[:2000]

    # Pattern: copyright or (c) followed by year
    m = re.search(r'(?:©|\(c\)|Copyright)\s*(\d{4})', header, re.IGNORECASE)
    if m and 1950 <= int(m.group(1)) <= 2026:
        return m.group(1)

    # Pattern: year in parentheses near beginning
    matches = re.findall(r'\((\d{4})\)', header)
    for yr in matches:
        if 1950 <= int(yr) <= 2026:
            return yr

    # Pattern: "Published" or "Accepted" or "Available online" date
    m = re.search(
        r'(?:Published|Accepted|Available\s+online|Received)[:\s]*\d{1,2}\s+\w+\s+(\d{4})',
        header, re.IGNORECASE
    )
    if m and 1950 <= int(m.group(1)) <= 2026:
        return m.group(1)

    # Any 4-digit year in header
    matches = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', header)
    if matches:
        # Take the most recent plausible year
        years = [int(y) for y in matches if 1950 <= int(y) <= 2026]
        if years:
            return str(max(years))

    return ""


def extract_first_author_from_text(text: str) -> str:
    """Extract first author surname from first-page text.

    Looks for common author-line patterns near the top of the paper.
    """
    if not text:
        return ""

    # Use first ~1500 chars (title + author block area)
    header = text[:1500]
    lines = [ln.strip() for ln in header.split('\n') if ln.strip()]

    # Skip very short headers, look for author-like lines
    for line in lines[1:15]:  # skip first line (usually title)
        # Skip lines that are clearly not author names
        if len(line) < 3 or len(line) > 500:
            continue
        if re.match(r'^(Abstract|ABSTRACT|Keywords|Introduction|INTRODUCTION)', line):
            break

        # Pattern: "Surname, Initial." or "Initial. Surname" with possible multiple authors
        # Try to find a line with capitalised words that looks like names
        # Common: "John Smith, Jane Doe, ..." or "Smith J., Doe J., ..."
        author_match = re.match(
            r'^([A-ZÀ-ÿ\u0100-\u017F][a-zà-ÿ\u0100-\u017F]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)*)',
            line
        )
        if author_match:
            candidate = author_match.group(1).split()[0]
            # Exclude common non-author words
            if candidate.lower() not in {
                'the', 'this', 'and', 'for', 'with', 'from', 'that', 'are',
                'was', 'were', 'has', 'have', 'been', 'will', 'can', 'may',
                'not', 'but', 'its', 'all', 'any', 'our', 'new', 'one',
                'two', 'three', 'journal', 'marine', 'fish', 'ocean',
                'research', 'article', 'original', 'review', 'letters',
                'short', 'communication', 'note', 'volume', 'issue',
                'received', 'accepted', 'published', 'available', 'online',
                'contents', 'list', 'elsevier', 'springer', 'wiley',
                'taylor', 'francis', 'science', 'direct', 'biology',
                'ecology', 'conservation', 'fisheries', 'environmental',
                'aquatic', 'deep', 'sea', 'global', 'change', 'regional',
                'studies', 'international', 'european', 'american',
                'progress', 'series', 'bulletin', 'proceedings', 'royal',
                'society', 'transactions', 'comparative', 'biochemistry',
                'physiology', 'molecular', 'general', 'applied',
            }:
                # Validate: at least 2 chars, starts with uppercase
                if len(candidate) >= 2 and candidate[0].isupper():
                    return candidate

    return ""


def extract_title_fragment_from_text(text: str) -> str:
    """Extract a short title fragment from first-page text."""
    if not text:
        return ""

    lines = [ln.strip() for ln in text[:2000].split('\n') if ln.strip()]

    # The title is typically one of the first substantial lines
    # Skip very short lines (journal headers, page numbers)
    title_candidates = []
    for line in lines[:10]:
        # Skip lines that are clearly not titles
        if len(line) < 10:
            continue
        if re.match(r'^\d+$', line):  # pure numbers
            continue
        if re.match(r'^(http|www\.|doi:|DOI:)', line):
            continue
        if re.match(r'^(Volume|Vol\.|Issue|No\.|Page|pp\.|ISSN)', line, re.IGNORECASE):
            continue
        title_candidates.append(line)

    if not title_candidates:
        return "Unknown"

    # Take the first substantial candidate as the title
    title = title_candidates[0]

    # Clean and shorten
    title = re.sub(r'\s+', ' ', title).strip()
    # Remove leading "ORIGINAL ARTICLE" or "RESEARCH PAPER" etc.
    title = re.sub(
        r'^(ORIGINAL\s+)?(?:ARTICLE|RESEARCH\s+(?:PAPER|ARTICLE|LETTER)|'
        r'SHORT\s+COMMUNICATION|REVIEW|NOTE|LETTER)\s*[:\-–]?\s*',
        '', title, flags=re.IGNORECASE
    ).strip()

    return clean_for_filename(title, max_len=60)


def count_authors_in_text(text: str) -> bool:
    """Heuristic: are there multiple authors? Look for 'and', '&', commas between names."""
    if not text:
        return False
    header = text[:1500]
    # Multiple authors indicated by &, "and" between names, or many commas
    # in the author block
    lines = [ln.strip() for ln in header.split('\n') if ln.strip()]
    for line in lines[1:10]:
        if re.search(r'[A-Z][a-z]+.*[,&].*[A-Z][a-z]+', line):
            return True
        if re.search(r'\band\b', line) and re.search(r'[A-Z][a-z]{2,}', line):
            return True
    return False


# ---------------------------------------------------------------------------
# SharkPapers library search
# ---------------------------------------------------------------------------

def build_library_index(shark_papers_dir: Path) -> dict[str, list[Path]]:
    """Build an index of existing PDFs: key = 'surname_year' → list of paths.

    Parses filenames like 'Author.etal.Year.Title.pdf' and 'Author.Year.Title.pdf'.
    """
    index: dict[str, list[Path]] = {}
    for year_dir in shark_papers_dir.iterdir():
        if not year_dir.is_dir():
            continue
        year_str = year_dir.name
        if not re.match(r'^\d{4}$', year_str):
            continue
        for pdf in year_dir.glob("*.pdf"):
            # Parse: Author.etal.Year.Title.pdf or Author.Year.Title.pdf
            stem = pdf.stem
            m = re.match(r'^([A-Za-zÀ-ÿ\u0100-\u017F\-]+)\.(?:etal\.)?(\d{4})\.', stem)
            if m:
                surname = strip_accents(m.group(1)).lower()
                yr = m.group(2)
                key = f"{surname}_{yr}"
                index.setdefault(key, []).append(pdf)
            # Also handle numeric-prefix format like "29003_Trujillo-Córdova_2020.pdf"
            m2 = re.match(r'^\d+_([A-Za-zÀ-ÿ\u0100-\u017F\-]+)_(\d{4})', stem)
            if m2:
                surname = strip_accents(m2.group(1)).lower()
                yr = m2.group(2)
                key = f"{surname}_{yr}"
                index.setdefault(key, []).append(pdf)
    return index


# ---------------------------------------------------------------------------
# Parquet database loading
# ---------------------------------------------------------------------------

def load_parquet_db(path: Path) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    """Load parquet and build DOI lookup and author+year lookup.

    Returns: (doi_lookup, author_year_lookup)
    """
    df = pd.read_parquet(path, columns=['literature_id', 'doi', 'authors', 'title', 'year'])

    doi_lookup: dict[str, dict] = {}
    author_year_lookup: dict[str, list[dict]] = {}

    for _, row in df.iterrows():
        rec = {
            'literature_id': str(row['literature_id']),
            'doi': str(row['doi']) if pd.notna(row['doi']) else '',
            'authors': str(row['authors']) if pd.notna(row['authors']) else '',
            'title': str(row['title']) if pd.notna(row['title']) else '',
            'year': row['year'],
        }

        # DOI index
        nd = normalise_doi(rec['doi'])
        if nd:
            doi_lookup[nd] = rec

        # Author+year index
        authors_str = rec['authors']
        if authors_str:
            # Extract first author surname: "Surname, I. & ..." or "Surname, I. (Year)"
            first = re.split(r'\s*&\s*', authors_str)[0].strip()
            first = re.sub(r'\(\d{4}\)', '', first).strip()
            if ',' in first:
                surname = first.split(',')[0].strip()
            else:
                parts = first.split()
                surname = parts[-1] if parts else ""

            surname_clean = strip_accents(surname).lower()
            try:
                year_str = str(int(float(rec['year'])))
            except (ValueError, TypeError):
                continue
            key = f"{surname_clean}_{year_str}"
            author_year_lookup.setdefault(key, []).append(rec)

    return doi_lookup, author_year_lookup


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_pdfs() -> None:
    """Process all PDFs in David's round 2 folder."""
    # Collect PDFs
    pdfs = sorted(SOURCE_DIR.glob("*.pdf")) + sorted(SOURCE_DIR.glob("*.PDF"))
    # Deduplicate (case-insensitive)
    seen_lower: set[str] = set()
    unique_pdfs: list[Path] = []
    for p in pdfs:
        low = p.name.lower()
        if low not in seen_lower:
            seen_lower.add(low)
            unique_pdfs.append(p)
    pdfs = unique_pdfs

    print(f"Found {len(pdfs)} PDFs in David's round 2 folder")
    print()

    # Load parquet database
    print("Loading parquet database...")
    doi_lookup, author_year_lookup = load_parquet_db(PARQUET_PATH)
    print(f"  {len(doi_lookup):,} DOIs indexed")
    print(f"  {len(author_year_lookup):,} author+year keys indexed")
    print()

    # Build SharkPapers library index
    print("Building SharkPapers library index...")
    lib_index = build_library_index(SHARK_PAPERS)
    print(f"  {sum(len(v) for v in lib_index.values()):,} files indexed across {len(lib_index):,} author+year keys")
    print()

    # Track results
    already_existed: list[tuple[str, str]] = []  # (original_name, match_info)
    newly_moved: list[tuple[str, str]] = []       # (original_name, new_path)
    failed: list[tuple[str, str]] = []            # (original_name, reason)

    for i, pdf_path in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {pdf_path.name}")

        # Step 1: Extract text and DOI
        try:
            text = extract_first_pages_text(pdf_path, max_pages=2)
        except Exception as e:
            text = ""
            print(f"  WARNING: Could not extract text: {e}")

        doi = extract_doi_from_text(text)
        if doi:
            print(f"  DOI: {doi}")

        # Step 2: Extract metadata from text
        year = extract_year_from_text(text)
        author = extract_first_author_from_text(text)

        # Also try to get info from the filename
        fn_year = ""
        fn_author = ""
        stem = pdf_path.stem

        # Filename patterns
        # Numeric prefix: "30216_Azofeifa_Solano_J_C_..."
        m = re.match(r'^\d+_([A-Za-zÀ-ÿ\u0100-\u017F]+)(?:_[A-Za-z])*.*?_(\d{4})_', stem)
        if m:
            fn_author = m.group(1)
            fn_year = m.group(2)
        # "1999HeistandGold--FisheryBulletin" pattern
        if not fn_year:
            m = re.match(r'^(\d{4})([A-Z][a-z]+)', stem)
            if m:
                fn_year = m.group(1)
                fn_author = m.group(2)
        # "2004 Listrocephalos n gen" pattern
        if not fn_year:
            m = re.match(r'^(\d{4})\s+(.+)', stem)
            if m:
                fn_year = m.group(1)
        # "Fisheries Oceanography - 2003 - Campana - ..."
        if not fn_year:
            m = re.search(r'[-–]\s*(\d{4})\s*[-–]\s*([A-Za-z]+)', stem)
            if m:
                fn_year = m.group(1)
                fn_author = m.group(2)
        # Descriptive names: try to find year anywhere
        if not fn_year:
            m = re.search(r'\b(19\d{2}|20[0-2]\d)\b', stem)
            if m:
                fn_year = m.group(1)

        # Use filename info as fallback
        if not year and fn_year:
            year = fn_year
        if not author and fn_author:
            author = fn_author

        if author:
            author_clean = strip_accents(author).lower()
        else:
            author_clean = ""

        # Step 3: Check if already in SharkPapers library (by author+year filename match)
        found_in_library = False
        library_match_info = ""

        if author_clean and year:
            key = f"{author_clean}_{year}"
            lib_matches = lib_index.get(key, [])
            if lib_matches:
                found_in_library = True
                library_match_info = f"Library match ({key}): {lib_matches[0].name}"
                print(f"  ALREADY IN LIBRARY: {library_match_info}")

        # Step 4: Check DOI against parquet database
        found_in_parquet = False
        parquet_rec = None

        if doi:
            nd = normalise_doi(doi)
            if nd in doi_lookup:
                found_in_parquet = True
                parquet_rec = doi_lookup[nd]
                print(f"  DOI found in parquet: lit_id={parquet_rec['literature_id']}")

                # If we found it in parquet but not library, also check library
                # using parquet metadata (more reliable)
                if not found_in_library and parquet_rec:
                    p_authors = parquet_rec['authors']
                    p_first = re.split(r'\s*&\s*', p_authors)[0].strip()
                    p_first = re.sub(r'\(\d{4}\)', '', p_first).strip()
                    if ',' in p_first:
                        p_surname = p_first.split(',')[0].strip()
                    else:
                        parts = p_first.split()
                        p_surname = parts[-1] if parts else ""
                    p_surname_clean = strip_accents(p_surname).lower()
                    try:
                        p_year = str(int(float(parquet_rec['year'])))
                    except (ValueError, TypeError):
                        p_year = ""

                    if p_surname_clean and p_year:
                        key2 = f"{p_surname_clean}_{p_year}"
                        lib_matches2 = lib_index.get(key2, [])
                        if lib_matches2:
                            found_in_library = True
                            library_match_info = f"Library match via parquet ({key2}): {lib_matches2[0].name}"
                            print(f"  ALREADY IN LIBRARY (via parquet): {library_match_info}")

        # Decision: already exists or new?
        if found_in_library:
            # DELETE from David's folder
            try:
                os.remove(pdf_path)
                already_existed.append((pdf_path.name, library_match_info))
                print(f"  -> DELETED from David's folder (already in library)")
            except Exception as e:
                failed.append((pdf_path.name, f"Could not delete: {e}"))
                print(f"  -> ERROR deleting: {e}")
        else:
            # NEW paper: build filename and MOVE to SharkPapers
            # Prefer parquet metadata if available
            if parquet_rec:
                # Use parquet metadata for naming
                p_authors = parquet_rec['authors']
                p_first = re.split(r'\s*&\s*', p_authors)[0].strip()
                p_first = re.sub(r'\(\d{4}\)', '', p_first).strip()
                if ',' in p_first:
                    final_surname = p_first.split(',')[0].strip()
                else:
                    parts = p_first.split()
                    final_surname = parts[-1] if parts else "Unknown"

                multi = '&' in p_authors
                final_title = clean_for_filename(parquet_rec['title'], max_len=60)
                try:
                    final_year = str(int(float(parquet_rec['year'])))
                except (ValueError, TypeError):
                    final_year = year or "Unknown"
            else:
                # Use text-extracted metadata
                final_surname = author if author else "Unknown"
                multi = count_authors_in_text(text)
                final_title = extract_title_fragment_from_text(text)
                final_year = year or "Unknown"

            # Clean surname for filename
            final_surname = clean_for_filename(final_surname, max_len=25)

            if not final_year or final_year == "Unknown":
                failed.append((pdf_path.name, "Could not determine year"))
                print(f"  -> FAILED: Could not determine year")
                continue

            if final_surname == "Unknown" and final_title == "Unknown":
                failed.append((pdf_path.name, "Could not extract any metadata"))
                print(f"  -> FAILED: No extractable metadata")
                continue

            # Build filename
            etal = ".etal" if multi else ""
            new_name = f"{final_surname}{etal}.{final_year}.{final_title}.pdf"

            # Target directory
            year_dir = SHARK_PAPERS / final_year
            year_dir.mkdir(parents=True, exist_ok=True)
            target = year_dir / new_name

            # Avoid overwrites
            if target.exists():
                # Already there with same name — treat as duplicate
                try:
                    os.remove(pdf_path)
                    already_existed.append((pdf_path.name, f"Exact filename match: {new_name}"))
                    print(f"  -> DELETED (exact filename already exists: {new_name})")
                except Exception as e:
                    failed.append((pdf_path.name, f"Could not delete duplicate: {e}"))
                continue

            # MOVE the file
            try:
                shutil.move(str(pdf_path), str(target))
                newly_moved.append((pdf_path.name, f"{final_year}/{new_name}"))
                print(f"  -> MOVED to {final_year}/{new_name}")
            except Exception as e:
                failed.append((pdf_path.name, f"Could not move: {e}"))
                print(f"  -> ERROR moving: {e}")

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total PDFs processed:    {len(pdfs)}")
    print(f"  Already existed (deleted): {len(already_existed)}")
    print(f"  New (moved to library):    {len(newly_moved)}")
    print(f"  Failed:                    {len(failed)}")
    print()

    if already_existed:
        print("--- Already existed (deleted from David's folder) ---")
        for orig, info in already_existed:
            print(f"  {orig}")
            print(f"    -> {info}")
        print()

    if newly_moved:
        print("--- New papers (moved to SharkPapers) ---")
        for orig, new_path in newly_moved:
            print(f"  {orig}")
            print(f"    -> {new_path}")
        print()

    if failed:
        print("--- Failed (still in David's folder) ---")
        for orig, reason in failed:
            print(f"  {orig}")
            print(f"    Reason: {reason}")
        print()

    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    process_pdfs()
