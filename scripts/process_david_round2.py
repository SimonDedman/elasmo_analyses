"""Process David's round 2 PDFs: extract metadata, check for duplicates, move or delete."""

import os
import re
import shutil
import hashlib
from pathlib import Path

import pandas as pd
from pdfminer.high_level import extract_text


# Paths
DAVID_DIR = Path("/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/database/others_libraries/David/papers_DRG_round2")
SHARK_PAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PARQUET_PATH = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/outputs/literature_review_enriched.parquet")

# Books to skip
BOOKS = {"978-3-031-06153-0.pdf", "978-3-319-40859-0.pdf", "978-3-319-57926-9.pdf"}

# Load parquet DOIs
df = pd.read_parquet(PARQUET_PATH, columns=["literature_id", "doi", "title", "authors", "year"])
# Normalise DOIs for matching
df["doi_norm"] = df["doi"].dropna().str.strip().str.lower()
parquet_dois = set(df["doi_norm"].dropna())


def extract_first_pages(pdf_path: Path, max_pages: int = 3) -> str:
    """Extract text from first few pages of a PDF."""
    try:
        text = extract_text(str(pdf_path), page_numbers=list(range(max_pages)))
        return text
    except Exception as e:
        return f"[EXTRACTION ERROR: {e}]"


def find_doi(text: str) -> str | None:
    """Find DOI in extracted text."""
    # Standard DOI pattern
    patterns = [
        r'(?:doi[:\s]*|https?://doi\.org/)(10\.\d{4,}/[^\s,;}\]\"\']+)',
        r'(10\.\d{4,}/[^\s,;}\]\"\']+)',
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            # Clean trailing punctuation
            doi = m.rstrip(".")
            return doi
    return None


def extract_springer_doi_from_filename(filename: str) -> str | None:
    """Convert Springer filename like s00227-024-04537-9.pdf to a DOI."""
    m = re.match(r's(\d{5})-(\d{3,4})-(\d{5})-(\w+)', filename.replace(".pdf", "").replace(" (1)", ""))
    if m:
        return f"10.1007/s{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}"
    return None


def extract_metadata_from_text(text: str) -> dict:
    """Try to extract author, year, title from first-page text."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    result = {"authors": None, "year": None, "title": None, "first_author_surname": None}

    # Find year
    for line in lines[:30]:
        m = re.search(r'\b(19\d{2}|20[0-2]\d)\b', line)
        if m:
            result["year"] = m.group(1)
            break

    # Title is usually one of the first substantial lines
    for line in lines[:10]:
        if len(line) > 20 and not re.match(r'^(doi|http|www|©|\d{4}|vol|issue|journal|received|accepted|published)', line, re.IGNORECASE):
            result["title"] = line
            break

    # First author - look for author line patterns
    for line in lines[:20]:
        # Look for lines with author-like patterns (names with commas or middot separators)
        if re.search(r'[A-Z][a-z]+.*[A-Z][a-z]+', line) and len(line) < 200:
            # Extract first surname
            m = re.match(r'([A-Z][a-zÀ-ÿ]+)', line)
            if m:
                result["first_author_surname"] = m.group(1)
                result["authors"] = line[:100]
                break

    return result


def search_shark_papers(surname: str, year: str) -> list[Path]:
    """Search SharkPapers for files matching author surname and year."""
    if not surname or not year:
        return []
    year_dir = SHARK_PAPERS / year
    if not year_dir.exists():
        return []

    matches = []
    pattern = surname.lower()
    for f in year_dir.iterdir():
        if f.suffix.lower() == ".pdf" and pattern in f.name.lower():
            matches.append(f)
    return matches


def sanitise_filename(title: str, max_len: int = 60) -> str:
    """Create a filename-safe title fragment."""
    # Remove special chars
    title = re.sub(r'[^\w\s-]', '', title)
    words = title.split()[:8]
    result = " ".join(words)
    return result[:max_len].strip()


def files_are_identical(path1: Path, path2: Path) -> bool:
    """Check if two files have identical content via MD5."""
    def md5(p):
        h = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    return md5(path1) == md5(path2)


def make_standard_name(first_author: str, year: str, title: str, multi_author: bool = True) -> str:
    """Create standard filename: Author.etal.Year.Title fragment.pdf"""
    surname = first_author or "Unknown"
    etal = ".etal" if multi_author else ""
    title_frag = sanitise_filename(title) if title else "untitled"
    return f"{surname}{etal}.{year}.{title_frag}.pdf"


# ============================================================
# Main processing
# ============================================================

results = {"books": [], "deleted": [], "moved": [], "skipped": [], "errors": []}

pdfs = sorted(DAVID_DIR.glob("*.pdf"))
print(f"Found {len(pdfs)} PDFs to process\n")

for pdf_path in pdfs:
    fname = pdf_path.name
    print(f"--- {fname} ---")

    # Skip books
    if fname in BOOKS:
        print(f"  BOOK: skipping (ISBN-based)")
        results["books"].append(fname)
        continue

    # Check for (1) duplicates — if the non-(1) version exists in this folder
    if "(1)" in fname:
        base_name = fname.replace(" (1)", "")
        base_path = DAVID_DIR / base_name
        if base_path.exists():
            if files_are_identical(pdf_path, base_path):
                print(f"  DUPLICATE of {base_name} (identical) → DELETE")
                os.remove(pdf_path)
                results["deleted"].append((fname, "duplicate of same-folder file"))
                continue
            else:
                print(f"  WARNING: {fname} differs from {base_name}")

    # Extract text
    text = extract_first_pages(pdf_path)

    # Try DOI from text first
    doi = find_doi(text)

    # Try DOI from Springer filename pattern
    if not doi:
        doi = extract_springer_doi_from_filename(fname)

    if doi:
        doi_clean = doi.strip().lower()
        print(f"  DOI: {doi}")
    else:
        doi_clean = None
        print(f"  DOI: not found")

    # Extract metadata
    meta = extract_metadata_from_text(text)
    print(f"  Author: {meta['first_author_surname']}, Year: {meta['year']}, Title: {(meta['title'] or '')[:70]}")

    # Check parquet for DOI
    in_parquet = False
    if doi_clean and doi_clean in parquet_dois:
        in_parquet = True
        print(f"  In parquet: YES")
    else:
        print(f"  In parquet: NO")

    # Check SharkPapers for existing copy
    existing = search_shark_papers(meta["first_author_surname"], meta["year"])
    in_library = False
    if existing:
        # Check if any are identical files
        for ex in existing:
            if files_are_identical(pdf_path, ex):
                in_library = True
                print(f"  Already in library: {ex.name}")
                break
        if not in_library and existing:
            print(f"  Similar files in library: {[e.name for e in existing]}")

    if in_library:
        # Already in library → delete
        print(f"  ACTION: DELETE (already in library)")
        os.remove(pdf_path)
        results["deleted"].append((fname, f"already in library as {ex.name}"))
    elif meta["year"]:
        # Move to SharkPapers
        year_dir = SHARK_PAPERS / meta["year"]
        year_dir.mkdir(exist_ok=True)

        new_name = make_standard_name(
            meta["first_author_surname"],
            meta["year"],
            meta["title"]
        )
        dest = year_dir / new_name

        # Avoid overwriting
        if dest.exists():
            # Add DOI suffix to disambiguate
            stem = dest.stem
            dest = year_dir / f"{stem}_2.pdf"

        shutil.move(str(pdf_path), str(dest))
        print(f"  ACTION: MOVE → {dest.relative_to(SHARK_PAPERS)}")
        results["moved"].append((fname, str(dest.relative_to(SHARK_PAPERS)), doi, in_parquet))
    else:
        print(f"  ACTION: SKIP (could not determine year)")
        results["skipped"].append((fname, doi))


# ============================================================
# Summary
# ============================================================

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"\nBooks skipped ({len(results['books'])}):")
for b in results["books"]:
    print(f"  - {b}")

print(f"\nDeleted ({len(results['deleted'])}):")
for fname, reason in results["deleted"]:
    print(f"  - {fname}: {reason}")

print(f"\nMoved to SharkPapers ({len(results['moved'])}):")
for fname, dest, doi, in_parq in results["moved"]:
    status = "IN PARQUET" if in_parq else "NEW — needs adding"
    doi_str = doi or "no DOI found"
    print(f"  - {fname} → {dest}")
    print(f"    DOI: {doi_str} [{status}]")

if results["skipped"]:
    print(f"\nSkipped ({len(results['skipped'])}):")
    for fname, doi in results["skipped"]:
        print(f"  - {fname} (DOI: {doi or 'unknown'})")

if results["errors"]:
    print(f"\nErrors ({len(results['errors'])}):")
    for fname, err in results["errors"]:
        print(f"  - {fname}: {err}")

print(f"\nNew papers needing parquet addition:")
new_count = 0
for fname, dest, doi, in_parq in results["moved"]:
    if not in_parq:
        new_count += 1
        print(f"  - {doi or 'NO DOI'}: {dest}")
print(f"  Total: {new_count}")
