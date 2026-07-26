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

# Marine Google calendar for milestone/failure markers.
MARINE_CALENDAR_ID = "oa9mb0k12rkfsdsm9752bsahsc@group.calendar.google.com"
