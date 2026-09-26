#!/usr/bin/env python3
"""Decide which paper each shared library file actually is, and rename it so it says so.

A library filename truncates the title at 60 characters, which is exactly where a
series says which part it is. So "Preservative Experiment of the Smoked Shark-Fillet"
and its "Part II" generated one name, and 128 files ended up claimed by two or more
records (272 records in all, measured 2026-09-25). One file, two papers: one of them
is not actually held, and filing it would have overwritten the other.

For each shared file this opens the PDF, scores its first pages against every
claimant's title, and:

  * renames the file to the winner's name under the new scheme (the part designator
    is preserved, so the name is unique), and
  * reports every loser, with whether it is still on the download queue, so the
    papers we do NOT hold go back on the list instead of looking filed.

A file whose winner is not clear (no candidate reaches --min-lead over the next) is
left alone and written to the review workbook, because guessing here is how a paper
ends up extracted from another paper's text.

  python3 scripts/resolve_filename_collisions.py                 # dry run + workbook
  python3 scripts/resolve_filename_collisions.py --apply         # rename the clear ones
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import extract_schema_columns as X  # noqa: E402
from lib.library_naming import build_filename  # noqa: E402

CONFLICTS = ROOT / "outputs" / "pdf_id_map_conflicts.csv"
OUT_CSV = ROOT / "outputs" / "filename_collisions_resolved.csv"
QUEUE = ROOT / "docs" / "papers_data.json"
OUTSTANDING = {"needs_library", "needs_pdf", "sr_sync_new"}


def al(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def toks(t, n=5):
    return {w[:n] for w in re.findall(r"[a-z]{4,}", al(t))}


def page_text(pdf, first=1, last=3):
    try:
        return subprocess.run(["pdftotext", "-f", str(first), "-l", str(last), pdf, "-"],
                              capture_output=True, text=True, timeout=40).stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9,
         "x": 10, "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15, "xvi": 16, "xvii": 17,
         "xviii": 18, "xix": 19, "xx": 20}


def series_number(title):
    """The part number of a series paper, however it is written: 'Part II', 'No. 7',
    '-X.', or a bare roman numeral at the end ('...of a shark I.'). None if absent."""
    t = al(title).rstrip(". ")
    m = re.search(r"\b(?:part|pt|no|number|vol)\.?\s*([ivxlcdm]+|\d{1,3})\b", t)
    if not m:
        m = re.search(r"[-\u2013\u2014\s]([ivxlcdm]{1,6}|\d{1,3})$", t)
    if not m:
        return None
    v = m.group(1)
    return ROMAN.get(v, None) if not v.isdigit() else int(v)


def number_in_text(n, text):
    """Does the paper itself say it is number n? Looks for the forms a title page and a
    running head use, so 'VIII' does not match inside 'XVIII'."""
    if n is None:
        return False
    romans = [k for k, v in ROMAN.items() if v == n]
    alts = [str(n)] + romans
    t = al(text)
    for a in alts:
        if re.search(rf"\b(?:part|pt\.?|no\.?|number)\s*{a}\b", t):
            return True
        if re.search(rf"[-\u2013\u2014.,:;\s]{a}[.\s)\]]", t):
            return True
    return False


def score(title, text, rival_titles=()):
    """How much of what makes THIS title different from its rivals is on the page.

    Scoring on the whole title is useless here: papers in a series share almost every
    word, so both candidates score 1.0. What separates "Light microscopy of
    photoreceptors" from "General description" is the words only one of them has, so
    that is what gets counted, with the part number on top.
    """
    mine = toks(title)
    if not mine:
        return 0.0
    theirs = set().union(*[toks(t) for t in rival_titles]) if rival_titles else set()
    distinctive = mine - theirs
    page = toks(text)
    base = (len(distinctive & page) / len(distinctive)) if distinctive else (len(mine & page) / len(mine))
    n = series_number(title)
    if n is not None:
        rivals_n = [series_number(t) for t in rival_titles]
        if number_in_text(n, text) and not any(number_in_text(r, text) for r in rivals_n if r != n):
            base += 0.5
        elif any(number_in_text(r, text) for r in rivals_n if r != n) and not number_in_text(n, text):
            base -= 0.5
    return round(base, 3)


def same_paper(a, b):
    """Two records catalogued from the same paper: near-identical titles and the same
    part number. Shark-References transcribes older titles inconsistently, so an exact
    match misses them ('...Muscle of Shark-Fish. I.' vs '...muscle of a shark I.')."""
    ta, tb = toks(a.title), toks(b.title)
    if not ta or not tb:
        return False
    jac = len(ta & tb) / len(ta | tb)
    return jac >= 0.7 and series_number(a.title) == series_number(b.title)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-lead", type=float, default=0.15,
                    help="how far the winner must beat the runner-up before a rename happens")
    ap.add_argument("--min-score", type=float, default=0.45)
    args = ap.parse_args()

    df = pd.read_parquet(X.INPUT_PARQUET, columns=["literature_id", "title", "year", "authors"])
    meta = {str(r.literature_id).split(".")[0]: r for r in df.itertuples()}
    queue = {str(p.get("literature_id", "")).replace(".0", "").strip(): p for p in json.load(open(QUEUE))}

    rows, verdicts = list(csv.DictReader(open(CONFLICTS))), []
    for r in rows:
        pdf = r["pdf"]
        ids = [i for i in r["literature_ids"].split(";") if i in meta]
        if len(ids) < 2 or not Path(pdf).exists():
            continue
        text = page_text(pdf)
        scored = sorted(((score(meta[i].title, text,
                                [meta[j].title for j in ids if j != i]), i) for i in ids), reverse=True)
        # a pair that is really one paper catalogued twice is a merge, not a split
        if len(ids) == 2 and same_paper(meta[ids[0]], meta[ids[1]]):
            lo = min(ids, key=lambda i: (0, int(i)) if i.isdigit() else (1, i))
            for lid in ids:
                verdicts.append({"pdf": pdf, "literature_id": lid,
                                 "score": dict(zip([i for _, i in scored], [s for s, _ in scored]))[lid],
                                 "verdict": "same paper, keep " + lo, "new_name": "",
                                 "on_queue": "yes" if queue.get(lid, {}).get("last_status") in OUTSTANDING else "no",
                                 "year": meta[lid].year, "title": (meta[lid].title or "")[:150]})
            continue
        (s1, win), rest = scored[0], scored[1:]
        s2 = rest[0][0] if rest else 0.0
        clear = bool(text.strip()) and s1 >= args.min_score and (s1 - s2) >= args.min_lead
        for sc, lid in scored:
            q = queue.get(lid)
            verdicts.append({
                "pdf": pdf, "literature_id": lid, "score": sc,
                "verdict": ("winner" if lid == win else "loser") if clear else "unclear",
                "new_name": build_filename({**meta[lid]._asdict(), "literature_id": lid}) if lid == win and clear else "",
                "on_queue": "yes" if q and q.get("last_status") in OUTSTANDING else "no",
                "year": meta[lid].year, "title": (meta[lid].title or "")[:150],
            })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["pdf", "literature_id", "score", "verdict",
                                           "new_name", "on_queue", "year", "title"])
        w.writeheader()
        w.writerows(verdicts)

    files = {v["pdf"] for v in verdicts}
    clear_files = {v["pdf"] for v in verdicts if v["verdict"] == "winner"}
    losers = [v for v in verdicts if v["verdict"] == "loser"]
    print(f"shared files examined: {len(files):,} covering {len(verdicts):,} records")
    print(f"  winner identified by opening the PDF: {len(clear_files):,} files")
    print(f"  too close to call, left alone:        {len(files) - len(clear_files):,} files")
    print(f"  papers we therefore do NOT hold:      {len(losers):,}"
          f"  (on the download queue already: {sum(1 for v in losers if v['on_queue'] == 'yes'):,})")
    print(f"wrote {OUT_CSV}")

    if not args.apply:
        print("dry run: nothing renamed (use --apply)")
        return

    renamed = collide = 0
    for v in verdicts:
        if v["verdict"] != "winner" or not v["new_name"]:
            continue
        src = Path(v["pdf"])
        dst = src.parent / v["new_name"]
        if dst == src:
            continue
        if dst.exists():
            collide += 1
            continue
        src.rename(dst)
        renamed += 1
    print(f"renamed {renamed:,} files ({collide:,} skipped: the new name was already taken)")
    print("Next: rebuild the id map, then re-extract what moved "
          "(sh scripts/refresh_pdf_map_and_extract.sh).")


if __name__ == "__main__":
    main()
