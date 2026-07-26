"""Classify a programme PDF into meeting / year / doc_type from its filename."""
import re
import subprocess
from pathlib import Path

_YEAR = re.compile(r"(19|20)\d{2}")


def _meeting(name: str) -> str:
    up = name.upper()
    if "JMIH" in up:
        return "JMIH"
    if "ASIH" in up:
        return "ASIH"
    if re.search(r"\bSI\d{2,4}\b", up) or "SHARKS_INTERNATIONAL" in up or "SHARKS INTERNATIONAL" in up:
        return "SI"
    if "EEA" in up:
        return "EEA"
    return "JMIH"  # Carylanne set is JMIH-dominant; fall back to JMIH


def _doc_type(name: str) -> str:
    low = name.lower()
    if "abstract" in low:
        return "abstract_book"
    if "poster" in low:
        return "poster_list"
    if "plenary" in low:
        return "plenary"
    if "session" in low or "symposia" in low or "symposium" in low:
        return "sessions_symposia"
    return "program_book"


def classify_from_name(name: str):
    """Pure-name classification -> (meeting, year, doc_type)."""
    base = Path(name).name
    m = _YEAR.search(base)
    year = int(m.group(0)) if m else None
    return _meeting(base), year, _doc_type(base)


def classify_pdf(path, is_ocr: bool = False) -> dict:
    """Full classification incl. page_count via pdfinfo."""
    path = Path(path)
    meeting, year, doc_type = classify_from_name(path.name)
    page_count = None
    try:
        out = subprocess.run(["pdfinfo", str(path)], capture_output=True,
                             timeout=60).stdout.decode("utf-8", "replace")
        mm = re.search(r"^Pages:\s+(\d+)", out, re.M)
        if mm:
            page_count = int(mm.group(1))
    except Exception:
        pass
    return dict(meeting=meeting, year=year, doc_type=doc_type,
                page_count=page_count, is_ocr=int(is_ocr),
                source_pdf=str(path))
