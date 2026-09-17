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

# Books a deterministic parser already covers, so conf_fable_prep must not queue
# a Fable agent for them. Keyed by worklist key -> why. Unlike
# SKIP_NAME_FRAGMENTS this does NOT stop run_pipeline parsing the PDF; it is
# only about not paying for an LLM pass over a book that is already solved.
FABLE_SKIP_KEYS = {
    "OCS2016": "parse_ocs_numbered.py: 222/222 against the book's own numbering",
    "OCS2020": "parse_ocs_labelled.py: 44/44 blocks, 42 complete",
    "OCS2022": "parse_ocs_labelled.py: 30/30 blocks, 25 complete",
    "OCS2025": "parse_ocs_labelled.py: 94/94 blocks, 94 complete",
    "JMIH2026": "parse_jmih_a5.py: 1,051 records, 1,048 with bodies — the "
                "born-digital book needs no LLM",
}

# General-ichthyology volumes where Fable reads only the elasmobranch pages.
# The two IPFC books were 20 of the 47 queued OCS/IPFC chunks and are mostly
# teleost (32% and 17.5% of their pages so much as name an elasmobranch), so
# they are screened page-by-page first (prescan_elasmo_pages.py) and the pages
# with no mention are never sent. before=0/after=1 keeps the page AFTER a hit,
# which protects a body running over the page break; the page BEFORE is not
# needed, because in both controls (OCS2016 n=66, JMIH2016 n=226) the mention
# was always on the same page as the title. MEASURED recall at this setting:
# 100% on both. The cost is real and must be stated wherever these are
# reported: the teleost abstracts in these two volumes are NOT captured, so
# they are "elasmo-targeted", never "Ingested".
ELASMO_TARGETED_BOOKS = {
    # skip_pages drops front matter that names elasmobranchs without being about
    # them. IPFC 2009 pages 1-6 are a contents listing of every talk in the
    # book; keeping them cost 356 of its 416 records, which came back as
    # title+authors with no body because the agents read the LISTING.
    "IPFC2009": dict(before=0, after=1, skip_pages=tuple(range(1, 7))),
    "IPFC2023": dict(before=0, after=1),
}
OCR_SCRATCH = Path("/media/simon/data/ocr_scratch")
LOG = REPO / "logs" / "conf_abstracts.log"
OUT = REPO / "outputs"

# Societies. AES is the elasmobranch one.
SOCIETIES = {"AES", "ASIH", "HL", "SSAR", "NIA", "SI", "EEA"}
ELASMO_SOCIETIES = {"AES"}
# meetings that are wholly elasmo regardless of session
# OCS is the Oceania Chondrichthyan Society: every talk is elasmo, so the
# meeting is tagged wholesale rather than per-session (added 2026-09-06 with
# Brit's 18-book donation).
# SOMEPEC (Sociedad Mexicana de Peces Cartilaginosos) is wholly elasmo;
# approved series 2026-09-17. It is NOT a joint meeting, so the blanket rule
# applies (the JOINT_MEETINGS carve-out below is only for OCS's joint years).
# Added because conf_fable_prep.py already declares SOMEPEC with
# is_elasmo_meeting=True, which makes conf_fable_merge SKIP the per-abstract
# lexicon fallback, while its absence from this set meant tag.resolve() never
# set the flag either: all 322 SOMEPEC abstracts landed is_elasmo=0. The two
# lists must agree, and this set is the one tag.resolve() reads.
ELASMO_MEETINGS = {"SI", "EEA", "OCS", "SOMEPEC"}

# OCS years that were JOINT meetings with a general fish or marine-science
# society, where the book is mostly teleost work and the blanket
# meeting-level elasmo rule would be wrong. Measured from the books
# themselves: 2012 names ASFB 86 times, 2015 NZMSS 229, 2019 NZMSS 94, and
# 2016 (Hobart, Sept 2016) never names OCS at all and opens on a fish-otolith
# plenary. In these, is_elasmo comes from the lexicon, per abstract.
JOINT_MEETINGS = {("OCS", 2012), ("OCS", 2015), ("OCS", 2016), ("OCS", 2019)}

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

# Born-digital JMIH abstract books exported straight from the submission system
# ("presenting author / authors / <type> ** <keywords> / N.N: Title / [id] body").
# The richest JMIH source there is, and no LLM needed. See parse_jmih_a5.py.
A5_FILES = {
    "2026_JMIH_AbstractBook": ("JMIH", 2026),
}

# Numbered born-digital OCS abstract books: a centred sequential number opens
# each abstract, then title / authors / numbered affiliations / body. The
# numbering is its own QA instrument. See parse_ocs_numbered.py.
OCS_NUMBERED_FILES = {
    "2016_OCS_AbstractBook": ("OCS", 2016),
}

# OCS books that print an "Abstract" label above each body: the label count is
# the book's own answer for how many abstracts it holds, and it is exact (44 in
# 2020, 30 in 2022, 94 in 2025, the last matched by 94 "Presented by:" lines).
# See parse_ocs_labelled.py. NOT here: 2024, whose pages have no label and no
# number — the rules reach 53 of its 74 abstracts and leak wrapped affiliations
# into bodies, so it stays with Fable.
OCS_LABELLED_FILES = {
    "2020_OCS_AbstractBook": ("OCS", 2020),
    "2022_OCS_AbstractBook": ("OCS", 2022),
    "2025_OCS_AbstractBook": ("OCS", 2025),
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

# JMIH Oxford Abstracts submission exports (xlsx). JMIH pays Oxford Abstracts
# for the submission site, so the programme officer can export every submitted
# abstract with title/authors/body/keywords/type/membership/career stage. These
# supersede the programme book for the same year (see ingest_oa_xlsx.py).
# Source: David M. Green (JMIH programme officer), first file 2026-09-04.
OA_XLSX_SOURCES = {
    ("JMIH", 2021): str(CONFERENCES / "2021" / "2021_JMIH_AbstractExport.xlsx"),
    ("JMIH", 2022): str(CONFERENCES / "2022" / "2022_JMIH_AbstractExport.xlsx"),
    ("JMIH", 2025): str(CONFERENCES / "2025" / "2025_JMIH_AbstractExport.xlsx"),
}
OA_MEETING_NAMES = {
    ("JMIH", 2021): "Joint Meeting of Ichthyologists and Herpetologists 2021",
    ("JMIH", 2022): "Joint Meeting of Ichthyologists and Herpetologists 2022",
    ("JMIH", 2025): "Joint Meeting of Ichthyologists and Herpetologists 2025",
}
OA_MEETING_CITIES = {
    ("JMIH", 2021): "Phoenix, AZ",
    ("JMIH", 2022): "Spokane, WA",   # from the 2022 programme book cover
    ("JMIH", 2025): "St. Paul, MN",   # matches the programme-book meeting row
}

# Host city per (meeting, year) for series whose books do not carry the venue in
# a parseable place. These come from the FILENAMES Brit supplied with the books
# themselves ("2009_IPFC Fremantle Abstract Book.pdf"), which is the donor's own
# record of where the meeting was, so they are cited rather than inferred.
MEETING_CITIES = {
    ("OCS", 2007): "Queenscliff, VIC, Australia",
    ("OCS", 2008): "Sydney, NSW, Australia",
    ("OCS", 2011): "Gold Coast, QLD, Australia",
    ("OCS", 2012): "Adelaide, SA, Australia",          # joint with ASFB
    ("OCS", 2013): "Brisbane, QLD, Australia",
    ("OCS", 2015): "Auckland, New Zealand",            # joint with NZMSS
    ("OCS", 2016): "Wrest Point, Tasmania, Australia",  # joint with ASFB
    ("OCS", 2018): "Moreton Bay, QLD, Australia",
    ("OCS", 2019): "Dunedin, New Zealand",             # joint with NZMSS
    ("OCS", 2020): "Virtual",
    ("OCS", 2022): "Virtual",
    ("OCS", 2024): "Geelong, VIC, Australia",
    ("OCS", 2025): "Sunshine Coast, QLD, Australia",
    ("IPFC", 2009): "Fremantle, WA, Australia",
    ("IPFC", 2023): "Auckland, New Zealand",
    ("SQERF", 2005): "Moreton Bay, QLD, Australia",
}

# SI2026 PDF supplies the abstract bodies the xlsx lacks (merged by A-#### id).
SI2026_BODY_PDF = str(CONFERENCES / "2026" / "2026_SI_AbstractBook.pdf")

# Marine Google calendar for milestone/failure markers.
MARINE_CALENDAR_ID = "oa9mb0k12rkfsdsm9752bsahsc@group.calendar.google.com"


# ---------------------------------------------------------------------------
# Multi-column scanned books.
#
# `pdftotext -layout` on a two-column page puts BOTH columns on each output
# line, interleaving two unrelated abstracts; `pdf_columns.extract` slices the
# page into column strips instead, giving true reading order (column 1 top to
# bottom, then column 2) and ~1/3 fewer characters (no gutter padding).
#
# Opt-in per book key: re-extracting an already Fable-cached book would change
# its source text, invalidate the cache and re-chunk it.
#   key -> dict(pages=(first, last), gutters=[x, ...] | None)
#   gutters=None detects the columns per page (use for books with a variable
#   page crop); a fixed list pins them (faster, and right for uniform books).
COLUMN_BOOKS = {
    # Carylanne's flatbed rescan of JMIH 1998 Guelph, received 2026-08-28,
    # replacing the unusable phone-photo scan. Pages 1-19 are the schedule grid
    # (3-4 columns, per-page crop) and 130-134 the author index; only pages
    # 20-129 carry abstract bodies. Gutter MEASURED at x=384 — 31 of 178,318
    # word boxes cross it (0.017%).
    "JMIH1998": dict(pages=(20, 129), gutters=[384]),
}
