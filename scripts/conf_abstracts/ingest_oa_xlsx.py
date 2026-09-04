"""Ingest a JMIH Oxford Abstracts submission export (xlsx) into the abstracts DB.

JMIH pays Oxford Abstracts for its submission site, so from ~2021 the programme
officer can export every submitted abstract as a spreadsheet. David M. Green
(JMIH programme officer, McGill) supplied the JMIH 2021 export on 2026-09-04.
This is the cleanest source we have for any JMIH year: born-digital title,
author list, presenter flag, full body, four keywords, presentation type,
society membership, career stage. What it does NOT carry is affiliations, the
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
import difflib
import re
import sqlite3
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts import lexicon, load, names  # noqa: E402

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

_STOP = {"the", "of", "a", "an", "in", "on", "and", "for", "from", "to", "with",
         "by", "at"}


def _toks(t):
    return {w for w in re.findall(r"[a-z]{3,}", (t or "").lower()) if w not in _STOP}


def _jaccard(a, b):
    return len(a & b) / len(a | b) if (a and b) else 0.0


def _norm(t):
    return re.sub(r"[^a-z0-9 ]", "", (t or "").lower())


def _shared_run(a, b, need=40):
    """Programme-book titles get mangled at either end - cut to the column
    width, run into the author list, or split so only the tail survives - but a
    long verbatim run through the middle still matches. This catches what token
    overlap misses: 16 of 242 in JMIH 2021, every one verified as a fragment of
    an abstract already in the export. 40 characters is long enough that a
    chance match between two unrelated titles is not a realistic concern."""
    a, b = _norm(a), _norm(b)
    if len(a) < need or len(b) < need:
        return False
    return difflib.SequenceMatcher(None, a, b, autojunk=False) \
        .find_longest_match(0, len(a), 0, len(b)).size >= need


def _s(v):
    return "" if v is None else str(v).strip()


def _presentation_type(text):
    low = text.lower()
    for needle, ptype in _TYPE_RULES:
        if needle in low:
            return ptype
    return "talk"


def _award(text):
    """The competition name, if this is a student competition entry."""
    if "competition" in text.lower():
        return re.sub(r"\s*\((?:all are )?virtual\)|\s+(?:IN-PERSON|VIRTUAL)\s*$",
                      "", text).strip()
    return None


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


def ensure_columns(con):
    """Two fields the Oxford Abstracts export carries that no PDF book does."""
    have = {r[1] for r in con.execute("PRAGMA table_info(abstracts)")}
    for col in ("discipline", "presenter_career_stage"):
        if col not in have:
            con.execute(f"ALTER TABLE abstracts ADD COLUMN {col} TEXT")
    con.commit()


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
        out.append(dict(
            title=title,
            abstract_text=body or None,
            keywords="; ".join(kws) or None,
            presentation_type=_presentation_type(presentation),
            award=_award(presentation),
            session_name=None,
            session_datetime=None,
            program_number=None,
            location=None,
            societies_explicit=membership or None,
            discipline=_s(r[idx["discipline"]]) or None if "discipline" in idx else None,
            presenter_career_stage=(_s(r[idx["career_stage"]]) or None
                                    if "career_stage" in idx else None),
            authors=_split_authors(_s(r[idx["authors"]]),
                                   _s(r[idx["presenter"]]) if "presenter" in idx else ""),
            is_elasmo=int(lexicon.is_elasmo_text(title, body)),
            elasmo_basis="content",
            confidence=1.0,
            needs_review=0,
            source_page=None,
        ))
    return out


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
        society, basis = _society_from_membership(rec["societies_explicit"])
        rec = dict(rec, society=society, society_basis=basis, society_inferred=None)
        extras = (rec.pop("discipline"), rec.pop("presenter_career_stage"))
        aid = load.insert_abstract(con, mid, rec)
        if aid is None:
            continue
        con.execute("UPDATE abstracts SET discipline=?, presenter_career_stage=? "
                    "WHERE abstract_id=?", (*extras, aid))
        n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return mid, records


def merge_program_schedule(con, year, mid, threshold=0.6):
    """Move the programme book's session/day/time onto the matching export rows,
    then delete the programme-book duplicates. Programme-book entries with no
    export counterpart are kept (they are the only record of those talks)."""
    prog = con.execute(
        """SELECT a.abstract_id, a.title, a.program_number, a.session_name,
                  a.session_datetime, a.society, a.society_basis, a.presentation_type
           FROM abstracts a JOIN meetings m USING(meeting_id)
           WHERE m.meeting IN ('JMIH','ASIH') AND m.year=? AND m.doc_type='program_book'
        """, (year,)).fetchall()
    if not prog:
        return 0, 0
    # Only carry the session name across if the programme book actually parsed
    # sessions. When its heading detection fails it labels every talk with one
    # heading (JMIH 2021: all 225 came back "Chasing Catastrophes Slowly:"),
    # which is worse than leaving the field empty.
    n_sessions = con.execute(
        """SELECT COUNT(DISTINCT a.session_name) FROM abstracts a
             JOIN meetings m USING(meeting_id)
            WHERE m.meeting IN ('JMIH','ASIH') AND m.year=?
              AND m.doc_type='program_book' AND a.session_name IS NOT NULL""",
        (year,)).fetchone()[0]
    take_session = n_sessions >= 3
    if not take_session:
        print(f"  programme book sessions unusable ({n_sessions} distinct) - not merged")
    export = con.execute(
        "SELECT abstract_id, title FROM abstracts WHERE meeting_id=?", (mid,)).fetchall()
    ex_toks = [(aid, _toks(t)) for aid, t in export]
    merged, victims = 0, []
    for row in prog:
        paid, ptitle = row[0], row[1]
        pt = _toks(ptitle)
        if len(pt) < 3:
            continue
        best_aid, best = None, 0.0
        for aid, et in ex_toks:
            j = _jaccard(pt, et)
            if j > best:
                best_aid, best = aid, j
        if best < threshold:
            best_aid = next((aid for aid, t in export if _shared_run(ptitle, t)), None)
            if best_aid is None:
                continue
        con.execute(
            """UPDATE abstracts
                  SET program_number   = COALESCE(program_number, ?),
                      session_name     = COALESCE(session_name, ?),
                      session_datetime = COALESCE(session_datetime, ?),
                      society          = COALESCE(society, ?),
                      society_basis    = CASE WHEN society IS NULL THEN ? ELSE society_basis END
                WHERE abstract_id=?""",
            (row[2], row[3] if take_session else None, row[4], row[5], row[6],
             best_aid))
        victims.append(paid)
        merged += 1
    for aid in victims:
        con.execute("DELETE FROM authors WHERE abstract_id=?", (aid,))
        con.execute("DELETE FROM abstracts WHERE abstract_id=?", (aid,))
    con.execute("UPDATE meetings SET n_abstracts="
                "(SELECT COUNT(*) FROM abstracts WHERE abstracts.meeting_id=meetings.meeting_id)")
    con.commit()
    return merged, len(prog) - merged


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
