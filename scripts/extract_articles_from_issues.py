#!/usr/bin/env python3
"""Extract individual articles from journal issue/book PDFs.

Reads detection results from outputs/articles_in_issues.xlsx and extracts
the relevant page ranges using pikepdf.  Only processes rows where:
  - year >= 2000
  - confidence == "high"
  - 2 <= article_pages <= 40

Safety: writes to a temp file first, verifies size > 10 KB, then replaces
the original.  Logs every operation to outputs/article_extraction_log.csv.
"""

import csv
import os
import shutil
import tempfile
from pathlib import Path

import openpyxl
import pikepdf

PROJECT = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
XLSX_PATH = PROJECT / "outputs" / "articles_in_issues.xlsx"
LOG_PATH = PROJECT / "outputs" / "article_extraction_log.csv"

MIN_OUTPUT_KB = 10  # minimum acceptable extracted-file size


def load_qualifying_rows():
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        year, filename, total_pages, art_start, art_end, art_pages, confidence, _ = row
        if (year is not None
                and int(year) >= 2000
                and confidence == "high"
                and art_pages is not None
                and 2 <= int(art_pages) <= 40):
            rows.append({
                "year": int(year),
                "filename": filename,
                "total_pdf_pages": int(total_pages),
                "article_start": int(art_start),
                "article_end": int(art_end),
                "article_pages": int(art_pages),
            })
    wb.close()
    return rows


def extract_pages(src_path: Path, start: int, end: int, dst_path: Path):
    """Extract pages [start, end] (1-indexed) from src_path into dst_path."""
    with pikepdf.open(src_path) as src:
        dst = pikepdf.new()
        for i in range(start - 1, end):  # 0-indexed
            dst.pages.append(src.pages[i])
        dst.save(dst_path)


def main():
    rows = load_qualifying_rows()
    print(f"Qualifying rows: {len(rows)}")

    log_rows = []
    total_original_kb = 0
    total_new_kb = 0
    success = 0
    skipped = 0
    errors = 0

    for r in rows:
        year = r["year"]
        fname = r["filename"]
        src = PDF_BASE / str(year) / fname
        entry = {
            "year": year,
            "filename": fname,
            "original_pages": None,
            "extracted_start": r["article_start"],
            "extracted_end": r["article_end"],
            "extracted_pages": r["article_pages"],
            "original_size_kb": None,
            "new_size_kb": None,
            "status": "",
        }

        # --- existence check ---
        if not src.exists():
            entry["status"] = "error: file not found"
            log_rows.append(entry)
            errors += 1
            print(f"  SKIP (not found): {src}")
            continue

        orig_size = src.stat().st_size
        entry["original_size_kb"] = round(orig_size / 1024, 1)

        # --- page-count check ---
        try:
            with pikepdf.open(src) as pdf:
                actual_pages = len(pdf.pages)
        except Exception as exc:
            entry["status"] = f"error: cannot open ({exc})"
            log_rows.append(entry)
            errors += 1
            print(f"  SKIP (open error): {fname}: {exc}")
            continue

        entry["original_pages"] = actual_pages

        if actual_pages != r["total_pdf_pages"]:
            entry["status"] = (
                f"error: page count mismatch (expected {r['total_pdf_pages']}, "
                f"got {actual_pages})"
            )
            log_rows.append(entry)
            errors += 1
            print(f"  SKIP (page mismatch): {fname} expected {r['total_pdf_pages']} got {actual_pages}")
            continue

        if r["article_end"] > actual_pages:
            entry["status"] = "error: article_end exceeds page count"
            log_rows.append(entry)
            errors += 1
            print(f"  SKIP (end > pages): {fname}")
            continue

        # --- extract to temp ---
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf", dir=src.parent)
            os.close(fd)
            extract_pages(src, r["article_start"], r["article_end"], Path(tmp_path))
        except Exception as exc:
            entry["status"] = f"error: extraction failed ({exc})"
            log_rows.append(entry)
            errors += 1
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            print(f"  ERROR (extract): {fname}: {exc}")
            continue

        # --- verify temp ---
        new_size = os.path.getsize(tmp_path)
        new_kb = round(new_size / 1024, 1)

        if new_kb < MIN_OUTPUT_KB:
            entry["status"] = f"error: extracted too small ({new_kb} KB)"
            entry["new_size_kb"] = new_kb
            log_rows.append(entry)
            errors += 1
            os.remove(tmp_path)
            print(f"  ERROR (too small): {fname}: {new_kb} KB")
            continue

        # --- replace original ---
        try:
            shutil.move(tmp_path, str(src))
        except Exception as exc:
            entry["status"] = f"error: replace failed ({exc})"
            entry["new_size_kb"] = new_kb
            log_rows.append(entry)
            errors += 1
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            print(f"  ERROR (replace): {fname}: {exc}")
            continue

        entry["new_size_kb"] = new_kb
        entry["status"] = "success"
        log_rows.append(entry)
        success += 1
        total_original_kb += entry["original_size_kb"]
        total_new_kb += new_kb
        saved_mb = round((entry["original_size_kb"] - new_kb) / 1024, 1)
        print(f"  OK  {fname}  {entry['original_size_kb']:.0f} -> {new_kb:.0f} KB  (saved {saved_mb} MB)")

    # --- write log ---
    fieldnames = [
        "year", "filename", "original_pages", "extracted_start",
        "extracted_end", "extracted_pages", "original_size_kb",
        "new_size_kb", "status",
    ]
    with open(LOG_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(log_rows)

    # --- summary ---
    saved_kb = total_original_kb - total_new_kb
    print("\n===== SUMMARY =====")
    print(f"Total qualifying rows : {len(rows)}")
    print(f"Successful extractions: {success}")
    print(f"Errors / skipped      : {errors}")
    print(f"Total original size   : {total_original_kb/1024:.1f} MB")
    print(f"Total new size        : {total_new_kb/1024:.1f} MB")
    print(f"Disk space saved      : {saved_kb/1024:.1f} MB")
    print(f"Log written to        : {LOG_PATH}")


if __name__ == "__main__":
    main()
