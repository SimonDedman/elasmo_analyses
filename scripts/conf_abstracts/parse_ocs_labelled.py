"""Parser for the OCS abstract books that print an "Abstract" label (2020, 2022, 2025).

Three books, one shape. Everything above the label is the header, everything
below it is the body, and the header's parts are separated by blank lines:

    15                              <- programme number (2020/2022 only)
                                       (2025 has none, and its title is ALLCAPS)
    Reconstructing recreational and commercial catches of Western Australian
    sharks and rays

    Matias Braccini *               <- authors, '*' or '(n)' keyed
                                       (2025 adds "Presented by:" and a
                                        "Authors and Affiliations" label)
    * Department of Primary Industries ...   <- affiliations, then the email
    Matias.Braccini@dpird.wa.gov.au

    Abstract                        <- the anchor: one per abstract, exactly
    Reliable catch information is scarce ...
    This presentation will be recorded.      <- trailer, not body

So the header is read as blank-line paragraphs and each is CLASSIFIED (number,
label, affiliations, the rest), rather than counted off by position: 2025
inserts two labels the others do not have, and any of the parts can wrap.

The label count is the QA instrument, and in these books it is exact: 44 labels
in 2020, 30 in 2022, and 94 in 2025 — where 2025 also prints 94 "Presented by:"
lines, an independent second count that agrees.
"""
import re

from conf_abstracts.parse_si2018_pdf import _is_prose

_MARKER = re.compile(r"^\s*Abstract:?\s*$")
_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")
_AFFIL = re.compile(r"^\s*(?:\*+|\d{1,2}[.)])\s*\S")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.\w")
_PRESENTED = re.compile(r"^\s*Presented by\s*:\s*(.+)$", re.I)
_LABEL = re.compile(r"^\s*(Authors and Affiliations?|Abstract)\s*:?\s*$", re.I)
# Printed under the body, about the presentation rather than the science.
_TRAILER = re.compile(
    r"^\s*(This presentation will be recorded\.?|Student prize considered\.?|"
    r"Short presentation \(poster type\)|Presentation and poster|"
    r"This presentation will not be recorded\.?)\s*$", re.I)


# Words that are common in a title and vanishingly rare in an author list. Two
# of them is enough to keep a Title Case title ("Tails From the Sea: Pelagic
# Thresher Shark Presence at a Coastal Seamount") out of the author block, which
# capitalisation alone cannot do.
_TITLE_WORDS = {"the", "of", "a", "an", "in", "for", "with", "on", "to", "from",
                "using", "at", "by", "its", "into", "during", "under"}


def _is_author_line(s):
    """A name list: mostly capitalised tokens, keyed or comma-separated, and
    without the function words a title carries."""
    toks = re.findall(r"[A-Za-z][A-Za-z’'\-]+", s)
    if len(toks) < 2:
        return False
    if sum(t.lower() in _TITLE_WORDS for t in toks) >= 2:
        return False
    if sum(t[0].isupper() for t in toks) / len(toks) < 0.6:
        return False
    if re.search(r"[,*]|\(\d|\d\s*[,)]| and ", s):
        return True
    # The tail of a wrapped author list is often one bare name with no
    # separator at all ("Jennifer Ovenden"). Accepting only separated lines
    # stopped the walk there and lost the entire author list on 18 of the 74
    # records in 2020 and 2022. A short line of nothing but capitalised names,
    # with none of the title words, is that tail.
    return len(toks) <= 6 and all(t[0].isupper() for t in toks) \
        and not any(t.lower() in _TITLE_WORDS for t in toks) \
        and not s.rstrip().endswith(":")


def _is_name_tail(s):
    """One or two capitalised words and nothing else: the wrapped tail of an
    author list."""
    toks = re.findall(r"[A-Za-z][A-Za-z’'\-]+", s)
    return (1 <= len(toks) <= 2 and len(toks) == len(s.split())
            and all(t[0].isupper() for t in toks)
            and not any(t.lower() in _TITLE_WORDS for t in toks)
            and not s.rstrip().endswith(":"))


def _header_start(lines, mark):
    """Where the header above an "Abstract" label begins.

    Every book in this family separates one abstract from the next with a run of
    at least two blank lines (after the trailer and the page number), and the
    header itself contains none. Prose cannot be used as the boundary: a wrapped
    title line is long and lowercase-rich, so it reads as prose and the walk
    stops in the middle of the header.
    """
    j = mark - 1
    while j >= 1:
        if not lines[j].strip() and not lines[j - 1].strip():
            return j + 1
        j -= 1
    return 0


def _header_labelled(lines):
    """2025: ALLCAPS title, then 'Presented by:', 'Authors and Affiliations',
    the author list, and numbered affiliations."""
    pres_i = next((i for i, l in enumerate(lines) if _PRESENTED.match(l)), None)
    if pres_i is None:
        return None
    presenter = _PRESENTED.match(lines[pres_i]).group(1).strip()
    title = " ".join(l.strip() for l in lines[:pres_i])
    rest = [l.strip() for l in lines[pres_i + 1:] if l.strip() and not _LABEL.match(l)]
    first_affil = next((i for i, l in enumerate(rest) if re.match(r"^\d{1,2}\.\s+\S", l)),
                       len(rest))
    return dict(title=title, authors=" ".join(rest[:first_affil]) or presenter,
                affil=" ".join(rest[first_affil:]), presenter=presenter, num=None)


def _header_starred(lines):
    """2020/2022: programme number, title, author list, '*'-keyed affiliation,
    email. Nothing is labelled, so the affiliation's '*' at line start is the
    anchor and the author lines are walked back from it."""
    ls = [l.strip() for l in lines if l.strip()]
    num = None
    if ls and _NUMBER.match(ls[0]):
        num, ls = ls[0], ls[1:]
    end = next((i for i, l in enumerate(ls)
                if re.match(r"^\*", l) or _EMAIL.search(l)), len(ls))
    # Walk back over the author block. Its last line is often a single wrapped
    # surname ("Huveneers"), which has no separator and no second token, so it
    # has to be accepted - but only BEFORE a full author line has been seen. A
    # one-word line above the author block is the tail of a wrapped TITLE
    # ("... in Oslob," / "Philippines"), and accepting that would eat the title.
    a, seen_author = end, False
    while a > 1:
        prev = ls[a - 1]
        if _is_author_line(prev):
            seen_author, a = True, a - 1
            continue
        if not seen_author and _is_name_tail(prev):
            a -= 1
            continue
        break
    return dict(title=" ".join(ls[:a]), authors=" ".join(ls[a:end]),
                affil=" ".join(ls[end:]), presenter=None, num=num)


def parse_ocs_labelled_blocks(text):
    lines = [ln.rstrip() for ln in text.replace("\f", "\n").splitlines()]
    marks = [i for i, ln in enumerate(lines) if _MARKER.match(ln)]
    blocks = []
    for k, mk in enumerate(marks):
        hs = _header_start(lines, mk)
        body_end = _header_start(lines, marks[k + 1]) if k + 1 < len(marks) else len(lines)
        hdr = lines[hs:mk]
        parsed = _header_labelled(hdr) or _header_starred(hdr)
        body = [l.strip() for l in lines[mk + 1:body_end]
                if l.strip() and not _TRAILER.match(l) and not _NUMBER.match(l)]
        title = re.sub(r"\s+", " ", parsed["title"]).strip()
        blocks.append(dict(
            program_number=parsed["num"], title=title,
            author_raw=re.sub(r"\s+", " ", parsed["authors"]).strip(),
            presenting_author=parsed["presenter"],
            affiliation=re.sub(r"\s+", " ", parsed["affil"]).strip() or None,
            abstract_text=re.sub(r"\s+", " ", " ".join(body)).strip() or None,
            needs_review=int(not (title and parsed["authors"]))))
    return blocks


def qa_markers(blocks, text):
    """Every abstract prints exactly one 'Abstract' label, so the label count is
    the book's own answer for how many there are."""
    marks = sum(1 for ln in text.replace("\f", "\n").splitlines() if _MARKER.match(ln))
    pres = sum(1 for ln in text.replace("\f", "\n").splitlines()
               if _PRESENTED.match(ln))
    full = [b for b in blocks if b["title"] and b["author_raw"]
            and len((b["abstract_text"] or "").split()) >= 50]
    return dict(parsed=len(blocks), markers=marks, presented_by=pres,
                complete=len(full),
                no_title=sum(1 for b in blocks if not b["title"]),
                no_authors=sum(1 for b in blocks if not b["author_raw"]),
                no_affil=sum(1 for b in blocks if not b["affiliation"]))


def ingest_ocs_labelled(con, text, meeting_meta):
    from conf_abstracts import extract, load, tag
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    meta.setdefault("is_ocr", 0)
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_ocs_labelled_blocks(text):
        if not b["title"]:
            continue
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
        pn = re.sub(r"[^a-z]", "", (b["presenting_author"] or "").lower())
        for a in rec.get("authors") or []:
            a["affiliation"] = b["affiliation"]
            if pn:
                a["is_presenter"] = int(re.sub(r"[^a-z]", "",
                                               a["full_name"].lower()) == pn)
                a["presenter_inferred"] = 0
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
