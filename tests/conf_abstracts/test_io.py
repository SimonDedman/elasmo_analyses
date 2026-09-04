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


def test_elasmo_lexicon_ray_noise():
    """\\bray\\b matched ray-finned fishes, fin-ray counts and X-rays: 143 of
    1,226 content-flagged elasmo records were false positives (2026-09-04)."""
    from conf_abstracts.lexicon import is_elasmo_text
    assert not is_elasmo_text("Evolution of the gular muscles in ray-finned fishes", "")
    assert not is_elasmo_text("Systematic revision", "a lower count of 1st dorsal fin rays")
    assert not is_elasmo_text("Clutch frequency", "mark-recapture and X-ray analysis")
    assert not is_elasmo_text("Bembrops", "with fewer dorsal and pectoral rays")
    # the scrub must not cost us real batoids
    assert is_elasmo_text("Movement of manta rays in Indonesia", "")
    assert is_elasmo_text("Age and growth", "we sampled rays and sharks from the trawl")
    assert is_elasmo_text("Habitat use of the bat ray", "Myliobatis californica")


def test_oa_xlsx_author_split():
    from conf_abstracts.ingest_oa_xlsx import _split_authors
    # Oxford Abstracts comma-separates 'First Last', but submitters slip in
    # 'Surname, Initials', which a naive split tears in half.
    got = [a["full_name"] for a in
           _split_authors("Purushottama, G. B., Muktha, M., Swatipriyanka Sen Dash", "")]
    assert got == ["G. B. Purushottama", "M. Muktha", "Swatipriyanka Sen Dash"], got
    auth = _split_authors("Brooke Anderson, Neil Hammerschlag", "Brooke Anderson")
    assert [a["is_presenter"] for a in auth] == [1, 0]
    # presenter not found in the list -> first author, flagged as inferred
    auth = _split_authors("B. Anderson, Neil Hammerschlag", "Brooke Anderson")
    assert auth[0]["is_presenter"] == 1 and auth[0]["presenter_inferred"] == 1


def test_oa_xlsx_presentation_type():
    from conf_abstracts.ingest_oa_xlsx import _presentation_type, _award
    assert _presentation_type("Contributed 15-minute Oral Paper VIRTUAL") == "talk"
    assert _presentation_type("Student Poster Competition (all are virtual)") == "poster"
    assert _presentation_type("Contributed 5-minute Lightning Paper") == "lightning"
    assert _presentation_type("Invited Symposium (all are virtual)") == "symposium"
    assert _award("Student Oral Competition IN-PERSON") == "Student Oral Competition"
    assert _award("Contributed 15-minute Oral Paper VIRTUAL") is None


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
