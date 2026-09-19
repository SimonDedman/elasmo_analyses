#!/usr/bin/env python3
"""Split a staged whole volume into per-row PDFs using the printed page ranges
already recorded on the queue rows, and stage them by literature_id.

For each outstanding queue row matched by --venue, the page ranges are read
from the tail of `findspot_raw` (e.g. "...: 259-260, 262-264"), shifted by
--offset (pdf_page - printed_page, MEASURED per volume from the running page
numbers), and the pages are copied into <staging-dir>/<literature_id>.pdf.

Identity is checked on the EXTRACTED pages, never assumed from the page maths:
  * the row's distinctive title words (>= --min-coverage of them), and
  * the first author's surname,
must both occur in the extracted text. "Species accounts: A b, C d" and
"Families X, Y" rows are tested on every named taxon instead of a title.
A row that fails is written as <lid>.pdf.held and reported, never staged.

Writes manifest.csv and coverage.json beside the PDFs. Touches nothing else:
file the result with `acquire_cascade.py --finalize-only --staging-dir <dir>`
(ONE pass per staging dir; never re-finalize a kept folder).

Usage:
  python3 scripts/split_volume_by_pages.py \
      --volume database/book_chapter_staging/A2_reports_tr90_pratt_1990_elasmobranchs_living_resources.pdf \
      --venue "NOAA Technical Report NMFS, 90" --offset 10 \
      --staging-dir outputs/download_push_2026-09-18/split_pratt1990
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_free_sources import (  # noqa: E402
    compile_patterns, first_surname, load_papers, outstanding_scope, title_tokens,
)

RANGE_RE = re.compile(r"(\d{1,4})\s*[–—-]\s*(\d{1,4})|(\d{1,4})")


def _ascii(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def page_ranges(findspot: str):
    """Printed page ranges from the tail of a findspot string, after the last colon."""
    tail = (findspot or "").rsplit(":", 1)[-1]
    tail = re.sub(r"figs?\.?\s*\d+\s*[–-]?\s*\d*|tabs?\.?\s*\d+|pls?\.?\s*\d+", "", tail, flags=re.I)
    out = []
    for m in RANGE_RE.finditer(tail):
        if m.group(1):
            a, b = int(m.group(1)), int(m.group(2))
            if b < a:  # "304-26" style abbreviation
                b = int(str(a)[: len(str(a)) - len(str(b))] + str(b))
        else:
            a = b = int(m.group(3))
        if 0 < a <= b and b - a < 400:
            out.append((a, b))
    return out


def taxa_in_title(title: str):
    """Binomials / family names for 'Species accounts: ...' and 'Families ...' rows, else []."""
    m = re.match(r"\s*(species accounts?|famil(?:y|ies|ie))\s*:?\s*(.*)", title or "", re.I)
    if not m:
        return []
    parts = [p.strip(" .") for p in re.split(r",|\band\b|&", m.group(2)) if p.strip(" .")]
    return [p for p in parts if re.match(r"^[A-Z][a-z]+", p)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--volume", required=True)
    ap.add_argument("--venue", required=True, action="append",
                    help="pattern matched against journal / journal_clean / findspot_raw (repeatable)")
    ap.add_argument("--offset", type=int, required=True, help="pdf_page - printed_page for this volume")
    ap.add_argument("--staging-dir", required=True)
    ap.add_argument("--min-coverage", type=float, default=0.8)
    ap.add_argument("--year", help="only rows of this year (guards against a shared editor stub)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = pymupdf.open(args.volume)
    staging = Path(args.staging_dir)
    staging.mkdir(parents=True, exist_ok=True)
    if not args.dry_run and any(staging.glob("*.pdf")):
        sys.exit(f"{staging} already holds PDFs: use a fresh staging dir per run")

    rows = outstanding_scope(load_papers(), compile_patterns(*args.venue))
    if args.year:
        rows = [r for r in rows if str(r.get("year"))[:4] == args.year]
    cov = {"volume": args.volume, "offset": args.offset, "rows_in_scope": len(rows), "staged": 0,
           "failed": {"no_page_range": 0, "pages_outside_volume": 0, "identity_failed": 0}, "not_attempted": 0}
    man = []
    for r in rows:
        lid = str(r["literature_id"])
        rec = {"literature_id": lid, "authors": (r.get("authors") or "")[:60], "title": (r.get("title") or "")[:100]}
        man.append(rec)
        ranges = page_ranges(r.get("findspot_raw") or r.get("journal") or "")
        if not ranges:
            cov["failed"]["no_page_range"] += 1
            rec["status"] = "no_page_range"
            continue
        pdf_pages = [p + args.offset for a, b in ranges for p in range(a, b + 1)]
        rec["printed_pages"] = ", ".join(f"{a}-{b}" for a, b in ranges)
        if min(pdf_pages) < 1 or max(pdf_pages) > len(doc):
            cov["failed"]["pages_outside_volume"] += 1
            rec["status"] = "pages_outside_volume"
            continue
        text = _ascii(" ".join(doc[p - 1].get_text() for p in pdf_pages))
        taxa = taxa_in_title(r.get("title"))
        if taxa:
            found = [t for t in taxa if _ascii(t) in text or _ascii(t.split()[-1]) in text]
            title_ok = len(found) == len(taxa)
            detail = f"taxa {len(found)}/{len(taxa)}"
        else:
            want = title_tokens(re.sub(r"^\s*chapter\s+\d+\s*[.:]\s*", "", r.get("title") or "", flags=re.I))
            first = title_tokens(_ascii(" ".join(doc[p - 1].get_text() for p in pdf_pages[:2])))
            hit = len({_ascii(w) for w in want} & first)
            title_ok = bool(want) and hit / len(want) >= args.min_coverage
            detail = f"title {hit}/{len(want)} on first 2 pages"
        sur = _ascii(first_surname(r.get("authors") or ""))
        sur_ok = bool(sur) and sur in text
        rec["check"] = f"{detail}; surname={'yes' if sur_ok else 'no'}; {len(pdf_pages)} pp"
        ok = title_ok and sur_ok
        if args.dry_run:
            rec["status"] = "would_stage" if ok else "would_hold"
            cov["staged" if ok else "not_attempted"] += 1
            continue
        out = pymupdf.open()
        for p in pdf_pages:
            out.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
        dest = staging / (f"{lid}.pdf" if ok else f"{lid}.pdf.held")
        out.save(dest)
        if ok:
            cov["staged"] += 1
            rec["status"] = "staged"
        else:
            cov["failed"]["identity_failed"] += 1
            rec["status"] = "held_identity_failed"

    fields = ["literature_id", "authors", "title", "printed_pages", "check", "status"]
    name = "manifest_dry_run.csv" if args.dry_run else "manifest.csv"
    with open(staging / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for m in man:
            w.writerow({k: m.get(k, "") for k in fields})
    if not args.dry_run:
        json.dump(cov, open(staging / "coverage.json", "w"), indent=2)
    print(json.dumps(cov, indent=1))
    for m in man:
        if m.get("status") not in ("staged", "would_stage"):
            print("  HOLD", m["literature_id"], m.get("status"), "|", m.get("printed_pages", ""), "|", m.get("check", ""), "|", m["title"][:60])


if __name__ == "__main__":
    main()
