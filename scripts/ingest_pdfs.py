#!/usr/bin/env python3
"""
Ingest PDFs from any source into the SharkPapers library.

Usage:
    python scripts/ingest_pdfs.py /path/to/pdfs/           # ingest a directory
    python scripts/ingest_pdfs.py file1.pdf file2.pdf       # ingest specific files
    python scripts/ingest_pdfs.py --check /path/to/pdfs/    # dry-run: check matches only
    python scripts/ingest_pdfs.py                           # (no args) shows usage

Matching strategy (in order):
  1. Extract DOI from full PDF text via pdftotext (not just first page)
  2. Match author surname + year from filename
  3. Fuzzy title matching from filename (if enough words)

Copies PDFs to SharkPapers/{year}/ with standardised naming.
No destructive operations — copies only, originals stay in place.
"""

import csv
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PROJECT = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
VIZ_DATA = PROJECT / "outputs/viz_data.csv"
LOG_DIR = PROJECT / "logs"
LOG_FILE = LOG_DIR / "ingest_pdfs_log.txt"

# Tracking files
PAPERS_DATA_JSON = PROJECT / "docs/papers_data.json"
DOWNLOAD_TRACKER_DB = PROJECT / "database/download_tracker.db"
DOWNLOAD_QUEUE_DB = PROJECT / "outputs/download_queue.db"

# OCR fallback for image-only PDFs
OCR_CACHE = PROJECT / "outputs" / ".ocr_cache"
OCR_ENABLED = True  # set by --no-ocr CLI flag
DEDUP_CHECK_ENABLED = True  # set by --no-dedup-check CLI flag

try:
    import sys as _sys
    _sys.path.insert(0, str(PROJECT / "scripts"))
    from dedup.ingest_hook import check_new_pdf as _dedup_check_new_pdf
    _DEDUP_OK = True
except Exception as _e:
    _DEDUP_OK = False
    _DEDUP_IMPORT_ERR = str(_e)
OCR_MIN_ALPHA = 50  # page 1 alphabetic-char threshold below which we OCR
OCR_LANGS = "eng+fra+deu+spa+por+ita"  # Latin-script European packs installed 2026-07-21; ingest has no per-file lang detection, so these cover the bulk of the corpus. CJK/Cyrillic omitted here to avoid slowing every OCR call.


# ---------------------------------------------------------------------------
# Utility functions (from ingest_jurgen_pdfs.py pattern)
# ---------------------------------------------------------------------------

def clean_for_filename(text: str, max_len: int = 50) -> str:
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


def extract_first_author(authors: str) -> str:
    """Extract first author's surname from author string."""
    if not authors:
        return "Unknown"
    authors = str(authors).strip()
    first = re.split(r'\s*&\s*', authors)[0].strip()
    first = re.sub(r'\(\d{4}\)', '', first).strip()
    if ',' in first:
        return clean_for_filename(first.split(',')[0], max_len=20)
    parts = first.split()
    return clean_for_filename(parts[-1] if parts else "Unknown", max_len=20)


def has_multiple_authors(authors: str) -> bool:
    """Check if there are multiple authors."""
    if not authors:
        return False
    return '&' in str(authors)


def build_filename(row: dict) -> str:
    """Build filename in library convention: Author.etal.Year.Title.pdf"""
    author = extract_first_author(row["authors"])
    year_val = row.get("year", "")
    try:
        year_int = int(float(year_val))
        year_str = str(year_int)
    except (ValueError, TypeError):
        year_str = "Unknown"
    title = clean_for_filename(row["title"], max_len=60)

    if has_multiple_authors(row["authors"]):
        return f"{author}.etal.{year_str}.{title}.pdf"
    else:
        return f"{author}.{year_str}.{title}.pdf"


def normalise_doi(doi: str) -> str:
    """Normalise DOI for matching: lowercase, strip whitespace, remove URL prefix."""
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    # Remove trailing punctuation
    doi = doi.rstrip('.')
    return doi


def strip_accents(s: str) -> str:
    """Remove accents for fuzzy matching."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


_REFS_HEADER_RE = re.compile(
    r'^\s*(REFERENCES|References|Bibliography|BIBLIOGRAPHY|'
    r'LITERATURE\s+CITED|Literature\s+Cited|WORKS\s+CITED)\s*$',
    re.MULTILINE
)


def _strip_references(text: str) -> str:
    """Remove everything after the references header."""
    m = _REFS_HEADER_RE.search(text)
    if m:
        return text[:m.start()]
    return text


def _strip_zero_width(text: str) -> str:
    """Strip Unicode zero-width characters that break DOI extraction."""
    return re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad]', '', text)


# ---------------------------------------------------------------------------
# OCR fallback for image-only PDFs
# ---------------------------------------------------------------------------

def _sha1_short(path: Path) -> str:
    """Short content hash for OCR cache key."""
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _page1_alpha_count(pdf_path: Path) -> int:
    """Count alphabetic characters on page 1 (proxy for text-extractability)."""
    try:
        result = subprocess.run(
            ["pdftotext", "-l", "1", str(pdf_path), "-"],
            capture_output=True, timeout=15,
        )
        text = result.stdout.decode("utf-8", errors="replace")
        return sum(1 for c in text if c.isalpha())
    except Exception:
        return 0


def ensure_text_extractable(pdf_path: Path) -> Path:
    """Return a text-extractable path for the given PDF.

    If the PDF already has text on page 1, returns the original path.
    Otherwise runs ocrmypdf into ``OCR_CACHE`` keyed by the source SHA1,
    and returns the cached OCR'd copy. Re-runs re-use the cache.

    Failure is non-fatal: returns the original path if OCR cannot run.
    """
    if not OCR_ENABLED:
        return pdf_path
    if _page1_alpha_count(pdf_path) >= OCR_MIN_ALPHA:
        return pdf_path

    OCR_CACHE.mkdir(parents=True, exist_ok=True)
    h = _sha1_short(pdf_path)
    cache = OCR_CACHE / f"{h}.pdf"
    if cache.exists() and cache.stat().st_size > 0:
        return cache

    print(f"  OCR: {pdf_path.name} (no text on page 1)")
    try:
        result = subprocess.run(
            ["ocrmypdf", "--skip-text", "--output-type", "pdf",
             "--language", OCR_LANGS, "--quiet",
             str(pdf_path), str(cache)],
            capture_output=True, timeout=600,
        )
        if cache.exists() and cache.stat().st_size > 0:
            return cache
        # Fall back to --force-ocr if --skip-text bailed (e.g., mixed content)
        result = subprocess.run(
            ["ocrmypdf", "--force-ocr", "--output-type", "pdf",
             "--language", OCR_LANGS, "--quiet",
             str(pdf_path), str(cache)],
            capture_output=True, timeout=600,
        )
        if cache.exists() and cache.stat().st_size > 0:
            return cache
        print(f"  OCR failed: {result.stderr.decode('utf-8', errors='replace')[:200]}")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  OCR unavailable/timeout: {e}")
    return pdf_path


def _search_text_for_doi(text: str, allow_bare: bool = False) -> str:
    """Search text for a DOI. Returns the best (longest) match or empty string.

    Collects all DOI candidates from prefixed and URL patterns, then returns
    the longest (most complete) one.  If allow_bare is True, also matches
    bare '10.XXXX/...' patterns (riskier — may match reference DOIs).
    """
    text = _strip_zero_width(text)
    candidates: list[str] = []

    # DOI: or doi: prefix — find all
    for m in re.finditer(r'(?:doi|DOI)[\s:]*\s*(10\.\d{4,}/[^\s\]>)]+)', text):
        candidates.append(m.group(1).rstrip('.,;'))
    # https://doi.org/ URL — find all
    for m in re.finditer(r'https?://(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s\]>)]+)', text):
        candidates.append(m.group(1).rstrip('.,;'))

    if candidates:
        # Prefer longest (most complete) DOI; discard obviously truncated
        valid = [d for d in candidates
                 if len(d.split('/', 1)[1]) >= 5] or candidates
        return max(valid, key=len)

    # Bare DOI (only when explicitly allowed, if nothing else found)
    if allow_bare:
        m = re.search(r'(10\.\d{4,}/[^\s\]>)]{3,})', text)
        if m:
            return m.group(1).rstrip('.,;')
    return ""


def reconstruct_doi_from_filename(filename: str) -> str:
    """Reconstruct DOI from known filename patterns.

    Covers Springer (BF*, s*) and Wiley (j.*) article-ID filenames.
    """
    stem = Path(filename).stem
    # Springer BF pattern: BF00002546 → 10.1007/BF00002546
    if re.match(r'^BF\d{5,}$', stem):
        return f"10.1007/{stem}"
    # Springer s-prefix: s00227-005-0151-x → 10.1007/s00227-005-0151-x
    if re.match(r'^s\d{4,}', stem) and '-' in stem:
        return f"10.1007/{stem}"
    # Wiley j.* pattern: j.1365-2621.1991.tb01157.x → 10.1111/j.1365-2621.1991.tb01157.x
    if re.match(r'^j\.\d{4}', stem):
        return f"10.1111/{stem}"
    return ""


def extract_doi_from_pdf(pdf_path: Path) -> str:
    """Extract the paper's own DOI from a PDF.

    Strategy (in order):
      1. First page — full search including bare DOIs (most papers
         print their DOI on page 1).
      2. Last page, excluding references section — catches DOIs in
         footers/headers. Only doi:/doi.org patterns, not bare DOIs,
         to avoid matching cited references.
    """
    # Pass 1: first page (fast, allow bare DOI)
    try:
        result = subprocess.run(
            ["pdftotext", "-l", "1", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=15
        )
        if result.stdout:
            doi = _search_text_for_doi(result.stdout, allow_bare=True)
            if doi:
                return doi
    except (subprocess.TimeoutExpired, Exception):
        pass

    # Pass 2: last page only, references stripped, no bare DOIs
    try:
        # Get page count
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True, timeout=10
        )
        pages_match = re.search(r'Pages:\s*(\d+)', result.stdout)
        if pages_match:
            last_page = pages_match.group(1)
            result = subprocess.run(
                ["pdftotext", "-f", last_page, "-l", last_page,
                 str(pdf_path), "-"],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout:
                text = _strip_references(result.stdout)
                doi = _search_text_for_doi(text, allow_bare=False)
                if doi:
                    return doi
    except (subprocess.TimeoutExpired, Exception):
        pass

    return ""


# ---------------------------------------------------------------------------
# Title-based fuzzy matching from PDF text
# ---------------------------------------------------------------------------

# Words too common to be useful for title matching
_TITLE_STOP_WORDS = frozenset({
    'with', 'from', 'that', 'this', 'have', 'been', 'were', 'their',
    'also', 'into', 'than', 'only', 'other', 'some', 'more', 'which',
    'when', 'will', 'each', 'make', 'like', 'very', 'does', 'made',
    'about', 'between', 'through', 'after', 'before', 'these', 'those',
    'under', 'over', 'such', 'both', 'most', 'same', 'first', 'last',
    'using', 'used', 'based', 'results', 'study', 'however', 'found',
    # Publishing boilerplate
    'journal', 'volume', 'number', 'press', 'published', 'received',
    'accepted', 'copyright', 'rights', 'reserved', 'abstract',
    'introduction', 'methods', 'discussion', 'acknowledgements',
    'references', 'printed', 'netherlands', 'springer', 'verlag',
    'wiley', 'elsevier', 'academic', 'publishers', 'university',
})


def _title_words(text: str) -> set[str]:
    """Extract meaningful 4+ char lowercase words, excluding stop words."""
    return set(re.findall(r'[a-z]{4,}', text.lower())) - _TITLE_STOP_WORDS


def extract_text_for_matching(pdf_path: Path) -> str:
    """Extract text from first 2 pages for title matching.

    Tries page 1 first; if it yields <30 chars (watermark/blank), tries page 2.
    """
    text_parts = []
    for page in ["1", "2"]:
        try:
            result = subprocess.run(
                ["pdftotext", "-f", page, "-l", page, str(pdf_path), "-"],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout:
                text_parts.append(_strip_zero_width(result.stdout))
        except (subprocess.TimeoutExpired, Exception):
            continue
    return "\n".join(text_parts)


def match_by_pdf_title(pdf_path: Path, all_rows: list[dict],
                       filename_year: str = "") -> tuple[dict | None, str]:
    """Extract text from PDF and fuzzy-match against database titles.

    Scores by how many of the DB title's meaningful words appear in
    the PDF's first-page text.  Requires >=60% coverage AND >=4 words.

    ``filename_year`` is an optional year extracted from the filename;
    used as fallback when the year cannot be read from the PDF text.
    """
    text = extract_text_for_matching(pdf_path)
    if len(text.strip()) < 30:
        return None, "no readable text in PDF"

    pdf_words = _title_words(text[:2000])  # first ~2000 chars, title area
    if len(pdf_words) < 3:
        return None, "too few meaningful words in PDF"

    # Try to extract a year from the text for faster filtering
    year_hint = ""
    ym = re.search(r'\b(19\d{2}|20\d{2})\b', text[:500])
    if ym:
        year_hint = ym.group(1)
    elif filename_year:
        year_hint = filename_year

    best: dict | None = None
    best_score = 0.0
    best_overlap = 0

    for r in all_rows:
        # Filter by year if available (speeds up search)
        if year_hint:
            try:
                ry = str(int(float(r["year"])))
            except (ValueError, TypeError):
                continue
            if ry != year_hint:
                continue

        rtw = _title_words(r["title"])
        if len(rtw) < 2:
            continue
        overlap = len(pdf_words & rtw)
        if overlap < 4:
            continue
        score = overlap / len(rtw)
        if score > best_score or (score == best_score and overlap > best_overlap):
            best_score = score
            best_overlap = overlap
            best = r

    if best and best_score >= 0.6 and best_overlap >= 4:
        return best, f"Title match from PDF text ({best_overlap} words, {best_score:.0%} of title)"

    # If year filter gave no result, retry without it
    if year_hint:
        best = None
        best_score = 0.0
        best_overlap = 0
        for r in all_rows:
            rtw = _title_words(r["title"])
            if len(rtw) < 2:
                continue
            overlap = len(pdf_words & rtw)
            if overlap < 4:
                continue
            score = overlap / len(rtw)
            if score > best_score or (score == best_score and overlap > best_overlap):
                best_score = score
                best_overlap = overlap
                best = r
        if best and best_score >= 0.6 and best_overlap >= 4:
            return best, f"Title match from PDF text, no year filter ({best_overlap} words, {best_score:.0%})"

    reason = f"best title overlap: {best_overlap} words"
    if best:
        reason += f", {best_score:.0%} coverage"
    return None, reason


# ---------------------------------------------------------------------------
# Book detection and chapter extraction
# ---------------------------------------------------------------------------

def get_page_count(pdf_path: Path) -> int:
    """Get page count via pdfinfo."""
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True, timeout=10
        )
        m = re.search(r'Pages:\s*(\d+)', result.stdout)
        if m:
            return int(m.group(1))
    except (subprocess.TimeoutExpired, Exception):
        pass
    return 0


def detect_book(pdf_path: Path) -> bool:
    """Detect if a PDF is a book (ISBN in filename or very high page count)."""
    stem = Path(pdf_path).stem
    # ISBN-13 pattern in filename
    if re.match(r'^978[-\d]+$', stem):
        return True
    # ISBN-10 pattern
    if re.match(r'^\d{10}$', stem):
        return True
    # High page count
    pages = get_page_count(pdf_path)
    if pages > 200:
        return True
    return False


def extract_toc_entries(pdf_path: Path) -> list[tuple[str, int, int]]:
    """Extract table-of-contents entries from a book PDF.

    Scans pages 2-30 for chapter/section headings with page numbers.
    Handles multiple TOC formats:
      - "Chapter N  Title ...... page"
      - "N. Title  page"
      - "Title ......... page"
      - Multi-line: "Chapter N  Title\\n  Author ... page"
    Returns list of (chapter_title, start_page, end_page).
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-f", "2", "-l", "30", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=30
        )
        if not result.stdout:
            return []
    except (subprocess.TimeoutExpired, Exception):
        return []

    text = _strip_zero_width(result.stdout)

    # First, try to find the "Contents" section
    contents_start = 0
    for m in re.finditer(r'^Contents\s*$', text, re.MULTILINE | re.IGNORECASE):
        contents_start = m.end()
        break

    if contents_start:
        toc_text = text[contents_start:]
    else:
        toc_text = text

    entries: list[tuple[str, int]] = []
    lines = toc_text.split('\n')

    # Multi-format TOC parser.  Springer books typically use:
    #   Chapter N                            ← chapter marker
    #                                        ← blank
    #   Title Spanning One or                ← title lines
    #   More Lines                           ← title continuation
    #   Author Name . . . . . . . . .        ← author + dots (no page!)
    #                                        ← blank
    #   17                                   ← page number standalone

    # State machine: collect chapter title, then wait for page number
    pending_title = ""
    saw_author_dots = False

    for line in lines:
        stripped = line.strip()

        # Detect "Chapter N" marker (title may follow on same line or next)
        m = re.match(r'^Chapter\s+(\d+)\s*(.*)', stripped, re.IGNORECASE)
        if m:
            # Save any previous pending entry if we somehow missed its page
            pending_title = m.group(2).strip()
            saw_author_dots = False
            continue

        # Detect "Part N" section headers — reset state, skip
        if re.match(r'^Part\s+[IVXLCDM]+', stripped, re.IGNORECASE):
            pending_title = ""
            saw_author_dots = False
            continue

        # Skip TOC page numbers like "xii", "xiii", boilerplate
        if re.match(r'^[ivxlcdm]+$', stripped, re.IGNORECASE):
            continue
        if stripped.lower() in ('contents', 'contributors', ''):
            continue

        # Standalone page number (1-4 digits on a line by itself)
        if re.match(r'^\d{1,4}$', stripped):
            page = int(stripped)
            if pending_title and page > 0:
                entries.append((pending_title, page))
                pending_title = ""
                saw_author_dots = False
            continue

        # Line ending with page number after dots/spaces
        m = re.match(r'^(.+?)\s*[.·\s]{3,}\s*(\d{1,4})\s*$', stripped)
        if m:
            page = int(m.group(2))
            if page > 0:
                if pending_title:
                    entries.append((pending_title, page))
                    pending_title = ""
                    saw_author_dots = False
                else:
                    # Standalone entry: title...page on one line
                    title = m.group(1).strip()
                    if title.lower() not in (
                        'preface', 'acknowledgments', 'index',
                        'subject index', 'author index', 'taxonomic index'
                    ) and len(title) > 10:
                        entries.append((title, page))
            continue

        # Author line (contains dots/periods pattern, no page number)
        if re.search(r'[.·]{3,}', stripped):
            saw_author_dots = True
            continue

        # If no pending title and blank line, skip
        if not stripped:
            continue

        # Title or title continuation line
        if pending_title and not saw_author_dots:
            pending_title += " " + stripped
        elif not pending_title:
            # Skip boilerplate
            if stripped.lower() in (
                'preface', 'acknowledgments', 'contributors',
                'index', 'subject index', 'author index',
                'taxonomic index', 'taxonomic appendix'
            ):
                continue
            # Could be start of a non-"Chapter N" title
            if len(stripped) > 10:
                pending_title = stripped
                saw_author_dots = False

    if not entries:
        return []

    # Deduplicate (same page) and enforce monotonically increasing pages.
    # Once page numbers start decreasing, we've left the TOC.
    total_pages = get_page_count(pdf_path)
    seen_pages: set[int] = set()
    unique_entries: list[tuple[str, int]] = []
    max_page_seen = 0
    for title, page in entries:
        if page > total_pages or page < 1:
            continue
        if page in seen_pages:
            continue
        if page < max_page_seen:
            # Page numbers went backwards — we've left the TOC
            break
        seen_pages.add(page)
        max_page_seen = page
        unique_entries.append((title, page))
    entries = unique_entries

    # Convert to (title, start_page, end_page) using next chapter's start
    result_entries: list[tuple[str, int, int]] = []
    for i, (title, start) in enumerate(entries):
        if i + 1 < len(entries):
            end = entries[i + 1][1] - 1
        else:
            end = min(start + 30, total_pages)
        result_entries.append((title, start, end))

    return result_entries


def handle_book(pdf_path: Path, doi_lookup: dict, author_year_lookup: dict,
                all_rows: list[dict]) -> list[tuple[Path, dict, str]]:
    """Handle a book PDF: detect chapters, match against DB, extract pages.

    Returns list of (extracted_pdf_path, matched_row, method) for each
    successfully extracted and matched chapter.
    """
    import pikepdf

    pages = get_page_count(pdf_path)
    print(f"  BOOK DETECTED: {pdf_path.name} ({pages} pages)")

    # Check if it's really just a single article with a book-like filename
    if pages <= 50:
        print(f"    Low page count ({pages}) — treating as single article")
        return []  # fall through to normal matching

    # Extract and parse TOC
    toc = extract_toc_entries(pdf_path)
    if not toc:
        print(f"    No TOC entries found — cannot extract chapters")
        return []

    print(f"    Found {len(toc)} TOC entries")

    # Match TOC chapter titles against database
    matched_chapters: list[tuple[str, int, int, dict, str]] = []
    for title, start, end in toc:
        title_words_set = _title_words(title)
        if len(title_words_set) < 3:
            continue

        best_row = None
        best_score = 0.0
        best_overlap = 0
        for r in all_rows:
            rtw = _title_words(r["title"])
            if len(rtw) < 2:
                continue
            overlap = len(title_words_set & rtw)
            if overlap < 3:
                continue
            score = overlap / len(rtw)
            if score > best_score or (score == best_score and overlap > best_overlap):
                best_score = score
                best_overlap = overlap
                best_row = r

        if best_row and best_score >= 0.7 and best_overlap >= 5:
            matched_chapters.append(
                (title, start, end, best_row,
                 f"Book chapter TOC match ({best_overlap} words, {best_score:.0%})")
            )
            print(f"    CHAPTER MATCH: '{title[:60]}' (pp.{start}-{end})")
            print(f"      → {best_row['title'][:70]}")

    if not matched_chapters:
        print(f"    No chapter titles matched database entries")
        return []

    # Extract matched chapters as separate PDFs
    extracted: list[tuple[Path, dict, str]] = []
    extract_dir = pdf_path.parent / "_extracted_chapters"
    extract_dir.mkdir(exist_ok=True)

    try:
        src = pikepdf.open(pdf_path)
    except Exception as e:
        print(f"    ERROR opening book PDF: {e}")
        return []

    for title, start, end, row, method in matched_chapters:
        # PDF pages are 0-indexed in pikepdf, but TOC numbers are logical
        # Need to account for front matter offset — estimate from first chapter
        # For now, use page numbers as-is (0-indexed adjustment)
        p_start = max(0, start - 1)
        p_end = min(len(src.pages) - 1, end - 1)

        if p_start >= len(src.pages):
            print(f"    SKIP: page {start} beyond PDF length ({len(src.pages)})")
            continue

        chapter_name = build_filename(row)
        chapter_path = extract_dir / chapter_name

        try:
            dst = pikepdf.new()
            for p in range(p_start, p_end + 1):
                dst.pages.append(src.pages[p])
            dst.save(chapter_path)
            dst.close()
            extracted.append((chapter_path, row, method))
            print(f"    EXTRACTED: pp.{start}-{end} → {chapter_name}")
        except Exception as e:
            print(f"    ERROR extracting pp.{start}-{end}: {e}")

    src.close()
    return extracted


def parse_filename_info(filename: str) -> dict:
    """
    Extract author surname and year from various filename formats.
    Returns dict with 'author' (lowercase, accent-stripped) and 'year'.
    """
    stem = Path(filename).stem
    info = {"author": "", "year": "", "title_words": []}

    # Format: "Author et al. - Year - Title..."
    m = re.match(r'^([A-Za-zÀ-ÿ\u0100-\u017F]+(?:\s+et\s+al\.?)?)\s*[-–]\s*(\d{4})\s*[-–]\s*(.+)', stem)
    if m:
        author = m.group(1).split()[0]
        info["author"] = strip_accents(author).lower()
        info["year"] = m.group(2)
        info["title_words"] = re.findall(r'[a-z]{4,}', m.group(3).lower())
        return info

    # Format: "Author etal Year Title..."  (e.g. from library)
    m = re.match(r'^([A-Za-zÀ-ÿ]+)\s+et\s+al\.\s*[-–]?\s*(\d{4})\s*[-–]?\s*(.+)', stem)
    if m:
        info["author"] = strip_accents(m.group(1)).lower()
        info["year"] = m.group(2)
        info["title_words"] = re.findall(r'[a-z]{4,}', m.group(3).lower())
        return info

    # Format: "Journal - Year - Author - Title..."
    m = re.match(r'^[A-Za-z\s&]+[-–]\s*(\d{4})\s*[-–]\s*([A-Za-zÀ-ÿ]+)\s*[-–]\s*(.+)', stem)
    if m:
        info["year"] = m.group(1)
        info["author"] = strip_accents(m.group(2)).lower()
        info["title_words"] = re.findall(r'[a-z]{4,}', m.group(3).lower())
        return info

    # Format: "CEYHAN et al. - Year - Title..."
    m = re.match(r'^([A-ZÀ-ÿ]+)\s+et\s+al\.\s*[-–]\s*(\d{4})\s*[-–]\s*(.+)', stem, re.IGNORECASE)
    if m:
        info["author"] = strip_accents(m.group(1)).lower()
        info["year"] = m.group(2)
        info["title_words"] = re.findall(r'[a-z]{4,}', m.group(3).lower())
        return info

    # Format: "Year - Journal..." (e.g. "2015 - Marine Ecology Progress Series 524255")
    m = re.match(r'^(\d{4})\s*[-–]\s*(.+)', stem)
    if m:
        info["year"] = m.group(1)
        info["title_words"] = re.findall(r'[a-z]{4,}', m.group(2).lower())
        return info

    # Format: "YYYY_art_author..."
    m = re.match(r'^(\d{4})_art_([a-z]+)', stem, re.IGNORECASE)
    if m:
        info["year"] = m.group(1)
        info["author"] = strip_accents(m.group(2)).lower()
        return info

    # Look for any 4-digit year
    m = re.search(r'\b(19\d{2}|20\d{2})\b', stem)
    if m:
        info["year"] = m.group(1)

    # Look for leading author name
    m = re.match(r'^([A-Za-zÀ-ÿ\u0100-\u017F]+)', stem)
    if m and len(m.group(1)) >= 3 and not m.group(1).isdigit():
        info["author"] = strip_accents(m.group(1)).lower()

    return info


# ---------------------------------------------------------------------------
# Database loading
# ---------------------------------------------------------------------------

def load_database() -> tuple[list[dict], dict[str, dict], dict[str, list[dict]]]:
    """
    Load viz_data.csv and build lookup indices.
    Returns: (all_rows, doi_lookup, author_year_lookup)
    """
    rows = []
    with open(VIZ_DATA, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "literature_id": r["literature_id"],
                "year": r["year"],
                "authors": r["authors"],
                "title": r["title"],
                "doi": r["doi"],
            })

    # DOI index
    doi_lookup: dict[str, dict] = {}
    for r in rows:
        nd = normalise_doi(r["doi"])
        if nd:
            doi_lookup[nd] = r

    # Author surname + year index (for fuzzy matching)
    author_year_lookup: dict[str, list[dict]] = {}
    for r in rows:
        surname = extract_first_author(r["authors"])
        surname_clean = strip_accents(surname).lower()
        try:
            year_str = str(int(float(r["year"])))
        except (ValueError, TypeError):
            continue
        key = f"{surname_clean}_{year_str}"
        author_year_lookup.setdefault(key, []).append(r)

    return rows, doi_lookup, author_year_lookup


def match_pdf(pdf_path: Path, doi_lookup: dict, author_year_lookup: dict,
              all_rows: list[dict],
              text_path: Path | None = None) -> tuple[dict | None, str]:
    """
    Try to match a PDF to the database. Returns (matched_row, method) or (None, reason).

    ``pdf_path`` is the original file (its name drives filename-based
    strategies). ``text_path`` — if supplied — is used for text
    extraction (DOI, title match) and defaults to ``pdf_path``; pass an
    OCR'd copy when the original is image-only.

    Strategies (tried in order):
      1. Extract DOI from PDF content
      2. Reconstruct DOI from filename pattern (Springer BF*, Wiley j.*, etc.)
      3. Author + year from filename
      4. Year + title words from filename
      5. Title fuzzy-match from PDF text (OCR fallback)
    """
    if text_path is None:
        text_path = pdf_path

    # Strategy 1: extract DOI from PDF content
    doi_text = extract_doi_from_pdf(text_path)
    if doi_text:
        nd = normalise_doi(doi_text)
        if nd in doi_lookup:
            return doi_lookup[nd], f"DOI from PDF text: {doi_text}"
        # Sometimes DOI has trailing garbage, try trimming
        for trim in [1, 2, 3]:
            trimmed = nd[:-trim] if len(nd) > trim else nd
            if trimmed in doi_lookup:
                return doi_lookup[trimmed], f"DOI from PDF text (trimmed): {doi_text}"

    # Strategy 2: reconstruct DOI from filename pattern
    recon_doi = reconstruct_doi_from_filename(pdf_path.name)
    if recon_doi:
        nd = normalise_doi(recon_doi)
        if nd in doi_lookup:
            return doi_lookup[nd], f"DOI reconstructed from filename: {recon_doi}"

    # Strategy 3: filename-based author+year matching
    finfo = parse_filename_info(pdf_path.name)
    if finfo["author"] and finfo["year"]:
        key = f"{finfo['author']}_{finfo['year']}"
        candidates = author_year_lookup.get(key, [])
        if len(candidates) == 1:
            return candidates[0], f"Author+year from filename: {finfo['author']} {finfo['year']}"
        elif len(candidates) > 1:
            # Try title word matching to disambiguate
            if finfo["title_words"]:
                best = None
                best_score = 0
                for c in candidates:
                    ctitle_words = set(re.findall(r'[a-z]{4,}', c["title"].lower()))
                    overlap = len(set(finfo["title_words"]) & ctitle_words)
                    if overlap > best_score:
                        best_score = overlap
                        best = c
                if best and best_score >= 2:
                    return best, f"Author+year+title from filename ({best_score} words matched)"
            # Filename gave no usable title words (common for journal-helper
            # names like Author-Title-Year): disambiguate the candidates using
            # the PDF's own title text rather than giving up.
            text = extract_text_for_matching(text_path)
            pdf_words = _title_words(text[:2000])
            if len(pdf_words) >= 3:
                best = None
                best_score = 0.0
                best_overlap = 0
                for c in candidates:
                    rtw = _title_words(c["title"])
                    if len(rtw) < 2:
                        continue
                    overlap = len(pdf_words & rtw)
                    if overlap < 4:
                        continue
                    score = overlap / len(rtw)
                    if score > best_score or (score == best_score and overlap > best_overlap):
                        best_score, best_overlap, best = score, overlap, c
                if best and best_score >= 0.6:
                    return best, (f"Author+year, disambiguated by PDF title "
                                  f"({best_overlap} words, {best_score:.0%} of title)")
            # Could not disambiguate against the candidate set — fall through to
            # the broader title-from-text strategy below instead of giving up.

    # Strategy 4: if we have a year and title words from filename, try broader match
    if finfo["year"] and finfo["title_words"] and len(finfo["title_words"]) >= 3:
        target_words = set(finfo["title_words"][:8])
        best = None
        best_score = 0
        try:
            target_year = str(int(finfo["year"]))
        except ValueError:
            target_year = ""
        for r in all_rows:
            try:
                ry = str(int(float(r["year"])))
            except (ValueError, TypeError):
                continue
            if ry != target_year:
                continue
            rtitle_words = set(re.findall(r'[a-z]{4,}', r["title"].lower()))
            overlap = len(target_words & rtitle_words)
            if overlap > best_score:
                best_score = overlap
                best = r
        if best and best_score >= 3:
            return best, f"Year+title words from filename ({best_score} words)"

    # Strategy 5: extract text from PDF and fuzzy-match title against database
    row, method = match_by_pdf_title(text_path, all_rows, filename_year=finfo.get("year", ""))
    if row:
        return row, method

    # All strategies failed — build informative reason
    reason_parts = []
    if not doi_text:
        reason_parts.append("no DOI in PDF")
    else:
        reason_parts.append(f"DOI not in DB: {doi_text}")
    if recon_doi:
        reason_parts.append(f"reconstructed DOI not in DB: {recon_doi}")
    if not finfo["author"]:
        reason_parts.append("no author in filename")
    elif not finfo["year"]:
        reason_parts.append("no year in filename")
    else:
        reason_parts.append(f"no DB match for {finfo['author']} {finfo['year']}")
    reason_parts.append(f"title match failed ({method})")

    return None, "; ".join(reason_parts)


# ---------------------------------------------------------------------------
# Tracking updates (from ingest_jurgen_pdfs.py pattern)
# ---------------------------------------------------------------------------

def update_papers_data_json(copied_ids: set, copied_dois: set,
                            timestamp: str, source_label: str) -> int:
    """Remove matched papers from docs/papers_data.json (they are no longer missing).

    Matches by literature_id first, then by DOI for papers with empty literature_ids.
    """
    if not PAPERS_DATA_JSON.exists():
        return 0
    with open(PAPERS_DATA_JSON) as f:
        data = json.load(f)
    if not data:
        return 0

    id_lookup = set()
    for lid in copied_ids:
        if not str(lid).strip():
            continue
        id_lookup.add(str(lid).strip())
        # Handle "12345.0" format
        try:
            lid_int = int(float(lid))
            id_lookup.add(f"{lid_int}.0")
            id_lookup.add(f"{lid_int}")
        except (ValueError, TypeError):
            pass
    # Safety: never match empty strings
    id_lookup.discard("")

    # Normalise DOIs for matching
    doi_lookup = set()
    for doi in copied_dois:
        nd = normalise_doi(doi)
        if nd:
            doi_lookup.add(nd)

    before = len(data)
    filtered = []
    for entry in data:
        lid = str(entry.get("literature_id", "")).strip()
        if lid and lid in id_lookup:
            continue  # matched by literature_id
        entry_doi = normalise_doi(str(entry.get("doi", "")))
        if entry_doi and entry_doi in doi_lookup:
            continue  # matched by DOI (catches empty-lit_id papers)
        filtered.append(entry)
    data = filtered
    after = len(data)
    removed = before - after

    if removed > 0:
        with open(PAPERS_DATA_JSON, "w") as f:
            json.dump(data, f, indent=2)

    return removed


def update_tracking_dbs(copied_ids: set, pdf_names: dict, timestamp: str, source_label: str):
    """Update download_tracker.db and download_queue.db."""
    import sqlite3

    # download_tracker.db
    tracker_db_path = DOWNLOAD_TRACKER_DB
    if tracker_db_path.exists():
        db = sqlite3.connect(str(tracker_db_path))
        try:
            rows = db.execute("SELECT id, literature_id FROM papers").fetchall()
            lit_to_paper_id = {}
            for pid, lid in rows:
                try:
                    lit_to_paper_id[int(float(lid))] = pid
                except (ValueError, TypeError):
                    continue
            inserted = 0
            for lit_id in copied_ids:
                try:
                    lid_int = int(float(lit_id))
                except (ValueError, TypeError):
                    continue
                paper_id = lit_to_paper_id.get(lid_int)
                if paper_id is None:
                    continue
                existing = db.execute(
                    "SELECT id FROM download_status WHERE paper_id = ? AND status = 'downloaded'",
                    (paper_id,)
                ).fetchone()
                if existing:
                    continue
                db.execute(
                    "INSERT INTO download_status (paper_id, status, download_date, source, notes, attempts, last_attempt) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (paper_id, "downloaded", timestamp, source_label,
                     f"Filed as {pdf_names.get(lit_id, 'unknown')}", 1, timestamp)
                )
                inserted += 1
            db.commit()
            print(f"  download_tracker.db: {inserted} rows inserted")
        except Exception as e:
            print(f"  download_tracker.db: error — {e}")
        finally:
            db.close()

    # download_queue.db
    queue_db_path = DOWNLOAD_QUEUE_DB
    if queue_db_path.exists():
        db = sqlite3.connect(str(queue_db_path))
        try:
            updated = 0
            for lit_id in copied_ids:
                try:
                    lid_int = int(float(lit_id))
                except (ValueError, TypeError):
                    continue
                for fmt in [str(lid_int), f"{lid_int}.0"]:
                    result = db.execute(
                        "UPDATE download_queue SET status = 'success', download_timestamp = ?, pdf_path = ? "
                        "WHERE literature_id = ? AND status != 'success'",
                        (timestamp, pdf_names.get(lit_id, ""), fmt)
                    )
                    updated += result.rowcount
            db.commit()
            print(f"  download_queue.db: {updated} rows updated")
        except Exception as e:
            print(f"  download_queue.db: error — {e}")
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def ingest_source(label: str, pdf_paths: list[Path],
                  doi_lookup: dict, author_year_lookup: dict,
                  all_rows: list[dict],
                  filed_map: dict | None = None) -> tuple[set, set, dict, list[str]]:
    """
    Ingest a list of PDFs. Returns (copied_ids, copied_dois, pdf_names, log_lines).

    ``filed_map`` (optional): if a dict is passed, it is populated in-place with
    ``{str(source_pdf_path): literature_id}`` for every matched PDF. Lets callers
    map a *specific input file* to the corpus id it was filed under -- e.g. so a
    staged '<download_id>.pdf' that matched the corpus by title (under a different
    id) can still be identified and its staging copy safely removed.
    """
    log_lines = []
    copied = 0
    skipped_exists = 0
    matched_existing = 0
    unmatched = 0
    errors = 0
    copied_ids: set = set()
    copied_dois: set = set()
    pdf_names: dict = {}

    print(f"\n{'=' * 70}")
    print(f"  Source: {label}")
    print(f"  PDFs: {len(pdf_paths)}")
    print(f"{'=' * 70}")

    def _file_one(pdf_src: Path, row: dict, method: str):
        """Copy a single matched PDF into the library. Returns True if new copy."""
        nonlocal copied, skipped_exists, errors
        lit_id = row["literature_id"]
        new_name = build_filename(row)
        try:
            year_int = int(float(row["year"]))
            year_str = str(year_int)
        except (ValueError, TypeError):
            year_str = "Unknown"

        year_dir = PDF_BASE / year_str
        target = year_dir / new_name

        if target.exists():
            skipped_exists += 1
            copied_ids.add(lit_id)
            if row.get("doi"):
                copied_dois.add(row["doi"])
            pdf_names[lit_id] = f"{year_str}/{new_name}"
            log_lines.append(f"EXISTS: {year_str}/{new_name} (from {pdf_src.name}) [{method}]")
            print(f"  EXISTS: {pdf_src.name} → {year_str}/{new_name}")
            return False

        try:
            year_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_src, target)
            copied += 1
            copied_ids.add(lit_id)
            if row.get("doi"):
                copied_dois.add(row["doi"])
            pdf_names[lit_id] = f"{year_str}/{new_name}"
            log_lines.append(f"COPIED: {pdf_src.name} → {year_str}/{new_name} [{method}]")
            print(f"  COPIED: {pdf_src.name}")
            print(f"      → {year_str}/{new_name}")
            print(f"      Method: {method}")

            if DEDUP_CHECK_ENABLED and _DEDUP_OK:
                try:
                    flags = _dedup_check_new_pdf(target, ocr_if_needed=False, do_doi=True)
                except Exception as e:
                    flags = []
                    log_lines.append(f"DEDUP_ERROR: {target.name} — {e}")
                for fl in flags:
                    msg = (f"      POSSIBLE DUPLICATE: {fl['candidate']}  "
                           f"({fl['decision']}, conf={fl['confidence']})  "
                           f"[{fl.get('signals','')}]")
                    print(msg)
                    log_lines.append(f"DEDUP_FLAG: {year_str}/{new_name} ↔ {fl['candidate']} "
                                     f"{fl['decision']} conf={fl['confidence']}")
            return True
        except Exception as e:
            errors += 1
            log_lines.append(f"ERROR: {pdf_src.name} — {e}")
            print(f"  ERROR: {pdf_src.name} — {e}")
            return False

    for pdf_path in pdf_paths:
        # Book detection: handle multi-chapter books specially
        if detect_book(pdf_path):
            chapters = handle_book(pdf_path, doi_lookup, author_year_lookup, all_rows)
            if chapters:
                for ch_path, ch_row, ch_method in chapters:
                    _file_one(ch_path, ch_row, ch_method)
                log_lines.append(f"BOOK: {pdf_path.name} — {len(chapters)} chapters extracted")
                continue
            # If no chapters matched, fall through to normal matching
            # (could be a single-chapter book or misdetected)
            print(f"    Falling through to normal matching for {pdf_path.name}")

        text_path = ensure_text_extractable(pdf_path)
        row, method = match_pdf(pdf_path, doi_lookup, author_year_lookup,
                                all_rows, text_path=text_path)

        if row is None:
            unmatched += 1
            log_lines.append(f"UNMATCHED: {pdf_path.name} — {method}")
            print(f"  UNMATCHED: {pdf_path.name}")
            print(f"            Reason: {method}")
            continue

        # Prefer OCR'd version for the library so future extraction has text
        file_src = text_path if text_path != pdf_path else pdf_path
        _file_one(file_src, row, method)
        if filed_map is not None:
            # Map the ORIGINAL input path (not the OCR cache) to its corpus id.
            filed_map[str(pdf_path)] = row["literature_id"]

    print(f"\n  Summary for {label}:")
    print(f"    Copied (new):    {copied}")
    print(f"    Already existed: {skipped_exists}")
    print(f"    Unmatched:       {unmatched}")
    print(f"    Errors:          {errors}")
    print(f"    Total acquired:  {len(copied_ids)} IDs, {len(copied_dois)} DOIs")

    return copied_ids, copied_dois, pdf_names, log_lines


def check_source(label: str, pdf_paths: list[Path],
                  doi_lookup: dict, author_year_lookup: dict,
                  all_rows: list[dict]) -> None:
    """
    Dry-run: check which PDFs match the database without copying or updating anything.
    Prints a summary table and saves CSV to outputs/ingest_check.csv.
    """
    results = []
    matched = 0
    unmatched = 0

    print(f"\n{'=' * 70}")
    print(f"  CHECK MODE (dry run) — no files will be copied or moved")
    print(f"  Source: {label}")
    print(f"  PDFs: {len(pdf_paths)}")
    print(f"{'=' * 70}")

    for i, pdf_path in enumerate(pdf_paths, 1):
        # Book detection in check mode
        if detect_book(pdf_path):
            pages = get_page_count(pdf_path)
            print(f"  [{i:3d}/{len(pdf_paths)}] BOOK: {pdf_path.name} ({pages} pages)")
            toc = extract_toc_entries(pdf_path)
            if toc:
                print(f"            {len(toc)} TOC entries found")
                # Check chapter matches
                ch_matches = 0
                for title, start, end in toc:
                    tw = _title_words(title)
                    if len(tw) < 3:
                        continue
                    for r in all_rows:
                        rtw = _title_words(r["title"])
                        if len(rtw) < 2:
                            continue
                        overlap = len(tw & rtw)
                        score = overlap / len(rtw) if rtw else 0
                        if score >= 0.7 and overlap >= 5:
                            ch_matches += 1
                            print(f"            Chapter: '{title[:50]}' → {r['title'][:50]}")
                            break
                if ch_matches:
                    matched += ch_matches
                    print(f"            {ch_matches} chapters matched DB entries")
                else:
                    unmatched += 1
                    print(f"            No chapters matched DB entries (threshold: 70%/5 words)")
            else:
                unmatched += 1
                print(f"            No TOC entries found")
            results.append({
                "filename": pdf_path.name,
                "status": f"BOOK ({pages}pp, {len(toc)} TOC entries)",
                "match_method": "book detection",
                "literature_id": "",
                "matched_title": "",
                "matched_doi": "",
            })
            continue

        text_path = ensure_text_extractable(pdf_path)
        row, method = match_pdf(pdf_path, doi_lookup, author_year_lookup,
                                all_rows, text_path=text_path)

        if row is None:
            unmatched += 1
            print(f"  [{i:3d}/{len(pdf_paths)}] NOT FOUND: {pdf_path.name}")
            print(f"            Reason: {method}")
            results.append({
                "filename": pdf_path.name,
                "status": "NOT FOUND",
                "match_method": method,
                "literature_id": "",
                "matched_title": "",
                "matched_doi": "",
            })
        else:
            matched += 1
            # Check if PDF already exists in SharkPapers
            new_name = build_filename(row)
            try:
                year_str = str(int(float(row["year"])))
            except (ValueError, TypeError):
                year_str = "Unknown"
            target = PDF_BASE / year_str / new_name
            exists_label = " (PDF already in library)" if target.exists() else ""
            print(f"  [{i:3d}/{len(pdf_paths)}] FOUND{exists_label}: {pdf_path.name}")
            print(f"            → {row['title'][:80]}")
            print(f"            Method: {method}")
            results.append({
                "filename": pdf_path.name,
                "status": "FOUND" + (" (exists)" if target.exists() else ""),
                "match_method": method,
                "literature_id": row["literature_id"] or "",
                "matched_title": row["title"],
                "matched_doi": row.get("doi", ""),
            })

    print(f"\n{'=' * 70}")
    print(f"CHECK SUMMARY")
    print(f"  Total PDFs:    {len(pdf_paths)}")
    print(f"  Matched:       {matched}")
    print(f"  Not found:     {unmatched}")
    print(f"{'=' * 70}")

    # Save CSV
    import pandas as pd
    out_csv = PROJECT / "outputs" / "ingest_check.csv"
    pd.DataFrame(results).to_csv(out_csv, index=False)
    print(f"  Results saved to: {out_csv}")


def main():
    import sys

    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Parse arguments: --check / --no-ocr / --no-dedup-check flags + paths
    global OCR_ENABLED, DEDUP_CHECK_ENABLED
    args = sys.argv[1:]
    check_mode = "--check" in args
    if check_mode:
        args = [a for a in args if a != "--check"]
    if "--no-ocr" in args:
        OCR_ENABLED = False
        args = [a for a in args if a != "--no-ocr"]
    recursive = "--recursive" in args
    if recursive:
        args = [a for a in args if a != "--recursive"]
    if "--no-dedup-check" in args:
        DEDUP_CHECK_ENABLED = False
        args = [a for a in args if a != "--no-dedup-check"]

    if DEDUP_CHECK_ENABLED and not _DEDUP_OK:
        print(f"  NOTE: dedup check disabled (import failed: {_DEDUP_IMPORT_ERR})")
        DEDUP_CHECK_ENABLED = False

    if not args:
        print("Usage: python scripts/ingest_pdfs.py [--check] [--no-ocr] [--no-dedup-check] /path/to/pdfs/ [file1.pdf ...]")
        print("  --check            Dry run: check matches without copying or updating")
        print("  --no-ocr           Disable OCR fallback on image-only PDFs")
        print("  --no-dedup-check   Skip flagging possible duplicates of existing library files")
        print("  --recursive        Walk subdirectories for PDFs (default: top level only)")
        print("  Provide one or more directories or PDF file paths to ingest.")
        sys.exit(0)

    pdf_paths: list[Path] = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            # --recursive walks subfolders (e.g. topic-organised libraries); default
            # is top-level only, preserving prior behaviour.
            globber = p.rglob if recursive else p.glob
            pdf_paths.extend(sorted(globber("*.pdf")))
            # Also pick up .PDF extension
            pdf_paths.extend(sorted(globber("*.PDF")))
        elif p.is_file() and p.suffix.lower() == ".pdf":
            pdf_paths.append(p)
        else:
            print(f"  WARNING: skipping {arg} (not a PDF or directory)")

    # Deduplicate (in case .pdf and .PDF overlap)
    seen = set()
    unique = []
    for p in pdf_paths:
        if p.name not in seen:
            seen.add(p.name)
            unique.append(p)
    pdf_paths = unique

    if not pdf_paths:
        print("No PDFs found in the given paths.")
        sys.exit(0)

    print("Loading database from viz_data.csv...")
    all_rows, doi_lookup, author_year_lookup = load_database()
    print(f"  {len(all_rows):,} papers loaded, {len(doi_lookup):,} with DOIs")

    source_label = ", ".join(args)

    if check_mode:
        check_source(source_label, pdf_paths, doi_lookup, author_year_lookup, all_rows)
        return

    all_ids, all_dois, all_names, all_log = ingest_source(
        source_label, pdf_paths, doi_lookup, author_year_lookup, all_rows
    )

    # --- Update tracking ---
    print(f"\n{'=' * 70}")
    print("Updating tracking systems...")
    n_json = update_papers_data_json(all_ids, all_dois, timestamp, source_label)
    print(f"  papers_data.json: {n_json} entries removed (no longer missing)")
    update_tracking_dbs(all_ids, all_names, timestamp, source_label)

    # --- Write log ---
    log_content = (
        f"PDF Ingest Log\n"
        f"Date: {timestamp}\n"
        f"Source: {source_label}\n"
        f"{'=' * 70}\n\n"
        f"PDFs found: {len(pdf_paths)}\n"
        f"Acquired: {len(all_ids)}\n"
        f"papers_data.json entries removed: {n_json}\n"
        f"\n{'=' * 70}\n\nDetails:\n"
    )
    with open(LOG_FILE, "w") as f:
        f.write(log_content)
        for line in all_log:
            f.write(line + "\n")

    print(f"\n{'=' * 70}")
    print("INGEST COMPLETE")
    print(f"  Total acquired: {len(all_ids)}")
    print(f"  Log: {LOG_FILE}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
