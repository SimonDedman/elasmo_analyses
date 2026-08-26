"""Shared configuration for the conference-abstracts pipeline."""
from pathlib import Path

# Repo root = three levels up from this file (scripts/conf_abstracts/config.py)
REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "database" / "conference_abstracts.db"
# Conference programme/abstract books live in the PDF library, one folder per
# year, named YYYY_<Conf>_<Type>[_qualifier].pdf (migrated 2026-08-25 from the
# partner inbox folders under database/others_libraries/, which remain the
# drop zones: new files land there, get renamed, and are copied here).
CONFERENCES = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/Conferences")
CARYLANNE = REPO / "database" / "others_libraries" / "Carylanne"
DIGITISED = CARYLANNE / "Digitised Programs"      # legacy inbox (still swept for new files)
UNDIGITISED = CARYLANNE / "Undigitised Programs"  # legacy inbox
# Files the segmenter must not touch: phone-scan books are ingested from
# outputs/a4_text/ by parse_jmih_a4; Copeia meeting summaries hold no abstracts.
SKIP_NAME_FRAGMENTS = ("_phonescan", "CopeiaMeetingSummary")
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
    ("SI", 2026): str(CONFERENCES / "2026" / "2026_SI_ConferenceProgramme.xlsx"),
}

# SI abstract-book PDFs with a dedicated parser, keyed by a filename substring.
# value = (meeting, year, parser_module). The 2018 (Joao Pessoa) book has no
# year in its filename, so it's matched here.
SI_PDF_PARSERS = {
    "2018_SI_AbstractBook": ("SI", 2018, "parse_si2018_pdf"),
}

# JMIH/ASIH abstract books in the 'A2' format (author-block delimited, no
# separators/ids/Keywords). Keyed by filename fragment -> (meeting, year).
A2_FILES = {
    "2012_JMIH_AbstractBook": ("JMIH", 2012),
}

# A3-format books (number + UPPERCASE authors + initial-keyed affils). The 2005
# book has underscore separators; the OCR'd 1997-2004 books (schedule-heavy,
# multi-column) parse poorly and are handled best-effort from a4_text/.
A3_FILES = {
    "2005_JMIH_AbstractBook": ("JMIH", 2005),
}

# Modern program/schedule books ("N.N | Title" format, no abstract bodies).
# Only 2024/2025 use this cleanly; 2021-2023 and the older grid-matrix books
# (2006-2019) use other layouts and are not yet handled.
PROGRAM_BOOK_FILES = {
    "2021_JMIH_ProgrammeBook": ("JMIH", 2021),   # time-delimited (no N.N|)
    "2022_JMIH_ProgrammeBook": ("JMIH", 2022),
    "2023_JMIH_ProgrammeBook": ("JMIH", 2023),
    "2024_JMIH_ProgrammeBook": ("JMIH", 2024),  # "N.N | Title"
    "2025_JMIH_ProgrammeBook": ("JMIH", 2025),
    "2026_JMIH_ProgrammeBook": ("JMIH", 2026),  # Whova export: "N.N: Title" + "Speaker:"
}

# SI2026 PDF supplies the abstract bodies the xlsx lacks (merged by A-#### id).
SI2026_BODY_PDF = str(CONFERENCES / "2026" / "2026_SI_AbstractBook.pdf")

# Marine Google calendar for milestone/failure markers.
MARINE_CALENDAR_ID = "oa9mb0k12rkfsdsm9752bsahsc@group.calendar.google.com"
