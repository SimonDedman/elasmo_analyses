"""Parser for the 'A2' JMIH/ASIH abstract-book format (e.g. JMIH-Abstracts-2012).

No IDs, no session headers, no underscore separators, no Keywords. Each abstract
is delimited by its author block:
    Surname, First (Affiliation); Surname, First (Affiliation, Country)   <- authors
    <Title, Title Case, may span 2 lines>
    <abstract body prose>
A new abstract starts at an author-block line that FOLLOWS a body line.
"""
import re

from conf_abstracts.segment import _title_like, _AFFIL_KW
from conf_abstracts.parse_si2018_pdf import _is_prose

# "Surname, First" at line start (surname capitalised; first name any case)
_AUTHOR_START = re.compile(r"^[A-ZÀ-Þ][\w'’À-ÿ.\-]+,\s+\w")
_COUNTRY = re.compile(
    r"\b(United States|United Kingdom|USA|UK|Canada|Australia|China|Brazil|"
    r"Mexico|Germany|Japan|France|Spain|Italy|India|Argentina|Colombia)\b", re.I)
_INITIAL_AFFIL = re.compile(r"^\([A-Z]{2,},?\s*[A-Z, ]*\)")   # "(ABC, PJM) University..."


def _is_author_start(s: str) -> bool:
    return bool(_AUTHOR_START.match(s)) and ("(" in s or ";" in s)


def _is_author_or_affil(s: str) -> bool:
    """Author line, or an affiliation continuation line."""
    if _is_author_start(s):
        return True
    if _AFFIL_KW.search(s) or _COUNTRY.search(s) or _INITIAL_AFFIL.match(s):
        return True
    # short line closing an affiliation paren, e.g. "Canada)" / "United States)"
    if s.endswith(")") and len(s) < 55 and not _is_prose(s):
        return True
    return False


def _parse_block(block_lines):
    lines = [l.strip() for l in block_lines if l.strip()]
    if len(lines) < 3:
        return None
    # title = first title-like line that is not an author/affiliation line
    ti = None
    for i, s in enumerate(lines):
        if i == 0 or _is_author_or_affil(s):
            continue
        if _title_like(s) and not _is_prose(s):
            ti = i
            break
    if ti is None:
        return None
    author_raw = " ".join(lines[:ti]).strip()
    # body = first prose line at/after the title onward
    bstart = next((k for k in range(ti, len(lines)) if _is_prose(lines[k])), None)
    if bstart is None or bstart == ti:
        # title present but no clear prose; take everything after title as body
        bstart = ti + 1
    title = " ".join(lines[ti:bstart]).strip()
    body = " ".join(lines[bstart:]).strip()
    body = re.sub(r"\s{2,}", " ", body)
    if not body or len(body.split()) < 40:
        return None
    return dict(author_raw=author_raw, title=title or None,
                abstract_text=body or None)


def parse_jmih_a2_blocks(text: str):
    lines = text.splitlines()
    # Run-based: consecutive author/affiliation lines form one author block; only
    # the FIRST author line of each run starts an abstract (co-authors don't).
    starts = []
    in_run = False
    for i, l in enumerate(lines):
        s = l.strip()
        if not s:
            continue
        if _is_author_start(s) and not in_run:
            starts.append(i)
        in_run = _is_author_or_affil(s)
    blocks = []
    for j, st in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(lines)
        parsed = _parse_block(lines[st:end])
        if parsed:
            blocks.append(parsed)
    return blocks


def ingest_jmih_a2(con, pdf_text, meeting_meta):
    """Parse an A2-format abstract book and insert abstracts. Society/elasmo left
    to the caller's tagging (JMIH is multi-society); here we tag via lexicon +
    default. Returns count."""
    from conf_abstracts import load, extract, tag
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_jmih_a2_blocks(pdf_text):
        rec = extract.extract_fields(
            dict(program_number=None, session_line="",
                 author_raw=b["author_raw"], title=b["title"],
                 abstract_text=b["abstract_text"]),
            meta["meeting"], fmt="asih_book", use_llm=False)
        rec["keywords"] = None
        rec = tag.resolve(rec, meta["meeting"])
        if rec.get("_llm_is_elasmo") and not rec["is_elasmo"]:
            rec["is_elasmo"] = 1
            rec["elasmo_basis"] = "content"
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
