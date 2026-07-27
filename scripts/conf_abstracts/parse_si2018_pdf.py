"""Parse the SI2018 (Joao Pessoa) PDF abstract book.

Different layout from SI2026: NO abstract IDs and NO per-abstract email. The
reliable anchor is the `Keywords:` line that TERMINATES each abstract. Block
shape (superscript affiliation numbers land on their own lines via pdftotext):
    <title, 1-3 lines>
    <authors: Name<superscript>, ...>
    <affiliation text>            (+ stray bare number lines)
    <abstract body>
    Keywords: ...                 <- terminator
    - N -                         <- page footer
"""
import re

_KW = re.compile(r"^\s*Keywords:\s*(.*)$", re.I)
_AUTHOR = re.compile(r"[A-Za-zÀ-ÿ]\d")          # a name immediately followed by a superscript digit
_FOOTER = re.compile(r"^\s*-\s*\d+\s*-\s*$")     # "- 13 -"
_BARE_NUM = re.compile(r"^\s*\d+\s*$")
# header: "398 – Oral Session, Monday 4 June 2018"  (en-dash or hyphen)
_HEADER = re.compile(
    r"^\s*(\d{1,4})\s*[–—-]\s*"
    r"(Oral|Poster|Speed|Keynote|Plenary|Lightning)[\w ]*Session\s*,?\s*(.*)$", re.I)
_TYPE = {"oral": "talk", "poster": "poster", "speed": "lightning",
         "keynote": "keynote", "plenary": "plenary", "lightning": "lightning"}
_DATE = re.compile(
    r"^\s*(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\s+\d{1,2}\s+\w+\s+\d{4}\s*$", re.I)


def _is_prose(s: str) -> bool:
    """A real body/sentence line: long, lowercase-rich, not an author/affil line."""
    s = s.strip()
    if len(s) < 55 or _AUTHOR.search(s):
        return False
    words = s.split()
    if len(words) < 9:
        return False
    lower = sum(1 for w in words if w[:1].islower())
    return lower / len(words) >= 0.4
_AFFIL_KW = re.compile(
    r"\b(univers|institut|federal|centro|department|laborat|museu|college|"
    r"funda|comiss|IF[A-Z]{2}|U[FN][A-Z]{1,3}|NOAA|Brazil|Mexico|USA|Board)\b", re.I)


def _clean(lines):
    return [l for l in lines if not _FOOTER.match(l)]


def _parse_block(lines):
    lines = _clean(lines)
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    # header line "NNN – Type Session, Date" marks a real abstract (skips front
    # matter / committee lists that have no header).
    hi = next((i for i, l in enumerate(lines) if _HEADER.match(l)), None)
    prog, ptype, sdate = None, "talk", None
    if hi is not None:
        m = _HEADER.match(lines[hi])
        prog = m.group(1)
        ptype = _TYPE.get(m.group(2).lower(), "talk")
        sdate = (m.group(3) or "").strip() or None
        lines = lines[hi + 1:]           # content starts after the header
        while lines and (not lines[0].strip() or _DATE.match(lines[0])):
            # drop leading blanks and a stray date line the header split off
            if lines[0].strip() and _DATE.match(lines[0]) and sdate is None:
                sdate = lines[0].strip()
            lines.pop(0)
    else:
        return None                      # no header -> not an abstract
    # author line = first with a name+superscript-digit
    ai = next((i for i, l in enumerate(lines) if _AUTHOR.search(l)), None)
    title = " ".join(l.strip() for l in lines[:ai]).strip() if ai else (
        lines[0].strip() if lines else None)
    # body = from the first genuine prose line to the end (skips authors/affils)
    bstart = next((i for i, l in enumerate(lines) if _is_prose(l)), None)
    # authors = superscript-bearing lines between title and body
    astart = ai if ai else 0
    aend = bstart if bstart is not None else len(lines)
    author_raw = " ".join(l.strip() for l in lines[astart:aend]
                          if _AUTHOR.search(l)).strip() or None
    if bstart is None:
        body = None
    else:
        body = " ".join(l.strip() for l in lines[bstart:] if l.strip())
        body = re.sub(r"\s{2,}", " ", body).strip()
    return dict(title=title or None, abstract_text=body or None,
                author_raw=author_raw, program_number=prog,
                presentation_type=ptype, session_datetime=sdate)


def parse_si2018_blocks(text: str):
    """Split into abstracts using the Keywords terminator. Returns list of
    dicts {title, abstract_text, keywords}."""
    lines = text.splitlines()
    kw_idx = [i for i, l in enumerate(lines) if _KW.match(l)]
    blocks = []
    prev = 0
    for k in kw_idx:
        block_lines = lines[prev:k]
        parsed = _parse_block(block_lines)
        if parsed and parsed["abstract_text"] and len(parsed["abstract_text"].split()) >= 40:
            kw = _KW.match(lines[k]).group(1).strip()
            parsed["keywords"] = re.sub(r"\s+-\s*\d+\s*-?\s*$", "", kw).strip() or None
            blocks.append(parsed)
        prev = k + 1
    return blocks


def ingest_si2018(con, pdf_text, meeting_meta):
    """Parse SI2018 PDF and insert abstracts (all elasmo). Returns count."""
    from conf_abstracts import load, extract
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_si2018_blocks(pdf_text):
        title = b.get("title")
        rec = dict(
            program_number=b.get("program_number"),
            title=title,
            presentation_type=b.get("presentation_type", "talk"),
            session_name=None, societies_explicit=None, award=None,
            society_inferred=None, society="AES", society_basis="meeting",
            session_datetime=b.get("session_datetime"), location=None,
            abstract_text=b.get("abstract_text"),
            keywords=b.get("keywords"),
            is_elasmo=1, elasmo_basis="meeting", confidence=0.8,
            needs_review=0 if (title and 10 < len(title) < 160) else 1,
            source_page=None,
            authors=extract.parse_authors(b.get("author_raw") or ""),
        )
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
