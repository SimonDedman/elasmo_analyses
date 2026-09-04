#!/usr/bin/env python3
"""Rename PDFs onto the paper they actually contain, and fix the acquisition state.

A misfiled PDF that is the ONLY copy of its content cannot be deleted: doing
so destroys a real paper to fix a filename.  The repair is a rename, onto the
paper the file actually holds.

Renaming moves the claim, so the accounting has to move with it.  The paper
the filename USED to claim no longer has a PDF and must go back on the
wanted list, or it silently counts as acquired for ever, which is the same
bookkeeping error the misfiling caused in the first place.

Input is a small CSV, one row per file:

    current_path,correct_literature_id,claimed_literature_id,action
    /path/to/Wrong.2015.Name.pdf,12614,23676,rename
    /path/to/Fragment.2017.Name.pdf,,25250,delete

``claimed_literature_id`` is the paper the filename currently claims, which
is the one about to lose its PDF.  State it: inferring it by fuzzy title
match against 31,653 corpus rows picked the wrong record twice out of four,
and a wrong id here silently leaves a paper counted as acquired.

Filenames are built by ``sync_shark_references.build_pdf_path`` so they match
the library convention exactly rather than a convention invented here.

Usage
-----
    python3 scripts/repair_misfiled_pdfs.py --plan plan.csv
    python3 scripts/repair_misfiled_pdfs.py --plan plan.csv --apply
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT = Path(__file__).resolve().parent.parent
PAPERS_DATA_JSON = PROJECT / "docs" / "papers_data.json"
TRACKER_DB = PROJECT / "database" / "download_tracker.db"
VIZ_DATA = PROJECT / "outputs" / "viz_data.csv"


def load_corpus(ids: set[str]) -> dict[str, dict]:
    """The corpus rows for the papers involved, keyed by literature_id."""
    csv.field_size_limit(sys.maxsize)
    keep = {}
    wanted = {i for i in ids if i}
    with open(VIZ_DATA) as fh:
        for row in csv.DictReader(fh):
            lid = str(row.get("literature_id", "")).strip()
            try:
                lid = str(int(float(lid)))
            except (ValueError, TypeError):
                pass
            if lid in wanted and lid not in keep:
                keep[lid] = {k: row.get(k) for k in
                             ("literature_id", "year", "authors", "title",
                              "doi", "journal")}
    return keep


def target_path(record: dict) -> Path:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_sync", Path(__file__).resolve().parent / "sync_shark_references.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_pdf_path({
        "authors": record["authors"],
        "year": int(float(record["year"])),
        "title": record["title"],
    })


def read_plan(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            row["correct_literature_id"] = str(
                row.get("correct_literature_id", "")).strip()
            row["claimed_literature_id"] = str(
                row.get("claimed_literature_id", "") or "").strip()
            row["action"] = (row.get("action") or "rename").strip().lower()
            rows.append(row)
    return rows


def claimed_id(path: str, corpus_by_title, log=print) -> str | None:
    """Fallback guess at which paper a filename claims.

    Only used when the plan does not say.  It is a fuzzy title match over
    31,653 rows and it got two of four wrong in testing, so prefer the
    explicit column: a wrong id here leaves a paper counted as acquired for
    ever, which is the bookkeeping error this whole repair exists to fix.
    """
    import re
    import unicodedata

    stem = os.path.basename(path)[:-4]
    parts = stem.split(".")
    title = stem
    for i, part in enumerate(parts):
        if re.fullmatch(r"(1[6-9]|20)\d\d", part):
            title = ".".join(parts[i + 1:])
            break

    def norm(s):
        s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
        return set(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())

    q = norm(title)
    best, best_score = None, 0.0
    for lid, t in corpus_by_title:
        tn = norm(t)
        if not tn or not q:
            continue
        score = len(q & tn) / min(len(q), len(tn))
        if score > best_score:
            best, best_score = lid, score
    return best if best_score >= 0.8 else None


def update_papers_data(readd: dict[str, dict], remove: set[str],
                       apply: bool, log=print) -> tuple[int, int]:
    """Put papers that lost their PDF back on the wanted list.

    docs/papers_data.json holds what is still MISSING, so acquisition is
    recorded by ABSENCE. De-acquiring means adding the entry back.
    """
    data = json.loads(PAPERS_DATA_JSON.read_text())
    present = set()
    for entry in data:
        lid = str(entry.get("literature_id", "")).strip()
        try:
            lid = str(int(float(lid)))
        except (ValueError, TypeError):
            pass
        present.add(lid)

    # Match the existing entries' types, or the file becomes subtly
    # heterogeneous and the next consumer has to handle both.
    next_id = max((int(e["id"]) for e in data
                   if str(e.get("id", "")).isdigit()), default=0) + 1

    def as_year(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    added = 0
    for lid, rec in readd.items():
        if lid in present:
            continue
        data.append({
            "literature_id": lid,
            "id": next_id + added,
            "title": rec.get("title", ""),
            "authors": rec.get("authors", ""),
            "year": as_year(rec.get("year")),
            "doi": rec.get("doi", "") or "",
            "journal": rec.get("journal", "") or "",
            "notes": f"re-added {datetime.now():%Y-%m-%d}: PDF was misfiled "
                     f"and has been renamed onto its real paper",
            "last_status": "needs_pdf",
        })
        added += 1

    removed = 0
    if remove:
        before = len(data)
        kept = []
        for entry in data:
            lid = str(entry.get("literature_id", "")).strip()
            try:
                lid = str(int(float(lid)))
            except (ValueError, TypeError):
                pass
            if lid in remove:
                continue
            kept.append(entry)
        removed = before - len(kept)
        data = kept

    if apply and (added or removed):
        # Match the file's existing serialisation exactly: indent=2 with
        # escaped non-ASCII. Writing it any other way reformats all 12,000
        # entries and buries four real changes in a 490,000-line diff.
        tmp = PAPERS_DATA_JSON.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        os.replace(tmp, PAPERS_DATA_JSON)
    return added, removed


def update_tracker(lost: set[str], gained: set[str], apply: bool,
                   log=print) -> tuple[int, int]:
    """Clear the 'downloaded' rows for papers that no longer have a PDF."""
    if not TRACKER_DB.exists() or not TRACKER_DB.stat().st_size:
        return 0, 0
    db = sqlite3.connect(str(TRACKER_DB))
    try:
        lit_to_paper = {}
        for pid, lid in db.execute("SELECT id, literature_id FROM papers"):
            try:
                lit_to_paper[str(int(float(lid)))] = pid
            except (ValueError, TypeError):
                continue
        cleared = marked = 0
        for lid in lost:
            pid = lit_to_paper.get(lid)
            if pid is None:
                continue
            rows = db.execute(
                "SELECT COUNT(*) FROM download_status "
                "WHERE paper_id = ? AND status = 'downloaded'", (pid,)).fetchone()[0]
            if not rows:
                continue
            if apply:
                db.execute("DELETE FROM download_status "
                           "WHERE paper_id = ? AND status = 'downloaded'", (pid,))
            cleared += rows
        for lid in gained:
            pid = lit_to_paper.get(lid)
            if pid is None:
                continue
            exists = db.execute(
                "SELECT 1 FROM download_status "
                "WHERE paper_id = ? AND status = 'downloaded'", (pid,)).fetchone()
            if exists:
                continue
            if apply:
                db.execute(
                    "INSERT INTO download_status (paper_id, status, download_date,"
                    " source, notes, attempts, last_attempt) VALUES (?,?,?,?,?,?,?)",
                    (pid, "downloaded", datetime.now().isoformat(timespec="seconds"),
                     "repair_misfiled_pdfs",
                     "recovered from a misfiled PDF renamed onto this paper", 1,
                     datetime.now().isoformat(timespec="seconds")))
            marked += 1
        if apply:
            db.commit()
        return cleared, marked
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--manifest", type=Path)
    args = ap.parse_args()

    plan = read_plan(args.plan)
    print(f"{len(plan)} files in the plan")

    csv.field_size_limit(sys.maxsize)
    corpus_by_title = []
    with open(VIZ_DATA) as fh:
        for row in csv.DictReader(fh):
            lid = str(row.get("literature_id", "")).strip()
            try:
                lid = str(int(float(lid)))
            except (ValueError, TypeError):
                pass
            corpus_by_title.append((lid, row.get("title", "")))

    ids = {r["correct_literature_id"] for r in plan}
    actions = []
    for row in plan:
        src = Path(row["current_path"])
        was = row["claimed_literature_id"] or claimed_id(
            row["current_path"], corpus_by_title)
        entry = {"src": str(src), "action": row["action"],
                 "claimed_by_filename": was,
                 "correct_id": row["correct_literature_id"],
                 "status": "planned"}
        if was:
            ids.add(was)
        actions.append(entry)

    records = load_corpus(ids)

    lost, gained = set(), set()
    for a in actions:
        src = Path(a["src"])
        if not src.exists():
            a["status"] = "skipped: file missing"
            continue
        if a["claimed_by_filename"]:
            lost.add(a["claimed_by_filename"])
        if a["action"] == "delete":
            a["dest"] = None
            if args.apply:
                src.unlink()
                a["status"] = "deleted"
            else:
                a["status"] = "would delete"
            continue
        rec = records.get(a["correct_id"])
        if not rec:
            a["status"] = f"skipped: literature_id {a['correct_id']} not in corpus"
            continue
        dest = target_path(rec)
        a["dest"] = str(dest)
        if dest.exists() and dest.resolve() != src.resolve():
            a["status"] = "skipped: target already exists"
            continue
        gained.add(a["correct_id"])
        if args.apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dest)
            a["status"] = "renamed"
        else:
            a["status"] = "would rename"

    # A paper that gained a PDF is not lost, even if some other filename
    # claimed it a moment ago.
    lost -= gained

    print(f"\n{'Applying' if args.apply else 'Plan'}:")
    for a in actions:
        print(f"  [{a['status']}] {Path(a['src']).name[:66]}")
        if a.get("dest"):
            print(f"      -> {Path(a['dest']).parent.name}/{Path(a['dest']).name[:64]}")

    print(f"\nAcquisition state:")
    print(f"  papers that LOSE their PDF (back on the wanted list): "
          f"{sorted(lost) if lost else 'none'}")
    print(f"  papers that GAIN one (off the wanted list): "
          f"{sorted(gained) if gained else 'none'}")

    unknown = sorted(lid for lid in lost if lid not in records)
    if unknown:
        print(f"  WARNING: {unknown} not found in the corpus, so they cannot "
              f"be re-added to the wanted list. Fix before applying.")
    added, removed = update_papers_data(
        {lid: records[lid] for lid in lost if lid in records}, gained,
        args.apply)
    cleared, marked = update_tracker(lost, gained, args.apply)
    print(f"  papers_data.json: +{added} re-added, -{removed} removed")
    print(f"  download_tracker.db: {cleared} 'downloaded' rows cleared, "
          f"{marked} added")

    if args.apply:
        manifest = args.manifest or (
            PROJECT / "outputs" /
            f"misfile_repair_{datetime.now():%Y%m%d_%H%M%S}.json")
        manifest.write_text(json.dumps(
            {"generated": datetime.now().isoformat(timespec="seconds"),
             "actions": actions, "lost": sorted(lost),
             "gained": sorted(gained)}, indent=1))
        print(f"  manifest: {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
