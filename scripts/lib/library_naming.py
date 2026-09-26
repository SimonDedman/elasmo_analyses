"""One definition of a library PDF's name.

    <first author>[.etal].<year>.<title, 60 chars>[ (lit <id>)].pdf     in <year>/

WHY THIS IS A MODULE
--------------------
The name is not decoration: `build_pdf_id_map.py` regenerates it from each record
to work out which file belongs to which paper, so the ingester and the map have to
agree letter for letter. They were separate copies (`ingest_pdfs.build_filename`,
`sync_shark_references.build_pdf_path`), which is how they drifted.

THE COLLISION THIS FIXES (measured 2026-09-25)
----------------------------------------------
Truncating the title at 60 characters throws away exactly the part that
distinguishes a series:

    12403  Preservative Experiment of the Smoked Shark-Fillet.
    12404  Preservative Experiment of Smoked Shark-Fillet. Part II. Change of oil...

Both produced `Yamamura.1951.Preservative Experiment of the Smoked Shark-Fillet..pdf`,
so filing the second would overwrite the first. 128 library files are claimed by two
or more records for this reason, covering 272 records.

Two changes:

* a part designator (Part II, No. VII, -IX-, II.) is preserved even when the
  truncation would drop it, because that is the only thing telling two papers apart;
* `disambiguate=True` appends ` (lit <id>)`, used when a different paper already
  holds the plain name. Readers try the plain name first and then the suffixed one,
  so nothing has to guess.
"""
from __future__ import annotations

import re
from pathlib import Path

PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
TITLE_LEN = 60

# "Part II", "Part 3", "No. VII", "- IX -", "Vol. 2", or a trailing roman numeral.
_PART = re.compile(
    r"\b(?:part|pt\.?|no\.?|number|vol\.?|volume)\s*[:.\-]?\s*([IVXLCDM]+|\d{1,3})\b"
    r"|\blong\s+dash\s+([IVXLCDM]+|\d{1,3})\b"
    r"|[-–—]\s*([IVXLCDM]{1,6}|\d{1,3})\s*[-–—.]"
    r"|\b([IVXLCDM]{1,6})\.\s*$",
    re.I,
)


def clean_for_filename(text: str, max_len: int = 50) -> str:
    if not text:
        return "Unknown"
    text = str(text).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"[\n\r\t]", " ", text)
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
    return text.strip() or "Unknown"


def extract_first_author(authors: str) -> str:
    if not authors:
        return "Unknown"
    authors = str(authors).strip()
    first = re.split(r"\s*&\s*", authors)[0].strip()
    first = re.sub(r"\(\d{4}\)", "", first).strip()
    if "," in first:
        return clean_for_filename(first.split(",")[0], max_len=20)
    parts = first.split()
    return clean_for_filename(parts[-1] if parts else "Unknown", max_len=20)


def part_designator(title: str) -> str:
    """'Part II' / 'No VII' / 'IX' from a series title, or '' when there is none."""
    m = _PART.search(str(title or ""))
    if not m:
        return ""
    num = next(g for g in m.groups() if g)
    word = m.group(0).strip(" -–—.")
    return re.sub(r"\s+", " ", word) if word.lower().startswith(("part", "pt", "no", "vol", "num")) else f"Part {num.upper()}"


def title_for_filename(title: str, max_len: int = TITLE_LEN) -> str:
    """The truncated title, with the series designator kept even if it fell off the end."""
    short = clean_for_filename(title, max_len=max_len)
    part = part_designator(title)
    if part:
        # the cut can leave the designator's first word dangling ("...Museum. Part")
        short = re.sub(r"[\s.]*\b(?:part|pt|no|number|vol|volume)\.?\s*$", "", short, flags=re.I)
        if part.lower() not in short.lower():
            short = f"{short.rstrip('. ')}. {part}"
    return short


def year_str(year) -> str:
    try:
        return str(int(float(year)))
    except (TypeError, ValueError):
        return "Unknown"


def build_filename(record: dict, disambiguate: bool = False) -> str:
    author = extract_first_author(record.get("authors", ""))
    y = year_str(record.get("year"))
    title = title_for_filename(record.get("title", ""))
    etal = ".etal" if "&" in str(record.get("authors", "")) else ""
    lid = str(record.get("literature_id", "")).split(".")[0]
    suffix = f" (lit {lid})" if disambiguate and lid else ""
    return f"{author}{etal}.{y}.{title}{suffix}.pdf"


def build_pdf_path(record: dict, disambiguate: bool = False, base: Path = PDF_BASE) -> Path:
    return base / year_str(record.get("year")) / build_filename(record, disambiguate)


def candidate_names(record: dict) -> list[str]:
    """Both spellings, so a reader finds the file whether or not it was disambiguated."""
    return [build_filename(record, False), build_filename(record, True)]


def free_path(record: dict, taken=lambda p: p.exists(), base: Path = PDF_BASE) -> Path:
    """The path to file this record at: the plain one, or the disambiguated one when
    the plain name is already another paper's."""
    plain = build_pdf_path(record, False, base)
    return plain if not taken(plain) else build_pdf_path(record, True, base)
