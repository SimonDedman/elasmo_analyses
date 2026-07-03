import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_parse_tool_response_to_dict():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.fable_extract import parse_tool_response
    fake = {"columns": [
        {"name": "d_movement", "present": True, "evidence": "acoustic telemetry", "confidence": 0.9},
        {"name": "pr_fishing", "present": False, "evidence": "", "confidence": 0.8}]}
    out = parse_tool_response(fake)
    assert out["d_movement"]["present"] is True
    assert out["d_movement"]["evidence"] == "acoustic telemetry"
    assert out["pr_fishing"]["present"] is False


def test_schema_column_defs_nonempty():
    """Schema column defs are built from ALL_SCHEMAS (7 SchemaCategory
    objects) with name+description, no network/API needed."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.fable_extract import _schema_column_defs
    cols = _schema_column_defs()
    assert len(cols) > 100
    names = {c["name"] for c in cols}
    assert "eco_pelagic" in names
    sample = next(c for c in cols if c["name"] == "eco_pelagic")
    assert "description" in sample and sample["description"]


def test_pdf_text_resolves_sample_paper():
    """_pdf_text() resolves real PDF text + sha1 for a paper on the
    validation sample list, using only local files (no network)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import pandas as pd
    from validation.fable_extract import _pdf_text

    sample_csv = ROOT / "outputs/validation/validation_sample.csv"
    if not sample_csv.exists():
        import pytest
        pytest.skip("validation_sample.csv not present")

    sample = pd.read_csv(sample_csv, dtype={"literature_id": str})
    resolved = False
    for lit_id in sample["literature_id"].head(20):
        text, sha1 = _pdf_text(lit_id)
        if text:
            resolved = True
            assert isinstance(sha1, str) and len(sha1) == 40
            assert len(text) > 0
            break
    assert resolved, "expected at least one of the first 20 sample papers to resolve a PDF"
