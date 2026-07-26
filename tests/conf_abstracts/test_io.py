"""Tests for segment / extract / export (no pytest)."""
import tempfile
from pathlib import Path

from conf_abstracts import segment, extract, schema, load, export, qa_ocr

FIX = Path(__file__).resolve().parent / "fixtures" / "jmih2016_p50.txt"


def test_elasmo_lexicon():
    from conf_abstracts.lexicon import is_elasmo_text
    assert is_elasmo_text("Growth Rates of Smalltooth Sawfish Pristis pectinata", "")
    assert is_elasmo_text("Population genetics of the cownose ray", "Rhinoptera bonasus")
    assert is_elasmo_text("Diet of the little skate", "Leucoraja erinacea")
    assert not is_elasmo_text("Calling Phenology of Coastal Prairie Anurans", "frogs")
    assert not is_elasmo_text("Osteology of Nurseryfish", "Kurtus gulliveri")


def test_qa_classify():
    assert qa_ocr._classify(0, 0.0) == "no_text"
    assert qa_ocr._classify(5000, 0.30) == "low_quality"
    assert qa_ocr._classify(5000, 0.60) == "ok"


def test_segment_jmih_blocks():
    txt = FIX.read_text()
    blocks = segment.segment_blocks(txt, "jmih_book")
    assert len(blocks) >= 2, f"got {len(blocks)}"
    b = blocks[0]
    assert b["program_number"] and b["program_number"].isdigit(), b
    assert b["title"], b
    assert b["abstract_text"] and len(b["abstract_text"].split()) > 20, b


def test_extract_authors_asih():
    a = extract.parse_authors("Armbruster, Jonathan; de Souza, Lesley; Lujan, Nathan")
    assert a[0]["full_name"] == "Jonathan Armbruster", a[0]
    assert a[0]["position"] == 1 and a[0]["is_presenter"] == 1
    assert len(a) == 3


def test_extract_authors_superscript():
    a = extract.parse_authors("Dana Bethea1, John Carlson1, Gregg Poulakis3")
    assert [x["full_name"] for x in a] == ["Dana Bethea", "John Carlson", "Gregg Poulakis"], a


def test_extract_fields_no_llm():
    txt = FIX.read_text()
    blocks = segment.segment_blocks(txt, "jmih_book")
    rec = extract.extract_fields(blocks[0], "JMIH", use_llm=False)
    assert rec["title"] and rec["authors"]
    assert rec["presentation_type"] in {"talk", "poster", "lightning",
                                        "symposium", "plenary", "keynote"}
    assert "confidence" in rec


def test_export_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        con = schema.create_db(d / "t.db")
        mid = load.upsert_meeting(con, {"meeting": "SI", "year": 2026,
                                        "source_pdf": "s.pdf"})
        load.insert_abstract(con, mid, {
            "program_number": "1", "title": "Shark movement", "abstract_text": "a b c d e",
            "societies_explicit": ["AES"], "society": "AES", "is_elasmo": 1,
            "presentation_type": "talk",
            "authors": [{"full_name": "A B", "position": 1}]})
        load.insert_abstract(con, mid, {
            "program_number": "2", "title": "Frog calls", "abstract_text": "x y z",
            "societies_explicit": [], "society": "HL", "is_elasmo": 0,
            "presentation_type": "poster", "authors": []})
        pq = d / "elasmo.parquet"
        js = d / "all.json"
        xl = d / "all.xlsx"
        n_el = export.to_parquet_elasmo(con, pq)
        export.to_json(con, js)
        export.to_xlsx(con, xl)
        assert n_el == 1 and pq.exists() and js.exists() and xl.exists()
        import json
        data = json.loads(js.read_text())
        assert len(data) == 2
