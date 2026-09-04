#!/usr/bin/env python3
"""Apply the reviewed decisions from the misfiled-PDF workbook.

Reads the ``misfiled`` tab of ``outputs/misfiled_pdf_review_*.xlsx`` and
removes each filename confirmed to hold a different paper:

    MISFILED   delete the file: this name claims a paper the file does not hold
    CONTAINER  the checker was wrong, leave it
    UNSURE     leave it
    (blank)    not reviewed, leave it

Deleting a misfiled NAME is not the same as deleting CONTENT.  These files are
hardlinked, so removing a wrong name normally just drops one link and the
document stays reachable under its correct name.  Where a name is the last one
pointing at its content, deleting it destroys the document, which is a
different act and needs a different decision, so ``--allow-content-loss``
gates it and the report says exactly what would be lost.

Nothing is judged here.  Every verdict came from the workbook; this only
checks that the world still looks the way it did when the sheet was made.

Usage
-----
    python3 scripts/apply_misfile_review.py --workbook outputs/x.xlsx
    python3 scripts/apply_misfile_review.py --workbook outputs/x.xlsx --apply
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import warnings
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore", message=".*Data Validation.*")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe_hardlink import sha256  # noqa: E402

DELETE = "MISFILED"
LEAVE = {"CONTAINER", "UNSURE", ""}


def read_rows(workbook: Path) -> list[dict]:
    import openpyxl
    ws = openpyxl.load_workbook(workbook, data_only=True)["misfiled"]
    header = [c.value for c in ws[1]]
    rows = []
    for values in ws.iter_rows(min_row=2, values_only=True):
        row = dict(zip(header, values))
        row["decision"] = (row.get("decision") or "").strip().upper()
        rows.append(row)
    return rows


def plan(rows: list[dict], log=print) -> tuple[list[dict], Counter]:
    counts = Counter()
    actions = []
    for row in rows:
        decision = row["decision"]
        counts[decision or "(blank)"] += 1
        if decision in LEAVE:
            continue
        if decision != DELETE:
            log(f"  unrecognised decision {decision!r}, skipping")
            counts["invalid"] += 1
            continue
        actions.append({
            "path": row["absent_path"],
            "claims": row["absent_title"],
            "actually_holds": row["pdf_holds_instead"],
            "correct_copy": row.get("correct_copy_path") or "",
            "sha256_prefix": row["sha256"],
            "record_year": row["record_year"],
            "status": "planned",
        })
    return actions, counts


def survivors(actions: list[dict]) -> dict[int, dict]:
    """Per inode: how many names it has, and how many we are about to remove.

    Counting by inode rather than by path is the whole point: five different
    filenames can be five links to one document, and deleting all five is
    deleting the document.
    """
    doomed = defaultdict(list)
    for a in actions:
        try:
            doomed[os.stat(a["path"]).st_ino].append(a)
        except OSError:
            continue
    out = {}
    for ino, group in doomed.items():
        nlink = os.stat(group[0]["path"]).st_nlink
        out[ino] = {"nlink": nlink, "deleting": len(group),
                    "remaining": nlink - len(group), "actions": group}
    return out


def execute(actions: list[dict], apply: bool, allow_loss: bool,
            log=print) -> tuple[int, list[dict]]:
    freed = 0
    emptied = []
    by_inode = survivors(actions)

    for ino, info in by_inode.items():
        if info["remaining"] > 0:
            continue
        emptied.append(info)
        if allow_loss:
            continue
        for a in info["actions"]:
            a["status"] = ("refused: would delete the last copy of this "
                           "content, not just a wrong name")

    for a in actions:
        if a["status"].startswith("refused"):
            continue
        path = Path(a["path"])
        if not path.exists():
            a["status"] = "skipped: already gone"
            continue
        try:
            size = path.stat().st_size
            # The sheet may be days old.  A file re-OCRed or replaced since
            # then is no longer the file that was judged.
            if not sha256(path).startswith(a["sha256_prefix"]):
                a["status"] = "skipped: content changed since review"
                log(f"  SKIP {path.name}: no longer the file that was reviewed")
                continue
        except OSError as exc:
            a["status"] = f"skipped: {exc}"
            continue

        if not apply:
            a["status"] = "would delete"
            freed += size
            continue
        try:
            path.unlink()
            a["status"] = "deleted"
            freed += size
        except OSError as exc:
            a["status"] = f"failed: {exc}"
            log(f"  FAILED {path}: {exc}")
    return freed, emptied


def write_orphaned_records(actions: list[dict], path: Path) -> int:
    """The records left with no PDF, for the extraction cleanup that follows.

    Deleting the file is only half the repair.  Each of these records still
    carries schema columns in the enriched parquet that were extracted from
    the wrong paper, and those are worse than absent columns because they
    look like data.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "claimed_title", "deleted_path",
                    "correct_copy_path", "still_has_a_pdf",
                    "extraction_needs_invalidating"])
        for a in actions:
            if a["status"] not in ("deleted", "would delete"):
                continue
            has_copy = bool(a["correct_copy"])
            w.writerow([a["record_year"], a["claims"], a["path"],
                        a["correct_copy"], "yes" if has_copy else "no", "yes"])
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workbook", type=Path, required=True)
    ap.add_argument("--apply", action="store_true",
                    help="actually delete; without this it is a dry run")
    ap.add_argument("--allow-content-loss", action="store_true",
                    help="permit deleting the last name pointing at a "
                         "document, destroying it")
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--orphans", type=Path,
                    default=Path("outputs/misfile_orphaned_records.csv"))
    args = ap.parse_args()

    rows = read_rows(args.workbook)
    print(f"Read {len(rows)} reviewed rows from {args.workbook}")
    actions, counts = plan(rows)
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    if not actions:
        print("\nNothing confirmed for deletion.")
        return 0

    print(f"\n{'Deleting' if args.apply else 'Dry run over'} {len(actions)} files...")
    freed, emptied = execute(actions, args.apply, args.allow_content_loss)

    done = [a for a in actions if a["status"] in ("deleted", "would delete")]
    refused = [a for a in actions if a["status"].startswith("refused")]
    skipped = [a for a in actions if a["status"].startswith("skipped")]
    failed = [a for a in actions if a["status"].startswith("failed")]

    verb = "deleted" if args.apply else "would delete"
    print(f"  {verb} {len(done)} names, {freed / 2 ** 20:.1f} MB")
    print(f"  {len(skipped)} skipped, {len(failed)} failed, {len(refused)} refused")

    if emptied:
        print(f"\n  {len(emptied)} document(s) would lose EVERY name "
              f"({'permitted' if args.allow_content_loss else 'REFUSED'}):")
        for info in emptied:
            print(f"    {info['nlink']} names, all confirmed misfiled:")
            for a in info["actions"]:
                print(f"      {Path(a['path']).name[:74]}")
        if not args.allow_content_loss:
            print("    Re-run with --allow-content-loss only if that content "
                  "should not exist.")

    n = write_orphaned_records(actions, args.orphans)
    print(f"\n  {n} records left needing their extraction invalidated: {args.orphans}")

    if args.apply:
        manifest = args.manifest or (
            Path("outputs") / f"misfile_applied_{datetime.now():%Y%m%d_%H%M%S}.json")
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(
            {"workbook": str(args.workbook),
             "generated": datetime.now().isoformat(timespec="seconds"),
             "freed_bytes": freed, "actions": actions}, indent=1))
        print(f"  manifest: {manifest}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
