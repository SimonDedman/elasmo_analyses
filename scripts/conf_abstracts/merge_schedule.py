"""Fold a programme book's schedule into the abstract records for the same year.

An abstract source (an Oxford Abstracts export, or an abstract-book PDF) carries
the science; the programme book for the same meeting carries what the abstract
source usually does not - the session, the day and time, and often whether a
talk was a talk, a poster, a lightning talk or a symposium contribution. Once
those are copied across, the programme-book row is a duplicate of the abstract
row and is deleted, so a year is counted once.

Matching is token overlap on the title, falling back to a 40-character verbatim
run, because programme-book titles are mangled at the ENDS - cut to the column
width, run into the author list, or split so only the tail survives.

Usage:
  merge_schedule.py --year 2023 --target-meeting 148
"""
import argparse
import difflib
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402

_STOP = {"the", "of", "a", "an", "in", "on", "and", "for", "from", "to", "with",
         "by", "at"}


def _toks(t):
    return {w for w in re.findall(r"[a-z]{3,}", (t or "").lower()) if w not in _STOP}


def _jaccard(a, b):
    return len(a & b) / len(a | b) if (a and b) else 0.0


def _norm(t):
    """Spaces go too: pdftotext drops them unpredictably at line joins, so the
    2023 programme prints "Latimeriachalumnae" where the abstract book has
    "Latimeria chalumnae", and a space-sensitive comparison misses the pair."""
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


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
    # Only trust the programme book's talk/poster split if it actually made one.
    # Before the 2023 poster sections were parsed it called all 389 rows 'talk',
    # and copying that across would have been worse than leaving the field null.
    types = {r[7] for r in prog if r[7]}
    take_type = len(types) > 1
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
                  SET program_number    = COALESCE(program_number, ?),
                      session_name      = COALESCE(session_name, ?),
                      session_datetime  = COALESCE(session_datetime, ?),
                      society           = COALESCE(society, ?),
                      society_basis     = CASE WHEN society IS NULL THEN ? ELSE society_basis END,
                      presentation_type = COALESCE(presentation_type, ?)
                WHERE abstract_id=?""",
            (row[2], row[3] if take_session else None, row[4], row[5], row[6],
             row[7] if take_type else None, best_aid))
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
    ap.add_argument("--target-meeting", type=int, required=True,
                    help="meeting_id of the abstract source to merge INTO")
    ap.add_argument("--threshold", type=float, default=0.6)
    a = ap.parse_args()
    con = sqlite3.connect(str(C.DB_PATH))
    merged, kept = merge_program_schedule(con, a.year, a.target_meeting, a.threshold)
    print(f"{a.year}: {merged} programme-book rows merged into meeting "
          f"{a.target_meeting} and removed; {kept} unmatched kept")
    con.close()


if __name__ == "__main__":
    main()
