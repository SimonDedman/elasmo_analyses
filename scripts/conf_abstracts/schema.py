"""SQLite schema for the conference-abstracts database."""
import sqlite3
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS meetings (
    meeting_id   INTEGER PRIMARY KEY,
    meeting      TEXT,        -- JMIH / ASIH / SI / EEA
    year         INTEGER,
    name         TEXT,
    location     TEXT,
    dates        TEXT,
    source_pdf   TEXT UNIQUE,
    doc_type     TEXT,        -- program_book / abstract_book / poster_list / plenary / sessions_symposia
    page_count   INTEGER,
    is_ocr       INTEGER DEFAULT 0,
    parse_status TEXT,        -- ok / partial / failed
    n_abstracts  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS abstracts (
    abstract_id        INTEGER PRIMARY KEY,
    meeting_id         INTEGER REFERENCES meetings(meeting_id),
    program_number     TEXT,
    title              TEXT,
    presentation_type  TEXT,
    session_name       TEXT,
    societies_explicit TEXT,   -- e.g. "AES" or "HL,ASIH,SSAR" or NULL
    award              TEXT,
    society_inferred   TEXT,
    society            TEXT,    -- resolved
    society_basis      TEXT,    -- session_prefix / award / content
    session_datetime   TEXT,
    location           TEXT,
    abstract_text      TEXT,
    length_words       INTEGER,
    is_elasmo          INTEGER DEFAULT 0,
    elasmo_basis       TEXT,    -- session_prefix / award / meeting / content
    confidence         REAL,
    needs_review       INTEGER DEFAULT 0,
    source_page        INTEGER
);

CREATE TABLE IF NOT EXISTS authors (
    author_id          INTEGER PRIMARY KEY,
    abstract_id        INTEGER REFERENCES abstracts(abstract_id),
    full_name          TEXT,
    position           INTEGER,
    is_presenter       INTEGER DEFAULT 0,
    presenter_inferred INTEGER DEFAULT 0,
    affiliation        TEXT,
    affiliation_country TEXT,
    raw_author_string  TEXT
);

CREATE INDEX IF NOT EXISTS idx_abstracts_meeting ON abstracts(meeting_id);
CREATE INDEX IF NOT EXISTS idx_abstracts_elasmo  ON abstracts(is_elasmo);
CREATE INDEX IF NOT EXISTS idx_authors_abstract  ON authors(abstract_id);
"""


def create_db(path) -> sqlite3.Connection:
    """Create (if needed) and open the abstracts DB, returning the connection."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.executescript(DDL)
    con.commit()
    return con
