"""Tests for the lid-named staging identity override. Touches only pytest's tmp_path."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest_pdfs import expected_page_length, load_identity_override, whole_volume_reason  # noqa: E402


def _side(tmp_path, lid, payload):
    pdf = tmp_path / f"{lid}.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    pdf.with_suffix(".identity.json").write_text(json.dumps(payload))
    return pdf


def test_accepts_matching_id_with_evidence(tmp_path):
    pdf = _side(tmp_path, "13024", {"literature_id": "13024", "verified_by": "Simon",
                                    "evidence": "species heading and author are on page 1 of the extract"})
    assert "identity override by Simon" in load_identity_override(pdf, "13024")


def test_rejects_other_id(tmp_path):
    pdf = _side(tmp_path, "13024", {"literature_id": "992", "verified_by": "Simon",
                                    "evidence": "species heading and author are on page 1 of the extract"})
    assert load_identity_override(pdf, "13024") is None


def test_rejects_id_that_is_not_the_filename(tmp_path):
    pdf = _side(tmp_path, "13024", {"literature_id": "992", "verified_by": "Simon",
                                    "evidence": "species heading and author are on page 1 of the extract"})
    assert load_identity_override(pdf, "992") is None


def test_rejects_empty_evidence_or_verifier(tmp_path):
    assert load_identity_override(_side(tmp_path, "1", {"literature_id": "1", "verified_by": "Simon", "evidence": "ok"}), "1") is None
    assert load_identity_override(_side(tmp_path, "2", {"literature_id": "2", "verified_by": "", "evidence": "x" * 40}), "2") is None


def test_absent_or_broken_sidecar(tmp_path):
    pdf = tmp_path / "5.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    assert load_identity_override(pdf, "5") is None
    pdf.with_suffix(".identity.json").write_text("{not json")
    assert load_identity_override(pdf, "5") is None


def test_expected_page_length_reads_the_last_range():
    assert expected_page_length({"findspot_raw": "Copeia, 1950(3), 165\u2013175"}) == 11
    assert expected_page_length({"findspot_raw": "NOAA Technical Report NMFS, 90: 304\u201326"}) == 23
    assert expected_page_length({"journal": "Biological Bulletin, 59, 179-186"}) == 8
    assert expected_page_length({"findspot_raw": "Tokai U. Press"}) is None
    # plates, figures and a trailing appendix pair must not be mistaken for the page range
    assert expected_page_length({"findspot_raw": "Verh. Batav. Genoot., 25: 1\u2013164, Pls. 1\u20136. [+ 6 pls. in v. 26, p. 165\u2013166."}) == 166
    assert expected_page_length({"findspot_raw": "London, vol. 1, pp. i\u2013vii, 1\u201378, pls 1\u201350"}) == 78
    assert expected_page_length({"findspot_raw": "Gen\u00e8ve, Fick, 1850, pl. 1\u201310."}) is None
    assert expected_page_length({"findspot_raw": "Gland: 259\u2013260, 262\u2013264"}) == 5


def test_whole_volume_is_held_and_an_article_is_not(tmp_path):
    import pymupdf
    def make(n):
        d = pymupdf.open()
        for _ in range(n):
            d.new_page()
        f = tmp_path / f"{n}.pdf"
        d.save(f)
        return f
    row = {"findspot_raw": "Copeia, 1950(3), 165\u2013175"}          # 11 printed pages
    assert whole_volume_reason(make(101), row)                        # whole issue
    assert whole_volume_reason(make(14), row) is None                 # article + plates
    assert whole_volume_reason(make(101), {"findspot_raw": "no pages here"}) is None


def test_match_pdf_uses_a_filename_that_is_a_doi_suffix(tmp_path):
    from ingest_pdfs import match_pdf
    f = tmp_path / "rstb.1924.0007.pdf"
    f.write_bytes(b"%PDF-1.4\n")
    row = {"literature_id": "10908", "title": "Some Peculiarities", "authors": "Burne, R.H. (1924)", "year": 1924}
    other = {"literature_id": "1", "title": "x", "authors": "y", "year": 1939}
    lookup = {"10.1098/rstb.1924.0007": row, "10.1098/rstb.1939.0008": other}
    got, how = match_pdf(f, lookup, {}, [row, other])
    assert got is row and "DOI suffix" in how
    # two DOIs sharing a suffix is ambiguous, so it must not match on this rule
    lookup["10.9999/rstb.1924.0007"] = other
    got, how = match_pdf(f, lookup, {}, [row, other])
    assert not (got is row and "DOI suffix" in (how or ""))
