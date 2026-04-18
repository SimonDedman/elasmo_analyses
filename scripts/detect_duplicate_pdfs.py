#!/usr/bin/env python3
"""Detect likely duplicate PDFs in SharkPapers library.

Three detection passes:
  1. Same (author, year) — multiple files for one author+year
  2. Adjacent years (year±1) — same author, year off by one
  3. Year-mismatched files — filename year ≠ folder year

For each candidate pair, compares filename title words (Jaccard) and,
when borderline, extracts first-page text for DOI and content overlap.

Output: outputs/duplicate_pdf_candidates.xlsx
"""

import re
import subprocess
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
OUTPUT = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
              "/outputs/duplicate_pdf_candidates.xlsx")


# ---------------------------------------------------------------------------
# Name normalisation (mirrors extract_schema_columns.py)
# ---------------------------------------------------------------------------

def _normalise_name(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().replace("-", "").replace(" ", "").replace("'", "").replace("ʼ", "")


def _extract_surname(stem: str) -> str:
    """Extract and normalise the author surname from a filename stem."""
    parts = stem.split(".")
    if len(parts) >= 2:
        return _normalise_name(parts[0])
    # Underscore-separated (SR numeric prefix: 12345_Author_Year)
    uparts = stem.split("_")
    if len(uparts) >= 2 and uparts[0].isdigit():
        return _normalise_name(uparts[1])
    return _normalise_name(uparts[0])


def _extract_file_year(stem: str) -> int | None:
    """Extract the year from a filename (not the folder)."""
    m = re.search(r"(?:^|[._])(\d{4})(?:[._]|$)", stem)
    return int(m.group(1)) if m else None


def _file_title_words(stem: str) -> set[str]:
    """Extract title words from a PDF filename stem."""
    parts = stem.split(".")
    # Remove surname, "etal"/"et"/"al", year digits
    title_parts = [p for p in parts
                   if p.lower() not in ("etal", "et", "al")
                   and not p.isdigit()]
    # Skip the first part (surname)
    if len(title_parts) > 1:
        title_parts = title_parts[1:]
    words = set()
    for p in title_parts:
        words |= set(re.findall(r"[a-z]{3,}", p.lower()))
    # Also try space/underscore-separated filenames
    for p in stem.split("_"):
        if not p.isdigit() and len(p) >= 3:
            words |= set(re.findall(r"[a-z]{3,}", p.lower()))
    return words


# ---------------------------------------------------------------------------
# First-page text extraction (for DOI + title confirmation)
# ---------------------------------------------------------------------------

_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s]+", re.IGNORECASE)

# Cache to avoid re-extracting the same file across passes
_PAGE_CACHE: dict[Path, str] = {}


def _extract_first_page(pdf_path: Path) -> str:
    """Extract text from first page of a PDF (cached)."""
    if pdf_path in _PAGE_CACHE:
        return _PAGE_CACHE[pdf_path]
    try:
        result = subprocess.run(
            ["pdftotext", "-l", "1", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=15,
        )
        text = result.stdout
    except Exception:
        text = ""
    _PAGE_CACHE[pdf_path] = text
    return text


def _extract_doi(text: str) -> str | None:
    """Find first DOI in text."""
    m = _DOI_RE.search(text)
    if m:
        doi = m.group(0).rstrip(".,;:)")
        return doi.lower()
    return None


def _first_page_title_words(text: str) -> set[str]:
    """Extract likely title words from first ~500 chars of page 1."""
    chunk = text[:500].lower()
    chunk = re.sub(r"(original|research|article|paper|short communication)\s*", "", chunk)
    words = set(re.findall(r"[a-z]{4,}", chunk))
    return words


# ---------------------------------------------------------------------------
# Corrigendum flag
# ---------------------------------------------------------------------------

_CORRIGENDUM_RE = re.compile(
    r"corrig|erratum|errata|correction\s+(?:to|for)", re.IGNORECASE
)

_SM_RE = re.compile(
    r"supplementary\s+(material|information|data|table|figure|file|document)"
    r"|supporting\s+(information|material|data|online)"
    r"|electronic\s+supplementary"
    r"|online\s+resource"
    r"|\bfigure\s+s\d"
    r"|\btable\s+s\d",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Core pair-comparison logic
# ---------------------------------------------------------------------------

def _evaluate_pair(
    p1: Path, p2: Path, source: str
) -> dict | None:
    """Compare two PDFs and return a row dict if they look like duplicates."""
    w1 = _file_title_words(p1.stem)
    w2 = _file_title_words(p2.stem)

    # Filename-based Jaccard
    union = w1 | w2
    jaccard = len(w1 & w2) / len(union) if union else 0.0

    # Decide whether to do content check
    few_words = len(w1) <= 2 or len(w2) <= 2
    needs_content = jaccard > 0.3 or few_words

    doi1 = doi2 = None
    content_jaccard = None
    doi_match = None

    if needs_content:
        text1 = _extract_first_page(p1)
        text2 = _extract_first_page(p2)
        doi1 = _extract_doi(text1)
        doi2 = _extract_doi(text2)
        doi_match = (doi1 is not None and doi2 is not None
                     and doi1 == doi2)

        ct1 = _first_page_title_words(text1)
        ct2 = _first_page_title_words(text2)
        ct_union = ct1 | ct2
        content_jaccard = (len(ct1 & ct2) / len(ct_union)
                           if ct_union else 0.0)

    # If both files have DOIs but they differ → different papers
    doi_mismatch = (doi1 is not None and doi2 is not None
                    and doi1 != doi2)
    if doi_mismatch:
        return None

    # Determine confidence level
    if doi_match:
        confidence = "confirmed"
    elif jaccard >= 0.8:
        confidence = "very_likely"
    elif content_jaccard is not None and content_jaccard > 0.5:
        confidence = "likely"
    elif jaccard >= 0.5:
        confidence = "possible"
    elif few_words and content_jaccard is not None and content_jaccard > 0.3:
        confidence = "possible"
    else:
        return None

    is_corrigendum = bool(
        _CORRIGENDUM_RE.search(p1.stem) or _CORRIGENDUM_RE.search(p2.stem)
    )

    # Detect supplementary material: one file is SM, the other is the
    # main paper.  Both share the same DOI but should both be kept.
    if needs_content:
        sm1 = bool(_SM_RE.search(text1[:1500]))
        sm2 = bool(_SM_RE.search(text2[:1500]))
    else:
        # If we didn't extract text above, do it now for SM check
        sm1 = bool(_SM_RE.search(_extract_first_page(p1)[:1500]))
        sm2 = bool(_SM_RE.search(_extract_first_page(p2)[:1500]))
    is_sm_pair = sm1 != sm2  # exactly one is supplementary

    s1 = p1.stat().st_size
    s2 = p2.stat().st_size
    surname = _extract_surname(p1.stem)

    return {
        "author": surname,
        "year_1": int(p1.parent.name) if p1.parent.name.isdigit() else None,
        "year_2": int(p2.parent.name) if p2.parent.name.isdigit() else None,
        "source": source,
        "confidence": confidence,
        "corrigendum_pair": is_corrigendum,
        "sm_pair": is_sm_pair,
        "filename_jaccard": round(jaccard, 3),
        "content_jaccard": round(content_jaccard, 3) if content_jaccard is not None else None,
        "doi_match": doi_match,
        "doi_1": doi1,
        "doi_2": doi2,
        "file_1": p1.name,
        "size_1_kb": round(s1 / 1024, 1),
        "file_2": p2.name,
        "size_2_kb": round(s2 / 1024, 1),
        "size_ratio": round(max(s1, s2) / min(s1, s2), 2) if min(s1, s2) > 0 else None,
        "keep_recommendation": p1.name if s1 >= s2 else p2.name,
        "remove_recommendation": p2.name if s1 >= s2 else p1.name,
        "path_1": str(p1),
        "path_2": str(p2),
    }


# ---------------------------------------------------------------------------
# Build index and detect duplicates
# ---------------------------------------------------------------------------

def build_pdf_index() -> dict[tuple[str, int], list[Path]]:
    """Index PDFs by (normalised_surname, folder_year)."""
    index: dict[tuple[str, int], list[Path]] = defaultdict(list)
    for year_dir in sorted(PDF_BASE.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        for pdf in year_dir.glob("*.pdf"):
            surname = _extract_surname(pdf.stem)
            index[(surname, year)].append(pdf)
    return dict(index)


def detect_duplicates() -> pd.DataFrame:
    """Find likely duplicate pairs across the library."""
    index = build_pdf_index()

    print(f"Total (author, year) keys: {len(index)}")
    print(f"Keys with 2+ PDFs: {sum(1 for v in index.values() if len(v) > 1)}")

    rows = []
    seen_pairs: set[tuple[str, str]] = set()  # avoid reporting same pair twice

    def _add_pair(p1: Path, p2: Path, source: str) -> None:
        key = tuple(sorted([str(p1), str(p2)]))
        if key in seen_pairs:
            return
        row = _evaluate_pair(p1, p2, source)
        if row is not None:
            seen_pairs.add(key)
            rows.append(row)

    # --- Pass 1: same (author, year) ---
    print("Pass 1: same author+year ...")
    for (surname, year), paths in sorted(index.items()):
        if len(paths) < 2:
            continue
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                _add_pair(paths[i], paths[j], "same_year")

    print(f"  candidates after pass 1: {len(rows)}")

    # --- Pass 2: adjacent years (year±1) ---
    print("Pass 2: adjacent years (year±1) ...")
    all_keys = set(index.keys())
    for (surname, year), paths in sorted(index.items()):
        for delta in (-1, +1):
            adj_key = (surname, year + delta)
            if adj_key not in all_keys:
                continue
            adj_paths = index[adj_key]
            for p1 in paths:
                for p2 in adj_paths:
                    _add_pair(p1, p2, "year_pm1")

    print(f"  candidates after pass 2: {len(rows)}")

    # --- Pass 3: year-mismatched files (filename year ≠ folder year) ---
    print("Pass 3: year-mismatched files ...")
    for (surname, year), paths in sorted(index.items()):
        for p in paths:
            file_year = _extract_file_year(p.stem)
            if file_year is not None and file_year != year:
                # Look for files in the correct year folder
                correct_key = (surname, file_year)
                if correct_key in index:
                    for p2 in index[correct_key]:
                        _add_pair(p, p2, "year_mismatch")

    print(f"  candidates after pass 3: {len(rows)}")
    print(f"Content checks performed: {len(_PAGE_CACHE)}")

    df = pd.DataFrame(rows)
    if not df.empty:
        conf_order = ["confirmed", "very_likely", "likely", "possible"]
        df["confidence"] = pd.Categorical(
            df["confidence"], categories=conf_order, ordered=True
        )
        df = df.sort_values(
            ["confidence", "source", "author", "year_1"]
        ).reset_index(drop=True)

    return df


def main() -> None:
    df = detect_duplicates()

    if df.empty:
        print("No duplicate candidates found.")
        return

    # Summary
    print(f"\n{'='*60}")
    print(f"Duplicate candidates found: {len(df)}")
    print("\nBy confidence:")
    for conf in ["confirmed", "very_likely", "likely", "possible"]:
        n = (df["confidence"] == conf).sum()
        if n:
            print(f"  {conf}: {n}")
    print("\nBy source:")
    for src in ["same_year", "year_pm1", "year_mismatch"]:
        n = (df["source"] == src).sum()
        if n:
            print(f"  {src}: {n}")

    wasted_kb = df.apply(
        lambda r: min(r["size_1_kb"], r["size_2_kb"]), axis=1
    ).sum()
    print(f"\nEstimated recoverable disk space: {wasted_kb / 1024:.1f} MB")

    # Write XLSX
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="duplicates", index=False)

        from openpyxl.styles import Font

        ws = writer.sheets["duplicates"]
        # Freeze top row, bold headers, autofilter
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = Font(bold=True)
        # Auto-fit column widths
        for col_idx, col_name in enumerate(df.columns, 1):
            max_len = max(
                len(str(col_name)),
                df[col_name].astype(str).str.len().max() if len(df) else 0,
            )
            ws.column_dimensions[ws.cell(1, col_idx).column_letter].width = min(
                max_len + 2, 60
            )

    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    main()
