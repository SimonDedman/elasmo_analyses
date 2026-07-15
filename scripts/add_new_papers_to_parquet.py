#!/usr/bin/env python3
"""Add brand-new papers (present in the master SR CSV but not yet in the
parquet) to the corpus, end to end.

Unlike ``extract_incremental.py`` -- which only *patches* rows that already
exist in the enriched parquet -- this script *appends* new rows. It is the
missing piece for ingesting papers that Shark References already lists but the
figure-corpus parquet has not yet absorbed (the parquet routinely lags the
master between full SR syncs).

For each ``(literature_id, pdf_path)`` in the mapping CSV it:

  1. pulls the paper's metadata (title/authors/year/doi/abstract) from the
     latest ``shark_references_complete_*.csv`` master,
  2. files the PDF into the library at ``PDF_BASE/<year>/<Surname>.<year>.<frag>.pdf``
     (SR naming, so ``build_pdf_index`` finds it by ``(surname, year)``),
  3. runs the real schema extraction (``process_paper``) against that PDF,
  4. appends a fully-formed row to BOTH ``literature_review.parquet`` (base,
     read by the OpenAlex enricher) and ``literature_review_enriched.parquet``
     (read by Altmetric + the viz pipeline), reindexed to each parquet's
     columns (binary schema cols default 0, everything else NaN),
  5. appends the evidence rows to ``schema_extraction_evidence.csv``.

Idempotent: ids already present in a parquet are skipped for that parquet.

Usage:
    python scripts/add_new_papers_to_parquet.py [mapping.csv]
        mapping.csv columns: literature_id,pdf_path
        (default: outputs/new_papers_to_add.csv)
"""
from __future__ import annotations

import glob
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from extract_schema_columns import (  # noqa: E402
    ALL_SCHEMAS,
    EVIDENCE_CSV,
    OUTPUT_PARQUET,
    PDF_BASE,
    _first_surname,
    _normalise_name,
    build_pdf_index,
    init_worker,
    process_paper,
)

BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
BASE_PARQUET = BASE / "outputs/literature_review.parquet"
MAPPING_DEFAULT = BASE / "outputs/new_papers_to_add.csv"
META_COLS = ["literature_id", "title", "abstract", "authors", "year", "doi"]


def latest_master() -> Path:
    files = sorted(glob.glob(str(BASE / "outputs/shark_references_bulk/shark_references_complete_*.csv")))
    if not files:
        raise FileNotFoundError("No master shark_references_complete_*.csv found.")
    return Path(files[-1])


def safe_frag(title: str) -> str:
    frag = re.sub(r"[^A-Za-z0-9 ]", "", str(title))[:40].strip().replace(" ", "-")
    return frag or "untitled"


def file_pdf(pdf_src: Path, meta: dict) -> Path | None:
    """Copy the PDF into PDF_BASE/<year>/<Surname>.<year>.<frag>.pdf."""
    surname_raw = str(meta["authors"]).split(",")[0].strip() or "Unknown"
    surname = re.sub(r"[^A-Za-z-]", "", surname_raw) or "Unknown"
    year = str(int(float(meta["year"])))
    year_dir = PDF_BASE / year
    year_dir.mkdir(parents=True, exist_ok=True)
    dest = year_dir / f"{surname}.{year}.{safe_frag(meta['title'])}.pdf"
    if dest.exists():
        print(f"    PDF already filed: {dest.name}")
        return dest
    try:
        shutil.copy2(pdf_src, dest)
        print(f"    filed PDF -> {year}/{dest.name}")
        return dest
    except OSError as e:
        print(f"    ERROR filing PDF: {e}")
        return None


def main() -> int:
    mapping_path = Path(sys.argv[1]) if len(sys.argv) > 1 else MAPPING_DEFAULT
    mapping = pd.read_csv(mapping_path, dtype={"literature_id": str})
    print(f"Mapping: {len(mapping)} papers from {mapping_path.name}")

    master = pd.read_csv(latest_master(), dtype=str, low_memory=False)
    master["literature_id"] = master["literature_id"].astype(str)

    # ---- Build metadata + file PDFs ----
    rows_meta: list[dict] = []
    for _, m in mapping.iterrows():
        lid = str(m["literature_id"])
        src = Path(m["pdf_path"])
        mrow = master[master["literature_id"] == lid]
        if mrow.empty:
            print(f"  {lid}: NOT in master, skipping")
            continue
        r = mrow.iloc[0]
        meta = {
            "literature_id": lid,
            "title": r.get("title", "") or "",
            "abstract": r.get("abstract", "") or "",
            "authors": r.get("authors", "") or "",
            "year": r.get("year", "") or "",
            "doi": (r.get("doi", "") or "").lower(),
        }
        print(f"  {lid}: {meta['year']} | {str(meta['authors'])[:35]} | {str(meta['title'])[:50]}")
        if not src.exists():
            print(f"    WARNING: source PDF missing: {src}")
        else:
            file_pdf(src, meta)
        rows_meta.append(meta)

    if not rows_meta:
        print("Nothing to add.")
        return 0

    # ---- Extract schema columns against the (now-filed) PDFs ----
    print(f"\nBuilding PDF index from {PDF_BASE} ...")
    pdf_index = build_pdf_index(PDF_BASE)
    init_worker(pdf_index)

    results, all_evidence = [], []
    for i, meta in enumerate(rows_meta):
        row = dict(meta)
        row["_row_idx"] = i
        res = process_paper(row)
        found = res.get("_pdf_found")
        print(f"  extract {meta['literature_id']}: {'PDF' if found else 'NO PDF'}")
        all_evidence.extend(res.pop("_evidence", []))
        res.pop("_pdf_found", None)
        results.append(res)

    results_df = pd.DataFrame(results)
    results_df["literature_id"] = results_df["literature_id"].astype(str)
    meta_df = pd.DataFrame(rows_meta)
    # process_paper returns literature_id + schema cols; join metadata back on
    merged = meta_df.merge(results_df, on="literature_id", how="left", suffixes=("", "_res"))

    binary_cols = {col.name for schema in ALL_SCHEMAS for col in schema.columns}

    def append_to_parquet(pq_path: Path, label: str) -> None:
        df = pd.read_parquet(pq_path)
        df["literature_id"] = df["literature_id"].astype(str)
        existing = set(df["literature_id"])
        add = merged[~merged["literature_id"].isin(existing)]
        if add.empty:
            print(f"  {label}: all {len(merged)} ids already present, nothing to append")
            return
        # Reindex the new rows to the parquet's columns
        new_rows = add.reindex(columns=df.columns)
        for c in df.columns:
            if c in binary_cols:
                new_rows[c] = new_rows[c].fillna(0).astype(int)
        # Keep numeric columns numeric so concat doesn't coerce them to object
        # (year in particular is filtered numerically downstream).
        if "year" in new_rows.columns:
            new_rows["year"] = pd.to_numeric(new_rows["year"], errors="coerce")
        out = pd.concat([df, new_rows], ignore_index=True)
        out.to_parquet(pq_path, index=False)
        print(f"  {label}: appended {len(add)} rows ({len(df)} -> {len(out)})")

    print("\nAppending to parquets...")
    append_to_parquet(BASE_PARQUET, "base parquet")
    append_to_parquet(OUTPUT_PARQUET, "enriched parquet")

    # ---- Evidence ----
    if all_evidence:
        ev = pd.DataFrame(all_evidence)
        if EVIDENCE_CSV.exists():
            old = pd.read_csv(EVIDENCE_CSV)
            old["literature_id"] = old["literature_id"].astype(str)
            add_ids = set(results_df["literature_id"])
            old = old[~old["literature_id"].isin(add_ids)]
            pd.concat([old, ev], ignore_index=True).to_csv(EVIDENCE_CSV, index=False)
        else:
            ev.to_csv(EVIDENCE_CSV, index=False)
        print(f"  evidence: +{len(ev)} rows")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
