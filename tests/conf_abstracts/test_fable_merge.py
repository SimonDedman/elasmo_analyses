"""Guards on folding the Fable DB into the DB of record (no pytest).
All on throwaway DBs: never the live conference_abstracts.db."""
import sqlite3
import tempfile
from pathlib import Path

from conf_abstracts import config as C, schema, load
from conf_abstracts import merge_fable_into_main as M
from conf_abstracts import scrape_elasmo_org as S

BODY = "Tracking juvenile fish across an estuary with acoustic telemetry arrays."


def _book(con, src, titles, year=2019, meeting="JMIH", **extra):
    mid = load.upsert_meeting(con, {"meeting": meeting, "year": year, "source_pdf": src})
    for i, t in enumerate(titles):
        load.insert_abstract(con, mid, dict({"program_number": str(i), "title": t,
                                             "abstract_text": f"{BODY} {t}"}, **extra))
    con.commit()
    return mid


def _titles(n, stem="Movement ecology of an estuarine fish population number"):
    return [f"{stem} {i}" for i in range(n)]


def test_merge_carries_society_forward_onto_unchanged_records():
    # re-merging a book must not blank the backfilled society of records whose
    # content did not change (2026-09-15: 10,698 rows blanked)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        main = schema.create_db(d / "main.db")
        _book(main, "2016.pdf", ["Frog calls in the rain forest canopy at dusk"],
              society="HL", society_basis="content", confidence=0.9)
        main.close()
        fab = schema.create_db(d / "fab.db")
        _book(fab, "2016.pdf", ["Frog calls in the rain forest canopy at dusk",
                                "A brand new abstract with no society yet assigned"])
        fab.close()
        M.merge(db_path=d / "main.db", fable_path=d / "fab.db", finish_chain=False)
        got = dict(sqlite3.connect(d / "main.db").execute(
            "SELECT title, society || '/' || society_basis FROM abstracts"))
        assert got["Frog calls in the rain forest canopy at dusk"] == "HL/content"
        assert got["A brand new abstract with no society yet assigned"] is None


def test_merge_aborts_when_a_sibling_meeting_holds_the_same_records():
    # JMIH 2019: Fable's part1 meeting held both halves, the main DB's part2
    # meeting was left beside it -> must roll back, not double-count
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        half1, half2 = _titles(12, "First half abstract"), _titles(12)
        main = schema.create_db(d / "main.db")
        _book(main, "part1.pdf", half1)
        _book(main, "part2.pdf", half2)
        main.close()
        fab = schema.create_db(d / "fab.db")
        _book(fab, "part1.pdf", half1 + half2)
        fab.close()
        before = (d / "main.db").read_bytes()
        try:
            M.merge(db_path=d / "main.db", fable_path=d / "fab.db", finish_chain=False)
            raise AssertionError("merge should have aborted")
        except SystemExit:
            pass
        n = sqlite3.connect(d / "main.db").execute("SELECT COUNT(*) FROM abstracts").fetchone()[0]
        assert n == 24 and (d / "main.db").read_bytes() == before


def test_merge_allows_the_odd_shared_title_between_oral_and_poster_books():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        main = schema.create_db(d / "main.db")
        _book(main, "poster.pdf", _titles(3, "Poster only abstract") + ["Shared talk title given as both oral and poster"])
        main.close()
        fab = schema.create_db(d / "fab.db")
        _book(fab, "oral.pdf", _titles(3) + ["Shared talk title given as both oral and poster"])
        fab.close()
        M.merge(db_path=d / "main.db", fable_path=d / "fab.db", finish_chain=False)
        assert sqlite3.connect(d / "main.db").execute("SELECT COUNT(*) FROM abstracts").fetchone()[0] == 8


def test_supersede_ignores_aes_inferred_from_content():
    # a lexicon-inferred AES tag is not evidence of an AES session: superseding
    # on it deleted talks elasmo.org does not hold
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        con = schema.create_db(d / "main.db")
        load.upsert_meeting(con, {"meeting": "AES", "year": 2005, "source_pdf": "aes.html"})
        _book(con, "jmih.pdf", ["Shark talk in an AES session with a session prefix"],
              year=2005, is_elasmo=1, society="AES", society_basis="session_prefix")
        _book(con, "jmih2.pdf", ["Shark talk tagged AES only by the lexicon backfill"],
              year=2005, is_elasmo=1, society="AES", society_basis="content")
        con.close()
        old = C.DB_PATH
        try:
            C.DB_PATH = d / "main.db"
            S.supersede()
        finally:
            C.DB_PATH = old
        left = [r[0] for r in sqlite3.connect(d / "main.db").execute("SELECT title FROM abstracts")]
        assert left == ["Shark talk tagged AES only by the lexicon backfill"]
