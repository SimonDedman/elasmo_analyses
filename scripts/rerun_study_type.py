#!/usr/bin/env python3
"""Incrementally re-run study_type classification across all PDF'd papers.

Reads the first page of each PDF in SharkPapers/, calls classify_study_type,
and writes three columns back to the parquet:
  - study_type           (corrigendum / letter / review / synthesis /
                          conceptual / empirical / None)
  - study_type_signal    (banner / title_kw / default_empirical / no_pdf)
  - study_type_evidence  (matched snippet or first 80 chars of banner)

Non-PDF papers get study_type = None (broad-scope rule from 2026-04-22).
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import re
import sys
from collections import defaultdict
from pathlib import Path

import fitz
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
LIB = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PARQUET = PROJECT / "outputs" / "literature_review_enriched.parquet"

sys.path.insert(0, str(PROJECT / "scripts"))
from extract_schema_columns import classify_study_type  # noqa: E402


# --------------------------------------------------------------------------
# PDF indexing (shared logic with extract_schema_columns)
# --------------------------------------------------------------------------

_FNAME_RE = re.compile(
    r"^([A-Za-zÀ-ÿ'\-]+?)[.\- ](?:etal\.)?(\d{4})\.(.+)\.pdf$",
    re.IGNORECASE,
)
_STOP = {"the", "a", "an", "of", "and", "or", "in", "on", "to", "for", "from",
         "with", "at", "by", "using", "sharks", "shark", "rays", "ray"}


def _toks(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z]{3,}", s or "") if w.lower() not in _STOP}


def _build_pdf_index() -> dict[tuple[str, str], list[tuple[Path, set[str]]]]:
    idx: dict[tuple[str, str], list[tuple[Path, set[str]]]] = defaultdict(list)
    for pdf in LIB.rglob("*.pdf"):
        m = _FNAME_RE.match(pdf.name)
        if not m:
            continue
        surname = m.group(1).lower().strip("-.' ")
        year = m.group(2)
        idx[(surname, year)].append((pdf, _toks(m.group(3))))
    return idx


def _locate_pdf(authors: str, year, title: str, idx: dict) -> Path | None:
    first = str(authors or "").split("&")[0].strip()
    m = re.match(r"([A-Za-zÀ-ÿ'\-]+)", first)
    if not m:
        return None
    surname = m.group(1).lower()
    y = str(int(year)) if pd.notna(year) else ""
    cands = idx.get((surname, y), [])
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0][0]
    q_toks = _toks(title)
    best = max(cands, key=lambda c: len(q_toks & c[1]))
    return best[0]


# --------------------------------------------------------------------------
# Per-paper worker
# --------------------------------------------------------------------------

_PDF_IDX: dict | None = None


def _init_worker(pdf_idx):
    global _PDF_IDX
    _PDF_IDX = pdf_idx


def _classify_row(args):
    lit_id, authors, year, title, journal = args
    assert _PDF_IDX is not None
    pdf = _locate_pdf(authors, year, title, _PDF_IDX)
    full_text = ""
    if pdf:
        try:
            doc = fitz.open(pdf)
            if len(doc):
                full_text = doc[0].get_text()
            doc.close()
        except Exception:
            pass
    label, signal, snippet = classify_study_type(
        title=title or "",
        full_text=full_text,
        journal=str(journal or ""),
    )
    return lit_id, label, signal, snippet


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=mp.cpu_count() - 1)
    ap.add_argument("--limit", type=int, help="Only process the first N papers (dev)")
    args = ap.parse_args()

    print("Loading parquet…", file=sys.stderr)
    df = pd.read_parquet(PARQUET)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[df["year"].notna()]

    print("Indexing PDFs…", file=sys.stderr)
    pdf_idx = _build_pdf_index()
    print(f"  {len(pdf_idx):,} (surname, year) keys · "
          f"{sum(len(v) for v in pdf_idx.values()):,} PDFs", file=sys.stderr)

    rows = list(
        zip(
            df["literature_id"].astype(str),
            df["authors"].fillna(""),
            df["year"],
            df["title"].fillna(""),
            df["journal"].fillna(""),
        )
    )
    if args.limit:
        rows = rows[: args.limit]

    print(f"Classifying {len(rows):,} papers on {args.workers} workers…", file=sys.stderr)
    with mp.Pool(args.workers, initializer=_init_worker, initargs=(pdf_idx,)) as pool:
        results = pool.map(_classify_row, rows, chunksize=50)

    out = pd.DataFrame(
        results,
        columns=["literature_id", "study_type", "study_type_signal", "study_type_evidence"],
    )
    # Deduplicate in case of duplicate literature_ids (keep first)
    out = out.drop_duplicates(subset="literature_id", keep="first")

    # Merge back into parquet (use map, not set_index assignment, because the
    # parquet has some duplicate literature_ids — harmless duplicate rows from
    # legacy imports; map handles them fine).
    print("Merging into parquet…", file=sys.stderr)
    df_full = pd.read_parquet(PARQUET)
    df_full["literature_id"] = df_full["literature_id"].astype(str)
    lookup = out.set_index("literature_id")
    for col in ["study_type", "study_type_signal", "study_type_evidence"]:
        df_full[col] = df_full["literature_id"].map(lookup[col])

    print("Writing parquet…", file=sys.stderr)
    df_full.to_parquet(PARQUET, index=False)

    # Summary
    sig = out["study_type_signal"].value_counts(dropna=False)
    typ = out["study_type"].value_counts(dropna=False)
    print("\nSignal distribution:")
    print(sig.to_string())
    print("\nStudy-type distribution:")
    print(typ.to_string())


if __name__ == "__main__":
    main()
