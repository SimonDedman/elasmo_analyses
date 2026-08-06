"""General parser for EEA (European Elasmobranch Association) abstract books.

EEA books share a TITLE-FIRST layout (unlike the JMIH/ASIH author-first or
ID-first formats):
    [session / time / 'ORAL CONTRIBUTION' / page-number header]   (optional)
    TITLE            (1-3 lines, first)
    AUTHORS          (A. Surname & B. Surname | Name 1,2 | SURNAME, Init.)
    AFFILIATION(S)   (institution lines, sometimes numbered/superscript)
    [Email: ...]
    BODY             (prose)
    [Keywords: ...]

Segmentation is prose-gap based: each abstract = a short header block followed
by a prose body. All EEA records are elasmo (meeting=EEA).
"""
import re

from conf_abstracts.segment import _title_like, _AFFIL_KW
from conf_abstracts.parse_si2018_pdf import _is_prose

_NOISE = re.compile(
    r"^\s*(Session\b|ORAL\b|POSTER\b|Oral Contribution|Poster Contribution|"
    r"Keywords?\b|Organisation\b|Address\b|Email\b|\d{1,3}\s*$|"
    r"\d{1,2}[:.]\d{2}\b|Page\b|Contents?\b|Programme\b|Index\b)", re.I)
_EMAIL = re.compile(r"[\w.\-]+@[\w.\-]+")
# title function-words (NOT 'and'/'&', which are author connectors)
_TITLEWORD = re.compile(
    r"\b(of|the|in|on|for|with|to|from|by|between|during|using|through|within|"
    r"among|into|study|effects?|role|status|case|analysis|assessment|new|"
    r"population|distribution|reproductive|management|conservation)\b", re.I)
# a name token: initial "J." / "J.F." or a Capitalised word (opt superscript/accent)
_NAMETOK = re.compile(r"^(?:[A-ZÀ-Ý]\.?){1,3}$|^[A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]+\d*[,;]?$")


def _is_namelist(s):
    """Author line: mostly name tokens (initials/surnames + and/&/commas),
    no title function-words, not an affiliation/email."""
    s = s.strip()
    if not s or _EMAIL.search(s) or _AFFIL_KW.search(s) or _TITLEWORD.search(s):
        return False
    core = re.sub(r"\b(and)\b|&|,|;", " ", s)          # drop author connectors
    words = [w for w in core.split() if w]
    if len(words) < 2:
        return False
    nameish = sum(1 for w in words if _NAMETOK.match(w))
    return nameish >= 2 and nameish / len(words) >= 0.7


def _parse_header(header_lines):
    """Return (title, author_raw, affiliation) from the header block."""
    lines = [l.strip() for l in header_lines if l.strip() and not _NOISE.match(l)]
    if not lines:
        return None, None, None
    # TITLE = leading title-like lines until the first author/affiliation line
    ti = 0
    title_parts = []
    while ti < len(lines):
        s = lines[ti]
        if _is_namelist(s) or _AFFIL_KW.search(s) or _EMAIL.search(s):
            break
        if _title_like(s) or len(s) > 25:
            title_parts.append(s)
            ti += 1
        else:
            break
    title = " ".join(title_parts).strip()
    rest = lines[ti:]
    # authors = leading name-list lines of the remainder
    auth = []
    ai = 0
    while ai < len(rest) and _is_namelist(rest[ai]):
        auth.append(rest[ai])
        ai += 1
    author_raw = " ".join(auth).strip()
    # affiliation = first institution / email-bearing line after authors
    affil = next((l for l in rest[ai:] if _AFFIL_KW.search(l) or _EMAIL.search(l)), None)
    return (title or None), (author_raw or None), affil


def parse_eea_blocks(text):
    lines = text.splitlines()
    blocks = []
    header = []
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if _is_prose(s):
            body = [s]
            i += 1
            while i < n and (_is_prose(lines[i].strip()) or not lines[i].strip()):
                t = lines[i].strip()
                if t and not re.match(r"(?i)^keywords", t):
                    body.append(t)
                i += 1
            title, author_raw, affil = _parse_header(header)
            body_txt = re.sub(r"\s{2,}", " ", " ".join(body)).strip()
            if title and body_txt and len(body_txt.split()) >= 45:
                blocks.append(dict(title=title, author_raw=author_raw,
                                   affiliation=affil, abstract_text=body_txt))
            header = []
        else:
            if s:
                header.append(s)
            if len(header) > 12:          # don't let noise accumulate unbounded
                header = header[-6:]
            i += 1
    return blocks


def ingest_eea(con, text, meeting_meta):
    from conf_abstracts import load, extract, tag
    meta = dict(meeting_meta)
    meta.setdefault("meeting", "EEA")
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_eea_blocks(text):
        rec = extract.extract_fields(
            dict(program_number=None, session_line="", author_raw=b["author_raw"] or "",
                 title=b["title"], abstract_text=b["abstract_text"]),
            "EEA", fmt="asih_book", use_llm=False)
        rec.update(abstract_text=b["abstract_text"], keywords=None,
                   society="AES", society_basis="meeting")
        if b.get("affiliation") and rec["authors"]:
            rec["authors"][0]["affiliation"] = b["affiliation"]
        rec = tag.resolve(rec, "EEA")     # EEA -> is_elasmo=1, basis=meeting
        if not rec.get("title") or len(rec["title"]) > 240:
            rec["needs_review"] = 1
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
