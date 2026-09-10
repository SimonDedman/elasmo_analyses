"""Cut a general-ichthyology book down to the pages that carry elasmobranch work,
so a Fable extraction pays for the shark content instead of the whole volume.

The two IPFC volumes are 20 of the 47 queued OCS/IPFC chunks and are mostly
teleost: only 32% (2009) and 17.5% (2023) of their text pages mention an
elasmobranch at all. This screens each page with the same deterministic lexicon
that decides `is_elasmo`, keeps the hits, and keeps their NEIGHBOURS too,
because an abstract that straddles a page break can name its shark on one page
and carry its title and authors on the other.

WHAT THIS COSTS, stated plainly: the result is a partial extraction. Pages that
never name an elasmobranch are not read at all, so the teleost and general
abstracts in these volumes stay uncaptured, and the coverage matrix must say
"elasmo-targeted", never "Ingested". That is a deliberate trade for the two
general-fisheries volumes; it is NOT how the chondrichthyan books are handled.

Recall is measured, not assumed: `control()` runs the screen over a book we have
already parsed in full, maps every abstract to the page it starts on, and reports
what share of the known elasmo abstracts survive the cut.

Usage:
  prescan_elasmo_pages.py --control OCS2016
  prescan_elasmo_pages.py --book IPFC2009 [--context 1] [--write]
"""
import argparse
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts import lexicon  # noqa: E402

_NUM = re.compile(r"^\s*(\d{1,4})\s*$")


def pages_of(pdf):
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True, timeout=600).stdout
    return txt.split("\f")


def screen(pages, context=1, before=None, after=None, skip_pages=()):
    """`skip_pages` is 1-based and applied BEFORE screening, for front matter
    that names elasmobranchs without being about them. IPFC 2009 lists every
    talk in a contents section on pages 3-4; those pages passed the lexicon,
    were kept, and the Fable agents extracted 356 title+author records from the
    LISTING instead of reading the abstract pages behind it — 369 of its 416
    records came back with no body. Docling does not help here: it labels those
    pages plain `text`, not `document_index`."""
    # Keeping the page AFTER a hit protects a body running over the page break;
    # keeping the page BEFORE buys nothing, since both controls (OCS2016 n=66,
    # JMIH2016 n=226) put the mention on the title's own page in 100% of cases.
    before = context if before is None else before
    after = context if after is None else after
    skip = {n - 1 for n in skip_pages}
    hits = {i for i, p in enumerate(pages)
            if i not in skip and lexicon.is_elasmo_text(p, "")}
    keep = set()
    for i in hits:
        keep.update(range(max(0, i - before), min(len(pages), i + after + 1)))
    return hits, sorted(keep - skip)


def reduce_text(pages, keep):
    """The kept pages, in order, with a marker where pages were dropped so a
    reader (or an extraction agent) can see the text is not continuous."""
    out, prev = [], None
    for i in keep:
        if prev is not None and i != prev + 1:
            out.append(f"[... {i - prev - 1} page(s) with no elasmobranch mention "
                       f"omitted by prescan_elasmo_pages.py ...]")
        out.append(pages[i])
        prev = i
    return "\f".join(out)


def control(book_key, context=1, before=None, after=None):
    """Measure recall against a book already parsed in full.

    Each abstract is mapped to the page its number is printed on, then the
    screen is applied and we count how many of the KNOWN elasmo abstracts fall
    on a kept page. A number under 100% is the cost of the cut, in records.
    """
    con = sqlite3.connect(str(C.DB_PATH))
    meeting, year = book_key[:-4], int(book_key[-4:])
    row = con.execute("select meeting_id, source_pdf from meetings where meeting=? "
                      "and year=? and doc_type='abstract_book'",
                      (meeting, year)).fetchone()
    if not row:
        sys.exit(f"no parsed abstract book in the DB for {book_key}")
    mid, pdf = row
    recs = con.execute("select title, is_elasmo from abstracts where meeting_id=?",
                       (mid,)).fetchall()
    con.close()
    pages = pages_of(Path(pdf))
    # Which page does each abstract sit on? Matched on a verbatim run of the
    # title, not on a printed number: numbering is per-format and most books
    # either have none or print it somewhere the page split cannot see, which
    # silently shrinks the control to a handful of records and makes its recall
    # figure meaningless.
    flat = [re.sub(r"[^a-z0-9]", "", p.lower()) for p in pages]
    known = []
    for title, el in recs:
        key = re.sub(r"[^a-z0-9]", "", (title or "").lower())[:60]
        if len(key) < 40:
            continue
        pg = next((i for i, f in enumerate(flat) if key in f), None)
        if pg is not None:
            known.append((title, el, pg))
    hits, keep = screen(pages, context, before, after)
    keep_set = set(keep)
    el = [(t, pg) for t, e, pg in known if e]
    kept_el = [t for t, pg in el if pg in keep_set]
    lost = [t[:60] for t, pg in el if pg not in keep_set]
    print(f"{book_key}: {len(pages)} pages, {len(hits)} mention an elasmobranch, "
          f"{len(keep)} kept with context={context} "
          f"({len(keep)/len(pages):.1%} of the book)")
    print(f"  {len(known)} of {len(recs)} abstracts located by title; "
          f"{len(el)} of them elasmo; "
          f"RECALL {len(kept_el)}/{len(el)} = {len(kept_el)/max(len(el),1):.1%}")
    for t_ in lost[:8]:
        print(f"  LOST: {t_}")
    return len(kept_el), len(el)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", help="book key already parsed in full, e.g. OCS2016")
    ap.add_argument("--book", help="book key to screen, e.g. IPFC2009")
    ap.add_argument("--context", type=int, default=1)
    ap.add_argument("--before", type=int, default=None,
                    help="pages kept before a hit (default: --context)")
    ap.add_argument("--after", type=int, default=None,
                    help="pages kept after a hit (default: --context)")
    ap.add_argument("--write", action="store_true",
                    help="write the reduced text beside the worklist source texts")
    a = ap.parse_args()
    if a.control:
        control(a.control, a.context, a.before, a.after)
        return
    if not a.book:
        sys.exit("give --control or --book")
    pdf = ELASMO_TARGETED_PDFS[a.book]
    pages = pages_of(Path(pdf))
    hits, keep = screen(pages, a.context, a.before, a.after)
    text = reduce_text(pages, keep)
    full = sum(len(p) for p in pages)
    print(f"{a.book}: {len(pages)} pages, {len(hits)} elasmo, {len(keep)} kept "
          f"({len(keep)/len(pages):.1%}); {full} -> {len(text)} chars "
          f"({len(text)/max(full,1):.1%}), ~{len(text)//4//25000 + 1} Fable chunks")
    if a.write:
        out = Path(C.OUT) / "conf_abstracts" / ".fable_src" / f"{a.book}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"  wrote {out}")


ELASMO_TARGETED_PDFS = {
    "IPFC2009": str(C.CONFERENCES / "2009" / "2009_IPFC_AbstractBook.pdf"),
    "IPFC2023": str(C.CONFERENCES / "2023" / "2023_IPFC_AbstractBook.pdf"),
}


if __name__ == "__main__":
    main()
