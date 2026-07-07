#!/usr/bin/env python3
"""
Merge the geographic-extraction pipeline (database/technique_taxonomy.db ->
paper_geography table) into the main analysis parquet
(outputs/literature_review_enriched.parquet).

Why this is non-trivial: paper_geography.paper_id is NOT a literature_id, it
is the SharkPapers library filename (e.g.
"Aalbers.etal.2010.The functional role of the caudal fin in the feeding.pdf").
There is no literature_id column anywhere in technique_taxonomy.db. So the
join has to be reconstructed by:

  1. Parsing each paper_geography.paper_id filename into
     (first_author_surname, year, truncated_title_words).
  2. For every row in the main parquet, deriving the same
     (first_author_surname, year) key from its `authors`/`year` columns.
  3. Within an (author, year) bucket, matching the filename's
     (possibly stopword-stripped, possibly mid-word-truncated) title
     fragment against the real title as an in-order prefix subsequence
     of words, and accepting the match only if it is unambiguous.

This recovers ~95% of the 6,183 paper_geography rows against the current
31,648-row parquet. Rows that can't be confidently matched are left with
NA geography rather than guessed.

Usage:
    python scripts/merge_geography.py            # do the merge, write parquet
    python scripts/merge_geography.py --dry-run  # report only, no writes
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
DB_PATH = PROJECT / "database/technique_taxonomy.db"
PARQUET_PATH = PROJECT / "outputs/literature_review_enriched.parquet"
BACKUP_DIR = PROJECT / "outputs"

# Columns pulled from paper_geography, prefixed with geo_ on merge.
# (paper_id / created_date / updated_date are join scaffolding, not carried over.)
GEO_COLUMNS = [
    "first_author_institution",
    "first_author_country",
    "first_author_region",
    "study_country",
    "study_ocean_basin",
    "study_latitude",
    "study_longitude",
    "study_location_text",
    "has_author_country",
    "has_study_location",
    "is_parachute_research",
    "oa_status",
    "oa_url",
    "oa_is_oa",
    "oa_journal_is_oa",
    "oa_journal_is_in_doaj",
    "oa_host_type",
    "oa_license",
    "oa_version",
]

STOPWORDS = {
    "a", "an", "the", "of", "in", "and", "on", "for", "to", "with", "from",
    "by", "at", "as", "is", "are", "using", "into", "its", "their", "this",
    "that",
}

FILENAME_RE = re.compile(
    r"^(?P<author>.+?)\.(?P<etal>etal\.)?(?P<year>\d{4})\.(?P<title>.*)\.pdf$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Text normalisation helpers (mirrors scripts/ingest_pdfs.py naming convention)
# ---------------------------------------------------------------------------

def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", str(s))
        if unicodedata.category(c) != "Mn"
    )


def extract_first_author_surname(authors: str) -> str:
    """Same logic as ingest_pdfs.extract_first_author, kept local/self-contained."""
    if not authors:
        return "unknown"
    authors = str(authors).strip()
    first = re.split(r"\s*&\s*", authors)[0].strip()
    first = re.sub(r"\(\d{4}\)", "", first).strip()
    if "," in first:
        surname = first.split(",")[0]
    else:
        parts = first.split()
        surname = parts[-1] if parts else "unknown"
    surname = strip_accents(surname).lower()
    return re.sub(r"[^a-z0-9]+", "", surname)


def word_list(s: str) -> list[str]:
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return [w for w in s.split() if w not in STOPWORDS]


def subseq_match_score(fn_words: list[str], title_words: list[str]) -> tuple[int, int]:
    """Greedily match fn_words as an in-order prefix-subsequence of title_words.

    Handles both whole-word truncation (word dropped) and mid-word truncation
    (e.g. filename word "Distribu" for real word "distribution").
    """
    ti = 0
    matched = 0
    for fw in fn_words:
        found = False
        while ti < len(title_words):
            tw = title_words[ti]
            ti += 1
            ok = (tw == fw) if len(fw) <= 3 else (tw.startswith(fw) or fw.startswith(tw))
            if ok:
                matched += 1
                found = True
                break
        if not found:
            continue
    return matched, len(fn_words)


# ---------------------------------------------------------------------------
# Build paper_id -> literature_id mapping
# ---------------------------------------------------------------------------

def build_paper_id_to_literature_id(geo: pd.DataFrame, df: pd.DataFrame) -> dict[str, str]:
    """Return {paper_geography.paper_id: literature_id} for confident matches only."""
    # Index geo rows by (author_surname, year) -> list of (title_words, paper_id)
    index: dict[tuple[str, str], list[tuple[list[str], str]]] = defaultdict(list)
    unparsed = 0
    for pid in geo["paper_id"]:
        m = FILENAME_RE.match(pid)
        if not m:
            unparsed += 1
            continue
        author_norm = re.sub(r"[^a-z0-9]+", "", strip_accents(m.group("author")).lower())
        year = m.group("year")
        index[(author_norm, year)].append((word_list(m.group("title")), pid))
    if unparsed:
        print(f"  WARNING: {unparsed} paper_geography.paper_id values did not match "
              f"the Author.etal.Year.Title.pdf convention and were skipped.")

    mapping: dict[str, str] = {}
    ambiguous = 0
    for _, row in df.iterrows():
        year_val = row.get("year")
        try:
            year = str(int(float(year_val)))
        except (ValueError, TypeError):
            continue
        author_norm = extract_first_author_surname(row.get("authors", ""))
        cands = index.get((author_norm, year))
        if not cands:
            continue
        title_words = word_list(str(row.get("title", "")))
        scored = []
        for fn_words, pid in cands:
            if not fn_words:
                continue
            m, tot = subseq_match_score(fn_words, title_words)
            frac = m / tot if tot else 0
            scored.append((frac, m, pid))
        if not scored:
            continue
        scored.sort(reverse=True)
        best_frac, best_m, best_pid = scored[0]
        if best_frac >= 0.8 and best_m >= 3:
            if (len(scored) > 1 and scored[1][0] >= 0.8 and scored[1][1] >= 3
                    and scored[1][2] != best_pid):
                ambiguous += 1
                continue
            # First literature_id wins if two rows point at the same paper_id
            # (duplicate/near-duplicate parquet rows); don't overwrite.
            mapping.setdefault(best_pid, str(row["literature_id"]))

    if ambiguous:
        print(f"  {ambiguous} parquet rows had ambiguous multi-candidate matches "
              f"(same author+year, tied title score) and were left unmatched.")
    return mapping


# ---------------------------------------------------------------------------
# Main merge
# ---------------------------------------------------------------------------

def normalise_id(x) -> str:
    """literature_id normaliser: handles the classic float/string mismatch."""
    try:
        return str(int(float(x)))
    except (ValueError, TypeError):
        return str(x).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report only, do not write parquet")
    args = ap.parse_args()

    if not PARQUET_PATH.exists():
        print(f"ERROR: {PARQUET_PATH} not found", file=sys.stderr)
        return 1
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found", file=sys.stderr)
        return 1

    print(f"Loading {PARQUET_PATH} ...")
    df = pd.read_parquet(PARQUET_PATH)
    rows_before = len(df)
    cols_before = len(df.columns)
    print(f"  {rows_before} rows, {cols_before} columns")

    print(f"Loading paper_geography from {DB_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    try:
        geo = pd.read_sql("SELECT * FROM paper_geography", conn)
    finally:
        conn.close()
    print(f"  {len(geo)} geography rows")

    print("Reconstructing paper_id -> literature_id mapping (author+year+title match) ...")
    pid_to_litid = build_paper_id_to_literature_id(geo, df)
    print(f"  {len(pid_to_litid)} / {len(geo)} geography rows matched to a literature_id "
          f"({len(pid_to_litid) / len(geo) * 100:.1f}%)")

    geo = geo.copy()
    geo["literature_id"] = geo["paper_id"].map(pid_to_litid)
    geo = geo.dropna(subset=["literature_id"])
    geo["literature_id"] = geo["literature_id"].map(normalise_id)
    # In case two paper_geography rows somehow map to the same literature_id, keep first.
    geo = geo.drop_duplicates(subset=["literature_id"], keep="first")

    geo_subset = geo[["literature_id"] + GEO_COLUMNS].copy()
    geo_subset = geo_subset.rename(columns={c: f"geo_{c}" for c in GEO_COLUMNS})

    # Drop any pre-existing geo_ columns from a prior run before merging fresh.
    new_col_names = list(geo_subset.columns.drop("literature_id"))
    pre_existing = [c for c in new_col_names if c in df.columns]
    if pre_existing:
        print(f"  Dropping {len(pre_existing)} pre-existing geo_ columns before re-merge "
              f"(re-running this script is idempotent).")
        df = df.drop(columns=pre_existing)

    df["_lit_id_norm"] = df["literature_id"].map(normalise_id)
    merged = df.merge(
        geo_subset.rename(columns={"literature_id": "_lit_id_norm"}),
        on="_lit_id_norm",
        how="left",
    )
    merged = merged.drop(columns=["_lit_id_norm"])

    rows_with_geo = merged["geo_first_author_country"].notna().sum() if "geo_first_author_country" in merged.columns else 0
    coverage_any = merged[new_col_names].notna().any(axis=1).sum()

    print()
    print("=== Merge report ===")
    print(f"Rows total:                 {len(merged)}")
    print(f"Rows with any geo_ data:    {coverage_any} ({coverage_any / len(merged) * 100:.2f}%)")
    print(f"Rows with author country:   {rows_with_geo} ({rows_with_geo / len(merged) * 100:.2f}%)")
    print(f"Columns added:              {len(new_col_names)}")
    for c in new_col_names:
        print(f"  {c}")

    if args.dry_run:
        print("\n--dry-run: not writing parquet.")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"literature_review_enriched.backup_{timestamp}.parquet"
    print(f"\nBacking up original parquet to {backup_path}")
    shutil.copy2(PARQUET_PATH, backup_path)

    tmp_path = PARQUET_PATH.with_suffix(".parquet.tmp")
    merged.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, PARQUET_PATH)
    print(f"Wrote merged parquet to {PARQUET_PATH} "
          f"({len(merged)} rows, {len(merged.columns)} columns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
