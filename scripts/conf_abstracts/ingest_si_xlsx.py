"""Ingest a Sharks International structured programme XLSX into the abstracts DB.

SI programmes ship as a spreadsheet (not a PDF to parse). The SI2026 file has an
'Abstracts' sheet: Abstract ID, Title, Presenting Author, Corresponding Author,
Email, Session, Talk Type, Authors & Affiliations, Keywords. All SI records are
elasmo (society=AES, elasmo_basis=meeting). No abstract body column exists, so
abstract_text stays null; keywords are captured.

Reuses the approach proven in Shark Network's R/02_ingest_si2026.R (reads the
Abstracts sheet, parses 'Authors & Affiliations', marks the presenting author).
"""
import re

import pandas as pd

from conf_abstracts import load

# Talk Type -> presentation_type
_TYPE_MAP = {
    "regular talk": "talk",
    "speed talk": "lightning",
    "poster": "poster",
    "panel": "talk",
    "keynote": "keynote",
    "plenary": "plenary",
}


def _norm(s):
    return re.sub(r"[^a-z]", "", str(s).lower())


def parse_si_authors(raw: str, presenter: str = None):
    """Parse 'Name (affil); Name (affil); ...' into author dicts, marking the
    presenting author."""
    raw = "" if raw is None else str(raw).strip()
    if not raw or raw.lower() == "nan":
        authors = []
    else:
        # split between entries at ");" boundaries
        parts = re.split(r"\)\s*;\s*", raw)
        authors = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            m = re.match(r"^(.*?)\s*\((.*?)\)?\s*$", p)
            if m:
                name, affil = m.group(1).strip(), m.group(2).strip() or None
            else:
                name, affil = p.strip(), None
            if name:
                authors.append((name, affil))
    pnorm = _norm(presenter) if presenter else None
    out = []
    presenter_set = False
    for i, (name, affil) in enumerate(authors, 1):
        is_pres = bool(pnorm and _norm(name) == pnorm)
        if is_pres:
            presenter_set = True
        out.append(dict(full_name=name, position=i,
                        is_presenter=1 if is_pres else 0,
                        presenter_inferred=0,
                        affiliation=affil, affiliation_country=None,
                        raw_author_string=raw))
    # if presenter named but not matched, and we have authors, add presenter first
    if presenter and not presenter_set:
        if out:
            out[0]["is_presenter"] = 1
            out[0]["presenter_inferred"] = 1
        else:
            out.append(dict(full_name=str(presenter).strip(), position=1,
                            is_presenter=1, presenter_inferred=1,
                            affiliation=None, affiliation_country=None,
                            raw_author_string=raw))
    return out


def ingest_si_xlsx(con, xlsx_path, meeting_meta: dict, sheet="Abstracts") -> int:
    """Insert all abstracts from the SI programme xlsx. meeting_meta must include
    meeting/year/source_pdf(=xlsx path). Returns inserted count."""
    df = pd.read_excel(xlsx_path, sheet_name=sheet)
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    n = 0
    for _, r in df.iterrows():
        title = r.get("Title")
        if pd.isna(title) or not str(title).strip():
            continue
        ttype = str(r.get("Talk Type") or "").strip().lower()
        rec = dict(
            program_number=(None if pd.isna(r.get("Abstract ID"))
                            else str(r.get("Abstract ID")).strip()),
            title=str(title).strip(),
            presentation_type=_TYPE_MAP.get(ttype, "talk"),
            session_name=(None if pd.isna(r.get("Session"))
                          else str(r.get("Session")).strip()),
            societies_explicit=None,
            award=None,
            society_inferred=None,
            society="AES",
            society_basis="meeting",
            session_datetime=None,
            location=None,
            abstract_text=None,
            keywords=(None if pd.isna(r.get("Keywords"))
                      else str(r.get("Keywords")).strip()),
            is_elasmo=1,
            elasmo_basis="meeting",
            confidence=1.0,
            needs_review=0,
            source_page=None,
            authors=parse_si_authors(r.get("Authors & Affiliations"),
                                     r.get("Presenting Author")),
        )
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
