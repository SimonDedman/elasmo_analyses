"""Field + author extraction: turn a raw block into a full abstract record.

Rules do the structural work; the LLM (Ollama) infers society/elasmo only when
no explicit society signal is present.
"""
import re

from conf_abstracts import llm
from conf_abstracts.sessions import parse_session_line

_TRAIL_DIGITS = re.compile(r"[\d\*†‡,;]+$")
_LEAD_DIGITS = re.compile(r"^\d+")


def _clean_name(n: str) -> str:
    n = n.strip().strip(",")
    n = _TRAIL_DIGITS.sub("", n).strip()
    return re.sub(r"\s+", " ", n)


def parse_authors(raw: str):
    """Parse an author string. Handles 'Surname, First; ...' and
    'First Last<superscript>, ...' forms. Returns list of author dicts."""
    raw = (raw or "").strip()
    if not raw:
        return []
    authors = []
    if ";" in raw:  # ASIH "Surname, First; Surname, First"
        for part in raw.split(";"):
            part = part.strip()
            if not part:
                continue
            if "," in part:
                surname, first = part.split(",", 1)
                name = f"{_clean_name(first)} {_clean_name(surname)}".strip()
            else:
                name = _clean_name(part)
            authors.append(name)
    else:  # "First Last1, First Last2, ..."
        for part in raw.split(","):
            part = _clean_name(part)
            if part and not part.isdigit() and len(part) > 1:
                authors.append(part)
    out = []
    for i, name in enumerate(authors, 1):
        if not name:
            continue
        out.append(dict(full_name=name, position=i,
                        is_presenter=1 if i == 1 else 0,
                        presenter_inferred=1 if i == 1 else 0,
                        affiliation=None, affiliation_country=None,
                        raw_author_string=raw))
    return out


def extract_fields(block: dict, meeting: str, fmt: str = "jmih_book",
                   use_llm: bool = True) -> dict:
    """Merge session parse + authors into a full record. Sets confidence and
    needs_review; runs LLM society inference when no explicit society."""
    rec = dict(block)
    sess = parse_session_line(block.get("session_line", "") or "")
    rec.update(dict(
        session_name=sess["session_name"],
        societies_explicit=sess["societies_explicit"],
        award=sess["award"],
        presentation_type=sess["presentation_type"],
        session_datetime=sess["session_datetime"],
        location=sess["location"],
    ))
    rec["authors"] = parse_authors(block.get("author_raw", ""))
    rec["society_inferred"] = None

    title = rec.get("title") or ""
    body = rec.get("abstract_text") or ""

    # confidence heuristic
    conf = 1.0
    if not title:
        conf -= 0.4
    if not body or len(body.split()) < 20:
        conf -= 0.3
    if not rec["authors"]:
        conf -= 0.2
    rec["confidence"] = round(max(conf, 0.0), 2)
    rec["needs_review"] = 1 if conf < 0.7 else 0

    # LLM society inference only when structure gave no society and we have text
    if use_llm and not rec["societies_explicit"] and title and body \
            and meeting not in ("SI", "EEA"):
        got = llm.infer_society(title, body)
        if got:
            rec["society_inferred"] = got.get("society")
            rec["_llm_is_elasmo"] = got.get("is_elasmo")
            if got.get("confidence"):
                rec["confidence"] = round(min(rec["confidence"] or 1.0,
                                              0.5 + got["confidence"] / 2), 2)
    return rec
