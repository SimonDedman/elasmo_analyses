#!/usr/bin/env python3
"""Give every Shark References record a corpus row, whether or not we hold its PDF.

The January 2026 corpus holds every record of the bulk export. Since then the
monthly sync has appended new records to the master CSV and the todo list, but
gave a record a parquet row only when the sync itself downloaded its PDF on
that run. A record filed later by any other route (the coauthor drop-folder
scan, the acquisition cascade, ingest_pdfs.py) had a PDF in the library and no
corpus row, so it was never extracted. Measured 2026-10-04: 2,652 master
records without a row, 575 of them with a PDF in the library.

This script closes that gap and is safe to run after every filing batch:

  1. master-CSV records with no base-parquet row are appended to
     outputs/literature_review.parquet, unless the paper is already held under
     another id (same DOI and an agreeing title) or cannot be told apart from
     an existing row (DOI conflict, or an identical title + year). Those are
     written to outputs/corpus_backfill_held_<date>.csv, never guessed.
  2. the literature_id -> PDF map is rebuilt, so the new rows can find a PDF.
  3. the new rows are extracted and appended to the enriched parquet.
  4. metadata the enriched parquet lacks (title, authors, year, doi, abstract:
     the sync's append path never wrote them, leaving 1,209 rows blank) is
     filled from the base parquet.

Usage:
    python3 scripts/backfill_corpus_rows.py            # dry run: report only
    python3 scripts/backfill_corpus_rows.py --apply
"""
from __future__ import annotations

import argparse
import csv
import logging
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_shark_references as sr  # noqa: E402

ROOT = sr.PROJECT_ROOT
BASE_PARQUET = sr.BASE_PARQUET
ENRICHED_PARQUET = sr.PARQUET
EVIDENCE_CSV = ROOT / "outputs/schema_extraction_evidence.csv"
# Columns both parquets carry and the master CSV (or the base parquet) can supply.
META_COLS = ["title", "authors", "year", "doi", "abstract", "pdf_url",
             "journal", "date_added", "data_source"]


def _lid(value) -> str:
    return sr._normalise_lid(value)


def latest_master() -> Path:
    files = sorted(sr.MASTER_CSV_DIR.glob("shark_references_complete_*.csv"),
                   key=lambda p: p.stat().st_mtime)
    if not files:
        sys.exit(f"no master CSV under {sr.MASTER_CSV_DIR}")
    return files[-1]


def plan(df_base: pd.DataFrame, master: Path):
    """Split master records lacking a base row into (to_add, held)."""
    known = {_lid(v) for v in df_base["literature_id"]} - {""}
    doi_rows = sr.build_parquet_doi_rows(df_base)
    key_dois: dict = {}
    for title, year, doi in zip(df_base["title"], df_base["year"], df_base["doi"]):
        key = sr._title_year_key(title, year)
        if key:
            key_dois.setdefault(key, set()).add(
                sr._normalise_doi(doi) if isinstance(doi, str) else "")

    to_add, held, seen = [], [], set()
    csv.field_size_limit(10 ** 9)
    with open(master, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lid = _lid(r.get("literature_id"))
            if not lid or lid in known or lid in seen:
                continue
            seen.add(lid)
            title = sr.master_row_title(r).strip()
            year = sr._year_int(r.get("year"))
            doi = sr._doi_of(r)
            rec = {"literature_id": lid, "title": title,
                   "authors": (r.get("authors") or "").strip(),
                   "year": float(year) if year is not None else float("nan"),
                   "doi": (r.get("doi") or "").strip(),
                   "abstract": (r.get("abstract") or "").strip(),
                   "pdf_url": (r.get("pdf_url") or "").strip()}
            why = other = ""
            if not title:
                why = "no title in the master CSV"
            elif doi and doi in doi_rows:
                rows = doi_rows[doi]
                other = ", ".join(x[0] for x in rows)
                if len(rows) == 1 and sr._same_paper(title, year, rows[0][1], rows[0][2]):
                    why = "already in the corpus under another id (same DOI, agreeing title)"
                else:
                    why = "DOI is on another corpus row whose title disagrees, or on several rows"
            elif sr._title_year_duplicate(sr._title_year_key(title, year), doi, key_dois):
                why = "identical title and year to an existing corpus row"
            if why:
                held.append({**{k: rec[k] for k in ("literature_id", "year", "authors", "title", "doi")},
                             "reason": why, "corpus_ids_sharing_doi": other})
            else:
                to_add.append(rec)
    return to_add, held


def fill_enriched_metadata() -> int:
    """Copy metadata from the base parquet into enriched cells that are blank."""
    df_base = pd.read_parquet(BASE_PARQUET)
    df_enr = pd.read_parquet(ENRICHED_PARQUET)
    base = df_base.assign(_lid=df_base["literature_id"].map(_lid)).drop_duplicates("_lid").set_index("_lid")
    key = df_enr["literature_id"].map(_lid)
    filled_rows = pd.Series(False, index=df_enr.index)
    for col in META_COLS:
        if col not in df_enr.columns or col not in base.columns:
            continue
        blank = df_enr[col].isna()
        if not blank.any():
            continue
        new = key[blank].map(base[col])
        got = new.notna()
        if col == "year":
            new = pd.to_numeric(new, errors="coerce")
        df_enr.loc[new.index[got], col] = new[got].astype(df_enr[col].dtype, errors="ignore")
        filled_rows.loc[new.index[got]] = True
    if filled_rows.any():
        df_enr.to_parquet(ENRICHED_PARQUET, index=False)
    return int(filled_rows.sum())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write. Default is a dry run.")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("backfill_corpus_rows")

    master = latest_master()
    df_base = pd.read_parquet(BASE_PARQUET)
    to_add, held = plan(df_base, master)

    def era(rec):
        y = sr._year_int(rec["year"])
        return ("no year" if y is None else "pre-1950" if y < 1950
                else "2026+" if y >= 2026 else "2025" if y == 2025 else "1950-2024")

    print(f"master: {master.name}")
    print(f"base parquet rows: {len(df_base):,}")
    print(f"records to add: {len(to_add):,}  {dict(Counter(era(r) for r in to_add))}")
    print(f"records held (not added): {len(held):,}  {dict(Counter(h['reason'] for h in held))}")

    stamp = datetime.now().strftime("%Y-%m-%d")
    if held:
        held_csv = ROOT / f"outputs/corpus_backfill_held_{stamp}.csv"
        if args.apply:
            pd.DataFrame(held).to_csv(held_csv, index=False)
            print(f"held list: {held_csv}")

    if not args.apply:
        print("[dry run] nothing written. Re-run with --apply.")
        return 0

    if to_add:
        backup = ROOT / f"outputs/backup_corpus_backfill_{datetime.now():%Y%m%d_%H%M%S}"
        backup.mkdir(parents=True)
        for p in (BASE_PARQUET, ENRICHED_PARQUET, EVIDENCE_CSV):
            if p.exists():
                shutil.copy2(p, backup / p.name)
        print(f"backup: {backup}")

        for rec in to_add:
            rec["date_added"] = stamp
            rec["data_source"] = "shark-references.com"
        added = sr.propagate_to_base_parquet(to_add, log)
        print(f"base parquet: +{added:,} rows")

        # New rows are invisible to extraction until the id -> PDF map knows them.
        subprocess.run([sys.executable, str(ROOT / "scripts/build_pdf_id_map.py")], check=True)
        # That rebuild diffs against the previous map and so consumes the list of
        # records whose PDF moved. Keep a copy for refresh_pdf_map_and_extract.sh,
        # whose own rebuild straight afterwards would otherwise report no change.
        changes = ROOT / "outputs/pdf_id_map_changes.csv"
        if changes.exists():
            shutil.copy2(changes, ROOT / "outputs/pdf_id_map_changes_backfill.csv")
        ids = {r["literature_id"] for r in to_add}
        with_pdf = sr.run_incremental_extraction(ids, log)
        print(f"extracted: {len(ids):,} rows, {with_pdf:,} with PDF text")

    filled = fill_enriched_metadata()
    print(f"enriched parquet: metadata filled from the base parquet on {filled:,} rows")

    n_base = len(pd.read_parquet(BASE_PARQUET, columns=["literature_id"]))
    n_enr = len(pd.read_parquet(ENRICHED_PARQUET, columns=["literature_id"]))
    print(f"rows now: base {n_base:,}, enriched {n_enr:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
