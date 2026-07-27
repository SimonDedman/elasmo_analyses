"""Shared configuration for the conference-abstracts pipeline."""
from pathlib import Path

# Repo root = three levels up from this file (scripts/conf_abstracts/config.py)
REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "database" / "conference_abstracts.db"
CARYLANNE = REPO / "database" / "others_libraries" / "Carylanne"
DIGITISED = CARYLANNE / "Digitised Programs"
UNDIGITISED = CARYLANNE / "Undigitised Programs"
OCR_SCRATCH = Path("/media/simon/data/ocr_scratch")
LOG = REPO / "logs" / "conf_abstracts.log"
OUT = REPO / "outputs"

# Societies. AES is the elasmobranch one.
SOCIETIES = {"AES", "ASIH", "HL", "SSAR", "NIA", "SI", "EEA"}
ELASMO_SOCIETIES = {"AES"}
# meetings that are wholly elasmo regardless of session
ELASMO_MEETINGS = {"SI", "EEA"}

# Normalise society tokens seen in session lines.
SOCIETY_ALIASES = {
    "AES": "AES", "ASIH": "ASIH", "HL": "HL", "SSAR": "SSAR", "NIA": "NIA",
    "SI": "SI", "EEA": "EEA",
}

PRESENTATION_TYPES = {
    "talk", "poster", "lightning", "symposium", "plenary", "keynote",
}

# Text-quality thresholds (from the 2026-07-24 pdftotext quality pass).
ALPHA_MIN = 200
DENSITY_MIN = 0.45

# Ollama (user-local install, port 11435, per docs/LLM/rag_prototype_status.md)
OLLAMA_HOST = "http://127.0.0.1:11435"
OLLAMA_MODEL = "qwen2.5:3b-instruct"

# Structured (xlsx) sources for conferences that ship a spreadsheet programme
# rather than a parseable abstract-book PDF. Keyed by (meeting, year).
# SI programmes are structured; reuse them instead of PDF segmentation.
SI_SOURCES = {
    ("SI", 2026): "/media/simon/data/Documents/Si Work/PostDoc Work/SI/"
                  "2026 Sri Lanka/Sessions info/SI2026_Conference_Programme.xlsx",
}

# SI abstract-book PDFs with a dedicated parser, keyed by a filename substring.
# value = (meeting, year, parser_module). The 2018 (Joao Pessoa) book has no
# year in its filename, so it's matched here.
SI_PDF_PARSERS = {
    "Sharks_International_Conference-Abstract_Book_2": ("SI", 2018, "parse_si2018_pdf"),
}

# JMIH/ASIH abstract books in the 'A2' format (author-block delimited, no
# separators/ids/Keywords). Keyed by filename fragment -> (meeting, year).
A2_FILES = {
    "JMIH-Abstracts-2012": ("JMIH", 2012),
}

# A3-format books (number + UPPERCASE authors + initial-keyed affils). The 2005
# book has underscore separators; the OCR'd 1997-2004 books (schedule-heavy,
# multi-column) parse poorly and are handled best-effort from a4_text/.
A3_FILES = {
    "2005-JMIH-Abstract-Book": ("JMIH", 2005),
}

# Modern program/schedule books ("N.N | Title" format, no abstract bodies).
# Only 2024/2025 use this cleanly; 2021-2023 and the older grid-matrix books
# (2006-2019) use other layouts and are not yet handled.
PROGRAM_BOOK_FILES = {
    "2021_JMIH_ConferenceProgram": ("JMIH", 2021),   # time-delimited (no N.N|)
    "2022_JMIH_Conference_Program": ("JMIH", 2022),
    "2023_JMIH_Conference_Program": ("JMIH", 2023),
    "2024_JMIH_Conference_Program": ("JMIH", 2024),  # "N.N | Title"
    "2025_JMIH_Conference_Program": ("JMIH", 2025),
}

# SI2026 PDF supplies the abstract bodies the xlsx lacks (merged by A-#### id).
SI2026_BODY_PDF = ("/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/"
                   "database/others_libraries/Carylanne/Digitised Programs/"
                   "SI2026 - Abstract Book (29th April 2026).pdf")

# Marine Google calendar for milestone/failure markers.
MARINE_CALENDAR_ID = "oa9mb0k12rkfsdsm9752bsahsc@group.calendar.google.com"
