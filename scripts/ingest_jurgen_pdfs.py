#!/usr/bin/env python3
"""
Ingest PDFs from Jürgen's Shark-References NAS export.

Copies PDFs named {literature_id}.pdf into the SharkPapers library
with standardised naming: {Author}.etal.{Year}.{Abbreviated title}.pdf
inside year subdirectories.

Also updates tracking systems:
  - docs/papers_data.json (web interface status)
  - database/download_tracker.db (download_status table)
  - outputs/download_queue.db (download_queue table)

No destructive operations — copies only, originals stay on source drive.
"""

import json
import pandas as pd
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOURCE_DIR = Path("/media/simon/UBUNTU 25_0/EEA_export/")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PROJECT = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PARQUET = PROJECT / "outputs/literature_review_enriched.parquet"
LOG_DIR = PROJECT / "logs"
LOG_FILE = LOG_DIR / "jurgen_ingest_log.txt"

# Tracking files
PAPERS_DATA_JSON = PROJECT / "docs/papers_data.json"
DOWNLOAD_TRACKER_DB = PROJECT / "database/download_tracker.db"
DOWNLOAD_QUEUE_DB = PROJECT / "outputs/download_queue.db"


def clean_for_filename(text: str, max_len: int = 50) -> str:
    """Sanitise text for use in a filename."""
    if not text or pd.isna(text):
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
    if not authors or pd.isna(authors):
        return "Unknown"
    authors = str(authors).strip()
    # Split by & first, then take first part
    first = re.split(r'\s*&\s*', authors)[0].strip()
    # Remove year in parentheses
    first = re.sub(r'\(\d{4}\)', '', first).strip()
    # If comma format: "Smith, J." → "Smith"
    if ',' in first:
        return clean_for_filename(first.split(',')[0], max_len=20)
    # Space format: "John Smith" → "Smith"
    parts = first.split()
    return clean_for_filename(parts[-1] if parts else "Unknown", max_len=20)


def has_multiple_authors(authors: str) -> bool:
    """Check if there are multiple authors."""
    if not authors or pd.isna(authors):
        return False
    return '&' in str(authors)


def build_filename(row) -> str:
    """Build filename in library convention: Author.etal.Year.Title.pdf"""
    author = extract_first_author(row["authors"])
    year = int(row["year"]) if pd.notna(row["year"]) else 0
    year_str = str(year) if year > 0 else "Unknown"
    title = clean_for_filename(row["title"], max_len=60)

    if has_multiple_authors(row["authors"]):
        return f"{author}.etal.{year_str}.{title}.pdf"
    else:
        return f"{author}.{year_str}.{title}.pdf"


def update_papers_data_json(copied_ids: set[int], timestamp: str) -> int:
    """Update docs/papers_data.json — set status to 'downloaded' for copied papers."""
    if not PAPERS_DATA_JSON.exists():
        return 0

    with open(PAPERS_DATA_JSON) as f:
        data = json.load(f)

    # literature_id in JSON is stored as "12345.0" string format
    id_lookup = {f"{lid}.0" for lid in copied_ids}

    updated = 0
    for entry in data:
        lit_id = str(entry.get("literature_id", ""))
        if lit_id in id_lookup:
            entry["last_status"] = "downloaded"
            entry["notes"] = f"Shark-References NAS (Jürgen) {timestamp}"
            updated += 1

    with open(PAPERS_DATA_JSON, "w") as f:
        json.dump(data, f, indent=2)

    return updated


def update_download_tracker_db(copied_ids: set[int], pdf_names: dict[int, str], timestamp: str) -> int:
    """Update database/download_tracker.db — add download_status entries."""
    if not DOWNLOAD_TRACKER_DB.exists():
        return 0

    db = sqlite3.connect(str(DOWNLOAD_TRACKER_DB))

    # Get paper_id mapping from papers table
    rows = db.execute("SELECT id, literature_id FROM papers").fetchall()
    lit_to_paper_id = {}
    for pid, lid in rows:
        try:
            lid_int = int(float(lid))
            lit_to_paper_id[lid_int] = pid
        except (ValueError, TypeError):
            continue

    inserted = 0
    for lit_id in copied_ids:
        paper_id = lit_to_paper_id.get(lit_id)
        if paper_id is None:
            continue
        # Check if already has a 'downloaded' status
        existing = db.execute(
            "SELECT id FROM download_status WHERE paper_id = ? AND status = 'downloaded'",
            (paper_id,)
        ).fetchone()
        if existing:
            continue
        db.execute(
            "INSERT INTO download_status (paper_id, status, download_date, source, notes, attempts, last_attempt) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (paper_id, "downloaded", timestamp, "Shark-References NAS",
             f"Jürgen bulk export; filed as {pdf_names.get(lit_id, 'unknown')}", 1, timestamp)
        )
        inserted += 1

    db.commit()
    db.close()
    return inserted


def update_download_queue_db(copied_ids: set[int], pdf_names: dict[int, str], timestamp: str) -> int:
    """Update outputs/download_queue.db — set status to 'success' for copied papers."""
    if not DOWNLOAD_QUEUE_DB.exists():
        return 0

    db = sqlite3.connect(str(DOWNLOAD_QUEUE_DB))

    updated = 0
    for lit_id in copied_ids:
        # literature_id stored as string in this DB
        for fmt in [str(lit_id), f"{lit_id}.0"]:
            result = db.execute(
                "UPDATE download_queue SET status = 'success', download_timestamp = ?, pdf_path = ? WHERE literature_id = ? AND status != 'success'",
                (timestamp, pdf_names.get(lit_id, ""), fmt)
            )
            updated += result.rowcount

    db.commit()
    db.close()
    return updated


def main():
    LOG_DIR.mkdir(exist_ok=True)
    log_lines: list[str] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("Loading metadata from parquet...")
    df = pd.read_parquet(PARQUET, columns=["literature_id", "authors", "year", "title"])
    df["lit_id_int"] = pd.to_numeric(df["literature_id"], errors="coerce")

    # Build lookup: literature_id (int) → row
    meta = {}
    for _, row in df.dropna(subset=["lit_id_int"]).iterrows():
        meta[int(row["lit_id_int"])] = row
    print(f"  Loaded metadata for {len(meta):,} papers")

    # Scan source PDFs
    source_pdfs = sorted(SOURCE_DIR.glob("*.pdf"))
    print(f"  Found {len(source_pdfs):,} PDFs in source directory")

    copied = 0
    skipped_exists = 0
    skipped_no_meta = 0
    errors = 0
    copied_ids: set[int] = set()
    pdf_names: dict[int, str] = {}  # lit_id → filename for tracking

    for pdf in source_pdfs:
        if not pdf.stem.isdigit():
            log_lines.append(f"SKIP_NON_ID: {pdf.name}")
            continue

        lit_id = int(pdf.stem)
        row = meta.get(lit_id)

        if row is None:
            skipped_no_meta += 1
            log_lines.append(f"NO_META: {pdf.name} — literature_id not in database")
            continue

        # Build target path
        year = int(row["year"]) if pd.notna(row["year"]) else 0
        year_str = str(year) if year > 0 else "Unknown"
        new_name = build_filename(row)
        year_dir = PDF_BASE / year_str
        target = year_dir / new_name

        # Handle collision
        if target.exists():
            skipped_exists += 1
            log_lines.append(f"EXISTS: {year_str}/{new_name}")
            # Still record as acquired for tracking
            copied_ids.add(lit_id)
            pdf_names[lit_id] = f"{year_str}/{new_name}"
            continue

        try:
            year_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf, target)
            copied += 1
            copied_ids.add(lit_id)
            pdf_names[lit_id] = f"{year_str}/{new_name}"
            log_lines.append(f"COPIED: {pdf.name} → {year_str}/{new_name}")
            if copied % 200 == 0:
                print(f"  Copied {copied:,}...")
        except Exception as e:
            errors += 1
            log_lines.append(f"ERROR: {pdf.name} — {e}")

    # --- Update tracking systems ---
    print("\nUpdating tracking systems...")

    n_json = update_papers_data_json(copied_ids, timestamp)
    print(f"  papers_data.json: {n_json:,} entries updated")

    n_tracker = update_download_tracker_db(copied_ids, pdf_names, timestamp)
    print(f"  download_tracker.db: {n_tracker:,} status rows inserted")

    n_queue = update_download_queue_db(copied_ids, pdf_names, timestamp)
    print(f"  download_queue.db: {n_queue:,} rows updated to 'success'")

    # Write log
    summary = (
        f"Jürgen PDF Ingest Log\n"
        f"Date: {timestamp}\n"
        f"Source: {SOURCE_DIR}\n"
        f"{'=' * 70}\n\n"
        f"Summary:\n"
        f"  Source PDFs:               {len(source_pdfs):,}\n"
        f"  Copied (new):              {copied:,}\n"
        f"  Already existed:           {skipped_exists:,}\n"
        f"  No metadata:               {skipped_no_meta:,}\n"
        f"  Errors:                    {errors:,}\n"
        f"  Total acquired:            {len(copied_ids):,}\n\n"
        f"Tracking updates:\n"
        f"  papers_data.json:          {n_json:,} updated\n"
        f"  download_tracker.db:       {n_tracker:,} inserted\n"
        f"  download_queue.db:         {n_queue:,} updated\n"
        f"\n{'=' * 70}\n\nDetails:\n"
    )
    with open(LOG_FILE, "w") as f:
        f.write(summary)
        for line in log_lines:
            f.write(line + "\n")

    print(f"\n{'=' * 70}")
    print(f"INGEST COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Copied (new):        {copied:,}")
    print(f"  Already existed:     {skipped_exists:,}")
    print(f"  No metadata:         {skipped_no_meta:,}")
    print(f"  Errors:              {errors:,}")
    print(f"  Total acquired:      {len(copied_ids):,}")
    print(f"  Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
