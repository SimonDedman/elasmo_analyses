"""Parser for the numbered born-digital OCS abstract books (2016 to start).

The book is a submission-system export with one fixed block per abstract and no
front matter at all - abstract 1 opens page 1:

    <centred number, own line>                     <- 1..N, strictly sequential
    Are Sharks Smart? Using Brain Anatomy ...      <- title (may wrap)
    Kara Yopak1                                    <- authors, superscript affil keys
    1. University of Western Australia, Crawley    <- numbered affiliations
    Selection for cognitive ability has been ...   <- body, to the next number

The affiliation line is the anchor rather than the author line: every abstract
has at least one, it is unmistakable (`N. Institution`), and it fixes BOTH
boundaries at once - the authors are the line above it and the body starts
after the last one. Detecting the author line directly does not work, because
the superscript keys are dropped for authors with no affiliation ("William
White1, Gerry Allen, Mark Erdmann").

The numbers are also the QA instrument: they run 1..N with no gaps, so a
parse can be checked against the book's own count rather than against this
parser's opinion of it. `qa_numbers()` reports that, and the author index in the
back pages gives a second, independent check on the same numbers.
"""
import re

from conf_abstracts.parse_si2018_pdf import _is_prose

_NUM = re.compile(r"^\s*(\d{1,4})\s*$")
_AFFIL = re.compile(r"^\s*\d{1,2}\.\s+\S")
# An author line carries at least one superscript affiliation key fused to a
# name ("Kara Yopak1", "Sianipar6") and is mostly capitalised tokens. Long
# author lists wrap, so the line above the affiliations can be the tail of the
# list rather than the whole of it; the ratio test is what keeps a title
# containing "CO2" or "Bin 1" out.
_SUPER = re.compile(r"[A-Za-z]\d")
# The back-of-book author index: "Yopak, K        2" / "Walker, T.I  112,218,62".
_INDEX = re.compile(r"^[A-Z][A-Za-z’'\-]+,\s*[A-Z]([.\s]|[A-Z])*\s+\d[\d,\s]*$")


def _is_author_line(s):
    if not _SUPER.search(s) or len(s) > 400:
        return False
    toks = [t for t in re.findall(r"[A-Za-z][A-Za-z’'\-]+", s) if len(t) > 1]
    if not toks:
        return False
    return sum(t[0].isupper() for t in toks) / len(toks) >= 0.6


def _find_starts(lines):
    """Number lines that continue the sequence, so a stray page number or a
    figure caption cannot open a block. The first abstract is number 1."""
    starts, want = [], 1
    for i, ln in enumerate(lines):
        m = _NUM.match(ln)
        if m and int(m.group(1)) == want:
            starts.append((i, want))
            want += 1
    return starts


def parse_ocs_numbered_blocks(text):
    lines = [ln.rstrip() for ln in text.replace("\f", "\n").splitlines()]
    starts = _find_starts(lines)
    blocks = []
    for k, (i, num) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        blk = [ln.strip() for ln in lines[i + 1:end] if ln.strip()]
        # The last block runs into the author index at the back of the book.
        idx = next((j for j, l in enumerate(blk) if _INDEX.match(l)), None)
        if idx is not None:
            blk = blk[:idx]
        if len(blk) < 3:
            continue
        # Affiliations sit at the top of the block, directly under the author
        # line - never after prose. Without that last test, an abstract whose
        # author gave no affiliation anchors on a numbered sentence inside its
        # own body ("3. The critical prey density threshold was 11.2 mg m-3 ...")
        # and the title swallows the author line and everything above it.
        first_affil = next((j for j, l in enumerate(blk[:8])
                            if _AFFIL.match(l) and j >= 2 and not _is_prose(blk[j - 1])),
                           None)
        if first_affil is None or first_affil < 2:
            # No affiliations: the body is the first prose line, the authors are
            # the line above it, and the title is what is left.
            p = next((j for j, l in enumerate(blk) if j >= 2 and _is_prose(l)), None)
            if p is None:
                p = 2
            blocks.append(dict(program_number=str(num),
                               title=re.sub(r"\s+", " ", " ".join(blk[:p - 1])).strip(),
                               author_raw=blk[p - 1],
                               affiliation=None,
                               abstract_text=re.sub(r"\s+", " ", " ".join(blk[p:])) or None,
                               needs_review=1))
            continue
        j = first_affil
        while j < len(blk) and _AFFIL.match(blk[j]):
            j += 1
        # Walk back over every wrapped author line, not just the last one.
        a = first_affil - 1
        while a > 1 and _is_author_line(blk[a - 1]):
            a -= 1
        blocks.append(dict(
            program_number=str(num),
            title=re.sub(r"\s+", " ", " ".join(blk[:a])).strip(),
            author_raw=" ".join(blk[a:first_affil]),
            affiliation=" ".join(blk[first_affil:j]),
            abstract_text=re.sub(r"\s+", " ", " ".join(blk[j:])).strip() or None,
            needs_review=0))
    return blocks


def qa_numbers(blocks, text):
    """Compare what was parsed with the book's own numbering: the highest
    number printed, and any number in that range that produced no record."""
    lines = [ln.rstrip() for ln in text.replace("\f", "\n").splitlines()]
    printed = [int(m.group(1)) for m in (_NUM.match(l) for l in lines) if m]
    top = max((n for n in printed if n <= 2000), default=0)
    got = {int(b["program_number"]) for b in blocks}
    return dict(parsed=len(blocks), highest_number=top,
                missing=sorted(set(range(1, top + 1)) - got)[:20],
                n_missing=len(set(range(1, top + 1)) - got))


def ingest_ocs_numbered(con, text, meeting_meta):
    """Parse a numbered OCS abstract book and insert its abstracts."""
    from conf_abstracts import extract, load, tag
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    meta.setdefault("is_ocr", 0)
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_ocs_numbered_blocks(text):
        rec = extract.extract_fields(
            dict(program_number=b["program_number"], session_line="",
                 author_raw=b["author_raw"], title=b["title"],
                 abstract_text=b["abstract_text"]),
            meta["meeting"], fmt="jmih_book", use_llm=False)
        rec = tag.resolve(rec, meta["meeting"], year=meta.get("year"))
        if rec.get("_llm_is_elasmo") and not rec["is_elasmo"]:
            rec["is_elasmo"] = 1
            rec["elasmo_basis"] = "content"
        if b["needs_review"]:
            rec["needs_review"] = 1
        for a in rec.get("authors") or []:
            a["affiliation"] = b["affiliation"]
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
