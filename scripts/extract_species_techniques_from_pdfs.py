#!/usr/bin/env python3
"""
Extract species and analytical technique mentions from full PDF text,
with frequency counting and evidence context. Also extracts depth
evidence sentences.

Reuses the PDF-to-paper mapping from extract_schema_columns.py.

Usage:
    python scripts/extract_species_techniques_from_pdfs.py             # full run
    python scripts/extract_species_techniques_from_pdfs.py --limit 50  # test
    python scripts/extract_species_techniques_from_pdfs.py --resume    # continue
"""

import argparse
import csv
import json
import math
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"
EVIDENCE_PATH = PROJECT_ROOT / "outputs" / "schema_extraction_evidence.csv"
PDF_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PROGRESS_PATH = PROJECT_ROOT / "outputs" / ".sp_tech_progress.json"
TECH_DB = PROJECT_ROOT / "database" / "technique_taxonomy.db"

# ---------------------------------------------------------------------------
# Import PDF mapping from extract_schema_columns.py
# ---------------------------------------------------------------------------

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from extract_schema_columns import (
    build_pdf_index,
    _first_surname,
    _pick_best_pdf,
    extract_text_from_pdf,
)


# ---------------------------------------------------------------------------
# Load species patterns
# ---------------------------------------------------------------------------

def load_species_patterns() -> list[dict]:
    """Load species column names from parquet and build search patterns."""
    schema = pq.read_schema(PARQUET_PATH)
    sp_cols = sorted(c for c in schema.names if c.startswith("sp_"))

    # Try to load common names
    species_csv = PROJECT_ROOT / "data" / "sharkipedia" / "species_list.csv"
    common_names = {}
    if species_csv.exists():
        with open(species_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                binomial = (row.get("binomial") or "").strip()
                common = (row.get("common_name_primary") or "").strip()
                if binomial and common:
                    common_names[binomial.lower()] = common

    species = []
    for col in sp_cols:
        binomial = col.replace("sp_", "").replace("_", " ")
        common = common_names.get(binomial.lower(), "")
        patterns = [re.compile(r"\b" + re.escape(binomial) + r"\b", re.IGNORECASE)]
        if common:
            patterns.append(re.compile(r"\b" + re.escape(common) + r"\b", re.IGNORECASE))
        species.append({"col": col, "binomial": binomial, "common": common, "patterns": patterns})

    return species


# ---------------------------------------------------------------------------
# Load technique patterns
# ---------------------------------------------------------------------------

def load_technique_patterns() -> list[dict]:
    """Load technique search patterns from the taxonomy database."""
    schema = pq.read_schema(PARQUET_PATH)
    a_cols = sorted(c for c in schema.names if c.startswith("a_"))

    tech_queries: dict[str, list[str]] = {}
    if TECH_DB.exists():
        conn = sqlite3.connect(str(TECH_DB))
        try:
            # techniques table has technique_name and synonyms
            rows = conn.execute(
                "SELECT technique_name, synonyms FROM techniques"
            ).fetchall()
            for name, synonyms in rows:
                col_name = "a_" + name.lower().replace(" ", "_").replace("-", "_").replace("/", "_")
                queries = [name]  # primary: the technique name itself
                if synonyms:
                    queries.extend(s.strip() for s in synonyms.split(",") if s.strip())
                tech_queries[col_name] = queries
        finally:
            conn.close()

    techniques = []
    for col in a_cols:
        queries = tech_queries.get(col, [col.replace("a_", "").replace("_", " ")])
        patterns = []
        for q in queries:
            try:
                patterns.append((q, re.compile(r"\b" + re.escape(q) + r"\b", re.IGNORECASE)))
            except re.error:
                continue
        techniques.append({"col": col, "queries": queries, "patterns": patterns})

    return techniques


# ---------------------------------------------------------------------------
# Depth evidence extraction
# ---------------------------------------------------------------------------

_DEPTH_RANGE_RE = re.compile(
    r"(?:depth[s]?\s+(?:of\s+|from\s+|between\s+|ranging?\s+(?:from\s+)?)?)"
    r"(\d+(?:\.\d+)?)\s*(?:[-\u2013\u2014to]+)\s*(\d+(?:\.\d+)?)\s*(?:m\b|meter|metre)",
    re.IGNORECASE,
)
_DEPTH_SINGLE_RE = re.compile(
    r"(?:depth[s]?\s+(?:of\s+|>|<|\u2265|\u2264|at\s+)?)"
    r"(\d+(?:\.\d+)?)\s*(?:m\b|meter|metre)",
    re.IGNORECASE,
)


def _context_around(text: str, start: int, window: int = 120) -> str:
    """Extract context around a match position."""
    lo = max(0, start - window)
    hi = min(len(text), start + window)
    # Extend to sentence boundaries
    while lo > 0 and text[lo] not in ".\n":
        lo -= 1
    while hi < len(text) and text[hi] not in ".\n":
        hi += 1
    return text[lo:hi].replace("\n", " ").strip()[:250]


# ---------------------------------------------------------------------------
# Process one paper
# ---------------------------------------------------------------------------

def process_paper(
    lit_id: str,
    text: str,
    species: list[dict],
    techniques: list[dict],
) -> dict:
    """Extract species freq, technique freq, and depth evidence from text."""

    sp_counts: dict[str, int] = {}
    sp_evidence: list[dict] = []
    for sp in species:
        total = 0
        first_ctx = ""
        for pat in sp["patterns"]:
            matches = list(pat.finditer(text))
            total += len(matches)
            if matches and not first_ctx:
                first_ctx = _context_around(text, matches[0].start())
        sp_counts[sp["col"]] = total
        if total > 0:
            sp_evidence.append({
                "literature_id": lit_id,
                "title": "",
                "column": sp["col"],
                "binary": 1,
                "total_freq": str(total),
                "raw_freq": str(total),
                "section": "",
                "term_count": str(total),
                "threshold": "1",
                "matched_terms": f"{sp['binomial']}({total})",
                "matched_anchors": "",
                "context": first_ctx,
            })

    tech_counts: dict[str, int] = {}
    tech_evidence: list[dict] = []
    for tech in techniques:
        total = 0
        first_ctx = ""
        parts = []
        for query, pat in tech["patterns"]:
            matches = list(pat.finditer(text))
            n = len(matches)
            total += n
            if n > 0:
                parts.append(f"{query}({n})")
                if not first_ctx:
                    first_ctx = _context_around(text, matches[0].start())
        tech_counts[tech["col"]] = total
        if total > 0:
            tech_evidence.append({
                "literature_id": lit_id,
                "title": "",
                "column": tech["col"],
                "binary": 1,
                "total_freq": str(total),
                "raw_freq": str(total),
                "section": "",
                "term_count": str(total),
                "threshold": "1",
                "matched_terms": "; ".join(parts),
                "matched_anchors": "",
                "context": first_ctx,
            })

    depth_evidence: list[dict] = []
    for regex in [_DEPTH_RANGE_RE, _DEPTH_SINGLE_RE]:
        for m in regex.finditer(text):
            ctx = _context_around(text, m.start())
            depth_evidence.append({
                "literature_id": lit_id,
                "title": "",
                "column": "depth_range",
                "binary": 1,
                "total_freq": "1",
                "raw_freq": "1",
                "section": "",
                "term_count": "1",
                "threshold": "1",
                "matched_terms": m.group(0)[:80],
                "matched_anchors": "",
                "context": ctx,
            })

    return {
        "species": sp_counts,
        "techniques": tech_counts,
        "sp_evidence": sp_evidence,
        "tech_evidence": tech_evidence,
        "depth_evidence": depth_evidence,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Process first N papers only")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    species = load_species_patterns()
    techniques = load_technique_patterns()
    print(f"Loaded {len(species)} species, {len(techniques)} techniques")

    # Build PDF index (same as extract_schema_columns.py)
    print("Building PDF index...")
    pdf_index = build_pdf_index(PDF_DIR)
    print(f"  {sum(len(v) for v in pdf_index.values())} PDFs indexed")

    # Load parquet
    print("Loading parquet...")
    df = pd.read_parquet(PARQUET_PATH, columns=["literature_id", "year", "authors", "title"])

    # Resume support
    processed = set()
    if args.resume and PROGRESS_PATH.exists():
        with open(PROGRESS_PATH) as f:
            processed = set(json.load(f).get("processed", []))
        print(f"  Resuming: {len(processed)} already done")

    # Map papers to PDF paths
    print("Resolving PDFs...")
    paper_pdfs: list[tuple[str, Path, str]] = []
    for _, row in df.iterrows():
        lid_raw = row.get("literature_id")
        if lid_raw is None or (isinstance(lid_raw, float) and math.isnan(lid_raw)):
            continue
        lit_id = str(int(float(lid_raw)))
        if lit_id in processed:
            continue

        authors = row.get("authors")
        year_raw = row.get("year")
        title = row.get("title") or ""
        if not authors or pd.isna(year_raw):
            continue

        year = int(year_raw)
        surname = _first_surname(authors)
        if not surname:
            continue

        candidates = pdf_index.get((surname, year), [])
        best_pdf = _pick_best_pdf(candidates, title)
        if best_pdf:
            paper_pdfs.append((lit_id, best_pdf, title))

    print(f"  {len(paper_pdfs)} papers with PDFs to process")
    if args.limit:
        paper_pdfs = paper_pdfs[: args.limit]

    # Process papers
    all_sp = {}
    all_tech = {}
    all_evidence: list[dict] = []
    count = 0

    for lit_id, pdf_path, title in paper_pdfs:
        text = extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            continue

        result = process_paper(lit_id, text, species, techniques)
        all_sp[lit_id] = result["species"]
        all_tech[lit_id] = result["techniques"]
        all_evidence.extend(result["sp_evidence"])
        all_evidence.extend(result["tech_evidence"])
        all_evidence.extend(result["depth_evidence"])

        processed.add(lit_id)
        count += 1

        if count % 200 == 0:
            print(f"  {count}/{len(paper_pdfs)} done "
                  f"({len(all_evidence)} evidence rows so far)")
            with open(PROGRESS_PATH, "w") as f:
                json.dump({"processed": sorted(processed)}, f)

    # Final save
    with open(PROGRESS_PATH, "w") as f:
        json.dump({"processed": sorted(processed)}, f)

    print(f"\nProcessed {count} papers.")
    sp_ev = sum(1 for e in all_evidence if e["column"].startswith("sp_"))
    tech_ev = sum(1 for e in all_evidence if e["column"].startswith("a_"))
    depth_ev = sum(1 for e in all_evidence if e["column"] == "depth_range")
    print(f"  Species evidence: {sp_ev} rows")
    print(f"  Technique evidence: {tech_ev} rows")
    print(f"  Depth evidence: {depth_ev} rows")

    # --- Update parquet: sp_ bool→int16, a_ bool→int16 ---
    print("\nUpdating parquet columns to int16 with frequencies...")
    table = pq.read_table(PARQUET_PATH)
    lit_ids = []
    for v in table.column("literature_id"):
        raw = v.as_py()
        if raw is None or (isinstance(raw, float) and math.isnan(raw)):
            lit_ids.append("")
        else:
            lit_ids.append(str(int(float(raw))))

    sp_cols = [c for c in table.column_names if c.startswith("sp_")]
    a_cols = [c for c in table.column_names if c.startswith("a_")]

    for cols, freq_dict in [(sp_cols, all_sp), (a_cols, all_tech)]:
        for col in cols:
            new_vals = []
            for i, lid in enumerate(lit_ids):
                if lid in freq_dict and col in freq_dict[lid]:
                    new_vals.append(freq_dict[lid][col])
                else:
                    old = table.column(col)[i].as_py()
                    new_vals.append(1 if old else 0)
            idx = table.column_names.index(col)
            table = table.set_column(idx, col, pa.array(new_vals, type=pa.int16()))

    pq.write_table(table, PARQUET_PATH)
    print(f"  Updated {len(sp_cols)} sp_ and {len(a_cols)} a_ columns to int16.")

    # --- Append evidence ---
    if all_evidence:
        print(f"Appending {len(all_evidence)} evidence rows to {EVIDENCE_PATH}...")
        cols = [
            "literature_id", "title", "column", "binary", "total_freq",
            "raw_freq", "section", "term_count", "threshold",
            "matched_terms", "matched_anchors", "context",
        ]
        with open(EVIDENCE_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            for ev in all_evidence:
                w.writerow(ev)

    print("\nDone. Run generate_validation_pages.py to update the UI.")


if __name__ == "__main__":
    main()
