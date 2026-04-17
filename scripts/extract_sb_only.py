#!/usr/bin/env python3
"""
Supplementary extraction for the sb_ (ocean sub-basin) schema only.

Reuses extract_schema_columns.py's compile/match infrastructure but
only processes the SUB_BASIN schema. Adds sb_ columns to the parquet
and appends evidence rows to the evidence CSV without touching other
columns.

Usage:
    python scripts/extract_sb_only.py             # full run
    python scripts/extract_sb_only.py --limit 50  # test
    python scripts/extract_sb_only.py --resume    # continue
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"
EVIDENCE_PATH = PROJECT_ROOT / "outputs" / "schema_extraction_evidence.csv"
PDF_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PROGRESS_PATH = PROJECT_ROOT / "outputs" / ".sb_progress.json"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from extract_schema_columns import (
    build_pdf_index,
    _first_surname,
    _pick_best_pdf,
    extract_text_from_pdf,
    compile_schema,
    _match_column,
    _label_sections,
    SUB_BASIN,
)


def _context_around(text: str, start: int, window: int = 120) -> str:
    """Sentence-bounded context around a position."""
    lo = max(0, start - window)
    hi = min(len(text), start + window)
    while lo > 0 and text[lo] not in ".\n":
        lo -= 1
    while hi < len(text) and text[hi] not in ".\n":
        hi += 1
    return text[lo:hi].replace("\n", " ").strip()[:250]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Process first N papers only")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    print("Compiling SUB_BASIN schema...")
    compiled_cols = compile_schema(SUB_BASIN)
    print(f"  {len(compiled_cols)} sb_ columns compiled")

    print("Building PDF index...")
    pdf_index = build_pdf_index(PDF_DIR)
    print(f"  {sum(len(v) for v in pdf_index.values())} PDFs indexed")

    print("Loading parquet...")
    df = pd.read_parquet(
        PARQUET_PATH,
        columns=["literature_id", "year", "authors", "title"],
    )

    processed = set()
    if args.resume and PROGRESS_PATH.exists():
        with open(PROGRESS_PATH) as f:
            processed = set(json.load(f).get("processed", []))
        print(f"  Resuming: {len(processed)} already done")

    paper_pdfs: list[tuple[str, Path]] = []
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
            paper_pdfs.append((lit_id, best_pdf))

    if args.limit:
        paper_pdfs = paper_pdfs[: args.limit]

    print(f"Processing {len(paper_pdfs)} papers...")

    # Collect results: lit_id -> {col_name: binary_value}
    sb_results: dict[str, dict[str, int]] = {}
    all_evidence: list[dict] = []
    count = 0

    for lit_id, pdf_path in paper_pdfs:
        text = extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            continue

        labelled_sections = _label_sections(text)

        paper_sb: dict[str, int] = {}
        for col in compiled_cols:
            result = _match_column(text, col, schema_prefix="sb_",
                                   labelled_sections=labelled_sections)
            paper_sb[col.name] = result.binary
            if result.binary:
                all_evidence.append({
                    "literature_id": lit_id,
                    "title": "",
                    "column": col.name,
                    "binary": 1,
                    "total_freq": str(result.total_freq),
                    "raw_freq": str(result.raw_freq),
                    "section": result.primary_section,
                    "term_count": str(result.term_count),
                    "threshold": str(col.threshold),
                    "matched_terms": "; ".join(result.matched_terms),
                    "matched_anchors": "; ".join(result.matched_anchors),
                    "context": (result.sample_context or "")[:250],
                })

        sb_results[lit_id] = paper_sb
        processed.add(lit_id)
        count += 1

        if count % 500 == 0:
            print(f"  {count}/{len(paper_pdfs)} papers, {len(all_evidence)} evidence rows")
            with open(PROGRESS_PATH, "w") as f:
                json.dump({"processed": sorted(processed)}, f)

    with open(PROGRESS_PATH, "w") as f:
        json.dump({"processed": sorted(processed)}, f)

    print(f"\nProcessed {count} papers, {len(all_evidence)} evidence rows")

    # Update parquet: add/update sb_ columns
    print("Updating parquet with sb_ columns...")
    table = pq.read_table(PARQUET_PATH)
    lit_ids = []
    for v in table.column("literature_id"):
        raw = v.as_py()
        if raw is None or (isinstance(raw, float) and math.isnan(raw)):
            lit_ids.append("")
        else:
            lit_ids.append(str(int(float(raw))))

    sb_col_names = sorted(col.name for col in compiled_cols)
    existing_sb = [c for c in table.column_names if c.startswith("sb_")]

    for col_name in sb_col_names:
        new_vals = []
        for i, lid in enumerate(lit_ids):
            if lid in sb_results and col_name in sb_results[lid]:
                new_vals.append(sb_results[lid][col_name])
            elif col_name in existing_sb:
                old = table.column(col_name)[i].as_py()
                new_vals.append(int(old) if old is not None else 0)
            else:
                new_vals.append(0)

        if col_name in existing_sb:
            idx = table.column_names.index(col_name)
            table = table.set_column(idx, col_name, pa.array(new_vals, type=pa.int64()))
        else:
            table = table.append_column(col_name, pa.array(new_vals, type=pa.int64()))

    pq.write_table(table, PARQUET_PATH)
    print(f"  Wrote {len(sb_col_names)} sb_ columns")

    # Append evidence
    if all_evidence:
        print(f"Appending {len(all_evidence)} evidence rows...")
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
