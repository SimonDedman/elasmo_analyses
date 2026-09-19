"""Tests for the lid-named staging identity override. Touches only pytest's tmp_path."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest_pdfs import load_identity_override  # noqa: E402


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
