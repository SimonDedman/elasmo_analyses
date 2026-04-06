#!/usr/bin/env python3
"""
Incremental schema extraction for a small batch of papers.

Processes only specified literature_ids, then patches results into the
existing enriched parquet and appends evidence rows to the evidence CSV.
Much faster than a full re-run for small batches (e.g. after PDF ingestion).

Usage:
    python scripts/extract_incremental.py outputs/ingest_check.csv
    python scripts/extract_incremental.py --ids 500199,33199,31611
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Import extraction machinery from the main script
sys.path.insert(0, str(Path(__file__).parent))
from extract_schema_columns import (
    ALL_SCHEMAS,
    OUTPUT_PARQUET,
    EVIDENCE_CSV,
    PDF_BASE,
    build_pdf_index,
    init_worker,
    process_paper,
)

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
INPUT_PARQUET = PROJECT_BASE / "outputs/literature_review.parquet"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Incremental schema extraction for a small batch of papers."
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        help="CSV with a 'literature_id' column (e.g. ingest_check.csv)",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default="",
        help="Comma-separated literature_ids to process.",
    )
    args = parser.parse_args()

    # Collect target IDs
    target_ids: set[str] = set()
    if args.csv_file:
        df_ids = pd.read_csv(args.csv_file)
        target_ids = set(df_ids["literature_id"].dropna().astype(str))
    if args.ids:
        target_ids |= set(args.ids.split(","))

    if not target_ids:
        print("No literature_ids specified. Provide a CSV or --ids.")
        sys.exit(1)

    print(f"Target papers: {len(target_ids)}")

    # Load source parquet (the un-enriched one with original metadata)
    print(f"Loading input parquet: {INPUT_PARQUET}")
    df_input = pd.read_parquet(INPUT_PARQUET)
    df_input["literature_id"] = df_input["literature_id"].astype(str)

    # Filter to target papers
    needed_cols = ["literature_id", "title", "abstract", "authors", "year", "doi"]
    mask = df_input["literature_id"].isin(target_ids)
    rows = df_input.loc[mask, needed_cols].to_dict("records")
    for i, row in enumerate(rows):
        row["_row_idx"] = i

    print(f"Found {len(rows)} papers in parquet (of {len(target_ids)} requested)")

    if not rows:
        print("No papers to process.")
        return

    # Build PDF index and process
    print(f"Building PDF index from {PDF_BASE} ...")
    pdf_index = build_pdf_index(PDF_BASE)
    total_pdfs = sum(len(v) for v in pdf_index.values())
    print(f"Indexed {total_pdfs} PDFs across {len(pdf_index)} keys")

    init_worker(pdf_index)

    results = []
    for i, row in enumerate(rows, 1):
        result = process_paper(row)
        pdf_flag = "PDF" if result.get("_pdf_found") else "no PDF"
        print(f"  [{i:3d}/{len(rows)}] {row['literature_id']} — {pdf_flag}")
        results.append(result)

    # Collect evidence rows
    all_evidence = []
    for r in results:
        all_evidence.extend(r.pop("_evidence", []))

    results_df = pd.DataFrame(results)
    pdf_count = results_df["_pdf_found"].sum()
    print(f"\nProcessed: {len(results_df)} papers, {pdf_count} with PDF text")

    results_df = results_df.drop(columns=["_pdf_found"], errors="ignore")

    # --- Patch into enriched parquet ---
    print(f"\nPatching into {OUTPUT_PARQUET} ...")
    df_enriched = pd.read_parquet(OUTPUT_PARQUET)
    df_enriched["literature_id"] = df_enriched["literature_id"].astype(str)
    results_df["literature_id"] = results_df["literature_id"].astype(str)

    # Build lookup from results
    results_lookup = {}
    for i, lid in enumerate(results_df["literature_id"]):
        if lid not in results_lookup:
            results_lookup[lid] = i

    # Update columns for matched papers
    new_cols = [c for c in results_df.columns if c != "literature_id"]
    updated = 0
    for idx, lid in enumerate(df_enriched["literature_id"]):
        if lid in results_lookup:
            ri = results_lookup[lid]
            for col in new_cols:
                df_enriched.at[idx, col] = results_df.at[ri, col]
            updated += 1

    # Ensure binary columns are int
    binary_cols = [col.name for schema in ALL_SCHEMAS for col in schema.columns]
    for col_name in binary_cols:
        if col_name in df_enriched.columns:
            df_enriched[col_name] = df_enriched[col_name].fillna(0).astype(int)

    df_enriched.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"Updated {updated} rows in enriched parquet ({len(df_enriched)} total)")

    # --- Append to evidence CSV ---
    if all_evidence:
        evidence_df = pd.DataFrame(all_evidence)

        if EVIDENCE_CSV.exists():
            # Remove old evidence rows for these papers, then append new
            existing = pd.read_csv(EVIDENCE_CSV)
            existing["literature_id"] = existing["literature_id"].astype(str)
            before = len(existing)
            existing = existing[~existing["literature_id"].isin(target_ids)]
            removed = before - len(existing)
            combined = pd.concat([existing, evidence_df], ignore_index=True)
            combined.to_csv(EVIDENCE_CSV, index=False)
            print(f"Evidence CSV: removed {removed} old rows, added {len(evidence_df)} new ({len(combined)} total)")
        else:
            evidence_df.to_csv(EVIDENCE_CSV, index=False)
            print(f"Evidence CSV created: {len(evidence_df)} rows")
    else:
        print("No evidence rows generated (all papers may lack PDFs)")

    print("\nDone.")


if __name__ == "__main__":
    main()
