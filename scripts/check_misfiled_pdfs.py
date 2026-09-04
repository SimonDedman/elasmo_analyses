#!/usr/bin/env python3
"""Find corpus records whose PDF is not the paper they name.

Several papers can legitimately share one PDF: a scanned journal volume backs
every article in it.  But a shared PDF can also mean the ingest matcher filed
one paper's file under another paper's name, and the two look identical from
the outside.  Nineteen 2021 shark records were found pointing at a 2005
Portuguese literature-journal article this way.

The test that separates them: extract the PDF's full text and ask, of every
record naming it, whether that paper's title appears anywhere inside.  A real
volume contains all its articles.  A misfile contains no trace of the paper
it is filed as, and anything schema extraction produced for that record
describes a different paper.

Three results, deliberately kept apart, because collapsing them turns a
limitation of the tool into a false finding:

    present      the title is in the document
    absent       the document has good text and the title is not in it
    untestable   too little text to judge, or a title too short to match

Two known ways to be wrong, both handled:

*   **Abbreviated filenames.**  A title fragment on disk may abbreviate its
    words ("Bioturb stingray Ningaloo", "Biologging horiz vert mov"), so
    literal matching calls a paper absent from a PDF that plainly contains
    it.  Words are matched by prefix.  Adding this removed 44 of 139 flags.
*   **Non-Latin scans.**  A Japanese society bulletin is a genuine container
    whose Latin titles OCR cannot recover.  Text that is mostly non-Latin is
    flagged ``check_ocr`` so it is reviewed rather than trusted.

Usage
-----
    python3 scripts/check_misfiled_pdfs.py --csv outputs/misfiled_records.csv

Text is cached by content hash, so re-running after changing the matching
rule costs seconds instead of ten minutes.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dedupe_hardlink import DEFAULT_ROOT, scan  # noqa: E402

CACHE_DIR = Path("outputs/.pdf_text_cache")
# Words too common in titles to carry evidence either way.
STOP = {"the", "of", "and", "a", "an", "in", "on", "for", "from", "with",
        "to", "its", "new", "at", "by", "two", "one", "note", "notes"}
MIN_TITLE_WORDS = 3
MIN_TEXT_WORDS = 100
MATCH_THRESHOLD = 0.7
LATIN_THRESHOLD = 0.5


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def parse_filename(path: str) -> tuple[set[str], int, str]:
    """Split ``Surname[.etal].Year.Title fragment.pdf`` into its parts."""
    stem = os.path.basename(path)
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4]
    parts = stem.split(".")
    for i, part in enumerate(parts):
        if re.fullmatch(r"(1[6-9]|20)\d\d", part):
            return set(parts[:i]) - {"etal"}, int(part), ".".join(parts[i + 1:])
    return set(), 0, stem


def extract_text(path: str, digest: str, cache_dir: Path) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{digest}.txt"
    if cached.exists():
        return cached.read_text(errors="replace")
    try:
        text = subprocess.run(["pdftotext", path, "-"], capture_output=True,
                              text=True, timeout=240).stdout
    except (subprocess.TimeoutExpired, OSError):
        text = ""
    cached.write_text(text, errors="replace")
    return text


def latin_fraction(text: str) -> float:
    """Share of letters that are ASCII.

    A Japanese bulletin scan scores low, which is the signal that its Latin
    titles are unrecoverable rather than absent.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(c.isascii() for c in letters) / len(letters)


def title_present(title: str, sorted_tokens: list[str]) -> bool | None:
    """Is this title in the document?  ``None`` when it cannot be judged.

    Matches by prefix so an abbreviated filename word finds its full form.
    """
    words = [w for w in norm(title).split()
             if len(w) > 3 and w not in STOP]
    if len(words) < MIN_TITLE_WORDS:
        return None
    hits = 0
    for word in words:
        i = bisect.bisect_left(sorted_tokens, word)
        if i < len(sorted_tokens) and sorted_tokens[i].startswith(word):
            hits += 1
    return hits / len(words) >= MATCH_THRESHOLD


def distinct_records(group: dict) -> list[dict]:
    """One entry per paper naming this PDF, collapsing name variants."""
    seen, records = set(), []
    for f in group["files"]:
        authors, year, title = parse_filename(f["path"])
        key = norm(title)[:45]
        if key in seen:
            continue
        seen.add(key)
        # sorted list, not the parsed set: this dict is serialised to JSON
        records.append({"authors": sorted(authors), "year": year,
                        "title": title, "path": f["path"]})
    return records


def judge_group(group: dict, cache_dir: Path) -> dict | None:
    records = distinct_records(group)
    if len(records) < 2:
        return None

    text = extract_text(records[0]["path"], group["sha256"], cache_dir)
    words = norm(text).split()
    tokens = sorted(set(words))
    latin = latin_fraction(text)
    first_line = " ".join(text.split())[:160]

    entry = {
        "sha256": group["sha256"],
        "size_mb": round(group["size"] / 2 ** 20, 1),
        "year": records[0]["year"],
        "n_records": len(records),
        "n_words": len(words),
        "latin_fraction": round(latin, 2),
        "pdf_starts": first_line,
    }

    if len(words) < MIN_TEXT_WORDS:
        entry["verdict"] = "untestable_no_text"
        entry["records"] = [dict(r, present=None) for r in records]
        return entry

    judged = [dict(r, present=title_present(r["title"], tokens))
              for r in records]
    testable = [r for r in judged if r["present"] is not None]
    if not testable:
        entry["verdict"] = "untestable_short_titles"
    elif all(r["present"] for r in testable):
        entry["verdict"] = "container"
    elif any(r["present"] for r in testable):
        entry["verdict"] = "misfiled_some_absent"
    else:
        entry["verdict"] = "misfiled_none_found"
    entry["records"] = judged
    return entry


def confidence(entry: dict) -> str:
    """Whether the flag can be trusted, or needs a human because the tool has
    a known blind spot here."""
    if entry["latin_fraction"] < LATIN_THRESHOLD:
        return "check_ocr"
    if entry["n_words"] < 400:
        return "check_thin_text"
    if entry["verdict"] == "misfiled_none_found":
        return "check_none_matched"
    return "auto"


def write_csv(entries: list[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group_id", "year", "size_mb", "n_records", "confidence",
                    "absent_title", "pdf_holds_instead", "pdf_starts",
                    "latin_fraction", "n_words", "absent_path", "sha256",
                    "decision", "notes"])
        for gid, e in enumerate(entries, 1):
            if not e["verdict"].startswith("misfiled"):
                continue
            present = [r["title"] for r in e["records"] if r["present"]]
            for r in e["records"]:
                if r["present"] is not False:
                    continue
                w.writerow([
                    gid, e["year"], e["size_mb"], e["n_records"],
                    confidence(e), r["title"],
                    present[0] if present else "(no naming paper found in it)",
                    e["pdf_starts"], e["latin_fraction"], e["n_words"],
                    r["path"], e["sha256"][:12], "", "",
                ])
                rows += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--cache", type=Path, default=CACHE_DIR)
    ap.add_argument("--csv", type=Path, default=Path("outputs/misfiled_records.csv"))
    ap.add_argument("--json", type=Path, help="also write full per-group verdicts")
    args = ap.parse_args()

    print(f"Scanning {args.root} for shared PDFs...")
    groups = scan(args.root)
    shared = [g for g in groups if len(distinct_records(g)) > 1]
    print(f"  {len(shared)} PDFs named by more than one paper")

    print("Extracting text and testing each naming paper...")
    entries = []
    for i, g in enumerate(shared, 1):
        entry = judge_group(g, args.cache)
        if entry:
            entries.append(entry)
        if i % 100 == 0:
            print(f"  {i}/{len(shared)}", flush=True)

    counts = Counter(e["verdict"] for e in entries)
    for k, v in counts.most_common():
        print(f"  {v:4d}  {k}")

    absent = sum(1 for e in entries for r in e["records"]
                 if r["present"] is False)
    untested = sum(1 for e in entries for r in e["records"]
                   if r["present"] is None)
    print(f"\n  {absent} records absent from the PDF they name")
    print(f"  {untested} records could not be tested (not the same thing)")

    rows = write_csv(entries, args.csv)
    print(f"  wrote {args.csv} ({rows} rows for review)")
    by_conf = Counter(confidence(e) for e in entries
                      if e["verdict"].startswith("misfiled"))
    for k, v in by_conf.most_common():
        print(f"    {v:4d} groups: {k}")

    if args.json:
        args.json.write_text(json.dumps(entries, indent=1))
        print(f"  wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
