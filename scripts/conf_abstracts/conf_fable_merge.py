"""STAGE 3 — merge Fable abstract-extraction caches into the abstracts DB.

Reads each book's JSON cache (written by the Fable agents), inserts meetings +
abstracts + authors via the existing load layer, tags elasmo (EEA/SI meetings
are wholly elasmo; otherwise the lexicon decides), and regenerates the exports.

By default writes to a SEPARATE DB (conference_abstracts_fable.db) so the Fable
output can be quality-compared against the regex DB before replacing it. Pass
--db to point elsewhere.

Run: ./venv/bin/python scripts/conf_abstracts/conf_fable_merge.py [--db PATH]
"""
import argparse
import json
from pathlib import Path

from conf_abstracts import config as C, schema, load, tag, lexicon, export

WORKLIST = C.OUT / "conf_abstracts" / "fable_worklist.json"


def _mk_record(a: dict, meeting: str, is_elasmo_meeting: bool, soc_hint: str):
    """Turn one Fable abstract object into a load.insert_abstract record."""
    title = (a.get("title") or "").strip()
    body = (a.get("abstract_text") or "").strip() or None
    ptype = (a.get("presentation_type") or "").strip().lower() or None
    if ptype and ptype not in C.PRESENTATION_TYPES:
        ptype = None
    kw = a.get("keywords") or []
    keywords = "; ".join(k for k in kw if k) if isinstance(kw, list) else (kw or None)

    authors = []
    for i, au in enumerate(a.get("authors") or [], start=1):
        if isinstance(au, str):
            authors.append(dict(full_name=au.strip(), position=i))
        elif isinstance(au, dict):
            authors.append(dict(
                full_name=(au.get("full_name") or au.get("name") or "").strip(),
                position=i,
                is_presenter=int(bool(au.get("is_presenter"))),
                affiliation=(au.get("affiliation") or None),
                affiliation_country=(au.get("affiliation_country") or None)))
    authors = [x for x in authors if x["full_name"]]

    # society from the session heading's society prefix ("AES GRUBER",
    # "SSAR SEIBERT ECOLOGY", "Session 7: ASIH Stoye ...") — same rule as the
    # programme-book parser, so JMIH multi-society books tag per abstract.
    from conf_abstracts.parse_program_book import _session_society
    session = (a.get("session_name") or None)
    soc = _session_society(session) if session else None
    rec = dict(
        program_number=a.get("program_number"),
        title=title or None,
        presentation_type=ptype,
        session_name=session,
        abstract_text=body,
        keywords=keywords,
        authors=authors,
        society=None, societies_explicit=[soc] if soc else None, society_inferred=None,
    )
    rec = tag.resolve(rec, meeting)          # EEA/SI meeting -> is_elasmo=1
    # non-elasmo-meeting books: fall back to the lexicon on title+body
    if not rec["is_elasmo"] and not is_elasmo_meeting:
        if lexicon.is_elasmo_text(title, body or ""):
            rec["is_elasmo"] = 1
            rec["elasmo_basis"] = "content"
    if is_elasmo_meeting and rec.get("society") is None:
        rec["society"] = soc_hint
        rec["society_basis"] = "meeting"
    if not rec["title"] or len(rec["title"]) > 300:
        rec["needs_review"] = 1
    return rec


def merge(db_path):
    wl = json.loads(WORKLIST.read_text(encoding="utf-8"))
    # rebuild fresh from the caches every run — the DB is a derived artifact, so
    # rebuilding keeps per-book counts accurate and the merge idempotent (an
    # append would dedup re-merged books to "0 inserted").
    dbp = Path(db_path)
    if dbp.exists():
        dbp.unlink()
    con = schema.create_db(db_path)
    missing = []
    for w in wl:
        cache = Path(w["cache_path"])
        if not cache.exists() or cache.stat().st_size < 2:
            missing.append(w["key"])
            continue
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  {w['key']:16} BAD JSON: {e}")
            missing.append(w["key"])
            continue
        abstracts = data if isinstance(data, list) else data.get("abstracts", [])
        # chunks of one book share source_pdf -> one meeting; title-dedup folds
        # the overlap. upsert_meeting returns the existing id for later chunks.
        meta = dict(
            meeting=w["meeting"], year=w["year"], name=None,
            location=w["city"], dates=None, source_pdf=w["source_pdf"],
            doc_type="abstract_book", page_count=None, is_ocr=0,
            parse_status="ok")
        mid = load.upsert_meeting(con, meta)
        for a in abstracts:
            if not isinstance(a, dict):
                continue
            rec = _mk_record(a, w["meeting"], w["is_elasmo_meeting"],
                             w["society_hint"])
            if not rec["title"]:
                continue
            load.insert_abstract(con, mid, rec)   # dedups within the meeting
        con.commit()

    # fix per-meeting counts from the DB (cumulative across chunks) and report
    con.execute("UPDATE meetings SET n_abstracts = "
                "(SELECT COUNT(*) FROM abstracts WHERE abstracts.meeting_id = meetings.meeting_id)")
    con.commit()
    tot_books = tot_abs = 0
    print()
    for mid, mtg, yr, loc, n in con.execute(
            "SELECT meeting_id, meeting, year, location, n_abstracts "
            "FROM meetings ORDER BY year, location"):
        wb = con.execute("SELECT COUNT(*) FROM abstracts WHERE meeting_id=? "
                         "AND abstract_text IS NOT NULL AND length(trim(abstract_text))>0",
                         (mid,)).fetchone()[0]
        print(f"  {mtg} {yr} {(loc or ''):12} {n:4} abstracts ({wb} with body)")
        tot_books += 1
        tot_abs += n
    if missing:
        print(f"\n  NOT YET EXTRACTED: {', '.join(sorted(set(missing)))}")
    print(f"\n{tot_books} meetings, {tot_abs} abstracts -> {db_path}")

    # exports alongside the DB
    stem = Path(db_path).with_suffix("")
    export.to_parquet_elasmo(con, f"{stem}.parquet")
    export.to_json(con, f"{stem}.json")
    export.to_xlsx(con, f"{stem}.xlsx")
    print(f"exports: {stem}.{{parquet,json,xlsx}}")
    con.close()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(C.REPO / "database" / "conference_abstracts_fable.db"))
    a = ap.parse_args()
    merge(a.db)
