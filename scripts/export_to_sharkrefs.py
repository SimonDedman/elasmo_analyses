#!/usr/bin/env python3
"""
Track papers we hold that Shark References does not, and stage them for the SR
team to collect.

Papers acquired outside the SR crawl (coauthor deliveries, book chapters, BHL
and archive.org finds) are given a literature_id in the 600000+ range by
stage_orphan_pdfs.py and appended to the master CSV. Nothing has recorded them
as "SR does not have this" until now: the ID range was the only marker, and the
staging log is rewritten on every run.

This script maintains a durable manifest of those papers and copies their PDFs
into a folder the SR team can reach over Synology. They download and delete;
deletion is the signal that a paper has been collected, and the manifest keeps
the record after the file is gone.

Usage:
    python3 scripts/export_to_sharkrefs.py --check    # report, copy nothing
    python3 scripts/export_to_sharkrefs.py            # refresh manifest + export
    python3 scripts/export_to_sharkrefs.py --reconcile  # mark collected files
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ingest_pdfs import PDF_BASE, PROJECT, build_filename  # noqa: E402

EXPORT_DIR = PROJECT / "database/SharkRefsExport"
MANIFEST = PROJECT / "outputs/non_sr_papers.csv"
MASTER_CSV_DIR = PROJECT / "outputs/shark_references_bulk"

# literature_ids at or above this were staged by us, not crawled from SR.
ORPHAN_ID_BASE = 600000

FIELDS = ["literature_id", "doi", "year", "authors", "title", "journal",
          "library_path", "export_filename", "first_seen", "exported_at",
          "collected_at", "status", "notes"]

README = """Shark References — papers held by the EEA 2025 Data Panel review
that are not in the Shark References database.

Each PDF here corresponds to a row in manifest.csv, which carries the
bibliographic metadata (DOI, year, authors, title, journal).

Please download whatever is useful and DELETE the PDF from this folder when
you are done. These are duplicates of files we hold, so deleting costs us
nothing, and an empty folder tells us everything has been collected.

manifest.csv is regenerated automatically; do not edit it. If something looks
wrong, or a paper is already in Shark References under a different record,
tell Simon rather than editing the sheet.

Contact: Simon Dedman <simondedman@gmail.com>
"""


def latest_master() -> Path | None:
    files = sorted(MASTER_CSV_DIR.glob("shark_references_complete_*.csv"),
                   key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    with open(MANIFEST, "r", encoding="utf-8") as f:
        return {r["literature_id"]: r for r in csv.DictReader(f)}


def save_manifest(entries: dict[str, dict]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for k in sorted(entries, key=lambda x: int(float(x))):
            w.writerow({fld: entries[k].get(fld, "") for fld in FIELDS})


def find_library_pdf(row: dict) -> Path | None:
    """Where stage_orphan_pdfs would have filed this paper's PDF."""
    try:
        year = str(int(float(row.get("year") or 0)))
    except (ValueError, TypeError):
        year = "Unknown"
    candidate = PDF_BASE / year / build_filename(row)
    if candidate.exists():
        return candidate
    # Filename conventions have shifted over time; fall back to a year-folder
    # scan on the first-author surname so older stagings are still found.
    folder = PDF_BASE / year
    if folder.is_dir():
        surname = (row.get("authors") or "").split(",")[0].split("&")[0].strip()
        if surname:
            hits = sorted(folder.glob(f"{surname}*.pdf"))
            if len(hits) == 1:
                return hits[0]
    return None


def collect_non_sr_rows() -> list[dict]:
    master = latest_master()
    if master is None:
        return []
    out = []
    with open(master, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            raw = (r.get("literature_id") or "").strip()
            if not raw:
                continue
            try:
                lid = int(float(raw))
            except ValueError:
                continue
            if lid >= ORPHAN_ID_BASE:
                r["literature_id"] = str(lid)
                out.append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="Report what would change; copy nothing")
    ap.add_argument("--reconcile", action="store_true",
                    help="Mark exported files the SR team has since deleted as collected")
    args = ap.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    manifest = load_manifest()
    rows = collect_non_sr_rows()

    print(f"{'=' * 70}\n  Non-SR paper export — {now}\n{'=' * 70}")
    print(f"  Papers with literature_id >= {ORPHAN_ID_BASE}: {len(rows)}")
    print(f"  Manifest entries already tracked:  {len(manifest)}")

    added, exported, missing = 0, 0, []
    for r in rows:
        lid = r["literature_id"]
        entry = manifest.get(lid)
        if entry is None:
            entry = {f: "" for f in FIELDS}
            entry.update({
                "literature_id": lid,
                "doi": (r.get("doi") or "").strip(),
                "year": (r.get("year") or "").strip(),
                "authors": (r.get("authors") or "").strip(),
                "title": (r.get("title") or "").strip(),
                "journal": (r.get("findspot") or "").strip(),
                "first_seen": now,
                "status": "pending",
            })
            manifest[lid] = entry
            added += 1

        if entry.get("status") == "collected":
            continue

        pdf = find_library_pdf(r)
        if pdf is None:
            missing.append(lid)
            entry["notes"] = "PDF not found in library"
            continue
        entry["library_path"] = str(pdf)

        dest_name = f"{lid}_{pdf.name}"
        entry["export_filename"] = dest_name
        dest = EXPORT_DIR / dest_name
        if dest.exists():
            entry["status"] = "exported"
            continue
        if entry.get("exported_at") and args.reconcile:
            # Was exported before and is gone now: the SR team collected it.
            entry["status"] = "collected"
            entry["collected_at"] = now
            continue
        if args.check:
            print(f"  WOULD EXPORT {dest_name}")
            exported += 1
            continue
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf, dest)
        entry["exported_at"] = now
        entry["status"] = "exported"
        exported += 1
        print(f"  EXPORTED {dest_name}")

    print(f"\n  New manifest entries: {added}")
    print(f"  Exported this run:    {exported}")
    if missing:
        print(f"  PDF not found for:    {len(missing)} ({', '.join(missing[:8])})")

    if args.check:
        print("\n  (dry run — nothing written)")
        return 0

    save_manifest(manifest)
    print(f"  Manifest: {MANIFEST}")

    if EXPORT_DIR.exists():
        (EXPORT_DIR / "README.txt").write_text(README, encoding="utf-8")
        sheet = EXPORT_DIR / "manifest.csv"
        with open(sheet, "w", newline="", encoding="utf-8") as f:
            cols = ["literature_id", "doi", "year", "authors", "title",
                    "journal", "export_filename"]
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for e in manifest.values():
                if e.get("status") == "exported":
                    w.writerow({c: e.get(c, "") for c in cols})
        pending = sum(1 for e in manifest.values() if e.get("status") == "exported")
        print(f"  Export folder: {EXPORT_DIR} ({pending} PDFs awaiting collection)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
