"""Parser for the 'A3' JMIH abstract-book format (2005-JMIH-Abstract-Book and
the OCR'd 1997-2004 books).

Block shape:
    254                                         <- abstract number (own line)
    *FEITOZA, B. M.; ROSA, R. S.; *ROCHA, L. A. <- UPPERCASE authors, * = presenter
    (LAR) University of Florida ...; (BMF) ...  <- initial-keyed affiliations
    Deep reef fishes of Paraiba State ...       <- title (Title Case)
    The northeastern Brazilian coast has ...    <- body
    19/06/2000 - 09:00:00 AM - Conquistador     <- optional trailing datetime/room

Delimiter: a bare number line followed (within a couple of lines) by an
UPPERCASE author line. Works with or without the underscore separators that the
2005 book has but the OCR'd books lose.
"""
import re

from conf_abstracts.segment import _title_like, _AFFIL_KW
from conf_abstracts.parse_si2018_pdf import _is_prose
from conf_abstracts.parse_jmih_a2 import _is_author_start as _mixed_author

_NUM = re.compile(r"^\s*(\d{1,4})\s*$")
_UPPER_AUTHOR = re.compile(r"^\s*\*?\s*[A-ZÀ-Þ][A-ZÀ-Þ'’.\-]+\s*,")
_AFFIL_PAREN = re.compile(r"^\s*\([A-Z]{1,4}[,;]?")          # "(LAR) ...", "(ABC, PJM) ..."
_DATETIME = re.compile(r"\d{1,2}[/.]\d{1,2}[/.]\d{2,4}.*(AM|PM|:\d\d)")


def _is_upper_author(s: str) -> bool:
    s = s.strip()
    if not _UPPER_AUTHOR.match(s):
        return False
    alpha = [c for c in s if c.isalpha()]
    if not alpha:
        return False
    upper = sum(1 for c in alpha if c.isupper())
    return upper / len(alpha) >= 0.6


def _find_starts(lines):
    """Abstract start = a bare number line with an UPPERCASE author line within
    the next 3 non-empty lines."""
    starts = []
    for i, l in enumerate(lines):
        if not _NUM.match(l):
            continue
        seen = 0
        for j in range(i + 1, min(i + 5, len(lines))):
            s = lines[j].strip()
            if not s:
                continue
            seen += 1
            # UPPERCASE (2005) or mixed-case "Surname, Initials" (OCR'd books)
            if _is_upper_author(s) or _mixed_author(s):
                starts.append((i, j))
                break
            if seen >= 3:
                break
    return starts


def _parse_block(lines, author_idx):
    lines = [l.rstrip() for l in lines]
    # authors = consecutive UPPERCASE author / continuation lines from author_idx
    ai = author_idx
    authors_lines = []
    k = ai
    while k < len(lines):
        s = lines[k].strip()
        if not s:
            k += 1
            continue
        if _is_upper_author(s) or (authors_lines and s.isupper()):
            authors_lines.append(s)
            k += 1
        else:
            break
    author_raw = " ".join(authors_lines).strip()
    rest = lines[k:]
    # title = first Title-Case line that is not an affiliation / uppercase / prose
    ti = None
    for idx, s in enumerate(rest):
        s = s.strip()
        if not s or _AFFIL_PAREN.match(s) or _AFFIL_KW.search(s) or s.isupper():
            continue
        if _title_like(s) and not _is_prose(s):
            ti = idx
            break
    if ti is None:
        return None
    # body = first prose line after title
    bstart = next((x for x in range(ti, len(rest)) if _is_prose(rest[x].strip())), None)
    if bstart is None or bstart == ti:
        bstart = ti + 1
    title = " ".join(rest[ti:bstart]).strip()
    body_lines = [x.strip() for x in rest[bstart:] if x.strip()]
    # drop a trailing datetime/room line
    if body_lines and _DATETIME.search(body_lines[-1]):
        body_lines = body_lines[:-1]
    body = re.sub(r"\s{2,}", " ", " ".join(body_lines)).strip()
    if not body or len(body.split()) < 40:
        return None
    return dict(author_raw=author_raw, title=title or None,
                abstract_text=body or None)


_SEP = re.compile(r"^_{15,}\s*$", re.M)


def _parse_sep_block(chunk_lines):
    """Parse one underscore-delimited block: [number?] [authors] [affils] [title]
    [body]. Used for the 2005 book which has separators."""
    lines = [l for l in chunk_lines if l.strip()]
    if not lines:
        return None
    program_number = None
    if _NUM.match(lines[0]):
        program_number = lines[0].strip()
        lines = lines[1:]
    # author line = first upper-author (or first line if none)
    ai = next((i for i, l in enumerate(lines) if _is_upper_author(l.strip())), 0)
    parsed = _parse_block(lines[ai:], 0)
    if parsed:
        parsed["program_number"] = program_number
    return parsed


def parse_jmih_a3_blocks(text: str):
    lines = text.splitlines()
    # If the book has underscore separators (2005), split on them; else use
    # number+UPPERCASE-author starts (OCR'd 1997-2004 lose the separators).
    if len(_SEP.findall(text)) > 50:
        blocks = []
        for chunk in _SEP.split(text):
            parsed = _parse_sep_block(chunk.splitlines())
            if parsed:
                blocks.append(parsed)
        return blocks
    starts = _find_starts(lines)
    blocks = []
    for n, (num_i, auth_i) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        parsed = _parse_block(lines[auth_i:end], 0)
        if parsed:
            parsed["program_number"] = lines[num_i].strip()
            blocks.append(parsed)
    return blocks


def ingest_jmih_a3(con, text, meeting_meta):
    """Parse an A3-format book and insert abstracts. Returns count."""
    from conf_abstracts import load, extract, tag
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_jmih_a3_blocks(text):
        rec = extract.extract_fields(
            dict(program_number=b.get("program_number"), session_line="",
                 author_raw=b["author_raw"], title=b["title"],
                 abstract_text=b["abstract_text"]),
            meta["meeting"], fmt="asih_book", use_llm=False)
        rec["keywords"] = None
        rec = tag.resolve(rec, meta["meeting"])
        if rec.get("_llm_is_elasmo") and not rec["is_elasmo"]:
            rec["is_elasmo"] = 1
            rec["elasmo_basis"] = "content"
        if (not rec.get("title") or len(rec["title"]) > 200
                or _AFFIL_KW.search(rec.get("title") or "")):
            rec["needs_review"] = 1
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
