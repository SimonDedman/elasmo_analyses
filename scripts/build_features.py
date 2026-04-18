#!/usr/bin/env python3
"""Build / refresh the PDF feature cache.

Walks PDF_BASE, computes features for any PDF whose (size, mtime) has
changed since the last run, writes to SQLite. Multi-process pool for
CPU-bound extraction; main process is the sole SQLite writer.

Usage:
    python3 scripts/build_features.py                        # all PDFs
    python3 scripts/build_features.py --year 2020            # one year
    python3 scripts/build_features.py --only-paths f.txt     # subset
    python3 scripts/build_features.py --no-doi               # skip CrossRef
    python3 scripts/build_features.py --no-ocr               # skip scan OCR
    python3 scripts/build_features.py --workers 6
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.dedup import FeatureCache, PdfFeatures  # noqa: E402
from scripts.dedup.extractors import extract_features  # noqa: E402


PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
CACHE_PATH = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/"
                  "Data Panel/outputs/pdf_features.sqlite")


def discover_pdfs(root: Path, years: list[str] | None = None) -> list[Path]:
    if years:
        out: list[Path] = []
        for y in years:
            out.extend((root / y).glob("*.pdf"))
        return out
    return list(root.rglob("*.pdf"))


def _worker(args: tuple[str, str, bool, bool, bool]) -> tuple[str, PdfFeatures | None, str | None]:
    pdf_path_str, rel_path, ocr_if_needed, do_doi, do_crossref = args
    pdf_path = Path(pdf_path_str)
    try:
        feat = extract_features(
            pdf_path,
            rel_path=rel_path,
            ocr_if_needed=ocr_if_needed,
            do_doi=do_doi,
            do_crossref=do_crossref,
            do_visual=True,
        )
        return rel_path, feat, None
    except Exception as e:
        return rel_path, None, f"{type(e).__name__}: {e}"


def build(
    years: list[str] | None,
    only_paths: list[str] | None,
    workers: int,
    do_doi: bool,
    do_crossref: bool,
    do_ocr: bool,
    force: bool,
) -> None:
    cache = FeatureCache(CACHE_PATH)
    print(f"Cache: {CACHE_PATH} ({cache.count()} rows)")

    if only_paths:
        pdfs = [Path(p) for p in only_paths if Path(p).exists()]
    else:
        pdfs = discover_pdfs(PDF_BASE, years)
    print(f"Discovered {len(pdfs)} PDFs under {PDF_BASE}")

    todo: list[tuple[str, str, bool, bool]] = []
    skipped = 0
    for p in pdfs:
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        try:
            rel = str(p.relative_to(PDF_BASE))
        except ValueError:
            rel = p.name
        if not force and cache.is_fresh(rel, st.st_size, st.st_mtime):
            skipped += 1
            continue
        todo.append((str(p), rel, do_ocr, do_doi, do_crossref))
    print(f"Fresh in cache: {skipped};  to (re)extract: {len(todo)}")

    if not todo:
        cache.close()
        return

    t0 = time.time()
    done = 0
    errs = 0

    if workers <= 1:
        for args in todo:
            rel, feat, err = _worker(args)
            if feat is not None:
                cache.put(feat)
            else:
                errs += 1
            done += 1
            if done % 25 == 0:
                rate = done / max(1e-9, time.time() - t0)
                print(f"  {done}/{len(todo)}  {rate:.1f}/s  errs={errs}")
    else:
        with mp.get_context("spawn").Pool(workers) as pool:
            for rel, feat, err in pool.imap_unordered(_worker, todo, chunksize=1):
                if feat is not None:
                    cache.put(feat)
                else:
                    errs += 1
                done += 1
                if done % 25 == 0:
                    rate = done / max(1e-9, time.time() - t0)
                    print(f"  {done}/{len(todo)}  {rate:.1f}/s  errs={errs}")

    dt = time.time() - t0
    print(f"Done: {done} in {dt:.1f}s ({done/max(dt,1e-9):.1f}/s), errors={errs}")
    cache.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", action="append", help="Restrict to one or more year dirs")
    ap.add_argument("--only-paths", help="File listing one PDF absolute path per line")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-doi", action="store_true", help="Skip even cheap DOI regex")
    ap.add_argument("--crossref", action="store_true", help="Enable pdf2doi + CrossRef (slow network calls)")
    ap.add_argument("--no-ocr", action="store_true", help="Skip OCR on scanned PDFs")
    ap.add_argument("--force", action="store_true", help="Re-extract even if cache is fresh")
    args = ap.parse_args()

    only_paths = None
    if args.only_paths:
        only_paths = Path(args.only_paths).read_text().splitlines()

    build(
        years=args.year,
        only_paths=only_paths,
        workers=args.workers,
        do_doi=not args.no_doi,
        do_crossref=args.crossref,
        do_ocr=not args.no_ocr,
        force=args.force,
    )


if __name__ == "__main__":
    main()
