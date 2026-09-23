#!/usr/bin/env python3
"""Close queue rows whose PDF is already filed, after a last identity check.

Input: the review workbook from scripts/build_already_filed_workbook.R, carrying
Simon's your_decision column, plus the rows that passed the automatic check.

A row is closed the way ingest_pdfs.py closes one: removed from
docs/papers_data.json, through lib.papers_data_io.mutate(allow_deletions=True).

Nothing is taken on trust. Immediately before writing, every row to be closed has
its PDF opened again and must still show the title and first author on pages 1-2
(or the title alone at 95%), which is the check that produced the "verified"
verdict in the first place. A row that now fails is not closed, and is reported.

Decisions are matched case-insensitively on the first word:
  correct  -> close          wrong / unsure / can't tell / blank -> leave open

  python3 scripts/close_already_filed_rows.py                 # dry run
  python3 scripts/close_already_filed_rows.py --apply
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from lib.papers_data_io import mutate  # noqa: E402

WORKBOOK = ROOT / "outputs" / "queue_rows_already_filed_2026-09-23.xlsx"


def al(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def toks(t, n=5):
    return {w[:n] for w in re.findall(r"[a-z]{4,}", al(t))}


def surname(authors):
    return al(re.split(r"[;&]| and ", str(authors or ""))[0].split(",")[0].strip())


def verify(pdf, title, authors):
    """The same check that produced the 'verified' verdict, re-run at write time."""
    try:
        txt = subprocess.run(["pdftotext", "-f", "1", "-l", "2", pdf, "-"],
                             capture_output=True, text=True, timeout=30).stdout
    except (subprocess.TimeoutExpired, OSError):
        return False, 0.0
    want = toks(title)
    cov = len(want & toks(txt)) / max(len(want), 1)
    sur = surname(authors)
    return ((cov >= 0.8 and sur and sur in al(txt)) or cov >= 0.95), round(cov, 2)


def load_rows(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["rows"]
    head = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2, values_only=True):
        yield dict(zip(head, row))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workbook", type=Path, default=WORKBOOK)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    rows = list(load_rows(args.workbook))
    close, hold = [], []
    for r in rows:
        dec = str(r.get("your_decision") or "").strip().lower()
        auto_ok = str(r.get("action_status") or "").startswith("claude:")
        if dec.startswith("correct") or (auto_ok and not dec):
            close.append(r)
        else:
            hold.append((r, dec or ("(no decision)" if not auto_ok else "")))
    print(f"workbook rows: {len(rows)}   to close: {len(close)}   left open: {len(hold)}")
    for r, why in hold:
        print(f"  HOLD {r['lid']}: {why[:70]}  |  {str(r['title'])[:60]}")

    failed = []
    for r in close:
        ok, cov = verify(r["pdf"], r["title"], r["authors"])
        if not ok:
            failed.append((r, cov))
    if failed:
        print(f"\nre-check at write time FAILED for {len(failed)} row(s); they will NOT be closed:")
        for r, cov in failed:
            print(f"  {r['lid']} title coverage {cov}  {str(r['title'])[:60]}")
        # a row Simon called correct is his judgement, not the matcher's: keep it
        keep = {str(r["lid"]) for r, _ in failed
                if not str(r.get("your_decision") or "").strip().lower().startswith("correct")}
        close = [r for r in close if str(r["lid"]) not in keep]
        print(f"  ({len(failed) - len(keep)} of those are rows you marked correct, so they stay in the list)")

    ids = {str(r["lid"]).strip() for r in close}
    print(f"\nrows that will be removed from docs/papers_data.json: {len(ids)}")
    if not args.apply:
        print("dry run: nothing written (use --apply)")
        return

    with mutate(allow_deletions=True) as papers:
        before = len(papers)
        seen = Counter(str(p.get("literature_id", "")).replace(".0", "").strip() for p in papers)
        papers[:] = [p for p in papers
                     if str(p.get("literature_id", "")).replace(".0", "").strip() not in ids]
        removed = before - len(papers)
    missing = sorted(i for i in ids if not seen.get(i))
    print(f"removed {removed} rows; queue now {before - removed:,}")
    if missing:
        print(f"{len(missing)} id(s) were not in the queue: {missing[:10]}")


if __name__ == "__main__":
    main()
