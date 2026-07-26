"""Insert meetings/abstracts/authors into SQLite, with dedup."""
import re

_WS = re.compile(r"\s+")


def _norm_title(t: str) -> str:
    return _WS.sub(" ", (t or "").strip().lower())


def upsert_meeting(con, meta: dict) -> int:
    """Insert a meeting (or return existing id by source_pdf)."""
    cur = con.execute("SELECT meeting_id FROM meetings WHERE source_pdf=?",
                      (meta.get("source_pdf"),))
    row = cur.fetchone()
    if row:
        return row[0]
    cols = ["meeting", "year", "name", "location", "dates", "source_pdf",
            "doc_type", "page_count", "is_ocr", "parse_status"]
    vals = [meta.get(c) for c in cols]
    cur = con.execute(
        f"INSERT INTO meetings ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
        vals)
    con.commit()
    return cur.lastrowid


def _is_dup(con, meeting_id, record) -> bool:
    pn = record.get("program_number")
    if pn:
        r = con.execute(
            "SELECT 1 FROM abstracts WHERE meeting_id=? AND program_number=?",
            (meeting_id, pn)).fetchone()
        if r:
            return True
    nt = _norm_title(record.get("title"))
    if nt:
        r = con.execute(
            "SELECT 1 FROM abstracts WHERE meeting_id=? AND lower(trim(title))=?",
            (meeting_id, nt)).fetchone()
        if r:
            return True
    return False


def insert_abstract(con, meeting_id: int, record: dict):
    """Insert one abstract + its authors. Returns abstract_id, or None if dup."""
    if _is_dup(con, meeting_id, record):
        return None
    societies = record.get("societies_explicit")
    if isinstance(societies, list):
        societies = ",".join(societies) if societies else None
    text = record.get("abstract_text") or ""
    cols = dict(
        meeting_id=meeting_id,
        program_number=record.get("program_number"),
        title=record.get("title"),
        presentation_type=record.get("presentation_type"),
        session_name=record.get("session_name"),
        societies_explicit=societies,
        award=record.get("award"),
        society_inferred=record.get("society_inferred"),
        society=record.get("society"),
        society_basis=record.get("society_basis"),
        session_datetime=record.get("session_datetime"),
        location=record.get("location"),
        abstract_text=record.get("abstract_text"),
        length_words=len(text.split()) if text else 0,
        is_elasmo=record.get("is_elasmo", 0),
        elasmo_basis=record.get("elasmo_basis"),
        confidence=record.get("confidence"),
        needs_review=record.get("needs_review", 0),
        source_page=record.get("source_page"),
    )
    keys = list(cols)
    cur = con.execute(
        f"INSERT INTO abstracts ({','.join(keys)}) VALUES ({','.join('?'*len(keys))})",
        [cols[k] for k in keys])
    aid = cur.lastrowid
    for i, a in enumerate(record.get("authors") or [], start=1):
        con.execute(
            "INSERT INTO authors (abstract_id, full_name, position, is_presenter, "
            "presenter_inferred, affiliation, affiliation_country, raw_author_string) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (aid, a.get("full_name"), a.get("position", i),
             int(a.get("is_presenter", 0)), int(a.get("presenter_inferred", 0)),
             a.get("affiliation"), a.get("affiliation_country"),
             a.get("raw_author_string")))
    con.commit()
    return aid
