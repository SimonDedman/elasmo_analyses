"""Parser for the born-digital JMIH abstract books (the 'A5' set; 2026 on).

The submission system now exports the whole book with one fixed block per
abstract, so nothing has to be inferred:

    Alena Anderson                                       <- presenting author
    Alena Anderson; Danielle McAree; John Carlson; ...   <- authors (may wrap)
    Student Oral ** Blacknose Shark;Chondrichthys;...    <- type ** keywords
    2.8: Growing Pains: Evidence of Compensatory ...     <- "N.N: Title" (may wrap)
    [314] Compensatory responses in life history ...     <- [submission id] body

This is the richest JMIH source there is - presenting author, full author list,
presentation type, keywords, programme number, title and body - and it needs no
LLM. It supersedes the 2026 PROGRAMME book, which is a scan whose OCR text layer
mangles the "Speaker:" labels and which yielded only 286 of the meeting's 1,003
entries.

The "type **" line is the anchor: every abstract has one, wrapped titles and
author lists do not, and it cannot be confused with prose.
"""
import re

# The presentation types the book prints, plus the one-off award addresses. The
# alternation is anchored to the line start and bounded by " **", so a "**"
# inside a body cannot be mistaken for a header.
_TYPES = [
    ("student oral", "talk"), ("student poster", "poster"),
    ("oral presentation", "talk"), ("symposium talk", "symposium"),
    ("lightning talk", "lightning"), ("poster", "poster"),
    ("keynote address", "keynote"), ("plenary address", "plenary"),
    ("presidential address", "plenary"), ("past-presidential address", "plenary"),
    ("distinguished herpetologist", "plenary"), ("address", "plenary"),
]
_HEADER = re.compile(r"^(?P<type>[^\n*]{1,60}?)\s*\*\*\s*(?P<kw>[^\n]*)$")
# A session number can carry a letter on EITHER side of the dot: parallel AES
# sessions are numbered 59A.4 / 59B.7, and 24 abstracts (most of them elasmo)
# had no programme number at all while the letter was only allowed at the end.
# The colon is optional because a handful of late additions omit it.
_NUMBERED = re.compile(
    r"^(?P<num>P?\d{1,3}[A-Za-z]?\.\d{1,3}[A-Za-z]?)\s*:?\s+(?P<title>.*)$")
_BODY = re.compile(r"^\[(?P<sid>\d+)\]\s*(?P<head>.*)$")
_PAGEISH = re.compile(r"^(JMIH\s+\d{4}|New Orleans|Abstracts|\d{1,4})\s*$", re.I)
# Some abstracts were pasted into the submission form out of Word and kept their
# markup, so the body opens "<p class=\"MsoNormal\" ...>[1065] Cornification is".
_HTML = re.compile(r"<[^>]{1,200}>")
# The book marks changes since the programme in the title itself.
_STATUS = re.compile(r"\[(CANCELLED|WITHDRAWN|NEW|MOVED)\]", re.I)


def _ptype(label):
    low = label.lower()
    for needle, ptype in _TYPES:
        if needle in low:
            return ptype
    return "talk"


def _award(label):
    """Student competition entries and the named addresses both live in the
    type field; keep the printed wording for the ones that are an award."""
    low = label.lower()
    if low.startswith("student") or "award" in low or "address" in low \
            or "distinguished" in low:
        return label.strip()
    return None


def parse_jmih_a5_blocks(text):
    lines = [_HTML.sub("", ln).rstrip() for ln in text.replace("\f", "\n").splitlines()]
    heads = [i for i, ln in enumerate(lines) if _HEADER.match(ln.strip())]
    blocks = []
    for k, h in enumerate(heads):
        m = _HEADER.match(lines[h].strip())
        label = m.group("type").strip()
        keywords = "; ".join(x.strip() for x in m.group("kw").split(";") if x.strip())

        # Backwards: the author list, then the presenting author above it. The
        # block is bounded by the blank line that separates it from the
        # previous abstract's body.
        j = h - 1
        while j >= 0 and not lines[j].strip():
            j -= 1                # a page break lands blank lines above the header
        pre = []
        while j >= 0 and lines[j].strip() and not _BODY.match(lines[j].strip()):
            pre.insert(0, lines[j].strip())
            j -= 1
        pre = [p for p in pre if not _PAGEISH.match(p)]
        if not pre:
            continue
        presenter = pre[0]
        authors = " ".join(pre[1:]).strip() or presenter

        # Forwards: the title (one or more lines, opening "N.N:"), then the
        # body, which runs to the start of the next abstract's block.
        stop = heads[k + 1] if k + 1 < len(heads) else len(lines)
        num, title_parts, body_parts, seen_body = None, [], [], False
        for ln in lines[h + 1:stop]:
            s = ln.strip()
            if not s or _PAGEISH.match(s):
                continue
            bm = _BODY.match(s)
            if bm and not seen_body:
                seen_body = True
                if bm.group("head"):
                    body_parts.append(bm.group("head"))
                continue
            if not seen_body:
                nm = _NUMBERED.match(s)
                if nm and num is None:
                    num = nm.group("num")
                    if nm.group("title"):
                        title_parts.append(nm.group("title"))
                else:
                    title_parts.append(s)
            else:
                body_parts.append(s)
        # The trailing lines of a body belong to the NEXT abstract's header
        # block, which was already claimed walking backwards from it; drop them.
        if k + 1 < len(heads):
            tail = []
            j = heads[k + 1] - 1
            while j >= 0 and lines[j].strip() and not _BODY.match(lines[j].strip()):
                tail.insert(0, lines[j].strip())
                j -= 1
            for t in tail:
                if body_parts and body_parts[-1] == t:
                    body_parts.pop()
        title = re.sub(r"\s+", " ", " ".join(title_parts)).strip()
        body = re.sub(r"\s+", " ", " ".join(body_parts)).strip()
        if not title:
            continue
        sm = _STATUS.search(title)
        status = sm.group(1).lower() if sm else None
        title = _STATUS.sub("", title).strip()
        blocks.append(dict(
            program_number=num, title=title, author_raw=authors,
            presenting_author=presenter, abstract_text=body or None,
            keywords=keywords or None, presentation_type=_ptype(label),
            award=_award(label), type_label=label, status=status))
    return blocks


def ingest_jmih_a5(con, text, meeting_meta):
    """Parse a born-digital JMIH abstract book and insert its abstracts."""
    from conf_abstracts import load, extract, tag
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    meta.setdefault("is_ocr", 0)
    mid = load.upsert_meeting(con, meta)
    have = {r[1] for r in con.execute("PRAGMA table_info(abstracts)")}
    if "status" not in have:
        con.execute("ALTER TABLE abstracts ADD COLUMN status TEXT")
    n = 0
    for b in parse_jmih_a5_blocks(text):
        rec = extract.extract_fields(
            dict(program_number=b["program_number"], session_line="",
                 author_raw=b["author_raw"], title=b["title"],
                 abstract_text=b["abstract_text"]),
            meta["meeting"], fmt="jmih_book", use_llm=False)
        rec["keywords"] = b["keywords"]
        rec["presentation_type"] = b["presentation_type"]
        rec["award"] = b["award"]
        # The book names the presenting author outright, so the usual
        # first-author assumption is not needed here.
        pn = re.sub(r"[^a-z]", "", b["presenting_author"].lower())
        matched = False
        for a in rec.get("authors") or []:
            a["is_presenter"] = int(re.sub(r"[^a-z]", "", a["full_name"].lower()) == pn)
            a["presenter_inferred"] = 0
            matched = matched or bool(a["is_presenter"])
        if not matched and rec.get("authors"):
            rec["authors"][0]["is_presenter"] = 1
            rec["authors"][0]["presenter_inferred"] = 1
        rec = tag.resolve(rec, meta["meeting"])
        if rec.get("_llm_is_elasmo") and not rec["is_elasmo"]:
            rec["is_elasmo"] = 1
            rec["elasmo_basis"] = "content"
        rec["needs_review"] = 0
        aid = load.insert_abstract(con, mid, rec)
        if aid:
            if b["status"]:
                con.execute("UPDATE abstracts SET status=? WHERE abstract_id=?",
                            (b["status"], aid))
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
