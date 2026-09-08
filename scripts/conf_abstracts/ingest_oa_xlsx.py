"""Ingest a JMIH Oxford Abstracts submission export (xlsx) into the abstracts DB.

JMIH pays Oxford Abstracts for its submission site, so from ~2021 the programme
officer can export every submitted abstract as a spreadsheet. David M. Green
(JMIH programme officer, McGill) supplied the JMIH 2021 export on 2026-09-04.
This is the cleanest source we have for any JMIH year: born-digital title,
author list, presenter flag, full body, four keywords, presentation type,
society membership, career stage, and (2022 on) a subject category. The columns
vary by year - 2022 drops "Job Status" and adds "Categories", and 2025 renames
most of them again, drops the keywords, and adds a taxonomic group and a common
name - so every field beyond title/authors/abstract is optional and resolved
from the header row. What it does NOT carry is affiliations, the
session name, or the day/time - and it reflects SUBMISSIONS, so cancellations
are still in and last-minute changes are not.

The programme book for the same year holds exactly what the export lacks
(session, society prefix, day/time) and nothing the export lacks. So
`merge_program_schedule()` copies the schedule fields onto the matching export
records and then drops the programme-book duplicates, leaving one row per talk
with both halves of the story.

Usage:
  ingest_oa_xlsx.py --year 2021                # ingest + merge schedule
  ingest_oa_xlsx.py --year 2021 --dry-run      # parse and report, write nothing
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts import lexicon, load, names  # noqa: E402
from conf_abstracts.merge_schedule import merge_program_schedule  # noqa: E402,F401

# Column headers as Oxford Abstracts writes them. Matched case-insensitively on
# the header row, so a year that renames "Job Status" -> "Career stage" needs
# only an alias added here.
_HEADERS = {
    "presenting": "presenter",
    "authors": "authors",
    "title": "title",
    "abstract": "abstract",
    "job status": "career_stage",
    "career stage": "career_stage",
    "membership": "membership",
    "herpetology or ichthyology": "discipline",
    "presentation": "presentation",
    "type of presentation": "presentation",
    "categories": "subject_category",
    "presentation subject": "subject_category",
    "membership:": "membership",
    "taxonomic information": "taxon_group",
    "common name": "common_name",
}
_KEYWORD_RE = re.compile(r"^keyword\s*\d+$", re.I)

# Presentation strings carry three things at once: the format, whether it is a
# student competition, and (in 2021 only) whether it was virtual. Match on
# keywords so later years' wording still routes.
_TYPE_RULES = [
    ("lightning", "lightning"),
    ("poster", "poster"),
    ("symposium", "symposium"),
    ("plenary", "plenary"),
    ("keynote", "keynote"),
    ("oral", "talk"),
    ("paper", "talk"),
]

# Oxford Abstracts writes a literal "N/A" where a submitter left an optional
# dropdown unset (177 of the 662 Categories cells in 2022). That is an absent
# value, not a category, so it must not reach the DB as a string.
_BLANK = {"", "n/a", "na", "none", "-", "not applicable"}


def _s(v):
    """Cell text, with the export's placeholders for 'unset' read as empty."""
    if v is None:
        return ""
    # 2025 submitters pasted from Word, so 26 titles and 250 bodies carry
    # non-breaking spaces. Left in, they defeat any plain-space comparison
    # against a programme book; other whitespace is untouched so bodies keep
    # their paragraphs.
    t = str(v).replace("\xa0", " ").strip()
    return "" if t.lower() in _BLANK else t


def _type_of(text):
    low = (text or "").lower()
    return next((t for n, t in _TYPE_RULES if n in low), None)


def _presentation_type(text):
    """From 2025 the field is 'Category: choice', and the category can be a MENU.

    'Contributed Oral, Lightning or Poster Presentation: Regular Oral
    Presentation (15 min)' names three formats before it names the one that was
    chosen, so reading the whole string in rule order calls all 379 contributed
    presentations lightning talks. When the part before the colon offers more
    than one format it is a menu and the answer is after the colon; when it
    offers one ('Student Competition Poster') that IS the answer, and the tail
    is the award. Pre-2025 exports have no colon and are read as before.
    """
    head, _, tail = (text or "").partition(":")
    if tail.strip() and len({t for n, t in _TYPE_RULES if n in head.lower()}) > 1:
        return _type_of(tail) or _type_of(head) or "talk"
    return _type_of(head) or _type_of(tail) or "talk"


def _tail(text):
    """The specific choice after the 2025 'Category: choice' prefix, if any."""
    head, sep, tail = (text or "").partition(":")
    return tail.strip() if sep and tail.strip() else ""


def _award(text):
    """The competition name, if this is a student competition entry.

    2021/2022 name only the competition class ('Student Oral Competition');
    2025 names the actual award after the colon ('Student Competition Poster:
    AES Carrier Award'), which is the more useful half."""
    if "competition" not in (text or "").lower():
        return None
    return _tail(text) or re.sub(
        r"\s*\((?:all are )?virtual\)|\s+(?:IN-PERSON|VIRTUAL)\s*$", "", text).strip()


def _session(text):
    """2025 names the symposium or plenary after the colon; that is a session,
    and the programme book is the only other place it is recorded."""
    low = (text or "").lower()
    return _tail(text) or None if ("symposium" in low or "plenary" in low) else None


# A fragment that is nothing but initials ("G. B.", "T. M.", "V.") is the tail
# of a "Surname, Initials" name that the comma split cut in half.
_INITIALS_ONLY = re.compile(r"^(?:[A-Z]\.?\s*){1,3}$")


def _split_authors(raw, presenter):
    """'First Last, First Last, ...' -> author dicts, presenter flagged.

    Oxford Abstracts writes the author list comma-separated with no
    affiliations. Most names are already 'First Last', so normalise() only has
    to fix capitalisation and particles - but submitters sometimes type
    'Surname, Initials' inside that comma-separated list, which the split would
    tear apart, so those halves are rejoined first.
    """
    parts = [p.strip() for p in re.split(r",(?![^(]*\))", raw or "") if p.strip()]
    joined = []
    for p in parts:
        if joined and _INITIALS_ONLY.match(p):
            joined[-1] = f"{p.strip()} {joined[-1]}".strip()
        else:
            joined.append(p)
    parts = joined
    pn = re.sub(r"[^a-z]", "", (presenter or "").lower())
    out, matched = [], False
    for i, name in enumerate(parts, 1):
        half = len(name) // 2
        if len(name) % 2 == 1 and name[:half].strip() == name[half + 1:].strip():
            name = name[:half].strip()      # submitter typed their name twice
        clean = names.normalise(name)
        is_pres = bool(pn) and re.sub(r"[^a-z]", "", clean.lower()) == pn
        matched = matched or is_pres
        out.append(dict(full_name=clean, position=i, is_presenter=int(is_pres),
                        presenter_inferred=0, affiliation=None,
                        affiliation_country=None, raw_author_string=raw))
    if presenter and not matched:
        # Presenter named but not found in the author list (a spelling variant):
        # flag the first author, and record that we inferred it.
        if out:
            out[0]["is_presenter"] = 1
            out[0]["presenter_inferred"] = 1
        else:
            out.append(dict(full_name=names.normalise(presenter), position=1,
                            is_presenter=1, presenter_inferred=1,
                            affiliation=None, affiliation_country=None,
                            raw_author_string=raw))
    return out


# Fields the export carries that the abstracts table has no column for. Held
# apart from the record dict because they are written in a second statement.
_EXTRA_COLS = ("discipline", "presenter_career_stage", "subject_category",
               "taxon_group", "common_name")


def ensure_columns(con):
    """Fields the Oxford Abstracts export carries that no PDF book does."""
    have = {r[1] for r in con.execute("PRAGMA table_info(abstracts)")}
    for col in _EXTRA_COLS:
        if col not in have:
            con.execute(f"ALTER TABLE abstracts ADD COLUMN {col} TEXT")
    con.commit()


def _elasmo(title, body, taxon, common):
    """2025 asks the submitter which taxon they work on, and one of the choices
    is 'Ichthyofauna: Chondrichthyan fishes (AES)'. That is the author's own
    answer, so it beats reading the prose - but it does not replace the
    lexicon, because a talk filed under 'Ichthyofauna in general' can still be
    about sharks. Either one is enough; the basis records which said so."""
    if "chondrichthyan" in (taxon or "").lower():
        return True, "taxon_group"
    if lexicon.is_elasmo_text(title, body) or lexicon.is_elasmo_text(common, ""):
        return True, "content"
    return False, "content"


_SOC_RE = re.compile(r"\b(" + "|".join(sorted(C.SOCIETIES)) + r")\b")


def _society(rec):
    """Whose part of the meeting this was, from the most specific field that
    names exactly one society: the award competed for, then the symposium, then
    the taxon group ('... (AES)'), and only then the submitter's membership."""
    for field, basis in (("award", "award"), ("session_name", "symposium"),
                         ("taxon_group", "taxon_group")):
        found = set(_SOC_RE.findall(rec.get(field) or ""))
        if len(found) == 1:
            return found.pop(), basis
    return _society_from_membership(rec.get("societies_explicit"))


def read_export(xlsx_path):
    """Parse the export into record dicts. Ignores the trailing per-author
    block columns: they are misaligned in the 2021 file (three rows carry
    another abstract's co-authors) and the 'Authors' column is complete."""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    idx, kw_cols = {}, []
    for i, h in enumerate(header):
        key = _s(h).lower()
        if key in _HEADERS:
            idx.setdefault(_HEADERS[key], i)
        elif _KEYWORD_RE.match(key):
            kw_cols.append(i)
    missing = {"title", "abstract", "authors"} - set(idx)
    if missing:
        raise ValueError(f"{xlsx_path}: export is missing column(s) {sorted(missing)}")

    out = []
    for r in rows[1:]:
        title = _s(r[idx["title"]]) if idx.get("title") is not None else ""
        if not title:
            continue
        body = _s(r[idx["abstract"]])
        presentation = _s(r[idx["presentation"]]) if "presentation" in idx else ""
        membership = _s(r[idx["membership"]]) if "membership" in idx else ""
        kws = [_s(r[i]) for i in kw_cols if _s(r[i])]
        taxon = _s(r[idx["taxon_group"]]) if "taxon_group" in idx else ""
        common = _s(r[idx["common_name"]]) if "common_name" in idx else ""
        elasmo, basis = _elasmo(title, body, taxon, common)
        out.append(dict(
            title=title,
            abstract_text=body or None,
            keywords="; ".join(kws) or None,
            presentation_type=_presentation_type(presentation),
            award=_award(presentation),
            session_name=_session(presentation),
            session_datetime=None,
            program_number=None,
            location=None,
            societies_explicit=membership or None,
            discipline=_s(r[idx["discipline"]]) or None if "discipline" in idx else None,
            presenter_career_stage=(_s(r[idx["career_stage"]]) or None
                                    if "career_stage" in idx else None),
            subject_category=(_s(r[idx["subject_category"]]) or None
                              if "subject_category" in idx else None),
            taxon_group=taxon or None,
            common_name=common or None,
            authors=_split_authors(_s(r[idx["authors"]]),
                                   _s(r[idx["presenter"]]) if "presenter" in idx else ""),
            is_elasmo=int(elasmo),
            elasmo_basis=basis,
            confidence=1.0,
            needs_review=0,
            source_page=None,
        ))
    return _dedupe(out)


def _dedupe(records):
    """Collapse the same talk submitted twice, keeping the fuller submission.

    Submitters resubmit - in 2022 one abstract appears twice, once with two
    authors and once with all fourteen. The DB's own dedupe keeps whichever
    arrives first, which would have thrown away twelve names, so choose here on
    author count then body length instead of leaving it to insertion order.
    """
    best = {}
    order = []
    for rec in records:
        key = re.sub(r"\s+", " ", rec["title"]).strip().lower()
        prev = best.get(key)
        if prev is None:
            best[key] = rec
            order.append(key)
            continue
        rank = lambda x: (len(x["authors"]), len(x["abstract_text"] or ""))
        if rank(rec) > rank(prev):
            best[key] = rec
    return [best[k] for k in order]


def _society_from_membership(membership):
    """Membership is who the submitter belongs to, not whose session they spoke
    in, so resolve it only when it is unambiguous; the rest are left for the
    programme-book merge or infer_society_missing.py."""
    toks = [t for t in re.split(r"[-,;/ ]+", membership or "") if t in C.SOCIETIES]
    return (toks[0], "membership") if len(toks) == 1 else (None, None)


def ingest(con, xlsx_path, meta, dry_run=False):
    records = read_export(xlsx_path)
    if dry_run:
        return None, records
    ensure_columns(con)
    mid = load.upsert_meeting(con, meta)
    n = 0
    for rec in records:
        society, basis = _society(rec)
        rec = dict(rec, society=society, society_basis=basis, society_inferred=None)
        extras = [rec.pop(c, None) for c in _EXTRA_COLS]
        aid = load.insert_abstract(con, mid, rec)
        if aid is None:
            continue
        con.execute("UPDATE abstracts SET "
                    + ", ".join(f"{c}=?" for c in _EXTRA_COLS)
                    + " WHERE abstract_id=?", (*extras, aid))
        n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return mid, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--meeting", default="JMIH")
    ap.add_argument("--xlsx", help="override the path in config.OA_XLSX_SOURCES")
    ap.add_argument("--no-merge-schedule", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.6)
    a = ap.parse_args()

    key = (a.meeting, a.year)
    xlsx = a.xlsx or C.OA_XLSX_SOURCES.get(key)
    if not xlsx:
        sys.exit(f"no Oxford Abstracts export registered for {key}; "
                 f"add it to config.OA_XLSX_SOURCES or pass --xlsx")
    con = sqlite3.connect(str(C.DB_PATH))
    meta = dict(meeting=a.meeting, year=a.year,
                name=C.OA_MEETING_NAMES.get(key, f"{a.meeting} {a.year}"),
                location=C.OA_MEETING_CITIES.get(key), dates=None,
                source_pdf=str(xlsx), doc_type="abstract_book", page_count=None,
                is_ocr=0, parse_status="ok")
    mid, records = ingest(con, xlsx, meta, dry_run=a.dry_run)
    n_el = sum(r["is_elasmo"] for r in records)
    n_body = sum(1 for r in records if (r["abstract_text"] or "").split().__len__() > 50)
    print(f"{Path(xlsx).name}: {len(records)} abstracts parsed, {n_body} with a body "
          f"(>50 words), {n_el} elasmo")
    if a.dry_run:
        print("dry run - nothing written")
        return
    print(f"  inserted into meeting_id {mid}")
    if not a.no_merge_schedule:
        merged, kept = merge_program_schedule(con, a.year, mid, a.threshold)
        print(f"  programme book: {merged} duplicates merged into the export rows "
              f"(session/day/time carried over) and removed; {kept} unmatched kept")
    con.close()


if __name__ == "__main__":
    main()
