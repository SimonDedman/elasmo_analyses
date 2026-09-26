#!/usr/bin/env python3
"""Mark duplicate Shark-References records that claim the same library PDF.

Building the literature_id -> PDF map (scripts/build_pdf_id_map.py) leaves a file
unassigned when two records generate the same library filename, because guessing
which record owns it is how papers end up extracted from another paper's text.
Most of those pairs are not a filing problem at all: they are the SAME paper
catalogued twice by Shark-References.

This marks the extras rather than deleting them (Simon, 2026-09-25): the lowest
literature_id stays canonical and every other record in the group gets
`merged_into = <canonical>`. Nothing is removed, so a Shark-References id a
collaborator quotes still resolves, and the decision can be undone by deleting a
column.

Only records whose titles agree are merged. A file claimed by records with
DIFFERENT titles is a multi-part work or a genuine mis-claim; those are listed
and left alone.

Writes  outputs/merged_records.csv          lid, merged_into, title, why
        (with --apply) a `merged_into` column in the enriched parquet, and a
        note on the matching queue rows in docs/papers_data.json.

  python3 scripts/merge_duplicate_records.py            # dry run
  python3 scripts/merge_duplicate_records.py --apply
"""
import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import extract_schema_columns as X  # noqa: E402
from lib.papers_data_io import mutate  # noqa: E402

CONFLICTS = ROOT / "outputs" / "pdf_id_map_conflicts.csv"
OUT = ROOT / "outputs" / "merged_records.csv"


def squash(s):
    return re.sub(r"[^a-z0-9]+", "",
                  unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower())


def lid_key(lid):
    """Numeric where possible, so 'lowest id' means lowest number, not lowest string."""
    try:
        return (0, int(lid))
    except ValueError:
        return (1, lid)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--title-chars", type=int, default=60,
                    help="compare this many squashed title characters (library filenames truncate at 60)")
    args = ap.parse_args()

    df = pd.read_parquet(X.INPUT_PARQUET, columns=["literature_id", "title", "year", "authors", "doi"])
    meta = {str(r.literature_id).split(".")[0]: r for r in df.itertuples()}

    merges, mixed = [], []
    for row in csv.DictReader(open(CONFLICTS)):
        ids = [i for i in row["literature_ids"].split(";") if i]
        known = [i for i in ids if i in meta]
        if len(known) < 2:
            continue
        titles = {squash(meta[i].title)[:args.title_chars] for i in known}
        dois = {str(meta[i].doi or "").strip().lower() for i in known if str(meta[i].doi or "").strip()}
        if len(titles) == 1:
            canon = sorted(known, key=lid_key)[0]
            why = "same title" + (", same DOI" if len(dois) == 1 and dois else "")
            for i in known:
                if i != canon:
                    merges.append({"literature_id": i, "merged_into": canon,
                                   "title": (meta[i].title or "")[:120], "why": why,
                                   "pdf": row["pdf"]})
        else:
            mixed.append((row["pdf"], known, [(i, (meta[i].title or "")[:70]) for i in known]))

    print(f"conflict files: {sum(1 for _ in csv.DictReader(open(CONFLICTS))):,}")
    print(f"  duplicate records to mark: {len(merges):,} (keeping {len({m['merged_into'] for m in merges}):,} canonical records)")
    print(f"  files whose claimants have DIFFERENT titles, left alone: {len(mixed):,}")
    print("  reasons:", dict(Counter(m["why"] for m in merges)))
    for pdf, ids, ts in mixed[:5]:
        print(f"    LEFT: {Path(pdf).name[:64]}")
        for i, t in ts:
            print(f"        {i}  {t}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["literature_id", "merged_into", "title", "why", "pdf"])
        w.writeheader()
        w.writerows(sorted(merges, key=lambda m: lid_key(m["merged_into"])))
    print(f"wrote {OUT}")
    if not args.apply:
        print("dry run: parquet and queue untouched (use --apply)")
        return

    # 1. the enriched parquet carries the mark, beside the other provenance columns
    enr = pd.read_parquet(X.OUTPUT_PARQUET)
    by_lid = {m["literature_id"]: m["merged_into"] for m in merges}
    key = enr.literature_id.astype(str).str.split(".").str[0]
    if "merged_into" not in enr.columns:
        enr["merged_into"] = pd.NA
    enr["merged_into"] = key.map(by_lid).fillna(enr["merged_into"])
    enr.to_parquet(X.OUTPUT_PARQUET, index=False)
    print(f"enriched parquet: {int(enr.merged_into.notna().sum()):,} rows carry merged_into")

    # 2. a queue row for a duplicate is work nobody needs to do twice
    with mutate() as papers:
        n = 0
        for p in papers:
            lid = str(p.get("literature_id", "")).replace(".0", "").strip()
            if lid in by_lid:
                p["merged_into"] = by_lid[lid]
                note = f"Duplicate of literature_id {by_lid[lid]} (same title, same PDF)."
                if note not in (p.get("notes") or ""):
                    p["notes"] = ((p.get("notes") or "") + " " + note).strip()
                n += 1
    print(f"queue rows marked: {n:,}")
    print("Next: rebuild the id map so the canonical record claims the file, then re-extract it.")


if __name__ == "__main__":
    main()
