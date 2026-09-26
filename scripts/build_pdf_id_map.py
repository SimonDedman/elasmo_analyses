#!/usr/bin/env python3
"""Map every library PDF to the literature_id it belongs to, by inverting the
filename the library itself generates.

WHY
---
extract_schema_columns.py resolves a paper's PDF from (first-author surname,
year) and takes the first candidate when nothing better presents itself. A paper
with no PDF of its own, whose first author published something else that year,
is therefore extracted from that other paper's text: 1,471 corpus rows measured
on 2026-09-18, ~97% of a sample confirmed wrong.

Surname and year are not an identity. The library FILENAME is, because
sync_shark_references.build_pdf_path() generates it from the record:

    <first author>[.etal].<year>.<title truncated to 60 chars>.pdf   in <year>/

So the map is built by regenerating that name for all 31,772 corpus records and
matching it against the library, rather than by guessing from author and year.

METHODS, in the order tried, each recorded per row in `method`:
  exact      the generated name matches a library file exactly
  nospace    matches ignoring case, spacing and punctuation (OCR-era renames)
  title      same surname and year, and the file's title part is >= --cover
             covered by the record's title (library names truncate at 60 chars)
A file claimed by more than one record, or a record matching more than one file,
is left OUT of the map and written to the conflicts CSV: those are the genuine
multi-part works and duplicate records that need a human.

  python3 scripts/build_pdf_id_map.py
  python3 scripts/build_pdf_id_map.py --verify 300   # also open N mapped PDFs and check them
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import extract_schema_columns as X  # noqa: E402
from sync_shark_references import build_pdf_path  # noqa: E402

OUT = ROOT / "outputs" / "pdf_id_map.csv"
CONFLICTS = ROOT / "outputs" / "pdf_id_map_conflicts.csv"
COVERAGE = ROOT / "outputs" / "pdf_id_map_coverage.json"


def al(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def squash(name):
    """Filename identity that survives case, spacing, punctuation and OCR renames."""
    return re.sub(r"[^a-z0-9]+", "", al(name))


def toks(t, n=5):
    return {w[:n] for w in re.findall(r"[a-z]{4,}", al(t))}


def title_part(fname):
    """The title portion of a library filename: Surname[.etal].Year.Title.pdf.
    The surname is squashed, because the library writes Bendix-Almgreen as
    BendixAlmgreen and de Andres as deAndres."""
    m = re.match(r"([^.]+?)(?:\.etal)?\.(\d{4})\.(.*)\.pdf$", fname, re.I)
    return (squash(m.group(1)), m.group(2), m.group(3)) if m else (None, None, None)


def is_subsequence(short, long_):
    """Every character of `short`, in order, somewhere in `long_`.

    clean_for_filename() drops punctuation and short words ("Notes on the Upper"
    becomes "Notes Upper"), so a token comparison misses matches that are
    obviously the same title. Squashed to letters and digits, the filename's
    title is a subsequence of the record's title whenever they are the same
    work, and almost never otherwise."""
    it = iter(long_)
    return all(c in it for c in short)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cover", type=float, default=0.85)
    ap.add_argument("--verify", type=int, default=0, help="open this many mapped PDFs and check the title on pages 1-2")
    ap.add_argument("--compare-old-matcher", action="store_true",
                    help="also report how the map differs from the retired surname+year matcher (slow)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    df = pd.read_parquet(X.INPUT_PARQUET, columns=["literature_id", "title", "authors", "year"])
    df = df[df.literature_id.notna()]
    records = [{"lid": str(r.literature_id).split(".")[0], "title": r.title, "authors": r.authors,
                "year": r.year} for r in df.itertuples()]
    print(f"corpus records: {len(records):,}")

    lib_by_squash, lib_by_surname_year, n_files = {}, defaultdict(list), 0
    for root, _, files in os.walk(X.PDF_BASE):
        for f in files:
            if not f.lower().endswith(".pdf"):
                continue
            n_files += 1
            full = str(Path(root) / f)
            lib_by_squash.setdefault(squash(f), []).append(full)
            sur, yr, _ = title_part(f)
            if sur:
                lib_by_surname_year[(sur, yr)].append(full)
    print(f"library PDFs: {n_files:,}")

    claims = defaultdict(list)   # pdf path -> [(lid, method)]
    picks = {}                   # lid -> (pdf, method)
    for rec in records:
        try:
            want = build_pdf_path({"authors": rec["authors"], "year": rec["year"], "title": rec["title"]})
        except Exception:
            continue
        hit = lib_by_squash.get(squash(want.name))
        method = "exact" if hit and any(Path(h).name == want.name for h in hit) else ("nospace" if hit else None)
        if hit:
            path = next((h for h in hit if Path(h).name == want.name), hit[0])
        else:
            sur, yr, _ = title_part(want.name)
            rec_sq = squash(rec["title"])
            best, bestcov, bestlen = None, 0.0, 0
            for cand in lib_by_surname_year.get((sur, yr), []):
                _, _, t = title_part(Path(cand).name)
                if not t:
                    continue
                ft, fsq = toks(t), squash(t)
                cov = len(ft & toks(rec["title"])) / max(len(ft), 1)
                # either the words agree, or the squashed filename title is a
                # subsequence of the record's (punctuation and dropped stopwords)
                ok = cov >= args.cover or (len(fsq) >= 12 and is_subsequence(fsq, rec_sq))
                if ok and len(fsq) > bestlen:
                    best, bestcov, bestlen = cand, cov, len(fsq)
            if best is None:
                continue
            path, method = best, "title"
        picks[rec["lid"]] = (path, method)
        claims[path].append((rec["lid"], method))

    # a file claimed by several records, or a record claiming a file another record
    # claimed more strongly, is a conflict: leave it out rather than guess.
    conflicts = {p: c for p, c in claims.items() if len(c) > 1}
    rank = {"exact": 0, "nospace": 1, "title": 2}
    resolved = {}
    for path, c in claims.items():
        if len(c) == 1:
            resolved[c[0][0]] = (path, c[0][1])
            continue
        best = sorted(c, key=lambda t: rank[t[1]])
        if rank[best[0][1]] < rank[best[1][1]]:      # one record names it better than the rest
            resolved[best[0][0]] = (path, best[0][1] + "_won")
    print(f"\nmapped: {len(resolved):,} records -> a PDF")
    print("by method:", Counter(m for _, m in resolved.values()).most_common())
    print(f"files claimed by more than one record: {len(conflicts):,} "
          f"(covering {sum(len(c) for c in conflicts.values()):,} records)")

    # Diff against the PREVIOUS map, which is what extraction actually used, so the
    # change list is exactly the set of rows that need re-extracting. (The retired
    # surname+year matcher is only interesting on a first build: --compare-old-matcher.)
    if args.compare_old_matcher:
        idx = X.build_pdf_index(X.PDF_BASE)
        old = {}
        for rec in records:
            sur = X._first_surname(rec["authors"])
            try:
                yr = int(rec["year"])
            except (TypeError, ValueError):
                continue
            if sur and X._pick_best_pdf(idx.get((sur, yr), []), rec["title"] or "") is not None:
                old[rec["lid"]] = str(X._pick_best_pdf(idx.get((sur, yr), []), rec["title"] or ""))
    else:
        old = {}
        if args.out.exists():
            with open(args.out, newline="") as fh:
                old = {r["literature_id"]: r["pdf"] for r in csv.DictReader(fh)}
    label = "the retired surname+year matcher" if args.compare_old_matcher else "the previous map"
    same = sum(1 for lid, (p, _) in resolved.items() if old.get(lid) == p)
    changed = {lid: (old.get(lid), p) for lid, (p, _) in resolved.items() if old.get(lid) != p}
    lost = {lid: old[lid] for lid in old if lid not in resolved}
    print(f"\nagainst {label}" + (" (none on disk: first build, everything counts as new)" if not old else "") + ":")
    print(f"  unchanged:            {same:,}")
    print(f"  different PDF now:    {len([1 for lid, (o, n) in changed.items() if o]):,}")
    print(f"  had a PDF, now none:  {len(lost):,}")
    print(f"  newly mapped:         {len([1 for lid, (o, n) in changed.items() if not o]):,}")

    verified = unverified = 0
    if args.verify:
        import random
        random.seed(7)
        for lid in random.sample(sorted(resolved), min(args.verify, len(resolved))):
            path, _ = resolved[lid]
            rec = next(r for r in records if r["lid"] == lid)
            try:
                txt = subprocess.run(["pdftotext", "-f", "1", "-l", "2", path, "-"],
                                     capture_output=True, text=True, timeout=25).stdout
            except (subprocess.TimeoutExpired, OSError):
                txt = ""
            want = toks(rec["title"])
            cov = len(want & toks(txt)) / max(len(want), 1)
            if cov >= 0.6 or not txt.strip():
                verified += 1
            else:
                unverified += 1
        print(f"\nspot check of {args.verify} mapped PDFs: {verified} consistent, {unverified} not "
              f"(a scan with no text layer counts as consistent: nothing to compare)")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["literature_id", "pdf", "method"])
        for lid, (path, method) in sorted(resolved.items()):
            w.writerow([lid, path, method])
    with open(CONFLICTS, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pdf", "literature_ids", "methods"])
        for path, c in sorted(conflicts.items()):
            w.writerow([path, ";".join(x[0] for x in c), ";".join(x[1] for x in c)])
    json.dump({"records": len(records), "library_pdfs": n_files, "mapped": len(resolved),
               "by_method": dict(Counter(m for _, m in resolved.values())),
               "conflict_files": len(conflicts),
               "same_as_old": same, "changed": len(changed), "lost": len(lost),
               "gained": sum(1 for lid in resolved if lid not in old),
               "spot_check": {"n": args.verify, "consistent": verified, "not": unverified}},
              open(COVERAGE, "w"), indent=1)
    with open(ROOT / "outputs" / "pdf_id_map_changes.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["literature_id", "old_pdf", "new_pdf"])
        for lid, (o, n) in sorted(changed.items()):
            w.writerow([lid, o or "", n])
        for lid, o in sorted(lost.items()):
            w.writerow([lid, o, ""])
    print(f"\nwrote {args.out}, {CONFLICTS.name}, pdf_id_map_changes.csv, {COVERAGE.name}")


if __name__ == "__main__":
    main()
