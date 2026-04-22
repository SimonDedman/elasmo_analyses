#!/usr/bin/env python3
"""Regenerate docs/papers_data.json by removing entries whose PDFs are on disk.

Matches queue entries against SharkPapers/ PDFs by (first-author-surname, year)
plus title-word overlap to avoid false positives for common surname/year pairs.

Also updates the "Updated:" stamp in docs/remaining_downloads.html.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
LIB = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
QUEUE = PROJECT / "docs" / "papers_data.json"
HTML_PAGE = PROJECT / "docs" / "remaining_downloads.html"

_FNAME_RE = re.compile(
    r"^([A-Za-zÀ-ÿ'\-]+?)[.\- ](?:etal\.)?(\d{4})\.(.+)\.pdf$",
    re.IGNORECASE,
)
_STOP = {
    "the", "a", "an", "of", "and", "or", "in", "on", "to", "for", "from",
    "with", "at", "by", "using", "de", "la", "le", "du", "des", "un", "una",
    "el", "los", "las", "sharks", "shark", "rays", "ray", "first", "new",
    "record", "species", "study", "analysis", "review", "report",
}


def tokens(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z]{3,}", text or "") if w.lower() not in _STOP}


def surname_from_authors(authors: str) -> str:
    first = (authors or "").split("&")[0].strip()
    m = re.match(r"([A-Za-zÀ-ÿ'\-]+)", first)
    return m.group(1).lower() if m else ""


def build_pdf_index() -> dict[tuple[str, str], list[set[str]]]:
    idx: dict[tuple[str, str], list[set[str]]] = defaultdict(list)
    for pdf in LIB.rglob("*.pdf"):
        m = _FNAME_RE.match(pdf.name)
        if not m:
            continue
        surname = m.group(1).lower().strip("-.' ")
        year = m.group(2)
        idx[(surname, year)].append(tokens(m.group(3)))
    return idx


def filter_queue(queue: list[dict], pdf_idx: dict) -> tuple[list[dict], list[dict]]:
    kept, removed = [], []
    for entry in queue:
        surname = surname_from_authors(entry.get("authors", ""))
        year = str(entry.get("year", "")).strip()
        if year.endswith(".0"):
            year = year[:-2]
        candidates = pdf_idx.get((surname, year), []) if (surname and year) else []
        if not candidates:
            kept.append(entry)
            continue
        q_tok = tokens(entry.get("title", ""))
        min_overlap = 1 if len(q_tok) < 4 else 2
        if any(len(q_tok & pdf_t) >= min_overlap for pdf_t in candidates):
            removed.append(entry)
        else:
            kept.append(entry)
    return kept, removed


def update_html_stamp(new_count: int) -> None:
    if not HTML_PAGE.exists():
        return
    html = HTML_PAGE.read_text(encoding="utf-8")
    today = date.today().isoformat()
    new_html = re.sub(
        r'Updated:\s*\d{4}-\d{2}-\d{2}',
        f"Updated: {today}",
        html,
        count=1,
    )
    if new_html != html:
        HTML_PAGE.write_text(new_html, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = ap.parse_args()

    print("Scanning PDF library…")
    pdf_idx = build_pdf_index()
    total_pdfs = sum(len(v) for v in pdf_idx.values())
    print(f"  {len(pdf_idx):,} (surname, year) keys · {total_pdfs:,} PDFs indexed")

    print("Loading queue…")
    queue = json.loads(QUEUE.read_text())
    print(f"  {len(queue):,} entries loaded")

    kept, removed = filter_queue(queue, pdf_idx)
    print(f"Removing {len(removed):,} entries with matched PDFs on disk")
    print(f"New queue size: {len(kept):,}")

    if args.dry_run:
        print("\n(dry-run — nothing written)")
        return

    # Reassign id field to be consecutive (DataTables uses it as a stable key)
    for i, entry in enumerate(kept, start=1):
        entry["id"] = i

    QUEUE.write_text(json.dumps(kept, indent=2, ensure_ascii=False))
    update_html_stamp(len(kept))
    print(f"\nWrote {QUEUE.relative_to(PROJECT)} ({len(kept):,} entries)")
    print(f"Updated Updated-stamp in {HTML_PAGE.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
