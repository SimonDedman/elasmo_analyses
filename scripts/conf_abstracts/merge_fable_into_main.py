"""Fold the Fable-extracted EEA books (conference_abstracts_fable.db) into the
main conference_abstracts.db, making one DB of record (Simon, 2026-08-25).

Idempotent: every EEA meeting in the main DB is replaced by the Fable set on
each run (the Fable DB is itself rebuilt from caches by conf_fable_merge.py).
Refreshes the exports beside both DBs afterwards.

Two guards (2026-09-15), both after a wholesale re-merge damaged the DB:
- society tags on records whose content did not change are carried forward,
  so folding in ONE new book no longer blanks the backfill on every other one
  (10,698 rows blanked, ~3.5 h of Ollama to redo);
- if a replaced book's records also sit in a sibling meeting of the same
  series and year, the merge rolls back and exits (JMIH 2019 part2 was left
  beside a part1 meeting that already held both halves: +424 double-counted).
"""
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C, schema, export, names  # noqa: E402

FABLE = C.REPO / "database" / "conference_abstracts_fable.db"

# per-record fields written after the merge (session prefix or Ollama backfill)
SOCIETY_COLS = ("society", "society_inferred", "society_basis", "confidence")
# MEASURED 2026-09-15: in the good DB of record no two meetings of one series-year
# share more than 1 title (oral vs poster, programme vs abstract book); the
# broken JMIH 2019 merge shared 423.
MAX_SHARED_TITLES = 10


def _content_key(meeting, year, title, body):
    return (meeting, year, re.sub(r"\W+", "", (title or "").lower()),
            re.sub(r"\s+", " ", body or "")[:200])


def _shared_titles(con, new_mids):
    """(series, year, book_a, book_b, n) for meeting pairs of one series-year that
    share more than MAX_SHARED_TITLES titles, where one side was just inserted."""
    by_title = defaultdict(set)
    books = {}
    for mid, mtg, yr, src, title in con.execute(
            "SELECT m.meeting_id, m.meeting, m.year, m.source_pdf, a.title "
            "FROM abstracts a JOIN meetings m USING(meeting_id)"):
        k = re.sub(r"\W+", "", (title or "").lower())
        if len(k) >= 20:        # short stubs ("Poster session") collide by chance
            by_title[(mtg, yr, k)].add(mid)
            books[mid] = (mtg, yr, Path(src or "").name)
    pairs = Counter()
    for mids in by_title.values():
        if len(mids) > 1 and mids & new_mids:
            s = sorted(mids)
            for i, a in enumerate(s):
                for b in s[i + 1:]:
                    pairs[(a, b)] += 1
    return [(*books[a][:2], books[a][2], books[b][2], n)
            for (a, b), n in pairs.items() if n > MAX_SHARED_TITLES]


def merge(db_path=C.DB_PATH, fable_path=FABLE, finish_chain=True, only_books=None):
    """only_books: optional set of source_pdf BASENAMES. When given, ONLY those
    Fable books are folded in and only the main meetings they supersede are
    replaced -- the blanket "replace every EEA meeting" rule is skipped too.
    Added 2026-09-17 to fold SOMEPEC + IPFC 2009 in on their own, without also
    swapping main's JMIH 1998/2005 books for their Fable versions (which need
    Simon's sign-off). Passing nothing keeps the original whole-DB behaviour."""
    main = schema.create_db(db_path)
    fab = sqlite3.connect(str(fable_path))
    fab.row_factory = sqlite3.Row
    # replace every main meeting that the Fable set supersedes: all EEA rows, plus
    # any regex-parsed book whose source_pdf Fable has also extracted (JMIH 2005/2016)
    fab_srcs = [r[0] for r in fab.execute("SELECT source_pdf FROM meetings")]
    if only_books is not None:
        only_books = set(only_books)
        fab_srcs = [s for s in fab_srcs if Path(s or "").name in only_books]
        unknown = only_books - {Path(s or "").name for s in fab_srcs}
        if unknown:
            raise SystemExit(f"no such book in the Fable DB: {sorted(unknown)}")
        old = main.execute("SELECT meeting_id FROM meetings WHERE source_pdf IN (%s)"
                           % ",".join("?" * len(fab_srcs)), fab_srcs).fetchall()
    else:
        old = main.execute("SELECT meeting_id FROM meetings WHERE meeting='EEA' OR source_pdf IN (%s)"
                           % ",".join("?" * len(fab_srcs)), fab_srcs).fetchall()

    # A flatbed rescan SUPERSEDES the phone scan of the same meeting, but the two
    # have different filenames (..._phonescan.pdf), so matching on source_pdf
    # alone left both in the DB: JMIH 1998 carried 94 junk phone-scan records
    # (every one needs_review, titles like "American Socicty of Ichthyologist and
    # Elerpatc!szsts") alongside the 601 clean flatbed ones. Drop the superseded
    # meeting, but ONLY where a clean book for that same meeting-year is actually
    # being merged — for 1997/1999/2000/2001 the phone scan is still the only
    # source we have and must be kept.
    fab_years = {(r[0], r[1]) for r in fab.execute("SELECT meeting, year, source_pdf FROM meetings")
                 if only_books is None or Path(r[2] or "").name in only_books}
    for mid, meeting, year, src in main.execute(
            "SELECT meeting_id, meeting, year, source_pdf FROM meetings").fetchall():
        if not src or not any(frag in src for frag in C.SKIP_NAME_FRAGMENTS):
            continue
        if (meeting, year) in fab_years:
            print(f"  SUPERSEDED {meeting} {year}: dropping {Path(src).name} "
                  f"(replaced by the clean book)")
            old.append((mid,))

    # snapshot society tags before the rows go; a key seen with two different
    # tag sets is ambiguous and restores nothing
    kept = {}
    for (mid,) in old:
        for mtg, yr, title, body, *soc in main.execute(
                f"SELECT m.meeting, m.year, a.title, a.abstract_text, "
                f"{', '.join('a.' + c for c in SOCIETY_COLS)} "
                f"FROM abstracts a JOIN meetings m USING(meeting_id) "
                f"WHERE a.meeting_id=? AND a.society IS NOT NULL", (mid,)):
            k = _content_key(mtg, yr, title, body)
            kept[k] = tuple(soc) if kept.get(k, tuple(soc)) == tuple(soc) else None

    for (mid,) in old:
        main.execute("DELETE FROM authors WHERE abstract_id IN (SELECT abstract_id FROM abstracts WHERE meeting_id=?)", (mid,))
        main.execute("DELETE FROM abstracts WHERE meeting_id=?", (mid,))
        main.execute("DELETE FROM meetings WHERE meeting_id=?", (mid,))
    mcols = [r[1] for r in fab.execute("PRAGMA table_info(meetings)") if r[1] != "meeting_id"]
    acols = [r[1] for r in fab.execute("PRAGMA table_info(abstracts)") if r[1] not in ("abstract_id", "meeting_id")]
    ucols = [r[1] for r in fab.execute("PRAGMA table_info(authors)") if r[1] not in ("author_id", "abstract_id")]
    n_m = n_a = n_u = n_soc = 0
    new_mids = set()
    for m in fab.execute("SELECT * FROM meetings ORDER BY year"):
        if only_books is not None and Path(m["source_pdf"] or "").name not in only_books:
            continue
        cur = main.execute(f"INSERT INTO meetings ({','.join(mcols)}) VALUES ({','.join('?'*len(mcols))})",
                           [m[c] for c in mcols])
        new_mid = cur.lastrowid; n_m += 1
        new_mids.add(new_mid)
        for a in fab.execute("SELECT * FROM abstracts WHERE meeting_id=?", (m["meeting_id"],)):
            vals = {c: a[c] for c in acols}
            soc = kept.get(_content_key(m["meeting"], m["year"], a["title"], a["abstract_text"]))
            if vals["society"] is None and soc:
                vals.update(zip(SOCIETY_COLS, soc)); n_soc += 1
            cur = main.execute(f"INSERT INTO abstracts (meeting_id,{','.join(acols)}) VALUES (?,{','.join('?'*len(acols))})",
                               [new_mid] + list(vals.values()))
            new_aid = cur.lastrowid; n_a += 1
            for u in fab.execute("SELECT * FROM authors WHERE abstract_id=? ORDER BY position", (a["abstract_id"],)):
                main.execute(f"INSERT INTO authors (abstract_id,{','.join(ucols)}) VALUES (?,{','.join('?'*len(ucols))})",
                             [new_aid] + [u[c] for c in ucols])
                n_u += 1

    clashes = _shared_titles(main, new_mids)
    if clashes:
        main.rollback(); main.close(); fab.close()
        for mtg, yr, a, b, n in clashes:
            print(f"  ABORT {mtg} {yr}: {a} and {b} share {n} titles")
        print("merge rolled back, DB of record unchanged. A replaced book's records "
              "also sit in a sibling meeting: check the worklist's source_pdf for "
              "each book_key, then rebuild with conf_fable_merge.py.")
        raise SystemExit(1)

    main.execute("UPDATE meetings SET n_abstracts=(SELECT COUNT(*) FROM abstracts WHERE abstracts.meeting_id=meetings.meeting_id)")
    main.commit()
    print(f"author names normalised: {names.normalise_db(main)}")
    print(f"replaced {len(old)} main meetings (EEA + Fable-superseded books) with {n_m} from Fable: {n_a} abstracts, {n_u} authors")
    print(f"society tags carried forward onto unchanged records: {n_soc}")
    main.close(); fab.close()
    if not finish_chain:
        return
    # the Fable set re-introduces AES talks that elasmo.org already holds —
    # always finish the chain here so a bare re-merge can't leave duplicates
    # behind (bitten 2026-08-26). Exports come AFTER, or they carry the duplicates.
    from conf_abstracts import scrape_elasmo_org as S
    S.dedup(0.6)
    S.supersede()
    main = sqlite3.connect(str(db_path))
    tot = main.execute("SELECT COUNT(*), SUM(is_elasmo) FROM abstracts").fetchone()
    print(f"main DB now {tot[0]} abstracts / {tot[1]} elasmo")
    for base in (C.OUT, C.REPO / "database"):
        export.to_parquet_elasmo(main, str(base / "conference_abstracts_elasmo.parquet"))
        export.to_json(main, str(base / "conference_abstracts.json"))
        export.to_xlsx(main, str(base / "conference_abstracts.xlsx"))
        print(f"exports refreshed in {base}")
    left = main.execute("SELECT COUNT(*) FROM abstracts a JOIN meetings m USING(meeting_id) "
                        "WHERE m.meeting IN ('JMIH','ASIH') AND a.society IS NULL "
                        "AND length(a.abstract_text) > 50").fetchone()[0]
    main.close()
    print(f"NOTE: {left} JMIH/ASIH records with a body have no society — "
          "run infer_society_missing.py to backfill them.")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="+", metavar="BOOK.pdf",
                    help="fold in ONLY these Fable books (source_pdf basenames) "
                         "and replace only the main meetings they supersede")
    ap.add_argument("--db", default=str(C.DB_PATH), help="main DB to merge into")
    ap.add_argument("--no-finish-chain", action="store_true",
                    help="skip the dedup/supersede/export chain (testing only)")
    a = ap.parse_args()
    merge(db_path=Path(a.db), only_books=a.only,
          finish_chain=not a.no_finish_chain)
