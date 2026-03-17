#!/usr/bin/env python3
"""
Ingest PDFs from Elena's library and today's Downloads into SharkPapers.

Matching strategy (in order):
  1. Extract DOI from first page of PDF via pdftotext
  2. Match author surname + year from filename
  3. Fuzzy title matching from filename (if enough words)

Copies PDFs to SharkPapers/{year}/ with standardised naming.
No destructive operations — copies only, originals stay in place.
"""

import csv
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
LOG_FILE = LOG_DIR / "elena_downloads_ingest_log.txt"

# Tracking files
PAPERS_DATA_JSON = PROJECT / "docs/papers_data.json"
DOWNLOAD_TRACKER_DB = PROJECT / "database/download_tracker.db"
DOWNLOAD_QUEUE_DB = PROJECT / "outputs/download_queue.db"

ELENA_DIR = Path(
    "/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
    "/database/others_libraries/Elena/papers_elena"
)
DOWNLOADS_DIR = Path("/home/simon/Downloads")
DOWNLOADS_FILES = [
    "1-s2.0-S2351989425003580-main.pdf",
    "Environmetrics - 2024 - Panunzi - Estimating the spatial distribution of the white shark in the Mediterranean Sea via an.pdf",
    "aps.73.20240399.pdf",
    "2023_art_faagoyanna.pdf",
]


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


def extract_doi_from_pdf(pdf_path: Path) -> str:
    """Extract DOI from first page of PDF using pdftotext."""
    try:
        result = subprocess.run(
            ["pdftotext", "-l", "1", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=15
        )
        text = result.stdout
        if not text:
            return ""
        # Common DOI patterns
        # Look for DOI: prefix first
        m = re.search(r'(?:doi|DOI)[\s:]*\s*(10\.\d{4,}/[^\s\]>)]+)', text)
        if m:
            doi = m.group(1).rstrip('.,;')
            return doi
        # Look for https://doi.org/ URLs
        m = re.search(r'https?://(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s\]>)]+)', text)
        if m:
            doi = m.group(1).rstrip('.,;')
            return doi
        # Bare DOI pattern
        m = re.search(r'(10\.\d{4,}/[^\s\]>)]{3,})', text)
        if m:
            doi = m.group(1).rstrip('.,;')
            return doi
    except (subprocess.TimeoutExpired, Exception):
        pass
    return ""


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
              all_rows: list[dict]) -> tuple[dict | None, str]:
    """
    Try to match a PDF to the database. Returns (matched_row, method) or (None, reason).
    """
    # Strategy 1: extract DOI from PDF content
    doi_text = extract_doi_from_pdf(pdf_path)
    if doi_text:
        nd = normalise_doi(doi_text)
        if nd in doi_lookup:
            return doi_lookup[nd], f"DOI from PDF text: {doi_text}"
        # Sometimes DOI has trailing garbage, try trimming
        for trim in [1, 2, 3]:
            trimmed = nd[:-trim] if len(nd) > trim else nd
            if trimmed in doi_lookup:
                return doi_lookup[trimmed], f"DOI from PDF text (trimmed): {doi_text}"

    # Strategy 2: filename-based author+year matching
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
            # If only 2-3 candidates and no title words, still ambiguous
            return None, f"AMBIGUOUS: {len(candidates)} candidates for {finfo['author']} {finfo['year']}"

    # Strategy 3: if we have a year and title words from filename, try broader match
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

    reason_parts = []
    if not doi_text:
        reason_parts.append("no DOI in PDF")
    else:
        reason_parts.append(f"DOI not in DB: {doi_text}")
    if not finfo["author"]:
        reason_parts.append("no author in filename")
    elif not finfo["year"]:
        reason_parts.append("no year in filename")
    else:
        reason_parts.append(f"no DB match for {finfo['author']} {finfo['year']}")

    return None, "; ".join(reason_parts)


# ---------------------------------------------------------------------------
# Tracking updates (from ingest_jurgen_pdfs.py pattern)
# ---------------------------------------------------------------------------

def update_papers_data_json(copied_ids: set, timestamp: str, source_label: str) -> int:
    """Remove matched papers from docs/papers_data.json (they are no longer missing)."""
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

    before = len(data)
    data = [
        entry for entry in data
        if str(entry.get("literature_id", "")).strip() not in id_lookup
    ]
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
                  all_rows: list[dict]) -> tuple[set, dict, list[str]]:
    """
    Ingest a list of PDFs. Returns (copied_ids, pdf_names, log_lines).
    """
    log_lines = []
    copied = 0
    skipped_exists = 0
    matched_existing = 0
    unmatched = 0
    errors = 0
    copied_ids: set = set()
    pdf_names: dict = {}

    print(f"\n{'=' * 70}")
    print(f"  Source: {label}")
    print(f"  PDFs: {len(pdf_paths)}")
    print(f"{'=' * 70}")

    for pdf_path in pdf_paths:
        row, method = match_pdf(pdf_path, doi_lookup, author_year_lookup, all_rows)

        if row is None:
            unmatched += 1
            log_lines.append(f"UNMATCHED: {pdf_path.name} — {method}")
            print(f"  UNMATCHED: {pdf_path.name}")
            print(f"            Reason: {method}")
            continue

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
            pdf_names[lit_id] = f"{year_str}/{new_name}"
            log_lines.append(f"EXISTS: {year_str}/{new_name} (from {pdf_path.name}) [{method}]")
            print(f"  EXISTS: {pdf_path.name} → {year_str}/{new_name}")
            continue

        try:
            year_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, target)
            copied += 1
            copied_ids.add(lit_id)
            pdf_names[lit_id] = f"{year_str}/{new_name}"
            log_lines.append(f"COPIED: {pdf_path.name} → {year_str}/{new_name} [{method}]")
            print(f"  COPIED: {pdf_path.name}")
            print(f"      → {year_str}/{new_name}")
            print(f"      Method: {method}")
        except Exception as e:
            errors += 1
            log_lines.append(f"ERROR: {pdf_path.name} — {e}")
            print(f"  ERROR: {pdf_path.name} — {e}")

    print(f"\n  Summary for {label}:")
    print(f"    Copied (new):    {copied}")
    print(f"    Already existed: {skipped_exists}")
    print(f"    Unmatched:       {unmatched}")
    print(f"    Errors:          {errors}")
    print(f"    Total acquired:  {len(copied_ids)}")

    return copied_ids, pdf_names, log_lines


def main():
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("Loading database from viz_data.csv...")
    all_rows, doi_lookup, author_year_lookup = load_database()
    print(f"  {len(all_rows):,} papers loaded, {len(doi_lookup):,} with DOIs")

    # --- Source 1: Elena's papers ---
    elena_pdfs = sorted(ELENA_DIR.glob("*.pdf"))
    elena_ids, elena_names, elena_log = ingest_source(
        "Elena's papers", elena_pdfs, doi_lookup, author_year_lookup, all_rows
    )

    # --- Source 2: Today's downloads ---
    download_pdfs = []
    for fname in DOWNLOADS_FILES:
        p = DOWNLOADS_DIR / fname
        if p.exists():
            download_pdfs.append(p)
        else:
            print(f"  WARNING: not found: {p}")
    dl_ids, dl_names, dl_log = ingest_source(
        "Today's Downloads", download_pdfs, doi_lookup, author_year_lookup, all_rows
    )

    # --- Combine and update tracking ---
    all_ids = elena_ids | dl_ids
    all_names = {**elena_names, **dl_names}

    print(f"\n{'=' * 70}")
    print("Updating tracking systems...")
    n_json = update_papers_data_json(all_ids, timestamp, "Elena + Downloads ingest")
    print(f"  papers_data.json: {n_json} entries removed (no longer missing)")
    update_tracking_dbs(all_ids, all_names, timestamp, "Elena + Downloads ingest")

    # --- Write log ---
    log_content = (
        f"Elena & Downloads PDF Ingest Log\n"
        f"Date: {timestamp}\n"
        f"{'=' * 70}\n\n"
        f"Elena's papers ({len(elena_pdfs)} PDFs):\n"
        f"  Acquired: {len(elena_ids)}\n\n"
        f"Today's Downloads ({len(download_pdfs)} PDFs):\n"
        f"  Acquired: {len(dl_ids)}\n\n"
        f"Total acquired: {len(all_ids)}\n"
        f"papers_data.json entries removed: {n_json}\n"
        f"\n{'=' * 70}\n\nElena details:\n"
    )
    with open(LOG_FILE, "w") as f:
        f.write(log_content)
        for line in elena_log:
            f.write(line + "\n")
        f.write(f"\n{'=' * 70}\n\nDownloads details:\n")
        for line in dl_log:
            f.write(line + "\n")

    print(f"\n{'=' * 70}")
    print("INGEST COMPLETE")
    print(f"  Total acquired: {len(all_ids)}")
    print(f"  Log: {LOG_FILE}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
