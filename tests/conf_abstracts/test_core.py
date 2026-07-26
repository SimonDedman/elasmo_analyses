"""Plain-assert tests (no pytest dependency) for the pure-logic modules.
Run: ./venv/bin/python tests/conf_abstracts/run_tests.py
"""
import sqlite3
import tempfile
from pathlib import Path

from conf_abstracts import schema, classify, tag, load
from conf_abstracts.sessions import parse_session_line as P


def test_schema_tables():
    with tempfile.TemporaryDirectory() as d:
        con = schema.create_db(Path(d) / "t.db")
        tables = {r[0] for r in con.execute(
            "select name from sqlite_master where type='table'")}
        assert {"meetings", "abstracts", "authors"} <= tables, tables
        cols = {r[1] for r in con.execute("pragma table_info(abstracts)")}
        need = {"society", "societies_explicit", "society_inferred",
                "society_basis", "is_elasmo", "elasmo_basis", "award",
                "presentation_type", "abstract_text"}
        assert need <= cols, need - cols


def test_classify_names():
    c = classify.classify_from_name
    assert c("2016-JMIH-Abstract-Book-180n2l2.pdf") == ("JMIH", 2016, "abstract_book")
    assert c("2007 ASIH.pdf")[:2] == ("ASIH", 2007)
    assert c("SI2026 - Abstract Book (29th April 2026).pdf")[:2] == ("SI", 2026)
    assert c("2009-JMIH-Poster-Presentations-13bd3x5.pdf")[2] == "poster_list"
    assert c("2019-JMIH-Program-Book-MASTER-FINAL.pdf")[2] == "program_book"


def test_session_prefix():
    r = P("AES Sawfishes Symposium, Salon E, Sunday 10 July 2016")
    assert r["societies_explicit"] == ["AES"], r
    assert r["presentation_type"] == "symposium"
    assert r["session_datetime"] == "Sunday 10 July 2016", r
    assert r["location"] == "Salon E", r


def test_session_award_suffix():
    r = P("Poster Session I, Acadia/Bissonet, Friday 8 July 2016; AES CARRIER")
    assert r["societies_explicit"] == ["AES"], r
    assert r["award"].startswith("AES"), r
    assert r["presentation_type"] == "poster"


def test_session_multi_society():
    r = P("HL, ASIH, SSAR: Eco-Evolutionary Dynamics Symposium, Room 1, Sunday 10 July 2016")
    assert set(r["societies_explicit"]) == {"HL", "ASIH", "SSAR"}, r


def test_session_no_society():
    r = P("Poster Session II, Acadia/Bissonet, Saturday 9 July 2016")
    assert r["societies_explicit"] == [], r
    assert r["presentation_type"] == "poster"


def test_tag_explicit_aes():
    r = tag.resolve({"societies_explicit": ["AES"], "society_inferred": None,
                     "award": None}, "JMIH")
    assert r["society"] == "AES" and r["society_basis"] == "session_prefix"
    assert r["is_elasmo"] == 1 and r["elasmo_basis"] == "session_prefix"


def test_tag_meeting_si():
    r = tag.resolve({"societies_explicit": [], "society_inferred": None,
                     "award": None}, "SI")
    assert r["is_elasmo"] == 1 and r["elasmo_basis"] == "meeting"


def test_tag_content_inferred():
    r = tag.resolve({"societies_explicit": [], "society_inferred": "AES",
                     "award": None}, "JMIH")
    assert r["society"] == "AES" and r["society_basis"] == "content"
    assert r["is_elasmo"] == 1 and r["elasmo_basis"] == "content"


def test_tag_non_elasmo():
    r = tag.resolve({"societies_explicit": ["HL"], "society_inferred": None,
                     "award": None}, "JMIH")
    assert r["society"] == "HL" and r["is_elasmo"] == 0


def test_load_insert_and_dedup():
    with tempfile.TemporaryDirectory() as d:
        con = schema.create_db(Path(d) / "t.db")
        mid = load.upsert_meeting(con, {"meeting": "JMIH", "year": 2016,
                                        "source_pdf": "x.pdf"})
        rec = {"program_number": "0974", "title": "T", "abstract_text": "a b c",
               "societies_explicit": ["AES"], "society": "AES", "is_elasmo": 1,
               "authors": [{"full_name": "A B", "position": 1}]}
        a1 = load.insert_abstract(con, mid, rec)
        a2 = load.insert_abstract(con, mid, rec)
        assert a1 and a2 is None
        assert con.execute("select count(*) from authors").fetchone()[0] == 1
        assert con.execute("select length_words from abstracts").fetchone()[0] == 3
