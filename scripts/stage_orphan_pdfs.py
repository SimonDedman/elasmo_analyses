#!/usr/bin/env python3
"""
Stage orphan PDFs into the master CSV before Shark References indexes them.

Use case: a coauthor delivers a recent paper (e.g. 2025/2026 Frontiers article)
that hasn't yet been crawled by Shark References. Without this script, the PDF
sits unmatched in the source folder for weeks until the monthly SR sync
catches up. With this script, we fetch the bibliographic metadata from
Crossref by DOI (or by title+author fallback), append a new row to the
master CSV in `outputs/shark_references_bulk/`, and file the PDF normally
into `SharkPapers/{year}/`. The next full extraction run picks the new
entries up automatically.

Matching chain (per orphan PDF):
  1. Extract DOI from PDF text (reuse ingest_pdfs.py logic).
  2. If DOI present:
     a. If already in parquet  → file PDF normally (delegate to ingest_pdfs).
     b. Else                   → fetch Crossref metadata, queue new entry.
  3. If no DOI extractable:
     a. Extract title + author candidates from PDF first page.
     b. Search Crossref by title+author for top hit.
     c. If hit's DOI is in parquet → delegate to ingest_pdfs.
        Else                       → queue new entry.

New entries get literature_id in the 600000+ range (separate from the
500001-502293 range used for SR-without-IDs papers). The next SR sync's
diff-by-DOI step (sync_shark_references.py:826) will see the DOI as
"known" and skip duplication.

Usage:
    python scripts/stage_orphan_pdfs.py /path/to/orphans/
    python scripts/stage_orphan_pdfs.py file1.pdf file2.pdf
    python scripts/stage_orphan_pdfs.py --check /path/to/orphans/
    python scripts/stage_orphan_pdfs.py --no-network /path/to/orphans/  # offline test
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# Reuse the existing ingest pipeline's helpers
sys.path.insert(0, str(Path(__file__).parent))
from ingest_pdfs import (  # noqa: E402
    PDF_BASE,
    build_filename,
    ensure_text_extractable,
    extract_doi_from_pdf,
    extract_text_for_matching,
    load_database,
    normalise_doi,
    strip_accents,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
ENRICHED_PARQUET = PROJECT_ROOT / "outputs/literature_review_enriched.parquet"
MASTER_CSV_DIR = PROJECT_ROOT / "outputs/shark_references_bulk"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "stage_orphan_pdfs_log.txt"

# Literature_id range for orphan-staged entries (avoids collision with
# SR-native [<500001] and SR-without-ID [500001-502293] ranges).
ORPHAN_ID_BASE = 600000

CROSSREF_API = "https://api.crossref.org/works"
CROSSREF_TIMEOUT = 15
CROSSREF_DELAY = 1.0  # polite pause between API calls
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "SharkResearchBot/1.0 (mailto:simondedman@gmail.com)"
)

# Master CSV columns (must match shark_references_complete_*.csv exactly)
MASTER_COLUMNS = [
    "year", "authors", "citation", "findspot", "doi", "full_text",
    "literature_id", "pdf_url", "title",
    "keyword_time", "described_species", "described_genus", "abstract",
    "keyword_place", "new_descriptions_species", "new_description_genus",
    "described_families", "described_parasites",
    "new_descriptions_parasites", "new_descriptions_family",
]


# ---------------------------------------------------------------------------
# Crossref lookups
# ---------------------------------------------------------------------------

def crossref_by_doi(doi: str) -> dict | None:
    """Fetch a Crossref work record by DOI. Returns the message dict or None."""
    if not doi:
        return None
    url = f"{CROSSREF_API}/{requests.utils.quote(doi, safe='')}"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT},
                         timeout=CROSSREF_TIMEOUT)
        if r.status_code == 200:
            return r.json().get("message")
        if r.status_code == 404:
            return None
    except requests.RequestException as e:
        print(f"  Crossref DOI error: {e}")
    return None


def crossref_search(title: str, author_surname: str = "",
                    year: str = "") -> dict | None:
    """Search Crossref by title (and optional author/year). Returns top match."""
    if not title or len(title) < 10:
        return None
    params = {"query.title": title[:200], "rows": 5}
    if author_surname:
        params["query.author"] = author_surname
    if year:
        params["filter"] = f"from-pub-date:{year},until-pub-date:{year}"
    try:
        r = requests.get(CROSSREF_API, params=params,
                         headers={"User-Agent": USER_AGENT},
                         timeout=CROSSREF_TIMEOUT)
        if r.status_code != 200:
            return None
        items = r.json().get("message", {}).get("items", [])
    except requests.RequestException as e:
        print(f"  Crossref search error: {e}")
        return None

    # Score each candidate by title-word overlap; demand >=70% coverage.
    qwords = set(re.findall(r"[a-z]{4,}", title.lower()))
    if not qwords:
        return None
    best, best_score = None, 0.0
    for item in items:
        rt = (item.get("title") or [""])[0]
        rwords = set(re.findall(r"[a-z]{4,}", rt.lower()))
        if not rwords:
            continue
        score = len(qwords & rwords) / max(len(qwords), 1)
        if score > best_score:
            best_score = score
            best = item
    if best and best_score >= 0.7:
        return best
    return None


# ---------------------------------------------------------------------------
# Crossref → master CSV row
# ---------------------------------------------------------------------------

def _format_authors(crossref_authors: list[dict]) -> str:
    """Render a Crossref author list in the SR-style 'Surname, F. & Surname, F.' form."""
    parts = []
    for a in crossref_authors or []:
        family = a.get("family", "").strip()
        given = a.get("given", "").strip()
        if not family:
            continue
        # Reduce given name to initials (handles 'John Quincy' → 'J.Q.')
        initials = "".join(
            f"{tok[0]}." for tok in re.split(r"[\s\-]+", given) if tok
        )
        parts.append(f"{family}, {initials}".strip(", "))
    return " & ".join(parts)


def crossref_to_master_row(item: dict, lit_id: int) -> dict:
    """Convert a Crossref work record into a master-CSV row dict."""
    title = (item.get("title") or [""])[0].strip()
    container = (item.get("container-title") or [""])[0].strip()
    volume = item.get("volume", "").strip() if item.get("volume") else ""
    issue = item.get("issue", "").strip() if item.get("issue") else ""
    page = item.get("page", "").strip() if item.get("page") else ""
    article_number = item.get("article-number", "")
    doi = item.get("DOI", "").strip().lower()

    # Year: prefer published-print → published-online → issued
    year = ""
    for key in ("published-print", "published-online", "issued", "created"):
        d = item.get(key, {}).get("date-parts", [[None]])[0]
        if d and d[0]:
            year = str(d[0])
            break

    authors_str = _format_authors(item.get("author", []))
    if authors_str and year:
        authors_str = f"{authors_str} ({year})"

    # Build a citation in SR style — best-effort
    findspot_parts = []
    if container:
        findspot_parts.append(container)
    if volume:
        findspot_parts.append(volume)
    if issue:
        findspot_parts.append(f"({issue})")
    if page:
        findspot_parts.append(page)
    elif article_number:
        findspot_parts.append(f"Article {article_number}")
    findspot = ", ".join(findspot_parts)

    citation = f"{authors_str} {title}. {findspot}"
    if doi:
        citation += f" DOI: {doi}"

    full_text = (
        f"{authors_str} {title}. {findspot}. DOI: {doi}".strip()
        if doi else f"{authors_str} {title}. {findspot}".strip()
    )

    abstract = item.get("abstract", "") or ""
    # Strip JATS XML tags from Crossref abstracts
    abstract = re.sub(r"<[^>]+>", "", abstract).strip()

    return {
        "year": year,
        "authors": authors_str,
        "citation": citation,
        "findspot": findspot,
        "doi": doi,
        "full_text": full_text,
        "literature_id": str(lit_id),
        "pdf_url": "",
        "title": title,
        "keyword_time": "",
        "described_species": "",
        "described_genus": "",
        "abstract": abstract,
        "keyword_place": "",
        "new_descriptions_species": "",
        "new_description_genus": "",
        "described_families": "",
        "described_parasites": "",
        "new_descriptions_parasites": "",
        "new_descriptions_family": "",
    }


# ---------------------------------------------------------------------------
# Title/author extraction from PDF text (fallback when DOI absent)
# ---------------------------------------------------------------------------

def guess_title_and_author(pdf_text: str) -> tuple[str, str]:
    """Heuristic title + first-author surname extraction from page-1 text.

    The title is usually the first long-ish line block; the first author
    surname is the capitalised word preceding 'et al' or the first name
    in a list. Best-effort — returns empty strings on failure.
    """
    if not pdf_text or len(pdf_text) < 50:
        return "", ""

    # Take first ~1500 chars (top of page 1).
    head = pdf_text[:1500]

    # Title heuristic: longest contiguous block of capitalised/word lines
    # before any 'Abstract' / 'Introduction' marker.
    cut = re.search(r"\b(Abstract|Introduction|Summary|Keywords|ABSTRACT)\b",
                    head)
    if cut:
        head_for_title = head[:cut.start()]
    else:
        head_for_title = head

    # Pick consecutive lines longer than 20 chars as title body.
    lines = [l.strip() for l in head_for_title.splitlines() if l.strip()]
    title_lines: list[str] = []
    for ln in lines:
        if len(ln) < 20:
            if title_lines:
                break
            continue
        # Skip lines that are mostly digits / journal headers
        if re.search(r"\d{4}.*\d{4}", ln):
            continue
        if re.match(r"^(Vol|VOL|Volume|VOLUME|Issue|ISSUE|No\.|No |"
                    r"DOI|Received|Accepted|Published|Copyright|©)", ln):
            continue
        title_lines.append(ln)
        if sum(len(t) for t in title_lines) > 200:
            break
    title = " ".join(title_lines).strip()
    title = re.sub(r"\s+", " ", title)[:300]

    # Author heuristic: 'Surname et al' or first capitalised name
    # appearing after the title block.
    author = ""
    m = re.search(r"\b([A-Z][a-zA-ZÀ-ÿĀ-ſ\-']{2,})\s+et\s+al\.?",
                  head)
    if m:
        author = strip_accents(m.group(1)).lower()
    else:
        # Look for first 'Name, Initial.' pattern
        m = re.search(r"\b([A-Z][a-zA-ZÀ-ÿĀ-ſ\-']{2,}),\s*"
                      r"[A-Z]\.", head)
        if m:
            author = strip_accents(m.group(1)).lower()

    return title, author


# ---------------------------------------------------------------------------
# Main staging logic
# ---------------------------------------------------------------------------

def find_latest_master_csv() -> Path:
    """Locate the most recent master CSV (or create the dir if absent)."""
    MASTER_CSV_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(MASTER_CSV_DIR.glob("shark_references_complete_*.csv"),
                   key=lambda p: p.stat().st_mtime)
    if files:
        return files[-1]
    # Fresh start
    return MASTER_CSV_DIR / (
        f"shark_references_complete_{datetime.now():%Y%m%d}.csv"
    )


def next_orphan_id(existing_ids: set[int]) -> int:
    """Pick the next free literature_id in the 600000+ range."""
    candidate = ORPHAN_ID_BASE
    while candidate in existing_ids:
        candidate += 1
    return candidate


def file_pdf(pdf_src: Path, row: dict) -> Path | None:
    """Copy the PDF into SharkPapers/{year}/ with the standard filename.

    Returns the target path on success (or if it already exists), None on error.
    """
    new_name = build_filename(row)
    try:
        year_str = str(int(float(row["year"])))
    except (ValueError, TypeError):
        year_str = "Unknown"
    target = PDF_BASE / year_str / new_name
    if target.exists():
        print(f"  EXISTS: {year_str}/{new_name}")
        return target
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_src, target)
        print(f"  COPIED: {year_str}/{new_name}")
        return target
    except OSError as e:
        print(f"  ERROR copying: {e}")
        return None


def stage_orphan(pdf_path: Path, doi_lookup: dict, all_rows: list[dict],
                 existing_orphan_ids: set[int],
                 no_network: bool = False) -> dict | None:
    """Stage one orphan PDF. Returns the new master-CSV row dict, or None."""
    print(f"\n→ {pdf_path.name}")

    # Step 1: extract DOI from the PDF (with OCR fallback if necessary)
    text_path = ensure_text_extractable(pdf_path)
    doi = extract_doi_from_pdf(text_path)
    if doi:
        print(f"  DOI extracted: {doi}")
        nd = normalise_doi(doi)
        if nd in doi_lookup:
            print(f"  ALREADY IN DB → file normally (id={doi_lookup[nd]['literature_id']})")
            file_pdf(pdf_path, doi_lookup[nd])
            return None

    # Step 2: if no DOI, try title/author search
    if not doi:
        text = extract_text_for_matching(text_path)
        title_guess, author_guess = guess_title_and_author(text)
        if not title_guess:
            print("  FAIL: no DOI, no title extractable from PDF")
            return None
        print(f"  Title guess: {title_guess[:80]}")
        if no_network:
            print("  (--no-network; skipping Crossref search)")
            return None
        time.sleep(CROSSREF_DELAY)
        item = crossref_search(title_guess, author_guess)
        if not item:
            print("  FAIL: Crossref search returned no confident match")
            return None
        doi = item.get("DOI", "").strip().lower()
        print(f"  Crossref title search → DOI {doi}")
        nd = normalise_doi(doi)
        if nd in doi_lookup:
            print(f"  ALREADY IN DB → file normally")
            file_pdf(pdf_path, doi_lookup[nd])
            return None
    else:
        item = None

    # Step 3: fetch full Crossref metadata for the DOI (if not already)
    if no_network:
        print("  (--no-network; cannot stage without metadata)")
        return None
    if item is None:
        time.sleep(CROSSREF_DELAY)
        item = crossref_by_doi(doi)
    if not item:
        print(f"  FAIL: Crossref returned no record for {doi}")
        return None

    # Step 4: assign new orphan ID + build row
    new_id = next_orphan_id(existing_orphan_ids)
    existing_orphan_ids.add(new_id)
    row = crossref_to_master_row(item, new_id)
    if not row.get("year") or not row.get("title"):
        print(f"  FAIL: Crossref record incomplete (year={row.get('year')!r})")
        return None

    print(f"  STAGED: id={new_id} | {row['year']} | {row['authors'][:50]} | {row['title'][:60]}")

    # Step 5: file the PDF using the new row's metadata
    file_pdf(pdf_path, row)
    return row


def append_to_master_csv(new_rows: list[dict], log_lines: list[str]) -> Path:
    """Append staged rows to the latest master CSV (creating it if needed)."""
    master = find_latest_master_csv()
    if master.exists():
        df_existing = pd.read_csv(master, dtype=str)
    else:
        df_existing = pd.DataFrame(columns=MASTER_COLUMNS)

    df_new = pd.DataFrame(new_rows, columns=MASTER_COLUMNS).fillna("")

    # Dedupe by DOI against existing master CSV
    if "doi" in df_existing.columns:
        existing_dois = {normalise_doi(d)
                         for d in df_existing["doi"].dropna()} - {""}
        before = len(df_new)
        df_new = df_new[~df_new["doi"].apply(normalise_doi).isin(existing_dois)]
        skipped = before - len(df_new)
        if skipped:
            print(f"  Skipped {skipped} already-in-master DOIs")
            log_lines.append(f"DEDUP_MASTER: skipped {skipped} entries")

    if df_new.empty:
        print("  Nothing new to append to master CSV")
        return master

    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined.to_csv(master, index=False, encoding="utf-8")
    print(f"  Appended {len(df_new)} rows to {master.name}")
    log_lines.append(f"APPENDED: {len(df_new)} rows to {master.name}")
    return master


# ---------------------------------------------------------------------------
# Public API (also called from sync_shark_references.py Phase 0)
# ---------------------------------------------------------------------------

def stage_pdfs(pdf_paths: list[Path], no_network: bool = False) -> dict:
    """Stage a list of orphan PDFs end-to-end. Returns a stats dict.

    The dict contains: ``staged`` (rows appended to master CSV),
    ``filed_existing`` (PDFs matched to existing parquet entries),
    ``copied`` (PDFs newly copied to library), ``failed`` (orphans
    that could not be resolved), ``new_ids`` (literature_ids of newly
    staged rows — useful for incremental extraction afterwards),
    ``log_lines`` (per-PDF outcome strings).
    """
    stats = {
        "staged": 0, "filed_existing": 0, "copied": 0, "failed": 0,
        "new_ids": [], "log_lines": [],
    }
    if not pdf_paths:
        return stats

    all_rows, doi_lookup, _ = load_database()
    existing_orphan_ids = load_existing_orphan_ids()

    staged_rows: list[dict] = []
    for pdf in pdf_paths:
        row = stage_orphan(pdf, doi_lookup, all_rows,
                           existing_orphan_ids, no_network=no_network)
        if row:
            staged_rows.append(row)
            stats["new_ids"].append(row["literature_id"])
            stats["log_lines"].append(
                f"STAGED: {pdf.name} → id={row['literature_id']} "
                f"DOI={row['doi']} title={row['title'][:80]}"
            )
        else:
            stats["failed"] += 1
            stats["log_lines"].append(f"SKIPPED: {pdf.name}")

    if staged_rows:
        log_buf: list[str] = []
        append_to_master_csv(staged_rows, log_buf)
        stats["log_lines"].extend(log_buf)
        stats["staged"] = len(staged_rows)
    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def collect_pdfs(args: list[str]) -> list[Path]:
    """Resolve CLI args (files or directories) to a sorted list of PDF paths."""
    paths: list[Path] = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.pdf")))
            paths.extend(sorted(p.glob("*.PDF")))
        elif p.is_file() and p.suffix.lower() == ".pdf":
            paths.append(p)
    seen, unique = set(), []
    for p in paths:
        if p.resolve() in seen:
            continue
        seen.add(p.resolve())
        unique.append(p)
    return unique


def load_existing_orphan_ids() -> set[int]:
    """Find all literature_ids >= ORPHAN_ID_BASE already present anywhere."""
    used: set[int] = set()
    if ENRICHED_PARQUET.exists():
        df = pd.read_parquet(ENRICHED_PARQUET, columns=["literature_id"])
        for v in df["literature_id"].dropna().astype(str):
            try:
                n = int(float(v))
                if n >= ORPHAN_ID_BASE:
                    used.add(n)
            except (ValueError, TypeError):
                continue
    # Also scan latest master CSV (in case staging happened since last extract)
    master = find_latest_master_csv()
    if master.exists():
        try:
            df = pd.read_csv(master, dtype=str, usecols=["literature_id"])
            for v in df["literature_id"].dropna():
                try:
                    n = int(float(v))
                    if n >= ORPHAN_ID_BASE:
                        used.add(n)
                except (ValueError, TypeError):
                    continue
        except (ValueError, KeyError):
            pass
    return used


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage orphan PDFs (not yet in Shark References) into "
                    "the master CSV via Crossref metadata lookup.",
    )
    parser.add_argument("paths", nargs="+",
                        help="PDF files or directories of PDFs to stage")
    parser.add_argument("--check", action="store_true",
                        help="Dry run: report what would be staged, do not "
                        "modify the master CSV or copy PDFs")
    parser.add_argument("--no-network", action="store_true",
                        help="Skip Crossref calls (offline test of "
                        "DOI extraction and existing-DB matching only)")
    args = parser.parse_args()

    pdfs = collect_pdfs(args.paths)
    if not pdfs:
        print("No PDFs found.")
        return 0

    print(f"Loading database from viz_data.csv...")
    all_rows, doi_lookup, _author_year_lookup = load_database()
    print(f"  {len(all_rows):,} papers loaded, {len(doi_lookup):,} with DOIs")

    existing_orphan_ids = load_existing_orphan_ids()
    print(f"  Existing orphan IDs (>={ORPHAN_ID_BASE}): {len(existing_orphan_ids)}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\nStaging {len(pdfs)} orphan PDFs ({'CHECK' if args.check else 'LIVE'} mode)...")
    print("=" * 70)

    staged_rows: list[dict] = []
    for pdf in pdfs:
        if args.check:
            # Just diagnose — skip Crossref network and CSV writes.
            text_path = ensure_text_extractable(pdf)
            doi = extract_doi_from_pdf(text_path)
            print(f"\n→ {pdf.name}")
            if doi:
                nd = normalise_doi(doi)
                state = "in DB" if nd in doi_lookup else "NEW"
                print(f"  DOI: {doi}  ({state})")
            else:
                text = extract_text_for_matching(text_path)
                title, author = guess_title_and_author(text)
                print(f"  No DOI. Title guess: {title[:80] or '(none)'}")
                if author:
                    print(f"  Author guess: {author}")
            continue

        row = stage_orphan(pdf, doi_lookup, all_rows,
                           existing_orphan_ids, no_network=args.no_network)
        if row:
            staged_rows.append(row)
            log_lines.append(
                f"STAGED: {pdf.name} → id={row['literature_id']} "
                f"DOI={row['doi']} title={row['title'][:80]}"
            )
        else:
            log_lines.append(f"SKIPPED: {pdf.name}")

    if args.check or not staged_rows:
        if staged_rows:
            print(f"\nWould stage {len(staged_rows)} rows.")
        return 0

    print(f"\n{'=' * 70}")
    print(f"Appending {len(staged_rows)} staged rows to master CSV...")
    append_to_master_csv(staged_rows, log_lines)

    # Persist log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Stage Orphan PDFs Log\nDate: {timestamp}\n")
        f.write(f"Inputs: {[str(p) for p in args.paths]}\n")
        f.write(f"Staged: {len(staged_rows)}\n\n")
        for line in log_lines:
            f.write(line + "\n")

    print(f"\nLog: {LOG_FILE}")
    print("Note: new entries enter literature_review_enriched.parquet at the "
          "next full extraction run (extract_schema_columns.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
