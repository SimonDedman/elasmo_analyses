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
MIN_CONFIDENT_WORDS = 400
# Below this many testable title words, a miss proves little either way.
MIN_SOLID_WORDS = 4


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


def _in_text(word: str, sorted_tokens: list[str]) -> bool:
    i = bisect.bisect_left(sorted_tokens, word)
    return i < len(sorted_tokens) and sorted_tokens[i].startswith(word)


def title_words(title: str) -> list[str]:
    return [w for w in norm(title).split() if len(w) > 3 and w not in STOP]


def title_present(title: str, sorted_tokens: list[str]
                  ) -> tuple[bool | None, int, int]:
    """Is this title in the document?

    Returns (verdict, words found, words looked for), so the review sheet can
    show the evidence rather than an unexplained flag.  ``None`` means the
    title is too short to judge, which is not the same as absent.

    Words match by prefix, because filenames abbreviate them
    ("Bioturb" for "Bioturbation").  A word is also retried without a leading
    or trailing "i": titles carrying BibTeX italic markup lose their angle
    brackets somewhere upstream, leaving the tag glued to the species name
    ("<i>Tursiops aduncus</i>" becomes "iTursiops aduncusi").
    """
    words = title_words(title)
    if len(words) < MIN_TITLE_WORDS:
        return None, 0, len(words)
    hits = 0
    for word in words:
        if _in_text(word, sorted_tokens):
            hits += 1
        elif word.startswith("i") and len(word) > 4 \
                and _in_text(word[1:], sorted_tokens):
            hits += 1
        elif word.endswith("i") and len(word) > 4 \
                and _in_text(word[:-1], sorted_tokens):
            hits += 1
    return hits / len(words) >= MATCH_THRESHOLD, hits, len(words)


def same_paper(a: str, b: str) -> bool:
    """Are these two filenames naming the same paper?

    A record whose title nearly matches one that IS in the document is a
    duplicate filename, not a misfile, and belongs in the twins workflow.
    """
    wa, wb = set(title_words(a)), set(title_words(b))
    if len(wa) < 3 or len(wb) < 3:
        return False
    return len(wa & wb) / min(len(wa), len(wb)) >= 0.6


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

    judged = []
    for r in records:
        verdict, hits, total = title_present(r["title"], tokens)
        judged.append(dict(r, present=verdict, words_found=hits,
                           words_sought=total))

    # A record whose title nearly matches one that IS in the document is a
    # duplicate filename, not a misfile.  BibTeX italic markup loses its
    # angle brackets upstream and mangles a title enough to look absent.
    here = [r for r in judged if r["present"]]
    for r in judged:
        if r["present"] is False and any(same_paper(r["title"], h["title"])
                                         for h in here):
            r["present"] = "name_variant"

    testable = [r for r in judged if r["present"] not in (None, "name_variant")]
    if not testable:
        entry["verdict"] = "untestable_short_titles"
    elif all(r["present"] for r in testable):
        entry["verdict"] = "container"
    elif any(r["present"] for r in testable):
        entry["verdict"] = "misfiled_some_absent"
    else:
        entry["verdict"] = "misfiled_none_found"
    entry["records"] = judged
    # The year of the paper the document actually holds, which is often not
    # the year of the record being questioned.
    entry["pdf_year"] = next((r["year"] for r in judged if r["present"] is True),
                             None)
    return entry


def confidence(entry: dict, record: dict | None = None) -> tuple[str, str]:
    """How far this row can be trusted, and why, in words for the sheet.

    Confidence turns on the quality of the EVIDENCE, never on how alarming
    the verdict is.  An earlier version doubted every "none of the papers
    matched" group, which demoted the clearest finding in the whole set:
    nineteen records on one PDF, judged from 4,000 words of clean text that
    is plainly a different article.

    Three things genuinely weaken a row: a scan whose script the OCR cannot
    read, too little text to search, and a filename abbreviated so hard that
    only two or three words remain to test ("3D mov hab select jGWS NY
    Bight", which is the same paper as "Three-Dimensional Movements and
    Habitat Selection of Young White Sharks").
    """
    if entry["latin_fraction"] < LATIN_THRESHOLD:
        return ("check the scan", "PDF is mostly non-Latin script, so Latin "
                "titles cannot be OCRed; 'absent' here is probably the "
                "checker failing, not a misfile")
    if entry["n_words"] < MIN_CONFIDENT_WORDS:
        return ("check the scan", f"only {entry['n_words']} words of text "
                "extracted, so a title not being found is weak evidence")
    if record is not None and record.get("words_sought", 99) <= MIN_SOLID_WORDS:
        return ("short title", f"the filename leaves only "
                f"{record['words_sought']} testable words, too few to be sure "
                "either way; a heavily abbreviated title can miss its own paper")
    if entry["verdict"] == "misfiled_none_found":
        return ("strong", f"clean text ({entry['n_words']:,} words) and NONE "
                f"of the {entry['n_records']} papers naming this PDF are in it")
    return ("strong", f"clean text ({entry['n_words']:,} words), and the "
            "other paper naming this PDF was found in it")


def write_csv(entries: list[dict], path: Path) -> int:
    """The review table: one row per record whose paper is not in its PDF.

    Every column exists to let the row be judged without opening anything:
    what the filename claims, what the document actually is, and the count of
    title words looked for against found.  Records reclassified as duplicate
    filenames, and records that could not be tested, are excluded.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group_id", "how_sure", "why", "record_year",
                    "absent_title", "pdf_year", "pdf_holds_instead",
                    "pdf_starts", "words_found", "words_sought",
                    "n_records", "size_mb", "latin_fraction", "n_words",
                    "absent_path", "sha256", "decision", "notes"])
        for gid, e in enumerate(entries, 1):
            if not e["verdict"].startswith("misfiled"):
                continue
            present = [r["title"] for r in e["records"] if r["present"] is True]
            for r in e["records"]:
                if r["present"] is not False:
                    continue
                how_sure, why = confidence(e, r)
                w.writerow([
                    gid, how_sure, why,
                    r["year"], r["title"],
                    e["pdf_year"] or "",
                    present[0] if present else "(none of the naming papers)",
                    e["pdf_starts"], r["words_found"], r["words_sought"],
                    e["n_records"], e["size_mb"], e["latin_fraction"],
                    e["n_words"], r["path"], e["sha256"][:12], "", "",
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
    variant = sum(1 for e in entries for r in e["records"]
                  if r["present"] == "name_variant")
    print(f"\n  {absent} records absent from the PDF they name")
    print(f"  {untested} records could not be tested (not the same thing)")
    print(f"  {variant} were duplicate filenames, not misfiles (twins workflow)")

    rows = write_csv(entries, args.csv)
    print(f"  wrote {args.csv} ({rows} rows for review)")
    by_conf = Counter(confidence(e, r)[0] for e in entries
                      if e["verdict"].startswith("misfiled")
                      for r in e["records"] if r["present"] is False)
    for k, v in by_conf.most_common():
        print(f"    {v:4d} groups: {k}")

    if args.json:
        args.json.write_text(json.dumps(entries, indent=1))
        print(f"  wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
