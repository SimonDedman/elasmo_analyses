"""Parser for the OCR'd 1997-2004 JMIH books (the 'A4' set).

These are single-column, author-delimited, with NO abstract numbers:
    LÓPEZ, J. ANDRÉS                                   <- author (small-caps; OCR mangles it)
    School of Fisheries, Univ. of Washington, Seattle  <- affiliation
    Umbrid phylogeny based on mitochondrial DNA ...     <- title
    The Umbridae contains six species ...               <- body
    (Poster Session 2, Sunday 8-5)                      <- trailing session note

OCR mangles the small-caps author names badly, but affiliation/title/body are
recoverable. Segmentation is prose-gap based: each abstract is a short header
block (author, affiliation, title) followed by a prose body. The schedule
sections have no prose bodies and are naturally skipped.
"""
import re

from conf_abstracts.segment import _title_like, _AFFIL_KW
from conf_abstracts.parse_si2018_pdf import _is_prose

_SESSION_NOTE = re.compile(r"^\(?\s*(Poster|Oral|Session|Symposium|Contributed)",
                           re.I)
_PAREN_INIT = re.compile(r"\([A-Z]{1,4}[,)]")             # "(RSM)", "(AA,BB)"
_POSTAL = re.compile(r"\b[A-Z]{2}\s?\d{4,5}\b|\b\d{5}\b")  # "NJ 07732", "93195"
_BIO = re.compile(r"\b(Professor|Lab\.?|Laboratory|Museum|Dept|Department|"
                  r"Institut|Research|Univers|College|Academy|Station)\b", re.I)


def _looks_affil(s: str) -> bool:
    return bool(_AFFIL_KW.search(s) or _PAREN_INIT.search(s)
                or _POSTAL.search(s) or _BIO.search(s))


def _make_abstract(header, body_lines):
    header = [h.strip() for h in header if h.strip()]
    body = " ".join(b.strip() for b in body_lines if b.strip())
    body = re.sub(r"\s{2,}", " ", body).strip()
    if not body or len(body.split()) < 45:
        return None
    if len(header) < 2:
        return None
    # title = last header line that is title-like and not an affiliation
    ti = None
    for k in range(len(header) - 1, -1, -1):
        s = header[k]
        if _title_like(s) and not _looks_affil(s) and not _is_prose(s):
            ti = k
            break
    title = header[ti] if ti is not None else None
    # author = first header line; affiliation = a header line that looks like one
    author_raw = header[0]
    affil = next((h for h in header[1:] if _looks_affil(h)), None)
    # Real abstracts carry an affiliation; front-matter (registration, logo,
    # transport, welcome) does not — require one to filter logistics noise.
    if not affil or not title:
        return None
    return dict(author_raw=author_raw, affiliation=affil, title=title,
                abstract_text=body)


def parse_jmih_a4_blocks(text: str):
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
                if t and not _SESSION_NOTE.match(t):
                    body.append(t)
                i += 1
            parsed = _make_abstract(header, body)
            if parsed:
                blocks.append(parsed)
            header = []
        else:
            if s and not _SESSION_NOTE.match(s):
                header.append(s)
            # keep header from growing unbounded across schedule noise
            if len(header) > 8:
                header = header[-4:]
            i += 1
    return blocks


def ingest_jmih_a4(con, text, meeting_meta):
    """Parse an OCR'd A4 book and insert abstracts (best-effort; authors are
    OCR-mangled so all get needs_review). Returns count."""
    from conf_abstracts import load, extract, tag
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    meta.setdefault("is_ocr", 1)
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_jmih_a4_blocks(text):
        rec = extract.extract_fields(
            dict(program_number=None, session_line="",
                 author_raw=b["author_raw"], title=b["title"],
                 abstract_text=b["abstract_text"]),
            meta["meeting"], fmt="asih_book", use_llm=False)
        rec["keywords"] = None
        if b.get("affiliation") and rec["authors"]:
            rec["authors"][0]["affiliation"] = b["affiliation"]
        rec = tag.resolve(rec, meta["meeting"])
        if rec.get("_llm_is_elasmo") and not rec["is_elasmo"]:
            rec["is_elasmo"] = 1
            rec["elasmo_basis"] = "content"
        rec["needs_review"] = 1          # OCR'd source: always review
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
