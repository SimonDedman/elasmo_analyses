#!/usr/bin/env python3
"""Find queue rows whose PDF is ALREADY in the library, and verify by opening it.

The queue is meant to be the truth: a row is outstanding until its PDF is filed.
That breaks when a PDF gets filed without the row being closed, and the paper then
sits on the download hub forever while somebody's copy is already on disk. Found
2026-09-23 while checking why 89 of Elena's marked papers were still outstanding:
83 of them were filed and verified, and her drop folder was empty because the PDFs
had been ingested and removed.

Matching is deliberately conservative, then checked rather than trusted
([[feedback_ingest_checks_must_test_identity]]):

  1. index the library by (first-author surname, year) from its filenames;
  2. a candidate must have its (truncated) filename title covered by the record
     title at >= --cover;
  3. the PDF is then OPENED and its first two pages must carry >= 80% of the
     record's title words plus the first author's surname (or >= 95% of the title
     words alone, for old papers that print no author on page one).

Writes a CSV with one row per candidate and a verdict of verified / needs_eyes.
It changes nothing: closing the rows is a separate, deliberate step through
scripts/lib/papers_data_io.py::mutate().

  python3 scripts/find_queue_rows_already_filed.py
  python3 scripts/find_queue_rows_already_filed.py --csv outputs/already_filed.csv --no-verify
"""
import argparse
import csv
import json
import os
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
QUEUE = ROOT / "docs" / "papers_data.json"
OUTSTANDING = {"needs_library", "needs_pdf", "sr_sync_new"}
FILENAME = re.compile(r"([^.]+?)(?:\.etal)?\.(\d{4})\.(.*)\.pdf$", re.I)


def al(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def toks(t, n=5):
    """Five-letter prefixes of the words of a title: library filenames abbreviate."""
    return {w[:n] for w in re.findall(r"[a-z]{4,}", al(t))}


def surname(authors):
    first = re.split(r"[;&]| and ", str(authors or ""))[0]
    return al(first.split(",")[0].strip())


def library_index():
    idx = defaultdict(list)
    n = 0
    for root, _, files in os.walk(LIB):
        for f in files:
            if not f.lower().endswith(".pdf"):
                continue
            n += 1
            m = FILENAME.match(f)
            if m:
                idx[(al(m.group(1)), m.group(2))].append((f, str(Path(root) / f)))
    return idx, n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=ROOT / "outputs" / "queue_rows_already_filed.csv")
    ap.add_argument("--cover", type=float, default=0.85, help="share of the filename's title words the record must contain")
    ap.add_argument("--no-verify", action="store_true", help="skip opening the PDFs (candidates only, never trust this)")
    ap.add_argument("--marked-by", help="only rows this person marked in the shared record (needs the reconcile CSV)")
    ap.add_argument("--reconcile-csv", type=Path, help="CSV from reconcile_download_marks.py, for --marked-by")
    args = ap.parse_args()

    rows = [p for p in json.load(open(QUEUE))
            if p.get("last_status") in OUTSTANDING and p.get("triage") != "conference_abstract"]
    if args.marked_by:
        if not args.reconcile_csv:
            raise SystemExit("--marked-by needs --reconcile-csv")
        keep = {r["literature_id"] for r in csv.DictReader(open(args.reconcile_csv)) if r["marked_by"] == args.marked_by}
        rows = [p for p in rows if str(p.get("literature_id")) in keep]
    idx, n_lib = library_index()
    print(f"library PDFs indexed: {n_lib:,}; queue rows checked: {len(rows):,}")

    cands = []
    for p in rows:
        year = str(p.get("year") or "").split(".")[0]
        sur, want = surname(p.get("authors")), toks(p.get("title"))
        if not sur or not want:
            continue
        for fname, full in idx.get((sur, year), []):
            ft = toks(fname.rsplit(".pdf", 1)[0].split(".", 2)[-1])
            if ft and len(ft & want) / len(ft) >= args.cover:
                cands.append({"lid": str(p.get("literature_id")), "status": p.get("last_status"),
                              "year": year, "authors": p.get("authors"), "title": p.get("title"),
                              "doi": p.get("doi") or "", "pdf": full})
                break
    print(f"candidates (library filename matches the record): {len(cands):,}")

    verified = 0
    for c in cands:
        if args.no_verify:
            c["title_cov"], c["author_on_page"], c["verdict"] = "", "", "unchecked"
            continue
        try:
            txt = subprocess.run(["pdftotext", "-f", "1", "-l", "2", c["pdf"], "-"],
                                 capture_output=True, text=True, timeout=30).stdout
        except (subprocess.TimeoutExpired, OSError):
            txt = ""
        want = toks(c["title"])
        cov = len(want & toks(txt)) / max(len(want), 1)
        sur = surname(c["authors"])
        on_page = bool(sur and sur in al(txt))
        c["title_cov"] = round(cov, 2)
        c["author_on_page"] = on_page
        c["verdict"] = "verified" if ((cov >= 0.8 and on_page) or cov >= 0.95) else "needs_eyes"
        verified += c["verdict"] == "verified"
    if not args.no_verify:
        print(f"verified by opening the PDF: {verified:,}; needs eyes: {len(cands) - verified:,}")
    print("by status:", Counter(c["status"] for c in cands).most_common())

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["lid", "status", "year", "authors", "title", "doi",
                                           "pdf", "title_cov", "author_on_page", "verdict"])
        w.writeheader()
        for c in sorted(cands, key=lambda c: (c["verdict"], c["lid"])):
            w.writerow(c)
    print(f"wrote {args.csv}")
    print("Nothing was changed. Close the verified rows only on a deliberate pass through "
          "scripts/lib/papers_data_io.py::mutate().")


if __name__ == "__main__":
    main()
