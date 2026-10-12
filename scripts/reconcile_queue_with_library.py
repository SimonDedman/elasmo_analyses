#!/usr/bin/env python3
"""Close todo-list rows whose PDF is already in the library.

A queue row leaves docs/papers_data.json only when a filing path closes it. A PDF
that reaches the library any other way (an old Zotero copy, a BHL harvest, a
manual rename, a record merge) is mapped by build_pdf_id_map.py but the row stays
on the list, and the team keeps downloading it: on 2026-10-12 three rows had sat
on the list since October 2025 with verified PDFs in the library (Chisholm 2004,
Underwood 2004, Van den Berg 1983), and a team member re-downloaded all three.

For every queue row that pdf_id_map.csv maps to an existing PDF, the PDF text
must pass the drop-audit identity test (title words + first-author surname,
OCR for scans, the byline anywhere for long documents). Passing rows are closed
through ingest_pdfs.update_papers_data_json; failing rows are reported (the map
may point at a whole abstract book or a wrong file) and left open.

    python3 scripts/reconcile_queue_with_library.py            # report only
    python3 scripts/reconcile_queue_with_library.py --apply    # close passing rows

Writes outputs/queue_reconcile_<date>.csv (every candidate, closed or not).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import audit_drop_folder as adf  # noqa: E402
import ingest_pdfs as ing  # noqa: E402

PROJECT = ing.PROJECT
OUT = PROJECT / f"outputs/queue_reconcile_{date.today():%Y-%m-%d}.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    pdfmap = {}
    with open(PROJECT / "outputs/pdf_id_map.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pdfmap.setdefault(str(r["literature_id"]), r)
    queue = json.loads((PROJECT / "docs/papers_data.json").read_text())
    cands = {str(e["literature_id"]): e for e in queue if str(e["literature_id"]) in pdfmap}
    adf._init()
    rows = []
    for lid, e in sorted(cands.items()):
        pdf = Path(pdfmap[lid]["pdf"])
        row = {"literature_id": lid, "title": (e.get("title") or "")[:120], "pdf": str(pdf),
               "map_method": pdfmap[lid]["method"], "pages": "", "title_ok": "", "surname_ok": "",
               "decision": ""}
        if not pdf.exists():
            row["decision"] = "open: mapped PDF missing on disk"
            rows.append(row)
            continue
        try:
            tp = ing.ensure_text_extractable(pdf)
            text, pages = adf.page_text(tp)
            if pages > 30:
                text, _ = adf.page_text(tp, 10)
            rec = adf.IDX["by_id"].get(lid) or {"title": e.get("title"), "authors": e.get("authors"),
                                                "doi": e.get("doi")}
            t_ok, s_ok, *_ = adf.identity(text, rec, fuzzy=True)
            if t_ok and not s_ok:
                s_ok = adf.surname_present(adf.page_text(tp, 60)[0], rec.get("authors"), True)
            row.update(pages=pages, title_ok=t_ok, surname_ok=s_ok)
            row["decision"] = "close" if (t_ok and s_ok) else "open: library PDF fails the identity test"
        except Exception as ex:  # noqa: BLE001
            row["decision"] = f"open: cannot read PDF ({ex})"
        rows.append(row)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["literature_id"])
        w.writeheader()
        w.writerows(rows)
    close = {r["literature_id"] for r in rows if r["decision"] == "close"}
    print(f"queue rows mapped to a library PDF: {len(rows)}; identity passes: {len(close)}; "
          f"left open: {len(rows) - len(close)} -> {OUT.name}")
    for r in rows:
        print(f"  {r['literature_id']:>7} {r['decision'][:45]:45} {r['title'][:60]}")
    if a.apply and close:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        label = f"queue reconciliation {date.today()} (library PDF already present, identity checked)"
        ing.update_papers_data_json(close, set(), ts, label)
        ing.update_tracking_dbs(close, {l: Path(pdfmap[l]["pdf"]).name for l in close}, ts, label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
